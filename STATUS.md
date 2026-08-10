# STATUS — Project Wickham

Single source of truth for **where the build is, what's next, and how to resume**. Read
this at session start. **Keep it current in the same commit/PR as the work it describes**
— if a change makes a line here wrong, fix the line in that change, not later.

**Last updated:** 10 August 2026
**Stage:** P1 data acquisition complete. **No scenario has been run. Nothing in this repo
is a result.**

---

## Phase board

Phases as defined in [`newcastle-lr-proposal.md`](newcastle-lr-proposal.md) §7.1.

| Phase | State | Notes |
|---|---|---|
| P0 Scoping | ✅ complete | Base year 2026, zone system, scenario list S0–S6 settled. Scope calls closing proposal §10 are recorded in [`DECISIONS.md`](DECISIONS.md) §1. |
| P1 Data acquisition | ✅ complete | 182 files, 2.31 GiB, all provenance-tagged and hashed in [`data/MANIFEST.csv`](data/MANIFEST.csv). Three critical inputs remain unobtained — see below. |
| P2 Network build | ⬜ next | pt2matsim conversion of era + scenario feeds; netconvert for the SUMO corridor; manual OSM correction of Hunter/Scott Street. |
| P3 Demand synthesis | ⬜ not started | Synthetic population and plans exist as P1 artefacts; activity/OD work is P3. |
| P4 Calibration | ⬜ not started | 67 calibration targets built; 143 held out. |
| P5 Scenario runs | ⬜ not started | `src/run/` is empty. |
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
| Base year | 2026 · CRS EPSG:28356 (GDA2020 / MGA Zone 56) |

Reproduction commands: [`README.md`](README.md) "Reproducing". Column-level definitions:
[`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md).

For a one-page orientation — the P0–P7 milestone flow with the data each phase consumes
and yields, the MATSim ↔ SUMO coupling loop, the scenario matrix and the pre-registered
output metrics — open [`docs/project-flow.html`](docs/project-flow.html) in a browser.
Every domain term, tool and abbreviation on it carries a hover (or keyboard-focus)
explanation, with a link to the primary source where one exists.
It is a **plan, not a result**: every run-time figure on it is modelled from the assumed
dwell and signal parameters, and is restated once SCATS and dwell data land.

---

## Next up — P2 network build

1. **Manual OSM correction, Hunter/Scott Street corridor** — lane counts, turn
   restrictions and kerbside use are currently **75–98% imputed**
   ([`DECISIONS.md`](DECISIONS.md) §3.1). The B3 net-arrivals test depends on these, so
   this is the first task, not a cleanup.
2. **pt2matsim conversion** of the era feeds and the S0–S6 scenario feeds.
3. **netconvert** for the SUMO corridor, wired to the A2 signal layer.
4. Extend `tests/check_package.py` with network-build integrity checks as the layers land.

---

## Open items carried forward

Three inputs the proposal named as critical are **unobtained**, and are handled by
**sweep, not by assumption-as-fact** ([`DECISIONS.md`](DECISIONS.md) §0, §13). Formal
requests are outstanding; do not pin any of them to a point value.

| Input | Why it matters | Current handling |
|---|---|---|
| SCATS signal phasing | Corridor run time swings 38% between no priority and full priority (S2 vs S2b) — the largest single uncertainty in the model | Swept |
| Journey-linked Opal | Needed to *estimate* the transfer penalty rather than sweep it | Swept, 3–15 min |
| Measured charging dwell | Assumed 20 s per intermediate stop; worth 11% of end-to-end run time | Swept |

Also absent: pedestrian counts (none published for Newcastle), frontage-level retail
floorspace and vacancy, parking meter transactions, and a 2014 timetable to validate the
era-1 reconstruction.

---

## How to resume

1. Read this file, then [`DECISIONS.md`](DECISIONS.md) §0 (status summary) and
   [`CLAUDE.md`](CLAUDE.md) (conventions and hard constraints).
2. `python tests/check_manifest.py` — confirms the committed subset is intact.
3. `python tests/check_package.py` — needs the full local ~2.3 GiB package; run it before
   declaring any data phase complete.
4. Branch as `<git-handle>/<short-kebab-description>` (never `claude/*`).
