#!/usr/bin/env python
"""Overpass harvester for the study area, on an extent DERIVED from the package.

Both extents used to be typed rectangles. The study one did not cover the study
area: it cut 0.30 degrees off the west and 0.26 off the east of the five
declared LGAs, leaving **87 of 1,500 core SA1s and 31,940 agents - 5.2% of the
population - outside the road network**, where they made 3.2x longer trips and
cycled at 36.5% against 14.8%. It survived three phases, because a typed
rectangle cannot be wrong in a way anyone notices (issue #32).

So neither is typed now:

  STUDY      the dissolved LGA boundary from data/processed/zones/zones_LGA.gpkg,
             plus A.osm.harvest_margin_m.
  BUILDINGS  the observed light rail STOP SET from the GTFS-derived
             A3_stop_extras.csv, plus A.osm.buildings_margin_m. The stops are
             observed, they exist before any OSM harvest, and every city with a
             corridor has them. At the declared margin this extent CONTAINS the
             rectangle it replaced, so no building previously harvested is lost
             (issue #34).

Both inputs are produced from raw downloads that do not depend on OSM, so a cold
start still works: ABS boundaries for the first, the GTFS feed for the second.

**Tiled.** The corrected study extent is 2.02x the rectangle it replaced, and a
single Overpass query over it returns 504 Gateway Timeout - measured, twice, on
the roads layer. Each layer is therefore fetched over a grid of tiles no larger
than A.osm.harvest_tile_deg on a side and merged, de-duplicating elements by id:
Overpass returns a whole way when any part of it matches, so a way crossing a
tile boundary arrives in both.
"""
import sys, os, re, math, time, urllib.request, urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import registry as _registry  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import osm_tiles  # noqa: E402
CFG = _registry.load()

#: Overpass mirrors, tried in order. One endpoint returning 504 on a tile that
#: another serves in seconds is normal load-shedding, not a fault in the query -
#: measured here on the roads layer, where the same tile failed four times on
#: the first mirror. Having a second is the difference between a harvest that
#: completes and one that needs babysitting.
ENDPOINTS = ("https://overpass.kumi.systems/api/interpreter",
             "https://overpass-api.de/api/interpreter",
             "https://overpass.private.coffee/api/interpreter")

LGA = 'data/processed/zones/zones_LGA.gpkg'
STOPS = 'data/processed/schedule_extras/A3_stop_extras.csv'
CRS_M = 'EPSG:28356'


def _bbox_from_lga(margin_m):
    """S,W,N,E of the dissolved LGA boundary, buffered."""
    import geopandas as gpd
    g = gpd.read_file(LGA).to_crs(CRS_M)
    w, s, e, n = g.geometry.union_all().buffer(margin_m).bounds
    import shapely.geometry as sg
    ll = gpd.GeoSeries([sg.box(w, s, e, n)], crs=CRS_M).to_crs('EPSG:4326').total_bounds
    return (round(float(ll[1]), 4), round(float(ll[0]), 4),
            round(float(ll[3]), 4), round(float(ll[2]), 4))


def _bbox_from_corridor_stops(margin_m):
    """S,W,N,E of the observed light rail stop set, buffered."""
    import csv as _csv
    import geopandas as gpd
    import shapely.geometry as sg
    pts = []
    with open(STOPS, encoding='utf-8') as f:
        for r in _csv.DictReader(f):
            if r.get('modes_served') == CORRIDOR_MODE:
                pts.append(sg.Point(float(r['stop_lon']), float(r['stop_lat'])))
    if not pts:
        raise SystemExit('no %r stop found in %s - the corridor extent is derived '
                         'from the stop set and cannot be guessed'
                         % (CORRIDOR_MODE, STOPS))
    g = gpd.GeoSeries(pts, crs='EPSG:4326').to_crs(CRS_M)
    w, s, e, n = g.union_all().buffer(margin_m).bounds
    ll = gpd.GeoSeries([sg.box(w, s, e, n)], crs=CRS_M).to_crs('EPSG:4326').total_bounds
    return (round(float(ll[1]), 4), round(float(ll[0]), 4),
            round(float(ll[3]), 4), round(float(ll[2]), 4))


#: The GTFS mode label the corridor under study runs under.
CORRIDOR_MODE = CFG.get('A.transit.corridor_mode_label')

STUDY = _bbox_from_lga(CFG.get('A.osm.harvest_margin_m'))
CORRIDOR = _bbox_from_corridor_stops(CFG.get('A.osm.buildings_margin_m'))

def bb(b): return f"{b[0]},{b[1]},{b[2]},{b[3]}"

QUERY_TEMPLATES = {
 # --- A1 road network (drivable + service) ---
 "roads": """[out:xml][timeout:1800];
 (way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|service|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link|road|busway)$"]({bb}););
 (._;>;); out body qt;""",

 # --- A6 active transport network ---
 "footways": """[out:xml][timeout:1800];
 (way["highway"~"^(footway|path|pedestrian|steps|cycleway|track|bridleway|corridor)$"]({bb});
  way["footway"]({bb});
  way["sidewalk"]({bb}););
 (._;>;); out body qt;""",

 # --- rail / tram / PT infrastructure ---
 "railways": """[out:xml][timeout:1800];
 (way["railway"]({bb}); node["railway"]({bb});
  relation["route"~"^(train|tram|light_rail|subway|bus|ferry)$"]({bb}););
 (._;>;); out body qt;""",

 # --- A2 signals / crossings / turn restrictions ---
 "signals": """[out:xml][timeout:900];
 (node["highway"="traffic_signals"]({bb});
  node["highway"="crossing"]({bb});
  node["crossing"]({bb});
  node["highway"="stop"]({bb});
  node["highway"="give_way"]({bb});
  node["traffic_calming"]({bb});
  relation["type"="restriction"]({bb}););
 out body qt;""",

 # --- A5 parking ---
 "parking": """[out:xml][timeout:900];
 (nwr["amenity"="parking"]({bb});
  nwr["amenity"="parking_space"]({bb});
  nwr["amenity"="motorcycle_parking"]({bb});
  way["parking:lane:both"]({bb});
  way["parking:lane:left"]({bb});
  way["parking:lane:right"]({bb});
  way["parking:both"]({bb});
  way["parking:left"]({bb});
  way["parking:right"]({bb}););
 (._;>;); out body qt;""",

 # --- D1 land use / POI ---
 "poi": """[out:xml][timeout:1800];
 (nwr["shop"]({bb}); nwr["amenity"]({bb}); nwr["office"]({bb});
  nwr["tourism"]({bb}); nwr["leisure"]({bb}); nwr["healthcare"]({bb});
  nwr["landuse"~"^(retail|commercial|industrial|residential|education)$"]({bb}););
 (._;>;); out body qt;""",

 # --- D1 CBD buildings for frontage/floorspace ---
 "buildings_cbd": """[out:xml][timeout:1800];
 (way["building"]({bb}); relation["building"]({bb}););
 (._;>;); out body qt;""",

 # --- admin boundaries ---
 "boundaries": """[out:xml][timeout:900];
 (relation["boundary"="administrative"]["admin_level"~"^(4|6|7)$"]({bb}););
 (._;>;); out body qt;""",

 # --- water bodies, for the run replay basemap only ---
 # NO MODEL CONSUMER. The harbour, the Hunter River and Lake Macquarie are what
 # make an overhead view of this study area legible as Newcastle, and none of
 # them is a polygon in any other extract: `poi` carries 7 natural=water ways in
 # total. Nothing in src/build or src/run reads this; src/analyse/build_basemap.py
 # does. ODbL 1.0 like every other OSM-derived layer.
 "water": """[out:xml][timeout:1800];
 (way["natural"="water"]({bb}); relation["natural"="water"]({bb});
  way["waterway"="riverbank"]({bb}); relation["waterway"="riverbank"]({bb});
  way["landuse"~"^(reservoir|basin)$"]({bb});
  way["natural"="coastline"]({bb}););
 (._;>;); out body qt;""",

 # --- green and open space, for the run replay basemap only ---
 # Same standing as `water`: cartography, not a model input.
 "green": """[out:xml][timeout:1800];
 (way["leisure"~"^(park|golf_course|nature_reserve|garden)$"]({bb});
  way["natural"~"^(wood|scrub|heath|beach|sand|wetland)$"]({bb});
  way["landuse"~"^(forest|grass|meadow|recreation_ground|cemetery|village_green)$"]({bb}););
 (._;>;); out body qt;""",
}



#: Which derived extent each layer is harvested over.
QUERY_EXTENT = {
    'roads': STUDY,
    'footways': STUDY,
    'railways': STUDY,
    'signals': STUDY,
    'parking': STUDY,
    'poi': STUDY,
    'buildings_cbd': CORRIDOR,
    'boundaries': STUDY,
    'water': STUDY,
    'green': STUDY,
}

TILE_DEG = CFG.get('A.osm.harvest_tile_deg')
TILE_DIR = 'networks/osm/_tiles'


def _get(query, dest, label):
    """One Overpass request, rotating mirrors and backing off between attempts.

    A tile is only given up on after every mirror has refused it repeatedly; the
    caller caches whatever did arrive, so a resumed harvest retries just the
    stragglers.
    """
    attempts = CFG.get('A.osm.harvest_attempts')
    for attempt in range(attempts):
        ep = ENDPOINTS[attempt % len(ENDPOINTS)]
        t0 = time.time()
        try:
            req = urllib.request.Request(
                ep, data=urllib.parse.urlencode({"data": query}).encode(),
                headers={"User-Agent": "newcastle-lr-sim/0.1 (research)"})
            with urllib.request.urlopen(req, timeout=1900) as r, open(dest, "wb") as f:
                n = 0
                while True:
                    c = r.read(1 << 20)
                    if not c:
                        break
                    f.write(c)
                    n += len(c)
            print("    OK    %s: %s B in %.0fs" % (label, format(n, ","), time.time() - t0),
                  flush=True)
            return True
        except Exception as e:
            if os.path.exists(dest):
                os.remove(dest)      # never leave a truncated tile to be cached
            print("    RETRY %s attempt %d on %s: %s"
                  % (label, attempt + 1, ep.split("/")[2], e), flush=True)
            time.sleep(min(120, 15 * (attempt + 1)))
    return False


def fetch(name, outdir="networks/osm"):
    """Harvest one layer over its derived extent, tile by tile, and merge.

    A layer already present and non-trivial is skipped, so an interrupted
    harvest resumes rather than re-downloading what it already has.
    """
    os.makedirs(outdir, exist_ok=True)
    os.makedirs(TILE_DIR, exist_ok=True)
    path = os.path.join(outdir, "newcastle_%s.osm" % name)
    if os.path.exists(path) and os.path.getsize(path) > 20000:
        print("SKIP %s (%s B)" % (name, format(os.path.getsize(path), ",")))
        return path
    extent = QUERY_EXTENT[name]
    grid = osm_tiles.tiles(extent, TILE_DEG)
    print("%s: %d tile(s) over %s" % (name, len(grid), extent), flush=True)
    parts = []
    for i, tb in enumerate(grid):
        part = os.path.join(TILE_DIR, "%s_%02d.osm" % (name, i))
        if os.path.exists(part) and os.path.getsize(part) > 200:
            print("    have  tile %d/%d" % (i + 1, len(grid)), flush=True)
            parts.append(part)
            continue
        q = QUERY_TEMPLATES[name].format(bb=bb(tb))
        if not _get(q, part, "tile %d/%d" % (i + 1, len(grid))):
            print("FAIL %s: tile %d could not be fetched" % (name, i + 1), flush=True)
            return None
        parts.append(part)
    kept, dup = osm_tiles.merge(parts, path)
    ways, with_children = osm_tiles.verify(path)
    print("OK   %s: %s elements (%s duplicates across tiles), %d/%d sampled ways "
          "carry geometry -> %s"
          % (name, format(kept, ","), format(dup, ","), with_children, ways, path),
          flush=True)
    # Tiles are only discarded once the merge has been verified. Deleting them
    # first is what made the truncation bug expensive: the merged files were
    # corrupt and the inputs were already gone.
    for part in parts:
        os.remove(part)
    return path


if __name__ == "__main__":
    print("STUDY     S,W,N,E = %s" % (STUDY,), flush=True)
    print("BUILDINGS S,W,N,E = %s" % (CORRIDOR,), flush=True)
    names = sys.argv[1:] or list(QUERY_TEMPLATES)
    unknown = [n for n in names if n not in QUERY_TEMPLATES]
    if unknown:
        raise SystemExit("no such layer %s. Available: %s"
                         % (unknown, ", ".join(sorted(QUERY_TEMPLATES))))
    for n in names:
        fetch(n)
