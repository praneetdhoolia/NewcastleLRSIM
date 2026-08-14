#!/usr/bin/env python
"""Generate the portable half of the input contract from the reference city.

    python src/registry/render_schema.py            regenerate
    python src/registry/render_schema.py --check    fail if stale

`config/schema/` already said what shape ANY field must be in. It did not say
WHICH fields a city must supply, or which artefacts it must produce - so a city
directory that was half-populated resolved cleanly and failed later, one
`get()` at a time, several hundred lines into a build. These two documents close
that:

    required_fields.json   every field key a city must declare, its units, its
                           value type, and whether it must carry a sweep
    layers.json            every city-relative artefact the FRAMEWORK reads,
                           and the columns the reference city's copy carries

Both are GENERATED, never hand-edited, for the reason CONFIG_REFERENCE.md is:
a hand-kept mirror of the registry drifts, and this repository has already been
bitten by exactly that - `params/C1` was a hand-kept copy of 26 registry values
that reached nothing.

**What `required` means here, stated honestly.** It means the reference city
declares the field and the framework will not run without it. It does NOT mean
every city in the world must have it: a city with no light rail has no use for
`A.lightrail.dwell_fixed_s`. Narrowing the set to what each layer of the model
genuinely needs is real work and is not done - so the contract today is *match
the reference city's field set, and justify any omission*. That is a weaker
claim than it looks, and saying so is the point.

`layers.json` is derived by a different and stronger route: it lists the
artefacts the framework's own source ASKS FOR, found by reading every
`city.path(...)` call under `src/`, rather than by listing what one city
happens to contain.
"""
import argparse
import ast
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))

import city as _city                                          # noqa: E402
sys.path.insert(0, HERE)
import registry                                               # noqa: E402

SCHEMA_DIR = os.path.join(REPO, 'config', 'schema')
FIELDS_OUT = os.path.join(SCHEMA_DIR, 'required_fields.json')
LAYERS_OUT = os.path.join(SCHEMA_DIR, 'layers.json')

# `source` values that field.schema.json obliges to carry a sweep, a held-fixed
# rule or a derived-from identity. Kept in one place so the two documents cannot
# disagree about it.
SWEPT_SOURCES = registry.SWEPT_SOURCES

TYPES = {bool: 'boolean', int: 'number', float: 'number', str: 'string',
         list: 'array', dict: 'object', type(None): 'null'}


# --------------------------------------------------------------------------
# required_fields.json
# --------------------------------------------------------------------------
def build_fields():
    fields, origin = registry.load_registry()
    out = {}
    for key in sorted(fields):
        f = fields[key]
        value = f.get('value')
        out[key] = {
            'layer': key.split('.')[0],
            'units': f.get('units'),
            'type': TYPES.get(type(value), 'unknown'),
            'source_in_reference_city': f.get('source'),
            'sweep_required': f.get('source') in SWEPT_SOURCES,
            'unobtained_in_reference_city': f.get('status') == 'unobtained',
            'declared_in': origin[key].split('/')[-1],
        }
    by_layer = {}
    for key, spec in out.items():
        by_layer[spec['layer']] = by_layer.get(spec['layer'], 0) + 1
    return {
        'generated_by': 'src/registry/render_schema.py',
        'generated_from': 'cities/%s/registry' % _city.CITY,
        'contract': ('Every key below must be declared by any city, with the stated '
                     'units and value type. A field whose source is measured, derived, '
                     'literature or assumed MUST additionally carry a sweep, a '
                     'held_fixed rule or a derived_from identity - field.schema.json '
                     'enforces that, and check_city.py tests it.'),
        'no_prose': ("Field DESCRIPTIONS are deliberately absent. They are the "
                     "reference city's own wording and would put one city's prose - its "
                     "suburbs, its agencies, its datasets - inside the portable half of "
                     "the contract. What a city must supply is a key, its units and its "
                     "value type; WHY a particular city chose a particular value belongs "
                     "in that city's docs/reference/CONFIG_REFERENCE.md."),
        'caveat': ('`required` means the reference city declares it and the framework '
                   'will not run without it. It does NOT mean every city needs it: an '
                   'intervention-specific field is meaningless to a city without that '
                   'intervention. Narrowing this set per model layer is not done.'),
        'n_fields': len(out),
        'n_by_layer': dict(sorted(by_layer.items())),
        'fields': out,
    }


# --------------------------------------------------------------------------
# layers.json
# --------------------------------------------------------------------------
def framework_paths():
    """Every city-relative artefact the FRAMEWORK asks for, read from its source.

    Finds `city.path('...')` / `_city.path('...')` calls under src/ and tests/.
    A path built at run time from a variable cannot be seen this way and is not
    claimed to be - the count of unresolvable calls is reported rather than
    silently dropped.
    """
    found, dynamic = {}, 0
    for root in ('src', 'tests'):
        for dirpath, dirs, names in os.walk(os.path.join(REPO, root)):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for n in sorted(names):
                if not n.endswith('.py'):
                    continue
                full = os.path.join(dirpath, n)
                rel_src = os.path.relpath(full, REPO).replace(os.sep, '/')
                try:
                    tree = ast.parse(io.open(full, encoding='utf-8').read())
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue
                    fn = node.func
                    if not (isinstance(fn, ast.Attribute) and fn.attr == 'path'
                            and isinstance(fn.value, ast.Name)
                            and fn.value.id in ('city', '_city')):
                        continue
                    parts = []
                    for arg in node.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            parts.append(arg.value)
                        else:
                            parts = None
                            break
                    if parts is None:
                        dynamic += 1
                        continue
                    p = '/'.join(parts)
                    found.setdefault(p, set()).add(rel_src)
    return found, dynamic


def columns_of(rel_path):
    """The header of the reference city's copy, if it has one and it is tabular."""
    full = _city.path(rel_path)
    if not os.path.isfile(full) or not rel_path.endswith('.csv'):
        return None
    try:
        with io.open(full, encoding='utf-8', errors='replace') as f:
            head = f.readline().strip()
    except OSError:
        return None
    if not head:
        return None
    return [c.strip().lstrip('﻿') for c in head.split(',')]


def build_layers():
    found, dynamic = framework_paths()
    artefacts = {}
    for rel_path in sorted(found):
        if any(ch in rel_path for ch in '*?%'):
            kind = 'pattern'
        elif os.path.isdir(_city.path(rel_path)):
            kind = 'directory'
        else:
            kind = 'file'
        entry = {
            'kind': kind,
            'read_by': sorted(found[rel_path]),
            'present_in_reference_city': os.path.exists(_city.path(rel_path)),
        }
        cols = columns_of(rel_path)
        if cols:
            entry['columns_in_reference_city'] = cols
        artefacts[rel_path] = entry
    return {
        'generated_by': 'src/registry/render_schema.py',
        'generated_from': 'static reads of city.path(...) under src/ and tests/',
        'contract': ('A city must produce every artefact below, at the same '
                     'city-relative path, before the framework can run against it. '
                     'The producing script may be entirely different - that is what a '
                     'jurisdiction adapter is for - but the path and the columns the '
                     'framework reads are the contract.'),
        'caveat': ('`columns_in_reference_city` is the header of the reference '
                   'city\'s own copy, not '
                   'a proven minimum: a column here may be incidental. Narrowing it to '
                   'the columns framework code actually reads is not done.'),
        'n_artefacts': len(artefacts),
        'n_present_in_reference_city': sum(1 for a in artefacts.values()
                                           if a['present_in_reference_city']),
        'n_paths_built_at_runtime': dynamic,
        'artefacts': artefacts,
    }


# --------------------------------------------------------------------------
def write(path, doc, check):
    text = json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=False) + '\n'
    if check:
        if not os.path.exists(path):
            print('%s is MISSING - regenerate with '
                  'python src/registry/render_schema.py' % path)
            return 1
        current = io.open(path, encoding='utf-8').read()
        if current != text:
            print('%s is stale - regenerate with '
                  'python src/registry/render_schema.py' % path)
            return 1
        print('%s is current' % os.path.basename(path))
        return 0
    with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true',
                    help='exit non-zero if either document has drifted')
    a = ap.parse_args()

    fields, layers = build_fields(), build_layers()
    rc = write(FIELDS_OUT, fields, a.check) | write(LAYERS_OUT, layers, a.check)
    if not a.check:
        print('required_fields.json: %d fields (%s)'
              % (fields['n_fields'],
                 ', '.join('%s %d' % kv for kv in fields['n_by_layer'].items())))
        print('layers.json: %d artefacts, %d present in the reference city, '
              '%d path(s) built at run time and therefore not listed'
              % (layers['n_artefacts'], layers['n_present_in_reference_city'],
                 layers['n_paths_built_at_runtime']))
    return rc


if __name__ == '__main__':
    sys.exit(main())
