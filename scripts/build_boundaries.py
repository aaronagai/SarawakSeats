#!/usr/bin/env python3
"""Build the seat map's boundaries: data/dun82-boundaries.json (TopoJSON).

Source: MECo, the Malaysian Election Corpus — Thevananthan & Chacko, "Electoral
Maps and Cartograms from 1954 to 2025" (arXiv:2512.24211), released CC0 at
https://github.com/Thevesh/paper-meco-maps. Its `sarawak_2015_dun` layer is the
2015 delimitation: the 82 seats in force for the coming state election. MECo is
a digitisation of SPR's gazetted maps, not an SPR publication; it is fit for
showing where seats lie, not for assigning an individual voter to a seat (that
is MySPR Semak's job).

The 82 DUN polygons are simplified with mapshaper, which simplifies shared
edges once so neighbouring seats never open slivers between them, and the 31
parliaments are dissolved from those same DUN polygons so every parliament
border sits exactly on a DUN border. Seat codes, names and parliaments were
checked against the 82-seat table in index.html: all 82 match.

Usage: python3 scripts/build_boundaries.py [path/to/sarawak_2015_dun.geojson]
       (downloads the MECo file when no path is given; needs node for npx)
"""
import json, os, re, subprocess, sys, tempfile, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "dun82-boundaries.json")
SRC_URL = ("https://raw.githubusercontent.com/Thevesh/paper-meco-maps/main/"
           "data/geojson/delimitations/sarawak_2015_dun.geojson")
SIMPLIFY = "15%"   # ~114 KB gzipped; keeps Kuching's small urban seats legible

src = sys.argv[1] if len(sys.argv) > 1 else None
tmp = tempfile.mkdtemp()
if not src:
    src = os.path.join(tmp, "sarawak_2015_dun.geojson")
    print("downloading", SRC_URL)
    urllib.request.urlretrieve(SRC_URL, src)

subprocess.run(["npx", "-y", "mapshaper@0.6.102", "-i", src, "name=dun", "-clean",
                "-simplify", SIMPLIFY, "keep-shapes",
                "-filter-fields", "code_dun,code_parlimen",
                "-dissolve", "fields=code_parlimen", "+", "name=par",
                "-o", "format=topojson", "quantization=1e6", "target=dun,par", OUT],
               check=True)

# the seats in the page and the seats on the map must be the same 82
page = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
D = json.loads(re.search(r'<script>const D=(\{.*?\});?</script>', page, re.S).group(1))
topo = json.load(open(OUT))
geo = {g["properties"]["code_dun"]: g["properties"]["code_parlimen"]
       for g in topo["objects"]["dun"]["geometries"]}
want = {r[0]: D["par82"][r[2]][0] for r in D["d82"]}
assert geo == want, "boundary seats differ from the 82-seat table: %s" % (
    set(geo.items()) ^ set(want.items()))
print("wrote", OUT, os.path.getsize(OUT), "bytes;", len(geo), "seats,",
      len(topo["objects"]["par"]["geometries"]), "parliaments")
