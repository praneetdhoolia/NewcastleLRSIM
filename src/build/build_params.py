#!/usr/bin/env python
"""Layer C1 - behavioural parameter sets, with sweep ranges.

Proposal section 6.1: "This layer decides the answer." Every row therefore
carries `source` and an explicit sweep range, and every row with
source='assumed' is mirrored in DECISIONS.md.

beta_transfer_penalty_min is the parameter the whole policy question turns on
(proposal 6.2): a five-minute-equivalent penalty produces a broadly favourable
result for the light rail, a twelve-minute penalty produces a net disbenefit for
external origins. It is never reported as a point estimate - the sweep grid
below is mandatory for every headline finding.

Money values are 2026 AUD. Base values follow the ATAP PV2 / TfNSW Economic
Parameter Values conventions; they are marked source='literature' where taken
from published guidance and source='assumed' where chosen by judgement.
"""
import os
import csv
import json
import itertools

# Model inputs come from config/registry/, not from literals in this file. Every
# value below carries its units, provenance and either a sweep, a held-fixed rule
# or a derived-from identity there. See DECISIONS.md 15.
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import registry as _registry  # noqa: E402
CFG = _registry.load()

OUT = 'params'
os.makedirs(OUT, exist_ok=True)

# --------------------------------------------------------------------------
# Trip purposes, mapped to the B2 schema codes
#   HW  home-work (commute)          HE  home-education
#   HS  home-shopping                HO  home-other (personal business, social)
#   WB  work-related business        NHB non-home-based
# --------------------------------------------------------------------------
PURPOSES = ['HW', 'HE', 'HS', 'HO', 'WB', 'NHB']

# value of travel time savings, AUD per hour, 2026 prices
VOT = CFG.get('C.vot.by_purpose')
VOT_SWEEP = {k: (round(v * 0.7, 2), round(v * 1.3, 2)) for k, v in VOT.items()}

# multipliers on in-vehicle time (beta_ivt is the numeraire = 1.0)
WEIGHTS = {
    'beta_ivt':            (1.00, 1.00, 1.00, 'definition'),
    'beta_walk_access':    (2.00, 1.50, 2.50, 'literature'),
    'beta_walk_egress':    (2.00, 1.50, 2.50, 'literature'),
    'beta_wait':           (2.00, 1.50, 2.50, 'literature'),
    'beta_headway':        (0.50, 0.35, 0.65, 'literature'),
    'beta_reliability':    (1.30, 0.80, 1.80, 'literature'),
    'beta_crowding_seated': (1.00, 1.00, 1.10, 'literature'),
    'beta_crowding_standing': (1.45, 1.15, 1.85, 'literature'),
    'beta_gradient_uphill': (0.09, 0.04, 0.15, 'assumed'),
    'beta_gradient_downhill': (0.02, 0.00, 0.05, 'assumed'),
}

# THE parameter. Minutes of in-vehicle-time equivalent per transfer, on top of
# the actual wait. Swept across the full plausible range in every run.
TRANSFER_PENALTY = dict(base=8.0, low=3.0, high=15.0,
                        grid=[3.0, 5.0, 6.5, 8.0, 10.0, 12.0, 15.0],
                        source='assumed',
                        estimation_route='NSW HTS interchange rates + Opal tap '
                                         'sequence at Newcastle Interchange')

# alternative-specific constants, relative to car driver = 0.
# To be estimated on the pre-intervention period and held fixed (proposal s9,
# ASC absorption). Values here are priors for the first calibration pass.
ASC = {'asc_car_driver': (0.00, 'definition'),
       'asc_car_passenger': (-0.85, 'assumed'),
       'asc_bus': (-1.05, 'assumed'),
       'asc_lr': (-0.75, 'assumed'),
       'asc_rail': (-0.65, 'assumed'),
       'asc_walk': (0.35, 'assumed'),
       'asc_cycle': (-1.35, 'assumed')}

# walk access decay. Proposal 6.3 forbids a threshold: a 400 m cut-off treats a
# person at 401 m as identical to one at 2 km and flatters fixed-route modes.
WALK_DECAY = dict(function='negative_exponential',
                  params={'beta_per_m': 0.0018},
                  sweep={'beta_per_m': [0.0010, 0.0014, 0.0018, 0.0024, 0.0030]},
                  alternative='cumulative_gaussian',
                  alternative_params={'mu_m': 700, 'sigma_m': 420},
                  max_considered_m=2500,
                  source='assumed',
                  note='At beta=0.0018 the weight is 0.49 at 400 m, 0.24 at 800 m '
                       'and 0.12 at 1200 m. Never truncate at 400 m.')

NEST = dict(structure='nested_logit',
            nests={'motorised_pt': ['bus', 'lr', 'rail'],
                   'private': ['car_driver', 'car_passenger'],
                   'active': ['walk', 'cycle']},
            nesting_coefficient_pt=0.65,
            nesting_coefficient_private=0.80,
            nesting_coefficient_active=0.70,
            source='assumed')

SEGMENTS = [
    ('all', 'population average'),
    ('car_available', 'household has >=1 vehicle and person holds a licence'),
    ('car_unavailable', 'no household vehicle or no licence'),
    ('concession', 'concession / senior / pensioner Opal holder'),
    ('student', 'full-time student'),
]


def rows_c1():
    out = []
    for seg, seg_desc in SEGMENTS:
        for pur in PURPOSES:
            vot = VOT[pur]
            # car-unavailable travellers have a lower money value of time but a
            # higher penalty on walking and waiting
            adj_walk = 1.15 if seg == 'car_unavailable' else 1.0
            adj_vot = 0.75 if seg in ('car_unavailable', 'concession', 'student') else 1.0
            r = dict(param_set_id='C1_%s_%s' % (seg, pur), segment_id=seg,
                     segment_desc=seg_desc, purpose=pur,
                     vot_aud_hr=round(vot * adj_vot, 2),
                     vot_sweep_low=VOT_SWEEP[pur][0], vot_sweep_high=VOT_SWEEP[pur][1],
                     vot_source='literature',
                     beta_cost_per_aud=round(1.0 / (vot * adj_vot / 60.0), 4),
                     beta_transfer_penalty_min=TRANSFER_PENALTY['base'],
                     beta_transfer_penalty_low=TRANSFER_PENALTY['low'],
                     beta_transfer_penalty_high=TRANSFER_PENALTY['high'],
                     beta_transfer_penalty_source=TRANSFER_PENALTY['source'],
                     walk_decay_function=WALK_DECAY['function'],
                     walk_decay_beta_per_m=WALK_DECAY['params']['beta_per_m'],
                     walk_decay_source=WALK_DECAY['source'],
                     nesting_structure=NEST['structure'])
            for k, (base, lo, hi, src) in WEIGHTS.items():
                v = base * (adj_walk if 'walk' in k else 1.0)
                r[k] = round(v, 3)
                r[k + '_low'] = lo
                r[k + '_high'] = hi
                r[k + '_source'] = src
            for k, (v, src) in ASC.items():
                r[k] = v
                r[k + '_source'] = src
            r['source'] = 'mixed'
            out.append(r)
    return out


def rows_sweep():
    """The mandatory sensitivity grid. Every headline finding is reported as a
    curve across this grid, never as a point estimate (proposal 3.4 S-d)."""
    out = []
    i = 0
    for tp in TRANSFER_PENALTY['grid']:
        for wd in WALK_DECAY['sweep']['beta_per_m']:
            for ch in [0.0, 10.0, 20.0, 35.0]:
                i += 1
                out.append(dict(sweep_id='SW%04d' % i,
                                beta_transfer_penalty_min=tp,
                                walk_decay_beta_per_m=wd,
                                dwell_charging_s=ch,
                                is_baseline=int(tp == TRANSFER_PENALTY['base'] and
                                                wd == WALK_DECAY['params']['beta_per_m'] and
                                                ch == 20.0)))
    return out


def _w(name, rows):
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with open(os.path.join(OUT, name), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    print('wrote %-40s %d rows x %d cols' % (name, len(rows), len(cols)))


if __name__ == '__main__':
    c1 = rows_c1()
    _w('C1_behavioural_parameters.csv', c1)
    sw = rows_sweep()
    _w('C1_sensitivity_sweep_grid.csv', sw)
    json.dump(dict(vot_aud_hr=VOT, weights={k: dict(base=v[0], low=v[1], high=v[2], source=v[3])
                                            for k, v in WEIGHTS.items()},
                   transfer_penalty=TRANSFER_PENALTY, asc=ASC,
                   walk_decay=WALK_DECAY, nesting=NEST,
                   n_param_sets=len(c1), n_sweep_points=len(sw),
                   assumed_rows=[r['param_set_id'] for r in c1]),
              open(os.path.join(OUT, 'C1_parameters.json'), 'w'), indent=2)
    # the list DECISIONS.md must carry
    assumed = sorted({k for k, v in WEIGHTS.items() if v[3] == 'assumed'} |
                     {k for k, v in ASC.items() if v[1] == 'assumed'} |
                     {'beta_transfer_penalty_min', 'walk_decay_beta_per_m',
                      'nesting_coefficients'})
    print('\nparameters with source=assumed (must appear in DECISIONS.md):')
    for a in assumed:
        print('   -', a)
