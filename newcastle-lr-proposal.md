# Testing the Integration Claim

## A counterfactual microsimulation of the Newcastle Light Rail as a transport intervention

**Status:** Proposal — v1, for review
**Date:** August 2026
**Working title:** Project Wickham

---

## 1. Summary

In 2018 the NSW Auditor-General found that the business case for the Newcastle Light Rail was prepared after the decision to build it had been announced, that the analysis relied on international comparators materially unlike Newcastle, and that the project's transport benefits were expected to be small — with journey times and interchange counts increasing for travellers originating outside the city centre.

The delivery agencies nonetheless described the system as the centrepiece of an integrated transport network, and as a means of delivering customers directly to the door of city-centre businesses.

Neither claim has been tested against a constructed counterfactual. Observed patronage cannot settle the question, because the corridor was altered five times in six years — heavy rail truncation, bus franchise redesign, interchange opening, light rail opening, and the pandemic — and no published analysis separates these effects.

This project builds an agent-based and microscopic simulation of the Greater Newcastle transport network, holds land use and the bus network fixed at a common base year, and varies only the central-city trunk mode. It produces a defensible estimate of what the light rail did to journey cost, accessibility, mode share and city-centre footfall, relative to the alternatives that were available in 2013.

The intended output is a reproducible model, an open data package, and a paper.

---

## 2. Why this is worth doing

Three reasons, in descending order of general interest.

**It is a rare case of a clean natural experiment that was never analysed.** A trunk rail corridor was severed and replaced with a shorter surface mode on a partially different alignment, in a mid-sized city, with a defined before and after. Most light rail evaluations compare a corridor to itself over time and inherit every confounder going. Newcastle offers a genuine mode-substitution question with an identifiable counterfactual.

**The scale question is open and generalisable.** The interesting hypothesis is not "light rail is wrong for Newcastle." It is that a 2.7 km trunk sits below the threshold at which a trunk mode produces network effects at all — that there is a minimum viable length for the integration claim, below which a light rail line functions as a distributor and cannot produce the accessibility gains that justify its cost. If that threshold can be estimated, it transfers directly to every mid-sized city considering a starter line, including the proposed Broadmeadow extension.

**The evaluation gap is itself a finding.** The Auditor-General noted that the program's benefits management plan was written in 2014 and never used in implementation, that no funding was allocated to assess whether objectives were achieved, and that separating light rail's contribution from concurrent urban renewal would be very difficult. This project demonstrates that the separation is tractable with open data and public tooling — which is a governance argument as much as a transport one.

---

## 3. Research questions and hypotheses

### 3.1 Primary question

Relative to the feasible alternatives available in 2013, what was the effect of the Newcastle Light Rail on the generalised cost of travel, on accessibility to employment and services, on public transport mode share, and on arrivals at city-centre retail frontages?

### 3.2 Claim A — "centrepiece of an integrated transport network"

| ID | Hypothesis | Primary metric | Falsification condition |
|---|---|---|---|
| A1 | LR carries a structurally significant share of regional PT | LR person-legs ÷ total PT person-legs, Greater Newcastle | Share below ~10% indicates a distributor, not a trunk |
| A2 | LR functions as a trunk rather than a shuttle | Transfer intensity: share of LR legs that are non-terminal legs of a multi-leg journey; mean legs per PT journey | Legs/journey rises while GJT also rises → shuttle, not trunk |
| A3 | Door-to-door journey cost falls | Δ demand-weighted GJT by OD pair vs counterfactual S0 | GJT rises for external-origin OD pairs |
| A4 | Accessibility rises | Hansen accessibility per SA1: jobs and services reachable within 30 / 45 min by PT | No significant change outside a narrow CBD band |
| A5 | Mode shift is genuine, not reshuffled | Decomposition of LR boardings into diverted-from-car, diverted-from-bus, re-routed heavy rail, diverted-from-walk, induced | Car-diverted share below ~15% |
| A6 | LR occupies a central position in the network graph | Betweenness centrality of LR edges in the demand-weighted PT graph; passenger-km load profile | High degree at one node, low betweenness → stub |

### 3.3 Claim B — "delivers customers directly to the door of businesses"

| ID | Hypothesis | Primary metric | Falsification condition |
|---|---|---|---|
| B1 | Frontage exposure rises | Modelled pedestrian throughput per 50 m Hunter St frontage segment, by hour | No increase net of baseline pedestrian flow |
| B2 | Retail catchment expands | Population reachable within 15 / 30 min PT of each frontage, weighted by floorspace | Catchment unchanged or contracts |
| B3 | **Net arrivals rise across all modes** | Δ total arrivals at CBD retail frontages by every mode combined | LR-borne arrivals are offset or exceeded by suppressed car and bus arrivals |
| B4 | Activity is generated, not displaced | Spatial distribution of arrivals: Hunter St vs Darby St vs Honeysuckle vs Newcastle East | Gains on the corridor are matched by losses off it |

**B3 is the decisive test of Claim B and the one most likely to be neglected.** The Auditor-General recorded that the chosen route produced higher road impacts, increased travel times and reduced space for active transport. A simulation that models the tram without modelling the lane loss, banned turning movements, kerbside parking removal and signal cycle changes on Hunter Street will report a spurious gain. The road-space externality must be present in the same model run.

### 3.4 Secondary questions

- **S-a. What is the marginal cost of the wire-free decision?** Charging dwell was introduced with a late $35m urban amenity package. Isolate its contribution to end-to-end run time and to modelled patronage.
- **S-b. What would transit signal priority have been worth?** Quantify the run-time and reliability gain from full TSP on the Hunter/Scott corridor.
- **S-c. What is the minimum viable trunk length?** Sweep corridor length from 2.7 km through the Broadmeadow extension and beyond, and identify where accessibility and mode-shift metrics become non-marginal.
- **S-d. How sensitive is the whole result to the transfer penalty?** Report every headline finding as a curve across the plausible transfer-penalty range rather than a point estimate.

---

## 4. Identification strategy

### 4.1 The problem with before-and-after

At least six changes occurred in the study window:

| Date | Change |
|---|---|
| Dec 2014 | Heavy rail truncated at Hamilton, then Wickham |
| Jul 2017 | Keolis Downer franchise begins; the bus network is comprehensively redesigned |
| Oct 2017 | Newcastle Interchange opens |
| Feb 2019 | Light rail opens |
| Mar 2020 | Pandemic; sustained change in travel demand and work location |
| 2015–2026 | CBD land use transformation: university campus, residential and commercial development on former railway land |

Any observed change in patronage, mode share or footfall over this window is jointly caused. Attributing it to the light rail is the same inferential error the Auditor-General identified when transport policy documents credited the light rail with triggering the court house, the interchange and the university campus — investments that respectively pre-dated the announcement, were necessitated by the closure decision itself, and were contracted three months after the announcement.

### 4.2 The design

**Fix a base year. Hold land use, bus network, population and behavioural parameters constant. Vary only the central-city trunk mode.**

The comparison is not 2013 against 2026. It is: given the city as it exists in the base year, what would each candidate trunk mode deliver?

This isolates the intervention from concurrent urban renewal, from the franchise redesign, and from the pandemic. It sacrifices the ability to claim a realised historical effect and gains the ability to claim a causal one.

**Base year:** 2026, subject to Census release timing (see §7.3).

### 4.3 Scenario matrix

| ID | Trunk mode | Purpose |
|---|---|---|
| **S0** | Heavy rail retained to Newcastle station | Primary counterfactual: the line is not cut |
| **S1** | Bus shuttle from Wickham, no LR | The December 2012 policy as originally announced |
| **S2** | **Light rail as built** — wire-free, current signal arrangement | Actual |
| S2a | Light rail, charging dwell removed | Isolates the wire-free decision (S-a) |
| S2b | Light rail with full TSP | Isolates signal priority (S-b) |
| S2c | Light rail on the Option A alignment (former railway land) | The route with plurality public support that was not selected |
| **S3** | Bus rapid transit on the same alignment | The alternative the 2020 Strategic Business Case later favoured |
| S4 | Light rail extended to Broadmeadow | Trunk-length hypothesis (S-c) |
| S5 | Light rail extended to Broadmeadow and John Hunter Hospital | Upper bound of the plausible network |
| S6 | No trunk mode; walk, cycle and local bus only | Lower bound |

S2 vs S0 is the headline test. S2 vs S3 is the value-for-money test. S2 vs S4/S5 tests whether underperformance is attributable to mode choice or to corridor length — the most transferable finding available.

All scenarios share: identical land use, identical population, identical behavioural parameters, identical non-CBD bus network, identical parking supply except where the trunk mode physically requires change.

---

## 5. Method and architecture

### 5.1 Tool allocation

The claims decompose across two layers, and no single tool spans both.

| Layer | Question | Tool |
|---|---|---|
| Demand and behaviour | Does anyone ride it? How do journeys restructure? What happens to accessibility? | **MATSim** — activity-based, co-evolutionary utility scoring, native intermodal legs and transfer disutility |
| Supply and operations | Given riders, how does the system physically perform? What does it cost other road users? | **SUMO** — microscopic, signal-accurate, dwell-explicit |

MATSim alone will under-represent signal interaction, charging dwell and the road-capacity externality on Hunter Street. SUMO alone cannot answer whether anyone chooses to ride, because its demand is exogenous — feed it 3,000 tram passengers and it will faithfully return 3,000 tram passengers.

### 5.2 Coupling

```
OSM (Osmium extract + filter)
   │
   ├──► pt2matsim ──► MATSim network + transit schedule
   │                       │
   │                       ▼
   │              MATSim run (scenario k, N iterations to relaxation)
   │                       │
   │                       ├──► accessibility, mode share, GJT skims
   │                       │
   │                       ▼
   │              Corridor demand profile (boardings, alightings,
   │                       turning movements, ped flows)
   │                       │
   └──► netconvert ──► SUMO corridor network ◄───────┘
                           │
                           ▼
              SUMO microsimulation, ≥30 seeded replications
                           │
                           ▼
              Observed run time, dwell, reliability variance,
              car delay, ped delay, frontage throughput
                           │
                           ▼
              Revised LOS parameters ──► back to MATSim
                    (2–3 outer iterations to convergence)
```

The outer loop matters. If SUMO shows the corridor run time is 20% worse than the MATSim schedule assumed, that changes mode choice, which changes corridor demand, which changes dwell time, which changes run time. Run the loop until the corridor run time is stable within a tolerance to be defined at calibration.

### 5.3 Scope boundaries

**In scope:** Greater Newcastle — Newcastle, Lake Macquarie, and the Maitland/Cessnock corridor to the extent needed to represent Hunter Line demand. Full 24-hour day, weekday and weekend day types.

**Out of scope:** freight, the Port, long-distance intercity travel beyond a boundary treatment at Fassifern/Maitland, and land-use response. Land use is held fixed by design; endogenous land-use feedback would reintroduce the confounding the design exists to remove.

---

## 6. Data requirements

Full field-level schemas are in Appendix A. This section states what is needed and how hard it is to get.

### 6.1 Layer summary

| Layer | Contents | Criticality |
|---|---|---|
| **A. Network supply** | Road graph, signal control, GTFS across four eras, LR vehicle and dwell model, parking, active-transport graph with gradient | Signal timings and charging dwell are the two highest-leverage unknowns |
| **B. Demand** | Synthetic population, activity/trip records, OD matrices, journey-linked Opal, traffic and pedestrian counts | Journey-linked Opal is the difference between a good model and a guess |
| **C. Behavioural parameters** | VOT, IVT/wait/walk weights, transfer penalty, reliability weighting, crowding, mode-choice coefficients and ASCs | **This layer decides the answer.** See §6.3 |
| **D. Land use** | Frontage-level retail floorspace and business counts, employment by DZN, dwellings by SA1, POI, all year-stamped | Year-stamping is non-negotiable |
| **E. Scenario config** | Variant references binding each scenario to its network, schedule, land use, parking, signals, demand and parameter sets | Reproducibility depends entirely on this |

### 6.2 Three fields that carry disproportionate weight

**`dwell_charging_s` — per-stop supercapacitor charging dwell.** Not published. If charging adds roughly twenty seconds at each of six stops, that is approximately two minutes on a ten-minute run: a run-time penalty of around twenty per cent attributable entirely to a late amenity decision. Model it as a separate additive term so it can be toggled independently of boarding dwell. Acquisition: field measurement, or inference from GTFS-Realtime dwell distributions.

**`tsp_enabled` and SCATS phase data.** Whether and how Hunter Street signals give the tram priority determines corridor run time more than any other single input. Requires a formal data request to TfNSW. Without it the model rests on an assumption that drives the headline result — which must then be stated prominently and swept.

**`beta_transfer_penalty_min`.** The entire policy question is whether forcing an interchange at Wickham is worth the CBD distribution it buys. A five-minute-equivalent penalty produces a broadly favourable result; a twelve-minute penalty produces a net disbenefit for external origins. Literature defaults must not be used. Estimate from Newcastle Household Travel Survey and Opal data, and report every finding as a curve across the plausible range.

### 6.3 A note on walk access

Access should be modelled as a distance-decay function — negative exponential or cumulative Gaussian — not a threshold. A 400 m cut-off treats a person at 401 m as identical to one at 2 km and systematically flatters fixed-route modes. Gradient must be attached per footway edge from a DEM and treated asymmetrically; uphill and downhill are different costs, and this is material in Newcastle East and The Hill.

### 6.4 Known data hazards

- **Opal series break.** TfNSW changed the line-level trip calculation methodology on 1 July 2024 and states that aggregations between line, agency and mode levels are no longer valid, because one passenger may use several lines in a journey. Any time series crossing that date requires an explicit break flag.
- **Opal Patronage start date.** The dataset begins January 2020 — two months before the pandemic. There is effectively no clean post-opening, pre-pandemic baseline in the public data.
- **Census contamination.** 2011 JTW captures the heavy rail era; 2016 captures the bus-replacement interregnum; 2021 is heavily distorted by lockdown and work-from-home. **The August 2026 Census is the first clean post-light-rail journey-to-work observation** and is being collected now. This drives the base-year decision.
- **Historic GTFS.** Pre-2015 timetables may exist only as PDFs. Budget for manual reconstruction.
- **OSM completeness.** Lane counts, turn restrictions and kerbside use are unreliable in Newcastle. Manual correction from aerial imagery is typically thirty to forty per cent of network-build effort and directly determines car-delay results.

---

## 7. Work plan

### 7.1 Phases

| Phase | Work | Output | Indicative duration |
|---|---|---|---|
| **P0. Scoping** | Confirm base year, zone system, scenario list; register data requests | Signed-off scope; requests lodged | 2 weeks |
| **P1. Data acquisition** | Open data harvest; formal requests to TfNSW and City of Newcastle; field measurement of dwell | Raw data lake, provenance-tagged | 6–10 weeks, gated by request turnaround |
| **P2. Network build** | OSM extraction and correction; MATSim and SUMO network generation; GTFS era variants | Validated networks, all scenarios | 6 weeks |
| **P3. Demand synthesis** | Population synthesis; activity generation; OD estimation | Synthetic population and plans | 6 weeks |
| **P4. Calibration** | Fit to observed counts, Opal boardings, run times; parameter estimation | Calibrated base; calibration report | 4 weeks |
| **P5. Scenario runs** | All scenarios; replications; outer-loop convergence | Result set | 3 weeks |
| **P6. Analysis** | Metric computation; sensitivity sweeps; decomposition | Findings | 4 weeks |
| **P7. Write-up** | Paper, model release, data package | Publication and repository | 4 weeks |

P1 runs in parallel with P2 wherever possible; the formal data requests are the critical path.

### 7.2 Fallback if data requests fail

The project must remain viable if SCATS and journey-linked Opal are refused. Contingencies:

- **No SCATS:** infer effective signal delay from GTFS-Realtime run-time distributions; treat cycle time and priority as swept parameters rather than fixed inputs; state the resulting uncertainty band explicitly in all headline figures.
- **No journey-linked Opal:** estimate transfer rates from tap-on/tap-off timing at the Interchange using aggregate stop-level data plus a matching model; validate against the published interchange percentages.
- **No pedestrian counts:** deploy temporary counters at a small number of Hunter Street frontage segments; calibrate the remainder from land use and modelled alightings.

### 7.3 Base-year decision

Provisionally 2026, pending Census release. 2026 JTW is the first uncontaminated post-opening observation, but first release is unlikely before mid-2027. Options: proceed on a 2024 base with 2021 JTW corrected for work-from-home, then re-run on 2026 data when available; or delay P3 until release. Recommend the former, with the re-run scheduled as a validation exercise.

---

## 8. Deliverables

1. **Reproducible model** — MATSim and SUMO scenarios, version-controlled, containerised, seeded.
2. **Open data package** — every derived input, with provenance, licence status and processing lineage.
3. **Calibration report** — fit statistics against all validation targets, with honest reporting of where fit is poor.
4. **Findings paper** — targeting a transport policy or transport modelling venue.
5. **Interactive result explorer** — accessibility surfaces and corridor metrics per scenario, browsable.
6. **Method note on evaluation gaps** — the governance argument: that ex-post evaluation of this kind is tractable with open data and public tooling, and that its absence is a choice.

### 8.1 Repository structure

```
newcastle-lr/
├── README.md
├── PROPOSAL.md                 # this document
├── DECISIONS.md                # decision log — every modelling choice, with rationale
├── data/
│   ├── raw/                    # immutable, provenance-tagged
│   ├── interim/
│   └── processed/
├── networks/
│   ├── osm/
│   ├── matsim/
│   └── sumo/
├── schedules/                  # GTFS variants, one per era and scenario
├── demand/
│   ├── population/
│   └── plans/
├── params/                     # behavioural parameter sets, versioned
├── scenarios/                  # S0–S6 configs, each binding variant refs
├── src/
│   ├── extract/
│   ├── build/
│   ├── calibrate/
│   ├── run/
│   └── analyse/
├── results/
├── docs/
└── tests/
```

`DECISIONS.md` is not optional. Every parameter chosen without direct empirical support must be recorded there with its rationale and its sweep range. The credibility of this project rests on being more transparent about its assumptions than the business case it examines.

---

## 9. Threats to validity

| Threat | Mitigation |
|---|---|
| **ASC absorption** — calibrating mode constants to observed 2019 patronage fits away the effect under test | Estimate ASCs on the pre-intervention period and hold fixed; or constrain them and report the constraint |
| **Corridor tunnel vision** — modelling the tram without the road-space externality | Lane loss, banned turns, kerbside removal and signal cycle changes present in the same run; B3 as a mandatory reported metric |
| **Parameter-driven conclusions** — the transfer penalty and walk decay determine the sign of the result | Full sensitivity sweep; findings reported as curves; no point-estimate headline claims |
| **Counterfactual naivety** — assuming the retained heavy rail would have performed as it did in 2014 | Model S0 with realistic frequency and a modernised interchange, not the 2014 service as-is |
| **Land-use endogeneity** — holding land use fixed understates any genuine LR-induced development | Stated as a deliberate scope boundary; addressed in discussion, not in the model |
| **Overfitting to Opal** | Hold out validation targets; report fit on unseen counts |
| **Advocacy drift** | Pre-register hypotheses and falsification conditions in this document before any scenario is run. §3 is the pre-registration |

The last one deserves emphasis. This project examines a decision that has attracted strong local feeling for over a decade. Its value depends entirely on being able to publish a result that vindicates the light rail as readily as one that does not. The falsification conditions in §3 are fixed as of this document, and any change to them after results are seen must be recorded in `DECISIONS.md` with reasoning.

---

## 10. Open decisions

Items requiring a call before P1 begins:

1. **Base year** — 2024 with re-run, or wait for 2026 Census? (§7.3; recommend the former)
2. **Zone system granularity** — SA1 throughout, or SA1 in the corridor and SA2 beyond?
3. **Study area boundary** — where to cut the Hunter Line: Maitland, Singleton, or Fassifern?
4. **Scenario list** — is S2c (the unselected Option A alignment) worth the build cost, or is it a curiosity?
5. **Weekend modelling** — full weekend day type, or weekday only with a weekend sensitivity note? Beach and event demand is a real part of this system's use case and arguably its strongest.
6. **Event demand** — model major event peaks separately? The system's operator cites event movement as a core benefit, and it is the one use case where a 2.7 km line plausibly outperforms buses.
7. **Publication venue** — modelling venue, policy venue, or both?
8. **Data request strategy** — approach TfNSW as an independent research project, or seek a university affiliation to improve the odds on SCATS and journey-linked Opal?

---

## Appendix A — Field-level schemas

### A1. Road network

```
edge_id, from_node, to_node, geometry(LINESTRING, EPSG:28356),
num_lanes, lane_width_m, speed_limit_kmh, road_class,
oneway_flag, turn_restrictions[], gradient_pct,
kerbside_use(parking|loading|clearway|tram_lane|bus_lane),
time_of_day_restrictions[], capacity_veh_hr, scenario_variant_ref
```

### A2. Signal control

```
intersection_id, scats_site_id, control_type(fixed|actuated|adaptive),
cycle_time_s, phase_sequence[], phase_split_pct[], offset_s,
coordination_group, pedestrian_phase_flag, ped_clearance_s,
tsp_enabled(bool), tsp_type(green_extension|early_start|phase_insert),
tsp_detection_distance_m, tsp_max_extension_s, scenario_variant_ref
```

### A3. Public transport supply

Standard GTFS: `agency`, `routes`, `trips`, `stop_times`, `stops`, `calendar`, `calendar_dates`, `shapes`, `frequencies`, `transfers`.

Required extensions:

```
route_extras:  route_id, mode(bus|lr|heavy_rail|ferry), vehicle_type_id,
               contract_area, franchise_operator, valid_from, valid_to

stop_extras:   stop_id, platform_geom, shelter(bool), seating(bool),
               real_time_info(bool), step_free(bool), platform_height_mm,
               interchange_group_id

transfer_extras: from_stop, to_stop, walk_distance_m, walk_time_s,
               is_sheltered(bool), requires_road_crossing(bool),
               signalised_crossing_delay_s
```

Era variants required: pre-Dec 2014; 2015–Jul 2017; Jul 2017–Feb 2019; post-Feb 2019.

### A4. Light rail vehicle and dwell model

```
vehicle_spec:      model, length_m, capacity_seated, capacity_crush,
                   max_accel_ms2, max_decel_ms2, max_speed_kmh,
                   door_count, door_width_mm,
                   boarding_rate_pax_s, alighting_rate_pax_s

stop_dwell_model:  stop_id, dwell_fixed_s,
                   dwell_boarding_s = f(pax_boarding),
                   dwell_charging_s,
                   dwell_dist(mean, sd, distribution_type)

signal_interaction: stop_id, downstream_signal_id, distance_m,
                   departure_coordination(bool)
```

### A5. Parking

```
parking_facility_id, geom, type(onstreet|offstreet_public|offstreet_private),
capacity_spaces, price_schedule[], max_stay_min,
occupancy_by_hour[], walk_time_to_frontages_s, scenario_variant_ref
```

### A6. Active transport network

```
footway_edge_id, geometry, width_m, surface, gradient_pct,
lighting(bool), shade(bool),
crossing_type(signalised|zebra|unmarked|none), crossing_delay_s,
step_free(bool), tram_track_crossing(bool)
```

### B1. Synthetic population

```
person_id, household_id, home_sa1, age_band, sex, employment_status,
occupation_anzsco1, income_band, licence_holder(bool),
household_vehicles, household_size, dwelling_type,
student_status, mobility_impairment_flag, weight
```

### B2. Activity and trip records

```
person_id, trip_seq, purpose(HW|HE|HS|HO|WB|NHB),
origin_coord, dest_coord, dep_time_s, arr_time_s,
observed_mode, party_size, is_tour_anchor(bool),
activity_duration_s, time_flexibility_band
```

### B3. OD matrices (fallback)

```
origin_zone, dest_zone, period(AM|IP|PM|EV|WE), purpose, mode,
trips, source(census|hts|opal|modelled), confidence
```

### B4. Observed PT journeys

```
journey_id, card_type(adult|concession|student|senior|school),
legs[{mode, route_id, board_stop, board_time, alight_stop,
      alight_time, vehicle_id}],
transfer_times_s[], journey_gjt_s, date, daytype, methodology_epoch
```

`methodology_epoch` flags the 1 July 2024 series break.

### B5. Counts

```
count_site_id, geom, count_type(tube|loop|camera|manual|ped_sensor),
date, interval_min, direction, vehicle_class, volume,
turning_movement{from_approach, to_approach, volume}
```

### C1. Behavioural parameters

```
param_set_id, segment_id, purpose,
vot_aud_hr, beta_ivt(=1.0), beta_walk_access, beta_walk_egress,
beta_wait, beta_transfer_penalty_min, beta_headway,
beta_reliability, beta_crowding(load_factor), beta_cost,
asc_car, asc_bus, asc_lr, asc_rail, asc_walk, asc_cycle,
nesting_structure, walk_decay_function, walk_decay_params[],
source(estimated|literature|assumed), sweep_range_low, sweep_range_high
```

Every row with `source = assumed` must appear in `DECISIONS.md`.

### D1. Land use

```
frontage_segment_id, street_name, geom(50m segments), year,
retail_floorspace_m2, business_count, business_categories[],
vacancy_rate, active_frontage_pct, awning_coverage_pct

employment:  dzn_code, jobs_by_anzsic[], jobs_total, year
residential: sa1_code, dwellings, population, dwelling_type_mix, year
poi:         poi_id, geom, category, attraction_weight, year
```

### E1. Scenario configuration

```
scenario_id, label, base_year, is_counterfactual(bool), parent_scenario_id,
network_variant_ref, gtfs_variant_ref, landuse_variant_ref,
parking_variant_ref, signal_variant_ref, demand_variant_ref,
params_variant_ref, n_replications, seed_list[]
```

---

## Appendix B — Simulation outputs harvested

### SUMO

```
tripinfo:   duration, routeLength, waitingTime, timeLoss,
            departDelay, rerouteNo
personinfo: walk{depart, arrival, duration, routeLength, timeLoss}
            ride{waitingTime, vehicle, depart, arrival, routeLength}
stopinfo:   busStop, started, ended, delay,
            loadedPersons, unloadedPersons
edgeData:   edge_id, interval, sampledSeconds, density, occupancy,
            speed, waitingTime, timeLoss
```

### MATSim

```
events:         all agent events, full trace
trips.csv:      person, trip, mode, dep_time, trav_time, wait_time,
                traveled_distance, main_mode, start/end activity
legs.csv:       per-leg detail including transfer structure
pt_stop2stop:   boardings, alightings, load profile per link
scorestats, modestats, accessibility grids
```

### Derived skim

```
scenario_id, origin_zone, dest_zone, period, mode,
ivt_s, wait_s, walk_access_s, walk_egress_s, n_transfers,
transfer_wait_s, fare_aud, gjt_s, gjt_sd_s, n_replications
```

Minimum thirty seeded replications per scenario. Reliability variance is a first-order finding, not a nuisance parameter: a fifteen-minute-headway service with variable signal delay carries a materially different effective cost from its mean run time.

---

## Appendix C — Data acquisition register

| Dataset | Source | Access | Lead time | Criticality | Fallback |
|---|---|---|---|---|---|
| OSM extract | Geofabrik / Overpass | Open | Immediate | High | — |
| GTFS current | TfNSW Open Data Hub | Open | Immediate | High | — |
| GTFS historic | TfNSW / archives | Partial | Weeks | Medium | Manual reconstruction from PDF |
| GTFS-Realtime archive | TfNSW | Open forward | Ongoing | High | Own collection from now |
| Opal aggregate patronage | TfNSW Open Data Hub | Open | Immediate | Medium | — |
| Opal journey-linked | TfNSW | **Request** | Months | **Critical** | Transfer inference model (§7.2) |
| SCATS signal timings | TfNSW | **Request** | Months | **Critical** | Parameter sweep (§7.2) |
| Census JTW | ABS TableBuilder | Open | Immediate | High | — |
| NSW HTS microdata | TfNSW | Request | Weeks | High | Sydney parameters with local adjustment |
| Charging dwell | — | **Field measurement** | Days | **Critical** | GTFS-R dwell inference |
| Parking transactions | City of Newcastle | Request | Weeks | Medium | Occupancy survey |
| Pedestrian counts | City of Newcastle | Request/deploy | Weeks | Medium | Temporary counters |
| Retail floorspace and vacancy | Council / commercial | Mixed | Weeks | Medium | Field audit of the corridor |
| DEM for gradient | Geoscience Australia / ELVIS | Open | Immediate | High | — |

---

## Appendix D — Source basis for §1 and §4.1

The characterisation of the business case, the cost trajectory, the consultation process and the attribution errors derives from the NSW Auditor-General's performance audit *Newcastle Urban Transformation and Transport Program*, report number 310, released 12 December 2018. Patronage figures derive from TfNSW Opal datasets and reporting thereon. The 2020 Strategic Business Case for the light rail extension and the 2025 Newcastle Future Transit Corridor strategic justification report inform §3.4 and the S4/S5 scenarios.

Full citation and page-level referencing to be completed at write-up.
