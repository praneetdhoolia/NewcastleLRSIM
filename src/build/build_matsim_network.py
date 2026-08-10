#!/usr/bin/env python
"""Convert the OSM extracts and every GTFS feed into a MATSim network + schedules.

Runs pt2matsim 26.6 (see `src/setup/bootstrap_toolchain.py`) in three stages:

  1. merge the road and railway OSM extracts into one multimodal file, since
     pt2matsim reads a single .osm and the P1 extracts are themed;
  2. `Osm2MultimodalNetwork` -> the base MATSim network in EPSG:28356, using the
     capacity and speed defaults recorded in DECISIONS.md 3.2 rather than
     pt2matsim's own, so the MATSim and SUMO corridors share one set of numbers;
  3. `Gtfs2TransitSchedule` + `PublicTransitMapper` for each of the 5 era feeds
     and 10 scenario feeds -> mapped schedules and their networks.

The four E1 road variants are applied as **link-attribute patches** over the one
base network, from `data/processed/network/A1_road_variant_patches.csv`. They are
not four independent conversions: the variants differ only in lane count and
kerbside use on corridor edges, never in topology, so building them as deltas is
what makes 'scenario networks differ only where E1 says they should' a structural
property rather than a diff assertion after the fact.

Determinism: the OSM merge preserves source file order, the configs are written
from the tables in this file, and Java's GZIPOutputStream stamps MTIME=0, so a
rebuilt network hashes identically to the one in data/MANIFEST.csv.

Usage:
    python src/build/build_matsim_network.py                # everything
    python src/build/build_matsim_network.py --stage network
    python src/build/build_matsim_network.py --stage schedules --only S2,base2026
    python src/build/build_matsim_network.py --workers 3
"""
import os
import re
import sys
import csv
import json
import gzip
import time
import hashlib
import shutil
import zipfile
import argparse
import subprocess
import collections
import concurrent.futures as futures

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'setup'))
import bootstrap_toolchain as tc  # noqa: E402

OUT = 'networks/matsim'
WORK = os.path.join(OUT, '_work')
CRS = 'EPSG:28356'
PATCHES = 'data/processed/network/A1_road_variant_patches.csv'
E1_ROAD_VARIANTS = 'scenarios/E1_road_variants.csv'
JAVA_XMX = '-Xmx6g'

# The signals extract is merged for its `type=restriction` relations - the road
# extract carries none, so without it pt2matsim writes no `disallowedNextLinks`
# and every banned turn on the corridor would silently vanish from the network.
OSM_INPUTS = ['networks/osm/newcastle_roads.osm',
              'networks/osm/newcastle_railways.osm',
              'networks/osm/newcastle_signals.osm']

FEEDS = collections.OrderedDict([
    ('base2026', 'schedules/base2026.zip'),
    ('era1_pre2014_reconstructed', 'schedules/era1_pre2014_reconstructed.zip'),
    ('era2_2016_rail_truncated', 'schedules/era2_2016_rail_truncated.zip'),
    ('era3_2018_keolis_interchange', 'schedules/era3_2018_keolis_interchange.zip'),
    ('era4_2019_lr_open', 'schedules/era4_2019_lr_open.zip'),
    ('S0', 'schedules/scenarios/S0.zip'),
    ('S1', 'schedules/scenarios/S1.zip'),
    ('S2', 'schedules/scenarios/S2.zip'),
    ('S2a', 'schedules/scenarios/S2a.zip'),
    ('S2b', 'schedules/scenarios/S2b.zip'),
    ('S2c', 'schedules/scenarios/S2c.zip'),
    ('S3', 'schedules/scenarios/S3.zip'),
    ('S4', 'schedules/scenarios/S4.zip'),
    ('S5', 'schedules/scenarios/S5.zip'),
    ('S6', 'schedules/scenarios/S6.zip'),
])

# All three day types are converted into a single schedule ("all"). The era and
# scenario feeds namespace their trip ids by day type (WEEKDAY./SAT./SUN., see
# DECISIONS.md 11), so a run selects its day type by prefix without needing three
# separate mapped schedules - and the route set that PublicTransitMapper has to
# map is nearly identical across day types anyway.
GTFS_DAY_PARAM = 'all'

# ---------------------------------------------------------------------------
# Way defaults. Capacities are DECISIONS.md 3.2 (Austroads-style, assumed);
# speeds are the NSW class defaults from build_network_layers.py. freespeed is
# m/s. Kept here rather than taken from pt2matsim's own defaults so that the
# MATSim network, the SUMO corridor and A1_road_edges.csv cannot drift apart.
# ---------------------------------------------------------------------------
WAY_DEFAULTS = [
    # osmKey,   osmValue,        lanes, freespeed_kmh, laneCapacity, oneway, modes
    ('highway', 'motorway',        2, 100, 2000, 'true',  'car'),
    ('highway', 'motorway_link',   1,  60, 1500, 'true',  'car'),
    ('highway', 'trunk',           2,  80, 1800, 'false', 'car'),
    ('highway', 'trunk_link',      1,  60, 1400, 'false', 'car'),
    ('highway', 'primary',         2,  60, 1600, 'false', 'car'),
    ('highway', 'primary_link',    1,  50, 1200, 'false', 'car'),
    ('highway', 'secondary',       1,  60, 1400, 'false', 'car'),
    ('highway', 'secondary_link',  1,  50, 1100, 'false', 'car'),
    ('highway', 'tertiary',        1,  50, 1200, 'false', 'car'),
    ('highway', 'tertiary_link',   1,  40, 1000, 'false', 'car'),
    ('highway', 'unclassified',    1,  50, 1000, 'false', 'car'),
    ('highway', 'residential',     1,  50,  800, 'false', 'car'),
    ('highway', 'living_street',   1,  10,  300, 'false', 'car'),
    ('highway', 'service',         1,  20,  400, 'false', 'car'),
    ('highway', 'busway',          1,  50, 1200, 'false', 'car,bus'),
    ('railway', 'rail',            1, 160, 9999, 'false', 'rail'),
    ('railway', 'light_rail',      1,  70, 9999, 'false', 'light_rail'),
    ('railway', 'tram',            1,  70, 9999, 'false', 'light_rail'),
]

# GTFS route_type -> MATSim schedule mode, then which network modes may carry it.
MODE_ASSIGNMENT = [
    ('bus', 'car,bus'),
    ('rail', 'rail'),
    ('light_rail', 'light_rail,tram,car'),
    ('tram', 'light_rail,tram,car'),
    ('ferry', 'artificial'),
]


def log(msg):
    print('%s  %s' % (time.strftime('%H:%M:%S'), msg), flush=True)


def java(args, tag):
    j, jar, _nc, _sh = tc.require()
    cmd = [j, JAVA_XMX, '-cp', jar] + args
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t0
    logdir = os.path.join(WORK, 'logs')
    os.makedirs(logdir, exist_ok=True)
    with open(os.path.join(logdir, tag + '.log'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(p.stdout or '')
        f.write('\n---- stderr ----\n')
        f.write(p.stderr or '')
    if p.returncode != 0:
        tail = '\n'.join((p.stderr or p.stdout or '').strip().splitlines()[-25:])
        raise SystemExit('pt2matsim failed (%s, exit %d)\n%s' % (tag, p.returncode, tail))
    return dt


# ---------------------------------------------------------------------------
# stage 1: merge the themed OSM extracts
# ---------------------------------------------------------------------------
def merge_osm(dest):
    """One .osm carrying the road and railway extracts, elements in OSM order.

    Written by hand rather than with an OSM tool so the pipeline keeps its P1
    dependency footprint (lxml only) and so the merge order - and therefore the
    output digest - is fixed by this function, not by a library's iteration.
    """
    from lxml import etree
    if os.path.exists(dest):
        log('   merged OSM already present (%s, %.0f MB)'
            % (dest, os.path.getsize(dest) / 1e6))
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    seen = {'node': set(), 'way': set(), 'relation': set()}
    counts = collections.Counter()
    tmp = dest + '.part'
    with open(tmp, 'wb') as out:
        out.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        out.write(b'<osm version="0.6" generator="build_matsim_network.py">\n')
        for kind in ('node', 'way', 'relation'):
            for src in OSM_INPUTS:
                ctx = etree.iterparse(src, events=('end',), tag=(kind,))
                for _, el in ctx:
                    i = el.get('id')
                    if i in seen[kind]:
                        el.clear()
                        continue
                    seen[kind].add(i)
                    counts[kind] += 1
                    out.write(etree.tostring(el, encoding='utf-8'))
                    el.clear()
                    while el.getprevious() is not None:
                        del el.getparent()[0]
                del ctx
                log('   %-8s after %s: %d' % (kind, os.path.basename(src), counts[kind]))
        out.write(b'</osm>\n')
    os.replace(tmp, dest)
    log('   merged -> %s (%.0f MB) %s' % (dest, os.path.getsize(dest) / 1e6, dict(counts)))
    return dest


# ---------------------------------------------------------------------------
# stage 2: base network
# ---------------------------------------------------------------------------
def write_osm_config(path, osm_file, network_out):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<!DOCTYPE config SYSTEM "http://www.matsim.org/files/dtd/config_v2.dtd">',
             '<config>', '\t<module name="OsmConverter" >',
             '\t\t<param name="keepPaths" value="false" />',
             '\t\t<param name="keepTagsAsAttributes" value="true" />',
             '\t\t<param name="keepWaysWithPublicTransit" value="true" />',
             '\t\t<param name="maxLinkLength" value="500.0" />',
             '\t\t<param name="osmFile" value="%s" />' % osm_file.replace('\\', '/'),
             '\t\t<param name="outputCoordinateSystem" value="%s" />' % CRS,
             '\t\t<param name="outputNetworkFile" value="%s" />' % network_out.replace('\\', '/'),
             '\t\t<param name="parseTurnRestrictions" value="true" />',
             '\t\t<param name="scaleMaxSpeed" value="false" />',
             '\t\t<param name="writeCRS" value="true" />']
    for modes, sub in (('car', 'car'), ('bus, car', 'bus'), ('rail, light_rail', 'rail')):
        lines += ['\t\t<parameterset type="routableSubnetwork" >',
                  '\t\t\t<param name="allowedTransportModes" value="%s" />' % modes,
                  '\t\t\t<param name="subnetworkMode" value="%s" />' % sub,
                  '\t\t</parameterset>']
    for key, val, lanes, kmh, cap, oneway, modes in WAY_DEFAULTS:
        lines += ['\t\t<parameterset type="wayDefaultParams" >',
                  '\t\t\t<param name="allowedTransportModes" value="%s" />' % modes,
                  '\t\t\t<param name="freespeed" value="%.6f" />' % (kmh / 3.6),
                  '\t\t\t<param name="freespeedFactor" value="1.0" />',
                  '\t\t\t<param name="laneCapacity" value="%.1f" />' % cap,
                  '\t\t\t<param name="lanes" value="%.1f" />' % lanes,
                  '\t\t\t<param name="oneway" value="%s" />' % oneway,
                  '\t\t\t<param name="osmKey" value="%s" />' % key,
                  '\t\t\t<param name="osmValue" value="%s" />' % val,
                  '\t\t</parameterset>']
    lines += ['\t</module>', '</config>', '']
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines))
    return path


def build_base_network():
    os.makedirs(os.path.join(OUT, 'base'), exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    osm = merge_osm(os.path.join(WORK, 'newcastle_multimodal.osm'))
    net = os.path.join(OUT, 'base', 'network.xml.gz')
    cfg = write_osm_config(os.path.join(WORK, 'osm_converter.xml'), osm, net)
    log('Osm2MultimodalNetwork -> %s' % net)
    dt = java(['org.matsim.pt2matsim.run.Osm2MultimodalNetwork', cfg], 'osm2network')
    log('   done in %.0f s, %.0f MB' % (dt, os.path.getsize(net) / 1e6))
    return net


# ---------------------------------------------------------------------------
# stage 3: E1 road variants as link-attribute patches
# ---------------------------------------------------------------------------
LINK_BLOCK_RE = re.compile(r'<link\b.*?</link>', re.S)
ATTR_RE = re.compile(r'(\w[\w:]*)="([^"]*)"')
WAY_ID_RE = re.compile(r'name="osm:way:id"[^>]*>(\d+)<')
DISALLOWED_RE = re.compile(
    r'\s*<attribute name="disallowedNextLinks".*?</attribute>\n?', re.S)


def apply_variants(base_net):
    """Write one network per E1 road variant by rewriting link attributes.

    A MATSim link carries its OSM way id as the nested attribute `osm:way:id`,
    and one OSM way becomes several links, so a patch row fans out over every
    link derived from that way. Lane count moves `permlanes`; capacity moves with
    it at the same per-lane rate; kerbside use is not a MATSim link field so it is
    carried as a link attribute for the SUMO corridor and the parking layer.

    The full-capacity counterfactual additionally drops `disallowedNextLinks`
    from corridor links - E1 specifies 'no banned turns' for the network without
    the tram, and those restrictions are exactly what pt2matsim wrote there.
    """
    variants = list(csv.DictReader(open(E1_ROAD_VARIANTS, encoding='utf-8')))
    patches = list(csv.DictReader(open(PATCHES, encoding='utf-8')))
    by_variant = collections.defaultdict(dict)
    for p in patches:
        by_variant[p['road_variant_ref']][p['edge_id'][1:]] = p   # strip the 'w'

    with gzip.open(base_net, 'rt', encoding='utf-8') as f:
        xml = f.read()

    report = {}
    for v in variants:
        ref = v['road_variant_ref']
        out_dir = os.path.join(OUT, 'variants', ref)
        os.makedirs(out_dir, exist_ok=True)
        dest = os.path.join(out_dir, 'network.xml.gz')
        pat = by_variant.get(ref, {})
        drop_turns = v['banned_turn_movements'] == '0'
        applied = collections.Counter()

        if not pat:
            # The as-built variant departs from OSM nowhere, so it *is* the base
            # network. Writing it as a copy keeps the per-variant path contract.
            body = xml
        else:
            def patch_link(m):
                s = m.group(0)
                wid = WAY_ID_RE.search(s)
                p = pat.get(wid.group(1)) if wid else None
                if not p:
                    return s
                head_end = s.index('>')
                head, tail = s[:head_end], s[head_end:]
                a = dict(ATTR_RE.findall(head))
                changed = p['fields_changed'].split(';')

                if 'num_lanes_per_dir' in changed and p['field_num_lanes_per_dir_to']:
                    new_lanes = float(p['field_num_lanes_per_dir_to'])
                    old_lanes = float(a.get('permlanes') or 1)
                    cap = float(a.get('capacity') or 0)
                    per_lane = (cap / old_lanes) if old_lanes else float(
                        p['capacity_veh_hr_lane'])
                    head = re.sub(r'permlanes="[^"]*"',
                                  'permlanes="%.1f"' % new_lanes, head)
                    head = re.sub(r'capacity="[^"]*"',
                                  'capacity="%.1f"' % (per_lane * new_lanes), head)
                    applied['num_lanes_per_dir'] += 1

                if 'kerbside_use' in changed and p['field_kerbside_use_to']:
                    tail = tail.replace(
                        '</attributes>',
                        '\t<attribute name="kerbsideUse" class="java.lang.String">'
                        '%s</attribute>\n\t\t\t</attributes>'
                        % p['field_kerbside_use_to'], 1)
                    applied['kerbside_use'] += 1

                if drop_turns and 'disallowedNextLinks' in tail:
                    tail = DISALLOWED_RE.sub('', tail)
                    applied['banned_turns_removed'] += 1

                return head + tail
            body = LINK_BLOCK_RE.sub(patch_link, xml)

        with open(dest, 'wb') as fh:
            g = gzip.GzipFile(fileobj=fh, mode='wb', mtime=0)
            g.write(body.encode('utf-8'))
            g.close()
        report[ref] = dict(patch_rows=len(pat), links_touched=dict(applied),
                           identical_to_base=not pat,
                           banned_turns_dropped=drop_turns,
                           bytes=os.path.getsize(dest))
        log('   %-42s %5d patch rows -> links %s'
            % (ref, len(pat), dict(applied) or 'none (= base)'))
    return report


# ---------------------------------------------------------------------------
# stage 4: GTFS -> unmapped schedule -> mapped schedule
# ---------------------------------------------------------------------------
def write_mapper_config(path, network, schedule, out_net, out_sched, out_street, threads):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<!DOCTYPE config SYSTEM "http://www.matsim.org/files/dtd/config_v2.dtd">',
             '<config>', '\t<module name="PublicTransitMapping" >',
             '\t\t<param name="boundedSearch" value="true" />',
             '\t\t<param name="candidateDistanceMultiplier" value="1.6" />',
             '\t\t<param name="inputNetworkFile" value="%s" />' % network.replace('\\', '/'),
             '\t\t<param name="inputScheduleFile" value="%s" />' % schedule.replace('\\', '/'),
             '\t\t<param name="maxLinkCandidateDistance" value="90.0" />',
             '\t\t<param name="maxTravelCostFactor" value="5.0" />',
             '\t\t<param name="modeSpecificRules" value="false" />',
             '\t\t<param name="modesToKeepOnCleanUp" value="car" />',
             '\t\t<param name="nLinkThreshold" value="6" />',
             '\t\t<param name="networkRouter" value="SpeedyALT" />',
             '\t\t<param name="numOfThreads" value="%d" />' % threads,
             '\t\t<param name="outputNetworkFile" value="%s" />' % out_net.replace('\\', '/'),
             '\t\t<param name="outputScheduleFile" value="%s" />' % out_sched.replace('\\', '/'),
             '\t\t<param name="outputStreetNetworkFile" value="%s" />'
             % out_street.replace('\\', '/'),
             '\t\t<param name="removeNotUsedStopFacilities" value="true" />',
             '\t\t<param name="routingWithCandidateDistance" value="true" />',
             '\t\t<param name="scheduleFreespeedModes" value="artificial" />',
             '\t\t<param name="threadChunkSize" value="100" />',
             '\t\t<param name="travelCostType" value="linkLength" />']
    for sched_mode, net_modes in MODE_ASSIGNMENT:
        lines += ['\t\t<parameterset type="transportModeAssignment" >',
                  '\t\t\t<param name="maxLinkCandidateDistance" value="90.0" />',
                  '\t\t\t<param name="nLinkThreshold" value="6" />',
                  '\t\t\t<param name="networkModes" value="%s" />' % net_modes,
                  '\t\t\t<param name="scheduleMode" value="%s" />' % sched_mode,
                  '\t\t\t<param name="strictLinkRule" value="false" />',
                  '\t\t</parameterset>']
    lines += ['\t</module>', '</config>', '']
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines))
    return path


def unpack_feed(name, zip_path):
    """pt2matsim reads a GTFS folder, not a zip."""
    d = os.path.join(WORK, 'gtfs', name)
    if os.path.isdir(d) and os.path.exists(os.path.join(d, 'stop_times.txt')):
        return d
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        for n in sorted(z.namelist()):
            if n.endswith('/'):
                continue
            with z.open(n) as src, open(os.path.join(d, os.path.basename(n)), 'wb') as dst:
                shutil.copyfileobj(src, dst)
    return d


def build_schedule(name, zip_path, base_net, threads):
    out_dir = os.path.join(OUT, 'schedules', name)
    os.makedirs(out_dir, exist_ok=True)
    unmapped = os.path.join(WORK, 'unmapped', '%s_schedule.xml.gz' % name)
    vehicles = os.path.join(out_dir, 'transitVehicles.xml.gz')
    os.makedirs(os.path.dirname(unmapped), exist_ok=True)

    folder = unpack_feed(name, zip_path)
    t0 = time.time()
    if not os.path.exists(unmapped):
        java(['org.matsim.pt2matsim.run.Gtfs2TransitSchedule',
              folder, GTFS_DAY_PARAM, CRS, unmapped, vehicles], 'gtfs_%s' % name)
    t_gtfs = time.time() - t0

    mapped_sched = os.path.join(out_dir, 'transitSchedule.xml.gz')
    mapped_net = os.path.join(out_dir, 'network.xml.gz')
    street_net = os.path.join(WORK, 'street', '%s_street.xml.gz' % name)
    os.makedirs(os.path.dirname(street_net), exist_ok=True)
    cfg = write_mapper_config(os.path.join(WORK, 'ptmap_%s.xml' % name),
                             base_net, unmapped, mapped_net, mapped_sched,
                             street_net, threads)
    t1 = time.time()
    java(['org.matsim.pt2matsim.run.PublicTransitMapper', cfg], 'ptmap_%s' % name)
    t_map = time.time() - t1

    stats = schedule_stats(mapped_sched)
    stats.update(feed=zip_path, gtfs_seconds=round(t_gtfs, 1),
                 mapping_seconds=round(t_map, 1),
                 network_bytes=os.path.getsize(mapped_net),
                 schedule_bytes=os.path.getsize(mapped_sched))
    log('   %-30s %5.0f s map | %d stops, %d routes, %d unmapped-link stops'
        % (name, t_map, stats['stop_facilities'], stats['transit_routes'],
           stats['stops_without_link']))
    return stats


STOP_LINK_RE = re.compile(r'<stopFacility id="([^"]+)"[^>]*?linkRefId="([^"]+)"')
ROUTE_RE = re.compile(r'<transitRoute id="([^"]+)".*?</transitRoute>', re.S)


def schedule_stats(path):
    """Counts straight off the mapped schedule: the mapping's own report.

    Also records two fingerprints, because PublicTransitMapper is not
    reproducible run to run (DECISIONS.md 3.5):

      stop_link_fingerprint   sha256 over the sorted stop -> link assignment.
                              Measured stable across repeated builds, so
                              tests/check_package.py asserts it exactly.
      route_link_fingerprint  sha256 over the sorted route link sequences. This
                              one moves between builds; it identifies the build
                              of record rather than constraining a rebuild.
    """
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        xml = f.read()
    facilities = re.findall(r'<stopFacility\b[^>]*>', xml)
    linked = sum(1 for s in facilities if 'linkRefId="' in s)
    routes = xml.count('<transitRoute ')
    lines = xml.count('<transitLine ')
    departures = xml.count('<departure ')
    route_links = re.findall(r'<link\s+refId="([^"]+)"', xml)
    artificial = sum(1 for l in route_links if l.startswith('pt_'))
    modes = collections.Counter(re.findall(r'<transportMode>([^<]+)</transportMode>', xml))

    stop_link = sorted('%s\t%s' % (a, b) for a, b in STOP_LINK_RE.findall(xml))
    route_seq = sorted('%s\t%s' % (m.group(1),
                                   ','.join(re.findall(r'<link refId="([^"]+)"', m.group(0))))
                       for m in ROUTE_RE.finditer(xml))
    return dict(stop_facilities=len(facilities),
                stops_with_link=linked,
                stops_without_link=len(facilities) - linked,
                transit_lines=lines, transit_routes=routes, departures=departures,
                route_link_refs=len(route_links),
                artificial_link_refs=artificial,
                artificial_share_pct=round(100.0 * artificial / max(len(route_links), 1), 2),
                stop_link_fingerprint=hashlib.sha256(
                    '\n'.join(stop_link).encode('utf-8')).hexdigest(),
                route_link_fingerprint=hashlib.sha256(
                    '\n'.join(route_seq).encode('utf-8')).hexdigest(),
                modes=dict(modes))


def compare_builds(name, base_net, threads):
    """Re-map one feed and report how far the second build drifts from the first.

    The drift is a property of pt2matsim, not of this pipeline, so it is measured
    and published rather than asserted away.
    """
    out_dir = os.path.join(OUT, 'schedules', name)
    tmp = os.path.join(WORK, 'determinism')
    os.makedirs(tmp, exist_ok=True)
    keep = {n: os.path.join(tmp, '%s_first_%s' % (name, n))
            for n in ('transitSchedule.xml.gz', 'network.xml.gz')}
    for n, k in keep.items():
        shutil.copyfile(os.path.join(out_dir, n), k)
    build_schedule(name, FEEDS[name], base_net, threads)

    def load(p):
        with gzip.open(p, 'rt', encoding='utf-8') as f:
            return f.read()
    A, B = load(keep['transitSchedule.xml.gz']), \
        load(os.path.join(out_dir, 'transitSchedule.xml.gz'))
    fa, fb = dict(STOP_LINK_RE.findall(A)), dict(STOP_LINK_RE.findall(B))
    shared = set(fa) & set(fb)
    same_link = sum(1 for k in shared if fa[k] == fb[k])

    def routes(x):
        return {m.group(1): tuple(re.findall(r'<link refId="([^"]+)"', m.group(0)))
                for m in ROUTE_RE.finditer(x)}
    ra, rb = routes(A), routes(B)
    rshared = set(ra) & set(rb)
    same_route = sum(1 for k in rshared if ra[k] == rb[k])
    # restore the build of record: the check must not become the artefact
    for n, k in keep.items():
        shutil.copyfile(k, os.path.join(out_dir, n))
    return dict(
        feed=name,
        stop_facilities=[len(fa), len(fb)],
        stop_link_assignment_identical_pct=round(100.0 * same_link / max(len(shared), 1), 3),
        transit_routes=[len(ra), len(rb)],
        route_link_sequence_identical_pct=round(100.0 * same_route / max(len(rshared), 1), 3))


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', choices=['all', 'network', 'variants', 'schedules'],
                    default='all')
    ap.add_argument('--only', default='', help='comma-separated feed names')
    ap.add_argument('--workers', type=int, default=2,
                    help='feeds mapped concurrently (each uses --threads threads)')
    ap.add_argument('--threads', type=int, default=2, help='PublicTransitMapper threads')
    ap.add_argument('--determinism-check', default='',
                    help='comma-separated feeds to re-map and compare (DECISIONS 3.5)')
    a = ap.parse_args()

    tc.require()
    os.makedirs(OUT, exist_ok=True)
    report_path = os.path.join(OUT, '_matsim_build_report.json')
    report = json.load(open(report_path, encoding='utf-8')) \
        if os.path.exists(report_path) else {}

    base_net = os.path.join(OUT, 'base', 'network.xml.gz')
    if a.stage in ('all', 'network') or not os.path.exists(base_net):
        base_net = build_base_network()
        report['base_network'] = network_stats(base_net)

    if a.stage in ('all', 'variants'):
        log('applying E1 road variants')
        report['road_variants'] = apply_variants(base_net)

    if a.stage in ('all', 'schedules'):
        want = [k for k in FEEDS if not a.only or k in a.only.split(',')]
        log('mapping %d feed(s) with %d worker(s) x %d thread(s)'
            % (len(want), a.workers, a.threads))
        sched = report.get('schedules', {})
        with futures.ThreadPoolExecutor(max_workers=a.workers) as ex:
            fut = {ex.submit(build_schedule, k, FEEDS[k], base_net, a.threads): k
                   for k in want}
            for f in futures.as_completed(fut):
                k = fut[f]
                sched[k] = f.result()
        report['schedules'] = {k: sched[k] for k in FEEDS if k in sched}

    if a.determinism_check:
        log('determinism check: re-mapping %s' % a.determinism_check)
        drift = [compare_builds(k, base_net, a.threads)
                 for k in a.determinism_check.split(',') if k in FEEDS]
        report['determinism_check'] = drift
        for d in drift:
            log('   %-30s stop->link %.3f%% identical, route link seq %.3f%% identical'
                % (d['feed'], d['stop_link_assignment_identical_pct'],
                   d['route_link_sequence_identical_pct']))

    report['toolchain'] = {c['component']: c['version']
                           for c in (tc.load_manifest() or {}).get('components', [])}
    report['crs'] = CRS
    report['gtfs_day_param'] = GTFS_DAY_PARAM
    with open(report_path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write('\n')
    log('report -> %s' % report_path)


def network_stats(path):
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        xml = f.read()
    nodes = xml.count('<node ')
    links = re.findall(r'<link\b[^>]*>', xml)
    modes = collections.Counter()
    length = 0.0
    for s in links:
        m = re.search(r'modes="([^"]*)"', s)
        if m:
            for mode in m.group(1).split(','):
                modes[mode.strip()] += 1
        m = re.search(r'length="([^"]*)"', s)
        if m:
            length += float(m.group(1))
    return dict(nodes=nodes, links=len(links), km=round(length / 1000, 1),
                links_by_mode=dict(modes), bytes=os.path.getsize(path))


if __name__ == '__main__':
    main()
