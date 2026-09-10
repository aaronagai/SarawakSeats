# SarawakSeats

A dashboard for the Election Commission's (SPR) **proposed** 2026 redelineation
of Sarawak — the 99 proposed state constituencies (DUN) set against the 82
currently in force, with the demographic profile of every seat.

SPR publishes the proposal for public reading, but only inside a flipbook PDF
viewer that is hard to search or read on a phone. This is the same data, plus
the demographics needed to actually reason about it.

## What it shows

- **Two datasets, one electorate.** Toggle between the proposed 99 seats and the
  current 82. Both are drawn on the same gazetted roll of 2,037,648 electors, so
  they compare directly.
- **Malapportionment.** Every seat carries its deviation from the state average
  (20,582 electors under the proposal). The largest-to-smallest spread is
  **3.33:1** proposed, against **7.11:1** under the current boundaries.
- **Demographics per seat.** Ethnic composition, five age bands and sex, for all
  99 (and all 82) seats, filterable by parliamentary constituency.
- **Polling districts.** All 1,141 proposed daerah mengundi and all 887 current
  ones, with DM codes and elector counts, searchable and filterable.
- **What changed.** Per seat and per parliament: core retention, effective
  predecessors, the shift in ethnic mix, and the polling districts that moved in
  and out. Traced by district name, with coverage stated per seat.

## Status of the data

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

**A second discrepancy, and why the polling-district table changed source.**
The site originally carried polling districts extracted from the SPR PDF (names
and elector counts only). Adding DM codes meant joining to the workbook, and
that join surfaced a conflict in exactly one seat, **N.55 Meradong**: both
sources list the same thirteen daerah with the same thirteen elector counts and
the same subtotal (29,144), but eight of them are paired to different names. A
permutation inside one DUN preserves every subtotal, which is why no earlier
reconciliation caught it.

The workbook rows are in strict DM-code order and are internally consistent, and
the README already noted that the PDF's text layer "scrambles reading order on
some pages" — so the polling-district table is now taken wholly from the
workbook rather than stapling its codes onto figures from the other source.
**This one seat is worth checking against the SPR PDF directly**; the state
total is unaffected either way.

**One known discrepancy.** In the **82-seat** workbook the ethnicity columns do
not sum exactly to the elector count: 75 of 82 seats are out by a few electors,
235 statewide (0.012%), worst case 0.087% on a single seat. Age and sex
reconcile exactly, and the 99-seat set is exact throughout. This is rounding in
the upstream source. Ethnic percentages are therefore computed against the sum
of the ethnicity columns rather than the elector total, so the shares always add
to 100%.

## Build

None. `index.html` carries the data, styles and scripts inline; `kuching.png` is
the only separate asset. The embedded dataset is generated from the two workbooks
in `data/` and reconciled against the SPR figures before it is written in.
