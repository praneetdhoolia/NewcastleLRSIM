import sys,urllib.request,urllib.parse,xml.etree.ElementTree as ET
NS={'s3':'http://s3.amazonaws.com/doc/2006-03-01/'}
def ls(host,prefix,delim='/',maxk=1000):
    tok=None; pre=[]; keys=[]
    while True:
        q={'list-type':'2','prefix':prefix,'max-keys':str(maxk)}
        if delim: q['delimiter']=delim
        if tok: q['continuation-token']=tok
        url=f"https://{host}/?"+urllib.parse.urlencode(q)
        r=ET.fromstring(urllib.request.urlopen(url,timeout=90).read())
        for c in r.findall('s3:CommonPrefixes/s3:Prefix',NS): pre.append(c.text)
        for c in r.findall('s3:Contents',NS):
            keys.append((c.find('s3:Key',NS).text,int(c.find('s3:Size',NS).text)))
        t=r.find('s3:NextContinuationToken',NS)
        if t is None or r.find('s3:IsTruncated',NS).text!='true': break
        tok=t.text
    return pre,keys
if __name__=='__main__':
    host=sys.argv[1]; prefix=sys.argv[2]; delim=sys.argv[3] if len(sys.argv)>3 else '/'
    pre,keys=ls(host,prefix,delim if delim!='none' else '')
    for p in pre: print("DIR ",p)
    for k,s in keys: print(f"FILE {s:>12,}  {k}")
