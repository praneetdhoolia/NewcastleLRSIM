#!/usr/bin/env python
"""Close out a completed run: what it did, and whether it can be believed.

A finished run used to leave a log, a directory of scratch and three JSON files,
and the question *"so what happened?"* was answered by reading them. This writes
the answer down, in both dialects: `_summary.json` against a declared schema for
anything downstream, and `SUMMARY.md` for a person.

**It answers three questions and refuses a fourth.**

  1. *What was run?* Scenario, day type, sample fraction, seed, iteration count,
     thread count and the controler hash. A reading can never be separated from
     the run that produced it, and at 1% it cannot be compared with 10% at all
     (DECISIONS.md 9.12).
  2. *Did it relax?* After MATSim disables innovation no new plans are created,
     so any remaining movement in mode share is relaxation rather than search.
     That is precisely the question issue #5 turns on, and a run that has not
     settled supports no conclusion at all.
  3. *Did its own accounting close?* Every departure must end as an arrival, a
     stuck agent or an unresolved leg. A run that has lost agents is not one to
     take a number from.

The fourth question - *what does this say about Newcastle?* - is refused. There
is no mode share here, no patronage, no fit statistic and no comparison against a
validation target. Those come from `extract_metrics.py` -> `fit.py` ->
`report.py`, which is the only route to a reportable number, and the 67/143 split
is enforced inside `fit.py` rather than here. What this file carries is the
state of the RUN, not a finding about the city.

Run automatically by `run_matsim.py` when a run succeeds, and standalone on any
run directory that already holds telemetry:

    python src/analyse/summarise_run.py --run live_demo
"""
import os
import csv
import sys
import json
import argparse
import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(_HERE))
RESULTS = os.path.join(ROOT, 'results')
sys.path.insert(0, os.path.join(ROOT, 'src'))
import city as _city  # noqa: E402
import registry  # noqa: E402
from registry import outputs  # noqa: E402

# The city being modelled, for the two refusals this file prints. They named
# Newcastle in framework code, so a second city's run summary would have
# refused to make a finding about the wrong place.
_CITY_NAME = _city.descriptor()['name']

# How flat the trace must be before a run is reported as settled. DECLARED, not
# typed here: it decides the verdict issue #5 turns on, so it is swept like any
# other unobserved value instead of sitting in a constant nobody can see or vary.
# It was `DRIFT_THRESHOLD_PP = 0.5` in this file; the value moved unchanged.
DRIFT_TOLERANCE_PP = registry.load().get('RUN.relaxation.drift_tolerance_pp')


def _load(path, default=None):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _read_jsonl(path):
    out = []
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        continue
    except OSError:
        return []
    return out


def _config_param(run_dir, name):
    """A MATSim config param as the run actually executed it, else None."""
    import re
    try:
        with open(os.path.join(run_dir, 'config.xml'), encoding='utf-8') as f:
            m = re.search(r'name="%s" value="([^"]*)"' % re.escape(name), f.read())
    except OSError:
        return None
    return m.group(1) if m else None


def _modestats(path):
    try:
        with open(path, encoding='utf-8') as f:
            rows = list(csv.DictReader(f, delimiter=';'))
    except OSError:
        return {}
    if not rows:
        return {}
    out = {'iteration': [int(float(r['iteration'])) for r in rows]}
    for c in rows[0]:
        if not c or c == 'iteration':
            continue
        vals = []
        for r in rows:
            try:
                vals.append(float(r[c]))
            except (TypeError, ValueError):
                vals.append(None)
        out[c] = vals
    return out


def relaxation(modes, innovation_off_at, tolerance_pp=None):
    """Movement per mode between the innovation cutoff and the last iteration.

    Reports the two iteration numbers the movement was measured BETWEEN, not
    just the verdict: "settled" means nothing without the window it was settled
    over, and a reader applying a different tolerance needs both ends.
    """
    if tolerance_pp is None:
        tolerance_pp = DRIFT_TOLERANCE_PP
    block = {'innovation_off_at': innovation_off_at, 'drift_pp': {},
             'max_abs_drift_pp': None, 'tolerance_pp': tolerance_pp,
             'from_iteration': None, 'to_iteration': None,
             'relaxed': None,
             'basis': ('mode share between the innovation cutoff and the final '
                       'iteration. After the cutoff MATSim creates no new plans, '
                       'so what remains is relaxation, not search. This is a '
                       'statement about the run, not about mode choice.')}
    it = modes.get('iteration')
    if not it or innovation_off_at is None:
        return block
    try:
        i0 = next(i for i, v in enumerate(it) if v >= innovation_off_at)
    except StopIteration:
        block['basis'] += ' The run did not reach the cutoff.'
        return block
    if len(it) - 1 <= i0:
        return block
    block['from_iteration'] = int(it[i0])
    block['to_iteration'] = int(it[-1])
    worst = 0.0
    for k, v in modes.items():
        if k == 'iteration' or v[i0] is None or v[-1] is None:
            continue
        d = round((v[-1] - v[i0]) * 100.0, 3)
        block['drift_pp'][k] = d
        worst = max(worst, abs(d))
    if block['drift_pp']:
        block['max_abs_drift_pp'] = round(worst, 3)
        block['relaxed'] = worst <= tolerance_pp
    return block


def integrity(history):
    """Whether departures = arrivals + stuck + unresolved, per mode."""
    block = {'iterations_recorded': len(history) or None,
             'conservation_closes': None, 'conservation_detail': {},
             'telemetry_write_failures': None, 'stuck': {}, 'unresolved': {},
             'stuck_share_of_departures': None}
    if not history:
        return block
    last = history[-1]
    dep = last.get('departures') or {}
    arr = last.get('arrivals') or {}
    stk = last.get('stuck') or {}
    unr = last.get('unresolved') or {}
    closes = True
    for m in sorted(k for k in dep if k != 'total'):
        d = dep.get(m, 0)
        total = arr.get(m, 0) + stk.get(m, 0) + unr.get(m, 0)
        ok = (d == total)
        closes &= ok
        block['conservation_detail'][m] = {
            'departures': d, 'arrivals': arr.get(m, 0),
            'stuck': stk.get(m, 0), 'unresolved': unr.get(m, 0),
            'closes': ok}
    block['conservation_closes'] = closes
    block['stuck'] = {k: v for k, v in stk.items() if k != 'total'}
    block['unresolved'] = {k: v for k, v in unr.items() if k != 'total'}
    dtot = dep.get('total') or sum(v for k, v in dep.items() if k != 'total')
    stot = stk.get('total') or sum(v for k, v in stk.items() if k != 'total')
    if dtot:
        block['stuck_share_of_departures'] = round(100.0 * stot / dtot, 4)
    return block


def build(run_dir):
    name = os.path.basename(os.path.abspath(run_dir))
    out_dir = os.path.join(run_dir, 'output')
    rec = _load(os.path.join(run_dir, '_run.json'), {}) or {}
    snap = (_load(os.path.join(run_dir, '_config.json'), {}) or {}).get('values') or {}
    history = _read_jsonl(os.path.join(out_dir, 'telemetry.jsonl'))
    live = _load(os.path.join(out_dir, 'telemetry_live.json'), {}) or {}
    modes = _modestats(os.path.join(out_dir, 'modestats.csv'))

    iterations = rec.get('iterations') or snap.get('RUN.controler.last_iteration')
    # Read the cutoff from the config the run ACTUALLY executed, not from a
    # default. The first version looked up a registry key that does not exist
    # (`fraction_innovation_off`; the field is
    # `RUN.replanning.fraction_to_disable_innovation`) and fell back to a
    # hard-coded 0.8 - which is the shipped value, so it gave the right answer
    # for the wrong reason and would have kept giving it after the field moved.
    # There is no fallback now: unknown stays unknown.
    frac_off = _config_param(run_dir, 'fractionOfIterationsToDisableInnovation')
    if frac_off is None:
        frac_off = snap.get('RUN.replanning.fraction_to_disable_innovation')
    innovation_off_at = None
    if iterations and frac_off is not None:
        try:
            innovation_off_at = int(float(frac_off) * float(iterations))
        except (TypeError, ValueError):
            innovation_off_at = None

    integ = integrity(history)
    integ['telemetry_write_failures'] = live.get('write_failures')

    last = history[-1] if history else {}
    doc = {
        'name': name,
        'generated_utc': datetime.datetime.now(datetime.timezone.utc)
                                 .strftime('%Y-%m-%dT%H:%M:%SZ'),
        'produced_by': 'src/analyse/summarise_run.py',
        'run': {
            'scenario': rec.get('scenario'),
            'day': rec.get('day'),
            'fraction': rec.get('fraction', snap.get('RUN.sample.fraction')),
            'seed': rec.get('seed', snap.get('RUN.machine.seed')),
            'iterations': iterations,
            'threads': rec.get('threads'),
            'rc': rec.get('rc'),
            'wall_s': rec.get('wall_s'),
            'median_iteration_s': rec.get('median_iteration_s'),
            'persons_kept': rec.get('persons_kept'),
            'controler_sha256': rec.get('controler_sha256'),
        },
        'relaxation': relaxation(modes, innovation_off_at),
        'integrity': integ,
        'activity': {
            'departures': last.get('departures') or {},
            'arrivals': last.get('arrivals') or {},
            'en_route_vehicle_type_peak': _peak_fleet(last),
        },
        'not_a_result': (
            'This file records the STATE OF THE RUN, not a finding about '
            + _CITY_NAME + '. It carries no mode share, no patronage, no fit '
            'statistic and no comparison against a validation target. Leg '
            'counts here are what the mobsim moved in one iteration, which is '
            'neither the mode agents chose (modestats.csv) nor the trips that '
            'completed (_metrics.json) - DECISIONS.md 9.12. Nothing here is '
            'reportable as a model outcome.'),
        'next': [
            'python src/analyse/extract_metrics.py --run %s' % name,
            'python src/calibrate/fit.py --run %s' % name,
            'python src/calibrate/report.py --run %s' % name,
            'python src/run/prune_run.py --run %s   # reclaims output/ITERS' % name,
        ],
    }
    return doc


def _peak_fleet(last):
    """Largest simultaneous transit fleet in flight, by vehicle type."""
    peak = {}
    for b in last.get('profile') or []:
        for k, v in (b.get('vehicle_types') or {}).items():
            if k == 'total':
                continue
            if v > peak.get(k, 0):
                peak[k] = v
    return peak


def _fmt_s(v):
    if v is None:
        return '—'
    v = int(round(v))
    h, m, s = v // 3600, (v % 3600) // 60, v % 60
    return ('%dh %02dm' % (h, m)) if h else ('%dm %02ds' % (m, s))


def markdown(doc):
    r, rel, integ = doc['run'], doc['relaxation'], doc['integrity']
    L = []
    A = L.append
    A('# Run summary — `%s`' % doc['name'])
    A('')
    A('*Generated by `src/analyse/summarise_run.py`. Regenerate it; do not edit it.*')
    A('')
    A('> **This is not a result.** It records the state of the run, not a '
      'finding about ' + _CITY_NAME + ' - no mode share, no patronage, no fit '
      'statistic, no comparison against a validation target. Those come from '
      '`extract_metrics.py` → `fit.py` → `report.py`.')
    A('')

    # --- the verdict, first, because it decides whether anything else matters
    A('## Can this run be believed?')
    A('')
    verdict = []
    if rel.get('relaxed') is True:
        verdict.append('| relaxation | ✅ **settled** — no mode moves more than '
                       '%.1f pp between iteration %s and %s |'
                       % (rel['tolerance_pp'], rel.get('from_iteration'),
                          rel.get('to_iteration')))
    elif rel.get('relaxed') is False:
        verdict.append('| relaxation | ❌ **NOT settled** — worst mode still moving '
                       '**%.2f pp** between iteration %s and %s (tolerance %.1f pp) |'
                       % (rel['max_abs_drift_pp'], rel.get('from_iteration'),
                          rel.get('to_iteration'), rel['tolerance_pp']))
    else:
        verdict.append('| relaxation | — not measurable (run did not reach the '
                       'innovation cutoff) |')
    if integ.get('conservation_closes') is True:
        verdict.append('| accounting | ✅ every departure ends as an arrival, a '
                       'stuck agent or an unresolved leg |')
    elif integ.get('conservation_closes') is False:
        verdict.append('| accounting | ❌ **does not close** — the run has lost '
                       'agents |')
    else:
        verdict.append('| accounting | — no telemetry recorded |')
    wf = integ.get('telemetry_write_failures')
    if wf is not None:
        verdict.append('| telemetry | %s %d write failure(s) |'
                       % ('✅' if wf == 0 else '⚠️', wf))
    A('| | |')
    A('|---|---|')
    L.extend(verdict)
    A('')
    if rel.get('relaxed') is False:
        A('**A run that has not settled supports no conclusion.** After the '
          'innovation cutoff MATSim creates no new plans, so continued movement '
          'is the model still relaxing — the question issue #5 turns on. '
          '`DECISIONS.md` §9.27 measured the iteration count needed at ~1000.')
        A('')

    A('## What was run')
    A('')
    A('| | |')
    A('|---|---|')
    A('| scenario | **%s** × **%s** |' % (r.get('scenario'), r.get('day')))
    frac = r.get('fraction')
    A('| sample fraction | **%s** |'
      % ('—' if frac is None else '%g%%' % (frac * 100)))
    A('| seed | %s |' % r.get('seed'))
    A('| iterations | %s |' % r.get('iterations'))
    A('| agents | %s |' % ('—' if r.get('persons_kept') is None
                           else '{:,}'.format(r['persons_kept'])))
    A('| threads | %s |' % r.get('threads'))
    A('| wall clock | %s |' % _fmt_s(r.get('wall_s')))
    A('| median iteration | %s |'
      % ('—' if r.get('median_iteration_s') is None
         else '%.1f s' % r['median_iteration_s']))
    A('| exit code | %s |' % r.get('rc'))
    A('| controler | `%s` |' % (r.get('controler_sha256') or '—')[:16])
    A('')
    if frac is not None and frac <= 0.01:
        A('> ⚠️ **At 1% MATSim floors link storage at one vehicle**, producing '
          'spurious spillback that inflates car delay while teleported modes are '
          'immune. Cross-fraction comparison is invalid (`DECISIONS.md` §9.12, §15).')
        A('')

    if rel.get('drift_pp'):
        A('## Relaxation — drift after innovation was disabled')
        A('')
        A('Innovation off at iteration **%s** of %s.'
          % (rel.get('innovation_off_at'), r.get('iterations')))
        A('')
        A('| mode | drift |')
        A('|---|---:|')
        for k in sorted(rel['drift_pp']):
            A('| %s | %+.2f pp |' % (k, rel['drift_pp'][k]))
        A('')

    if integ.get('conservation_detail'):
        A('## Accounting — every departure has an end')
        A('')
        A('| mode | departures | arrivals | stuck | unresolved | closes |')
        A('|---|---:|---:|---:|---:|:--:|')
        for m in sorted(integ['conservation_detail']):
            c = integ['conservation_detail'][m]
            A('| %s | %s | %s | %s | %s | %s |'
              % (m, '{:,}'.format(c['departures']), '{:,}'.format(c['arrivals']),
                 '{:,}'.format(c['stuck']), '{:,}'.format(c['unresolved']),
                 '✅' if c['closes'] else '❌'))
        A('')
        share = integ.get('stuck_share_of_departures')
        if share is not None:
            A('Stuck agents are **%.3f%%** of all departures. A stuck agent is one '
              'the mobsim gave up on; a rising count means the network is '
              'gridlocked or broken.' % share)
            A('')

    peak = doc['activity'].get('en_route_vehicle_type_peak') or {}
    if peak:
        A('## Transit fleet in flight (peak, final iteration)')
        A('')
        A('| vehicle type | peak simultaneous |')
        A('|---|---:|')
        for k in sorted(peak):
            A('| %s | %s |' % (k, '{:,}'.format(peak[k])))
        A('')
        A("A passenger's leg mode is `pt` for all of these, so the split comes "
          'from the transit fleet, not from mode choice.')
        A('')

    A('## To get a reportable number from here')
    A('')
    A('```')
    for c in doc['next']:
        A(c)
    A('```')
    A('')
    A('`fit.py` reads **only** the calibration half of the pre-registered 67/143 '
      'split and raises if a holdout row survives its filter. That split opens '
      'once, at the end.')
    return '\n'.join(L) + '\n'


def summarise(run_dir, quiet=False):
    doc = build(run_dir)
    jpath = os.path.join(run_dir, '_summary.json')
    try:
        outputs.write_checked(jpath, doc, 'summary')
    except outputs.OutputError as e:
        print('summary failed its contract: %s' % e, flush=True)
        return None
    mpath = os.path.join(run_dir, 'SUMMARY.md')
    with open(mpath, 'w', encoding='utf-8', newline='\n') as f:
        f.write(markdown(doc))
    if not quiet:
        rel = doc['relaxation']
        print('wrote %s and SUMMARY.md' % os.path.basename(jpath), flush=True)
        print('  relaxed: %s   accounting closes: %s'
              % (rel.get('relaxed'), doc['integrity'].get('conservation_closes')),
              flush=True)
    return doc


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--run', required=True,
                    help='a directory name under results/, or a path')
    args = ap.parse_args()
    run_dir = args.run
    if not os.path.isdir(run_dir):
        run_dir = os.path.join(RESULTS, args.run)
    if not os.path.isdir(run_dir):
        raise SystemExit('no such run: %s' % args.run)
    summarise(run_dir)


if __name__ == '__main__':
    main()
