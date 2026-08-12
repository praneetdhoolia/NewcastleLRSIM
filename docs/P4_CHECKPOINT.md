# P4 checkpoint — the long-form handoff

**Rewritten 12 August 2026, after every phase was re-verified against the
package and the three open decisions were taken (§9.22).** [`STATUS.md`](../STATUS.md) is the short live status and holds the
**verified phase board and the full deliverable checklist**; this is the
full picture for someone picking the work up cold. Where the two disagree,
`STATUS.md` is newer.

---

## 0. The one-paragraph version

P4 is calibration. Its deliverable list has grown from seven to **nine** and
**six are met**. The three that are not are the ones that matter: a **calibrated
base**, a **transfer-penalty estimate** the proposal's own fallback specified and
nobody built, and a new **deliverable 0 — specification and input completeness**
which now gates the calibrated base, because calibrating a model with
known-missing demand calibrates the wrong model. A wide data search settled the
three long-unobtained inputs: SCATS phasing is **refused by policy** and that is
now citable, journey-linked Opal is unpublished, and charging dwell has no
published figure. Published fleet capacities were found and **every capacity in
the model was too generous**. **Nothing in this repository is a result.**

---

## 1. Read these first, in this order

```
STATUS.md                     verified phase board + the nine deliverables
DECISIONS.md  §0, §8.5, §9.7–§9.21, §12.1, §15, §16
CLAUDE.md                     conventions and hard constraints
docs/CONFIG_REFERENCE.md      generated; skim "no value" and "held fixed"
gh issue list --state open   12 open; NONE awaits a decision -
                             9 awaiting-implementation, 3 awaiting-run
```

Then confirm the package is intact:

```
python tests/check_manifest.py                    fast, committed subset
python src/setup/bootstrap_toolchain.py --verify  JDK / pt2matsim / SUMO digests
python tests/check_package.py                     ~960 checks, 1 standing warning
```

The standing warning is `lastIteration`, which is issue #5. It is *supposed* to
be there. **Do not re-read the P1–P3 package**: 364 files are hashed in
[`data/MANIFEST.csv`](../data/MANIFEST.csv) and the build is verified.

**Machine:** 24 logical cores, 63.5 GiB. One run averages **2.4 busy cores of
24** — the mobsim synchronises every simulated second, so threads idle. Memory
(9.6 + 87 GiB × fraction) binds long before cores. **Parallelise across runs,
never threads within one**: thread count is part of the run identity. There is
**no GPU path**; do not re-investigate it.

---

## 2. Where the work actually is

**Deliverable 0 comes before deliverable 5, and 0a comes before the rest.**
The breakdown is in [`STATUS.md`](../STATUS.md) under *The deliverable
checklist*; it is not repeated here. The ordering argument is:

> Mode share is car **32.5%** against an observed **59.0%** and car passenger
> **50.0%** against **20.6%**. Something structural is still wrong. Adding
> freight, business travel and through traffic on top of an unexplained error
> makes it harder to find, not easier — and each of them moves mode share, so a
> base calibrated before them must be calibrated again after them.

So: **0a specification audit → 0b derive what can be derived → 0d the missing
demand → re-baseline → then calibrate.** 0c (fleet) and 0e (housekeeping) do not
touch demand generation and can run in parallel with any of it.

### What deliverable 5 is actually blocked by

Not code. The loop exists, is deterministic and resumable, and cannot read a
holdout row through two independent guards. It derives its search space from the
registry: of the fields carrying a scalar sweep, **21 are excluded with a stated
reason** — the loop's own controls, run identity, the measurement apparatus,
anything needing the schedule mapper re-run (§3.5), anything with no consumer.
Of the rest, almost all need a **demand rebuild per candidate** the loop does not
implement. What remains is one parameter that barely matters.

That is not a bug. The mode constants are `held_fixed` under §8.5 **precisely
because** moving them absorbs the effect under test. **A calibrated base is not
reachable by turning the dials that are open.** Three ways forward, and it is
the user's call:

1. **Implement the demand-rebuild stage** — makes `B.activity.*` reachable, at
   roughly 50 min per candidate on top of a 2.3 h run.
2. **Re-open §8.5** — fastest, and proposal §9 names it the **primary threat to
   validity**. Requires a departure logged before results.
3. **Accept a constrained base** rather than a calibrated one, and report it as
   such. `report.py` already states which applies.

---

## 3. Measured and true — do not re-derive

**Mode share, S2 × WEEKDAY, 10%, 250 iterations, Newcastle LGA from `_fit.json`**
— the reportable geography, **not** the five-LGA aggregate. Pre- and post- the
§9.15 demand repair, both at `ride` distance rate zero:

| | pre-repair | post-repair | HTS |
|---|---:|---:|---:|
| Vehicle driver | 30.85 | **32.54** | 59.0 |
| Vehicle passenger | 50.94 | **50.03** | 20.6 |
| Public transport | 0.99 | 0.83 | 3.8 |
| Walk only | 0.80 | 0.75 | 13.4 |
| Other | 16.43 | 15.86 | 3.2 |
| MAE over 5 targets | 17.43 pp | **16.83 pp** | |
| passengers per driver | 1.6512 | **1.5376** | 0.3503 |
| ride ÷ car trip length | 1.3462 | **1.3516** | 0.9608 |

**Repairing the external tier and typing 14.53% of legs as escort trips did not
move ride.** The distortion is in `ride`'s specification, not the demand.
**§9.17's premise survives the rebuild** — the trip-length ratio it was justified
against did not move, so the departure does not rest on an artefact.

**Post-innovation drift on that run** (iteration 200 → 250, after new plans stop
being created): ride **+0.0367**, walk −0.0246, bike −0.0116, pt −0.0081, car
+0.0075. §9.7 holds at ten times the population and on repaired demand: **the
model has not relaxed, and 250 is still too low.** The live run view computes
this while a run is in flight.

**Other measurements that stand:**

- **1% is unusable, not merely unrepresentative** (§9.12). `flowCapacityFactor
  = 0.01` gives an 1,800 veh/h link **one vehicle per 200 s**; 1,032 car legs
  abort against 4 at 10%. This is *flow*, distinct from the *storage* argument
  §9.10 ruled out.
- **Fraction sensitivity has flattened:** 1%→10% moved car +14.8 pp; 10%→25%
  only +1.6 pp. **100% does not fit in 63.5 GiB; ceiling ≈ 40%.**
- **Run cost:** 9.8 s/iter at 1%, ~24 s at 10%, 56.4 s at 25%.
- **Counts:** 30 stations scored, mean error **−69.9%**, one modelled zero
  (V113, the M1 at Wyee). All 195 matched links are name-and-proximity; none is
  proximity-only (§9.20).
- **Walk trips run 5.05× their observed length.** A **finding to report** under
  deliverable 6, not a work item to chase.
- `modestats.csv` ≠ `_metrics.json` — one records the mode agents **chose**, the
  other trips that **completed**. Both correct. **Never report from modestats.**
- **Registry: 171 fields.** After any registry edit:
  `python src/registry/render_docs.py`
- A `consumers` entry is a **machine claim**, verified by `check_package.py` —
  but its *absence* proves nothing, because the list is a read log and only
  records what the generating run touched.

---

## 4. The traps — handle, do not rediscover

1. **The 67/143 split is pre-registered.** Never calibrate on, re-split or peek
   at a holdout row. New observables become **constraints** (the C4 pattern),
   never targets. If you need a holdout row to diagnose something: **say so and
   stop.**
2. **One build of the network per comparison** (§3.5). A scenario runs on its own
   `schedules/<S>/network.xml.gz` plus the E1 patch by `osm:way:id`. **Never
   re-run the mapper.**
3. **Mode-share target is HTS Newcastle LGA** (59.0 / 20.6 / 13.4 / 3.8 / 3.2).
   Comparing a five-LGA modelled mean to a Newcastle-LGA published one is the
   error §9.13 records being made — it once inverted a headline.
4. **The observed 20.8% "light rail share of local PT boardings"** is LR ÷ (LR +
   NISC 1 bus) **taps**. A1's metric is LR person-**legs** ÷ **total** PT
   person-legs. It is an **upper bound**. Never calibrate A1 against it. TfNSW's
   own post-July-2024 note that line/mode aggregations are invalid confirms this
   independently (§9.21).
5. **PT mode share halved**, 7.3% (2018/19) → 3.8% (2024/25). A 2026 base
   calibrates to a pandemic-suppressed PT market. **Comparisons** stay valid;
   **absolute patronage** does not transfer.
6. **No count-based calibration until the M1 gap is resolved** (§9.14).
   `calibrate.py` enforces this.
7. **The three unobtained inputs stay swept, never pinned.** SCATS is now a
   *documented refusal* (§9.21), which triggers proposal §7.2 and **binds every
   corridor headline to a stated uncertainty band**.
8. **Bash heredocs mangle backticks.** Write prose to a file and splice with
   Python. This has bitten three times.
9. **Do not trust a search summary.** One asserted a charging-dwell figure that
   the cited page does not contain. Read the source.

---

## 5. Errors made, so they are not repeated

- **A defect was "fixed" before it was reproduced.** A run died at iteration 0 in
  `ImageIO`; it was attributed to the launching shell, announced as such, and
  then **did not reproduce** — and the log had been overwritten. Reproduce
  first, then attribute.
- **A determinism bug was written into new code:** Python salts string `hash()`
  per process, so a vehicle-thinning hash would have made the same run produce a
  different picture. Use `zlib.crc32`.
- **A gate was skipped before committing two hours of compute.** The run inputs
  were rebuilt and a run launched without re-running `check_package.py` or
  diffing the two runs' resolved configs. Both passed on inspection afterwards —
  but that was luck, not method. **Run the gate before the run, not after.**
- **A "week average trip rate" was compared against a three-day baseline** after
  building only WEEKDAY. Check both sides cover the same thing.
- **A `PermissibleModesCalculator` compiled, ran clean and did nothing**, because
  the seed still handed agents the mode. **Verify the consumer, not the
  mechanism.**

**What not to do:** do not treat "~960 checks pass" as "the model is right" —
seven P4 defects were invisible to a passing suite, and `fit.py` had zero
coverage while producing every calibration number. Do not report anything from a
sub-250-iteration run. Do not add a parameter without a sweep, a `held_fixed`
rule or a `derived_from` identity. Do not close an issue because the list looks
long: the bar is **structurally prevented, not remembered**.

---

## 6. How to drive it

```bash
# a committed overlay - the reproducible way to vary a run
python src/run/run_matsim.py --scenario S2 --day WEEKDAY --run-config ride_cost_10pct

# a one-off, still checked against the sweep and held-fixed rules
python src/run/run_matsim.py --scenario S2 --day WEEKDAY \
    --fraction 0.25 --iterations 250 --threads 8 --xmx 40g --tag my_run

# the declared pipeline - the ONLY route to a reportable number
python src/analyse/extract_metrics.py --run <tag>
python src/calibrate/fit.py           --run <tag>
python src/calibrate/report.py        --run <tag> --out docs/CALIBRATION_REPORT.md

# watch a run in flight (the url is also printed by run_matsim.py itself)
python src/analyse/run_monitor.py --run <tag>
```

After any change to a build input: `normalise_eol.py` → `build_manifest.py` →
`normalise_eol.py`, then both check suites.

---

## 7. Out of P4 scope — do not start these

- **socnetsim joint plans** — absent from the pinned jar; a §14 toolchain change,
  which is a model change.
- **Running SUMO.** Deliverable 7 is the **tolerance**, a number. The SUMO
  harness and the outer loop are **P5**. The corridor has been built six times
  and simulated **zero** times, deliberately: coupling it to a demand model whose
  mode share is wrong would propagate the error into run time, car delay and B3
   — the decisive test of Claim B. **SUMO pedestrian crossings** need a SUMO
  version change and belong here too.
- **P5 scenario runs, P6 analysis**, and a 2013 historical reconstruction
  (considered and dropped — do not reopen without the user).
- **Any holdout row.**

---

## 8. Housekeeping

- **30.6 GiB of superseded runs** in `results/ride_sufficiency_*`. They are the
  evidence base for §9.12, §9.13 and §9.17, all now recorded, and the 25% run
  backs the published replay. **Delete once the post-repair runs have replaced
  them as the reference, not before.**
- The replay tooling (`replay_events.py`, `build_basemap.py`,
  `build_replay_page.py`) and the live view (`run_monitor.py`) are used and
  documented. Their output pages are **not committed** — megabytes of payload.
- Two Overpass layers (`water`, `green`) are **visual-only** and deliberately
  retained for the replay basemap. They have no model consumer and that is not a
  defect.
- **Branch:** `praneetdhoolia/external-cordon-and-escort`, on top of
  `praneetdhoolia/config-registry`. **Nothing has been pushed.**
