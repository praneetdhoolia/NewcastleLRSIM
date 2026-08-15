#!/usr/bin/env python
"""Reclaim a completed run's per-iteration scratch, keeping everything analysable.

A 250-iteration run at 10% leaves 8.7 GB behind, and **8.3 GB of it - 95% - is
`output/ITERS/`**, MATSim's per-iteration plans and events. Nothing in
`src/analyse/` or `src/calibrate/` reads that directory: the metric extraction,
the fit statistic and the run monitor read the final `output_*` files, the
`modestats.csv` trajectory and the log. So the bulk is intermediate, and keeping
it is what turns the calibration loop and the sweep into three quarters of a
terabyte.

What is kept is everything that lets a result be re-examined without re-running:
the final plans, events, trips, legs, links and network, the mode-share
trajectory, the log, and the four declared records. What is dropped can always
be recreated - a run is seeded and deterministic, so re-running reproduces it.

**It refuses to prune a run whose metrics have not been extracted.** Deleting an
intermediate before the thing that reads it has run is how a result becomes
unreproducible in practice rather than in principle, so the order is enforced
rather than remembered.

Every prune writes `_pruned.json` into the run directory recording what was
removed and how much it freed, so a pruned run is visibly pruned rather than
quietly incomplete.

Usage:
    python src/run/prune_run.py results/<run>            one run
    python src/run/prune_run.py --all                    every completed run
    python src/run/prune_run.py --all --dry-run          report, delete nothing
"""
import argparse
import datetime
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
RESULTS = os.path.join(REPO, 'results')

# The only thing dropped. It is MATSim's per-iteration scratch and no module in
# this repository reads it; every consumer works off the final output_* files.
PRUNABLE = ('ITERS',)

# A run must have produced these before anything is deleted: the run record so we
# know it finished, and the metrics so we know the outputs have been read.
REQUIRED = ('_run.json', '_metrics.json')


def dir_bytes(path):
    total = 0
    for dirpath, _, names in os.walk(path):
        for n in names:
            try:
                total += os.path.getsize(os.path.join(dirpath, n))
            except OSError:
                pass
    return total


def prune(run_dir, dry_run=False):
    """Returns (status, bytes_freed). Never raises on a run it declines to touch."""
    name = os.path.basename(run_dir.rstrip(os.sep))
    missing = [f for f in REQUIRED if not os.path.exists(os.path.join(run_dir, f))]
    if missing:
        return 'skipped: no %s' % ', '.join(missing), 0
    if os.path.exists(os.path.join(run_dir, '_pruned.json')):
        return 'already pruned', 0

    freed, removed = 0, []
    for rel in PRUNABLE:
        target = os.path.join(run_dir, 'output', rel)
        if not os.path.isdir(target):
            continue
        size = dir_bytes(target)
        freed += size
        removed.append({'path': 'output/' + rel, 'bytes': size})
        if not dry_run:
            shutil.rmtree(target, ignore_errors=True)
    if not removed:
        return 'nothing to prune', 0
    if dry_run:
        return 'would free %.1f GiB' % (freed / (1 << 30)), freed

    with open(os.path.join(run_dir, '_pruned.json'), 'w',
              encoding='utf-8', newline='\n') as f:
        json.dump({
            'run': name,
            'pruned_utc': datetime.datetime.now(datetime.UTC)
                          .strftime('%Y-%m-%dT%H:%M:%SZ'),
            'removed': removed,
            'bytes_freed': freed,
            'produced_by': 'src/run/prune_run.py',
            'note': 'MATSim per-iteration scratch. No module in src/analyse or '
                    'src/calibrate reads it; the final output_* files, modestats.csv '
                    'and the log are kept. The run is seeded and deterministic, so '
                    're-running reproduces what was removed.',
        }, f, indent=2)
        f.write('\n')
    return 'freed %.1f GiB' % (freed / (1 << 30)), freed


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('run_dir', nargs='?', help='a single run directory')
    ap.add_argument('--all', action='store_true', help='every run under results/')
    ap.add_argument('--dry-run', action='store_true', help='report, delete nothing')
    a = ap.parse_args()
    if not a.run_dir and not a.all:
        ap.error('give a run directory or --all')

    if a.all:
        runs = [os.path.join(RESULTS, d) for d in sorted(os.listdir(RESULTS))
                if os.path.isdir(os.path.join(RESULTS, d))]
    else:
        runs = [a.run_dir]

    total = 0
    for r in runs:
        status, freed = prune(r, a.dry_run)
        total += freed
        print('  %-44s %s' % (os.path.basename(r.rstrip(os.sep)), status))
    print('\n%s %.1f GiB across %d run(s)'
          % ('would free' if a.dry_run else 'freed', total / (1 << 30), len(runs)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
