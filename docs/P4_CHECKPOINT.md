# P4 checkpoint — the long-form handoff

**Written 12 August 2026.** [`STATUS.md`](../STATUS.md) is the short live status;
this is the full picture for someone picking the work up cold. Where the two
disagree, `STATUS.md` is newer.

---

## 0. The one-paragraph version

P4 is calibration. Three of its seven deliverables were already built; **three
more landed this session (the loop, the report, the outer-loop tolerance)**, and
**one — the calibrated base — is not met and is blocked by a modelling decision
rather than by missing code.** Two specification defects were found by
measurement and repaired: the external demand tier was being charged a walk to
the network that the modes it chose instead were exempt from, and escort trips
were being generated as two-hour discretionary stays instead of five-minute
drop-offs. A §8.5 departure was logged, before results, charging car passengers
the same distance cost as drivers. **Nothing in this repository is a result.**

---

## 1. Read these first, in this order

```
STATUS.md                       where the build is
DECISIONS.md  §0, §8.5, §9.7–§9.17, §12.1, §15     every value that is not observed
CLAUDE.md                       conventions and hard constraints
docs/CONFIG_REFERENCE.md        generated; skim "no value" and "held fixed"
gh issue list --state open      12 open, and they ARE the worklist
```

Then confirm the package is intact:

```
python tests/check_manifest.py                    fast, committed subset
python src/setup/bootstrap_toolchain.py --verify  JDK / pt2matsim / SUMO digests
python tests/check_package.py                     ~950 checks, 1 standing warning
```

The standing warning is `lastIteration`, and it is issue #5. It is *supposed* to
be there.

**Do not re-read the P1–P3 package.** 364 files are hashed in
[`data/MANIFEST.csv`](../data/MANIFEST.csv) and the build is verified.

**Machine:** 24 logical cores, 63.5 GiB. One run averages **2.4 busy cores of 24**
— the mobsim synchronises every simulated second, so threads idle. Memory
(9.6 + 87 GiB × fraction) binds long before cores. **Parallelise across runs,
never threads within one**: thread count is part of the run identity. There is
**no GPU path**; do not re-investigate it.

---

## 2. What is running, or was

| run | what it is |
|---|---|
| `results/S2_WEEKDAY_f01_i250_s20260810/` | **the first run on repaired demand.** S2 × WEEKDAY, 10%, 250 iterations, 8 threads, seed 20260810. Overlay `config/runs/cordon_escort_10pct.json`. Was at iteration 191/250 when this was written |
| `results/ride_sufficiency_{1,10,25}pct/` | **historical.** Pre-repair demand. 30.6 GiB. The evidence base for §9.10, §9.12, §9.13 and §9.17 — all now recorded in `DECISIONS.md`. `ride_sufficiency_25pct` also backs the published replay |

The run directory is auto-named because `--tag` was omitted; the overlay name is
`cordon_escort_10pct` and `_run.json` records the parameters. Not worth fixing
retroactively.

**⚠ First action:** if `_run.json` exists, run the declared pipeline on it:

```
python src/analyse/extract_metrics.py --run S2_WEEKDAY_f01_i250_s20260810
python src/calibrate/fit.py           --run S2_WEEKDAY_f01_i250_s20260810
python src/calibrate/report.py        --run S2_WEEKDAY_f01_i250_s20260810 \
       --out docs/CALIBRATION_REPORT.md
```

**⚠ Second action, and it is easy to miss:** the registry now charges `ride` the
car distance rate (§9.17) but **the built run inputs in `scenarios/matsim/` still
carry the old zero.** They were not rebuilt because the run in flight reads the
shared network and schedule from that directory. Once it finishes:

```
python src/build/build_matsim_run_inputs.py
python src/build/normalise_eol.py && python src/build/build_manifest.py && python src/build/normalise_eol.py
```

Then launch the ride-corrected run. **That is the measurement §9.17 was logged
against.**

---

## 3. The seven deliverables

| # | deliverable | state |
|---|---|---|
| 1 | Run harness | done — `src/run/` |
| 2 | Metric extraction | done — `src/analyse/` |
| 3 | Fit statistic | done and tested — `src/calibrate/fit.py` |
| 4 | **Calibration loop** | **done — `src/calibrate/calibrate.py`** |
| 5 | **Calibrated base + provenance** | **NOT MET.** Blocked by a decision, not by code |
| 6 | **Calibration report** | **done — `src/calibrate/report.py`** |
| 7 | **Outer-loop tolerance** | **done — 5 s.** §9.16, issue #8 closed |

### Why deliverable 5 is blocked, and what the choice is

The loop derives its search space from the registry. Of **38** fields carrying a
scalar sweep, **21 are excluded with a stated reason** — the loop's own controls,
run identity, the measurement apparatus, anything needing the schedule mapper
re-run (§3.5), anything with no consumer. Of the rest, almost all need a **demand
rebuild per candidate** that the loop does not implement. What remains is **one
parameter that barely matters**.

That is not a bug. The mode constants are `held_fixed` under §8.5 *precisely*
because moving them absorbs the effect under test. **A calibrated base is not
reachable by turning the dials that are open.** Three ways forward, and it is a
modelling decision:

1. **Implement the demand-rebuild stage** — makes `B.activity.*` reachable, at
   roughly 50 min extra per candidate on top of a 2.3 h run.
2. **Re-open §8.5** — fastest, and proposal §9 names it the primary threat to
   validity. Requires a departure logged before results.
3. **Accept a constrained base** rather than a calibrated one, and report it as
   such. The report already says which applies.

---

## 4. What was found this session, by measurement

### 4.1 The external tier was walking to the network (§9.15)

Six hypotheses had already died. The seventh was measured.

`routing.accessEgressType = accessEgressModeToLink` with
`networkModes = car,ride` charges car and ride an access walk to the link and
charges the teleported modes **nothing**. **All 201 external zones lie outside
the modelled area** — median **21.3 km** beyond the boundary, max **128.7 km** —
while the network is clipped to the study area.

| tier | mode | median access walk |
|---|---|---:|
| core | car | **0.097 km** |
| external | car | **2.656 km** (top deciles 16.4 / 39.9 / **49.8 km**) |
| external | bike | **0.000 km** |

At iteration 0 (uniform seed, so mode is exogenous), a car tour with <0.5 h of
access scored **+94.21**; one with >6 h scored **−1165.01**, and **48% were in
that band**. 39.0% of external car tours never got home, against 13.9% by bike.
**Mode choice was correct** — the 478 agents cycling 96 km were picking the only
mode that did not require walking to a road.

**Repaired:** boundary demand now enters at one of **42 cordon crossings**,
derived from the network rather than listed, choosing the entry that minimises
`d(zone, cordon) + d(cordon, destination)`. Destinations placed on observed
attractors. Median external leg **54.2 → 21.6 km**.

**Two more defects alongside:** all 531 external agents carried
`rideAvail=always` although built household-less — **432 of 962 external trips
were passengers with no possible driver** — and the tier is a **single SA4 arc**
(SE/S/SW = 0 zones), so the M1 gap is *outside its declared scope*, not a
tier-size problem.

### 4.2 Escort trips were mistyped, not missing (§9.15)

`Serve passenger` **was** read — mapped to `NHB`, then folded into discretionary
tours because NHB is not a tour purpose. The trip **rate** survived; the **type**
did not. An escort was a two-hour stay made by anyone rather than a five-minute
drop-off made by a driver.

Now its own purpose `HX`: own gravity decay against the observed journey
distance, education departure profile and attractors, licence requirement, and a
5-minute MATSim `escort` activity. **14.53% of weekday legs against an observed
15.7% of journeys.** Week trip rate −2.2% → **−1.6%**.

### 4.3 The §8.5 departure, logged before results (§9.17)

`C.scoring.monetary_distance_rate['ride']`: **0.0 → −0.00018**, the car rate.

§9.8 set it to zero on the identity *a vehicle cost is paid once*. **True, and
about the wrong quantity** — that governs aggregate system cost accounting;
`monetaryDistanceRate` is the cost **perceived by one person choosing**. §9.13
had already falsified it with a **constraint, not a target**: modelled ride ÷ car
trip length **1.372** against an observed **0.961**, widening with sample
fraction — the signature a zero marginal distance cost produces.

**Not** `asc_car_passenger`, which stays at −0.85 and is unreachable by the loop.

**Falsification recorded in advance:** if ride overshoots *below* 20.6%, or the
length ratio below 0.961, the rate is doing more work than the correction
justifies and the second candidate must not be stacked on it.

### 4.4 Mode coverage, audited

| observed (Newcastle LGA 2024/25) | model | note |
|---|---|---|
| Vehicle driver 59.0% | `car` | queue-simulated |
| Vehicle passenger 20.6% | `ride` | network-routed, teleported in qsim |
| Public transport 3.8% | `pt` | bus 1,448 + rail 332 + light rail 252 + ferry 107 weekday departures |
| Walk only 13.4% | `walk` | teleported |
| Other 3.2% | `bike` | **approximate** — "Other" also holds taxi, motorcycle, rideshare |

Freight is not modelled and the comparison accounts for it: counts use the
**light-vehicle** column, heavy share **measured** at 6.52%.

### 4.5 Two findings that are now issues

- **#21 (new):** gradient penalties and PT walk-access decay are declared, swept,
  mirrored into C1 — and **read by nothing**. `gradient` appears **zero** times
  in the generated MATSim config, and neither is on §9.3's register of what does
  not survive translation. Sweeping a parameter that reaches nothing yields a
  sensitivity band of zero, reported as "insensitive" when the truth is "absent".
- **The registry/C1 mirror:** the C-layer behavioural values live in
  `config/registry/` *and* `params/C1_parameters.json`, and the model reads the
  latter. `check_legacy_drift.py` pins the registry to source *constants*, not to
  a params file, so the pair was unpinned. All 11 comparable values agree; a
  check now asserts it (§9.16).

---

## 5. Measured and true — do not re-derive

**Pre-repair mode share**, S2 × WEEKDAY, 250 iterations, Newcastle LGA from
`_fit.json` — the reportable geography, **not** the five-LGA aggregate:

| | 1% | 10% | 25% | HTS |
|---|---:|---:|---:|---:|
| Vehicle driver | 16.01 | 30.85 | 32.48 | **59.0** |
| **Vehicle passenger** | 61.06 | 50.94 | 49.87 | **20.6** |
| Public transport | 0.62 | 0.99 | 0.97 | 3.8 |
| Walk only | 1.59 | 0.80 | 0.74 | 13.4 |
| Other | 20.73 | 16.43 | 15.93 | 3.2 |
| MAE over 5 targets | 23.19pp | 17.43pp | 16.80pp | |
| passengers/driver | 3.814 | 1.651 | 1.535 | **0.3503** |

- **1% is unusable, not merely unrepresentative** (#17, §9.12). 1,032 car legs
  abort at the 30 h horizon against 4 at 10%; 380 PT passengers board and never
  alight against 0. `flowCapacityFactor = 0.01` gives an 1,800 veh/h link **one
  vehicle per 200 s**. This is *flow*, distinct from the *storage* argument §9.10
  ruled out. Every 1% behavioural number carries it.
- **Fraction sensitivity has flattened:** 1%→10% moved car +14.8 pp; 10%→25%
  moves it +1.6 pp.
- `modestats.csv` ≠ `_metrics.json` — one records the mode agents **chose**, the
  other trips that **completed**. Both correct. **Never report from modestats.**
- **Counts do not move with fraction:** −72.9 / −73.8 / −73.1%.
- **Run cost:** 9.8 s/iter at 1%, ~28 s at 10%, 56.4 s at 25%. Memory ≈
  9.6 + 87 GiB × fraction. **100% does not fit in 63.5 GiB; ceiling ≈ 40%.**
- `fit.py` scores **38** + explains **29** = **67**, over 33 count stations. A
  modelled zero is scored at −100% and named. Ten tests guard it.
- **Registry: 164 fields.** After any registry edit:
  `python src/registry/render_docs.py`
- A `consumers` entry is a **machine claim**, verified true by `check_package.py`.

**Two §12 traps — handle, do not rediscover:**
- The observed 20.8% "light rail share of local PT boardings" is LR ÷ (LR + NISC 1
  bus) **taps**. Hypothesis A1's metric is LR person-**legs** ÷ total PT
  person-legs. It is an **upper bound**. Never calibrate A1 against it.
- PT mode share **halved**, 7.3% (2018/19) → 3.8% (2024/25). A 2026 base
  calibrates to a pandemic-suppressed PT market. **Comparisons** stay valid;
  **absolute patronage** does not transfer.

---

## 6. Next tasks, in order

1. **Measure the repaired demand.** Pipeline on
   `S2_WEEKDAY_f01_i250_s20260810`. This is the first look at whether the §9.15
   repair moved car and ride.
2. **Rebuild the run inputs** so §9.17's rate reaches MATSim, then **run it**.
   Compare against step 1 — that is the departure's test, and its falsification
   conditions are already written down.
3. **#16 — close it** on that measurement, or take the second candidate (zero-PCE
   queued `ride`), which **ships only with its measurement**: ride min/km must
   converge on car's, and `vol_car` at the 33 stations must not move, or §12.2a's
   count identity breaks.
4. **#5 — the iteration count.** Do not chase it before #16: you would be timing
   a corner forming. `run_matsim.py` refuses to start without one.
5. **#6 — the run programme.** ~765 machine-days, worse since #17 killed the
   cheap 1% tier. Measure seed variance rather than assuming 30 replications;
   replace the 140-point full factorial with a screening design; sweep **weekday
   only**. If it still does not fit, put "cut scope vs rent compute" to the user
   — they have not ruled out spending money.
6. **#14 — deliverable 5**, on the decision in §3 above.
7. **#20 — boundary through traffic**, if count-based calibration is wanted. All
   five Pacific Motorway stations are **calibration** rows, so an external-station
   matrix seeded from cordon counts touches no holdout. It is a **scope decision**
   about what the model is for.

### Fixable without running the simulation

These need no compute and can be done in parallel with anything above:

| issue | what it needs |
|---|---|
| **#21** | name gradient and walk decay in `not_representable`, so the register is complete. Cheap and honest. Making them *reach* the model is a §14-scale decision |
| **#18** | light rail capacity: 180 seats is pt2matsim's generic tram default and the zero standing room is a `useStandingRoom` flag the build never set. Fully diagnosed. A vehicle-definition fix in the build layer |
| **#10** | three count stations outside the network, one a calibration target. Pure geometry and matching; #20 already showed Raymond Terrace Road was a proximity-only mismatch at 107.9 m |
| **#12** | the 1-seat capacity floor below ~1.5% sample. Largely moot since 1% is unusable, but it is a build-layer capacity floor and could be made explicit |

---

## 7. Hard constraints — do not violate

1. **The 67/143 split is pre-registered.** Never calibrate on, re-split or peek at
   a holdout row. New observables become **constraints** (the C4 pattern), never
   targets.
2. **One build of the network per comparison** (§3.5). A scenario runs on its own
   `schedules/<S>/network.xml.gz` plus the E1 patch by `osm:way:id`. **Never
   re-run the mapper.**
3. **Mode-share target is HTS Newcastle LGA** (59.0 / 20.6 / 13.4 / 3.8 / 3.2).
   Comparing a five-LGA modelled mean to a Newcastle-LGA published one is the
   error §9.13 records being made.
4. **The three unobtained inputs stay swept, never pinned** — SCATS phasing,
   journey-linked Opal, measured charging dwell. `B.external.interaction_rate`
   too.
5. **Everything seeded 20260810.** `normalise_eol.py` **before**
   `build_manifest.py`, then again after.
6. **No invented data.** Derive it from the package or sweep it. Never type an
   observed value into a script.
7. **Run the declared pipeline:** `run_matsim.py` → `extract_metrics.py` →
   `fit.py`, producing schema-validated `_metrics.json` and `_fit.json`.
8. **No count-based calibration until #20 is resolved** (§9.14). `calibrate.py`
   enforces this; it is no longer a matter of remembering.
9. **Bash heredocs mangle backticks.** Write prose to a file and splice with
   Python.

---

## 8. Out of P4 scope

- **socnetsim joint plans** — absent from the pinned jar; a §14 toolchain change,
  which is a model change.
- **Running SUMO.** Deliverable 7 is the **tolerance**, a number. The SUMO harness
  and the outer loop are **P5**. The corridor has been built six times and
  simulated zero times, deliberately: coupling it to a demand model whose mode
  share is wrong would propagate the error into run time, car delay and B3 — the
  decisive test of Claim B.
- **P5 scenario runs, P6 analysis**, and a 2013 historical reconstruction
  (considered and dropped).
- **Any holdout row.** If you need one to diagnose something: **say so and stop.**
- **Walk trips are 5× observed length** (3.55 km modelled vs 0.70). That is a
  **finding to report** under deliverable 6, not a work item to chase.

---

## 9. Housekeeping

- **30.6 GiB of superseded runs** sit in `results/ride_sufficiency_*`. They are
  the evidence base for §9.12, §9.13 and §9.17, all now recorded, and
  `ride_sufficiency_25pct` backs the published replay. **Deliberately not
  deleted** — they underpin a decision logged hours ago. Delete once the
  post-repair runs have replaced them as the reference, not before.
- The run replay tooling (`src/analyse/replay_events.py`, `build_basemap.py`,
  `build_replay_page.py`) is used and documented. Its output page is **not
  committed** — megabytes of payload, and this repo does not commit bulk data.
  Two Overpass layers (`water`, `green`) were fetched for it; both are ODbL like
  every other OSM-derived layer and **neither has a model consumer**.
- **Branch:** `praneetdhoolia/external-cordon-and-escort`, on top of
  `praneetdhoolia/config-registry`. **Nothing has been pushed.**
