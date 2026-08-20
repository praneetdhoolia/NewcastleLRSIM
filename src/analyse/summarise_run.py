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

# How many iterations after the innovation cutoff the drift window starts.
# DECLARED for the same reason as the tolerance: it decides the verdict. The
# window used to start AT the cutoff, which swept in a ONE-ITERATION selection
# snap (+3.4 pp car at both fractions) and made the gate unpassable at any
# horizon - a defect in the instrument, not in the runs (DECISIONS.md 9.43).
SETTLE_MARGIN_ITERS = registry.load().get('RUN.relaxation.settle_margin_iterations')


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


def relaxation(modes, innovation_off_at, tolerance_pp=None, settle_margin=None):
    """Movement per mode between the SETTLE POINT and the last iteration.

    Reports the two iteration numbers the movement was measured BETWEEN, not
    just the verdict: "settled" means nothing without the window it was settled
    over, and a reader applying a different tolerance needs both ends.

    **The window does not start at the innovation cutoff, and this is the whole
    point of the function.** When innovation is disabled, exploration stops in a
    single step and selection concentrates every agent onto its best-scoring
    plan. Measured on both 1000-iteration arms, that snap lands entirely in
    iteration 801: car +3.256 pp at 10% and +3.380 pp at 25%, walk 3.97 -> 1.02%,
    pt 1.08 -> 0.25%. It is a property of the scoring structure, and a window
    starting at the cutoff includes it - so a run of ANY length failed the gate
    by ~3.5 pp no matter how well it had relaxed (DECISIONS.md 9.43).

    So the window starts at cutoff + `RUN.relaxation.settle_margin_iterations`,
    and the snap is REPORTED rather than discarded: `snap_pp` carries it, and
    `cutoff_to_final_pp` carries the number the old instrument produced, so
    nothing that was previously visible has been hidden by the fix.
    """
    if tolerance_pp is None:
        tolerance_pp = DRIFT_TOLERANCE_PP
    if settle_margin is None:
        settle_margin = SETTLE_MARGIN_ITERS
    block = {'innovation_off_at': innovation_off_at, 'drift_pp': {},
             'max_abs_drift_pp': None, 'tolerance_pp': tolerance_pp,
             'settle_margin_iterations': settle_margin,
             'settle_point': None,
             'snap_pp': {}, 'max_abs_snap_pp': None,
             'cutoff_to_final_pp': {},
             'from_iteration': None, 'to_iteration': None,
             'relaxed': None,
             'basis': ('mode share between the settle point (the innovation '
                       'cutoff plus the declared settle margin) and the final '
                       'iteration. After the cutoff MATSim creates no new plans, '
                       'so what remains is relaxation, not search. The margin '
                       'excludes the one-iteration selection snap at the cutoff, '
                       'which is reported separately as snap_pp and is NOT '
                       'evidence of an unsettled run. This is a statement about '
                       'the run, not about mode choice.')}
    it = modes.get('iteration')
    if not it or innovation_off_at is None:
        return block

    def _at(target):
        """Index of the first recorded iteration at or after `target`."""
        try:
            return next(i for i, v in enumerate(it) if v >= target)
        except StopIteration:
            return None

    i_cut = _at(innovation_off_at)
    if i_cut is None:
        block['basis'] += ' The run did not reach the cutoff.'
        return block

    settle_point = innovation_off_at + (settle_margin or 0)
    i0 = _at(settle_point)
    if i0 is None or len(it) - 1 <= i0:
        # The run stopped inside the settle margin: there is a cutoff but no
        # window to score. Report the snap that IS measurable and refuse the
        # verdict rather than scoring a window shorter than the margin.
        block['settle_point'] = settle_point
        block['basis'] += (' The run ended within the settle margin of the '
                           'cutoff, so no relaxation window exists and no '
                           'verdict is given.')
        return block

    block['settle_point'] = int(it[i0])
    block['from_iteration'] = int(it[i0])
    block['to_iteration'] = int(it[-1])
    worst = 0.0
    worst_snap = 0.0
    for k, v in modes.items():
        if k == 'iteration':
            continue
        if v[i0] is not None and v[-1] is not None:
            d = round((v[-1] - v[i0]) * 100.0, 3)
            block['drift_pp'][k] = d
            worst = max(worst, abs(d))
        # The snap, and the number the pre-9.43 instrument reported. Kept so a
        # reader can see exactly what the window change did and re-derive the
        # old verdict without re-reading the run.
        if v[i_cut] is not None and v[i0] is not None:
            s = round((v[i0] - v[i_cut]) * 100.0, 3)
            block['snap_pp'][k] = s
            worst_snap = max(worst_snap, abs(s))
        if v[i_cut] is not None and v[-1] is not None:
            block['cutoff_to_final_pp'][k] = round((v[-1] - v[i_cut]) * 100.0, 3)
    if block['snap_pp']:
        block['max_abs_snap_pp'] = round(worst_snap, 3)
    if block['drift_pp']:
        block['max_abs_drift_pp'] = round(worst, 3)
        block['relaxed'] = worst <= tolerance_pp
    return block


def events_accounting(out_dir):
    """Per-mode departures / arrivals / stuck, read from the final iteration's
    own events stream rather than from telemetry's in-flight tracking (#54).

    Each `stuckAndAbort` is attributed to the PERSON'S OPEN LEG - the leg whose
    departure event is still unterminated when the abort arrives. Measured on
    both physical-boarding probes, the mobsim's end-of-day abort and an
    engine's afterMobsim abort can BOTH fire for the same passenger (ride: 3
    stuck events against 2 unfinished legs on `allmodes_probe`, 12 against 7 on
    `jointride_probe`, all at 30:00:00), so a second abort for a person with no
    open leg is counted in `duplicate_aborts` instead of corrupting the
    conservation identity - which is exactly how the telemetry-based
    attribution false-negatived the gate on runs whose events balance.

    Returns None when the events file is absent (e.g. a pruned run), in which
    case the telemetry snapshot remains the only source and `integrity()` says
    so. Streams the file; on a 25% arm this reads a few hundred MB of gzip and
    takes minutes, which a once-per-run close-out can afford.
    """
    path = os.path.join(out_dir, 'output_events.xml.gz')
    if not os.path.exists(path):
        return None
    import gzip
    import xml.etree.ElementTree as ET

    def bump(d, k):
        d[k] = d.get(k, 0) + 1

    dep, arr, stuck, dup, unresolved = {}, {}, {}, {}, {}
    open_leg = {}  # person id -> mode of the leg currently in flight
    try:
        with gzip.open(path) as f:
            stream = ET.iterparse(f, events=('start', 'end'))
            _, root = next(stream)
            for ev, el in stream:
                if ev != 'end' or el.tag != 'event':
                    continue
                t = el.get('type')
                if t == 'departure':
                    open_leg[el.get('person')] = el.get('legMode')
                    bump(dep, el.get('legMode'))
                elif t == 'arrival':
                    open_leg.pop(el.get('person'), None)
                    bump(arr, el.get('legMode'))
                elif t == 'stuckAndAbort':
                    m = open_leg.pop(el.get('person'), None)
                    if m is None:
                        bump(dup, el.get('legMode') or 'unknown')
                    else:
                        bump(stuck, m)
                root.clear()
    except (OSError, ET.ParseError):
        return None
    for m in open_leg.values():
        bump(unresolved, m)
    return {'departures': dep, 'arrivals': arr, 'stuck': stuck,
            'duplicate_aborts': dup, 'unresolved': unresolved}


def integrity(history, events=None):
    """Whether departures = arrivals + stuck + unresolved, per mode.

    The counts come from the events stream when the final iteration's events
    file is on disk (`events_accounting`), because telemetry's own stuck
    attribution over-assigned end-of-day aborts and would have failed a run
    whose events conserve exactly (#54). The telemetry snapshot is the
    fallback for a run whose events file is gone, and where both instruments
    exist any disagreement between them is reported, never hidden.
    """
    block = {'iterations_recorded': len(history) or None,
             'basis': None,
             'conservation_closes': None, 'conservation_detail': {},
             'telemetry_write_failures': None, 'stuck': {}, 'unresolved': {},
             'duplicate_aborts': {}, 'telemetry_disagrees': {},
             'stuck_share_of_departures': None}
    last = history[-1] if history else {}
    if events is not None:
        block['basis'] = 'events'
        dep = events['departures']
        arr = events['arrivals']
        stk = events['stuck']
        unr = events['unresolved']
        block['duplicate_aborts'] = dict(events['duplicate_aborts'])
        # The instrument-vs-instrument check that found #54: the telemetry
        # snapshot saw the same stream, so a differing count means one of the
        # two attributions is wrong. Reported as a diagnostic, not gated - the
        # events-based identity above is the gate.
        for name, tele in (('departures', last.get('departures') or {}),
                           ('arrivals', last.get('arrivals') or {}),
                           ('stuck', last.get('stuck') or {})):
            src = {'departures': dep, 'arrivals': arr, 'stuck': stk}[name]
            for m in sorted(set(src) | set(k for k in tele if k != 'total')):
                if tele and src.get(m, 0) != tele.get(m, 0):
                    block['telemetry_disagrees'].setdefault(m, {})[name] = {
                        'events': src.get(m, 0), 'telemetry': tele.get(m, 0)}
    elif history:
        block['basis'] = 'telemetry'
        dep = last.get('departures') or {}
        arr = last.get('arrivals') or {}
        stk = last.get('stuck') or {}
        unr = last.get('unresolved') or {}
    else:
        return block
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
    stot = sum(v for k, v in stk.items() if k != 'total')
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

    integ = integrity(history, events_accounting(out_dir))
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
        A('Innovation off at iteration **%s** of %s. Drift is measured from '
          'iteration **%s** — the cutoff plus the declared settle margin of %s '
          '— because the cutoff itself carries a one-iteration selection snap '
          'that is not relaxation (`DECISIONS.md` §9.43).'
          % (rel.get('innovation_off_at'), r.get('iterations'),
             rel.get('from_iteration'), rel.get('settle_margin_iterations')))
        A('')
        A('| mode | snap at cutoff | drift %s → %s | cutoff → %s |'
          % (rel.get('from_iteration'), rel.get('to_iteration'),
             rel.get('to_iteration')))
        A('|---|---:|---:|---:|')
        for k in sorted(rel['drift_pp']):
            A('| %s | %s | **%+.2f pp** | %s |'
              % (k,
                 ('%+.2f pp' % rel['snap_pp'][k]) if k in rel.get('snap_pp', {})
                 else '—',
                 rel['drift_pp'][k],
                 ('%+.2f pp' % rel['cutoff_to_final_pp'][k])
                 if k in rel.get('cutoff_to_final_pp', {}) else '—'))
        A('')
        A('The middle column is the verdict. The last column is what the '
          'pre-§9.43 instrument reported: it includes the snap, which is why it '
          'failed at every horizon and for every run.')
        A('')

    if integ.get('conservation_detail'):
        A('## Accounting — every departure has an end')
        A('')
        if integ.get('basis') == 'events':
            A('Counted from the final iteration\'s own events stream, with each '
              'stuck event attributed to the person\'s open leg (#54). The '
              'telemetry snapshot is a second instrument over the same stream; '
              'where the two disagree it is reported below.')
        else:
            A('> ⚠️ Counted from the TELEMETRY snapshot — the events file is '
              'not on disk. Telemetry\'s stuck attribution is known to '
              'over-assign end-of-day aborts (#54), so a ❌ here may be the '
              'instrument, not the run.')
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
        dup = integ.get('duplicate_aborts') or {}
        if dup:
            A('**Duplicate aborts** — a second stuck event for a person whose leg '
              'was already terminated (the end-of-day netsim abort and an '
              'engine\'s afterMobsim abort both firing, #54). Counted, excluded '
              'from the identity above: %s.'
              % ', '.join('%s %d' % (m, dup[m]) for m in sorted(dup)))
            A('')
        dis = integ.get('telemetry_disagrees') or {}
        if dis:
            A('⚠️ **Telemetry disagrees with the events stream** on: %s. The '
              'events-based counts above are the gate; the disagreement is the '
              'instrument defect #54 tracks.'
              % '; '.join('%s (%s)' % (m, ', '.join(
                  '%s %d vs %d' % (f, dis[m][f]['events'], dis[m][f]['telemetry'])
                  for f in sorted(dis[m]))) for m in sorted(dis)))
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
