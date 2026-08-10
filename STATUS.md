# STATUS — Project Wickham

Single source of truth for **where the build is, what's next, and how to resume**. Read
this at session start. **Keep it current in the same commit/PR as the work it describes**
— if a change makes a line here wrong, fix the line in that change, not later.

**Last updated:** 10 August 2026
**Stage:** **P3 demand synthesis complete.** Population, tour-based chains, MATSim
plans and per-scenario run inputs all built on one network build. **No scenario has
been run. Nothing in this repo is a result.** **No scenario has been run. Nothing in this repo is a result.**

---

## Phase board

Phases as defined in [`newcastle-lr-proposal.md`](newcastle-lr-proposal.md) §7.1.

| Phase | State | Notes |
|---|---|---|
| P0 Scoping | ✅ complete | Base year 2026, zone system, scenario list S0–S6 settled. Scope calls closing proposal §10 are recorded in [`DECISIONS.md`](DECISIONS.md) §1. |
| P1 Data acquisition | ✅ complete | 182 files, 2.31 GiB, all provenance-tagged and hashed in [`data/MANIFEST.csv`](data/MANIFEST.csv). Three critical inputs remain unobtained — see below. |
| P2 Network build | ✅ complete | MATSim network + 15 mapped schedules, 4 SUMO corridor nets, corridor attributes graded by evidence. See below. |
| P3 Demand synthesis | ✅ complete | Shape defect closed, network rebuilt once, B2 rebuilt as tours (3 day types + external boundary demand), MATSim plans and 30 runnable scenario×day-type input sets. 528 package checks pass. |
| P4 Calibration | ⬜ next | 67 calibration targets built; 143 held out. Mode share is seeded near HTS but **not calibrated** — that is P4's job ([`DECISIONS.md`](DECISIONS.md) §9.3). |
| P5 Scenario runs | ⬜ not started | `src/run/` is empty. **Read the one-build constraint in [`DECISIONS.md`](DECISIONS.md) §3.5 before designing a run.** |
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
| Validation | 210 targets (67 calibration / 143 holdout) |
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
| Plans | `demand/plans/matsim/population_{WEEKDAY,SAT,SUN}.xml.gz` — **517,936** weekday persons, 2,188,436 legs, 2,706,372 activities, at **100%** of the population |
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

## Open for P5 — the run load does not fit one machine

Sizing done during P3 planning, recorded here so P5 does not rediscover it:

| | Runs |
|---|---:|
| Sensitivity sweep (140 points × 10 scenarios) | 1,400 |
| Headline set (10 scenarios × `n_replications=30`) | 300 |

At any sample fraction this does not fit on a single workstation. **The levers are
sweep breadth and `n_replications`, not the population sample fraction** — restricting
the sweep to the decisive contrasts (S2vS0, S2vS2b) is ~3.3×, and 30 → 10 replications
another ~3×. Demand is built at 100% precisely so this stays a P5 run-time choice;
measure a real per-iteration cost before picking fractions.

---

## How to resume

1. Read this file, then [`DECISIONS.md`](DECISIONS.md) §0 (status summary) and
   [`CLAUDE.md`](CLAUDE.md) (conventions and hard constraints).
2. `python tests/check_manifest.py` — confirms the committed subset is intact.
3. `python src/setup/bootstrap_toolchain.py --verify` — confirms the toolchain, or run it
   without `--verify` to fetch it (~1.4 GiB, needed only to rebuild the networks).
4. `python tests/check_package.py` — needs the full local package, the built networks
   **and** the P3 demand artefacts; **528 checks**. Run it before declaring any phase
   complete.
5. Branch as `<git-handle>/<short-kebab-description>` (never `claude/*`).
