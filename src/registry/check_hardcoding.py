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


def portable(path):
    """A repo-relative path with this city's directory written `<city>/`.

    So a framework register can name a file inside a city without naming the
    city - the same reason the manifest records city-relative paths.
    """
    prefix = 'cities/%s/' % _city.CITY
    return '<city>/' + path[len(prefix):] if path.startswith(prefix) else path


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
        # An audit does not get to cite itself as evidence. This module names
        # keys in PENDING_CONSUMER and MEASUREMENT_OWNED_KEYS to EXCUSE them,
        # and counting those mentions as reads marked all seven pending fields
        # wired - which emptied the unwired list and made the gate pass for the
        # worst possible reason. Same exclusion the other four scans already use.
        if r in SELF_REFERENTIAL:
            continue
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
        # A key BUILT at the call site, e.g.
        # `CFG.get('C.constraint.trip_length_km.%s' % mode)`. The docstring of
        # this audit has always conceded that a field may legitimately be read
        # by prefix; conceding it and then not detecting it reported eleven
        # measured constraint fields as unwired while a builder read every one.
        for pattern in _key_patterns(literals):
            for key in keys:
                if pattern.match(key):
                    out.setdefault(key, set()).add(r)
    return out


def _key_patterns(literals):
    """Regexes for string literals that CONSTRUCT a key rather than being one.

    Only literals that already look like a registry key are considered - at
    least two dotted segments and a placeholder - so an unrelated format string
    cannot start matching fields.
    """
    out = []
    for text in literals:
        if text.count('.') < 2:
            continue
        if '%s' not in text and '%d' not in text and '{}' not in text:
            continue
        # Split on the placeholders FIRST and escape only the literal parts.
        # Escaping the whole string and then substituting does not work: since
        # Python 3.7 re.escape leaves `%` alone, so `\%s` never matches and the
        # eleven measured constraint fields kept reporting as unwired while a
        # builder read every one of them.
        parts = re.split(r'(%s|%d|\{\})', text)
        # A placeholder stands for ONE key segment, so it must not match a dot.
        # Allowing dots made 'B.counts.%s' match D.retail.vacancy_rate and every
        # other field, which silently emptied the unwired list - a checker that
        # passes because its pattern is too greedy is worse than no checker.
        body = ''.join(r'\w+' if p in ('%s', '{}')
                       else (r'\d+' if p == '%d' else re.escape(p))
                       for p in parts)
        try:
            out.append(re.compile('^' + body + '$'))
        except re.error:
            continue
    return out


def schema_referenced_keys():
    """Field keys named by the portable config schema rather than by code.

    `RUN.replanning.subpopulations` is read through the `repeat_over` clause of
    config/schema/param_config.json - the emitter never spells the key in
    Python. A field wired through a declaration is wired.
    """
    found = set()
    path = os.path.join(REPO, 'config', 'schema', 'param_config.json')
    if not os.path.exists(path):
        return found

    def walk(node):
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str):
            found.add(node)
    walk(json.load(io.open(path, encoding='utf-8')))
    return found


def identity_referenced_keys(fields):
    """Field keys named inside another field's `derived_from` identity.

    A field that is an INPUT to a declared identity participates in the model
    through that identity. `C.vot.trip_weighted` is the trip-weighted value of
    time: nothing spells its key, and three computed scoring fields name it as
    the quantity they are derived from.
    """
    found = set()
    for f in fields.values():
        if not isinstance(f, dict):
            continue
        found.update((f.get('derived_from') or {}).get('fields') or [])
    return found


# --------------------------------------------------------------------------
# Fields DECLARED AHEAD OF THE CODE THAT WILL CONSUME THEM, each named against
# the phase or issue that will wire it.
#
# An unwired field is not a hardcoded value - it is the opposite - but the
# handover brief is right that it is still a defect: "a declared field that
# nothing reads is worse than no field, because it looks like the model is
# configurable when it is not". The cure is not to hide it. It is to say WHEN
# it becomes real, so an entry here is a commitment with an owner rather than a
# tolerated gap, and a NEW unwired field with no entry fails the gate.
# --------------------------------------------------------------------------
PENDING_CONSUMER = {
    'B.activity.weekend_to_weekday':
        'measured from the RMS hourly counts, which carry dates. Deliverable '
        '0b folds it into the day-type shape; nothing reads it until the SAT '
        'and SUN demand is rebuilt on it',
    'B.counts.heavy_vehicle_share':
        'issue #24. The measured 6.52% heavy share is the basis of the freight '
        'layer, and no freight is generated yet - the model has no trucks to '
        'apply it to',
    'B.counts.vehicles_per_car_leg':
        'issue #20. Converts modelled legs to vehicles for comparison against '
        'observed counts, and count-based calibration is blocked until the '
        'boundary through traffic lands - calibrate.py enforces that',
    'B.counts.vehicles_per_ride_leg':
        'issue #20, the ride half of the same conversion',
    'C.constraint.passenger_per_driver':
        'issue #31. It bounds how many passengers one driver may carry, and '
        'the constraint that would enforce it is not adopted: eqasim\'s '
        'PassengerConstraint is a trip-level biconditional that consults no '
        'driver, and adopting it would pin the ride share to the B2 seed',
    'D.retail.vacancy_rate':
        'P6, and UNOBTAINED. Hypothesis B2 depends on it, no frontage-level '
        'retail audit is published for the corridor, so it is swept rather '
        'than pinned and nothing consumes it before P6',
    'RUN.sumo.outer_loop_max_iterations':
        'P5. SUMO has been built six times and simulated zero times, '
        'deliberately, so the MATSim-SUMO outer loop it bounds has never run',
}

TOOL_BINDINGS = ('matsim_param', 'sumo_param',
                 'pt2matsim_osm_param', 'pt2matsim_mapper_param')

# --------------------------------------------------------------------------
# Numbers that are NOT model values, each with the reason it stays in code.
#
# This is the same device as `check_legacy_drift.EXPECTED_DIVERGENCE`: a
# deliberate exception is recorded in a file under version control, with a
# written justification, rather than silently filtered. An entry here is a
# claim - "this number decides nothing about the transport system" - and it is
# reviewable precisely because it had to be written down.
#
# Keyed by "path:SYMBOL", with a city's own directory written `<city>/` so this
# framework file does not name a place. A MODEL VALUE MUST NEVER BE ADDED HERE:
# if you cannot state why a number is not a modelling choice in one sentence,
# it is one.
# --------------------------------------------------------------------------
STRUCTURAL = {
    'src/analyse/run_view.py:RAMP_MIN':
        'a display scale: the narrowest and widest a congestion ramp is drawn. '
        'The live view reads the run and never writes to it, so no number here '
        'can reach a result',
    'src/analyse/run_view.py:RAMP_MAX':
        'the other end of the same display scale',
    'src/analyse/run_view.py:_send(code)':
        'an HTTP status code. The default 200 is the HTTP specification, not a '
        'transport parameter',
    'src/analyse/replay_events.py:--step':
        'replay animation step in seconds - how often the REPLAY PAGE redraws a '
        'finished run. It reads events already written and changes nothing',
    'src/analyse/replay_events.py:--keep-every':
        'replay decimation, for page size only',
    'src/analyse/replay_events.py:--horizon-h':
        'how much of the simulated day the replay page draws. The day window '
        'itself is RUN.qsim.end_time_h, which IS declared',
    'src/analyse/replay_events.py:--net-sample':
        'how many network links the replay page draws, for page size only',
    'src/calibrate/report.py:pct(nd)':
        'decimal places in a printed percentage',
    'src/build/build_data_dictionary.py:sniff(n)':
        'how many rows of a CSV are read to infer its column types. A property '
        'of the file reader, not of the data',
    'src/build/det_io.py:gzip_writer(compresslevel)':
        'gzip compression level. FIXED FOR DETERMINISM rather than chosen for a '
        'model reason: the level changes the bytes, so it is pinned and must '
        'not vary. It affects file size, never content',
    'src/build/measure_osm_defaults.py:MIN_TAGGED':
        'the minimum tagged-edge count before an observed class median replaces '
        'an assumed default. It governs HOW A MEASUREMENT IS TAKEN, not what '
        'the model consumes - the values it produces are what enter the '
        'registry, each with its own observed sweep. The reasoning is written '
        'above the constant',
    'src/build/build_matsim_network.py:--workers':
        'process count for the OSM merge. Throughput only - unlike '
        'RUN.machine.threads, which partitions the mobsim network and IS part '
        'of a run identity',
    'src/build/build_matsim_network.py:--threads':
        'a build-time override for the mapper thread count, which otherwise '
        'comes from RUN.machine.threads',
    'src/run/run_matsim.py:setp(count)':
        'how many regex matches to replace. A re.sub argument',
    'src/registry/param_config.py:SECONDS_PER_UNIT':
        'how many seconds are in an hour and a minute. The definition of the '
        'units themselves, not a value about any city',
    '<city>/build/build_sumo_corridor.py:_indent(level)':
        'XML pretty-printing indent depth',
    '<city>/build/build_scenario_schedules.py:'
    'scale_lr_runtime(delta_per_intermediate_s)':
        'a NEUTRAL default of zero: "change nothing unless a caller asks". Each '
        'caller passes the scenario delta it means, and those deltas are '
        'declared (E.s2b.signal_delay_removed_share and its siblings)',
    '<city>/build/build_scenario_schedules.py:'
    'scale_lr_runtime(delta_per_segment_s)':
        'the other neutral zero of the same function',
}


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
            and k not in uses and k not in PENDING_CONSUMER]


def pending(fields, uses):
    """Unwired fields that carry a written reason and the phase that will wire them."""
    return [(k, PENDING_CONSUMER[k]) for k in sorted(PENDING_CONSUMER)
            if k in fields and k not in uses and not is_bound(fields[k])]


def stale_pending(fields, uses):
    """A PENDING_CONSUMER entry for a field that is now wired, or is gone.

    The register is a promise that something will read the field. When it does,
    the promise is kept and the entry must go - otherwise the list grows into a
    permanent excuse, which is what any allowlist becomes if nothing prunes it.
    """
    return sorted(k for k in PENDING_CONSUMER
                  if k not in fields or k in uses or is_bound(fields.get(k, {})))


# Layers whose fields BELONG to the measurement apparatus: how the calibration
# loop searches, how the live view polls, how flat a mode-share trace must be
# before a run is called settled. A field here being read only by src/analyse or
# src/calibrate is correct, not a defect - so it is reported for visibility and
# not counted against the gate. Anything else read only there is printed back
# after a run while deciding nothing, which is the trap.
MEASUREMENT_OWNED_PREFIXES = ('CAL.', 'RUN.monitor.', 'RUN.relaxation.')

# Individual fields that belong to the measurement apparatus without sharing a
# prefix with it. Each states why.
MEASUREMENT_OWNED_KEYS = {
    'B.counts.station_match_radius_m':
        'the radius that joins an observed traffic count station to a network '
        'link. It decides what the VALIDATION compares, never what the model '
        'simulates, so being read only by src/analyse is correct',
}


def report_only(fields, uses):
    """A field only the measurement layer reads: printed back, never applied.

    Returns (defects, owned). A bound field is excluded from both: it reaches its
    tool through the binding, so where its key happens to be spelled in code
    says nothing about whether it decides anything - the perturbation probe
    answers that, and answers it better.
    """
    defects, owned = [], []
    for key in sorted(uses):
        if is_bound(fields[key]):
            continue
        where = {p for p in uses[key] if not is_test(p)}
        if not where or not all(is_measurement(p) for p in where):
            continue
        row = (key, fields[key].get('source'), sorted(where))
        if key.startswith(MEASUREMENT_OWNED_PREFIXES) or key in MEASUREMENT_OWNED_KEYS:
            owned.append(row)
        else:
            defects.append(row)
    return defects, owned


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
def stale_structural(corpus):
    """A STRUCTURAL entry naming a symbol that no longer exists.

    An allowlist that outlives what it excuses is how an exception quietly
    becomes a blanket. Each entry is checked against the scanner's own
    findings, so deleting a constant deletes its excuse with it.
    """
    seen = set()
    for p in sorted(corpus):
        r = rel(p)
        if not p.endswith('.py') or r in SELF_REFERENTIAL or is_test(r):
            continue
        try:
            for d in _legacy.scan_decisions(p):
                seen.add('%s:%s' % (portable(r), d['name']))
        except SyntaxError:
            continue
    return sorted(k for k in STRUCTURAL if k not in seen)


def script_decisions(corpus, fields):
    pinned = {str(f.get('legacy_symbol', '')).rsplit(':', 1)[-1]
              for f in fields.values()
              if isinstance(f, dict) and f.get('legacy_symbol')}
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
            if '%s:%s' % (portable(r), d['name']) in STRUCTURAL:
                continue
            if d['name'] in pinned:
                # Pinned to its registry field by `legacy_symbol` and compared
                # with it on every run of check_legacy_drift.py. Two copies of a
                # number, but not two UNCOMPARED copies - which is the thing
                # that bites. Accounted for by a different committed check
                # rather than excused here.
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


# --------------------------------------------------------------------------
# 8. Java-side defaults that shadow a declared value
# --------------------------------------------------------------------------
# A MATSim ConfigGroup field is a config parameter when a @StringSetter names
# it. Its Java initialiser is the value used IF THE CONFIG NEVER SETS IT - so a
# default equal to the declared value is the worst case the handover brief
# names: right by accident, every test passing, and silently wrong the moment
# anyone sweeps the field, because a config that lost the binding would run on
# the Java number and report success.
JAVA_FIELD = re.compile(
    r'private\s+(?:static\s+)?(?:final\s+)?(?:double|int|long|float|boolean|String)\s+'
    r'(\w+)\s*=\s*([^;]+);')
JAVA_SETTER = re.compile(r'@StringSetter\("([^"]+)"\)')


def _java_literal(text):
    """The Java initialiser as a Python value, or None if it is not a literal."""
    raw = text.strip().rstrip('LlFfDd') if text.strip()[-1:] in 'LlFfDd' else text.strip()
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    if raw in ('true', 'false'):
        return raw == 'true'
    try:
        return float(raw) if '.' in raw or 'e' in raw.lower() else int(raw)
    except ValueError:
        return None


def java_shadow_defaults(corpus, fields):
    """A Java config default that EQUALS the value its registry field declares."""
    by_param = {}
    for key, f in fields.items():
        if not isinstance(f, dict):
            continue
        for target in str(f.get('matsim_param') or '').split(','):
            target = target.strip()
            if target and '[' not in target:
                by_param[target.split('.')[-1]] = (key, f.get('value'))

    out = []
    for path, text in sorted(corpus.items()):
        if not path.endswith('.java'):
            continue
        params = set(JAVA_SETTER.findall(text))
        for m in JAVA_FIELD.finditer(text):
            name, raw = m.group(1), m.group(2)
            if name not in params or name not in by_param:
                continue
            value = _java_literal(raw)
            if value is None:
                continue
            key, declared = by_param[name]
            same = value == declared
            if isinstance(declared, list) and len(declared) == 1:
                same = value == declared[0]
            if isinstance(declared, (int, float)) and isinstance(value, (int, float)):
                same = abs(float(value) - float(declared)) < 1e-9
            if same:
                out.append((rel(path), text[:m.start()].count('\n') + 1,
                            name, raw.strip(), key))
    return out


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
    # Two more ways a field reaches the model without its key being spelled in
    # Python: named by the portable config schema, or named as an input to
    # another field's declared derived_from identity.
    for key in schema_referenced_keys() | identity_referenced_keys(fields):
        if key in fields:
            uses.setdefault(key, set()).add('config/schema/param_config.json')
    reaching, inert, error = config_reach()
    defects, owned = report_only(fields, uses)
    led = dict(
        unwired=unwired(fields, uses),
        report_only=defects,
        stale_structural=[(k,) for k in stale_structural(corpus)],
        stale_pending=[(k,) for k in stale_pending(fields, uses)],
        template_literals=template_literals(corpus),
        script_decisions=script_decisions(corpus, fields),
        coordinates=coordinates(corpus),
        java_shadow_defaults=java_shadow_defaults(corpus, fields),
        inert_bindings=[(k,) for k in inert],
    )
    if error:
        led['reach_probe_failed'] = [(error,)]
    return corpus, fields, led, len(reaching), owned, pending(fields, uses)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--strict', action='store_true',
                    help='exit 1 if anything is reported')
    ap.add_argument('--json', metavar='OUT',
                    help='write the ledger as JSON as well as printing it')
    a = ap.parse_args()

    corpus, fields, led, n_reaching, owned, pending_rows = audit()

    print('city %s - %d declared field(s), %d source file(s)\n'
          % (_city.CITY, len(fields), len(corpus)))

    print('1. DECLARED BUT UNWIRED - the key appears nowhere as a value')
    for key, src, status in led['unwired']:
        print('     %-46s source=%-11s status=%s' % (key, src, status))
    print('     %d\n' % len(led['unwired']))

    print('   DECLARED AHEAD OF ITS CONSUMER - unwired, with a written reason')
    for key, why in pending_rows:
        print('     %-46s %s' % (key, why[:72]))
    print('     %d  (not counted: each names the phase or issue that will wire '
          'it, and a NEW unwired field with no reason fails the gate)\n'
          % len(pending_rows))

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

    print('6. JAVA DEFAULTS THAT EQUAL THEIR DECLARED VALUE - right by accident')
    for f, ln, name, raw, key in led['java_shadow_defaults']:
        print('     %s:%-5d %-22s = %-12s shadows %s' % (f, ln, name, raw, key))
    print('     %d\n' % len(led['java_shadow_defaults']))

    print('7. INERT BINDINGS - the field is declared, resolves, and moving it '
          'changes NOTHING')
    for (key,) in led['inert_bindings']:
        print('     %s' % key)
    for (why,) in led.get('reach_probe_failed', []):
        print('     PROBE FAILED (not a pass): %s' % why)
    print('     %d of %d bound field(s) proven to reach the config by changing '
          'them\n' % (n_reaching, n_reaching + len(led['inert_bindings'])))

    print('8. STALE EXCEPTIONS - a STRUCTURAL entry whose symbol is gone')
    for (key,) in led['stale_structural']:
        print('     %s' % key)
    print('     %d of %d structural exception(s) no longer name anything'
          % (len(led['stale_structural']), len(STRUCTURAL)))
    for (key,) in led['stale_pending']:
        print('     %s is now wired - drop its PENDING_CONSUMER entry' % key)
    print('     %d of %d pending-consumer entr(ies) are kept promises to prune\n'
          % (len(led['stale_pending']), len(PENDING_CONSUMER)))

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
