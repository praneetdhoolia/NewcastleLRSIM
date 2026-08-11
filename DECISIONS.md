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

**2.5 — The corridor is not 75–98% imputed; that was the network-wide rate.**
§3.1 measured imputation over all 43,112 road edges and concluded that
"manual correction from aerial imagery is required on the Hunter/Scott corridor".
Measured *on the corridor* — the 40 Hunter and Scott Street edges within 60 m of
the light rail alignment, 4.08 km — the rates invert:

| Field | Corridor trunk observed in OSM | Network-wide imputed (§3.1) |
|---|---:|---:|
| `num_lanes` | **87.5%** | 75.4% imputed |
| `speed_limit_kmh` | **97.5%** | 53.7% imputed |
| `oneway` | 87.5% | — |
| `kerbside_use` | 27.5% | 98.0% imputed |
| `lane_width_m` | 0% | 99.2% imputed |

The corridor is one of the best-mapped parts of the extract, not the worst — and
the imputation rate over the 84 corridor cross streets (23.8% lanes observed) is
much closer to the network-wide figure, which is what §3.1's average was actually
measuring. The as-built corridor reads `lanes=1, oneway=yes, maxspeed=40`,
consistent with NSW Movement and Place: *"one lane of traffic in each direction
on Hunter and Scott streets between Worth Place and Telford Street"*.

**Consequence.** The 30–40% of network-build effort the proposal budgeted for
manual aerial correction is not needed for the as-built lane counts, which are
observed. What is genuinely unavailable is the **counterfactual** — Hunter and
Scott *before* the tram — which no 2026 imagery can supply. That is now an
explicit swept assumption (§3.4) rather than a digitising task. The B3
net-arrivals test is therefore an observed-network-versus-assumed-network
comparison, and the assumed side is the one that is swept.

**2.6 — EPSG:28356 is GDA94 / MGA zone 56, not GDA2020.** The repo labels the
CRS "EPSG:28356 (GDA2020 / MGA Zone 56)" throughout. EPSG:28356 is
*GDA94* / MGA zone 56; GDA2020 / MGA zone 56 is EPSG:7856. The two differ by
about 1.8 m — immaterial to network topology, junction geometry or run time, and
well inside the positional error of the OSM geometry the network is built from,
so **the projection in use is not changed**. The label is wrong and is corrected
here rather than propagated. Note that the ABS boundary downloads *are* GDA2020
(their filenames say so), so the 1.8 m offset is real but absorbed at zone
resolution.

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

> **Superseded by §2.5 and §3.4 (P2).** This section originally concluded that
> manual correction from aerial imagery was required on the Hunter/Scott corridor.
> Measured on the corridor rather than network-wide, 87.5% of trunk lane counts
> and 97.5% of trunk speed limits are observed in OSM, and the imagery correction
> is not needed for the as-built network. The counterfactual — the corridor
> *without* the tram — is what cannot be observed, and it is now an explicit swept
> assumption. The claim in the last line below was also wrong: corridor edges were
> **not** flagged via `scenario_variant_ref` (every one of the 43,112 A1 rows
> carries `base2026`); they are flagged in
> [`A1_corridor_road_edges.csv`](data/processed/network/A1_corridor_road_edges.csv)
> as of P2.

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

### 3.4 Corridor attribute provenance and the E1 road variants (P2)

`src/build/build_corridor_road_attributes.py` grades the corridor by evidence
rather than correcting it by hand, and turns `scenarios/E1_road_variants.csv`
into edge-level deltas. Three artefacts:

| File | What it holds |
|---|---|
| [`data/processed/network/A1_corridor_road_edges.csv`](data/processed/network/A1_corridor_road_edges.csv) | 605 corridor / parallel edges, each attribute paired with a `*_source` of `osm`, `imputed_rule`, `assumed` or `absent` |
| [`data/processed/network/A2_turn_restrictions_resolved.csv`](data/processed/network/A2_turn_restrictions_resolved.csv) | all 1,385 OSM restriction relations resolved to coordinates and to a distance from the alignment |
| [`data/processed/network/A1_road_variant_patches.csv`](data/processed/network/A1_road_variant_patches.csv) | 195 rows: the only places any E1 variant departs from the observed network |

**Corridor extent is geometric, not drawn.** The alignment comes from the tram
route's own GTFS shapes. `corridor_trunk` = Hunter/Scott within 60 m of it (40
edges); `corridor_cross` = any other road within 40 m (84 edges, the cross
streets at the 14 signalised intersections); `parallel` = the named comparator
and diversion routes within 1.5 km (417 edges).

**Turn restrictions are observed, and now checkable.** `A2_turn_restrictions_osm.csv`
stored member strings with no geometry, so E1's `banned_turn_movements` could not
be verified. Resolving each relation through its via node, else its via way, else
its from way, locates 1,385 of 1,386 (one relation has no resolvable member) and
puts **10 within 40 m** of the alignment and 15 within 80 m, against E1's assumed
14. E1's figure is a reasonable summary of the observed restriction set, and the
network build uses the observed restrictions, not the number.

#### Assumed values introduced here

| Value | Assumed | Sweep | Why it cannot be observed |
|---|---|---|---|
| `pre_lr_lanes_per_direction` (Hunter/Scott without the tram) | **2** | **1–2** | The tram was built in 2017–19. A 2026 extract, and 2026 imagery, show only the post-tram cross-section. This is the counterfactual the whole B3 test rests on. |
| `pre_lr_kerbside_use` | `parking` | — | Same reason. E1 already asserts kerbside parking is restored in the no-tram network. |
| `extension_lane_take_per_direction` (S4/S5) | **1** | **0–1** | The extensions were never built. The rule mirrors what the tram did to Hunter/Scott: one running lane per direction, floored at one, and the kerbside where the street is already single-lane. |
| Extension corridor extent | derived from the S4/S5 **stop** sitings | — | See the defect below. |

#### A P1 defect this exposed

The S2c, S4 and S5 scenario feeds add or move stops but carry the **unmodified
275-point as-built shape** — all four tram feeds have byte-identical geometry.
So the Broadmeadow and John Hunter Hospital extensions have stops hanging off an
alignment that stops at Newcastle Interchange, and S2c's "reserved former-railway
alignment" is geometrically the as-built street alignment.

Handled, not hidden:

- the extension corridor (66 edges for S4, 89 for S5) is derived from the
  extension **stop coordinates**, which do exist, by interpolating through the
  stop sequence and buffering at 60 m. The stop sitings are themselves assumed
  (§10), so the extension corridor is assumed twice over and is labelled so;
- S2c is unaffected in road terms — it uses the full-capacity Hunter Street
  network either way — but its run-time advantage is a property of its GTFS
  timings, not of a modelled alignment, and should not be reported as though the
  reserved corridor had been traced;
- **Action:** rebuild the S2c/S4/S5 shapes in `build_scenario_schedules.py`
  before any extension result is published.

**Resolved at P3 (10 August 2026).** `src/build/shape_tools.py` builds the
missing geometry from layers the package already observes, and
`build_scenario_schedules.py` writes it into the feeds. The defect turned out
to extend one feed further than recorded above: **S0** extends heavy rail to
Civic and Newcastle without extending its shape either.

| Feed | Alignment now | Length | Evidence |
|---|---|---|---|
| S4 / S5 | Routed over the **observed OSM centreline** of the streets the 2020 NLR Extension Strategic Business Case names — Tudor, Belford, Lambton Rd, Turton Rd, Russell Rd, Lookout Rd | 7.00 km to JHH (S4 is this truncated at Broadmeadow, 2.58 km) | The SBC states **6.65 km**; the independently routed corridor lands **+5.3%** on that, over the published street sequence |
| S2c | The retained **harbour-side former-railway strip**, observed where it survives (Foreshore Footpath) and interpolated across the redeveloped gap | 2.93 km | 33% of the length is observed OSM geometry; the rest is interpolated and labelled so |
| S0 | The same corridor, to the former Newcastle station | 2.58 km | 21% observed |

**Stop sitings are still assumed, but no longer typed.** Each extension stop is
now anchored on an observed feature and then projected onto the routed
corridor:

| Stop | Anchor | Offset |
|---|---|---|
| Hamilton (Beaumont St) | observed Tudor St × Beaumont St intersection | 0 m |
| Broadmeadow | observed `railway=station` node, Broadmeadow Station | 98 m |
| Lambton | observed Lambton Rd × Turton Rd intersection | 0 m |
| John Hunter Hospital | observed POI `w1025992530`, `health:hospital` | 107 m |

The P1 coordinate for **Hamilton sat 548 m off the published corridor** — it
was near Beaumont St/Maitland Rd rather than on Tudor St. That is the one
siting the correction actually moves.

**Consequences, both material:**

1. **The extension corridor roughly doubled.** Derived from a real 7.0 km
   routed alignment rather than a straight-line interpolation through two to
   four stops, the E1 patch set grows from 195 rows to **414** (S5 89 → 240,
   S4 66 → 134). Corridor/parallel edges go from 605 to **714**. The extension
   lane take is applied to far more edges than at P2, and 85.4% of those lane
   counts are observed in OSM.
2. **S2c is now a different scenario in the model, not just in the timetable.**
   Its 11 tram stops move onto the reserved corridor (about 115 m north of
   Hunter Street) *before* the run-time decomposition, so its timetable
   describes the reserved alignment. Previously its stops sat on Hunter/Scott
   and pt2matsim mapped them to the street network — the alignment the
   scenario exists to avoid.

**One pre-existing source-feed limitation, measured rather than patched over.**
**477 of 4,374 base-feed trips (10.9%)** carry a GTFS shape that ends more than
500 m from the trip's own last stop — worst case 249 km, the intercity services
whose shapes cover only part of the run. It is identical in every scenario feed
so it cannot bias a comparison. The S0 corridor is therefore spliced only onto
shapes that actually reach the Interchange (`S0_JOIN_TOLERANCE_M = 1500 m`);
125 of the 254 extended trips keep their short source shape rather than gain
an invented 2.4 km of geometry.

### 3.5 pt2matsim is not reproducible run to run — measured, not assumed away

`PublicTransitMapper` does not produce byte-identical output from identical
inputs. Confirmed across `SpeedyALT`, `AStarLandmarks` and `CHRouter`, and at
`numOfThreads=1` as well as 3, so it is not thread scheduling — it is candidate
selection over a hash-ordered collection. This collides with the project's
determinism rule, so the drift is measured and published rather than waved
through (`--determinism-check` in `build_matsim_network.py`):

| Property | Repeat-build agreement |
|---|---|
| stop → link assignment | **100.000%** |
| transit route count | 1,714 = 1,714 |
| stop facility count | 4,171–4,178 (±0.17%) |
| **route link sequences** | **81.9–82.3%** |

So roughly **18% of transit routes take a different path between two builds of
the same feed**, while every stop attaches to the same link every time. That
matters for bus link loading, and therefore for B3.

**How this is handled.**

1. The mapped schedules are a **build of record**: hashed into
   `data/MANIFEST.csv`, and the artefacts P3+ consume. Regeneration reproduces
   the model statistically, not byte-for-byte.
2. `tests/check_package.py` asserts the reproducible half **exactly** — the
   `stop_link_fingerprint` must match the recorded build — and asserts the
   invariants that hold in every build (no unmapped stop, artificial link share
   under 5%).
3. `route_link_fingerprint` is recorded per feed to identify which build a result
   came from.
4. **Any scenario comparison must be run against one build of the network.**
   Comparing S2 mapped in one build against S0 mapped in another would put an
   18% route-path difference inside the treatment effect. This is a P5 run
   constraint, recorded here because it originates in P2.

Everything else in P2 *is* deterministic: the OSM merge, the variant patching and
netconvert are byte-identical on rebuild (verified by re-running and comparing
digests).

### 3.6 Toolchain, pinned

P2 needs a JVM, pt2matsim and SUMO, none of which the repo can regenerate.
`src/setup/bootstrap_toolchain.py` fetches all three into `.tools/` (gitignored)
and records version, source URL, sha256 and retrieval date in
`.tools/toolchain.json` — the provenance record for the tools, mirroring
`data/raw/provenance_*.json` for the data.

| Tool | Version | Source | Why this one |
|---|---|---|---|
| Eclipse Temurin JDK | 25.0.4+7 | github.com/adoptium | pt2matsim 26.6's pom sets `<release>25</release>`; a 21 JDK will not load it |
| pt2matsim | 26.6 (shaded jar) | repo.matsim.org | bundles MATSim and declares `PublicTransitMapper` as Main-Class, so no Maven and no build step |
| Eclipse SUMO | 1.27.1 | PyPI `eclipse-sumo` wheel | SUMO publishes no GitHub release assets; the wheel is the only pinnable Windows distribution |

A toolchain change is a model change: re-run, re-hash, and log it in §14. Two
domains were added to `sandbox.network.allowedDomains` for these
(`repo.matsim.org`, `pypi.org`/`files.pythonhosted.org`).

**Known tool defect.** `netconvert --osm.crossings` segfaults (exit 139) on this
extract in SUMO 1.27.1, reproducibly and on its own. Crossings and sidewalks are
therefore not imported into the SUMO corridor. Pedestrians are modelled in MATSim
on the A6 active-transport network, and the crossing inventory itself is
unaffected — it lives in `A2_crossings_osm.csv`.

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

#### The other three signal variants (added in P2)

`scenarios/E1_scenarios.csv` references **five** `signal_variant_ref` values;
`A2_signal_control_corridor.csv` contained two. The three scenarios pointing at
the missing ones had no signal layer at all. All three are now built, over the
same 14 intersections, and all three are **assumed**:

| Variant | Cycle | TSP | Tram delay | Basis |
|---|---:|---:|---:|---|
| `S0_no_tram` | **100 s** | 0 | **0 s** | E1 sets 100 s for the full-capacity network; there is no tram to delay |
| `S2c_reserved_alignment` | 110 s | 0 | **9.9 s** | the reserved alignment removes 60% of at-grade signal conflict (§10), so 0.40 × 24.75 |
| `S3_brt_priority` | 110 s | 1 | 6.2 s | BRT is given the *same* priority mechanism as S2b, so S2b and S3 differ in vehicle and dwell rather than in how generously each is signalled |

All three sweep on the same 80–140 s cycle range as S2. Giving BRT the same
priority as the tram is a deliberate choice against the light rail's favour: the
alternative — modelling BRT with priority the tram lacks — would let the signal
assumption decide the S2-versus-S3 comparison.

#### How the assumed timings reach SUMO

`netconvert` derives each junction's **phase structure** from its geometry. That
structure is kept; only the **durations** are replaced, distributing the A2 split
across the green phases and giving each intervening yellow/all-red phase the A2
pedestrian clearance. Structure and timing are never blended, and every emitted
program carries both provenances as parameters (`phase_structure_source`,
`timing_source`). All 14 A2 intersections match a signalised junction in every
variant, and the realised cycle lands within 1 s of the A2 value.


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

### 9.1 B1 — persons and households

**612,668 persons in 245,738 households.** Seed 20260810, deterministic.
Fitted to census marginals per SA1 — household size (G35), vehicles (G34),
dwelling structure (G36), age–sex (G04), labour force (G43/G46), income (G17),
occupation (G60). Validation of the fit:

| Statistic | Census | Synthetic |
|---|---:|---:|
| Mean household size | 2.49 (implied) | 2.493 |
| Zero-vehicle households | 5.71% | 5.95% |
| Mean vehicles per household | 1.818 | 1.806 |
| Employed as share of persons | ~50% | 50.4% |

Assumed elements: **licence holding by age band** (0.62 at 18–24 rising to 0.94
at 45–54, falling to 0.45 at 85+), NSW-typical; **home coordinates** jittered
within the SA1 at 0.6 × the equivalent-circle radius.

> **P3 note.** `build_population.py` no longer generates chains, so it no longer
> draws random numbers for them, and the person/household draw moved slightly:
> 612,680 → 612,668 persons, 246,022 → 245,738 households. Every fit statistic
> above is unchanged to within 0.02 pp. The file is a different sample of the
> same distribution, not a different distribution.

### 9.2 B2 — activity chains (rebuilt at P3)

The P1 chains were **not usable as MATSim plans**. Measured on the delivered
file before replacing it:

| Defect | Measured |
|---|---|
| Destinations were zone centroids | 1,452,065 activity legs landed on **1,481 distinct coordinates**; one centroid took **158,431 legs (10.9%)** |
| Chains were not tours | activities were shuffled and chained without returning home, so **684,125 legs (47%)** had a home-based purpose but did not start at home |
| Purposes were wrong | **all 568,631** closing legs were labelled NHB, making 70% of "NHB" simply going home |
| One subtour per agent | every day was a single home→…→home loop, so MATSim's `SubtourModeChoice` would fix one chain-based mode for the whole day |
| The day did not close | 1.77% of arrivals fell past 24 h, the latest at **36.0 h** |
| One generic day | though the schedules carry WEEKDAY/SAT/SUN |

`src/build/build_activity_chains.py` replaces them with home-anchored **tours**,
one file per day type. Realised over 612,668 persons:

| | WEEKDAY | SAT | SUN |
|---|---:|---:|---:|
| Legs | 2,177,684 | 1,991,493 | 1,688,002 |
| Tours | 970,065 | 887,526 | 751,564 |
| Legs per person | 3.554 | 3.251 | 2.755 |
| Persons with more than one tour | 56.7% | 56.2% | 49.9% |

Structural properties, verified on the full output: **100%** of tours close at
home; **zero** return-home legs are labelled NHB; **zero** legs arrive after the
30 h horizon; non-home destinations occupy **76,278** distinct coordinates on a
weekday and the busiest single coordinate takes **0.65%** of legs, against 10.9%
before. **95.5%** of activity ends are placed on an observed POI or CBD building
footprint; 4.5% fall back to a jittered point in zones that have neither.

The realised week trip rate is **3.397** against the HTS **3.473** (−2.2%; P1
was −5%). The residual is tours dropped for not fitting inside the day.

#### Assumed values introduced here

**Measured from Newcastle data** (`src/build/measure_network_factors.py` →
[`params/C2_network_factors.json`](params/C2_network_factors.json)). Each of
these was a typed-in constant until P3:

| Value | Measured | Source | Was |
|---|---|---|---|
| `DETOUR_FACTOR` (straight-line → network) | **1.3376**, sweep 1.25–1.42 | Shortest path over the observed A1 road graph, 551 population-weighted zone pairs routed. Aggregate ratio of summed network to summed straight-line distance — the mean of per-pair ratios (1.43) is pulled up by short circuitous trips and would overstate the correction for the long trips that dominate a distance mean. | assumed 1.30 |
| Weekday vs weekend travel | **0.7521**, sweep 0.709–0.816 | RMS traffic counts, which publish a `WEEKDAYS` and a `WEEKENDS` figure per station-year — 551 station-years. | assumed (implied 0.825) |
| Lower bound on work attendance | **0.6508** | Census G62: of employed residents, the share who travelled to work on census night. | no bound |

**Still assumed, each now with a sweep range:**

| Value | Assumed | Sweep | Why it is not observed |
|---|---|---|---|
| Saturday : Sunday split *within* the weekend | 1.1875 | 1.00–1.45 | The traffic counts report one `WEEKENDS` figure and do not separate the two days. This is the only part of the day-type shape still assumed — the weekday/weekend ratio itself is measured. |
| Day-type purpose mix | commute and education collapse at the weekend, shopping and social rise | ±30% on each multiplier | The HTS carries no day-of-week dimension — confirmed in the raw workbook, whose only dimensions are financial year, LGA, mode and purpose. Renormalised against the HTS purpose share so it redistributes rather than inflates. |
| `P_MANDATORY` (work / education tour made on a given day) | 0.78 / 0.85 weekday | **0.65**–0.90 / 0.70–0.95 | The lower bound is now observed: census G62 says 65.1% of employed residents travelled to work on census night. It cannot set the *value* — that night was August 2021 with 19.2% working from home, so it carries the lockdown with it, and §2.4 already rules G62 out as a behavioural rate. It bounds the sweep from below instead. |
| `P_INTERMEDIATE_STOP` by purpose | 0.12–0.30 | 0.10–0.35 | Trip chaining rates are not in the published HTS tables. **This parameter decides how many sub-tours exist, and therefore how freely MATSim's mode choice can vary within a day.** |
| `P_SECOND_STOP` | 0.25 | 0.12–0.40 | Same reason. |
| `CHILD_TOUR_RETENTION` | 0.4 | 0.25–0.60 | Share of an under-12's secondary tours made independently. |
| `EXTERNAL_INTERACTION_RATE` | 0.08 | 0.04–0.15 | Share of external-tier residents entering the core on a weekday. **This one is not derivable from the package as it stands**: the census place-of-work tables (W01A…) give jobs *by* SA2 but there is no journey-to-work origin-destination table (SA2 usual residence × SA2 place of work), which is what would settle it. Added to §13. |
| Activity durations, departure profiles | carried from P1 | ±25% on each mean; ±30% lognormal within | Not Newcastle-specific in any observable sense. |

#### Destination choice is now tied to the HTS, not set by hand

P1 set the gravity decay to `1/mean-distance` directly, which left education and
shopping **60% too long** and work-related business **22% too short**. The decay
is now solved per purpose by bisection so the model's own expected journey
distance equals the HTS figure. Realised against target, all six purposes:

| Purpose | HTS network km | Model network km |
|---|---:|---:|
| HW | 17.76 | 17.76 |
| HE | 6.44 | 6.44 |
| HS | 7.13 | 7.13 |
| HO | 10.16 | 10.16 |
| WB | 23.02 | 23.02 |
| NHB | 7.84 | 7.84 |

#### External boundary demand

B1 synthesises the 1,500 core SA1s only, so the 201 external SA1s — the boundary
tier that exists to carry Hunter Line through-demand (§1, scope decision 3) —
generated no travel at all, though their **70,448** residents are a ninth of the
core population. A boundary treatment now generates **5,384** weekday agents
(2,254 Saturday, 1,697 Sunday), each making one home-based tour into the core,
reaching 828 distinct core zones at a mean 59.8 km. This is a boundary
treatment, not a second population synthesis: freight, the Port and full
external synthesis stay out of scope (proposal §5).

**Known limitation, unchanged from P1.** The plans are *seed* plans: departure
times are initial conditions for MATSim's co-evolutionary scoring, not
predictions. Mode is deliberately **not** assigned in B2 — assigning it here
would pre-empt the question the model exists to answer.

## 9.3 MATSim plans and the C1 translation (P3)

`build_matsim_plans.py` turns B2 into `population_v6` plans, one file per day
type; `build_matsim_run_inputs.py` assembles a runnable scenario per
(scenario × day type). 521,502 weekday persons, 2,237,373 legs, 2,758,875
activities.

**Mode is seeded here, and only here.** B2 still carries no mode (§9.2), but a
MATSim plan cannot omit one. A mode is drawn **per tour**, so a car that leaves
home comes home again and `SubtourModeChoice`'s mass conservation holds from
iteration 0. This only works because the P3 chains have several tours a day —
under the P1 chains every agent had exactly one subtour, so a per-tour draw
would have fixed one mode for the whole day.

| | Seeded | HTS 2024/25 |
|---|---:|---:|
| car | 55.7% | 57.5% |
| ride (car passenger) | 18.6% | 21.5% |
| walk | 19.3% | 16.1% |
| pt | 4.0% | 3.4% |
| bike / other | 2.4% | 1.6% |

The seed is set near the HTS aggregate because starting iteration 0 far from the
observed point wastes iterations without changing where the model converges.
**Seeding near HTS is not matching it** — mode share is a P4 calibration target
(§2.4), and this is the initial condition the calibration starts from. Assumed,
swept: car share among car-available 0.68–0.86, PT share among car-unavailable
0.05–0.20.

### What does not survive the C1 → MATSim translation

C1 is a nested-logit specification; MATSim scores with a Charypar–Nagel utility.
Three things have no representation and are recorded rather than dropped
quietly:

| C1 element | Fate |
|---|---|
| `nesting_coefficient_pt = 0.65` and the nest structure | **Not representable.** MATSim's mode choice is a co-evolutionary search, not a closed-form nested logit; there is nowhere to put a nest coefficient. |
| Per-purpose value of time (commute 18.6, work-business 55.4 AUD/h) | **Collapsed** to a trip-weighted **16.96 AUD/h**, because MATSim scores per mode, not per purpose. A scenario that shifts the purpose mix will not shift the value of time with it. |
| `beta_crowding_seated` / `_standing` | **Not enabled.** Capacity-dependent PT scoring needs an explicit extension. |

The identity used is the conventional
`VOT = (performing − traveling_mode) / marginalUtilityOfMoney`, with
`performing = 6.0` utils/h (assumed; the whole scoring scale is relative to it)
and `marginalUtilityOfMoney = 1.0` utils/AUD as the definitional anchor.
`utilityOfLineSwitch` carries the swept transfer penalty (§8.1).

### The one-build constraint, discharged structurally

Every feed's mapped schedule carries all three day types at once — S2 has 1,714
routes, 1,231 WEEKDAY + 291 SAT + 192 SUN, and 4,269 departures against 2,188
weekday GTFS trips. **Running an unfiltered schedule would put roughly twice the
real PT supply on the network.** The day-type filter therefore operates on the
*already mapped* schedule, selecting `transitRoute` ids by their day-type token.
Verified on S2: all **1,714** route link sequences byte-identical to the source,
the stop→link map for all **4,174** facilities unchanged, and the three day types
partition the route set exactly. No feed is ever re-mapped, so §3.5's constraint
holds by construction rather than by discipline.

**The run network is not `networks/matsim/variants/`.** Those are patched over
the *base* network, which has no mapped transit links, so they are a reference
artefact and not runnable. A scenario runs on its own mapped
`schedules/<S>/network.xml.gz` — 151,594 links against the base 157,678, with
928 artificial transit links added and 7,012 pre-mapping rail placeholders
removed, **all of them pt-mode; no car link is lost**. The E1 road variant is
re-applied on top by `osm:way:id`, which every link carries, and reproduces the
base build's patch counts exactly (54 lanes / 59 kerbside / 8 banned turns for
the full-capacity variant).

#### Three defects this stage caught

1. **The day-type token is not always dot-delimited.** The era and scenario
   feeds namespace it `nisc001:WEEKDAY.2302960`, but the S1 shuttle and S3 BRT
   that `build_scenario_schedules.py` generates use `S1SHUTTLE_WEEKDAY_0_1`.
   Matching only the dotted form dropped both from *every* day type — which
   would have run **S1 with no shuttle and S3 with no BRT**, each scenario
   without the intervention it exists to test. Caught by a package check
   asserting that the split partitions the mapped schedule exactly.
2. **Banned-turn removal was network-wide.** E1's "no banned turns" applies to
   the corridor without the tram; a first cut stripped `disallowedNextLinks`
   from the whole network, deleting **1,235** observed restrictions instead of
   **8**, and quietly handing four scenarios a freer road network.
3. **`gzip.open` writes the wall clock into the gzip header**, so two builds of
   identical content produced different bytes and different manifest digests -
   a direct breach of the determinism rule, and one that would have made every
   rebuild look like a data change. `src/build/det_io.py` pins the header mtime
   to 0; a repeat build of the plans and all 30 run-input sets is now
   byte-identical.

### Assumed values introduced here

**None of these is Newcastle-specific** — they are properties of MATSim's
scoring and replanning formulation, not observable quantities of this study
area, so there is nothing local to derive them from. All are swept.

| Value | Assumed | Sweep | Why |
|---|---|---|---|
| Seed mode split | see table above | car 0.68–0.86, PT 0.05–0.20 | Initial condition for co-evolution; P4 moves it. The *blend* is positioned against the observed HTS mode share. |
| `performing` | 6.0 utils/h | 4.0–8.0 | Conventional MATSim value; the whole scoring scale is relative to it. |
| `monetaryDistanceRate` car | −0.00018 AUD/m | −0.00025 to −0.00012 | Fuel and tyres only, not standing costs: a mode choice within the day does not re-decide car ownership. Varies with national fuel prices, not with Newcastle. |
| Typical activity durations | home 12 h, work 8 h, education 6 h, shopping 1 h, other 2 h, business 1 h | ±25% | MATSim scoring needs a typical duration per activity type. |
| `SubtourModeChoice` weight | 0.10 | 0.05–0.20 | The replanning weight that governs how far the co-evolution can move mode share. Innovation is switched off for the last 20% of iterations. |

## 9.4 The assembled run inputs did not load (P4 stage 0)

P3 delivered 30 scenario × day-type input sets and verified them thoroughly *as
data*: the day-type split partitions the mapped schedule exactly, all 1,714 route
link sequences are byte-identical to source, the stop→link map is unchanged, no
stop dangles, and the E1 patch reproduces the base build's counts. Every one of
those statements is true. **None of the 30 sets could be loaded by MATSim**, and
no check noticed, because every check treated the artefacts as tables to be
audited rather than as files a simulator has to read.

Found by launching one, not by re-reading the code. Three independent defects:

| # | Defect | Reach | Symptom |
|---|---|---|---|
| 1 | The day-type filter round-trips the schedule through `ElementTree`, which **drops the doctype** | **all 30** schedules | MATSim selects its reader *from* the doctype; without it the parse fails at line 2 with a null-delegate `SAXParseException` |
| 2 | Dropping two thirds of the routes **orphans the stop facilities and `minimalTransferTimes` relations only they used** — 113 facilities and 42 relations on S2/WEEKDAY, 2,193 and 1,034 on S0/SAT | **all 30** schedules | `SwissRailRaptorData.calculateRouteStopTransfers` dereferences a null array. The schedule stayed *smaller* but stopped being *referentially closed* |
| 3 | The kerbside patch appends a **second `<attributes>` block** to links that already have one — and every mapped link has one, since `osm:way:id` is how the patch finds it | **6 of 10** run networks: S0, S1, S2c 59 links each, S4 302, S5 498, S6 59 | `More than one instance of element <attributes>`; the network DTD rejects it. S2/S2a/S2b/S3 escaped only because `net_base2026` is the observed network and carries no patch rows |

Defect 3 is the one that would have been hardest to catch late: it strikes
exactly the six scenarios that carry an E1 road change, i.e. every counterfactual
that the corridor comparison depends on, and leaves the four that don't alone.

**Fixed** in `build_matsim_run_inputs.py`: the doctype is written back
explicitly, the filter prunes facilities and transfer relations down to what the
surviving routes serve, and `set_link_attribute()` writes into a link's existing
`<attributes>` block instead of adding another. The 30 sets rebuild
byte-identically, the patch counts are unchanged (54 lanes / 59 kerbside /
8 banned turns on the full-capacity variant), and all 30 now load and run in
MATSim. `check_package.py` 556 → **657 checks**: doctype, orphaned facilities,
dangling transfer relations and duplicate `<attributes>` are now asserted for
every one of the 30 sets.

**The lesson worth keeping:** "the artefact is internally consistent" and "the
tool can read the artefact" are different claims, and P3 only tested the first.
Nothing here changes a modelled value, a target or a falsification condition.

## 9.5 What a run costs on one workstation — measured

Measured, not estimated: S2 × WEEKDAY, nested deterministic subsamples (1% ⊂ 10%
⊂ 25%, blake2b on person id, seed 20260810), 16 threads, `ride` teleported,
peak working set sampled every 2 s. **24 cores, 63.5 GiB, no useful GPU** —
MATSim will not touch one. The probe was driven by a throwaway script; the
committed harness that reproduces these numbers lands with `src/run/`, which is
still empty.

| Sample | Persons | Iteration 0 | Steady per-iteration | Peak resident |
|---|---:|---:|---:|---:|
| 1% | 5,209 | 13.2 s | **9.8 s** | 9.8 GiB |
| 10% | 52,758 | 43.4 s | **29.9 s** | 18.4 GiB |
| 25% | 131,291 | 112.2 s | **~64 s** | 31.5 GiB |

Both curves are close to linear in the sample fraction with a large fixed cost —
the run network (**151,592 links / 70,146 nodes** for S2, of which 143,891 carry
car and ride) and the raptor transfer table (**970,047 entries** for S2/WEEKDAY)
are paid once regardless of how many agents exist:

- time ≈ **3.1 s + 268 s × fraction** per iteration → **~4.5 min/iteration at 100%**
- memory ≈ **9.6 GiB + 87 GiB × fraction** → **~97 GiB at 100%**

**A 100% weekday run does not fit in 63.5 GiB.** The practical ceiling on this
machine is about **40%** (≈45 GiB), and 25% is the largest fraction that leaves
room to do anything else. Demand is built at 100% so this stays a run-time
choice (§9.2), and this is that choice being made on measurement.

Consequence for the load recorded in `STATUS.md`: 1,400 sweep runs + 300
headline runs, each of which is really three day types, is 5,100 run-days. At
25% that is ~3.6 h each — **about 765 days of wall clock**. The shortfall is
roughly three orders of magnitude, so it is not closeable by tuning; it is
closeable only by cutting sweep breadth, replications and day types. Sample
fraction is the *weakest* of the available levers, because cost is sublinear in
it and precision is not.

## 9.6 Mode choice was not choosing, and the seed is now uninformed (P4 stage 0)

Three things about the shipped configuration only became visible by running it.

**Defect 4: `ride` was declared a network mode that no link permitted.** The
config set `qsim.mainMode=car,ride` and `routing.networkModes=car,ride`, but the
mapped network permits `car`, never `ride`. MATSim reports
`checking 0 nodes and 0 links for dead-ends` for mode `ride` and then throws in
`PrepareForSim`. **The shipped config could not run even after §9.4's three
schedule and network defects were fixed** — this is the fourth, and it lived in
the config rather than in the data, which is why the load test in §9.4 did not
see it: that test overrode the mode handling in order to exercise the artefacts.

**Defect 5: `ride` was not in MATSim's choice set, so its share was an output
equal to its seed.** `subtourModeChoice` was never configured, so MATSim's
default applied: `modes=car,pt,bike,walk` with
`behavior=fromSpecifiedModesToSpecifiedModes`. A subtour whose mode is `ride` is
not in the specified set, so it is never offered an alternative — an absorbing
state. Measured over 30 iterations at 1%, `ride` sat at **0.18311 in every single
iteration**, to five decimal places. **18.6% of legs were an input wearing the
costume of a result**, and the HTS vehicle-passenger target (20.6%) could only
ever have been "met" by whatever the seed happened to be.

**Defect 6: car availability was ignored.** `considerCarAvailability` defaults to
`false`, so an agent B1 records as having no car could be assigned one by mode
choice. B1 synthesises car availability and the seed was drawn conditional on it;
the choice model then discarded the structure.

### What changed

| | Was | Now |
|---|---|---|
| `qsim.mainMode` | `car,ride` | **`car`** — a car passenger is not a second vehicle |
| Link `modes` | `car` | **`car,ride`** on 143,891 links, so `ride` is *routed* on the road network and gets a congested travel time rather than a beeline guess |
| `travelTimeCalculator` | default (per-mode) | **`separateModes=false`, `analyzedModes=car`** — no ride vehicle is ever observed, so ride reads the car travel times instead of falling back to free speed |
| `subtourModeChoice.modes` | default `car,pt,bike,walk` | **`car,ride,pt,bike,walk`** |
| `subtourModeChoice.considerCarAvailability` | default `false` | **`true`** |
| Seed mode split | positioned near the HTS aggregate | **uninformed**, uniform over the modes each person can use |

Verified: the shipped config now runs unmodified, the ride subnetwork has 143,891
links, and `ride` moves — 0.1941 → 0.1975 → 0.1983 → 0.2048 over the first four
iterations, where before it did not move at all.

**Ride occupies no road capacity.** It is routed but teleported, so a car
passenger adds no vehicle. That is right when the driver is separately modelled
and wrong when they are not, and B2 does not generate escort trips, so modelled
link volumes are biased *low* against an observed all-vehicle count. Together
with the freight the model omits, this is why the traffic-count comparison
carries explicit corrections (§12.2a) rather than a fitted constant.

### The seed is now uninformed

The P3 seed was positioned so the blended share landed near the HTS aggregate
(car 55.7 against 57.5, pt 4.0 against 3.4), on the reasonable ground that
starting far from the observed point wastes iterations. That is a fine
convergence aid and a poor initial condition for a calibration whose target *is*
the HTS mode share.

The seed is now **uniform over the modes each person can use**, conditioned only
on B1 car availability — a population attribute, not a behavioural prior.
Realised: car **14.3%**, and about 21.4% each for bike, pt, ride and walk,
against an HTS car share of 59%. It is deliberately a bad guess.

| | Uninformed (default) | Informed (P3, retained) |
|---|---:|---:|
| car | 14.3% | 55.7% |
| ride | 21.4% | 18.5% |
| walk | 21.4% | 19.3% |
| pt | 21.5% | 4.0% |
| bike | 21.4% | 2.5% |

The informed seed is **kept**, selectable with
`build_matsim_plans.py --seed-mode informed`, so that "the answer does not depend
on the initial condition" is a claim that can be **tested by running both** rather
than asserted. §9.7 reports that test.

## 9.7 The seed test, and a model that does not converge (P4 stage 0)

Two 1% runs of 250 iterations, S2 × WEEKDAY, identical in every respect except
the initial mode draw. 2,205 s and 2,419 s wall, run concurrently.

| Iteration | Uninformed car / ride | Informed car / ride |
|---:|---|---|
| 0 | 0.143 / 0.223 | 0.564 / 0.183 |
| 50 | 0.182 / 0.401 | 0.374 / 0.375 |
| 100 | 0.178 / 0.508 | 0.291 / 0.491 |
| 150 | 0.166 / 0.573 | 0.241 / 0.561 |
| 200 | 0.153 / 0.619 | 0.202 / 0.609 |
| **250** | **0.147 / 0.664** | **0.201 / 0.649** |

**Finding 1 — the seed's influence decays but has not vanished.** The two starts
differ by **42.1 pp** on car share; at iteration 250 they differ by **5.4 pp**
(ride 1.5 pp, pt 1.0 pp, walk 1.1 pp, bike 1.8 pp). So 87% of the initial gap
closes, and the remaining 5.4 pp cannot be attributed to the seed rather than to
finding 2. The defensible statement is **"the seed's influence decays strongly and
is not yet eliminated at 250 iterations"** — not "the seed does not matter".

**Finding 2 — the model has not converged, and is not close.** MATSim switched
innovation off at iteration 200 (`fractionOfIterationsToDisableInnovation=0.8`),
after which no new plans are created and agents only re-select among the five
they already hold. Ride share still moved **0.619 → 0.664** over those last 50
iterations. A system that keeps drifting after its search is switched off has not
relaxed. **`lastIteration=100` is not merely unvalidated; it is far too low, and
250 is also too low.** The default is left at 100 rather than replaced with
another number that cannot be justified, and `check_package.py` now emits a
standing warning to that effect on every run of the suite.

**Finding 3 — the attractor is wrong, and it is a specification problem.** Both
runs converge toward **ride ≈ 65%, car ≈ 15–20%**, against an HTS calibration
target of ride 20.6% and car 59.0%. In MATSim, `ride`:

* has **no driver-availability constraint** — nothing requires a driver to exist,
  so every agent can be a passenger simultaneously;
* is charged **half** the distance cost of car (−9e-05 against −0.00018 AUD/m),
  on a cost-sharing assumption nothing else in the model represents;
* consumes no road capacity, so it never congests itself.

Against all that, the only thing restraining it is `asc_car_passenger = −0.85`.
Findings 2 and 3 are probably the same fact: a mode that strictly dominates
drives the co-evolution toward a corner, and corner solutions relax slowly.

**This runs directly into §8.5.** Pulling ride from 65% to 20.6% by fitting
`asc_car_passenger` is exactly the ASC absorption proposal §9 names as the
primary threat to validity, and §8.5 forbids it without a departure logged
**before results are seen** — which is now. The candidates, and none is chosen
here:

1. **Charge `ride` the same distance cost as car.** A passenger's trip burns the
   same fuel; halving it models an intra-household transfer the rest of the model
   does not have. A specification fix that leaves the ASCs alone and keeps §8.5
   intact.
2. **Estimate the ASCs on era 3 (2018) and hold them fixed**, which is what §8.5
   actually prescribes and what has never been attempted. Note that era 3
   predates the light rail, so it cannot identify `asc_lr` at all.
3. **Calibrate `asc_car_passenger` freely**, logging the departure from §8.5 here
   first.

Nothing downstream of this should be built until it is settled, because the
choice determines what the calibration loop is allowed to move.

## 9.8 The ride constant is constrained to observed vehicle occupancy

§9.7 left three options open and none chosen. This is the resolution, and it is
the second branch §8.5 already permits — *"or constrain them and report the
constraint"* — with the constraining quantity measured rather than picked.

### The model produced a physically impossible car

At `asc_car_passenger = −0.85` the model settled at **4.52 ride legs per car
leg**: an implied **5.52 people per vehicle**. A car has about five seats. The
observed Newcastle figure, from the HTS vehicle driver and vehicle passenger trip
counts, is **1.3503** — and it is stable:

| Financial year | Driver trips | Passenger trips | Occupancy |
|---|---:|---:|---:|
| 2016/17 | 334,000 | 106,000 | 1.3174 |
| 2017/18 | 303,000 | 86,000 | 1.2838 |
| 2018/19 | 337,000 | 84,000 | 1.2493 |
| 2019/20 | 348,000 | 99,000 | 1.2845 |
| 2022/23 | 335,000 | 132,000 | 1.3940 |
| 2023/24 | 317,000 | 109,000 | 1.3438 |
| **2024/25** | 334,000 | 117,000 | **1.3503** |

Both quantities are ratios of two published counts. `src/calibrate/measure_mode_constraints.py`
derives them into [`params/C4_mode_constraints.json`](params/C4_mode_constraints.json);
the sweep is **1.2493–1.3940**, the observed spread across all seven survey years
in the file, not an interval anyone chose.

### First, a double charge removed

`ride` was charged **half** the car distance rate — −9e-05 against −0.00018. That
half was typed in, not derived, and it double-counts: a vehicle's operating cost
is paid once, and at an occupancy of 1.35 charging both driver and passenger
makes the model's aggregate vehicle operating cost about 1.35× the real one. The
only value derivable from the data is **zero** — the driver, who is separately
modelled, already carries it.

This makes `ride` free at the margin, and that is the point: it moves the whole
burden of pinning ride's share onto one constant, in the open, instead of
splitting it between a constant and a cost share that was invented.

### Then the constant, solved against the observed ratio

`src/calibrate/solve_asc_ride.py` runs candidate values of `asc_car_passenger`
and interpolates on log(ride ÷ car legs) — the scale on which a logit constant
acts linearly — to the observed passenger:driver ratio of **0.3503**. It reads
`C4` and its own runs' `modestats.csv`; **it never opens the validation targets
at all**, so it cannot touch a holdout row even by accident.

### Why this is not ASC absorption

Proposal §9 names ASC absorption as the primary threat: *calibrating mode
constants to observed patronage fits away the effect under test*. The distinction
that makes this admissible:

* the constrained constant is **car passenger**. `asc_lr`, `asc_bus` and
  `asc_rail` stay at their §8.5 priors and are not touched;
* the constraining quantity is **vehicle occupancy** — how many people fit in a
  car — not light rail patronage, not PT mode share, not any quantity the
  hypotheses in proposal §3 turn on;
* it is a **physical** constraint. The unconstrained model was not merely fitting
  badly, it was putting 5.5 people in a car.

The solved value is reported as a constraint, never presented as an estimate of
Newcastle's taste for being a passenger, and both the value and the observed
range it was solved against travel with every result that uses it.

### What this does not fix

The solve is run at a fixed 250-iteration protocol, which §9.7 shows is **not
equilibrium**. It must be re-solved once the iteration count is settled, and the
value below is provisional until then. Whether constraining ride also cures the
non-convergence — the two are plausibly the same problem, since a dominating mode
drives the co-evolution to a corner and corners relax slowly — is measured by the
same runs.

## 9.9 The with-tram scenario had no tram on a weekday (P4 stage 1)

Found while building `src/analyse/extract_metrics.py`: the extractor reported
**zero light rail boardings** for S2 × WEEKDAY. Not few — zero.

`S2.zip` carries 550 light rail trips, of which **252 are weekday** on a
`service_id=WEEKDAY` running Monday to Friday. The mapping keeps all 550. But
the mapped schedule has exactly **two** light rail `transitRoute`s, named
`lightrail:SAT.69659…` and `lightrail:SUN.72626…`, and **each carries 275
departures: 74 Saturday, 75 Sunday and 126 weekday.**

**pt2matsim groups trips into a `transitRoute` by stop sequence, not by
service.** A route is therefore *not day-type homogeneous*, and the day-type
filter keyed on the **route id**. So:

* every weekday run dropped both light rail routes — the **with-tram scenario
  had no tram** — and a weekday S2-versus-S0 comparison would have measured the
  effect of nothing at all;
* Saturday and Sunday each received all 275 departures, roughly **3.7×** the
  real light rail service.

It is not confined to the light rail. Across S2's 1,714 routes:

| | |
|---|---:|
| Routes whose departures span more than one day type | **233 (13.6%)** |
| Departures placed in the wrong day type | **1,261 of 4,269 (29.5%)** |
| True weekday departures vs delivered | 2,139 vs **1,747** (18% short) |
| True Saturday vs delivered | 1,128 vs **1,330** (18% over) |
| True Sunday vs delivered | 1,002 vs **1,192** (19% over) |

### Why the existing check passed

§9.3 called the one-build constraint "discharged structurally" and
`check_package.py` asserted that the split **partitions the route set exactly** —
1,231 + 291 + 192 = 1,714. That was true, and it was the wrong invariant.
Partitioning routes is not partitioning service when a route is not
day-type homogeneous. The check confirmed an arithmetic identity while 29.5% of
the service was in the wrong place.

### The fix

`split_schedule` now filters **departures** by their own day token and keeps a
route if it retains any, so a route named after a Saturday trip still carries its
126 weekday departures into the weekday run. This still operates on the
already-mapped schedule — no feed is re-mapped, no link sequence is touched — so
§3.5 holds exactly as before.

Verified: light rail now has **252 weekday, 148 Saturday, 150 Sunday**
departures, matching the GTFS calendar exactly, and every scenario's departures
partition its source total precisely.

Two checks replace the one that passed:

1. the split partitions **departures** exactly, and every departure is kept in
   exactly one day type and dropped from the other two;
2. **the intervention is present with departures in every day type** — per
   scenario, the light rail line for S2/S2a/S2b/S2c/S4/S5, the shuttle for S1,
   the BRT for S3, and correctly nothing for the S0 and S6 counterfactuals. A
   generic partition count cannot see a missing tram; this can.

**Nothing that had been run on the old inputs was kept.** The three
`asc_car_passenger` candidate runs in flight were discarded rather than reported,
because a solve calibrated on a network with no weekday tram is a solve of a
different model.

---

## 9.10 Is the 1% sample representative? Partly — and the answer splits (P4 stage 2)

Every P4 behavioural result had been measured at **1%** — 5,209 people, 0.85% of
the population. Two runs, identical but for the sample fraction, 250 iterations,
8 threads, S2 × WEEKDAY, uninformed seed, shipped constants.

| Mode | 1% (5,209) | 10% (52,758) | difference | HTS target |
|---|---:|---:|---:|---:|
| car | 0.1223 | 0.1913 | **+6.91 pp** | 0.590 |
| ride | 0.7213 | 0.7190 | **−0.23 pp** | 0.206 |
| pt | 0.0395 | 0.0044 | **−3.51 pp (9×)** | 0.038 |
| walk | 0.0315 | 0.0123 | −1.93 pp | 0.134 |
| bike | 0.0854 | 0.0730 | −1.24 pp | 0.032 |

**1. Ride dominance is a property of the model, not of the sample.** The two
trajectories track within 0.006 at *every* checkpoint — 0.2228/0.2167 at
iteration 0, 0.4034/0.4011 at 50, 0.6208/0.6192 at 150, 0.7213/0.7190 at 250.
Ten times the population reproduces the same curve. **The §9.7 finding is
confirmed at scale and is a specification problem**: `ride` has no
driver-availability constraint, consumes no road capacity, and since §9.8
carries no distance cost either, so only `asc_car_passenger` restrains it. At
0.7213 against a 0.206 target it is 3.5× observed, and the model puts 5.9 people
in every car.

**2. Non-convergence is likewise a model property.** Innovation stops at
iteration 200. Between 200 and 250, with no new plans being created, `ride` rose
**+0.0461 at 1% and +0.0474 at 10%** — the same drift at both fractions. This is
not slow relaxation toward an equilibrium; it is a corner still being approached
when the run stops.

**3. But 1% is NOT representative for `car` or `pt`, and that invalidates a hope.**
Car differs by 6.91 pp and PT by a factor of nine. Any statement about car or PT
*levels* measured at 1% does not transfer, so calibration against the mode-share
targets cannot be done at 1%. The hope that sweeps could run cheaply at 1% and
only headline runs at 25% is therefore **not available for car or PT**, which is
a direct cost to the §9.5 budget problem.

**4. The mechanism for the car/PT divergence is NOT established, and is recorded
as open rather than guessed.** Two candidate explanations were checked and
neither survives:

- *Transit capacity.* The fleet is seats-only (`standingRoomInPersons=0`
  throughout) and seats scale with the fraction, flooring at 1 below ~1.5%
  (issue #12), so 1% carries ~43% more PT capacity per capita than proportional.
  But at 10% the timetable offers roughly **20× more boarding capacity than the
  model uses**, so capacity is not binding and cannot explain a nine-fold
  collapse.
- *Small-sample spillback.* Ruled out separately: MATSim enforces
  `storageCapacityFactor == flowCapacityFactor` (§15), and the storage floor
  gives 1% *more* link storage than proportional, which would make car more
  attractive at 1% — the opposite of the observed direction.

**An unreconciled vehicle capacity, found while checking the above.** The MATSim
fleet gives the light rail **180** seats and no standing room. §4.1 records the
CAF Urbos 100 with a **published maximum capacity of 270** and an assumed
`capacity_seated` of **60**. 180 reconciles with neither. Because the fleet has
no standing room, the C1 crowding multipliers (1.00 seated / 1.45 standing) can
never apply to any vehicle in any scenario.

**What this settles for sequencing.** The dominant distortion is a specification
error that scale does not cure. Calibrating, sweeping or coupling SUMO to a
demand model in which 72% of legs are car passengers would propagate that error
into every downstream number, so the specification comes first.

---

## 9.11 `ride` requires a driver — a logged departure under §8.5 (P4 stage 2)

§9.10 established that ride dominance is specification, not sampling. This is the
fix, and §8.5 requires it to be recorded **before results are seen**, which is now.

**What was wrong.** MATSim's standard treatment lets any agent be a car passenger
on any trip. Riding as a passenger should only be available when another agent is
driving the same trip at the same time; it is usually modelled without that
requirement and teleported. That is the field's default weakness, not a
misconfiguration here.

**What was rejected.** Solving `asc_car_passenger` harder. That is ASC absorption,
the primary threat to validity in proposal §9: the constant would be doing the job
the missing rule should do, and would misbehave the moment a scenario changes —
which is the entire experiment.

**What was implemented.** A per-person availability flag, DERIVED from B1: a person
may be a car passenger only if their household holds a vehicle **and** contains at
least one *other* licence holder. **22.1% of the weekday population (115,034 of
521,502) may not ride.** Two pieces were needed, and the first alone did nothing:

1. `src/java/wickham/RideAvailabilityModesCalculator.java` — core MATSim honours
   `carAvail` but has no equivalent for `ride`, and `subtourModeChoice.modes` is
   global, so a custom `PermissibleModesCalculator` is the smallest structural fix.
   Bound by `wickham.WickhamControler`.
2. **The seed had to be fixed too.** `PermissibleModesCalculator` governs only
   *new* mode choices — it never strips a mode from a plan an agent already holds.
   Seeding a person who cannot ride with `ride` leaves an illegal plan in memory
   that `ChangeExpBeta` re-selects indefinitely. Measured: **4,723 illegal ride
   legs survived 30 iterations** with the calculator alone. After seeding
   correctly: **0**.

| | before | after |
|---|---:|---:|
| Illegal ride legs at iteration 30 | 4,723 | **0** |
| Seed ride share | 0.2228 | 0.1712 |
| Ride at iteration 25 | 0.3098 | **0.2548** |

**Toolchain.** The pinned digests are UNCHANGED: this adds a compiled artefact
beside the shaded jar rather than replacing it. It builds from committed source
with the pinned javac 25.0.4 — no Maven — which is what makes it reproducible.

**This is necessary and probably not sufficient, and that is stated now rather
than discovered later.** The constraint lowers the ceiling to the 77.9% who may
ride; the unconstrained attractor was 0.72, so it does not bind hard at the
corner. Ride was still climbing at iteration 30 (0.2787). Whether it now settles
near the observed 0.206 is unmeasured and needs a converged run.

**Residual limitation, stated not hidden.** This makes ride available or not per
*person*. It does not bind a passenger to a specific driver at a specific time, so
the model can still produce more passengers than there are drivers in any given
hour. That is the socnetsim joint-plans contrib (Dubernet & Axhausen, STRC 2013;
Transportation 2015), which is **absent from the pinned jar** and out of scope.

---

## 9.12 The ride constraint is necessary and not sufficient, and 1% is unusable (P4 stage 3)

§9.11 predicted the constraint would not bind at the corner and asked for a
converged run to settle it. Two runs of S2 × WEEKDAY, 250 iterations, uninformed
seed, **8 threads** (matching the §9.10 baselines exactly — thread count is part
of the run identity), driven by committed overlays and the declared pipeline
`run_matsim.py` → `extract_metrics.py` → `fit.py`. **Neither is a result**: §9.7
shows 250 iterations is measurably short of relaxation.

| | 1% (5,209 persons) | 10% (52,758 persons) |
|---|---:|---:|
| wall / median iteration | 2,636 s / 9.94 s | 8,176 s / 27.76 s |

**Mode share, Newcastle LGA — the reportable quantity** (§12.1), not the
five-LGA aggregate the seed was positioned against:

| | 1% | **10%** | HTS target |
|---|---:|---:|---:|
| Vehicle driver | 16.01 | **30.85** | 59.0 |
| **Vehicle passenger** | 61.06 | **50.94** | **20.6** |
| Public transport | 0.62 | 0.99 | 3.8 |
| Walk only | 1.59 | 0.80 | 13.4 |
| Other | 20.73 | 16.43 | 3.2 |
| mean absolute error | 23.19 pp | **17.43 pp** | |
| passengers per driver | 3.8140 | **1.6512** | 0.3503, range [0.2493, 0.394] |

**The constraint did the largest single piece of work any P4 change has done, and
it is still not enough.** On the five-LGA quantity §9.10 measured, ride fell from
0.7213 / 0.7190 to 0.6105 / 0.5592 and car rose from 0.1223 / 0.1913 to
0.2057 / 0.2743. At 10%, ride still lands at **2.5× the observed 20.6%** and
vehicle occupancy at **4.7×** the observed passenger:driver ratio, outside the
seven-year observed spread. §9.11's own prediction is confirmed: the ceiling is
0.779 and the model settles far below it, so the constraint never binds where it
would matter.

### Why the 1% column must not be read behaviourally

**1% does not deliver the simulated day.** Counting `stuckAndAbort` in each run's
own events:

| | 1% | 10% |
|---|---:|---:|
| car legs aborted at the 30 h horizon | **1,032** | **4** |
| walk / pt / bike / ride aborted | 19 / 41 / 1 / 0 | 253 / 183 / 9 / 2 |
| PT passengers who boarded and never alighted | **380** | **0** |

Every abort at 1% occurs at exactly 108,000 s — `qsim.endTime` — so these are
agents still travelling when the day ends. A tenfold population increase makes
car non-completion fall **258-fold**, which is not proportional to demand.

The mechanism is **flow**-capacity granularity, a different quantity from the
storage argument §9.10 correctly ruled out. `RUN.sample.flow_capacity_factor` is
derived to equal the sample fraction, so at 1% an 1,800 veh/h link discharges
**18 veh/h — one vehicle every 200 s**, and two sampled cars arriving inside that
window queue behind pure arithmetic with no congestion present. At 10% the same
link releases one every 20 s. Storage and flow are pinned equal (§15), so this
cannot be separated by configuration, only by fraction — which is what these two
runs do. It is the first mechanism offered for the §9.10 car/PT divergence that
survives measurement, after four died, and it explains the direction too: a fifth
of car legs missing from the completed-trip denominator inflates every other mode.

It also explains a gap that would otherwise look like a defect in the metric
extractor. `modestats.csv` records the mode agents **chose** (pt 4.69% at 1%);
`output_trips` records trips that **completed** (pt 0.357%). Both are correct.
Only the second is a mode share, and at 1% the simulation is not producing one.

**Consequence.** Every P4 behavioural measurement taken at 1% carries this
artefact, including the §9.7 seed test and the §9.10 fraction diagnostic. The
§9.10 conclusion nevertheless **stands**. It was nearly overturned on the apparent
fraction-sensitivity of ride (61.06 → 50.94), and most of that swing is the
artefact rather than sampling. Because a §8.5 departure cannot be un-logged, the
10% reading is being **confirmed at 25% before any specification change is
chosen**; the threshold between 10% and 25% is unmeasured.

### A defect found by computing the first fits, and it flattered the answer

`fit.py` collapsed two different situations into one branch — a station that
resolved to no link, and a station whose links carry a modelled volume of zero —
and emitted the *did not resolve to a link on the run network* reason for both.
Only one of the three affected targets fits that description.

| target | station | observed AADT | modelled | actual situation |
|---|---|---:|---:|---|
| V079 | 55717 Tarean Road (Karuah) | 1,270 | absent | genuinely outside the network (issue 10) |
| V096 | 55839 Raymond Terrace Rd | 11,810 | **0** | links resolve; the model routes nothing over them |
| V113 | 55888 **M1 Pacific Motorway (Wyee)** | **48,016** | **0** | links resolve; the model routes nothing over them |

**A modelled zero is a result, not an unscorable target**, and dropping it removed
the two stations where the model fails hardest from every aggregate — the
inversion of proposal §8 deliverable 3. Corrected: the two conditions carry
separate reasons, a zero is scored at −100% and flagged in
`counts.modelled_zero_stations`. The fit moves from 36 scored / 31 unscorable to
**38 / 29**, counts from 31 stations to 33, and the count error honestly worsens
(10%: mean −72.1% → **−73.8%**, RMSE 20,849 → **21,750**).

**This exposes a modelling gap, not a reporting question.** The model puts **zero
cars on the M1 at Wyee** — a 4,000-capacity, 110 km/h link with an observed 48,016
AADT on the southern study-area boundary. The likely cause is the external tier:
B2 synthesises 5,384 weekday boundary agents and evidently routes none onto the
motorway there. Until that is understood, every boundary-adjacent count is biased
low. Recorded rather than fixed.

### Three values that were governing the model from outside the registry

Found by auditing for literals rather than by a failure, and all three now resolve
through `config/registry/`:

- **`B.counts.station_match_radius_m` (new field, 120 m).** A CLI default in
  `map_count_stations.py` with no provenance and no range, and it decides which
  `road_aadt` targets are scorable **at all** — a lever on the reported fit, not a
  plotting tolerance. Swept 60–120 m on measurement: the largest accepted match is
  119.7 m, so 120 m is exactly binding; at 100 m six of the 116 matched stations
  lose their link and at 60 m twenty-three do. Gated as the build-layer migration
  was — `count_station_links.csv` rebuilds **byte-identical**.
- **`sample_population.SEED`** held its own copy of 20260810 and now resolves from
  `RUN.machine.seed`.
- **`solve_asc_ride.py`** carried five run parameters and the −0.85 prior as
  literals and — found while removing them — **called `run_matsim.run()` with the
  pre-registry positional signature, so it could not execute at all.** It is the
  tool #9 needs, so it was repaired rather than deleted: every run parameter now
  resolves through the registry, the candidate bracket is a required argument on
  the same principle as `--iterations`, and it reads the schema-validated
  `_metrics.json` rather than raw `modestats.csv`. `fit.py` is deliberately still
  not invoked, so it remains structurally unable to reach a validation target.

Two P1 exploratory probes (`src/extract/ckan_probe.py`, `src/extract/s3_list.py`)
were deleted: no docstring, no artefact in the manifest, referenced by nothing.

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

### 12.1 What the 67 calibration targets can actually constrain (P4 stage 0)

The split is 67/143 and stays 67/143. But 67 targets is not 67 pieces of
information, and P4 has to say so before fitting anything to them.

| Block | n | What it can identify |
|---|---:|---|
| `road_aadt` | 34 | Car demand and assignment — **once the values are repaired, see below** |
| `lr_cardtype_share` | 13 | **Nothing.** MATSim has no fare-product dimension, and 31.7% of the mix is `CTP` — contactless payment, an instrument rather than a person attribute, so it is not even decomposable into age bands. Three of the 13 are 0.0 or 0.01 |
| `hts_mode_share` | 12 | Two mutually incompatible vintages: 2018/19 uses `Bus`/`Train`/`Vehicle Driver`, 2024/25 uses `Public transport`/`Vehicle driver`. The base year is 2026, so only the **2024/25 six** apply; `Walk linked` is structurally 0.0 and the remainder sum to 100, leaving **4 free degrees of freedom** |
| `lr_boardings_*` | 3 | V001 and V002 are the **same datum** (3,417/day = 103,892 ÷ 30.4). Both are Mar 2019 – Feb 2020, the pre-pandemic market. Only **V003** (83,753/month, 2025-07 onward) belongs to a 2026 base |
| `bus_boardings_monthly_mean` | 1 | 2019 only. There is **no contemporary bus target** in the pre-registered set, though the package holds the NISC 1 series to Jun 2026 (222,616/month). **Deliberately not added** — see §12.4 |
| `lr_share_of_local_pt_boardings` | 1 | **Nothing new** — it is algebraically V001 ÷ (V001 + V023). This is the 20.8% figure, and it is *not* hypothesis A1's metric (see the note above) |
| `lr_scheduled_runtime` | 2 | Two identical duplicates of a **schedule input**. MATSim runs transit on the schedule, so it reproduces 12.00 min by construction. This is a SUMO corridor target, not a MATSim one |
| `lr_alignment_length` | 1 | Geometry, already satisfied by the network build |

**Effective independent information: about 4 mode-share degrees of freedom, one
contemporary light rail patronage level, and 34 traffic counts.** Any fit
statistic P4 reports must name the targets it was computed over, because "fits
67 targets" would be a much stronger claim than the data supports.

**The mode-share targets are Newcastle LGA; the model is five LGAs.** The fit
has to be computed over trips made by Newcastle-LGA residents, not over the whole
synthetic population. `build_matsim_plans.py` positioned its seed against a
*five-LGA* HTS aggregate (car 57.46 / ride 21.46 / walk 16.14 / pt 3.39), which
is a different quantity from the target (59.0 / 20.6 / 13.4 / 3.8).

### 12.2 The `road_aadt` target values are the mean of incompatible periods

`build_validation_targets.py` filters the RMS counts on classification and
direction but **never on `period`**, then takes the station mean. Each target is
therefore the average of `ALL DAYS`, `AM PEAK`, `OFF PEAK`, `PM PEAK`,
`WEEKDAYS`, `WEEKENDS` and — where present — `PUBLIC HOLIDAYS`: daily totals
averaged together with peak-period counts. It is not a quantity with a physical
meaning.

Station 55710, 2021: true `ALL DAYS` = **50,133** veh/day; recorded target
**33,114**. Across all 119 stations the recorded value is **0.58–0.71×** the true
`ALL DAYS` figure (calibration mean 0.660, holdout 0.656). Because the number of
period rows varies by station it is not even a constant rescaling, so it cannot
be absorbed by a calibration constant.

The raw layer already carries the fix: the `WEEKDAYS` period is present for **all
119** stations, which is the right basis for a weekday run, and `LIGHT`/`HEAVY
VEHICLES` classification exists for 23 of them (weekday heavy share median 6.5%,
range 1.3–15.3%) — a measured handle on the freight the model does not
represent, though only **3 of the 34 calibration stations** have it, so the rest
would have to be modelled and swept.

**Repaired.** `build_validation_targets.py` now filters on `period` and uses
**`WEEKDAYS`**, two-way, all classes — published for every one of the 119
stations, and the basis that matches the day type the model runs. `ALL DAYS` is
carried alongside in `road_aadt_targets.csv` so the weekday choice stays visible
rather than baked in, and the observed `LIGHT`/`HEAVY VEHICLES` counts are
carried per station with a `heavy_share_source` of `observed` (23 stations) or
`not_classified_at_this_station` (96), so the freight the model does not
represent is never silently taken to be zero.

Effect of the repair, measured against the old file: **119 values changed and
nothing else did.** Same 210 targets, same ids, same geographies, same metrics,
**same 67/143 split** — the AADT split rule is structural (`permanent_station` →
calibration, sample station → holdout) and never depended on the value. New
values run 1.43–1.87× the old ones (median 1.64); station 55710, 2021 is now
**53,721 veh/weekday** where it was recorded as 33,114 (and its `ALL DAYS` figure
is 50,133 — a weekday is busier than the all-day average, as it should be).

`check_package.py` now asserts the split **exactly** at 67/143 rather than merely
"both non-empty", asserts that every `road_aadt` target names the period it was
measured over, and asserts the heavy-share provenance label. A target that does
not say what it is a count *of* is not a target.

### 12.2a The heavy-vehicle and unmodelled-vehicle corrections

The model carries no freight and generates no escort trips, so a modelled link
volume is not directly comparable to an observed all-classes count. The
corrections apply **at comparison time**, to the comparison and not to the model,
and are written to [`params/C3_count_comparison.json`](params/C3_count_comparison.json)
by `build_validation_targets.py` rather than left in prose, so the sweep-range
rule can be tested rather than trusted.

| Correction | Value | Range | Basis |
|---|---|---|---|
| Heavy-vehicle share, where the station carries a classified count | the station's **own observed** share | — | 23 of 119 stations (weekday, two-way): median **0.0652**, mean 0.0776 |
| Heavy-vehicle share, where it does not | **0.0652** (median) | **0.0129–0.1529** | The observed range across those 23. Only **3 of the 34 calibration stations** are classified, so this assumed case is the usual one |
| Vehicles per person-trip by car | **1 vehicle per `car` leg, 0 per `ride` leg** | occupancy **1.2493–1.3940** | Derived, not assumed. HTS observes 1.3503 persons per vehicle (§9.8), i.e. **vehicle trips = driver trips**: passengers ride in vehicles that are already counted. So the modelled vehicle count is the `car` legs alone, and a `ride` leg correctly adds none — *provided* the modelled ride:car ratio matches the observed passenger:driver ratio, which is what §9.8 constrains it to |

The third replaces what an earlier draft of this section left as a bare 0–1
interval for "the share of ride legs whose driver is not otherwise modelled".
That framing was wrong: the HTS occupancy figure settles it. Because observed
vehicle trips *are* driver trips, teleporting `ride` is the correct treatment for
a count comparison, and the residual error is not an unknown share but the gap
between the modelled and observed passenger:driver ratio — which is measurable,
and is the thing §9.8 pins. What remains genuinely unmodelled is the **escort
trip**: B2 generates none, so a driver making a trip solely to carry someone else
is absent from both the `car` legs and the counts' explanation. That is a stated
limitation, not a fitted parameter.

Both corrections must be reported with the fit, never folded silently into a
calibrated constant.

### 12.3 The AADT holdout is a 2008–2010 snapshot

Survey years behind the traffic-count targets:

| Split | n | Years |
|---|---:|---|
| Calibration (permanent stations) | 34 | 2014×2, 2015×2, 2016×4, 2017×2, **2018×18**, 2020×3, 2021, 2024, 2025 |
| Holdout (sample stations) | 85 | **2007×2, 2008×21, 2010×62** |

Every holdout traffic count is at least fifteen years old, and they are 85 of the
143 holdout targets. The holdout remains untouched and unpeeked, but it should be
described for what it is: a 2008–2010 traffic snapshot plus stop-level Opal, not
a contemporary test set.

### 12.4 A contemporary bus target was considered and rejected

The only bus patronage target in the pre-registered set is Mar 2019 – Feb 2020
(395,539/month), i.e. pre-pandemic, while `bus_monthly_series.csv` runs to
Jun 2026 (222,616/month). Adding the current figure was considered — the timing
would have been legitimate, since nothing has been run and an amendment declared
before the first result is not goalpost-moving.

**It was not added, because it would identify nothing.** MATSim's scoring
collapses every public transport service into a single mode `pt` with a single
alternative-specific constant (§9.3 — bus, light rail and heavy rail have no
separate `modeParams`). There is therefore no parameter in the model that a bus
patronage level could pin down which the light rail level and the PT mode share
do not already pin down; a fourth PT aggregate would add a row to the fit
statistic and no information to the fit. Amending a pre-registration for that
trade is a bad bargain.

The contemporary figure will instead be reported as a **labelled post-hoc
diagnostic** alongside the calibration, clearly outside the 210. The
pre-registered set stays at 210 targets, 67/143.

If a later change gives bus and light rail distinct scoring constants — which
would require a MATSim mode-vehicle extension, not a config edit — this decision
should be revisited, because at that point the bus level *would* be identifying.

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
11. **Journey-to-work origin-destination table** (ABS: SA2 usual residence ×
    SA2 place of work) — the package holds the place-of-work side (`W01A…`,
    jobs *by* SA2) but not the origin-destination pairing, which is what would
    settle `EXTERNAL_INTERACTION_RATE` (§9.2) instead of sweeping it. It is a
    standard ABS TableBuilder extract, not a formal request.
12. **A day-of-week travel split** — the HTS LGA tables have none, so the
    Saturday:Sunday division within the weekend is the last assumed part of the
    day-type shape (the weekday/weekend ratio itself is now measured from RMS
    traffic counts, §9.2).

---

## 15. The input registry — every controllable value, declared (P4)

Proposal §8.1 requires that *"every parameter chosen without direct empirical
support must be recorded with its rationale and its sweep range."* Until now that
was a discipline applied to `DECISIONS.md` prose and to `params/C1–C4`, while the
values the model actually ran on lived in **316 module-level constants across 45
scripts**, a 110-parameter MATSim config per run set, and a handful of CLI
defaults. One of those 316 carried a machine-readable `source` label. Eighteen
carried a sweep.

`config/registry/` now declares **142 fields** — every value the model consumes
that is not read from an immutable raw download — each with its units, its
provenance, and either a sweep range or an explicit rule holding it fixed.
`src/registry/` resolves them; `docs/CONFIG_REFERENCE.md` is generated from them
and cannot drift; `check_package.py` tests the rules rather than trusting them.

### What the declaration buys that prose did not

| Rule | How it is now enforced |
|---|---|
| A value chosen without empirical support carries a sweep | Schema constraint: `source` of `assumed`/`literature`/`measured`/`derived` requires `sweep`, `held_fixed` or `derived_from`. There is no fourth option |
| The three unobtained inputs are never pinned (§0, §13) | They carry `value: null` and `status: unobtained`. `get()` **raises**. A caller must select a sweep member explicitly |
| The mode constants are not freely calibrated (§8.5) | `held_fixed` with the rule and what a departure requires. Any layer that tries to set one is rejected |
| A run states the inputs that produced it | The resolved snapshot is written to `_config.json` in every run directory, and `_run.json` fails its contract without one |
| Escaping a declared range is deliberate and recorded | Only a committed overlay may carry `allow_outside_sweep`, and only with a written `justification`. A shell flag cannot do it |

The one legitimate use of that escape hatch is **S2a**, which is *defined* as the
no-charging-dwell counterfactual: zero is outside the 10–35 s sweep because the
sweep is the range for a system that charges, and S2a is the case where it does
not. That is the scenario, not a parameter choice.

### Two factors that were set in code, with no rationale and no range

`run_matsim.py` set `flowCapacityFactor` and `storageCapacityFactor` to the
sample fraction. Neither string appeared anywhere in `DECISIONS.md`,
`check_package.py` or the P4 checkpoint. They are now registry fields:

- **`RUN.sample.flow_capacity_factor` is derived**, not chosen: it equals the
  sample fraction, which is the standard MATSim scaling rule. It carries a
  `derived_from` identity rather than a fabricated sweep.
- **`RUN.sample.storage_capacity_exponent` is 1.0, and it is derived, not
  chosen.** `storageCapacityFactor = fraction ** exponent`, and MATSim
  **enforces** storage == flow: `GlobalConfigGroup.checkConsistency` throws when
  the two differ by more than `global.relativeTolerance`, which defaults to 0.0.

**A correction, recorded because it was committed before it was tested.** An
earlier revision of this section declared the exponent *assumed*, swept 0.75–1.0,
and called it an open risk — the reasoning being that MATSim floors link storage
at one vehicle, so a 1% sample would produce spurious spillback, inflate car
travel times and drive agents to teleported `walk` (the discarded 250-iteration
runs showed walk at 0.38–0.55 against a 0.134 target). **That reasoning is
superseded.** The diagnostic run built to test it died in one second:

> your storageCapFactor=0.0316228 is more than the relativeTolerance=0.0
> different from the flowCapFactor=0.01. (The old approach of setting the stor
> cap fact larger than the flow cap fact is no longer needed since the qsim
> became a lot more deterministic.)

Raising storage above flow is *older MATSim practice that this version rejects*.
The declared sweep was therefore a range whose members the tool will not accept —
exactly the undisciplined declaration the registry exists to prevent, introduced
by the same change that introduced the registry. The field is now `derived` with
the identity stated, `run_matsim.py` fails in 0.1 s rather than handing MATSim an
inconsistent pair, and `check_package.py` asserts the equality instead of the
sweep.

**What survives the correction.** The question the exponent was a proxy for —
whether behaviour moves with the **sample fraction**, given that every P4
behavioural result was measured at 1% — is untouched, and is what the 1% versus
10% arms of the diagnostic test. The mechanism is no longer a candidate
explanation; the phenomenon, if there is one, still needs a cause.

### Note also the shipped configs

`scenarios/matsim/<S>/<DAY>/config.xml` still carries `flowCapacityFactor 1.0`.
Running one of those directly — as the §9.4 load test did — simulates a **sampled
demand against full supply**. The harness must be used.

### The SUMO corridor layer, migrated and verified

`build_sumo_corridor.py` now reads the registry rather than holding its own
constants — 17 fields in `config/registry/RUN_sumo.json`. The netconvert options
that are **modelling choices** are named fields rather than entries in a flag
list, so a choice cannot hide inside one:

| Field | Why it is a choice, not a flag |
|---|---|
| `RUN.sumo.lefthand` | With it off netconvert builds right-hand connections and **every turning movement on the corridor is wrong** |
| `RUN.sumo.tls_default_type` | `actuated` vs `static` stands in for the unobtained SCATS phasing — part of the 38% run-time uncertainty, not a build detail |
| `RUN.sumo.junctions_join` | Moves junction centroids, which is why the A2 match radius is 60 m rather than A2's own 45 m |
| `RUN.sumo.no_turnarounds` | Uncontrolled U-turns on a trunk corridor are a build artefact, not observed behaviour |
| `RUN.sumo.crossings_enabled` | **False because `--osm.crossings` segfaults netconvert 1.27.1** (§3.6) — a tool defect, not a judgement that pedestrians do not matter |

**The refactor is inert, and that was verified rather than asserted.** The
assembled option list is identical to the literal list it replaced, in the same
order, and `check_package.py` asserts it. The corridor was then rebuilt: all four
`corridor.net.xml` and all seven `tls_*.add.xml` are **byte-identical** to the
pre-migration build.

**Nine files did differ, and they are not the model.** The plain XML
(`corridor.{nod,edg,con,tll,typ}.xml`), the `netccfg`, two netconvert logs and
the build report. Running the build **twice more with no code change between
them** produced the same nine differences, so they are inherently
non-deterministic — netconvert stamps a wall-clock timestamp into each. This
refines a claim made at P2: *"netconvert output is byte-identical on rebuild"* is
true of **the nets and the signal programs**, and false of the intermediates.
Anything that hashes `networks/sumo/_work/` will see spurious churn.

**A determinism defect found by the gate, and fixed.** `_sumo_build_report.json`
is a **committed** artefact carrying a manifest hash, and it recorded
`netconvert_seconds` — wall-clock timing. Its digest therefore changed on every
rebuild even when the four nets were byte-identical, so a committed file could
not be regenerated to the same bytes. That is the reproducibility gate failing,
and CLAUDE.md forbids wall-clock dependence in a build script outright. Timings
now go to `networks/sumo/_work/netconvert_timings.json`, which is gitignored;
the committed report is byte-identical across consecutive rebuilds, verified by
building twice and comparing. The manifest was regenerated. The defect predates
this change and was only exposed because the migration forced a rebuild.

**A SUMO run still does not exist.** The corridor nets have been built four times
and simulated zero times. Proposal §5.1 gives SUMO the entire supply-and-operations
layer — run time, dwell, reliability variance, car delay, frontage throughput —
and §5.2 the outer loop. The fields such a run would need are declared
(`step_length_s`, `begin_h`, `end_h`, `outer_loop_max_iterations`), and two carry
no value on purpose: `RUN.sumo.replications`, because proposal §5.2 asks for at
least 30 and §9.5 shows the budget does not fit and nobody has decided what to cut
(issue #6); and `E.coupling.outer_loop_tolerance_s`, which has never been defined
(issue #8). Declaring them null means a SUMO harness cannot be built on an
unexamined default.

### What is declared but not yet consumed

The **demand and network build layer** has not been migrated: `src/build/*.py`
other than `build_sumo_corridor.py` still hold their own constants, and the
registry declares the same values. Two copies of a number is
exactly the drift this package cannot absorb, so
`src/registry/check_legacy_drift.py` pins them together by test —
**54 fields compared, one deliberate divergence, one expression that is not a
literal**. Writing that check immediately found four values transcribed wrongly
into the registry; the code was authoritative and the registry was corrected.
The migration itself needs a full package rebuild to verify byte-identically and
has not been run.

### The build layer, migrated (P6 cleared)

`src/build/*.py` no longer hold their own copies of the values the registry
declares. 52 fields across 13 scripts now resolve from `config/registry/`, taking
runtime consumption from **16 of 140 to 68 of 140**. The migration was mechanical
— by AST, so no value was retyped — and gated by rebuilding the package in README
order and asserting byte-identical output. `build_matsim_network.py` was
**deliberately not re-run**: §3.5 forbids re-running the mapper, and the gate
instead proves the feeds it was mapped from are unchanged, which `check_package`
confirms through the stop→link fingerprints.

**The gate did its job — it caught three defects, all pre-existing.**

| Defect | Consequence |
|---|---|
| `build_landuse_parking.py` iterated an **unsorted set** to build `frontage_retail_m2_by_street` | The report was **hash-seed dependent**: three runs at different `PYTHONHASHSEED` gave three different digests. Identical data, different bytes. Same defect as the P3 stage 0 `stop_times.txt` bug, in a different file |
| Every GTFS **zip embedded the wall clock** in each entry's header | The 11 scenario and era feeds could never regenerate byte-identically, so their manifest digests were unreproducible by construction. `det_io.py` already solved this one container up, for gzip |
| `_landuse_report.json` and `_run_inputs_report.json` carried **dict-insertion order** as output order | A benign reordering changed the digest |

All three are the same failure the project has fought before, and all three were
invisible while nobody re-ran the builds. **A manifest digest only proves
reproducibility if something actually re-derives it.** The package had not been
rebuilt end to end since the manifest was written, so the gate had never fired.

Fixed: the set iteration is sorted, `det_io.zip_entry` pins every zip entry to a
fixed timestamp, and the registry key order matches the output order it feeds. The
manifest was regenerated. Two fields keep their `legacy_symbol` deliberately —
`B.activity.detour_factor` (the build keeps a labelled 1.30 fallback for when the
C2 file is absent) and `A.lightrail.dwell_charging_s` (declared unobtained; the
literal is the baseline sweep point, which lives in the scenario overlays).

### Fields whose value is null, and why that is the honest encoding

| Field | Why |
|---|---|
| `A.signals.scats_phasing` | Unobtained; TfNSW request outstanding. 38% swing in corridor run time |
| `A.lightrail.dwell_charging_s` | Unmeasured; a few hours of field observation resolves it. 11% of run time |
| `B.opal.journey_linked` | Unobtained; it is what would let the transfer penalty be estimated rather than swept |
| `D.retail.vacancy_rate` | No Newcastle frontage audit exists. Registered so hypothesis B2 cannot quietly acquire one |
| `E.coupling.outer_loop_tolerance_s` | Proposal §5.2 defers it to calibration and **it has never been defined** (issue #8) |
| `RUN.controler.last_iteration` | §9.7 shows 100 and 250 are both too low and no justified value has been measured (issue #5) |

The last two are not missing data — they are **decisions nobody has taken**.
Declaring them with a null value means the model cannot run past them silently:
`run_matsim.py` now refuses to start without an explicit iteration count, which
is the same refusal `--iterations` already implemented, moved from one script's
argument parser into the registry where it binds everything.

---

## 14. Change log

| Date | Change |
|---|---|
| 2026-08-11 | **The input registry (§15).** Every value the model consumes that is not read from an immutable raw download is now declared in `config/registry/` with its units, its provenance and either a sweep range or an explicit rule holding it fixed — **123 fields**, against 316 module-level constants of which exactly one carried a machine-readable source label. Proposal §8.1 becomes a schema constraint rather than a discipline: `assumed` without a sweep does not validate. The three unobtained inputs carry `value: null` and the resolver **raises** rather than returning a point value, so §0 and §13 are enforced structurally; the §8.5 mode constants are `held_fixed` and no overlay, environment variable or flag can move them. Two factors that governed every P4 result were found set in code with no rationale and no range — `flowCapacityFactor` (derived, and now stated as such) and `storageCapacityFactor` (assumed, exponent swept 0.75–1.0, and an open risk at 1% because MATSim floors link storage at one vehicle). Outputs are declared to the same standard: `_run.json`, `_metrics.json`, `_fit.json` and `_config.json` each carry a JSON Schema, and a fit block that does not name its target ids fails its contract. `docs/CONFIG_REFERENCE.md` is generated and checked for staleness. `check_package.py` 860 → **908 checks**, 1 standing warning. The build layer is declared but not yet migrated and is pinned to the registry by a drift test, which caught four transcription errors on its first run. No parameter value was changed, no target value was changed, the 67/143 split is untouched and no scenario was run. |
| 2026-08-10 | **P4 stage 0 — the assembled run inputs did not load, and what a run actually costs (§9.4, §9.5, §12.1–12.3).** MATSim was pointed at `scenarios/matsim/S2/WEEKDAY/` and refused it. Three independent defects, none visible to a check that treats the artefacts as data: the day-type filter dropped the doctype MATSim selects its reader from (all 30 sets); it left stop facilities and `minimalTransferTimes` relations orphaned by the routes it removed, which makes SwissRailRaptor dereference a null array (all 30); and the kerbside patch appended a second `<attributes>` block to links that already had one, invalidating **6 of the 10** run networks — precisely the six carrying an E1 road change. Fixed, rebuilt byte-identically with the patch counts unchanged, and **all 30 sets now load and run**. `check_package.py` 556 → **657 checks**, with the three failure modes asserted per set. Run cost measured on this machine rather than estimated: **9.8 s/iteration at 1%, 29.9 s at 10%, ~64 s at 25%**, memory 9.8/18.4/31.5 GiB, extrapolating to ~4.5 min and ~97 GiB at 100% — so **a 100% weekday run does not fit in 63.5 GiB** and the specified 5,100 run-days is ~765 days of wall clock. Also recorded, without acting on either: 13 of the 67 calibration targets (`lr_cardtype_share`) can identify nothing in MATSim and several others are duplicates or schedule inputs, leaving ~4 mode-share degrees of freedom + 1 patronage level + 34 counts; and the 119 `road_aadt` values are the mean of `ALL DAYS` with the peak-period rows, 0.58–0.71× the true figure. **The 67/143 split is untouched, no holdout value was used, no target value was changed and no falsification condition altered. Still no scenario run.** |
| 2026-08-10 | **P3 stage 3 — assumptions replaced by Newcastle measurements where the data allows, and the sweep-range rule made mechanical.** Three constants derived rather than typed: the **detour factor** is now routed over the observed A1 road graph (**1.3376**, 551 zone pairs, was assumed 1.30); the **weekday/weekend travel split** comes from the RMS counts' own `WEEKDAYS`/`WEEKENDS` periods (**0.752**, 551 station-years, was implied 0.825); and census G62 gives an observed **lower bound** on work attendance (0.651) without being allowed to set the value, since census night carries the 2021 lockdown (§2.4). Seven parameters that breached proposal §8.1 by carrying no sweep range now carry one, and `check_package.py` **enforces the rule as a test** rather than leaving it to discipline. What genuinely cannot be localised is labelled so: MATSim's `performing`, distance rates, typical durations and replanning weights are properties of the scoring formulation, not of Newcastle. `EXTERNAL_INTERACTION_RATE` stays swept and the missing ABS journey-to-work origin-destination table is added to §13. 497 → **556 checks**, all passing. Still no scenario run; no falsification condition altered. |
| 2026-08-10 | **P3 stage 2 — MATSim plans, day-type run inputs and the C1 scoring translation (§9.3).** 517,936 weekday agents wired to the single P2 build; the day-type filter works on the already-mapped schedule and is verified to preserve all 1,714 route link sequences and the whole stop→link map. What C1 loses in translation — the nest structure, per-purpose VOT, crowding — is recorded, not dropped. Two defects caught by the new checks: the day-type token is underscore-delimited for the S1 shuttle and S3 BRT, so both were being dropped from every day type and each scenario would have run without its intervention; and banned-turn removal was network-wide, deleting 1,235 observed restrictions instead of 8. `check_package.py` 322 → **497 checks**, all passing. Still no scenario run; no falsification condition altered. |
| 2026-08-10 | **P3 stage 1 — B2 activity chains rebuilt as tours (§9.2).** The P1 chains put 1,452,065 activity legs on 1,481 zone centroids, labelled every return-home leg NHB, and gave each agent a single subtour; they are replaced, not patched. Destinations are now placed on observed POIs and building footprints, the gravity decay is solved against the HTS journey distance per purpose, three day types are produced, and the 201 external SA1s finally generate boundary demand. `build_population.py` keeps B1 and no longer writes B2; because it no longer draws for chains, the B1 sample shifted 612,680 → 612,668 persons with every fit statistic unchanged. Still no scenario run; no falsification condition altered. |
| 2026-08-10 | **P3 stage 0 — the §3.4 shape defect closed, and one determinism bug with it.** S0/S2c/S4/S5 alignments rebuilt from observed geometry (§3.4); extension stop sitings anchored on observed features, one of them 548 m out. E1 patch set 195 → 414 rows as a consequence. **`build_scenario_schedules.py` iterated a `set` of trip ids in two places, so `stop_times.txt` row order varied with the Python hash seed** — a violation of the determinism rule that predates this branch and was caught by a repeat-build check; now sorted, and two consecutive builds are byte-identical across all 10 feeds. One MATSim build of all 15 feeds and 4 SUMO nets regenerated on the corrected feeds; 322 package checks pass. Still no scenario run; no falsification condition altered. |
| 2026-08-10 | **P2 network build.** Toolchain pinned (§3.6). Corridor attributes graded by evidence and the E1 road variants derived as edge-level deltas (§3.4); premise corrected — the corridor is not 75–98% imputed (§2.5). pt2matsim's run-to-run drift measured and bounded (§3.5). Three missing signal variants built (§5). CRS label corrected (§2.6). MATSim network + 15 mapped schedules and 4 SUMO corridor nets produced. Still no scenario run; no falsification condition altered. |
| 2026-08-10 | Initial. P1 data acquisition. Scope decisions §10.1–3, 4, 5 closed. Proposal premises corrected per §2.1–2.4. No scenario run; no falsification condition altered. |
