# STATUS — Project Wickham

Single source of truth for **where the build is, what's next, and how to resume**. Read
this at session start. **Keep it current in the same commit/PR as the work it describes**
— if a change makes a line here wrong, fix the line in that change, not later.

**Last updated:** 11 August 2026 (P4 stage 3 - the ride constraint measured)
**Stage:** **P4 stages 0–3.** **Seven** defects fixed, every one of which would
have produced a confident wrong answer rather than an obvious failure: the 30
run-input sets could not be loaded by MATSim at all, the mode choice was not
choosing, and the day-type filter left **the with-tram scenario with no tram on a
weekday** (§9.9). Run cost, seed dependence and convergence are measured rather
than assumed, and the ride constant is constrained to observed vehicle occupancy
(§9.8). Every controllable value is now **declared** rather than typed into a script:
`config/registry/` holds 152 fields with units, provenance and a sweep or a
held-fixed rule, and the resolver refuses to hand back a point value for
anything unobtained (§15). **Two fits have now been computed against the
calibration targets — 38 scored, 29 explained — but both are on runs known to be
short of relaxation, no calibration loop exists, and nothing in this repo is a
result.**

---

## Phase board

Phases as defined in [`newcastle-lr-proposal.md`](newcastle-lr-proposal.md) §7.1.

| Phase | State | Notes |
|---|---|---|
| P0 Scoping | ✅ complete | Base year 2026, zone system, scenario list S0–S6 settled. Scope calls closing proposal §10 are recorded in [`DECISIONS.md`](DECISIONS.md) §1. |
| P1 Data acquisition | ✅ complete | 182 files, 2.31 GiB, all provenance-tagged and hashed in [`data/MANIFEST.csv`](data/MANIFEST.csv). Three critical inputs remain unobtained — see below. |
| P2 Network build | ✅ complete | MATSim network + 15 mapped schedules, 4 SUMO corridor nets, corridor attributes graded by evidence. See below. |
| P3 Demand synthesis | ✅ complete | Shape defect closed, network rebuilt once, B2 rebuilt as tours (3 day types + external boundary demand), MATSim plans and 30 scenario×day-type input sets. They did not in fact load in MATSim — fixed at P4 stage 0 (§9.4). |
| P4 Calibration | 🟡 stages 0–3 | Run inputs load (§9.4), run cost measured (§9.5), mode choice fixed and the seed uninformed (§9.6), seed dependence and convergence measured (§9.7), the ride constant constrained to observed occupancy (§9.8), **the day-type filter corrected — the with-tram scenario had no tram on a weekday (§9.9)**, sample fraction tested (§9.10) and **1% found unusable** (§9.12), `ride` given a driver requirement (§9.11) and measured **necessary but not sufficient** (§9.12), trip length by mode constrained (§9.13), target identifiability written down (§12.1–12.4). Deliverables **3 of 7**: run harness, metric extraction and fit statistic exist and are tested; **the calibration loop, the calibrated base and the report do not** (#14), and the phase is blocked on the §8.5 ride specification (#16). |
| P5 Scenario runs | ⬜ not started | The P4 harness in `src/run/` is what P5 will drive. **Read the one-build constraint in [`DECISIONS.md`](DECISIONS.md) §3.5 before designing a run**, and §9.5 before choosing a sample fraction — the specified load is ~765 days of wall clock and that cut has not been made. |
| P6 Analysis | ⬜ not started | `src/analyse/` holds the P4 metric extraction only; nothing for the A/B hypotheses yet. |
| P7 Write-up | ⬜ not started | |

---

## What P1 delivered

| | |
|---|---|
| Study area | Newcastle, Lake Macquarie, Maitland, Cessnock, Port Stephens — 4,086 km² |
| Zones | 1,500 core SA1 + 201 external SA1, 222 core DZN |
| Population | 611,915 (2021 Census) → 612,680 synthetic agents |
| Road network | 43,112 edges, 9,207 km, gradient-attached |
| Active network | 35,653 edges, 6,325 km, directional walk-speed factors |
| PT | 5 GTFS eras + 10 scenario variants |
| Validation | 210 targets (67 calibration / 143 holdout). The 119 traffic-count **values** were repaired at P4 ([`DECISIONS.md`](DECISIONS.md) §12.2); the split did not move. |
| Base year | 2026 · CRS EPSG:28356 (GDA94 / MGA Zone 56 — label corrected, [`DECISIONS.md`](DECISIONS.md) §2.6) |

---

## What P2 delivered

**Toolchain, pinned by digest** — `python src/setup/bootstrap_toolchain.py` fetches
Temurin JDK 25.0.4+7, pt2matsim 26.6 (shaded jar) and SUMO 1.27.1 into `.tools/`
(gitignored, ~1.4 GiB) and records each one's version, URL and sha256 in
`.tools/toolchain.json`. `--verify` re-checks the digests. No Maven: the shaded jar
carries MATSim. Details and the one known tool defect: [`DECISIONS.md`](DECISIONS.md) §3.6.

**Corridor attributes, graded by evidence rather than corrected by hand**
(`src/build/build_corridor_road_attributes.py`):

| | |
|---|---|
| Corridor / parallel edges classified | 605 (40 trunk, 84 cross, 417 parallel) |
| As-built trunk lane counts observed in OSM | **87.5%** — the corridor is not 75–98% imputed ([`DECISIONS.md`](DECISIONS.md) §2.5) |
| Turn restrictions resolved to coordinates | 1,385 of 1,386; 10 within 40 m of the alignment vs E1's assumed 14 |
| E1 road variants expressed as edge-level deltas | 195 patch rows; the as-built variant has **zero** — it is the observed network |

**MATSim** (`src/build/build_matsim_network.py`) — one base network,
157,678 links / 73,227 nodes / 23,212 km in EPSG:28356, plus the four E1 road variants as
link-attribute patches over it (so "variants differ only where E1 says" is structural, not
a diff), and all 15 feeds mapped:

| | |
|---|---|
| Feeds mapped | 15 (5 era + 10 scenario) |
| GTFS stops without a network link | **0, in every feed** |
| Artificial link share | 0.4–0.6% |
| Turn restrictions carried into the network | 1,240 `disallowedNextLinks` |

**SUMO corridor** (`src/build/build_sumo_corridor.py`) — 4 nets, one per road variant,
15,666 edges / 7,090 junctions / 211 traffic lights each, left-hand traffic, plus a
traffic-light additional file per (road variant × signal variant). All 14 A2 intersections
match a signalised junction in every variant and every realised cycle lands within 1 s of
its A2 value. netconvert output is byte-identical on rebuild.

**Checks** — `tests/check_package.py` grew from 180 to 374 lines: stop→link coverage and
fingerprints, orphan links and nodes, variant-vs-base containment, TLS pairing and cycle
fidelity, corridor provenance vocabulary, sweep ranges on every assumed patch, toolchain
pinning. **322 checks, all passing.**

---

## Open items carried forward

Three inputs the proposal named as critical are **unobtained**, and are handled by
**sweep, not by assumption-as-fact** ([`DECISIONS.md`](DECISIONS.md) §0, §13). Formal
requests are outstanding; do not pin any of them to a point value.

| Input | Why it matters | Current handling |
|---|---|---|
| SCATS signal phasing | Corridor run time swings 38% between no priority and full priority (S2 vs S2b) — the largest single uncertainty in the model | Swept. The SUMO corridor now carries the proxy timings explicitly, each program labelled `timing_source=assumed` |
| Journey-linked Opal | Needed to *estimate* the transfer penalty rather than sweep it | Swept, 3–15 min |
| Measured charging dwell | Assumed 20 s per intermediate stop; worth 11% of end-to-end run time | Swept |

Also absent: pedestrian counts (none published for Newcastle), frontage-level retail
floorspace and vacancy, parking meter transactions, and a 2014 timetable to validate the
era-1 reconstruction.

**Raised by P2, not yet resolved:**

| Item | Where | Consequence if left |
|---|---|---|
| ~~S2c/S4/S5 GTFS shapes were never extended~~ **Closed at P3 stage 0.** It also affected S0. | [`DECISIONS.md`](DECISIONS.md) §3.4 | Alignments now routed over observed geometry; extension stop sitings anchored on observed features. E1 patch set grew 195 → 414 rows as a result. |
| **pt2matsim is not reproducible run to run** — ~18% of route link sequences differ between identical builds | [`DECISIONS.md`](DECISIONS.md) §3.5 | Every scenario comparison must use **one** build of the network. Comparing feeds mapped in different builds puts an 18% path difference inside the treatment effect. |
| Pre-tram Hunter/Scott cross-section is assumed (2 lanes/direction, swept 1–2) | [`DECISIONS.md`](DECISIONS.md) §3.4 | This is the counterfactual B3 rests on. It must be reported as swept, never as a point estimate. |
| `--osm.crossings` segfaults SUMO 1.27.1 | [`DECISIONS.md`](DECISIONS.md) §3.6 | No crossings/sidewalks in the SUMO corridor. Pedestrians are MATSim's job on A6, so this is acceptable — but do not model pedestrian delay in SUMO. |

---

## P3 stage 0 — what changed (10 August 2026)

| | |
|---|---|
| S4/S5 extension alignment | Routed over the observed OSM centreline of the SBC street sequence. **7.00 km vs the SBC's stated 6.65 km (+5.3%)** |
| S2c / S0 alignment | The retained harbour-side former-railway strip — 33% / 21% observed OSM geometry, remainder interpolated |
| Extension stop sitings | Anchored on observed features (two intersections, a station node, a POI). The P1 Hamilton coordinate was **548 m off the published corridor** |
| E1 road patch set | 195 → **414** rows; corridor/parallel edges 605 → **714** |
| Determinism | A **pre-existing** set-iteration bug in `build_scenario_schedules.py` made `stop_times.txt` row order hash-seed dependent. Fixed; two consecutive builds are now byte-identical across all 10 feeds |
| Network | **One build** of all 15 feeds + 4 SUMO nets, on the corrected feeds. 0 unmapped stops in every feed; artificial link share 0.48–0.60% |
| Checks | `check_package.py` **322 checks pass**; `check_manifest.py` OK |

**Not done, deliberately:** S1 and S3 leave 532 and 712 shuttle/BRT trips with no
`shape_id`. That is valid GTFS, pt2matsim maps them from the network, and both routes
run on streets where a shape adds little. Recorded rather than built.

---

## P3 stage 1 — B2 rebuilt as tours (10 August 2026)

The P1 chains were a skeleton, not plans. Replaced, not patched
([`DECISIONS.md`](DECISIONS.md) §9.2). Before → after, measured on the full output:

| | P1 | P3 |
|---|---|---|
| Distinct non-home destination coordinates | **1,481** (zone centroids) | **76,278** |
| Busiest single coordinate | **10.9%** of activity legs | **0.65%** |
| Legs with a home-based purpose not starting at home | **684,125 (47%)** | **0** |
| Return-home legs labelled NHB | **568,631 (all of them)** | **0** |
| Persons with more than one tour (real sub-tours) | **0%** | **56.7%** |
| Legs arriving after the day horizon | 1.77%, latest **36.0 h** | **0** |
| Day types | 1 generic | **3** (WEEKDAY / SAT / SUN) |
| External-tier demand | none | **5,384** weekday boundary agents |
| Realised week trip rate vs HTS 3.473 | 3.298 (−5%) | **3.397 (−2.2%)** |
| Gravity distance vs HTS, worst purpose | **+66%** (education) | **exact, all six purposes** |

95.5% of activity ends now sit on an observed POI or CBD building footprint.
Output is three files, `demand/plans/B2_activity_trips_{WEEKDAY,SAT,SUN}.csv`,
5.86M legs. `build_population.py` keeps B1 and no longer writes chains.

**Watch this one:** `P_INTERMEDIATE_STOP` (0.12–0.30, swept 0.10–0.35) decides how
many sub-tours exist, and therefore how freely MATSim's mode choice can vary within
a day. It is assumed, and it is the demand-side parameter with the most leverage
over mode share.

---

## P3 stage 2 — MATSim plans and run inputs (10 August 2026)

| | |
|---|---|
| Plans | `demand/plans/matsim/population_{WEEKDAY,SAT,SUN}.xml.gz` — **521,502** weekday persons, 2,237,373 legs, 2,758,875 activities, at **100%** of the population |
| Run inputs | `scenarios/matsim/<S>/<DAY>/` — **30 sets** (10 scenarios × 3 day types), each with a day-type-filtered schedule, its vehicles, a patched run network and a `config.xml` |
| Seed mode share | car 55.7 / ride 18.6 / walk 19.3 / pt 4.0 / bike 2.4 against HTS 57.5 / 21.5 / 16.1 / 3.4 / 1.6 — an **initial condition**, not a calibration |
| One build | day-type split runs on the **already-mapped** schedule: all 1,714 S2 route link sequences byte-identical to source, stop→link map for 4,174 facilities unchanged |
| Run network | the scenario's **own mapped** network + E1 patch by `osm:way:id`, not `networks/matsim/variants/` (which is patched over the base and has no transit links — reference only, not runnable) |

**Three defects caught here, two of which would have produced a plausible-looking
wrong answer:**

1. The day-type token is dot-delimited in the era and scenario feeds
   (`nisc001:WEEKDAY.2302960`) but **underscore-delimited** for the S1 shuttle and
   S3 BRT (`S1SHUTTLE_WEEKDAY_0_1`). Matching only the dotted form dropped both from
   every day type — **S1 would have run without its shuttle and S3 without its BRT**.
2. Banned-turn removal was applied network-wide, deleting **1,235** observed turn
   restrictions instead of the **8** on the corridor.
3. `gzip.open` stamps the wall clock into the gzip header, so identical content
   produced different manifest digests on every rebuild. Pinned in
   [`src/build/det_io.py`](src/build/det_io.py); repeat builds are byte-identical.

**Carried into P4:** what C1 loses in translation to MATSim scoring — the nested-logit
structure (`nesting_coefficient_pt = 0.65`), per-purpose value of time (collapsed to a
trip-weighted 16.96 AUD/h) and the crowding multipliers. See
[`DECISIONS.md`](DECISIONS.md) §9.3.

---

## P3 stage 3 — assumptions replaced by measurement where the data allows

Three P3 constants are no longer typed in. `src/build/measure_network_factors.py`
derives them from layers already in the package and writes
[`params/C2_network_factors.json`](params/C2_network_factors.json):

| Value | Was | Now | Measured from |
|---|---|---|---|
| Detour factor (straight-line → network) | assumed 1.30 | **1.3376**, sweep 1.25–1.42 | 551 population-weighted zone pairs routed over the observed A1 road graph |
| Weekday vs weekend travel | assumed, implied 0.825 | **0.7521**, sweep 0.709–0.816 | RMS traffic counts' own `WEEKDAYS`/`WEEKENDS` periods, 551 station-years |
| Work-attendance lower bound | none | **0.651** | Census G62 — bounds the `P_MANDATORY` sweep, and is **not** allowed to set the value, because census night was August 2021 with 19.2% working from home ([`DECISIONS.md`](DECISIONS.md) §2.4) |

**Seven parameters breached proposal §8.1** by carrying no sweep range. They now
carry one, and `check_package.py` **tests the rule** instead of relying on discipline.

**What is genuinely not localisable, and is labelled so:** MATSim's `performing`,
monetary distance rate, typical activity durations and replanning weights are
properties of the scoring formulation, not observable quantities of Newcastle.

**What is localisable but not yet available:** `EXTERNAL_INTERACTION_RATE` needs the
ABS journey-to-work origin-destination table (SA2 usual residence × SA2 place of
work). The package has the place-of-work side but not the pairing — added to
[`DECISIONS.md`](DECISIONS.md) §13 as a standard TableBuilder extract, not a formal
request.

---

## P4 stage 0 — the run inputs did not load (10 August 2026)

P3 verified the 30 assembled sets thoroughly *as data* and every one of those
statements is still true. **None of them could be loaded by MATSim.** Found by
launching one; see [`DECISIONS.md`](DECISIONS.md) §9.4.

| Defect | Reach | Symptom |
|---|---|---|
| The day-type filter round-trips through `ElementTree`, which drops the **doctype** | all 30 schedules | MATSim picks its reader *from* the doctype — parse fails at line 2 |
| Removing two thirds of the routes **orphans stop facilities and `minimalTransferTimes` relations** (113 + 42 on S2/WEEKDAY; 2,193 + 1,034 on S0/SAT) | all 30 schedules | `SwissRailRaptorData` dereferences a null array |
| The kerbside patch appends a **second `<attributes>` block** to links that already have one | **6 of 10** run networks — S0, S1, S2c, S6 (59 links), S4 (302), S5 (498) | network DTD rejects it. S2/S2a/S2b/S3 escaped only because `net_base2026` carries no patch rows |

The third is the dangerous one: it hits exactly the six scenarios carrying an E1
road change and leaves the four that don't alone. Fixed; the 30 sets rebuild
byte-identically with patch counts unchanged (54 lanes / 59 kerbside / 8 banned
turns), **all 30 load and run**, and `check_package.py` grew **556 → 657 checks**
asserting all three failure modes per set.

## P4 stage 0 — what a run costs, measured (10 August 2026)

S2 × WEEKDAY, nested deterministic subsamples (1% ⊂ 10% ⊂ 25%), 16 threads,
`ride` teleported. **24 cores, 63.5 GiB.**

| Sample | Persons | Steady per-iteration | Peak resident |
|---|---:|---:|---:|
| 1% | 5,209 | **9.8 s** | 9.8 GiB |
| 10% | 52,758 | **29.9 s** | 18.4 GiB |
| 25% | 131,291 | **~64 s** | 31.5 GiB |

Large fixed cost, near-linear slope: time ≈ 3.1 s + 268 s × fraction, memory ≈
9.6 + 87 GiB × fraction. So **~4.5 min/iteration and ~97 GiB at 100% — a 100%
weekday run does not fit in 63.5 GiB.** Practical ceiling ≈ 40%.

**The P3 sizing is confirmed and then some.** 1,400 sweep runs + 300 headline
runs is 5,100 run-days once each is counted across three day types; at 25% that
is ~765 days of wall clock. The gap is ~3 orders of magnitude, so it closes only
by cutting sweep breadth, replications and day types — **not** by sample
fraction, which is the weakest lever because cost is sublinear in it.

## P4 stage 0 — mode choice was not choosing (11 August 2026)

Three more defects, all in the configuration rather than the data, so the §9.4
load test could not see them — it overrode the mode handling in order to exercise
the artefacts. Full detail in [`DECISIONS.md`](DECISIONS.md) §9.6.

| # | Defect | Consequence |
|---|---|---|
| 4 | `ride` was declared a network mode that **no link permitted** | `checking 0 nodes and 0 links` for mode ride, then a throw in `PrepareForSim`. **The shipped config could not run even after the §9.4 fixes** |
| 5 | `subtourModeChoice` was never configured, so MATSim's default `modes=car,pt,bike,walk` applied and a `ride` subtour was an **absorbing state** | `ride` sat at **0.18311 in every iteration**, to five decimals. 18.6% of legs were an input wearing the costume of a result |
| 6 | `considerCarAvailability` defaulted to `false` | B1's synthesised car availability was **ignored by mode choice** |

Fixed: `qsim.mainMode=car` (a car passenger is not a second vehicle), `ride`
added to the `modes` of 143,891 links so it is *routed* on the road network,
`travelTimeCalculator.separateModes=false` so it reads the car travel times,
`subtourModeChoice.modes=car,ride,pt,bike,walk` and `considerCarAvailability=true`.
The shipped config now runs unmodified and `ride` moves.

**The seed is now uninformed.** Uniform over the modes each person can use,
conditioned only on B1 car availability — car **14.3%** against an HTS target of
59%, deliberately a bad guess. The P3 informed seed is retained behind
`build_matsim_plans.py --seed-mode informed` so seed dependence can be **tested**
rather than asserted. `check_package.py` now asserts the seed is *far from* the
target, the inversion of the check it replaces. **814 checks**, all passing.

## P4 stage 0 — the seed test, and a model that does not converge (11 August 2026)

Two 1% runs of 250 iterations, identical except the initial mode draw
([`DECISIONS.md`](DECISIONS.md) §9.7). 2,205 s and 2,419 s wall.

| | car | ride | pt | walk | bike |
|---|---:|---:|---:|---:|---:|
| Uninformed, iteration 0 | 0.143 | 0.223 | 0.101 | 0.323 | 0.209 |
| Informed, iteration 0 | 0.564 | 0.183 | 0.019 | 0.209 | 0.026 |
| **Uninformed, iteration 250** | **0.147** | **0.664** | 0.059 | 0.043 | 0.088 |
| **Informed, iteration 250** | **0.201** | **0.649** | 0.049 | 0.031 | 0.070 |
| HTS calibration target | 0.590 | 0.206 | 0.038 | 0.134 | 0.032 |

1. **Seed influence decays but is not gone.** A 42.1 pp gap on car closes to
   5.4 pp — 87% — and the residual cannot be separated from point 2.
2. **The model has not converged.** Innovation switches off at iteration 200;
   ride still moved 0.619 → 0.664 over the last 50 iterations with no new plans
   being created. **`lastIteration=100` is far too low and 250 is also too low.**
   The default is left at 100 rather than replaced by another unjustified number,
   and `check_package.py` now carries a **standing warning** to that effect.
3. **The attractor is wrong, and it is a specification problem.** `ride` has no
   driver-availability constraint, is charged half car's distance cost, and
   consumes no road capacity; only `asc_car_passenger = −0.85` restrains it.
   Points 2 and 3 are probably the same fact — a dominating mode drives the
   co-evolution to a corner, and corners relax slowly.

## P4 stage 1 — the ride constant, constrained to observed occupancy (11 August 2026)

§9.7 left three options open. The resolution is the second branch
[`DECISIONS.md`](DECISIONS.md) §8.5 already permits — *"constrain them and report
the constraint"* — with the constraining quantity **measured, not chosen**
([`DECISIONS.md`](DECISIONS.md) §9.8).

**The model produced a physically impossible car.** 4.52 ride legs per car leg is
**5.52 people per vehicle**. Newcastle's observed occupancy, from the HTS driver
and passenger trip counts, is **1.3503** and has been between **1.2493 and
1.3940** in every one of the seven survey years in the file.

| | |
|---|---|
| Constraint derived by | `src/calibrate/measure_mode_constraints.py` → [`params/C4_mode_constraints.json`](params/C4_mode_constraints.json) |
| Value | occupancy **1.3503**, passenger:driver **0.3503**, sweep = the observed seven-year spread |
| Also fixed | `ride` was charged **half** the car distance rate. That half was typed in and double-charges — a vehicle's cost is paid once, and at occupancy 1.35 charging both occupants makes aggregate vehicle operating cost 1.35× the real one. The only derivable value is **zero** |
| Solved by | `src/calibrate/solve_asc_ride.py`, interpolating on log(ride ÷ car) to the observed ratio. It **never opens the validation targets**, so it cannot read a holdout row |

**Why this is not ASC absorption:** the constrained constant is *car passenger*;
`asc_lr`, `asc_bus` and `asc_rail` stay at their §8.5 priors. The constraining
quantity is *how many people fit in a car*, not patronage or PT mode share. No
hypothesis in proposal §3 turns on it.

**P4 deliverable 1 exists.** `src/run/` now holds `sample_population.py` (nested
hash subsample; **transit seat capacity scaled with the fraction**, without which
a 10% sample gives every bus ten times its real capacity and crowding silently
disappears) and `run_matsim.py` (deterministic, resumable, records its own run).
`--iterations` has **no default**, because §9.7 shows both 100 and 250 are wrong
and no justified value has been measured.

---

## P4 stage 1 — the with-tram scenario had no tram on a weekday (11 August 2026)

Found by building the metric extractor: it reported **zero** light rail boardings
for S2 × WEEKDAY. Full detail in [`DECISIONS.md`](DECISIONS.md) §9.9.

`S2.zip` carries 252 weekday light rail trips and the mapping keeps all of them.
But **pt2matsim groups trips into a route by stop sequence, not by service**, so
each of the two light rail routes holds 275 departures — 74 Saturday, 75 Sunday
and **126 weekday** — and both are *named* after a weekend trip. The day-type
filter keyed on the route name.

| | |
|---|---:|
| Routes whose departures span more than one day type | **233 of 1,714 (13.6%)** |
| Departures placed in the wrong day type | **1,261 of 4,269 (29.5%)** |
| Weekday service delivered vs true | 1,747 vs 2,139 — **18% short** |
| Saturday / Sunday delivered vs true | **18% / 19% over** |

**A weekday S2-versus-S0 comparison would have measured the effect of nothing at
all**, and reported it confidently.

**Why the check passed.** It asserted the split partitions the *route set*
exactly — 1,231 + 291 + 192 = 1,714. True, and the wrong invariant: partitioning
routes is not partitioning service when a route is not day-type homogeneous.

Fixed by filtering **departures** rather than routes, still on the already-mapped
schedule, so §3.5 holds unchanged. Light rail is now 252 / 148 / 150, matching
the GTFS calendar exactly. Two checks replace the old one: departures partition
exactly, and **the intervention is present with departures in every day type** —
light rail for S2/S2a/S2b/S2c/S4/S5, the shuttle for S1, the BRT for S3, and
correctly nothing for the S0 and S6 counterfactuals. **860 checks.**

The three `asc_car_passenger` candidate runs then in flight were **discarded, not
reported**: a constant solved on a network with no weekday tram is a solve of a
different model.

## P4 stage 1 — analysis layer (11 August 2026)

`src/analyse/` now exists, and holds the two correspondences a fit needs before
any modelled quantity can be compared with a target:

| Script | What it resolves |
|---|---|
| `map_sa1_to_lga.py` | The mode-share target is **Newcastle LGA** and the model covers five (§12.1), but nothing in the package carried SA1 → LGA — `zones_SA1.csv` has SA2/SA3/SA4 only, and SA3 "Newcastle" is not Newcastle LGA. Spatial join against the ABS LGA boundaries already in `data/raw/`: **1,701 SA1s, 0 unmatched**, 390 in Newcastle |
| `map_count_stations.py` | A count target is a two-way total at a point, so it must resolve to links. **116 of 119** stations matched, 189 of 203 links by **name and proximity** rather than proximity alone, median distance 30.6 m. The 3 unmatched — one of them a calibration station — are outside the modelled network and are **reported, not dropped** |
| `extract_metrics.py` | Mode share by LGA of residence, PT boardings by line, link volumes at mapped stations. Reads no validation target, so it cannot see the split |

## What P4 still has to build

Proposal §7.1 makes P4 *"fit to observed counts, Opal boardings, run times;
parameter estimation"*, delivering a **calibrated base** and a **calibration
report** — §8 deliverable 3, *"fit statistics against all validation targets,
with honest reporting of where fit is poor"*. None of it exists yet.

| # | Deliverable | Where | Notes |
|---|---|---|---|
| 1 | ~~**Run harness**~~ **done** | `src/run/` | Nested subsample, transit seat capacity scaled with the fraction, deterministic, resumable, records its own parameters |
| 2 | ~~**Metric extraction**~~ **done** | `src/analyse/` | Mode share by LGA of residence, PT boardings by line, link volumes at the mapped count stations |
| 3 | ~~**Fit statistic**~~ **done** | [`src/calibrate/fit.py`](src/calibrate/fit.py) | Calibration rows only, and it raises if a holdout row survives the filter. **38 scored + 29 explained = 67**, asserted rather than assumed. A modelled zero is scored at −100%, not dropped — dropping it flattered the count fit by removing the stations where the model fails hardest (issue 19). The output contract now **fails a fit block that does not name its target ids** |
| 4 | **Calibration loop** — deterministic, resumable, and structurally unable to read a holdout row | `src/calibrate/` | |
| 5 | **Calibrated base** + parameter provenance | `params/` | |
| 6 | **Calibration report** | `docs/` | |
| 7 | **The outer-loop tolerance** — proposal §5.2 runs the MATSim↔SUMO loop *"until the corridor run time is stable within a tolerance **to be defined at calibration**"* | `DECISIONS.md` | **A P4 obligation that was not on any list until now.** It is a number P4 must define, not P5 |

**Everything above is downstream of the §8.5 decision in §9.7.** Building a
calibration loop before deciding which parameters it may move would be building
the wrong loop.

## P4 stage 2 — the input registry (11 August 2026)

Every value the model consumes that is not read from an immutable raw download
is declared in [`config/registry/`](config/registry/) with its units, its
provenance and either a sweep range or an explicit rule holding it fixed. Full
rationale in [`DECISIONS.md`](DECISIONS.md) §15; the generated reference is
[`docs/CONFIG_REFERENCE.md`](docs/CONFIG_REFERENCE.md).

**What it replaced:** 316 module-level constants across 45 scripts, a
110-parameter MATSim config per run set, and a handful of CLI defaults. Exactly
**one** of those 316 carried a machine-readable `source` label; 18 carried a
sweep.

| | |
|---|---:|
| Fields declared | **152** |
| …assumed | 72 |
| …literature | 18 |
| …definition | 36 |
| …measured / derived / observed | 5 / 7 / 2 |
| Fields with **no value at all** | **7** |
| Fields **held fixed** under §8.5 | 6 |
| `check_package.py` | 860 → **925 checks**, 1 standing warning |

**Proposal §8.1 is now a schema constraint, not a discipline.** A field whose
source is `assumed`, `literature`, `measured` or `derived` must carry a sweep, a
`held_fixed` rule, or a `derived_from` identity. There is no fourth option, and
`assumed` with no sweep does not validate.

**The six fields with no value are the project's honest edge.** SCATS phasing,
charging dwell and journey-linked Opal carry `value: null` and the resolver
**raises** rather than returning a point value — §0 and §13 enforced
structurally. So do two decisions nobody has taken: the MATSim↔SUMO outer-loop
tolerance (issue #8) and **the iteration count** (issue #5). `run_matsim.py` now
refuses to start without an explicit iteration count, which is the refusal
`--iterations` already implemented, moved into the registry where it binds
everything rather than one argument parser.

**Two factors that governed every P4 result were set in code with no rationale
and no range.** Neither `flowCapacityFactor` nor `storageCapacityFactor`
appeared anywhere in `DECISIONS.md`, `check_package.py` or the P4 checkpoint.
Both are *derived*, and neither is a choice: flow equals the sample fraction,
and storage equals flow. **A correction is recorded in §15.** The registry first
declared the storage exponent *assumed* and swept 0.75–1.0, on the reasoning that
MATSim's one-vehicle storage floor would cause spurious spillback at 1%. The
diagnostic run built to test that died in one second — MATSim rejects any storage
factor different from the flow factor and states the practice is superseded
"since the qsim became a lot more deterministic". The sweep declared values the
tool will not accept, which is the very failure the registry exists to prevent.
Corrected: the field is derived, the harness fails fast, and the check asserts
the equality. **The question the exponent stood proxy for — whether behaviour
moves with the sample fraction — is unaffected**, and is what the 1% versus 10%
diagnostic tests.

**Outputs are declared to the same standard as inputs.** `_run.json`,
`_metrics.json`, `_fit.json` and `_config.json` each carry a JSON Schema in
[`config/schema/outputs/`](config/schema/outputs/), validated at write time. Two
rules are enforced beyond shape: a fit block must **name the target ids it was
computed over**, and `scored + unscorable` must reconcile to the calibration
targets available. Every run directory now carries `_config.json`, the resolved
snapshot — a completed run without one fails its contract, because a result that
cannot state its inputs is not reportable.

**The SUMO corridor layer is migrated and verified.**
[`build_sumo_corridor.py`](src/build/build_sumo_corridor.py) reads the registry;
the netconvert options that are *modelling choices* — left-hand traffic, the
signal controller type, junction joining, turnarounds, crossings — are named
fields rather than entries in a flag list. The corridor was rebuilt and **all
four nets and all seven TLS programs are byte-identical** to the pre-migration
build. Nine intermediates differed, and two further rebuilds **with no code
change** reproduced exactly the same nine, so they are timestamped by netconvert
rather than affected by the change. That refines the P2 claim: byte-identical
rebuild holds for the **nets**, not for `networks/sumo/_work/`.

**The build layer is migrated (P6 cleared).** 52 fields across 13 scripts now
resolve from the registry; runtime consumption went **16 → 68 of 140**. Gated by a
full rebuild in README order with byte-identical output, without re-running the
pt2matsim mapper (§3.5) — the stop→link fingerprints confirm the feeds it was
mapped from are unchanged. **The gate caught three pre-existing defects**: a
hash-seed-dependent set iteration in `build_landuse_parking.py`, wall-clock
timestamps embedded in all 11 GTFS zips making them unreproducible by
construction, and dict-order leaking into two reports. All three were invisible
because the package had not been rebuilt end to end since the manifest was
written — a manifest digest only proves reproducibility if something re-derives
it. See [`DECISIONS.md`](DECISIONS.md) §15.

**Superseded note.** The rest of
`src/build/*.py` still hold their own constants. Two copies of a number is the
drift this package cannot absorb, so
[`src/registry/check_legacy_drift.py`](src/registry/check_legacy_drift.py) pins
them together by test — **1 remaining**, one deliberate divergence (the migration removed the other 51 constants outright), one expression
that is not a literal. Writing that check immediately found **four values
transcribed wrongly into the registry**; the code was authoritative and the
registry was corrected. That migration needs a full package rebuild to verify
byte-identically and **has not been run**.

**One determinism defect fell out of the gate.** The committed
`_sumo_build_report.json` recorded `netconvert_seconds`, so its manifest hash
changed on every rebuild even when the nets did not — a committed artefact that
could not be regenerated to the same bytes. Timings moved to the gitignored work
directory; the report is now byte-identical across consecutive builds and the
manifest was regenerated. The defect predates this change.

**The corridor has been built four times and simulated zero times.** No SUMO run
harness exists. The fields one would need are declared, and two carry no value on
purpose: `RUN.sumo.replications` (issue #6) and
`E.coupling.outer_loop_tolerance_s` (issue #8).

**Driving it:**

```bash
# a committed overlay - the reproducible way to vary a run
cp config/runs/example.json config/runs/my_run.json
python src/run/run_matsim.py --scenario S2 --day WEEKDAY --run-config my_run

# a one-off, checked against the same sweep and held-fixed rules
python src/run/run_matsim.py --scenario S2 --day WEEKDAY \
    --set RUN.sample.fraction=0.10 --set RUN.controler.last_iteration=500

WICKHAM_RUN_SAMPLE_FRACTION=0.10 python src/run/run_matsim.py --scenario S2 ...
```

---

## P4 stage 2 — is the 1% sample representative? (11 August 2026)

Two runs identical but for the sample fraction, 250 iterations, S2 × WEEKDAY.
Full detail in [`DECISIONS.md`](DECISIONS.md) §9.10. **Neither is a result** —
250 iterations is known non-converged; these are diagnostics.

| Mode | 1% | 10% | difference | HTS |
|---|---:|---:|---:|---:|
| car | 0.1223 | 0.1913 | **+6.91 pp** | 0.590 |
| ride | 0.7213 | 0.7190 | **−0.23 pp** | 0.206 |
| pt | 0.0395 | 0.0044 | **−3.51 pp (9×)** | 0.038 |
| walk | 0.0315 | 0.0123 | −1.93 pp | 0.134 |
| bike | 0.0854 | 0.0730 | −1.24 pp | 0.032 |

- **Ride dominance survives a ten-fold increase in population unchanged** — the
  two trajectories track within 0.006 at every checkpoint. It is a specification
  problem, not a sampling artefact, and §9.7 is confirmed at scale.
- **Non-convergence is identical at both fractions**: ride drifts +0.046 and
  +0.047 between iterations 200 and 250 *after innovation stops*.
- **Car and PT levels do not transfer from 1%.** Calibration against the
  mode-share targets cannot be done there, and the hope that sweeps could run
  cheaply at 1% is not available for those two modes.
- **The car/PT divergence has no established mechanism.** Transit capacity and
  small-sample spillback were both checked and neither survives; recorded as open
  rather than guessed.
- **An unreconciled vehicle capacity surfaced**: the fleet gives light rail 180
  seats and no standing room, while §4.1 records a published maximum of 270 and
  an assumed 60 seated. Because nothing has standing room, the C1 crowding
  multipliers can never apply in any scenario.

**Sequencing consequence.** The dominant distortion is a specification error that
scale does not cure. Coupling SUMO to a demand model in which 72% of legs are car
passengers would propagate it into every corridor number, so **SUMO waits**.

---

## P4 stage 2 — `ride` now requires a driver (11 August 2026)

The §9.10 finding acted on. Full rationale and the §8.5 departure in
[`DECISIONS.md`](DECISIONS.md) §9.11.

A person may be a car passenger only if their household holds a vehicle **and**
contains another licence holder — derived from B1, not assumed. **22.1% of the
weekday population (115,034 of 521,502) may not ride.**

| | before | after |
|---|---:|---:|
| Illegal ride legs at iteration 30 | 4,723 | **0** |
| Seed ride share | 0.2228 | 0.1712 |
| Ride at iteration 25 | 0.3098 | **0.2548** |

**Two pieces were needed and the first alone did nothing.** MATSim's
`PermissibleModesCalculator` governs only *new* mode choices; it never strips a
mode from a plan an agent already holds. With the calculator alone, 4,723 illegal
ride legs survived 30 iterations because the *seed* had handed those agents a
ride plan that `ChangeExpBeta` kept re-selecting. Fixing the seed as well took it
to zero. Core MATSim honours `carAvail` but has no equivalent for `ride`, so the
calculator is ours: [`src/java/wickham/`](src/java/wickham/), ~40 lines, compiled
by the pinned javac. **The pinned toolchain digests are unchanged** — this adds an
artefact beside the shaded jar rather than replacing one.

**Necessary, probably not sufficient — stated now rather than discovered later.**
The constraint lowers the ceiling to the 77.9% who may ride, and the
unconstrained attractor was 0.72, so it does not bind hard at the corner. Ride was
still climbing at iteration 30 (0.2787). **Whether it now settles near the
observed 0.206 is unmeasured** and needs a converged run at 1% *and* 10%.

---

## P4 stage 3 — the ride constraint measured, and 1% found unusable (11 August 2026)

The §9.11 question answered. Two runs of S2 × WEEKDAY at 250 iterations, 8 threads,
committed overlays, declared pipeline. Full detail in [`DECISIONS.md`](DECISIONS.md) §9.12.
**Neither is a result** — §9.7 shows 250 iterations is short of relaxation.

**Mode share, Newcastle LGA** — the reportable quantity, not the five-LGA aggregate:

| | 1% | **10%** | HTS |
|---|---:|---:|---:|
| Vehicle driver | 16.01 | **30.85** | 59.0 |
| **Vehicle passenger** | 61.06 | **50.94** | **20.6** |
| mean absolute error | 23.19 pp | **17.43 pp** | |
| passengers per driver | 3.8140 | **1.6512** | 0.3503 |

**Necessary, not sufficient.** Ride fell from 0.72 to 0.56 on the five-LGA quantity
— the largest single move any P4 change has produced — and still lands at **2.5×**
the observed share, with occupancy **4.7×** observed. §9.11 predicted exactly this:
the ceiling is 0.779 and the model settles far below it, so the constraint never
binds where it would matter. **Issue #16 stays open**; the three candidates are live
and the §8.5 departure has not been chosen.

**1% is unusable, not merely unrepresentative (#17).** 1,032 car legs abort at the
30 h horizon against **4** at 10%, and 380 PT passengers board and never alight
against **0**. A tenfold population increase cuts car non-completion **258-fold**,
so it is not proportional to demand: at `flowCapacityFactor = 0.01` an 1,800 veh/h
link discharges **one vehicle every 200 s** and cars queue on arithmetic alone.
This is *flow*, distinct from the *storage* argument §9.10 already ruled out, and
it is the first mechanism for the car/PT divergence to survive measurement after
four died. It also explains why `modestats.csv` and `_metrics.json` disagree: one
records the mode agents **chose**, the other trips that **completed**.

**A 25% run is in flight** to confirm the 10% reading before a §8.5 departure is
chosen — a departure cannot be un-logged, and the threshold between 10% and 25% is
unmeasured.

**A defect that flattered the fit (#19).** `fit.py` dropped a count station when
the model routed *zero* traffic over it, under a reason that said the station had
not resolved to a link. The M1 Pacific Motorway at Wyee — observed **48,016** AADT,
modelled **0** — was silently excluded, along with Raymond Terrace Road. A modelled
zero is a **result**, and the worst one in the set. Now scored at −100% and flagged:
**38 scored + 29 explained = 67**, counts 31 → **33 stations**, and the count error
honestly worsens (mean −72.1% → **−73.8%**). It exposes a real gap — the model puts
**no cars on the M1 at Wyee** — most likely in the external boundary tier.

**The fit statistic had no tests at all.** [`tests/check_package.py`](tests/check_package.py)
contained zero checks against [`src/calibrate/fit.py`](src/calibrate/fit.py) — which
is how #19 survived: a defect that silently *improved* the reported fit, in code the
whole suite never touched. Ten checks now drive the scoring functions on synthetic
metrics, so they need no completed run (`results/` is gitignored and a check may not
depend on one). Verified by reintroducing the defect — **3 checks fail**, and pass
again on restore. **937 checks**, 1 standing warning.

**Three values were governing the model from outside the registry**, found by audit:
`B.counts.station_match_radius_m` (**new field**, 120 m, swept 60–120 on measurement
— it decides which count targets are scorable at all); `sample_population.SEED`,
which held its own copy of 20260810; and `solve_asc_ride.py`, which carried five run
parameters and the −0.85 prior as literals **and called `run_matsim.run()` with the
pre-registry signature, so it could not execute at all**. All now resolve through
the registry. `count_station_links.csv` rebuilds **byte-identical**, which is the
gate. Two orphaned P1 probes were deleted.

---

## P4 stage 3 — trip length by mode, an observable the package always held (11 August 2026)

The HTS carries `TRIP_AVG_DISTANCE` and `TRIP_AVG_TIME` per mode for fourteen
years and **nothing used them**. Mode share says how many people choose a mode; it
cannot say whether they choose it for the right journeys. Full detail in
[`DECISIONS.md`](DECISIONS.md) §9.13.

Now measured into [`params/C4_mode_constraints.json`](params/C4_mode_constraints.json)
on the same principle as the §9.8 occupancy constraint — value from the base year,
**sweep from the observed spread across every survey year**, never an interval
anyone chose — declared as **ten registry fields** (one per mode per quantity,
because the schema takes an interval per field and weakening it would have been the
wrong repair), and reported by `fit.py` beside the fit.

**It is a constraint, not a target.** The 67/143 split is pre-registered and
nothing joins it; `check_package.py` asserts no calibration metric carries a
trip-length name.

**It caught an error the moment it existed, and the error was mine.** A hand
comparison had reported car as "10.16 modelled against 10.20 observed — essentially
exact". That compared a **five-LGA** modelled mean with a **Newcastle-LGA**
published one — the same geography mismatch §12.1 records for the seed. Like for
like, both sides Newcastle LGA:

| mode | modelled km | observed km | ratio |
|---|---:|---:|---:|
| car | 6.36 | 10.20 | **0.62** |
| ride | 8.56 | 9.80 | 0.87 |
| walk | 2.90 | 0.70 | **4.14** |

So car trips are **38% too short, not exact**, and the earlier "ride is 41% too
long" was an artefact. What survives is the part that matters, because a **ratio is
robust to geography**: modelled ride ÷ car trip length is **1.346** against an
observed **0.961**. Observed passenger trips are slightly *shorter* than driver
trips; the model makes them **35% longer** — the signature the §9.8 zero distance
rate would produce. It also puts a number on a distortion nobody had looked at:
modelled **walk** trips run **4.1× their observed length**.

**Why it is in place before the §8.5 departure is chosen.** §9.8 set `ride`'s
distance rate to zero and declared it *derived, not assumed*, on an aggregate-cost
identity — and the observable that would have tested that identity was in the
package all along. A value declared `derived` is only as good as the identity
behind it. Whichever ride candidate is taken can now be judged against an
observable rather than against the mode share it was chosen to move.

**Also unused until now:** `Serve passenger` is **15.7% of observed journeys** —
87,000 a day, the second-largest purpose in Newcastle, larger than commuting. B2
generates none (#11). That is a measured demand component, not the assumption the
issue recorded, and it is the driver side of the same problem.

**942 checks**, 1 standing warning.

---

## How to resume

**For P4 specifically, read [`docs/P4_CHECKPOINT.md`](docs/P4_CHECKPOINT.md)
first** — the long-form handoff: the seven defects and the pattern they share,
every measurement taken, every decision and its rationale, what is built and how
to drive it, and the traps. This file stays the short live status.


1. Read this file, then [`DECISIONS.md`](DECISIONS.md) §0 (status summary) and
   [`CLAUDE.md`](CLAUDE.md) (conventions and hard constraints).
2. `python tests/check_manifest.py` — confirms the committed subset is intact.
3. `python src/setup/bootstrap_toolchain.py --verify` — confirms the toolchain, or run it
   without `--verify` to fetch it (~1.4 GiB, needed only to rebuild the networks).
4. `python tests/check_package.py` — needs the full local package, the built networks
   **and** the P3 demand artefacts; **925 checks**. Run it before declaring any phase
   complete.
5. `python src/registry/render_docs.py` after any change to `config/registry/`, or
   `check_package.py` will report the reference as stale.
6. Branch as `<git-handle>/<short-kebab-description>` (never `claude/*`).
