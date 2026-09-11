#!/usr/bin/env python3
"""Rebuild the `chg` block embedded in index.html from the SPR polling-district
crosswalk (data/dm-lineage.json) and the seat tables already embedded in the page.

The crosswalk says, for every proposed polling district, which current seat its
electors were drawn from and how that was established (see README). This script
only aggregates it: per proposed seat (which current seats it draws from), per
current seat (which proposed seats it goes to), per parliament, and statewide.

Usage: python3 scripts/build_changes.py            # rewrites index.html in place
"""
import json, re, sys, os
from collections import defaultdict, Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "index.html")
LIN = json.load(open(os.path.join(ROOT, "data", "dm-lineage.json")))["districts"]
SPR = json.load(open(os.path.join(ROOT, "data", "spr-peta-dm-2026.json")))["parliaments"]

html = open(INDEX, encoding="utf-8").read()
m = re.search(r'<script>const D=(\{.*?\});?</script>', html, re.S)
D = json.loads(m.group(1))

def norm(n): return re.sub(r"[^A-Z0-9]", "", n.upper()).replace("TANJUNG", "TANJONG").replace("KAMPONG", "KAMPUNG")
CERTAIN = {"same", "same-dun", "moved", "moved(unmarked)", "remnant"}

d99 = {r[0]: r for r in D["d99"]}; d82 = {r[0]: r for r in D["d82"]}
par99 = {i: p for i, p in enumerate(D["par"])}; par82 = {i: p for i, p in enumerate(D["par82"])}
par_of99 = {c: D["par"][r[2]] for c, r in d99.items()}
par_of82 = {c: D["par82"][r[2]] for c, r in d82.items()}

# proper-case names for polling districts, from the workbook tables (matched on name + count)
def pretty(pdtable, code, name, n):
    for row in pdtable.get(code, []):
        if row[2] == n and norm(row[1]) == norm(name): return row[1]
    return name.title().replace("`", "'")

# ---- ethnic mix helpers (mirror the page's ETH_SRC fold of the nine columns)
E0 = 12
ETH_SRC = [[5], [3], [0], [6], [1], [7], [2, 4, 8]]
def mix(row):
    v = [sum(row[E0 + i] for i in src) for src in ETH_SRC]
    t = sum(v) or 1
    return [round(x / t, 4) for x in v]
def mix_rows(rows):
    tot = [0] * 7
    for r in rows:
        for j, src in enumerate(ETH_SRC): tot[j] += sum(r[E0 + i] for i in src)
    t = sum(tot) or 1
    return [round(x / t, 4) for x in tot]
def tvd(a, b): return round(0.5 * sum(abs(x - y) for x, y in zip(a, b)), 4)
def mover(was, now):
    i = max(range(7), key=lambda k: abs(now[k] - was[k]))
    return [i, was[i], now[i]]

# ---- flows from the crosswalk
# LIN: "N.xx|idx" -> [{old, n, how}], with the new DM name/count in SPR[new]
new_dm = {}   # (nc, idx) -> (name, n)
for pc, P in SPR.items():
    for t in P["new"]:
        code = "N.%02d" % t["no"]
        for i, d in enumerate(t["dms"]): new_dm[(code, i)] = (d["name"], d["n"])
for code, rows in D["pd"].items():          # status-quo seats are not in the SPR tables
    for i, r in enumerate(rows):
        new_dm.setdefault((code, i), (r[1].upper(), r[2]))
old_dm = {}
for pc, P in SPR.items():
    for t in P["old"]:
        code = "N.%02d" % t["no"]
        for i, d in enumerate(t["dms"]): old_dm[(code, i)] = (d["name"], d["n"])
for code, rows in D["pd82"].items():
    for i, r in enumerate(rows):
        old_dm.setdefault((code, i), (r[1].upper(), r[2]))

flow = defaultdict(lambda: defaultdict(lambda: [0, 0]))   # new -> old -> [electors, inferred]
pieces = defaultdict(list)                                # new -> [(dmName, n, old, how)]
for key, parts in LIN.items():
    nc, ni = key.split("|"); ni = int(ni)
    name, n = new_dm[(nc, ni)]
    for p in parts:
        f = flow[nc][p["old"]]
        f[0] += p["n"]
        if p["how"] not in CERTAIN: f[1] += p["n"]
        pieces[nc].append((name, p["n"], p["old"], p["how"], p.get("oi")))

meta = {}   # new code -> {new: bool, ren: oldname}
for pc, P in SPR.items():
    for t in P["new"]:
        meta["N.%02d" % t["no"]] = {"new": t["hcol"] == "red", "ren": t.get("oldname")}

def entry(code, total, sources, now, was, cp_name):
    s = sorted(sources, key=lambda x: -x[4])
    shares = [x[4] / total for x in s]
    return {"t": total, "u": 0, "s": s, "core": round(max(shares), 4) if shares else 0,
            "enp": round(1 / sum(sh * sh for sh in shares), 2) if shares else 0,
            "now": now, "was": was, "tvd": tvd(now, was), "mv": mover(was, now), "cp": cp_name}

# ---- proposed seats: where each one's electors come from
P = {}
for nc, row in d99.items():
    total = row[4]
    srcs = [[oc, d82[oc][1], par_of82[oc][0], par_of82[oc][1], v[0], v[1]] for oc, v in flow[nc].items()]
    core = max(srcs, key=lambda x: x[4])
    e = entry(nc, total, srcs, mix(row), mix(d82[core[0]]), d82[core[0]][1])
    e["n"] = row[1]
    e["new"] = meta.get(nc, {}).get("new", False)
    if meta.get(nc, {}).get("ren"): e["ren"] = d82[core[0]][1] if core[0] else meta[nc]["ren"].title()
    # came in: districts (or parts) drawn from a seat other than the core one. A brand-new
    # seat has no "own" predecessor, so for it every district came in and nothing "went out".
    inn = []
    for name, n, oc, how, oi in pieces[nc]:
        if oc == core[0] and not e["new"]: continue
        inn.append([pretty(D["pd"], nc, name, n), n, d82[oc][1], how not in CERTAIN])
    # went out: parts of the core seat that ended up in other proposed seats
    out = []
    for onc, lst in pieces.items():
        if onc == nc or e["new"]: continue
        for name, n, oc, how, oi in lst:
            if oc != core[0]: continue
            out.append([pretty(D["pd"], onc, name, n), n, onc, d99[onc][1], how not in CERTAIN])
    e["in"] = sorted(inn, key=lambda x: -x[1]); e["out"] = sorted(out, key=lambda x: -x[1])
    P[nc] = e

# ---- current seats: where each one's electors go
C = {}
back = defaultdict(lambda: defaultdict(lambda: [0, 0]))
for nc, olds in flow.items():
    for oc, v in olds.items():
        back[oc][nc][0] += v[0]; back[oc][nc][1] += v[1]
for oc, row in d82.items():
    total = row[4]
    dst = [[nc, d99[nc][1], par_of99[nc][0], par_of99[nc][1], v[0], v[1]] for nc, v in back[oc].items()]
    core = max(dst, key=lambda x: x[4])
    e = entry(oc, total, dst, mix(row), mix(d99[core[0]]), d99[core[0]][1])
    e["n"] = row[1]
    C[oc] = e

# ---- parliaments: same thing one level up
PP = {}
pflow = defaultdict(lambda: defaultdict(lambda: [0, 0]))
ppieces = defaultdict(list)
for nc, olds in flow.items():
    pc = par_of99[nc][0]
    for oc, v in olds.items():
        pflow[pc][par_of82[oc][0]][0] += v[0]; pflow[pc][par_of82[oc][0]][1] += v[1]
for nc, lst in pieces.items():
    for name, n, oc, how, oi in lst:
        ppieces[par_of99[nc][0]].append((name, n, par_of82[oc][0], how, nc))
pname82 = {p[0]: p[1] for p in D["par82"]}; pname99 = {p[0]: p[1] for p in D["par"]}
rows99_by_par = defaultdict(list); rows82_by_par = defaultdict(list)
for c, r in d99.items(): rows99_by_par[par_of99[c][0]].append(r)
for c, r in d82.items(): rows82_by_par[par_of82[c][0]].append(r)
for pc, p in pname99.items():
    total = sum(r[4] for r in rows99_by_par[pc])
    srcs = [[opc, pname82[opc], "", "", v[0], v[1]] for opc, v in pflow[pc].items()]
    core = max(srcs, key=lambda x: x[4])
    e = entry(pc, total, srcs, mix_rows(rows99_by_par[pc]), mix_rows(rows82_by_par[core[0]]), pname82[core[0]])
    e["n"] = p
    inn = [[pretty(D["pd"], nc, name, n), n, pname82[opc], how not in CERTAIN] for name, n, opc, how, nc in ppieces[pc] if opc != core[0]]
    out = []
    for onc, lst in ppieces.items():
        if onc == pc: continue
        for name, n, opc, how, nc in lst:
            if opc == core[0]: out.append([pretty(D["pd"], nc, name, n), n, onc, pname99[onc], how not in CERTAIN])
    e["in"] = sorted(inn, key=lambda x: -x[1]); e["out"] = sorted(out, key=lambda x: -x[1])
    PP[pc] = e

# ---- statewide summary
tot = sum(r[4] for r in d99.values())
stay = sum(v[0] for nc, olds in flow.items() for oc, v in olds.items() if norm(d99[nc][1]) == norm(d82[oc][1]) or (meta.get(nc, {}).get("ren") and norm(meta[nc]["ren"]) == norm(d82[oc][1])))
inferred = sum(v[1] for olds in flow.values() for v in olds.values())
whole = sum(1 for parts in LIN.values() for p in parts if p["how"] == "moved" or p["how"] == "moved(unmarked)")
xpar = sum(v[0] for nc, olds in flow.items() for oc, v in olds.items() if par_of99[nc][0] != par_of82[oc][0])
M = D["chg"]["m"]
M.update({"total": tot, "stay": stay, "inferred": inferred, "wholeMoved": whole, "crossPar": xpar,
          "newSeats": sum(1 for v in meta.values() if v["new"]), "renamed": sum(1 for v in meta.values() if v["ren"])})

D["chg"] = {"p": P, "c": C, "m": M, "pp": PP}

# ---- N.55 Meradong: the workbook pairs eight of its thirteen district counts to the wrong names.
# SPR's notice and its Peta & DM table agree with each other (and with the current N.46 list),
# so the counts follow SPR here. Codes and order stay as in the workbook.
spr55 = {norm(d["name"]): d["n"] for t in SPR["P.208"]["new"] if t["no"] == 55 for d in t["dms"]}
for row in D["pd"]["N.55"]:
    row[2] = spr55[norm(row[1])]
assert sum(r[2] for r in D["pd"]["N.55"]) == d99["N.55"][4]

new_json = json.dumps(D, ensure_ascii=False, separators=(",", ":"))
html = html[:m.start(1)] + new_json + html[m.end(1):]
open(INDEX, "w", encoding="utf-8").write(html)
print("chg rebuilt: %d proposed, %d current, %d parliaments; inferred %d of %d electors (%.1f%%); N.55 counts corrected"
      % (len(P), len(C), len(PP), inferred, tot, 100 * inferred / tot))
