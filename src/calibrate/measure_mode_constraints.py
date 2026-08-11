#!/usr/bin/env python
"""Observed constraints the calibration must reproduce, derived from the HTS.

MATSim's `ride` is an unconstrained mode. It occupies no vehicle, requires no
driver to exist, consumes no road capacity, and - once the double charge is
removed (DECISIONS.md 9.8) - costs nothing per kilometre. Nothing in the
simulation stops every agent becoming a car passenger at once, and measured over
250 iterations nothing did: the model settled at a ride:car leg ratio of 4.52,
an implied **5.52 people per car**.

A car has about five seats and Newcastle's observed occupancy is 1.35, so that
outcome is not merely a poor fit, it is physically impossible. This script
derives the constraint from the only place it can be observed - the HTS vehicle
driver and vehicle passenger trip counts - so that the value the calibration
targets is measured rather than chosen.

    occupancy   = (driver trips + passenger trips) / driver trips
    passengers  = passenger trips / driver trips

Both are pure ratios of two published counts. Neither is a modelling choice, and
the sweep range is the observed spread across every survey year in the file
rather than an interval anyone picked.
"""
import json
import os

import pandas as pd

HTS = 'data/processed/hts/hts_mode_newcastle.csv'
OUT = 'params/C4_mode_constraints.json'
BASE_YEAR = '2024/25'
TARGET_LGA = 'Newcastle'


def series(h, area=None):
    """occupancy and passenger:driver ratio per financial year."""
    out = {}
    for yr in sorted(h['FINANCIAL_YEAR'].unique()):
        y = h[h['FINANCIAL_YEAR'] == yr]
        if area:
            y = y[y['area_name'] == area]
        t = y.groupby('mode')['TRIPS_BY_MODE'].sum()
        if 'vehicle driver' not in t or 'vehicle passenger' not in t:
            continue
        d, p = float(t['vehicle driver']), float(t['vehicle passenger'])
        if d <= 0:
            continue
        out[yr] = dict(driver_trips=int(d), passenger_trips=int(p),
                       occupancy=round((d + p) / d, 4),
                       passenger_per_driver=round(p / d, 4))
    return out


def main():
    h = pd.read_csv(HTS)
    h = h[h['geography'] == 'lga'].copy()
    h['mode'] = (h['TRAVEL_MODE'].str.replace('*', '', regex=False)
                 .str.strip().str.lower())

    newcastle = series(h, TARGET_LGA)
    study_area = series(h)
    occ = [v['occupancy'] for v in newcastle.values()]
    base = newcastle[BASE_YEAR]

    doc = {
        'source': 'measured - NSW Household Travel Survey, vehicle driver and '
                  'vehicle passenger trip counts by LGA. Both quantities are '
                  'ratios of two published counts; neither is a modelling choice.',
        'base_year': BASE_YEAR,
        'geography': '%s LGA - the geography of mode-share targets V202-V207 '
                     '(DECISIONS.md 12.1)' % TARGET_LGA,
        'vehicle_occupancy': {
            'value': base['occupancy'],
            'sweep': [round(min(occ), 4), round(max(occ), 4)],
            'sweep_basis': 'the observed spread across all %d survey years in '
                           'the file, not a chosen interval' % len(occ),
            'years_observed': len(occ),
        },
        'passenger_per_driver': {
            'value': base['passenger_per_driver'],
            'sweep': [round(min(v['passenger_per_driver']
                                for v in newcastle.values()), 4),
                      round(max(v['passenger_per_driver']
                                for v in newcastle.values()), 4)],
        },
        'constrains': 'asc_car_passenger',
        'constraint_rule':
            "DECISIONS.md 8.5 permits two treatments of the mode constants: "
            "estimate them on the pre-intervention period and hold them fixed, "
            "or CONSTRAIN THEM AND REPORT THE CONSTRAINT. This is the second. "
            "asc_car_passenger is solved so the modelled ride:car leg ratio "
            "reproduces the observed passenger:driver ratio, and the solved "
            "value is reported as a constraint rather than presented as an "
            "estimate. The constrained constant is car passenger - NOT "
            "asc_lr, asc_bus or asc_rail, which stay at their 8.5 priors - so "
            "the effect under test is untouched and this is not the ASC "
            "absorption proposal 9 warns about.",
        'by_year_newcastle': newcastle,
        'by_year_study_area': study_area,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(doc, open(OUT, 'w'), indent=2)
    print('%s: occupancy %.4f (sweep %.4f-%.4f over %d survey years), '
          'passenger:driver %.4f'
          % (TARGET_LGA, doc['vehicle_occupancy']['value'],
             doc['vehicle_occupancy']['sweep'][0],
             doc['vehicle_occupancy']['sweep'][1],
             doc['vehicle_occupancy']['years_observed'],
             doc['passenger_per_driver']['value']))


if __name__ == '__main__':
    main()
