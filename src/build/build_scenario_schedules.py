#!/usr/bin/env python
"""Generate the GTFS variant for every scenario in the matrix (proposal 4.3).

All scenarios share the same land use, population, behavioural parameters and
non-CBD bus network. Only the central-city trunk mode changes. This script
derives each variant from the base 2026 feed so that identity is guaranteed by
construction rather than by hand-editing.

    S0   heavy rail retained through Wickham to Newcastle station, no LR
    S1   bus shuttle from Wickham, no LR (the December 2012 policy as announced)
    S2   light rail as built                                        (= base2026)
    S2a  light rail, charging dwell removed
    S2b  light rail with full transit signal priority
    S2c  light rail on the Option A alignment (former railway land)
    S3   bus rapid transit on the same alignment
    S4   light rail extended to Broadmeadow
    S5   light rail extended to Broadmeadow and John Hunter Hospital
    S6   no trunk mode; walk, cycle and local bus only

Run-time changes are applied through the same kinematic + dwell + signal-delay
decomposition used in build_corridor_layers.py, so a scenario's run time is a
consequence of its stated physical differences, not a free parameter.
"""
import os
import sys
import csv
import json
import math
import copy
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gtfs_tools import read_feed, write_feed
from shape_tools import (RoadGraph, harbourside_corridor, project_onto,
                         resolve_anchor, shape_rows, densify, dedupe,
                         polyline_length_m)

# Model inputs come from config/registry/<city>/, not from literals here. Every
# value below carries its units, provenance and either a sweep, a held-fixed rule
# or a derived-from identity there. See DECISIONS.md 15.
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import registry as _registry  # noqa: E402
CFG = _registry.load()

BASE = 'schedules/base2026.zip'
OUT = 'schedules/scenarios'
os.makedirs(OUT, exist_ok=True)

LR_ROUTE_PREFIX = 'lightrail:'
ACCEL, DECEL = 1.2, 1.3
LINE_SPEED = CFG.get('A.lightrail.line_speed_kmh')
CORRIDOR_SPEED = CFG.get('A.lightrail.corridor_speed_kmh')
DWELL_FIXED = CFG.get('A.lightrail.dwell_fixed_s')
DWELL_CHARGING = 20.0
SIGNAL_DELAY_PER_INT = CFG.get('A.signals.delay_per_intersection_s')
# How close a heavy-rail shape's end must come to the Interchange before the S0
# corridor is spliced onto it. Newcastle Interchange platforms sit ~200 m from
# the tram stop the corridor starts at, so this is generous but far short of
# the next station in any direction.
S0_JOIN_TOLERANCE_M = CFG.get('A.transit.s0_join_tolerance_m')
N_CORRIDOR_INTERSECTIONS = CFG.get('A.signals.n_corridor_intersections')

# Extension stops. *That* there is a stop here is assumed - the SBC names the
# corridor but sites no platform. *Where* it is is no longer assumed: each stop
# is anchored on an observed feature the corridor passes, resolved from the OSM
# and POI layers at build time, then projected onto the routed alignment. P1
# typed four plausible coordinates instead, and one of them (Hamilton) sat 548 m
# off the published corridor.
EXT_BROADMEADOW = [
    ('Hamilton (Beaumont St)', ('intersection', 'Tudor Street', 'Beaumont Street')),
    ('Broadmeadow', ('rail_station', 'Broadmeadow Station')),
]
EXT_JHH = [
    ('Lambton', ('intersection', 'Lambton Road', 'Turton Road')),
    ('John Hunter Hospital', ('poi', 'John Hunter Hospital', 'health:hospital')),
]
# S1 bus shuttle stop spacing is tighter than light rail
S1_SHUTTLE = [
    ('Newcastle Interchange', -32.92433, 151.75943),
    ('Honeysuckle', -32.92647, 151.76583),
    ('Civic', -32.92699, 151.77175),
    ('Market Street', -32.92660, 151.77450),
    ('Crown Street', -32.92637, 151.77721),
    ('Queens Wharf', -32.92633, 151.78164),
    ('Watt Street', -32.92700, 151.78400),
    ('Newcastle Beach', -32.92748, 151.78626),
]
S0_EXTENSION = [
    ('Civic Station', -32.92800, 151.77560, 'assumed - former station site'),
    ('Newcastle Station', -32.92820, 151.78460, 'assumed - former terminus site'),
]


def hav(a, b):
    R = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    dp = p2 - p1
    return 2 * R * math.asin(math.sqrt(
        math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))


def kin(d, v_kmh, a=ACCEL, b=DECEL):
    v = v_kmh / 3.6
    da, db = v * v / (2 * a), v * v / (2 * b)
    if d >= da + db:
        return v / a + v / b + (d - da - db) / v
    vp = math.sqrt(2 * d * a * b / (a + b))
    return vp / a + vp / b


def sec(t):
    h, m, s = map(int, t.split(':'))
    return h * 3600 + m * 60 + s


def hhmmss(s):
    s = int(round(s))
    return '%02d:%02d:%02d' % (s // 3600, (s % 3600) // 60, s % 60)


def renumber_sequences(feed):
    """Renumber stop_sequence 1..n per trip, preserving list order.

    Source feeds do not guarantee contiguous stop_sequence values, so appending
    stops with len(rows)+1 can collide with an existing number. Every builder
    emits each trip's stop_times in the correct order, so a positional
    renumbering is both safe and sufficient.
    """
    seen = collections.defaultdict(int)
    for r in feed['stop_times']:
        seen[r['trip_id']] += 1
        r['stop_sequence'] = seen[r['trip_id']]
    return feed


def group_trips(feed):
    b = collections.defaultdict(list)
    for r in feed['stop_times']:
        b[r['trip_id']].append(r)
    for k in b:
        b[k].sort(key=lambda r: int(r['stop_sequence']))
    return b


def lr_trip_ids(feed):
    lr_routes = {r['route_id'] for r in feed['routes']
                 if r['route_id'].startswith(LR_ROUTE_PREFIX)}
    return {t['trip_id'] for t in feed['trips'] if t['route_id'] in lr_routes}, lr_routes


def drop_lr(feed):
    """Remove the light rail route entirely."""
    f = copy.deepcopy(feed)
    tids, rids = lr_trip_ids(f)
    f['trips'] = [t for t in f['trips'] if t['trip_id'] not in tids]
    f['stop_times'] = [r for r in f['stop_times'] if r['trip_id'] not in tids]
    f['routes'] = [r for r in f['routes'] if r['route_id'] not in rids]
    keep = {r['stop_id'] for r in f['stop_times']}
    f['stops'] = [s for s in f['stops']
                  if s['stop_id'] in keep or s.get('stop_id') in
                  {x.get('parent_station') for x in f['stops'] if x['stop_id'] in keep}]
    return f


def scale_lr_runtime(feed, delta_per_intermediate_s=0.0, delta_per_segment_s=0.0,
                     speed_kmh=None, label=''):
    """Rebuild light rail stop_times with an altered run-time decomposition."""
    f = copy.deepcopy(feed)
    tids, _ = lr_trip_ids(f)
    by = group_trips(f)
    stops = {s['stop_id']: s for s in f['stops']}
    newst = []
    for r in f['stop_times']:
        if r['trip_id'] not in tids:
            newst.append(r)
    for tid in sorted(tids):
        rows = by.get(tid)
        if not rows:
            continue
        t0 = sec(rows[0]['departure_time'])
        cum = t0
        out = []
        for i, r in enumerate(rows):
            if i == 0:
                r = dict(r, arrival_time=hhmmss(cum), departure_time=hhmmss(cum))
                out.append(r)
                continue
            a, b = rows[i - 1], r
            pa = stops.get(a['stop_id'])
            pb = stops.get(b['stop_id'])
            d = hav((float(pa['stop_lat']), float(pa['stop_lon'])),
                    (float(pb['stop_lat']), float(pb['stop_lon']))) * 1.06
            base_seg = sec(b['arrival_time']) - sec(a['departure_time'])
            if speed_kmh:
                seg = kin(d, speed_kmh) + max(0.0, base_seg - kin(d, LINE_SPEED)) \
                    + delta_per_segment_s
            else:
                seg = base_seg + delta_per_segment_s
            seg = max(30.0, seg)
            cum += seg
            arr = cum
            dw = 0.0 if i == len(rows) - 1 else max(0.0, delta_per_intermediate_s)
            cum += dw
            out.append(dict(r, arrival_time=hhmmss(arr), departure_time=hhmmss(cum)))
        newst.extend(out)
    f['stop_times'] = newst
    return f


def extend_lr(feed, extra_stops, speed_kmh=LINE_SPEED, tag='EXT'):
    """Append stops beyond Newcastle Interchange (the western terminus)."""
    f = copy.deepcopy(feed)
    tids, _ = lr_trip_ids(f)
    by = group_trips(f)
    stops = {s['stop_id']: s for s in f['stops']}
    # register new stops
    newstops = []
    ids = []
    for i, (nm, la, lo, src) in enumerate(extra_stops):
        sid = 'lightrail:EXT_%s_%d' % (tag, i + 1)
        ids.append(sid)
        newstops.append(dict(stop_id=sid, stop_name=nm, stop_lat=la, stop_lon=lo,
                             location_type='0', stop_code='', parent_station=''))
    f['stops'] = f['stops'] + newstops
    interchange = [s for s in f['stops']
                   if 'Newcastle Interchange' in s['stop_name'] and s['stop_id'].startswith('lightrail:')]
    if not interchange:
        return f
    inter = interchange[0]
    newst = [r for r in f['stop_times'] if r['trip_id'] not in tids]
    for tid in sorted(tids):
        rows = by.get(tid)
        if not rows:
            continue
        first, last = rows[0], rows[-1]
        starts_at_inter = 'Newcastle Interchange' in stops[first['stop_id']]['stop_name']
        chain = [(inter, None)] + [(dict(stop_id=i_, stop_name=n[0], stop_lat=n[1], stop_lon=n[2]), i_)
                                   for i_, n in zip(ids, extra_stops)]
        legs = []
        for a, b in zip(chain, chain[1:]):
            d = hav((float(a[0]['stop_lat']), float(a[0]['stop_lon'])),
                    (float(b[0]['stop_lat']), float(b[0]['stop_lon']))) * 1.15
            legs.append(kin(d, speed_kmh) + DWELL_FIXED + DWELL_CHARGING + SIGNAL_DELAY_PER_INT * 0.6)
        if starts_at_inter:
            # trip now begins at the far end of the extension and runs inbound
            t_first = sec(first['departure_time'])
            pre = []
            t = t_first - sum(legs)
            for j, sid in enumerate(ids[::-1]):
                pre.append(dict(trip_id=tid, stop_id=sid, stop_sequence=0,
                                arrival_time=hhmmss(t), departure_time=hhmmss(t),
                                pickup_type='0', drop_off_type='0'))
                t += legs[len(ids) - 1 - j]
            for k, r in enumerate(pre):
                r['stop_sequence'] = k + 1
            for k, r in enumerate(rows):
                r = dict(r)
                r['stop_sequence'] = len(pre) + k + 1
                pre.append(r)
            newst.extend(pre)
        else:
            t = sec(last['arrival_time'])
            out = [dict(r) for r in rows]
            for j, sid in enumerate(ids):
                t += legs[j]
                out.append(dict(trip_id=tid, stop_id=sid,
                                stop_sequence=len(out) + 1,
                                arrival_time=hhmmss(t), departure_time=hhmmss(t),
                                pickup_type='0', drop_off_type='0'))
            newst.extend(out)
    f['stop_times'] = newst
    return f


def extend_heavy_rail(feed):
    """S0: run CCN and HUN services through Wickham to Newcastle station."""
    f = drop_lr(feed)
    by = group_trips(f)
    stops = {s['stop_id']: s for s in f['stops']}
    routes = {r['route_id']: r for r in f['routes']}
    newstops = []
    ids = []
    for i, (nm, la, lo, src) in enumerate(S0_EXTENSION):
        sid = 'sydneytrains:S0_%d' % (i + 1)
        ids.append(sid)
        newstops.append(dict(stop_id=sid, stop_name=nm, stop_lat=la, stop_lon=lo,
                             location_type='0', parent_station=''))
    f['stops'] = f['stops'] + newstops
    inter_names = ('Newcastle Interchange',)
    # heavy rail runs on reserved alignment: faster than the tram over the same ground
    chain_ll = [(-32.92404, 151.75908)] + [(s[1], s[2]) for s in S0_EXTENSION]
    legs = []
    for a, b in zip(chain_ll, chain_ll[1:]):
        d = hav(a, b) * 1.10
        legs.append(kin(d, CORRIDOR_SPEED) + 30.0)   # 30 s station dwell
    n_ext = 0
    newst = []
    touched = set()
    for tid, rows in by.items():
        last = stops.get(rows[-1]['stop_id'], {})
        rt = routes.get(next((t['route_id'] for t in f['trips'] if t['trip_id'] == tid), ''), {})
        if rt.get('route_type') != '2':
            continue
        if 'Non Revenue' in (rt.get('route_short_name', '') or rt.get('route_long_name', '')):
            continue
        if not any(n in last.get('stop_name', '') for n in inter_names):
            continue
        touched.add(tid)
        t = sec(rows[-1]['arrival_time'])
        out = [dict(r) for r in rows]
        for j, sid in enumerate(ids):
            t += legs[j]
            out.append(dict(trip_id=tid, stop_id=sid, stop_sequence=len(out) + 1,
                            arrival_time=hhmmss(t), departure_time=hhmmss(t),
                            pickup_type='0', drop_off_type='0'))
        newst.extend(out)
        n_ext += 1
    for r in f['stop_times']:
        if r['trip_id'] not in touched:
            newst.append(r)
    f['stop_times'] = newst
    return f, n_ext


def make_bus_shuttle(feed, stops_def, headway_s, route_id, route_name, mode='3',
                     speed_kmh=28.0, dwell_s=15.0, first_h=5, last_h=24):
    """Insert a new surface route along the CBD spine (used by S1 and S3)."""
    f = copy.deepcopy(feed)
    sids = []
    for i, (nm, la, lo) in enumerate(stops_def):
        sid = '%s_S%d' % (route_id, i + 1)
        sids.append(sid)
        f['stops'].append(dict(stop_id=sid, stop_name=nm, stop_lat=la, stop_lon=lo,
                               location_type='0', parent_station=''))
    f['routes'].append(dict(route_id=route_id, agency_id=f['routes'][0].get('agency_id', ''),
                            route_short_name=route_name, route_long_name=route_name,
                            route_type=mode, route_color='0057B8', route_text_color='FFFFFF'))
    legs = []
    for a, b in zip(stops_def, stops_def[1:]):
        d = hav((a[1], a[2]), (b[1], b[2])) * 1.10
        legs.append(kin(d, speed_kmh) + dwell_s + SIGNAL_DELAY_PER_INT * 0.5)
    n = 0
    for daytype in ['WEEKDAY', 'SAT', 'SUN']:
        hw = headway_s * (1.0 if daytype == 'WEEKDAY' else 1.5)
        t = first_h * 3600
        while t < last_h * 3600:
            for direction, order in ((0, sids), (1, sids[::-1])):
                n += 1
                tid = '%s_%s_%d_%d' % (route_id, daytype, direction, n)
                f['trips'].append(dict(route_id=route_id, service_id=daytype, trip_id=tid,
                                       direction_id=str(direction), shape_id='',
                                       trip_headsign=order[-1].split('_')[0]))
                tt = t
                for k, sid in enumerate(order):
                    if k:
                        tt += legs[k - 1] if direction == 0 else legs[len(legs) - k]
                    f['stop_times'].append(dict(trip_id=tid, stop_id=sid,
                                                stop_sequence=k + 1,
                                                arrival_time=hhmmss(tt),
                                                departure_time=hhmmss(tt),
                                                pickup_type='0', drop_off_type='0'))
            t += hw
    return f, n


# ---------------------------------------------------------------------------
# Shapes
#
# P1 added and moved stops without ever touching shapes.txt, so S0, S2c, S4 and
# S5 all carried the same 275-point as-built geometry (DECISIONS.md 3.4). Every
# shape below is routed over geometry the package already observes; only the
# stop sitings stay assumed.
# ---------------------------------------------------------------------------

LR_SHAPE_OUT = 'lightrail:NLR.OUTBOUND'   # Interchange -> Newcastle Beach
LR_SHAPE_IN = 'lightrail:NLR.INBOUND'     # Newcastle Beach -> Interchange

# Street sequence of the S4/S5 extension, from the Newcastle Light Rail
# Extension Strategic Business Case (2020): out of Newcastle Interchange onto
# Tudor Street, into Belford Street through the Nine Ways and over the
# Broadmeadow rail overbridge, onto Lambton Road, across Turton Road into New
# Lambton and onto Russell Road, then left off Lookout Road to the hospital.
# The streets are named in a published document; the geometry joining them is
# the observed OSM centreline of those streets.
SBC_EXTENSION_STREETS = ('Hunter Street', 'Tudor Street', 'Belford Street',
                         'Lambton Road', 'Turton Road', 'Russell Road',
                         'Lookout Road')
SBC_EXTENSION_KM = CFG.get('A.transit.sbc_extension_km')
INTERCHANGE_LL = (-32.92433, 151.75943)
JHH_LL = (-32.92230, 151.69440)


def shape_points(feed, shape_id):
    rows = sorted((r for r in feed['shapes'] if r['shape_id'] == shape_id),
                  key=lambda r: int(r['shape_pt_sequence']))
    return [(float(r['shape_pt_lat']), float(r['shape_pt_lon'])) for r in rows]


def put_shapes(feed, mapping):
    """Replace the named shapes with new point lists, leaving the rest alone."""
    feed['shapes'] = [r for r in feed['shapes'] if r['shape_id'] not in mapping]
    for sid in sorted(mapping):
        feed['shapes'] += shape_rows(sid, mapping[sid])


def extension_alignment(graph):
    """Newcastle Interchange -> John Hunter Hospital over the SBC streets."""
    a, _ = graph.nearest_node(INTERCHANGE_LL)
    b, _ = graph.nearest_node(JHH_LL)
    pts = graph.shortest_path(a, b, prefer_names=SBC_EXTENSION_STREETS)
    if not pts:
        raise RuntimeError('extension corridor did not route')
    return densify(dedupe([INTERCHANGE_LL] + list(pts) + [JHH_LL]), 20.0)


def site_extension_stops(alignment, specs):
    """Resolve each stop's observed anchor, then project it onto the corridor.

    Returns (name, lat, lon, source, offset_from_anchor_m, distance_along_m).
    The offset says how far the corridor runs from the feature the stop is
    named for; a large one would mean the anchor and the route disagree.
    """
    out = []
    for nm, spec in specs:
        anchor, desc = resolve_anchor(spec)
        if anchor is None:
            raise RuntimeError('could not resolve anchor for %s: %r' % (nm, spec))
        q, d, along = project_onto(alignment, anchor)
        src = 'assumed siting, anchored on %s' % desc
        out.append((nm, round(q[0], 7), round(q[1], 7), src, round(d, 1), along))
    return out


def set_lr_extension_shape(feed, alignment):
    """Prepend/append the extension to the two tram shapes.

    OUTBOUND starts at the Interchange, so the extension goes on the front,
    reversed, and the trip now begins at the far end. INBOUND is its mirror.
    """
    out_pts = shape_points(feed, LR_SHAPE_OUT)
    new_out = dedupe(list(reversed(alignment))[:-1] + out_pts)
    put_shapes(feed, {LR_SHAPE_OUT: new_out,
                      LR_SHAPE_IN: list(reversed(new_out))})
    return polyline_length_m(alignment)


def move_lr_stops_onto(feed, corridor):
    """Project the tram stops onto a corridor, in place.

    Must run *before* the run-time decomposition: `scale_lr_runtime` derives
    every segment time from the stop-to-stop distance, so moving stops
    afterwards would leave the timetable describing the old geometry.
    """
    moved = 0
    for s in feed['stops']:
        if not s['stop_id'].startswith('lightrail:'):
            continue
        q, _, _ = project_onto(corridor, (float(s['stop_lat']), float(s['stop_lon'])))
        s['stop_lat'], s['stop_lon'] = round(q[0], 7), round(q[1], 7)
        moved += 1
    return moved


def set_reserved_alignment_shape(feed, corridor):
    """S2c: put the tram shape on the retained former-railway corridor."""
    put_shapes(feed, {LR_SHAPE_OUT: corridor,
                      LR_SHAPE_IN: list(reversed(corridor))})


def set_s0_rail_shapes(feed, corridor, ext_stop_ids):
    """S0: carry the extended heavy-rail trips beyond the Interchange.

    A shape can be shared by trips that were extended and trips that were not,
    so the extended trips get their own shape id rather than the original
    being rewritten underneath everyone.
    """
    by_trip = collections.defaultdict(list)
    for r in feed['stop_times']:
        by_trip[r['trip_id']].append(r)
    extended = {t for t, rows in by_trip.items()
                if any(r['stop_id'] in ext_stop_ids for r in rows)}
    existing = {r['shape_id'] for r in feed['shapes']}
    made = {}
    n = 0
    for t in feed['trips']:
        if t['trip_id'] not in extended or not t.get('shape_id'):
            continue
        src = t['shape_id']
        if src not in existing:
            continue
        dst = src + '+S0EXT'
        if dst not in made:
            base = shape_points(feed, src)
            if not base:
                continue
            # A Hunter line shape may run Newcastle-outward or outward-Newcastle,
            # so the corridor goes on whichever end actually sits at the
            # Interchange. If neither does, the shape is left alone rather than
            # spliced across the Hunter Valley.
            head_gap = haversine_ll(base[0], corridor[0])
            tail_gap = haversine_ll(base[-1], corridor[0])
            if min(head_gap, tail_gap) > S0_JOIN_TOLERANCE_M:
                continue
            if tail_gap <= head_gap:
                made[dst] = dedupe(base + corridor[1:])
            else:
                made[dst] = dedupe(list(reversed(corridor))[:-1] + base)
        if dst not in made:
            continue
        t['shape_id'] = dst
        n += 1
    for sid in sorted(made):
        feed['shapes'] += shape_rows(sid, made[sid])
    return n, len(made)


def haversine_ll(a, b):
    return hav(a, b)


def shape_coverage(feed, tol_m=500.0):
    """How often a trip's shape actually reaches the trip's last stop."""
    stops = {s['stop_id']: s for s in feed['stops']}
    sh = collections.defaultdict(list)
    for r in feed['shapes']:
        sh[r['shape_id']].append(r)
    by = group_trips(feed)
    total = short = 0
    worst = 0.0
    for t in feed['trips']:
        sid = t.get('shape_id')
        rows = by.get(t['trip_id'])
        if not sid or sid not in sh or not rows:
            continue
        last = stops.get(rows[-1]['stop_id'])
        if not last:
            continue
        ll = (float(last['stop_lat']), float(last['stop_lon']))
        pts = sorted(sh[sid], key=lambda r: int(r['shape_pt_sequence']))
        ends = [(float(pts[0]['shape_pt_lat']), float(pts[0]['shape_pt_lon'])),
                (float(pts[-1]['shape_pt_lat']), float(pts[-1]['shape_pt_lon']))]
        d = min(hav(e, ll) for e in ends)
        total += 1
        if d > tol_m:
            short += 1
            worst = max(worst, d)
    return dict(trips_with_shape=total, shape_short_of_last_stop=short,
                pct=round(100.0 * short / max(total, 1), 1),
                worst_gap_m=round(worst),
                note='pre-existing in the source GTFS; identical in every '
                     'scenario feed, so it cannot bias a scenario comparison')


def summarise(f, label):
    tids, rids = lr_trip_ids(f)
    by = group_trips(f)
    rt = {r['route_id']: r for r in f['routes']}
    trip_route = {t['trip_id']: t['route_id'] for t in f['trips']}
    # end-to-end run time of the trunk route, weekday
    svc = {t['trip_id'] for t in f['trips'] if t['service_id'] == 'WEEKDAY'}
    durs = collections.defaultdict(list)
    for tid, rows in by.items():
        if tid not in svc or len(rows) < 2:
            continue
        r = rt.get(trip_route.get(tid), {})
        nm = r.get('route_short_name', '')
        if nm in ('NLR', 'S1SHUTTLE', 'S3BRT') or r.get('route_type') in ('0',):
            durs[nm or r.get('route_id')].append(
                sec(rows[-1]['arrival_time']) - sec(rows[0]['departure_time']))
    return {'routes': len(f['routes']), 'trips': len(f['trips']),
            'stops': len(f['stops']), 'stop_times': len(f['stop_times']),
            'trunk_runtime_min': {k: round(sum(v) / len(v) / 60.0, 2)
                                  for k, v in durs.items() if v},
            'trunk_trips_weekday': {k: len(v) for k, v in durs.items()}}


def main():
    base = read_feed(BASE)
    print('base2026: routes=%d trips=%d stops=%d' %
          (len(base['routes']), len(base['trips']), len(base['stops'])), flush=True)
    out = {}
    geom = {}

    # ---- alignments, built once from observed geometry -------------------
    print('building alignments from the road and footway extracts ...', flush=True)
    graph = RoadGraph()
    ext_align = extension_alignment(graph)
    ext_km = polyline_length_m(ext_align) / 1000.0
    print('   S4/S5 extension corridor: %.2f km over %d points '
          '(SBC states %.2f km, %+.1f%%)'
          % (ext_km, len(ext_align), SBC_EXTENSION_KM,
             (ext_km / SBC_EXTENSION_KM - 1) * 100), flush=True)

    lr_west = shape_points(base, LR_SHAPE_OUT)[0]
    lr_east = shape_points(base, LR_SHAPE_OUT)[-1]
    tram_corridor, tram_obs_m, tram_tot_m = harbourside_corridor(lr_west, lr_east)
    rail_corridor, rail_obs_m, rail_tot_m = harbourside_corridor(
        lr_west, (S0_EXTENSION[-1][1], S0_EXTENSION[-1][2]))
    print('   S2c reserved corridor:    %.2f km, %.0f%% on observed OSM geometry'
          % (tram_tot_m / 1000.0, 100.0 * tram_obs_m / max(tram_tot_m, 1)), flush=True)
    print('   S0 rail corridor:         %.2f km, %.0f%% on observed OSM geometry'
          % (rail_tot_m / 1000.0, 100.0 * rail_obs_m / max(rail_tot_m, 1)), flush=True)

    bmd = site_extension_stops(ext_align, EXT_BROADMEADOW)
    jhh = site_extension_stops(ext_align, EXT_JHH)
    for nm, la, lo, src, off, along in bmd + jhh:
        print('   stop %-26s %.2f km out, %4.0f m from its anchor'
              % (nm, along / 1000.0, off), flush=True)
    bmd_stops = [(nm, la, lo, src) for nm, la, lo, src, _, _ in bmd]
    jhh_stops = [(nm, la, lo, src) for nm, la, lo, src, _, _ in jhh]
    # S4 runs the same corridor as S5, truncated at Broadmeadow, so the two
    # scenarios cannot differ by geometry over their shared section
    bmd_end = max(a for *_, a in bmd)
    ext_align_bmd = [p for p in ext_align
                     if project_onto(ext_align, p)[2] <= bmd_end + 1.0]
    geom['extension'] = dict(
        km=round(ext_km, 3), points=len(ext_align),
        sbc_stated_km=SBC_EXTENSION_KM,
        sbc_streets=list(SBC_EXTENSION_STREETS),
        s4_truncated_km=round(polyline_length_m(ext_align_bmd) / 1000.0, 3),
        source='modelled - routed over observed OSM centreline of the streets '
               'named in the 2020 NLR Extension Strategic Business Case; stop '
               'sitings remain assumed (DECISIONS.md 3.4, 10)')
    geom['reserved_corridor'] = dict(
        tram_km=round(tram_tot_m / 1000.0, 3),
        tram_observed_pct=round(100.0 * tram_obs_m / max(tram_tot_m, 1), 1),
        rail_km=round(rail_tot_m / 1000.0, 3),
        rail_observed_pct=round(100.0 * rail_obs_m / max(rail_tot_m, 1), 1),
        source='modelled - the retained harbour-side former-railway strip, '
               'observed in OSM where it survives (Foreshore Footpath) and '
               'interpolated across the redeveloped gap')

    # S2 - as built
    write_feed(renumber_sequences(base), os.path.join(OUT, 'S2.zip'))
    out['S2'] = summarise(base, 'S2')

    # S0 - heavy rail retained to Newcastle station
    s0, n_ext = extend_heavy_rail(base)
    n_trips, n_shapes = set_s0_rail_shapes(
        s0, rail_corridor, {'sydneytrains:S0_%d' % (i + 1)
                            for i in range(len(S0_EXTENSION))})
    write_feed(renumber_sequences(s0), os.path.join(OUT, 'S0.zip'))
    out['S0'] = summarise(s0, 'S0')
    out['S0']['heavy_rail_trips_extended'] = n_ext
    out['S0']['shapes_extended'] = dict(trips=n_trips, shapes=n_shapes)

    # S1 - bus shuttle from Wickham, no light rail
    s1, n1 = make_bus_shuttle(drop_lr(base), S1_SHUTTLE, 600, 'S1SHUTTLE',
                              'S1SHUTTLE', mode='3', speed_kmh=26.0, dwell_s=18.0)
    write_feed(renumber_sequences(s1), os.path.join(OUT, 'S1.zip'))
    out['S1'] = summarise(s1, 'S1')
    out['S1']['shuttle_trips'] = n1

    # S2a - charging dwell removed
    s2a = scale_lr_runtime(base, delta_per_intermediate_s=DWELL_FIXED,
                           delta_per_segment_s=-0.0)
    s2a = scale_lr_runtime(base, delta_per_intermediate_s=0.0,
                           delta_per_segment_s=-DWELL_CHARGING)
    write_feed(renumber_sequences(s2a), os.path.join(OUT, 'S2a.zip'))
    out['S2a'] = summarise(s2a, 'S2a')

    # S2b - full transit signal priority (75% of signal delay removed)
    saving = SIGNAL_DELAY_PER_INT * N_CORRIDOR_INTERSECTIONS * 0.75 / 5.0
    s2b = scale_lr_runtime(base, delta_per_segment_s=-saving)
    write_feed(renumber_sequences(s2b), os.path.join(OUT, 'S2b.zip'))
    out['S2b'] = summarise(s2b, 'S2b')
    out['S2b']['signal_delay_removed_s_per_segment'] = round(saving, 1)

    # S2c - Option A alignment on former railway land: reserved, fewer conflicts.
    # The stops move onto the corridor before the run time is decomposed, so the
    # timetable describes the reserved alignment rather than the street one.
    s2c_src = copy.deepcopy(base)
    n_moved = move_lr_stops_onto(s2c_src, tram_corridor)
    s2c = scale_lr_runtime(s2c_src, speed_kmh=CORRIDOR_SPEED,
                           delta_per_segment_s=-SIGNAL_DELAY_PER_INT * 0.6)
    set_reserved_alignment_shape(s2c, tram_corridor)
    write_feed(renumber_sequences(s2c), os.path.join(OUT, 'S2c.zip'))
    out['S2c'] = summarise(s2c, 'S2c')
    out['S2c']['stops_moved_to_reserved_corridor'] = n_moved

    # S3 - bus rapid transit on the same alignment
    brt_stops = [(n, la, lo) for n, la, lo in
                 [('Newcastle Interchange', -32.92433, 151.75943),
                  ('Honeysuckle', -32.92647, 151.76583),
                  ('Civic', -32.92699, 151.77175),
                  ('Crown Street', -32.92637, 151.77721),
                  ('Queens Wharf', -32.92633, 151.78164),
                  ('Newcastle Beach', -32.92748, 151.78626)]]
    s3, n3 = make_bus_shuttle(drop_lr(base), brt_stops, 450, 'S3BRT', 'S3BRT',
                              mode='3', speed_kmh=40.0, dwell_s=12.0)
    write_feed(renumber_sequences(s3), os.path.join(OUT, 'S3.zip'))
    out['S3'] = summarise(s3, 'S3')
    out['S3']['brt_trips'] = n3

    # S4 - extended to Broadmeadow
    s4 = extend_lr(base, bmd_stops, tag='BMD')
    out['S4_extension_km'] = round(set_lr_extension_shape(s4, ext_align_bmd) / 1000.0, 3)
    write_feed(renumber_sequences(s4), os.path.join(OUT, 'S4.zip'))
    out['S4'] = summarise(s4, 'S4')

    # S5 - extended to Broadmeadow and John Hunter Hospital
    s5 = extend_lr(base, bmd_stops + jhh_stops, tag='JHH')
    out['S5_extension_km'] = round(set_lr_extension_shape(s5, ext_align) / 1000.0, 3)
    write_feed(renumber_sequences(s5), os.path.join(OUT, 'S5.zip'))
    out['S5'] = summarise(s5, 'S5')

    # S6 - no trunk mode
    s6 = drop_lr(base)
    write_feed(renumber_sequences(s6), os.path.join(OUT, 'S6.zip'))
    out['S6'] = summarise(s6, 'S6')

    # Pre-existing source-feed limitation, measured so it is visible rather than
    # discovered later: some intercity shapes cover only part of the run they
    # belong to. It is identical in every scenario feed, so it cannot bias a
    # scenario comparison - but it is why the S0 corridor is spliced only onto
    # shapes that actually reach the Interchange (S0_JOIN_TOLERANCE_M) instead
    # of onto every extended trip.
    geom['source_shape_coverage'] = shape_coverage(base)
    out['_geometry'] = geom
    json.dump(out, open(os.path.join(OUT, '_scenario_schedule_report.json'), 'w'), indent=2)
    for k in ['S0', 'S1', 'S2', 'S2a', 'S2b', 'S2c', 'S3', 'S4', 'S5', 'S6']:
        v = out[k]
        print('%-5s routes=%-4d trips=%-6d stops=%-5d trunk_runtime=%s'
              % (k, v['routes'], v['trips'], v['stops'], v['trunk_runtime_min']), flush=True)


if __name__ == '__main__':
    main()
