#!/usr/bin/env python
"""Grade the corridor's road attributes by evidence, and derive the E1 road variants.

Why this exists
---------------
DECISIONS.md 3.1 reported network-wide imputation rates (75.4% of `num_lanes`,
98.0% of `kerbside_use`) and concluded that the Hunter/Scott corridor needed
manual correction from aerial imagery before any B3 net-arrivals figure could be
published. Measured *on the corridor* rather than network-wide, that conclusion
does not hold: OSM tags 89.7% of corridor lane counts and 97.4% of corridor
speed limits. The corridor is one of the best-mapped parts of the extract, not
the worst.

So the job is not to invent corridor geometry. It is to:

  1. separate what OSM observed from what `build_network_layers.py` defaulted,
     per edge and per field - A1 records imputation only as a global counter, so
     downstream code currently cannot tell a measured lane count from a guess;
  2. resolve the OSM turn-restriction relations to real coordinates, so the
     banned-turn counts asserted in `scenarios/E1_road_variants.csv` become
     auditable instead of assumed;
  3. state the counterfactual - Hunter/Scott *without* the tram - as an explicit,
     swept assumption, because no 2026 observation can supply it.

Nothing here is digitised by hand and nothing is measured from imagery.

Corridor definition (deterministic, geometric, no hand-drawn extent)
--------------------------------------------------------------------
The alignment comes from the GTFS shapes of the tram route in each scenario feed
(base2026 for the as-built corridor, S2c/S4/S5 for the alternative and extended
alignments), so the corridor extent is derived from the same artefacts the
scenarios are built from.

    corridor_trunk   a named trunk-corridor street (Hunter/Scott, plus the
                     extension streets for S4/S5) within 60 m of that alignment.
                     These are the streets the tram takes road space from.
    corridor_cross   any other road within 40 m of the alignment - the cross
                     streets at the 14 signalised intersections, which is where
                     the banned turns live.
    parallel         the named parallel and comparator routes within 1.5 km -
                     the diversion paths that carry whatever B3 displaces.

Outputs
-------
    data/processed/network/A1_corridor_road_edges.csv      per-edge, per-field provenance
    data/processed/network/A2_turn_restrictions_resolved.csv  restrictions with geometry
    data/processed/network/A1_road_variant_patches.csv     E1 variants as edge-level deltas
    data/processed/network/_corridor_attributes_report.json
"""
import os
import io
import sys
import csv
import json
import math
import zipfile
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from osm_parse import parse, haversine, fnum

OUT = 'data/processed/network'
ROADS_OSM = 'networks/osm/newcastle_roads.osm'
SIGNALS_OSM = 'networks/osm/newcastle_signals.osm'
E1_ROAD_VARIANTS = 'scenarios/E1_road_variants.csv'

# Alignment source per variant.
#
# `shape` uses the tram route's own GTFS shape. `stops` interpolates through the
# tram route's stop sequence instead, and is used for S4/S5 because those feeds
# add extension stops (Hamilton, Broadmeadow, Lambton, John Hunter Hospital)
# without extending the shape: all four scenario feeds still carry the 275-point
# as-built 2.7 km shape. That is a P1 defect - recorded in DECISIONS.md 3.4 - and
# it means the extension corridor has to be derived from the (assumed) stop
# sitings rather than from a surveyed alignment. S2c is affected in the same way,
# but its road variant is the full-capacity Hunter Street network, so the missing
# reserved-alignment geometry does not change any road attribute here.
ALIGNMENT_FEEDS = {
    'base2026': ('schedules/raw/base2026/lightrail.zip', 'shape'),
    'S2c': ('schedules/scenarios/S2c.zip', 'shape'),
    'S4': ('schedules/scenarios/S4.zip', 'stops'),
    'S5': ('schedules/scenarios/S5.zip', 'stops'),
}

# The streets the tram takes road space from on the as-built corridor. Hunter and
# Scott are observed: the alignment runs in their carriageway.
TRUNK_STREETS = {
    'base2026': ('Hunter Street', 'Scott Street'),
    'S2c': ('Hunter Street', 'Scott Street'),
}

# For the extensions the street set is not asserted. Any named road of a trunk-ish
# class within CORRIDOR_TRUNK_M of the extension polyline is treated as carrying
# the lane take, so the extension corridor follows the assumed stop sitings rather
# than a hand-picked list of street names.
EXTENSION_VARIANTS = ('S4', 'S5')
TRUNKISH = ('motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified')

# Named parallel and comparator routes: the alternative east-west paths through
# the CBD plus the north-south connectors that feed them.
PARALLEL_STREETS = (
    'King Street', 'Wharf Road', 'Honeysuckle Drive', 'Parry Street', 'Tudor Street',
    'Darby Street', 'Beaumont Street', 'Union Street', 'Stewart Avenue', 'Church Street',
    'Watt Street', 'Newcomen Street', 'Perkins Street', 'Merewether Street',
    'Steel Street', 'Denison Street', 'National Park Street', 'Bull Street',
    'Auckland Street', 'Brown Street', 'Wolfe Street', 'Pacific Street',
    'Telford Street', 'Worth Place', 'Railway Street', 'Hannell Street',
)

CORRIDOR_TRUNK_M = 60.0
CORRIDOR_CROSS_M = 40.0
PARALLEL_M = 1500.0

# Defaults from build_network_layers.py, repeated here so a value that came from
# a rule can be identified as such rather than re-derived.
SPEED_DEFAULT = {'motorway': 100, 'trunk': 80, 'primary': 60, 'secondary': 60,
                 'tertiary': 50, 'unclassified': 50, 'residential': 50,
                 'living_street': 10, 'service': 20, 'motorway_link': 60,
                 'trunk_link': 60, 'primary_link': 50, 'secondary_link': 50,
                 'tertiary_link': 40, 'road': 50, 'busway': 50}
LANES_DEFAULT = {'motorway': 2, 'trunk': 2, 'primary': 2, 'secondary': 1, 'tertiary': 1,
                 'unclassified': 1, 'residential': 1, 'living_street': 1, 'service': 1,
                 'motorway_link': 1, 'trunk_link': 1, 'primary_link': 1,
                 'secondary_link': 1, 'tertiary_link': 1, 'road': 1, 'busway': 1}
CAP_DEFAULT = {'motorway': 2000, 'trunk': 1800, 'primary': 1600, 'secondary': 1400,
               'tertiary': 1200, 'unclassified': 1000, 'residential': 800,
               'living_street': 300, 'service': 400, 'motorway_link': 1500,
               'trunk_link': 1400, 'primary_link': 1200, 'secondary_link': 1100,
               'tertiary_link': 1000, 'road': 1000, 'busway': 1200}

# --------------------------------------------------------------------------
# The counterfactual. Hunter/Scott before the tram cannot be observed in a 2026
# extract, so it is assumed and swept. `lanes_per_direction=2` is the value
# `scenarios/E1_road_variants.csv` already carries; the sweep is what makes it
# honest. See DECISIONS.md 3.4.
# --------------------------------------------------------------------------
PRE_LR_LANES_PER_DIR = 2
PRE_LR_LANES_SWEEP = (1, 2)
PRE_LR_KERBSIDE = 'parking'
EXTENSION_LANE_TAKE = 1          # lanes removed per direction on an extension trunk
EXTENSION_LANE_TAKE_SWEEP = (0, 1)


# --------------------------------------------------------------------------
# geometry helpers - a local equirectangular projection and a 100 m grid, so a
# 43,112-way distance sweep runs in seconds and does so identically every time.
# --------------------------------------------------------------------------
class Near:
    """Grid index over alignment points; nearest-point distance in metres."""

    CELL = 100.0

    def __init__(self, pts):
        self.lat0 = sum(p[0] for p in pts) / len(pts)
        self.kx = 111320.0 * math.cos(math.radians(self.lat0))
        self.ky = 110540.0
        self.pts = [self._xy(p) for p in pts]
        self.grid = collections.defaultdict(list)
        for i, (x, y) in enumerate(self.pts):
            self.grid[(int(x // self.CELL), int(y // self.CELL))].append(i)

    def _xy(self, p):
        return (p[1] * self.kx, p[0] * self.ky)

    def dist(self, p, cutoff=2000.0):
        x, y = self._xy(p)
        r = int(cutoff // self.CELL) + 1
        cx, cy = int(x // self.CELL), int(y // self.CELL)
        best = float('inf')
        for i in range(cx - r, cx + r + 1):
            for j in range(cy - r, cy + r + 1):
                for k in self.grid.get((i, j), ()):
                    px, py = self.pts[k]
                    d = math.hypot(px - x, py - y)
                    if d < best:
                        best = d
        return best

    def dist_way(self, pts, cutoff=2000.0):
        return min((self.dist(p, cutoff) for p in pts), default=float('inf'))


def densify(pts, step_m=25.0):
    """Interpolate a polyline so a buffer test cannot fall through long legs."""
    out = []
    for a, b in zip(pts, pts[1:]):
        d = haversine(a, b)
        n = max(1, int(d // step_m))
        for i in range(n):
            f = i / float(n)
            out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
    out.append(pts[-1])
    return out


def read_alignment(zip_path, mode='shape'):
    """Tram-route alignment points from a GTFS feed, in stable order.

    mode='shape' reads shapes.txt; mode='stops' interpolates through the stop
    sequence of the longest tram trip, for feeds whose shape was not extended.
    """
    z = zipfile.ZipFile(zip_path)

    def rd(name):
        m = [x for x in z.namelist() if x.endswith(name)]
        if not m:
            return []
        with z.open(m[0]) as f:
            return list(csv.DictReader(io.TextIOWrapper(f, 'utf-8-sig')))

    routes = rd('routes.txt')
    tram = {r['route_id'] for r in routes if r.get('route_type') == '0'}
    trips = [t for t in rd('trips.txt') if t.get('route_id') in tram]
    if not trips:
        return []

    if mode == 'stops':
        stops = {s['stop_id']: (float(s['stop_lat']), float(s['stop_lon']))
                 for s in rd('stops.txt')}
        by_trip = collections.defaultdict(list)
        tids = {t['trip_id'] for t in trips}
        for r in rd('stop_times.txt'):
            if r['trip_id'] in tids:
                by_trip[r['trip_id']].append(r)
        pts = []
        # one representative trip per direction, longest stop sequence first, so
        # the extension legs are always present
        seen = {}
        dirs = {t['trip_id']: t.get('direction_id', '0') for t in trips}
        for tid, rows in sorted(by_trip.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            d = dirs.get(tid, '0')
            if d in seen:
                continue
            seen[d] = tid
            seq = sorted(rows, key=lambda r: int(r['stop_sequence']))
            leg = [stops[r['stop_id']] for r in seq if r['stop_id'] in stops]
            if len(leg) >= 2:
                pts += densify(leg)
        return pts

    shape_ids = {t['shape_id'] for t in trips if t.get('shape_id')}
    by = collections.defaultdict(list)
    for r in rd('shapes.txt'):
        if not shape_ids or r['shape_id'] in shape_ids:
            by[r['shape_id']].append(r)
    pts = []
    for sid in sorted(by):
        rows = sorted(by[sid], key=lambda r: int(r['shape_pt_sequence']))
        pts += [(float(r['shape_pt_lat']), float(r['shape_pt_lon'])) for r in rows]
    return pts


def load_roads():
    """(node index, [(way_id, refs, tags, pts, length_m)]) from the road extract."""
    idx = {}
    raw = []
    for rec in parse(ROADS_OSM):
        if rec[0] == 'node':
            idx[rec[1]] = (rec[2], rec[3])
        elif rec[0] == 'way' and 'highway' in rec[3]:
            raw.append((rec[1], rec[2], rec[3]))
    ways = []
    for wid, refs, tags in raw:
        pts = [idx[r] for r in refs if r in idx]
        if len(pts) < 2:
            continue
        L = sum(haversine(a, b) for a, b in zip(pts, pts[1:]))
        if L <= 0:
            continue
        ways.append((wid, refs, tags, pts, L))
    return idx, ways


def sample(pts, n=12):
    """Up to n evenly spaced points of a way, endpoints always included."""
    if len(pts) <= n:
        return pts
    step = (len(pts) - 1) / float(n - 1)
    return [pts[int(round(i * step))] for i in range(n)]


# --------------------------------------------------------------------------
# per-field provenance
# --------------------------------------------------------------------------
def grade(tags):
    """Resolve each attribute and say where the value came from.

    Returns a dict of value/source pairs. `osm` means the tag was present on the
    way; `imputed_rule` means build_network_layers.py's class default applied.
    """
    hw = tags['highway']
    out = {}

    oneway = tags.get('oneway') in ('yes', '1', '-1', 'true')
    out['oneway_flag'] = int(oneway)
    out['oneway_source'] = 'osm' if 'oneway' in tags else 'imputed_rule'

    ln = fnum(tags.get('lanes'))
    if ln is None:
        out['num_lanes_per_dir'] = float(LANES_DEFAULT.get(hw, 1))
        out['num_lanes_source'] = 'imputed_rule'
    else:
        # OSM `lanes` counts both directions on a two-way street.
        out['num_lanes_per_dir'] = ln if oneway else max(1.0, ln / 2.0)
        out['num_lanes_source'] = 'osm'

    sl = fnum(tags.get('maxspeed'))
    out['speed_limit_kmh'] = float(sl) if sl is not None else float(SPEED_DEFAULT.get(hw, 50))
    out['speed_limit_source'] = 'osm' if sl is not None else 'imputed_rule'

    w = fnum(tags.get('width'))
    out['lane_width_m'] = float(w) if w is not None else 3.2
    out['lane_width_source'] = 'osm' if w is not None else 'imputed_rule'

    out['turn_lanes'] = tags.get('turn:lanes', '')
    out['turn_lanes_source'] = 'osm' if 'turn:lanes' in tags else 'absent'

    kerb, ksrc = kerbside(tags)
    out['kerbside_use'] = kerb
    out['kerbside_source'] = ksrc

    out['capacity_veh_hr_lane'] = CAP_DEFAULT.get(hw, 1000)
    out['capacity_source'] = 'imputed_rule'   # Austroads-style, DECISIONS 3.2
    return out


def kerbside(tags):
    """Kerbside use, and whether OSM said so or a rule did."""
    if tags.get('railway') == 'tram' or tags.get('embedded_rails'):
        return 'tram_lane', 'osm'
    if tags.get('highway') == 'busway' or 'bus' in (tags.get('lanes:psv') or ''):
        return 'bus_lane', 'osm'
    vals = [v for k, v in tags.items() if k.startswith('parking:')]
    if any(v in ('no', 'no_stopping', 'no_parking') for v in vals):
        return 'clearway', 'osm'
    if any(v in ('parallel', 'perpendicular', 'diagonal', 'lane', 'street_side', 'yes')
           for v in vals):
        return 'parking', 'osm'
    return 'unknown', 'imputed_rule'


# --------------------------------------------------------------------------
# turn restrictions
# --------------------------------------------------------------------------
def resolve_restrictions(node_idx, ways, near_by_variant):
    """Give every OSM restriction relation a coordinate and a corridor distance.

    `A2_turn_restrictions_osm.csv` stores member strings only, so the restriction
    count on the corridor could not previously be checked against E1. Restrictions
    are located by their via member: a via node directly, else the midpoint of a
    via way, else the midpoint of the `from` way.
    """
    waypt = {}
    for wid, refs, tags, pts, L in ways:
        waypt[wid] = pts[len(pts) // 2]

    signal_nodes = {}
    rels = []
    for rec in parse(SIGNALS_OSM):
        if rec[0] == 'node':
            signal_nodes[rec[1]] = (rec[2], rec[3])
        elif rec[0] == 'rel' and rec[3].get('type') == 'restriction':
            rels.append((rec[1], rec[2], rec[3]))

    rows = []
    unresolved = 0
    for rid, members, tags in rels:
        pt, how = None, ''
        for typ, ref, role in members:
            if role == 'via' and typ == 'node':
                pt = signal_nodes.get(ref) or node_idx.get(ref)
                how = 'via_node'
                if pt:
                    break
        if pt is None:
            for typ, ref, role in members:
                if role == 'via' and typ == 'way' and ref in waypt:
                    pt, how = waypt[ref], 'via_way'
                    break
        if pt is None:
            for typ, ref, role in members:
                if role == 'from' and typ == 'way' and ref in waypt:
                    pt, how = waypt[ref], 'from_way'
                    break
        if pt is None:
            unresolved += 1
            continue
        frm = next((r for t, r, ro in members if ro == 'from'), '')
        to = next((r for t, r, ro in members if ro == 'to'), '')
        via = next((r for t, r, ro in members if ro == 'via'), '')
        row = dict(rel_id=rid,
                   restriction=tags.get('restriction', '')
                   or tags.get('restriction:motorcar', '') or 'unspecified',
                   from_way=frm, via_member=via, to_way=to,
                   lat=round(pt[0], 7), lon=round(pt[1], 7),
                   located_by=how, source='osm')
        for name, nr in near_by_variant.items():
            row['dist_to_%s_m' % name] = round(nr.dist_way([pt], cutoff=3000.0), 1)
        d0 = row['dist_to_base2026_m']
        row['corridor_flag'] = int(d0 <= CORRIDOR_CROSS_M)
        rows.append(row)
    rows.sort(key=lambda r: (r['dist_to_base2026_m'], r['rel_id']))
    return rows, unresolved


# --------------------------------------------------------------------------
# main build
# --------------------------------------------------------------------------
def build():
    os.makedirs(OUT, exist_ok=True)
    print('reading alignments ...', flush=True)
    align = {k: read_alignment(p, m) for k, (p, m) in ALIGNMENT_FEEDS.items()}
    near = {k: Near(v) for k, v in align.items() if v}
    for k, v in align.items():
        print('   %-9s %5d points (%s)' % (k, len(v), ALIGNMENT_FEEDS[k][1]))

    print('reading %s ...' % ROADS_OSM, flush=True)
    node_idx, ways = load_roads()
    print('   %d road ways with usable geometry' % len(ways), flush=True)

    print('classifying corridor membership ...', flush=True)
    rows = []
    for wid, refs, tags, pts, L in ways:
        sp = sample(pts)
        d = {k: round(nr.dist_way(sp, cutoff=PARALLEL_M + 200), 1) for k, nr in near.items()}
        dmin_base = d['base2026']
        name = tags.get('name', '')

        classes = []
        for variant in near:
            if name in TRUNK_STREETS.get(variant, ()) and d[variant] <= CORRIDOR_TRUNK_M:
                classes.append('corridor_trunk:%s' % variant)
            elif (variant in EXTENSION_VARIANTS and name
                    and tags['highway'] in TRUNKISH and d[variant] <= CORRIDOR_TRUNK_M):
                classes.append('corridor_trunk:%s' % variant)
        if dmin_base <= CORRIDOR_CROSS_M and not any(
                c.startswith('corridor_trunk:base2026') for c in classes):
            classes.append('corridor_cross')
        if name in PARALLEL_STREETS and dmin_base <= PARALLEL_M and not classes:
            classes.append('parallel')
        if not classes:
            continue

        g = grade(tags)
        r = dict(edge_id='w' + wid, osm_way_id=wid, name=name,
                 road_class=tags['highway'], length_m=round(L, 1),
                 corridor_class=';'.join(classes),
                 is_corridor_trunk=int(any(c.startswith('corridor_trunk') for c in classes)),
                 dist_to_alignment_m=dmin_base)
        r.update(g)
        for k, v in sorted(d.items()):
            r['dist_to_%s_m' % k] = v
        r['scenario_variant_ref'] = 'base2026'
        rows.append(r)
    rows.sort(key=lambda r: (r['dist_to_alignment_m'], r['edge_id']))
    print('   %d corridor / parallel edges' % len(rows), flush=True)

    print('resolving turn restrictions ...', flush=True)
    restr, unresolved = resolve_restrictions(node_idx, ways, near)
    print('   %d resolved, %d unresolvable' % (len(restr), unresolved), flush=True)

    patches, variant_report = build_variant_patches(rows, restr)

    # ---- write ----
    write_csv('A1_corridor_road_edges.csv', rows)
    write_csv('A2_turn_restrictions_resolved.csv', restr)
    write_csv('A1_road_variant_patches.csv', patches)

    report = dict(
        corridor_definition=dict(
            trunk_buffer_m=CORRIDOR_TRUNK_M, cross_buffer_m=CORRIDOR_CROSS_M,
            parallel_buffer_m=PARALLEL_M,
            alignment_source={k: dict(feed=p, mode=m, points=len(align[k]))
                              for k, (p, m) in ALIGNMENT_FEEDS.items()},
            trunk_streets=TRUNK_STREETS,
            extension_variants=list(EXTENSION_VARIANTS),
            p1_defect=('S2c/S4/S5 scenario feeds carry the unmodified 275-point as-built '
                       'shape; extension geometry is therefore derived from the assumed '
                       'stop sitings, not from a surveyed alignment. DECISIONS.md 3.4.')),
        counts=dict(
            edges_total=len(rows),
            corridor_trunk_base2026=sum(1 for r in rows
                                        if 'corridor_trunk:base2026' in r['corridor_class']),
            corridor_cross=sum(1 for r in rows if 'corridor_cross' in r['corridor_class']),
            parallel=sum(1 for r in rows if 'parallel' in r['corridor_class']),
            km_corridor_trunk=round(sum(r['length_m'] for r in rows
                                        if 'corridor_trunk:base2026' in r['corridor_class'])
                                    / 1000, 2)),
        observed_share=observed_share(rows),
        turn_restrictions=dict(
            resolved=len(restr), unresolvable=unresolved,
            within_40m_of_alignment=sum(1 for r in restr if r['dist_to_base2026_m'] <= 40),
            within_80m_of_alignment=sum(1 for r in restr if r['dist_to_base2026_m'] <= 80),
            within_300m_of_alignment=sum(1 for r in restr if r['dist_to_base2026_m'] <= 300),
            by_type=dict(collections.Counter(
                r['restriction'] for r in restr if r['dist_to_base2026_m'] <= 80))),
        road_variants=variant_report,
        assumptions=dict(
            pre_lr_lanes_per_direction=dict(value=PRE_LR_LANES_PER_DIR,
                                            sweep=list(PRE_LR_LANES_SWEEP),
                                            source='assumed',
                                            note='Hunter/Scott before the tram cannot be '
                                                 'observed in a 2026 extract.'),
            pre_lr_kerbside_use=dict(value=PRE_LR_KERBSIDE, source='assumed'),
            extension_lane_take_per_direction=dict(value=EXTENSION_LANE_TAKE,
                                                   sweep=list(EXTENSION_LANE_TAKE_SWEEP),
                                                   source='assumed')))
    with open(os.path.join(OUT, '_corridor_attributes_report.json'), 'w',
              encoding='utf-8', newline='\n') as f:
        json.dump(report, f, indent=2)
        f.write('\n')
    print(json.dumps(report, indent=2))


def observed_share(rows):
    """Share of each field that OSM actually stated, by corridor class."""
    fields = ('num_lanes', 'speed_limit', 'oneway', 'lane_width', 'kerbside')
    out = {}
    groups = dict(
        corridor_trunk=[r for r in rows if 'corridor_trunk:base2026' in r['corridor_class']],
        corridor_cross=[r for r in rows if 'corridor_cross' in r['corridor_class']],
        parallel=[r for r in rows if 'parallel' in r['corridor_class']],
        all=rows)
    for g, sel in groups.items():
        n = len(sel)
        out[g] = dict(n=n, **{f: (round(100.0 * sum(1 for r in sel
                                                    if r['%s_source' % f] == 'osm') / n, 1)
                                  if n else None) for f in fields})
    return out


def build_variant_patches(rows, restr):
    """Turn `scenarios/E1_road_variants.csv` into edge-level attribute deltas.

    A patch row is only written where a variant *departs* from the observed
    network, so the as-built variant is empty by construction and the check in
    tests/check_package.py ('variants differ only where E1 says') is structural
    rather than a diff after the fact.
    """
    variants = list(csv.DictReader(open(E1_ROAD_VARIANTS, encoding='utf-8')))
    trunk_by_variant = {}
    for v in ('base2026', 'S2c', 'S4', 'S5'):
        trunk_by_variant[v] = [r for r in rows if 'corridor_trunk:%s' % v in r['corridor_class']]

    patches = []
    report = {}
    for v in variants:
        ref = v['road_variant_ref']
        want_lanes = float(v['hunter_st_lanes_per_direction'])
        kerb_removed = v['kerbside_parking_removed'] == '1'
        e1_banned = int(v['banned_turn_movements'])

        if ref == 'net_base2026':
            scope, target_lanes, lane_src, sweep = [], None, 'osm', None
        elif ref == 'net_base2026_hunter_st_full_capacity':
            scope = trunk_by_variant['base2026']
            target_lanes, lane_src, sweep = float(PRE_LR_LANES_PER_DIR), 'assumed', PRE_LR_LANES_SWEEP
        elif ref == 'net_base2026_broadmeadow_extension':
            scope = [r for r in trunk_by_variant['S4']
                     if 'corridor_trunk:base2026' not in r['corridor_class']]
            target_lanes, lane_src, sweep = None, 'assumed', EXTENSION_LANE_TAKE_SWEEP
        elif ref == 'net_base2026_jhh_extension':
            scope = [r for r in trunk_by_variant['S5']
                     if 'corridor_trunk:base2026' not in r['corridor_class']]
            target_lanes, lane_src, sweep = None, 'assumed', EXTENSION_LANE_TAKE_SWEEP
        else:
            scope, target_lanes, lane_src, sweep = [], None, 'assumed', None

        n_lane, n_kerb = 0, 0
        for r in scope:
            obs = float(r['num_lanes_per_dir'])
            new = target_lanes if target_lanes is not None \
                else max(1.0, obs - EXTENSION_LANE_TAKE)
            new_kerb = PRE_LR_KERBSIDE if not kerb_removed else 'clearway'
            lane_change = abs(new - obs) > 1e-9
            kerb_change = new_kerb != r['kerbside_use']
            if not (lane_change or kerb_change):
                continue
            n_lane += int(lane_change)
            n_kerb += int(kerb_change)
            if ref == 'net_base2026_hunter_st_full_capacity':
                why = ('pre-tram reconstruction: road space and kerbside restored. '
                       'Not observable in a 2026 extract; assumed and swept '
                       '(DECISIONS 3.4)')
            elif lane_change:
                why = ('extension lane take: one lane per direction to the tram, '
                       'mirroring the as-built corridor. Assumed and swept')
            else:
                why = ('extension kerbside take: the street is already single-lane, '
                       'so the tram takes the kerbside rather than a running lane. '
                       'Assumed')
            patches.append(dict(
                road_variant_ref=ref, edge_id=r['edge_id'], name=r['name'],
                corridor_class=r['corridor_class'],
                fields_changed=';'.join(f for f, c in
                                        (('num_lanes_per_dir', lane_change),
                                         ('kerbside_use', kerb_change)) if c),
                field_num_lanes_per_dir_from=obs,
                field_num_lanes_per_dir_to=new if lane_change else '',
                num_lanes_observed_source=r['num_lanes_source'],
                field_kerbside_use_from=r['kerbside_use'],
                field_kerbside_use_to=new_kerb if kerb_change else '',
                kerbside_observed_source=r['kerbside_source'],
                capacity_veh_hr_lane=r['capacity_veh_hr_lane'],
                signal_cycle_s=v['signal_cycle_s'],
                tram_lane_present=v['tram_lane_present'],
                source=lane_src,
                sweep_low=(sweep[0] if sweep else ''),
                sweep_high=(sweep[1] if sweep else ''),
                rationale=why))

        obs_banned = sum(1 for x in restr if x['dist_to_base2026_m'] <= CORRIDOR_CROSS_M)
        report[ref] = dict(
            edges_in_scope=len(scope), patched_lanes=n_lane, patched_kerbside=n_kerb,
            e1_lanes_per_direction=want_lanes,
            observed_modal_lanes_per_direction=modal_lanes(trunk_by_variant['base2026']),
            e1_banned_turn_movements=e1_banned,
            observed_restrictions_within_40m=obs_banned,
            lane_source=lane_src)
    return patches, report


def modal_lanes(rows):
    if not rows:
        return None
    c = collections.Counter(float(r['num_lanes_per_dir']) for r in rows
                            if r['num_lanes_source'] == 'osm')
    return c.most_common(1)[0][0] if c else None


def write_csv(name, rows):
    p = os.path.join(OUT, name)
    if not rows:
        print('   (no rows) %s' % name)
        # still write the header-less empty file so the artefact exists
        open(p, 'w', encoding='utf-8', newline='\n').close()
        return
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with open(p, 'w', newline='\n', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    print('   wrote %-40s %6d rows' % (name, len(rows)))


if __name__ == '__main__':
    build()
