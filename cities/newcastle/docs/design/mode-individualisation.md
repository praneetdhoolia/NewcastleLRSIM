# Mode individualisation — every mode's own observed share, and the three tiers of "distinct"

**Evidence dossier for issues #49 and #50 (owner directives, DECISIONS.md
§9.51 priorities 2 and 4). Research record — measured anchors and costed
tiers; the build order is the owner's call.**

The directives: *all 9+ modes distinguished and unique — never under a `pt`
or `Other` umbrella; motorbike and taxi/rideshare individualised* (#49), and
*mode distributions across age groups, jobs, etc. matching real life* (#50).

---

## 1. The observed anchors, measured from held data (20 Aug 2026)

`census2021_G62_SA1.csv`, one-method journeys to work, the 1,500 core SA1s,
**179,761 journeys** (2021 Census):

| mode | journeys | share of one-method JTW |
|---|---:|---:|
| Car as driver | 157,832 | 87.801% |
| Car as passenger | 9,430 | 5.246% |
| Walked only | 4,383 | 2.438% |
| Truck | 1,618 | 0.900% |
| Bus | 1,178 | 0.655% |
| Bicycle | 903 | 0.502% |
| **Motorbike/scooter** | **653** | **0.363%** |
| Other | 605 | 0.337% |
| Train | 231 | 0.129% |
| Taxi/Rideshare | 56 | 0.031% |
| Tram/light rail | 52 | 0.029% |
| Ferry | 40 | 0.022% |

**Every mode the directive names now has an observed commute number.** Two
caveats that must travel with this table: (a) **2021 was a COVID census** —
car share is WFH-inflated and PT collapsed (bus 0.655% against HTS-era PT
shares near 3.8% of all trips); treat these as *structure* (relative submode
splits, motorbike:car ratios), not as level targets, and prefer the 2016 JTW
for pre-COVID levels if acquired. (b) JTW is **commute only**; all-purpose
shares for motorbike and taxi remain unobserved (HTS `Other` excludes
motorcycle — it sits inside Vehicle driver/passenger, so carving motorbike
out SHRINKS the car and ride targets and both must be restated together).

## 2. The three tiers of "distinct", cheapest first

### Tier R — reporting (days, no model change, no new family)

Bus/train/LR/ferry realised shares from the events: the fleet is already
physically distinct (1,448/332/252/107 vehicles) and `pt_boardings` per line
exist. Work: split `mode_share`/`trip_geometry` pt rows by the boarding
vehicle's type; report motorbike/taxi as `not modelled` rows rather than
silence. **No comparability break.** This alone ends the `pt` umbrella in
every report.

### Tier C — choice-distinct (the constants already exist)

C1 declares asc_bus −1.05, asc_lr −0.75, asc_rail −0.65 — and the MATSim
translation collapses them to one `pt` (§9.3 `not_representable`). Research:
SwissRailRaptor's mode-mapping (`useModeMappingForPassengers` +
per-submode `modeParams`) lets scored PT legs carry their submode. Must be
verified against the pinned build's bytecode, not the docs (the §9.44
discipline). **A scoring change → a new comparability family**; sequence
with #48's break, not separately.

### Tier P — physically new modes

- **Motorbike**: generated in B2 (it is not today), routed and simulated as
  a qsim main mode at literature PCE (~0.5–0.75 — a motorbike consumes LESS
  than a car; the §9.49 vehicles-file machinery takes a third type in one
  line). Target: the observed 0.363% JTW anchor for commute; all-purpose
  share declared and swept. Every step has the §9.49 freight change as its
  template — this is now a solved pattern.
- **Taxi/rideshare**: the §9.42 dossier and
  [`point-to-point-mode.md`](point-to-point-mode.md) stand (teleported
  priced mode; IPART band 10k–35k trips/day as a constraint, never a
  target). JTW 0.031% confirms commute is negligible — the mode matters for
  the all-purpose band, exactly as §9.42 records.

## 3. #50 — the demographic inventory, measured

What is actually HELD, checked table by table (20 Aug):

| observable | held? | where |
|---|---|---|
| JTW mode × **sex**, SA1 | ✅ | G62 (`_M`/`_F`/`_P` columns) |
| JTW mode × **age** | ❌ **not held** | ABS TableBuilder / a further DataPack table — a named ACQUISITION, not a modelling gap |
| HTS mode × age / income / employment | ❌ not in the held slices | `hts_mode.csv` carries no demographic column (LGA aggregates); TfNSW publishes some age tables — acquisition to research |
| Population age × employment × geography | ✅ | G46 (§9.47 — already IN the model) |
| Occupation × age × sex, SA1 | ✅ | G60 (not yet consumed by anything) |
| Industry × age × sex, SA1 | ✅ | G54 (not yet consumed) |

**The model side needs no acquisition**: every agent already carries age,
sex-free employment status, licence and household attributes (§9.47), so
modelled mode × demographic tables are one events-join away from any
completed run. The comparison's OBSERVED side is the bottleneck: today it
supports mode × sex (commute) only. First build: the modelled
mode × age-band × employment table from the next valid run + the G62
mode × sex comparison; file the mode × age acquisition as its own tracked
item. **New observables enter as constraints, never targets** (§9.8/§9.13);
the 67/143 split does not move.

## 4. Suggested order, for the owner to confirm

1. **Tier R now** (no break, days) — ends the umbrella in reporting.
2. The **mode × sex comparison + acquisition list** for #50 (no break).
3. **Tier P motorbike + Tier C submode scoring** batched WITH #48's
   comparability break — one family boundary instead of three.
4. Taxi/rideshare per the standing 4.4 plan, in the same batch.

*Nothing here is a result. All numbers trace to G62, the HTS slices, C1,
§9.3, §9.42, §9.47–§9.51.*
