#!/usr/bin/env python
"""Clip ABS ASGS boundaries to the Greater Newcastle study area.

Zone tiers (resolves proposal open decisions 2 and 3):
  core     - the five LGAs Newcastle, Lake Macquarie, Maitland, Cessnock and
             Port Stephens. Modelled at SA1.
  external - the remainder of SA4 'Hunter Valley exc Newcastle' (Singleton,
             Muswellbrook, Upper Hunter, Dungog). Retained only as a boundary
             treatment for Hunter Line through-demand, modelled at SA2.

Outputs zone geometries (GeoPackage), attributes (CSV) and centroids in
EPSG:28356 (GDA2020 / MGA Zone 56), the project CRS from Appendix A1.
"""
import os
import json
import geopandas as gpd
import pandas as pd

RAW = 'data/raw/boundaries'
OUT = 'data/processed/zones'
os.makedirs(OUT, exist_ok=True)

SA4S = ['Newcastle and Lake Macquarie', 'Hunter Valley exc Newcastle']
CORE_LGAS = ['Newcastle', 'Lake Macquarie', 'Maitland', 'Cessnock', 'Port Stephens']
CRS_M = 'EPSG:28356'

SPECS = [
    ('SA1', 'SA1_2021_AUST_SHP_GDA2020.zip', 'SA1_2021_AUST_GDA2020.shp', 'SA1_CODE21'),
    ('SA2', 'SA2_2021_AUST_SHP_GDA2020.zip', 'SA2_2021_AUST_GDA2020.shp', 'SA2_CODE21'),
    ('SA3', 'SA3_2021_AUST_SHP_GDA2020.zip', 'SA3_2021_AUST_GDA2020.shp', 'SA3_CODE21'),
    ('DZN', 'DZN_2021_AUST_GDA2020_SHP.zip', 'DZN_2021_AUST_GDA2020.shp', 'DZN_CODE21'),
]


def enrich(sel, key, core_union):
    """Add tier, area, centroid columns."""
    selm = sel.to_crs(CRS_M)
    sel = sel.copy()
    sel['area_km2'] = (selm.geometry.area / 1e6).round(4)
    rp = selm.geometry.representative_point()
    rp_ll = gpd.GeoSeries(rp, crs=CRS_M).to_crs('EPSG:4326')
    sel['x_mga56'] = rp.x.round(1)
    sel['y_mga56'] = rp.y.round(1)
    sel['lon'] = rp_ll.x.round(7)
    sel['lat'] = rp_ll.y.round(7)
    sel['zone_tier'] = ['core' if core_union.contains(p) else 'external' for p in rp]
    sel['zone_id'] = sel[key].astype(str)
    return sel


print('reading LGA boundaries ...', flush=True)
lga = gpd.read_file('zip://%s/LGA_2021_AUST_GDA2020_SHP.zip!LGA_2021_AUST_GDA2020.shp' % RAW)
core = lga[lga['LGA_NAME21'].isin(CORE_LGAS)].copy()
core_m = core.to_crs(CRS_M)
core_union = core_m.geometry.union_all()
core_ll = enrich(core, 'LGA_CODE21', core_union)
core_ll.to_file(os.path.join(OUT, 'zones_LGA.gpkg'), driver='GPKG')
core_ll.drop(columns='geometry').to_csv(os.path.join(OUT, 'zones_LGA.csv'), index=False)
print('  core LGAs: %d, %.0f km2' % (len(core), core['LGA_CODE21'].size and core_m.geometry.area.sum() / 1e6))

report = {'LGA': {'n': len(core), 'area_km2': round(float(core_m.geometry.area.sum() / 1e6), 1),
                  'names': sorted(core['LGA_NAME21'].tolist())}}
sa1_core = None

for level, zf, shp, key in SPECS:
    print('reading %s ...' % level, flush=True)
    g = gpd.read_file('zip://%s/%s!%s' % (RAW, zf, shp))
    if 'SA4_NAME21' in g.columns:
        sel = g[g['SA4_NAME21'].isin(SA4S)].copy()
    else:
        # DZN carries no SA4 field: intersect with the SA4 selection footprint
        base = sa1_core.to_crs(CRS_M)
        sel = gpd.sjoin(g.to_crs(CRS_M), base[['geometry']], how='inner', predicate='intersects')
        sel = sel.drop(columns=[c for c in sel.columns if c.startswith('index_')])
        sel = sel.drop_duplicates(subset=[key]).to_crs(g.crs)
    sel = sel[~sel.geometry.isna()].copy()
    sel = enrich(sel, key, core_union)
    if level == 'SA1':
        sa1_core = sel
    sel.to_file(os.path.join(OUT, 'zones_%s.gpkg' % level), driver='GPKG')
    sel.drop(columns='geometry').to_csv(os.path.join(OUT, 'zones_%s.csv' % level), index=False)
    t = sel['zone_tier'].value_counts().to_dict()
    a = sel.groupby('zone_tier')['area_km2'].sum().round(1).to_dict()
    report[level] = {'n': len(sel), 'key': key, 'by_tier': t, 'area_km2_by_tier': a}
    print('  %s: %d zones  tiers=%s  area=%s' % (level, len(sel), t, a), flush=True)

# zone lookup used by every downstream layer
sa1 = pd.read_csv(os.path.join(OUT, 'zones_SA1.csv'))
keep = ['SA1_CODE21', 'SA2_CODE21', 'SA2_NAME21', 'SA3_CODE21', 'SA3_NAME21',
        'SA4_CODE21', 'SA4_NAME21', 'zone_tier', 'area_km2', 'x_mga56', 'y_mga56', 'lon', 'lat']
sa1[[c for c in keep if c in sa1.columns]].to_csv(os.path.join(OUT, 'zone_lookup_SA1.csv'), index=False)

json.dump(report, open(os.path.join(OUT, '_zones_report.json'), 'w'), indent=2)
print(json.dumps(report, indent=2))
