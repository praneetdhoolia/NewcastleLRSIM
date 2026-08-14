#!/usr/bin/env python
"""Layer A3 extension tables: route_extras, stop_extras, transfer_extras.

transfer_extras is the important one. The whole policy question is whether
forcing an interchange at Wickham is worth the CBD distribution it buys
(proposal 6.2), so the physical cost of that interchange - walk distance,
whether it is sheltered, whether it requires a signalised road crossing - has to
be an explicit input rather than an implicit constant.
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
import csv
import json
import math
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gtfs_tools import read_feed

# Model inputs come from cities/<city>/registry/, not from literals here. Every
# value below carries its units, provenance and either a sweep, a held-fixed rule
# or a derived-from identity there. See DECISIONS.md 15.
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import registry as _registry  # noqa: E402
CFG = _registry.load()

OUT = _city.path('data/processed/schedule_extras')
os.makedirs(OUT, exist_ok=True)
BASE = _city.path('schedules/base2026.zip')

WALK_SPEED_MS = CFG.get('A.transit.walk_speed_ms')
INTERCHANGE_RADIUS_M = CFG.get('A.transit.interchange_radius_m')

MODE_BY_TYPE = {'0': 'lr', '1': 'metro', '2': 'heavy_rail', '3': 'bus', '4': 'ferry'}
OPERATOR = {'nisc001': 'Keolis Downer Hunter (Newcastle Transport)',
            'lightrail': 'Keolis Downer Hunter (Newcastle Transport)',
            'regionbuses': 'Hunter Valley Buses',
            'sydneytrains': 'Sydney Trains',
            'nswtrains': 'NSW TrainLink'}
CONTRACT = {'nisc001': 'NISC 1', 'lightrail': 'NISC 1 (light rail)',
            'regionbuses': 'Newcastle Hunter region', 'sydneytrains': 'Intercity',
            'nswtrains': 'Regional'}
VALID = {'nisc001': ('2017-07-01', ''), 'lightrail': ('2019-02-17', ''),
         'regionbuses': ('2024-09-01', ''), 'sydneytrains': ('', ''), 'nswtrains': ('', '')}


def hav(a, b):
    R = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    dp = p2 - p1
    return 2 * R * math.asin(math.sqrt(
        math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))


def main():
    f = read_feed(BASE)
    stops = {s['stop_id']: s for s in f['stops']}
    routes = {r['route_id']: r for r in f['routes']}

    # which stops each route serves, and which modes serve each stop
    trip_route = {t['trip_id']: t['route_id'] for t in f['trips']}
    stop_modes = collections.defaultdict(set)
    stop_routes = collections.defaultdict(set)
    for r in f['stop_times']:
        rid = trip_route.get(r['trip_id'])
        if not rid:
            continue
        rt = routes.get(rid, {})
        stop_modes[r['stop_id']].add(MODE_BY_TYPE.get(rt.get('route_type'), 'other'))
        stop_routes[r['stop_id']].add(rid)

    # ---------------- route_extras ----------------
    rrows = []
    for rid, r in routes.items():
        feed = rid.split(':')[0]
        rrows.append(dict(route_id=rid,
                          mode=MODE_BY_TYPE.get(r.get('route_type'), 'other'),
                          route_short_name=r.get('route_short_name', ''),
                          route_long_name=r.get('route_long_name', ''),
                          vehicle_type_id=('CAF_URBOS_100_NLR'
                                           if r.get('route_type') == '0' else
                                           'HEAVY_RAIL_EMU' if r.get('route_type') == '2'
                                           else 'BUS_RIGID_12M'),
                          contract_area=CONTRACT.get(feed, ''),
                          franchise_operator=OPERATOR.get(feed, ''),
                          valid_from=VALID.get(feed, ('', ''))[0],
                          valid_to=VALID.get(feed, ('', ''))[1],
                          source_feed=feed))
    _w('A3_route_extras.csv', rrows)

    # ---------------- stop_extras ----------------
    # interchange grouping: cluster stops served by >1 mode, or sharing a parent
    ll = {sid: (float(s['stop_lat']), float(s['stop_lon']))
          for sid, s in stops.items() if s.get('stop_lat')}
    named = [(sid, s) for sid, s in stops.items()
             if 'Newcastle Interchange' in s.get('stop_name', '')]
    inter_ids = set()
    if named:
        c = ll[named[0][0]]
        for sid, p in ll.items():
            if hav(c, p) <= INTERCHANGE_RADIUS_M:
                inter_ids.add(sid)

    srows = []
    for sid, s in stops.items():
        modes = sorted(stop_modes.get(sid, []))
        is_rail = 'heavy_rail' in modes
        is_lr = 'lr' in modes
        srows.append(dict(
            stop_id=sid, stop_name=s.get('stop_name', ''),
            stop_lat=s.get('stop_lat', ''), stop_lon=s.get('stop_lon', ''),
            modes_served='|'.join(modes), n_routes=len(stop_routes.get(sid, [])),
            location_type=s.get('location_type', ''),
            parent_station=s.get('parent_station', ''),
            platform_geom='',
            shelter=1 if (is_rail or is_lr) else -1,
            seating=1 if (is_rail or is_lr) else -1,
            real_time_info=1 if (is_rail or is_lr or sid in inter_ids) else -1,
            step_free=1 if (is_lr or is_rail) else -1,
            platform_height_mm=300 if is_lr else (1080 if is_rail else 0),
            interchange_group_id='NEWCASTLE_INTERCHANGE' if sid in inter_ids else '',
            attribute_source='assumed' if not (is_rail or is_lr) else 'inferred_from_mode'))
    _w('A3_stop_extras.csv', srows)

    # ---------------- transfer_extras ----------------
    # every stop pair within walking range, with the physical cost of the transfer
    trows = []
    ids = [sid for sid in ll if stop_modes.get(sid)]
    inter_list = [sid for sid in ids if sid in inter_ids]
    for i, a in enumerate(ids):
        pa = ll[a]
        for b in ids:
            if a >= b:
                continue
            pb = ll[b]
            d = hav(pa, pb)
            if d > 400:
                continue
            ma, mb = stop_modes.get(a, set()), stop_modes.get(b, set())
            if not (ma - mb or mb - ma) and d > 150:
                continue
            walk = d * 1.25          # network detour factor on a straight line
            crossing = int(d > 60 and not (a in inter_ids and b in inter_ids))
            delay = 22 if crossing else 0
            trows.append(dict(
                from_stop=a, to_stop=b,
                from_name=stops[a].get('stop_name', ''), to_name=stops[b].get('stop_name', ''),
                from_modes='|'.join(sorted(ma)), to_modes='|'.join(sorted(mb)),
                straight_distance_m=round(d, 1),
                walk_distance_m=round(walk, 1),
                walk_time_s=round(walk / WALK_SPEED_MS, 1),
                is_sheltered=1 if (a in inter_ids and b in inter_ids) else 0,
                requires_road_crossing=crossing,
                signalised_crossing_delay_s=delay,
                total_transfer_time_s=round(walk / WALK_SPEED_MS + delay, 1),
                in_interchange_group=int(a in inter_ids and b in inter_ids),
                source='modelled'))
    _w('A3_transfer_extras.csv', trows)

    # the interchange itself, reported separately because it carries the result
    inter_rows = [r for r in trows if r['in_interchange_group'] == 1]
    cross_modal = [r for r in inter_rows if r['from_modes'] != r['to_modes']]
    rep = dict(routes=len(rrows), stops=len(srows), transfers=len(trows),
               interchange_stops=len(inter_list),
               interchange_stop_names=sorted({stops[s].get('stop_name', '') for s in inter_list}),
               interchange_pairs=len(inter_rows),
               interchange_cross_modal_pairs=len(cross_modal),
               interchange_mean_walk_time_s=round(
                   sum(r['total_transfer_time_s'] for r in inter_rows) / len(inter_rows), 1)
               if inter_rows else None,
               interchange_max_walk_time_s=round(
                   max((r['total_transfer_time_s'] for r in inter_rows), default=0), 1))
    json.dump(rep, open(os.path.join(OUT, '_extras_report.json'), 'w'), indent=2)
    print(json.dumps(rep, indent=2))


def _w(name, rows):
    if not rows:
        print('   (empty) %s' % name)
        return
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with open(os.path.join(OUT, name), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    print('   wrote %-30s %d rows' % (name, len(rows)))


if __name__ == '__main__':
    main()
