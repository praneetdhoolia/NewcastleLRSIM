#!/usr/bin/env python
"""P4 deliverable 6: the calibration report.

Proposal §8 deliverable 3 asks for *"fit statistics against all validation
targets, with honest reporting of where fit is poor"*. This writes that report
from one or more `_fit.json` files. It computes nothing new: every number here
was produced by `fit.py`, which reads the calibration half and cannot reach the
holdout. The report's job is to say what the numbers mean and, more importantly,
what they do not.

**It leads with what the fit cannot do.** A report that opens with a headline
error invites the reader to treat it as a score. This one opens with how many
targets were scored, how many could not be, and how much independent information
the scored ones actually carry - DECISIONS.md §12.1 puts it at roughly four
mode-share degrees of freedom, one patronage level and the counts.

**It reports constraints separately from targets, and never mixes them.** The
C4 occupancy and trip-length constraints are observables the model is checked
against but never fitted to. Presenting them beside the targets would let a
reader count them as evidence of fit; they are evidence of plausibility.

**It states which parameters moved and which could not.** A calibrated base
whose provenance is not stated is not reportable.

    python src/calibrate/report.py --run <tag> [--run <tag> ...] \
        --out docs/CALIBRATION_REPORT.md
"""
import os
import json
import argparse
import datetime

DEFAULT_OUT = 'docs/CALIBRATION_REPORT.md'
CAL = 'params/C5_calibration.json'


def load(tag):
    run_dir = tag if os.path.isdir(tag) else os.path.join('results', tag)
    path = os.path.join(run_dir, '_fit.json')
    if not os.path.exists(path):
        raise SystemExit('no _fit.json in %s - run fit.py first' % run_dir)
    return json.load(open(path, encoding='utf-8'))


def pct(x, nd=2):
    return '—' if x is None else ('%.*f' % (nd, x))


def section_scope(w, fits):
    w('## What this report is, and is not\n')
    f = fits[0]
    w('Every number below comes from `fit.py`, which reads **only** the '
      'calibration half of the pre-registered 67/143 split and raises if a '
      'holdout row survives its filter. **No holdout target has been read, at '
      'any point, by anything that produced this document.**\n')
    w('\n| | |\n|---|---:|\n')
    w('| Calibration targets available | %d |\n'
      % f['calibration_targets_available'])
    w('| Scored | **%d** |\n' % f['scored'])
    w('| Could not be scored, each with a reason | %d |\n' % f['unscored'])
    w('\nScoring %d of %d is **not** the same as fitting %d. DECISIONS.md §12.1 '
      'sets out why: several targets identify nothing in MATSim, several are '
      'duplicates or schedule inputs, and only the 2024/25 mode-share vintage '
      'applies to a 2026 base. The effective independent information is roughly '
      '**four mode-share degrees of freedom**, one patronage level, and the '
      'counts.\n' % (f['scored'], f['calibration_targets_available'],
                     f['calibration_targets_available']))
    w('\n**Traffic counts are scored and reported here but were not optimised '
      'against.** DECISIONS.md §9.14 and §9.15: the external tier carries no '
      'boundary through traffic, so every boundary-adjacent count is biased low '
      'by construction, and tuning the core network against them would '
      'compensate for demand the model does not contain.\n')


def section_runs(w, fits, tags):
    w('\n## The runs this report covers\n\n')
    w('| run | scenario | day | sample | iterations |\n|---|---|---|---:|---:|\n')
    for t, f in zip(tags, fits):
        w('| `%s` | %s | %s | %g%% | %d |\n'
          % (t, f['scenario'], f['day'], f['fraction'] * 100, f['iterations']))
    w('\n')
    if any(f['iterations'] < 500 for f in fits):
        w('> **Not a result.** DECISIONS.md §9.7 measured mode share still '
          'drifting after innovation was switched off at 250 iterations, so a '
          'run at or below that is short of relaxation. Issue #5 holds the '
          'iteration count open; nothing here is reportable as a converged '
          'model outcome.\n')


def section_mode_share(w, fits, tags):
    w('\n## Mode share — the one block that carries the objective\n\n')
    for t, f in zip(tags, fits):
        ms = f['mode_share']
        if not ms['errors']:
            continue
        w('**`%s`** — %d targets, mean absolute error **%.2f pp**\n\n'
          % (t, ms['n'], ms['mean_abs_pp']))
        w('| HTS category | modelled % | observed % | error (pp) |\n')
        w('|---|---:|---:|---:|\n')
        for e in ms['errors']:
            w('| %s | %.2f | %.2f | %+.2f |\n'
              % (e['hts_category'], e['modelled'], e['observed'],
                 e['abs_error']))
        w('\n')
    w('Five shares that sum to one carry four independent numbers. That is the '
      'ceiling on how many parameters a calibration against this block can '
      'identify, and `calibrate.py` enforces it rather than trusting anyone to '
      'remember it.\n')


def section_counts(w, fits, tags):
    w('\n## Traffic counts — scored, reported, not fitted\n\n')
    any_counts = False
    for t, f in zip(tags, fits):
        c = f['counts']
        if not c['n']:
            continue
        any_counts = True
        w('**`%s`** — %d stations, light-vehicle basis\n\n' % (t, c['n']))
        w('| statistic | value |\n|---|---:|\n')
        w('| mean percentage error | %+.1f%% |\n' % c['mean_pct_error'])
        w('| mean absolute percentage error | %.1f%% |\n'
          % c['mean_abs_pct_error'])
        w('| RMSE | %.0f vehicles (%.1f%% of mean observed) |\n'
          % (c['rmse'], c['rmse_pct_of_mean_observed']))
        w('| heavy-vehicle share assumed at | %d of %d stations |\n'
          % (c['heavy_share_assumed_at'], c['n']))
        if c['modelled_zero_stations']:
            w('\n**The model routes no traffic at all over %d station(s):** %s. '
              'These are scored at −100%%, not dropped: a modelled zero is a '
              'result, and the worst one in the set (issue #19). Dropping them '
              'flattered the fit by removing exactly where the model fails '
              'hardest.\n'
              % (len(c['modelled_zero_stations']),
                 ', '.join('`%s`' % s for s in c['modelled_zero_stations'])))
        w('\n')
    if not any_counts:
        w('No count station scored in these runs.\n')


def section_unscorable(w, fits, tags):
    w('\n## What could not be scored, and why\n\n')
    f = fits[0]
    groups = {}
    for u in f['unscorable']:
        groups.setdefault(u['reason'], []).append(u['target_id'])
    w('%d of the %d calibration targets could not be compared with this run. '
      'Each is named, because "fits %d targets" is a much stronger claim than '
      'this data supports.\n\n'
      % (len(f['unscorable']), f['calibration_targets_available'],
         f['calibration_targets_available']))
    w('| n | targets | why not |\n|---:|---|---|\n')
    for reason, ids in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        shown = ', '.join('`%s`' % i for i in sorted(ids)[:8])
        if len(ids) > 8:
            shown += ', … (%d more)' % (len(ids) - 8)
        w('| %d | %s | %s |\n' % (len(ids), shown, reason))


def section_constraints(w, fits, tags):
    w('\n## Constraints — checked, never fitted\n\n')
    w('These are observables the model is held against but **never optimised '
      'towards**. They are not part of the 67, they are not targets, and they '
      'are reported apart from the fit so they cannot be counted as evidence of '
      'it. A model can satisfy every one of them and still fit badly.\n\n')
    for t, f in zip(tags, fits):
        o = f.get('occupancy_constraint') or {}
        tg = f.get('trip_geometry_constraint') or {}
        if not o and not tg:
            continue
        w('**`%s`**\n\n' % t)
        if o:
            w('- Vehicle occupancy: modelled **%.4f** passengers per driver '
              'against an observed **%.4f** (range %s) — **%s**\n'
              % (o['modelled_passenger_per_driver'], o['observed'],
                 o['observed_sweep'],
                 'inside' if o['inside_observed_range'] else 'OUTSIDE'))
        if tg and tg.get('modes'):
            w('\n| mode | modelled km | observed km | ratio | in observed range |\n')
            w('|---|---:|---:|---:|---|\n')
            for m, g in sorted(tg['modes'].items()):
                w('| %s | %.2f | %.2f | %.2f | %s |\n'
                  % (m, g['modelled_mean_distance_km'],
                     g['observed_mean_distance_km'],
                     g['ratio_modelled_to_observed'],
                     'yes' if g['inside_observed_range'] else '**no**'))
            r = tg.get('ride_to_car_length_ratio')
            if r:
                w('\nRide-to-car trip length: modelled **%.3f** against observed '
                  '**%.3f**. A ratio is robust to the geography mismatch that '
                  'levels are not (§9.13).\n' % (r['modelled'], r['observed']))
        w('\n')


def section_provenance(w):
    w('\n## Parameter provenance\n\n')
    if not os.path.exists(CAL):
        w('**No calibration search has been run.** `%s` does not exist, so no '
          'parameter in this model has been moved by a calibration loop. Every '
          'value is its declared registry value, and the fit above is the fit '
          'of the *uncalibrated* base. This is stated rather than left to '
          'inference: P4 deliverable 5 is not met until that file exists.\n'
          % CAL)
        return
    c = json.load(open(CAL, encoding='utf-8'))
    w('From `%s`, written by `calibrate.py`.\n\n' % CAL)
    w('| | |\n|---|---|\n')
    w('| Objective | %s |\n' % ', '.join('`%s` x%.3g' % (k, v)
                                         for k, v in sorted(c['objective_components'].items())))
    w('| Independent numbers in it | %d |\n' % c['independent_targets'])
    w('| Free parameters | %s |\n'
      % (', '.join('`%s`' % k for k in c['free_parameters']) or 'none'))
    w('| Candidates evaluated | %d |\n' % len(c.get('history', [])))
    w('| Best objective | %s |\n' % pct(c.get('best_objective'), 4))
    w('\n**Calibrated values**\n\n| parameter | value |\n|---|---:|\n')
    for k, v in sorted((c.get('calibrated') or {}).items()):
        w('| `%s` | %g |\n' % (k, v))
    w('\nEvery parameter *not* listed above kept its declared registry value. '
      'The mode constants are unreachable from the loop by construction — they '
      'are `held_fixed` under DECISIONS.md §8.5, and proposal §9 names ASC '
      'absorption as the primary threat to validity.\n')


def section_poor_fit(w, fits, tags):
    w('\n## Where the fit is poor — stated plainly\n\n')
    f, t = fits[0], tags[0]
    bad = []
    ms = f['mode_share']
    for e in ms.get('errors', []):
        if abs(e['abs_error']) >= 5.0:
            bad.append('**%s** is %+.2f pp out (modelled %.2f against observed '
                       '%.2f)' % (e['hts_category'], e['abs_error'],
                                  e['modelled'], e['observed']))
    c = f['counts']
    if c['n'] and abs(c['mean_pct_error']) >= 20:
        bad.append('**traffic counts** average %+.1f%% across %d stations'
                   % (c['mean_pct_error'], c['n']))
    if c.get('modelled_zero_stations'):
        bad.append('**%d station(s) carry no modelled traffic at all**'
                   % len(c['modelled_zero_stations']))
    tg = f.get('trip_geometry_constraint') or {}
    for m, g in sorted((tg.get('modes') or {}).items()):
        if not g.get('inside_observed_range', True):
            bad.append('**%s trip length** is %.2f km against an observed '
                       '%.2f km' % (m, g['modelled_mean_distance_km'],
                                    g['observed_mean_distance_km']))
    if not bad:
        w('No mode share is more than 5 pp out, no count block averages more '
          'than 20%% out, and no constraint is violated, on `%s`.\n' % t)
        return
    w('On `%s`:\n\n' % t)
    for b in bad:
        w('- %s\n' % b)
    w('\nThese are reported because deliverable 3 asks for honest reporting of '
      'where fit is poor, not because they are surprising.\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--run', action='append', required=True)
    ap.add_argument('--out', default=DEFAULT_OUT)
    a = ap.parse_args()
    fits = [load(t) for t in a.run]
    tags = [f['run'] for f in fits]

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    buf = []
    w = buf.append
    w('# Calibration report\n\n')
    w('*Generated by `src/calibrate/report.py` on %s from `_fit.json`. '
      'Regenerate it; do not edit it.*\n\n'
      % datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d'))
    section_scope(w, fits)
    section_runs(w, fits, tags)
    section_mode_share(w, fits, tags)
    section_counts(w, fits, tags)
    section_constraints(w, fits, tags)
    section_unscorable(w, fits, tags)
    section_provenance(w)
    section_poor_fit(w, fits, tags)
    with open(a.out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(''.join(buf))
    print('wrote %s (%d runs)' % (a.out, len(fits)))


if __name__ == '__main__':
    main()
