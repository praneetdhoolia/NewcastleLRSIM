#!/usr/bin/env python
"""Emit docs/DATA_DICTIONARY.md by introspecting every produced CSV."""
import os,csv,json,glob
ROOT='.'
GROUPS=[
 ('A1/A6 network','data/processed/network/*.csv'),
 ('A4/A2 corridor','data/processed/corridor/*.csv'),
 ('A3 schedule extras','data/processed/schedule_extras/*.csv'),
 ('A5/D1 land use and parking','data/processed/landuse/*.csv'),
 ('Zones','data/processed/zones/*.csv'),
 ('HTS','data/processed/hts/*.csv'),
 ('Observed','data/processed/observed/*.csv'),
 ('Validation','data/processed/validation/*.csv'),
 ('C1 parameters','params/*.csv'),
 ('E1 scenarios','scenarios/*.csv'),
 ('B1/B2 demand','demand/*/*.csv'),
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
open('docs/DATA_DICTIONARY.md','w',encoding='utf-8').write('\n'.join(out))
print('wrote docs/DATA_DICTIONARY.md (%d lines)'%len(out))
