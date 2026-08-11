#!/usr/bin/env python
"""SA1 -> LGA correspondence, by spatial join against the ABS LGA boundaries.

The mode-share targets are **Newcastle LGA** while the model covers five LGAs
(DECISIONS.md 12.1), so a fit needs to know which agents are Newcastle
residents. Nothing in the package carried that: `zones_SA1.csv` has SA2, SA3 and
SA4 names but no LGA, and SA3 `Newcastle` is not the same region as Newcastle
LGA.

Rather than approximate one with the other, this joins each SA1's centroid to
the ABS LGA polygons that `data/raw/boundaries/LGA_2021_AUST_GDA2020_SHP.zip`
already provides - a real boundary file already in the package with provenance,
not a lookup typed by hand.

A centroid join is exact for SA1s wholly inside one LGA, which is the normal
case because the ASGS nests SA1s inside LGAs by design. Any SA1 whose centroid
falls outside every LGA polygon is written with an empty LGA and counted, so a
gap shows up rather than silently reassigning agents.
"""
import os

import geopandas as gpd
import pandas as pd

ZONES = 'data/processed/zones/zones_SA1.csv'
LGA_ZIP = 'data/raw/boundaries/LGA_2021_AUST_GDA2020_SHP.zip'
OUT = 'data/processed/zones/sa1_to_lga.csv'
CRS_M = 'EPSG:28356'


def main():
    z = pd.read_csv(ZONES, dtype={'SA1_CODE21': str})
    pts = gpd.GeoDataFrame(
        z[['SA1_CODE21', 'zone_tier']].copy(),
        geometry=gpd.points_from_xy(z['x_mga56'], z['y_mga56']), crs=CRS_M)

    lga = gpd.read_file('zip://' + os.path.abspath(LGA_ZIP))
    name_col = next(c for c in lga.columns if c.upper().startswith('LGA_NAME'))
    code_col = next(c for c in lga.columns if c.upper().startswith('LGA_CODE'))
    lga = lga[[name_col, code_col, 'geometry']].to_crs(CRS_M)

    joined = gpd.sjoin(pts, lga, how='left', predicate='within')
    joined = joined.drop_duplicates(subset='SA1_CODE21', keep='first')
    out = joined[['SA1_CODE21', 'zone_tier', name_col, code_col]].rename(
        columns={name_col: 'lga_name', code_col: 'lga_code'})
    out['lga_name'] = out['lga_name'].fillna('')
    out.to_csv(OUT, index=False)

    missing = int((out['lga_name'] == '').sum())
    core = out[out['zone_tier'] == 'core']
    print('%d SA1s joined to %d LGAs; %d unmatched'
          % (len(out), out['lga_name'].nunique(), missing))
    print('core tier by LGA:')
    for k, v in core['lga_name'].value_counts().items():
        print('  %-24s %d' % (k or '(none)', v))


if __name__ == '__main__':
    main()
