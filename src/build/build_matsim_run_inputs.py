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
import os
import re
import csv
import gzip
import json
import shutil
import argparse
import collections
import xml.etree.ElementTree as ET

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from det_io import gzip_writer

MATSIM = 'networks/matsim'
PATCHES = 'data/processed/network/A1_road_variant_patches.csv'
E1 = 'scenarios/E1_scenarios.csv'
PARAMS = 'params/C1_parameters.json'
PLANS = 'demand/plans/matsim'
OUT = 'scenarios/matsim'
DAY_TYPES = ['WEEKDAY', 'SAT', 'SUN']

# MATSim's opportunity cost of time, utils per hour. Conventional value; the
# whole scoring scale is relative to it. Assumed, and **not Newcastle-specific**:
# it is a property of the scoring formulation, not of this study area, so there
# is nothing local to derive it from. Swept.
PERFORMING_UTILS_PER_H = 6.0
PERFORMING_SWEEP = (4.0, 8.0)
MARGINAL_UTILITY_OF_MONEY = 1.0        # utils per AUD, definitional anchor

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


def split_schedule(src_dir, dst_dir, day):
    """Filter a mapped schedule to one day type. No re-mapping, ever.

    Returns counts so the caller can assert that link sequences were copied
    rather than regenerated.
    """
    os.makedirs(dst_dir, exist_ok=True)
    with gzip.open(os.path.join(src_dir, 'transitSchedule.xml.gz'), 'rb') as f:
        tree = ET.parse(f)
    root = tree.getroot()

    kept_routes = dropped_routes = 0
    kept_dep = 0
    vehicles_used = set()
    stops_served = set()
    for line in list(root.findall('transitLine')):
        for route in list(line.findall('transitRoute')):
            rid = route.get('id', '')
            if day_of_route(rid) != day:
                line.remove(route)
                dropped_routes += 1
                continue
            kept_routes += 1
            for stop in route.findall('./routeProfile/stop'):
                stops_served.add(stop.get('refId'))
            for dep in route.findall('./departures/departure'):
                kept_dep += 1
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
    out_veh = os.path.join(dst_dir, 'transitVehicles.xml.gz')
    with gzip_writer(out_veh, text=False) as f:
        vtree.write(f, encoding='utf-8', xml_declaration=True)

    return dict(routes_kept=kept_routes, routes_dropped=dropped_routes,
                departures=kept_dep, vehicles=kept_veh,
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


def scoring_from_c1(c1, purpose_share):
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
    perf = PERFORMING_UTILS_PER_H
    mm = MARGINAL_UTILITY_OF_MONEY

    def traveling(weight):
        return round(perf - vot_avg * weight * mm, 4)

    modes = {
        'car': dict(constant=asc['asc_car_driver'][0],
                    marginalUtilityOfTraveling=traveling(1.0)),
        'ride': dict(constant=asc['asc_car_passenger'][0],
                     marginalUtilityOfTraveling=traveling(1.0)),
        'pt': dict(constant=asc['asc_bus'][0],
                   marginalUtilityOfTraveling=traveling(w['beta_ivt']['base'])),
        'walk': dict(constant=asc['asc_walk'][0],
                     marginalUtilityOfTraveling=traveling(w['beta_walk_access']['base'])),
        'bike': dict(constant=asc['asc_cycle'][0],
                     marginalUtilityOfTraveling=traveling(1.3)),
    }
    tp = c1['transfer_penalty']['base']
    return dict(
        performing_utils_per_h=perf,
        performing_sweep=list(PERFORMING_SWEEP),
        monetary_distance_rate=MONETARY_DISTANCE_RATE,
        monetary_distance_rate_sweep=list(MONETARY_DISTANCE_RATE_SWEEP),
        strategies=dict(STRATEGIES),
        subtour_mode_choice_weight_sweep=list(SUBTOUR_MODE_CHOICE_WEIGHT_SWEEP),
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
        ])


# MATSim defaults its output compression to zst. gzip is set instead so the
# analysis reads run outputs with the standard library alone - the repo pins a
# JVM, pt2matsim and SUMO by digest and declares no Python dependency beyond
# pandas/numpy, and an undeclared `zstandard` would be a reproducibility hole
# that only shows up on a machine that happens not to have it.
CONFIG = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE config SYSTEM "http://www.matsim.org/files/dtd/config_v2.dtd">
<config>
\t<module name="global">
\t\t<param name="coordinateSystem" value="EPSG:28356" />
\t\t<param name="randomSeed" value="{seed}" />
\t\t<param name="numberOfThreads" value="{threads}" />
\t</module>
\t<module name="network">
\t\t<param name="inputNetworkFile" value="{network}" />
\t</module>
\t<module name="plans">
\t\t<param name="inputPlansFile" value="{plans}" />
\t</module>
\t<module name="transit">
\t\t<param name="useTransit" value="true" />
\t\t<param name="transitScheduleFile" value="{schedule}" />
\t\t<param name="vehiclesFile" value="{vehicles}" />
\t\t<param name="transitModes" value="pt" />
\t</module>
\t<module name="controler">
\t\t<param name="outputDirectory" value="{output}" />
\t\t<param name="firstIteration" value="0" />
\t\t<param name="lastIteration" value="{iterations}" />
\t\t<param name="writeEventsInterval" value="{write_interval}" />
\t\t<param name="writePlansInterval" value="{write_interval}" />
\t\t<param name="overwriteFiles" value="failIfDirectoryExists" />
\t\t<param name="compressionType" value="gzip" />
\t</module>
\t<module name="qsim">
\t\t<param name="startTime" value="00:00:00" />
\t\t<param name="endTime" value="30:00:00" />
\t\t<param name="flowCapacityFactor" value="{capacity_factor}" />
\t\t<param name="storageCapacityFactor" value="{capacity_factor}" />
\t\t<param name="numberOfThreads" value="{threads}" />
\t\t<param name="mainMode" value="car" />
\t\t<param name="snapshotperiod" value="00:00:00" />
\t\t<param name="vehiclesSource" value="defaultVehicle" />
\t</module>
\t<module name="scoring">
\t\t<param name="learningRate" value="1.0" />
\t\t<param name="BrainExpBeta" value="1.0" />
\t\t<param name="marginalUtilityOfMoney" value="{money}" />
\t\t<param name="performing" value="{performing}" />
\t\t<param name="lateArrival" value="-18.0" />
\t\t<param name="earlyDeparture" value="0.0" />
\t\t<param name="waiting" value="0.0" />
\t\t<param name="waitingPt" value="{waiting_pt}" />
\t\t<param name="utilityOfLineSwitch" value="{line_switch}" />
{activities}
{modes}
\t</module>
\t<module name="replanning">
\t\t<param name="maxAgentPlanMemorySize" value="{plan_memory}" />
\t\t<param name="fractionOfIterationsToDisableInnovation" value="0.8" />
{strategies}
\t</module>
\t<module name="subtourModeChoice">
\t\t<param name="modes" value="car,ride,pt,bike,walk" />
\t\t<param name="chainBasedModes" value="car,bike" />
\t\t<param name="considerCarAvailability" value="true" />
\t\t<param name="behavior" value="fromSpecifiedModesToSpecifiedModes" />
\t</module>
\t<module name="travelTimeCalculator">
\t\t<param name="separateModes" value="false" />
\t\t<param name="analyzedModes" value="car" />
\t</module>
\t<module name="routing">
\t\t<param name="networkModes" value="car,ride" />
\t\t<parameterset type="teleportedModeParameters">
\t\t\t<param name="mode" value="walk" />
\t\t\t<param name="teleportedModeSpeed" value="1.05" />
\t\t\t<param name="beelineDistanceFactor" value="1.3" />
\t\t</parameterset>
\t\t<parameterset type="teleportedModeParameters">
\t\t\t<param name="mode" value="bike" />
\t\t\t<param name="teleportedModeSpeed" value="4.2" />
\t\t\t<param name="beelineDistanceFactor" value="1.3" />
\t\t</parameterset>
\t</module>
</config>
"""

ACTIVITY_BLOCK = """\t\t<parameterset type="activityParams">
\t\t\t<param name="activityType" value="{name}" />
\t\t\t<param name="typicalDuration" value="{duration}" />
\t\t\t<param name="minimalDuration" value="00:15:00" />
\t\t</parameterset>"""

MODE_BLOCK = """\t\t<parameterset type="modeParams">
\t\t\t<param name="mode" value="{mode}" />
\t\t\t<param name="constant" value="{constant}" />
\t\t\t<param name="marginalUtilityOfTraveling_util_hr" value="{traveling}" />
\t\t\t<param name="monetaryDistanceRate" value="{money_rate}" />
\t\t</parameterset>"""

STRATEGY_BLOCK = """\t\t<parameterset type="strategysettings">
\t\t\t<param name="strategyName" value="{name}" />
\t\t\t<param name="weight" value="{weight}" />
\t\t\t<param name="subpopulation" value="{subpop}" />
\t\t</parameterset>"""

# Per-km running cost seen by the traveller, AUD. Assumed: fuel and tyres only,
# not standing costs, because a mode-choice decision does not re-decide car
# ownership within the day.
MONETARY_DISTANCE_RATE = {'car': -0.00018, 'ride': 0.0,
                          'pt': 0.0, 'walk': 0.0, 'bike': 0.0}
# AUD/m for car. Fuel and tyres vary with national prices, not with Newcastle,
# so this is swept rather than localised.
MONETARY_DISTANCE_RATE_SWEEP = (-0.00025, -0.00012)
# `ride` was charged half the car rate. That half was typed in, not derived, and
# it double-charges: a vehicle's operating cost is paid once, and the observed
# Newcastle occupancy is 1.3503 persons per vehicle (params/C4_mode_constraints
# .json, HTS, seven survey years). Charging the driver 0.00018 and the passenger
# 0.00009 makes the model's aggregate vehicle operating cost about 1.35x the
# real one. The only value derivable from the data is zero: the driver, who is
# separately modelled, already carries it.
#
# This makes `ride` free at the margin and therefore moves the whole burden of
# pinning its share onto asc_car_passenger, which is then constrained to
# reproduce the observed occupancy. That is deliberate and is stated rather than
# hidden: see DECISIONS.md 9.8.

STRATEGIES = [('ChangeExpBeta', 0.70), ('ReRoute', 0.15),
              ('SubtourModeChoice', 0.10), ('TimeAllocationMutator', 0.05)]
# The mode-choice innovation weight is the one that matters for how far the
# co-evolution can move mode share; swept. Not Newcastle-specific.
SUBTOUR_MODE_CHOICE_WEIGHT_SWEEP = (0.05, 0.20)

TYPICAL_DURATION_S = {'home': 12 * 3600, 'work': 8 * 3600, 'education': 6 * 3600,
                      'shopping': 1 * 3600, 'other': 2 * 3600, 'business': 1 * 3600}


def hhmmss(s):
    s = int(s)
    return '%02d:%02d:%02d' % (s // 3600, (s % 3600) // 60, s % 60)


def hts_purpose_share():
    import pandas as pd
    pur = pd.read_csv('data/processed/hts/hts_purpose_newcastle.csv')
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


def main(seed=20260810, iterations=100, capacity_factor=1.0, plan_memory=5,
         threads=8, day_types=None, scenarios=None):
    day_types = day_types or DAY_TYPES
    os.makedirs(OUT, exist_ok=True)
    c1 = json.load(open(PARAMS, encoding='utf-8'))
    scoring = scoring_from_c1(c1, hts_purpose_share())

    rows = list(csv.DictReader(open(E1, encoding='utf-8')))
    if scenarios:
        rows = [r for r in rows if r['scenario_id'] in scenarios]

    patch_rows = list(csv.DictReader(open(PATCHES, encoding='utf-8')))
    by_variant = collections.defaultdict(dict)
    for p in patch_rows:
        by_variant[p['road_variant_ref']][p['edge_id'][1:]] = p
    road_variants = {r['road_variant_ref']: r for r in
                     csv.DictReader(open('scenarios/E1_road_variants.csv',
                                         encoding='utf-8'))}

    report = dict(seed=seed, iterations=iterations,
                  capacity_factor=capacity_factor, plan_memory=plan_memory,
                  scoring=scoring, scenarios={})
    print('scoring: VOT %.2f AUD/h (trip-weighted), performing %.1f utils/h'
          % (scoring['vot_aud_hr_used'], scoring['performing_utils_per_h']),
          flush=True)
    for line in scoring['not_representable']:
        print('   does not survive translation: %s' % line, flush=True)

    activities = '\n'.join(
        ACTIVITY_BLOCK.format(name=k, duration=hhmmss(v))
        for k, v in sorted(TYPICAL_DURATION_S.items()))
    modes = '\n'.join(
        MODE_BLOCK.format(mode=m, constant=v['constant'],
                          traveling=v['marginalUtilityOfTraveling'],
                          money_rate=MONETARY_DISTANCE_RATE.get(m, 0.0))
        for m, v in sorted(scoring['modes'].items()))
    strategies = '\n'.join(
        STRATEGY_BLOCK.format(name=n, weight=w, subpop=sp)
        for sp in ('person', 'external')
        for n, w in STRATEGIES)

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
        entry = dict(road_variant=ref, patch_rows=len(pat),
                     links_touched=touched, days={})
        for d in day_types:
            dst = os.path.join(OUT, sid, d)
            counts = split_schedule(sched_dir, dst, d)
            cfg = CONFIG.format(
                seed=seed, threads=threads,
                network=os.path.relpath(net_dst, dst).replace('\\', '/'),
                plans=os.path.relpath(os.path.join(PLANS, 'population_%s.xml.gz' % d),
                                      dst).replace('\\', '/'),
                schedule='transitSchedule.xml.gz',
                vehicles='transitVehicles.xml.gz',
                output='output', iterations=iterations,
                write_interval=max(1, iterations // 10),
                capacity_factor=capacity_factor,
                money=scoring['marginal_utility_of_money'],
                performing=scoring['performing_utils_per_h'],
                waiting_pt=scoring['waiting_pt'],
                line_switch=scoring['utility_of_line_switch'],
                activities=activities, modes=modes,
                plan_memory=plan_memory, strategies=strategies)
            with open(os.path.join(dst, 'config.xml'), 'w', encoding='utf-8',
                      newline='\n') as f:
                f.write(cfg)
            entry['days'][d] = counts
        report['scenarios'][sid] = entry
        print('   %-5s %-38s %s' % (sid, ref,
              ' '.join('%s:%d routes/%d dep' % (d, v['routes_kept'], v['departures'])
                       for d, v in sorted(entry['days'].items()))), flush=True)

    json.dump(report, open(os.path.join(OUT, '_run_inputs_report.json'), 'w'),
              indent=2)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', type=int, default=20260810)
    ap.add_argument('--iterations', type=int, default=100)
    ap.add_argument('--capacity-factor', type=float, default=1.0)
    ap.add_argument('--plan-memory', type=int, default=5)
    ap.add_argument('--threads', type=int, default=8)
    ap.add_argument('--day-types', default=','.join(DAY_TYPES))
    ap.add_argument('--scenarios', default='')
    a = ap.parse_args()
    main(a.seed, a.iterations, a.capacity_factor, a.plan_memory, a.threads,
         [d for d in a.day_types.split(',') if d],
         [s for s in a.scenarios.split(',') if s] or None)
