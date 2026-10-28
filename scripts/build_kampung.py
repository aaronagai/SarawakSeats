#!/usr/bin/env python3
"""Build data/kampung.json: every lokaliti (kampung, rumah panjang, taman,
jalan) in each polling district of the 82 seats, from SPR's own lists.

Below the polling district (daerah mengundi, DM), SPR registers every voter to
a lokaliti, the unit printed on a MySPR Semak slip. SPR does not publish the
lokaliti on their own, but each monthly Daftar Pemilih Tambahan (supplementary
roll) opens every polling district that gained a voter with its full "Senarai
Lokaliti": every lokaliti in that district, numbered 001, 002, ..., including
those with no new voter that month. Two rolls are online:

  Ogos 2026       gazetted 25 September 2026
  September 2026  gazetted 22 October 2026

Between them they open 863 of the 887 polling districts. The other 24 gained
no voter in either month, so their lists are not published yet; a later
month's roll adds them (add the month to MONTHS and re-run).

Only the Senarai Lokaliti pages are read. The pages that follow, listing the
new voters by name, are skipped: nothing about any person leaves the PDFs.
SPR does not publish electors per lokaliti, so the one count kept is the new
voters each lokaliti gained over the months read.

Checks, all failing loudly: lokaliti numbers run without a break in each list
(the few gaps are identical in every month: codes SPR has retired), each list's
new voters sum to SPR's JUMLAH for that district, every month that opens a
district lists the same lokaliti, and every district is one of the site's 887.

Codes 301 and up are police and army lokaliti (barracks, "BEKAS POLIS"); they
are kept and marked as such. Absent-voter (PTH) entries are not places, and
are left out.

Positions: a lokaliti is placed on the map only when its name, with SPR's
abbreviations expanded (KG, SG, RH, JLN, ...), exactly matches a named place
or road in OpenStreetMap that lies inside the lokaliti's own seat, and the
matches do not lie more than ~2 km apart. About one in eight qualify; most of
the rest are rumah panjang known by their Tuai Rumah's name, which OSM does
not carry. Positions are approximate and derived from OSM (ODbL).

Output: {"months": [...], "dm": {"192/01/01": [[code, name, new, lon?, lat?], ...]}}

Usage: python3 scripts/build_kampung.py      (needs PyMuPDF and shapely;
       downloads into .cache/kampung/ on first run)
"""
import collections, json, os, re, sys, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".cache", "kampung")
OUT = os.path.join(ROOT, "data", "kampung.json")
MONTHS = [("8Ogos", "Ogos 2026", "25 Sep 2026"), ("9September", "September 2026", "22 Okt 2026")]
DPT = "https://sprinfo.spr.gov.my/spr/DPT/%s/SARAWAK/P%d.pdf"
MECO = ("https://raw.githubusercontent.com/Thevesh/paper-meco-maps/main/"
        "data/geojson/delimitations/sarawak_2015_dun.geojson")
OVERPASS = "https://overpass-api.de/api/interpreter"
UA = {"User-Agent": "SarawakSeats/1.0 (https://sarawakseats.org)"}

def fetch(url, path, data=None):
    if os.path.exists(path) and os.path.getsize(path): return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    print("downloading", url)
    req = urllib.request.Request(url, data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=600) as r, open(path + ".part", "wb") as f: f.write(r.read())
    os.replace(path + ".part", path)
    return path

page = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
D = json.loads(re.search(r'<script>const D=(\{.*?\});?</script>', page, re.S).group(1))
dm2seat = {x[0]: s for s, l in D["pd82"].items() for x in l}

# ---- SPR: the Senarai Lokaliti of every polling district each roll opens ----
import fitz   # PyMuPDF
SECT = {"PENGUNDI BIASA": "b", "PENGUNDI TIDAK HADIR (PTH) POLIS": "p", "PENGUNDI TIDAK HADIR (PTH) TENTERA": "t"}
num = lambda s: re.fullmatch(r"[\d,]+", s)
lists = collections.defaultdict(dict)   # dm -> month -> {code: [name, new]}
fail = []
for month, _, _ in MONTHS:
    for p in range(192, 223):
        pdf = fetch(DPT % (month, p), os.path.join(CACHE, month, "P%d.pdf" % p))
        state = {}
        for pg in fitz.open(pdf):
            t = pg.get_text()
            if not t.startswith("SENARAI LOKALITI"): continue
            L = [l.strip() for l in t.split("\n") if l.strip()]
            dm = L[L.index("DAERAH MENGUNDI (UNIT PENDAFTARAN)") + 1].lstrip(": ").split()[0]
            body = L[[i for i, l in enumerate(L) if l.startswith("©")][0] + 1:]
            s = state.setdefault(dm, {"sec": None, "rows": {}, "tot": None})
            i = 0
            while i < len(body):
                l = body[i]
                if l in SECT: s["sec"] = SECT[l]; i += 1; continue
                if l.startswith("JUMLAH"):
                    if l == "JUMLAH PENGUNDI BIASA": s["tot"] = int(body[i + 1].replace(",", ""))
                    i += 2; continue
                if s["sec"] and re.fullmatch(r"\d{3}", l):
                    j, name = i + 1, []
                    while not num(body[j]): name.append(body[j]); j += 1
                    new = int(body[j].replace(",", ""))
                    if s["sec"] == "b": s["rows"][int(l)] = [" ".join(name), new]
                    i = j + (2 if new else 1)   # a lokaliti with new voters also gives their page
                    continue
                fail.append("%s %s: unread line %r" % (month, dm, l)); i += 1
        for dm, s in state.items():
            if dm not in dm2seat: fail.append("%s %s: not one of the 887 polling districts" % (month, dm))
            if sum(v[1] for v in s["rows"].values()) != s["tot"]:
                fail.append("%s %s: lokaliti sum to %d, SPR's total %s" % (month, dm, sum(v[1] for v in s["rows"].values()), s["tot"]))
            lists[dm][month] = s["rows"]

gaps = collections.Counter()
for dm, by in lists.items():
    names = [{c: v[0] for c, v in rows.items()} for rows in by.values()]
    if any(n != names[0] for n in names): fail.append("%s: the months list different lokaliti" % dm)
    civil = sorted(c for c in names[0] if c < 300)
    if civil and civil != list(range(1, civil[-1] + 1)): gaps[dm] = civil[-1] - len(civil)
if fail:
    print("\n%d FAILED:" % len(fail)); print("\n".join("  " + f for f in fail[:50])); sys.exit(1)

# ---- OSM: an approximate position, for names that match exactly inside their seat ----
from shapely.geometry import shape, Point
from shapely.prepared import prep
seatpoly = {f["properties"]["code_dun"]: prep(shape(f["geometry"]).buffer(0.01))   # ~1 km of slack at the border
            for f in json.load(open(fetch(MECO, os.path.join(CACHE, "sarawak_2015_dun.geojson"))))["features"]}
Q = """[out:json][timeout:300];
area["name"="Sarawak"]["admin_level"="4"]->.s;
(nwr["place"~"^(village|hamlet|isolated_dwelling|neighbourhood|suburb|quarter|locality|town|city)$"](area.s);
 nwr["building"="longhouse"]["name"](area.s);
 nwr["landuse"="residential"]["name"](area.s);
 way["highway"]["name"](area.s););
out center tags;"""
osm = json.load(open(fetch(OVERPASS, os.path.join(CACHE, "osm-sarawak.json"),
                           urllib.parse.urlencode({"data": Q}).encode())))["elements"]

AB = {"KG": "KAMPUNG", "KPG": "KAMPUNG", "KAMPONG": "KAMPUNG", "SG": "SUNGAI", "SUNGEI": "SUNGAI",
      "RH": "RUMAH", "JLN": "JALAN", "JL": "JALAN", "LRG": "LORONG", "LOR": "LORONG", "TMN": "TAMAN",
      "BKT": "BUKIT", "LBK": "LUBOK", "LUBUK": "LUBOK", "PKN": "PEKAN", "RD": "ROAD", "ST": "STREET",
      "BTG": "BATANG", "TG": "TANJUNG", "TANJONG": "TANJUNG", "TJG": "TANJUNG", "HULU": "ULU",
      "LG": "LONG", "PERUMAHAN": "TAMAN", "AK": "ANAK", "SRI": "SERI"}
GEN = {"KAMPUNG", "RUMAH", "TAMAN", "JALAN", "LORONG"}
def norm(s, bt=None):
    s = re.sub(r"\([^)]*\)", "", s.upper().replace("'", "").replace("`", ""))
    return " ".join(bt if (w == "BT" and bt) else AB.get(w, w) for w in re.sub(r"[^A-Z0-9]+", " ", s).split())
def core(n):
    w = n.split()
    while w and w[0] in GEN: w = w[1:]
    return " ".join(w)
idx = collections.defaultdict(list)
for e in osm:
    t = e.get("tags", {})
    c = e if "lat" in e else e.get("center")
    if not c: continue
    kind = "road" if "highway" in t else "place"
    for k in ("name", "name:ms", "alt_name", "old_name", "official_name"):
        for nm in t.get(k, "").split(";"):
            if not nm.strip(): continue
            v = norm(nm)
            idx[v].append((c["lat"], c["lon"], kind))
            if kind == "place" and core(v) != v: idx["~" + core(v)].append((c["lat"], c["lon"], kind))

def locate(name, poly):
    inside = lambda c: [x for x in c if poly.contains(Point(x[1], x[0]))]
    n = norm(name)
    bare = re.sub(r"\b(BAZAAR|BAZAR|PEKAN)$", "", n).strip()
    keys = [n, norm(name, "BUKIT"), norm(name, "BATU")]
    if bare and bare.split()[0] not in GEN: keys += ["KAMPUNG " + bare, bare]
    hit = next((h for h in (inside(idx.get(k, [])) for k in keys) if h), None)
    if not hit and n.split()[0] in ("KAMPUNG", "RUMAH", "TAMAN") and len(core(n)) >= 4:
        hit = [x for x in inside(idx.get("~" + core(n), []) + idx.get(core(n), [])) if x[2] == "place"]
    if not hit: return None
    la, lo = [x[0] for x in hit], [x[1] for x in hit]
    if max(max(la) - min(la), max(lo) - min(lo)) > 0.02: return None   # two places of that name: unsure
    return [round(sum(lo) / len(lo), 5), round(sum(la) / len(la), 5)]

out, placed, total, inst = {}, 0, 0, 0
for dm in sorted(lists):
    by = lists[dm]
    names = next(iter(by.values()))
    rows = []
    for code in sorted(names):
        name = names[code][0]
        new = sum(m.get(code, [0, 0])[1] for m in by.values())
        row = [code, name, new]
        if code < 300:
            total += 1
            pt = locate(name, seatpoly[dm2seat[dm]])
            if pt: row += pt; placed += 1
        else: inst += 1
        rows.append(row)
    out[dm] = rows

json.dump({"months": [[m[1], m[2]] for m in MONTHS], "dm": out}, open(OUT, "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
missing = sorted(set(dm2seat) - set(out))
print("wrote %s: %d polling districts, %d lokaliti (+%d police/army), %d placed on the map (%.0f%%)" %
      (OUT, len(out), total, inst, placed, placed / total * 100))
print("retired codes in %d districts; not yet published: %d districts, %s electors" %
      (len(gaps), len(missing), "{:,}".format(sum(x[2] for l in D["pd82"].values() for x in l if x[0] in missing))))
