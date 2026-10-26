#!/usr/bin/env python3
"""Build the seat map's boundaries, at two levels of detail (both TopoJSON):

  data/dun82-boundaries.json         simplified, for the statewide view (~115 KB gz)
  data/dun82-boundaries-detail.json  every vertex MECo has (~315,000, a point
                                     every ~27 m on median), loaded once the
                                     reader zooms in to a town or kampung

Source: MECo, the Malaysian Election Corpus — Thevananthan & Chacko, "Electoral
Maps and Cartograms from 1954 to 2025" (arXiv:2512.24211), released CC0 at
https://github.com/Thevesh/paper-meco-maps. Its `sarawak_2015_dun` layer is the
2015 delimitation: the 82 seats in force for the coming state election. MECo is
a digitisation of SPR's gazetted maps, not an SPR publication; it is fit for
showing where seats lie, not for assigning an individual voter to a seat (that
is MySPR Semak's job).

For the overview, the 82 DUN polygons are simplified with mapshaper, which simplifies shared
edges once so neighbouring seats never open slivers between them, and the 31
parliaments are dissolved from those same DUN polygons so every parliament
border sits exactly on a DUN border. Each seat also gets a label point inside it
(shapely's polylabel). Seat codes, names and parliaments were
checked against the 82-seat table in index.html: all 82 match.

Usage: python3 scripts/build_boundaries.py [path/to/sarawak_2015_dun.geojson]
       (downloads the MECo file when no path is given; needs node for npx)
"""
import json, os, re, subprocess, sys, tempfile, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SRC_URL = ("https://raw.githubusercontent.com/Thevesh/paper-meco-maps/main/"
           "data/geojson/delimitations/sarawak_2015_dun.geojson")
LEVELS = [
    # file, simplification, quantization
    ("dun82-boundaries.json", ["-simplify", "15%", "keep-shapes"], "1e6"),   # ~0.7 m grid
    ("dun82-boundaries-detail.json", [], "4e6"),                            # ~0.2 m grid
]

src = sys.argv[1] if len(sys.argv) > 1 else None
tmp = tempfile.mkdtemp()
if not src:
    src = os.path.join(tmp, "sarawak_2015_dun.geojson")
    print("downloading", SRC_URL)
    urllib.request.urlretrieve(SRC_URL, src)

# a label point per seat: the pole of inaccessibility of its largest part, which
# (unlike a centroid) always falls inside the seat, however it is shaped
from shapely.geometry import shape
from shapely.ops import polylabel
lab = {}
for f in json.load(open(src))["features"]:
    g = shape(f["geometry"])
    part = max(getattr(g, "geoms", [g]), key=lambda p: p.area)
    pt = polylabel(part, tolerance=0.0005)
    lab[f["properties"]["code_dun"]] = [round(pt.x, 4), round(pt.y, 4)]

# the seats in the page and the seats on the map must be the same 82
page = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
D = json.loads(re.search(r'<script>const D=(\{.*?\});?</script>', page, re.S).group(1))
want = {r[0]: D["par82"][r[2]][0] for r in D["d82"]}

for name, simplify, q in LEVELS:
    out = os.path.join(DATA, name)
    subprocess.run(["npx", "-y", "mapshaper@0.6.102", "-i", src, "name=dun", "-clean", *simplify,
                    "-filter-fields", "code_dun,code_parlimen",
                    "-dissolve", "fields=code_parlimen", "+", "name=par",
                    "-o", "format=topojson", "quantization=" + q, "target=dun,par", out],
                   check=True)
    topo = json.load(open(out))
    for g in topo["objects"]["dun"]["geometries"]:
        g["properties"]["lab"] = lab[g["properties"]["code_dun"]]
    json.dump(topo, open(out, "w"), separators=(",", ":"))
    geo = {g["properties"]["code_dun"]: g["properties"]["code_parlimen"]
           for g in topo["objects"]["dun"]["geometries"]}
    assert geo == want, "boundary seats differ from the 82-seat table: %s" % (
        set(geo.items()) ^ set(want.items()))
    print("wrote", out, os.path.getsize(out), "bytes;", len(geo), "seats,",
          len(topo["objects"]["par"]["geometries"]), "parliaments,",
          sum(len(a) for a in topo["arcs"]), "points")
