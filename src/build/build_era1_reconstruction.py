#!/usr/bin/env python
"""Reconstruct the pre-December-2014 heavy rail service to Newcastle station.

The TfNSW historical GTFS archive begins in August 2016, by which time the line
had already been truncated. There is therefore no archived feed for the era the
proposal calls 'pre-Dec 2014', and Appendix C anticipates this: historic
timetables may exist only as PDFs, and manual reconstruction must be budgeted.

This script produces a defensible reconstruction rather than a fabrication:
it takes the earliest archived feed (August 2016, the 2015-Jul 2017 era) and
restores the three closed stations - Wickham, Civic and Newcastle - onto the
services that terminate at the truncation point, using running times derived
from the alignment length at heavy rail line speed.

WHAT THIS IS NOT: it is not the 2014 timetable. Frequency, stopping pattern and
rolling stock are those of 2016. Validating it against a 2014 public timetable
remains an outstanding data task, recorded in DECISIONS.md.
"""
import os
import sys
import csv
import json
import math
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gtfs_tools import read_feed, write_feed

# Model inputs come from config/registry/, not from literals in this file. Every
# value below carries its units, provenance and either a sweep, a held-fixed rule
# or a derived-from identity there. See DECISIONS.md 15.
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import registry as _registry  # noqa: E402
CFG = _registry.load()

SRC = 'schedules/era2_2016_rail_truncated.zip'
OUT = 'schedules/era1_pre2014_reconstructed.zip'
REPORT = 'schedules/_era1_reconstruction_report.json'

# The three stations closed on 26 December 2014, with their real sites.
CLOSED_STATIONS = [
    ('Wickham Station (closed 2014)', -32.92450, 151.76500),
    ('Civic Station (closed 2014)', -32.92800, 151.77560),
    ('Newcastle Station (closed 2014)', -32.92820, 151.78460),
]
TRUNCATION_POINTS = ('Hamilton Station', 'Newcastle Interchange', 'Wickham')
LINE_SPEED_KMH = CFG.get('A.transit.era1_line_speed_kmh')
ACCEL, DECEL = 0.7, 0.8      # heavy rail EMU, gentler than a tram
STATION_DWELL_S = CFG.get('A.transit.era1_station_dwell_s')


def hav(a, b):
    R = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1])
    dp = p2 - p1
    return 2 * R * math.asin(math.sqrt(
        math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))


def kin(d, v_kmh=LINE_SPEED_KMH, a=ACCEL, b=DECEL):
    v = v_kmh / 3.6
    da, db = v * v / (2 * a), v * v / (2 * b)
    if d >= da + db:
        return v / a + v / b + (d - da - db) / v
    vp = math.sqrt(2 * d * a * b / (a + b))
    return vp / a + vp / b


def sec(t):
    h, m, s = map(int, t.split(':'))
    return h * 3600 + m * 60 + s


def hhmmss(s):
    s = int(round(s))
    return '%02d:%02d:%02d' % (s // 3600, (s % 3600) // 60, s % 60)


def main():
    f = read_feed(SRC)
    stops = {s['stop_id']: s for s in f['stops']}
    routes = {r['route_id']: r for r in f['routes']}
    trip_route = {t['trip_id']: t['route_id'] for t in f['trips']}
    by = collections.defaultdict(list)
    for r in f['stop_times']:
        by[r['trip_id']].append(r)
    for k in by:
        by[k].sort(key=lambda r: int(r['stop_sequence']))

    # register the closed stations
    ids = []
    for i, (nm, la, lo) in enumerate(CLOSED_STATIONS):
        sid = 'era1:CLOSED_%d' % (i + 1)
        ids.append(sid)
        f['stops'].append(dict(stop_id=sid, stop_name=nm, stop_lat=la, stop_lon=lo,
                               location_type='0', parent_station=''))

    # which stop is the truncation terminus in this feed
    term_counts = collections.Counter()
    for tid, rows in by.items():
        rt = routes.get(trip_route.get(tid), {})
        if rt.get('route_type') != '2':
            continue
        term_counts[stops.get(rows[-1]['stop_id'], {}).get('stop_name', '?')] += 1

    extended = 0
    newst = []
    touched = set()
    for tid, rows in by.items():
        rt = routes.get(trip_route.get(tid), {})
        if rt.get('route_type') != '2':
            continue
        last = stops.get(rows[-1]['stop_id'], {})
        name = last.get('stop_name', '')
        if not any(t in name for t in TRUNCATION_POINTS):
            continue
        try:
            cur = (float(last['stop_lat']), float(last['stop_lon']))
        except (KeyError, TypeError, ValueError):
            continue
        t = sec(rows[-1]['arrival_time'])
        out = [dict(r) for r in rows]
        for sid, (nm, la, lo) in zip(ids, CLOSED_STATIONS):
            d = hav(cur, (la, lo)) * 1.08
            if d < 50:                      # already at/next to this site
                cur = (la, lo)
                continue
            t += kin(d) + STATION_DWELL_S
            out.append(dict(trip_id=tid, stop_id=sid, stop_sequence=0,
                            arrival_time=hhmmss(t), departure_time=hhmmss(t + STATION_DWELL_S),
                            pickup_type='0', drop_off_type='0'))
            cur = (la, lo)
        for i, r in enumerate(out):
            r['stop_sequence'] = i + 1
        newst.extend(out)
        touched.add(tid)
        extended += 1
    for r in f['stop_times']:
        if r['trip_id'] not in touched:
            newst.append(r)
    f['stop_times'] = newst
    write_feed(f, OUT)

    # end-to-end added time
    d_tot = 0.0
    cur = None
    for nm, la, lo in CLOSED_STATIONS:
        if cur:
            d_tot += hav(cur, (la, lo))
        cur = (la, lo)
    rep = dict(source_feed=SRC, output=OUT,
               trips_extended=extended,
               truncation_termini_in_source=dict(term_counts.most_common(8)),
               closed_stations=[c[0] for c in CLOSED_STATIONS],
               reconstructed_extension_length_m=round(d_tot, 0),
               line_speed_kmh=LINE_SPEED_KMH, station_dwell_s=STATION_DWELL_S,
               status='RECONSTRUCTION - frequency and stopping pattern are 2016, '
                      'not 2014. Validate against a 2014 public timetable before use '
                      'in any published figure.',
               source='assumed')
    json.dump(rep, open(REPORT, 'w'), indent=2)
    print(json.dumps(rep, indent=2))


if __name__ == '__main__':
    main()
