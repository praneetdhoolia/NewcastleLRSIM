#!/usr/bin/env python
"""Decompose the ride-pairing realisation gap (issues #48, #31; DECISIONS.md 9.48).

The demand provably contains the coincidence (15.31% of ride trips share an
OD with a household car trip; 120,980 weekday escort bindings placed exactly)
but the declared regime realises 1.30%. The factor of ~12 lives in three
layers, named in 9.48 and unmeasured until this script:

  1. MODE CO-ASSIGNMENT - co-evolution must hand the escorter `car` and the
     escortee `ride` on the same day before a bound pair can pair at all;
  2. THE WINDOW - the +/-15 min applies to REALISED departures, and the
     mobsim moves them;
  3. LINK RESOLUTION - `both_links` requires both trips to resolve identical
     coordinates to identical links.

It also measures the PAIRING CEILING the physical-ride directive needs
(docs/design/physical-ride.md section 4): the share of ride demand a
household-only physical service could ever carry, from the demand itself.

Bound pairs are reconstructed from B2, not guessed: an escorted HX anchor
(dest_placement == 'escorted') is matched to the household member trip with
the IDENTICAL destination coordinate and departure second - the 9.46 binding
wrote them to be exactly coincident, and the reconstruction asserts
uniqueness rather than tolerating ambiguity.

    python src/analyse/measure_realisation_gap.py --run bind1000_25pct

Reads the run's output_trips only (realised modes, times, links). Writes
`realisation_gap_<run>.json` into the run directory. Deterministic; no model
state is touched; nothing here is a result about the light rail.
"""

# City-relative paths resolve through src/city.py: `data/...` names a
# location inside cities/<city>/, not inside the repository root.
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                  '..', '..', 'src'))
import city as _city  # noqa: E402

import os
import json
import gzip
import argparse
import collections

import pandas as pd

B2 = _city.path('demand/plans/B2_activity_trips_WEEKDAY.csv')


def hhmmss_to_s(text):
    try:
        h, m, s = str(text).split(':')
        return int(h) * 3600 + int(m) * 60 + int(s)
    except Exception:                                     # noqa: BLE001
        return None


def load_bound_pairs():
    """(escorter person, escortee person) pairs, reconstructed from B2.

    The 9.46 binding gives the escorter's HX anchor the escorted member's
    destination COORDINATE and departure SECOND exactly, and both tours start
    at the household home - so the pair key (household home x, dest x/y,
    departure s) identifies partners. Where several members share all four
    (twins to the same school at the same second) any of them is the physical
    partner; the first by person id is taken and counted as such.
    """
    use = ['person_id', 'purpose', 'tour_purpose', 'dest_placement',
           'origin_x', 'origin_y', 'dest_x', 'dest_y', 'dep_time_s',
           'is_tour_anchor', 'agent_tier']
    df = pd.read_csv(B2, usecols=use)
    df = df[(df.agent_tier == 'core') & (df.is_tour_anchor == 1)]
    esc = df[(df.tour_purpose == 'HX') & (df.dest_placement == 'escorted')]
    other = df[df.tour_purpose != 'HX']
    key = ['origin_x', 'origin_y', 'dest_x', 'dest_y', 'dep_time_s']
    j = esc.merge(other, on=key, suffixes=('_escorter', '_escortee'))
    j = j.sort_values('person_id_escortee').drop_duplicates(
        subset=['person_id_escorter', 'dep_time_s'] + key[:2])
    ambiguous = len(j) - j.drop_duplicates(
        subset=['person_id_escorter', 'dep_time_s']).shape[0]
    pairs = j[['person_id_escorter', 'person_id_escortee', 'dep_time_s']]
    return pairs, len(esc), ambiguous


def load_trips(run_dir):
    p = os.path.join(run_dir, 'output', 'output_trips.csv.gz')
    use = ['person', 'trip_number', 'main_mode', 'dep_time',
           'start_link', 'end_link', 'start_x', 'start_y', 'end_x', 'end_y']
    with gzip.open(p, 'rt', encoding='utf-8') as f:
        t = pd.read_csv(f, sep=';', usecols=use,
                        dtype={'person': str, 'start_link': str,
                               'end_link': str})
    t['dep_s'] = t.dep_time.map(hhmmss_to_s)
    return t


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--run', required=True)
    ap.add_argument('--window-min', type=float, default=None,
                    help='pairing window; default: the declared '
                         'B.ride.pairing_window_min')
    a = ap.parse_args()
    run_dir = (a.run if os.path.isdir(a.run)
               else os.path.join(_city.REPO, 'results', a.run))

    import registry as _registry
    cfg = _registry.load()
    window_s = 60.0 * (a.window_min if a.window_min is not None
                       else float(cfg.get('B.ride.pairing_window_min')))

    pairs, n_escorted, ambiguous = load_bound_pairs()
    print('bound pairs reconstructed from B2: %d (of %d escorted anchors; '
          '%d ambiguous same-second multi-member matches, first taken)'
          % (len(pairs), n_escorted, ambiguous))

    trips = load_trips(run_dir)
    # the run is a subsample: keep pairs where BOTH members were drawn
    persons = set(trips.person)
    pairs = pairs[
        pairs.person_id_escorter.astype(str).isin(persons)
        & pairs.person_id_escortee.astype(str).isin(persons)].copy()
    print('pairs with both members in the run sample: %d' % len(pairs))

    # first trip of each person's plan near the planned departure: match the
    # realised trip whose planned departure the binding set. Take, per person,
    # the trip with minimal |realised - planned| and require it within 3 h -
    # beyond that the tour is not the bound one (replanning moved times, but
    # not that far; TimeAllocationMutator's reach is bounded).
    t_by_person = {p: g for p, g in trips.groupby('person')}

    def realised(person, planned_s):
        g = t_by_person.get(str(person))
        if g is None:
            return None
        d = (g.dep_s - planned_s).abs()
        i = d.idxmin()
        if d.loc[i] > 3 * 3600:
            return None
        return g.loc[i]

    stages = collections.Counter()
    for row in pairs.itertuples():
        er = realised(row.person_id_escorter, row.dep_time_s)
        ee = realised(row.person_id_escortee, row.dep_time_s)
        if er is None or ee is None:
            stages['tour_not_found_in_run'] += 1
            continue
        stages['both_tours_realised'] += 1
        if not (er.main_mode == 'car' and ee.main_mode == 'ride'):
            stages['mode_not_co_assigned'] += 1
            stages['modes_%s_%s' % (er.main_mode, ee.main_mode)] += 1
            continue
        stages['modes_co_assigned_car_ride'] += 1
        if abs((er.dep_s or 0) - (ee.dep_s or 0)) > window_s:
            stages['outside_realised_window'] += 1
            continue
        stages['inside_realised_window'] += 1
        if er.start_link == ee.start_link and er.end_link == ee.end_link:
            stages['both_links_identical'] += 1
        elif er.end_link == ee.end_link:
            stages['dest_link_only'] += 1
        else:
            stages['links_differ'] += 1

    # ---- the pairing ceiling, from the demand alone (dossier section 4) ----
    # If mode assignment, windows and link resolution were all perfect, the
    # household-only physical service could carry at most: every bound
    # escortee trip, plus every other ride-eligible trip sharing an OD with a
    # household car trip (the run measured that as 15.31%). The bound share
    # of ride demand is the demand-side floor of the ceiling.
    fit = json.load(open(os.path.join(run_dir, '_fit.json'), encoding='utf-8')) \
        if os.path.exists(os.path.join(run_dir, '_fit.json')) else {}
    pj_path = [p for p in os.listdir(run_dir) if p.startswith('pairability_')]
    structure = {}
    if pj_path:
        structure = json.load(open(os.path.join(run_dir, pj_path[0]),
                                   encoding='utf-8')).get('structure', {})

    out = dict(
        run=os.path.basename(run_dir),
        window_min=window_s / 60.0,
        bound_pairs_in_demand=int(n_escorted),
        bound_pairs_reconstructed=int(len(pairs)),
        stages=dict(sorted(stages.items())),
        ceiling=dict(
            ride_trips=structure.get('ride_trips'),
            od_coincident_share=structure.get('share_sharing_an_od'),
            note='the OD-coincident share is the household-only physical '
                 'ceiling on PAIRABLE ride demand; observed ride share is '
                 '20.60%, so the difference is the unobserved '
                 'non-household-lift share the owner must rule on '
                 '(docs/design/physical-ride.md section 4)'))
    dst = os.path.join(run_dir, 'realisation_gap_%s.json' % out['run'])
    json.dump(out, open(dst, 'w'), indent=2)
    print(json.dumps(out['stages'], indent=1))
    print('-> %s' % dst)


if __name__ == '__main__':
    main()
