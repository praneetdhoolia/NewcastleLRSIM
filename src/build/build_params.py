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

# Model inputs come from cities/<city>/registry/, not from literals here. Every
# value below carries its units, provenance and either a sweep, a held-fixed rule
# or a derived-from identity there. See DECISIONS.md 15.
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import city as _city  # noqa: E402
import registry as _registry  # noqa: E402
CFG = _registry.load()

OUT = _city.path('params')
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
_VOT_PROP = CFG.field('C.vot.by_purpose')['sweep']['proportional']
VOT_SWEEP = {k: (round(v * (1.0 - _VOT_PROP), 2), round(v * (1.0 + _VOT_PROP), 2))
             for k, v in VOT.items()}
# Segment adjustments, both declared: concession/student/car-unavailable pay a
# lower money value of time, and the car-unavailable face walk and wait without
# an alternative.
VOT_ADJ = CFG.get('C.vot.concession_factor')
WALK_ADJ = CFG.get('C.vot.car_unavailable_walk_factor')

# Everything below is RESOLVED FROM THE REGISTRY, not typed here. Until
# DECISIONS.md 9.32 it was typed here, and the registry copy was a mirror that
# reached nothing: setting C.transfer.beta_transfer_penalty_min - the parameter
# proposal 6.2 says the whole policy question turns on - through an overlay, an
# environment variable or the resolver's own override path left
# C1_parameters.json byte-identical, because this file is what the model reads
# and it never asked. Seventh instance of that defect class.
#
# The direction of the relationship is the fix: C1 is GENERATED from the
# registry rather than checked against it.
def _base(key):
    return CFG.get(key)


def _lo_hi(key):
    """The declared [lo, hi] for a field, from its own sweep.

    A field with no sweep is not free to move - `definition`, or `held_fixed`
    under DECISIONS.md 8.5 - so its range is the point itself. Inventing an
    interval for a value nobody may tune is the fabrication proposal 8.1 exists
    to prevent.
    """
    sweep = CFG.field(key).get('sweep')
    if isinstance(sweep, list) and len(sweep) == 2:
        return float(sweep[0]), float(sweep[1])
    if isinstance(sweep, dict) and 'interval' in sweep:
        return float(sweep['interval'][0]), float(sweep['interval'][1])
    value = float(CFG.get(key))
    return value, value


def _triple(key):
    lo, hi = _lo_hi(key)
    return (float(CFG.get(key)), lo, hi, CFG.source(key))


# multipliers on in-vehicle time (beta_ivt is the numeraire = 1.0)
WEIGHT_FIELDS = [
    ('beta_ivt', 'C.time_weights.beta_ivt'),
    ('beta_walk_access', 'C.time_weights.beta_walk_access'),
    ('beta_walk_egress', 'C.time_weights.beta_walk_egress'),
    ('beta_wait', 'C.time_weights.beta_wait'),
    ('beta_headway', 'C.time_weights.beta_headway'),
    ('beta_reliability', 'C.time_weights.beta_reliability'),
    ('beta_crowding_seated', 'C.crowding.seated_multiplier'),
    ('beta_crowding_standing', 'C.crowding.standing_multiplier'),
    ('beta_gradient_uphill', 'C.gradient.uphill_penalty_per_pct'),
    ('beta_gradient_downhill', 'C.gradient.downhill_penalty_per_pct'),
]
WEIGHTS = {name: _triple(key) for name, key in WEIGHT_FIELDS}

# THE parameter. Minutes of in-vehicle-time equivalent per transfer, on top of
# the actual wait. Swept across the full plausible range in every run.
TP_KEY = 'C.transfer.beta_transfer_penalty_min'
_TP_LO, _TP_HI = _lo_hi(TP_KEY)
TRANSFER_PENALTY = dict(base=_base(TP_KEY), low=_TP_LO, high=_TP_HI,
                        grid=list(CFG.get('C.transfer.penalty_sweep_grid')),
                        source=CFG.source(TP_KEY),
                        estimation_route='NOT ESTIMABLE FROM THIS PACKAGE - see '
                                         'DECISIONS.md 9.32. Proposal 7.2 asks for '
                                         'tap-on/tap-off TIMING and every Opal source '
                                         'held is a monthly aggregate; the stop-level '
                                         'tap data is holdout; no calibration target '
                                         'bears on interchange. The sweep stands.')
# The grid must cover the range it claims to sample, or a headline reported
# "across the plausible range" would not be.
if TRANSFER_PENALTY['grid'][0] != _TP_LO or TRANSFER_PENALTY['grid'][-1] != _TP_HI:
    raise SystemExit('C.transfer.penalty_sweep_grid runs %g-%g but the declared sweep '
                     'is %g-%g: the mandatory sensitivity grid would not span the range '
                     'proposal 3.4 S-d requires every headline to be reported across'
                     % (TRANSFER_PENALTY['grid'][0], TRANSFER_PENALTY['grid'][-1],
                        _TP_LO, _TP_HI))
if TRANSFER_PENALTY['base'] not in TRANSFER_PENALTY['grid']:
    raise SystemExit('the transfer-penalty base %g is not a member of its own sweep '
                     'grid, so no grid row is the baseline'
                     % TRANSFER_PENALTY['base'])

# alternative-specific constants, relative to car driver = 0. HELD FIXED under
# DECISIONS.md 8.5 - calibrating them would fit away the effect under test - so
# they carry no sweep, and _lo_hi collapses to the point value.
ASC_FIELDS = [('asc_car_driver', 'C.asc.car_driver'),
              ('asc_car_passenger', 'C.asc.car_passenger'),
              ('asc_bus', 'C.asc.bus'),
              ('asc_lr', 'C.asc.light_rail'),
              ('asc_rail', 'C.asc.rail'),
              ('asc_walk', 'C.asc.walk'),
              ('asc_cycle', 'C.asc.cycle')]
ASC = {name: (float(CFG.get(key)), CFG.source(key)) for name, key in ASC_FIELDS}

# walk access decay. Proposal 6.3 forbids a threshold: a 400 m cut-off treats a
# person at 401 m as identical to one at 2 km and flatters fixed-route modes.
_WD_LO, _WD_HI = _lo_hi('C.walk.decay_beta_per_m')
WALK_DECAY = dict(function=CFG.get('C.walk.decay_form'),
                  params={'beta_per_m': CFG.get('C.walk.decay_beta_per_m')},
                  sweep={'beta_per_m': [_WD_LO, _WD_HI]},
                  alternative='cumulative_gaussian',
                  alternative_params={'mu_m': CFG.get('C.walk.gaussian_mu_m'),
                                      'sigma_m': CFG.get('C.walk.gaussian_sigma_m')},
                  max_considered_m=CFG.get('C.walk.max_considered_m'),
                  source=CFG.source('C.walk.decay_beta_per_m'),
                  note='At beta=0.0018 the weight is 0.49 at 400 m, 0.24 at 800 m '
                       'and 0.12 at 1200 m. Never truncate at 400 m.')

NEST = dict(structure='nested_logit',
            nests={'motorised_pt': ['bus', 'lr', 'rail'],
                   'private': ['car_driver', 'car_passenger'],
                   'active': ['walk', 'cycle']},
            nesting_coefficient_pt=CFG.get('C.nesting.pt_coefficient'),
            nesting_coefficient_private=CFG.get('C.nesting.private_coefficient'),
            nesting_coefficient_active=CFG.get('C.nesting.active_coefficient'),
            source=CFG.source('C.nesting.pt_coefficient'))

# The dwell axis samples an UNOBTAINED field, so the grid is declared and the
# field stays null. The baseline point lives in the reference scenario's own
# overlay, which is where DECISIONS.md 4.3 says it lives - resolving that
# overlay is how it is read, rather than repeating 20.0 here.
DWELL_GRID = list(CFG.get('A.lightrail.dwell_sweep_grid'))
DWELL_BASELINE = _registry.load(
    scenario=CFG.get('E.matrix.reference_scenario')).get('A.lightrail.dwell_charging_s')
if DWELL_BASELINE not in DWELL_GRID:
    raise SystemExit('the reference scenario sets a charging dwell of %g s, which is '
                     'not a member of A.lightrail.dwell_sweep_grid %s: no grid row '
                     'would be the baseline' % (DWELL_BASELINE, DWELL_GRID))

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
            adj_walk = WALK_ADJ if seg == 'car_unavailable' else 1.0
            adj_vot = VOT_ADJ if seg in ('car_unavailable', 'concession',
                                         'student') else 1.0
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
    curve across this grid, never as a point estimate (proposal 3.4 S-d).

    `walk_decay_beta_per_m` was a third axis of five levels and is NOT one any
    more. It reaches the model through nothing - zero occurrences of the decay
    curve in the generated MATSim config, and it is named in `not_representable`
    for that reason (issue 21, DECISIONS.md 9.3). Sweeping it five ways produced
    a sensitivity band of exactly zero by construction, which would have been
    reported as "insensitive to walk access" when the truth is "walk decay is
    not in the model" - a false negative, and worse than an absent one. It also
    consumed four fifths of the grid: 140 points, of which 112 could not differ
    from another point for any reason a reader would care about.

    140 -> 28 (DECISIONS.md 9.22). The axis returns the day the curve reaches
    the model, and not before.
    """
    out = []
    i = 0
    for tp in TRANSFER_PENALTY['grid']:
        for ch in DWELL_GRID:
            i += 1
            out.append(dict(sweep_id='SW%04d' % i,
                            beta_transfer_penalty_min=tp,
                            dwell_charging_s=ch,
                            is_baseline=int(tp == TRANSFER_PENALTY['base'] and
                                            ch == DWELL_BASELINE)))
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
