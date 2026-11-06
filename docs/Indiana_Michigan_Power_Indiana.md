# Indiana Michigan Power · Indiana bundled electric service

The regional study supports IURC No. 20 ordinary residential RS 015/016
and secondary GS 215/218 for confirmed non-demand-metered customers.
The four codes appear individually in the catalog so the account record
keeps the exact I&M assignment. The two codes within each schedule use
the same filed rates in this scope.

Use the Indianapolis civil clock and complete 15-minute data. This model
uses matching complete calendar meter cycles and bill months, with the
bill dated the last day and the full monthly charge. I&M typically reads
meters at approximately 30-day intervals on different billing schedules.

| Year | Supported complete cycles |
| --- | --- |
| 2025 | June–September and November–December |
| 2026 | January–April and July–November |

I&M sets its FAC by service date when the filed sheet specifies an
effective service date, and uses the assigned bill month when the sheet
specifies bills rendered. The early 2025 intersection lacks final FAC 93
and earlier Phase II evidence. May and October 2025, May–June 2026 and
December 2026 are explicitly blocked. The [source ledger](utility_sources/im_in/sources.json)
details the boundary and source grade for each interval.

## Eligibility and billing

- Confirm ordinary bundled service on one 120/240 V single-phase secondary
  meter. The initial scope excludes optional rates, incentives, standby
  charges, adjustments for metering at a different voltage, exemptions,
  credit balances and other account-specific charges.
- Sheet 4 charges $15 per month with a 900 kWh energy breakpoint for RS.
  Its base minimum is $15. Sheet 12 charges secondary GS $29 per month
  with a 4,500 kWh energy breakpoint. This GS model prices the first block
  and independently bounds native load and imports at 4,500 kWh per
  cycle and 10 kW. RS has a 25 kW study cap.
- Sheet 12.1 allows I&M to install a demand meter at any usage and requires
  it at an average of at least 4,500 kWh per month. Obtain independent I&M
  confirmation of no demand meter or billed demand, no pending
  reclassification, and an average below 4,500 kWh. The sheet's demand
  charge on demand above 10 kW is outside the non-demand-metered scope.
  Confirm ordinary non-opt-out DSM/EE for GS. For multicycle actual studies,
  review these facts for each cycle and supply cycle overrides if they vary.
- The filed base rate bundles supply and delivery. FAC, DSM/EE, ECR,
  OSS/PJM, RA, SPR, the Phase-In Rate Adjustment credit and the Tax Rider
  stay itemized. State sales tax applies at 7% to the ordinary taxable
  subtotal, including the fixed charge and net rider amounts. The
  ratemaking Tax Rider is separate from that sales tax. The study retains
  unrounded component arithmetic and reports component-rounded cents.
- The default supplier and distribution utility are I&M Indiana. The
  retail OSS/PJM Cost Rider is independent of the PJM AEP zone and any
  optional wholesale price data. The model adds no wholesale settlement
  charge to the retail bill.
- For PV or PV-plus-storage, supply final I&M interconnection approval and
  a written agreement covering the exact non-export installation with
  ordinary import rates and no separate standby charges. Approval must be
  active for the entire cycle. Storage charges only from onsite PV.
  Export, Rider NMS, Rider EDG, COGEN/SPP, standalone batteries and
  demand-metered GS are outside the implemented scope.

See the [implementation and validation evidence](Indiana_Michigan_Power_Indiana_Implementation_Validation.md).
