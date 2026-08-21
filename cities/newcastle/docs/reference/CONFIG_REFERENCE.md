# Configuration reference

**Generated from `cities/<city>/registry/` by `src/registry/render_docs.py`. Do not edit by hand** - edit the registry and regenerate, or the two will disagree and `check_package.py` will say so.

Every value the model consumes that is not read from an immutable raw download is declared here with its units, its provenance, and either a sweep range or an explicit rule holding it fixed. That is proposal 8.1 - *"every parameter chosen without direct empirical support must be recorded with its rationale and its sweep range"* - enforced as a schema constraint rather than a convention.

## How to control any of it

```bash
# a run overlay - the committed way to vary a run
cp cities/<city>/overlays/runs/example.json cities/<city>/overlays/runs/my_run.json
python src/run/run_matsim.py --scenario S2 --day WEEKDAY --run-config my_run

# a one-off override, checked against the same rules
python src/run/run_matsim.py --scenario S2 --day WEEKDAY \
    --set RUN.sample.fraction=0.10 --set RUN.controler.last_iteration=500

# or from the environment
CITYSIM_RUN_SAMPLE_FRACTION=0.10 python src/run/run_matsim.py --scenario S2 ...
```

Resolution order, lowest precedence first: `cities/<city>/registry/*.json` -> `overlays/scenarios/<S>.json` -> `overlays/day/<DAY>.json` -> `overlays/runs/<tag>.json` -> `CITYSIM_*` environment -> `--set`. The resolved snapshot is written into every run directory as `_config.json`, so a result always carries the exact inputs that produced it.

Three things are refused at every layer:

1. **An unobtained input cannot acquire a point value by being read.** `get()` raises; the caller must select a sweep member explicitly.
2. **An overlay cannot invent a field.** A key that is not already declared is rejected.
3. **A value cannot silently leave its sweep, and a held-fixed value cannot move at all.** Escaping a range requires `allow_outside_sweep` plus a written justification in a committed overlay - never a flag typed at a shell.

## What the 334 fields are made of

| Provenance | Fields | Meaning |
|---|---:|---|
| `observed` | 4 | read directly from a raw download |
| `measured` | 22 | computed from observed data in this package |
| `derived` | 27 | follows from another registry field by identity |
| `literature` | 40 | a published value, not specific to this city |
| `assumed` | 136 | chosen without direct empirical support |
| `definition` | 105 | fixed by the formulation, not an empirical quantity |

| Status | Fields | Meaning |
|---|---:|---|
| `active` | 314 | usable point value |
| `computed` | 10 | written at run time from other fields; do not hand-edit |
| `placeholder` | 5 | a structural stand-in; the model runs but the field is not defensible |
| `unobtained` | 5 | the datum does not exist in the package; must be swept, never pinned |

### The 5 fields with no value

These carry `value: null` and the resolver refuses to return a point value for them. They are the project's honest edge: what it does not know, declared rather than guessed.

| Field | Sweep | Why it has no value |
|---|---|---|
| `A.lightrail.dwell_charging_s` | 10 - 35 | NOT MEASURED - a few hours of field observation at Civic or Crown Street would resolve it (DECISIONS.md 13 priority 2) |
| `A.signals.scats_phasing` | `proxy_no_priority`, `proxy_partial_priority`, `proxy_full_priority` | NOT OBTAINED - a formal TfNSW request is outstanding |
| `B.opal.journey_linked` | `tap_sequence_matching_model` | NOT OBTAINED - a formal TfNSW request is outstanding |
| `D.retail.vacancy_rate` | 0 - 0.25 | NOT OBTAINED and not currently consumed by any metric |
| `RUN.sumo.replications` | 5 - 30 | NO VALUE: proposal 5.2 asks for at least 30, DECISIONS.md 9.5 shows the specified load does not fit on this machine, and nobody has decided what to cu |

### The 12 fields held fixed

Not tunable. DECISIONS.md 8.5 holds the mode constants fixed because calibrating them would fit away the effect under test - proposal 9 names ASC absorption as the primary threat to validity.

- `A.signals.scats_match_radius_m` - A data-join tolerance, not a model parameter. It decides which observed TfNSW signal is the same physical intersection as a clustered OSM one, and no behaviour, run time or score r
- `A.transit.ferry_capacity_seated` - Published seated capacity, held on the same reasoning as the total: it is a fact about the vessel. This is the ONLY vehicle in the fleet whose seated/standing split is published - 
- `A.transit.ferry_capacity_total` - A published vessel capacity is a fact about the boat, not a behavioural parameter, and sweeping it would assert an uncertainty that does not exist. Both Stockton ferries carry the 
- `B.freight.length_m` - Cosmetic in the queue model: MATSim's qsim consumes road space and flow through passengerCarEquivalents (B.freight.pce), not through vehicle length, so no output varies across this
- `B.motorbike.length_m` - Cosmetic in the queue model: MATSim's qsim consumes road space and flow through passengerCarEquivalents (B.motorbike.pce), not through vehicle length, so no output varies across th
- `C.asc.bus` - DECISIONS.md 8.5: these are priors for the first calibration pass only and must not be freely calibrated. Either estimate them on the pre-intervention period (era 3, 2018) and hold
- `C.asc.car_passenger` - Constrained, not calibrated. DECISIONS.md 9.8 solves this constant so the modelled ride:car leg ratio reproduces the OBSERVED passenger:driver ratio (0.3503, HTS). That is the seco
- `C.asc.cycle` - Constrained, not calibrated - the second branch DECISIONS.md 8.5 permits. THE DEPARTURE IS LOGGED AT 9.28, before any run on the changed specification. The shipped -1.35 stays as t
- `C.asc.light_rail` - DECISIONS.md 8.5: these are priors for the first calibration pass only and must not be freely calibrated. Either estimate them on the pre-intervention period (era 3, 2018) and hold
- `C.asc.rail` - DECISIONS.md 8.5: these are priors for the first calibration pass only and must not be freely calibrated. Either estimate them on the pre-intervention period (era 3, 2018) and hold
- `C.asc.walk` - DECISIONS.md 8.5: these are priors for the first calibration pass only and must not be freely calibrated. Either estimate them on the pre-intervention period (era 3, 2018) and hold
- `E.coupling.outer_loop_tolerance_s` - A convergence tolerance is a numerical control, not a quantity of Newcastle: it decides how many outer-loop iterations are paid for, not what the answer is, PROVIDED it stays well 

## Network supply (A1-A6)

*`cities/newcastle/registry/A_supply.json` - 94 fields*

Road graph, signal control, transit supply, light rail vehicle and dwell, parking and the active network. Two of the three inputs the proposal named as critical and unobtained live here - A.signals.scats_phasing and A.lightrail.dwell_charging_s - and both carry status 'unobtained' with a null value, so the resolver refuses to hand back a point value and the caller must select a sweep member. That is DECISIONS.md 0 and 13 enforced structurally rather than by discipline.

| Field | Value | Units | Provenance | Sweep |
|---|---|---|---|---|
| `A.active.footway_width_default` | `{"bridleway": 2.0, "corridor": 2.0, "cycleway": 2.0, "footway": 2.0, "path": 1.0, "pedestrian": 6.0, "steps...` | metres | `measured` | 0.5 - 3 |
| `A.corridor.attribute_search_cutoff_m` | `2000.0` | metres | `assumed` | 500 - 5000 |
| `A.corridor.cross_buffer_m` | `40.0` | metres | `assumed` | 25 - 60 |
| `A.corridor.dedupe_tolerance_m` | `1.0` | metres | `assumed` | 0.1 - 5 |
| `A.corridor.densify_step_m` | `25.0` | metres | `assumed` | 5 - 50 |
| `A.corridor.extension_lane_take` | `1` | lanes | `assumed` | 0 - 1 |
| `A.corridor.nearest_node_max_rings` | `8` | rings | `assumed` | 3 - 20 |
| `A.corridor.off_corridor_penalty` | `12.0` | dimensionless_cost_multiplier | `assumed` | 6 - 20 |
| `A.corridor.parallel_buffer_m` | `1500.0` | metres | `assumed` | 1000 - 2500 |
| `A.corridor.pre_lr_lanes_per_dir` | `2` | lanes_per_direction | `assumed` | 1 - 2 |
| `A.corridor.report_sample_n` | `12` | edges | `definition` | - |
| `A.corridor.shape_coverage_tolerance_m` | `500.0` | metres | `definition` | - |
| `A.corridor.trunk_buffer_m` | `60.0` | metres | `assumed` | 40 - 100 |
| `A.lightrail.capacity_seated` | `60` | persons_per_vehicle | `assumed` | 50 - 80 |
| `A.lightrail.capacity_standing` | `210` | persons_per_vehicle | `derived` | derived: capacity_standing = capacity_total - capacity_seated |
| `A.lightrail.capacity_total` | `270` | persons_per_vehicle | `observed` | - |
| `A.lightrail.corridor_speed_kmh` | `60.0` | km_per_hour | `assumed` | 40 - 70 |
| `A.lightrail.dwell_charging_s` | *(null - unobtained)* | seconds_per_intermediate_stop | `assumed` | 10 - 35 |
| `A.lightrail.dwell_fixed_s` | `8.0` | seconds_per_stop | `assumed` | 5 - 15 |
| `A.lightrail.dwell_sweep_grid` | `[0.0, 10.0, 20.0, 35.0]` | seconds_per_intermediate_stop | `definition` | - |
| `A.lightrail.line_speed_kmh` | `40.0` | km_per_hour | `assumed` | 30 - 50 |
| `A.lightrail.tsp_enabled` | `false` | boolean | `assumed` | `False`, `True` |
| `A.network.bicycle_excluded_classes` | `["motorway", "motorway_link"]` | osm_highway_classes | `definition` | - |
| `A.network.freespeed_factor` | `1.0` | factor | `definition` | - |
| `A.network.keep_paths` | `false` | boolean | `definition` | - |
| `A.network.keep_tags_as_attributes` | `true` | boolean | `definition` | - |
| `A.network.keep_ways_with_public_transit` | `true` | boolean | `definition` | - |
| `A.network.max_link_length_m` | `500.0` | metres | `assumed` | 200 - 2000 |
| `A.network.parse_turn_restrictions` | `true` | boolean | `definition` | - |
| `A.network.pedestrian_excluded_classes` | `["motorway", "motorway_link"]` | osm_highway_classes | `definition` | - |
| `A.network.railway_lane_capacity_veh_h` | `9999.0` | vehicles_per_hour | `definition` | - |
| `A.network.railway_speed_default_kmh` | `{"rail": 160.0, "light_rail": 70.0, "tram": 70.0}` | km_per_hour | `assumed` | 40 - 180 |
| `A.network.routable_subnetworks` | `{"car": ["car"], "bus": ["bus", "car"], "rail": ["rail", "light_rail"]}` | mode_names_by_subnetwork | `definition` | - |
| `A.network.scale_max_speed` | `false` | boolean | `definition` | - |
| `A.network.way_default_oneway` | `{"motorway": true, "motorway_link": true}` | boolean_by_way_class | `definition` | - |
| `A.network.write_crs` | `true` | boolean | `definition` | - |
| `A.osm.buildings_margin_m` | `3500.0` | metres | `assumed` | 2000 - 6000 |
| `A.osm.harvest_attempts` | `12` | count | `definition` | - |
| `A.osm.harvest_margin_m` | `5000.0` | metres | `assumed` | 2000 - 15000 |
| `A.osm.harvest_tile_deg` | `0.4` | degrees | `assumed` | 0.2 - 0.8 |
| `A.parking.capacity_default` | `{"onstreet": 12, "offstreet_public": 60, "offstreet_private": 40}` | spaces_per_facility | `assumed` | 5 - 100 |
| `A.parking.charged_end_hour` | *(null - unobtained)* | hour_of_day | `derived` | derived: chargedEndHour = A.parking.charged_hours_by_day_type[day][1], or 0.0 w |
| `A.parking.charged_hours_by_day_type` | `{"WEEKDAY": [8.0, 18.0], "SAT": [8.0, 13.0], "SUN": null}` | hour_of_day | `assumed` | plus/minus 25% |
| `A.parking.charged_modes` | `["car"]` | enum | `definition` | - |
| `A.parking.charged_start_hour` | *(null - unobtained)* | hour_of_day | `derived` | derived: chargedStartHour = A.parking.charged_hours_by_day_type[day][0], or 0.0 |
| `A.parking.exempt_activity_types` | `["home"]` | enum | `assumed` | `['home']`, `[]` |
| `A.parking.max_stay_min` | `120.0` | minutes | `assumed` | 60 - 180 |
| `A.parking.occupancy_profile` | `[0.1, 0.08, 0.07, 0.06, 0.08, 0.14, 0.28, 0.46, 0.6, 0.66, 0.7, 0.72, 0.73, 0.72, 0.7, 0.66, 0.58, 0.46, 0....` | occupancy_ratio_by_hour | `assumed` | plus/minus 25% |
| `A.parking.price_aud_hr_max` | `3.2` | AUD_per_hour | `assumed` | 1.6 - 4.8 |
| `A.parking.price_saturation_pctile` | `99.0` | percentile | `assumed` | 95 - 99.5 |
| `A.parking.price_threshold_pctile` | `90.0` | percentile | `assumed` | 80 - 95 |
| `A.road.capacity_default` | `{"motorway": 2000, "trunk": 1800, "primary": 1600, "secondary": 1400, "tertiary": 1200, "unclassified": 100...` | vehicles_per_hour_per_lane | `assumed` | 300 - 2200 |
| `A.road.lane_width_default_m` | `3.5` | metres | `measured` | 2.5 - 4.5 |
| `A.road.lanes_default` | `{"busway": 1, "living_street": 1.0, "motorway": 2.0, "motorway_link": 1.0, "primary": 2.0, "primary_link": ...` | lanes_per_direction | `measured` | 1 - 3 |
| `A.road.speed_default` | `{"busway": 50, "living_street": 10.0, "motorway": 110.0, "motorway_link": 80.0, "primary": 60.0, "primary_l...` | km_per_hour | `measured` | 10 - 110 |
| `A.road.speed_zone_clip_margin_m` | `2000.0` | metres | `assumed` | 500 - 5000 |
| `A.road.speed_zone_excluded_classes` | `["service"]` | enum | `definition` | - |
| `A.road.speed_zone_match_m` | `10.0` | metres | `assumed` | 5 - 20 |
| `A.schedule_mapping.bounded_search` | `true` | boolean | `definition` | - |
| `A.schedule_mapping.candidate_distance_multiplier` | `1.6` | factor | `assumed` | 1.2 - 2.5 |
| `A.schedule_mapping.max_link_candidate_distance_m` | `90.0` | metres | `assumed` | 50 - 150 |
| `A.schedule_mapping.max_travel_cost_factor` | `5.0` | factor | `assumed` | 2 - 10 |
| `A.schedule_mapping.mode_specific_rules` | `false` | boolean | `definition` | - |
| `A.schedule_mapping.modes_to_keep_on_cleanup` | `["car"]` | mode_names | `definition` | - |
| `A.schedule_mapping.n_link_threshold` | `6` | links | `assumed` | 3 - 12 |
| `A.schedule_mapping.network_router` | `SpeedyALT` | router_name | `definition` | - |
| `A.schedule_mapping.remove_not_used_stop_facilities` | `true` | boolean | `definition` | - |
| `A.schedule_mapping.routing_with_candidate_distance` | `true` | boolean | `definition` | - |
| `A.schedule_mapping.schedule_freespeed_modes` | `["artificial"]` | mode_names | `definition` | - |
| `A.schedule_mapping.strict_link_rule` | `false` | boolean | `definition` | - |
| `A.schedule_mapping.thread_chunk_size` | `100` | routes | `definition` | - |
| `A.schedule_mapping.transport_mode_assignment` | `{"bus": ["car", "bus"], "rail": ["rail"], "light_rail": ["light_rail", "tram", "car"], "tram": ["light_rail...` | network_modes_by_schedule_mode | `definition` | - |
| `A.schedule_mapping.travel_cost_type` | `linkLength` | cost_basis | `definition` | - |
| `A.signals.delay_per_intersection_s` | `26.0` | seconds | `assumed` | 15 - 40 |
| `A.signals.junction_match_m` | `60.0` | metres | `assumed` | 30 - 100 |
| `A.signals.min_green_s` | `6.0` | seconds | `assumed` | 4 - 10 |
| `A.signals.n_corridor_intersections` | `14` | count | `observed` | - |
| `A.signals.scats_match_radius_m` | `60` | metres | `assumed` | **held fixed** |
| `A.signals.scats_phasing` | *(null - unobtained)* | phase_plan | `assumed` | `proxy_no_priority`, `proxy_partial_priority`, `proxy_full_priority` |
| `A.transit.bus_capacity_seated` | `44` | persons_per_vehicle | `literature` | 40 - 51 |
| `A.transit.bus_capacity_standing` | `18` | persons_per_vehicle | `literature` | 14 - 22 |
| `A.transit.corridor_mode_label` | `lr` | enum | `observed` | - |
| `A.transit.era1_line_speed_kmh` | `60.0` | km_per_hour | `assumed` | 45 - 75 |
| `A.transit.era1_station_dwell_s` | `30.0` | seconds | `assumed` | 20 - 45 |
| `A.transit.ferry_capacity_seated` | `149` | persons_per_vehicle | `literature` | **held fixed** |
| `A.transit.ferry_capacity_standing` | `51` | persons_per_vehicle | `derived` | derived: ferry_capacity_standing = ferry_capacity_total - ferry_capacity_seated |
| `A.transit.ferry_capacity_total` | `200` | persons_per_vehicle | `literature` | **held fixed** |
| `A.transit.interchange_radius_m` | `250` | metres | `assumed` | 150 - 400 |
| `A.transit.rail_capacity_seated` | `98` | persons_per_vehicle | `assumed` | 80 - 120 |
| `A.transit.rail_capacity_standing` | `48` | persons_per_vehicle | `derived` | derived: rail_capacity_standing = rail_capacity_total - rail_capacity_seated |
| `A.transit.rail_capacity_total` | `146` | persons_per_vehicle | `literature` | 146 - 177 |
| `A.transit.s0_join_tolerance_m` | `1500.0` | metres | `assumed` | 800 - 2500 |
| `A.transit.sbc_extension_km` | `6.65` | kilometres | `observed` | - |
| `A.transit.walk_speed_ms` | `1.25` | metres_per_second | `literature` | 1 - 1.4 |

#### `A.active.footway_width_default`

Fallback footway width. Footway widths were not obtained for Newcastle. MEASURED from the observed OSM width tag over this extract: 3 of 8 classes carry at least 30 tagged edges and take their own median; bridleway, corridor, pedestrian, steps, track keep the assumed value for want of coverage and say so in params/C2_osm_defaults.json, which carries the per-class counts and quantiles.

***measured** · status **active** · DECISIONS.md §9.33*

> **Sweep basis.** the union of the observed interquartile ranges across the 3 classes with at least 30 tagged edges - an observed spread, not a chosen interval

#### `A.corridor.attribute_search_cutoff_m`

Search cutoff when attributing corridor road attributes to a way. A keyword default on two functions until this change.

***assumed** · status **active** · DECISIONS.md §9.34, 15*

> **Sweep basis.** how far the corridor attribute builder searches for a matching way before giving up. Wide enough to find a parallel service road, narrow enough not to reach the next suburb.

#### `A.corridor.cross_buffer_m`

Distance within which a turn restriction or cross street is treated as on the corridor. At 40 m, 10 of the 1,385 resolved restrictions fall on the alignment, against the 14 E1 assumed.

***assumed** · status **active** · DECISIONS.md §3.4*

#### `A.corridor.dedupe_tolerance_m`

Tolerance for dropping consecutive near-duplicate points from a shape.

***assumed** · status **active** · DECISIONS.md §9.34, 15*

> **Sweep basis.** how close two consecutive shape points must be before one is dropped. GTFS consumers dislike near-duplicates; too large a tolerance starts removing real geometry.

#### `A.corridor.densify_step_m`

Step length used when densifying a shape for geometric matching. The SAME NUMBER was a keyword default in two places - src/build/shape_tools.py and the corridor attribute builder - with no link between them.

***assumed** · status **active** · DECISIONS.md §9.34, 15*

> **Sweep basis.** spacing at which a polyline is resampled before geometric comparison. Finer resolves a kerb line; coarser is faster and can cut a curve. It sets the resolution of every corridor geometry comparison, so it is swept rather than fixed.

#### `A.corridor.extension_lane_take`

Lanes removed per direction where an S4/S5 extension runs in the carriageway.

***assumed** · status **active** · DECISIONS.md §3.4*

#### `A.corridor.nearest_node_max_rings`

Maximum grid rings searched when snapping a coordinate to the nearest road-graph node.

***assumed** · status **active** · DECISIONS.md §9.34, 15*

> **Sweep basis.** how far the spatial index expands when no node is found in the first cell. Too few and an anchor off the graph finds nothing; too many is slow. No measurement bears on it.

#### `A.corridor.off_corridor_penalty`

Routing penalty that keeps a reconstructed alignment on observed geometry.

***assumed** · status **active** · DECISIONS.md §3.4*

#### `A.corridor.parallel_buffer_m`

Distance within which a road is treated as a parallel route that may absorb diverted traffic.

***assumed** · status **active** · DECISIONS.md §3.4*

#### `A.corridor.pre_lr_lanes_per_dir`

Hunter/Scott cross-section BEFORE the light rail. THIS IS THE COUNTERFACTUAL HYPOTHESIS B3 RESTS ON and it is assumed, not observed. It must be reported as swept and never as a point estimate.

***assumed** · status **active** · DECISIONS.md §3.4 · proposal §3.3 B3*

> **Sweep basis.** both values are plausible from the historical record; neither is observed

#### `A.corridor.report_sample_n`

How many corridor edges the builder prints as a worked sample. REPORTING ONLY - it changes what a person reads, never what the model computes - and it is declared so that claim is checkable rather than asserted.

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.corridor.shape_coverage_tolerance_m`

Distance within which a stop counts as covered by its route shape, for the coverage figure the schedule builder reports. A REPORTING tolerance: it decides what the build prints about itself, not what any vehicle does.

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.corridor.trunk_buffer_m`

Distance from the alignment within which a road edge is classified corridor trunk.

***assumed** · status **active** · DECISIONS.md §3.4*

#### `A.lightrail.capacity_seated`

Seats on a light rail vehicle. Only the split is assumed - the total it is taken from is observed.

***assumed** · status **active** · DECISIONS.md §4.1, 9.18*

#### `A.lightrail.capacity_standing`

Standing room on a light rail vehicle. Not a free value: it is whatever the published maximum leaves once seats are taken out. Before this existed, no vehicle in the fleet had standing room at all, so the C1 crowding multipliers could never apply in any scenario (issue 18).

***derived** · status **active** · DECISIONS.md §4.1, 9.18*

> **Derived from** `A.lightrail.capacity_total`, `A.lightrail.capacity_seated`: capacity_standing = capacity_total - capacity_seated

#### `A.lightrail.capacity_total`

Maximum capacity of the CAF Urbos 100 as published, and the figure DECISIONS.md 4.1 records. The mapped fleet carried 180 seats with no standing room, which is pt2matsim generic tram default and reconciles with neither the published maximum nor the assumed seated figure (issue 18).

***observed** · status **active** · DECISIONS.md §4.1, 9.18*

#### `A.lightrail.corridor_speed_kmh`

Design speed on the reserved corridor sections.

***assumed** · status **active** · DECISIONS.md §4.2*

#### `A.lightrail.dwell_charging_s`

Supercapacitor charging dwell added at each intermediate stop. NOT MEASURED - a few hours of field observation at Civic or Crown Street would resolve it (DECISIONS.md 13 priority 2). Worth about 11% of end-to-end run time, and it is the subject of secondary question S-a: the marginal cost of the wire-free decision, taken with a late 35m urban amenity package. Modelled as a SEPARATE ADDITIVE TERM so it can be toggled independently of boarding dwell (S2 vs S2a). THIS FIELD HAS NO POINT VALUE.

***assumed** · status **unobtained** · DECISIONS.md §0, 4.3, 13 · proposal §6.2, 3.4 S-a*

> **Sweep basis.** DECISIONS.md 4.3; the shipped scenario descriptions use 20 s as the baseline sweep point, which lives in the scenario config, not on this field

#### `A.lightrail.dwell_fixed_s`

Boarding and alighting dwell, separate from charging dwell.

***assumed** · status **active** · DECISIONS.md §4.4*

#### `A.lightrail.dwell_sweep_grid`

The points at which the UNOBTAINED A.lightrail.dwell_charging_s is sampled for the sensitivity grid. A sampling design, not a value for the field, which stays null and unpinned. The 0 s member is NOT a sweep point of the unobtained quantity - it is the charging-dwell-disabled arm, the S2 vs S2a toggle that makes the wire-free decision's marginal cost separable. The remaining members lie inside the declared sweep, and check_package.py asserts it.

***definition** · status **active** · DECISIONS.md §9.32 · proposal §3.4 S-a*

#### `A.lightrail.line_speed_kmh`

Light rail running speed between stops, used in the run-time decomposition.

***assumed** · status **active** · DECISIONS.md §4.2*

#### `A.lightrail.tsp_enabled`

Transit signal priority on the corridor. Downstream of A.signals.scats_phasing.

***assumed** · status **active** · DECISIONS.md §5 · proposal §3.4 S-b*

#### `A.network.bicycle_excluded_classes`

Road classes a network-simulated cyclist may not use: bicycles are prohibited on motorways by road rules (trunk roads are legal for cycling in NSW). A vocabulary of the road rules, not a tunable.

***definition** · status **active** · DECISIONS.md §9.54*

#### `A.network.freespeed_factor`

Multiplier applied to a way default free speed. One, because the free speed is taken from the regulated speed instrument and a factor over it would be an undeclared second opinion about the same quantity.

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.network.keep_paths`

Whether every intermediate OSM node becomes a MATSim node. False collapses a way between junctions into one link, which is what a mobsim needs: keeping paths multiplies link count without adding a decision point, and MATSim queues form per link.

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.network.keep_tags_as_attributes`

Whether OSM tags survive onto the MATSim link. TRUE IS LOAD-BEARING: the E1 road variants are re-applied to a scenario network by osm:way:id, which exists on the link only because this is true (DECISIONS.md 9.3).

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.network.keep_ways_with_public_transit`

Retain a way carrying a public transit route even when its class would otherwise be dropped. False would delete bus-only links and strand the routes mapped onto them.

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.network.max_link_length_m`

Longest MATSim link before a way is split. Decided in the network builder as a literal until this change, which made a network-construction parameter invisible to every sweep.

***assumed** · status **active** · DECISIONS.md §9.34, 15*

> **Sweep basis.** no measurement bears on it: it trades link count against the spatial resolution of a queue. The lower bound is about a city block, the upper long enough that a rural link is not split for its own sake. Swept because link length changes where congestion can form.

#### `A.network.parse_turn_restrictions`

Whether OSM turn restrictions become MATSim disallowed next links. The base network carries 1,240 of them and the E1 variants add banned turn movements on the corridor, so the road-space externality of proposal 3.3 depends on this being true.

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.network.pedestrian_excluded_classes`

Road classes a network-simulated pedestrian may not use. NSW Road Rules prohibit pedestrians on motorways (rule 288, signposted roads) and NOWHERE ELSE: an urban trunk road (Stewart Avenue, Maitland Road) is a legal pedestrian route with footpaths, and the 9.54 list wrongly extended the motorway prohibition to trunk/trunk_link - which severed the walkable city (9.58: 16.7k walk links stripped as unreachable because whole neighbourhoods connect only through a trunk segment; 30,330 activities stranded on walk-less links at 25%). The walk mode is simulated on the road graph as the footpath proxy (the observed footway network is data, not part of the one mapped MATSim build - 3.5 forbids a remap). A vocabulary of the road rules, not a tunable.

***definition** · status **active** · DECISIONS.md §9.54, 9.58*

#### `A.network.railway_lane_capacity_veh_h`

Lane capacity written for a railway link. A SENTINEL MEANING UNCONSTRAINED, not a measurement: rail headway is governed by the signalling system and the timetable, neither of which a MATSim link capacity represents. It must stay far above any plausible flow so the queue never binds on a rail link.

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.network.railway_speed_default_kmh`

Default free speed for a RAILWAY class way, where A.road.speed_default does not apply because the class is not a road. Split out of the network builder table, which held speeds for road and railway classes together and had drifted from A.road.speed_default on six road classes.

***assumed** · status **active** · DECISIONS.md §9.34, 15*

> **Sweep basis.** line speed on reserved rail alignment where no regulated speed zone applies. The Hunter Line is a 160 km/h class alignment and Australian street-running light rail is limited to about 70; both are class defaults rather than measurements of this corridor, and A.lightrail.line_speed_kmh is the measured corridor quantity.

#### `A.network.routable_subnetworks`

Which transport modes each routable subnetwork admits, as subnetworkMode -> allowedTransportModes. A vocabulary the network is defined over rather than a value to tune: the bus subnetwork admits car because buses run in traffic, and that is the property making transit feel congestion.

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.network.scale_max_speed`

Whether pt2matsim scales the OSM maxspeed by its own factor. False: free speed comes from the TfNSW regulated speed zones - the legal instrument - and from A.road.speed_default where no zone applies, not from a tool default.

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.network.way_default_oneway`

Way classes whose DEFAULT direction is one way, used where OSM carries no explicit oneway tag. A class absent from this map defaults to two way. Motorway and its links only: every other class is bidirectional unless the data says otherwise.

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.network.write_crs`

Write the coordinate system into the network file, so a downstream reader cannot mistake the projection. This repository carried the wrong datum label in four documents at once (DECISIONS.md 2.6).

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.osm.buildings_margin_m`

Margin around the observed light rail STOP SET for the CBD building harvest, which feeds the D1 frontage segments hypothesis B1 is measured on. Anchored on the stops in the GTFS feed rather than a drawn rectangle - the stops are observed, available before any OSM harvest, and exist for any city with a corridor. Issue #34.

***assumed** · status **active** · DECISIONS.md §9.35*

> **Sweep basis.** chosen. At 3,500 m the derived extent CONTAINS the rectangle it replaced, which needed 3,217 m, so no building previously harvested is lost; all seven pre-registered frontage comparators lie within 1,161 m of a light rail stop.

#### `A.osm.harvest_attempts`

Attempts per harvest tile before it is given up on, rotating across the Overpass mirrors. An acquisition retry budget, not a model input - it cannot change a result, only whether the download finishes. 12 gives each of the three mirrors four tries, which is what the roads layer needed.

***definition** · status **active** · DECISIONS.md §9.35*

#### `A.osm.harvest_margin_m`

Margin around the DISSOLVED LGA boundary for the OSM harvest. The extent is derived from zones_LGA.gpkg, never typed: the rectangle this replaced cut 0.30 degrees off the west and 0.26 off the east of the declared study area, putting 87 of 1,500 core SA1s and 31,940 agents outside the road network for three phases (issue #32).

***assumed** · status **active** · DECISIONS.md §9.35*

> **Sweep basis.** chosen. Wide enough that a trip leaving the study area still has road to leave on, narrow enough that the harvest stays a study area rather than a state.

#### `A.osm.harvest_tile_deg`

Maximum side of an Overpass harvest tile. The corrected study extent is 2.02x the rectangle it replaced and will not fetch in one request, so each layer is tiled and merged, de-duplicating by element id because Overpass returns a whole way when any part of it matches.

***assumed** · status **active** · DECISIONS.md §9.35*

> **Sweep basis.** MEASURED as a ceiling, not chosen: the whole corrected extent in one query returns 504 Gateway Timeout from the endpoint, twice on the roads layer, while the 0.85 x 0.65 degree rectangle it replaced always succeeded. 0.4 keeps every tile well inside what is known to work.

#### `A.parking.capacity_default`

Fallback capacity where a parking facility carries none. 4,861 of 7,710 facilities carry an observed capacity.

***assumed** · status **active** · DECISIONS.md §6*

#### `A.parking.charged_end_hour`

Hour at which parking stops being charged, for the day type this config is being emitted for. See A.parking.charged_start_hour: an end at or before the start means the day is free.

***derived** · status **computed** · DECISIONS.md §9.31 · MATSim `parking.chargedEndHour`*

> **Derived from** `A.parking.charged_hours_by_day_type`: chargedEndHour = A.parking.charged_hours_by_day_type[day][1], or 0.0 when that day type declares no window

#### `A.parking.charged_hours_by_day_type`

The window in which parking is charged, per day type. IT IS A WINDOW PER DAY TYPE, NOT THE TWO PARAMETERS: this field carried matsim_param parking.chargedStartHour, parking.chargedEndHour until the config emitter was built, which would have written the whole dictionary into both scalars. The per-day scalars are A.parking.charged_start_hour and A.parking.charged_end_hour, selected from this by the day type the config is being emitted for. Assumed, and stated rather than left implicit: A5_parking_facilities.csv already asserted 'Mon-Fri 08:00-18:00; Sat 08:00-13:00; else free' in its price_schedule string, where it reached nothing. Without a window, SUN - one of the three day types - would be charged at weekday meter rates.

***assumed** · status **active** · DECISIONS.md §9.31*

#### `A.parking.charged_modes`

Leg modes that occupy a parking space and are charged for it. Fixed by the formulation, not an empirical quantity: only the driver parks the vehicle. Charging `ride` as well would bill one car twice - the same double-count DECISIONS.md 9.17 removed from the per-km rate.

***definition** · status **active** · DECISIONS.md §9.31 · MATSim `parking.chargedModes`*

#### `A.parking.charged_start_hour`

Hour at which parking begins to be charged, for the day type this config is being emitted for. Computed rather than declared because the choice of day is not a registry value - it is which of the thirty run-input sets is being written. A day type with no window resolves to a zero-length window, which the Java handler reads as `charge nothing`; expressing a free day that way rather than with a separate flag keeps one code path.

***derived** · status **computed** · DECISIONS.md §9.31 · MATSim `parking.chargedStartHour`*

> **Derived from** `A.parking.charged_hours_by_day_type`: chargedStartHour = A.parking.charged_hours_by_day_type[day][0], or 0.0 when that day type declares no window

#### `A.parking.exempt_activity_types`

Activity types at which a parked car is not charged. Home is exempt because residential parking is off-street private or permit, and because charging it would levy the max-stay cap on every agent who drives home each night - a standing penalty on living in a dense zone rather than a price on a travel choice. Activity types are generic to any city's chain builder, so this carries no place name.

***assumed** · status **active** · DECISIONS.md §9.31 · MATSim `parking.exemptActivityTypes`*

#### `A.parking.max_stay_min`

Maximum charged parking duration. DOUBLES AS THE CHARGE CAP: the charge is price x min(duration, max_stay), so a stay longer than this is UNDER-charged rather than penalised. That is a declared modelling choice, not an oversight - modelling over-stay enforcement would need an infringement rate nobody has measured here.

***assumed** · status **active** · DECISIONS.md §9.31 · MATSim `parking.maxStayMinutes`*

> **Sweep basis.** +/-50% of the point value.

#### `A.parking.occupancy_profile`

Hourly occupancy profile, applied to EVERY parking facility. Assumed: parking meter transactions and occupancy counts were not obtained (DECISIONS.md 13 priority 6-adjacent). It replaced four hand-typed per-zone profiles that rested on no observation and reached no consumer (DECISIONS.md 9.31).

***assumed** · status **active** · DECISIONS.md §6*

#### `A.parking.price_aud_hr_max`

Parking price in the densest employment zone, in 2026 AUD per hour. The ceiling of the density ramp, not a citywide rate.

***assumed** · status **active** · DECISIONS.md §9.31*

> **Sweep basis.** +/-50% of the point value. Assumed, NOT observed: City of Newcastle publishes no meter tariff in this package, and the OSM fee=yes tag is unusable - 452 of its 472 facilities are University of Newcastle car parks (DECISIONS.md 9.31).

#### `A.parking.price_saturation_pctile`

Job-density percentile at which the parking price reaches price_aud_hr_max. Newcastle p99 = 8,710.5 jobs/km2. Between threshold and saturation the price rises linearly; above saturation it is clamped.

***assumed** · status **active** · DECISIONS.md §9.31*

> **Sweep basis.** chosen. Must exceed price_threshold_pctile; the builder rejects an inversion rather than dividing by a negative span.

#### `A.parking.price_threshold_pctile`

Job-density percentile at which paid parking begins. Read against the CITY'S OWN core-zone job-density distribution, so a new city computes its own threshold and no extent is ever typed. Newcastle p90 = 1,500.9 jobs/km2, which prices 150 of 1,500 core zones.

***assumed** · status **active** · DECISIONS.md §9.31*

> **Sweep basis.** chosen, not observed: no Newcastle meter-transaction or paid-zone boundary dataset exists to fit the threshold against. The range spans the top quintile to the top twentieth of zones.

#### `A.road.capacity_default`

Saturation flow by road class. Never observed; a class-level convention.

***assumed** · status **active** · DECISIONS.md §3.2*

#### `A.road.lane_width_default_m`

Per-lane carriageway width where OSM carries no width, applied to 99.2% of road edges. It had NO registry field: build_network_layers.py carried a bare 3.2. Derived as width/lanes on the 265 edges carrying both tags. The width tag ALONE is the whole carriageway and stands at 6.5 m; writing that into a per-lane field would double every carriageway in the model.

***measured** · status **active** · DECISIONS.md §9.33*

> **Sweep basis.** the interquartile range of per-lane widths over 265 edges carrying both a width and a lanes tag - an observed spread

#### `A.road.lanes_default`

Fallback lane count where OSM carries no lanes tag. Applied only to edges with no observation - DECISIONS.md 2.5 corrected the proposal premise that the corridor is 75-98% imputed: as-built trunk lane counts are observed in OSM for 87.5% of corridor trunk edges. Full class table is in the build script; the registry overrides per class. MEASURED from the observed OSM lanes tag, halved on two-way ways over this extract: 13 of 16 classes carry at least 30 tagged edges and take their own median; busway, road, tertiary_link keep the assumed value for want of coverage and say so in params/C2_osm_defaults.json, which carries the per-class counts and quantiles.

***measured** · status **active** · DECISIONS.md §9.33*

> **Sweep basis.** the union of the observed interquartile ranges across the 13 classes with at least 30 tagged edges - an observed spread, not a chosen interval

#### `A.road.speed_default`

Fallback free-flow speed where OSM carries no maxspeed tag. MEASURED from the observed OSM maxspeed tag over this extract: 13 of 16 classes carry at least 30 tagged edges and take their own median; busway, road, tertiary_link keep the assumed value for want of coverage and say so in params/C2_osm_defaults.json, which carries the per-class counts and quantiles.

***measured** · status **active** · DECISIONS.md §9.33*

> **Sweep basis.** the union of the observed interquartile ranges across the 13 classes with at least 30 tagged edges - an observed spread, not a chosen interval

#### `A.road.speed_zone_clip_margin_m`

Margin around the dissolved LGA boundary when clipping the statewide Speed Zones layer. A MARGIN on a derived boundary, not an extent: the boundary comes from zones_LGA.gpkg, so a new city clips to its own.

***assumed** · status **active** · DECISIONS.md §9.34*

> **Sweep basis.** chosen. Wide enough that a road crossing the LGA boundary keeps its zone, narrow enough not to carry the rest of the state.

#### `A.road.speed_zone_excluded_classes`

Road classes that do NOT take a regulated speed zone. `service` is driveways, car-park aisles and alleys: TfNSW does not speed-zone them, so the nearest zone line belongs to the arterial they run beside. Measured agreement with OSM on service roads is 37% against 83% on residential - the join is not wrong there, it is matching a different road. Excluding by OSM class is portable; excluding by measured agreement would be fitting the join to its own validation.

***definition** · status **active** · DECISIONS.md §9.34*

#### `A.road.speed_zone_match_m`

Maximum distance from a road edge to a Speed Zone line for the regulated speed to be adopted. Output DOES vary across it - unlike the SCATS join radius, which is held fixed because nothing varies - so it is swept.

***assumed** · status **active** · DECISIONS.md §9.34*

> **Sweep basis.** MEASURED, not chosen: agreement with the OSM maxspeed tag where both exist holds at 73-77% out to 5 m and 72% to 10 m, then collapses to 30% at 10-20 m and 15% at 20-40 m. Beyond 10 m the nearest line is a different road.

#### `A.schedule_mapping.bounded_search`

Bound the link-candidate search by distance rather than searching the whole network per stop. Off, the mapping of 15 feeds does not finish in usable time.

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.schedule_mapping.candidate_distance_multiplier`

How far beyond the nearest candidate link the mapper keeps looking, as a multiple of that distance.

***assumed** · status **active** · DECISIONS.md §9.34, 15*

> **Sweep basis.** pt2matsim documents no calibrated value. Too low and a stop on the far side of a dual carriageway finds no candidate; too high and it maps onto a parallel road. The package reports 0 unmapped stops and an artificial link share of 0.4-0.6%, which is evidence the current value works, not that it is optimal.

#### `A.schedule_mapping.max_link_candidate_distance_m`

Furthest a stop may be from a candidate link. Written to BOTH the module default and every transport-mode assignment, which is why it is one field: two copies drifting apart would map bus and rail to different tolerances silently.

***assumed** · status **active** · DECISIONS.md §9.34, 15*

> **Sweep basis.** the distance a stop may sit from the link that serves it. The corridor measurement that bears on it is the 112 s interchange walk (DECISIONS.md 9.32); 50 m is tight for a divided road and 150 m starts admitting the wrong street.

#### `A.schedule_mapping.max_travel_cost_factor`

Ceiling on a mapped route path cost relative to the direct path. Raising it maps more of a route onto real road; lowering it produces more artificial link, on which no car ever queues.

***assumed** · status **active** · DECISIONS.md §9.34, 15*

> **Sweep basis.** how much longer than the direct path a mapped route may be before the mapper inserts an artificial link instead. It controls the artificial link share directly, which the package reports at 0.4-0.6%.

#### `A.schedule_mapping.mode_specific_rules`

Whether pt2matsim applies its own per-mode routing rules. False: the mode-to-network assignment is declared in A.schedule_mapping.transport_mode_assignment instead, where it can be read.

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.schedule_mapping.modes_to_keep_on_cleanup`

Network modes preserved when the mapper removes links no route uses. Car is kept because the road network is the thing being modelled; removing it to suit a schedule would delete the study.

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.schedule_mapping.n_link_threshold`

Candidate links retained per stop. Written to both the module default and every transport-mode assignment, for the same reason as the candidate distance.

***assumed** · status **active** · DECISIONS.md §9.34, 15*

> **Sweep basis.** how many candidate links a stop keeps before the router chooses. Fewer is faster and can miss the right link at a complex junction; more is slower with diminishing return. No measurement bears on it.

#### `A.schedule_mapping.network_router`

Which least-cost path router the mapper uses. A TOOLCHAIN CHOICE AND THEREFORE A MODEL CHOICE: pt2matsim mapping is already not reproducible run to run (DECISIONS.md 3.5, about 18% of route link sequences differ between identical builds), and changing the router changes that distribution.

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.schedule_mapping.remove_not_used_stop_facilities`

Drop stop facilities no mapped route serves. True keeps schedule and network consistent; a stranded facility is a stop no vehicle can call at.

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.schedule_mapping.routing_with_candidate_distance`

Include the stop-to-link distance in the mapping cost, so a nearer link is preferred among otherwise equal paths.

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.schedule_mapping.schedule_freespeed_modes`

Modes whose link free speed is set from the SCHEDULE rather than from the road. Artificial links only: a tram on a real street must feel that street, and that trams and buses traverse congested links is a stated property of this model.

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.schedule_mapping.strict_link_rule`

Whether a route may ONLY use links carrying its declared network modes. False allows an artificial link where no permitted link exists, which is what keeps the unmapped-stop count at zero; true would strand routes rather than report them.

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.schedule_mapping.thread_chunk_size`

How many routes a mapper thread takes at once. Throughput only - it does not change which link a route maps to.

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.schedule_mapping.transport_mode_assignment`

Which network modes may carry each schedule mode, as scheduleMode -> networkModes. LIGHT RAIL AND TRAM ADMIT CAR DELIBERATELY: the Newcastle line runs in the Hunter Street carriageway, so its links are shared with traffic and the tram is delayed by it. Ferry maps to artificial because no water network is modelled.

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.schedule_mapping.travel_cost_type`

Whether the mapper minimises link LENGTH or link TRAVEL TIME. Length, so a mapped path follows the geometry the timetable describes rather than the fastest road: a tram pushed onto a parallel arterial because it is quicker would put transit on the wrong street.

***definition** · status **active** · DECISIONS.md §9.34, 15*

#### `A.signals.delay_per_intersection_s`

Proxy signal delay per corridor intersection, used to decompose scheduled run time in the absence of SCATS phasing. Downstream of A.signals.scats_phasing.

***assumed** · status **active** · DECISIONS.md §5*

#### `A.signals.junction_match_m`

Radius for matching an A2 intersection to a SUMO junction.

***assumed** · status **active** · DECISIONS.md §5*

#### `A.signals.min_green_s`

Minimum green time in a generated SUMO signal program.

***assumed** · status **active** · DECISIONS.md §5*

#### `A.signals.n_corridor_intersections`

Signalised intersections on the corridor. All 14 match a signalised junction in every SUMO road variant and every realised cycle lands within 1 s of its A2 value.

***observed** · status **active** · DECISIONS.md §5*

#### `A.signals.scats_match_radius_m`

Radius within which an intersection in A2_signal_control_corridor.csv is matched to a signal in the TfNSW Traffic Lights Location inventory, to recover its SCATS site number and installation date. The corridor intersections are clusters of OSM traffic-signal nodes and carry no identifier of their own; the TfNSW inventory is the only observed source of both. Measured match distances on the 14 corridor intersections range from 1 to 26 m.

***assumed** · status **active** · DECISIONS.md §9.24*

> **Held fixed.** A data-join tolerance, not a model parameter. It decides which observed TfNSW signal is the same physical intersection as a clustered OSM one, and no behaviour, run time or score reads it - only the identity written into scats_site_id. It is held fixed rather than swept because a sweep could not change the join: all 14 corridor intersections match inside 26 m, so every radius from the 45 m OSM clustering distance up to about 100 m yields the identical assignment, and widening it past that would begin attaching an intersection to its neighbour rather than resolving a real ambiguity. Declaring a sweep interval over which the output is constant would be the defect this project has already hit three times.
>
> *Departure requires: a re-measured match-distance distribution showing a corridor intersection falling outside this radius, or a corridor extension into an area where signals sit closer together than the radius*

#### `A.signals.scats_phasing`

SCATS phase data for the Hunter/Scott corridor. NOT OBTAINED - a formal TfNSW request is outstanding. It determines corridor run time more than any other single input: the swing between no priority and full priority is 38% (S2 vs S2b). Every program in the SUMO corridor is labelled timing_source=assumed. THIS FIELD HAS NO POINT VALUE AND THE RESOLVER WILL NOT INVENT ONE: select a sweep member explicitly.

***assumed** · status **unobtained** · DECISIONS.md §0, 5, 13 · proposal §6.2, 7.2*

#### `A.transit.bus_capacity_seated`

Seats on a Newcastle bus. Published Volvo B12BLE figure. The mapped fleet carried pt2matsim's generic 70 seats, overstating seats by about 59% (issue 18).

***literature** · status **active** · DECISIONS.md §9.21, 9.30*

#### `A.transit.bus_capacity_standing`

Standing room on a Newcastle bus. Published B12BLE figure, 44 + 18 = 62 total. Before issue 18 NO vehicle in the fleet had standing room, so the C1 crowding multipliers were inert by construction.

***literature** · status **active** · DECISIONS.md §9.21, 9.30*

#### `A.transit.corridor_mode_label`

The modes_served label the corridor under study carries in A3_stop_extras.csv, read from the GTFS feed. Declared rather than typed into the harvester so the corridor extent is derived from an observed stop set; a city whose feed labels its corridor differently changes this one value.

***observed** · status **active** · DECISIONS.md §9.35*

#### `A.transit.era1_line_speed_kmh`

Heavy rail line speed in the reconstructed pre-2014 era. No 2014 public timetable has been obtained to validate this (DECISIONS.md 13 priority 8).

***assumed** · status **active** · DECISIONS.md §11*

#### `A.transit.era1_station_dwell_s`

Heavy rail station dwell in the reconstructed pre-2014 era.

***assumed** · status **active** · DECISIONS.md §11*

#### `A.transit.ferry_capacity_seated`

Published seated capacity of the Stockton ferries. Unlike rail and light rail, the ferry split IS published, so neither half is assumed.

***literature** · status **active** · DECISIONS.md §9.21, 9.30*

> **Held fixed.** Published seated capacity, held on the same reasoning as the total: it is a fact about the vessel. This is the ONLY vehicle in the fleet whose seated/standing split is published - tram and rail both have an assumed, swept seated share because only their totals are.
>
> *Departure requires: a different vessel entering service on the Stockton route*

#### `A.transit.ferry_capacity_standing`

Standing room on a Stockton ferry. Whatever the published total leaves once the published seats are taken out - both halves are published, so this identity carries no assumption.

***derived** · status **active** · DECISIONS.md §9.21, 9.30*

> **Derived from** `A.transit.ferry_capacity_total`, `A.transit.ferry_capacity_seated`: ferry_capacity_standing = ferry_capacity_total - ferry_capacity_seated

#### `A.transit.ferry_capacity_total`

Published capacity of the Stockton ferries MV Shortland and MV Hunter. The mapped fleet carried 250 seats and no standing room, overstating by 25%.

***literature** · status **active** · DECISIONS.md §9.21, 9.30*

> **Held fixed.** A published vessel capacity is a fact about the boat, not a behavioural parameter, and sweeping it would assert an uncertainty that does not exist. Both Stockton ferries carry the same published figure.
>
> *Departure requires: a different vessel entering service on the Stockton route*

#### `A.transit.interchange_radius_m`

Radius within which two stops are treated as one interchange for transfer generation.

***assumed** · status **active** · DECISIONS.md §11*

#### `A.transit.rail_capacity_seated`

Seats on a two-car Hunter Line set. Only the SPLIT is assumed - the total it comes from is published.

***assumed** · status **active** · DECISIONS.md §9.21, 9.30*

#### `A.transit.rail_capacity_standing`

Standing room on a two-car Hunter Line set. Not a free value: whatever the published total leaves once seats are taken out.

***derived** · status **active** · DECISIONS.md §9.21, 9.30*

> **Derived from** `A.transit.rail_capacity_total`, `A.transit.rail_capacity_seated`: rail_capacity_standing = rail_capacity_total - rail_capacity_seated

#### `A.transit.rail_capacity_total`

Capacity of a two-car Hunter Line set. The mapped fleet carried pt2matsim's generic 400 seats with no standing room - overstating a two-car set by roughly 2.7x, which is part of why transit capacity never binds (DECISIONS.md 9.12, issue 18).

***literature** · status **active** · DECISIONS.md §9.21, 9.30*

#### `A.transit.s0_join_tolerance_m`

Tolerance for joining the retained heavy rail alignment to the observed network in S0.

***assumed** · status **active** · DECISIONS.md §3.4*

#### `A.transit.sbc_extension_km`

Broadmeadow extension length as STATED in the Strategic Business Case. The alignment routed over observed OSM centreline is 7.00 km, 5.3% longer. The model uses the routed geometry; this field records the published figure.

***observed** · status **active** · DECISIONS.md §3.4*

#### `A.transit.walk_speed_ms`

Walk speed used to generate GTFS transfer times. Distinct from the MATSim teleported walk speed - see RUN.matsim.teleported_walk_speed_ms, which is 1.05. Since 9.54 it is ALSO the walk vehicle type maximum velocity: the same physical walking speed, carried into the mobsim and the router (CappedSpeedTravelTime).

***literature** · status **active** · DECISIONS.md §11*

## Demand (B1-B5)

*`cities/newcastle/registry/B_demand.json` - 68 fields*

Synthetic population, activity and tour generation, external boundary demand, and the count-comparison corrections. The third unobtained input, B.opal.journey_linked, lives here. B.activity.p_intermediate_stop is the demand-side parameter with the most leverage over mode share and is assumed.

| Field | Value | Units | Provenance | Sweep |
|---|---|---|---|---|
| `B.activity.act_duration_min` | `{"HW": 465, "HE": 360, "HS": 45, "HO": 90, "WB": 60, "NHB": 20, "HX": 5}` | minutes | `assumed` | plus/minus 25% |
| `B.activity.child_tour_retention` | `0.4` | probability | `assumed` | 0.25 - 0.6 |
| `B.activity.day_horizon_s` | `108000` | seconds | `definition` | - |
| `B.activity.day_purpose_mix` | `{"WEEKDAY": {"HW": 1.0, "HE": 1.0, "HS": 0.9, "HO": 0.9, "WB": 1.0, "HX": 1.0}, "SAT": {"HW": 0.25, "HE": 0...` | multiplier_on_weekday | `assumed` | plus/minus 30% |
| `B.activity.days_per_week` | `{"WEEKDAY": 5.0, "SAT": 1.0, "SUN": 1.0}` | days | `definition` | - |
| `B.activity.departure_profile` | `{"HE": [0.0, 0.0, 0.0, 0.0, 0.002, 0.01, 0.06, 0.23, 0.27, 0.09, 0.035, 0.03, 0.035, 0.04, 0.075, 0.06, 0.0...` | probability_by_hour | `assumed` | plus/minus 25% |
| `B.activity.detour_factor` | `1.3376` | ratio | `measured` | 1.25 - 1.423 |
| `B.activity.duration_cv` | `0.3` | coefficient_of_variation | `assumed` | 0.2 - 0.45 |
| `B.activity.escort_binding_enabled` | `true` | boolean | `definition` | - |
| `B.activity.escort_binding_min_gap_s` | `2700` | seconds | `assumed` | 900 - 5400 |
| `B.activity.escort_binding_nonhh_scope` | `same_zone` | enum | `assumed` | `household_only`, `same_zone` |
| `B.activity.escort_binding_scope` | `any_member_trip` | enum | `assumed` | `any_member_trip`, `unlicensed_or_education` |
| `B.activity.escort_excludes_ride` | `true` | boolean | `derived` | derived: an escort trip is a trip made in order to convey another person, so th |
| `B.activity.escort_requires_licence` | `true` | boolean | `derived` | derived: an escort trip is a trip made in order to convey another person, so th |
| `B.activity.hts_rate_per_person_day` | `3.473` | trips_per_person_per_day | `measured` | 3.3 - 3.65 |
| `B.activity.p_intermediate_stop` | `{"HW": 0.22, "HE": 0.12, "HS": 0.18, "HO": 0.2, "WB": 0.3, "HX": 0.15}` | probability | `assumed` | 0.1 - 0.35 |
| `B.activity.p_mandatory` | `{"WEEKDAY": {"work": 0.78, "education": 0.85}, "SAT": {"work": 0.16, "education": 0.03}, "SUN": {"work": 0....` | probability | `assumed` | 0.6 - 0.95 |
| `B.activity.p_second_stop` | `0.25` | probability | `assumed` | 0.12 - 0.4 |
| `B.activity.plan_access_s` | `240` | seconds | `assumed` | 120 - 480 |
| `B.activity.plan_speed_car_kmh` | `26.0` | km/h | `assumed` | 20 - 32 |
| `B.activity.plan_speed_nocar_kmh` | `16.0` | km/h | `assumed` | 10 - 22 |
| `B.activity.weekend_to_weekday` | `0.7521` | ratio | `measured` | 0.709 - 0.816 |
| `B.bike.pce` | `0.2` | passenger_car_equivalents | `literature` | 0.1 - 0.4 |
| `B.bike.speed_ms` | `4.2` | m/s | `literature` | 3.1 - 5.5 |
| `B.counts.heavy_vehicle_share` | `0.0652` | share_of_vehicles | `measured` | 0.0129 - 0.1529 |
| `B.counts.station_match_radius_m` | `120.0` | metres | `assumed` | 60 - 120 |
| `B.counts.vehicles_per_car_leg` | `1.0` | vehicles_per_leg | `derived` | derived: observed vehicle trips ARE driver trips at occupancy 1.3503, so a car  |
| `B.counts.vehicles_per_ride_leg` | `0.0` | vehicles_per_leg | `derived` | derived: a passenger rides in a vehicle already counted, so a ride leg contribu |
| `B.external.agent_profile` | `{"car_available": 1, "age": 40, "licence_holder": 1, "employment_status": "employed_full_time", "student_st...` | person_attributes | `definition` | - |
| `B.external.agent_ride_available` | `false` | boolean | `derived` | derived: a person may be a car passenger only if their household holds a vehicl |
| `B.external.cordon_road_classes` | `["motorway", "trunk", "primary", "secondary", "motorway_link", "trunk_link", "primary_link"]` | osm_highway_class | `definition` | - |
| `B.external.interaction_rate` | `0.08` | probability | `assumed` | 0.04 - 0.15 |
| `B.external.person_id_base` | `900000000` | integer_offset | `definition` | - |
| `B.external.purpose_split` | `{"HW": 0.7, "HO": 0.3}` | probability | `assumed` | plus/minus 20% |
| `B.external.through_corridor_match_km` | `30.0` | km | `assumed` | 10 - 50 |
| `B.external.through_min_separation_km` | `30.0` | km | `assumed` | 20 - 50 |
| `B.external.through_outside_min_m` | `1000.0` | metres | `assumed` | 300 - 3000 |
| `B.external.through_share` | `0.35` | share_of_aadt | `assumed` | 0.15 - 0.6 |
| `B.freight.attractor_divisions` | `["AgFF", "Min", "Mnf", "EGWWS", "Const", "WST", "RetT", "TPW"]` | anzsic_division_column_stems | `definition` | - |
| `B.freight.gravity_beta_per_km` | `0.08` | per_km | `assumed` | 0.03 - 0.2 |
| `B.freight.length_m` | `12.5` | metres | `literature` | **held fixed** |
| `B.freight.max_speed_kmh` | `100.0` | km/h | `definition` | - |
| `B.freight.pce` | `2.0` | passenger_car_equivalents | `literature` | 1.5 - 3.5 |
| `B.freight.trip_ratio` | `0.0697` | heavy_vehicle_trips_per_light_vehicle_trip | `assumed` | 0 - 0.14 |
| `B.mode.seed_split` | `{"car_available": {"bike": 0.2, "car": 0.2, "pt": 0.2, "ride": 0.2, "walk": 0.2}, "no_car": {"bike": 0.25, ...` | share_by_mode | `definition` | - |
| `B.mode.seed_split_informed` | `{"car_available": {"bike": 0.01, "car": 0.78, "pt": 0.02, "ride": 0.1, "walk": 0.09}, "no_car": {"bike": 0....` | share_by_mode | `assumed` | `uninformed`, `informed` |
| `B.motorbike.length_m` | `2.2` | metres | `literature` | **held fixed** |
| `B.motorbike.pce` | `0.4` | passenger_car_equivalents | `literature` | 0.3 - 0.75 |
| `B.motorbike.trip_share` | `0.0036` | share_of_trips | `assumed` | 0 - 0.01 |
| `B.network_factors.distance_band` | `0.25` | share | `assumed` | 0.1 - 0.5 |
| `B.network_factors.min_pair_m` | `500.0` | metres | `assumed` | 100 - 2000 |
| `B.network_factors.n_pairs` | `600` | zone_pairs | `assumed` | 200 - 5000 |
| `B.opal.journey_linked` | *(null - unobtained)* | dataset | `assumed` | `tap_sequence_matching_model` |
| `B.population.age_bands` | `[[0, 4], [5, 11], [12, 17], [18, 24], [25, 34], [35, 44], [45, 54], [55, 64], [65, 74], [75, 84], [85, 120]]` | years | `definition` | - |
| `B.population.bike_available_rate` | `0.5` | share | `assumed` | 0.3 - 1 |
| `B.population.build_sample_share` | `1.0` | share_of_population | `definition` | - |
| `B.population.licence_rate_by_age_band` | `[0, 0, 0, 0.62, 0.88, 0.93, 0.94, 0.93, 0.88, 0.72, 0.45]` | probability | `literature` | plus/minus 10% |
| `B.population.ride_requires_household_driver` | `true` | boolean | `derived` | derived: a person may be a car passenger only if their B1 household holds at le |
| `B.ride.max_passengers_per_vehicle` | `4` | persons | `assumed` | 1 - 4 |
| `B.ride.pairing_enabled` | `true` | boolean | `definition` | - |
| `B.ride.pairing_rule` | `both_links` | enum | `assumed` | `both_links`, `origin_link`, `dest_link`, `window_only` |
| `B.ride.pairing_window_min` | `15.0` | minutes | `assumed` | 5 - 60 |
| `B.ride.physical_boarding` | `true` | boolean | `definition` | - |
| `B.ride.pickup_dwell_s` | `0.0` | seconds | `assumed` | 0 - 120 |
| `B.ride.remode_unpaired` | `true` | boolean | `definition` | - |
| `B.ride.wait_for_driver` | `true` | boolean | `definition` | - |
| `B.seed.master` | `20260810` | integer_seed | `definition` | - |
| `B.walk.pce` | `0.0` | passenger_car_equivalents | `definition` | - |

#### `B.activity.act_duration_min`

Mean activity duration by purpose. HX (serve passenger) is a drop-off: the driver does not perform an activity at the destination, so its duration is the dwell, not a stay. No survey in the package measures a drop-off dwell, so it is assumed and carries the same proportional sweep as the rest.

***assumed** · status **active** · DECISIONS.md §9.2*

#### `B.activity.child_tour_retention`

Share of child tours retained as independent tours.

***assumed** · status **active** · DECISIONS.md §9.2*

#### `B.activity.day_horizon_s`

Simulation day horizon, 30 hours. Matches RUN.qsim.end_time_h. No leg may arrive after it; the P1 chains had 1.77% arriving late, latest 36.0 h. The build script writes it as the expression 30 * 3600, which is not a literal and so is not compared by value in the legacy-drift check.

***definition** · status **active** · DECISIONS.md §9.2*

#### `B.activity.day_purpose_mix`

Weekend purpose mix relative to the weekday. HX (serve passenger) is derived demand - it exists because somebody else has to be somewhere - so it falls at the weekend with the school run without vanishing, because weekend escorting is sport and social rather than education. Like every other entry here it is assumed and swept; the HTS extract in the package carries no day-type dimension to estimate it from. NHB is absent: it is a leg label, not a tour purpose, so it has no day-type mix to carry.

***assumed** · status **active** · DECISIONS.md §9.2*

#### `B.activity.days_per_week`

Days each day type represents when composing a week.

***definition** · status **active** · DECISIONS.md §9.2*

#### `B.activity.departure_profile`

Probability that a tour of each purpose departs in each hour 0-23. ONE HUNDRED AND FORTY-FOUR ASSUMED NUMBERS that decide when every trip in the model happens, and therefore what the peak looks like and where congestion forms. They were a dict literal in src/build/build_activity_chains.py labelled "assumed, NSW-typical shapes", which no audit could see because a container is not a scalar and no sweep could reach. HX is a copy of HE and is derived at load rather than declared twice.

***assumed** · status **active** · DECISIONS.md §9, 15*

> **Sweep basis.** the whole profile may be reweighted by a quarter either way per hour, then renormalised. There is no Newcastle observation to bracket it: the HTS held is aggregate and reports journeys by purpose, not departure hour. A proportional sweep is the honest expression of "NSW-typical shape, magnitude unknown".

#### `B.activity.detour_factor`

Straight-line to network distance, routed over the observed A1 road graph. Replaces an assumed 1.30. The build script keeps a 1.30 fallback labelled 'assumed - C2 factors file not found'; that fallback is now this field. The build script no longer keeps its own copy: it READS THIS FIELD as the fallback when params/C2_network_factors.json is absent, so the two values that check_legacy_drift.py existed to compare are now one value.

***measured** · status **active** · DECISIONS.md §9.2*

> **Sweep basis.** the interquartile range of the per-pair ratios over 551 population-weighted zone pairs

#### `B.activity.duration_cv`

Spread of activity duration around its mean.

***assumed** · status **active** · DECISIONS.md §9.2*

#### `B.activity.escort_binding_enabled`

Whether an HX (serve passenger) tour takes its destination and departure from an actual household member's already-drawn trip, instead of drawing both from the education-attractor distribution and the HE departure profile. Not an empirical quantity: it selects which of two mechanisms builds the escort tour, exactly as B.ride.pairing_enabled does on the supply side, and false restores the pre-9.46 behaviour so the two demands are comparable within one build. Binding RE-TARGETS existing HX tours and never adds one - the HX rate stays calibrated to the observed Serve passenger share. An escorter with no bindable household trip that day (lone-person households are 26.2% of all households) falls back to the distribution draw.

***definition** · status **active** · DECISIONS.md §9.46*

#### `B.activity.escort_binding_min_gap_s`

Minimum separation between the departures of two escort tours BOUND for the same escorter, so the driver can physically make both runs.

***assumed** · status **active** · DECISIONS.md §9.46*

> **Sweep basis.** no observation bears on how closely one driver can stack two escort runs; 45 minutes covers a school-run drop-off (dwell ~5 min) plus the return at the model's own seed speeds over the observed 6.4 km escort distance. The bounds are a 15-minute back-to-back stack and a 90-minute spacing. Finer overlap - a drawn intermediate stop stretching one bound tour into the next - resolves at placement, where the later binding drops rather than shifts.

#### `B.activity.escort_binding_nonhh_scope`

Which non-household passengers an HX escort tour that found no household trip may be re-targeted to serve (9.60). The driver supply is the observed Serve-passenger rate, already generated; this decides only how far an unbound tour may look for the passenger it exists to carry. Passengers are the driverless-household class - the people household pairing structurally cannot reach.

***assumed** · status **active** · DECISIONS.md §9.60*

#### `B.activity.escort_binding_scope`

Which classes of already-drawn household trips an HX escort tour may take its destination and departure from.

***assumed** · status **active** · DECISIONS.md §9.46*

#### `B.activity.escort_excludes_ride`

Whether a person whose day includes an escort (HX) tour is denied `ride` for that day type. Measured motivation: 4,791 escort trips on the relaxed 25% arm were made BY ride - a passenger being driven in order to convey somebody, with no driver bound to either of them. Consumed by build_matsim_plans.py, which forces rideAvail=never for that person-day; the existing AvailabilityModesCalculator then withholds ride with no Java change.

***derived** · status **active** · DECISIONS.md §9.46*

> **Derived from** `B.activity.escort_requires_licence`: an escort trip is a trip made in order to convey another person, so the traveller is the driver - the same identity that already restricts HX generation to licence holders, taken through to mode choice: a person whose plan carries an escort activity cannot make that day's trips as a car passenger. Applied at the day-plan level (rideAvail=never on the escort day's population file) because MATSim's PermissibleModesCalculator is per-plan, not per-subtour; the collateral - the escorting driver cannot be driven on OTHER tours the same day - is stated, small and plausibly the truth

#### `B.activity.escort_requires_licence`

Whether a serve-passenger (HX) tour may only be drawn for a licence holder. Consumed where tours are allocated to persons.

***derived** · status **active** · DECISIONS.md §9.15*

> **Derived from** `B.population.licence_rate_by_age_band`: an escort trip is a trip made in order to convey another person, so the traveller is the driver, and a person without a licence cannot make one; the same identity as B.population.ride_requires_household_driver taken on the driver side rather than the passenger side

#### `B.activity.hts_rate_per_person_day`

Observed NSW HTS trip rate the synthesis is calibrated to reproduce. The realised rate is 3.397, 2.2% low.

***measured** · status **active** · DECISIONS.md §9.2*

#### `B.activity.p_intermediate_stop`

Probability a tour carries an intermediate stop, by purpose. WATCH THIS ONE: it decides how many sub-tours exist and therefore how freely MATSim mode choice can vary within a day. It is assumed, and it is the demand-side parameter with the most leverage over mode share. 56.7% of persons have more than one tour at the shipped values. HX (serve passenger) chains at the same rate as a discretionary tour: a driver who drops a passenger may link another stop before returning.

***assumed** · status **active** · DECISIONS.md §9.2*

#### `B.activity.p_mandatory`

Probability an employed person or student attends on a given day type.

***assumed** · status **active** · DECISIONS.md §2.4, 9.2*

> **Sweep basis.** the work entry is bounded BELOW by the census G62 observed attendance of 0.651, which bounds the sweep and is not allowed to set the value, because census night was August 2021 with 19.2% working from home

#### `B.activity.p_second_stop`

Probability of a second intermediate stop, given a first.

***assumed** · status **active** · DECISIONS.md §9.2*

#### `B.activity.plan_access_s`

Fixed per-leg overhead added to every B2 planned leg time on top of distance/speed. Not a routing or scoring quantity.

***assumed** · status **active** · DECISIONS.md §9.61*

> **Sweep basis.** fixed access-and-egress overhead per planned leg (getting to the vehicle, parking, walking in). Scaffold-only, declared per 9.61.

#### `B.activity.plan_speed_car_kmh`

Door-to-door planning speed for a car-available person, used by the B2 chain builder to time tours (straight-line distance at this speed plus B.activity.plan_access_s). Not a routing or scoring quantity.

***assumed** · status **active** · DECISIONS.md §9.61*

> **Sweep basis.** urban door-to-door average including parking and access; brackets typical metropolitan network speeds. It decides only the B2 chain-timing scaffold (whether tours fit a day, and their planned departure spacing) - the mobsim re-times every leg physically - but a value that decides anything is declared (9.61: it sat as a bare 26.0 inside time_tour's expression, invisible to the ledger's scanner).

#### `B.activity.plan_speed_nocar_kmh`

Door-to-door planning speed for a person without car availability, used by the B2 chain builder to time tours. Not a routing or scoring quantity.

***assumed** · status **active** · DECISIONS.md §9.61*

> **Sweep basis.** a blend of walk, cycle and bus door-to-door speeds for a person without a car. Same scaffold-only role, same 9.61 declaration rationale, as plan_speed_car_kmh.

#### `B.activity.weekend_to_weekday`

Weekend vs weekday travel, measured from the RMS traffic counts own WEEKDAYS and WEEKENDS periods. Replaces an assumed value that implied 0.825. Vehicle volume, not person trips.

***measured** · status **active** · DECISIONS.md §9.2*

> **Sweep basis.** observed across 551 RMS station-years

#### `B.bike.pce`

Road capacity a network-simulated cyclist consumes. Unlike a pedestrian, a cyclist genuinely takes carriageway space - this is the field that makes bike PHYSICAL rather than decorative.

***literature** · status **active** · DECISIONS.md §9.54*

> **Sweep basis.** Austroads and HCM passenger-car-equivalent ranges for on-road bicycles run from about 0.1 (wide kerbside lane, filtering) to about 0.4 (narrow lane, no filtering). No local lane-width-conditioned observation exists, so the class low-mid value is taken and the published range is swept.

#### `B.bike.speed_ms`

Cycling speed, carried by the bike vehicle type as its maximum velocity: a cyclist traverses each link at the lower of this and the link's free speed, in the router (CappedSpeedTravelTime) and the mobsim alike - one declared value, both consumers.

***literature** · status **active** · DECISIONS.md §9.54*

> **Sweep basis.** Carried over verbatim from the retired RUN.routing.teleported_bike_speed_ms (9.54): the disagreement between published MATSim practice and ATAP cycling speeds is unresolved and stays swept, not repinned. The quantity is unchanged - the speed a cyclist rides at - only its consumer moved from the teleportation formula to the vehicle type's maximumVelocity.

#### `B.counts.heavy_vehicle_share`

Heavy vehicle share, in two roles. (1) AT COMPARISON TIME: the count comparison uses the station's own observed share where classified and this median at the remaining 96 stations - only 3 of the 34 calibration stations are classified, so the assumed case is the usual one there. (2) AT GENERATION TIME (9.49): the through tier splits each cordon gate's volume into car and truck by the gate station's own observed heavy share, and a gate whose station is unclassified falls back to this median.

***measured** · status **active** · DECISIONS.md §12.2a*

> **Sweep basis.** the observed range across the 23 stations that carry a classified count

#### `B.counts.station_match_radius_m`

Radius within which a permanent traffic count station may be attached to a network link it is taken to count. It decides which road_aadt targets are scorable at all, so it is a lever on the reported fit, not a plotting tolerance: 189 of 203 link matches are by name AND proximity, 14 by proximity alone. Was a CLI default typed into map_count_stations.py with no provenance and no range (issue 19).

***assumed** · status **active** · DECISIONS.md §12.1*

> **Sweep basis.** measured on data/processed/validation/count_station_links.csv: the largest ACCEPTED match is 119.7 m, so 120 m is exactly binding. Tightening costs targets at a measured rate - at 100 m six of the 116 matched stations lose their link and at 60 m twenty-three do - which is the lower bound. The upper bound is the current value because loosening cannot gain anything already in the file; whether a larger radius would resolve the three stations that match nothing (issue 10) has NOT been tested, and testing it means re-running the mapper and regenerating a committed artefact.

#### `B.counts.vehicles_per_car_leg`

A car leg contributes one vehicle to a count. Derived from occupancy 1.3503: observed vehicle trips ARE driver trips.

***derived** · status **active** · DECISIONS.md §12.2a*

> **Derived from** `C.constraint.vehicle_occupancy`: observed vehicle trips ARE driver trips at occupancy 1.3503, so a car leg contributes exactly one vehicle

#### `B.counts.vehicles_per_ride_leg`

A ride leg contributes NO vehicle: the passenger rides in a vehicle already counted. Holds only while the modelled ride:car ratio matches the observed passenger:driver ratio, which is what C.asc.car_passenger is constrained to reproduce. What stays genuinely unmodelled is the escort trip - B2 generates none, so a driver travelling solely to carry someone is absent from both the car legs and the counts explanation (issue 11).

***derived** · status **active** · DECISIONS.md §12.2a*

> **Derived from** `C.constraint.vehicle_occupancy`, `C.asc.car_passenger`: a passenger rides in a vehicle already counted, so a ride leg contributes zero - valid only while the modelled ride:car ratio matches the observed passenger:driver ratio

#### `B.external.agent_profile`

Placeholder person attributes for an external boundary agent, which has no B1 household. Definitional placeholders for a tier that is a boundary treatment rather than a synthesised population, not estimates of anything. Ride availability is deliberately NOT among them: see B.external.agent_ride_available.

***definition** · status **active** · DECISIONS.md §9.15*

#### `B.external.agent_ride_available`

Whether an external boundary agent may travel as a car passenger.

***derived** · status **active** · DECISIONS.md §9.15*

> **Derived from** `B.population.ride_requires_household_driver`: a person may be a car passenger only if their household holds a vehicle AND contains another licence holder; an external boundary agent is household-less by construction, so that condition cannot be satisfied and ride is unavailable. Resolving the same unknown the other way made 432 of 962 external trips car-passenger trips with no possible driver

#### `B.external.cordon_road_classes`

Road classes whose network nodes may serve as an external station, that is a cordon entry point. Defines what counts as a road capable of carrying boundary demand into the study area; a residential cul-de-sac is not one.

***definition** · status **active** · DECISIONS.md §9.15*

#### `B.external.interaction_rate`

Rate at which external-tier residents interact with the core. LOCALISABLE BUT NOT YET AVAILABLE: the ABS journey-to-work origin-destination table (SA2 usual residence x SA2 place of work) would settle it. The package holds the place-of-work side but not the pairing. A standard TableBuilder extract, not a formal request (DECISIONS.md 13 priority 11).

***assumed** · status **active** · DECISIONS.md §9.2, 13*

#### `B.external.person_id_base`

Id offset that keeps external agents distinguishable from core agents.

***definition** · status **active** · DECISIONS.md §9.2*

#### `B.external.purpose_split`

Purpose split for external boundary demand.

***assumed** · status **active** · DECISIONS.md §9.2*

#### `B.external.through_corridor_match_km`

A boundary-crossing road edge becomes a through-traffic gate only if a calibration count station ON THE SAME NAMED ROAD lies within this distance of the crossing; the nearest such station anchors the gate's volume. Beyond it the corridor is unobserved and generates nothing.

***assumed** · status **active** · DECISIONS.md §9.41*

> **Sweep basis.** MEASURED MOTIVATION: only one calibration station sits within 2 km of the boundary crossing it measures (the M1 at Wyee, 273 m); the others that observe a boundary corridor sit 16-24 km inside it (Pacific Highway at Tomago, New England Highway at Tarro). Matching by same road NAME along the corridor is what the held data supports; the radius bounds how far along the corridor a station may sit and still anchor the gate. An inland station overstates the boundary volume by its local traffic - absorbed, stated, by the through_share sweep.

#### `B.external.through_min_separation_km`

Minimum straight-line separation between the entry gate and the exit gate for a generated trip to count as through traffic. Exit gates closer than this to the entry are excluded from its destination set.

***assumed** · status **active** · DECISIONS.md §9.41*

> **Sweep basis.** The study area spans roughly 60-90 km. A through trip must actually cross it: two gates a few kilometres apart on the same corridor edge would otherwise exchange 'through' trips that never leave the boundary region. 30 km forces entry and exit to lie on opposite sides; the sweep brackets how strict that requirement is.

#### `B.external.through_outside_min_m`

A boundary crossing counts as leaving the study area only if some endpoint of its ROAD (any same-named edge within the corridor-match distance of the crossing) lies at least this far beyond the dissolved boundary. Road-level, not edge-level: a motorway's crossing way often ends metres past the polygon while the road continues on further ways. Filters water crossings INSIDE the area (harbour bridges) out of the gate set.

***assumed** · status **active** · DECISIONS.md §9.41*

> **Sweep basis.** The dissolved study boundary includes the coastline and the harbour, so a road bridging the Hunter River 'crosses the boundary' without leaving the study area - Hannell Street at Wickham is the measured example (nothing of it reaches more than 2 m beyond the polygon), and its station would otherwise seed through traffic entering in central Newcastle. Genuine exits measured on the rebuilt layer put same-named endpoints 1-8 km beyond the boundary while their crossing EDGES often end 31-203 m out, so the evidence is road-level. 1 km separates a departure from a river crossing; the sweep brackets that judgement.

#### `B.external.through_share`

Share of the AADT measured at a cordon-gate calibration count station that is through traffic - vehicles whose journey neither starts nor ends inside the study area. Applied symmetrically: half of the through component enters at the gate and half exits, so the generated inbound volume at gate i is 0.5 x through_share x AADT_i. Seeded from CALIBRATION count rows only; the split filter is structural in the builder and no holdout row is ever read.

***assumed** · status **active** · DECISIONS.md §9.41*

> **Sweep basis.** No through-share survey exists for the study boundary and no journey-linked data can separate through from local traffic at a count station, so the share is assumed and swept wide. The motivating observation is V113 (the M1 at Wyee, 48,016 AADT, a calibration row): the Sydney-Newcastle motorway at the boundary is the road most dominated by through traffic, and the model routed zero vehicles onto it because the demand contained no through movement at all (issue #20).

#### `B.freight.attractor_divisions`

The ANZSIC divisions counted as freight-generating when weighting zones for the internal freight OD draw: agriculture, mining, manufacturing, utilities, construction, wholesale, retail and transport/warehousing - the goods-handling divisions of the standard classification. A vocabulary over the observed census place-of-work table (D1_employment_by_anzsic_POW_SA2.csv), not a tuned value: the WEIGHT each zone gets is its observed employment in these divisions.

***definition** · status **active** · DECISIONS.md §9.49*

#### `B.freight.gravity_beta_per_km`

Distance decay (negative-exponential, per km) for the internal freight destination draw over the freight-employment attractor. Controls the modelled truck trip length, which no local observation constrains.

***assumed** · status **active** · DECISIONS.md §9.49*

> **Sweep basis.** No freight OD observation exists for the study area, so the destination-choice decay is assumed and swept wide. The bounds bracket the person-purpose decays this package SOLVES from observed trip lengths (roughly 0.05-0.25 per km across purposes and home LGAs, DECISIONS.md 9.40): the lower bound lets a truck trip run materially longer than a discretionary person trip, which is what line-haul freight does; the upper bound pins it to short urban delivery.

#### `B.freight.length_m`

Stated length of the truck vehicle type in the vehicles file. Does not reach the traffic model - space and flow consumption run on PCE - and is held fixed rather than swept for exactly that reason.

***literature** · status **active** · DECISIONS.md §9.49*

> **Held fixed.** Cosmetic in the queue model: MATSim's qsim consumes road space and flow through passengerCarEquivalents (B.freight.pce), not through vehicle length, so no output varies across this value. Recorded because the vehicle type must state a length; a typical rigid-truck figure is used.
>
> *Departure requires: a logged decision*

#### `B.freight.max_speed_kmh`

Maximum speed of a modelled heavy vehicle: the NSW regulated limit for vehicles over 4.5 t GVM. A fact of law, not a tunable - it binds only on links whose free speed exceeds it (motorway classes at 110 km/h).

***definition** · status **active** · DECISIONS.md §9.49*

#### `B.freight.pce`

Passenger-car equivalents of one modelled heavy vehicle - how much road capacity and storage a truck consumes in the mobsim relative to a car. This is the field that makes freight PHYSICAL: at PCE > 1 a truck changes the travel time of every vehicle sharing its links.

***literature** · status **active** · DECISIONS.md §9.49*

> **Sweep basis.** Austroads and HCM passenger-car-equivalent ranges for heavy commercial vehicles on level urban roads run from about 1.5 (rigid truck, flat) to 3.5 (articulated, interrupted flow); no Newcastle-specific fleet mix is observed, so the class mid-value is taken and the published range is swept. For scale: the bus fleet in this package carries the pt2matsim literature figure 2.8.

#### `B.freight.trip_ratio`

Internal heavy-vehicle trips generated per resident light-vehicle trip, applied to the observed car-driver share of the day's generated person trips. This is the background freight VOLUME knob: it is a declared, sweepable background load, not an estimate of freight demand (issue #24). Through freight is seeded separately at the cordon gates from each gate station's own observed heavy share and is not scaled by this field.

***assumed** · status **active** · DECISIONS.md §9.49*

> **Sweep basis.** The default restates the MEASURED median heavy share of classified station flow (B.counts.heavy_vehicle_share, 0.0652) as a ratio to light vehicles: 0.0652 / (1 - 0.0652). What is ASSUMED is the transfer from a flow share at count stations to a trip share of the resident vehicle-trip base - trucks travel further per trip than cars, so a flow share overstates a trip share by an unobserved factor, and no freight OD survey exists for this or any comparable city in the package. The lower bound is zero, which turns the internal freight layer off entirely so its whole effect is measurable as a sweep member; the upper bound is roughly the classified stations' upper-quartile share expressed the same way.

#### `B.mode.seed_split`

The mode split the co-evolution STARTS from, conditioned only on car availability from B1. UNIFORM OVER THE USABLE MODES AND DELIBERATELY A BAD GUESS: it starts the search far from the observed point so that arriving there is evidence about the model rather than about the seed. It is a definition, not an assumption, because "uniform over what a person can use" is fully determined by B1 car availability and has no free share to sweep. What is swept is the CHOICE of seed - see B.mode.seed_split_informed.

***definition** · status **active** · DECISIONS.md §9.6, 9.7*

#### `B.mode.seed_split_informed`

The informed seed the uniform one replaced, retained so the seed-independence claim is testable by running both. Selected with --seed-mode informed. Approximately the observed split, which is exactly why it is NOT the default: seeding at the answer makes reaching the answer uninformative.

***assumed** · status **active** · DECISIONS.md §9.6, 9.7*

> **Sweep basis.** the sweep is over WHICH SEED IS USED, not over the shares. These are the only two seeds the plan builder can produce, and DECISIONS.md 9.7 reports the measured difference between the runs they produce. That is what makes "the result does not depend on the seed" a claim that can be tested rather than asserted (DECISIONS.md 9.6).

#### `B.motorbike.length_m`

Stated length of the motorbike vehicle type in the vehicles file. Does not reach the traffic model - space and flow run on PCE - and is held fixed for exactly that reason.

***literature** · status **active** · DECISIONS.md §9.52*

> **Held fixed.** Cosmetic in the queue model: MATSim's qsim consumes road space and flow through passengerCarEquivalents (B.motorbike.pce), not through vehicle length, so no output varies across this value. Recorded because the vehicle type must state a length; a typical motorcycle figure is used.
>
> *Departure requires: a logged decision*

#### `B.motorbike.pce`

Passenger-car equivalents of one modelled motorbike - it consumes LESS road capacity than a car. This is the field that makes the mode PHYSICAL in the mobsim.

***literature** · status **active** · DECISIONS.md §9.52*

> **Sweep basis.** Austroads and HCM passenger-car-equivalent ranges for motorcycles in urban traffic run from about 0.3 (filtering, uncongested) to 0.75 (no filtering, interrupted flow); no local fleet-mix or filtering observation exists, so the class low-mid value is taken and the published range is swept.

#### `B.motorbike.trip_share`

Share of resident person trips made by motorbike, realised as a PERSON-LEVEL carve: a licensed, car-available adult becomes a motorbike user (their whole day locks to the mode - vehicle continuity is chain-based by nature) with the probability that makes carved persons' trips this share of all trips. Carved FROM car-driver demand, which is where the HTS and census place motorcyclists - so the car comparison folds motorbike back in at fit time (fit.py) and the carve never invents a trip.

***assumed** · status **active** · DECISIONS.md §9.52*

> **Sweep basis.** The default restates the MEASURED census G62 one-method journey-to-work share for the 1,500 core SA1s: 653 of 179,761 journeys = 0.363% by motorbike/scooter (docs/design/mode-individualisation.md). What is ASSUMED is the transfer from a commute share to an all-purpose trip share - the HTS cannot separate motorcycle trips (its data document places them inside Vehicle driver/passenger), so no all-purpose observation exists. The lower bound is zero, which turns the mode off so its whole effect is a sweep member; the upper bound is roughly 3x the commute anchor, spanning the plausible all-purpose range for a mode whose registration share exceeds its trip share.

#### `B.network_factors.distance_band`

Half-width of the distance band used when drawing a destination for the network-factor measurement.

***assumed** · status **active** · DECISIONS.md §9.2, 15*

> **Sweep basis.** width of the distance band a destination is drawn from, as a share either side of the observed trip length. Wide enough that every origin has candidates, narrow enough that the measurement stays at the mode’s own length scale.

#### `B.network_factors.min_pair_m`

Minimum straight-line distance between two zone centroids for the pair to enter the detour measurement.

***assumed** · status **active** · DECISIONS.md §9.2, 15*

> **Sweep basis.** the shortest straight-line separation a measured pair may have. Below it the network detour ratio is dominated by which side of the block each centroid fell on rather than by the road graph, and above it short trips - the ones walk needs - stop being represented.

#### `B.network_factors.n_pairs`

Zone pairs routed over the observed road graph to measure B.activity.detour_factor. A keyword default AND an argparse default carrying the same number, neither declared.

***assumed** · status **active** · DECISIONS.md §9.2, 15*

> **Sweep basis.** how many population-weighted zone pairs the detour factor is measured over. It is a MONTE CARLO SAMPLE SIZE, so the sweep is about the precision of the measurement rather than about the city: too few pairs and the ratio is noisy, more than a few thousand buys little and costs routing time.

#### `B.opal.journey_linked`

Journey-linked Opal. NOT OBTAINED - a formal TfNSW request is outstanding. Proposal 6.1 calls it 'the difference between a good model and a guess'. It is what would let C.transfer.beta_transfer_penalty_min be ESTIMATED rather than swept. Until it lands the transfer penalty stays a curve across 3-15 min.

***assumed** · status **unobtained** · DECISIONS.md §0, 13 · proposal §6.1, 7.2*

#### `B.population.age_bands`

Age banding for population synthesis. Follows the census table structure.

***definition** · status **active** · DECISIONS.md §9.1*

#### `B.population.bike_available_rate`

Share of synthetic persons with a bicycle available to them. Until this field existed, car was the only mode whose ownership was modelled while bike was silently available to everyone - a structural bias against car in the choice set itself, undeclared anywhere (issue #29, SPEC_AUDIT A3). Drawn deterministically per person in build_matsim_plans.py and consumed by the same availability calculator that enforces rideAvail. External boundary agents keep bike available: they are household-less by construction, so no ownership identity exists to derive a denial from, and the choice is recorded in DECISIONS.md 9.39.

***assumed** · status **active** · DECISIONS.md §9.39*

> **Sweep basis.** The census carries no bicycle-ownership variable, so any rate is assumed. The upper bound 1.0 is the previous silent behaviour (bike available to everyone), retained in the sweep so the constraint's own effect is measurable; the lower bound allows for household access well below half. Re-size against the observed 3.2% bike share only AFTER the post-rebuild run re-measures the modelled share - the old 5x was measured on a model that no longer exists (issue #29).

#### `B.population.build_sample_share`

Share of the synthetic population BUILT. One, always: this is the build, not the run. Sampling for a run is RUN.sample.fraction, applied by the harness to a full population - and conflating the two would make every run a sample of a sample. Declared so the distinction is visible; it was an argparse default of 1.0 sitting next to a run-time fraction of the same shape.

***definition** · status **active** · DECISIONS.md §15*

#### `B.population.licence_rate_by_age_band`

Driver licence holding by age band, aligned to B.population.age_bands.

***literature** · status **active** · DECISIONS.md §9.1*

#### `B.population.ride_requires_household_driver`

Whether `ride` is withheld from a person with nobody to drive them. MATSim's standard treatment lets any agent be a car passenger on any trip; DECISIONS.md 9.10 measures the cost at 0.72 of legs against an observed 0.206, unmoved by a tenfold sample increase, i.e. 5.9 people per car. Core MATSim can restrict `car` per person via `carAvail` but has no equivalent for `ride`, and subtourModeChoice.modes is global, so the fix is a person attribute honoured by a custom PermissibleModesCalculator (src/java/citysim/). Setting this false restores the previous behaviour for comparison. RESIDUAL LIMITATION, stated not hidden: this makes ride available or not per person, it does NOT bind a passenger to a specific driver at a specific time - that is the socnetsim joint-plans contrib (Dubernet & Axhausen), absent from the pinned jar and out of scope.

***derived** · status **active** · DECISIONS.md §8.5, 9.10, 15 · proposal §9*

> **Derived from** `B.seed.master`: a person may be a car passenger only if their B1 household holds at least one vehicle AND contains at least one OTHER licence holder who could drive them; computed from B1_synthetic_population.csv household_id, household_vehicles and licence_holder, so it is derived from the synthetic population rather than chosen

#### `B.ride.max_passengers_per_vehicle`

How many passengers one driver's leg may carry. Without a cap a single driver would serve every passenger their household offered - the same unbounded-supply defect that rideAvail removed on the availability side, where an unconstrained model put 5.9 people in every car (9.10). Consumed by src/java/citysim/RidePairingEngine.

***assumed** · status **active** · DECISIONS.md §9.44 · MATSim `ridePairing.maxPassengersPerVehicle`*

> **Sweep basis.** The upper bound is the physical one: a five-seat car minus the driver, which is what the overwhelming majority of the registered light fleet is. The lower bound is one passenger per driver, the most conservative reading of a household lift. No observation splits household lifts by party size - HTS reports Vehicle passenger as a share of trips, not an occupancy distribution - so the cap is assumed within physical bounds and swept. It is not binding at the measured pairing rates and the diagnostic reports how often it refuses, so a run in which it starts to bind is visible rather than silent.

#### `B.ride.pairing_enabled`

Whether a `ride` leg may NAME the household member who drives it, and take that driver's realised travel time instead of its own routed one. Not an empirical quantity: it selects which of two mechanisms the model runs, exactly as B.population.ride_requires_household_driver does on the availability side, and false restores the pre-9.44 behaviour so the two are comparable within one build. The pairing itself is made at the BeforeMobsim boundary, where every selected plan is final and nothing will move until the mobsim runs - which is why SubtourModeChoice cannot destroy it the way it destroys a pairing baked into plans. Consumed by src/java/citysim/RidePairingEngine.

***definition** · status **active** · DECISIONS.md §9.44 · proposal §9 · MATSim `ridePairing.enabled`*

#### `B.ride.pairing_rule`

The spatial coincidence a pairing requires, expressed on LINK IDENTITY rather than on distance - no coordinate, no radius and no place enters the model, so the rule reads identically for a city the framework has never seen. `both_links` means the driver's leg starts and ends on the same links as the passenger's, i.e. the passenger is in the car for the whole of the driver's trip. Consumed by src/java/citysim/RidePairingEngine.

***assumed** · status **active** · DECISIONS.md §9.44 · MATSim `ridePairing.rule`*

#### `B.ride.pairing_window_min`

How far apart a passenger's and a driver's PLANNED departures may be and still be treated as one trip. This is the tolerance the pairing is allowed, NOT a modelled waiting time: Tier 1 does not move the passenger's departure, because shifting it would cascade through the rest of that person's day and the blast radius of the change is deliberately bounded. Who adapts is nonetheless DECLARED rather than left open - the passenger does, since the driver's plan cascades further - and the unmodelled sub-window adjustment is a stated limitation, not a silent one. Consumed by src/java/citysim/RidePairingEngine.

***assumed** · status **active** · DECISIONS.md §9.44 · MATSim `ridePairing.windowMinutes`*

> **Sweep basis.** No local observation of how far apart a household lift's two departures may be exists, and HTS carries no household-linked trip records at all, so the tolerance is assumed and swept rather than fitted. The lower bound is a tight coincidence; the upper is an hour, beyond which calling two departures one trip stops being credible. MEASURED SENSITIVITY on the relaxed 25% pilot arm (9.44): the share of ride legs with ANY household car leg in the window runs 1.1% at +-5 min, 3.1% at +-15, 5.6% at +-30 and 15.1% at +-120, so this field moves the pairing rate by an order of magnitude and may not be pinned.

#### `B.ride.physical_boarding`

Whether a PAIRED ride passenger physically BOARDS the driver's vehicle in the mobsim (a real PersonEntersVehicleEvent, every link ridden, alighting at the shared destination link) instead of inheriting the driver's clock by teleport. Selects a mechanism under the 9.51 owner directive (every ride physically in a car); false restores the 9.44 Tier-1 behaviour exactly, so the two are comparable within one build. A booked passenger whose car has already left falls back to Tier 1 and is counted - a miss is the measured window layer of the realisation gap wearing its physical face, reported never hidden. Consumed by citysim.JointRideEngine via citysim.RidePairingEngine's bookings.

***definition** · status **active** · DECISIONS.md §9.53 · MATSim `ridePairing.physicalBoarding`*

#### `B.ride.pickup_dwell_s`

Seconds added to a PAIRED passenger's travel time for the act of being picked up. Zero by default: the mechanism Tier 1 asserts is that the passenger experiences the driver's realised trip, and nothing in the package observes a friction on top of that. This field exists so the question can be swept rather than assumed away. Consumed by src/java/citysim/RidePairingEngine.

***assumed** · status **active** · DECISIONS.md §9.44 · MATSim `ridePairing.pickupDwellSeconds`*

> **Sweep basis.** No measurement of pickup dwell exists for this city, or for any comparable one in the package, so the value is swept and NEVER fitted. The default is deliberately NEUTRAL. The car-minus-ride residual this lane exists to remove was MEASURED from the pilot arms' own output_legs at about 5 s at 25% and 13 s at 10%, flat across every distance bin below 50 km; a one-minute friction would therefore be five to twelve times the entire quantity it was meant to explain. Sizing this to close that gap is calibration wearing a mechanism's clothes and was REFUSED. The upper bound is two minutes, which is already far beyond what the residual can bear, and exists so the sweep can show that.

#### `B.ride.remode_unpaired`

Whether an UNPAIRED ride leg is re-moded to network-simulated walk at the BeforeMobsim boundary - the 9.51 owner directive's own ruling (every ride physically in a car, no exceptions, no teleportation) enacted without inventing a parameter: a ride trip no household driver can physically serve is not a ride trip, it walks, scores accordingly, and co-evolution reassigns the tour - so the surviving ride share is EMERGENT from the physical driver supply rather than declared. False keeps Tier 1's teleport for the unpaired, for comparability within one build. Consumed by citysim.RidePairingEngine.

***definition** · status **active** · DECISIONS.md §9.55 · MATSim `ridePairing.remodeUnpaired`*

#### `B.ride.wait_for_driver`

Whether a booked passenger whose car is not at the meeting point yet physically WAITS for it, bounded by the declared pairing window (B.ride.pairing_window_min - the same tolerance the booking was made under, so no second number is invented). The 9.53 boarding engine could board only a car ALREADY parked at the link; a passenger departing first was a counted miss falling back to teleport - the measured x6.91 window layer of the realisation gap wearing its physical face. Waiting is real elapsed time: a timed-out passenger completes on the Tier-1 clock FROM THE TIMEOUT, so waiting costs what waiting costs and scores accordingly. False restores the 9.53 behaviour. Consumed by citysim.JointRideEngine.

***definition** · status **active** · DECISIONS.md §9.60 · MATSim `ridePairing.waitForDriver`*

#### `B.seed.master`

The one seed everything synthetic derives from. CLAUDE.md forbids unseeded randomness, wall-clock dependence and dict/set-ordering dependence anywhere in a build script. Changing this changes every synthetic artefact.

***definition** · status **active** · DECISIONS.md §9.1*

#### `B.walk.pce`

Road capacity a network-simulated pedestrian consumes: zero, by definition - a walker moves along the network beside the carriageway (the sidewalk, expressed in queue arithmetic), physically present on every link (real LinkEnter/LinkLeave events, speed-capped at the declared walking speed) while neither impeding nor being impeded by motor traffic. Not a tunable: a pedestrian who consumed road capacity would be walking in the traffic lane.

***definition** · status **active** · DECISIONS.md §9.54*

## Calibration (P4 deliverables 4-6)

*`cities/newcastle/registry/CAL_calibration.json` - 6 fields*

What the calibration loop is allowed to move, what it scores itself against, and the guards that stop it fitting more parameters than the data can identify. The objective deliberately excludes traffic counts: DECISIONS.md 9.14 forbids count-based calibration while boundary through traffic is unrepresented, and the loop enforces that rather than remembering it.

| Field | Value | Units | Provenance | Sweep |
|---|---|---|---|---|
| `CAL.objective.components` | `{"mode_share.mean_abs_pp": 1.0}` | weight_per_fit_component | `definition` | - |
| `CAL.objective.include_counts` | `false` | boolean | `derived` | derived: the external tier represents boundary demand from one SA4 to the north |
| `CAL.objective.independent_targets` | `4` | count | `derived` | derived: five HTS mode-share targets are reported but they are shares of one to |
| `CAL.search.convergence_delta` | `0.25` | percentage_points | `assumed` | 0.1 - 1 |
| `CAL.search.max_rounds` | `3` | count | `assumed` | 1 - 6 |
| `CAL.search.points_per_parameter` | `3` | count | `assumed` | 3 - 7 |

#### `CAL.objective.components`

Dotted paths into _fit.json that form the scalar objective, with their weights. ONE component, and that is not an oversight: patronage scores n=0 in a single day-type run (the contemporary monthly target needs WEEKDAY, SAT and SUN composed over a calendar month, and the rest are a pre-pandemic PT market), and counts are excluded by CAL.objective.include_counts. Mode share is what is left. A component named here that is missing from a fit output is a hard error, never a silent zero.

***definition** · status **active** · DECISIONS.md §9.16, 12.1*

#### `CAL.objective.include_counts`

Whether traffic counts may enter the calibration objective. FALSE, and the loop refuses to start if it is set true without a recorded departure. Counts are still SCORED and REPORTED on every run; they are simply not optimised against.

***derived** · status **active** · DECISIONS.md §9.14, 9.15*

> **Derived from** `B.external.interaction_rate`: the external tier represents boundary demand from one SA4 to the north-west and no through traffic at all, so every boundary-adjacent count is biased low by construction; tuning core network parameters against those counts would be compensating for demand the model does not contain, which is the count analogue of the ASC absorption proposal 9 names as the primary threat to validity (DECISIONS.md 9.14, 9.15)

#### `CAL.objective.independent_targets`

How many independent numbers the objective actually contains. The loop refuses to move more free parameters than this, because a fit of more parameters than data is not a calibration.

***derived** · status **active** · DECISIONS.md §12.1*

> **Derived from** `CAL.objective.components`: five HTS mode-share targets are reported but they are shares of one total and sum to 1, so only four are independent; DECISIONS.md 12.1 reaches the same number from the other direction, that the effective information in the calibration half is roughly four mode-share degrees of freedom plus one patronage level plus the counts

#### `CAL.search.convergence_delta`

A coordinate pass that improves the objective by less than this ends the search. In the units of the objective, which is mean absolute mode-share error in percentage points. Below roughly 0.1 pp the search would be chasing seed noise rather than parameter effects, which DECISIONS.md 9.7 measured at the same order.

***assumed** · status **active** · DECISIONS.md §9.16*

#### `CAL.search.max_rounds`

Maximum coordinate-descent passes over the free parameters. The loop stops earlier if a pass improves the objective by less than CAL.search.convergence_delta.

***assumed** · status **active** · DECISIONS.md §9.16*

#### `CAL.search.points_per_parameter`

Points evaluated along each parameter's declared sweep interval in one coordinate pass, endpoints included. Three is the smallest number that can show curvature. Each point is a full run, so this multiplies wall clock directly.

***assumed** · status **active** · DECISIONS.md §9.16*

## Behavioural parameters (C1)

*`cities/newcastle/registry/C_behaviour.json` - 55 fields*

Proposal 6.2 calls this the layer that decides the answer. It is also the layer with no Newcastle measurement in it: of the twenty distinct parameters, ten are assumed, eight are literature and two are definitional. Everything here is therefore either swept or explicitly held fixed under a stated rule - see the sweep and held_fixed keys. The per-segment C1 table (30 sets = 5 segments x 6 purposes) is generated from these fields by src/build/build_params.py; the registry holds the parameters, the CSV holds their expansion.

| Field | Value | Units | Provenance | Sweep |
|---|---|---|---|---|
| `C.asc.bus` | `-1.05` | utils | `assumed` | **held fixed** |
| `C.asc.car_driver` | `0.0` | utils | `definition` | - |
| `C.asc.car_passenger` | `-0.85` | utils | `assumed` | **held fixed** |
| `C.asc.cycle` | `-1.35` | utils | `assumed` | **held fixed** |
| `C.asc.light_rail` | `-0.75` | utils | `assumed` | **held fixed** |
| `C.asc.rail` | `-0.65` | utils | `assumed` | **held fixed** |
| `C.asc.walk` | `0.35` | utils | `assumed` | **held fixed** |
| `C.constraint.passenger_per_driver` | `0.3503` | ratio | `derived` | 0.2493 - 0.394 |
| `C.constraint.trip_length_km.bike` | `5.2` | kilometres_per_trip | `measured` | 3.1 - 5.2 |
| `C.constraint.trip_length_km.car` | `10.2` | kilometres_per_trip | `measured` | 6.6 - 10.8 |
| `C.constraint.trip_length_km.pt` | `23.4` | kilometres_per_trip | `measured` | 15.9 - 24.5 |
| `C.constraint.trip_length_km.ride` | `9.8` | kilometres_per_trip | `measured` | 5.6 - 9.8 |
| `C.constraint.trip_length_km.walk` | `0.7` | kilometres_per_trip | `measured` | 0.7 - 1.1 |
| `C.constraint.trip_time_min.bike` | `19.2` | minutes_per_trip | `measured` | 15.7 - 19.4 |
| `C.constraint.trip_time_min.car` | `17.2` | minutes_per_trip | `measured` | 14.5 - 17.6 |
| `C.constraint.trip_time_min.pt` | `34.4` | minutes_per_trip | `measured` | 30.7 - 37.7 |
| `C.constraint.trip_time_min.ride` | `15.5` | minutes_per_trip | `measured` | 12.2 - 15.5 |
| `C.constraint.trip_time_min.walk` | `12.3` | minutes_per_trip | `measured` | 10.6 - 14.8 |
| `C.constraint.vehicle_occupancy` | `1.3503` | persons_per_vehicle | `measured` | 1.2493 - 1.394 |
| `C.crowding.seated_multiplier` | `1.0` | ratio | `literature` | 1 - 1.15 |
| `C.crowding.standing_multiplier` | `1.45` | ratio | `literature` | 1.2 - 1.8 |
| `C.gradient.downhill_penalty_per_pct` | `0.02` | utils_per_percent_grade | `assumed` | 0 - 0.05 |
| `C.gradient.uphill_penalty_per_pct` | `0.09` | utils_per_percent_grade | `assumed` | 0.05 - 0.14 |
| `C.nesting.active_coefficient` | `0.7` | dimensionless | `assumed` | 0.5 - 0.95 |
| `C.nesting.private_coefficient` | `0.8` | dimensionless | `assumed` | 0.5 - 0.95 |
| `C.nesting.pt_coefficient` | `0.65` | dimensionless | `assumed` | 0.5 - 0.95 |
| `C.scoring.activity_minimal_applied_s` | *(null - unobtained)* | seconds | `derived` | derived: minimalDuration[a] = min(C.scoring.activity_minimal_duration_s, C.scor |
| `C.scoring.activity_minimal_duration_s` | `900` | seconds | `assumed` | 300 - 1800 |
| `C.scoring.activity_typical_duration_s` | `{"home": 43200, "work": 28800, "education": 21600, "shopping": 3600, "other": 7200, "business": 3600, "esco...` | seconds | `assumed` | plus/minus 25% |
| `C.scoring.marginal_utility_of_money` | `1.0` | utils_per_AUD | `definition` | - |
| `C.scoring.marginal_utility_of_traveling` | *(null - unobtained)* | utils_per_hour | `derived` | derived: marginalUtilityOfTraveling[m] = performing - trip_weighted_VOT * beta[ |
| `C.scoring.mode_constant` | *(null - unobtained)* | utils | `derived` | derived: constant[m] = the C1 alternative-specific constant for the mode m maps |
| `C.scoring.monetary_distance_rate` | `{"car": -0.00018, "ride": -0.00018, "pt": 0.0, "walk": 0.0, "bike": 0.0, "truck": 0.0, "motorbike": 0.0, "n...` | AUD_per_metre | `derived` | derived: a kilometre in a car costs the same kilometre whether you are in the d |
| `C.scoring.performing_utils_per_h` | `6.0` | utils_per_hour | `literature` | 4 - 8 |
| `C.scoring.utility_of_line_switch` | *(null - unobtained)* | utils | `derived` | derived: utilityOfLineSwitch = -(C.transfer.penalty_min / 60) * trip_weighted_V |
| `C.scoring.waiting_pt` | *(null - unobtained)* | utils_per_hour | `derived` | derived: waitingPt = performing - trip_weighted_VOT * beta_wait * marginalUtili |
| `C.time_weights.beta_bike_mode` | `1.21` | ratio_to_ivt | `literature` | 1 - 1.3 |
| `C.time_weights.beta_headway` | `0.5` | ratio_to_ivt | `literature` | 0.35 - 0.65 |
| `C.time_weights.beta_ivt` | `1.0` | ratio_to_ivt | `definition` | - |
| `C.time_weights.beta_reliability` | `1.3` | ratio_to_ivt | `literature` | 0.8 - 1.8 |
| `C.time_weights.beta_wait` | `2.0` | ratio_to_ivt | `literature` | 1.5 - 2.5 |
| `C.time_weights.beta_walk_access` | `2.0` | ratio_to_ivt | `literature` | 1.5 - 2.5 |
| `C.time_weights.beta_walk_egress` | `2.0` | ratio_to_ivt | `literature` | 1.5 - 2.5 |
| `C.time_weights.beta_walk_mode` | `1.04` | ratio_to_ivt | `literature` | 1 - 1.3 |
| `C.transfer.beta_transfer_penalty_min` | `8.0` | minutes_equivalent | `assumed` | 3 - 15 |
| `C.transfer.penalty_sweep_grid` | `[3.0, 5.0, 6.5, 8.0, 10.0, 12.0, 15.0]` | minutes_equivalent | `definition` | - |
| `C.vot.by_purpose` | `{"HW": 18.6, "HE": 9.3, "HS": 15.2, "HO": 15.2, "WB": 55.4, "NHB": 15.2}` | AUD_2026_per_hour | `literature` | plus/minus 30% |
| `C.vot.car_unavailable_walk_factor` | `1.15` | ratio | `assumed` | 1 - 1.3 |
| `C.vot.concession_factor` | `0.75` | ratio | `literature` | 0.6 - 0.9 |
| `C.vot.trip_weighted` | `16.96` | AUD_2026_per_hour | `derived` | plus/minus 30% |
| `C.walk.decay_beta_per_m` | `0.0018` | per_metre | `assumed` | 0.001 - 0.003 |
| `C.walk.decay_form` | `negative_exponential` | enum | `assumed` | `negative_exponential`, `cumulative_gaussian` |
| `C.walk.gaussian_mu_m` | `700.0` | metres | `assumed` | 500 - 900 |
| `C.walk.gaussian_sigma_m` | `420.0` | metres | `assumed` | 300 - 550 |
| `C.walk.max_considered_m` | `2500.0` | metres | `assumed` | 1500 - 4000 |

#### `C.asc.bus`

Alternative-specific constant relative to car driver = 0.

***assumed** · status **active** · DECISIONS.md §8.5*

> **Held fixed.** DECISIONS.md 8.5: these are priors for the first calibration pass only and must not be freely calibrated. Either estimate them on the pre-intervention period (era 3, 2018) and hold fixed, or constrain them and report the constraint. Proposal 9 names ASC absorption as the PRIMARY threat to validity: calibrating mode constants to observed patronage fits away the effect under test.
>
> *Departure requires: a departure logged in DECISIONS.md BEFORE results are seen*

#### `C.asc.car_driver`

The reference alternative. Fixed at zero by definition.

***definition** · status **active** · DECISIONS.md §8.5*

#### `C.asc.car_passenger`

Car-passenger constant. The shipped -0.85 is the 8.5 prior; the solved value is written by src/calibrate/solve_asc_ride.py. Status is placeholder because the solve is provisional until the iteration count is settled.

***assumed** · status **placeholder** · DECISIONS.md §8.5, 9.8*

> **Held fixed.** Constrained, not calibrated. DECISIONS.md 9.8 solves this constant so the modelled ride:car leg ratio reproduces the OBSERVED passenger:driver ratio (0.3503, HTS). That is the second branch DECISIONS.md 8.5 permits - constrain and report the constraint - with the constraining quantity measured. It is not ASC absorption: the constrained constant is car passenger, the constraining quantity is how many people fit in a car, and asc_light_rail, asc_bus and asc_rail stay at their 8.5 priors.
>
> *Departure requires: re-solving once the iteration count is settled - the current solve ran at a fixed 250-iteration protocol which DECISIONS.md 9.7 shows is NOT equilibrium, so the value is PROVISIONAL (issue 9)*

#### `C.asc.cycle`

Cycle alternative-specific constant relative to car driver = 0. Status is placeholder because the 8.5 prior is known too weak - AToM's estimated walk-to-bike ASC gap is 3.418 against this model's 1.70 - and the constrained solve has not been built. The point value is deliberately NOT hand-moved: substituting one unjustified number for another is exactly what 8.5 exists to prevent.

***assumed** · status **placeholder** · DECISIONS.md §8.5, 9.28*

> **Held fixed.** Constrained, not calibrated - the second branch DECISIONS.md 8.5 permits. THE DEPARTURE IS LOGGED AT 9.28, before any run on the changed specification. The shipped -1.35 stays as the 8.5 prior; a solve over [-4.0, -1.35] is to be constrained against the OBSERVED walk and bike trip lengths already measured into C.constraint.trip_length_km.*, never against a mode share and never against a patronage level. This is not ASC absorption: the constant opened is CYCLE, asc_light_rail, asc_bus and asc_rail stay at their 8.5 priors, and no hypothesis in proposal 3 turns on it.
>
> *Departure requires: the constrained solve must run AFTER the 9.28 scoring repair, never before - calibrating a constant against a known structural error is the failure proposal 9 names as the primary threat to validity*

#### `C.asc.light_rail`

Alternative-specific constant relative to car driver = 0. This is the constant the effect under test runs through; it is never fitted.

***assumed** · status **active** · DECISIONS.md §8.5*

> **Held fixed.** DECISIONS.md 8.5: these are priors for the first calibration pass only and must not be freely calibrated. Either estimate them on the pre-intervention period (era 3, 2018) and hold fixed, or constrain them and report the constraint. Proposal 9 names ASC absorption as the PRIMARY threat to validity: calibrating mode constants to observed patronage fits away the effect under test.
>
> *Departure requires: a departure logged in DECISIONS.md BEFORE results are seen*

#### `C.asc.rail`

Alternative-specific constant relative to car driver = 0.

***assumed** · status **active** · DECISIONS.md §8.5*

> **Held fixed.** DECISIONS.md 8.5: these are priors for the first calibration pass only and must not be freely calibrated. Either estimate them on the pre-intervention period (era 3, 2018) and hold fixed, or constrain them and report the constraint. Proposal 9 names ASC absorption as the PRIMARY threat to validity: calibrating mode constants to observed patronage fits away the effect under test.
>
> *Departure requires: a departure logged in DECISIONS.md BEFORE results are seen*

#### `C.asc.walk`

Alternative-specific constant relative to car driver = 0.

***assumed** · status **active** · DECISIONS.md §8.5*

> **Held fixed.** DECISIONS.md 8.5: these are priors for the first calibration pass only and must not be freely calibrated. Either estimate them on the pre-intervention period (era 3, 2018) and hold fixed, or constrain them and report the constraint. Proposal 9 names ASC absorption as the PRIMARY threat to validity: calibrating mode constants to observed patronage fits away the effect under test.
>
> *Departure requires: a departure logged in DECISIONS.md BEFORE results are seen*

#### `C.constraint.passenger_per_driver`

Occupancy minus one. The quantity C.asc.car_passenger is solved against.

***derived** · status **active** · DECISIONS.md §9.8*

#### `C.constraint.trip_length_km.bike`

Observed mean trip length for bike (HTS "other"), Newcastle LGA, from the TRIP_AVG_DISTANCE column - published, and used by nothing until 9.13. It answers what mode share cannot: whether a mode is used over the RANGE it is used for in reality. A CONSTRAINT, NOT A VALIDATION TARGET: the 67/143 split is pre-registered and this is not part of it. fit.py reports it beside the fit and never counts it into one, exactly as vehicle occupancy is handled. Compare on Newcastle LGA BOTH SIDES - a five-LGA modelled mean against this published Newcastle mean is a geography error that flatters or damns a mode by accident. Measured by src/calibrate/measure_mode_constraints.py into params/C4_mode_constraints.json, which is what fit.py reads; this declaration is pinned to that artefact by check_package.py so the two cannot drift.

***measured** · status **active** · DECISIONS.md §9.13*

#### `C.constraint.trip_length_km.car`

Observed mean trip length for car (HTS "vehicle driver"), Newcastle LGA, from the TRIP_AVG_DISTANCE column - published, and used by nothing until 9.13. It answers what mode share cannot: whether a mode is used over the RANGE it is used for in reality. A CONSTRAINT, NOT A VALIDATION TARGET: the 67/143 split is pre-registered and this is not part of it. fit.py reports it beside the fit and never counts it into one, exactly as vehicle occupancy is handled. Compare on Newcastle LGA BOTH SIDES - a five-LGA modelled mean against this published Newcastle mean is a geography error that flatters or damns a mode by accident. Measured by src/calibrate/measure_mode_constraints.py into params/C4_mode_constraints.json, which is what fit.py reads; this declaration is pinned to that artefact by check_package.py so the two cannot drift.

***measured** · status **active** · DECISIONS.md §9.13*

#### `C.constraint.trip_length_km.pt`

Observed mean trip length for pt (HTS "public transport"), Newcastle LGA, from the TRIP_AVG_DISTANCE column - published, and used by nothing until 9.13. It answers what mode share cannot: whether a mode is used over the RANGE it is used for in reality. A CONSTRAINT, NOT A VALIDATION TARGET: the 67/143 split is pre-registered and this is not part of it. fit.py reports it beside the fit and never counts it into one, exactly as vehicle occupancy is handled. Compare on Newcastle LGA BOTH SIDES - a five-LGA modelled mean against this published Newcastle mean is a geography error that flatters or damns a mode by accident. Measured by src/calibrate/measure_mode_constraints.py into params/C4_mode_constraints.json, which is what fit.py reads; this declaration is pinned to that artefact by check_package.py so the two cannot drift.

***measured** · status **active** · DECISIONS.md §9.13*

#### `C.constraint.trip_length_km.ride`

Observed mean trip length for ride (HTS "vehicle passenger"), Newcastle LGA, from the TRIP_AVG_DISTANCE column - published, and used by nothing until 9.13. It answers what mode share cannot: whether a mode is used over the RANGE it is used for in reality. A CONSTRAINT, NOT A VALIDATION TARGET: the 67/143 split is pre-registered and this is not part of it. fit.py reports it beside the fit and never counts it into one, exactly as vehicle occupancy is handled. Compare on Newcastle LGA BOTH SIDES - a five-LGA modelled mean against this published Newcastle mean is a geography error that flatters or damns a mode by accident. Measured by src/calibrate/measure_mode_constraints.py into params/C4_mode_constraints.json, which is what fit.py reads; this declaration is pinned to that artefact by check_package.py so the two cannot drift.

***measured** · status **active** · DECISIONS.md §9.13*

#### `C.constraint.trip_length_km.walk`

Observed mean trip length for walk (HTS "walk only"), Newcastle LGA, from the TRIP_AVG_DISTANCE column - published, and used by nothing until 9.13. It answers what mode share cannot: whether a mode is used over the RANGE it is used for in reality. A CONSTRAINT, NOT A VALIDATION TARGET: the 67/143 split is pre-registered and this is not part of it. fit.py reports it beside the fit and never counts it into one, exactly as vehicle occupancy is handled. Compare on Newcastle LGA BOTH SIDES - a five-LGA modelled mean against this published Newcastle mean is a geography error that flatters or damns a mode by accident. Measured by src/calibrate/measure_mode_constraints.py into params/C4_mode_constraints.json, which is what fit.py reads; this declaration is pinned to that artefact by check_package.py so the two cannot drift.

***measured** · status **active** · DECISIONS.md §9.13*

#### `C.constraint.trip_time_min.bike`

Observed mean trip duration for bike (HTS "other"), Newcastle LGA. Paired with trip length it separates a mode used for the wrong DISTANCES from one that is simply too slow. A CONSTRAINT, NOT A VALIDATION TARGET: the 67/143 split is pre-registered and this is not part of it. fit.py reports it beside the fit and never counts it into one, exactly as vehicle occupancy is handled. Compare on Newcastle LGA BOTH SIDES - a five-LGA modelled mean against this published Newcastle mean is a geography error that flatters or damns a mode by accident. Measured by src/calibrate/measure_mode_constraints.py into params/C4_mode_constraints.json, which is what fit.py reads; this declaration is pinned to that artefact by check_package.py so the two cannot drift.

***measured** · status **active** · DECISIONS.md §9.13*

#### `C.constraint.trip_time_min.car`

Observed mean trip duration for car (HTS "vehicle driver"), Newcastle LGA. Paired with trip length it separates a mode used for the wrong DISTANCES from one that is simply too slow. A CONSTRAINT, NOT A VALIDATION TARGET: the 67/143 split is pre-registered and this is not part of it. fit.py reports it beside the fit and never counts it into one, exactly as vehicle occupancy is handled. Compare on Newcastle LGA BOTH SIDES - a five-LGA modelled mean against this published Newcastle mean is a geography error that flatters or damns a mode by accident. Measured by src/calibrate/measure_mode_constraints.py into params/C4_mode_constraints.json, which is what fit.py reads; this declaration is pinned to that artefact by check_package.py so the two cannot drift.

***measured** · status **active** · DECISIONS.md §9.13*

#### `C.constraint.trip_time_min.pt`

Observed mean trip duration for pt (HTS "public transport"), Newcastle LGA. Paired with trip length it separates a mode used for the wrong DISTANCES from one that is simply too slow. A CONSTRAINT, NOT A VALIDATION TARGET: the 67/143 split is pre-registered and this is not part of it. fit.py reports it beside the fit and never counts it into one, exactly as vehicle occupancy is handled. Compare on Newcastle LGA BOTH SIDES - a five-LGA modelled mean against this published Newcastle mean is a geography error that flatters or damns a mode by accident. Measured by src/calibrate/measure_mode_constraints.py into params/C4_mode_constraints.json, which is what fit.py reads; this declaration is pinned to that artefact by check_package.py so the two cannot drift.

***measured** · status **active** · DECISIONS.md §9.13*

#### `C.constraint.trip_time_min.ride`

Observed mean trip duration for ride (HTS "vehicle passenger"), Newcastle LGA. Paired with trip length it separates a mode used for the wrong DISTANCES from one that is simply too slow. A CONSTRAINT, NOT A VALIDATION TARGET: the 67/143 split is pre-registered and this is not part of it. fit.py reports it beside the fit and never counts it into one, exactly as vehicle occupancy is handled. Compare on Newcastle LGA BOTH SIDES - a five-LGA modelled mean against this published Newcastle mean is a geography error that flatters or damns a mode by accident. Measured by src/calibrate/measure_mode_constraints.py into params/C4_mode_constraints.json, which is what fit.py reads; this declaration is pinned to that artefact by check_package.py so the two cannot drift.

***measured** · status **active** · DECISIONS.md §9.13*

#### `C.constraint.trip_time_min.walk`

Observed mean trip duration for walk (HTS "walk only"), Newcastle LGA. Paired with trip length it separates a mode used for the wrong DISTANCES from one that is simply too slow. A CONSTRAINT, NOT A VALIDATION TARGET: the 67/143 split is pre-registered and this is not part of it. fit.py reports it beside the fit and never counts it into one, exactly as vehicle occupancy is handled. Compare on Newcastle LGA BOTH SIDES - a five-LGA modelled mean against this published Newcastle mean is a geography error that flatters or damns a mode by accident. Measured by src/calibrate/measure_mode_constraints.py into params/C4_mode_constraints.json, which is what fit.py reads; this declaration is pinned to that artefact by check_package.py so the two cannot drift.

***measured** · status **active** · DECISIONS.md §9.13*

#### `C.constraint.vehicle_occupancy`

Newcastle LGA vehicle occupancy, HTS 2024/25 driver and passenger trip counts. Both quantities are ratios of two published counts; neither is a modelling choice. The unconstrained model produced 5.52 people per vehicle.

***measured** · status **active** · DECISIONS.md §9.8*

> **Sweep basis.** the observed spread across all 7 survey years in the file, not a chosen interval

#### `C.crowding.seated_multiplier`

Crowding multiplier, seated. NOT carried into MATSim scoring (DECISIONS.md 9.3).

***literature** · status **active** · DECISIONS.md §8.4, 9.3*

#### `C.crowding.standing_multiplier`

Crowding multiplier, standing. NOT carried into MATSim scoring (DECISIONS.md 9.3), and the transit fleet carries standingRoomInPersons=0, so standing does not occur in the current fleet at all.

***literature** · status **active** · DECISIONS.md §8.4, 9.3*

#### `C.gradient.downhill_penalty_per_pct`

Asymmetric gradient cost, downhill.

***assumed** · status **active** · DECISIONS.md §8.4*

#### `C.gradient.uphill_penalty_per_pct`

Asymmetric gradient cost on active-mode edges. Proposal 6.3 requires uphill and downhill to be different costs; material in Newcastle East and The Hill.

***assumed** · status **active** · DECISIONS.md §8.4 · proposal §6.3*

#### `C.nesting.active_coefficient`

Nested-logit nest coefficient. SPECIFIED IN C1 BUT NOT PRESENT IN MATSim SCORING - MATSim scores plans, it does not evaluate a nested logit. DECISIONS.md 9.3 records this as lost in translation. Status is placeholder: the value is declared but nothing consumes it, and it must not be reported as if the model used it.

***assumed** · status **placeholder** · DECISIONS.md §8.6, 9.3*

#### `C.nesting.private_coefficient`

Nested-logit nest coefficient. SPECIFIED IN C1 BUT NOT PRESENT IN MATSim SCORING - MATSim scores plans, it does not evaluate a nested logit. DECISIONS.md 9.3 records this as lost in translation. Status is placeholder: the value is declared but nothing consumes it, and it must not be reported as if the model used it.

***assumed** · status **placeholder** · DECISIONS.md §8.6, 9.3*

#### `C.nesting.pt_coefficient`

Nested-logit nest coefficient. SPECIFIED IN C1 BUT NOT PRESENT IN MATSim SCORING - MATSim scores plans, it does not evaluate a nested logit. DECISIONS.md 9.3 records this as lost in translation. Status is placeholder: the value is declared but nothing consumes it, and it must not be reported as if the model used it.

***assumed** · status **placeholder** · DECISIONS.md §8.6, 9.3*

#### `C.scoring.activity_minimal_applied_s`

The minimal duration actually written per activity type. Computed rather than declared because it is not free: it is a floor taken against each activity's own typical duration, and a floor above the typical duration would hold a vehicle at a drop-off.

***derived** · status **computed** · DECISIONS.md §9.15 · MATSim `scoring.activityParams[*].minimalDuration`*

> **Derived from** `C.scoring.activity_minimal_duration_s`, `C.scoring.activity_typical_duration_s`: minimalDuration[a] = min(C.scoring.activity_minimal_duration_s, C.scoring.activity_typical_duration_s[a]), per activity type a

#### `C.scoring.activity_minimal_duration_s`

MATSim minimalDuration for a scored activity. Applied as min(this, typical duration) so it can never exceed the typical duration of a short activity: an escort drop-off has a typical duration of 5 minutes and a 15-minute floor over it would be self-contradictory. The APPLIED per-activity result is C.scoring.activity_minimal_applied_s; this is the ceiling it is taken against.

***assumed** · status **active** · DECISIONS.md §9.15*

#### `C.scoring.activity_typical_duration_s`

MATSim typical activity duration per activity type. THIS DICTIONARY IS THE ACTIVITY VOCABULARY: the config carries one activityParams block per key here, so an activity type absent from it is unscored and an agent performing it earns nothing. MATSim reads the duration as a clock string, which is why this field declares its format - the value is seconds, because seconds is what it is. A property of the scoring formulation rather than an observable quantity of Newcastle (DECISIONS.md 9.3), so it is assumed and swept. The escort activity is the drop-off that comes with the serve-passenger tour purpose: the driver stops and leaves, so its typical duration is minutes rather than hours, and a longer one would hold the vehicle at the destination and displace the return trip out of the peak.

***assumed** · status **active** · DECISIONS.md §9.3, 9.15 · MATSim `scoring.activityParams[*].typicalDuration`*

#### `C.scoring.marginal_utility_of_money`

Sets the utility numeraire to AUD. Definitional, not empirical.

***definition** · status **active** · DECISIONS.md §9.3 · MATSim `scoring.marginalUtilityOfMoney`*

#### `C.scoring.marginal_utility_of_traveling`

The MATSim per-mode marginal utility of travel time. COMPUTED, NOT DECLARED: the beta_* fields are RATIOS to in-vehicle time and this parameter is a UTILITY RATE PER HOUR. beta_walk_mode and beta_bike_mode were bound straight to this parameter until the config emitter was built, which would have written the ratio 1.04 into a util/hour rate - the same class of error as an exponent bound to a factor, and invisible while the config was a hand-written template.

***derived** · status **computed** · DECISIONS.md §9.28 · MATSim `scoring.modeParams[*].marginalUtilityOfTraveling_util_hr`*

> **Derived from** `C.scoring.performing_utils_per_h`, `C.vot.trip_weighted`, `C.scoring.marginal_utility_of_money`, `C.time_weights.beta_ivt`, `C.time_weights.beta_walk_mode`, `C.time_weights.beta_bike_mode`: marginalUtilityOfTraveling[m] = performing - trip_weighted_VOT * beta[m] * marginalUtilityOfMoney, the conventional MATSim identity. beta is 1.0 for car and ride, beta_ivt for pt, beta_walk_mode for walk and beta_bike_mode for bike

#### `C.scoring.mode_constant`

The MATSim alternative-specific constant per scored mode. Computed, because C1 is a nested-logit specification over named alternatives and MATSim scores over its own mode vocabulary - the mapping between them is the translation, and it is stated here rather than left implicit in a builder. The C.asc.* fields remain the declared quantities and are what a calibration moves; DECISIONS.md 8.5 holds them fixed.

***derived** · status **computed** · DECISIONS.md §8.5, 9.8 · MATSim `scoring.modeParams[*].constant`*

> **Derived from** `C.asc.car_driver`, `C.asc.car_passenger`, `C.asc.bus`, `C.asc.walk`, `C.asc.cycle`: constant[m] = the C1 alternative-specific constant for the mode m maps to, translated in src/build/build_matsim_run_inputs.py: car<-asc_car_driver, ride<-asc_car_passenger, pt<-asc_bus, walk<-asc_walk, bike<-asc_cycle

#### `C.scoring.monetary_distance_rate`

Vehicle operating cost per metre AS PERCEIVED BY THE TRAVELLER MAKING THE CHOICE. RIDE CARRIES THE CAR RATE (DECISIONS.md 9.17, the 8.5 departure for issue 16). It was zero, derived from an aggregate-cost identity that governs system accounting rather than individual choice; the 9.13 trip-length constraint then measured modelled ride:car trip length at 1.372 against an observed 0.961, which is what a mode with no marginal distance cost produces. This is NOT a move of asc_car_passenger, which stays constrained to observed occupancy at -0.85 and is held fixed under 8.5: proposal 9 names ASC absorption as the primary threat to validity, and correcting a mis-specified distance rate is the opposite of absorbing that error into a constant.

***derived** · status **active** · DECISIONS.md §9.8, 9.13, 9.17 · MATSim `scoring.modeParams[*].monetaryDistanceRate`*

> **Sweep basis.** applies to the car entry only; ride follows it by the identity above, and pt, walk and bike remain zero because no vehicle operating cost is borne by their traveller. Truck is zero because a freight agent's mode is LOCKED (9.49): scoring never compares a truck alternative against anything, so a cost model here would be decoration pretending to be behaviour

> **Derived from** `C.scoring.monetary_distance_rate`: a kilometre in a car costs the same kilometre whether you are in the driver seat or beside it, so ride carries the car rate. This SUPERSEDES the 9.8 identity that set ride to zero: that identity - a vehicle operating cost is paid once, so charging both occupants makes AGGREGATE cost 1.35x the real one - is a statement about system cost accounting, and monetaryDistanceRate is the cost PERCEIVED BY ONE PERSON weighing one alternative. The 9.13 trip length constraint falsified the old treatment: modelled ride to car trip length was 1.372 against an observed 0.961, widening with sample fraction - the signature a zero marginal distance cost produces. See DECISIONS.md 9.17

#### `C.scoring.performing_utils_per_h`

Marginal utility of performing an activity. A property of the MATSim scoring formulation, not an observable quantity of Newcastle. The effective cost of travel time is performing plus the absolute marginalUtilityOfTraveling, which is how the 16.96 AUD/h VOT is reproduced: 6.0 + 10.9608.

***literature** · status **active** · DECISIONS.md §9.3 · MATSim `scoring.performing`*

#### `C.scoring.utility_of_line_switch`

The scoring penalty for changing transit line, ON TOP of the walk and wait MATSim already simulates. Computed from the declared transfer penalty, which is SWEPT 3-15 min because the estimate proposal 7.2 asks for is not possible from this package (deliverable 8, DECISIONS.md 9.32). Every headline that touches interchange is bound to a curve across that sweep, and this is the parameter the sweep moves.

***derived** · status **computed** · DECISIONS.md §9.32 · MATSim `scoring.utilityOfLineSwitch`*

> **Derived from** `C.transfer.penalty_min`, `C.vot.trip_weighted`, `C.scoring.marginal_utility_of_money`: utilityOfLineSwitch = -(C.transfer.penalty_min / 60) * trip_weighted_VOT * marginalUtilityOfMoney

#### `C.scoring.waiting_pt`

Disutility of waiting for public transport, per hour. Distinct from RUN.scoring.waiting, which is general waiting and is a declared value: this one is derived from the C1 wait weight. Confusing the two is the DECISIONS.md 9.28 defect class.

***derived** · status **computed** · DECISIONS.md §9.28 · MATSim `scoring.waitingPt`*

> **Derived from** `C.scoring.performing_utils_per_h`, `C.vot.trip_weighted`, `C.scoring.marginal_utility_of_money`, `C.time_weights.beta_wait`: waitingPt = performing - trip_weighted_VOT * beta_wait * marginalUtilityOfMoney, the same identity as the per-mode travel rate applied to the waiting weight

#### `C.time_weights.beta_bike_mode`

Weight on BIKE travel time relative to in-vehicle time. Value from Melbourne AToM, estimated on VISTA n=14,959. MUST BE >= C.time_weights.beta_walk_mode: cycling time being dearer per hour than walking time is the finding of 9.28, not an incidental ordering - the model had it inverted (walk 2.0, bike 1.3) and that inversion conceded every short trip to bike. Replaces a bare literal 1.3 typed into src/build/build_matsim_run_inputs.py that carried no registry field, no source, no sweep and no consumer while governing bike's mode share.

***literature** · status **active** · DECISIONS.md §8.4, 9.28*

> **Sweep basis.** same bracket as beta_walk_mode. AToM estimates 1.21 for cycling; Kelheim uses 1.50 and Leipzig 1.92, so 1.0-1.3 is the conservative end of published practice.

#### `C.time_weights.beta_headway`

Weight on service headway.

***literature** · status **active** · DECISIONS.md §8.4*

#### `C.time_weights.beta_ivt`

In-vehicle time is the numeraire the other weights are expressed against.

***definition** · status **active** · DECISIONS.md §8.4*

#### `C.time_weights.beta_reliability`

Weight on travel time variability.

***literature** · status **active** · DECISIONS.md §8.4*

#### `C.time_weights.beta_wait`

Weight on wait time relative to in-vehicle time.

***literature** · status **active** · DECISIONS.md §8.4*

#### `C.time_weights.beta_walk_access`

Weight on walk access time relative to in-vehicle time.

***literature** · status **active** · DECISIONS.md §8.4*

#### `C.time_weights.beta_walk_egress`

Weight on walk egress time relative to in-vehicle time.

***literature** · status **active** · DECISIONS.md §8.4*

#### `C.time_weights.beta_walk_mode`

Weight on WALK-AS-A-MODE travel time relative to in-vehicle time. DISTINCT FROM beta_walk_access, which is the appraisal weight on walking to a PT stop INSIDE a PT journey and must never be used here: doing so priced a whole walking trip at 2x car time, put the walk-bike indifference distance at 174 m against an observed mean walk trip of 700 m, and produced a 0.13% walk share against 13.4% (9.28). Value from Melbourne AToM, estimated on VISTA n=14,959, the only calibrated Australian agent-based model.

***literature** · status **active** · DECISIONS.md §8.4, 9.28*

> **Sweep basis.** bracketed by the two conventions actually in use: Open Berlin, Kelheim and Hamburg price walk time equal to car (1.00) and Duesseldorf at 1.15, while Melbourne AToM estimates 1.04 on Australian revealed preference. No published calibrated MATSim scenario exceeds 1.15.

#### `C.transfer.beta_transfer_penalty_min`

Behavioural penalty for an interchange, ON TOP of the measured Newcastle Interchange walk time (mean 112 s, max 284 s over 51 stop pairs). The whole policy question is whether forcing a transfer at Wickham is worth the CBD distribution it buys: 5 min gives a broadly favourable result, 12 min a net disbenefit for external origins. NO HEADLINE MAY BE REPORTED AT A SINGLE VALUE. It is assumed rather than estimated only because journey-linked Opal is unobtained.

***assumed** · status **active** · DECISIONS.md §8.1 · proposal §6.2, 3.4 S-d*

> **Sweep basis.** proposal 6.2 forbids a literature default and requires every finding to be reported as a curve across this range; the grid crosses 3, 5, 6.5, 8, 10, 12, 15

#### `C.transfer.penalty_sweep_grid`

The points at which C.transfer.beta_transfer_penalty_min is sampled for the mandatory sensitivity grid. A sampling design, not an empirical quantity - which is why it is a definition rather than a swept value. Denser near the base than at the ends because the policy answer turns over in the middle of the range. check_package.py asserts the endpoints match the declared sweep and that the base is a member, so the grid cannot drift away from the range it is supposed to cover.

***definition** · status **active** · DECISIONS.md §9.32 · proposal §3.4 S-d*

#### `C.vot.by_purpose`

Value of travel time by trip purpose, ATAP PV2 / TfNSW Economic Parameter Values conventions. NOT a Newcastle measurement. MATSim scoring cannot carry per-purpose VOT, so the run inputs collapse this to a trip-weighted 16.96 AUD/h - see C.vot.trip_weighted and DECISIONS.md 9.3.

***literature** · status **active** · DECISIONS.md §8.3 · proposal §A/C1, 6.2*

#### `C.vot.car_unavailable_walk_factor`

Multiplier on the walk and wait time weights for the car-unavailable segment, who face them without an alternative. Applied to every weight whose name carries `walk`.

***assumed** · status **active** · DECISIONS.md §8.3, 9.32*

> **Sweep basis.** chosen. 1.0 is the arm in which car availability does not change how walking is valued.

#### `C.vot.concession_factor`

Multiplier on VOT for concession, student and car-unavailable segments.

***literature** · status **active** · DECISIONS.md §8.3*

#### `C.vot.trip_weighted`

The single VOT MATSim actually scores with, trip-weighted across purposes. This is what C1 per-purpose structure degrades to in translation, and is one of the three things DECISIONS.md 9.3 records as lost.

***derived** · status **computed** · DECISIONS.md §9.3*

#### `C.walk.decay_beta_per_m`

Negative-exponential distance decay on walk access. Weight 0.49 at 400 m, 0.24 at 800 m, 0.12 at 1200 m, considered to 2500 m. NO 400 m THRESHOLD IS USED ANYWHERE: proposal 6.3 is explicit that a cut-off treats a person at 401 m as identical to one at 2 km and systematically flatters fixed-route modes.

***assumed** · status **active** · DECISIONS.md §8.2 · proposal §6.3*

#### `C.walk.decay_form`

Functional form of the walk access decay.

***assumed** · status **active** · DECISIONS.md §8.2*

#### `C.walk.gaussian_mu_m`

Alternative-form parameter, used only when decay_form is cumulative_gaussian.

***assumed** · status **active** · DECISIONS.md §8.2*

#### `C.walk.gaussian_sigma_m`

Alternative-form parameter, used only when decay_form is cumulative_gaussian.

***assumed** · status **active** · DECISIONS.md §8.2*

#### `C.walk.max_considered_m`

Outer distance over which the walk-access decay curve is evaluated. NOT a catchment threshold: proposal 6.3 forbids one, because a 400 m cut-off treats a person at 401 m as identical to one at 2 km and flatters fixed-route modes.

***assumed** · status **active** · DECISIONS.md §8.4, 9.32 · proposal §6.3*

> **Sweep basis.** chosen. Proposal 6.3 forbids a THRESHOLD on the decay curve; this is the outer distance at which the curve is still evaluated, not a cut-off applied to behaviour.

## Land use (D1)

*`cities/newcastle/registry/D_landuse.json` - 5 fields*

Frontage geometry, attraction weights and the unobtained retail vacancy. Land use is HELD FIXED BY DESIGN across all scenarios (proposal 4.2): endogenous land-use feedback would reintroduce the confounding the identification strategy exists to remove.

| Field | Value | Units | Provenance | Sweep |
|---|---|---|---|---|
| `D.attraction.job_weight_by_category` | `{"office": 12.0, "retail": 4.0, "food": 6.0, "civic": 15.0, "health": 8.0, "leisure": 2.0, "tourism": 3.0, ...` | jobs_per_poi_weight | `assumed` | plus/minus 40% |
| `D.attraction.purpose_weight` | `{"HW": {"office": 12.0, "retail": 4.0, "food": 6.0, "civic": 15.0, "health": 8.0, "leisure": 2.0, "tourism"...` | attraction_weight | `assumed` | plus/minus 40% |
| `D.frontage.buffer_m` | `30.0` | metres | `assumed` | 15 - 50 |
| `D.frontage.segment_length_m` | `50.0` | metres | `definition` | - |
| `D.retail.vacancy_rate` | *(null - unobtained)* | share_of_frontage | `assumed` | 0 - 0.25 |

#### `D.attraction.job_weight_by_category`

Relative employment weight by POI category, used to distribute SA2 job counts to zones. Retail floorspace and vacancy were not obtained, so this stands in for them (DECISIONS.md 13 priority 7).

***assumed** · status **active** · DECISIONS.md §7*

#### `D.attraction.purpose_weight`

Destination attraction weight by trip purpose and POI category.

***assumed** · status **active** · DECISIONS.md §7*

#### `D.frontage.buffer_m`

Distance from a frontage segment within which a building is attributed to it.

***assumed** · status **active** · DECISIONS.md §7*

#### `D.frontage.segment_length_m`

Length of a Hunter St frontage segment. Hypothesis B1 is defined per 50 m segment, so this is fixed by the pre-registered metric, not tunable.

***definition** · status **active** · DECISIONS.md §7 · proposal §3.3 B1*

#### `D.retail.vacancy_rate`

Frontage-level retail vacancy. NOT OBTAINED and not currently consumed by any metric. Registered so that hypothesis B2, which weights catchment by floorspace, cannot quietly acquire a vacancy assumption later without one appearing here.

***assumed** · status **unobtained** · DECISIONS.md §7, 13 · proposal §6.1*

## Scenario configuration (E1)

*`cities/newcastle/registry/E_scenario.json` - 27 fields*

The scenario matrix and the coupling controls. Per-scenario variant references stay in scenarios/S*.json, which bind a scenario to its network, schedule, land use, parking, signals, demand and parameter sets; this layer holds the values those configs share.

| Field | Value | Units | Provenance | Sweep |
|---|---|---|---|---|
| `E.bus.signal_delay_share` | `0.5` | share | `assumed` | 0.3 - 1 |
| `E.coupling.outer_loop_tolerance_s` | `5.0` | seconds | `assumed` | **held fixed** |
| `E.lightrail.extension_detour_factor` | `1.15` | factor | `assumed` | 1 - 1.4 |
| `E.matrix.day_types` | `["WEEKDAY", "SAT", "SUN"]` | enum | `definition` | - |
| `E.matrix.reference_scenario` | `S2` | enum | `definition` | - |
| `E.matrix.scenario_ids` | `["S0", "S1", "S2", "S2a", "S2b", "S2c", "S3", "S4", "S5", "S6"]` | enum | `definition` | - |
| `E.replication.n_replications` | `30` | count | `definition` | 5 - 30 |
| `E.s0.heavy_rail_detour_factor` | `1.1` | factor | `assumed` | 1 - 1.3 |
| `E.s0.station_dwell_s` | `30.0` | seconds | `assumed` | 20 - 60 |
| `E.s1.first_hour` | `5` | hour_of_day | `assumed` | 4 - 7 |
| `E.s1.headway_s` | `600` | seconds | `definition` | - |
| `E.s1.last_hour` | `24` | hour_of_day | `assumed` | 22 - 27 |
| `E.s1.shuttle_dwell_s` | `18.0` | seconds | `assumed` | 10 - 30 |
| `E.s1.shuttle_speed_kmh` | `26.0` | km_per_hour | `assumed` | 18 - 40 |
| `E.s2b.lr_segment_count` | `5.0` | segments | `assumed` | 4 - 8 |
| `E.s2b.signal_delay_removed_share` | `0.75` | share | `assumed` | 0.5 - 1 |
| `E.s2c.signal_delay_removed_share` | `0.6` | share | `assumed` | 0.4 - 0.9 |
| `E.s3.brt_dwell_s` | `12.0` | seconds | `assumed` | 8 - 25 |
| `E.s3.brt_speed_kmh` | `40.0` | km_per_hour | `assumed` | 25 - 55 |
| `E.s3.headway_s` | `450` | seconds | `assumed` | 300 - 900 |
| `E.schedule.bus_route_type` | `3` | gtfs_route_type | `definition` | - |
| `E.schedule.min_segment_s` | `30.0` | seconds | `definition` | - |
| `E.schedule.weekend_headway_factor` | `1.5` | factor | `assumed` | 1 - 3 |
| `E.vehicle.emu_accel_ms2` | `0.7` | metres_per_second_squared | `literature` | 0.5 - 1 |
| `E.vehicle.emu_decel_ms2` | `0.8` | metres_per_second_squared | `literature` | 0.6 - 1.1 |
| `E.vehicle.tram_accel_ms2` | `1.2` | metres_per_second_squared | `literature` | 0.8 - 1.5 |
| `E.vehicle.tram_decel_ms2` | `1.3` | metres_per_second_squared | `literature` | 0.9 - 1.6 |

#### `E.bus.signal_delay_share`

Share of A.signals.delay_per_intersection_s borne by an S1 or S3 bus at each corridor intersection. IT SETS HOW MUCH FASTER THE BUS COUNTERFACTUALS ARE than the tram they are compared with, and it was a bare 0.5 in an expression.

***assumed** · status **active** · DECISIONS.md §4.3, 9.34, 15*

> **Sweep basis.** what share of the per-intersection signal delay a bus suffers relative to the value measured for the tram. A bus stops in the traffic lane and rejoins, so it is not obviously less delayed than a tram; 0.5 is a judgement and the upper bound treats it as equal.

#### `E.coupling.outer_loop_tolerance_s`

Corridor run-time stability tolerance for the MATSim-SUMO outer loop. Proposal 5.2 defers this explicitly - run the loop "until the corridor run time is stable within a tolerance to be defined at calibration". P4 deliverable 7 defines it: the loop is converged when end-to-end corridor run time changes by less than this between successive outer iterations. Derived from the resolution of the target and the size of the declared sensitivities rather than chosen - see the held_fixed rule. The SUMO run harness and the loop itself are P5; this is the number they must honour.

***assumed** · status **active** · DECISIONS.md §15 · proposal §5.2*

> **Held fixed.** A convergence tolerance is a numerical control, not a quantity of Newcastle: it decides how many outer-loop iterations are paid for, not what the answer is, PROVIDED it stays well below the smallest difference the study reports. So it is held fixed rather than swept, and it is bounded from above by three measured quantities. (1) The corridor run time is validated against V208/V209, which are SCHEDULED times: every segment in A4_segment_runtime_decomposition.csv is a whole multiple of 60 s and direction 0 sums to exactly the 720 s target, so the target itself is known only to plus or minus 30 s. (2) The charging dwell assumption is worth 11% of end-to-end run time, about 79 s - the smallest declared corridor sensitivity in the project. (3) The signal priority sweep (S2 against S2b) moves run time 38%, about 274 s. At 5 s - 0.69% of the 720 s run time - the loop is an order of magnitude inside the smallest of those and well inside the resolution of the target it is judged against, so a converged loop cannot contribute materially to any reported difference.
>
> *Departure requires: A SELF-POLICING BOUND, not a preference: if any reported scenario comparison ever turns on a corridor run-time difference smaller than TWICE this tolerance, the difference is not resolvable by the loop that produced it. The tolerance must then be tightened and both scenarios re-run before the comparison is reported.*

#### `E.lightrail.extension_detour_factor`

Path-length multiplier on the beeline between stops of a light rail EXTENSION (S4 Broadmeadow, S5 John Hunter Hospital). A bare 1.15 inside the leg-length expression until this change.

***assumed** · status **active** · DECISIONS.md §4.3, 9.34, 15*

> **Sweep basis.** how much longer a street-running extension is than the straight line between its stops. Higher than the reserved-alignment factor because a tram on a street follows the street. Nothing measures it for an extension that does not exist.

#### `E.matrix.day_types`

Full weekend day types are built, not a weekday-only model with a note. Beach and event demand is arguably this system strongest use case and excluding it would bias against the light rail (DECISIONS.md 1 item 5).

***definition** · status **active** · DECISIONS.md §1*

#### `E.matrix.reference_scenario`

The scenario every comparison is made against - light rail as built. Declared here because the sweep grid's baseline row needs to know which scenario overlay carries the baseline point for an unobtained input, and reading a scenario id out of a script is the same defect as reading a value out of one.

***definition** · status **active** · DECISIONS.md §9.32*

#### `E.matrix.scenario_ids`

The scenario matrix, fixed at P0. S2 vs S0 is the headline test, S2 vs S3 the value-for-money test, S2 vs S4/S5 the trunk-length test.

***definition** · status **active** · DECISIONS.md §1 · proposal §4.3*

#### `E.replication.n_replications`

Seeded replications per scenario. One of the three things that can be cut to close the run-budget gap - the others being sweep breadth and day types. Sample fraction is the WEAKEST lever because cost is sublinear in it.

***definition** · status **active** · DECISIONS.md §1*

> **Sweep basis.** proposal 5.2 specifies at least 30 SUMO replications; the sweep records that cutting replications is one of the three levers on the run budget

#### `E.s0.heavy_rail_detour_factor`

Path-length multiplier applied to the beeline between S0 station sites when computing run time. A bare 1.10 in an expression until this change, which is the form of literal no module-level constant scan can reach.

***assumed** · status **active** · DECISIONS.md §4.3, 9.34, 15*

> **Sweep basis.** how much longer the running alignment is than the straight line between two station sites. Rail on reserved alignment is close to straight, so the range is tight; the road detour factor B.activity.detour_factor is 1.3376 and does NOT apply here.

#### `E.s0.station_dwell_s`

Dwell at each restored S0 station. A bare 30.0 added inside the leg-time expression until this change.

***assumed** · status **active** · DECISIONS.md §4.3, 9.34, 15*

> **Sweep basis.** heavy rail station dwell on a suburban service. Bracketed by observed practice rather than measured on this line.

#### `E.s1.first_hour`

First hour of the S1 shuttle service day.

***assumed** · status **active** · DECISIONS.md §4.3, 9.34, 15*

> **Sweep basis.** service span start. Newcastle bus services begin between about 04:30 and 06:00 depending on the route.

#### `E.s1.headway_s`

S1 shuttle headway. TEN MINUTES IS THE ANNOUNCED POLICY, not an assumption: the December 2012 announcement specified a ten-minute shuttle, and E1_scenarios.csv already describes S1 as "10 minute headway, 8 stops, mixed traffic". Held as a definition of the scenario - changing it would be modelling a different policy, not testing a range.

***definition** · status **active** · DECISIONS.md §4.3, 9.34, 15 · proposal §3.4*

#### `E.s1.last_hour`

Last hour in which an S1 shuttle departs.

***assumed** · status **active** · DECISIONS.md §4.3, 9.34, 15*

> **Sweep basis.** service span end, expressed on the same 30 h clock as the qsim window so a late trip can still arrive.

#### `E.s1.shuttle_dwell_s`

Dwell at each S1 shuttle stop. Like the speed, this had a live call-site value of 18.0 and a dead signature default of 15.0.

***assumed** · status **active** · DECISIONS.md §4.3, 9.34, 15 · proposal §3.4*

> **Sweep basis.** boarding dwell for a high-floor bus with mixed fare payment. Bracketed by observed urban bus practice rather than measured here.

#### `E.s1.shuttle_speed_kmh`

Average running speed of the S1 Wickham bus shuttle between stops, excluding dwell. TWO VALUES EXISTED: the call site passed 26.0 while the function signature defaulted to 28.0, so the default was dead code that looked like the specification. The operative 26.0 is declared here and the signature no longer carries a default at all.

***assumed** · status **active** · DECISIONS.md §4.3, 9.34, 15 · proposal §3.4*

> **Sweep basis.** a bus in mixed traffic on an urban main street. The lower bound is congested Hunter Street, the upper is free-flowing. No timetable exists for a service that never ran, so nothing measures it - and S1 is a counterfactual the study reports against S2, so its run time is part of the comparison.

#### `E.s2b.lr_segment_count`

Segments over which the S2b signal-priority saving is divided to give a per-segment delta. A bare divisor 5.0 in the S2b expression until this change. DERIVING IT FROM THE FEED IS OUTSTANDING WORK: if the segment count and this value disagree, S2b removes the wrong total amount of delay.

***assumed** · status **active** · DECISIONS.md §5, 15*

> **Sweep basis.** the number of stop-to-stop segments the corridor signal delay is spread across. It SHOULD be derived from the mapped light rail feed rather than declared - the feed knows how many segments it has - and it is recorded as assumed because it is not yet.

#### `E.s2b.signal_delay_removed_share`

Share of corridor signal delay removed by full transit signal priority. THIS IS THE S2b INTERVENTION: the 38% swing S2b exists to measure is produced by this number, and it was the literal 0.75 inside an arithmetic expression - the form the previous audit was structurally blind to. A.lightrail.tsp_enabled says WHETHER priority applies; this says how much it is worth.

***assumed** · status **active** · DECISIONS.md §5, 9.21, 15 · proposal §3.4 S-b*

> **Sweep basis.** what "full transit signal priority" removes of the delay a tram suffers at signalised intersections. Total removal (1.0) is the theoretical ceiling and is not achievable where the tram crosses a coordinated arterial; 0.5 is partial priority. NOTHING MEASURES IT - SCATS phasing is refused by policy (DECISIONS.md 9.21), which is exactly why this must be swept and not pinned.

#### `E.s2c.signal_delay_removed_share`

Share of corridor signal delay avoided by the S2c reserved alignment. A bare 0.6 in an expression until this change.

***assumed** · status **active** · DECISIONS.md §5, 15 · proposal §3.4*

> **Sweep basis.** the reserved former-railway alignment of Option A has fewer conflicting movements than the street alignment, but it still crosses roads. Lower than full priority because it is a geometric effect rather than a signal-control one.

#### `E.s3.brt_dwell_s`

Dwell at each S3 BRT stop.

***assumed** · status **active** · DECISIONS.md §4.3, 9.34, 15 · proposal §3.4*

> **Sweep basis.** shorter than the S1 shuttle because rapid transit assumes level boarding and off-vehicle fare payment. Assumed, like the speed.

#### `E.s3.brt_speed_kmh`

Average running speed of the S3 bus rapid transit alternative. S3 exists to test whether the corridor benefit needed rail at all, so THIS NUMBER LARGELY DECIDES THE ANSWER - and it was a call-site literal, make_bus_shuttle(..., speed_kmh=40.0).

***assumed** · status **active** · DECISIONS.md §4.3, 9.34, 15 · proposal §3.4*

> **Sweep basis.** bus rapid transit with priority and wider stop spacing than S1. The lower bound is little better than the S1 shuttle, the upper is close to free-flow on the corridor. Nothing measures it: S3 is a service that has never run.

#### `E.s3.headway_s`

S3 BRT headway. Unlike the S1 headway this is NOT an announced policy - S3 is the study’s own alternative - so it is assumed and swept.

***assumed** · status **active** · DECISIONS.md §4.3, 9.34, 15 · proposal §3.4*

> **Sweep basis.** 7.5 minutes was chosen to be more frequent than the S1 shuttle and comparable to the light rail. No document specifies it.

#### `E.schedule.bus_route_type`

The GTFS route_type written for the invented bus services. 3 is Bus in the GTFS specification - a vocabulary the feed is defined over, not a value to tune.

***definition** · status **active** · DECISIONS.md §4.3, 9.34, 15*

#### `E.schedule.min_segment_s`

Floor on a rebuilt stop-to-stop segment time. A GUARD, not a modelling value: a scenario that shortened a segment below this would produce a timetable with two stops at the same second, which GTFS readers and pt2matsim both mishandle. Declared so the guard is visible rather than typed into the arithmetic it guards.

***definition** · status **active** · DECISIONS.md §4.3, 9.34, 15*

#### `E.schedule.weekend_headway_factor`

Headway multiplier applied to the invented S1 and S3 services on Saturday and Sunday. A bare 1.5 in an expression until this change.

***assumed** · status **active** · DECISIONS.md §4.3, 9.34, 15*

> **Sweep basis.** how much less frequent a weekend service is than a weekday one. The real feeds carry their own weekend timetables and this factor applies ONLY to the invented S1 and S3 services, for which no weekend timetable exists to read.

#### `E.vehicle.emu_accel_ms2`

Heavy rail EMU service acceleration, used by the era 1 reconstruction and by S0. Also a tuple unpack until this change.

***literature** · status **active** · DECISIONS.md §4.3, 9.34, 15*

> **Sweep basis.** heavy rail electric multiple unit, gentler than a tram. Bracketed by published figures for the class of unit the Hunter Line ran.

#### `E.vehicle.emu_decel_ms2`

Heavy rail EMU service deceleration.

***literature** · status **active** · DECISIONS.md §4.3, 9.34, 15*

> **Sweep basis.** service braking rate for the same unit.

#### `E.vehicle.tram_accel_ms2`

Tram service acceleration, used to compute run time between stops. IT WAS PART OF A TUPLE UNPACK - ACCEL, DECEL = 1.2, 1.3 - which a single-target constant scan cannot see, so two vehicle parameters sat outside the audit entirely.

***literature** · status **active** · DECISIONS.md §4.3, 9.34, 15*

> **Sweep basis.** service acceleration of a modern low-floor tram, bracketed by published rolling-stock figures. Not measured on this vehicle.

#### `E.vehicle.tram_decel_ms2`

Tram service deceleration.

***literature** · status **active** · DECISIONS.md §4.3, 9.34, 15*

> **Sweep basis.** service braking rate, bracketed with the acceleration. Emergency braking is higher and is not what a timetable is built on.

## Execution control

*`cities/newcastle/registry/RUN_execution.json` - 62 fields*

Everything that governs a run rather than the model it runs. Two fields here were previously set in code with no rationale and no sweep - RUN.sample.flow_capacity_factor and RUN.sample.storage_capacity_exponent - which is the exact breach of proposal 8.1 that check_package.py exists to catch. RUN.controler.last_iteration carries a null value because no justified value has been measured; the resolver will not invent one.

| Field | Value | Units | Provenance | Sweep |
|---|---|---|---|---|
| `RUN.controler.compression_type` | `gzip` | enum | `definition` | - |
| `RUN.controler.create_graphs` | `true` | boolean | `definition` | - |
| `RUN.controler.first_iteration` | `0` | iterations | `definition` | - |
| `RUN.controler.last_iteration` | `1000` | iterations | `measured` | 250 - 2000 |
| `RUN.controler.overwrite_files` | `failIfDirectoryExists` | policy | `definition` | - |
| `RUN.controler.write_events_interval` | `10` | iterations | `definition` | - |
| `RUN.controler.write_plans_interval` | `10` | iterations | `definition` | - |
| `RUN.machine.event_handler_threads` | `4` | threads | `definition` | - |
| `RUN.machine.events_one_thread_per_handler` | `false` | boolean | `definition` | - |
| `RUN.machine.events_synchronize_on_simsteps` | `true` | boolean | `definition` | - |
| `RUN.machine.replanning_threads` | `10` | threads | `definition` | 1 - 24 |
| `RUN.machine.seed` | `20260810` | integer_seed | `definition` | - |
| `RUN.machine.threads` | `10` | threads | `definition` | 1 - 24 |
| `RUN.machine.xmx` | `14g` | jvm_heap | `definition` | - |
| `RUN.mode_choice.chain_based_modes` | `["car", "bike"]` | enum | `definition` | - |
| `RUN.mode_choice.consider_car_availability` | `true` | boolean | `definition` | - |
| `RUN.mode_choice.coord_distance_m` | `100.0` | metres | `literature` | 0 - 100 |
| `RUN.mode_choice.modes` | `["car", "ride", "pt", "bike", "walk"]` | enum | `definition` | - |
| `RUN.mode_choice.proba_random_single_trip_mode` | `0.5` | probability | `literature` | 0 - 0.5 |
| `RUN.mode_choice.subtour_behavior` | `betweenAllAndFewerConstraints` | enum | `literature` | `betweenAllAndFewerConstraints`, `fromSpecifiedModesToSpecifiedModes` |
| `RUN.monitor.enabled` | `true` | boolean | `definition` | - |
| `RUN.monitor.live_poll_s` | `0.5` | seconds | `definition` | - |
| `RUN.monitor.poll_s` | `3` | seconds | `definition` | - |
| `RUN.monitor.port` | `8731` | tcp_port | `definition` | - |
| `RUN.monitor.stall_s` | `300` | seconds | `definition` | - |
| `RUN.qsim.car_vehicle` | `{"length_m": 7.5, "width_m": 1.0, "pce": 1.0}` | metres/metres/passenger_car_equivalents | `definition` | - |
| `RUN.qsim.end_time_h` | `30` | hours | `definition` | - |
| `RUN.qsim.link_dynamics` | `PassingQ` | enum | `definition` | - |
| `RUN.qsim.main_mode` | `["car", "truck", "motorbike", "walk", "bike"]` | enum | `definition` | - |
| `RUN.qsim.snapshot_period` | `00:00:00` | hh:mm:ss | `definition` | - |
| `RUN.qsim.start_time_h` | `0` | hours | `definition` | - |
| `RUN.qsim.vehicles_source` | `modeVehicleTypesFromVehiclesData` | policy | `definition` | - |
| `RUN.relaxation.drift_tolerance_pp` | `0.5` | percentage_points | `assumed` | 0.1 - 1 |
| `RUN.relaxation.settle_margin_iterations` | `10` | iterations | `measured` | 1 - 100 |
| `RUN.replanning.fraction_to_disable_innovation` | `0.8` | share_of_iterations | `literature` | 0.7 - 0.9 |
| `RUN.replanning.max_agent_plan_memory` | `5` | plans | `literature` | 3 - 10 |
| `RUN.replanning.strategy_subpopulations` | `{"SubtourModeChoice": ["person"]}` | subpopulation_names_per_strategy | `definition` | - |
| `RUN.replanning.subpopulations` | `["person", "external", "freight"]` | subpopulation_names | `definition` | - |
| `RUN.replanning.weights` | `{"ChangeExpBeta": 0.7, "ReRoute": 0.15, "SubtourModeChoice": 0.1, "TimeAllocationMutator": 0.05}` | strategy_weight | `literature` | plus/minus 50% |
| `RUN.routing.access_egress_type` | `none` | policy | `definition` | - |
| `RUN.routing.access_walk_beeline_factor` | `1.6902` | ratio | `measured` | 1.294 - 1.794 |
| `RUN.routing.access_walk_speed_ms` | `1.25` | m/s | `derived` | derived: the same physical walking speed - the access/egress stub walk to and f |
| `RUN.routing.clear_default_teleported_params` | `true` | boolean | `definition` | - |
| `RUN.routing.network_modes` | `["car", "ride", "truck", "motorbike", "walk", "bike"]` | enum | `definition` | - |
| `RUN.sample.flow_capacity_factor` | *(null - unobtained)* | share_of_capacity | `derived` | derived: flowCapacityFactor = RUN.sample.fraction, the standard MATSim scaling  |
| `RUN.sample.fraction` | `0.01` | share_of_population | `assumed` | 0.01 - 0.4 |
| `RUN.sample.storage_capacity_exponent` | `1.0` | exponent | `derived` | derived: storageCapacityFactor = fraction ** 1.0 = flowCapacityFactor. MATSim e |
| `RUN.sample.storage_capacity_factor` | *(null - unobtained)* | share_of_capacity | `derived` | derived: storageCapacityFactor = RUN.sample.fraction ** RUN.sample.storage_capa |
| `RUN.sample.transit_capacity_floor` | `1` | seats | `assumed` | 1 - 4 |
| `RUN.sample.transit_capacity_scaling` | `true` | boolean | `derived` | derived: seats = max(floor, round(seats x RUN.sample.fraction)); not scaling it |
| `RUN.sample.unit` | `household` | enum | `derived` | derived: a sample drawn per PERSON keeps each household member independently, s |
| `RUN.scoring.brain_exp_beta` | `1.0` | logit_scale | `literature` | 0.5 - 2 |
| `RUN.scoring.early_departure_utils_per_h` | `0.0` | utils_per_hour | `assumed` | -18 - 0 |
| `RUN.scoring.late_arrival_utils_per_h` | `-18.0` | utils_per_hour | `literature` | -36 - -6 |
| `RUN.scoring.learning_rate` | `1.0` | share | `literature` | 0.5 - 1 |
| `RUN.scoring.waiting_utils_per_h` | `0.0` | utils_per_hour | `assumed` | -6 - 0 |
| `RUN.telemetry.live_interval_s` | `3600` | seconds | `definition` | - |
| `RUN.transit.transit_modes` | `["pt"]` | mode_names | `definition` | - |
| `RUN.transit.use_transit` | `true` | boolean | `definition` | - |
| `RUN.transit_router.max_beeline_walk_connection_m` | `300.0` | metres | `literature` | 100 - 500 |
| `RUN.travel_time.analysed_modes` | `["car"]` | mode_names | `definition` | - |
| `RUN.travel_time.separate_modes` | `false` | boolean | `definition` | - |

#### `RUN.controler.compression_type`

Output compression. MUST be gzip: runs made before this was set write .zst, which extract_metrics.py can only read if zstandard happens to be installed, and the repo does not require it.

***definition** · status **active** · DECISIONS.md §15 · MATSim `controler.compressionType`*

#### `RUN.controler.create_graphs`

Whether MATSim renders its per-iteration diagnostic PNGs (mode stats, leg histograms - eight images every iteration). Wall time and disk only, never the model; declared so a long arm's overlay can turn the rendering off instead of paying it a thousand times (9.59).

***definition** · status **active** · DECISIONS.md §9.59 · MATSim `controler.createGraphs`*

#### `RUN.controler.first_iteration`

Start iteration.

***definition** · status **active** · DECISIONS.md §15 · MATSim `controler.firstIteration`*

#### `RUN.controler.last_iteration`

Iterations to relaxation. MEASURED at 1000 by two full post-rebuild arms - 10% x 1000 (11.0 h, 54,617 agents) and 25% x 1000 (30.8 h, 136,068 agents), one arm at a time, same network build, seed 20260810 - and declared on that evidence (9.43, issue 5). WHAT IS MEASURED IS NARROWER THAN THE FIELD NAME: at 1000 the post-snap state is settled at both fractions (worst-mode drift +0.22 pp / +0.17 pp over the snap-aware window, inside RUN.relaxation.drift_tolerance_pp), and that result is fraction-independent. WHAT IS NOT MEASURED is whether 1000 iterations of SEARCH suffice: car mode share was still creeping +0.76 pp per 100 iterations at the cutoff, decaying x0.73 per 100, which extrapolates to roughly 2 pp of movement left in the innovated state when innovation was disabled. The 1500-iteration arm that would have measured that directly was CANCELLED BY THE OWNER for compute economy; the residual is carried as declared uncertainty, not resolved. Read this value with 9.43 beside it. Prior state, kept because it is the floor: two 1% runs of 250 iterations showed the model had NOT converged - innovation switches off at iteration 200 and ride still moved 0.619 to 0.664 over the last 50 iterations with no new plans being created. Shipped scenario configs now carry this measured value rather than the sweep floor; run_matsim.py still gives --iterations no default so a run states its own horizon.

***measured** · status **active** · DECISIONS.md §9.7, 9.43, 15 · MATSim `controler.lastIteration`*

#### `RUN.controler.overwrite_files`

What MATSim does with an output directory that already exists. Failing is deliberate: silently overwriting would let a re-run blend into a previous one, which is the same failure mode as a timing series outliving its run.

***definition** · status **active** · DECISIONS.md §15 · MATSim `controler.overwriteFiles`*

#### `RUN.controler.write_events_interval`

How often events are written. Affects disk and wall time, not the model.

***definition** · status **active** · DECISIONS.md §15 · MATSim `controler.writeEventsInterval`*

#### `RUN.controler.write_plans_interval`

How often plans are written. Affects disk and wall time, not the model.

***definition** · status **active** · DECISIONS.md §15 · MATSim `controler.writePlansInterval`*

#### `RUN.machine.event_handler_threads`

Threads for MATSim's parallel events manager. UNLIKE RUN.machine.threads this is a wall-time knob, NOT run identity: event handlers are observers - each still receives the complete stream in per-handler order, so scores, plans and every model output are unchanged (verified bit-identical against the single-thread default, DECISIONS.md 9.56). Declared because the framework default (null = one thread) was measured saturated on the all-physical model: 172-177 s CPU per ~265 s iteration at 25%, throttling ten qsim threads at every sim-step sync.

***definition** · status **active** · DECISIONS.md §9.56 · MATSim `eventsManager.numberOfThreads`*

#### `RUN.machine.events_one_thread_per_handler`

Give each registered event handler its own thread instead of sharing RUN.machine.event_handler_threads workers. A wall-time knob of the same class as event_handler_threads (handlers are observers; each still sees the complete stream in order - NOT run identity). 9.56 deliberately left this alone; 9.59 declares it so a timing probe can measure it: the 9.57 arm's busiest events runnable burned ~119 s CPU against a 145 s mobsim wall, so the heaviest single handler is the next binding constraint. Default false = the 9.56 behaviour, until a probe justifies otherwise.

***definition** · status **active** · DECISIONS.md §9.59 · MATSim `eventsManager.oneThreadPerHandler`*

#### `RUN.machine.events_synchronize_on_simsteps`

Whether the qsim waits for the events pipeline at every sim-step. True (the MATSim default) makes the wall time max(qsim, events) at each step; false decouples them so the wall approaches the slower of the two over the whole iteration, at the price of buffered events memory and of live per-step telemetry snapshots becoming eventually-consistent (RunTelemetry is a diagnostic instrument, not a result - 9.36). Model outputs are unchanged either way: handlers see the complete stream. Default true = current behaviour, until a probe justifies otherwise.

***definition** · status **active** · DECISIONS.md §9.59 · MATSim `eventsManager.synchronizeOnSimSteps`*

#### `RUN.machine.replanning_threads`

Thread count for replanning, routing and everything else global.numberOfThreads governs. RUN IDENTITY like RUN.machine.threads (per-thread work partitioning changes results); split from it in 9.59 so the replanning pool can be sized to the machine independently of the mobsim's declared partitioning. Held at the mobsim value until a timing probe justifies otherwise.

***definition** · status **active** · DECISIONS.md §9.59 · MATSim `global.numberOfThreads`*

#### `RUN.machine.seed`

MATSim random seed. Held at the master seed unless replications are being drawn.

***definition** · status **active** · DECISIONS.md §9.7 · MATSim `global.randomSeed`*

#### `RUN.machine.threads`

Mobsim thread count. PART OF THE RUN IDENTITY, NOT A PERFORMANCE KNOB: MATSim partitions the network by thread count, so changing it changes results. Until 9.59 this one field wrote global.numberOfThreads too; the pair is now two declared fields because they govern different partitionings (mobsim vs replanning/routing) with different saturation points - the 9.57 arm ran replanning at a median 59 s with 14 of 24 CPUs idle. Each field is run identity in its own right.

***definition** · status **active** · DECISIONS.md §9.5, 9.59 · MATSim `qsim.numberOfThreads`*

#### `RUN.machine.xmx`

JVM heap. Must exceed 9.6 GiB + 87 GiB x fraction or the run dies.

***definition** · status **active** · DECISIONS.md §9.5*

#### `RUN.mode_choice.chain_based_modes`

Modes whose vehicle must return home, so a tour cannot abandon it mid-chain.

***definition** · status **active** · DECISIONS.md §9.6 · MATSim `subtourModeChoice.chainBasedModes`*

#### `RUN.mode_choice.consider_car_availability`

MATSim defaults this to FALSE, which made mode choice ignore the car availability B1 synthesised. Must stay true.

***definition** · status **active** · DECISIONS.md §9.6 · MATSim `subtourModeChoice.considerCarAvailability`*

#### `RUN.mode_choice.coord_distance_m`

Distance within which two activity coordinates count as the same subtour location. At the default 0 two activities metres apart open a subtour that can never close.

***literature** · status **active** · DECISIONS.md §9.28 · MATSim `subtourModeChoice.coordDistance`*

> **Sweep basis.** 0 is the MATSim default and was live here unset; 100 is Open Berlin's value.

#### `RUN.mode_choice.modes`

Modes subtour mode choice may switch between. IF RIDE IS OMITTED, MATSim defaults to car,pt,bike,walk and a ride subtour becomes an ABSORBING STATE - ride sat at 0.18311 in every iteration to five decimals, and 18.6% of legs were an input wearing the costume of a result.

***definition** · status **active** · DECISIONS.md §9.6 · MATSim `subtourModeChoice.modes`*

#### `RUN.mode_choice.proba_random_single_trip_mode`

Probability that mode choice reassigns a SINGLE trip rather than a whole subtour. At the MATSim default of 0.0 every trip in a subtour must share one mode, so with chainBasedModes = car,bike there is no single-trip escape from a bike subtour and agents lock into bike once it wins (9.28).

***literature** · status **active** · DECISIONS.md §9.28 · MATSim `subtourModeChoice.probaForRandomSingleTripMode`*

> **Sweep basis.** 0.0 is the MATSim default, which its own source annotates as a backwards-compatibility setting that should be changed; 0.5 is the value Open Berlin, Leipzig and Kelheim all use.

#### `RUN.mode_choice.subtour_behavior`

How subtour mode choice treats tours it cannot close. Under the MATSim default fromSpecifiedModesToSpecifiedModes, AN AGENT WITH AN OPEN OR UNCLOSED SUBTOUR CANNOT CHANGE MODE AT ALL and is frozen at its seeded mode for the whole run - MATSim's own javadoc says to use betweenAllAndFewerConstraints if open subtours exist in the data (9.28).

***literature** · status **active** · DECISIONS.md §9.28 · MATSim `subtourModeChoice.behavior`*

#### `RUN.monitor.enabled`

Serve the live run view while a run is in flight. An OBSERVER only: it reads the run directory, holds no lock and writes nothing, so a run observed is byte-for-byte a run unobserved. It is not part of the run identity and cannot alter a result.

***definition** · status **active** · DECISIONS.md §9.19*

#### `RUN.monitor.live_poll_s`

How often the live view re-reads status WHILE THE MOBSIM IS SWEEPING. The mobsim runs a 30 h simulated day in about 15 s of wall clock, so the shipped RUN.monitor.poll_s of 3 s would sample the whole day five times and the peak would build and dissipate between two reads. 0.5 s matches the rate at which the run publishes windows at RUN.telemetry.live_interval_s = 3600 simulated seconds. Between mobsims the page falls back to RUN.monitor.poll_s, because nothing it shows changes during replanning and scoring.

***definition** · status **active** · DECISIONS.md §9.36*

#### `RUN.monitor.poll_s`

How often the page re-reads status. Well under a single iteration at any usable sample fraction (9.8 s at 1%, 56.4 s at 25%), so no iteration passes unseen.

***definition** · status **active** · DECISIONS.md §9.19*

#### `RUN.monitor.port`

Loopback port for the live run view. Bound on 127.0.0.1 only. If it is taken - a second concurrent run - the next free port is used and the actual url is printed, so parallel runs do not collide.

***definition** · status **active** · DECISIONS.md §9.19*

#### `RUN.monitor.stall_s`

How long the log may go untouched before the live view calls a run stalled rather than running. Comfortably longer than the slowest iteration measured (56.4 s at 25%) and than the events and plans writes that punctuate every tenth iteration, so a working run is never reported as stalled.

***definition** · status **active** · DECISIONS.md §9.19*

#### `RUN.qsim.car_vehicle`

The car vehicle type written into the run inputs' vehicles file: MATSim's own default vehicle, restated explicitly because qsim.vehiclesSource=modeVehicleTypesFromVehiclesData replaces the implicit default. Equality with MATSim's default (7.5 m, 1.0 m, PCE 1.0) is what keeps the car fleet's physics unchanged by the freight change - a value here that drifted from the default would silently change every car in the model.

***definition** · status **active** · DECISIONS.md §9.49*

#### `RUN.qsim.end_time_h`

Mobsim end. Matches B.activity.day_horizon_h; a 30-hour day catches after-midnight returns.

***definition** · status **active** · DECISIONS.md §15 · MATSim `qsim.endTime`*

#### `RUN.qsim.link_dynamics`

The queue discipline vehicles obey within a link: FIFO (MATSim's default - vehicles exit in entry order), PassingQ (a faster vehicle may overtake within the link), or SeepageQ. The emitted config carried NO value, so the all-physical model ran FIFO by silent default - under which a 1.25 m/s pedestrian at the head of a shared link's queue blocks every car behind it regardless of its PCE 0.0, directly contradicting 9.54's declared semantics ('neither impeding nor impeded by motor traffic': PCE governs capacity arithmetic, not exit order). PassingQ restores the declared semantics - a car overtakes a walker on the carriageway, which is also what a street does - and is the standard setting for multimodal single-network MATSim models. A MODEL CHANGE: part of the 9.58/9.59 family boundary.

***definition** · status **active** · DECISIONS.md §9.59 · MATSim `qsim.linkDynamics`*

#### `RUN.qsim.main_mode`

The modes physically simulated in the mobsim: car; truck (9.49) and motorbike (9.52) at their declared PCE; and walk and bike (9.54) - a pedestrian at PCE 0.0 capped at walking speed occupies the network without consuming road capacity (the sidewalk, expressed in queue arithmetic), a cyclist at the declared PCE genuinely takes road space. A car passenger is not a second vehicle: ride stays routed, with PAIRED passengers physically boarded (9.53).

***definition** · status **active** · DECISIONS.md §9.54 · MATSim `qsim.mainMode`*

#### `RUN.qsim.snapshot_period`

Interval between mobsim vehicle-position snapshots. Zero disables them: this study reads movement through RunTelemetry from inside the mobsim and through the event stream, not through snapshot files, which are large and are not part of any result.

***definition** · status **active** · DECISIONS.md §15 · MATSim `qsim.snapshotperiod`*

#### `RUN.qsim.start_time_h`

Mobsim start.

***definition** · status **active** · DECISIONS.md §15 · MATSim `qsim.startTime`*

#### `RUN.qsim.vehicles_source`

Where the mobsim gets a private vehicle's characteristics. Was `defaultVehicle` while car was the only main mode; the freight layer (9.49) needs a truck to weigh more than a car, so each main mode now takes the vehicle type of its own name from the vehicles file the run inputs emit - car restating MATSim's default exactly (RUN.qsim.car_vehicle), truck carrying B.freight.pce and B.freight.max_speed_kmh. TRANSIT vehicles are unaffected - they come from the schedule's own vehicles file, whose seats RUN.sample.transit_capacity_scaling scales.

***definition** · status **active** · DECISIONS.md §9.49 · MATSim `qsim.vehiclesSource`*

#### `RUN.relaxation.drift_tolerance_pp`

Largest absolute mode-share movement, in percentage points, that a run may still show after innovation is disabled and still be reported as settled. Measured per mode between the SETTLE POINT (the innovation cutoff plus RUN.relaxation.settle_margin_iterations) and the final iteration: after the cutoff MATSim creates no new plans, so whatever movement remains is relaxation rather than search. This decides a VERDICT ABOUT A RUN, not a model input - no agent sees it and changing it cannot move a mode share. It was 0.5 hard-coded as DRIFT_THRESHOLD_PP in summarise_run.py; the value is carried over unchanged so the migration is a move, not a re-decision. 9.7 measured mode share still drifting while innovation was already off and 9.27 put the iteration count needed at ~1000, so this is a floor for calling a run unsettled, never a claim that anything under it has converged. NOTE the window moved in 9.43: it used to start AT the cutoff, which included the one-iteration selection snap and made the gate unpassable at any horizon.

***assumed** · status **active** · DECISIONS.md §9.27*

#### `RUN.relaxation.settle_margin_iterations`

Iterations to skip AFTER the innovation cutoff before drift is measured, so the relaxation verdict scores relaxation and not the selection snap. When MATSim disables innovation, exploration noise stops in a single step and selection concentrates every agent onto its best-scoring plan: measured at iteration 801 of both 1000-iteration arms, car jumps +3.256 pp (10%) and +3.380 pp (25%) in that ONE iteration, walk falls 3.97 to 1.02% and pt 1.08 to 0.25%. That is a property of the scoring structure, not a run failing to settle - but the old window started at the cutoff and swept it into the drift number, so EVERY run of EVERY length failed the gate by ~3.5 pp regardless of horizon (9.43). The margin is 10 rather than 1 because a 10x guard on a one-iteration phenomenon costs nothing and matches the 10-iteration interval the outputs are written on; it is NOT tuned to pass. HONEST RESIDUAL: at 10 the worst-mode drift is +0.22 pp (10%) and +0.17 pp (25%), which passes the declared 0.5 pp tolerance but NOT the 0.1 pp floor of that tolerance's own sweep. The movement keeps decaying with margin (+0.089/+0.088 pp at 50, -0.008/+0.033 at 100), which is the signature of relaxation rather than of a metric artefact - a larger margin would pass the whole sweep, and is declined precisely because it would pass by measuring a shorter window.

***measured** · status **active** · DECISIONS.md §9.43*

#### `RUN.replanning.fraction_to_disable_innovation`

Share of iterations after which no new plans are created. At 250 iterations innovation stopped at 200 and mode share was still moving, which is how the non-convergence was identified.

***literature** · status **active** · DECISIONS.md §9.7 · MATSim `replanning.fractionOfIterationsToDisableInnovation`*

#### `RUN.replanning.max_agent_plan_memory`

Plans retained per agent. A property of the MATSim formulation, not of Newcastle.

***literature** · status **active** · DECISIONS.md §9.3 · MATSim `replanning.maxAgentPlanMemorySize`*

#### `RUN.replanning.strategy_subpopulations`

Which subpopulations each replanning strategy is emitted for; a strategy absent from this dict goes to all of them. SubtourModeChoice is restricted to `person` because an external or freight agent's mode IS its data: the through tier is seeded from classified cordon vehicle counts (9.41, 9.49), so a through car that innovates into another mode falsifies the count it was built from. MEASURED before this was declared: by iteration 100 of the first all-physical arm, 405 external agents had abandoned car - 451 walk legs, 164 bike, 62 pt, 256 ride - i.e. 40 km boundary crossings on foot, each also wedging at walk-less gate links (9.58). Read by the emitter through the schema's repeat_over.restrict clause, like RUN.replanning.subpopulations.

***definition** · status **active** · DECISIONS.md §9.58*

#### `RUN.replanning.subpopulations`

The subpopulations the replanning strategies are applied to. A vocabulary the model is defined over, not a value to tune: `person` is a modelled resident of the study area, `external` is a boundary-tier agent, and `freight` is a heavy-vehicle background agent (9.49) whose mode is locked to truck. The strategy set is emitted once per subpopulation, so this decides HOW MANY strategysettings blocks the config carries.

***definition** · status **active** · DECISIONS.md §15*

#### `RUN.replanning.weights`

Replanning strategy weights, applied to every subpopulation EXCEPT where RUN.replanning.strategy_subpopulations withholds a strategy (9.58: SubtourModeChoice is person-only - a boundary-tier agent's vehicle class is measured cordon data, not a choice). Properties of the scoring formulation, not observable quantities of Newcastle.

***literature** · status **active** · DECISIONS.md §9.3 · MATSim `replanning.strategysettings[*].weight`*

#### `RUN.routing.access_egress_type`

How a network-mode trip connects an activity to its first link. Set to none when walk became a NETWORK mode (9.54), because the default (accessEgressModeToLink) creates beeline stub legs of MODE walk - and the qsim casts every main-mode leg route to a NetworkRoute at agent insertion (PopulationAgentSource, measured: the 9.54 probe died on exactly that ClassCastException). The alternative (walkConstantTimeToLink) needs per-mode access/egress-time attributes on every link - a declared constant nobody has observed. Consequence stated: the stub access walk between an activity and its link is no longer a scored leg; it was a beeline artefact, and the 9.54 comparability break owns the scoring change.

***definition** · status **active** · DECISIONS.md §9.54 · MATSim `routing.accessEgressType`*

#### `RUN.routing.access_walk_beeline_factor`

Straight-line to path-distance ratio for the teleported access/egress stub walk. The measured walk detour factor, retired from the MAIN walk mode when walk became network-simulated (whose realised detour is now the road graph own), surviving here in its remaining teleported role.

***measured** · status **active** · DECISIONS.md §9.54 · MATSim `routing.teleportedModeParameters[non_network_walk].beelineDistanceFactor`*

> **Sweep basis.** Carried over verbatim from the retired RUN.routing.beeline_distance_factor_walk (9.54): measured over the observed A6 active network unioned with every road class a pedestrian may use. The quantity survives in the ACCESS-WALK role - the stub walk from an activity to its link is beeline-teleported, and this is the measured straight-line-to-path ratio for walking.

#### `RUN.routing.access_walk_speed_ms`

Speed of the teleported access/egress stub walk (non_network_walk) that connects an activity to its network link. The MAIN walk mode is network-simulated (9.54); this helper covers only the stub, and it carries the same declared walking speed.

***derived** · status **active** · DECISIONS.md §9.54 · MATSim `routing.teleportedModeParameters[non_network_walk].teleportedModeSpeed`*

> **Derived from** `A.transit.walk_speed_ms`: the same physical walking speed - the access/egress stub walk to and from a network link is walking, at the one declared walking speed

#### `RUN.routing.clear_default_teleported_params`

Clear MATSim built-in default teleportation parameters. Required once walk and bike are NETWORK modes (9.54): the built-in walk/bike defaults conflict with network routing outright (the config consistency check refuses the run - measured, the first 9.54 probe died on it), and a default that silently teleports a mode this model simulates is the right-by-accident defect class. Clearing also removes the non_network_walk helper defaults, so those are DECLARED below instead of inherited.

***definition** · status **active** · DECISIONS.md §9.54 · MATSim `routing.clearDefaultTeleportedModeParams`*

#### `RUN.routing.network_modes`

Modes routed on the road graph. Ride must be here AND permitted on the links (143,891 of them): declaring it a network mode that no link permits gives 'checking 0 nodes and 0 links' and a throw in PrepareForSim.

***definition** · status **active** · DECISIONS.md §9.6 · MATSim `routing.networkModes`*

#### `RUN.sample.flow_capacity_factor`

Road flow capacity scaled to the sample. DERIVED: equals RUN.sample.fraction exactly, which is the standard MATSim rule and is not a free choice. Set by the harness at run time. NOTE the SHIPPED scenario config carries 1.0, so running scenarios/matsim/<S>/<DAY>/config.xml DIRECTLY simulates a sampled demand against full supply - the harness must be used.

***derived** · status **computed** · DECISIONS.md §15 · MATSim `qsim.flowCapacityFactor`*

> **Derived from** `RUN.sample.fraction`: flowCapacityFactor = RUN.sample.fraction, the standard MATSim scaling rule

#### `RUN.sample.fraction`

Share of the synthetic population simulated. The subsample is NESTED - a person is kept if a hash of their id falls below the fraction, so 1% is a strict subset of 10% and a difference between fractions is a sample-size effect rather than a sampling one. EVERY P4 BEHAVIOURAL RESULT SO FAR WAS MEASURED AT 1% (5,209 persons, 0.85% of the population).

***assumed** · status **active** · DECISIONS.md §9.5, 15*

> **Sweep basis.** measured: 9.8 s/iteration and 9.8 GiB at 1%, 29.9 s and 18.4 GiB at 10%, ~64 s and 31.5 GiB at 25%. time = 3.1 s + 268 s x fraction, memory = 9.6 + 87 GiB x fraction, so 100% needs ~97 GiB and DOES NOT FIT in 63.5 GiB. The upper bound is the machine ceiling, not a modelling judgement

#### `RUN.sample.storage_capacity_exponent`

The exponent relating storage capacity to the sample fraction. IT IS AN EXPONENT, NOT THE PARAMETER: this field carried matsim_param qsim.storageCapacityFactor until the config emitter was built, which would have written the exponent 1.0 straight into the factor at every sample fraction - MATSim rejects 1.0 against a flow factor of 0.01 in one second. The factor is RUN.sample.storage_capacity_factor, computed from this and the fraction. IT IS 1.0 AND IT IS NOT FREE. An earlier revision of this registry declared it assumed with a 0.75-1.0 sweep, on the reasoning that MATSim floors link storage at one vehicle so a 1% sample would produce spurious spillback, and that raising storage relative to flow is the usual treatment. That reasoning is superseded. MATSim rejects any value below 1.0 outright and states the reason: 'the old approach of setting the stor cap fact larger than the flow cap fact is no longer needed since the qsim became a lot more deterministic'. The sweep was therefore a range whose members the tool will not accept, which is exactly the undisciplined declaration this registry exists to prevent. Corrected after the diagnostic run that tried to use it failed in one second. The remaining question - whether behaviour moves with the SAMPLE FRACTION itself - is unaffected and is what the 1% versus 10% arms test.

***derived** · status **active** · DECISIONS.md §15*

> **Derived from** `RUN.sample.fraction`: storageCapacityFactor = fraction ** 1.0 = flowCapacityFactor. MATSim enforces the equality: GlobalConfigGroup.checkConsistency throws when the two differ by more than global.relativeTolerance, which defaults to 0.0

#### `RUN.sample.storage_capacity_factor`

Link storage capacity scaled to the sample. NOT A FREE CHOICE and not the exponent: it is the exponent applied to the fraction, and the harness computes it per run. Split out from RUN.sample.storage_capacity_exponent when the config emitter was built, because the exponent had been bound directly to the factor parameter - two quantities in one field, of which only one is what MATSim reads.

***derived** · status **computed** · DECISIONS.md §15 · MATSim `qsim.storageCapacityFactor`*

> **Derived from** `RUN.sample.fraction`, `RUN.sample.storage_capacity_exponent`: storageCapacityFactor = RUN.sample.fraction ** RUN.sample.storage_capacity_exponent, which at the declared exponent of 1.0 equals flowCapacityFactor exactly. MATSim's GlobalConfigGroup.checkConsistency throws when the two differ by more than global.relativeTolerance, which defaults to 0.0

#### `RUN.sample.transit_capacity_floor`

Minimum seats after scaling, so a vehicle never becomes unusable. Capacity floors at 1 seat below about a 1.5% sample, which makes capacity systematically too generous at small fractions. Acceptable while crowding scoring is off; revisit if it is enabled (issue 12).

***assumed** · status **active** · DECISIONS.md §15*

#### `RUN.sample.transit_capacity_scaling`

Scale transit vehicle seats by the sample fraction. NOT OPTIONAL in practice: at a 10% sample an unscaled bus carries 70 sampled agents, i.e. 700 real ones, so capacity never binds and crowding silently disappears.

***derived** · status **active** · DECISIONS.md §15*

> **Derived from** `RUN.sample.fraction`: seats = max(floor, round(seats x RUN.sample.fraction)); not scaling it would give every vehicle 1/fraction times its real capacity

#### `RUN.sample.unit`

Whether the population subsample keeps whole HOUSEHOLDS or independent PERSONS. It was person-wise and undeclared until 9.45, and the cost was measured on the completed pilot arms: the share of ride legs whose household drives at all was 32.6% at a 10% sample and 43.1% at 25%, rising with the fraction because the sampler - not the demand - was deciding it. The sample still NESTS (a household id hashes to one number, so the 1% sample stays a strict subset of the 10%) and is still seeded and deterministic. The external and through boundary tiers hold no household by construction and continue to hash on their own id. What this buys is bought at a price that is stated rather than hidden: a household-clustered sample has higher variance at a given size than a person-wise one. Consumed by src/run/sample_population.py.

***derived** · status **active** · DECISIONS.md §9.45 · proposal §9*

> **Derived from** `RUN.sample.fraction`: a sample drawn per PERSON keeps each household member independently, so a household of size n retains on average f*n of its members and the probability that a given person keeps any co-member at all is 1-(1-f)^(n-1) - 0.14 at f=0.10 and 0.32 at f=0.25 for the mean household size here. Every household-coupled mechanism is therefore destroyed by the sampler in a way that is a function of the fraction, which is the one thing a sample fraction must not be. Sampling by household makes the retained population a set of WHOLE households, so the coupling is fraction-independent by construction. The identity, not a preference: it follows from what a fraction is meant to mean.

#### `RUN.scoring.brain_exp_beta`

The logit scale in the ChangeExpBeta plan-selection rule: how sharply an agent's probability of switching plans responds to the score difference between them. IT WAS UNDECLARED AND TYPED INTO THE CONFIG TEMPLATE until this change, which made the single parameter governing choice sharpness the one value in the scoring block that could not be swept. Not a property of Newcastle.

***literature** · status **active** · DECISIONS.md §9.3, 15 · MATSim `scoring.BrainExpBeta`*

> **Sweep basis.** MATSim's own default is 1.0 and the manual treats it as the conventional starting point rather than a measured quantity. The interval spans the range in common use: below 1 agents respond more softly to a utility difference and mode shares flatten, above 1 they respond more sharply and the model can lock in. Nothing about Newcastle bears on it.

#### `RUN.scoring.early_departure_utils_per_h`

Penalty for leaving an activity before its earliest end time. ZERO IS A CHOICE, not an absence of one, and it was typed into the config template rather than declared.

***assumed** · status **active** · DECISIONS.md §9.3, 15 · MATSim `scoring.earlyDeparture`*

> **Sweep basis.** Zero is an assumption that leaving an activity early costs nothing beyond the activity utility already forgone, which is the usual MATSim treatment and avoids charging the same shortfall twice. The interval allows an explicit penalty up to the late-arrival rate for a sensitivity arm.

#### `RUN.scoring.late_arrival_utils_per_h`

Penalty for arriving at an activity after its latest start time. Behavioural scoring, undeclared and typed into the config template until this change.

***literature** · status **active** · DECISIONS.md §9.3, 15 · MATSim `scoring.lateArrival`*

> **Sweep basis.** MATSim's conventional value is -18 utils/h, three times a typical performing rate, and the manual presents it as a convention rather than an estimate. The interval spans one third to twice that. No Newcastle observation bears on it: the HTS held is aggregate and carries no schedule-adherence measure.

#### `RUN.scoring.learning_rate`

How much of a plan's newly executed score replaces its remembered score. Governs how fast the co-evolution forgets, and therefore interacts with the iteration count the pilot exists to measure. A property of the MATSim formulation, not of Newcastle.

***literature** · status **active** · DECISIONS.md §9.3, 9.7, 15 · MATSim `scoring.learningRate`*

> **Sweep basis.** MATSim's default is 1.0, meaning a plan's score is replaced outright by the latest execution rather than blended with its history. Values below 1 blend, which damps oscillation at the cost of slower relaxation - directly relevant to issue 5, and therefore swept rather than pinned.

#### `RUN.scoring.waiting_utils_per_h`

Disutility of general waiting, over and above the opportunity cost of the time. NOT the public-transport wait - that is scoring.waitingPt, derived from C.time_weights.beta_wait, and confusing the two is the DECISIONS.md 9.28 defect class.

***assumed** · status **active** · DECISIONS.md §9.3, 9.28, 15 · MATSim `scoring.waiting`*

> **Sweep basis.** Zero avoids double-counting: general waiting is already priced through the forgone performing utility of the time. The interval allows an additional explicit disutility for a sensitivity arm. Distinct from scoring.waitingPt, which is DERIVED from the C1 beta_wait and is not this field.

#### `RUN.telemetry.live_interval_s`

Simulated seconds between live telemetry snapshots while the mobsim runs. The boundary is SIMULATED time, never wall clock, so a repeated run writes the same snapshots in the same places - the determinism rule applies to an observer as much as to a build script. 3600 puts one snapshot per simulated hour, which at the measured sweep rate (a 30 h day in about 15 s of wall clock) is roughly one every half second. Lowering it loses nothing - the file carries the accumulating profile of the day, not a single instant - it only refines the bins. This does NOT require writeEventsInterval to change: a registered handler receives the full event stream on every iteration whether or not that stream is also written to disk, which the package demonstrates at 26 event files against 251 leg histograms.

***definition** · status **active** · DECISIONS.md §9.19 · MATSim `telemetry.liveIntervalS`*

#### `RUN.transit.transit_modes`

The mode string the transit schedule is served under. One value, because the study scores public transport as a single mode and distinguishes tram from bus from rail by vehicle type inside it, not by mode.

***definition** · status **active** · DECISIONS.md §15 · MATSim `transit.transitModes`*

#### `RUN.transit.use_transit`

Whether the mobsim simulates the transit schedule at all. False would make every scenario in this study meaningless, which is exactly why it is declared rather than left as a literal nobody can see.

***definition** · status **active** · DECISIONS.md §15 · MATSim `transit.useTransit`*

#### `RUN.transit_router.max_beeline_walk_connection_m`

Maximum stop-to-stop distance at which the PT router will create a transfer. THIS PARAMETER ALONE CREATES EVERY INTERCHANGE IN THE MODEL: none of the five raw TfNSW feeds carries a transfers.txt, so the schedule holds zero minimalTransferTimes and nothing backstops it. At the unset default of 100 m the light rail at Newcastle Interchange reached Stand A (49.0 m), Stand B (95.1 m) and the heavy rail platforms (53.9-57.8 m) but NOT Stand C at 119.2-139.0 m, which carries the regional buses and NSW TrainLink - the external-origin connection hypothesis A3 falsifies on (9.28).

***literature** · status **active** · DECISIONS.md §9.28 · MATSim `transitRouter.maxBeelineWalkConnectionDistance`*

> **Sweep basis.** 100 m is the MATSim default that was live here unset; 300 m is the value Open Berlin, Leipzig and Kelheim all set. The upper bound spans Leipzig and Kelheim's 500 m extensionRadius.

#### `RUN.travel_time.analysed_modes`

Which modes contribute observed link travel times. Only car is physically simulated (RUN.qsim.main_mode), so only car can contribute one. See RUN.travel_time.separate_modes: the two are one decision in two parameters.

***definition** · status **active** · DECISIONS.md §9.29, 15 · MATSim `travelTimeCalculator.analyzedModes`*

#### `RUN.travel_time.separate_modes`

Whether travel times are accumulated per mode rather than once for the network. False with analysedModes=car is the pairing that makes `ride` read the car travel time it is routed on - the mechanism at the centre of issue 28. Declared so that pairing is visible and swept together, not typed into two adjacent lines of a template.

***definition** · status **active** · DECISIONS.md §9.29, 15 · MATSim `travelTimeCalculator.separateModes`*

## SUMO corridor (build and microsimulation)

*`cities/newcastle/registry/RUN_sumo.json` - 17 fields*

The corridor half of proposal 5.1: SUMO answers what the system physically does given riders, and what it costs other road users. Two things are declared here that the package does not have. The netconvert options that are MODELLING CHOICES are separated from those that are geometry handling, so a choice cannot hide inside a flag list - `tls_default_type` in particular stands in for the unobtained SCATS phasing. And the fields a SUMO RUN would need are declared even though no SUMO run harness exists: the corridor nets are built and have never been simulated.

| Field | Value | Units | Provenance | Sweep |
|---|---|---|---|---|
| `RUN.sumo.bbox_margin_m` | `300.0` | metres | `assumed` | 100 - 800 |
| `RUN.sumo.begin_h` | `0` | hours | `definition` | - |
| `RUN.sumo.crossings_enabled` | `false` | boolean | `definition` | - |
| `RUN.sumo.end_h` | `30` | hours | `definition` | - |
| `RUN.sumo.junctions_join` | `true` | boolean | `assumed` | `True`, `False` |
| `RUN.sumo.lefthand` | `true` | boolean | `definition` | - |
| `RUN.sumo.netconvert_options` | `["--osm.turn-lanes", "true", "--osm.elevation", "false", "--geometry.remove", "true", "--roundabouts.guess"...` | cli_flags | `definition` | - |
| `RUN.sumo.no_turnarounds` | `true` | boolean | `assumed` | `True`, `False` |
| `RUN.sumo.outer_loop_max_iterations` | `3` | iterations | `literature` | 2 - 5 |
| `RUN.sumo.projection` | `+proj=utm +zone=56 +south +ellps=GRS80 +units=m +no_defs` | proj4 | `definition` | - |
| `RUN.sumo.replications` | *(null - unobtained)* | count | `assumed` | 5 - 30 |
| `RUN.sumo.seed` | `20260810` | integer_seed | `definition` | - |
| `RUN.sumo.spreadtype` | `roadCenter` | enum | `definition` | - |
| `RUN.sumo.step_length_s` | `1.0` | seconds | `assumed` | 0.1 - 1 |
| `RUN.sumo.tls_default_type` | `actuated` | enum | `assumed` | `actuated`, `static` |
| `RUN.sumo.tls_guess_signals` | `true` | boolean | `assumed` | `True`, `False` |
| `RUN.sumo.tls_join` | `true` | boolean | `assumed` | `True`, `False` |

#### `RUN.sumo.bbox_margin_m`

Margin added around the corridor edge extent when clipping the OSM input for netconvert. Too small and turning traffic has nowhere to come from; too large and the corridor net stops being a corridor. Taken from the A1 edge endpoints rather than re-read from OSM, so the clip follows the built network.

***assumed** · status **active** · DECISIONS.md §3.6, 15*

#### `RUN.sumo.begin_h`

Microsimulation start. Declared; no SUMO run harness exists yet.

***definition** · status **active** · DECISIONS.md §15*

#### `RUN.sumo.crossings_enabled`

Pedestrian crossings and sidewalks in the SUMO corridor. FALSE BECAUSE THE OPTION SEGFAULTS netconvert 1.27.1 on this extract (exit 139), not because it was judged unnecessary - DECISIONS.md 3.6. CONSEQUENCE: there are no pedestrians in the SUMO corridor, so pedestrian delay MUST NOT be modelled there. Walk and frontage throughput are MATSim's job on A6. A toolchain change that fixes the segfault is a model change and belongs in DECISIONS.md 14.

***definition** · status **active** · DECISIONS.md §3.6 · proposal §3.3 B1, A6*

#### `RUN.sumo.end_h`

Microsimulation end, matching B.activity.day_horizon_s and RUN.qsim.end_time_h so the two tools cover the same day. Declared; no SUMO run harness exists yet.

***definition** · status **active** · DECISIONS.md §15*

#### `RUN.sumo.junctions_join`

Merge clustered approach nodes into one junction. Interacts with A.signals.junction_match_m: joining moves a junction centroid, which is why the A2 match radius is 60 m rather than A2's own 45 m clustering radius.

***assumed** · status **active** · DECISIONS.md §5, 15*

#### `RUN.sumo.lefthand`

Left-hand traffic. NOT optional and not cosmetic: with it off, netconvert builds right-hand connections and every turning movement on the corridor is wrong.

***definition** · status **active** · DECISIONS.md §3.6*

#### `RUN.sumo.netconvert_options`

The netconvert options that are geometry handling rather than modelling choices. Every option that IS a modelling choice is a separate registry field - lefthand, junctions_join, tls_guess_signals, tls_join, tls_default_type, no_turnarounds, spreadtype, crossings_enabled - so that a choice cannot hide inside a flag list.

***definition** · status **active** · DECISIONS.md §3.6*

#### `RUN.sumo.no_turnarounds`

Suppress U-turns at junctions. Left on because uncontrolled U-turns on a trunk corridor are an artefact of the network build rather than observed behaviour.

***assumed** · status **active** · DECISIONS.md §5, 15*

#### `RUN.sumo.outer_loop_max_iterations`

Maximum MATSim-SUMO outer iterations. Proposal 5.2 says 2-3 outer iterations to convergence. The loop stops when corridor run time is stable within E.coupling.outer_loop_tolerance_s - WHICH HAS NEVER BEEN DEFINED (issue 8), so this cap is currently the only thing that would terminate it.

***literature** · status **active** · DECISIONS.md §15 · proposal §5.2*

#### `RUN.sumo.projection`

The projection of EPSG:28356, stated as proj4 because netconvert takes a proj4 definition rather than an EPSG code. The datum label follows the repo's correction in DECISIONS.md 2.6 (GDA94, not GDA2020).

***definition** · status **active** · DECISIONS.md §2.6, 3.6*

#### `RUN.sumo.replications`

Seeded SUMO replications per scenario. NO VALUE: proposal 5.2 asks for at least 30, DECISIONS.md 9.5 shows the specified load does not fit on this machine, and nobody has decided what to cut (issue 6). Declaring it null means a SUMO harness cannot be built on an unexamined default.

***assumed** · status **unobtained** · DECISIONS.md §9.5, 15 · proposal §5.2*

#### `RUN.sumo.seed`

netconvert seed. Held at the master seed; netconvert output is byte-identical on rebuild, and check_package.py asserts it.

***definition** · status **active** · DECISIONS.md §3.6*

#### `RUN.sumo.spreadtype`

How lanes are spread about the reference geometry. roadCenter keeps the centreline as the road centre, which is what the A1 geometry represents.

***definition** · status **active** · DECISIONS.md §3.6*

#### `RUN.sumo.step_length_s`

Microsimulation time step. DECLARED BUT NOT YET CONSUMED: no SUMO run harness exists. Proposal 5.1 gives SUMO the supply and operations layer - run time, dwell, reliability variance, car delay, frontage throughput - and none of it has been executed.

***assumed** · status **active** · DECISIONS.md §15*

> **Sweep basis.** 1.0 s is the SUMO default; sub-second steps resolve car-following and signal response more finely at proportionally higher cost

#### `RUN.sumo.tls_default_type`

Signal controller type netconvert assigns. A real modelling choice standing in for information the project does not have: the corridor run time swings 38% between no priority and full priority, and this field is part of that uncertainty rather than a build detail.

***assumed** · status **active** · DECISIONS.md §5, 15*

#### `RUN.sumo.tls_guess_signals`

Infer signalised junctions from OSM traffic-signal nodes.

***assumed** · status **active** · DECISIONS.md §5, 15*

#### `RUN.sumo.tls_join`

Join adjacent traffic lights into one controller. Affects how many independent signal programs the corridor carries, and therefore what the A2 timings are applied to.

***assumed** · status **active** · DECISIONS.md §5, 15*
