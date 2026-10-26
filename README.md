# SarawakSeats

Sarawak's **82 state seats** (DUN) for the coming state election: a map of every
seat's borders, the electors and demographic profile of every seat, and all 887
polling districts.

## The 99-seat proposal is shelved

The site was built around the Election Commission's (SPR) **proposed** 2026
redelineation (99 seats). The coming election is fought on the 82 seats gazetted
in 2015, so the proposal is set aside: no dataset toggle, no Changes tab, and the
short addresses belong to the 82 seats. Nothing was deleted. Its data stays
embedded in `index.html` and in `data/`, and setting `var PROPOSAL=true` in
`index.html` (then re-running `scripts/build_seat_pages.py`) brings the toggle,
the tab and its addresses back. The sections on the proposal below still
describe that data.

## What it shows

- **Seat map.** The borders of all 82 seats, labelled by seat code, with the 31
  parliaments as a soft grouping beneath them. Coloured by largest ethnic group
  or by deviation from the state average, over a grey, street or satellite
  basemap down to street level. It follows the rest of the page: pick a seat, a
  parliament or search and it frames that; click a seat on the map to open it.
- **Malapportionment.** Every seat carries its deviation from the state average
  (24,849 electors). The largest-to-smallest spread is **7.11:1**.
- **Demographics per seat.** Ethnic composition, five age bands and sex for all
  82 seats, filterable by parliamentary constituency.
- **Polling districts.** All 887 daerah mengundi, with DM codes and elector
  counts, searchable and filterable.

## Addresses

Every seat and parliament has its own address, so a link can be saved or pasted
into a group: `sarawakseats.org/N.16/` is N.16, `/P.219/` a parliament, with
`#daerah` and the other tab names after it. Each of those is a real page on the
server (`scripts/build_seat_pages.py` writes a stub per seat carrying that seat's
own title and link preview) that opens the app on that seat; the app keeps the
same path in the address bar as you move around, and the older `?dun=N.16` form
still works. Links shared during the objection period as `/82/N.16/` open the
same seat. Near-misses such as `/n16` are caught by `404.html`.

## Seat borders

`data/dun82-boundaries.json` and `data/dun82-boundaries-detail.json` are from **MECo**, the Malaysian Election Corpus
(Thevananthan & Chacko, *Electoral Maps and Cartograms from 1954 to 2025*,
[arXiv:2512.24211](https://arxiv.org/abs/2512.24211)), released CC0 at
https://github.com/Thevesh/paper-meco-maps. Its `sarawak_2015_dun` layer is the
2015 delimitation. `scripts/build_boundaries.py` writes it at two levels: a
simplified file for the statewide view (~115 KB gzipped; mapshaper simplifies
shared edges once, so neighbouring seats never open gaps), and every vertex MECo
has (~174,000 points, one every ~27 m on median; ~570 KB gzipped), which the map
fetches once the reader zooms in to town level. Both dissolve the parliaments
from the same polygons, so a parliament border always sits on a DUN border, and
both carry a label point inside every seat. All 82 seat codes, names and parliaments match the seat
table. MECo is a digitisation of SPR's gazetted maps, not an SPR publication: it
shows where a seat lies, but to confirm which seat a voter is in, use
[MySPR Semak](https://mysprsemak.spr.gov.my/). At street level, remember the border is
only as exact as MECo's digitisation of the gazette maps: good for seeing which
side of a river or road a seat runs, not for settling which side of it a single
house falls. The basemaps are Esri's World Gray Canvas, World Street Map and
World Imagery (© Esri, HERE, Garmin, Maxar, Earthstar Geographics,
© OpenStreetMap contributors).

## Status of the proposal data

These are **syor yang dicadangkan** — proposed recommendations, not gazetted
boundaries. Public exhibition ran 1–30 September 2026 and objections can still
change them. Refer to SPR's own documents for any official purpose.

## Sources

Two, and they are not the same authority:

**Boundaries, seat names and elector counts — SPR.**
Notis Syor Untuk Pameran Kali Pertama, Jadual Kedua (Second Schedule) — notice
under Section 4, Part II of the Thirteenth Schedule to the Federal Constitution,
Article 113(2). Elector counts are from the electoral roll gazetted 29 January
2026 [P.U. (B) 35/2026]. Portal: https://myst.spr.gov.my/pameran-syor

**Demographic breakdowns (ethnicity, age, sex) and the polling-district tables
for both sets (DM codes, names, elector counts) — ElectionData.MY**, via its Lukis
redistricting tool (https://lukis.electiondata.my). These are **not** an SPR
publication and are not part of the gazetted notice. The workbooks in `data/`
carry their own source notes.

**Where each seat's electors come from — SPR's per-constituency exhibition
files.** For each of the 31 federal constituencies SPR publishes a "Peta & DM
(Asal + Syor)" PDF: the current seats with their polling districts, the proposed
seats with theirs, and a colour code — districts moved out (green), districts
moved in (purple), new seat or district names (red), renamed districts (blue).
`data/spr-peta-dm-2026.json` is those tables, extracted with their colour coding
from the 29 constituencies that change (P.205 Saratok and P.214 Selangau are
status quo). Two constituencies' current-seat totals are also confirmed by the
Master Indeks (the roll by current seat) and the Notis.

## Accuracy

The SPR figures were extracted from the PDF by word coordinates (its text layer
scrambles reading order on some pages), then reconciled against the notice's own
subtotals: every DUN subtotal (99/99), every federal constituency subtotal
(31/31), and the stated state total of 2,037,648 electors. Names and figures
were additionally cross-checked by a second, independent extraction pass and by
reading rendered pages.

The demographic workbooks are reconciled at build time before being embedded.
Both sets agree with the SPR totals exactly, and in the 99-seat set every seat's
ethnicity, age bands and sex each sum to its elector count.

**N.55 Meradong, settled.** The workbook and the SPR notice list the same
thirteen daerah with the same thirteen counts, but pair eight of them to
different names (a permutation inside one seat preserves every subtotal, which is
why reconciliation never caught it). SPR's own Peta & DM table for P.208 pairs
them exactly as the notice does, and identically to the current N.46 Meradong
list — so the notice is right and the workbook is scrambled. The site now carries
SPR's pairing for N.55, with the workbook's codes and order.

**Two misprints in SPR's Peta & DM tables**, both caught by the tables' own
subtotals: N.58 Machan lists Latong as 4,281 where the notice, the seat total and
the page total all say 4,298; and N.81 Ba'kelalan prints one count as "1,2897",
which is 1,297 by the JUMLAH and the roll. Both are corrected in the extract and
annotated there.

**One known discrepancy.** In the **82-seat** workbook the ethnicity columns do
not sum exactly to the elector count: 75 of 82 seats are out by a few electors,
235 statewide (0.012%), worst case 0.087% on a single seat. Age and sex
reconcile exactly, and the 99-seat set is exact throughout. This is rounding in
the upstream source. Ethnic percentages are therefore computed against the sum
of the ethnicity columns rather than the elector total, so the shares always add
to 100%.

## How the flows were established

The question the Changes tab answers is: for every proposed seat, how many of its
electors were in each current seat? SPR's tables state most of it directly, and
the rest is forced by arithmetic. `data/dm-lineage.json` records, for each of the
1,141 proposed polling districts, the current seat(s) its electors come from and
which of these rules established it:

| rule | electors | what it rests on |
|---|---:|---|
| unchanged district, same seat | 1,159,367 | name and count identical; not marked as moved |
| district re-cut inside its own seat | 362,834 | not marked as moved in, so it stays with the seat of the same name |
| whole district moved to another seat | 263,357 | marked moved out / moved in; name and count identical |
| remnant keeping its old name | 62,049 | the name identifies the district it was cut from, and so the seat |
| read from SPR's map | 72,721 | SPR's "Peta Asal" draws the new districts inside the old boundaries, labelled with the old seat's code |
| by subtraction | 117,320 | the only assignment that makes every current seat's total balance exactly |

The last two classes (9.3% of electors) are shown on the site with a ≈ mark. The
subtraction is checked, not assumed: with the stated districts fixed, every
current seat's remaining electors must be exactly accounted for by the renamed
pieces nearby, and for every seat there is exactly one way to do it. One district
(Tijirak, in the new Sungai Serin) is built from parts of two current seats; its
split is by subtraction too. One district (Sungai Empit, 439 electors) is marked
by SPR as moved into the new Stakan but is arithmetically the sliver of the old
Stakan's Merdang that stayed behind, and is treated as such.

The Peta Asal maps were read where the arithmetic alone left more than one
answer — chiefly Miri, where old Pujut and old Senadin both feed the new
Permaisuri. The labels are small; the readings are listed in
`scripts/derive_lineage.py` and every one of them is consistent with the
seat totals.

## Build

`index.html` carries the data, styles and scripts inline; `kuching.png` is the
only separate asset. The seat and polling-district tables were generated from the
two workbooks in `data/` and reconciled against the SPR figures before being
written in. `python3 scripts/build_changes.py` rebuilds the Changes block from
`data/spr-peta-dm-2026.json` and `data/dm-lineage.json` and writes it back into
the page.
