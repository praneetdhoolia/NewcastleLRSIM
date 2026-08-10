# Project Wickham — data package

Counterfactual microsimulation of the Newcastle Light Rail as a transport
intervention. This repository currently contains **phase P1: data acquisition**
for the MATSim + SUMO model described in [`newcastle-lr-proposal.md`](newcastle-lr-proposal.md).

No scenario has been run. Nothing here is a result.

---

## What is here

| | |
|---|---|
| Files | 182 |
| Size | 2.31 GiB (1.82 GiB raw, 0.49 GiB processed) |
| Study area | Newcastle, Lake Macquarie, Maitland, Cessnock, Port Stephens — 4,086 km² |
| Zones | 1,500 core SA1 + 201 external SA1, 222 core DZN |
| Population | 611,915 (2021 Census) → 612,680 synthetic agents |
| Road network | 43,112 edges, 9,207 km, gradient-attached |
| Active network | 35,653 edges, 6,325 km, directional walk-speed factors |
| PT | 5 GTFS eras + 10 scenario variants |
| Validation | 210 targets (67 calibration / 143 holdout) |
| Base year | 2026 · CRS EPSG:28356 (GDA2020 / MGA Zone 56) |

**Read [`DECISIONS.md`](DECISIONS.md) before using any of it.** It records every
assumed value, its sweep range, and four corrections to premises stated in the
proposal.

---

## Layout

```
data/
  raw/            immutable downloads, provenance-tagged
    opal/         patronage, tap data, station entries/exits
    counts/       NSW road traffic volumes (station ref, AADT, hourly)
    hts/          Household Travel Survey, both release epochs
    census/       ABS 2021 DataPacks (GCP SA1/SA2, PEP, WPP POW SA2)
    boundaries/   ABS ASGS Ed3 SA1/SA2/SA3/DZN/LGA
    dem/          Copernicus GLO-30 tiles
  processed/
    zones/        study-area boundaries, centroids, core/external tiers
    census/       26 census tables clipped to the study area
    hts/          Newcastle mode and purpose series, 2009/10-2024/25
    observed/     Newcastle slices of Opal, counts, station usage
    network/      A1 road edges, A6 footway edges, A2 signals/crossings/turns
    corridor/     A4 vehicle + dwell, run-time decomposition, A2 corridor signals
    landuse/      D1 POI, buildings, frontage segments, zone attractions, jobs
    schedule_extras/  A3 route/stop/transfer extras
    validation/   calibration and holdout targets
  MANIFEST.json   every file: hash, rows, source, licence, producing script
networks/osm/     raw Overpass extracts (roads, footways, rail, parking, POI, buildings)
schedules/        era feeds + scenarios/S0..S6
demand/           population/ and plans/
params/           C1 behavioural parameters + 140-point sweep grid
scenarios/        E1 configs, one JSON per scenario
src/extract/      acquisition and clipping
src/build/        layer construction
```

---

## Reproducing

Python 3.11+. `pip install requests pandas numpy shapely pyproj lxml geopandas pyogrio rasterio openpyxl`

```bash
# --- acquisition (network-bound, ~2 GiB) ---
python src/extract/overpass.py                  # OSM, 8 themed extracts
python src/extract/fetch_gtfs.py                # era GTFS from the TfNSW S3 archive
python src/extract/fetch_open_data.py           # Opal, traffic counts, HTS
python src/extract/fetch_abs_dem.py             # ABS boundaries, census, DEM

# --- clipping ---
python src/extract/extract_zones.py
python src/extract/extract_census.py
python src/extract/extract_hts.py
python src/extract/slice_newcastle.py

# --- layer construction ---
python src/build/build_era_feeds.py             # A3 era variants
python src/build/build_network_layers.py        # A1, A2, A5, A6
python src/build/attach_gradient.py             # gradient onto A1 and A6
python src/build/build_corridor_layers.py       # A4 + corridor A2
python src/build/build_landuse_parking.py       # D1 + A5 completion
python src/build/build_zone_attractions.py      # jobs to SA1, attraction terms
python src/build/build_params.py                # C1
python src/build/build_population.py            # B1 persons + households (~30 s)
python src/build/build_gtfs_extras.py           # A3 extras
python src/build/build_scenario_schedules.py    # S0..S6 feeds
python src/build/build_era1_reconstruction.py   # pre-2014 reconstruction
python src/build/build_scenario_configs.py      # E1
python src/build/build_validation_targets.py

# --- P2 network build (needs the toolchain below) ---
python src/setup/bootstrap_toolchain.py         # JDK 25, pt2matsim 26.6, SUMO 1.27.1
python src/build/build_corridor_road_attributes.py   # corridor provenance + E1 deltas
python src/build/build_matsim_network.py        # MATSim network + 15 mapped schedules
python src/build/build_sumo_corridor.py         # SUMO corridor, 4 road variants

# --- P3 demand synthesis (needs the P2 build above: one build, shared by all
#     scenarios - see DECISIONS.md 3.5) ---
python src/build/measure_network_factors.py     # C2: detour factor, day-type split (~70 s)
python src/build/build_activity_chains.py       # B2 tours, 3 day types (~90 s, 790 MB out)
python src/build/build_matsim_plans.py          # MATSim population per day type (~45 s)
python src/build/build_matsim_run_inputs.py     # 30 runnable scenario x day-type sets (~45 s)

python src/build/build_data_dictionary.py
python src/build/build_manifest.py
```

Everything this repository generates is seeded (`20260810`) and deterministic, with one
exception that is measured rather than assumed away: **pt2matsim's schedule mapping is not
reproducible run to run** — about 18% of transit route link sequences differ between
identical builds, while 100% of stop-to-link assignments hold. See
[`DECISIONS.md`](DECISIONS.md) §3.5 for the measurements and for the constraint it places
on scenario comparisons.

### Toolchain

P2 needs three tools the repository cannot regenerate. `src/setup/bootstrap_toolchain.py`
fetches them into `.tools/` (gitignored, ~1.4 GiB) and pins each by sha256 in
`.tools/toolchain.json`:

| Tool | Version | Source |
|---|---|---|
| Eclipse Temurin JDK | 25.0.4+7 | github.com/adoptium (pt2matsim 26.6 targets Java 25) |
| pt2matsim | 26.6, shaded jar | repo.matsim.org (bundles MATSim; no Maven needed) |
| Eclipse SUMO `netconvert` | 1.27.1 | PyPI `eclipse-sumo` wheel |

`python src/setup/bootstrap_toolchain.py --verify` re-checks the digests without
downloading anything.

---

## Sources and licensing

| Source | Licence |
|---|---|
| TfNSW Open Data Hub — GTFS, Opal, traffic counts, HTS | CC-BY 4.0 |
| ABS — Census DataPacks, ASGS boundaries | CC-BY 4.0 |
| OpenStreetMap (via Overpass) | ODbL 1.0 |
| Copernicus GLO-30 DEM | ESA, free and open |

Per-file provenance, hashes and the producing script are in
[`data/MANIFEST.csv`](data/MANIFEST.csv).

Note the OSM layers are **ODbL**, which is share-alike. Derived network files
inherit that obligation; the rest of the package is CC-BY. Keep the distinction
when the data package is published.

---

## What is not here

Three inputs the proposal named as critical were not obtainable from open
sources and are handled by parameter sweep, with formal requests outstanding:

- **SCATS signal phasing** — corridor run time swings 38% between no priority and
  full priority (S2 vs S2b). Largest single uncertainty in the model.
- **Journey-linked Opal** — needed to *estimate* the transfer penalty rather than
  sweep it across 3–15 minutes.
- **Measured charging dwell** — assumed 20 s per intermediate stop, worth 11% of
  end-to-end run time.

Also absent: pedestrian counts (none published for Newcastle), frontage-level
retail floorspace and vacancy, parking meter transactions, and a 2014 timetable
to validate the era-1 reconstruction. Full list and priority order in
[`DECISIONS.md` §13](DECISIONS.md).

---

## Next phase

P2 is complete: the MATSim network and all 15 mapped schedules, the four E1 road
variants as link-attribute patches, and the SUMO corridor with the A2 signal
timings attached. The corridor turned out **not** to need the hand correction
§3.1 called for — 87.5% of as-built trunk lane counts are observed in OSM
([`DECISIONS.md` §2.5](DECISIONS.md)) — so what the B3 net-arrivals test rests on
is the *counterfactual* cross-section, which is assumed and swept 1–2 lanes per
direction rather than digitised.

P3 demand synthesis is next. Read [`STATUS.md`](STATUS.md) for the four items P2
raised that P3–P5 must respect, in particular the requirement that any scenario
comparison run against a single build of the network
([`DECISIONS.md` §3.5](DECISIONS.md)).
