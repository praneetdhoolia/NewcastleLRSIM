#!/usr/bin/env python
"""Clip the statewide NSW Speed Zones linework to the study area.

Issue #27 lists the corridor attributes hypothesis B3 rests on, and grades each
by evidence. Speed limit is the one an open dataset can settle: TfNSW publishes
the **regulated** speed zone for every road in NSW, which is a stronger source
than the OSM `maxspeed` tag - it is the legal instrument rather than a mapper's
transcription of a sign.

It also settles far more than the corridor. Across the whole road graph
`speed_limit_kmh` is imputed on 53.7% of edges from a per-class default; the
speed zones cover the network, not just the 714 corridor edges.

What this does NOT settle, and #27 is explicit about it: kerbside use (95%
imputed on the corridor), lane width (98.6%), capacity (100%) and turn lanes
(90% absent). The kerbside dataset TfNSW publishes is **Sydney CBD loading
zones**, verified against the catalogue, and no statewide lane-count or capacity
inventory exists. Those need street imagery, and they stay imputed and labelled.

The extent is derived, never typed: the study area is the dissolved LGA boundary
the zone build already produced, buffered by a declared margin. A hand-drawn
rectangle here would be the #32 defect again.
"""

# City-relative paths resolve through src/city.py: `data/...` names a
# location inside cities/<city>/, not inside the repository root.
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                  '..', '..', '..', 'src'))
import city as _city  # noqa: E402
import io
import os
import sys
import json
import hashlib
import argparse
import datetime

import geopandas as gpd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import registry as _registry  # noqa: E402
CFG = _registry.load()

RAW = _city.path('data/raw/speedzones')
SHP = os.path.join(RAW, 'Speed_Zones.shp')
ZIP = os.path.join(RAW, 'speedzones.zip')
LGA = _city.path('data/processed/zones/zones_LGA.gpkg')
OUT = _city.path('data/processed/network/A1_speed_zones.gpkg')
PROV = os.path.join(RAW, 'provenance_speed_zones.json')
CRS_M = 'EPSG:28356'

URL = ('https://opendata.transport.nsw.gov.au/data/dataset/'
       '4253a054-b377-4b5b-83d1-71385bb6ff33/resource/'
       '72cd0f29-f231-4c8c-a885-595946f3f202/download/speedzones.zip')

#: Only zones in force. `Proposed` and `Superseded` describe a road that is not
#: the one being modelled.
KEEP_STATUS = 'Existing'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def study_area():
    """Dissolved LGA boundary plus the declared margin, in metres."""
    lga = gpd.read_file(LGA).to_crs(CRS_M)
    margin = CFG.get('A.road.speed_zone_clip_margin_m')
    return lga.geometry.union_all().buffer(margin), margin


def main():
    if not os.path.exists(SHP):
        raise SystemExit(
            '%s is missing. Download it first:\n  curl -sL -o %s "%s"\n'
            'then unzip it in place. It is 62 MB and is not committed.'
            % (SHP, ZIP, URL))
    area, margin = study_area()
    print('reading the statewide layer (this is a 436 MB dbf) ...', flush=True)
    g = gpd.read_file(SHP)
    n_all = len(g)
    g = g.to_crs(CRS_M)
    g = g[g['Status'] == KEEP_STATUS]
    n_existing = len(g)
    g = g[g.geometry.intersects(area)].copy()
    g['speed_kmh'] = (g['Speed'].astype(str).str.extract(r'(\d+)')[0]
                      .astype(float))
    g = g[g.speed_kmh.notna() & (g.speed_kmh > 0)]
    g = g[['Type', 'Status', 'Direction', 'speed_kmh', 'geometry']]
    g = g.rename(columns={'Type': 'zone_type', 'Status': 'zone_status',
                          'Direction': 'direction'})
    g = g.sort_values(['speed_kmh', 'zone_type']).reset_index(drop=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if os.path.exists(OUT):
        os.remove(OUT)
    g.to_file(OUT, driver='GPKG', layer='speed_zones')
    print('   statewide %d -> existing %d -> in study area %d'
          % (n_all, n_existing, len(g)), flush=True)
    print('   speeds present: %s'
          % sorted(int(v) for v in g.speed_kmh.unique()), flush=True)

    prov = [dict(path='speedzones/speedzones.zip', url=URL,
                 description='TfNSW Speed Zones - the regulated speed zone for '
                             'every road in NSW, statewide linework',
                 licence='CC-BY 4.0',
                 bytes=os.path.getsize(ZIP) if os.path.exists(ZIP) else None,
                 sha256=sha256(ZIP) if os.path.exists(ZIP) else None,
                 retrieved=datetime.date.today().isoformat(),
                 clip=dict(source=LGA, margin_m=margin,
                           note='the extent is the dissolved LGA boundary plus a '
                                'declared margin, never a typed rectangle'),
                 records_statewide=n_all, records_existing=n_existing,
                 records_in_study_area=len(g))]
    with io.open(PROV, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(prov, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print('wrote %s and %s' % (OUT, PROV), flush=True)


if __name__ == '__main__':
    argparse.ArgumentParser().parse_args()
    main()
