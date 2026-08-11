#!/usr/bin/env python
"""Layer E1 - scenario configuration, binding each scenario to its variant refs.

Proposal 6.1: "Reproducibility depends entirely on this." Every scenario names
the exact network, schedule, land use, parking, signal, demand and parameter
variant it uses, plus its replication count and seed list. All scenarios share
land use, population, behavioural parameters and the non-CBD bus network by
construction - only the trunk-mode-dependent refs differ.
"""
import os
import csv
import json

# Model inputs come from config/registry/, not from literals in this file. Every
# value below carries its units, provenance and either a sweep, a held-fixed rule
# or a derived-from identity there. See DECISIONS.md 15.
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import registry as _registry  # noqa: E402
CFG = _registry.load()

OUT = 'scenarios'
os.makedirs(OUT, exist_ok=True)

N_REPLICATIONS = CFG.get('E.replication.n_replications')
BASE_SEED = 20260810

COMMON = dict(
    base_year=2026,
    crs='EPSG:28356',
    zone_system='SA1 core / SA2 external',
    network_variant_ref='net_base2026',
    landuse_variant_ref='lu_2026',
    demand_variant_ref='demand_2026_seed20260810',
    params_variant_ref='C1_v1',
    active_network_ref='A6_base2026',
    day_types='WEEKDAY|SAT|SUN',
)

SCENARIOS = [
    dict(scenario_id='S0', label='Heavy rail retained to Newcastle station',
         is_counterfactual=1, parent_scenario_id='',
         trunk_mode='heavy_rail', gtfs_variant_ref='schedules/scenarios/S0.zip',
         signal_variant_ref='S0_no_tram', parking_variant_ref='park_2026_pre_lr',
         road_variant_ref='net_base2026_hunter_st_full_capacity',
         purpose='Primary counterfactual: the line is not cut',
         notes='Modernised frequency and interchange, not the 2014 service as-is '
               '(proposal s9, counterfactual naivety). Hunter St retains the road '
               'capacity and kerbside parking that the tram removed.'),
    dict(scenario_id='S1', label='Bus shuttle from Wickham, no light rail',
         is_counterfactual=1, parent_scenario_id='',
         trunk_mode='bus_shuttle', gtfs_variant_ref='schedules/scenarios/S1.zip',
         signal_variant_ref='S0_no_tram', parking_variant_ref='park_2026_pre_lr',
         road_variant_ref='net_base2026_hunter_st_full_capacity',
         purpose='The December 2012 policy as originally announced',
         notes='10 minute headway, 8 stops, mixed traffic.'),
    dict(scenario_id='S2', label='Light rail as built (wire-free, current signals)',
         is_counterfactual=0, parent_scenario_id='',
         trunk_mode='light_rail', gtfs_variant_ref='schedules/scenarios/S2.zip',
         signal_variant_ref='S2_base', parking_variant_ref='park_2026',
         road_variant_ref='net_base2026',
         purpose='Actual. The reference case for every comparison',
         notes='Charging dwell 20 s per intermediate stop; no transit signal priority.'),
    dict(scenario_id='S2a', label='Light rail, charging dwell removed',
         is_counterfactual=1, parent_scenario_id='S2',
         trunk_mode='light_rail', gtfs_variant_ref='schedules/scenarios/S2a.zip',
         signal_variant_ref='S2_base', parking_variant_ref='park_2026',
         road_variant_ref='net_base2026',
         purpose='Isolates the wire-free decision (secondary question S-a)',
         notes='dwell_charging_s set to 0 at all stops; everything else identical to S2.'),
    dict(scenario_id='S2b', label='Light rail with full transit signal priority',
         is_counterfactual=1, parent_scenario_id='S2',
         trunk_mode='light_rail', gtfs_variant_ref='schedules/scenarios/S2b.zip',
         signal_variant_ref='S2b_full_tsp', parking_variant_ref='park_2026',
         road_variant_ref='net_base2026',
         purpose='Isolates signal priority (secondary question S-b)',
         notes='Green extension plus early start at all 14 corridor intersections; '
               '75 per cent of tram signal delay removed.'),
    dict(scenario_id='S2c', label='Light rail on the Option A alignment',
         is_counterfactual=1, parent_scenario_id='S2',
         trunk_mode='light_rail', gtfs_variant_ref='schedules/scenarios/S2c.zip',
         signal_variant_ref='S2c_reserved_alignment', parking_variant_ref='park_2026_pre_lr',
         road_variant_ref='net_base2026_hunter_st_full_capacity',
         purpose='The route with plurality public support that was not selected',
         notes='Reserved former-railway alignment: 60 km/h line speed, few at-grade '
               'conflicts, and Hunter Street keeps its road capacity.'),
    dict(scenario_id='S3', label='Bus rapid transit on the same alignment',
         is_counterfactual=1, parent_scenario_id='',
         trunk_mode='brt', gtfs_variant_ref='schedules/scenarios/S3.zip',
         signal_variant_ref='S3_brt_priority', parking_variant_ref='park_2026',
         road_variant_ref='net_base2026',
         purpose='The alternative the 2020 Strategic Business Case later favoured',
         notes='Same 6 stops and same lane take as the tram; 7.5 minute headway.'),
    dict(scenario_id='S4', label='Light rail extended to Broadmeadow',
         is_counterfactual=1, parent_scenario_id='S2',
         trunk_mode='light_rail', gtfs_variant_ref='schedules/scenarios/S4.zip',
         signal_variant_ref='S2_base', parking_variant_ref='park_2026',
         road_variant_ref='net_base2026_broadmeadow_extension',
         purpose='Trunk-length hypothesis (secondary question S-c)',
         notes='Adds Hamilton and Broadmeadow; corridor length rises from 2.7 to 5.2 km.'),
    dict(scenario_id='S5', label='Light rail to Broadmeadow and John Hunter Hospital',
         is_counterfactual=1, parent_scenario_id='S4',
         trunk_mode='light_rail', gtfs_variant_ref='schedules/scenarios/S5.zip',
         signal_variant_ref='S2_base', parking_variant_ref='park_2026',
         road_variant_ref='net_base2026_jhh_extension',
         purpose='Upper bound of the plausible network',
         notes='Adds Lambton and John Hunter Hospital; corridor length about 9.5 km.'),
    dict(scenario_id='S6', label='No trunk mode; walk, cycle and local bus only',
         is_counterfactual=1, parent_scenario_id='',
         trunk_mode='none', gtfs_variant_ref='schedules/scenarios/S6.zip',
         signal_variant_ref='S0_no_tram', parking_variant_ref='park_2026_pre_lr',
         road_variant_ref='net_base2026_hunter_st_full_capacity',
         purpose='Lower bound',
         notes='Light rail removed and not replaced.'),
]

# Road-space externality. Proposal 3.3 / s9: a simulation that models the tram
# without modelling the lane loss, banned turns, kerbside removal and signal
# cycle changes will report a spurious gain. These are the deltas each road
# variant applies to the Hunter/Scott corridor edges relative to net_base2026.
ROAD_VARIANTS = [
    dict(road_variant_ref='net_base2026', description='As built, with the tram in place',
         hunter_st_lanes_per_direction=1, kerbside_parking_removed=1,
         banned_turn_movements=14, signal_cycle_s=110, tram_lane_present=1,
         source='osm + assumed'),
    dict(road_variant_ref='net_base2026_hunter_st_full_capacity',
         description='Hunter/Scott St without the tram: lane and kerbside restored',
         hunter_st_lanes_per_direction=2, kerbside_parking_removed=0,
         banned_turn_movements=0, signal_cycle_s=100, tram_lane_present=0,
         source='assumed'),
    dict(road_variant_ref='net_base2026_broadmeadow_extension',
         description='As built plus lane take on Hunter/Tudor St to Broadmeadow',
         hunter_st_lanes_per_direction=1, kerbside_parking_removed=1,
         banned_turn_movements=22, signal_cycle_s=110, tram_lane_present=1,
         source='assumed'),
    dict(road_variant_ref='net_base2026_jhh_extension',
         description='As built plus lane take to Broadmeadow and John Hunter Hospital',
         hunter_st_lanes_per_direction=1, kerbside_parking_removed=1,
         banned_turn_movements=30, signal_cycle_s=110, tram_lane_present=1,
         source='assumed'),
]

PARKING_VARIANTS = [
    dict(parking_variant_ref='park_2026', description='As built: kerbside removed on the corridor',
         onstreet_spaces_removed_corridor=210, source='assumed'),
    dict(parking_variant_ref='park_2026_pre_lr',
         description='Corridor kerbside parking retained (no tram)',
         onstreet_spaces_removed_corridor=0, source='assumed'),
]


def main():
    rows = []
    for s in SCENARIOS:
        r = dict(COMMON)
        r.update(s)
        r['n_replications'] = N_REPLICATIONS
        r['seed_list'] = ';'.join(str(BASE_SEED + i) for i in range(N_REPLICATIONS))
        r['sensitivity_grid_ref'] = 'params/C1_sensitivity_sweep_grid.csv'
        rows.append(r)
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with open(os.path.join(OUT, 'E1_scenarios.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    for name, data in [('E1_road_variants.csv', ROAD_VARIANTS),
                       ('E1_parking_variants.csv', PARKING_VARIANTS)]:
        c = list(dict.fromkeys(k for r in data for k in r))
        with open(os.path.join(OUT, name), 'w', newline='', encoding='utf-8') as fh:
            w = csv.DictWriter(fh, fieldnames=c)
            w.writeheader()
            w.writerows(data)
    # one JSON config per scenario, the form the run harness consumes
    for r in rows:
        d = dict(r)
        d['seed_list'] = [int(x) for x in d['seed_list'].split(';')]
        json.dump(d, open(os.path.join(OUT, '%s.json' % r['scenario_id']), 'w'), indent=2)
    print('wrote %d scenario configs to %s' % (len(rows), OUT))
    for r in rows:
        print('  %-4s %-52s trunk=%-11s gtfs=%s'
              % (r['scenario_id'], r['label'][:52], r['trunk_mode'],
                 os.path.basename(r['gtfs_variant_ref'])))


if __name__ == '__main__':
    main()
