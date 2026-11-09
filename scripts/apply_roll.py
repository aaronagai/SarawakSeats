#!/usr/bin/env python3
"""Write the seats in data/roll-2026.json into the 82-seat table in index.html.

For each seat SPR's full roll is held for (only N.16 Muara Tuang so far), its
row and polling districts take the roll's counts in place of the January 2026
totals and ElectionData's estimates: electors, sex and the five age bands are
counted from the roll. SPR's roll gives Melayu and Melanau as one group; that
group is divided between the two in the proportion of the seat's previous
estimate, and every other group is counted. The parliament total follows, and
D.roll records which seats changed and from which roll, so the page can say so.

The original row is kept in D.roll[seat].was, so the change can be undone by
re-running with --undo.

Usage: python3 scripts/apply_roll.py [--undo]
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "index.html")
page = open(PAGE, encoding="utf-8").read()
m = re.search(r'(<script>const D=)(\{.*?\})(;?</script>)', page, re.S)
D = json.loads(m.group(2))
R = json.load(open(os.path.join(ROOT, "data", "roll-2026.json"), encoding="utf-8"))
undo = "--undo" in sys.argv
roll = D.get("roll", {})

def par_index(code): return next(r[2] for r in D["d82"] if r[0] == code)

# put back any seat already applied, so a re-run starts from the original
for code, info in list(roll.items()):
    i = next(k for k, r in enumerate(D["d82"]) if r[0] == code)
    old = D["d82"][i]
    D["d82"][i] = info["was"]["row"]
    D["pd82"][code] = info["was"]["pd"]
    D["par82"][old[2]][3] += info["was"]["row"][4] - old[4]
roll = {}

if not undo:
    for code, s in R["seats"].items():
        i = next(k for k, r in enumerate(D["d82"]) if r[0] == code)
        old = D["d82"][i]; c = s["seat"]
        # ethFull: Melayu, Melanau, Kedayan, Cina, India, Iban, Bidayuh, Orang Ulu, Lain-lain
        mm, iban, cina, bid, ou, lain = c["kaum"]
        est_my, est_mn = old[12], old[13]
        melanau = round(mm * est_mn / (est_my + est_mn)) if est_my + est_mn else 0
        eth = [mm - melanau, melanau, 0, cina, 0, iban, bid, ou, lain]
        if sum(c["site_age"]) + c["no_age"] != c["n"]: sys.exit("%s: age bands do not sum" % code)
        if c["no_age"]: sys.exit("%s: %d electors with no age" % (code, c["no_age"]))
        row = old[:4] + [c["n"], c["L"], c["P"]] + c["site_age"] + eth
        names = {x[0]: x[1] for x in D["pd82"][code]}
        pd = [[dm, names[dm], s["dm"][dm]["n"]] for dm in sorted(s["dm"])]
        if set(names) != set(s["dm"]): sys.exit("%s: polling districts differ from the site" % code)
        roll[code] = {"roll": s["roll"], "src": s["src"], "ref": R["ref"],
                      "was": {"row": old, "pd": D["pd82"][code]}}
        D["d82"][i] = row; D["pd82"][code] = pd
        D["par82"][old[2]][3] += row[4] - old[4]
        print("%s %s: %d -> %d electors; Melayu/Melanau %d split %d/%d" % (code, old[1], old[4], row[4], mm, mm - melanau, melanau))

if roll: D["roll"] = roll
else: D.pop("roll", None)
out = m.group(1) + json.dumps(D, ensure_ascii=False, separators=(",", ":")) + m.group(3)
total = sum(r[4] for r in D["d82"])
page = page[:m.start()] + out + page[m.end():]
page = re.sub(r"var TOTAL=\d+;", "var TOTAL=%d;" % total, page, count=1)
open(PAGE, "w", encoding="utf-8").write(page)
print("state total", total, "· seats on a newer roll:", ", ".join(roll) or "none")
