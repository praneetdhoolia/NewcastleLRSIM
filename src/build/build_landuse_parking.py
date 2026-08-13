#!/usr/bin/env python
"""Build layer D1 (land use / frontages / POI) and complete layer A5 (parking).

D1 frontage segments are the unit of test for Claim B: modelled pedestrian
throughput per 50 m of frontage, and net arrivals across all modes. Four streets
are segmented so that B4 (generation vs displacement) can be tested:
    Hunter Street  - the light rail corridor
    Scott Street   - the eastern corridor leg
    Darby Street   - the off-corridor retail comparator
    Honeysuckle    - the waterfront comparator

Retail floorspace is not published at frontage level anywhere in Newcastle. It
is therefore modelled from OSM building footprints x levels x an activity
fraction inferred from the POI mix, and flagged source='modelled'. The field
audit in the proposal's fallback plan replaces it.
"""
import os
import csv
import json
import sys
import math
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from osm_parse import parse, centroid, fnum, haversine
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree
import pyproj

# Model inputs come from config/registry/<city>/, not from literals here. Every
# value below carries its units, provenance and either a sweep, a held-fixed rule
# or a derived-from identity there. See DECISIONS.md 15.
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import registry as _registry  # noqa: E402
CFG = _registry.load()

OUT = 'data/processed/landuse'
NET = 'data/processed/network'
os.makedirs(OUT, exist_ok=True)

CRS_M = 'EPSG:28356'
TO_M = pyproj.Transformer.from_crs('EPSG:4326', CRS_M, always_xy=True).transform
TO_LL = pyproj.Transformer.from_crs(CRS_M, 'EPSG:4326', always_xy=True).transform

CBD = dict(s=-32.9450, w=151.7250, n=-32.9050, e=151.8050)
SEG_M = CFG.get('D.frontage.segment_length_m')
FRONTAGE_BUFFER_M = CFG.get('D.frontage.buffer_m')

TARGET_STREETS = {
    'Hunter Street': 'corridor',
    'Scott Street': 'corridor',
    'Darby Street': 'off_corridor',
    'Honeysuckle Drive': 'waterfront',
    'Wharf Road': 'waterfront',
    'King Street': 'off_corridor',
    'Beaumont Street': 'off_corridor',
}

# POI categories that generate or attract pedestrian activity at frontage level
RETAIL_KEYS = ('shop',)
FOOD_AMENITY = {'restaurant', 'cafe', 'fast_food', 'bar', 'pub', 'food_court', 'ice_cream'}
CIVIC_AMENITY = {'library', 'townhall', 'community_centre', 'theatre', 'cinema',
                 'arts_centre', 'place_of_worship', 'university', 'college', 'school'}


def in_cbd(lat, lon):
    return CBD['s'] <= lat <= CBD['n'] and CBD['w'] <= lon <= CBD['e']


# ---------------------------------------------------------------- POI (D1)
def build_poi():
    idx = {}
    items = []
    for rec in parse('networks/osm/newcastle_poi.osm'):
        if rec[0] == 'node':
            idx[rec[1]] = (rec[2], rec[3])
            items.append(('n', rec[1], [(rec[2], rec[3])], rec[4]))
        elif rec[0] == 'way':
            items.append(('w', rec[1], rec[2], rec[3]))
    rows = []
    for kind, i, geo, t in items:
        cat = None
        if any(k in t for k in RETAIL_KEYS):
            cat = 'retail:' + t.get('shop', 'yes')
        elif t.get('amenity') in FOOD_AMENITY:
            cat = 'food:' + t['amenity']
        elif t.get('amenity') in CIVIC_AMENITY:
            cat = 'civic:' + t['amenity']
        elif t.get('office'):
            cat = 'office:' + t.get('office', 'yes')
        elif t.get('tourism'):
            cat = 'tourism:' + t['tourism']
        elif t.get('leisure'):
            cat = 'leisure:' + t['leisure']
        elif t.get('healthcare') or t.get('amenity') in ('clinic', 'hospital', 'pharmacy', 'doctors'):
            cat = 'health:' + (t.get('healthcare') or t.get('amenity'))
        elif t.get('amenity'):
            cat = 'amenity:' + t['amenity']
        elif t.get('landuse'):
            cat = 'landuse:' + t['landuse']
        if not cat:
            continue
        pts = geo if kind == 'n' else [idx[r] for r in geo if r in idx]
        if not pts:
            continue
        lat, lon = centroid(pts)
        # attraction weight: relative pedestrian pull, used by the accessibility
        # and frontage-throughput measures. Assumed, swept in sensitivity.
        head = cat.split(':')[0]
        w = {'retail': 1.0, 'food': 1.2, 'civic': 1.5, 'office': 0.8,
             'tourism': 1.1, 'leisure': 0.9, 'health': 1.0,
             'amenity': 0.4, 'landuse': 0.1}.get(head, 0.3)
        rows.append(dict(poi_id='%s%s' % (kind, i), lat=round(lat, 7), lon=round(lon, 7),
                         category=cat, category_group=head, attraction_weight=w,
                         name=t.get('name', ''), brand=t.get('brand', ''),
                         opening_hours=t.get('opening_hours', ''),
                         levels=t.get('building:levels', ''),
                         in_cbd=int(in_cbd(lat, lon)), year=2026,
                         weight_source='assumed'))
    _w('D1_poi.csv', rows)
    return rows


# ------------------------------------------------------- buildings (D1)
def build_buildings():
    idx = {}
    ways = []
    for rec in parse('networks/osm/newcastle_buildings_cbd.osm'):
        if rec[0] == 'node':
            idx[rec[1]] = (rec[2], rec[3])
        elif rec[0] == 'way' and 'building' in rec[3]:
            ways.append((rec[1], rec[2], rec[3]))
    rows = []
    for wid, refs, t in ways:
        pts = [idx[r] for r in refs if r in idx]
        if len(pts) < 4:
            continue
        try:
            poly = Polygon([TO_M(p[1], p[0]) for p in pts])
            if not poly.is_valid or poly.area <= 0:
                continue
        except Exception:
            continue
        lv = fnum(t.get('building:levels'))
        lv_src = 'osm'
        if lv is None:
            bt = t.get('building', 'yes')
            lv = {'retail': 1, 'commercial': 3, 'office': 4, 'apartments': 4,
                  'house': 1, 'residential': 2, 'industrial': 1, 'warehouse': 1}.get(bt, 2)
            lv_src = 'assumed'
        c = poly.centroid
        lon, lat = TO_LL(c.x, c.y)
        rows.append(dict(building_id='b' + wid, lat=round(lat, 7), lon=round(lon, 7),
                         footprint_m2=round(poly.area, 1), levels=lv, levels_source=lv_src,
                         gross_floor_area_m2=round(poly.area * lv, 1),
                         building_type=t.get('building', 'yes'),
                         shop=t.get('shop', ''), amenity=t.get('amenity', ''),
                         name=t.get('name', ''), year=2026))
    _w('D1_buildings_cbd.csv', rows)
    return rows, {r['building_id']: Polygon([TO_M(p[1], p[0])
                                             for p in [idx[x] for x in w[1] if x in idx]])
                  for r, w in zip(rows, ways) if len(w[1]) >= 4}


# ------------------------------------------------------- frontages (D1)
def build_frontages(poi_rows, bld_rows):
    """Cut target streets into 50 m frontage segments and attach land use."""
    geom = {}
    with open(os.path.join(NET, 'A1_road_geometry.jsonl'), encoding='utf-8') as fh:
        for line in fh:
            d = json.loads(line)
            geom[d['edge_id']] = d['coords']
    edges = list(csv.DictReader(open(os.path.join(NET, 'A1_road_edges.csv'), encoding='utf-8')))

    # POI / building spatial indexes in metres
    poi_pts, poi_meta = [], []
    for p in poi_rows:
        if not p['in_cbd']:
            continue
        x, y = TO_M(p['lon'], p['lat'])
        poi_pts.append(Point(x, y))
        poi_meta.append(p)
    poi_tree = STRtree(poi_pts) if poi_pts else None

    bld_pts, bld_meta = [], []
    for b in bld_rows:
        x, y = TO_M(b['lon'], b['lat'])
        bld_pts.append(Point(x, y))
        bld_meta.append(b)
    bld_tree = STRtree(bld_pts) if bld_pts else None

    rows = []
    for street, role in TARGET_STREETS.items():
        parts = []
        for e in edges:
            if e['name'] != street:
                continue
            co = geom.get(e['edge_id'])
            if not co or len(co) < 2:
                continue
            if not in_cbd(float(e['start_lat']), float(e['start_lon'])):
                continue
            parts.append((e, LineString([TO_M(c[0], c[1]) for c in co])))
        if not parts:
            print('   no CBD geometry for %s' % street)
            continue
        # order west->east then cut on cumulative distance
        parts.sort(key=lambda p: p[1].centroid.x)
        cum = 0.0
        k = 0
        for e, ln in parts:
            L = ln.length
            n = max(1, int(round(L / SEG_M)))
            for j in range(n):
                a, b = j / n, (j + 1) / n
                sub = LineString([ln.interpolate(a * L), ln.interpolate((a + b) / 2 * L),
                                  ln.interpolate(b * L)])
                k += 1
                seg_len = L / n
                buf = sub.buffer(FRONTAGE_BUFFER_M)
                npoi = collections.Counter()
                aw = 0.0
                cats = []
                if poi_tree is not None:
                    for i in poi_tree.query(buf):
                        if buf.contains(poi_pts[i]):
                            m = poi_meta[i]
                            npoi[m['category_group']] += 1
                            aw += float(m['attraction_weight'])
                            cats.append(m['category'])
                gfa = 0.0
                nb = 0
                if bld_tree is not None:
                    for i in bld_tree.query(buf):
                        if buf.contains(bld_pts[i]):
                            gfa += float(bld_meta[i]['gross_floor_area_m2'])
                            nb += 1
                biz = sum(npoi.values())
                # retail floorspace: ground-floor share of GFA scaled by the
                # retail/food share of the POI mix. Modelled, not observed.
                act = (npoi['retail'] + npoi['food'])
                retail_frac = (act / biz) if biz else 0.0
                retail_fsa = gfa * 0.35 * retail_frac
                mid = sub.interpolate(0.5, normalized=True)
                lon, lat = TO_LL(mid.x, mid.y)
                rows.append(dict(
                    frontage_segment_id='%s_%03d' % (street.replace(' ', '')[:8].upper(), k),
                    street_name=street, corridor_role=role, seg_index=k,
                    length_m=round(seg_len, 1),
                    lat=round(lat, 7), lon=round(lon, 7),
                    x_mga56=round(mid.x, 1), y_mga56=round(mid.y, 1),
                    road_edge_id=e['edge_id'],
                    business_count=biz,
                    n_retail=npoi['retail'], n_food=npoi['food'], n_office=npoi['office'],
                    n_civic=npoi['civic'], n_leisure=npoi['leisure'], n_health=npoi['health'],
                    business_categories=';'.join(sorted(set(cats))[:12]),
                    attraction_weight_sum=round(aw, 2),
                    n_buildings=nb, gross_floor_area_m2=round(gfa, 1),
                    retail_floorspace_m2=round(retail_fsa, 1),
                    retail_floorspace_source='modelled',
                    active_frontage_pct=round(min(100.0, biz / (seg_len / 25.0) * 100), 1) if seg_len else 0,
                    vacancy_rate='', vacancy_source='not_available',
                    awning_coverage_pct='', awning_source='not_available',
                    year=2026, scenario_variant_ref='base2026'))
    _w('D1_frontage_segments.csv', rows)
    return rows


# -------------------------------------------------------------- A5 parking
# City of Newcastle does not publish meter transactions or occupancy. Price and
# occupancy are therefore constructed by parking zone and flagged as assumed.
PARK_ZONES = [
    ('cbd_core',      dict(s=-32.9320, w=151.7680, n=-32.9200, e=151.7880),
     3.20, 120, [0.20, 0.15, 0.12, 0.10, 0.12, 0.22, 0.45, 0.70, 0.85, 0.90, 0.92,
                 0.93, 0.94, 0.93, 0.90, 0.85, 0.75, 0.60, 0.48, 0.42, 0.38, 0.33, 0.28, 0.23]),
    ('cbd_fringe',    dict(s=-32.9380, w=151.7550, n=-32.9180, e=151.7950),
     2.40, 180, [0.15, 0.12, 0.10, 0.09, 0.10, 0.18, 0.38, 0.62, 0.78, 0.84, 0.86,
                 0.87, 0.88, 0.87, 0.84, 0.79, 0.68, 0.52, 0.40, 0.34, 0.30, 0.26, 0.22, 0.18]),
    ('honeysuckle',   dict(s=-32.9300, w=151.7550, n=-32.9200, e=151.7750),
     2.40, 240, [0.12, 0.10, 0.08, 0.07, 0.08, 0.14, 0.30, 0.52, 0.70, 0.78, 0.82,
                 0.85, 0.86, 0.84, 0.80, 0.76, 0.70, 0.62, 0.58, 0.55, 0.50, 0.42, 0.32, 0.20]),
    ('beach_east',    dict(s=-32.9350, w=151.7800, n=-32.9150, e=151.8000),
     2.00, 240, [0.10, 0.08, 0.07, 0.06, 0.08, 0.16, 0.30, 0.45, 0.58, 0.68, 0.76,
                 0.82, 0.85, 0.84, 0.80, 0.74, 0.66, 0.56, 0.48, 0.42, 0.36, 0.28, 0.20, 0.14]),
]
FREE_OCC = CFG.get('A.parking.free_occupancy_profile')

CAP_DEFAULT = CFG.get('A.parking.capacity_default')


def build_parking():
    src = os.path.join(NET, 'A5_parking_osm.csv')
    rows = list(csv.DictReader(open(src, encoding='utf-8')))
    out = []
    n_imputed_cap = 0
    for r in rows:
        lat, lon = float(r['lat']), float(r['lon'])
        zone = None
        for name, bb, price, stay, occ in PARK_ZONES:
            if bb['s'] <= lat <= bb['n'] and bb['w'] <= lon <= bb['e']:
                zone, p_rate, p_stay, p_occ = name, price, stay, occ
                break
        if zone is None:
            zone, p_rate, p_stay, p_occ = 'outer_free', 0.0, 0, FREE_OCC
        cap = r['capacity_spaces']
        if cap == '':
            cap = CAP_DEFAULT.get(r['type'], 30)
            n_imputed_cap += 1
            cap_src = 'imputed_by_type'
        else:
            cap = int(cap)
            cap_src = 'osm'
        priced = 1 if (p_rate > 0 and r['type'] != 'offstreet_private') else 0
        rec = dict(r)
        rec.update(parking_zone=zone, capacity_spaces=cap, capacity_source=cap_src,
                   is_priced=priced,
                   price_aud_hr=p_rate if priced else 0.0,
                   price_source='assumed' if priced else 'assumed_free',
                   price_sweep_low=round(p_rate * 0.5, 2), price_sweep_high=round(p_rate * 1.5, 2),
                   max_stay_min_modelled=p_stay if priced else 0,
                   price_schedule='Mon-Fri 08:00-18:00 @ %.2f AUD/hr; Sat 08:00-13:00 @ %.2f; else free'
                                  % (p_rate, p_rate) if priced else 'free',
                   occupancy_by_hour=';'.join('%.2f' % x for x in p_occ),
                   occupancy_source='assumed',
                   walk_time_to_frontages_s='',
                   year=2026)
        out.append(rec)
    _w('A5_parking_facilities.csv', out)
    tot = collections.Counter()
    capsum = collections.Counter()
    for r in out:
        tot[r['parking_zone']] += 1
        capsum[r['parking_zone']] += int(r['capacity_spaces'])
    return len(out), n_imputed_cap, dict(tot), dict(capsum)


def _w(name, rows):
    if not rows:
        print('   (empty) %s' % name)
        return
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with open(os.path.join(OUT, name), 'w', newline='', encoding='utf-8') as fh:
        wr = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
        wr.writeheader()
        wr.writerows(rows)
    print('   wrote %-34s %d rows' % (name, len(rows)))


if __name__ == '__main__':
    print('POI ...', flush=True)
    poi = build_poi()
    print('buildings ...', flush=True)
    bld, _ = build_buildings()
    print('frontages ...', flush=True)
    fr = build_frontages(poi, bld)
    print('parking ...', flush=True)
    pk = build_parking()
    rep = {
        'poi_total': len(poi),
        'poi_in_cbd': sum(p['in_cbd'] for p in poi),
        'poi_by_group': dict(collections.Counter(p['category_group'] for p in poi)),
        'buildings_cbd': len(bld),
        'cbd_gross_floor_area_m2': round(sum(b['gross_floor_area_m2'] for b in bld), 0),
        'frontage_segments': len(fr),
        'frontage_by_street': dict(collections.Counter(f['street_name'] for f in fr)),
        'frontage_retail_m2_by_street': {
            k: round(sum(f['retail_floorspace_m2'] for f in fr if f['street_name'] == k), 0)
            # sorted(): iterating a set makes the output order hash-seed
            # dependent, so two builds of identical data produce different
            # bytes. Same defect as the P3 stage 0 stop_times.txt bug
            # (DECISIONS.md §9.2). CLAUDE.md forbids it outright.
            for k in sorted(set(f['street_name'] for f in fr))},
        'parking_facilities': pk[0], 'parking_capacity_imputed': pk[1],
        'parking_by_zone': pk[2], 'parking_spaces_by_zone': pk[3]}
    json.dump(rep, open(os.path.join(OUT, '_landuse_report.json'), 'w'), indent=2)
    print(json.dumps(rep, indent=2))
