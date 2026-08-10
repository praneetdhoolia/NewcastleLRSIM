#!/usr/bin/env python
"""Download era-variant GTFS bundles from the TfNSW historical GTFS S3 archive."""
import os,urllib.request,hashlib,json,sys
BASE="https://opendata-gtfs.transport.nsw.gov.au/"
OUT="schedules/raw"
# era_key -> list of (feed_label, s3_key)
ERAS={
 "era2_2016_rail_truncated":[
   ("sydneytrains","historical_gtfs/sydneytrains/2016/2016-09/sydneytrains_schedule_data_20160920000000.zip"),
   ("nswtrains","historical_gtfs/nswtrains/2016/2016-09/nswtrains_schedule_data_20160923000000.zip"),
   ("complete","historical_gtfs/complete_gtfs/2016/2016-08/full_greater_sydney_gtfs_static_20160829.zip"),
 ],
 "era3_2018_keolis_interchange":[
   ("nisc001","historical_gtfs/NISC001/2018/2018-10/NISC001_scheduled_data_20181019.zip"),
   ("sydneytrains","historical_gtfs/sydneytrains/2018/2018-10/SydneyTrains_scheduled_data_20181030.zip"),
   ("nswtrains","historical_gtfs/nswtrains/2018/2018-10/nswtrains_scheduled_data_20181007011000.zip"),
 ],
 "era4_2019_lr_open":[
   ("nisc001","historical_gtfs/NISC001/2019/2019-03/NISC001_scheduled_data_20190325210300.zip"),
   ("sydneytrains","historical_gtfs/sydneytrains/2019/2019-03/sydneytrains_scheduled_data_20190331010300.zip"),
   ("nswtrains","historical_gtfs/nswtrains/2019/2019-03/nswtrains_scheduled_data_20190330010300.zip"),
   ("lightrail","historical_gtfs/lightrail-newcastle/2020/2020-02/lightrail-newcastle_scheduled_data_20200218010200.zip"),
 ],
 "base2026":[
   ("nisc001","historical_gtfs/NISC001/2026/2026-08/NISC001_scheduled_data_20260805190800.zip"),
   ("lightrail","historical_gtfs/lightrail-newcastle/2026/2026-08/lightrail-newcastle_scheduled_data_20260804010800.zip"),
   ("regionbuses","historical_gtfs/regionbuses-newcastlehunter/2026/2026-08/regionbuses-newcastlehunter_scheduled_data_20260801200800.zip"),
   ("sydneytrains","historical_gtfs/sydneytrains/2026/2026-08/sydneytrains_scheduled_data_20260808010800.zip"),
   ("nswtrains","historical_gtfs/nswtrains/2026/2026-08/nswtrains_scheduled_data_20260801010800.zip"),
 ],
}
prov=[]
for era,items in ERAS.items():
    d=os.path.join(OUT,era); os.makedirs(d,exist_ok=True)
    for label,key in items:
        p=os.path.join(d,f"{label}.zip")
        if os.path.exists(p) and os.path.getsize(p)>1000:
            print(f"SKIP {era}/{label}"); 
        else:
            url=BASE+key
            print(f"GET  {era}/{label} <- {key}",flush=True)
            try:
                urllib.request.urlretrieve(url,p)
            except Exception as e:
                print(f"  FAIL {e}"); continue
        h=hashlib.sha256(open(p,'rb').read()).hexdigest()[:16]
        sz=os.path.getsize(p)
        print(f"  {sz:>12,} B sha256:{h}")
        prov.append({"era":era,"feed":label,"s3_key":key,"bytes":sz,"sha256_16":h,
                     "source":"TfNSW Open Data Hub historical GTFS archive","licence":"CC-BY 4.0"})
json.dump(prov,open(os.path.join(OUT,"provenance.json"),"w"),indent=2)
print("\nwrote",os.path.join(OUT,"provenance.json"))
