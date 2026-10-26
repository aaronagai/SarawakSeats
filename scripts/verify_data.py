#!/usr/bin/env python3
"""Fact-check the 82-seat data embedded in index.html.

Always: every seat's sexes and age bands sum to its electors, its polling
districts sum to its electors and match its district count, every DM code
sits under its own seat and parliament, parliament and state totals add up,
and the seat map carries the same 82 seats.

When SPR's exhibition files are present (SPR Sarawak 2026/, not committed):
every one of the 887 polling districts against SPR's Master Indeks (code, name,
electors), every seat's name, parliament and total, and the state total
against the Notis.

Ethnicity is reported, not failed: ElectionData ships it as 2022-roll shares,
so rounded counts can differ from a seat's electors by a few.

Usage: python3 scripts/verify_data.py      (exit 1 on any failure)
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPR = os.path.join(ROOT, "SPR Sarawak 2026", "2 - State Documents (4)")
page = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
D = json.loads(re.search(r'<script>const D=(\{.*?\});?</script>', page, re.S).group(1))
seats, pd, par = D["d82"], D["pd82"], D["par82"]
fail = []
def norm(n): return re.sub(r"[^A-Z0-9]", "", n.upper())

for r in seats:
    c, v = r[0], r[4]
    if r[5] + r[6] != v: fail.append("%s: male + female %d, electors %d" % (c, r[5] + r[6], v))
    if sum(r[7:12]) != v: fail.append("%s: age bands %d, electors %d" % (c, sum(r[7:12]), v))
    dms = pd.get(c, [])
    if len(dms) != r[3]: fail.append("%s: %d districts listed, %d stated" % (c, len(dms), r[3]))
    if sum(x[2] for x in dms) != v: fail.append("%s: districts sum to %d, electors %d" % (c, sum(x[2] for x in dms), v))
    prefix = par[r[2]][0][2:] + "/" + c[2:] + "/"
    fail += ["%s: DM code %s is not under %s" % (c, x[0], prefix) for x in dms if not x[0].startswith(prefix)]
for i, p in enumerate(par):
    rows = [r for r in seats if r[2] == i]
    if sum(r[4] for r in rows) != p[3]: fail.append("%s: electors %d, seats sum %d" % (p[0], p[3], sum(r[4] for r in rows)))
    if sum(r[3] for r in rows) != p[2]: fail.append("%s: districts %d, seats sum %d" % (p[0], p[2], sum(r[3] for r in rows)))
total = sum(r[4] for r in seats)
eth = [sum(r[12:21]) - r[4] for r in seats]

geo = os.path.join(ROOT, "data", "dun82-boundaries.json")
if os.path.exists(geo):
    t = json.load(open(geo))
    got = {g["properties"]["code_dun"]: g["properties"]["code_parlimen"] for g in t["objects"]["dun"]["geometries"]}
    if got != {r[0]: par[r[2]][0] for r in seats}: fail.append("map: boundary seats differ from the seat table")

checked_spr = False
mi_path = os.path.join(SPR, "Master Indeks KSP Sarawak.pdf")
if os.path.exists(mi_path):
    import fitz   # PyMuPDF
    MI, tot, info = {}, {}, {}
    for pg in fitz.open(mi_path):
        L = [l.strip() for l in pg.get_text().split("\n") if l.strip()]
        kod = pname = sname = None
        for i, l in enumerate(L):
            if l == "BAHAGIAN PILIHAN RAYA PERSEKUTUAN": pname = L[i + 1].lstrip(": ").strip()
            if l == "BAHAGIAN PILIHAN RAYA NEGERI": sname = L[i + 1].lstrip(": ").strip()
            m = re.match(r"^: (\d{3})/(\d{2})$", l)
            if m and L[i - 1].startswith("KOD BAHAGIAN PILIHAN RAYA NEGERI"):
                kod = "N." + m.group(2); info[kod] = ("P." + m.group(1), pname, sname)
            m = re.match(r"^(\d{3}/\d{2}/\d{2})\s+(.*)$", l)
            if m and i + 1 < len(L) and re.match(r"^[\d,]+$", L[i + 1]):
                MI[m.group(1)] = (m.group(2).strip(), int(L[i + 1].replace(",", "")))
            if l == "JUMLAH PEMILIH" and kod and i + 1 < len(L) and re.match(r"^[\d,]+$", L[i + 1]):
                tot[kod] = int(L[i + 1].replace(",", ""))
    site = {x[0]: (x[1], x[2]) for l in pd.values() for x in l}
    for k in sorted(set(site) | set(MI)):
        if k not in MI: fail.append("DM %s %s: not in SPR's Master Indeks" % (k, site[k][0])); continue
        if k not in site: fail.append("DM %s %s: in SPR's Master Indeks, missing here" % (k, MI[k][0])); continue
        if MI[k][1] != site[k][1]: fail.append("DM %s %s: %d here, %d in SPR" % (k, site[k][0], site[k][1], MI[k][1]))
        if norm(MI[k][0]) != norm(site[k][0]): fail.append("DM %s: named %s here, %s in SPR" % (k, site[k][0], MI[k][0]))
    for r in seats:
        c = r[0]
        if c not in info: fail.append("%s: not in SPR's Master Indeks" % c); continue
        pc, pn, sn = info[c]
        if norm(sn) != norm(r[1]): fail.append("%s: named %s here, %s in SPR" % (c, r[1], sn))
        if pc != par[r[2]][0] or norm(pn) != norm(par[r[2]][1]):
            fail.append("%s: in %s %s here, %s %s in SPR" % (c, par[r[2]][0], par[r[2]][1], pc, pn))
        if tot.get(c) != r[4]: fail.append("%s: %d electors here, %s in SPR" % (c, r[4], tot.get(c)))
    notis = os.path.join(SPR, "Notis Syor Untuk Pameran Kali Pertama.pdf")
    if os.path.exists(notis):
        txt = " ".join(p.get_text() for p in fitz.open(notis))
        m = re.search(r"pemilih seramai ([\d,]+) orang", txt)
        if not m or int(m.group(1).replace(",", "")) != total:
            fail.append("state total %d here, %s in SPR's Notis" % (total, m and m.group(1)))
    checked_spr = True

print("82 seats, %d polling districts, %s electors" % (sum(len(l) for l in pd.values()), "{:,}".format(total)))
print("SPR Master Indeks and Notis:", "checked" if checked_spr else "skipped (SPR Sarawak 2026/ not present)")
print("ethnicity (estimate, 2022-roll shares): %d seats off by rounding, largest gap %d, net %d" %
      (sum(1 for d in eth if d), max(map(abs, eth)), sum(eth)))
if fail:
    print("\n%d FAILED:" % len(fail)); print("\n".join("  " + f for f in fail)); sys.exit(1)
print("all checks passed")
