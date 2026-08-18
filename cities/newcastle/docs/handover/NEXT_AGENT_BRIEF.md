# Brief for the next agent — TIER 1 IS BUILT; THE DEMAND CANNOT SUPPLY A DRIVER

*Rewritten 18 August 2026, after the Tier 1 ride pairing was built, wired,
verified at the consumer, and MEASURED to pair almost nothing — because the
demand it draws on does not contain the drivers. This is a HANDOVER, not a
source of truth: where it disagrees with [`STATUS.md`](../STATUS.md),
[`DECISIONS.md`](../DECISIONS.md) or
[`.claude/CLAUDE.md`](../../../../.claude/CLAUDE.md), those win. Paste it whole
to start a session cold.*

---

═══════════════════════════════════════════════════════════════════════════════
§0  DO THIS FIRST
═══════════════════════════════════════════════════════════════════════════════

```bash
python src/setup/bootstrap_toolchain.py --verify   # ~1 min, COMPILES THE JAVA (8 sources now)
python tests/check_manifest.py                     # committed subset intact
python src/registry/check_hardcoding.py --strict   # must exit 0
```

**⚠ OWNER DIRECTIVE: NO MULTI-HOUR RUNS WITHOUT EXPLICIT OWNER APPROVAL.**
"We can't afford to run full-day runs every now and then." Your lane is code,
declarations and short verification runs. State the cost and get a yes before
anything long.

**`results/` right now:** `conv1000_10pct` and `conv1000_25pct` (both rc=0, both
evaluated). ⚠ **They are baselines for the PRE-pairing model only** — §9.44
changed the model and §9.45 changed which agents are sampled, so nothing run
from here is comparable with them. `smoke_postrebuild`;
`ride_pairing_probe` (a 3-iteration 1% PLUMBING PROBE, not a result);
`results/_aborted_20260816/` is quarantine; ⚠ `results/S2_WEEKDAY_f025_i1000_s20260810/`
is a dead run with no `_run.json` — not a result, not quarantined, owner may delete.

**`--iterations` below 250 is REFUSED by the resolver.** A short probe needs
`allow_outside_sweep` in a run overlay with a written justification —
[`ride_pairing_probe.json`](../../overlays/runs/ride_pairing_probe.json) is the
worked example. Do not fight the guard; it is correct.

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

**That "CHECKED, not assumed" clause has now caught its first defect** — see
§2, `RUN.sample.unit`. Keep checking it; it is not decoration.

| | status | evidence |
|---|---|---|
| Cars | ✅ | qsim `mainMode`, 175,560 links |
| Buses | ✅ | 1,448 vehicles, PCE 2.8, sharing **22,102 road links with cars** |
| Trains | ✅ | 332 vehicles, 6,766 dedicated rail links |
| Light rail | ✅ | 252 tram vehicles, incl. **21 links shared on-street** |
| Ferries | ✅ | 107 vehicles (Stockton) |
| **Car passengers** | ⚠ **PAIRED, still teleported** | Tier 1 built (§9.44). **Pairs <0.1% — the demand has no drivers to name** |
| Motorbikes | ❌ absent | silently inside `car`/`ride` targets — DECLINED, no target exists |
| Taxis / Uber | ❌ absent | inside the `Other`/bike bucket (§4) |

| # | Goal | State |
|---|---|---|
| **G1** | The light-rail counterfactual (calibrated base → S0–S6 → 143 sealed holdouts → findings with bands) | Inputs trustworthy; #5 closed; **the active lane is now the escort↔escorted binding in B2** |
| **G2** | City-agnostic simulator | ✅ 13 CI assertions; ledger 0 `--strict`; reach **74/74** |

The law: **every value DECLARED in `cities/<city>/registry/` and REACHING the
model through the resolver.** 9 of 10 rail forecasts overestimate patronage
(avg +106%); a flattering answer is the EXPECTED failure mode.

---

═══════════════════════════════════════════════════════════════════════════════
§2  WHAT IS DONE — do not redo any of it
═══════════════════════════════════════════════════════════════════════════════

**#5 IS CLOSED (§9.43).** `RUN.controler.last_iteration` = **1000**, `measured`.
Both arms report `relaxed: true` at +0.22 / +0.17 pp. **Declared uncertainty:**
~2 pp of pre-cutoff search creep never measured (the 1500 arm was cancelled by
the owner). §9.45 does NOT invalidate this — the horizon was measured on
post-snap settling, a property of the search rather than of which agents were drawn.

**★ TIER 1 OF THE RIDE PAIRING IS BUILT AND VERIFIED (§9.44).**

- [`RidePairingEngine.java`](../../../../src/java/citysim/RidePairingEngine.java) —
  a `BeforeMobsim` listener. Each `ride` leg names a household member whose
  `car` leg it could be inside; a **paired** passenger takes that driver's
  **realised** (previous-iteration) travel time, an **unpaired** one behaves
  exactly as before.
- **The mechanism, verified against bytecode not API docs:**
  `decideOnLegTravelTime` is `route.getTravelTime().or(leg.getTravelTime())`, so
  the **route's** time wins, and both routing modules set leg and route together.
  The engine therefore writes **only the route's time**, which leaves the
  router's estimate in `leg.getTravelTime()` as a self-refreshing baseline that
  survives plan copying. **No side map, no mobsim change.**
- **Verified at the CONSUMER:** in the probe, 356 legs ended with route ≠ leg
  time, and every unambiguous case teleported on the **route** value. Realised
  lookup fires from iteration 1.
- **Blast radius MEASURED against a control** (`ride_pairing_25pct_control`,
  the same run with `pairing_enabled` false): per-iteration mode share is
  **bit-identical to 17 significant figures**, while **7 legs were rewritten in
  the paired arm and 0 in the control** and `scorestats` differ by 3.8e-05. Both
  halves are needed — the rewrite count proves it is not a no-op, the identical
  mode share proves it touched nothing else.
- **Tested at two horizons** (committed overlays, both rc=0, both flat):
  **1% × 50** for durability across `ReRoute`/`SubtourModeChoice` (5–6 ms/iter)
  and **25% × 10** for scale (184–310 ms/iter, **0.4% of an iteration** on
  136k agents). Cost scales with population and nothing else. 1% alone is NOT
  sufficient — it is a plumbing fraction (§9.12) and a mechanism that transmits
  realised congestion cannot be judged there.
- Five declared fields `B.ride.*`; `ridePairing` module in every emitted config;
  `ride_pairing.csv` written per iteration with the unpaired share **split by
  direction**.

**★ AND THE MEASUREMENT THAT REFRAMES THE LANE.**
[`measure_ride_pairability.py`](../../../../src/analyse/measure_ride_pairability.py),
on the two relaxed arms:

| | 10% | 25% |
|---|---:|---:|
| ride trips | 79,372 | 185,170 |
| in a household that drives **at all** that day | 32.6% | 43.1% |
| **sharing an OD pair with a household car trip, at ANY time** | **0.039%** | **0.104%** |
| pairable under the declared rule (`both_links`, ±15 min) | 0 | **7** |

**`ride` is 32.7% of trips and essentially none of it can physically happen.**
Two independent causes:

1. **The sampler was shredding households — FIXED (§9.45), and it bought almost
   nothing, which was MEASURED not assumed.** The household-sampled 25% arm pairs
   at 0.00004 — the same rate as the person-sampled one. Keeping households
   intact raises the share of ride legs whose household drives AT ALL (structural,
   and the real defect), but not OD-coincidence, because B2 never co-locates them.
   **So cause 2 below is the whole of the remaining problem.** The subsample hashed
   the PERSON id, so a household of size *n* kept *f·n* members and the chance of
   keeping any co-member was `1−(1−f)^(n−1)` — 0.14 at 10%, 0.32 at 25%. Every
   household mechanism was being decided by the *sampler*, differently at each
   fraction. `RUN.sample.unit` = `household` now; the sample still nests, is
   still seeded, and `unit = person` reproduces the old draw byte for byte.
   Membership travels as a `householdId` person attribute — one mechanism, read
   by both the sampler and the Java.
2. **B2 draws an escort tour's destination from a DISTRIBUTION, not from the
   person being escorted — OPEN, and it is your lane (§3).**

**HTS mode categories, verbatim:** `Other` = Taxi/rideshare/carshare,
wheelchair, bicycle, aircraft. So motorcycle is **not** in `Other` — it sits
inside `Vehicle driver`/`passenger`, and `car`/`ride` targets have always
silently contained motorcycles. [`fit.py:49`](../../../../src/calibrate/fit.py)'s
caveat is WRONG and must be corrected when touched.

**A POPULATION DEFECT, found and NOT fixed.** `build_population.py` claims
age-conditional labour force status (G46); it applies **one flat 15+ employment
rate** from G43 to every adult — **65–74 at 52.2% employed, 75+ at 47.7%**
against real ~15–25% and ~3–5%. **~35,000 phantom elderly commuters**, and they
are exactly the population that RIDES. Also `student_status` is `full_time` for
**100% of under-18s**, including all 22,115 aged 0–4.

**Phases:** P0–P3 ✅ · **P4 in progress** · P5–P7 not started.

---

═══════════════════════════════════════════════════════════════════════════════
§3  ★ YOUR JOB: BIND THE ESCORT TOUR TO THE PERSON BEING ESCORTED
═══════════════════════════════════════════════════════════════════════════════

**This is the change that makes Tier 1 bite.** It is a DEMAND change, in
[`build_activity_chains.py`](../../../../src/build/build_activity_chains.py),
not a coupling change — the coupling is built and waiting.

### 3.1 The mechanism, inventoried

B2 **does** generate escort tours — `HX` is a real purpose and there were
**44,258 escort trips** in the relaxed 25% arm. (The note in
`B.counts.vehicles_per_ride_leg`'s description that "B2 generates none" is
STALE — correct it when you touch it.) What is missing is the **binding**:

- `PURPOSES` includes `HX`; only licence holders draw one
  (`B.activity.escort_requires_licence`).
- `ATTRACTION_ALIAS = {'HX': 'HE'}` — an escort destination draws from the
  **education attractor vector**, i.e. from the same *distribution* a child's
  school is drawn from, never the same *instance*.
- `DEPART['HX'] = DEPART['HE']` — same for the departure time.

So a parent escorts to *a* school at *a* plausible time while their own child
travels to *another* school at *another* time. Measured consequence: **0.10% of
ride trips share an OD with a household car trip.** Reading the code would not
have found this; the measurement did. Reproduce it before changing anything:

```bash
python src/analyse/measure_ride_pairability.py --run conv1000_25pct
```

### 3.2 What the fix has to do, and what it must NOT do

**Do:** when a person draws an `HX` tour, bind it to an actual household
member's already-drawn trip — take that member's destination and departure, and
mark the escorted person's corresponding trip as the one being served.

**Must not:**
- **Invent a target.** There is **NO observation anywhere** of who drives whom
  inside a household (§3.3 row 11 of the previous brief still holds). Derive the
  eligibility from **licence + vehicle only**, exactly as `rideAvail` does, and
  declare every choice with a sweep.
- **Manufacture trips.** The `HX` tour rate is already calibrated to
  `Serve passenger` = 10–19.5% of journeys by LGA (OBSERVED, `hts_purpose.csv`).
  Binding must **re-target existing HX tours**, not add them. If the bound
  destination changes the HX trip-length distribution, that is a real effect and
  must be reported against the observed HX mean (6.4 km) — not tuned away.
- **Force symmetry.** Return trips pair INDEPENDENTLY (§9.44). A passenger owns
  no vehicle, `ride` is correctly not chain-based, and forcing a return lift
  would manufacture car trips — the direction of error this project is most
  exposed to.
- **Touch the 143 holdouts.**

**The measured direction split says the failure is UNIFORM**, not asymmetric:
outbound and return unpaired shares are within 0.3% of each other at every rule
and window. So there is no return-specific demand defect to chase.

### 3.3 The data that exists for each scenario, unchanged from the last search

| # | Scenario | Data | Grade |
|---|---|---|---|
| 1 | **Child → school** (dominant) | private vehicle = **61% of school trips** nationally; **~4 in 10** children under 1 km still driven | literature |
| 3 | **Elderly driven** | NSW 60+ licence holding 22%→28% (2010→2024); family transport major post-cessation | literature |
| 4 | Work with colleague/partner | **3.35% of JTW, passenger:driver 0.0598**, at SA1 | **OBSERVED** (`census2021_G62_SA1.csv`, in package) |
| 5 | Driver side, all purposes | `Serve passenger` **10–19.5% of journeys** | **OBSERVED** (`hts_purpose.csv`) |
| 6 | All-purpose passenger share | `Vehicle passenger` **18–32% of trips** | **OBSERVED** (`hts_mode.csv`) |
| 8 | Occupancy | **0.35** passengers/driver (0.25–0.394) | declared, `C.constraint.passenger_per_driver` |
| 10 | **Non-household lift** | **NO TARGET ANYWHERE** | do not build; stated limitation |
| 11 | **Who drives whom in the household** | **NO TARGET** | licence + vehicle only |

**Commute carpooling is RARE** (passenger:driver 0.0598 for JTW against 18–32%
of all trips), so the ride demand is overwhelmingly **non-commute** — which is
why the school run and the elderly lift are the scenarios that matter.
**HTS carries no age split**, so 1 and 3 are literature-graded, swept, and may
never be validation targets.

**Structural facts the binding must respect** (measured from B1):
**26.2% of households are lone-person** — 64,334 people with no possible
in-household driver, ever; **91.5% of under-15s** have an in-household licensed
driver; **77.3%** of the population is ride-eligible; plans carry
**external/through agents in the `9xxxxxxxx` id space with no household at all**
and any household lookup must tolerate them (the engine already does).

### 3.4 A second, smaller incoherence found in the same measurement

**4,791 escort trips were made by `ride`** — a passenger being driven in order
to convey somebody. `B.activity.escort_requires_licence` constrains
*generation*; mode choice may still turn the tour into a ride. Fix it where the
lock already exists: the `lockedMode` attribute and
`AvailabilityModesCalculator` are the precedent.

### 3.5 After that, in order

1. **The elderly employment defect** (§2) — and re-validate the pairing after.
2. **Taxi + rideshare** ([`point-to-point-mode.md`](../design/point-to-point-mode.md)):
   fares measured (flagfall $5.17, $2.61/km first 12 km), fleet ~175 taxis,
   inferred band 10k–35k trips/day. **Uber goes WITH taxis.** Carving it out of
   `Other` **shrinks the bike target**; the split is inferred, declared, swept.
   Validate against the band as a **constraint, never a target**.
3. **#14** calibrated base: ASCs on era 3 (2018), HELD FIXED; log the departure
   BEFORE any result is seen.
4. **#24** freight, own PR: real `truck` mode with vehicle type + PCE.
5. **Tier 2** of the pairing (passenger as a real `MobsimPassengerAgent`, seats
   binding physically) — an increment, and **not worth building until the demand
   can pair**.
6. **P5** — SUMO harness; still deliberately unsimulated.

---

═══════════════════════════════════════════════════════════════════════════════
§4  WHAT INVALIDATES YOUR WORK
═══════════════════════════════════════════════════════════════════════════════

- **No multi-hour run without owner approval** (§0). State cost, get a yes.
- **The two pilot arms are baselines for the PRE-pairing model ONLY.** §9.44 and
  §9.45 landed together, deliberately, so there is one comparability break and
  not two.
- **NEVER compare across sample fractions** (1% is a plumbing fraction), and
  `target_lga_pct`, never `all_residents_pct`.
- **THE 67/143 SPLIT IS PRE-REGISTERED.** Never calibrate on, re-split or peek
  at a holdout row; `fit.py` enforces it. Need one? SAY SO AND STOP.
- **One build of the network per comparison.** Threads = 10, part of run identity.
- **No invented data.** Scenario 1/3 values are literature, labelled and swept.
- **A run without `_run.json` is not a result.**
- **`controler_sha256()` hashes only `src/java/`.** A jar change would alter the
  model and leave the run identity untouched — still unfixed, fix it when any
  toolchain change actually lands.

---

═══════════════════════════════════════════════════════════════════════════════
§5  EXACT STATE — 18 August 2026
═══════════════════════════════════════════════════════════════════════════════

| | |
|---|---|
| Branch | `praneetdhoolia/convergence-pilot-arms`, clean tree |
| `main` | the merged 16 Aug rebuild (PR #38); CI green |
| Toolchain | **3 pinned components** — JDK 25.0.4+7, pt2matsim 26.6, SUMO 1.27.1. **UNCHANGED by this work** — the pairing adds compiled source beside the shaded jar, not a contrib |
| Java | **8 sources** in `src/java/citysim/` (added `RidePairingEngine`, `RidePairingConfigGroup`) |
| Registry | **304 fields** (5 × `B.ride.*`, 1 × `RUN.sample.unit`); ledger **0** `--strict`; reach **74/74** |
| Plans | regenerated 18 Aug, now carrying `householdId`; 30 run-input sets reassembled, each config carrying a `ridePairing` module |
| Machine | 63.5 GiB RAM, 24 logical cores; memory is the binding constraint |
| Open issues | **5** — #9 #14 #24 #28 #31. **#31 moves from "unmodelled" to "modelled and measured to be starved of supply" — it does NOT close** |
| **Results** | **NONE. Nothing in this repository is an output of the model.** |

### Bootstrap reading, in this order

```
cities/newcastle/docs/STATUS.md                               the board + numbered plan
cities/newcastle/docs/DECISIONS.md  §9.44, §9.45              THE PAIRING AND THE SAMPLER
cities/newcastle/docs/audit/CONVERGENCE_PILOT_EVALUATION.md   the pilot evidence
cities/newcastle/docs/design/point-to-point-mode.md           taxi dossier + build plan
.claude/CLAUDE.md                                             conventions + hard constraints
```

---

═══════════════════════════════════════════════════════════════════════════════
§6  DECISIONS TAKEN — do not re-litigate
═══════════════════════════════════════════════════════════════════════════════
• **#5 IS DECLARED AND CLOSED** at 1000 with a snap-aware drift window. The 1500
  probe was cancelled by the owner; the residual creep is declared uncertainty.
• **THE RIDE PAIRING IS A `BeforeMobsim` LOOKUP, TIER 1, AND IT IS BUILT.** NOT
  joint plans — socnetsim was built, measured at ~10×
  (`CourtesyEventsGenerator`, 16.7 M events by sim-hour 15), and REVERTED by
  owner instruction. Do not reintroduce it.
• **THE SAMPLING UNIT IS THE HOUSEHOLD.** Person-wise sampling made every
  household mechanism a function of the fraction.
• **RETURN TRIPS PAIR INDEPENDENTLY**, not as round trips. Report by direction.
• **DO NOT add `ride` to qsim main modes** (phantom vehicles) **or to
  `chainBasedModes`**. eqasim's `PassengerConstraint` consults no driver: it
  compiles, runs, constrains nothing and reports success.
• **A PICKUP FRICTION IS NOT A FITTED PARAMETER.** The measured residual is
  ~5 s at 25% / ~13 s at 10%, FLAT across distance bins; a 1-minute friction is
  5–12× it. `B.ride.pickup_dwell_s` defaults to **0.0** and is swept, never fitted.
• **`both_links` IS THE DECLARED PAIRING RULE.** It is the only one under which
  handing over the driver's realised time is correct. The looser rules are
  sensitivities — under `window_only` a paired passenger inherits an unrelated
  trip and comes out **+493 to +725 s** wrong.
• **NON-HOUSEHOLD LIFTS ARE NOT BUILT** — no target exists. Stated limitation.
• **TAXI/RIDESHARE**: re-opened; Uber goes with taxis; the split is inferred,
  declared and swept; constraint never target. Owner said NO to data requests.
• **DELIVERABLE 5 TAKES §8.5's FIRST BRANCH:** ASCs on era 3 (2018), HELD FIXED.
  LOG THE DEPARTURE BEFORE ANY RESULT IS SEEN.
• SCATS refused by policy, journey-linked Opal unpublished (3–15 min sweep),
  charging dwell field-measurement-only — all swept, never pinned.
• ONE ARM AT A TIME. n_replications stays 30 until seed variance is MEASURED.
• STILL DECLINED: touching the 143 holdouts; weather in mode choice;
  **motorcycle as its own mode** (no target); year-long simulation.

---

═══════════════════════════════════════════════════════════════════════════════
§7  TRAPS — each has already cost a day (or nearly)
═══════════════════════════════════════════════════════════════════════════════
1. **HEREDOCS MANGLE OR FAIL — bash AND PowerShell.** Write scripts with the
   Write tool, run the file. **This bit again this session**, on an escaped
   quote inside a Python string.
2. **`compileall` does not catch a NameError.** Import the module and call it.
   It also does not catch a `TypeError` from a schema shape — `sweep` may be a
   bare list OR `{"interval": [...]}`, and both are legal.
3. Everything is seeded **20260810**. After ANY registry edit: `render_docs.py`
   AND `render_schema.py`. After any data change: `normalise_eol.py` →
   `build_manifest.py` → `normalise_eol.py`.
4. **VERIFY THE CONSUMER, NOT THE MECHANISM.** Reading code has never once
   caught a dead binding here. This session it earned its keep twice: the
   teleport binding was confirmed by decompiling the pinned jar and then by a
   probe run, and **the direction split shipped silently all-zero** because a
   ride trip's adjacent activity is a `ride interaction` STAGE activity, not the
   real one.
5. **Reproduce a defect before attributing it.** The previous brief's ride fix
   (a) was already implemented; three sessions could have been spent "adding" it.
6. **The hardcoding ledger is not a formality.** It caught a five-number
   reporting grid in a brand-new analysis script this session. Derive the grid
   from the declared sweep instead.
7. `pkill` does not work; PowerShell `Stop-Process`, then VERIFY it died.
8. Branch `<git-handle>/<short-kebab>`, never `claude/*`. No attribution
   trailers, no session links. **Keep `STATUS.md` current in the SAME commit.**
9. **Big agency PDFs (TfNSW, IPART) return HTTP 403 to WebFetch.** The HTS data
   document is ALREADY IN THE PACKAGE at
   `data/raw/hts/hts_data_document_2020_2024.pdf` — read it locally.
10. **A DOCTYPE in a MATSim input sends the parser to the network** for a DTD;
    what came back was an HTML error page and the parse died. Omit it.
