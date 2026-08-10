#!/usr/bin/env python
"""Download the open observed-data bundle with provenance."""
import os,json,hashlib,urllib.request,datetime,sys
B="https://opendata.transport.nsw.gov.au/data/dataset/"
M=[
 # ---- B4 Opal patronage ----
 ("opal/lightrail_trips_by_line_cardtype.csv",B+"6641ea76-4818-4e38-864f-4e3cb6bb98ee/resource/2bb651a0-eb15-4729-8dd5-9891b3708e6d/download/lightrail.csv","TfNSW Opal Trips - Light Rail (NRT, by month/line/card type)","CC-BY 4.0"),
 ("opal/lightrail_trips_by_tapon_station.csv",B+"6641ea76-4818-4e38-864f-4e3cb6bb98ee/resource/80b57af2-dc41-49c0-bb54-e0d7fa5214f6/download/lightrail-june-2024.csv","TfNSW Opal Light Rail trips by tap-on station (to Jun 2024; pre series break)","CC-BY 4.0"),
 ("opal/bus_trips_by_contract_region.csv",B+"e63d778f-46dd-4ea1-b832-ef917876ce5a/resource/6095c2b7-8649-4244-902d-4e62c8ea87d9/download/bus.csv","TfNSW Opal Trips - Bus by contract region","CC-BY 4.0"),
 ("opal/bus_trips_by_contract_area_legacy.csv",B+"e63d778f-46dd-4ea1-b832-ef917876ce5a/resource/9862b4f1-37d9-495a-97b6-0c867fa91d83/download/bus-card-type_48.csv","TfNSW Opal bus trips by contract area (legacy, pre-2024 methodology)","CC-BY 4.0"),
 ("opal/all_modes_trips.csv",B+"c92c0418-8678-4e39-9c34-70be8c35f7ef/resource/c77b83d7-cdcd-4a0e-9b12-fcc159727589/download/all_modes.csv","TfNSW Opal Trips - All Modes","CC-BY 4.0"),
 ("opal/all_modes_trips_legacy.csv",B+"c92c0418-8678-4e39-9c34-70be8c35f7ef/resource/75df8157-3eab-4cf1-a877-86ce7c08af26/download/all-modes_legacy.csv","TfNSW Opal Trips - All Modes (legacy methodology epoch)","CC-BY 4.0"),
 ("opal/station_entries_exits_monthly.csv",B+"3977df59-a1fa-422e-91ff-cfaeac355cc9/resource/f8bb2918-0540-4bb3-9ccf-f7aef04d4249/download/entry_exit.csv","TfNSW Train/Metro/LR station monthly usage (Opal batch, from Nov 2024)","CC-BY 4.0"),
 ("opal/station_entries_exits_2016_2023_typical_day.xlsx",B+"3977df59-a1fa-422e-91ff-cfaeac355cc9/resource/491763fc-82ed-4e44-9fca-8f3285db526e/download/train-station-entries-and-exits-version-2.2.xlsx","TfNSW Train station entries/exits 2016-2023 typical day","CC-BY 4.0"),
 ("opal/tap_time_loc_20160725-31.csv",B+"4789edda-acb9-4eba-acc1-327db1a13843/resource/ce1e431d-30a2-4f73-b1dd-d1944a203ca3/download/time-loc_20160725-31_2.csv","Opal tap on/off by time and location, 25-31 Jul 2016 (era 2)","CC-BY 4.0"),
 ("opal/tap_time_loc_20160808-14.csv",B+"4789edda-acb9-4eba-acc1-327db1a13843/resource/91a8e531-b2f8-4d0f-9d82-79e45c56ce27/download/time-loc_20160808-14.csv","Opal tap on/off by time and location, 8-14 Aug 2016 (era 2)","CC-BY 4.0"),
 ("opal/opal_tap_documentation.pdf",B+"4789edda-acb9-4eba-acc1-327db1a13843/resource/a148d2c0-bf82-44f8-904b-124f20e8a7bb/download/open-opal-data-documentation_0_1.pdf","Open Opal Data documentation","CC-BY 4.0"),
 # ---- B5 counts ----
 ("counts/rms_station_reference.csv",B+"ef2b0bd2-db1e-48f3-9ea1-2bb9e6bc6504/resource/c65ad7b4-0257-4cc6-953e-5299ac8d27ba/download/road_traffic_counts_station_reference.csv","NSW road traffic count station reference","CC-BY 4.0"),
 ("counts/rms_yearly_summary.csv",B+"ef2b0bd2-db1e-48f3-9ea1-2bb9e6bc6504/resource/cba9a012-c305-414e-b848-f0e3aad18d97/download/road_traffic_counts_yearly_summary.csv","NSW road traffic counts yearly summary (AADT)","CC-BY 4.0"),
 ("counts/rms_hourly_permanent.zip",B+"ef2b0bd2-db1e-48f3-9ea1-2bb9e6bc6504/resource/bca06c7e-30be-4a90-bc8b-c67428c0823a/download/road_traffic_counts_hourly_permanent.zip","NSW road traffic counts hourly, permanent stations","CC-BY 4.0"),
 ("counts/rms_documentation.pdf",B+"ef2b0bd2-db1e-48f3-9ea1-2bb9e6bc6504/resource/13d061b1-1606-49b5-b182-d36ce0801f14/download/rms-dataset-documentation-nsw-traffic-volume-counts_0.pdf","NSW traffic volume counts documentation","CC-BY 4.0"),
 # ---- C1 behavioural evidence: HTS ----
 ("hts/hts_by_lga_2020-21_to_2024-25.xlsx",B+"c0f9a300-38e5-4086-90fb-c7a1f0b0fe31/resource/8b0a7e54-9dea-43c3-9804-5e2917bf4f1f/download/data-by-lga-2020_21-to-2024_25.xlsx","NSW Household Travel Survey by LGA 2020/21-2024/25","CC-BY 4.0"),
 ("hts/hts_by_sa3_2020-21_to_2024-25.xlsx",B+"c0f9a300-38e5-4086-90fb-c7a1f0b0fe31/resource/e95e31d5-64ed-44f1-b845-250498849758/download/data-by-sa3-2020_21-to-2024_25.xlsx","NSW Household Travel Survey by SA3 2020/21-2024/25","CC-BY 4.0"),
 ("hts/hts_by_lga_2009-10_to_2019-20.xlsx",B+"c0f9a300-38e5-4086-90fb-c7a1f0b0fe31/resource/2bc7603b-6bba-456d-9a81-e560d8a0f5ce/download/data-by-lga-2009-to-2019_revised-release-feb-2026.xlsx","NSW Household Travel Survey by LGA 2009/10-2019/20","CC-BY 4.0"),
 ("hts/hts_by_sa3_2009-10_to_2019-20.xlsx",B+"c0f9a300-38e5-4086-90fb-c7a1f0b0fe31/resource/75b3e41c-18e6-499d-948d-de735fd8e308/download/data-by-sa3-2009-to-2019_revised-release-feb-2026.xlsx","NSW Household Travel Survey by SA3 2009/10-2019/20","CC-BY 4.0"),
 ("hts/hts_data_document_2020_2024.pdf",B+"c0f9a300-38e5-4086-90fb-c7a1f0b0fe31/resource/5a0ac96e-4562-4ffe-bb96-beb0cb0dca89/download/hts-data-document-2020_2024.pdf","HTS data documentation 2020-2024","CC-BY 4.0"),
 ("hts/hts_data_document_2009_2019.pdf",B+"c0f9a300-38e5-4086-90fb-c7a1f0b0fe31/resource/8c440e30-09b2-4c70-99ed-74a250fb55f9/download/hts-data-document-2009_2019.pdf","HTS data documentation 2009-2019","CC-BY 4.0"),
]
root='data/raw'; prov=[]
for rel,url,desc,lic in M:
    p=os.path.join(root,rel); os.makedirs(os.path.dirname(p),exist_ok=True)
    if os.path.exists(p) and os.path.getsize(p)>500:
        print(f"SKIP {rel}")
    else:
        print(f"GET  {rel}",flush=True)
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'newcastle-lr-sim/0.1 (research)'})
            with urllib.request.urlopen(req,timeout=600) as r, open(p,'wb') as f:
                while True:
                    c=r.read(1<<20)
                    if not c: break
                    f.write(c)
        except Exception as e:
            print(f"  FAIL {e}"); continue
    sz=os.path.getsize(p); h=hashlib.sha256(open(p,'rb').read()).hexdigest()
    print(f"  {sz:>13,} B")
    prov.append({"path":rel,"url":url,"description":desc,"licence":lic,"bytes":sz,
                 "sha256":h,"retrieved":datetime.date.today().isoformat()})
json.dump(prov,open(os.path.join(root,'provenance_open_data.json'),'w'),indent=2)
print("\nwrote data/raw/provenance_open_data.json  (%d files)"%len(prov))
