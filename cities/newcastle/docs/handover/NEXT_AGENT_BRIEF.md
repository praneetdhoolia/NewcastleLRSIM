# Brief for the next agent — start a run before you read the rest

*Written 14 August 2026, after the city restructure. This is a HANDOVER, not a
source of truth: where it disagrees with [`STATUS.md`](../STATUS.md),
[`DECISIONS.md`](../DECISIONS.md) or [`.claude/CLAUDE.md`](../../../../.claude/CLAUDE.md),
those win. Paste it whole to start a session cold.*

---

═══════════════════════════════════════════════════════════════════════════════
§0  DO THIS FIRST — BEFORE READING ANYTHING BELOW
═══════════════════════════════════════════════════════════════════════════════

```bash
python src/setup/bootstrap_toolchain.py --verify     # ~1 min, COMPILES THE JAVA
python run.py --run-config convergence_pilot_10pct --tag conv1000_postrestructure
```

**~11.6 hours, 18.4 GiB, about 2.4 busy cores of 24.** Start it, then read this
document while it runs. It is the issue **#5** pilot: 1000 iterations at a 10%
sample, innovation off at 800, leaving 200 iterations of measurable
post-innovation drift per mode.

**WHAT THIS RUN IS.** A measurement of *how many iterations this model needs to
relax*. That is the single blocking unknown in the project:
`RUN.controler.last_iteration` is declared `unobtained` and the resolver refuses
to invent one, because **100 and 250 are both MEASURED to be too low** (§9.7,
§9.27). Measured: 100→250 moves a mode 13.2 points, 250→500 6.8, 500→800 3.0,
flat only from ~900.

**WHAT THIS RUN IS NOT.** It is not a result and no mode share, patronage, count
or fit statistic may be quoted from it. It runs on the **current demand**, which
the B0 batch (§4) will replace — destinations are too far (#30), bike ownership
is universal (#29), ride is not simulated in the network (#28), and freight and
boundary traffic are absent (#24, #20). Its **convergence behaviour** survives
those; its **mode shares do not**.

Two 10% runs fit in memory at once, not three. **PARALLELISE ACROSS RUNS, NEVER
THREADS WITHIN ONE.** `python src/run/prune_run.py --run results/<name>` after
every run, or the P5 sweep needs ~750 GB. An **untagged** re-run DELETES the old
directory — always `--tag`.

⚠ **Run records written before this session cannot be read.** The metrics key
`newcastle_lga_pct` is now `target_lga_pct`. This was accepted deliberately in
exchange for a city-agnostic output schema. The 8 runs in `results/` were
already superseded; do not try to salvage them.

---

═══════════════════════════════════════════════════════════════════════════════
§1  THE GOALS — there are two, and they now pull in the same direction
═══════════════════════════════════════════════════════════════════════════════

| # | Goal | What "done" looks like | State |
|---|---|---|---|
| **G1** | **Answer the counterfactual.** What did the Newcastle light rail do to journey cost, accessibility, mode share and city-centre footfall, against the alternatives available in 2013? | A calibrated base, S0–S6 run to relaxation, the 143 holdout targets opened once, and a findings paper that states its uncertainty bands | **Not started.** No scenario has been run to a reportable state |
| **G2** | **A city-agnostic simulator with a full input schema.** Any city supplies a declared input package and the framework runs unchanged | A second city built from `config/schema/` alone, with no framework edit | **Structurally in place, never exercised.** One city exists |

G1 exists because that estimate was never produced and the business case is not
inspectable. Every discipline in this repo — the sealed holdout, the declared
sweeps, the refusal to report a point value for an unobserved input — descends
from one fact: **9 of 10 rail projects overestimate patronage, by an average of
106%** (Flyvbjerg, 210 projects). A model of a rail project that produces a
flattering answer is the EXPECTED outcome, not a surprising one.

G2 was not an original goal. It became one because the repo kept producing the
same class of defect — a value typed into a script where nobody could see it —
and the only structural cure is a framework that cannot name a place.

---

═══════════════════════════════════════════════════════════════════════════════
§2  WHAT IT ACTUALLY DOES TODAY
═══════════════════════════════════════════════════════════════════════════════

**A regional agent-based demand model coupled to a corridor microsimulation.**

| Layer | What runs | Fidelity |
|---|---|---|
| **Population** | 612,680 synthetic agents from 2021 Census marginals over 1,500 core SA1s; 521,502 weekday persons | Marginals matched; joint distribution synthesised |
| **Demand** | B2 activity chains as tours, 3 day types, purpose/duration/departure drawn from NSW HTS aggregates | Tour structure **assumed** — the HTS held is aggregate tables, not unit records |
| **Network** | MATSim: 157,678 links / 73,227 nodes / 23,212 km, EPSG:28356, gradient-attached, TfNSW regulated speed zones, 1,240 turn restrictions | Observed from OSM + the legal speed instrument |
| **Transit** | 15 mapped GTFS feeds (5 eras + 10 scenario variants), **0 stops unmapped**, artificial link share 0.4–0.6% | Real timetables. **Trams and buses traverse congested links** — verified in the event stream |
| **Mode choice** | car, ride, pt, bike, walk; MATSim scoring with ASCs, VOT by purpose, transfer penalty swept 3–15 min | Utility-based, uncalibrated |
| **Parking** | Priced from the city's own job-density distribution, charged **car only** from arrival to next car departure via `PersonMoneyEvent`, home exempt | Reaches the model — verified by changing the value and watching the output |
| **Corridor** | SUMO: 4 nets × 15,666 edges / 211 traffic lights, left-hand traffic, A2 signal timings attached | **Built six times, simulated zero times, deliberately** |
| **Instrumentation** | `RunTelemetry` publishes per-mode and per-vehicle-type counts, per-link delay and stuck agents from **inside the mobsim**, in simulated-time order | Live view on loopback; structurally unable to stop a run |

**Day window is 30 hours** (`qsim.endTime=30:00:00`) so a 23:30 departure can
arrive. That is correct and stays; only the wrap (#37) is a defect.

---

═══════════════════════════════════════════════════════════════════════════════
§3  THE PHASES — P0 to P7, with tasks and measured durations
═══════════════════════════════════════════════════════════════════════════════

**Durations are wall clock on this machine (24 cores, 63.5 GiB).** "not
measured" means exactly that — do not substitute a guess.

| Phase | State | Tasks | Duration |
|---|---|---|---|
| **P0** Scoping | ✅ complete | Base year 2026, zone system, S0–S6 settled | — |
| **P1** Data acquisition | 🟡 substantially complete | OSM harvest (10 layers × 8 tiles) · GTFS eras · Opal/counts/HTS · ABS boundaries + census + DEM · clip zones/census/HTS/observed | harvest **hours** (504 timeouts, mirror rotation, resumes from cached tiles); clips minutes each |
| **P2** Network build | 🟡 complete, **will be redone** | `build_network_layers` · `attach_gradient` · `attach_speed_zones` · `build_corridor_road_attributes` · `build_matsim_network` (runs pt2matsim) · `build_sumo_corridor` | pt2matsim + SUMO: **not separately timed**; the whole B0 chain is a day's work including verification |
| **P3** Demand synthesis | 🟡 complete, **will be superseded** | `measure_network_factors` ~70 s · `build_population` ~30 s · `build_activity_chains` ~90 s (790 MB out) · `build_matsim_plans` ~45 s · `build_matsim_run_inputs` ~45 s | **~5 min total.** Cheap to redo — which is why B0 batches everything that touches B2 |
| **P4** Calibration | 🟡 **7 of 9 deliverables** | see §4 | dominated by run time, not code |
| **P5** Scenario runs | ⬜ not started | 10 scenarios × 3 day types × sweep grid × replications | ⚠ **~765 days of wall clock as specified.** Grid already cut 140 → 28; `n_replications` stays 30 until seed variance is MEASURED. **Cutting it further is a DEFENSIBILITY decision to be argued and recorded, not a scheduling one** |
| **P6** Analysis | ⬜ not started | Hypothesis tests A/B/C, accessibility, footfall | **Hypothesis B1 has NO OBSERVABLE AT ALL** without pedestrian counts |
| **P7** Write-up | ⬜ not started | Findings paper, method note on evaluation gaps | — |

### P4 deliverables — the current phase

| # | Deliverable | State | Effort remaining |
|---|---|---|---|
| 0 | **Specification + input completeness** — gates 5 | ⬜ **not started** | see §4; the batch is the work |
| 1 | Run harness | ✅ done | — |
| 2 | Metric extraction | ✅ done | — |
| 3 | Fit statistic (10 tests) | ✅ done | — |
| 4 | Calibration loop | ✅ done | — |
| 5 | **Calibrated base + parameter provenance** | ❌ **NOT MET** | blocked by deliverable 0 **and** by a modelling decision (#14) |
| 6 | Calibration report generator | ✅ done | — |
| 7 | MATSim↔SUMO outer-loop tolerance = 5 s | ✅ done | — |
| 8 | Transfer-penalty estimate | ✅ **met by its own fallback** (§9.32) — not possible from this package, reason recorded, 3–15 min sweep stands | — |
| 9 | Live run view | ✅ rebuilt | restore `check_package` coverage for it |

---

═══════════════════════════════════════════════════════════════════════════════
§4  THE WORK QUEUE — B0 IS THE POINT OF NO RETURN AND IT IS FIRST
═══════════════════════════════════════════════════════════════════════════════

**Everything below the B0 line invalidates every existing run** (it re-runs
pt2matsim; §3.5 — ~18% of route link sequences differ between identical builds,
so one build per comparison, always).

| Order | Task | Issue | Kind | Effort | Notes |
|---|---|---|---|---|---|
| **B0.1** | Re-run the OSM harvest | **#32** | data | hours | `python cities/newcastle/extract/overpass.py`. Resumes from cached tiles |
| **B0.2** | Rebuild the layer chain | #32 | processing | ~a day incl. verification | `build_network_layers` → `attach_gradient` → `attach_speed_zones` → `build_corridor_road_attributes` → `build_matsim_network` → `build_landuse_parking` → `build_zone_attractions` |
| **B0.3** | **VERIFY before building on it** | #32 | check | ~1 h | every layer **LARGER** than its `osm_pre_issue32/` counterpart; `osm_tiles.verify()` passes; **the 87 core SA1s / 31,940 agents are now INSIDE the road network** — check explicitly, it is the whole point |
| **B1** | Destination placement | **#30** | processing | days — **DIAGNOSE FIRST** | P3 stage 1 reports gravity distance matching HTS exactly on all six purposes, yet education is 2.19× too long and B2 plans 10.80 km against 6.33 km realised for car. Destination choice is not in replanning so they should agree. **NOBODY HAS CHASED THIS.** Target: 4.9% of trips under 1 km → ~11.5% |
| **B2** | Bike availability | **#29** | processing | ~1 day | Draw a household bike count from NCPS; gate to 0 for the youngest band **ON PHYSICAL GROUNDS ONLY**. **NEVER age-grade from participation data** — that is the absorption trap. Austroads is COPYRIGHT: cite, do not redistribute |
| **B3** | Freight + boundary traffic | **#24**, **#20** | data + processing | days | SFM22, SA3 geography, 2026 is a column. XLSB **double-mislabelled** as XLSX. **ROW 30001 IS AN UNLABELLED GRAND TOTAL** — drop it or everything doubles. **COAL IS 89% RAIL**: the port contributes ZERO trucks to Hunter Street. SFM22 road tonnage is a LOWER BOUND (26,156 kt vs ABS 9223.0's 53,926 kt). Commodity→vehicle crosswalk **DOES NOT EXIST** — assume and sweep |
| **B4** | The 30-hour day | **#37** | processing | hours | 348 agents have a trip at 02:00 AND at 26:00 in one day. It is in the SEED (25,210 late departures at iteration 0, flat across 30 iterations), not in replanning. B2 draws hours 0–23 correctly; nothing caps a chain at the 24 h boundary. 0.66% of agents |
| **B5** | Ride constraint | **#31** | **modelling decision** | ~1 day + a decision | eqasim's `PassengerConstraint` is a TRIP-LEVEL biconditional on `getInitialMode()`; no driver is consulted. Adopting it **PINS THE RIDE SHARE TO THE B2 SEED** — ride becomes an input wearing the costume of a result (§9.6). If taken, every result must state the car-passenger share is exogenous. ⚠ **DO NOT ADD `ride` TO chainBasedModes** — that is vehicle mass conservation, meaningless for a lift. ⚠ **If porting the eqasim class, its mode string is `car_passenger`, HARD-CODED** — a copied constraint compiles, runs, constrains nothing and reports success |
| **GATE** | `check_package` · diff resolved configs · regenerate all 30 run-input sets | — | check | ~1 h | |
| **C1** | Re-measure the iteration count | **#5** | run | **~11.6 h** | Only meaningful AFTER the batch — the batch moves the landscape |
| **C2** | #28 residual | **#28** | analysis | ~1 day | ride vs car **IN MATCHED DISTANCE BINS**. Aggregate means are confounded by trip-length composition; that mistake produced a withdrawn headline once |
| **C3** | Calibrated base | **#14** | decision + runs | weeks | Deliverable 5. Takes §8.5's first branch: estimate ASCs on era 3 (2018) and HOLD FIXED. **LOG THE DEPARTURE BEFORE ANY RUN** |
| **C4** | Re-solve `asc_car_passenger` | **#9** | run | hours | after C1 settles the horizon |
| **D1** | The fifth rectangle | **#34** | processing | ~1 day | **DELIBERATELY DEFERRED** — it moves a pre-registered B1 denominator. **MEASURE THE DAMAGE FIRST.** Now declared at its exact old value in `cities/newcastle/geometry/analysis_extents.json` |

**#36 is closed** — the `CITYSIM_*` prefix and `src/java/citysim/` landed with the
restructure.

---

═══════════════════════════════════════════════════════════════════════════════
§5  WHAT WOULD IMPROVE THE SIMULATOR MOST — processing, not data
═══════════════════════════════════════════════════════════════════════════════

**The answer is processing, by a wide margin, and it is not close.**

The specification audit found **two near-exact inversions**, and both are
specification defects on data already held:

| Defect | Size | Cause | Fix is |
|---|---|---|---|
| car −26.5 / ride +29.4 | ~26 pp | ride is routed on the network but **not simulated in it** — a passenger realises 55.7 km/h against car's 49.3 and arrives **13% faster than the car carrying them** (#28) | processing |
| walk −12.7 / bike +12.7 | ~13 pp | bike ownership is **silently universal** (#29); walk's deficit may be trip lengths, not scoring (#30) | processing |

**Not one of those needs a byte of new data.** For comparison, the three inputs
that are genuinely unobtainable are handled by sweep and bound the *uncertainty*
of a result, not its central estimate.

| Category | Items | Verdict |
|---|---|---|
| **Processing on data already held** | #28 ride simulation · #29 bike ownership · #30 destination placement · #31 ride constraint · #37 the 30-hour day · #34 the CBD box | **Do these first.** They are worth tens of percentage points of mode share |
| **Processing on data that is obtainable but unbuilt** | #20 boundary/through traffic (cordon counts, touches no holdout row) · #24 freight (SFM22 published) · `B.external.interaction_rate` (ABS journey-to-work SA2×SA2, a standard TableBuilder extract) · day-of-week split (RMS counts carry dates) | **Second.** Each adds demand and will move mode share, so calibrating before them means re-calibrating after |
| **Genuinely missing data, cheap to get** | Charging dwell — one field visit to Civic or Crown Street, worth 11% of corridor run time | **Third.** The GTFS-RT fallback is gone: TfNSW's historical archive covers Metro and Ferry only |
| **Genuinely missing data, blocks a hypothesis outright** | **Pedestrian counts** — none published for Newcastle, and **hypothesis B1 has no observable at all without them**. Retail floorspace/vacancy blocks B2 | **P6 blocker.** Temporary counters on Hunter St, or calibrate from land use and modelled alightings |
| **Refused / unpublished, handled by sweep** | SCATS phasing (refused by policy, citable) · journey-linked Opal (unpublished) | **Do not pin.** The refusal is itself a documented finding for the method note |

**Also worth doing, and cheap: 0b — derive what can be derived.** 89 of 210
registry fields are `assumed`. A realistic target is **15–25 moved to
measured/derived**, not 89: anything about tour structure is not derivable from
aggregate HTS tables. Candidates are listed in `STATUS.md` deliverable 0b.

---

═══════════════════════════════════════════════════════════════════════════════
§6  HOW CLOSE IS THIS TO A REAL-LIFE SIMULATION? — an honest reading
═══════════════════════════════════════════════════════════════════════════════

**Inputs: strong. Behaviour: unvalidated. Verdict: not yet a credible
predictor, and it is one calibrated base away from being an interesting one.**

| Dimension | Where it stands |
|---|---|
| **Physical realism** | High. Real network geometry, real gradients, the *legal* speed instrument rather than a mapper's transcription, real timetables, 0 unmapped stops, turn restrictions carried into the network, transit vehicles that feel congestion |
| **Population realism** | Moderate–high on marginals (census-matched), unknown on joint structure. Tour structure is assumed because the HTS held is aggregate |
| **Behavioural realism** | **Low, today.** Four known structural defects, two of them near-exact inversions. Uncalibrated |
| **Convergence** | **Unknown.** No run has reached relaxation. This is #5 and it is the reason §0 exists |
| **Validation** | **None yet.** 210 targets, pre-registered 67 calibration / 143 holdout. The holdout opens **once**, at the end. No calibrated base has ever been scored |
| **Corridor** | SUMO built and never simulated — deliberate. Deliverable 7 (5 s tolerance) is settled; the harness and outer loop are P5 |

**The number that sets expectations.** The benchmark is AToM Melbourne (MATSim,
also 10%): driving 74.8 vs 75.2 observed, PT 21.5 vs 19.3, walk 2.1 vs 3.7,
cycle 1.6 vs 1.7 — roughly 1–2 points per mode, and car counts under 25% WAPE in
peak. **Active modes fit worst there too**, which is why #29/#30 are the known
hard part. This model's total absolute mode-share deviation was **33.8 pp at
1000 iterations pre-fix and 44.6 pp at 250 post-fix** (§9.27) — one to two orders
of magnitude off the benchmark, on an uncalibrated model that has not relaxed.
**Do not read those as the model's quality; read them as the distance still to
cover.**

**What is genuinely unusual and worth protecting.** Reproducibility baseline in
this field: **1.82% of transport simulation studies publish a repository at
all**, ~5% by 2024. This package is seeded, pinned by digest, hash-manifested and
provenance-tagged per file. And there is **no published ex-post counterfactual
microsimulation of a light rail line's effect on car traffic AND street activity
in any city** — that gap is the contribution.

---

═══════════════════════════════════════════════════════════════════════════════
§7  EXACT STATE — 14 August 2026, after the city restructure
═══════════════════════════════════════════════════════════════════════════════

```
branch praneetdhoolia/mode-choice-specification   (uncommitted restructure in the tree)
```

**The layout changed. Every path in an older document is stale.**

```
README.md  run.py            the only two things at the repo root
docs/README.md               the FRAMEWORK's documentation
config/schema/               the portable contract: 5 documents + outputs/
src/                         city.py · build · run · calibrate · analyse · registry · java/citysim
cities/newcastle/            registry overlays extract build geometry docs
                             data networks schedules demand scenarios params
```

| | |
|---|---|
| City selector | `CITYSIM_CITY` (default `newcastle`) — was `WICKHAM_CITY` |
| Java entry point | `citysim.CitysimControler` — was `wickham.WickhamControler` |
| Metrics key | `target_lga_pct` — was `newcastle_lga_pct`. **Breaks older run records** |
| `cities/newcastle/networks/osm/` | **EMPTY.** #32 re-harvest never re-run |
| `osm_pre_issue32/` | 10 layers, 179 MB, **THE ONLY COPY** — now under generic names (`roads.osm`, …). **DO NOT DELETE** |
| Manifest | **376 files**, city-relative paths, unchanged in content across the whole restructure |
| Registry | **210 fields** — 89 assumed, 51 definition, 28 literature, 21 measured, 17 derived, 4 observed; **7 carry no value** |
| Run inputs | 30 scenario × day-type sets, all carrying `telemetry` |
| `results/` | 8 dirs, ~15 GB, **every one superseded and now unreadable by `fit.py`** |
| Open issues | **12** — #5 #9 #14 #20 #24 #28 #29 #30 #31 #32 #34 #37 |
| **Results** | **NONE. Nothing in this repository is an output of the model.** |

### Bootstrap, in this order

```
cities/newcastle/docs/STATUS.md         the board
cities/newcastle/docs/DECISIONS.md      START AT ITS "How to find something" INDEX
                                        4,400+ lines, sections NOT in file order (§15
                                        precedes §14), §9 holds unrelated topics.
                                        Then §0, §8.5, §9.12, §9.27, §9.36, §9.37, §15
.claude/CLAUDE.md                       conventions + hard constraints
docs/README.md                          the framework and the portable contract
cities/newcastle/docs/audit/SPEC_AUDIT.md   where the logic can be silently wrong

python tests/check_manifest.py                 fast, committed subset
python src/registry/check_city.py              the city contract gate
python src/registry/render_schema.py --check   the contract is not stale
python tests/check_package.py                  full local package
```

**DO NOT RE-READ THE P1–P3 PACKAGE.** 376 files hashed in
`cities/newcastle/data/MANIFEST.csv`.

**`check_package.py` has exactly ONE failure, and it pre-dates all of this:**
the registry claims `TelemetryConfigGroup.java` consumes
`RUN.telemetry.live_interval_s`; the Java spells it `liveIntervalS` and never
mentions the key. It is a provenance decision, left rather than quietly deleted.

---

═══════════════════════════════════════════════════════════════════════════════
§8  ★ THE TRAP THAT KEEPS WINNING — NOW NINE INSTANCES
═══════════════════════════════════════════════════════════════════════════════

**A DECLARED VALUE THAT REACHES NOTHING, OR A DEFAULT THAT IS RIGHT BY ACCIDENT.**
  • Parking price declared since P1, read by NO script — a car parked free in a
    study about city-centre access.
  • `params/C1` was a hand-kept mirror of the registry: 26 values, including every
    mode constant and THE transfer penalty, reached nothing. Setting one through
    the resolver left the output BYTE-IDENTICAL.
  • Gradient penalties and PT walk-access decay reach the model through nothing.
  • The summariser read a registry key that DOES NOT EXIST and fell back to a
    hard-coded 0.8 — the shipped value, so it was right for the wrong reason.
  • **NEW:** four scripts assigned a bare directory name as a path
    (`OUT = 'schedules'`). One wrote **32 MB of rebuilt GTFS into the repository
    root** instead of the city. The script succeeds, the manifest still passes,
    and the outputs are simply somewhere else. `check_city.py` now fails on the
    class — and the guard was verified by **reintroducing the defect and watching
    it go red**.

`consumers` in the registry is a claim, NOT proof. **Establish reach by CHANGING
A VALUE AND WATCHING THE OUTPUT.**

**AND: THE AVAILABLE NUMBER LOOKS LIKE THE ANSWER AND IS A DIFFERENT QUANTITY.**
  • `fee=yes` on 472 parking facilities → 452 are ONE university campus.
  • Published interchange TIME ≠ transfer PENALTY (MATSim already simulates the
    walk and wait; the penalty sits ON TOP of a measured 112 s walk).
  • OSM `width` on a road = CARRIAGEWAY (6.5 m), not a lane (3.5 m).
  • 4,861 parking "capacities" — 4,623 are `1`, because they are BAYS.
  • `build_basemap` dropped every segment >327 m, so the LGA boundary shattered
    and the map rendered as ocean — while looking like a normal dark map.

**NONE of these was caught by reading code. All were caught by ARITHMETIC.**

---

═══════════════════════════════════════════════════════════════════════════════
§9  READ FIRST — WHAT INVALIDATES RESULTS
═══════════════════════════════════════════════════════════════════════════════

**NO RUN AT 250 ITERATIONS MEANS ANYTHING.** `RUN.controler.last_iteration`
STAYS `unobtained`. Re-measure AFTER the demand batch.

**1% IS NOT A CHEAP SUBSTITUTE FOR 10%.** MATSim floors link storage at one
vehicle, so 1% produces spurious spillback that inflates car delay while
teleported modes are immune. Measured: car stuck 1,079 at 1% vs **1** at 10%.
**CROSS-FRACTION COMPARISON IS INVALID.**

**MODE-SHARE TARGET IS THE HTS LGA SERIES** (59.0 / 20.6 / 13.4 / 3.8 / 3.2).
Use `target_lga_pct`, NEVER `all_residents_pct` — it has inverted a headline.

**THE 67/143 SPLIT IS PRE-REGISTERED.** Never calibrate on, re-split, or peek at
a holdout row. `fit.py` enforces it. If you need one to diagnose: SAY SO AND STOP.

**ONE BUILD OF THE NETWORK PER COMPARISON** (§3.5).

**`modestats.csv` ≠ `_metrics.json`.** One is the mode agents CHOSE, the other
trips that COMPLETED. Never report from modestats.

---

═══════════════════════════════════════════════════════════════════════════════
§10  DECISIONS ALREADY TAKEN — do not re-litigate
═══════════════════════════════════════════════════════════════════════════════
• PRE-TRAM SIGNAL COUNT STAYS AT 14 (8 of the 14 were installed in 2018 for the
  light rail; recorded as an attribute only).
• OWN REALTIME COLLECTION DROPPED (#26): TfNSW's archive covers Metro and Ferry
  ONLY, verified against the live API.
• SCATS REFUSED BY POLICY and citable. Main Roads WA publishes phasing; Utah DOT
  open-sourced ATSPM on 88% of 2,085 signals. **That contrast IS the method note.**
• FREIGHT IS THE PROPER SFM22 PATH. Licence conflict: USER IS HANDLING IT.
• GRID 140 → 28. `n_replications` STAYS 30 until seed variance is MEASURED.
• PARKING MAX-STAY DOUBLES AS THE CHARGE CAP; it UNDER-charges a long stay.
• DELIVERABLE 5 TAKES §8.5's FIRST BRANCH: estimate ASCs on era 3 (2018) and HOLD
  FIXED. **LOG THE DEPARTURE BEFORE ANY RUN.**
• The parking ramp prices Kotara/Glendale/Charlestown at CBD rates where parking
  is free. The contiguity fix was BUILT AND REJECTED — it also excludes the
  University and John Hunter Hospital, which DO charge.
• #34 DELIBERATELY DEFERRED — it moves a pre-registered B1 denominator.
• The 30 h qsim window is CORRECT and stays. Only the wrap (#37) is a defect.
• **The city restructure (§9.37) is settled.** Do not move anything back.

### DECLINED — do not re-raise
• The 143 held-back targets stay untouched. They open ONCE, at the end.
• The 13 Opal card-type targets are not deleted.
• No separate taxi / motorcycle / rideshare modes (no target exists).
• Weather is NOT modelled in mode choice — represent it as a wet-day sensitivity
  ARM on `asc_cycle` weighted by the BoM rain-day fraction.
• Reclassifying the SUMO booleans / corridor buffers to `definition`. REVIEWED
  AND DECLINED — they each change a result.

---

═══════════════════════════════════════════════════════════════════════════════
§11  TRAPS (harness)
═══════════════════════════════════════════════════════════════════════════════
1. **BASH HEREDOCS MANGLE BACKSLASH ESCAPES.** `\n` inside a quoted heredoc
   becomes a literal newline and breaks JS/Python strings. It bit **four more
   times** this session. Write prose/code with the Write or Edit tool.
   `io.open(p,'w')` TRUNCATES BEFORE THE WRITE FAILS — validate, then write.
2. `pkill` DOES NOT WORK RELIABLY HERE. Use PowerShell `Get-CimInstance` +
   `Stop-Process`, and VERIFY.
3. **NORMALISE → MANIFEST**, and do it LAST.
4. NEVER compare across sample fractions. NEVER compare aggregate mean speeds
   across modes — bin by distance first.
5. NO COUNT-BASED CALIBRATION until #20 lands. `calibrate.py` enforces it.
6. Everything seeded **20260810**. Regenerate `CONFIG_REFERENCE.md` AND
   `render_schema.py` after ANY registry edit, or the checks fail on staleness.
7. WebSearch/WebFetch are NOT sandboxed; bash curl IS. WebFetch cannot read PDFs
   but DOES save them — then pdftotext locally.
8. **DO NOT TRUST A SEARCH SUMMARY.** Verify against the live API or the file.
9. Branch `<git-handle>/<short-kebab>`, never `claude/*`. No Claude attribution
   and no session link in commits or PRs. Commit messages state what changed in
   the MODEL or the DATA. Keep `STATUS.md` current in the SAME commit.
10. **A script that names a city directory relative to the working directory
    writes outside the city.** `check_city.py` fails on it — do not silence it.

---

═══════════════════════════════════════════════════════════════════════════════
§12  WORKING STYLE
═══════════════════════════════════════════════════════════════════════════════
1. **Inventory first.** Read the relevant files; state your understanding; flag
   contradictions, gaps and decisions.
2. **Plan, then get sign-off.** Wait for approval before writing files.
3. **Implement.** Only after approval. Prefer clear TODOs over speculative code.
4. **REPRODUCE A DEFECT BEFORE ATTRIBUTING IT.**
5. **CLOSE ISSUES AS YOU GO.** The bar is STRUCTURALLY PREVENTED, NOT REMEMBERED.
6. **NO INVENTED DATA.** If a value is not measured it is assumed or modelled,
   labelled as such in `source`, and recorded in `DECISIONS.md` with a rationale
   and a sweep range. **An unsupported number presented as observed is the one
   failure this project cannot absorb.**
