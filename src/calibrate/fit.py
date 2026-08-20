#!/usr/bin/env python
"""Fit statistics against the CALIBRATION targets, and only those.

Proposal §8 deliverable 3 asks for *"fit statistics against all validation
targets, with honest reporting of where fit is poor"*. This computes the
calibration half. It is built so that the holdout half cannot be reached from
here: `load_targets()` filters `split == 'calibration'` at read time and raises
if anything else survives, so a holdout value is never in memory, never in an
intermediate, and never in the output.

**A modelled zero is scored, not dropped.** Where the model routes no traffic
over a link that carries observed volume, that is a *result* and the worst one
in the set - the M1 Pacific Motorway at Wyee is observed 48,016 and modelled 0.
Dropping it would flatter every aggregate below by removing the stations where
the model fails hardest, which is the inversion of proposal §8 deliverable 3.
Only a station that resolves to no link at all is unscorable, and the two cases
carry different reasons (issue 19).

**It reports what it could not score, as loudly as what it could.** A target with
no modelled counterpart is listed as `unscorable` with the reason, because
"fits 67 targets" is a much stronger claim than this data supports and
DECISIONS.md §12.1 sets out why: 13 of the 67 identify nothing in MATSim, several
are duplicates or schedule inputs, and only the 2024/25 mode-share vintage
applies to a 2026 base. The effective independent information is roughly four
mode-share degrees of freedom, one contemporary patronage level and 34 counts.

Every fit statistic carries the list of target ids it was computed over. A
statistic that does not name its targets is not reportable.
"""

# City-relative paths resolve through src/city.py: `data/...` names a
# location inside cities/<city>/, not inside the repository root.
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                  '..', '..', 'src'))
import city as _city  # noqa: E402
import argparse
import csv
import json
import math
import os

TARGETS = _city.path('data/processed/validation/validation_targets.csv')
C3 = _city.path('params/C3_count_comparison.json')
C4 = _city.path('params/C4_mode_constraints.json')

# MATSim mode -> the HTS category it is comparable with. `bike` carries HTS
# "Other", which also holds taxi/rideshare/carshare, wheelchair, bicycle and
# aircraft - the HTS data document's own list. Motorcycle is NOT in it: it sits
# inside Vehicle driver/passenger, so the car and ride targets silently contain
# motorcycles. An imperfect map, stated here rather than hidden in a lookup.
MODE_TO_HTS = {'car': 'Vehicle driver', 'ride': 'Vehicle passenger',
               'pt': 'Public transport', 'walk': 'Walk only', 'bike': 'Other'}
BASE_YEAR_HTS = '2024/25'


def load_targets():
    """Calibration rows only. The holdout is not read into this process."""
    with open(TARGETS, encoding='utf-8') as f:
        rows = [r for r in csv.DictReader(f) if r['split'] == 'calibration']
    stray = [r for r in rows if r['split'] != 'calibration']
    if stray:
        raise SystemExit('holdout rows leaked into the calibration set')
    return rows


def scale_error(modelled, observed):
    if observed in (None, 0) or modelled is None:
        return None
    return dict(modelled=round(modelled, 2), observed=round(observed, 2),
                abs_error=round(modelled - observed, 2),
                pct_error=round(100.0 * (modelled - observed) / observed, 2))


def score_mode_share(targets, metrics, out):
    """Linked main-mode share, Newcastle LGA, 2024/25 vintage only."""
    share = metrics['mode_share']['target_lga_pct']
    rows = [t for t in targets
            if t['metric'] == 'hts_mode_share' and t['period'] == BASE_YEAR_HTS]
    hts_to_mode = {v.lower(): k for k, v in MODE_TO_HTS.items()}
    used, errs = [], []
    for t in rows:
        mode = hts_to_mode.get(t['note'].strip().lower())
        if mode is None:
            out['unscorable'].append(dict(
                target_id=t['target_id'], metric=t['metric'], note=t['note'],
                reason='no MATSim mode corresponds to this HTS category '
                       '("Walk linked" is 0.0 by construction: the walk stage of '
                       'a PT trip is counted as PT in a linked mode share)'))
            continue
        modelled = share.get(mode, 0.0)
        if mode == 'car':
            # The HTS 'Vehicle driver' category CONTAINS motorcyclists (its
            # data document places them there, not in Other), and the model
            # now carves motorbike out of car-driver demand (DECISIONS.md
            # 9.52) - so the comparable modelled quantity is car + motorbike.
            # Comparing car alone would under-read the model by exactly the
            # declared carve.
            modelled += share.get('motorbike', 0.0)
        e = scale_error(modelled, float(t['value']))
        e.update(target_id=t['target_id'], hts_category=t['note'],
                 matsim_mode=(mode if mode != 'car' else 'car+motorbike'))
        errs.append(e)
        used.append(t['target_id'])
    for t in targets:
        if t['metric'] == 'hts_mode_share' and t['period'] != BASE_YEAR_HTS:
            out['unscorable'].append(dict(
                target_id=t['target_id'], metric=t['metric'], note=t['note'],
                reason='%s vintage: a different mode vocabulary from the base '
                       'year, and a pre-pandemic PT market (DECISIONS.md 12.1)'
                       % t['period']))
    return dict(targets=used, n=len(used), errors=errs,
                mean_abs_pp=round(sum(abs(e['abs_error']) for e in errs)
                                  / len(errs), 3) if errs else None)


def score_patronage(targets, metrics, out):
    """Light rail and bus boardings. Only the contemporary LR target applies."""
    used, errs = [], []
    lr_daily = metrics['pt']['light_rail_boardings']
    for t in targets:
        m, period = t['metric'], t['period']
        if m == 'lr_boardings_monthly_mean' and period.startswith('2025-07'):
            # a modelled weekday is not a month; a monthly figure needs all
            # three day types composed, which a single run cannot supply
            out['unscorable'].append(dict(
                target_id=t['target_id'], metric=m, note=period,
                reason='monthly total: needs WEEKDAY, SAT and SUN runs composed '
                       'over a calendar month. A single day-type run cannot be '
                       'compared with it'))
        elif m in ('lr_boardings_monthly_mean', 'lr_boardings_daily_mean',
                   'bus_boardings_monthly_mean', 'lr_share_of_local_pt_boardings'):
            out['unscorable'].append(dict(
                target_id=t['target_id'], metric=m, note=period,
                reason='Mar 2019 - Feb 2020 is a pre-pandemic PT market; the '
                       'base year is 2026 and PT mode share roughly halved '
                       '(DECISIONS.md 12). V002 is also V001 divided by 30.4, '
                       'and the 20.8% share is algebraically V001/(V001+V023)'
                if period.startswith('2019') else
                       'no modelled counterpart in a single day-type run'))
    return dict(targets=used, n=len(used), errors=errs,
                modelled_lr_weekday_boardings=lr_daily)


def score_counts(targets, metrics, corrections, out):
    """Two-way weekday vehicles at the permanent count stations."""
    by_station = {s['station_key']: s for s in metrics['counts']['stations']}
    heavy = corrections['heavy_vehicle_share']
    default_heavy = heavy['value']
    obs_heavy = {}
    with open(_city.path('data/processed/validation/road_aadt_targets.csv'),
              encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['heavy_share_source'] == 'observed' and r['heavy_share']:
                obs_heavy[r['station_key']] = float(r['heavy_share'])

    used, errs = [], []
    for t in targets:
        if t['metric'] != 'road_aadt':
            continue
        key = t['note'].split('station_key=')[1].split(';')[0]
        s = by_station.get(key)
        # Two different situations, and only one of them is unscorable. An
        # earlier cut collapsed them into a single branch and emitted the
        # "did not resolve to a link" reason for both, which was false for the
        # zero-volume stations AND dropped the worst misses out of the fit -
        # the M1 at Wyee is observed 48,016 and modelled 0 (issue 19).
        if s is None:
            out['unscorable'].append(dict(
                target_id=t['target_id'], metric=t['metric'], note=key,
                reason='station did not resolve to any link on the run network, '
                       'so the model carries no counterpart to compare '
                       '(outside the modelled area - issue 10)'))
            continue
        # the model has no freight, so the observed all-classes count is put on
        # a light-vehicle basis using the station's own share where classified
        hs = obs_heavy.get(key, default_heavy)
        observed_light = float(t['value']) * (1.0 - hs)
        e = scale_error(s['modelled_vehicles'], observed_light)
        e.update(target_id=t['target_id'], station_key=key,
                 observed_all_classes=float(t['value']),
                 heavy_share=round(hs, 4),
                 heavy_share_source='observed' if key in obs_heavy else 'assumed',
                 matched_by=s['matched_by'],
                 max_link_distance_m=s['max_distance_m'])
        # A modelled zero is a RESULT - the model routes no traffic over a link
        # that carries observed volume - not a target that cannot be scored. It
        # is flagged so it is visible rather than buried in an aggregate.
        if not s['modelled_vehicles']:
            e['modelled_zero'] = True
        errs.append(e)
        used.append(t['target_id'])
    if not errs:
        return dict(targets=[], n=0, errors=[])
    pe = [e['pct_error'] for e in errs]
    sq = [(e['modelled'] - e['observed']) ** 2 for e in errs]
    obs = [e['observed'] for e in errs]
    return dict(targets=used, n=len(used), errors=errs,
                mean_pct_error=round(sum(pe) / len(pe), 2),
                mean_abs_pct_error=round(sum(abs(x) for x in pe) / len(pe), 2),
                rmse=round(math.sqrt(sum(sq) / len(sq)), 1),
                rmse_pct_of_mean_observed=round(
                    100.0 * math.sqrt(sum(sq) / len(sq)) / (sum(obs) / len(obs)), 2),
                heavy_share_assumed_at=sum(1 for e in errs
                                           if e['heavy_share_source'] == 'assumed'),
                modelled_zero_stations=[e['target_id'] for e in errs
                                        if e.get('modelled_zero')])


def account_for_the_rest(targets, out):
    """Every calibration target is scored or explained. No silent third case.

    An earlier cut of this file scored 35 and listed 16 reasons out of 67,
    leaving 16 targets neither scored nor accounted for - the same failure the
    day-type check had (DECISIONS.md 9.9): a statistic that looks complete
    because nothing contradicts it. The reconciliation below is asserted, not
    assumed.
    """
    reasons = {
        'lr_cardtype_share':
            'MATSim has no fare-product dimension, and 31.7% of the observed '
            'mix is CTP - contactless payment, an instrument rather than a '
            'person attribute, so the mix is not decomposable into anything the '
            'model represents (DECISIONS.md 12.1)',
        'lr_scheduled_runtime':
            'a schedule INPUT: MATSim runs transit on the timetable, so it '
            'reproduces 12.00 min by construction. It is a SUMO corridor target, '
            'not a MATSim one',
        'lr_alignment_length':
            'network geometry, already satisfied by the P2 build; it identifies '
            'no behavioural parameter',
    }
    listed = {u['target_id'] for u in out['unscorable']}
    scored = set(out['mode_share']['targets'] + out['patronage']['targets']
                 + out['counts']['targets'])
    for t in targets:
        if t['target_id'] in listed or t['target_id'] in scored:
            continue
        out['unscorable'].append(dict(
            target_id=t['target_id'], metric=t['metric'], note=t['note'],
            reason=reasons.get(t['metric'],
                               'no modelled counterpart, and no reason recorded '
                               'for it - this is a gap in fit.py, not a property '
                               'of the target')))


def score_occupancy(metrics, c4):
    """Not a validation target: the physical constraint of DECISIONS.md 9.8."""
    share = metrics['mode_share']['target_lga_pct']
    # motorbike folds into the driver denominator for the same reason it
    # folds into the car mode-share row: the observed passenger:driver ratio
    # counts motorcyclists as drivers (DECISIONS.md 9.52)
    car = share.get('car', 0.0) + share.get('motorbike', 0.0)
    ride = share.get('ride', 0.0)
    if not car:
        return None
    modelled = ride / car
    lo, hi = c4['passenger_per_driver']['sweep']
    return dict(modelled_passenger_per_driver=round(modelled, 4),
                observed=c4['passenger_per_driver']['value'],
                observed_sweep=[lo, hi],
                inside_observed_range=bool(lo <= modelled <= hi),
                modelled_vehicle_occupancy=round(1.0 + modelled, 4),
                note='a constraint, not a validation target; it is not counted '
                     'in any fit statistic')


def score_trip_geometry(metrics, c4):
    """Not a validation target: is each mode used over the right RANGE?

    Mode share says how many people choose a mode; this says whether the trips
    they choose it for are the right length. A mode can hit its share exactly
    while being used for journeys it would never serve in reality.

    Both sides are Newcastle LGA. Comparing a five-LGA modelled mean against the
    Newcastle-LGA published mean is a geography error that flatters or damns a
    mode by accident - the same trap DECISIONS.md 12.1 flags for the seed.

    The RATIO between two modes is reported alongside the levels because it is
    robust to that geography: it survives whatever the trip-length distribution
    of the study area happens to be.
    """
    obs = (c4.get('trip_geometry') or {}).get('modes') or {}
    mod = (metrics.get('trip_geometry') or {}).get('by_mode') or {}
    if not obs or not mod:
        return None
    modes = {}
    for m, o in sorted(obs.items()):
        g = mod.get(m)
        if not g:
            continue
        lo, hi = o['avg_distance_sweep']
        km = g['mean_distance_km']
        modes[m] = dict(
            modelled_mean_distance_km=km,
            observed_mean_distance_km=o['avg_distance_km'],
            observed_distance_sweep=[lo, hi],
            inside_observed_range=bool(lo <= km <= hi),
            ratio_modelled_to_observed=round(km / o['avg_distance_km'], 4)
            if o['avg_distance_km'] else None,
            modelled_mean_time_min=g['mean_time_min'],
            observed_mean_time_min=o['avg_time_min'],
            trips=g['trips'])
    out = dict(geography=_city.descriptor()['mode_share_target']['geography'],
               modes=modes,
               note='a constraint, not a validation target; it is not counted '
                    'in any fit statistic. The 67/143 split is pre-registered '
                    'and this is not part of it')
    if 'ride' in modes and 'car' in modes and modes['car']['modelled_mean_distance_km']:
        mr = (modes['ride']['modelled_mean_distance_km']
              / modes['car']['modelled_mean_distance_km'])
        orr = (modes['ride']['observed_mean_distance_km']
               / modes['car']['observed_mean_distance_km'])
        out['ride_to_car_length_ratio'] = dict(
            modelled=round(mr, 4), observed=round(orr, 4),
            note='geography-robust: the level of either mode depends on the '
                 'study area, this ratio does not. Observed passenger trips are '
                 'slightly SHORTER than driver trips')
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', required=True)
    ap.add_argument('--out')
    a = ap.parse_args()
    run_dir = a.run if os.path.isdir(a.run) else os.path.join(_city.REPO, 'results', a.run)
    metrics = json.load(open(os.path.join(run_dir, '_metrics.json'),
                             encoding='utf-8'))
    corrections = json.load(open(C3, encoding='utf-8'))
    c4 = json.load(open(C4, encoding='utf-8'))
    targets = load_targets()

    out = dict(run=metrics['run'], scenario=metrics['scenario'],
               day=metrics['day'], fraction=metrics['fraction'],
               iterations=metrics['iterations'],
               overrides=metrics.get('overrides', {}),
               calibration_targets_available=len(targets),
               unscorable=[])
    out['mode_share'] = score_mode_share(targets, metrics, out)
    out['patronage'] = score_patronage(targets, metrics, out)
    out['counts'] = score_counts(targets, metrics, corrections, out)
    out['occupancy_constraint'] = score_occupancy(metrics, c4)
    out['trip_geometry_constraint'] = score_trip_geometry(metrics, c4)

    account_for_the_rest(targets, out)
    scored = (out['mode_share']['n'] + out['patronage']['n'] + out['counts']['n'])
    out['scored'] = scored
    out['unscored'] = len(targets) - scored
    if scored + len(out['unscorable']) != len(targets):
        raise SystemExit(
            'reconciliation failed: %d scored + %d explained != %d calibration '
            'targets. Every target must be one or the other.'
            % (scored, len(out['unscorable']), len(targets)))
    out['headline'] = (
        'Scored %d of the %d calibration targets. %d could not be scored; each '
        'is listed with a reason. Any statement of fit must name these targets '
        '- "fits 67 targets" is not what this measures (DECISIONS.md 12.1).'
        % (scored, len(targets), len(targets) - scored))

    path = a.out or os.path.join(run_dir, '_fit.json')
    json.dump(out, open(path, 'w'), indent=2)
    print(out['headline'])
    ms = out['mode_share']
    if ms['errors']:
        print('\nmode share, %s (percentage points):'
              % _city.descriptor()['mode_share_target']['geography'])
        for e in ms['errors']:
            print('  %-18s modelled %6.2f  observed %6.2f  error %+6.2f pp'
                  % (e['hts_category'], e['modelled'], e['observed'],
                     e['abs_error']))
        print('  mean absolute error %.2f pp over %d targets'
              % (ms['mean_abs_pp'], ms['n']))
    c = out['counts']
    if c['n']:
        print('\ntraffic counts (%d stations, light-vehicle basis):' % c['n'])
        print('  mean pct error %+.1f%%   mean abs pct error %.1f%%   '
              'RMSE %.0f (%.1f%% of mean observed)'
              % (c['mean_pct_error'], c['mean_abs_pct_error'], c['rmse'],
                 c['rmse_pct_of_mean_observed']))
        print('  heavy-vehicle share assumed at %d of %d stations'
              % (c['heavy_share_assumed_at'], c['n']))
        if c['modelled_zero_stations']:
            print('  MODELLED ZERO at %d station(s): %s - the model routes no '
                  'traffic over a link that carries observed volume. Scored at '
                  '-100%%, not dropped (issue 19)'
                  % (len(c['modelled_zero_stations']),
                     ', '.join(c['modelled_zero_stations'])))
    tg = out.get('trip_geometry_constraint')
    if tg:
        print('\ntrip geometry, %s (a constraint, never scored):'
              % _city.descriptor()['mode_share_target']['geography'])
        print('  %-5s %11s %11s %9s %8s' % ('mode', 'modelled km', 'observed km',
                                            'ratio', 'in range'))
        for m, g in sorted(tg['modes'].items()):
            print('  %-5s %11.2f %11.2f %9.2f %8s'
                  % (m, g['modelled_mean_distance_km'],
                     g['observed_mean_distance_km'],
                     g['ratio_modelled_to_observed'],
                     'yes' if g['inside_observed_range'] else 'NO'))
        r = tg.get('ride_to_car_length_ratio')
        if r:
            print('  ride:car trip length  modelled %.3f  observed %.3f  '
                  '(geography-robust)' % (r['modelled'], r['observed']))
    o = out['occupancy_constraint']
    if o:
        print('\noccupancy constraint (not a target): modelled %.4f passengers '
              'per driver vs observed %.4f, range %s -> %s'
              % (o['modelled_passenger_per_driver'], o['observed'],
                 o['observed_sweep'],
                 'inside' if o['inside_observed_range'] else 'OUTSIDE'))
    print('\n-> %s' % path)


if __name__ == '__main__':
    main()
