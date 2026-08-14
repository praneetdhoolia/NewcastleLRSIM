#!/usr/bin/env python
"""Find values the model uses that were decided in a script, not declared.

    python src/registry/check_hardcoding.py            report
    python src/registry/check_hardcoding.py --strict   exit 1 if anything is found

This repository's signature defect is not a wrong number. It is a number in a
place nobody looks: a declared field that reaches nothing, a template literal
that shadows it, a sweep range typed beside the value it is supposed to bound.
Every instance found so far was caught by ARITHMETIC or by an audit, never by
reading the code, so the audit is committed rather than remembered.

Four questions, asked separately because the answers mean different things:

  1. UNWIRED FIELDS   a declared field whose key no source file names. It cannot
                      reach the model, whatever `consumers` claims.
  2. TEMPLATE LITERALS a <param name=... value=...> written as a constant rather
                      than substituted. Each is a modelling choice in a builder.
  3. SCRIPT CONSTANTS  a module-level NUMERIC constant in the build/run layer.
  4. COORDINATES       a latitude/longitude pair typed into a script. The hard
                      constraint is absolute: a coordinate belongs in
                      `cities/<city>/geometry/` or the registry, never in code.

It reports; it does not judge. A field may legitimately be read by prefix, and a
constant may be structural. The point is that every one of them is SEEN.

City-agnostic: the city comes from `city.py`, and nothing here names a place.
"""
import argparse
import ast
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, '..'))
import city as _city  # noqa: E402

REPO = os.path.abspath(os.path.join(_HERE, '..', '..'))
SKIP_DIRS = {'.git', '__pycache__', '.tools', 'results', 'node_modules', '.venv'}
CODE_EXT = ('.py', '.java', '.html')

# Structural names: a path, a column list, a regex. Not modelling values.
IGNORE_SUFFIX = ('_FILE', '_DIR', '_PATH', '_RE', '_COLS', '_COLUMNS', '_URL',
                 '_HEADER', '_ENCODING', '_SEP', '_EPOCH', '_EXT')

# A latitude/longitude pair, as a tuple of two floats with at least four
# decimals. The magnitude test matters: a sweep tuple like (-0.00025, -0.00012)
# has the same shape and is not a place, so both components must also be big
# enough to BE a coordinate and small enough to be a legal one.
LATLON = re.compile(r'\(\s*(-?\d{1,3}\.\d{4,})\s*,\s*(-?\d{1,3}\.\d{4,})\s*\)')


def _is_place(lat, lon):
    return 1.0 <= abs(lat) <= 90.0 and 1.0 <= abs(lon) <= 180.0


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


def load_fields():
    reg = os.path.join(_city.CITY_DIR, 'registry')
    fields = {}
    for f in sorted(os.listdir(reg)):
        if f.endswith('.json'):
            doc = json.load(open(os.path.join(reg, f), encoding='utf-8'))
            fields.update(doc.get('fields', doc))
    return fields


def unwired(fields, corpus):
    out = []
    for key, meta in sorted(fields.items()):
        if not isinstance(meta, dict):
            continue
        if not any(key in t for t in corpus.values()):
            out.append((key, meta.get('source'), meta.get('status')))
    return out


def template_literals(corpus):
    """<param name="X" value="Y"> where Y is a constant, not a {substitution}."""
    param = re.compile(r'<param name="([^"]+)" value="([^"]*)"')
    out = []
    for p, text in sorted(corpus.items()):
        # Builders only. A checker that greps for the same pattern is not
        # writing a config, and reporting its regex as a hardcoded value is how
        # an audit trains people to ignore it.
        if not p.endswith('.py') or os.sep + 'build' + os.sep not in p:
            continue
        for m in param.finditer(text):
            name, val = m.group(1), m.group(2)
            # Both substitution styles count as wired: `{x}` for str.format and
            # `%s` for printf. Only a bare constant is a decision made here.
            if '{' in val or '%' in val:
                continue
            out.append((rel(p), text[:m.start()].count('\n') + 1, name, val))
    return out


def _is_num(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
            and not isinstance(node.value, bool):
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return _is_num(node.operand)
    return False


def _num(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_num(node.operand)
    return None


def script_constants(corpus):
    out = []
    for p, text in sorted(corpus.items()):
        if not p.endswith('.py'):
            continue
        if os.sep + 'build' + os.sep not in p and os.sep + 'run' + os.sep not in p:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if len(names) != 1:
                continue
            name = names[0]
            if not name.isupper() or name.endswith(IGNORE_SUFFIX):
                continue
            if _is_num(node.value):
                out.append((rel(p), node.lineno, name, _num(node.value)))
    return out


def coordinates(corpus):
    out = []
    for p, text in sorted(corpus.items()):
        if not p.endswith('.py'):
            continue
        for m in LATLON.finditer(text):
            if not _is_place(float(m.group(1)), float(m.group(2))):
                continue
            line = text[:m.start()].count('\n') + 1
            out.append((rel(p), line, m.group(0)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--strict', action='store_true',
                    help='exit 1 if anything is reported')
    a = ap.parse_args()

    corpus = {}
    for p in sources():
        try:
            corpus[p] = open(p, encoding='utf-8', errors='replace').read()
        except OSError:
            pass

    fields = load_fields()
    un = unwired(fields, corpus)
    tl = template_literals(corpus)
    sc = script_constants(corpus)
    co = coordinates(corpus)

    print('city %s - %d declared field(s), %d source file(s)\n'
          % (_city.CITY, len(fields), len(corpus)))

    print('1. DECLARED BUT UNWIRED - no source file names the key')
    for key, src, status in un:
        print('     %-46s source=%-11s status=%s' % (key, src, status))
    print('     %d\n' % len(un))

    print('2. TEMPLATE LITERALS - a <param> constant rather than a substitution')
    for f, ln, name, val in tl:
        print('     %s:%-5d %-42s = %s' % (f, ln, name, val))
    print('     %d\n' % len(tl))

    print('3. NUMERIC CONSTANTS in the build/run layer')
    for f, ln, name, val in sc:
        print('     %s:%-5d %-34s = %s' % (f, ln, name, val))
    print('     %d\n' % len(sc))

    print('4. COORDINATES typed into a script - always a violation')
    for f, ln, txt in co:
        print('     %s:%-5d %s' % (f, ln, txt))
    print('     %d\n' % len(co))

    total = len(un) + len(tl) + len(sc) + len(co)
    print('TOTAL %d item(s). A number in a script is a modelling choice nobody '
          'can see or sweep.' % total)
    if a.strict and total:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
