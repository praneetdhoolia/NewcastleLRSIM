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

# Names that are plumbing by construction: a path, a column list, a regex, an
# encoding. Declared here rather than in the checker so the scanner and the
# audit that reads it cannot disagree about what counts as a value.
IGNORE_SUFFIX = ('_FILE', '_DIR', '_PATH', '_RE', '_COLS', '_COLUMNS', '_URL',
                 '_HEADER', '_ENCODING', '_SEP', '_EPOCH', '_EXT')

# How many numbers a container must carry before it is reported as a table
# rather than as incidental structure. Two is a pair of bounds; four is a table
# somebody typed.
CONTAINER_MIN_NUMBERS = 4


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


def scan_decisions(path):
    """Every value DECIDED in one module, in each of the five forms it takes.

    `scan_file` answers a narrower question - "what is this named module-level
    constant worth?" - because it was written to pin a `legacy_symbol` to the
    literal it replaced. A value that decides something does not have to be a
    named module-level scalar, and in this repository most of them are not:

      constant       MODULE_LEVEL = 1.3        what `scan_file` already finds
      table          MODULE_LEVEL = [...]      a container carrying numbers
      unpacked       ACCEL, DECEL = 1.2, 1.3   invisible to a single-target scan
      kwarg_default  def f(speed_kmh=28.0)     a scenario spec in a signature
      cli_default    add_argument(default=100) a value the registry declares
                                               UNOBTAINED, supplied anyway

    The last three are the forms that carried this project's scenario
    definitions - the S1 shuttle's speed and dwell, two vehicles' acceleration,
    and the iteration count - past an audit that only looked at the first two.

    Returns a list of records; `kind` is `classify`'s verdict, so a caller can
    keep `parameter` and drop `path`/`pattern`/`structure` exactly as the
    one-time migration did. Numbers are counted rather than transcribed for a
    container, because a 144-number departure profile is one decision to report,
    not 144.
    """
    with io.open(path, encoding='utf-8') as f:
        tree = ast.parse(f.read(), filename=path)

    def rec(form, name, value, line, n=1):
        # A container that carries numbers is a table of decisions whatever else
        # it also carries. `classify` calls a list of (name, lat, lon) tuples
        # `structure`, which is right for a vocabulary and wrong for the eight
        # stop positions of a scenario alignment - so the entry condition, not
        # the shape, decides here.
        kind = 'parameter' if form == 'table' else classify(value)
        return dict(form=form, name=name, value=value, line=line,
                    kind=kind, n_numbers=n)

    out = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            # ACCEL, DECEL = 1.2, 1.3 - one Tuple target, not one Name, so a
            # single-target scan drops it entirely.
            if isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple):
                for nm, val in zip(target.elts, node.value.elts):
                    if not isinstance(nm, ast.Name) or not nm.id.isupper():
                        continue
                    v = literal(val)
                    if numeric(v):
                        out.append(rec('unpacked', nm.id, v, node.lineno))
                continue
            if not isinstance(target, ast.Name):
                continue
            name = target.id
            if not name.isupper() or name.startswith('_') \
                    or name.endswith(IGNORE_SUFFIX):
                continue
            value = literal(node.value)
            if numeric(value):
                out.append(rec('constant', name, value, node.lineno))
            elif count_numbers(value) >= CONTAINER_MIN_NUMBERS:
                out.append(rec('table', name, value, node.lineno,
                               count_numbers(value)))

    for node in ast.walk(tree):
        # def make_bus_shuttle(..., speed_kmh=28.0, dwell_s=15.0)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args.args + node.args.kwonlyargs
            defaults = list(node.args.defaults) + [d for d in node.args.kw_defaults
                                                   if d is not None]
            named = args[len(node.args.args) - len(node.args.defaults):]
            for arg, default in zip(named + node.args.kwonlyargs, defaults):
                v = literal(default)
                if numeric(v):
                    out.append(rec('kwarg_default',
                                   '%s(%s)' % (node.name, arg.arg), v, node.lineno))
        # ap.add_argument('--iterations', type=int, default=100)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == 'add_argument':
            flag = next((a.value for a in node.args
                         if isinstance(a, ast.Constant) and isinstance(a.value, str)),
                        '?')
            for kw in node.keywords:
                if kw.arg != 'default':
                    continue
                v = literal(kw.value)
                if numeric(v):
                    out.append(rec('cli_default', flag, v, node.lineno))
    return sorted(out, key=lambda r: (r['line'], r['name']))


def count_numbers(value):
    """How many numbers a literal container carries, at any depth."""
    if numeric(value):
        return 1
    if isinstance(value, dict):
        return sum(count_numbers(v) for v in value.values())
    if isinstance(value, (list, tuple, set)):
        return sum(count_numbers(v) for v in value)
    return 0


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
