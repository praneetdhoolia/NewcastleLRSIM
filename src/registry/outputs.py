#!/usr/bin/env python
"""The output contract: validate what the model writes, not only what it reads.

Inputs and outputs are declared to the same standard. `config/schema/outputs/`
holds a JSON Schema per artefact the pipeline produces, and this module checks a
document against its schema at write time, so a malformed result fails where it
is produced rather than three steps downstream in a table nobody re-derives.

Two rules are enforced here rather than left to the schema, because they are
about meaning rather than shape:

  * a fit block must NAME the target ids it was computed over. A statistic that
    does not name its targets is not reportable - "fits 67 targets" is a much
    stronger claim than DECISIONS.md 12.1 says the data supports.
  * scored + unscorable must reconcile to the number of calibration targets
    available. Every target is either scored or explained.

jsonschema is optional: CI installs nothing, so the structural rules run
everywhere and the full schema check runs where the library is present.
"""
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
OUTPUT_SCHEMA_DIR = os.path.join(REPO, 'config', 'schema', 'outputs')

KINDS = {
    'run': 'run.schema.json',
    'metrics': 'metrics.schema.json',
    'fit': 'fit.schema.json',
    'config': 'config_snapshot.schema.json',
    'summary': 'summary.schema.json',
}
FILENAMES = {'_run.json': 'run', '_metrics.json': 'metrics',
             '_fit.json': 'fit', '_config.json': 'config',
             '_summary.json': 'summary'}


class OutputError(Exception):
    """An output document does not meet its declared contract."""


def kind_of(path):
    """Infer the artefact kind from the filename, or None."""
    return FILENAMES.get(os.path.basename(path))


def _schema(kind):
    try:
        name = KINDS[kind]
    except KeyError:
        raise OutputError('no output contract for kind %r' % kind)
    with io.open(os.path.join(OUTPUT_SCHEMA_DIR, name), encoding='utf-8') as f:
        return json.load(f)


def _semantic_errors(kind, doc):
    """The rules that are about meaning, not shape."""
    errors = []
    if kind == 'fit':
        for block in ('mode_share', 'patronage', 'counts'):
            b = doc.get(block)
            if not isinstance(b, dict):
                continue
            if 'targets' not in b:
                errors.append('%s: no target ids. A fit statistic that does not name the '
                              'targets it was computed over is not reportable '
                              '(DECISIONS.md 12.1).' % block)
                continue
            if b.get('n') is not None and len(b['targets']) != b['n']:
                errors.append('%s: n=%s but %d target ids listed - they must agree.'
                              % (block, b['n'], len(b['targets'])))
        available = doc.get('calibration_targets_available')
        scored = doc.get('scored')
        unscorable = doc.get('unscorable')
        if None not in (available, scored) and isinstance(unscorable, list):
            if scored + len(unscorable) != available:
                errors.append('reconciliation failed: %d scored + %d explained != %d '
                              'calibration targets. Every target must be one or the other.'
                              % (scored, len(unscorable), available))
        for u in unscorable or []:
            if not u.get('reason'):
                errors.append('unscorable target %s carries no reason.'
                              % u.get('target_id', '?'))
    if kind == 'metrics':
        ms = doc.get('mode_share') or {}
        pct = ms.get('newcastle_lga_pct') or {}
        if pct:
            total = sum(pct.values())
            if abs(total - 100.0) > 0.5:
                errors.append('mode_share.newcastle_lga_pct sums to %.2f, not 100.' % total)
    if kind == 'run':
        if doc.get('rc') == 0 and not doc.get('config_snapshot'):
            errors.append('a completed run carries no config_snapshot: it cannot state what '
                          'inputs produced it.')
    return errors


def validate_doc(kind, doc):
    """Return a list of problems. Empty means the document meets its contract."""
    errors = _semantic_errors(kind, doc)
    try:
        import jsonschema
    except ImportError:
        return errors
    schema = _schema(kind)
    schema.pop('$id', None)
    validator = jsonschema.Draft202012Validator(schema)
    for e in sorted(validator.iter_errors(doc), key=lambda x: list(x.path)):
        where = '/'.join(str(p) for p in e.path) or '(root)'
        errors.append('%s: %s' % (where, e.message))
    return errors


def validate_file(path, kind=None):
    kind = kind or kind_of(path)
    if kind is None:
        raise OutputError('cannot infer an output kind from %s' % path)
    with io.open(path, encoding='utf-8') as f:
        return validate_doc(kind, json.load(f))


def write_checked(path, doc, kind=None):
    """Write an output document only if it meets its contract."""
    kind = kind or kind_of(path)
    problems = validate_doc(kind, doc)
    if problems:
        raise OutputError('%s does not meet the %s contract:\n  %s'
                          % (path, kind, '\n  '.join(problems)))
    with io.open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write('\n')
    return path


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--kind', choices=sorted(KINDS))
    a = ap.parse_args()
    bad = 0
    for p in a.paths:
        problems = validate_file(p, a.kind)
        if problems:
            bad += 1
            print('FAIL %s' % p)
            for x in problems:
                print('   ', x)
        else:
            print('OK   %s' % p)
    raise SystemExit(1 if bad else 0)


if __name__ == '__main__':
    main()
