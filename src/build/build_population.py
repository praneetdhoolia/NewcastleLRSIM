#!/usr/bin/env python
"""Layer B1 - synthetic population (households and persons).

Method
------
Households are drawn per SA1 to match the census marginals for household size
(G35), motor vehicles (G34) and dwelling structure (G36). Persons are then drawn
to match the SA1 age-sex distribution (G04, including the grouped 80-99
columns), the age- and sex-conditional labour force status (G46, per SA1 with a
core-region fallback for empty cells), and the age-conditional education
attendance (G01). Licence holding, income band and occupation follow.

Daily activity chains are **not** built here. They were until P3, as layer B2 in
this same pass; `src/build/build_activity_chains.py` now owns them, builds them
as home-anchored tours rather than a shuffled activity list, and produces one
file per day type. See DECISIONS.md 9.

Everything is seeded. Re-running with the same seed reproduces the population
exactly; the seed is recorded in the scenario configuration (schema E1).
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
import numpy as np
import pandas as pd

# Model inputs come from cities/<city>/registry/, not from literals here. Every
# value below carries its units, provenance and either a sweep, a held-fixed rule
# or a derived-from identity there. See DECISIONS.md 15.
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import registry as _registry  # noqa: E402
CFG = _registry.load()

CEN = _city.path('data/processed/census')
LU = _city.path('data/processed/landuse')
OUT = _city.path('demand')
os.makedirs(os.path.join(OUT, 'population'), exist_ok=True)
os.makedirs(os.path.join(OUT, 'plans'), exist_ok=True)

AGE_BANDS = CFG.get('B.population.age_bands')
BAND_LABEL = ['0-4', '5-11', '12-17', '18-24', '25-34', '35-44',
              '45-54', '55-64', '65-74', '75-84', '85+']
# NSW driver-licence holding rate by age band (assumed; ABS/TfNSW-typical)
LICENCE_RATE = CFG.get('B.population.licence_rate_by_age_band')
# Of 18+ education attendees (G01, observed), the share studying full time -
# the ones who draw a mandatory HE tour. Assumed and swept: the table that
# would measure it (G15) is not in the package (age-structure dossier 5).
TERTIARY_FT = CFG.get('B.population.tertiary_ft_share')
OCCUPATIONS = ['Managers', 'Professionals', 'TechnicTrades_Wrs', 'CommunPersnlSvc_W',
               'ClericalAdminis_W', 'Sales_W', 'Mach_oper_drivers', 'Labourers']
INCOME_BANDS = ['Neg_Nil', '1_149', '150_299', '300_399', '400_499', '500_649',
                '650_799', '800_999', '1000_1249', '1250_1499', '1500_1749',
                '1750_1999', '2000_2999', '3000_more']


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
    g01 = rd('census2021_G01_SA1.csv')
    g34 = rd('census2021_G34_SA1.csv')
    g35 = rd('census2021_G35_SA1.csv')
    g36 = rd('census2021_G36_SA1.csv')
    g43 = rd('census2021_G43_SA1.csv')
    # G46 is labour force status BY AGE AND SEX: G46A carries the male columns,
    # G46B the female and persons ones. Both are needed - employment is drawn
    # per (SA1, sex, age band), not from one flat 15+ rate.
    g46 = rd('census2021_G46A_SA1.csv').merge(
        rd('census2021_G46B_SA1.csv'), on=[key, 'zone_tier'], suffixes=('', '_b'))
    g17 = rd('census2021_G17A_SA1.csv').merge(
        rd('census2021_G17B_SA1.csv'), on=[key, 'zone_tier'], suffixes=('', '_b'))
    g60 = rd('census2021_G60A_SA1.csv').merge(
        rd('census2021_G60B_SA1.csv'), on=[key, 'zone_tier'], suffixes=('', '_b'))
    for d in (g01, g04, g34, g35, g36, g43, g46, g17, g60):
        d[key] = d[key].astype(str)
    return dict(key=key, g01=g01, g04=g04, g34=g34, g35=g35, g36=g36, g43=g43,
                g46=g46, g17=g17, g60=g60)


# ABS age bands as G46/G01 publish them. These are the TABLES' banding, read
# off their own column names, not a modelling choice - the model's own banding
# stays B.population.age_bands.
ABS_LF_BANDS = [('15_19', 15, 19), ('20_24', 20, 24), ('25_34', 25, 34),
                ('35_44', 35, 44), ('45_54', 45, 54), ('55_64', 55, 64),
                ('65_74', 65, 74), ('75_84', 75, 84), ('85ov', 85, 200)]
# G01 education-attendance age groups, with the two column spellings the
# DataPack uses ('educ_inst' up to 14, 'edu_inst' from 15).
ABS_EDU_GROUPS = [('0_4', 0, 4, 'Age_psns_att_educ_inst_0_4_P', 'Age_0_4_yr_P'),
                  ('5_14', 5, 14, 'Age_psns_att_educ_inst_5_14_P', 'Age_5_14_yr_P'),
                  ('15_19', 15, 19, 'Age_psns_att_edu_inst_15_19_P', 'Age_15_19_yr_P'),
                  ('20_24', 20, 24, 'Age_psns_att_edu_inst_20_24_P', 'Age_20_24_yr_P')]
ABS_EDU_25OV_ATT = 'Age_psns_att_edu_inst_25_ov_P'
ABS_EDU_25OV_POP = ['Age_25_34_yr_P', 'Age_35_44_yr_P', 'Age_45_54_yr_P',
                    'Age_55_64_yr_P', 'Age_65_74_yr_P', 'Age_75_84_yr_P',
                    'Age_85ov_P']


def abs_lf_band(age):
    for name, lo, hi in ABS_LF_BANDS:
        if lo <= age <= hi:
            return name
    return None


def _cell(row, col):
    v = row.get(col, 0)
    try:
        return float(v) if pd.notna(v) else 0.0
    except (TypeError, ValueError):
        return 0.0


def lf_rates_from(row, sex, band):
    """(employment, FT-of-employed, unemployed-of-non-employed) for one G46
    row slice, or None where the cell holds nobody to measure.

    The employment base is persons with a STATED labour force status
    (Tot_LF + Not_in_LF); the census not-stated residual is excluded from the
    denominator rather than counted as not-working.
    """
    emp = _cell(row, '%s_Tot_Emp_%s' % (sex, band))
    lf = _cell(row, '%s_Tot_LF_%s' % (sex, band))
    nilf = _cell(row, '%s_Not_in_LF_%s' % (sex, band))
    stated = lf + nilf
    if stated <= 0:
        return None
    ft = _cell(row, '%s_Emp_FullT_%s' % (sex, band))
    pt = _cell(row, '%s_Emp_PartT_%s' % (sex, band))
    unemp = _cell(row, '%s_Tot_Unemp_%s' % (sex, band))
    non_emp = unemp + nilf
    return (min(emp / stated, 1.0),
            (ft / (ft + pt)) if (ft + pt) > 0 else None,
            (unemp / non_emp) if non_emp > 0 else 0.0)


def region_lf_rates(g46):
    """Core-region (sex, band) labour-force rates - the fallback for the 7.4%
    of SA1 cells that hold nobody of that sex and band."""
    core = g46[g46.zone_tier == 'core']
    sums = core.sum(numeric_only=True)
    out = {}
    for sex in ('M', 'F'):
        for band, _, _ in ABS_LF_BANDS:
            r = lf_rates_from(sums, sex, band)
            if r is None:
                r = (0.0, 0.0, 0.0)
            ft = r[1] if r[1] is not None else 0.0
            out[(sex, band)] = (r[0], ft, r[2])
    return out


def region_edu_rates(g01):
    """Core-region attendance rate per G01 age group - the SA1 fallback."""
    core = g01[g01.zone_tier == 'core']
    sums = core.sum(numeric_only=True)
    out = {}
    for name, _, _, att_col, pop_col in ABS_EDU_GROUPS:
        pop = _cell(sums, pop_col)
        out[name] = min(_cell(sums, att_col) / pop, 1.0) if pop > 0 else 0.0
    pop25 = sum(_cell(sums, c) for c in ABS_EDU_25OV_POP)
    out['25_ov'] = min(_cell(sums, ABS_EDU_25OV_ATT) / pop25, 1.0) if pop25 > 0 else 0.0
    return out


def sa1_lf_rates(r46, fallback):
    """(sex, band) -> rates for one SA1, falling back to the region where the
    SA1's own cell holds nobody of that sex and band."""
    out = {}
    for sex in ('M', 'F'):
        for band, _, _ in ABS_LF_BANDS:
            r = lf_rates_from(r46, sex, band)
            if r is None:
                out[(sex, band)] = fallback[(sex, band)]
            else:
                ft = r[1] if r[1] is not None else fallback[(sex, band)][1]
                out[(sex, band)] = (r[0], ft, r[2])
    return out


def sa1_edu_rates(r01, fallback):
    """G01 age group -> attendance rate for one SA1, region fallback."""
    out = {}
    for name, _, _, att_col, pop_col in ABS_EDU_GROUPS:
        pop = _cell(r01, pop_col)
        out[name] = min(_cell(r01, att_col) / pop, 1.0) if pop > 0 \
            else fallback[name]
    pop25 = sum(_cell(r01, c) for c in ABS_EDU_25OV_POP)
    out['25_ov'] = min(_cell(r01, ABS_EDU_25OV_ATT) / pop25, 1.0) if pop25 > 0 \
        else fallback['25_ov']
    return out


def edu_group_of(age):
    for name, lo, hi, _, _ in ABS_EDU_GROUPS:
        if lo <= age <= hi:
            return name
    return '25_ov'


# G04 publishes single-year columns only to age 79; 80-99 exist solely as the
# grouped columns below. The old loop read `Age_yr_<N>` for every year and so
# silently dropped every person aged 80-99: the built population held 186
# persons 85+ against a census 15,151, and their probability mass was
# redistributed across the younger bands (age-structure dossier, D1).
G04_GROUPED = [(80, 84, 'Age_yr_80_84_%s'), (85, 89, 'Age_yr_85_89_%s'),
               (90, 94, 'Age_yr_90_94_%s'), (95, 99, 'Age_yr_95_99_%s')]


def age_sex_dist(row):
    """Collapse G04 age columns into the model's age bands, by sex.

    Single years to 79, the grouped 80-99 columns apportioned to bands by
    year overlap (uniform within a group), and the 100+ column to whichever
    band reaches it.
    """
    out = np.zeros((len(AGE_BANDS), 2))
    for bi, (lo, hi) in enumerate(AGE_BANDS):
        for a in range(lo, min(hi, 79) + 1):
            for si, sx in enumerate(('M', 'F')):
                c = 'Age_yr_%d_%s' % (a, sx)
                if c in row:
                    v = row[c]
                    if pd.notna(v):
                        out[bi, si] += float(v)
        for glo, ghi, pat in G04_GROUPED:
            overlap = max(0, min(hi, ghi) - max(lo, glo) + 1)
            if overlap <= 0:
                continue
            frac = overlap / float(ghi - glo + 1)
            for si, sx in enumerate(('M', 'F')):
                c = pat % sx
                if c in row and pd.notna(row[c]):
                    out[bi, si] += frac * float(row[c])
        if hi >= 100:
            for c, si in (('Age_yr_100_yr_over_M', 0), ('Age_yr_100_yr_over_F', 1)):
                if c in row and pd.notna(row[c]):
                    out[bi, si] += float(row[c])
    return out


def main(seed=None, sample=None, max_sa1=None):
    # Resolved, not defaulted. The seed is this project's headline determinism
    # claim and it existed in nine copies; the build sample is ONE, always, and
    # is a different quantity from the run-time RUN.sample.fraction.
    seed = CFG.get('B.seed.master') if seed is None else seed
    sample = CFG.get('B.population.build_sample_share') if sample is None else sample
    rng = np.random.default_rng(seed)
    M = load_marginals()
    key = M['key']
    zones = pd.read_csv(os.path.join(LU, 'D1_zone_attractions_SA1.csv'),
                        dtype={'SA1_CODE21': str})
    core = zones[zones.zone_tier == 'core'].reset_index(drop=True)
    if max_sa1:
        core = core.head(max_sa1)
    idx = {k: M[k].set_index(key)
           for k in ('g01', 'g04', 'g34', 'g35', 'g36', 'g46', 'g17', 'g60')}
    # core-region fallbacks for SA1 cells that hold nobody of a sex and band
    region_lf = region_lf_rates(M['g46'])
    region_edu = region_edu_rates(M['g01'])

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
    # ABS-band accumulators so the report states the realised age-conditional
    # rates beside the census they were drawn from: [persons, employed, FT students]
    bands = {}

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
            r01 = idx['g01'].loc[sa1]
            r04 = idx['g04'].loc[sa1]
            r34 = idx['g34'].loc[sa1]
            r35 = idx['g35'].loc[sa1]
            r36 = idx['g36'].loc[sa1]
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

        # labour force status per (sex, ABS age band) from this SA1's own G46
        # row, and education attendance per age group from its G01 row - the
        # region-wide rates fill the cells that hold nobody
        lf = sa1_lf_rates(r46, region_lf)
        edu = sa1_edu_rates(r01, region_edu)
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
                else:
                    er, fts, us = lf[(sex, abs_lf_band(age))]
                    if rng.random() < er:
                        est = ('employed_full_time' if rng.random() < fts
                               else 'employed_part_time')
                    else:
                        est = ('unemployed' if rng.random() < us
                               else 'not_in_labour_force')
                employed = est.startswith('employed')
                occ = OCCUPATIONS[int(rng.choice(len(OCCUPATIONS), p=p_occ))] if employed else ''
                ib = INCOME_BANDS[int(rng.choice(len(INCOME_BANDS), p=p_inc))] if age >= 15 else 'Neg_Nil'
                lic = int(age >= 17 and rng.random() < LICENCE_RATE[b])
                # attendance is observed (G01); how an 18+ attendee splits
                # full/part-time is not held and is declared and swept
                if rng.random() < edu[edu_group_of(age)]:
                    if age < 18:
                        student = 'full_time'
                    else:
                        student = ('full_time'
                                   if rng.random() < TERTIARY_FT[
                                       '18_24' if age <= 24 else '25_ov']
                                   else 'part_time')
                else:
                    student = 'none'
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
                bk = abs_lf_band(age) or ('0_4' if age < 5 else '5_14')
                acc = bands.setdefault(bk, [0, 0, 0])
                acc[0] += 1
                acc[1] += int(employed)
                acc[2] += int(student == 'full_time')
            made += size


    for f in (hh_f, pp_f):
        f.close()

    stats['seed'] = seed
    stats['sample_fraction'] = sample
    stats['mean_household_size'] = round(stats['persons'] / max(stats['households'], 1), 3)
    stats['pct_zero_car_households'] = round(stats['zero_car_hh'] / max(stats['households'], 1) * 100, 1)
    stats['pct_employed_of_persons'] = round(stats['employed'] / max(stats['persons'], 1) * 100, 1)
    stats['by_abs_age_band'] = {
        k: dict(persons=n, employed_pct=round(100.0 * e / max(n, 1), 1),
                student_full_time_pct=round(100.0 * s / max(n, 1), 1))
        for k, (n, e, s) in sorted(bands.items())}
    json.dump(stats, open(os.path.join(OUT, 'population', '_population_report.json'), 'w'), indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', type=int, help='override B.seed.master')
    ap.add_argument('--sample', type=float,
                    help='override B.population.build_sample_share')
    ap.add_argument('--max-sa1', type=int, default=None)
    a = ap.parse_args()
    main(a.seed, a.sample, a.max_sa1)
