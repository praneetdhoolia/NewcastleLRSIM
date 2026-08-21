# Non-household lifts — closing the reported gap physically

*21 August 2026. The owner directed (superseding the §9.55 report-only
stance): FIX the non-household-lift gap. This dossier records the option
analysis and the mechanism built (DECISIONS.md §9.60). Nothing here is a
result; every number below is an input, a measured diagnostic of an aborted
run, or a published observation.*

## 1. The gap, decomposed

Observed all-purpose `Vehicle passenger` share: **20.60%** (V205, calibration
split). Household OD-coincidence caps intra-household pairing at **15.31%**
of ride trips (§9.48); the declared regime realises 1.30%; with §9.55
re-moding on, emergent ride sat at **0.26–0.31%** through the aborted arm's
first 135 iterations. The missing mass is:

- **(a) intra-household lifts the realised-departure window misses** — the
  measured ×6.91 layer of the §9.53 gap decomposition (driver's car already
  gone, or not yet there, when the passenger departs);
- **(b) non-household lifts** — friends, neighbours, colleagues,
  non-resident drivers — for which the data grade is **NO TARGET AT ALL**:
  nothing held records who drives whom.

## 2. The one under-used asset

B2 already generates **serve-passenger (HX) driver tours at the observed
rate** (driver-side `Serve passenger` is 10–19.5% of journeys by LGA-year —
an OBSERVED input, not an assumption). §9.46 binds them to household member
trips — **68.6% bind; the rest drive to a drawn attractor serving nobody**,
because lone-person and single-driver households have nobody to bind to.
Meanwhile the people those drivers exist to carry — the driverless-household
class — generate ride demand that household pairing structurally cannot
serve. The unbound HX supply and the unservable ride demand are the same
phenomenon seen from two sides.

## 3. Options considered

| | mechanism | new assumed values | observed anchor | verdict |
|---|---|---|---|---|
| M0 | **Wait for the driver**: a booked passenger whose car is not at the link yet physically waits, bounded by the declared pairing window; boards on arrival; timeout completes on the Tier-1 clock from the timeout | **0** (reuses `B.ride.pairing_window_min`) | household car trips (existing) | **BUILT** |
| M1 | **Non-household escort binding**: re-target unbound HX tours to driverless-household passengers — tour becomes home_d → passenger origin (pickup) → passenger destination → home_d, serving leg departing at the passenger's own departure EXACTLY, so the runtime pairing matches it under the unchanged declared rule and window | 1 categorical scope (`B.activity.escort_binding_nonhh_scope`, swept `household_only`/`same_zone`) | **Serve passenger 10–19.5%, observed** — adds NO tour, re-aims existing ones | **BUILT** |
| M2 | **Driver-detour lifts**: match residual unpaired rides to existing car drivers within a declared detour bound; the car physically drives the detour and the driver arrives late | detour bound (literature, swept) + candidate scope (assumed, swept) | none — emergent, swept | **DEFERRED** — gated on M0+M1's measured shortfall at the next converged arm |
| M3 | Declared lift allowance (teleport or phantom driver) | 1 unvalidatable share | none | **REJECTED** — violates no-teleportation and no-invented-data directly |

## 4. What was built (§9.60)

- **M0** in `JointRideEngine` (`ridePairing.waitForDriver` ←
  `B.ride.wait_for_driver`): a waiting registry at the meeting point; board
  on the car's arrival; give up after the declared window and complete on
  the Tier-1 clock counted from the timeout — waiting costs what waiting
  costs. Counted: `waited(boarded, timedOut)`.
- **M1** in `build_activity_chains.bind_nonhousehold_lifts` (a second pass
  after each day file closes): deterministic, drawless matching of unbound
  HX anchor tours to driverless-household anchor trips within the declared
  scope, passengers ranked as the §9.46 binder ranks (unlicensed education
  first). The re-timed tour goes through `time_tour` twice (offset probe,
  then pinned), so no speed or overhead constant is restated. Infeasible
  re-timings (collision with the driver's other tours, pre-dawn start, the
  #37 cap) are SKIPPED and the original tour kept. Writes
  `B2_lift_bindings_<day>.csv`.
- **The runtime coupling**: `build_matsim_plans` grants a bound passenger
  `rideAvail` (the availability identity is satisfied by construction — a
  driver now exists) and stamps `liftHousehold`; `RidePairingEngine` widens
  that passenger's candidate search to the driver's household, own household
  first. The binding is an ELIGIBILITY for the declared pairing, never a
  guarantee — the driver's leg must still match under rule and window, the
  boarding is still physical, and an unserved leg still re-modes to walk.
- **Sampling integrity** (`sample_population`): a binding couples two
  households, which independent household sampling would sever with
  probability 1−fraction (the §9.45 defect class one level up). Households
  joined by a binding are unioned into one sampling cluster hashed on a
  canonical representative: kept or dropped together, inclusion probability
  unchanged, the §9.45 variance price stated.

## 5. What this deliberately does not do

No target is touched; the 67/143 split is untouched; the household/
non-household split of boarded lifts is REPORTED (ride_pairing.csv), never
fitted — no observation of who-drives-whom exists to fit it to. Commute
carpooling must stay rare (G62: car-as-passenger 3.35% of JTW): the priority
order concentrates lifts on unlicensed and education trips, and the G62
check reports the commute split rather than constraining it. M2 stays
unbuilt until a converged arm shows what M0+M1 leave unserved; occupancy is
reported against its declared observed range [0.2493, 0.394].
