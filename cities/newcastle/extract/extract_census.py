#!/usr/bin/env python
"""Extract the 2021 Census tables the model needs, clipped to the study area.

Residence side (GCP, SA1) -> synthetic population marginals (schema B1) and the
observed method-of-travel-to-work mode split used as a calibration target.

Workplace side (WPP, POW SA2) -> jobs by industry and occupation for the
accessibility measures (A4) and the destination-side mode split.
"""

# City-relative paths resolve through src/city.py: `data/...` names a
# location inside cities/<city>/, not inside the repository root.
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                  '..', '..', '..', 'src'))
import city as _city  # noqa: E402
import os
import io
import json
import zipfile
import pandas as pd

RAW = _city.path('data/raw/census')
OUT = _city.path('data/processed/census')
ZON = _city.path('data/processed/zones')
os.makedirs(OUT, exist_ok=True)

GCP_TABLES = {
    'G01': 'selected person characteristics by sex',
    'G02': 'selected medians and averages',
    'G04A': 'age by sex (part A)', 'G04B': 'age by sex (part B)',
    'G17A': 'personal income weekly (part A)', 'G17B': 'personal income weekly (part B)',
    'G17C': 'personal income weekly (part C)',
    'G34': 'number of motor vehicles by dwelling',
    'G35': 'household composition by persons usually resident',
    'G36': 'dwelling structure',
    'G43': 'labour force education and migration characteristics by sex',
    'G46A': 'labour force status by age by sex (part A)',
    'G46B': 'labour force status by age by sex (part B)',
    'G54A': 'industry of employment by age by sex (part A)',
    'G54B': 'industry of employment by age by sex (part B)',
    'G60A': 'occupation by age by sex (part A)',
    'G60B': 'occupation by age by sex (part B)',
    'G62': 'method of travel to work by sex',
}
WPP_TABLES = {
    'W01A': 'labour force status by age by sex (POW)',
    'W09A': 'industry of employment by sex (POW, part A)',
    'W09B': 'industry of employment by sex (POW, part B)',
    'W13': 'occupation by sex (POW)',
    'W21A': 'method of travel to work by occupation (POW, part A)',
    'W21B': 'method of travel to work by occupation (POW, part B)',
    'W22A': 'method of travel to work by age by sex (POW, part A)',
    'W22B': 'method of travel to work by age by sex (POW, part B)',
}


def load_zip_csv(zpath, table, suffix):
    z = zipfile.ZipFile(zpath)
    hits = [n for n in z.namelist()
            if n.endswith('.csv') and ('_%s_' % table) in n.split('/')[-1] and suffix in n]
    if not hits:
        return None
    return pd.read_csv(io.BytesIO(z.read(hits[0])), low_memory=False)


sa1 = pd.read_csv(os.path.join(ZON, 'zones_SA1.csv'), dtype={'SA1_CODE21': str})
sa2 = pd.read_csv(os.path.join(ZON, 'zones_SA2.csv'), dtype={'SA2_CODE21': str})
sa1_ids = set(sa1['SA1_CODE21'].astype(str))
sa2_ids = set(sa2['SA2_CODE21'].astype(str))
tier1 = dict(zip(sa1['SA1_CODE21'].astype(str), sa1['zone_tier']))
tier2 = dict(zip(sa2['SA2_CODE21'].astype(str), sa2['zone_tier']))

report = {'gcp_sa1': {}, 'wpp_sa2': {}}
gcp = os.path.join(RAW, '2021_GCP_SA1_for_NSW_short-header.zip')
wpp = os.path.join(RAW, '2021_WPP_SA2_for_NSW_short-header.zip')

for t, desc in GCP_TABLES.items():
    d = load_zip_csv(gcp, t, 'SA1')
    if d is None:
        print('MISS GCP', t)
        continue
    key = [c for c in d.columns if c.upper().startswith('SA1_CODE')][0]
    d[key] = d[key].astype(str)
    s = d[d[key].isin(sa1_ids)].copy()
    s.insert(1, 'zone_tier', s[key].map(tier1))
    s.to_csv(os.path.join(OUT, 'census2021_%s_SA1.csv' % t), index=False)
    report['gcp_sa1'][t] = {'desc': desc, 'rows': len(s), 'cols': len(s.columns)}
    print('GCP %-5s %-58s rows=%5d cols=%4d' % (t, desc[:58], len(s), len(s.columns)), flush=True)

for t, desc in WPP_TABLES.items():
    d = load_zip_csv(wpp, t, 'POW_SA2')
    if d is None:
        print('MISS WPP', t)
        continue
    key = [c for c in d.columns if 'SA2_CODE' in c.upper() or c.upper().startswith('POW')][0]
    d[key] = d[key].astype(str).str.replace('POW', '', regex=False)
    s = d[d[key].isin(sa2_ids)].copy()
    s.insert(1, 'zone_tier', s[key].map(tier2))
    s.to_csv(os.path.join(OUT, 'census2021_%s_POW_SA2.csv' % t), index=False)
    report['wpp_sa2'][t] = {'desc': desc, 'rows': len(s), 'cols': len(s.columns)}
    print('WPP %-5s %-58s rows=%5d cols=%4d' % (t, desc[:58], len(s), len(s.columns)), flush=True)

# ---- headline summary: population, dwellings, jobs, observed JTW mode split ----
summary = {}
g01 = pd.read_csv(os.path.join(OUT, 'census2021_G01_SA1.csv'), dtype={'SA1_CODE_2021': str}, low_memory=False)
pcol = [c for c in g01.columns if c.lower() in ('tot_p_p', 'total_persons_p')]
if pcol:
    summary['population_2021'] = {
        'core': int(g01.loc[g01['zone_tier'] == 'core', pcol[0]].sum()),
        'external': int(g01.loc[g01['zone_tier'] == 'external', pcol[0]].sum())}

g36 = pd.read_csv(os.path.join(OUT, 'census2021_G36_SA1.csv'), low_memory=False)
dcol = [c for c in g36.columns if 'Total' in c and 'dwellings' in c.lower()]
if not dcol:
    dcol = [c for c in g36.columns if c.lower().startswith('total') or c.lower().endswith('_total')]
if dcol:
    summary['dwellings_2021_col'] = dcol[0]
    summary['dwellings_2021'] = {
        'core': int(pd.to_numeric(g36.loc[g36['zone_tier'] == 'core', dcol[0]], errors='coerce').sum()),
        'external': int(pd.to_numeric(g36.loc[g36['zone_tier'] == 'external', dcol[0]], errors='coerce').sum())}

g62 = pd.read_csv(os.path.join(OUT, 'census2021_G62_SA1.csv'), low_memory=False)
core62 = g62[g62['zone_tier'] == 'core']
tot = {c: int(pd.to_numeric(core62[c], errors='coerce').sum())
       for c in g62.columns if c.endswith('_P') and 'Tot' not in c}
summary['jtw_mode_core_2021_top20'] = dict(sorted(tot.items(), key=lambda kv: -kv[1])[:20])

json.dump({'tables': report, 'summary': summary},
          open(os.path.join(OUT, '_census_report.json'), 'w'), indent=2)
print('\n', json.dumps(summary, indent=2)[:3000])
