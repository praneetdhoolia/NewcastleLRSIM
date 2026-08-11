#!/usr/bin/env python
"""One-time migration tool: inventory every module-level constant in `src/`.

This does not decide anything. It reads the scripts with `ast`, finds every
module-level assignment to an ALL_CAPS name whose right-hand side is a literal,
pairs each one with its `_SWEEP` and `_SOURCE` siblings where the repo already
has them, and classifies it so the registry can be authored from measurement
rather than from transcription.

Classification is deliberately conservative:

  parameter  numeric scalar, or a container of numerics - a model input
  structure  a container of strings, or a lone string that is not a path - a
             vocabulary the model is defined over, not a value to tune
  path       a filesystem path - plumbing, stays in code
  pattern    a regex - plumbing

Only `parameter` and `structure` belong in the registry. Run it again after the
migration: anything still classified `parameter` is a value that escaped.
"""
import argparse
import ast
import collections
import json
import io
import os

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..'))
SRC = os.path.join(REPO, 'src')
BS = chr(92)
PATH_HINTS = ('/', BS)
PATH_SUFFIXES = ('.csv', '.json', '.xml', '.gz', '.zip', '.py', '.md', '.txt',
                 '.xsd', '.dtd', '.jar', '.exe', '.sumocfg')
REGEX_HINTS = ('(?', '[^', '.*', BS + 'd', BS + 'w', BS + 's', BS + '.')
SIBLING_SUFFIXES = ('_SWEEP', '_SOURCE', '_RANGE', '_LOW', '_HIGH')


def literal(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError, TypeError):
        return Ellipsis


def numeric(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def all_numeric(v):
    if isinstance(v, dict):
        return bool(v) and all(all_numeric(x) for x in v.values())
    if isinstance(v, (list, tuple)):
        return bool(v) and all(all_numeric(x) for x in v)
    return numeric(v)


def classify(value):
    if value is Ellipsis:
        return 'unparsed'
    if isinstance(value, bool):
        return 'parameter'
    if isinstance(value, str):
        if any(h in value for h in PATH_HINTS) or value.endswith(PATH_SUFFIXES):
            return 'path'
        if any(h in value for h in REGEX_HINTS):
            return 'pattern'
        return 'structure'
    if all_numeric(value):
        return 'parameter'
    if isinstance(value, dict):
        vals = list(value.values())
        if vals and all(all_numeric(v) for v in vals):
            return 'parameter'
        if vals and all(isinstance(v, str) for v in vals):
            return 'structure'
        return 'mixed'
    if isinstance(value, (list, tuple, set)):
        return 'structure'
    if value is None:
        return 'structure'
    return 'other'


def scan_file(path):
    with io.open(path, encoding='utf-8') as f:
        tree = ast.parse(f.read(), filename=path)
    found = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        name = target.id
        if not name.isupper() or name.startswith('_'):
            continue
        value = literal(node.value)
        found[name] = dict(name=name, value=value, line=node.lineno,
                           kind=classify(value))
    for name, rec in list(found.items()):
        if any(name.endswith(s) for s in SIBLING_SUFFIXES):
            continue
        for suffix in ('_SWEEP', '_SOURCE'):
            sib = found.get(name + suffix)
            if sib is not None:
                rec[suffix.lower().lstrip('_')] = sib['value']
                sib['is_sibling_of'] = name
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out')
    ap.add_argument('--kind', action='append', default=[])
    a = ap.parse_args()

    inventory, counts = {}, collections.Counter()
    for sub in sorted(os.listdir(SRC)):
        d = os.path.join(SRC, sub)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith('.py'):
                continue
            rel = 'src/%s/%s' % (sub, fn)
            found = scan_file(os.path.join(d, fn))
            keep = {k: v for k, v in found.items()
                    if 'is_sibling_of' not in v
                    and (not a.kind or v['kind'] in a.kind)}
            if keep:
                inventory[rel] = keep
            for v in found.values():
                if 'is_sibling_of' not in v:
                    counts[v['kind']] += 1

    total = sum(counts.values())
    print('%d module-level constants across %d files' % (total, len(inventory)))
    for kind, n in counts.most_common():
        print('  %-10s %4d  %5.1f%%' % (kind, n, 100.0 * n / max(total, 1)))
    print('  %-10s %4d  already carry a _SWEEP sibling'
          % ('', sum(1 for f in inventory.values() for v in f.values() if 'sweep' in v)))

    if a.out:
        with io.open(a.out, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(inventory, f, indent=2, ensure_ascii=False, default=str,
                      sort_keys=True)
            f.write('\n')
        print('wrote %s' % a.out)


if __name__ == '__main__':
    main()
