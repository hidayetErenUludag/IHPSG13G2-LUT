#!/usr/bin/env python3
"""
IHP SG13G2 gm/ID lookup-table generator (Open-LUT style).
Sweeps VGS x VDS for a list of L and finger widths Wf (ng=1), VSB = 0, TT corner, 27 C,
and stores PSP103 operating-point values per point.
Output: npz/lut_<device>_wf<Wf>.npz (full precision) + web/<device>_wf<Wf>.json (float32/base64 for the page)
+ web/index.json (grids and the PDK's mismatch coefficients per device).
Run inside IIC-OSIC-TOOLS:  python3 gen_lut.py [device ...]
Rewrite web/*.json from the existing npz files without simulating:  python3 gen_lut.py --web
"""
import os, re, sys, subprocess, json, base64, time
import numpy as np
from concurrent.futures import ThreadPoolExecutor

PDK = os.path.join(os.environ.get("PDK_ROOT", "/foss/pdks"), "ihp-sg13g2")
HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work"); os.makedirs(WORK, exist_ok=True)
WF = [0.5, 1.0, 2.0, 5.0, 10.0]   # finger widths (um), ng=1 each; multi-finger devices scale linearly with ng
W = 10e-6

DEVICES = {
  "sg13_lv_nmos": dict(pol=+1, lib="cornerMOSlv.lib", vmax=1.2, vgs_step=0.02, vds_step=0.05,
                       L=[0.13,0.15,0.18,0.2,0.25,0.3,0.35,0.4,0.5,0.6,0.8,1.0,1.5,2.0,3.0,5.0]),
  "sg13_lv_pmos": dict(pol=-1, lib="cornerMOSlv.lib", vmax=1.2, vgs_step=0.02, vds_step=0.05,
                       L=[0.13,0.15,0.18,0.2,0.25,0.3,0.35,0.4,0.5,0.6,0.8,1.0,1.5,2.0,3.0,5.0]),
  "sg13_hv_nmos": dict(pol=+1, lib="cornerMOShv.lib", vmax=3.3, vgs_step=0.05, vds_step=0.1,
                       L=[0.45,0.5,0.6,0.8,1.0,1.5,2.0,3.0,5.0]),
  "sg13_hv_pmos": dict(pol=-1, lib="cornerMOShv.lib", vmax=3.3, vgs_step=0.05, vds_step=0.1,
                       L=[0.4,0.45,0.5,0.6,0.8,1.0,1.5,2.0,3.0,5.0]),
}
# PSP op-point variables to save
OPV = ["ids","gm","gds","gmb","vth","vdss","cgg","cgs","cgd","cgsol","cgdol","cdd","cjd","sid","sfl"]

def grid(vmax, step):
    n = int(round(vmax/step)) + 1
    return np.round(np.linspace(0, vmax, n), 6)

def parse_ascii_raw(path):
    with open(path) as f: txt = f.read()
    head, data = txt.split("Values:\n", 1)
    names = []; nvar = npts = 0; invars = False
    for line in head.splitlines():
        if line.startswith("No. Variables:"): nvar = int(line.split(":")[1])
        elif line.startswith("No. Points:"): npts = int(line.split(":")[1])
        elif line.startswith("Variables:"): invars = True
        elif invars and line.strip():
            parts = line.split(); names.append(parts[1])
    tok = data.split()
    vals = np.empty((npts, nvar))
    k = 0
    for p in range(npts):
        k += 1  # point index
        for v in range(nvar):
            vals[p, v] = float(tok[k].split(",")[0]); k += 1
    return {n: vals[:, i] for i, n in enumerate(names)}

def run_one(dev, cfg, L, W=10e-6):
    s = cfg["pol"]
    vg = grid(cfg["vmax"], cfg["vgs_step"]); vd = grid(cfg["vmax"], cfg["vds_step"])
    inst = f"n.xm1.n{dev}"
    saves = " ".join(f"@{inst}[{p}]" for p in OPV)
    raw = os.path.join(WORK, f"{dev}_W{W*1e6:g}_L{L:g}.raw")
    # mm_ok=0: newer PDKs include the mismatch models in mos_tt, which would make every run a random sample
    net = f"""* LUT {dev} L={L}u
.lib {cfg['lib']} mos_tt
.temp 27
Vd d 0 0
Vg g 0 0
XM1 d g 0 0 {dev} w={W} l={L}u ng=1 m=1 mm_ok=0
.options gmin=1e-15 reltol=1e-4 abstol=1e-14 itl1=500 itl2=500
.control
set num_threads=1
set filetype=ascii
save {saves}
dc Vg 0 {s*cfg['vmax']} {s*cfg['vgs_step']} Vd 0 {s*cfg['vmax']} {s*cfg['vds_step']}
write {raw}
.endc
.end
"""
    sp = os.path.join(WORK, f"{dev}_W{W*1e6:g}_L{L:g}.spice")
    open(sp, "w").write(net)
    if os.path.exists(raw): os.remove(raw)
    nG, nD = len(vg), len(vd)
    out = {}
    try:
        subprocess.run(["ngspice", "-b", sp], cwd=WORK, capture_output=True, text=True, timeout=60)
        d = parse_ascii_raw(raw)
        for p in OPV:
            key = next(k for k in d if f"[{p}]" in k.lower())
            out[p] = d[key].reshape(nD, nG).T          # Vg inner, Vd outer -> (nG, nD)
        return vg, vd, out
    except Exception as e:
        print(f"  {dev} L={L}: 2-D sweep failed ({type(e).__name__}); falling back to one VGS sweep per VDS", flush=True)
    out = {p: np.full((nG, nD), np.nan) for p in OPV}
    for j, v in enumerate(vd):
        net1 = net.replace("Vd d 0 0", f"Vd d 0 {s*v}").replace(
            f"dc Vg 0 {s*cfg['vmax']} {s*cfg['vgs_step']} Vd 0 {s*cfg['vmax']} {s*cfg['vds_step']}",
            f"dc Vg 0 {s*cfg['vmax']} {s*cfg['vgs_step']}")
        sp1 = sp.replace(".spice", f"_vd{j}.spice"); open(sp1, "w").write(net1)
        if os.path.exists(raw): os.remove(raw)
        try:
            subprocess.run(["ngspice", "-b", sp1], cwd=WORK, capture_output=True, text=True, timeout=20)
            d = parse_ascii_raw(raw)
            for p in OPV:
                key = next(k for k in d if f"[{p}]" in k.lower())
                out[p][:len(d[key]), j] = d[key][:nG]
        except Exception as e:
            print(f"    VDS={v}: failed ({type(e).__name__}), left as NaN", flush=True)
    return vg, vd, out

def build(dev, wf):
    cfg = DEVICES[dev]; t0 = time.time(); W = wf*1e-6
    res = {}
    with ThreadPoolExecutor(os.cpu_count()) as ex:   # one single-threaded ngspice process per L
        for vg, vd, o in ex.map(lambda L: run_one(dev, cfg, L, W), cfg["L"]):
            for p in OPV: res.setdefault(p, []).append(o[p])
    A = {p: np.array(v) for p, v in res.items()}      # shape (nL, nVGS, nVDS)
    tab = dict(
        id   = np.abs(A["ids"]),
        gm   = np.abs(A["gm"]),
        gds  = np.abs(A["gds"]),
        gmb  = np.abs(A["gmb"]),
        vth  = np.abs(A["vth"]),
        vdsat= np.abs(A["vdss"]),
        cgg  = np.abs(A["cgg"]) + np.abs(A["cgsol"]) + np.abs(A["cgdol"]),   # incl. overlap
        cgs  = np.abs(A["cgs"]) + np.abs(A["cgsol"]),
        cgd  = np.abs(A["cgd"]) + np.abs(A["cgdol"]),
        cdd  = np.abs(A["cdd"]) + np.abs(A["cgdol"]) + np.abs(A["cjd"]),
        sid  = np.abs(A["sid"]),     # drain thermal-noise PSD (A^2/Hz)
        sfl  = np.abs(A["sfl"]),     # flicker-noise PSD at 1 Hz (A^2/Hz)
    )
    np.savez_compressed(os.path.join(HERE, "npz", f"lut_{dev}_wf{wf:g}.npz"), L=np.array(cfg["L"])*1e-6,
                        vgs=vg, vds=vd, W=W, **tab)
    print(f"{dev} Wf={wf}u: {len(cfg['L'])} L x {len(vg)} VGS x {len(vd)} VDS in {time.time()-t0:.1f}s", flush=True)
    return dict(L=cfg["L"], vgs=vg.tolist(), vds=vd.tolist(), W=W, wf=wf, vmax=cfg["vmax"], tab=tab)

def mismatch_params(dev):
    """The PDK's per-instance mismatch for this device, read from sg13g2_mos{lv,hv}_mismatch.lib (one sigma):
    delvto = A_VT/sqrt(W*L) with A_VT in V*um, factuo (mobility factor, not area-scaled), dw and dl (absolute, m)."""
    path = os.path.join(PDK, "libs.tech", "ngspice", "models", f"sg13g2_mos{dev[5:7]}_mismatch.lib")
    txt = open(path).read(); name = "sg13g2" + dev[4:]
    get = lambda k: float(re.search(rf"\.param\s+{name}_{k}_mm\s*=\s*([-\d.eE+]+)", txt).group(1))
    return dict(avt=get("delvto"), factuo=get("factuo"), dw=get("dw"), dl=get("dl"))

def flicker_exponent(dev):
    """EFO of the device's PSP model card: flicker noise goes as sfl / f^EF (HV PMOS has 1.152, not 1)."""
    txt = open(os.path.join(PDK, "libs.tech", "ngspice", "models", f"sg13g2_mos{dev[5:7]}_parm.lib")).read()
    card = re.search(rf"\.model\s+sg13g2{dev[4:]}_psp\b(.*?)(?=\n\.model|\Z)", txt, re.S).group(1)
    return float(re.search(r"\befo\s*=\s*([-\d.eE+]+)", card).group(1))

def index_entry(dev):
    cfg = DEVICES[dev]
    return dict(L=cfg["L"], vmax=cfg["vmax"], vgs=grid(cfg["vmax"], cfg["vgs_step"]).tolist(),
                vds=grid(cfg["vmax"], cfg["vds_step"]).tolist(), wf=WF, mm=mismatch_params(dev),
                ef=flicker_exponent(dev))

WEB_KEYS = ("id", "gm", "gds", "gmb", "vth", "vdsat", "cgg", "cgs", "cgd", "cdd", "sid", "sfl")
def write_web(dev, wf, tab):
    json.dump({"dev": dev, "wf": wf, "data": {k: b64(tab[k]) for k in WEB_KEYS}},
              open(os.path.join(HERE, "web", f"{dev}_wf{wf:g}.json"), "w"))

def b64(a): return base64.b64encode(np.ascontiguousarray(a, dtype=np.float32).tobytes()).decode()

if __name__ == "__main__":
    web_only = "--web" in sys.argv
    devs = [a for a in sys.argv[1:] if a != "--web"] or list(DEVICES)
    os.makedirs(os.path.join(HERE, "npz"), exist_ok=True); os.makedirs(os.path.join(HERE, "web"), exist_ok=True)
    index = {"meta": dict(pdk="IHP SG13G2", corner="mos_tt", temp=27, vsb=0, wf=WF,
                          note="One file per device and finger width Wf (ng=1). Multi-finger devices scale linearly with ng. cgg includes overlap caps. "
                               "sid: drain thermal-noise PSD (A^2/Hz); sfl: flicker-noise PSD at 1 Hz (A^2/Hz), scaling as 1/f^ef. "
                               "mm: the PDK's one-sigma mismatch per instance (avt in V*um, factuo relative, dw and dl in m).",
                          layout="each array is float32, shape [nL][nVGS][nVDS], row-major"), "devices": {}}
    for dev in devs:
        index["devices"][dev] = index_entry(dev)
        for wf in WF:
            tab = dict(np.load(os.path.join(HERE, "npz", f"lut_{dev}_wf{wf:g}.npz"))) if web_only else build(dev, wf)["tab"]
            write_web(dev, wf, tab)
    json.dump(index, open(os.path.join(HERE, "web", "index.json"), "w"))
    print("done")
