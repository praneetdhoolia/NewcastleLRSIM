# Issue verdicts — every open issue re-measured on today's model

**Written 15 August 2026, after the zero-hardcoding change**, against the
protocol in
[`handover/ISSUE_ASSESSMENT_BRIEF.md`](../handover/ISSUE_ASSESSMENT_BRIEF.md) §2:
*every open issue is a hypothesis until it is re-measured, because the model it
was measured on no longer exists.*

**This document changes no parameter and fixes nothing.** It records, per issue,
what was claimed, what the claim rested on, what today's package says, and what
follows. Where a claim could not be reproduced without a run, it says so and says
why the run is not worth making yet, rather than reporting an old number as
current.

---

## The state these verdicts were measured on

| | |
|---|---|
| Branch / tree | `praneetdhoolia/mode-choice-specification`, clean |
| `tests/check_manifest.py` | **OK** — 378 files verified |
| `src/registry/check_hardcoding.py --strict` | **TOTAL 0**, and **69 of 69** bound fields proven to reach |
| Emitted config read from | `cities/newcastle/scenarios/matsim/S2/WEEKDAY/config.xml`, written 15 Aug by the emitter |
| Demand artefacts read from | `demand/plans/B2_activity_trips_*.csv` and `demand/plans/matsim/population_*.xml.gz`, written **12 Aug** — the emitter change did not regenerate them |
| Road layer read from | `data/processed/network/A1_road_edges.csv`, written **13 Aug** |
| Runnable network read from | `networks/matsim/base/network.xml.gz`, built **10 Aug** |
| `results/` | **empty** — no run exists to measure anything on |
| `networks/osm/` | **empty** (#32); `networks/osm_pre_issue32/` is the only copy |

**Nothing in this repository is an output of the model**, and nothing below
reports one.

---

## Verdict table

| # | Claim | Evidence it rested on | Re-measured | Verdict | Next action |
|---|---|---|---|---|---|
| **5** | 100 and 250 iterations are both too low; the model does not converge | two 1% × 250 runs, **8 threads**, pre-emitter, pre-walk-repair; a 25% pilot that has since been deleted | **not reproducible** — `results/` is empty, and any run made now is invalidated by the B0 re-harvest it must precede (§3.5) | **UNTESTABLE (run-blocked, and deliberately not run)** | one arm, after the B0 batch, never three at once |
| **9** | re-solve `asc_car_passenger` once the iteration count settles | a constrained solve at a fixed 250-iteration protocol, on the **pre-ride-fix** model | field still `-0.85`, `status: placeholder`; its premise (4.52 ride legs per car leg) was measured on a model that no longer exists | **CONFIRMED-OPEN, and its premise also needs re-measuring** | strictly downstream of #5 |
| **14** | deliverable 5 (calibrated base) not met; needs a modelling decision | a 3-of-7 deliverable table | `params/C5_calibration.json` **absent** → still not met. The issue's own table is stale: 4, 6 and 7 are met and the list is now 9 items, 7 met | **CONFIRMED in substance; issue body stale** | edit the body; the decision is still §8.5's first branch, logged before any run |
| **20** (1) M1 | no boundary through traffic; the M1 at Wyee carries no cars | a modelled volume of 0 at station 55888 on a 10% run | **10,934 external legs of 2,255,047 (0.485%)**, and every one terminates at a `home`, `work` or `other` **inside** the study area. No through movement exists in the demand to route onto the M1 | **CONFIRMED structurally** (the run-side zero is untestable) | external-station matrix from cordon counts, in the B0 batch |
| **20** (2) mis-match | Raymond Terrace Rd (55839) is attached to a one-lane Dockyard Rd by proximity alone | 14 proximity-only matches of 203 | today's `count_station_links.csv`: **195 rows, 111 stations, 0 proximity-only**; station 55839 is matched to **nothing** | **FALSE — fixed 12 Aug (`5dc685a`), issue never updated** | strike part 2 from the issue |
| **24** business | work-related business travel is an observed purpose the model does not generate | the B2 purpose list | **WB = 47,612 legs = 2.111%** against an observed **2.0%** | **FALSE (already struck in the title; re-confirmed)** | do not build it — it would double-count |
| **24** freight | freight is absent | absence | no freight demand anywhere; `B.counts.heavy_vehicle_share` (0.0652) is applied **at comparison time**, to the comparison, not to the model | **CONFIRMED** | heavy-vehicle background layer, swept not pinned, in the B0 batch |
| **28** | a car passenger arrives **13% faster** than the car, because ride gets free-flow times | `output_legs.csv.gz` of a 250-iteration run, since deleted | the 13% was **already withdrawn** (aggregate over unequal lengths; 4–8% stratified). `CitysimControler` has bound ride to `networkTravelTime()` and the car disutility since **12 Aug (`5f5631a`)**, so the free-flow mechanism named in the title is **gone**. The config still reads `mainMode=car` / `networkModes=car,ride` — the fix is in the runner, not the config | **CHANGED — the claim as stated is false; a smaller residual is asserted and unverified** | the residual (ride experiences congestion but causes none) is a **run** measurement; do not re-open until after B0 |
| **29** mechanism | car ownership is modelled, bike ownership is silently universal, and the asymmetry is undeclared | `_plans_report.json` seed shares | plans carry `carAvail` and `rideAvail` and **no bike attribute**; seed shares reproduce **exactly** (bike 22.67%, car 15.72%); **no registry field and no `DECISIONS.md` entry** records the asymmetry | **CONFIRMED, unchanged** | declare the asymmetry before deciding whether to model it |
| **29** magnitude | bike is **5×** its observed share (15.86% vs 3.2%) | a run predating two changes to the walk/bike specification | the specification moved: walk's rate **−27.92 → −11.6392**, bike's **−16.05 → −14.5226**, walk speed 1.05 → 1.25 m/s, one 1.30 beeline factor → measured 1.6902 / 1.5231. The walk-beats-bike indifference distance moves **174 m → 373 m beeline** (2.14×), and the share of B2 legs inside it **0.657% → 1.816%** | **CHANGED — magnitude unverified on today's model** | re-measure after B0; do not size a bike constraint against the old 5× |
| **30** cause 2 (trip lengths) | destinations too far; education 2.19×; 4.9% of trips under 1 km | B2 vs HTS `JOURNEY_AVG_DISTANCE` | reproduces **digit for digit**: 4.922% under 1 km network; education **6.571 km vs 3.0 (2.19×)**, commute 17.31 vs 11.5 (1.50×), social/rec 11.05 vs 13.6 (0.81×), shopping 8.37 vs 6.0 (1.39×), escort 7.86 vs 6.4 (1.23×) | **CONFIRMED, unchanged** | destination placement, in the B0 batch. **Still nobody has chased it** |
| **30** cause 1 (scoring) | walk −27.92 util/hr vs bike −16.05, at 3.78 km/h | the config as shipped on 12 Aug | today: walk **−11.6392**, bike **−14.5226**; the ordering the issue describes is **reversed** | **FALSE — repaired 13 Aug (`febc729`, §9.28)** | strike cause 1 from the issue; the issue is now about trip lengths alone |
| **31** | a subtour switches to ride freely; one driver chauffeurs unlimited passengers | reading the config and §9.11 | `chainBasedModes = car,bike` unchanged; `RideAvailabilityModesCalculator` is a **choice-set** filter and its own javadoc says it binds no driver; **no `PassengerConstraint` anywhere**; and B2 carries `party_size = 1` on **all 2,255,047** legs, so the demand has no joint trip either | **CONFIRMED, unchanged** | ⚠ **do not add `ride` to `chainBasedModes`**, and do not copy eqasim's constraint — see the brief §7.10 |
| **32** | the OSM harvest box clipped **87 of 1,500** core SA1s, **31,940 agents**, out of the road network | the shipped road layer against `zones_SA1.gpkg` | reproduces **exactly**: road layer reaches 151.0316–152.0118; **87** core SA1s have their centroid outside it, carrying **31,940** agents. Also measured: **99** core SA1s / **35,365** agents contain **no road node at all** | **CONFIRMED — the code fix landed, the data defect has not been repaired** | the B0 re-harvest. Verify the 87 are inside afterwards, and that every layer is **larger** |
| **34** mechanism | a hand-drawn CBD rectangle sets a pre-registered B1 denominator | reading `build_landuse_parking.py` | the rectangle is **relocated, not fixed** — `geometry/analysis_extents.json`, byte-identical, and the builder still filters on it | **CONFIRMED, unchanged** | derive it — but see the next row first |
| **34** damage Q2 | does a segmented street run outside the box? | never measured | **No.** Across the seven streets, **0 edges straddle the boundary**, and the nearest edge the box drops is **1.11 km** outside it (median 8–36 km). What the box actually does is **disambiguate street names across the five LGAs** — the dropped edges are Hunter, Scott and King Streets in *other towns* | **FALSE as a fear; the box clips no frontage** | any derived replacement **must keep a name disambiguator**, or the frontage metric silently gains other towns' streets |
| **34** damage Q1 | how much floorspace falls outside the box? | never measured | **cannot be measured from this package**: `buildings_cbd.osm` was itself harvested inside that same rectangle (extent −32.9450…−32.9044, 151.7244…151.7985 — the box ±60 m), so buildings outside it were never acquired | **UNTESTABLE until the re-harvest** | measure it against the derived corridor extent (1.6 km further S, 1.4 km N, 1.8 km E) **before** changing the denominator |
| **37** | **348 agents** have a trip at 02:00 **and** at 26:00 | a 10% run's event stream at **iteration 30**, after time mutation | on the artefact the issue names, cross-checked against B2: **2,066 WEEKDAY persons (0.394%)** carry both — plus **SAT 358 (0.080%)** and **SUN 240 (0.058%)**, which were never measured | **CONFIRMED (mechanism and presence); the 348 is a post-mutation run figure and does not reproduce at the seed** | cap or wrap the chain in B2, in the B0 batch. **Acceptance must cover all three day types**, not just WEEKDAY |

**Tally:** 3 FALSE · 2 CHANGED · 7 CONFIRMED · 2 UNTESTABLE (one of them run-blocked,
one gated on the re-harvest). Two issues (#20, #30, #34) split into parts with
different verdicts, which is why the rows outnumber the issues.

---

## How each verdict was produced

Every figure below came from a committed or on-disk artefact. No run was made,
no holdout row was read, and nothing was inferred from a number that was not
measured here.

### #37 — recount, on the file the issue names

Departure = an activity `end_time`. Counted per person, on
`demand/plans/matsim/population_<DAY>.xml.gz`, and independently on
`demand/plans/B2_activity_trips_<DAY>.csv`; **the two agree exactly**.

| day | persons | ends < 06:00 | ends ≥ 24:00 | persons with **both** | share |
|---|---:|---:|---:|---:|---:|
| WEEKDAY | 524,125 | 37,611 | 107,465 | **2,066** | **0.394%** |
| SAT | 450,319 | 14,412 | 41,799 | **358** | 0.080% |
| SUN | 413,279 | 13,733 | 26,727 | **240** | 0.058% |

The issue's 348 is 0.66% of a 10% sample at iteration 30 — *after*
`TimeAllocationMutator` has moved departure times — so it is not the same
quantity as the seed count and cannot be reproduced without a run. The issue's
own diagnosis is nevertheless upheld: the collision is present at the seed, in
B2, before any plan has been mutated. `B.activity.departure_profile` is
**value-identical** to the `DEPART` literal it replaced (checked key by key
against `8d97f6a`), so the rewiring did not move this.

### #30 — trip length by purpose, against HTS

Modelled `straight_dist_km` × `B.activity.detour_factor` (1.3376, measured)
against `JOURNEY_AVG_DISTANCE`, Newcastle LGA 2024/25 — a **constraint, not a
target**, and not one of the 210.

| purpose | legs | modelled km | observed km | ratio |
|---|---:|---:|---:|---:|
| HW commute | 422,223 | 17.31 | 11.5 | **1.50×** |
| HE education | 146,160 | **6.57** | **3.0** | **2.19×** |
| HS shopping | 351,089 | 8.37 | 6.0 | 1.39× |
| HX serve passenger | 327,611 | 7.86 | 6.4 | 1.23× |
| NHB personal business | 228,297 | 6.83 | 5.6 | 1.22× |
| WB work business | 47,612 | 19.47 | 12.8 | 1.52× |
| HO social/recreation | 732,055 | 11.05 | 13.6 | **0.81×** |

**4.922%** of legs are under 1 km network (1.822% under 0.5 km). The issue's
figures reproduce exactly, which is expected: the demand has not been rebuilt.

### #30 / #29 — the scoring half, which has moved twice

The §9.28 arithmetic, re-run on today's emitted config. (The method reproduces
§9.28's own numbers exactly when given the values of the day, which is how it was
validated.)

| | then (12 Aug, as the issues state it) | now |
|---|---:|---:|
| walk `marginalUtilityOfTraveling` | −27.9216 | **−11.6392** |
| bike `marginalUtilityOfTraveling` | −16.05 | **−14.5226** |
| walk teleported speed | 1.05 m/s | **1.25 m/s** |
| beeline distance factor | one assumed 1.30 | **measured 1.6902 walk / 1.5231 bike** |
| utils per beeline-km, walk | 11.666 | **6.625** |
| utils per beeline-km, bike | 1.896 | **2.067** |
| **walk beats bike below** | **174 m beeline** (226 m walked) | **373 m beeline** (630 m walked) |
| **share of B2 legs inside that window** | **0.657%** | **1.816%** |

`C.constraint.trip_length_km.walk` records the observed mean walk trip as
**0.7 km network**; **2.96%** of B2 legs are shorter than that. So the scoring
repair roughly triples walk's winning window and brings the crossover just under
the observed mean trip — while the trip-length defect (#30 cause 2) still caps
what walk can reach. **Both halves matter and only one of them is still true as
written.**

### #32 — core SA1s outside the road network

Road layer's true extent from `A1_road_edges.csv`: **S −33.2550, W 151.0316,
N −32.5049, E 152.0118** — the same extent the issue quotes, so the shipped
network is still the one built inside the old rectangle.

| test | core SA1s | agents |
|---|---:|---:|
| centroid outside the road extent | **87** | **31,940** |
| geometry entirely outside it | 82 | 30,307 |
| **no road node anywhere inside the SA1** | **99** | **35,365** |

The first row is the issue's, reproduced exactly. The third is stricter and is
the one the re-harvest should be verified against.

### #34 — what the CBD rectangle actually clips

Box: S −32.9450, W 151.7250, N −32.9050, E 151.8050. The builder keeps an edge
whose **start node** is inside it.

| street | named edges | km kept | km dropped | edges straddling the boundary | nearest dropped edge |
|---|---:|---:|---:|---:|---:|
| Hunter Street | 68 | 5.18 | 5.28 | **0** | 13.58 km outside |
| Scott Street | 52 | 2.43 | 2.83 | **0** | 24.84 km |
| King Street | 128 | 5.63 | 10.28 | **0** | 1.11 km |
| Honeysuckle Drive | 24 | 2.22 | 0.47 | **0** | 28.66 km |
| Wharf Road | 16 | 1.79 | 0.09 | **0** | 14.14 km |
| Darby Street | 29 | 1.95 | 0.00 | **0** | — |
| Beaumont Street | 20 | 2.59 | 0.00 | **0** | — |

No edge of any target street has one end in and one end out, and **not one
dropped edge lies within 500 m of the box**. The dropped kilometres are
same-named streets in Maitland, Cessnock and Raymond Terrace. The rectangle is
therefore doing a job nobody wrote down — **name disambiguation** — and a
replacement that only derives an extent will pull those streets in.

`buildings_cbd.osm` (the only copy, under `osm_pre_issue32/`) spans
−32.9450…−32.9044 lat and 151.7244…151.7985 lon: the box plus about 60 m, which
is Overpass returning whole ways that cross the boundary. Nothing outside the box
was ever harvested, so question 1 of the issue is not answerable from this
package.

### #28 and #31 — read off today's specification

`cities/newcastle/scenarios/matsim/S2/WEEKDAY/config.xml`:
`qsim.mainMode = car`, `routing.networkModes = car,ride`,
`travelTimeCalculator.analyzedModes = car`,
`subtourModeChoice.chainBasedModes = car,bike`.

`src/java/citysim/CitysimControler.java` (the class `run_matsim.py` actually
launches, `MAIN = 'citysim.CitysimControler'`) binds
`addTravelTimeBinding(TransportMode.ride).to(networkTravelTime())` and the car
disutility factory. So a passenger is priced with congested car times **despite**
the config, and the residual is the one the class documents itself: ride
*experiences* congestion without *causing* it, because no ride vehicle enters the
mobsim. That residual is #31, and #31 is confirmed on three independent readings
— the config, the calculator's own javadoc, and B2's `party_size = 1` on every
leg.

### #20 and #24 — from the demand and the mapping

External tier: **10,934 legs (0.485%)**, destinations `home` 5,467, `work` 3,813,
`other` 1,654 — all inside the study area. `count_station_links.csv`: 195 rows,
111 stations, **`matched_by = name_and_proximity` on every one**. WB legs
**47,612 (2.111%)**. No freight object of any kind exists in the registry, the
builders or the run inputs.

---

## The one measurement deliberately not made, and why

**#5 needs a run, and the run is not worth making yet.**

The brief lists #5 among the cheap checks. It is not cheap on today's package,
and worse, it is not durable:

- every prior convergence curve is at **8 threads**, and `RUN.machine.threads`
  says in its own description that thread count is part of the run identity;
- the 25% pilot that was extending it is deleted, correctly — it had no
  `_run.json`;
- the shipped runnable network is the **10 August** build, which the B0
  re-harvest replaces, and §3.5 forbids comparing across builds;
- B2 is regenerated by #30, #37, #24 and #20 in that same batch.

At the measured cost (§9.5: 9.8 s/iteration at 1%, 29.9 s at 10%) a single
1,000-iteration arm is **2.7 h at 1%** or **8.3 h at 10%** — and the B0 batch
invalidates the answer the moment it lands. `STATUS.md` already orders it that
way: *"only after that is it worth re-measuring the iteration count."*

**This is a judgement call against the instruction to re-measure everything, and
it is recorded as one.** If the iteration count is wanted before B0 regardless,
the arm to run is 10% × 1,000, **alone** — three arms declared 78 GiB of heap on
a 63.5 GiB machine and paged it.

The same reasoning covers **#9** (downstream of #5) and the **residual half of
#28** (a realised-speed comparison in matched distance bins, which needs legs
from a completed run).

---

## Three defects found while measuring, outside the twelve

**1. The shipped network and the shipped road layer disagree about speed.**
`A1_road_edges.csv` (13 Aug) already carries the declared `A.road.speed_default`
— service 25, trunk 60, motorway 110. `networks/matsim/base/network.xml.gz`
(10 Aug) was built from the drifted second copy the zero-hardcoding change
deleted, and still carries the old ones: **43,174 of its 157,678 links are at
20.00 km/h**, the retired `service` default. Any run made today uses the old
speed on **27.4%** of links while the road layer says otherwise. B0 fixes this by
rebuilding; until then the two artefacts are not describing the same city.

**2. `params/C3_count_comparison.json` states a fact that is no longer true.**
Its `vehicles_per_leg` note reads *"What stays genuinely unmodelled is the escort
trip: B2 generates none."* B2 generates **327,611 HX legs and 177,025 escort
activities**, and `build_activity_chains.py` is explicit that an escort tour is
made *by the driver*. The note predates the §9.15 escort repair and was never
updated. It is in a committed parameter file, not a document.

**3. `RUN.controler.last_iteration`'s description is stale.** It says *"the
shipped scenario configs carry 100"*. They have carried **250** since `0fb61ba`.

None of the three changes a model value. All three are the same class as the
issues above: a statement that was true when written and is now checked by
nothing.

---

## What this changes about the next action

The B0 ordering in [`STATUS.md`](../STATUS.md) survives unchanged — #32 is still
first, and it is still the point of no return. What the verdicts change is the
**contents of the batch** and the **acceptance tests**:

1. **#30 loses half its scope.** It is a destination-placement issue now. The
   scoring half is repaired and must not be re-fixed.
2. **#29 must be re-measured before it is sized.** The mechanism is real and
   undeclared; the 5× is not a number to design a constraint against.
3. **#34 must not be "derived" naively.** The rectangle is load-bearing as a
   name disambiguator. Its floorspace damage is measurable only after the
   re-harvest, so #34's measurement belongs *inside* B0 after all — contrary to
   the issue's own scope note, which says D1 sits outside the point of no return.
4. **#37's acceptance covers three day types**, and the target is zero on each.
5. **#20 and #24 shrink to one part each** — through traffic and freight.
6. **#28 is not a blocker any more.** It is labelled `blocker`; the blocking
   mechanism was fixed on 12 August. What remains is a residual that only a run
   can size.

**No issue has been closed or edited on the strength of this document.** Three
verdicts (#20 part 2, #24 business, #30 cause 1) are FALSE and two more (#14,
#28) have stale bodies; those edits are proposed, not made.

---

## Addendum, 16 August — what the 4.1 rebuild resolved, measured

The B0/4.1 batch ran to completion the night after these verdicts were
written. Post-rebuild measurements against the open questions above:

| # | Post-rebuild measurement | State |
|---|---|---|
| **32** | Harvest 10/10 layers over the derived extent, every layer larger than `osm_pre_issue32/`; core SA1s with **no road node: 99 → 4, carrying 0 agents** (the stricter test this document specified). Road layer now spans 150.68–152.28 | **REPAIRED — closeable** |
| **37** | Chains capped (§9.38): **0 persons** with departures both before 06:00 and at/after 24:00, on WEEKDAY **and** SAT **and** SUN (2,609/458/286 colliding tours dropped, <0.5% of tours) | **FIXED to its own acceptance — closeable** |
| **30** | Decay now solved per purpose × home LGA (§9.40): **all 30 cells realise their own LGA's HTS distance**, including Newcastle education at 3.0 km (was 6.57) and Port Stephens shopping (unreachable pre-rebuild — its attractors were inside the clipped area; now exact at 7.2 km, direct confirmation of the #32 contamination this document hypothesised) | placement fixed; walk's sub-km recovery re-measures on the first real run |
| **20** | Through tier live (§9.41): 3 gates (M1 48,016 · Hunter Expressway 33,882 · Pacific Highway 20,701), 17,955 WEEKDAY vehicles, car-locked, single-leg between distinct gates (now a package check). Northern exits ungated — recorded limitation, swept | V113 non-zero confirms on the first run |
| **29** | Asymmetry declared and constrained (§9.39): `bikeAvail` drawn at 0.50 (swept 0.30–1.00), seed share bike 0.113 vs walk/pt 0.26 | magnitude re-measure before sizing, as this document required |
| **34** | The floorspace question this document called unanswerable is answered: the new corridor-extent buildings layer holds **2,303 buildings outside the old box; the nearest is 281 m** from any frontage segment against a 50 m attribution ceiling. The box clips nothing; its name-disambiguation role stands | measured; portability fix stays low-priority |
| defect 1 | The network/road-layer speed disagreement is gone: the rebuilt network takes the declared speeds (service 25 km/h on 50,226 links; 455 residual 20 km/h links are observed maxspeed tags) | closed by the rebuild |
| **5/9/28** | Now unblocked: run inputs regenerated, package gate green, smoke run rc=0 (median iteration 10.1 s at 1%, was 9.8) | the 4.2 run campaign measures them |

Also surfaced and fixed during the batch, same stale-extent class as #32: the
**DEM tile list was typed in** with the old extent's comment, so the rebuilt
network's western and eastern strips had no elevation source (93.5% road
coverage). The tile set is now derived from the boundary + harvest margin;
coverage is 100% on roads and footways.
