#!/usr/bin/env python3
"""Pack web/*.json into one self-contained, offline index.html (log-quantised uint16 + gzip, <=0.05 % error).
Run from this folder after gen_lut.py:  python3 build_html.py"""
import json, base64, gzip, glob, numpy as np, re, os
index=json.load(open('web/index.json')); pack={}; maxerr=0
for f in sorted(glob.glob('web/sg13_*.json')):
    j=json.load(open(f)); key=f"{j['dev']}_wf{j['wf']:g}"
    keys=list(j['data']); lohi=[]; planes=[]
    for k in keys:
        a=np.frombuffer(base64.b64decode(j['data'][k]),dtype=np.float32).astype(np.float64); n=a.size
        la=np.log10(np.maximum(np.abs(a),1e-30)); lo,hi=float(la.min()),float(la.max())
        if hi==lo: hi=lo+1
        q=np.round((la-lo)/(hi-lo)*65535).astype(np.int64)
        z=(np.diff(q,prepend=0)%65536).astype(np.uint16)
        # decode check
        qq=np.cumsum(z.astype(np.int64))%65536; assert (qq==q).all()
        r=10**(lo+qq/65535*(hi-lo)); m=np.abs(a)>1e-25; maxerr=max(maxerr,float(np.max(np.abs(r[m]/np.abs(a[m])-1))))
        planes.append((z>>8).astype(np.uint8).tobytes()+(z&255).astype(np.uint8).tobytes()); lohi.append([lo,hi])
    pack[key]={"n":n,"keys":keys,"lohi":lohi,"b64":base64.b64encode(gzip.compress(b''.join(planes),9)).decode()}
print("max rel err",maxerr)
html=open('sg13g2_lut.html').read()
old_load=html[html.index('async function loadSet(name,wf){'):html.index('async function useSet(){')]
new_load='''async function loadSet(name,wf){
  const key=name+"_wf"+wf;
  if(!cache[key]){
    const P=PACK[key]; if(!P) throw new Error("no table "+key);
    const bin=atob(P.b64); const u=new Uint8Array(bin.length); for(let i=0;i<bin.length;i++) u[i]=bin.charCodeAt(i);
    const buf=new Uint8Array(await new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer());
    const n=P.n, a={};
    P.keys.forEach((k,idx)=>{
      const off=idx*2*n, lo=P.lohi[idx][0], hi=P.lohi[idx][1], out=new Float64Array(n); let q=0;
      for(let i=0;i<n;i++){ q=(q+((buf[off+i]<<8)|buf[off+n+i]))&0xFFFF; out[i]=Math.pow(10,lo+q/65535*(hi-lo)); }
      a[k]=out;
    });
    cache[key]=a;
  }
  return cache[key];
}
'''
html=html.replace(old_load,new_load)
old_boot=html[html.index('fetch("web/index.json")'):html.index('.catch(err=>')]
html=html.replace(old_boot,'''Promise.resolve(INDEX).then(j=>{
  if(typeof DecompressionStream==="undefined") throw new Error("this browser is too old; use a current Chrome, Edge, Firefox or Safari");
  LUT=j; buildCharts(); setDevice($("#dev").value); return useSet();
})''')
html=html.replace('Every value comes from','This file is self-contained and works offline; values are stored log-quantised to 16 bits (at most 0.05 % error). Every value comes from')
title=re.search(r'<title>.*?</title>',html).group(0); body=html.replace(title,'',1)
head,rest=body.split('<div class="wrap">',1); markup,script=rest.split('<script>',1)
out=('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n'+title+'\n'+head+
     '</head>\n<body>\n<div class="wrap">'+markup+'<script>\nconst INDEX='+json.dumps(index,separators=(",",":"))+';\nconst PACK='+
     json.dumps(pack,separators=(",",":"))+';\n</script>\n<script>'+script+'\n</body>\n</html>\n')
out=out.replace('body{background:var(--ground)','body{margin:0;background:var(--ground)')
open('index.html','w').write(out)
print(os.path.getsize('SG13G2_gmID_Lookup.html')/1e6,'MB')
