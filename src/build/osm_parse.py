#!/usr/bin/env python
"""Streaming OSM XML parser -> tidy layers.

Deliberately dependency-light (lxml only) so the pipeline reproduces anywhere
without a GDAL/GEOS toolchain.
"""
import math
from lxml import etree


def parse(path):
    """Yield tuples:
        ('node', id, lat, lon, tags)
        ('way',  id, [node_refs], tags)
        ('rel',  id, [(type, ref, role)], tags)
    """
    ctx = etree.iterparse(path, events=('end',), tag=('node', 'way', 'relation'))
    for _, el in ctx:
        tags = {t.get('k'): t.get('v') for t in el.findall('tag')}
        if el.tag == 'node':
            yield ('node', el.get('id'), float(el.get('lat')), float(el.get('lon')), tags)
        elif el.tag == 'way':
            yield ('way', el.get('id'), [n.get('ref') for n in el.findall('nd')], tags)
        else:
            yield ('rel', el.get('id'),
                   [(m.get('type'), m.get('ref'), m.get('role')) for m in el.findall('member')],
                   tags)
        el.clear()
        while el.getprevious() is not None:
            del el.getparent()[0]


def haversine(a, b):
    """Great-circle metres between (lat, lon) pairs."""
    R = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    dp = p2 - p1
    return 2 * R * math.asin(math.sqrt(
        math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))


def way_len(refs, idx):
    pts = [idx[r] for r in refs if r in idx]
    return sum(haversine(a, b) for a, b in zip(pts, pts[1:])), pts


def centroid(pts):
    if not pts:
        return (None, None)
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def fnum(v, d=None):
    """First numeric token of an OSM value ('50 mph', '2;3' -> 50, 2)."""
    if v is None:
        return d
    try:
        return float(str(v).split(';')[0].split()[0].replace('m', ''))
    except Exception:
        return d
