#!/usr/bin/env python
"""Layer B2 - tour-based activity chains for the synthetic population.

Replaces the activity-generation half of `build_population.py`. B1 (persons and
households) is reused unchanged; only the chains are rebuilt.

Why rebuild
-----------
The P1 chains were a list of activities in random order, joined end to end and
closed with one trip home. Measured on the delivered file:

  * every non-home destination sat on one of 1,481 zone centroids, and a single
    centroid absorbed 158,431 of 1,452,065 activity legs;
  * 684,125 legs (47%) carried a home-based purpose but did not start at home;
  * all 568,631 closing legs were labelled NHB, so 70% of "NHB" was going home;
  * every person's day was one home-to-home loop, which gives MATSim exactly one
    subtour per agent and makes chain-based mode choice all-or-nothing;
  * 1.8% of arrivals fell after the end of the day, the latest at 36.0 h;
  * there was one generic day, though the schedules carry WEEKDAY/SAT/SUN.

What this builds instead
------------------------
A day is a sequence of home-anchored **tours**. Each tour leaves home, reaches a
primary activity, optionally makes intermediate stops, and returns home. Trip
purpose follows the standard four-step convention - a home-based leg carries its
tour's purpose in either direction, and only genuinely non-home-based legs are
NHB - so the return trip from work is HW, not NHB.

Destinations are placed **inside** the zone on an observed point of attraction
where one exists (23,697 D1 POIs, 10,796 CBD building footprints), and only fall
back to a jittered point where a zone has neither. 79.3% of core zones have at
least one POI.

Three day types are produced. The HTS tables carry no day-of-week dimension, so
the day-type profile is **assumed and swept**; its *level* is not free - the
weekday/Saturday/Sunday rates are rescaled so the week average reproduces the
observed HTS trip rate exactly.

Determinism: one seeded generator, persons visited in sorted id order, zone and
POI arrays built in sorted order. Same seed reproduces the file byte for byte.
"""
import os
import csv
import json
import math
import argparse
import collections

import numpy as np
import pandas as pd

ZON = 'data/processed/zones'
LU = 'data/processed/landuse'
HTS = 'data/processed/hts'
POP = 'demand/population'
OUT = 'demand/plans'

SEED = 20260810
PURPOSES = ['HW', 'HE', 'HS', 'HO', 'WB', 'NHB']
DAY_TYPES = ['WEEKDAY', 'SAT', 'SUN']
DAYS_PER_WEEK = {'WEEKDAY': 5.0, 'SAT': 1.0, 'SUN': 1.0}

# MATSim activity type per trip purpose. `home` is emitted for the leg that
# closes a tour; the purpose column still carries the tour purpose.
ACT_TYPE = {'HW': 'work', 'HE': 'education', 'HS': 'shopping',
            'HO': 'other', 'WB': 'business', 'NHB': 'other'}

# ---------------------------------------------------------------------------
# Assumed parameters. Every one of these is recorded in DECISIONS.md with a
# sweep range; none is observed.
# ---------------------------------------------------------------------------

# Day-type shape. The HTS LGA tables have no day-of-week dimension (checked in
# the raw workbook: FINANCIAL_YEAR / LGA / MODE / PURPOSE only), so the relative
# profile is assumed. The absolute level is *not* assumed: RATE_SHAPE is
# rescaled at run time so 5xWEEKDAY + SAT + SUN reproduces the HTS week average.
DAY_RATE_SHAPE = {'WEEKDAY': 1.06, 'SAT': 0.95, 'SUN': 0.80}
DAY_RATE_SWEEP = {'WEEKDAY': (1.00, 1.12), 'SAT': (0.85, 1.05), 'SUN': (0.70, 0.92)}

# How the purpose mix shifts by day type, as a multiplier on the weekday rate
# for that purpose. Commute and education collapse at the weekend; shopping and
# social rise. Assumed.
DAY_PURPOSE_MIX = {
    'WEEKDAY': {'HW': 1.00, 'HE': 1.00, 'HS': 0.90, 'HO': 0.90, 'WB': 1.00, 'NHB': 1.00},
    'SAT':     {'HW': 0.25, 'HE': 0.05, 'HS': 1.60, 'HO': 1.50, 'WB': 0.15, 'NHB': 1.10},
    'SUN':     {'HW': 0.18, 'HE': 0.02, 'HS': 1.00, 'HO': 1.60, 'WB': 0.10, 'NHB': 1.00},
}

# Probability that a person with the relevant status makes their mandatory tour
# on a given day type. Assumed.
P_MANDATORY = {
    'WEEKDAY': {'work': 0.78, 'education': 0.85},
    'SAT': {'work': 0.16, 'education': 0.03},
    'SUN': {'work': 0.09, 'education': 0.01},
}

# Probability a tour includes an intermediate stop, by tour purpose. This is
# what creates genuine sub-tours, and therefore what lets MATSim's mode choice
# vary within a day rather than for the whole day at once. Assumed.
P_INTERMEDIATE_STOP = {'HW': 0.22, 'HE': 0.12, 'HS': 0.18, 'HO': 0.20, 'WB': 0.30}
P_SECOND_STOP = 0.25          # given a first intermediate stop
# Share of an under-12's drawn secondary tours that are actually made alone.
# Applied as per-tour thinning, not as a scaling of the count.
CHILD_TOUR_RETENTION = 0.4
P_INTERMEDIATE_SWEEP = (0.10, 0.35)

# Straight-line to network distance. Used only to compare the gravity model's
# realised distances against the HTS journey distances, which are network
# distances. Assumed.
DETOUR_FACTOR = 1.30
DETOUR_SWEEP = (1.20, 1.40)

# Mean activity duration in minutes by purpose (carried from P1, DECISIONS 9).
ACT_DURATION = {'HW': 465, 'HE': 360, 'HS': 45, 'HO': 90, 'WB': 60, 'NHB': 20}
DURATION_CV = 0.30

# The day closes. Chains are compressed rather than allowed to run past this.
DAY_HORIZON_S = 30 * 3600

# Departure-time profiles by purpose, probability by hour 0..23 (carried from
# P1, DECISIONS 9; assumed, NSW-typical shapes). Weekend tours start later; the
# shift is applied as a whole-profile roll, and is assumed.
DEPART = {
    'HW':  [.002, .001, .001, .002, .010, .045, .110, .190, .175, .085, .040, .030,
            .028, .028, .030, .035, .050, .055, .035, .020, .012, .008, .005, .003],
    'HE':  [.000, .000, .000, .000, .002, .010, .060, .230, .270, .090, .035, .030,
            .035, .040, .075, .060, .030, .015, .008, .005, .003, .002, .000, .000],
    'HS':  [.001, .001, .000, .001, .002, .008, .020, .040, .070, .095, .110, .110,
            .100, .095, .090, .080, .065, .050, .030, .018, .008, .004, .002, .001],
    'HO':  [.004, .002, .002, .002, .005, .015, .035, .060, .075, .080, .080, .080,
            .075, .075, .075, .075, .070, .065, .055, .045, .035, .025, .012, .008],
    'WB':  [.001, .001, .001, .002, .005, .020, .055, .090, .110, .120, .115, .100,
            .085, .085, .080, .060, .040, .020, .006, .002, .001, .001, .000, .000],
    'NHB': [.002, .001, .001, .002, .006, .020, .060, .110, .105, .070, .060, .060,
            .060, .070, .100, .095, .070, .050, .030, .018, .008, .004, .002, .001],
}
WEEKEND_DEPARTURE_SHIFT_H = {'WEEKDAY': 0, 'SAT': 1, 'SUN': 1}

# POI categories that are street furniture rather than somewhere anyone travels
# to. Without this, 5,628 parking spaces and 652 benches would out-vote every
# shop in the study area.
FURNITURE = frozenset((
    'amenity:parking_space', 'amenity:parking', 'amenity:parking_entrance',
    'amenity:bench', 'amenity:waste_basket', 'amenity:toilets',
    'amenity:drinking_water', 'amenity:post_box', 'amenity:telephone',
    'amenity:bicycle_parking', 'amenity:shelter', 'amenity:bicycle_repair_station',
    'amenity:motorcycle_parking', 'amenity:charging_station', 'amenity:bbq',
    'amenity:fountain', 'amenity:clock', 'amenity:hunting_stand',
    'leisure:picnic_table', 'leisure:firepit', 'leisure:bleachers',
    'leisure:outdoor_seating', 'leisure:slipway', 'leisure:bird_hide',
    'tourism:viewpoint', 'tourism:information', 'tourism:artwork',
    'tourism:picnic_site',
))

# Which POI groups can host which activity purpose.
PURPOSE_GROUPS = {
    'HW': ('office', 'civic', 'health', 'retail', 'food', 'landuse', 'leisure'),
    'HE': ('civic',),
    'HS': ('retail', 'food', 'landuse'),
    'HO': ('leisure', 'tourism', 'food', 'civic', 'health', 'amenity'),
    'WB': ('office', 'civic', 'landuse'),
    'NHB': ('retail', 'food', 'leisure', 'tourism', 'civic', 'health', 'amenity',
            'office', 'landuse'),
}
EDUCATION_CATEGORIES = ('civic:school', 'civic:university', 'civic:college',
                        'civic:kindergarten', 'civic:childcare')


def norm(a):
    a = np.asarray(a, dtype=float)
    a = np.where(np.isfinite(a) & (a > 0), a, 0.0)
    s = a.sum()
    return a / s if s > 0 else np.full(len(a), 1.0 / len(a))


def hts_rates():
    """Trip rate and mean journey distance per purpose, from the HTS extract."""
    pur = pd.read_csv(os.path.join(HTS, 'hts_purpose_newcastle.csv'))
    pur = pur[(pur.geography == 'lga')]
    yr = sorted(pur.FINANCIAL_YEAR.unique())[-1]
    pur = pur[pur.FINANCIAL_YEAR == yr]
    pmap = {'Commute': 'HW', 'Education/childcare': 'HE', 'Shopping': 'HS',
            'Personal business': 'HO', 'Social/recreation': 'HO',
            'Serve passenger': 'NHB', 'Work related business': 'WB', 'Other': 'HO'}
    pur['p'] = pur.TRAVEL_PURPOSE.str.rstrip('*').map(pmap)
    pur = pur[pur.p.notna()]
    journeys = pur.groupby('p').JOURNEYS_BY_MODE.sum()
    dist = (pur.groupby('p')
            .apply(lambda d: np.average(d.JOURNEY_AVG_DISTANCE,
                                        weights=d.JOURNEYS_BY_MODE.clip(lower=1)),
                   include_groups=False))
    demo = pd.read_csv(os.path.join(HTS, 'hts_mode_newcastle.csv'))
    demo = demo[(demo.geography == 'lga') & (demo.FINANCIAL_YEAR == yr)]
    total_trips = demo.TRIPS_BY_MODE.sum()
    share = journeys / journeys.sum()
    return yr, total_trips, share.to_dict(), dist.to_dict()


def load_zones():
    z = pd.read_csv(os.path.join(LU, 'D1_zone_attractions_SA1.csv'),
                    dtype={'SA1_CODE21': str})
    z = z.sort_values('SA1_CODE21').reset_index(drop=True)
    return z


def load_poi_by_zone(zones):
    """POIs and CBD buildings joined to their SA1, indexed for fast sampling."""
    import geopandas as gpd
    zg = gpd.read_file(os.path.join(ZON, 'zones_SA1.gpkg'))[['SA1_CODE21', 'geometry']]
    poi = pd.read_csv(os.path.join(LU, 'D1_poi.csv'))
    poi = poi[~poi.category.isin(FURNITURE)].copy()
    g = gpd.GeoDataFrame(poi, geometry=gpd.points_from_xy(poi.lon, poi.lat),
                         crs='EPSG:4326').to_crs(zg.crs)
    j = gpd.sjoin(g, zg, how='left', predicate='within')
    j = j[j.SA1_CODE21.notna()]
    pts = gpd.GeoDataFrame(j, geometry=j.geometry, crs=zg.crs).to_crs('EPSG:28356')
    j = j.assign(x=pts.geometry.x.to_numpy(), y=pts.geometry.y.to_numpy())

    bld = pd.read_csv(os.path.join(LU, 'D1_buildings_cbd.csv'))
    gb = gpd.GeoDataFrame(bld, geometry=gpd.points_from_xy(bld.lon, bld.lat),
                          crs='EPSG:4326').to_crs(zg.crs)
    jb = gpd.sjoin(gb, zg, how='left', predicate='within')
    jb = jb[jb.SA1_CODE21.notna()]
    bpts = gpd.GeoDataFrame(jb, geometry=jb.geometry, crs=zg.crs).to_crs('EPSG:28356')
    jb = jb.assign(x=bpts.geometry.x.to_numpy(), y=bpts.geometry.y.to_numpy(),
                   category='building:cbd',
                   category_group='building',
                   attraction_weight=jb.gross_floor_area_m2.fillna(100.0)
                   .clip(lower=1.0) / 1000.0)

    keep = ['SA1_CODE21', 'x', 'y', 'category', 'category_group', 'attraction_weight']
    allp = pd.concat([j[keep], jb[keep]], ignore_index=True)
    allp = allp.sort_values(['SA1_CODE21', 'category', 'x', 'y']).reset_index(drop=True)

    zi = {c: i for i, c in enumerate(zones['SA1_CODE21'])}
    index = {p: collections.defaultdict(lambda: None) for p in PURPOSES}
    store = {}
    for purpose in PURPOSES:
        groups = PURPOSE_GROUPS[purpose]
        sub = allp[allp.category_group.isin(groups) |
                   (allp.category_group == 'building')]
        if purpose == 'HE':
            sub = allp[allp.category.isin(EDUCATION_CATEGORIES)]
        by = {}
        for sa1, grp in sub.groupby('SA1_CODE21', sort=True):
            k = zi.get(sa1)
            if k is None:
                continue
            w = norm(grp.attraction_weight.to_numpy())
            by[k] = (grp.x.to_numpy(), grp.y.to_numpy(), np.cumsum(w))
        store[purpose] = by
    return store, len(allp)


def calibrate_decay(X, Y, ATTR, meandist, prod):
    """Solve the gravity decay so realised mean distance matches the HTS.

    P1 set beta = 1/mean-distance directly, which left education and shopping
    60% long and work-related business 22% short. Bisecting on the realised
    expectation instead ties each purpose to its own HTS journey distance.
    """
    DX = X[None, :] - X[:, None]
    DY = Y[None, :] - Y[:, None]
    DKM = np.hypot(DX, DY) / 1000.0
    del DX, DY
    out, diag = {}, {}
    pw = norm(prod)
    for p in PURPOSES:
        target = max(meandist.get(p, 8.0), 0.8) / DETOUR_FACTOR
        lo, hi = 0.005, 4.0

        def realised(beta):
            w = ATTR[p][None, :] * np.exp(-beta * DKM)
            s = w.sum(axis=1, keepdims=True)
            w = np.divide(w, np.where(s > 0, s, 1.0))
            return float((pw * (w * DKM).sum(axis=1)).sum())

        r_lo, r_hi = realised(lo), realised(hi)
        if not (r_hi <= target <= r_lo):
            beta = 1.0 / target
        else:
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                if realised(mid) > target:
                    lo = mid
                else:
                    hi = mid
            beta = 0.5 * (lo + hi)
        got = realised(beta)
        out[p] = beta
        diag[p] = dict(beta=round(beta, 5),
                       target_straight_km=round(target, 2),
                       realised_straight_km=round(got, 2),
                       hts_network_km=round(meandist.get(p, float('nan')), 2),
                       realised_network_km=round(got * DETOUR_FACTOR, 2))
    CUM = {}
    for p in PURPOSES:
        w = ATTR[p][None, :] * np.exp(-out[p] * DKM)
        s = w.sum(axis=1, keepdims=True)
        w = np.divide(w, np.where(s > 0, s, 1.0))
        CUM[p] = np.cumsum(w, axis=1).astype(np.float32)
    del DKM
    return CUM, diag


def solve_day_rates(total_rate):
    """Scale the assumed day-type shape so the week average matches the HTS."""
    wk = sum(DAYS_PER_WEEK.values())
    avg = sum(DAYS_PER_WEEK[d] * DAY_RATE_SHAPE[d] for d in DAY_TYPES) / wk
    k = total_rate / avg
    return {d: DAY_RATE_SHAPE[d] * k for d in DAY_TYPES}


def legs_per_tour(purpose):
    """Expected legs in one tour: out, back, and any intermediate stop."""
    return 2.0 + P_INTERMEDIATE_STOP.get(purpose, 0.15) * (1.0 + P_SECOND_STOP)


def solve_secondary_rates(day, share, day_rate, employed_frac, student_frac,
                          child_frac):
    """Tour rates for the secondary purposes, given the mandatory tours.

    The target is a *trip* rate, but the model draws *tours*, and a tour is two
    legs plus any intermediate stop. Treating the HTS purpose share as a tour
    count - which is what the first cut of this script did - overshot the trip
    rate by 43%. The day-type purpose mix also has to redistribute rather than
    inflate, so it is renormalised against the HTS share before use.

    Returns (lambda per secondary purpose, diagnostics).
    """
    mix = DAY_PURPOSE_MIX[day]
    w = {p: share.get(p, 0.0) * mix[p] for p in PURPOSES}
    tot = sum(w.values())
    w = {p: (v / tot if tot > 0 else 0.0) for p, v in w.items()}

    mandatory = (P_MANDATORY[day]['work'] * employed_frac * legs_per_tour('HW')
                 + P_MANDATORY[day]['education'] * student_frac * legs_per_tour('HE'))
    secondary_target = max(0.0, day_rate - mandatory)
    sec = ('HS', 'HO', 'WB', 'NHB')
    denom = sum(w[p] * legs_per_tour(p) for p in sec)
    # under-12 secondary tours are thinned after the Poisson draw, so the solve
    # has to expect fewer legs per unit of lambda than the raw tour rate implies
    thin = 1.0 - child_frac * (1.0 - CHILD_TOUR_RETENTION)
    k = secondary_target / (denom * thin) if denom > 0 and thin > 0 else 0.0
    # NHB is not a tour purpose - a non-home-based leg only arises as an
    # intermediate stop - so its weight is folded into the discretionary tours
    lam = {p: k * w[p] for p in ('HS', 'HO', 'WB')}
    lam['HO'] += k * w['NHB']
    return lam, dict(day_rate_target=round(day_rate, 4),
                     mandatory_legs=round(mandatory, 4),
                     secondary_target_legs=round(secondary_target, 4),
                     child_thinning_factor=round(thin, 4),
                     purpose_weights={p: round(v, 4) for p, v in w.items()},
                     tour_lambda={p: round(v, 4) for p, v in lam.items()})


class Uniforms:
    """Buffered uniform draws from one seeded generator.

    Drawing 20 million scalars one at a time dominates the runtime; drawing
    them in blocks does not change the stream, only how often it is refilled.
    """

    def __init__(self, rng, block=1 << 20):
        self.rng = rng
        self.block = block
        self.buf = rng.random(block)
        self.i = 0

    def __call__(self):
        if self.i >= self.buf.size:
            self.buf = self.rng.random(self.block)
            self.i = 0
        v = self.buf[self.i]
        self.i += 1
        return float(v)


ACT_OF_PURPOSE = {'HW': 'work', 'HE': 'education', 'HS': 'shopping',
                  'HO': 'other', 'WB': 'business'}
PURPOSE_OF_ACT = {v: k for k, v in ACT_OF_PURPOSE.items()}


def leg_purpose(from_act, to_act):
    """Standard four-step trip purpose from the two activity ends.

    A home-based leg carries the purpose of its non-home end in either
    direction, so the trip *back* from work is HW. Only legs with neither end
    at home are NHB - which is what "non-home-based" has always meant.
    """
    if from_act == 'home' or to_act == 'home':
        other = to_act if from_act == 'home' else from_act
        return PURPOSE_OF_ACT.get(other, 'HO')
    if to_act == 'business' or from_act == 'business':
        return 'WB'
    return 'NHB'


def place_in_zone(store, purpose, k, zx, zy, rad, u):
    """A coordinate inside the destination zone, on an attractor if one exists."""
    by = store.get(purpose, {}).get(k)
    if by is not None:
        xs, ys, cum = by
        i = int(np.searchsorted(cum, u()))
        if i >= xs.size:
            i = xs.size - 1
        return float(xs[i]), float(ys[i]), 'poi'
    ang = 2.0 * math.pi * u()
    rr = rad * math.sqrt(u())
    return zx + rr * math.cos(ang), zy + rr * math.sin(ang), 'jitter'


def draw_hour(profile, shift, u):
    """Hour of day from a departure profile, rolled for weekend day types."""
    x = u()
    c = 0.0
    for h, p in enumerate(profile):
        c += p
        if x <= c:
            return (h + shift) % 24
    return (23 + shift) % 24


def build_day(person, day, rates, CUM, store, zone_arr, u, pre, dropped):
    """One person's tours for one day type.

    Returns a list of leg dicts. Every tour starts and ends at the person's
    home, so the day decomposes into proper sub-tours for MATSim, and a tour
    that will not fit inside the day horizon is dropped rather than allowed to
    run past midnight.
    """
    X, Y, ZX, ZY, RAD, SA1 = zone_arr
    hx, hy, hz = person['hx'], person['hy'], person['hzi']
    legs = []

    # ---- which tours does this person make today ----
    tours = []
    if person['employed'] and u() < P_MANDATORY[day]['work']:
        tours.append('HW')
    elif person['student'] and u() < P_MANDATORY[day]['education']:
        tours.append('HE')
    for p in ('HS', 'HO', 'WB'):
        if p == 'WB' and not person['employed']:
            continue
        n = pre[p]
        if person['age'] < 12 and n:
            # Children make fewer independent secondary tours. Thin each drawn
            # tour with probability CHILD_TOUR_RETENTION rather than scaling the
            # count - int(n * 0.4) rounds a single tour to zero, which suppressed
            # every under-12 secondary tour instead of 60% of them.
            n = sum(1 for _ in range(n) if u() < CHILD_TOUR_RETENTION)
        tours += [p] * n
    if not tours:
        return legs

    shift = WEEKEND_DEPARTURE_SHIFT_H[day]
    starts = [draw_hour(DEPART[p], shift, u) * 3600 + int(3600 * u())
              for p in tours]
    order = sorted(range(len(tours)), key=lambda i: (starts[i], tours[i], i))

    t_now = None
    tour_id = 0
    for oi in order:
        purpose = tours[oi]
        t_start = starts[oi]
        if t_now is not None and t_start < t_now + 600:
            t_start = t_now + 600
        if t_start > DAY_HORIZON_S - 3600:
            dropped[0] += len(order) - order.index(oi)
            break

        # ---- destination sequence for this tour ----
        primary_k = int(np.searchsorted(CUM[purpose][hz], u()))
        if primary_k >= X.size:
            primary_k = X.size - 1
        chain = [(purpose, primary_k)]
        if u() < P_INTERMEDIATE_STOP.get(purpose, 0.15):
            stop_purpose = 'HS' if u() < 0.5 else 'HO'
            k = int(np.searchsorted(CUM[stop_purpose][primary_k], u()))
            chain.append((stop_purpose, min(k, X.size - 1)))
            if u() < P_SECOND_STOP:
                k2 = int(np.searchsorted(CUM['HO'][chain[-1][1]], u()))
                chain.append(('HO', min(k2, X.size - 1)))

        # ---- walk the tour, home -> ... -> home ----
        cur_x, cur_y, cur_z, cur_act = hx, hy, hz, 'home'
        t = t_start
        pending = []
        ok = True
        for idx, (leg_purpose_hint, k) in enumerate(chain):
            act = ACT_OF_PURPOSE[leg_purpose_hint]
            dx, dy, how = place_in_zone(store, leg_purpose_hint, k,
                                        float(ZX[k]), float(ZY[k]), float(RAD[k]), u)
            dist_km = math.hypot(dx - cur_x, dy - cur_y) / 1000.0
            spd = 26.0 if person['cav'] else 16.0
            tt = int(dist_km / spd * 3600) + 240
            arr = t + tt
            if idx == 0:
                dur = ACT_DURATION[leg_purpose_hint]
            else:
                dur = ACT_DURATION['NHB'] if leg_purpose_hint == 'HO' else \
                    ACT_DURATION[leg_purpose_hint]
            dur = int(max(300, dur * 60 * (1.0 + DURATION_CV * (2.0 * u() - 1.0))))
            pending.append(dict(
                purpose=leg_purpose(cur_act, act), dest_activity_type=act,
                origin_sa1=SA1[cur_z], dest_sa1=SA1[k],
                origin_x=cur_x, origin_y=cur_y, dest_x=dx, dest_y=dy,
                dep_time_s=t, arr_time_s=arr, straight_dist_km=dist_km,
                activity_duration_s=dur, is_tour_anchor=int(idx == 0),
                dest_placement=how))
            cur_x, cur_y, cur_z, cur_act = dx, dy, k, act
            t = arr + dur
        # closing leg home
        dist_km = math.hypot(hx - cur_x, hy - cur_y) / 1000.0
        spd = 26.0 if person['cav'] else 16.0
        tt = int(dist_km / spd * 3600) + 240
        arr_home = t + tt
        if arr_home > DAY_HORIZON_S:
            ok = False
        if not ok:
            dropped[0] += 1
            continue
        pending.append(dict(
            purpose=leg_purpose(cur_act, 'home'), dest_activity_type='home',
            origin_sa1=SA1[cur_z], dest_sa1=SA1[hz],
            origin_x=cur_x, origin_y=cur_y, dest_x=hx, dest_y=hy,
            dep_time_s=t, arr_time_s=arr_home, straight_dist_km=dist_km,
            activity_duration_s=0, is_tour_anchor=0, dest_placement='home'))
        tour_id += 1
        for r in pending:
            r['tour_id'] = tour_id
            r['tour_purpose'] = purpose
        legs += pending
        t_now = arr_home
    return legs



# ---------------------------------------------------------------------------
# External boundary demand
#
# B1 synthesises persons for the 1,500 core SA1s only, so the 201 external SA1s
# - the boundary tier that exists to carry Hunter Line through-demand
# (DECISIONS.md 1, scope decision 3) - generated no travel at all. Their 70,448
# residents are a ninth of the core population and they load the Hunter Line and
# the highways at exactly the point where the corridor's catchment ends.
#
# This is a boundary *treatment*, not a second population synthesis: an external
# agent is a household-less person making one home-based tour into the core. The
# proposal puts full external synthesis, freight and the Port out of scope
# (proposal line 171), and this does not reach past that boundary.
# ---------------------------------------------------------------------------

# Share of external-tier residents making a trip into the core on a weekday.
# Assumed - no journey-linked Opal and no external-tier HTS cell exists to
# estimate it from.
EXTERNAL_INTERACTION_RATE = 0.08
EXTERNAL_INTERACTION_SWEEP = (0.04, 0.15)
EXTERNAL_DAY_FACTOR = {'WEEKDAY': 1.0, 'SAT': 0.40, 'SUN': 0.30}
EXTERNAL_PURPOSE_SPLIT = {'HW': 0.70, 'HO': 0.30}
EXTERNAL_PERSON_ID_BASE = 900000000


def external_agents(zones, core, decay, u, day, seq_base):
    """One home-based tour per boundary agent, from an external SA1 into the core.

    Destinations are drawn over the core zones only, with the same purpose decay
    the resident population uses, so a boundary trip is not systematically
    longer or shorter than a resident one of the same purpose.
    """
    ext = zones[zones.zone_tier == 'external'].reset_index(drop=True)
    if ext.empty:
        return [], 0
    CX = core['x_mga56'].to_numpy(dtype=float)
    CY = core['y_mga56'].to_numpy(dtype=float)
    CSA = core['SA1_CODE21'].to_numpy()
    CRAD = np.sqrt(np.maximum(core['area_km2'].to_numpy(dtype=float), 1e-4)
                   * 1e6 / math.pi) * 0.6
    attr = {p: norm(core['attr_' + p].to_numpy()) for p in ('HW', 'HO')}

    legs = []
    n_agents = 0
    pid = seq_base
    for row in ext.sort_values('SA1_CODE21').itertuples():
        pop = float(getattr(row, 'population', 0.0) or 0.0)
        n = int(round(pop * EXTERNAL_INTERACTION_RATE * EXTERNAL_DAY_FACTOR[day]))
        if n <= 0:
            continue
        ex, ey = float(row.x_mga56), float(row.y_mga56)
        erad = math.sqrt(max(float(row.area_km2), 1e-4) * 1e6 / math.pi) * 0.6
        dkm = np.hypot(CX - ex, CY - ey) / 1000.0
        cum = {}
        for p in ('HW', 'HO'):
            w = attr[p] * np.exp(-decay[p]['beta'] * dkm)
            s = w.sum()
            cum[p] = np.cumsum(w / s) if s > 0 else np.linspace(0, 1, len(CX))
        for _ in range(n):
            pid += 1
            n_agents += 1
            purpose = 'HW' if u() < EXTERNAL_PURPOSE_SPLIT['HW'] else 'HO'
            k = int(np.searchsorted(cum[purpose], u()))
            if k >= CX.size:
                k = CX.size - 1
            ang = 2.0 * math.pi * u()
            rr = erad * math.sqrt(u())
            hx, hy = ex + rr * math.cos(ang), ey + rr * math.sin(ang)
            ang = 2.0 * math.pi * u()
            rr = float(CRAD[k]) * math.sqrt(u())
            dx, dy = float(CX[k]) + rr * math.cos(ang), float(CY[k]) + rr * math.sin(ang)
            dist_km = math.hypot(dx - hx, dy - hy) / 1000.0
            t0 = draw_hour(DEPART[purpose], WEEKEND_DEPARTURE_SHIFT_H[day],
                           u) * 3600 + int(3600 * u())
            tt = int(dist_km / 45.0 * 3600) + 240      # boundary trips are highway
            arr = t0 + tt
            dur = int(max(1800, ACT_DURATION[purpose] * 60
                          * (1.0 + DURATION_CV * (2.0 * u() - 1.0))))
            back = arr + dur
            if back + tt > DAY_HORIZON_S:
                continue
            act = ACT_OF_PURPOSE[purpose]
            common = dict(person_id=pid, day_type=day, tour_id=1, party_size=1,
                          tour_purpose=purpose, agent_tier='external',
                          time_flexibility_band='fixed' if purpose == 'HW' else 'flexible')
            legs.append(dict(common, trip_seq=1, purpose=purpose,
                             dest_activity_type=act,
                             origin_sa1=row.SA1_CODE21, dest_sa1=CSA[k],
                             origin_x=round(hx, 1), origin_y=round(hy, 1),
                             dest_x=round(dx, 1), dest_y=round(dy, 1),
                             dep_time_s=t0, arr_time_s=arr,
                             straight_dist_km=round(dist_km, 3),
                             activity_duration_s=dur, is_tour_anchor=1,
                             dest_placement='jitter_external'))
            legs.append(dict(common, trip_seq=2, purpose=purpose,
                             dest_activity_type='home',
                             origin_sa1=CSA[k], dest_sa1=row.SA1_CODE21,
                             origin_x=round(dx, 1), origin_y=round(dy, 1),
                             dest_x=round(hx, 1), dest_y=round(hy, 1),
                             dep_time_s=back, arr_time_s=back + tt,
                             straight_dist_km=round(dist_km, 3),
                             activity_duration_s=0, is_tour_anchor=0,
                             dest_placement='home'))
    return legs, n_agents


COLUMNS = ['person_id', 'day_type', 'tour_id', 'trip_seq', 'purpose',
           'tour_purpose', 'dest_activity_type', 'origin_sa1', 'dest_sa1',
           'origin_x', 'origin_y', 'dest_x', 'dest_y', 'dep_time_s',
           'arr_time_s', 'straight_dist_km', 'activity_duration_s',
           'is_tour_anchor', 'party_size', 'time_flexibility_band',
           'dest_placement', 'agent_tier']

# The HTS per-person-per-day trip rate for the study-area LGAs, carried from
# DECISIONS 9 where it was derived from the same tables.
HTS_RATE_PER_PERSON_DAY = 3.473


def main(seed=SEED, max_persons=None, day_types=None):
    day_types = day_types or DAY_TYPES
    os.makedirs(OUT, exist_ok=True)
    rng = np.random.default_rng(seed)
    u = Uniforms(rng)

    zones = load_zones()
    core = zones[zones.zone_tier == 'core'].reset_index(drop=True)
    zi = {c: i for i, c in enumerate(core['SA1_CODE21'])}
    X = core['x_mga56'].to_numpy(dtype=float)
    Y = core['y_mga56'].to_numpy(dtype=float)
    RAD = np.sqrt(np.maximum(core['area_km2'].to_numpy(dtype=float), 1e-4)
                  * 1e6 / math.pi) * 0.6
    SA1 = core['SA1_CODE21'].to_numpy()
    ATTR = {p: norm(core['attr_' + p].to_numpy()) for p in PURPOSES}
    zone_arr = (X, Y, X, Y, RAD, SA1)

    yr, _total, share, meandist = hts_rates()
    print('HTS %s | purpose share %s'
          % (yr, {k: round(v, 3) for k, v in share.items()}), flush=True)

    print('joining POIs and CBD buildings to zones ...', flush=True)
    store, n_attractors = load_poi_by_zone(core)
    covered = {p: len(store[p]) for p in PURPOSES}
    print('   %d attractors; core zones with an attractor, by purpose: %s'
          % (n_attractors, covered), flush=True)

    print('calibrating gravity decay against HTS journey distances ...', flush=True)
    CUM, decay = calibrate_decay(X, Y, ATTR, meandist,
                                 core['population'].to_numpy(dtype=float))
    for p in PURPOSES:
        d = decay[p]
        print('   %-4s beta=%.4f  realised %5.2f km vs HTS %5.2f km'
              % (p, d['beta'], d['realised_network_km'], d['hts_network_km']),
              flush=True)

    hh = pd.read_csv(os.path.join(POP, 'B1_households.csv'),
                     usecols=['household_id', 'home_x_mga56', 'home_y_mga56'])
    home = dict(zip(hh.household_id.to_numpy(),
                    zip(hh.home_x_mga56.to_numpy(), hh.home_y_mga56.to_numpy())))
    del hh
    persons = pd.read_csv(os.path.join(POP, 'B1_synthetic_population.csv'),
                          dtype={'home_sa1': str},
                          usecols=['person_id', 'household_id', 'home_sa1', 'age',
                                   'employment_status', 'student_status',
                                   'car_available'])
    persons = persons.sort_values('person_id', kind='stable')
    if max_persons and max_persons < len(persons):
        # B1 writes persons zone by zone, so head() would draw the whole sample
        # from a handful of neighbouring SA1s and make every spatial statistic
        # meaningless. Take an evenly spaced slice instead - still deterministic,
        # but spread over the study area.
        step = len(persons) // max_persons
        persons = persons.iloc[::step].head(max_persons)
    n_persons = len(persons)
    print('%d persons x %d day types' % (n_persons, len(day_types)), flush=True)

    pid = persons.person_id.to_numpy()
    hid = persons.household_id.to_numpy()
    hsa = persons.home_sa1.to_numpy()
    age = persons.age.to_numpy()
    emp = np.char.startswith(persons.employment_status.astype(str)
                             .to_numpy().astype('U24'), 'employed')
    stu = (persons.student_status.astype(str).to_numpy() == 'full_time')
    cav = (persons.car_available.to_numpy() == 1)
    del persons

    employed_frac = float(emp.mean())
    # a person only makes an education tour if they are not already making a
    # work tour, so the student fraction used for the rate solve is the
    # non-employed full-time students
    student_frac = float((stu & ~emp).mean())
    child_frac = float((age < 12).mean())
    day_rate = solve_day_rates(HTS_RATE_PER_PERSON_DAY)
    stats = dict(seed=seed, hts_year=yr,
                 hts_rate_per_person_day=HTS_RATE_PER_PERSON_DAY,
                 day_rate={k: round(v, 4) for k, v in day_rate.items()},
                 day_rate_shape=DAY_RATE_SHAPE, day_rate_sweep=DAY_RATE_SWEEP,
                 day_purpose_mix=DAY_PURPOSE_MIX, decay=decay,
                 detour_factor=DETOUR_FACTOR, detour_sweep=DETOUR_SWEEP,
                 attractors=n_attractors,
                 zones_with_attractor={p: len(store[p]) for p in PURPOSES},
                 persons=n_persons, by_day={},
                 placement=collections.Counter(),
                 tours_dropped_over_horizon=0)

    for d in day_types:
        path = os.path.join(OUT, 'B2_activity_trips_%s.csv' % d)
        fh = open(path, 'w', newline='', encoding='utf-8')
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction='ignore',
                           lineterminator='\n')
        w.writeheader()

        rates, rate_diag = solve_secondary_rates(
            d, share, day_rate[d], employed_frac, student_frac, child_frac)
        stats.setdefault('rate_solution', {})[d] = rate_diag
        counts = {p: rng.poisson(rates[p], size=n_persons)
                  for p in ('HS', 'HO', 'WB')}

        n_legs = n_tours = n_travel = 0
        dropped = [0]
        by_purpose = collections.Counter()
        anchors = collections.Counter()
        for i in range(n_persons):
            hxy = home.get(hid[i])
            if hxy is None:
                continue
            hz = zi.get(hsa[i])
            if hz is None:
                continue
            person = dict(hx=float(hxy[0]), hy=float(hxy[1]), hzi=hz,
                          age=int(age[i]), employed=bool(emp[i]),
                          student=bool(stu[i]), cav=bool(cav[i]))
            pre = {p: int(counts[p][i]) for p in ('HS', 'HO', 'WB')}
            legs = build_day(person, d, rates, CUM, store, zone_arr, u, pre,
                             dropped)
            if not legs:
                continue
            n_travel += 1
            for seq, leg in enumerate(legs, start=1):
                leg['person_id'] = pid[i]
                leg['day_type'] = d
                leg['trip_seq'] = seq
                leg['party_size'] = 1
                leg['agent_tier'] = 'core'
                leg['time_flexibility_band'] = (
                    'fixed' if leg['tour_purpose'] in ('HW', 'HE') else 'flexible')
                leg['origin_x'] = round(leg['origin_x'], 1)
                leg['origin_y'] = round(leg['origin_y'], 1)
                leg['dest_x'] = round(leg['dest_x'], 1)
                leg['dest_y'] = round(leg['dest_y'], 1)
                leg['straight_dist_km'] = round(leg['straight_dist_km'], 3)
                by_purpose[leg['purpose']] += 1
                stats['placement'][leg['dest_placement']] += 1
                w.writerow(leg)
            anchors[legs[-1]['tour_id']] += 1
            n_legs += len(legs)
            n_tours += legs[-1]['tour_id']
        ext_legs, n_ext = external_agents(zones, core, decay, u, d,
                                          EXTERNAL_PERSON_ID_BASE)
        for leg in ext_legs:
            w.writerow(leg)
        fh.close()
        stats['by_day'][d] = dict(
            external_agents=n_ext, external_legs=len(ext_legs),
            legs=n_legs, tours=n_tours, travelling_persons=n_travel,
            legs_per_person=round(n_legs / max(n_persons, 1), 3),
            tours_per_traveller=round(n_tours / max(n_travel, 1), 3),
            tours_dropped_over_horizon=dropped[0],
            by_purpose=dict(by_purpose))
        print('%-8s %9d legs %8d tours %6.3f legs/person  dropped=%d'
              % (d, n_legs, n_tours, n_legs / max(n_persons, 1), dropped[0]),
              flush=True)

    stats['placement'] = dict(stats['placement'])
    wk = sum(DAYS_PER_WEEK[d] for d in day_types)
    week_rate = sum(DAYS_PER_WEEK[d] * stats['by_day'][d]['legs_per_person']
                    for d in day_types) / wk
    stats['realised_week_trip_rate'] = round(week_rate, 3)
    json.dump(stats, open(os.path.join(OUT, '_activity_chains_report.json'), 'w'),
              indent=2)
    print('week average %.3f trips/person/day against the HTS %.3f'
          % (week_rate, HTS_RATE_PER_PERSON_DAY), flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', type=int, default=SEED)
    ap.add_argument('--max-persons', type=int, default=None)
    ap.add_argument('--day-types', default=','.join(DAY_TYPES))
    a = ap.parse_args()
    main(a.seed, a.max_persons, [d for d in a.day_types.split(',') if d])
