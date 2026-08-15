#!/usr/bin/env python
"""Assemble a runnable MATSim scenario per (scenario x day type).

Three things have to come together, and each has a constraint attached.

1. **The schedule, filtered to one day type.** Every mapped feed carries all
   three day types at once - S2 has 1,714 routes, 1,231 WEEKDAY + 291 SAT +
   192 SUN, and 4,269 departures against 2,188 weekday GTFS trips. Running the
   unfiltered schedule would put roughly twice the real PT supply on the
   network. The filter works on the **already mapped** schedule, selecting
   `transitRoute` ids by their day-type token, so no feed is ever re-mapped:
   route link sequences are copied through untouched. That matters because
   pt2matsim is not reproducible run to run (DECISIONS.md 3.5) and every
   scenario comparison must sit on one build.

2. **The run network.** It is *not* `networks/matsim/variants/`. Those are
   patched over the base network, which has no mapped transit links. The
   network a scenario actually runs on is its own mapped
   `schedules/<S>/network.xml.gz` - 151,594 links against the base 157,678,
   with 928 artificial transit links added and 7,012 pre-mapping rail
   placeholders removed (all of them pt-mode; no car link is lost). The E1 road
   variant is re-applied on top of that by `osm:way:id`, which every link
   carries, so the variant means the same thing on the run network as it does
   on the base.

3. **Scoring, translated from C1.** C1 is a nested-logit specification and
   MATSim's scoring is not. What does not survive the translation is stated in
   the report rather than quietly dropped.

Nothing here runs a scenario. It writes the inputs a run would consume.
"""

# City-relative paths resolve through src/city.py: `data/...` names a
# location inside cities/<city>/, not inside the repository root.
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                  '..', '..', 'src'))
import city as _city  # noqa: E402
import os
import re
import csv
import gzip
import json
import argparse
import collections
import xml.etree.ElementTree as ET

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from det_io import gzip_writer

# Model inputs come from cities/<city>/registry/, not from literals here. Every
# value below carries its units, provenance and either a sweep, a held-fixed rule
# or a derived-from identity there. See DECISIONS.md 15.
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import registry as _registry  # noqa: E402
from registry import param_config as _param_config  # noqa: E402

MATSIM = _city.path('networks/matsim')
PATCHES = _city.path('data/processed/network/A1_road_variant_patches.csv')
E1 = _city.path('scenarios/E1_scenarios.csv')
PARAMS = _city.path('params/C1_parameters.json')
PLANS = _city.path('demand/plans/matsim')
OUT = _city.path('scenarios/matsim')
PARK_PRICE_ZONES = _city.path('data/processed/landuse/A5_parking_price_zones.csv')
PARK_PRICE_FILE = 'parking_prices.tsv'

# The day types come from the city's own descriptor. They were a list literal
# here, which meant a city with a different service week could not be built
# without editing the framework.
DAY_TYPES = list(_city.descriptor()['day_types'])

# NOTHING IS RESOLVED AT IMPORT. Twenty-two values used to be read into module
# constants here, and a value read at import is a value fixed BEFORE the
# scenario, day and run overlays are known - so a run overlay setting one of
# them was accepted by the resolver, recorded in the run's provenance snapshot,
# and could not possibly reach the config. Every read below happens inside a
# function, against the configuration that run actually resolved.


def check_scoring_order(cfg):
    """The one ordering that is a finding rather than an incidental.

    Cycling time is dearer per hour than walking time in every calibrated model.
    The model had it inverted (walk 2.0, bike 1.3), and that inversion conceded
    every short trip to bike (DECISIONS.md 9.28). Checked against the resolved
    configuration, so an overlay cannot reintroduce it either.
    """
    walk = cfg.get('C.time_weights.beta_walk_mode')
    bike = cfg.get('C.time_weights.beta_bike_mode')
    if bike < walk:
        raise SystemExit('C.time_weights.beta_bike_mode (%s) must be >= '
                         'beta_walk_mode (%s): cycling time is dearer per hour than '
                         'walking time in every calibrated model, and inverting that '
                         'ordering is the DECISIONS.md 9.28 defect' % (bike, walk))

LINK_BLOCK_RE = re.compile(r'<link\b.*?(?:/>|</link>)', re.S)
WAY_ID_RE = re.compile(r'name="osm:way:id"[^>]*>(\d+)<')
ATTR_RE = re.compile(r'(\w[\w:]*)="([^"]*)"')


# A route id carries its day type as a delimited token. The era and scenario
# feeds namespace it with a dot (`nisc001:WEEKDAY.2302960`); the S1 shuttle and
# S3 BRT that this script generates use underscores (`S1SHUTTLE_WEEKDAY_0_1`).
# Matching only the dotted form silently dropped both from every day type -
# which would have run S1 with no shuttle and S3 with no BRT, i.e. each
# scenario without the intervention it exists to test.
DAY_TOKEN_RE = re.compile(r'(?:^|[.:_])(WEEKDAY|SAT|SUN)(?:[._]|$)')

# MATSim picks its reader from the doctype, so a schedule written without one
# cannot be loaded at all - the parser fails at line 2 with a null delegate.
# ElementTree drops the doctype on a parse/write round trip, so it is written
# back explicitly. See DECISIONS.md 9.4.
XML_DECL = b"<?xml version='1.0' encoding='utf-8'?>\n"
SCHEDULE_DOCTYPE = (b'<!DOCTYPE transitSchedule SYSTEM '
                    b'"http://www.matsim.org/files/dtd/transitSchedule_v2.dtd">\n')


def day_of_route(route_id):
    m = DAY_TOKEN_RE.search(route_id)
    return m.group(1) if m else None


def split_schedule(src_dir, dst_dir, day, cfg):
    """Filter a mapped schedule to one day type. No re-mapping, ever.

    Returns counts so the caller can assert that link sequences were copied
    rather than regenerated.
    """
    os.makedirs(dst_dir, exist_ok=True)
    with gzip.open(os.path.join(src_dir, 'transitSchedule.xml.gz'), 'rb') as f:
        tree = ET.parse(f)
    root = tree.getroot()

    kept_routes = dropped_routes = 0
    kept_dep = dropped_dep = 0
    mixed_routes = 0
    vehicles_used = set()
    stops_served = set()
    for line in list(root.findall('transitLine')):
        for route in list(line.findall('transitRoute')):
            # Filter DEPARTURES, not routes. pt2matsim groups trips into a
            # transitRoute by stop sequence, not by service, so a route is not
            # day-type homogeneous: 233 of S2's 1,714 routes carry departures
            # from more than one service. Keying the filter on the route id put
            # 1,261 of 4,269 departures (29.5%) in the wrong day type and
            # removed the light rail from every weekday run outright, because
            # both of its routes happen to be named after a weekend trip.
            # See DECISIONS.md 9.9.
            deps = route.find('departures')
            keep_here = []
            for dep in list(deps.findall('departure') if deps is not None else []):
                if day_of_route(dep.get('id', '')) == day:
                    keep_here.append(dep)
                else:
                    deps.remove(dep)
                    dropped_dep += 1
            if not keep_here:
                line.remove(route)
                dropped_routes += 1
                continue
            if day_of_route(route.get('id', '')) != day:
                mixed_routes += 1
            kept_routes += 1
            kept_dep += len(keep_here)
            for stop in route.findall('./routeProfile/stop'):
                stops_served.add(stop.get('refId'))
            for dep in keep_here:
                v = dep.get('vehicleRefId')
                if v:
                    vehicles_used.add(v)
        if not line.findall('transitRoute'):
            root.remove(line)

    # Dropping two thirds of the routes orphans the stops and the transfer
    # relations that only they used, and SwissRailRaptor dereferences a null
    # array on the first of those it meets - so the schedule has to be left
    # referentially closed, not merely smaller. See DECISIONS.md 9.4.
    facilities = root.find('transitStops')
    dropped_fac = 0
    for fac in list(facilities.findall('stopFacility')):
        if fac.get('id') not in stops_served:
            facilities.remove(fac)
            dropped_fac += 1
    kept_fac = len(facilities.findall('stopFacility'))

    mtt = root.find('minimalTransferTimes')
    kept_rel = dropped_rel = 0
    if mtt is not None:
        for rel in list(mtt.findall('relation')):
            if (rel.get('fromStop') not in stops_served
                    or rel.get('toStop') not in stops_served):
                mtt.remove(rel)
                dropped_rel += 1
        kept_rel = len(mtt.findall('relation'))

    out_sched = os.path.join(dst_dir, 'transitSchedule.xml.gz')
    with gzip_writer(out_sched, text=False) as f:
        f.write(XML_DECL)
        f.write(SCHEDULE_DOCTYPE)
        tree.write(f, encoding='utf-8', xml_declaration=False)

    with gzip.open(os.path.join(src_dir, 'transitVehicles.xml.gz'), 'rb') as f:
        vtree = ET.parse(f)
    vroot = vtree.getroot()
    tag = lambda e: e.tag.split('}')[-1]
    kept_veh = 0
    for veh in list(vroot):
        if tag(veh) != 'vehicle':
            continue
        if veh.get('id') in vehicles_used:
            kept_veh += 1
        else:
            vroot.remove(veh)
    # The mapped fleet is pt2matsim's generic defaults, and every one of them
    # overstates the real vehicle: tram 180 seats against a published 270 total,
    # rail 400 against a 146 two-car set (roughly 2.7x), ferry 250 against 200,
    # bus 70 seats against 44. None of them carried ANY standing room, which
    # left the C1 crowding multipliers inert by construction - crowding cannot
    # bind if nobody can stand (issue 18, DECISIONS.md 9.12, 9.18, 9.21).
    #
    # All four are now corrected from published figures (DECISIONS.md 9.30).
    # Where a published split exists it is used (ferry, bus); where only a total
    # is published the seated share is assumed and swept and the standing room
    # is derived by identity (tram, rail). Nothing here is observed for
    # Newcastle operations - these are manufacturer and operator figures.
    FLEET_CAPACITY = {
        'Tram':  ('A.lightrail.capacity_seated', 'A.lightrail.capacity_standing'),
        'Bus':   ('A.transit.bus_capacity_seated', 'A.transit.bus_capacity_standing'),
        'Ferry': ('A.transit.ferry_capacity_seated', 'A.transit.ferry_capacity_standing'),
        'Rail':  ('A.transit.rail_capacity_seated', 'A.transit.rail_capacity_standing'),
    }
    patched_types = []
    for vt in vroot:
        if tag(vt) != 'vehicleType':
            continue
        keys = FLEET_CAPACITY.get(vt.get('id'))
        if keys is None:
            continue
        seated, standing = cfg.get(keys[0]), cfg.get(keys[1])
        for cap in vt:
            if tag(cap) != 'capacity':
                continue
            patched_types.append((vt.get('id'), cap.get('seats'),
                                  cap.get('standingRoomInPersons'),
                                  str(seated), str(standing)))
            cap.set('seats', str(seated))
            cap.set('standingRoomInPersons', str(standing))
    out_veh = os.path.join(dst_dir, 'transitVehicles.xml.gz')
    with gzip_writer(out_veh, text=False) as f:
        vtree.write(f, encoding='utf-8', xml_declaration=True)

    return dict(routes_kept=kept_routes, routes_dropped=dropped_routes,
                departures=kept_dep, departures_dropped=dropped_dep,
                routes_kept_under_a_foreign_day_id=mixed_routes,
                vehicles=kept_veh,
                vehicle_capacity_patched=patched_types,
                vehicle_refs=len(vehicles_used),
                stop_facilities_kept=kept_fac, stop_facilities_dropped=dropped_fac,
                transfer_relations_kept=kept_rel,
                transfer_relations_dropped=dropped_rel)


ATTRIBUTE_EL = ('<attribute name="%s" class="java.lang.String">%s</attribute>')
NAMED_ATTR_RE = r'<attribute name="%s"[^>]*>.*?</attribute>'


def set_link_attribute(tail, name, value):
    """Set one `<attribute>` inside a link's existing `<attributes>` block.

    Every mapped link already carries an `<attributes>` block (`osm:way:id` is
    how the E1 patch finds it at all), so appending a second one before
    `</link>` produces `More than one instance of element <attributes>` and
    MATSim refuses to read the network. Six of the ten run networks were built
    that way. See DECISIONS.md 9.4.
    """
    el = ATTRIBUTE_EL % (name, value)
    existing = re.search(NAMED_ATTR_RE % re.escape(name), tail, re.S)
    if existing:
        return tail[:existing.start()] + el + tail[existing.end():]
    if '</attributes>' in tail:
        return tail.replace('</attributes>', el + '</attributes>', 1)
    if '</link>' in tail:
        return tail.replace('</link>', '<attributes>' + el + '</attributes></link>', 1)
    return tail


MODES_ATTR_RE = re.compile(r'modes="([^"]*)"')


def allow_ride(xml):
    """Let `ride` use the roads `car` uses.

    The mapped network permits `car`, never `ride`, so a config that declared
    `ride` a network mode produced `checking 0 nodes and 0 links for dead-ends`
    and then threw during `PrepareForSim` - the run inputs could not be used
    even once the schedules were fixed (DECISIONS.md 9.4, defect 4).

    A car passenger is not a second vehicle, so `ride` is *routed* on the road
    network - which is what gives it a congested travel time rather than a
    beeline guess - but is not simulated in the mobsim, so it occupies no
    capacity. `travelTimeCalculator.separateModes=false` makes it read the car
    travel times, since no ride vehicle is ever observed to generate its own.
    """
    n = 0

    def add_ride(m):
        nonlocal n
        modes = [x for x in m.group(1).split(',') if x]
        if 'car' not in modes or 'ride' in modes:
            return m.group(0)
        n += 1
        return 'modes="%s"' % ','.join(sorted(modes + ['ride']))

    return MODES_ATTR_RE.sub(add_ride, xml), n


def patch_network(src_net, dst_net, patches, drop_turns):
    """Re-apply an E1 road variant to a mapped schedule network by osm:way:id."""
    with gzip.open(src_net, 'rt', encoding='utf-8') as f:
        xml = f.read()
    applied = collections.Counter()

    def patch_link(m):
        s = m.group(0)
        wid = WAY_ID_RE.search(s)
        p = patches.get(wid.group(1)) if wid else None
        if not p:
            return s
        head_end = s.index('>')
        head, tail = s[:head_end], s[head_end:]
        a = dict(ATTR_RE.findall(head))
        changed = (p.get('fields_changed') or '').split(';')
        if 'num_lanes_per_dir' in changed and p.get('field_num_lanes_per_dir_to'):
            try:
                old = float(a.get('permlanes', '1') or 1)
                new = float(p['field_num_lanes_per_dir_to'])
                if old > 0 and new > 0:
                    cap = float(a.get('capacity', '0') or 0)
                    a['capacity'] = '%.1f' % (cap / old * new)
                    a['permlanes'] = '%.1f' % new
                    head = '<link ' + ' '.join('%s="%s"' % kv for kv in a.items())
                    applied['num_lanes_per_dir'] += 1
            except (ValueError, ZeroDivisionError):
                pass
        if 'kerbside_use' in changed and p.get('field_kerbside_use_to'):
            new_tail = set_link_attribute(tail, 'osm:way:kerbside',
                                          p['field_kerbside_use_to'])
            if new_tail != tail:
                applied['kerbside_use'] += 1
                tail = new_tail
        if drop_turns and 'disallowedNextLinks' in tail:
            # E1's "no banned turns" applies to the corridor without the tram,
            # not to the whole study area. Stripping the attribute network-wide
            # would delete 1,235 observed restrictions instead of the handful on
            # the corridor, and quietly hand every scenario a freer road network.
            new_tail = re.sub(r'<attribute name="disallowedNextLinks".*?</attribute>',
                              '', tail, flags=re.S)
            if new_tail != tail:
                applied['banned_turns_removed'] += 1
                tail = new_tail
        return head + tail

    body = LINK_BLOCK_RE.sub(patch_link, xml)
    body, ride_links = allow_ride(body)
    applied['ride_links'] = ride_links
    os.makedirs(os.path.dirname(dst_net), exist_ok=True)
    with gzip_writer(dst_net) as f:
        f.write(body)
    return dict(applied)


ZONES_SA1 = _city.path('data/processed/zones/zones_SA1.gpkg')


def write_parking_prices(net_path, dst_path):
    """Join the run network's car links to the zone parking price.

    A link is priced by the zone its midpoint falls in. Only PRICED links are
    written - roughly 22k of the run network's ~144k car links - because a link
    absent from the table is free, and writing 144k rows to say so 30 times over
    is bytes for nothing.

    The join happens here rather than in Java for the reason CLAUDE.md gives:
    the price of a place has to be derived from a boundary, and a boundary is a
    build-time object. Java gets two columns.
    """
    import geopandas as gpd

    prices = {}
    for r in csv.DictReader(open(PARK_PRICE_ZONES, encoding='utf-8')):
        p = float(r['price_aud_hr'])
        if p > 0:
            prices[r['SA1_CODE21']] = p
    nodes, links = {}, []
    with gzip.open(net_path, 'rb') as fh:
        for _, el in ET.iterparse(fh, events=('end',)):
            if el.tag == 'node':
                nodes[el.get('id')] = (float(el.get('x')), float(el.get('y')))
                el.clear()
            elif el.tag == 'link':
                if 'car' in el.get('modes', '').split(','):
                    links.append((el.get('id'), el.get('from'), el.get('to')))
                el.clear()
    if not links:
        raise SystemExit('%s carries no car links' % net_path)
    xs = [(nodes[a][0] + nodes[b][0]) / 2.0 for _, a, b in links]
    ys = [(nodes[a][1] + nodes[b][1]) / 2.0 for _, a, b in links]
    zones = gpd.read_file(ZONES_SA1).to_crs(_city.crs())[['SA1_CODE21', 'geometry']]
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(xs, ys), crs=_city.crs())
    j = gpd.sjoin(pts, zones, how='left', predicate='within')
    j = j[~j.index.duplicated(keep='first')].sort_index()
    codes = list(j['SA1_CODE21'])

    rows = []
    for (link_id, _, _), code in zip(links, codes):
        # NaN for a link outside the zone system - beyond the study area, and
        # free, which is what an absent row already means.
        price = prices.get('' if code != code or code is None else str(code))
        if price:
            rows.append((link_id, price))
    rows.sort(key=lambda r: r[0])
    with open(dst_path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('link_id\tprice_aud_hr\n')
        for link_id, price in rows:
            fh.write('%s\t%.4f\n' % (link_id, price))
    return dict(car_links=len(links), priced_links=len(rows),
                priced_zones=len(prices))


def parking_window(cfg, day):
    """The charged window for one day type, as (start_h, end_h).

    A day type with no window - Sunday - resolves to (0, 0), and the handler
    reads an end at or before the start as `charge nothing`. Expressing a free
    day that way rather than with a separate flag keeps one code path.
    """
    win = (cfg.get('A.parking.charged_hours_by_day_type') or {}).get(day)
    if not win:
        return 0.0, 0.0
    return float(win[0]), float(win[1])


def scoring_from_c1(cfg, c1, purpose_share):
    """Translate the C1 nested-logit parameters into MATSim scoring.

    MATSim scores with a Charypar-Nagel utility: one marginal utility of
    travelling per mode, one alternative-specific constant per mode, and an
    opportunity cost of time shared by every activity. Two things in C1 have no
    representation in it, and are reported rather than silently dropped:

      * the **nest structure** (`nesting_coefficient_pt = 0.65`). MATSim's mode
        choice is a co-evolutionary search, not a closed-form nested logit;
        there is nowhere to put a nest coefficient.
      * the **per-purpose value of time**. C1 prices a commute minute at
        18.6 AUD/h and a work-business minute at 55.4; MATSim's scoring is per
        mode, not per purpose. A trip-weighted average is used, so a scenario
        that shifts the purpose mix will not shift the value of time with it.

    The identity used is the conventional one:
        VOT = (performing - traveling_mode) / marginalUtilityOfMoney
    """
    vot = c1['vot_aud_hr']
    wsum = sum(purpose_share.get(p, 0.0) for p in vot)
    vot_avg = (sum(vot[p] * purpose_share.get(p, 0.0) for p in vot) / wsum
               if wsum > 0 else sum(vot.values()) / len(vot))
    w = c1['weights']
    asc = c1['asc']
    perf = cfg.get('C.scoring.performing_utils_per_h')
    mm = cfg.get('C.scoring.marginal_utility_of_money')

    def traveling(weight):
        return round(perf - vot_avg * weight * mm, 4)

    modes = {
        'car': dict(constant=asc['asc_car_driver'][0],
                    marginalUtilityOfTraveling=traveling(1.0)),
        'ride': dict(constant=asc['asc_car_passenger'][0],
                     marginalUtilityOfTraveling=traveling(1.0)),
        'pt': dict(constant=asc['asc_bus'][0],
                   marginalUtilityOfTraveling=traveling(w['beta_ivt']['base'])),
        # walk and bike are scored as MODES here, so they take their own
        # mode-time weights - NOT beta_walk_access, which is the appraisal
        # weight on walking to a stop INSIDE a PT journey. Using the access
        # weight priced a whole walking trip at 2x car time and put the
        # walk-bike indifference distance at 174 m against an observed mean
        # walk trip of 700 m (DECISIONS.md 9.28). MATSim also scores PT
        # access, egress and transfer legs with these same walk params, in the
        # scoring function and again in the raptor router, so this one value
        # governs walk AND half the cost of every PT trip.
        'walk': dict(constant=asc['asc_walk'][0],
                     marginalUtilityOfTraveling=traveling(cfg.get('C.time_weights.beta_walk_mode'))),
        'bike': dict(constant=asc['asc_cycle'][0],
                     marginalUtilityOfTraveling=traveling(cfg.get('C.time_weights.beta_bike_mode'))),
    }
    tp = c1['transfer_penalty']['base']
    return dict(
        performing_utils_per_h=perf,
        performing_sweep=list(cfg.sweep('C.scoring.performing_utils_per_h')),
        monetary_distance_rate=cfg.get('C.scoring.monetary_distance_rate'),
        monetary_distance_rate_sweep=list(cfg.sweep('C.scoring.monetary_distance_rate')),
        strategies=cfg.get('RUN.replanning.weights'),
        replanning_weight_sweep=cfg.sweep('RUN.replanning.weights'),
        marginal_utility_of_money=mm,
        vot_aud_hr_used=round(vot_avg, 3),
        vot_aud_hr_by_purpose=vot,
        purpose_weights=purpose_share,
        waiting_pt=traveling(w['beta_wait']['base']),
        utility_of_line_switch=round(-(tp / 60.0) * vot_avg * mm, 4),
        transfer_penalty_min=tp,
        transfer_penalty_sweep=[c1['transfer_penalty']['low'],
                                c1['transfer_penalty']['high']],
        modes=modes,
        not_representable=[
            'nesting_coefficient_pt=%s and the nested-logit structure: MATSim '
            'mode choice is a co-evolutionary search with no nest parameter'
            % c1['nesting']['nesting_coefficient_pt'],
            'per-purpose value of time: MATSim scores per mode, so a '
            'trip-weighted average (%.2f AUD/h) is used in place of the six '
            'purpose-specific values' % vot_avg,
            'crowding multipliers (beta_crowding_*): require an explicit '
            'capacity-dependent scoring extension, not enabled here',
            'gradient penalties (beta_gradient_uphill=%s, beta_gradient_'
            'downhill=%s): MATSim scores a leg from time and distance and has '
            'no gradient term, so the gradient attached to 43,112 road and '
            '35,653 footway edges reaches mode choice through nothing. It '
            'remains used for corridor grades (issue 21)'
            % (w['beta_gradient_uphill']['base'],
               w['beta_gradient_downhill']['base']),
            'PT walk-access decay (walk_decay, beta_per_m=%s): the access and '
            'egress walk that actually happens is routing.accessEgressType '
            'plus SwissRailRaptor own radius handling, neither of which reads '
            'a decay curve, so the declared curve reaches nothing (issue 21)'
            % c1['walk_decay']['params']['beta_per_m'],
        ])


# --------------------------------------------------------------------------
# the config, BUILT from the registry rather than substituted into a template
# --------------------------------------------------------------------------
# This used to be a 100-line XML template with `{substitution}` holes. Every
# parameter nobody had cut a hole for stayed a literal, and forty-seven of them
# did - including the innovation cutoff the entire relaxation measurement hinges
# on, the four strategy weights that govern how far co-evolution can move mode
# share, and the logit scale, which had no registry field at all.
#
# There is no template now. `src/registry/param_config.py` builds the document
# from the fields that declare a `matsim_param` binding, so a parameter exists
# only if a field claims it or the caller supplies it under a declared runtime
# role. The three roles are the three things a registry cannot hold: a path on
# this machine, the city's own identity, and a value DERIVED from declared
# fields. Everything else is a leak, and `closure()` returns it.


def config_runtime(cfg, scoring, day, paths):
    """What the registry cannot hold, each entry carrying the role that justifies it.

    `scoring` is the C1 translation: MATSim scores with a Charypar-Nagel utility
    and C1 is a nested logit, so the mode constants and per-mode time rates are
    computed rather than declared. Each one names the identity that produced it,
    and the registry declares the same identity on the matching `computed` field
    - so the value is derived in one place and its provenance is recorded in
    another that a reader can find without opening a builder.
    """
    start_h, end_h = parking_window(cfg, day)
    typical = cfg.get('C.scoring.activity_typical_duration_s')
    minimal = cfg.get('C.scoring.activity_minimal_duration_s')
    runtime = {
        'global.coordinateSystem': (_city.crs(), 'identity', 'city.json crs.epsg'),
        'controler.outputDirectory': (paths['output'], 'path', 'run output'),
        'network.inputNetworkFile': (paths['network'], 'path', 'scenario run network'),
        'plans.inputPlansFile': (paths['plans'], 'path', 'day-type plans'),
        'transit.transitScheduleFile': (paths['schedule'], 'path', 'filtered schedule'),
        'transit.vehiclesFile': (paths['vehicles'], 'path', 'transit vehicles'),
        'parking.priceFile': (paths['parking_prices'], 'path', 'per-link price table'),
        # The two capacity factors are identities on the sample fraction, not
        # choices. Both registry fields are declared `computed`, so the emitter
        # REFUSES to write them from a declared value and requires them here.
        'qsim.flowCapacityFactor': (
            paths['fraction'], 'derived', 'flowCapacityFactor = RUN.sample.fraction'),
        'qsim.storageCapacityFactor': (
            paths['fraction'] ** cfg.get('RUN.sample.storage_capacity_exponent'),
            'derived', 'storageCapacityFactor = fraction ** '
                       'RUN.sample.storage_capacity_exponent'),
        # The charged parking window is one field carrying a window per day type;
        # MATSim reads two parameters. Which day this set is for is not a
        # registry value, so the selection happens here.
        'parking.chargedStartHour': (
            start_h, 'derived',
            'A.parking.charged_hours_by_day_type[%s][0]' % day),
        'parking.chargedEndHour': (
            end_h, 'derived',
            'A.parking.charged_hours_by_day_type[%s][1]' % day),
        'scoring.waitingPt': (
            scoring['waiting_pt'], 'derived',
            'performing - trip-weighted VOT * beta_wait * marginalUtilityOfMoney'),
        'scoring.utilityOfLineSwitch': (
            scoring['utility_of_line_switch'], 'derived',
            '-(C.transfer.penalty_min / 60) * trip-weighted VOT * '
            'marginalUtilityOfMoney'),
        'scoring.modeParams[*].constant': (
            {m: v['constant'] for m, v in scoring['modes'].items()},
            'derived', 'the C1 alternative-specific constant for each mode'),
        'scoring.modeParams[*].marginalUtilityOfTraveling_util_hr': (
            {m: v['marginalUtilityOfTraveling'] for m, v in scoring['modes'].items()},
            'derived',
            'performing - trip-weighted VOT * beta[mode] * marginalUtilityOfMoney'),
        # Applied as min(minimal, typical): a 15-minute floor over a 5-minute
        # drop-off would be self-contradictory, and MATSim would hold the
        # vehicle there.
        'scoring.activityParams[*].minimalDuration': (
            {a: min(minimal, d) for a, d in typical.items()},
            'derived',
            'min(C.scoring.activity_minimal_duration_s, typical duration) per activity',
            _param_config.HHMMSS, 'seconds'),
    }
    return runtime


def write_config(path, cfg, scoring, day, paths):
    """Emit one scenario x day-type config, and refuse a leak."""
    runtime = config_runtime(cfg, scoring, day, paths)
    leaks = _param_config.closure('matsim', cfg, runtime)
    if leaks:
        raise SystemExit('the emitted config carries %d parameter(s) that came '
                         'from neither a registry field nor a declared runtime '
                         'role: %s' % (len(leaks), leaks))
    return _param_config.write(path, 'matsim', cfg, runtime)


def hts_purpose_share():
    import pandas as pd
    pur = pd.read_csv(_city.path('data/processed/hts/hts_purpose.csv'))
    pur = pur[pur.geography == 'lga']
    yr = sorted(pur.FINANCIAL_YEAR.unique())[-1]
    pur = pur[pur.FINANCIAL_YEAR == yr]
    pmap = {'Commute': 'HW', 'Education/childcare': 'HE', 'Shopping': 'HS',
            'Personal business': 'HO', 'Social/recreation': 'HO',
            'Serve passenger': 'NHB', 'Work related business': 'WB', 'Other': 'HO'}
    pur = pur.assign(p=pur.TRAVEL_PURPOSE.str.rstrip('*').map(pmap))
    pur = pur[pur.p.notna()]
    j = pur.groupby('p').JOURNEYS_BY_MODE.sum()
    return (j / j.sum()).to_dict()


def shipped_iterations(cfg):
    """The iteration count written into a SHIPPED config, or the refusal.

    `RUN.controler.last_iteration` is `unobtained`: 100 and 250 are both MEASURED
    to be short of relaxation and no sufficient value has been established
    (DECISIONS.md 9.7). This builder used to supply 100 from an argparse default,
    which walked straight past the resolver's refusal and shipped the known-wrong
    number into all thirty configs.

    It no longer invents one. A shipped config carries the LOWER BOUND OF THE
    DECLARED SWEEP, which is the largest value measured to be insufficient - so
    a config run directly, outside the harness, is short rather than plausible.
    The harness resolves the real value per run and re-emits.
    """
    sweep = cfg.sweep('RUN.controler.last_iteration')
    interval = sweep['interval'] if isinstance(sweep, dict) else sweep
    return int(interval[0])


def main(day_types=None, scenarios=None, set_overrides=None):
    day_types = day_types or DAY_TYPES
    os.makedirs(OUT, exist_ok=True)
    c1 = json.load(open(PARAMS, encoding='utf-8'))
    purpose_share = hts_purpose_share()

    rows = list(csv.DictReader(open(E1, encoding='utf-8')))
    if scenarios:
        rows = [r for r in rows if r['scenario_id'] in scenarios]

    patch_rows = list(csv.DictReader(open(PATCHES, encoding='utf-8')))
    by_variant = collections.defaultdict(dict)
    for p in patch_rows:
        by_variant[p['road_variant_ref']][p['edge_id'][1:]] = p
    road_variants = {r['road_variant_ref']: r for r in
                     csv.DictReader(open(_city.path('scenarios/E1_road_variants.csv'),
                                         encoding='utf-8'))}

    # The shipped configs carry the sweep's lower bound, set EXPLICITLY through
    # the resolver rather than substituted past it, so `_config.json` records
    # where the number came from and the value is checked against its own
    # declared range like any other.
    shipped = {'RUN.controler.last_iteration':
               shipped_iterations(_registry.load(strict=True))}
    shipped.update(set_overrides or {})

    # Recorded so the HARNESS can recompute the C1 translation against its own
    # resolution without re-reading the HTS. Without this the derived scoring
    # would be frozen at build time, and a run overlay moving the transfer
    # penalty - the field deliverable 8 sweeps 3-15 min - would not move
    # utilityOfLineSwitch, which is the only parameter it acts through.
    report = dict(scenarios={}, purpose_share=purpose_share)
    for r in rows:
        sid = r['scenario_id']
        sched_dir = os.path.join(MATSIM, 'schedules', sid)
        if not os.path.isdir(sched_dir):
            print('   %-5s SKIP - no mapped schedule' % sid, flush=True)
            continue
        ref = r['road_variant_ref']
        pat = by_variant.get(ref, {})
        drop = road_variants.get(ref, {}).get('banned_turn_movements') == '0'
        net_dst = os.path.join(OUT, sid, 'network.xml.gz')
        touched = patch_network(os.path.join(sched_dir, 'network.xml.gz'),
                                net_dst, pat, drop)
        price_dst = os.path.join(OUT, sid, PARK_PRICE_FILE)
        parking = write_parking_prices(net_dst, price_dst)
        entry = dict(road_variant=ref, patch_rows=len(pat),
                     links_touched=touched, parking=parking, days={})
        for d in day_types:
            # RESOLVED PER SCENARIO AND DAY TYPE. The scenario and day overlays
            # are layers of the registry, so S2b's signal priority and Sunday's
            # parking window are properties of THIS resolution rather than
            # arguments threaded through a template.
            cfg = _registry.load(scenario=sid, day=d, set=shipped)
            check_scoring_order(cfg)
            scoring = scoring_from_c1(cfg, c1, purpose_share)
            dst = os.path.join(OUT, sid, d)
            counts = split_schedule(sched_dir, dst, d, cfg)
            paths = dict(
                output='output',
                network=os.path.relpath(net_dst, dst).replace('\\', '/'),
                plans=os.path.relpath(os.path.join(PLANS, 'population_%s.xml.gz' % d),
                                      dst).replace('\\', '/'),
                schedule='transitSchedule.xml.gz',
                vehicles='transitVehicles.xml.gz',
                parking_prices=os.path.relpath(price_dst, dst).replace('\\', '/'),
                fraction=cfg.get('RUN.sample.fraction'))
            write_config(os.path.join(dst, 'config.xml'), cfg, scoring, d, paths)
            entry['days'][d] = counts
            report.setdefault('scoring', scoring)
        report['scenarios'][sid] = entry
        print('   %-5s %-38s %s | parking %d/%d links priced' % (sid, ref,
              ' '.join('%s:%d routes/%d dep' % (d, v['routes_kept'], v['departures'])
                       for d, v in sorted(entry['days'].items())),
              parking['priced_links'], parking['car_links']), flush=True)

    if 'scoring' in report:
        print('scoring: VOT %.2f AUD/h (trip-weighted), performing %.1f utils/h'
              % (report['scoring']['vot_aud_hr_used'],
                 report['scoring']['performing_utils_per_h']), flush=True)
        for line in report['scoring']['not_representable']:
            print('   does not survive translation: %s' % line, flush=True)

    json.dump(report, open(os.path.join(OUT, '_run_inputs_report.json'), 'w'),
              indent=2)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # NO VALUE DEFAULTS. --seed, --iterations, --capacity-factor, --plan-memory
    # and --threads all used to sit here with a number beside them, and every
    # one of those numbers was a registry field being supplied past the
    # resolver. `--iterations 100` was the worst: the registry declares that
    # field UNOBTAINED because 100 is MEASURED to be too low, and this default
    # shipped it into all thirty configs anyway. Vary a value with --set, which
    # is checked against the field's declared sweep.
    ap.add_argument('--day-types', default=','.join(DAY_TYPES))
    ap.add_argument('--scenarios', default='')
    ap.add_argument('--set', action='append', default=[], metavar='KEY=VALUE',
                    help='registry override, e.g. RUN.machine.threads=8. Checked '
                         'against the declared sweep like any other layer')
    a = ap.parse_args()
    main([d for d in a.day_types.split(',') if d],
         [s for s in a.scenarios.split(',') if s] or None,
         _registry.parse_set(a.set))
