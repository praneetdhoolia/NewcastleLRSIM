#!/usr/bin/env python
"""Measure, from Newcastle data, three factors P3 previously assumed.

Writes `params/C2_network_factors.json`, which `build_activity_chains.py`
consumes. Each factor here was a typed-in constant until this script existed;
each is now derived from an observed layer already in the package, and the ones
that still cannot be observed say so and keep a sweep range instead.

  detour_factor          the straight-line to network-distance ratio, routed
                         over the observed A1 road graph. Used to compare the
                         gravity model against HTS *journey* distances, which
                         are network distances. Previously assumed 1.30.

  day_type_rate_shape    weekday vs weekend travel, from the observed RMS
                         traffic counts, which publish WEEKDAYS and WEEKENDS
                         periods per station-year. Previously assumed outright.
                         Note what this can and cannot settle: the counts
                         separate weekday from weekend but **not Saturday from
                         Sunday**, so the split within the weekend stays
                         assumed and swept.

  work_attendance        share of employed persons who travelled to work,
                         from census G62. Used only as the **lower bound** of
                         the P_MANDATORY sweep, never as the value - census
                         night was August 2021 and 19.2% worked from home, so
                         the figure carries the lockdown with it (DECISIONS.md
                         2.4 already rules G62 out as a behavioural rate).

Determinism: the routing sample is drawn from one seeded generator over zones
in sorted order, so the measured factor is reproducible.
"""
import os
import sys
import csv
import json
import argparse

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shape_tools import RoadGraph
from osm_parse import haversine

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import registry as _registry  # noqa: E402
CFG = _registry.load()

LU = 'data/processed/landuse'
OBS = 'data/processed/observed'
CEN = 'data/processed/census'
OUT = 'params/C2_network_factors.json'
SEED = 20260810
MIN_PAIR_M = 500.0
# Width of the distance band a destination POI is drawn from, either side of
# the observed trip length. Wide enough that every origin has candidates,
# narrow enough that the measurement stays at the mode's own length scale.
BAND = 0.25


def measure_detour(n_pairs, seed):
    """Ratio of total network distance to total straight-line distance.

    The aggregate ratio, not the mean of per-pair ratios: the factor is applied
    to a *mean* journey distance, and E[network]/E[straight] is the quantity
    that converts one mean into the other. The mean of ratios (1.43 on this
    network) is pulled up by short trips with high circuity and would overstate
    the correction for the long trips that dominate the distance mean.
    """
    g = RoadGraph()
    z = pd.read_csv(os.path.join(LU, 'D1_zone_attractions_SA1.csv'),
                    dtype={'SA1_CODE21': str})
    z = z[z.zone_tier == 'core'].sort_values('SA1_CODE21').reset_index(drop=True)
    pop = z.population.to_numpy(dtype=float)
    pop = np.where(pop > 0, pop, 0.0)
    pop = pop / pop.sum()
    lat, lon = z.lat.to_numpy(), z.lon.to_numpy()
    rng = np.random.default_rng(seed)

    sum_net = sum_straight = 0.0
    ratios = []
    routed = unroutable = 0
    for _ in range(n_pairs):
        i, j = rng.choice(len(z), size=2, p=pop, replace=False)
        a, b = (lat[i], lon[i]), (lat[j], lon[j])
        sd = haversine(a, b)
        if sd < MIN_PAIR_M:
            continue
        na, _ = g.nearest_node(a)
        nb, _ = g.nearest_node(b)
        path = g.shortest_path(na, nb) if (na and nb) else None
        if not path:
            unroutable += 1
            continue
        nd = sum(haversine(x, y) for x, y in zip(path, path[1:]))
        if nd <= 0:
            continue
        routed += 1
        sum_net += nd
        sum_straight += sd
        ratios.append(nd / sd)
    r = np.array(ratios)
    aggregate = sum_net / sum_straight
    return dict(
        value=round(float(aggregate), 4),
        sweep=[round(float(np.percentile(r, 25)), 3),
               round(float(np.percentile(r, 75)), 3)],
        source='measured - shortest path over the observed A1 road graph',
        pairs_routed=routed, pairs_unroutable=unroutable,
        sample_seed=seed,
        mean_of_ratios=round(float(r.mean()), 4),
        median_of_ratios=round(float(np.median(r)), 4),
        note='aggregate ratio of summed network to summed straight-line '
             'distance over population-weighted zone pairs; the sweep is the '
             'interquartile range of the per-pair ratios')


class ActiveGraph(RoadGraph):
    """The network a pedestrian or cyclist actually uses.

    The A6 active layer alone will not do: 23,808 of its 35,653 edges are
    `footway`, and OSM maps a separate footway beside a residential street only
    where somebody has drawn one. Routing walk trips over A6 by itself would
    traverse a sparse, largely disconnected graph and report circuity that is an
    artefact of the mapping rather than of the streets. So this unions A6 with
    every road a pedestrian may legally use.

    The exclusion is by OSM highway class, which any city's extract carries -
    no place name and no extent.
    """

    #: Road classes a pedestrian may not walk along. Motorway only: Australian
    #: trunk and primary roads carry footpaths and are walked.
    NO_FOOT = frozenset(('motorway', 'motorway_link'))

    def __init__(self):
        ways = []
        ways += self._load('data/processed/network/A6_footway_edges.csv',
                           'data/processed/network/A6_footway_geometry.jsonl',
                           'footway_edge_id',
                           lambda r: r.get('foot') != 'no')
        ways += self._load('data/processed/network/A1_road_edges.csv',
                           'data/processed/network/A1_road_geometry.jsonl',
                           'edge_id',
                           lambda r: r.get('road_class') not in self.NO_FOOT)
        ways.sort(key=lambda w: w[0])
        self._build(ways)

    @staticmethod
    def _load(edges_csv, geom_jsonl, id_col, keep):
        geom = {}
        with open(geom_jsonl, encoding='utf-8') as f:
            for ln in f:
                d = json.loads(ln)
                geom[d[id_col]] = [(c[1], c[0]) for c in d['coords']]
        out = []
        with open(edges_csv, encoding='utf-8') as f:
            for r in csv.DictReader(f):
                if not keep(r):
                    continue
                pts = geom.get(r[id_col])
                if pts and len(pts) >= 2:
                    out.append((r[id_col], (r.get('name') or '').strip(), pts))
        return out


def measure_active_detour(n_pairs, seed, target_m, label):
    """Straight-line to path ratio on the ACTIVE network, at one trip length.

    `RUN.routing.beeline_distance_factor` was assumed 1.30 with a note that the
    measured 1.3376 belongs to the road graph and "has not been measured on the
    active network". This measures it, rather than aliasing one to the other:
    they are different networks AND different trip lengths, and circuity falls
    with distance, so a factor measured over multi-kilometre zone pairs is the
    wrong number for a 700 m walk.

    Sampling is at the observed trip length for the mode, between the kind of
    endpoints the model actually uses: an origin is drawn from the
    population-weighted core zones, and the destination is an observed **POI**
    lying at roughly `target_m` from it. Drawing a random bearing instead was
    tried first and rejected - it sends walk trips to points nobody walks to,
    across the harbour and the motorway, and the resulting ratio is a property
    of those barriers rather than of walking. It measured 1.96 for walk against
    a median of 1.52, the gap being the tail of destinations with no walkable
    route. B2 places every activity on a POI or a building footprint, so POI
    endpoints are the model's own geometry.
    """
    g = ActiveGraph()
    z = pd.read_csv(os.path.join(LU, 'D1_zone_attractions_SA1.csv'),
                    dtype={'SA1_CODE21': str})
    z = z[z.zone_tier == 'core'].sort_values('SA1_CODE21').reset_index(drop=True)
    pop = z.population.to_numpy(dtype=float)
    pop = np.where(pop > 0, pop, 0.0)
    pop = pop / pop.sum()
    lat, lon = z.lat.to_numpy(), z.lon.to_numpy()
    rng = np.random.default_rng(seed)

    poi = pd.read_csv(os.path.join(LU, 'D1_poi.csv')).sort_values('poi_id')
    plat = poi.lat.to_numpy()
    plon = poi.lon.to_numpy()

    sum_net = sum_straight = 0.0
    ratios = []
    routed = unroutable = nodest = 0
    for _ in range(n_pairs):
        i = rng.choice(len(z), p=pop)
        a = (lat[i], lon[i])
        # POIs in a band around the target distance. Metre-scale conversion is
        # local and only used to select candidates; every reported distance is
        # haversine.
        dy = (plat - lat[i]) * 111320.0
        dx = (plon - lon[i]) * 111320.0 * np.cos(np.radians(lat[i]))
        d = np.hypot(dx, dy)
        cand = np.flatnonzero((d >= target_m * (1.0 - BAND))
                              & (d <= target_m * (1.0 + BAND)))
        if not len(cand):
            nodest += 1
            continue
        k = cand[rng.integers(len(cand))]
        b = (float(plat[k]), float(plon[k]))
        na, _ = g.nearest_node(a)
        nb, _ = g.nearest_node(b)
        if na is None or nb is None or na == nb:
            unroutable += 1
            continue
        # Measure between the SNAPPED points, so the ratio is a property of the
        # network rather than of how far the sample fell from it.
        sd = haversine(na, nb)
        if sd <= 0:
            continue
        path = g.shortest_path(na, nb)
        if not path:
            unroutable += 1
            continue
        nd = sum(haversine(x, y) for x, y in zip(path, path[1:]))
        if nd <= 0:
            continue
        routed += 1
        sum_net += nd
        sum_straight += sd
        ratios.append(nd / sd)
    if not ratios:
        raise SystemExit('no %s pair could be routed on the active network' % label)
    r = np.array(ratios)
    return dict(
        value=round(float(sum_net / sum_straight), 4),
        sweep=[round(float(np.percentile(r, 25)), 3),
               round(float(np.percentile(r, 75)), 3)],
        source='measured - shortest path over the observed A6 active network '
               'unioned with every road class a pedestrian may use, between '
               'population-weighted origins and observed POI destinations',
        target_distance_m=target_m, band=BAND,
        pairs_routed=routed, pairs_unroutable=unroutable,
        pairs_without_destination=nodest, sample_seed=seed,
        mean_of_ratios=round(float(r.mean()), 4),
        median_of_ratios=round(float(np.median(r)), 4),
        note='sampled at the observed %s trip length between population-weighted '
             'origins and observed POI destinations; the aggregate ratio of '
             'summed path to summed straight-line distance, with the sweep the '
             'interquartile range of the per-pair ratios' % label)


def measure_day_type():
    """Weekday vs weekend traffic, from the observed RMS counts."""
    t = pd.read_csv(os.path.join(OBS, 'traffic_aadt_newcastle.csv'),
                    low_memory=False)
    t = t[t.classification_type.isin(['ALL VEHICLES', 'UNCLASSIFIED'])]
    piv = t.pivot_table(index=['station_key', 'year'], columns='period',
                        values='traffic_count', aggfunc='mean')
    piv = piv.dropna(subset=['WEEKDAYS', 'WEEKENDS'])
    r = (piv['WEEKENDS'] / piv['WEEKDAYS']).replace([np.inf, -np.inf], np.nan).dropna()
    r = r[(r > 0.2) & (r < 2.0)]
    med = float(r.median())
    return dict(
        weekend_to_weekday=round(med, 4),
        sweep=[round(float(r.quantile(0.25)), 3), round(float(r.quantile(0.75)), 3)],
        station_years=int(len(r)),
        source='measured - RMS traffic counts, WEEKENDS vs WEEKDAYS period',
        note='vehicle volume, not person trips: it fixes the weekday/weekend '
             'ratio but says nothing about how the weekend splits between '
             'Saturday and Sunday, which stays assumed and swept')


def measure_work_attendance():
    """Share of employed persons who travelled to work, census G62."""
    g = pd.read_csv(os.path.join(CEN, 'census2021_G62_SA1.csv'))
    tot = float(g['Tot_P'].sum())
    home = float(g['Worked_home_P'].sum())
    away = float(g['Did_not_go_to_work_P'].sum())
    travelled = (tot - home - away) / tot if tot > 0 else float('nan')
    return dict(
        census_day_attendance=round(travelled, 4),
        worked_from_home_pct=round(100 * home / tot, 2),
        did_not_go_pct=round(100 * away / tot, 2),
        source='measured - census 2021 G62, used as a sweep LOWER BOUND only',
        note='census night was August 2021 and 19.2% worked from home, so this '
             'carries the lockdown with it. DECISIONS.md 2.4 already rules G62 '
             'out as a behavioural rate; it bounds the P_MANDATORY sweep from '
             'below rather than setting it.')


def main(n_pairs=600, seed=SEED):
    print('routing %d zone pairs over the A1 road graph ...' % n_pairs, flush=True)
    detour = measure_detour(n_pairs, seed)
    print('   detour factor %.4f (was assumed 1.30), sweep %s from %d routed pairs'
          % (detour['value'], detour['sweep'], detour['pairs_routed']), flush=True)
    day = measure_day_type()
    print('   weekend/weekday traffic %.4f over %d station-years, sweep %s'
          % (day['weekend_to_weekday'], day['station_years'], day['sweep']), flush=True)
    att = measure_work_attendance()
    print('   census-day work attendance %.4f (sweep lower bound only)'
          % att['census_day_attendance'], flush=True)
    # The teleported beeline factor belongs to the ACTIVE network and to the
    # trip lengths walk and bike are actually made at, not to the road graph.
    # Trip lengths come from C4/the registry, measured from HTS.
    active = {}
    for label in ('walk', 'bike'):
        target = CFG.get('C.constraint.trip_length_km.%s' % label) * 1000.0
        print('routing %d %s pairs at %.0f m over the active network ...'
              % (n_pairs, label, target), flush=True)
        active[label] = measure_active_detour(n_pairs, seed, target, label)
        print('   %s beeline factor %.4f, sweep %s from %d routed pairs'
              % (label, active[label]['value'], active[label]['sweep'],
                 active[label]['pairs_routed']), flush=True)
    out = dict(seed=seed, detour_factor=detour, day_type=day,
               work_attendance=att, active_beeline_factor=active)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, 'w'), indent=2)
    print('wrote %s' % OUT, flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--pairs', type=int, default=600)
    ap.add_argument('--seed', type=int, default=SEED)
    a = ap.parse_args()
    main(a.pairs, a.seed)
