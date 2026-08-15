# Brief for the next agent — the build is done; MEASURE IT

*Written 16 August 2026, after PR #38 merged the issue-32 rebuild to `main`.
This is a HANDOVER, not a source of truth: where it disagrees with
[`STATUS.md`](../STATUS.md), [`DECISIONS.md`](../DECISIONS.md) or
[`.claude/CLAUDE.md`](../../../../.claude/CLAUDE.md), those win. Paste it whole
to start a session cold.*

---

═══════════════════════════════════════════════════════════════════════════════
§0  DO THIS FIRST
═══════════════════════════════════════════════════════════════════════════════

```bash
python src/setup/bootstrap_toolchain.py --verify   # ~1 min, COMPILES THE JAVA
python tests/check_manifest.py                     # committed subset intact
```

**Check whether a run is already finished or in flight before starting one:**
look in `results/` for directories with a `_run.json`, and for a live `java.exe`.
`results/smoke_postrebuild/` exists and is a plumbing test, not a result.

If nothing is running, your first command is the issue #5 pilot:

```bash
python run.py --scenario S2 --day WEEKDAY --fraction 0.10 --iterations 1000 \
    --xmx 30g --tag conv1000_10pct
```

- **~10 h alone on this machine** (29.9 s/iteration at 10% on the OLD network;
  the smoke run measured the new network ~3% slower at 1% — re-time from the
  run's own series, not from this estimate).
- **ONE ARM AT A TIME.** Three concurrent arms once declared 78 GiB of heap on
  63.5 GiB of RAM and paged the machine. Iteration *count* survives contention;
  iteration *duration* does not.
- Threads come from the registry (**10** — part of the run identity; do not
  pass `--threads 8` "for comparability", every pre-rebuild curve is void).
- The run prints its own live-view url before MATSim starts.
- The 25% arm (~16-20 h) only if the 10% curve is ambiguous.
- **A run with no `_run.json` is not a result and is not kept** — delete such a
  directory AND its timing series together.

**What the pilot is:** the measurement of how many iterations THIS model needs
to relax. `RUN.controler.last_iteration` is `unobtained`; shipped configs carry
250 — the sweep floor, the largest value MEASURED insufficient — as a visibly
provisional value. On the pre-rebuild model, 100→250 moved a mode 13.2 points,
250→500 6.8, 500→800 3.0, flat only from ~900; innovation switches off at 0.8 ×
horizon, leaving a measurable post-innovation drift window that
`summarise_run.py` scores against the declared
`RUN.relaxation.drift_tolerance_pp`.

**When it finishes:** §3 is your whole job.

---

═══════════════════════════════════════════════════════════════════════════════
§1  THE MISSION, AND WHERE IT STANDS
═══════════════════════════════════════════════════════════════════════════════

| # | Goal | Done looks like | State |
|---|---|---|---|
| **G1** | **Answer the counterfactual.** What did the Newcastle light rail do to journey cost, accessibility, mode share and city-centre footfall, against the alternatives available in 2013? | A calibrated base, S0–S6 run to relaxation, the 143 holdout targets opened once, a findings paper stating its uncertainty bands | **The inputs are finally trustworthy; no run has reached relaxation.** This is the work |
| **G2** | **A city-agnostic simulator with a full input schema** | A second city runs the framework unchanged | ✅ **Exercised**: `check_city_agnostic.py`, 13 assertions, CI on every push |

Every discipline here — the sealed holdout, the declared sweeps, the refusal to
pin an unobserved input — descends from one fact: **9 of 10 rail projects
overestimate patronage, by an average of 106%** (Flyvbjerg, 210 projects). A
flattering answer is the EXPECTED failure. The law that guards it: **every
value the model uses is DECLARED in `cities/<city>/registry/` and REACHES the
model through the resolver** — the ledger is 0, `--strict` gates CI, and reach
is proven by perturbation (69/69), not claimed. To add a MATSim parameter,
declare a field with a binding; there is nowhere to type a literal and
`closure()` fails the build if you find one.

---

═══════════════════════════════════════════════════════════════════════════════
§2  WHAT IS DONE — do not redo any of it
═══════════════════════════════════════════════════════════════════════════════

**The 16 August rebuild (PR #38) crossed the point of no return once and paid
for everything:**

- **Harvest (#32 closed):** 10/10 OSM layers over the boundary-derived extent.
  Core SA1s without a road node **99 → 4, holding 0 agents** — all 35,365
  stranded agents are on the network. `osm_pre_issue32/` is the pre-repair
  reference; do not delete it.
- **Network:** 181,892 links at the declared speeds; **all 15 GTFS feeds mapped
  in ONE pt2matsim build, 0 unmapped stops each**. One build per comparison
  (§3.5) — never re-run the mapper casually.
- **Demand, one regeneration, five fixes** (DECISIONS.md §9.38–§9.41):
  - per-(purpose × home LGA) destination decay — all 30 cells realise their own
    LGA's HTS distance (#30 closed);
  - the 30-hour-day cap — **zero** midnight collisions, all three day types
    (#37 closed);
  - through-traffic tier at 3 cordon gates, car-locked, seeded from calibration
    counts only (#20 closed pending run confirmation, see §3);
  - bike availability declared and drawn at a swept 0.50 (#29 closed;
    **sizing** is calibration work, see §3);
  - business travel deliberately NOT rebuilt — already generated at 2.11%
    against 2.0% observed.
- **DEM tiles derived from the boundary** (the tile list had the same typed-in
  extent disease as the old harvest box); gradient coverage 100%.
- **#34 closed by measurement:** the CBD box clips nothing (nearest out-of-box
  building 281 m from any segment vs a 50 m ceiling), and it silently does
  name-disambiguation work — any derived replacement must keep a name guard.
- **Gates:** `check_package` **1,452 ALL PASSED** (2 owned warnings);
  manifest **391**; smoke run `smoke_postrebuild` rc=0.
- **A bare `python run.py` runs the default 25% × 1000 from the committed
  `default_25pct` overlay** — the point values live in the overlay, not the
  script. `--run-config smoke` is the plumbing test.

**Phases:** P0 ✅ · P1 ✅ (for P4's needs) · P2 ✅ rebuilt · P3 ✅ regenerated ·
**P4 in progress, 7 of 9** (deliverables 0 and 5 open) · P5/P6/P7 not started.
The full numbered plan with ETAs is in `STATUS.md` — this brief repeats only
your lane.

**Open issues — exactly six, all live:** #5 (iteration count → YOU, first),
#9 (ASC re-solve, after #5), #14 (calibrated base decision), #24 (freight, the
next focused PR), #28 (ride residual → run measurement), #31 (driver-capacity
decision). #20/#29/#30/#32/#34/#36/#37 are closed — each closure comment states
its REOPEN IF condition; honour them.

---

═══════════════════════════════════════════════════════════════════════════════
§3  ★ YOUR JOB: BENCHMARK AND EVALUATE THE RUNS
═══════════════════════════════════════════════════════════════════════════════

The declared pipeline — **the ONLY route to a reportable number**:

```bash
python src/analyse/extract_metrics.py --run results/<tag>
python src/calibrate/fit.py           --run results/<tag>
python src/calibrate/report.py        --run results/<tag> --out cities/newcastle/docs/audit/CALIBRATION_REPORT.md
```

`summarise_run.py` closes the run out (relaxation light against the declared
tolerance, accounting closure). Read `_metrics.json`, never `modestats.csv`
(chosen mode ≠ completed trips).

### 3.1 The relaxation verdict (#5) — the number everything waits on

From the pilot's own mode-share series: where does per-mode drift fall inside
`RUN.relaxation.drift_tolerance_pp` after innovation stops? Declare the
measured iteration count in the registry (with the pilot as provenance), update
the shipped default, log it in `DECISIONS.md`, close #5. If 10% has not settled
by 1000, say so and run the 25% arm before declaring anything.

### 3.2 The evaluation slate — run these measurements on the first relaxed run

| Measurement | Compares against | Owns |
|---|---|---|
| Mode share, **`target_lga_pct`, linked** | HTS Newcastle LGA: car 59.0 / ride 20.6 / walk 13.4 / pt 3.8 / bike+other 3.2 (targets V202–V207, calibration rows) | the headline gap |
| Ride vs car realised speed **in matched distance bins** — NEVER aggregate means (that produced a withdrawn headline once) | ride/car ≤ ~1.0× per bin | #28 residual: close it or size it |
| Bike and walk shares | observed 3.2 / 13.4 | sizing `B.population.bike_available_rate` (#29 closure comment) — a calibration move on a DECLARED sweep, logged in DECISIONS.md |
| Sub-1 km trip share, Newcastle LGA residents | the HTS-implied short-trip mass (walk mean 0.7 km at 13.4%) | #30's reopen condition |
| **V113 (M1 at Wyee) modelled volume** | observed 48,016 AADT; must be materially non-zero | #20's reopen condition; boundary count bias |
| Count fit over the 34 calibration stations, light-vehicle | `fit.py` output | notes for #24: what freight's absence costs |
| Stuck-agent panel from telemetry (car vs walk/pt separately) | smoke and prior notes: ~1,500/iter walk+pt stuck was seen pre-rebuild and never explained | a defect hunt if it persists |
| Wall-clock + heap at 10% | old: 29.9 s/iter, 18.4 GiB | re-derive the memory model before any 25%+ run |

**Context that sets the bar:** AToM Melbourne (MATSim, 10%) sits 1–2 points per
mode against observation, active modes worst. This model's pre-fix distance was
**33.8 pp total absolute deviation at 1,000 iterations**. The five fixes exist
to close structural gaps — measure how much they closed, mode by mode, and
report the residual honestly. **Do not read a good headline as calibration**:
nothing is calibrated until deliverable 5.

Write the evaluation up in `cities/newcastle/docs/audit/` (the
`ISSUE_VERDICTS.md` addendum pattern — claim, measurement, verdict), update the
board, and close or reopen issues on the evidence.

### 3.3 Then, in order

1. **#9** — re-solve `asc_car_passenger` at the settled horizon
   (`solve_asc_ride.py`, deterministic, resumable).
2. **#14** — the calibrated base. §8.5's FIRST branch: estimate ASCs on era 3
   (2018) and HOLD FIXED. **LOG THE DEPARTURE BEFORE ANY RESULT IS SEEN.**
   Deliverable 0b derivations (JTW table, day-of-week split, VOT — see the
   STATUS plan 4.3) ride along.
3. **#24** — freight, as its OWN focused PR: a real `truck` mode with a vehicle
   type and PCE (fields + emitter + vehicles file), NOT inflated car agents —
   they would contaminate the light-vehicle count comparison. #31's decision
   (`C.constraint.passenger_per_driver` is declared and waiting) belongs in the
   same modelling sitting.
4. **P5** — SUMO harness and scenario runs, per the STATUS plan. SUMO has been
   built six times and simulated zero times, deliberately: do not couple it to
   an uncalibrated demand model.

---

═══════════════════════════════════════════════════════════════════════════════
§4  WHAT INVALIDATES YOUR EVALUATION
═══════════════════════════════════════════════════════════════════════════════

- **Nothing pre-rebuild is comparable to anything post-rebuild.** Different
  network build, thread count, road speeds, demand. Historical numbers in old
  docs are context, never baselines.
- **NEVER compare across sample fractions.** 1% produces spurious spillback
  (car stuck 1,028 at 1% vs 7 at 10%, measured) — it is a plumbing fraction.
- **`target_lga_pct`, never `all_residents_pct`** — the latter inverted a
  headline once.
- **THE 67/143 SPLIT IS PRE-REGISTERED.** Never calibrate on, re-split, or peek
  at a holdout row; `fit.py` enforces it. Need one to diagnose? **SAY SO AND
  STOP.** The holdout opens ONCE, at the end of the study.
- **One build of the network per comparison** (§3.5). All 15 feeds were mapped
  in the 16 Aug build; every scenario comparison uses it.
- **No invented data.** Unmeasured values are assumed or modelled, labelled,
  swept, and recorded in `DECISIONS.md`. A calibration move happens on a
  declared sweep and is logged before its result is quoted.
- **A run without `_run.json` is not a result.** Delete it and its timing
  series together.

---

═══════════════════════════════════════════════════════════════════════════════
§5  EXACT STATE — 16 August 2026, post-merge
═══════════════════════════════════════════════════════════════════════════════

| | |
|---|---|
| `main` | holds the merged rebuild (PR #38); CI fully green |
| Registry | **297 fields**; ledger **0** (`--strict` in CI); reach **69/69** |
| Manifest | **391 files** · `check_package` 1,452 ALL PASSED (2 owned warnings) |
| Network | 181,892 links; 15 mapped feeds, 0 unmapped stops |
| Demand | 612,668 agents; WEEKDAY 542,231 persons = core + 5,467 external + 17,955 through; zero midnight collisions |
| Run inputs | 30 scenario × day-type sets, emitted 16 Aug |
| `results/` | `smoke_postrebuild` only — a plumbing test |
| Open issues | **6** — #5 #9 #14 #24 #28 #31 |
| **Results** | **NONE. Nothing in this repository is an output of the model.** |

### Bootstrap reading, in this order

```
cities/newcastle/docs/STATUS.md              the board + the numbered plan
cities/newcastle/docs/audit/ISSUE_VERDICTS.md   verdicts + post-rebuild addendum
cities/newcastle/docs/DECISIONS.md           START AT ITS INDEX; 9.38-9.41 are the new fixes
.claude/CLAUDE.md                            conventions + hard constraints
cities/newcastle/docs/handover/P4_CHECKPOINT.md  older long-form context (12 Aug; STATUS wins)
```

---

═══════════════════════════════════════════════════════════════════════════════
§6  DECISIONS TAKEN — do not re-litigate
═══════════════════════════════════════════════════════════════════════════════
• DELIVERABLE 5 TAKES §8.5's FIRST BRANCH: ASCs on era 3 (2018), HELD FIXED.
  **LOG THE DEPARTURE BEFORE ANY RUN.**
• SCATS REFUSED BY POLICY, citable (§9.21) — swept, never pinned. Same for
  journey-linked Opal (transfer penalty stays a 3–15 min sweep, §9.32) and
  charging dwell (field measurement is the only route left).
• PRE-TRAM SIGNAL COUNT STAYS 14. The 30 h qsim window is CORRECT.
• GRID 140 → 28; `n_replications` stays 30 until seed variance is MEASURED.
• The parking ramp's mall-pricing limitation is known; the contiguity fix was
  BUILT AND REJECTED (it exempts the University and John Hunter, which charge).
• The city restructure is settled. ONE pilot arm at a time is settled.
• Northern through exits stay ungated this build (§9.41) — reachable by the
  `through_outside_min_m` sweep, revisit after #5.
• DECLINED, do not re-raise: touching the 143 holdout targets; deleting the 13
  Opal card-type rows; separate taxi/motorcycle/rideshare modes; weather in
  mode choice (a wet-day sensitivity arm exists instead).

⚠ **#31 trap, verbatim from the audit:** eqasim's `PassengerConstraint` is a
trip-level biconditional on `getInitialMode()`; no driver is consulted.
Adopting it PINS THE RIDE SHARE TO THE B2 SEED. **Do not add `ride` to
`chainBasedModes`.** Its mode string is `car_passenger`, hard-coded — a copied
constraint compiles, runs, constrains nothing and reports success.

---

═══════════════════════════════════════════════════════════════════════════════
§7  TRAPS — each of these has already cost a day
═══════════════════════════════════════════════════════════════════════════════
1. **BASH HEREDOCS MANGLE BACKSLASH ESCAPES.** Write code with the Write/Edit
   tool. `io.open(p,'w')` truncates before the write fails.
2. **`compileall` does not catch a NameError.** A build script can pass every
   check and die on its first statement.
3. Everything is seeded **20260810**. After ANY registry edit: regenerate
   `render_docs.py` AND `render_schema.py`, or CI fails on staleness. After any
   data change: `normalise_eol.py` → `build_manifest.py` → `normalise_eol.py`.
4. **The layers contract carries no machine state** (presence is a report, not
   content) — that is what lets CI verify it on a data-less checkout. Do not
   put an `os.path.exists` back into a committed generated file.
5. `pkill` does not work here; use PowerShell `Stop-Process` and VERIFY the
   process died.
6. Branch `<git-handle>/<short-kebab>`, never `claude/*`. No attribution
   trailers, no session links. Commit messages state what changed in the MODEL
   or the DATA. **Keep `STATUS.md` current in the SAME commit.**
7. **Verify the consumer, not the mechanism.** Every signature defect here — a
   declared value reaching nothing, a default right by accident — was caught by
   arithmetic or an audit, never by reading code. Establish reach by changing
   the value and watching the output change.
8. **Reproduce a defect before attributing it**, and when you fix one, write
   the check that would have caught it.
