#!/usr/bin/env python
"""Slice the national/state open datasets down to Greater Newcastle."""
import pandas as pd, os, json
os.makedirs('data/processed/observed',exist_ok=True)
LGAS=['Newcastle','Lake Macquarie','Maitland','Cessnock','Port Stephens']
rep={}

# --- Opal light rail: Newcastle line only ---
d=pd.read_csv('data/raw/opal/lightrail_trips_by_line_cardtype.csv')
n=d[d['Line'].str.contains('Newcastle',case=False,na=False)].copy()
n['Trip']=pd.to_numeric(n['Trip'],errors='coerce')
n.to_csv('data/processed/observed/opal_lr_newcastle_by_month_cardtype.csv',index=False)
rep['lr_lines_available']=sorted(d['Line'].dropna().unique().tolist())
rep['lr_newcastle_months']=[str(n['Year_Month'].iloc[0]),str(n['Year_Month'].iloc[-1])] if len(n) else []
rep['lr_newcastle_rows']=len(n)

# --- Opal LR by tap-on station ---
d=pd.read_csv('data/raw/opal/lightrail_trips_by_tapon_station.csv')
NST=['Newcastle Interchange','Honeysuckle','Civic','Crown Street','Queens Wharf','Newcastle Beach']
m=d[d['Location'].str.contains('|'.join(NST),case=False,na=False)]
m=m[~m['Location'].str.contains('Sydney|Dulwich|Arlington|Randwick|Kingsford',case=False,na=False)]
m.to_csv('data/processed/observed/opal_lr_newcastle_by_stop.csv',index=False)
rep['lr_stop_rows']=len(m); rep['lr_stops_found']=sorted(m['Location'].unique().tolist())

# --- Opal bus by contract region ---
d=pd.read_csv('data/raw/opal/bus_trips_by_contract_region.csv')
regs=sorted(d['Contract_region'].dropna().unique().tolist())
nb=d[d['Contract_region'].str.contains('Newcastle|Hunter',case=False,na=False)]
nb.to_csv('data/processed/observed/opal_bus_newcastle_hunter.csv',index=False)
rep['bus_regions_newcastle']=sorted(nb['Contract_region'].unique().tolist())
rep['bus_all_regions']=regs

# --- Station entries/exits (Hunter line + Newcastle area) ---
STN=['Newcastle Interchange','Wickham','Hamilton','Broadmeadow','Adamstown','Cardiff','Cockle Creek',
     'Teralba','Booragul','Fassifern','Warabrook','Sandgate','Waratah','Kotara','Thornton','Maitland',
     'East Maitland','Victoria Street','Metford','Tarro','Hexham','Morisset','Awaba','Dora Creek','Wyee']
d=pd.read_csv('data/raw/opal/station_entries_exits_monthly.csv')
pat='|'.join(STN)
s=d[d['Station'].str.contains(pat,case=False,na=False)]
s.to_csv('data/processed/observed/station_entries_exits_newcastle.csv',index=False)
rep['station_rows']=len(s); rep['stations_found']=sorted(s['Station'].str.strip().unique().tolist())

# --- Road traffic counts: Newcastle-area stations ---
d=pd.read_csv('data/raw/counts/rms_station_reference.csv',low_memory=False)
st=d[d['lga'].isin(LGAS)].copy()
st.to_csv('data/processed/observed/traffic_count_stations_newcastle.csv',index=False)
rep['count_stations']=len(st)
rep['count_stations_by_lga']=st['lga'].value_counts().to_dict()
ids=set(st['station_key'].astype(str))
# yearly AADT for those stations
y=pd.read_csv('data/raw/counts/rms_yearly_summary.csv',low_memory=False)
rep['yearly_cols']=list(y.columns)
kcol='station_key' if 'station_key' in y.columns else y.columns[0]
yn=y[y[kcol].astype(str).isin(ids)]
yn.to_csv('data/processed/observed/traffic_aadt_newcastle.csv',index=False)
rep['aadt_rows']=len(yn)
if 'year' in yn.columns: rep['aadt_years']=[int(yn['year'].min()),int(yn['year'].max())]
json.dump(rep,open('data/processed/observed/_slice_report.json','w'),indent=2,default=str)
print(json.dumps(rep,indent=2,default=str)[:4000])
