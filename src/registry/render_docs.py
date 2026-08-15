#!/usr/bin/env python
"""Generate cities/<city>/docs/reference/CONFIG_REFERENCE.md from the registry.

The reference is GENERATED, never hand-written, so it cannot drift from the
values it documents. If a field changes, the documentation changes in the same
commit or `check_package.py` fails.

Regenerate with:

    python src/registry/render_docs.py

and run `python src/build/normalise_eol.py` afterwards if the manifest is being
rebuilt in the same change.
"""
import argparse
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))

import registry  # noqa: E402
import city as _city  # noqa: E402

# The reference documents ONE CITY's registry, so it belongs to that city.
OUT = _city.path('docs', 'reference', 'CONFIG_REFERENCE.md')

SOURCE_ORDER = ['observed', 'measured', 'derived', 'literature', 'assumed', 'definition']
SOURCE_GLOSS = {
    'observed': 'read directly from a raw download',
    'measured': 'computed from observed data in this package',
    'derived': 'follows from another registry field by identity',
    'literature': 'a published value, not specific to this city',
    'assumed': 'chosen without direct empirical support',
    'definition': 'fixed by the formulation, not an empirical quantity',
}
STATUS_GLOSS = {
    'active': 'usable point value',
    'unobtained': 'the datum does not exist in the package; must be swept, never pinned',
    'placeholder': 'a structural stand-in; the model runs but the field is not defensible',
    'computed': 'written at run time from other fields; do not hand-edit',
}


def fmt_value(v):
    if v is None:
        return '*(null - unobtained)*'
    if isinstance(v, bool):
        return '`%s`' % ('true' if v else 'false')
    if isinstance(v, (dict, list)):
        text = json.dumps(v, ensure_ascii=False)
        if len(text) > 110:
            text = text[:107] + '...'
        return '`%s`' % text
    return '`%s`' % v


def fmt_sweep(field):
    if 'held_fixed' in field:
        return '**held fixed**'
    if 'derived_from' in field:
        return 'derived: %s' % field['derived_from']['identity'][:70]
    s = field.get('sweep')
    if s is None:
        return '-'
    if isinstance(s, list):
        return '%g - %g' % (s[0], s[1])
    if 'interval' in s:
        return '%g - %g' % (s['interval'][0], s['interval'][1])
    if 'proportional' in s:
        return 'plus/minus %g%%' % (100 * s['proportional'])
    if 'categorical' in s:
        return ', '.join('`%s`' % x for x in s['categorical'])
    return '-'


def render(fields, origin):
    by_file = collections.defaultdict(dict)
    for key, f in fields.items():
        by_file[origin[key]][key] = f

    src_counts = collections.Counter(f['source'] for f in fields.values())
    st_counts = collections.Counter(f['status'] for f in fields.values())
    unobtained = sorted(k for k, f in fields.items() if f['status'] == 'unobtained')
    held = sorted(k for k, f in fields.items() if 'held_fixed' in f)

    L = []
    A = L.append
    A('# Configuration reference')
    A('')
    A('**Generated from `cities/<city>/registry/` by `src/registry/render_docs.py`. Do not edit '
      'by hand** - edit the registry and regenerate, or the two will disagree and '
      '`check_package.py` will say so.')
    A('')
    A('Every value the model consumes that is not read from an immutable raw download is '
      'declared here with its units, its provenance, and either a sweep range or an '
      'explicit rule holding it fixed. That is proposal 8.1 - *"every parameter chosen '
      'without direct empirical support must be recorded with its rationale and its sweep '
      'range"* - enforced as a schema constraint rather than a convention.')
    A('')
    A('## How to control any of it')
    A('')
    A('```bash')
    A('# a run overlay - the committed way to vary a run')
    A('cp cities/<city>/overlays/runs/example.json cities/<city>/overlays/runs/my_run.json')
    A('python src/run/run_matsim.py --scenario S2 --day WEEKDAY --run-config my_run')
    A('')
    A('# a one-off override, checked against the same rules')
    A('python src/run/run_matsim.py --scenario S2 --day WEEKDAY \\')
    A('    --set RUN.sample.fraction=0.10 --set RUN.controler.last_iteration=500')
    A('')
    A('# or from the environment')
    A('CITYSIM_RUN_SAMPLE_FRACTION=0.10 python src/run/run_matsim.py --scenario S2 ...')
    A('```')
    A('')
    A('Resolution order, lowest precedence first: `cities/<city>/registry/*.json` -> '
      '`overlays/scenarios/<S>.json` -> `overlays/day/<DAY>.json` -> `overlays/runs/<tag>.json` '
      '-> `CITYSIM_*` environment -> `--set`. The resolved snapshot is written into every '
      'run directory as `_config.json`, so a result always carries the exact inputs that '
      'produced it.')
    A('')
    A('Three things are refused at every layer:')
    A('')
    A('1. **An unobtained input cannot acquire a point value by being read.** `get()` raises; '
      'the caller must select a sweep member explicitly.')
    A('2. **An overlay cannot invent a field.** A key that is not already declared is rejected.')
    A('3. **A value cannot silently leave its sweep, and a held-fixed value cannot move at '
      'all.** Escaping a range requires `allow_outside_sweep` plus a written justification '
      'in a committed overlay - never a flag typed at a shell.')
    A('')
    A('## What the %d fields are made of' % len(fields))
    A('')
    A('| Provenance | Fields | Meaning |')
    A('|---|---:|---|')
    for s in SOURCE_ORDER:
        if src_counts.get(s):
            A('| `%s` | %d | %s |' % (s, src_counts[s], SOURCE_GLOSS[s]))
    A('')
    A('| Status | Fields | Meaning |')
    A('|---|---:|---|')
    for s in ['active', 'computed', 'placeholder', 'unobtained']:
        if st_counts.get(s):
            A('| `%s` | %d | %s |' % (s, st_counts[s], STATUS_GLOSS[s]))
    A('')
    A('### The %d fields with no value' % len(unobtained))
    A('')
    A('These carry `value: null` and the resolver refuses to return a point value for them. '
      'They are the project\'s honest edge: what it does not know, declared rather than '
      'guessed.')
    A('')
    A('| Field | Sweep | Why it has no value |')
    A('|---|---|---|')
    for k in unobtained:
        f = fields[k]
        why = f['description'].split('. ')
        why = (why[1] if len(why) > 1 else why[0])[:150]
        A('| `%s` | %s | %s |' % (k, fmt_sweep(f), why))
    A('')
    A('### The %d fields held fixed' % len(held))
    A('')
    A('Not tunable. DECISIONS.md 8.5 holds the mode constants fixed because calibrating them '
      'would fit away the effect under test - proposal 9 names ASC absorption as the primary '
      'threat to validity.')
    A('')
    for k in held:
        A('- `%s` - %s' % (k, fields[k]['held_fixed']['rule'][:180]))
    A('')

    for path in sorted(by_file):
        doc_fields = by_file[path]
        layer_doc = json.load(io.open(os.path.join(REPO, path), encoding='utf-8'))
        A('## %s' % layer_doc['title'])
        A('')
        A('*`%s` - %d fields*' % (path, len(doc_fields)))
        A('')
        A(layer_doc.get('description', ''))
        A('')
        A('| Field | Value | Units | Provenance | Sweep |')
        A('|---|---|---|---|---|')
        for key in sorted(doc_fields):
            f = doc_fields[key]
            A('| `%s` | %s | %s | `%s` | %s |'
              % (key, fmt_value(f.get('value')), f['units'], f['source'], fmt_sweep(f)))
        A('')
        for key in sorted(doc_fields):
            f = doc_fields[key]
            A('#### `%s`' % key)
            A('')
            A(f['description'])
            A('')
            bits = ['**%s**' % f['source'], 'status **%s**' % f['status']]
            if f.get('decisions_ref'):
                bits.append('DECISIONS.md §%s' % f['decisions_ref'])
            if f.get('proposal_ref'):
                bits.append('proposal §%s' % f['proposal_ref'])
            if f.get('legacy_symbol'):
                bits.append('was `%s`' % f['legacy_symbol'])
            if f.get('matsim_param'):
                bits.append('MATSim `%s`' % f['matsim_param'])
            A('*%s*' % ' · '.join(bits))
            A('')
            if f.get('sweep_basis'):
                A('> **Sweep basis.** %s' % f['sweep_basis'])
                A('')
            if 'held_fixed' in f:
                hf = f['held_fixed']
                A('> **Held fixed.** %s' % hf['rule'])
                A('>')
                A('> *Departure requires: %s*' % hf.get('departure_requires', 'a logged decision'))
                A('')
            if 'derived_from' in f:
                d = f['derived_from']
                A('> **Derived from** %s: %s'
                  % (', '.join('`%s`' % x for x in d['fields']), d['identity']))
                A('')
    return '\n'.join(L).rstrip() + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--check', action='store_true',
                    help='exit 1 if the file on disk differs from what would be generated')
    a = ap.parse_args()
    fields, origin = registry.load_registry()
    text = render(fields, origin)
    if a.check:
        if not os.path.exists(a.out):
            raise SystemExit('%s does not exist; run without --check' % a.out)
        current = io.open(a.out, encoding='utf-8', newline='').read().replace('\r\n', '\n')
        if current != text:
            raise SystemExit('%s is stale - regenerate with '
                             'python src/registry/render_docs.py' % a.out)
        print('%s is current (%d fields)' % (a.out, len(fields)))
        return
    with io.open(a.out, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    print('%s: %d fields, %d lines' % (a.out, len(fields), text.count('\n')))


if __name__ == '__main__':
    main()
