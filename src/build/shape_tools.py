#!/usr/bin/env python
"""Build GTFS shape geometry for scenario feeds from observed network geometry.

Why this exists
---------------
The P1 scenario feeds added or moved stops without ever extending the tram's
GTFS shape, so S0, S2c, S4 and S5 all carried the same 275-point as-built
2.7 km geometry (DECISIONS.md 3.4). A stop that hangs off the end of a shape
gets mapped by pt2matsim onto whatever link happens to be nearest, which for
the extensions means the as-built corridor and for S2c means the on-street
Hunter/Scott alignment the scenario exists to avoid.

Rather than digitise an alignment by hand, every shape here is routed over
geometry the package already observes:

    road corridor   Dijkstra over the A1 road edges, with the streets named in
                    the published corridor description weighted down so the
                    route follows them and bridges any gap between them.
    reserved rail   the retained harbour-side corridor, observed in OSM where
                    it survives and interpolated across the redeveloped gap.

The stop *sitings* remain assumed - that does not change. What changes is that
the geometry joining them is now observed street centreline instead of absent.

Determinism: adjacency lists are sorted by edge id, the priority queue breaks
ties on node id, and no dict iteration order reaches a result. Repeat runs
produce byte-identical output.
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
import heapq
import collections

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from osm_parse import parse, haversine

# Model inputs come from config/registry/<city>/, not from literals here. Every
# value below carries its units, provenance and either a sweep, a held-fixed rule
# or a derived-from identity there. See DECISIONS.md 15.
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import registry as _registry  # noqa: E402
CFG = _registry.load()

ROAD_EDGES = _city.path('data/processed/network/A1_road_edges.csv')
ROAD_GEOM = _city.path('data/processed/network/A1_road_geometry.jsonl')
FOOTWAYS_OSM = _city.path('networks/osm/footways.osm')
RAILWAYS_OSM = _city.path('networks/osm/railways.osm')

# The window searched for the surviving harbour-side strip of the former rail
# corridor. Declared in cities/<city>/geometry/analysis_extents.json rather than
# typed here; the ORDER is (south, north, west, east), matching the comparison
# in _osm_named_ways. Value-identical to the tuple it replaced.
_HS = _city.extent('harbourside_corridor_search')
_HARBOURSIDE_BBOX = (_HS['s'], _HS['n'], _HS['w'], _HS['e'])

# A route is allowed to leave the named corridor, but pays for it. The penalty
# is a cost multiplier on off-corridor edges: high enough that a parallel back
# street is never preferred to the named street, low enough that a genuine gap
# (a roundabout, an unnamed slip, a bridge deck) is still bridgeable.
OFF_CORRIDOR_PENALTY = CFG.get('A.corridor.off_corridor_penalty')

# Classes a tram or a bus can plausibly run in. Service ways and tracks are
# excluded so a route cannot cut through a car park or a fire trail.
RUNNING_CLASSES = frozenset((
    'motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'unclassified',
    'residential', 'living_street', 'busway',
    'trunk_link', 'primary_link', 'secondary_link', 'tertiary_link',
))


def densify(pts, step_m=25.0):
    """Interpolate a polyline so no leg is longer than step_m."""
    if len(pts) < 2:
        return list(pts)
    out = []
    for a, b in zip(pts, pts[1:]):
        d = haversine(a, b)
        n = max(1, int(d // step_m))
        for i in range(n):
            f = i / float(n)
            out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
    out.append(pts[-1])
    return out


def polyline_length_m(pts):
    return sum(haversine(a, b) for a, b in zip(pts, pts[1:]))


def dedupe(pts, tol_m=1.0):
    """Drop consecutive near-duplicate points; GTFS consumers dislike them."""
    out = []
    for p in pts:
        if not out or haversine(out[-1], p) > tol_m:
            out.append(p)
    return out


class RoadGraph:
    """Undirected routable graph over the observed A1 road geometry.

    The A1 layer stores one edge per OSM *way*, not per intersection-to-
    intersection segment, so two streets that cross mid-way share no endpoint
    and a graph keyed on `from_node`/`to_node` is disconnected. The graph is
    therefore keyed on the shared *vertex coordinates* instead: geometry comes
    straight from the OSM node coordinates, so two ways meeting at a junction
    carry the identical coordinate pair and join there.

    Undirected on purpose: a shape is a route centreline, not a movement, and
    the one-way pairs on Hunter and Scott would otherwise force a shape to
    detour around the block it is supposed to run along.
    """

    def __init__(self, classes=RUNNING_CLASSES):
        geom = {}
        with open(ROAD_GEOM, encoding='utf-8') as f:
            for ln in f:
                d = json.loads(ln)
                geom[d['edge_id']] = [(c[1], c[0]) for c in d['coords']]
        ways = []
        with open(ROAD_EDGES, encoding='utf-8') as f:
            for r in csv.DictReader(f):
                if classes and r['road_class'] not in classes:
                    continue
                pts = geom.get(r['edge_id'])
                if pts and len(pts) >= 2:
                    ways.append((r['edge_id'], (r['name'] or '').strip(), pts))
        ways.sort(key=lambda w: w[0])
        self._build(ways)

    def _build(self, ways):
        """Adjacency, node index and lookup grid from [(id, name, points)].

        Split out of __init__ so a subclass can assemble `ways` from a
        different set of layers - measure_network_factors.ActiveGraph unions
        the A6 active edges with the roads a pedestrian may use - without
        duplicating the graph construction or changing it.
        """
        self.adj = collections.defaultdict(list)
        self.node_xy = {}
        for eid, name, pts in ways:
            for a, b in zip(pts, pts[1:]):
                if a == b:
                    continue
                length = haversine(a, b)
                if length <= 0:
                    continue
                self.node_xy.setdefault(a, a)
                self.node_xy.setdefault(b, b)
                self.adj[a].append((b, eid, length, name))
                self.adj[b].append((a, eid, length, name))
        for k in self.adj:
            self.adj[k].sort(key=lambda e: (e[1], e[0]))
        self._grid = collections.defaultdict(list)
        for lat, lon in self.node_xy:
            self._grid[(int(lat * 200), int(lon * 200))].append((lat, lon))
        for k in self._grid:
            self._grid[k].sort()

    def nearest_node(self, latlon, max_rings=8):
        """Nearest graph node to a coordinate, searched outward by grid ring."""
        klat, klon = int(latlon[0] * 200), int(latlon[1] * 200)
        best, bestd = None, float('inf')
        for ring in range(max_rings + 1):
            for dlat in range(-ring, ring + 1):
                for dlon in range(-ring, ring + 1):
                    if ring and max(abs(dlat), abs(dlon)) != ring:
                        continue
                    for n in self._grid.get((klat + dlat, klon + dlon), ()):
                        d = haversine(latlon, n)
                        if d < bestd or (d == bestd and (best is None or n < best)):
                            best, bestd = n, d
            if best is not None and ring >= 1:
                break
        return best, bestd

    def shortest_path(self, src, dst, prefer_names=frozenset(),
                      penalty=OFF_CORRIDOR_PENALTY):
        """Dijkstra from src to dst, discounting edges on the named streets.

        Returns the coordinate polyline, or None if unreachable.
        """
        prefer = frozenset(n.lower() for n in prefer_names)
        dist = {src: 0.0}
        prev = {}
        pq = [(0.0, src)]
        seen = set()
        while pq:
            d, u = heapq.heappop(pq)
            if u in seen:
                continue
            seen.add(u)
            if u == dst:
                break
            for v, eid, length, name in self.adj[u]:
                if v in seen:
                    continue
                w = length if (prefer and name.lower() in prefer) else length * (
                    penalty if prefer else 1.0)
                nd = d + w
                if nd < dist.get(v, float('inf')):
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))
        if dst not in dist:
            return None
        out = [dst]
        cur = dst
        while cur != src:
            cur = prev[cur]
            out.append(cur)
        out.reverse()
        return out

    def route_through(self, anchors, prefer_names=frozenset(),
                      penalty=OFF_CORRIDOR_PENALTY):
        """Route through a sequence of coordinates, leg by leg.

        Legs that cannot be routed fall back to the straight line between the
        anchors, so a shape is always produced; the caller is told how many
        legs fell back so it can be recorded rather than hidden.
        """
        pts, fallbacks = [], 0
        for a, b in zip(anchors, anchors[1:]):
            na, _ = self.nearest_node(a)
            nb, _ = self.nearest_node(b)
            leg = None
            if na and nb and na != nb:
                leg = self.shortest_path(na, nb, prefer_names, penalty)
            if not leg:
                leg = [a, b]
                fallbacks += 1
            pts += leg if not pts else leg[1:]
        return dedupe(pts), fallbacks


def _osm_named_ways(path, name, bbox=None):
    """Coordinate chains of every way carrying an exact name tag."""
    idx, out = {}, []
    for rec in parse(path):
        if rec[0] == 'node':
            idx[rec[1]] = (rec[2], rec[3])
        elif rec[0] == 'way' and (rec[3].get('name') or '') == name:
            pts = [idx[n] for n in rec[2] if n in idx]
            if len(pts) >= 2:
                if bbox and not any(bbox[0] <= p[0] <= bbox[1] and
                                    bbox[2] <= p[1] <= bbox[3] for p in pts):
                    continue
                out.append((rec[1], pts))
    out.sort(key=lambda w: w[0])
    return out


def harbourside_corridor(west_anchor, east_anchor):
    """The retained former-railway corridor, observed where it survives.

    The heavy rail between Wickham and Newcastle closed in 2014 and the track
    was lifted, so OSM carries no continuous disused way for it - only two
    two-node abandoned stubs near Wickham. What does survive, and is observed,
    is the harbour-side strip the corridor occupied: the Foreshore Footpath,
    mapped from lon 151.7767 to 151.7889 at lat about -32.9256, north of the
    Hunter Street alignment the as-built tram uses.

    So the eastern half of this alignment is observed OSM geometry and the
    western half - across the redeveloped land between Newcastle Interchange
    and the surviving path - is interpolated. Both halves are reported.
    """
    ways = _osm_named_ways(FOOTWAYS_OSM, 'Foreshore Footpath',
                           bbox=_HARBOURSIDE_BBOX)
    obs = []
    for _, pts in ways:
        obs += pts
    # keep only the stretch that lies between the two anchors, so the observed
    # path cannot double the alignment back on itself at either end
    lo, hi = sorted((west_anchor[1], east_anchor[1]))
    obs = [p for p in obs if lo < p[1] < hi]
    obs = dedupe(sorted(obs, key=lambda p: p[1]))
    if not obs:
        return densify([west_anchor, east_anchor], 20.0), 0.0, 0.0
    chain = dedupe([west_anchor] + obs + [east_anchor])
    observed_m = polyline_length_m(obs)
    total_m = polyline_length_m(chain)
    return densify(chain, 20.0), observed_m, total_m


POI_CSV = _city.path('data/processed/landuse/D1_poi.csv')


def road_intersection(name_a, name_b):
    """The observed point where two named streets share a vertex.

    A1 stores one edge per OSM way and the geometry carries the original node
    coordinates, so two streets that meet at a junction share that exact
    coordinate. Where several are shared (a dual carriageway, a slip), the
    lexicographically first is taken so the result is stable.
    """
    geom = {}
    with open(ROAD_GEOM, encoding='utf-8') as f:
        for ln in f:
            d = json.loads(ln)
            geom[d['edge_id']] = [(c[1], c[0]) for c in d['coords']]
    pts = {name_a: set(), name_b: set()}
    with open(ROAD_EDGES, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            nm = (r['name'] or '').strip()
            if nm in pts:
                pts[nm].update(geom.get(r['edge_id'], ()))
    shared = sorted(pts[name_a] & pts[name_b])
    return shared[0] if shared else None


def rail_station(name):
    """Coordinates of an observed railway=station node by exact name."""
    hits = []
    for rec in parse(RAILWAYS_OSM):
        if rec[0] != 'node' or len(rec) < 5 or not isinstance(rec[4], dict):
            continue
        t = rec[4]
        if t.get('railway') == 'station' and (t.get('name') or '') == name:
            hits.append((rec[1], (rec[2], rec[3])))
    hits.sort()
    return hits[0][1] if hits else None


def poi_point(name, category):
    """Coordinates of an observed D1 POI by exact name and category."""
    hits = []
    with open(POI_CSV, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r.get('name') == name and r.get('category') == category:
                hits.append((r['poi_id'], (float(r['lat']), float(r['lon']))))
    hits.sort()
    return hits[0][1] if hits else None


def resolve_anchor(spec):
    """Resolve an ('intersection'|'rail_station'|'poi', ...) anchor spec."""
    kind = spec[0]
    if kind == 'intersection':
        return road_intersection(spec[1], spec[2]), \
            'observed OSM intersection of %s and %s' % (spec[1], spec[2])
    if kind == 'rail_station':
        return rail_station(spec[1]), 'observed OSM railway station %s' % spec[1]
    if kind == 'poi':
        return poi_point(spec[1], spec[2]), 'observed OSM POI %s (%s)' % (spec[1], spec[2])
    raise ValueError('unknown anchor kind %r' % kind)


def project_onto(polyline, latlon):
    """Nearest point on a polyline to a coordinate, and its distance along it."""
    best, bestd, along, run = polyline[0], float('inf'), 0.0, 0.0
    for a, b in zip(polyline, polyline[1:]):
        seg = haversine(a, b)
        if seg <= 0:
            continue
        # planar projection is fine at this latitude over a 25 m step
        ax, ay = a[1], a[0]
        bx, by = b[1], b[0]
        px, py = latlon[1], latlon[0]
        vx, vy = bx - ax, by - ay
        t = ((px - ax) * vx + (py - ay) * vy) / max(vx * vx + vy * vy, 1e-18)
        t = max(0.0, min(1.0, t))
        q = (ay + (by - ay) * t, ax + (bx - ax) * t)
        d = haversine(latlon, q)
        if d < bestd:
            best, bestd, along = q, d, run + seg * t
        run += seg
    return best, bestd, along


def shape_rows(shape_id, pts):
    """GTFS shapes.txt rows for a polyline, with cumulative distance."""
    rows, run = [], 0.0
    for i, p in enumerate(pts):
        if i:
            run += haversine(pts[i - 1], p)
        rows.append(dict(shape_id=shape_id,
                         shape_pt_lat='%.7f' % p[0],
                         shape_pt_lon='%.7f' % p[1],
                         shape_pt_sequence=str(i + 1),
                         shape_dist_traveled='%.1f' % run))
    return rows
