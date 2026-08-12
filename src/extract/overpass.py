#!/usr/bin/env python
"""Overpass harvester for the Greater Newcastle study area."""
import sys,os,time,urllib.request,urllib.parse

EP="https://overpass.kumi.systems/api/interpreter"
# Greater Newcastle: Newcastle + Lake Macquarie + Maitland + Cessnock + Hunter Line
STUDY=(-33.20,151.10,-32.55,151.95)          # S,W,N,E
CORRIDOR=(-32.9450,151.7250,-32.9050,151.8050)

def bb(b): return f"{b[0]},{b[1]},{b[2]},{b[3]}"

QUERIES={
 # --- A1 road network (drivable + service) ---
 "roads": f"""[out:xml][timeout:1800];
 (way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street|service|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link|road|busway)$"]({bb(STUDY)}););
 (._;>;); out body qt;""",

 # --- A6 active transport network ---
 "footways": f"""[out:xml][timeout:1800];
 (way["highway"~"^(footway|path|pedestrian|steps|cycleway|track|bridleway|corridor)$"]({bb(STUDY)});
  way["footway"]({bb(STUDY)});
  way["sidewalk"]({bb(STUDY)}););
 (._;>;); out body qt;""",

 # --- rail / tram / PT infrastructure ---
 "railways": f"""[out:xml][timeout:1800];
 (way["railway"]({bb(STUDY)}); node["railway"]({bb(STUDY)});
  relation["route"~"^(train|tram|light_rail|subway|bus|ferry)$"]({bb(STUDY)}););
 (._;>;); out body qt;""",

 # --- A2 signals / crossings / turn restrictions ---
 "signals": f"""[out:xml][timeout:900];
 (node["highway"="traffic_signals"]({bb(STUDY)});
  node["highway"="crossing"]({bb(STUDY)});
  node["crossing"]({bb(STUDY)});
  node["highway"="stop"]({bb(STUDY)});
  node["highway"="give_way"]({bb(STUDY)});
  node["traffic_calming"]({bb(STUDY)});
  relation["type"="restriction"]({bb(STUDY)}););
 out body qt;""",

 # --- A5 parking ---
 "parking": f"""[out:xml][timeout:900];
 (nwr["amenity"="parking"]({bb(STUDY)});
  nwr["amenity"="parking_space"]({bb(STUDY)});
  nwr["amenity"="motorcycle_parking"]({bb(STUDY)});
  way["parking:lane:both"]({bb(STUDY)});
  way["parking:lane:left"]({bb(STUDY)});
  way["parking:lane:right"]({bb(STUDY)});
  way["parking:both"]({bb(STUDY)});
  way["parking:left"]({bb(STUDY)});
  way["parking:right"]({bb(STUDY)}););
 (._;>;); out body qt;""",

 # --- D1 land use / POI ---
 "poi": f"""[out:xml][timeout:1800];
 (nwr["shop"]({bb(STUDY)}); nwr["amenity"]({bb(STUDY)}); nwr["office"]({bb(STUDY)});
  nwr["tourism"]({bb(STUDY)}); nwr["leisure"]({bb(STUDY)}); nwr["healthcare"]({bb(STUDY)});
  nwr["landuse"~"^(retail|commercial|industrial|residential|education)$"]({bb(STUDY)}););
 (._;>;); out body qt;""",

 # --- D1 CBD buildings for frontage/floorspace ---
 "buildings_cbd": f"""[out:xml][timeout:1800];
 (way["building"]({bb(CORRIDOR)}); relation["building"]({bb(CORRIDOR)}););
 (._;>;); out body qt;""",

 # --- admin boundaries ---
 "boundaries": f"""[out:xml][timeout:900];
 (relation["boundary"="administrative"]["admin_level"~"^(4|6|7)$"]({bb(STUDY)}););
 (._;>;); out body qt;""",

 # --- water bodies, for the run replay basemap only ---
 # NO MODEL CONSUMER. The harbour, the Hunter River and Lake Macquarie are what
 # make an overhead view of this study area legible as Newcastle, and none of
 # them is a polygon in any other extract: `poi` carries 7 natural=water ways in
 # total. Nothing in src/build or src/run reads this; src/analyse/build_basemap.py
 # does. ODbL 1.0 like every other OSM-derived layer.
 "water": f"""[out:xml][timeout:1800];
 (way["natural"="water"]({bb(STUDY)}); relation["natural"="water"]({bb(STUDY)});
  way["waterway"="riverbank"]({bb(STUDY)}); relation["waterway"="riverbank"]({bb(STUDY)});
  way["landuse"~"^(reservoir|basin)$"]({bb(STUDY)});
  way["natural"="coastline"]({bb(STUDY)}););
 (._;>;); out body qt;""",

 # --- green and open space, for the run replay basemap only ---
 # Same standing as `water`: cartography, not a model input.
 "green": f"""[out:xml][timeout:1800];
 (way["leisure"~"^(park|golf_course|nature_reserve|garden)$"]({bb(STUDY)});
  way["natural"~"^(wood|scrub|heath|beach|sand|wetland)$"]({bb(STUDY)});
  way["landuse"~"^(forest|grass|meadow|recreation_ground|cemetery|village_green)$"]({bb(STUDY)}););
 (._;>;); out body qt;""",
}

def fetch(name,q,outdir="networks/osm"):
    os.makedirs(outdir,exist_ok=True)
    path=f"{outdir}/newcastle_{name}.osm"
    if os.path.exists(path) and os.path.getsize(path)>20000:
        print(f"SKIP {name} ({os.path.getsize(path):,} B)"); return path
    for attempt in range(4):
        t0=time.time()
        try:
            req=urllib.request.Request(EP,data=urllib.parse.urlencode({"data":q}).encode(),
                                       headers={"User-Agent":"newcastle-lr-sim/0.1 (research)"})
            with urllib.request.urlopen(req,timeout=1900) as r, open(path,"wb") as f:
                n=0
                while True:
                    c=r.read(1<<20)
                    if not c: break
                    f.write(c); n+=len(c)
            print(f"OK   {name}: {n:,} B in {time.time()-t0:.0f}s -> {path}",flush=True)
            return path
        except Exception as e:
            print(f"RETRY {name} attempt {attempt+1}: {e}",flush=True); time.sleep(20*(attempt+1))
    print(f"FAIL {name}",flush=True); return None

if __name__=="__main__":
    names=sys.argv[1:] or list(QUERIES)
    for n in names: fetch(n,QUERIES[n])
