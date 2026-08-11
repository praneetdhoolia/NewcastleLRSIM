#!/usr/bin/env python
"""Constrain `asc_car_passenger` to the observed vehicle occupancy.

DECISIONS.md 8.5 allows two treatments of the mode constants: estimate them on
the pre-intervention period and hold them fixed, or **constrain them and report
the constraint**. This is the second, and the constraint is a physical one.

MATSim's `ride` occupies no vehicle, needs no driver to exist, consumes no road
capacity and costs nothing per kilometre (DECISIONS.md 9.8). Nothing in the
simulation stops every agent becoming a passenger, and nothing did: at the prior
constant of -0.85 the model settled at 4.52 ride legs per car leg, an implied
5.52 people per car against an observed 1.3503.

So `asc_car_passenger` is solved to reproduce the **observed** passenger:driver
ratio from `params/C4_mode_constraints.json`, which is a ratio of two published
HTS counts. The solved value is reported as a constraint, not presented as an
estimate of anything.

**This is not the ASC absorption proposal 9 warns about.** The constrained
constant is car passenger. `asc_lr`, `asc_bus` and `asc_rail` stay at their 8.5
priors and are not touched here, so the effect under test is untouched. What is
being pinned is how many people fit in a car.

The solve reads `params/C4_mode_constraints.json` and the schema-validated
`_metrics.json` of its own runs, produced by the declared pipeline rather than by
reading `modestats.csv` directly. **It does not open the validation targets at
all** - `fit.py` is deliberately not invoked - so it cannot read a holdout row
even by accident.

Every run parameter resolves through `config/registry/`; this file carries no
constant of its own. The candidate bracket is a required argument for the same
reason `--iterations` is: it is a choice the operator makes and records.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src', 'run'))
sys.path.insert(0, os.path.join(REPO, 'src'))
import run_matsim  # noqa: E402
import registry    # noqa: E402

CONSTRAINTS = os.path.join(REPO, 'params', 'C4_mode_constraints.json')
OUT = os.path.join(REPO, 'results', '_asc_ride_solve.json')


def shares_of(run_dir):
    """Mode shares from the DECLARED pipeline, not from raw `modestats.csv`.

    CLAUDE.md requires run_matsim.py -> extract_metrics.py, producing a
    schema-validated `_metrics.json`; reading `modestats.csv` directly and
    reporting from it is forbidden. `extract_metrics` opens run outputs, the
    station-link map and C3 only, so calling it here preserves this module's
    property that it cannot reach a validation target - `fit.py` is
    deliberately NOT invoked.
    """
    metrics = os.path.join(run_dir, '_metrics.json')
    if not os.path.exists(metrics):
        rc = subprocess.call([sys.executable,
                              os.path.join(REPO, 'src', 'analyse',
                                           'extract_metrics.py'),
                              '--run', run_dir], cwd=REPO)
        if rc != 0 or not os.path.exists(metrics):
            return None
    doc = json.load(open(metrics, encoding='utf-8'))
    return {k: v / 100.0
            for k, v in doc['mode_share']['all_residents_pct'].items()}


def ratio(shares):
    """ride legs per car leg - the model's analogue of passengers per driver."""
    if not shares or not shares.get('car'):
        return None
    return shares['ride'] / shares['car']


def evaluate(value, args, overrides):
    # Every run parameter resolves through the registry, so this solve runs
    # under exactly the same sweep and held-fixed guards as any other run and
    # writes the same `_config.json` snapshot. It previously called run() with
    # the pre-registry positional signature and could not execute at all.
    cfg = run_matsim.resolve(args.scenario, args.day, args.run_config, overrides)
    doc = run_matsim.run(args.scenario, args.day, cfg,
                         {'ride.constant': '%g' % value},
                         tag='asc_ride_%g_i%d' % (value, args.iterations))
    run_dir = os.path.join(run_matsim.RESULTS, doc['name'])
    shares = shares_of(run_dir)
    return dict(asc_car_passenger=value, shares=shares, ride_per_car=ratio(shares),
                run=doc.get('name'), rc=doc.get('rc'))


def interpolate(points, target):
    """Secant on log(ratio), which is where a logit constant acts linearly."""
    import math
    usable = [p for p in points if p['ride_per_car'] and p['ride_per_car'] > 0]
    if len(usable) < 2:
        return None
    usable.sort(key=lambda p: p['asc_car_passenger'])
    lo = hi = None
    for a, b in zip(usable, usable[1:]):
        if (a['ride_per_car'] - target) * (b['ride_per_car'] - target) <= 0:
            lo, hi = a, b
            break
    if lo is None:
        lo, hi = usable[0], usable[-1]          # extrapolate, and say so
    x0, y0 = lo['asc_car_passenger'], math.log(lo['ride_per_car'])
    x1, y1 = hi['asc_car_passenger'], math.log(hi['ride_per_car'])
    if y1 == y0:
        return None
    return round(x0 + (math.log(target) - y0) * (x1 - x0) / (y1 - y0), 4)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--values', required=True,
                    help='candidate asc_car_passenger values to bracket with, '
                         'comma separated. REQUIRED: a bracket is a choice the '
                         'operator makes, not a constant this file may carry')
    ap.add_argument('--scenario', default='S2')
    ap.add_argument('--day', default='WEEKDAY')
    ap.add_argument('--run-config', metavar='TAG',
                    help='a committed overlay under config/runs/<TAG>.json')
    # No defaults below. Each is a declared registry field, and a second copy in
    # this file is exactly the drift the registry exists to prevent
    # (DECISIONS.md 15). Passing one overrides the registry through the same
    # sweep and held-fixed guards as any other override.
    ap.add_argument('--fraction', type=float)
    ap.add_argument('--iterations', type=int, required=True)
    ap.add_argument('--threads', type=int)
    ap.add_argument('--xmx')
    ap.add_argument('--seed', type=int)
    a = ap.parse_args()

    overrides = {}
    for flag, key in (('fraction', 'RUN.sample.fraction'),
                      ('iterations', 'RUN.controler.last_iteration'),
                      ('threads', 'RUN.machine.threads'),
                      ('xmx', 'RUN.machine.xmx'),
                      ('seed', 'RUN.machine.seed')):
        value = getattr(a, flag)
        if value is not None:
            overrides[key] = value
    resolved = run_matsim.resolve(a.scenario, a.day, a.run_config, overrides)
    a.fraction = resolved.get('RUN.sample.fraction')
    a.seed = resolved.get('RUN.machine.seed')
    a.threads = resolved.get('RUN.machine.threads')

    c4 = json.load(open(CONSTRAINTS, encoding='utf-8'))
    target = c4['passenger_per_driver']['value']
    lo, hi = c4['passenger_per_driver']['sweep']
    print('observed passenger:driver = %.4f (observed range %.4f-%.4f over %d '
          'survey years)' % (target, lo, hi, c4['vehicle_occupancy']['years_observed']),
          flush=True)

    points = [evaluate(float(v), a, overrides) for v in a.values.split(',')]
    solved = interpolate(points, target)
    doc = dict(target_passenger_per_driver=target,
               target_sweep=[lo, hi],
               target_source=c4['source'],
               protocol=dict(scenario=a.scenario, day=a.day, fraction=a.fraction,
                             iterations=a.iterations, seed=a.seed,
                             threads=a.threads),
               points=points, solved_asc_car_passenger=solved,
               prior_asc_car_passenger=registry.load().get('C.asc.car_passenger'),
               note='Solved at a fixed %d-iteration protocol, which DECISIONS.md '
                    '9.7 shows is NOT equilibrium. The value is a constraint '
                    'reported under DECISIONS.md 8.5, not an estimate, and must '
                    'be re-solved once the iteration count is settled.'
                    % a.iterations)
    json.dump(doc, open(OUT, 'w'), indent=2)
    print()
    for p in points:
        print('  asc %-7s -> ride/car %s  (car %s ride %s)'
              % (p['asc_car_passenger'],
                 ('%.4f' % p['ride_per_car']) if p['ride_per_car'] else 'n/a',
                 ('%.4f' % p['shares']['car']) if p['shares'] else 'n/a',
                 ('%.4f' % p['shares']['ride']) if p['shares'] else 'n/a'))
    print('\nsolved asc_car_passenger = %s (prior %.2f)' % (solved, -0.85))


if __name__ == '__main__':
    main()
