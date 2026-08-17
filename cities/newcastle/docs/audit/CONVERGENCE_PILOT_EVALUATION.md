# Convergence pilot evaluation — issue #5, first post-rebuild measurements

*18 August 2026. Two arms complete on the 16 August rebuild; a third in flight.
Claim → measurement → verdict, per the `ISSUE_VERDICTS.md` pattern. Nothing here
is a result about Newcastle: both runs are uncalibrated and neither passes the
declared relaxation gate, so every figure below is a statement about the run,
not about the city.*

## What was run

| | arm 1 | arm 2 | arm 3 (in flight) |
|---|---|---|---|
| tag | `conv1000_10pct` | `conv1000_25pct` | `conv1500_10pct` |
| fraction × iterations | 10% × 1000 | 25% × 1000 | 10% × 1500 |
| agents | 54,617 | 136,068 | 54,617 |
| wall clock | 10 h 59 m | 30 h 47 m | ~17 h expected |
| median iteration | 33.3 s | 90.2 s | — |
| exit / accounting / telemetry | 0 / closes / clean | 0 / closes / clean | — |
| stuck agents | 0.022% of departures | 0.023% | — |

One arm at a time, threads 10 (registry), seed 20260810, same network build.
Two earlier directories from a concurrent 2 AM launch on 16 August died without
`_run.json` and were quarantined to `results/_aborted_20260816/`.

## The relaxation verdict (#5) — measured, not yet declarable

**Claim (shipped):** ~1000 iterations suffice (`DECISIONS.md` §9.27, pre-rebuild).

**Measurement:** by the declared metric (per-mode drift, iteration 800 → 1000,
tolerance `RUN.relaxation.drift_tolerance_pp` = 0.5 pp) **both arms fail
identically**: worst-mode drift +3.54 pp (10%) and +3.60 pp (25%), car in both.

The drift decomposes into two phenomena the metric cannot distinguish:

1. **A selection snap at the cutoff, complete within 10 iterations.** 800 → 810:
   car +3.4 pp, walk 3.97 → 1.02%, pt 1.08 → 0.25% at both fractions to within
   0.1 pp. When innovation stops, exploration noise vanishes and selection
   concentrates agents onto their best-scoring plans. This is a property of the
   scoring structure, not of non-relaxation — **a run of any length fails the
   800-vs-final window while the snap exists.**
2. **True post-snap drift, well inside tolerance:** 810/850 → 1000 moves car
   +0.09 pp (10%) and +0.17 pp (25%).

**What is genuinely unconverged is the pre-cutoff search.** Car creep per 100
iterations at 25%: +1.94, +1.43, +1.04, +0.76 (iterations 400→800), a geometric
decay of ×0.73 per block; the 10% arm shows the same +0.75 at 700→800.
Extrapolated, ~2 pp of movement remained in the innovated state when the cutoff
froze it.

**Verdict: OPEN, pending arm 3.** `conv1500_10pct` (cutoff 1200) measures the
extrapolation directly: if its final state sits ~1.5 pp from arm 1's, the
horizon drives the answer and 1000 is insufficient; if it matches, the creep
extrapolation overstates and 1000 can be declared with the snap-aware window.
Either way the declaration must also redefine or re-justify the drift window
(a `DECISIONS.md` entry, because the current declared instrument can never
pass), and only then does the registry field move off `unobtained`.

**Fraction-independence is established:** snap size, post-snap drift, creep
decay, stuck-agent profile and every structural finding below replicate at both
fractions. The 10% arm is a valid convergence probe for 25% conclusions.

## The evaluation slate on the two arms

| Claim | Measurement | Verdict |
|---|---|---|
| Mode share near HTS after the five demand fixes | `target_lga_pct`, linked: MAE **8.45 pp** (10%) / **6.95 pp** (25%). Car −5.0/−1.2, ride +20.3/+16.6, walk −12.7/−12.7, pt −3.5/−3.4, other +0.8/+0.8 | Structure right for car/bike/other; ride, walk, pt carry the calibration load (#9, #14). 25% fits better on the car/ride margin |
| #28: ride ≤ car realised speed per distance bin | Ride faster in **every bin below 50 km** at both fractions: 1.13–1.14× (0–1 km) declining to 1.01–1.02× (20–50 km). Aggregate means show parity (45.3 vs 45.2 km/h) — Simpson's reversal from ride's shorter trip mix | **Residual sized, #28 stays open.** Aggregate-mean comparisons remain banned |
| #31 occupancy constraint | 0.76 (10%) / 0.64 (25%) passengers per driver vs observed 0.35, range [0.25, 0.39] | Outside at both fractions; the #31 decision is live for the calibration sitting |
| #30 reopen: sub-1 km trip mass | 2.56% (10%) / 2.50% (25%) of completed trips vs HTS-implied >~10%. Destinations are fixed at generation, so this is generation-side | **Reopen condition met** — fraction-independent, structural |
| #29 sizing: bike share | 4.01/4.00% vs 3.2 observed | Availability 0.50 draw approximately right; **no constraint tuning warranted** |
| #20 reopen: V113 (M1 at Wyee) materially non-zero | Modelled 60 (10%, scaled) vs 44,885 observed light-vehicle; the through tier holds 17,955 agents with M1 its largest gate | **Reopen condition met** — through demand exists but does not traverse the count link; injection-point/routing question |
| Count fit sizes freight's absence (#24) | Mean −92% at both fractions, RMSE ~113% of mean observed, same 7 zero stations. Freight explains ~6.5%. The two stations on roads with no parallel alternative fit at −31% and −6%; urban arterials sit at −95 to −100%, including two matched within 6 m carrying zero | **The gap is structural, not freight-sized.** Working hypothesis: flat road hierarchy (no junction delay off-corridor; residential 50 vs arterial 60 km/h) disperses traffic off arterials. Needs verification before any remedy is proposed |
| Stuck-agent panel | 149 (10%) / 387 (25%) per iteration, walk+pt dominated; pre-rebuild was ~1,500 | Halved by the rebuild, persists at small scale; pt-stuck ≈ pt en route at the 30:00 window end |
| Wall-clock + heap re-derivation | 33.3 s/iter, ~29 GiB WS @ 10% (30g); 90.2 s/iter, ~33–38 GiB @ 25% (40g). One unexplained slow block (iterations ~200–293 at 25%, ~179 s/iter apparent, self-recovered — consistent with the §9.36-era stall, still unattributed) | Memory model: ~24 GiB fixed + ~0.09–0.3 MB/agent → 100% ≈ 80–160 GiB heap. 25% × 1000 costs ~31 h on the 2-channel laptop |

**Cross-fraction scaling (goal check):** walk, pt and bike+other shares match
across fractions to 0.1 pp; the car↔ride margin shifts ~3.7 pp (car 54.0 → 57.8,
ride 40.9 → 37.2 from 10% to 25%). Fraction scaling is clean for the minor modes
and **not neutral on the car/ride split** — to be re-examined once the ride
scoring defect is fixed, since that margin is currently dominated by it.

## Not done here, deliberately

No issue closed or reopened, no registry field moved, no `DECISIONS.md` entry:
the #5 declaration waits on arm 3, and issue actions belong with it. `fit.py`
outputs live in each run directory (`_fit.json`); no calibration report was
written into `docs/audit/` from unrelaxed runs.
