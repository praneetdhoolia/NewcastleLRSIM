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

REPO = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

TEXT_EXT = {'.csv', '.json', '.txt', '.md', '.py', '.html', '.yml', '.yaml',
            '.jsonl', '.cfg', '.ini', '.sh'}
BINARY_EXT = {'.zip', '.tif', '.tiff', '.pdf', '.xlsx', '.xls', '.gpkg', '.pbf',
              '.png', '.jpg', '.jpeg', '.osm'}
# Two trees, because the repository holds a framework and one city's instance of
# it. Paths in CITY_* are relative to cities/<city>/; paths in REPO_* to the root.
REPO_ROOTS = ['docs', 'src', 'tests', 'config', '.githooks', '.claude', '.github']
CITY_ROOTS = ['data/processed', 'params', 'scenarios', 'demand', 'extract', 'build',
              'geometry',
              'overlays', 'registry']
# P2 build outputs: the reports are committed, so they are hashed over LF bytes
# like everything else. The XML networks under them are gitignored bulk.
CITY_ROOTS += ['networks/matsim', 'networks/sumo']
# DECISIONS.md, STATUS.md and CLAUDE.md are deliberately absent: they live under
# docs/ and .claude/, both already walked by REPO_ROOTS. README.md and run.py are
# the only files left at the repo root, so they are the only ones named here.
REPO_SINGLE = ['README.md', 'run.py', '.gitignore', '.gitattributes']
CITY_SINGLE = ['data/raw/provenance_open_data.json', 'data/raw/provenance_abs_dem.json',
               'data/raw/_s3_historical_gtfs_listing.txt', 'data/raw/_osm_fetch.log',
               'schedules/provenance.json', 'schedules/raw/provenance.json',
               'schedules/era_build_summary.json',
               'schedules/_era1_reconstruction_report.json',
               'schedules/scenarios/_scenario_schedule_report.json',
               'data/MANIFEST.csv', 'data/MANIFEST.json']

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', 'src'))
import city as _city  # noqa: E402

ROOTS = [os.path.join(REPO, r) for r in REPO_ROOTS] +         [_city.path(r) for r in CITY_ROOTS]
SINGLE = [os.path.join(REPO, s) for s in REPO_SINGLE] +          [_city.path(s) for s in CITY_SINGLE]


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
