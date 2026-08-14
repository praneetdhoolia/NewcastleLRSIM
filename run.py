#!/usr/bin/env python
"""Run a scenario. The one command this repository needs a newcomer to know.

    python run.py                            a smoke run: S2, weekday, 1%, 2 iterations
    python run.py --list                     what can be run: scenarios, day types, overlays
    python run.py --dry-run                  resolve every input and print it; execute nothing
    python run.py --run-config ride_fix_10pct        a committed run overlay
    python run.py --scenario S3 --day SAT --fraction 0.10 --iterations 1000 --tag s3_sat

This is a front door, not a second harness. Everything below it is
`src/run/run_matsim.py`, which owns the run identity, the subsample, the config
patching and the run record; this module adds argument defaults, a dry run, a
listing and the metric extraction that would otherwise be a second command.

**It will not invent an iteration count.** `RUN.controler.last_iteration` is
declared `unobtained` in the registry (DECISIONS.md 9.7: 100 and 250 are both
MEASURED to be too low, and no justified value has been established), so a bare
`python run.py` does not quietly pick one. It selects the committed `smoke`
overlay, which sets 2 iterations, and says so in terms that cannot be mistaken
for a result. Any run you intend to read must name its own overlay or pass
`--iterations`.

**Nothing this produces is a result** until the model has a calibrated base;
see docs/STATUS.md.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for sub in ('run', 'analyse', 'registry', ''):
    sys.path.insert(0, os.path.join(HERE, 'src', sub) if sub else os.path.join(HERE, 'src'))

import registry                      # noqa: E402
import run_matsim                    # noqa: E402

DEFAULT_OVERLAY = 'smoke'

SMOKE_BANNER = """
+---------------------------------------------------------------------------+
|  SMOKE RUN - a plumbing test, NOT a modelling run.                         |
|                                                                            |
|  No overlay and no --iterations were given, and the registry declares       |
|  RUN.controler.last_iteration UNOBTAINED, so this falls back to the         |
|  committed `smoke` overlay: 1% sample, 2 iterations.                        |
|                                                                            |
|  NOTHING PRODUCED UNDER THIS OVERLAY IS A RESULT. No mode share, no         |
|  patronage, no count and no fit statistic from it may be quoted or          |
|  compared. Two iterations is three orders of magnitude short of relaxation. |
|                                                                            |
|  For a real run, name an overlay (--run-config) or pass --iterations.       |
+---------------------------------------------------------------------------+
"""


def listing():
    """What is actually runnable, read from the package rather than hardcoded."""
    print('scenarios with assembled run inputs (%s):' % run_matsim.SETS)
    if os.path.isdir(run_matsim.SETS):
        for s in sorted(os.listdir(run_matsim.SETS)):
            if not os.path.isdir(os.path.join(run_matsim.SETS, s)):
                continue                       # the run-inputs report sits alongside
            days = sorted(d for d in os.listdir(os.path.join(run_matsim.SETS, s))
                          if os.path.isdir(os.path.join(run_matsim.SETS, s, d)))
            print('  %-5s %s' % (s, ' '.join(days) if days else '(no day types)'))
    else:
        print('  none - %s does not exist' % run_matsim.SETS)

    print('\nrun overlays (--run-config):')
    runs_dir = registry.OVERLAY_DIRS['run']
    for f in sorted(os.listdir(runs_dir)) if os.path.isdir(runs_dir) else []:
        if not f.endswith('.json'):
            continue
        import json
        doc = json.load(open(os.path.join(runs_dir, f), encoding='utf-8'))
        sets = doc.get('set', {})
        print('  %-28s f=%-6s i=%-6s %s'
              % (f[:-5],
                 sets.get('RUN.sample.fraction', '-'),
                 sets.get('RUN.controler.last_iteration', '-'),
                 (doc.get('description', '')[:60] + '...')
                 if len(doc.get('description', '')) > 60 else doc.get('description', '')))

    print('\nfinished runs in %s:' % run_matsim.RESULTS)
    if os.path.isdir(run_matsim.RESULTS):
        for d in sorted(os.listdir(run_matsim.RESULTS)):
            done = os.path.exists(os.path.join(run_matsim.RESULTS, d, '_run.json'))
            print('  %-40s %s' % (d, 'complete' if done else 'incomplete'))
    return 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--scenario', default='S2', help='default: S2')
    ap.add_argument('--day', default='WEEKDAY', choices=['WEEKDAY', 'SAT', 'SUN'])
    ap.add_argument('--run-config', metavar='TAG',
                    help='a committed overlay under the city overlays/runs directory - '
                         'the reproducible way to vary a run. Defaults to `%s` ONLY '
                         'when no --iterations is given' % DEFAULT_OVERLAY)
    ap.add_argument('--fraction', type=float, help='sample fraction, e.g. 0.10')
    ap.add_argument('--iterations', type=int,
                    help='MATSim last iteration. There is no default: the registry '
                         'declares this field unobtained and refuses to invent one')
    ap.add_argument('--threads', type=int)
    ap.add_argument('--xmx', help='JVM heap, e.g. 26g')
    ap.add_argument('--seed', type=int)
    ap.add_argument('--tag', help='name the run directory. ALWAYS tag a re-run: an '
                                  'untagged re-run overwrites the previous directory')
    ap.add_argument('--force', action='store_true',
                    help='re-run even if a complete run record already exists')
    ap.add_argument('--config-set', action='append', default=[], metavar='KEY=VALUE',
                    help='registry override, checked against the declared sweep')
    ap.add_argument('--set', action='append', default=[], metavar='KEY=VALUE',
                    help='MATSim config override, e.g. ride.constant=-3.4')
    ap.add_argument('--dry-run', action='store_true',
                    help='resolve the registry, print the snapshot, execute nothing')
    ap.add_argument('--list', action='store_true',
                    help='list runnable scenarios, run overlays and finished runs')
    ap.add_argument('--no-metrics', action='store_true',
                    help='skip metric extraction after a successful run')
    a = ap.parse_args()

    if a.list:
        return listing()

    # The one defaulting decision this script makes, and it is made loudly.
    run_config = a.run_config
    smoke = False
    if run_config is None and a.iterations is None:
        run_config = DEFAULT_OVERLAY
        smoke = True
        print(SMOKE_BANNER)

    overrides = registry.parse_set(a.config_set)
    for flag, key in (('fraction', 'RUN.sample.fraction'),
                      ('iterations', 'RUN.controler.last_iteration'),
                      ('threads', 'RUN.machine.threads'),
                      ('xmx', 'RUN.machine.xmx'),
                      ('seed', 'RUN.machine.seed')):
        value = getattr(a, flag)
        if value is not None:
            overrides[key] = value

    cfg = run_matsim.resolve(a.scenario, a.day, run_config, overrides)

    if a.dry_run:
        print('scenario %s  day %s  overlay %s'
              % (a.scenario, a.day, run_config or '(none)'))
        src_dir = os.path.join(run_matsim.SETS, a.scenario, a.day)
        print('inputs   %s  %s' % (src_dir, 'OK' if os.path.isdir(src_dir) else 'MISSING'))
        snap = cfg.snapshot()
        values, origin = snap['values'], snap['resolved_from']
        print('\nresolved registry - %d fields, layers %s:'
              % (snap['registry_fields'], ' -> '.join(snap['layers'])))
        for key in sorted(values):
            print('  %-46s %-24s [%s]'
                  % (key, repr(values[key])[:24], origin.get(key, '?')))
        print('\ndry run: nothing was executed')
        return 0

    doc = run_matsim.run(a.scenario, a.day, cfg,
                         dict(run_matsim.parse_override(s) for s in a.set),
                         a.tag, a.force)
    if doc.get('rc') != 0:
        return 1

    run_dir = os.path.join(run_matsim.RESULTS, doc['name'])
    if not a.no_metrics:
        try:
            _extract(run_dir)
        except Exception as e:                               # noqa: BLE001
            # A failed extraction does not invalidate the run: the run record and
            # the summary are already written, and metrics can be re-extracted.
            print('metric extraction failed (the run itself is intact): %s' % e,
                  flush=True)

    print('\nrun directory: %s' % run_dir)
    print('live/replay view:  python src/analyse/run_view.py --run %s' % run_dir)
    if smoke:
        print('\nreminder: this was a SMOKE run. It is not a result.')
    return 0


def _extract(run_dir):
    """Shell out to the metric extractor, which owns its own CLI contract."""
    import subprocess
    subprocess.check_call([sys.executable,
                           os.path.join(HERE, 'src', 'analyse', 'extract_metrics.py'),
                           '--run', run_dir])


if __name__ == '__main__':
    sys.exit(main())
