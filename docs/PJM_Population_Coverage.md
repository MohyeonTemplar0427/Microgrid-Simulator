# Indicative PJM population coverage

Reviewed October 25, 2026 against the current utility registry and the separate
ComEd workflow. **The implemented utility footprints correspond to roughly
28 million people, or about 42% of PJM's publicly reported 67 million people.**
This is a household-based planning estimate, not an exact count of residents
inside service-area polygons and not a count of people eligible for every
implemented billing plan. Alliant Iowa belongs to MISO and adds **zero** to
this PJM numerator.

## Definition and method

The question answered is: approximately how many residents are associated with
the electric distribution utilities for which the simulator has at least one
executable retail billing workflow?

1. Read the final **2024 EIA-861** `Sales_Ult_Cust_2024.xlsx`, `States` sheet.
   Keep balancing-authority code `PJM` and service types `Bundled` and
   `Delivery`. Exclude `Energy` supplier rows so a delivery account is not
   counted again when its customer chooses another retail supplier. Use only
   residential accounts for the population proxy; commercial/industrial
   accounts are not people. EIA describes the file as customer counts by
   state, sector, service type and balancing authority. [EIA data and method](https://www.eia.gov/electricity/data/eia861/).
2. Select ComEd, Dominion Virginia/North Carolina, PSE&G, Ohio Edison, PECO
   and only the West Penn rate district. The same Virginia Electric & Power
   Company EIA ID is used for Dominion's two state rows; it is not counted
   twice as two whole companies. PSEG Long Island, gas customers, other
   FirstEnergy Pennsylvania districts and MISO utilities are excluded.
3. Estimate people as residential distribution accounts multiplied by the
   state's **2020–2024 Census QuickFacts persons per household**: Illinois
   2.46; Ohio 2.37; Pennsylvania 2.39; New Jersey 2.62; Virginia 2.52; North
   Carolina 2.44. The relevant sources are linked in the checked-in
   [input ledger](utility_sources/pjm_population/inputs.json).
4. Divide that estimate by PJM's rounded public population headline of
   **67 million**, verified on its current [About PJM page](https://www.pjm.com/m/About-PJM).

The formula is:

```text
Estimated footprint population = sum(residential distribution accounts × state household size)
Indicative coverage share = estimated footprint population / 67,000,000
```

| Implemented electric utility / district | Residential accounts used | Estimated people, millions |
| --- | ---: | ---: |
| ComEd, Illinois | 3,727,675 | 9.17 |
| Dominion, Virginia | 2,383,548 | 6.01 |
| Dominion, North Carolina | 108,656 | 0.27 |
| PSE&G, New Jersey | 2,056,231 | 5.39 |
| PECO, Pennsylvania | 1,535,818 | 3.67 |
| Ohio Edison, Ohio | 957,780 | 2.27 |
| West Penn district, Pennsylvania | approximately 638,517 | 1.53 |
| **Total** | **approximately 11.41 million** | **28.30** |

The numerical calculation is 42.23%, but that precision describes arithmetic,
not measurement accuracy. The appropriate headline is **about 42%**, not an
exact percentage of all residents or all billable accounts.

## West Penn merger and district estimate

EIA's 2024 FirstEnergy Pennsylvania ID `66101` combines Met-Ed, Penelec,
Penn Power and West Penn. Counting that entire company would overstate the
implemented footprint. FirstEnergy confirms the consolidation took effect
January 1, 2024 while the local brands/rate districts remained separate.
[Official consolidation announcement](https://www.firstenergycorp.com/newsroom/news_articles/firstenergy-pennsylvania-subsidiaries-receive-approval-to-consolidate.html).

For a same-year district estimate, the Pennsylvania PUC's September 2024
switching table reports West Penn's residential switched customers as
**113,656**, or **17.8% of its residential customers**. Dividing gives about
638,517 total district residential accounts. The adjacent 17.6% value is load
share and is not used. Assuming the customer percentage was rounded to the
nearest 0.1 percentage point, its denominator is about 636,728–640,315 accounts.
This rounding interval does not measure broader population uncertainty.
[PUC district table](https://www.papowerswitch.com/media/dsbp5oci/paps_numbers093024.pdf).

## Cross-checks, uncertainty and interpretation

The selected utilities/district represent about **41.1% of PJM's 27.76 million
residential distribution accounts** in the EIA snapshot, an additional
account-share cross-check on the household-weighted estimate. The denominator
retains EIA's identified state/BA adjustment rows, including negative ones;
those adjustments are not arbitrarily assigned to particular utilities.
Nine nonresidential-only rows with a residential dot have zero residential
accounts verified against the other-sector/total identities, with source
notation preserved. The small New York rows reported with BA `PJM` stay in
the EIA denominator; they are not counted as West Penn.

The population proxy assumes an account corresponds to one occupied household
and statewide household size represents each subterritory. Master-metered
housing, seasonal/second-home meters, vacancies, group quarters, meter timing,
and local differences in household size can break that relationship. No
utility-territory/PJM/Census-block polygon intersection was performed. Input
vintages also differ: 2024 account data, 2020–2024 household factors and a
current rounded PJM headline.

An illustrative **±10% change in the occupancy multiplier** moves the result
to about **38–46%**. This is a sensitivity scenario, not a statistical
confidence interval or a demonstrated uncertainty bound. The estimate should
not be presented as evidence that exactly 42% of PJM residents can receive a
fully verified simulated bill: supported schedules, supplier arrangements,
solar programs, account eligibility and historical rate dates are narrower.

Large remaining PJM distribution footprints include Ohio Power/AEP Ohio,
PPL Electric Utilities, Baltimore Gas & Electric, Jersey Central Power & Light,
other FirstEnergy Pennsylvania districts, Pepco and Appalachian Power. Adding
Alliant Iowa or another MISO utility does not close those PJM gaps.

## Reproduction and evidence

The public source extract, household factors, utility IDs, source URLs and
SHA-256 checks are under
[`docs/utility_sources/pjm_population/`](utility_sources/pjm_population/inputs.json).
The original EIA ZIP/workbook and PUC PDF are retained in ignored
`.cache/pjm_population`. No credentials or private customer data are used.
The Census API required a key and direct CSV requests returned 403, so those
responses were not used as data; values were read from official Census pages.
The 2025 early release was not substituted for final 2024 data.

```sh
/usr/local/bin/python3 tools/estimate_pjm_population_coverage.py
```

The command is offline. It validates the source-extract hash, distribution
service types, utility/state uniqueness, adjustment IDs and selected utility
presence, rejects the merged FirstEnergy company in the numerator, and
recalculates the estimate and sensitivity. Machine-readable output is retained
in [estimate.json](utility_sources/pjm_population/estimate.json).

Verification of this reporting tool: an offline rerun reproduced the checked-in
JSON byte-for-byte. Four corruption/overcount checks rejected a repeated
utility/state, the merged FirstEnergy company, an energy-only supplier row and
a changed source-extract hash. The private check receipt is
`.cache/pjm_population/offline_guard_checks.json`; these checks validate report
arithmetic and evidence handling, not the population-proxy assumptions.
