# Kentucky Power Kentucky ordinary RS and small secondary GS

The regional adapter implements bundled ordinary Residential Service RS and
a bounded, non-demand-metered secondary General Service GS scope. Kentucky
Power is both the distribution utility and bundled supplier. Kentucky
jurisdiction, PJM/AEP metadata, wholesale inputs and retail charges remain
separate. No wholesale price is added to the filed bundled bill.

## Executable dates and billing clocks

Supported **service cycles are December 2025 through August 2026**. All must
be complete calendar cycles with consecutive 15-minute Eastern-time records,
full monthly charges and a separately confirmed Company billing-month
assignment. The initial study convention issues the bill on the following
day, in the following named billing month: December 1–31 service is billed
January 1 and uses January monthly factors. This is an explicit hypothetical
calendar convention, not a representation of Kentucky Power's normal reading
calendar. Actual accounts require evidence that these cycle facts apply.

The service-date base, annual riders and monthly billing factors retain their
different clocks. The filed temporary March 2026 FAC applies to bills rendered
February 24–March 24. A February calendar study with a March 1 bill uses that
factor; a full March service cycle cannot be assigned March rates with a
March 31 bill. `hypothetical_cycle_fields(service_start)` supplies consistent
documented-cycle inputs for the browser and historical driver.

January–November 2025 component intersections are not fully reconciled.
September 2026 crosses the September 29 service-date DR change and requires
an unverified allocation. October–December 2026 lack a fully reconciled later
annual-rider/monthly-factor stack. Those periods reject. There is no annual
2025 or annual 2026 acceptance claim.

The [source ledger](utility_sources/kentucky_power_ky/sources.json) records
filed No. 13/14 sheets, Commission orders, monthly factors, original hashes,
calculator inconsistencies and remaining gaps. Raw material is retained under
`.cache/kentucky_power_ky/sources/`.

## Account scope and billing

Initial service is one ordinary 120/240 V single-phase secondary meter in
**unincorporated Pike County**, with 3% school tax and no city franchise fee or
additional local charge. RS requires the Company's accepted primary-domicile
sales-tax exemption. GS pays 6% state sales tax on the taxable subtotal,
including the school levy. Location, tax status and assignment need independent
evidence; they are not inferred from coordinates or modeled imports.

RS retains the exact Company code 015, 017 or 022. Before March 2026 the
customer charge is $20 and energy is $0.12785/kWh. The separately itemized
temporary charge is $0.00494/kWh during the supported period. From March 1,
2026, energy uses $0.15385/kWh for the first 600 kWh and $0.11534 thereafter;
the service charge is $24 through 2,000 kWh and $38 above it. Initial native
load and imports are capped at **2,000 kWh and 25 kW**, excluding the higher
discontinuous service-charge tier. This is a study restriction, not a tariff
eligibility threshold. Optional water-heating, demand, TOD, bimonthly and
assistance-credit provisions are outside scope.

GS retains one of codes 211/212/215/216/218, with Company-confirmed non-demand
metering and no metering-voltage adjustment. The full tariff generally permits
average maximum demand up to 100 kW and charges billing demand over 10 kW.
Demand metering is mandatory at 4,450 kWh per month and can be installed below
that level. The initial study instead requires independently reviewed actual
billing demand and contract capacity no more than 10 kW, including contract
and past-eleven-month effects. Native load and imports are capped at **9.49 kW
and 4,449 kWh**. The Company classification cannot be inferred from PV savings.
Within that scope, the customer charge/first-block energy are $28/$0.13060
before March 2026 and $31/$0.13725 from March 1. Demand charges remain zero;
the customer-plus-demand minimum therefore reduces to the customer charge.

The bill separately identifies REA ($0.40 RS), KEDS ($1 GS), DSM, system sales,
PPA, FTC, FAC, the billing-month fuel credit, GR/DTL, DR, SSR and ES. The 2026
January–April billing-month credit is authorized by the December 22, 2025
amended settlement order. GR and DTL start with March 1, 2026 service, even
when the separately assigned billing month differs.

RS percent-rider bases include ordinary charges and fuel. GS bases exclude
FAC/its credit and subtract embedded base fuel of $0.03380/kWh. **SSR applies
to DR; DR does not apply to SSR**, as the Commission confirmed in case
2025-00307. ES remains a separate percentage of its applicable ordinary base.
The model follows approved tariff calculations and does not reproduce
undercollection caused by the utility calculator's stale SSR formula.

## Source discrepancies resolved or blocked

* January 2026's workbook repeats December's ES factor. The regulator's
  environmental review gives November 2025 expense factors of 0.048531 RS and
  0.087593 all-other for January bills. The filed two-month expense/billing
  lag is retained; the stale 0.050112/0.086949 pair is not substituted.
* March 2026's workbook retains the old base rates. Filed March 1 rates govern.
* Workbook RS energy combines the temporary charge with base energy. The
  adapter separates it once. Workbook GR/DTL row dates also contain stale
  2025 years; filed dates and the rider table establish March 2026.
* Reviewed workbooks exclude DR from SSR, contrary to the May 28 and October 8,
  2026 orders. The Commission's explicit instruction governs over that formula
  and the tariff's narrower enumerated charge list.
* The calculator GS description retains an obsolete demand-based availability
  phrase. Filed availability and actual Company classification govern.
* The current DSM page retains a 2025 end-year caption. The stamped March 2026
  reissue and the continuation proceeding establish the dated scope; later
  October factors are not enabled merely because a workbook lists them.

## PV, storage and verification

RS and GS direct qualifying generation to the applicable generator tariff or a
special agreement. The initial non-export path requires final approval and a
written agreement for the exact PV or PV-plus-storage installation preserving
ordinary import terms without standby or other extra charges. Storage charges
only from onsite PV. Standalone storage, export settlement and credit banks
reject. Hypothetical approvals are labeled as assumptions, not actual consent.

The utility's final development selection passed **109 focused tests** in the
[local receipt](../.cache/kentucky_power_ky/development_final/report.json).
They use independent literal Decimal component vectors, numerical/symbolic
parity at the declining energy-block boundary, next-month billing clocks,
source corrections, account/DER rejection, DST and malformed intervals. Both
native and import restrictions are checked. No actual customer invoice was
supplied. Independent 1,000-kWh component-rounded totals include $174.63 RS /
$200.28 GS for December 2025 service and $203.45 RS / $227.08 GS for March
2026 service, under the explicit following-month billing convention.

Frozen-candidate queued-worker, saved-artifact, historical/OpenDSS and browser
acceptance belongs to the enclosing batch report, not this development receipt.
