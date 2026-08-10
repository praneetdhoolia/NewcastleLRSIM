#!/usr/bin/env python
"""GTFS utilities: read, clip to study area, merge feeds, pick a service date."""
import zipfile,csv,io,os,collections,datetime,shutil

STUDY=dict(s=-33.20,w=151.10,n=-32.55,e=151.95)
FILES=['agency','stops','routes','trips','stop_times','calendar','calendar_dates',
       'shapes','frequencies','transfers','feed_info','pathways','levels']

def read_feed(path):
    z=zipfile.ZipFile(path); out={}
    for n in z.namelist():
        base=os.path.basename(n)
        if not base.endswith('.txt'): continue
        with z.open(n) as f:
            out[base[:-4]]=list(csv.DictReader(io.TextIOWrapper(f,'utf-8-sig')))
    return out

def write_feed(feed,path):
    os.makedirs(os.path.dirname(path),exist_ok=True)
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for name in FILES:
            rows=feed.get(name)
            if not rows: continue
            cols=list(dict.fromkeys(k for r in rows for k in r))
            buf=io.StringIO(); w=csv.DictWriter(buf,fieldnames=cols,extrasaction='ignore',lineterminator='\n')
            w.writeheader(); w.writerows(rows)
            z.writestr(name+'.txt',buf.getvalue())

def in_study(s,box=STUDY):
    try: lat=float(s['stop_lat']); lon=float(s['stop_lon'])
    except: return False
    return box['s']<=lat<=box['n'] and box['w']<=lon<=box['e']

def clip(feed,box=STUDY):
    """Keep trips that touch >=1 stop in the box; keep all stops of those trips."""
    stops={s['stop_id']:s for s in feed.get('stops',[])}
    inside={sid for sid,s in stops.items() if in_study(s,box)}
    # include children of inside parents and vice versa
    for sid,s in stops.items():
        if s.get('parent_station') in inside: inside.add(sid)
    bytrip=collections.defaultdict(list)
    for r in feed.get('stop_times',[]): bytrip[r['trip_id']].append(r)
    keep_trips={t for t,rows in bytrip.items() if any(r['stop_id'] in inside for r in rows)}
    trips=[t for t in feed.get('trips',[]) if t['trip_id'] in keep_trips]
    keep_trips={t['trip_id'] for t in trips}
    stimes=[r for r in feed.get('stop_times',[]) if r['trip_id'] in keep_trips]
    used_stops={r['stop_id'] for r in stimes}
    for sid in list(used_stops):
        p=stops.get(sid,{}).get('parent_station')
        if p: used_stops.add(p)
    keep_routes={t['route_id'] for t in trips}
    keep_serv={t['service_id'] for t in trips}
    keep_shapes={t.get('shape_id') for t in trips if t.get('shape_id')}
    out=dict(feed)
    out['trips']=trips; out['stop_times']=stimes
    out['stops']=[s for s in feed.get('stops',[]) if s['stop_id'] in used_stops]
    out['routes']=[r for r in feed.get('routes',[]) if r['route_id'] in keep_routes]
    out['calendar']=[c for c in feed.get('calendar',[]) if c['service_id'] in keep_serv]
    out['calendar_dates']=[c for c in feed.get('calendar_dates',[]) if c['service_id'] in keep_serv]
    out['shapes']=[s for s in feed.get('shapes',[]) if s.get('shape_id') in keep_shapes]
    out['agency']=[a for a in feed.get('agency',[]) if a.get('agency_id') in {r.get('agency_id') for r in out['routes']} or len(feed.get('agency',[]))==1]
    out['transfers']=[t for t in feed.get('transfers',[]) if t.get('from_stop_id') in used_stops and t.get('to_stop_id') in used_stops]
    out['frequencies']=[f for f in feed.get('frequencies',[]) if f['trip_id'] in keep_trips]
    return out

def prefix_feed(feed,pfx):
    """Namespace ids so feeds can be merged."""
    m={'stops':['stop_id','parent_station'],'routes':['route_id'],
       'trips':['route_id','service_id','trip_id','shape_id','block_id'],
       'stop_times':['trip_id','stop_id'],'calendar':['service_id'],
       'calendar_dates':['service_id'],'shapes':['shape_id'],
       'frequencies':['trip_id'],'transfers':['from_stop_id','to_stop_id'],
       'agency':['agency_id']}
    out={}
    for t,rows in feed.items():
        cols=m.get(t,[])
        nr=[]
        for r in rows:
            r=dict(r)
            for c in cols:
                if r.get(c): r[c]=f"{pfx}:{r[c]}"
            nr.append(r)
        out[t]=nr
    # routes.agency_id also needs prefix
    for r in out.get('routes',[]):
        if r.get('agency_id') and not r['agency_id'].startswith(pfx+':'): r['agency_id']=f"{pfx}:{r['agency_id']}"
    return out

def merge(feeds):
    out=collections.defaultdict(list)
    for f in feeds:
        for t,rows in f.items(): out[t].extend(rows)
    return dict(out)

def active_services(feed,date):
    """service_ids active on YYYYMMDD."""
    d=datetime.datetime.strptime(date,'%Y%m%d').date()
    dow=['monday','tuesday','wednesday','thursday','friday','saturday','sunday'][d.weekday()]
    act=set()
    for c in feed.get('calendar',[]):
        if c['start_date']<=date<=c['end_date'] and c.get(dow)=='1': act.add(c['service_id'])
    for c in feed.get('calendar_dates',[]):
        if c['date']==date:
            if c['exception_type']=='1': act.add(c['service_id'])
            elif c['exception_type']=='2': act.discard(c['service_id'])
    return act
