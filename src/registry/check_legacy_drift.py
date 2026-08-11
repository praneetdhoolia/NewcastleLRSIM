#!/usr/bin/env python
"""Assert that a registry field and the constant it replaced still agree.

The build layer HAS been migrated and this check is now nearly empty, which is
the point: every migrated script reads the registry, so its duplicate constant
was deleted with the `legacy_symbol` that pinned it. What remains is whatever
still holds its own copy of a declared value. Two copies of a number is exactly
the drift this package cannot absorb, so any that survive are pinned by test
until they are migrated too.

Every field carrying `legacy_symbol: "path/to/file.py:SYMBOL"` is compared with
the literal actually assigned in that file. A mismatch is a failure, not a
warning: it means the registry documents one value and the model runs another.

This check becomes unnecessary the moment a script reads the registry instead,
and the `legacy_symbol` key is removed with the constant.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))

import registry                                   # noqa: E402
from registry import extract_legacy_constants as legacy   # noqa: E402

# Fields whose registry value is deliberately NOT the legacy literal, with the
# reason. Each one is a value the project decided to change; the constant is
# still in the source only because that script has not been migrated.
EXPECTED_DIVERGENCE = {
    'B.activity.detour_factor': (
        'the build script keeps 1.30 as a fallback labelled "assumed - C2 factors file '
        'not found"; the registry carries the MEASURED 1.3376 that C2 supplies at load '
        '(DECISIONS.md 9.2)'),
    'A.lightrail.dwell_charging_s': (
        'the registry declares this UNOBTAINED with no point value; the build script '
        'literal 20.0 is the baseline sweep point, which now lives in the scenario '
        'overlays (DECISIONS.md 0, 4.3)'),
}


def parse_symbol(spec):
    path, _, name = spec.rpartition(':')
    return path, name


def compare(fields, verbose=False):
    problems, checked, diverged, skipped = [], 0, 0, 0
    for key in sorted(fields):
        spec = fields[key].get('legacy_symbol')
        if not spec:
            continue
        rel, name = parse_symbol(spec)
        path = os.path.join(REPO, rel.replace('/', os.sep))
        if not os.path.exists(path):
            problems.append('%s: legacy_symbol points at %s, which does not exist'
                            % (key, rel))
            continue
        found = legacy.scan_file(path)
        if name not in found:
            problems.append('%s: %s is no longer defined in %s - if it was migrated, '
                            'drop legacy_symbol from the registry field' % (key, name, rel))
            continue
        code_value = found[name]['value']
        reg_value = fields[key].get('value')
        if code_value is Ellipsis:
            # the constant is an expression (e.g. 30 * 3600), not a literal, so
            # there is nothing to compare by value. Recorded, not silently passed.
            skipped += 1
            if verbose:
                print('  not a literal        %-42s %s:%s' % (key, rel, name))
            continue
        checked += 1
        if key in EXPECTED_DIVERGENCE:
            diverged += 1
            if verbose:
                print('  diverges (expected)  %-42s %s' % (key, EXPECTED_DIVERGENCE[key][:60]))
            continue
        if not values_agree(reg_value, code_value):
            problems.append(
                '%s: registry says %r, %s:%s says %r. Two copies of a number have '
                'drifted - fix the registry or the constant, and if the difference is '
                'deliberate record it in EXPECTED_DIVERGENCE with a reason.'
                % (key, reg_value, rel, name, code_value))
        elif verbose:
            print('  agrees               %-42s %r' % (key, reg_value))
    return problems, checked, diverged, skipped


def values_agree(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        # the registry may declare a documented subset of a larger code table
        return all(values_agree(v, b.get(k)) for k, v in a.items() if k in b) and \
            bool(set(a) & set(b))
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(values_agree(x, y) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        try:
            return abs(float(a) - float(b)) < 1e-9
        except (TypeError, ValueError):
            return a == b
    return a == b


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--verbose', action='store_true')
    a = ap.parse_args()
    fields, _ = registry.load_registry()
    problems, checked, diverged, skipped = compare(fields, a.verbose)
    print('%d registry field(s) compared with the constant they replaced; '
          '%d deliberately diverge, %d are expressions rather than literals'
          % (checked, diverged, skipped))
    if problems:
        print('\nFAIL %d' % len(problems))
        for p in problems:
            print('  %s' % p)
        raise SystemExit(1)
    print('registry and source constants agree')


if __name__ == '__main__':
    main()
