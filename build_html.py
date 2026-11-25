#!/usr/bin/env python3
"""Build the two published pages from sg13g2_lut.html (page body) and web/*.json (tables).

  index.html               online page for GitHub Pages; loads web/*.json on demand (~1.3 MB per table)
  SG13G2_gmID_Lookup.html  offline, self-contained copy with every table packed in
                           (log-quantised uint16 + gzip, at most 0.05 % error)

Run from the repository root after gen_lut.py:  python3 build_html.py
"""
import json, base64, gzip, glob, re, os, datetime
import numpy as np

SITE = "https://hidayeterenuludag.github.io/IHPSG13G2-LUT/"
REPO = "https://github.com/hidayetErenUludag/IHPSG13G2-LUT"
AUTHOR_URL = "https://github.com/hidayetErenUludag"
BUILD_DATE = datetime.date.today().isoformat()
VERSION = "1.2.0"
TITLE = "IHP SG13G2 gm/ID Lookup Tables & MOSFET Sizing Calculator"
# Search result snippet: keep under ~155 characters.
DESC = ("Free gm/ID lookup tables and MOSFET sizing calculator for the IHP SG13G2 130 nm open PDK. "
        "LV and HV NMOS/PMOS by finger width, with noise and mismatch.")
# Social cards get their own wording so link previews do not repeat the search snippet.
OG_DESC = ("Size SG13G2 MOSFETs from a gm/ID target and read the finger count, VGS, gm/gds, fT, capacitances, "
           "noise and mismatch in your browser, or compare two devices side by side. Free, open source, works offline.")
TW_DESC = "gm/ID sizing for IHP SG13G2: pick a device, L and finger width, get W, VGS, gain, fT, noise and offset."
KEYWORDS = ("gm/ID, gm/ID lookup table, IHP SG13G2, SG13G2 PDK, 130 nm BiCMOS, open-source PDK, analog IC design, "
            "MOSFET sizing, transistor sizing calculator, ngspice, PSP103")
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' rx='6' fill='%230C6B86'/%3E"
           "%3Cpath d='M6 24 C10 24 12 8 26 8' stroke='white' stroke-width='3' fill='none' stroke-linecap='round'/%3E%3C/svg%3E")
DEVICE_ROLE = {"sg13_lv_nmos": "1.2 V core NMOS", "sg13_lv_pmos": "1.2 V core PMOS",
               "sg13_hv_nmos": "3.3 V I/O NMOS", "sg13_hv_pmos": "3.3 V I/O PMOS"}

def strip_tags(h):
    return re.sub(r"<[^>]+>", "", h)


def jsonld(index):
    person = {"@type": "Person", "@id": AUTHOR_URL + "#person", "name": "Hidayet Eren Uludağ", "url": AUTHOR_URL,
              "sameAs": [AUTHOR_URL],
              "affiliation": {"@type": "CollegeOrUniversity", "name": "Özyeğin University", "url": "https://www.ozyegin.edu.tr/"}}
    openlut = {"@type": "ScholarlyArticle",
               "name": "Open-LUT: Interactive gm/ID Lookup Tables for MOSFET Sizing in Open-Source PDKs",
               "author": [{"@type": "Person", "name": n} for n in ("Sihawi A. Khalid", "Susie E. Maestre", "Karla M. Madrid-Khalid")],
               "datePublished": "2025", "sameAs": "https://doi.org/10.1109/ICICM66614.2025.11316023"}
    lic = "https://www.apache.org/licenses/LICENSE-2.0"
    dist = [{"@type": "DataDownload", "encodingFormat": "application/octet-stream",
             "name": os.path.basename(f), "contentUrl": SITE + f.replace(os.sep, "/")}
            for f in sorted(glob.glob("npz/lut_sg13_*.npz"))]
    dist.append({"@type": "DataDownload", "encodingFormat": "text/html", "name": "Offline calculator (single HTML file)",
                 "contentUrl": SITE + "SG13G2_gmID_Lookup.html"})
    return {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "@id": SITE + "#website", "url": SITE, "name": "SG13G2 gm/ID Lookup",
         "inLanguage": "en", "publisher": {"@id": AUTHOR_URL + "#person"}},
        {"@type": "WebApplication", "@id": SITE + "#app", "name": "SG13G2 gm/ID Lookup", "url": SITE,
         "description": DESC, "applicationCategory": "DesignApplication", "applicationSubCategory": "Analog IC design",
         "operatingSystem": "Any (web browser)", "browserRequirements": "Requires JavaScript",
         "isAccessibleForFree": True, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
         "softwareVersion": VERSION, "dateModified": BUILD_DATE, "license": lic, "inLanguage": "en",
         "keywords": KEYWORDS, "image": SITE + "preview.png", "screenshot": SITE + "preview.png",
         "author": {"@id": AUTHOR_URL + "#person"}, "isPartOf": {"@id": SITE + "#website"},
         "isBasedOn": openlut, "mainEntityOfPage": SITE},
        {"@type": "SoftwareSourceCode", "@id": REPO, "name": "IHPSG13G2-LUT", "codeRepository": REPO,
         "programmingLanguage": ["Python", "JavaScript"], "license": lic, "author": {"@id": AUTHOR_URL + "#person"},
         "targetProduct": {"@id": SITE + "#app"}},
        {"@type": "Dataset", "@id": SITE + "#dataset",
         "name": "IHP SG13G2 gm/ID MOSFET lookup tables (ngspice PSP103, mos_tt, 27 °C)",
         "description": ("Pre-computed DC operating-point lookup tables for the four MOSFETs of the IHP SG13G2 130 nm BiCMOS "
                         "open-source PDK (sg13_lv_nmos, sg13_lv_pmos, sg13_hv_nmos, sg13_hv_pmos), for gm/ID-based analog "
                         "transistor sizing. Each table sweeps VGS and VDS for every channel length at finger widths of 0.5, 1, 2, "
                         "5 and 10 µm (single finger, ng = 1), and stores ID, gm, gds, gmb, Vth, VDsat, Cgg, Cgs, Cgd and Cdd, "
                         "plus drain thermal and flicker noise PSDs in the NumPy files. Simulated in ngspice-47 with the PSP103 "
                         "model, typical corner mos_tt, 27 °C, VSB = 0; checked against direct simulation within 3 % for ID, gm "
                         "and gds."),
         "url": SITE, "sameAs": REPO, "license": lic, "isAccessibleForFree": True, "version": VERSION,
         "dateModified": BUILD_DATE, "creator": {"@id": AUTHOR_URL + "#person"},
         "keywords": ["gm/ID", "lookup table", "IHP SG13G2", "MOSFET", "analog IC design", "open-source PDK", "PSP103", "ngspice"],
         "measurementTechnique": "ngspice-47 DC operating-point sweep of the IHP-Open-PDK PSP103 MOSFET models",
         "variableMeasured": ["drain current ID", "transconductance gm", "output conductance gds", "body transconductance gmb",
                              "threshold voltage Vth", "saturation voltage VDsat", "gate capacitance Cgg", "Cgs", "Cgd", "Cdd",
                              "drain thermal-noise PSD", "flicker-noise PSD at 1 Hz"],
         "isBasedOn": "https://github.com/IHP-GmbH/IHP-Open-PDK", "distribution": dist},
    ]}


def head(title, canonical, index, extra=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{DESC}">
<meta name="author" content="Hidayet Eren Uludağ">
<meta name="keywords" content="{KEYWORDS}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">
<link rel="canonical" href="{canonical}">
<link rel="author" href="{AUTHOR_URL}">
<link rel="icon" href="{FAVICON}">
<link rel="alternate" type="text/plain" href="{SITE}llms.txt" title="Plain-text summary for language models">
<meta name="theme-color" content="#F3F6F8" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0C1218" media="(prefers-color-scheme: dark)">
<meta property="og:type" content="website">
<meta property="og:locale" content="en_US">
<meta property="og:site_name" content="SG13G2 gm/ID Lookup">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{OG_DESC}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{SITE}preview.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="SG13G2 gm/ID lookup charts: ID/W, intrinsic gain, fT and VGS versus gm/ID">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{TW_DESC}">
<meta name="twitter:image" content="{SITE}preview.png">
<meta name="twitter:image:alt" content="SG13G2 gm/ID lookup charts: ID/W, intrinsic gain, fT and VGS versus gm/ID">
<script type="application/ld+json">{json.dumps(jsonld(index), ensure_ascii=False, separators=(",", ":"))}</script>
{extra}"""


# ---------- static content rendered at build time (readable without JavaScript) ----------
def _nearest(arr, x):
    return min(range(len(arr)), key=lambda i: abs(arr[i] - x))


def ref_points(index, wf=1.0, targets=(5, 10, 15, 20, 25)):
    """Mirror of the page's solve(): strong-inversion side of the gm/ID peak, linear interpolation along VGS."""
    rows = []
    for dev, dv in index["devices"].items():
        j = json.load(open(f"web/{dev}_wf{wf:g}.json"))
        a = {k: np.frombuffer(base64.b64decode(v), dtype=np.float32).astype(np.float64) for k, v in j["data"].items()}
        nG, nD = len(dv["vgs"]), len(dv["vds"])
        k = _nearest(dv["L"], 1.0 if "hv" in dev else 0.5); jj = _nearest(dv["vds"], dv["vmax"] / 2)
        at = lambda key, i: a[key][(k * nG + i) * nD + jj]
        pts = [i for i in range(nG) if at("id", i) > 1e-13]
        gmid = [at("gm", i) / at("id", i) for i in pts]
        pk = int(np.argmax(gmid)); pts, gmid = pts[pk:], gmid[pk:]
        out = []
        for t in targets:
            if not (gmid[-1] <= t <= gmid[0]): continue
            n = next(n for n in range(len(pts) - 1) if gmid[n] >= t >= gmid[n + 1])
            f = 0 if gmid[n] == gmid[n + 1] else (gmid[n] - t) / (gmid[n] - gmid[n + 1])
            L = lambda key: at(key, pts[n]) + (at(key, pts[n + 1]) - at(key, pts[n])) * f
            vgs = dv["vgs"][pts[n]] + (dv["vgs"][pts[n + 1]] - dv["vgs"][pts[n]]) * f
            idw = L("id") / (wf * 1e-6)          # A/m, numerically equal to µA/µm
            out.append(dict(gmid=t, vgs=vgs, vth=L("vth"), idw=idw, gain=L("gm") / L("gds"),
                            ft=L("gm") / (2 * np.pi * L("cgg"))))
        rows.append(dict(dev=dev, L=dv["L"][k], vds=dv["vds"][jj], pts=out))
    return rows


def _ft(x):
    return f"{x/1e9:.2f} GHz" if x >= 1e9 else f"{x/1e6:.0f} MHz"


def _idw(x):
    return f"{x:.3g}"


def ref_table_html(rows):
    h = ['<div class="tablewrap"><table class="ref">',
         '<caption>W<sub>f</sub> = 1 µm, mos_tt, 27 °C, V<sub>SB</sub> = 0. L and |V<sub>DS</sub>| as listed per device '
         '(the calculator defaults). PMOS values are magnitudes. Linear interpolation along V<sub>GS</sub>.</caption>',
         '<thead><tr><th scope="col">g<sub>m</sub>/I<sub>D</sub> (S/A)</th><th scope="col">|V<sub>GS</sub>| (V)</th>'
         '<th scope="col">|V<sub>th</sub>| (V)</th><th scope="col">I<sub>D</sub>/W (µA/µm)</th>'
         '<th scope="col">g<sub>m</sub>/g<sub>ds</sub> (V/V)</th><th scope="col">f<sub>T</sub></th></tr></thead>']
    for r in rows:
        h.append(f'<tbody><tr class="grp"><th colspan="6" scope="rowgroup">{r["dev"]} '
                 f'<span>· {DEVICE_ROLE[r["dev"]]} · L = {r["L"]:.2f} µm · |V<sub>DS</sub>| = {r["vds"]:.2f} V</span></th></tr>')
        for p in r["pts"]:
            h.append(f'<tr><td>{p["gmid"]}</td><td>{p["vgs"]:.3f}</td><td>{p["vth"]:.3f}</td><td>{_idw(p["idw"])}</td>'
                     f'<td>{p["gain"]:.1f}</td><td>{_ft(p["ft"])}</td></tr>')
        h.append('</tbody>')
    h.append('</table></div>')
    return "\n".join(h)


def llms_txt(rows):
    t = [f"# SG13G2 gm/ID Lookup", "",
         f"> {DESC}", "",
         f"Interactive page: {SITE}", f"Source and data: {REPO}", f"Offline calculator: {SITE}SG13G2_gmID_Lookup.html",
         f"Author: Hidayet Eren Uludağ, Özyeğin University. License: Apache-2.0. Updated {BUILD_DATE}.", "",
         "## What it does",
         "Sizes IHP SG13G2 MOSFETs from a gm/ID target. Inputs: device, |VDS|, channel length L, finger width Wf, gm/ID, "
         "and one of ID, gm or total W. Outputs: finger count ng x Wf, W, ID, gm, gds, gmb, VGS, Vth, Vov, VDsat, "
         "gm/gds, intrinsic gain in dB, fT, Cgg/Cgs/Cgd/Cdd; noise (gamma, flicker corner, input-referred noise density "
         "and band-integrated rms); and mismatch from the PDK model (sigma Vth, sigma ID/ID, pair offset, mirror error). "
         "A second configuration B can be compared side by side.", "",
         "## Conditions",
         "ngspice-47, PSP103 models from IHP-Open-PDK, corner mos_tt, 27 C, VSB = 0, single-finger devices (ng = 1) at "
         "Wf = 0.5, 1, 2, 5, 10 um. Size by fingers, not total width: LV device characteristics depend on finger width.", "",
         "## Accuracy",
         "Versus direct ngspice simulation of sized devices: ID, gm, gds within 3 %; fT within 8 %. Simulation only, "
         "not measured silicon.", "",
         "## Reference values (Wf = 1 um)"]
    for r in rows:
        t.append(f"\n### {r['dev']} ({DEVICE_ROLE[r['dev']]}), L = {r['L']:.2f} um, |VDS| = {r['vds']:.2f} V")
        t.append("| gm/ID (S/A) | VGS (V) | Vth (V) | ID/W (uA/um) | gm/gds | fT |")
        t.append("|---|---|---|---|---|---|")
        for p in r["pts"]:
            t.append(f"| {p['gmid']} | {p['vgs']:.3f} | {p['vth']:.3f} | {_idw(p['idw'])} | {p['gain']:.1f} | {_ft(p['ft'])} |")
    t += ["", "## Cite", "Khalid, Maestre and Madrid-Khalid, \"Open-LUT: Interactive gm/ID Lookup Tables for MOSFET Sizing "
          "in Open-Source PDKs,\" ICICM 2025, doi:10.1109/ICICM66614.2025.11316023; and this repository (CITATION.cff)."]
    return "\n".join(t) + "\n"


def sitemap_xml():
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
  <url>
    <loc>{SITE}</loc>
    <lastmod>{BUILD_DATE}</lastmod>
    <image:image><image:loc>{SITE}preview.png</image:loc></image:image>
  </url>
</urlset>
"""


def async_fonts(styles):
    """Load the Google Fonts stylesheet without blocking first paint (display=optional avoids a later swap)."""
    m = re.search(r'<link rel="stylesheet" href="(https://fonts.googleapis.com/[^"]+)">', styles)
    if not m:
        return styles
    url = m.group(1)
    return styles.replace(m.group(0),
        f'<link rel="preload" as="style" href="{url}" onload="this.onload=null;this.rel=\'stylesheet\'">\n'
        f'<noscript><link rel="stylesheet" href="{url}"></noscript>')


def online_boot(script, index):
    """Inline web/index.json so the first table request starts immediately."""
    a = script.index('fetch("web/index.json")'); b = script.index(".catch(err=>")
    return (script[:a] + 'Promise.resolve(' + json.dumps(index, separators=(",", ":")) + ').then(j=>{\n'
            '  LUT=j; setDevice($("#dev").value); return useSet();\n})' + script[b:])


def split_source(html):
    """sg13g2_lut.html is a body fragment: <title>, fonts/<style>, markup, <script>."""
    html = re.sub(r"<title>.*?</title>\n?", "", html, count=1)
    if "<!--BODY-->" in html:
        styles, rest = html.split("<!--BODY-->", 1); lead = ""
    else:
        styles, rest = html.split('<div class="wrap">', 1); lead = '<div class="wrap">'
    markup, script = rest.split("<script>", 1)
    styles = styles.replace("body{background:var(--ground)", "body{margin:0;background:var(--ground)")
    return styles, lead + markup, script


ICON_PLAY = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>'
ICON_DL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4v11M7 10l5 5 5-5M5 20h14"/></svg>'
ICON_GH = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m8 9-4 3 4 3M16 9l4 3-4 3"/></svg>'


def add_links(markup, offline_link, rows):
    btns = f'<a class="btn primary" href="#calc">Open the calculator {ICON_PLAY}</a>'
    if offline_link:
        btns += f'<a class="btn" href="SG13G2_gmID_Lookup.html" download>{ICON_DL} Offline version ({OFFLINE_MB} MB)</a>'
    btns += f'<a class="btn" href="{REPO}">{ICON_GH} Source and data</a>'
    return (markup.replace("<!--LINKS-->", f'<div class="ctas">{btns}</div>', 1)
                  .replace("<!--REFTABLE-->", ref_table_html(rows), 1)
                  .replace("<!--UPDATED-->", f"Version {VERSION} · tables built with ngspice-47 and PSP103 · page updated "
                           f'<time datetime="{BUILD_DATE}">{BUILD_DATE}</time>', 1))


def pack_tables():
    pack, maxerr = {}, 0.0
    for f in sorted(glob.glob("web/sg13_*.json")):
        j = json.load(open(f)); key = f"{j['dev']}_wf{j['wf']:g}"
        keys = list(j["data"]); lohi = []; planes = []; n = 0
        for k in keys:
            a = np.frombuffer(base64.b64decode(j["data"][k]), dtype=np.float32).astype(np.float64); n = a.size
            la = np.log10(np.maximum(np.abs(a), 1e-30)); lo, hi = float(la.min()), float(la.max())
            if hi == lo: hi = lo + 1
            q = np.round((la - lo) / (hi - lo) * 65535).astype(np.int64)
            z = (np.diff(q, prepend=0) % 65536).astype(np.uint16)
            qq = np.cumsum(z.astype(np.int64)) % 65536; assert (qq == q).all()
            r = 10 ** (lo + qq / 65535 * (hi - lo)); m = np.abs(a) > 1e-25
            maxerr = max(maxerr, float(np.max(np.abs(r[m] / np.abs(a[m]) - 1))))
            planes.append((z >> 8).astype(np.uint8).tobytes() + (z & 255).astype(np.uint8).tobytes()); lohi.append([lo, hi])
        pack[key] = {"n": n, "keys": keys, "lohi": lohi, "b64": base64.b64encode(gzip.compress(b"".join(planes), 9)).decode()}
    print(f"packed {len(pack)} tables, max rel err {maxerr:.2e}")
    return pack


OFFLINE_LOAD = '''async function loadSet(name,wf){
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

OFFLINE_MB = "?"

def build(pack):
    src = open("sg13g2_lut.html", encoding="utf-8").read()
    styles, markup, script = split_source(src)

    # 1) online page
    index = json.load(open("web/index.json"))
    styles = async_fonts(styles)
    preload = '<link rel="preload" href="web/sg13_lv_nmos_wf1.json" as="fetch" type="application/json" crossorigin="anonymous">\n'
    rows = ref_points(index)
    NOSCRIPT = ('<noscript><p style="max-width:1240px;margin:0 auto 24px;padding:0 20px">The interactive calculator needs '
                'JavaScript. The reference values, method notes and downloadable tables on this page work without it.</p></noscript>\n')
    online = (head(TITLE, SITE, index, preload) + styles + "</head>\n<body>\n" + add_links(markup, True, rows)
              + NOSCRIPT + '<script>'
              + online_boot(script, index) + "\n</body>\n</html>\n")
    open("index.html", "w", encoding="utf-8").write(online)

    # 2) offline page
    s = script.replace(script[script.index("async function loadSet(name,wf){"):script.index("async function useSet(")], OFFLINE_LOAD)
    s = s.replace(s[s.index('fetch("web/index.json")'):s.index(".catch(err=>")],
                  '''Promise.resolve(INDEX).then(j=>{
  if(typeof DecompressionStream==="undefined") throw new Error("this browser is too old; use a current Chrome, Edge, Firefox or Safari");
  LUT=j; setDevice($("#dev").value); return useSet();
})''')
    m = markup.replace("Every value comes from", "This file is self-contained and works offline; values are stored "
                       "log-quantised to 16 bits (at most 0.05 % error). Every value comes from")
    offline = (head(TITLE, SITE, index) + styles + "</head>\n<body>\n" + add_links(m, False, rows)
               + "<script>\nconst INDEX=" + json.dumps(index, separators=(",", ":")) + ";\nconst PACK="
               + json.dumps(pack, separators=(",", ":")) + ";\n</script>\n<script>" + s + "\n</body>\n</html>\n")
    open("SG13G2_gmID_Lookup.html", "w", encoding="utf-8").write(offline)

    open("sitemap.xml", "w", encoding="utf-8").write(sitemap_xml())
    open("llms.txt", "w", encoding="utf-8").write(llms_txt(rows))



if __name__ == "__main__":
    pack = pack_tables()
    for guess in (f"{len(json.dumps(pack, separators=(',', ':')))/1e6 + 0.15:.1f}", None):
        OFFLINE_MB = guess or f"{os.path.getsize('SG13G2_gmID_Lookup.html')/1e6:.1f}"
        build(pack)
        if f"{os.path.getsize('SG13G2_gmID_Lookup.html')/1e6:.1f}" == OFFLINE_MB:
            break
    for f in ("index.html", "SG13G2_gmID_Lookup.html", "llms.txt"):
        print(f"{f}: {os.path.getsize(f)/1e6:.2f} MB")
