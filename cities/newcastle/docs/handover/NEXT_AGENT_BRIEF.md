# Brief for the next agent — THE GOAL, THE FOUR MISSING MODES, AND A PRUNED PLAN

*Rewritten 18 August 2026 against the owner's goal statement, replacing the
previous brief entirely. It does three things the old one did not: it
**prioritises the four missing modes separately** instead of lumping them, it
**assesses every open task for alignment and proposes deletions**, and it
answers **what kind of work comes next** — code, data, or runs. This is a
HANDOVER, not a source of truth: where it disagrees with
[`STATUS.md`](../STATUS.md), [`DECISIONS.md`](../DECISIONS.md) or
[`.claude/CLAUDE.md`](../../../../.claude/CLAUDE.md), those win.*

---

═══════════════════════════════════════════════════════════════════════════════
§0  DO THIS FIRST
═══════════════════════════════════════════════════════════════════════════════

```bash
python src/setup/bootstrap_toolchain.py --verify   # ~1 min, COMPILES THE JAVA (8 sources)
python tests/check_manifest.py                     # committed subset intact
python src/registry/check_hardcoding.py --strict   # must exit 0
```

**⚠ OWNER DIRECTIVES, both standing:**
1. **NO MULTI-HOUR RUNS WITHOUT EXPLICIT APPROVAL.** State the cost, get a yes.
2. **DO ONE THING RIGHT rather than bloating the repo.** Do not open ten tasks.
   Do not harvest data the model cannot yet consume. Do not build a mode whose
   share is 1% while a mode at 33% is unphysical.

Start from `main` — nothing is in flight.

---

═══════════════════════════════════════════════════════════════════════════════
§1  THE GOAL, AND THE ONE SENTENCE THAT GOVERNS EVERYTHING
═══════════════════════════════════════════════════════════════════════════════

> **A digital twin of any city, traffic-wise: simulate the whole population or a
> percentage of it — and if a percentage, congestion and capacity scale
> accordingly, and whether that scaling actually predicts the correct ridership
> per mode must be CHECKED, not assumed.** Implemented for Newcastle, where the
> light-rail project gives claims we can evaluate. **Every form of transport
> should be IN ACTION physically.**

**"CHECKED, not assumed" is the load-bearing clause.** It has already caught two
defects that reading code never would have:

- `RUN.sample.unit` (§9.45) — the subsample hashed the *person* id, so household
  structure dissolved at a rate set by the sample fraction. Every
  household-coupled mechanism was being decided by the sampler.
- The ride pairing (§9.44) — built, verified, and then measured to pair **fewer
  than 1 ride trip in 1,000**, because the demand contains no drivers to pair with.

Treat every new mechanism the same way: build it, then measure whether it does
anything, and publish the answer when it doesn't.

**The standing risk:** 9 of 10 rail forecasts overestimate patronage (avg
+106%). A flattering answer is the EXPECTED failure mode of this project.

---

═══════════════════════════════════════════════════════════════════════════════
§2  THE NINE MODES — WHAT IS PHYSICAL, AND WHAT EACH GAP IS WORTH
═══════════════════════════════════════════════════════════════════════════════

Measured, not assumed. **Five of nine are already physically in the mobsim** and
must not be rebuilt:

| mode | state | evidence |
|---|---|---|
| Cars | ✅ physical | qsim `mainMode`, 175,560 links |
| Buses | ✅ physical | 1,448 vehicles, PCE 2.8, sharing **22,102 road links with cars** — genuinely competing for capacity |
| Trains | ✅ physical | 332 vehicles, 6,766 dedicated rail links |
| Light rail | ✅ physical | 252 tram vehicles, incl. **21 links shared on-street with cars** |
| Ferries | ✅ physical | 107 vehicles (Stockton) |

**2,139 transit vehicles move every iteration.** The gap is passengers,
motorbikes, taxis and Uber — not the fleet.

### The four gaps, prioritised SEPARATELY by what each is worth

| rank | gap | share of trips | mechanism | data to support it | verdict |
|---|---|---:|---|---|---|
| **1** | **Car passengers (`ride`)** | **32.7%** | **BUILT** (Tier 1, §9.44) but **starved** — pairs <0.1% | occupancy 0.35 OBSERVED; who-drives-whom **no target** | **DO THIS. One demand defect stands between a third of all trips and physicality** |
| **2** | **Freight / heavy vehicles** | **6.52% of vehicles** (MEASURED) | absent — no `truck` mode | share measured from RMS counts; PCE from literature | **DO THIS SECOND.** Cheap, measured, and it changes congestion for *every* mode |
| **3** | Taxis + Uber | **0.4–1.5%** (10k–35k trips/day of ~2.27M) | absent — inside the `Other` bucket | fares MEASURED; fleet literature; volume band INFERRED, no target | **DEFER.** A ~1% refinement must not precede a 33% defect |
| **4** | Motorbikes | unknown, inside `car`/`ride` | absent | **NO TRIP-SHARE TARGET ANYWHERE.** Registration data gives FLEET share, not trip share | **STAY DECLINED.** Any split would be invented, and it would shrink both the car and ride targets |

**Why freight outranks taxis** even though it is not in the goal's list of nine:
it is **measured** rather than inferred, it is **6.5×** the taxi share, and a
heavy vehicle at PCE > 1 changes the travel time of every car, bus and tram
sharing its links. It improves the *denominator* every mode is judged against.
Taxis improve a 1% sliver and rest on an inferred band.

**Why motorbikes stay declined:** the HTS data document is explicit — `Other` =
*Taxi/rideshare/carshare, wheelchair, bicycle, aircraft*. Motorcycle is **not**
in it; it sits inside `Vehicle driver`/`Vehicle passenger`. So `car` and `ride`
targets have always silently contained motorcycles, and carving them out without
a trip-share observation would be invention. ([`fit.py:49`](../../../../src/calibrate/fit.py)'s
caveat states this wrongly and must be corrected when touched.)

---

═══════════════════════════════════════════════════════════════════════════════
§3  WHAT DATA WE ACTUALLY HAVE ON HOW PEOPLE CHOOSE A MODE
═══════════════════════════════════════════════════════════════════════════════

The owner asked for this assessment explicitly. **It is the least comfortable
section in this brief, and it should stay that way.**

### What we have — all of it OUTCOMES, none of it PREFERENCES

| what | source | grade |
|---|---|---|
| Mode share by trip, by LGA | `hts_mode.csv` (NSW HTS) | **OBSERVED** |
| Trip purpose split | `hts_purpose.csv` — incl. `Serve passenger` 10–19.5% | **OBSERVED** |
| Trip length + duration per mode | `C4_mode_constraints.json` | **OBSERVED** |
| Vehicle occupancy 1.35 / passenger:driver 0.35 | HTS, 7 survey years | **OBSERVED** |
| Journey to work, SA1 × mode | `census2021_G62_SA1.csv` — car driver 56.0%, **car passenger 3.35%** | **OBSERVED** |
| Value of time | `C.vot.*`, TfNSW published parameters | literature |
| Patronage / boardings | Opal, **unlinked only** | OBSERVED but unlinked |

### What we do NOT have, and cannot get

- **No stated-preference or revealed-preference survey for Newcastle.** Nothing
  in the package records *why* anyone chose a mode.
- **No journey-linked Opal.** Unpublished. So the actual path a PT passenger
  took — the transfers they accepted, the walk they tolerated — is unobserved.
  Carried as a 3–15 min transfer-penalty sweep, never pinned.
- **No mode-choice model estimated on Newcastle data.** The ASCs are *not*
  estimates.

### The consequence, stated plainly

The behavioural layer is **55 fields: 20 assumed, 12 literature, 11 measured, 8
derived, 4 definition**. **58% of how this model decides a mode is assumed or
imported literature.** We have excellent data on *what people did* and none on
*why*, so the ASCs must be either held fixed on a pre-intervention period or
constrained-and-reported (§8.5) — never fitted to make the answer look right.
That is exactly why §8.5 exists and why ASC absorption is named as the primary
threat to validity.

**The honest implication for the goal:** the twin can be made to *reproduce*
observed mode shares. Whether it *predicts* ridership under an intervention
rests on transferred coefficients, and the sweep bands are the only honest
expression of that uncertainty. **Every headline must carry its band.**

**More outcome data will not fix this.** Harvesting another mode-share table
adds a target, not an explanation. The two acquisitions that *would* move it —
journey-linked Opal and a local preference survey — are unpublished and
non-existent respectively.

---

═══════════════════════════════════════════════════════════════════════════════
§4  ★ WHAT TO DO NEXT — CODE, NOT DATA, NOT RUNS
═══════════════════════════════════════════════════════════════════════════════

The owner asked whether the next work is realigning values, harvesting data, or
testing runs. **It is none of the three. It is two demand-model defects, then a
modelling decision.** Reasoning:

- **Not data harvesting.** The package has 391 committed files and passes 1,456
  checks. The binding constraint is not missing data — §3 shows the one gap that
  matters cannot be filled from any source we can reach.
- **Not runs.** The two convergence arms cost 42 h and are spent. Running the
  model again *now* would spend another 30 h measuring a demand we already know
  is broken in two specific ways.
- **Not value realignment.** Realigning ASCs before the demand is coherent would
  fit the constants to absorb a structural defect — the §8.5 failure mode by name.

### The order, and why

| step | task | why it comes here | ETA |
|---|---|---|---|
| **1** | **Bind the escort tour to the person escorted** (§5) | Unblocks **32.7% of trips**. The coupling is already built and waiting; this is the one defect between it and working | attended 2–3 days |
| **2** | **Fix the elderly employment defect** (§6) | ~35,000 phantom elderly commuters, and they are *exactly* the population that rides rather than drives — so it contaminates step 1's validation | attended 1 day |
| **3** | **Re-measure pairability, then re-validate** | "CHECKED, not assumed." Steps 1–2 either move the 0.1% or they do not, and either answer is publishable | attended 0.5 day + one 25% arm |
| **4** | **#24 freight** — real `truck` mode, vehicle type + PCE | Measured 6.52%; improves the congestion every mode is judged against | attended 1–2 days |
| **5** | **#14 the §8.5 calibration decision** | ASCs on era 3 (2018), HELD FIXED. **Log the departure BEFORE any result is seen.** Only sensible once the demand is coherent | attended 1–2 days |

**Do steps 1–3 and stop.** That is a complete, publishable unit of work. Steps
4–5 are the next session's.

---

═══════════════════════════════════════════════════════════════════════════════
§5  STEP 1 IN DETAIL — THE ESCORT BINDING
═══════════════════════════════════════════════════════════════════════════════

A DEMAND change, in
[`build_activity_chains.py`](../../../../src/build/build_activity_chains.py).

**The mechanism, inventoried.** B2 *does* generate escort tours — `HX` is a real
purpose, **44,258 escort trips** in the relaxed 25% arm. What is missing is the
binding:

- `ATTRACTION_ALIAS = {'HX': 'HE'}` — an escort destination draws from the
  education attractor **distribution**, never the escorted child's actual school.
- `DEPART['HX'] = DEPART['HE']` — same for departure time.

So a parent escorts to *a* school at *a* plausible time while their own child
travels to *another* school at *another* time. Measured consequence: **0.104% of
ride trips share an OD with a household car trip at any time of day.**

Reproduce before changing anything:

```bash
python src/analyse/measure_ride_pairability.py --run conv1000_25pct
```

**Do:** when a person draws an `HX` tour, bind it to an actual household
member's already-drawn trip — take that member's destination and departure.

**Must NOT:**
- **Invent a target.** There is no observation of who drives whom in a
  household. Derive eligibility from **licence + vehicle only**, as `rideAvail`
  does, and declare every choice with a sweep.
- **Manufacture trips.** The `HX` rate is already calibrated to
  `Serve passenger` 10–19.5% (OBSERVED). **Re-target existing HX tours, do not
  add any.** If the binding changes HX trip length, report it against the
  observed 6.4 km mean — do not tune it away.
- **Force return symmetry.** Return trips pair independently (§9.44). Forcing
  symmetry would manufacture car trips — the error direction this project is
  most exposed to. The measured direction split is **uniform** (outbound and
  return within 0.3%), so there is no return-specific defect to chase.

**Structural facts to respect:** 26.2% of households are lone-person (64,334
people with no possible in-household driver, ever); 91.5% of under-15s have one;
77.3% of the population is ride-eligible; external/through agents in the
`9xxxxxxxx` id space have no household and any lookup must tolerate them.

**A second, smaller incoherence in the same family:** 4,791 escort trips were
made *by* `ride` — a passenger being driven in order to convey somebody.
`B.activity.escort_requires_licence` constrains generation; mode choice can
still turn the tour into a ride. Fix where the lock exists: `lockedMode` +
`AvailabilityModesCalculator` are the precedent.

---

═══════════════════════════════════════════════════════════════════════════════
§6  STEP 2 IN DETAIL — THE POPULATION DEFECT
═══════════════════════════════════════════════════════════════════════════════

`build_population.py`'s docstring claims age-conditional labour force status
(G46). **It is not:** one flat 15+ employment rate from G43 is applied to every
adult. Result — **65–74 modelled at 52.2% employed, 75+ at 47.7%**, against real
~15–25% and ~3–5%. That is **~35,000 phantom elderly commuters**, ~6% of the
population, and they are exactly the cohort that rides rather than drives.

Also: `student_status` is `full_time` for **100% of under-18s**, including all
22,115 aged 0–4. Children are otherwise correct (0 employed, 0 licensed, tours
thinned, cannot escort).

G46 is age-conditional and is already in the package. This is a real fix with
real data behind it, not a re-parameterisation.

---

═══════════════════════════════════════════════════════════════════════════════
§7  THE FULL PLAN, ASSESSED — WITH FOUR PROPOSED DELETIONS
═══════════════════════════════════════════════════════════════════════════════

Every open task, its ETA, and **an alignment verdict against the goal**.
[`STATUS.md`](../STATUS.md) §"The plan" is the plan of record and carries the
same numbering; this table adds the assessment the owner asked for.

### Aligned — keep, in this order

| # | task | ETA | alignment |
|---|---|---|---|
| **NEW 4.2.5** | **Escort binding** (§5) | 2–3 d | **CRITICAL** — 32.7% of trips |
| **NEW 4.2.6** | **Elderly employment defect** (§6) | 1 d | **CRITICAL** — contaminates the above |
| 4.2.4 | §8.5 calibration decision + calibrated base (#14) | 1–2 d + 2–3 d wall | **CORE** — G1 depends on it |
| 4.3 | Deliverable 0b: derive 15–25 of the 78 `assumed` fields from data already held | 2–3 d | **HIGH, and under-rated** — attacks §3's 58%-assumed problem directly |
| #24 | Freight `truck` mode, own PR | 1–2 d | **HIGH** — measured, and improves every mode's congestion |
| 5.4 | Scenario × day-type runs S0–S6 (prioritise S0/S1/S2 × WEEKDAY) | wall: weeks | **CORE** — this is the counterfactual |
| 5.5 | Per-run close-out: metrics → fit → summary | ~1 h/run | **CORE** |
| 6.3 | Open the 143 holdouts **once**, at the end | 0.5 d | **CORE** — the pre-registered test |
| 6.4 | Hypothesis tests with every headline bound to its sweep band | 1–2 wk | **CORE** |
| 7.1 | Findings paper | 1–2 wk | **CORE** |
| 4.4 | Taxi + rideshare p2p mode | 2–3 d | **DEFER** — 0.4–1.5% of trips; correct as written, wrong to do now |
| 5.1 | SUMO corridor harness + outer loop | 3–5 d | **KEEP, lower** — answers corridor cost, not ridership |
| 7.2 | Method note on the SCATS refusal | 2–3 d | **KEEP** — cheap, and citable |
| 7.3 / 7.4 | Containerise; publish the data package | 1–2 d each | **KEEP** — deliverables 1 and 2 |

### ⚠ Proposed for deletion or rework — bring these to the owner

| # | task | why it is misaligned | proposal |
|---|---|---|---|
| **5.2** | SUMO version change for pedestrian crossings (`--osm.crossings` segfaults 1.27.1) | A **§14 toolchain change invalidates every prior run**, spent for pedestrian crossings on one corridor. Enormous blast radius, near-zero ridership value | **DELETE** from the plan. Record crossings as a stated corridor limitation |
| **5.3** | Charging dwell field measurement (physical visit to Civic or Crown St) | One tram parameter, already swept, affecting LR travel time marginally. A site visit is disproportionate | **REWORK** to "stays swept, never pinned". Delete the visit |
| **6.1** | Pedestrian counts — temporary counters on Hunter St | Elapsed **weeks** for hypothesis B1 (street-level activity). B1 is a secondary retail-outcome hypothesis, not ridership | **REWORK** — attempt the land-use + modelled-alightings fallback only; if that fails, **report B1 as untestable** rather than buying counters |
| **6.2** | Retail floorspace + vacancy audit (`D.retail.vacancy_rate` is `unobtained`) | Same family as 6.1, same distance from the goal | **REWORK** — scope to what the existing land-use layer supports; do not commission an audit |

**The through-line:** 5.2, 5.3, 6.1 and 6.2 are the four most expensive tasks
per unit of goal in the plan. They are about the *corridor's street life*, not
about *whether the twin predicts ridership per mode*. Cutting them is the
single biggest protection against the owner's "don't bloat the repo" directive.

### Backlog — do not start

2014 public timetable · LiDAR DTM (gradient reaches the behavioural model
through **nothing**, #21) · event attendance · socnetsim joint plans (measured
at ~10×, reverted) · 2013 historical reconstruction (dropped; do not reopen).

---

═══════════════════════════════════════════════════════════════════════════════
§8  WHAT IS DONE — do not redo any of it
═══════════════════════════════════════════════════════════════════════════════

**#5 CLOSED (§9.43).** `RUN.controler.last_iteration` = **1000**, `measured`.
Both arms `relaxed: true` at +0.22 / +0.17 pp. Declared uncertainty: ~2 pp of
pre-cutoff search creep never measured (the 1500 arm was cancelled).

**TIER 1 RIDE PAIRING BUILT, VERIFIED, MERGED (§9.44, PR #40).**
[`RidePairingEngine.java`](../../../../src/java/citysim/RidePairingEngine.java) —
a `BeforeMobsim` listener naming a household driver per `ride` leg; a paired
passenger takes that driver's **realised** travel time, an unpaired one is
untouched.

- **Mechanism verified against bytecode, not API docs.**
  `decideOnLegTravelTime` = `route.getTravelTime().or(leg.getTravelTime())`, and
  both routing modules set leg and route together — so the engine writes **only
  the route's time**, leaving the router's estimate in the leg as a
  self-refreshing baseline that survives plan copying. No side map, no mobsim change.
- **Blast radius MEASURED against a control:** mode share **bit-identical to 17
  s.f.**, **7 legs rewritten vs 0**, `scorestats` differ 3.8e-05.
- **Two horizons:** 1% × 50 (5–6 ms/iter) and 25% × 10 (184–310 ms/iter = **0.4%
  of an iteration**). **Stressed** at `window_only`: 14,406–18,489 pairings an
  iteration at *the same cost* — the cost is the plan WALK, not the pairing.

**SAMPLING UNIT IS THE HOUSEHOLD (§9.45).** And it bought **almost nothing** for
pairability — measured, not assumed: the household-sampled 25% arm pairs at
0.00004, the same as person-sampled. It removes a real fraction-dependence in
"does this household drive at all" (32.6% → 43.1%), but not OD-coincidence.

**Phases:** P0–P3 ✅ · **P4 in progress** · P5–P7 not started.

---

═══════════════════════════════════════════════════════════════════════════════
§9  WHAT INVALIDATES YOUR WORK
═══════════════════════════════════════════════════════════════════════════════

- **No multi-hour run without owner approval.** State cost, get a yes.
- **The two pilot arms are baselines for the PRE-pairing model ONLY.** §9.44 and
  §9.45 landed together so there is one comparability break, not two.
- **NEVER compare across sample fractions** (1% is a plumbing fraction), and
  `target_lga_pct`, never `all_residents_pct`.
- **THE 67/143 SPLIT IS PRE-REGISTERED.** Never calibrate on, re-split or peek at
  a holdout row; `fit.py` enforces it. Need one? SAY SO AND STOP.
- **One build of the network per comparison.** Threads = 10, part of run identity.
- **No invented data.** A value that is not measured is assumed or modelled, and
  must be labelled and swept.
- **A run without `_run.json` is not a result.**
- **`controler_sha256()` hashes only `src/java/`** — a jar change would alter the
  model and leave the run identity untouched. Still unfixed; fix it when any
  toolchain change lands.

---

═══════════════════════════════════════════════════════════════════════════════
§10  EXACT STATE — 18 August 2026
═══════════════════════════════════════════════════════════════════════════════

| | |
|---|---|
| Branch | **start from `main`** — nothing in flight |
| `main` | PR #40 (Tier 1 pairing + household sampling), PR #41 (board currency). CI green |
| Toolchain | 3 pinned — JDK 25.0.4+7, pt2matsim 26.6, SUMO 1.27.1. **Unchanged** by the pairing |
| Java | **8 sources** in `src/java/citysim/` |
| Registry | **304 fields**; ledger **0** `--strict`; reach **74/74** |
| Package | 391 files; `check_package.py` **1,456 checks ALL PASSED**, 2 standing warnings |
| Machine | 63.5 GiB RAM, 24 cores; **memory is the binding constraint** (~24 GiB fixed + 0.09–0.3 MB/agent → a 100% run needs 80–160 GiB) |
| Run cost | 33.3 s/iter at 10%, 90.2 s at 25% → a 1000-iteration arm is 11 h / 31 h |
| Open issues | **5** — #9 #14 #24 #28 #31 |
| **Results** | **NONE. Nothing in this repository is an output of the model.** |

### Bootstrap reading, in this order

```
cities/newcastle/docs/STATUS.md                               the board + numbered plan
cities/newcastle/docs/DECISIONS.md  §9.44, §9.45              the pairing and the sampler
cities/newcastle/docs/audit/CONVERGENCE_PILOT_EVALUATION.md   the pilot evidence
.claude/CLAUDE.md                                             conventions + hard constraints
```

---

═══════════════════════════════════════════════════════════════════════════════
§11  DECISIONS TAKEN — do not re-litigate
═══════════════════════════════════════════════════════════════════════════════
• **#5 DECLARED AND CLOSED** at 1000. Do not relaunch the 1500 arm.
• **THE RIDE PAIRING IS A `BeforeMobsim` LOOKUP, TIER 1, BUILT.** NOT joint
  plans — socnetsim measured at ~10× (`CourtesyEventsGenerator`, 16.7 M events)
  and REVERTED by owner instruction.
• **THE SAMPLING UNIT IS THE HOUSEHOLD.**
• **RETURN TRIPS PAIR INDEPENDENTLY.** Report the unpaired share by direction.
• **DO NOT add `ride` to qsim main modes or `chainBasedModes`.** eqasim's
  `PassengerConstraint` consults no driver: it compiles, runs, constrains
  nothing, reports success.
• **A PICKUP FRICTION IS NOT A FITTED PARAMETER.** Measured residual ~5 s at 25%
  / ~13 s at 10%, flat across bins. `B.ride.pickup_dwell_s` = **0.0**, swept.
• **`both_links` IS THE DECLARED PAIRING RULE** — the only one under which the
  driver's realised time is *correct*. Looser rules are sensitivities; under
  `window_only` a paired passenger comes out **+493 to +725 s** wrong.
• **NON-HOUSEHOLD LIFTS ARE NOT BUILT** — no target exists. Stated limitation.
• **TAXI/RIDESHARE**: Uber goes with taxis; the split is inferred, declared and
  swept; validated as a **constraint, never a target**. Owner said NO to lodging
  data requests.
• **DELIVERABLE 5 TAKES §8.5's FIRST BRANCH:** ASCs on era 3 (2018), HELD FIXED.
  **LOG THE DEPARTURE BEFORE ANY RESULT IS SEEN.**
• SCATS refused by policy; journey-linked Opal unpublished (3–15 min sweep);
  charging dwell swept — never pinned.
• ONE ARM AT A TIME. `n_replications` stays 30 until seed variance is MEASURED.
• STILL DECLINED: touching the 143 holdouts; weather in mode choice;
  **motorcycle as its own mode** (§2); year-long simulation.

---

═══════════════════════════════════════════════════════════════════════════════
§12  TRAPS — each has already cost a day (or nearly)
═══════════════════════════════════════════════════════════════════════════════
1. **HEREDOCS MANGLE OR FAIL — bash AND PowerShell.** Write the script with the
   Write tool, run the file. Bit again last session, on an escaped quote.
2. **`compileall` catches neither a NameError nor a schema-shape `TypeError`.**
   Import the module and CALL it. (`sweep` may be a bare list OR
   `{"interval": [...]}` — both legal.)
3. Everything is seeded **20260810**. After ANY registry edit: `render_docs.py`
   AND `render_schema.py`. After any data change: `normalise_eol.py` →
   `build_manifest.py` → `normalise_eol.py`.
4. **VERIFY THE CONSUMER, NOT THE MECHANISM.** Reading code has never once
   caught a dead binding here. Last session it earned its keep twice — and the
   pairing's **direction split shipped silently all-zero** because a ride trip's
   adjacent activity is a `ride interaction` STAGE activity, not the real one.
5. **Reproduce a defect before attributing it.** A previous brief's "fix" was
   already implemented; three sessions could have been spent adding it.
6. **The hardcoding ledger is not a formality.** It caught a five-number
   reporting grid in a brand-new analysis script. Derive grids from declared sweeps.
7. **A broad log grep will false-positive.** `IllegalArgumentException:
   Unsupported class file major version 69` is **benign and pre-existing** —
   Guice's bundled ASM cannot read Java 25 class files while attaching line
   numbers. It appears in every run including the 31 h pilot. Exclude it.
8. `pkill` does not work; PowerShell `Stop-Process`, then VERIFY it died.
9. Branch `<git-handle>/<short-kebab>`, never `claude/*`. No attribution
   trailers, no session links. **Keep `STATUS.md` current in the SAME commit.**
10. **Big agency PDFs (TfNSW, IPART) return HTTP 403 to WebFetch.** The HTS data
    document is already local at `data/raw/hts/hts_data_document_2020_2024.pdf`.
11. **A DOCTYPE in a MATSim input sends the parser to the network** for a DTD;
    an HTML error page came back and the parse died. Omit it.
