# Brief for the next agent — THE ARM IS STOPPED MID-FLIGHT; GET THE RELAUNCH DECISION (AND DECIDE #60 FIRST)

*Updated 21 August 2026, session close. The session: the #54 accounting fix
(PR #58, merged) · the 50-iteration all-physical shakedown `phys50_25pct`
(nothing broken) · the §9.56 events-pipeline threads (PR #59, merged, ~21%
off the wall) · the §9.57 arm attempt — horizon decided at the FULL 1000,
launched with approval, 135 healthy iterations, **stopped at owner
instruction during iteration 136**, quarantined · the #60 walk turn-refusal
defect measured and filed · every issue and PR retitled to `P<phase>:
<summary>`. This is a HANDOVER, not a source of truth: where it disagrees
with [`STATUS.md`](../STATUS.md), [`DECISIONS.md`](../DECISIONS.md) or
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
   phys1000 approval was granted 21 Aug, consumed by the launch, and the
   owner then STOPPED that run at iteration 136 and said "await further
   instructions". State the cost (**~65 h/arm measured, §9.57**), get a
   fresh yes, every time.
2. **DO ONE THING RIGHT rather than bloating the repo.**
3. **The four §9.51 directives** (physical ride — enacted §9.53/§9.55;
   9+ modes distinct — motorbike enacted §9.52, pt-split/taxi open on #49;
   sub-1 km walk — decomposed twice, mechanism open on #30; demographic
   fidelity — inventoried, open on #50).
4. **All GitHub titles**: `P<phase>: <plain summary>`, refs in parens at the
   end. No "Owner directive:" / "Audit:" / "handover:" / "Tooling:" slop
   (owner, 21 Aug; in `.claude/CLAUDE.md`).
5. **Any table comparing numbers lists EVERY mode individually** — never a
   "public transport" umbrella row; when only the pt aggregate is held, say
   so per row (owner, 20 Aug /goal directive).

**Start from `main`. No run is in progress; the machine is free.**

---

═══════════════════════════════════════════════════════════════════════════════
§1  THE GOAL — and where it now stands
═══════════════════════════════════════════════════════════════════════════════

> **A digital twin of any city, traffic-wise ... whether that scaling
> actually predicts the correct ridership per mode must be CHECKED, not
> assumed. Every form of transport should be IN ACTION physically.**

**"In action physically" is DONE** (§2) and now SHAKEN DOWN at the campaign
fraction: `phys50_25pct` (50 × 25%) ran rc=0 with per-mode conservation
closing on every mode under the repaired #54 gate. **"Checked" is still
unrun**: the first converged arm got 135 of 1000 iterations (car 46.3%,
walk 32.8% and still moving fast — §9.57) before the owner stopped it.
Nothing after §9.49 has a completed run; one family boundary; the standing
risk is unchanged (9 of 10 rail forecasts overestimate; §9.50 rules every
flattering error REPORTED, never absorbed).

---

═══════════════════════════════════════════════════════════════════════════════
§2  THE MODES — all physical, now measured at 25%
═══════════════════════════════════════════════════════════════════════════════

| mode | mechanism | shakedown evidence (`phys50_25pct`, 25% × 50) |
|---|---|---|
| Car | qsim; explicit type = MATSim default, bytecode-proven (§9.49) | 189,809 dep = 188,873 arr + 936 stuck ✅ |
| Truck | PCE 2.0 swept, 100 km/h cap (§9.49) | 22,648 = 22,581 + 67 ✅ |
| Motorbike | PCE 0.4, locked carve on the measured G62 anchor 0.363% (§9.52) | 1,263 = 1,254 + 9 ✅ |
| Walk | PCE 0.0 capped 1.25 m/s (§9.54) | 299,699 = 283,204 + 16,495 ✅ — but see **#60** |
| Bike | PCE 0.2 swept, 4.2 m/s (§9.54) | 58,427 = 57,375 + 1,052 ✅ |
| Bus/rail/tram/ferry | 1,448/332/252/107 transit vehicles; leg mode is the `pt` aggregate — the reporting split is #49 Tier R | 58,965 = 52,332 + 6,633 ✅ |
| Ride | paired → physically boarded (§9.53); unpaired → re-moded to walk (§9.55): EMERGENT share | 1,712 = 1,703 + 9 ✅; re-mode measured live at 5,533–5,792 legs/iteration; share 0.26–0.31% vs observed 20.60 — the REPORTED non-household-lift gap |

Still teleported, declared, neither a mode: PT access/egress stubs (§9.54)
and the counted boarding-miss fallback. Taxi/rideshare: not a mode (#49,
task 4.4).

---

═══════════════════════════════════════════════════════════════════════════════
§3  THE ACTIVE LANE — in order
═══════════════════════════════════════════════════════════════════════════════

1. **Bring the owner two linked decisions** (the run was stopped explicitly
   to "await further instructions"):
   - **#60 first, recommended**: verify the walk turn-refusal mechanism
     (hours — do refused link pairs carry `disallowedNextLinks` for the
     approach link?), then exempt walk from motor-vehicle turn restrictions
     at network build (declared, per-mode). It is a measured bias in the
     flattering-to-car direction AND a per-timestep cost; fixing it changes
     the model, but the family has NO completed run yet, so fixing before
     the relaunch is free family-wise. Skipping it is also coherent — then
     it is a stated limitation of the arm.
   - **The relaunch**: S2 × WEEKDAY, 25% × 1000, `phys1000_25pct` overlay —
     **~65 h wall measured** (median 234 s/iteration over 135 iterations,
     §9.57), plus possible it-110-style outliers. The horizon question is
     SETTLED: full 1000, ~500 rejected on both arms' trajectories (§9.57).
2. **The arm's close-out delivers in one pass**: the emergent ride share,
   walk's re-baseline (#30), `params/C5_calibration.json` via
   `calibrate.py --constrained-base` + the §9.50 report (closing #14, #9),
   and the #48/#31 realised-boarding numbers at convergence.
3. Then by the recorded order: #30's generation mechanism, #49's remaining
   tiers (pt reporting split is cheap and break-free), #50's modelled
   table + the mode × age acquisition.

---

═══════════════════════════════════════════════════════════════════════════════
§4  WHAT IS DONE — do not redo any of it
═══════════════════════════════════════════════════════════════════════════════

- **§9.49–§9.55** (20 Aug): freight physical · §9.50 constrain-and-report ·
  §9.51 directives + dossiers + the ×42 gap decomposition · motorbike ·
  physical boarding · walk/bike physical · emergent ride. Landed via PR #56.
- **#54 / PR #58** (21 Aug): run accounting reads the final iteration's own
  events stream; each stuck event attributed to the person's open leg;
  duplicate engine aborts counted separately (`duplicate_aborts`);
  telemetry-vs-events disagreement reported. Verified: conservation closes
  on all modes of `allmodes_probe`, `jointride_probe`, `rp25_stress` and
  `bind1000_25pct`.
- **§9.56 / PR #59** (21 Aug): `RUN.machine.event_handler_threads` = 4
  (`eventsManager.numberOfThreads`) — the framework-default SINGLE events
  thread was measured saturated (172–177 s CPU per ~261 s iteration under
  the all-physical event volume); the knob buys ~21% wall, verified
  bit-identical on model outputs; costs events-file byte-order stability
  (recorded). Write intervals 100 in the arm overlay. G2 test extended to
  the third `numberOfThreads` owner. Registry verified **327** fields.
- **§9.57** (21 Aug): the horizon decision (full 1000), the arm attempt
  (135 healthy iterations, median 234 s), the walk-leg decomposition (66%
  whole-trip at mean ~11 km / 34% PT stubs / zero car access-egress), the
  it-110 outlier (7,867 s walk knot, self-recovered, §9.36's family), the
  #60 measurement, the stop and quarantine.
- **Titles**: all 9 open issues and all 22 PRs conform to the scheme.

**Phases:** P0–P3 ✅ · P4 🟡 (deliverables 0 and 5 open) · P5–P7 ⬜.

---

═══════════════════════════════════════════════════════════════════════════════
§5  WHAT INVALIDATES YOUR WORK
═══════════════════════════════════════════════════════════════════════════════

- **No multi-hour run without owner approval. None standing; the last one
  was spent and the run then stopped by the owner.**
- **One family boundary at §9.49**: nothing after it compares to
  `bind1000_25pct` or older. NEVER compare across families or fractions;
  `target_lga_pct`, never `all_residents_pct`. A #60 fix starts ANOTHER
  family — fine only while the family has no completed run.
- **THE 67/143 SPLIT IS PRE-REGISTERED** — `fit.py` enforces; need a
  holdout? SAY SO AND STOP.
- **One build of the network per comparison** (§3.5); threads=10 is run
  identity (`RUN.machine.event_handler_threads` is NOT — §9.56, verified).
- **No invented data**: the emergent-ride gap stays REPORTED (§9.55); thin
  demographic cells stay unvalidatable; #60's mechanism is a SUSPICION
  until verified.
- **A run without `_run.json` is not a result** — that includes
  `_aborted_20260821/phys1000_25pct`; its 135 iterations are diagnostics.

---

═══════════════════════════════════════════════════════════════════════════════
§6  EXACT STATE — 21 August 2026, session close
═══════════════════════════════════════════════════════════════════════════════

| | |
|---|---|
| PRs | **None open.** #58, #59 merged; branch cleanup done |
| Toolchain | 3 pinned, unchanged; 12 Java sources compile |
| Registry | **327 fields, verified against the generated contract** (§9.56 corrected the board's off-by-one); ledger **0** `--strict` |
| Package | 423 files; `check_manifest` OK; full `check_package` not re-run this session (no data artefact changed) |
| Machine | **free**; no run in progress |
| Run cost | **All-physical at 25%: median 234 s/iteration measured over 135 iterations → ~65 h/arm** (§9.57); events threads already included; one 7,867 s outlier observed |
| Runs | `bind1000_25pct` — last completed run, SUPERSEDED family (§9.48). `phys50_25pct` — the all-physical shakedown, rc=0, accounted, NOT a result. Probes: `allmodes_probe`, `jointride_probe`, `evthreads_ab`/`ab2`/`timing`, `rp25_stress`, `freight_smoke`, `motorbike_smoke`, `ride_pairing_probe`. **`_aborted_20260821/phys1000_25pct` — the stopped first arm, 135 iterations of diagnostics** |
| Open issues | **9**: #60 NEW (walk turn refusals — decide before relaunch) · #48 #49 #50 #30 (directive lanes, build done, measurement awaits the arm) · #14 #9 (await C5) · #28 #31 (ride ledgers) |
| **Results** | **No findings. Nothing is a finding about the light rail.** The stopped arm is diagnostics; `phys50_25pct` is a shakedown; §9.48's fit rows belong to a superseded family |

---

═══════════════════════════════════════════════════════════════════════════════
§7  DECISIONS TAKEN — do not re-litigate
═══════════════════════════════════════════════════════════════════════════════
• **Iteration horizon = 1000** (§9.43, re-affirmed §9.57 against ~500 on two
  arms' trajectories). • §8.5 = CONSTRAIN-AND-REPORT (§9.50); ASCs stay
  priors. • RIDE IS EMERGENT (§9.55); the non-household-lift gap is
  REPORTED. • Motorbike is a locked carve; walk rides the road graph.
• Events accounting is the gate; telemetry is the fallback instrument
  (#54). • `event_handler_threads` = 4 is wall-time only, verified; its
  byte-order cost is recorded (§9.56). • Freight swept never pinned; SCATS
  refused; Opal swept 3–15 min; dwell swept. ONE ARM AT A TIME.

---

═══════════════════════════════════════════════════════════════════════════════
§8  TRAPS — new ones first, each paid for
═══════════════════════════════════════════════════════════════════════════════
1. **"Fix #NN" anywhere in a PR body is a GitHub closing keyword** — it
   auto-closed #54 unfixed when the stack merged (cost: a false "done" on
   the gate defect). Write "the #NN fix" unless closure is intended.
2. **The G2 test asserts the `numberOfThreads` MULTISET** — a new
   `*.numberOfThreads` binding must add its field to the fixture's PERTURB
   or CI fails (cost: PR #59's first red X).
3. **A `tail -f` monitor holds a Windows lock on the run directory** — stop
   monitors (and their orphaned tail/grep children) before quarantining a
   run (cost: two failed `mv`s).
4. **1% timing says NOTHING about 25% events saturation** — the events knob
   is SLOWER at 1% and ~21% faster at 25% (§9.56); and the 5-iteration
   probe under-predicts the arm (181–201 s probe vs 234 s median measured).
5. **MATSim's default events manager is ONE thread** — on any model that
   multiplies event volume, check `ProcessEventsRunnable` CPU in the log
   before buying hardware or blaming the qsim.
6. qsim component bindings COLLECT (remove the stock name); car vehicles
   carry the BARE person id; `modeVehicleTypesFromVehiclesData` demands a
   type for EVERY routing.networkMode; the transit router's generic walk
   stubs need `TolerantAgentSource` + `GenericRouteTeleporter`;
   `clearDefaultTeleportedModeParams` also clears `non_network_walk`;
   unreachable mode subnetworks are REFUSED (SCC-clean at build); CLEAR a
   re-moded leg's route. HEREDOCS mangle; import and CALL after edits;
   `render_docs`/`render_schema` after registry edits. `pkill` fails —
   PowerShell `Stop-Process` then VERIFY. `Unsupported class file major
   version 69` is benign. Branch `<git-handle>/<kebab>`, no attribution,
   STATUS in the same commit.

---

═══════════════════════════════════════════════════════════════════════════════
§9  STATE OF THE PROJECT — THE SIX QUESTIONS (21 August 2026, close)
═══════════════════════════════════════════════════════════════════════════════

### 1. Goals & achievement
Research goal (proposal §1/§3): hypotheses A1–A6, B1–B4 — **none tested**.
Operational goal: physical half **COMPLETE and shaken down at 25%** (§2);
checked half awaits the relaunched converged arm (stopped at 13.6%).
Proposal §8 deliverables: model 🟡 · data 🟡 · calibration report 🟡 (§9.50
decision done, C5 pending a run) · paper ⬜ · explorer 🟡 · method note 🟡.

### 2. Phases — 4 of 8
P0 ✅ · P1 ✅ · P2 ✅ · P3 ✅ · **P4 🟡 (deliverables 0 and 5 open)** ·
P5–P7 ⬜. Home: [`STATUS.md`](../STATUS.md) phase table.

### 3. Tasks
4.1: 9/9 ✅. 4.2: six of eight done-and-evaluated; 4.2.4 decided-not-
delivered (C5 awaits the arm). 4.3, 4.4 open (4.4 folded into #49).
**Batch 4.5: build halves DONE; measurement halves await the arm; 4.5.0 was
resolved by the launch and re-opened by the stop — the relaunch decision is
the owner's, with #60 recommended first.** P5 0/5 · P6 0/5 · P7 0/4 (the
four deletion/rework proposals for 5.2/5.3/6.1/6.2 still await the owner).

### 4. Simulator vs real life
Latest COMPLETED run = `bind1000_25pct` (superseded family, pre-calibration
diagnostics): car 63.95/59.0 · ride 31.05/20.6 · walk 0.71/13.4 · pt-aggregate
0.36/3.8 · bike 4.0/3.2 · occupancy 0.4855/0.3503 (flattering; REPORTED). The
all-physical model has NO completed fit: the stopped arm's iteration-133
diagnostics (car 46.32 · walk 32.77 · bike 9.92 · pt 6.62 · ride 0.26 ·
truck 3.89 · motorbike 0.22) are a mid-search snapshot, still moving ~+3.3
pp car per 25 iterations, and predict nothing.

### 5. Issue ledger — 38 filed (numbers shared with PRs), 29 closed, 9 open
#60: decide-before-relaunch (measured, mechanism unverified) · #48/#49/#50/
#30: directive lanes, measurement open (fresh diagnostics commented 21 Aug)
· #14/#9: await C5 · #28/#31: ride ledgers. Every closed issue carries its
REOPEN IF.

### 6. PR history, and the next PR
22 PRs, all merged, all retitled to the scheme: #1–#3 P1–P3 foundations ·
#4 run-input fix · #38 audit+rebuild · #40 ride pairing · #41–#42 board/
brief · #43 escort+age · #44 first repaired-demand run · #45 skills · #46
freight · #47 calibration decision · #51 workstreams · #52 motorbike · #53
all-physical modes · #55–#57 close-out/landing/convention · #58 #54-fix ·
#59 events threads + arm launch. **Next PR: whatever the owner's #60/relaunch
ruling produces — either `P4: Exempt walk from motor-vehicle turn
restrictions (#60)` or the arm's close-out (`P4: First converged all-physical
run — C5 and the re-baselines (#14)`).**

---

### Bootstrap reading, in this order

```
cities/newcastle/docs/STATUS.md                 the board; §3 above is the lane
cities/newcastle/docs/DECISIONS.md §9.56–§9.57  this session, cross-linked
issues #60 #48 #30                              what the arm measured, what it awaits
.claude/CLAUDE.md                               conventions + hard constraints (title scheme updated 21 Aug)
```
