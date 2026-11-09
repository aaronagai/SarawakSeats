#!/usr/bin/env python3
"""Count electors per seat, polling district and lokaliti from SPR's full
electoral roll (Daftar Pemilih) for the seats we hold it for, into
data/roll-2026.json.

Only N.16 Muara Tuang so far. N.04 Pantai Damai is held back until its
roll is complete (the Rampangi district is missing).

Inputs are the cleaned roll workbooks built from SPR's PDFs. They hold names
and IC numbers, so they stay outside this repository and are passed in by path:

  python3 scripts/build_roll.py \
      --n16 ".../Daftar Pemilih April 2026 - N16 Muara Tuang.xlsx"

Only counts are written. A lokaliti with fewer than MIN_DETAIL electors keeps
its total but not its sex, age or race split, so no figure points at a person.

Age is the exact age on REF, from the date of birth in the IC number; where
the IC is unreadable or gives an impossible age, from the printed birth year.
"""
import argparse, datetime, json, os, re
from collections import defaultdict
from openpyxl import load_workbook

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = datetime.date(2026, 11, 9)
MIN_DETAIL = 10
AGE = [("18-28", 18, 28), ("29-45", 29, 45), ("46-60", 46, 60), ("61+", 61, 999)]
SITE_AGE = [(18, 20), (21, 30), (31, 45), (46, 59), (60, 999)]   # the site's five bands
KAUM = ["MELAYU/MELANAU", "IBAN", "CINA", "BIDAYUH", "ORANG ULU", "LAIN-LAIN"]

# SPR's own elector count per polling district for the N.04 roll: from the
# file name of each district's PDF, and the Borang Jumlah Pencerakinan for
# Rampangi, whose PDF we do not have.
N04_SPR = {"193/04/01": 2648, "193/04/02": 649, "193/04/03": 917, "193/04/04": 453,
           "193/04/05": 1705, "193/04/06": 3424, "193/04/07": 13683, "193/04/08": 1306,
           "193/04/09": 4891, "193/04/10": 1614, "193/04/11": 3689, "193/04/12": 6312}


def age(ic, yr):
    yr = int(yr) if yr else None
    if ic and re.fullmatch(r"\d{12}", str(ic)):
        ic = str(ic); yy, mm, dd = int(ic[:2]), int(ic[2:4]), int(ic[4:6])
        y = yr if (yr and yr % 100 == yy) else (2000 if yy <= 26 else 1900) + yy
        try:
            b = datetime.date(y, mm, dd)
            a = REF.year - b.year - ((REF.month, REF.day) < (b.month, b.day))
            if a >= 18 or not yr: return a
        except ValueError:
            pass
    if yr: return REF.year - yr - (1 if (REF.month, REF.day) < (7, 1) else 0)
    return None


def band(a, bands):
    if a is None: return None
    for i, b in enumerate(bands):
        lo, hi = b[-2], b[-1]
        if lo <= a <= hi: return i
    return None


NAMES = {}


def read(path, seat):
    """Normalised voters: dm code, lokaliti number, sex, age, kaum."""
    ws = load_workbook(path, read_only=True)["Semua Pengundi"]
    rows = ws.iter_rows(values_only=True)
    h = list(next(rows))
    col = lambda name: h.index(name)
    out = []
    for r in rows:
        if seat == "N.04":
            kod, sex, a, kaum = r[col("Kod Lokaliti")], r[col("Jantina")], age(r[col("No K/P")], r[col("Tahun Lahir")]), None
            NAMES[str(kod)] = r[col("Lokaliti")]
        else:
            kod, kaum = r[col("Kod Lokaliti")], r[col("Kaum")]
            sex = {"LELAKI": "L", "PEREMPUAN": "P"}.get(r[col("Jantina")])
            a = age(r[col("No K/P")], r[col("Tahun Lahir")])
            NAMES[str(kod)] = r[col("Lokaliti")]
        kod = str(kod)
        dm = "%s/%s/%s" % (kod[:3], kod[3:5], kod[5:7])
        out.append((dm, int(kod[7:]), sex, a, kaum))
    return out


def counts(vs, with_kaum):
    c = {"n": len(vs), "L": sum(v[2] == "L" for v in vs), "P": sum(v[2] == "P" for v in vs),
         "age": [sum(band(v[3], AGE) == i for v in vs) for i in range(len(AGE))]}
    if with_kaum: c["kaum"] = [sum(v[4] == k for v in vs) for k in KAUM]
    return c


def build(seat, vs, roll, src, spr_dm=None):
    with_kaum = seat == "N.16"
    by_dm, by_lok = defaultdict(list), defaultdict(list)
    for v in vs:
        by_dm[v[0]].append(v); by_lok[(v[0], v[1])].append(v)
    dms = {}
    for dm in sorted(by_dm):
        c = counts(by_dm[dm], with_kaum)
        c["spr"] = spr_dm.get(dm, c["n"]) if spr_dm else c["n"]
        dms[dm] = c
    if spr_dm:
        for dm, n in spr_dm.items():
            dms.setdefault(dm, {"n": 0, "spr": n, "missing": True})
    lok = defaultdict(dict)
    for (dm, num), lv in sorted(by_lok.items()):
        c = counts(lv, with_kaum)
        if c["n"] < MIN_DETAIL: c = {"n": c["n"]}
        c["name"] = NAMES.get("%s%s%s%03d" % (dm[:3], dm[4:6], dm[7:9], num), "")
        lok[dm][str(num)] = c
    # a district holding a lokaliti too small to split keeps its total only, or
    # the small lokaliti could be worked out by subtraction
    for dm, ls in lok.items():
        if any("L" not in c for c in ls.values()):
            dms[dm] = {"n": dms[dm]["n"], "spr": dms[dm]["spr"]}
    seat_c = counts(vs, with_kaum)
    seat_c["site_age"] = [sum(band(v[3], SITE_AGE) == i for v in vs) for i in range(len(SITE_AGE))]
    seat_c["no_age"] = sum(v[3] is None for v in vs)
    seat_c["spr"] = sum(d["spr"] for d in dms.values())
    return {"roll": roll, "src": src, "seat": seat_c, "dm": dms, "lok": lok}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n16", required=True)
    a = ap.parse_args()
    out = {"ref": REF.isoformat(), "min_detail": MIN_DETAIL, "age": [x[0] for x in AGE],
           "kaum": ["Melayu/Melanau", "Iban", "Cina", "Bidayuh", "Orang Ulu", "Lain-lain"], "seats": {}}
    out["seats"]["N.16"] = build("N.16", read(a.n16, "N.16"), "Daftar Pemilih April 2026",
                                 "SPR, Daftar Pemilih Muara Tuang April 2026")
    path = os.path.join(ROOT, "data", "roll-2026.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    for s, d in out["seats"].items():
        c = d["seat"]
        print("%s  roll %d  SPR %d  L %d  P %d  age %s  dms %d  lokaliti %d" % (
            s, c["n"], c["spr"], c["L"], c["P"], c["age"], len(d["dm"]), sum(len(v) for v in d["lok"].values())))
    print("wrote", os.path.relpath(path, ROOT), os.path.getsize(path), "bytes")


if __name__ == "__main__":
    main()
