# Brief for the next agent — the pilots are measured; FIX RIDE, THEN TAXI

*Rewritten 18 August 2026, after both convergence-pilot arms completed and were
evaluated. This is a HANDOVER, not a source of truth: where it disagrees with
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

**⚠ OWNER DIRECTIVE (18 Aug): NO MULTI-HOUR RUNS WITHOUT EXPLICIT OWNER
APPROVAL.** "We can't afford to run full-day runs every now and then." The
convergence measurements are DONE — two full arms, 42 h of compute, evaluated.
A cancelled 1500-iteration probe was quarantined; do not relaunch it. Your lane
is code, declarations and short verification runs. When the ride sitting needs
its solver runs (~hours each), state the cost and get a yes first.

**Check `results/` before anything:** `conv1000_10pct` and `conv1000_25pct`
(both rc=0, both evaluated — the evidence base for your work), plus
`smoke_postrebuild` (plumbing). `results/_aborted_20260816/` is quarantined
garbage the classifier wouldn't let us delete; the owner can. A run with no
`_run.json` is not a result and is not kept.

**Your first task costs no compute:** the #5 declaration (§3.1). Everything
else is gated behind it.

---

═══════════════════════════════════════════════════════════════════════════════
§1  THE MISSION — the owner's own words, then the state
═══════════════════════════════════════════════════════════════════════════════

The owner's standing goal (given via `/goal`, 18 Aug — treat as the directive):

> **Goal: a digital twin of any given city (traffic-wise), simulating the
> entire population or a percentage of it — if a percentage, congestion and
> capacity are scaled accordingly, and whether that scaling actually predicts
> the correct ridership per mode must be CHECKED, not assumed.** The twin is
> implemented in the context of Newcastle, where the light-rail project gives
> claims we can actually evaluate. **Get to fixing the ride share (by riding
> actual cars) and the taxi, etc. ridership now.** Token limit applies: don't
> pick up tens of tasks in one go — do it right rather than bloating the repo
> with unnecessary data or overcomplicated workflows.

The owner's three onboarding questions are ANSWERED — do not redo them, read
them: data inventory + decision-making data assessment and the full task/ETA
alignment live in `STATUS.md` (the numbered plan, re-aligned 18 Aug); the
"what work next" answer is §3 of this brief. The fraction-scaling check the
goal demands has its first measurement: walk/pt/bike shares identical across
10% and 25% to 0.1 pp; the car↔ride margin shifts ~3.7 pp — re-test after the
ride fix, since that margin is currently dominated by the ride defect.

| # | Goal | State |
|---|---|---|
| **G1** | Answer the light-rail counterfactual (calibrated base → S0–S6 → 143 sealed holdouts opened once → findings with uncertainty bands) | Inputs trustworthy; pilots measured; **calibration is the work, and the ride sitting is its first move** |
| **G2** | City-agnostic simulator, full input schema | ✅ exercised: 13 assertions in CI; ledger 0 `--strict`; reach 69/69 by perturbation |

The law that guards everything: **every value is DECLARED in
`cities/<city>/registry/` and REACHES the model through the resolver.** 9 of 10
rail forecasts overestimate patronage (avg +106%); a flattering answer is the
EXPECTED failure mode.

---

═══════════════════════════════════════════════════════════════════════════════
§2  WHAT IS DONE — do not redo any of it
═══════════════════════════════════════════════════════════════════════════════

**The 16 Aug rebuild (PR #38, merged):** harvest 10/10 layers, 99→4 SA1s
without a road node (0 agents); 181,892 links at declared speeds; 15 GTFS feeds
mapped in ONE build, 0 unmapped stops; demand regenerated with the five fixes;
`check_package` 1,452 ALL PASSED; manifest 391.

**The convergence pilots (17–18 Aug, evaluated in
[`docs/audit/CONVERGENCE_PILOT_EVALUATION.md`](../audit/CONVERGENCE_PILOT_EVALUATION.md)):**

- Both arms (10% × 1000, 11.0 h · 25% × 1000, 30.8 h) **fail the declared
  drift gate identically** (+3.54 / +3.60 pp, car) — and the decomposition is
  the finding: **~3.4 pp is a selection snap completing within 10 iterations of
  the innovation cutoff at BOTH fractions** (walk 4.0→1.0%, pt 1.1→0.25%),
  followed by a frozen tail (true drift +0.09 / +0.17 pp — inside tolerance).
  A run of ANY length fails the current 800-vs-1000 window while the snap
  exists. Pre-cutoff search creep decays ×0.73 per 100 iterations at both
  fractions (~2 pp extrapolated remainder). Fraction-independence established.
- **Fit (uncalibrated floor):** mode MAE 6.95 pp at 25% (car −1.2, ride +16.6,
  walk −12.7, pt −3.4, bike +0.8). Ride out-runs car in EVERY bin <50 km
  (1.13×→1.01×; aggregate parity is a Simpson's reversal — never compare
  aggregate means). Occupancy 0.64 vs 0.35 observed. Counts −92% mean, 7 zero
  stations, V113 (M1 Wyee) 60 vs 44,885 — reopen conditions for #30 and #20
  are MET (recorded in the evaluation; issue actions ride with the sitting).
  Counts gap is structural (no-alternative rural stations fit at −31%/−6%;
  urban arterials near zero → flat-hierarchy / rat-run hypothesis, unverified).
- **Run economics (measured):** 33.3 s/iter @10% (29 GiB WS on 30g); 90.2 s
  @25% (33–38 GiB on 40g); memory model ≈ 24 GiB fixed + 0.09–0.3 MB/agent →
  100% needs ~80–160 GiB heap. Software savings available: plan-dump I/O ~6%,
  post-cutoff tail 200→50 iters ~15%. One unattributed slow block (25% arm,
  iters ~200–293, self-recovered) — the old stall pattern; do not assume gone.

**Also done 18 Aug:** taxi/rideshare evidence dossier
([`docs/design/point-to-point-mode.md`](../design/point-to-point-mode.md));
ride mechanism inventory (§3.2); an explainer artifact for the owner (agents /
infrastructure / iterations) — ask them for the link if needed.

**Phases:** P0–P3 ✅ · **P4 in progress** (deliverables 0 and 5 open) · P5–P7
not started. Full plan + ETAs: `STATUS.md`.

**Open issues — six:** #5 (declare NOW, §3.1), #9 + #28 + #31 (one sitting,
§3.2), #14 (after), #24 (freight, own PR). #20 and #30 have their reopen
conditions met on pilot evidence — act on them with the sitting, not before.

---

═══════════════════════════════════════════════════════════════════════════════
§3  ★ YOUR JOB: THE RIDE SITTING, THEN TAXI
═══════════════════════════════════════════════════════════════════════════════

### 3.1 First, the #5 declaration — paperwork, no compute, gates everything

From the two measured arms (do NOT run more):

- Declare `RUN.controler.last_iteration` = **1000** with the pilots as
  provenance; update the shipped default off the provisional 250.
- **Redefine the drift window snap-aware** (measure from cutoff+50 → final, or
  equivalent): the current declared instrument catches the fraction-independent
  selection snap and can NEVER pass — that is a defect in the metric, not the
  run. New/changed field with sweep; `summarise_run.py` consumes it.
- Log both in `DECISIONS.md` (the ~2 pp unresolved pre-cutoff creep is stated
  as declared uncertainty — the cancelled 1500 probe would have measured it;
  the owner traded that for compute economy, record the trade). Regenerate
  `render_docs.py` + `render_schema.py`. Close #5.

### 3.2 THE RIDE SITTING — "riding actual cars", the feasible way (#28 #31 #9)

**Mechanism, already inventoried (verify, then build):** `routing.networkModes
= car,ride` but `qsim.mainMode = car` — ride follows a real road path at the
ROUTER'S estimated time while car pays the queue's ACTUAL time; ride pays the
fuel-rate money but no parking charge (deliberate — same vehicle twice) and NO
pickup/drop-off time. Hence ride out-running car worst at short range: the
signature of a missing FIXED friction.

One focused PR, every value declared with a sweep:

- **(a) Congested time for ride:** bind ride's routing/teleport time to car's
  realised (previous-iteration) travel times — an `addTravelTimeBinding("ride")`
  -pattern change in `CitysimControler`, behind a declared toggle field.
  Passengers experience real traffic without adding phantom vehicles to the
  counts (do NOT make ride a qsim main mode — that double-counts the escort
  driver's car, which B2 already generates).
- **(b) Pickup/drop-off friction:** a declared, swept minutes-per-ride-leg
  field reaching the model (routing- or scoring-side — pick the binding that
  provably reaches, trap 7). This is what kills the 1.13× short-bin residual.
- **(c) Occupancy:** re-solve `asc_car_passenger` with `solve_asc_ride.py`
  (deterministic, resumable) so the equilibrium reproduces **0.35
  passengers/driver** (declared range 0.25–0.394) — #31's constraint through
  #9's solver, at the §3.1 horizon. **Solver runs are multi-hour: cost them
  out and get owner approval first (§0).**
- Re-measure the §2 slate on the sitting's verification run: bins (a script
  pattern exists in the evaluation doc), occupancy, shares, sub-1 km, V113.
  Close or size #28; decide #20/#30 actions on the new evidence.

⚠ **#31 trap, verbatim from the audit:** eqasim's `PassengerConstraint` is a
trip-level biconditional on `getInitialMode()`; no driver is consulted.
Adopting it PINS THE RIDE SHARE TO THE B2 SEED. **Do not add `ride` to
`chainBasedModes`.** A copied constraint compiles, runs, constrains nothing
and reports success.

**Full passenger-in-vehicle coupling (joint plans / socnetsim) stays the
logged backlog escalation** — a §14 toolchain change. Revisit ONLY if (a)–(c)
leave a measured residual.

### 3.3 Taxi + rideshare — task 4.4, right after the sitting

Owner re-opened the declined decision on new evidence (18 Aug). The dossier
([`docs/design/point-to-point-mode.md`](../design/point-to-point-mode.md)) has
fares (measured: flagfall $5.17, $2.61/km first 12 km), fleet (~175 taxis
greater Newcastle, literature), and an inferred volume band (10k–35k trips/day,
~0.5–1.5% of trips). Build: **teleported priced mode**, all values declared
with grade + sweep, validated against the band as a **constraint, never a
target** (the 67/143 split cannot grow). First step: extract the Newcastle &
Hunter table from the IPART 2025 information paper (the PDF times out on
WebFetch — try a browser tool or download locally). Write the DECISIONS.md
re-opening entry WITH the build.

### 3.4 Then, in order

1. **#14** — calibrated base: ASCs on era 3 (2018), HELD FIXED; **log the
   departure before any result is seen**; 0b derivations ride along (STATUS 4.3).
2. **#24** — freight, own PR: real `truck` mode with vehicle type + PCE, NOT
   inflated car agents.
3. **P5** — SUMO harness + scenario runs; still deliberately unsimulated.

---

═══════════════════════════════════════════════════════════════════════════════
§4  WHAT INVALIDATES YOUR WORK
═══════════════════════════════════════════════════════════════════════════════

- **No multi-hour run without owner approval** (§0). State cost, get a yes.
- **Nothing pre-rebuild is comparable to anything post-rebuild.** And the ride
  sitting is itself a model change: post-sitting runs are a NEW comparison
  family — the pilot arms become context, not baselines.
- **NEVER compare across sample fractions** (1% is a plumbing fraction), and
  `target_lga_pct`, never `all_residents_pct`.
- **THE 67/143 SPLIT IS PRE-REGISTERED.** Never calibrate on, re-split, or
  peek at a holdout row; `fit.py` enforces it. Need one? SAY SO AND STOP.
- **One build of the network per comparison** — never re-run the mapper
  casually. Threads = 10, part of the run identity.
- **No invented data.** Inferred values (the taxi dossier) are labelled,
  swept, and logged before any result is quoted.
- **A run without `_run.json` is not a result.**

---

═══════════════════════════════════════════════════════════════════════════════
§5  EXACT STATE — 18 August 2026
═══════════════════════════════════════════════════════════════════════════════

| | |
|---|---|
| Branch | `praneetdhoolia/convergence-pilot-arms` — **3 commits ahead, UNPUSHED** (pilot evaluation + board, taxi dossier + task 4.4, ride-sitting alignment). Raise the PR or continue on it |
| `main` | the merged 16 Aug rebuild (PR #38); CI green |
| Registry | 297 fields; ledger 0 (`--strict` in CI); reach 69/69 |
| `results/` | `conv1000_10pct` + `conv1000_25pct` (evaluated) · `smoke_postrebuild` · `_aborted_20260816/` (quarantine, owner may delete) |
| Machine | 63.5 GiB RAM, 24 logical cores, 2-channel laptop — ~2.7 cores busy per run; memory is the binding constraint. Hardware/cloud options are scoped in the session record if the owner asks |
| Open issues | 6 — #5 #9 #14 #24 #28 #31 (#20/#30 reopen conditions met, actions pending the sitting) |
| **Results** | **NONE. The pilots are run-state measurements, not findings about Newcastle. Nothing is calibrated until deliverable 5.** |

### Bootstrap reading, in this order

```
cities/newcastle/docs/STATUS.md                      the board + numbered plan (re-aligned 18 Aug)
cities/newcastle/docs/audit/CONVERGENCE_PILOT_EVALUATION.md   the pilot evidence your work stands on
cities/newcastle/docs/design/point-to-point-mode.md  taxi dossier + build plan
cities/newcastle/docs/DECISIONS.md                   START AT ITS INDEX
.claude/CLAUDE.md                                    conventions + hard constraints
```

---

═══════════════════════════════════════════════════════════════════════════════
§6  DECISIONS TAKEN — do not re-litigate
═══════════════════════════════════════════════════════════════════════════════
• #5 DECLARES FROM THE TWO ARMS; the 1500 probe was cancelled BY THE OWNER for
  compute economy. Do not relaunch it; record the residual-creep uncertainty.
• RIDE FIX = the §3.2 sitting, NOT joint plans (backlog escalation only on a
  measured residual). DO NOT add ride to qsim main modes (phantom vehicles).
• TAXI/RIDESHARE: the old "declined" entry is SUPERSEDED — re-opened by the
  owner 18 Aug on new evidence (IPART regional survey; the levy counts every
  trip). Build per the dossier; constraint, never target. Owner said NO to
  lodging data requests — infer from open sources, labelled and swept.
• DELIVERABLE 5 TAKES §8.5's FIRST BRANCH: ASCs on era 3 (2018), HELD FIXED.
  LOG THE DEPARTURE BEFORE ANY RESULT IS SEEN.
• SCATS refused by policy (§9.21), journey-linked Opal unpublished (3–15 min
  transfer sweep, §9.32), charging dwell = field measurement only — all swept,
  never pinned. Pre-tram signal count stays 14. The 30 h qsim window is correct.
• ONE ARM AT A TIME stays settled. n_replications stays 30 until seed variance
  is MEASURED. Northern through exits stay ungated this build (§9.41).
• STILL DECLINED, do not re-raise: touching the 143 holdout targets; deleting
  the 13 Opal card-type rows; weather in mode choice (wet-day arm instead);
  motorcycle as its own mode (no target exists — the taxi re-opening does NOT
  extend to it); year-long / multi-day simulation (the targets are typical-day
  quantities; day-of-week texture arrives via 0b as a possible fourth day type).

---

═══════════════════════════════════════════════════════════════════════════════
§7  TRAPS — each has already cost a day (or nearly)
═══════════════════════════════════════════════════════════════════════════════
1. **HEREDOCS MANGLE OR FAIL — bash AND PowerShell** (`<<'PY'` is a parse error
   in PowerShell). Write scripts with the Write tool, run the file.
2. **`compileall` does not catch a NameError.** A script can pass every check
   and die on its first statement.
3. Everything is seeded **20260810**. After ANY registry edit: `render_docs.py`
   AND `render_schema.py`, or CI fails on staleness. After any data change:
   `normalise_eol.py` → `build_manifest.py` → `normalise_eol.py`.
4. The layers contract carries no machine state — no `os.path.exists` in a
   committed generated file.
5. `pkill` does not work; PowerShell `Stop-Process`, then VERIFY it died.
   Note: `Get-Process`'s `.CPU` diff can read 0 on a busy JVM — trust the log's
   own timestamps over a single process-CPU sample.
6. Branch `<git-handle>/<short-kebab>`, never `claude/*`. No attribution
   trailers, no session links. Commit messages state what changed in the MODEL
   or the DATA. **Keep `STATUS.md` current in the SAME commit.**
7. **Verify the consumer, not the mechanism.** Establish reach by changing the
   value and watching the output change — reading code has never once caught a
   dead binding here. The sitting's new fields get the same treatment.
8. **Reproduce a defect before attributing it**; when you fix one, write the
   check that would have caught it.
9. **Big agency PDFs (IPART) time out on WebFetch**; search-result summaries
   carry the headline numbers, a browser tool or local download gets tables.
10. **The declared drift metric would fail ANY horizon** until §3.1 lands —
    do not read a failed relaxation light as "run longer" before fixing the
    window it is scored on.
