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

# City-relative paths resolve through src/city.py: `data/...` names a
# location inside cities/<city>/, not inside the repository root.
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                  '..', '..', 'src'))
import city as _city  # noqa: E402
import os
import csv
import json
import math
import argparse
import collections

import numpy as np
import pandas as pd

# Model inputs come from cities/<city>/registry/, not from literals here. Every
# value below carries its units, provenance and either a sweep, a held-fixed rule
# or a derived-from identity there. See DECISIONS.md 15.
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import registry as _registry  # noqa: E402
CFG = _registry.load()

ZON = _city.path('data/processed/zones')
LU = _city.path('data/processed/landuse')
HTS = _city.path('data/processed/hts')
POP = _city.path('demand/population')
OUT = _city.path('demand/plans')

SEED = CFG.get('B.seed.master')
# Purposes that choose a destination: each one has an HTS journey distance to
# calibrate its gravity decay against, and an attractor set to draw from.
#
# HX is `serve passenger`: a tour made in order to carry someone else, which the
# HTS puts at 15.7% of Newcastle journeys, level with commuting. It used to be
# mapped onto NHB and then folded into the discretionary tours, which preserved
# the trip *rate* but not the trip *type* - see DECISIONS.md 9.15.
#
# NHB is NOT here, and no longer is. It is a *leg* label, not a tour purpose: a
# non-home-based leg arises only as an intermediate stop, whose destination is
# drawn with the HS or HO decay. Serve passenger was the only HTS purpose ever
# mapped to it, so with that moved to HX nothing observed maps to NHB at all,
# and it has no journey distance to calibrate against. Carrying it here built an
# attractor index and solved a decay that nothing then drew from.
PURPOSES = ['HW', 'HE', 'HS', 'HO', 'WB', 'HX']
DAY_TYPES = CFG.get('E.matrix.day_types')
DAYS_PER_WEEK = CFG.get('B.activity.days_per_week')

# MATSim activity type per trip purpose. `home` is emitted for the leg that
# closes a tour; the purpose column still carries the tour purpose.
ACT_TYPE = {'HW': 'work', 'HE': 'education', 'HS': 'shopping',
            'HO': 'other', 'WB': 'business', 'NHB': 'other'}

# ---------------------------------------------------------------------------
# Assumed parameters. Every one of these is recorded in DECISIONS.md with a
# sweep range; none is observed.
# ---------------------------------------------------------------------------

# Day-type shape. The HTS LGA tables have no day-of-week dimension (checked in
# the raw workbook: FINANCIAL_YEAR / LGA / MODE / PURPOSE only), but the RMS
# traffic counts do - they publish a WEEKDAYS and a WEEKENDS figure per
# station-year. `measure_network_factors.py` reads the weekend/weekday ratio off
# them (0.752 over 551 station-years) and it is loaded here, so the weekday
# against weekend split is **observed Newcastle data**, not an assumption.
#
# What the counts cannot settle is how the weekend divides between Saturday and
# Sunday: they report one WEEKENDS figure. That ratio alone stays assumed, and
# is swept. The absolute level is not free either - the shape is rescaled so
# 5xWEEKDAY + SAT + SUN reproduces the HTS week average exactly.
SAT_TO_SUN_RATE = CFG.get('B.activity.sat_to_sun_rate')
SAT_TO_SUN_SWEEP = (1.00, 1.45)

# How the purpose mix shifts by day type, as a multiplier on the weekday rate
# for that purpose. Commute and education collapse at the weekend; shopping and
# social rise. Assumed.
# Swept because the weekend collapse of commute and education is assumed: the
# multiplier on each weekend purpose may move by this factor either way.
DAY_PURPOSE_MIX_SWEEP = CFG.sweep('B.activity.day_purpose_mix')['proportional']
DAY_PURPOSE_MIX = CFG.get('B.activity.day_purpose_mix')

# Probability that a person with the relevant status makes their mandatory tour
# on a given day type. Assumed, but the weekday work figure is now bounded from
# below by observation: census G62 records that 65.1% of employed residents
# travelled to work on census night. That night was August 2021 with 19.2%
# working from home, so it carries the lockdown with it and cannot set the
# value (DECISIONS.md 2.4 rules G62 out as a behavioural rate) - it bounds the
# sweep instead. The upper bound allows for leave and illness.
P_MANDATORY_WORK_SWEEP = (None, 0.90)     # lower bound filled from C2 at load
P_MANDATORY_EDUCATION_SWEEP = (0.70, 0.95)
P_MANDATORY = CFG.get('B.activity.p_mandatory')

# Probability a tour includes an intermediate stop, by tour purpose. This is
# what creates genuine sub-tours, and therefore what lets MATSim's mode choice
# vary within a day rather than for the whole day at once. Assumed.
P_INTERMEDIATE_STOP = CFG.get('B.activity.p_intermediate_stop')
P_SECOND_STOP = CFG.get('B.activity.p_second_stop')
P_SECOND_STOP_SWEEP = (0.12, 0.40)

# An escort tour is made by the person doing the driving, so a non-licence
# holder cannot make one. Derived from the same identity as the `ride` driver
# requirement, taken on the driver side (DECISIONS.md 9.15).
ESCORT_REQUIRES_LICENCE = CFG.get('B.activity.escort_requires_licence')
# Whether an HX tour is BOUND to an actual household member's already-drawn
# trip - destination and departure taken from the person being escorted -
# instead of drawing both from the education-attractor distribution and the
# HE profile. Binding re-targets existing tours and never adds one; false
# restores the pre-9.46 behaviour (DECISIONS.md 9.46).
ESCORT_BINDING = CFG.get('B.activity.escort_binding_enabled')
# Which household trips an escort may bind to. Assumed and swept - there is no
# observation of who-drives-whom. 'unlicensed_or_education' stops at priority
# class 2 (see bind_escort_tours); 'any_member_trip' allows all four.
ESCORT_SCOPE = CFG.get('B.activity.escort_binding_scope')
# Two bindings for the same escorter must sit at least this far apart, so the
# driver can physically make both runs. Assumed and swept.
ESCORT_MIN_GAP_S = CFG.get('B.activity.escort_binding_min_gap_s')
# Share of an under-12's drawn secondary tours that are actually made alone.
# Applied as per-tour thinning, not as a scaling of the count.
CHILD_TOUR_RETENTION = CFG.get('B.activity.child_tour_retention')
CHILD_TOUR_RETENTION_SWEEP = (0.25, 0.60)
P_INTERMEDIATE_SWEEP = (0.10, 0.35)

# Straight-line to network distance, used to compare the gravity model against
# the HTS journey distances, which are network distances. **Measured**, not
# assumed: `measure_network_factors.py` routes population-weighted zone pairs
# over the observed A1 road graph and takes the aggregate ratio. Loaded from
# params/C2_network_factors.json; the fallback below is only used if that file
# is missing, and the build says so when it falls back.
# The fallback is the DECLARED field, not a literal beside it. Both carried the
# same quantity and only one of them was compared with anything: the field held
# the measured 1.3376 while this held 1.30, pinned by `legacy_symbol` so
# check_legacy_drift.py could see the divergence - but a divergence recorded is
# still two copies. There is one now, and the sweep comes from the field's own
# `sweep` key rather than from a tuple typed beside it.
DETOUR_FACTOR = CFG.get('B.activity.detour_factor')
DETOUR_SWEEP = tuple(CFG.sweep('B.activity.detour_factor'))
DETOUR_SOURCE = '%s - C2 factors file not found, using the declared value'     % CFG.source('B.activity.detour_factor')
NETWORK_FACTORS = _city.path('params/C2_network_factors.json')

# Mean activity duration in minutes by purpose (carried from P1, DECISIONS 9).
ACT_DURATION = CFG.get('B.activity.act_duration_min')
# Proportional, applied to every mean duration. Taken from the field's own
# `sweep` key: a sweep range typed beside the value it bounds cannot be
# resolved, overlaid or varied by a run overlay.
ACT_DURATION_SWEEP = CFG.sweep('B.activity.act_duration_min')['proportional']
DURATION_CV = CFG.get('B.activity.duration_cv')

# The day closes. Chains are compressed rather than allowed to run past this.
DAY_HORIZON_S = CFG.get('B.activity.day_horizon_s')

# Departure-time profiles by purpose, probability by hour 0..23 (carried from
# P1, DECISIONS 9; assumed, NSW-typical shapes). Weekend tours start later; the
# shift is applied as a whole-profile roll, and is assumed.
DEPART = dict(CFG.get('B.activity.departure_profile'))
DEPART['HX'] = DEPART['HE']
WEEKEND_DEPARTURE_SHIFT_H = CFG.get('B.activity.weekend_departure_shift_h')

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
    # An escort destination is wherever the escorted person was going. The
    # dominant and by far the most sharply peaked component is the school run,
    # so HX draws the same attractors as HE. Escorting to other destinations is
    # folded into it and inherits its timing; the trip *length* is not inherited
    # but calibrated to the HTS serve-passenger journey distance like every
    # other purpose. Stated as a modelling choice in DECISIONS.md 9.15.
    'HX': ('civic',),
}
EDUCATION_CATEGORIES = ('civic:school', 'civic:university', 'civic:college',
                        'civic:kindergarten', 'civic:childcare')
# Purposes whose destinations are drawn from the education attractor set, and
# whose zone-level attraction vector is shared rather than separately built.
EDUCATION_ATTRACTOR_PURPOSES = ('HE', 'HX')
ATTRACTION_ALIAS = {'HX': 'HE'}


def norm(a):
    a = np.asarray(a, dtype=float)
    a = np.where(np.isfinite(a) & (a > 0), a, 0.0)
    s = a.sum()
    return a / s if s > 0 else np.full(len(a), 1.0 / len(a))


def hts_rates():
    """Trip rate and mean journey distance per purpose, from the HTS extract.

    Returns the journey distance twice: aggregated over the five LGAs
    (journey-weighted, used for the external tier and as the fallback), and per
    home LGA. The per-LGA table exists because one decay per purpose reproduced
    the five-LGA mean exactly while missing every LGA's own mean - Newcastle
    education realised 6.57 km against its observed 3.0 while the aggregate
    target of 6.44 was hit to two decimals (issue #30, DECISIONS.md 9.40).
    """
    pur = pd.read_csv(os.path.join(HTS, 'hts_purpose.csv'))
    pur = pur[(pur.geography == 'lga')]
    yr = sorted(pur.FINANCIAL_YEAR.unique())[-1]
    pur = pur[pur.FINANCIAL_YEAR == yr]
    # `Serve passenger` was mapped to NHB, and solve_secondary_rates then folded
    # NHB's weight into HO because a non-home-based leg is not a tour purpose.
    # That preserved the trip rate and lost the trip type: an escort became a
    # two-hour discretionary stay made by anyone, rather than a drop-off made by
    # a driver. It is its own tour purpose now (DECISIONS.md 9.15).
    pmap = {'Commute': 'HW', 'Education/childcare': 'HE', 'Shopping': 'HS',
            'Personal business': 'HO', 'Social/recreation': 'HO',
            'Serve passenger': 'HX', 'Work related business': 'WB', 'Other': 'HO'}
    pur['p'] = pur.TRAVEL_PURPOSE.str.rstrip('*').map(pmap)
    pur = pur[pur.p.notna()]
    journeys = pur.groupby('p').JOURNEYS_BY_MODE.sum()
    dist = (pur.groupby('p')
            .apply(lambda d: np.average(d.JOURNEY_AVG_DISTANCE,
                                        weights=d.JOURNEYS_BY_MODE.clip(lower=1)),
                   include_groups=False))
    dist_lga = (pur.groupby(['area_name', 'p'])
                .apply(lambda d: np.average(d.JOURNEY_AVG_DISTANCE,
                                            weights=d.JOURNEYS_BY_MODE.clip(lower=1)),
                       include_groups=False))
    demo = pd.read_csv(os.path.join(HTS, 'hts_mode.csv'))
    demo = demo[(demo.geography == 'lga') & (demo.FINANCIAL_YEAR == yr)]
    total_trips = demo.TRIPS_BY_MODE.sum()
    share = journeys / journeys.sum()
    return (yr, total_trips, share.to_dict(), dist.to_dict(),
            {(lga, p): float(v) for (lga, p), v in dist_lga.items()})


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
    pts = gpd.GeoDataFrame(j, geometry=j.geometry, crs=zg.crs).to_crs(_city.crs())
    j = j.assign(x=pts.geometry.x.to_numpy(), y=pts.geometry.y.to_numpy())

    bld = pd.read_csv(os.path.join(LU, 'D1_buildings_cbd.csv'))
    gb = gpd.GeoDataFrame(bld, geometry=gpd.points_from_xy(bld.lon, bld.lat),
                          crs='EPSG:4326').to_crs(zg.crs)
    jb = gpd.sjoin(gb, zg, how='left', predicate='within')
    jb = jb[jb.SA1_CODE21.notna()]
    bpts = gpd.GeoDataFrame(jb, geometry=jb.geometry, crs=zg.crs).to_crs(_city.crs())
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
        if purpose in EDUCATION_ATTRACTOR_PURPOSES:
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


def calibrate_decay(X, Y, ATTR, meandist, prod, zone_lga=None, meandist_lga=None):
    """Solve the gravity decay so realised mean distance matches the HTS.

    P1 set beta = 1/mean-distance directly, which left education and shopping
    60% long and work-related business 22% short. Bisecting on the realised
    expectation instead ties each purpose to its own HTS journey distance.

    One beta per purpose then reproduced the five-LGA aggregate exactly while
    missing every LGA's own mean - the aggregate hides the heterogeneity the
    HTS itself publishes (education is 3.0 km for a Newcastle resident and
    12.9 km for a Port Stephens one; the old build realised 6.57 km for both
    while hitting its 6.44 aggregate target to two decimals). The decay is now
    solved per (purpose x home LGA) against that LGA's own HTS row, with the
    aggregate solve kept as the fallback for suppressed cells and as the decay
    the external tier uses, since a boundary agent has no home LGA (issue #30,
    DECISIONS.md 9.40).
    """
    DX = X[None, :] - X[:, None]
    DY = Y[None, :] - Y[:, None]
    DKM = np.hypot(DX, DY) / 1000.0
    del DX, DY
    out, diag = {}, {}
    pw = norm(prod)

    def solve(p, target, rows=None):
        """Bisect beta so the realised mean over `rows` origins hits target."""
        w_origin = pw if rows is None else norm(np.where(rows, pw, 0.0))

        def realised(beta):
            w = ATTR[p][None, :] * np.exp(-beta * DKM)
            s = w.sum(axis=1, keepdims=True)
            w = np.divide(w, np.where(s > 0, s, 1.0))
            return float((w_origin * (w * DKM).sum(axis=1)).sum())

        lo, hi = 0.005, 4.0
        r_lo, r_hi = realised(lo), realised(hi)
        if target >= r_lo:
            # even the weakest decay realises shorter trips than observed
            beta = lo
        elif target <= r_hi:
            # unreachable: even the strongest decay overshoots, because the
            # attractor surface is too sparse near these origins - the closest
            # achievable beta is hi, and the diag shows the gap honestly (the
            # Port Stephens shopping cell is the measured case: its attractors
            # sit inside the clipped #32 harvest)
            beta = hi
        else:
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                if realised(mid) > target:
                    lo = mid
                else:
                    hi = mid
            beta = 0.5 * (lo + hi)
        return beta, realised(beta)

    lgas = sorted(set(zone_lga)) if zone_lga is not None else []
    beta_of_zone = {}
    for p in PURPOSES:
        target = max(meandist.get(p, 8.0), 0.8) / DETOUR_FACTOR
        beta, got = solve(p, target)
        out[p] = beta
        diag[p] = dict(beta=round(beta, 5),
                       target_straight_km=round(target, 2),
                       realised_straight_km=round(got, 2),
                       hts_network_km=round(meandist.get(p, float('nan')), 2),
                       realised_network_km=round(got * DETOUR_FACTOR, 2))
        by_lga = {}
        zone_beta = np.full(X.size, beta)
        for lga in lgas:
            obs = (meandist_lga or {}).get((lga, p))
            rows = np.asarray(zone_lga) == lga
            if obs is None or not rows.any():
                by_lga[lga] = dict(beta=round(beta, 5), fallback='aggregate',
                                   hts_network_km=None)
                continue
            t_lga = max(obs, 0.8) / DETOUR_FACTOR
            b_lga, got_lga = solve(p, t_lga, rows)
            zone_beta[rows] = b_lga
            by_lga[lga] = dict(beta=round(b_lga, 5),
                               target_straight_km=round(t_lga, 2),
                               realised_straight_km=round(got_lga, 2),
                               hts_network_km=round(obs, 2),
                               realised_network_km=round(got_lga * DETOUR_FACTOR, 2))
        if lgas:
            diag[p]['by_lga'] = by_lga
        beta_of_zone[p] = zone_beta
    CUM = {}
    for p in PURPOSES:
        w = ATTR[p][None, :] * np.exp(-beta_of_zone[p][:, None] * DKM)
        s = w.sum(axis=1, keepdims=True)
        w = np.divide(w, np.where(s > 0, s, 1.0))
        CUM[p] = np.cumsum(w, axis=1).astype(np.float32)
    del DKM
    return CUM, diag


def load_network_factors():
    """Pull in the factors measured from Newcastle data, if they exist.

    Sets the module-level detour factor, the day-type shape and the observed
    lower bound on the work-attendance sweep. Falls back loudly rather than
    silently: a build that could not find the measurements says so, and the
    report records which values were measured and which were assumed.
    """
    global DETOUR_FACTOR, DETOUR_SWEEP, DETOUR_SOURCE
    global P_MANDATORY_WORK_SWEEP
    shape = {'WEEKDAY': 1.0, 'SAT': 0.95, 'SUN': 0.80}
    shape_source = 'assumed - C2 factors file not found'
    if os.path.exists(NETWORK_FACTORS):
        c2 = json.load(open(NETWORK_FACTORS, encoding='utf-8'))
        d = c2['detour_factor']
        DETOUR_FACTOR = float(d['value'])
        DETOUR_SWEEP = tuple(d['sweep'])
        DETOUR_SOURCE = d['source']
        # weekend/weekday is observed; the split inside the weekend is not
        ratio = float(c2['day_type']['weekend_to_weekday'])
        sun = 2.0 * ratio / (SAT_TO_SUN_RATE + 1.0)
        shape = {'WEEKDAY': 1.0, 'SAT': sun * SAT_TO_SUN_RATE, 'SUN': sun}
        shape_source = ('measured weekend/weekday from RMS traffic counts '
                        '(%.4f over %d station-years); the Saturday:Sunday '
                        'split within the weekend is assumed %.4f, swept %s'
                        % (ratio, c2['day_type']['station_years'],
                           SAT_TO_SUN_RATE, list(SAT_TO_SUN_SWEEP)))
        att = float(c2['work_attendance']['census_day_attendance'])
        P_MANDATORY_WORK_SWEEP = (att, P_MANDATORY_WORK_SWEEP[1])
    return shape, shape_source


def solve_day_rates(total_rate, shape):
    """Scale the day-type shape so the week average matches the HTS."""
    wk = sum(DAYS_PER_WEEK.values())
    avg = sum(DAYS_PER_WEEK[d] * shape[d] for d in DAY_TYPES) / wk
    k = total_rate / avg
    return {d: shape[d] * k for d in DAY_TYPES}


def legs_per_tour(purpose):
    """Expected legs in one tour: out, back, and any intermediate stop."""
    return 2.0 + P_INTERMEDIATE_STOP.get(purpose, 0.15) * (1.0 + P_SECOND_STOP)


def solve_secondary_rates(day, share, day_rate, employed_frac, student_frac,
                          child_frac, licence_frac):
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
    sec = ('HS', 'HO', 'WB', 'HX')
    denom = sum(w[p] * legs_per_tour(p) for p in sec)
    # under-12 secondary tours are thinned after the Poisson draw, so the solve
    # has to expect fewer legs per unit of lambda than the raw tour rate implies
    thin = 1.0 - child_frac * (1.0 - CHILD_TOUR_RETENTION)
    k = secondary_target / (denom * thin) if denom > 0 and thin > 0 else 0.0
    # No fold any more. NHB used to carry the serve-passenger share and have it
    # added to HO, because NHB is not a tour purpose. HX *is* one, and draws its
    # own tours against the same observed share (DECISIONS.md 9.15).
    lam = {p: k * w[p] for p in sec}
    # Only licence holders draw an escort tour, so the per-person rate has to be
    # raised by that fraction for the *realised* escort legs to reach the
    # observed serve-passenger share. Without this the tier lands short by the
    # non-driving fraction of the population, children included.
    if ESCORT_REQUIRES_LICENCE and licence_frac > 0:
        lam['HX'] /= licence_frac
    return lam, dict(day_rate_target=round(day_rate, 4),
                     licence_frac=round(licence_frac, 4),
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
                  'HO': 'other', 'WB': 'business', 'HX': 'escort'}
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


def draw_tour_spec(purpose, hz, CUM, store, zone_arr, u, fixed_dest=None):
    """The stochastic content of one tour - destination chain, in-zone
    placements and activity durations - drawn exactly once, so that moving the
    tour's start in the timeline (to flow around an immovable escort tour)
    never redraws it.

    `fixed_dest` is the escort binding (DECISIONS.md 9.46): the primary
    destination is the escorted household member's own drawn destination, not a
    draw from the attractor distribution. Intermediate stops still chain off it
    at the ordinary rate - a driver who drops a passenger may link another stop
    before returning.
    """
    X, Y, ZX, ZY, RAD, SA1 = zone_arr
    if fixed_dest is None:
        primary_k = int(np.searchsorted(CUM[purpose][hz], u()))
        if primary_k >= X.size:
            primary_k = X.size - 1
        dx, dy, how = place_in_zone(store, purpose, primary_k,
                                    float(ZX[primary_k]), float(ZY[primary_k]),
                                    float(RAD[primary_k]), u)
    else:
        primary_k, dx, dy = fixed_dest
        how = 'escorted'
    chain = [(purpose, primary_k, dx, dy, how)]
    if u() < P_INTERMEDIATE_STOP.get(purpose, 0.15):
        stop_purpose = 'HS' if u() < 0.5 else 'HO'
        k = min(int(np.searchsorted(CUM[stop_purpose][primary_k], u())),
                X.size - 1)
        sx, sy, show = place_in_zone(store, stop_purpose, k, float(ZX[k]),
                                     float(ZY[k]), float(RAD[k]), u)
        chain.append((stop_purpose, k, sx, sy, show))
        if u() < P_SECOND_STOP:
            k2 = min(int(np.searchsorted(CUM['HO'][k], u())), X.size - 1)
            s2x, s2y, s2how = place_in_zone(store, 'HO', k2, float(ZX[k2]),
                                            float(ZY[k2]), float(RAD[k2]), u)
            chain.append(('HO', k2, s2x, s2y, s2how))
    durs = []
    for idx, entry in enumerate(chain):
        hint = entry[0]
        if idx == 0:
            base = ACT_DURATION[hint]
        else:
            base = ACT_DURATION['NHB'] if hint == 'HO' else ACT_DURATION[hint]
        durs.append(int(max(300, base * 60
                            * (1.0 + DURATION_CV * (2.0 * u() - 1.0)))))
    return dict(purpose=purpose, chain=chain, durs=durs)


def time_tour(spec, t_start, person, hx, hy, hz, SA1):
    """Pure time arithmetic: the legs of one tour at the given start.

    No draw happens here, so the same spec can be re-timed when the timeline
    pushes it, without perturbing the random stream.
    """
    spd = 26.0 if person['cav'] else 16.0
    cur_x, cur_y, cur_z, cur_act = hx, hy, hz, 'home'
    t = t_start
    pending = []
    for idx, (hint, k, dx, dy, how) in enumerate(spec['chain']):
        act = ACT_OF_PURPOSE[hint]
        dist_km = math.hypot(dx - cur_x, dy - cur_y) / 1000.0
        tt = int(dist_km / spd * 3600) + 240
        arr = t + tt
        dur = spec['durs'][idx]
        pending.append(dict(
            purpose=leg_purpose(cur_act, act), dest_activity_type=act,
            origin_sa1=SA1[cur_z], dest_sa1=SA1[k],
            origin_x=cur_x, origin_y=cur_y, dest_x=dx, dest_y=dy,
            dep_time_s=t, arr_time_s=arr, straight_dist_km=dist_km,
            activity_duration_s=dur, is_tour_anchor=int(idx == 0),
            dest_placement=how))
        cur_x, cur_y, cur_z, cur_act = dx, dy, k, act
        t = arr + dur
    dist_km = math.hypot(hx - cur_x, hy - cur_y) / 1000.0
    tt = int(dist_km / spd * 3600) + 240
    arr_home = t + tt
    pending.append(dict(
        purpose=leg_purpose(cur_act, 'home'), dest_activity_type='home',
        origin_sa1=SA1[cur_z], dest_sa1=SA1[hz],
        origin_x=cur_x, origin_y=cur_y, dest_x=hx, dest_y=hy,
        dep_time_s=t, arr_time_s=arr_home, straight_dist_km=dist_km,
        activity_duration_s=0, is_tour_anchor=0, dest_placement='home'))
    return pending, arr_home


def build_day(person, day, rates, CUM, store, zone_arr, u, pre, dropped,
              fixed_tours=()):
    """One person's tours for one day type.

    Returns (legs, anchors). Every tour starts and ends at the person's home,
    so the day decomposes into proper sub-tours for MATSim, and a tour that
    will not fit inside the day horizon is dropped rather than allowed to run
    past midnight.

    `fixed_tours` are escort (HX) tours BOUND to another household member's
    already-drawn trip (DECISIONS.md 9.46): their start and destination are the
    escorted trip's own and are IMMOVABLE - moving them would unmake the
    co-location the binding exists to create. The person's movable tours flow
    around them: one that would overlap an immovable tour is pushed past its
    end, which is the school run's own logic - drop the child, then go to work.

    `anchors` describes each placed tour's primary destination and departure,
    so a later household member's escort tour can bind to it.
    """
    X, Y, ZX, ZY, RAD, SA1 = zone_arr
    hx, hy, hz = person['hx'], person['hy'], person['hzi']

    # ---- which movable tours does this person make today ----
    tours = []
    if person['employed'] and u() < P_MANDATORY[day]['work']:
        tours.append('HW')
    elif person['student'] and u() < P_MANDATORY[day]['education']:
        tours.append('HE')
    for p in ('HS', 'HO', 'WB', 'HX'):
        if p == 'WB' and not person['employed']:
            continue
        # An escort tour is made *by the driver*: someone without a licence
        # cannot make one. B.activity.escort_requires_licence.
        if p == 'HX' and ESCORT_REQUIRES_LICENCE and not person['licence']:
            continue
        n = pre[p]
        if person['age'] < 12 and n:
            # Children make fewer independent secondary tours. Thin each drawn
            # tour with probability CHILD_TOUR_RETENTION rather than scaling the
            # count - int(n * 0.4) rounds a single tour to zero, which suppressed
            # every under-12 secondary tour instead of 60% of them.
            n = sum(1 for _ in range(n) if u() < CHILD_TOUR_RETENTION)
        tours += [p] * n
    if not tours and not fixed_tours:
        return [], []

    # ---- immovable escort tours first: content drawn, time taken as bound ----
    placed = []   # (start_s, arr_home_s, spec, legs)
    for ft in sorted(fixed_tours, key=lambda f: f['start_s']):
        spec = draw_tour_spec('HX', hz, CUM, store, zone_arr, u,
                              fixed_dest=(ft['k'], ft['dx'], ft['dy']))
        if ft['start_s'] > DAY_HORIZON_S - 3600:
            dropped[0] += 1
            continue
        legs_f, arr_home = time_tour(spec, ft['start_s'], person, hx, hy, hz, SA1)
        if arr_home > DAY_HORIZON_S:
            dropped[0] += 1
            continue
        if any(ft['start_s'] < e and arr_home > s for s, e, _, _ in placed):
            # the binder keeps bound departures escort_binding_min_gap_s apart,
            # but a drawn intermediate stop can stretch one binding into the
            # next; a bound time may not move, so the collision drops, not shifts
            dropped[0] += 1
            continue
        placed.append((ft['start_s'], arr_home, spec, legs_f))
    fixed_intervals = [(s, e) for s, e, _, _ in placed]

    shift = WEEKEND_DEPARTURE_SHIFT_H[day]
    starts = [draw_hour(DEPART[p], shift, u) * 3600 + int(3600 * u())
              for p in tours]
    order = sorted(range(len(tours)), key=lambda i: (starts[i], tours[i], i))

    t_now = None
    for oi in order:
        purpose = tours[oi]
        t_start = starts[oi]
        if t_now is not None and t_start < t_now + 600:
            t_start = t_now + 600
        spec = draw_tour_spec(purpose, hz, CUM, store, zone_arr, u)
        # flow around the immovable escort tours: a movable tour that would
        # overlap one is pushed past its end and re-timed (never redrawn)
        legs_m = None
        while t_start <= DAY_HORIZON_S - 3600:
            legs_m, arr_home = time_tour(spec, t_start, person, hx, hy, hz, SA1)
            hit = next(((fs, fe) for fs, fe in fixed_intervals
                        if t_start < fe + 600 and arr_home > fs), None)
            if hit is None:
                break
            t_start = hit[1] + 600
            legs_m = None
        if legs_m is None:
            dropped[0] += len(order) - order.index(oi)
            break
        if arr_home > DAY_HORIZON_S:
            dropped[0] += 1
            continue
        placed.append((t_start, arr_home, spec, legs_m))
        t_now = arr_home if t_now is None else max(t_now, arr_home)

    # ---- assemble the day in chronological order ----
    placed.sort(key=lambda pl: pl[0])
    legs = []
    for tid, (s, e, spec, tour_legs) in enumerate(placed, start=1):
        for r in tour_legs:
            r['tour_id'] = tid
            r['tour_purpose'] = spec['purpose']
        legs += tour_legs

    # The 30-hour-day cap (issue #37, DECISIONS.md 9.38). The qsim horizon's
    # tail exists so a late-evening chain can arrive after midnight - hours
    # 24..horizon are 00:00 onward the FOLLOWING morning. That is only
    # coherent for a person who is not also travelling in those same
    # early-morning hours of the modelled day: a departure at 02:00 and
    # another at 26:00 is one person with two 2 a.m.s. CAP, not wrap: the
    # colliding late tour is dropped whole, because wrapping it onto the
    # early morning would create exactly the collision being removed.
    tail_s = DAY_HORIZON_S - 24 * 3600
    if legs and any(l['dep_time_s'] < tail_s for l in legs):
        bad = {l['tour_id'] for l in legs if l['dep_time_s'] >= 24 * 3600}
        if bad:
            dropped[1] += len(bad)
            legs = [l for l in legs if l['tour_id'] not in bad]

    kept = {l['tour_id'] for l in legs}
    anchors = []
    for tid, (s, e, spec, _tour_legs) in enumerate(placed, start=1):
        if tid not in kept:
            continue
        first = spec['chain'][0]
        anchors.append(dict(tour_id=tid, purpose=spec['purpose'], dep_s=s,
                            k=first[1], dx=first[2], dy=first[3],
                            escorted=(first[4] == 'escorted')))
    return legs, anchors


def bind_escort_tours(n_hx, candidates, claimed):
    """Choose which household trips up to `n_hx` escort tours are bound to.

    Deterministic - no draw. Priority reflects who actually needs conveying:
    an unlicensed member's education trip (the school run) first, then any
    unlicensed member's trip, then a licensed member's education trip, then
    any remaining trip. One escort per escorted trip household-wide
    (`claimed`), and two bindings for the same escorter must sit at least
    B.activity.escort_binding_min_gap_s apart so the driver can physically
    make both; finer overlap from a drawn intermediate stop resolves at
    placement, where the collision drops.
    An HX tour that finds no candidate stays UNBOUND and draws from the
    distribution exactly as before - lone-person households (26.2%) have
    nobody to bind to and must keep their observed escort rate.
    """
    def pri(c):
        if not c['licence'] and c['purpose'] == 'HE':
            return 0
        if not c['licence']:
            return 1
        if c['purpose'] == 'HE':
            return 2
        return 3

    max_pri = 2 if ESCORT_SCOPE == 'unlicensed_or_education' else 3
    fixed = []
    for c in sorted(candidates, key=lambda c: (pri(c), c['member'], c['tour_id'])):
        if len(fixed) >= n_hx:
            break
        if pri(c) > max_pri:
            break
        key = (c['member'], c['tour_id'])
        if key in claimed:
            continue
        if any(abs(c['dep_s'] - f['start_s']) < ESCORT_MIN_GAP_S for f in fixed):
            continue
        claimed.add(key)
        fixed.append(dict(start_s=c['dep_s'], k=c['k'], dx=c['dx'], dy=c['dy'],
                          priority=pri(c)))
    return fixed



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
EXTERNAL_INTERACTION_RATE = CFG.get('B.external.interaction_rate')
EXTERNAL_INTERACTION_SWEEP = (0.04, 0.15)
EXTERNAL_DAY_FACTOR = CFG.get('B.external.day_factor')
EXTERNAL_PURPOSE_SPLIT = CFG.get('B.external.purpose_split')
EXTERNAL_PERSON_ID_BASE = CFG.get('B.external.person_id_base')
CORDON_ROAD_CLASSES = frozenset(CFG.get('B.external.cordon_road_classes'))
ROADS = _city.path('data/processed/network/A1_road_edges.csv')

# Through traffic (issue #20, DECISIONS.md 9.41). The radial external tier
# above sends boundary residents INTO the core and home again; nothing in it
# ever crosses the study area, so the M1 at Wyee - observed 48,016 AADT,
# calibration target V113 - carried zero modelled vehicles. Through demand is
# seeded from the cordon's own observed volumes: a cordon crossing becomes a
# "gate" when a CALIBRATION count station sits within the declared radius of
# it, and gates exchange trips whose entry and exit are at least the declared
# separation apart. The through share of a gate's AADT is unobserved and is
# assumed and swept, never pinned.
THROUGH_SHARE = CFG.get('B.external.through_share')
THROUGH_CORRIDOR_KM = CFG.get('B.external.through_corridor_match_km')
THROUGH_OUTSIDE_MIN_M = CFG.get('B.external.through_outside_min_m')
THROUGH_MIN_SEP_KM = CFG.get('B.external.through_min_separation_km')
AADT_TARGETS = _city.path('data/processed/validation/road_aadt_targets.csv')
LGA_ZONES = _city.path('data/processed/zones/zones_LGA.gpkg')

# Freight (issue #24, DECISIONS.md 9.49). A heavy-vehicle BACKGROUND LOAD, not
# a freight demand model: the through tier's gate volumes split into car and
# truck by each gate station's own observed heavy share, and an internal tier
# adds truck trips over the observed freight-employment attractor, scaled by a
# declared, swept ratio. Departure times and the weekend drop are MEASURED
# from the classified hourly counts (extract_freight_profile.py); the volume
# and the distance decay are the assumptions, and both are declared and swept.
FREIGHT_TRIP_RATIO = CFG.get('B.freight.trip_ratio')
FREIGHT_BETA_PER_KM = CFG.get('B.freight.gravity_beta_per_km')
FREIGHT_DIVISIONS = list(CFG.get('B.freight.attractor_divisions'))
HEAVY_SHARE_FALLBACK = CFG.get('B.counts.heavy_vehicle_share')
FREIGHT_PROFILE = _city.path('data/processed/observed/freight_hourly_profile.csv')
FREIGHT_DAY_FACTORS = _city.path('data/processed/observed/freight_day_factors.csv')
EMPLOYMENT_ANZSIC = _city.path(
    'data/processed/landuse/D1_employment_by_anzsic_POW_SA2.csv')


def cordon_nodes(ext):
    """External stations: where boundary demand enters the modelled network.

    Every one of the 201 external SA1s lies OUTSIDE the five-LGA study area - a
    median of 21.3 km beyond the boundary and up to 128.7 km - while the road
    network is clipped to the study area. Placing a trip end at an external zone
    centroid therefore places it where no modelled road exists, and MATSim's
    `accessEgressModeToLink` then walks the agent to the edge of the network:
    a median 2.7 km against the core population's 0.097 km, and 16-50 km in the
    top three deciles. At 1.05 m/s that is most of a day, so 48% of external car
    tours never completed and the modes that are teleported door to door - bike
    and walk, which are charged no access leg at all - won on score. That is the
    whole of the 96 km bicycle result (DECISIONS.md 9.14, 9.15).

    The standard treatment is an external station: boundary demand enters at the
    point where its corridor crosses the cordon, on a real link, and the journey
    outside the study area is simply not modelled. The cordon set is derived, not
    listed: a node is an external station if it is the nearest node on a road
    capable of carrying boundary demand to at least one external zone, which by
    construction puts it on the outward-facing edge of the network. Testing
    distance to the study-area boundary instead would pick up the coastline,
    which is a boundary but not a crossing.

    Returns (node_x, node_y) for the cordon set, in EPSG:28356.
    """
    xs, ys = [], []
    seen = set()
    with open(ROADS, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if r['road_class'] not in CORDON_ROAD_CLASSES:
                continue
            for nd, la, lo in ((r['from_node'], r['start_lat'], r['start_lon']),
                               (r['to_node'], r['end_lat'], r['end_lon'])):
                if nd in seen:
                    continue
                seen.add(nd)
                xs.append(float(lo))
                ys.append(float(la))
    import pyproj
    tf = pyproj.Transformer.from_crs(4326, 28356, always_xy=True)
    nx, ny = tf.transform(np.asarray(xs), np.asarray(ys))
    nx = np.asarray(nx, dtype=float)
    ny = np.asarray(ny, dtype=float)
    ex = ext['x_mga56'].to_numpy(dtype=float)
    ey = ext['y_mga56'].to_numpy(dtype=float)
    keep = set()
    # chunked so the 201 x ~7,000 distance matrix never materialises whole
    for i0 in range(0, ex.size, 64):
        ex_c, ey_c = ex[i0:i0 + 64], ey[i0:i0 + 64]
        d = np.hypot(nx[None, :] - ex_c[:, None], ny[None, :] - ey_c[:, None])
        keep.update(int(j) for j in d.argmin(axis=1))
    idx = np.array(sorted(keep), dtype=int)
    return nx[idx], ny[idx]


def external_agents(zones, core, decay, u, day, seq_base, store, cordon):
    """One tour per boundary agent, entering the network at an external station.

    Destinations are drawn over the core zones only, with the same purpose decay
    the resident population uses, so a boundary trip is not systematically
    longer or shorter than a resident one of the same purpose, and they are
    placed on an observed attractor by the same routine the core uses rather
    than jittered inside the zone.

    The agent's origin is the cordon crossing that minimises
    d(external zone, cordon) + d(cordon, destination) - the entry that is on the
    way - so the modelled trip is the in-network portion of the journey and
    begins on a link. What lies beyond the cordon is outside the model.
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
        dkm = np.hypot(CX - ex, CY - ey) / 1000.0
        # distance from every cordon crossing to this zone, fixed for the zone
        d_zone_cordon = np.hypot(cordon[0] - ex, cordon[1] - ey)
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
            dx, dy, how = place_in_zone(store, purpose, k, float(CX[k]),
                                        float(CY[k]), float(CRAD[k]), u)
            # The external station this agent enters through: the crossing that
            # is on the way, not merely the nearest one to home.
            j = int((d_zone_cordon
                     + np.hypot(cordon[0] - dx, cordon[1] - dy)).argmin())
            hx, hy = float(cordon[0][j]), float(cordon[1][j])
            dist_km = math.hypot(dx - hx, dy - hy) / 1000.0
            t0 = draw_hour(DEPART[purpose], WEEKEND_DEPARTURE_SHIFT_H[day],
                           u) * 3600 + int(3600 * u())
            # in-network now, so the same seed-plan speed the core tours use
            tt = int(dist_km / 26.0 * 3600) + 240
            arr = t0 + tt
            dur = int(max(1800, ACT_DURATION[purpose] * 60
                          * (1.0 + DURATION_CV * (2.0 * u() - 1.0))))
            back = arr + dur
            if back + tt > DAY_HORIZON_S:
                continue
            # the 30-hour-day cap, single-tour form (issue #37): a return
            # departing past midnight is fine unless this agent also departed
            # in the early-morning hours the tail maps onto
            if t0 < DAY_HORIZON_S - 24 * 3600 and back >= 24 * 3600:
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
                             dest_placement=how))
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


def through_gates():
    """Boundary crossings of major roads, anchored on same-corridor counts.

    A gate is a road edge of a cordon-capable class with one endpoint inside
    the dissolved study boundary and the other at least THROUGH_OUTSIDE_MIN_M
    beyond it - genuinely leaving the area, not bridging the harbour inside it
    (Hannell Street's river crossing is the measured false positive). Its
    volume comes from the nearest CALIBRATION count station on the SAME NAMED
    road within THROUGH_CORRIDOR_KM: only one boundary corridor has a station
    at the crossing itself (the M1 at Wyee, 273 m), the rest are measured
    16-24 km inside, and the name is what carries the corridor identity.

    Reads ONLY split == 'calibration' rows - the filter is structural, ahead of
    any use, so no holdout row can seed demand. Crossings of the same named
    road within THROUGH_CORRIDOR_KM of each other collapse to the
    highest-volume one (two carriageways are one corridor).

    Returns a list of dicts: x, y (EPSG:28356, the inside endpoint), volume
    (veh/weekday, both directions), road, station_key, station_name.
    """
    import geopandas as gpd
    import pyproj
    import shapely

    edges = pd.read_csv(ROADS, usecols=['edge_id', 'road_class', 'name',
                                        'start_lat', 'start_lon',
                                        'end_lat', 'end_lon'])
    edges = edges[edges.road_class.isin(CORDON_ROAD_CLASSES)
                  & edges.name.notna() & (edges.name != '')].reset_index(drop=True)
    lga = gpd.read_file(LGA_ZONES)
    if 'zone_tier' in lga.columns:
        lga = lga[lga.zone_tier == 'core']
    diss = lga.to_crs(_city.crs()).geometry.union_all()
    tf = pyproj.Transformer.from_crs(4326, 28356, always_xy=True)
    sxe, sye = tf.transform(edges.start_lon.to_numpy(dtype=float),
                            edges.start_lat.to_numpy(dtype=float))
    exe, eye = tf.transform(edges.end_lon.to_numpy(dtype=float),
                            edges.end_lat.to_numpy(dtype=float))
    s_in = shapely.contains(diss, shapely.points(sxe, sye))
    e_in = shapely.contains(diss, shapely.points(exe, eye))
    cross = s_in != e_in

    t = pd.read_csv(AADT_TARGETS)
    t = t[t.split == 'calibration'].copy()
    t = t.assign(volume=t.weekday_count.fillna(t.all_days_count))
    t = t[t.volume.notna() & (t.volume > 0)].reset_index(drop=True)
    t = t.assign(road_key=t.road_name.fillna('').str.strip().str.lower())
    sx, sy = tf.transform(t.lon.to_numpy(dtype=float), t.lat.to_numpy(dtype=float))

    # Outward evidence is a property of the ROAD, not of the crossing edge: a
    # motorway's boundary-crossing way often ends a few tens of metres past the
    # polygon while the road itself continues on further ways (measured: the
    # Hunter Expressway's crossing edge ends 61 m out, the Pacific Highway's
    # 31-96 m, while only the M1's happens to run 1.9 km). So the test is
    # whether ANY same-named endpoint lies at least THROUGH_OUTSIDE_MIN_M
    # beyond the boundary within corridor-match range of the crossing - which
    # still rejects Hannell Street, whose river bridge puts nothing more than
    # 2 m beyond the polygon.
    out_d_s = np.where(s_in, 0.0,
                       shapely.distance(diss, shapely.points(sxe, sye)))
    out_d_e = np.where(e_in, 0.0,
                       shapely.distance(diss, shapely.points(exe, eye)))
    name_key = edges['name'].astype(str).str.strip().str.lower().to_numpy()

    gates = []
    for k in np.flatnonzero(cross):
        inside_start = bool(s_in[k])
        row = edges.iloc[k]
        gx, gy = (sxe[k], sye[k]) if inside_start else (exe[k], eye[k])
        road_key = str(row['name']).strip().lower()
        mask = name_key == road_key
        near = THROUGH_CORRIDOR_KM * 1000.0
        outward = (((out_d_s[mask] >= THROUGH_OUTSIDE_MIN_M)
                    & (np.hypot(sxe[mask] - gx, sye[mask] - gy) <= near))
                   | ((out_d_e[mask] >= THROUGH_OUTSIDE_MIN_M)
                      & (np.hypot(exe[mask] - gx, eye[mask] - gy) <= near)))
        if not bool(outward.any()):
            continue
        same = t[t.road_key == road_key]
        if same.empty:
            continue
        pos = same.index.to_numpy()
        d = np.hypot(sx[pos] - gx, sy[pos] - gy)
        j = int(d.argmin())
        if float(d[j]) > THROUGH_CORRIDOR_KM * 1000.0:
            continue
        st = same.iloc[j]
        # The gate's heavy share (DECISIONS.md 9.49): the station's own
        # classified observation where one exists, the declared measured
        # median where it does not. Splits the gate's through volume into
        # car and truck; before this, through trucks rode in the model as
        # PCE-1 cars.
        hs = st.get('heavy_share')
        observed_hs = hs == hs and hs is not None
        gates.append(dict(x=float(gx), y=float(gy), road=str(row['name']),
                          volume=float(st.volume),
                          heavy_share=(float(hs) if observed_hs
                                       else float(HEAVY_SHARE_FALLBACK)),
                          heavy_share_source=('observed' if observed_hs
                                              else 'median_fallback'),
                          station_key=str(st.station_key),
                          station_name=str(st['name']),
                          station_dist_m=round(float(d[j]), 0),
                          sa1=''))
    # collapse same-corridor duplicates (two carriageways, split ways)
    gates.sort(key=lambda g: (-g['volume'], g['road'], g['x'], g['y']))
    kept = []
    for g in gates:
        if any(k['road'].strip().lower() == g['road'].strip().lower()
               and math.hypot(k['x'] - g['x'], k['y'] - g['y']) / 1000.0
               < THROUGH_CORRIDOR_KM for k in kept):
            continue
        kept.append(g)
    kept.sort(key=lambda g: (g['road'], g['x'], g['y']))
    # a gate's inside endpoint sits in a real zone; carrying that SA1 keeps
    # every downstream join (metrics, tier analyses) working on through legs
    if kept:
        sa1 = gpd.read_file(os.path.join(ZON, 'zones_SA1.gpkg'))
        sa1 = sa1.to_crs(_city.crs())[['SA1_CODE21', 'geometry']]
        gpts = gpd.GeoDataFrame(
            geometry=gpd.points_from_xy([g['x'] for g in kept],
                                        [g['y'] for g in kept]),
            crs=_city.crs())
        joined = gpd.sjoin_nearest(gpts, sa1, how='left')
        codes = joined.groupby(joined.index)['SA1_CODE21'].first()
        for i, g in enumerate(kept):
            g['sa1'] = str(codes.get(i, ''))
    return kept


def load_freight_profile():
    """The MEASURED heavy-vehicle temporal profile (extract_freight_profile.py).

    Returns ({day_type: (hours, cumulative shares)}, {day_type: day factor}).
    The hourly shape and the weekend factors are observed at the study slice's
    classified count stations - the two temporal facts the freight layer does
    not have to assume.
    """
    prof = pd.read_csv(FREIGHT_PROFILE)
    cum = {}
    for dt, grp in prof.groupby('day_type'):
        g = grp.sort_values('hour')
        cum[dt] = (g.hour.to_numpy(dtype=int), np.cumsum(g.share.to_numpy()))
    fac = {str(r.day_type): float(r.factor)
           for r in pd.read_csv(FREIGHT_DAY_FACTORS).itertuples()}
    return cum, fac


def draw_freight_hour(profile, day, u):
    hours, cum = profile[day]
    j = int(np.searchsorted(cum, u() * float(cum[-1])))
    return int(hours[min(j, hours.size - 1)])


def through_agents(gates, u, day, seq_base, freight_profile, freight_factor):
    """Through trips: enter at one gate, cross the study area, exit at another.

    One agent is one direction: inbound volume at gate i is half the through
    component of its AADT (the other half is the same vehicles exiting, which
    the opposite gate generates as its own inbound). The exit gate is drawn
    weighted by the candidate gates' observed volumes, restricted to gates at
    least THROUGH_MIN_SEP_KM away so the trip genuinely crosses the area. The
    mode is locked downstream (build_matsim_plans writes lockedMode) - a
    volume anchored on a road count must stay on the road.

    The volume splits into car and truck by the gate's heavy share
    (DECISIONS.md 9.49): each half takes its own observed day-of-week
    behaviour (the external day factor for cars, the measured freight day
    factor for trucks) and its own departure profile (HO for cars, which have
    no observed profile; the MEASURED classified hourly shape for trucks).
    """
    legs = []
    n_car = n_truck = 0
    pid = seq_base
    shift = WEEKEND_DEPARTURE_SHIFT_H[day]
    for i, gi in enumerate(gates):
        cand = [(j, gj) for j, gj in enumerate(gates) if j != i
                and math.hypot(gj['x'] - gi['x'], gj['y'] - gi['y']) / 1000.0
                >= THROUGH_MIN_SEP_KM]
        if not cand:
            continue
        w = norm([gj['volume'] for _, gj in cand])
        cum = np.cumsum(w)
        inbound = 0.5 * THROUGH_SHARE * gi['volume']
        counts = (('through', int(round(inbound * (1.0 - gi['heavy_share'])
                                        * EXTERNAL_DAY_FACTOR[day]))),
                  ('through_freight', int(round(inbound * gi['heavy_share']
                                                * freight_factor[day]))))
        for kind, n in counts:
            is_truck = kind == 'through_freight'
            for _ in range(n):
                pid += 1
                if is_truck:
                    n_truck += 1
                else:
                    n_car += 1
                j = int(np.searchsorted(cum, u()))
                gj = cand[min(j, len(cand) - 1)][1]
                dist_km = math.hypot(gj['x'] - gi['x'],
                                     gj['y'] - gi['y']) / 1000.0
                if is_truck:
                    t0 = (draw_freight_hour(freight_profile, day, u) * 3600
                          + int(3600 * u()))
                else:
                    # HO is the broadest declared daytime departure profile;
                    # through CAR traffic has no observed profile of its own
                    # (DECISIONS.md 9.41)
                    t0 = draw_hour(DEPART['HO'], shift, u) * 3600 + int(3600 * u())
                tt = int(dist_km / 26.0 * 3600) + 240
                legs.append(dict(person_id=pid, day_type=day, tour_id=1,
                                 trip_seq=1, party_size=1, tour_purpose=kind,
                                 agent_tier=('freight' if is_truck else 'through'),
                                 time_flexibility_band='flexible',
                                 purpose=kind, dest_activity_type='home',
                                 origin_sa1=gi['sa1'], dest_sa1=gj['sa1'],
                                 origin_x=round(gi['x'], 1),
                                 origin_y=round(gi['y'], 1),
                                 dest_x=round(gj['x'], 1), dest_y=round(gj['y'], 1),
                                 dep_time_s=t0, arr_time_s=t0 + tt,
                                 straight_dist_km=round(dist_km, 3),
                                 activity_duration_s=0, is_tour_anchor=1,
                                 dest_placement='cordon'))
    return legs, n_car, n_truck


def freight_attractor(core):
    """Per-SA1 freight weight: SA1 jobs x the SA2's observed freight-industry share.

    Jobs are already disaggregated to SA1 (D1_zone_attractions_SA1.csv, an
    observed layer); the census place-of-work table gives each SA2's
    employment by ANZSIC division, and the declared freight-generating
    divisions' share of it weights the SA1 jobs underneath. Both inputs are
    observed; the only choice is WHICH divisions count, and that vocabulary
    is declared (B.freight.attractor_divisions).
    """
    emp = pd.read_csv(EMPLOYMENT_ANZSIC, dtype={'SA2_CODE21': str})
    cols = ['%s_Tot_P' % d for d in FREIGHT_DIVISIONS]
    missing = [c for c in cols if c not in emp.columns]
    if missing:
        raise SystemExit('freight attractor divisions not in %s: %s'
                         % (EMPLOYMENT_ANZSIC, missing))
    tot = emp[[c for c in emp.columns if c.endswith('_Tot_P')]].sum(axis=1)
    share = (emp[cols].sum(axis=1) / tot.replace(0, np.nan)).fillna(0.0)
    sa2_share = dict(zip(emp.SA2_CODE21, share))
    jobs = core['jobs'].to_numpy(dtype=float)
    sa2 = core['SA2_CODE21'].astype(str).to_numpy()
    w = jobs * np.array([sa2_share.get(s, 0.0) for s in sa2])
    if w.sum() <= 0:
        raise SystemExit('the freight attractor is zero everywhere - the '
                         'employment table or the declared divisions changed')
    return w


def freight_agents(core, u, day, seq_base, n_light_trips, car_share,
                   freight_profile, freight_factor, person_day_shape):
    """Internal heavy-vehicle trips over the freight-employment attractor.

    A BACKGROUND LOAD, declared as such (DECISIONS.md 9.49): the volume is
    B.freight.trip_ratio x the observed car-driver share of the day's
    generated core person trips, re-shaped from the person day-of-week curve
    to freight's own MEASURED one - the person-trip base already carries the
    person weekend drop, so it is divided out before the freight factor is
    applied, or the weekend would be dropped twice. One agent is one one-way
    trip, like the through tier: no local observation supports a tour
    structure, and inventing depots would be structure pretending to be
    rigour. Origins draw on the freight attractor; destinations draw on the
    same attractor under the declared distance decay. Departures take the
    measured classified hourly shape.
    """
    person_shape = (person_day_shape[day]
                    / person_day_shape.get('WEEKDAY', 1.0)) or 1.0
    n = int(round(FREIGHT_TRIP_RATIO * car_share * n_light_trips
                  * freight_factor[day] / person_shape))
    if n <= 0:
        return [], 0
    w = freight_attractor(core)
    X = core['x_mga56'].to_numpy(dtype=float)
    Y = core['y_mga56'].to_numpy(dtype=float)
    SA1 = core['SA1_CODE21'].to_numpy()
    RAD = np.sqrt(np.maximum(core['area_km2'].to_numpy(dtype=float), 1e-4)
                  * 1e6 / math.pi) * 0.6
    cum_origin = np.cumsum(norm(w))
    dest_cum = {}   # per-origin-zone destination distribution, built lazily

    def jitter(k):
        return (round(X[k] + RAD[k] * (2.0 * u() - 1.0), 1),
                round(Y[k] + RAD[k] * (2.0 * u() - 1.0), 1))

    legs = []
    pid = seq_base
    for _ in range(n):
        pid += 1
        k0 = min(int(np.searchsorted(cum_origin, u())), X.size - 1)
        if k0 not in dest_cum:
            d_km = np.hypot(X - X[k0], Y - Y[k0]) / 1000.0
            wd = w * np.exp(-FREIGHT_BETA_PER_KM * d_km)
            s = wd.sum()
            dest_cum[k0] = (np.cumsum(wd / s) if s > 0
                            else np.linspace(0, 1, X.size))
        k1 = min(int(np.searchsorted(dest_cum[k0], u())), X.size - 1)
        ox, oy = jitter(k0)
        dx, dy = jitter(k1)
        dist_km = math.hypot(dx - ox, dy - oy) / 1000.0
        t0 = draw_freight_hour(freight_profile, day, u) * 3600 + int(3600 * u())
        tt = int(dist_km / 26.0 * 3600) + 240
        legs.append(dict(person_id=pid, day_type=day, tour_id=1, trip_seq=1,
                         party_size=1, tour_purpose='freight',
                         agent_tier='freight',
                         time_flexibility_band='flexible',
                         purpose='freight', dest_activity_type='home',
                         origin_sa1=SA1[k0], dest_sa1=SA1[k1],
                         origin_x=ox, origin_y=oy, dest_x=dx, dest_y=dy,
                         dep_time_s=t0, arr_time_s=t0 + tt,
                         straight_dist_km=round(dist_km, 3),
                         activity_duration_s=0, is_tour_anchor=1,
                         dest_placement='freight'))
    return legs, n


def hts_car_driver_share():
    """The observed car-driver share of trips, study LGAs, latest survey year.

    Sizes the internal freight base (trip_ratio is heavy trips PER LIGHT
    VEHICLE TRIP, and a light vehicle trip is a car-driver person trip).
    An observed HTS quantity read from the slice, like the purpose shares -
    not a model output, so the identity is evaluable at build time.
    """
    m = pd.read_csv(_city.path('data/processed/hts/hts_mode.csv'))
    m = m[m.geography == 'lga']
    yr = sorted(m.FINANCIAL_YEAR.unique())[-1]
    m = m[m.FINANCIAL_YEAR == yr]
    mode = m.TRAVEL_MODE.astype(str).str.replace('*', '', regex=False).str.strip()
    drv = float(m[mode == 'Vehicle driver'].TRIPS_BY_MODE.sum())
    tot = float(m.TRIPS_BY_MODE.sum())
    if not (tot > 0 and drv > 0):
        raise SystemExit('no Vehicle driver rows in hts_mode.csv for %s' % yr)
    return drv / tot, yr


COLUMNS = ['person_id', 'day_type', 'tour_id', 'trip_seq', 'purpose',
           'tour_purpose', 'dest_activity_type', 'origin_sa1', 'dest_sa1',
           'origin_x', 'origin_y', 'dest_x', 'dest_y', 'dep_time_s',
           'arr_time_s', 'straight_dist_km', 'activity_duration_s',
           'is_tour_anchor', 'party_size', 'time_flexibility_band',
           'dest_placement', 'agent_tier']

# The HTS per-person-per-day trip rate for the study-area LGAs, carried from
# DECISIONS 9 where it was derived from the same tables.
HTS_RATE_PER_PERSON_DAY = CFG.get('B.activity.hts_rate_per_person_day')


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
    # HX shares HE's zone attraction vector rather than adding a column to the
    # land-use layer: an escort destination is an education destination, and the
    # gravity decay is calibrated separately per purpose against the HTS journey
    # distance, so HX still lands on its own observed 6.4 km.
    ATTR = {p: norm(core['attr_' + ATTRACTION_ALIAS.get(p, p)].to_numpy())
            for p in PURPOSES}
    zone_arr = (X, Y, X, Y, RAD, SA1)

    day_shape, day_shape_source = load_network_factors()
    print('detour factor %.4f  [%s]' % (DETOUR_FACTOR, DETOUR_SOURCE), flush=True)
    print('day-type shape %s' % {k: round(v, 4) for k, v in day_shape.items()},
          flush=True)
    print('   [%s]' % day_shape_source, flush=True)

    yr, _total, share, meandist, meandist_lga = hts_rates()
    print('HTS %s | purpose share %s'
          % (yr, {k: round(v, 3) for k, v in share.items()}), flush=True)

    # home LGA per core zone, for the per-LGA decay solve (DECISIONS.md 9.40)
    s2l = pd.read_csv(os.path.join(ZON, 'sa1_to_lga.csv'),
                      dtype={'SA1_CODE21': str})
    lga_of = dict(zip(s2l.SA1_CODE21, s2l.lga_name))
    zone_lga = np.array([lga_of.get(c, '') for c in core['SA1_CODE21']])

    print('joining POIs and CBD buildings to zones ...', flush=True)
    store, n_attractors = load_poi_by_zone(core)
    covered = {p: len(store[p]) for p in PURPOSES}
    print('   %d attractors; core zones with an attractor, by purpose: %s'
          % (n_attractors, covered), flush=True)

    print('locating external stations (cordon crossings) ...', flush=True)
    cordon = cordon_nodes(zones[zones.zone_tier == 'external'])
    print('   %d cordon crossings on %s'
          % (cordon[0].size, ','.join(sorted(CORDON_ROAD_CLASSES))), flush=True)
    gates = through_gates()
    print('   %d through-traffic gates (boundary crossings with a same-road '
          'calibration count within %.0f km):' % (len(gates), THROUGH_CORRIDOR_KM),
          flush=True)
    for g in gates:
        print('      %-24s <- station %s %s (%.0f veh/day, heavy %.4f [%s], '
              '%.1f km away)'
              % (g['road'], g['station_key'], g['station_name'], g['volume'],
                 g['heavy_share'], g['heavy_share_source'],
                 g['station_dist_m'] / 1000.0), flush=True)

    # Freight (DECISIONS.md 9.49): the measured temporal profile, and the
    # observed car-driver share that sizes the internal truck base.
    freight_profile, freight_factor = load_freight_profile()
    car_share, car_share_yr = hts_car_driver_share()
    print('freight: trip ratio %.4f x observed car-driver share %.4f (HTS %s); '
          'day factors %s' % (FREIGHT_TRIP_RATIO, car_share, car_share_yr,
                              {k: round(v, 3) for k, v in freight_factor.items()}),
          flush=True)

    print('calibrating gravity decay against HTS journey distances, '
          'per purpose x home LGA ...', flush=True)
    CUM, decay = calibrate_decay(X, Y, ATTR, meandist,
                                 core['population'].to_numpy(dtype=float),
                                 zone_lga=zone_lga, meandist_lga=meandist_lga)
    for p in PURPOSES:
        d = decay[p]
        print('   %-4s aggregate beta=%.4f  realised %5.2f km vs HTS %5.2f km'
              % (p, d['beta'], d['realised_network_km'], d['hts_network_km']),
              flush=True)
        for lga, dl in sorted(d.get('by_lga', {}).items()):
            if dl.get('fallback'):
                print('        %-16s falls back to the aggregate (no HTS cell)'
                      % lga, flush=True)
            else:
                print('        %-16s beta=%.4f  realised %5.2f km vs HTS %5.2f km'
                      % (lga, dl['beta'], dl['realised_network_km'],
                         dl['hts_network_km']), flush=True)

    hh = pd.read_csv(os.path.join(POP, 'B1_households.csv'),
                     usecols=['household_id', 'home_x_mga56', 'home_y_mga56'])
    home = dict(zip(hh.household_id.to_numpy(),
                    zip(hh.home_x_mga56.to_numpy(), hh.home_y_mga56.to_numpy())))
    del hh
    persons = pd.read_csv(os.path.join(POP, 'B1_synthetic_population.csv'),
                          dtype={'home_sa1': str},
                          usecols=['person_id', 'household_id', 'home_sa1', 'age',
                                   'employment_status', 'student_status',
                                   'car_available', 'licence_holder'])
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
    est = persons.employment_status.astype(str).to_numpy().astype('U24')
    emp = np.char.startswith(est, 'employed')
    emp_ft = (est == 'employed_full_time')
    stu = (persons.student_status.astype(str).to_numpy() == 'full_time')
    cav = (persons.car_available.to_numpy() == 1)
    lic = (persons.licence_holder.to_numpy() == 1)
    del persons

    # The weekday priority between work and study (age-structure dossier 3.4):
    # full-time work outranks study, full-time study outranks a part-time job -
    # a 16-year-old with a weekend job goes to school on a weekday. The old
    # rule sent every employed full-time student to work, which mattered
    # little while the population had no age-conditional employment and every
    # under-18 was a full-time student; with G46/G01 rates it would misdirect
    # the 15-19 band, whose employment is 67% part-time alongside study.
    work_first = emp_ft | (emp & ~stu)
    edu_first = stu & ~work_first

    # households whole, members in person order, for the escort binding
    hh_members = {}
    hh_order = []
    for i in range(n_persons):
        h = int(hid[i])
        if h not in hh_members:
            hh_members[h] = []
            hh_order.append(h)
        hh_members[h].append(i)

    employed_frac = float(work_first.mean())
    # a person only makes an education tour if they are not already making a
    # work tour, so the student fraction used for the rate solve is the
    # full-time students not directed to work
    student_frac = float(edu_first.mean())
    child_frac = float((age < 12).mean())
    licence_frac = float(lic.mean())
    day_rate = solve_day_rates(HTS_RATE_PER_PERSON_DAY, day_shape)
    stats = dict(seed=seed, hts_year=yr,
                 hts_rate_per_person_day=HTS_RATE_PER_PERSON_DAY,
                 day_rate={k: round(v, 4) for k, v in day_rate.items()},
                 day_rate_shape={k: round(v, 4) for k, v in day_shape.items()},
                 day_rate_shape_source=day_shape_source,
                 sat_to_sun_rate=SAT_TO_SUN_RATE,
                 sat_to_sun_sweep=list(SAT_TO_SUN_SWEEP),
                 day_purpose_mix=DAY_PURPOSE_MIX,
                 day_purpose_mix_sweep=DAY_PURPOSE_MIX_SWEEP,
                 p_mandatory=P_MANDATORY,
                 p_mandatory_work_sweep=list(P_MANDATORY_WORK_SWEEP),
                 p_mandatory_education_sweep=list(P_MANDATORY_EDUCATION_SWEEP),
                 p_intermediate_stop=P_INTERMEDIATE_STOP,
                 p_intermediate_sweep=list(P_INTERMEDIATE_SWEEP),
                 p_second_stop=P_SECOND_STOP,
                 p_second_stop_sweep=list(P_SECOND_STOP_SWEEP),
                 child_tour_retention=CHILD_TOUR_RETENTION,
                 child_tour_retention_sweep=list(CHILD_TOUR_RETENTION_SWEEP),
                 act_duration_min=ACT_DURATION,
                 act_duration_sweep=ACT_DURATION_SWEEP,
                 external_interaction_rate=EXTERNAL_INTERACTION_RATE,
                 external_interaction_sweep=list(EXTERNAL_INTERACTION_SWEEP),
                 through_share=THROUGH_SHARE,
                 through_corridor_match_km=THROUGH_CORRIDOR_KM,
                 through_outside_min_m=THROUGH_OUTSIDE_MIN_M,
                 through_min_separation_km=THROUGH_MIN_SEP_KM,
                 through_gates=[dict(road=g['road'], station=g['station_key'],
                                     name=g['station_name'],
                                     volume=g['volume'],
                                     heavy_share=g['heavy_share'],
                                     heavy_share_source=g['heavy_share_source'],
                                     station_dist_m=g['station_dist_m'])
                                for g in gates],
                 freight_trip_ratio=FREIGHT_TRIP_RATIO,
                 freight_trip_ratio_sweep=list(CFG.sweep('B.freight.trip_ratio')),
                 freight_gravity_beta_per_km=FREIGHT_BETA_PER_KM,
                 freight_gravity_beta_sweep=list(
                     CFG.sweep('B.freight.gravity_beta_per_km')),
                 freight_attractor_divisions=FREIGHT_DIVISIONS,
                 freight_car_driver_share=round(car_share, 4),
                 freight_car_driver_share_year=car_share_yr,
                 freight_day_factor={k: round(v, 4)
                                     for k, v in freight_factor.items()},
                 heavy_share_fallback=HEAVY_SHARE_FALLBACK,
                 decay=decay,
                 detour_factor=DETOUR_FACTOR, detour_sweep=list(DETOUR_SWEEP),
                 detour_source=DETOUR_SOURCE,
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
            d, share, day_rate[d], employed_frac, student_frac, child_frac,
            licence_frac)
        stats.setdefault('rate_solution', {})[d] = rate_diag
        counts = {p: rng.poisson(rates[p], size=n_persons)
                  for p in ('HS', 'HO', 'WB', 'HX')}

        n_legs = n_tours = n_travel = 0
        dropped = [0, 0]   # [over-horizon, midnight-collision (issue #37)]
        by_purpose = collections.Counter()
        tours_hist = collections.Counter()
        esc = dict(requested=0, bound=0, unbound=0,
                   by_priority=collections.Counter(),
                   bound_km=0.0, bound_n=0, unbound_km=0.0, unbound_n=0)
        for h in hh_order:
            members = hh_members[h]
            # Escort binding (DECISIONS.md 9.46): members without an HX draw
            # build first, so an escorter binds to a trip that already exists.
            # A second escorter in the same household sees the first one's
            # tours too; nothing is ever bound to an HX tour itself.
            if ESCORT_BINDING:
                pass1 = [i for i in members if counts['HX'][i] == 0]
                pass2 = [i for i in members if counts['HX'][i] > 0]
            else:
                pass1, pass2 = members, []
            candidates = []
            claimed = set()
            legs_of = {}
            for i in pass1 + pass2:
                hxy = home.get(hid[i])
                if hxy is None:
                    continue
                hz = zi.get(hsa[i])
                if hz is None:
                    continue
                person = dict(hx=float(hxy[0]), hy=float(hxy[1]), hzi=hz,
                              age=int(age[i]), employed=bool(work_first[i]),
                              student=bool(edu_first[i]), cav=bool(cav[i]),
                              licence=bool(lic[i]))
                pre = {p: int(counts[p][i]) for p in ('HS', 'HO', 'WB', 'HX')}
                fixed = ()
                may_escort = person['licence'] or not ESCORT_REQUIRES_LICENCE
                if pre['HX'] > 0 and ESCORT_BINDING and may_escort:
                    esc['requested'] += pre['HX']
                    fixed = bind_escort_tours(pre['HX'], candidates, claimed)
                    pre['HX'] -= len(fixed)
                    esc['bound'] += len(fixed)
                    esc['unbound'] += pre['HX']
                    for f in fixed:
                        esc['by_priority'][f['priority']] += 1
                legs, tour_anchors = build_day(person, d, rates, CUM, store,
                                               zone_arr, u, pre, dropped,
                                               fixed_tours=fixed)
                for a in tour_anchors:
                    if a['purpose'] == 'HX':
                        continue
                    candidates.append(dict(
                        member=int(pid[i]), tour_id=a['tour_id'],
                        purpose=a['purpose'], dep_s=a['dep_s'], k=a['k'],
                        dx=a['dx'], dy=a['dy'], licence=bool(lic[i])))
                if legs:
                    legs_of[i] = legs
            for i in sorted(legs_of):
                legs = legs_of[i]
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
                    if leg['tour_purpose'] == 'HX' and leg['is_tour_anchor'] == 1:
                        side = 'bound' if leg['dest_placement'] == 'escorted' \
                            else 'unbound'
                        esc[side + '_km'] += leg['straight_dist_km']
                        esc[side + '_n'] += 1
                    w.writerow(leg)
                # the #37 cap can drop the highest-numbered tour, so count the
                # tours that exist rather than reading the last id
                ntp = len({l['tour_id'] for l in legs})
                tours_hist[ntp] += 1
                n_legs += len(legs)
                n_tours += ntp
        ext_legs, n_ext = external_agents(zones, core, decay, u, d,
                                          EXTERNAL_PERSON_ID_BASE, store, cordon)
        for leg in ext_legs:
            w.writerow(leg)
        thr_legs, n_thr, n_thr_truck = through_agents(
            gates, u, d, EXTERNAL_PERSON_ID_BASE + n_ext,
            freight_profile, freight_factor)
        for leg in thr_legs:
            w.writerow(leg)
        frt_legs, n_frt = freight_agents(
            core, u, d, EXTERNAL_PERSON_ID_BASE + n_ext + n_thr + n_thr_truck,
            n_legs, car_share, freight_profile, freight_factor, day_shape)
        for leg in frt_legs:
            w.writerow(leg)
        fh.close()
        stats['by_day'][d] = dict(
            external_agents=n_ext, external_legs=len(ext_legs),
            through_agents=n_thr, through_legs=len(thr_legs),
            through_freight_agents=n_thr_truck,
            freight_internal_agents=n_frt,
            freight_agents_total=n_thr_truck + n_frt,
            legs=n_legs, tours=n_tours, travelling_persons=n_travel,
            legs_per_person=round(n_legs / max(n_persons, 1), 3),
            tours_per_traveller=round(n_tours / max(n_travel, 1), 3),
            tours_dropped_over_horizon=dropped[0],
            tours_dropped_midnight_collision=dropped[1],
            by_purpose=dict(by_purpose),
            # DECISIONS.md 9.46. The trip-length comparison is REPORTED, never
            # tuned: an escort's length is now the escorted trip's own.
            escort_binding=dict(
                enabled=bool(ESCORT_BINDING),
                scope=ESCORT_SCOPE,
                hx_tours_requested=esc['requested'],
                hx_tours_bound=esc['bound'],
                hx_tours_unbound_no_candidate=esc['unbound'],
                bound_by_priority={str(k): v for k, v
                                   in sorted(esc['by_priority'].items())},
                anchors_placed_bound=esc['bound_n'],
                anchors_placed_unbound=esc['unbound_n'],
                mean_network_km_bound=(
                    round(esc['bound_km'] / esc['bound_n'] * DETOUR_FACTOR, 2)
                    if esc['bound_n'] else None),
                mean_network_km_unbound=(
                    round(esc['unbound_km'] / esc['unbound_n'] * DETOUR_FACTOR, 2)
                    if esc['unbound_n'] else None),
                hts_network_km=(round(meandist['HX'], 2)
                                if 'HX' in meandist else None)))
        print('%-8s %9d legs %8d tours %6.3f legs/person  dropped=%d '
              'midnight-capped=%d  through=%d  freight=%d (%d through + %d '
              'internal)  HX bound=%d/%d'
              % (d, n_legs, n_tours, n_legs / max(n_persons, 1), dropped[0],
                 dropped[1], n_thr, n_thr_truck + n_frt, n_thr_truck, n_frt,
                 esc['bound'], esc['bound'] + esc['unbound']),
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
