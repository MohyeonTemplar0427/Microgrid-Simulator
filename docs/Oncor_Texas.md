# Oncor Electric Delivery and Texas retail contracts

The local study form lists the following contracts for separately confirmed Oncor accounts. Oncor sets the delivery charges. The retail electric provider (REP) sets the supply price. ERCOT is recorded as grid operator with no wholesale settlement point. A Houston hub price or PJM carbon series cannot enter this calculation.

## Plan list

| Customer | Oncor delivery schedule | Retail contract | Supply price before delivery |
| --- | --- | --- | --- |
| Residential | §6.1.1.1.1 Residential Service | NEC Co-op Energy Residential Variable, non-demand meter | $7.50 per month plus a dated energy charge. For example, 9.83¢/kWh for September 2025 bills and 9.74¢/kWh for June 2026 bills. |
| Residential | §6.1.1.1.1 | Constellation 12 Month Residential Fixed Rate, EFL 310745 dated December 6, 2024 | 10.40¢/kWh, $0 monthly REP charge |
| Residential | §6.1.1.1.1 | Constellation 12 Month Residential Fixed Rate, EFL 381771 dated May 1, 2025 | 11.30¢/kWh, $0 monthly REP charge |
| Residential | §6.1.1.1.1 | Constellation 12 Month Residential Fixed Rate, EFL 4930520 dated April 1, 2026 | 8.85¢/kWh, $0 monthly REP charge |
| Small commercial | §6.1.1.1.2 Secondary Service ≤10 kW | NEC Co-op Energy Small Commercial Variable, single-phase | $7.50 per month plus the separately verified commercial EFL energy charge. September 2025 and June 2026 match the residential energy prices shown above. The commercial TDU schedule differs. |
| Residential | §6.1.1.1.1 | 4Change Energy One Rate 24, September 2024 and September 2025 editions | $4.95/month plus 9.8273¢/kWh or 10.7278¢/kWh, respectively. Requires positive usage, active paperless enrollment and the standard renewable selection. |
| Small commercial | §6.1.1.1.2 ≤10 kW or §6.1.1.1.3 >10 kW | Ambit TSC 12-month fixed, May 10, 2025 | 12.90¢/kWh plus $9.99 when monthly imports are below 1,250 kWh |
| Small commercial | Same two secondary delivery schedules | Ambit TSC 24-month fixed, May 10, 2025 | 11.50¢/kWh with the same $9.99 low-usage fee |

[Residential labels, terms and comparisons](Oncor_Residential_Plans.md) · [Commercial monthly rates, comparisons and conflicts](Oncor_Commercial_Plans.md) · [Dated delivery charges, rider changes and eligibility](Oncor_Delivery_Sources.md)

Select **Residential** or **Commercial** in the browser before opening the Oncor billing-plan menu. It shows six residential and five commercial selections. Each Ambit contract appears twice so the study uses the delivery schedule on the customer's Oncor account. At 1,250 kWh the usage fee is zero. Both commercial contracts require ordinary unaggregated small-business enrollment and prior 12-month demand below 50 kW.

For §6.1.1.1.3 the supported account is an established 240 V single-phase premises on standard 15-minute noncoincident peak (NCP) billing. Provide the previous 11 monthly peaks in chronological order, with a maximum above 10 kW and at most 20 kW, on an account without a power-factor adjustment, 4CP billing or a historical peak of 700 kW or more. The current cycle may fall below 10 kW. Distribution and transmission use its actual peak. Specified riders use the higher of that peak and 80% of the prior 11-month maximum. The study rolls the measured peak into history after every cycle. Accounts outside this band, primary voltage, transmission, lighting and seasonal agricultural service remain open. NEC's small-commercial scope still requires both historical and simulated peaks strictly below 10 kW. [Oncor retail delivery tariff](https://www.oncor.com/us/en/home/about-us/regulatory/tariffs-rate-schedules.html)

## Service and bill dates

The study covers standard single-phase, single-meter, full calendar reads with the Oncor delivery invoice rendered on the final service day. The customer provides the separate REP bill date. NEC's historic prices change on **bill issue dates**, including a price change on October 3, 2025. For a September service cycle, a bill issued October 2 uses 8.41¢/kWh for NEC supply. An October 3 bill uses 7.81¢/kWh with exactly the same September delivery charges. The study accepts documented REP bills up to 31 days after the meter read, within the source review horizon. Receipt of a different NEC membership benefit, credit, discount, addendum, first-bill charge or special delivery adjustment takes the account outside this scope.

| Plan | Verified service months with the REP bill also issued on the final service day |
| --- | --- |
| NEC residential | March–November 2025 and February–August 2026 |
| NEC small commercial | February, May and September–November 2025. January–July and September–October 2026 |
| Constellation 310745 | January–November 2025 for an illustrative contract commencing on the label date |
| Constellation 381771 | May–November 2025 and January–April 2026 for an illustrative contract commencing on the label date |
| Constellation 4930520 | April–October 2026 for an illustrative contract commencing on the label date |
| 4Change September 2024 edition | January–November 2025 and January–August 2026 |
| 4Change September 2025 edition | October–November 2025 and January–October 2026 |
| Ambit TSC 12-month, either meter class | June–November 2025 and January–April 2026 |
| Ambit TSC 24-month, either meter class | June–November 2025 and January–October 2026 |

For fixed contracts, the customer's signed version, first TDU meter read and documented term end determine eligibility. An account with a later verified activation can have a different eligible window. A new NEC label cannot fill a missing period. The delivery component covers 21 of the 22 complete service months from January 2025 through October 2026. December 2025 remains unavailable for every contract because the nuclear decommissioning factor changed on December 15 and the allocation across an actual invoice remains unresolved. November 2026 NEC bill issue dates through the 19th can apply to a completed October cycle when the matching label is reconciled. No complete November or December 2026 service is enabled.

The fixed-contract ranges in the table assume activation on the label date. The two Ambit 2026 ranges come from the remaining life of the May 2025 contracts. No newly issued 2026 Ambit price is assumed.

## Reproducing an invoice

Ambit and 4Change produce a recurring pretax subtotal for grid-only service. The supplier's treatment of the Texas PUC assessment remains unverified.

For NEC or Constellation, choose a verified recurring subtotal or a complete bill for a documented **unincorporated meter outside all local taxing districts**. The latter requires ordinary wholly residential use or fully taxable business use, a separate disclosure of the nuclear charge, and evidence of how the REP handles the PUC assessment. An NEC account in this scope has the assessment included in its running price. A Constellation account in this scope reimburses it separately at 0.1667%. State sales tax is 0% for solely residential use and 6.25% for taxable commercial use. Separately identified nuclear decommissioning charges are removed from the assessment and sales-tax bases. No municipal gross receipts reimbursement is due in this narrow unincorporated profile. The illustrative Dallas weather coordinates establish none of these account facts. For a meter in Dallas proper, the recurring subtotal excludes taxes and separately billed assessments. [Texas Comptroller guidance and worked bill, pp. 5–7](https://comptroller.texas.gov/taxes/publications/96-1309.pdf) · [Cities taxing residential electricity](https://comptroller.texas.gov/taxes/sales/utility/cities.php)

Each bill retains the supply label, Oncor source sheets, effective dates, per-kWh and monthly charges, and individual charge amounts. Solver objectives use unrounded rates. The reported study bill rounds each component to cents. NEC supports grid-only and approved zero-export solar, with optional storage charged only by PV. Oncor permission to operate and NEC ordinary-import terms for the exact installation are separate required inputs. Every fixed-price version supports grid-only service. Capital credits, buyback, battery exports, grid charging and discretionary fees are outside this implementation. [NEC renewable generation terms](https://neccoopenergy.com/for-members/buyback/) · [Oncor interconnection guidance](https://www.oncor.com/content/oncorwww/us/en/home/faqs/faqs-details.html)

## Targeted acceptance, November 19, 2026

The base checkout was main at `4abe016`. The tested local engine was `d146ca929847b2f83ef272f53e73f8c23f65f78b1f38aed5d80bae9654421f09`. The aggregate browser asset digest was `a646a8fb55b4c4f6907335fea438a5d0c26a0d4159ac0389b29493d4315f57a5`. The five Oncor test files plus affected regional reference-bill, historical driver/resume, carbon isolation and launcher tests passed **266 tests**. The changed JavaScript passed its syntax check. Checks cover local DST, gaps and duplicate intervals, exports, account eligibility, distinct bill dates, tax treatment, exact half-cent rounding, symbolic/numeric parity, queue execution, saved settings and CSV/ZIP contents.

| Frozen historical selection | Studies | Scenarios | Electrical interval checks |
| --- | ---: | ---: | ---: |
| September 2025 NEC residential, NEC commercial, Constellation 310745 and 381771; April 2026 Constellation 4930520 | 5 | 9 | 25,920 |
| June 2026 NEC residential, NEC commercial and Constellation 4930520 | 3 | 7 | 20,160 |
| Total | 8 | 16 | 46,080 |

Every interval in these selected cases passed representative OpenDSS replay. The scenarios include grid, non-export PV, and PV with PV-charged storage for NEC, and grid for Constellation. The two selections exercise the June 1 delivery redesign and earlier rates with each retail plan version. They use synthetic loads and site/year-matched ERA5 weather wherever PV is present. The frozen-candidate evidence is a sample of billing months. Tariff tests cover other rate boundaries. The December 2025 allocation gap prevents a full-year 2025 study. No other utility matrix, desktop GUI, release suite or stable-engine promotion was part of this targeted acceptance.

A separate Decimal calculation integrated the exported quarter-hour imports and checked zero export, all 212 individual charges, and rounded and unrounded totals for all 16 scenarios. All matched. Targeted pytest took about 17 seconds. The overlapping historical groups took about 81 and 50 seconds of elapsed driver time.

The browser restored an NEC small-commercial hypothetical account. It displayed Oncor, Texas, NEC and ERCOT separately, advanced through all seven steps, submitted the rerun and displayed its results. The September 2025 clear-sky example showed $269.93 grid-only and $220.44 with PV. The browser saved the rerun under a new name, opened the original fixture and reopened the named result. The rerun worker reported 3.34 seconds. This UI example used the explicitly assumed unincorporated tax profile.

Private evidence is under `.cache/oncor_tx/`. The identity is in `pin.json`, focused receipt in `frozen_focused/report.json`, and historical per-case manifests, bills, electrical intervals and dispatch tables in `matrix_sample/` and `matrix_summer/`. The independent implementation and results are `matrix_rebill.py` and `matrix_rebill.json`. The matched weather is under `weather/`. The browser receipt and image are `browser_receipt.json` and `browser-acceptance.jpg`.

## Fixed-plan expansion acceptance, November 19, 2026

The expansion was validated on development engine `bde0f94fca2251daa1714de4a87656c4759de027dedf697c95763a2ff4c05d44`. The browser asset digest was `a646a8fb55b4c4f6907335fea438a5d0c26a0d4159ac0389b29493d4315f57a5`. The earlier acceptance above belongs to its original engine. The frozen focused selection covered all six Oncor test files, regional counterfactuals, and historical driver and resume contracts. All **251 tests passed** in 18.76 seconds of pytest runtime. Checks included the twelve printed Ambit/4Change price examples, signed terms, metering and seasonal boundaries, demand-history rollover, the 1,250 kWh fee boundary, numeric/symbolic parity on fixed loads, DST, missing intervals, worker submission, saved settings and CSV/ZIP contents.

| Selected historical studies | Grid-only studies | Cycle bills | OpenDSS intervals |
| --- | ---: | ---: | ---: |
| October 2025, all six added selections | 6 | 6 | 17,856 |
| May–June 2026, Ambit 24-month demand meter across the June 1 delivery redesign | 1 | 2 | 5,856 |
| October 2026, Ambit 24-month on both meter classes and the September 2025 4Change edition | 3 | 3 | 8,928 |
| Total | 10 | 11 | 32,640 |

All selected intervals passed representative electrical replay. The separate Decimal audit used the exported quarter-hour imports and source-transcribed rates to reproduce all 140 individual charges and eleven subtotals, including the carried demand history across the June rate change. The historical groups ran concurrently for approximately 99, 17 and 48 seconds, respectively. All six additions are grid-only. December 2025 prevents an annual study. Desktop GUI, other utilities' matrices and the full release suite were outside this targeted acceptance.

The local browser displayed the four new Ambit options, restored the 24-month demand account with its eleven prior monthly peaks and submitted the study. The June 2026 example showed 8,640 kWh, zero exports and a $1,188.11 verified recurring subtotal. At a constant 12 kW with an 18 kW historical peak, the metered demand was 12 kW and the rider demand was 14.4 kW. Saving and reopening the result preserved the account and cycles. The browser-submitted worker took 2.30 seconds. The UI pass exercised commercial demand service. The other newly added selections were exercised through the historical worker.

Private receipts are under `.cache/oncor_tx/expansion/`: `pin.json`, `frozen_focused/report.json`, the three matrix folders `fall25/`, `transition26/` and `fall26/`, `rebill.py`, `rebill-receipt.json`, `browser-receipt.json` and `browser-acceptance.jpg`.
