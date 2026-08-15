#!/usr/bin/env python
"""Attach per-edge gradient from the DEM to the road and footway graphs.

Gradient is stored in the digitisation direction of the edge; the reverse
direction takes the negative. Proposal section 6.3 requires gradient to be
treated asymmetrically, because uphill and downhill are different costs and
this is material in Newcastle East and The Hill.

Also emits a walk-speed multiplier per edge using a Tobler-style rule, so the
active-transport graph carries a directional cost rather than a flat speed.
"""

# City-relative paths resolve through src/city.py: `data/...` names a
# location inside cities/<city>/, not inside the repository root.
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                  '..', '..', 'src'))
import city as _city  # noqa: E402
import os
import csv
import json
import math
import numpy as np
import rasterio
from rasterio.merge import merge

DEM_DIR = _city.path('data/raw/dem')
NET = _city.path('data/processed/network')

TILES = [os.path.join(DEM_DIR, f) for f in sorted(os.listdir(DEM_DIR)) if f.endswith('.tif')]


def build_mosaic():
    srcs = [rasterio.open(t) for t in TILES]
    arr, tf = merge(srcs)
    crs = srcs[0].crs
    nod = srcs[0].nodata
    for s in srcs:
        s.close()
    return arr[0], tf, crs, nod


def sampler(arr, tf, nod):
    inv = ~tf
    h, w = arr.shape

    def sample(lon, lat):
        c, r = inv * (lon, lat)
        r, c = int(round(r)), int(round(c))
        if r < 0 or c < 0 or r >= h or c >= w:
            return None
        v = float(arr[r, c])
        if nod is not None and v == nod:
            return None
        if v < -400 or v > 3000:
            return None
        return v
    return sample


def tobler_factor(g):
    """Walking speed multiplier relative to flat, from Tobler's hiking function
    normalised so that a 0% grade gives 1.0."""
    s = g / 100.0
    v = math.exp(-3.5 * abs(s + 0.05))
    return v / math.exp(-3.5 * 0.05)


def process(edges_csv, geom_jsonl, id_field, out_csv):
    arr, tf, crs, nod = build_mosaic()
    smp = sampler(arr, tf, nod)
    geom = {}
    with open(geom_jsonl, encoding='utf-8') as fh:
        for line in fh:
            d = json.loads(line)
            geom[d[id_field]] = d['coords']
    rows = list(csv.DictReader(open(edges_csv, encoding='utf-8')))
    stats = {'n': 0, 'sampled': 0, 'nodata': 0}
    grads = []
    for r in rows:
        stats['n'] += 1
        co = geom.get(r[id_field])
        L = float(r['length_m'] or 0)
        if not co or L <= 0:
            stats['nodata'] += 1
            continue
        z0 = smp(co[0][0], co[0][1])
        z1 = smp(co[-1][0], co[-1][1])
        if z0 is None or z1 is None:
            stats['nodata'] += 1
            continue
        # rise over the true path length, clipped to a physically plausible band
        g = max(-25.0, min(25.0, (z1 - z0) / L * 100.0))
        # roughness: max absolute segment gradient along the way
        zs = [smp(c[0], c[1]) for c in co]
        zs = [z for z in zs if z is not None]
        r['gradient_pct'] = round(g, 3)
        r['elev_start_m'] = round(z0, 1)
        r['elev_end_m'] = round(z1, 1)
        r['elev_min_m'] = round(min(zs), 1) if zs else ''
        r['elev_max_m'] = round(max(zs), 1) if zs else ''
        r['gradient_source'] = 'copernicus_glo30'
        if 'footway_edge_id' in r:
            r['walk_speed_factor_fwd'] = round(tobler_factor(g), 4)
            r['walk_speed_factor_rev'] = round(tobler_factor(-g), 4)
        stats['sampled'] += 1
        grads.append(abs(g))
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with open(out_csv, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    if grads:
        a = np.array(grads)
        stats['abs_gradient_pct'] = {'mean': round(float(a.mean()), 2),
                                     'p50': round(float(np.percentile(a, 50)), 2),
                                     'p90': round(float(np.percentile(a, 90)), 2),
                                     'p99': round(float(np.percentile(a, 99)), 2),
                                     'max': round(float(a.max()), 2)}
    return stats


if __name__ == '__main__':
    print('DEM tiles:', [os.path.basename(t) for t in TILES])
    rep = {}
    rep['roads'] = process(os.path.join(NET, 'A1_road_edges.csv'),
                           os.path.join(NET, 'A1_road_geometry.jsonl'),
                           'edge_id', os.path.join(NET, 'A1_road_edges.csv'))
    print('roads   :', rep['roads'], flush=True)
    rep['footways'] = process(os.path.join(NET, 'A6_footway_edges.csv'),
                              os.path.join(NET, 'A6_footway_geometry.jsonl'),
                              'footway_edge_id', os.path.join(NET, 'A6_footway_edges.csv'))
    print('footways:', rep['footways'], flush=True)
    json.dump(rep, open(os.path.join(NET, '_gradient_report.json'), 'w'), indent=2)
