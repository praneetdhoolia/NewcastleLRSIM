#!/usr/bin/env python
"""MATSim plans (population_v6) from the B2 activity chains, one file per day type.

Consumes `demand/plans/B2_activity_trips_<DAY>.csv` and writes
`demand/plans/matsim/population_<DAY>.xml.gz`. Nothing here invents travel: the
activity sequence, its coordinates and its timing all come from B2. What this
adds is the two things MATSim needs and B2 deliberately does not carry -
a mode on every leg, and person attributes for the scoring and choice modules.

Mode is a seed, not a prediction
--------------------------------
DECISIONS.md 9 keeps mode out of B2 on purpose: assigning it there would
pre-empt the question the model exists to answer. But a MATSim plan file cannot
omit it - every leg needs a mode to be routed and scored at iteration 0. So a
mode is drawn here **per tour**, from a car-availability-conditioned
multinomial, and is an *initial condition* for the co-evolutionary loop, not an
output. Two properties make that safe:

  * it is drawn per **tour**, never per leg, so a car that leaves home comes
    home again and `SubtourModeChoice`'s mass conservation for chain-based modes
    holds from iteration 0;
  * the shares are recorded in DECISIONS.md as assumed with a sweep range, and
    P4 is expected to move them.

The full-day chains B2 now produces are what make this work at all. Under the P1
chains every agent had exactly one subtour, so a per-tour draw would have fixed
one mode for the entire day.

Determinism: one seeded generator, persons consumed in the file's own sorted
order, so the same B2 reproduces the same plans byte for byte.
"""
import os
import csv
import gzip
import json
import argparse
import collections

import numpy as np
import pandas as pd

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from det_io import gzip_writer

PLANS = 'demand/plans'
POP = 'demand/population'
OUT = os.path.join(PLANS, 'matsim')
SEED = 20260810
DAY_TYPES = ['WEEKDAY', 'SAT', 'SUN']

# Seed mode split, by car availability. Assumed; recorded in DECISIONS.md with a
# sweep range. These are *initial conditions*, deliberately not calibrated here -
# the HTS mode share is a P4 calibration target, not a P3 input (DECISIONS.md 2.4
# rules out census journey-to-work for that purpose).
# Chosen so the *blended* seed share lands near the HTS aggregate - 71.5% of
# legs are made by car-available persons - because starting iteration 0 far from
# the observed point wastes iterations without changing where the model
# converges. Seeding near HTS is not the same as matching it: the mode share is
# a P4 calibration target (DECISIONS.md 2.4), and this is the initial condition
# the calibration starts from.
SEED_MODE_SPLIT = {
    True:  [('car', 0.78), ('ride', 0.10), ('walk', 0.09), ('pt', 0.02), ('bike', 0.01)],
    False: [('ride', 0.40), ('walk', 0.45), ('pt', 0.09), ('bike', 0.06)],
}
SEED_MODE_SWEEP = {'car_share_car_available': (0.68, 0.86),
                   'pt_share_no_car': (0.05, 0.20)}
# HTS 2024/25 for the five study-area LGAs, reliability-flag variants collapsed.
HTS_MODE_SHARE_PCT = {'car': 57.46, 'ride': 21.46, 'walk': 16.14, 'pt': 3.39,
                      'bike_other': 1.55}

# Activity types carried through to the scoring configuration.
ACT_TYPES = ('home', 'work', 'education', 'shopping', 'other', 'business')
TYPICAL_DURATION_S = {'home': 12 * 3600, 'work': 8 * 3600, 'education': 6 * 3600,
                      'shopping': 1 * 3600, 'other': 2 * 3600, 'business': 1 * 3600}


def hhmmss(s):
    s = max(0, int(round(s)))
    return '%02d:%02d:%02d' % (s // 3600, (s % 3600) // 60, s % 60)


def esc(v):
    return (str(v).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;'))


def load_person_attributes():
    """car availability, age band and employment, keyed by person id."""
    p = pd.read_csv(os.path.join(POP, 'B1_synthetic_population.csv'),
                    usecols=['person_id', 'age', 'car_available', 'licence_holder',
                             'employment_status', 'student_status',
                             'mobility_impairment_flag'])
    return {
        int(r.person_id): (int(r.car_available), int(r.age), int(r.licence_holder),
                           str(r.employment_status), str(r.student_status),
                           int(r.mobility_impairment_flag))
        for r in p.itertuples()
    }


def pick_mode(car_available, u):
    table = SEED_MODE_SPLIT[bool(car_available)]
    x = u()
    c = 0.0
    for mode, p in table:
        c += p
        if x <= c:
            return mode
    return table[-1][0]


def stream_persons(path):
    """Yield (person_id, [legs]) from a B2 file already sorted by person id."""
    with open(path, newline='', encoding='utf-8') as f:
        cur, rows = None, []
        for r in csv.DictReader(f):
            pid = int(r['person_id'])
            if cur is not None and pid != cur:
                yield cur, rows
                rows = []
            cur = pid
            rows.append(r)
        if cur is not None:
            yield cur, rows


def write_day(day, attrs, rng, report):
    src = os.path.join(PLANS, 'B2_activity_trips_%s.csv' % day)
    dst = os.path.join(OUT, 'population_%s.xml.gz' % day)
    u_buf = {'buf': rng.random(1 << 20), 'i': 0}

    def u():
        if u_buf['i'] >= u_buf['buf'].size:
            u_buf['buf'] = rng.random(1 << 20)
            u_buf['i'] = 0
        v = u_buf['buf'][u_buf['i']]
        u_buf['i'] += 1
        return float(v)

    n_persons = n_legs = n_acts = 0
    modes = collections.Counter()
    act_counts = collections.Counter()
    tours = 0

    with gzip_writer(dst) as w:
        w.write('<?xml version="1.0" encoding="utf-8"?>\n')
        w.write('<!DOCTYPE population SYSTEM '
                '"http://www.matsim.org/files/dtd/population_v6.dtd">\n')
        w.write('<population>\n')
        for pid, rows in stream_persons(src):
            rows.sort(key=lambda r: int(r['trip_seq']))
            external = rows[0]['agent_tier'] == 'external'
            if external:
                car_av, age, lic, emp, stu, mob = 1, 40, 1, 'employed_full_time', 'none', 0
            else:
                a = attrs.get(pid)
                if a is None:
                    continue
                car_av, age, lic, emp, stu, mob = a

            # one mode per tour keeps chain-based modes conserved from the start
            tour_mode = {}
            for r in rows:
                tid = int(r['tour_id'])
                if tid not in tour_mode:
                    tour_mode[tid] = pick_mode(car_av, u)
            tours += len(tour_mode)

            w.write('\t<person id="%d">\n' % pid)
            w.write('\t\t<attributes>\n')
            w.write('\t\t\t<attribute name="subpopulation" class="java.lang.String">'
                    '%s</attribute>\n' % ('external' if external else 'person'))
            w.write('\t\t\t<attribute name="carAvail" class="java.lang.String">'
                    '%s</attribute>\n' % ('always' if car_av else 'never'))
            w.write('\t\t\t<attribute name="hasLicense" class="java.lang.String">'
                    '%s</attribute>\n' % ('yes' if lic else 'no'))
            w.write('\t\t\t<attribute name="age" class="java.lang.Integer">'
                    '%d</attribute>\n' % age)
            w.write('\t\t\t<attribute name="employment" class="java.lang.String">'
                    '%s</attribute>\n' % esc(emp))
            w.write('\t\t\t<attribute name="mobilityImpaired" class="java.lang.String">'
                    '%s</attribute>\n' % ('yes' if mob else 'no'))
            w.write('\t\t</attributes>\n')
            w.write('\t\t<plan selected="yes">\n')

            # opening activity: home, at the first leg's origin
            first = rows[0]
            w.write('\t\t\t<activity type="home" x="%s" y="%s" end_time="%s" />\n'
                    % (first['origin_x'], first['origin_y'],
                       hhmmss(int(first['dep_time_s']))))
            n_acts += 1
            act_counts['home'] += 1

            for i, r in enumerate(rows):
                mode = tour_mode[int(r['tour_id'])]
                w.write('\t\t\t<leg mode="%s" />\n' % mode)
                modes[mode] += 1
                n_legs += 1
                act = r['dest_activity_type']
                act_counts[act] += 1
                n_acts += 1
                if i == len(rows) - 1:
                    w.write('\t\t\t<activity type="%s" x="%s" y="%s" />\n'
                            % (act, r['dest_x'], r['dest_y']))
                else:
                    end = int(rows[i + 1]['dep_time_s'])
                    w.write('\t\t\t<activity type="%s" x="%s" y="%s" '
                            'end_time="%s" />\n'
                            % (act, r['dest_x'], r['dest_y'], hhmmss(end)))
            w.write('\t\t</plan>\n')
            w.write('\t</person>\n')
            n_persons += 1
        w.write('</population>\n')

    report[day] = dict(persons=n_persons, legs=n_legs, activities=n_acts,
                       tours=tours, bytes=os.path.getsize(dst),
                       seed_mode_share={k: round(v / max(n_legs, 1), 4)
                                        for k, v in sorted(modes.items())},
                       activity_types=dict(sorted(act_counts.items())))
    print('%-8s %7d persons %9d legs %9d activities  %s'
          % (day, n_persons, n_legs, n_acts,
             {k: round(v / max(n_legs, 1), 3) for k, v in sorted(modes.items())}),
          flush=True)


def main(seed=SEED, day_types=None):
    day_types = day_types or DAY_TYPES
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(seed)
    print('loading person attributes ...', flush=True)
    attrs = load_person_attributes()
    report = {}
    for d in day_types:
        write_day(d, attrs, rng, report)
    meta = dict(seed=seed, seed_mode_split={str(k): v for k, v in SEED_MODE_SPLIT.items()},
                seed_mode_sweep=SEED_MODE_SWEEP,
                hts_mode_share_pct=HTS_MODE_SHARE_PCT,
                typical_duration_s=TYPICAL_DURATION_S,
                note='Seed modes are initial conditions for MATSim co-evolution, '
                     'drawn per tour so chain-based modes stay conserved. They are '
                     'not a mode-share prediction and not calibrated here; the '
                     'calibration target is HTS (DECISIONS.md 2.4).',
                by_day=report)
    json.dump(meta, open(os.path.join(OUT, '_plans_report.json'), 'w'), indent=2)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', type=int, default=SEED)
    ap.add_argument('--day-types', default=','.join(DAY_TYPES))
    a = ap.parse_args()
    main(a.seed, [d for d in a.day_types.split(',') if d])
