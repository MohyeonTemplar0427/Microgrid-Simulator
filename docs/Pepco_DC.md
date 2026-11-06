# Pepco District of Columbia R and GS-ND SOS

The regional adapter implements ordinary Pepco DC Residential R and
secondary General Service Non-Demand GS-ND Standard Offer Service.
Utility identity, District of Columbia jurisdiction, SOS supplier,
PJM PEPCO zone and optional wholesale price data remain independent.

## Executable coverage

| Period | Coverage |
| --- | --- |
| June 2025 | Complete matching calendar cycle |
| June–October 2026 | Complete matching calendar cycles |

The [source ledger](utility_sources/pepco_dc/sources.json) retains dated
tariffs, monthly administrative credits, BSA evidence, surcharge tables
and hashes. Other 2025–2026 months reject. The June 2025 credit chart
fills June alone. Its later blank columns cannot establish rates. The
October 2026 chart explicitly fills June through October with zero
administrative credit. Both years' full annual billing remains blocked.

June 2026 retains the prior summer generation prices. July 2026 starts
the new awarded generation prices and administration. The filed 2026
transmission is applied separately. October 2026 implements the filed
statutory SETF and Mayor's Energy Surcharge Fund changes. The prior
surcharge fiscal-year dates are retained.

BSA Adjustment II uses the utility's published rate table, corroborated
by its August 2026 PSC report. The report identifies continued Adjustment
II collection and states that Adjustment I recovery for 2026 revenues is
expected after PSC approval in 2027. The statutory annual BSA formula
alone is insufficient to manufacture a new billed factor.

## Account and billing scope

R serves individually metered ordinary residences. GS-ND is retained by
Pepco for maximum monthly demand below 25 kW, with the utility's annual
June reclassification rules. The model requires retained GS-ND status
and twelve independent actual monthly demand values below 25 kW.
It also requires confirmed non-demand metering, independent current-cycle
Company review with no pending reclassification, and all twelve prior
monthly energy readings below 6,000 kWh. R-6.1 calls for demand metering
after two winter months above 6,000 kWh, one summer month above 7,500 kWh,
or any month at or above 25 kW. Reversion to non-demand billing requires
each prior twelve months below 6,000 kWh and demand below 25 kW. The
initial study further limits current native energy and imports to below
6,000 kWh in every GS-ND cycle. Reduced modeled imports never establish
historical eligibility.
For a multicycle actual study, confirm assignment for each cycle and
provide account overrides where appropriate. All initial studies use
one single-phase secondary 120/240 V meter. Native load and imports
also stay below the declared 25 kW study envelope.

Use complete consecutive Eastern-time 15-minute intervals and a
complete matching calendar service and bill month, full monthly
charges and a final-day bill date. These are explicit study restrictions.
Utility meter-reading schedules differ from this calendar assumption.

The R generation minimum includes the first 30 kWh and administration
on those kWh. Energy and administration above 30 kWh are charged
separately. Its transmission minimum also includes the first 30 kWh.
Distribution and EDIT use their separate 400 kWh blocks. GS-ND
generation, administration, transmission and energy riders apply to
all imported kWh. Supply prices include applicable taxes. The
statutory delivery tax remains separately itemized at the filed class
rate. The model adds no wholesale energy, capacity or transmission
settlement charge.

The bill also itemizes PCA, administrative credit, BSA Adjustment II,
PSOS, SETF, EATF, RADS, UPC, the dated Underground Rider, MRP and EDIT.
The model excludes accounts receiving RAD, senior/disabled relief,
community-solar credits, optional programs or special-service terms.
Its result is a complete ordinary bill within these conditions.
Invoice-specific rounding may differ from the study's component rounding.

## PV and storage

Initial solar studies require a documented Pepco agreement and final
interconnection approval preserving ordinary import billing for the
exact non-export PV or PV-plus-storage installation. Approval must
precede the cycle. Paired storage charges only from PV. No export
settlement, NEM bank, standby schedule or standalone battery billing
is implemented. Hypothetical studies explicitly label the assumed
approval.

## Development verification

The utility tests independently transcribe source rates using Decimal
arithmetic. They exercise all complete component stacks at 0, 15, 30,
30.5, 399.5, 400, 400.5 and 1,000 kWh, exact numeric/symbolic parity,
date gaps, eligibility, DST source-gap rejection, missing/duplicate
intervals, native-load boundaries, state rejection and DER approval.
The batch implementation report owns the final frozen-candidate,
worker, artifact, historical and browser acceptance evidence.
