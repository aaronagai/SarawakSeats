#!/usr/bin/env python3
"""Extract SPR's "Peta & DM (Asal + Syor)" tables, with their colour coding, into
data/spr-peta-dm-2026.json.

    python3 scripts/extract_spr_tables.py "/path/to/SPR Sarawak 2026/1 - Parliament Files (31)"

Needs PyMuPDF (pip install pymupdf). Each constituency PDF carries the current
seats' district tables (PETA ASAL / DM DALAM DUN ASAL pages) and the proposed
seats' (PETA SYOR / DM DALAM DUN SYOR). Table cells are located from the drawn
borders and the text layer; the fill colour of each row (green = moved out,
purple = moved in) is read from a render of the page because some files draw the
fills as vectors and others as images; the name colour (red = new, blue =
renamed) comes from the text layer. Every table's rows are checked against its
printed JUMLAH.
"""
import fitz, glob, os, re, json, sys
from collections import Counter

ROOT = sys.argv[1] if len(sys.argv) > 1 else "SPR Sarawak 2026/1 - Parliament Files (31)"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "spr-peta-dm-2026.json")
ZOOM = 2.0

def classify_px(r,g,b):
    if r>235 and g>235 and b>235: return "white"
    if r<60 and 150<g<200 and 50<b<110: return "green"
    if 100<r<150 and 80<g<120 and 140<b<180: return "purple"
    if r>240 and g>240 and b<130: return "yellow"
    if 200<r<230 and 200<g<230 and 200<b<230: return "grey"
    return None

def classify_text(c):
    r=(c>>16)&255; g=(c>>8)&255; b=c&255
    if r<60 and g<60 and b<60: return "black"
    if r>180 and g<80 and b<80: return "red"
    if b>150 and r<100 and g<100: return "blue"
    return f"other({r},{g},{b})"

def page_title(p):
    t = [x.strip() for x in p.get_text().split("\n") if x.strip() and x.strip()!="RAHSIA"]
    return t[0] if t else ""

NUM = re.compile(r"^\d{1,3}(,\d{3})*$|^\d+$")
HEAD = re.compile(r"^N\.\s*(\d+)\s+(.+)$")

def cell_fill(pix, rect):
    x0 = max(0, int(rect.x0*ZOOM)); x1 = min(pix.width, int(rect.x1*ZOOM))
    y0 = max(0, int(rect.y0*ZOOM)); y1 = min(pix.height, int(rect.y1*ZOOM))
    c = Counter()
    for y in range(y0, y1, 2):
        for x in range(x0, x1, 2):
            k = classify_px(*pix.pixel(x, y)[:3])
            if k: c[k]+=1
    return c.most_common(1)[0][0] if c else "?"

def hsegs(p):
    segs = []
    for dr in p.get_drawings():
        if dr['type'] != 's': continue
        for it in dr['items']:
            if it[0] == 'l':
                a, b = it[1], it[2]
                if abs(a.y-b.y) < 1.0 and abs(a.x-b.x) > 40:
                    segs.append((min(a.x,b.x), max(a.x,b.x), (a.y+b.y)/2))
    return segs

def parse_page(p, warn):
    pix = p.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM))
    lines = []
    for b in p.get_text("dict")['blocks']:
        for l in b.get('lines', []):
            txt = "".join(s['text'] for s in l['spans']).strip()
            if not txt: continue
            cols = Counter(classify_text(s['color']) for s in l['spans'] if s['text'].strip())
            lines.append({"r": fitz.Rect(l['bbox']), "t": re.sub(r"\s+"," ",txt), "c": cols.most_common(1)[0][0]})
    segs = hsegs(p)
    heads = [l for l in lines if HEAD.match(l['t']) and "NAMA DM" not in l['t'].upper()]
    tables = []
    for h in heads:
        m = HEAD.match(h['t'])
        no = int(m.group(1)); name = m.group(2).strip().upper()
        oldname = None
        mm = re.search(r"\(\s*NAMA ASAL\s*:?\s*(.+?)\s*\)", name)
        if mm: oldname = mm.group(1).strip(); name = name[:mm.start()].strip()
        hr = h['r']; cx = (hr.x0+hr.x1)/2
        cand = [s for s in segs if s[0]-3 <= cx <= s[1]+3 and hr.y0-6 <= s[2] <= hr.y1+30]
        if not cand:
            warn(f"no border lines for N.{no} {name}"); continue
        wide = max(cand, key=lambda s: s[1]-s[0])
        tx0, tx1 = wide[0], wide[1]
        # table text lines: centre within table x-range, below header top
        body = [l for l in lines if l is not h and l['r'].y0 >= hr.y0 and tx0-2 < (l['r'].x0+l['r'].x1)/2 < tx1+2]
        body.sort(key=lambda l: l['r'].y0)
        rows = []; total = None; names = []; jum = []
        for l in body:
            t = l['t']; T = t.upper()
            if HEAD.match(t) and "NAMA DM" not in T:
                if abs(l['r'].y0 - hr.y0) < 6: continue   # hidden duplicate of this same header
                break
            if T.startswith("NAMA DM") or T in ("PEMILIH","NAMA","DM","NAMA DM PEMILIH"): continue
            if T.startswith("CATATAN"): continue
            if T.startswith("DAERAH MENGUNDI YANG") or T.startswith("NAMA DUN/") or T.startswith("NAMA PINDA"): continue
            mm = re.search(r"\(\s*NAMA ASAL\s*:?\s*(.+?)\s*\)", T)
            if mm and not rows:
                oldname = mm.group(1).strip(); continue
            if T.startswith("(NAMA ASAL") or T.startswith("( NAMA ASAL") or T.startswith("(NAMA") :
                oldname = re.sub(r"[()]|NAMA ASAL\s*:?", "", T).strip(); continue
            if oldname is not None and not rows and T.endswith(")") and not NUM.match(t.replace(" ","")):
                oldname = (oldname + " " + T.rstrip(")")).strip(); continue
            if T.startswith("JUMLAH") or T.startswith("JUMIAH"):
                if "PEMILIH" in T: continue
                mm = re.search(r"([\d,]+)\s*$", t)
                if mm and NUM.match(mm.group(1)): total = int(mm.group(1).replace(",",""))
                else: jum.append(l)
                continue
            if t.replace(" ","") == "1,2897":   # N.81 Ba`kelalan: misprint; 1,297 by the JUMLAH and the roll
                t = "1,297"; warn(f"N.{no} {name}: read '1,2897' as 1,297")
            if NUM.match(t.replace(" ","")):
                rows.append({"n": int(t.replace(",","").replace(" ","")), "nr": l['r'], "names": []})
            else:
                names.append(l)
        def vo(a, b, pad=8):
            return min(a.y1, b.y1+pad) - max(a.y0, b.y0-pad)
        for jl in jum:
            best=None; bd=1e9
            for r in rows:
                if vo(jl['r'], r['nr'], 3) > 0 and r['nr'].x0 >= jl['r'].x0 - 5:
                    dd = r['nr'].x0 - jl['r'].x1
                    if dd < bd: bd=dd; best=r
            if best is not None:
                total = best['n']; rows.remove(best)
            else: warn(f"N.{no} {name}: JUMLAH without number")
        for nl in names:
            best=None; bo=-1; bd=1e9
            hgt = nl['r'].height
            for r in rows:
                o = vo(nl['r'], r['nr'], 1)
                if o < 0.3*hgt: continue
                if r['nr'].x0 < nl['r'].x1 - 5: continue   # number must sit to the right of the name
                dd = r['nr'].x0 - nl['r'].x1
                if dd < bd - 12 or (abs(dd-bd) <= 12 and o > bo): bd=dd; bo=o; best=r
            if best is not None: best['names'].append(nl)
            else: warn(f"N.{no} {name}: orphan text '{nl['t']}'")
        dms = []
        for r in rows:
            r['names'].sort(key=lambda l: l['r'].y0)
            nm = re.sub(r"\s+", " ", " ".join(l['t'] for l in r['names']).upper().strip())
            if not r['names']: warn(f"N.{no} {name}: number {r['n']} without name")
            tcol = Counter(l['c'] for l in r['names']).most_common(1)[0][0] if r['names'] else "black"
            y0 = min([l['r'].y0 for l in r['names']] + [r['nr'].y0]); y1 = max([l['r'].y1 for l in r['names']] + [r['nr'].y1])
            nx1 = max(l['r'].x1 for l in r['names']) if r['names'] else tx0
            gap = fitz.Rect(nx1+2, y0+1, r['nr'].x0-2, y1-1)
            if gap.width < 4: gap = fitz.Rect(tx0+1, y0+1, tx1-1, y1-1)
            fill = cell_fill(pix, gap)
            dms.append({"name": nm, "n": r['n'], "fill": fill, "tcol": tcol})
        s = sum(d['n'] for d in dms)
        tables.append({"no": no, "name": name, "oldname": oldname, "hcol": h['c'], "dms": dms, "total": total, "sum": s,
                       "_seg": (round(tx0), round(tx1)), "_hy": hr.y0, "_off": abs(cx - (tx0+tx1)/2)})
    # de-duplicate headers drawn more than once (hidden copies per column pair): keep the fullest
    kept = []
    for t in sorted(tables, key=lambda t: t['_off']):
        if any(k['_seg'] == t['_seg'] and abs(k['_hy'] - t['_hy']) < 10 for k in kept): continue
        kept.append(t)
    tables = kept
    for t in tables: del t['_seg']; del t['_off']; del t['_hy']
    for t in tables:
        if t['total'] != t['sum']: warn(f"sum mismatch N.{t['no']:02d} {t['name']}: rows {t['sum']} vs JUMLAH {t['total']}")
    return tables

result = {}
for f in sorted(glob.glob(f"{ROOT}/*/*Peta & DM*.pdf")):
    base = os.path.basename(f)
    m = re.match(r"(P\.\d+) (.+?) - Peta", base)
    pcode, pname = m.group(1), m.group(2)
    d = fitz.open(f)
    old, new = [], []
    status = None
    warn = lambda s: print(f"  !! {pcode} p{i+1}: {s}", file=sys.stderr)
    for i, p in enumerate(d):
        title = page_title(p).upper()
        if i == 0:
            if "STATUS QUO" in p.get_text().upper(): status = "STATUS QUO"
            continue
        tabs = parse_page(p, warn)
        if not tabs: continue
        if "ASAL" in title and "SYOR" not in title: old += tabs
        elif "SYOR" in title: new += tabs
        else: warn(f"page title {title}")
    result[pcode] = {"name": pname, "status": status, "old": old, "new": new}
    print(pcode, pname, status or "", "old:", len(old), "duns", sum(len(t['dms']) for t in old), "dms", sum(t['sum'] for t in old), "|", "new:", len(new), "duns", sum(len(t['dms']) for t in new), "dms", sum(t['sum'] for t in new))

# N.58 Machan: the table prints Latong as 4,281; the notice, the seat's JUMLAH and the page total say 4,298.
for t in result["P.210"]["new"]:
    if t["no"] == 58:
        for d in t["dms"]:
            if d["name"] == "LATONG" and d["n"] == 4281:
                d["n"] = 4298; d["note"] = "printed 4,281 in the Peta & DM table; 4,298 per the notice and the table's own JUMLAH"
        t["sum"] = sum(d["n"] for d in t["dms"])
for t in result["P.222"]["old"]:
    if t["no"] == 81:
        for d in t["dms"]:
            if d["n"] == 1297: d["note"] = "printed '1,2897'; read as 1,297 (matches the JUMLAH and the roll)"
out = {"source": "SPR, Kajian Semula Persempadanan 2026 — 'Peta & DM (Asal + Syor)' PDF for each federal constituency; tables extracted with their colour coding",
       "legend": {"fill": {"green": "daerah mengundi yang dipindah keluar (moved out)", "purple": "daerah mengundi yang dipindah masuk (moved in)"},
                  "tcol": {"red": "new DUN / new polling district name", "blue": "renamed"}, "hcol": {"red": "new DUN"}},
       "parliaments": result}
json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=0, separators=(",", ":"))
