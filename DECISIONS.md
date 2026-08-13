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

### Confirmed at 25% — the 10% reading was real (added after the run landed)

The 25% confirmation run the §8.5 decision was gated on. 131,291 persons, 16,365 s
wall, 56.4 s median iteration, same 8 threads and same declared pipeline.

| Newcastle LGA | 1% | 10% | **25%** | HTS |
|---|---:|---:|---:|---:|
| Vehicle driver | 16.01 | 30.85 | **32.48** | 59.0 |
| **Vehicle passenger** | 61.06 | 50.94 | **49.87** | **20.6** |
| mean absolute error | 23.19 pp | 17.43 pp | **16.80 pp** | |
| passengers per driver | 3.814 | 1.651 | **1.535** | 0.3503 |

**The fraction sensitivity has flattened.** 1% → 10% moved car **+14.8 pp**; 10% →
25% moves it **+1.6 pp** and ride **−1.1 pp**. The divergence really was the 1%
artefact, and 10% already behaves like 25% — so the answer stands where the
artefact is absent: **ride settles near 50%, about 2.4× the observed 20.6%, at
1.535 passengers per driver against an observed 0.3503.** §9.11's constraint was
necessary and is not sufficient, and that is now measured rather than suspected.

The §9.13 constraint says the same thing independently and more sharply, because
it is geography-robust and is scored into nothing:

| ride ÷ car trip length | 1% | 10% | **25%** | observed |
|---|---:|---:|---:|---:|
| | 1.075 | 1.346 | **1.372** | **0.961** |

Observed passenger trips are slightly *shorter* than driver trips; the model makes
them 43% longer, and **the gap widens with sample fraction rather than closing**.

Counts, by contrast, do not move with fraction at all — −72.9% / −73.8% / −73.1%
— which points at §9.14 rather than at sampling.

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

## 9.13 Trip length by mode — an observable the package always held (P4 stage 3)

The HTS mode table carries `TRIP_AVG_DISTANCE` and `TRIP_AVG_TIME` per mode, per
LGA, for fourteen survey years. **Nothing used them.** P4 read `MODE_SHARE` for
the targets and `TRIPS_BY_MODE` for the §9.8 occupancy constraint, and left the
two columns that say whether a mode is used over the right *range* untouched.

Mode share says how many people choose a mode. It cannot say whether they choose
it for the right journeys, and a model can hit a share exactly while using a mode
for trips it would never serve in reality.

### The constraint, measured

`src/calibrate/measure_mode_constraints.py` now derives it into
[`params/C4_mode_constraints.json`](../params/C4_mode_constraints.json) on the
same principle as occupancy: the value is the base-year figure and the sweep is
**the observed spread across every survey year for that mode**, not an interval
anyone chose.

| mode | HTS category | observed km | sweep | observed min | years |
|---|---|---:|---|---:|---:|
| car | Vehicle driver | 10.20 | 6.60 – 10.80 | 17.20 | 7 |
| ride | Vehicle passenger | 9.80 | 5.60 – 9.80 | 15.50 | 7 |
| pt | Public transport | 23.40 | 15.90 – 24.50 | 34.40 | 3 |
| walk | Walk only | 0.70 | 0.70 – 1.10 | 12.30 | 7 |
| bike | Other | 5.20 | 3.10 – 5.20 | 19.20 | 7 |

Ten registry fields declare it — one per mode per quantity, because the schema
takes an interval per field and **weakening the schema to accept a per-mode
mapping would have been the wrong repair**. `fit.py` reports the comparison
beside the fit and never counts it into one.

**It is a constraint, not a target.** The 67/143 split is pre-registered and
nothing here joins it; `check_package.py` asserts that no calibration metric
carries a trip-length name.

### It caught an error the moment it existed, and the error was mine

Before the constraint was wired up, the comparison was made by hand and reported
as *"car 10.16 modelled against 10.20 observed — essentially exact, and car is the
only mode with a distance cost"*. **That was wrong.** The modelled figure was the
**five-LGA** mean and the observed figure is **Newcastle LGA**. The study area
includes Cessnock, Maitland and Port Stephens, whose trips are far longer than
Newcastle's, so the two numbers were never comparable — the identical mismatch
§12.1 records for the seed.

Like for like, both sides Newcastle LGA, on `ride_sufficiency_10pct`:

| mode | modelled km | observed km | ratio |
|---|---:|---:|---:|
| car | 6.36 | 10.20 | **0.62** |
| ride | 8.56 | 9.80 | 0.87 |
| pt | 11.02 | 23.40 | 0.47 |
| walk | 2.90 | 0.70 | **4.14** |
| bike | 5.72 | 5.20 | 1.10 |

So the correct statement is nearly the opposite of the one first drawn: **car
trips are 38% too short, not exact**, and `ride` is closer to its observed length
than `car` is to its. The claim that ride was "41% too long" was an artefact of
the geography error.

### What survives the correction, and it is the part that matters

The **ratio between two modes is robust to geography** — it does not depend on
how long the study area's trips happen to be:

| | modelled | observed |
|---|---:|---:|
| ride ÷ car trip length | **1.346** | **0.961** |

Observed passenger trips are slightly **shorter** than driver trips. The model
makes them **35% longer**. That asymmetry is real, it is the signature the §9.8
zero distance rate would produce, and it is unaffected by the geography error
that damaged the levels.

It also puts a number on a second distortion nobody had looked at: modelled
**walk** trips are **4.1× their observed length** (2.90 km against 0.70 km, and a
median of 45.99 min), which is not walking behaviour under any reading.

### Why this is recorded before any specification change

§9.8 set `ride`'s monetary distance rate to zero and declared it *derived, not
assumed*, on an aggregate-cost identity. The observable that would have tested
that derivation was in the package the whole time. **A value declared `derived`
is only as good as the identity it was derived from, and this is the check that
catches one derived from the wrong identity.** It is in place before the §8.5
departure is chosen, so whichever candidate is taken can be judged against an
observable rather than against the mode share it was chosen to move.

**Also unused until now: `Serve passenger` is 15.7% of observed journeys** —
87,000 a day, average 6.4 km, the second-largest purpose in Newcastle and larger
than commuting. B2 generates none of them (issue 11). That is a measured demand
component, not the assumption the issue had recorded it as, and it is the driver
side of the same problem: with no escort trips, a car passenger costs nobody
anything.

---

## 9.14 The external tier is 0.43% of trips and does not drive (P4 stage 3)

§9.12's correction to `fit.py` stopped discarding count stations the model fails
on, and the first thing it surfaced was a modelled **zero** on the M1 Pacific
Motorway at Wyee against an observed 48,016 AADT. Investigating that turned out
not to be about one station.

### Every motorway station is short, and the error grows toward the boundary

| target | station | modelled | observed (light-vehicle) | error |
|---|---|---:|---:|---:|
| V113 | Pacific Motorway (Wyee) | **0** | 44,885 | **−100.0%** |
| V094 | Pacific Motorway (Freemans Waterhole) | 90 | 35,922 | −99.8% |
| V093 | Pacific Motorway (Freemans Waterhole) | 90 | 3,483 | −97.4% |
| V091 | Pacific Motorway (West Wallsend) | 200 | 3,076 | −93.5% |
| V081 | Pacific Motorway (Black Hill) | 3,590 | 31,356 | −88.5% |

**Motorway stations median −97.4%; every other calibration station −69.6%.**
Black Hill, nearest the urban core, is least wrong; Wyee at the far southern
boundary is exactly zero. The network is not at fault: **263 of 314 links named
"Motorway" carry traffic**, so the M1 is connected and routable. It carries a
median of 40 vehicles per link at a 10% sample — roughly 400/day scaled — where
one station observes ~45,000.

### The tier that should supply that traffic is 0.43% of trips

962 external boundary trips against 223,144 core trips, median length 68 km.
`B.external.interaction_rate` is **0.08, `assumed`**, swept 0.04–0.15, and its own
registry entry already records that it is *localisable but not yet available*: the
ABS journey-to-work SA2 × SA2 origin–destination table would settle it, and the
package holds the place-of-work side without the pairing (§13). A tier this size
cannot load a motorway whose observed flow at a single station exceeds the whole
modelled external demand roughly 45-fold.

### And the external agents that exist almost never drive

| mode | trips | median km | median hours |
|---|---:|---:|---:|
| **bike** | **478** | **96.1** | **6.35** |
| ride | 432 | 46.7 | 0.76 |
| pt | 46 | 110.3 | 3.20 |
| **car** | **6** | 50.0 | 0.74 |

**478 external agents cycle a median 96 km over 6.35 hours**, and that survived
250 iterations of a utility-maximising co-evolution. It is specific to the tier —
core agents at 60 km and beyond take car 24.5% and bike 3.7%, which is sensible.

**Ruled out by measurement:** not permission, since all 531 external agents carry
`carAvail=always` and `hasLicense=yes`; not connectivity, since all **586**
distinct start and end links they use exist in the run network and **every one
permits car**; not the network, which routes traffic on 84% of motorway links.

**The mechanism is not established and is recorded as open rather than guessed.**
On the shipped scoring a 96 km bike trip costs roughly −140 utils against about
−38 for the same trip by car, so mode choice moving agents *into* bike and *out
of* car inverts what the utilities imply. Something structural is doing it. Five
hypotheses have already died between this and §9.12; this one gets measured.

### Why it is recorded rather than fixed

Both halves — an undersized tier and a tier that does not drive — are B2 changes,
and B2 regenerates the P3 demand artefacts and **breaks comparability with every
run to date**. That is a planned break, not something to slip in beside a
specification change while a fraction series is still being measured.

**Consequence, and it is not small.** Until this is understood every
boundary-adjacent count is biased low, and the −73.8% overall count error carries
a large contribution from a demand tier that is both too small and not driving.
Calibrating the core network against those counts would be tuning it to
compensate for missing through traffic — the count analogue of the ASC absorption
proposal §9 names as the primary threat to validity. **No count-based calibration
should be attempted until §9.14 is resolved.**

---

## 9.15 The external tier walks to the network, and the escort trip is typed wrong (P4 stage 4)

§9.14 left the external tier's behaviour "recorded as open rather than guessed"
after six hypotheses died. The seventh was measured rather than guessed, and it
is structural: **the external tier is charged a walk that the modes it chooses
instead are exempt from.**

### The mechanism

`routing.accessEgressType = accessEgressModeToLink` with
`routing.networkModes = car,ride`. So `car` and `ride` are routed on the network
and pay an access and egress walk from the activity coordinate to the link;
`bike` and `walk` are teleported at a beeline speed and pay **nothing**.

That is harmless for the core population, whose activities sit on observed POIs
inside the network. It is not harmless for the external tier, because **all 201
external zones lie outside the modelled area**: their centroids sit a median
**21.3 km** beyond the five-LGA boundary, a top decile of 80.7 km and a maximum
of **128.7 km**, while the road network is clipped to the study area. B2 placed
the trip end by uniform area-jitter inside the external SA1, so it landed where
no modelled road exists and MATSim walked the agent to the edge of the network.

Access and egress walk per trip, iteration 0, from `0.legs.csv.gz`:

| tier | mode | trips | median walk km | median walk h | median main km |
|---|---|---:|---:|---:|---:|
| core | car | 31,197 | **0.097** | 0.026 | 8.8 |
| core | ride | 35,119 | 0.099 | 0.026 | 8.2 |
| core | bike | 47,108 | 0.000 | 0.000 | 7.1 |
| **external** | **car** | 134 | **2.656** | **0.703** | 46.9 |
| external | ride | 151 | 1.054 | 0.279 | 47.5 |
| external | bike | 188 | **0.000** | 0.000 | 72.0 |

The external car access walk is **27x the core's**, and its top three deciles are
**16.4 / 39.9 / 49.8 km — of walking**, at the 1.05 m/s teleport speed.

### It is monotone in the score, so it is not a coincidence

Iteration 0 is the clean test: the uninformed seed assigns modes uniformly, so
mode is exogenous and every agent is equally unrelaxed.

| mode | access-walk band | agents | median score | activities performed |
|---|---|---:|---:|---:|
| car | < 0.5 h | 24 | **+94.21** | 3 |
| car | 0.5 - 2 h | 13 | +72.91 | 3 |
| car | 2 - 6 h | 6 | -22.10 | 3 |
| car | **> 6 h** | **39 (48%)** | **-1165.01** | **2** |
| ride | < 0.5 h | 35 | **+111.67** | 3 |
| ride | > 6 h | 44 (47%) | -1169.82 | 2 |
| bike | < 0.5 h | **101 (all of them)** | -96.17 | 3 |

A well-connected external car tour scores **+94**. A badly-connected one scores
**-1165**, and **48%** of them are badly connected. The tour truncates - two
activities instead of three - because the agent spends the day walking to the car
and never gets home. Tours that never complete: **car 39.0%, ride 38.7%, pt
66.7%, walk 85.3%, bike 13.9%**.

Bike is the *worst* mode for a connected external agent and the *best* for a
disconnected one, and it is the only mode that is never disconnected, because it
is teleported door to door. Within-agent, over the 220 agents that realised both,
bike beats car by a median **+118.93** utils, and the difference is **bimodal at
plus or minus 1000** - the signature of a plan that does not complete, not of a
cost. **Mode choice was behaving correctly.** The 478 agents cycling 96 km were
choosing the only mode that did not require them to walk to a road.

**Why six hypotheses died.** Permission, connectivity, the network, replanning,
aborts and the seed all tested *the link*. Every one of them was sound. The
defect is *the distance to the link*, which none of them measured. §9.14's
utility arithmetic - "-140 by bike against -38 by car, so the choice inverts what
the utilities imply" - omitted the access leg, which is the structural thing it
correctly concluded must exist.

### A second defect, independent of the first

All 531 external agents carried `rideAvail=always`. `build_matsim_plans.py`
resolved the unknown that way on the ground that "external boundary agents are
not in B1, so household composition is unknown". But §9.11's rule is that a
person may be a car passenger only if their household holds a vehicle **and**
contains another licence holder, and an external agent is **household-less by
construction** - the generator's own words. A person with no household cannot
satisfy that condition, so the unknown was resolved in the wrong direction, and
**432 of 962 external trips were car-passenger trips with no possible driver.**

### A third, which is a scope consequence and not a defect

The external tier is not a ring. Every one of its 201 zones is in a single SA4:

| sector | N | NE | E | SE | S | SW | W | NW |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| zones | 18 | 23 | 17 | **0** | **0** | **0** | 3 | **140** |

The southernmost external zone is at latitude -32.856; the M1 southern cordon is
at -33.218. **There is no external zone anywhere in the Sydney direction**, so no
interaction rate can put traffic on the M1 at Wyee. That is not an accident:
`extract_zones.py` defines the tier as "the remainder of SA4 'Hunter Valley exc
Newcastle' ... retained only as a boundary treatment for **Hunter Line**
through-demand", which is scope decision 3 in §1. The M1 gap therefore lies
**outside the tier's declared purpose**, and #20's framing of it as a tier-size
problem is corrected: raising `B.external.interaction_rate` would not have
touched it.

### The repair

The standard treatment of boundary demand is an **external station**: the trip
enters at the point where its corridor crosses the cordon, on a real link, and
the portion of the journey outside the study area is not modelled. That is what
is now built, and it removes the mechanism by construction rather than by
counterweight.

1. **Cordon anchoring.** The cordon set is *derived, not listed*: a node is an
   external station if it is the nearest node on a road capable of carrying
   boundary demand (`B.external.cordon_road_classes`) to at least one external
   zone, which by construction puts it on the outward-facing edge of the network.
   **42 crossings.** Testing distance to the study-area boundary instead picks up
   the **coastline**, which is a boundary but not a crossing. Each agent enters
   through the crossing that minimises `d(zone, cordon) + d(cordon, destination)`
   - the entry that is on the way, not merely the nearest to home.
2. **Destinations on observed attractors.** The external tour's core end was
   jittered inside the destination zone while the core population's was placed on
   a POI. It now uses the same routine.
3. **Ride withheld from the tier** (`B.external.agent_ride_available`, derived),
   and the placeholder attributes it used to type in are declared
   (`B.external.agent_profile`).
4. **`Serve passenger` given its own tour purpose, HX.** It was mapped to NHB and
   then folded into the discretionary tours, because NHB is not a tour purpose.
   That preserved the trip **rate** and lost the trip **type**: an escort became a
   two-hour discretionary stay made by anyone, rather than a five-minute drop-off
   made by a driver. It now carries its own rate, its own gravity decay against
   the observed serve-passenger journey distance, the education departure profile
   and attractor set (the school run being the dominant and most peaked
   component), a licence requirement on the traveller
   (`B.activity.escort_requires_licence`, derived), and a MATSim `escort` activity
   whose typical duration is minutes rather than hours - a longer one would hold
   the vehicle at the destination and displace the return trip out of the peak.
   **#11's premise is corrected: the demand was not absent, it was mistyped.**
5. **NHB removed from the destination-choice purposes.** With serve passenger
   moved out, nothing observed maps to NHB, so it had no journey distance to
   calibrate against - the check caught this immediately. It is a *leg* label, not
   a tour purpose, and carrying it built an attractor index and solved a decay
   that nothing drew from.

### What the repair does to the inputs

| | before | after |
|---|---:|---:|
| External leg length, median | 54.2 km | **21.6 km** |
| External leg length, top decile | 106.6 km | 43.0 km |
| External destination placement | 5,385 `jitter_external` | **5,408 `poi`**, 59 jitter |
| Serve-passenger share of weekday legs | **0** | **14.53%** (observed 15.7% of journeys) |
| Week trip rate vs HTS 3.473 | 3.397 (-2.2%) | **3.418 (-1.6%)** |
| Seed ride share | 0.1712 | 0.1620 |

### What is deliberately NOT repaired

- **The M1, and boundary through traffic generally.** Representing it needs an
  external-station matrix seeded from cordon counts, which is a scope decision
  about what the model is for, not a defect fix. **The §9.14 consequence stands
  unchanged: no count-based calibration until it is resolved.**
- **`B.external.interaction_rate` stays `assumed` and swept 0.04-0.15**, not
  pinned. It still needs the ABS journey-to-work SA2 x SA2 table (§13).
- **The escort trip is still only the driver's side.** No passenger is bound to
  the escorting driver; that is the socnetsim limitation §9.11 already records.
- **`WB` is not corrected for the employed fraction**, though `HX` is corrected
  for the licence-holding fraction. Both are secondary purposes drawn only for a
  subset of persons, and the rate solve accounts for neither. Logged rather than
  changed: it is pre-existing, it is not what this change is about, and altering
  it would move an existing calibration for no measured reason.

### This is a planned comparability break

B2 was regenerated, so the demand under every run to date has changed. **The
three `ride_sufficiency_*` runs are historical** and no earlier run shares this
demand. The re-measurement runs as `cordon_escort_10pct`, configured identically
to `ride_sufficiency_10pct` so the comparison isolates the demand change.

**Neither is a result.** 250 iterations remains measurably short of relaxation
(§9.7), and the §8.5 ride departure (#16) is still unchosen - it must be re-taken
on the repaired demand, because the ride share it was to be chosen against has
moved.

---

## 9.16 The calibration loop, the report, and the outer-loop tolerance (P4 stage 5)

P4 deliverables 4, 6 and 7. Deliverable 5, the calibrated base, needs the loop to
have run and is **not** met by this section.

### What the loop is allowed to move, and why almost nothing is

`src/calibrate/calibrate.py` **derives its search space from the registry rather
than listing one**. A field is movable only if it is `assumed`, carries a scalar
sweep, is not `held_fixed`, and — the clause that does most of the work — can
actually be *realised* by the pipeline the loop runs.

Thirty-eight registry fields carry a scalar sweep. **Twenty-one are excluded,
each with a stated reason**, and the exclusions are derived from the `consumers`
declaration rather than hand-maintained:

| excluded because | example | why it is not a calibration parameter |
|---|---|---|
| the loop's own controls | `CAL.search.max_rounds` | calibrating the search against itself |
| run identity or compute | `RUN.sample.fraction` | a machine choice, not a property of Newcastle |
| measurement apparatus | `B.counts.station_match_radius_m` | moving it changes what the fit can *see*, not what the model *does* — which is precisely the defect issue #19 was |
| needs the mapper re-run | `A.transit.era1_line_speed_kmh` | §3.5: ~18% of route link sequences differ between identical builds, so a scenario mapped in one build cannot be compared with one mapped in another |
| needs a demand rebuild | `B.activity.p_second_stop` | B2, the plans and the 30 run-input sets would have to be regenerated per candidate; possible, but not implemented, and therefore refused rather than silently skipped |
| no declared consumer | — | nothing would read a change |

That last mechanism matters more than it sounds. The loop runs
`run_matsim.py -> extract_metrics.py -> fit.py` and rebuilds nothing else. Passing
`--set` for a field that only a build script reads would change the **recorded
configuration** without changing a single **input** — a run that reports a
parameter it did not use. Refusing is the only honest option.

**The mode constants are unreachable by construction.** They carry `held_fixed`
under §8.5, so the filter removes them before any search begins. Proposal §9
names ASC absorption as the primary threat to validity, and this is that rule
made structural rather than remembered.

### The objective is mode share, and that is not an oversight

| block | targets scored | in the objective |
|---|---:|---|
| mode share | 5 | **yes** |
| patronage | **0** | no — nothing to score |
| counts | 33 | **no — forbidden by §9.14** |

**Patronage scores zero in a single day-type run.** The contemporary monthly
target needs WEEKDAY, SAT and SUN composed over a calendar month; the rest are a
pre-pandemic PT market against a 2026 base (§12). So it contributes nothing.

**Counts are scored and reported on every run but never optimised against**
(`CAL.objective.include_counts = false`, and the loop refuses to start if it is
set true without a recorded departure). §9.14 and §9.15: the external tier
carries no boundary through traffic, so every boundary-adjacent count is biased
low by construction and tuning the core network against them would compensate for
demand the model does not contain.

That leaves **five HTS mode shares, which sum to one — four independent
numbers.** `CAL.objective.independent_targets` records it and **the loop refuses
to move more than four free parameters**, printing the movable set instead of
producing a fit of more parameters than data. §12.1 reached the same number from
the other direction.

### Constraints stay constraints

The C4 occupancy and trip-length observables are **feasibility conditions, never
objective terms**. A candidate that violates one is marked infeasible and
reported; it is not penalised into the objective. Adding an observable to the
objective would convert a constraint into a target, and the 67/143 split is
pre-registered — new observables join as constraints or not at all.

### Two independent guards against reading a holdout row

`fit.py` filters to `split == 'calibration'` at read time and raises if anything
else survives, so a holdout value is never in memory. The loop **never opens the
targets file at all**; it reads the `_fit.json` that `fit` wrote, and
`audit_no_holdout()` re-checks that the fit output reconciles scored against
explained and that every block naming a count of targets also names the targets.
A leak would have to defeat both.

### Deliverable 7: the outer-loop tolerance is 5 seconds

Proposal §5.2 defers this — run the loop *"until the corridor run time is stable
within a tolerance to be defined at calibration"*. It is now defined, and
**derived from the resolution of the target rather than chosen**:

| quantity | value | source |
|---|---:|---|
| Corridor run-time target (V208/V209) | **720 s** | scheduled, not observed |
| Timetable quantum | **60 s** | every segment of `A4_segment_runtime_decomposition.csv` is a whole multiple; direction 0 sums to exactly 720 s |
| So the target is known to | **±30 s** | |
| Smallest declared corridor sensitivity | **≈79 s** | charging dwell, 11% of end-to-end run time |
| Largest | **≈274 s** | signal priority, S2 against S2b, 38% |
| **Tolerance** | **5 s** | 0.69% of the run time |

At 5 s the loop sits an order of magnitude inside the smallest declared
sensitivity and well inside the resolution of the target it is judged against, so
a converged loop cannot contribute materially to any reported difference. It is
`held_fixed` rather than swept because a convergence tolerance decides how many
outer iterations are *paid for*, not what the answer is.

**It carries a self-policing bound.** If any reported scenario comparison ever
turns on a corridor run-time difference smaller than **twice** the tolerance,
that difference is not resolvable by the loop that produced it: the tolerance
must be tightened and both scenarios re-run **before** the comparison is
reported. `check_package.py`'s assertion is the **inversion** of the one it
replaces — it used to assert the value was still null so that no loop could be
built on an unexamined default; it now asserts the value exists, is held fixed
with a rule, and carries that bound.

The SUMO run harness and the loop itself remain **P5**. This is the number they
must honour.

### Deliverable 6: the report leads with what the fit cannot do

`src/calibrate/report.py` computes nothing. Every number in it was produced by
`fit.py`. It opens with how many targets were scored, how many could not be and
why, and how much independent information the scored ones carry — because a
report that opens with a headline error invites the reader to treat it as a
score. Constraints are reported in their own section, apart from the targets, so
they cannot be counted as evidence of fit. Where no calibration search has run,
the provenance section **says so** rather than leaving it to inference.

### A finding the loop turned up: the C-layer values have two homes

Six behavioural fields resolve from the registry and are read by **nothing**:
`C.transfer.beta_transfer_penalty_min`, `C.walk.*`, `C.gradient.*`,
`C.crowding.*`, `C.nesting.*`. Two of those are documented as not surviving
translation to MATSim scoring (§9.3 — crowding and nesting). The others are read,
but from `params/C1_parameters.json`, which is what
`build_matsim_run_inputs.py` actually opens — the transfer penalty reaches the
model as `utilityOfLineSwitch = -2.2614`, which is 8 minutes at the trip-weighted
16.96 AUD/h.

So the registry copy is a **mirror**, and `check_legacy_drift.py` pins the
registry to source *constants*, not to a params file. **The pair was unpinned.**
All eleven comparable values agree today; a check now asserts it, because two
copies of a number is the drift this package cannot absorb.

---

## 9.17 The §8.5 departure: a car passenger pays for the kilometre (P4 stage 5, issue #16)

**Logged before the result it will be judged on.** §8.5 requires a departure to
be recorded *before* results are seen, and this section is written while the
`cordon_escort_10pct` run is still at iteration 161 of 250, before any fit has
been computed on it.

**What had been seen, stated rather than glossed:** the intermediate
`modestats.csv` of that run up to iteration 161. That file records the mode
agents *chose*, not trips that *completed* (§9.12), it is far short of
relaxation, and — the part that matters — **neither piece of evidence for this
departure comes from it.** Both were measured on the `ride_sufficiency_*` runs
and are recorded in §9.12 and §9.13, before the demand repair existed.

### The departure

`C.scoring.monetary_distance_rate['ride']` moves from **0.0** to **−0.00018
AUD/m**, the car rate.

### Why this is a correction, not a calibration

§9.8 set the rate to zero and declared it **derived, not assumed**, on this
identity: *a vehicle's operating cost is paid once, and at occupancy 1.35
charging both occupants makes aggregate vehicle operating cost 1.35× the real
one.*

**That identity is true, and it is about the wrong quantity.** It is a statement
about **aggregate system cost accounting** — do not count the same litre of fuel
twice when totting up what the region spends. `monetaryDistanceRate` is not that.
In MATSim it is the cost **perceived by one person weighing one alternative**.
The identity was applied to a term it does not govern.

Stated as the identity that now applies: **a kilometre in a car costs the same
kilometre whether you are in the driver's seat or beside it.** The rate is still
*derived* — derived from the car rate, because it is the same vehicle — rather
than assumed or fitted.

### The observable that falsified the old identity, and it is not a target

§9.13 measured trip length by mode against the HTS, as a **constraint** that is
reported and never scored:

| | modelled | observed |
|---|---:|---:|
| ride ÷ car trip length | **1.372** | **0.961** |

Observed passenger trips are slightly **shorter** than driver trips. The model
made them **43% longer**, and the distortion **widened with sample fraction**
(1.075 → 1.346 → 1.372). §9.13 named it at the time: *"the signature the §9.8
zero distance rate would produce."* A mode with no marginal cost of distance is
chosen disproportionately for long trips, which is exactly what was measured.

This matters for the integrity of the departure: the evidence is a **constraint**
in the C4 sense, not one of the 67 calibration targets and not a holdout row. The
correction is justified without reference to any target the model is scored
against, so it cannot be a case of fitting the answer.

§9.8's own field description also anticipated it: *"with ride at zero and no
driver-availability constraint, ride is cheaper than car on any trip longer than
about 4.7 km. That asymmetry is real."* It is now removed rather than left for
the constant to absorb.

### What this deliberately is NOT

**It is not solving `asc_car_passenger` harder.** The constant stays where §9.8
constrained it, at −0.85, tied to observed vehicle occupancy. Proposal §9 names
ASC absorption as the primary threat to validity, and moving a distance rate that
was mis-specified is the opposite of absorbing a specification error into a
constant. `calibrate.py` cannot reach the mode constants at all — they are
`held_fixed`.

**It is not the whole of #16.** The second candidate — a zero-PCE queued `ride`,
so that a car passenger experiences congestion instead of being teleported at the
router's free-flow estimate — remains **scoped and unapplied**. It addresses a
separately measured distortion: `ride` runs **15–22% faster per kilometre than
car in every distance band**, with identical leg composition and near-identical
routed detour (1.4490 against 1.4716). A passenger physically travels in a car
and cannot arrive sooner than one.

That candidate is deliberately **not** applied in the same change, for two
reasons. It alters the mobsim rather than the scoring, so it must ship with its
own measurement — `ride` minutes per kilometre must converge on `car`'s, and
`vol_car` at the 33 count stations must not move, or §12.2a's count identity
breaks. And applying two corrections at once makes neither attributable. This one
is the larger lever and the better evidenced; it goes first, and the second is
decided on what it leaves behind.

### What would falsify this departure

If `ride` overshoots **below** the observed 20.6% share, or if the ride ÷ car
trip-length ratio overshoots below the observed 0.961, the rate is doing more
work than the correction justifies and the second candidate must not be added on
top of it. Both are recorded here **before** the run that tests them.

---

## 9.18 The light rail vehicle carries the capacity that was published (P4 stage 6, issue #18)

**Three numbers described one vehicle and none of them agreed.** The mapped
fleet gave the tram **180 seats and no standing room**; `DECISIONS.md` §4.1
records a published CAF Urbos 100 maximum of **270** and an assumed
`capacity_seated` of **60**. 180 reconciles with neither.

180 is not a Newcastle figure at all — it is **pt2matsim's generic tram
default**, and the zero standing room is a flag the build never set. So was
every other vehicle's: bus, rail and ferry are all seats-only.

### Why the second half was worse than the first

Because **no vehicle in the fleet had standing room**, the C1 crowding
multipliers (1.00 seated / 1.45 standing) were **inert by construction**.
Standing never occurred, so a multiplier on standing could never apply, in any
scenario. That is the §9.3 pattern again and the issue #21 defect class: a
declared parameter that reaches nothing produces a sensitivity band of zero and
would be reported as "insensitive to crowding" when the truth is "crowding
cannot happen here".

### The decision

| field | value | source |
|---|---:|---|
| `A.lightrail.capacity_total` | **270** | **observed** — published, §4.1 |
| `A.lightrail.capacity_seated` | **60** | **assumed**, swept 50–80 |
| `A.lightrail.capacity_standing` | **210** | **derived** — total − seated |

Only the *split* is assumed; the total it is taken from is published. The
standing figure is not a free value and carries no sweep of its own, because it
is whatever the published maximum leaves once the seats are removed — the
`derived_from` identity the schema requires instead of an invented interval.

Applied in `build_matsim_run_inputs.py`, over the **already-mapped** fleet.
The schedule mapper is not re-run, so §3.5 holds unchanged.

### What is deliberately NOT done

**Bus, rail and ferry keep their pt2matsim defaults and keep no standing room.**
This package holds a published capacity for the light rail vehicle — the object
of study — and holds none for a Newcastle bus, a Hunter Line car or the Stockton
ferry. Setting a standing figure for those would be inventing an observation,
which is the one failure this project cannot absorb. **It is recorded as a
limitation and is the open half of issue #18**, to be closed by a source or by
an explicit swept assumption, not by a number chosen here.

**Consequence to carry:** light rail capacity rises 180 → 270 per vehicle, which
is +50%, and it moves the ceiling on hypothesis A1's own metric. No result
existed when this was taken.

---

## 9.19 A live view of a run, and why it is not a live map (P4 stage 6)

`src/analyse/run_monitor.py` serves a run in flight on loopback; `run_matsim.py`
prints the url as it launches MATSim.

**It is an observer.** It reads the run directory, holds no lock, opens nothing
the run is writing to and writes nothing itself. It is not in `_run.json` and
not part of the run identity: a run observed is byte-for-byte a run unobserved.
`RUN.monitor.enabled` turns it off.

### Why it shows progress and convergence rather than vehicles

A live *map* was measured and rejected on the measurement, not on effort.
Events are written only every `RUN.controler.write_events_interval` = **10**
iterations. When they are written, the file grows at **~5.2 MB/s** and the whole
30 h simulated day lands in about **50 s** of wall clock — roughly **2,000×
real time** — then nothing for ~3.5 minutes until the next events iteration.
A partial gzip does decode cleanly (a 10 MiB prefix yields 93.8 MB of XML to
simulated 07:15), so the *plumbing* would work; there is simply no steady stream
to watch. A live map would show a flicker and then a blank screen.

What changes at a human pace is **progress** and **convergence**, so that is what
is served: iteration against target with an ETA from the observed iteration
time, the mode trajectory, the score trajectory, and the drift after innovation
switches off — which is the direct read on the question issue #5 turns on.

**The mode trajectory is `modestats`, and the page says so on its face:** the
mode agents *chose*, not trips that *completed* (§9.12). `extract_metrics.py` →
`fit.py` remains the only route to a reportable number.

`replay_events.py` is unaffected and remains the instrument for what a finished
run did in space.

---

## 9.20 A count of one road is not a count of its neighbour (P4 stage 6, issues #20, #10)

`map_count_stations.py` matched a station on road name **and** proximity where a
name existed, and fell back to the **nearest link of any name** where it did
not. The fallback was doing more work than intended, and in two directions.

### It was rejecting matches that were the same road

| station | link it was attached to | distance | what it is |
|---|---|---:|---|
| Red Head Road | **Redhead** Road | 46.4 m | one road, spaced two ways |
| St James Road | **Saint** James Road | 25.9 m | RMS abbreviates, OSM does not |
| Werribi Street | Werribi Street **(West)** | 23.0 m | OSM carries a qualifier, the station does not |

All three were being recorded as `proximity_only` — a weaker claim than the
truth. `normalise` now folds `saint`→`st` as it already folded `street`, drops a
parenthetical qualifier, and a second naming tier compares with spaces removed.

### It was accepting matches that were a different road

The other nine fallbacks attached a station to a road it does not count. The
clearest is **Raymond Terrace Road** (V096, observed **11,810 AADT**), attached
at 107.9 m to **Dockyard Road** — one lane, 50 km/h, which is not a plausible
carrier of 11,810 vehicles a day — and then **scored against it**. Also
**Pacific Motorway** to a *George Booth Drive Offramp*, and **Nelson Bay Road**
to *Teal Street*.

**The rule now: a station that names its road may only be matched to a link
bearing that name.** Where none is in range the station is reported unmatched,
with the count of nearby links that were deliberately *not* taken. Proximity
alone still matches a station that names no road.

**Every one of the 195 matched links is now `name_and_proximity`; zero are
proximity-only.**

### This moves the reported count fit, and in which direction matters

| | before | after |
|---|---:|---:|
| stations matched | 116 | **111** |
| links | 203 | **195** |
| proximity-only | 14 | **0** |
| count stations scored | 33 | **30** |
| mean count error | −72.2% | **−69.9%** |
| modelled zeros | 2 (V096, V113) | **1 (V113)** |

The fit **improves by 2.3 pp, and that improvement is not the model getting
better** — it is a wrong comparison being withdrawn. This has to be stated
plainly because it is the shape of the #19 defect running backwards: #19 was a
station being dropped *because* the model failed on it, which flattered the fit.
Here a station leaves the scored set because the link was never its road. The
test that separates the two is whether the reason survives inspection without
reference to the model's answer, and V096's does: *Dockyard Road is not Raymond
Terrace Road*, which was true before any run existed.

**The M1 at Wyee (V113) is untouched and still scores −100%.** It matched by
name, on both carriageways, at 67.3 m and 68.3 m. That was the point of
separating the two halves of #20: the mis-match is a mapping fault and is now
fixed; **the modelled zero on the M1 is a demand fault and is not**, and it
stays visible in the fit. §9.14's consequence stands unchanged — no count-based
calibration until the boundary through-traffic question is settled.

**Issue #10 is answered rather than fixed.** Tarean Road, The Bucketts Way and
one Nelson Bay Road station have **no car link within 120 m in any direction**:
they lie outside the five-LGA clip, which is a scope decision (§1, decision 3),
not an oversight. Extending the clip would mean rebuilding the network and
re-running the schedule mapper, which §3.5 forbids for anything already run.
They are reported with that reason and are not dropped.

---

## 9.21 What a wide data search settled, and what it did not (P4 stage 7)

The three unobtained inputs (§0, §13) and the undeclared fleet capacities (§9.18)
were searched for exhaustively rather than assumed to be unavailable. The result
changes the *status* of two of them from "request outstanding" to something
firmer, and it produces real vehicle figures for the first time.

### SCATS phasing is refused by policy, and that is now citable

**This is no longer an outstanding request. It is a documented refusal.** In
April 2025 WalkSydney, Better Streets and Jake Coppinger formally requested
SCATS signal phasing data. Transport for NSW replied that it *"does not publish
the SCATS Signal Phasing data you requested and currently has no plans to make
this information publicly available"*, and maintained that position through
follow-up correspondence and a meeting in July 2025. **Western Australia
publishes the equivalent data freely.**

Two consequences, and the second is binding:

1. **Proposal §7.2's "No SCATS" contingency is the operative path, not a
   hypothetical.** It requires signal delay to be inferred from GTFS-Realtime
   run-time distributions, cycle time and priority to be **swept**, and — the
   part that binds every future headline — *"state the resulting uncertainty
   band explicitly in all headline figures."* `A.signals.scats_phasing` stays
   `unobtained` with its three-way categorical sweep, and the corridor result
   may never be quoted as a point estimate.
2. **It is a finding, not only a gap.** The proposal already argues that the
   absence of ex-post evaluation is a governance choice rather than a technical
   limit. A refusal to release the phasing data that would let anyone else check
   a corridor claim is the same argument with a citation attached, and it
   belongs in deliverable 6 (the method note on evaluation gaps).

### Journey-linked Opal is not published, and our own fallback was never built

Only aggregate trip counts are published, which is what the package already
holds. A privacy-preserving unit-record sample was released with CSIRO Data61,
but it is Sydney and pre-dates the light rail opening, so it cannot inform a
Newcastle transfer penalty.

**The more useful finding is about this project rather than about TfNSW.**
Proposal §7.2 specifies what to do when this request fails: *"estimate transfer
rates from tap-on/tap-off timing at the Interchange using aggregate stop-level
data plus a matching model, validate against the published interchange
percentages."* **That was never built.** `C.transfer.beta_transfer_penalty_min`
is consumed by `build_params.py` and `build_matsim_run_inputs.py` and is
estimated by nothing; the package holds `lr_tapon_share_by_stop` and the station
entry/exit series the method would need. The fallback was skipped in favour of
sweeping, and sweeping is what §7.2 permits only *after* the estimate is
attempted. **This is a missing deliverable, not a missing dataset.**

**One incidental confirmation.** TfNSW records that from 1 July 2024,
aggregations between line, agency and mode are no longer valid because a
passenger may use several lines on one trip. That is independent operator
confirmation of the §12 trap on hypothesis A1's denominator, which until now
rested on our own reading.

### Charging dwell has no published figure

WSP and Aurecon both describe the charge-bar system; neither publishes a
duration. §4.3's assessment — *"not published anywhere"* — survives the search.
`A.lightrail.dwell_charging_s` stays `unobtained`, swept 10–35 s.

**A false lead is recorded so it is not re-followed.** A search summary asserted
20–30 s at each stop and attributed it to the Newcastle Light Rail encyclopaedia
entry. **The page does not contain that figure.** It was not adopted. Anything
that reaches this model must be read from the source, not from a summary of it.

### The fleet, and every capacity in it was too generous

The mapped fleet is pt2matsim's generic defaults (§9.18). Published figures were
found for three of the four vehicle types:

| vehicle | published | model carried |
|---|---|---|
| Stockton ferry (MV Shortland / MV Hunter) | **200 total, 149 seated** | 250 seats, 0 standing |
| Hunter railcar | **77 (HM) / 69 (HMT) per car**, 7 two-car sets | 400 seats, 0 standing |
| Endeavour railcar | **95 (LE) / 82 (TE) per car** | *(same `Rail` type)* |
| Volvo B12BLE bus | **44 seated + 18 standing = 62** | 70 seats, 0 standing |
| Volvo B10B bus | **51 seated** | |

**Every one of them overstates capacity** — rail by roughly 2.7x on a two-car
set, ferry by 25%, bus seats by about 59%. That is consistent with, and
partially explains, §9.12's finding that transit capacity never binds: some of
the headroom was fictional. Newcastle still operates an almost entirely diesel
bus fleet — three battery-electric buses — so the Volvo figures are the right
basis rather than the zero-emission models now entering service elsewhere.

**Source grade, stated rather than glossed.** These are encyclopaedia and
enthusiast-maintained fleet pages, not operator or manufacturer publications;
the authoritative Australian fleet list refused automated access. They therefore
enter the registry as `literature` **with their urls**, and **swept** — not as
`observed`, which this package reserves for a value read from a source it
downloaded itself. That is a weaker claim than §9.18's light rail figure, whose
270 is a published manufacturer maximum, and the difference is deliberate.

### Taxi, motorcycle and rideshare cannot be separated

The HTS tables this package holds report **"Other" as a single bucket**. No
observed decomposition into taxi, motorcycle and rideshare exists in the
package or in the open data searched. IPART runs an annual Survey of Point to
Point Transport Use, but it measures *usage incidence* among NSW residents, not
trip mode share for Newcastle, so it can suggest a split and cannot validate
one.

**Adding three modes with no target for any of them would add structure that
cannot be falsified**, which is the opposite of what this project is for. The
single approximate mode stays, and stays labelled approximate in `fit.py`.

---

## 9.22 Three decisions taken, and the carried-over work re-prioritised (P4 stage 7)

Three questions that had been open for the user rather than for the code were
put and answered on 12 August 2026.

### 1. The §8.5 question is DEFERRED, not answered

Deliverable 5 needs a ruling on whether the mode constants may move, and there
were three ways forward (§9.16). **The decision is to take none of them yet, and
to revisit after deliverable 0a.**

The reasoning is that the fit is currently wrong in a way nobody has explained:
car **32.5%** against an observed **59.0%**, car passenger **50.0%** against
**20.6%**, and the §9.15 demand repair moved car by 1.69 pp. Seven defects have
already been found in this model and **every one produced a confident wrong
answer rather than an obvious failure**. If 0a finds an eighth, the fit may move
without touching a constant.

**Choosing branch (b) — re-opening §8.5 — to fix what turns out to be a bug
would be the exact failure proposal §9 names as the primary threat to
validity**, and it would be unrecoverable: once a constant has absorbed a
specification error, no later run can tell you it did. Deferring costs nothing,
because 0a has to happen regardless.

### 2. The run programme is cut, and one fifth of it was never doing anything

Issue #6. The specified load is 140 sweep points × 10 scenarios + 10 scenarios ×
30 replications, each over three day types = **5,100 run-days ≈ 765 days of wall
clock** at 25%.

**A fifth of it required no decision at all.** The grid was 7 × 5 × 4 over
`beta_transfer_penalty_min`, `walk_decay_beta_per_m` and `dwell_charging_s`.
**`walk_decay_beta_per_m` reaches the model through nothing** (issue #21): zero
occurrences in the generated config, and it is named in `not_representable` for
that reason. Sweeping it five ways produces a sensitivity band of exactly zero
**by construction**, which would be reported as *"insensitive to walk access"*
when the truth is *"walk decay is not in the model"*. That is a false negative in
a sensitivity analysis, and worse than an absent one.

**The grid is cut from 140 to 28 points**, and the axis returns the day the decay
curve reaches the model, not before. This is a defect fix, not a scope cut:
**112 of the 140 points could not have differed from another point for any reason
a reader would care about.**

The remaining cuts are scope decisions and were approved:

| cut | run-days | wall clock at 25% |
|---|---:|---:|
| as specified | 5,100 | ~765 days |
| drop the axis that reaches nothing | 1,740 | ~284 days |
| + sweep **weekday only** | 1,180 | ~193 days |
| + replications 30 → 5 | 430 | ~70 days |
| + sweep only the decisive contrasts (S2vS0, S2vS2b) | **262** | **~43 days** |

At 25% a run needs 31.5 GiB, so **two fit concurrently in 63.5 GiB** — roughly
**three weeks of wall clock**, which is the first version of this programme that
this machine can actually execute.

**Replications are to be measured, not assumed.** `E.replication.n_replications`
is 30 with a declared range of 5–30; the 5 above is a planning figure and the
value must come from **measured seed variance**, which is cheap. Until that
measurement exists the 5 is provisional and is recorded as such.

### 3. The two refusals are confirmed

Both were requested directly and both were declined; the user confirmed the
refusals stand.

- **The 143 holdout targets stay closed.** They are the only test the model has.
  The 67/143 split was fixed before any fitting precisely so that no target can
  move after a result is seen. They open **once**, at the end. A new observable
  becomes a **constraint** (the §9.8 / §9.13 pattern), never a target.
- **The 13 Opal card-type targets are not deleted.** They are calibration rows
  inside the pre-registered 210 and cannot be scored, because MATSim has no
  fare-product dimension. Deleting them retrospectively would change a set fixed
  in advance — the move that would let anyone quietly drop whatever the model
  fails at. They are reported with the reason instead.

### 4. Carried-over work from P0–P2, re-prioritised

Verifying the phase board (`STATUS.md`) found work carried from earlier phases
that no deliverable owned. Two items are now urgent for reasons that did not
apply when they were first listed.

**GTFS-Realtime collection was judged to be on the critical path here. That
judgement was overturned in §9.23 and this paragraph is superseded.** §13 item 10 says *"start now; it is the fallback for both dwell and
signal delay, and it accrues only forward."* **No collection exists** — verified,
the only reference in `src/` is a note naming it as an acquisition route. That
was tolerable while SCATS was merely unobtained. **§9.21 established that SCATS
is refused by policy**, which makes proposal §7.2's contingency the operative
path — and §7.2 requires signal delay to be *"inferred from GTFS-Realtime
run-time distributions."* **The fallback for the largest single uncertainty in
the model depends on a dataset nobody is collecting, and every day of delay is a
day of it permanently lost.** It is cheap to start and impossible to backfill.

**The corridor's road attributes are mostly imputed, and B3 rests on them.**
Measured over the 714 corridor and parallel edges:

| field | observed in OSM | imputed |
|---|---:|---:|
| speed limit | 639 | 75 |
| one-way | 475 | 239 |
| lane count | 435 | **279** |
| turn lanes | 70 | **644 absent** |
| kerbside | 36 | **678** |
| lane width | 10 | **704** |
| capacity | 0 | **714** |

§2.5's *"87.5% of as-built trunk lane counts are observed"* is true and is about
the **40 trunk edges**; it is not a statement about the 714. **Kerbside is 95%
imputed, lane width 98.6%, capacity 100%** — and B3, *"the decisive test of
Claim B"*, is precisely the hypothesis that turns on lane loss, banned turns and
kerbside parking removal. §13 item 4 named this and nothing owned it.

**Also carried, and now explicitly owned rather than floating:** the charging
dwell field measurement (§13 item 2, physical, one visit), pedestrian counts
(§13 item 6 — B1 has no observable at all without them), retail vacancy (§13
item 7 — `D.retail.vacancy_rate` is `unobtained` and B2 depends on it), the ABS
journey-to-work table (§13 item 11, obtainable, settles a swept parameter), and
the 2014 timetable (§13 item 8, validates the era-1 reconstruction).

**What this changes:** these are not P4 calibration work, and pretending
otherwise is how they stayed unowned. They are recorded in `STATUS.md` as
**carried-over deliverables with an explicit owner phase and priority**, and the
two urgent ones are issues rather than list items.

---

## 9.23 Own collection dropped, and what the published catalogue actually holds (P4 stage 8)

An Open Data Hub API key was obtained. That changed the option set that had made
own GTFS-Realtime collection look like the only path (§9.22), so the collector
built earlier in that stage was **reverted in full** and issue #26 closed as not
planned. This section records what the published catalogue was found to contain,
because the assessment is the thing that justifies the reversal.

### The archive that would have replaced collection covers the wrong modes

TfNSW publishes **Historical GTFS and GTFS Realtime** — trip updates, vehicle
positions and timetable — through `POST /v1/gtfs/historical`. Its documentation
says Metro and Ferry only. That was verified against the live API rather than
taken from the page:

| request | files returned |
|---|---|
| `FER` / `SydneyFerries` / `TripUpdate`, the documented sample dates | **3** |
| `MET` / `Metro` / `VehiclePosition`, 2024 and 2026 | **5** each |
| every light rail naming tried (`LRT`, `LR`, `NLR` × `NewcastleLightRail`, `LightRail`) | **0** |
| `BUS` / `Buses` | **0** |

The controls return files, so the empty light rail results are the archive's
content and not a malformed request. **The archive cannot backfill Newcastle.**

This leaves proposal §7.2's contingency for the SCATS refusal without a realtime
source. That is recorded as an **open gap**, not a solved one. What it does not
justify is standing up an unbounded rolling stream for months before the rest of
the catalogue has been worked: the published data settles several things the
stream never would, and it settles them today rather than in a quarter.

### The catalogue, enumerated

230 datasets, pulled from the CKAN endpoint
`/data/api/3/action/package_search` and matched against the registry's **6
unobtained** and **78 assumed** fields and the open issues.

### What it settles — verified against the data, not the title

**Traffic Lights Location — the strongest hit, and it lands on the corridor.**
4,582 signals statewide with `Equipment_ID`, cross streets, suburb, install date
and coordinates. **352 fall in the study area; all 14 distinct corridor
intersections in `A2_signal_control_corridor.csv` match one within 60 m** (most
within 10 m). Three consequences:

- `scats_site_id` in that artefact is a **declared but empty column** on all 70
  rows. `Equipment_ID` *is* the SCATS site number, so the column can be filled
  from an observed source.
- **8 of the 14 corridor signals were installed in 2018**, four of them in the
  September batch along Scott St and two named `LIGHT RAIL CROSSING`. The
  pre-light-rail corridor had **6** signalised intersections, not 14. That is an
  observed, dated basis for a counterfactual the model currently assumes.
- The signal inventory is currently OSM-inferred (`A2_signal_nodes_osm.csv`,
  1,265 nodes). This is an independent observed source to validate it against.

**Strategic Freight Model 2022 (SFM22).** NSW freight commodity movements on an
**origin-destination basis**, 20 commodity groups, road and rail, 2021–2061, as
a flat file with a data dictionary. Issue #24's freight layer currently has
nothing but a measured 6.52% heavy-vehicle share to work from.

**Reference Tables for TfNSW GTFS feeds.** Carries `IC-Hunter Line - Up` and
`- Dn` running-time tables (March 2026) and the turn-up-and-go frequency list.
Bears directly on `A.transit.era1_line_speed_kmh` and `era1_station_dwell_s`,
both assumed, and on the era-1 reconstruction that has no 2014 timetable.

**School and public holidays.** NSW public holidays and public-school term dates
as CSV. The RMS hourly counts carry dates, so this is the join that turns them
into a school-term / holiday / public-holiday stratification — which is what
`B.activity.sat_to_sun_rate` and the day-type shape need (§13 item 12).

**Covid-19 TfNSW Vehicle Capacity.** Vehicle capacity by transport class across
several restriction levels. Relevant to issue #18, with the obvious caveat that
a physical-distancing capacity is not a normal one; only a baseline column would
be usable, and it enters as `literature` with a url, swept — never `observed`.

**Opal Tap On and Tap Off, Release 3.** Tap counts by **time and location** for
four separate weeks in 2020, all four modes. Finer than the monthly series the
package holds. It is **not journey-linked** — there is no card-level chaining —
so `B.opal.journey_linked` stays `unobtained` and deliverable 8 keeps its §7.2
fallback.

### What it does not settle, recorded so it is not re-searched

- **No SCATS phase data anywhere in the catalogue.** §9.21 stands.
- **Kerbside, lane width, turn lanes and capacity for the corridor are still
  imputed.** The four datasets that look like the answer — Loading Zones
  Kerbside, Off-Street Parking, Bus Lanes, NSW Clearways and NSW Transit Lanes —
  are **Sydney-only** by their own descriptions, so the four fields #27 turns on
  still need their own survey. **One exception, verified since:** `speed_limit` is
  only 10.5% imputed (75 of 714 corridor edges) and Speed Zones is statewide, so
  that part is closable from published data.
- **Journey to Work 2016 was withdrawn by TfNSW** for re-identification risk and
  must come from the ABS. JTW 2006 and 2011 remain available with travel-zone
  geography, so `B.external.interaction_rate` can be settled on an older vintage
  or wait for the ABS extract.
- **Speed Zones** is statewide and covers Newcastle, but the CSV resource carries
  attributes with **no geometry**; the usable form is the shapefile.
- **Historic Roads Travel Time (TTDS)** is GPS speed traces with speed limits,
  which is the right shape for road signal delay — but only four weeks of 2016
  and two months of 2017, and its area coverage is unverified.

### What this does not do

No value has been changed. Nothing here has been acquired, written to
`data/raw/`, or entered in the registry: this is an assessment of what is
available and what it would settle. Each item above becomes an acquisition with
a provenance record and a registry field of its own, or it does not happen.
`A.lightrail.dwell_charging_s`, `A.signals.scats_phasing` and
`B.opal.journey_linked` all remain `unobtained` and swept.

---

## 9.24 The corridor signals acquire their real identity, and a dated counterfactual appears (P4 stage 9)

`A2_signal_control_corridor.csv` has declared a `scats_site_id` column since P2
and left it empty on all 70 rows. The corridor intersections are clusters of OSM
traffic-signal nodes, so they carried no identifier that anything outside this
package would recognise. TfNSW's **Traffic Lights Location** dataset (§9.23)
supplies one: `Equipment_ID` *is* the SCATS site number.

### The join, and why its tolerance is held fixed rather than swept

4,582 signals statewide, matched by distance to the 14 corridor intersections.
No bounding box is applied first — scanning the whole inventory is trivial, and a
bbox would be one more undeclared constant deciding which observations are
eligible.

**All 14 matched, at a mean of 8.0 m and a maximum of 26.4 m.** Nothing is
unmatched, and an unmatched intersection would have been written with
`scats_source='unmatched'` and blank fields rather than dropped or given a
neighbour's id.

`A.signals.scats_match_radius_m` is declared at 60 m and **held fixed**, not
swept. The rule is recorded in the registry: no behaviour, run time or score
reads it — only the identity written into the artefact — and every radius from
the 45 m OSM clustering distance up to roughly 100 m produces the identical
assignment, because the furthest true match is 26.4 m. Declaring a sweep
interval across which the output cannot vary is the defect this project has
already hit three times (issues #21, #12, and 112 wasted grid points). Departure
requires a re-measured distance distribution, not a preference.

This also migrates `build_corridor_layers.py` onto the registry, which it had
never read.

### Eight of the fourteen corridor signals were installed for the light rail

The inventory carries an installation date, now written to `signal_installed`:

| era | count | examples |
|---|---:|---|
| 2018 | **8** | 4762 *Stewart Av / light rail crossing* (Nov 2018), 4770 *Steel St / light rail crossing* (Nov 2018), 4766–4769 along Scott St (Sep 2018) |
| pre-2018 | 6 | 782 Hunter/Auckland (1973), 1655 Hunter/Darby (1981), 1875 Scott/Watt (1988) |

**The pre-intervention corridor carried 6 signalised intersections, not 14.**
That is an observed, dated fact about the counterfactual the B3 test rests on,
and the model currently assumes a corridor whose signal count does not vary by
era.

### What has deliberately NOT been changed

**Nothing downstream.** The date is recorded as an attribute and no scenario, no
variant and no parameter has been altered by it. `S0_no_tram` still carries all
14 intersections at a 100 s cycle, exactly as before.

**The decision was taken on 12 August 2026: no.** The pre-light-rail corridor
keeps all 14 signalised intersections in `S0_no_tram`, and the install dates
stay an attribute. Re-deriving the counterfactual from this observation would
reshape the same quantity that
`A.corridor.pre_lr_lanes_per_dir` encodes — and that constant *is* the B3
hypothesis, the decisive test of Claim B. Changing the hypothesis to fit an
observation discovered afterwards is the move proposal §9 names as the primary
threat to validity. It is held for an explicit decision, with the evidence now
on the table for that decision to be made against.

Note also what this does **not** supply: the inventory gives location, identity
and install date. It gives **no phase plan, no cycle time and no split**. SCATS
phasing remains refused (§9.21) and `A.signals.scats_phasing` remains
`unobtained` and swept. What has changed is that the corridor's signals can now
be named in a request, a citation or a SUMO controller — not that their
operation is known.

---

## 9.25 The specification audit: two inversions, not five miscalibrations (P4 deliverable 0a)

Deliverable 0a ran first because mode share was wrong in a way nobody had
explained, and calibrating on top of an unexplained error fits it into a
constant. The full ranked register is [`docs/SPEC_AUDIT.md`](docs/SPEC_AUDIT.md);
this records what it changes.

**The symptom is two near-exact inversions, not five independent errors.** Car
-26.5 against ride +29.4, and walk -12.7 against bike +12.7. That pattern points
at structural asymmetries moving pairs of modes, not at five constants set
wrongly - which is why the audit looked at how modes are simulated rather than
at what they score.

**A1, and it is physically impossible.** `qsim.mainMode = car` while
`routing.networkModes = car,ride`, so `ride` is routed over the network and given
free-flow link times: it never queues and never contributes to congestion.
Measured over a completed 250-iteration run, **ride realises 55.7 km/h against
car's 49.3**. That aggregate overstates it - ride legs are longer and longer
trips use faster roads - and the corrected figure is **4-8%, present in every
distance bin from under 2 km to over 40 km**, which a composition artefact
would not survive. A car passenger arrives faster than the car carrying them.
The scoring config makes ride look *dominated* (identical time and money
disutility, and a -0.85 constant against car's 0.0), so nobody reading the
behavioural parameters would find this. It is worst exactly where car is most
congested, which is the peak and the corridor. Issue #28.

**A2 and A3 push the same way.** `ride` is not a chain-based mode while `car` is,
so a subtour adopts ride freely but must conserve a car; and the 9.11 ride
constraint is choice-set only, so one household driver can chauffeur unlimited
simultaneous passengers (#31). Separately, **car is the only mode whose ownership
is modelled** - bike is available to every agent always, and returns 15.86%
against an observed 3.2% (#29). A4 records that walk's 18x deficit may be a
trip-length problem rather than a scoring one, and names the test (#30).

**B1 is the finding that prevented damage.** Issue #24 states that work-related
business travel is an observed HTS purpose the model does not generate. **It
does.** B2 carries 47,612 weekday `WB` legs, **2.11%** of all legs, against an
HTS Newcastle figure of **2.0%**. Building it as scoped would have double-counted
an already-correct purpose and moved mode share for a reason no later run could
attribute. #24 is narrowed to freight, which does stand, as does #20 - external
legs are 0.48% of the total and every one terminates inside the study area.

**A caution about the registry's own defect detector.** `consumers` is generated
from read logging and is stale: three light rail capacity fields list no
consumers while `build_matsim_run_inputs.py` reads two of them. An empty
`consumers` means the generator has not seen the field, **not** that nothing
reads it, so it can neither confirm nor deny reach. Reach must be established by
changing a value and observing the output. This matters because "a declared,
swept parameter that reaches nothing" is a defect class this project has hit
three times and `consumers` is the mechanism used to catch it.

**Deliverable 0e is already satisfied** and its checklist entry was stale: the
`water` and `green` layers are annotated *"for the run replay basemap only"* in
`overpass.py` and are consumed by `build_basemap.py`.

**Nothing was changed by this audit.** No parameter, no target, no scenario. The
67/143 split is untouched and no holdout row was opened. The audit's product is
a register and four issues; the fixes are separate work, and #28 must land before
#9 is re-solved or #14 is attempted, because both would otherwise absorb it.

---

## 9.26 The passenger stops outrunning the driver, and the car–ride inversion mostly closes (P4 stage 10, issue #28)

> **CORRECTED BY §9.27.** The mode-share figures below were measured with both
> arms at 250 iterations, and that protocol is now known to sit ~13 percentage
> points of car share short of relaxation. The pre-fix model run to 1000
> iterations reaches a **better** fit (33.8 pp) than the post-fix model at 250
> (44.6 pp), so **most of the movement claimed here was the absence of
> relaxation, not the fix**. The physics defect and the fix stand; the claim that
> this was "the largest single correction" does not. Read §9.27 first.

§9.25 A1 found that `ride` sits in `routing.networkModes` but is not the qsim
`mainMode`, so MATSim routed it over the network on **free-flow** link times: a
car passenger never queued, never waited, and never met the congestion the
driver met. `WickhamControler` now binds `ride`'s travel time to
`networkTravelTime()` and its disutility to the car factory, so a passenger is
priced with the congested car times.

It deliberately does **not** put a ride vehicle in the mobsim. A passenger
travels in a car that is already there; a second vehicle would double-count the
traffic. So `ride` now *experiences* congestion without *causing* it — correct
only insofar as every ride trip is paired with a driver trip, and it is not.
That is issue #31, still open.

### What it moved

Two runs at 10%, 250 iterations, seed 20260810, 8 threads — **identical but for
the controler**. Newcastle LGA, linked trips, the figures comparable to the
target (§9.13):

| mode | before | after | change | target |
|---|---:|---:|---:|---:|
| car | 32.54% | **52.30%** | **+19.76** | 59.0% |
| ride | 50.03% | **29.45%** | **−20.58** | 20.6% |
| walk | 0.75% | 0.71% | −0.03 | 13.4% |
| bike | 15.86% | 16.67% | +0.81 | 3.2% |
| pt | 0.83% | 0.88% | +0.05 | 3.8% |

**Total absolute gap to target: 84.2 → 44.6 percentage points.** The largest
single correction this model has had, and it came from a defect rather than a
constant.

**It also confirms the audit's central claim.** §9.25 argued the symptom was
*two* inversions, not five miscalibrated constants. Fixing the car↔ride
mechanism moved car and ride by ±20 points and left walk↔bike **untouched**
(−0.03 / +0.81). Two independent mechanisms, exactly as the register predicted.
Walk and bike are #30 and #29.

### The defect is reduced, not eliminated

Ride is still faster than car at matched distance. Both runs, ride/car speed
ratio by leg distance:

| distance | before | after |
|---|---:|---:|
| 0–2 km | 1.08× | **1.11×** |
| 2–5 km | 1.08× | 1.07× |
| 5–10 km | 1.08× | 1.05× |
| 10–20 km | 1.06× | 1.04× |
| 20–40 km | 1.04× | 1.02× |
| 40 km+ | 1.04× | **1.01×** |

The advantage collapses on long trips and **grows on short ones**. Two
mechanisms are consistent with that and this section does not separate them: the
router prices `ride` from the *previous* iteration's travel times while `car`
realises the current one, which matters more the further from relaxation the run
is (#5); and a teleported leg never pays the junction queueing that dominates a
short trip. **#28 stays open on the residual.**

### Why the first verification was thrown away

It ran at 1% and was uninterpretable. §15 records that MATSim floors link storage
at one vehicle, so a 1% sample produces **spurious spillback that inflates car
delay** — and `ride`, being teleported, is immune to precisely that. It
penalises car by construction and widens the gap the fix exists to close. It
duly showed ride 1.14–1.25× faster, which says nothing. **A fraction-sensitive
artefact makes a cross-fraction comparison invalid**, so the verification was
re-run at the baseline's own 10%.

### Two reproducibility defects the fix exposed

**Nothing compiled the Java.** `run_matsim.py` runs `wickham.WickhamControler`,
the source is committed, `.tools/` is gitignored, and no script built one from
the other — the classes had been made by hand. A fresh clone held the source,
the jar, and no way to run. `bootstrap_toolchain.py` now compiles with the
pinned `javac` against the pinned jar, on the fetch path and the `--verify` path.

**A run record could not say which controler produced it.** The run name is built
from the scenario and the registry values, which cannot see the controler.
Re-running after this change would have found the old `_run.json` and returned
the **pre-fix** result silently, with nothing to tell the two apart. Records now
carry `controler_sha256` over the committed Java source, it is declared in the
run contract, and the harness re-runs rather than resuming across a change. It is
also why the verification ran under its own tag: the harness deletes a run
directory before repeating it, and the only pre-fix baseline in existence sat in
the directory the new run would have claimed.

### What this is not

**Not a result.** 250 iterations is measurably short of relaxation (§9.7), the
demand still lacks boundary through traffic and freight, and no count-based
calibration may be read from it (§9.14). **No target was fitted**: the mode share
moved because a defect was removed, not because anything was tuned. No parameter
value changed, the 67/143 split is untouched, and no holdout row was opened.

---

## 9.27 The model needs a thousand iterations, and most of §9.26 was measuring their absence (P4 stage 10, issue #5)

The 1000-iteration pilot at 10% finished: 41,860 s wall, median 34.2 s/iteration,
rc=0. It answers issue #5 and it **overturns the headline of §9.26**, which was
written before it landed.

### 250 iterations is not near relaxation, and every result to date used it

Largest single-mode change in the chosen-mode series across a window:

| window | max change | |
|---|---:|---|
| 100 → 250 | 0.1316 | |
| 250 → 500 | 0.0682 | |
| 500 → 800 | 0.0297 | |
| 800 → 900 | 0.0339 | innovation switches off at 800 |
| 900 → 950 | **0.00026** | flat |
| 950 → 1000 | **0.00032** | flat |
| 990 → 1000 | **0.00008** | flat |

The model relaxes about **100 iterations after innovation is disabled**, and is
flat from 900. Between the 250-iteration protocol and relaxation, chosen car
share moves **+0.1324** — thirteen percentage points.

**Every run this project has produced used 250 iterations.** DECISIONS.md §9.7
called that short; this measures how short.

### The correction to §9.26

§9.26 reported the #28 controler fix as *"the largest single correction this model
has had"*, on a 44.6 pp total gap against an 84.2 pp baseline. **Both figures were
taken at 250 iterations, and that baseline was broken.** Newcastle LGA, linked
trips:

| run | car | ride | walk | bike | pt | total gap |
|---|---:|---:|---:|---:|---:|---:|
| pre-fix, 250 iter | 32.54% | 50.03% | 0.75% | 15.86% | 0.83% | 84.2 |
| **pre-fix, 1000 iter** | **65.01%** | **22.25%** | 0.13% | 12.41% | 0.19% | **33.8** |
| post-fix, 250 iter | 52.30% | 29.45% | 0.71% | 16.67% | 0.88% | 44.6 |
| *target* | *59.0%* | *20.6%* | *13.4%* | *3.2%* | *3.8%* | |

**The pre-fix model, simply run to relaxation, fits better than the post-fix
model at 250 iterations.** So most of the ±20 point movement attributed to the
controler fix was the absence of relaxation, not the fix. The car↔ride inversion
was largely an artefact of reading an unconverged run.

This is the failure mode the specification audit exists to catch, produced by the
audit's own follow-up: a controlled comparison, correctly executed, at a protocol
that was itself invalid. **A comparison is only as good as the state both arms
are in.**

### What survives, and what changes

**The physics defect is not in question.** `ride` outran `car` at *every* matched
distance band, which is impossible for a passenger travelling in that car, and
the binding demonstrably narrows it (1.08→1.05 at 5–10 km, 1.04→1.01 above
40 km). The fix is correct and stays. What is withdrawn is the claim about how
much of the mode-share gap it closes; that is now being measured properly, by a
post-fix run at the same 1000 iterations, under its own tag so the pre-fix
relaxed baseline survives.

**The walk↔bike inversion is confirmed structural.** At relaxation it does not
improve — walk **0.13%** against 13.4% and bike **12.41%** against 3.2%, if
anything worse. Iterations do not touch it. §9.25's two-inversion reading holds,
but the two have different natures: car↔ride was mostly protocol, walk↔bike is
mechanism, and it is issues #30 and #29.

### Issue #5, and why it is not closed

The measured answer is **~1000 iterations**, with the caveat that
`fraction_to_disable_innovation` is a *fraction*, so a 900-iteration run would
disable innovation at 720 rather than 800 — this run shows that 1000 works, not
that 900 would.

`RUN.controler.last_iteration` **stays `unobtained`**. This measurement is on the
**pre-#28** model, and #29 and #30 will change the mode-choice landscape again.
Pinning a value measured on a specification that is being repaired would be
substituting one unjustified number for another, which is the whole reason the
field refuses a point value. It is re-measured once the mode-choice defects are
settled.

**The practical consequence is immediate regardless:** no run at 250 iterations
means anything, including every run in `results/` and both arms of §9.26.

---

## 9.28 Walking was priced with the parameter for walking to a bus stop (P4 stage 11, issues #29, #30)

**This section is written before the change it authorises and before any run on
the changed specification**, because it logs a departure from §8.5 and §8.5's own
rule is that a departure must be recorded before results are seen.

### The defect: one parameter, three broken mode shares

`src/build/build_matsim_run_inputs.py` translates C1 into MATSim scoring through
`traveling(weight) = performing − vot_avg × weight`. Two of its five calls are
wrong.

```python
'walk': marginalUtilityOfTraveling=traveling(w['beta_walk_access']['base'])   # 2.0
'bike': marginalUtilityOfTraveling=traveling(1.3)                             # a literal
```

**`C.time_weights.beta_walk_access` is the appraisal weight on walk access time
*inside a public transport journey*** — the penalty for walking to a stop, where
walking is an unwanted addition to a PT trip. It is not the value of time for a
walking trip. Applying it to the `walk` *mode* prices an entire walking journey
at twice in-vehicle time. This is the hazard §9.3 recorded as *"what C1 loses in
translation to MATSim scoring"*, realised.

MATSim's effective travel disutility is `performing + |marginalUtilityOfTraveling|`:

| mode | weight | effective util/hr | speed | **util per beeline-km** |
|---|---:|---:|---:|---:|
| car / ride / pt | 1.0 | 16.96 | measured | 0.61 (car) |
| bike | **1.3, a literal** | 22.05 | 15.12 km/h | **1.896** |
| walk | **2.0, the PT-access weight** | 33.92 | 3.78 km/h | **11.666** |

With `C.asc.walk = +0.35` and `C.asc.cycle = −1.35`, walk and bike are
indifferent at **174 m beeline (226 m network)**. `C.constraint.trip_length_km.walk`
records the observed mean walk trip as **0.7 km**. **Essentially no observed
walking trip falls inside the window where this model would choose to walk**, and
the resulting 0.13% share is arithmetic rather than behaviour.

### It is also half the PT collapse

MATSim scores access, egress and transfer walk legs with the **`walk` mode
parameters**, in the scoring function and again in the router's generalised cost.
A 5 km PT trip with 400 m access and egress, 10 min wait and one transfer costs
**−18.29 utils before any in-vehicle time**, of which **−9.33 (51%) is the walk
at each end**. That fixed cost equals 57 minutes of car driving. **Walk and PT
are one failure, not two**, which corrects §9.25's note that PT was "plausibly
downstream of A1–A3".

### The benchmark, from committed configs of calibrated scenarios

Effective travel disutility relative to car:

| scenario | car | pt | bike | walk |
|---|---:|---:|---:|---:|
| Open Berlin v6.4 | 1.00 | 1.00 | 1.00 | 1.00 |
| Leipzig v1.3.1 | 1.00 | 1.58 | 1.92 | 0.94 |
| Kelheim v3.1 | 1.00 | 1.00 | 1.50 | 1.00 |
| Düsseldorf v1.0 | 1.00 | 1.23 | 1.15 | 1.15 |
| **Melbourne AToM** (estimated on VISTA, n = 14,959) | 1.00 | 1.01 | **1.21** | **1.04** |
| **Newcastle, as built** | 1.00 | 1.00 | **1.30** | **2.00** |

**No published calibrated MATSim scenario prices walking above ~1.15× car.** The
Australian model estimated on Australian revealed preference uses 1.04×, and has
**cycling time dearer per hour than walking** — Newcastle has that ordering
inverted. Australian appraisal guidance is independently consistent: ATAP M1 and
the TfNSW Economic Parameter Values both put the walk *access* weight at **1.5**,
and Wardman's meta-analysis of 3,109 valuations at **1.45**. Even for the
quantity it was meant for, 2.0 sits at the top of the range.

### Why fixing destination placement first would have made it worse

Issue #30 is real — the model carries **4.9%** of trips under 1 km where national
travel surveys report 14–23% (US 2009 NHTS 19% under 1 mile; MiD 2023 ~23% under
1 km; ODiN 2024 14.4%). But at a 174 m crossover the recovered short trips would
go to **bike**, not walk. In every observed system walking takes the shortest
band — 61% of US sub-0.8 km trips, 81% of German sub-0.5 km trips, 62% of Dutch
sub-1 km trips, and NSW HTS puts walk at 71% of sub-1 km trips. **The scoring is
repaired first and #30 second.** This reverses the order §9.25 implied.

Recorded so it is not mistaken for a target error: roughly a quarter of sub-km
NSW trips *are* driven, and that behaviour is already inside the 13.4% walk
target. The target is not misread.

### Live MATSim defaults that no one set

`output_config.xml` from a completed run — MATSim's own fully resolved config,
which is the only place a live default is visible — shows the mode-choice and PT
router running entirely on defaults that every comparator scenario overrides:

| parameter | Newcastle | comparators | consequence |
|---|---|---|---|
| `maxBeelineWalkConnectionDistance` | **100 m** (default) | 300 m (Berlin, Leipzig, Kelheim) | see below |
| `probaForRandomSingleTripMode` | **0.0** (default) | 0.5 | no single-trip escape from a bike subtour |
| `subtourModeChoice.behavior` | `fromSpecifiedModesToSpecifiedModes` | `betweenAllAndFewerConstraints` | **an agent with an open subtour cannot change mode at all** |
| `coordDistance` | **0.0** (default) | 100 | two activities metres apart are not one subtour location |

**Measured consequence of the first, at Newcastle Interchange**, from the
S2 × WEEKDAY schedule:

| from light rail | to | distance | reachable |
|---|---|---:|---|
| Newcastle Interchange LR | Stand A, local bus | 49.0 m | yes |
| Newcastle Interchange LR | heavy rail platforms 1–3 | 53.9–57.8 m | yes |
| Newcastle Interchange LR | Stand B, local bus | 95.1 m | yes, by 4.9 m |
| **Newcastle Interchange LR** | **Stand C — `regionbuses`, `nswtrains`** | **119.2–139.0 m** | **no** |

Nothing backstops it: the schedule carries **zero** `minimalTransferTimes`, and
**none of the five raw TfNSW feeds contains a `transfers.txt`** — so this is a
source-data gap, and every interchange in the model is created by that one unset
parameter. **Claim A's hypothesis A3 falsifies on generalised journey time rising
for external-origin OD pairs, and Stand C is the external-origin connection.**
The Auditor-General's finding concerned travellers originating outside the city
centre specifically. `C.transfer.beta_transfer_penalty_min`, swept 3–15 as the
parameter the policy question turns on, has been priced against a transfer set
missing that connection.

### The §8.5 departure, logged before results

**Departed from:** §8.5 holds `C.asc.cycle` fixed at the prior −1.35.

**Departure:** `C.asc.cycle` opens a sweep of **[−4.0, −1.35]** and its status
becomes `placeholder`, to be **constrained** — not calibrated — against the
observed walk:bike split by distance band, on the pattern §9.8 established for
`C.asc.car_passenger`. The constraining quantity is an observed distributional
fact about which mode wins at which distance, not a patronage level and not a
mode share the hypotheses turn on.

**Why this is not ASC absorption.** The constant being opened is *cycle*.
`asc_light_rail`, `asc_bus` and `asc_rail` stay at their §8.5 priors and are
untouched, so no hypothesis in proposal §3 turns on it. The point value is **not
moved in this change** — only the sweep is opened and the departure recorded —
because a hand-set −3.0 would be substituting one unjustified number for another,
which is what §8.5 exists to prevent. The constrained solve is built after the
scoring repair, not before, since calibrating a constant against a known
structural error is exactly the failure proposal §9 names as the primary threat
to validity.

**Not departed from:** the 67/143 split is untouched, no holdout row was opened,
no target value changed and no falsification condition was altered.

### One research claim falsified during checking, and one of my own withdrawn

`accessEgressType` **is** active (`accessEgressModeToLink`), confirmed from the
resolved config, against a research finding that it defaulted to `none`. §9.15
stands and car does pay a walk to the network.

The claim that the teleported walk speed was set too slow is **withdrawn**. ATAP
M4 gives average walking at 4 km/h; `RUN.routing.teleported_walk_speed_ms` = 1.05
(3.78 km/h) is consistent with it. **The speeds are not the defect; the
coefficients are.** What survives is an internal inconsistency worth closing
separately: `A.transit.walk_speed_ms` is 1.25 while
`RUN.routing.teleported_walk_speed_ms` is 1.05, both labelled `literature`.

The teleported *bike* speed is left at 4.2 m/s with its sweep widened rather than
repinned, because the two sources disagree and neither was dismissed: published
MATSim practice is 3.14 m/s (Kelheim, Düsseldorf, eqasim) while ATAP M4 gives
average cycling at ~15 km/h, which is what 4.2 m/s encodes. The sweep is widened
to reach both rather than a value being chosen between them.

### Still open, and stated so

Car pays **no parking charge anywhere in the scoring** and carries no
`dailyMonetaryConstant`; its 0.18 utils/km is roughly half the Australian
estimate. In a study whose subject is city-centre access this is a real omission,
recorded here and not fixed in this change.

**Nothing in this section is a result.** No scenario has been run on the changed
specification.

---

## 9.29 The registry is named for the city it describes, and the harvest box was clipping the study area

### The naming

`config/registry/` held eight files of values, every one of them Newcastle's,
under a name that said nothing about that. `config/schema/` is the portable
half — what any city must supply and in what shape — so the instance is now
`config/registry/<city>/`, selected by `WICKHAM_CITY` and defaulting to
`newcastle`. `load_registry()` already took a directory override, so the seam
existed; only the name was missing.

The distinction matters because it is easy to mistake a generic *key* for a
generic *value*. `A.road.speed_default` is a portable field name. 50 km/h
residential, 16.96 AUD/h and a 0.50 bicycle ownership rate are not portable
values, and a directory called `registry` invited exactly that confusion.

### The defect the naming exposed

Asked to declare parking prices "via schema inputs", the first attempt wrote
**four hand-drawn Newcastle lat/lon rectangles into the registry** and called it
a schema. That is not an input schema, it is a hardcoded constant that has moved
house. It was reverted, and the question — *where else is there a hand-drawn
rectangle?* — found one that matters.

`src/extract/overpass.py` harvests OSM inside a typed-in extent,
`STUDY = (-33.20, 151.10, -32.55, 151.95)`. Against the actual boundaries in
`data/processed/zones/zones_LGA.gpkg`:

| | study area, 5 LGAs | harvest box | |
|---|---:|---:|---|
| West | 150.8013 | **151.1000** | ~28 km cut off |
| East | 152.2055 | **151.9500** | ~24 km cut off |
| South | −33.2028 | −33.2000 | marginal |
| North | −32.5788 | −32.5500 | box larger, harmless |

The road layer reaches 151.0316–152.0118 because OSM returns whole ways that
cross the boundary. Measured against that true extent rather than the box:

**87 of 1,500 core SA1s (5.8%) lie outside the road network — 86 in Port
Stephens, 1 in Lower Hunter.** Core SA1 centroids span 150.9683 to 152.1766.

Core tier means full demand generation, so those zones synthesise population and
activities over ground that has no modelled road. That is the §9.15 pathology —
agents with no road to reach — and §9.15 was diagnosed as an *external-tier*
problem because nobody checked whether core zones had the same exposure.

### The behavioural consequence, now measured

Measured on `results/ride_fix_10pct` (10%, post-#28), comparing agents homed in
the 87 unreached SA1s against every other core agent. **31,940 agents live
there, 5.21% of 612,668.**

| | other core | **unreached** | ratio |
|---|---:|---:|---:|
| trips observed (10% sample) | 213,634 | 10,480 | |
| median trip length | 7.69 km | **24.86 km** | **3.2×** |
| mean trip length | 10.72 km | 27.05 km | 2.5× |
| access + egress walk on a car/ride trip, median | 0.095 km | **0.364 km** | **3.8×** |
| …mean | 0.131 km | 0.698 km | 5.3× |
| …90th percentile | 0.225 km | **1.454 km** | **6.5×** |

Mode split, same two groups:

| | car | ride | walk | bike | pt |
|---|---:|---:|---:|---:|---:|
| other core | 52.8% | 30.9% | 1.0% | **14.8%** | 0.5% |
| **unreached** | 33.6% | 26.7% | 3.1% | **36.5%** | 0.1% |

**This is the §9.15 signature exactly.** An agent with no road near home pays a
large access walk to reach one, and flees to the mode that is teleported and
therefore immune to the penalty. Bike at **36.5%** against 14.8% is that flight,
and car is depressed 19 points to pay for it.

**Blast radius, stated so it is not overstated.** None of the 87 zones is in
Newcastle LGA — 86 are Port Stephens, 1 Cessnock — so `newcastle_lga_pct`, the
reportable mode-share metric, is **untouched**. The contamination is on the
five-LGA aggregate, which §9.13 already says must not be reported, worth roughly
**+1 percentage point of bike**; and on network-wide count fit, since 60% of
these trips are car or ride and do load the network, at a median 24.86 km. The
corridor is ~50 km away and is not measurably affected.

So the defect is **real, confirmed and bounded**. It is not a reason to pull the
extent fix ahead of the demand batch, which was the condition set for doing so.

### Why a typed rectangle is worse than a wrong number

A wrong parameter is caught by a sweep, a drift check or a reviewer reading the
registry. **A typed-in rectangle is caught by nobody**, because it looks like
scope rather than like an input. The rule added to `CLAUDE.md` is therefore
about derivation, not declaration: an extent should come from a boundary file or
a tag that any city also has. `zones_LGA.gpkg` is already in the package, so the
harvest extent is `boundaries ∪ margin` and can be computed.

The same applies to parking. The reverted rectangles priced 646 facilities;
OSM's own `fee` tag observes **472 `yes` and 640 `no`** across the 7,710
facilities, so priced-ness moves from `assumed` to `observed` for 1,112 of them
and works in any city. The price *level* stays assumed and swept — `charge` is
tagged on **1** facility — but that is a smaller assumption than drawing the
zones by hand.

### Not fixed here

Deriving the harvest extent means **re-harvesting OSM and rebuilding the
network**, and §3.5 makes every existing run incomparable across a re-map. That
is a scope decision, not a defect fix, and it is recorded rather than taken. The
cost is at its lowest now — every run on disk is already invalidated by the
250-iteration protocol (§9.27) — and rises once the repaired-model run programme
starts.

**No value changed in this section.** The registry files moved; their contents
are byte-identical. `check_package.py` and the drift check pass unchanged.

---

## 9.30 The fleet carries the capacities that were published (P4 deliverable 0c, issue #18)

§9.18 corrected the light rail vehicle and left the other three on pt2matsim's
generic defaults, recorded at the time as *"a stated limitation, not an
oversight"*. §9.21 then found published figures for all of them. This applies
them, which closes deliverable 0c.

| vehicle | mapped default | published | now |
|---|---|---|---|
| Bus (Volvo B12BLE) | 70 seats, **0 standing** | 44 seated + 18 standing | **44 / 18 = 62** |
| Ferry (MV Shortland, MV Hunter) | 250 seats, **0 standing** | 200 total, 149 seated | **149 / 51 = 200** |
| Rail (Hunter two-car set) | 400 seats, **0 standing** | 77 + 69 = 146 | **98 / 48 = 146** |
| Tram (CAF Urbos 100) | 180 seats, 0 standing | 270 total | 60 / 210 = 270 (§9.18) |

**Every default overstated the real vehicle** — rail by roughly 2.7× on a
two-car set, ferry by 25%, bus seats by about 59%. That is consistent with
§9.12's finding that transit capacity never binds: some of the headroom was
fictional.

**The larger defect was that no vehicle in the fleet had standing room at all.**
The C1 crowding multipliers — seated 1.00, standing 1.45 — could therefore never
apply in any scenario, because standing never occurred anywhere. They were
declared, swept and unreachable, the #21 defect class. All four vehicle types
now carry standing room, so crowding can bind.

### What is published and what is not

Only the **ferry** split is published, so neither half of it is assumed and both
are `held_fixed` — a vessel capacity is a fact about the boat, not a behavioural
parameter, and sweeping it would assert an uncertainty that does not exist. The
schema enforced this: `literature` with no sweep and no `held_fixed` rule does
not validate, and the first attempt was rejected.

**Bus** carries a published seated *and* standing figure, swept across the two
Volvo models Newcastle actually runs — B12BLE 44 seated, B10B 51 — so the
interval is the observed spread of stock in service rather than a chosen range.

**Rail** publishes only per-car capacity, so the seated share is assumed at two
thirds and swept 80–120, and standing is derived by identity. Same treatment as
the tram at §9.18: only the *split* is assumed, and the total it comes from is
published.

**None of this is observed for Newcastle operations.** These are manufacturer
and operator figures, labelled `literature`, and the capacities are per vehicle
as scheduled — no allowance is made for a set running short.

**Registry 178 → 186 fields.** `check_package.py` 1,107 → **1,245 checks**: every
vehicle type in every one of the 30 run-input sets is asserted to carry standing
room, which is the property rather than the numbers, so the seated sweeps stay
free to move. **Nothing was run.**

---

## 9.31 A car stops parking for free, and the price stops being a drawn rectangle (P4 stage 13, issue #33)

Parking price is the prime competitive lever between car and public transport
for a city-centre trip, and this study is about city-centre access. The model
did not have one. Two defects met in the same file.

### The price was declared and reached nothing

`data/processed/landuse/A5_parking_facilities.csv` has carried `is_priced`
(646 of 7,710 facilities), `price_aud_hr`, `price_sweep_low`/`_high`,
`max_stay_min_modelled` and a `price_schedule` string since P1. **No script read
any of them.** `check_package.py` asserted only that the file existed. This is
the "declared, swept value that reaches nothing" class on its **sixth** instance
— after #12, #21, the walk decay, the gradient, and the seven config-template
literals at §9.28.

### The spatial basis was four hand-drawn rectangles, and one could never match

`build_landuse_parking.py` defined `PARK_ZONES`: four lat/lon boxes with place
names, each carrying a literal price, a literal max-stay and a hand-typed
24-value occupancy profile.

| zone | box (s, w, n, e) | AUD/h | max stay | facilities matched |
|---|---|---|---|---|
| `cbd_core` | -32.9320, 151.7680, -32.9200, 151.7880 | 3.20 | 120 | 203 |
| `cbd_fringe` | -32.9380, 151.7550, -32.9180, 151.7950 | 2.40 | 180 | 465 |
| `honeysuckle` | -32.9300, 151.7550, -32.9200, 151.7750 | 2.40 | 240 | **0** |
| `beach_east` | -32.9350, 151.7800, -32.9150, 151.8000 | 2.00 | 240 | 4 |

`honeysuckle` is **fully contained in `cbd_fringe` on all four edges**, and
`cbd_fringe` is tested first in the same first-match-wins loop. It could never
match a facility and never did. A declared parking zone with its own price,
max-stay and occupancy profile, geometrically dead, unnoticed for three phases —
because a typed rectangle cannot be wrong in a way anyone notices. That is the
#32 lesson and the CLAUDE.md hard constraint, both restated by the same file.

### What was not used

OSM `fee=yes` looks like observed pricing. **452 of the 472 tagged facilities
are University of Newcastle car parks** at Callaghan, a median 7.8 km from the
centre; the CBD's own paid parking is untagged. Reproduced on
`data/processed/network/A5_parking_osm.csv` before anything was built on it,
per the rule that a defect is reproduced before it is attributed.

### The replacement: the city's own job-density distribution

    price(zone) = A.parking.price_aud_hr_max
                  x clamp((dens - thr) / (sat - thr), 0, 1)

`dens` is jobs per km² from `data/processed/landuse/D1_zone_attractions_SA1.csv`;
`thr` and `sat` are percentiles of **that city's own core-zone distribution**, so
a new city computes its own thresholds and no extent is ever typed. `zone_tier`
is a tag any city's zone build produces.

| quantity | value |
|---|---|
| core-zone job density p50 | 103.0 jobs/km² |
| p90 → `thr` | 1,500.9 jobs/km² |
| p99 → `sat` | 8,710.5 jobs/km² |
| core zones priced | 150 of 1,500 |
| all zones priced | 162 of 1,701 |
| car links priced (per scenario) | 22,353 of 143,891 |
| car links inside any SA1 | 95.7% — the rest are outside the zone system and free |

New fields, all `assumed` and swept, in `config/registry/newcastle/A_supply.json`:
`A.parking.price_threshold_pctile` 90 [80, 95], `A.parking.price_saturation_pctile`
99 [95, 99.5], `A.parking.price_aud_hr_max` 3.20 [1.60, 4.80],
`A.parking.max_stay_min` 120 [60, 180], `A.parking.charged_hours_by_day_type`
(WEEKDAY 08–18, SAT 08–13, SUN none) and `A.parking.exempt_activity_types`
`["home"]`. `A.parking.charged_modes` is `definition` — only the driver parks.
`A.parking.free_occupancy_profile` became `A.parking.occupancy_profile`: it now
applies to every facility, because the four per-zone profiles it replaced were
hand-typed per drawn box, rested on no observation and reached no consumer.

**The charge cap.** `max_stay_min` doubles as the cap — `price × min(duration,
max_stay)`. This **under-charges** a long stay. Declared, not hidden: modelling
over-stay properly needs an infringement rate nobody has measured here.

### Two additions beyond the formula, both deliberate

**Charged hours.** SUN is one of three day types and charging Sunday at weekday
meter rates would be wrong. The assumption already existed — A5's own
`price_schedule` string asserted "Mon-Fri 08:00-18:00; Sat 08:00-13:00; else
free" where it reached nothing. It is now a swept registry field, and the
handler charges the overlap of the parking spell with that window.

**Home is exempt.** A car is parked from arrival until the *next car departure*,
so without an exemption every agent who drives home is charged the max-stay cap
every night for living in a dense zone — a standing levy on city-centre
residence rather than a price on a travel choice. Swept against the empty set.

### How it reaches the model

`ParkingChargeHandler` (`src/java/wickham/`) emits a `PersonMoneyEvent` per
parking spell, on the precedent of `RideAvailabilityModesCalculator`. A spell
runs from a **car arrival to the next car departure**, not merely for the
following activity, so an agent who parks and walks onward is charged for the
whole spell. Charges accumulate during the mobsim and are emitted in
`notifyAfterMobsim` — the pattern MATSim's roadpricing contrib uses, because
emitting from inside a handler re-enters the events manager. **roadpricing is
not in the pinned jar** (only its DTD ships), so the pattern is reproduced, not
reused. `ParkingConfigGroup` makes `parking` a real typed module, so an
unrecognised parameter fails the run and the module appears in the output config
dump. The link→price table is built once per scenario by
`build_matsim_run_inputs.py`; **Java does no spatial work at all**.

### Reach established by changing values, not by reading `consumers`

`consumers` is a read log and cannot prove reach. Four smoke arms on S0
(2 iterations at 1% — plumbing tests, **not results**, and no mode share from
them is quoted anywhere):

| arm | parking charges | total AUD | largest single |
|---|---|---|---|
| WEEKDAY, `price_aud_hr_max` 3.20 | 526 | −721.42 | −6.40 |
| WEEKDAY, `price_aud_hr_max` 1.60 | 527 | −361.62 | −3.20 |
| SUN, 3.20 | **0** | 0.00 | — |

Halving the price halved the total (ratio 0.5013; the residual is one extra
charged agent from replanning). The largest single charge is exactly
`price_max × 2 h`, the cap. Sunday charges nothing. Charges are 1:1 with car
arrivals at the charged link.

**The reach test caught a real defect.** The first arm charged 641 spells, **267
of them at links where the person's real activity was home** — the exemption was
matching nothing. `routing.accessEgressType` is `accessEgressModeToLink` by
MATSim's own default, so the activity immediately following a car arrival is the
synthetic `car interaction`, not the destination. The handler now skips stage
activities via `TripStructureUtils.isStageActivityType` and waits for the real
one. Charges fell 641 → 526 and `home` disappeared from the charged set. Had
this shipped, every agent living in a dense zone would have paid a nightly levy
that no observation supports.

### What this formula gets wrong, measured rather than supposed

Job density alone does not distinguish a city centre from a suburban shopping
centre. The ramp prices **Westfield Kotara (8,709 jobs/km²), Stockland Glendale
(13,338) and Charlestown** at or near the 3.20 maximum, and parking at all three
is free in reality.

A contiguity refinement was built and **rejected on the evidence**. Taking the
zones above `thr` and joining those that share a boundary gives a strikingly
bimodal result — one cluster of **80 zones / 62,770 jobs** centred on Newcastle –
Cooks Hill, and 49 clusters of **1 to 5 zones**, with nothing in between. A
minimum-cluster-size rule would therefore separate the centre cleanly. It was
not adopted because it also excludes **the University of Newcastle (a singleton,
3,015 mapped facilities) and John Hunter Hospital**, the two places outside the
centre that verifiably *do* charge. It trades one error for another, so it buys
complexity rather than correctness. The diagnostic is recorded here so a future
decision starts from the measurement.

**Bearing on the study.** Parking price is identical across S0–S6 — E1's parking
variants change corridor kerbside *supply*, not price — so a mispriced zone
largely differences out of the scenario comparison. It does affect the **base
calibration**, where the ASCs would absorb part of it. That is the reason to fix
it before deliverable 5, not after.

### Not fixed here, filed instead

`build_landuse_parking.py` carries a **fifth** hand-drawn rectangle,
`CBD = dict(s=-32.9450, w=151.7250, n=-32.9050, e=151.8050)`, driving the D1
frontage segments that hypothesis B1 rests on. Different blast radius, its own
decision: **issue #34**, which also records that the damage must be measured
before it is fixed. Noted for calibration: car still carries **no**
`dailyMonetaryConstant` and pays 0.18 utils/km against Melbourne AToM's
estimated 0.365.

### Guarded structurally, not by memory

`check_package.py` gains **187 checks** (1,248 → 1,435 passing, 1 standing
warning). The one that matters re-derives **every zone price from the registry
and the city's own job-density percentiles** and compares it to the shipped
artefact: a typed price, a re-drawn extent or a hand-edited artefact all fail it.
The four dead zone names are asserted absent from *code* — comments are stripped
first, deliberately, because a defect that stays explained does not come back by
accident.

**No scenario was run, no target value changed, the 67/143 split is untouched
and nothing here is a result.**

---

## 9.32 The transfer penalty cannot be estimated from this package, and the parameter it names was reaching nothing anyway (P4 deliverable 8, issues #25, #35)

Deliverable 8 asks for the estimate proposal §7.2 specified as its fallback when
journey-linked Opal is refused. Two findings, and the second was found while
establishing the first.

### The estimate cannot be made, on three independent grounds

§7.2's exact words: *"estimate transfer rates from tap-on/tap-off timing at the
Interchange using aggregate stop-level data plus a matching model; validate
against the published interchange percentages."*

**1. The timing does not exist.** Every Opal source in the package is a monthly
aggregate:

| file | columns | resolution |
|---|---|---|
| `opal_lr_newcastle_by_stop.csv` | Year_Month, Location, Card_type, Trip | month × stop |
| `opal_lr_newcastle_by_month_cardtype.csv` | Year_Month, Card_type, Line, Trip | month × line |
| `opal_bus_newcastle_hunter.csv` | Year_Month, Card_type, Contract_region, Trip | month × region |
| `station_entries_exits_newcastle.csv` | MonthYear, Station, Station_Type, Entry_Exit, Trip | month × station |

There is no timestamp, no tap-off paired to a tap-on, and no sub-monthly
resolution anywhere. A matching model matches a tap-off at one stop to a tap-on
at another **within a time window**. With monthly totals there is no window. The
method is not hard here; it is undefined.

**2. The data that would substitute is holdout.** `lr_tapon_share_by_stop` (6
rows) and `station_entry_monthly_mean` / `station_exit_monthly_mean` (26 + 26)
are all `split=holdout`. The 67 calibration rows contain **nothing** bearing on
interchange — the non-count calibration rows are light rail and bus boardings,
the light rail share of local PT boardings, scheduled run time and alignment
length. So the alternative route — constrain the penalty so the model reproduces
an observed transfer rate, the §9.8 / §9.13 pattern — has no non-holdout
observable to constrain against either. The HTS held is aggregate mode × purpose
with no interchange table, and its trips-to-journeys ratio cannot be split by
mode, so PT transfers cannot be isolated from it.

**3. The published validation source could not be located**, and the figures
that might have substituted are the wrong quantity. Three searches found no
published interchange percentage for Newcastle. More important: interchange
**times** — the kind of figure TfNSW does publish — are not the transfer
**penalty**. MATSim already simulates the interchange walk from the schedule and
scores the wait at `beta_wait` = 2.0 × in-vehicle time.
`C.transfer.beta_transfer_penalty_min` is explicitly the behavioural premium *on
top of* the measured Newcastle Interchange walk (mean 112 s over 51 stop pairs).
Substituting a published transfer time for it would double-count what the model
already computes. **This is the trap worth recording**: the available figure
looks like the answer and is a different quantity.

The issue's own bar anticipates this: *"If the estimate cannot be made, the
reason is recorded and the sweep stands, which is a better outcome than an
unexamined assumption."* The sweep stands, at 3–15 minutes, crossed at seven
points, and every headline remains bound to report as a curve across it
(proposal §3.4 S-d). `estimation_route` in `C1_parameters.json` now records the
impossibility rather than naming a route that does not exist.

**What would settle it:** journey-linked or timestamped Opal, which is a TfNSW
unit-record request, not a published dataset. Nothing in the open catalogue
closes it (§9.23).

### The parameter was reaching nothing, so the estimate could not have mattered

Establishing the above meant tracing where the parameter goes, which found that
it does not go anywhere. `build_params.py` read **one** registry field
(`C.vot.by_purpose`) and typed the other 26 behavioural values in as literals.
`params/C1_parameters.json` is what `build_matsim_run_inputs.py` reads, so the
registry declarations reached nothing.

Reproduced before attributing it — setting the value through the resolver's own
override path left C1 **byte-identical** at 8.0:

    WICKHAM_C_TRANSFER_BETA_TRANSFER_PENALTY_MIN=12.0 python src/build/build_params.py

Seventh instance of the class, after #12, #21, the walk decay, the gradient, the
seven config-template literals at §9.28 and the parking price at §9.31.

Two consequences sharper than the general case. **The ASCs are `held_fixed`
under §8.5** — the resolver refuses every overlay, environment variable and flag
— and the model was not reading the value being protected. Deliverable 5 (#14)
is "estimate the ASCs on era 3 and freeze them"; that work would have written
seven estimated constants into the registry and changed nothing, reporting
success. **And the sweep grid was a literal too**, so #25's own bar — move the
field to `measured` "with the sweep set from the estimate's own spread" — was
unmeetable by construction: a narrowed range would not have moved the 28-point
grid.

The existing check compared **bases only**, and its own comment conceded the
arrangement: *"The registry copy is a mirror; C1 is what reaches the model."*
Agreement was maintained by hand, which is what a check cannot detect. Three
ranges had already drifted apart unnoticed:

| field | C1 literal | registry |
|---|---|---|
| `beta_crowding_seated` | 1.00 – 1.10 | 1.00 – **1.15** |
| `beta_crowding_standing` | **1.15** – **1.85** | 1.20 – 1.80 |
| `beta_gradient_uphill` | **0.04** – **0.15** | 0.05 – 0.14 |

### The fix, and the proof it changed no result

The direction is inverted: **C1 is generated from the registry** rather than
checked against it. Every base comes from the field's `value`, every range from
its own `sweep`, every label from its `source`. Five declarations were missing
and are added, because a value absent from the registry cannot be generated from
it: `C.transfer.penalty_sweep_grid`, `A.lightrail.dwell_sweep_grid`,
`C.vot.car_unavailable_walk_factor` (1.15), `C.walk.max_considered_m` (2500) and
`E.matrix.reference_scenario`. The two grids are `definition` — a sampling design
is not an empirical quantity — and **declaring where to sample the charging dwell
did not pin it**: the field stays `unobtained` with a null value. The dwell
baseline is read by resolving the reference scenario's own overlay, which is
where §4.3 already said it lives.

**Value-neutral, and demonstrated.** Diffing all 30 rows of
`C1_behavioural_parameters.csv` column by column, the only columns that moved are
the five belonging to the three drifted ranges. No base changed, and regenerating
all 30 run-input sets produced no change at all.

**Reach demonstrated by changing a value**, not by reading `consumers`:

| | before | after |
|---|---|---|
| override → `transfer_penalty.base` | 8.0 (unchanged) | **12.0** |
| override → the 30 C1 rows | 8.0 | **12.0** |
| override → baseline grid row | 8.0 | **12.0** |
| override → `utilityOfLineSwitch` | −2.2613 | **−3.3922** |

−3.3922 is −(12/60) × 16.96, the VOT conversion, so the chain holds end to end.

### Guarded

`check_package.py` 1,435 → **1,440** passing. The new checks assert that the ASCs
agree, that every declared **range** reaches C1 (a base-only comparison read as
green while three ranges were wrong), that the sensitivity grid spans its declared
sweep exactly and contains its own base, that every non-zero dwell grid point lies
inside the declared sweep, and that declaring the grid did not pin the unobtained
field.

**No scenario was run, no target value changed, no holdout row was opened, the
67/143 split is untouched and nothing here is a result.**

---

## 9.33 Six defaults stop being guesses, and a suspected duplicate turns out to be two different numbers (P4 deliverable 0b, issue #23)

Deliverable 0b asks how many of the registry's `assumed` fields the data can
actually settle. **88 → 84 assumed**, **15 → 21 measured**, plus one field that
existed nowhere and should have. The realistic target was 15–25 fields of tour
structure and network defaults; what the data supports is the network half, and
the reason the other half resists is recorded rather than worked around.

### The suspected duplicate was not one, and both numbers were wrong

`RUN.routing.beeline_distance_factor` (assumed 1.30) and `B.activity.detour_factor`
(measured 1.3376) were flagged as "probably the same quantity declared twice". They
are not. The detour factor is the **road graph at multi-kilometre zone spacing**;
the beeline factor is the **active network at walk and bike trip lengths**, and
circuity falls with distance. Measuring it settles the question instead of
aliasing one to the other:

| | value | sweep (observed IQR) | measured at |
|---|---|---|---|
| walk | **1.6902** | 1.294 – 1.794 | 700 m, the observed walk trip length |
| bike | **1.5231** | 1.207 – 1.456 | 5.2 km, the observed bike trip length |
| road (unchanged) | 1.3376 | 1.25 – 1.423 | population-weighted zone pairs |

Walk and bike differ enough that one shared factor was wrong for both, so the
field is **split in two**. The network routed over is the A6 active layer
**unioned with every road class a pedestrian may use**: A6 alone is 23,808
footway edges, and OSM maps a footway beside a residential street only where
somebody drew one, so routing on it alone would report the mapping's circuity
rather than the city's.

**A first attempt was rejected on its own evidence.** Drawing a random bearing
from each origin gave walk 1.96 against a median of 1.52 — the gap being
destinations across the harbour and the motorway that nobody walks to. Sampling
observed **POI** destinations instead, which is where B2 places activities, gives
1.69 against a median of 1.46. The tail is smaller because the destinations are
real.

### The walk speed was one quantity declared twice, and that one WAS a duplicate

`A.transit.walk_speed_ms` (1.25, generating GTFS transfer times) and
`RUN.routing.teleported_walk_speed_ms` (1.05) each carried `literature` and each
described the other as a different quantity. The pinned jar disagrees.
`TeleportationRoutingModule` computes

    travelDistance = beelineDistance x beelineDistanceFactor    // dmul
    travelTime     = travelDistance / teleportedModeSpeed       // ddiv

so `teleportedModeSpeed` is the speed **along the walked path** — exactly what
the GTFS figure is. Verified in the bytecode, not from memory. The MATSim field
is now `derived` with that identity, at 1.25. The detour a walker makes is
carried by the measured beeline factor, which the speed no longer has to absorb.

Net effect on a walk leg: 1.6902/1.30 × 1.05/1.25 = **1.09**, about 9% slower,
with every component now measured or physically grounded rather than chosen.

### Defaults measured from the city's own OSM tags

The imputation is not a rounding error — `lane_width_m` is imputed on **99.2%**
of road edges, `num_lanes` on 75.4%, `speed_limit_kmh` on 53.7% — but the
complement is real data: 10,613 edges carry a `lanes` tag and 19,961 a
`maxspeed`. `measure_osm_defaults.py` takes each class's own median where at
least 30 edges are tagged, and its own interquartile range as the sweep.

| field | classes measured | notable corrections |
|---|---|---|
| `A.road.speed_default` | 13 of 16 | **trunk 80 → 60** (n=1,702), **motorway 100 → 110** (n=432), motorway_link 60 → 80, service 20 → 25 |
| `A.road.lanes_default` | 13 of 16 | every measured class confirmed its assumed value |
| `A.active.footway_width_default` | 3 of 8 | footway 1.8 → 2.0, cycleway 2.5 → 2.0, path 1.5 → 1.0 |

`busway`, `road` and `tertiary_link` keep their assumed values for want of
coverage and say so; `A.road.capacity_default` is **not** measured at all —
saturation flow is an engineering convention OSM does not record and this
package has no per-class count data to estimate it from.

**A field that existed nowhere.** `build_network_layers.py` carried a bare
`lw = 3.2` for lane width, applied to 99.2% of edges, in no registry at all.
It is now `A.road.lane_width_default_m`, **measured at 3.5 m** (IQR 2.5–4.5).

It could not be read off the `width` tag. On a road, OSM `width` is the whole
**carriageway**: measured straight it is 6.5 m, which is two lanes, and writing
that into a per-lane field would have doubled every carriageway in the model.
Per-lane width is derived as width ÷ lanes on the 265 edges carrying both tags.
The build script now divides a tagged width by its lane count for the same
reason.

### Three things the data looked able to settle and could not

Each is the same trap: **the available number looks like the answer and is a
different quantity.** Three instances in one session is a pattern worth naming.

1. **Parking capacity.** 4,861 of 7,710 facilities carry an observed
   `capacity`, which looks like ample coverage — and **4,623 of them are `1`.**
   They are individual bays, not car parks. Only 162 facilities carry a capacity
   of 5 or more. `A.parking.capacity_default` **stays assumed**; a measured
   default of 1.0 would have said every car park in Newcastle holds one car.
2. **The transfer penalty** (§9.32): a published interchange *time* is not a
   behavioural *penalty*.
3. **Parking price** (§9.31): `fee=yes` is 452 University car parks.

### The reclassification the issue proposed, reviewed and mostly declined

#23 suggests several `assumed` fields are really methodological choices
mislabelled, and that reclassifying them to `definition` would stop them
inflating the count. Reviewed one by one, that is **not** what they are. The
SUMO booleans each change a result — `junctions_join` moves a junction centroid
and interacts with `A.signals.junction_match_m`; `tls_join` changes how many
signal programs the corridor carries; `tls_default_type` is, in its own words,
"a real modelling choice standing in for information the project does not have".
The corridor buffers carry documented empirical consequences and would lose
their sweeps. Relabelling a real assumption to make a percentage look better is
the opposite of what deliverable 0b is for, so the count stays honest at 84.

### Guarded

`check_package.py` gains a pin from the registry to
`params/C2_osm_defaults.json`, class for class — the same two-copies-of-a-number
hazard §9.32 found in C1 — plus an assertion that the per-lane width is a lane
and not a carriageway.

**The measured speed defaults are in `A1_road_edges.csv` as of this change; the
MATSim network still carries the old ones and is rebuilt at #32, which
re-harvests the extent anyway. No scenario was run, no target value changed, the
67/143 split is untouched and nothing here is a result.**

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
10. **GTFS-Realtime collection** — **considered and dropped (§9.23).** A collector
    was built and reverted once an Open Data Hub API key made the published
    catalogue assessable. TfNSW's own **Historical GTFS and GTFS Realtime**
    archive carries trip updates and vehicle positions but **only for Metro and
    Ferry** — verified against the live API, with Metro/Ferry returning files and
    every light rail and bus naming returning none — so it does not backfill
    Newcastle. Standing up an unbounded rolling stream is not justified until the
    published catalogue has been worked through; that assessment is §9.23.
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

`config/registry/` now declares **152 fields** — every value the model consumes
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

**Superseded in part — see "The build layer, migrated" below.** The migration
landed, so the drift check that pinned duplicate constants is now nearly empty by
design: a migrated script reads the registry, and its duplicate constant was
deleted along with the `legacy_symbol` that pinned it. **One field remains
pinned**, one deliberately diverges. Writing that check originally found four
values transcribed wrongly into the registry; the code was authoritative and the
registry was corrected.

**Of the 152 declared fields, 66 are referenced by no code in `src/` or
`tests/`.** That is not drift and not a defect: a registry field is a
*declaration* first — units, provenance and a sweep for a value the model relies
on — and only a runtime lookup second. The 66 divide into three kinds, and the
distinction matters:

- **constraints**, which mirror a measured artefact rather than feed a script.
  `C.constraint.*` declares occupancy (§9.8) and trip length and time (§9.13);
  the values live in `params/C4_mode_constraints.json`, which is what `fit.py`
  reads, and `check_package.py` pins declaration to artefact so they cannot
  drift.
- **values consumed through an intermediate artefact** rather than by key —
  `B.counts.*` reaches `fit.py` through `params/C3_count_comparison.json`, for
  instance.
- **values genuinely not yet wired**, including the seven that carry no value at
  all and must never be pinned (§0, §13).

**A `consumers` entry is a machine-readable claim and is verified.** It asserts
that a named file reads that field, and `check_package.py` now checks the file
exists *and* references the key. An untrue claim is worse than an absent one: it
makes a value look wired into the model when nothing reads it, which is the very
drift the registry exists to prevent, asserted in the registry's own hand. Ten
fields added at §9.13 named two readers that in fact read the C4 artefact; the
check caught it, and every one of the sixty pre-existing claims was already
true.

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
| 2026-08-13 | **P4 deliverable 0b - six defaults stop being guesses, and a suspected duplicate turns out to be two different numbers (§9.33, issue #23).** **88 → 84 assumed, 15 → 21 measured**, plus one field that existed nowhere. `RUN.routing.beeline_distance_factor` and `B.activity.detour_factor` were flagged as probably the same quantity declared twice; they are not - one is the road graph at zone spacing, the other the ACTIVE network at walk and bike trip lengths, and circuity falls with distance. Measured: **walk 1.6902, bike 1.5231** against a shared assumed 1.30, so the field is **split in two**. A first sampling by random bearing gave 1.96 and was **rejected on its own evidence** - it sent walk trips across the harbour; sampling observed POI destinations, which is where B2 puts activities, gives 1.69. The walk SPEED, though, WAS a genuine duplicate: `A.transit.walk_speed_ms` 1.25 and `RUN.routing.teleported_walk_speed_ms` 1.05, both `literature`, each describing the other as a different quantity - and the pinned jar's bytecode shows `travelTime = (beeline x factor) / teleportedModeSpeed`, so the speed is ALONG the path and they are one number. Now `derived` by identity at 1.25. Per-class defaults measured from the city's own OSM tags where at least 30 edges are tagged: **trunk speed 80 → 60** over 1,702 tagged edges, **motorway 100 → 110**, and a **lane width that was a bare 3.2 in no registry at all**, now measured at **3.5 m** - and NOT from the `width` tag, which on a road is the whole carriageway at 6.5 m and would have doubled every carriageway in the model. Three things the data looked able to settle and could not, all the same trap: parking capacity has 4,861 observed values of which **4,623 are 1** because they are individual bays, not car parks. The reclassification #23 proposed was reviewed and **mostly declined** - the SUMO booleans and corridor buffers each change a result, and relabelling a real assumption to make a percentage look better is the opposite of what 0b is for. **No scenario was run, no target value changed, the 67/143 split is untouched and nothing here is a result.** |
| 2026-08-13 | **P4 deliverable 8 - the transfer penalty cannot be estimated from this package, and the parameter was reaching nothing anyway (§9.32, issues #25, #35).** Proposal §7.2's fallback asks for tap-on/tap-off **timing** at the Interchange plus a matching model. **Every Opal source held is a monthly aggregate** - no timestamp, no tap-off paired to a tap-on, nothing for a matching model to match. The stop-level tap data that would substitute is **holdout**, and the 67 calibration rows contain nothing bearing on interchange, so the constrain-to-an-observable route (§9.8) has no observable either. No published interchange percentage for Newcastle could be located; and published interchange **times** are the wrong quantity - MATSim already simulates the walk and scores the wait at 2.0x in-vehicle time, and this parameter is the premium **on top of** the measured 112 s Interchange walk, so substituting one would double-count. Per the deliverable's own bar the reason is recorded and **the sweep stands** at 3-15 minutes across seven points. Tracing where the parameter goes found that it went nowhere: `build_params.py` read **one** registry field and typed the other **26** in as literals, so setting the value through the resolver's own override path left `C1_parameters.json` **byte-identical**. Seventh instance of the class. Two consequences sharper than usual - the **mode constants are `held_fixed` under §8.5** and the model was not reading the value being protected, so deliverable 5 (#14) would have estimated seven ASCs, written them to the registry, changed nothing and reported success; and the **sweep grid was a literal too**, making #25's own bar unmeetable by construction. The prior check compared **bases only** and its comment conceded *"the registry copy is a mirror"* - three RANGES had already drifted apart unnoticed. C1 is now **generated from** the registry rather than checked against it, with five missing declarations added; declaring a sampling grid for the charging dwell did **not** pin it, which stays unobtained and null. **Value-neutral and proved so** - no base moved and all 30 run-input sets regenerated unchanged - and **reach proved by changing a value**: the override now moves `utilityOfLineSwitch` -2.2613 to -3.3922, exactly the VOT conversion. `check_package.py` 1,435 -> **1,440**. **No scenario was run, no target value changed, no holdout row was opened and nothing here is a result.** |
| 2026-08-13 | **P4 stage 13 - a car stops parking for free, and the price stops being a drawn rectangle (§9.31, issue #33).** Parking price is the prime competitive lever between car and PT for a city-centre trip, and this study is about city-centre access. `A5_parking_facilities.csv` has declared `is_priced`, `price_aud_hr` and a sweep on both since P1 and **no script read any of it** - the "declared value that reaches nothing" class on its **sixth** instance. Its spatial basis was four hand-drawn lat/lon rectangles with place names, literal prices and hand-typed occupancy profiles, and **one of the four, `honeysuckle`, was fully contained in the box tested before it and could never match a facility** - dead for three phases, because a typed rectangle cannot be wrong in a way anyone notices. Price is now derived from **the city's own core-zone job-density distribution** (p90 = 1,500.9 and p99 = 8,710.5 jobs/km², pricing 150 of 1,500 core zones and 22,353 of 143,891 car links), so a new city computes its own thresholds and no extent is typed. OSM `fee=yes` was reproduced and rejected as the basis: **452 of its 472 facilities are University of Newcastle car parks**. The charge reaches the model through `ParkingChargeHandler`, which bills a car from arrival to the next car departure as a `PersonMoneyEvent`; roadpricing is **not** in the pinned jar, so its deferred-emission pattern is reproduced rather than reused, and Java does no spatial work. **Reach was established by changing values, not by reading `consumers`** - halving `price_aud_hr_max` halved the charges (−721.42 → −361.62 AUD), Sunday charges nothing, and the largest single charge is exactly the max-stay cap. **That test caught a real defect**: `accessEgressType` inserts a `car interaction` activity after every car arrival, so the `home` exemption matched nothing and **267 of the first 641 charges were levied at people's own homes** - a nightly penalty on living in a dense zone that no observation supports. What the formula still gets wrong is measured rather than supposed: it prices Kotara, Glendale and Charlestown at or near the maximum where parking is free, and a contiguity refinement that would separate the centre cleanly (one 80-zone cluster against 49 of 1–5) was **built and rejected** because it also excludes the University and John Hunter Hospital, the two places outside the centre that verifiably do charge. Price is common to all scenarios, so it largely differences out of the S-vs-S comparison and bites on the base calibration instead. `check_package.py` 1,248 → **1,435** passing, the key check re-deriving every zone price from the registry so a typed price cannot survive. **No scenario was run, no target value changed, the 67/143 split is untouched and nothing here is a result.** |
| 2026-08-13 | **P4 stage 10 - the passenger stops outrunning the driver (§9.26, issue #28).** `ride` was routed over the network on **free-flow** times because it is in `routing.networkModes` but is not the qsim `mainMode`. `WickhamControler` now binds its travel time to `networkTravelTime()` and its disutility to the car factory. Verified against a like-for-like 10% baseline differing only in the controler: **car 32.54 -> 52.30%, ride 50.03 -> 29.45%**, total absolute gap to target **84.2 -> 44.6 pp** - the largest single correction this model has had, and it came from a defect rather than a constant. It confirms §9.25's claim that the symptom was **two** inversions: car↔ride moved ±20 points while walk↔bike moved -0.03/+0.81, untouched. **The defect is reduced, not eliminated** - ride is still 1.01-1.11x faster at matched distance, worst on short trips, so #28 stays open. The audit's headline was also corrected: the original 13% was an aggregate confounded by trip-length composition; stratified it is 4-8%, present in every bin. A first verification at 1% was **discarded as uninterpretable** - §15's storage floor produces spurious spillback that inflates car delay while teleported ride is immune, so a cross-fraction comparison is invalid. Two reproducibility defects exposed and closed: **nothing compiled the committed Java**, so a fresh clone could not run; and a run record could not say which controler produced it, so re-running would have served pre-fix results silently - records now carry `controler_sha256` and the harness refuses to resume across a change. `prune_run.py` drops MATSim's per-iteration scratch, **95% of a run's bytes** and read by nothing, reclaiming 36.6 GiB. **Not a result:** 250 iterations is short of relaxation, demand still lacks through traffic and freight, no target was fitted, the 67/143 split is untouched and no holdout row was opened. |
| 2026-08-12 | **P4 stage 8 - own realtime collection dropped, and the published catalogue assessed instead (§9.23).** A GTFS-Realtime collector was built and **reverted in full** once an Open Data Hub API key made the 230-dataset catalogue assessable. TfNSW's own **Historical GTFS Realtime** archive was verified against the live API and carries **Metro and Ferry only** - controls return files, every light rail and bus naming returns none - so it cannot backfill Newcastle, and §7.2's contingency for the SCATS refusal is recorded as an **open gap**. What the catalogue does settle, verified against the data rather than the titles: **Traffic Lights Location** matches **all 14 corridor intersections within 60 m**, supplies the `scats_site_id` that `A2_signal_control_corridor.csv` declares but leaves empty, and dates **8 of the 14 as 2018 light-rail installations** - so the pre-intervention corridor had 6 signals, not 14, which is an observed basis for a counterfactual now assumed; **SFM22** gives origin-destination freight for issue #24; the **GTFS reference tables** carry Hunter Line running times bearing on the assumed era-1 constants; **school and public holiday** dates stratify the dated RMS counts. Recorded as *not* settled: no SCATS phasing exists in the catalogue, the kerbside and lane-width datasets are **Sydney-only** so issue #27 is untouched, JTW 2016 is withdrawn by TfNSW, and Opal tap data is **not journey-linked** so deliverable 8 keeps its fallback. **No value was acquired, changed or registered** - this is an assessment. No parameter value changed, no target value changed, the 67/143 split is untouched and no scenario was run. |
| 2026-08-11 | **The input registry (§15).** Every value the model consumes that is not read from an immutable raw download is now declared in `config/registry/` with its units, its provenance and either a sweep range or an explicit rule holding it fixed — **123 fields**, against 316 module-level constants of which exactly one carried a machine-readable source label. Proposal §8.1 becomes a schema constraint rather than a discipline: `assumed` without a sweep does not validate. The three unobtained inputs carry `value: null` and the resolver **raises** rather than returning a point value, so §0 and §13 are enforced structurally; the §8.5 mode constants are `held_fixed` and no overlay, environment variable or flag can move them. Two factors that governed every P4 result were found set in code with no rationale and no range — `flowCapacityFactor` (derived, and now stated as such) and `storageCapacityFactor` (assumed, exponent swept 0.75–1.0, and an open risk at 1% because MATSim floors link storage at one vehicle). Outputs are declared to the same standard: `_run.json`, `_metrics.json`, `_fit.json` and `_config.json` each carry a JSON Schema, and a fit block that does not name its target ids fails its contract. `docs/CONFIG_REFERENCE.md` is generated and checked for staleness. `check_package.py` 860 → **908 checks**, 1 standing warning. The build layer is declared but not yet migrated and is pinned to the registry by a drift test, which caught four transcription errors on its first run. No parameter value was changed, no target value was changed, the 67/143 split is untouched and no scenario was run. |
| 2026-08-10 | **P4 stage 0 — the assembled run inputs did not load, and what a run actually costs (§9.4, §9.5, §12.1–12.3).** MATSim was pointed at `scenarios/matsim/S2/WEEKDAY/` and refused it. Three independent defects, none visible to a check that treats the artefacts as data: the day-type filter dropped the doctype MATSim selects its reader from (all 30 sets); it left stop facilities and `minimalTransferTimes` relations orphaned by the routes it removed, which makes SwissRailRaptor dereference a null array (all 30); and the kerbside patch appended a second `<attributes>` block to links that already had one, invalidating **6 of the 10** run networks — precisely the six carrying an E1 road change. Fixed, rebuilt byte-identically with the patch counts unchanged, and **all 30 sets now load and run**. `check_package.py` 556 → **657 checks**, with the three failure modes asserted per set. Run cost measured on this machine rather than estimated: **9.8 s/iteration at 1%, 29.9 s at 10%, ~64 s at 25%**, memory 9.8/18.4/31.5 GiB, extrapolating to ~4.5 min and ~97 GiB at 100% — so **a 100% weekday run does not fit in 63.5 GiB** and the specified 5,100 run-days is ~765 days of wall clock. Also recorded, without acting on either: 13 of the 67 calibration targets (`lr_cardtype_share`) can identify nothing in MATSim and several others are duplicates or schedule inputs, leaving ~4 mode-share degrees of freedom + 1 patronage level + 34 counts; and the 119 `road_aadt` values are the mean of `ALL DAYS` with the peak-period rows, 0.58–0.71× the true figure. **The 67/143 split is untouched, no holdout value was used, no target value was changed and no falsification condition altered. Still no scenario run.** |
| 2026-08-10 | **P3 stage 3 — assumptions replaced by Newcastle measurements where the data allows, and the sweep-range rule made mechanical.** Three constants derived rather than typed: the **detour factor** is now routed over the observed A1 road graph (**1.3376**, 551 zone pairs, was assumed 1.30); the **weekday/weekend travel split** comes from the RMS counts' own `WEEKDAYS`/`WEEKENDS` periods (**0.752**, 551 station-years, was implied 0.825); and census G62 gives an observed **lower bound** on work attendance (0.651) without being allowed to set the value, since census night carries the 2021 lockdown (§2.4). Seven parameters that breached proposal §8.1 by carrying no sweep range now carry one, and `check_package.py` **enforces the rule as a test** rather than leaving it to discipline. What genuinely cannot be localised is labelled so: MATSim's `performing`, distance rates, typical durations and replanning weights are properties of the scoring formulation, not of Newcastle. `EXTERNAL_INTERACTION_RATE` stays swept and the missing ABS journey-to-work origin-destination table is added to §13. 497 → **556 checks**, all passing. Still no scenario run; no falsification condition altered. |
| 2026-08-10 | **P3 stage 2 — MATSim plans, day-type run inputs and the C1 scoring translation (§9.3).** 517,936 weekday agents wired to the single P2 build; the day-type filter works on the already-mapped schedule and is verified to preserve all 1,714 route link sequences and the whole stop→link map. What C1 loses in translation — the nest structure, per-purpose VOT, crowding — is recorded, not dropped. Two defects caught by the new checks: the day-type token is underscore-delimited for the S1 shuttle and S3 BRT, so both were being dropped from every day type and each scenario would have run without its intervention; and banned-turn removal was network-wide, deleting 1,235 observed restrictions instead of 8. `check_package.py` 322 → **497 checks**, all passing. Still no scenario run; no falsification condition altered. |
| 2026-08-10 | **P3 stage 1 — B2 activity chains rebuilt as tours (§9.2).** The P1 chains put 1,452,065 activity legs on 1,481 zone centroids, labelled every return-home leg NHB, and gave each agent a single subtour; they are replaced, not patched. Destinations are now placed on observed POIs and building footprints, the gravity decay is solved against the HTS journey distance per purpose, three day types are produced, and the 201 external SA1s finally generate boundary demand. `build_population.py` keeps B1 and no longer writes B2; because it no longer draws for chains, the B1 sample shifted 612,680 → 612,668 persons with every fit statistic unchanged. Still no scenario run; no falsification condition altered. |
| 2026-08-10 | **P3 stage 0 — the §3.4 shape defect closed, and one determinism bug with it.** S0/S2c/S4/S5 alignments rebuilt from observed geometry (§3.4); extension stop sitings anchored on observed features, one of them 548 m out. E1 patch set 195 → 414 rows as a consequence. **`build_scenario_schedules.py` iterated a `set` of trip ids in two places, so `stop_times.txt` row order varied with the Python hash seed** — a violation of the determinism rule that predates this branch and was caught by a repeat-build check; now sorted, and two consecutive builds are byte-identical across all 10 feeds. One MATSim build of all 15 feeds and 4 SUMO nets regenerated on the corrected feeds; 322 package checks pass. Still no scenario run; no falsification condition altered. |
| 2026-08-10 | **P2 network build.** Toolchain pinned (§3.6). Corridor attributes graded by evidence and the E1 road variants derived as edge-level deltas (§3.4); premise corrected — the corridor is not 75–98% imputed (§2.5). pt2matsim's run-to-run drift measured and bounded (§3.5). Three missing signal variants built (§5). CRS label corrected (§2.6). MATSim network + 15 mapped schedules and 4 SUMO corridor nets produced. Still no scenario run; no falsification condition altered. |
| 2026-08-10 | Initial. P1 data acquisition. Scope decisions §10.1–3, 4, 5 closed. Proposal premises corrected per §2.1–2.4. No scenario run; no falsification condition altered. |
