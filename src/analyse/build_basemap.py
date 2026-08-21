#!/usr/bin/env python
"""Compact basemap for the run replay, built from the package's own layers.

No third-party map renderer is used, and that is a constraint rather than a
preference. A published page is served under a policy that blocks every external
host, so tiles, styles and library CDNs are all unreachable; and the project's
network allowlist carries the data sources only, not a package registry. Anything
drawn must therefore be inlined, which rules out a tile-based renderer
(MapLibre, Leaflet, Mapbox) because no offline tile set exists here, and makes a
WebGL toolkit (deck.gl) a large dependency for a job the data itself decides.
So the realism comes from the layers, not the library:

  roads   A1_road_geometry.jsonl - the true OSM polyline of every edge - joined
          to A1_road_edges.csv for road class and lane count, so a motorway is
          drawn wider than a residential street because it *is* wider.
  rail    railway=rail from the immutable Overpass extract.
  tram    railway=tram - the light rail alignment the study is about.
  coast   the five-LGA boundary, whose eastern edge is the coastline, used as
          the landmass so the ocean is ocean.
  water   natural=water, riverbank and reservoir polygons - the harbour, the
          Hunter River and Lake Macquarie. Fetched for this map and for nothing
          else: no model input reads them.
  green   parks, reserves, forest and cemeteries; `sand` is beach and dune.

Output is one JSON file whose geometry is base64 uint16, quantised over the
network bounding box (about 2 m over a 130 km extent). Classes are simplified at
different tolerances: a motorway keeps its curve, a cul-de-sac does not need to.

    python src/analyse/build_basemap.py --out cities/<city>/data/processed/basemap.json
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
import base64
import struct
import argparse
import xml.etree.ElementTree as ET

ROADS_GEOM = _city.path('data/processed/network/A1_road_geometry.jsonl')
ROADS_ATTR = _city.path('data/processed/network/A1_road_edges.csv')
RAILWAYS = _city.path('networks/osm/railways.osm')
WATER = _city.path('networks/osm/water.osm')
GREEN = _city.path('networks/osm/green.osm')
LGA = _city.path('data/processed/zones/zones_LGA.gpkg')
SUMO_NET = _city.path('networks/sumo/net_base2026/corridor.net.xml')

# area layers: the tag values that make a filled polygon, per source file
AREA_SELECT = {
    'water': (WATER, {'natural': ('water',), 'waterway': ('riverbank',),
                      'landuse': ('reservoir', 'basin')}),
    'green': (GREEN, {'leisure': ('park', 'golf_course', 'nature_reserve',
                                  'garden'),
                      'natural': ('wood', 'scrub', 'heath', 'wetland'),
                      'landuse': ('forest', 'grass', 'meadow',
                                  'recreation_ground', 'cemetery',
                                  'village_green')}),
    'sand': (GREEN, {'natural': ('beach', 'sand')}),
}

# draw order matters: the big roads must land on top of the small ones
CLASS_GROUP = {
    'motorway': 'motorway', 'motorway_link': 'motorway',
    'trunk': 'trunk', 'trunk_link': 'trunk',
    'primary': 'primary', 'primary_link': 'primary',
    'secondary': 'secondary', 'secondary_link': 'secondary',
    'tertiary': 'tertiary', 'tertiary_link': 'tertiary',
    'residential': 'residential', 'unclassified': 'residential',
    'living_street': 'residential', 'busway': 'secondary',
}
def simplify_tolerance_m(group):
    """Metres of line simplification for a drawn layer.

    A DRAWING choice, not a model quantity: it decides how much of a polyline
    survives into the picture and nothing else reads it, which is why it lives
    in code rather than in the registry. A motorway curve is information; a
    residential wiggle is not. `service` roads are dropped entirely - 16,651
    parking aisles and driveways are noise at city scale, not realism.
    """
    return {'motorway': 2, 'trunk': 2, 'primary': 3, 'secondary': 4,
            'tertiary': 6, 'residential': 10, 'rail': 2, 'tram': 1,
            'coast': 6, 'water': 4, 'green': 8, 'sand': 4}.get(group, 0)


def pack(lines, origin):
    """[(lanes, [(x,y), ...]), ...] -> base64, in CENTIMETRES.

    Anchor plus deltas. Each polyline carries an int32 centimetre anchor and
    then int16 centimetre steps, because consecutive vertices of a road are
    metres apart, not kilometres. That is 4 bytes a vertex at 1 cm precision,
    against 4 bytes a vertex at 2 m precision for a uint16 grid over the whole
    130 km study area - the same size for 200x the resolution, which is what
    makes zooming to a 10 m view meaningful rather than a staircase.

    A step that will not fit in an int16 (more than 327 m) is DENSIFIED - split
    into equal collinear sub-steps - rather than allowed to start a new run.

    That is a repair, not a refinement. The previous behaviour began a new
    anchored run on overflow, but the run that would have carried the long step
    was then degenerate (n == 1) and skipped, so **the segment was silently
    dropped**. On a road that is a missing link. On a polygon it is fatal:
    `read_coast` simplifies the dissolved LGA boundary, and simplification is
    precisely what creates straight segments longer than 327 m, so every ring
    came apart. Measured on the shipped basemap: the coast layer packed to 180
    fragments of which only 33 closed, the largest spanning 12.5 km against a
    boundary that spans 131 km, and the landmass filled 1 of 40 sampled points -
    the whole map rendered as ocean. Densifying adds collinear vertices, changes
    no geometry, and needs no change to the wire format.
    """
    ox, oy = origin
    lim = 32000                                  # cm, inside the int16 bound
    out = bytearray()
    for lanes, pts in lines:
        cm = [(int(round((x - ox) * 100.0)), int(round((y - oy) * 100.0)))
              for x, y in pts]
        dense = cm[:1]
        for (x1, y1), (x2, y2) in zip(cm, cm[1:]):
            steps = max(abs(x2 - x1), abs(y2 - y1)) // lim + 1
            for k in range(1, steps + 1):
                dense.append((x1 + (x2 - x1) * k // steps,
                              y1 + (y2 - y1) * k // steps))
        cm = dense
        i = 0
        while i < len(cm) - 1:
            # how far can we run before a delta overflows int16
            j = i + 1
            while j < len(cm):
                dx = cm[j][0] - cm[j - 1][0]
                dy = cm[j][1] - cm[j - 1][1]
                if dx < -32768 or dx > 32767 or dy < -32768 or dy > 32767:
                    break
                j += 1
            n = j - i
            if n < 2:
                i = j
                continue
            out += struct.pack('<iiHBB', cm[i][0], cm[i][1], n,
                               min(255, max(1, int(lanes or 1))), 0)
            for k in range(i + 1, j):
                out += struct.pack('<hh', cm[k][0] - cm[k - 1][0],
                                   cm[k][1] - cm[k - 1][1])
            i = j - 1 if j < len(cm) else j
    return base64.b64encode(bytes(out)).decode('ascii')


def read_roads(simplify):
    from shapely.geometry import LineString
    import pyproj
    tf = pyproj.Transformer.from_crs('EPSG:4326', _city.crs(), always_xy=True)
    attr = {}
    with open(ROADS_ATTR, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            g = CLASS_GROUP.get(r['road_class'])
            if g:
                try:
                    lanes = int(float(r['num_lanes'] or 1))
                except ValueError:
                    lanes = 1
                attr[r['edge_id']] = (g, lanes)
    groups = {}
    with open(ROADS_GEOM, encoding='utf-8') as fh:
        for line in fh:
            d = json.loads(line)
            a = attr.get(d['edge_id'])
            if a is None:
                continue
            g, lanes = a
            lon = [c[0] for c in d['coords']]
            lat = [c[1] for c in d['coords']]
            xs, ys = tf.transform(lon, lat)
            pts = list(zip(xs, ys))
            if len(pts) < 2:
                continue
            if simplify:
                pts = list(LineString(pts).simplify(simplify_tolerance_m(g)).coords)
            groups.setdefault(g, []).append((lanes, pts))
    return groups


def read_railways(simplify):
    from shapely.geometry import LineString
    import pyproj
    tf = pyproj.Transformer.from_crs('EPSG:4326', _city.crs(), always_xy=True)
    nodes, ways, cur, tags, refs = {}, {'rail': [], 'tram': []}, None, {}, []
    for ev, el in ET.iterparse(RAILWAYS, events=('start', 'end')):
        if ev == 'end' and el.tag == 'node':
            nodes[el.get('id')] = (float(el.get('lon')), float(el.get('lat')))
            el.clear()
        elif ev == 'start' and el.tag == 'way':
            cur, tags, refs = el.get('id'), {}, []
        elif ev == 'end' and el.tag == 'nd':
            refs.append(el.get('ref'))
        elif ev == 'end' and el.tag == 'tag':
            tags[el.get('k')] = el.get('v')
        elif ev == 'end' and el.tag == 'way':
            rw = tags.get('railway')
            key = 'tram' if rw in ('tram', 'light_rail') else (
                'rail' if rw == 'rail' else None)
            if key and len(refs) > 1:
                pts = [nodes[n] for n in refs if n in nodes]
                if len(pts) > 1:
                    xs, ys = tf.transform([p[0] for p in pts],
                                          [p[1] for p in pts])
                    q = list(zip(xs, ys))
                    if simplify:
                        q = list(LineString(q).simplify(simplify_tolerance_m(key)).coords)
                    ways[key].append((2, q))
            el.clear()
    return ways


def read_sumo_lanes():
    """Individual lane centrelines from the SUMO corridor network.

    This is the only true lane-level geometry available: netconvert resolves
    each edge into per-lane polylines with a width, a speed and a mode
    permission set, which is what an HD map format (OpenDRIVE, Lanelet2) carries
    and what a rendered basemap needs to draw a carriageway rather than a wire.
    It exists because P2 already built the corridor four times; nothing is
    fetched for it.

    Coverage is the CORRIDOR ONLY - about 10 x 9 km around the Newcastle CBD,
    which is the part of the study area the light rail question is about. Beyond
    it the region layers carry a lane *count* but not lane geometry, so lanes
    there are drawn as a carriageway width rather than as separate lanes.

    Internal junction lanes (ids beginning ':') are skipped: they are the
    turning paths inside an intersection, and drawing them fills every junction
    with a solid blob.
    """
    import re
    txt = open(SUMO_NET, encoding='utf-8').read()
    m = re.search(r'netOffset="(-?[0-9.]+),(-?[0-9.]+)"', txt)
    ox, oy = (-float(m.group(1)), -float(m.group(2))) if m else (0.0, 0.0)
    out = []
    edge_re = re.compile(r'<edge id="([^"]+)"[^>]*?(?: type="([^"]*)")?[^>]*>')
    lane_re = re.compile(r'<lane id="([^"]+)"[^>]*?shape="([^"]+)"[^>]*/>')
    for lm in lane_re.finditer(txt):
        lid, shape = lm.group(1), lm.group(2)
        if lid.startswith(':'):
            continue
        seg = txt[max(0, lm.start() - 1200):lm.start()]
        w = re.search(r'width="([0-9.]+)"', lm.group(0))
        # SUMO's own default when a lane declares no width
        width = float(w.group(1)) if w else 3.2
        rail = 'allow="tram' in lm.group(0) or 'allow="rail' in lm.group(0)
        pts = []
        for pair in shape.split(' '):
            if ',' not in pair:
                continue
            a, b = pair.split(',')[:2]
            pts.append((float(a) + ox, float(b) + oy))
        if len(pts) > 1:
            # lanes byte carries the width in decimetres so the renderer can
            # draw the carriageway in metres; flag rail-only lanes as 255
            out.append((255 if rail else max(1, min(254, int(round(width * 10)))),
                        pts))
    return out


def read_areas(path, select, tol):
    """Closed ways carrying any of the selected tags, as polygons in the city CRS.

    Ways only. An OSM multipolygon relation would carry the islands in a lake as
    inner rings, and dropping them fills a lake solid - visible, and wrong, but
    a great deal less wrong than having no lake at all. Recorded rather than
    silently accepted.
    """
    from shapely.geometry import LineString
    import pyproj
    tf = pyproj.Transformer.from_crs('EPSG:4326', _city.crs(), always_xy=True)
    nodes, out, tags, refs = {}, [], {}, []
    for ev, el in ET.iterparse(path, events=('start', 'end')):
        if ev == 'end' and el.tag == 'node':
            nodes[el.get('id')] = (float(el.get('lon')), float(el.get('lat')))
            el.clear()
        elif ev == 'start' and el.tag == 'way':
            tags, refs = {}, []
        elif ev == 'end' and el.tag == 'nd':
            refs.append(el.get('ref'))
        elif ev == 'end' and el.tag == 'tag':
            tags[el.get('k')] = el.get('v')
        elif ev == 'end' and el.tag == 'way':
            hit = any(tags.get(k) in v for k, v in select.items())
            if hit and len(refs) > 3 and refs[0] == refs[-1]:
                pts = [nodes[n] for n in refs if n in nodes]
                if len(pts) > 3:
                    xs, ys = tf.transform([p[0] for p in pts],
                                          [p[1] for p in pts])
                    q = list(zip(xs, ys))
                    if tol:
                        q = list(LineString(q).simplify(tol).coords)
                    if len(q) > 3:
                        out.append((1, q))
            el.clear()
    return out


def read_coast(simplify):
    import geopandas as gpd
    from shapely.ops import unary_union
    g = gpd.read_file(LGA).to_crs(_city.crs())
    area = unary_union(g.geometry.values)
    if simplify:
        area = area.simplify(simplify_tolerance_m('coast'))
    out = []
    geoms = getattr(area, 'geoms', [area])
    for poly in geoms:
        out.append((1, list(poly.exterior.coords)))
    return out


def _rebind_osm_dir(d):
    """Point every .osm input at `d`, keeping the filenames."""
    global RAILWAYS, WATER, GREEN, AREA_SELECT
    RAILWAYS = os.path.join(d, os.path.basename(RAILWAYS))
    WATER = os.path.join(d, os.path.basename(WATER))
    GREEN = os.path.join(d, os.path.basename(GREEN))
    AREA_SELECT = {
        'water': (WATER, AREA_SELECT['water'][1]),
        'green': (GREEN, AREA_SELECT['green'][1]),
        'sand': (GREEN, AREA_SELECT['sand'][1]),
    }
    missing = [p for p in (RAILWAYS, WATER, GREEN) if not os.path.exists(p)]
    if missing:
        raise SystemExit('missing OSM layer(s) under %s: %s'
                         % (d, ', '.join(missing)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--no-simplify', action='store_true')
    # The harvest directory is a parameter rather than a constant because the
    # issue #32 re-harvest empties `networks/osm/`, and the visual layers -
    # water, green, sand, rail - have no model consumer, so a basemap can
    # legitimately be built from the retained pre-#32 extracts while the road
    # network comes from the current build. Whatever is used is recorded in
    # the payload's `source` block, so a picture always says where it came from.
    ap.add_argument('--osm-dir', default=os.path.dirname(RAILWAYS),
                    help='directory holding the Overpass .osm layers '
                         '(default: networks/osm)')
    a = ap.parse_args()
    if a.osm_dir:
        _rebind_osm_dir(a.osm_dir)
    simplify = not a.no_simplify

    print('reading roads ...', flush=True)
    groups = read_roads(simplify)
    print('reading railways ...', flush=True)
    groups.update(read_railways(simplify))
    print('reading the study-area outline ...', flush=True)
    groups['coast'] = read_coast(simplify)
    for name, (path, select) in AREA_SELECT.items():
        print('reading %s areas ...' % name, flush=True)
        groups[name] = read_areas(path, select,
                                  simplify_tolerance_m(name) if simplify else 0)
    if os.path.exists(SUMO_NET):
        print('reading SUMO lane geometry ...', flush=True)
        groups['lanes'] = read_sumo_lanes()

    xs, ys = [], []
    for lines in groups.values():
        for _, pts in lines:
            for x, y in pts:
                xs.append(x)
                ys.append(y)
    bbox = [min(xs), min(ys), max(xs), max(ys)]
    origin = (bbox[0], bbox[1])

    layers, stats = {}, {}
    for g, lines in groups.items():
        layers[g] = pack(lines, origin)
        stats[g] = {'lines': len(lines), 'points': sum(len(p) for _, p in lines)}
        print('   %-11s %6d lines %8d points' % (g, stats[g]['lines'],
                                                 stats[g]['points']), flush=True)

    payload = {'bbox': bbox, 'origin': list(origin), 'units': 'cm_from_origin',
               'layers': layers, 'stats': stats,
               'source': {'roads': ROADS_GEOM, 'rail': RAILWAYS, 'coast': LGA,
                          'lanes': SUMO_NET}}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8') as w:
        json.dump(payload, w, separators=(',', ':'))
    print('wrote %s  (%.1f MiB)' % (a.out, os.path.getsize(a.out) / 2**20))


if __name__ == '__main__':
    main()
