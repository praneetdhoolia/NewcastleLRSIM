#!/usr/bin/env python
"""Deterministic population subsample, with the transit fleet scaled to match.

Two properties matter and neither is free.

**Nested.** A person is kept if a hash of their id falls below the fraction, so
the 1% sample is a strict subset of the 10% sample. Three fractions are then
three views of one population rather than three independent draws, and a
difference between them is a sample-size effect rather than a sampling one.

**Fleet scaled with it.** MATSim enforces transit vehicle capacity at boarding,
and the fleet carries `seats` with `standingRoomInPersons=0` (Bus 70, Tram 180).
At a 10% sample an unscaled bus carries 70 sampled agents, i.e. 700 real ones,
so capacity never binds and crowding silently disappears. Seats are therefore
scaled by the same fraction, with a floor of 1 so no vehicle becomes unusable.

Nothing here reads a validation target, let alone a holdout one.
"""
import argparse
import gzip
import hashlib
import os
import re

import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'build'))
from det_io import gzip_writer  # noqa: E402

SEED = 20260810
PERSON_RE = re.compile(r'<person id="([^"]+)"')
# <ns0:capacity seats="70" standingRoomInPersons="0"> - both numbers are scaled,
# so a fleet that had standing room would scale too, though this one has none.
CAPACITY_RE = re.compile(r'(<[\w:]*capacity\b[^>]*?)'
                         r'(seats|standingRoomInPersons)(=")(\d+)(")')


def keep(person_id, fraction, seed=SEED):
    """Uniform in [0,1) from the person id, so the sample nests by fraction."""
    h = hashlib.blake2b(('%s|%d' % (person_id, seed)).encode(), digest_size=8)
    return int.from_bytes(h.digest(), 'big') / 2 ** 64 < fraction


def subsample_plans(src, dst, fraction, seed=SEED):
    n_in = n_out = 0
    with gzip.open(src, 'rt', encoding='utf-8') as f, gzip_writer(dst) as w:
        buf, pid = None, None
        for line in f:
            if buf is None:
                m = PERSON_RE.search(line)
                if m:
                    buf, pid, n_in = [line], m.group(1), n_in + 1
                elif not line.startswith('\t'):
                    w.write(line)
                continue
            buf.append(line)
            if line.startswith('\t</person>'):
                if keep(pid, fraction, seed):
                    w.write(''.join(buf))
                    n_out += 1
                buf = None
    return n_in, n_out


def scale_transit_capacity(src, dst, fraction):
    """Scale every vehicle type's seat count by the sample fraction."""
    with gzip.open(src, 'rt', encoding='utf-8') as f:
        xml = f.read()
    scaled = []

    def shrink(m):
        before = int(m.group(4))
        # floor of 1 on a non-zero capacity: a vehicle scaled to zero seats
        # would refuse every boarding and silently delete the service
        after = max(1, int(round(before * fraction))) if before else 0
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
    n_in, n_out = subsample_plans(a.plans, a.out_plans, a.fraction, a.seed)
    print('plans: %d of %d persons kept (%.4f)' % (n_out, n_in, n_out / max(n_in, 1)))
    if a.vehicles and a.out_vehicles:
        sc = scale_transit_capacity(a.vehicles, a.out_vehicles, a.fraction)
        print('transit capacity scaled on %d vehicle types: %s'
              % (len(sc), sorted(set(sc))))


if __name__ == '__main__':
    main()
