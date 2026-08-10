import json,sys,urllib.request
BASE="https://opendata.transport.nsw.gov.au/data/api/3/action/package_show?id="
pkgs=sys.argv[1:]
for p in pkgs:
    try:
        d=json.load(urllib.request.urlopen(BASE+p,timeout=60))['result']
    except Exception as e:
        print("ERR",p,e); continue
    print("="*70); print("PKG:",p,"|",d.get('title'))
    for r in d.get('resources',[]):
        print("   -",r.get('name'),"|",r.get('format'),"|",r.get('url'))
