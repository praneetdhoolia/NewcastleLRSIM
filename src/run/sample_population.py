#!/usr/bin/env python
"""Deterministic population subsample, with the transit fleet scaled to match.

Three properties matter and none is free.

**Whole households.** The sampling UNIT is the household, not the person
(`RUN.sample.unit`, DECISIONS.md 9.45). It was the person until then, and the
cost was invisible because nothing in the model was household-coupled: a sample
drawn per person keeps each member independently, so a household of size n
retains on average f*n of its members and the chance a given person keeps ANY
co-member is 1-(1-f)^(n-1) - about 0.14 at f=0.10 and 0.32 at f=0.25 here. Every
household mechanism was therefore being decided by the sampler, and decided
DIFFERENTLY at each fraction, which is the one thing a sample fraction must not
do. Measured on the two completed pilot arms: the share of `ride` legs whose
household drives at all was 32.6% at 10% and 43.1% at 25%. The price, stated
rather than hidden, is that a household-clustered sample carries more variance
at a given size than a person-wise one.

**Nested.** A unit is kept if a hash of its id falls below the fraction, so the
1% sample is a strict subset of the 10% sample. Three fractions are then three
views of one population rather than three independent draws, and a difference
between them is a sample-size effect rather than a sampling one. Hashing the
HOUSEHOLD id nests exactly as hashing the person id did.

**Fleet scaled with it.** MATSim enforces transit vehicle capacity at boarding,
and the fleet carries `seats` with `standingRoomInPersons=0` (Bus 70, Tram 180).
At a 10% sample an unscaled bus carries 70 sampled agents, i.e. 700 real ones,
so capacity never binds and crowding silently disappears. Seats are therefore
scaled by the same fraction, with a floor of `RUN.sample.transit_capacity_floor`
seats so no vehicle becomes unusable.

Nothing here reads a validation target, let alone a holdout one.
"""
import argparse
import gzip
import hashlib
import os
import re

import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, '..', 'build'))
sys.path.insert(0, os.path.join(_HERE, '..'))
from det_io import gzip_writer  # noqa: E402
import registry                 # noqa: E402

# The seed is NOT a literal here. It resolved from the registry, so there is one
# copy of it and changing it is a declared change - two copies of a number is the
# drift this package cannot absorb (DECISIONS.md 15). run_matsim.py passes
# RUN.machine.seed explicitly; this default only serves a standalone invocation.
SEED = registry.load().get('RUN.machine.seed')
# Nor is the capacity floor. It was a literal `1` here while the registry
# declared RUN.sample.transit_capacity_floor and swept it 1-4, so the sweep
# moved a number the code never read - a declared parameter reaching nothing,
# the issue 21 defect class (issue 12).
CAPACITY_FLOOR = registry.load().get('RUN.sample.transit_capacity_floor')
CAPACITY_FLOOR_DOC = None
# The sampling unit is declared, not typed in. `person` reproduces every run
# made before DECISIONS.md 9.45 byte for byte, which is what makes the two
# comparable within one build.
SAMPLE_UNIT = registry.load().get('RUN.sample.unit')
PERSON_RE = re.compile(r'<person id="([^"]+)"')
# The boundary tiers carry no householdId at all - they have no B1 household -
# so the absence of this attribute is meaningful and those agents keep hashing
# on their own id.
HOUSEHOLD_RE = re.compile(
    r'<attribute name="householdId"[^>]*>([^<]+)</attribute>')
# <ns0:capacity seats="70" standingRoomInPersons="0"> - both numbers are scaled,
# so a fleet that had standing room would scale too, though this one has none.
CAPACITY_RE = re.compile(r'(<[\w:]*capacity\b[^>]*?)'
                         r'(seats|standingRoomInPersons)(=")(\d+)(")')


def keep(person_id, fraction, seed=SEED, household_id=None, unit=None):
    """Uniform in [0,1) from the sampling unit's id, so the sample nests.

    The unit is the household where the agent has one and `RUN.sample.unit`
    says so, and the person otherwise - which covers the external and through
    boundary tiers, household-less by construction. The person key is
    UNCHANGED from before 9.45, so `unit = person` reproduces the old sample
    exactly; the household key is namespaced so a household id and a person id
    that happen to be the same integer are still two independent draws.
    """
    unit = SAMPLE_UNIT if unit is None else unit
    if unit == 'household' and household_id is not None:
        key = 'household|%s|%d' % (household_id, seed)
    else:
        key = '%s|%d' % (person_id, seed)
    h = hashlib.blake2b(key.encode(), digest_size=8)
    return int.from_bytes(h.digest(), 'big') / 2 ** 64 < fraction


def subsample_plans(src, dst, fraction, seed=SEED, unit=None):
    n_in = n_out = n_no_household = 0
    with gzip.open(src, 'rt', encoding='utf-8') as f, gzip_writer(dst) as w:
        buf, pid, hid = None, None, None
        for line in f:
            if buf is None:
                m = PERSON_RE.search(line)
                if m:
                    buf, pid, hid, n_in = [line], m.group(1), None, n_in + 1
                elif not line.startswith('\t'):
                    w.write(line)
                continue
            buf.append(line)
            if hid is None:
                h = HOUSEHOLD_RE.search(line)
                if h:
                    hid = h.group(1)
            if line.startswith('\t</person>'):
                if hid is None:
                    n_no_household += 1
                if keep(pid, fraction, seed, hid, unit):
                    w.write(''.join(buf))
                    n_out += 1
                buf = None
    return n_in, n_out, n_no_household


def scale_transit_capacity(src, dst, fraction, floor=None):
    """Scale every vehicle type's seat count by the sample fraction."""
    if floor is None:
        floor = CAPACITY_FLOOR
    with gzip.open(src, 'rt', encoding='utf-8') as f:
        xml = f.read()
    scaled = []

    def shrink(m):
        before = int(m.group(4))
        # the floor keeps a vehicle usable: one scaled to zero seats would
        # refuse every boarding and silently delete the service. It is
        # RUN.sample.transit_capacity_floor, not a literal.
        after = max(floor, int(round(before * fraction))) if before else 0
        scaled.append((m.group(2), before, after))
        return m.group(1) + m.group(2) + m.group(3) + str(after) + m.group(5)

    out = CAPACITY_RE.sub(shrink, xml)
    with gzip_writer(dst) as w:
        w.write(out)
    return scaled


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plans', required=True)
    ap.add_argument('--vehicles')
    ap.add_argument('--out-plans', required=True)
    ap.add_argument('--out-vehicles')
    ap.add_argument('--fraction', type=float, required=True)
    ap.add_argument('--seed', type=int, default=SEED)
    a = ap.parse_args()
    n_in, n_out, n_hhless = subsample_plans(a.plans, a.out_plans, a.fraction,
                                            a.seed)
    print('plans: %d of %d persons kept (%.4f), unit %s, %d household-less'
          % (n_out, n_in, n_out / max(n_in, 1), SAMPLE_UNIT, n_hhless))
    if a.vehicles and a.out_vehicles:
        sc = scale_transit_capacity(a.vehicles, a.out_vehicles, a.fraction)
        print('transit capacity scaled on %d vehicle types: %s'
              % (len(sc), sorted(set(sc))))


if __name__ == '__main__':
    main()
