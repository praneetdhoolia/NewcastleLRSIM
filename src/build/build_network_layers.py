#!/usr/bin/env python
"""Build supply-side layers from the OSM extracts.

Produces (schemas per Appendix A of the proposal):
    A1_road_edges.csv          road graph with lanes/speed/capacity/kerbside
    A6_footway_edges.csv       active-transport graph (gradient attached later)
    A2_signal_nodes_osm.csv    traffic signal inventory (SCATS proxy base)
    A2_crossings_osm.csv       pedestrian crossings
    A2_turn_restrictions_osm.csv
    A5_parking_osm.csv         parking facilities

Every field imputed rather than observed is counted and reported so the
imputation rate lands in DECISIONS.md.
"""

# City-relative paths resolve through src/city.py: `data/...` names a
# location inside cities/<city>/, not inside the repository root.
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                  '..', '..', 'src'))
import city as _city  # noqa: E402
import os
import csv
import json
import sys
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from osm_parse import parse, way_len, centroid, fnum

# Model inputs come from config/registry/<city>/, not from literals here. Every
# value below carries its units, provenance and either a sweep, a held-fixed rule
# or a derived-from identity there. See DECISIONS.md 15.
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import registry as _registry  # noqa: E402
CFG = _registry.load()

OUT = _city.path('data/processed/network')
os.makedirs(OUT, exist_ok=True)

# ---- defaults applied where OSM is silent (all recorded in DECISIONS.md) ----
# speed_limit_kmh by road class: NSW default urban 50, and class-typical above that
SPEED = CFG.get('A.road.speed_default')
# lanes per direction
LANES = CFG.get('A.road.lanes_default')
# mid-block capacity veh/hr/lane, Austroads-style
CAP = CFG.get('A.road.capacity_default')
FOOT_WIDTH = CFG.get('A.active.footway_width_default')
# Per-lane width where OSM carries none, which is 99.2% of edges. Was a bare
# 3.2 in this file and in no registry at all (DECISIONS.md 9.33).
LANE_WIDTH = CFG.get('A.road.lane_width_default_m')


def _write(name, rows):
    if not rows:
        print('   (no rows for %s)' % name)
        return
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with open(os.path.join(OUT, name), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def _kerbside(t):
    """Classify kerbside use from OSM parking:* / transit tagging."""
    if t.get('railway') == 'tram' or t.get('embedded_rails'):
        return 'tram_lane'
    if t.get('highway') == 'busway' or 'bus' in (t.get('lanes:psv') or ''):
        return 'bus_lane'
    vals = [v for k, v in t.items() if k.startswith('parking:')]
    if any(v in ('no', 'no_stopping', 'no_parking') for v in vals):
        return 'clearway'
    if any(v in ('parallel', 'perpendicular', 'diagonal', 'lane', 'street_side', 'yes')
           for v in vals):
        return 'parking'
    return 'unknown'


def build_roads():
    idx = {}
    ways = []
    for rec in parse(_city.path('networks/osm/roads.osm')):
        if rec[0] == 'node':
            idx[rec[1]] = (rec[2], rec[3])
        elif rec[0] == 'way' and 'highway' in rec[3]:
            ways.append((rec[1], rec[2], rec[3]))
    rows = []
    imp = collections.Counter()
    geom = open(os.path.join(OUT, 'A1_road_geometry.jsonl'), 'w', encoding='utf-8')
    for wid, refs, t in ways:
        L, pts = way_len(refs, idx)
        if L <= 0 or len(pts) < 2:
            continue
        hw = t['highway']
        sl = fnum(t.get('maxspeed'))
        if sl is None:
            sl = SPEED.get(hw, 50)
            sl_src = 'imputed_rule'
            imp['speed_limit_kmh'] += 1
        else:
            sl_src = 'osm'
        oneway = t.get('oneway') in ('yes', '1', '-1', 'true')
        ln = fnum(t.get('lanes'))
        if ln is None:
            ln = LANES.get(hw, 1)
            imp['num_lanes'] += 1
        elif not oneway:
            ln = max(1.0, ln / 2.0)   # OSM lanes=total both directions
        # OSM `width` on a road is the whole CARRIAGEWAY, not one lane, so it
        # is divided by the lane count before it can stand in for a lane width.
        lw = fnum(t.get('width'))
        if lw is None:
            lw = LANE_WIDTH
            imp['lane_width_m'] += 1
        else:
            raw_lanes = fnum(t.get('lanes'))
            lw = (lw / raw_lanes) if (raw_lanes and raw_lanes > 0) else LANE_WIDTH
        kerb = _kerbside(t)
        if kerb == 'unknown':
            imp['kerbside_use'] += 1
        rows.append(dict(
            edge_id='w' + wid, from_node=refs[0], to_node=refs[-1], n_nodes=len(refs),
            length_m=round(L, 1), road_class=hw, num_lanes=ln, lane_width_m=lw,
            speed_limit_kmh=sl, speed_limit_source=sl_src, oneway_flag=int(oneway),
            oneway_dir=(-1 if t.get('oneway') == '-1' else 1),
            capacity_veh_hr_lane=CAP.get(hw, 1000), kerbside_use=kerb,
            gradient_pct='', bridge=int('bridge' in t), tunnel=int('tunnel' in t),
            surface=t.get('surface', ''), name=t.get('name', ''), ref=t.get('ref', ''),
            access=t.get('access', ''), psv=t.get('psv', ''),
            turn_lanes=t.get('turn:lanes', ''),
            start_lat=round(pts[0][0], 7), start_lon=round(pts[0][1], 7),
            end_lat=round(pts[-1][0], 7), end_lon=round(pts[-1][1], 7),
            scenario_variant_ref='base2026'))
        geom.write(json.dumps({'edge_id': 'w' + wid,
                               'coords': [[round(p[1], 7), round(p[0], 7)] for p in pts]}) + '\n')
    geom.close()
    _write('A1_road_edges.csv', rows)
    return len(rows), dict(imp), sum(r['length_m'] for r in rows)


def build_footways():
    idx = {}
    ways = []
    for rec in parse(_city.path('networks/osm/footways.osm')):
        if rec[0] == 'node':
            idx[rec[1]] = (rec[2], rec[3])
        elif rec[0] == 'way' and ('highway' in rec[3] or 'footway' in rec[3]):
            ways.append((rec[1], rec[2], rec[3]))
    rows = []
    imp = collections.Counter()
    geom = open(os.path.join(OUT, 'A6_footway_geometry.jsonl'), 'w', encoding='utf-8')
    for wid, refs, t in ways:
        L, pts = way_len(refs, idx)
        if L <= 0 or len(pts) < 2:
            continue
        hw = t.get('highway', 'footway')
        width = fnum(t.get('width'))
        if width is None:
            width = FOOT_WIDTH.get(hw, 1.8)
            imp['width_m'] += 1
        lit = 1 if t.get('lit') == 'yes' else (0 if t.get('lit') == 'no' else -1)
        if lit == -1:
            imp['lighting'] += 1
        rows.append(dict(
            footway_edge_id='f' + wid, from_node=refs[0], to_node=refs[-1],
            length_m=round(L, 1), highway=hw, footway=t.get('footway', ''),
            width_m=width, surface=t.get('surface', '') or 'paved',
            lighting=lit,
            shade=1 if (t.get('covered') == 'yes' or 'tunnel' in t) else -1,
            crossing_type=(t.get('crossing', '') or
                           ('signalised' if t.get('crossing:signals') == 'yes' else '')),
            crossing_delay_s='', step_free=0 if hw == 'steps' else 1,
            steps=int(hw == 'steps'), tram_track_crossing=0,
            incline=t.get('incline', ''), gradient_pct='',
            bicycle=t.get('bicycle', ''), foot=t.get('foot', ''),
            wheelchair=t.get('wheelchair', ''), name=t.get('name', ''),
            start_lat=round(pts[0][0], 7), start_lon=round(pts[0][1], 7),
            end_lat=round(pts[-1][0], 7), end_lon=round(pts[-1][1], 7),
            scenario_variant_ref='base2026'))
        geom.write(json.dumps({'footway_edge_id': 'f' + wid,
                               'coords': [[round(p[1], 7), round(p[0], 7)] for p in pts]}) + '\n')
    geom.close()
    _write('A6_footway_edges.csv', rows)
    return len(rows), dict(imp), sum(r['length_m'] for r in rows)


def build_signals():
    sig, cross, restr = [], [], []
    for rec in parse(_city.path('networks/osm/signals.osm')):
        if rec[0] == 'node':
            _, i, lat, lon, t = rec
            if t.get('highway') == 'traffic_signals':
                sig.append(dict(node_id=i, lat=round(lat, 7), lon=round(lon, 7),
                                direction=t.get('traffic_signals:direction', ''),
                                signal_type=t.get('traffic_signals', ''),
                                ped_phase_flag=1 if (t.get('crossing') or
                                                     t.get('button_operated') == 'yes') else -1,
                                button_operated=t.get('button_operated', ''),
                                name=t.get('name', '')))
            elif t.get('highway') == 'crossing' or 'crossing' in t:
                cross.append(dict(node_id=i, lat=round(lat, 7), lon=round(lon, 7),
                                  crossing=t.get('crossing', ''),
                                  signals=t.get('crossing:signals', ''),
                                  markings=t.get('crossing:markings', ''),
                                  island=t.get('crossing:island', ''),
                                  tactile_paving=t.get('tactile_paving', '')))
        elif rec[0] == 'rel' and rec[3].get('type') == 'restriction':
            restr.append(dict(rel_id=rec[1], restriction=rec[3].get('restriction', ''),
                              members=';'.join('%s:%s:%s' % m for m in rec[2])))
    _write('A2_signal_nodes_osm.csv', sig)
    _write('A2_crossings_osm.csv', cross)
    _write('A2_turn_restrictions_osm.csv', restr)
    return len(sig), len(cross), len(restr)


def build_parking():
    idx = {}
    items = []
    for rec in parse(_city.path('networks/osm/parking.osm')):
        if rec[0] == 'node':
            idx[rec[1]] = (rec[2], rec[3])
            items.append(('node', rec[1], [(rec[2], rec[3])], rec[4]))
        elif rec[0] == 'way':
            items.append(('way', rec[1], rec[2], rec[3]))
    rows = []
    n_cap = 0
    for kind, i, geo, t in items:
        if t.get('amenity') not in ('parking', 'parking_space', 'motorcycle_parking'):
            continue
        pts = geo if kind == 'node' else [idx[r] for r in geo if r in idx]
        if not pts:
            continue
        lat, lon = centroid(pts)
        cap = fnum(t.get('capacity'))
        if cap:
            n_cap += 1
        access = t.get('access', '')
        if access in ('private', 'customers', 'permissive') or t.get('parking') == 'private':
            ptype = 'offstreet_private'
        elif t.get('parking') in ('street_side', 'lane', 'on_street'):
            ptype = 'onstreet'
        else:
            ptype = 'offstreet_public'
        rows.append(dict(
            parking_facility_id='p%s%s' % (kind[0], i), lat=round(lat, 7), lon=round(lon, 7),
            type=ptype, osm_parking=t.get('parking', ''),
            capacity_spaces=int(cap) if cap else '',
            capacity_source='osm' if cap else 'imputed',
            fee=t.get('fee', ''), charge=t.get('charge', '') or t.get('fee:conditional', ''),
            max_stay_min=t.get('maxstay', ''), access=access,
            operator=t.get('operator', ''), surface=t.get('surface', ''),
            levels=t.get('parking:levels', '') or t.get('levels', ''),
            name=t.get('name', ''), scenario_variant_ref='base2026'))
    _write('A5_parking_osm.csv', rows)
    return len(rows), n_cap


if __name__ == '__main__':
    r = build_roads()
    print('A1 road edges         : %d  | %.1f km | imputed %s' % (r[0], r[2] / 1000, r[1]), flush=True)
    f = build_footways()
    print('A6 footway edges      : %d  | %.1f km | imputed %s' % (f[0], f[2] / 1000, f[1]), flush=True)
    s = build_signals()
    print('A2 signals=%d crossings=%d turn_restrictions=%d' % s, flush=True)
    p = build_parking()
    print('A5 parking facilities : %d  | with OSM capacity %d' % p, flush=True)
    json.dump({'road_edges': r[0], 'road_km': round(r[2] / 1000, 1), 'road_imputed': r[1],
               'footway_edges': f[0], 'footway_km': round(f[2] / 1000, 1), 'footway_imputed': f[1],
               'signals': s[0], 'crossings': s[1], 'turn_restrictions': s[2],
               'parking_facilities': p[0], 'parking_with_osm_capacity': p[1]},
              open(os.path.join(OUT, '_build_report.json'), 'w'), indent=2)
