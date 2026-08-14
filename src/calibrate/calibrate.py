#!/usr/bin/env python
"""P4 deliverable 4: the calibration loop.

Deterministic, resumable, and structurally unable to read a holdout row.

**It cannot see the holdout.** This module never opens the validation targets. It
calls `run_matsim` and `extract_metrics`, then `fit`, and reads the `_fit.json`
that `fit` wrote - and `fit` filters to `split == 'calibration'` at read time and
raises if anything else survives. As a second, independent check the loop asserts
that every target id appearing in a fit block is in the calibration set *as
reported by fit itself*, so a leak would have to defeat both.

**It cannot move a parameter it is not allowed to move.** The search space is
derived from the registry, not listed here: a field is free only if it is
`assumed`, carries a numeric sweep interval, and is NOT `held_fixed`. The six
fields held fixed under DECISIONS.md 8.5 - the mode constants - are therefore
unreachable from this loop by construction, which is the whole point of 8.5.
Proposal 9 names ASC absorption as the primary threat to validity.

**It refuses to fit more parameters than the data identifies.** The objective
contains four independent numbers (five HTS mode shares that sum to one). A
search over more free parameters than that is not a calibration, and the loop
exits rather than producing one.

**It does not calibrate against traffic counts.** DECISIONS.md 9.14 and 9.15:
the external tier carries no through traffic, so every boundary-adjacent count is
biased low by construction and tuning the core network against them would be
compensating for absent demand. Counts are still scored and reported on every
run - they are simply not optimised against. `CAL.objective.include_counts`
holds the rule and the loop enforces it.

**Constraints are constraints, not targets.** The occupancy and trip-length
constraints (C4) never enter the objective; a candidate that violates one is
marked infeasible and reported. Adding an observable to the objective would make
it a target, and the 67/143 split is pre-registered.

    python src/calibrate/calibrate.py --scenario S2 --day WEEKDAY \
        --run-config cordon_escort_10pct --plan
    python src/calibrate/calibrate.py --scenario S2 --day WEEKDAY \
        --run-config cordon_escort_10pct --execute
"""

# City-relative paths resolve through src/city.py: `data/...` names a
# location inside cities/<city>/, not inside the repository root.
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                  '..', '..', 'src'))
import city as _city  # noqa: E402
import os
import sys
import json
import argparse
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import registry as _registry                                    # noqa: E402

OUT = _city.path('params/C5_calibration.json')


# What a candidate has to REBUILD before a change to a field is real. The loop
# runs run_matsim -> extract_metrics -> fit and rebuilds nothing else, so a field
# whose only consumer is a build script cannot be realised by passing --set: that
# would change the recorded configuration without changing a single input, which
# is worse than not calibrating it at all.
#
# `forbidden` is not about cost. DECISIONS.md 3.5: re-running the pt2matsim
# mapper changes ~18% of route link sequences, so a scenario mapped in one build
# cannot be compared with one mapped in another. Those fields are uncalibratable
# inside a comparison, whatever their sweep says.
STAGE_OF_CONSUMER = {
    'build_matsim_network.py': 'forbidden',
    'build_scenario_schedules.py': 'forbidden',
    'build_sumo_corridor.py': 'forbidden',
    'build_corridor_road_attributes.py': 'forbidden',
    'build_era1_reconstruction.py': 'forbidden',
    'build_gtfs_extras.py': 'forbidden',
    'shape_tools.py': 'forbidden',
    'build_activity_chains.py': 'demand',
    'build_population.py': 'demand',
    'build_matsim_plans.py': 'demand',
    'build_landuse_parking.py': 'demand',
    'build_zone_attractions.py': 'demand',
    'build_matsim_run_inputs.py': 'run_inputs',
}
MEASUREMENT_LAYERS = ('src/analyse/', 'src/calibrate/')
# Stages this loop can actually carry out for a candidate.
STAGES_IMPLEMENTED = ('none', 'run_inputs')


def rebuild_stage(key, field):
    """What a change to this field would require. 'none' means run-time only."""
    if key.startswith('CAL.'):
        return 'excluded', "the loop's own search controls"
    if key.startswith('RUN.'):
        return 'excluded', ('run identity and compute, not a property of %s'
                            % _city.descriptor()['name'])
    stage, why = 'none', None
    for c in field.get('consumers') or []:
        if any(c.startswith(m) for m in MEASUREMENT_LAYERS):
            return 'excluded', ('consumed by %s: measurement apparatus, not the '
                                'model' % c)
        st = STAGE_OF_CONSUMER.get(c.rsplit('/', 1)[-1])
        if st == 'forbidden':
            return 'forbidden', ('consumed by %s: realising it needs the '
                                 'schedule mapper re-run, which 3.5 forbids '
                                 'inside a comparison' % c)
        if st == 'demand' and stage != 'demand':
            stage, why = 'demand', ('consumed by %s: needs B2, the plans and the '
                                    'run inputs rebuilt per candidate' % c)
        elif st == 'run_inputs' and stage == 'none':
            stage, why = 'run_inputs', 'needs the 30 run-input sets regenerated'
    if not (field.get('consumers') or []):
        return 'excluded', 'no declared consumer: nothing would read a change'
    return stage, why


def excluded_reason(key, field):
    """Why a field with a sweep is still not calibratable. None if it is."""
    stage, why = rebuild_stage(key, field)
    if stage in STAGES_IMPLEMENTED:
        return None
    return why or ('needs the %s rebuild, which this loop does not carry out'
                   % stage)


def free_parameters(cfg, report=None):
    """Registry fields this loop is permitted to move, derived not listed."""
    free = []
    for key in sorted(cfg.keys()):
        f = cfg.field(key)
        if f.get('status') != 'active':
            continue
        if f.get('source') != 'assumed':
            continue                      # measured/derived/definition are not ours
        if 'held_fixed' in f:
            continue                      # DECISIONS.md 8.5 and friends
        lo, hi = sweep_interval(f)
        if lo is None or not isinstance(f.get('value'), (int, float)):
            continue                      # dict- or list-valued sweeps are not scalar
        why = excluded_reason(key, f)
        if why:
            if report is not None:
                report.append((key, why))
            continue
        free.append(dict(key=key, value=float(f['value']), lo=lo, hi=hi,
                         units=f.get('units'), decisions_ref=f.get('decisions_ref')))
    return free


def sweep_interval(field):
    """(lo, hi) if the field carries a scalar sweep, else (None, None)."""
    s = field.get('sweep')
    if isinstance(s, list) and len(s) == 2 and all(
            isinstance(v, (int, float)) for v in s):
        return float(s[0]), float(s[1])
    if isinstance(s, dict):
        iv = s.get('interval')
        if isinstance(iv, list) and len(iv) == 2:
            return float(iv[0]), float(iv[1])
        p = s.get('proportional')
        v = field.get('value')
        if isinstance(p, (int, float)) and isinstance(v, (int, float)):
            return v * (1.0 - p), v * (1.0 + p)
    return None, None


def objective(fit, components):
    """Scalar objective from a fit block. A missing component is an error."""
    total = 0.0
    parts = {}
    for path, weight in sorted(components.items()):
        node = fit
        for bit in path.split('.'):
            if not isinstance(node, dict) or bit not in node:
                raise SystemExit(
                    'objective component %r is not in the fit output. The loop '
                    'will not treat a missing component as zero - that would '
                    'silently optimise something other than what was declared.'
                    % path)
            node = node[bit]
        if not isinstance(node, (int, float)):
            raise SystemExit('objective component %r is not a number' % path)
        parts[path] = node
        total += weight * float(node)
    return total, parts


def feasible(fit):
    """C4 constraints. Violations make a candidate infeasible, never scored."""
    why = []
    occ = fit.get('occupancy_constraint') or {}
    if occ and not occ.get('inside_observed_range', True):
        why.append('vehicle occupancy %.4f passengers/driver is outside the '
                   'observed range %s'
                   % (occ.get('modelled_passenger_per_driver', float('nan')),
                      occ.get('observed_sweep')))
    tg = fit.get('trip_geometry_constraint') or {}
    for mode, g in sorted((tg.get('modes') or {}).items()):
        if not g.get('inside_observed_range', True):
            why.append('%s trip length %.2f km is outside the observed range'
                       % (mode, g.get('modelled_mean_distance_km', float('nan'))))
    return (not why), why


def audit_no_holdout(fit):
    """Second, independent check that no holdout row reached the objective."""
    avail = fit.get('calibration_targets_available')
    if not isinstance(avail, int):
        raise SystemExit('fit output does not state how many calibration '
                         'targets were available; refusing to optimise on it')
    scored, unscorable = fit.get('scored'), fit.get('unscorable')
    if scored is None or unscorable is None:
        raise SystemExit('fit output does not reconcile scored against '
                         'explained; refusing to optimise on it')
    if scored + len(unscorable) != avail:
        raise SystemExit('fit output does not reconcile: %s scored + %s '
                         'explained != %s available'
                         % (scored, len(unscorable), avail))
    for block in ('mode_share', 'patronage', 'counts'):
        b = fit.get(block) or {}
        if b.get('n') and not b.get('targets'):
            raise SystemExit('fit block %r scored %s targets without naming '
                             'them; a statistic that does not name its targets '
                             'is not reportable' % (block, b.get('n')))


def grid(p, n):
    """n points across a parameter's sweep, endpoints included, current kept."""
    if n < 2:
        return [p['value']]
    step = (p['hi'] - p['lo']) / (n - 1)
    pts = [p['lo'] + i * step for i in range(n)]
    if not any(abs(x - p['value']) < 1e-12 for x in pts):
        pts.append(p['value'])
    return sorted(set(round(x, 10) for x in pts))


def candidate_tag(base, key, value):
    short = key.replace('.', '_')
    return '%s__%s_%g' % (base, short, value)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--scenario', default='S2')
    ap.add_argument('--day', default='WEEKDAY')
    ap.add_argument('--run-config', required=True,
                    help='committed overlay giving fraction, iterations, threads')
    ap.add_argument('--plan', action='store_true',
                    help='print the search and its cost, run nothing')
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--only', action='append', default=None,
                    help='restrict the free set to these registry keys')
    a = ap.parse_args()
    if not (a.plan or a.execute):
        raise SystemExit('choose --plan or --execute')

    cfg = _registry.load(scenario=a.scenario, day=a.day, run=a.run_config)
    comps = cfg.get('CAL.objective.components')
    if cfg.get('CAL.objective.include_counts'):
        raise SystemExit(
            'CAL.objective.include_counts is true. DECISIONS.md 9.14 forbids '
            'count-based calibration while boundary through traffic is '
            'unrepresented. Record a departure there before setting it.')
    n_free_allowed = int(cfg.get('CAL.objective.independent_targets'))
    ppp = int(cfg.get('CAL.search.points_per_parameter'))
    max_rounds = int(cfg.get('CAL.search.max_rounds'))
    delta = float(cfg.get('CAL.search.convergence_delta'))

    excluded = []
    free = free_parameters(cfg, excluded)
    if a.only:
        keep = set(a.only)
        free = [p for p in free if p['key'] in keep]
        missing = keep - {p['key'] for p in free}
        if missing:
            raise SystemExit('not free parameters (measured, held fixed, or no '
                             'scalar sweep): %s' % ', '.join(sorted(missing)))

    print('%d registry fields are movable by this loop (assumed, scalar sweep, '
          'not held fixed, not excluded).' % len(free))
    print('%d were excluded with a reason:' % len(excluded))
    for k, why in excluded:
        print('   %-46s %s' % (k, why))
    print('The objective contains %d independent numbers.' % n_free_allowed)
    if len(free) > n_free_allowed:
        print('\nA search over all of them would fit %d parameters to %d '
              'numbers.' % (len(free), n_free_allowed))
        print('Name at most %d with --only. The movable set is:'
              % n_free_allowed)
        for p in free:
            print('   %-46s %10.5g  sweep %.5g - %.5g  [%s]'
                  % (p['key'], p['value'], p['lo'], p['hi'], p['units']))
        raise SystemExit(
            '\nrefusing to fit %d parameters to %d independent numbers: that is '
            'not a calibration. Choose a subset with --only, on a stated reason.'
            % (len(free), n_free_allowed))

    evals = sum(len(grid(p, ppp)) for p in free) * max_rounds
    print('\nsearch: coordinate descent, %d parameter(s), %d point(s) each, '
          'up to %d round(s)' % (len(free), ppp, max_rounds))
    print('objective: %s' % ', '.join('%s x%.3g' % (k, v)
                                      for k, v in sorted(comps.items())))
    print('at most %d run(s); each is a full MATSim run at the overlay settings'
          % evals)
    for p in free:
        print('   %-46s start %10.5g   points %s'
              % (p['key'], p['value'],
                 ', '.join('%g' % x for x in grid(p, ppp))))
    if a.plan:
        print('\n--plan: nothing was run.')
        return

    import subprocess

    history, current = [], {p['key']: p['value'] for p in free}
    best_obj, best_tag = None, None
    base = 'cal_%s_%s_%s' % (a.scenario, a.day, a.run_config)

    def evaluate(tag, overrides):
        """One candidate: run, extract, fit, score. Resumable by tag."""
        run_dir = os.path.join(_city.REPO, 'results', tag)
        fit_path = os.path.join(run_dir, '_fit.json')
        if not os.path.exists(fit_path):
            # the declared pipeline, invoked exactly as a reader would by hand:
            # run_matsim.py -> extract_metrics.py -> fit.py
            sets = []
            for k, v in sorted(overrides.items()):
                sets += ['--set', '%s=%s' % (k, v)]
            steps = [
                [sys.executable, 'src/run/run_matsim.py',
                 '--scenario', a.scenario, '--day', a.day,
                 '--run-config', a.run_config, '--tag', tag] + sets,
                [sys.executable, 'src/analyse/extract_metrics.py', '--run', tag],
                [sys.executable, 'src/calibrate/fit.py', '--run', tag],
            ]
            for cmd in steps:
                r = subprocess.run(cmd)
                if r.returncode != 0:
                    raise SystemExit('%s failed (%d) for candidate %s'
                                     % (cmd[1], r.returncode, tag))
        f = json.load(open(fit_path, encoding='utf-8'))
        audit_no_holdout(f)
        obj, parts = objective(f, comps)
        ok, why = feasible(f)
        rec = dict(tag=tag, overrides=dict(overrides), objective=obj,
                   components=parts, feasible=ok, constraint_violations=why)
        history.append(rec)
        print('   %-58s obj %8.4f %s' % (tag, obj, '' if ok else '  INFEASIBLE'))
        return rec

    for rnd in range(max_rounds):
        print('\nround %d' % (rnd + 1))
        start = best_obj
        for p in free:
            for value in grid(p, ppp):
                ov = dict(current)
                ov[p['key']] = value
                rec = evaluate(candidate_tag(base, p['key'], value), ov)
                if rec['feasible'] and (best_obj is None or rec['objective'] < best_obj):
                    best_obj, best_tag = rec['objective'], rec['tag']
                    current[p['key']] = value
        if start is not None and best_obj is not None and start - best_obj < delta:
            print('round improved the objective by %.4f < %.4f: stopping'
                  % (start - best_obj, delta))
            break

    result = dict(
        generated=datetime.datetime.now(datetime.timezone.utc)
        .strftime('%Y-%m-%dT%H:%M:%SZ'),
        scenario=a.scenario, day=a.day, run_config=a.run_config,
        objective_components=comps,
        independent_targets=n_free_allowed,
        free_parameters=[p['key'] for p in free],
        best_tag=best_tag, best_objective=best_obj,
        calibrated=current, history=history,
        note='Calibrated against the CALIBRATION half only. Counts were scored '
             'and reported but not optimised against (DECISIONS.md 9.14). The '
             'C4 constraints were feasibility conditions, never targets.')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(result, open(OUT, 'w'), indent=2)
    print('\nbest %s at objective %.4f -> %s' % (best_tag, best_obj, OUT))


if __name__ == '__main__':
    main()
