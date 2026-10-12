# San Diego residential import billing

Implemented on main, October 11, 2026. This is a bounded billing-cycle study,
not complete regional or historical coverage. The independent browser clone
is not modified by this change.

## Supported accounts and dates

| Delivery plan | Generation | Executable service dates |
| --- | --- | --- |
| SDG&E TOU-DR1 | SDG&E bundled, SDCP, CEA | June 1–October 11, 2026 |
| SDG&E TOU-DR2 | SDG&E bundled, SDCP, CEA | June 1–October 11, 2026 |
| SDG&E EV-TOU-5 | SDG&E bundled, SDCP, CEA | June 1–October 11, 2026 |

Ordinary individually metered residential secondary accounts only: no CARE,
FERA, medical baseline, deed-restricted discount, master meter, direct access,
CPP/Reduce Your Use, CEA Peak Smart Savers, or other special riders. EV-TOU-5
requires confirmed eligible EV enrollment; natural-gas fueling and solar NBT
qualification paths are not implemented. The utility must confirm storage is
allowed on the ordinary import plan without standby or event-program riders.

One confirmed cycle of at most 40 days. Dates are inclusive local service days,
using complete timestamped 15-minute intervals with UTC offsets. Short study
periods are allowed only with explicit cycle assumptions and a baseline
quantity covering those exact dates. No demand charge applies to these plans;
the reported maximum kW is information, not a billed charge.

Confirmed **zero local utility-user tax** is required. SDG&E bundled accounts
inside City of San Diego limits include the city's franchise differential.
**CCA accounts inside those city limits reject**: the city's differential and
CCA municipal-surcharge ordering are not yet reconciled. Do not replace these
accounts with bundled generation except as an explicitly hypothetical study.

## Prices and cost expressions

SDG&E prices have two distinct dated versions, June 1–July 31 and August
1–October 11, 2026. October 11 closes the research snapshot; it is not a
published tariff expiration date. Each interval uses its local service date.
Dates outside those windows fail rather than extending current prices.

The bill and battery optimizer share `src/billing/san_diego.py` expressions:

- UDC delivery, including its published component adjustments;
- wildfire/DWR charge, separately from UDC;
- bundled EECC **or** the selected CCA generation charge, never both;
- daily ordinary Base Services Charge of **$0.79343**, counted by local service
  days, rather than days/30 or a guessed monthly fee;
- TOU-DR1/DR2 baseline adjustment, crediting imports up to **130% of the
  account-confirmed cycle baseline allowance**; EV-TOU-5 has no baseline credit;
- CCA PCIA using the **confirmed 2009–2026 account vintage**, with the applicable
  dated SDG&E price; CEA MCAM **$0.00006/kWh** is separate;
- franchise fee equivalent: 1.1% of wildfire/DWR charges, plus 1.1% of imputed
  SDG&E generation for CCA service. The standard SDG&E franchise fee is already
  embedded in UDC/EECC. CCA generation premiums do not change this imputed base;
- for supported bundled City of San Diego accounts, 5.78% of the energy,
  generation, wildfire, fixed and baseline-adjustment subtotal;
- E-PUC regulatory fee **$0.001/kWh**, and state electrical-energy surcharge
  **$0.0003/kWh**, separately, each charged once;
- optional bill-confirmed climate credit applied once after fees. No credit
  amount or posting date is inferred, and no credit is added by default.

Prices and totals remain unrounded study values. Printed utility bills round
line items and may include additional account adjustments. This release is
validated against filed tables and independent arithmetic, not calibrated
against a new customer's real San Diego bill.

### TOU calendar and baseline allocation

Summer is June 1–October 31; winter is November 1–May 31. All plans have
on-peak hours 4–9 p.m., including weekends and holidays. TOU-DR2 has off-peak
at all other times. TOU-DR1/EV-TOU-5 use super off-peak midnight–6 a.m. and
10 a.m.–2 p.m. on weekdays, and midnight–2 p.m. on weekends/tariff holidays.
Use actual local clock time. Eight tariff holidays are New Year's Day,
Presidents' Day, Memorial Day, Independence Day, Labor Day, Veterans Day,
Thanksgiving and Christmas; Sunday holidays are observed Monday. Saturday
holidays do not make Friday a holiday.

Confirm this ordinary TOU calendar on the account for the selected cycle.
Older calendar definitions and optional event schedules are excluded. Winter
rate columns are retained as source data; November 2026 bills remain outside
the executable snapshot coverage.

For TOU-DR1/DR2, users supply the baseline allowance for the exact cycle dates
from the bill or utility, or identify an explicit hypothetical assumption.
No baseline climate zone or basic/all-electric allocation is inferred from a
city or service territory. Across a dated rate change, the allowance is split
by service days, and each subperiod receives its own capped credit. **That
allocation is an acknowledged study approximation**, not a verified SDG&E
meter-read reconciliation rule. Interval import energy uses actual records.

### SDCP and CEA generation

SDCP generation rates are effective May 1, 2026, and are selected from the
separately published **2021 or 2022 rate cohort**. The cohort and PCIA vintage
are separate confirmed inputs, not automatically equated. Supported options:
PowerOn, PowerBase, and Power100 (PowerOn plus **$0.01/kWh**).

CEA generation rates are effective June 1, 2026. Supported options: Clean
Impact, Clean Impact Plus (**$0.001/kWh** premium), and Green Impact
(**$0.0075/kWh** premium). Only Clean Impact receives the published residential
rate-relief credit of **$0.03871/kWh**. The relief program is announced through
December 31, 2026; that does not extend this model's October 11 coverage.

CCA generation and delivery/exit fees remain itemized. Rates are not a claim
that any one provider or plan is cheaper for every load shape, and comparative
savings do not prove enrollment eligibility.

## Shared workflow and dispatch

The existing schema-6 account-qualified study workflow, durable queue,
independent pinned-source worker, saved result tables and CSV exports are
reused. No new simulation or browser layout is introduced. Desktop GUI
launches the same local web application in its native WebKit window, so both
interfaces receive the same controls and calculations.

CEC distribution identity **AgencyNum 80402** identifies SDG&E. CCA identities
**OBJECTID 25 / San Diego Community Power (SDCP)** and **OBJECTID 10 / Clean
Energy Alliance (CEA)** are checked by both identifier and name. Boundary and
overlapping matches remain ambiguous; map results do not establish actual
provider enrollment, tax jurisdiction, baseline quantity or vintage. Users
confirm delivery from their account, then choose generation independently.
The delivery override preserves original map evidence.

Actual-service mode prices the confirmed generation provider. Explicit
hypothetical bundled mode retains the original provider in the saved request
but prices SDG&E generation and removes CCA PCIA, premiums and MCAM.

Dispatch minimizes the same modeled utility bill by default, with optional
degradation cost, battery power/SOC/efficiency limits and equal starting/ending
energy. Arbitrage sees TOU generation, delivery, baseline credits, PCIA and
applicable variable fees. Credits already posted on a bill are fixed offsets
and do not create an artificial dispatch incentive. Lowest throughput is a
tie-break among bill-optimal schedules. The authoritative bill must reconcile
with the objective before a result is saved.

PV is supported only with explicitly approved **non-export interconnection
and standby exemption**, through the existing clear-sky PV model. Surplus is
curtailed. SDG&E/CCA NEM, NBT/Solar Billing Plan and export settlement, commercial
plans, assistance discounts, other tax jurisdictions and full-year studies
are future work. No PG&E or SCE solar rules are borrowed.
The solar-program catalog identifies SDG&E SBP/legacy NEM, SDCP SBP and CEA
NEM separately, all with `research_only` status. These entries enable no export
billing or optimizer path.

## Sources and reproduction

Official sources retrieved October 11, 2026:

- [SDG&E total rate tables and historical versions](https://www.sdge.com/total-electric-rates):
  TOU-DR1, TOU-DR2 and EV-TOU-5, June 1 and August 1, 2026. PDF hashes, URLs,
  retrieval dates and text extraction names are in
  `utility_sources/san_diego/source_manifest.json`.
- [SDG&E filed tariff book](https://tariffsprd.sdge.com): TOU-DR1, TOU-DR2,
  EV-TOU-5, CCA-CRS (including January 1, 2026 MCAM), E-PUC (AL 4763-E,
  effective January 1, 2026), Rule 1, Rule 9, Rule 27 and preliminary statement.
- [SDG&E franchise fees](https://www.sdge.com/rates-and-regulations/miscellaneous-tariff-related-information/electric-franchise-fees),
  [electricity supplied by others](https://www.sdge.com/rates-and-regulations/miscellaneous-tariff-related-information/calculating-franchise-fees-electric-energy-supplied-others),
  and [official CCA sample bill](https://www.sdge.com/sites/default/files/documents/FINAL_S1870134_UnderstandCCABill.pdf).
- [SDCP residential rates](https://sdcommunitypower.org/residential-rates/),
  [2021 cohort](https://sdcommunitypower.org/wp-content/uploads/2026/04/Res_2021V_042026.pdf)
  and [2022 cohort](https://sdcommunitypower.org/wp-content/uploads/2026/04/Res_2022V_042026.pdf).
- [CEA adopted June 1, 2026 rates](https://thecleanenergyalliance.org/wp-content/uploads/2026/06/CEA-Adopted-Residential-Rate-Schedule-Effective-2026_06_01-1.pdf)
  and [rate-relief scope](https://thecleanenergyalliance.org/clean-energy-alliance-approves-rate-relief-measures-to-protect-customers-from-rising-costs/).
- [CDTFA 2026 electrical-energy surcharge notice](https://cdtfa.ca.gov/formspubs/l1020.pdf).

The rolling ten-year research target remains in force. The source archive
contains the available plan tables within 2016–2026 and CCA documents since
those providers began service. **Archive retrieval is not historical billing
coverage**: missing tariff calendars, fixed-charge transitions, CCA options,
PCIA rules and fee bases must be reconciled before enabling earlier dates.
Failed legacy tariff URLs remain recorded as retrieval failures, not sources
of rates. There is no assumption that a new plan existed ten years earlier.

Rebuild the runtime Python literals offline:

```sh
/usr/local/bin/python3 tools/build_san_diego_rates.py
```

The builder reads six official SDG&E tables, both current SDCP cohort tables
and CEA's adopted table. It checks column counts, UDC+WF+EECC reconciliation,
PCIA coverage, expected TOU rows and transcribed CEA season columns. Python
literals travel with pinned engine snapshots; no runtime network fetch or
external mutable rate file is required. Research PDF binaries and rendered
inspection images remain ignored under `.cache/san_diego_research/`.

Validation covers independent monthly and one-day bills, zero/low consumption,
CCA premiums and relief, PCIA/cohort distinction, the July/August price boundary,
calendar/holiday/DST helpers, explicit coverage rejection, account eligibility,
export rejection, and battery objective/bill reconciliation across all nine
plan/provider pairings. Production JavaScript request-builder tests submit
each provider through HTTP to the pinned worker and inspect saved results.

### Validated cases, October 11, 2026

Full repository regression: **1,534 passed, 1 skipped**, using
`/usr/local/bin/python3 -m pytest -q`. JavaScript syntax checks for `app.js`
and `socal.js` and `git diff --check` passed. The existing skip remains a skip,
not an additional validated scenario. No commit, push or deployment was made.

The nine plan/provider dispatch cases use July 31–August 1, 2026, 15-minute
intervals, 0.5 kW base load and 2 kW from 4–9 p.m., no PV, an 8 kWh battery
starting/ending at 4 kWh, 10–90% SOC bounds, 2 kW charge/discharge limits and
95% charge/discharge efficiencies. The cycle baseline is 18 kWh where
applicable. CCA PCIA is 2021; SDCP uses its 2021 PowerOn cohort and CEA uses
Clean Impact. Each final bill reconciles with its dispatch objective.

The three production-form/API/worker cases use August 6, 2026, 1 kW base load
and a 2 kW 4–9 p.m. peak, the same battery, and no PV. They exercise bundled
TOU-DR1, SDCP TOU-DR2 with 2022 cohort/Power100, and CEA EV-TOU-5 with Green
Impact. The PCIA remains 2021, demonstrating that cohort and vintage are
separate inputs. Confirmations and fee jurisdiction are synthetic test data.

A live browser submission also completed for a synthetic August 1–31, 2026
SDG&E TOU-DR1 / SDCP PowerOn account, with 2021 PCIA and generation cohort,
outside City of San Diego limits, zero local UUT and no climate credit. It
uses 0.4 kW base load and 2 kW during 4–9 p.m., totaling **545.6 kWh**, a
**279 kWh** explicitly assumed cycle baseline, and no PV or battery. The
displayed utility bill is **$288.6672** before display rounding. This verifies
the form, territory/account controls, saved worker output and result table;
it is not a comparison to a real customer bill.
