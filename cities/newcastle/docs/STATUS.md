# STATUS — NewcastleLRSIM

Single source of truth for **where the build is, what's next, and how to resume**. Read
this at session start. **Keep it current in the same commit/PR as the work it describes**
— if a change makes a line here wrong, fix the line in that change, not later.

**Last updated:** 14 August 2026 · branch `praneetdhoolia/mode-choice-specification`

> **This file is a board, not a diary.** The dated build narrative that used to live
> here (944 lines) is archived in
> [`docs/handover/SESSION_LOG.md`](handover/SESSION_LOG.md). Its authoritative
> version is [`DECISIONS.md`](DECISIONS.md) §9.1–§9.36. **Do not append a session
> narrative here again** — record the decision in `DECISIONS.md` and update the board
> lines below that it makes wrong.

---

## ⛔ One thing blocks everything: the OSM harvest is empty

`cities/newcastle/networks/osm/` holds **nothing**. The issue #32 re-harvest was started, produced four
corrupt layers, was deleted, and has **not been re-run**. Until it is:

- nothing downstream of the OSM extract can be rebuilt;
- `tests/check_package.py` **cannot pass**;
- the manifest carries **376** files instead of 386, because the 10 OSM layers do not
  exist to hash;
- `build_basemap.py` runs only against `cities/newcastle/networks/osm_pre_issue32/` (10 layers,
  179 MB, now carrying the generic layer names `roads.osm`, `footways.osm`, ...,
  gitignored) — **do not delete that directory** until a new harvest verifies.

The re-harvest is step **B0** below and is a **point of no return**: it re-runs
pt2matsim, which makes every existing run incomparable
([`DECISIONS.md`](DECISIONS.md) §3.5).

## Where the build is

| | |
|---|---|
| Phase | **P4 (calibration), in progress** — 7 of 9 deliverables met |
| Blocking state | OSM harvest empty; package gate un-runnable |
| Committed data package | **376 files** in [`data/MANIFEST.csv`](../data/MANIFEST.csv) · `check_manifest.py` passes |
| Input registry | **211 fields** — 90 assumed, 51 definition, 28 literature, 21 measured, 17 derived, 4 observed; **7 carry no value** and the resolver refuses to invent one |
| Run inputs assembled | **30** scenario × day-type sets, all carrying the `telemetry` module |
| Runs on disk | **1 convergence pilot in flight** (below), 25% only. The 8 superseded runs are deleted (14.5 GiB — unreadable by `fit.py` after the `newcastle_lga_pct` → `target_lga_pct` rename), and so are the 3 crash-interrupted ones (13.3 GiB). **A run with no `_run.json` is not a result and is not kept.** |
| Open issues | **13** — #5 #9 #14 #20 #24 #28 #29 #30 #31 #32 #34 #36 #37 |
| **Results** | **None. No scenario has been run to a reportable state, and nothing in this repository is an output of the model.** |

### Convergence pilot in flight — issue #5, 25% only

`convergence_pilot_25pct` → `conv1000_25pct_postrestructure`, S2 × WEEKDAY,
1000 iterations, 8 threads, seed 20260810, innovation off at 800. It prints its
own view url when it starts.

Running **before** the B0 batch, deliberately and against the ordering below.
That ordering still stands for **mode share**: it runs on the CURRENT demand,
which B0 replaces, so **no mode share, count or fit statistic may be read from
it**. What survives B0 is the *iteration count* to relaxation, which is the only
thing it is being read for.

**A three-arm attempt (1% + 10% + 25% concurrently) was lost to a machine
crash** and every partial reading was deleted — a run without a `_run.json`
is not a result and was not kept. That attempt is worth recording for one
reason: the three declared heaps total 78 GiB on a 63.5 GiB machine, Windows
grew the pagefile from 8.1 to 19.1 GiB to carry it, and the 10% arm's median
iteration went from ~19 s alone to ~42 s alongside the others. **Do not run the
three arms together.** Iteration count survives contention; iteration duration
does not, and the `convergence_pilot_25pct` overlay description says so too.

**One unexplained event, from the lost 10% arm.** Iteration 4 took **2,415 s**
against a ~20 s median — 37 minutes between `PersonPrepareForSim` and QSim
start, at near-zero CPU with zero log output, confirmed by MATSim's own
`realT=2237s at simT=0.0s`. Not CPU, not GC, not the monitor, and the repo is
not under OneDrive. It did not recur in ~400 iterations. Unattributed — do not
assume it is gone.

### ⚠ The hardcoding ledger — 95 items, audited and NOT yet fixed

```
python src/registry/check_hardcoding.py            report
python src/registry/check_hardcoding.py --strict   exit 1 if anything is found
```

Committed this session and city-agnostic. **37** declared-but-unwired fields ·
**44** MATSim config-template literals · **11** numeric constants in the build
layer · **3** coordinates typed into a script. The full ledger, ordered by what
changes a result, is §2 of
[`NEXT_AGENT_BRIEF.md`](handover/NEXT_AGENT_BRIEF.md); the highest-value items
are below. Two entries — `DETOUR_FACTOR` and `DWELL_CHARGING` — are **deliberate**
divergences pinned by `legacy_symbol`; leave them.

Three that are not merely unwired but **undeclared anywhere**:
`BrainExpBeta = 1.0` (the logit scale — it governs how sharply agents respond to
utility differences), `learningRate = 1.0`, and `lateArrival = -18.0` util/h.
And `fractionOfIterationsToDisableInnovation` is hardcoded `0.8` in the template
while `RUN.replanning.fraction_to_disable_innovation` is read **only** by
`summarise_run.py` to report the cutoff back — **the value the whole relaxation
measurement hinges on decides nothing.**

The issue #12 / #21 / #33 defect class again, in the run-input builder. These
registry fields are read by **no code at all**; `build_matsim_run_inputs.py`
writes the same numbers as literals, and every literal currently **matches** its
registry value — so they are right by accident, and sweeping any of them would
change nothing.

| Field | What actually decides it |
|---|---|
| `RUN.replanning.weights` | `STRATEGIES = [('ChangeExpBeta', 0.70), ...]`, [`build_matsim_run_inputs.py`](../../../src/build/build_matsim_run_inputs.py) L712 |
| `RUN.controler.first_iteration` | literal `value="0"`, L596 |
| `RUN.controler.compression_type` | literal `value="gzip"`, L601 |
| `RUN.qsim.start_time_h` | literal `value="00:00:00"`, L604 |
| `RUN.qsim.end_time_h` | literal `value="30:00:00"`, L605 |
| `RUN.qsim.main_mode` | literal `value="car"`, L609 |
| `RUN.controler.write_plans_interval`, `RUN.replanning.max_agent_plan_memory` | substituted, but from `main()`'s Python defaults (`plan_memory=5`), not from the registry |

`RUN.replanning.weights` is the one that matters: the strategy weights govern how
far co-evolution can move mode share, and the comment beside `STRATEGIES` calls
the mode-choice weight "swept". It is not swept — nothing reads the field.

**Not fixed here on purpose.** The fix edits the builder and requires
regenerating all 30 run-input sets, which would invalidate the pilot now in
flight (§3.5, one build per comparison). Do it with the B0 batch, which
regenerates them anyway. **Beware the near-miss**: `c1['weights']` in the same
builder is a different quantity — behavioural betas (`beta_ivt`, `beta_wait`),
not strategy weights.

## Phase progress

| Phase | State | What is done | What is not |
|---|---|---|---|
| **P0** Scoping | ✅ complete | Base year 2026, zone system, S0–S6 settled (§1) | — |
| **P1** Data acquisition | 🟡 substantially complete | 376 files hashed, provenance-tagged | Field dwell measurement never done. SCATS **refused by policy** (§9.21), journey-linked Opal unpublished — both swept, never pinned. **10 OSM layers absent** pending #32. |
| **P2** Network build | 🟡 complete, will be redone | 1 MATSim base + 4 variants, 15 mapped feeds, 0 unmapped stops, 4 SUMO nets | Corridor kerbside 95% imputed, lane width 98.6%, capacity 100% (#27 closed as *cannot* be closed — B3 must report them as uncertainty). **#32 re-harvest will rebuild all of it.** |
| **P3** Demand synthesis | 🟡 complete as built, **will be superseded** | 612,680 agents, 521,502 weekday persons, 3 day types, 30 run-input sets | Freight, business travel and boundary through traffic absent (#24, #20). Destinations too far (#30). Bike ownership universal (#29). 348 agents live a 30-hour day (#37). |
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
| **0d** | **The missing demand.** In value order: **(1)** boundary/through traffic — the M1 gap, external-station matrix seeded from cordon counts, touching no holdout row; **(2)** work-related business travel — an **observed HTS purpose** the model does not generate; **(3)** freight — a heavy-vehicle layer from the measured 6.52% heavy share. **Deferred to P5:** SUMO pedestrian crossings, which need a SUMO version change and are therefore a §14 toolchain change. | Each adds demand and will move mode share. Calibrating before them means re-calibrating after them. |
| **0e** | **Housekeeping.** ALREADY SATISFIED, the entry was stale (§9.25). | `overpass.py` annotates both layers *"for the run replay basemap only"* and `src/analyse/build_basemap.py` consumes them, feeding `build_replay_page.py`. Used **and** labelled; no work outstanding. |
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

### Carried over from P0–P2 — work no deliverable owned

Verifying the phase board found work carried from earlier phases that was listed
in [`DECISIONS.md`](DECISIONS.md) §13 and owned by nothing. It is owned now.
**Two are urgent for reasons that did not apply when they were first written**
(§9.22).

| | Carried item | From | Priority | Why now |
|---|---|---|---|---|
| - | GTFS-Realtime collection | P1 (§13.10) | **settled - dropped** | Own collection was built and reverted. TfNSW's **Historical GTFS Realtime** archive covers **Metro and Ferry only** (verified against the live API: Metro and Ferry return files, every light rail and bus naming returns none), so it cannot backfill Newcastle - but nor is a months-long rolling stream justified before the published catalogue is worked through. Issue #26 closed as not planned; the catalogue assessment is §9.23. |
| **#27** | **Corridor road-attribute correction** | P2 (§13.4) | 🟠 **high** | **B3 is "the decisive test of Claim B" and rests on lane loss, banned turns and kerbside parking removal.** Measured over the 714 corridor edges: kerbside **95% imputed**, lane width **98.6%**, capacity **100%**, turn lanes **90% absent**. §2.5's 87.5%-observed figure is about the **40 trunk edges**, not these. |
| **#34** | **The CBD box: a fifth hand-drawn rectangle** | P1/P2 (found at §9.31) | 🟠 **high** | `CBD = dict(s=-32.9450, ...)` in `build_landuse_parking.py` selects the buildings whose floorspace `D1_frontage_segments.csv` attributes per 50 m — **the unit of test for hypothesis B1**. Same class as #32 and the `PARK_ZONES` boxes just removed. Measure the damage before fixing; D1 is land use, so it does **not** sit behind the B0 point of no return. |
| — | Charging dwell field measurement | P1 (§13.2) | 🟡 medium | Physical, one visit to Civic or Crown Street. Worth 11% of end-to-end run time; `A.lightrail.dwell_charging_s` stays `unobtained` and swept until then. The GTFS-Realtime fallback is **gone** (§9.23): TfNSW's historical archive excludes light rail, so field measurement is now the only route. |
| — | ABS journey-to-work SA2×SA2 table | P1 (§13.11) | 🟡 medium | **Obtainable** — a standard TableBuilder extract, not a request. Settles `B.external.interaction_rate`, currently assumed 0.08. **Folded into deliverable 0b.** |
| — | Day-of-week travel split | P1 (§13.12) | 🟡 medium | The Saturday:Sunday division is the last assumed part of the day-type shape. RMS hourly counts carry dates, so this is derivable. **Folded into deliverable 0b.** |
| — | Pedestrian counts | P1 (§13.6) | 🟡 medium | **B1 has no observable at all without them** — none are published for Newcastle. §7.2's fallback is temporary counters on Hunter St, or calibrating from land use and modelled alightings. A P6 blocker, not a P4 one. |
| — | Retail floorspace and vacancy audit | P1 (§13.7) | 🟡 medium | `D.retail.vacancy_rate` is `unobtained` and **B2 depends on it**. A P6 blocker. |
| — | 2014 public timetable | P1 (§13.8) | 🟢 low | Validates the era-1 reconstruction. Nothing currently depends on it. |
| — | LiDAR DTM for the CBD | P1 (§13.5) | 🟢 low | **Demoted.** It was to replace GLO-30 "where gradient actually matters" — but #21 established gradient **reaches the behavioural model through nothing**. It matters only for corridor grades now. |
| — | Event attendance data | P1 (§13.9) | 🟢 low | Feeds the event-demand overlay, a proposal §10 extension. Out of scope until the base works. |
| — | *"Requests lodged"* (P0 output) | P0 | ✅ **settled** | SCATS is **refused by policy** and documented (§9.21); journey-linked Opal is unpublished and its §7.2 fallback is now **deliverable 8**. Nothing further to lodge. |

**Priority rule applied here:** urgency is set by *whether waiting destroys the
option*, not by how much each is worth. #26 was first on that rule and has since
been **dropped** (§9.23) - the option it protected turned out not to exist for
Newcastle. **#27 is now first**, because it gates the decisive test of Claim B.
Everything marked 🟡 blocks P6, not P4, and must not be allowed to reorder
deliverable 0.


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

## Next action

**B0 — re-run the OSM harvest (#32), then rebuild the layers that depend on it.**
It is first because it is the point of no return: it re-runs pt2matsim and makes
every existing run incomparable, and #30, #24 and #20 all regenerate B2 anyway, so
they belong in the same batch or B2 is rebuilt twice.

```
python cities/newcastle/extract/overpass.py   # 10 layers x 8 tiles; expect 504s and mirror rotation
                                        # resumes from cached tiles
```
then, in order: `build_network_layers` → `attach_gradient` → `attach_speed_zones` →
`build_corridor_road_attributes` → `build_matsim_network` → `build_landuse_parking` →
`build_zone_attractions`.

**Verify before building on it — this is the whole point of #32:**

- every new layer must be **larger** than its `cities/newcastle/networks/osm_pre_issue32/` counterpart
  (a layer that shrinks when its extent doubles cannot be right — that is exactly how
  the corrupt merge was caught);
- `osm_tiles.verify()` must pass on each;
- the **87 core SA1s / 31,940 agents** must now be inside the road network. Check it
  explicitly.

A bigger network is more memory. Re-measure before assuming a 10% sample still fits.

**Then, in the same batch** (each regenerates B2, so doing them separately rebuilds it
several times): #30 destination placement, #29 bike availability, #24 freight, #20
boundary through traffic and #37 the 30-hour day. **#36 is closed** — the `CITYSIM_*` prefix
and `src/java/citysim/` landed with the city restructure below.

**Only after that** is it worth re-measuring the iteration count (#5), because the batch
moves the landscape it would be measured on.

### Housekeeping that is safe to do at any time

- ~~`results/live_demo` holds 9.8 GB of `output/ITERS`~~ — **done**: all 8 superseded runs
  were deleted outright rather than pruned, reclaiming 14.5 GiB. They post-date nothing
  that needs them: the metrics key rename made every one unreadable by `fit.py`.
  `prune_run.py` remains the right tool for a run whose metrics are still wanted — it
  refuses until `extract_metrics.py` has run, by design.
- **Any replay page built before 14 August is wrong** and must be rebuilt: the basemap
  packing defect (§9.36) broke every area fill.
- `check_package.py` lost its coverage of the live view when `run_monitor.py` was deleted.
  Restore it against `run_view.py` / `summarise_run.py`.

---

## How to resume

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
