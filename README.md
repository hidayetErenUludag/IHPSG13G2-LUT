# SG13G2 gm/ID Lookup

Interactive gm/I<sub>D</sub> lookup tables and a transistor-sizing calculator for the **IHP SG13G2** 130 nm BiCMOS open-source PDK.

Pick a device, |V<sub>DS</sub>|, channel length and finger width, enter a gm/I<sub>D</sub> target, and size by I<sub>D</sub>, g<sub>m</sub> or W. The calculator returns the finger count (ng × W<sub>f</sub>), V<sub>GS</sub>, V<sub>th</sub>, V<sub>ov</sub>, V<sub>Dsat</sub>, intrinsic gain g<sub>m</sub>/g<sub>ds</sub>, f<sub>T</sub>, device capacitances, noise (γ, flicker corner, input-referred noise density and band-integrated rms) and mismatch from the PDK model (σ(V<sub>th</sub>), σ(I<sub>D</sub>)/I<sub>D</sub>, differential-pair offset, current-mirror error), alongside six lookup charts versus gm/I<sub>D</sub>. **Compare** (+ B) adds a second device, length or finger width at the same gm/I<sub>D</sub> and size target, side by side in the table and dashed in the charts.

This is an SG13G2 port of **Open-LUT** by Khalid, Maestre and Madrid-Khalid ([paper](https://doi.org/10.1109/ICICM66614.2025.11316023) · [SKY130 web tool](http://www.open-lut.org/)), extended with a finger-width axis. If you use this tool in published work, please cite their paper (BibTeX below).

## Quick start

**Use it online:** <https://hidayeterenuludag.github.io/IHPSG13G2-LUT/>

**Or offline:** download [`SG13G2_gmID_Lookup.html`](SG13G2_gmID_Lookup.html) and open it in a current Chrome, Edge, Firefox or Safari. It is a single self-contained file (about 5.5 MB) with all tables built in.

**Example.** `sg13_lv_nmos`, |V<sub>DS</sub>| = 0.6 V, L = 0.5 µm, W<sub>f</sub> = 2 µm, gm/I<sub>D</sub> = 15 S/A, I<sub>D</sub> = 10 µA gives 2 × 2 µm fingers, V<sub>GS</sub> = 0.355 V, g<sub>m</sub> = 0.19 mS, g<sub>m</sub>/g<sub>ds</sub> = 26 and f<sub>T</sub> ≈ 2 GHz.

## Coverage

| Device | Role | L (µm) | V<sub>GS</sub>, \|V<sub>DS</sub>\| | Grid step (V<sub>GS</sub> / V<sub>DS</sub>) |
|---|---|---|---|---|
| `sg13_lv_nmos`, `sg13_lv_pmos` | 1.2 V core, thin oxide | 0.13 – 5 (16 values) | 0 – 1.2 V | 20 mV / 50 mV |
| `sg13_hv_nmos` | 3.3 V I/O, thick oxide | 0.45 – 5 (9 values) | 0 – 3.3 V | 50 mV / 100 mV |
| `sg13_hv_pmos` | 3.3 V I/O, thick oxide | 0.40 – 5 (10 values) | 0 – 3.3 V | 50 mV / 100 mV |

- Finger widths W<sub>f</sub> = 0.5, 1, 2, 5, 10 µm, each characterised as a single-finger device (ng = 1). 10 µm is the PDK's maximum finger width for all four devices.
- Corner `mos_tt`, 27 °C, V<sub>SB</sub> = 0. PMOS values are magnitudes.
- Stored per bias point: I<sub>D</sub>, g<sub>m</sub>, g<sub>ds</sub>, g<sub>mb</sub>, V<sub>th</sub>, V<sub>Dsat</sub>, C<sub>gg</sub>, C<sub>gs</sub>, C<sub>gd</sub>, C<sub>dd</sub>, the drain thermal-noise PSD (`sid`, A²/Hz) and the flicker-noise PSD at 1 Hz (`sfl`, A²/Hz).
- C<sub>gg</sub> includes gate overlap capacitance, so g<sub>m</sub>/(2π·C<sub>gg</sub>) equals PSP's own `fug`. C<sub>dd</sub> adds the drain junction and gate–drain overlap.
- SG13G2 has one threshold flavour per oxide (no LVT/HVT variants as in SKY130). The `*_rf_*` symbols are the same transistors with an RF/NQS model and are not tabulated separately.

## Noise and mismatch

**Noise.** Drain noise of an ng-finger device is ng·(S<sub>id</sub> + S<sub>fl</sub>/f<sup>EF</sup>); the page divides by g<sub>m</sub><sup>2</sup> for input-referred noise, integrates over the band you enter, and shows γ = S<sub>id</sub>/(4kT·g<sub>m</sub>) and the flicker corner f<sub>c</sub> = (S<sub>fl</sub>/S<sub>id</sub>)<sup>1/EF</sup>. EF is the model card's flicker exponent (`efo`): 1.0 for LV NMOS, LV PMOS and HV NMOS, **1.152 for HV PMOS**. `gen_lut.py` reads it from the PDK into `web/index.json` (`ef`).

**Mismatch.** The PDK's `mos_tt` includes a per-instance mismatch model (`sg13g2_mos{lv,hv}_mismatch.lib`, one sigma), and the page uses it directly:

| Device | A<sub>VT</sub> (mV·µm) | mobility (`factuo`) | ΔW | ΔL |
|---|---|---|---|---|
| `sg13_lv_nmos` | 2.0 | 1 % | 4 nm | 2 nm |
| `sg13_lv_pmos` | 2.5 | 0.5 % | 5 nm | 1.5 nm |
| `sg13_hv_nmos` | 9.0 | 0.8 % | 8 nm | 3 nm |
| `sg13_hv_pmos` | 8.0 | 1 % | 9 nm | 3 nm |

σ(V<sub>th</sub>) = √((A<sub>VT</sub>/√(WL))² + (∂V<sub>th</sub>/∂L·ΔL)²) and σ(I<sub>D</sub>)/I<sub>D</sub> = √((g<sub>m</sub>/I<sub>D</sub>·A<sub>VT</sub>/√(WL))² + factuo² + (ΔW/W)² + (∂lnI<sub>D</sub>/∂L·ΔL)²), with the L slopes taken from the tables at the same V<sub>GS</sub>, so ΔL includes short-channel V<sub>th</sub> roll-off. Only the V<sub>th</sub> term shrinks with area. A matched pair has √2 times the single-device spread; the pair's input offset is √2·σ(I<sub>D</sub>)/I<sub>D</sub> ÷ (g<sub>m</sub>/I<sub>D</sub>). `gen_lut.py` copies the coefficients from the PDK into `web/index.json` (`mm`).

## Why finger width is an axis

SG13G2 LV devices depend on finger width, not only on total width. At the same bias, LV NMOS V<sub>th</sub> falls from 0.29 V at a 1 µm finger to 0.21 V at a 50 µm finger, and current per µm changes by about 25 % between 1 µm and 5 µm fingers. A table built at a single width therefore mis-sizes other widths by up to 34 % in I<sub>D</sub>.

Fingers of the same W<sub>f</sub> scale exactly with ng, so the calculator sizes as **ng × W<sub>f</sub>** and warns when rounding to whole fingers moves I<sub>D</sub> or g<sub>m</sub> more than 10 % from the target.

## Accuracy

`verify.py` sizes eight devices from the tables, rounds them to whole fingers, simulates each one directly in ngspice and compares:

| Quantity | Agreement with direct simulation |
|---|---|
| I<sub>D</sub>, g<sub>m</sub>, g<sub>ds</sub> | within 3 % |
| f<sub>T</sub> | within 8 % (the table is conservative for multi-finger devices) |
| Drain noise (ngspice `.noise` at f<sub>c</sub>/100, f<sub>c</sub>, 100·f<sub>c</sub>) | within 5 % |
| Mismatch (`mismatch_mc.py`: 2000-sample ngspice Monte Carlo of the PDK mismatch model, 9 cases) | σ(V<sub>th</sub>) and σ(I<sub>D</sub>)/I<sub>D</sub> within 10 %; within 4 % for L ≥ 0.5 µm |

The standalone HTML stores values log-quantised to 16 bits, which adds at most 0.05 % error. All results are simulation only and have not been compared against measured silicon.

## Regenerating the tables

Requirements: [IIC-OSIC-TOOLS](https://github.com/iic-jku/IIC-OSIC-TOOLS) (ngspice with OSDI support and the IHP-Open-PDK at `$PDK_ROOT/ihp-sg13g2`) and Python 3 with NumPy.

```bash
python3 gen_lut.py      # writes npz/lut_<device>_wf<Wf>.npz and web/*.json
python3 gen_lut.py --web   # only rewrites web/*.json and web/index.json from the npz files (no simulation)
python3 verify.py       # cross-checks sized devices (DC, fT, noise) against direct simulation
python3 mismatch_mc.py  # checks the page's mismatch formula against an ngspice Monte Carlo (~1 min)
python3 build_html.py   # builds index.html (online) and SG13G2_gmID_Lookup.html (offline) from sg13g2_lut.html + web/*.json
```

`gen_lut.py` reads PSP103 operating-point values directly from the model instance (`@n.xm1.n<device>[gm]`, `[gds]`, `[cgg]`, …) during a nested V<sub>GS</sub> × V<sub>DS</sub> DC sweep, one ngspice run per (device, L, W<sub>f</sub>). It uses `reltol=1e-4, abstol=1e-14, itl1=itl2=500`; tighter tolerances stall the LV PMOS sweep at L = 5 µm. Regenerate whenever IHP updates the models and record the new PDK commit below.

### Versions used

| Component | Version |
|---|---|
| IHP-Open-PDK | commit `<fill in: cat $PDK_ROOT/ihp-sg13g2/COMMIT>` |
| Simulator | ngspice-47, PSP103 via OSDI (OpenVAF-reloaded) |
| Environment | IIC-OSIC-TOOLS `hpretl/iic-osic-tools:latest`, September 2026 |

## Using the tables in Python

```python
import numpy as np

t = np.load("npz/lut_sg13_lv_nmos_wf2.npz")   # arrays shaped [L][VGS][VDS]
L, vgs, vds = t["L"], t["vgs"], t["vds"]       # metres, volts, volts
gm_id = t["gm"] / t["id"]                      # S/A
id_w  = t["id"] / t["W"]                       # A/m per finger (W = one finger)
ft    = t["gm"] / (2 * np.pi * t["cgg"])       # Hz
fc    = t["sfl"] / t["sid"]                    # flicker corner, Hz (EF = 1; HV PMOS: ** (1/1.152))
```

For a device with ng fingers, multiply I<sub>D</sub>, g<sub>m</sub>, g<sub>ds</sub> and all capacitances by ng. Ratios (gm/I<sub>D</sub>, g<sub>m</sub>/g<sub>ds</sub>, f<sub>T</sub>) and voltages do not change.

## Repository layout

| Path | Purpose |
|---|---|
| `index.html` | The online calculator served by GitHub Pages. Loads only the table you select from `web/`. |
| `SG13G2_gmID_Lookup.html` | Offline calculator. Self-contained; download and double-click. |
| `sg13g2_lut.html` | Page body source shared by both pages. Edit this, then run `build_html.py`. |
| `gen_lut.py` | Table generator (ngspice) |
| `verify.py` | Check against direct simulation (DC, f<sub>T</sub>, noise) |
| `mismatch_mc.py` | Check the mismatch estimate against a Monte Carlo |
| `build_html.py` | Builds both pages and adds the search/social metadata |
| `npz/` | Full-precision tables for Python |
| `web/` | float32 tables loaded by `index.html` |
| `preview.png`, `sitemap.xml`, `llms.txt` | Link-preview image, sitemap and plain-text summary for search engines and AI assistants (all regenerated by `build_html.py`) |
| `CITATION.cff` | Citation metadata (GitHub's "Cite this repository" button) |


## References

1. S. A. Khalid, S. E. Maestre and K. M. Madrid-Khalid, "Open-LUT: Interactive g<sub>m</sub>/I<sub>D</sub> Lookup Tables for MOSFET Sizing in Open-Source PDKs," in *2025 10th International Conference on Integrated Circuits and Microsystems (ICICM)*, Hefei, China, 2025, pp. 344–353, doi: [10.1109/ICICM66614.2025.11316023](https://doi.org/10.1109/ICICM66614.2025.11316023).
2. IHP GmbH, *IHP-Open-PDK*, Apache-2.0. <https://github.com/IHP-GmbH/IHP-Open-PDK>
3. P. G. A. Jespers and B. Murmann, *Systematic Design of Analog CMOS Circuits: Using Pre-Computed Lookup Tables*. Cambridge University Press, 2017.
4. H. Pretl, G. Zachl et al., *IIC-OSIC-TOOLS*, Johannes Kepler University Linz. <https://github.com/iic-jku/IIC-OSIC-TOOLS>
5. *ngspice* circuit simulator. <https://ngspice.sourceforge.io/>

### Citing this tool

Use GitHub's **Cite this repository** button (from [`CITATION.cff`](CITATION.cff)), and please also cite Open-LUT.

### Citing Open-LUT

```bibtex
@INPROCEEDINGS{khalid2025openlut,
  author    = {Khalid, Sihawi A. and Maestre, Susie E. and Madrid-Khalid, Karla M.},
  title     = {{Open-LUT}: Interactive $g_m/I_D$ Lookup Tables for {MOSFET} Sizing in Open-Source {PDKs}},
  booktitle = {2025 10th International Conference on Integrated Circuits and Microsystems (ICICM)},
  address   = {Hefei, China},
  year      = {2025},
  pages     = {344--353},
  doi       = {10.1109/ICICM66614.2025.11316023}
}
```

## License

Copyright 2026 Hidayet Eren Uludağ.

Code, page and generated tables are released under the [Apache License 2.0](LICENSE). The tables are derived from the IHP SG13G2 device models, © IHP GmbH, also Apache-2.0; see [NOTICE](NOTICE).

## Author

Hidayet Eren Uludağ, Electrical and Electronics Engineering, Özyeğin University, Istanbul.
