# Brief for the next agent

*Written 14 August 2026 at HEAD `a66388d`. This is a HANDOVER, not a source of
truth: where it disagrees with [`STATUS.md`](../../STATUS.md),
[`DECISIONS.md`](../../DECISIONS.md) or [`CLAUDE.md`](../../CLAUDE.md), those
win. Paste it whole to start a session cold.*

---

═══════════════════════════════════════════════════════════════════════════════
WHAT THIS PROJECT IS — read once, hold it behind every decision
═══════════════════════════════════════════════════════════════════════════════
A counterfactual microsimulation of the **Newcastle (NSW) light rail**: what did
the line do to journey cost, accessibility, mode share and city-centre footfall,
against the alternatives available in 2013. MATSim for the region, SUMO for the
corridor.

It exists because that estimate was never produced and the business case is not
inspectable. Every discipline below — the sealed holdout, the declared sweeps,
the refusal to report a point value for an unobserved input — descends from one
fact: **9 of 10 rail projects overestimate patronage, by an average of 106%**
(Flyvbjerg, 210 projects). A model of a rail project that produces a flattering
answer is the EXPECTED outcome, not a surprising one.

**The city is Newcastle — five LGAs, 4,086 km², 1,500 core SA1s, 612,680 agents.
Wickham is ONE SUBURB of it.** The name is legitimate in exactly three places:
the suburb's own zones/stops, Newcastle Interchange **at** Wickham (what the
transfer penalty prices), and S1 the bus-shuttle scenario. Two stale codename
identifiers survive in code — the `WICKHAM_*` env prefix and `src/java/wickham/`
— tracked as **#36**. Do not add more.

═══════════════════════════════════════════════════════════════════════════════
BOOTSTRAP — in this order
═══════════════════════════════════════════════════════════════════════════════
  STATUS.md                    the board: phases P0–P7, deliverables, next action
  DECISIONS.md                 START AT ITS "How to find something" INDEX.
                               4,400 lines, sections NOT in file order (§15
                               precedes §14), and §9 holds unrelated topics.
                               Then §0, §8.5, §9.12, §9.27, §9.36, §15.
  CLAUDE.md                    conventions + hard constraints
  docs/README.md               index; 4 of 8 documents are GENERATED
  docs/audit/SPEC_AUDIT.md     where the logic can be silently wrong
  gh issue list --state open   13 open

  python tests/check_manifest.py                    fast, committed subset
  python src/setup/bootstrap_toolchain.py --verify  digests + COMPILES THE JAVA
  python tests/check_package.py                     ⛔ CANNOT PASS RIGHT NOW

DO NOT RE-READ THE P1–P3 PACKAGE. 376 files hashed in data/MANIFEST.csv.

═══════════════════════════════════════════════════════════════════════════════
⛔ EXACT STATE — 14 August 2026
═══════════════════════════════════════════════════════════════════════════════
  branch praneetdhoolia/mode-choice-specification, clean, 50 commits ahead of main
  HEAD a66388d

  networks/osm/            EMPTY. The #32 re-harvest was started, produced four
                           corrupt layers, was deleted, and NEVER RE-RUN.
  networks/osm_pre_issue32/ 10 layers, 179 MB — THE ONLY COPY. DO NOT DELETE.
  data/MANIFEST.csv        376 files (was 386: the 10 OSM layers left the
                           manifest because they do not exist)
  registry                 210 fields — 89 assumed, 51 definition, 28 literature,
                           21 measured, 17 derived, 4 observed; 7 carry NO VALUE
  run inputs               30 scenario × day-type sets, all with `telemetry`
  results/                 8 dirs, ~15 GB, every one superseded
  NOTHING IN THIS REPO IS A RESULT.

**check_package.py cannot pass until the harvest is re-run.** That is not a bug
to fix; it is the state.

═══════════════════════════════════════════════════════════════════════════════
★ THE TRAP THAT KEEPS WINNING — EIGHT INSTANCES
═══════════════════════════════════════════════════════════════════════════════
**A DECLARED VALUE THAT REACHES NOTHING, OR A DEFAULT THAT IS RIGHT BY ACCIDENT.**
  • Parking price declared since P1, read by NO script — a car parked free in a
    study about city-centre access.
  • params/C1 was a hand-kept mirror of the registry: 26 values, including every
    mode constant and THE transfer penalty, reached nothing. Setting one through
    the resolver left the output BYTE-IDENTICAL.
  • Gradient penalties and PT walk-access decay reach the model through nothing.
  • The summariser read a registry key that DOES NOT EXIST and fell back to a
    hard-coded 0.8 — the shipped value, so it was right for the wrong reason.
`consumers` in the registry is a claim, NOT proof. **Establish reach by CHANGING
A VALUE AND WATCHING THE OUTPUT.** That is how the home-parking exemption was
caught failing on 267 of 641 charges.

**AND: THE AVAILABLE NUMBER LOOKS LIKE THE ANSWER AND IS A DIFFERENT QUANTITY.**
  • `fee=yes` on 472 parking facilities → 452 are ONE university campus.
  • Published interchange TIME ≠ transfer PENALTY (MATSim already simulates the
    walk and wait; the penalty sits ON TOP of a measured 112 s walk).
  • OSM `width` on a road = CARRIAGEWAY (6.5 m), not a lane (3.5 m).
  • 4,861 parking "capacities" — 4,623 are `1`, because they are BAYS.
  • A merged OSM way keeping its id but losing its `<nd>` children: well formed,
    plausible, geometrically empty.
  • build_basemap dropped every segment >327 m, so the LGA boundary shattered and
    the map rendered as ocean — while looking like a perfectly normal dark map.

**NONE of these was caught by reading code. All were caught by ARITHMETIC** — a
ratio that could not be true, or a value that did not move when it should have.

═══════════════════════════════════════════════════════════════════════════════
READ FIRST — WHAT INVALIDATES RESULTS
═══════════════════════════════════════════════════════════════════════════════
**NO RUN AT 250 ITERATIONS MEANS ANYTHING.** Measured 100→250 moves a mode 13.2
points; 250→500 6.8; 500→800 3.0; flat only from ~900. §9.27 measured ~1000 on
the PRE-#28 model. Re-confirmed 14 Aug on the CURRENT controler: a 250-iteration
10% run still moved **car +3.21 pp** after innovation was disabled at 200.
`RUN.controler.last_iteration` STAYS `unobtained`. **Re-measure AFTER the demand
batch, not before** — the batch moves the landscape.

**1% IS NOT A CHEAP SUBSTITUTE FOR 10%.** MATSim floors link storage at one
vehicle, so 1% produces spurious spillback that inflates car delay while
teleported modes are immune. Measured: car stuck 1,079 at 1% vs **1** at 10%.
**CROSS-FRACTION COMPARISON IS INVALID.**

**MODE-SHARE TARGET IS HTS NEWCASTLE LGA** (59.0 / 20.6 / 13.4 / 3.8 / 3.2).
Use `newcastle_lga_pct`, NEVER `all_residents_pct` — it has inverted a headline.

**THE 67/143 SPLIT IS PRE-REGISTERED.** Never calibrate on, re-split, or peek at
a holdout row. `fit.py` enforces it. If you need one to diagnose: SAY SO AND STOP.

**ONE BUILD OF THE NETWORK PER COMPARISON** (§3.5). ~18% of route link sequences
differ between identical pt2matsim builds.

**modestats.csv ≠ _metrics.json.** One is the mode agents CHOSE, the other trips
that COMPLETED. Never report from modestats.

═══════════════════════════════════════════════════════════════════════════════
MACHINE
═══════════════════════════════════════════════════════════════════════════════
24 cores, 63.5 GiB, ~1.2 TB free. A run averages **2.4 busy cores of 24** — the
mobsim synchronises every simulated second. **MEMORY BINDS:** 9.8 GiB at 1%, 18.4
at 10%, 31.5 at 25%. TWO 10% runs fit at once, not three. **PARALLELISE ACROSS
RUNS, NEVER THREADS WITHIN ONE.** No GPU path.
Measured 14 Aug: 250 iterations at 10% = **2 h 43 m**, median iteration 31.8 s.
A 1000-iteration 10% run is ~11.6 h. **PRUNE AFTER EVERY RUN** or the sweep needs
~750 GB. An UNTAGGED re-run DELETES the old directory — always `--tag`.

═══════════════════════════════════════════════════════════════════════════════
WHAT LANDED IN THE LAST TWO SESSIONS — 4 commits, cb02e90..a66388d
═══════════════════════════════════════════════════════════════════════════════
**Repository cleanup.** STATUS.md was 79% dated narrative (944 lines) and is now
a 340-line board; the narrative is archived in docs/handover/SESSION_LOG.md.
Four of its figures were stale and one self-contradictory. **A correction
recorded in §2.6 had never propagated**: CLAUDE.md and README.md still labelled
EPSG:28356 as GDA2020 when §2.6 establishes it is **GDA94** — the one file that
overrides all others was stating the wrong datum. Documents filed under
docs/{design,reference,audit,handover}/. DECISIONS.md gained a topical index
(nothing renumbered — §9.x ids are referenced from code, issues and both other
documents). Project renamed off the suburb; two code identifiers tracked as #36.

**A run now reports itself, live** (§9.36). `src/java/wickham/RunTelemetry.java`
publishes per-mode counts, per-vehicle-type transit counts (Bus/Rail/Tram/Ferry —
this CANNOT come from mode choice, a passenger's leg mode is `pt` for all four),
per-link delay and volume, and stuck agents — **from inside the mobsim, in
simulated-time order**. `src/analyse/run_view.py` + `run_view.html` serve it on
loopback with a live congestion map. `summarise_run.py` closes out a finished run
with `SUMMARY.md` + `_summary.json`.

⚠ **`writeEventsInterval` WAS NEVER THE OBSTACLE.** MATSim's EventsManager fires
every event to every registered handler on EVERY iteration; the interval governs
only whether `EventWriterXML` — itself just another handler — is among them. The
package proves it: **26 event files against 251 leg histograms.** Do not "fix"
this by setting writeEventsInterval=1; that costs 16 MB/iteration at 1% and buys
nothing.

**Three defects, all found by arithmetic:**
  1. ⚠⚠ **THE OBSERVER KILLED A RUN.** On Windows a reader holding
     `telemetry_links.json` makes the writer's `Files.move` throw; the exception
     propagated out of the handler and **terminated a run at iteration 5 of 10**.
     Telemetry is now structurally unable to reach the mobsim (bounded retry →
     in-place write → give up and count). Verified at 1,987 concurrent reads,
     zero exceptions. **AN INSTRUMENT THAT CAN STOP THE EXPERIMENT IS NOT ONE.**
     Any future observer in this repo gets the same treatment.
  2. **build_basemap.pack() silently dropped every segment >327 m** (int16-cm
     delta overflow started a new run, but that run was degenerate and skipped).
     `read_coast` SIMPLIFIES the LGA boundary, and simplification is what
     manufactures long segments: coast packed to 180 fragments, 33 closed,
     largest 12.5 km against a 131 km boundary; landmass filled 1 of 40 sampled
     points. Fixed by densifying. ⚠ **`build_replay_page.py` decodes the same
     payload — EVERY REPLAY PAGE BUILT BEFORE 14 AUG HAS BROKEN AREA FILLS.**
  3. **A silent default that was right by accident** (see the trap above).

**Two findings recorded, not fixed:**
  • **#37 — 348 agents live a 30-hour day.** `qsim.endTime=30:00:00` is correct
    (hours 24–30 are the following morning, so a 23:30 departure can arrive), but
    348 agents have a trip at 02:00 AND at 26:00 in one modelled day. It is in
    the SEED (25,210 late departures at iteration 0, flat across 30 iterations),
    not in replanning. B2 draws departure hours 0–23 correctly; nothing caps a
    chain at the 24 h boundary. 0.66% of agents. **Fix inside the demand batch.**
  • **#5** re-confirmed on the current controler (above).

═══════════════════════════════════════════════════════════════════════════════
YOUR TASK — B0 IS THE POINT OF NO RETURN AND IT IS FIRST
═══════════════════════════════════════════════════════════════════════════════
**B0 — #32 RE-HARVEST + REBUILD.** `python src/extract/overpass.py` (10 layers ×
8 tiles; expect 504s and mirror rotation; RESUMES from cached tiles). Then, in
order: `build_network_layers` → `attach_gradient` → `attach_speed_zones` →
`build_corridor_road_attributes` → `build_matsim_network` (RE-RUNS pt2matsim) →
`build_landuse_parking` → `build_zone_attractions`.

✅ **VERIFY BEFORE BUILDING ON IT:**
  • every layer must be **LARGER** than its `networks/osm_pre_issue32/`
    counterpart — a layer that shrinks when its extent doubles cannot be right;
    that is exactly how the corrupt merge was caught;
  • `osm_tiles.verify()` must pass on each (refuses <90% of sampled ways carrying
    an `<nd>`);
  • the **87 core SA1s / 31,940 agents** must now be INSIDE the road network.
    Check explicitly — it is the whole point of #32.
  ⚠ A bigger network is more memory. Re-measure before assuming 10% still fits.

DERIVED EXTENTS (verify these print before trusting a harvest):
  STUDY      S,W,N,E = (-33.2553, 150.7418, -32.5209, 152.2606)   8 tiles
  BUILDINGS  S,W,N,E = (-32.9594, 151.7215, -32.8924, 151.8241)   1 tile

**THEN, IN THE SAME BATCH** — each regenerates B2, so separately rebuilds it
several times:
  #30 destination placement. ⚠ DIAGNOSE BEFORE FIXING. P3 stage 1 reports gravity
      distance matching HTS EXACTLY on all six purposes, yet education is 2.19×
      too long and B2 plans 10.80 km against 6.33 km realised for car.
      Destination choice is not in replanning so they should agree. NOBODY HAS
      CHASED THIS. Target: 4.9% of trips under 1 km → ~11.5%.
  #29 bike availability. 0.50, swept [0.35,0.60], drawn as a household bike count
      from NCPS, gated to 0 for the youngest band ON PHYSICAL GROUNDS ONLY.
      **NEVER age-grade from participation data** — that is the absorption trap.
      Austroads is COPYRIGHT: cite figures, do not redistribute.
  #24 + #20 SFM22 freight + boundary traffic. SA3 geography, 2026 is a column,
      XLSB DOUBLE-MISLABELLED as XLSX by both CKAN and the HTTP header. **ROW
      30001 IS AN UNLABELLED GRAND TOTAL** — drop it or everything doubles. COAL
      IS 89% RAIL: the port contributes ZERO trucks to Hunter Street. SFM22 road
      tonnage is a LOWER BOUND (26,156 kt vs ABS 9223.0's 53,926 kt on identical
      geography). Payload RSEs come free (SMVU Table 26); the commodity→vehicle
      crosswalk DOES NOT EXIST — assume and sweep.
  #37 the 30-hour day (above).
  #36 the WICKHAM_* / src/java/wickham/ rename — **free here**, because the batch
      already invalidates every run record and recompiles the Java.

**#31 ride constraint — A MODELLING DECISION, NOT A PATCH.** eqasim's
PassengerConstraint does what #31 describes: a TRIP-LEVEL biconditional on
getInitialMode(). No driver is consulted; eqasim has NO driver-passenger matching.
BUT adopting it **PINS THE RIDE SHARE TO THE B2 SEED** — ride becomes an input
wearing the costume of a result (§9.6). Whether that is defensible here is a
DECISION FOR THE LOG, and if taken, every result must state the car-passenger
share is exogenous.
  ⚠ **DO NOT ADD `ride` TO chainBasedModes.** ChooseRandomLegModeForSubtour
    implements chain-based modes as VEHICLE MASS CONSERVATION; applied to ride it
    forces a passenger leg to begin where the last one ended, meaningless for
    someone getting a lift. Berlin v6.4, Lausitz v2.0, Kelheim v3.1, Kyoto v1.0,
    LA v1.1 and SBB ALL list `ride` in modes and ALL keep chainBasedModes=car,bike.
  ⚠ **IF PORTING THE eqasim CLASS:** its mode is `car_passenger` and the string is
    HARD-CODED. Ours is `ride`. A copied constraint compiles, runs, constrains
    nothing and reports success — reach defect number nine.
  Option 3 (true matching) is socnetsim joint plans, ABSENT FROM THE PINNED JAR.

**GATE:** check_package, diff the resolved configs, regenerate all 30 sets.
**ONLY THEN:** #5 re-measure (~11.6 h), #28 residual (ride vs car IN MATCHED
DISTANCE BINS — aggregate means are confounded by trip-length composition; that
mistake produced a withdrawn headline once), #14 deliverable 5, #9, #34.

⚠ **P5 AS SPECIFIED IS ~765 DAYS OF WALL CLOCK.** Cutting it is a DEFENSIBILITY
decision to be argued and recorded, not a scheduling one.

═══════════════════════════════════════════════════════════════════════════════
HOUSEKEEPING — safe at any time
═══════════════════════════════════════════════════════════════════════════════
  • `results/live_demo` holds 9.8 GB of `output/ITERS`. `prune_run.py` reclaims it
    and will NOT touch the telemetry, but refuses until `extract_metrics.py` has
    run — by design.
  • Rebuild any replay page (basemap packing defect).
  • `check_package.py` lost its live-view coverage when run_monitor.py was
    deleted. Restore it against run_view.py / summarise_run.py.
  • `build_matsim_run_inputs.py` with `--scenarios` rewrites
    `_run_inputs_report.json` to cover ONLY what it touched. Run it whole, or fix
    that.

═══════════════════════════════════════════════════════════════════════════════
DECISIONS ALREADY TAKEN — do not re-litigate
═══════════════════════════════════════════════════════════════════════════════
• PRE-TRAM SIGNAL COUNT STAYS AT 14 (8 of the 14 were installed in 2018 for the
  light rail; recorded as an attribute only — re-deriving the counterfactual from
  it would reshape the B3 test).
• OWN REALTIME COLLECTION DROPPED (#26): TfNSW's historical GTFS-RT archive
  covers Metro and Ferry ONLY, verified against the live API.
• SCATS REFUSED BY POLICY and citable (independently corroborated, WalkSydney
  Sept 2025). Main Roads WA publishes phasing; Utah DOT open-sourced ATSPM on 88%
  of 2,085 signals. **That contrast IS the method note.**
• FREIGHT IS THE PROPER SFM22 PATH. Licence conflict: USER IS HANDLING IT.
• GRID 140 → 28. n_replications STAYS 30 until seed variance is MEASURED.
• PARKING MAX-STAY DOUBLES AS THE CHARGE CAP; it UNDER-charges a long stay.
• DELIVERABLE 5 TAKES §8.5's FIRST BRANCH: estimate ASCs on era 3 (2018) and HOLD
  FIXED. **LOG THE DEPARTURE BEFORE ANY RUN.**
• The parking ramp prices Kotara/Glendale/Charlestown at CBD rates where parking
  is free. The contiguity fix was BUILT AND REJECTED — it also excludes the
  University and John Hunter Hospital, which DO charge.
• #34 (the fifth rectangle) DELIBERATELY DEFERRED — it moves a pre-registered B1
  denominator. MEASURE THE DAMAGE FIRST.
• The 30 h qsim window is CORRECT and stays. Only the wrap (#37) is a defect.

═══════════════════════════════════════════════════════════════════════════════
DECLINED — do not re-raise
═══════════════════════════════════════════════════════════════════════════════
• The 143 held-back targets stay untouched. They open ONCE, at the end.
• The 13 Opal card-type targets are not deleted.
• No separate taxi / motorcycle / rideshare modes (no target exists).
• Weather is NOT modelled in mode choice — represent it as a wet-day sensitivity
  ARM on asc_cycle weighted by the BoM rain-day fraction.
• Reclassifying the SUMO booleans / corridor buffers to `definition` to lower the
  assumed count. REVIEWED AND DECLINED — they each change a result.

═══════════════════════════════════════════════════════════════════════════════
TRAPS (harness)
═══════════════════════════════════════════════════════════════════════════════
1. **BASH HEREDOCS MANGLE BACKSLASH ESCAPES.** `\n` inside a quoted heredoc
   becomes a literal newline and breaks JS/Python strings. It bit twice more this
   session. Write prose/code with the Write or Edit tool, not a heredoc.
   `io.open(p,'w')` TRUNCATES BEFORE THE WRITE FAILS — validate, then write.
2. `pkill` DOES NOT WORK RELIABLY HERE. Use PowerShell Get-CimInstance +
   Stop-Process, and VERIFY. Two harvests once ran concurrently into one dir.
3. **NORMALISE → MANIFEST**, and do it LAST. Regenerating artefacts after
   build_manifest ships stale hashes. It has happened.
4. NEVER compare across sample fractions. NEVER compare aggregate mean speeds
   across modes — bin by distance first.
5. NO COUNT-BASED CALIBRATION until #20 lands. calibrate.py enforces it.
6. Everything seeded **20260810**. Regenerate docs/reference/CONFIG_REFERENCE.md
   after ANY registry edit or check_package fails on staleness.
7. WebSearch/WebFetch are NOT sandboxed; bash curl IS. WebFetch cannot read PDFs
   but DOES save them — then pdftotext locally.
8. **DO NOT TRUST A SEARCH SUMMARY.** Verify against the live API or the file.
9. Branch `<git-handle>/<short-kebab>`, never `claude/*`. No Claude attribution
   and no session link in commits or PRs (enforced in four layers). Commit
   messages state what changed in the MODEL or the DATA. Keep STATUS.md current
   in the SAME commit.

═══════════════════════════════════════════════════════════════════════════════
DESK RESEARCH — use it, do not re-run it
═══════════════════════════════════════════════════════════════════════════════
• **NO published ex-post counterfactual microsimulation of a light rail line's
  effect on car traffic AND street activity exists in any city.** That is the gap.
• BENCHMARK (AToM Melbourne, MATSim, ALSO 10%): driving 74.8 vs 75.2, PT 21.5 vs
  19.3, walk 2.1 vs 3.7, cycle 1.6 vs 1.7; car counts <25% WAPE in peak. **ACTIVE
  MODES FIT WORST THERE TOO** — #29/#30 are the known hard part.
• VALIDATION TARGETS (UK TAG): screenlines <5% for 95%; GEH<5 for >85% of links;
  journey time within 15% for >85%; PT boardings <15% grouped / <25% individual,
  NOT applied below 150 pax/hr; ≥10 seeds, PUBLISHED, no cherry-picking. BUT the
  agent-based family (BEAM) reports NO R²/RMSE/GEH at all — it publishes
  operator-by-operator levels INCLUDING ITS MISSES (NJ Transit bus +53%).
  **REPORT BOTH DIALECTS.**
• TAG M3.2 requires an explicit BOARDINGS-vs-LINKED-TRIPS adjustment. Our targets
  are labelled boardings, sourced from Opal "trips", and DECISIONS is silent.
  CONFIRM BEFORE QUOTING EITHER. (Unverified — do not assume a defect.)
• **DO NOT CLAIM A CONVERGED MATSim↔SUMO LOOP.** There is NO standard convergence
  criterion for demand↔microsim coupling. 5 s is a stopping rule. Canonical
  reference Gütlein/German/Djanatliev 2018 → daceDS; closest live precedent
  DLR-TS/tsc (TAPAS↔SUMO, EPL-2.0).
• Reproducibility baseline: **1.82%** of transport simulation studies publish a
  repository at all; ~5% by 2024. This package is already unusual.
• TfNSW pays US$35k/yr into the ActivitySim consortium, operates a CLOSED
  tour-based model covering Sydney/NEWCASTLE/Illawarra, is building an ABM (Apr
  2025 → late 2027), and refused SCATS phasing.
• LICENCES (verified from the files): MATSim is GPL-2.0-OR-LATER (matsim/LICENSE,
  below repo root — which is why GitHub shows none). BEAM is GPLv3. SUMO EPL-2.0.
• VERIFIED STRENGTH: our trams/buses traverse congested network links (checked in
  the event stream). BEAM's buses do NOT feel congestion — for S1/S3 bus
  counterfactuals that would have been fatal.

═══════════════════════════════════════════════════════════════════════════════
OUT OF SCOPE
═══════════════════════════════════════════════════════════════════════════════
• Running SUMO. Deliverable 7 is the TOLERANCE, 5 s, settled. Harness and outer
  loop are P5. #27's survey half must land before the first corridor run.
• socnetsim joint plans — absent from the pinned jar.
• P6 analysis, P7 write-up, a 2013 historical reconstruction.
• Pedestrian counts / retail vacancy / 2014 timetable block P6, NOT P4.
  **Hypothesis B1 has NO OBSERVABLE AT ALL without pedestrian counts.**

═══════════════════════════════════════════════════════════════════════════════
WORKING STYLE
═══════════════════════════════════════════════════════════════════════════════
1. **Inventory first.** Read the relevant files; state your understanding; flag
   contradictions, gaps and decisions.
2. **Plan, then get sign-off.** Wait for approval before writing files.
3. **Implement.** Only after approval. Prefer clear TODOs over speculative code.
4. **REPRODUCE A DEFECT BEFORE ATTRIBUTING IT.**
5. **CLOSE ISSUES AS YOU GO.** The bar is STRUCTURALLY PREVENTED, NOT REMEMBERED.
6. **NO INVENTED DATA.** If a value is not measured it is assumed or modelled,
   labelled as such in `source`, and recorded in DECISIONS.md with a rationale
   and a sweep range. **An unsupported number presented as observed is the one
   failure this project cannot absorb.**
