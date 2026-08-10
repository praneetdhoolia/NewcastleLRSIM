#!/usr/bin/env python
"""Normalise generated text artefacts to LF.

The manifest digests must be computed over the same bytes CI checks out. See
.gitattributes: the repo pins eol=lf everywhere, so every generated text file is
rewritten to LF here before build_manifest.py hashes it.

Downloaded raw files are never touched - they are immutable (CLAUDE.md). Only files
this project generates are normalised, including the provenance and listing files
under data/raw/ that our own extract scripts wrote.
"""
import os
import sys

TEXT_EXT = {'.csv', '.json', '.txt', '.md', '.py', '.html', '.yml', '.yaml',
            '.jsonl', '.cfg', '.ini', '.sh'}
BINARY_EXT = {'.zip', '.tif', '.tiff', '.pdf', '.xlsx', '.xls', '.gpkg', '.pbf',
              '.png', '.jpg', '.jpeg', '.osm'}
ROOTS = ['data/processed', 'params', 'scenarios', 'demand', 'docs', 'src', 'tests',
         '.githooks', '.claude', '.github']
SINGLE = ['DECISIONS.md', 'README.md', 'STATUS.md', 'CLAUDE.md', '.gitignore',
          '.gitattributes', 'newcastle-lr-proposal.md',
          'data/raw/provenance_open_data.json', 'data/raw/provenance_abs_dem.json',
          'data/raw/_s3_historical_gtfs_listing.txt', 'data/raw/_osm_fetch.log',
          'schedules/provenance.json', 'schedules/raw/provenance.json',
          'schedules/era_build_summary.json', 'schedules/_era1_reconstruction_report.json',
          'schedules/scenarios/_scenario_schedule_report.json',
          'data/MANIFEST.csv', 'data/MANIFEST.json']


def candidates():
    for root in ROOTS:
        for dirpath, dirs, names in os.walk(root):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for n in names:
                ext = os.path.splitext(n)[1].lower()
                if ext in BINARY_EXT or (ext and ext not in TEXT_EXT):
                    continue
                yield os.path.join(dirpath, n)
    for p in SINGLE:
        if os.path.exists(p):
            yield p


def main():
    changed = skipped = 0
    for p in candidates():
        try:
            with open(p, 'rb') as f:
                b = f.read()
        except OSError:
            continue
        if b'\x00' in b[:8192]:          # looks binary, leave it
            skipped += 1
            continue
        n = b.replace(b'\r\n', b'\n')
        if n != b:
            with open(p, 'wb') as f:
                f.write(n)
            changed += 1
    print('normalised %d file(s) to LF; skipped %d binary-looking' % (changed, skipped))
    return 0


if __name__ == '__main__':
    sys.exit(main())
