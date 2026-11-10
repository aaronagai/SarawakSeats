#!/usr/bin/env python3
"""Estimate locality outlines inside each seat.

Nobody publishes polling-district or locality boundaries, so this draws an
estimate: each kampung with a known position (OpenStreetMap's place of that
name, from build_kampung.py) gets the part of its seat that is nearer to it than
to any other positioned kampung in the same seat (a Voronoi cell, clipped to
the seat's MECo border). Cells of the same polling district are merged for the
district lines. Kampung with no position get no cell, and their area falls to
their neighbours, so these are approximate and the page says so.

Straight Voronoi edges read as a diagram, not a place, so the cells are bent
before they are clipped: the whole plane is pushed by a smooth, deterministic
noise field (a few octaves of sine waves, sized to the seat's cells), which
moves a shared edge identically for both cells beside it, so they still tile
with no gaps. The seat border is cut afterwards and stays exactly MECo's.
The wiggles are decoration, not data.

Output: one file per seat, data/localities/N.01.json, loaded only when that
seat is in focus:
  {"k": [[dm, kampung_code, [ring, ...]], ...],
   "d": [[dm, [ring, ...]], ...],
   "cov": [districts_with_a_point, districts]}
Rings are [[lng, lat], ...] rounded to 5 decimals.

Usage: python3 scripts/build_localities.py   (after build_kampung.py)
"""
import json, os, re
from shapely.geometry import Point, Polygon, MultiPolygon, MultiPoint, shape
from shapely.ops import unary_union
import shapely
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
topo = json.load(open(os.path.join(ROOT, "data", "dun82-boundaries-detail.json")))
kamp = json.load(open(os.path.join(ROOT, "data", "kampung.json")))["dm"]
page = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
D = json.loads(re.search(r'<script>const D=(\{.*?\});?</script>', page, re.S).group(1))

# ---- TopoJSON -> shapely ----
sx, sy = topo["transform"]["scale"]; tx, ty = topo["transform"]["translate"]
arcs = []
for a in topo["arcs"]:
    x = y = 0; pts = []
    for dx, dy in a:
        x += dx; y += dy
        pts.append((x * sx + tx, y * sy + ty))
    arcs.append(pts)
def ring(idx):
    out = []
    for i in idx:
        pts = arcs[i] if i >= 0 else arcs[~i][::-1]
        out.extend(pts if not out else pts[1:])
    return out
def geom(g):
    if g["type"] == "Polygon":
        return Polygon(ring(g["arcs"][0]), [ring(h) for h in g["arcs"][1:]])
    return MultiPolygon([Polygon(ring(p[0]), [ring(h) for h in p[1:]]) for p in g["arcs"]])
seat_geom = {g["properties"]["code_dun"]: geom(g).buffer(0) for g in topo["objects"]["dun"]["geometries"]}

def warp_field(seed, scale):
    """A smooth displacement field: four octaves of randomly oriented sine
    waves, the largest about one cell across. Gradient stays well under 1, so
    the plane is bent but never folded."""
    rng = np.random.default_rng(seed)
    waves = []
    amp, freq = 0.075 * scale, 1.0 / scale
    for _ in range(4):
        for _ in range(3):
            th = rng.uniform(0, np.pi); ph = rng.uniform(0, 2 * np.pi, 2)
            waves.append((amp / 3, freq * np.cos(th), freq * np.sin(th), ph))
        amp *= 0.4; freq *= 2.5
    def f(xy):
        x, y = xy[:, 0], xy[:, 1]
        dx = np.zeros_like(x); dy = np.zeros_like(y)
        for a, kx, ky, ph in waves:
            t = 2 * np.pi * (kx * x + ky * y)
            dx += a * np.sin(t + ph[0]); dy += a * np.sin(t + ph[1])
        return np.column_stack([x + dx, y + dy])
    return f

def rings_of(g, tol=0.0003):
    g = g.simplify(tol, preserve_topology=True)
    polys = [g] if g.geom_type == "Polygon" else [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]
    out = []
    for p in polys:
        if p.is_empty or p.area < 1e-9: continue
        out.append([[round(x, 5), round(y, 5)] for x, y in p.exterior.coords])
    return out

seats_out = {}
for code, dms in D["pd82"].items():
    sg = seat_geom.get(code)
    if sg is None: continue
    pts = {}                                  # one cell per position
    for d in dms:
        for r in kamp.get(d[0], []):
            if r[0] >= 300 or len(r) <= 4: continue
            key = (round(r[3], 5), round(r[4], 5))
            pts.setdefault(key, (d[0], r[0]))
    cov = len({v[0] for v in pts.values()})
    if len(pts) < 2:
        seats_out[code] = {"k": [], "d": [], "cov": [cov, len(dms)]}
        continue
    keys = list(pts)
    mp = MultiPoint([Point(k) for k in keys])
    cells = shapely.voronoi_polygons(mp, extend_to=sg.envelope.buffer(0.5))
    scale = (sg.area / len(keys)) ** 0.5            # a typical cell's width
    warp = warp_field(sum(ord(ch) * 31 ** i for i, ch in enumerate(code)) % 2**32, scale)
    seg, tol = scale / 60, scale / 500
    k_out, by_dm = [], {}
    for cell in cells.geoms:
        # each unclipped cell holds exactly one of the points
        hit = next((k for k in keys if cell.contains(Point(k))), None)
        if hit is None: continue
        bent = shapely.transform(shapely.segmentize(cell, seg), warp).buffer(0)
        clip = bent.intersection(sg)
        if clip.is_empty: continue
        dm, kc = pts[hit]
        rs = rings_of(clip, tol)
        if rs: k_out.append([dm, kc, rs])
        by_dm.setdefault(dm, []).append(clip)
    d_out = []
    for dm, parts in by_dm.items():
        rs = rings_of(unary_union(parts).buffer(0), tol)
        if rs: d_out.append([dm, rs])
    seats_out[code] = {"k": k_out, "d": d_out, "cov": [cov, len(dms)]}

outdir = os.path.join(ROOT, "data", "localities")
os.makedirs(outdir, exist_ok=True)
size = 0
for code, v in seats_out.items():
    fp = os.path.join(outdir, code + ".json")
    json.dump(v, open(fp, "w"), separators=(",", ":"))
    size += os.path.getsize(fp)
print("seats", len(seats_out), "cells", sum(len(v["k"]) for v in seats_out.values()),
      "total kB", size // 1024, "largest kB", max(os.path.getsize(os.path.join(outdir, c + ".json")) for c in seats_out) // 1024)
