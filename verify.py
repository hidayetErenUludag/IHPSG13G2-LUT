#!/usr/bin/env python3
"""Size a device from the finger-width LUT (gm/ID + ID + Wf), round to whole fingers, simulate it, compare."""
import numpy as np, subprocess, os, re
HERE=os.path.dirname(os.path.abspath(__file__)); WORK=os.path.join(HERE,"work")
def lib(dev): return "cornerMOSlv.lib" if "_lv_" in dev else "cornerMOShv.lib"
def lut_size(dev,L,vds,gmid,ID,wf):
    z=np.load(os.path.join(HERE,"npz",f"lut_{dev}_wf{wf:g}.npz")); k=int(np.argmin(abs(z["L"]-L*1e-6))); j=int(np.argmin(abs(z["vds"]-vds)))
    idc=z["id"][k,:,j]; g=z["gm"][k,:,j]/np.where(idc>1e-13,idc,np.nan); pk=int(np.nanargmax(g))
    for i in range(pk,len(g)-1):
        if g[i]>=gmid>=g[i+1]:
            f=(g[i]-gmid)/(g[i]-g[i+1]); lp=lambda a:a[k,i,j]+(a[k,i+1,j]-a[k,i,j])*f
            ng=max(1,round(ID/lp(z["id"]))); s=ng          # one finger = one characterised device
            vgs=z["vgs"][i]+(z["vgs"][i+1]-z["vgs"][i])*f
            return dict(ng=ng, W=wf*ng, vgs=vgs, id=lp(z["id"])*s, gm=lp(z["gm"])*s, gds=lp(z["gds"])*s, ft=lp(z["gm"])/(2*np.pi*lp(z["cgg"])))
def sim(dev,L,W_um,ng,vgs,vds):
    s=-1 if "pmos" in dev else 1; inst=f"n.xm1.n{dev}"
    net=f"* verify\n.lib {lib(dev)} mos_tt\nVd d 0 {s*vds}\nVg g 0 {s*vgs}\nXM1 d g 0 0 {dev} w={W_um}u l={L}u ng={ng} m=1\n.control\nop\nprint @{inst}[ids] @{inst}[gm] @{inst}[gds] @{inst}[fug]\n.endc\n.end\n"
    p=os.path.join(WORK,"verify.spice"); open(p,"w").write(net)
    o=subprocess.run(["ngspice","-b",p],cwd=WORK,capture_output=True,text=True,timeout=60).stdout
    return {k:abs(float(x)) for k,x in re.findall(r"\[(ids|gm|gds|fug)\]\s*=\s*([-\d.eE+]+)",o)}
cases=[("sg13_lv_nmos",0.5,0.6,15,10e-6,1),("sg13_lv_nmos",0.5,0.6,15,10e-6,2),("sg13_lv_nmos",0.13,0.6,10,100e-6,5),
       ("sg13_lv_nmos",2.0,0.6,20,2e-6,0.5),("sg13_lv_pmos",0.5,0.6,15,10e-6,2),("sg13_lv_pmos",1.0,0.6,8,50e-6,5),
       ("sg13_hv_nmos",1.0,1.6,12,20e-6,2),("sg13_hv_pmos",1.0,1.6,12,20e-6,5)]
if __name__=="__main__":
  print(f"{'device':13} {'L':>5} {'gm/ID':>5} {'Wf':>5} {'ng':>3} {'W':>7} {'VGS':>6} | {'ID sim/lut':>10} {'gm sim/lut':>10} {'gds sim/lut':>11} {'fT sim/lut':>10}")
  for dev,L,vds,gmid,ID,wf in cases:
    p=lut_size(dev,L,vds,gmid,ID,wf); v=sim(dev,L,p["W"],p["ng"],p["vgs"],vds)
    print(f"{dev:13} {L:5.2f} {gmid:5.0f} {wf:5.1f} {p['ng']:3d} {p['W']:6.1f}u {p['vgs']:6.3f} | {v['ids']/p['id']:10.3f} {v['gm']/p['gm']:10.3f} {v['gds']/p['gds']:11.3f} {v['fug']/p['ft']:10.3f}")
