# Brief for the next agent — EVERY MODE IS PHYSICAL; FIX #54, GET THE SEQUENCING RULING, RUN THE FIRST CONVERGED ARM

*Updated 20 August 2026, session close. One day, six landings, all stacked
and unmerged: **freight physical** (§9.49, PR #46) · **the §8.5
constrain-and-report decision, logged before results** (§9.50, PR #47; its
base arm owner-stopped at ~iteration 20) · **four owner directives + the
research dossiers + the measured ×42 gap decomposition** (§9.51, PR #51) ·
**motorbike physical** (§9.52, PR #52) · **paired ride physically boarded,
walk and bike physically simulated, and the unpairable ride trip re-moded to
walk — ride becomes emergent** (§9.53–§9.55, PR #53). This is a HANDOVER,
not a source of truth: where it disagrees with [`STATUS.md`](../STATUS.md),
[`DECISIONS.md`](../DECISIONS.md) or
[`.claude/CLAUDE.md`](../../../../.claude/CLAUDE.md), those win.*

---

═══════════════════════════════════════════════════════════════════════════════
§0  DO THIS FIRST
═══════════════════════════════════════════════════════════════════════════════

**Run `/onboard`**; at session end, `/handoff`. The checks:

```bash
python src/setup/bootstrap_toolchain.py --verify   # ~1 min, COMPILES 12 Java sources
python tests/check_manifest.py                     # committed subset intact
python src/registry/check_hardcoding.py --strict   # must exit 0
```

**⚠ OWNER DIRECTIVES, standing:**

1. **NO MULTI-HOUR RUNS WITHOUT EXPLICIT APPROVAL — none is standing.** The
   §9.48 approval was spent; the §9.50 base-arm launch was consumed and the
   owner then STOPPED that run. State the cost, get a yes, every time.
2. **DO ONE THING RIGHT rather than bloating the repo.**
3. **The four §9.51 directives** (physical ride — enacted §9.53/§9.55;
   9+ modes distinct — motorbike enacted §9.52, pt-split/taxi open on #49;
   the sub-1 km walk deficit — decomposed, mechanism open on #30;
   demographic fidelity — inventoried, open on #50).

**The stack landed on `main` via PR #56** (the six stacked PRs #46–#55 had
been merged into their base branches, so #56 carried the union to `main`).
Start from `main`; delete the merged work branches. **No run is in
progress.**

---

═══════════════════════════════════════════════════════════════════════════════
§1  THE GOAL — and where it now stands
═══════════════════════════════════════════════════════════════════════════════

> **A digital twin of any city, traffic-wise ... whether that scaling
> actually predicts the correct ridership per mode must be CHECKED, not
> assumed. Every form of transport should be IN ACTION physically.**

**The "in action physically" half is DONE** (§2). The "checked" half now has
its biggest test unrun: the model changed shape five times today with **no
completed run between them — one family boundary** (nothing after §9.49
compares to `bind1000_25pct`), and the first converged arm of the
all-physical model re-baselines everything at once. The standing risk is
unchanged: 9 of 10 rail forecasts overestimate; §9.48's occupancy excess
(0.4855 vs 0.3503) was the first measured flattering-direction error, and
§9.50 rules it REPORTED, never absorbed.

---

═══════════════════════════════════════════════════════════════════════════════
§2  THE MODES — all physical, measured
═══════════════════════════════════════════════════════════════════════════════

| mode | mechanism | probe evidence (1%) |
|---|---|---|
| Car | qsim; explicit type = MATSim default, bytecode-proven (§9.49) | — |
| Truck | PCE 2.0 swept, 100 km/h cap (§9.49) | 913 trips, 140,380 traversals |
| Motorbike | PCE 0.4 swept, locked carve on the measured G62 anchor 0.363% (§9.52) | 52 trips, 0 stuck |
| **Walk** | **PCE 0.0 capped 1.25 m/s — the sidewalk in queue arithmetic (§9.54)** | 9,050 trips, conserving |
| **Bike** | **PCE 0.2 swept, 4.2 m/s (§9.54)** | 2,311 trips |
| Bus/rail/tram/ferry | 2,139 transit vehicles | pre-existing |
| **Ride** | **paired → physically boarded (`JointRideEngine`, §9.53); unpaired → re-moded to physical walk (§9.55): EMERGENT share, no invented parameter** | final probe iteration: ride = 67 trips, ALL boarded; 2,758 re-moded at it.0 |

Still teleported, both declared and neither a mode: the PT access/egress
stub (`non_network_walk` — speed, detour 1.6902 measured, and scoring all
DECLARED, §9.54) and the counted boarding-miss fallback (5–6/iteration — the
×6.91 window layer; ending it is a joint-departure-time replanning question,
on #48). **Taxi/rideshare is not in the mode vocabulary**: the tier plan is
on #49; task 4.4's owner sequencing stands.

**The consequence the owner accepted with "no exceptions"**: equilibrium
ride is bounded by household pairability (OD-coincidence 15.31%) and will
sit far below the observed 20.60% — the gap IS the unobserved
non-household-lift share and is REPORTED (dossier §4, option i). Where the
displaced ~10 pp settles is the first converged run's headline.

---

═══════════════════════════════════════════════════════════════════════════════
§3  THE ACTIVE LANE — in order
═══════════════════════════════════════════════════════════════════════════════

1. **Merge the stack** (#46 → #53 + handover).
2. **Fix #54 first — it gates everything**: the summariser's per-mode stuck
   attribution over-assigns end-of-day aborts (events conserve EXACTLY —
   measured on both probes; the attribution does not), so `accounting
   closes` would false-negative a healthy converged run. Fix: attribute
   stuck per mode from the events stream; assert departures = arrivals +
   stuck per mode on the probes.
3. **Bring the owner the 4.5.0 sequencing ruling + the run request**: the
   first converged arm of the all-physical model — S2 × WEEKDAY, 25% × 1000,
   ~35 h wall (the §9.48-family measured 105.9 s/iteration; this model adds
   walk/bike/motorbike vehicles and the boarding engine — expect slower,
   unmeasured). Its close-out delivers in one pass: the emergent ride share,
   walk's re-baseline (#30 decomposition already isolates generation),
   `params/C5_calibration.json` via `calibrate.py --constrained-base` + the
   §9.50 report (closing #14, #9), and the #48/#31 realised-boarding
   numbers at convergence.
4. Then by the recorded order: #30's generation mechanism, #49's remaining
   tiers (pt reporting split is cheap and break-free), #50's modelled
   table + the mode × age acquisition.

---

═══════════════════════════════════════════════════════════════════════════════
§4  WHAT IS DONE — do not redo any of it
═══════════════════════════════════════════════════════════════════════════════

- **§9.49 freight** — through-gate split by observed station heavy shares;
  internal tier on the observed freight-industry attractor; hourly profile
  and weekend factors MEASURED from 33,816 classified station-days
  (`extract_freight_profile.py`).
- **§9.50 the calibration decision** — constrain-and-report, logged BEFORE
  results; era-3 estimation recorded infeasible; ASCs stay priors; #9
  resolved by decision; the loop's movable set corrected (2 parameters, ~21
  × 35 h — search declined with cost stated); `--constrained-base` built and
  tested. **C5/report NOT yet produced — needs a completed arm.**
- **§9.51 the four directives**, with research WRITTEN:
  [`design/physical-ride.md`](../design/physical-ride.md) and
  [`design/mode-individualisation.md`](../design/mode-individualisation.md);
  the ×42 realisation-gap decomposition MEASURED
  (`measure_realisation_gap.py`, `realisation_gap_bind1000_25pct.json`):
  ×2.24 mode co-assignment (incl. 14,141 escortees driving themselves) ×
  6.91 realised window × 2.73 link resolution.
- **§9.52 motorbike** — person-level locked carve from car, hash-drawn (no
  rng perturbation), escort days excepted; `fit.py` compares car+motorbike
  against the Vehicle-driver target that contains motorcyclists.
- **§9.53 physical boarding** — bookings at BeforeMobsim, boarding when the
  driver's car is still parked at the shared origin, real
  Enters/LeavesVehicle events; misses fall back to Tier 1 VERBATIM, counted.
- **§9.54 walk/bike physical** — one declared speed per mode consumed by
  both router (`CappedSpeedTravelTime`) and mobsim; road-rule exclusions +
  per-mode largest-SCC cleaning (walk stripped from 16,726 unreachable
  links, bike 5,177); four teleported fields retired; the transit router's
  9,466 generic walk stubs carried by `TolerantAgentSource` +
  `GenericRouteTeleporter`; the silently-defaulted `non_network_walk`
  scoring now declared.
- **§9.55 emergent ride** — unpaired ride re-modes to network walk at
  BeforeMobsim, route cleared for re-routing as walk.
- Earlier, same family of dones: §9.43–§9.48 (iterations=1000, pairing,
  household sampling, escort binding, age structure, the re-measure arm).

**Phases:** P0–P3 ✅ · P4 🟡 (deliverables 0 and 5 open) · P5–P7 ⬜.

---

═══════════════════════════════════════════════════════════════════════════════
§5  WHAT INVALIDATES YOUR WORK
═══════════════════════════════════════════════════════════════════════════════

- **No multi-hour run without owner approval. None standing.**
- **One family boundary today**: nothing after §9.49 compares to
  `bind1000_25pct` or anything older. NEVER compare across families or
  sample fractions; `target_lga_pct`, never `all_residents_pct`.
- **THE 67/143 SPLIT IS PRE-REGISTERED** — `fit.py` enforces; need a
  holdout? SAY SO AND STOP.
- **One build of the network per comparison** (§3.5); threads=10 is run
  identity.
- **No invented data**: G62 anchors commute for motorbike/taxi; non-commute
  shares are swept; thin demographic cells are unvalidatable, never filled.
- **A run without `_run.json` is not a result.** `controler_sha256()` still
  hashes only `src/java/` — fix when any toolchain change lands.
- **#54 before the next arm** — the accounting gate itself is currently
  mis-attributing.

---

═══════════════════════════════════════════════════════════════════════════════
§6  EXACT STATE — 20 August 2026, session close
═══════════════════════════════════════════════════════════════════════════════

| | |
|---|---|
| PRs | Stack **#46 ← #47 ← #51 ← #52 ← #53 ← handover**, merge in order, then `main` |
| Toolchain | 3 pinned, unchanged. **Java: 12 sources** (+`JointRideEngine`, `TolerantAgentSource`, `GenericRouteTeleporter`, `CappedSpeedTravelTime`) |
| Registry | **327 fields**; ledger **0** `--strict` |
| Package | **423 files**; `check_package.py` ALL PASSED (incl. the new freight-tier and §-existence assertions); city-agnostic **13/13** |
| Machine | free; no run in progress |
| Run cost | §9.48 family measured 105.9 s/iter at 25% (~35 h/arm); the all-physical model is SLOWER and unmeasured — state that when asking approval |
| Runs | `bind1000_25pct` — the only valid full run, LAST of its family (§9.48). Probes: `ride_pairing_probe`, `freight_smoke`, `motorbike_smoke`, `jointride_probe`, `allmodes_probe` — not results. `_aborted_20260820/` holds the owner-stopped `base1000_25pct` + the old S2 dead run |
| Open issues | **9**: #48 #49 #50 #30 (directive lanes, build halves done) · **#54 NEW** (summariser stuck attribution — fix first) · #14 #9 (await C5) · #28 #31 (ride ledgers) · #24 closes with #46 |
| **Results** | **No findings. Nothing is a finding about the light rail.** §9.48's fit rows are diagnostics of a superseded family; the all-physical model has run only 2-iteration probes |

---

═══════════════════════════════════════════════════════════════════════════════
§7  DECISIONS TAKEN — do not re-litigate
═══════════════════════════════════════════════════════════════════════════════
• §8.5 branch = CONSTRAIN-AND-REPORT (§9.50); ASCs stay priors; #9 by
  decision; the parameter search declined with its cost stated.
• RIDE IS EMERGENT (§9.55): unpaired ride walks; the non-household-lift gap
  is REPORTED, not parameterised. Tier-1 teleport survives ONLY as the
  counted boarding-miss fallback.
• Motorbike is a LOCKED CARVE (no choice competition — no preference data);
  fit compares car+motorbike. Walk rides the road graph as footpath proxy
  (the footway network is data; §3.5 forbids a remap) — road-rule exclusions
  + SCC cleaning declared.
• The four teleported walk/bike fields are RETIRED; the measured 1.6902
  detour lives on as the access-stub factor; `non_network_walk` scoring is
  declared, not defaulted.
• Freight is a background load, swept never pinned; truck routing
  unconstrained is a stated limitation. `bind1000_25pct` is the last run of
  its family. ONE ARM AT A TIME. SCATS refused; journey-linked Opal swept
  3–15 min; charging dwell swept — never pinned.

---

═══════════════════════════════════════════════════════════════════════════════
§8  TRAPS — new ones first, each paid for today
═══════════════════════════════════════════════════════════════════════════════
1. **qsim component bindings COLLECT, they do not override** — binding a
   second agent source under the stock name ran BOTH (vehicles parked
   twice). Remove the named component and add yours under a new name.
2. **Car vehicles carry the BARE person id; every other mode suffixes**
   (`123` vs `123_truck`) — the first boarding probe missed 100% on the
   guessed `_car` form. Measured from events, kept as a counted-miss
   fallback.
3. **`modeVehicleTypesFromVehiclesData` demands a type for EVERY
   routing.networkMode** (ride included), not only main modes.
4. **The transit router emits mode-`walk` legs with GENERIC routes**
   (access/egress/direct-walk; 9,466 per 1% day) and the stock agent source
   casts every main-mode leg's route to NetworkRoute — walk-as-main-mode
   dies at agent insertion without `TolerantAgentSource` +
   `GenericRouteTeleporter`.
5. **MATSim's BUILT-IN teleported defaults conflict with network walk/bike**
   (`clearDefaultTeleportedModeParams`), and clearing them also clears
   `non_network_walk` — declare the helper explicitly or PT breaks.
6. **A mode subnetwork with unreachable links is REFUSED** — road-rule
   exclusions sever pockets; strip the mode outside its largest SCC at build
   (done in `build_matsim_run_inputs.py`), report the counts.
7. **`PersonPrepareForSim` refuses a route inconsistent with link modes** —
   when re-moding a leg, CLEAR its route so it re-routes on the new mode's
   network.
8. HEREDOCS mangle (Write the file, run it). `compileall` catches neither a
   NameError nor a schema TypeError — import and CALL. After registry edits:
   `render_docs` + `render_schema`; after data changes: `normalise_eol` →
   `build_manifest` → `normalise_eol`. `check_package` asserts every
   `decisions_ref` section EXISTS — write the DECISIONS entry before citing
   it.
9. `pkill` fails; PowerShell `Stop-Process` then VERIFY. The live log is
   `<run>/matsim.log`. `Unsupported class file major version 69` is benign.
   Branch `<git-handle>/<kebab>`, no attribution, STATUS in the same commit.

---

═══════════════════════════════════════════════════════════════════════════════
§9  STATE OF THE PROJECT — THE SIX QUESTIONS (20 August 2026, close)
═══════════════════════════════════════════════════════════════════════════════

### 1. Goals & achievement
Research goal (proposal §1/§3): hypotheses A1–A6, B1–B4 (B3 decisive) —
**none tested**. Operational goal: the per-mode-checked physical twin —
**the physical half is COMPLETE** (§2); the checked half awaits the first
all-physical converged arm. Proposal §8 deliverables: model 🟡 · data 🟡 ·
calibration report 🟡 (decision §9.50 done, C5 pending a run) · paper ⬜ ·
explorer 🟡 · method note 🟡.

### 2. Phases — 4 of 8
P0 ✅ · P1 ✅ · P2 ✅ · P3 ✅ (regenerated 20 Aug, freight + motorbike
demand) · **P4 🟡 (deliverables 0 and 5 open)** · P5–P7 ⬜.
Home: [`STATUS.md`](../STATUS.md).

### 3. Tasks
4.1: 9/9 ✅. 4.2: 6/8 done-and-evaluated; **4.2.4 decided-not-delivered**
(§9.50 — C5 awaits the arm); 4.3 open; 4.4 folded into #49. **Batch 4.5
(directives): build halves DONE (§9.52–§9.55); measurement halves await the
converged arm; 4.5.0 sequencing is the owner's.** P5 0/5 · P6 0/5 · P7 0/4
(5.2 DELETE and 5.3/6.1/6.2 REWORK proposals still pending the owner).

### 4. Simulator vs real life
Latest valid full run = `bind1000_25pct` (§9.48, pre-calibration, SUPERSEDED
family): car 63.95/59.0 · ride 31.05/20.6 · walk 0.71/13.4 · pt 0.36/3.8 ·
occupancy 0.4855/0.3503 (flattering) · counts unusable (#20 unwired). The
all-physical model has NO fit numbers yet — 2-iteration probes only; its
first arm re-baselines every row, with ride EXPECTED far below 20.6 by
design (§9.55 — the reported non-household-lift gap).

### 5. Issue ledger — 37 filed (numbers shared with PRs), 27 closed, 9 open, #24 closing
#48/#49/#50/#30: directive lanes, build done, measurement open · #54: fix
first · #14/#9: await C5 · #28/#31: ride ledgers. Every closed issue carries
its REOPEN IF.

### 6. PR history, and the next PR
#1 P1 data · #2 P2 networks · #3 P3 demand · #4 run inputs loadable · #38
spec audit + rebuild · #40 ride pairing · #41 board · #42 handover · #43
escort binding + age structure · #44 §9.48 evaluation · #45 /handoff +
/onboard · **open stack: #46 freight · #47 calibration decision · #51
directives + dossiers · #52 motorbike · #53 all-physical (boarding, walk,
bike, emergent ride) · the handover PR**. **Next substantive PR:
`P4 (#54): stuck attribution from the events`, then the converged-arm
close-out (`P4 (4.2.4/#14)`) once the owner approves the run.**

---

### Bootstrap reading, in this order

```
cities/newcastle/docs/STATUS.md                the board; batch 4.5 is the lane
cities/newcastle/docs/DECISIONS.md §9.49–§9.55 today's six sections, all cross-linked
issues #54 #48 #49 #50 #30                     what is open, with the measured numbers
cities/newcastle/docs/design/physical-ride.md  + mode-individualisation.md — the dossiers
.claude/CLAUDE.md                              conventions + hard constraints
```
