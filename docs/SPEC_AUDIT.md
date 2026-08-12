# Specification audit — where the logic can be silently wrong

**P4 deliverable 0a.** Output of walking population → activities → tours → mode
choice → network → scoring → metrics → fit, asking at each joint: *what would be
wrong if this were wrong, and would we see it?*

Ranked by how much each could move the headline, not by how easy it is to fix.
Every finding here is **verified against the package or a completed run** — the
evidence column says how. Nothing in this document changes a parameter.

**Why this ran first.** Mode share is car **32.5%** against an observed **59.0%**
and car passenger **50.0%** against **20.6%**. The §9.15 demand repair moved car
1.69 points. Adding demand on top of an unexplained error makes it harder to
find, not easier.

The symptom, in full, from `results/S2_WEEKDAY_f01_i250_s20260810/_metrics.json`
(Newcastle LGA, linked trips):

| mode | modelled | observed | gap |
|---|---:|---:|---:|
| car | 32.54% | 59.0% | **−26.5** |
| ride | 50.03% | 20.6% | **+29.4** |
| walk | 0.75% | 13.4% | **−12.7** |
| bike | 15.86% | 3.2% | **+12.7** |
| pt | 0.83% | 3.8% | −3.0 |

**Two near-exact inversions, not five independent errors.** Car↔ride is −26.5/+29.4
and walk↔bike is −12.7/+12.7. That pattern says two structural asymmetries, each
moving a pair, rather than five miscalibrated constants. Findings A1–A4 below are
those asymmetries.

---

## A1 — `ride` is routed on the network but never simulated in it · **critical**

**What is wrong.** `config.xml` sets `qsim.mainMode = car` while
`routing.networkModes = car,ride`. A mode in `networkModes` but not in the mobsim
is routed over the network graph and given **free-flow link times**: it never
queues, never waits, and never contributes to the congestion it should be part of.

**Evidence — realised speeds from `output_legs.csv.gz`, 250-iteration run:**

| mode | legs | mean km | mean min | mean km/h |
|---|---:|---:|---:|---:|
| **ride** | 122,025 | 13.46 | 13.4 | **55.7** |
| **car** | 66,604 | 10.02 | 10.9 | **49.3** |

**A car passenger arrives faster than the car they are sitting in.** That is not
a calibration error; it is physically impossible.

**Correction to this finding's headline, made on re-checking.** The 13% above is
an aggregate over legs of different lengths, and ride legs are longer (13.46 km
against 10.02 km) while longer trips use faster roads — so composition inflates
it. Controlling for distance, the advantage is smaller and **more damning,
because it is present in every bin**:

| leg distance | car km/h | ride km/h | ride/car |
|---|---:|---:|---:|
| 0–2 km | 39.7 | 42.7 | 1.08× |
| 2–5 km | 44.1 | 47.9 | 1.08× |
| 5–10 km | 48.3 | 52.1 | 1.08× |
| 10–20 km | 54.7 | 58.0 | 1.06× |
| 20–40 km | 63.6 | 66.4 | 1.04× |
| 40 km+ | 69.4 | 72.4 | 1.04× |

**4–8%, consistently positive at every distance.** A composition artefact would
not survive stratification; this does. The defect is real and the aggregate
figure was the wrong way to state it.

**Why it is invisible.** The scoring parameters make ride look *unattractive* —
car and ride carry identical `marginalUtilityOfTraveling` (−10.9608) and
identical `monetaryDistanceRate` (−0.00018, the §9.17 departure), and ride
carries a −0.85 constant against car's 0.0. Anyone reading the scoring config
concludes ride is dominated. The advantage lives entirely in the mobsim
configuration, three modules away.

**It also gets worse where it matters most.** The free-flow advantage is largest
exactly where car is most congested — the peak, and the corridor. So the defect
biases the corridor result, which is the study's subject.

**VERIFIED AND LARGELY FIXED (§9.26).** Binding `ride` to the congested car
travel time moved **car 32.54 → 52.30%** and **ride 50.03 → 29.45%** against a
like-for-like baseline, closing the gap to target from 84.2 to 44.6 pp — and it
left walk↔bike untouched (−0.03 / +0.81), confirming these are two independent
inversions. **Not eliminated:** ride is still 1.01–1.11× faster at matched
distance, worst on short trips, so #28 remains open on the residual.

**Do not fix by tuning `asc_car_passenger`.** §8.5 and proposal §9 name ASC
absorption as the primary threat to validity, and #9 already holds that constant
provisional. A constant that absorbs this would hide it permanently.

---

## A2 — `ride` is not chain-based, `car` is · **high**

**What is wrong.** `subtourModeChoice.chainBasedModes = car,bike`. A subtour
that adopts `car` must conserve it across every leg — the vehicle has to come
home. `ride` carries no such constraint, so any subtour can switch to ride
freely, in one leg or all of them.

**Why it matters.** This is a second asymmetry pushing the same way as A1, and
it is not obviously wrong: `ride` genuinely is not a vehicle the traveller owns.
But combined with A1 it means ride is both cheaper to adopt and faster once
adopted.

**Would we see it?** No. It shows up only as a share.

**Note the interaction with §9.11.** Ride availability was constrained to agents
with a potential driver in the household — a *choice-set* constraint. No driver
is required to actually make a matching trip in the mobsim, so a household's
single driver can chauffeur an unlimited number of simultaneous passengers.

---

## A3 — car and ride carry availability constraints; bike carries none · **high**

**Evidence — uninformed seed shares from `_plans_report.json`**, which are
uniform over each person's *available* modes:

| mode | seed share | implied availability |
|---|---:|---:|
| walk | 22.68% | 100% |
| bike | 22.67% | ~100% |
| pt | 22.70% | 100% |
| **ride** | 16.24% | ~72% |
| **car** | 15.72% | ~69% |

**Car is the only mode whose ownership is modelled, so it is the only mode that
can be denied to an agent.** Bike is available to everyone, always. Against an
observed bike share of 3.2%, the model returns 15.86%.

This is a structural bias against car in the choice set itself, before any
scoring happens. Whether a bike-availability constraint *should* exist is a
modelling decision — the census carries no bicycle-ownership variable — but the
asymmetry is currently undeclared and unlabelled.

---

## A4 — walk is 18× under-represented, and trip lengths are why · **high**

**RESOLVED since this register was written — cause 2 confirmed, and sufficient
on its own.** Observed walk trips average **0.7 km** and are 13.4% of all trips;
the model carries only **4.9% of trips under 1 km**. Walk cannot reach its
observed share because the trips are not there to be won, which caps it near 5%
before mode choice is consulted. It is destination *placement*, not a uniform
stretch: education is **2.19×** too long (6.57 km against an observed 3.00 km),
commute 1.50×, while social/recreation is 0.81× — too *close*. Purpose shares
themselves are good. Full working in issue #30.

The original two candidates, kept for the record:

1. **Scoring.** Walk's time disutility is −27.92 util/hr against bike's −16.05,
   at 3.78 km/h against 15.1 km/h. Beyond roughly a kilometre bike dominates
   walk by a wide margin, so walk can only win on very short trips.
2. **Trip lengths.** Modelled mean trip distance is 6.33 km by car and 5.78 km
   by bike. If B2 places destinations systematically too far away, the short
   trips that walk should win **do not exist to be won**.

**Cause 2 is the one to test first**, because it would also inflate bike, and
A3 shows bike is inflated by the same 12.7 points walk is deficient. Test:
compare the modelled trip-length distribution against the HTS
`JOURNEY_AVG_DISTANCE` by purpose, which is already in
`data/processed/hts/hts_purpose_newcastle.csv` and is **not** a holdout row.

---

## B1 — issue #24's business-travel premise is false · **high, and it prevents damage**

**Issue #24 states that work-related business travel is "an observed HTS purpose
the model does not generate". It does generate it.**

| | value |
|---|---|
| B2 weekday legs with `purpose = WB` | **47,612** of 2,255,047 = **2.11%** |
| MATSim `business` activities | 23,806 |
| HTS Newcastle LGA 2024/25, *Work related business* | **2.0%** of journeys |

The model is within 0.1 pp of the observed share. **Building this deliverable as
written would double-count an already-correct purpose**, moving mode share for a
reason nobody would later be able to attribute — the exact failure mode this
audit exists to catch.

The freight half of #24 is unaffected and stands: there is no heavy-vehicle
layer, and `B.counts.heavy_vehicle_share` (0.0652) is the only freight-adjacent
value in the registry.

Issue #20 also stands: external-tier legs are **10,934 of 2,255,047 (0.48%)**,
and every one terminates at a `home` or `poi` destination inside the study area.
Nothing passes through.

---

## C1 — `consumers` metadata is stale, so it cannot evidence reach · **medium**

The registry's `consumers` list is generated from read logging, not maintained
by hand, and it is **out of date**. `A.lightrail.capacity_total`,
`capacity_seated` and `capacity_standing` all list no consumers, but
`src/build/build_matsim_run_inputs.py:197-198` reads two of them.

**Why this matters more than it looks.** "A declared, swept parameter that
reaches nothing" is a defect class this project has hit three times, and
`consumers` is the mechanism used to detect it. An empty `consumers` currently
means *"the generator has not seen this field"*, not *"nothing reads it"* — so
it can neither confirm nor deny reach. Any reach claim must be made by changing
the value and observing the output.

*(Checked and cleared: `C.crowding.seated_multiplier` / `standing_multiplier`
also list no consumers, but `build_matsim_run_inputs.py` documents them as inert
by construction with a stated reason. Labelled, not orphaned.)*

---

## C2 — undeclared constants in `build_corridor_layers.py` · **medium**

The script filters signals to within **60 m** of the alignment and clusters OSM
nodes within **45 m** into one intersection. Both decide how many corridor
intersections exist — `n_corridor_signals = 14` is a direct output of them — and
neither is in the registry. The script now reads the registry (§9.24), so the
wiring exists; these two constants were not migrated with it.

---

## D1 — deliverable 0e is already satisfied · **housekeeping**

0e asks that the `water` and `green` OSM layers be labelled visual-only so they
never read as orphaned inputs. They already are: `src/extract/overpass.py`
annotates both *"for the run replay basemap only"*, and both are consumed by
`src/analyse/build_basemap.py`, which feeds `build_replay_page.py`. No work is
outstanding; the checklist entry is stale.

---

## What this audit did not cover

Stated so the gaps are not mistaken for clean results:

- **Fit statistic and target attribution** were not re-walked; #14 and the
  67/143 split were left untouched, and no holdout row was opened.
- **A4's two candidate causes were not separated.** That needs the trip-length
  comparison named above.
- **PT at 0.83% against 3.8%** was not investigated. It is the smallest gap and
  is plausibly downstream of A1–A3 rather than independent, but that is an
  assumption, not a finding.
- **Network and scoring translation** were read as configured, not re-derived
  from C1.
