# Brief for the next agent — ASSESS BEFORE YOU RESOLVE

*Written 15 August 2026, after the zero-hardcoding change. This is a HANDOVER,
not a source of truth: where it disagrees with [`STATUS.md`](../STATUS.md),
[`DECISIONS.md`](../DECISIONS.md) or [`.claude/CLAUDE.md`](../../../../.claude/CLAUDE.md),
those win. Paste it whole to start a session cold.*

---

## §0 THE ONE RULE

**EVERY OPEN ISSUE IS A HYPOTHESIS UNTIL YOU RE-MEASURE IT. ONE OR ALL OF THEM
MAY ALREADY BE FALSE.**

Not because anyone was careless — because **the model they were measured on no
longer exists.** The zero-hardcoding change moved values that had reached
nothing into the model, and moved others off literals onto their declared
values. A defect diagnosed against the old model may have changed magnitude,
moved to a different mode, or vanished. A new one may have appeared.

Your first deliverable is **not a fix. It is a verdict per issue**, with the
measurement that produced it.

### Proof that this is not theoretical

**#36 is already false, and it takes thirty seconds to show:**

```bash
grep -rn "WICKHAM_" --include=*.py --include=*.java src cities tests run.py | wc -l   # 0
ls src/java                                                                          # citysim
```

The issue says *"rename the `WICKHAM_*` prefix and the `wickham` Java package"*.
There is no `WICKHAM_` prefix and no `wickham` package — it is `citysim`. The
work was done and the issue was never closed. **Close it with the evidence
above.** Then assume the same is possible of every other issue until you have
checked.

---

## §1 WHAT CHANGED BENEATH EVERY PRIOR MEASUREMENT

Read this before you trust any number in `DECISIONS.md` §9 or in an issue body.
Each of these was measured on a model that differed from today's in at least one
of the following ways:

| What | Then | Now | Why it invalidates a measurement |
|---|---|---|---|
| **`numberOfThreads`** | 8 | **10** (`RUN.machine.threads`) | **MATSim partitions the network by thread count. The registry field's own description says it is "PART OF THE RUN IDENTITY, NOT A PERFORMANCE KNOB: changing it changes results."** Every prior run used 8. |
| Road free speed, 6 classes | motorway 100, trunk 80, motorway_link 60, primary_link 50, secondary_link 50, service 20 | **110, 60, 80, 60, 60, 25** (`A.road.speed_default`) | The network builder held a second copy that had drifted. Travel times change on those classes at the next build, which moves every mode share. |
| `fractionOfIterationsToDisableInnovation` | literal `0.8`, field read by nothing | field reaches the model | Sweeping it now does something. |
| Strategy weights | literal table, field read by nothing | field reaches the model | These bound how far co-evolution can move mode share. |
| `BrainExpBeta`, `learningRate`, `lateArrival`, `earlyDeparture`, `waiting` | literals, **no field existed** | declared and swept | The logit scale was undeclared. It governs how sharply agents respond to utility differences. |
| `A.lightrail.tsp_enabled` | set by all 10 scenario overlays, **read by nothing** | decides whether S2b's saving applies | S2 vs S2b was distinguished only by a literal. |
| `A.parking.charged_modes`, `liveIntervalS` | Java defaults **equal to** the registry values | sentinels; Java refuses a run that lost the binding | Right by accident before. |
| Shipped `lastIteration` | 100 (argparse default, past an `unobtained` field) | 250 (declared sweep floor, through the resolver) | 100 is MEASURED too low. |
| Shipped `flowCapacityFactor` | 1.0 | resolved sample fraction | A config run directly simulated sampled demand against full supply. |
| Overlay reach | harness patched **6 parameters** into a shipped config | harness **emits** from the run's own resolution | A run overlay setting anything else was validated, recorded in `_config.json` as provenance, **and changed nothing.** |

**The last row is the one that should worry you most.** If any prior measurement
was made by setting a value through an overlay and comparing, and that value was
not one of the six patched parameters, **the comparison was against an unchanged
model and the finding is an artefact.** Check how each issue's evidence was
produced before you trust it.

---

## §2 THE ASSESSMENT PROTOCOL

Per issue, in this order. Do not skip to the fix.

1. **Read the issue body and the `DECISIONS.md` section it cites.** Record what
   is CLAIMED, what MEASUREMENT produced it, and WHEN.
2. **Ask what the claim rests on.** A file that no longer exists? A field that
   used to reach nothing? A run at 8 threads? A network built at motorway 100?
3. **Reproduce the measurement on today's model.** *"REPRODUCE A DEFECT BEFORE
   ATTRIBUTING IT"* — §12.4 of the working style, and it is the rule this
   project has been bitten for skipping.
4. **Write the verdict**: `CONFIRMED` (with the number), `CHANGED` (with both
   numbers), `FALSE` (with the evidence), or `UNTESTABLE` (with what is missing).
5. **Only then fix**, and only what survived step 4.

**Cross-fraction and cross-build comparison is invalid.** 1% produces spurious
spillback (car stuck 1,028 at 1% vs 7 at 10%); `pt2matsim` mapping is not
reproducible run to run (~18% of route link sequences differ). Compare like with
like or do not compare.

---

## §3 THE THIRTEEN, AND WHAT TO SUSPECT ABOUT EACH

**Ordered by how likely the assessment is to change the answer, not by severity.**

### Likely already false, or largely so — check these first, they are cheap

| # | Claims | Why it may be false | How to test it |
|---|---|---|---|
| **#36** | `WICKHAM_*` prefix and a `wickham` Java package survive | **ALREADY FALSE.** Zero occurrences; the package is `citysim` | the two greps in §0. **Close it.** |
| **#28** | a car passenger arrives 13% faster than the car | The 13% was **already withdrawn** as an aggregate confounded by trip-length composition, restated as 4–8% stratified. The controler fix landed. Road speeds change again at the next build | Re-measure ride vs car **IN MATCHED DISTANCE BINS**. Never aggregate means — that mistake produced a withdrawn headline once |
| **#5** | 100 and 250 iterations are both too low | The measurement stands, but **the pilot that was extending it is deleted** and every prior curve is at 8 threads. The drift verdict is also now a declared tolerance (`RUN.relaxation.drift_tolerance_pp`) rather than a constant | Re-run the convergence pilot on today's inputs. **ONE ARM AT A TIME** — three arms paged the machine |

### Diagnosed on the old model — magnitude almost certainly moved

| # | Claims | Why it may have changed | How to test it |
|---|---|---|---|
| **#29** | bike ownership silently universal, bike 5× observed | The bike share depends on `beta_bike_mode`, the teleported bike speed and the beeline factor — **all three now reach the model differently**, and the walk/bike ordering guard is enforced against the resolved config | Re-measure the bike share before touching ownership. The *mechanism* (no ownership gate) is verifiable by reading B1; the *5×* is not |
| **#30** | destinations too far; education 2.19×; 4.9% of trips under 1 km | Trip lengths interact with the beeline distance factors and the road speeds that just changed. The 2.19× was measured against HTS on the old network | Recompute the distance distributions per purpose on today's plans. **The issue says "NOBODY HAS CHASED THIS" — that is still true** |
| **#37** | 348 agents have a trip at 02:00 AND 26:00 | Seeded in B2, "flat across 30 iterations". Plans were rebuilt? Check. 348 is 0.66% of agents | Recount on today's `demand/plans/matsim/population_WEEKDAY.xml.gz`. Trivial to verify, trivial to be wrong about |
| **#31** | a subtour switches to ride freely; one driver chauffeurs unlimited passengers | The mechanism claim is structural and probably holds. But **`RUN.mode_choice.chain_based_modes` now reaches the model** | Verify the constraint is absent, then read the ⚠ below |

### Structural / data — the claim is about absence, so most likely still true

| # | Claims | What to verify anyway |
|---|---|---|
| **#32** | the OSM harvest box clipped 87 of 1,500 core SA1s | **THE HARVEST IS EMPTY** (`networks/osm/` has 0 files). The box itself is already fixed — `A.osm.harvest_margin_m` derives the extent from the dissolved LGA boundary. What is unverified is whether the RE-HARVEST restores the 87 SA1s. **This gates almost everything else** |
| **#20** | no boundary through traffic; the M1 carries no cars | Verify against today's plans. `calibrate.py` still blocks count-based calibration until this lands |
| **#24** | freight absent | Verify. Note the issue's own title records the business-travel half as **already struck** — 2.11% generated against 2.0% observed |
| **#34** | the CBD box sets a pre-registered B1 denominator | The box is relocated to `geometry/analysis_extents.json` **at byte-identical values** — relocated, NOT fixed. **MEASURE THE DAMAGE BEFORE CHANGING IT**: it moves a pre-registered denominator |

### Blocked on a decision, not on code

| # | Claims | Note |
|---|---|---|
| **#14** | deliverable 5 needs a modelling decision | Depends on #5 and on the demand batch. §8.5's first branch: estimate ASCs on era 3 (2018) and **HOLD FIXED**. **LOG THE DEPARTURE BEFORE ANY RUN** |
| **#9** | re-solve `asc_car_passenger` after the iteration count settles | Strictly downstream of #5 |

---

## §4 DEPENDENCY ORDER — DO NOT FIGHT IT

```
#32 (re-harvest)  ──> rebuild layer chain ──> rebuild network ──> REGENERATE run inputs
                                                                        │
                    #29 #30 #37 (demand defects) ─────────────────────> │
                                                                        v
                                                              #5 (iteration count)
                                                                        │
                                                        #9, #14 (calibrated base)
                                                                        │
                                                                 #20 #24 (missing demand)
```

**#32 is a point of no return**: re-running the harvest re-runs `pt2matsim`, and
**every existing run becomes incomparable** (DECISIONS §3.5, one build per
comparison). Batch everything that needs a rebuild and pay the cost once.

**The scenario GTFS feeds have NOT been rebuilt** since the declarations moved —
`build_scenario_schedules.py` needs `networks/osm/footways.osm` and the harvest
is empty. The rewiring was proved **value-neutral against git** (23 values and
every coordinate identical), so nothing is known to be wrong; it is simply not
yet rebuilt from the declarations. Do it in the #32 batch.

---

## §5 STATE OF THE REPO — 15 August 2026

| | |
|---|---|
| Branch | `praneetdhoolia/mode-choice-specification`, 65 commits ahead of `main`, tree clean |
| **Hardcoding ledger** | **0 items**, `--strict` gates CI. 8 questions incl. Java defaults and a perturbation probe |
| **Reach** | **69 of 69** bound fields PROVEN to reach the model by changing the value and diffing the emitted config |
| `check_package.py` | **ALL CHECKS PASSED**, 2 warnings (was 1 standing failure) |
| `check_city.py --all` | PASS 40, FAIL 0 |
| `check_city_agnostic.py` | PASS 13, FAIL 0 — a second city runs the framework unchanged |
| Registry | **292 fields** — 122 assumed, 85 definition, 35 literature, 25 derived, 21 measured, 4 observed; 15 carry no value |
| Manifest | **378 files** |
| Run inputs | 30 sets, regenerated from the emitter |
| `results/` | **EMPTY.** Both dead runs deleted |
| `networks/osm/` | **EMPTY.** #32 never re-run. `osm_pre_issue32/` is THE ONLY COPY — **do not delete** |
| **Results** | **NONE. Nothing in this repository is an output of the model.** |

### Verified working end to end

A smoke run (1%, 2 iterations) executed on a config built **entirely** by
`src/registry/param_config.py`: `rc=0`, `_run.json` written, metrics extracted.
The simulator runs. It is not calibrated and has produced no result.

---

## §6 HOW THE MODEL IS CONFIGURED NOW — read before you change a value

- **There is no config template.** `src/registry/param_config.py` BUILDS the
  MATSim config and pt2matsim's two from fields carrying a `matsim_param` /
  `pt2matsim_*_param` binding. **To add a parameter, declare a field with a
  binding.** There is nowhere to type a literal, and `closure()` fails the build
  if you find one.
- **`run_matsim.py` emits, it does not patch.** A run overlay now reaches every
  declared field.
- **Prove reach by moving the value.** `check_hardcoding` question 7 does this
  automatically. Keep it at 69/69.
- **Two registers, each entry with a written reason**: `STRUCTURAL` (18 — an
  HTTP status, a gzip level) and `PENDING_CONSUMER` (7 — declared ahead of the
  phase that reads them). **A model value must never be added to `STRUCTURAL`.**
- **A `computed` field** carries an identity and is supplied by the caller under
  the `derived` runtime role; the emitter refuses to invent one.

---

## §7 TRAPS THAT WILL COST YOU A DAY

1. **`compileall` does not catch a `NameError`.** A build script can compile,
   pass every check and die on its first statement. This bit again during the
   zero-hardcoding work (`split_schedule` referenced a deleted `CFG`).
2. **`%` binds tighter than `+`.** `'...%s...' + name + '...' % args` formats
   the last fragment only. This bit too.
3. **BASH HEREDOCS MANGLE BACKSLASH ESCAPES.** Write code with the Write/Edit
   tool. `io.open(p,'w')` truncates before the write fails.
4. **NEVER compare across sample fractions, thread counts or network builds.**
5. **`modestats.csv` ≠ `_metrics.json`** — one is the mode agents CHOSE, the
   other trips that COMPLETED. Never report from modestats.
6. **Mode-share target is `target_lga_pct`**, never `all_residents_pct` — the
   latter has inverted a headline.
7. **THE 67/143 SPLIT IS PRE-REGISTERED.** Never calibrate on, re-split, or peek
   at a holdout row. If you need one to diagnose: **SAY SO AND STOP.**
8. **A run without `_run.json` is not a result and is not kept.**
9. **NO INVENTED DATA.** If a value is not measured it is assumed or modelled,
   labelled in `source`, and recorded in `DECISIONS.md` with a rationale and a
   sweep range.
10. ⚠ **#31 specifically**: eqasim's `PassengerConstraint` is a TRIP-LEVEL
    biconditional on `getInitialMode()`; no driver is consulted. Adopting it
    **PINS THE RIDE SHARE TO THE B2 SEED**. **DO NOT ADD `ride` TO
    `chainBasedModes`.** Its mode string is `car_passenger` and is HARD-CODED —
    a copied constraint compiles, runs, constrains nothing and reports success.

---

## §8 YOUR FIRST DELIVERABLE

**An assessment table, committed to `docs/audit/`, before any fix:**

| # | Claim | Evidence it rested on | Re-measured | Verdict | Next action |
|---|---|---|---|---|---|

Then, and only then, work the survivors in the §4 dependency order.

**Do not open a PR that fixes an issue you have not first reproduced.**
