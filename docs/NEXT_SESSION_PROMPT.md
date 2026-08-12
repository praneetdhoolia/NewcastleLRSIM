# Next-session prompt

Paste the block below verbatim to start the next session. It is written to be
self-contained enough to orient without reading everything, and to point at the
authoritative documents rather than duplicate them — those documents are kept
current; a copy inside a prompt is not.

---

Project Wickham — P4 calibration. Branch `praneetdhoolia/external-cordon-and-escort`
(on top of `praneetdhoolia/config-registry`). 14 commits, NONE PUSHED.
Nothing in this repo is a result.

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
   THAT REACHES NOTHING IS THE SAME DEFECT.
4. Do not change things speculatively. Monitor what runs; when you find factors
   that might matter, LOG them rather than acting on them. REPRODUCE A DEFECT
   BEFORE ATTRIBUTING IT — this was got wrong once already.
5. Inventory first, state what you find, propose, WAIT FOR SIGN-OFF, then
   implement. If the user grants standing autonomy for a phase, act decisively
   and report; do not re-ask.
6. RUN THE GATE BEFORE THE RUN, NOT AFTER. Rebuilding inputs and launching a
   2-hour run without re-running check_package.py and diffing the resolved
   configs happened once. It passed on inspection afterwards. That was luck.

═══════════════════════════════════════════════════════════════════════════════
BOOTSTRAP — cheap, in this order
═══════════════════════════════════════════════════════════════════════════════
  STATUS.md                  VERIFIED phase board + THE NINE DELIVERABLES.
                             Start here. Every phase state in it was checked
                             against the package on 12 Aug, not carried forward.
  docs/P4_CHECKPOINT.md      the long-form handoff: what is measured and true,
                             the traps, the errors already made, how to drive it
  DECISIONS.md §0, §8.5, §9.7–§9.21, §12.1, §15, §16
  CLAUDE.md
  docs/CONFIG_REFERENCE.md   generated; skim "no value" and "held fixed"
  gh issue list --state open       11 open, and they ARE the worklist.
                             Deliverable 0 is #22 #23 #24 (+ #18 #20);
                             deliverable 8 is #25; deliverable 5 is #14.

  python tests/check_manifest.py                    fast, committed subset
  python src/setup/bootstrap_toolchain.py --verify  JDK/pt2matsim/SUMO digests
  python tests/check_package.py                     ~960 checks, 1 standing warn

The standing warning is lastIteration = issue #5. It is SUPPOSED to be there.
DO NOT RE-READ THE P1–P3 PACKAGE. 364 files hashed in data/MANIFEST.csv.

MACHINE: 24 logical cores, 63.5 GiB. One run averages 2.4 BUSY CORES OF 24 — the
mobsim synchronises every simulated second, so threads idle. Memory
(9.6 + 87 GiB × fraction) binds long before cores. PARALLELISE ACROSS RUNS, never
threads within one: thread count is part of the run identity. NO GPU PATH exists;
do not re-investigate.

═══════════════════════════════════════════════════════════════════════════════
YOUR TASK: DELIVERABLE 0, THEN RE-BASELINE, THEN RUN
═══════════════════════════════════════════════════════════════════════════════
P4 has NINE deliverables and SIX are met. The full checklist with the reasoning
is in STATUS.md — read it there, it is the source of truth. In short:

  0  Specification and input completeness   NOT STARTED  ← YOUR WORK, AND IT
                                                          GATES DELIVERABLE 5
  1  Run harness                            done
  2  Metric extraction                      done
  3  Fit statistic                          done, 10 tests
  4  Calibration loop                       done
  5  Calibrated base + provenance           NOT MET (decision + deliverable 0)
  6  Calibration report                     done
  7  Outer-loop tolerance                   done: 5 s
  8  Transfer-penalty estimate              NOT STARTED — proposal §7.2's OWN
                                            fallback, which was never built
  9  Live run view                          done

DO THEM IN THIS ORDER. 0c and 0e touch no demand and may run in parallel.

  0a  SPECIFICATION AUDIT — first, and it may change what the rest is worth.
      Walk population → activities → tours → mode choice → network → scoring →
      metrics → fit. At each joint ask: what would be wrong if this were wrong,
      and WOULD WE SEE IT? Output a ranked register of where the logic can be
      silently wrong. WHY FIRST: mode share is car 32.5% against an observed
      59.0% and car passenger 50.0% against 20.6%. Something structural is still
      wrong, and adding demand on top of an unexplained error makes it harder to
      find. Seven defects have already been found this way and every one
      produced a confident wrong answer rather than an obvious failure.

  0b  DERIVE WHAT CAN BE DERIVED. Move as many of the 78 `assumed` fields to
      measured/derived as the data supports, and reclassify the ones that are
      methodological choices rather than empirical guesses. REALISTIC TARGET
      15–25, NOT 78: the HTS held is AGGREGATE tables, so tour structure
      (intermediate stops, activity durations, second stops) is NOT derivable
      without a TfNSW unit-record request. Named candidates are in STATUS.md.
      Two specifics worth doing early: B.external.interaction_rate is settled by
      the ABS journey-to-work SA2×SA2 table, which §13 says is a standard
      TableBuilder extract and NOT a formal request; and
      RUN.routing.beeline_distance_factor is PROBABLY A DUPLICATE of the
      measured detour factor 1.3376 — check before deriving anything else.

  0c  FLEET CAPACITIES. Apply the §9.21 figures: ferry 149 seated + 51 standing,
      rail from the Hunter/Endeavour car figures, bus 44 seated + 18 standing.
      Enter them as `literature` WITH THEIR URLS and SWEPT — not `observed`,
      which is reserved for a value this package downloaded itself. Light rail
      is already done (270 published, §9.18). EVERY CURRENT CAPACITY OVERSTATES
      THE REAL VEHICLE, rail by ~2.7× on a two-car set.

  0d  THE MISSING DEMAND, in value order:
      (1) boundary/through traffic — the M1 gap (#20). External-station matrix
          seeded from cordon counts. All five Pacific Motorway stations are
          CALIBRATION rows, so this touches NO HOLDOUT.
      (2) work-related business travel — an OBSERVED HTS purpose the model does
          not generate.
      (3) freight — a heavy-vehicle layer from the measured 6.52% heavy share.
      DEFERRED TO P5: SUMO pedestrian crossings, which need a SUMO version
      change and are therefore a §14 toolchain change = a model change.

  0e  HOUSEKEEPING. Keep the `water` and `green` OSM layers, documented as
      VISUAL-ONLY so they never read as orphaned model inputs.

  8   TRANSFER-PENALTY ESTIMATE. Proposal §7.2 specifies exactly what to do when
      journey-linked Opal is refused: estimate transfer rates from tap-on/tap-off
      timing at the Interchange using aggregate stop-level data plus a matching
      model, and validate against the published interchange percentages. The
      package holds lr_tapon_share_by_stop and the station entry/exit series.
      CAREFUL: lr_tapon_share_by_stop is HOLDOUT. Validate against the published
      percentages, NOT against those rows.

THEN: rebuild the demand, re-baseline with one run, and only then calibrate.
Every part of 0d moves mode share, so a base calibrated before it must be
calibrated again after it.

FINALLY, SIMULATE. Declared pipeline, no exceptions:
  run_matsim.py → extract_metrics.py → fit.py → report.py
producing schema-validated _metrics.json and _fit.json. The run prints a live
view url as it launches; src/analyse/run_monitor.py --run <tag> serves a
finished or in-flight run on its own.

═══════════════════════════════════════════════════════════════════════════════
DECLINED — recorded so they are not re-raised
═══════════════════════════════════════════════════════════════════════════════
• THE 143 HELD-BACK TARGETS STAY UNTOUCHED. They are the only test the model
  has. The 67/143 split was fixed before any fitting precisely so that nobody
  can move a target after seeing a result. They open ONCE, at the end. A new
  observable becomes a CONSTRAINT (the §9.8 / §9.13 pattern), never a target.
• THE 13 OPAL CARD-TYPE TARGETS ARE NOT DELETED. They are calibration rows in
  the pre-registered 210; deleting them retrospectively changes a set fixed in
  advance, which is the move that would let anyone drop whatever the model fails
  at. They are reported with the reason they cannot be scored.
• NO SEPARATE TAXI / MOTORCYCLE / RIDESHARE MODES. The HTS reports "Other" as
  one bucket and no decomposition exists. Three unfalsifiable modes would be
  structure pretending to be rigour.
• SCATS PHASING IS REFUSED BY POLICY and that is documented and citable (§9.21).
  Proposal §7.2's contingency is now the OPERATIVE PATH and it binds every
  corridor headline to an explicitly stated uncertainty band.

═══════════════════════════════════════════════════════════════════════════════
HARD CONSTRAINTS
═══════════════════════════════════════════════════════════════════════════════
1. The 67/143 split is PRE-REGISTERED. Never calibrate on, re-split or peek at a
   holdout row. If you need one to diagnose something: SAY SO AND STOP.
2. ONE BUILD OF THE NETWORK PER COMPARISON (§3.5). A scenario runs on its own
   schedules/<S>/network.xml.gz + the E1 patch by osm:way:id. NEVER RE-RUN THE
   MAPPER.
3. Mode-share target is HTS NEWCASTLE LGA (59.0/20.6/13.4/3.8/3.2). Comparing a
   five-LGA modelled mean to a Newcastle-LGA published one is the error §9.13
   records being made — it once inverted a headline.
4. The three unobtained inputs stay SWEPT, never pinned. B.external.interaction_rate
   too, until the ABS table lands.
5. Everything seeded 20260810. normalise_eol.py BEFORE build_manifest.py, then
   again after.
6. NO INVENTED DATA — derive it from the package or SWEEP it. Never type an
   observed value into a script; read it from its artefact. And DO NOT TRUST A
   SEARCH SUMMARY: one asserted a charging-dwell figure the cited page does not
   contain.
7. NO COUNT-BASED CALIBRATION until the M1 gap is resolved (§9.14).
   calibrate.py ENFORCES this.
8. BASH HEREDOCS MANGLE BACKTICKS. Write prose to a file and splice with Python.
   This has bitten three times.

═══════════════════════════════════════════════════════════════════════════════
OUT OF P4 SCOPE — do not start these
═══════════════════════════════════════════════════════════════════════════════
• RUNNING SUMO. Deliverable 7 is the TOLERANCE, a number. The SUMO harness and
  the outer loop are P5. The corridor has been built six times and simulated
  ZERO times, deliberately: coupling it to a demand model whose mode share is
  wrong would propagate the error into run time, car delay and B3 — the decisive
  test of Claim B. SUMO pedestrian crossings belong here too.
• socnetsim joint plans — absent from the pinned jar; a §14 toolchain change.
• P5 scenario runs, P6 analysis, and a 2013 historical reconstruction
  (considered and dropped — do not reopen without the user).

STYLE: inventory first, state findings, propose, wait for sign-off, then
implement. Keep STATUS.md current in the SAME commit as the work. Commit
messages state what changed in the MODEL or the DATA, not which script ran.
Branch <git-handle>/<short-kebab-description>, never claude/*. No Claude
attribution and no session link in commits or PRs.
