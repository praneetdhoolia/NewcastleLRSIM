---
name: onboard
description: Start-of-session onboarding — rebuild the complete project picture from the repo and GitHub (goals, phases, tasks, simulator-vs-reality, issues, PRs), verify the environment, and state the active lane. Use at the start of any session, especially with no prior context. The counterpart of /handoff.
---

# /onboard — reconstruct the whole picture from `main` alone

Assume zero session memory. Everything below is read from the repository and
GitHub; nothing is taken from recollection. Where a document disagrees with
another, the precedence is: `.claude/CLAUDE.md` (constraints) →
`DECISIONS.md` (record) → `STATUS.md` (board) → `NEXT_AGENT_BRIEF.md`
(pointer). **Trust order: artefact > document > brief.** The brief says this
about itself — verify anything load-bearing against the artefact it cites.

Run the phases in order. The output of this skill is a briefing to the user
(Phase 6) — do not start work the brief assigns until the briefing is given
and the environment checks pass.

## Phase 0 — The reading, in order

1. `.claude/CLAUDE.md` — conventions and hard constraints (loaded
   automatically; re-read the hard-constraints list deliberately).
2. `cities/newcastle/docs/handover/NEXT_AGENT_BRIEF.md` — the handover:
   goal, done-do-not-redo, active lane, traps, owner directives.
3. `cities/newcastle/docs/STATUS.md` — the board: phase table, deliverable
   checklist, numbered plan, runs on disk, run economics.
4. `cities/newcastle/docs/DECISIONS.md` — start at its topical index ("How
   to find something in this file"); read the sections the brief and board
   point at (the newest §9.x family and the top of the §14 change log).
5. `cities/newcastle/docs/design/newcastle-lr-proposal.md` §1, §3, §7, §8 —
   the research goal, hypotheses A1–A6/B1–B4, phases, deliverables.
6. Only as needed after that: the audit reports under
   `cities/newcastle/docs/audit/` and design dossiers under `docs/design/`.

## Phase 1 — Environment verification (the brief's §0, always)

```bash
python src/setup/bootstrap_toolchain.py --verify   # pins + compiles the Java
python tests/check_manifest.py                     # committed subset intact
python src/registry/check_hardcoding.py --strict   # must exit 0
```

Also: `git status` / current branch (work starts from `main` unless the
brief says otherwise); confirm whether a run is in progress (MATSim java
process, `results/` mtimes) before assuming the machine is free.

## Phase 2 — The live state from GitHub, not from documents

1. `gh issue list --state open` — for each open issue: title, last comment
   date, whether its numbers predate the latest DECISIONS entry (if so it
   needs updating, which is /handoff work to flag, not silently absorb).
2. `gh pr list --state all` — the merged sequence tells the project's story;
   any OPEN PR is unfinished business to surface before new work starts.
3. Cross-check: does the brief's issue/PR ledger match what GitHub actually
   shows? A mismatch is a finding — report it, do not paper over it.

## Phase 3 — The six state-of-the-project questions

Answer all six exhaustively, every number traceable to its source:

1. **Goals & achievement.** The research goal (proposal §1: the untested
   Auditor-General claims; hypotheses A1–A6, B1–B4, secondary S-a–S-d) and
   the operational goal (brief §1: the digital twin, "CHECKED, not
   assumed"). Against them: what is built, what is *measured* to work, and
   the state of each of the six project deliverables (proposal §8).
2. **Phases.** P0–P7 with each one's state and the evidence for it
   (STATUS.md phase table, verified against the artefacts it cites).
3. **Tasks per phase.** The numbered plan (STATUS.md "The plan"): per batch,
   how many done, how many done *and evaluated* (a task without its
   measurement is not evaluated), which are open, which is the active lane,
   which are proposed for deletion/rework and awaiting the owner.
4. **Simulator vs real life.** The latest valid run's fit against the
   calibration targets: per-mode modelled/observed/error, occupancy,
   trip-geometry ratios, counts, patronage — labelled pre- or
   post-calibration, diagnostics or results. If no run exists, say so;
   never infer results from inputs.
5. **Issue ledger.** Totals filed/closed/open; per open issue: what it
   tracks, its last evidence date, and whether it needs evaluation,
   updating, or is queued work.
6. **PR history and the next PR.** One line per merged PR; what the next PR
   should achieve per the recorded value order, and whether that choice is
   pending an owner decision.

## Phase 4 — The constraints that invalidate work (recite, don't rediscover)

From CLAUDE.md and the brief, confirm you can state without looking: no
multi-hour run without explicit approval (say the cost, get a yes); no
invented data; the 67/143 holdout split is never opened or peeked; never
compare across sample fractions or network builds; one arm at a time; raw
data immutable; every assumed value declared in the registry with a sweep;
run outputs need `_run.json` to be results; branch naming and
no-attribution rules. Then read the brief's traps section — each one has
already cost a day.

## Phase 5 — Gap scan

- Board lines contradicted by artefacts (stale figures, wrong counts).
- Uncommitted work in the tree that no document mentions.
- An in-progress or crashed run nobody closed out.
- Open issues whose numbers are older than the newest DECISIONS entry.
- An open PR that should merge or close before new work.

Each gap goes in the briefing; fixing them is scoped work, not something to
do silently during onboarding.

## Phase 6 — The briefing (the deliverable)

Report to the user, in this order and with numbers:
1. The six answers from Phase 3, compressed but complete.
2. Environment check results (Phase 1) and anything they block.
3. Gaps found (Phase 5).
4. **The active lane** — the single next task per the brief, its cost, and
   whether it needs an owner decision or approval before starting.

Then stop. Do not begin the active lane until the user (or a standing
directive in the brief) says to.
