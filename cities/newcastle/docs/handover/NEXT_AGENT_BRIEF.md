# Brief for the next agent — #5 IS CLOSED; BUILD THE RIDE PAIRING (TIER 1)

*Rewritten 18 August 2026, after the #5 declaration landed and after a
socnetsim joint-plans implementation was built, measured, and REVERTED on
evidence. This is a HANDOVER, not a source of truth: where it disagrees with
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

**⚠ OWNER DIRECTIVE: NO MULTI-HOUR RUNS WITHOUT EXPLICIT OWNER APPROVAL.**
"We can't afford to run full-day runs every now and then." The convergence
measurements are DONE — two full arms, 42 h, evaluated, and the #5 declaration
is made from them. Your lane is code, declarations and short verification runs.
State the cost and get a yes before anything long.

**`results/` right now:** `conv1000_10pct` and `conv1000_25pct` (both rc=0,
both evaluated, both **valid baselines again** — their `controler_sha256`
matches the current source), plus `smoke_postrebuild`.
`results/_aborted_20260816/` is quarantine. ⚠ `results/S2_WEEKDAY_f025_i1000_s20260810/`
is a **fourth dead run with no `_run.json`** — not a result, not quarantined,
owner may delete.

**The iteration count is now DECLARED (1000), so `--iterations` below 250 is
REFUSED by the resolver.** A short probe needs `allow_outside_sweep` in a run
overlay with a written justification. Do not fight the guard; it is correct.

---

═══════════════════════════════════════════════════════════════════════════════
§1  THE MISSION
═══════════════════════════════════════════════════════════════════════════════

The owner's standing goal (treat as the directive):

> **Goal: a digital twin of any given city (traffic-wise), simulating the
> entire population or a percentage of it — if a percentage, congestion and
> capacity are scaled accordingly, and whether that scaling actually predicts
> the correct ridership per mode must be CHECKED, not assumed.** Implemented
> for Newcastle, where the light-rail project gives claims we can evaluate.
> **Fix the ride share by riding actual cars, and the taxi/rideshare
> ridership.** Token limit applies: do it right rather than bloating the repo.
> **Every form of transport should be IN ACTION physically** — cars, buses,
> motorbikes, taxis, ubers, ferries, trains, light rail.

**Five of the nine are ALREADY physical — measured 18 Aug, do not rebuild:**

| | status | evidence |
|---|---|---|
| Cars | ✅ | qsim `mainMode`, 175,560 links |
| **Buses** | ✅ | 1,448 vehicles, PCE 2.8, sharing **22,102 road links with cars** |
| **Trains** | ✅ | 332 vehicles, 6,766 dedicated rail links |
| **Light rail** | ✅ | 252 tram vehicles, incl. **21 links shared on-street with cars** |
| **Ferries** | ✅ | 107 vehicles (Stockton) |
| Car passengers | ❌ **teleported** | **your job (§3)** |
| Motorbikes | ❌ absent | silently inside `car`/`ride` targets (§2, §3.4) |
| Taxis / Uber | ❌ absent | inside the `Other`/bike bucket (§3.4) |

2,139 transit vehicles move every iteration. `usingTransitInMobsim=true`.

| # | Goal | State |
|---|---|---|
| **G1** | The light-rail counterfactual (calibrated base → S0–S6 → 143 sealed holdouts → findings with bands) | Inputs trustworthy; #5 closed; **the ride pairing is the active lane** |
| **G2** | City-agnostic simulator | ✅ 13 CI assertions; ledger 0 `--strict`; reach 69/69 |

The law: **every value DECLARED in `cities/<city>/registry/` and REACHING the
model through the resolver.** 9 of 10 rail forecasts overestimate patronage
(avg +106%); a flattering answer is the EXPECTED failure mode.

---

═══════════════════════════════════════════════════════════════════════════════
§2  WHAT IS DONE — do not redo any of it
═══════════════════════════════════════════════════════════════════════════════

**#5 IS CLOSED (§9.43).** `RUN.controler.last_iteration` = **1000**,
`measured`/`active`, off `unobtained` and out of `city.json`'s unobtained list.
The drift gate was **broken and could never pass at any horizon**: it measured
from the innovation cutoff, and the per-iteration trace shows the entire
+3.5 pp is **ONE iteration wide** (all of it at iteration 801: car +3.256 pp at
10%, +3.380 pp at 25%). New field `RUN.relaxation.settle_margin_iterations`
= 10 (swept 1–100); both arms now report **`relaxed: true`** at +0.22 / +0.17 pp.
Summaries carry `snap_pp`, the scored `drift_pp`, and `cutoff_to_final_pp`
(which reproduces the old +3.54/+3.60 exactly, so the change is auditable).
**Declared uncertainty:** ~2 pp of pre-cutoff search creep never measured — the
1500-iteration arm was cancelled by the owner for compute economy — and the
verdict passes at tolerance 0.25–1.0 pp but **fails the sweep's 0.1 pp floor**.

**THE RIDE DIAGNOSIS — measured, and it overturned the old brief:**

- **The congested-time binding the previous brief listed as fix (a) ALREADY
  EXISTED** (`CitysimControler` since `047b7a0`) and **both arms ran with it**
  (`controler_sha256 eee4fdfa…` matches). Ride already pays congested car time
  and is still faster. Inventory beats a written premise.
- **The residual is a FIXED overhead, not a speed error.** Per distance bin
  from the arms' own `output_legs.csv.gz`, the car's disadvantage is flat in
  seconds, not growing with distance: **≈5 s at 25%, ≈13 s at 10%**, across
  every bin below 50 km. The declining ratio (1.107 → 1.002) is arithmetic.
  Above 50 km the sign REVERSES (ride slower, 0.897) — unexplained, small n.
- **A 1-minute pickup friction would be 5–12× the entire residual.** Sizing one
  to close a 5 s gap is calibration wearing a mechanism's clothes. **REFUSED
  as a fitted parameter.**
- **The overhead is FRACTION-DEPENDENT, and that is the goal-check answer.**
  Car pays sample-dependent queueing; a teleported passenger is structurally
  immune (§9.12 floored-storage artefact). This is the mechanism behind the
  ~3.7 pp car↔ride margin shift across fractions the pilot evaluation flagged
  and could not explain.

**HTS mode categories — the package's own data document, verbatim:**
`Other` includes **Taxi/rideshare/carshare, wheelchair, bicycle, aircraft**.
So (a) **motorcycle is NOT in `Other`** — it sits inside `Vehicle driver`/
`Vehicle passenger`, meaning **`car` and `ride` targets have always silently
contained motorcycles**; (b) **`bike` is validated against a bucket holding
point-to-point trips**. [`fit.py:49`](../../../../src/calibrate/fit.py)'s
caveat is WRONG and must be corrected when touched.

**A POPULATION DEFECT, found and NOT yet fixed.**
`build_population.py`'s docstring claims "age-conditional labour force status
(G46)". It is not: **one flat 15+ employment rate from G43 is applied to every
adult**. Result — **65–74 modelled at 52.2% employed, 75+ at 47.7%**, against
real ~15–25% and ~3–5%. That is **~35,000 phantom elderly commuters**, ~6% of
the population, and they are exactly the population that RIDES rather than
drives. Also `student_status` is `full_time` for **100% of under-18s**,
including all 22,115 aged 0–4. Children are otherwise correct (0 employed,
0 licensed, tours thinned, cannot escort). **Sequencing note: the owner
directed the coupling first, and that direction is recorded, not argued — but
coupling validated against this population will need re-validating after.**

**Convergence pilots** (evaluated in
[`docs/audit/CONVERGENCE_PILOT_EVALUATION.md`](../audit/CONVERGENCE_PILOT_EVALUATION.md)):
MAE 6.95 pp at 25% (car −1.2, ride **+16.6**, walk −12.7, pt −3.4, bike +0.8);
occupancy **0.64 vs 0.35 observed**; counts −92% mean, 7 zero stations, V113
60 vs 44,885 (#20/#30 reopen conditions MET). Run economics: 33.3 s/iter @10%,
90.2 s @25%; ~24 GiB fixed + 0.09–0.3 MB/agent → 100% needs ~80–160 GiB heap.
**Early-iteration baseline at 25% is ~42 s/iter** (iter 0 = 106 s; iter 10
writes events) — use this, not the 90 s median, to judge a short probe.

**Phases:** P0–P3 ✅ · **P4 in progress** · P5–P7 not started.

---

═══════════════════════════════════════════════════════════════════════════════
§3  ★ YOUR JOB: THE RIDE PAIRING, TIER 1
═══════════════════════════════════════════════════════════════════════════════

### 3.0 What was tried and REVERTED — read this before proposing joint plans

A full socnetsim joint-plans implementation was built and then **deleted from
history by owner instruction** (the branch was reset to the #5 commit). It is
NOT in the repo. What it cost and taught:

- socnetsim `2027.0-2026w25` exists and **links cleanly** against the MATSim
  that pt2matsim 26.6 shades (same build; zero overlapping classes). Its
  `PassengerRoute.getDriverId()` / `DriverRoute.getPassengersIds()` are exactly
  the representation we want, and `JointActingTypes` gives `car_driver`,
  `car_passenger` and a **`joint` interaction activity** (pickup as structure,
  not a penalty).
- **It is ~10× too slow.** A 25% probe on identical inputs: iteration 0 alone
  ran **>16 minutes and had not finished**, against a ~42 s baseline. **The cost
  is NOT the group replanning** — it is inside the mobsim:
  `CourtesyEventsGenerator` fires an event for **every social-contact pair at
  every activity start/end** (16.7 M events by sim-hour 15), which is
  socnetsim's joint-**activity** machinery, a different research question from
  joint **trips**.
- Adding a contrib is a **§14 toolchain change** that invalidates every prior
  run. It also exposed a **still-unfixed hole**: `controler_sha256()` hashes
  only `src/java/`, so a jar change alters the model and leaves the run
  identity untouched — a resume would hand back a stale result. **Fix that
  when any toolchain change actually lands.**
- Two integration traps if anyone returns to it: `SocialNetworkConfigGroup`'s
  group name is **`socialNetwork`** (capital N), and `JointScenarioUtils.
  loadScenario()` **does NOT read the social network** — you must call
  `SocialNetworkReader` yourself or every consumer is injected null and the run
  dies in an event thread. Also socnetsim's **XML strategy config is broken**
  against this MATSim: the alias table rewrites parameterset type `strategy` →
  `replanning` and `createParameterSet` throws on it; strategies must be set
  programmatically.

**DECISION (owner, 18 Aug): do NOT use joint plans. Build the pairing as a
lookup.**

### 3.1 The design — pairing is like boarding a bus, not co-optimising

What makes boarding a bus cheap is that the timetable is **fixed before
routing**, so the passenger does a lookup. A household car can work the same
way: a passenger leg only ever needs to **name a driver**, and the candidate
set is the household — mean ~1.5 licensed adults, never more than 9.

**Where the pairing happens: a `BeforeMobsim` listener.** MATSim's loop is
`replan → all plans final → mobsim`. At that boundary every selected plan is
stable and nothing will move until the mobsim runs. **That is our timetable.**
Pairing there is valid for that iteration and re-made the next — exactly as a
pt connection is re-found on each re-route.

**This dissolves the objection that sent the previous attempt to socnetsim.**
A pairing baked into *plans* is destroyed by `SubtourModeChoice` (weight 0.10,
`ride` in its mode list). A pairing made *after* replanning is not.

**Cost:** `O(ride legs × household size)` ≈ 50k × ~2 at 25%. No plan-composition
search anywhere. Target: **< 5 s/iteration added**. Measure it; if it exceeds
that, stop and report rather than proceeding.

**TIER 1 IS THE APPROVED FIRST TARGET (owner, 18 Aug).** Definition:

> A **paired** passenger takes the **driver's realised travel time** plus a
> declared pickup dwell. Occupancy is **counted from the pairings**. **No
> mobsim change.** An **unpaired** leg behaves exactly as it does today.

That makes Tier 1 a strict improvement with a bounded blast radius, and it is
what kills both the fixed ~5 s residual and the fraction-dependence. **Tier 2**
— passenger as a real `MobsimPassengerAgent` inside the vehicle, seats binding
physically — becomes an increment, not a prerequisite.

### 3.2 RETURN TRIPS: pair legs INDEPENDENTLY, not as round trips (thought out)

The instinct is that a child driven to school must be driven home, so the pair
should be solved together. **That is wrong, for four converging reasons:**

1. **`ride` is correctly not chain-based.** `chainBasedModes = car,bike`. A
   chain constraint exists to bring a *vehicle* back to where it was parked; a
   passenger owns no vehicle. MATSim already permits "driven in, bus home".
2. **Asymmetric lifts are the realistic case.** Dropped off on a parent's way
   to work, then walking or catching a bus home, is ordinary. Forcing symmetry
   would MANUFACTURE car trips — the exact direction of error this project is
   most exposed to.
3. **The driver's return is already modelled.** In the school-run case the
   parent's `HX` escort tour is home→school→onward in B2 already. The empty
   return leg is the *driver's* trip and is already on the network.
4. **Feasibility is already enforced by the time window.** If the parent is at
   work at 15:30 their plan holds no car leg in the window, so the return
   simply does not pair. Independent pairing cannot produce "child rides home
   in a car that is at work".

**The obligation this creates:** count and report the unpaired share **split by
direction**. A large unpaired-*return* share is a genuine finding — it would
mean B2 generates ride demand no household can serve, which is a DEMAND defect,
not a coupling defect. Under Tier 1 an unpaired leg is exactly today's
behaviour, so there is no regression risk in letting it happen.

### 3.3 THE SCENARIOS, AND THE DATA FOR EACH — searched 18 Aug

**The headline finding: commute carpooling is RARE, and ride demand is
overwhelmingly non-commute.** Measured from `census2021_G62_SA1.csv`, already
in the package and currently read only for the employment rate:

| journey to work, five LGAs, 2021 | persons | share |
|---|---:|---:|
| Car as driver | 177,701 | 56.03% |
| **Car as passenger** | **10,628** | **3.35%** |
| Train / Bus / Walk / Bike | 231 / 1,188 / 5,560 / 940 | — |

**Passenger:driver ratio for COMMUTE = 0.0598**, against an all-purpose HTS
`Vehicle passenger` share of **18–32% of trips**. Whatever the ride demand is,
it is not colleagues carpooling to work.

| # | Scenario | Data available | Grade | Where |
|---|---|---|---|---|
| 1 | **Child → school** (dominant) | Private vehicle = **61% of school trips** nationally (2025); **~4 in 10** children living <1 km are still driven; primary: **75% private-school vs 62% public** | literature | Aust. School Travel Survey / Univ. Sydney 2026 |
| 2 | **Child → school, parent continues to work** | no direct split | **NONE** | infer from HX chaining (`B.activity.p_intermediate_stop['HX']` = 0.15) |
| 3 | **Elderly driven** | NSW 60+ licence holding rose **22% → 28%** (2010→2024); family/informal transport is a major mode post-cessation; women cease earlier | literature, qualitative | Monash review; medRxiv 2025 |
| 4 | **Work with colleague/partner** | **3.35% of JTW, ratio 0.0598, at SA1** | **OBSERVED** | `census2021_G62_SA1.csv`, IN PACKAGE |
| 5 | **Driver side, all purposes** | `Serve passenger` = **10–19.5% of journeys** by LGA | **OBSERVED** | `hts_purpose.csv`, IN PACKAGE |
| 6 | **All-purpose passenger share** | `Vehicle passenger` **18–32% of trips** by LGA | **OBSERVED** | `hts_mode.csv`, IN PACKAGE |
| 7 | **Ride trip length / duration** | HTS `TRIP_AVG_DISTANCE` / `TRIP_AVG_TIME` for Vehicle passenger, Newcastle LGA | **OBSERVED** | `C4_mode_constraints.json` |
| 8 | **Occupancy** | **0.35** passengers/driver, range 0.25–0.394 | declared | registry, `C.constraint.passenger_per_driver` |
| 9 | **Shopping / social shared trips** | only inside the aggregate `Vehicle passenger` and `Serve passenger` rows | partial | HTS |
| 10 | **Non-household lift** (friend, colleague from another household) | **NO TARGET ANYWHERE** | **NONE** | do not build; state as a limitation |
| 11 | **Who drives whom inside the household** | **NO TARGET** | **NONE** | derive from licence + vehicle only |
| 12 | **Return-trip asymmetry** | **NO TARGET** | **NONE** | report the unpaired-return share as a diagnostic |

**HTS carries no age split** — the by-LGA and by-SA3 workbooks have a
Demographics sheet with population/households/vehicles only. So scenarios 1 and
3 are **literature-graded, swept, never pinned**, and neither may be used as a
validation target: the 67/143 split is pre-registered and does not grow.

**Structural facts the pairing must respect** (measured from B1):

- **26.2% of households are lone-person** — 64,334 people with no possible
  in-household driver, ever. They still make `Vehicle passenger` trips in HTS;
  that difference IS the non-household lift we cannot observe.
- **91.5% of under-15s** have an in-household licensed driver; ~4.4% do not.
- **77.3% of the population** is ride-eligible under the existing
  `rideAvail` rule (household vehicle AND another licence holder).
- Plans carry **external/through agents in the `9xxxxxxxx` id space** (base
  `B.external.person_id_base` = 900000000) with no household at all. Any
  household lookup must tolerate them.

**Scenarios that need an explicit decision and have no data to settle them:**
**(7) vehicle contention** — two licensed adults, one car, overlapping car legs;
this is ALREADY unenforced in the model and the pairing makes it visible.
**(13) who adapts** — the passenger's departure must shift to the driver's;
declare a tolerance window (`B.ride.pairing_window_min`) and declare that the
**passenger adapts**, since the driver's plan cascades.

### 3.4 After the pairing, in order

1. **Taxi + rideshare** ([`docs/design/point-to-point-mode.md`](../design/point-to-point-mode.md)):
   fares measured (flagfall $5.17, $2.61/km first 12 km), fleet ~175 taxis
   (literature), inferred band 10k–35k trips/day. **Uber goes WITH taxis** —
   HTS classes them together, and the network physics differ from a private
   ride (a rideshare trip adds **deadhead**, ~40–50% of TNC vehicle-km; a
   private ride adds ≈zero net vehicle-km). Carving it out of `Other` **shrinks
   the bike target**; the split is **inferred, declared and swept** (owner
   decision, 18 Aug). Validate against the band as a **constraint, never a
   target**.
2. **The elderly employment defect** (§2) — and re-validate the pairing after.
3. **#14** calibrated base: ASCs on era 3 (2018), HELD FIXED; log the departure
   BEFORE any result is seen.
4. **#24** freight, own PR: real `truck` mode with vehicle type + PCE.
5. **Motorcycle** stays declined — HTS gives **no motorcycle target at all**
   (it is inside `Vehicle driver`/`passenger`). Vehicle-registration data gives
   FLEET share, not TRIP share; any split would be inferred, and it would
   shrink both the car and ride targets.
6. **P5** — SUMO harness; still deliberately unsimulated.

---

═══════════════════════════════════════════════════════════════════════════════
§4  WHAT INVALIDATES YOUR WORK
═══════════════════════════════════════════════════════════════════════════════

- **No multi-hour run without owner approval** (§0). State cost, get a yes.
- **Nothing pre-rebuild is comparable to anything post-rebuild.** The pilot
  arms ARE valid baselines right now — `controler_sha256` matches. **Tier 1
  changes the model**, so post-pairing runs are a new comparison family.
- **NEVER compare across sample fractions** (1% is a plumbing fraction), and
  `target_lga_pct`, never `all_residents_pct`.
- **THE 67/143 SPLIT IS PRE-REGISTERED.** Never calibrate on, re-split or peek
  at a holdout row; `fit.py` enforces it. Need one? SAY SO AND STOP.
- **One build of the network per comparison.** Threads = 10, part of run identity.
- **No invented data.** Scenario 1/3 values are literature, labelled and swept.
- **A run without `_run.json` is not a result.**

---

═══════════════════════════════════════════════════════════════════════════════
§5  EXACT STATE — 18 August 2026
═══════════════════════════════════════════════════════════════════════════════

| | |
|---|---|
| Branch | `praneetdhoolia/convergence-pilot-arms` at **`da563ac`**, **pushed** (force-pushed after the socnetsim revert). Clean tree |
| `main` | the merged 16 Aug rebuild (PR #38); CI green |
| Toolchain | **3 pinned components** — JDK 25.0.4+7, pt2matsim 26.6, SUMO 1.27.1. socnetsim was pinned and is now REMOVED |
| Java | 6 sources in `src/java/citysim/`; identity `eee4fdfa…` = the pilots' |
| Registry | **298 fields** (#5 added `RUN.relaxation.settle_margin_iterations`); ledger **0** `--strict`; reach 69/69 |
| `results/` | `conv1000_10pct` + `conv1000_25pct` (valid baselines) · `smoke_postrebuild` · `_aborted_20260816/` · ⚠ `S2_WEEKDAY_f025_i1000_s20260810` (no `_run.json`) |
| Machine | 63.5 GiB RAM, 24 logical cores, 2-channel laptop; memory is the binding constraint |
| Open issues | **5** — #9 #14 #24 #28 #31 (**#5 CLOSED 18 Aug**; #20/#30 reopen conditions met, actions pending) |
| **Results** | **NONE. Nothing in this repository is an output of the model.** |

### Bootstrap reading, in this order

```
cities/newcastle/docs/STATUS.md                               the board + numbered plan
cities/newcastle/docs/audit/CONVERGENCE_PILOT_EVALUATION.md   the pilot evidence
cities/newcastle/docs/design/point-to-point-mode.md           taxi dossier + build plan
cities/newcastle/docs/DECISIONS.md                            START AT ITS INDEX (§9.43 = #5)
.claude/CLAUDE.md                                             conventions + hard constraints
```

---

═══════════════════════════════════════════════════════════════════════════════
§6  DECISIONS TAKEN — do not re-litigate
═══════════════════════════════════════════════════════════════════════════════
• **#5 IS DECLARED AND CLOSED** at 1000 with a snap-aware drift window. The
  1500 probe was cancelled by the owner; the residual creep is declared
  uncertainty. Do not relaunch it.
• **RIDE FIX = the §3.1 BeforeMobsim pairing, TIER 1.** NOT joint plans —
  socnetsim was built, measured at ~10×, and REVERTED by owner instruction.
  Do not reintroduce it without new evidence about the courtesy-event cost.
• **RETURN TRIPS PAIR INDEPENDENTLY**, not as round trips (§3.2). Report the
  unpaired share by direction.
• **DO NOT add `ride` to qsim main modes** (phantom vehicles: B2 already
  generates the escort driver's car) and **do not add `ride` to
  `chainBasedModes`**. eqasim's `PassengerConstraint` is a trip-level
  biconditional on `getInitialMode()` that consults no driver — it compiles,
  runs, constrains nothing and reports success.
• **A PICKUP FRICTION IS NOT A FITTED PARAMETER.** The measured residual is
  ~5 s; a 1-minute friction is 5–12× it.
• **NON-HOUSEHOLD LIFTS ARE NOT BUILT** — no target exists. Stated limitation.
• **TAXI/RIDESHARE**: re-opened on new evidence; Uber goes with taxis; the
  bike/point-to-point split is inferred, declared and swept; constraint never
  target. Owner said NO to lodging data requests — infer from open sources.
• **DELIVERABLE 5 TAKES §8.5's FIRST BRANCH:** ASCs on era 3 (2018), HELD
  FIXED. LOG THE DEPARTURE BEFORE ANY RESULT IS SEEN.
• SCATS refused by policy, journey-linked Opal unpublished (3–15 min sweep),
  charging dwell field-measurement-only — all swept, never pinned. Pre-tram
  signal count stays 14. The 30 h qsim window is correct.
• ONE ARM AT A TIME. n_replications stays 30 until seed variance is MEASURED.
• STILL DECLINED: touching the 143 holdouts; deleting the 13 Opal card-type
  rows; weather in mode choice; **motorcycle as its own mode** (no target —
  the taxi re-opening does NOT extend to it); year-long simulation.

---

═══════════════════════════════════════════════════════════════════════════════
§7  TRAPS — each has already cost a day (or nearly)
═══════════════════════════════════════════════════════════════════════════════
1. **HEREDOCS MANGLE OR FAIL — bash AND PowerShell.** Write scripts with the
   Write tool, run the file. This bit again this session.
2. **`compileall` does not catch a NameError.** Import the module and call it.
3. Everything is seeded **20260810**. After ANY registry edit: `render_docs.py`
   AND `render_schema.py`. After any data change: `normalise_eol.py` →
   `build_manifest.py` → `normalise_eol.py`.
4. The layers contract carries no machine state.
5. `pkill` does not work; PowerShell `Stop-Process`, then VERIFY it died.
6. Branch `<git-handle>/<short-kebab>`, never `claude/*`. No attribution
   trailers, no session links. **Keep `STATUS.md` current in the SAME commit** —
   this was violated twice this session and had to be repaired.
7. **Verify the CONSUMER, not the mechanism.** Reading code has never once
   caught a dead binding here. It also caught a real defect this session: a
   hand-written XML file parsed fine by inspection and died at MATSim's reader.
8. **Reproduce a defect before attributing it.** The previous brief's fix (a)
   was already implemented; three sessions could have been spent "adding" it.
9. **Big agency PDFs (TfNSW, IPART) return HTTP 403 to WebFetch.** The HTS data
   document is ALREADY IN THE PACKAGE at
   `data/raw/hts/hts_data_document_2020_2024.pdf` — read it locally.
10. **A DOCTYPE in a MATSim input sends the parser to the network** for a DTD;
    what came back was an HTML error page and the parse died. Omit it.
11. **`results/` has a stray run with no `_run.json`** (§0). Do not treat it as
    evidence.
