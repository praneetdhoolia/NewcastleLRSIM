# STATUS — NewcastleLRSIM

Single source of truth for **where the build is, what's next, and how to resume**. Read
this at session start. **Keep it current in the same commit/PR as the work it describes**
— if a change makes a line here wrong, fix the line in that change, not later.

**Last updated:** 20 August 2026 (three changes this session, in order: **freight is PHYSICAL** — §9.49, issue #24, PR #46: a `truck` mode at declared PCE, smoke-verified, a planned comparability break; **the calibrated base takes §8.5's constrain-and-report branch, logged before its run's results** — §9.50, PR #47 — and its base arm was then **STOPPED by the owner at ~iteration 20** and quarantined, so deliverable 5 stays open; **four owner directives reset the value order** — §9.51, issues #48/#49/#50 and re-opened #30: physical ride, 9+ modes individualised, the sub-1 km walk deficit, demographic-conditional mode fidelity. Active lane: **research the §9.51 directives — #48 first — and decide sequencing against the base-arm relaunch**) · branch `praneetdhoolia/calibration-constrained-base` (PR stack #46 ← #47 ← handover)

> **This file is a board, not a diary.** The dated build narrative that used to live
> here (944 lines) is archived in
> [`docs/handover/SESSION_LOG.md`](handover/SESSION_LOG.md). Its authoritative
> version is [`DECISIONS.md`](DECISIONS.md) §9.1–§9.36. **Do not append a session
> narrative here again** — record the decision in `DECISIONS.md` and update the board
> lines below that it makes wrong.

---

## ✅ The rebuild batch (4.1) is DONE — the point of no return was crossed 16 August

The issue #32 re-harvest ran to completion over the boundary-derived extent
(2.02× the old rectangle) and the whole chain was rebuilt on it in one batch:
network layers, gradients (DEM tile set now **derived** from the boundary —
100% coverage), speed zones, corridor attributes, scenario GTFS feeds, one
pt2matsim build of **all 15 feeds (0 unmapped stops each)**, land use, parking
prices, attractions, B2 demand with the five demand fixes, MATSim plans, and
the 30 run-input sets. `tests/check_package.py`: **1,456 checks, ALL PASSED**,
2 standing warnings. Verified gates: every OSM layer larger than its
`osm_pre_issue32/` counterpart; core SA1s without a road node **99 → 4, with 0
agents in them** (all 35,365 stranded agents are on the network); network link
speeds agree with `A1_road_edges.csv`. **Every run made before this batch is
incomparable with every run after it** ([`DECISIONS.md`](DECISIONS.md) §3.5) —
which is why `results/` was already empty when it landed.
`networks/osm_pre_issue32/` remains the pre-repair reference copy.

## Where the build is

| | |
|---|---|
| Phase | **P4 (calibration), in progress** — 7 of 9 deliverables met; batch 4.1 (the rebuild) **done 16 Aug** |
| Blocking state | **None mechanical; the lane is a decision-and-research lane.** Freight LANDED (§9.49). The §8.5 branch is DECIDED and logged (§9.50) but its base arm was **stopped by the owner** — C5/report await a relaunch (~35 h, needs approval). **Active lane: the four §9.51 owner directives, #48 (physical ride) first** — each is research-then-owner-decision before any build; #48 in particular must confront the recorded ~10× socnetsim cost and the 26.2% lone-person-household fact. Sequencing question to settle first: directives will change the demand family again, so relaunching the base arm before them buys a family that #48/#49 would immediately break |
| Committed data package | **423 files** in [`data/MANIFEST.csv`](../data/MANIFEST.csv) (§9.49 added the two measured freight-profile artefacts and the 30 per-set `vehicles.xml`) · `check_manifest.py` passes · `check_package.py` **1,466 checks ALL PASSED** (2 standing warnings) |
| Input registry | **319 fields** (§9.49 added six `B.freight.*` + `RUN.qsim.car_vehicle`; §9.52 added three `B.motorbike.*`) — every one with units, provenance and a sweep, held-fixed rule or derived identity; ledger **0** with `--strict` gating CI; reach **74/74** |
| Run inputs assembled | **30** scenario × day-type sets, **regenerated 20 Aug** on the §9.49 freight demand; each config carries `ridePairing`, `qsim.mainMode = car,truck` and an explicit per-mode vehicles file the harness re-emits per run |
| What is PHYSICALLY simulated (measured 20 Aug, §9.49/§9.52) | **7 of 9+ modes in the mobsim**: `car`; **`truck`** at PCE 2.0 (swept 1.5–3.5), 100 km/h cap — smoke: 913 trips / 140,380 traversals at 1%; **`motorbike`** at PCE 0.4 (swept 0.3–0.75), carved from car on the measured G62 anchor — smoke: 12 riders / 52 trips / 6,286 traversals at 1%; **bus** 1,448 vehicles at PCE 2.8 on **22,102 shared road links**; **rail** 332; **tram** 252 (21 on-street links); **ferry** 107. **`ride` is PAIRED but still teleported** (§9.44 — #48 ends this). Taxi/rideshare not a mode (4.4/#49 tier plan) |
| **Ride pairability — the repair is MEASURED to work (§9.48)** | Pre-repair, **0.10% (25%) and 0.04% (10%) of ride trips shared an origin–destination pair with a household car trip at any time**. Both causes were fixed (§9.45 sampler, §9.46 binding), and the re-measure arm (`bind1000_25pct`) now puts numbers on the repair: **OD-coincidence 15.31% (23,738 of 155,085 ride trips), declared-regime (`both_links` ±15 min) pairing rate 0.0130 (2,014 trips), direction split non-zero (239 return pairings)**. The realisation gap — 15.31% coincident vs 1.30% paired — is named in §9.48 and deliberately not chased while occupancy sits ABOVE its observed value (0.4855 vs 0.3503, outside the declared range in the flattering direction) |
| Ride scenarios — data grade | **Commute carpooling is RARE and the demand is non-commute**: census G62 (already in the package) gives car-as-passenger **3.35% of journeys to work**, passenger:driver **0.0598**, at SA1 — against an all-purpose HTS `Vehicle passenger` share of 18–32%. OBSERVED: commute (G62), driver-side `Serve passenger` 10–19.5% of journeys, all-purpose share, ride trip length/duration, occupancy 0.35. LITERATURE ONLY: child→school (61% of school trips by private vehicle), elderly driven. **NO TARGET AT ALL: non-household lifts, who-drives-whom, return-trip asymmetry** — not built, stated as limitations |
| Comparability | **A second planned family boundary (§9.49)**: freight changes the demand (new tier, through split) AND the model (truck in the mobsim, explicit vehicle types), so **`bind1000_25pct` is the last run of the §9.46/§9.47 family and nothing run after §9.49 compares to it**. The earlier triple break (§9.44/§9.45/§9.46-47) stands; the two pilot arms remain baselines for the PRE-repair model only. §9.43 (iterations=1000) is unaffected |
| Runs on disk | `smoke_postrebuild` (plumbing, 1% × 2) · **`conv1000_10pct`** and **`conv1000_25pct`** (the #5 pilot arms, both rc=0, both **`relaxed: true`** — evaluation in [`docs/audit/CONVERGENCE_PILOT_EVALUATION.md`](audit/CONVERGENCE_PILOT_EVALUATION.md)). `results/_aborted_20260816/` quarantines three dead runs without `_run.json`, including the cancelled `conv1500_10pct` — **do not relaunch it**. ⚠️ `results/S2_WEEKDAY_f025_i1000_s20260810/` is a fourth dead run with no `_run.json`, not yet quarantined. `ride_pairing_probe` (3-iteration 1%, §9.44) and **`freight_smoke` (1% × 2, §9.49 — proves trucks physically move)** are PLUMBING PROBES, not results. `results/_aborted_20260818/bind1000_25pct` is the STOPPED first attempt at the re-measure arm. **`results/_aborted_20260820/` quarantines two dead runs**: `base1000_25pct` (the §9.50 base arm, stopped by the owner at ~iteration 20 — relaunch needs approval) and `S2_WEEKDAY_f025_i1000_s20260810` (the old unquarantined dead run, now filed). **`results/bind1000_25pct/` is the completed re-measure arm** — rc=0, `relaxed: true`, evaluated in §9.48 — and is **the LAST run of the §9.46/§9.47 family: nothing run on the §9.49 freight demand compares to it** |
| Open issues | **9 open** (8 after #24 closes with PR #46). The four §9.51 directive issues: **#48 physical ride (THE ACTIVE LANE)**, #49 modes individualised, #50 demographic fidelity, **#30 re-opened** (sub-1 km walk mass — its own REOPEN IF met). Carried: #14 + #9 (stay open until a base arm completes and C5 exists — the 20 Aug arm was stopped), #28 (measurement ledger for the teleportation-to-physical transition), #31 (realisation-gap measurements; mechanism decision moved to #48). Verdicts: [`docs/audit/ISSUE_VERDICTS.md`](audit/ISSUE_VERDICTS.md). |
| **Results** | **No findings.** The reference scenario (S2 × WEEKDAY, 25%) has now run once to a relaxed, accounted state (§9.48) — a valid run record, whose fit rows are **pre-calibration diagnostics**. No counterfactual has run, deliverable 5 (calibrated base) is not met, and **nothing in this repository is a finding about the light rail.** |

### Measured run costs — the binding constraint now that #5 is settled

The pre-rebuild pilots are dead and deleted; what survived them was the timing.
The two post-rebuild arms are on disk and evaluated. **Convergence is no longer
what limits the campaign — run economics are.** The figures below are what any
run plan must be costed against, and the owner directive stands: no multi-hour
run without explicit approval.

- **9.8 s/iteration at 1%, ~24–30 s at 10%, 56–58 s at 25%** — so a
  1,000-iteration arm is ~2.7 h / ~8.3 h / ~16 h.
- **Post-rebuild, measured on the completed arms (18 Aug):** median 33.3 s at
  10% (11.0 h, ~29 GiB WS on 30g) and 90.2 s at 25% (30.8 h, ~33–38 GiB on
  40g). Memory model ≈ 24 GiB fixed + 0.09–0.3 MB/agent → a 100% run needs
  ~80–160 GiB heap. One unexplained slow block (25% arm, iterations ~200–293)
  self-recovered — the §9.36-era stall pattern, still unattributed.
- **On the repaired demand (20 Aug, `bind1000_25pct`):** median **105.9 s** at
  25% (34 h 44 m for 1000 iterations, WS ~34–37 GiB on 40g) — ~17% slower than
  the pre-repair arm. Pace was ~66 s/iteration for the first ~150 iterations,
  then 117–160 s through the congested middle, recovering to ~127 s after the
  innovation cutoff; the log never stalled.
- **Never run convergence arms concurrently.** Three arms declared 78 GiB of
  heap on a 63.5 GiB machine, Windows grew the pagefile from 8.1 to 19.1 GiB,
  and the 10% arm's median iteration went from ~19 s alone to ~42 s alongside
  the others. Iteration *count* survives contention; iteration *duration* does
  not.
- **One unexplained event, unattributed — do not assume it is gone:** a 10% arm
  iteration took **2,415 s** against a ~20 s median, stalled 37 minutes between
  `PersonPrepareForSim` and QSim start at near-zero CPU (`realT=2237s at
  simT=0.0s`). Not CPU, not GC, not the monitor, not OneDrive. It did not recur
  in ~400 iterations.

### ✅ G2 is EXERCISED, not asserted — a second city runs the framework unchanged

`python tests/check_city_agnostic.py` — **13 assertions, all passing**, and a CI
job on every push. It builds a second city from this city's own declarations
under a different identity (different projection, base year, seed, day types,
**three modes not five**), emits its MATSim config through the same emitter, and
asserts **differences** — a test that only checked the config parsed would pass
even if every value in it were Newcastle's. It hashes `src/`, `config/schema/`
and `run.py` either side to prove no framework file changed while it ran. It
invents no observation and deletes its fixture afterwards.

**Building it found two defects that one city could never expose:**

- **`CITYSIM_CITY` had never worked.** Setting the documented city selector to
  *any* value — including its own default — made every `registry.load()` raise
  `env CITYSIM_CITY matches no registry field`. The resolver read `CITYSIM_*` as
  field overrides and skipped only `CITYSIM_REPO`. Nobody had set it, because
  there is one city and the default applies when it is absent.
- **The contract was over-strict, and its own caveat said so.**
  `required_fields.json` demanded all 292 fields of every city; a three-mode
  city was refused for not declaring bike parameters. Fields now carry
  `required_if_mode`, **derived** from the tool binding rather than judged.

### ✅ The hardcoding ledger — 0 items, and `--strict` is a CI gate

```
python src/registry/check_hardcoding.py            report
python src/registry/check_hardcoding.py --strict   exit 1 if anything is found
```

**The honest starting count was 185, not 95.** The audit had been asking whether
a field key was a SUBSTRING of any source file, which counted a mention in a
comment, a docstring or a test assertion as reach — so the count *fell* when
someone added an explanatory comment. Its constant scan saw only module-level,
single-target, ALL-CAPS, **scalar** assignments, which is a small minority of
the forms a decision takes: it could not see `ACCEL, DECEL = 1.2, 1.3`, a table
of stop coordinates, `def make_bus_shuttle(speed_kmh=28.0)`, or
`add_argument('--iterations', default=100)`. Its coordinate rule wanted a
literal two-tuple, so it reported 3 of this repository's 22 coordinates.

| Question | Was (as counted then) | Honest baseline | Now |
|---|---|---|---|
| Declared but unwired | 37 | 38 | **0** + 7 declared-ahead-of-consumer, each with a written reason |
| Read only by the measurement layer | — | 11 | **0** |
| Config template literals | 44 | 47 | **0** — there is no template |
| Values decided in code | 11 | 67 | **0** + 18 structural exceptions, each with a written reason |
| Coordinates in a script | 3 | 22 | **0** |
| **Inert bindings** (new) | — | — | **0 of 69** — every bound field proven to reach the model |

**The sixth question is the one that matters.** `param_config.reach()` changes
each bound field's value and diffs the emitted config. A field that resolves,
appears in the run's provenance snapshot and moves nothing is this repository's
signature defect, and no text search can see it — `consumers` is a claim, a
substring finds the key in a comment, and reading the code has never once caught
an instance. **69 of 69 pass.** It costs about a second and starts no JVM.

### What replaced the template

`src/registry/param_config.py` **builds** the MATSim config and pt2matsim's two
from the fields that declare a binding. A parameter exists only if a field
claims it or the caller supplies it under one of three declared runtime roles —
a path, the city's own identity, a value **derived** from declared fields — and
`closure()` returns anything else. There is nowhere left to type a number.

`run_matsim.py` **emits** rather than patches. It used to read the shipped
config and rewrite six parameters, so a run overlay setting any other field was
validated against its sweep, written into `_config.json` as the run's
provenance, and reached nothing: the snapshot said one thing and the run did
another. Every declared field now reaches the model.

### Four mis-bindings the emitter found by refusing to write them

| Field | Bound to | Why it is wrong |
|---|---|---|
| `RUN.sample.storage_capacity_exponent` | `qsim.storageCapacityFactor` | an **exponent** into a **factor** — 1.0 against a 0.01 flow factor, which MATSim rejects in one second |
| `C.time_weights.beta_walk_mode`, `beta_bike_mode` | `…marginalUtilityOfTraveling_util_hr` | a **ratio to in-vehicle time** into a **util/hour rate** |
| `A.parking.charged_hours_by_day_type` | `chargedStartHour`, `chargedEndHour` | a per-day-type **window dict** into two **scalar hours** |
| `C.scoring.activity_typical_duration_s` | — | declared in seconds; MATSim reads `hh:mm:ss`, and the template held a second representation of the same value |

### ⚠ One model value changed, deliberately

`build_matsim_network.py` held its own copy of the road class defaults, and the
comment above it said it was kept there *"so that the MATSim network, the SUMO
corridor and A1_road_edges.csv cannot drift apart"*. **They had drifted**, on
six classes and in both directions:

| class | script | `A.road.speed_default` |
|---|---|---|
| motorway | 100 | **110** |
| motorway_link | 60 | **80** |
| trunk | 80 | **60** |
| primary_link | 50 | **60** |
| secondary_link | 50 | **60** |
| service | 20 | **25** |

Nothing compared them: a second copy with no `legacy_symbol` is invisible to
`check_legacy_drift.py`. There is one copy now and **the network takes the
declared speed**, so the next network build changes on those six classes. Taken
because the registry is the declared source of truth and #32 rebuilds the
network anyway.

### Two things the handover brief got wrong

- **`DWELL_CHARGING = 20.0` was NOT pinned by `legacy_symbol`.** §2.7 said it
  was and told the next agent to leave it alone. It carried none, its
  `EXPECTED_DIVERGENCE` entry compared nothing, and it **pinned an `unobtained`
  input in a script** — walking past the one refusal the registry exists to
  make. It now takes the baseline sweep point from the reference scenario's
  overlay.
- **`A.lightrail.tsp_enabled` reached nothing** while all ten scenario overlays
  set it, so S2b was distinguished from S2 only by a literal `0.75` in an
  expression. Both are declared and wired.

`check_legacy_drift.py` now compares **zero** fields, and that is the point:
both `EXPECTED_DIVERGENCE` entries are retired because neither has a second copy
to diverge from.

## Phase progress

| Phase | State | What is done | What is not |
|---|---|---|---|
| **P0** Scoping | ✅ complete | Base year 2026, zone system, S0–S6 settled (§1) | — |
| **P1** Data acquisition | ✅ complete for P4's needs | **391 files hashed**, provenance-tagged; 10 OSM layers re-harvested 16 Aug over the derived extent; DEM tile set derived from the boundary (5 tiles, 100% gradient coverage) | Field dwell measurement never done. SCATS **refused by policy** (§9.21), journey-linked Opal unpublished — both swept, never pinned. Two ABS DataPack URLs (Mesh Blocks NSW, WPP DZN) now 404 upstream — files were never held locally; noted, not chased. |
| **P2** Network build | ✅ **rebuilt 16 Aug on the corrected extent** | 1 MATSim base (181,892 links) + 4 variants, 15 mapped feeds, **0 unmapped stops in every feed**, 4 SUMO nets; link speeds agree with the declared registry values | Corridor kerbside 95% imputed, lane width 98.6%, capacity 100% (#27 closed as *cannot* be closed — B3 must report them as uncertainty). |
| **P3** Demand synthesis | ✅ **regenerated 20 Aug with the freight tier (§9.49)**, on the 18 Aug age-structure and escort-binding repairs (§9.46, §9.47) | 612,687 agents with census age structure, employment per SA1 × sex × age band (G46), education attendance per SA1 (G01); 621,722 WEEKDAY plan persons (incl. external, 16,264 through cars and **90,393 freight trucks** — 1,691 through + 88,702 internal); **68.6% of weekday escort tours bound** (identical to §9.46); destinations solved per purpose × home LGA; through tier at 3 gates, each split car/truck by its station's observed heavy share | Northern through exits ungated (§9.41 limitation). Truck routing unconstrained (§9.49 limitation — no truck-route layer exists). Bike/walk shares re-measure on the first real run before #29 is sized. |
| **P4** Calibration | 🟡 **in progress — 7 of 9** | Harness, metrics, fit, calibration loop, report, outer-loop tolerance, **live run view** | Deliverable **0** (input completeness) and **5** (calibrated base) not met. |
| **P5** Scenario runs | ⬜ not started | — | **SUMO has been built six times and simulated zero times**, deliberately. |
| **P6** Analysis | ⬜ not started | — | Hypothesis B1 has **no observable at all** without pedestrian counts. |
| **P7** Write-up | ⬜ not started | — | — |

### What the city restructure changed

**The framework no longer knows it is modelling Newcastle.** Everything specific to the
city — its registry, its scenario/day/run overlays, its acquisition adapters, its data,
networks, schedules, demand, scenarios and params, and the seven builders that encode its
intervention, corridor and history — lives under `cities/newcastle/`. `config/` is now
`config/schema/` alone: the portable half.

- **`src/city.py` is the only module that knows where a city lives.** 338 path literals
  across 46 scripts now resolve through it, and paths stay **city-relative** inside a
  city, so one manifest row means the same thing in every city. The migration was
  verified by regenerating the manifest and diffing it: **376 rows before and after, no
  path added or removed, no hash or byte count changed** — only `produced_by`.
- **The input contract is now stated, not implied.** `config/schema/city.schema.json`
  (identity, and a boundary that must be **derived**, never a typed rectangle), plus the
  generated `required_fields.json` (210 keys) and `layers.json` (119 artefacts, found by
  reading the framework's own `city.path(...)` calls). `python src/registry/check_city.py`
  gates a city **before** it runs, and CI runs it.
- **Constants that were one city's value are declared:** the CRS in seven modules, the
  mode-share filter value in three, the `#34` CBD box and the harbourside search window.
  **Both extents were relocated at byte-identical values** — #34 is still open, and
  relocating a constant is not fixing it.
- **The metrics key `newcastle_lga_pct` is now `target_lga_pct`.** This is a breaking
  output-schema change: **run records written before it cannot be read by `fit.py`.**
  Accepted deliberately in favour of a city-agnostic schema.
- **Two defects found by doing it.** Four scripts assigned a bare directory name as a
  path (`OUT = 'schedules'`), which silently wrote 32 MB of rebuilt GTFS into the
  repository root instead of the city; `check_city.py` now fails on that class, and the
  guard was verified by reintroducing the defect and watching it fail. The `build_manifest`
  CRS string still said **GDA2020** — the §2.6 correction had never reached it either.

**Second pass — the study's records moved too.** This city's research design,
decision log, board, audits, handover notes and generated references are now under
`cities/newcastle/docs/`; `docs/` documents the framework alone, and the three
generators write into the city that owns the document. `build_landuse_parking.py`,
`build_sumo_corridor.py` and `map_sa1_to_lga.py` followed their logic into
`cities/newcastle/build/`. `required_fields.json` stopped copying field
descriptions out of the registry, which had put 213 place mentions inside the one
file meant to be city-free. **Framework-wide place mentions: ~2,900 → 262.**

### What the last two sessions established

**Repository cleanup.** `STATUS.md` was 79% dated narrative; the documents had drifted
from the model (four stale figures, one self-contradictory header, and the §2.6 CRS
correction never propagated to `CLAUDE.md`). Documents are now filed under `docs/`,
`DECISIONS.md` has a topical index, and the project is no longer codenamed after one
suburb (§9.36, #36 tracks the two surviving code identifiers).

**A run now reports itself.** `RunTelemetry` publishes per-mode and per-vehicle-type
counts and per-link congestion **from inside the mobsim**, and `summarise_run.py` closes
out a finished run with `SUMMARY.md` + `_summary.json`. `writeEventsInterval` did not
need to change: a registered handler sees every event on every iteration — the package's
own 26 event files against 251 leg histograms proves it.

**Three defects found by measurement, not by reading** (§9.36):

- **The observer killed a run.** A Windows file-replace threw while the view was reading,
  and the exception propagated out of the handler, terminating a run at iteration 5.
  Telemetry is now structurally unable to reach the mobsim. *An instrument that can stop
  the experiment is not an instrument.*
- **`build_basemap.pack()` silently dropped every segment longer than 327 m**, so the
  simplified LGA boundary shattered and the landmass never filled — the map rendered as
  ocean. `build_replay_page.py` decodes the same payload: **any replay page built before
  this is wrong and must be rebuilt.**
- **A silent default that happened to be right.** The summariser read a registry key that
  does not exist and fell back to a hard-coded `0.8` — the shipped value, so it produced
  the correct answer for the wrong reason.

**Eight of this project's defects are now the same class:** a declared value that reaches
nothing, or a default that is right by accident. Establish reach by **changing a value and
watching the output**, never by reading the code.

---

## The deliverable checklist

Proposal §8 sets six project-level deliverables. P4's own list has grown from
seven to nine: one because the proposal's §7.2 fallback was found never to have
been built, and one because calibrating a model with known-missing demand would
calibrate the wrong model.

### P4 — calibration

| # | Deliverable | State | Where |
|---|---|---|---|
| **0** | **Specification and input completeness** — **NEW, and it gates 5** | ⬜ **not started** | see breakdown below |
| 1 | Run harness | ✅ done | [`src/run/`](../../../src/run/) |
| 2 | Metric extraction | ✅ done | [`src/analyse/`](../../../src/analyse/) |
| 3 | Fit statistic | ✅ done, 10 tests | [`src/calibrate/fit.py`](../../../src/calibrate/fit.py) |
| 4 | Calibration loop | ✅ done | [`src/calibrate/calibrate.py`](../../../src/calibrate/calibrate.py) |
| **5** | **Calibrated base + parameter provenance** | ❌ **NOT MET** — blocked by a modelling decision **and** now by deliverable 0 | `params/C5_calibration.json` |
| 6 | Calibration report | ✅ done | [`src/calibrate/report.py`](../../../src/calibrate/report.py) |
| 7 | MATSim↔SUMO outer-loop tolerance | ✅ done — **5 s** | [`DECISIONS.md`](DECISIONS.md) §9.16 |
| **8** | **Transfer-penalty estimate** — proposal §7.2's own fallback | ✅ **met by its own fallback clause (§9.32)**: the estimate is **not possible** from this package and the reason is recorded, so the 3–15 min sweep stands and every headline stays bound to a curve across it. §7.2 needs tap-on/tap-off **timing**; every Opal source held is a monthly aggregate, the stop-level tap data is **holdout**, and no calibration row bears on interchange. Published interchange **times** are the wrong quantity — they would double-count the walk and wait MATSim already simulates. Settled only by a TfNSW unit-record request. | §9.32, §9.21 |
| 9 | Live run view | ✅ **rebuilt** (§9.36) — the run now publishes live telemetry from inside the mobsim: iteration progress, simulated clock, per-mode and per-vehicle-type counts, stuck agents, and a per-iteration congestion map. All 30 run-input sets carry the `telemetry` module, and a finished run writes `SUMMARY.md` + `_summary.json` stating whether it relaxed and whether its accounting closed. **Now actually wired**: the view was rebuilt but never re-connected, so `RUN.monitor.enabled`, `.port` and `.poll_s` reached nothing — every run prints its own `live view:` url before MATSim starts, and `.stall_s`/`.poll_s` were recorded as `consumers: null` while `run_view.py` read them. The port scan was also broken on Windows (`allow_reuse_address` set on `socketserver.TCPServer` itself let three concurrent views bind 8731; two served nothing). The relaxation panel now carries a red/green light against a **declared** tolerance, `RUN.relaxation.drift_tolerance_pp`, which replaced a hard-coded `DRIFT_THRESHOLD_PP = 0.5` in `summarise_run.py`. | [`src/analyse/run_view.py`](../../../src/analyse/run_view.py), [`src/java/citysim/RunTelemetry.java`](../../../src/java/citysim/RunTelemetry.java) |

### Deliverable 0, broken down — the work that must precede a calibrated base

Ordered. 0a is first because it may change what the rest is worth.

| | Work package | Why it gates a calibrated base |
|---|---|---|
| **0a** | **Specification audit.** DONE - the ranked register is [`docs/audit/SPEC_AUDIT.md`](audit/SPEC_AUDIT.md) (§9.25). | **Two near-exact inversions, not five miscalibrations:** car -26.5 / ride +29.4 and walk -12.7 / bike +12.7. **A1: ride is routed on the network but not simulated in it**, so it realises **55.7 km/h against car's 49.3** - a passenger arrives 13% faster than the car carrying them (#28). A2/A3: ride is not chain-based and bike ownership is silently universal (#31, #29). A4: walk's 18x deficit may be trip lengths, not scoring (#30). **B1 prevented damage - #24's business-travel premise is false.** **A1's defect is verified; its mode-share effect is WITHDRAWN (§9.27) - both arms ran at 250 iterations, and the pre-fix model at 1000 fits BETTER (33.8 pp) than the post-fix model at 250 (44.6 pp), so car/ride was largely non-relaxation. Walk/bike does NOT improve at relaxation and is confirmed structural (#30, #29).** |
| **0b** | **Derive what can be derived.** Move as many of the 78 `assumed` fields as the data supports to `measured`/`derived`, and reclassify those that are methodological choices rather than empirical guesses. **Realistic target 15–25, not 78** — the HTS held is aggregate tables, so anything about tour structure (intermediate stops, activity durations, second stops) is *not* derivable without a TfNSW unit-record request. Candidates: `B.activity.day_purpose_mix`, `B.activity.p_mandatory`, `B.activity.sat_to_sun_rate` (RMS hourly counts carry dates → real day-of-week), `B.external.interaction_rate` (ABS journey-to-work table, §13 item 11 — obtainable), `A.road.*_default` (observed OSM distributions), `A.lightrail.line_speed_kmh` (GTFS ÷ measured alignment), `C.vot.*` (TfNSW published economic parameters), and `RUN.routing.beeline_distance_factor`, which is **probably a duplicate** of the measured detour factor 1.3376. | 46% of the model's controllable values are educated guesses. Every one carries a sweep, so nothing is hidden — but a calibrated base resting on 78 guesses is a weaker claim than one resting on 55. |
| **0c** | **Fleet capacities. DONE (§9.30).** Bus 44+18, ferry 149+51, rail 98+48, tram 60+210. `literature`; the ferry split is the only published one and is held fixed, rail's seated share is assumed and swept. | **Closed.** Every default overstated the real vehicle, rail by ~2.7×, and **no vehicle in the fleet had standing room at all** — so the C1 crowding multipliers were unreachable in every scenario. They can now bind. |
| **0d** | **The missing demand. DONE in all three parts.** **(1)** boundary/through traffic ✅ (§9.41, seeded from cordon counts, no holdout row); **(2)** work-related business travel ✅ struck on evidence — B2 already generates WB at 2.11% against an observed 2.0% (spec-audit finding B1); **(3)** freight ✅ (§9.49, issue #24 — a physical `truck` mode, smoke-verified). **Deferred to P5:** SUMO pedestrian crossings (a §14 toolchain change; proposed DELETE). | Each added demand ahead of calibration, so nothing needs re-calibrating after them — which was the point of the ordering. |
| **0f** | **Parking price. DONE (§9.31, issue #33).** Derived from the city's own core-zone job-density distribution (p90 = 1,500.9, p99 = 8,710.5 jobs/km²), reaching the model through a `PersonMoneyEvent` handler that charges **car only** from arrival to the next car departure. | **Closed.** The price layer had been declared since P1 and **read by nothing** — a car parked free in a study about city-centre access — and its spatial basis was four hand-drawn boxes, one of which could never match a facility. Known limitation, measured not supposed: the ramp prices suburban malls at CBD rates; the contiguity fix was built and **rejected** because it also excludes the University and John Hunter Hospital, which do charge. Price is common to all scenarios, so it bites on the base calibration rather than on the S-vs-S comparison. |

### Landed from the published catalogue (§9.23, §9.24)

| Input | State |
|---|---|
| **Corridor SCATS site ids** | ✅ **observed.** `A2_signal_control_corridor.csv` declared `scats_site_id` from P2 and left it empty on all 70 rows. TfNSW's Traffic Lights Location inventory fills all 14 intersections, mean match 8.0 m, max 26.4 m. The join tolerance `A.signals.scats_match_radius_m` is **held fixed, not swept** - no output varies across it. |
| **Corridor signal install dates** | ✅ **observed, and deliberately not acted on.** **8 of the 14 corridor signals were installed in 2018 for the light rail**, two named *light rail crossing*; the pre-intervention corridor had **6**. Recorded as an attribute only. Re-deriving the counterfactual from it would reshape the same hypothesis `A.corridor.pre_lr_lanes_per_dir` encodes, which is the B3 test - **decision taken 12 Aug 2026: NO** - the pre-light-rail corridor keeps all 14 signalised intersections and the dates stay an attribute (§9.24). |
| **SCATS phasing** | ❌ still refused. The inventory gives identity, location and install date, and **no phase plan, cycle time or split**. `A.signals.scats_phasing` stays `unobtained` and swept. |

### Declined, with reasons — recorded so they are not re-raised

| Request | Answer |
|---|---|
| Incorporate the 143 held-back targets | **No.** They are the only test the model has. The split was fixed before any fitting precisely so nobody can move a target after seeing a result. They open **once**, at the end. New observables become **constraints** (the §9.8 / §9.13 pattern), never targets. |
| Delete the targets that cannot inform anything | **No.** The 13 Opal card-type rows are *calibration* rows in the pre-registered 210. Deleting them retrospectively changes a set fixed in advance — the move that would let anyone drop whatever the model fails at. They cost one line of explanation and are reported with the reason they cannot be scored. |
| Taxi / motorcycle / rideshare as their own modes | **No target exists.** The HTS reports "Other" as one bucket; IPART's survey measures usage incidence, not Newcastle mode share. Three unfalsifiable modes would be structure pretending to be rigour. |
| Obtain SCATS phasing | **Refused by policy**, documented (§9.21). Proposal §7.2's contingency is now the operative path and binds every headline figure to a stated uncertainty band. |

### Carried over from P0–P2 — now owned by numbered plan tasks

Work carried from earlier phases that no deliverable owned is now owned by the
numbered plan below — the settled rows (GTFS-Realtime, dropped §9.23; *"requests
lodged"*, settled §9.21) and closed #27 (P2 row above: **cannot** be closed —
task 6.4 reports the imputation as uncertainty instead) are removed from this
board. Open carried items and where they went: **#34** → 4.1.6 (its floorspace
question is answerable only after the re-harvest — the verdicts showed
`buildings_cbd.osm` was itself harvested inside the box); **charging dwell field
measurement** → 5.3; **ABS journey-to-work SA2×SA2** and the **day-of-week
split** → 4.3 (deliverable 0b); **pedestrian counts** → 6.1 and **retail
floorspace/vacancy audit** → 6.2 (both block P6, not P4); **2014 timetable,
LiDAR DTM, event attendance** → backlog (nothing depends on them; do not start
before the base works).


### Project-level (proposal §8)

| # | Deliverable | State |
|---|---|---|
| 1 | Reproducible model | 🟡 on track — seeded, pinned, byte-identical rebuilds; not containerised |
| 2 | Open data package | 🟡 **376** files, provenance, licence, lineage — 10 OSM layers pending the #32 re-harvest |
| 3 | Calibration report | 🟡 generator exists; no calibrated base to report |
| 4 | Findings paper | ⬜ not started |
| 5 | Interactive result explorer | 🟡 replay + live run view exist; per-scenario explorer does not |
| 6 | Method note on evaluation gaps | 🟡 **strengthened** — the SCATS refusal is now a documented, citable instance (§9.21) |

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
(`cities/newcastle/build/build_corridor_road_attributes.py`):

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

## The plan — every open task, numbered, with ETA

Every open task and deliverable in the repository, consolidated from this
board, [`docs/audit/ISSUE_VERDICTS.md`](audit/ISSUE_VERDICTS.md),
[`DECISIONS.md`](DECISIONS.md) §13 and the twelve open issues, in dependency
order. Task numbers are `<phase>.<batch>.<step>` and replace the old ad-hoc
names (`B0` = batch 4.1). ETAs are **estimates** — *attended* is hands-on
effort, *wall* is elapsed compute/network time; run-cost figures derive from the
measured s/iteration above, the rest are judgement and say so by being
estimates.

### Batch 4.1 — the rebuild — ✅ **DONE 16 August** (this PR)

Executed as planned, in one batch. Measured outcomes against the gates:
harvest 10/10 layers, all larger; **99 → 4** core SA1s without a road node,
**0 agents** in the 4; network speeds agree with the registry; 15 feeds mapped
in one build, 0 unmapped stops each; `check_package` **1,452 ALL PASSED**;
manifest **391**; `check_hardcoding --strict` **0**, reach 69/69; #37
acceptance **zero on all three day types**; #34 floorspace damage measured
**nil** (nearest out-of-box building 281 m from any segment); smoke run
`smoke_postrebuild` rc=0, median iteration 10.1 s at 1% (was 9.8 s on the
smaller network) — full memory re-measure belongs to the first 10% arm
(4.2.1). The task table below stands as the plan of record.

| # | Task | Closes | ETA |
|---|---|---|---|
| 4.1.1 | Re-run the OSM harvest over the derived extent: `python cities/newcastle/extract/overpass.py` (10 layers × 8 tiles; expect 504s and mirror rotation; resumes from cached tiles). Gate: every layer **larger** than its `networks/osm_pre_issue32/` counterpart; `osm_tiles.verify()` passes on each | #32 (data half) | attended ~1 h · wall 3–6 h |
| 4.1.2 | Rebuild the layer chain, in order: `build_network_layers` → `attach_gradient` → `attach_speed_zones` → `build_corridor_road_attributes` → `build_matsim_network` → `build_landuse_parking` → `build_zone_attractions`. Gate: the 87 clipped core SA1s (verify against the stricter **99 SA1s / 35,365 agents with no road node**) are inside the road network; network link speeds now match `A1_road_edges.csv` (kills the 27.4%-of-links speed disagreement) | #32, speed-disagreement defect | attended 2–3 h · wall 0.5–1 day |
| 4.1.3 | Demand fixes, then regenerate B2 **once** (all three day types): **(a)** cap or wrap activity chains at the 24 h boundary, acceptance **zero** collisions on WEEKDAY/SAT/SUN (#37); **(b)** declare the bike-availability asymmetry in `DECISIONS.md` + registry, and decide (and sweep) a constraint or record why not (#29 mechanism); **(c)** destination placement against the HTS per-purpose distance constraint — placement only, the scoring half is repaired and must not be re-fixed (#30); **(d)** external-station through matrix seeded from cordon counts, touching no holdout row (#20); **(e)** heavy-vehicle background layer from the measured 6.52% share, swept never pinned (#24). Every new value: declared field + sweep + `DECISIONS.md` entry | #37, #29 (mechanism), #30, #20, #24 | attended 4–6 days · wall +hours per B2 regen |
| 4.1.4 | Rebuild scenario GTFS feeds from the declarations (needs `networks/osm/footways.osm` from 4.1.1) and regenerate the 30 run-input sets through the emitter | stale feeds | attended 1 h · wall 2–4 h |
| 4.1.5 | Gates, in order: `check_hardcoding --strict` (keep 0; keep reach 69/69 — new fields must bind), `build_manifest`, `check_manifest`, `render_docs`/`render_schema`, `check_package` (must now pass its OSM checks; manifest back to ~386) | package gate | attended 2–3 h |
| 4.1.6 | #34's floorspace question, now answerable: measure buildings outside the old CBD box fronting the seven streets against the new harvest, **before** changing the denominator; any derived replacement keeps a street-name disambiguator (the verdicts showed the box's undocumented job is name disambiguation) | #34 | attended 2–4 h |
| 4.1.7 | Stale-statement fixes: the false escort note in `params/C3_count_comparison.json`; `RUN.controler.last_iteration`'s "carry 100" description | verdict defects 2–3 | attended 1 h |
| 4.1.8 | Housekeeping riding along: restore `check_package.py` coverage of the live view (`run_view.py` / `summarise_run.py`); rebuild any replay page before use (all pre-14 Aug pages are wrong, §9.36); strike the FALSE halves from issue bodies #20/#24/#30, refresh #14/#28, drop #28's `blocker` label | board hygiene | attended 1–2 h |
| 4.1.9 | Smoke-run the rebuilt package (10%, few iterations) to prove MATSim executes it, and **re-measure memory** — a bigger network may move the ~40% sample ceiling | executability | attended 1 h · wall 1–2 h |

### Batch 4.2 — measure, then calibrate (runs, not commits; strictly after 4.1)

| # | Task | Closes | ETA |
|---|---|---|---|
| 4.2.1 | ✅ **DONE 18 Aug.** Convergence pilot, one arm at a time: 10% × 1000 and 25% × 1000. Both failed the *declared* gate identically — diagnosed as a defect in the instrument, not the runs: the window started at the innovation cutoff and so included a **one-iteration** selection snap (+3.3 pp car at both fractions), making it unpassable at any horizon. Fixed and declared in one change (§9.43): `RUN.relaxation.settle_margin_iterations` = 10, `RUN.controler.last_iteration` = **1000** (`measured`, off `unobtained`), both arms now `relaxed: true` at +0.22 / +0.17 pp. Arm 3 (`conv1500_10pct`) **cancelled by the owner** for compute economy — the ~2 pp of un-relaxed pre-cutoff search creep is carried as **declared uncertainty**. Evaluation: [`docs/audit/CONVERGENCE_PILOT_EVALUATION.md`](audit/CONVERGENCE_PILOT_EVALUATION.md) | #5 | ✅ 42 h of compute spent |
| 4.2.2 | ✅ **DONE 18 Aug** — measured on both pilot arms: ride out-runs car in every bin below 50 km (1.13× → 1.01×), the aggregate parity is a Simpson's reversal; bike 4.0% vs 3.2 observed needs no tuning; sub-1 km mass 2.5% vs >~10% reopens #30. [`docs/audit/CONVERGENCE_PILOT_EVALUATION.md`](audit/CONVERGENCE_PILOT_EVALUATION.md) | #28 (sized), #29 (closed) | — |
| 4.2.3 | ✅ **DONE — built 18 Aug (§9.44, PR #40), re-measured on the repaired demand 20 Aug (§9.48).** Tier 1 `BeforeMobsim` pairing: a paired passenger takes the household driver's realised time; blast radius measured against a control (7 legs rewritten vs 0, mode share bit-identical). **Step 3, the re-measure arm, is complete**: `bind1000_25pct` (25% × 1000 WEEKDAY, rc=0, relaxed) measures OD-coincidence 0.104% → **15.31%** and declared-regime pairing 0.00004 → **0.0130**; the #28 residual is ~11.6 s at 25%; occupancy 0.4855 vs observed 0.3503 (outside range, flattering direction — 4.2.4's problem). The realisation gap (15.31% vs 1.30%) is named in §9.48, not chased | #28 (sized), #31 (measured), #9 | ✅ |
| **4.2.5** | ✅ **DONE 18 Aug (§9.46).** The escort tour binds to the person being escorted: households generate whole, an HX tour takes an already-drawn member trip's destination and departure **exactly** (all 120,980 placed weekday bindings verified coincident), bound tours are immovable in the escorter's timeline, unbound tours fall back to the distribution. **68.6% of weekday HX tours bound**; rate untouched (re-target, never add); binding scope and min-gap declared and swept; escort trips can no longer be made BY `ride`. Whether realised pairability moves is the next run's measurement | #31 (supply half), §9.44, §9.46 | ✅ |
| **4.2.6** | ✅ **DONE 18 Aug (§9.47).** Employment now per (SA1, sex, ABS age band) from G46 — 65–74 realises 15.3%, 75–84 1.5% against the flat 52/48 before; **plus two defects the brief did not know**: the 75+ population was missing (grouped G04 columns never read — 85+ had 186 persons against a census 15,151, now 16,188) and student status is now observed attendance (G01) instead of 100% of under-18s. Full evidence: [`docs/design/age-structure.md`](design/age-structure.md) | population defect, §9.47 | ✅ |
| **0d(3)** | ✅ **DONE 20 Aug (§9.49).** Freight is a physical `truck` mode: through-gate volumes split by each station's own observed heavy share, an internal tier over the observed freight-industry attractor at the assumed swept ratio (0.0697, sweep 0.0–0.14), departures and weekend factors MEASURED from the classified hourly counts. Smoke-verified (913 trips, 140,380 traversals at 1%); car fleet unchanged, proven against the jar's bytecode. **Comparability break: a new demand family starts here** | #24 | ✅ |
| 4.2.4 | 🟡 **DECIDED, not delivered (§9.50, PR #47).** The §8.5 branch is constrain-and-report, logged before any result: ASCs stay priors, #9 resolved by decision, the §9.48 occupancy excess reported not absorbed; the loop's rebuild-stage defect fixed (unclassified consumers were defaulting to movable); `--constrained-base` machinery built and tested. **The base arm was STOPPED by the owner at ~iteration 20** — C5 + report await an approved relaunch (~35 h at 25% × 1000), and the §9.51 directives may change the demand family first (sequencing decision) | #14, #9 | decision ✅ · base run blocked on approval + sequencing |
| 4.4 | **Point-to-point (taxi + rideshare) mode** — decision re-opened by the owner 18 Aug 2026 on new evidence (IPART now surveys Newcastle and Hunter as its own p2p region; the passenger service levy counts every trip). Build as a teleported priced mode: measured taxi fares, literature rideshare rates (swept), fleet assumed; validated against the inferred 10,000–35,000 trips/day band as a **constraint, never a target**. Evidence dossier and declaration plan: [`docs/design/point-to-point-mode.md`](design/point-to-point-mode.md). **Strictly after 4.2.4** — a ~1% refinement does not precede the measured 10–20 pp defects. First step: extract the Newcastle and Hunter table from the IPART 2025 information paper (PDF fetch timed out on first pass) | p2p mode | attended 2–3 days |
| 4.3 | Deliverable 0b, parallelisable with 4.1: derive what the data supports (realistic 15–25 of 78 `assumed` fields) — ABS journey-to-work SA2×SA2 extract → `B.external.interaction_rate`; day-of-week split from dated RMS counts; `A.road.*_default` from observed OSM distributions; `A.lightrail.line_speed_kmh` from GTFS ÷ alignment; `C.vot.*` from TfNSW published parameters; resolve the probable `RUN.routing.beeline_distance_factor` ↔ measured 1.3376 duplicate | 0b | attended 2–3 days |

### Batch 4.5 — the four §9.51 owner directives (research first, owner decision, then build)

Set 20 August 2026, superseding the prior value order. **Each is
research-and-discussion BEFORE any build** — the owner asked for exhaustive
research, and each collides with a recorded cost or data limit that the
research must confront rather than rediscover.

| # | Task | Issue | State |
|---|---|---|---|
| **4.5.1** | **Physical ride** — every ride trip a passenger physically in a car, share tuned to the observed 20.60% | **#48 — FIRST** | 🟡 **research WRITTEN** ([`design/physical-ride.md`](design/physical-ride.md)): four mechanisms with recorded costs (socnetsim ~10×; DVRP probe; joint-vehicle-plans engine on the §9.46 binding; demand-side re-moding). **Open: the owner's mechanism + re-moding policy choice**, then the dossier §5 probes |
| 4.5.2 | **Modes individualised** — pt split into bus/train/LR/ferry; motorbike + taxi/rideshare distinct | #49 | 🟡 **research WRITTEN** ([`design/mode-individualisation.md`](design/mode-individualisation.md)), anchors MEASURED, and **Tier P motorbike is BUILT and smoke-verified (§9.52)** — a physical locked carve from car on the G62 anchor, fit comparing car+motorbike. Open: Tier R (pt reporting split), Tier C (choice-distinct submodes, batch with #48's break), taxi/rideshare (4.4 plan) |
| 4.5.3 | **Sub-1 km walk mass** | #30 (re-opened) | 🟡 **decomposition MEASURED** (on #30): generation is the loss site — 4.45% of legs under 1 km / 7.85% under 1.5 km against walk-only alone observed at 13.40%; p5 trip length 1.08 km; scoring/placement/mode choice exonerated. Open: the generation mechanism choice + a citable observed distance-band source |
| 4.5.4 | **Demographic-conditional mode fidelity** | #50 | 🟡 **inventory MEASURED** (dossier §3): held = mode × sex (G62), G46/G54/G60 demographics; **mode × age is NOT held — an acquisition item**. Open: the modelled table from the next valid run + the acquisition |
| 4.5.0 | **Sequencing decision (owner)**: relaunch the 4.2.4 base arm before or after 4.5.1–4.5.3 — each changes the demand family | #14 | ⬜ ~35 h per arm; no standing run approval exists |

### P5 — scenario runs (blocked on 4.2)

| # | Task | ETA |
|---|---|---|
| 5.1 | SUMO corridor harness + MATSim↔SUMO outer loop against the declared 5 s tolerance (SUMO: built six times, simulated zero — deliberate until the base is right) | attended 3–5 days |
| 5.2 | SUMO version change for pedestrian crossings (`--osm.crossings` segfaults 1.27.1) — a §14 toolchain change = a model change; log it | attended 1 day + corridor rebuild |
| 5.3 | Charging dwell field measurement (one visit, Civic or Crown St) — the only route left, the GTFS-RT fallback is gone; until then `A.lightrail.dwell_charging_s` stays swept | attended 0.5 day |
| 5.4 | Scenario × day-type runs, S0–S6, at the chosen fraction and settled iteration count — prioritise S0/S1/S2 × WEEKDAY; 30 sets total | wall: weeks; sequence by hypothesis need |
| 5.5 | Per-run close-out: metrics → fit → summary; replay pages rebuilt post-§9.36 only | attended ~1 h per run |

### P6 — analysis (blocked on P5)

| # | Task | ETA |
|---|---|---|
| 6.1 | Pedestrian counts: temporary counters on Hunter St frontage segments, or the land-use + modelled-alightings fallback — **hypothesis B1 has no observable without one of these** | elapsed weeks; attended 1–2 days |
| 6.2 | Retail floorspace + vacancy audit (`D.retail.vacancy_rate` is `unobtained`; hypothesis B2 depends on it) | attended 1–2 days |
| 6.3 | Open the 143 holdout targets **once**, at the end; score and report | attended 0.5 day |
| 6.4 | Hypothesis tests B1/B2/B3 with every headline bound to its sweep band (SCATS 38% swing, transfer penalty 3–15 min, charging dwell, corridor imputation uncertainty — the closed-as-impossible #27 reports here) | attended 1–2 weeks |
| 6.5 | Per-scenario interactive result explorer (project deliverable 5; replay + live view exist) | attended 3–5 days |

### P7 — write-up (blocked on P6)

| # | Task | ETA |
|---|---|---|
| 7.1 | Findings paper (project deliverable 4) | attended 1–2 weeks |
| 7.2 | Method note on evaluation gaps — the citable SCATS refusal (§9.21) | attended 2–3 days |
| 7.3 | Containerise the reproduction path (project deliverable 1's gap) | attended 1–2 days |
| 7.4 | Publish the data package with the ODbL / CC-BY split visible (deliverable 2; needs the 10 OSM layers from 4.1.1) | attended 1–2 days |

### ⚠ Four tasks PROPOSED FOR DELETION or rework — owner decision pending

Assessed against the goal (*does this help the twin predict ridership per
mode?*) in [`NEXT_AGENT_BRIEF.md`](handover/NEXT_AGENT_BRIEF.md) §7. These four
are the most expensive per unit of goal in the whole plan, and all four are
about the corridor's street life rather than about ridership.

| # | proposal | why |
|---|---|---|
| 5.2 | **DELETE** | A §14 toolchain change invalidates **every prior run**, spent to get pedestrian crossings on one corridor. Record crossings as a stated corridor limitation instead |
| 5.3 | **REWORK** to "stays swept, never pinned" — delete the site visit | One tram parameter, already swept, marginal effect on LR travel time. A physical visit to Civic or Crown St is disproportionate |
| 6.1 | **REWORK** — try the land-use + modelled-alightings fallback only; if it fails, report hypothesis B1 as **untestable** | Elapsed *weeks* to buy pedestrian counters for a secondary retail-outcome hypothesis |
| 6.2 | **REWORK** — scope to what the existing land-use layer supports; commission no audit | Same family as 6.1, same distance from the goal |

### Backlog — do not start before the base works

2014 public timetable (era-1 validation) · LiDAR DTM (corridor grades only —
gradient reaches the behavioural model through nothing, #21) · event attendance
data (event-demand overlay, proposal §10) · socnetsim joint plans (toolchain
change) · a 2013 historical reconstruction (considered and dropped — do not
reopen without the user).

---

## How to resume

**Run `/onboard`** — it executes the sequence below as a skill: the reading in
precedence order, the §0 environment checks, a cross-check of these documents
against live GitHub state, and the six state-of-the-project answers. At
session end, **run `/handoff`** to close out. The manual sequence, for a
session without the skills:

**For P4 specifically, read [`docs/handover/P4_CHECKPOINT.md`](handover/P4_CHECKPOINT.md)** —
the long-form handoff: what has been measured and is true, the traps, the errors
already made and how to drive the harness. **This file stays the source of truth
for the phase board and the deliverable checklist**; the checkpoint does not
repeat them. The dated build narrative is in
[`docs/handover/SESSION_LOG.md`](handover/SESSION_LOG.md) — archive only.

1. Read this file, then [`DECISIONS.md`](DECISIONS.md) §0 (status summary) and
   [`CLAUDE.md`](../../../.claude/CLAUDE.md) (conventions and hard constraints).
2. `python tests/check_manifest.py` — confirms the committed subset is intact.
3. `python src/setup/bootstrap_toolchain.py --verify` — confirms the toolchain and
   **compiles the Java**, or run it without `--verify` to fetch it (~1.4 GiB).
4. `python tests/check_package.py` — needs the full local package, the built networks
   **and** the P3 demand artefacts. **It cannot pass until the harvest above is
   re-run.** Run it before declaring any phase complete.
5. `python src/registry/render_docs.py` and `python src/registry/render_schema.py` after
   any change to `cities/<city>/registry/`, or
   `check_package.py` will report the reference as stale.
6. Branch as `<git-handle>/<short-kebab-description>` (never `claude/*`).
