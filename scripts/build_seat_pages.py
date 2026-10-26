#!/usr/bin/env python3
"""Give every seat and parliament its own address.

Writes a one-file stub at /N.16/, /P.219/, /82/, /82/N.16/, /82/P.219/ for each
seat and parliament in both maps. Each stub carries that seat's own title and
link preview (electors, parliament, where it draws from) and bounces straight
to the app, which then shows the same path in the address bar. So a saved or
pasted link like sarawakseats.org/N.16/ previews as that seat and opens on it.
Also writes 404.html, which catches near-misses (n16, N16, n.16) and forwards them.

While the 99-seat proposal is shelved (`var PROPOSAL=false` in index.html), the
82 seats take the short addresses (/N.16/ is the current N.16) and no proposal
pages are written. The old /82/... addresses are kept as stubs that open the
same seat, so links already shared keep working.

Usage: python3 scripts/build_seat_pages.py   (run after build_changes.py)
"""
import json, re, os, shutil, html
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
page = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
D = json.loads(re.search(r'<script>const D=(\{.*?\});?</script>', page, re.S).group(1))
SITE = "https://sarawakseats.org"
PROPOSAL = re.search(r"var PROPOSAL=(true|false);", page).group(1) == "true"

def fmt(n): return "{:,}".format(n)
def esc(s): return html.escape(s, quote=True)

def stub(path, title, desc):
    url = SITE + path
    return f'''<!doctype html><html lang="ms"><head><meta charset="utf-8">
<title>{esc(title)} — SarawakSeats</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{esc(desc)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{SITE}/og-image.png">
<meta property="og:url" content="{url}">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{url}">
<meta http-equiv="refresh" content="0; url=/?go={esc(path)}">
<script>location.replace("/?go="+encodeURIComponent({json.dumps(path)})+location.hash)</script>
</head><body><p><a href="/?go={esc(path)}">{esc(title)}</a></p></body></html>
'''

def write(path, content):
    d = os.path.join(ROOT, path.strip("/"))
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(content)

# clear previously generated stubs (any top-level N.xx / P.xxx dir, and /82)
for name in os.listdir(ROOT):
    if re.match(r"^(N\.\d{2}|P\.\d{3}|82)$", name): shutil.rmtree(os.path.join(ROOT, name))

if PROPOSAL:
    SETS = [("99", D["d99"], D["par"], D["pd"], ["/"], "Cadangan 99 DUN Sarawak 2026"),
            ("82", D["d82"], D["par82"], D["pd82"], ["/82/"], "DUN Sarawak semasa (82)")]
else:
    SETS = [("82", D["d82"], D["par82"], D["pd82"], ["/", "/82/"], "PRN Sarawak · 82 DUN")]

def pages(setkey, seats, pars, pd, setname):
    """(path, title, description) for the set's home, every seat and every parliament."""
    chg = D["chg"]["p"] if setkey == "99" else D["chg"]["c"]
    out = []
    if setkey == "82":
        out.append(("", setname, "%s pengundi, %d DUN, %d daerah mengundi, peta sempadan dan demografi setiap kerusi." % (
            fmt(sum(r[4] for r in seats)), len(seats), sum(len(v) for v in pd.values()))))
    for r in seats:
        code, name, pi, npd, v = r[0], r[1], r[2], r[3], r[4]
        par = pars[pi]; e = chg.get(code, {})
        title = "%s %s%s" % (code, name, " (Baharu)" if e.get("new") else "")
        bits = ["%s pengundi" % fmt(v), "%s %s" % (par[0], par[1]), "%d daerah mengundi" % npd]
        if e.get("s") and setkey == "99":
            src = ", ".join("%s %d%%" % (x[1], round(100 * x[4] / e["t"])) for x in e["s"][:3])
            bits.append(("Kerusi baharu, diambil daripada " if e.get("new") else "Diambil daripada ") + src)
        elif e.get("s") and PROPOSAL:
            dst = ", ".join("%s %d%%" % (x[1], round(100 * x[4] / e["t"])) for x in e["s"][:3])
            bits.append("Beralih kepada " + dst)
        out.append((code + "/", title + " · " + setname, " · ".join(bits)))
    by_par = defaultdict(list)
    for r in seats: by_par[r[2]].append(r)
    for pi, par in enumerate(pars):
        rows = by_par[pi]
        out.append((par[0] + "/", "%s %s · %s" % (par[0], par[1], setname),
                    "%s pengundi · %d DUN: %s" % (fmt(sum(r[4] for r in rows)), len(rows),
                    ", ".join("%s %s" % (r[0], r[1]) for r in rows))))
    return out

n = 0
if PROPOSAL:
    for rel, title, desc in pages("99", D["d99"], D["par"], D["pd"], "Cadangan 99 DUN Sarawak 2026"):
        if rel: write("/" + rel, stub("/" + rel, title, desc)); n += 1
    for rel, title, desc in pages("82", D["d82"], D["par82"], D["pd82"], "DUN Sarawak semasa (82)"):
        write("/82/" + rel, stub("/82/" + rel, title, desc)); n += 1
else:
    # the 82 seats own the short addresses; /82/... stays as an alias of the same page
    for rel, title, desc in pages("82", D["d82"], D["par82"], D["pd82"], "PRN Sarawak · 82 DUN"):
        if rel: write("/" + rel, stub("/" + rel, title, desc)); n += 1
        write("/82/" + rel, stub("/" + rel, title, desc)); n += 1

open(os.path.join(ROOT, "404.html"), "w", encoding="utf-8").write('''<!doctype html><html lang="ms"><head><meta charset="utf-8">
<title>SarawakSeats</title>
<meta name="robots" content="noindex">
<script>
// /n16, /N16, /n.16, /p219, /82/n16 ... -> the app, which reads the seat from the path
(function(){
  var parts=location.pathname.split("/").filter(Boolean), out=[];
  if (parts[0]==="82"){ out.push("82"); parts.shift() }
  var m=/^([np])\\.?(\\d{2,3})$/i.exec(parts[0]||"");
  if (m){ var k=m[1].toUpperCase(); out.push(k+"."+(k==="N" ? ("0"+m[2]).slice(-2) : m[2])) }
  var path="/"+out.join("/")+(out.length?"/":"");
  location.replace("/?go="+encodeURIComponent(path)+location.hash);
})();
</script></head><body><p><a href="/">SarawakSeats</a></p></body></html>
''')
open(os.path.join(ROOT, ".nojekyll"), "w").close()
print("wrote", n, "stub pages, 404.html, .nojekyll")
