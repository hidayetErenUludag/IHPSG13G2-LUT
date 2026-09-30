#!/usr/bin/env python3
"""Build the two published pages from sg13g2_lut.html (page body) and web/*.json (tables).

  index.html               online page for GitHub Pages; loads web/*.json on demand (~1.3 MB per table)
  SG13G2_gmID_Lookup.html  offline, self-contained copy with every table packed in
                           (log-quantised uint16 + gzip, at most 0.05 % error)

Run from the repository root after gen_lut.py:  python3 build_html.py
"""
import json, base64, gzip, glob, re, os
import numpy as np

SITE = "https://hidayeterenuludag.github.io/IHPSG13G2-LUT/"
REPO = "https://github.com/hidayetErenUludag/IHPSG13G2-LUT"
TITLE = "SG13G2 gm/ID Lookup Tables | IHP 130 nm Open PDK"
DESC = ("Free interactive gm/ID lookup tables and MOSFET sizing calculator for the IHP SG13G2 130 nm "
        "BiCMOS open-source PDK. Size LV and HV NMOS/PMOS by finger width and read W, VGS, gm/gds, fT "
        "and capacitances from ngspice PSP103 sweeps.")
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' rx='6' fill='%230C6B86'/%3E"
           "%3Cpath d='M6 24 C10 24 12 8 26 8' stroke='white' stroke-width='3' fill='none' stroke-linecap='round'/%3E%3C/svg%3E")

JSONLD = {
    "@context": "https://schema.org",
    "@type": "WebApplication",
    "name": "SG13G2 gm/ID Lookup",
    "url": SITE,
    "description": DESC,
    "applicationCategory": "DesignApplication",
    "operatingSystem": "Any (web browser)",
    "isAccessibleForFree": True,
    "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
    "license": "https://www.apache.org/licenses/LICENSE-2.0",
    "codeRepository": REPO,
    "inLanguage": "en",
    "keywords": "gm/ID, lookup table, IHP SG13G2, 130 nm, BiCMOS, open-source PDK, analog IC design, MOSFET sizing, ngspice, PSP103",
    "image": SITE + "preview.png",
    "author": {"@type": "Person", "name": "Hidayet Eren Uludağ",
               "affiliation": {"@type": "CollegeOrUniversity", "name": "Özyeğin University"}},
    "isBasedOn": {"@type": "ScholarlyArticle",
                  "name": "Open-LUT: Interactive gm/ID Lookup Tables for MOSFET Sizing in Open-Source PDKs",
                  "author": ["Sihawi A. Khalid", "Susie E. Maestre", "Karla M. Madrid-Khalid"],
                  "datePublished": "2025",
                  "sameAs": "https://doi.org/10.1109/ICICM66614.2025.11316023"},
}


def head(title, canonical, extra=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{DESC}">
<meta name="author" content="Hidayet Eren Uludağ">
<meta name="keywords" content="{JSONLD['keywords']}">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="{FAVICON}">
<meta name="theme-color" content="#0C6B86">
<meta property="og:type" content="website">
<meta property="og:site_name" content="SG13G2 gm/ID Lookup">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{DESC}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{SITE}preview.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="SG13G2 gm/ID lookup charts: ID/W, intrinsic gain, fT and VGS versus gm/ID">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{DESC}">
<meta name="twitter:image" content="{SITE}preview.png">
<script type="application/ld+json">{json.dumps(JSONLD, ensure_ascii=False)}</script>
{extra}"""


def split_source(html):
    """sg13g2_lut.html is a body fragment: <title>, fonts/<style>, markup, <script>."""
    html = re.sub(r"<title>.*?</title>\n?", "", html, count=1)
    styles, rest = html.split('<div class="wrap">', 1)
    markup, script = rest.split("<script>", 1)
    styles = styles.replace("body{background:var(--ground)", "body{margin:0;background:var(--ground)")
    return styles, '<div class="wrap">' + markup, script


def add_links(markup, offline_link):
    links = f'<a href="{REPO}">Source on GitHub</a>'
    if offline_link:
        links += ' · <a href="SG13G2_gmID_Lookup.html" download>Offline version (single HTML file)</a>'
    return markup.replace(
        '<div class="cond" aria-label="Characterisation conditions">',
        f'<p class="links" style="margin:6px 0 0;font-size:13px">{links}</p>\n    '
        '<div class="cond" aria-label="Characterisation conditions">', 1)


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

if __name__ == "__main__":
    src = open("sg13g2_lut.html", encoding="utf-8").read()
    styles, markup, script = split_source(src)

    # 1) online page
    online = (head(TITLE, SITE) + styles + "</head>\n<body>\n" + add_links(markup, True)
              + '<noscript><p style="padding:16px">This calculator needs JavaScript.</p></noscript>\n<script>'
              + script + "\n</body>\n</html>\n")
    open("index.html", "w", encoding="utf-8").write(online)

    # 2) offline page
    index = json.load(open("web/index.json"))
    pack = pack_tables()
    s = script.replace(script[script.index("async function loadSet(name,wf){"):script.index("async function useSet(){")], OFFLINE_LOAD)
    s = s.replace(s[s.index('fetch("web/index.json")'):s.index(".catch(err=>")],
                  '''Promise.resolve(INDEX).then(j=>{
  if(typeof DecompressionStream==="undefined") throw new Error("this browser is too old; use a current Chrome, Edge, Firefox or Safari");
  LUT=j; buildCharts(); setDevice($("#dev").value); return useSet();
})''')
    m = markup.replace("Every value comes from", "This file is self-contained and works offline; values are stored "
                       "log-quantised to 16 bits (at most 0.05 % error). Every value comes from")
    offline = (head(TITLE, SITE) + styles + "</head>\n<body>\n" + add_links(m, False)
               + "<script>\nconst INDEX=" + json.dumps(index, separators=(",", ":")) + ";\nconst PACK="
               + json.dumps(pack, separators=(",", ":")) + ";\n</script>\n<script>" + s + "\n</body>\n</html>\n")
    open("SG13G2_gmID_Lookup.html", "w", encoding="utf-8").write(offline)

    for f in ("index.html", "SG13G2_gmID_Lookup.html"):
        print(f"{f}: {os.path.getsize(f)/1e6:.2f} MB")
