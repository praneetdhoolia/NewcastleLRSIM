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
        # a seed is not a prediction, but starting far from the observed
        # aggregate wastes iterations, so hold it loosely to HTS
        if hts_share:
            car = 100 * seed.get('car', 0)
            pt = 100 * seed.get('pt', 0)
            check(abs(car - hts_share['car']) < 8.0,
                  '%s: seed car share %.1f%% within 8 pp of the HTS %.1f%%'
                  % (day, car, hts_share['car']))
            check(abs(pt - hts_share['pt']) < 3.0,
                  '%s: seed PT share %.1f%% within 3 pp of the HTS %.1f%%'
                  % (day, pt, hts_share['pt']))
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
        # the split must partition the mapped schedule, losing nothing
        total = sum(d['routes_kept'] for d in days.values())
        src_routes = mrep2['schedules'].get(sid, {}).get('transit_routes')
        if src_routes:
            check(total == src_routes,
                  '%s: day-type split partitions the mapped schedule exactly '
                  '(%d = %d routes)' % (sid, total, src_routes))
        for d, c in sorted(days.items()):
            check(c['routes_kept'] > 0 and c['departures'] > 0,
                  '%s/%s: schedule retains services (%d routes, %d departures)'
                  % (sid, d, c['routes_kept'], c['departures']))
            check(c['vehicles'] == c['vehicle_refs'],
                  '%s/%s: every referenced transit vehicle is present (%d)'
                  % (sid, d, c['vehicles']))
            cfg = 'scenarios/matsim/%s/%s/config.xml' % (sid, d)
            check(os.path.exists(cfg), '%s/%s: config.xml written' % (sid, d))
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
if os.path.exists(RUN_REPORT):
    probe = [('S2', 'WEEKDAY'), ('S5', 'WEEKDAY'), ('S0', 'SUN')]
    for sid, day in probe:
        net = 'scenarios/matsim/%s/network.xml.gz' % sid
        sch = 'scenarios/matsim/%s/%s/transitSchedule.xml.gz' % (sid, day)
        if not (os.path.exists(net) and os.path.exists(sch)):
            continue
        links = set()
        with gzip.open(net, 'rt', encoding='utf-8') as f:
            for ln in f:
                m = re.search(r'<link id="([^"]+)"', ln)
                if m:
                    links.add(m.group(1))
        refs, missing = 0, 0
        with gzip.open(sch, 'rt', encoding='utf-8') as f:
            for ln in f:
                m = re.search(r'<stopFacility [^>]*linkRefId="([^"]+)"', ln)
                if m:
                    refs += 1
                    if m.group(1) not in links:
                        missing += 1
        check(refs > 0 and missing == 0,
              '%s/%s: every transit stop attaches to a link that exists on the '
              'run network (%d stops, %d dangling)' % (sid, day, refs, missing))


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
