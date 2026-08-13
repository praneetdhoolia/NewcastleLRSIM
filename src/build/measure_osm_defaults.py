#!/usr/bin/env python
"""Measure, from the observed OSM tags, the defaults applied where OSM is silent.

`build_network_layers.py` fills an untagged edge from a per-class default, and
those defaults were **assumed** - a class-level convention, not a Newcastle
measurement. That matters more than it looks, because the imputation is not a
rounding error:

    lane_width_m       42,747 of 43,112 road edges   99.2%
    num_lanes          32,499 of 43,112              75.4%
    speed_limit_kmh    23,151 of 43,112              53.7%
    footway width_m    35,074 of 35,653              98.4%

But the complement is real data: 10,613 edges DO carry a `lanes` tag and 19,961
carry `maxspeed`. A default derived from the observed distribution of the same
class in the same city is a measurement; a default typed from convention is a
guess, and P4 deliverable 0b (#23) is about telling those apart.

What this does NOT do is invent coverage. A class with no observation keeps its
assumed value and says so, and `capacity_veh_hr_lane` is not measured at all:
saturation flow is an engineering convention that OSM does not record and this
package has no count data to estimate per class. It stays assumed and swept.

The sweep for each measured default is the observed interquartile range of that
class - an observed spread, not an interval anyone chose. Where a class has too
few observations for an IQR to mean anything, it keeps its assumed value.

Determinism: no sampling; every figure is a quantile over the full tag set.
"""
import os
import sys
import json
import argparse
import collections

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from osm_parse import parse, fnum

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import registry as _registry  # noqa: E402
CFG = _registry.load()

ROADS = 'networks/osm/newcastle_roads.osm'
FOOTWAYS = 'networks/osm/newcastle_footways.osm'
OUT = 'params/C2_osm_defaults.json'

#: A class needs at least this many tagged edges before its observed median
#: replaces the assumed default. Below it the quantiles describe the mapper, not
#: the city. Declared here rather than in the registry because it governs how a
#: MEASUREMENT is taken, not what the model consumes - the outputs it produces
#: are what enter the registry, each with its own observed sweep.
MIN_TAGGED = 30


def _quantiles(values):
    v = np.array(sorted(values), dtype=float)
    return (round(float(np.median(v)), 4),
            round(float(np.percentile(v, 25)), 4),
            round(float(np.percentile(v, 75)), 4))


def _collect(path, tag_getters):
    """Per-highway-class lists of observed tag values."""
    out = {name: collections.defaultdict(list) for name in tag_getters}
    for item in parse(path):
        if item[0] != 'way':
            continue
        _, _wid, refs, t = item
        hw = t.get('highway')
        if not hw or len(refs) < 2:
            continue
        for name, get in tag_getters.items():
            v = get(t)
            if v is not None:
                out[name][hw].append(v)
    return out


def _lanes_per_direction(t):
    """OSM `lanes` counts BOTH directions unless the way is one-way.

    Halving on a two-way road is exactly what build_network_layers.py does when
    it reads the tag, so the measured default is on the same footing as the
    observed value it stands in for.
    """
    v = fnum(t.get('lanes'))
    if v is None or v <= 0:
        return None
    if t.get('oneway') in ('yes', '1', '-1', 'true'):
        return v
    return max(1.0, v / 2.0)


def _maxspeed(t):
    v = fnum(t.get('maxspeed'))
    return v if (v and v > 0) else None


def _width(t):
    v = fnum(t.get('width'))
    return v if (v and v > 0) else None


def _lane_widths(path):
    """Per-lane width, from edges carrying both `width` and `lanes`.

    `lanes` here is the raw tag - the total across both directions - because
    `width` is the total carriageway, so the two divide directly.
    """
    out = []
    for item in parse(path):
        if item[0] != 'way':
            continue
        _, _wid, refs, t = item
        if not t.get('highway') or len(refs) < 2:
            continue
        w = fnum(t.get('width'))
        n = fnum(t.get('lanes'))
        if w and n and w > 0 and n > 0:
            per = w / n
            # A per-lane width outside this range is a mis-tag, not a lane:
            # below 1.5 m nothing drives, above 6 m the tag is a carriageway
            # that was recorded with a lane count for something else.
            if 1.5 <= per <= 6.0:
                out.append(per)
    return out


def measure(assumed, observed, unit, note):
    """One measured default per class, with the assumed value it replaces."""
    out = {}
    for hw, base in sorted(assumed.items()):
        vals = observed.get(hw, [])
        if len(vals) >= MIN_TAGGED:
            med, lo, hi = _quantiles(vals)
            out[hw] = dict(value=med, sweep=[lo, hi], n_tagged=len(vals),
                           assumed_was=base, source='measured')
        else:
            out[hw] = dict(value=base, sweep=None, n_tagged=len(vals),
                           assumed_was=base, source='assumed',
                           reason='fewer than %d tagged edges of this class' % MIN_TAGGED)
    return dict(unit=unit, note=note, by_class=out)


def main():
    print('reading %s ...' % ROADS, flush=True)
    road = _collect(ROADS, dict(lanes=_lanes_per_direction,
                                maxspeed=_maxspeed, width=_width))
    print('reading %s ...' % FOOTWAYS, flush=True)
    foot = _collect(FOOTWAYS, dict(width=_width))

    lanes = measure(CFG.get('A.road.lanes_default'), road['lanes'],
                    'lanes_per_direction',
                    'OSM lanes tag, halved on two-way ways exactly as '
                    'build_network_layers.py halves it when the tag is present')
    speed = measure(CFG.get('A.road.speed_default'), road['maxspeed'],
                    'km_per_hour', 'OSM maxspeed tag')
    width = measure(CFG.get('A.active.footway_width_default'), foot['width'],
                    'metres', 'OSM width tag on the active layer')

    # Lane width had NO registry field at all - build_network_layers.py carried
    # a bare 3.2 - so there is no assumed dict to walk.
    #
    # It cannot be read off the `width` tag. On a road, OSM `width` is the
    # CARRIAGEWAY, both directions together: measured straight it comes out at
    # 6.5 m, which is two lanes, and writing that into a per-lane field would
    # double every carriageway in the model. It is the same class of error as
    # reading a published interchange TIME as a transfer PENALTY (9.32) - the
    # available number looks like the answer and is a different quantity.
    # Per-lane width is therefore derived only where BOTH tags are present.
    per_lane = _lane_widths(ROADS)
    if len(per_lane) >= MIN_TAGGED:
        med, lo, hi = _quantiles(per_lane)
        lane_width = dict(value=med, sweep=[lo, hi], n_tagged=len(per_lane),
                          source='measured',
                          note='OSM width divided by OSM lanes on edges carrying '
                               'BOTH tags. The width tag alone is the carriageway, '
                               'not a lane, and stands at 6.5 m; it stood in for a '
                               'bare 3.2 that was in no registry at all')
    else:
        lane_width = dict(value=None, sweep=None, n_tagged=len(per_lane),
                          source='assumed',
                          note='too few edges carry both width and lanes')

    for name, blk in (('lanes', lanes), ('maxspeed', speed), ('footway width', width)):
        n_meas = sum(1 for v in blk['by_class'].values() if v['source'] == 'measured')
        print('   %-14s %d of %d classes measured' % (name, n_meas, len(blk['by_class'])),
              flush=True)
        for hw, v in sorted(blk['by_class'].items()):
            if v['source'] == 'measured' and v['value'] != v['assumed_was']:
                print('      %-16s %-6s -> %-6s  (n=%d, IQR %s)'
                      % (hw, v['assumed_was'], v['value'], v['n_tagged'], v['sweep']),
                      flush=True)
    print('   lane width     %s m from %d tagged road edges'
          % (lane_width['value'], lane_width['n_tagged']), flush=True)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(dict(min_tagged=MIN_TAGGED, lanes_per_direction=lanes,
                       speed_limit_kmh=speed, footway_width_m=width,
                       road_lane_width_m=lane_width), f, indent=2)
        f.write('\n')
    print('wrote %s' % OUT, flush=True)


if __name__ == '__main__':
    argparse.ArgumentParser().parse_args()
    main()
