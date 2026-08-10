#!/usr/bin/env python
"""Map each traffic count station to the network links it counts.

A count target is a **two-way daily total at a point** (DECISIONS.md 12.2). To
compare it with the model, that point has to be resolved to the links carrying
the road there - both directions, since the count is `PRESCRIBED AND COUNTER`.

The match is made on **road name plus proximity**, and never on proximity alone
where a name is available:

  * project the station to EPSG:28356 and take every car link whose midpoint is
    within the search radius;
  * if the station's `road_name` matches a link's `name`, keep only the matching
    links - a station on the Pacific Highway must not be matched to the service
    road beside it;
  * keep the nearest link per direction, identified by the from/to node pair, so
    a divided road contributes both carriageways and a two-way single
    carriageway contributes once.

Every station carries how it was matched and how far away the link was, so a
weak match is visible in the fit rather than hidden inside it. Stations that
cannot be matched are written out as unmatched rather than silently dropped:
a count target with no link is a target the model cannot be scored against, and
that has to be stated.

This reads the station coordinates and the network. **It does not read a
validation target value**, so it is indifferent to the calibration/holdout split
and maps all 119 stations alike.
"""
import argparse
import csv
import gzip
import math
import os
import re

import pyproj

CRS_M = 'EPSG:28356'
TO_M = pyproj.Transformer.from_crs('EPSG:4326', CRS_M, always_xy=True).transform

STATIONS = 'data/processed/validation/road_aadt_targets.csv'
OUT = 'data/processed/validation/count_station_links.csv'
DEFAULT_NETWORK = 'scenarios/matsim/S2/network.xml.gz'

NODE_RE = re.compile(r'<node id="([^"]+)"[^>]*x="([-\d.eE]+)"[^>]*y="([-\d.eE]+)"')
LINK_RE = re.compile(r'<link id="([^"]+)" from="([^"]+)" to="([^"]+)"[^>]*>')
MODES_RE = re.compile(r'modes="([^"]*)"')
# the road name is a child <attribute>, not a link attribute
WAY_NAME_RE = re.compile(r'<attribute name="osm:way:name"[^>]*>([^<]*)</attribute>')


def normalise(name):
    """Compare road names without punctuation, case or the usual abbreviations."""
    s = (name or '').lower()
    for a, b in (('street', 'st'), ('road', 'rd'), ('avenue', 'ave'),
                 ('drive', 'dr'), ('highway', 'hwy'), ('parade', 'pde'),
                 ('lane', 'ln'), ('place', 'pl'), ('terrace', 'tce'),
                 ('crescent', 'cres'), ('boulevard', 'blvd')):
        s = re.sub(r'\b%s\b' % a, b, s)
    return re.sub(r'[^a-z0-9 ]', '', s).strip()


def load_network(path):
    """Car links as (id, name, midpoint, node pair). Streamed, not parsed."""
    nodes, links = {}, []
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        pending = None
        for line in f:
            m = NODE_RE.search(line)
            if m:
                nodes[m.group(1)] = (float(m.group(2)), float(m.group(3)))
                continue
            m = LINK_RE.search(line)
            if m:
                modes = MODES_RE.search(line)
                pending = ([m.group(1), '', m.group(2), m.group(3)]
                           if modes and 'car' in modes.group(1).split(',')
                           else None)
                if pending and line.rstrip().endswith('/>'):
                    links.append(tuple(pending))
                    pending = None
                continue
            if pending is None:
                continue
            nm = WAY_NAME_RE.search(line)
            if nm:
                pending[1] = nm.group(1)
            elif '</link>' in line:
                links.append(tuple(pending))
                pending = None
    out = []
    for lid, name, a, b in links:
        if a not in nodes or b not in nodes:
            continue
        (x1, y1), (x2, y2) = nodes[a], nodes[b]
        out.append(dict(link=lid, name=name, from_node=a, to_node=b,
                        mx=(x1 + x2) / 2.0, my=(y1 + y2) / 2.0))
    return out


def match(stations, links, radius_m):
    rows, unmatched = [], []
    for s in stations:
        try:
            sx, sy = TO_M(float(s['lon']), float(s['lat']))
        except (TypeError, ValueError):
            unmatched.append((s, 'no coordinate'))
            continue
        near = []
        for l in links:
            d = math.hypot(l['mx'] - sx, l['my'] - sy)
            if d <= radius_m:
                near.append((d, l))
        if not near:
            unmatched.append((s, 'no car link within %d m' % radius_m))
            continue
        want = normalise(s.get('road_name') or s.get('name'))
        named = [(d, l) for d, l in near if want and normalise(l['name']) == want]
        how = 'name_and_proximity' if named else 'proximity_only'
        pool = named or near
        pool.sort(key=lambda t: t[0])
        # one link per direction: the node pair unordered identifies the road
        # segment, and the two orderings are its two carriageways
        seen, chosen = set(), []
        for d, l in pool:
            key = tuple(sorted((l['from_node'], l['to_node'])))
            if key in seen:
                continue
            seen.add(key)
            chosen.append((d, l))
            if len(chosen) >= 2:
                break
        for d, l in chosen:
            rows.append(dict(station_key=s['station_key'], split=s['split'],
                             station_name=s['name'], road_name=s['road_name'],
                             link=l['link'], link_name=l['name'],
                             distance_m=round(d, 1), matched_by=how))
    return rows, unmatched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--network', default=DEFAULT_NETWORK)
    ap.add_argument('--radius', type=float, default=120.0)
    a = ap.parse_args()

    with open(STATIONS, encoding='utf-8') as f:
        stations = list(csv.DictReader(f))
    links = load_network(a.network)
    rows, unmatched = match(stations, links, a.radius)

    with open(OUT, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    matched = {r['station_key'] for r in rows}
    by_how = {}
    for r in rows:
        by_how[r['matched_by']] = by_how.get(r['matched_by'], 0) + 1
    print('%d car links loaded from %s' % (len(links), a.network))
    print('%d of %d stations matched (%d links); %d unmatched'
          % (len(matched), len(stations), len(rows), len(unmatched)))
    print('  by match quality: %s' % by_how)
    cal = {r['station_key'] for r in rows if r['split'] == 'calibration'}
    print('  calibration stations matched: %d of %d'
          % (len(cal), sum(1 for s in stations if s['split'] == 'calibration')))
    for s, why in unmatched[:10]:
        print('  UNMATCHED %s %s (%s): %s'
              % (s['station_key'], s['name'], s['split'], why))


if __name__ == '__main__':
    main()
