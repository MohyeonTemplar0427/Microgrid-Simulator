# Duquesne RS / GS account, tax and DER rules

Verified 2026-10-29. These are source-reading notes and implementation scope
recommendations, not a transcript of the complete current tariff. Parent research
retains the current tariff's original URL and blocked direct-download receipt.
Primary cached-current-PDF text was readable; selected current-tariff screenshot
requests returned cache misses. The separate original 2025 STAS filing and
acceptance letter were downloaded from the PUC and hashed; its printed page 112
was rendered and visually checked as described below.

## Primary filed tariff

[Supplement 110, Tariff 25, effective October 1, 2026](https://www.duquesnelight.com/docs/default-source/default-document-library/tariff-no-25-%28110%29-effective-10-01-2026---rider-no-22---distribution-system-improvement-charge-%28dsic%29-quarterly-filing.pdf).
PDF page numbers below are one-based; printed tariff numbers are separate.

| Rule | Source and dated page | Verified meaning |
| --- | --- | --- |
| Service territory | PDF 5-6, printed 4-5, original December 2, 2019 | Parts of Allegheny and Beaver counties; facilities and actual service must be confirmed. Beaver County's listed communities include Center Township. Coordinates do not establish service. |
| Standard service | PDF 7, printed 6, Supplement 85, effective December 20, 2024; voltage list effective January 1, 2025 | Standard 120/240 V, three-wire single-phase service exists. A study can restrict both classes to one such meter rather than infer arbitrary voltage/phase eligibility. |
| RS eligibility | PDF 43, printed 38, Supplement 85 effective December 20, 2024 | Residential/combined residential-farm household use; associated commercial/professional use must be below 25% of monthly usage. At most 240 V single-phase through one meter to one dwelling/unit. Solely residential is the narrower tax-safe initial scope; mixed use is not automatically wholly sales-tax exempt. |
| RS minimum | PDF 44, printed 39 | The customer distribution charge is the schedule minimum; riders retain their own rules. Late-payment charges are separate and excluded from ordinary modeled current charges. |
| GS distribution class | PDF 51, printed 46, Supplement 85 effective December 20, 2024 | GS is non-demand service, with $18 customer charge and 8.4601 cents/kWh distribution energy. GM is separately demand metered. Do not apply GM's demand price to GS. |
| GS assignment | PDF 51-52, printed 46-47 | New/limited-history assignment uses Company estimates for the next 12 months. Existing GS assignment lasts 12 months; on review the rolling 12-month averages must be at most 1,000 kWh and 5 kW. Exceeding either moves to the applicable GM class next cycle. Company confirmation and history are separate from optimized import quantities. |
| Metering threshold | PDF 54, printed 49, original December 2, 2019 | Demand is measured if a month's energy exceeds 1,000 kWh or known demand exceeds 5 kW. Demand measurement uses the greatest 15-minute average. A stricter initial domain can keep every native/current/historical month under these quantities, but that is not the tariff's rolling-average assignment rule. |
| GS/GM minimum | PDF 53, printed 48, Supplement 36 effective January 15, 2022 | Paragraph is under the common non-demand/demand heading, not explicitly GM-only. It includes customer distribution plus demand based on 30% of the highest preceding-11-month billing demand, plus current Company supply/transmission charges. Its closing customer-charge-floor sentence has ambiguous grammatical scope for GS. See bounded treatment below. |
| Default supply eligibility | PDF 52, printed 47 | Non-demand customers are eligible for Rider 8; larger average-demand customers have different classes or Rider 9. GS does not acquire PJM hourly pricing just because the utility operates in PJM. |
| 2025 STAS | PUC 1860313 PDF 7, printed 112, Supplement 86, issued December 20, 2024 and effective January 1, 2025; PUC 1861038 acceptance January 2, 2025 | Part 1 is negative 0.1278% on distribution; Part 2 is explicitly 0.0000% on all bill portions. Bills-rendered clock; calculation pages 8-9 explicitly cover January 1-December 31, 2025. The utility history's January 1, 2024 date is contradicted by the original primary documents. |
| 2026 STAS | Current PDF 126, printed 112, Supplement 98 effective January 1, 2026 | Part 1 is negative 0.0964% on distribution; Part 2 is explicitly 0.0000% on all bill portions. The application language is bills rendered. The current page is not proof of the 2025 price. |
| TSC | PDF 168, printed 146 | TSC is outside the rate-schedule minimum, receives no credits/discounts, and is not affected by STAS. Filed calculations already gross up applicable GRT; do not add a second 5.9% charge. |
| DSIC | PDF 155-156, printed 138-139 | DSIC base is all billed distribution service excluding STAS. STAS then applies to DSIC. DSIC is outside the schedule minimum, is not credit/discount eligible, and cannot reduce minimum bills. Delivery research owns numeric dated values. |
| SMC | PDF 147, printed 131 | SMC is outside the schedule minimum; cannot reduce minimum bills; STAS applies. Delivery research owns dated values and zero/negative cases. |
| Renewable customer-generators | PDF 149-150, printed 133-134, Supplement 36 effective January 15, 2022 | Rider 21 applies to approved qualifying renewable generation at RS/GS/GM and other listed classes. Residential nameplate limit is 50 kW; commercial limit is 3,000 kW, with separate exceptional 3-5 MW provisions. Actual application and written Company approval are required; a model-size guard is not approval. |
| Ordinary net-import billing | PDF 150-151 and 153, printed 134-135 and 136A | Underlying schedule's customer/demand/other charges and minimum remain. With no exports and no opening bank, there is no export credit to calculate. Export banking/May31 settlement, supplier switching and aggregation remain outside a zero-export implementation. June2025 changes involve TOU detail; do not infer old export terms from a current page. |
| Standby rider | PDF 137, printed 123, effective May 12, 2022 | Rider 16 applicability lists GM, GMH, GL, GLH and L, not RS or non-demand GS. No standby price is invented for the narrow RS/GS ordinary-service scope. Contracted exceptional service is excluded. |

## Minimum-bill limitation

The combined GS/GM minimum paragraph does not provide an unambiguous standalone
GS dollar demand price. Keep the exact paragraph reference; do not manufacture
a GM rate for GS, erase old contract obligations, or silently assume all minimum
cases are settled. A narrowly accepted existing GS account should separately
confirm continuous non-demand GS, no prior GM/priced-demand minimum and no
contract minimum obligation, with preceding history preserved.

If the implementation needs to avoid the common paragraph's two plausible
customer-floor readings, accept only solutions whose current base distribution
and current distribution after riders both exceed twice the customer charge,
with an explicit cent tolerance. This is an **inactive-domain bound**, not a
filed two-customer-charge tariff minimum and never an added bill line. Current
Company DSS/TSC appear on both sides of the comparison. Low-import cases should
reject after solving rather than force purchases to cross an invented minimum.
Exact low-usage/zero-import minimum ordering remains unverified unless a further
official source resolves it. Root owns the final accepted guard and wording.

## Tax jurisdiction and purchase-price rules

Official source URLs and downloaded HTML hashes are recorded in
`tax_sources.json`; raw HTML/text stays in `.cache/duquesne_pa/sources/rules/`.

- PA DOR states the sales-tax rate is 6%; Allegheny adds 1%, Philadelphia 2%.
  Restricting a separately confirmed ordinary business meter to Beaver County
  avoids those two local sales-tax jurisdictions. This is not a statement about
  every possible special municipal, contractual or exempt account.
- DOR's residential-utility answer (updated March 3, 2026) and 61 Pa. Code
  32.25 address residential electricity exemption. Business/mixed-use,
  common-area, corporate-purchased and specially exempt accounts need their own
  treatment. The direct FAQ download returned 403, while the official cached
  page and directly downloaded 61 Pa. Code 32.25 were readable.
- 61 Pa. Code 33.2(a) includes delivery, Commonwealth taxes and passed-through
  vendor costs such as GRT in taxable purchase price. Thus ordinary taxable GS
  sales tax is applied to the complete ordinary charge subtotal, not energy
  supply alone. Discounts reduce the sale price under the rule's conditions.
- 61 Pa. Code 60.16 makes taxable utility service locally taxable where its
  registering meter is in a taxable county. Meter location, not mailing address
  or generic city coordinates, controls this regional tax fact.
- PA DOR confirms electricity GRT is 59 mills on the seller's gross receipts.
  This is distinct from residential sales-tax exemption. Embedded tariff GRT
  must not be added twice.
- No additional ordinary Center Township customer electricity-tax line was
  established in this bounded source review. Retain explicit state-only/local-
  charges confirmation; other localities and unusual taxes remain unsupported.

## DER scope recommendation

Require already-active Company-approved qualifying renewable PV and any attached
storage, one ordinary meter, no aggregation, zero opening bank and zero export.
Require PV-only battery charging and no battery export unless another verified
agreement establishes broader scope. The public Company application portal
explicitly requests a battery addendum, but that does not independently approve
an account or demonstrate historical battery eligibility. Standalone storage,
nonrenewable generation, Rider16 contracts and export settlement remain excluded.

Suggested hypothetical site: Center Township, Beaver County, approximately
40.65,-80.31, with distribution utility, tax-meter jurisdiction and eligibility
independently declared. This is not a service-boundary or actual-account finding.

## Unverified boundaries

Irregular/partial-cycle proration and component crossings are not resolved here;
complete calendar cycles are a model scope restriction, not an assertion that
Duquesne's actual meter calendar follows month ends. Exact printed cent-rounding
and low-usage minimum sequencing are unverified. No original complete-current-
tariff PDF binary or current-page visual pass is claimed from the blocked route;
the original PUC-hosted 2025 STAS supplement is a separate verified exception.
No live customer account, approval, entitlement or supplier agreement was inspected.

## Original 2025 STAS audit

The official [R-2024-3052641 docket](https://www.puc.pa.gov/docket/R-2024-3052641)
identifies Supplement 86 as effective January 1, 2025. It links the original
[11-page filing](https://www.puc.pa.gov/pcdocs/1860313.pdf) and the
[January 2, 2025 acceptance letter](https://www.puc.pa.gov/pcdocs/1861038.pdf).
Both downloads returned HTTP 200 PDF bytes. `stas_2025_sources.json` records
their SHA-256 identities, sizes, retrieval timestamps, source pages and exact
prices/bases/application clock. Selected original text is retained in the two
`stas_2025_*_excerpts.txt` files.

The filing cover letter, supplement cover, printed page 112 header, and 2025
calculation-period headings all state January 1, 2025. The PUC letter expressly
accepts negative 0.1278% Part 1 and zero Part 2 effective that date. The utility
history's January 1, 2024 text is therefore recorded as a source typo rather
than inferred as a different rate window. No remaining 2025 STAS value or
effective-date gap is identified by this audit.

Printed page 112 was rendered to
`.cache/duquesne_pa/sources/rules/stas_2025_verified-07.png` and visually checked:
the decrease marker, parenthesized 0.1278%, explicit 0.0000%, distribution/all-
portions bases, bills-rendered wording and January 1, 2025 footer were legible
and consistent with the extracted text. Poppler emitted font-cache errors on
the following calculation page; the needed tariff page rendered successfully,
and no separate visual pass of the following page is claimed.
