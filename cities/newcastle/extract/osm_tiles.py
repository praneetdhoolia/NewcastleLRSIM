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
    """Index just past the element beginning at `start`, or -1.

    The opening tag is resolved FIRST, and only then the closing tag. Searching
    for the earlier of `/>` and `</way>` looks equivalent and is not: a way with
    children contains `<nd ref="..."/>`, whose `/>` comes long before `</way>`,
    so that version cut every way off at its first node reference. It produced
    files that parsed, looked plausible and were 40% smaller than the originals
    on a 2x larger extent - a corrupt network that would have rebuilt without
    complaint.
    """
    gt = block.find(b'>', start)
    if gt == -1:
        return -1
    if block[gt - 1:gt] == b'/':          # <node ... /> - opening tag IS the element
        return gt + 1
    close = block.find(b'</' + kind + b'>', gt)
    if close == -1:
        return -1
    return close + len(kind) + 3


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


def verify(path):
    """Refuse a merged file whose ways lost their node references.

    The truncation bug above was silent: the file was well formed, every way
    was present, and only the CHILDREN were missing. Nothing downstream would
    have complained - build_network_layers would simply have produced a network
    with no geometry. So the merge is checked here rather than trusted, and the
    check is on the invariant that actually broke.
    """
    ways = with_children = 0
    with open(path, 'rb') as f:
        data = f.read()
    for m in re.finditer(br'<way\s[^>]*?id="(\d+)"', data):
        ways += 1
        end = _element_end(data, m.start(), b'way')
        if end != -1 and b'<nd ' in data[m.start():end]:
            with_children += 1
        if ways >= 2000:
            break
    if ways and with_children < ways * 0.9:
        raise SystemExit(
            '%s is CORRUPT: only %d of the first %d ways carry a node reference. '
            'A way without <nd> children has no geometry, and every downstream '
            'build would have accepted it silently.' % (path, with_children, ways))
    return ways, with_children
