# Configuration reference

**Generated from `config/registry/` by `src/registry/render_docs.py`. Do not edit by hand** - edit the registry and regenerate, or the two will disagree and `check_package.py` will say so.

Every value the model consumes that is not read from an immutable raw download is declared here with its units, its provenance, and either a sweep range or an explicit rule holding it fixed. That is proposal 8.1 - *"every parameter chosen without direct empirical support must be recorded with its rationale and its sweep range"* - enforced as a schema constraint rather than a convention.

## How to control any of it

```bash
# a run overlay - the committed way to vary a run
cp config/runs/example.json config/runs/my_run.json   # then edit
python src/run/run_matsim.py --scenario S2 --day WEEKDAY --run-config my_run

# a one-off override, checked against the same rules
python src/run/run_matsim.py --scenario S2 --day WEEKDAY \
    --set RUN.sample.fraction=0.10 --set RUN.controler.last_iteration=500

# or from the environment
WICKHAM_RUN_SAMPLE_FRACTION=0.10 python src/run/run_matsim.py --scenario S2 ...
```

Resolution order, lowest precedence first: `config/registry/*.json` -> `config/scenarios/<S>.json` -> `config/day/<DAY>.json` -> `config/runs/<tag>.json` -> `WICKHAM_*` environment -> `--set`. The resolved snapshot is written into every run directory as `_config.json`, so a result always carries the exact inputs that produced it.

Three things are refused at every layer:

1. **An unobtained input cannot acquire a point value by being read.** `get()` raises; the caller must select a sweep member explicitly.
2. **An overlay cannot invent a field.** A key that is not already declared is rejected.
3. **A value cannot silently leave its sweep, and a held-fixed value cannot move at all.** Escaping a range requires `allow_outside_sweep` plus a written justification in a committed overlay - never a flag typed at a shell.

## What the 142 fields are made of

| Provenance | Fields | Meaning |
|---|---:|---|
| `observed` | 2 | read directly from a raw download |
| `measured` | 5 | computed from observed data in this package |
| `derived` | 9 | follows from another registry field by identity |
| `literature` | 18 | a published value, not specific to Newcastle |
| `assumed` | 72 | chosen without direct empirical support |
| `definition` | 36 | fixed by the formulation, not an empirical quantity |

| Status | Fields | Meaning |
|---|---:|---|
| `active` | 129 | usable point value |
| `computed` | 2 | written at run time from other fields; do not hand-edit |
| `placeholder` | 4 | a structural stand-in; the model runs but the field is not defensible |
| `unobtained` | 7 | the datum does not exist in the package; must be swept, never pinned |

### The 7 fields with no value

These carry `value: null` and the resolver refuses to return a point value for them. They are the project's honest edge: what it does not know, declared rather than guessed.

| Field | Sweep | Why it has no value |
|---|---|---|
| `A.lightrail.dwell_charging_s` | 10 - 35 | NOT MEASURED - a few hours of field observation at Civic or Crown Street would resolve it (DECISIONS.md 13 priority 2) |
| `A.signals.scats_phasing` | `proxy_no_priority`, `proxy_partial_priority`, `proxy_full_priority` | NOT OBTAINED - a formal TfNSW request is outstanding |
| `B.opal.journey_linked` | `tap_sequence_matching_model` | NOT OBTAINED - a formal TfNSW request is outstanding |
| `D.retail.vacancy_rate` | 0 - 0.25 | NOT OBTAINED and not currently consumed by any metric |
| `E.coupling.outer_loop_tolerance_s` | 5 - 60 | Proposal 5.2 defers this explicitly - run the loop 'until the corridor run time is stable within a tolerance TO BE DEFINED AT CALIBRATION' |
| `RUN.controler.last_iteration` | 250 - 2000 | NO JUSTIFIED VALUE HAS BEEN MEASURED |
| `RUN.sumo.replications` | 5 - 30 | NO VALUE: proposal 5.2 asks for at least 30, DECISIONS.md 9.5 shows the specified load does not fit on this machine, and nobody has decided what to cu |

### The 6 fields held fixed

Not tunable. DECISIONS.md 8.5 holds the mode constants fixed because calibrating them would fit away the effect under test - proposal 9 names ASC absorption as the primary threat to validity.

- `C.asc.bus` - DECISIONS.md 8.5: these are priors for the first calibration pass only and must not be freely calibrated. Either estimate them on the pre-intervention period (era 3, 2018) and hold
- `C.asc.car_passenger` - Constrained, not calibrated. DECISIONS.md 9.8 solves this constant so the modelled ride:car leg ratio reproduces the OBSERVED passenger:driver ratio (0.3503, HTS). That is the seco
- `C.asc.cycle` - DECISIONS.md 8.5: these are priors for the first calibration pass only and must not be freely calibrated. Either estimate them on the pre-intervention period (era 3, 2018) and hold
- `C.asc.light_rail` - DECISIONS.md 8.5: these are priors for the first calibration pass only and must not be freely calibrated. Either estimate them on the pre-intervention period (era 3, 2018) and hold
- `C.asc.rail` - DECISIONS.md 8.5: these are priors for the first calibration pass only and must not be freely calibrated. Either estimate them on the pre-intervention period (era 3, 2018) and hold
- `C.asc.walk` - DECISIONS.md 8.5: these are priors for the first calibration pass only and must not be freely calibrated. Either estimate them on the pre-intervention period (era 3, 2018) and hold

## Network supply (A1-A6)

*`config/registry/A_supply.json` - 28 fields*

Road graph, signal control, transit supply, light rail vehicle and dwell, parking and the active network. Two of the three inputs the proposal named as critical and unobtained live here - A.signals.scats_phasing and A.lightrail.dwell_charging_s - and both carry status 'unobtained' with a null value, so the resolver refuses to hand back a point value and the caller must select a sweep member. That is DECISIONS.md 0 and 13 enforced structurally rather than by discipline.

| Field | Value | Units | Provenance | Sweep |
|---|---|---|---|---|
| `A.active.footway_width_default` | `{"steps": 1.5, "pedestrian": 6.0, "footway": 1.8, "path": 1.5, "cycleway": 2.5, "track": 2.5, "corridor": 2...` | metres | `assumed` | 1 - 6 |
| `A.corridor.cross_buffer_m` | `40.0` | metres | `assumed` | 25 - 60 |
| `A.corridor.extension_lane_take` | `1` | lanes | `assumed` | 0 - 1 |
| `A.corridor.off_corridor_penalty` | `12.0` | dimensionless_cost_multiplier | `assumed` | 6 - 20 |
| `A.corridor.parallel_buffer_m` | `1500.0` | metres | `assumed` | 1000 - 2500 |
| `A.corridor.pre_lr_lanes_per_dir` | `2` | lanes_per_direction | `assumed` | 1 - 2 |
| `A.corridor.trunk_buffer_m` | `60.0` | metres | `assumed` | 40 - 100 |
| `A.lightrail.corridor_speed_kmh` | `60.0` | km_per_hour | `assumed` | 40 - 70 |
| `A.lightrail.dwell_charging_s` | *(null - unobtained)* | seconds_per_intermediate_stop | `assumed` | 10 - 35 |
| `A.lightrail.dwell_fixed_s` | `8.0` | seconds_per_stop | `assumed` | 5 - 15 |
| `A.lightrail.line_speed_kmh` | `40.0` | km_per_hour | `assumed` | 30 - 50 |
| `A.lightrail.tsp_enabled` | `false` | boolean | `assumed` | `False`, `True` |
| `A.parking.capacity_default` | `{"onstreet": 12, "offstreet_public": 60, "offstreet_private": 40}` | spaces_per_facility | `assumed` | 5 - 100 |
| `A.parking.free_occupancy_profile` | `[0.1, 0.08, 0.07, 0.06, 0.08, 0.14, 0.28, 0.46, 0.6, 0.66, 0.7, 0.72, 0.73, 0.72, 0.7, 0.66, 0.58, 0.46, 0....` | occupancy_ratio_by_hour | `assumed` | plus/minus 25% |
| `A.road.capacity_default` | `{"motorway": 2000, "trunk": 1800, "primary": 1600, "secondary": 1400, "tertiary": 1200, "unclassified": 100...` | vehicles_per_hour_per_lane | `assumed` | 300 - 2200 |
| `A.road.lanes_default` | `{"motorway": 2, "trunk": 2, "primary": 2, "secondary": 1, "tertiary": 1, "unclassified": 1, "residential": ...` | lanes_per_direction | `assumed` | 1 - 3 |
| `A.road.speed_default` | `{"motorway": 100, "trunk": 80, "primary": 60, "secondary": 60, "tertiary": 50, "unclassified": 50, "residen...` | km_per_hour | `assumed` | 10 - 110 |
| `A.signals.delay_per_intersection_s` | `26.0` | seconds | `assumed` | 15 - 40 |
| `A.signals.junction_match_m` | `60.0` | metres | `assumed` | 30 - 100 |
| `A.signals.min_green_s` | `6.0` | seconds | `assumed` | 4 - 10 |
| `A.signals.n_corridor_intersections` | `14` | count | `observed` | - |
| `A.signals.scats_phasing` | *(null - unobtained)* | phase_plan | `assumed` | `proxy_no_priority`, `proxy_partial_priority`, `proxy_full_priority` |
| `A.transit.era1_line_speed_kmh` | `60.0` | km_per_hour | `assumed` | 45 - 75 |
| `A.transit.era1_station_dwell_s` | `30.0` | seconds | `assumed` | 20 - 45 |
| `A.transit.interchange_radius_m` | `250` | metres | `assumed` | 150 - 400 |
| `A.transit.s0_join_tolerance_m` | `1500.0` | metres | `assumed` | 800 - 2500 |
| `A.transit.sbc_extension_km` | `6.65` | kilometres | `observed` | - |
| `A.transit.walk_speed_ms` | `1.25` | metres_per_second | `literature` | 1 - 1.4 |

#### `A.active.footway_width_default`

Fallback footway width. Footway widths were not obtained for Newcastle.

***assumed** · status **active** · DECISIONS.md §3.1*

#### `A.corridor.cross_buffer_m`

Distance within which a turn restriction or cross street is treated as on the corridor. At 40 m, 10 of the 1,385 resolved restrictions fall on the alignment, against the 14 E1 assumed.

***assumed** · status **active** · DECISIONS.md §3.4*

#### `A.corridor.extension_lane_take`

Lanes removed per direction where an S4/S5 extension runs in the carriageway.

***assumed** · status **active** · DECISIONS.md §3.4*

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

#### `A.corridor.trunk_buffer_m`

Distance from the alignment within which a road edge is classified corridor trunk.

***assumed** · status **active** · DECISIONS.md §3.4*

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

#### `A.lightrail.line_speed_kmh`

Light rail running speed between stops, used in the run-time decomposition.

***assumed** · status **active** · DECISIONS.md §4.2*

#### `A.lightrail.tsp_enabled`

Transit signal priority on the corridor. Downstream of A.signals.scats_phasing.

***assumed** · status **active** · DECISIONS.md §5 · proposal §3.4 S-b*

#### `A.parking.capacity_default`

Fallback capacity where a parking facility carries none. 4,861 of 7,710 facilities carry an observed capacity.

***assumed** · status **active** · DECISIONS.md §6*

#### `A.parking.free_occupancy_profile`

Hourly occupancy profile for free parking. Assumed: parking meter transactions were not obtained (DECISIONS.md 13 priority 6-adjacent).

***assumed** · status **active** · DECISIONS.md §6*

#### `A.road.capacity_default`

Saturation flow by road class. Never observed; a class-level convention.

***assumed** · status **active** · DECISIONS.md §3.2*

#### `A.road.lanes_default`

Fallback lane count where OSM carries no lanes tag. Applied only to edges with no observation - DECISIONS.md 2.5 corrected the proposal premise that the corridor is 75-98% imputed: as-built trunk lane counts are observed in OSM for 87.5% of corridor trunk edges. Full class table is in the build script; the registry overrides per class.

***assumed** · status **active** · DECISIONS.md §3.1*

> **Sweep basis.** the plausible range for an unlabelled edge of each class

#### `A.road.speed_default`

Fallback free-flow speed where OSM carries no maxspeed tag.

***assumed** · status **active** · DECISIONS.md §3.1*

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

#### `A.signals.scats_phasing`

SCATS phase data for the Hunter/Scott corridor. NOT OBTAINED - a formal TfNSW request is outstanding. It determines corridor run time more than any other single input: the swing between no priority and full priority is 38% (S2 vs S2b). Every program in the SUMO corridor is labelled timing_source=assumed. THIS FIELD HAS NO POINT VALUE AND THE RESOLVER WILL NOT INVENT ONE: select a sweep member explicitly.

***assumed** · status **unobtained** · DECISIONS.md §0, 5, 13 · proposal §6.2, 7.2*

#### `A.transit.era1_line_speed_kmh`

Heavy rail line speed in the reconstructed pre-2014 era. No 2014 public timetable has been obtained to validate this (DECISIONS.md 13 priority 8).

***assumed** · status **active** · DECISIONS.md §11*

#### `A.transit.era1_station_dwell_s`

Heavy rail station dwell in the reconstructed pre-2014 era.

***assumed** · status **active** · DECISIONS.md §11*

#### `A.transit.interchange_radius_m`

Radius within which two stops are treated as one interchange for transfer generation.

***assumed** · status **active** · DECISIONS.md §11*

#### `A.transit.s0_join_tolerance_m`

Tolerance for joining the retained heavy rail alignment to the observed network in S0.

***assumed** · status **active** · DECISIONS.md §3.4*

#### `A.transit.sbc_extension_km`

Broadmeadow extension length as STATED in the Strategic Business Case. The alignment routed over observed OSM centreline is 7.00 km, 5.3% longer. The model uses the routed geometry; this field records the published figure.

***observed** · status **active** · DECISIONS.md §3.4*

#### `A.transit.walk_speed_ms`

Walk speed used to generate GTFS transfer times. Distinct from the MATSim teleported walk speed - see RUN.matsim.teleported_walk_speed_ms, which is 1.05.

***literature** · status **active** · DECISIONS.md §11*

## Demand (B1-B5)

*`config/registry/B_demand.json` - 27 fields*

Synthetic population, activity and tour generation, external boundary demand, and the count-comparison corrections. The third unobtained input, B.opal.journey_linked, lives here. B.activity.p_intermediate_stop is the demand-side parameter with the most leverage over mode share and is assumed.

| Field | Value | Units | Provenance | Sweep |
|---|---|---|---|---|
| `B.activity.act_duration_min` | `{"HW": 465, "HE": 360, "HS": 45, "HO": 90, "WB": 60, "NHB": 20}` | minutes | `assumed` | plus/minus 25% |
| `B.activity.child_tour_retention` | `0.4` | probability | `assumed` | 0.25 - 0.6 |
| `B.activity.day_horizon_s` | `108000` | seconds | `definition` | - |
| `B.activity.day_purpose_mix` | `{"WEEKDAY": {"HW": 1.0, "HE": 1.0, "HS": 0.9, "HO": 0.9, "WB": 1.0, "NHB": 1.0}, "SAT": {"HW": 0.25, "HE": ...` | multiplier_on_weekday | `assumed` | plus/minus 30% |
| `B.activity.days_per_week` | `{"WEEKDAY": 5.0, "SAT": 1.0, "SUN": 1.0}` | days | `definition` | - |
| `B.activity.detour_factor` | `1.3376` | ratio | `measured` | 1.25 - 1.423 |
| `B.activity.duration_cv` | `0.3` | coefficient_of_variation | `assumed` | 0.2 - 0.45 |
| `B.activity.hts_rate_per_person_day` | `3.473` | trips_per_person_per_day | `measured` | 3.3 - 3.65 |
| `B.activity.p_intermediate_stop` | `{"HW": 0.22, "HE": 0.12, "HS": 0.18, "HO": 0.2, "WB": 0.3}` | probability | `assumed` | 0.1 - 0.35 |
| `B.activity.p_mandatory` | `{"WEEKDAY": {"work": 0.78, "education": 0.85}, "SAT": {"work": 0.16, "education": 0.03}, "SUN": {"work": 0....` | probability | `assumed` | 0.6 - 0.95 |
| `B.activity.p_second_stop` | `0.25` | probability | `assumed` | 0.12 - 0.4 |
| `B.activity.sat_to_sun_rate` | `1.1875` | ratio | `assumed` | 1 - 1.45 |
| `B.activity.weekend_departure_shift_h` | `{"WEEKDAY": 0, "SAT": 1, "SUN": 1}` | hours | `assumed` | 0 - 2 |
| `B.activity.weekend_to_weekday` | `0.7521` | ratio | `measured` | 0.709 - 0.816 |
| `B.counts.heavy_vehicle_share` | `0.0652` | share_of_vehicles | `measured` | 0.0129 - 0.1529 |
| `B.counts.station_match_radius_m` | `120.0` | metres | `assumed` | 60 - 120 |
| `B.counts.vehicles_per_car_leg` | `1.0` | vehicles_per_leg | `derived` | derived: observed vehicle trips ARE driver trips at occupancy 1.3503, so a car  |
| `B.counts.vehicles_per_ride_leg` | `0.0` | vehicles_per_leg | `derived` | derived: a passenger rides in a vehicle already counted, so a ride leg contribu |
| `B.external.day_factor` | `{"WEEKDAY": 1.0, "SAT": 0.4, "SUN": 0.3}` | multiplier | `assumed` | plus/minus 30% |
| `B.external.interaction_rate` | `0.08` | probability | `assumed` | 0.04 - 0.15 |
| `B.external.person_id_base` | `900000000` | integer_offset | `definition` | - |
| `B.external.purpose_split` | `{"HW": 0.7, "HO": 0.3}` | probability | `assumed` | plus/minus 20% |
| `B.opal.journey_linked` | *(null - unobtained)* | dataset | `assumed` | `tap_sequence_matching_model` |
| `B.population.age_bands` | `[[0, 4], [5, 11], [12, 17], [18, 24], [25, 34], [35, 44], [45, 54], [55, 64], [65, 74], [75, 84], [85, 120]]` | years | `definition` | - |
| `B.population.licence_rate_by_age_band` | `[0, 0, 0, 0.62, 0.88, 0.93, 0.94, 0.93, 0.88, 0.72, 0.45]` | probability | `literature` | plus/minus 10% |
| `B.population.ride_requires_household_driver` | `true` | boolean | `derived` | derived: a person may be a car passenger only if their B1 household holds at le |
| `B.seed.master` | `20260810` | integer_seed | `definition` | - |

#### `B.activity.act_duration_min`

Mean activity duration by purpose.

***assumed** · status **active** · DECISIONS.md §9.2*

#### `B.activity.child_tour_retention`

Share of child tours retained as independent tours.

***assumed** · status **active** · DECISIONS.md §9.2*

#### `B.activity.day_horizon_s`

Simulation day horizon, 30 hours. Matches RUN.qsim.end_time_h. No leg may arrive after it; the P1 chains had 1.77% arriving late, latest 36.0 h. The build script writes it as the expression 30 * 3600, which is not a literal and so is not compared by value in the legacy-drift check.

***definition** · status **active** · DECISIONS.md §9.2*

#### `B.activity.day_purpose_mix`

Weekend purpose mix relative to the weekday.

***assumed** · status **active** · DECISIONS.md §9.2*

#### `B.activity.days_per_week`

Days each day type represents when composing a week.

***definition** · status **active** · DECISIONS.md §9.2*

#### `B.activity.detour_factor`

Straight-line to network distance, routed over the observed A1 road graph. Replaces an assumed 1.30. The build script keeps a 1.30 fallback labelled 'assumed - C2 factors file not found'; that fallback is now this field.

***measured** · status **active** · DECISIONS.md §9.2 · was `src/build/build_activity_chains.py:DETOUR_FACTOR`*

> **Sweep basis.** the interquartile range of the per-pair ratios over 551 population-weighted zone pairs

#### `B.activity.duration_cv`

Spread of activity duration around its mean.

***assumed** · status **active** · DECISIONS.md §9.2*

#### `B.activity.hts_rate_per_person_day`

Observed NSW HTS trip rate the synthesis is calibrated to reproduce. The realised rate is 3.397, 2.2% low.

***measured** · status **active** · DECISIONS.md §9.2*

#### `B.activity.p_intermediate_stop`

Probability a tour carries an intermediate stop, by purpose. WATCH THIS ONE: it decides how many sub-tours exist and therefore how freely MATSim mode choice can vary within a day. It is assumed, and it is the demand-side parameter with the most leverage over mode share. 56.7% of persons have more than one tour at the shipped values.

***assumed** · status **active** · DECISIONS.md §9.2*

#### `B.activity.p_mandatory`

Probability an employed person or student attends on a given day type.

***assumed** · status **active** · DECISIONS.md §2.4, 9.2*

> **Sweep basis.** the work entry is bounded BELOW by the census G62 observed attendance of 0.651, which bounds the sweep and is not allowed to set the value, because census night was August 2021 with 19.2% working from home

#### `B.activity.p_second_stop`

Probability of a second intermediate stop, given a first.

***assumed** · status **active** · DECISIONS.md §9.2*

#### `B.activity.sat_to_sun_rate`

Saturday-to-Sunday trip rate ratio. THE LAST ASSUMED PART OF THE DAY-TYPE SHAPE: the weekday/weekend ratio itself is measured (B.activity.weekend_to_weekday), but the HTS LGA tables carry no day-of-week split, so how the weekend divides stays assumed (DECISIONS.md 13 priority 12).

***assumed** · status **active** · DECISIONS.md §9.2*

#### `B.activity.weekend_departure_shift_h`

Shift applied to the weekday departure profile on weekend day types.

***assumed** · status **active** · DECISIONS.md §9.2*

#### `B.activity.weekend_to_weekday`

Weekend vs weekday travel, measured from the RMS traffic counts own WEEKDAYS and WEEKENDS periods. Replaces an assumed value that implied 0.825. Vehicle volume, not person trips.

***measured** · status **active** · DECISIONS.md §9.2*

> **Sweep basis.** observed across 551 RMS station-years

#### `B.counts.heavy_vehicle_share`

Heavy vehicle share, applied AT COMPARISON TIME to the comparison and not to the model, because the model represents no freight. At the 23 stations with a classified count the station own observed share is used; at the remaining 96 this median is assumed. Only 3 of the 34 calibration stations are classified, so the assumed case is the usual one.

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

#### `B.external.day_factor`

External boundary demand by day type, relative to the weekday.

***assumed** · status **active** · DECISIONS.md §9.2*

#### `B.external.interaction_rate`

Rate at which external-tier residents interact with the core. LOCALISABLE BUT NOT YET AVAILABLE: the ABS journey-to-work origin-destination table (SA2 usual residence x SA2 place of work) would settle it. The package holds the place-of-work side but not the pairing. A standard TableBuilder extract, not a formal request (DECISIONS.md 13 priority 11).

***assumed** · status **active** · DECISIONS.md §9.2, 13*

#### `B.external.person_id_base`

Id offset that keeps external agents distinguishable from core agents.

***definition** · status **active** · DECISIONS.md §9.2*

#### `B.external.purpose_split`

Purpose split for external boundary demand.

***assumed** · status **active** · DECISIONS.md §9.2*

#### `B.opal.journey_linked`

Journey-linked Opal. NOT OBTAINED - a formal TfNSW request is outstanding. Proposal 6.1 calls it 'the difference between a good model and a guess'. It is what would let C.transfer.beta_transfer_penalty_min be ESTIMATED rather than swept. Until it lands the transfer penalty stays a curve across 3-15 min.

***assumed** · status **unobtained** · DECISIONS.md §0, 13 · proposal §6.1, 7.2*

#### `B.population.age_bands`

Age banding for population synthesis. Follows the census table structure.

***definition** · status **active** · DECISIONS.md §9.1*

#### `B.population.licence_rate_by_age_band`

Driver licence holding by age band, aligned to B.population.age_bands.

***literature** · status **active** · DECISIONS.md §9.1*

#### `B.population.ride_requires_household_driver`

Whether `ride` is withheld from a person with nobody to drive them. MATSim's standard treatment lets any agent be a car passenger on any trip; DECISIONS.md 9.10 measures the cost at 0.72 of legs against an observed 0.206, unmoved by a tenfold sample increase, i.e. 5.9 people per car. Core MATSim can restrict `car` per person via `carAvail` but has no equivalent for `ride`, and subtourModeChoice.modes is global, so the fix is a person attribute honoured by a custom PermissibleModesCalculator (src/java/wickham/). Setting this false restores the previous behaviour for comparison. RESIDUAL LIMITATION, stated not hidden: this makes ride available or not per person, it does NOT bind a passenger to a specific driver at a specific time - that is the socnetsim joint-plans contrib (Dubernet & Axhausen), absent from the pinned jar and out of scope.

***derived** · status **active** · DECISIONS.md §8.5, 9.10, 15 · proposal §9*

> **Derived from** `B.seed.master`: a person may be a car passenger only if their B1 household holds at least one vehicle AND contains at least one OTHER licence holder who could drive them; computed from B1_synthetic_population.csv household_id, household_vehicles and licence_holder, so it is derived from the synthetic population rather than chosen

#### `B.seed.master`

The one seed everything synthetic derives from. CLAUDE.md forbids unseeded randomness, wall-clock dependence and dict/set-ordering dependence anywhere in a build script. Changing this changes every synthetic artefact.

***definition** · status **active** · DECISIONS.md §9.1*

## Behavioural parameters (C1)

*`config/registry/C_behaviour.json` - 33 fields*

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
| `C.constraint.vehicle_occupancy` | `1.3503` | persons_per_vehicle | `measured` | 1.2493 - 1.394 |
| `C.crowding.seated_multiplier` | `1.0` | ratio | `literature` | 1 - 1.15 |
| `C.crowding.standing_multiplier` | `1.45` | ratio | `literature` | 1.2 - 1.8 |
| `C.gradient.downhill_penalty_per_pct` | `0.02` | utils_per_percent_grade | `assumed` | 0 - 0.05 |
| `C.gradient.uphill_penalty_per_pct` | `0.09` | utils_per_percent_grade | `assumed` | 0.05 - 0.14 |
| `C.nesting.active_coefficient` | `0.7` | dimensionless | `assumed` | 0.5 - 0.95 |
| `C.nesting.private_coefficient` | `0.8` | dimensionless | `assumed` | 0.5 - 0.95 |
| `C.nesting.pt_coefficient` | `0.65` | dimensionless | `assumed` | 0.5 - 0.95 |
| `C.scoring.marginal_utility_of_money` | `1.0` | utils_per_AUD | `definition` | - |
| `C.scoring.monetary_distance_rate` | `{"car": -0.00018, "ride": 0.0, "pt": 0.0, "walk": 0.0, "bike": 0.0}` | AUD_per_metre | `derived` | -0.00025 - -0.00012 |
| `C.scoring.performing_utils_per_h` | `6.0` | utils_per_hour | `literature` | 4 - 8 |
| `C.time_weights.beta_headway` | `0.5` | ratio_to_ivt | `literature` | 0.35 - 0.65 |
| `C.time_weights.beta_ivt` | `1.0` | ratio_to_ivt | `definition` | - |
| `C.time_weights.beta_reliability` | `1.3` | ratio_to_ivt | `literature` | 0.8 - 1.8 |
| `C.time_weights.beta_wait` | `2.0` | ratio_to_ivt | `literature` | 1.5 - 2.5 |
| `C.time_weights.beta_walk_access` | `2.0` | ratio_to_ivt | `literature` | 1.5 - 2.5 |
| `C.time_weights.beta_walk_egress` | `2.0` | ratio_to_ivt | `literature` | 1.5 - 2.5 |
| `C.transfer.beta_transfer_penalty_min` | `8.0` | minutes_equivalent | `assumed` | 3 - 15 |
| `C.vot.by_purpose` | `{"HW": 18.6, "HE": 9.3, "HS": 15.2, "HO": 15.2, "WB": 55.4, "NHB": 15.2}` | AUD_2026_per_hour | `literature` | plus/minus 30% |
| `C.vot.concession_factor` | `0.75` | ratio | `literature` | 0.6 - 0.9 |
| `C.vot.trip_weighted` | `16.96` | AUD_2026_per_hour | `derived` | plus/minus 30% |
| `C.walk.decay_beta_per_m` | `0.0018` | per_metre | `assumed` | 0.001 - 0.003 |
| `C.walk.decay_form` | `negative_exponential` | enum | `assumed` | `negative_exponential`, `cumulative_gaussian` |
| `C.walk.gaussian_mu_m` | `700.0` | metres | `assumed` | 500 - 900 |
| `C.walk.gaussian_sigma_m` | `420.0` | metres | `assumed` | 300 - 550 |

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

Alternative-specific constant relative to car driver = 0.

***assumed** · status **active** · DECISIONS.md §8.5*

> **Held fixed.** DECISIONS.md 8.5: these are priors for the first calibration pass only and must not be freely calibrated. Either estimate them on the pre-intervention period (era 3, 2018) and hold fixed, or constrain them and report the constraint. Proposal 9 names ASC absorption as the PRIMARY threat to validity: calibrating mode constants to observed patronage fits away the effect under test.
>
> *Departure requires: a departure logged in DECISIONS.md BEFORE results are seen*

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

#### `C.scoring.marginal_utility_of_money`

Sets the utility numeraire to AUD. Definitional, not empirical.

***definition** · status **active** · DECISIONS.md §9.3 · MATSim `scoring.marginalUtilityOfMoney`*

#### `C.scoring.monetary_distance_rate`

Vehicle operating cost per metre. RIDE IS ZERO AND THAT IS DERIVED, NOT ASSUMED: a vehicle cost is paid once, and at occupancy 1.35 charging both occupants would make aggregate vehicle operating cost 1.35x the real one (DECISIONS.md 9.8). The earlier half-of-car was typed in and double-charged. CAUTION: with ride at zero and no driver-availability constraint, ride is cheaper than car on any trip long enough for the distance term to exceed the 0.85 ASC gap - about 4.7 km. That asymmetry is real and is why the constant must be constrained rather than left to absorb it.

***derived** · status **active** · DECISIONS.md §9.8 · MATSim `scoring.modeParams[*].monetaryDistanceRate`*

> **Sweep basis.** applies to the car entry only; the others are derived and not free

#### `C.scoring.performing_utils_per_h`

Marginal utility of performing an activity. A property of the MATSim scoring formulation, not an observable quantity of Newcastle. The effective cost of travel time is performing plus the absolute marginalUtilityOfTraveling, which is how the 16.96 AUD/h VOT is reproduced: 6.0 + 10.9608.

***literature** · status **active** · DECISIONS.md §9.3 · MATSim `scoring.performing`*

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

#### `C.transfer.beta_transfer_penalty_min`

Behavioural penalty for an interchange, ON TOP of the measured Newcastle Interchange walk time (mean 112 s, max 284 s over 51 stop pairs). The whole policy question is whether forcing a transfer at Wickham is worth the CBD distribution it buys: 5 min gives a broadly favourable result, 12 min a net disbenefit for external origins. NO HEADLINE MAY BE REPORTED AT A SINGLE VALUE. It is assumed rather than estimated only because journey-linked Opal is unobtained.

***assumed** · status **active** · DECISIONS.md §8.1 · proposal §6.2, 3.4 S-d*

> **Sweep basis.** proposal 6.2 forbids a literature default and requires every finding to be reported as a curve across this range; the grid crosses 3, 5, 6.5, 8, 10, 12, 15

#### `C.vot.by_purpose`

Value of travel time by trip purpose, ATAP PV2 / TfNSW Economic Parameter Values conventions. NOT a Newcastle measurement. MATSim scoring cannot carry per-purpose VOT, so the run inputs collapse this to a trip-weighted 16.96 AUD/h - see C.vot.trip_weighted and DECISIONS.md 9.3.

***literature** · status **active** · DECISIONS.md §8.3 · proposal §A/C1, 6.2*

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

## Land use (D1)

*`config/registry/D_landuse.json` - 5 fields*

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

*`config/registry/E_scenario.json` - 6 fields*

The scenario matrix and the coupling controls. Per-scenario variant references stay in scenarios/S*.json, which bind a scenario to its network, schedule, land use, parking, signals, demand and parameter sets; this layer holds the values those configs share.

| Field | Value | Units | Provenance | Sweep |
|---|---|---|---|---|
| `E.coupling.outer_loop_tolerance_s` | *(null - unobtained)* | seconds | `assumed` | 5 - 60 |
| `E.matrix.base_year` | `2026` | year | `definition` | - |
| `E.matrix.crs` | `EPSG:28356` | enum | `definition` | - |
| `E.matrix.day_types` | `["WEEKDAY", "SAT", "SUN"]` | enum | `definition` | - |
| `E.matrix.scenario_ids` | `["S0", "S1", "S2", "S2a", "S2b", "S2c", "S3", "S4", "S5", "S6"]` | enum | `definition` | - |
| `E.replication.n_replications` | `30` | count | `definition` | 5 - 30 |

#### `E.coupling.outer_loop_tolerance_s`

Corridor run-time stability tolerance for the MATSim-SUMO outer loop. Proposal 5.2 defers this explicitly - run the loop 'until the corridor run time is stable within a tolerance TO BE DEFINED AT CALIBRATION'. IT HAS NOT BEEN DEFINED. This is a P4 obligation that appeared on no deliverable list until issue 8. Registered with a null value so it cannot be silently assumed by whoever builds the loop.

***assumed** · status **unobtained** · DECISIONS.md §15 · proposal §5.2*

#### `E.matrix.base_year`

Base year, using 2021 Census marginals with HTS 2024/25 behaviour.

***definition** · status **active** · DECISIONS.md §1*

#### `E.matrix.crs`

GDA94 / MGA Zone 56, metres. The proposal label GDA2020 was corrected.

***definition** · status **active** · DECISIONS.md §2.6*

#### `E.matrix.day_types`

Full weekend day types are built, not a weekday-only model with a note. Beach and event demand is arguably this system strongest use case and excluding it would bias against the light rail (DECISIONS.md 1 item 5).

***definition** · status **active** · DECISIONS.md §1*

#### `E.matrix.scenario_ids`

The scenario matrix, fixed at P0. S2 vs S0 is the headline test, S2 vs S3 the value-for-money test, S2 vs S4/S5 the trunk-length test.

***definition** · status **active** · DECISIONS.md §1 · proposal §4.3*

#### `E.replication.n_replications`

Seeded replications per scenario. One of the three things that can be cut to close the run-budget gap - the others being sweep breadth and day types. Sample fraction is the WEAKEST lever because cost is sublinear in it.

***definition** · status **active** · DECISIONS.md §1*

> **Sweep basis.** proposal 5.2 specifies at least 30 SUMO replications; the sweep records that cutting replications is one of the three levers on the run budget

## Execution control

*`config/registry/RUN_execution.json` - 26 fields*

Everything that governs a run rather than the model it runs. Two fields here were previously set in code with no rationale and no sweep - RUN.sample.flow_capacity_factor and RUN.sample.storage_capacity_exponent - which is the exact breach of proposal 8.1 that check_package.py exists to catch. RUN.controler.last_iteration carries a null value because no justified value has been measured; the resolver will not invent one.

| Field | Value | Units | Provenance | Sweep |
|---|---|---|---|---|
| `RUN.controler.compression_type` | `gzip` | enum | `definition` | - |
| `RUN.controler.first_iteration` | `0` | iterations | `definition` | - |
| `RUN.controler.last_iteration` | *(null - unobtained)* | iterations | `assumed` | 250 - 2000 |
| `RUN.controler.write_events_interval` | `10` | iterations | `definition` | - |
| `RUN.controler.write_plans_interval` | `10` | iterations | `definition` | - |
| `RUN.machine.seed` | `20260810` | integer_seed | `definition` | - |
| `RUN.machine.threads` | `10` | threads | `definition` | 1 - 24 |
| `RUN.machine.xmx` | `14g` | jvm_heap | `definition` | - |
| `RUN.mode_choice.chain_based_modes` | `["car", "bike"]` | enum | `definition` | - |
| `RUN.mode_choice.consider_car_availability` | `true` | boolean | `definition` | - |
| `RUN.mode_choice.modes` | `["car", "ride", "pt", "bike", "walk"]` | enum | `definition` | - |
| `RUN.qsim.end_time_h` | `30` | hours | `definition` | - |
| `RUN.qsim.main_mode` | `car` | enum | `definition` | - |
| `RUN.qsim.start_time_h` | `0` | hours | `definition` | - |
| `RUN.replanning.fraction_to_disable_innovation` | `0.8` | share_of_iterations | `literature` | 0.7 - 0.9 |
| `RUN.replanning.max_agent_plan_memory` | `5` | plans | `literature` | 3 - 10 |
| `RUN.replanning.weights` | `{"ChangeExpBeta": 0.7, "ReRoute": 0.15, "SubtourModeChoice": 0.1, "TimeAllocationMutator": 0.05}` | strategy_weight | `literature` | plus/minus 50% |
| `RUN.routing.beeline_distance_factor` | `1.3` | ratio | `assumed` | 1.2 - 1.45 |
| `RUN.routing.network_modes` | `["car", "ride"]` | enum | `definition` | - |
| `RUN.routing.teleported_bike_speed_ms` | `4.2` | metres_per_second | `literature` | 3.5 - 5.5 |
| `RUN.routing.teleported_walk_speed_ms` | `1.05` | metres_per_second | `literature` | 0.9 - 1.35 |
| `RUN.sample.flow_capacity_factor` | *(null - unobtained)* | share_of_capacity | `derived` | derived: flowCapacityFactor = RUN.sample.fraction, the standard MATSim scaling  |
| `RUN.sample.fraction` | `0.01` | share_of_population | `assumed` | 0.01 - 0.4 |
| `RUN.sample.storage_capacity_exponent` | `1.0` | exponent | `derived` | derived: storageCapacityFactor = fraction ** 1.0 = flowCapacityFactor. MATSim e |
| `RUN.sample.transit_capacity_floor` | `1` | seats | `assumed` | 1 - 4 |
| `RUN.sample.transit_capacity_scaling` | `true` | boolean | `derived` | derived: seats = max(floor, round(seats x RUN.sample.fraction)); not scaling it |

#### `RUN.controler.compression_type`

Output compression. MUST be gzip: runs made before this was set write .zst, which extract_metrics.py can only read if zstandard happens to be installed, and the repo does not require it.

***definition** · status **active** · DECISIONS.md §15 · MATSim `controler.compressionType`*

#### `RUN.controler.first_iteration`

Start iteration.

***definition** · status **active** · DECISIONS.md §15 · MATSim `controler.firstIteration`*

#### `RUN.controler.last_iteration`

Iterations to relaxation. NO JUSTIFIED VALUE HAS BEEN MEASURED. Two 1% runs of 250 iterations showed the model had NOT converged: innovation switches off at iteration 200 and ride still moved 0.619 to 0.664 over the last 50 iterations with no new plans being created. The shipped scenario configs carry 100, which is known wrong and left in place rather than replaced by another unjustified number; run_matsim.py deliberately gives --iterations NO DEFAULT. Everything downstream needs this number (issue 5).

***assumed** · status **unobtained** · DECISIONS.md §9.7, 15 · MATSim `controler.lastIteration`*

#### `RUN.controler.write_events_interval`

How often events are written. Affects disk and wall time, not the model.

***definition** · status **active** · DECISIONS.md §15 · MATSim `controler.writeEventsInterval`*

#### `RUN.controler.write_plans_interval`

How often plans are written. Affects disk and wall time, not the model.

***definition** · status **active** · DECISIONS.md §15 · MATSim `controler.writePlansInterval`*

#### `RUN.machine.seed`

MATSim random seed. Held at the master seed unless replications are being drawn.

***definition** · status **active** · DECISIONS.md §9.7 · MATSim `global.randomSeed`*

#### `RUN.machine.threads`

Mobsim thread count. PART OF THE RUN IDENTITY, NOT A PERFORMANCE KNOB: MATSim partitions the network by thread count, so changing it changes results.

***definition** · status **active** · DECISIONS.md §9.5*

#### `RUN.machine.xmx`

JVM heap. Must exceed 9.6 GiB + 87 GiB x fraction or the run dies.

***definition** · status **active** · DECISIONS.md §9.5*

#### `RUN.mode_choice.chain_based_modes`

Modes whose vehicle must return home, so a tour cannot abandon it mid-chain.

***definition** · status **active** · DECISIONS.md §9.6 · MATSim `subtourModeChoice.chainBasedModes`*

#### `RUN.mode_choice.consider_car_availability`

MATSim defaults this to FALSE, which made mode choice ignore the car availability B1 synthesised. Must stay true.

***definition** · status **active** · DECISIONS.md §9.6 · MATSim `subtourModeChoice.considerCarAvailability`*

#### `RUN.mode_choice.modes`

Modes subtour mode choice may switch between. IF RIDE IS OMITTED, MATSim defaults to car,pt,bike,walk and a ride subtour becomes an ABSORBING STATE - ride sat at 0.18311 in every iteration to five decimals, and 18.6% of legs were an input wearing the costume of a result.

***definition** · status **active** · DECISIONS.md §9.6 · MATSim `subtourModeChoice.modes`*

#### `RUN.qsim.end_time_h`

Mobsim end. Matches B.activity.day_horizon_h; a 30-hour day catches after-midnight returns.

***definition** · status **active** · DECISIONS.md §15 · MATSim `qsim.endTime`*

#### `RUN.qsim.main_mode`

The only mode physically simulated in the mobsim. A car passenger is not a second vehicle, so ride is routed on the road network and reads car travel times but consumes NO ROAD CAPACITY. One of five modes is in the mobsim.

***definition** · status **active** · DECISIONS.md §9.6 · MATSim `qsim.mainMode`*

#### `RUN.qsim.start_time_h`

Mobsim start.

***definition** · status **active** · DECISIONS.md §15 · MATSim `qsim.startTime`*

#### `RUN.replanning.fraction_to_disable_innovation`

Share of iterations after which no new plans are created. At 250 iterations innovation stopped at 200 and mode share was still moving, which is how the non-convergence was identified.

***literature** · status **active** · DECISIONS.md §9.7 · MATSim `replanning.fractionOfIterationsToDisableInnovation`*

#### `RUN.replanning.max_agent_plan_memory`

Plans retained per agent. A property of the MATSim formulation, not of Newcastle.

***literature** · status **active** · DECISIONS.md §9.3 · MATSim `replanning.maxAgentPlanMemorySize`*

#### `RUN.replanning.weights`

Replanning strategy weights, applied to both the person and external subpopulations. Properties of the scoring formulation, not observable quantities of Newcastle.

***literature** · status **active** · DECISIONS.md §9.3 · MATSim `replanning.strategysettings[*].weight`*

#### `RUN.routing.beeline_distance_factor`

Straight-line to path distance for teleported modes. Note B.activity.detour_factor is the MEASURED equivalent for the road graph, 1.3376; this one applies to walk and bike and has not been measured on the active network.

***assumed** · status **active** · DECISIONS.md §15 · MATSim `routing.teleportedModeParameters[*].beelineDistanceFactor`*

#### `RUN.routing.network_modes`

Modes routed on the road graph. Ride must be here AND permitted on the links (143,891 of them): declaring it a network mode that no link permits gives 'checking 0 nodes and 0 links' and a throw in PrepareForSim.

***definition** · status **active** · DECISIONS.md §9.6 · MATSim `routing.networkModes`*

#### `RUN.routing.teleported_bike_speed_ms`

Teleported bike speed in MATSim.

***literature** · status **active** · DECISIONS.md §15 · MATSim `routing.teleportedModeParameters[bike].teleportedModeSpeed`*

#### `RUN.routing.teleported_walk_speed_ms`

Teleported walk speed in MATSim. Distinct from A.transit.walk_speed_ms (1.25), which generates GTFS transfer times. Walk is immune to network conditions, which matters when diagnosing where agents flee to.

***literature** · status **active** · DECISIONS.md §15 · MATSim `routing.teleportedModeParameters[walk].teleportedModeSpeed`*

#### `RUN.sample.flow_capacity_factor`

Road flow capacity scaled to the sample. DERIVED: equals RUN.sample.fraction exactly, which is the standard MATSim rule and is not a free choice. Set by the harness at run time. NOTE the SHIPPED scenario config carries 1.0, so running scenarios/matsim/<S>/<DAY>/config.xml DIRECTLY simulates a sampled demand against full supply - the harness must be used.

***derived** · status **computed** · DECISIONS.md §15 · MATSim `qsim.flowCapacityFactor`*

> **Derived from** `RUN.sample.fraction`: flowCapacityFactor = RUN.sample.fraction, the standard MATSim scaling rule

#### `RUN.sample.fraction`

Share of the synthetic population simulated. The subsample is NESTED - a person is kept if a hash of their id falls below the fraction, so 1% is a strict subset of 10% and a difference between fractions is a sample-size effect rather than a sampling one. EVERY P4 BEHAVIOURAL RESULT SO FAR WAS MEASURED AT 1% (5,209 persons, 0.85% of the population).

***assumed** · status **active** · DECISIONS.md §9.5, 15*

> **Sweep basis.** measured: 9.8 s/iteration and 9.8 GiB at 1%, 29.9 s and 18.4 GiB at 10%, ~64 s and 31.5 GiB at 25%. time = 3.1 s + 268 s x fraction, memory = 9.6 + 87 GiB x fraction, so 100% needs ~97 GiB and DOES NOT FIT in 63.5 GiB. The upper bound is the machine ceiling, not a modelling judgement

#### `RUN.sample.storage_capacity_exponent`

The exponent relating storage capacity to the sample fraction. IT IS 1.0 AND IT IS NOT FREE. An earlier revision of this registry declared it assumed with a 0.75-1.0 sweep, on the reasoning that MATSim floors link storage at one vehicle so a 1% sample would produce spurious spillback, and that raising storage relative to flow is the usual treatment. That reasoning is superseded. MATSim rejects any value below 1.0 outright and states the reason: 'the old approach of setting the stor cap fact larger than the flow cap fact is no longer needed since the qsim became a lot more deterministic'. The sweep was therefore a range whose members the tool will not accept, which is exactly the undisciplined declaration this registry exists to prevent. Corrected after the diagnostic run that tried to use it failed in one second. The remaining question - whether behaviour moves with the SAMPLE FRACTION itself - is unaffected and is what the 1% versus 10% arms test.

***derived** · status **active** · DECISIONS.md §15 · MATSim `qsim.storageCapacityFactor`*

> **Derived from** `RUN.sample.fraction`: storageCapacityFactor = fraction ** 1.0 = flowCapacityFactor. MATSim enforces the equality: GlobalConfigGroup.checkConsistency throws when the two differ by more than global.relativeTolerance, which defaults to 0.0

#### `RUN.sample.transit_capacity_floor`

Minimum seats after scaling, so a vehicle never becomes unusable. Capacity floors at 1 seat below about a 1.5% sample, which makes capacity systematically too generous at small fractions. Acceptable while crowding scoring is off; revisit if it is enabled (issue 12).

***assumed** · status **active** · DECISIONS.md §15*

#### `RUN.sample.transit_capacity_scaling`

Scale transit vehicle seats by the sample fraction. NOT OPTIONAL in practice: at a 10% sample an unscaled bus carries 70 sampled agents, i.e. 700 real ones, so capacity never binds and crowding silently disappears.

***derived** · status **active** · DECISIONS.md §15*

> **Derived from** `RUN.sample.fraction`: seats = max(floor, round(seats x RUN.sample.fraction)); not scaling it would give every vehicle 1/fraction times its real capacity

## SUMO corridor (build and microsimulation)

*`config/registry/RUN_sumo.json` - 17 fields*

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
