#!/usr/bin/env python
"""Refuse a city that cannot run, BEFORE it runs.

    python src/registry/check_city.py                 check the selected city
    python src/registry/check_city.py --city adelaide
    python src/registry/check_city.py --all

Without this, a half-populated city directory resolved cleanly and failed one
`get()` at a time, several hundred lines into a build - and a field a city
forgot to declare was indistinguishable from a field the framework had stopped
reading. This checks the city against the three portable documents:

    city.schema.json       identity: CRS, base year, boundary SOURCE, adapters
    required_fields.json   which values must be declared, and in what units
    layers.json            which artefacts the framework will ask for

and against the registry's own rules, which `field.schema.json` states and
`registry.validate()` enforces.

**It also checks the boundary in the other direction.** A framework that names
one city is not a framework. So the last check reads every framework source file
looking for this city's own name and the names in its boundary selector: a hit
is a place name that has leaked out of `cities/<city>/` and back into code that
is supposed to work for a city it has never seen. This is reported as a finding
rather than a pass/fail, because the repository currently has known instances
and hiding them would defeat the purpose.
"""
import argparse
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))
sys.path.insert(0, HERE)

import city as citymod                                        # noqa: E402
import registry                                               # noqa: E402

SCHEMA_DIR = os.path.join(REPO, 'config', 'schema')
FRAMEWORK_ROOTS = ('src', 'tests', 'config/schema')
FRAMEWORK_SKIP = ('src/city.py', 'src/registry/check_city.py')

_state = {'pass': 0, 'fail': 0, 'note': 0}


def check(ok, label, note=False):
    if note:
        _state['note'] += 1
        print('note  ' + label)
        return ok
    if ok:
        _state['pass'] += 1
    else:
        _state['fail'] += 1
        print('FAIL  ' + label)
    return ok


def read_json(path):
    with io.open(path, encoding='utf-8') as f:
        return json.load(f)


# --------------------------------------------------------------------------
def check_descriptor(city_dir, name):
    """city.json exists, parses, and satisfies city.schema.json."""
    path = os.path.join(city_dir, 'city.json')
    if not check(os.path.exists(path), '%s: city.json present' % name):
        return None
    try:
        doc = read_json(path)
    except ValueError as e:
        check(False, '%s: city.json is valid JSON (%s)' % (name, e))
        return None

    schema = read_json(os.path.join(SCHEMA_DIR, 'city.schema.json'))
    try:
        import jsonschema
    except ImportError:
        check(True, '%s: city.json parses (jsonschema absent - shape NOT validated)'
              % name, note=True)
    else:
        schema.pop('$id', None)
        errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(doc),
                        key=lambda e: list(e.path))
        for e in errors[:10]:
            check(False, '%s: city.json %s: %s'
                  % (name, '/'.join(str(p) for p in e.path) or '(root)', e.message))
        check(not errors, '%s: city.json satisfies city.schema.json' % name)

    check(doc.get('id') == name,
          '%s: city.json id matches its directory name (got %r)' % (name, doc.get('id')))

    # The boundary must be DERIVED. A descriptor that smuggles a rectangle in as
    # a selector defeats the one constraint this schema exists to impose.
    for sel in doc.get('boundary', {}).get('selector', []):
        check(not re.match(r'^-?\d+(\.\d+)?$', str(sel).strip()),
              '%s: boundary selector %r names a feature, not a coordinate' % (name, sel))
    return doc


def check_fields(city_dir, name, doc):
    """Every required key is declared, with the right units and value type."""
    required = read_json(os.path.join(SCHEMA_DIR, 'required_fields.json'))['fields']
    try:
        fields, _origin = registry.load_registry(os.path.join(city_dir, 'registry'))
    except registry.RegistryError as e:
        check(False, '%s: registry loads (%s)' % (name, e))
        return
    missing = sorted(set(required) - set(fields))
    extra = sorted(set(fields) - set(required))
    for k in missing[:15]:
        check(False, '%s: required field not declared: %s (%s)'
              % (name, k, required[k]['units']))
    check(not missing, '%s: all %d required fields declared' % (name, len(required)))
    if extra:
        check(True, '%s: %d field(s) declared beyond the contract - regenerate '
                    'required_fields.json if they are meant to be required: %s'
              % (name, len(extra), ', '.join(extra[:5])), note=True)

    bad_units = [k for k in sorted(set(required) & set(fields))
                 if fields[k].get('units') != required[k]['units']]
    for k in bad_units[:10]:
        check(False, '%s: %s declared in %r, contract says %r'
              % (name, k, fields[k].get('units'), required[k]['units']))
    check(not bad_units, '%s: every field carries its contracted units' % name)

    # the registry's own rules: a swept source must carry a sweep
    errors = registry.validate(fields)
    for e in errors[:10]:
        check(False, '%s: %s' % (name, e))
    check(not errors, '%s: every field satisfies field.schema.json' % name)

    # the descriptor and the registry must agree where they overlap
    if doc:
        modes = fields.get('RUN.mode_choice.modes', {}).get('value')
        check(modes is None or sorted(doc.get('modes', [])) == sorted(modes),
              '%s: city.json modes match RUN.mode_choice.modes (%s vs %s)'
              % (name, doc.get('modes'), modes))
        seed = fields.get('B.population.seed', {}).get('value')
        check(seed is None or doc.get('seed') == seed,
              '%s: city.json seed matches B.population.seed (%s vs %s)'
              % (name, doc.get('seed'), seed))
        for f in doc.get('unobtained', []):
            key = f.get('field')
            if key and key in fields:
                check(fields[key].get('value') is None,
                      '%s: %s is declared unobtained and carries NO point value'
                      % (name, key))


def check_overlays(city_dir, name, doc):
    """Every scenario and day type the descriptor names has an overlay to resolve."""
    base = os.path.join(city_dir, 'overlays')
    for sub in ('scenarios', 'day', 'runs'):
        check(os.path.isdir(os.path.join(base, sub)),
              '%s: overlays/%s/ present' % (name, sub))
    if not doc:
        return
    for s in (doc.get('intervention') or {}).get('scenarios', []):
        check(os.path.exists(os.path.join(base, 'scenarios', '%s.json' % s)),
              '%s: scenario %s has an overlay' % (name, s))
    for d in doc.get('day_types', []):
        check(os.path.exists(os.path.join(base, 'day', '%s.json' % d)),
              '%s: day type %s has an overlay' % (name, d))


def check_layers(city_dir, name):
    """Which contracted artefacts this city actually has.

    Absence is reported, not failed: a city part-way through its build is a
    normal state, and this repository's own OSM layers are absent by design
    until a re-harvest. What matters is that the list is explicit.
    """
    layers = read_json(os.path.join(SCHEMA_DIR, 'layers.json'))['artefacts']
    concrete = {p: a for p, a in layers.items() if a['kind'] != 'pattern'}
    absent = sorted(p for p in concrete
                    if not os.path.exists(os.path.join(city_dir, p)))
    check(True, '%s: %d of %d contracted artefacts present'
          % (name, len(concrete) - len(absent), len(concrete)), note=True)
    for p in absent[:12]:
        check(True, '%s:   absent - %s (read by %s)'
              % (name, p, ', '.join(concrete[p]['read_by'][:2])), note=True)
    if len(absent) > 12:
        check(True, '%s:   ... and %d more' % (name, len(absent) - 12), note=True)


def check_framework_is_city_free(name, doc):
    """A framework that names one city is not a framework."""
    if not doc:
        return
    tokens = {name.lower()}
    for sel in doc.get('boundary', {}).get('selector', []):
        tokens.add(str(sel).split()[0].lower())
    tokens = {t for t in tokens if len(t) > 4}
    pattern = re.compile('|'.join(re.escape(t) for t in sorted(tokens)), re.I)

    hits = []
    for root in FRAMEWORK_ROOTS:
        for dirpath, dirs, names in os.walk(os.path.join(REPO, root)):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for n in sorted(names):
                if not n.endswith(('.py', '.json', '.java')):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, n), REPO)
                rel = rel.replace(os.sep, '/')
                if rel in FRAMEWORK_SKIP:
                    continue
                try:
                    text = io.open(os.path.join(dirpath, n), encoding='utf-8',
                                   errors='replace').read()
                except OSError:
                    continue
                for i, line in enumerate(text.splitlines(), 1):
                    if pattern.search(line):
                        hits.append((rel, i, line.strip()[:90]))
    check(True, '%s: %d place-name occurrence(s) in the framework '
                '(src/, tests/, config/schema/)' % (name, len(hits)), note=True)
    for rel, i, line in hits[:15]:
        check(True, '  %s:%d  %s' % (rel, i, line), note=True)
    if len(hits) > 15:
        check(True, '  ... and %d more' % (len(hits) - 15), note=True)


# --------------------------------------------------------------------------
CITY_DIRS = ('data', 'networks', 'schedules', 'demand', 'scenarios', 'params',
             'registry', 'overlays', 'geometry')


def check_no_cwd_relative_output(name):
    """No script may name a city directory as a bare working-directory path.

    `OUT = 'schedules'` is not a city path - it is whatever directory the script
    happens to be run from. Four of these survived the migration because they
    carried no trailing slash and so did not look like paths at all; one of them
    wrote 32 MB of rebuilt GTFS into the repository root, beside the city that
    should have received it. The failure is silent: the script succeeds, the
    manifest still passes, and the outputs are simply somewhere else.
    """
    bad = []
    # Narrow deliberately: only a bare NAME = 'dir' assignment, which is a path
    # relative to the working directory. `os.path.join(ROOT, 'data', ...)` is
    # anchored on a resolved root and is correct.
    pattern = re.compile(r"^\s*[A-Za-z_][A-Za-z_0-9]*\s*=\s*['\"](%s)['\"]\s*(;|$)"
                         % '|'.join(CITY_DIRS))
    for root in ('src', 'tests', os.path.join('cities', name)):
        for dirpath, dirs, names in os.walk(os.path.join(REPO, root)):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for n in sorted(names):
                if not n.endswith('.py'):
                    continue
                p = os.path.join(dirpath, n)
                rel_p = os.path.relpath(p, REPO).replace(os.sep, '/')
                for i, line in enumerate(io.open(p, encoding='utf-8',
                                                 errors='replace').read().splitlines(), 1):
                    for part in line.split(';'):
                        if pattern.match(part.strip() and part or line):
                            bad.append('%s:%d  %s' % (rel_p, i, line.strip()[:80]))
                            break
    for b in bad[:10]:
        check(False, '%s: working-directory path where a city path belongs - %s'
              % (name, b))
    check(not bad, '%s: no script names a city directory relative to the '
                   'working directory' % name)


def check_city(name):
    city_dir = os.path.join(citymod.CITIES_DIR, name)
    print('\n=== %s (%s) ===' % (name, city_dir))
    if not check(os.path.isdir(city_dir), '%s: directory present' % name):
        return
    missing = [d for d in citymod.LAYERS
               if not os.path.isdir(os.path.join(city_dir, d))]
    for d in missing:
        check(False, '%s: missing directory %s/' % (name, d))
    check(not missing, '%s: every expected subdirectory present' % name)

    doc = check_descriptor(city_dir, name)
    check_fields(city_dir, name, doc)
    check_overlays(city_dir, name, doc)
    check_layers(city_dir, name)
    check_no_cwd_relative_output(name)
    check_framework_is_city_free(name, doc)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--city', help='default: the selected city')
    ap.add_argument('--all', action='store_true', help='check every city present')
    a = ap.parse_args()

    names = citymod.available() if a.all else [a.city or citymod.CITY]
    if not names:
        print('no cities found under %s' % citymod.CITIES_DIR)
        return 1
    for n in names:
        check_city(n)
    print('\nPASS %d   FAIL %d   note %d'
          % (_state['pass'], _state['fail'], _state['note']))
    return 1 if _state['fail'] else 0


if __name__ == '__main__':
    sys.exit(main())
