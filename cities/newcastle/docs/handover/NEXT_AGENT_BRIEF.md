# Brief for the next agent — FOUR OWNER DIRECTIVES SET THE VALUE ORDER; RESEARCH #48 FIRST

*Updated 20 August 2026 (evening). Three things happened this session, in
order: **freight became physical** (§9.49, PR #46 — a `truck` mode in the
mobsim at declared PCE, smoke-verified, a planned comparability break);
**the §8.5 calibration decision was taken and logged before its run's
results existed** (§9.50, PR #47 — constrain-and-report; ASCs stay priors;
the §9.48 occupancy excess is reported, not absorbed) — and its base arm was
then **STOPPED by the owner at ~iteration 20** and quarantined, so
deliverable 5 stays open; and the owner issued **four standing directives**
(§9.51) that reset the value order — recorded as issues **#48, #49, #50 and
re-opened #30**. This is a HANDOVER, not a source of truth: where it
disagrees with [`STATUS.md`](../STATUS.md), [`DECISIONS.md`](../DECISIONS.md)
or [`.claude/CLAUDE.md`](../../../../.claude/CLAUDE.md), those win.*

---

═══════════════════════════════════════════════════════════════════════════════
§0  DO THIS FIRST
═══════════════════════════════════════════════════════════════════════════════

**Run `/onboard`** — it executes this section as a skill. At session end, run
`/handoff`. The checks, for a session without the skills:

```bash
python src/setup/bootstrap_toolchain.py --verify   # ~1 min, COMPILES THE JAVA (8 sources)
python tests/check_manifest.py                     # committed subset intact
python src/registry/check_hardcoding.py --strict   # must exit 0
```

**⚠ OWNER DIRECTIVES, all standing:**

1. **NO MULTI-HOUR RUNS WITHOUT EXPLICIT APPROVAL.** State the cost, get a
   yes. **No standing approval exists**: the §9.48 arm's approval was spent
   on 20 Aug, and the §9.50 base arm's launch was consumed the same day —
   the owner then **stopped that run at ~iteration 20**. Treat every future
   arm as unapproved until asked for by name with its cost.
2. **DO ONE THING RIGHT rather than bloating the repo.**
3. **THE FOUR §9.51 DIRECTIVES** (verbatim intent, 20 Aug):
   - *Every ride trip is a passenger PHYSICALLY in the car. No exceptions.
     No teleportation. And ride is over-supplied — tune it to real life.*
     (**#48 — research this FIRST, exhaustively, before building anything.**)
   - *All 9+ modes of transport distinguished and unique — never under a
     `pt` or `Other` umbrella; motorbike and taxi/rideshare individualised
     into their distinct shares.* (#49)
   - *The walk row is structural — the model generates too little sub-1 km
     trip mass. Fix it.* (#30, re-opened under its own REOPEN IF)
   - *Mode distributions across age groups, jobs, etc. identical to real
     life.* (#50 — bounded by what is observed; constraints, never targets)

**Start from `main` once the PR stack merges** — the stack is
**#46 (freight) ← #47 (calibration decision) ← the handover PR**, and they
must merge in that order. **No run is in progress**; the machine is free.

---

═══════════════════════════════════════════════════════════════════════════════
§1  THE GOAL, AND THE SENTENCE THAT GOVERNS EVERYTHING
═══════════════════════════════════════════════════════════════════════════════

> **A digital twin of any city, traffic-wise: simulate the whole population or
> a percentage of it — and if a percentage, congestion and capacity scale
> accordingly, and whether that scaling actually predicts the correct ridership
> per mode must be CHECKED, not assumed.** Implemented for Newcastle, where the
> light-rail project gives claims we can evaluate. **Every form of transport
> should be IN ACTION physically.**

"CHECKED, not assumed" has caught, to date: the person-hashed sampler
(§9.45), the starved ride pairing (§9.44 — fewer than 1 in 1,000 pairable),
the phantom elderly commuters (§9.47), and this session the calibration
loop's own movable-set defect (§9.50 — unclassified consumers defaulted to
"movable at run time", putting the OSM harvest margins in the search space).

**The standing risk:** 9 of 10 rail forecasts overestimate patronage (avg
+106%). The §9.48 occupancy excess (0.4855 vs 0.3503, flattering direction)
is this project's first measured instance of an error pointing the flattering
way. It is REPORTED, never absorbed (§9.50).

---

═══════════════════════════════════════════════════════════════════════════════
§2  THE MODES — WHAT IS PHYSICAL NOW, AND WHAT EACH DIRECTIVE DEMANDS
═══════════════════════════════════════════════════════════════════════════════

Measured, not assumed. **Six of nine-plus are physically in the mobsim**:

| mode | state | evidence |
|---|---|---|
| Cars | ✅ physical | qsim `mainMode`, explicit car type = MATSim default, proven against bytecode (§9.49) |
| **Trucks** | ✅ **physical (NEW, §9.49)** | PCE 2.0 (swept 1.5–3.5), 100 km/h cap; smoke: 913 trips, 922 vehicles, 140,380 link traversals at 1% |
| Buses | ✅ physical | 1,448 vehicles, PCE 2.8, 22,102 road links shared with cars |
| Trains | ✅ physical | 332 vehicles, 6,766 dedicated rail links |
| Light rail | ✅ physical | 252 vehicles, incl. 21 on-street shared links |
| Ferries | ✅ physical | 107 vehicles (Stockton) |
| Ride | ⚠ paired, TELEPORTED — **#48 ends this** | §9.44 Tier 1; §9.48: 1.30% of ride trips pair; the passenger inherits a clock, occupies no seat |
| Walk / bike | teleported (MATSim design) | #30 owns walk's structural deficit |
| Motorbike / taxi+rideshare | not modes — **#49 ends this** | G62 verified to carry both as observed JTW columns |

---

═══════════════════════════════════════════════════════════════════════════════
§3  WHAT DATA EXISTS FOR THE DIRECTIVES — verified locations, not hopes
═══════════════════════════════════════════════════════════════════════════════

- **`data/processed/census/census2021_G62_SA1.csv`** — VERIFIED at handover
  to carry per-SA1, per-sex journey-to-work counts with **every directive-2
  mode as its own observed column**: Train, Bus, Ferry, Tram/light rail,
  Taxi/Rideshare, Car-as-driver, Car-as-passenger, Truck,
  **Motorbike/scooter**, Bicycle, Walked-only, Other.
- **C1 already declares per-submode constants** (asc_bus −1.05, asc_lr −0.75,
  asc_rail −0.65) that **collapse to one `pt`** in the MATSim translation
  (§9.3 `not_representable`). The spec is ahead of the implementation.
- **HTS `Other` does NOT contain motorcycle** — it sits inside `Vehicle
  driver`/`Vehicle passenger`, so carving motorbike out SHRINKS the car and
  ride targets. `fit.py:49`'s caveat states this wrongly; correct it when
  touched.
- **The freight temporal machinery generalises**: `extract_freight_profile.py`
  measured hourly shapes and weekend factors from classified counts — the
  same raw data may support other measured profiles.
- **The behavioural layer is still 58% assumed or literature** (55 fields:
  20 assumed, 12 literature, 11 measured, 8 derived, 4 definition). No
  stated-preference survey exists for Newcastle; journey-linked Opal is
  unpublished. **Every headline must carry its band.**

---

═══════════════════════════════════════════════════════════════════════════════
§4  THE FOUR DIRECTIVE LANES — what each must confront (research first!)
═══════════════════════════════════════════════════════════════════════════════

### 4A — #48: physical ride (FIRST)

The directive's two halves are one fix: a physical-service constraint caps
ride at what the driver supply can carry, which is also the tuning mechanism
(modelled 31.05% vs observed 20.60%; occupancy 0.4855 vs 0.3503).

**On the record, do not rediscover:**
- socnetsim joint plans: **measured ~10× runtime** and reverted by owner
  instruction. That cost is the benchmark; the owner's new directive re-opens
  the question but does not repeal the price.
- eqasim's `PassengerConstraint` consults no driver — compiles, runs,
  constrains nothing.
- **Vanilla qsim boards no passengers into private cars.** Candidate
  mechanisms to research: socnetsim/joint plans (cost known), DVRP-style
  dispatch of household vehicles, demand-level joint tours (escorter and
  escortee written into one vehicle's plan at build time — the §9.46 binding
  already co-locates them in space and time).
- **26.2% of households are lone-person — 64,334 people with NO possible
  in-household driver, ever** — and non-household lifts have no target.
  Under "no exceptions", unpairable ride demand must RE-MODE; the research
  must state what the observed 20.6% implies about non-household lifts
  before deciding where that demand goes.
- The §9.48 realisation gap (15.31% OD-coincident vs 1.30% paired, ×12) is
  decomposed on paper (mode co-assignment; realised-vs-planned windows;
  `both_links` link resolution) and unmeasured beyond the headline. #31
  holds the measurement ledger.

### 4B — #49: modes individualised

Order the research cheap-to-dear: **(1)** per-submode REPORTING from events
(bus/train/LR/ferry realised shares — the fleet is already distinct; `pt_boardings`
per line already exist); **(2)** choice-distinct PT submodes (SwissRailRaptor
mode mappings / per-submode scoring — C1's constants are waiting); **(3)**
motorbike as a mode (G62 observed commute anchor; non-commute share swept,
never pinned; a motorbike PCE exists in literature); **(4)** taxi/rideshare
(the §9.42 dossier and [`design/point-to-point-mode.md`](../design/point-to-point-mode.md)
are current; task 4.4's plan stands, now elevated).

### 4C — #30 (re-opened): the sub-1 km walk mass

Measured: 2.5% of trips under 1 km vs >~10% observed; walk 0.71% vs 13.40%;
modelled walk trips 2.43 km mean vs ~0.7 observed. Scoring (§9.28) and
placement decay (§9.40) are ALREADY repaired — do not re-fix them. **First
step is a decomposition, not a fix**: per purpose × LGA, against the held
HTS distance distributions (C4), find where the sub-1 km mass is lost —
generation (tours anchor on zone attractors; no corner-shop micro-trips),
placement, or mode choice.

### 4D — #50: demographic-conditional fidelity

Inventory FIRST (which mode × age / employment cells are actually observed,
census and HTS, with cell sizes), measure the model against them from run
events joined to B1 attributes (the population already carries census
age/employment, §9.47), and only then decide mechanisms. New observables are
**constraints, never targets** (§9.8/§9.13); the 67/143 split is untouched.

### 4·0 — the sequencing decision (owner)

Every one of 4A–4C changes the demand family. Relaunching the 4.2.4 base arm
(~35 h, needs approval) BEFORE them buys a calibrated base the directives
immediately break; AFTER them it anchors the final model. Bring this to the
owner as the first question of the next session.

---

═══════════════════════════════════════════════════════════════════════════════
§5  WHAT IS DONE — do not redo any of it
═══════════════════════════════════════════════════════════════════════════════

**FREIGHT IS PHYSICAL (§9.49, PR #46, 20 Aug).** `truck` in `qsim.mainMode`
at declared PCE via an explicit vehicles file the harness re-emits per run
(a swept `B.freight.pce` reaches the mobsim); through-gate volumes split
car/truck by each station's own observed heavy share (conservation exact:
16,264 + 1,691 = the old 17,955); 88,702 internal weekday trucks over the
observed freight-industry attractor; hourly profile and weekend factors
MEASURED from 33,816 classified station-days. Smoke-verified. Registry 316
fields, ledger 0, package 1,466 checks, manifest 423 files. **A planned
family boundary: `bind1000_25pct` is the last run of the §9.46/§9.47
family.** Do not rebuild; do not compare across it.

**THE §8.5 DECISION IS TAKEN AND LOGGED (§9.50, PR #47, 20 Aug) — before any
result of the new family existed.** Constrain-and-report: ASCs stay at
priors, held fixed; #9 resolved by decision (no re-solve — the occupancy
excess is reported, not absorbed); the loop's movable set corrected to
exactly 2 legitimately searchable parameters and the ~21-run search DECLINED
with its cost stated; `calibrate.py --constrained-base TAG` builds C5 from
one run's fit and refuses a run without `_run.json`. **Not delivered: C5 and
the report themselves** — the base arm was stopped (§9.51).

**Everything in the 18–20 Aug family**: escort binding (§9.46), age
structure (§9.47), the re-measure arm and its evaluation (§9.48), ride
pairing Tier 1 (§9.44), household sampling (§9.45), iterations=1000
(§9.43). All measured, all recorded, none to be redone.

**Phases:** P0–P3 ✅ · **P4 in progress** (deliverables 0+5 open) ·
P5–P7 ⬜.

---

═══════════════════════════════════════════════════════════════════════════════
§6  WHAT INVALIDATES YOUR WORK
═══════════════════════════════════════════════════════════════════════════════

- **No multi-hour run without owner approval. None is standing.**
- **Never compare across demand families**: three boundaries now — pre-§9.44,
  the §9.46/§9.47 family (ends at `bind1000_25pct`), and the §9.49 freight
  family (no completed run yet).
- **NEVER compare across sample fractions**; `target_lga_pct`, never
  `all_residents_pct`.
- **THE 67/143 SPLIT IS PRE-REGISTERED.** Never calibrate on, re-split or
  peek at a holdout row; `fit.py` enforces it. Need one? SAY SO AND STOP.
- **One build of the network per comparison** (§3.5). Threads = 10 is part
  of run identity.
- **No invented data.** Unobserved → assumed/modelled, labelled, swept.
  This binds directives #49/#50 hard: G62 anchors commute; non-commute
  shares for motorbike/taxi are swept, and thin demographic cells are
  stated as unvalidatable, never filled in.
- **A run without `_run.json` is not a result.**
- **`controler_sha256()` hashes only `src/java/`** — still unfixed; fix when
  any toolchain change lands.

---

═══════════════════════════════════════════════════════════════════════════════
§7  EXACT STATE — 20 August 2026, session close
═══════════════════════════════════════════════════════════════════════════════

| | |
|---|---|
| Branch / PRs | Stack: **#46 (freight) ← #47 (calibration decision) ← the handover PR** — merge in order, then start from `main` |
| Toolchain | 3 pinned — JDK 25.0.4+7, pt2matsim 26.6, SUMO 1.27.1. Unchanged |
| Java | 8 sources; **the freight change needed NO Java change** (`lockedMode` is generic) |
| Registry | **316 fields** (§9.49: six `B.freight.*` + `RUN.qsim.car_vehicle`); ledger **0** `--strict`; reach **74/74** |
| Package | **423 files**; `check_package.py` **1,466 checks ALL PASSED** (2 standing warnings); demand is the §9.49 freight family |
| Machine | 63.5 GiB RAM, 24 cores; memory is the binding constraint; **no run in progress** |
| Run cost | §9.48 family: median 105.9 s/iter at 25% → ~35 h per 1000-iteration arm. The freight family adds ~5% more agents at PCE ≥ 1 — expect slightly slower; unmeasured |
| Runs | `results/bind1000_25pct/` — the only valid full run (§9.48), last of its family. `freight_smoke` + `ride_pairing_probe` are plumbing probes. `results/_aborted_20260820/` quarantines the owner-stopped `base1000_25pct` and the old `S2_WEEKDAY_f025_i1000_s20260810` |
| Open issues | **9**: #48 #49 #50 (directives) · #30 re-opened · #14 #9 (await a completed base arm) · #28 #31 (ride ledgers) · #24 (closes with PR #46) |
| **Results** | **No findings. Nothing is a finding about the light rail.** The §9.48 fit rows are pre-calibration diagnostics of a superseded family |

---

═══════════════════════════════════════════════════════════════════════════════
§8  DECISIONS TAKEN — do not re-litigate
═══════════════════════════════════════════════════════════════════════════════
• **THE §8.5 BRANCH IS CONSTRAIN-AND-REPORT (§9.50), logged before results.**
  Era-3 estimation is recorded infeasible as stated (no 2018 demand; the
  historical reconstruction stays dropped). ASCs stay priors; the §9.48
  occupancy excess is REPORTED.
• **#9 IS RESOLVED BY DECISION** — `asc_car_passenger` is not re-solved
  against the excess; that would be ASC absorption.
• **THE PARAMETER SEARCH IS DECLINED WITH ITS COST STATED** (2 movable
  parameters, ~21 × 35 h runs, cannot reach the structural misfits). The
  loop stays built and gated.
• **FREIGHT IS A BACKGROUND LOAD, SWEPT NEVER PINNED** (§9.49). Truck
  routing unconstrained — a stated limitation, not a defect to quietly fix.
• **`bind1000_25pct` IS THE LAST RUN OF ITS FAMILY.**
• Tier-1 ride pairing stays the merged baseline until #48's successor lands;
  `both_links` stays the declared pairing rule; return trips pair
  independently; non-household lifts are not built (no target).
• Motorbike's old "declined" stance is superseded by #49 **to the extent G62
  anchors it** — the no-invented-data rule still bounds everything.
• SCATS refused by policy; journey-linked Opal unpublished (3–15 min sweep);
  charging dwell swept — never pinned. ONE ARM AT A TIME.

---

═══════════════════════════════════════════════════════════════════════════════
§9  TRAPS — each has already cost time (new ones first)
═══════════════════════════════════════════════════════════════════════════════
1. **`modeVehicleTypesFromVehiclesData` demands a vehicle type for EVERY
   routing.networkMode, not only the qsim main modes** — the first freight
   smoke died in 10 s with `Could not find requested vehicle type = ride`.
   The vehicles file now carries a `ride` type restating the car (§9.49);
   keep it if you add network modes.
2. **The calibration loop's stage table treats UNCLASSIFIED consumers as
   excluded** (§9.50). If you add a build script that consumes a swept
   field, classify it in `STAGE_OF_CONSUMER` or the field is silently
   uncalibratable — which is correct but should be knowing.
3. **HEREDOCS MANGLE OR FAIL — bash AND PowerShell.** Write the script with
   the Write tool, run the file.
4. **`compileall` catches neither a NameError nor a schema-shape TypeError.**
   Import the module and CALL it. (`sweep` may be a bare list OR
   `{"interval": [...]}`.)
5. Everything is seeded **20260810**. After ANY registry edit:
   `render_docs.py` AND `render_schema.py`. After any data change:
   `normalise_eol.py` → `build_manifest.py` → `normalise_eol.py`.
6. **VERIFY THE CONSUMER, NOT THE MECHANISM.** Bytecode over API docs
   (§9.44, and §9.49's car-type equality). Reading code has never once
   caught a dead binding here.
7. **Reproduce a defect before attributing it.**
8. **A broad log grep will false-positive**: `Unsupported class file major
   version 69` is benign (Guice's ASM vs Java 25), in every run.
9. `pkill` does not work; PowerShell `Stop-Process`, then VERIFY it died
   (used again this session to stop the base arm).
10. **A run's live log is `<run_dir>/matsim.log`, NOT `output/logfile.log`**
    (a 0-byte stub).
11. Branch `<git-handle>/<short-kebab>`, never `claude/*`. No attribution
    trailers, no session links. **STATUS.md current in the SAME commit.**
12. **Big agency PDFs (TfNSW, IPART) return HTTP 403 to WebFetch.** The HTS
    data document is local at `data/raw/hts/hts_data_document_2020_2024.pdf`.

---

═══════════════════════════════════════════════════════════════════════════════
§10  STATE OF THE PROJECT — THE SIX QUESTIONS (20 August 2026, session close)
═══════════════════════════════════════════════════════════════════════════════

### 1. Goals, and what is achieved

**Research goal** ([proposal](../design/newcastle-lr-proposal.md) §1, §3):
test the untested claims about the Newcastle Light Rail — hypotheses A1–A6,
B1–B4 (B3 decisive), secondary S-a–S-d. **Operational goal** (§1 above): a
per-mode-checked traffic digital twin, every mode physical. **Achieved**: the
423-file provenance package; the networks (15 mapped feeds, 4 SUMO nets);
the 612,687-person demand with census age structure, bound escorts and now
a physical freight tier; the 316-field registry at ledger 0; the run harness;
**six of nine-plus modes physically simulated**; one valid full run
(superseded family). **No hypothesis is tested.** Proposal §8 deliverables:
model 🟡, data package 🟡, calibration report 🟡 (decision taken §9.50, base
run pending), paper ⬜, explorer 🟡, method note 🟡.

### 2. Phases — 4 of 8 complete

P0 ✅ · P1 ✅ (for P4's needs) · P2 ✅ (rebuilt 16 Aug) · P3 ✅ (regenerated
20 Aug with freight) · **P4 🟡 (deliverables 0 and 5 open; 5 is
decision-done, run-pending)** · P5–P7 ⬜. Home: [`STATUS.md`](../STATUS.md).

### 3. Tasks — done and evaluated, per batch

- Batch 4.1 (rebuild): **9/9 done**, gates measured.
- Batch 4.2: **6 of 8 done and evaluated** — 4.2.1 (§9.43), 4.2.2, 4.2.3
  (§9.44+§9.48), 4.2.5 (§9.46), 4.2.6 (§9.47), 0d complete in all three
  parts (§9.41, spec-audit B1, §9.49/#24). **4.2.4 decided-not-delivered
  (§9.50)**; 4.3 (deliverable 0b) open; 4.4 folded into #49.
- **Batch 4.5 (NEW): the four §9.51 directives — 0/4, all research-first;
  4.5.1/#48 is the active lane.** Plus 4.5.0, the sequencing decision.
- P5 0/5 (5.2 proposed DELETE, 5.3 REWORK pending owner) · P6 0/5 (6.1/6.2
  REWORK pending) · P7 0/4.

### 4. Simulator vs real life (§9.48 — pre-calibration diagnostics of the SUPERSEDED family; no run of the current family exists)

car 63.95 vs 59.0 · ride 31.05 vs 20.6 · walk-only 0.71 vs 13.4 · pt 0.36
vs 3.8 · other 3.92 vs 3.2 (MAE 6.45 pp); occupancy 0.4855 vs 0.3503
(OUTSIDE range, flattering); car length 10.40 vs 10.20 km (in range);
ride:car 0.862 vs 0.961; bike/pt/walk lengths out of range (1.74× / 0.50× /
3.47×); counts unusable (−91%, #20 conversion unwired); pairing 1.30%
declared-regime vs 15.31% OD-coincident. Full table:
`results/bind1000_25pct/_fit.json`.

### 5. Issue ledger — 35 filed, 26 closed, 9 open

| # | tracks | state |
|---|---|---|
| **#48** | physical ride directive | **THE ACTIVE LANE — research first** |
| #49 | modes individualised directive | queued; G62 anchor verified |
| #50 | demographic fidelity directive | queued; inventory first |
| #30 | sub-1 km walk mass | **re-opened** under its own REOPEN IF (2.5% vs >~10%) |
| #14 | calibrated base | decision done (§9.50); awaits an approved base arm + sequencing (4.5.0) |
| #9 | asc_car_passenger | resolved by decision (§9.50); closes when C5 exists |
| #28 | ride residual | measurement ledger for the teleport→physical transition |
| #31 | ride constraint family | realisation-gap ledger; mechanism moved to #48 |
| #24 | freight | done (§9.49); closes when PR #46 merges |

### 6. PR history, and the next PR

#1 P1 data · #2 P2 networks · #3 P3 demand · #4 P4 stage 0 · #38 spec audit
+ rebuild · #40 ride pairing · #41 board · #42 handover + deletion proposals
· #43 escort binding + age structure · #44 §9.48 evaluation · #45 /handoff +
/onboard tooling · **#46 (open) P4 freight** · **#47 (open, stacked) P4
calibration decision** · the handover PR (this one) · #39 closed unmerged.
**The next substantive PR**: whatever #48's research concludes, as
`P4 (4.5.1/#48): …` — after the owner rules on the mechanism and on
sequencing (4.5.0).

---

### Bootstrap reading, in this order

```
cities/newcastle/docs/STATUS.md                the board + numbered plan (batch 4.5 is the lane)
cities/newcastle/docs/DECISIONS.md §9.49–§9.51 freight, the §8.5 branch, the four directives
issues #48 #49 #50 #30                         the directive lanes, each with its evidence base
cities/newcastle/docs/DECISIONS.md §9.44–§9.48 the ride mechanism #48 must supersede
.claude/CLAUDE.md                              conventions + hard constraints
```
