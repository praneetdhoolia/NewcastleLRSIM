# STATUS — Project Wickham

Single source of truth for **where the build is, what's next, and how to resume**. Read
this at session start. **Keep it current in the same commit/PR as the work it describes**
— if a change makes a line here wrong, fix the line in that change, not later.

**Last updated:** 11 August 2026
**Stage:** **P4 stage 0 complete; P4 proper is blocked on one decision.** Six
defects fixed — the 30 run-input sets could not be loaded by MATSim at all, and
the mode choice was not choosing. Run cost, seed dependence and convergence are
now measured rather than assumed. **The model does not converge and settles on a
mode split far from the observed one for a structural reason, which collides with
the pre-registered rule on mode constants (§8.5). No calibration has been
performed and nothing in this repo is a result.**

---

## Phase board

Phases as defined in [`newcastle-lr-proposal.md`](newcastle-lr-proposal.md) §7.1.

| Phase | State | Notes |
|---|---|---|
| P0 Scoping | ✅ complete | Base year 2026, zone system, scenario list S0–S6 settled. Scope calls closing proposal §10 are recorded in [`DECISIONS.md`](DECISIONS.md) §1. |
| P1 Data acquisition | ✅ complete | 182 files, 2.31 GiB, all provenance-tagged and hashed in [`data/MANIFEST.csv`](data/MANIFEST.csv). Three critical inputs remain unobtained — see below. |
| P2 Network build | ✅ complete | MATSim network + 15 mapped schedules, 4 SUMO corridor nets, corridor attributes graded by evidence. See below. |
| P3 Demand synthesis | ✅ complete | Shape defect closed, network rebuilt once, B2 rebuilt as tours (3 day types + external boundary demand), MATSim plans and 30 scenario×day-type input sets. They did not in fact load in MATSim — fixed at P4 stage 0 (§9.4). |
| P4 Calibration | 🟡 stages 0–1 | Run inputs load (§9.4), run cost measured (§9.5), mode choice fixed and the seed made uninformed (§9.6), seed dependence and convergence measured (§9.7), the ride constant constrained to observed vehicle occupancy (§9.8), target identifiability written down (§12.1–12.4). `src/run/` and `src/calibrate/` exist; **`src/analyse/` is still empty and there is no fit statistic yet**. |
| P5 Scenario runs | ⬜ not started | `src/run/` is empty. **Read the one-build constraint in [`DECISIONS.md`](DECISIONS.md) §3.5 before designing a run**, and §9.5 before choosing a sample fraction. |
| P6 Analysis | ⬜ not started | `src/analyse/` is empty. |
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

## What P4 still has to build

Proposal §7.1 makes P4 *"fit to observed counts, Opal boardings, run times;
parameter estimation"*, delivering a **calibrated base** and a **calibration
report** — §8 deliverable 3, *"fit statistics against all validation targets,
with honest reporting of where fit is poor"*. None of it exists yet.

| # | Deliverable | Where | Notes |
|---|---|---|---|
| 1 | **Run harness** — deterministic nested subsample, transit vehicle capacity scaled with the sample, launch, resume, record | `src/run/` | The scratchpad prototype behind §9.5 and §9.7 is not committed. Vehicle capacities are `seats` only with `standingRoomInPersons=0`, so below 100% they must be scaled or capacity never binds |
| 2 | **Metric extraction** from events — boardings by line, link volumes, mode share **by LGA of residence** | `src/analyse/` | The mode-share target is Newcastle LGA and the model is five LGAs (§12.1) |
| 3 | **Fit statistic** against the 67, per target, with the §12.2a corrections shown and never closed by a fitted constant | `src/calibrate/` | Must name the targets it was computed over — "fits 67 targets" overstates what §12.1 says the data supports |
| 4 | **Calibration loop** — deterministic, resumable, and structurally unable to read a holdout row | `src/calibrate/` | |
| 5 | **Calibrated base** + parameter provenance | `params/` | |
| 6 | **Calibration report** | `docs/` | |
| 7 | **The outer-loop tolerance** — proposal §5.2 runs the MATSim↔SUMO loop *"until the corridor run time is stable within a tolerance **to be defined at calibration**"* | `DECISIONS.md` | **A P4 obligation that was not on any list until now.** It is a number P4 must define, not P5 |

**Everything above is downstream of the §8.5 decision in §9.7.** Building a
calibration loop before deciding which parameters it may move would be building
the wrong loop.

## How to resume

1. Read this file, then [`DECISIONS.md`](DECISIONS.md) §0 (status summary) and
   [`CLAUDE.md`](CLAUDE.md) (conventions and hard constraints).
2. `python tests/check_manifest.py` — confirms the committed subset is intact.
3. `python src/setup/bootstrap_toolchain.py --verify` — confirms the toolchain, or run it
   without `--verify` to fetch it (~1.4 GiB, needed only to rebuild the networks).
4. `python tests/check_package.py` — needs the full local package, the built networks
   **and** the P3 demand artefacts; **657 checks**. Run it before declaring any phase
   complete.
5. Branch as `<git-handle>/<short-kebab-description>` (never `claude/*`).
