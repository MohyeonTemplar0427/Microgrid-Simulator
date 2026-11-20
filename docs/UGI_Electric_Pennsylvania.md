# UGI Electric Pennsylvania

UGI Utilities, Inc. – Electric Division supplies ordinary Rate R residential and Rate GS-1 small-general-service accounts under Rider B GSR-1. The simulator accepts complete calendar meter cycles in Eastern time, billed on the last service date. Rate sources were reviewed on November 19, 2026. The source ledger identifies the exact filed supplement, page, effective date, PDF fingerprint and retrieval route. [Official electric tariff archive](https://ugi.outsystemsenterprise.com/UGITariff_FO/TariffDetail?TariffId=211) · [Source ledger](utility_sources/ugi_pa/sources.json)

## Calendar coverage

| Plans | Completed service cycles | In progress November 19, 2026 | Published forward service |
| --- | --- | --- | --- |
| R and GS-1 | February–August and October–December 2025, February–June and August–September 2026 | November 2026 | GS-1 only, December 2026 |

Five cycles cross a service-rendered change to Rider A, on January 20 and September 20, 2025, and January 19, July 20 and October 19, 2026. The filed sheets establish both prices. Rule 13(a) addresses unusually long or short bills and leaves allocation of the monthly fixed charge across these particular changes unresolved. Those five cycles reject, so annual 2025 billing is unavailable. Meter periods shifted from calendar months, partial cycles, estimated readings and provisional rates also reject. [Rule 13 and Rider A](https://www.ugi.com/wp-content/uploads/2026/03/BOOK%20IX%20(Current%20Tariffs)_ADA.pdf)

The public compiled Supplement 101 sets the December 2026 GSR-1 prices. Its GS-1, A, E and G sheets establish the other ordinary small-commercial charges. Supplement 95 requires a residential USP recalculation when the GSR changes. The December residential USP filing was unavailable as of the review date. Supplement 94 suspended the proposed base rates in Supplement 92 until January 1, 2027. November and December bills carry an explicit timing label. [Filed electric supplements](https://ugi.outsystemsenterprise.com/UGITariff_FO/TariffDetail?TariffId=211)

## Accounts and settlement

- **R** covers a single dwelling or individual dwelling unit. The filed schedule also allows certain nonresidential uses below 2 kW. This implementation accepts a solely residential meter because a mixed-use meter has different Pennsylvania tax treatment. The ordinary monthly customer charge is $10.75 and the distribution energy charge is 5.290¢/kWh.
- **GS-1** covers established ordinary general lighting or power on the utility’s distribution lines with utility-determined demand at most 5 kW at any time of year. The customer charge is $17.00 and distribution is 5.987¢/kWh. Recurring months above 2,000 kWh ordinarily trigger demand metering unless the utility establishes eligibility separately. The implemented subset requires an active standard yearly contract, the utility’s independent annual assignment and demand record, and native and imported consumption at most 2,000 kWh per month with a 5 kW peak. The public-worship exception, metered-demand cases and recurring higher use are outside this subset. Solar production cannot establish the historical class. [Rates R and GS-1, pp. 53 and 62](https://www.ugi.com/wp-content/uploads/2026/03/BOOK%20IX%20(Current%20Tariffs)_ADA.pdf)
- **Default supply** uses UGI as retail supplier. Before June 2025, Supplement 52 placed R and GS-1 directly in GSR-1. From June 2025, Supplement 80 places all residential customers in GSR-1 and requires a separate utility-determined supply peak load impact below 100 kW for a nonresidential account. This uses the highest impact in the twelve months ending September 30, or the utility’s estimate for a new account. The service model requires an established ordinary account and excludes individual migration reconciliations, third-party suppliers, hourly GSR-2 and special contracts. [Rider B and prior default-service sheets](https://ugi.outsystemsenterprise.com/UGITariff_FO/TariffDetail?TariffId=211)
- **Jurisdiction and grid** are independent account facts. The tariff lists Dallas Borough in Luzerne County among its electric service locations. Ordinary state sales tax is 6% for a fully taxable private GS-1 business. A residential purchaser’s own solely residential electricity qualifies for exemption. Financial assistance, partial-use exemptions, special facilities, optional services and unpaid balances are outside scope. PJM lists UGI Electric Service in transmission zone UGI. No utility, supplier or wholesale price follows from location alone. [Pennsylvania sales tax](https://www.pa.gov/agencies/revenue/resources/tax-types-and-information/sales-use-and-hotel-occupancy-tax) · [Metered use under 61 Pa. Code §32.25](https://www.pacodeandbulletin.gov/secure/pacode/data/061/chapter32/s32.25.html) · [PJM zone directory](https://emergencyprocedures.pjm.com/ep/pages/regions.jsf)
- **PV and paired storage** require final UGI approval for the exact renewable installation and any battery, prior activation, one bidirectional meter, ordinary import-rate treatment and no additional recurring charge. Rule 17 applies R or GS-1 to net purchases. With zero exports and an empty credit bank, these equal the measured imports. The simulator caps combined equipment at 10 kW in this small-inverter subset and requires PV-only charging for storage. EIA’s UGI return records four residential and one commercial PV-paired battery installations in 2025. Individual approval and tariff classification still require account evidence. Standalone storage, exports, credit balances, annual payouts, aggregation and application fees are outside this modeled account. [UGI interconnection requirements](https://www.ugi.com/resources-for-customer-generation/) · [Rule 17](https://www.ugi.com/wp-content/uploads/2026/03/BOOK%20IX%20(Current%20Tariffs)_ADA.pdf) · [EIA-861 utility data](https://www.eia.gov/electricity/data/eia861/)

## Dated charges

Each base rate has a minimum monthly charge equal to its customer charge. Rider E applies to both classes. Rider C applies only to residential R. Rider G DSIC multiplies the customer charge, distribution energy, EEC and any USP, using the bill-rendered date. Rider A STAS multiplies those distribution charges plus DSIC and GSR-1 supply, using the service date. State sales tax then applies to the taxable commercial purchase price. GSR-1 already includes capacity, transmission, ancillary costs, administration and gross receipts tax. The utility’s posted price to compare includes STAS and is used for reconciliation. [Tariff and rider sheets](https://ugi.outsystemsenterprise.com/UGITariff_FO/TariffDetail?TariffId=211) · [Taxable purchase price](https://www.pacodeandbulletin.gov/secure/pacode/data/061/chapter33/s33.2.html) · [UGI posted prices](https://www.ugi.com/price-to-compare/ugi-electric/)

| First service date | R GSR-1, ¢/kWh | GS-1 GSR-1, ¢/kWh | R USP, ¢/kWh |
| --- | ---: | ---: | ---: |
| December 1, 2024 | 10.637 | 10.637 | 2.121 |
| June 1, 2025 | 11.470 | 11.005 | 2.222 |
| December 1, 2025 | 11.211 | 10.758 | 1.868 |
| June 1, 2026 | 12.616 | 12.093 | 2.120 |
| December 1, 2026 | 12.401 published | 11.886 published | Unverified |

| Rider | Filed rates |
| --- | --- |
| EEC R / GS-1 in ¢/kWh | From September 1, 2024, 0.151 / 0.122. From September 1, 2025, 0.181 / 0.233. From September 1, 2026, 0.170 / 0.343. |
| DSIC, service bills from quarter start | 2025 Q1–Q4 at 0.32%, 0.74%, 1.23%, 1.41%. 2026 Q1–Q4 at 1.83%, 2.28%, 3.25%, 4.46%. |
| STAS | 0.00% entering 2025, +0.01% from January 20, 2025, +0.02% from September 20, 2025, +0.01% from January 19, 2026, 0.00% from July 20, 2026, and −0.01% from October 19, 2026. |

## Bill reconciliation

UGI’s March 2026 rate-case Exhibit E provides an independent check on the charge bases for both classes. Its pro forma uses 5.00% DSIC and 0.02% STAS. Applying the reported class volumes reproduces residential DSIC of $2,307,136 and STAS of $21,826, and GS-1 DSIC of $132,690 and STAS of $1,023 at the exhibit’s whole-dollar precision. Applying those same projected factors to a residential 1,000 kWh month gives the utility’s published $200.50 example. The operating March 2026 tariff instead uses 1.83% DSIC and 0.01% STAS. [Exhibit E, pp. 2–3, PDF pp. 233–234](https://www.ugi.com/wp-content/uploads/2026/03/BOOK%20IV%20(Exhibits%20A,%20B%20and%20E)_ADA.pdf) · [UGI customer notice](https://www.ugi.com/notices/)

The independent Decimal test reconstructs each enabled plan-month from a separate transcription, verifies each raw and cent-rounded line, and checks the zero-usage minimum, signed STAS, spring and autumn DST, numeric and symbolic agreement, eligibility, missing intervals and rejection of exports. Study rounding uses each component rounded half-up to cents. The source receipt records the basis for the rounded website PTC and EIA class totals. [Independent tests](../test/test_ugi_pa.py) · [Source inventory](utility_sources/ugi_pa/sources.json)
