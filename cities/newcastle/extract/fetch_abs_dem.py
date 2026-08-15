#!/usr/bin/env python
"""ABS boundaries + Census DataPacks, and Copernicus DEM tiles."""

# City-relative paths resolve through src/city.py: `data/...` names a
# location inside cities/<city>/, not inside the repository root.
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                  '..', '..', '..', 'src'))
import city as _city  # noqa: E402
import os,urllib.request,hashlib,json,datetime
ABS="https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs/edition-3-july-2021-june-2026/access-and-downloads/digital-boundary-files/"
DP="https://www.abs.gov.au/census/find-census-data/datapacks/download/"
COP="https://copernicus-dem-30m.s3.amazonaws.com/"
M=[
 ("boundaries/SA1_2021_AUST_SHP_GDA2020.zip",ABS+"SA1_2021_AUST_SHP_GDA2020.zip","ABS ASGS Ed3 SA1 2021 digital boundaries","CC-BY 4.0"),
 ("boundaries/SA2_2021_AUST_SHP_GDA2020.zip",ABS+"SA2_2021_AUST_SHP_GDA2020.zip","ABS ASGS Ed3 SA2 2021 digital boundaries","CC-BY 4.0"),
 ("boundaries/SA3_2021_AUST_SHP_GDA2020.zip",ABS+"SA3_2021_AUST_SHP_GDA2020.zip","ABS ASGS Ed3 SA3 2021 digital boundaries","CC-BY 4.0"),
 ("boundaries/DZN_2021_AUST_GDA2020_SHP.zip",ABS+"DZN_2021_AUST_GDA2020_SHP.zip","ABS Destination Zones 2021 (workplace geography)","CC-BY 4.0"),
 ("boundaries/LGA_2021_AUST_GDA2020_SHP.zip",ABS+"LGA_2021_AUST_GDA2020_SHP.zip","ABS LGA 2021 boundaries","CC-BY 4.0"),
 ("boundaries/MB_2021_NSW_SHP_GDA2020.zip",ABS+"MB_2021_NSW_SHP_GDA2020.zip","ABS Mesh Blocks 2021 NSW","CC-BY 4.0"),
 ("census/2021_GCP_SA1_for_NSW_short-header.zip",DP+"2021_GCP_SA1_for_NSW_short-header.zip","ABS Census 2021 General Community Profile, SA1, NSW","CC-BY 4.0"),
 ("census/2021_GCP_SA2_for_NSW_short-header.zip",DP+"2021_GCP_SA2_for_NSW_short-header.zip","ABS Census 2021 GCP, SA2, NSW","CC-BY 4.0"),
 ("census/2021_PEP_SA2_for_NSW_short-header.zip",DP+"2021_PEP_SA2_for_NSW_short-header.zip","ABS Census 2021 Place of Enumeration Profile, SA2, NSW","CC-BY 4.0"),
 ("census/2021_WPP_DZN_for_NSW_short-header.zip",DP+"2021_WPP_DZN_for_NSW_short-header.zip","ABS Census 2021 Working Population Profile by Destination Zone, NSW (jobs by industry/occupation at workplace)","CC-BY 4.0"),
]


def dem_tiles():
    """Copernicus GLO-30 1-degree cells covering the DERIVED study extent.

    The list used to be typed in with the comment 'study area spans lat
    -32.55..-33.20, lon 151..152' - the same stale-extent class as the issue
    #32 harvest box: when the harvest extent was corrected to the dissolved
    LGA boundary plus A.osm.harvest_margin_m, the road network grew past
    151..152 and 6.5% of edges silently lost their gradient source. The cells
    are now derived from the same boundary + margin the harvest itself uses.
    Falls back to the two original cells, loudly, if the processed boundary
    does not exist yet (first-fetch bootstrap: boundaries download before
    zones are built).
    """
    import math
    try:
        import geopandas as gpd
        _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                          '..', '..', '..', 'src'))
        import registry as _registry
        margin = _registry.load().get('A.osm.harvest_margin_m')
        lga = gpd.read_file(_city.path('data/processed/zones/zones_LGA.gpkg'))
        if 'zone_tier' in lga.columns:
            lga = lga[lga.zone_tier == 'core']
        w, s, e, n = lga.to_crs(4326).total_bounds
        deg = margin / 111000.0
        s, w, n, e = s - deg, w - deg, n + deg, e + deg
    except Exception as exc:                                   # noqa: BLE001
        print('DEM extent falls back to the two original cells - the derived '
              'boundary is not available yet (%s)' % exc, flush=True)
        s, w, n, e = -33.20, 151.0, -32.55, 152.0
    cells = []
    for lat0 in range(int(math.floor(s)), int(math.ceil(n))):
        for lon0 in range(int(math.floor(w)), int(math.ceil(e))):
            name = 'Copernicus_DSM_COG_10_S%02d_00_E%03d_00_DEM' % (-lat0, lon0)
            cells.append(('dem/%s.tif' % name, COP + '%s/%s.tif' % (name, name),
                          'Copernicus GLO-30 DEM tile S%02dE%03d (cell derived '
                          'from the dissolved LGA boundary + harvest margin)'
                          % (-lat0, lon0), 'ESA / open'))
    return cells


M += dem_tiles()
root=_city.path('data/raw'); prov=[]
for rel,url,desc,lic in M:
    p=os.path.join(root,rel); os.makedirs(os.path.dirname(p),exist_ok=True)
    if os.path.exists(p) and os.path.getsize(p)>1000:
        print(f"SKIP {rel} ({os.path.getsize(p):,})",flush=True)
    else:
        print(f"GET  {rel}",flush=True)
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'newcastle-lr-sim/0.1 (research)'})
            with urllib.request.urlopen(req,timeout=1800) as r, open(p,'wb') as f:
                while True:
                    c=r.read(1<<20)
                    if not c: break
                    f.write(c)
        except Exception as e:
            print(f"  FAIL {e}",flush=True); continue
    sz=os.path.getsize(p)
    h=hashlib.sha256(open(p,'rb').read()).hexdigest()
    print(f"  {sz:>13,} B",flush=True)
    prov.append({"path":rel,"url":url,"description":desc,"licence":lic,"bytes":sz,"sha256":h,
                 "retrieved":datetime.date.today().isoformat()})
json.dump(prov,open(os.path.join(root,'provenance_abs_dem.json'),'w'),indent=2)
print("wrote provenance_abs_dem.json",len(prov))
