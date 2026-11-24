#!/usr/bin/env python3
"""Check the page's mismatch estimate against an ngspice Monte Carlo of the PDK's own mismatch model.

Each case is sized from the LUT (as in verify.py), then N copies of the device sit in one netlist with
mm_ok=1, so every copy draws its own delvto, factuo, dw and dl. One operating point gives N samples of
Vth and ID; their spread is compared with the page's formula:

  sigma(Vth)   = sqrt( (A_VT/sqrt(W L))^2 + (dVth/dL * dl)^2 )
  sigma(ID)/ID = sqrt( (gm/ID * A_VT/sqrt(W L))^2 + factuo^2 + (dw/W)^2 + (dlnID/dL * dl)^2 )

dVth/dL and dlnID/dL are taken from the tables at the same VGS and VDS (neighbouring L grid points), so the
dl term includes short-channel Vth roll-off, not only the 1/L geometry; it matters at minimum L.

A_VT, factuo, dw and dl are the one-sigma values in web/index.json (read from the PDK by gen_lut.py).
The sampling error of a standard deviation from N samples is about 1/sqrt(2N), 1.6 % for N = 2000.
Run: python3 mismatch_mc.py   (same environment as verify.py)
"""
import json, os, re, subprocess
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from verify import lut_size, lib, HERE, WORK

N = 2000
MM = {d: v["mm"] for d, v in json.load(open(os.path.join(HERE, "web", "index.json")))["devices"].items()}

def l_slopes(dev, wf, L, vds, vgs):
    """dVth/dL (V/um) and dln(ID)/dL (1/um) at fixed VGS, VDS: central difference over the L grid."""
    z = np.load(os.path.join(HERE, "npz", f"lut_{dev}_wf{wf:g}.npz")); Ls = z["L"] * 1e6
    k = int(np.argmin(abs(Ls - L))); j = int(np.argmin(abs(z["vds"] - vds)))
    at = lambda key, kk: np.interp(vgs, z["vgs"], z[key][kk, :, j])
    a, b = max(k - 1, 0), min(k + 1, len(Ls) - 1)
    return ((at("vth", b) - at("vth", a)) / (Ls[b] - Ls[a]),
            (np.log(at("id", b)) - np.log(at("id", a))) / (Ls[b] - Ls[a]))

def predict(dev, L, W, gmid, wf, vds, vgs):
    m = MM[dev]; sa = m["avt"] / np.sqrt(W * L); dl = m["dl"] * 1e6   # W, L, dl in um; avt in V*um
    sv, si = l_slopes(dev, wf, L, vds, vgs)
    svt = np.sqrt(sa ** 2 + (sv * dl) ** 2)
    sid = np.sqrt((gmid * sa) ** 2 + m["factuo"] ** 2 + (m["dw"] * 1e6 / W) ** 2 + (si * dl) ** 2)
    return svt, sid

def mc(dev, L, W_um, ng, vgs, vds, tag):
    s = -1 if "pmos" in dev else 1; inst = lambda i: f"n.xm{i}.n{dev}"
    lines = [f"* mismatch MC {dev}", f".lib {lib(dev)} mos_tt", f"Vg g 0 {s*vgs}"]
    for i in range(N):
        lines += [f"Vd{i} d{i} 0 {s*vds}", f"XM{i} d{i} g 0 0 {dev} w={W_um}u l={L}u ng={ng} m=1"]
    lines += [".control", "set num_threads=1", "op"]
    lines += [f"print @{inst(i)}[ids] @{inst(i)}[vth]" for i in range(N)]
    lines += [".endc", ".end"]
    p = os.path.join(WORK, f"mc_{tag}.spice"); open(p, "w").write("\n".join(lines) + "\n")
    o = subprocess.run(["ngspice", "-b", p], cwd=WORK, capture_output=True, text=True, timeout=1200).stdout
    ids = np.abs([float(x) for x in re.findall(r"\[ids\] = ([-\d.eE+]+)", o)])
    vth = np.array([float(x) for x in re.findall(r"\[vth\] = ([-\d.eE+]+)", o)])
    assert len(ids) == N and len(vth) == N, f"{tag}: got {len(ids)} samples"
    return vth.std(ddof=1), ids.std(ddof=1) / ids.mean()

cases = [("sg13_lv_nmos", 0.13, 0.6, 10, 100e-6, 5), ("sg13_lv_nmos", 0.5, 0.6, 15, 10e-6, 2),
         ("sg13_lv_nmos", 2.0, 0.6, 20, 2e-6, 0.5), ("sg13_lv_nmos", 1.0, 0.6, 8, 50e-6, 5),
         ("sg13_lv_pmos", 0.13, 0.6, 10, 100e-6, 5), ("sg13_lv_pmos", 0.5, 0.6, 15, 10e-6, 2),
         ("sg13_hv_nmos", 0.45, 1.6, 8, 100e-6, 5), ("sg13_hv_nmos", 1.0, 1.6, 12, 20e-6, 2),
         ("sg13_hv_pmos", 1.0, 1.6, 12, 20e-6, 5)]

if __name__ == "__main__":
    os.makedirs(WORK, exist_ok=True)
    sized = [(c, lut_size(*c)) for c in cases]
    with ThreadPoolExecutor(os.cpu_count()) as ex:
        res = list(ex.map(lambda a: mc(a[0][0], a[0][1], a[1]["W"], a[1]["ng"], a[1]["vgs"], a[0][2], str(a[2])),
                          [(c, p, n) for n, (c, p) in enumerate(sized)]))
    print(f"N = {N} per case (sampling error ~{100/np.sqrt(2*N):.1f} %)")
    print(f"{'device':13} {'L':>5} {'gm/ID':>5} {'ng x Wf':>9} | {'sVth mc':>8} {'formula':>8} {'ratio':>6} | {'sID/ID mc':>9} {'formula':>8} {'ratio':>6}")
    for ((dev, L, vds, gmid, ID, wf), p), (svt, sid) in zip(sized, res):
        pv, pi = predict(dev, L, p["W"], gmid, wf, vds, p["vgs"])
        print(f"{dev:13} {L:5.2f} {gmid:5.0f} {p['ng']:3d} x {wf:<4g} | {svt*1e3:6.2f}mV {pv*1e3:6.2f}mV {svt/pv:6.3f} | "
              f"{sid*100:8.2f}% {pi*100:7.2f}% {sid/pi:6.3f}")
