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
    'B2 activity trips': 'demand/plans/B2_activity_trips.csv',
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
