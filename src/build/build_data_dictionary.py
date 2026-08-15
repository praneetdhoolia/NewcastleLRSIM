#!/usr/bin/env python
"""Emit cities/<city>/docs/reference/DATA_DICTIONARY.md from that city's CSVs."""

# City-relative paths resolve through src/city.py: `data/...` names a
# location inside cities/<city>/, not inside the repository root.
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                  '..', '..', 'src'))
import city as _city  # noqa: E402
import os, csv, glob
ROOT='.'
GROUPS=[
 ('A1/A6 network',_city.path('data/processed/network/*.csv')),
 ('A4/A2 corridor',_city.path('data/processed/corridor/*.csv')),
 ('A3 schedule extras',_city.path('data/processed/schedule_extras/*.csv')),
 ('A5/D1 land use and parking',_city.path('data/processed/landuse/*.csv')),
 ('Zones',_city.path('data/processed/zones/*.csv')),
 ('HTS',_city.path('data/processed/hts/*.csv')),
 ('Observed',_city.path('data/processed/observed/*.csv')),
 ('Validation',_city.path('data/processed/validation/*.csv')),
 ('C1 parameters',_city.path('params/*.csv')),
 ('E1 scenarios',_city.path('scenarios/*.csv')),
 ('B1/B2 demand',_city.path('demand/*/*.csv')),
]
def sniff(p,n=400):
    with open(p,encoding='utf-8',errors='replace') as f:
        r=csv.DictReader(f); rows=[]
        for i,x in enumerate(r):
            rows.append(x)
            if i>=n: break
        return r.fieldnames or [], rows
def kind(vals):
    vals=[v for v in vals if v not in ('',None)]
    if not vals: return 'empty'
    try:
        [float(v) for v in vals]
        return 'int' if all(float(v).is_integer() for v in vals) else 'float'
    except: return 'str'
out=['# Data dictionary','',
     'Auto-generated from the produced files by `src/build/build_data_dictionary.py`.',
     'Column types are inferred from the first 400 rows. Schema letters refer to',
     'Appendix A of the proposal.','']
for title,pat in GROUPS:
    files=sorted(glob.glob(pat))
    if not files: continue
    out.append('## %s'%title); out.append('')
    for p in files:
        base=os.path.basename(p)
        if base.startswith('_'): continue
        cols,rows=sniff(p)
        if not cols: continue
        total=sum(1 for _ in open(p,encoding='utf-8',errors='replace'))-1
        out.append('### `' + p.replace(chr(92), '/') + '`')
        out.append('')
        out.append('%d rows, %d columns'%(total,len(cols)))
        out.append('')
        out.append('| column | type | example | non-empty in sample |')
        out.append('|---|---|---|---|')
        for c in cols:
            vals=[r.get(c,'') for r in rows]
            nz=sum(1 for v in vals if v not in ('',None))
            ex=next((str(v) for v in vals if v not in ('',None)),'')
            if len(ex)>34: ex=ex[:31]+'...'
            out.append('| `%s` | %s | %s | %d/%d |'%(c,kind(vals),ex.replace(chr(124),'/'),nz,len(vals)))
        out.append('')
os.makedirs('docs',exist_ok=True)
open(_city.path('docs','reference','DATA_DICTIONARY.md'),'w',encoding='utf-8').write('\n'.join(out))
print('wrote DATA_DICTIONARY.md (%d lines)'%len(out))
