# Atlantic City Electric New Jersey RS / MGS-Secondary

Verified development scope reviewed October 27, 2026. Utility key
`atlantic_city_electric_new_jersey`; ordinary **RS residential** and measured
**MGS-SECONDARY** commercial with utility default **BGS-RSCP**. The source ledger,
dated originals, component pages and blocked/gap notes are in
[utility sources](utility_sources/atlantic_city_electric/README.md).

## Executable account and date scope

The first implementation accepts **exactly 30 complete local service days inside
one calendar month, season and verified component regime**, with a final-service-day
bill date and an explicitly documented or hypothetical cycle. Section II 6.5
requires proration for other durations, but the component-specific formulas have
not been verified. A 31-day calendar month is not silently charged as 30 days.
For example, October 1-30 can run; October 1-31 rejects. February has no executable
30-day within-month cycle. Actual shifted or crossed-month cycles are unsupported.

| Component intersections | Main evidence |
| --- | --- |
| February-April 2025 | February adopted book plus direct next-revision continuity |
| May 2025 | Same base/riders/supply, independently dated May 1 TEC from June book |
| June 2025 | June adopted book; deleted NGC and zero ZEC are explicit |
| July-August 2025 | July book and mandatory residential $30 monthly credit |
| October-November 2025 | October book; November current/redline adoption evidence |
| September 2026 | September adopted book and separately dated components |
| October 2026 | October adopted book; transmission and riders change October 1 |

January, September and December 2025 and January-August 2026 do not have an
executable complete component stack here. Known prices in the ledger do not fill
these gaps. Later dates reject. **Full-year 2025 and annual billing are unsupported**;
neither cached annual weather nor short-cycle acceptance establishes annual coverage.

The initial physical/account domain is one ordinary taxable 120/240 V single-phase
secondary meter/service and unity **billing** power factor. The representative
OpenDSS circuit has independently declared assumptions. Multi-meter aggregation,
other voltage/phase, exemptions, religious/veteran discounts, heating exclusions,
EV programs, development/facility contracts, computed fixed loads and special
standby service are excluded by explicit account confirmation, not inferred absent
from coordinates or demand.

MGS requires measured 15-minute demand and independently utility-assigned annual
generation-capacity **PLS below 500 kW** for the relevant November assignment, with
confirmed BGS-RSCP and no CIEP election. The study's actual import peak is bounded
to 100 kW. A modeled monthly peak does not determine PLS or supplier eligibility.
Unmetered summer energy/150, annual ratchets and hourly CIEP supply are unsupported.

## Charges, measurement and objective

All ordinary recurring tariff components are included within the accepted domain.
Base distribution, BGS energy, BGS-RSCP reconciliation, transmission, TEC, SBC,
RGGI/EECEC, IIP, CIP, SEC, EDIT, ZEC and the dated RS fixed deferral are itemized.
Published SBC/RGGI totals reconcile with their components and are not added twice.
NGC deletion, zero rates and negative ZEC credit retain their source signs/dates.
IIP is added once to the published base rates, with its own explanatory lines.

Published rates include **CBT/SUT**; supply energy also includes generation capacity,
ancillary services and administration. No extra 6.625% tax, wholesale LMP, PLC/NSPL
or supply administration charge is added. Tax-exempt and special accounts reject.

RS has summer 750 kWh distribution/supply blocks; winter distribution's printed
500 kWh split has identical prices, and winter supply is flat. RS keeps raw energy:
the MGS-only quantity-rounding clause is not imported. The mandatory residential
fixed adjustment is -$30 in July/August 2025 and +$10 September 2025-February 2026,
only where the other component stack is verified. Negative raw or component-rounded
post-credit balances reject because refund/carry settlement is unverified. The
optimizer does not force purchases to make such an account pass.

MGS distribution demand and IIP demand use **all billed kW**. Transmission demand
uses only the amount above **3 kW**. Unity billing PF makes the reactive-demand
charge inactive. The ordinary minimum is the applicable customer charge plus
adjustments; nonnegative distribution energy/demand and the accepted ordinary
rates make that minimum inactive. No invented extra floor is added.

The final MGS bill rounds energy to the nearest **0.01 kWh** and demand to the
nearest **0.1 kW**. Exact half ties reject because their convention is unverified.
Its dispatch reuses the existing objective-input contract and optimizes charges
using quantities **before measurement rounding**. The final quantity-rounded bill
is computed separately. An explicit charge-error bound reconciles their unrounded
component totals. Primary-cost and minimum-cycling proofs apply to this proxy,
**not a minimum rounded customer invoice**. The internal account type cannot be
requested through JSON to disable final billing rules.

Shared component half-up monetary cents and the unrounded component totals are
both retained. Exact line-versus-invoice rounding has not been independently
calibrated. Complete ordinary component coverage does not assert exact printed
invoice matching or global rounded-cash optimality. The official 650 kWh October
2026 transmission increase independently reconciles to $1.60; PTC displays are
rounded comparisons, and the commercial transmission average is not an account
demand rate. Source notes retain the PTC heading/image date conflict.

## PV, storage and regional metadata

PV or PV-plus-storage needs written ordinary Class I/NEM-account parallel approval,
zero exports, zero opening bank and no standby/special fees. Combined PV/storage
study capacity is at most 25 kW; that limit does not prove actual interconnection
eligibility. Historical NEM leaves retain ordinary rates and billing units when
there are no exports. No export compensation, credit bank, annual true-up,
community solar or standalone storage is enabled.

RS has source-backed historical ordinary PV scope. **MGS 2025 DER rejects**: its
historical standby rule uses generation availability and six-month history that
this adapter does not model. MGS 2026 DER uses the adopted December 2025 standby
rule and explicit written ordinary-service approval. The grid-only reference
removes DER assertions while retaining tariff, PLS and all other account facts.

The explicit hypothetical reference is 39.45 N, 74.58 W in Atlantic County, NJ.
Coordinates do not assign retail territory or enrollment. PJM's **AECO** transmission
zone is metadata; utility, supplier, NJ jurisdiction, PLS, tax status and an optional
wholesale pricing node remain independent. BGS-RSCP does not require wholesale prices.

## Validation and limitations

Use the [targeted validation policy](Development_Validation.md#select-validation-by-change-impact).
Utility-specific tests cover literal filed arithmetic, dated boundaries, tax/admin
inclusion, independent benchmarks, quantity/proxy parity, DST and rejection cases.
Direct form/queued-worker/save/CSV-ZIP tests and changed JavaScript syntax checks
cover the new wiring. Selected historical studies use actual-year weather and
synthetic native load, with every interval checked by representative OpenDSS.
The [implementation report](Atlantic_City_Electric_Implementation_Validation.md)
records the frozen candidate, exact selections, results and exclusions.

Historical perfect foresight runs cycle by cycle. No annual optimum, customer
savings, field validation, exact printed-invoice calibration or unverified export
settlement is claimed. Desktop GUI development remains paused; deployment and
stable-engine promotion require separate authorization.
