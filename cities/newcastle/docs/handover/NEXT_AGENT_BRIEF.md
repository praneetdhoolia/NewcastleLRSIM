# Brief for the next agent — the law is ZERO HARDCODING

*Written 15 August 2026. This is a HANDOVER, not a source of truth: where it
disagrees with [`STATUS.md`](../STATUS.md), [`DECISIONS.md`](../DECISIONS.md) or
[`.claude/CLAUDE.md`](../../../../.claude/CLAUDE.md), those win. Paste it whole to
start a session cold.*

---

═══════════════════════════════════════════════════════════════════════════════
§0  DO THIS FIRST
═══════════════════════════════════════════════════════════════════════════════

```bash
python src/setup/bootstrap_toolchain.py --verify   # ~1 min, COMPILES THE JAVA
python src/registry/check_hardcoding.py            # the ledger. READ IT.
```

**A 25% convergence pilot may already be running.** Check before starting
anything: `python src/analyse/run_view.py --run <tag> --once`, or look for a
`java.exe` whose command line names a run directory. A run announces its own
live view url when it starts — that is new, and it works.

If nothing is running and you need the iteration count (#5):

```bash
python run.py --run-config convergence_pilot_25pct --tag conv1000_25pct_<what>
```

**~16 h alone on this machine** - MEASURED at 58 s/iteration over the 43
iterations the dead arm completed, not the ~13 h this brief previously stated.
1000 iterations, innovation off at 800, leaving 200 iterations of measurable
post-innovation drift per mode.

**RUN ONE ARM AT A TIME.** Three arms (1% + 10% + 25%) were tried together and
the machine paged: three declared heaps total 78 GiB against 63.5 GiB of RAM,
Windows grew the pagefile from 8.1 to 19.1 GiB, and the 10% arm's median
iteration went from ~19 s alone to ~42 s. Iteration **count** survives
contention; iteration **duration** does not.

**WHAT THE PILOT IS.** A measurement of *how many iterations this model needs to
relax*. `RUN.controler.last_iteration` is declared `unobtained` and the resolver
refuses to invent one, because **100 and 250 are both MEASURED to be too low**
(§9.7, §9.27): 100→250 moves a mode 13.2 points, 250→500 6.8, 500→800 3.0, flat
only from ~900.

**WHAT IT IS NOT.** Not a result. No mode share, patronage, count or fit
statistic may be quoted from it. It runs on the **current demand**, which the B0
batch replaces. Its **convergence behaviour** survives that; its **mode shares do
not**.

**A run with no `_run.json` is not a result and is not kept.** A machine crash
took a three-arm attempt; every partial reading was deleted, including the
watcher's timing series — a timing file that outlives its run silently blends two
runs into one benchmark. Delete both when you delete a run.

---

═══════════════════════════════════════════════════════════════════════════════
§1  THE MISSION, AND THE ONE LAW
═══════════════════════════════════════════════════════════════════════════════

| # | Goal | Done looks like | State |
|---|---|---|---|
| **G1** | **Answer the counterfactual.** What did the Newcastle light rail do to journey cost, accessibility, mode share and city-centre footfall, against the alternatives available in 2013? | A calibrated base, S0–S6 run to relaxation, the 143 holdout targets opened once, a findings paper stating its uncertainty bands | **Not started.** No scenario has been run to a reportable state |
| **G2** | **A city-agnostic simulator with a full input schema.** Any city supplies a declared package and the framework runs unchanged | A second city built from `config/schema/` alone, no framework edit | **Structurally in place, never exercised** |

G1 exists because that estimate was never produced and the business case is not
inspectable. Every discipline here — the sealed holdout, the declared sweeps, the
refusal to report a point value for an unobserved input — descends from one fact:
**9 of 10 rail projects overestimate patronage, by an average of 106%**
(Flyvbjerg, 210 projects). A model of a rail project that produces a flattering
answer is the EXPECTED outcome, not a surprising one.

### ★ THE LAW: ZERO HARDCODING

> **Every value the model uses is DECLARED in `cities/<city>/registry/`, carries
> its units and provenance and a sweep or a held-fixed rule, and REACHES THE
> MODEL THROUGH THE RESOLVER. A number in a script is a modelling choice nobody
> can see, nobody can sweep, and nobody will find.**

This is not style. It is the only structural cure for the defect this repository
keeps producing (§8), and it is why G2 exists at all: a framework that cannot
name a place cannot hide a value in one.

Three things follow, and they are not negotiable:

1. **`consumers` in the registry is a CLAIM, not proof.** Establish reach by
   **changing the value and watching the output change.** Every instance in §8
   was caught by arithmetic or an audit; **not one was caught by reading code.**
2. **A declared field that nothing reads is worse than no field**, because it
   looks like the model is configurable when it is not.
3. **A literal that happens to equal its registry field is the worst case of
   all** — it is right by accident, every test passes, and it silently stops
   being right the moment someone sweeps the field.

---

═══════════════════════════════════════════════════════════════════════════════
§2  ★ THE HARDCODING LEDGER — DONE. IT IS ZERO, AND `--strict` GATES CI
═══════════════════════════════════════════════════════════════════════════════

```bash
python src/registry/check_hardcoding.py            # report
python src/registry/check_hardcoding.py --strict   # exit 1 if anything is found
```

**This section used to say 95 items and "it is the first work". Both are now
historical.** The honest starting count was **185** — the audit was measuring
the wrong things — and it is **0**. Read `STATUS.md` for the table and
`DECISIONS.md` §14 (15 Aug) for the reasoning. What a new agent needs:

1. **There is no config template.** `src/registry/param_config.py` BUILDS the
   MATSim config and pt2matsim's two from fields carrying a `matsim_param` /
   `pt2matsim_*_param` binding. To add a MATSim parameter, **declare a field
   with a binding** — do not add a literal, because there is nowhere to put one
   and `closure()` fails the build if you find one.
2. **`run_matsim.py` emits, it does not patch.** A run overlay now reaches every
   declared field, not the six the old patcher rewrote.
3. **Reach is proven, not claimed.** `check_hardcoding` question 6 changes each
   bound value and diffs the emitted config: **69 of 69 reach**. This is the
   rule in §1 turned into a test. Keep it passing.
4. **The audit now reads Java too.** Two MATSim `ConfigGroup` defaults EQUALLED
   the registry values they shadow (`liveIntervalS = 3600.0`,
   `chargedModes = "car"`). A Java default equal to its declared value is the
   worst case there is: a config that lost the binding would run on the Java
   number and report success. Both are a sentinel or a neutral value now, with
   `checkConsistency` refusing the run.
5. **G2 IS EXERCISED**: `python tests/check_city_agnostic.py` builds a second
   city and asserts its config carries THAT city's values. Keep it passing — it
   is the only thing standing between "city-agnostic" and a claim. Building it
   found that **`CITYSIM_CITY` had never worked**: setting the documented city
   selector to any value, its own default included, made every registry load
   raise.
6. **Two committed registers, each entry with a written reason**:
   `STRUCTURAL` (18 — an HTTP status, a gzip level, decimal places) and
   `PENDING_CONSUMER` (7 — declared ahead of the phase that will read them,
   each naming its issue). Both are pruned automatically when they go stale.
   **A model value must never be added to `STRUCTURAL`.**

### ⚠ Two things THIS BRIEF told you that were wrong

- **§2.7 said `DWELL_CHARGING = 20.0` was pinned by `legacy_symbol` and should
  be left alone.** It carried none. `check_legacy_drift.py` never compared it,
  its `EXPECTED_DIVERGENCE` entry compared nothing, and it **pinned an
  `unobtained` input in a script** — the one refusal the registry exists to
  make. Fixed: it takes the baseline sweep point from the reference scenario's
  overlay.
- **§7 said 12 open issues and "#36 closed".** #36 is **OPEN**. There are 13.
  `STATUS.md` was right.

### What the fix exposed, and what it changed

- **Four fields were bound to a parameter of a different kind** — an exponent
  to a factor, a time ratio to a util/hour rate, a window dict to two scalar
  hours, a duration table with no clock format. The emitter found each by
  refusing to write it.
- **`0.75` was the S2b intervention.** "Full transit signal priority" removes
  75% of corridor signal delay, and that share sat as a bare literal in an
  arithmetic expression — a form no module-level constant scan can see.
  `A.lightrail.tsp_enabled` reached nothing while all ten scenario overlays set
  it. Both declared and wired.
- **The S1 and S3 alignments were 22 typed coordinates**, with the S3 list a
  copy of the S1 list. They are in `cities/<city>/geometry/`, and S3 is now
  expressed as which S1 stops it omits.
- **`make_bus_shuttle(speed_kmh=28.0, dwell_s=15.0)` were dead defaults** — the
  S1 call site passed 26.0 and 18.0.
- ⚠ **ONE MODEL VALUE CHANGED.** The network builder held a second copy of the
  road class defaults which had **drifted on six classes in both directions**
  (motorway 100 v 110, trunk 80 v 60, plus three links and `service`). One copy
  now, taking the declared speed. **The next network build changes on those six
  classes** — expected, and #32 rebuilds it anyway.
- **CI had been failing since the city restructure**: the provenance job tested
  `docs/DECISIONS.md`, which moved to `cities/<city>/docs/`.

---

═══════════════════════════════════════════════════════════════════════════════
§3  THE CHECKLIST — what is done, what is not
═══════════════════════════════════════════════════════════════════════════════

| Phase | State | Not done |
|---|---|---|
| **P0** Scoping | ✅ complete | — |
| **P1** Data acquisition | 🟡 substantially complete | Field dwell never measured. SCATS **refused by policy**, journey-linked Opal unpublished — both swept, never pinned. **10 OSM layers absent** pending #32 |
| **P2** Network build | 🟡 complete, **will be redone** | Corridor kerbside 95% imputed, lane width 98.6%, capacity 100%. #32 rebuilds all of it |
| **P3** Demand synthesis | 🟡 complete, **will be superseded** | Tour structure assumed (HTS held is aggregate). ~5 min to rebuild — which is why B0 batches everything touching B2 |
| **P4** Calibration | 🟡 **7 of 9 deliverables** | see below |
| **P5** Scenario runs | ⬜ not started | ⚠ **~765 days of wall clock as specified.** Grid cut 140 → 28; `n_replications` stays 30 until seed variance is MEASURED |
| **P6** Analysis | ⬜ not started | **Hypothesis B1 has NO OBSERVABLE AT ALL** without pedestrian counts |
| **P7** Write-up | ⬜ not started | — |

### P4 deliverables

| # | Deliverable | State |
|---|---|---|
| 0 | **Specification + input completeness** — gates 5 | ⬜ **not started.** §2 is now part of it |
| 1 | Run harness | ✅ done |
| 2 | Metric extraction | ✅ done |
| 3 | Fit statistic (10 tests) | ✅ done |
| 4 | Calibration loop | ✅ done |
| **5** | **Calibrated base + parameter provenance** | ❌ **NOT MET** — blocked by 0 and by a modelling decision (#14) |
| 6 | Calibration report generator | ✅ done |
| 7 | MATSim↔SUMO outer-loop tolerance = 5 s | ✅ done |
| 8 | Transfer-penalty estimate | ✅ met by its own fallback (§9.32) — not possible from this package, reason recorded, 3–15 min sweep stands |
| 9 | Live run view | ✅ done **and now actually wired** — see below |

### Landed since the last brief

- **The city restructure is committed.** `config/schema/` portable; `cities/<city>/`
  is one city's everything; `src/city.py` is the only module that knows where a
  city lives. Repo root is `README.md` and `run.py`.
- **The live view is wired into the harness.** It had been rebuilt but never
  re-connected: `RUN.monitor.enabled`, `.port` and `.poll_s` **reached nothing**.
  Every run now prints its own url before MATSim starts. Verified end-to-end.
- **A Windows-only bind bug is fixed.** `allow_reuse_address` was set on
  `socketserver.TCPServer` itself; on Windows that permits binding an already-bound
  port, so three concurrent views all took 8731 and **two served nothing while
  reporting a url**. Also changed the default for every other server in the process.
- **The relaxation verdict is declared, not typed.** `DRIFT_THRESHOLD_PP = 0.5`
  in `summarise_run.py` is now `RUN.relaxation.drift_tolerance_pp` with an
  interval sweep. The view shows a red/green light with **the two iteration
  numbers the drift was measured between** — "settled" says nothing without the
  window. The live view and the finished summary now call the **same function**;
  the view previously had a second implementation in different units.
- **`build_params.py` could never have run.** It called `_city.path('params')`
  since the restructure without importing `city` — fails no compile, no manifest
  check, dies on its first statement. Found by an AST check for names read and
  never bound.
- **`hts_trip_rates()` deleted.** It fed B2 until commit `529b626` and had opened
  HTS files for nothing since, keeping a whole stratum of the superseded activity
  model alive (`HTS_PURPOSE_MAP`, `PURPOSES`, `DEPART`, a literal `ACT_DURATION`).
- **Housekeeping**: 22 dead imports, 16 files repointed from the deleted
  `config/registry/<city>/`, 8 superseded + 3 crash-interrupted runs deleted
  (27.8 GiB).

---

═══════════════════════════════════════════════════════════════════════════════
§4  THE WORK QUEUE
═══════════════════════════════════════════════════════════════════════════════

**H0 is new and it is first, because it is cheap, it is the user's stated
priority, and B0 regenerates the run inputs anyway — so do H0 *with* B0 and pay
the regeneration cost once.**

| Order | Task | Issue | Effort | Notes |
|---|---|---|---|---|
| ~~H0.1–H0.5~~ | **DONE 15 Aug.** Ledger 185 → **0**; `--strict` gates CI | — | took ~1 day | The config is BUILT from the registry, so the literals have nowhere to live. 69 of 69 bound fields **proven** to reach by changing them. See §2 |
| **H0.6** | **Delete the dead pilot** | — | minutes | `results/conv1000_25pct_postrestructure/` has no `_run.json`. Delete it and its timing series together. LEFT IN PLACE deliberately: deleting a run directory is irreversible and was not explicitly authorised |
| **H0.9** | Rebuild the scenario GTFS feeds | **#32** | ~1 h | BLOCKED: `networks/osm/footways.osm` is absent, so `build_scenario_schedules.py` cannot run. The rewiring was proved value-neutral against git instead - 23 values and every coordinate identical - but the feeds have not been rebuilt from the declarations |
| **H0.7** | Derive `E.s2b.lr_segment_count` from the mapped feed | — | ~1 h | It is declared at 5.0 and the feed knows its own segment count. If they disagree, S2b removes the wrong TOTAL delay |
| **H0.8** | Derive the JHH anchor from the OSM POI | #32 | ~1 h | `cities/newcastle/geometry/scenario_alignments.json` says so itself. Needs the re-harvest |
| **B0.1** | Re-run the OSM harvest | **#32** | hours | `python cities/newcastle/extract/overpass.py`. Resumes from cached tiles |
| **B0.2** | Rebuild the layer chain | #32 | ~a day | `build_network_layers` → `attach_gradient` → `attach_speed_zones` → `build_corridor_road_attributes` → `build_matsim_network` → `build_landuse_parking` → `build_zone_attractions` |
| **B0.3** | **VERIFY before building on it** | #32 | ~1 h | Every layer **LARGER** than its `osm_pre_issue32/` counterpart; `osm_tiles.verify()` passes; **the 87 core SA1s / 31,940 agents are now INSIDE the road network** — check explicitly, it is the whole point |
| **B1** | Destination placement | **#30** | days — **DIAGNOSE FIRST** | Gravity distance matches HTS on all six purposes, yet education is 2.19× too long and B2 plans 10.80 km against 6.33 km realised for car. Destination choice is not in replanning so they should agree. **NOBODY HAS CHASED THIS.** Target: 4.9% of trips under 1 km → ~11.5% |
| **B2** | Bike availability | **#29** | ~1 day | Draw a household bike count from NCPS; gate to 0 for the youngest band **ON PHYSICAL GROUNDS ONLY**. **NEVER age-grade from participation data.** Austroads is COPYRIGHT: cite, do not redistribute |
| **B3** | Freight + boundary traffic | **#24**, **#20** | days | SFM22, SA3 geography, 2026 is a column. XLSB **double-mislabelled** as XLSX. **ROW 30001 IS AN UNLABELLED GRAND TOTAL** — drop it or everything doubles. **COAL IS 89% RAIL**: the port contributes ZERO trucks to Hunter Street. SFM22 road tonnage is a LOWER BOUND (26,156 kt vs ABS 9223.0's 53,926 kt). Commodity→vehicle crosswalk **DOES NOT EXIST** — assume and sweep |
| **B4** | The 30-hour day | **#37** | hours | 348 agents have a trip at 02:00 AND at 26:00. It is in the SEED (25,210 late departures at iteration 0, flat across 30), not replanning. 0.66% of agents |
| **B5** | Ride constraint | **#31** | ~1 day + a decision | eqasim's `PassengerConstraint` is a TRIP-LEVEL biconditional on `getInitialMode()`; no driver is consulted. Adopting it **PINS THE RIDE SHARE TO THE B2 SEED**. ⚠ **DO NOT ADD `ride` TO chainBasedModes.** ⚠ **Its mode string is `car_passenger`, HARD-CODED** — a copied constraint compiles, runs, constrains nothing and reports success |
| **GATE** | `check_hardcoding --strict` · `check_package` · diff resolved configs · regenerate all 30 run-input sets | — | ~1 h | |
| **C1** | Re-measure the iteration count | **#5** | ~13 h | Only meaningful AFTER the batch |
| **C2** | #28 residual | **#28** | ~1 day | ride vs car **IN MATCHED DISTANCE BINS**. Aggregate means are confounded by trip-length composition; that mistake produced a withdrawn headline once |
| **C3** | Calibrated base | **#14** | weeks | Deliverable 5. §8.5's first branch: estimate ASCs on era 3 (2018) and HOLD FIXED. **LOG THE DEPARTURE BEFORE ANY RUN** |
| **C4** | Re-solve `asc_car_passenger` | **#9** | hours | After C1 settles the horizon |
| **D1** | The fifth rectangle | **#34** | ~1 day | **DELIBERATELY DEFERRED** — moves a pre-registered B1 denominator. **MEASURE THE DAMAGE FIRST** |

---

═══════════════════════════════════════════════════════════════════════════════
§5  WHAT IT ACTUALLY DOES TODAY
═══════════════════════════════════════════════════════════════════════════════

| Layer | What runs | Fidelity |
|---|---|---|
| **Population** | 612,680 synthetic agents from 2021 Census marginals over 1,500 core SA1s; 521,502 weekday persons | Marginals matched; joint distribution synthesised |
| **Demand** | B2 activity chains as tours, 3 day types | Tour structure **assumed** — HTS held is aggregate tables |
| **Network** | MATSim: 157,678 links / 73,227 nodes / 23,212 km, EPSG:28356, gradients, TfNSW regulated speed zones, 1,240 turn restrictions | Observed from OSM + the legal speed instrument |
| **Transit** | 15 mapped GTFS feeds, **0 stops unmapped**, artificial link share 0.4–0.6% | Real timetables. **Trams and buses traverse congested links** |
| **Mode choice** | car, ride, pt, bike, walk; MATSim scoring, ASCs, VOT by purpose, transfer penalty swept 3–15 min | Utility-based, **uncalibrated** |
| **Parking** | Priced from the city's own job density, charged **car only**, home exempt | Reaches the model — verified by changing the value |
| **Corridor** | SUMO: 4 nets × 15,666 edges / 211 traffic lights, left-hand | **Built six times, simulated zero times, deliberately** |
| **Instrumentation** | `RunTelemetry` publishes per-mode and per-vehicle-type counts, per-link delay, stuck agents from **inside the mobsim** | Live view per run, own port, url printed at start |

**Day window is 30 hours** (`qsim.endTime=30:00:00`) so a 23:30 departure can
arrive. Correct and stays; only the wrap (#37) is a defect.

**Measured this session, confirming §9's warning:** at 1% **1,028 car agents
stuck** against **7** at 10% (of 554,825 legs). The 1% arm's car behaviour is
contaminated by spurious spillback exactly as documented.

**Also unremarked and worth someone's attention:** the 10% arm showed ~1,125
walk and ~416 pt agents stuck per iteration, car clean. That is **a different
quantity** from #37's 348 agents — do not conflate them.

---

═══════════════════════════════════════════════════════════════════════════════
§6  HOW CLOSE IS THIS TO REAL? — an honest reading
═══════════════════════════════════════════════════════════════════════════════

**Inputs: strong. Behaviour: unvalidated. Verdict: not yet a credible predictor,
and it is one calibrated base away from being an interesting one.**

- **Physical realism** — high. Real geometry, gradients, the *legal* speed
  instrument, real timetables, 0 unmapped stops, transit that feels congestion.
- **Behavioural realism** — **low**. Four known structural defects, two of them
  near-exact inversions. Uncalibrated.
- **Convergence** — **unknown**. No run has ever reached relaxation. This is #5.
- **Validation** — **none**. 210 targets, pre-registered 67/143. The holdout
  opens **once**, at the end.

**The two inversions, both specification defects on data already held:**

| Defect | Size | Cause |
|---|---|---|
| car −26.5 / ride +29.4 | ~26 pp | ride is routed on the network but **not simulated in it** — a passenger realises 55.7 km/h against car's 49.3 and arrives **13% faster than the car carrying them** (#28) |
| walk −12.7 / bike +12.7 | ~13 pp | bike ownership is **silently universal** (#29); walk's deficit may be trip lengths (#30) |

**Not one needs a byte of new data.**

**The number that sets expectations.** AToM Melbourne (MATSim, also 10%):
driving 74.8 vs 75.2 observed, PT 21.5 vs 19.3, walk 2.1 vs 3.7, cycle 1.6 vs
1.7 — 1–2 points per mode. **Active modes fit worst there too.** This model's
total absolute mode-share deviation was **33.8 pp at 1000 iterations pre-fix and
44.6 pp at 250 post-fix** (§9.27). **Do not read those as the model's quality;
read them as the distance still to cover.**

**What is worth protecting.** **1.82% of transport simulation studies publish a
repository at all.** This package is seeded, digest-pinned, hash-manifested and
provenance-tagged per file. And there is **no published ex-post counterfactual
microsimulation of a light rail line's effect on car traffic AND street activity
in any city** — that gap is the contribution.

---

═══════════════════════════════════════════════════════════════════════════════
§7  EXACT STATE — 15 August 2026
═══════════════════════════════════════════════════════════════════════════════

```
branch praneetdhoolia/mode-choice-specification
README.md  run.py            the only two things at the repo root
config/schema/               the portable contract
src/                         city.py · build · run · calibrate · analyse · registry · java/citysim
cities/newcastle/            registry overlays extract build geometry docs
                             data networks schedules demand scenarios params
```

| | |
|---|---|
| City selector | `CITYSIM_CITY` (default `newcastle`) |
| Java entry point | `citysim.CitysimControler` |
| Metrics key | `target_lga_pct` — **breaks run records older than the restructure** |
| `cities/newcastle/networks/osm/` | **EMPTY.** #32 re-harvest never run |
| `osm_pre_issue32/` | 10 layers, 179 MB, **THE ONLY COPY. DO NOT DELETE** |
| Manifest | **376 files**, city-relative paths |
| Registry | **292 fields** — 122 assumed, 85 definition, 35 literature, 25 derived, 21 measured, 4 observed; **15 carry no value** and the resolver refuses to invent one; 271 active, 10 computed, 6 unobtained, 5 placeholder |
| Hardcoding ledger | **0 items**, `--strict` gates CI. Honest baseline was 185 |
| Run inputs | 30 scenario × day-type sets, all carrying `telemetry` |
| `results/` | the 25% pilot DIED at iteration 43/1000 and must be deleted |
| Open issues | **13** — #5 #9 #14 #20 #24 #28 #29 #30 #31 #32 #34 #36 #37. **#36 IS OPEN** |
| **Results** | **NONE. Nothing in this repository is an output of the model.** |

### Bootstrap, in this order

```
cities/newcastle/docs/STATUS.md      the board
cities/newcastle/docs/DECISIONS.md   START AT ITS "How to find something" INDEX
                                     4,400+ lines, sections NOT in file order
.claude/CLAUDE.md                    conventions + hard constraints
docs/README.md                       the framework and the portable contract
cities/newcastle/docs/audit/SPEC_AUDIT.md   where the logic can be silently wrong

python src/registry/check_hardcoding.py        the ledger
python tests/check_manifest.py                 fast, committed subset
python src/registry/check_city.py              the city contract gate
python src/registry/render_schema.py --check   the contract is not stale
python src/registry/check_legacy_drift.py      pinned duplicate constants
python tests/check_package.py                  full local package
```

**DO NOT RE-READ THE P1–P3 PACKAGE.** 376 files hashed in the manifest.

**`check_package.py` has exactly ONE failure and it pre-dates everything:** the
registry claims `TelemetryConfigGroup.java` consumes
`RUN.telemetry.live_interval_s`; the Java spells it `liveIntervalS` and never
mentions the key. A provenance decision, left rather than quietly deleted.
**It is itself a §2 item** — fix it by wiring the key, not by deleting the claim.

---

═══════════════════════════════════════════════════════════════════════════════
§8  ★ THE SIGNATURE TRAP — ELEVEN INSTANCES AND COUNTING
═══════════════════════════════════════════════════════════════════════════════

**A DECLARED VALUE THAT REACHES NOTHING, OR A DEFAULT THAT IS RIGHT BY ACCIDENT.**
- Parking price declared since P1, read by NO script — a car parked free in a
  study about city-centre access.
- `params/C1` was a hand-kept mirror: 26 values, including every mode constant
  and THE transfer penalty, reached nothing. Setting one through the resolver
  left the output BYTE-IDENTICAL.
- Gradient penalties and PT walk-access decay reach the model through nothing.
- The summariser read a registry key that DOES NOT EXIST and fell back to a
  hard-coded 0.8 — the shipped value, so it was right for the wrong reason.
- Four scripts assigned a bare directory name as a path (`OUT = 'schedules'`).
  One wrote **32 MB of rebuilt GTFS into the repository root**. `check_city.py`
  now fails on the class, verified by reintroducing the defect and watching it
  go red.
- **NEW:** the live view's four `RUN.monitor.*` fields reached nothing — the view
  was rebuilt and never re-wired, and the code said so in a comment nobody acted on.
- **NEW:** `DRIFT_THRESHOLD_PP = 0.5` decided whether a run was reported settled
  — the verdict issue #5 turns on — from a constant in a script.
- **NEW:** `RUN.replanning.weights` and the innovation cutoff, §2.1.
- **NEW:** `build_params.py` used `_city` without importing it. Compiles, passes
  the manifest check, dies on its first statement.

**AND: THE AVAILABLE NUMBER LOOKS LIKE THE ANSWER AND IS A DIFFERENT QUANTITY.**
- `fee=yes` on 472 parking facilities → 452 are ONE university campus.
- Published interchange TIME ≠ transfer PENALTY (MATSim already simulates the
  walk and wait; the penalty sits ON TOP of a measured 112 s walk).
- OSM `width` on a road = CARRIAGEWAY (6.5 m), not a lane (3.5 m).
- 4,861 parking "capacities" — 4,623 are `1`, because they are BAYS.
- `build_basemap` dropped every segment >327 m, so the LGA boundary shattered and
  the map rendered as ocean — while looking like a normal dark map.
- **NEW:** `c1['weights']` (behavioural betas) vs `RUN.replanning.weights`
  (strategy weights). Same word, different quantity, adjacent lines.
- **NEW:** stuck **walk/pt** agents (~1,500/iteration) are not #37's 348 agents.

**NONE was caught by reading code. ALL were caught by ARITHMETIC or an audit.**

---

═══════════════════════════════════════════════════════════════════════════════
§9  WHAT INVALIDATES RESULTS
═══════════════════════════════════════════════════════════════════════════════

**NO RUN AT 250 ITERATIONS MEANS ANYTHING.** `RUN.controler.last_iteration` STAYS
`unobtained`. Re-measure AFTER the demand batch.

**1% IS NOT A CHEAP SUBSTITUTE FOR 10%.** MATSim floors link storage at one
vehicle, so 1% produces spurious spillback that inflates car delay while
teleported modes are immune. **Re-measured this session: car stuck 1,028 at 1% vs
7 at 10%.** **CROSS-FRACTION COMPARISON IS INVALID.**

**MODE-SHARE TARGET IS THE HTS LGA SERIES** (59.0 / 20.6 / 13.4 / 3.8 / 3.2). Use
`target_lga_pct`, NEVER `all_residents_pct` — it has inverted a headline.

**THE 67/143 SPLIT IS PRE-REGISTERED.** Never calibrate on, re-split, or peek at a
holdout row. `fit.py` enforces it. If you need one to diagnose: SAY SO AND STOP.

**ONE BUILD OF THE NETWORK PER COMPARISON** (§3.5): ~18% of route link sequences
differ between identical pt2matsim builds.

**`modestats.csv` ≠ `_metrics.json`.** One is the mode agents CHOSE, the other
trips that COMPLETED. Never report from modestats.

**A RUN WITHOUT `_run.json` IS NOT A RESULT.** Delete it, and delete its timing
series with it.

---

═══════════════════════════════════════════════════════════════════════════════
§10  DECISIONS TAKEN — do not re-litigate
═══════════════════════════════════════════════════════════════════════════════
• PRE-TRAM SIGNAL COUNT STAYS AT 14.
• OWN REALTIME COLLECTION DROPPED (#26): TfNSW's archive covers Metro and Ferry ONLY.
• SCATS REFUSED BY POLICY and citable. Main Roads WA publishes phasing; Utah DOT
  open-sourced ATSPM on 88% of 2,085 signals. **That contrast IS the method note.**
• FREIGHT IS THE PROPER SFM22 PATH. Licence conflict: USER IS HANDLING IT.
• GRID 140 → 28. `n_replications` STAYS 30 until seed variance is MEASURED.
• PARKING MAX-STAY DOUBLES AS THE CHARGE CAP; it UNDER-charges a long stay.
• DELIVERABLE 5 TAKES §8.5's FIRST BRANCH: ASCs on era 3 (2018), HELD FIXED.
  **LOG THE DEPARTURE BEFORE ANY RUN.**
• The parking ramp prices Kotara/Glendale/Charlestown at CBD rates. The contiguity
  fix was BUILT AND REJECTED — it also excludes the University and John Hunter
  Hospital, which DO charge.
• #34 DELIBERATELY DEFERRED. The 30 h qsim window is CORRECT and stays.
• **The city restructure is settled.** Do not move anything back.
• **The three-arm pilot is settled: run ONE arm at a time.**

### DECLINED — do not re-raise
• The 143 held-back targets stay untouched. They open ONCE, at the end.
• The 13 Opal card-type targets are not deleted.
• No separate taxi / motorcycle / rideshare modes (no target exists).
• Weather is NOT modelled in mode choice — a wet-day sensitivity ARM on
  `asc_cycle` weighted by the BoM rain-day fraction.
• Reclassifying the SUMO booleans / corridor buffers to `definition`. REVIEWED
  AND DECLINED — they each change a result.

---

═══════════════════════════════════════════════════════════════════════════════
§11  HARNESS TRAPS
═══════════════════════════════════════════════════════════════════════════════
1. **BASH HEREDOCS MANGLE BACKSLASH ESCAPES.** A trailing `\` or a `\n` inside a
   quoted heredoc breaks the string. Write code with the Write or Edit tool. It
   bit again this session. `io.open(p,'w')` TRUNCATES BEFORE THE WRITE FAILS —
   validate everything, stage it, then write.
2. `pkill` DOES NOT WORK HERE. Use PowerShell `Get-CimInstance` + `Stop-Process`,
   and VERIFY. **Avoid the literal `/1GB` in a PowerShell format string** — the
   sandbox reads it as a path and blocks the command.
3. **NORMALISE → MANIFEST**, and do it LAST.
4. NEVER compare across sample fractions. NEVER compare aggregate mean speeds
   across modes — **bin by distance first.**
5. NO COUNT-BASED CALIBRATION until #20 lands. `calibrate.py` enforces it.
6. Everything seeded **20260810**. Regenerate `CONFIG_REFERENCE.md` **and**
   `render_schema.py` after ANY registry edit, or the checks fail on staleness.
   **Adding one field made `layers.json` stale twice this session.**
7. WebSearch/WebFetch are NOT sandboxed; bash curl IS. WebFetch cannot read PDFs
   but DOES save them — then pdftotext locally.
8. **DO NOT TRUST A SEARCH SUMMARY.** Verify against the live API or the file.
9. Branch `<git-handle>/<short-kebab>`, never `claude/*`. No Claude attribution
   and no session link in commits or PRs. Commit messages state what changed in
   the MODEL or the DATA. Keep `STATUS.md` current in the SAME commit.
10. **A script that names a city directory relative to the working directory
    writes outside the city.** `check_city.py` fails on it — do not silence it.
11. **`compileall` does not catch a NameError.** A build script can compile,
    pass every check and die on its first statement. Check that names read are
    names bound.

---

═══════════════════════════════════════════════════════════════════════════════
§12  WORKING STYLE
═══════════════════════════════════════════════════════════════════════════════
1. **Inventory first.** Read the relevant files; state your understanding; flag
   contradictions, gaps and decisions.
2. **Plan, then get sign-off.** Wait for approval before writing files.
3. **Implement.** Only after approval. Prefer clear TODOs over speculative code.
4. **REPRODUCE A DEFECT BEFORE ATTRIBUTING IT.** And when you break something
   yourself, do not just fix it — write the check that would have caught it.
5. **CLOSE ISSUES AS YOU GO.** The bar is STRUCTURALLY PREVENTED, NOT REMEMBERED.
6. **NO INVENTED DATA.** If a value is not measured it is assumed or modelled,
   labelled as such in `source`, and recorded in `DECISIONS.md` with a rationale
   and a sweep range. **An unsupported number presented as observed is the one
   failure this project cannot absorb.**
7. **ZERO HARDCODING.** Before you commit: `python
   src/registry/check_hardcoding.py`. If your change added an item, it is not
   finished.
