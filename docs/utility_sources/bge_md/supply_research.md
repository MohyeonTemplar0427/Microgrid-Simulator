# BGE supply research receipt

Reviewed October 25, 2026. Official sources only support implementation;
third-party rate databases were used solely to discover original documents.

## Schedule choice and eligibility

Use residential Schedule R and secondary-voltage General Service Schedule G
with BGE Standard Offer Service (SOS), Type I for G. Schedule GS has flat
delivery but time-of-use supply and is elective; it is not a flat-supply default.
The current GS sheet no longer contains the historical 2,000 kWh minimum quoted
by some rate databases.

[Rider 1, tariff pages 76-77](https://azure-na-assets.contentstack.com/v3/assets/blt71bfe6e8a1c2d265/blt970ee32f55c20fde/6abe810c794a172f39b99bc0/Rdr_1_9.pdf)
has an unchanged eligibility page effective February 1, 2023. G/GU/GS/SL receive
Type I except accounts assigned Type II. Type II criteria include metered
30-minute demand at least 25 kW, usage over 6,000 kWh in two consecutive winter
billing months (October-May), or over 7,500 kWh in one summer month
(June-September). A PJM capacity peak-load contribution of 600 kW or more belongs
to hourly service. SOS service type cannot change within an SOS year. Require
an independently confirmed account assignment; a study horizon cannot establish
historical eligibility. Applying stricter per-month study limits is a supported
subset, not the complete tariff eligibility test.

[Schedule G](https://azure-na-assets.contentstack.com/v3/assets/blt71bfe6e8a1c2d265/bltae5a035d36f7f19e/P3_SCH_G.pdf)
sets delivery seasons by billing periods ending June-September versus
October-May. Full calendar cycles avoid the unverified allocation of a cycle
crossing these boundaries. Secondary delivery is the proposed supported scope.

## Independently verified supply components

Values below are cents/kWh. Generation already includes administrative charges
and applicable supply taxes. Transmission already includes GRT and PSC
assessment. Rider 8 must be added separately; do not double-count either tax.

| Window | R energy/admin/tax | R generation/transmission | G energy/admin/tax | G generation/transmission |
| --- | --- | --- | --- | --- |
| Jan 2025 | 10.019 / .355 / .031 | 10.405 / 1.682 | 9.675 / .322 / .030 | 10.027 / 1.413 |
| Feb-May 2025 | 10.019 / .347 / .031 | 10.397 / 1.682 | 9.675 / .341 / .030 | 10.046 / 1.413 |
| Jun-Aug 2025 | not decomposed here | 10.247 / 2.322 | not decomposed here | 10.123 / 1.986 |
| Sep 2025 | not decomposed here | 13.496 / 2.322 | not decomposed here | 12.320 / 1.986 |
| Oct-Nov 2025 | not decomposed here | 14.321 / 2.322 | not decomposed here | 12.521 / 1.986 |
| Feb 2026 | 10.602 / .477 / .036 | 11.115 / 2.322 | 9.921 / .418 / .033 | 10.372 / 1.986 |
| Mar-May 2026 | 13.842 / .477 / .046 | 14.365 / 2.322 | 12.111 / .418 / .040 | 12.569 / 1.986 |
| Oct 2026 | 12.507 / .412 / .043 | 12.962 / 2.228 | see current sheet | 12.076 / 1.762 |

Sources and qualifications:

- [Supplement 728](https://www.bge.com/cdn/assets/v3/assets/blt71bfe6e8a1c2d265/bltafdea164ab2ca8e9/67656b943570d6863a327ab0/Johnston_Suppl728_ML314385.pdf?branch=prod_alias): physical page 10 redline preserves January 2025 prior rates; physical page 15 clean table verifies February-May. Its June 2025 projections were superseded and must not be implemented.
- [June-August 2025 final SOS sheet](https://www.bge.com/cdn/assets/v3/assets/blt71bfe6e8a1c2d265/blte65b1dd8c5037101/6841ae4babfad136cad48034/POLR_Rates_PTC_MiscCharges_January_Barnes.pdf?branch=prod_alias).
- [September 2025 final SOS sheet](https://www.bge.com/cdn/assets/v3/assets/blt71bfe6e8a1c2d265/blte65b1dd8c5037101/68b9ab98e477c8355a323b41/POLR_Rates_PTC_MiscCharges.pdf?branch=prod_alias).
- [October-November 2025 final SOS sheet](https://www.bge.com/cdn/assets/v3/assets/blt71bfe6e8a1c2d265/blte65b1dd8c5037101/68dbe17ce346510a223e59cd/POLR_Rates_PTC_MiscCharges.pdf?branch=prod_alias). Future comparison figures exclude unknown adjustments and are not final-rate evidence.
- [Supplement 751](https://www.bge.com/cdn/assets/v3/assets/blt71bfe6e8a1c2d265/blt1a0b1cc4f39d8a37/69fb4e3050f7ae24dd91cb6f/Johnston_Suppl751_ML329738.pdf?branch=prod_alias): physical pages 8-9 redlines preserve prior February-May 2026 rates, replacing R Supplement 746 and G Supplement 748. Tables required visual rendering; ordinary text extraction omitted them. Its June-September transmission figures are explicitly based on June 2025 transmission and await the annual transmission update, so they are not final June 2026 composite evidence.
- [Current October 2026 SOS sheet](https://www.bge.com/cdn/assets/v3/assets/blt71bfe6e8a1c2d265/blte65b1dd8c5037101/6abe9abda6ea1d360734e875/POLR_Rates_PTC_MiscCharges_5.pdf?branch=prod_alias) and Rider 1 physical pages 3-4 verify current rates. Transmission changed in June 2026: R 2.228, G 1.762. The OPC October 2026 informational page still quotes R transmission 2.322; use the filed utility sheet.

Supply tax notes: GRT 2% applies to transmission only. PSC assessment is .3013%
effective October 2024 and .3205% effective October 2025; the published composite
columns already include those amounts. Do not infer application to delivery
from these supply-table notes.

## Retrieval and remaining scope

The official Angular page returns no tariff text to a plain HTML fetch. Its
public content endpoint exposes the actual PDF links:
`https://eudapi.bge.com/content-api/api/content/products/other/pages`, with
`url=/my-account/my-dashboard/rates-tariffs/electric-service-rates-tariffs` and
`environment=live`. The companion index uses
`url=/my-account/my-dashboard/rates-tariffs/electric-service/electric-rates-information`.
This is a read-only public endpoint and requires no customer session.

Final supported months additionally require verified Rider 8, delivery riders,
tax jurisdiction, minimums, cycle rules and benchmark reconciliation. This receipt
alone does not claim a complete bill or authorize interpolation.

The delivery research subsequently recovered the original complete
[CSEG ledger](https://www.bge.com/cdn/assets/v3/assets/blt71bfe6e8a1c2d265/blt8ad3da6ba8d050f5/6acfc043f4251ab7b699fb93/Rdr32_CS_Current_Rates_12.pdf?branch=prod_alias).
Independent readback of physical pages 2 and 6 resolves the June-September 2026
gap: R generation $0.12519/kWh, transmission $0.02228/kWh and Rider 8
-$0.00138/kWh; G generation $0.12140/kWh, transmission $0.01762/kWh and
Rider 8 -$0.00285/kWh. These dated ledger columns establish the final rates;
the earlier Supplement 751 transmission projections are superseded. Physical
pages 12 and 16 preserve the full 2025 R and G histories. November-December
2026 columns are blank and do not establish those months.
