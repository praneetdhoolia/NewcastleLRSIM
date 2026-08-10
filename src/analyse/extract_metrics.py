#!/usr/bin/env python
"""Turn a completed run into quantities comparable with the validation targets.

Three metrics, each in the units its target is published in, and each with the
translation stated rather than assumed:

**Mode share.** MATSim's `main_mode` per trip is a *linked* concept - a walk to
a bus stop is part of a pt trip - which is what the published HTS `MODE_SHARE`
measures and is why the linked Newcastle-LGA figures are the comparable ones
(DECISIONS.md 12.1). The target geography is **Newcastle LGA**, and the model
covers five, so trips are attributed to the LGA of the traveller's **home**
coordinate and the share computed over Newcastle residents alone.

**PT boardings.** Every pt leg with a `transit_line` is one boarding, which is
what an Opal tap-on is. Legs are scaled by 1/fraction to full population. Light
rail is identified from the line id, not by guessing at names.

**Link volumes.** `vol_car` from `output_links.csv`, summed over the links a
count station maps to (both directions, since the counts are two-way), scaled by
1/fraction. Two corrections from `params/C3_count_comparison.json` are applied
and reported separately, never folded in: a `ride` leg contributes **no** vehicle
because observed vehicle trips are driver trips (DECISIONS.md 9.8), and the
model carries no freight, so the observed count is compared on a light-vehicle
basis using each station's own heavy share where classified.

This module reads run outputs, the station-link map and C3. **It never opens
`validation_targets.csv`**, so it cannot see the calibration/holdout split, let
alone a holdout value. Scoring against targets is `src/calibrate/fit.py`, which
reads the calibration rows only.
"""
import argparse
import collections
import csv
import gzip
import json
import os
import sys

CRS_M = 'EPSG:28356'
STATION_LINKS = 'data/processed/validation/count_station_links.csv'
C3 = 'params/C3_count_comparison.json'
POP = 'demand/population/B1_synthetic_population.csv'
SA1_LGA = 'data/processed/zones/sa1_to_lga.csv'
TARGET_LGA = 'Newcastle'


def open_output(run_dir, stem):
    """Open a MATSim output table, whatever it was compressed with.

    The configs set `compressionType=gzip` so the analysis needs only the
    standard library (DECISIONS.md 9.8). `.zst` is MATSim's default and is
    accepted as a fallback for runs made before that was set - but only if
    `zstandard` happens to be installed, which the repo does not require, so
    the failure is explicit rather than a confusing ImportError.
    """
    base = os.path.join(run_dir, 'output', stem)
    if os.path.exists(base + '.csv.gz'):
        return gzip.open(base + '.csv.gz', 'rt', encoding='utf-8')
    if os.path.exists(base + '.csv'):
        return open(base + '.csv', encoding='utf-8')
    if os.path.exists(base + '.csv.zst'):
        try:
            import io
            import zstandard
        except ImportError:
            raise SystemExit(
                '%s is .zst, from a run made before compressionType=gzip was '
                'set, and `zstandard` is not installed. Re-run it, or install '
                'zstandard for this one analysis - it is deliberately not a '
                'declared dependency of this repo.' % (stem + '.csv.zst'))
        f = open(base + '.csv.zst', 'rb')
        return io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(f),
                                encoding='utf-8')
    raise SystemExit('%s not found in %s/output' % (stem, run_dir))


def rows(run_dir, stem):
    with open_output(run_dir, stem) as f:
        for r in csv.DictReader(f, delimiter=';'):
            yield r


def home_lga():
    """person id -> LGA, via B1's home SA1 and the ABS boundary join.

    Built by `map_sa1_to_lga.py`; `zones_SA1.csv` carries SA2/SA3/SA4 but no
    LGA, and SA3 `Newcastle` is not Newcastle LGA. External-tier agents are not
    in B1 and map to '' rather than being counted as residents of anywhere.
    """
    if not os.path.exists(SA1_LGA):
        raise SystemExit('%s missing - run src/analyse/map_sa1_to_lga.py' % SA1_LGA)
    lga = {}
    with open(SA1_LGA, encoding='utf-8') as f:
        for z in csv.DictReader(f):
            lga[z['SA1_CODE21']] = z['lga_name']
    out = {}
    with open(POP, encoding='utf-8') as f:
        for p in csv.DictReader(f):
            out[p['person_id']] = lga.get(p['home_sa1'], '')
    return out


def mode_share(run_dir, person_lga):
    """Linked main-mode share, all residents and Newcastle residents alone."""
    everyone = collections.Counter()
    newcastle = collections.Counter()
    seen_unknown = 0
    for t in rows(run_dir, 'output_trips'):
        m = t['main_mode']
        everyone[m] += 1
        who = person_lga.get(t['person'])
        if who == TARGET_LGA:
            newcastle[m] += 1
        elif who is None:
            seen_unknown += 1

    def pct(c):
        n = sum(c.values())
        return {k: round(100.0 * v / n, 4) for k, v in sorted(c.items())} if n else {}
    return dict(all_residents_pct=pct(everyone), all_residents_trips=sum(everyone.values()),
                newcastle_lga_pct=pct(newcastle),
                newcastle_lga_trips=sum(newcastle.values()),
                persons_without_home_lga=seen_unknown)


def pt_boardings(run_dir, fraction):
    """One boarding per pt leg that boards a transit line; scaled to full pop."""
    by_line = collections.Counter()
    total = 0
    for l in rows(run_dir, 'output_legs'):
        line = (l.get('transit_line') or '').strip()
        if not line:
            continue
        by_line[line] += 1
        total += 1
    scale = 1.0 / fraction
    lr = {k: v for k, v in by_line.items() if 'lightrail' in k.lower()
          or 'light_rail' in k.lower() or k.lower().startswith('lr')}
    return dict(scale=scale,
                total_pt_boardings=round(total * scale),
                light_rail_boardings=round(sum(lr.values()) * scale),
                light_rail_lines=sorted(lr),
                by_line={k: round(v * scale) for k, v in by_line.most_common(40)})


def link_volumes(run_dir, fraction):
    """Modelled vehicles per station, two-way, scaled to full population."""
    want = collections.defaultdict(list)
    meta = {}
    with open(STATION_LINKS, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            want[r['link']].append(r['station_key'])
            meta.setdefault(r['station_key'], dict(
                station_key=r['station_key'], split=r['split'],
                road_name=r['road_name'], links=[], matched_by=r['matched_by'],
                max_distance_m=0.0, modelled_vehicles=0))
            m = meta[r['station_key']]
            m['links'].append(r['link'])
            m['max_distance_m'] = max(m['max_distance_m'], float(r['distance_m']))

    found = 0
    for l in rows(run_dir, 'output_links'):
        lid = l['link']
        if lid not in want:
            continue
        vol = float(l.get('vol_car') or 0)
        found += 1
        for key in want[lid]:
            meta[key]['modelled_vehicles'] += vol
    scale = 1.0 / fraction
    for m in meta.values():
        m['modelled_vehicles'] = round(m['modelled_vehicles'] * scale)
        m['links'] = ';'.join(m['links'])
    return dict(links_matched_in_output=found, links_expected=len(want),
                scale=scale, stations=sorted(meta.values(),
                                             key=lambda r: r['station_key']))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', required=True, help='a results/<name> directory')
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    run_dir = a.run if os.path.isdir(a.run) else os.path.join('results', a.run)
    rec = json.load(open(os.path.join(run_dir, '_run.json'), encoding='utf-8'))
    fraction = rec['fraction']

    c3 = json.load(open(C3, encoding='utf-8'))
    person_lga = home_lga()
    doc = dict(run=rec['name'], scenario=rec['scenario'], day=rec['day'],
               fraction=fraction, iterations=rec['iterations'],
               overrides=rec.get('overrides', {}),
               mode_share=mode_share(run_dir, person_lga),
               pt=pt_boardings(run_dir, fraction),
               counts=link_volumes(run_dir, fraction),
               corrections=dict(
                   vehicles_per_leg=c3['vehicles_per_leg'],
                   heavy_vehicle_share=c3['heavy_vehicle_share']),
               note='Modelled quantities only. No validation target is read '
                    'here; scoring is src/calibrate/fit.py.')
    out = a.out or os.path.join(run_dir, '_metrics.json')
    json.dump(doc, open(out, 'w'), indent=2)
    ms = doc['mode_share']
    print('%s: %d trips (%d by Newcastle residents)'
          % (rec['name'], ms['all_residents_trips'], ms['newcastle_lga_trips']))
    print('  Newcastle LGA mode share: %s' % ms['newcastle_lga_pct'])
    print('  PT boardings %s of which light rail %s'
          % (doc['pt']['total_pt_boardings'], doc['pt']['light_rail_boardings']))
    print('  count stations with a modelled volume: %d'
          % sum(1 for s in doc['counts']['stations'] if s['modelled_vehicles']))
    print('  -> %s' % out)


if __name__ == '__main__':
    main()
