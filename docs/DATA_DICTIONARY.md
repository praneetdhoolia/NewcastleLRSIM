# Data dictionary

Auto-generated from the produced files by `src/build/build_data_dictionary.py`.
Column types are inferred from the first 400 rows. Schema letters refer to
Appendix A of the proposal.

## A1/A6 network

### `data/processed/network/A1_corridor_road_edges.csv`

714 rows, 27 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `edge_id` | str | w880437939 | 401/401 |
| `osm_way_id` | int | 880437939 | 401/401 |
| `name` | str | Hunter Street | 367/401 |
| `road_class` | str | secondary | 401/401 |
| `length_m` | float | 22.5 | 401/401 |
| `corridor_class` | str | corridor_trunk:base2026;corrido... | 401/401 |
| `is_corridor_trunk` | int | 1 | 401/401 |
| `dist_to_alignment_m` | float | 0.6 | 401/401 |
| `oneway_flag` | int | 1 | 401/401 |
| `oneway_source` | str | osm | 401/401 |
| `num_lanes_per_dir` | float | 1.0 | 401/401 |
| `num_lanes_source` | str | osm | 401/401 |
| `speed_limit_kmh` | int | 40.0 | 401/401 |
| `speed_limit_source` | str | osm | 401/401 |
| `lane_width_m` | float | 3.2 | 401/401 |
| `lane_width_source` | str | imputed_rule | 401/401 |
| `turn_lanes` | str | none/right | 27/401 |
| `turn_lanes_source` | str | absent | 401/401 |
| `kerbside_use` | str | unknown | 401/401 |
| `kerbside_source` | str | imputed_rule | 401/401 |
| `capacity_veh_hr_lane` | int | 1400 | 401/401 |
| `capacity_source` | str | imputed_rule | 401/401 |
| `dist_to_S2c_m` | float | 156.2 | 401/401 |
| `dist_to_S4_m` | float | 0.6 | 401/401 |
| `dist_to_S5_m` | float | 0.6 | 401/401 |
| `dist_to_base2026_m` | float | 0.6 | 401/401 |
| `scenario_variant_ref` | str | base2026 | 401/401 |

### `data/processed/network/A1_road_edges.csv`

43112 rows, 32 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `edge_id` | str | w196838798 | 401/401 |
| `from_node` | int | 1928450060 | 401/401 |
| `to_node` | int | 5731969818 | 401/401 |
| `n_nodes` | int | 158 | 401/401 |
| `length_m` | float | 16457.7 | 401/401 |
| `road_class` | str | secondary | 401/401 |
| `num_lanes` | int | 1.0 | 401/401 |
| `lane_width_m` | float | 3.2 | 401/401 |
| `speed_limit_kmh` | int | 100.0 | 401/401 |
| `oneway_flag` | int | 0 | 401/401 |
| `oneway_dir` | int | 1 | 401/401 |
| `capacity_veh_hr_lane` | int | 1400 | 401/401 |
| `kerbside_use` | str | unknown | 401/401 |
| `gradient_pct` | float | 0.513 | 401/401 |
| `bridge` | int | 0 | 401/401 |
| `tunnel` | int | 0 | 401/401 |
| `surface` | str | asphalt | 299/401 |
| `name` | str | George Downes Drive | 295/401 |
| `ref` | str | 33 | 20/401 |
| `access` | str | private | 36/401 |
| `psv` | empty |  | 0/401 |
| `turn_lanes` | str | none/right | 12/401 |
| `start_lat` | float | -33.1099066 | 401/401 |
| `start_lon` | float | 151.1357802 | 401/401 |
| `end_lat` | float | -33.2085066 | 401/401 |
| `end_lon` | float | 151.2026735 | 401/401 |
| `scenario_variant_ref` | str | base2026 | 401/401 |
| `elev_start_m` | float | 257.7 | 401/401 |
| `elev_end_m` | float | 342.2 | 401/401 |
| `elev_min_m` | float | 247.1 | 401/401 |
| `elev_max_m` | float | 374.0 | 401/401 |
| `gradient_source` | str | copernicus_glo30 | 401/401 |

### `data/processed/network/A1_road_variant_patches.csv`

414 rows, 18 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `road_variant_ref` | str | net_base2026_hunter_st_full_cap... | 401/401 |
| `edge_id` | str | w880437939 | 401/401 |
| `name` | str | Hunter Street | 401/401 |
| `corridor_class` | str | corridor_trunk:base2026;corrido... | 401/401 |
| `fields_changed` | str | num_lanes_per_dir;kerbside_use | 401/401 |
| `field_num_lanes_per_dir_from` | float | 1.0 | 401/401 |
| `field_num_lanes_per_dir_to` | float | 2.0 | 284/401 |
| `num_lanes_observed_source` | str | osm | 401/401 |
| `field_kerbside_use_from` | str | unknown | 401/401 |
| `field_kerbside_use_to` | str | parking | 401/401 |
| `kerbside_observed_source` | str | imputed_rule | 401/401 |
| `capacity_veh_hr_lane` | int | 1400 | 401/401 |
| `signal_cycle_s` | int | 100 | 401/401 |
| `tram_lane_present` | int | 0 | 401/401 |
| `source` | str | assumed | 401/401 |
| `sweep_low` | int | 1 | 401/401 |
| `sweep_high` | int | 2 | 401/401 |
| `rationale` | str | pre-tram reconstruction: road s... | 401/401 |

### `data/processed/network/A2_crossings_osm.csv`

9981 rows, 8 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `node_id` | int | 11237816045 | 401/401 |
| `lat` | float | -33.185125 | 401/401 |
| `lon` | float | 151.4779418 | 401/401 |
| `crossing` | str | unmarked | 360/401 |
| `signals` | str | no | 4/401 |
| `markings` | str | no | 317/401 |
| `island` | str | yes | 23/401 |
| `tactile_paving` | str | no | 6/401 |

### `data/processed/network/A2_signal_nodes_osm.csv`

1265 rows, 8 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `node_id` | int | 9297985434 | 401/401 |
| `lat` | float | -33.199672 | 401/401 |
| `lon` | float | 151.5227318 | 401/401 |
| `direction` | str | forward | 394/401 |
| `signal_type` | str | signal | 314/401 |
| `ped_phase_flag` | int | -1 | 401/401 |
| `button_operated` | empty |  | 0/401 |
| `name` | empty |  | 0/401 |

### `data/processed/network/A2_turn_restrictions_osm.csv`

1386 rows, 3 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `rel_id` | int | 17461964 | 401/401 |
| `restriction` | str | no_u_turn | 399/401 |
| `members` | str | way:944963514:from;way:12719485... | 401/401 |

### `data/processed/network/A2_turn_restrictions_resolved.csv`

1385 rows, 14 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `rel_id` | int | 13424022 | 401/401 |
| `restriction` | str | no_u_turn | 401/401 |
| `from_way` | int | 190524730 | 401/401 |
| `via_member` | int | 630409402 | 401/401 |
| `to_way` | int | 880437935 | 401/401 |
| `lat` | float | -32.9269158 | 401/401 |
| `lon` | float | 151.772968 | 401/401 |
| `located_by` | str | via_way | 401/401 |
| `source` | str | osm | 401/401 |
| `dist_to_base2026_m` | float | 4.2 | 401/401 |
| `dist_to_S2c_m` | float | 197.2 | 401/401 |
| `dist_to_S4_m` | float | 4.2 | 401/401 |
| `dist_to_S5_m` | float | 4.2 | 401/401 |
| `corridor_flag` | int | 1 | 401/401 |

### `data/processed/network/A5_parking_osm.csv`

7710 rows, 16 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `parking_facility_id` | str | pn4952059042 | 401/401 |
| `lat` | float | -33.1863337 | 401/401 |
| `lon` | float | 151.5563944 | 401/401 |
| `type` | str | offstreet_public | 401/401 |
| `osm_parking` | str | street_side | 113/401 |
| `capacity_spaces` | int | 1 | 43/401 |
| `capacity_source` | str | imputed | 401/401 |
| `fee` | str | no | 109/401 |
| `charge` | empty |  | 0/401 |
| `max_stay_min` | str | 2 minutes | 3/401 |
| `access` | str | private | 144/401 |
| `operator` | str | HMBA | 36/401 |
| `surface` | str | dirt | 107/401 |
| `levels` | empty |  | 0/401 |
| `name` | str | Carpark 2 | 14/401 |
| `scenario_variant_ref` | str | base2026 | 401/401 |

### `data/processed/network/A6_footway_edges.csv`

35653 rows, 33 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `footway_edge_id` | str | f79270131 | 401/401 |
| `from_node` | int | 925829188 | 401/401 |
| `to_node` | int | 1124585200 | 401/401 |
| `length_m` | float | 7406.5 | 401/401 |
| `highway` | str | track | 401/401 |
| `footway` | str | crossing | 57/401 |
| `width_m` | float | 2.5 | 401/401 |
| `surface` | str | unpaved | 401/401 |
| `lighting` | int | -1 | 401/401 |
| `shade` | int | -1 | 401/401 |
| `crossing_type` | str | unmarked | 51/401 |
| `crossing_delay_s` | empty |  | 0/401 |
| `step_free` | int | 1 | 401/401 |
| `steps` | int | 0 | 401/401 |
| `tram_track_crossing` | int | 0 | 401/401 |
| `incline` | str | up | 2/401 |
| `gradient_pct` | float | -0.943 | 401/401 |
| `bicycle` | str | yes | 10/401 |
| `foot` | str | yes | 16/401 |
| `wheelchair` | empty |  | 0/401 |
| `name` | str | Old North Road | 118/401 |
| `start_lat` | float | -33.1475902 | 401/401 |
| `start_lon` | float | 151.1005095 | 401/401 |
| `end_lat` | float | -33.2088561 | 401/401 |
| `end_lon` | float | 151.0988296 | 401/401 |
| `scenario_variant_ref` | str | base2026 | 401/401 |
| `elev_start_m` | float | 241.9 | 401/401 |
| `elev_end_m` | float | 172.0 | 401/401 |
| `elev_min_m` | float | 172.0 | 401/401 |
| `elev_max_m` | float | 241.9 | 401/401 |
| `gradient_source` | str | copernicus_glo30 | 401/401 |
| `walk_speed_factor_fwd` | float | 1.0336 | 401/401 |
| `walk_speed_factor_rev` | float | 0.9675 | 401/401 |

## A4/A2 corridor

### `data/processed/corridor/A2_signal_control_corridor.csv`

70 rows, 24 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `intersection_id` | str | NLR_SIG_01 | 70/70 |
| `osm_node_id` | str | 8229466262;11359660267;72866859... | 70/70 |
| `scats_site_id` | empty |  | 0/70 |
| `n_approach_nodes` | int | 7 | 70/70 |
| `lat` | float | -32.92452494285714 | 70/70 |
| `lon` | float | 151.7598467 | 70/70 |
| `dist_to_alignment_m` | float | 1.3 | 70/70 |
| `control_type` | str | adaptive | 70/70 |
| `cycle_time_s` | int | 110 | 70/70 |
| `cycle_time_sweep_low` | int | 80 | 70/70 |
| `cycle_time_sweep_high` | int | 140 | 70/70 |
| `n_phases` | int | 4 | 70/70 |
| `phase_split_pct` | str | 45/15/30/10 | 70/70 |
| `offset_s` | int | 0 | 70/70 |
| `coordination_group` | str | HUNTER_SCOTT | 70/70 |
| `pedestrian_phase_flag` | int | 1 | 70/70 |
| `ped_clearance_s` | int | 8 | 70/70 |
| `tsp_enabled` | int | 0 | 70/70 |
| `tsp_type` | str | green_extension+early_start | 28/70 |
| `tsp_detection_distance_m` | int | 0 | 70/70 |
| `tsp_max_extension_s` | int | 0 | 70/70 |
| `mean_delay_to_tram_s` | float | 24.8 | 70/70 |
| `source` | str | assumed | 70/70 |
| `scenario_variant_ref` | str | S2_base | 70/70 |

### `data/processed/corridor/A4_segment_runtime_decomposition.csv`

10 rows, 11 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `direction_id` | int | 0 | 10/10 |
| `from_stop` | str | Newcastle Interchange | 10/10 |
| `to_stop` | str | Honeysuckle | 10/10 |
| `distance_m` | float | 681.5 | 10/10 |
| `scheduled_runtime_s` | int | 180 | 10/10 |
| `kinematic_runtime_s` | float | 70.2 | 10/10 |
| `residual_s` | float | 109.8 | 10/10 |
| `implied_mean_speed_kmh` | float | 13.6 | 10/10 |
| `line_speed_kmh` | int | 40 | 10/10 |
| `distance_source` | str | gtfs_shape_scaled | 10/10 |
| `kinematic_source` | str | computed | 10/10 |

### `data/processed/corridor/A4_stop_dwell_model.csv`

6 rows, 15 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `stop_name` | str | Newcastle Interchange | 6/6 |
| `stop_seq` | int | 1 | 6/6 |
| `is_terminus` | int | 1 | 6/6 |
| `dwell_fixed_s` | int | 8.0 | 6/6 |
| `dwell_fixed_sweep_low` | int | 5.0 | 6/6 |
| `dwell_fixed_sweep_high` | int | 12.0 | 6/6 |
| `dwell_boarding_fn` | str | max(pax_board/0.60, pax_alight/... | 6/6 |
| `dwell_charging_s` | int | 20.0 | 6/6 |
| `dwell_charging_sweep_low` | int | 10.0 | 6/6 |
| `dwell_charging_sweep_high` | int | 35.0 | 6/6 |
| `dwell_sd_s` | int | 6.0 | 6/6 |
| `distribution_type` | str | lognormal | 6/6 |
| `layover_s` | int | 180 | 6/6 |
| `source` | str | assumed | 6/6 |
| `acquisition_route` | str | field measurement, or GTFS-Real... | 6/6 |

### `data/processed/corridor/A4_vehicle_spec.csv`

1 rows, 28 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `vehicle_type_id` | str | CAF_URBOS_100_NLR | 1/1 |
| `model` | str | CAF Urbos 100 (5-module, 100% l... | 1/1 |
| `fleet_size` | int | 6 | 1/1 |
| `fleet_numbers` | str | 2151-2156 | 1/1 |
| `length_m` | float | 32.966 | 1/1 |
| `width_m` | float | 2.65 | 1/1 |
| `mass_tonnes` | int | 45 | 1/1 |
| `capacity_seated` | int | 60 | 1/1 |
| `capacity_standing` | int | 210 | 1/1 |
| `capacity_crush` | int | 270 | 1/1 |
| `capacity_seated_source` | str | assumed | 1/1 |
| `capacity_crush_source` | str | published | 1/1 |
| `max_accel_ms2` | float | 1.2 | 1/1 |
| `max_decel_ms2` | float | 1.3 | 1/1 |
| `emergency_decel_ms2` | float | 2.8 | 1/1 |
| `max_speed_kmh` | int | 70 | 1/1 |
| `line_speed_kmh` | int | 40 | 1/1 |
| `door_count_per_side` | int | 4 | 1/1 |
| `door_width_mm` | int | 1300 | 1/1 |
| `boarding_rate_pax_s` | float | 0.6 | 1/1 |
| `alighting_rate_pax_s` | float | 0.8 | 1/1 |
| `traction_voltage_v` | int | 750 | 1/1 |
| `energy_storage` | str | supercapacitor (ACR) | 1/1 |
| `charging_mode` | str | pantograph raise to overhead AC... | 1/1 |
| `accel_source` | str | assumed | 1/1 |
| `door_source` | str | assumed | 1/1 |
| `boarding_rate_source` | str | assumed | 1/1 |
| `notes` | str | Wire-free between stops; 750 V ... | 1/1 |

## A3 schedule extras

### `data/processed/schedule_extras/A3_route_extras.csv`

290 rows, 10 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `route_id` | str | nisc001:3000_10X | 290/290 |
| `mode` | str | other | 290/290 |
| `route_short_name` | str | 10X | 288/290 |
| `route_long_name` | str | Charlestown to Newcastle Interc... | 290/290 |
| `vehicle_type_id` | str | BUS_RIGID_12M | 290/290 |
| `contract_area` | str | NISC 1 | 290/290 |
| `franchise_operator` | str | Keolis Downer Hunter (Newcastle... | 290/290 |
| `valid_from` | str | 2017-07-01 | 231/290 |
| `valid_to` | empty |  | 0/290 |
| `source_feed` | str | nisc001 | 290/290 |

### `data/processed/schedule_extras/A3_stop_extras.csv`

3873 rows, 16 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `stop_id` | str | nisc001:228013 | 401/401 |
| `stop_name` | str | Pacific Hwy at Docker St | 401/401 |
| `stop_lat` | float | -33.062499 | 401/401 |
| `stop_lon` | float | 151.651677 | 401/401 |
| `modes_served` | str | other | 401/401 |
| `n_routes` | int | 11 | 401/401 |
| `location_type` | empty |  | 0/401 |
| `parent_station` | empty |  | 0/401 |
| `platform_geom` | empty |  | 0/401 |
| `shelter` | int | -1 | 401/401 |
| `seating` | int | -1 | 401/401 |
| `real_time_info` | int | -1 | 401/401 |
| `step_free` | int | -1 | 401/401 |
| `platform_height_mm` | int | 0 | 401/401 |
| `interchange_group_id` | empty |  | 0/401 |
| `attribute_source` | str | assumed | 401/401 |

### `data/processed/schedule_extras/A3_transfer_extras.csv`

3584 rows, 15 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `from_stop` | str | nisc001:228013 | 401/401 |
| `to_stop` | str | nisc001:228049 | 401/401 |
| `from_name` | str | Pacific Hwy at Docker St | 401/401 |
| `to_name` | str | Pacific Hwy at Docker St | 401/401 |
| `from_modes` | str | other | 401/401 |
| `to_modes` | str | other | 401/401 |
| `straight_distance_m` | float | 72.1 | 401/401 |
| `walk_distance_m` | float | 90.1 | 401/401 |
| `walk_time_s` | float | 72.1 | 401/401 |
| `is_sheltered` | int | 0 | 401/401 |
| `requires_road_crossing` | int | 1 | 401/401 |
| `signalised_crossing_delay_s` | int | 22 | 401/401 |
| `total_transfer_time_s` | float | 94.1 | 401/401 |
| `in_interchange_group` | int | 0 | 401/401 |
| `source` | str | modelled | 401/401 |

## A5/D1 land use and parking

### `data/processed/landuse/A5_parking_facilities.csv`

7710 rows, 28 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `parking_facility_id` | str | pn4952059042 | 401/401 |
| `lat` | float | -33.1863337 | 401/401 |
| `lon` | float | 151.5563944 | 401/401 |
| `type` | str | offstreet_public | 401/401 |
| `osm_parking` | str | street_side | 113/401 |
| `capacity_spaces` | int | 60 | 401/401 |
| `capacity_source` | str | imputed_by_type | 401/401 |
| `fee` | str | no | 109/401 |
| `charge` | empty |  | 0/401 |
| `max_stay_min` | str | 2 minutes | 3/401 |
| `access` | str | private | 144/401 |
| `operator` | str | HMBA | 36/401 |
| `surface` | str | dirt | 107/401 |
| `levels` | empty |  | 0/401 |
| `name` | str | Carpark 2 | 14/401 |
| `scenario_variant_ref` | str | base2026 | 401/401 |
| `parking_zone` | str | outer_free | 401/401 |
| `is_priced` | int | 0 | 401/401 |
| `price_aud_hr` | float | 0.0 | 401/401 |
| `price_source` | str | assumed_free | 401/401 |
| `price_sweep_low` | float | 0.0 | 401/401 |
| `price_sweep_high` | float | 0.0 | 401/401 |
| `max_stay_min_modelled` | int | 0 | 401/401 |
| `price_schedule` | str | free | 401/401 |
| `occupancy_by_hour` | str | 0.10;0.08;0.07;0.06;0.08;0.14;0... | 401/401 |
| `occupancy_source` | str | assumed | 401/401 |
| `walk_time_to_frontages_s` | empty |  | 0/401 |
| `year` | int | 2026 | 401/401 |

### `data/processed/landuse/D1_buildings_cbd.csv`

10795 rows, 12 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `building_id` | str | b568088752 | 401/401 |
| `lat` | float | -32.9435821 | 401/401 |
| `lon` | float | 151.7253932 | 401/401 |
| `footprint_m2` | float | 185.0 | 401/401 |
| `levels` | int | 2 | 401/401 |
| `levels_source` | str | assumed | 401/401 |
| `gross_floor_area_m2` | float | 370.0 | 401/401 |
| `building_type` | str | yes | 401/401 |
| `shop` | str | hardware | 4/401 |
| `amenity` | str | veterinary | 4/401 |
| `name` | str | Newcastle Healthcare | 15/401 |
| `year` | int | 2026 | 401/401 |

### `data/processed/landuse/D1_employment_by_anzsic_POW_SA2.csv`

55 rows, 22 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `SA2_CODE21` | int | 106011107 | 55/55 |
| `AgFF_Tot_P` | int | 186 | 55/55 |
| `Min_Tot_P` | int | 107 | 55/55 |
| `Mnf_Tot_P` | int | 751 | 55/55 |
| `EGWWS_Tot_P` | int | 9 | 55/55 |
| `Const_Tot_P` | int | 391 | 55/55 |
| `WST_Tot_P` | int | 41 | 55/55 |
| `RetT_Tot_P` | int | 433 | 55/55 |
| `AcFd_Tot_P` | int | 1458 | 55/55 |
| `TPW_Tot_P` | int | 228 | 55/55 |
| `IMT_Tot_P` | int | 9 | 55/55 |
| `FinIns_Tot_P` | int | 33 | 55/55 |
| `RHRE_Tot_P` | int | 57 | 55/55 |
| `ProSTS_Tot_P` | int | 111 | 55/55 |
| `AdSup_Tot_P` | int | 215 | 55/55 |
| `PubAS_Tot_P` | int | 39 | 55/55 |
| `EdTrn_Tot_P` | int | 240 | 55/55 |
| `HC_SA_Tot_P` | int | 205 | 55/55 |
| `ArtsR_Tot_P` | int | 81 | 55/55 |
| `OthSvs_Tot_P` | int | 142 | 55/55 |
| `jobs_sa2` | int | 4941 | 55/55 |
| `year` | int | 2021 | 55/55 |

### `data/processed/landuse/D1_frontage_segments.csv`

498 rows, 30 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `frontage_segment_id` | str | HUNTERST_001 | 401/401 |
| `street_name` | str | Hunter Street | 401/401 |
| `corridor_role` | str | corridor | 401/401 |
| `seg_index` | int | 1 | 401/401 |
| `length_m` | float | 55.2 | 401/401 |
| `lat` | float | -32.9098307 | 401/401 |
| `lon` | float | 151.733458 | 401/401 |
| `x_mga56` | float | 381560.7 | 401/401 |
| `y_mga56` | float | 6357997.8 | 401/401 |
| `road_edge_id` | str | w29417650 | 401/401 |
| `business_count` | int | 0 | 401/401 |
| `n_retail` | int | 0 | 401/401 |
| `n_food` | int | 0 | 401/401 |
| `n_office` | int | 0 | 401/401 |
| `n_civic` | int | 0 | 401/401 |
| `n_leisure` | int | 0 | 401/401 |
| `n_health` | int | 0 | 401/401 |
| `business_categories` | str | amenity:parking | 288/401 |
| `attraction_weight_sum` | float | 0.0 | 401/401 |
| `n_buildings` | int | 0 | 401/401 |
| `gross_floor_area_m2` | float | 0.0 | 401/401 |
| `retail_floorspace_m2` | float | 0.0 | 401/401 |
| `retail_floorspace_source` | str | modelled | 401/401 |
| `active_frontage_pct` | float | 0.0 | 401/401 |
| `vacancy_rate` | empty |  | 0/401 |
| `vacancy_source` | str | not_available | 401/401 |
| `awning_coverage_pct` | empty |  | 0/401 |
| `awning_source` | str | not_available | 401/401 |
| `year` | int | 2026 | 401/401 |
| `scenario_variant_ref` | str | base2026 | 401/401 |

### `data/processed/landuse/D1_poi.csv`

23697 rows, 13 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `poi_id` | str | n2071316965 | 401/401 |
| `lat` | float | -33.1369602 | 401/401 |
| `lon` | float | 151.2033722 | 401/401 |
| `category` | str | tourism:viewpoint | 401/401 |
| `category_group` | str | tourism | 401/401 |
| `attraction_weight` | float | 1.1 | 401/401 |
| `name` | str | Great North Walk | 140/401 |
| `brand` | str | Australia Post | 33/401 |
| `opening_hours` | str | Mo-Su 07:00-22:00 | 18/401 |
| `levels` | empty |  | 0/401 |
| `in_cbd` | int | 0 | 401/401 |
| `year` | int | 2026 | 401/401 |
| `weight_source` | str | assumed | 401/401 |

### `data/processed/landuse/D1_zone_attractions_SA1.csv`

1701 rows, 30 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `SA1_CODE21` | int | 10601110701 | 401/401 |
| `SA2_CODE21` | int | 106011107 | 401/401 |
| `SA2_NAME21` | str | Branxton - Greta - Pokolbin | 401/401 |
| `zone_tier` | str | core | 401/401 |
| `area_km2` | float | 0.4799 | 401/401 |
| `x_mga56` | float | 348567.8 | 401/401 |
| `y_mga56` | float | 6384035.7 | 401/401 |
| `lon` | float | 151.3850026 | 401/401 |
| `lat` | float | -32.670974 | 401/401 |
| `population` | int | 706 | 401/401 |
| `dwellings_total` | int | 264 | 401/401 |
| `office` | int | 0.0 | 401/401 |
| `retail` | int | 0.0 | 401/401 |
| `food` | int | 0.0 | 401/401 |
| `civic` | int | 0.0 | 401/401 |
| `health` | int | 0.0 | 401/401 |
| `leisure` | int | 2.0 | 401/401 |
| `tourism` | int | 0.0 | 401/401 |
| `amenity` | int | 1.0 | 401/401 |
| `landuse` | int | 1.0 | 401/401 |
| `job_index` | float | 5.2 | 401/401 |
| `jobs_sa2` | int | 4941 | 401/401 |
| `jobs` | float | 19.1 | 401/401 |
| `jobs_source` | str | modelled_from_WPP_SA2 | 401/401 |
| `attr_HW` | float | 19.1 | 401/401 |
| `attr_HE` | float | 14.620000000000001 | 401/401 |
| `attr_HS` | float | 0.5 | 401/401 |
| `attr_HO` | int | 11.0 | 401/401 |
| `attr_WB` | int | 1.0 | 401/401 |
| `attr_NHB` | int | 1.0 | 401/401 |

## Zones

### `data/processed/zones/zone_lookup_SA1.csv`

1701 rows, 13 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `SA1_CODE21` | int | 10601110701 | 401/401 |
| `SA2_CODE21` | int | 106011107 | 401/401 |
| `SA2_NAME21` | str | Branxton - Greta - Pokolbin | 401/401 |
| `SA3_CODE21` | int | 10601 | 401/401 |
| `SA3_NAME21` | str | Lower Hunter | 401/401 |
| `SA4_CODE21` | int | 106 | 401/401 |
| `SA4_NAME21` | str | Hunter Valley exc Newcastle | 401/401 |
| `zone_tier` | str | core | 401/401 |
| `area_km2` | float | 0.4799 | 401/401 |
| `x_mga56` | float | 348567.8 | 401/401 |
| `y_mga56` | float | 6384035.7 | 401/401 |
| `lon` | float | 151.3850026 | 401/401 |
| `lat` | float | -32.670974 | 401/401 |

### `data/processed/zones/zones_DZN.csv`

265 rows, 18 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `DZN_CODE21` | int | 110306044 | 265/265 |
| `SA2_CODE21` | int | 102011030 | 265/265 |
| `SA2_NAME21` | str | Calga - Kulnura | 265/265 |
| `STE_CODE21` | int | 1 | 265/265 |
| `STE_NAME21` | str | New South Wales | 265/265 |
| `AUS_CODE21` | str | AUS | 265/265 |
| `AUS_NAME21` | str | Australia | 265/265 |
| `AREASQKM21` | float | 315.789 | 265/265 |
| `LOCI_URI21` | str | http://linked.data.gov.au/datas... | 265/265 |
| `SHAPE_Leng` | float | 1.13488504175 | 265/265 |
| `SHAPE_Area` | float | 0.0305522216241 | 265/265 |
| `area_km2` | float | 315.7635 | 265/265 |
| `x_mga56` | float | 331700.6 | 265/265 |
| `y_mga56` | float | 6319632.3 | 265/265 |
| `lon` | float | 151.1934092 | 265/265 |
| `lat` | float | -33.2491895 | 265/265 |
| `zone_tier` | str | external | 265/265 |
| `zone_id` | int | 110306044 | 265/265 |

### `data/processed/zones/zones_LGA.csv`

5 rows, 17 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `LGA_CODE21` | int | 11720 | 5/5 |
| `LGA_NAME21` | str | Cessnock | 5/5 |
| `STE_CODE21` | int | 1 | 5/5 |
| `STE_NAME21` | str | New South Wales | 5/5 |
| `AUS_CODE21` | str | AUS | 5/5 |
| `AUS_NAME21` | str | Australia | 5/5 |
| `AREASQKM21` | float | 1965.1593 | 5/5 |
| `LOCI_URI21` | str | http://linked.data.gov.au/datas... | 5/5 |
| `SHAPE_Leng` | float | 2.98220593348 | 5/5 |
| `SHAPE_Area` | float | 0.189449688154 | 5/5 |
| `area_km2` | float | 1964.9372 | 5/5 |
| `x_mga56` | float | 340987.3 | 5/5 |
| `y_mga56` | float | 6359144.3 | 5/5 |
| `lon` | float | 151.2999234 | 5/5 |
| `lat` | float | -32.8943464 | 5/5 |
| `zone_tier` | str | core | 5/5 |
| `zone_id` | int | 11720 | 5/5 |

### `data/processed/zones/zones_SA1.csv`

1701 rows, 24 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `SA1_CODE21` | int | 10601110701 | 401/401 |
| `CHG_FLAG21` | int | 0 | 401/401 |
| `CHG_LBL21` | str | No change | 401/401 |
| `SA2_CODE21` | int | 106011107 | 401/401 |
| `SA2_NAME21` | str | Branxton - Greta - Pokolbin | 401/401 |
| `SA3_CODE21` | int | 10601 | 401/401 |
| `SA3_NAME21` | str | Lower Hunter | 401/401 |
| `SA4_CODE21` | int | 106 | 401/401 |
| `SA4_NAME21` | str | Hunter Valley exc Newcastle | 401/401 |
| `GCC_CODE21` | str | 1RNSW | 401/401 |
| `GCC_NAME21` | str | Rest of NSW | 401/401 |
| `STE_CODE21` | int | 1 | 401/401 |
| `STE_NAME21` | str | New South Wales | 401/401 |
| `AUS_CODE21` | str | AUS | 401/401 |
| `AUS_NAME21` | str | Australia | 401/401 |
| `AREASQKM21` | float | 0.48 | 401/401 |
| `LOCI_URI21` | str | http://linked.data.gov.au/datas... | 401/401 |
| `area_km2` | float | 0.4799 | 401/401 |
| `x_mga56` | float | 348567.8 | 401/401 |
| `y_mga56` | float | 6384035.7 | 401/401 |
| `lon` | float | 151.3850026 | 401/401 |
| `lat` | float | -32.670974 | 401/401 |
| `zone_tier` | str | core | 401/401 |
| `zone_id` | int | 10601110701 | 401/401 |

### `data/processed/zones/zones_SA2.csv`

55 rows, 23 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `SA2_CODE21` | int | 106011107 | 55/55 |
| `SA2_NAME21` | str | Branxton - Greta - Pokolbin | 55/55 |
| `CHG_FLAG21` | int | 0 | 55/55 |
| `CHG_LBL21` | str | No change | 55/55 |
| `SA3_CODE21` | int | 10601 | 55/55 |
| `SA3_NAME21` | str | Lower Hunter | 55/55 |
| `SA4_CODE21` | int | 106 | 55/55 |
| `SA4_NAME21` | str | Hunter Valley exc Newcastle | 55/55 |
| `GCC_CODE21` | str | 1RNSW | 55/55 |
| `GCC_NAME21` | str | Rest of NSW | 55/55 |
| `STE_CODE21` | int | 1 | 55/55 |
| `STE_NAME21` | str | New South Wales | 55/55 |
| `AUS_CODE21` | str | AUS | 55/55 |
| `AUS_NAME21` | str | Australia | 55/55 |
| `AREASQKM21` | float | 392.2862 | 55/55 |
| `LOCI_URI21` | str | http://linked.data.gov.au/datas... | 55/55 |
| `area_km2` | float | 392.2113 | 55/55 |
| `x_mga56` | float | 343760.6 | 55/55 |
| `y_mga56` | float | 6379612.0 | 55/55 |
| `lon` | float | 151.3330125 | 55/55 |
| `lat` | float | -32.7101926 | 55/55 |
| `zone_tier` | str | core | 55/55 |
| `zone_id` | int | 106011107 | 55/55 |

### `data/processed/zones/zones_SA3.csv`

7 rows, 21 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `SA3_CODE21` | int | 10601 | 7/7 |
| `SA3_NAME21` | str | Lower Hunter | 7/7 |
| `CHG_FLAG21` | int | 0 | 7/7 |
| `CHG_LBL21` | str | No change | 7/7 |
| `SA4_CODE21` | int | 106 | 7/7 |
| `SA4_NAME21` | str | Hunter Valley exc Newcastle | 7/7 |
| `GCC_CODE21` | str | 1RNSW | 7/7 |
| `GCC_NAME21` | str | Rest of NSW | 7/7 |
| `STE_CODE21` | int | 1 | 7/7 |
| `STE_NAME21` | str | New South Wales | 7/7 |
| `AUS_CODE21` | str | AUS | 7/7 |
| `AUS_NAME21` | str | Australia | 7/7 |
| `AREASQKM21` | float | 8566.7812 | 7/7 |
| `LOCI_URI21` | str | http://linked.data.gov.au/datas... | 7/7 |
| `area_km2` | float | 8565.9671 | 7/7 |
| `x_mga56` | float | 331443.1 | 7/7 |
| `y_mga56` | float | 6392815.6 | 7/7 |
| `lon` | float | 151.2040267 | 7/7 |
| `lat` | float | -32.5893274 | 7/7 |
| `zone_tier` | str | external | 7/7 |
| `zone_id` | int | 10601 | 7/7 |

## HTS

### `data/processed/hts/hts_mode_newcastle.csv`

752 rows, 14 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `geography` | str | lga | 401/401 |
| `source_file` | str | hts_by_lga_2020-21_to_2024-25.xlsx | 401/401 |
| `FINANCIAL_YEAR` | str | 2024/25 | 401/401 |
| `HH_LGA_ID` | int | 1720.0 | 211/401 |
| `area_name` | str | Cessnock | 401/401 |
| `TRAVEL_MODE` | str | Other** | 401/401 |
| `TRIPS_BY_MODE` | int | 2000 | 401/401 |
| `PCT_OF_TOTAL_TRIPS` | float | 1.2 | 401/401 |
| `MODE_SHARE` | float | 1.2 | 371/401 |
| `DISTANCE_BY_MODE` | int | 3000 | 401/401 |
| `PCT_OF_TOTAL_DISTANCE` | float | 0.1 | 401/401 |
| `TRIP_AVG_DISTANCE` | float | 1.6 | 401/401 |
| `TRIP_AVG_TIME` | float | 8.2 | 401/401 |
| `HH_SA3_ID` | int | 11101.0 | 190/401 |

### `data/processed/hts/hts_purpose_newcastle.csv`

951 rows, 13 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `geography` | str | lga | 401/401 |
| `source_file` | str | hts_by_lga_2020-21_to_2024-25.xlsx | 401/401 |
| `FINANCIAL_YEAR` | str | 2024/25 | 401/401 |
| `HH_LGA_ID` | int | 1720.0 | 280/401 |
| `area_name` | str | Cessnock | 401/401 |
| `TRAVEL_PURPOSE` | str | Commute* | 401/401 |
| `JOURNEYS_BY_MODE` | int | 32000 | 401/401 |
| `PCT_OF_TOTAL_JOURNEYS` | float | 19.1 | 401/401 |
| `DISTANCE_BY_PURPOSE` | int | 861000 | 401/401 |
| `PCT_OF_TOTAL_DISTANCE` | float | 38.1 | 401/401 |
| `JOURNEY_AVG_DISTANCE` | float | 26.7 | 401/401 |
| `JOURNEY_AVG_TIME` | float | 29.9 | 401/401 |
| `HH_SA3_ID` | int | 11101.0 | 121/401 |

## Observed

### `data/processed/observed/opal_bus_newcastle_hunter.csv`

1363 rows, 4 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `Year_Month` | str | Jul-2017 | 401/401 |
| `Card_type` | str | Adult | 401/401 |
| `Contract_region` | str | NISC 1 | 401/401 |
| `Trip` | int | 109623 | 401/401 |

### `data/processed/observed/opal_lr_newcastle_by_month_cardtype.csv`

16604 rows, 4 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `Year_Month` | str | Feb-19 | 401/401 |
| `Card_type` | str | Sgl Trip LR Adult | 401/401 |
| `Line` | str | Newcastle Light Rail | 401/401 |
| `Trip` | int | 115 | 401/401 |

### `data/processed/observed/opal_lr_newcastle_by_stop.csv`

4079 rows, 4 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `Year_Month` | str | 2019-02 | 401/401 |
| `Location` | str | Civic Light Rail | 401/401 |
| `Card_type` | str | Adult | 401/401 |
| `Trip` | int | 4379 | 401/401 |

### `data/processed/observed/station_entries_exits_newcastle.csv`

1092 rows, 5 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `MonthYear` | str | 2024-10-01 00:00:00.000 | 401/401 |
| `Station` | str | Adamstown  Station | 401/401 |
| `Station_Type` | str | Train | 401/401 |
| `Entry_Exit` | str | Entry | 401/401 |
| `Trip` | int | 2618 | 401/401 |

### `data/processed/observed/traffic_aadt_newcastle.csv`

12231 rows, 27 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `the_geom` | empty |  | 0/401 |
| `cartodb_id` | int | 670961 | 401/401 |
| `the_geom_webmercator` | empty |  | 0/401 |
| `record_id` | empty |  | 0/401 |
| `station_key` | int | 56077 | 401/401 |
| `station_id` | str | 05571 | 401/401 |
| `traffic_direction_seq` | int | 0 | 401/401 |
| `traffic_direction_name` | str | COUNTER | 401/401 |
| `cardinal_direction_seq` | int | 3 | 401/401 |
| `cardinal_direction_name` | str | EAST | 401/401 |
| `classification_seq` | int | 0 | 401/401 |
| `classification_type` | str | UNCLASSIFIED | 401/401 |
| `count_type` | str | TRAFFIC COUNT | 401/401 |
| `year` | int | 2017 | 401/401 |
| `period` | str | WEEKENDS | 401/401 |
| `partial_year` | str | False | 401/401 |
| `latest_date` | empty |  | 0/401 |
| `traffic_count` | int | 10480 | 401/401 |
| `data_start_date` | empty |  | 0/401 |
| `data_end_date` | empty |  | 0/401 |
| `data_duration` | empty |  | 0/401 |
| `data_availability` | int | -1 | 401/401 |
| `data_reliability` | int | -1 | 401/401 |
| `data_quality_indicator` | int | 0 | 401/401 |
| `publish` | int | 1 | 401/401 |
| `md5` | str | 6c28805edf623dfbdc4ce7757d7f0ad0 | 401/401 |
| `updated_on` | str | 2018-01-09 22:39:10.806238+00 | 397/401 |

### `data/processed/observed/traffic_count_stations_newcastle.csv`

134 rows, 42 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `the_geom` | empty |  | 0/134 |
| `cartodb_id` | int | 5557 | 134/134 |
| `the_geom_webmercator` | empty |  | 0/134 |
| `record_id` | empty |  | 0/134 |
| `station_key` | int | 15828002 | 134/134 |
| `station_id` | str | 7211 | 134/134 |
| `name` | str | Lily Lane | 134/134 |
| `road_name` | str | Lily Lane | 134/134 |
| `full_name` | str | Lily Lane, South of Fern Circuit | 134/134 |
| `common_road_name` | str | Lily Lane | 134/134 |
| `secondary_name` | str | South of Fern Circuit | 134/134 |
| `road_name_base` | str | Lily | 134/134 |
| `road_name_type` | str | Lane | 131/134 |
| `intersection` | str | Fern Circuit | 134/134 |
| `distance_to_intersection` | int | 40 | 134/134 |
| `road_number` | int | -10 | 134/134 |
| `link_number` | int | -10 | 134/134 |
| `mab_way_type` | str | B | 87/134 |
| `mab_way_number` | int | 63.0 | 87/134 |
| `mab_identifier` | str | B63 | 87/134 |
| `road_functional_hierarchy` | str | Local Road | 134/134 |
| `road_on_type` | str | OnGround | 134/134 |
| `lane_count` | str | OneLane | 134/134 |
| `road_classification_type` | str | Lane | 131/134 |
| `road_classification_admin` | str | Local | 134/134 |
| `rms_region` | str | Hunter | 134/134 |
| `lga` | str | Newcastle | 134/134 |
| `suburb` | str | Adamstown | 134/134 |
| `post_code` | int | 2289.0 | 134/134 |
| `device_type` | str | Tirtl | 134/134 |
| `heavy_vehicle_checking_station` | str | False | 134/134 |
| `permanent_station` | int | 1 | 134/134 |
| `vehicle_classifier` | int | 1 | 134/134 |
| `lambert_easting` | int | 9740191 | 134/134 |
| `lambert_northing` | float | 4524353.5 | 134/134 |
| `wgs84_latitude` | float | -32.940571 | 134/134 |
| `wgs84_longitude` | float | 151.71312 | 134/134 |
| `direction_seq` | int | 7 | 134/134 |
| `quality_rating` | int | 5 | 134/134 |
| `publish` | str | True | 134/134 |
| `md5` | str | be6e76534a9cbe57941a6971d910a6eb | 134/134 |
| `updated_on` | str | 2018-06-12 02:48:41.978017+00 | 131/134 |

## Validation

### `data/processed/validation/bus_monthly_series.csv`

108 rows, 3 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `d` | str | 2017-07-01 | 108/108 |
| `trips` | int | 380232 | 108/108 |
| `Year_Month` | str | Jul-2017 | 108/108 |

### `data/processed/validation/lr_monthly_series.csv`

89 rows, 3 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `d` | str | 2019-02-01 | 89/89 |
| `trips` | int | 47073 | 89/89 |
| `Year_Month` | str | Feb-19 | 89/89 |

### `data/processed/validation/lr_taps_by_stop.csv`

6 rows, 2 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `Location` | str | Newcastle Interchange Light Rail | 6/6 |
| `taps` | int | 1600188 | 6/6 |

### `data/processed/validation/road_aadt_targets.csv`

119 rows, 10 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `station_key` | int | 55710 | 119/119 |
| `name` | str | Pacific Highway | 119/119 |
| `road_name` | str | Pacific Highway | 119/119 |
| `suburb` | str | Tomago | 119/119 |
| `lga` | str | Port Stephens | 119/119 |
| `lat` | float | -32.818165 | 119/119 |
| `lon` | float | 151.692841 | 119/119 |
| `aadt` | int | 33114.0 | 119/119 |
| `survey_year` | int | 2021 | 119/119 |
| `split` | str | calibration | 119/119 |

### `data/processed/validation/station_entries_exits_mean.csv`

52 rows, 3 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `Station` | str | Adamstown  Station | 52/52 |
| `Entry_Exit` | str | Entry | 52/52 |
| `Trip_num` | float | 2394.285714285714 | 52/52 |

### `data/processed/validation/validation_targets.csv`

210 rows, 9 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `target_id` | str | V001 | 210/210 |
| `metric` | str | lr_boardings_monthly_mean | 210/210 |
| `geography` | str | Newcastle Light Rail | 210/210 |
| `period` | str | 2019-03..2020-02 | 210/210 |
| `value` | float | 103892.0 | 210/210 |
| `unit` | str | boardings/month | 210/210 |
| `source` | str | TfNSW Opal Trips - Light Rail | 210/210 |
| `split` | str | calibration | 210/210 |
| `note` | str | Post-opening, pre-pandemic base... | 208/210 |

## C1 parameters

### `params/C1_behavioural_parameters.csv`

30 rows, 72 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `param_set_id` | str | C1_all_HW | 30/30 |
| `segment_id` | str | all | 30/30 |
| `segment_desc` | str | population average | 30/30 |
| `purpose` | str | HW | 30/30 |
| `vot_aud_hr` | float | 18.6 | 30/30 |
| `vot_sweep_low` | float | 13.02 | 30/30 |
| `vot_sweep_high` | float | 24.18 | 30/30 |
| `vot_source` | str | literature | 30/30 |
| `beta_cost_per_aud` | float | 3.2258 | 30/30 |
| `beta_transfer_penalty_min` | int | 8.0 | 30/30 |
| `beta_transfer_penalty_low` | int | 3.0 | 30/30 |
| `beta_transfer_penalty_high` | int | 15.0 | 30/30 |
| `beta_transfer_penalty_source` | str | assumed | 30/30 |
| `walk_decay_function` | str | negative_exponential | 30/30 |
| `walk_decay_beta_per_m` | float | 0.0018 | 30/30 |
| `walk_decay_source` | str | assumed | 30/30 |
| `nesting_structure` | str | nested_logit | 30/30 |
| `beta_ivt` | int | 1.0 | 30/30 |
| `beta_ivt_low` | int | 1.0 | 30/30 |
| `beta_ivt_high` | int | 1.0 | 30/30 |
| `beta_ivt_source` | str | definition | 30/30 |
| `beta_walk_access` | float | 2.0 | 30/30 |
| `beta_walk_access_low` | float | 1.5 | 30/30 |
| `beta_walk_access_high` | float | 2.5 | 30/30 |
| `beta_walk_access_source` | str | literature | 30/30 |
| `beta_walk_egress` | float | 2.0 | 30/30 |
| `beta_walk_egress_low` | float | 1.5 | 30/30 |
| `beta_walk_egress_high` | float | 2.5 | 30/30 |
| `beta_walk_egress_source` | str | literature | 30/30 |
| `beta_wait` | int | 2.0 | 30/30 |
| `beta_wait_low` | float | 1.5 | 30/30 |
| `beta_wait_high` | float | 2.5 | 30/30 |
| `beta_wait_source` | str | literature | 30/30 |
| `beta_headway` | float | 0.5 | 30/30 |
| `beta_headway_low` | float | 0.35 | 30/30 |
| `beta_headway_high` | float | 0.65 | 30/30 |
| `beta_headway_source` | str | literature | 30/30 |
| `beta_reliability` | float | 1.3 | 30/30 |
| `beta_reliability_low` | float | 0.8 | 30/30 |
| `beta_reliability_high` | float | 1.8 | 30/30 |
| `beta_reliability_source` | str | literature | 30/30 |
| `beta_crowding_seated` | int | 1.0 | 30/30 |
| `beta_crowding_seated_low` | int | 1.0 | 30/30 |
| `beta_crowding_seated_high` | float | 1.1 | 30/30 |
| `beta_crowding_seated_source` | str | literature | 30/30 |
| `beta_crowding_standing` | float | 1.45 | 30/30 |
| `beta_crowding_standing_low` | float | 1.15 | 30/30 |
| `beta_crowding_standing_high` | float | 1.85 | 30/30 |
| `beta_crowding_standing_source` | str | literature | 30/30 |
| `beta_gradient_uphill` | float | 0.09 | 30/30 |
| `beta_gradient_uphill_low` | float | 0.04 | 30/30 |
| `beta_gradient_uphill_high` | float | 0.15 | 30/30 |
| `beta_gradient_uphill_source` | str | assumed | 30/30 |
| `beta_gradient_downhill` | float | 0.02 | 30/30 |
| `beta_gradient_downhill_low` | int | 0.0 | 30/30 |
| `beta_gradient_downhill_high` | float | 0.05 | 30/30 |
| `beta_gradient_downhill_source` | str | assumed | 30/30 |
| `asc_car_driver` | int | 0.0 | 30/30 |
| `asc_car_driver_source` | str | definition | 30/30 |
| `asc_car_passenger` | float | -0.85 | 30/30 |
| `asc_car_passenger_source` | str | assumed | 30/30 |
| `asc_bus` | float | -1.05 | 30/30 |
| `asc_bus_source` | str | assumed | 30/30 |
| `asc_lr` | float | -0.75 | 30/30 |
| `asc_lr_source` | str | assumed | 30/30 |
| `asc_rail` | float | -0.65 | 30/30 |
| `asc_rail_source` | str | assumed | 30/30 |
| `asc_walk` | float | 0.35 | 30/30 |
| `asc_walk_source` | str | assumed | 30/30 |
| `asc_cycle` | float | -1.35 | 30/30 |
| `asc_cycle_source` | str | assumed | 30/30 |
| `source` | str | mixed | 30/30 |

### `params/C1_sensitivity_sweep_grid.csv`

140 rows, 5 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `sweep_id` | str | SW0001 | 140/140 |
| `beta_transfer_penalty_min` | float | 3.0 | 140/140 |
| `walk_decay_beta_per_m` | float | 0.001 | 140/140 |
| `dwell_charging_s` | int | 0.0 | 140/140 |
| `is_baseline` | int | 0 | 140/140 |

## E1 scenarios

### `scenarios/E1_parking_variants.csv`

2 rows, 4 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `parking_variant_ref` | str | park_2026 | 2/2 |
| `description` | str | As built: kerbside removed on t... | 2/2 |
| `onstreet_spaces_removed_corridor` | int | 210 | 2/2 |
| `source` | str | assumed | 2/2 |

### `scenarios/E1_road_variants.csv`

4 rows, 8 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `road_variant_ref` | str | net_base2026 | 4/4 |
| `description` | str | As built, with the tram in place | 4/4 |
| `hunter_st_lanes_per_direction` | int | 1 | 4/4 |
| `kerbside_parking_removed` | int | 1 | 4/4 |
| `banned_turn_movements` | int | 14 | 4/4 |
| `signal_cycle_s` | int | 110 | 4/4 |
| `tram_lane_present` | int | 1 | 4/4 |
| `source` | str | osm + assumed | 4/4 |

### `scenarios/E1_scenarios.csv`

10 rows, 23 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `base_year` | int | 2026 | 10/10 |
| `crs` | str | EPSG:28356 | 10/10 |
| `zone_system` | str | SA1 core / SA2 external | 10/10 |
| `network_variant_ref` | str | net_base2026 | 10/10 |
| `landuse_variant_ref` | str | lu_2026 | 10/10 |
| `demand_variant_ref` | str | demand_2026_seed20260810 | 10/10 |
| `params_variant_ref` | str | C1_v1 | 10/10 |
| `active_network_ref` | str | A6_base2026 | 10/10 |
| `day_types` | str | WEEKDAY/SAT/SUN | 10/10 |
| `scenario_id` | str | S0 | 10/10 |
| `label` | str | Heavy rail retained to Newcastl... | 10/10 |
| `is_counterfactual` | int | 1 | 10/10 |
| `parent_scenario_id` | str | S2 | 5/10 |
| `trunk_mode` | str | heavy_rail | 10/10 |
| `gtfs_variant_ref` | str | schedules/scenarios/S0.zip | 10/10 |
| `signal_variant_ref` | str | S0_no_tram | 10/10 |
| `parking_variant_ref` | str | park_2026_pre_lr | 10/10 |
| `road_variant_ref` | str | net_base2026_hunter_st_full_cap... | 10/10 |
| `purpose` | str | Primary counterfactual: the lin... | 10/10 |
| `notes` | str | Modernised frequency and interc... | 10/10 |
| `n_replications` | int | 30 | 10/10 |
| `seed_list` | str | 20260810;20260811;20260812;2026... | 10/10 |
| `sensitivity_grid_ref` | str | params/C1_sensitivity_sweep_gri... | 10/10 |

## B1/B2 demand

### `demand/plans/B2_activity_trips_SAT.csv`

1861017 rows, 22 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `person_id` | int | 1 | 401/401 |
| `day_type` | str | SAT | 401/401 |
| `tour_id` | int | 1 | 401/401 |
| `trip_seq` | int | 1 | 401/401 |
| `purpose` | str | HO | 401/401 |
| `tour_purpose` | str | HO | 401/401 |
| `dest_activity_type` | str | other | 401/401 |
| `origin_sa1` | int | 10601110701 | 401/401 |
| `dest_sa1` | int | 10602161507 | 401/401 |
| `origin_x` | float | 348659.1 | 401/401 |
| `origin_y` | float | 6383994.3 | 401/401 |
| `dest_x` | float | 362372.1 | 401/401 |
| `dest_y` | float | 6381129.7 | 401/401 |
| `dep_time_s` | int | 49539 | 401/401 |
| `arr_time_s` | int | 51718 | 401/401 |
| `straight_dist_km` | float | 14.009 | 401/401 |
| `activity_duration_s` | int | 4352 | 401/401 |
| `is_tour_anchor` | int | 1 | 401/401 |
| `party_size` | int | 1 | 401/401 |
| `time_flexibility_band` | str | flexible | 401/401 |
| `dest_placement` | str | poi | 401/401 |
| `agent_tier` | str | core | 401/401 |

### `demand/plans/B2_activity_trips_SUN.csv`

1575989 rows, 22 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `person_id` | int | 2 | 401/401 |
| `day_type` | str | SUN | 401/401 |
| `tour_id` | int | 1 | 401/401 |
| `trip_seq` | int | 1 | 401/401 |
| `purpose` | str | HO | 401/401 |
| `tour_purpose` | str | HO | 401/401 |
| `dest_activity_type` | str | other | 401/401 |
| `origin_sa1` | int | 10601110701 | 401/401 |
| `dest_sa1` | int | 10602161512 | 401/401 |
| `origin_x` | float | 348659.1 | 401/401 |
| `origin_y` | float | 6383994.3 | 401/401 |
| `dest_x` | float | 361001.4 | 401/401 |
| `dest_y` | float | 6380488.0 | 401/401 |
| `dep_time_s` | int | 38708 | 401/401 |
| `arr_time_s` | int | 41834 | 401/401 |
| `straight_dist_km` | float | 12.831 | 401/401 |
| `activity_duration_s` | int | 6338 | 401/401 |
| `is_tour_anchor` | int | 1 | 401/401 |
| `party_size` | int | 1 | 401/401 |
| `time_flexibility_band` | str | flexible | 401/401 |
| `dest_placement` | str | poi | 401/401 |
| `agent_tier` | str | core | 401/401 |

### `demand/plans/B2_activity_trips_WEEKDAY.csv`

2237373 rows, 22 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `person_id` | int | 1 | 401/401 |
| `day_type` | str | WEEKDAY | 401/401 |
| `tour_id` | int | 1 | 401/401 |
| `trip_seq` | int | 1 | 401/401 |
| `purpose` | str | HW | 401/401 |
| `tour_purpose` | str | HW | 401/401 |
| `dest_activity_type` | str | work | 401/401 |
| `origin_sa1` | int | 10601110701 | 401/401 |
| `dest_sa1` | int | 11102121507 | 401/401 |
| `origin_x` | float | 348659.1 | 401/401 |
| `origin_y` | float | 6383994.3 | 401/401 |
| `dest_x` | float | 370216.3 | 401/401 |
| `dest_y` | float | 6347295.1 | 401/401 |
| `dep_time_s` | int | 45533 | 401/401 |
| `arr_time_s` | int | 51666 | 401/401 |
| `straight_dist_km` | float | 42.562 | 401/401 |
| `activity_duration_s` | int | 27523 | 401/401 |
| `is_tour_anchor` | int | 1 | 401/401 |
| `party_size` | int | 1 | 401/401 |
| `time_flexibility_band` | str | fixed | 401/401 |
| `dest_placement` | str | poi | 401/401 |
| `agent_tier` | str | core | 401/401 |

### `demand/population/B1_households.csv`

245738 rows, 10 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `household_id` | int | 1 | 401/401 |
| `home_sa1` | int | 10601110701 | 401/401 |
| `home_x_mga56` | float | 348659.1 | 401/401 |
| `home_y_mga56` | float | 6383994.3 | 401/401 |
| `home_lon` | float | 151.3850026 | 401/401 |
| `home_lat` | float | -32.670974 | 401/401 |
| `household_size` | int | 2 | 401/401 |
| `household_vehicles` | int | 2 | 401/401 |
| `dwelling_type` | str | separate_house | 401/401 |
| `weight` | int | 1.0 | 401/401 |

### `demand/population/B1_synthetic_population.csv`

612668 rows, 17 columns

| column | type | example | non-empty in sample |
|---|---|---|---|
| `person_id` | int | 1 | 401/401 |
| `household_id` | int | 1 | 401/401 |
| `home_sa1` | int | 10601110701 | 401/401 |
| `age_band` | str | 45-54 | 401/401 |
| `age` | int | 48 | 401/401 |
| `sex` | str | F | 401/401 |
| `employment_status` | str | employed_part_time | 401/401 |
| `occupation_anzsco1` | str | Mach_oper_drivers | 227/401 |
| `income_band` | str | 800_999 | 401/401 |
| `licence_holder` | int | 1 | 401/401 |
| `household_vehicles` | int | 2 | 401/401 |
| `household_size` | int | 2 | 401/401 |
| `dwelling_type` | str | separate_house | 401/401 |
| `student_status` | str | none | 401/401 |
| `mobility_impairment_flag` | int | 1 | 401/401 |
| `car_available` | int | 1 | 401/401 |
| `weight` | int | 1.0 | 401/401 |
