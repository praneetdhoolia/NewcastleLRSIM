# NewcastleLRSIM

A counterfactual microsimulation of the **Newcastle (NSW) light rail** as a transport
intervention — MATSim for the five-LGA regional demand model, SUMO for the corridor.
It exists because that estimate was never produced and the business case is not
inspectable.

> **Nothing in this repository is a result.** No scenario has been run to a reportable
> state. The network, the mapped schedules, the SUMO corridor, the synthetic population,
> the activity chains and the 30 assembled scenario × day-type run-input sets are all
> **inputs**. See [`cities/newcastle/docs/STATUS.md`](cities/newcastle/docs/STATUS.md) for the board and the next action.

---

## Run a scenario

```bash
python run.py --list        # what is runnable: scenarios, day types, run overlays
python run.py --dry-run     # resolve every input, print it, execute nothing
python run.py               # a SMOKE run: S2, weekday, 1% sample, 2 iterations
```

A real run names its own overlay, or its own iteration count:

```bash
python run.py --run-config ride_fix_10pct --tag my_run
python run.py --scenario S3 --day SAT --fraction 0.10 --iterations 1000 --tag s3_sat
```

| Flag | What it does |
|---|---|
| `--scenario` | `S0`–`S6` (default `S2`). `--list` shows which have assembled inputs |
| `--day` | `WEEKDAY`, `SAT` or `SUN` |
| `--run-config TAG` | a committed run overlay — **the reproducible way to vary a run** |
| `--fraction` `--iterations` `--threads` `--xmx` `--seed` | registry overrides, checked against each field's declared sweep |
| `--tag NAME` | names the run directory. **Always tag a re-run** — an untagged re-run overwrites the previous one |
| `--set KEY=VALUE` | a raw MATSim config override, e.g. `ride.constant=-3.4` |
| `--dry-run` `--list` `--no-metrics` `--force` | resolve-only, list, skip metric extraction, ignore an existing run record |

**`run.py` will not invent an iteration count.** `RUN.controler.last_iteration` is
declared `unobtained` in the registry — 100 and 250 are both *measured* to be too low
and no justified value has been established — so a bare `python run.py` falls back to
the committed `smoke` overlay (2 iterations) and says loudly that nothing it produces
is a result. That refusal is the house style: an input nobody has measured never
acquires a point value by being read.

After a run:

```bash
python src/analyse/run_view.py --run results/<name>   # live + replay view, congestion map
python src/run/prune_run.py --run results/<name>      # reclaim the per-iteration output
```

### Before the first run

```bash
pip install requests pandas numpy shapely pyproj lxml geopandas pyogrio rasterio openpyxl
python src/setup/bootstrap_toolchain.py     # JDK 25, pt2matsim 26.6, SUMO 1.27.1 -> .tools/
python tests/check_manifest.py              # the committed subset is intact
```

Python 3.11+. The toolchain is ~1.4 GiB, gitignored, and **pinned by sha256** —
`--verify` re-checks the digests and compiles the Java entry point without downloading.
A toolchain change is a model change.

---

## What is here

| | |
|---|---|
| Files in the manifest | **376** ([`data/MANIFEST.csv`](cities/newcastle/data/MANIFEST.csv): hash, rows, producing script, source, licence, retrieval date) |
| Package on disk | ~4.7 GB across `data/`, `networks/`, `schedules/`, `demand/`, `scenarios/` — mostly gitignored and regenerable |
| Study area | Newcastle, Lake Macquarie, Maitland, Cessnock, Port Stephens — 4,086 km² |
| Zones | 1,500 core SA1 + 201 external SA1, 222 core DZN |
| Population | 611,915 (2021 Census) → 612,680 synthetic agents |
| Road network | 43,112 edges, 9,207 km, gradient-attached |
| Active network | 35,653 edges, 6,325 km, directional walk-speed factors |
| PT | 5 GTFS eras + 10 scenario variants, 15 feeds mapped, 0 unmapped stops |
| Input registry | 210 controllable fields, each with units, provenance and a sweep or a held-fixed rule |
| Validation | 210 targets, pre-registered 67 calibration / 143 holdout |
| Base year | 2026 · CRS EPSG:28356 (GDA94 / MGA Zone 56) |

⚠ **`networks/osm/` is currently empty.** The issue #32 re-harvest has not been re-run,
so `tests/check_package.py` cannot pass and the manifest carries 376 files rather than
386. [`cities/newcastle/docs/STATUS.md`](cities/newcastle/docs/STATUS.md) holds the procedure and the checks.

---

## Documentation

| | |
|---|---|
| [`cities/newcastle/docs/STATUS.md`](cities/newcastle/docs/STATUS.md) | **The board** — phase state, deliverables, next action. Read first |
| [`cities/newcastle/docs/DECISIONS.md`](cities/newcastle/docs/DECISIONS.md) | **Every value that is not observed**, with its rationale and sweep range. Start at its own index |
| [`docs/README.md`](docs/README.md) | The **framework's** documentation and the portable input contract |
| [`.claude/CLAUDE.md`](.claude/CLAUDE.md) | Conventions and hard constraints for anyone (human or agent) changing this repo |

**Read [`cities/newcastle/docs/DECISIONS.md`](cities/newcastle/docs/DECISIONS.md) before using any of this.** It records
every assumed value, its sweep range, and four corrections to premises stated in the
research proposal.

---

## Layout

**The framework is city-agnostic; everything Newcastle-specific lives under
`cities/newcastle/`.** That split is the point: `config/schema/` states what *any*
city must supply, and a city directory is one instance of it.

```
run.py                       run a scenario
config/schema/               PORTABLE: what any city must supply, and in what shape
src/city.py                  resolves which city's inputs a run reads
src/build/                   layer construction (the reproduction pipeline)
src/run/                     the run harness
src/calibrate/               fit and calibration
src/analyse/                 metrics, run view, replay
src/registry/                the registry resolver, validators and docs generator
tests/                       check_manifest.py (CI) and check_package.py (local)
results/                     run outputs (gitignored)

cities/newcastle/            ONE CITY - every Newcastle/NSW/Australia-specific input
  registry/                  the 210 declared values, with units, provenance, sweeps
  overlays/scenarios|day|runs  per-scenario, per-day-type and per-run value overlays
  extract/                   acquisition adapters: ABS, TfNSW Open Data, Overpass
  build/                     builders that encode THIS city's intervention,
                             corridor, history and statistical geography
  docs/                      THIS city's study: STATUS, DECISIONS, design,
                             audit, handover and the generated reference
  geometry/                  declared extents that were once typed into scripts
  data/raw/                  immutable downloads + provenance_*.json
  data/processed/            zones, census, hts, observed, network, corridor, landuse
  data/MANIFEST.csv          every file: hash, rows, producing script, source, licence
  networks/                  OSM extracts, the MATSim network and variants, SUMO corridor
  schedules/                 GTFS era feeds + scenarios/S0..S6 variants
  demand/                    synthetic population (B1) and plans (B2 tours, MATSim plans)
  params/                    C1 behavioural parameters + the sensitivity sweep grid
  scenarios/                 E1 scenario configs + matsim/ assembled run inputs
```

Paths inside a city are recorded city-relative — `data/processed/network/...`, not
`cities/newcastle/data/processed/network/...` — so the same manifest row means the
same thing in every city. `src/city.py` is the only module that knows where a city
lives; the city is selected by `CITYSIM_CITY` (default `newcastle`).

---

## Reproducing the data package

Every derived file is regenerable by a committed script from the immutable raw
downloads, seeded (`20260810`) and deterministic — with one measured exception:
**pt2matsim's schedule mapping is not reproducible run to run**. About 18% of transit
route link sequences differ between identical builds while 100% of stop-to-link
assignments hold, so **any scenario comparison must use a single build of the network**
([`cities/newcastle/docs/DECISIONS.md`](cities/newcastle/docs/DECISIONS.md) §3.5).

```bash
# --- acquisition (network-bound, ~2 GiB) ---
python cities/newcastle/extract/overpass.py                  # OSM, 10 themed extracts over 8 tiles
python cities/newcastle/extract/fetch_gtfs.py                # era GTFS from the TfNSW S3 archive
python cities/newcastle/extract/fetch_open_data.py           # Opal, traffic counts, HTS
python cities/newcastle/extract/fetch_abs_dem.py             # ABS boundaries, census, DEM

# --- clipping ---
python cities/newcastle/extract/extract_zones.py
python cities/newcastle/extract/extract_census.py
python cities/newcastle/extract/extract_hts.py
python cities/newcastle/extract/slice_newcastle.py

# --- layer construction ---
python cities/newcastle/build/build_era_feeds.py             # A3 era variants
python src/build/build_network_layers.py        # A1, A2, A5, A6
python src/build/attach_gradient.py             # gradient onto A1 and A6
python src/build/attach_speed_zones.py          # TfNSW regulated speed zones
python cities/newcastle/build/build_corridor_layers.py       # A4 + corridor A2
python cities/newcastle/build/build_landuse_parking.py   # D1 + A5 completion
python src/build/build_zone_attractions.py      # jobs to SA1, attraction terms
python src/build/build_params.py                # C1
python src/build/build_population.py            # B1 persons + households (~30 s)
python src/build/build_gtfs_extras.py           # A3 extras
python cities/newcastle/build/build_scenario_schedules.py    # S0..S6 feeds
python cities/newcastle/build/build_era1_reconstruction.py   # pre-2014 reconstruction
python cities/newcastle/build/build_scenario_configs.py      # E1
python cities/newcastle/build/build_validation_targets.py

# --- P2 network build (needs the toolchain) ---
python cities/newcastle/build/build_corridor_road_attributes.py
python src/build/build_matsim_network.py        # MATSim network + 15 mapped schedules
python cities/newcastle/build/build_sumo_corridor.py     # SUMO corridor, 4 road variants

# --- P3 demand synthesis (needs the P2 build above) ---
python src/build/measure_network_factors.py     # C2: detour factor, day-type split
python src/build/build_activity_chains.py       # B2 tours, 3 day types (~90 s, 790 MB)
python src/build/build_matsim_plans.py          # MATSim population per day type
python src/build/build_matsim_run_inputs.py     # 30 runnable scenario x day-type sets

python src/build/build_data_dictionary.py
python src/build/build_manifest.py              # regenerate the manifest LAST
```

---

## Sources and licensing

| Source | Licence |
|---|---|
| TfNSW Open Data Hub — GTFS, Opal, traffic counts, HTS, speed zones | CC-BY 4.0 |
| ABS — Census DataPacks, ASGS boundaries | CC-BY 4.0 |
| OpenStreetMap (via Overpass) | **ODbL 1.0 (share-alike)** |
| Copernicus GLO-30 DEM | ESA, free and open |

OSM-derived layers are **ODbL**, which is share-alike; derived network files inherit
that obligation and the rest of the package is CC-BY 4.0. Keep the distinction visible
in anything published. Per-file provenance is in
[`data/MANIFEST.csv`](cities/newcastle/data/MANIFEST.csv).

---

## What is not here

Three inputs the research design named as critical could not be obtained from open
sources. **They are handled by parameter sweep, never pinned to a point value:**

- **SCATS signal phasing** — refused by TfNSW policy. Corridor run time swings 38%
  between no priority and full priority; the largest single uncertainty in the model.
- **Journey-linked Opal** — needed to *estimate* the transfer penalty rather than sweep
  it across 3–15 minutes.
- **Measured charging dwell** — assumed 20 s per intermediate stop, worth 11% of
  end-to-end run time.

Also absent: pedestrian counts (none published for Newcastle — hypothesis B1 has no
observable without them), frontage-level retail floorspace and vacancy, parking meter
transactions, and a 2014 timetable to validate the era-1 reconstruction. The full list
and priority order is in [`cities/newcastle/docs/DECISIONS.md`](cities/newcastle/docs/DECISIONS.md) §13.
