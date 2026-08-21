# Brief for the next agent — THE §9.58–§9.61 FAMILY IS BUILT AND VERIFIED; GET THE RELAUNCH DECISION

*Updated 21 August 2026, second session of the day (the owner's `/goal`
session: fix the non-household-lift gap · replace assumptions with data ·
city-agnostic · ≥10× iterations without teleportation · every runless
issue). The session: **§9.58** #60 verified to be a different defect and
repaired four ways (refusals 3.8k/iteration → 0) · **§9.59** every
wall-time knob declared and probed, the 10× ask answered by measurement ·
**§9.60** the non-household-lift mechanism (M0 waiting + M1 re-targeted
escort tours, 55,280 weekday bindings) · **§9.61** three assumptions became
measurements from held data · #49 Tier R (pt split) done · #62/#63 filed.
This is a HANDOVER, not a source of truth: where it disagrees with
[`STATUS.md`](../STATUS.md), [`DECISIONS.md`](../DECISIONS.md) or
[`.claude/CLAUDE.md`](../../../../.claude/CLAUDE.md), those win.*

---

═══════════════════════════════════════════════════════════════════════════════
§0  DO THIS FIRST
═══════════════════════════════════════════════════════════════════════════════

**Run `/onboard`**; at session end, `/handoff`. The checks:

```bash
python src/setup/bootstrap_toolchain.py --verify   # ~1 min, COMPILES 14 Java sources
python tests/check_manifest.py                     # committed subset intact
python src/registry/check_hardcoding.py --strict   # must exit 0
```

**⚠ OWNER DIRECTIVES, standing:**

1. **NO MULTI-HOUR RUNS WITHOUT EXPLICIT APPROVAL — none is standing.**
   The 21 Aug phys1000 approval was consumed and that run then stopped by
   the owner. State the cost (**~233 s/iteration measured on the new
   family → ~65 h/arm**, or TWO CONCURRENT ARMS at qsim 8 + events 4,
   §9.59), get a fresh yes, every time.
2. **DO ONE THING RIGHT rather than bloating the repo.**
3. **The four §9.51 directives** (physical ride — enacted §9.53/§9.55,
   extended §9.60; modes distinct — motorbike §9.52, pt reporting split
   DONE, choice-split/taxi open on #49; sub-1 km walk — #30 awaits
   re-measurement on the new family; demographic fidelity — #50 awaits
   the arm).
4. **The `/goal` directives of 21 Aug** (this session's charter): the
   non-household-lift gap is now MECHANISED, not merely reported (§9.60);
   assumptions are replaced by data where held data allows (§9.61, backlog
   #63); city-agnosticism is audited (#62 carries what the gates cannot
   see); the 10× ask is answered by measurement (§9.59).
5. **All GitHub titles**: `P<phase>: <plain summary>`, refs in parens at
   the end. **Every mode individually in every numbers table** — never a
   "public transport" umbrella row (Tier R makes this mechanical).
6. **Never commit directly to `main`; the session's ONE PR opens at
   `/handoff`**, is watched to merge, and the branch deleted both sides.

**Start from `main`. No run is in progress; the machine is free.**

---

═══════════════════════════════════════════════════════════════════════════════
§1  THE GOAL — and where it now stands
═══════════════════════════════════════════════════════════════════════════════

> **A digital twin of any city, traffic-wise ... whether that scaling
> actually predicts the correct ridership per mode must be CHECKED, not
> assumed. Every form of transport should be IN ACTION physically.**

**"In action physically" is DONE and now includes non-household lifts**
(§2). **"Checked" is still unrun**: no completed run exists in the current
(§9.58–§9.61) family. The standing risk is unchanged (9 of 10 rail
forecasts overestimate; §9.50 rules every flattering error REPORTED,
never absorbed).

---

═══════════════════════════════════════════════════════════════════════════════
§2  THE MODES — all physical, the wedge repaired, lifts mechanised
═══════════════════════════════════════════════════════════════════════════════

| mode | mechanism | state |
|---|---|---|
| Car | qsim; PassingQ link dynamics (§9.59 — FIFO let walkers block cars, contradicting §9.54's declared PCE-0 semantics) | verified at probes |
| Truck | PCE 2.0 swept, 100 km/h cap (§9.49) | unchanged |
| Motorbike | PCE 0.4, locked carve on the measured G62 anchor (§9.52) | unchanged |
| Walk | PCE 0.0 capped 1.25 m/s; **trunk now walkable (the exclusion over-read the law), one-way streets carry reverse complements, every activity pinned to a walk-reachable link (§9.58)** | refusals 3.8k/it → **0**, probe-verified twice |
| Bike | PCE 0.2 swept, 4.2 m/s; same §9.58 coverage repairs | ✅ |
| Bus/rail/tram/ferry | 2,139 transit vehicles; **reporting split by scheduled submode is DONE (#49 Tier R)** — `pt_split` in `_metrics.json`, submode rows in `fit.py`, intervention patronage by declared `intervention.mode` | choice-split (Tier C) still open |
| Ride | paired → physically boarded (§9.53); **booked-but-early passengers physically WAIT (§9.60 M0)**; unpaired → re-modes to walk (§9.55); **unbound observed-rate escort tours re-targeted to driverless-household passengers (§9.60 M1: WEEKDAY 55,280/55,614 bound)** | share stays EMERGENT; measured at the arm |

Still teleported, declared: PT access/egress stubs and the counted
boarding-miss fallback (now near-zero — the waiting path absorbs the old
missed classes). Taxi/rideshare: not a mode (#49, task 4.4).

---

═══════════════════════════════════════════════════════════════════════════════
§3  THE ACTIVE LANE — in order
═══════════════════════════════════════════════════════════════════════════════

1. **Bring the owner the relaunch decision.** The #60 blocker it was
   waiting on is RESOLVED (§9.58, verified to zero refusals). The arm is
   S2 × WEEKDAY, 25% × 1000 on the §9.58–§9.61 family: **~233 s/iteration
   measured → ~65 h single**, or — new option, §9.59 — **two arms
   concurrently** (qsim 8 + events 4 each; both fit 24 CPUs / 63.5 GiB;
   iteration count survives contention). The horizon question is SETTLED
   at the full 1000 (§9.43, §9.57).
2. **The arm's close-out delivers in one pass**: the emergent ride share
   (now with §9.60 lifts) vs 20.60, walk's re-baseline (#30 — its
   diagnosis numbers are from the WEDGED model and must be re-measured),
   `params/C5_calibration.json` via `calibrate.py --constrained-base` +
   the §9.50 report (closing #14, #9), the #48/#31 realised-boarding and
   lift ledgers at convergence, and the M2 (driver-detour) go/no-go from
   what M0+M1 leave unserved.
3. Then by recorded order: #30's generation mechanism (post
   re-measurement), #49 Tier C + taxi (4.4, owner-sequenced), #50's
   modelled table + the mode × age acquisition (#63 item), #62's
   contract parameterisation, #63's remaining derivations.

---

═══════════════════════════════════════════════════════════════════════════════
§4  WHAT IS DONE — do not redo any of it
═══════════════════════════════════════════════════════════════════════════════

- **§9.49–§9.57** (20–21 Aug, PRs #56/#58/#59): freight physical ·
  constrain-and-report · motorbike · physical boarding · walk/bike
  physical · emergent ride · events-based accounting · events threads ·
  the stopped first arm (135 iterations of diagnostics, quarantined).
- **§9.58** (21 Aug, this session): #60's filed mechanism DISPROVEN by
  bytecode (qsim never reads `disallowedNextLinks`; routers apply them
  per mode); the real defect (activities on walk-less links + silent
  nearest-link routes) measured and repaired four ways; verified 0
  refusals on both the old and regenerated demand. **NEW FAMILY
  BOUNDARY.**
- **§9.59**: knob probes run one at a time (`phys_timing2_*`);
  `replanning_threads` = 20 (76→33 s); events 12 = no gain; async events
  = regression; `oneThreadPerHandler` = FATAL; PassingQ = correctness at
  ~42 s price; `-Xms`; `create_graphs` declared. **10×: not reachable
  without shrinking the physical work — the multiplier is concurrency.**
- **§9.60**: M0 + M1 built, regenerated, probe-verified (`lift_probe`
  rc=0, 0 refusals, accounting closes, waiting counters live). Dossier:
  [`design/non-household-lifts.md`](../design/non-household-lifts.md).
- **§9.61**: G15 education split observed per SA1; SAT:SUN 1.1473,
  external weekend 0.8429/0.7347, 1 h shift measured; scaffold speeds
  declared; FOUR assumed fields retired; B1/B2/plans regenerated
  (~4.5 min for the whole chain — the board's old "hours" was wrong);
  manifest 429; `check_package` ALL PASSED.
- **#49 Tier R** done; **#62** (deep city-agnosticism) and **#63** (0b
  backlog) filed with full detail; day-type/scenario CLI vocabulary,
  EPSG transformers and silent fleet-capacity gaps fixed.

**Phases:** P0–P3 ✅ · P4 🟡 (deliverables 0 and 5 open) · P5–P7 ⬜.

---

═══════════════════════════════════════════════════════════════════════════════
§5  WHAT INVALIDATES YOUR WORK
═══════════════════════════════════════════════════════════════════════════════

- **No multi-hour run without owner approval. None standing.**
- **The family boundary is §9.58**: nothing run after it compares to
  `phys50_25pct`, the aborted `phys1000_25pct` diagnostics, or anything
  older. NEVER compare across families or fractions; `target_lga_pct`,
  never `all_residents_pct`.
- **THE 67/143 SPLIT IS PRE-REGISTERED** — `fit.py` enforces; need a
  holdout? SAY SO AND STOP.
- **One build of the network per comparison** (§3.5); `RUN.machine.threads`
  (qsim) and `replanning_threads` are run identity; `event_handler_threads`
  is not (§9.56).
- **No invented data**: who-drives-whom stays unobserved — the lift split
  is REPORTED (§9.60); thin demographic cells stay unvalidatable.
- **A run without `_run.json` is not a result** — the timing probes and
  `lift_probe` are plumbing, and the aborted arm is diagnostics.

---

═══════════════════════════════════════════════════════════════════════════════
§6  EXACT STATE — 21 August 2026, second session close
═══════════════════════════════════════════════════════════════════════════════

| | |
|---|---|
| PRs | The session PR (`praneetdhoolia/goal-physical-speed-and-gaps`) opens at this handoff; all prior 23 merged |
| Toolchain | 3 pinned, unchanged; **14** Java sources compile (+`ActivityLinkAssigner`) |
| Registry | **334 fields** (+7 declared, −4 retired-as-measured); ledger **0** `--strict`; G2 13/13 |
| Package | **429 files**; `check_manifest` OK; **full `check_package` ALL PASSED at session close** |
| Machine | **free**; no run in progress |
| Run cost | **~233 s/iteration at 25% on the new family (declared stack, §9.59) → ~65 h/arm**, or two concurrent arms; it-110-style outliers explained (routing poisoned by gridlock — the §9.58 repairs attack the cause) |
| Runs | All previous families' runs stand as recorded (§6 of the previous brief); **new probes, none results**: `wedge_probe`/`wedge_probe2` (§9.58), `phys_timing2_base/evt/async/fifo` (§9.59), `lift_probe` (§9.60) |
| Open issues | **9**: #48 #49 #50 #30 (directive lanes — build halves done or extended, measurement awaits the arm) · #60 (repaired in-tree, closes with the PR) · #14 #9 (await C5) · #28 #31 (ride ledgers) · plus #62 #63 (filed this session — framework hardening and 0b backlog) = **11 total open** |
| **Results** | **No findings. Nothing is a finding about the light rail.** No completed run exists in the current family |

---

═══════════════════════════════════════════════════════════════════════════════
§7  DECISIONS TAKEN — do not re-litigate
═══════════════════════════════════════════════════════════════════════════════
• Iteration horizon = 1000 (§9.43, §9.57). • §8.5 = CONSTRAIN-AND-REPORT
(§9.50); ASCs stay priors. • RIDE IS EMERGENT (§9.55) and the
non-household-lift mechanism is M0+M1 with M2 deferred and M3 rejected
(§9.60). • Pedestrian exclusion = motorways only; walk/bike ride reverse
complements; activities pin to usable links; SubtourModeChoice is
person-only (§9.58). • PassingQ on correctness; replanning 20; events 4;
sync on; oneThreadPerHandler NEVER (measured fatal) (§9.59). • The
SAT:SUN split, external weekend scaling, weekend shift and tertiary
full-time split are MEASURED — do not re-assume them (§9.61). • Freight
swept never pinned; SCATS refused; Opal swept 3–15 min; dwell swept.
ONE ARM AT A TIME unless the owner approves the two-arm §9.59 pattern.

---

═══════════════════════════════════════════════════════════════════════════════
§8  TRAPS — new ones first, each paid for
═══════════════════════════════════════════════════════════════════════════════
1. **`eventsManager.oneThreadPerHandler` CRASHES this MATSim build**
   (`.initProcessing() has to be called before processing events!`) —
   measured fatal, recorded on the field; do not retry it (cost: one
   ruined 20-min timing probe).
2. **`build_matsim_run_inputs.py --scenarios <subset>` OVERWRITES
   `_run_inputs_report.json` with only that subset** — a later
   full-package check fails "found 9 of 10". Regenerate all scenarios in
   ONE invocation (cost: one failed `check_package` + a 20-min re-run).
3. **Timing probes never share the machine** — not even a single-thread
   pandas job; and `run.py`'s post-run metrics extraction keeps the
   process alive minutes after MATSim exits — wait for the driver's own
   done-marker, not the java process (cost: two false "still running"
   diagnoses).
4. **PowerShell here-strings mangle in this harness** — embedded quotes
   split `git commit -m` / `gh --body` arguments into pathspecs. Write
   the message to a file and use `-F`/`--body-file` (cost: two failed
   commits).
5. **MATSim's `decideOnLink` silently accepts an activity link outside
   the mode's subnetwork** and starts the route at the nearest in-network
   link — the qsim then wedges the vehicle at a disconnected first hop.
   Any new mode or exclusion change must re-verify
   `ActivityLinkAssigner`'s coverage (cost: the whole #60 defect class).
6. **"Fix #NN" in a PR body is a GitHub closing keyword** — write "the
   #NN fix" unless closure is intended. **The G2 test asserts the
   `numberOfThreads` MULTISET** — a new `*.numberOfThreads` binding must
   update the fixture PERTURB. **A `tail -f` monitor holds a Windows lock
   on the run directory.** **1% timing says NOTHING about 25%.** qsim
   component bindings COLLECT; car vehicles carry the BARE person id;
   CLEAR a re-moded leg's route; `render_docs`/`render_schema` after
   registry edits; `pkill` fails — PowerShell `Stop-Process` then VERIFY;
   branch `<git-handle>/<kebab>`, no attribution, STATUS in the same
   commit.

---

═══════════════════════════════════════════════════════════════════════════════
§9  STATE OF THE PROJECT — THE SIX QUESTIONS (21 August 2026, close)
═══════════════════════════════════════════════════════════════════════════════

### 1. Goals & achievement
Research goal (proposal §1/§3): hypotheses A1–A6, B1–B4 — **none tested**.
Operational goal: physical half **COMPLETE, wedge-free, lift-capable**
(§2); checked half awaits the first converged arm of the §9.58–§9.61
family. Proposal §8 deliverables: model 🟡 · data 🟡 (429 files, four
fewer assumptions) · calibration report 🟡 (§9.50 decision done, C5
pending a run) · paper ⬜ · explorer 🟡 · method note 🟡.

### 2. Phases — 4 of 8
P0 ✅ · P1 ✅ · P2 ✅ · P3 ✅ (regenerated 21 Aug on §9.60/§9.61) ·
**P4 🟡 (deliverables 0 and 5 open)** · P5–P7 ⬜. Home:
[`STATUS.md`](../STATUS.md) phase table.

### 3. Tasks
4.1: 9/9 ✅. 4.2: six of eight done-and-evaluated; 4.2.4 decided-not-
delivered (C5 awaits the arm). 4.3 (0b) **started — four fields measured,
backlog is #63**. 4.4 owner-sequenced. Batch 4.5: build halves DONE
(4.5.1 extended by §9.60; 4.5.2's Tier R done); measurement halves await
the arm; **4.5.0 (the relaunch) is the active lane and the owner's
decision**. P5 0/5 · P6 0/5 · P7 0/4 (the four deletion/rework proposals
for 5.2/5.3/6.1/6.2 still await the owner).

### 4. Simulator vs real life
Latest COMPLETED run = `bind1000_25pct` (a family two boundaries back,
pre-calibration diagnostics): car 63.95/59.0 · ride 31.05/20.6 · walk
0.71/13.4 · pt-aggregate 0.36/3.8 · bike 4.0/3.2 · occupancy
0.4855/0.3503 (flattering; REPORTED). The current family has **NO
completed fit** — the aborted arm's snapshots belong to the superseded
family and predict nothing. Every future report lists every mode
individually (Tier R is mechanical now).

### 5. Issue ledger — 40 filed (numbers shared with PRs), 29 closed, 11 open
#60 repaired in-tree (closes with the PR) · #48/#49/#50/#30 directive
lanes (fresh evidence commented 21 Aug; #30 explicitly flagged for
re-measurement on the new family) · #14/#9 await C5 · #28/#31 ride
ledgers · **#62** framework-contract hardening (the audit's
breaks-another-city findings) · **#63** 0b backlog (ranked, incl. two
attended acquisitions). Every closed issue carries its REOPEN IF.

### 6. PR history, and the next PR
23 merged PRs tell the build story (#1–#3 foundations · #38 audit+rebuild
· #40 ride pairing · #43 escort+age · #44 first repaired-demand run ·
#46 freight · #47 calibration decision · #52 motorbike · #53 all-physical
· #58 accounting · #59 events threads + arm launch · #61 PR-only
convention). **This session's PR carries §9.58–§9.61 + Tier R + the
agnosticism fixes.** The next PR after it: whatever the owner's relaunch
ruling produces — the converged arm's close-out (`P4: First converged
all-physical run — C5 and the re-baselines (#14)`).

---

### Bootstrap reading, in this order

```
cities/newcastle/docs/STATUS.md                 the board; §3 above is the lane
cities/newcastle/docs/DECISIONS.md §9.58–§9.61  this session, cross-linked
cities/newcastle/docs/design/non-household-lifts.md   the §9.60 option analysis
issues #62 #63                                  the filed backlogs
.claude/CLAUDE.md                               conventions + hard constraints
```
