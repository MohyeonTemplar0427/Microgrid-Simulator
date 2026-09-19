# Southern California residential validation — September 19, 2026

## Outcome

**Partial support, not an end-to-end pass for both utilities.** Fifteen LADWP studies completed through the existing port-8876 HTTP API, durable queue and pinned worker. Eighteen SCE submissions were correctly rejected with HTTP 400 because no 2025 SCE rates are implemented (verified coverage starts June 25, 2026). No 2026 prices were applied to 2025 consumption.

Engine: `00a262a1b8c2cc6151ba0e0b7d5b9506e8cdae6d1412ff0a141834ed48f0a2f6`. No engine or application source changes made for this validation.

## Data and assumptions

- [EIA-861M 2025 monthly workbook](https://www.eia.gov/electricity/data/eia861m/archive/xls/sales_ult_cust_2025.xlsx): preliminary residential sales MWh × 1,000 / residential customer count; LADWP utility 11208, SCE 17609. This is a utility-wide monthly sales-per-customer statistic, not city-specific household measurements. SCE's monthly bundled-service sample does not represent all CCA customers.
- [SCE 2025 DOM-S/M dynamic profile](https://www.sce.com/regulatory/regulatory-information/load-profiles/dynamic-load-profiles): hourly class-average demand, scaled to each utility's EIA monthly value. For LADWP, this is explicitly a proxy shape, not a measured LADWP profile.
- [SCE file format](https://www.sce.com/sites/default/files/inline-files/Format_Data_Files.txt): hour-ending fixed PST. Converted to hour-start instants, then America/Los_Angeles. Each hourly average is held over four quarter-hours; no measured 15-minute variability is claimed. July contains 2,976 intervals; November contains 2,884, including the fall clock change.
- Same utility-wide consumption and shape used at all three locations for each utility. Differences between local households, cooling demand and dwelling types are not modeled. These cases test geographic routing and account assumptions, not differences in city consumption.
- Hypothetical bundled, individually metered residential service; no solar, no special riders, no climate credit or other one-off adjustment. Local tax assumed zero, so results are not complete actual municipal-tax-inclusive bills. Model includes its $0.0003/kWh state surcharge.
- LADWP temperature zone assumed 1 for West LA/San Pedro, 2 for Van Nuys. PAC tier 2 ($7.90/month) and prior monthly average 500 kWh explicitly assumed, not derived from the study month or asserted as actual account history. Monthly billing factor 1. These are individual calendar-month estimates, not a replay of a customer's bimonthly meter-read cycle.
- SCE baseline regions 6/8/15 and basic allowance are hypothetical assumptions for Santa Monica/Irvine/Palm Desert. No bill is produced, and these tests do not establish automatic baseline geography.

| Utility | July 2025 kWh/customer | November 2025 kWh/customer |
|---|---:|---:|
| LADWP | 474.454149 | 456.721538 |
| SCE bundled | 612.692810 | 468.450102 |

## Completed LADWP bills

| Location / assumed zone | July R-1A | July R-1B | November R-1A | November R-1B |
|---|---:|---:|---:|---:|
| West Los Angeles / 1 | $130.65 | $137.28 | $126.66 | $130.01 |
| Van Nuys / 2 | $123.36 | $137.28 | $120.41 | $130.01 |
| San Pedro / 1 | $130.65 | $137.28 | $126.66 | $130.01 |

All twelve grid-only bills match separate calculations using [LADWP's published 2025 total energy rates](https://www.ladwp.com/account/customer-service/electric-rates/residential-rates), fixed charges and model surcharge, within $0.005. Maximum unrounded difference was $2.85e-14. Independent calculations do not call backend rate or TOU-period functions. This validates these tariff calculations under the stated assumptions, not accuracy against actual customer bills.

Three additional July R-1B battery-only studies used 10 kWh nameplate, 20–80% SOC, initial/final energy 5 kWh, 3 kW charge/discharge, 95% efficiency each way and $0.01/kWh throughput wear. Each produced a $132.8783 utility bill plus $1.5631 wear = **$134.4415 operating cost**, saving $2.8420 from $137.2834. Their identical results follow from the same load and R-1B rates. Export is zero, SOC bounds and terminal energy pass, maximum power-balance residual is below 1e-5 kW, and optimized-objective/bill reconciliation error is zero. Capital cost is excluded.

The saved West LA battery result was opened and checked in the browser: displayed totals, scenario labels, degradation and savings agree with downloaded CSVs.

## Geographic checks and SCE gap

Live CEC resolution returned LADWP among candidates for all three LA points, and SCE for Santa Monica, Irvine and Palm Desert. Five points were ambiguous due to the Metropolitan Water District overlap; Palm Desert returned an approximate SCE-only match. Ambiguity was preserved and no actual-account verification was claimed.

SCE D, TOU-D-4-9 and TOU-D-5-8 were each submitted for July and November at all three SCE locations: **18 historical-coverage rejections**, all before queue creation. This is correct fail-closed behavior but means the requested SCE 2025 bill simulations cannot currently complete. Historical delivery, generation, fixed/minimum charges, baseline credits and applicable adjustments must be verified and versioned before rerunning. Merely extending the current effective date is not a valid fix.

## Reproduction and artifacts

- [Case summary](socal_2025_residential_cases.csv) contains all 33 outcomes and saved study IDs.
- Local `.cache/socal_2025_validation/` contains downloaded sources, SHA-256 manifest, geographic evidence, reproducible `run_cases.py`, saved requests, API results and battery dispatch CSVs. These generated files are kept out of tracked source.
- Saved studies remain in the existing preview's `/tmp/microgrid-municipal-browser-review` store; that temporary deployment directory is not a permanent archive.
- [West LA July battery result](http://127.0.0.1:8876/?review=2025-validation#4535b844d0ae42a78ce93b51ec96a445).

Focused existing tests: 25 passed under the sandbox; the HTTP integration test was blocked by socket-binding permissions and rerun separately with localhost access. Final rerun outcome recorded below.

HTTP integration rerun: **1 passed**, giving **26/26 focused tests passed** across the two executions. No full-suite rerun was needed for this report-only task. Saved dispatches additionally checked for zero exports and no simultaneous charging/discharging. `git diff --check` passed. No commit or push.
