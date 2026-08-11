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

# Seed mode split: UNINFORMED, uniform over the modes a person can use.
#
# The P3 seed was positioned so the blended share landed near the HTS aggregate
# (car 55.7 against 57.5, pt 4.0 against 3.4). That is defensible as a
# convergence aid and indefensible as an initial condition for a calibration
# whose target *is* the HTS mode share: a model that starts at the answer cannot
# be said to have found it. Worse, until P4 fixed the mode-choice configuration
# `ride` was not in MATSim's choice set at all, so the seeded 18.6% car-passenger
# share was not an initial condition but the model's output (DECISIONS.md 9.6).
#
# The only thing conditioned on here is **car availability**, which is a
# population attribute from B1, not a behavioural prior. Within the modes a
# person can actually use, the draw is uniform. This is deliberately a bad guess:
# it starts the co-evolution far from the observed point so that arriving there
# is evidence about the model rather than about the seed.
SEED_MODE_SPLIT = {
    True:  [('car', 0.20), ('ride', 0.20), ('walk', 0.20), ('pt', 0.20), ('bike', 0.20)],
    False: [('ride', 0.25), ('walk', 0.25), ('pt', 0.25), ('bike', 0.25)],
}
# The uniform seed has no free share to sweep - "uniform over the usable modes"
# is fully determined by B1 car availability. What is swept instead is the
# *choice of seed itself*, which is the quantity that could bias the result:
# the two entries are the two seeds this script can produce, and DECISIONS.md
# 9.7 reports the measured difference between them.
SEED_MODE_SWEEP = {'seed_mode': ('uninformed', 'informed')}
# The informed seed the uniform one replaces. Retained so that "the result does
# not depend on the seed" is a claim that can be tested by running both, not an
# assertion (DECISIONS.md 9.6); selected with --seed-mode informed.
SEED_MODE_SPLIT_INFORMED = {
    True:  [('car', 0.78), ('ride', 0.10), ('walk', 0.09), ('pt', 0.02), ('bike', 0.01)],
    False: [('ride', 0.40), ('walk', 0.45), ('pt', 0.09), ('bike', 0.06)],
}
HTS_FILE = 'data/processed/hts/hts_mode_newcastle.csv'
HTS_YEAR = '2024/25'
HTS_TARGET_LGA = 'Newcastle'


def hts_mode_share():
    """Both HTS 2024/25 aggregations, derived from the file rather than typed.

    They are different quantities and the difference matters:

    * **unlinked, five LGAs** - trips-weighted over the whole study area, with
      the walk stage of a public transport trip counted as its own walk trip.
      This is the aggregate the P3 seed was positioned against.
    * **linked, Newcastle LGA** - the published `MODE_SHARE` column, where a
      walk-plus-bus trip counts once, as public transport, so `walk linked` is
      0.0 by construction.

    MATSim's `modestats` reports the **main mode of a trip**, which is the
    linked concept, and the pre-registered calibration targets V202-V207 are the
    linked Newcastle-LGA figures (DECISIONS.md 12.1). So the linked aggregate is
    the one a fit is computed against; the unlinked one is kept only because it
    is what the P3 seed was compared to, and dropping it would make that
    comparison unreproducible.
    """
    h = pd.read_csv(HTS_FILE)
    h = h[(h['FINANCIAL_YEAR'] == HTS_YEAR) & (h['geography'] == 'lga')].copy()
    h['mode'] = (h['TRAVEL_MODE'].str.replace('*', '', regex=False)
                 .str.strip().str.lower())
    t = h.groupby('mode')['TRIPS_BY_MODE'].sum()
    tot = t.sum()
    unlinked = {'car': 100 * t['vehicle driver'] / tot,
                'ride': 100 * t['vehicle passenger'] / tot,
                'walk': 100 * (t['walk only'] + t['walk linked']) / tot,
                'pt': 100 * t['public transport'] / tot,
                'bike_other': 100 * t['other'] / tot}
    n = h[h['area_name'] == HTS_TARGET_LGA].set_index('mode')['MODE_SHARE']
    linked = {'car': float(n['vehicle driver']), 'ride': float(n['vehicle passenger']),
              'walk': float(n['walk only']), 'pt': float(n['public transport']),
              'bike_other': float(n['other'])}
    return ({k: round(v, 2) for k, v in unlinked.items()},
            {k: round(v, 2) for k, v in linked.items()})

# Activity types carried through to the scoring configuration.
ACT_TYPES = ('home', 'work', 'education', 'shopping', 'other', 'business')
TYPICAL_DURATION_S = {'home': 12 * 3600, 'work': 8 * 3600, 'education': 6 * 3600,
                      'shopping': 1 * 3600, 'other': 2 * 3600, 'business': 1 * 3600}
# Proportional sweep on every typical duration. Not Newcastle-specific: this is
# MATSim's scoring shape parameter, not an observable local quantity.
TYPICAL_DURATION_SWEEP = 0.25


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


def pick_mode(car_available, u, table_by_avail=None):
    table = (table_by_avail or SEED_MODE_SPLIT)[bool(car_available)]
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


def write_day(day, attrs, rng, report, seed_table=None):
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
                    tour_mode[tid] = pick_mode(car_av, u, seed_table)
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


def main(seed=SEED, day_types=None, seed_mode='uninformed'):
    day_types = day_types or DAY_TYPES
    seed_table = (SEED_MODE_SPLIT_INFORMED if seed_mode == 'informed'
                  else SEED_MODE_SPLIT)
    hts_unlinked, hts_linked = hts_mode_share()
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(seed)
    print('loading person attributes ...', flush=True)
    attrs = load_person_attributes()
    report = {}
    for d in day_types:
        write_day(d, attrs, rng, report, seed_table)
    meta = dict(seed=seed, seed_mode=seed_mode,
                seed_mode_split={str(k): v for k, v in seed_table.items()},
                seed_mode_sweep=SEED_MODE_SWEEP,
                hts_mode_share_pct=hts_unlinked,
                hts_mode_share_pct_source=(
                    'derived from %s, %s, LGA rows: trips-weighted over the five '
                    'study-area LGAs, unlinked, walk includes the walk stage of a '
                    'PT trip' % (HTS_FILE, HTS_YEAR)),
                hts_calibration_target_pct=hts_linked,
                hts_calibration_target_source=(
                    'derived from %s, %s, %s LGA, published MODE_SHARE column '
                    '(linked trips). This is the basis of validation targets '
                    'V202-V207 and the one a MATSim mode share is comparable to '
                    '(DECISIONS.md 12.1)' % (HTS_FILE, HTS_YEAR, HTS_TARGET_LGA)),
                typical_duration_s=TYPICAL_DURATION_S,
                typical_duration_sweep=TYPICAL_DURATION_SWEEP,
                note='Seed modes are initial conditions for MATSim co-evolution, '
                     'drawn per tour so chain-based modes stay conserved. The '
                     'default seed is UNINFORMED - uniform over the modes each '
                     'person can use, conditioned only on B1 car availability - '
                     'so that the HTS mode share is a target the model has to '
                     'reach rather than one it is handed (DECISIONS.md 9.6). '
                     'Run with --seed-mode informed to reproduce the P3 seed.',
                by_day=report)
    json.dump(meta, open(os.path.join(OUT, '_plans_report.json'), 'w'), indent=2)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', type=int, default=SEED)
    ap.add_argument('--day-types', default=','.join(DAY_TYPES))
    ap.add_argument('--seed-mode', choices=['uninformed', 'informed'],
                    default='uninformed',
                    help='uninformed (default): uniform over usable modes. '
                         'informed: the P3 seed positioned near the HTS '
                         'aggregate, retained so the seed dependence can be '
                         'tested rather than asserted.')
    ap.add_argument('--out', default=None,
                    help='override the output directory (for seed experiments)')
    a = ap.parse_args()
    if a.out:
        OUT = a.out
    main(a.seed, [d for d in a.day_types.split(',') if d], a.seed_mode)
