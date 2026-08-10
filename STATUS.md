# STATUS — Project Wickham

Single source of truth for **where the build is, what's next, and how to resume**. Read
this at session start. **Keep it current in the same commit/PR as the work it describes**
— if a change makes a line here wrong, fix the line in that change, not later.

**Last updated:** 10 August 2026
**Stage:** P2 network build complete. **No scenario has been run. Nothing in this repo
is a result.**

---

## Phase board

Phases as defined in [`newcastle-lr-proposal.md`](newcastle-lr-proposal.md) §7.1.

| Phase | State | Notes |
|---|---|---|
| P0 Scoping | ✅ complete | Base year 2026, zone system, scenario list S0–S6 settled. Scope calls closing proposal §10 are recorded in [`DECISIONS.md`](DECISIONS.md) §1. |
| P1 Data acquisition | ✅ complete | 182 files, 2.31 GiB, all provenance-tagged and hashed in [`data/MANIFEST.csv`](data/MANIFEST.csv). Three critical inputs remain unobtained — see below. |
| P2 Network build | ✅ complete | MATSim network + 15 mapped schedules, 4 SUMO corridor nets, corridor attributes graded by evidence. See below. |
| P3 Demand synthesis | ⬜ next | Synthetic population and plans exist as P1 artefacts; activity/OD work is P3. |
| P4 Calibration | ⬜ not started | 67 calibration targets built; 143 held out. |
| P5 Scenario runs | ⬜ not started | `src/run/` is empty. **Read the one-build constraint in [`DECISIONS.md`](DECISIONS.md) §3.5 before designing a run.** |
| P6 Analysis | ⬜ not started | `src/analyse/` is empty. |
| P7 Write-up | ⬜ not started | |

---

## What P1 delivered

| | |
|---|---|
| Study area | Newcastle, Lake Macquarie, Maitland, Cessnock, Port Stephens — 4,086 km² |
| Zones | 1,500 core SA1 + 201 external SA1, 222 core DZN |
| Population | 611,915 (2021 Census) → 612,680 synthetic agents |
| Road network | 43,112 edges, 9,207 km, gradient-attached |
| Active network | 35,653 edges, 6,325 km, directional walk-speed factors |
| PT | 5 GTFS eras + 10 scenario variants |
| Validation | 210 targets (67 calibration / 143 holdout) |
| Base year | 2026 · CRS EPSG:28356 (GDA94 / MGA Zone 56 — label corrected, [`DECISIONS.md`](DECISIONS.md) §2.6) |

---

## What P2 delivered

**Toolchain, pinned by digest** — `python src/setup/bootstrap_toolchain.py` fetches
Temurin JDK 25.0.4+7, pt2matsim 26.6 (shaded jar) and SUMO 1.27.1 into `.tools/`
(gitignored, ~1.4 GiB) and records each one's version, URL and sha256 in
`.tools/toolchain.json`. `--verify` re-checks the digests. No Maven: the shaded jar
carries MATSim. Details and the one known tool defect: [`DECISIONS.md`](DECISIONS.md) §3.6.

**Corridor attributes, graded by evidence rather than corrected by hand**
(`src/build/build_corridor_road_attributes.py`):

| | |
|---|---|
| Corridor / parallel edges classified | 605 (40 trunk, 84 cross, 417 parallel) |
| As-built trunk lane counts observed in OSM | **87.5%** — the corridor is not 75–98% imputed ([`DECISIONS.md`](DECISIONS.md) §2.5) |
| Turn restrictions resolved to coordinates | 1,385 of 1,386; 10 within 40 m of the alignment vs E1's assumed 14 |
| E1 road variants expressed as edge-level deltas | 195 patch rows; the as-built variant has **zero** — it is the observed network |

**MATSim** (`src/build/build_matsim_network.py`) — one base network,
157,678 links / 73,227 nodes / 23,212 km in EPSG:28356, plus the four E1 road variants as
link-attribute patches over it (so "variants differ only where E1 says" is structural, not
a diff), and all 15 feeds mapped:

| | |
|---|---|
| Feeds mapped | 15 (5 era + 10 scenario) |
| GTFS stops without a network link | **0, in every feed** |
| Artificial link share | 0.4–0.6% |
| Turn restrictions carried into the network | 1,240 `disallowedNextLinks` |

**SUMO corridor** (`src/build/build_sumo_corridor.py`) — 4 nets, one per road variant,
15,666 edges / 7,090 junctions / 211 traffic lights each, left-hand traffic, plus a
traffic-light additional file per (road variant × signal variant). All 14 A2 intersections
match a signalised junction in every variant and every realised cycle lands within 1 s of
its A2 value. netconvert output is byte-identical on rebuild.

**Checks** — `tests/check_package.py` grew from 180 to 374 lines: stop→link coverage and
fingerprints, orphan links and nodes, variant-vs-base containment, TLS pairing and cycle
fidelity, corridor provenance vocabulary, sweep ranges on every assumed patch, toolchain
pinning. **322 checks, all passing.**

---

## Open items carried forward

Three inputs the proposal named as critical are **unobtained**, and are handled by
**sweep, not by assumption-as-fact** ([`DECISIONS.md`](DECISIONS.md) §0, §13). Formal
requests are outstanding; do not pin any of them to a point value.

| Input | Why it matters | Current handling |
|---|---|---|
| SCATS signal phasing | Corridor run time swings 38% between no priority and full priority (S2 vs S2b) — the largest single uncertainty in the model | Swept. The SUMO corridor now carries the proxy timings explicitly, each program labelled `timing_source=assumed` |
| Journey-linked Opal | Needed to *estimate* the transfer penalty rather than sweep it | Swept, 3–15 min |
| Measured charging dwell | Assumed 20 s per intermediate stop; worth 11% of end-to-end run time | Swept |

Also absent: pedestrian counts (none published for Newcastle), frontage-level retail
floorspace and vacancy, parking meter transactions, and a 2014 timetable to validate the
era-1 reconstruction.

**Raised by P2, not yet resolved:**

| Item | Where | Consequence if left |
|---|---|---|
| **S2c/S4/S5 GTFS shapes were never extended** — all four tram feeds carry the same 275-point as-built geometry | [`DECISIONS.md`](DECISIONS.md) §3.4 | Extension corridors are derived from assumed stop sitings. Rebuild the shapes in `build_scenario_schedules.py` before publishing any S4/S5 result. |
| **pt2matsim is not reproducible run to run** — ~18% of route link sequences differ between identical builds | [`DECISIONS.md`](DECISIONS.md) §3.5 | Every scenario comparison must use **one** build of the network. Comparing feeds mapped in different builds puts an 18% path difference inside the treatment effect. |
| Pre-tram Hunter/Scott cross-section is assumed (2 lanes/direction, swept 1–2) | [`DECISIONS.md`](DECISIONS.md) §3.4 | This is the counterfactual B3 rests on. It must be reported as swept, never as a point estimate. |
| `--osm.crossings` segfaults SUMO 1.27.1 | [`DECISIONS.md`](DECISIONS.md) §3.6 | No crossings/sidewalks in the SUMO corridor. Pedestrians are MATSim's job on A6, so this is acceptable — but do not model pedestrian delay in SUMO. |

---

## How to resume

1. Read this file, then [`DECISIONS.md`](DECISIONS.md) §0 (status summary) and
   [`CLAUDE.md`](CLAUDE.md) (conventions and hard constraints).
2. `python tests/check_manifest.py` — confirms the committed subset is intact.
3. `python src/setup/bootstrap_toolchain.py --verify` — confirms the toolchain, or run it
   without `--verify` to fetch it (~1.4 GiB, needed only to rebuild the networks).
4. `python tests/check_package.py` — needs the full local package **and** the built
   networks; run it before declaring any phase complete.
5. Branch as `<git-handle>/<short-kebab-description>` (never `claude/*`).
