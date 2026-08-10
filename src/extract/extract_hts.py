#!/usr/bin/env python
"""Extract NSW Household Travel Survey estimates for the study area LGAs.

These are the observed calibration targets for mode share and the empirical
basis for trip rates and activity durations in the synthetic demand. Both the
2009/10-2019/20 and 2020/21-2024/25 releases are read so that pre-pandemic and
current behaviour can be separated - proposal section 4.1 lists the pandemic as
one of the six confounded changes, so the model must be able to see both.
"""
import os
import json
import pandas as pd

RAW = 'data/raw/hts'
OUT = 'data/processed/hts'
os.makedirs(OUT, exist_ok=True)

LGAS = ['Newcastle', 'Lake Macquarie', 'Maitland', 'Cessnock', 'Port Stephens']
SA3S = ['Newcastle', 'Lake Macquarie - East', 'Lake Macquarie - West',
        'Maitland', 'Port Stephens', 'Lower Hunter']

FILES = [
    ('lga', 'hts_by_lga_2020-21_to_2024-25.xlsx', 'HH_LGA_NAME', LGAS),
    ('lga', 'hts_by_lga_2009-10_to_2019-20.xlsx', 'HH_LGA_NAME', LGAS),
    ('sa3', 'hts_by_sa3_2020-21_to_2024-25.xlsx', None, SA3S),
    ('sa3', 'hts_by_sa3_2009-10_to_2019-20.xlsx', None, SA3S),
]


def read_sheet(path, sheet):
    """Column names differ in case and slightly in wording between the two
    HTS releases; normalise to the newer upper-case convention."""
    d = pd.read_excel(path, sheet_name=sheet, header=0)
    d.columns = [str(c).strip().upper() for c in d.columns]
    d = d.rename(columns={'JOURNEYS_BY_PURPOSE': 'JOURNEYS_BY_MODE'})
    return d


frames = {'mode': [], 'purpose': []}
for geo, fn, keycol, wanted in FILES:
    p = os.path.join(RAW, fn)
    if not os.path.exists(p):
        print('missing', fn)
        continue
    xl = pd.ExcelFile(p)
    for sheet in xl.sheet_names:
        low = sheet.lower()
        if 'mode' in low:
            kind = 'mode'
        elif 'purpose' in low:
            kind = 'purpose'
        else:
            continue
        d = read_sheet(p, sheet)
        namecol = [c for c in d.columns if c.endswith('_NAME')]
        if not namecol:
            continue
        nc = namecol[0]
        s = d[d[nc].astype(str).str.strip().isin(wanted)].copy()
        if s.empty:
            continue
        s.insert(0, 'geography', geo)
        s.insert(1, 'source_file', fn)
        s = s.rename(columns={nc: 'area_name'})
        frames[kind].append(s)
        print('%-42s %-12s %-8s rows=%d' % (fn, sheet, geo, len(s)), flush=True)

report = {}
for kind, fl in frames.items():
    if not fl:
        continue
    d = pd.concat(fl, ignore_index=True)
    d.to_csv(os.path.join(OUT, 'hts_%s_newcastle.csv' % kind), index=False)
    report['%s_rows' % kind] = len(d)
    report['%s_years' % kind] = sorted(d['FINANCIAL_YEAR'].astype(str).unique().tolist())

# ---- headline: Newcastle LGA mode share, latest and pre-pandemic ----
m = pd.read_csv(os.path.join(OUT, 'hts_mode_newcastle.csv'))
m['MODE_SHARE'] = pd.to_numeric(m['MODE_SHARE'], errors='coerce')
m['TRIPS_BY_MODE'] = pd.to_numeric(m['TRIPS_BY_MODE'], errors='coerce')
sel = m[m['area_name'].str.strip() == 'Newcastle']
tbl = {}
for yr in ['2018/19', '2024/25']:
    y = sel[sel['FINANCIAL_YEAR'].astype(str) == yr]
    if len(y):
        tot = y['TRIPS_BY_MODE'].sum()
        tbl[yr] = {str(r['TRAVEL_MODE']).strip():
                   {'trips': int(r['TRIPS_BY_MODE']) if pd.notna(r['TRIPS_BY_MODE']) else None,
                    'pct_of_trips': round(float(r['TRIPS_BY_MODE']) / tot * 100, 2) if tot else None}
                   for _, r in y.iterrows()}
report['newcastle_lga_mode_split'] = tbl

p = pd.read_csv(os.path.join(OUT, 'hts_purpose_newcastle.csv'))
p['JOURNEYS_BY_MODE'] = pd.to_numeric(p['JOURNEYS_BY_MODE'], errors='coerce')
psel = p[(p['area_name'].str.strip() == 'Newcastle')]
tblp = {}
for yr in ['2018/19', '2024/25']:
    y = psel[psel['FINANCIAL_YEAR'].astype(str) == yr]
    if len(y):
        tot = y['JOURNEYS_BY_MODE'].sum()
        tblp[yr] = {str(r['TRAVEL_PURPOSE']).strip():
                    {'journeys': int(r['JOURNEYS_BY_MODE']) if pd.notna(r['JOURNEYS_BY_MODE']) else None,
                     'pct': round(float(r['JOURNEYS_BY_MODE']) / tot * 100, 2) if tot else None,
                     'avg_distance_km': r.get('JOURNEY_AVG_DISTANCE'),
                     'avg_time_min': r.get('JOURNEY_AVG_TIME')}
                    for _, r in y.iterrows()}
report['newcastle_lga_purpose_split'] = tblp

json.dump(report, open(os.path.join(OUT, '_hts_report.json'), 'w'), indent=2, default=str)
print('\n' + json.dumps(report, indent=2, default=str)[:4000])
