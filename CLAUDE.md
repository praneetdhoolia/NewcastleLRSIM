# Project Wickham — project conventions

Repo-level guidance for any Claude Code session working in this repository.

## What this is

A counterfactual microsimulation of the **Newcastle Light Rail** as a transport
intervention — MATSim for the regional demand model, SUMO for the corridor — built to be
more transparent about its assumptions than the business case it examines.

- [`newcastle-lr-proposal.md`](newcastle-lr-proposal.md) is the **research design**: what
  is being built, which scenarios, which tests. Read it for intent, scope and vocabulary.
- **[`DECISIONS.md`](DECISIONS.md) is the single source of truth for every value that is
  not observed.** Every parameter chosen without direct empirical support is recorded
  there with its rationale and its sweep range (proposal §8.1 — *"not optional"*). It also
  records four corrections to premises stated in the proposal. **Consult it before
  changing any assumed value, and don't re-litigate a settled decision without new
  evidence.**
- **[`STATUS.md`](STATUS.md) is the single source of truth for where the build is, what's
  next, and how to resume.** Read it at session start; **keep it current in the same
  commit/PR as the work it describes.**
- [`README.md`](README.md) is the data-package guide: layout, reproduction commands,
  sources and licences.
- Current stage: **P3 demand synthesis complete. No scenario has been run. Nothing in
  the repo is a result.** The MATSim network, the 15 mapped schedules, the SUMO corridor,
  the synthetic population, the activity chains and the 30 assembled scenario x day-type
  run input sets are all *inputs*, not outputs.

## Working style (apply to every change)

1. **Inventory first.** Read the relevant files; state your understanding; flag
   contradictions, gaps and decisions.
2. **Plan, then get sign-off.** Propose the change and **wait for approval** before
   writing files.
3. **Implement.** Only after approval. Prefer clear TODOs over speculative
   implementation.

## Hard constraints (do not violate)

- **Every controllable value is declared in `config/registry/`, not typed into a
  script.** A value whose `source` is `assumed`, `literature`, `measured` or `derived`
  must carry a sweep, a `held_fixed` rule or a `derived_from` identity — the schema
  rejects anything else, and `check_package.py` tests it. Regenerate
  [`docs/CONFIG_REFERENCE.md`](docs/CONFIG_REFERENCE.md)
  (`python src/registry/render_docs.py`) in the same change. The build layer is not yet
  migrated and is pinned to the registry by `src/registry/check_legacy_drift.py`: if you
  change a constant there, change the registry field with it.
- **No invented data.** Never fabricate an observation, a count, a patronage figure or a
  coefficient. If a value is not measured it is **assumed or modelled**, and it must be
  labelled as such in the `source` field of its artefact **and** recorded in
  `DECISIONS.md` with a rationale and a sweep range. An unsupported number presented as
  observed is the one failure this project cannot absorb.
- **No result before a run.** Nothing in this repo is an output of the model until a
  scenario has actually been executed. Do not write, summarise or infer scenario results
  from the input package.
- **Reproducibility is a gate, not an aspiration.** Every derived file must be
  regenerable by a committed script from the immutable raw downloads, and must be listed
  in [`data/MANIFEST.csv`](data/MANIFEST.csv) with its hash, row count, producing script,
  source, licence and retrieval date. Regenerate the manifest
  (`python src/build/build_manifest.py`) whenever a data artefact changes.
- **Determinism.** Everything synthetic is seeded (`20260810`). Do not introduce
  unseeded randomness, wall-clock dependence or dict/set-ordering dependence into a build
  script.
- **Provenance for every acquisition.** A new download lands under `data/raw/` with a
  `provenance_*.json` recording source URL, retrieval timestamp and licence. Raw
  downloads are **immutable** — never edit one in place; corrections happen in
  `src/extract` / `src/build`.
- **Licence boundary.** OSM-derived layers are **ODbL 1.0 (share-alike)**; the rest of
  the package is CC-BY 4.0. Keep the distinction visible in the manifest and in anything
  published; do not merge an OSM-derived column into a CC-BY artefact without noting it.
- **The three unobtained inputs stay unobtained.** SCATS signal phasing, journey-linked
  Opal, and measured charging dwell are handled **by sweep, not by
  assumption-as-fact** (`DECISIONS.md` §0, §13). Do not quietly pin one to a point value.
- **The toolchain is pinned, and a toolchain change is a model change.** JDK, pt2matsim
  and SUMO are fetched by [`src/setup/bootstrap_toolchain.py`](src/setup/bootstrap_toolchain.py)
  into `.tools/` (gitignored) and pinned by sha256 in `.tools/toolchain.json`. Changing a
  version means re-running, re-hashing and logging it in `DECISIONS.md` §14 — a different
  `netconvert` can move a corridor result.
- **One build of the network per comparison.** pt2matsim's schedule mapping is not
  reproducible run to run (`DECISIONS.md` §3.5): ~18% of route link sequences differ
  between identical builds, while stop-to-link assignment is stable. Never compare a
  scenario mapped in one build against a scenario mapped in another. **Anything that
  needs a per-day-type or per-variant schedule must derive it from the already-mapped
  schedule** (as `build_matsim_run_inputs.py` does, by filtering `transitRoute` ids),
  never by re-running the mapper.
- **A scenario runs on its own mapped network, not on `networks/matsim/variants/`.**
  The variant networks are patched over the *base* network, which carries no mapped
  transit links; they are a reference artefact showing the E1 deltas. The runnable
  network is the scenario's own `schedules/<S>/network.xml.gz` with the E1 patch
  re-applied by `osm:way:id` (`DECISIONS.md` §9.3).
- **Bulk data is not committed.** See [`.gitignore`](.gitignore) — raw downloads, GTFS
  bundles, synthetic population/plans, large derived geometry and run outputs are
  regenerable and stay out of git. The manifest is committed; the bytes are not.
- **Units and CRS.** EPSG:28356 (GDA2020 / MGA Zone 56), metres, base year 2026. State
  units in every new column name or data-dictionary entry.
- **Language:** Australian / Indian English spellings throughout.

## Conventions

- **Branch naming.** `<git-handle>/<short-kebab-description>`, with `<git-handle>` derived
  from the active git identity (the `…+<handle>@users.noreply.github.com` email, else
  `git config user.name`). **Never `claude/*`** — if the harness assigns one, this rule
  wins: `git branch -m …` before committing. A SessionStart hook surfaces this each
  session.
- **Attribution.** No Claude co-author trailer or PR attribution
  (`attribution.commit`/`pr` empty, `includeCoAuthoredBy: false` in
  [`.claude/settings.json`](.claude/settings.json)); a SessionStart hook pins the git
  identity. **No `claude.ai/code` session link** in commit messages or PR bodies either.
  `attribution.sessionUrl: false` is set, but it does **not** suppress the session-link
  footer the cloud platform injects into a PR body — so this is enforced
  deterministically across four layers, not by that setting alone:
  1. [`.githooks/commit-msg`](.githooks/commit-msg) strips the session link /
     `Claude-Session:` trailer from every commit (activated each session via
     `core.hooksPath`, set in the SessionStart hook because an ephemeral container
     doesn't track `.git/hooks`);
  2. [`.claude/hooks/block-session-ref-in-pr.sh`](.claude/hooks/block-session-ref-in-pr.sh)
     (`PreToolUse`) denies `create`/`update_pull_request` MCP calls whose title/body carry
     the link;
  3. [`.claude/hooks/block-session-ref-in-gh-pr.sh`](.claude/hooks/block-session-ref-in-gh-pr.sh)
     (`PreToolUse`) denies `gh pr create`/`gh pr edit` commands carrying it (the `gh` CLI
     path);
  4. [`.github/workflows/strip-session-ref.yml`](.github/workflows/strip-session-ref.yml)
     scrubs the link from a PR **body** server-side — the only layer that catches a body
     injected by the cloud **platform** (outside the agent's tool loop, and not in git
     history, so layers 1–3 structurally cannot see it). It is a scrub-after-creation.
- **Network access** is sandboxed to the data sources this project actually uses
  (ABS, TfNSW Open Data, Overpass, Copernicus, GitHub) — see `sandbox.network` in
  `.claude/settings.json`. Adding a source means adding its domain there **and** a
  provenance record.
- **Path references in prose.** Never abbreviate a file path with `…`/`...` (e.g.
  `data/.../A1_road_edges.csv`). Renderers auto-link it into a literal, broken URL. Write
  the full real path — `data/processed/network/A1_road_edges.csv`.
- **Commit messages** state what changed in the *model or the data*, not which script ran.

## Checks

| Check | Where | Needs |
|---|---|---|
| `python tests/check_manifest.py` | CI (`.github/workflows/test.yml`) + local | committed files only |
| `python -m compileall -q src tests` | CI | nothing |
| JSON validity of provenance / scenario / params files | CI | nothing |
| `python tests/check_package.py` | **local only** | the full ~2.3 GiB package |

CI deliberately runs nothing that downloads a source dataset or executes a scenario:
those depend on ABS/TfNSW/Overpass availability and on compute, not on the diff. Run
`tests/check_package.py` on a workstation before declaring a data phase complete.

## Repo map

| Path | What it holds |
|------|---------------|
| `newcastle-lr-proposal.md` | The research design: scenarios, tests, appendices. |
| `DECISIONS.md` | Every assumed/modelled value + rationale + sweep range (don't re-litigate). |
| `STATUS.md` | **Verified phase board + the full deliverable checklist** — the source of truth for both (read at session start; keep current). |
| `docs/P4_CHECKPOINT.md` | Long-form P4 handoff: what is measured and true, the traps, errors already made, how to drive the harness. |
| `docs/NEXT_SESSION_PROMPT.md` | Ready-to-paste brief that orients a fresh session in one message. Keep in step with the two above. |
| `README.md` | Data-package guide: layout, reproduction commands, sources and licences. |
| `docs/DATA_DICTIONARY.md` | Column-level definitions for every processed artefact. |
| `docs/project-flow.html` | One-page orientation: P0–P7 flow, data layers, scenario matrix, pre-registered metrics. Plan, not result — restate its run-time figures when SCATS/dwell land. |
| `data/raw/` | Immutable downloads + `provenance_*.json`. Never edited in place. |
| `data/processed/` | Clipped and derived layers: zones, census, hts, observed, network, corridor, landuse, validation. |
| `data/MANIFEST.csv` / `.json` | Per-file hash, rows, producing script, source, licence, retrieval date. |
| `networks/osm/` | Raw Overpass extracts (roads, footways, rail, parking, POI, buildings). |
| `schedules/` | GTFS era feeds + `scenarios/S0..S6` variants. |
| `demand/` | Synthetic `population/` (B1) and `plans/` (B2 tours per day type + `matsim/` plans). Seeded, deterministic. |
| `config/` | **The input registry**: every controllable value with units, provenance and a sweep or held-fixed rule, plus the JSON Schemas for inputs and outputs and the scenario/day/run overlays. |
| `params/` | C1 behavioural parameters + the 140-point sensitivity sweep grid. |
| `scenarios/` | E1 scenario configs, one JSON per scenario, plus `matsim/` — the assembled run inputs, one directory per scenario x day type. |
| `src/extract/` | Acquisition and clipping. |
| `src/build/` | Layer construction (the reproduction pipeline, in README order). |
| `src/registry/` | The registry resolver, its validators, the legacy-drift check and the docs generator. |
| `src/run/`, `src/calibrate/`, `src/analyse/` | P3+ execution, calibration and analysis. |
| `results/` | Run outputs. Gitignored — nothing here is committed. |
| `tests/` | `check_manifest.py` (CI, committed subset) and `check_package.py` (local, full package). |
