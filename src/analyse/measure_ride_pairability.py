#!/usr/bin/env python
"""Could the `ride` demand a run produced actually be carried by anyone?

A car passenger is not a mode, it is a SEAT IN SOMEONE ELSE'S CAR. The model may
put any number of agents in that seat; whether a driver exists to be beside is a
separate question, and until this file existed nothing asked it. `rideAvail`
(DECISIONS.md 9.10) asks a much weaker one - does this person's household hold a
vehicle and another licence holder AT ALL - which is a property of the household,
not of the hour, the place or the trip.

This reads a COMPLETED run's own `output_trips.csv.gz`, joins every traveller to
their B1 household, and asks, for each ride trip, whether another member of that
household made a car trip the passenger could plausibly have been inside. It
reports the four declared `B.ride.pairing_rule` values against a spread of
windows, so the answer is a surface rather than a point.

**It is a diagnostic, not a validation.** It reads no target, holdout or
otherwise, and it invents nothing: every quantity here is counted out of the
run's own output and the committed synthetic population. What it produces is a
property of the demand and of the sampler, and it is exactly the check the
project's standing goal asks for - whether sampling a fraction of a population
still predicts the right ridership PER MODE, checked rather than assumed.

**Its headline is negative, and that is the point.** Measured on the two
completed convergence arms (DECISIONS.md 9.44): only 0.10% of ride trips at 25%
shared an origin-destination pair with a household car trip at ANY time of day,
and 56.9% belonged to a household that made no car trip at all. See also
DECISIONS.md 9.45 for the half of that which was the sampler's doing.

    python src/analyse/measure_ride_pairability.py --run conv1000_25pct
    python src/analyse/measure_ride_pairability.py --run conv1000_25pct --json out.json
"""
import argparse
import collections
import gzip
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(_HERE))
RESULTS = os.path.join(ROOT, 'results')
sys.path.insert(0, os.path.join(ROOT, 'src'))

import city as _city          # noqa: E402
import registry               # noqa: E402

# The rules are the declared ones, read from the field rather than listed here:
# a rule this file knew about and the model did not would be a measurement of
# something nobody can run.
RULES = ('both_links', 'origin_link', 'dest_link', 'window_only')
# The reporting grid is DERIVED, never typed: it is the declared sweep's two
# bounds and the declared value itself, so the surface spans exactly the range
# B.ride.pairing_window_min is allowed to take and nothing else. A hand-written
# grid here would be a modelling choice nobody could see or sweep - the same
# defect the hardcoding ledger exists to catch, and it caught this one.
# `--windows` widens it deliberately, for exploration that is labelled as such.


def hhmmss(text):
    """MATSim writes HH:MM:SS, and hours exceed 24 inside the 30 h qsim window."""
    h, m, s = text.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)


def load_trips(run_dir):
    """(person, dep_s, trav_s, mode, start_link, end_link, from_act, to_act)."""
    path = os.path.join(run_dir, 'output', 'output_trips.csv.gz')
    if not os.path.exists(path):
        raise SystemExit('%s holds no output_trips.csv.gz. This reads a '
                         'COMPLETED run, not a run in progress.' % run_dir)
    import csv
    rides, cars = [], []
    with gzip.open(path, 'rt', encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f, delimiter=';'):
            mode = r['main_mode']
            if mode not in ('ride', 'car'):
                continue
            row = (r['person'], hhmmss(r['dep_time']), hhmmss(r['trav_time']),
                   r['start_link'], r['end_link'],
                   r['start_activity_type'], r['end_activity_type'])
            (rides if mode == 'ride' else cars).append(row)
    return rides, cars


def load_households():
    """person id -> household id, from the city's own synthetic population."""
    import csv
    path = _city.path('demand/population/B1_synthetic_population.csv')
    out = {}
    with open(path, encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            out[r['person_id']] = r['household_id']
    return out


def direction(from_act, to_act):
    """Outbound leaves home, return arrives home, anything else is in between.

    `home` is an activity type the demand builder writes and any city has one;
    nothing here is a place.
    """
    if from_act == 'home':
        return 'outbound'
    if to_act == 'home':
        return 'return'
    return 'intermediate'


def endpoints_match(rule, driver, ride):
    if rule == 'both_links':
        return driver[3] == ride[3] and driver[4] == ride[4]
    if rule == 'origin_link':
        return driver[3] == ride[3]
    if rule == 'dest_link':
        return driver[4] == ride[4]
    if rule == 'window_only':
        return True
    raise ValueError(rule)


def pair(rides, cars, hh, rule, window_min, capacity):
    """One (rule, window, capacity) pass. Deterministic: no draw is made here."""
    window = window_min * 60.0
    by_household = collections.defaultdict(list)
    for c in cars:
        h = hh.get(c[0])
        if h is not None:
            by_household[h].append(c)
    for legs in by_household.values():
        legs.sort(key=lambda c: (c[0], c[1]))

    load = collections.Counter()
    paired = collections.Counter()
    unpaired = collections.Counter()
    n_paired = 0
    delta = []
    for ride in sorted(rides, key=lambda r: (r[0], r[1])):
        h = hh.get(ride[0])
        best, best_gap = None, None
        for driver in by_household.get(h, ()):
            if driver[0] == ride[0]:
                continue                        # you cannot drive yourself
            gap = abs(driver[1] - ride[1])
            if gap > window or not endpoints_match(rule, driver, ride):
                continue
            key = (driver[0], driver[1], driver[3], driver[4])
            if load[key] >= capacity:
                continue
            if best_gap is None or gap < best_gap:
                best, best_gap = driver, gap
        d = direction(ride[5], ride[6])
        if best is None:
            unpaired[d] += 1
            continue
        load[(best[0], best[1], best[3], best[4])] += 1
        paired[d] += 1
        n_paired += 1
        delta.append(best[2] - ride[2])
    return n_paired, paired, unpaired, delta


def structure(rides, cars, hh):
    """The two facts that decide everything else, before any rule is applied."""
    driving = {hh.get(c[0]) for c in cars}
    driving.discard(None)
    ride_households = {hh.get(r[0]) for r in rides}
    ride_households.discard(None)
    in_driving = sum(1 for r in rides if hh.get(r[0]) in driving)
    same_od = collections.defaultdict(set)
    for c in cars:
        h = hh.get(c[0])
        if h is not None:
            same_od[(h, c[3], c[4])].add(c[0])
    with_od = sum(1 for r in rides
                  if any(p != r[0] for p in same_od.get((hh.get(r[0]), r[3], r[4]), ())))
    no_household = sum(1 for r in rides if hh.get(r[0]) is None)
    return dict(
        ride_trips=len(rides), car_trips=len(cars),
        ride_trips_without_household=no_household,
        households_making_ride_trips=len(ride_households),
        ride_trips_in_a_household_that_drives_at_all=in_driving,
        share_in_a_household_that_drives=round(in_driving / max(len(rides), 1), 4),
        ride_trips_sharing_an_od_with_a_household_car_trip=with_od,
        share_sharing_an_od=round(with_od / max(len(rides), 1), 6))


def window_sweep():
    """The declared interval, whichever of the two schema shapes it takes.

    field.schema.json allows a bare two-element array as shorthand for
    {"interval": [...]}, and both are legal, so a reader that knew only one
    would break on a field it had no reason to care about.
    """
    sweep = registry.load().sweep('B.ride.pairing_window_min')
    lo, hi = sweep['interval'] if isinstance(sweep, dict) else sweep
    return float(lo), float(hi)


def lo_hi_contains(window_min):
    lo, hi = window_sweep()
    return lo <= window_min <= hi


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--run', required=True,
                    help='a completed run directory, or its name under results/')
    ap.add_argument('--capacity', type=int, default=None,
                    help='override B.ride.max_passengers_per_vehicle')
    ap.add_argument('--windows',
                    help='comma-separated minutes, widening the surface beyond '
                         'the declared sweep. EXPLORATORY: anything reported '
                         'from a window outside the declared sweep of '
                         'B.ride.pairing_window_min is outside the range the '
                         'model may take.')
    ap.add_argument('--json', help='write the full surface here')
    a = ap.parse_args()

    run_dir = a.run if os.path.isdir(a.run) else os.path.join(RESULTS, a.run)
    if not os.path.isdir(run_dir):
        raise SystemExit('no such run: %s' % a.run)

    cfg = registry.load()
    capacity = a.capacity or cfg.get('B.ride.max_passengers_per_vehicle')
    declared_rule = cfg.get('B.ride.pairing_rule')
    declared_window = cfg.get('B.ride.pairing_window_min')
    if a.windows:
        windows = tuple(float(w) for w in a.windows.split(','))
        exploratory = True
    else:
        lo, hi = window_sweep()
        windows = tuple(sorted({float(lo), float(declared_window), float(hi)}))
        exploratory = False

    rides, cars = load_trips(run_dir)
    hh = load_households()
    facts = structure(rides, cars, hh)

    print('%s' % os.path.basename(run_dir))
    print('  ride trips %d, car trips %d, %d ride trips with no household '
          '(the boundary tiers)'
          % (facts['ride_trips'], facts['car_trips'],
             facts['ride_trips_without_household']))
    print('  in a household that drives AT ALL that day: %d (%.3f)'
          % (facts['ride_trips_in_a_household_that_drives_at_all'],
             facts['share_in_a_household_that_drives']))
    print('  sharing an origin-destination pair with a household car trip, at '
          'ANY time: %d (%.5f)'
          % (facts['ride_trips_sharing_an_od_with_a_household_car_trip'],
             facts['share_sharing_an_od']))
    print('  declared regime: rule %s, window %g min, capacity %d'
          % (declared_rule, declared_window, capacity))
    print()
    print('%-12s %7s %9s %8s   %-30s %s'
          % ('rule', 'window', 'paired', 'rate', 'unpaired by direction', 'occupancy'))

    doc = dict(run=os.path.basename(run_dir), capacity=capacity,
               declared_rule=declared_rule, declared_window_min=declared_window,
               windows_min=list(windows), windows_are_exploratory=exploratory,
               structure=facts, surface=[])
    for rule in RULES:
        for window_min in windows:
            n, paired, unpaired, delta = pair(rides, cars, hh, rule, window_min,
                                              capacity)
            rate = n / max(len(rides), 1)
            mark = ' <- declared' if (rule == declared_rule
                                      and window_min == declared_window) else ''
            if exploratory:
                mark += ' (exploratory: outside the declared sweep)'                     if not lo_hi_contains(window_min) else ''
            print('%-12s %7g %9d %8.4f   %-30s %.4f%s'
                  % (rule, window_min, n, rate,
                     ' '.join('%s=%d' % (k, unpaired[k])
                              for k in ('outbound', 'return', 'intermediate')),
                     n / max(len(cars), 1), mark))
            doc['surface'].append(dict(
                rule=rule, window_min=window_min, paired=n,
                paired_rate=round(rate, 6),
                occupancy_from_pairings=round(n / max(len(cars), 1), 6),
                paired_by_direction=dict(paired),
                unpaired_by_direction=dict(unpaired),
                median_driver_minus_passenger_s=(
                    None if not delta
                    else round(sorted(delta)[len(delta) // 2], 1))))

    if a.json:
        with open(a.json, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(doc, f, indent=2)
            f.write('\n')
        print('\nwrote %s' % a.json)


if __name__ == '__main__':
    main()
