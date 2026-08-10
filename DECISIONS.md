# DECISIONS.md — modelling choices and their rationale

**Project Wickham** — counterfactual microsimulation of the Newcastle Light Rail
**Stage:** P1 data acquisition complete. No scenario has been run.
**Date:** 10 August 2026

Proposal §8.1: *"`DECISIONS.md` is not optional. Every parameter chosen without
direct empirical support must be recorded here with its rationale and its sweep
range. The credibility of this project rests on being more transparent about its
assumptions than the business case it examines."*

This file records every value in the data package whose `source` field reads
`assumed` or `modelled`, plus the scope decisions taken to close proposal §10.

---

## 0. Status summary

| Layer | Observed | Modelled / assumed | Not obtained |
|---|---|---|---|
| A1 road network | geometry, class, names | lanes, width, speed, kerbside, capacity | signal-level turn counts |
| A2 signals | 1,265 signal locations, 1,386 turn restrictions | cycle time, phasing, offsets, TSP | **SCATS phase data** |
| A3 PT supply | 4 GTFS eras, real feeds | pre-2014 era, stop/transfer attributes | pre-2014 timetable |
| A4 LR vehicle | length, mass, fleet, charging principle | accel, doors, dwell, **charging dwell** | measured dwell |
| A5 parking | 7,710 facilities, 4,861 capacities | price, max stay, occupancy | meter transactions |
| A6 active transport | geometry, gradient from DEM | width, lighting, crossing delay | footway widths |
| B demand | census, HTS, Opal, 119 traffic counts | synthetic population, plans | **journey-linked Opal** |
| C behaviour | VOT from published guidance | **transfer penalty**, walk decay, ASCs | local estimation |
| D land use | POI, buildings, jobs by SA2 | frontage floorspace, vacancy | retail floorspace, ped counts |

Three inputs the proposal named as critical remain unobtained and are handled by
sweep rather than assumption-as-fact: **SCATS phasing**, **journey-linked Opal**,
and **measured charging dwell**. Each is a formal data request (§7.2 fallbacks
are implemented below).

---

## 1. Scope decisions (closing proposal §10)

| # | Decision | Choice | Rationale |
|---|---|---|---|
| 1 | Base year | **2026**, using 2021 Census marginals with HTS 2024/25 behaviour | The 2026 Census is being collected now and will not release before mid-2027. Proceeding on 2021 marginals + current HTS, with the 2026 re-run scheduled as validation, is the proposal's recommended option (§7.3). |
| 2 | Zone granularity | **SA1 in the core, SA2 externally** | 1,500 core SA1s at ~400 persons each resolve the corridor; the external tier only carries Hunter Line through-demand and does not need SA1. |
| 3 | Study boundary | Five LGAs (Newcastle, Lake Macquarie, Maitland, Cessnock, Port Stephens) = 4,086 km², core. Remainder of SA4 *Hunter Valley exc Newcastle* = external boundary tier. | Selecting on SA4 alone dragged in Upper Hunter and Singleton (20,043 km²), far beyond any plausible influence on a 2.7 km corridor. The Hunter Line is cut at **Maitland**, with external SA2s as a boundary treatment. |
| 4 | S2c (Option A alignment) | **Built.** | Cheap to derive once the run-time decomposition exists — it is a speed and signal-conflict change on the same stop set. It is also the alignment with plurality public support, so its omission would be conspicuous. |
| 5 | Weekend modelling | **Full weekend day type built** (WEEKDAY / SAT / SUN in every feed) | Beach and event demand is arguably this system's strongest use case. Excluding it would bias against the light rail. |
| 6 | Event demand | **Not yet built.** Day types exist; an event overlay is not. | Requires venue-level attendance data not yet requested. Recorded as an open task, not silently dropped. |
| 7 | Publication venue | Deferred — not a data decision. | |
| 8 | Data request strategy | Open data harvested first; formal requests still required for SCATS, journey-linked Opal, parking transactions, pedestrian counts. | The open harvest turned out to cover far more than the proposal assumed (see §7), which reduces dependence on the requests. |

---

## 2. Corrections to the proposal's stated data hazards

Working the data changed three of the proposal's premises. Recorded here because
§9 requires that any change to the pre-registered position be logged.

**2.1 — There *is* a clean post-opening, pre-pandemic patronage baseline.**
Proposal §6.4 states the Opal Patronage dataset begins January 2020, "two months
before the pandemic", leaving "effectively no clean post-opening, pre-pandemic
baseline in the public data." The **Opal Trips – Light Rail** series in fact
begins **February 2019, the opening month**, and runs continuously to
September 2025 — 89 months. That yields a full 12-month clean baseline
(March 2019 – February 2020) of **3,417 boardings/day**, now the primary
calibration target. This materially strengthens the identification strategy.

**2.2 — The 1 July 2024 series break is real, and it is compounded by a second,
undocumented break.** NISC 1 bus boardings fall from ~292,000 (October 2024) to
~89,000 (October 2025). That is far larger than a methodology restatement should
produce. The historical GTFS archive shows a new feed,
`regionbuses-newcastlehunter`, first appearing in September 2024 — i.e. the
contract region was **re-scoped** at about the same moment the trip-counting
methodology changed. Any series crossing mid-2024 therefore carries **two**
confounded breaks, not one. All such series are flagged
`methodology_epoch` and are never compared across the boundary.

**2.3 — The published light rail GTFS cannot be used to infer dwell or run-time
variance.** The base feed reports a flat **12.00 minutes** end-to-end in both
directions for all 954 trips, with segment times of exactly 120 or 180 seconds
and **zero dwell at every intermediate stop**. It is an idealised planning
schedule, not an operational one. Consequently:
- observed run time and dwell must come from GTFS-Realtime or field measurement;
- the *scheduled* 12.00 min is retained only as a calibration reference;
- the run-time decomposition in §4 is the model's actual basis.

**2.4 — 2021 Census journey-to-work is unusable as a mode-share target.** Of the
core-area workforce, **56,619 worked from home and 45,289 did not go to work** —
about 34% of all responses. Public transport records 1,461 journeys total
(bus 1,178, train 231, tram/light rail 52), a 0.8% mode share against an HTS
figure of 7.3% pre-pandemic. G62 is retained for *spatial* structure only; the
mode-share calibration target is HTS.

---

## 3. Network layers (A1, A6)

### 3.1 OSM completeness — imputation rates

Proposal §6.4 predicted OSM lane counts, turn restrictions and kerbside use
would be unreliable. Measured rates over 43,112 road edges (9,207 km):

| Field | Imputed | Share | Default rule |
|---|---:|---:|---|
| `lane_width_m` | 42,747 | 99.2% | 3.2 m |
| `kerbside_use` | 42,233 | 98.0% | `unknown` |
| `num_lanes` | 32,499 | 75.4% | by road class (2 motorway/trunk/primary, else 1, per direction) |
| `speed_limit_kmh` | 23,151 | 53.7% | by road class (NSW urban default 50) |

Footways (35,653 edges, 6,325 km): `width_m` imputed 98.4%, `lighting` 98.9%.

**Consequence.** Car delay results are only as good as the corridor lane counts.
Manual correction from aerial imagery is required on the Hunter/Scott corridor
and its parallel routes before any B3 (net arrivals) figure is published. This is
the 30–40% of network-build effort the proposal budgets for, and it is **not yet
done**. Corridor edges are flagged via `scenario_variant_ref`.

### 3.2 Capacity

Mid-block capacity `veh/hr/lane` by class: motorway 2000, trunk 1800, primary
1600, secondary 1400, tertiary 1200, unclassified 1000, residential 800,
service 400, living_street 300. Austroads-style values, **assumed**. Sweep ±20%
where corridor results prove sensitive.

### 3.3 Gradient

Source: **Copernicus GLO-30 DEM**, tiles S33E151 and S34E151, sampled at each
edge's endpoints. Gradient is stored in the digitisation direction; the reverse
takes the negative, satisfying the proposal's asymmetry requirement (§6.3).
Footways additionally carry `walk_speed_factor_fwd` / `_rev` from a Tobler
hiking function normalised to 1.0 at zero grade.

Results: |gradient| median 2.07% (road), 1.68% (footway); p90 9.3% / 12.2%.

**Two caveats, both assumed away for now.**
1. GLO-30 is a **surface** model (DSM), not a terrain model. On short edges under
   tree canopy or beside buildings it overstates relief — visible in the p99
   pinning at the ±25% clip.
2. Gradient is endpoint-to-endpoint, so a way that dips and rises reports ~0.

Both are acceptable for network-wide accessibility and unacceptable for The Hill
and Newcastle East, which the proposal specifically names. **Action:** replace
with 5 m LiDAR DTM from ELVIS for the CBD, Cooks Hill, The Hill and Newcastle
East before publishing accessibility surfaces.

---

## 4. Light rail vehicle and dwell (A4) — the highest-leverage assumptions

### 4.1 Vehicle

Published: CAF Urbos 100, 5 modules, **32.966 m**, **45 t**, 750 V DC overhead
in depot only, **ACR supercapacitor charging at each stop**, fleet of 6
(2151–2156), maximum capacity 270.

Assumed (class-typical for a 33 m 100% low-floor Urbos):

| Field | Value | Basis |
|---|---|---|
| `capacity_seated` | 60 | crush 270 published; seated/standing split assumed |
| `max_accel_ms2` | 1.2 | typical LRV service acceleration |
| `max_decel_ms2` | 1.3 | typical service braking |
| `line_speed_kmh` | 40 | on-street CBD running |
| `door_count_per_side` | 4 | Urbos 5-module typical |
| `door_width_mm` | 1300 | double-leaf |
| `boarding_rate_pax_s` | 0.6 | per door-stream |
| `alighting_rate_pax_s` | 0.8 | per door-stream |

### 4.2 Run-time decomposition — how the residual was derived

Rather than guess a dwell figure, the schedule was decomposed against vehicle
physics on the true alignment (2,729 m from the GTFS shape):

```
scheduled end-to-end        720.0 s   (12.00 min, both directions)
kinematic minimum           290.1 s   (trapezoidal accel/decel at 40 km/h)
------------------------------------
residual to explain         429.9 s
   of which dwell           112.0 s   (4 intermediate stops x (8 s + 20 s))
   signals and recovery     317.9 s   (~26 s per corridor intersection, n=14)
```

This makes every term inspectable and independently toggleable, which is what
scenarios S2a and S2b require.

### 4.3 `dwell_charging_s` — **assumed 20 s, sweep 10–35 s**

Not published anywhere. The proposal's own working estimate is ~20 s at each
stop. Adopted as the base value, as a **separate additive term** so it can be
switched off (S2a) without touching boarding dwell.

**A correction to the proposal's arithmetic.** §6.2 reasons "twenty seconds at
each of six stops … approximately two minutes on a ten-minute run: a run-time
penalty of around twenty per cent." Only **four** of the six stops are
intermediate; both termini charge during layover, which does not enter run time.
The correct figure is 4 × 20 s = **80 s on a 720 s run = 11.1%**, not ~20%.
Still large, still attributable entirely to a late amenity decision, but the
published claim should use 11%.

Sweep across 10 / 20 / 35 s changes end-to-end run time by ±5.6%, which is
carried into mode choice through the outer loop.

**Acquisition route:** field measurement at Civic or Crown Street (a few hours of
observation), or inference from GTFS-Realtime dwell distributions. Until then
this remains the single largest assumed number in the model.

### 4.4 Dwell — other terms

`dwell_fixed_s` = 8 s (sweep 5–12), door open/close plus driver reaction.
`dwell_sd_s` = 6 s, lognormal. Terminus layover 180 s. All **assumed**.

---

## 5. Signal control (A2) — the SCATS proxy

SCATS phase data was not obtained. The corridor inventory is constructed from
OSM: 1,265 signal nodes state-wide in the extract, of which those within 60 m of
the light rail alignment cluster (45 m radius, per-approach nodes merged) into
**14 intersections** on Hunter/Scott Street.

Assumed for every corridor intersection:

| Field | Value | Sweep |
|---|---|---|
| `control_type` | `adaptive` | — (SCATS is adaptive by definition) |
| `cycle_time_s` | 110 | 80–140 |
| `n_phases` | 4 | — |
| `phase_split_pct` | 45 \| 15 \| 30 \| 10 | — |
| `ped_clearance_s` | 8 | — |
| `tsp_enabled` (S2) | **0** | — |
| `mean_delay_to_tram_s` | 24.75 | follows cycle sweep |

**This is the assumption that most drives the headline result**, exactly as the
proposal warned. It is stated prominently, swept, and the S2b variant quantifies
the upper bound: full TSP (green extension + early start, 120 m detection, 12 s
maximum extension, 75% of tram signal delay removed) cuts end-to-end run time
from **12.00 to 7.45 minutes — a 38% reduction**.

That number is the argument for requesting SCATS data. It is also the reason no
run-time-dependent finding may be published as a point estimate.

---

## 6. Parking (A5)

7,710 facilities from OSM; 4,861 carried a capacity tag, 2,849 were imputed by
type (on-street 12, off-street public 60, off-street private 40 spaces).

Price, maximum stay and hourly occupancy are **entirely assumed** — City of
Newcastle publishes neither meter transactions nor occupancy. Four zones:

| Zone | AUD/hr | Max stay | Peak occupancy | Facilities | Spaces |
|---|---:|---:|---:|---:|---:|
| CBD core | 3.20 | 120 min | 0.94 | 203 | 7,069 |
| CBD fringe | 2.40 | 180 min | 0.88 | 465 | 3,584 |
| Honeysuckle | 2.40 | 240 min | 0.86 | — | — |
| Beach / east | 2.00 | 240 min | 0.85 | 4 | 240 |
| Outer | free | — | 0.73 | 7,038 | 157,018 |

Price sweep ±50%. Occupancy profiles are 24-hour vectors, weekday shaped.

Corridor kerbside removal is modelled as a scenario variant, not a constant:
`park_2026` removes **210 on-street spaces** on the corridor (assumed);
`park_2026_pre_lr` retains them. Scenarios without a tram use the latter.

---

## 7. Land use (D1)

**Frontage segments.** 498 segments of 50 m across seven streets — Hunter and
Scott (corridor), Darby, King, Beaumont (off-corridor comparators), Honeysuckle
Drive and Wharf Road (waterfront). This set supports hypothesis B4 (generation
vs displacement) directly.

**Retail floorspace is modelled, not observed.** No frontage-level floorspace
data exists for Newcastle. Estimated as:

```
retail_floorspace_m2 = GFA_within_30m x 0.35 x (retail+food POI share of all POI)
```

where `GFA = building footprint x levels` and levels default by building type
when untagged. Yields 51,843 m² on Hunter St, 33,812 m² on Scott St,
16,444 m² on Darby St. The 0.35 ground-floor coefficient is **assumed**.
**Action:** field audit of the corridor replaces this (proposal §7.2 fallback).

`vacancy_rate` and `awning_coverage_pct` are **empty** — flagged
`not_available` rather than invented. Both are in the B1 metric set and both
require the field audit.

**Jobs.** The 2021 Working Population Profile is not published at Destination
Zone geography (confirmed: no WPP/DZN DataPack exists). Jobs are therefore taken
from **WPP at POW SA2** and disaggregated to SA1 in proportion to a
workplace-weighted POI index (office 12, civic 15, food 6, health 8, retail 4,
leisure 2, amenity 1 jobs per establishment — **assumed**), falling back to
population share where an SA2 contains no mapped POI. The SA2 control total is
preserved exactly: 296,471 modelled against 296,474 published. Flagged
`jobs_source = modelled_from_WPP_SA2`.

**POI attraction weights** (retail 1.0, food 1.2, civic 1.5, office 0.8,
tourism 1.1, leisure 0.9, health 1.0, amenity 0.4, landuse 0.1) are **assumed**
and feed both destination choice and frontage throughput.

---

## 8. Behavioural parameters (C1) — "this layer decides the answer"

30 parameter sets (5 segments × 6 purposes). Full table in
`params/C1_behavioural_parameters.csv`; sweep grid of 140 points in
`params/C1_sensitivity_sweep_grid.csv`.

### 8.1 `beta_transfer_penalty_min` — **assumed 8.0 min, sweep 3–15**

The parameter the policy question turns on. The proposal is explicit that
literature defaults must not be used and that every finding must be reported as
a curve. Implemented: the sweep grid crosses transfer penalty
{3, 5, 6.5, 8, 10, 12, 15} with walk decay and charging dwell, and **no headline
figure may be reported at a single value**.

Physical anchor now available: the Newcastle Interchange transfer table gives a
**mean 112 s and maximum 284 s** walk-plus-crossing time across 51 stop pairs
(35 of them cross-modal). The behavioural penalty sits *on top of* that measured
time.

**Estimation route:** NSW HTS interchange rates plus Opal tap sequencing at the
Interchange. Journey-linked Opal would settle it; the §7.2 fallback (tap-on /
tap-off timing plus a matching model) is the plan of record.

### 8.2 Walk access decay — **assumed negative exponential, β = 0.0018 /m**

Sweep 0.0010–0.0030. Weight 0.49 at 400 m, 0.24 at 800 m, 0.12 at 1,200 m;
considered to 2,500 m. A cumulative-Gaussian alternative (μ = 700 m, σ = 420 m)
is provided. **No 400 m threshold is used anywhere**, per §6.3.

### 8.3 Value of travel time — `literature`

2026 AUD/hr: commute 18.60, education 9.30, shopping/other 15.20, employer's
business 55.40. ATAP PV2 / TfNSW Economic Parameter Values conventions.
Sweep ±30%. Concession, student and car-unavailable segments take 0.75×.

### 8.4 Time weights

`beta_walk_access` / `_egress` 2.0 (1.5–2.5), `beta_wait` 2.0 (1.5–2.5),
`beta_headway` 0.5 (0.35–0.65), `beta_reliability` 1.3 (0.8–1.8),
crowding 1.00 seated / 1.45 standing. All `literature`.
Gradient penalties — uphill 0.09, downhill 0.02 per % grade — are **assumed**.

### 8.5 Alternative-specific constants — **assumed priors, must not be freely calibrated**

Relative to car driver = 0: car passenger −0.85, bus −1.05, light rail −0.75,
rail −0.65, walk +0.35, cycle −1.35.

**These are priors for the first calibration pass only.** Proposal §9 identifies
ASC absorption as the primary threat to validity: calibrating mode constants to
observed 2019 patronage would fit away the very effect under test. The rule
adopted is: **estimate ASCs on the pre-intervention period (era 3, 2018) and hold
them fixed across all scenarios**, or constrain them and report the constraint.
Any departure from this must be logged here before results are seen.

### 8.6 Nesting

Nested logit; PT nest {bus, lr, rail} coefficient 0.65, private 0.80,
active 0.70. **Assumed.**

---

## 9. Synthetic population and demand (B1, B2)

**612,680 persons in 246,022 households, 2,020,696 trips.** Seed 20260810.
Deterministic: same seed reproduces exactly.

Fitted to census marginals per SA1 — household size (G35), vehicles (G34),
dwelling structure (G36), age–sex (G04), labour force (G43/G46), income (G17),
occupation (G60). Validation of the fit:

| Statistic | Census | Synthetic |
|---|---:|---:|
| Mean household size | 2.49 (implied) | 2.49 |
| Zero-vehicle households | 5.71% | 5.93% |
| Mean vehicles per household | 1.818 | 1.809 |
| Employed as share of persons | ~50% | 50.4% |

Assumed elements:

- **Licence holding by age band** (0.62 at 18–24 rising to 0.94 at 45–54,
  falling to 0.45 at 85+). NSW-typical, assumed.
- **Trip rates** from HTS 2024/25 for the study-area LGAs: 3.47 trips/person/day.
  Because HTS counts the return-home leg, activity rates are scaled by **0.7345**
  so that E[activities] + P(any activity) = 3.47. Realised 3.298 (−5%), the
  shortfall being persons who generate no activity at all.
- **Departure-time profiles** by purpose: 24-hour vectors, NSW-typical shapes,
  **assumed**.
- **Activity durations**: work 465 min, education 360, shopping 45, other 90,
  business 60, NHB 20. **Assumed**, ±30% lognormal.
- **Destination choice**: singly-constrained gravity, attraction × exp(−d/d̄),
  with d̄ the HTS mean journey distance for that purpose (commute 19.3 km,
  education 6.9, shopping 7.4, other 9.1, business 23.7).
- **Home coordinates** are jittered within the SA1 at 0.6 × the equivalent-circle
  radius. Dwelling-level placement would be better and is available for the CBD
  only (10,795 building footprints).

**Known limitation.** The plans are *seed* plans: departure times and modes are
initial conditions for MATSim's co-evolutionary scoring, not predictions. Mode is
deliberately **not** assigned in B2 — assigning it here would pre-empt the
question the model exists to answer.

---

## 10. Scenario construction (E1)

All ten scenarios derive from `schedules/base2026.zip` by explicit transformation,
so the "identical land use, population, parameters, non-CBD bus network"
requirement of §4.3 holds by construction rather than by discipline.

Resulting trunk run times (weekday, end-to-end):

| Scenario | Trunk | Run time | Δ vs S2 |
|---|---|---:|---:|
| S0 heavy rail to Newcastle | heavy rail | — (254 trips extended) | — |
| S1 bus shuttle from Wickham | bus | 10.83 min | −9.8% |
| **S2 light rail as built** | light rail | **12.00 min** | — |
| S2a charging dwell removed | light rail | 10.33 min | **−13.9%** |
| S2b full TSP | light rail | 7.45 min | **−37.9%** |
| S2c Option A alignment | light rail | 9.70 min | −19.2% |
| S3 bus rapid transit | BRT | 7.08 min | −41.0% |
| S4 extended to Broadmeadow | light rail | 18.08 min | +50.7% |
| S5 extended to John Hunter | light rail | 26.35 min | +119.6% |
| S6 no trunk mode | none | — | — |

Assumed in these constructions:

- **S2b** removes 75% of tram signal delay. Assumed; the realistic range is
  50–90% and should be swept.
- **S2c** assumes the reserved former-railway alignment permits 60 km/h and
  removes 60% of at-grade signal conflict.
- **S3** BRT: 40 km/h, 12 s dwell, no charging, 7.5 min headway, same six stops
  and the **same lane take as the tram** — so the road-space externality is not
  quietly removed when comparing S2 to S3.
- **S4/S5 extension stop siting** (Hamilton, Broadmeadow, Lambton, John Hunter
  Hospital) is assumed from the 2020 Strategic Business Case and 2025 Future
  Transit Corridor work, not surveyed.
- **S0/S1/S2c/S6** use `net_base2026_hunter_st_full_capacity`: 2 lanes per
  direction on Hunter/Scott, kerbside parking retained, no banned turns,
  100 s cycle. This is what makes B3 testable — a scenario without a tram must
  get its road space back.

---

## 11. Era variants (A3)

| Era | Source | Status |
|---|---|---|
| pre-Dec 2014 | **Reconstructed** | Archive begins Aug 2016. Built by restoring Wickham, Civic and Newcastle stations onto the 219 services terminating at Hamilton in the Aug-2016 feed, at 60 km/h with 30 s station dwell. **Frequency and stopping pattern are 2016, not 2014.** Must be validated against a 2014 public timetable before use in any published figure. |
| 2015 – Jul 2017 | `complete_gtfs` 29 Aug 2016 | Real feed. 112 routes, 4,991 stops. |
| Jul 2017 – Feb 2019 | `NISC001` 19 Oct 2018 + trains | Real feed. Franchise start captured exactly (NISC001 archive begins 18 Jun 2017). |
| post-Feb 2019 | `NISC001` Mar 2019 + `lightrail-newcastle` Feb 2020 | Real feeds. Light rail feed epoch is Feb 2020 — the earliest archived — so it post-dates opening by a year. |
| base 2026 | Aug 2026 feeds | Real. |

Each era feed is normalised to a common WEEKDAY / SAT / SUN calendar by
selecting the representative service day with the most active services within
each source feed's own validity window. This makes eras directly comparable and
is a **modelling choice**, not a property of the source data.

Trip ids are namespaced by day type (`WEEKDAY.<trip_id>`). A trip that runs on
several day types carries one id in the source feed, so merging the three
slices without namespacing emitted that trip's `stop_times` two or three times
under a single id — silently inflating service on every multi-day trip. The
integrity check in `tests/check_package.py` asserts `stop_sequence` uniqueness
within every trip precisely to catch this class of error.

---

## 12. Validation design

210 targets, **67 calibration / 143 holdout**. The split is fixed here, before
any scenario is run, per §9.

- **Calibration:** aggregate light rail and bus patronage, HTS mode share,
  traffic counts at permanent stations, light rail card-type mix, scheduled
  run time, alignment length.
- **Holdout:** stop-level light rail tap-on shares (6), station entries and
  exits (52), traffic counts at sample stations (~108).

Headline calibration anchors:

| Target | Value | Period |
|---|---:|---|
| Light rail boardings | 3,417 /day | Mar 2019 – Feb 2020 |
| Light rail share of local PT boardings | 20.8% | Mar 2019 – Feb 2020 |
| Newcastle LGA PT mode share | 7.3% | 2018/19 |
| Newcastle LGA PT mode share | 3.8% | 2024/25 |
| Scheduled run time | 12.00 min | 2026 |
| Alignment length | 2,729 m | 2026 |

**Note on the 20.8% figure.** It is light rail ÷ (light rail + NISC 1 bus)
*boardings*, which is **not** hypothesis A1's metric. A1 asks for light rail
person-legs ÷ *total* PT person-legs across Greater Newcastle, whose denominator
also includes heavy rail and regional buses and whose numerator is legs, not
taps. The observed 20.8% is an upper bound on A1 and must not be quoted as if it
were A1. The model produces the A1 metric properly.

**Note on the pandemic.** PT mode share roughly halved between 2018/19 and
2024/25 (7.3% → 3.8%). A 2026 base year therefore calibrates to a
pandemic-suppressed PT market. Because all scenarios share that demand, the
*comparison* between scenarios remains valid; the *absolute* patronage levels do
not transfer to a pre-2020 world. Every headline should state which it is.

---

## 13. Outstanding data tasks, in priority order

1. **SCATS phase data** (TfNSW request) — currently the largest uncertainty in
   corridor run time; S2b shows the swing is 38%.
2. **Charging dwell field measurement** — a few hours at Civic or Crown Street
   resolves an 11% run-time term.
3. **Journey-linked Opal** (TfNSW request) — required to estimate the transfer
   penalty rather than sweep it.
4. **Manual OSM correction on the corridor** — lane counts, turn restrictions,
   kerbside. 75–98% of these fields are currently imputed; B3 depends on them.
5. **LiDAR DTM for the CBD, The Hill and Newcastle East** — replaces the GLO-30
   surface model where gradient actually matters.
6. **Pedestrian counts** — none published for Newcastle. Deploy temporary
   counters on Hunter St frontage segments (§7.2 fallback).
7. **Retail floorspace and vacancy field audit** — currently modelled from
   building footprints; vacancy is empty.
8. **2014 public timetable** — to validate the era-1 reconstruction.
9. **Event attendance data** — for the event-demand overlay (§10 item 6).
10. **GTFS-Realtime collection** — start now; it is the fallback for both dwell
    and signal delay, and it accrues only forward.

---

## 14. Change log

| Date | Change |
|---|---|
| 2026-08-10 | Initial. P1 data acquisition. Scope decisions §10.1–3, 4, 5 closed. Proposal premises corrected per §2.1–2.4. No scenario run; no falsification condition altered. |
