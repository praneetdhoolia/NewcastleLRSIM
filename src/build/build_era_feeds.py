#!/usr/bin/env python
"""Build era-variant GTFS feeds for Greater Newcastle, normalised to day types.

Each source feed is clipped to the study bbox, a representative service day of
each type (WEEKDAY/SAT/SUN) is selected from that feed's own validity window,
and all trips are re-stamped onto a common synthetic calendar so that every era
feed is directly comparable and consumable by pt2matsim.
"""
import sys,os,json,datetime,collections
sys.path.insert(0,os.path.dirname(__file__))
from gtfs_tools import read_feed,write_feed,clip,prefix_feed,merge,active_services,FILES

RAW='schedules/raw'; OUT='schedules'
ERAS={
 'era2_2016_rail_truncated':{'src':[('complete','complete.zip')],'note':'Heavy rail truncated at Hamilton/Wickham; pre-franchise State Transit Newcastle buses; no LR'},
 'era3_2018_keolis_interchange':{'src':[('nisc001','nisc001.zip'),('sydneytrains','sydneytrains.zip'),('nswtrains','nswtrains.zip')],'note':'Keolis Downer franchise; Newcastle Interchange open; no LR'},
 'era4_2019_lr_open':{'src':[('nisc001','nisc001.zip'),('sydneytrains','sydneytrains.zip'),('nswtrains','nswtrains.zip'),('lightrail','lightrail.zip')],'note':'LR open; LR feed epoch Feb-2020 (earliest archived)'},
 'base2026':{'src':[('nisc001','nisc001.zip'),('lightrail','lightrail.zip'),('regionbuses','regionbuses.zip'),('sydneytrains','sydneytrains.zip'),('nswtrains','nswtrains.zip')],'note':'Base year 2026 as-built network'},
}
DAYTYPES={'WEEKDAY':2,'SAT':5,'SUN':6}   # target weekday index

def feed_window(feed):
    ds=[c['start_date'] for c in feed.get('calendar',[]) if c.get('start_date')]
    de=[c['end_date'] for c in feed.get('calendar',[]) if c.get('end_date')]
    dd=[c['date'] for c in feed.get('calendar_dates',[])]
    lo=min(ds+dd) if (ds or dd) else None; hi=max(de+dd) if (de or dd) else None
    return lo,hi

def pick_date(feed,target_dow):
    """Best service date of the given weekday: the one with most active services."""
    lo,hi=feed_window(feed)
    if not lo: return None
    d0=datetime.datetime.strptime(lo,'%Y%m%d').date()
    d1=datetime.datetime.strptime(hi,'%Y%m%d').date()
    # search a bounded window from the start of validity
    d1=min(d1,d0+datetime.timedelta(days=120))
    best=(None,-1)
    d=d0
    while d<=d1:
        if d.weekday()==target_dow:
            n=len(active_services(feed,d.strftime('%Y%m%d')))
            if n>best[1]: best=(d.strftime('%Y%m%d'),n)
        d+=datetime.timedelta(days=1)
    return best[0]

def day_slice(feed,date,label):
    """Extract one service day and stamp it as a day type.

    A trip that runs on several day types keeps the same trip_id in the source
    feed, so merging the WEEKDAY/SAT/SUN slices would emit that trip's
    stop_times two or three times under one id. Trip ids are therefore
    namespaced by day type, which keeps every (trip, day type) pair distinct.
    """
    act=active_services(feed,date)
    keep={t['trip_id'] for t in feed.get('trips',[]) if t['service_id'] in act}
    ren=lambda tid: '%s.%s'%(label,tid)
    trips=[dict(t,service_id=label,trip_id=ren(t['trip_id']))
           for t in feed.get('trips',[]) if t['trip_id'] in keep]
    out=dict(feed)
    out['trips']=trips
    out['stop_times']=[dict(r,trip_id=ren(r['trip_id']))
                       for r in feed.get('stop_times',[]) if r['trip_id'] in keep]
    out['frequencies']=[dict(r,trip_id=ren(r['trip_id']))
                        for r in feed.get('frequencies',[]) if r['trip_id'] in keep]
    out['calendar']=[]; out['calendar_dates']=[]
    return out

summary={}
for era,cfg in ERAS.items():
    parts=[]; meta={'note':cfg['note'],'sources':{}}
    for label,fn in cfg['src']:
        p=os.path.join(RAW,era,fn)
        if not os.path.exists(p): print('MISSING',p); continue
        print(f'[{era}] reading {label} ...',flush=True)
        f=read_feed(p)
        f=clip(f)
        if not f.get('trips'): print(f'   {label}: no trips in study area'); continue
        chosen={}
        slices=[]
        for dt,dow in DAYTYPES.items():
            d=pick_date(f,dow)
            if not d: continue
            s=day_slice(f,d,dt)
            if s['trips']: chosen[dt]={'date':d,'trips':len(s['trips'])}; slices.append(s)
        if not slices: continue
        m=merge(slices)
        # dedupe non-trip tables
        for t in ['stops','routes','shapes','agency','transfers']:
            seen=set(); rows=[]
            keyf={'stops':'stop_id','routes':'route_id','agency':'agency_id'}.get(t)
            for r in m.get(t,[]):
                k=r.get(keyf) if keyf else tuple(sorted(r.items()))
                if k in seen: continue
                seen.add(k); rows.append(r)
            m[t]=rows
        m['calendar']=[{'service_id':dt,'monday':'1' if dt=='WEEKDAY' else '0','tuesday':'1' if dt=='WEEKDAY' else '0',
                        'wednesday':'1' if dt=='WEEKDAY' else '0','thursday':'1' if dt=='WEEKDAY' else '0',
                        'friday':'1' if dt=='WEEKDAY' else '0','saturday':'1' if dt=='SAT' else '0',
                        'sunday':'1' if dt=='SUN' else '0','start_date':'20260101','end_date':'20261231'}
                       for dt in chosen]
        parts.append(prefix_feed(m,label))
        meta['sources'][label]={'file':fn,'daytypes':chosen,
                                'stops':len(m['stops']),'routes':len(m['routes']),'trips':len(m['trips'])}
        print(f'   {label}: routes={len(m["routes"])} stops={len(m["stops"])} trips={len(m["trips"])} {chosen}')
    if not parts: continue
    M=merge(parts)
    # single shared calendar
    dts=sorted({t['service_id'].split(':')[-1] for t in M['trips']})
    for t in M['trips']: t['service_id']=t['service_id'].split(':')[-1]
    M['calendar']=[{'service_id':dt,'monday':'1' if dt=='WEEKDAY' else '0','tuesday':'1' if dt=='WEEKDAY' else '0',
                    'wednesday':'1' if dt=='WEEKDAY' else '0','thursday':'1' if dt=='WEEKDAY' else '0',
                    'friday':'1' if dt=='WEEKDAY' else '0','saturday':'1' if dt=='SAT' else '0',
                    'sunday':'1' if dt=='SUN' else '0','start_date':'20260101','end_date':'20261231'} for dt in dts]
    M['calendar_dates']=[]
    outp=os.path.join(OUT,f'{era}.zip')
    write_feed(M,outp)
    meta['output']=outp; meta['totals']={'routes':len(M['routes']),'stops':len(M['stops']),'trips':len(M['trips']),'stop_times':len(M['stop_times'])}
    summary[era]=meta
    print(f'==> {outp}: {meta["totals"]}\n',flush=True)
json.dump(summary,open(os.path.join(OUT,'era_build_summary.json'),'w'),indent=2)
print('wrote',os.path.join(OUT,'era_build_summary.json'))
