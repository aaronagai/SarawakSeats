#!/usr/bin/env python3
"""Put each seat's outgoing assemblyman into the page.

Reads data/assemblymen.json (code -> name, party, coalition; the 19th DUN,
dissolved 26 Oct 2026) and writes it into index.html as `const YB=...`, in its
own <script> block right after the main data block. Re-running replaces it.

Usage: python3 scripts/build_assemblymen.py
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = json.load(open(os.path.join(ROOT, "data", "assemblymen.json"), encoding="utf-8"))
yb = {"dissolved": src["dissolved"],
      "s": {c: [v["name"], v["party"], v["coalition"] or ""] for c, v in src["seats"].items()}}
block = "<script>const YB=" + json.dumps(yb, ensure_ascii=False, separators=(",", ":")) + ";</script>"

path = os.path.join(ROOT, "index.html")
page = open(path, encoding="utf-8").read()
if re.search(r"<script>const YB=.*?;</script>", page):
    page = re.sub(r"<script>const YB=.*?;</script>", lambda m: block, page, count=1)
else:
    m = re.search(r"<script>const D=\{.*?\};?</script>", page, re.S)
    page = page[:m.end()] + "\n" + block + page[m.end():]
open(path, "w", encoding="utf-8").write(page)
print("wrote", len(yb["s"]), "seats")
