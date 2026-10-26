# Ohio Power Company source evidence

Reviewed October 25, 2026. See [billing scope](../../AEP_Ohio.md) for supported
classes, dates and exclusions. Sources belong to Ohio Power Company/AEP Ohio,
not Ohio Edison. No wholesale price is used as a substitute for retail rates.

`sources.json` identifies original official utility/PUCO PDFs and the public
indexed text of historical official sheets whose originals no longer download.
The latter records have **null original hashes**; their checked-in factual
extract hashes do not pretend that a PDF binary was recovered. Original
documents remain in ignored `.cache/ppl_aep_ohio/` storage. No credentials or
private customer bills are included.

The utility's public QA hostname preserves April, June and July 2025 and June
and July 2026 tariff-book originals that the main hostname now returns as 404.
This is public first-party archival content, accessed over verified TLS without
authentication. The regulator's public No. 21 and No. 22 books provide
additional original sheets. A book title is not a rate's effective date.

Notable source limitations are retained rather than erased:

- The archived July 2025 book's LGR sheet is stale; the later official indexed
  August book contains the correct July-effective eighth revision.
- The October 2026 utility book embeds an obsolete No. 21 EDCR sheet. The
  applicable No. 22 original and independently matching utility examples
  establish the correct 1.80190% factor.
- Regulator No. 21 page 164 has a broken text-font mapping. ESRR 7.88222% and
  the December 2025 effective date were read from the rendered original and
  preserved in a separate visual fact extract.
- The April 10, 2026 price changes do not establish an April calendar-cycle
  allocation rule. That month remains rejected; no provisional model exists.

Early history in PUCO's PTC chart was inspected toward the project's ten-year
research target. It is a rounded residential supply cross-check, not complete
ten-year retail coverage, a commercial rate source or an extra charge.
