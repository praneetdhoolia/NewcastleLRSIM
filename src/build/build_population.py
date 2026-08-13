#!/usr/bin/env python
"""Layer B1 - synthetic population (households and persons).

Method
------
Households are drawn per SA1 to match the census marginals for household size
(G35), motor vehicles (G34) and dwelling structure (G36). Persons are then drawn
to match the SA1 age-sex distribution (G04) and the age-conditional labour force
status (G46). Licence holding, income band and occupation follow.

Daily activity chains are **not** built here. They were until P3, as layer B2 in
this same pass; `src/build/build_activity_chains.py` now owns them, builds them
as home-anchored tours rather than a shuffled activity list, and produces one
file per day type. See DECISIONS.md 9.

Everything is seeded. Re-running with the same seed reproduces the population
exactly; the seed is recorded in the scenario configuration (schema E1).
"""
import os
import csv
import json
import math
import argparse
import numpy as np
import pandas as pd

# Model inputs come from config/registry/<city>/, not from literals here. Every
# value below carries its units, provenance and either a sweep, a held-fixed rule
# or a derived-from identity there. See DECISIONS.md 15.
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import registry as _registry  # noqa: E402
CFG = _registry.load()

CEN = 'data/processed/census'
ZON = 'data/processed/zones'
LU = 'data/processed/landuse'
HTS = 'data/processed/hts'
OUT = 'demand'
os.makedirs(os.path.join(OUT, 'population'), exist_ok=True)
os.makedirs(os.path.join(OUT, 'plans'), exist_ok=True)

AGE_BANDS = CFG.get('B.population.age_bands')
BAND_LABEL = ['0-4', '5-11', '12-17', '18-24', '25-34', '35-44',
              '45-54', '55-64', '65-74', '75-84', '85+']
# NSW driver-licence holding rate by age band (assumed; ABS/TfNSW-typical)
LICENCE_RATE = CFG.get('B.population.licence_rate_by_age_band')
OCCUPATIONS = ['Managers', 'Professionals', 'TechnicTrades_Wrs', 'CommunPersnlSvc_W',
               'ClericalAdminis_W', 'Sales_W', 'Mach_oper_drivers', 'Labourers']
INCOME_BANDS = ['Neg_Nil', '1_149', '150_299', '300_399', '400_499', '500_649',
                '650_799', '800_999', '1000_1249', '1250_1499', '1500_1749',
                '1750_1999', '2000_2999', '3000_more']

PURPOSES = ['HW', 'HE', 'HS', 'HO', 'WB', 'NHB']
HTS_PURPOSE_MAP = {
    'Commute': 'HW', 'Education/childcare': 'HE', 'Shopping': 'HS',
    'Personal business': 'HO', 'Social/recreation': 'HO', 'Serve passenger': 'NHB',
    'Work related business': 'WB', 'Other': 'HO',
}
# departure-time profiles: probability by hour 0..23. Assumed, NSW-typical shapes.
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
# mean activity duration in minutes, by purpose (assumed)
ACT_DURATION = {'HW': 465, 'HE': 360, 'HS': 45, 'HO': 90, 'WB': 60, 'NHB': 20}


def rd(name, **kw):
    return pd.read_csv(os.path.join(CEN, name), low_memory=False, **kw)


def norm(a):
    a = np.asarray(a, dtype=float)
    a = np.where(np.isfinite(a) & (a > 0), a, 0.0)
    s = a.sum()
    return a / s if s > 0 else np.full(len(a), 1.0 / len(a))


def load_marginals():
    key = 'SA1_CODE_2021'
    g04a, g04b = rd('census2021_G04A_SA1.csv'), rd('census2021_G04B_SA1.csv')
    g04 = g04a.merge(g04b, on=[key, 'zone_tier'], suffixes=('', '_b'))
    g34 = rd('census2021_G34_SA1.csv')
    g35 = rd('census2021_G35_SA1.csv')
    g36 = rd('census2021_G36_SA1.csv')
    g43 = rd('census2021_G43_SA1.csv')
    g46 = rd('census2021_G46A_SA1.csv')
    g17 = rd('census2021_G17A_SA1.csv').merge(
        rd('census2021_G17B_SA1.csv'), on=[key, 'zone_tier'], suffixes=('', '_b'))
    g60 = rd('census2021_G60A_SA1.csv').merge(
        rd('census2021_G60B_SA1.csv'), on=[key, 'zone_tier'], suffixes=('', '_b'))
    for d in (g04, g34, g35, g36, g43, g46, g17, g60):
        d[key] = d[key].astype(str)
    return dict(key=key, g04=g04, g34=g34, g35=g35, g36=g36, g43=g43,
                g46=g46, g17=g17, g60=g60)


def age_sex_dist(row):
    """Collapse single-year age columns into the model's age bands, by sex."""
    out = np.zeros((len(AGE_BANDS), 2))
    for bi, (lo, hi) in enumerate(AGE_BANDS):
        for a in range(lo, min(hi, 99) + 1):
            for si, sx in enumerate(('M', 'F')):
                c = 'Age_yr_%d_%s' % (a, sx)
                if c in row:
                    v = row[c]
                    if pd.notna(v):
                        out[bi, si] += float(v)
        if hi >= 100:
            for c, si in (('Age_yr_100_yr_over_M', 0), ('Age_yr_100_yr_over_F', 1)):
                if c in row and pd.notna(row[c]):
                    out[bi, si] += float(row[c])
    return out


def hts_trip_rates():
    """Trips per person per day by purpose, from the HTS study-area rows."""
    m = pd.read_csv(os.path.join(HTS, 'hts_mode_newcastle.csv'))
    p = pd.read_csv(os.path.join(HTS, 'hts_purpose_newcastle.csv'))
    m['TRIPS_BY_MODE'] = pd.to_numeric(m['TRIPS_BY_MODE'], errors='coerce')
    p['JOURNEYS_BY_MODE'] = pd.to_numeric(p['JOURNEYS_BY_MODE'], errors='coerce')
    lm = m[(m.geography == 'lga')]
    yr = sorted(lm['FINANCIAL_YEAR'].astype(str).unique())[-1]
    lm = lm[lm['FINANCIAL_YEAR'].astype(str) == yr]
    lp = p[(p.geography == 'lga') & (p['FINANCIAL_YEAR'].astype(str) == yr)]
    trips_total = lm['TRIPS_BY_MODE'].sum()
    # population of the same LGA set, from the zone table
    z = pd.read_csv(os.path.join(LU, 'D1_zone_attractions_SA1.csv'))
    pop = z.loc[z.zone_tier == 'core', 'population'].sum()
    rate_total = trips_total / max(pop, 1)
    sh = {}
    for _, r in lp.iterrows():
        pur = HTS_PURPOSE_MAP.get(str(r['TRAVEL_PURPOSE']).strip().rstrip('*'))
        if pur and pd.notna(r['JOURNEYS_BY_MODE']):
            sh[pur] = sh.get(pur, 0.0) + float(r['JOURNEYS_BY_MODE'])
    tot = sum(sh.values()) or 1.0
    rates = {k: rate_total * v / tot for k, v in sh.items()}
    for k in PURPOSES:
        rates.setdefault(k, 0.0)
    # mean journey distance by purpose, for the gravity decay
    dist = {}
    for _, r in lp.iterrows():
        pur = HTS_PURPOSE_MAP.get(str(r['TRAVEL_PURPOSE']).strip().rstrip('*'))
        v = r.get('JOURNEY_AVG_DISTANCE')
        if pur and pd.notna(v):
            dist.setdefault(pur, []).append(float(v))
    dist = {k: float(np.mean(v)) for k, v in dist.items()}
    for k in PURPOSES:
        dist.setdefault(k, 8.0)
    return yr, rate_total, rates, dist


def main(seed=20260810, sample=1.0, max_sa1=None):
    rng = np.random.default_rng(seed)
    M = load_marginals()
    key = M['key']
    zones = pd.read_csv(os.path.join(LU, 'D1_zone_attractions_SA1.csv'),
                        dtype={'SA1_CODE21': str})
    core = zones[zones.zone_tier == 'core'].reset_index(drop=True)
    if max_sa1:
        core = core.head(max_sa1)
    idx = {k: M[k].set_index(key) for k in ('g04', 'g34', 'g35', 'g36', 'g43', 'g46', 'g17', 'g60')}

    hh_f = open(os.path.join(OUT, 'population', 'B1_households.csv'), 'w', newline='', encoding='utf-8')
    pp_f = open(os.path.join(OUT, 'population', 'B1_synthetic_population.csv'), 'w', newline='', encoding='utf-8')
    hw = csv.writer(hh_f)
    pw = csv.writer(pp_f)
    hw.writerow(['household_id', 'home_sa1', 'home_x_mga56', 'home_y_mga56', 'home_lon', 'home_lat',
                 'household_size', 'household_vehicles', 'dwelling_type', 'weight'])
    pw.writerow(['person_id', 'household_id', 'home_sa1', 'age_band', 'age', 'sex',
                 'employment_status', 'occupation_anzsco1', 'income_band', 'licence_holder',
                 'household_vehicles', 'household_size', 'dwelling_type', 'student_status',
                 'mobility_impairment_flag', 'car_available', 'weight'])

    hid = 0
    pid = 0
    stats = dict(households=0, persons=0, employed=0, students=0, zero_car_hh=0)

    dwell_cols = [('separate_house', 'OPDs_Separate_house_Dwellings'),
                  ('semi_terrace', 'OPDs_SD_r_t_h_th_Tot_Dwgs'),
                  ('flat_apartment', 'OPDs_F_ap_I_Tot_Dwgs'),
                  ('other', 'OPDs_Other_dwelling_Tot_Dwgs')]

    for _, z in core.iterrows():
        sa1 = z['SA1_CODE21']
        pop = int(z['population'])
        if pop <= 0:
            continue
        pop = int(round(pop * sample))
        if pop <= 0:
            continue
        try:
            r04 = idx['g04'].loc[sa1]
            r34 = idx['g34'].loc[sa1]
            r35 = idx['g35'].loc[sa1]
            r36 = idx['g36'].loc[sa1]
            r43 = idx['g43'].loc[sa1]
            r46 = idx['g46'].loc[sa1]
            r17 = idx['g17'].loc[sa1]
            r60 = idx['g60'].loc[sa1]
        except KeyError:
            continue
        if isinstance(r04, pd.DataFrame):
            r04 = r04.iloc[0]

        asd = age_sex_dist(r04)
        if asd.sum() <= 0:
            continue
        p_age = norm(asd.sum(axis=1))
        p_sex_given_age = np.array([norm(asd[b])[0] if asd[b].sum() > 0 else 0.5
                                    for b in range(len(AGE_BANDS))])

        # household size distribution (1..6+)
        hs = norm([r35.get('Num_Psns_UR_%s_Total' % s, 0)
                   for s in ['1', '2', '3', '4', '5', '6mo']])
        hs_vals = np.array([1, 2, 3, 4, 5, 6.6])
        # vehicles per dwelling
        veh = norm([r34.get('Num_MVs_per_dweling_%s' % s, 0)
                    for s in ['0_MVs', '1_MVs', '2_MVs', '3_MVs', '4mo_MVs']])
        veh_vals = np.array([0, 1, 2, 3, 4])
        # dwelling structure
        dw = norm([r36.get(c, 0) for _, c in dwell_cols])
        dw_names = [n for n, _ in dwell_cols]

        # employment rate for 15+, from G43
        p15 = float(r43.get('P_15_yrs_over_P', 0) or 0)
        emp = sum(float(r43.get(c, 0) or 0) for c in
                  ['lfs_Emplyed_wrked_full_time_P', 'lfs_Emplyed_wrked_part_time_P',
                   'lfs_Employed_away_from_work_P'])
        ft = float(r43.get('lfs_Emplyed_wrked_full_time_P', 0) or 0)
        emp_rate = emp / p15 if p15 > 0 else 0.55
        ft_share = ft / emp if emp > 0 else 0.6
        # occupation distribution
        occ_tot = []
        for o in OCCUPATIONS:
            v = 0.0
            for pre in ('M', 'F'):
                for band in ('15_19', '20_24', '25_34', '35_44', '45_54', '55_64', '65_74', '75ov'):
                    c = '%s%s_%s' % (pre, band, o)
                    if c in r60.index and pd.notna(r60[c]):
                        v += float(r60[c])
            occ_tot.append(v)
        p_occ = norm(occ_tot)
        # income distribution (persons 15+)
        inc_tot = []
        for b in INCOME_BANDS:
            v = 0.0
            for pre in ('M', 'F'):
                for band in ('15_19_yrs', '20_24_yrs', '25_34_yrs', '35_44_yrs',
                             '45_54_yrs', '55_64_yrs', '65_74_yrs', '75_84_yrs'):
                    c = '%s_%s_income_%s' % (pre, b, band) if b == 'Neg_Nil' else \
                        '%s_%s_%s' % (pre, b, band)
                    if c in r17.index and pd.notna(r17[c]):
                        v += float(r17[c])
            inc_tot.append(v)
        p_inc = norm(inc_tot) if sum(inc_tot) > 0 else norm(np.ones(len(INCOME_BANDS)))

        # jitter radius from zone area so homes are not all stacked on the centroid
        rad = math.sqrt(max(float(z['area_km2']), 1e-4) * 1e6 / math.pi) * 0.6

        made = 0
        while made < pop:
            hid += 1
            bsz = int(rng.choice(len(hs_vals), p=hs))
            # the top category is "6 or more"; give it a small tail
            size = 6 + int(rng.geometric(0.55)) - 1 if bsz == 5 else int(hs_vals[bsz])
            size = max(1, min(size, 10))
            if made + size > pop + 2:
                size = max(1, pop - made)
            nv = int(rng.choice(veh_vals, p=veh))
            dt = dw_names[int(rng.choice(len(dw_names), p=dw))]
            ang = rng.uniform(0, 2 * math.pi)
            rr = rad * math.sqrt(rng.uniform(0, 1))
            hx, hy = float(z['x_mga56']) + rr * math.cos(ang), float(z['y_mga56']) + rr * math.sin(ang)
            hw.writerow([hid, sa1, round(hx, 1), round(hy, 1), z['lon'], z['lat'],
                         size, nv, dt, round(1.0 / sample, 4)])
            stats['households'] += 1
            if nv == 0:
                stats['zero_car_hh'] += 1

            members = []
            for k in range(size):
                pid += 1
                if k == 0:
                    # the household reference person is an adult
                    b = int(rng.choice(len(AGE_BANDS),
                                       p=norm(np.concatenate([np.zeros(3), p_age[3:]]))))
                else:
                    b = int(rng.choice(len(AGE_BANDS), p=p_age))
                lo, hi = AGE_BANDS[b]
                age = int(rng.integers(lo, min(hi, 95) + 1))
                sex = 'M' if rng.random() < p_sex_given_age[b] else 'F'
                if age < 15:
                    est = 'not_in_labour_force'
                elif rng.random() < emp_rate:
                    est = 'employed_full_time' if rng.random() < ft_share else 'employed_part_time'
                else:
                    est = 'unemployed' if rng.random() < 0.06 else 'not_in_labour_force'
                employed = est.startswith('employed')
                occ = OCCUPATIONS[int(rng.choice(len(OCCUPATIONS), p=p_occ))] if employed else ''
                ib = INCOME_BANDS[int(rng.choice(len(INCOME_BANDS), p=p_inc))] if age >= 15 else 'Neg_Nil'
                lic = int(age >= 17 and rng.random() < LICENCE_RATE[b])
                student = ('full_time' if age < 18 else
                           ('full_time' if (18 <= age <= 24 and rng.random() < 0.35) else
                            ('part_time' if rng.random() < 0.04 else 'none')))
                mob = int(rng.random() < (0.05 + 0.25 * max(0, (age - 70)) / 30.0))
                cav = int(lic == 1 and nv > 0)
                pw.writerow([pid, hid, sa1, BAND_LABEL[b], age, sex, est, occ, ib, lic,
                             nv, size, dt, student, mob, cav, round(1.0 / sample, 4)])
                members.append(dict(pid=pid, age=age, band=b, est=est, employed=employed,
                                    student=student, cav=cav, hx=hx, hy=hy))
                stats['persons'] += 1
                if employed:
                    stats['employed'] += 1
                if student == 'full_time':
                    stats['students'] += 1
            made += size


    for f in (hh_f, pp_f):
        f.close()

    stats['seed'] = seed
    stats['sample_fraction'] = sample
    stats['mean_household_size'] = round(stats['persons'] / max(stats['households'], 1), 3)
    stats['pct_zero_car_households'] = round(stats['zero_car_hh'] / max(stats['households'], 1) * 100, 1)
    stats['pct_employed_of_persons'] = round(stats['employed'] / max(stats['persons'], 1) * 100, 1)
    json.dump(stats, open(os.path.join(OUT, 'population', '_population_report.json'), 'w'), indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', type=int, default=20260810)
    ap.add_argument('--sample', type=float, default=1.0)
    ap.add_argument('--max-sa1', type=int, default=None)
    a = ap.parse_args()
    main(a.seed, a.sample, a.max_sa1)
