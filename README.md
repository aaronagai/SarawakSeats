# SarawakSeats

A simple, readable view of the Election Commission's (SPR) **proposed** 2026
redelineation for Sarawak — all 99 state constituencies (DUN), their 1,141
polling districts (daerah mengundi), and elector counts.

SPR publishes this for public reading, but only inside a flipbook PDF viewer
that is hard to search or read on a phone. This is the same data, searchable.

## Status of the data

These are **syor yang dicadangkan** — proposed recommendations, not gazetted
boundaries. Public exhibition ran 1–30 September 2026 and objections can still
change them. Refer to SPR's own documents for any official purpose.

## Source

Notis Syor Untuk Pameran Kali Pertama, Jadual Kedua (Second Schedule) —
notice under Section 4, Part II of the Thirteenth Schedule to the Federal
Constitution, Article 113(2). Elector counts are from the electoral roll
gazetted 29 January 2026 [P.U. (B) 35/2026].

Portal: https://myst.spr.gov.my/pameran-syor

## Accuracy

Extracted from the PDF by word coordinates (its text layer scrambles reading
order on some pages), then reconciled against the notice's own subtotals:

- every DUN subtotal (99/99)
- every federal constituency subtotal (31/31)
- the stated state total of 2,037,648 electors

Names and figures were additionally cross-checked by a second, independent
extraction pass and by reading rendered pages.

## Build

None. Single self-contained `index.html` with the data inlined.
