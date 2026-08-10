#!/usr/bin/env python
"""Integrity checks over the assembled data package.

Verifies that every artefact the proposal's Appendix A calls for exists, that
the GTFS variants are internally consistent, and that cross-layer references
resolve. Exits non-zero on failure so it can gate the next phase.
"""
import os
import sys
import csv
import json
import glob
import zipfile
import collections

FAIL = []
WARN = []
OK = []


def check(cond, msg, warn=False):
    (OK if cond else (WARN if warn else FAIL)).append(msg)
    return cond


def rows(p):
    with open(p, encoding='utf-8', errors='replace') as f:
        return list(csv.DictReader(f))


def n_rows(p):
    with open(p, encoding='utf-8', errors='replace') as f:
        return max(0, sum(1 for _ in f) - 1)


# ---- 1. required artefacts, keyed to the Appendix A schemas ----
REQUIRED = {
    'A1 road network': 'data/processed/network/A1_road_edges.csv',
    'A2 signals': 'data/processed/network/A2_signal_nodes_osm.csv',
    'A2 turn restrictions': 'data/processed/network/A2_turn_restrictions_osm.csv',
    'A2 corridor signal control': 'data/processed/corridor/A2_signal_control_corridor.csv',
    'A3 route extras': 'data/processed/schedule_extras/A3_route_extras.csv',
    'A3 stop extras': 'data/processed/schedule_extras/A3_stop_extras.csv',
    'A3 transfer extras': 'data/processed/schedule_extras/A3_transfer_extras.csv',
    'A4 vehicle spec': 'data/processed/corridor/A4_vehicle_spec.csv',
    'A4 dwell model': 'data/processed/corridor/A4_stop_dwell_model.csv',
    'A5 parking': 'data/processed/landuse/A5_parking_facilities.csv',
    'A6 active transport': 'data/processed/network/A6_footway_edges.csv',
    'B1 population': 'demand/population/B1_synthetic_population.csv',
    'B1 households': 'demand/population/B1_households.csv',
    'B2 activity trips': 'demand/plans/B2_activity_trips.csv',
    'B5 counts': 'data/processed/observed/traffic_aadt_newcastle.csv',
    'C1 parameters': 'params/C1_behavioural_parameters.csv',
    'C1 sweep grid': 'params/C1_sensitivity_sweep_grid.csv',
    'D1 frontages': 'data/processed/landuse/D1_frontage_segments.csv',
    'D1 POI': 'data/processed/landuse/D1_poi.csv',
    'D1 employment': 'data/processed/landuse/D1_employment_by_anzsic_POW_SA2.csv',
    'D1 zone attractions': 'data/processed/landuse/D1_zone_attractions_SA1.csv',
    'E1 scenarios': 'scenarios/E1_scenarios.csv',
    'E1 road variants': 'scenarios/E1_road_variants.csv',
    'Validation targets': 'data/processed/validation/validation_targets.csv',
    'Manifest': 'data/MANIFEST.json',
    'Decisions log': 'DECISIONS.md',
    'Data dictionary': 'docs/DATA_DICTIONARY.md',
}
for k, p in REQUIRED.items():
    check(os.path.exists(p) and os.path.getsize(p) > 100, '%s present (%s)' % (k, p))

# ---- 2. GTFS variants ----
GTFS = sorted(glob.glob('schedules/*.zip')) + sorted(glob.glob('schedules/scenarios/*.zip'))
check(len(GTFS) >= 14, 'at least 14 GTFS feeds present (found %d)' % len(GTFS))
for p in GTFS:
    try:
        z = zipfile.ZipFile(p)
        names = {n.split('/')[-1] for n in z.namelist()}
        need = {'stops.txt', 'routes.txt', 'trips.txt', 'stop_times.txt', 'calendar.txt'}
        check(need <= names, '%s has the required GTFS tables' % os.path.basename(p))

        def rd(n):
            import io
            with z.open([x for x in z.namelist() if x.endswith(n)][0]) as f:
                return list(csv.DictReader(io.TextIOWrapper(f, 'utf-8-sig')))
        stops = {s['stop_id'] for s in rd('stops.txt')}
        trips = {t['trip_id'] for t in rd('trips.txt')}
        routes = {r['route_id'] for r in rd('routes.txt')}
        trip_routes = {t['route_id'] for t in rd('trips.txt')}
        st = rd('stop_times.txt')
        bad_stop = {r['stop_id'] for r in st} - stops
        bad_trip = {r['trip_id'] for r in st} - trips
        check(not bad_stop, '%s: all stop_times reference known stops' % os.path.basename(p))
        check(not bad_trip, '%s: all stop_times reference known trips' % os.path.basename(p))
        check(trip_routes <= routes, '%s: all trips reference known routes' % os.path.basename(p))
        seq = collections.defaultdict(list)
        for r in st:
            seq[r['trip_id']].append(int(r['stop_sequence']))
        badseq = [t for t, s in seq.items() if len(set(s)) != len(s)]
        check(not badseq, '%s: stop_sequence unique within every trip (%d bad)'
              % (os.path.basename(p), len(badseq)))
        empty = trips - set(seq)
        check(not empty, '%s: every trip has stop_times (%d empty)'
              % (os.path.basename(p), len(empty)), warn=True)
    except Exception as e:
        check(False, '%s readable (%s)' % (p, e))

# ---- 3. scenario configs resolve ----
for r in rows('scenarios/E1_scenarios.csv'):
    g = r['gtfs_variant_ref']
    check(os.path.exists(g), 'scenario %s gtfs_variant_ref resolves (%s)' % (r['scenario_id'], g))
    check(os.path.exists(r['sensitivity_grid_ref']),
          'scenario %s sweep grid resolves' % r['scenario_id'])
    check(len(r['seed_list'].split(';')) == int(r['n_replications']),
          'scenario %s seed_list matches n_replications' % r['scenario_id'])
road_variants = {x['road_variant_ref'] for x in rows('scenarios/E1_road_variants.csv')}
park_variants = {x['parking_variant_ref'] for x in rows('scenarios/E1_parking_variants.csv')}
for r in rows('scenarios/E1_scenarios.csv'):
    check(r['road_variant_ref'] in road_variants,
          'scenario %s road_variant_ref defined' % r['scenario_id'])
    check(r['parking_variant_ref'] in park_variants,
          'scenario %s parking_variant_ref defined' % r['scenario_id'])

# ---- 4. cross-layer referential integrity ----
zl = {r['SA1_CODE21'] for r in rows('data/processed/zones/zones_SA1.csv')}
za = {r['SA1_CODE21'] for r in rows('data/processed/landuse/D1_zone_attractions_SA1.csv')}
check(za <= zl, 'zone attractions reference known SA1s')

core = {r['SA1_CODE21'] for r in rows('data/processed/zones/zones_SA1.csv')
        if r['zone_tier'] == 'core'}
hh_sa1 = set()
with open('demand/population/B1_households.csv', encoding='utf-8') as f:
    for i, r in enumerate(csv.DictReader(f)):
        hh_sa1.add(r['home_sa1'])
        if i > 200000:
            break
check(hh_sa1 <= core, 'sampled household home_sa1 all in the core tier')

# ---- 5. gradient coverage ----
gr = json.load(open('data/processed/network/_gradient_report.json'))
for k in ('roads', 'footways'):
    s = gr[k]
    check(s['sampled'] / max(s['n'], 1) > 0.99,
          'gradient attached to >99%% of %s (%d/%d)' % (k, s['sampled'], s['n']))

# ---- 6. parameter sweep completeness ----
sw = rows('params/C1_sensitivity_sweep_grid.csv')
tp = sorted({float(r['beta_transfer_penalty_min']) for r in sw})
check(min(tp) <= 3.0 and max(tp) >= 15.0,
      'transfer penalty swept across the full 3-15 min range (%s)' % tp)
check(sum(int(r['is_baseline']) for r in sw) == 1, 'exactly one baseline sweep point')
ch = sorted({float(r['dwell_charging_s']) for r in sw})
check(0.0 in ch, 'charging dwell sweep includes 0 (the S2a case)')

# ---- 7. validation split fixed ----
vt = rows('data/processed/validation/validation_targets.csv')
sp = collections.Counter(r['split'] for r in vt)
check(sp['holdout'] > 0 and sp['calibration'] > 0,
      'validation targets split into calibration (%d) and holdout (%d)'
      % (sp['calibration'], sp['holdout']))

# ---- 8. assumed values carry sweep ranges ----
c1 = rows('params/C1_behavioural_parameters.csv')
check(all(r.get('beta_transfer_penalty_low') and r.get('beta_transfer_penalty_high')
          for r in c1), 'every parameter set carries a transfer-penalty sweep range')
dw = rows('data/processed/corridor/A4_stop_dwell_model.csv')
check(all(r['source'] == 'assumed' and r['dwell_charging_sweep_low'] for r in dw),
      'charging dwell flagged assumed with a sweep range at every stop')

# ---- report ----
print('PASS %d' % len(OK))
for m in OK:
    print('  ok    %s' % m)
if WARN:
    print('\nWARN %d' % len(WARN))
    for m in WARN:
        print('  warn  %s' % m)
if FAIL:
    print('\nFAIL %d' % len(FAIL))
    for m in FAIL:
        print('  FAIL  %s' % m)
print('\n%s' % ('FAILURES PRESENT' if FAIL else 'ALL CHECKS PASSED'))
sys.exit(1 if FAIL else 0)
