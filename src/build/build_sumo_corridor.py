#!/usr/bin/env python
"""Build the SUMO corridor network with netconvert, one net per E1 road variant.

MATSim carries the regional demand model; SUMO carries the corridor, where lane
take, banned turns, kerbside use and signal timing decide the car-delay side of
the B3 net-arrivals test. This script produces that corridor.

    1. clip the OSM extracts to the corridor bounding box (roads + railways for
       the tram alignment + signals for the turn-restriction relations);
    2. netconvert -> plain XML (nodes / edges / connections / traffic lights),
       in geo coordinates so the A2 signal inventory can be matched by position;
    3. per road variant, patch the plain edge file with the lane take and the
       kerbside state from `A1_road_variant_patches.csv`, attach the traffic
       light programs derived from `A2_signal_control_corridor.csv`, and run
       netconvert again to emit `corridor.net.xml`.

Left-hand traffic is set explicitly (`--lefthand`): with it off, netconvert
builds every intersection mirrored and the turn conflicts - the thing this
corridor exists to measure - come out wrong.

What is observed and what is not
--------------------------------
Lane counts, speed limits and turn restrictions come from OSM (89.7%, 97.4% and
16 restrictions within 80 m respectively - see `_corridor_attributes_report.json`).
Signal *phase structure* is netconvert's geometric guess and is labelled as such.
Signal *timings* are the A2 assumed values: 110 s cycle (100 s without the tram),
four phases split 45|15|30|10, 8 s pedestrian clearance, swept 80-140 s. No SCATS
data was obtained; nothing here should be read as measured phasing.

Outputs
-------
    networks/sumo/<road_variant_ref>/corridor.net.xml
    networks/sumo/<road_variant_ref>/tls_<signal_variant_ref>.add.xml
    networks/sumo/_sumo_build_report.json
"""
import os
import re
import sys
import csv
import json
import time
import math
import argparse
import subprocess
import collections
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'setup'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bootstrap_toolchain as tc      # noqa: E402
from osm_parse import parse, haversine  # noqa: E402
import registry                         # noqa: E402

# Every value below comes from config/registry/, not from a literal in this
# file. The netconvert options that are MODELLING CHOICES - left-hand traffic,
# the signal controller type, junction joining, turnarounds, crossings - are
# separate registry fields rather than entries in a flag list, so a choice
# cannot hide inside one. See DECISIONS.md 15.
CFG = registry.load()

OUT = 'networks/sumo'
WORK = os.path.join(OUT, '_work')
OSM_INPUTS = ['networks/osm/newcastle_roads.osm',
              'networks/osm/newcastle_railways.osm',
              'networks/osm/newcastle_signals.osm']
CORRIDOR_EDGES = 'data/processed/network/A1_corridor_road_edges.csv'
ROAD_EDGES = 'data/processed/network/A1_road_edges.csv'
PATCHES = 'data/processed/network/A1_road_variant_patches.csv'
SIGNALS = 'data/processed/corridor/A2_signal_control_corridor.csv'
RESTRICTIONS = 'data/processed/network/A2_turn_restrictions_resolved.csv'
E1_ROAD_VARIANTS = 'scenarios/E1_road_variants.csv'
E1_SCENARIOS = 'scenarios/E1_scenarios.csv'
PARKING = 'data/processed/network/A5_parking_osm.csv'

SEED = CFG.get('RUN.sumo.seed')
BBOX_MARGIN_M = CFG.get('RUN.sumo.bbox_margin_m')

# EPSG:28356's projection. Stated as proj4 rather than an EPSG code because
# netconvert takes a proj4 definition; the datum label is the repo's (see
# DECISIONS.md 3.6 on the GDA94/GDA2020 naming).
PROJ = CFG.get('RUN.sumo.projection')

# Which signal variant belongs to which road variant, read off E1_scenarios.csv
# at run time; this is only the fallback ordering for reporting.
SIGNAL_VARIANT_ORDER = ['S2_base', 'S2b_full_tsp', 'S0_no_tram', 'S2c_reserved_alignment']

# Junction-matching radius. A2 clusters OSM approach nodes within 45 m into one
# intersection; netconvert's --junctions.join then merges approaches into a single
# junction whose centroid can sit further from the A2 cluster centre than either
# radius alone. 60 m is the corridor buffer used everywhere else in this build,
# and every match is reported with its distance so the pairing stays auditable.
JUNCTION_MATCH_M = CFG.get('A.signals.junction_match_m')

# Shortest green a retimed phase may be given, so a junction with many phases
# cannot be squeezed below a movable interval.
MIN_GREEN_S = CFG.get('A.signals.min_green_s')


def log(msg):
    print('%s  %s' % (time.strftime('%H:%M:%S'), msg), flush=True)


def netconvert(args, tag):
    _j, _jar, nc, sumo_home = tc.require()
    env = dict(os.environ, SUMO_HOME=os.path.abspath(sumo_home))
    cmd = [nc] + args + ['--seed', str(SEED), '--no-warnings', 'false']
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    os.makedirs(os.path.join(WORK, 'logs'), exist_ok=True)
    with open(os.path.join(WORK, 'logs', tag + '.log'), 'w',
              encoding='utf-8', newline='\n') as f:
        f.write(' '.join(cmd) + '\n\n')
        f.write(p.stdout or '')
        f.write('\n---- stderr ----\n')
        f.write(p.stderr or '')
    if p.returncode != 0:
        tail = '\n'.join((p.stderr or p.stdout or '').strip().splitlines()[-20:])
        raise SystemExit('netconvert failed (%s, exit %d)\n%s' % (tag, p.returncode, tail))
    return time.time() - t0


# ---------------------------------------------------------------------------
# 1. clip the OSM extracts to the corridor
# ---------------------------------------------------------------------------
def corridor_bbox():
    """Bounding box of every corridor and parallel-route edge, plus a margin.

    Taken from A1_road_edges.csv endpoints rather than re-read from OSM, so the
    SUMO extent is defined by the same corridor classification the MATSim patches
    and the check suite use.
    """
    want = {r['edge_id'] for r in csv.DictReader(open(CORRIDOR_EDGES, encoding='utf-8'))}
    lat, lon = [], []
    for r in csv.DictReader(open(ROAD_EDGES, encoding='utf-8')):
        if r['edge_id'] in want:
            lat += [float(r['start_lat']), float(r['end_lat'])]
            lon += [float(r['start_lon']), float(r['end_lon'])]
    dlat = BBOX_MARGIN_M / 110540.0
    dlon = BBOX_MARGIN_M / (111320.0 * math.cos(math.radians(sum(lat) / len(lat))))
    return (min(lat) - dlat, min(lon) - dlon, max(lat) + dlat, max(lon) + dlon)


def clip_osm(bbox, dest):
    """Write the corridor sub-extract: nodes in the box, the ways that touch it,
    every node those ways need, and the restriction relations among them."""
    if os.path.exists(dest):
        log('   corridor OSM already present (%.1f MB)' % (os.path.getsize(dest) / 1e6))
        return dest
    s, w, n, e = bbox
    coords, way_refs, way_tags, rels = {}, {}, {}, []
    for src in OSM_INPUTS:
        for rec in parse(src):
            if rec[0] == 'node':
                coords[rec[1]] = (rec[2], rec[3], rec[4])
            elif rec[0] == 'way':
                if rec[1] not in way_refs:
                    way_refs[rec[1]] = rec[2]
                    way_tags[rec[1]] = rec[3]
            elif rec[0] == 'rel' and rec[3].get('type') == 'restriction':
                rels.append(rec)

    def inside(nid):
        c = coords.get(nid)
        return c is not None and s <= c[0] <= n and w <= c[1] <= e

    keep_ways = [wid for wid, refs in way_refs.items() if any(inside(r) for r in refs)]
    keep_ways.sort(key=lambda x: int(x))
    keep_nodes = set()
    for wid in keep_ways:
        keep_nodes.update(way_refs[wid])
    # standalone nodes carrying signals/crossings inside the box
    for nid, c in coords.items():
        if inside(nid) and c[2]:
            keep_nodes.add(nid)
    keep_way_set = set(keep_ways)
    keep_rels = [r for r in rels
                 if all(ref in keep_way_set for t, ref, role in r[2] if t == 'way')
                 and any(t == 'way' for t, ref, role in r[2])]

    def esc(v):
        return (v.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                .replace('"', '&quot;'))

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, 'w', encoding='utf-8', newline='\n') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<osm version="0.6" generator="build_sumo_corridor.py">\n')
        for nid in sorted(keep_nodes, key=lambda x: int(x)):
            c = coords.get(nid)
            if c is None:
                continue
            tags = c[2]
            if tags:
                f.write('  <node id="%s" lat="%.7f" lon="%.7f">\n' % (nid, c[0], c[1]))
                for k, v in sorted(tags.items()):
                    f.write('    <tag k="%s" v="%s"/>\n' % (esc(k), esc(v)))
                f.write('  </node>\n')
            else:
                f.write('  <node id="%s" lat="%.7f" lon="%.7f"/>\n' % (nid, c[0], c[1]))
        for wid in keep_ways:
            f.write('  <way id="%s">\n' % wid)
            for r in way_refs[wid]:
                if r in keep_nodes and r in coords:
                    f.write('    <nd ref="%s"/>\n' % r)
            for k, v in sorted(way_tags[wid].items()):
                f.write('    <tag k="%s" v="%s"/>\n' % (esc(k), esc(v)))
            f.write('  </way>\n')
        for _kind, rid, members, tags in sorted(keep_rels, key=lambda r: int(r[1])):
            f.write('  <relation id="%s">\n' % rid)
            for t, ref, role in members:
                f.write('    <member type="%s" ref="%s" role="%s"/>\n' % (t, ref, role))
            for k, v in sorted(tags.items()):
                f.write('    <tag k="%s" v="%s"/>\n' % (esc(k), esc(v)))
            f.write('  </relation>\n')
        f.write('</osm>\n')
    log('   clipped -> %s  %d nodes, %d ways, %d restriction relations'
        % (dest, len(keep_nodes), len(keep_ways), len(keep_rels)))
    return dest


# ---------------------------------------------------------------------------
# 2. netconvert -> plain XML
# ---------------------------------------------------------------------------
def _plain_opts():
    """netconvert options, assembled from the registry in netconvert's own order.

    Every option that is a MODELLING CHOICE is a named registry field rather than
    an entry in a flag list, so a choice cannot hide inside one. The order below
    reproduces the list this function replaced exactly, so the refactor is inert
    and the corridor nets rebuild byte-identically.

    `--osm.crossings` is absent because it segfaults netconvert 1.27.1 on this
    extract (DECISIONS.md 3.6) - a tool defect, not a judgement that pedestrians
    do not matter, and the reason pedestrian delay must not be modelled in SUMO.
    """
    def flag(name, key):
        return [name, 'true' if CFG.get(key) else 'false']

    opts = []
    if CFG.get('RUN.sumo.lefthand'):
        opts += ['--lefthand']
    opts += list(CFG.get('RUN.sumo.netconvert_options'))
    opts += flag('--junctions.join', 'RUN.sumo.junctions_join')
    opts += flag('--tls.guess-signals', 'RUN.sumo.tls_guess_signals')
    opts += flag('--tls.join', 'RUN.sumo.tls_join')
    opts += ['--tls.default-type', CFG.get('RUN.sumo.tls_default_type')]
    opts += flag('--no-turnarounds', 'RUN.sumo.no_turnarounds')
    opts += ['--default.spreadtype', CFG.get('RUN.sumo.spreadtype')]
    if CFG.get('RUN.sumo.crossings_enabled'):
        opts += ['--osm.crossings', 'true']
    return opts


PLAIN_OPTS = _plain_opts()


def build_plain(osm, prefix):
    args = ['--osm-files', osm, '--proj', PROJ, '--proj.plain-geo', 'true',
            '--plain-output-prefix', prefix, '--plain-output.lanes', 'true']
    dt = netconvert(args + PLAIN_OPTS, 'plain')
    log('   plain XML in %.0f s: %s' % (dt, ', '.join(
        sorted(os.path.basename(p) for p in _plain_files(prefix)))))
    return prefix


def _plain_files(prefix):
    return [prefix + s for s in ('.nod.xml', '.edg.xml', '.con.xml', '.tll.xml', '.typ.xml')
            if os.path.exists(prefix + s)]


# ---------------------------------------------------------------------------
# 3. per-variant patching
# ---------------------------------------------------------------------------
def load_patches():
    by = collections.defaultdict(dict)
    for p in csv.DictReader(open(PATCHES, encoding='utf-8')):
        by[p['road_variant_ref']][p['edge_id'][1:]] = p
    return by


def osm_way_of_edge(edge_id):
    """SUMO names an OSM-derived edge `<way>#<n>` or `-<way>#<n>`."""
    m = re.match(r'^-?(\d+)(?:#\d+)?$', edge_id)
    return m.group(1) if m else ''


def patch_edges(src_edg, dest_edg, patch):
    """Apply the lane take and record kerbside use on the plain edge file."""
    tree = ET.parse(src_edg)
    root = tree.getroot()
    applied = collections.Counter()
    for edge in root.findall('edge'):
        way = osm_way_of_edge(edge.get('id', ''))
        p = patch.get(way)
        if not p:
            continue
        changed = p['fields_changed'].split(';')
        if 'num_lanes_per_dir' in changed and p['field_num_lanes_per_dir_to']:
            new = int(round(float(p['field_num_lanes_per_dir_to'])))
            old = edge.get('numLanes')
            if old is None or int(old) != new:
                edge.set('numLanes', str(new))
                applied['numLanes'] += 1
                # a lane list written by --plain-output.lanes would contradict the
                # new count; drop it and let netconvert rebuild the lanes
                for lane in list(edge.findall('lane')):
                    edge.remove(lane)
        if 'kerbside_use' in changed and p['field_kerbside_use_to']:
            ET.SubElement(edge, 'param', {'key': 'kerbsideUse',
                                          'value': p['field_kerbside_use_to']})
            applied['kerbsideUse'] += 1
    _indent(root)
    tree.write(dest_edg, encoding='UTF-8', xml_declaration=True)
    return dict(applied)


def patch_connections(src_con, dest_con, drop_ways):
    """Drop the plain connections that touch a patched way, keep the rest.

    Two reasons, and they coincide on the corridor:

    * a connection in the plain file names a lane index, so once a variant
      changes `numLanes` the stored connections no longer resolve and netconvert
      quits on error. Removing them lets it rebuild those junctions from geometry.
    * netconvert encodes an OSM turn restriction by *withholding* the connection.
      So for the no-tram network, which E1 gives 'no banned turns', removing the
      corridor connections is precisely how the banned movements come back.

    Everything outside the patched ways keeps its imported connections, including
    its turn restrictions.
    """
    tree = ET.parse(src_con)
    root = tree.getroot()
    removed = 0
    for c in list(root):
        if c.tag != 'connection':
            continue
        if (osm_way_of_edge(c.get('from', '')) in drop_ways
                or osm_way_of_edge(c.get('to', '')) in drop_ways):
            root.remove(c)
            removed += 1
    _indent(root)
    tree.write(dest_con, encoding='UTF-8', xml_declaration=True)
    return removed


def _indent(el, level=0):
    pad = '\n' + '    ' * level
    if len(el):
        if not (el.text or '').strip():
            el.text = pad + '    '
        for child in el:
            _indent(child, level + 1)
        if not (el.tail or '').strip():
            el.tail = pad
        if not (el[-1].tail or '').strip():
            el[-1].tail = pad
    elif level and not (el.tail or '').strip():
        el.tail = pad


# ---------------------------------------------------------------------------
# traffic lights: netconvert guesses the structure, A2 supplies the timings
# ---------------------------------------------------------------------------
def read_signal_variant(ref):
    rows = [r for r in csv.DictReader(open(SIGNALS, encoding='utf-8'))
            if r['scenario_variant_ref'] == ref]
    return rows


def junction_positions(nod_file):
    """Traffic-light junctions from the plain node file, in geo coordinates."""
    root = ET.parse(nod_file).getroot()
    out = {}
    for n in root.findall('node'):
        if 'traffic_light' in (n.get('type') or ''):
            out[n.get('id')] = (float(n.get('y')), float(n.get('x')))  # plain-geo: x=lon
    return out


def programmed_junctions(net_path, junctions):
    """Restrict the candidate junctions to those the built net actually gives a
    traffic-light program. Matching an A2 intersection onto a junction with no
    program would report a match that could never be retimed."""
    root = ET.parse(net_path).getroot()
    have = {tl.get('id') for tl in root.findall('tlLogic')}
    return {k: v for k, v in junctions.items() if k in have}


def match_junctions(sig_rows, junctions):
    """Map each A2 intersection onto its nearest traffic-light junction."""
    used, pairs, unmatched = set(), [], []
    for s in sorted(sig_rows, key=lambda r: r['intersection_id']):
        ll = (float(s['lat']), float(s['lon']))
        best, bd = None, 1e9
        for jid, jll in sorted(junctions.items()):
            if jid in used:
                continue
            d = haversine(ll, jll)
            if d < bd:
                best, bd = jid, d
        if best is not None and bd <= JUNCTION_MATCH_M:
            used.add(best)
            pairs.append((s, best, round(bd, 1)))
        else:
            unmatched.append((s['intersection_id'], round(bd, 1) if best else None))
    return pairs, unmatched


def match_report(pairs, unmatched):
    return dict(matched=[dict(intersection_id=s['intersection_id'], junction=j,
                              distance_m=d) for s, j, d in pairs],
                unmatched=[dict(intersection_id=i, nearest_junction_m=d)
                           for i, d in unmatched])


def retime_tls(net_path, dest_add, pairs):
    """Retime the built network's own traffic-light programs onto the A2 values.

    The programs are read back out of `corridor.net.xml` rather than out of the
    plain `.tll.xml`, because the link indices a phase state string addresses are
    only settled once the lane take has been applied. Reading them from the built
    net means every state string is the right length for the net it belongs to.

    netconvert derives the phase *structure* from junction geometry. That
    structure is kept; only the durations are replaced, by distributing the A2
    phase split across the green phases in order and giving each intervening
    yellow/all-red phase the A2 pedestrian clearance. The result is a program
    whose shape is geometric and whose timing is the assumed SCATS proxy - the
    two are never blended, and both are labelled in the output.
    """
    root = ET.parse(net_path).getroot()
    by_junction = {j: s for s, j, _d in pairs}
    add = ET.Element('additional')
    retimed, skipped = 0, 0
    for src in root.findall('tlLogic'):
        s = by_junction.get(src.get('id'))
        if s is None:
            skipped += 1
            continue
        tl = ET.fromstring(ET.tostring(src))
        cycle = float(s['cycle_time_s'])
        clearance = float(s['ped_clearance_s'])
        split = [float(x) for x in s['phase_split_pct'].split('|')]
        tsp = s['tsp_enabled'] == '1'
        extension = float(s['tsp_max_extension_s'] or 0)
        phases = tl.findall('phase')
        greens = [p for p in phases if 'G' in (p.get('state') or '')]
        others = [p for p in phases if p not in greens]
        if not greens:
            skipped += 1
            continue
        inter = clearance * len(others)
        usable = max(cycle - inter, len(greens) * MIN_GREEN_S)
        # The A2 split has four entries. A junction netconvert gave a different
        # number of green phases takes the split cyclically, so every green phase
        # gets a weight - leaving any of them on its guessed duration is what made
        # the cycle overshoot the A2 value.
        weights = [split[i % len(split)] for i in range(len(greens))]
        tot = sum(weights)
        for p, w in zip(greens, weights):
            g = max(MIN_GREEN_S, usable * w / tot)
            p.set('duration', '%.0f' % g)
            if tsp:
                # transit signal priority is a green *extension*, so it shows up
                # as headroom on the actuated phase, not as a longer fixed green
                p.set('minDur', '%.0f' % g)
                p.set('maxDur', '%.0f' % (g + extension))
            else:
                p.set('minDur', '%.0f' % g)
                p.set('maxDur', '%.0f' % g)
        for p in others:
            p.set('duration', '%.0f' % clearance)
            p.attrib.pop('minDur', None)
            p.attrib.pop('maxDur', None)
        realised = sum(float(p.get('duration')) for p in phases)
        ET.SubElement(tl, 'param', {'key': 'realised_cycle_s', 'value': '%.0f' % realised})
        tl.set('programID', 'A2_%s' % s['scenario_variant_ref'])
        tl.set('type', 'actuated' if s['control_type'] == 'adaptive' else 'static')
        tl.set('offset', str(int(float(s['offset_s']))))
        ET.SubElement(tl, 'param', {'key': 'a2_intersection_id',
                                    'value': s['intersection_id']})
        ET.SubElement(tl, 'param', {'key': 'cycle_time_s', 'value': s['cycle_time_s']})
        ET.SubElement(tl, 'param', {'key': 'cycle_time_sweep',
                                    'value': '%s-%s' % (s['cycle_time_sweep_low'],
                                                        s['cycle_time_sweep_high'])})
        ET.SubElement(tl, 'param', {'key': 'tsp_enabled', 'value': s['tsp_enabled']})
        ET.SubElement(tl, 'param', {'key': 'tsp_max_extension_s',
                                    'value': s['tsp_max_extension_s']})
        ET.SubElement(tl, 'param', {'key': 'mean_delay_to_tram_s',
                                    'value': s['mean_delay_to_tram_s']})
        ET.SubElement(tl, 'param', {'key': 'timing_source', 'value': 'assumed (A2 proxy)'})
        ET.SubElement(tl, 'param', {'key': 'phase_structure_source',
                                    'value': 'netconvert geometric guess'})
        add.append(tl)
        retimed += 1
    _indent(add)
    ET.ElementTree(add).write(dest_add, encoding='UTF-8', xml_declaration=True)
    return retimed, skipped


# ---------------------------------------------------------------------------
def signal_variant_for_road_variant():
    """road_variant_ref -> the signal variants E1 pairs it with."""
    out = collections.defaultdict(set)
    for r in csv.DictReader(open(E1_SCENARIOS, encoding='utf-8')):
        out[r['road_variant_ref']].add(r['signal_variant_ref'])
    return {k: sorted(v, key=lambda x: (SIGNAL_VARIANT_ORDER.index(x)
                                        if x in SIGNAL_VARIANT_ORDER else 99))
            for k, v in out.items()}


def corridor_parking_count(bbox):
    """On-street parking facilities inside the corridor box - the observed
    cross-check against the assumed '210 spaces removed' in DECISIONS 6."""
    s, w, n, e = bbox
    fac, spaces = 0, 0
    if not os.path.exists(PARKING):
        return None
    for r in csv.DictReader(open(PARKING, encoding='utf-8')):
        try:
            lat, lon = float(r['lat']), float(r['lon'])
        except ValueError:
            continue
        if s <= lat <= n and w <= lon <= e and r['type'] == 'onstreet':
            fac += 1
            if r['capacity_spaces']:
                spaces += int(r['capacity_spaces'])
    return dict(onstreet_facilities=fac, onstreet_spaces_with_capacity=spaces)


def build():
    tc.require()
    os.makedirs(WORK, exist_ok=True)
    bbox = corridor_bbox()
    log('corridor bbox %.5f,%.5f .. %.5f,%.5f' % bbox)
    osm = clip_osm(bbox, os.path.join(WORK, 'corridor.osm'))
    prefix = build_plain(osm, os.path.join(WORK, 'corridor'))

    junctions = junction_positions(prefix + '.nod.xml')
    log('   %d traffic-light junctions in the corridor net' % len(junctions))

    patches = load_patches()
    pairing = signal_variant_for_road_variant()
    variants = list(csv.DictReader(open(E1_ROAD_VARIANTS, encoding='utf-8')))
    restrictions = [r for r in csv.DictReader(open(RESTRICTIONS, encoding='utf-8'))
                    if r['corridor_flag'] == '1']
    corridor_rows = list(csv.DictReader(open(CORRIDOR_EDGES, encoding='utf-8')))

    report = dict(bbox=dict(zip(('south', 'west', 'north', 'east'),
                                [round(x, 6) for x in bbox])),
                  proj=PROJ, lefthand=CFG.get('RUN.sumo.lefthand'), seed=SEED,
                  tl_junctions_in_net=len(junctions),
                  observed_corridor_restrictions=len(restrictions),
                  corridor_parking=corridor_parking_count(bbox),
                  road_variants={})
    timings = {}

    for v in variants:
        ref = v['road_variant_ref']
        out_dir = os.path.join(OUT, ref)
        os.makedirs(out_dir, exist_ok=True)
        pat = patches.get(ref, {})
        edg = os.path.join(WORK, '%s.edg.xml' % ref)
        applied = patch_edges(prefix + '.edg.xml', edg, pat)

        # Lane-patched ways always lose their stored connections; the no-tram
        # variant, which E1 gives 'no banned turns', loses them across every
        # corridor way so the restricted movements are rebuilt unrestricted.
        drop_restrictions = v['banned_turn_movements'] == '0'
        drop_ways = set(pat)
        if drop_restrictions:
            drop_ways |= {r['edge_id'][1:] for r in corridor_rows
                          if 'corridor' in r['corridor_class']}
        con = os.path.join(WORK, '%s.con.xml' % ref)
        n_dropped = patch_connections(prefix + '.con.xml', con, drop_ways)

        args = ['--node-files', prefix + '.nod.xml',
                '--edge-files', edg,
                '--connection-files', con,
                '--type-files', prefix + '.typ.xml',
                '--output-file', os.path.join(out_dir, 'corridor.net.xml'),
                '--proj', PROJ,
                '--lefthand', '--no-turnarounds', 'true',
                '--tls.default-type', 'actuated',
                '--default.spreadtype', 'roadCenter']
        dt = netconvert(args, 'net_%s' % ref)

        net_path = os.path.join(out_dir, 'corridor.net.xml')
        strip_generated_comment(net_path)
        stats = net_stats(net_path)

        # traffic lights come after the net: the phase state strings a program
        # writes are indexed against the connections of *this* variant's net.
        tls_report = {}
        tl_junctions = programmed_junctions(net_path, junctions)
        for sref in pairing.get(ref, ['S2_base']):
            sig_rows = read_signal_variant(sref)
            pairs, unmatched = match_junctions(sig_rows, tl_junctions)
            add_path = os.path.join(out_dir, 'tls_%s.add.xml' % sref)
            retimed, skipped = retime_tls(net_path, add_path, pairs)
            tls_report[sref] = dict(a2_intersections=len(sig_rows),
                                    matched_junctions=len(pairs),
                                    pairing=match_report(pairs, unmatched),
                                    programs_retimed=retimed,
                                    programs_left_as_guessed=skipped,
                                    realised_cycle_s=realised_cycles(add_path),
                                    cycle_time_s=(sig_rows[0]['cycle_time_s']
                                                  if sig_rows else None),
                                    tsp_enabled=(sig_rows[0]['tsp_enabled']
                                                 if sig_rows else None))
        report['road_variants'][ref] = dict(
            patch_rows=len(pat), edges_patched=applied,
            banned_turns_dropped=drop_restrictions,
            plain_connections_dropped=n_dropped,
            e1_banned_turn_movements=int(v['banned_turn_movements']),
            e1_lanes_per_direction=float(v['hunter_st_lanes_per_direction']),
            e1_kerbside_parking_removed=v['kerbside_parking_removed'] == '1',
            signal_variants=tls_report, **stats)
        # Wall-clock timing is a property of the machine, not of the model, and a
        # committed artefact that carries one cannot be regenerated to the same
        # bytes - which is the reproducibility gate, not an aspiration. Timings go
        # to the gitignored work directory instead.
        timings[ref] = round(dt, 1)
        log('   %-42s %4d patches -> %s | %d edges, %d junctions, %d tls'
            % (ref, len(pat), applied or 'no edge change',
               stats['edges'], stats['junctions'], stats['tls_programs']))

    path = os.path.join(OUT, '_sumo_build_report.json')
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write('\n')
    log('report -> %s' % path)

    tpath = os.path.join(WORK, 'netconvert_timings.json')
    with open(tpath, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(timings, f, indent=2, sort_keys=True)
        f.write('\n')
    log('timings -> %s (not committed: wall clock is a property of the machine, '
        'not of the model)' % tpath)


GENERATED_RE = re.compile(r'<!--.*?-->', re.S)


def strip_generated_comment(path):
    """netconvert stamps the run date and the full command line into a leading
    comment. Both are wall-clock and path dependent, so they are removed: the
    file must hash the same on a rebuild."""
    with open(path, encoding='utf-8') as f:
        s = f.read()
    head, sep, tail = s.partition('<net ')
    if sep:
        head = GENERATED_RE.sub('', head).replace('\n\n', '\n')
        s = head + sep + tail
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(s)


def realised_cycles(add_path):
    """Cycle length actually written per program - the check that the A2 cycle
    survived the retiming rather than being approximated by it."""
    root = ET.parse(add_path).getroot()
    out = collections.Counter()
    for tl in root.findall('tlLogic'):
        out['%.0f' % sum(float(p.get('duration')) for p in tl.findall('phase'))] += 1
    return dict(out)


def net_stats(path):
    root = ET.parse(path).getroot()
    edges = [e for e in root.findall('edge') if e.get('function') != 'internal']
    junctions = [j for j in root.findall('junction') if j.get('type') != 'internal']
    lanes = sum(len(e.findall('lane')) for e in edges)
    length = 0.0
    for e in edges:
        for ln in e.findall('lane'):
            length += float(ln.get('length', 0))
    return dict(edges=len(edges), lanes=lanes, junctions=len(junctions),
                lane_km=round(length / 1000, 1),
                tls_programs=len(root.findall('tlLogic')),
                connections=len(root.findall('connection')),
                bytes=os.path.getsize(path))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--rebuild-clip', action='store_true',
                    help='re-clip the corridor OSM even if it exists')
    a = ap.parse_args()
    if a.rebuild_clip:
        for p in (os.path.join(WORK, 'corridor.osm'),):
            if os.path.exists(p):
                os.remove(p)
    build()
