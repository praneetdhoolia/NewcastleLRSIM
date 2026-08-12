# Next-session prompt

Paste the block below verbatim to start the next session. It is written to
orient an agent in one message and to **point at the authoritative documents
rather than duplicate them** — those documents are kept current; a copy inside a
prompt goes stale the moment anything moves.

Keep it in step with [`../STATUS.md`](../STATUS.md) and
[`P4_CHECKPOINT.md`](P4_CHECKPOINT.md) whenever the state changes.

---

Project Wickham — P4 calibration. Branch `praneetdhoolia/external-cordon-and-escort`
(on top of `praneetdhoolia/config-registry`). 22 commits ahead of main, NONE PUSHED.
**Nothing in this repo is a result.**

═══════════════════════════════════════════════════════════════════════════════
STANDING INSTRUCTIONS FROM THE USER — these override convenience
═══════════════════════════════════════════════════════════════════════════════
1. NO UNUSED OR FUTURE STUFF. Focus on the current stage, step by step. DELETE
   unused things immediately rather than leaving them "for later".
2. NO UNTRACKED OR HARD-CODED VALUES ANYWHERE. Every controllable value passes
   through config/registry/. 171 fields. The check suite tests this and HAS
   caught a hard-coded constant in new code — do not argue with it, fix it.
3. EVERY PIECE OF CODE IS TRACKED, DOCUMENTED AND ACTIVELY INVOLVED. A file
   nothing references, a docstring that lies, or a `consumers` entry naming a
   reader that does not read — all are defects. A DECLARED, SWEPT PARAMETER
   THAT REACHES NOTHING IS THE SAME DEFECT, and it has now bitten three times
   (issues #21, #12, and a whole sweep axis worth 112 wasted grid points).
4. Do not change things speculatively. Monitor what runs; when you find factors
   that might matter, LOG them rather than acting on them. REPRODUCE A DEFECT
   BEFORE ATTRIBUTING IT — this was got wrong once already.
5. Inventory first, state what you find, propose, WAIT FOR SIGN-OFF, then
   implement. If the user grants standing autonomy for a phase, act decisively
   and report; do not re-ask.
6. RUN THE GATE BEFORE THE RUN, NOT AFTER. Rebuilding inputs and launching a
   2-hour run without re-running check_package.py and diffing the resolved
   configs happened once. It passed on inspection afterwards. That was luck.
7. CLOSE ISSUES AS YOU GO, and label what blocks each one. Never close one
   because the list looks long: the bar is STRUCTURALLY PREVENTED, NOT
   REMEMBERED.

═══════════════════════════════════════════════════════════════════════════════
BOOTSTRAP — cheap, in this order
═══════════════════════════════════════════════════════════════════════════════
  STATUS.md                  VERIFIED phase board, THE NINE P4 DELIVERABLES, the
                             CARRIED-OVER work from P0–P2, and what was DECLINED.
                             Start here — it is the source of truth for all four.
  docs/P4_CHECKPOINT.md      long-form handoff: what is measured and true, the
                             traps, the errors already made, how to drive it
  DECISIONS.md §0, §8.5, §9.7–§9.22, §12.1, §13, §15, §16
  CLAUDE.md
  docs/CONFIG_REFERENCE.md   generated; skim "no value" and "held fixed"
  gh issue list --state open

  python tests/check_manifest.py                    fast, committed subset
  python src/setup/bootstrap_toolchain.py --verify  JDK/pt2matsim/SUMO digests
  python tests/check_package.py                     ~960 checks, 1 standing warn

The standing warning is lastIteration = issue #5. It is SUPPOSED to be there.
DO NOT RE-READ THE P1–P3 PACKAGE. 364 files hashed in data/MANIFEST.csv.

MACHINE: 24 logical cores, 63.5 GiB. One run averages 2.4 BUSY CORES OF 24 — the
mobsim synchronises every simulated second, so threads idle. Memory
(9.6 + 87 GiB × fraction) binds long before cores. PARALLELISE ACROSS RUNS, never
threads within one: thread count is part of the run identity. At 25% a run needs
31.5 GiB, so TWO fit at once. NO GPU PATH exists; do not re-investigate.

═══════════════════════════════════════════════════════════════════════════════
THE BOARD — 12 open issues, and NONE of them awaits a decision
═══════════════════════════════════════════════════════════════════════════════
Every open issue is labelled with what blocks it. All decisions have been taken.

  awaiting-implementation (9)   work that is scoped, decided and not yet built
    #26  URGENT  GTFS-Realtime collection — accrues ONLY FORWARD
    #22  0a      specification audit
    #23  0b      derive what can be derived
    #18  0c      apply the published bus/rail/ferry capacities
    #20  0d(1)   boundary through traffic, so the M1 carries cars
    #24  0d(2,3) work-related business travel + freight
    #25  8       the transfer-penalty estimate §7.2 specified
    #27  P2      corridor kerbside/width/capacity are imputed; B3 rests on them
    #14  5       calibrated base — also gated by deliverable 0

  awaiting-run (3)              decision taken, a run must produce the number
    #16  the §9.17 ride-cost departure, logged with its falsification conditions
    #5   the iteration count — the model does not converge
    #9   re-solve asc_car_passenger, downstream of #5

═══════════════════════════════════════════════════════════════════════════════
YOUR TASK, IN THIS ORDER
═══════════════════════════════════════════════════════════════════════════════
0.  START #26 TODAY, BEFORE ANYTHING ELSE. It is a poller and a store, an hour
    of work, and it is the ONLY item on the board where waiting destroys the
    option. §9.21 established SCATS phasing is REFUSED BY POLICY, which makes
    proposal §7.2's contingency the operative path — and §7.2 requires signal
    delay to be inferred from GTFS-REALTIME RUN-TIME DISTRIBUTIONS. Nobody is
    collecting them. A stream not captured today does not exist tomorrow, and
    the loss is silent. Collect only; the inference is separate work that gets
    better the longer this has been running.

1.  #22 — 0a SPECIFICATION AUDIT. First of the modelling work, because it may
    change what the rest is worth. Walk population → activities → tours → mode
    choice → network → scoring → metrics → fit, and at each joint ask: what
    would be wrong if this were wrong, and WOULD WE SEE IT? Output a ranked
    register of where the logic can be silently wrong.
    WHY FIRST: car is 32.5% against an observed 59.0% and car passenger 50.0%
    against 20.6%. The §9.15 demand repair moved car 1.69 pp. Something
    structural is still wrong. Seven defects have been found this way and EVERY
    ONE produced a confident wrong answer rather than an obvious failure.

2.  #23 — 0b DERIVE WHAT CAN BE DERIVED. Target 15–25 of the 78 `assumed`
    fields, NOT 78: the HTS held is AGGREGATE tables, so tour structure is not
    derivable without a TfNSW unit-record request. Candidates are listed in
    STATUS.md. CHECK FIRST: RUN.routing.beeline_distance_factor (1.3, assumed)
    is probably the SAME QUANTITY as B.activity.detour_factor (1.3376,
    measured) declared twice. Also fold in the ABS journey-to-work table
    (obtainable, settles B.external.interaction_rate) and the day-of-week split
    from RMS hourly counts, which carry dates.

3.  #18 — 0c FLEET, and #27 — corridor attributes. NEITHER TOUCHES DEMAND, so
    both can run in parallel with 1 and 2. Figures and their source grade are in
    §9.21; they enter as `literature` WITH URLS and SWEPT, never `observed`.

4.  #20, #24 — 0d THE MISSING DEMAND. Through traffic first, then business
    travel, then freight. All three MOVE MODE SHARE, which is why they precede
    any calibration.

5.  RE-BASELINE. One run, declared pipeline, on the rebuilt demand.

6.  #16 — the ride-cost measurement, against its pre-recorded falsification
    conditions. THEN #5 (iteration count), THEN #9, THEN #14.

7.  #25 — deliverable 8, the transfer-penalty estimate. Independent of the
    above; slot it wherever it fits.

FINALLY, SIMULATE. Declared pipeline, no exceptions:
  run_matsim.py → extract_metrics.py → fit.py → report.py
producing schema-validated _metrics.json and _fit.json. run_matsim.py prints a
live-view url as it launches; src/analyse/run_monitor.py --run <tag> serves an
in-flight or finished run on its own.

═══════════════════════════════════════════════════════════════════════════════
DECISIONS ALREADY TAKEN — do not re-litigate (DECISIONS.md §9.22)
═══════════════════════════════════════════════════════════════════════════════
• THE §8.5 QUESTION IS DEFERRED until after 0a, deliberately. The fit is wrong in
  a way nobody has explained; if 0a finds an eighth defect the fit may move
  without touching a constant. Choosing to re-open §8.5 to fix what turns out to
  be a bug would be the exact failure proposal §9 names as the PRIMARY THREAT TO
  VALIDITY, and it is unrecoverable: once a constant has absorbed a
  specification error, no later run can tell you it did.
• THE RUN PROGRAMME IS CUT. The sweep grid went 140 → 28 because
  walk_decay_beta_per_m REACHES NOTHING and 112 points could not have differed
  from another point. Approved scope cuts take 5,100 run-days → 262, i.e. ~765
  days of wall clock → ~43, or ~3 weeks with two runs concurrent.
  E.replication.n_replications STAYS AT 30 in the registry: the planning figure
  of 5 must come from MEASURED SEED VARIANCE, and pinning 5 now would replace an
  unjustified 30 with an unjustified 5.
• SCATS IS REFUSED BY POLICY and it is citable (§9.21). §7.2's contingency is
  the operative path and BINDS EVERY CORRIDOR HEADLINE to an explicitly stated
  uncertainty band.

═══════════════════════════════════════════════════════════════════════════════
DECLINED — do not re-raise (STATUS.md, and §9.22)
═══════════════════════════════════════════════════════════════════════════════
• THE 143 HELD-BACK TARGETS STAY UNTOUCHED. They are the only test the model
  has. The 67/143 split was fixed before any fitting precisely so no target can
  move after a result is seen. They open ONCE, at the end. A new observable
  becomes a CONSTRAINT (the §9.8 / §9.13 pattern), never a target.
• THE 13 OPAL CARD-TYPE TARGETS ARE NOT DELETED. Calibration rows in the
  pre-registered 210; deleting them retrospectively changes a set fixed in
  advance, which is the move that would let anyone drop whatever the model fails
  at. They are reported with the reason they cannot be scored.
• NO SEPARATE TAXI / MOTORCYCLE / RIDESHARE MODES. The HTS reports "Other" as
  one bucket and no decomposition exists. Three unfalsifiable modes would be
  structure pretending to be rigour.

═══════════════════════════════════════════════════════════════════════════════
HARD CONSTRAINTS
═══════════════════════════════════════════════════════════════════════════════
1. The 67/143 split is PRE-REGISTERED. Never calibrate on, re-split or peek at a
   holdout row. If you need one to diagnose something: SAY SO AND STOP. Note
   that the obvious data for deliverable 8 IS holdout — use the aggregate
   stop-level series and validate against the PUBLISHED interchange percentages,
   exactly as §7.2 words it.
2. ONE BUILD OF THE NETWORK PER COMPARISON (§3.5). A scenario runs on its own
   schedules/<S>/network.xml.gz + the E1 patch by osm:way:id. NEVER RE-RUN THE
   MAPPER.
3. Mode-share target is HTS NEWCASTLE LGA (59.0/20.6/13.4/3.8/3.2). Comparing a
   five-LGA modelled mean to a Newcastle-LGA published one is the error §9.13
   records being made — it once inverted a headline. The same trap applies to
   §2.5's "87.5% observed", which is about the 40 TRUNK edges and NOT the 714
   corridor edges (§9.22).
4. The three unobtained inputs stay SWEPT, never pinned.
   B.external.interaction_rate too, until the ABS table lands.
5. Everything seeded 20260810. normalise_eol.py BEFORE build_manifest.py, then
   again after.
6. NO INVENTED DATA — derive it from the package or SWEEP it. Never type an
   observed value into a script; read it from its artefact. DO NOT TRUST A
   SEARCH SUMMARY: one asserted a charging-dwell figure the cited page does not
   contain.
7. NO COUNT-BASED CALIBRATION until #20 lands (§9.14). calibrate.py ENFORCES
   this. When building #20, note that seeding demand from counts and then
   scoring against those same counts is CIRCULAR — seed from the cordon
   stations, score elsewhere.
8. BASH HEREDOCS MANGLE BACKTICKS. Write prose to a file and splice with Python.
   This has bitten three times.

═══════════════════════════════════════════════════════════════════════════════
OUT OF P4 SCOPE — do not start these
═══════════════════════════════════════════════════════════════════════════════
• RUNNING SUMO. Deliverable 7 is the TOLERANCE, a number. The SUMO harness and
  the outer loop are P5. The corridor has been built six times and simulated
  ZERO times, deliberately: coupling it to a demand model whose mode share is
  wrong would propagate the error into run time, car delay and B3 — the decisive
  test of Claim B. #27 must land BEFORE the first corridor run. SUMO pedestrian
  crossings need a SUMO version change = a §14 toolchain change = a model change.
• socnetsim joint plans — absent from the pinned jar; a §14 toolchain change.
• P5 scenario runs, P6 analysis, and a 2013 historical reconstruction
  (considered and dropped — do not reopen without the user).
• The 🟡 carried-over items in STATUS.md (pedestrian counts, retail vacancy, the
  2014 timetable) block P6, NOT P4. Do not let them reorder deliverable 0.

STYLE: inventory first, state findings, propose, wait for sign-off, then
implement. Keep STATUS.md current in the SAME commit as the work. Commit
messages state what changed in the MODEL or the DATA, not which script ran.
Branch <git-handle>/<short-kebab-description>, never claude/*. No Claude
attribution and no session link in commits or PRs.
