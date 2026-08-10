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

| Value | Assumed | Sweep | Why it is not observed |
|---|---|---|---|
| Day-type rate shape (WEEKDAY / SAT / SUN) | 1.06 / 0.95 / 0.80 | 1.00–1.12 / 0.85–1.05 / 0.70–0.92 | The HTS LGA tables carry **no day-of-week dimension** — confirmed in the raw workbook, whose only dimensions are financial year, LGA, mode and purpose. Only the *shape* is assumed: the level is rescaled so 5×WEEKDAY + SAT + SUN reproduces the observed HTS week average exactly. |
| Day-type purpose mix | commute and education collapse at the weekend, shopping and social rise | — | Same reason. Renormalised against the HTS purpose share so it redistributes rather than inflates. |
| `P_MANDATORY` (work / education tour made on a given day) | 0.78 / 0.85 weekday | — | No local estimate of day-to-day work attendance. |
| `P_INTERMEDIATE_STOP` by purpose | 0.12–0.30 | 0.10–0.35 | Trip chaining rates are not in the published HTS tables. **This parameter decides how many sub-tours exist, and therefore how freely MATSim's mode choice can vary within a day.** |
| `CHILD_TOUR_RETENTION` | 0.4 | — | Share of an under-12's secondary tours made independently. |
| `DETOUR_FACTOR` (straight-line → network) | 1.30 | 1.20–1.40 | Used only to compare the gravity model against HTS *journey* distances, which are network distances. |
| `EXTERNAL_INTERACTION_RATE` | 0.08 | 0.04–0.15 | Share of external-tier residents entering the core on a weekday. No journey-linked Opal and no external-tier HTS cell exists to estimate it. |
| Activity durations, departure profiles | carried from P1 | ±30% lognormal | As before. |

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
(scenario × day type). 517,936 weekday persons, 2,188,436 legs, 2,706,372
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

| Value | Assumed | Sweep | Why |
|---|---|---|---|
| Seed mode split | see table above | car 0.68–0.86, PT 0.05–0.20 | Initial condition for co-evolution; P4 moves it. |
| `performing` | 6.0 utils/h | — | Conventional MATSim value; the scoring scale is relative to it. |
| `monetaryDistanceRate` car | −0.00018 AUD/m | — | Fuel and tyres only, not standing costs: a mode choice within the day does not re-decide car ownership. |
| Typical activity durations | home 12 h, work 8 h, education 6 h, shopping 1 h, other 2 h, business 1 h | — | MATSim scoring needs a typical duration per activity type. |
| Replanning strategy weights | ChangeExpBeta 0.70, ReRoute 0.15, SubtourModeChoice 0.10, TimeAllocationMutator 0.05 | — | Conventional; innovation switched off for the last 20% of iterations. |

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
| 2026-08-10 | **P3 stage 2 — MATSim plans, day-type run inputs and the C1 scoring translation (§9.3).** 517,936 weekday agents wired to the single P2 build; the day-type filter works on the already-mapped schedule and is verified to preserve all 1,714 route link sequences and the whole stop→link map. What C1 loses in translation — the nest structure, per-purpose VOT, crowding — is recorded, not dropped. Two defects caught by the new checks: the day-type token is underscore-delimited for the S1 shuttle and S3 BRT, so both were being dropped from every day type and each scenario would have run without its intervention; and banned-turn removal was network-wide, deleting 1,235 observed restrictions instead of 8. `check_package.py` 322 → **497 checks**, all passing. Still no scenario run; no falsification condition altered. |
| 2026-08-10 | **P3 stage 1 — B2 activity chains rebuilt as tours (§9.2).** The P1 chains put 1,452,065 activity legs on 1,481 zone centroids, labelled every return-home leg NHB, and gave each agent a single subtour; they are replaced, not patched. Destinations are now placed on observed POIs and building footprints, the gravity decay is solved against the HTS journey distance per purpose, three day types are produced, and the 201 external SA1s finally generate boundary demand. `build_population.py` keeps B1 and no longer writes B2; because it no longer draws for chains, the B1 sample shifted 612,680 → 612,668 persons with every fit statistic unchanged. Still no scenario run; no falsification condition altered. |
| 2026-08-10 | **P3 stage 0 — the §3.4 shape defect closed, and one determinism bug with it.** S0/S2c/S4/S5 alignments rebuilt from observed geometry (§3.4); extension stop sitings anchored on observed features, one of them 548 m out. E1 patch set 195 → 414 rows as a consequence. **`build_scenario_schedules.py` iterated a `set` of trip ids in two places, so `stop_times.txt` row order varied with the Python hash seed** — a violation of the determinism rule that predates this branch and was caught by a repeat-build check; now sorted, and two consecutive builds are byte-identical across all 10 feeds. One MATSim build of all 15 feeds and 4 SUMO nets regenerated on the corrected feeds; 322 package checks pass. Still no scenario run; no falsification condition altered. |
| 2026-08-10 | **P2 network build.** Toolchain pinned (§3.6). Corridor attributes graded by evidence and the E1 road variants derived as edge-level deltas (§3.4); premise corrected — the corridor is not 75–98% imputed (§2.5). pt2matsim's run-to-run drift measured and bounded (§3.5). Three missing signal variants built (§5). CRS label corrected (§2.6). MATSim network + 15 mapped schedules and 4 SUMO corridor nets produced. Still no scenario run; no falsification condition altered. |
| 2026-08-10 | Initial. P1 data acquisition. Scope decisions §10.1–3, 4, 5 closed. Proposal premises corrected per §2.1–2.4. No scenario run; no falsification condition altered. |
