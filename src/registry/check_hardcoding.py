#!/usr/bin/env python
"""Find values the model uses that were decided in a script, not declared.

    python src/registry/check_hardcoding.py            report
    python src/registry/check_hardcoding.py --strict   exit 1 if anything is found
    python src/registry/check_hardcoding.py --json OUT machine-readable ledger

This repository's signature defect is not a wrong number. It is a number in a
place nobody looks: a declared field that reaches nothing, a template literal
that shadows it, a sweep range typed beside the value it is supposed to bound.
Every instance found so far was caught by ARITHMETIC or by an audit, never by
reading the code, so the audit is committed rather than remembered.

Five questions, asked separately because the answers mean different things:

  1. UNWIRED FIELDS   a declared field whose key appears nowhere in the source
                      as a value. It cannot reach the model, whatever
                      `consumers` claims.
  2. REPORT-ONLY      a declared field read ONLY by the measurement layer. It
                      is printed back after a run; it decides nothing.
  3. TEMPLATE LITERALS a <param name=... value=...> written as a constant rather
                      than substituted. Each is a modelling choice in a builder.
  4. SCRIPT DECISIONS a value decided in code rather than declared - in any of
                      the five forms `scan_decisions` distinguishes.
  5. COORDINATES      a latitude/longitude pair typed into a script. The hard
                      constraint is absolute: a coordinate belongs in
                      `cities/<city>/geometry/` or the registry, never in code.

**What changed, and why the count moved.** The first version of this audit
asked whether a field key was a SUBSTRING of any source file. That counted a
mention in a comment, a docstring or a test assertion as reach - so
`RUN.controler.write_events_interval`, named only in a Java comment, and
`A.signals.scats_phasing`, named only in a test, both passed as wired while
deciding nothing. Worse, the count fell when someone added an explanatory
comment. A gate you can satisfy by editing prose is not a gate. A key is now
counted as reaching the model only where it appears as a COMPLETE STRING
LITERAL in non-test source - the form a key takes when it is data.

The constant scan has the same history. It looked only at module-level,
single-target, ALL-CAPS, SCALAR assignments, which is a small minority of the
forms a decision takes: it could not see `ACCEL, DECEL = 1.2, 1.3`, a table of
stop coordinates, `def make_bus_shuttle(speed_kmh=28.0)`, or
`add_argument('--iterations', default=100)` for a field the registry declares
UNOBTAINED. It now delegates to `extract_legacy_constants.scan_decisions`,
which is the repository's one AST scanner for decided values.

It reports; it does not judge. A field may legitimately be read by prefix, and a
constant may be structural. The point is that every one of them is SEEN.

City-agnostic: the city comes from `city.py`, and nothing here names a place.
"""
import argparse
import ast
import io
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, '..'))
sys.path.insert(0, _HERE)
import city as _city  # noqa: E402
import registry as _registry  # noqa: E402
import extract_legacy_constants as _legacy  # noqa: E402

REPO = os.path.abspath(os.path.join(_HERE, '..', '..'))
SKIP_DIRS = {'.git', '__pycache__', '.tools', 'results', 'node_modules', '.venv'}
CODE_EXT = ('.py', '.java', '.html')

# The measurement apparatus: it reads a finished run and reports on it. A field
# read only here is printed, not applied. `calibrate.py` draws the same line for
# the same reason and this is the same list, imported rather than repeated.
MEASUREMENT_LAYERS = ('src/analyse/', 'src/calibrate/')

# How many lines either side of a <param> match are searched for the regex call
# that would make it a pattern rather than a value. A pattern is often built
# over several lines, so one line is not enough of a window.
REGEX_WINDOW = 3

# Files that TALK ABOUT the pattern rather than commit it. An audit that reports
# its own regex trains people to ignore it.
SELF_REFERENTIAL = ('src/registry/check_hardcoding.py',
                    'src/registry/extract_legacy_constants.py',
                    'src/registry/check_legacy_drift.py')

# A latitude/longitude pair, in ANY syntactic position. The previous rule wanted
# a literal two-tuple, so it saw three of this repository's coordinates and
# missed nineteen - a scenario's whole stop alignment was written as
# `('Civic', -32.92699, 151.77175)` and never reported. The test is now per
# LINE: a line carrying both a plausible latitude and a plausible longitude is a
# place, whatever brackets are around it.
FLOAT = re.compile(r'-?\d{1,3}\.\d{4,}')
LAT_MAX, LON_MAX, PLACE_MIN = 90.0, 180.0, 1.0


def is_lat(v):
    return PLACE_MIN <= abs(v) <= LAT_MAX


def is_lon(v):
    return PLACE_MIN <= abs(v) <= LON_MAX


def sources(exts=CODE_EXT):
    """Every framework and city source file, city-relative agnostic."""
    for root in (os.path.join(REPO, 'src'), os.path.join(REPO, 'tests'),
                 _city.CITY_DIR, os.path.join(REPO, 'run.py')):
        if os.path.isfile(root):
            yield root
            continue
        for base, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            if os.path.abspath(base).startswith(os.path.join(_city.CITY_DIR,
                                                             'registry')):
                continue                  # a declaration is not a use
            for f in files:
                if f.endswith(exts):
                    yield os.path.join(base, f)


def rel(p):
    return os.path.relpath(p, REPO).replace(os.sep, '/')


def is_test(path):
    return path.startswith('tests/')


def is_measurement(path):
    return any(path.startswith(m) for m in MEASUREMENT_LAYERS)


# --------------------------------------------------------------------------
# 1 + 2. where a declared key is actually used
# --------------------------------------------------------------------------
JAVA_STRING = re.compile(r'"([^"\\]*)"')


def key_uses(corpus, keys):
    """{key: {file: True}} for every COMPLETE string literal naming a key.

    A key inside a comment or a docstring is prose about the model, not a read
    of it. Only a whole string literal is the model using the key as data, and
    that distinction is the whole difference between this audit and the one it
    replaces.
    """
    out = {}
    for path, text in sorted(corpus.items()):
        r = rel(path)
        literals = set()
        if path.endswith('.py'):
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            docstrings = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.FunctionDef,
                                     ast.AsyncFunctionDef, ast.ClassDef)):
                    doc = ast.get_docstring(node, clean=False)
                    if doc is not None and node.body:
                        first = node.body[0]
                        if isinstance(first, ast.Expr):
                            docstrings.add(id(first.value))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                        and id(node) not in docstrings:
                    literals.add(node.value)
        else:
            # Java and HTML have no AST here; a quoted run with no whitespace is
            # as close to "used as data" as a regex gets, and a comment naming a
            # key in prose does not survive it.
            literals = {m.group(1) for m in JAVA_STRING.finditer(text)}
        for key in keys:
            if key in literals:
                out.setdefault(key, set()).add(r)
    return out


TOOL_BINDINGS = ('matsim_param', 'sumo_param',
                 'pt2matsim_osm_param', 'pt2matsim_mapper_param')


def is_bound(field):
    """Does this field reach a tool through a declared parameter binding?

    A bound field does NOT need its key to appear in code: that is the point of
    building the config from the registry instead of substituting into a
    template. Its reach is decided by the perturbation probe - moving the value
    and watching the emitted config move - which is a stronger test than any
    text search, and it is reported separately as question 6.
    """
    return any(field.get(b) for b in TOOL_BINDINGS)


def unwired(fields, uses):
    """An UNBOUND field no source file names as data at all.

    Two routes to the model, so two tests. A field with a parameter binding is
    written into a tool's config by the emitter and is tested by moving it. A
    field without one has to be read by name somewhere, and if its key appears
    nowhere as a value then nothing can be reading it.
    """
    return [(k, fields[k].get('source'), fields[k].get('status'))
            for k in sorted(fields)
            if isinstance(fields[k], dict) and not is_bound(fields[k])
            and k not in uses]


def report_only(fields, uses):
    """A field only the measurement layer reads: printed back, never applied."""
    out = []
    for key in sorted(uses):
        where = {p for p in uses[key] if not is_test(p)}
        if where and all(is_measurement(p) for p in where):
            out.append((key, fields[key].get('source'), sorted(where)))
    return out


# --------------------------------------------------------------------------
# 3. config template literals
# --------------------------------------------------------------------------
def template_literals(corpus):
    """<param name="X" value="Y"> where Y is a constant, not a {substitution}."""
    param = re.compile(r'<param name="([^"]+)" value="([^"]*)"')
    out = []
    for p, text in sorted(corpus.items()):
        r = rel(p)
        if not p.endswith('.py') or r in SELF_REFERENTIAL or is_test(r):
            continue
        for m in param.finditer(text):
            name, val = m.group(1), m.group(2)
            # Both substitution styles count as WRITTEN FROM SOMEWHERE ELSE:
            # `{x}` for str.format and `%s` for printf. Whether that somewhere
            # is the resolver or a Python default is what question 4 answers.
            if '{' in val or '%' in val:
                continue
            line_no = text[:m.start()].count('\n') + 1
            lines = text.splitlines()
            # A REGEX that MATCHES a <param> is not a <param>. `setp` and
            # `set_mode_param` in the harness search for a parameter by name so
            # they can rewrite it; reporting their patterns as hardcoded values
            # is how an audit teaches people to skim past it. A window rather
            # than the one line, because a pattern is often built over several.
            window = '\n'.join(lines[max(0, line_no - 1 - REGEX_WINDOW):
                                     line_no + REGEX_WINDOW])
            if any(fn in window for fn in ('re.sub(', 're.subn(', 're.compile(',
                                           're.search(', 're.match(',
                                           're.finditer(')):
                continue
            out.append((r, line_no, name, val))
    return out


# --------------------------------------------------------------------------
# 4. values decided in code
# --------------------------------------------------------------------------
def script_decisions(corpus):
    out = []
    for p in sorted(corpus):
        r = rel(p)
        if not p.endswith('.py') or r in SELF_REFERENTIAL or is_test(r):
            continue
        try:
            found = _legacy.scan_decisions(p)
        except SyntaxError:
            continue
        for d in found:
            if d['kind'] != 'parameter':
                continue
            out.append((r, d['line'], d['form'], d['name'], d['value'],
                        d['n_numbers']))
    return out


# --------------------------------------------------------------------------
# 5. coordinates
# --------------------------------------------------------------------------
def _numeric_constants(tree):
    """{line: [value, ...]} for every numeric literal, negatives included.

    Read from the AST rather than from the text, so a figure quoted in a comment
    or a docstring - "an observed 1.3503", "lon 151.7767 to 151.7889" - cannot
    be reported as a place. Prose about a coordinate is not a coordinate.
    """
    by_line = {}
    for node in ast.walk(tree):
        value = None
        if isinstance(node, ast.Constant) and isinstance(node.value, float):
            value = node.value
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) \
                and isinstance(node.operand, ast.Constant) \
                and isinstance(node.operand.value, float):
            value = -node.operand.value
        if value is None:
            continue
        by_line.setdefault(node.lineno, []).append(value)
    return by_line


def coordinates(corpus):
    """A line whose literals include both a plausible latitude and longitude.

    Two passes, because either alone is wrong. The AST says which lines carry
    real numeric literals, so prose about a figure cannot be reported as a
    place. The SOURCE TEXT then supplies the precision, because a float's repr
    drops trailing zeros - `-32.92800` reprs as `32.928`, and judging precision
    from the parsed value silently dropped four of this repository's
    coordinates on the first attempt.
    """
    out = []
    for p, text in sorted(corpus.items()):
        r = rel(p)
        if not p.endswith('.py') or r in SELF_REFERENTIAL:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        lines = text.splitlines()
        numeric_lines = _numeric_constants(tree)
        for line in sorted(numeric_lines):
            if line > len(lines):
                continue
            src = lines[line - 1]
            vals = [float(m.group(0)) for m in FLOAT.finditer(src)]
            if any(is_lat(v) for v in vals) and any(is_lon(v) for v in vals):
                out.append((r, line, src.strip()[:96]))
    return out


# --------------------------------------------------------------------------
def config_reach():
    """Which bound fields move the emitted config, proven by moving them.

    This is the only check in the repository that can see a value which is
    declared, resolved, recorded in a run's provenance snapshot - and reaches
    nothing. `consumers` is a claim; a text search finds the key in a comment;
    reading the code has never once caught an instance. Changing the value and
    watching the output change has caught every one.

    Cheap enough to run on every commit: it emits a config per field, in memory,
    and never starts MATSim.

    Returns (reaching, inert, error). `error` is not a pass - it means the probe
    could not be built at all, which must be reported rather than counted as
    zero findings.
    """
    try:
        import param_config  # noqa: PLC0415
    except ImportError as exc:                            # noqa: BLE001
        return [], [], 'param_config unavailable: %s' % exc
    try:
        import sys as _s
        _s.path.insert(0, os.path.join(REPO, 'src', 'build'))
        import build_matsim_run_inputs as builder         # noqa: PLC0415
    except Exception as exc:                              # noqa: BLE001
        return [], [], 'the run-input builder does not import: %s' % exc
    try:
        sweep = _registry.load(strict=True).sweep('RUN.controler.last_iteration')
        interval = sweep['interval'] if isinstance(sweep, dict) else sweep
        city_doc = _city.descriptor()
        cfg = _registry.load(
            scenario=city_doc.get('intervention', {}).get('base_scenario'),
            day=city_doc['day_types'][0],
            set={'RUN.controler.last_iteration': int(interval[0])})
        scoring = builder.scoring_from_c1(
            cfg, json.load(io.open(builder.PARAMS, encoding='utf-8')),
            builder.hts_purpose_share())
        runtime = builder.config_runtime(cfg, scoring, city_doc['day_types'][0], dict(
            output='output', network='n', plans='p', schedule='s', vehicles='v',
            parking_prices='k', fraction=cfg.get('RUN.sample.fraction')))
    except Exception as exc:                              # noqa: BLE001
        return [], [], 'could not resolve a probe configuration: %s' % exc
    reaching, inert = param_config.reach('matsim', cfg, runtime)

    # The pt2matsim configs too. Their parameters are network-construction and
    # schedule-mapping choices - link splitting, candidate distance, which
    # network modes may carry a tram - and until this change all twenty-six of
    # them were literals in the network builder.
    try:
        import build_matsim_network as network            # noqa: PLC0415
        mapper_runtime = {
            'PublicTransitMapping.inputNetworkFile': ('n', 'path', ''),
            'PublicTransitMapping.inputScheduleFile': ('s', 'path', ''),
            'PublicTransitMapping.outputNetworkFile': ('o', 'path', ''),
            'PublicTransitMapping.outputScheduleFile': ('q', 'path', ''),
            'PublicTransitMapping.outputStreetNetworkFile': ('t', 'path', ''),
            'PublicTransitMapping.numOfThreads': (cfg.get('RUN.machine.threads'),
                                                  'derived', 'RUN.machine.threads'),
        }
        for tool_name, rt in (('pt2matsim_osm',
                               network.config_runtime_osm(cfg, 'osm', 'net')),
                              ('pt2matsim_mapper', mapper_runtime)):
            more_reaching, more_inert = param_config.reach(tool_name, cfg, rt)
            reaching = reaching + more_reaching
            inert = inert + more_inert
    except Exception as exc:                              # noqa: BLE001
        return reaching, inert, 'the pt2matsim probes did not run: %s' % exc
    return reaching, inert, None


def audit():
    """The whole ledger, as data. `--json` writes it; the gate checks it."""
    corpus = {}
    for p in sources():
        try:
            corpus[p] = io.open(p, encoding='utf-8', errors='replace').read()
        except OSError:
            pass
    fields, _ = _registry.load_registry()
    uses = key_uses(corpus, set(fields))
    reaching, inert, error = config_reach()
    led = dict(
        unwired=unwired(fields, uses),
        report_only=report_only(fields, uses),
        template_literals=template_literals(corpus),
        script_decisions=script_decisions(corpus),
        coordinates=coordinates(corpus),
        inert_bindings=[(k,) for k in inert],
    )
    if error:
        led['reach_probe_failed'] = [(error,)]
    return corpus, fields, led, len(reaching)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--strict', action='store_true',
                    help='exit 1 if anything is reported')
    ap.add_argument('--json', metavar='OUT',
                    help='write the ledger as JSON as well as printing it')
    a = ap.parse_args()

    corpus, fields, led, n_reaching = audit()

    print('city %s - %d declared field(s), %d source file(s)\n'
          % (_city.CITY, len(fields), len(corpus)))

    print('1. DECLARED BUT UNWIRED - the key appears nowhere as a value')
    for key, src, status in led['unwired']:
        print('     %-46s source=%-11s status=%s' % (key, src, status))
    print('     %d\n' % len(led['unwired']))

    print('2. REPORT-ONLY - read only by the measurement layer, decides nothing')
    for key, src, where in led['report_only']:
        print('     %-46s source=%-11s %s' % (key, src, ' '.join(where)))
    print('     %d\n' % len(led['report_only']))

    print('3. TEMPLATE LITERALS - a <param> constant rather than a substitution')
    for f, ln, name, val in led['template_literals']:
        print('     %s:%-5d %-42s = %s' % (f, ln, name, val))
    print('     %d\n' % len(led['template_literals']))

    print('4. VALUES DECIDED IN CODE - constant, table, unpacked, kwarg, CLI')
    for f, ln, form, name, val, n in led['script_decisions']:
        shown = ('%d numbers' % n) if n > 1 else repr(val)
        print('     %s:%-5d %-13s %-38s = %s' % (f, ln, form, name[:38], shown))
    print('     %d\n' % len(led['script_decisions']))

    print('5. COORDINATES typed into a script - always a violation')
    for f, ln, txt in led['coordinates']:
        print('     %s:%-5d %s' % (f, ln, txt))
    print('     %d\n' % len(led['coordinates']))

    print('6. INERT BINDINGS - the field is declared, resolves, and moving it '
          'changes NOTHING')
    for (key,) in led['inert_bindings']:
        print('     %s' % key)
    for (why,) in led.get('reach_probe_failed', []):
        print('     PROBE FAILED (not a pass): %s' % why)
    print('     %d of %d bound field(s) proven to reach the config by changing '
          'them\n' % (n_reaching, n_reaching + len(led['inert_bindings'])))

    total = sum(len(v) for v in led.values())
    print('TOTAL %d item(s). A number in a script is a modelling choice nobody '
          'can see or sweep.' % total)

    if a.json:
        with io.open(a.json, 'w', encoding='utf-8', newline='\n') as f:
            json.dump({k: [list(x) for x in v] for k, v in sorted(led.items())},
                      f, indent=2, ensure_ascii=False, sort_keys=True, default=str)
            f.write('\n')
        print('wrote %s' % a.json)

    if a.strict and total:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
