# Pepco Maryland supply research

Reviewed October 26, 2026. Maryland only; District of Columbia schedules and
rate documents are excluded. Scope is ordinary Schedule R residential and
low-voltage Schedule GS general service with Pepco Standard Offer Service
(SOS). This receipt proves the listed components, not complete bill coverage.

## Eligibility and clocks

Current tariff physical pages 8-9 (R), 12-13 (GS), 101-103 and 108 (SOS):

- R is residential service. GS is low-voltage general service, normally single
  phase 120/240 or 120/208 V, or three phase 120/208 or 265/460 V. Temporary,
  railway-propulsion and separately metered supplementary loads are excluded.
- GS excludes accounts reaching a maximum 30-minute demand of 25 kW or more
  in any one of twelve billing months; exceeding 6,000 kWh in two consecutive
  winter billing months (November-May); or exceeding 7,500 kWh in a summer
  billing month (June-October). Schedule transfers occur annually with the
  June billing month. Model intervals alone cannot establish prior account
  history or utility assignment.
- Rider SOS assigns R to residential SOS and GS to Type I. The customer may
  not change SOS type within an SOS year. Require separately confirmed GS
  assignment and ordinary service/supplier eligibility.
- Distribution seasons are billing months June-October versus November-May.
  Generation strips below instead explicitly use June-September versus
  October-May dates. Keep those clocks separate. The filed generation and
  transmission revision footers specify usage on/after their effective dates.
- PCA is a separate monthly $/kWh item applied to billed kWh. True-ups occur
  at least in June, November and February billing months; this is not authority
  to hold a missing monthly value constant. Administrative charges typically
  change in February, June and October; use final dated tables.

## Verified generation and embedded administrative charge

All values are dollars/kWh, before separate PCA and transmission GRT. `Total`
is energy plus its administrative charge; do not add admin a second time.

| Usage window | R energy | R admin | R total | GS energy | GS admin | GS total | Source |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Jan 2025 | .10115 | .00391 | .10506 | .10050 | .00326 | .10376 | book_2024_dec pp98-99 |
| Feb-May 2025 | .10115 | .00589 | .10704 | .10050 | .00530 | .10580 | book_2025_feb pp98-99 |
| Jun-Sep 2025 | .09882 | .00515 | .10397 | .09806 | .00421 | .10227 | book_2025_jul pp98-99 |
| Oct 2025-Jan 2026 | .10620 | .00525 | .11145 | .10377 | .00452 | .10829 | book_2025_sep pp97-98; book_2025_dec pp97-98 |
| Feb-May 2026 | .10620 | .00500 | .11120 | .10377 | .00493 | .10870 | book_2026_jun pp98-99 prior-period columns |
| Jun-Sep 2026 | .10764 | .00404 | .11168 | .10675 | .00362 | .11037 | book_2026_jun pp98-99 |
| Oct 2026 | .12266 | .00415 | .12681 | .11923 | .00367 | .12290 | book_current pp102-103 |

Earlier future-period administrative projections are superseded by the final
period table. The October 2026 final admin rates supersede June's projected
October rates. Blank or future PCA columns do not extend coverage.

## Verified transmission and boundaries

| Usage window | R $/kWh | GS $/kWh | Source |
| --- | ---: | ---: | --- |
| Jan-Aug 2025 | .01951 | .01302 | book_2024_dec pp98-99; book_2025_jul pp98-99 |
| Sep 2025-Aug 2026 | .02101 | .01423 | book_2025_aug26 pp97-98, explicitly effective September 1, 2025 |
| Sep-Oct 2026 | .02007 | .01421 | book_2026_aug pp102-103, explicitly effective September 1, 2026 |

Pepco's tariff states transmission includes **separately calculated GRT**.
Its official bill education example shows 2.0408% gross-receipts tax on the
transmission energy charge. These table rates must not be treated as BGE's
already tax-inclusive transmission composites. Tax interpretation and dated
local surcharges are handled by the tax research stream.

## Monthly PCA values verified in this stream

These are signed retail bill rates, dollars/kWh. Parentheses on utility charts
are credits. Community-solar credit tables reverse charge/credit signs; do not
copy their signs directly into retail billing.

| Month | R PCA | GS Type I PCA | Source |
| --- | ---: | ---: | --- |
| Jan 2025 | -.0017815 | -.0154652 | pca_2025_feb p1 |
| Feb 2025 | -.0030934 | -.0162402 | pca_2025_feb p1 |
| May 2026 | .0031853 | -.0149533 | delivery cseg_oct2026 pp1/4 |
| Jun 2026 | .0042037 | -.0155223 | pca_current p1 |
| Jul 2026 | .0045355 | -.0164524 | pca_current p1 |
| Aug 2026 | .0053515 | -.0176268 | pca_current p1 |
| Sep 2026 | .0055633 | -.0180350 | pca_current p1 |
| Oct 2026 | .0054696 | -.0179397 | pca_current p1 |

**Unverified: March 2025-April 2026 monthly PCA.** Do not interpolate,
carry neighboring values or claim a full-year 2025 bill without another
verified component source. The delivery stream separately owns CSEG-history
research. Its October 2026 original resolves May 2026 as shown above.

## Administrative delivery credit

Separate from the supply admin charge above. Verified credit magnitudes:
R Jan 2025 .0016300; Feb/Mar 2025 .0010900; GS Jan-Mar 2025 zero
(`admin_credit_2025_mar`, p1). R Jun-Sep 2026 .0011800, Oct 2026 .0012500;
GS Jun-Sep 2026 .0006900, Oct 2026 .0007100 (`admin_credit_current`, p1).
The delivery stream's October 2026 CSEG original independently verifies May
2026 R credit .0012200 and GS credit .0003400 (physical pages 1 and 4).
Apply confirmed credit amounts with a negative bill sign. Other historical
months remain unverified in this stream.

## Source preservation and verification

Original PDFs, full text, selected-page excerpts and outlined-table rendered
receipts are in ignored `.cache/pepco_md/sources/supply/`. The cache's
`supply_records.json` records each exact original URL, full SHA-256 and physical
PDF page selections. The following are the decisive originals; page numbers
above are physical PDF pages, one-based.

- [book_2024_dec](https://azure-na-assets.contentstack.com/v3/assets/bltbb7c204688a1a6a8/blt755a78723a5a305f/677311681931feb3f86c0d5d/2024-12-11_MASTER_MD_Pepco_Tariff_Book.pdf); SHA-256 `366d8ebc0dcbb84048a261f43b28fdbb0ac37946d0e65b5b73d55e3a8526d21e`.
- [book_2025_feb](https://azure-na-assets.contentstack.com/v3/assets/bltbb7c204688a1a6a8/blt194fef58574d7d43/6836297cc286f0907ec6c6d0/2025-02-28_MASTER_MD_Pepco_Tariff_Book_1.pdf); SHA-256 `d51c12b339765dfb3c12b7f7b17be6f63ffc68d9eebc9aa8e52c9d90196655eb`.
- [book_2025_jul](https://azure-na-assets.contentstack.com/v3/assets/bltbb7c204688a1a6a8/blt524bceaba0d0f205/6883d65a92c95443b3eb59f9/Pepco_MD_Current_Tariff_7.11.2025_.pdf); SHA-256 `cd0c8826e6af366ee72635725601ed344c2a23b1c0e6e110871bd6a245c70b84`.
- [book_2025_aug26](https://azure-na-assets.contentstack.com/v3/assets/bltbb7c204688a1a6a8/blt3933b07bcf0bbc31/68cc32852755d540bf48c859/2025-08-26_MASTER_MD_Pepco_Tariff_Book_(1).pdf); SHA-256 `5f82fc679a10ec69363c164f5c621d34b0829f223434152b336d077aca81d882`.
- [book_2025_sep](https://azure-na-assets.contentstack.com/v3/assets/bltbb7c204688a1a6a8/blt598d25d06beca65e/6984d230c4f5dcf21b846917/2025-09-17_MASTER_MD_Pepco_Tariff_Book_.pdf); SHA-256 `a6debb3e9f946702d210650e54e4e9f72a46ccdfe12194fbe5b0a0c53e720951`.
- [book_2025_dec](https://azure-na-assets.contentstack.com/v3/assets/bltbb7c204688a1a6a8/bltc311d360885f64f9/6984d3a7c529c64103cf0ec2/2025-12-31_MASTER_MD_Pepco_Tariff_Book_.pdf); SHA-256 `758679a8d1a247b9523cf32afa1c7da1776091b73435ad0dd9ea5d2225ee4ab1`.
- [book_2026_jun](https://azure-na-assets.contentstack.com/v3/assets/bltbb7c204688a1a6a8/blt0f5bcbdddd461eef/6a6d09371189f91f28cc80c6/9232_Pepco_MD_CURRENT_CLEAN_SOS_Filing_eff_060126.pdf); SHA-256 `0e0d7731da97d8001ab66dba977a2cde6888c769eebb786554bbb7ebf5b5e003`.
- [book_2026_aug](https://azure-na-assets.contentstack.com/v3/assets/bltbb7c204688a1a6a8/bltd839da018e95c86c/6abad7751cd4a4dc6a413611/2026-08-20_MASTER_MD_PEPCO_Tariff_Book_1.pdf); SHA-256 `15f2ee9b641ca6da025e322e8ac789e4cbe7cfe3e75908cd8fe33406ab8a4091`.
- [book_current](https://www.pepco.com/cdn/assets/v3/assets/bltbb7c204688a1a6a8/blte8a580e4cc79e2c4/6abad89015d5b7d18eb100f3/9232_AND_9761_Pepco_MD_CURRENT_CLEAN_Admin_Ch_.pdf?branch=prod_alias); SHA-256 `48da9de9906dbadfb6c080ad7917e02f57ebf28ec219a57df76f4a87abca424a`.
- [pca_2025_feb](https://www.pepco.com/cdn/assets/v3/assets/bltbb7c204688a1a6a8/blt9e3743d1d4f743f9/679d1303c9ecbb3763c0d104/Pepco_MD_SOS_-_PCA_022025.pdf?branch=prod_alias); SHA-256 `714d2000c0c44ea27757942d104f6180a7fad523248fa3e8410bc0b0d69d2099`.
- [pca_current](https://www.pepco.com/cdn/assets/v3/assets/bltbb7c204688a1a6a8/blt9e3743d1d4f743f9/6abd8ce1d4633692b4c108e9/Pepco_MD_PCA_-_102026_.pdf?branch=prod_alias); SHA-256 `07d646f03d1c9d1950dd3525ae137b4af8212ebce7c6a86abbb30ce86700b638`.
- [admin_credit_2025_mar](https://www.pepco.com/cdn/assets/v3/assets/bltbb7c204688a1a6a8/blteda6ce8aea39a7c0/67c5e1da64440c13171e98ff/Pepco_MD_Admin_Credit_-_032025.pdf?branch=prod_alias); SHA-256 `64fc40a2e03cbf111b934b251c273c6576249bc0f9220edaf8fe533c5e0dee89`.
- [admin_credit_current](https://www.pepco.com/cdn/assets/v3/assets/bltbb7c204688a1a6a8/blteda6ce8aea39a7c0/6abd91df9c17130cafc66f32/Pepco_MD_Admin_Credit_-_102026_.pdf?branch=prod_alias); SHA-256 `97d9af9f2275aa51ebfb4bbfcbf4cbc7c8960590ea63beca502d5937fc84207f`.
- [bill_education_2025](https://azure-na-assets.contentstack.com/v3/assets/bltbb7c204688a1a6a8/blt25da1effbd15aac6/6814f48b4fad9846f3c40b76/Pepco-MD_Bill_Education_Fact_Sheet_ada.2.pdf); SHA-256 `145835664f82e46cb7d82b969a75a19830595c19f14639a2b002148c492302f4`.

PCA and admin-credit current PDFs have outlined tables omitted by ordinary
text extraction; their PNG renders were read visually. The official 987-kWh
bill education example spans January 29-February 25, 2025 and has blended
supply energy/admin $0.1068693/kWh; it is a useful independent itemized example,
not a complete-calendar February benchmark. Its PCA is -$0.0030934/kWh and
its transmission GRT is separately shown as 2.0408%.

Public source discovery used Pepco's `eudapi.pepco.com/content-api` endpoint,
`/api/content/products/other/pages`, `environment=live`, with page URL
`/my-account/my-dashboard/rates-tariffs/maryland/current-tariffs` and its sibling
`tariff-archive`. Public index responses are preserved in the same cache.
The public search index exposes current documents but did not recover the
missing historical PCA charts. A discovered `Procurement_Cost_Adjustment_6.1.2025_.pdf`
was inspected and proved to be a DC document; it is explicitly excluded.
No proposed tariffs, DC prices, wholesale PJM prices or neighboring utilities
were substituted for missing Maryland retail components.

The final bounded history pass used two targeted query batches: exact
2025 CSEG December/June and filename strings, then official-domain annual and
monthly history phrases. It recovered only the previously known January and
February 2025 snapshots. The current
[October 2026 CSEG original](https://www.pepco.com/cdn/assets/v3/assets/bltbb7c204688a1a6a8/blt184aa0644dce17a4/6abebe49c7c45d25867c0a5a/CSEG_MD_Pepco_-_10_2026_.pdf?branch=prod_alias)
provides May-October 2026, not the missing March 2025-April 2026 history.
This records evidence not recovered by these routes; it does not assert that
no historical document exists. Query details are pinned in the cache's
`history_search_receipt.json`. `supply_source_manifest.json` consolidates exact
original, full-text, selected-page and visual-receipt hashes for the combined
source ledger, including explicit exclusion of the DC and Type II-only files.
