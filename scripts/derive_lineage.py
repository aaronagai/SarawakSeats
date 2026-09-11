#!/usr/bin/env python3
"""Derive data/dm-lineage.json: for every proposed polling district, which current
seat(s) its electors were in, and how that was established.

Inputs: data/spr-peta-dm-2026.json (SPR's Peta & DM tables with their colour
coding, see scripts/extract_spr_tables.py) and the seat / polling-district tables
embedded in index.html. Pure Python; no dependencies.

Rules, in order (the README's table):
  same        non-purple district whose name and count also appear in the seat of the same name
  same-dun    non-purple district with no such match: re-cut or renamed inside its own seat
  moved       purple district whose name and count match a green district elsewhere
  remnant     purple district whose name is that of a district not otherwise accounted for
  map         new name; source seat read off SPR's Peta Asal map (old-seat code beside the label)
  inferred    new name; the only assignment that balances every current seat's total
  split       one district built from two current seats (amounts by subtraction)
"""
import json, re, sys, os, difflib
from collections import defaultdict, Counter
sys.setrecursionlimit(10000)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPR = json.load(open(os.path.join(ROOT, "data", "spr-peta-dm-2026.json")))["parliaments"]
html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
D = json.loads(re.search(r'<script>const D=(\{.*?\});?</script>', html, re.S).group(1))

def norm(n): return re.sub(r"[^A-Z0-9]", "", n.upper()).replace("TANJUNG", "TANJONG").replace("KAMPONG", "KAMPUNG")
def sim(a, b):
    a, b = norm(a), norm(b)
    if a == b: return 1.0
    if a in b or b in a: return 0.9
    return difflib.SequenceMatcher(None, a, b).ratio()
pn = lambda p: int(p.split(".")[1])
# federal constituencies that share a border (a moved district can only come from next door)
ADJ = {192:[193,194,196,198], 193:[192,194,195,197], 194:[192,193,195,196,198], 195:[193,194,196,197],
 196:[192,194,195,197,198], 197:[193,195,196,198,199,200], 198:[192,194,196,197,199], 199:[197,198,200,202],
 200:[197,199,201,202], 201:[200,202,203,204], 202:[199,200,201,203,204], 203:[202,204,205,209,215],
 204:[201,202,203,205], 205:[203,204,206,208,209], 206:[205,207,208], 207:[206,208,211,212,213],
 208:[205,206,207,209,210,211,212], 209:[203,205,208,210,211,215], 210:[208,209,211,212,214,215],
 211:[208,209,210,212], 212:[207,208,210,211,213,214], 213:[207,212,214,217], 214:[210,212,213,215,216,217],
 215:[203,209,210,214,216], 216:[214,215,217,220], 217:[213,214,216,218,220], 218:[217,219,220],
 219:[218,220], 220:[216,217,218,219,221], 221:[220,222], 222:[221]}
def near(a, b): return a == b or b in ADJ[a] or a in ADJ[b]

# Readings from SPR's "Peta Asal" maps: the new polling-district subdivision is drawn inside the old seat
# boundaries and labelled OLDPAR/OLDDUN/nn NAME. Recorded where the arithmetic alone left more than one
# balancing assignment. The last entry is the one exception to SPR's colour code the arithmetic requires:
# Sungai Empit is purple in the new Stakan, but is the 439-elector sliver of old Stakan's Merdang that stayed.
MAP = {
 ("N.02","JAMBUSAN"):"N.02", ("N.23","REMBUS"):"N.16", ("N.23","PINANG"):"N.16", ("N.17","JALAN STAKAN"):"N.12",
 ("N.17","RANTAU PANJANG BATU KAWA"):"N.14", ("N.27","TAEE"):"N.21", ("N.66","KEMUYANG"):"N.55", ("N.64","NANG SANG"):"N.55",
 ("N.76","LUBOK DABAI"):"N.65", ("N.76","ULU METAH"):"N.65", ("N.78","LONG LIDAM"):"N.66", ("N.78","LONG LUAR"):"N.66", ("N.78","LONG WAT"):"N.66",
 ("N.84","SKRAT"):"N.71", ("N.84","SUNGAI TANGAP"):"N.71", ("N.84","LADANG DUA"):"N.71", ("N.92","SUNGAI KUAP"):"N.72", ("N.92","SUNGAI SENGKABANG"):"N.72",
 ("N.87","JEE FOH UTAMA"):"N.74", ("N.87","DESA SERI"):"N.74", ("N.89","PUJUT CORNER"):"N.74", ("N.89","PUJUT ADONG"):"N.74", ("N.89","PADANG BELON"):"N.74",
 ("N.89","KAMPUNG TUDAN"):"N.75", ("N.89","FASA EMPAT TUDAN"):"N.75", ("N.89","PRIMA VILLA"):"N.75", ("N.89","KAMPUNG SENADIN"):"N.75",
 ("N.89","PANGKALAN LUTONG"):"N.75", ("N.89","ASAM PAYA"):"N.75", ("N.87","KAMPUNG LOPENG"):"N.75", ("N.87","CANADA HILL"):"N.75",
 ("N.90","FASA DUA TUDAN"):"N.75", ("N.90","RPR PERMYJAYA"):"N.75", ("N.90","FASA ENAM TUDAN"):"N.75", ("N.90","PROMIN JAYA"):"N.75",
 ("N.90","DESA SENADIN"):"N.75", ("N.90","DESA MURNI"):"N.75",
 ("N.29","PANGKALAN BEDUP"):"N.23",
 ("N.24","SUNGAI EMPIT"):"N.17",
}

# ---- 1. the two sets of seats with their districts
d82 = {r[0]: r for r in D["d82"]}; d99 = {r[0]: r for r in D["d99"]}
par_of99 = {c: "P." + v[0][0].split("/")[0] for c, v in D["pd"].items()}
par_of82 = {c: "P." + v[0][0].split("/")[0] for c, v in D["pd82"].items()}
OLD, NEW = {}, {}
for pc, P in SPR.items():
    for t in P["old"]:
        OLD["N.%02d" % t["no"]] = {"name": t["name"], "par": pc, "dms": t["dms"], "total": sum(d["n"] for d in t["dms"])}
    for t in P["new"]:
        NEW["N.%02d" % t["no"]] = {"name": t["name"], "oldname": t.get("oldname"), "new": t["hcol"] == "red", "par": pc,
                                    "dms": t["dms"], "total": sum(d["n"] for d in t["dms"])}
for code, rows in D["pd82"].items():     # status-quo constituencies have no SPR table: identity
    OLD.setdefault(code, {"name": d82[code][1].upper(), "par": par_of82[code], "total": sum(r[2] for r in rows),
                          "dms": [{"name": r[1].upper(), "n": r[2], "fill": "white", "tcol": "black"} for r in rows]})
for code, rows in D["pd"].items():
    NEW.setdefault(code, {"name": d99[code][1].upper(), "oldname": None, "new": False, "par": par_of99[code], "total": sum(r[2] for r in rows),
                          "dms": [{"name": r[1].upper(), "n": r[2], "fill": "white", "tcol": "black"} for r in rows]})
assert sum(o["total"] for o in OLD.values()) == sum(n["total"] for n in NEW.values()) == 2037648

# predecessor of each proposed seat: the current seat of the same (or former) name
old_by_name = {norm(o["name"]): c for c, o in OLD.items()}
pred = {c: (None if n["new"] else old_by_name[norm(n["oldname"] or n["name"])]) for c, n in NEW.items()}
assert Counter(v for v in pred.values() if v) == Counter({oc: 1 for oc in OLD if oc in pred.values()})

# ---- 2. districts SPR's tables account for directly
old_dm = [(oc, i, d["name"], d["n"], d["fill"]) for oc, o in OLD.items() for i, d in enumerate(o["dms"])]
by_n = defaultdict(list)
for x in old_dm: by_n[x[3]].append(x)
lineage = defaultdict(list); assign = defaultdict(int); used_old = set(); pieces = []
def take(nc, i, x, how):
    lineage[(nc, i)].append({"old": x[0], "oi": x[1], "n": NEW[nc]["dms"][i]["n"], "how": how}); used_old.add((x[0], x[1])); assign[x[0]] += NEW[nc]["dms"][i]["n"]
for nc, n in sorted(NEW.items()):
    p = pred[nc]; ppar = pn(n["par"])
    for i, d in enumerate(n["dms"]):
        if d["fill"] != "purple":
            m = [x for x in by_n.get(d["n"], []) if x[0] == p and (x[0], x[1]) not in used_old and sim(x[2], d["name"]) >= 0.6]
            if m: take(nc, i, max(m, key=lambda x: sim(x[2], d["name"])), "same")
            else:
                lineage[(nc, i)].append({"old": p, "n": d["n"], "how": "same-dun"}); assign[p] += d["n"]
        else:
            m = [x for x in by_n.get(d["n"], []) if (x[0], x[1]) not in used_old and near(pn(OLD[x[0]]["par"]), ppar) and x[0] != p]
            m.sort(key=lambda x: (-(x[4] == "green"), -sim(x[2], d["name"])))
            good = [x for x in m if sim(x[2], d["name"]) >= 0.75]
            if good: take(nc, i, good[0], "moved" if good[0][4] == "green" else "moved(unmarked)")
            else: pieces.append([nc, i, d["name"], d["n"]])
bins = {oc: OLD[oc]["total"] - assign[oc] for oc in OLD}
assert min(bins.values()) >= 0

# ---- 3. remnants: a purple district keeping the name of a district not otherwise accounted for
vanished = defaultdict(list)
for oc, i, nm, nn, fill in old_dm:
    if (oc, i) not in used_old: vanished[norm(nm)].append(oc)
open_pieces = []
for u in pieces:
    nc, ni, nm, n = u
    c = [oc for oc in vanished.get(norm(nm), []) if bins[oc] > 0 and oc != pred[nc] and near(pn(OLD[oc]["par"]), pn(NEW[nc]["par"]))]
    if len(c) == 1:
        oc = c[0]; k = min(n, bins[oc])
        lineage[(nc, ni)].append({"old": oc, "n": k, "how": "remnant"}); bins[oc] -= k
        if k < n: open_pieces.append([nc, ni, nm, n - k, "split"])    # the rest came from elsewhere
    else:
        open_pieces.append(u + [None])

# ---- 4. the renamed pieces: map readings, then the unique exact partition of what is left
allowed = {}
for k, u in enumerate(open_pieces):
    nc, ni, nm, n, tag = u
    if (nc, nm) in MAP: allowed[k] = [MAP[(nc, nm)]]
    else: allowed[k] = [oc for oc in bins if bins[oc] > 0 and near(pn(OLD[oc]["par"]), pn(NEW[nc]["par"]))]
parent = {}
def find(a):
    while parent.get(a, a) != a: a = parent[a]
    return a
for k in allowed:
    for oc in allowed[k]:
        ra, rb = find(("p", k)), find(("b", oc))
        if ra != rb: parent[ra] = rb
comps = defaultdict(lambda: {"p": [], "b": []})
for k in allowed: comps[find(("p", k))]["p"].append(k)
for oc in bins:
    if bins[oc] > 0: comps[find(("b", oc))]["b"].append(oc)
size = {k: u[3] for k, u in enumerate(open_pieces)}
chosen = {}
for comp in comps.values():
    P, B = comp["p"], comp["b"]
    assert sum(size[k] for k in P) == sum(bins[oc] for oc in B)
    bin_pieces = {oc: [k for k in P if oc in allowed[k]] for oc in B}
    order = sorted(B, key=lambda oc: len(bin_pieces[oc]))
    sols = []
    def subsets(items, target, start, cur, used):
        if target == 0: yield list(cur); return
        for j in range(start, len(items)):
            k = items[j]
            if k in used or size[k] > target: continue
            cur.append(k); used.add(k)
            yield from subsets(items, target - size[k], j + 1, cur, used)
            cur.pop(); used.discard(k)
    def dfs(bi, used, asg):
        if len(sols) > 1: return
        if bi == len(order):
            if len(used) == len(P): sols.append(dict(asg))
            return
        oc = order[bi]
        for sub in subsets(sorted(bin_pieces[oc], key=lambda k: -size[k]), bins[oc], 0, [], used):
            for k in sub: asg[k] = oc; used.add(k)
            dfs(bi + 1, used, asg)
            for k in sub: used.discard(k); del asg[k]
            if len(sols) > 1: return
    dfs(0, set(), {})
    assert len(sols) == 1, "component with %d pieces has %d balancing assignments" % (len(P), len(sols))
    chosen.update(sols[0])
for k, u in enumerate(open_pieces):
    nc, ni, nm, n, tag = u
    lineage[(nc, ni)].append({"old": chosen[k], "n": n, "how": tag or ("map" if (nc, nm) in MAP else "inferred")})

# ---- 5. checks: every district fully placed, every current seat's total met
tot = defaultdict(int)
for (nc, ni), parts in lineage.items():
    assert sum(p["n"] for p in parts) == NEW[nc]["dms"][ni]["n"]
    for p in parts: tot[p["old"]] += p["n"]
assert all(tot[oc] == OLD[oc]["total"] for oc in OLD)
byhow = Counter(); byhowN = Counter()
for parts in lineage.values():
    for p in parts: byhow[p["how"]] += 1; byhowN[p["how"]] += p["n"]

out = {"source": "Derived from data/spr-peta-dm-2026.json by scripts/derive_lineage.py. For every proposed polling district: the current seat(s) its electors come from and how that was established.",
       "how": {"same": "unchanged district, same seat (name and count identical)",
               "same-dun": "district re-cut or renamed inside the same seat (not marked as moved in)",
               "moved": "whole district moved to another seat (marked moved out / moved in, name and count identical)",
               "moved(unmarked)": "as 'moved' but not colour-coded on the current-seat side",
               "remnant": "part of a district that kept its name after being split; source seat is the one that held that name",
               "map": "new name; source seat read from the old-DUN code SPR prints beside it on the Peta Asal map",
               "inferred": "new name; source seat is the only assignment that balances every current seat's total exactly",
               "split": "one district built from parts of two current seats; amounts by subtraction"},
       "districts": {"%s|%d" % k: v for k, v in sorted(lineage.items())}}
json.dump(out, open(os.path.join(ROOT, "data", "dm-lineage.json"), "w"), ensure_ascii=False, indent=0, separators=(",", ":"))
print("districts:", len(lineage), "| by rule:", dict(byhow), "| electors:", dict(byhowN))
