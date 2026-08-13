#!/usr/bin/env python
"""Split an Overpass bbox into tiles, and merge the responses back into one file.

The corrected study extent (issue #32) is 2.02x the rectangle it replaced, and a
single Overpass query over it returns **504 Gateway Timeout** - measured, twice,
on the roads layer. Each layer is therefore fetched over a grid of tiles and
merged.

Merging de-duplicates by (element type, id), because Overpass returns a **whole**
way when any part of it matches a bbox, so a way crossing a tile boundary arrives
in both tiles. Without the de-duplication the merged file would declare the same
node twice and every downstream parser would count it twice.

Streaming rather than parsing: these files run to hundreds of megabytes and the
only structure that matters here is where one element ends and the next begins.
"""
import re

#: `<node id="123" ...>` / `<way id="...">` / `<relation id="...">`
ELEM_RE = re.compile(br'<(node|way|relation)\s[^>]*?id="(\d+)"')


def tiles(bbox, max_deg):
    """Split S,W,N,E into tiles no larger than `max_deg` on a side.

    Deterministic: the count follows from the extent and the tiles come out in a
    fixed order, so two harvests of the same extent issue the same queries in
    the same sequence.
    """
    import math
    s, w, n, e = bbox
    ny = max(1, int(math.ceil((n - s) / float(max_deg))))
    nx = max(1, int(math.ceil((e - w) / float(max_deg))))
    dy, dx = (n - s) / ny, (e - w) / nx
    out = []
    for i in range(ny):
        for j in range(nx):
            out.append((round(s + i * dy, 6), round(w + j * dx, 6),
                        round(s + (i + 1) * dy, 6), round(w + (j + 1) * dx, 6)))
    return out


def _element_end(block, start, kind):
    """Index just past the element beginning at `start`, or -1."""
    self_close = block.find(b'/>', start)
    long_close = block.find(b'</' + kind + b'>', start)
    if long_close != -1 and (self_close == -1 or long_close < self_close):
        return long_close + len(kind) + 3
    if self_close != -1:
        return self_close + 2
    return -1


def merge(parts, out_path):
    """Write the union of `parts` to `out_path`. Returns (kept, duplicates)."""
    seen = set()
    kept = dropped = 0
    with open(out_path, 'wb') as out:
        out.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        out.write(b'<osm version="0.6" generator="newcastle-lr-sim tiled overpass">\n')
        for part in parts:
            with open(part, 'rb') as f:
                data = f.read()
            pos = 0
            for m in ELEM_RE.finditer(data):
                start = m.start()
                if start < pos:
                    continue                      # inside an element already written
                kind, eid = m.group(1), m.group(2)
                end = _element_end(data, start, kind)
                if end == -1:
                    continue
                pos = end
                key = (kind, eid)
                if key in seen:
                    dropped += 1
                    continue
                seen.add(key)
                out.write(data[start:end])
                out.write(b'\n')
                kept += 1
        out.write(b'</osm>\n')
    return kept, dropped
