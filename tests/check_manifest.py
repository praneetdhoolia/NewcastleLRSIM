#!/usr/bin/env python
"""Verify committed data files against data/MANIFEST.csv.

Offline, dependency-free counterpart to tests/check_package.py. The bulk of the
package is gitignored (see .gitignore), so a CI checkout holds only a subset of
the manifest; this checks exactly that subset:

  1. every manifest row whose file is present hashes to its recorded sha256 and
     matches its recorded byte count;
  2. every tracked file under data/processed appears in the manifest.

Absent files are reported and skipped, not failed — that is the normal state of a
fresh clone. Run tests/check_package.py locally, against the full package, for the
cross-layer integrity checks that need the bulk data.

Exits non-zero on any mismatch or unmanifested tracked file.
"""
import csv
import hashlib
import os
import subprocess
import sys

MANIFEST = 'data/MANIFEST.csv'
CHUNK = 1 << 20


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(CHUNK), b''):
            h.update(block)
    return h.hexdigest()


def norm(path):
    return path.replace(os.sep, '/')


def tracked_files():
    out = subprocess.run(['git', 'ls-files', '-z', 'data/processed'],
                         capture_output=True, text=True, check=True).stdout
    return {norm(p) for p in out.split(chr(0)) if p}


def main():
    if not os.path.exists(MANIFEST):
        print('FAIL  %s not found' % MANIFEST)
        return 1

    checked = absent = unhashed = 0
    failures = []
    manifested = set()

    with open(MANIFEST, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            path = norm(row['path'])
            manifested.add(path)
            if not os.path.exists(path):
                absent += 1
                continue
            checked += 1
            # build_manifest.py records a sentinel (e.g. `skipped_large`) instead of a
            # digest for files it declined to hash; size is still authoritative there.
            recorded = (row['sha256'] or '').strip()
            if len(recorded) == 64 and all(c in '0123456789abcdef' for c in recorded):
                actual = sha256(path)
                if actual != recorded:
                    failures.append('%s: sha256 %s, manifest says %s'
                                    % (path, actual[:16], recorded[:16]))
                    continue
            else:
                unhashed += 1
            if row['bytes']:
                size = os.path.getsize(path)
                if size != int(row['bytes']):
                    failures.append('%s: %d bytes, manifest says %s'
                                    % (path, size, row['bytes']))

    for path in sorted(tracked_files() - manifested):
        failures.append('%s: tracked but absent from %s' % (path, MANIFEST))

    print('verified %d present file(s) (%d size-only, no digest recorded); '
          '%d manifest entr(ies) not in this checkout (gitignored bulk data)'
          % (checked, unhashed, absent))
    for line in failures:
        print('FAIL  ' + line)
    if failures:
        print('\n%d failure(s)' % len(failures))
        return 1
    print('OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
