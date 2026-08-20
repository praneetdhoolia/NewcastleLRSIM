# Physical ride — the mechanism options, their recorded costs, and what must be measured before choosing

**Evidence dossier for issue #48 (owner directive, DECISIONS.md §9.51 priority 1).
Research record — no mechanism is chosen here; the choice is the owner's, and
three of the four options below still need a measured probe before they can be
costed honestly.**

The directive: *every ride trip is a passenger physically in a car — no
exceptions, no teleportation — and the ride share tuned to real life.*

---

## 1. The state being superseded, in numbers

| quantity | value | source |
|---|---:|---|
| Modelled ride share (Newcastle LGA linked) | 31.05% | §9.48, `bind1000_25pct` |
| Observed ride share | 20.60% | HTS, calibration target |
| Occupancy, modelled | 0.4855 pass/driver | §9.48 — OUTSIDE [0.2493, 0.394], flattering direction |
| Ride trips OD-coincident with a household car trip (any time) | 15.31% | §9.48 |
| Ride trips actually PAIRED (declared regime, ±15 min, both links) | **1.30%** | §9.48 |
| Ride trips physically in a vehicle | **0%** | §9.44 — a paired passenger inherits a clock, occupies no seat |

The two halves of the directive are one mechanism: **a physical-service
constraint is the tuning** — ride demand that no driver can physically carry
must re-mode, which caps ride at what the driver supply supports.

## 2. The hard facts any mechanism must survive

1. **Vanilla MATSim qsim boards no passengers into private cars.** A person
   is a driver or is teleported; multi-occupant private vehicles need one of
   the extensions below or a custom engine.
2. **socnetsim (joint plans) was measured at ~10× runtime** on this model
   (`CourtesyEventsGenerator`, 16.7 M events) and reverted by owner
   instruction. The directive re-opens the question; it does not repeal the
   price. A 1000-iteration 25% arm at 10× is ~15 days — that number is what
   any re-adoption must confront.
3. **eqasim's `PassengerConstraint` consults no driver** — it compiles,
   runs, constrains nothing (recorded trap; do not re-test it).
4. **26.2% of households are lone-person: 64,334 people with no possible
   in-household driver, ever.** Non-household lifts have **no observation**
   (who drives whom outside a household is unrecorded anywhere). Under "no
   exceptions", their ride demand must re-mode — see §4.
5. **The demand already co-locates escort pairs exactly** (§9.46: 121,621
   weekday escort tours bound to a household member's trip, destination and
   departure identical). The raw material for joint vehicle plans exists at
   build time.
6. The §9.48 realisation gap (15.31% coincident → 1.30% paired) has three
   named, unmeasured components: mode co-assignment (the escorter must draw
   `car` and the escortee `ride` the same day), the ±15 min window applying
   to *realised* not planned departures, and `both_links` link resolution.
   **Measuring their individual sizes is the first research task** — it
   bounds how much any engine can pair.

## 3. The mechanism options

### A — socnetsim / joint plans (the known-cost incumbent)

Full physicality with joint scoring and joint replanning. **Cost is the
problem and it is measured**: ~10×. Also a §14-class toolchain surface (the
contrib's compatibility with the pinned MATSim must be re-verified).
*Probe needed:* none for cost (already measured); re-measure only if a
smaller-scope configuration (joint plans for bound escort pairs ONLY, not
all social ties) is hypothesised to be cheaper — plausible, unmeasured.

### B — DVRP (household car as a one-vehicle fleet)

The DVRP/DRT machinery physically boards passengers today. Repurposing it:
each household vehicle is a fleet of one, serving that household's ride
requests. *Concerns to research:* dispatch semantics (DVRP optimises vehicle
routing; a parent's day is not a dispatch problem), the driver's own
activity plan vs the fleet abstraction (DVRP drivers are not agents with
jobs), and cost at 25%. *Probe needed:* a 1% × 3-iteration plumbing probe
with one household as a fleet — likely a structural mismatch discovered
cheaply.

### C — demand-level joint vehicle plans + a boarding engine (build on §9.46)

Since bound pairs already share exact OD and departure, write the pair into
**one vehicle** at build time: the escorter drives, the escortee's leg
carries the escorter's vehicle id, and a qsim extension boards the passenger
into the moving vehicle (enter/leave at the shared activity ends). This is
the narrowest engine that satisfies "physically in the car": no dispatch, no
joint replanning — the pairing is fixed in the demand, exactly where §9.46
already decides it. *Costs to research:* the Java engine (a passenger
`MobsimAgent` that waits for and rides a named vehicle — the DRT passenger
handling is the pattern to copy, ~one focused Java class by analogy with
`RidePairingEngine`); the replanning interaction (SubtourModeChoice must not
split a joint pair — `lockedMode` and the availability calculator are the
existing levers). *Probe needed:* 1% × 3 iterations, measure: passengers
board, travel times equal the driver's, cost per iteration.

### D — no engine: demand-side hard pairing with re-moding (the floor option)

Keep teleportation OUT by never generating an unservable ride: extend the
§9.46 binding to ALL ride demand (not only escort) — a ride trip exists only
where a same-household driver trip coincides — and re-mode the rest at
generation. The paired passenger still needs C's engine to be *physically*
in the car, so D alone does not meet the directive; it is the demand half
that A/B/C all need anyway.

## 4. The re-moding question (the directive's hardest consequence)

Under "no exceptions", ride demand that cannot pair must become another
mode. Measured bounds: 15.31% of current ride trips are OD-coincident at any
time — the pairing ceiling under household-only service is therefore FAR
below the observed 20.6% ride share, because **real life contains
non-household lifts and the package holds no observation of them**. The
owner must choose, explicitly:

- **(i)** ride = household-servable only → modelled ride lands well UNDER
  the observed 20.6%, and the gap is REPORTED as the unobserved
  non-household-lift share (honest, conservative, no invention); or
- **(ii)** a declared, swept non-household-lift allowance (a new assumed
  parameter with no observation behind it — the no-invented-data rule
  requires it be swept wide and stated as unvalidatable).

Option (i) is the one consistent with this project's rules; it must be put
to the owner with the number measured (what share of ride demand CAN pair
once mode co-assignment is forced — unmeasured today).

## 5. Recommended research sequence (measurements, not builds)

1. Decompose the ×12 realisation gap (§2.6) — sizes of the three components,
   from `bind1000_25pct`'s events (no new run).
2. Measure the household-pairing ceiling: with mode co-assignment forced in
   the DEMAND (escorter `car`, escortee `ride`, same day), what share of
   observed-level ride demand is servable? (Build-time analysis of B2+B1,
   no run.)
3. Probe C's engine at 1% × 3 (the only new Java); probe B only if C's
   probe fails structurally.
4. Bring the owner: the mechanism (likely C), the re-moding policy (i vs
   ii), and the run plan with costs. **Then** build.

*Nothing in this dossier is a result. No run was made for it; every number
traces to §9.44–§9.51 or the demand artefacts.*
