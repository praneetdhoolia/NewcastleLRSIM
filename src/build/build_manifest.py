#!/usr/bin/env python
"""Build the data package manifest: every file, its provenance and its lineage.

Deliverable 2 of the proposal is an open data package with every derived input,
its provenance, licence status and processing lineage. This walks the tree,
hashes everything, counts rows, and merges the per-stage provenance records.
"""
import os
import csv
import json
import hashlib
import datetime
import zipfile
import sys

# The manifest describes ONE CITY. Its paths stay city-relative - `data/...`,
# not `cities/newcastle/data/...` - so the manifest does not repeat the city's
# own name on all 376 of its rows, and a second city's manifest is comparable
# to this one row for row.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', 'src'))
import city as _city  # noqa: E402

ROOT = _city.CITY_DIR
SCAN = ['data/raw', 'data/processed', 'schedules', 'demand', 'params',
        'scenarios', 'networks/osm', 'networks/matsim', 'networks/sumo']
SKIP_EXT = {'.pyc'}
PROVENANCE_FILES = ['data/raw/provenance_open_data.json',
                    'data/raw/provenance_abs_dem.json',
                    'schedules/raw/provenance.json']
PROVENANCE_FILES = [os.path.join(ROOT, p) for p in PROVENANCE_FILES]


def _observed_adapter():
    """The city's own adapter for the observed layer, from its descriptor."""
    adapters = _city.descriptor().get('adapters', {})
    spec = adapters.get('observed') or {}
    return spec.get('script', 'extract/observed')


EXTRACT = 'cities/%s/extract/' % _city.CITY
# Builders that encode THIS CITY's intervention, corridor or history live
# with the city; the generic pipeline stays in src/build/.
CITY_BUILD = 'cities/%s/build/' % _city.CITY

# which script produced what, for the lineage graph
LINEAGE = {
    'networks/osm': EXTRACT + 'overpass.py',
    'schedules/raw': EXTRACT + 'fetch_gtfs.py',
    'data/raw/opal': EXTRACT + 'fetch_open_data.py',
    'data/raw/counts': EXTRACT + 'fetch_open_data.py',
    'data/raw/hts': EXTRACT + 'fetch_open_data.py',
    'data/raw/boundaries': EXTRACT + 'fetch_abs_dem.py',
    'data/raw/census': EXTRACT + 'fetch_abs_dem.py',
    'data/raw/dem': EXTRACT + 'fetch_abs_dem.py',
    'data/processed/zones': EXTRACT + 'extract_zones.py',
    'data/processed/census': EXTRACT + 'extract_census.py',
    'data/processed/hts': EXTRACT + 'extract_hts.py',
    # The adapter that produces this layer is named by the city's own
    # descriptor: `slice_newcastle.py` was one city's file name in framework
    # code, and a second city's adapter is called something else.
    'data/processed/observed': _observed_adapter(),
    'data/processed/network': 'src/build/build_network_layers.py + attach_gradient.py',
    'data/processed/corridor': CITY_BUILD + 'build_corridor_layers.py',
    'data/processed/landuse': CITY_BUILD + 'build_landuse_parking.py + '
                              'src/build/build_zone_attractions.py',
    'data/processed/schedule_extras': 'src/build/build_gtfs_extras.py',
    'data/processed/validation': CITY_BUILD + 'build_validation_targets.py',
    'schedules/scenarios': CITY_BUILD + 'build_scenario_schedules.py',
    'demand/population': 'src/build/build_population.py',
    'demand/plans': 'src/build/build_activity_chains.py',
    'demand/plans/matsim': 'src/build/build_matsim_plans.py',
    'params': 'src/build/build_params.py',
    'scenarios': CITY_BUILD + 'build_scenario_configs.py',
    'scenarios/matsim': 'src/build/build_matsim_run_inputs.py',
    'schedules': CITY_BUILD + 'build_era_feeds.py',
    'networks/matsim': 'src/build/build_matsim_network.py (pt2matsim 26.6)',
    'networks/sumo': CITY_BUILD + 'build_sumo_corridor.py (SUMO netconvert 1.27.1)',
}

# Every adapter's own `produces` declaration overlays the map above, so an
# adapter that produces a SPECIFIC FILE inside a directory another adapter
# owns (extract_freight_profile.py writing two CSVs into the observed layer)
# is attributed to the script that actually wrote it - longest prefix wins in
# lineage_for(). For the adapters already listed above this writes back the
# identical string, so no manifest row churns.
for _spec in _city.descriptor().get('adapters', {}).values():
    if _spec.get('script'):
        for _prefix in _spec.get('produces', []):
            LINEAGE[_prefix] = 'cities/%s/%s' % (_city.CITY, _spec['script'])

# P2 build intermediates: large, regenerable, and not part of the package.
SKIP_DIRS = ('networks/matsim/_work', 'networks/sumo/_work')


def sha256(p, limit=None):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def count_rows(p):
    if p.endswith('.csv'):
        try:
            with open(p, encoding='utf-8', errors='replace') as f:
                return max(0, sum(1 for _ in f) - 1)
        except Exception:
            return None
    if p.endswith('.jsonl'):
        try:
            with open(p, encoding='utf-8', errors='replace') as f:
                return sum(1 for _ in f)
        except Exception:
            return None
    if p.endswith('.zip'):
        try:
            z = zipfile.ZipFile(p)
            return len(z.namelist())
        except Exception:
            return None
    return None


def lineage_for(rel):
    best = ''
    for k, v in LINEAGE.items():
        if rel.replace('\\', '/').startswith(k) and len(k) > len(best):
            best = k
    return LINEAGE.get(best, '')


def main():
    prov = {}
    for pf in PROVENANCE_FILES:
        if os.path.exists(pf):
            try:
                for r in json.load(open(pf)):
                    k = r.get('path') or ('%s/%s.zip' % (r.get('era', ''), r.get('feed', '')))
                    prov[k] = r
            except Exception as e:
                print('warn: %s (%s)' % (pf, e))

    files = []
    for base in SCAN:
        base = os.path.join(ROOT, base)
        if not os.path.isdir(base):
            continue
        for dirpath, _, names in os.walk(base):
            for n in sorted(names):
                p = os.path.join(dirpath, n)
                ext = os.path.splitext(n)[1].lower()
                if ext in SKIP_EXT or '__pycache__' in dirpath:
                    continue
                rel = os.path.relpath(p, ROOT).replace('\\', '/')
                if rel.startswith(SKIP_DIRS):
                    continue
                sz = os.path.getsize(p)
                stage = 'raw' if rel.startswith(('data/raw', 'networks/osm', 'schedules/raw')) \
                    else 'processed'
                pkey = rel.replace('data/raw/', '')
                pr = prov.get(pkey, {})
                files.append(dict(
                    path=rel, bytes=sz, rows=count_rows(p),
                    sha256=sha256(p) if sz < 300 * 1 << 20 else 'skipped_large',
                    stage=stage,
                    produced_by=lineage_for(rel),
                    source=pr.get('description') or pr.get('source', ''),
                    source_url=pr.get('url') or pr.get('s3_key', ''),
                    licence=pr.get('licence', ''),
                    retrieved=pr.get('retrieved', '')))

    total = sum(f['bytes'] for f in files)
    man = dict(
        project=_city.descriptor().get('description') or _city.descriptor()['name'],
        generated=datetime.datetime.now().replace(microsecond=0).isoformat(),
        base_year=_city.base_year(),
        crs=_city.crs_label(),
        n_files=len(files),
        total_bytes=total,
        total_gib=round(total / (1 << 30), 2),
        by_stage={s: sum(1 for f in files if f['stage'] == s) for s in ('raw', 'processed')},
        bytes_by_stage={s: sum(f['bytes'] for f in files if f['stage'] == s)
                        for s in ('raw', 'processed')},
        files=files)
    json.dump(man, open(os.path.join(ROOT, 'data', 'MANIFEST.json'), 'w'), indent=2)
    cols = ['path', 'stage', 'bytes', 'rows', 'produced_by', 'source', 'source_url',
            'licence', 'retrieved', 'sha256']
    with open(os.path.join(ROOT, 'data', 'MANIFEST.csv'), 'w', newline='',
          encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        w.writerows(files)
    print('files=%d  total=%.2f GiB' % (len(files), man['total_gib']))
    print('by stage:', man['by_stage'], man['bytes_by_stage'])
    print('\nlargest 12:')
    for f in sorted(files, key=lambda x: -x['bytes'])[:12]:
        print('  %10.1f MB  %s' % (f['bytes'] / 1e6, f['path']))


if __name__ == '__main__':
    main()
