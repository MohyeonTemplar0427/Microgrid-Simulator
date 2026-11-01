# Indicative PJM population coverage

Reviewed **October 31, 2026** against the regional registry and the separate
ComEd workflow, including The Illuminating Company candidate. There are **21
implemented utility/state-district workflows** with at least one executable
retail billing plan in a verified date window. Their distribution footprints
correspond to **about 50 million people, or about 75%** of PJM's reported
67 million people, using the household-based proxy below.

**This is territory coverage, not the share of people eligible for supported
plans or fully verified 2025–2026 bills.** Some utilities have narrower verified
date windows, incomplete historical components, account restrictions, or
separate validation evidence pins. No utility-territory/Census-block polygon
intersection was performed. PJM carbon-data coverage is a separate metric.
CEI's account/date scope and candidate-specific acceptance are documented in
[the utility guide](Illuminating_Company_Ohio.md) and
[implementation validation](Illuminating_Company_Ohio_Implementation_Validation.md).

## Progress from this addition

| Scope | Implemented utility/state-district workflows | Estimated footprint people | Indicative PJM population share |
| --- | ---: | ---: | ---: |
| Immediately before CEI | 20 | 48.57 million | 72.5% |
| Including The Illuminating Company (CEI) | 21 | 50.17 million | 74.9% |
| Earlier October 25 seven-workflow baseline | 7 | 28.30 million | 42.2% |

CEI adds **676,098 residential distribution accounts**, approximately **1.60
million people** using Ohio's 2.37 persons per household, or **2.39 percentage
points** in this proxy. The earlier roughly 42% headline predates the subsequent
utility additions; it is preserved in its original input/output evidence,
rather than treated as the current implementation total.

The 21 count separates Dominion Virginia/North Carolina and the four FirstEnergy
Pennsylvania rate districts. It is not a count of corporate parents, tariff
schedules, all PJM utilities, fully supported customer classes or annual
acceptance passes. ComEd is a separate executable workflow outside the regional
utility dictionary. No MISO or California utility adds to this PJM numerator.

## Definition and method

1. Reuse the same final **2024 EIA-861** `Sales_Ult_Cust_2024.xlsx`, `States`
   extract. Select balancing authority `PJM` and service types `Bundled` and
   `Delivery`; exclude `Energy` supplier rows to avoid counting delivery
   accounts twice. Only residential accounts enter the population proxy.
   [EIA data and method](https://www.eia.gov/electricity/data/eia861/).
2. Select only the implemented utility/state combinations below. Pepco,
   Delmarva and Potomac Edison contribute **Maryland only**; their DC, Delaware
   and West Virginia rows remain outside the numerator. Dominion's two state
   rows are selected once each under one EIA utility ID.
3. Multiply residential distribution accounts by the state's **2020–2024
   Census QuickFacts persons per household**: IL 2.46, OH 2.37, PA 2.39,
   NJ 2.62, VA 2.52, NC 2.44, MD **2.57**. Prior factors are retained from the
   earlier source review; Maryland was newly verified on October 31.
   [Maryland QuickFacts](https://www.census.gov/quickfacts/fact/table/MD/HSD410224).
4. Divide by PJM's rounded public **67 million** population headline,
   reverified October 31. [About PJM](https://www.pjm.com/m/About-PJM).

```text
Estimated footprint people = sum(residential distribution accounts × state household size)
Indicative coverage share = estimated footprint people / 67,000,000
```

| Implemented utility/state footprint | Residential distribution accounts | Estimated people, millions |
| --- | ---: | ---: |
| ComEd · IL | 3,727,675 | 9.17 |
| Ohio Edison · OH | 957,780 | 2.27 |
| PECO · PA | 1,535,818 | 3.67 |
| PSE&G · NJ | 2,056,231 | 5.39 |
| Dominion Energy Virginia and North Carolina · VA | 2,383,548 | 6.01 |
| Dominion Energy Virginia and North Carolina · NC | 108,656 | 0.27 |
| Atlantic City Electric · NJ | 506,488 | 1.33 |
| Baltimore Gas & Electric · MD | 1,214,100 | 3.12 |
| Delmarva Power Maryland · MD | 186,368 | 0.48 |
| Duquesne Light · PA | 550,405 | 1.32 |
| JCP&L · NJ | 1,038,258 | 2.72 |
| AEP Ohio (Ohio Power) · OH | 1,339,232 | 3.17 |
| PPL Electric Utilities · PA | 1,295,883 | 3.10 |
| Potomac Edison Maryland · MD | 256,568 | 0.66 |
| Pepco Maryland · MD | 553,607 | 1.42 |
| Rockland Electric New Jersey · NJ | 65,889 | 0.17 |
| FirstEnergy Pennsylvania: all four PA districts · PA | 1,802,612 | 4.31 |
| The Illuminating Company (CEI) · OH | 676,098 | 1.60 |
| **Total** | **20,255,216** | **50.17** |

The mathematical result is 74.88%; **about 75%** is the appropriate headline.
Arithmetic precision does not measure the uncertainty in the household proxy.
The selected accounts are **73.0%** of EIA's **27,756,201 PJM residential
distribution accounts**, a separate cross-check with a different denominator.

## FirstEnergy Pennsylvania merger handling

The 2024 EIA utility ID **66101** combines Met-Ed, Penelec, Penn Power and West
Penn. All four Pennsylvania districts now have executable retail adapters, so
this update includes their **1,802,612 PA residential accounts once**. The
company's small New York rows remain excluded. It does not add four copies of
the merged company or add the earlier inferred West Penn district on top.
[Official consolidation announcement](https://www.firstenergycorp.com/newsroom/news_articles/firstenergy-pennsylvania-subsidiaries-receive-approval-to-consolidate.html).

The October 25 baseline included only West Penn, estimating that district from
a PUC switched-account count divided by a rounded percentage. That inference
was appropriate to the narrower old selection; its rounding-only range no
longer enters the current total. The original
[inputs](utility_sources/pjm_population/inputs_2026-10-25.json) and
[estimate](utility_sources/pjm_population/estimate_2026-10-25.json) are preserved
byte for byte and remain reproducible. The reporting tool requires all four
PA district keys before accepting merged-company counts, rejects NY scope and
rejects adding the old district estimate to the merged total.

## Limits and remaining gaps

An account is an imperfect proxy for one occupied household. Master metering,
seasonal homes, vacancies, group quarters, meter timing and differences between
statewide and utility-territory household size can distort the estimate. No
geographic uncertainty interval or statistical confidence interval is claimed.
An illustrative ±10% occupancy-factor sensitivity gives approximately **67–82%**;
this is a scenario, not a validated uncertainty bound.

The input vintages remain final 2024 account data, 2020–2024 household factors
and a current rounded PJM headline. The denominator retains identified EIA
state/BA adjustments, including negative ones; these are not allocated to a
utility by assumption. Nine nonresidential-only rows with a residential dot
retain the earlier zero-account verification and original source notation.
The source extract and its SHA-256 have not changed.

The result does **not** imply every residential/small-commercial tariff, all
2025–2026 dates, export/NEM settlement, actual customer eligibility, annual
bill optimum, site-specific electrical networks or local carbon intensity is
verified. Historical validation receipts retain their original engine/frontend
pins; adding a utility does not renew older acceptance evidence.

Remaining PJM footprints include Appalachian Power, AES Ohio, Duke Energy
Ohio/Kentucky, Toledo Edison, Mon Power, Pepco DC, Delmarva Delaware, Potomac
Edison West Virginia and many cooperatives/municipals. Their full footprints
must not be inferred from an already implemented affiliate or state.

## Reproduction and evidence

The public input ledger and output are
[inputs.json](utility_sources/pjm_population/inputs.json) and
[estimate.json](utility_sources/pjm_population/estimate.json). The earlier
source archive/workbook hashes and extract are retained. The October 31
source [refresh receipt](utility_sources/pjm_population/refresh_2026-10-31.json)
records Maryland/PJM checks separately. No credentials
or private customer data are read.

```sh
/usr/local/bin/python3 tools/estimate_pjm_population_coverage.py
```

This command is offline and makes no API or simulation calls. It verifies
source/baseline hashes, distribution-service rows, duplicate selections,
adjustments, merged-district scope and current-addition attribution. Ten focused
reporting tests passed under the validation launcher; the original October 25
JSON was independently reproduced exactly. These checks validate arithmetic and
evidence handling, not the population-proxy assumptions or any tariff billing.
Private check receipt: `.cache/illuminating_oh/population_focused_2/report.json`.
