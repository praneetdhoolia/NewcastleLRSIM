#!/usr/bin/env python
"""Adopt the REGULATED speed limit onto the road graph, where one matches.

`build_network_layers.py` fills `speed_limit_kmh` from the OSM `maxspeed` tag
where it exists and from a per-class default otherwise - on 53.7% of edges. The
TfNSW Speed Zones layer is a better source than either: it is the legal
instrument, not a mapper's transcription of a sign, and it covers the network
rather than the 714 corridor edges issue #27 is scoped to.

Precedence, strongest first:

    speed_zones    the regulated zone, matched within A.road.speed_zone_match_m
    osm            an explicit maxspeed tag
    imputed_rule   the measured per-class default (DECISIONS.md 9.33)

The join is validated rather than trusted: where an edge carries BOTH an OSM tag
and a matched zone, the two are compared and the agreement rate is reported. A
nearest-line match can capture a parallel service road, and the agreement rate is
what would show it.

Run after attach_gradient.py; it rewrites A1_road_edges.csv in place, as
attach_gradient does.
"""

# City-relative paths resolve through src/city.py: `data/...` names a
# location inside cities/<city>/, not inside the repository root.
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                  '..', '..', 'src'))
import city as _city  # noqa: E402
import io
import os
import sys
import csv
import json
import argparse

import geopandas as gpd
from shapely.geometry import LineString

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import registry as _registry  # noqa: E402
CFG = _registry.load()

NET = _city.path('data/processed/network')
ZONES = os.path.join(NET, 'A1_speed_zones.gpkg')
EDGES = os.path.join(NET, 'A1_road_edges.csv')
GEOM = os.path.join(NET, 'A1_road_geometry.jsonl')
REPORT = os.path.join(NET, '_speed_zone_report.json')
CRS_M = _city.crs()
WGS = 'EPSG:4326'


def edge_lines():
    """Edge geometry as LineStrings in metres, keyed by edge id."""
    ids, geoms = [], []
    with io.open(GEOM, encoding='utf-8') as f:
        for ln in f:
            d = json.loads(ln)
            pts = [(c[0], c[1]) for c in d['coords']]
            if len(pts) < 2:
                continue
            ids.append(d['edge_id'])
            geoms.append(LineString(pts))
    g = gpd.GeoDataFrame({'edge_id': ids}, geometry=geoms, crs=WGS)
    return g.to_crs(CRS_M)


def main():
    if not os.path.exists(ZONES):
        raise SystemExit('%s is missing - run src/extract/extract_speed_zones.py'
                         % ZONES)
    radius = CFG.get('A.road.speed_zone_match_m')
    excluded = set(CFG.get('A.road.speed_zone_excluded_classes'))
    zones = gpd.read_file(ZONES).to_crs(CRS_M)[['speed_kmh', 'zone_type', 'geometry']]
    edges = edge_lines()
    print('matching %d road edges against %d speed zone segments within %g m ...'
          % (len(edges), len(zones), radius), flush=True)

    j = gpd.sjoin_nearest(edges, zones, how='left', max_distance=radius,
                          distance_col='match_m')
    # One row per edge: the nearest zone wins, ties broken on the lower speed so
    # a repeat build cannot pick a different one.
    j = (j.sort_values(['edge_id', 'match_m', 'speed_kmh'])
          .drop_duplicates('edge_id', keep='first'))
    matched = dict(zip(j.edge_id, j.speed_kmh))
    dist = dict(zip(j.edge_id, j.match_m))

    rows = list(csv.DictReader(io.open(EDGES, encoding='utf-8')))
    n_zone = n_osm_kept = n_default_kept = 0
    agree = disagree = 0
    diffs = []
    for r in rows:
        eid = r['edge_id']
        # An edge whose speed equals its class default was imputed; anything
        # else came from an explicit OSM tag.
        had_osm = r.get('speed_limit_source') == 'osm'
        z = None if r['road_class'] in excluded else matched.get(eid)
        if z is not None and z == z:
            if had_osm:
                if abs(float(r['speed_limit_kmh']) - float(z)) < 1e-9:
                    agree += 1
                else:
                    disagree += 1
                    diffs.append((eid, r['road_class'],
                                  float(r['speed_limit_kmh']), float(z)))
            r['speed_limit_kmh'] = float(z)
            r['speed_limit_source'] = 'speed_zones'
            r['speed_zone_match_m'] = round(float(dist.get(eid, 0.0)), 2)
            n_zone += 1
        else:
            r.setdefault('speed_limit_source', 'osm' if had_osm else 'imputed_rule')
            r['speed_zone_match_m'] = ''
            if had_osm:
                n_osm_kept += 1
            else:
                n_default_kept += 1

    cols = list(dict.fromkeys(k for r in rows for k in r))
    with io.open(EDGES, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)

    both = agree + disagree
    rep = dict(match_radius_m=radius, excluded_classes=sorted(excluded), edges=len(rows), zone_segments=len(zones),
               matched_to_zone=n_zone, kept_osm=n_osm_kept,
               kept_class_default=n_default_kept,
               validated_against_osm=both,
               agreement_rate=round(agree / both, 4) if both else None,
               disagreements=len(diffs),
               example_disagreements=[dict(edge_id=e, road_class=c, osm=o, zone=z)
                                      for e, c, o, z in diffs[:10]])
    with io.open(REPORT, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(rep, f, indent=2)
        f.write('\n')
    print('   regulated speed adopted on %d of %d edges (%.1f%%)'
          % (n_zone, len(rows), 100.0 * n_zone / len(rows)), flush=True)
    print('   still on an OSM tag %d, still on a class default %d'
          % (n_osm_kept, n_default_kept), flush=True)
    if both:
        print('   validation: %d edges carry both; the zone agrees with OSM on '
              '%.1f%%' % (both, 100.0 * agree / both), flush=True)
    print('wrote %s' % REPORT, flush=True)


if __name__ == '__main__':
    argparse.ArgumentParser().parse_args()
    main()
