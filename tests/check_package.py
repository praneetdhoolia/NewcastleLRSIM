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
import gzip
import re
import hashlib
import zipfile
import collections
import shutil
import time

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
    'B2 activity trips (weekday)': 'demand/plans/B2_activity_trips_WEEKDAY.csv',
    'B2 activity trips (Saturday)': 'demand/plans/B2_activity_trips_SAT.csv',
    'B2 activity trips (Sunday)': 'demand/plans/B2_activity_trips_SUN.csv',
    'B5 counts': 'data/processed/observed/traffic_aadt_newcastle.csv',
    'C1 parameters': 'params/C1_behavioural_parameters.csv',
    'C1 sweep grid': 'params/C1_sensitivity_sweep_grid.csv',
    'D1 frontages': 'data/processed/landuse/D1_frontage_segments.csv',
    'D1 POI': 'data/processed/landuse/D1_poi.csv',
    'D1 employment': 'data/processed/landuse/D1_employment_by_anzsic_POW_SA2.csv',
    'D1 zone attractions': 'data/processed/landuse/D1_zone_attractions_SA1.csv',
    'A1 corridor road edges': 'data/processed/network/A1_corridor_road_edges.csv',
    'A1 road variant patches': 'data/processed/network/A1_road_variant_patches.csv',
    'A2 turn restrictions resolved':
        'data/processed/network/A2_turn_restrictions_resolved.csv',
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
# The split is pre-registered at 67/143 and fixed before any scenario is run
# (DECISIONS.md 12, proposal s9). It is asserted exactly, not loosely: the point
# of pre-registering it is that it cannot drift, and a target value being
# corrected (as the road_aadt values were, DECISIONS.md 12.2) must not move a
# single target between the two sets.
CALIBRATION_N, HOLDOUT_N = 67, 143
vt = rows('data/processed/validation/validation_targets.csv')
sp = collections.Counter(r['split'] for r in vt)
check(sp['calibration'] == CALIBRATION_N and sp['holdout'] == HOLDOUT_N,
      'validation split is the pre-registered %d calibration / %d holdout '
      '(found %d / %d)' % (CALIBRATION_N, HOLDOUT_N,
                           sp['calibration'], sp['holdout']))
check(len(vt) == CALIBRATION_N + HOLDOUT_N,
      'validation target set is the pre-registered %d targets (found %d)'
      % (CALIBRATION_N + HOLDOUT_N, len(vt)))
check(len({r['target_id'] for r in vt}) == len(vt),
      'every validation target has a unique id')

# A traffic count is only a target if it says which period it is a count *of*.
# The first cut averaged ALL DAYS with the peak-period rows and produced a
# number with no physical meaning (DECISIONS.md 12.2), which no structural check
# could see because the arithmetic was internally consistent.
_aadt_t = [r for r in vt if r['metric'] == 'road_aadt']
check(bool(_aadt_t) and all('period=' in r['note'] for r in _aadt_t),
      'every road_aadt target names the period it was measured over (%d)'
      % len(_aadt_t))
check(all(r['unit'] == 'vehicles/weekday' for r in _aadt_t),
      'road_aadt targets are on a stated weekday basis, matching the day type '
      'the model runs')
_aadt_rows = rows('data/processed/validation/road_aadt_targets.csv')
check(all(r['heavy_share_source'] in ('observed', 'not_classified_at_this_station')
          for r in _aadt_rows),
      'every traffic-count station declares whether its heavy-vehicle share is '
      'observed or absent, so the freight the model omits is never silently '
      'assumed to be zero')
_obs_heavy = [r for r in _aadt_rows if r['heavy_share_source'] == 'observed']
check(all(0.0 < float(r['heavy_share']) < 0.5 for r in _obs_heavy),
      'observed heavy-vehicle shares are plausible (%d stations)'
      % len(_obs_heavy))

# The corrections applied when comparing a modelled link volume to an observed
# count are a parameter artefact, not prose, so the sweep-range rule applies to
# them like any other assumed value (DECISIONS.md 12.2a).
C3 = 'params/C3_count_comparison.json'
if check(os.path.exists(C3), 'count-comparison corrections present (%s)' % C3):
    c3 = json.load(open(C3, encoding='utf-8'))
    hv = c3.get('heavy_vehicle_share', {})
    check(hv.get('source', '').startswith('measured'),
          'heavy-vehicle share is measured from the classified counts, not '
          'assumed (%s)' % hv.get('source', '')[:60])
    lo, hi = (hv.get('sweep') or [None, None])
    check(lo is not None and hi is not None and lo < hv.get('value', -1) < hi,
          'heavy-vehicle share carries a sweep range that brackets its value '
          '(%s in %s)' % (hv.get('value'), hv.get('sweep')))
    obs_n = {float(r['heavy_share']) for r in _obs_heavy}
    check(bool(obs_n) and abs(min(obs_n) - lo) < 1e-6 and abs(max(obs_n) - hi) < 1e-6,
          'the heavy-vehicle sweep is the observed range across the classified '
          'stations, not a chosen interval')
    vp = c3.get('vehicles_per_leg', {})
    check(vp.get('car') == 1.0 and vp.get('ride') == 0.0
          and vp.get('source', '').startswith('derived'),
          'the modelled vehicle count is derived from observed occupancy - a '
          'car leg is one vehicle, a ride leg none, because observed vehicle '
          'trips are driver trips')

# The constraint on asc_car_passenger is a measured ratio of two published HTS
# counts, and the value it may take is bounded by what the survey observed -
# not by what would make the fit look good (DECISIONS.md 9.8).
C4 = 'params/C4_mode_constraints.json'
if check(os.path.exists(C4), 'observed mode constraints present (%s)' % C4):
    c4 = json.load(open(C4, encoding='utf-8'))
    check(c4.get('source', '').startswith('measured'),
          'vehicle occupancy is measured from HTS trip counts, not assumed')
    occ = c4.get('vehicle_occupancy', {})
    lo, hi = (occ.get('sweep') or [None, None])
    years = c4.get('by_year_newcastle', {})
    obs = sorted(v['occupancy'] for v in years.values())
    check(bool(obs) and abs(obs[0] - lo) < 1e-6 and abs(obs[-1] - hi) < 1e-6,
          'the occupancy sweep is the observed spread across all %d survey '
          'years, not a chosen interval' % len(obs))
    check(1.0 < occ.get('value', 0) < 5.0,
          'the occupancy constraint is physically possible (%.4f persons per '
          'car)' % occ.get('value', -1))
    check(c4.get('constrains') == 'asc_car_passenger'
          and 'asc_lr' in c4.get('constraint_rule', ''),
          'the constraint names the constant it binds and records that the PT '
          'constants are NOT touched, so the effect under test is untouched')

# ---- 8. assumed values carry sweep ranges ----
c1 = rows('params/C1_behavioural_parameters.csv')
check(all(r.get('beta_transfer_penalty_low') and r.get('beta_transfer_penalty_high')
          for r in c1), 'every parameter set carries a transfer-penalty sweep range')
dw = rows('data/processed/corridor/A4_stop_dwell_model.csv')
check(all(r['source'] == 'assumed' and r['dwell_charging_sweep_low'] for r in dw),
      'charging dwell flagged assumed with a sweep range at every stop')

# ---- 9. P2 network build: MATSim ----
#
# Everything from here needs the built network, which is gitignored and is
# regenerated by src/build/build_matsim_network.py and build_sumo_corridor.py.
# Absent, it warns rather than fails: this file also runs on a data-only checkout.
MATSIM = 'networks/matsim'
MREPORT = os.path.join(MATSIM, '_matsim_build_report.json')
if not os.path.exists(MREPORT):
    check(False, 'MATSim network built (run src/build/build_matsim_network.py)', warn=True)
else:
    mrep = json.load(open(MREPORT, encoding='utf-8'))
    base_net = os.path.join(MATSIM, 'base', 'network.xml.gz')
    check(os.path.exists(base_net), 'MATSim base network present')

    def read_links(path):
        """link id -> lanes / capacity / endpoints / osm way / marker flags."""
        with gzip.open(path, 'rt', encoding='utf-8') as f:
            xml = f.read()
        nodes = set(re.findall(r'<node id="([^"]+)"', xml))
        out = {}
        for m in re.finditer(r'<link\b.*?</link>', xml, re.S):
            blk = m.group(0)
            a = dict(re.findall(r'(\w[\w:]*)="([^"]*)"', blk[:blk.index('>')]))
            way = re.search(r'name="osm:way:id"[^>]*>(\d+)<', blk)
            out[a['id']] = dict(permlanes=a.get('permlanes'), capacity=a.get('capacity'),
                                frm=a.get('from'), to=a.get('to'),
                                way=way.group(1) if way else '',
                                kerb='kerbsideUse' in blk,
                                banned='disallowedNextLinks' in blk)
        return out, nodes

    base_links, base_nodes = read_links(base_net)

    dangling = [k for k, v in base_links.items()
                if v['frm'] not in base_nodes or v['to'] not in base_nodes]
    check(not dangling,
          'no MATSim link references a missing node (%d dangling)' % len(dangling))
    used = set()
    for v in base_links.values():
        used.add(v['frm'])
        used.add(v['to'])
    orphan_nodes = base_nodes - used
    check(not orphan_nodes, 'no orphan MATSim nodes (%d unattached)' % len(orphan_nodes))

    check(len(mrep.get('schedules', {})) == 15,
          'all 15 feeds mapped (5 era + 10 scenario), found %d'
          % len(mrep.get('schedules', {})))
    for feed, st in sorted(mrep.get('schedules', {}).items()):
        check(st['stops_without_link'] == 0,
              '%s: every GTFS stop maps to a network link (%d unmapped)'
              % (feed, st['stops_without_link']))
        check(st['artificial_share_pct'] < 5.0,
              '%s: artificial link share under 5%% (%.2f%%)'
              % (feed, st['artificial_share_pct']))
        sched = os.path.join(MATSIM, 'schedules', feed, 'transitSchedule.xml.gz')
        if not check(os.path.exists(sched), '%s: mapped schedule present' % feed):
            continue
        # The stop -> link assignment is the reproducible half of the mapping;
        # the route link sequences are not (DECISIONS.md 3.5). Assert the half
        # that is, against the recorded build of record.
        with gzip.open(sched, 'rt', encoding='utf-8') as f:
            sxml = f.read()
        pairs = sorted('%s\t%s' % (a, b) for a, b in re.findall(
            r'<stopFacility id="([^"]+)"[^>]*?linkRefId="([^"]+)"', sxml))
        fp = hashlib.sha256('\n'.join(pairs).encode('utf-8')).hexdigest()
        check(fp == st['stop_link_fingerprint'],
              '%s: stop->link fingerprint matches the build of record' % feed)

    # ---- 10. road variants differ only where E1 says they should ----
    patch_rows_m = rows('data/processed/network/A1_road_variant_patches.csv')
    patched_ways = collections.defaultdict(set)
    for r in patch_rows_m:
        patched_ways[r['road_variant_ref']].add(r['edge_id'][1:])
    for v in rows('scenarios/E1_road_variants.csv'):
        ref = v['road_variant_ref']
        vp = os.path.join(MATSIM, 'variants', ref, 'network.xml.gz')
        if not check(os.path.exists(vp), 'variant network present: %s' % ref):
            continue
        vlinks, vnodes = read_links(vp)
        check(set(vlinks) == set(base_links),
              '%s: same link set as base (topology unchanged)' % ref)
        check(vnodes == base_nodes, '%s: same node set as base' % ref)
        strayed = [k for k in vlinks
                   if k in base_links
                   and (vlinks[k]['permlanes'] != base_links[k]['permlanes']
                        or vlinks[k]['capacity'] != base_links[k]['capacity']
                        or vlinks[k]['kerb'] != base_links[k]['kerb']
                        or vlinks[k]['banned'] != base_links[k]['banned'])
                   and vlinks[k]['way'] not in patched_ways[ref]]
        check(not strayed,
              '%s: no link changed outside the E1 patch set (%d strayed)'
              % (ref, len(strayed)))
        if patched_ways[ref]:
            touched = [k for k in vlinks
                       if vlinks[k]['way'] in patched_ways[ref]
                       and (vlinks[k]['permlanes'] != base_links[k]['permlanes']
                            or vlinks[k]['kerb'] != base_links[k]['kerb'])]
            check(touched, '%s: the E1 patch set actually changed the network' % ref)
        else:
            check(all(vlinks[k] == base_links[k] for k in vlinks),
                  '%s: as-built variant is identical to the base network' % ref)

# ---- 11. P2 network build: SUMO corridor ----
SUMO = 'networks/sumo'
SREPORT = os.path.join(SUMO, '_sumo_build_report.json')
a2 = rows('data/processed/corridor/A2_signal_control_corridor.csv')
a2_by_variant = collections.defaultdict(list)
for r in a2:
    a2_by_variant[r['scenario_variant_ref']].append(r)
want_sig = {r['signal_variant_ref'] for r in rows('scenarios/E1_scenarios.csv')}
check(want_sig <= set(a2_by_variant),
      'every E1 signal_variant_ref defined in A2 (missing %s)'
      % sorted(want_sig - set(a2_by_variant)))

if not os.path.exists(SREPORT):
    check(False, 'SUMO corridor built (run src/build/build_sumo_corridor.py)', warn=True)
else:
    srep = json.load(open(SREPORT, encoding='utf-8'))
    check(srep.get('lefthand') is True, 'SUMO corridor built for left-hand traffic')
    for ref, v in sorted(srep.get('road_variants', {}).items()):
        net = os.path.join(SUMO, ref, 'corridor.net.xml')
        check(os.path.exists(net) and os.path.getsize(net) > 1000,
              'SUMO net present: %s' % ref)
        check(v['edges'] > 0 and v['junctions'] > 0,
              '%s: SUMO net has edges and junctions (%d / %d)'
              % (ref, v['edges'], v['junctions']))
        for sref, t in sorted(v.get('signal_variants', {}).items()):
            check(not t['pairing']['unmatched'],
                  '%s/%s: every A2 intersection matched a signalised junction'
                  % (ref, sref))
            check(t['programs_retimed'] == t['matched_junctions'],
                  '%s/%s: every matched junction retimed to the A2 cycle' % (ref, sref))
            check(t['matched_junctions'] == len(a2_by_variant.get(sref, [])),
                  '%s/%s: all %d A2 intersections present in the net'
                  % (ref, sref, len(a2_by_variant.get(sref, []))))
            target = float(t['cycle_time_s'])
            off = [c for c in t['realised_cycle_s'] if abs(float(c) - target) > 2]
            check(not off,
                  '%s/%s: realised cycle within 2 s of the A2 %.0f s cycle (%s)'
                  % (ref, sref, target, t['realised_cycle_s']))
            check(os.path.exists(os.path.join(SUMO, ref, 'tls_%s.add.xml' % sref)),
                  '%s/%s: TLS additional file present' % (ref, sref))

# ---- 12. corridor attribute provenance ----
corridor = rows('data/processed/network/A1_corridor_road_edges.csv')
SRC_FIELDS = ('num_lanes_source', 'speed_limit_source', 'oneway_source',
              'lane_width_source', 'kerbside_source', 'capacity_source')
check(all(all(r.get(f) for f in SRC_FIELDS) for r in corridor),
      'every corridor edge carries a per-field provenance flag')
check(all(r[f] in ('osm', 'imputed_rule', 'assumed', 'absent')
          for r in corridor for f in SRC_FIELDS),
      'corridor provenance flags use the declared vocabulary')
# The as-built corridor and the extension corridors are graded separately. The
# as-built lane counts are the ones the B3 net-arrivals test rests on and they
# are overwhelmingly observed; the S4/S5 extension corridors are derived from
# assumed stop sitings (DECISIONS.md 3.4), so their tagging rate is reported
# rather than asserted.
trunk = [r for r in corridor if 'corridor_trunk:base2026' in r['corridor_class']]
ext = [r for r in corridor if r['is_corridor_trunk'] == '1' and r not in trunk]
check(bool(trunk), 'as-built corridor trunk edges identified (%d)' % len(trunk))
obs = sum(1 for r in trunk if r['num_lanes_source'] == 'osm')
check(obs / max(len(trunk), 1) > 0.8,
      'as-built corridor lane counts are majority observed, not imputed '
      '(%d/%d = %.1f%%)' % (obs, len(trunk), 100.0 * obs / max(len(trunk), 1)))
ext_obs = sum(1 for r in ext if r['num_lanes_source'] == 'osm')
check(ext_obs / max(len(ext), 1) > 0.5,
      'extension corridor lane counts mostly observed (%d/%d = %.1f%%) - the '
      'extension alignment itself is assumed'
      % (ext_obs, len(ext), 100.0 * ext_obs / max(len(ext), 1)), warn=True)

patch_rows2 = rows('data/processed/network/A1_road_variant_patches.csv')
check(all(r['sweep_low'] and r['sweep_high']
          for r in patch_rows2 if r['source'] == 'assumed'),
      'every assumed road-variant patch carries a sweep range')
check(all(r['rationale'] for r in patch_rows2),
      'every road-variant patch states why it departs from the observed network')

restr = rows('data/processed/network/A2_turn_restrictions_resolved.csv')
check(len(restr) > 1000, 'turn restrictions resolved to coordinates (%d)' % len(restr))
check(any(r['corridor_flag'] == '1' for r in restr),
      'corridor turn restrictions located (%d within 40 m of the alignment)'
      % sum(1 for r in restr if r['corridor_flag'] == '1'))
check(all(r['located_by'] in ('via_node', 'via_way', 'from_way') for r in restr),
      'every resolved restriction records how it was located')

# ---- 13. toolchain pinned ----
TOOLCHAIN = '.tools/toolchain.json'
if not os.path.exists(TOOLCHAIN):
    check(False, 'toolchain bootstrapped (run src/setup/bootstrap_toolchain.py)', warn=True)
else:
    tcm = json.load(open(TOOLCHAIN, encoding='utf-8'))
    comps = {c['component']: c for c in tcm['components']}
    check({'jdk', 'pt2matsim', 'sumo'} <= set(comps),
          'all three tools recorded in the toolchain manifest')
    check(all(c.get('sha256') and c.get('version') and c.get('url')
              for c in comps.values()),
          'every tool pinned by version, source URL and sha256')


# ---- 12. P3 demand: activity chains (B2) ----
DAY_TYPES = ['WEEKDAY', 'SAT', 'SUN']
CHAIN_REPORT = 'demand/plans/_activity_chains_report.json'
if not os.path.exists(CHAIN_REPORT):
    check(False, 'B2 activity chains built (run src/build/build_activity_chains.py)',
          warn=True)
else:
    crep = json.load(open(CHAIN_REPORT, encoding='utf-8'))
    zl = {r['SA1_CODE21'] for r in rows('data/processed/zones/zone_lookup_SA1.csv')}
    core_tier = {r['SA1_CODE21'] for r in
                 rows('data/processed/zones/zone_lookup_SA1.csv')
                 if r['zone_tier'] == 'core'}

    # the old single-file B2 must be gone, not left beside the new one
    check(not os.path.exists('demand/plans/B2_activity_trips.csv'),
          'the superseded single-day B2_activity_trips.csv has been removed')

    for day in DAY_TYPES:
        p = 'demand/plans/B2_activity_trips_%s.csv' % day
        if not check(os.path.exists(p), 'B2 chains present for %s' % day):
            continue
        n = 0
        bad_zone = bad_time = bad_seq = open_tour = nhb_home = 0
        home_not_core = home_not_external = 0
        coords = set()
        purposes = collections.Counter()
        placement = collections.Counter()
        per_person = collections.defaultdict(list)
        with open(p, encoding='utf-8') as f:
            for r in csv.DictReader(f):
                n += 1
                purposes[r['purpose']] += 1
                placement[r['dest_placement']] += 1
                if r['origin_sa1'] not in zl or r['dest_sa1'] not in zl:
                    bad_zone += 1
                dep, arr = int(r['dep_time_s']), int(r['arr_time_s'])
                if arr <= dep or arr > 30 * 3600:
                    bad_time += 1
                if r['dest_activity_type'] != 'home':
                    coords.add((r['dest_x'], r['dest_y']))
                if r['purpose'] == 'NHB' and r['dest_activity_type'] == 'home':
                    nhb_home += 1
                if r['agent_tier'] == 'core':
                    per_person[(r['person_id'], r['tour_id'])].append(
                        (int(r['trip_seq']), r['dest_activity_type'], r['origin_sa1']))
                    # a tour starts at home, so leg 1's origin IS the home zone
                    if int(r['trip_seq']) == 1 and r['origin_sa1'] not in core_tier:
                        home_not_core += 1
                elif int(r['trip_seq']) == 1 and r['origin_sa1'] in core_tier:
                    home_not_external += 1
        # every tour must close at home, or MATSim gets an agent who never goes home
        for key, legs in per_person.items():
            legs.sort()
            if legs[-1][1] != 'home':
                open_tour += 1
        check(bad_zone == 0,
              '%s: every activity location resolves to a known SA1 (%d bad)'
              % (day, bad_zone))
        check(home_not_core == 0,
              '%s: every resident agent starts from a home zone in the core tier '
              '(%d outside it)' % (day, home_not_core))
        check(home_not_external == 0,
              '%s: every boundary agent starts from the external tier, not the '
              'core (%d inside it)' % (day, home_not_external))
        check(bad_time == 0,
              '%s: no leg arrives before it departs or after the 30 h horizon (%d bad)'
              % (day, bad_time))
        check(open_tour == 0,
              '%s: every tour closes at home (%d left open)' % (day, open_tour))
        check(nhb_home == 0,
              '%s: no return-home leg is labelled NHB (%d were, in P1 all of them)'
              % (day, nhb_home))
        # the P1 failure this replaces: 1,481 distinct destinations for 1.45M legs
        check(len(coords) > 20000,
              '%s: activity destinations are sub-zonal, not centroids (%d distinct)'
              % (day, len(coords)))
        share_poi = placement.get('poi', 0) / max(sum(placement.values())
                                                  - placement.get('home', 0), 1)
        check(share_poi > 0.85,
              '%s: %.1f%% of activity ends sit on an observed attractor'
              % (day, 100 * share_poi))
        check('home' not in purposes,
              '%s: no leg carries "home" as a trip purpose' % day)

    # trip rate must stay tied to the HTS, not drift with the assumptions
    wk = crep.get('realised_week_trip_rate', 0)
    hts = crep.get('hts_rate_per_person_day', 3.473)
    check(abs(wk - hts) / hts < 0.06,
          'realised week trip rate %.3f within 6%% of the HTS %.3f' % (wk, hts))
    for pnt, d in crep.get('decay', {}).items():
        got, want = d['realised_network_km'], d['hts_network_km']
        check(abs(got - want) / max(want, 1e-6) < 0.02,
              'gravity decay for %s reproduces the HTS journey distance '
              '(%.2f vs %.2f km)' % (pnt, got, want))
    ext = sum(v.get('external_agents', 0) for v in crep.get('by_day', {}).values())
    check(ext > 0,
          'the external boundary tier generates demand (%d agents across day types)'
          % ext)

# ---- 13. P3 demand: MATSim plans ----
PLANS_REPORT = 'demand/plans/matsim/_plans_report.json'
if not os.path.exists(PLANS_REPORT):
    check(False, 'MATSim plans built (run src/build/build_matsim_plans.py)', warn=True)
else:
    prep = json.load(open(PLANS_REPORT, encoding='utf-8'))
    hts_share = prep.get('hts_mode_share_pct', {})
    tgt_share = prep.get('hts_calibration_target_pct', {})
    check(bool(tgt_share) and 'linked' in prep.get('hts_calibration_target_source', ''),
          'the HTS calibration target is recorded as the linked Newcastle-LGA '
          'aggregate, derived from the HTS file rather than typed in')
    check(bool(prep.get('hts_mode_share_pct_source')),
          'the five-LGA unlinked HTS aggregate records which aggregation it is')
    for day, v in prep.get('by_day', {}).items():
        pth = 'demand/plans/matsim/population_%s.xml.gz' % day
        if not check(os.path.exists(pth), 'MATSim population present for %s' % day):
            continue
        check(v['activities'] == v['legs'] + v['persons'],
              '%s: activities = legs + persons, so every plan alternates '
              'activity/leg and closes (%d = %d + %d)'
              % (day, v['activities'], v['legs'], v['persons']))
        seed = v.get('seed_mode_share', {})
        check(abs(sum(seed.values()) - 1.0) < 1e-3,
              '%s: seed mode shares sum to 1' % day)
        # The seed must NOT sit on the calibration target. P3 positioned it
        # within 2 pp of the HTS aggregate as a convergence aid, which makes a
        # model that reproduces HTS indistinguishable from one that was handed
        # it. This check is the inversion of the one it replaces: the initial
        # condition has to be far enough from the target that arriving there is
        # evidence (DECISIONS.md 9.6).
        # anchored to the LINKED Newcastle-LGA aggregate, which is what
        # validation targets V202-V207 are and what a MATSim main-mode share is
        # comparable to - not to the unlinked five-LGA figure the P3 seed was
        # positioned against (DECISIONS.md 12.1)
        if tgt_share:
            car = 100 * seed.get('car', 0)
            check(abs(car - tgt_share['car']) > 20.0,
                  '%s: seed car share %.1f%% is far from the HTS calibration '
                  'target %.1f%%, so the mode-share calibration is not handed '
                  'its answer' % (day, car, tgt_share['car']))
        # Uniform over the modes each person MAY use, which is not the same as
        # uniform over all non-car modes: since DECISIONS.md 9.11, `ride` is
        # offered only to the 77.9% who have a household driver, so its seed
        # share is lower BY CONSTRUCTION. bike/pt/walk are available to everyone
        # and must still be uniform; ride must sit below them but not at zero.
        free = [v_ for k, v_ in seed.items() if k not in ('car', 'ride')]
        check(bool(free) and (max(free) - min(free)) < 0.02,
              '%s: the seed is uninformed - uniform over the modes available to '
              'everyone (spread %.4f)' % (day, (max(free) - min(free)) if free else -1))
        ride = seed.get('ride', 0)
        check(0 < ride < min(free) if free else False,
              '%s: seed ride share %.3f sits below the freely available modes '
              '(%.3f) because 22.1%% of the population has nobody to drive them, '
              'and is not zero (DECISIONS.md 9.11)'
              % (day, ride, min(free) if free else -1))
    check(False,
          'lastIteration is NOT validated: two 250-iteration runs at 1% were '
          'still drifting after innovation was switched off (DECISIONS.md 9.7). '
          'The shipped default of 100 is known to be too low and is left in '
          'place only because no justified replacement has been measured',
          warn=True)
    check(prep.get('seed_mode') == 'uninformed',
          'plans were built from the uninformed seed (found %r); the informed '
          'P3 seed stays available via --seed-mode informed so the seed '
          'dependence can be tested rather than asserted'
          % prep.get('seed_mode'))
    # the first line of the file has to be parseable as MATSim v6 population
    head = gzip.open('demand/plans/matsim/population_WEEKDAY.xml.gz',
                     'rt', encoding='utf-8').read(400)
    check('population_v6.dtd' in head,
          'plans declare the MATSim population_v6 DTD')

# ---- 14. P3 run inputs: one build, day types, patched run networks ----
RUN_REPORT = 'scenarios/matsim/_run_inputs_report.json'
if not os.path.exists(RUN_REPORT):
    check(False, 'MATSim run inputs built (run src/build/build_matsim_run_inputs.py)',
          warn=True)
else:
    rrep = json.load(open(RUN_REPORT, encoding='utf-8'))
    mrep2 = json.load(open('networks/matsim/_matsim_build_report.json',
                           encoding='utf-8'))
    sc = rrep.get('scenarios', {})
    check(len(sc) == 10, 'run inputs assembled for all 10 scenarios (found %d)'
          % len(sc))
    for sid, v in sorted(sc.items()):
        days = v.get('days', {})
        check(set(days) == set(DAY_TYPES),
              '%s: run inputs for all three day types' % sid)
        # The split must partition **departures**, not routes. Partitioning the
        # route set was true and useless: pt2matsim groups trips into a route by
        # stop sequence rather than by service, so a route is not day-type
        # homogeneous, and a filter keyed on the route id put 29.5% of S2's
        # departures in the wrong day type while still partitioning the routes
        # exactly. It also removed the light rail from every weekday run,
        # because both of its routes are named after a weekend trip - the
        # with-tram scenario had no tram on a weekday. DECISIONS.md 9.9.
        total_dep = sum(d['departures'] for d in days.values())
        src_dep = mrep2['schedules'].get(sid, {}).get('departures')
        if src_dep:
            check(total_dep == src_dep,
                  '%s: the day-type split partitions the mapped DEPARTURES '
                  'exactly (%d = %d)' % (sid, total_dep, src_dep))
        check(sum(d.get('departures_dropped', 0) for d in days.values())
              == 2 * total_dep,
              '%s: every departure is kept in exactly one day type and dropped '
              'from the other two' % sid)
        for d, c in sorted(days.items()):
            check(c['routes_kept'] > 0 and c['departures'] > 0,
                  '%s/%s: schedule retains services (%d routes, %d departures)'
                  % (sid, d, c['routes_kept'], c['departures']))
            check(c['vehicles'] == c['vehicle_refs'],
                  '%s/%s: every referenced transit vehicle is present (%d)'
                  % (sid, d, c['vehicles']))
            cfg = 'scenarios/matsim/%s/%s/config.xml' % (sid, d)
            if not check(os.path.exists(cfg),
                         '%s/%s: config.xml written' % (sid, d)):
                continue
            # Mode choice has to be able to choose. Until P4, `ride` was outside
            # subtourModeChoice's mode set, so a ride subtour was an absorbing
            # state and 18.6% of legs came out exactly equal to their seed - an
            # input wearing the costume of a result (DECISIONS.md 9.6).
            ctext = open(cfg, encoding='utf-8').read()

            def param(name, t=ctext):
                m = re.search(r'<param name="%s" value="([^"]*)"' % name, t)
                return m.group(1) if m else None

            smc = re.search(r'<module name="subtourModeChoice".*?</module>',
                            ctext, re.S)
            smc = smc.group(0) if smc else ''
            check(bool(smc) and 'ride' in (param('modes', smc) or ''),
                  '%s/%s: ride is inside the mode-choice set, so its share is an '
                  'output rather than its seed' % (sid, d))
            check(param('considerCarAvailability', smc) == 'true',
                  "%s/%s: mode choice respects B1's car availability" % (sid, d))
            check('ride' not in (param('mainMode') or ''),
                  '%s/%s: ride is not simulated in the mobsim - a car passenger '
                  'is not a second vehicle' % (sid, d))
            check('ride' in (param('networkModes') or ''),
                  '%s/%s: ride is routed on the road network, so it carries a '
                  'congested travel time rather than a beeline guess' % (sid, d))
            check(param('separateModes') == 'false',
                  '%s/%s: ride reads the car travel times, since no ride vehicle '
                  'is ever observed to generate its own' % (sid, d))
    # the E1 road variant means the same on the run network as on the base
    base_touch = mrep2.get('road_variants', {})
    for sid, v in sorted(sc.items()):
        ref = v['road_variant']
        want = base_touch.get(ref, {}).get('links_touched', {})
        got = v.get('links_touched', {})
        if want.get('banned_turns_removed') is not None:
            check(got.get('banned_turns_removed') == want['banned_turns_removed'],
                  '%s: banned turns dropped only on the corridor, as on the base '
                  'network (%s vs %s)'
                  % (sid, got.get('banned_turns_removed'),
                     want['banned_turns_removed']))
        if want.get('num_lanes_per_dir'):
            ratio = got.get('num_lanes_per_dir', 0) / want['num_lanes_per_dir']
            check(0.95 <= ratio <= 1.0,
                  '%s: lane patch reaches the run network (%d of %d base links; '
                  'the shortfall is pt-only links pt2matsim removed)'
                  % (sid, got.get('num_lanes_per_dir', 0),
                     want['num_lanes_per_dir']))

# ---- 15. P3: every PT stop the run needs resolves on the run network ----
# A MATSim plan does not name stops - a pt leg is <leg mode="pt"/> and the
# router picks stops at run time - so "every plan's PT legs reference stops that
# exist" resolves to this: every stop in the schedule a scenario will run must
# attach to a link that exists on that scenario's run network. Checked for all
# 30 combinations, not a sample: a dangling stop is exactly the kind of thing
# that appears in one scenario and not another.
#
# The same pass also asserts what P4 discovered the hard way: none of the 30
# sets could be loaded by MATSim at all (DECISIONS.md 9.4). Three separate
# defects, none of which any structural check was asking about, because every
# check treated the assembled files as data rather than as something a
# simulator has to read:
#
#   * the day-type filter round-tripped the schedule through ElementTree, which
#     drops the doctype - and MATSim selects its reader *from* the doctype;
#   * dropping two thirds of the routes orphaned the stop facilities and
#     minimal-transfer relations only they used, and SwissRailRaptor
#     dereferences a null array on the first one it meets;
#   * the kerbside patch appended a second <attributes> block to links that
#     already had one, which the network DTD rejects.
LINK_BLOCK = re.compile(r'<link\b.*?(?:/>|</link>)', re.S)
if os.path.exists(RUN_REPORT):
    total_dangling = total_orphan = total_dangling_rel = total_dup_attr = 0
    for sid in sorted(json.load(open(RUN_REPORT, encoding='utf-8'))
                      .get('scenarios', {})):
        net = 'scenarios/matsim/%s/network.xml.gz' % sid
        if not os.path.exists(net):
            continue
        with gzip.open(net, 'rt', encoding='utf-8') as f:
            net_xml = f.read()
        links = set(re.findall(r'<link id="([^"]+)"', net_xml))
        dup = sum(1 for m in LINK_BLOCK.finditer(net_xml)
                  if m.group(0).count('<attributes>') > 1)
        total_dup_attr += dup
        check(dup == 0,
              '%s: no link carries two <attributes> blocks on the run network '
              '(%d)' % (sid, dup))
        for day in DAY_TYPES:
            sch = 'scenarios/matsim/%s/%s/transitSchedule.xml.gz' % (sid, day)
            if not os.path.exists(sch):
                continue
            refs, missing = 0, 0
            declared, served, relations = set(), set(), []
            with gzip.open(sch, 'rt', encoding='utf-8') as f:
                head = f.readline() + f.readline()
                check('transitSchedule_v2.dtd' in head,
                      '%s/%s: schedule declares the transitSchedule_v2 DTD, '
                      'without which MATSim cannot choose a reader'
                      % (sid, day))
                for ln in [head] + list(f):
                    m = re.search(r'<stopFacility id="([^"]+)"[^>]*'
                                  r'linkRefId="([^"]+)"', ln)
                    if m:
                        refs += 1
                        declared.add(m.group(1))
                        if m.group(2) not in links:
                            missing += 1
                        continue
                    m = re.search(r'<stop refId="([^"]+)"', ln)
                    if m:
                        served.add(m.group(1))
                        continue
                    m = re.search(r'<relation fromStop="([^"]+)" '
                                  r'toStop="([^"]+)"', ln)
                    if m:
                        relations.append((m.group(1), m.group(2)))
            total_dangling += missing
            check(refs > 0 and missing == 0,
                  '%s/%s: every transit stop attaches to a link on the run '
                  'network (%d stops, %d dangling)' % (sid, day, refs, missing))
            orphan = declared - served
            total_orphan += len(orphan)
            check(not orphan,
                  '%s/%s: every declared stop facility is served by a route '
                  'that survived the day-type filter (%d orphaned)'
                  % (sid, day, len(orphan)))
            bad_rel = [r for r in relations
                       if r[0] not in served or r[1] not in served]
            total_dangling_rel += len(bad_rel)
            check(not bad_rel,
                  '%s/%s: every minimal-transfer relation references a served '
                  'stop (%d dangling of %d)'
                  % (sid, day, len(bad_rel), len(relations)))
    check(total_dangling == 0,
          'no dangling transit stop in any of the 30 scenario x day-type run '
          'input sets')

# ---- 15b. the intervention survives into every day type ----
# The generic partition check above is necessary and not sufficient: it counts
# departures without asking WHICH service they belong to. A scenario exists to
# test one intervention, and a day type that lost it is a run that measures
# nothing. This asserts the line is present with departures, per scenario per
# day type, which is the check that would have caught the light rail vanishing
# from every weekday run (DECISIONS.md 9.9).
INTERVENTION = {
    'S0': None,                       # counterfactual: no tram is correct
    'S1': 'S1SHUTTLE', 'S2': 'lightrail', 'S2a': 'lightrail', 'S2b': 'lightrail',
    'S2c': 'lightrail', 'S3': 'BRT', 'S4': 'lightrail', 'S5': 'lightrail',
    'S6': None,
}
LINE_RE = re.compile(r'<transitLine id="([^"]+)"[^>]*>')
if os.path.exists(RUN_REPORT):
    for sid, token in sorted(INTERVENTION.items()):
        if not token:
            continue
        for day in DAY_TYPES:
            sch = 'scenarios/matsim/%s/%s/transitSchedule.xml.gz' % (sid, day)
            if not os.path.exists(sch):
                continue
            hits, deps, inside = [], 0, False
            with gzip.open(sch, 'rt', encoding='utf-8') as f:
                for ln in f:
                    m = LINE_RE.search(ln)
                    if m:
                        inside = token.lower() in m.group(1).lower()
                        if inside:
                            hits.append(m.group(1))
                    elif inside and '<departure ' in ln:
                        deps += 1
            check(bool(hits) and deps > 0,
                  '%s/%s: the intervention (%s) is present with departures '
                  '(%d line(s), %d departures)'
                  % (sid, day, token, len(hits), deps))
    check(total_orphan == 0 and total_dangling_rel == 0 and total_dup_attr == 0,
          'the 30 assembled run input sets are referentially closed and '
          'DTD-valid, i.e. loadable by MATSim')


# ---- 16. P3: every assumed value carries a sweep range ----
# Proposal 8.1, quoted at the top of DECISIONS.md: "Every parameter chosen
# without direct empirical support must be recorded here with its rationale and
# its sweep range." That was discipline; this makes it a test. A parameter is
# exempt only if it is measured from an observed layer, in which case the report
# says where from.
if os.path.exists(CHAIN_REPORT):
    crep2 = json.load(open(CHAIN_REPORT, encoding='utf-8'))

    def has_range(v):
        return (isinstance(v, (list, tuple)) and len(v) == 2
                and all(x is not None for x in v) and v[0] != v[1])

    for key in ('sat_to_sun_sweep', 'p_mandatory_work_sweep',
                'p_mandatory_education_sweep', 'p_intermediate_sweep',
                'p_second_stop_sweep', 'child_tour_retention_sweep',
                'external_interaction_sweep', 'detour_sweep'):
        check(has_range(crep2.get(key)),
              'B2 assumed value carries a sweep range: %s = %s'
              % (key, crep2.get(key)))
    for key in ('day_purpose_mix_sweep', 'act_duration_sweep'):
        v = crep2.get(key)
        check(isinstance(v, (int, float)) and v > 0,
              'B2 assumed value carries a proportional sweep: %s = %s' % (key, v))

    # the factors that ARE measured must say so, and must not read as assumed
    check('measured' in str(crep2.get('detour_source', '')),
          'detour factor is measured from the road network, not assumed (%s)'
          % crep2.get('detour_source'))
    check('measured' in str(crep2.get('day_rate_shape_source', '')),
          'weekday/weekend split is measured from traffic counts, not assumed')

if os.path.exists(PLANS_REPORT):
    prep2 = json.load(open(PLANS_REPORT, encoding='utf-8'))
    check(isinstance(prep2.get('typical_duration_sweep'), (int, float))
          and prep2['typical_duration_sweep'] > 0,
          'typical activity durations carry a proportional sweep')
    sw = prep2.get('seed_mode_sweep', {})
    check(all(len(v) == 2 and v[0] != v[1] for v in sw.values()) and sw,
          'seed mode split carries sweep ranges (%s)' % sorted(sw))

if os.path.exists(RUN_REPORT):
    rrep2 = json.load(open(RUN_REPORT, encoding='utf-8'))
    sco = rrep2.get('scoring', {})
    for key in ('performing_sweep', 'monetary_distance_rate_sweep',
                'subtour_mode_choice_weight_sweep', 'transfer_penalty_sweep'):
        v = sco.get(key)
        check(isinstance(v, list) and len(v) == 2 and v[0] != v[1],
              'MATSim scoring assumed value carries a sweep range: %s = %s'
              % (key, v))
    check(len(sco.get('not_representable', [])) >= 3,
          'the C1 elements that do not survive translation to MATSim scoring '
          'are recorded (%d)' % len(sco.get('not_representable', [])))

# ---- 17. C2 measured factors ----
C2 = 'params/C2_network_factors.json'
if not os.path.exists(C2):
    check(False, 'C2 network factors measured (run src/build/measure_network_factors.py)',
          warn=True)
else:
    c2 = json.load(open(C2, encoding='utf-8'))
    d = c2.get('detour_factor', {})
    check(d.get('pairs_routed', 0) > 200,
          'detour factor measured over a usable sample (%d routed zone pairs)'
          % d.get('pairs_routed', 0))
    check(1.1 < d.get('value', 0) < 1.8,
          'measured detour factor is physically plausible (%.4f)' % d.get('value', 0))
    check(d['sweep'][0] < d['value'] < d['sweep'][1],
          'measured detour factor sits inside its own sweep range')
    dt = c2.get('day_type', {})
    check(dt.get('station_years', 0) > 100,
          'weekend/weekday ratio measured over a usable sample (%d station-years)'
          % dt.get('station_years', 0))
    check(0.5 < dt.get('weekend_to_weekday', 0) < 1.0,
          'measured weekend/weekday traffic ratio is plausible (%.4f)'
          % dt.get('weekend_to_weekday', 0))
    wa = c2.get('work_attendance', {})
    check('LOWER BOUND' in wa.get('source', ''),
          'census G62 attendance is used only as a sweep lower bound, never as '
          'a value (DECISIONS.md 2.4 rules G62 out as a behavioural rate)')


# ---- N. the input registry: every controllable value, declared ----
# The registry is the single controllable surface for every value the model
# consumes that is not read from an immutable raw download. These checks test
# the rules rather than trusting them: proposal 8.1 requires a rationale and a
# sweep range for every value chosen without direct empirical support, and the
# three unobtained inputs (DECISIONS.md 0, 13) must stay unpinned.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
try:
    import registry as _registry
    from registry import outputs as _outputs
except ImportError as _e:
    check(False, 'the input registry imports (%s)' % _e)
    _registry = None

if _registry is not None:
    _fields, _origin = _registry.load_registry()
    _errors = _registry.validate(_fields)
    check(not _errors,
          'every registry field is well formed (%d fields checked)%s'
          % (len(_fields), '' if not _errors else ': ' + '; '.join(_errors[:3])))

    # proposal 8.1, tested rather than trusted
    _floating = [k for k, f in _fields.items()
                 if f['source'] in ('measured', 'derived', 'literature', 'assumed')
                 and f.get('sweep') is None and 'held_fixed' not in f
                 and 'derived_from' not in f]
    check(not _floating,
          'no assumed or literature value floats without a sweep, a held-fixed rule '
          'or a derived identity (proposal 8.1)%s'
          % ('' if not _floating else ': ' + ', '.join(sorted(_floating)[:4])))

    _no_ref = [k for k, f in _fields.items()
               if f['source'] in ('measured', 'derived', 'literature', 'assumed')
               and not f.get('decisions_ref')]
    check(not _no_ref,
          'every non-observed value cites a DECISIONS.md section%s'
          % ('' if not _no_ref else ': ' + ', '.join(sorted(_no_ref)[:4])))

    # the three unobtained inputs stay unpinned (DECISIONS.md 0, 13; issue 15)
    _unobtained = sorted(k for k, f in _fields.items() if f['status'] == 'unobtained')
    for _key in ('A.signals.scats_phasing', 'A.lightrail.dwell_charging_s',
                 'B.opal.journey_linked'):
        check(_key in _unobtained,
              'the unobtained input %s is declared unobtained, not pinned' % _key)
    _pinned = [k for k in _unobtained if _fields[k].get('value') is not None]
    check(not _pinned,
          'no unobtained input carries a point value (%d unobtained fields)'
          % len(_unobtained))

    # the resolver actually refuses to hand one back
    _cfg = _registry.load()
    _leaked = []
    for _key in _unobtained:
        try:
            _cfg.get(_key)
            _leaked.append(_key)
        except _registry.RegistryError:
            pass
    check(not _leaked,
          'the resolver refuses to return a point value for an unobtained input%s'
          % ('' if not _leaked else ': ' + ', '.join(_leaked)))

    # DECISIONS.md 8.5: the mode constants are not tunable
    for _key in ('C.asc.light_rail', 'C.asc.bus', 'C.asc.rail'):
        check('held_fixed' in _fields.get(_key, {}),
              '%s is held fixed, so ASC absorption cannot happen through an overlay '
              '(DECISIONS.md 8.5, proposal 9)' % _key)

    # no layer may invent an input, escape a sweep or move a held constant
    for _label, _kw in (('an unknown field', dict(set={'C.asc.hovercraft': '1'})),
                        ('a value outside its sweep',
                         dict(set={'RUN.sample.fraction': '0.95'})),
                        ('a held-fixed constant', dict(set={'C.asc.light_rail': '-2.0'}))):
        try:
            _registry.load(**_kw)
            check(False, 'the resolver rejects %s' % _label)
        except _registry.RegistryError:
            check(True, 'the resolver rejects %s' % _label)

    # every scenario in the matrix has an overlay, and it resolves
    _scenarios = _fields['E.matrix.scenario_ids']['value']
    for _sid in _scenarios:
        _path = os.path.join('config', 'scenarios', '%s.json' % _sid)
        if not check(os.path.exists(_path), 'scenario %s has a config overlay' % _sid):
            continue
        try:
            _registry.load(scenario=_sid)
            check(True, 'scenario overlay %s resolves against the registry' % _sid)
        except _registry.RegistryError as _e:
            check(False, 'scenario overlay %s resolves against the registry (%s)'
                  % (_sid, str(_e).replace('\n', ' ')[:90]))
    for _day in _fields['E.matrix.day_types']['value']:
        check(os.path.exists(os.path.join('config', 'day', '%s.json' % _day)),
              'day type %s has a config overlay' % _day)

    # an out-of-sweep overlay value must carry a written justification
    for _sid in _scenarios:
        _doc = json.load(open(os.path.join('config', 'scenarios', '%s.json' % _sid),
                              encoding='utf-8'))
        for _k in _doc.get('allow_outside_sweep', []):
            check(bool(_doc.get('justification', {}).get(_k)),
                  'scenario %s justifies setting %s outside its sweep' % (_sid, _k))

    # the generated reference cannot drift from the values it documents
    _docs = os.path.join('docs', 'CONFIG_REFERENCE.md')
    if check(os.path.exists(_docs), 'docs/CONFIG_REFERENCE.md exists'):
        import subprocess as _sp
        _rc = _sp.call([sys.executable, os.path.join('src', 'registry', 'render_docs.py'),
                        '--check'], stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
        check(_rc == 0,
              'docs/CONFIG_REFERENCE.md is current with the registry '
              '(regenerate: python src/registry/render_docs.py)')

    # the output contract exists for every artefact the pipeline writes
    for _kind, _name in sorted(_outputs.KINDS.items()):
        check(os.path.exists(os.path.join('config', 'schema', 'outputs', _name)),
              'the %s output carries a declared schema' % _kind)

    # any run already on disk must meet its contract
    for _rec in sorted(glob.glob(os.path.join('results', '*', '_run.json'))):
        _problems = _outputs.validate_file(_rec)
        check(not _problems, 'run record %s meets the run contract%s'
              % (os.path.basename(os.path.dirname(_rec)),
                 '' if not _problems else ': ' + _problems[0][:80]))

    # The C-layer behavioural values live in TWO places: config/registry/ declares
    # them, and params/C1_parameters.json is what build_matsim_run_inputs.py
    # actually reads. check_legacy_drift.py pins the registry to source
    # CONSTANTS, not to a params file, so this pair was unpinned and could drift
    # apart silently - two copies of a number is the drift this package cannot
    # absorb. The registry copy is a mirror; C1 is what reaches the model.
    _C1_PAIRS = {
        'C.transfer.beta_transfer_penalty_min': ('transfer_penalty', 'base'),
        'C.gradient.uphill_penalty_per_pct': ('weights', 'beta_gradient_uphill', 'base'),
        'C.gradient.downhill_penalty_per_pct': ('weights', 'beta_gradient_downhill', 'base'),
        'C.crowding.seated_multiplier': ('weights', 'beta_crowding_seated', 'base'),
        'C.crowding.standing_multiplier': ('weights', 'beta_crowding_standing', 'base'),
        'C.time_weights.beta_ivt': ('weights', 'beta_ivt', 'base'),
        'C.time_weights.beta_wait': ('weights', 'beta_wait', 'base'),
        'C.time_weights.beta_walk_access': ('weights', 'beta_walk_access', 'base'),
        'C.time_weights.beta_walk_egress': ('weights', 'beta_walk_egress', 'base'),
        'C.time_weights.beta_headway': ('weights', 'beta_headway', 'base'),
        'C.time_weights.beta_reliability': ('weights', 'beta_reliability', 'base'),
    }
    if os.path.exists('params/C1_parameters.json'):
        _c1 = json.load(open('params/C1_parameters.json', encoding='utf-8'))
        _bad = []
        for _k, _path in sorted(_C1_PAIRS.items()):
            _node = _c1
            for _bit in _path:
                _node = _node.get(_bit) if isinstance(_node, dict) else None
                if _node is None:
                    break
            _rv = _fields.get(_k, {}).get('value')
            if _node is None or not isinstance(_rv, (int, float)):
                _bad.append('%s: no comparable C1 value' % _k)
            elif abs(float(_rv) - float(_node)) > 1e-9:
                _bad.append('%s: registry %s vs C1 %s' % (_k, _rv, _node))
        check(not _bad,
              'the C-layer behavioural values agree between config/registry/ and '
              'params/C1_parameters.json, which is the copy build_matsim_run_inputs.py '
              'actually reads%s' % ('' if not _bad else ': ' + '; '.join(_bad[:3])))

    # the two capacity factors that were previously set in code with no rationale
    _sce = _fields['RUN.sample.storage_capacity_exponent']
    check(_sce.get('value') == 1.0 and 'derived_from' in _sce and _sce.get('sweep') is None,
          'the storage capacity exponent is derived and pinned at 1.0, not swept: MATSim '
          'rejects a storage factor different from the flow factor, so a sweep here would '
          'declare values the tool will not accept (DECISIONS.md 15)')
    check('derived_from' in _fields['RUN.sample.flow_capacity_factor'],
          'the flow capacity factor states the identity it is derived from')

    # no numeric model constant has escaped back into the run/analysis layer
    try:
        from registry import extract_legacy_constants as _elc
        _escaped = []
        for _sub in ('run', 'calibrate', 'analyse'):
            _d = os.path.join('src', _sub)
            if not os.path.isdir(_d):
                continue
            for _fn in sorted(os.listdir(_d)):
                if not _fn.endswith('.py'):
                    continue
                for _n, _rec2 in _elc.scan_file(os.path.join(_d, _fn)).items():
                    if _rec2['kind'] == 'parameter' and _n not in ('SEED',):
                        _escaped.append('%s/%s:%s' % (_sub, _fn, _n))
    except Exception:
        _escaped = None
    if _escaped is not None:
        check(not _escaped,
              'no model parameter is hard-coded in src/run, src/calibrate or '
              'src/analyse - they read the registry%s'
              % ('' if not _escaped else ': ' + ', '.join(_escaped[:4])), warn=True)



    # ---- the SUMO corridor layer reads the registry ----
    # build_sumo_corridor.py no longer holds its own constants. The options that
    # are MODELLING CHOICES are named fields rather than entries in a flag list,
    # so a choice cannot hide inside one (DECISIONS.md 15).
    for _key in ('RUN.sumo.lefthand', 'RUN.sumo.tls_default_type',
                 'RUN.sumo.junctions_join', 'RUN.sumo.tls_guess_signals',
                 'RUN.sumo.tls_join', 'RUN.sumo.no_turnarounds',
                 'RUN.sumo.crossings_enabled', 'RUN.sumo.spreadtype'):
        check(_key in _fields,
              'the netconvert modelling choice %s is a named registry field, not a '
              'flag buried in a list' % _key)

    # left-hand traffic is not cosmetic: with it off every turning movement is wrong
    check(_fields.get('RUN.sumo.lefthand', {}).get('value') is True,
          'SUMO builds left-hand traffic')

    # the crossings segfault is a recorded TOOL DEFECT, not a modelling judgement
    _cross = _fields.get('RUN.sumo.crossings_enabled', {})
    check(_cross.get('value') is False and 'segfault' in _cross.get('description', '').lower(),
          'pedestrian crossings are off because --osm.crossings segfaults netconvert '
          '1.27.1, and the field says so - so pedestrian delay is not modelled in SUMO '
          '(DECISIONS.md 3.6)')

    # the assembled option list must reproduce what the literal list used to be:
    # the registry refactor is inert, and the corridor nets rebuild byte-identically
    _expected_opts = ['--lefthand', '--osm.turn-lanes', 'true', '--osm.elevation', 'false',
                      '--geometry.remove', 'true', '--roundabouts.guess', 'true',
                      '--ramps.guess', 'true', '--junctions.join', 'true',
                      '--tls.guess-signals', 'true', '--tls.join', 'true',
                      '--tls.default-type', 'actuated', '--no-turnarounds', 'true',
                      '--default.spreadtype', 'roadCenter']
    try:
        sys.path.insert(0, os.path.join('src', 'build'))
        sys.path.insert(0, os.path.join('src', 'setup'))
        import build_sumo_corridor as _bsc
        check(_bsc.PLAIN_OPTS == _expected_opts,
              'the registry assembles netconvert options identical to the literal list '
              'they replaced, in the same order - so the corridor nets rebuild unchanged')
        check(_bsc.SEED == _fields['RUN.sumo.seed']['value']
              and _bsc.BBOX_MARGIN_M == _fields['RUN.sumo.bbox_margin_m']['value']
              and _bsc.MIN_GREEN_S == _fields['A.signals.min_green_s']['value'],
              'the SUMO build reads its seed, corridor margin and minimum green from '
              'the registry')
    except Exception as _e:
        check(False, 'the SUMO build imports and reads the registry (%s)' % _e)

    # a SUMO RUN is declared but does not exist: the nets have never been simulated
    check(_fields.get('RUN.sumo.replications', {}).get('status') == 'unobtained',
          'SUMO replications carry no value - proposal 5.2 asks for at least 30, the '
          'measured run budget does not fit, and the cut has not been made (issue 6)')
    # P4 deliverable 7 defined this (DECISIONS.md 9.16). The check is the
    # INVERSION of the one it replaces, which asserted the tolerance was still
    # null so a loop could not be built on an unexamined default: now it must
    # carry a value, a rule holding it fixed, and the self-policing bound that
    # says what to do if a comparison ever turns on a difference it cannot
    # resolve. A number without that bound would be exactly the unexamined
    # default the old check existed to prevent.
    _tol = _fields.get('E.coupling.outer_loop_tolerance_s', {})
    check(isinstance(_tol.get('value'), (int, float)) and _tol['value'] > 0
          and 'held_fixed' in _tol
          and 'departure_requires' in _tol.get('held_fixed', {})
          and _tol.get('status') == 'active',
          'the MATSim-SUMO outer-loop tolerance is DEFINED (%s s), held fixed with a '
          'stated rule, and carries the bound that forces a re-run if a reported '
          'comparison ever turns on a difference smaller than twice it (issue 8, '
          'P4 deliverable 7)' % _tol.get('value'))


    # A `consumers` entry is a MACHINE-READABLE CLAIM that a named file reads the
    # field. An untrue one is worse than none: it makes a value look wired up when
    # nothing reads it, which is precisely the drift the registry exists to stop.
    # Ten fields declared in 9.13 claimed two readers that read the C4 artefact
    # instead; caught by this check, which is why it exists.
    _lies = []
    for _k, _v in sorted(_fields.items()):
        for _c in _v.get('consumers') or []:
            if not os.path.exists(_c):
                _lies.append('%s -> %s (no such file)' % (_k, _c))
            elif _k not in open(_c, encoding='utf-8', errors='replace').read():
                _lies.append('%s -> %s (does not reference the key)' % (_k, _c))
    check(not _lies,
          'every registry `consumers` entry is TRUE - the named file exists and '
          'actually references the field key (%d claims across %d fields)%s'
          % (sum(len(v.get('consumers') or []) for v in _fields.values()),
             sum(1 for v in _fields.values() if v.get('consumers')),
             '' if not _lies else ': ' + _lies[0]))

    # the build layer has NOT been migrated: those scripts still hold their own
    # constants and the registry declares the same values. Two copies of a number
    # is exactly the drift this package cannot absorb, so they are pinned together
    # by test until the migration lands.
    try:
        from registry import check_legacy_drift as _drift
        _dp, _dn, _dd, _ds = _drift.compare(_fields)
        check(not _dp,
              'every registry field still agrees with the constant it replaced '
              '(%d compared, %d deliberately diverge, %d not literals)%s'
              % (_dn, _dd, _ds, '' if not _dp else ': ' + _dp[0][:110]))
    except ImportError as _e:
        check(False, 'the legacy-drift check imports (%s)' % _e)


# ---- O. the fit statistic itself (src/calibrate/fit.py) ----
#
# Deliverable 3 had NO test coverage, and that is how issue 19 survived: a defect
# that silently IMPROVED the reported fit, in code the whole suite never touched.
# These checks drive fit.py's scoring functions on SYNTHETIC metrics, so they need
# no completed run - `results/` is gitignored and a check may not depend on one.
if True:
    sys.path.insert(0, os.path.join('src', 'calibrate'))
    try:
        import fit as _fit
    except ImportError as _e:
        check(False, 'src/calibrate/fit.py imports (%s)' % _e)
        _fit = None

    if _fit is not None:
        _tg = _fit.load_targets()
        check(all(t['split'] == 'calibration' for t in _tg),
              'fit.py load_targets() returns calibration rows ONLY - the holdout '
              'is never read into the process, so it cannot reach an intermediate '
              'or an output (%d rows)' % len(_tg))

        _all_splits = {r['split'] for r in rows(
            'data/processed/validation/validation_targets.csv')}
        check(_all_splits == {'calibration', 'holdout'} and len(_tg) == 67,
              'the 67/143 pre-registered split is intact and fit.py sees exactly '
              'the 67 (%d of %d rows)' % (len(_tg), 210))

        _road = [t for t in _tg if t['metric'] == 'road_aadt']
        _key = lambda t: t['note'].split('station_key=')[1].split(';')[0]
        _corr = json.load(open('params/C3_count_comparison.json', encoding='utf-8'))

        def _fit_counts(station_overrides):
            """Run score_counts against a synthetic metrics block."""
            stations = [dict(station_key=_key(t), split='calibration',
                             road_name='x', links='1', matched_by='name_and_proximity',
                             max_distance_m=10.0,
                             modelled_vehicles=station_overrides.get(_key(t), 5000))
                        for t in _road if _key(t) in station_overrides
                        or station_overrides.get('_all')]
            out = dict(unscorable=[])
            block = _fit.score_counts(_road, dict(counts=dict(stations=stations)),
                                      _corr, out)
            return block, out

        # issue 19, regression: a modelled ZERO is a RESULT and must be scored.
        _zero_key = _key(_road[0])
        _blk, _out = _fit_counts({'_all': True, _zero_key: 0})
        _scored_zero = [e for e in _blk['errors'] if e['target_id'] == _road[0]['target_id']]
        check(bool(_scored_zero) and _scored_zero[0]['pct_error'] == -100.0,
              'issue 19: a station the model routes ZERO traffic over is SCORED at '
              '-100%, not dropped - dropping it flattered every aggregate by '
              'removing the stations where the model fails hardest')
        check(_road[0]['target_id'] in _blk['modelled_zero_stations'],
              'issue 19: a modelled zero is NAMED in counts.modelled_zero_stations '
              'rather than buried inside the aggregate')
        check(not any(u['target_id'] == _road[0]['target_id']
                      for u in _out['unscorable']),
              'issue 19: a modelled zero is no longer reported as unscorable')

        # the other branch, which is genuinely unscorable, and its reason must not
        # claim the zero-volume cause.
        _blk2, _out2 = _fit_counts({_key(_road[1]): 5000})
        _missing = [u for u in _out2['unscorable']
                    if u['target_id'] == _road[0]['target_id']]
        check(bool(_missing) and 'did not resolve to any link' in _missing[0]['reason'],
              'issue 19: a station that resolves to NO link is unscorable, and says '
              'so in its own words - the two causes no longer share one reason string')

        check(_blk['n'] == len(_blk['targets']) and _blk['targets'],
              'every fit block names the target ids it was computed over; a '
              'statistic that does not name its targets is not reportable '
              '(DECISIONS.md 12.1)')

        # the reconciliation fit.py asserts at run time, asserted here too
        _sc = len(_blk['targets'])
        check(_sc + len([u for u in _out['unscorable']
                         if u['metric'] == 'road_aadt']) == len(_road),
              'scored + unscorable reconciles over the road_aadt block (%d + %d '
              '= %d), so no target is silently neither' %
              (_sc, len(_road) - _sc, len(_road)))

        check(_fit.scale_error(0, 100.0) is not None
              and _fit.scale_error(5.0, 0) is None,
              'scale_error scores a modelled zero and refuses an OBSERVED zero - '
              'the asymmetry is deliberate, a zero denominator has no percentage')

        # DECISIONS.md 9.13: trip length by mode is a CONSTRAINT and must never
        # become a target. The 67/143 split is pre-registered.
        _c4 = json.load(open('params/C4_mode_constraints.json', encoding='utf-8'))
        _tg = (_c4.get('trip_geometry') or {}).get('modes') or {}
        check(set(_tg) == {'car', 'ride', 'pt', 'walk', 'bike'},
              'C4 carries observed trip length and time for all five MATSim modes, '
              'measured from the HTS TRIP_AVG_DISTANCE/TRIP_AVG_TIME columns that '
              'nothing used before 9.13 (%d modes)' % len(_tg))
        check(all(g['avg_distance_sweep'][0] <= g['avg_distance_km']
                  <= g['avg_distance_sweep'][1]
                  and g['avg_time_sweep'][0] <= g['avg_time_min']
                  <= g['avg_time_sweep'][1] and g['years_observed'] >= 3
                  for g in _tg.values()),
              'every observed trip length and duration sits inside its own sweep, '
              'and each sweep is the spread across that mode survey years rather '
              'than a chosen interval')
        _drift = [m for m, g in _tg.items()
                  if (_fields.get('C.constraint.trip_length_km.%s' % m) or {})
                  .get('value') != g['avg_distance_km']
                  or (_fields.get('C.constraint.trip_time_min.%s' % m) or {})
                  .get('value') != g['avg_time_min']]
        check(not _drift,
              'the registry trip constraints agree with C4 mode for mode, so the '
              'declaration and the measurement cannot drift apart%s'
              % ('' if not _drift else ': ' + ', '.join(_drift)))
        check(all((_fields.get('C.constraint.trip_length_km.%s' % m) or {})
                  .get('source') == 'measured'
                  and (_fields.get('C.constraint.trip_length_km.%s' % m) or {})
                  .get('sweep') for m in _tg),
              'every per-mode trip-length constraint is declared measured WITH a '
              'sweep, so proposal 8.1 holds for it like any other value')
        _metrics_declared = {t['metric'] for t in _fit.load_targets()}
        check(not any('trip_length' in x or 'trip_geometry' in x
                      for x in _metrics_declared),
              'trip length is NOT among the calibration target metrics - it is a '
              'constraint reported beside the fit, and the pre-registered 67/143 '
              'split is untouched by it')

        _radius = _fields.get('B.counts.station_match_radius_m')
        check(_radius is not None and _radius.get('sweep'),
              'the count-station match radius is a DECLARED registry field with a '
              'sweep, not a CLI default - it decides which road_aadt targets are '
              'scorable at all, so it is a lever on the reported fit')

# ---- report ----
print('PASS %d' % len(OK))
# ---- P. the live run view (src/analyse/run_monitor.py) ----
#
# It reports no fit statistic, but it DOES compute the post-innovation drift that
# issue 5 turns on, and a number that can be cited needs coverage - deliverable 3
# had none, and that is how issue 19 survived. Driven on a synthetic run
# directory, so no completed run is needed: `results/` is gitignored and a check
# may not depend on one.
if True:
    sys.path.insert(0, os.path.join('src', 'analyse'))
    try:
        import run_monitor as _mon
    except ImportError as _e:
        check(False, 'src/analyse/run_monitor.py imports (%s)' % _e)
        _mon = None

    if _mon is not None:
        import tempfile as _tf
        _d = _tf.mkdtemp(prefix='wickham_mon_')
        _out = os.path.join(_d, 'output')
        os.makedirs(_out)
        with open(os.path.join(_d, 'config.xml'), 'w', encoding='utf-8') as _f:
            _f.write('<config>\n'
                     '<param name="lastIteration" value="10" />\n'
                     '<param name="fractionOfIterationsToDisableInnovation" value="0.8" />\n'
                     '<param name="transitScheduleFile" '
                     'value="C:/x/scenarios/matsim/S2/WEEKDAY/transitSchedule.xml.gz" />\n'
                     '</config>\n')
        # two iterations 30 s apart, so the median iteration time is knowable
        with open(os.path.join(_d, 'matsim.log'), 'w', encoding='utf-8') as _f:
            _f.write('2026-08-12T10:00:00,000  INFO AbstractController:137 '
                     '### ITERATION 8 BEGINS\n'
                     '2026-08-12T10:00:30,000  INFO AbstractController:137 '
                     '### ITERATION 9 BEGINS\n')
        with open(os.path.join(_out, 'modestats.csv'), 'w', encoding='utf-8') as _f:
            _f.write('iteration;car;ride\n8;0.30;0.50\n9;0.31;0.54\n')
        _s = _mon.scan(_d)

        check(_s['target'] == 10 and _s['iteration'] == 9,
              'run_monitor reads the iteration and the target from the run own '
              'config and log, so progress is the run self-report and not an '
              'argument someone passed')
        check(_s['scenario'] == 'S2' and _s['day'] == 'WEEKDAY',
              'run_monitor identifies scenario and day type from the transit '
              'schedule path BEFORE _run.json exists - that file is written when '
              'a run ENDS, which is exactly when nobody is watching')
        check(_s['median_iteration_s'] == 30.0 and _s['eta_s'] == 30,
              'run_monitor derives the per-iteration cost and the ETA from '
              'OBSERVED iteration times, never from the measured 9.5 figures, so '
              'a run that slows down is reported as slower')
        check(_s['innovation_off_at'] == 8,
              'run_monitor locates the iteration at which innovation switches '
              'off from fractionOfIterationsToDisableInnovation x lastIteration '
              '- the point after which any drift is the issue 5 question')
        check(abs(_s['post_innovation_drift'].get('ride', 0) - 0.04) < 1e-9
              and abs(_s['post_innovation_drift'].get('car', 0) - 0.01) < 1e-9,
              'run_monitor post-innovation drift is measured from the innovation '
              'cut-off to the last iteration, per mode - a model still moving '
              'once it can no longer create plans has not relaxed (issue 5)')
        # a log written a moment ago is a RUNNING run; backdate it past
        # RUN.monitor.stall_s to exercise the other branch
        _old = time.time() - (_mon.STALL_S + 60)
        os.utime(os.path.join(_d, 'matsim.log'), (_old, _old))
        _s2 = _mon.scan(_d)
        check(_s['state'] == 'running' and _s2['state'] == 'stalled',
              'run_monitor calls a run with a cold log STALLED rather than '
              'running, so a died run is never displayed as though it were '
              'still working')

        _p = _mon.PAGE.format(name='x', poll=3)
        check('{' + '{' not in _p and '}' + '}' not in _p,
              'the run monitor page template survives formatting with its CSS '
              'and JS braces intact, so the served page is not silently broken')
        check('modestats' in _p and 'never a result' in _p,
              'the live view states on its face that its mode trajectory is the '
              'mode agents CHOSE and is never a result - modestats and '
              '_metrics.json disagree by construction (DECISIONS.md 9.12)')

        shutil.rmtree(_d, ignore_errors=True)


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
