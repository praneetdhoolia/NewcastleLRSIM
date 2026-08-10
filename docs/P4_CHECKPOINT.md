# P4 checkpoint — read this before touching anything

Handoff for **P4 calibration**, branch `praneetdhoolia/p4-calibration`, PR #4.
[`STATUS.md`](../STATUS.md) stays the short live status; this is the long form:
what was found, what was decided and why, what is built, what is open, and the
traps waiting for whoever picks it up.

**One-line state:** the model runs, the inputs are correct for the first time,
nothing has been fitted to any calibration target, and P4 is blocked on two
decisions the next session should take early.

---

## 1. The short version

| | |
|---|---|
| Started as | P4 calibration: fit the base to observed counts, Opal boardings and run times |
| Actually became | Removing **seven** defects that made calibration impossible, then building the instrument |
| Deliverables complete | **3 of 7** (run harness, metric extraction, fit statistic) |
| Fitted to a calibration target | **Nothing. Not once.** |
| Package checks | 556 → **860**, 1 standing warning |
| Commits | 5, all pushed |
| Blocked on | the iteration count (§5.1) and the run-budget cut (§5.2) |

**Nothing in the repo is a result.** No scenario has been run to completion at a
defensible iteration count, and no fit statistic has been computed on a converged
run.

---

## 2. The seven defects, and the pattern they share

Every one of these produces a **confident wrong answer** rather than an obvious
failure, and every one was invisible to a check that looked structurally sound.
That pattern is the single most important thing to carry forward.

| # | Defect | Reach | Recorded |
|---|---|---|---|
| 1 | Day-type filter dropped the schedule **doctype**; MATSim selects its reader from it | all 30 run-input sets | §9.4 |
| 2 | Filtering orphaned **stop facilities and transfer relations**; SwissRailRaptor NPEs | all 30 | §9.4 |
| 3 | Kerbside patch appended a **second `<attributes>` block**; network DTD rejects it | **6 of 10** run networks — exactly the six carrying an E1 road change | §9.4 |
| 4 | `ride` declared a network mode **no link permitted** | every config | §9.6 |
| 5 | `subtourModeChoice` unconfigured, so a `ride` subtour was an **absorbing state** | ride share = seed, to five decimals | §9.6 |
| 6 | `considerCarAvailability` defaulted false — **B1's car availability ignored** | all mode choice | §9.6 |
| 7 | Day-type filter keyed on **route id**, but pt2matsim groups trips by stop sequence, not service | **29.5% of departures in the wrong day type; the with-tram scenario had no tram on a weekday** | §9.9 |

Plus, in the validation layer: the 119 `road_aadt` target **values** were the mean
of `ALL DAYS` with the peak-period rows — 0.58–0.71× the true figure, and not a
constant factor (§12.2).

### The failure mode, stated plainly

**An invariant that is true but is not the one that matters.**

- Defect 7's check asserted the day-type split *partitions the route set exactly*
  — 1,231 + 291 + 192 = 1,714. Perfectly true. Partitioning routes is not
  partitioning service, because a route is not day-type homogeneous.
- The P3 checks verified the run inputs exhaustively **as data** and never asked
  whether a simulator could read them (defects 1–3).
- My own first cut of `fit.py` scored 35 targets and listed 16 reasons out of 67,
  leaving 16 neither scored nor explained — a statistic that looked complete
  because nothing contradicted it. It now **asserts** `scored + explained ==
  total` and exits otherwise.

Two of the seven were found only by **building the thing downstream that consumes
the output**: defect 4 by running the shipped config, defect 7 by extracting
metrics and seeing zero light rail boardings. That is the cheapest known detector
for this class, and it argues for building consumers early rather than late.

**There is an open proposal to spend a deliberate pass hunting this class before
the calibration loop is built on top** — see issue *"Audit pass: invariants that
are true but not the one that matters"*.

---

## 3. What was measured (not assumed)

### 3.1 Run cost, on this machine — §9.5

24 cores, 63.5 GiB. S2 × WEEKDAY, nested subsamples, 16 threads.

| Sample | Persons | Steady per-iteration | Peak resident |
|---|---:|---:|---:|
| 1% | 5,209 | 9.8 s | 9.8 GiB |
| 10% | 52,758 | 29.9 s | 18.4 GiB |
| 25% | 131,291 | ~64 s | 31.5 GiB |

Large fixed cost, near-linear slope: **time ≈ 3.1 s + 268 s × fraction**,
**memory ≈ 9.6 + 87 GiB × fraction**. So ~4.5 min/iteration and **~97 GiB at
100% — a full-population weekday run does not fit in 63.5 GiB**. Practical
ceiling ≈ 40%.

### 3.2 Seed dependence and convergence — §9.7

Two 250-iteration runs at 1%, identical but for the initial mode draw:

- seed influence **decays but is not gone**: a 42.1 pp gap on car share closes to
  5.4 pp;
- **the model does not converge.** Innovation switches off at iteration 200;
  ride share still moved 0.619 → 0.664 over the last 50 iterations with no new
  plans being created. `lastIteration=100` is far too low and **250 is also too
  low**.

### 3.3 Observed vehicle occupancy — §9.8

From HTS driver and passenger trip counts, Newcastle LGA:

| Year | 16/17 | 17/18 | 18/19 | 19/20 | 22/23 | 23/24 | **24/25** |
|---|---:|---:|---:|---:|---:|---:|---:|
| Occupancy | 1.3174 | 1.2838 | 1.2493 | 1.2845 | 1.3940 | 1.3438 | **1.3503** |

Sweep 1.2493–1.3940 = the observed spread, not a chosen interval. The
unconstrained model produced **5.52 people per car**.

---

## 4. Decisions taken, and where the rationale lives

| Decision | Where | One-line rationale |
|---|---|---|
| Traffic-count targets are **`WEEKDAYS`**, two-way, all classes | §12.2 | The old value averaged daily totals with peak-period rows. 119 values changed; **split untouched** |
| **No contemporary bus target added** | §12.4 | MATSim collapses all PT into one `pt` mode with one constant, so it would identify nothing the LR level and PT mode share do not already |
| Seed is **uninformed** (uniform over usable modes, car 14.3% vs target 59.0%) | §9.6 | A model that starts at the answer cannot be said to have found it. Informed seed retained behind `--seed-mode informed` |
| `ride` distance cost **0.0**, not half car's | §9.8 | A vehicle's cost is paid once; at occupancy 1.35 charging both occupants made aggregate cost 1.35× real. Zero is the only derivable value |
| `asc_car_passenger` **constrained to observed occupancy** | §9.8 | §8.5's second branch — *"constrain them and report the constraint"*. The constrained constant is **car passenger**; `asc_lr`/`asc_bus`/`asc_rail` are untouched, so the effect under test is untouched |
| Modelled vehicles = **car legs alone** | §12.2a | Observed vehicle trips *are* driver trips, so a teleported `ride` correctly adds none |
| Output compression **gzip**, not zst | §9.8 | The repo declares no `zstandard` dependency; an undeclared one is a reproducibility hole |

### Values derived from data, with their sweeps

| Value | Value | Sweep | Derived from |
|---|---|---|---|
| Vehicle occupancy | 1.3503 | 1.2493–1.3940 | HTS driver/passenger trip counts, 7 survey years |
| Heavy-vehicle share | 0.0652 | 0.0129–0.1529 | RMS classified counts, 23 of 119 stations, weekday |
| HTS mode share (linked, Newcastle LGA) | car 59.0 / ride 20.6 / pt 3.8 / walk 13.4 / other 3.2 | — | HTS `MODE_SHARE`, derived not typed |

**Rule that bit twice:** a value recorded only in prose breaches the project's own
sweep-range rule *and* slips past the test that enforces it. Anything assumed goes
in a `params/*.json` artefact.

---

## 5. Open decisions — take these first

### 5.1 The iteration count (blocking everything downstream)

100 and 250 are both measurably too low (§9.7). Every remaining deliverable needs
a converged run, and the run budget cannot be sized without this number.

The open question is whether the non-convergence was **caused by** ride
dominance, in which case constraining the ride constant may largely cure it. The
three candidate runs in flight at checkpoint time are the first evidence.

### 5.2 The run-budget cut (blocking P5 sizing)

1,400 sweep + 300 headline runs across three day types is **5,100 run-days ≈ 765
days of wall clock at 25%**. Three orders of magnitude out. It closes only by
cutting **sweep breadth, replications and day types** — *not* sample fraction,
which is the weakest lever because cost is sublinear in it and precision is not.
No cut has been made.

### 5.3 The audit pass (proposed, not decided)

See §2. Seven defects, every one invisible to a sound-looking check, two found
only by building the consumer. Whether to spend a deliberate pass on this class
before building the calibration loop is a cost/benefit call for the next session.

---

## 6. What is built, and how to drive it

```
src/run/
  sample_population.py    nested hash subsample + transit seat capacity scaled
                          with the fraction (without which a 10% sample gives
                          every bus 10x its real capacity)
  run_matsim.py           deterministic, resumable, records its own parameters.
                          --iterations has NO default, deliberately (5.1)
src/calibrate/
  measure_mode_constraints.py   HTS -> params/C4_mode_constraints.json
  solve_asc_ride.py             solves asc_car_passenger against observed occupancy
  fit.py                        fit statistics, CALIBRATION ROWS ONLY
src/analyse/
  map_sa1_to_lga.py       ABS LGA boundaries -> data/processed/zones/sa1_to_lga.csv
  map_count_stations.py   119 stations -> links, by road name AND proximity
  extract_metrics.py      mode share by LGA, PT boardings by line, link volumes
```

### The pipeline, end to end

```bash
python src/run/run_matsim.py --scenario S2 --day WEEKDAY \
    --fraction 0.01 --iterations 250 --threads 7 --xmx 12g \
    --set ride.constant=-4.35 --tag my_run
python src/analyse/extract_metrics.py --run my_run     # -> results/my_run/_metrics.json
python src/calibrate/fit.py          --run my_run      # -> results/my_run/_fit.json
```

`run_matsim.py` **resumes**: re-invoking a completed run is a no-op. A run that
died leaves no `_run.json` and repeats from the start (MATSim has no mid-run
checkpoint).

### Holdout safety, by construction

`fit.py` filters `split == 'calibration'` at read time and raises if anything
else survives — a holdout value is never in memory. `extract_metrics.py` and
`solve_asc_ride.py` never open `validation_targets.csv` at all. **The split is
67/143 and `check_package.py` asserts it exactly**, so a target-value correction
cannot quietly move a row between sets.

---

## 7. What the 67 calibration targets can actually do — §12.1

`fit.py` scores **35** and explains **32**, reconciled by assertion.

| Block | n | Verdict |
|---|---:|---|
| `road_aadt` | 34 | Scored at **30**; 4 stations lie outside the modelled network |
| `lr_cardtype_share` | 13 | **Identifies nothing** — no fare-product dimension in MATSim, and 31.7% of the mix is contactless payment, an instrument not a person attribute |
| `hts_mode_share` | 12 | Only the **2024/25 six** apply to a 2026 base; `Walk linked` is structurally 0.0 → **5 scored, 4 free degrees of freedom** |
| `lr_boardings_*` | 3 | V001 and V002 are the same datum ÷ 30.4. All pre-pandemic except V003, which is monthly and needs all three day types composed |
| `bus_boardings_monthly_mean` | 1 | 2019 only, pre-pandemic |
| `lr_share_of_local_pt_boardings` | 1 | Algebraically V001/(V001+V023). **Never calibrate A1 against 20.8%** |
| `lr_scheduled_runtime` | 2 | A schedule **input**; MATSim reproduces it by construction. A SUMO target |
| `lr_alignment_length` | 1 | Geometry, already satisfied |

**Effective independent information: ~4 mode-share degrees of freedom, one
contemporary patronage level, 30 usable counts.** Any statement of fit must name
its targets; "fits 67 targets" is not what this measures.

**The holdout is not a contemporary test set** either: 85 of its 143 targets are
traffic counts from 2007 (×2), 2008 (×21) and 2010 (×62) — §12.3.

---

## 8. Traps for the next session

1. **`lastIteration=100` is shipped and known wrong.** Left in place rather than
   replaced by another unjustified number. A standing warning fires on every
   `check_package.py` run.
2. **The ASC solve is provisional.** It runs at a fixed 250-iteration protocol
   which is not equilibrium. Re-solve once 5.1 is settled.
3. **One build of the network per comparison** (§3.5) still binds. The day-type
   fix operates on the already-mapped schedule; **never re-run the mapper.**
4. **A scenario runs on its own `schedules/<S>/network.xml.gz` + the E1 patch**,
   never on `networks/matsim/variants/` (§9.3).
5. **Transit capacity floors at 1 seat** below ~1.5% sample, so capacity is
   systematically too generous at small fractions. Fine while crowding scoring is
   off; revisit if it is ever enabled.
6. **`bike` carries HTS "Other"**, which also holds taxi, motorcycle and
   rideshare. An imperfect map, stated in `fit.py` rather than hidden.
7. **Runs made before `compressionType=gzip`** write `.zst`. `extract_metrics.py`
   accepts them only if `zstandard` happens to be installed, which the repo does
   not require.
8. **Everything seeded 20260810.** Run `normalise_eol.py` before
   `build_manifest.py`, then again after — `build_manifest.py` writes CRLF.

---

## 9. Open issues

Filed on the repo, labelled `P4` / `blocker` / `decision-needed` /
`data-quality` / `modelling-limitation` / `carried-forward`. GitHub issues are
repo-level, not per-branch; all of these arose on
`praneetdhoolia/p4-calibration` and reference PR #4.

| # | Title | Why it is open |
|---|---|---|
| [#5](../../issues/5) | The iteration count is unknown, and the model does not converge | **Blocker.** 100 and 250 are both measurably too low |
| [#6](../../issues/6) | The run load is ~765 days of wall clock and no cut has been made | **Blocker.** Nothing downstream can be sized |
| [#7](../../issues/7) | Audit pass: invariants that are true but not the one that matters | Proposed, not decided. Cost/benefit call |
| [#8](../../issues/8) | The MATSim–SUMO outer-loop tolerance is undefined | A P4 obligation that was on no list |
| [#9](../../issues/9) | Re-solve `asc_car_passenger` once the iteration count is settled | The solve is provisional |
| [#10](../../issues/10) | Four count stations outside the modelled network | Reported, not fixed; nothing blocked |
| [#11](../../issues/11) | B2 generates no escort trips | Stated limitation, deliberately not parameterised |
| [#12](../../issues/12) | Transit capacity floors at 1 seat below ~1.5% sample | Acceptable while crowding scoring is off |
| [#13](../../issues/13) | Only ~4 mode-share d.o.f., 1 patronage level and 30 counts constrain the model | Reporting rule, and the two traps |
| [#14](../../issues/14) | Deliverables 4–6 not started | Downstream of #5 and #6 |
| [#15](../../issues/15) | The three unobtained inputs stay swept, never pinned | Restated because a calibration loop is where a swept value quietly gets pinned |

---

## 10. Resuming

```bash
python tests/check_manifest.py                   # committed subset, fast
python src/setup/bootstrap_toolchain.py --verify # JDK/pt2matsim/SUMO digests
python tests/check_package.py                    # 860 checks, needs full package
```

Then read, in order: this file, [`STATUS.md`](../STATUS.md),
[`DECISIONS.md`](../DECISIONS.md) §9.4–§9.9 and §12.1–12.4, and the open GitHub
issues on this branch.

**First action:** read `results/asc_ride_*/` — three candidate
`asc_car_passenger` values at 250 iterations, 1%, S2 × WEEKDAY — then take
decision 5.1.
