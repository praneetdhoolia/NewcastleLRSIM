#!/usr/bin/env python
"""Reconstruct an overhead replay of a simulated day from a MATSim event stream.

MATSim's own on-the-fly viewer (OTFVis) is a contrib and the pinned
`pt2matsim-26.6-shaded.jar` carries no contribs at all, so it is not available
and adding it would be a toolchain change - a model change under CLAUDE.md.
Everything needed is in the outputs anyway: `entered link` and `left link`
events give the time a vehicle occupied each link, and the run's own
`output_network.xml.gz` gives the link endpoints, so a position can be
interpolated for any vehicle at any second.

This is a DIAGNOSTIC, not a result. It shows what a run did, at whatever sample
fraction and iteration count that run used, and carries those in its header so a
picture can never be separated from the run that produced it.

Output is a single JSON payload whose frames are base64 uint16 pairs - one
buffer for road vehicles and one for transit, per frame. Positions are all a
renderer needs, so no identity is carried: that is 4 bytes a vehicle a frame
against about 20 for the same thing as JSON numbers, which is the difference
between a 25% run fitting in a page and not.

Coordinates are quantised to unsigned 16-bit over the SHARED basemap bounding
box when one is given, so vehicles and roads land in the same frame of
reference; about 2 m over a 130 km extent, far finer than a screen pixel.

    python src/analyse/replay_events.py results/<run>/output --out docs/replay.json
"""
import os
import re
import zlib
import base64
import struct
import gzip
import json
import math
import argparse
import collections


def read_network(path):
    """Node coordinates and link endpoints from a MATSim network."""
    nodes = {}
    links = {}
    node_re = re.compile(r'<node id="([^"]+)" x="([^"]+)" y="([^"]+)"')
    link_re = re.compile(r'<link id="([^"]+)" from="([^"]+)" to="([^"]+)"')
    op = gzip.open if path.endswith('.gz') else open
    with op(path, 'rt', encoding='utf-8') as f:
        for line in f:
            m = node_re.search(line)
            if m:
                nodes[m.group(1)] = (float(m.group(2)), float(m.group(3)))
                continue
            m = link_re.search(line)
            if m:
                links[m.group(1)] = (m.group(2), m.group(3))
    out = {}
    for lid, (a, b) in links.items():
        if a in nodes and b in nodes:
            out[lid] = (nodes[a][0], nodes[a][1], nodes[b][0], nodes[b][1])
    return out


def scan_events(path, links, step, keep_every, horizon_s):
    """Position samples per frame, by streaming the event file once.

    Holds one open traversal per vehicle rather than the whole history, so peak
    memory is the number of vehicles in the network at once, not the number of
    events.
    """
    ev = re.compile(r'time="([0-9.]+)" type="([^"]+)"')
    veh_re = re.compile(r'vehicle="([^"]+)"')
    link_re = re.compile(r'link="([^"]+)"')
    open_leg = {}                      # vehicle -> (link, t_enter)
    transit = set()
    vid = {}                           # vehicle -> small integer id
    frames = collections.defaultdict(list)
    n_frames = int(horizon_s // step) + 1
    kept = 0
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        for line in f:
            m = ev.search(line)
            if not m:
                continue
            t = float(m.group(1))
            typ = m.group(2)
            if typ == 'TransitDriverStarts':
                mv = veh_re.search(line)
                if mv:
                    transit.add(mv.group(1))
                continue
            if typ not in ('entered link', 'left link',
                           'vehicle enters traffic', 'vehicle leaves traffic'):
                continue
            mv = veh_re.search(line)
            ml = link_re.search(line)
            if not mv or not ml:
                continue
            v, lid = mv.group(1), ml.group(1)
            if typ in ('entered link', 'vehicle enters traffic'):
                open_leg[v] = (lid, t)
                continue
            # a traversal closed: emit its frames
            prev = open_leg.pop(v, None)
            if prev is None or prev[0] != lid:
                continue
            geom = links.get(lid)
            if geom is None:
                continue
            if v not in vid:
                # deterministic thinning on the vehicle id, so the same
                # vehicles are drawn every time the replay is regenerated.
                # crc32, not hash(): Python salts string hashing per process,
                # which would make the same run produce a different picture.
                if keep_every > 1 and (zlib.crc32(v.encode()) % keep_every):
                    vid[v] = -1
                else:
                    vid[v] = len(vid)
                    kept += 1
            i = vid[v]
            if i < 0:
                continue
            t_in, t_out = prev[1], max(t, prev[1] + 1e-6)
            x0, y0, x1, y1 = geom
            f0 = int(math.ceil(t_in / step))
            f1 = int(math.floor(t_out / step))
            mode = 1 if v in transit else 0
            for fr in range(max(f0, 0), min(f1, n_frames - 1) + 1):
                a = (fr * step - t_in) / (t_out - t_in)
                a = 0.0 if a < 0 else (1.0 if a > 1 else a)
                frames[fr].append((x0 + (x1 - x0) * a,
                                   y0 + (y1 - y0) * a, mode))
    return frames, kept, len(vid)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('output_dir', help='a run output directory')
    ap.add_argument('--events', default=None,
                    help='event file (default: the run output_events.xml.gz)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--step', type=int, default=60,
                    help='simulated seconds between animation frames')
    ap.add_argument('--keep-every', type=int, default=1,
                    help='draw 1 vehicle in N; 1 draws every vehicle')
    ap.add_argument('--horizon-h', type=float, default=30.0)
    ap.add_argument('--net-sample', type=int, default=6,
                    help='draw 1 link in N as the fallback background map')
    ap.add_argument('--basemap', default=None,
                    help='a build_basemap.py payload; its bounding box is then '
                         'used so roads and vehicles share one frame of '
                         'reference, and the crude link background is dropped')
    a = ap.parse_args()
    # coordinate quantisation range: a rendering precision, not a model
    # value, so it is local to the writer rather than a declared field
    quant = 65535

    net_path = os.path.join(a.output_dir, 'output_network.xml.gz')
    events = a.events or os.path.join(a.output_dir, 'output_events.xml.gz')
    print('reading network ...', flush=True)
    links = read_network(net_path)
    print('   %d links' % len(links), flush=True)

    print('streaming events (this reads the whole file once) ...', flush=True)
    frames, kept, seen = scan_events(events, links, a.step, a.keep_every,
                                     a.horizon_h * 3600)
    print('   %d vehicles drawn of %d seen' % (kept, seen), flush=True)

    base = json.load(open(a.basemap, encoding='utf-8')) if a.basemap else None
    if base:
        x0, y0, x1, y1 = base['bbox']
    else:
        xs = [g[0] for g in links.values()] + [g[2] for g in links.values()]
        ys = [g[1] for g in links.values()] + [g[3] for g in links.values()]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    sx = quant / max(x1 - x0, 1.0)
    sy = quant / max(y1 - y0, 1.0)

    def qx(x):
        return max(0, min(quant, int((x - x0) * sx)))

    def qy(y):
        return max(0, min(quant, int((y - y0) * sy)))

    # the crude fallback background: every Nth link as a straight segment. Only
    # used when no real basemap is supplied, because a basemap carries the true
    # polyline, the road class and the lane count instead.
    net = []
    if not base:
        for i, g in enumerate(sorted(links.items())):
            if i % a.net_sample:
                continue
            gx = g[1]
            net.append([qx(gx[0]), qy(gx[1]), qx(gx[2]), qy(gx[3])])

    def packframe(pts, want):
        # int32 CENTIMETRES from the basemap origin, not a uint16 grid over the
        # whole study area. A uint16 grid is 2 m, and at a 10 m view that is a
        # fifth of the screen, so vehicles would jump between staircase
        # positions instead of moving. 8 bytes a vehicle a frame.
        buf = bytearray()
        for x, y, m in pts:
            if m == want:
                buf += struct.pack('<ii', int(round((x - x0) * 100.0)),
                                   int(round((y - y0) * 100.0)))
        return base64.b64encode(bytes(buf)).decode('ascii')

    run = {}
    rj = os.path.join(a.output_dir, '..', '_run.json')
    if os.path.exists(rj):
        run = json.load(open(rj, encoding='utf-8'))

    n_frames = max(frames) + 1 if frames else 0
    payload = {
        'meta': {
            'run': os.path.basename(os.path.dirname(os.path.abspath(a.output_dir))),
            'events': os.path.basename(events),
            'step_s': a.step,
            'frames': n_frames,
            'vehicles_drawn': kept,
            'vehicles_seen': seen,
            'keep_every': a.keep_every,
            'bbox': [x0, y0, x1, y1],
            'origin': [x0, y0],
            'units': 'cm_from_origin',
            'basemap': bool(base),
            'sample_fraction': run.get('sample_fraction'),
            'iterations': run.get('iterations'),
            'scenario': run.get('scenario'),
            'day': run.get('day'),
            'note': 'DIAGNOSTIC, not a result. Nothing in this repo is a result '
                    'until a scenario has been run and reported as one.',
        },
        'net': net,
        'road': [packframe(frames.get(fr, []), 0) for fr in range(n_frames)],
        'transit': [packframe(frames.get(fr, []), 1) for fr in range(n_frames)],
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8') as w:
        json.dump(payload, w, separators=(',', ':'))
    print('wrote %s  (%.1f MiB, %d frames)'
          % (a.out, os.path.getsize(a.out) / 2**20, n_frames), flush=True)


if __name__ == '__main__':
    main()
