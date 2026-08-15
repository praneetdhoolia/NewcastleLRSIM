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

# This builder encodes THIS CITY's intervention, corridor or statistical
# geography, so it lives with the city rather than in the framework. It still
# uses the framework's generic machinery, which is two directories up.
import os as _os
import sys as _sys
_REPO = _os.path.dirname(_os.path.dirname(_os.path.dirname(
    _os.path.dirname(_os.path.abspath(__file__)))))
_sys.path.insert(0, _os.path.join(_REPO, 'src'))
_sys.path.insert(0, _os.path.join(_REPO, 'src', 'build'))
_sys.path.insert(0, _os.path.join(_REPO, 'src', 'analyse'))
import city as _city  # noqa: E402
import os
import csv
import json
import sys
import math
import collections

from osm_parse import parse, centroid, fnum
from shapely.geometry import LineString, Point, Polygon
from shapely.strtree import STRtree
import pyproj

# Model inputs come from cities/<city>/registry/, not from literals here. Every
# value below carries its units, provenance and either a sweep, a held-fixed rule
# or a derived-from identity there. See DECISIONS.md 15.
import sys as _sys
import registry as _registry  # noqa: E402
CFG = _registry.load()

OUT = _city.path('data/processed/landuse')
NET = _city.path('data/processed/network')
os.makedirs(OUT, exist_ok=True)

CRS_M = _city.crs()
TO_M = pyproj.Transformer.from_crs('EPSG:4326', CRS_M, always_xy=True).transform
TO_LL = pyproj.Transformer.from_crs(CRS_M, 'EPSG:4326', always_xy=True).transform

# Declared in cities/<city>/geometry/analysis_extents.json, not typed here.
# It sets a PRE-REGISTERED denominator (issue #34): the buildings whose
# floorspace D1_frontage_segments.csv attributes per 50 m, which is the unit
# of test for hypothesis B1. Measure what a change moves before changing it.
CBD = _city.extent('cbd_buildings')
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
    for rec in parse(_city.path('networks/osm/poi.osm')):
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
    for rec in parse(_city.path('networks/osm/buildings_cbd.osm')):
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
# City of Newcastle does not publish meter transactions, tariffs or occupancy,
# and the OSM `fee=yes` tag cannot stand in for them: 452 of its 472 facilities
# are University of Newcastle car parks at Callaghan, a median 7.8 km from the
# centre, while the CBD's own paid parking is untagged (DECISIONS.md §9.31).
#
# Price is therefore derived from the CITY'S OWN job-density distribution. This
# replaced four hand-drawn lat/lon rectangles carrying literal prices, max-stays
# and occupancy profiles - one of which, `honeysuckle`, was fully contained in
# the box tested before it and so could never match a facility. A typed
# rectangle cannot be wrong in a way anyone notices (issue #33, and #32 before
# it), so there is no extent here: `thr` and `sat` are percentiles of whatever
# distribution the city's own zones present, and `zone_tier` is a tag any city's
# zone build produces.
#
#     price(zone) = price_aud_hr_max x clamp((dens - thr) / (sat - thr), 0, 1)
#
PRICE_THRESHOLD_PCTILE = CFG.get('A.parking.price_threshold_pctile')
PRICE_SATURATION_PCTILE = CFG.get('A.parking.price_saturation_pctile')
PRICE_AUD_HR_MAX = CFG.get('A.parking.price_aud_hr_max')
PRICE_SWEEP = CFG.sweep('A.parking.price_aud_hr_max')
MAX_STAY_MIN = CFG.get('A.parking.max_stay_min')
CHARGED_HOURS = CFG.get('A.parking.charged_hours_by_day_type')
# One assumed profile for every facility. The four priced-zone profiles this
# replaced were hand-typed per hand-drawn box, reached no consumer and rested on
# no observation; one assumed profile that says so is worth more than four that
# imply a measurement nobody made.
OCC_PROFILE = CFG.get('A.parking.occupancy_profile')

CAP_DEFAULT = CFG.get('A.parking.capacity_default')

ZONES_SA1 = _city.path('data/processed/zones/zones_SA1.gpkg')
ATTRACTIONS = os.path.join(OUT, 'D1_zone_attractions_SA1.csv')


def _pctile(sorted_values, q):
    """Linear-interpolated percentile over an already-sorted list.

    Written out rather than imported so the price ramp has no dependency on a
    library's default interpolation method changing under it.
    """
    if not sorted_values:
        raise SystemExit('no zones to take a job-density percentile over')
    pos = (len(sorted_values) - 1) * (q / 100.0)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def zone_prices():
    """Price every zone from the city's own core-zone job-density spread.

    Returns (by_sa1, stats). `by_sa1` maps SA1 code -> price in AUD/h; every
    zone appears, most at 0.00.
    """
    rows = list(csv.DictReader(open(ATTRACTIONS, encoding='utf-8')))
    dens = {}
    for r in rows:
        area = float(r['area_km2'])
        dens[r['SA1_CODE21']] = (float(r['jobs']) / area) if area > 0 else 0.0
    core = sorted(dens[r['SA1_CODE21']] for r in rows if r['zone_tier'] == 'core')
    thr = _pctile(core, PRICE_THRESHOLD_PCTILE)
    sat = _pctile(core, PRICE_SATURATION_PCTILE)
    if sat <= thr:
        raise SystemExit(
            'A.parking.price_saturation_pctile (%g -> %.1f jobs/km2) must exceed '
            'price_threshold_pctile (%g -> %.1f): the price ramp would divide by a '
            'non-positive span' % (PRICE_SATURATION_PCTILE, sat,
                                   PRICE_THRESHOLD_PCTILE, thr))
    by_sa1, weights = {}, {}
    for code, d in dens.items():
        w = min(1.0, max(0.0, (d - thr) / (sat - thr)))
        weights[code] = w
        by_sa1[code] = round(PRICE_AUD_HR_MAX * w, 4)
    out = []
    for r in rows:
        code = r['SA1_CODE21']
        out.append(dict(
            SA1_CODE21=code, zone_tier=r['zone_tier'], jobs=r['jobs'],
            area_km2=r['area_km2'], jobs_per_km2=round(dens[code], 2),
            density_weight=round(weights[code], 6),
            price_aud_hr=by_sa1[code],
            price_sweep_low=round(PRICE_SWEEP[0] * weights[code], 4),
            price_sweep_high=round(PRICE_SWEEP[1] * weights[code], 4),
            price_source='modelled_from_job_density'))
    out.sort(key=lambda x: x['SA1_CODE21'])
    _w('A5_parking_price_zones.csv', out)
    stats = dict(threshold_pctile=PRICE_THRESHOLD_PCTILE,
                 saturation_pctile=PRICE_SATURATION_PCTILE,
                 threshold_jobs_km2=round(thr, 1), saturation_jobs_km2=round(sat, 1),
                 core_zones=len(core),
                 zones_priced=sum(1 for v in by_sa1.values() if v > 0),
                 core_zones_priced=sum(1 for r in rows if r['zone_tier'] == 'core'
                                       and by_sa1[r['SA1_CODE21']] > 0),
                 price_aud_hr_max=PRICE_AUD_HR_MAX)
    return by_sa1, stats


def _schedule_text(price):
    """The charged window, per day type, exactly as the model will apply it."""
    parts = []
    for day in ('WEEKDAY', 'SAT', 'SUN'):
        win = CHARGED_HOURS.get(day)
        if win:
            parts.append('%s %02d:00-%02d:00 @ %.2f AUD/hr'
                         % (day, int(win[0]), int(win[1]), price))
        else:
            parts.append('%s free' % day)
    return '; '.join(parts)


def facility_zones(rows):
    """SA1 of every parking facility, by point in polygon. '' if outside."""
    import geopandas as gpd
    z = gpd.read_file(ZONES_SA1).to_crs(CRS_M)[['SA1_CODE21', 'geometry']]
    xs, ys = zip(*(TO_M(float(r['lon']), float(r['lat'])) for r in rows))
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(xs, ys), crs=CRS_M)
    j = gpd.sjoin(pts, z, how='left', predicate='within')
    j = j[~j.index.duplicated(keep='first')].sort_index()
    return ['' if v != v or v is None else str(v) for v in j['SA1_CODE21']]


def build_parking():
    by_sa1, price_stats = zone_prices()
    src = os.path.join(NET, 'A5_parking_osm.csv')
    rows = list(csv.DictReader(open(src, encoding='utf-8')))
    sa1 = facility_zones(rows)
    occ = ';'.join('%.2f' % x for x in OCC_PROFILE)
    out = []
    n_imputed_cap = 0
    for r, code in zip(rows, sa1):
        p_rate = by_sa1.get(code, 0.0)
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
        rec.update(parking_zone=code or 'outside_zone_system',
                   capacity_spaces=cap, capacity_source=cap_src,
                   is_priced=priced,
                   price_aud_hr=p_rate if priced else 0.0,
                   price_source='modelled_from_job_density' if priced else 'modelled_free',
                   price_sweep_low=round(PRICE_SWEEP[0] * p_rate / PRICE_AUD_HR_MAX, 4)
                                   if priced else 0.0,
                   price_sweep_high=round(PRICE_SWEEP[1] * p_rate / PRICE_AUD_HR_MAX, 4)
                                    if priced else 0.0,
                   max_stay_min_modelled=MAX_STAY_MIN if priced else 0,
                   price_schedule=_schedule_text(p_rate) if priced else 'free',
                   occupancy_by_hour=occ,
                   occupancy_source='assumed',
                   walk_time_to_frontages_s='',
                   year=2026)
        out.append(rec)
    _w('A5_parking_facilities.csv', out)
    capsum = collections.Counter()
    banded = collections.Counter()
    for r in out:
        band = 'free' if not r['is_priced'] else (
            'priced_under_1' if r['price_aud_hr'] < 1.0 else
            'priced_1_to_2' if r['price_aud_hr'] < 2.0 else 'priced_2_plus')
        banded[band] += 1
        capsum[band] += int(r['capacity_spaces'])
    return len(out), n_imputed_cap, dict(banded), dict(capsum), price_stats


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
        'parking_by_price_band': pk[2], 'parking_spaces_by_price_band': pk[3],
        'parking_price': pk[4]}
    json.dump(rep, open(os.path.join(OUT, '_landuse_report.json'), 'w'), indent=2)
    print(json.dumps(rep, indent=2))
