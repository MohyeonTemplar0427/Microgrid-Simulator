# Ameren Missouri residential and small-commercial billing

Local candidate, reviewed October 21, 2026. Rates are separate from Ameren
Illinois. The shared regional browser, queued worker, dispatch, CSV/ZIP tables
and representative OpenDSS replay are reused. No stable-engine promotion or
public deployment is implied. Desktop GUI work remains paused.

## Supported account boundary

- Residential classification **1(M)**: Anytime, Evening/Morning Saver,
  Smart Saver year-round A / summer-only B, and Overnight Saver year-round A /
  summer-only B. All modeled TOU accounts require confirmed AMI and enrollment.
- Commercial **standard 2(M)** Small General Service, secondary single-phase
  240 V or three-phase 480 V. Residential uses 120/240-V split phase.
- Ordinary bundled supply, full monthly charges, complete calendar service and
  billing months. All service dates must be January 1, 2025–October 21, 2026;
  consequently the last accepted complete month is September 2026. October
  rider changes are retained and tested, but an incomplete October cycle is
  not converted into a full bill or extrapolated into future service.
- First tax-inclusive scope: independently confirmed **unincorporated Cole
  County**, jurisdiction **00000-051-000**, no city/special district/franchise
  or underground charges. Official DOR tables show domestic utility tax 0% and
  ordinary commercial sales tax 5.6000% throughout the retained 2025/2026
  periods. This is an account restriction, not a coordinates-to-tax finding.
- Approved non-export renewable PV, optionally with storage, explicit written
  interconnection/ordinary-tariff eligibility. No NEM agreement, export credit,
  standalone storage or standby enrollment. A conservative model limit of
  50 kW aggregate PV nameplate plus storage discharge is not a statutory limit.
  Rider SSR addresses applicable generation/storage over 100 kW on larger
  classifications; its exemption and applicability must not be generalized to
  an unreviewed large installation.
- Historical 2(M) account eligibility is independently confirmed. This first
  model additionally constrains every scheduled import to at most 100 kW;
  reducing current import does not prove eligibility or undo a prior transfer
  to 3(M). The filed transfer trigger is summer demand exceeding 100 kW.

The hypothetical site at 38.49, -92.16 identifies a study location only. Distribution
utility, Missouri jurisdiction, supplier, tariff, MISO LRZ5, transmission owner
and optional verified pricing node remain separate facts. MISO transmission
pricing Zone3B is not capacity LRZ5. No wholesale price enters the bundled bill,
no separate PLC/transmission add-on is charged, and no CAISO carbon is assigned.

## Rate and billing rules

`src/billing/ameren_mo_rates.py` holds dated Python literals included in immutable
engine snapshots. Official documents and retained page hashes are in
[the source manifest](utility_sources/ameren_mo/manifest.json). Full downloaded
PDFs and weather inputs stay in the ignored research cache.

Base prices change June 1, 2025, with the filed rates continuing into the verified
2026 window. FAC, SUR, EEIC and RESRAM use their own exact service dates. FAC
secondary factors are already voltage-adjusted; do not multiply them by losses
again. The June 2025 FAC is the actual 6th revised sheet 71.32 ($0.00360/kWh),
not the zero-filled template on original sheet 72.14. RESRAM changes from
$0.00313 to $0.00133/kWh on June 1, 2025 as recoveries move into base rates;
using its original February annual factor for all of 2025 would double count.
All fixed customer and low-income pilot charges, mandatory riders and the
applicable Cole County sales tax are itemized. Capacity and transmission are
bundled in filed base/FAC costs; no MISO market charge is added.

Summer is June 1–September 30 by service date. Normal cycle proration is described
on sheet 130 but this first model does not invent operational denominators or
block allocation across seasons/base revisions. Partial, cross-month, initial,
final and rerouted bills are explicitly rejected.

Anytime winter energy uses first 750 kWh/tail declining blocks. EMS applies its
winter blocks to total energy and adds its on-peak adjustment to on-peak kWh.
EMS on-peak is 09:00–21:00 every day. Overnight on-peak is 06:00–22:00 every day.
Option B Smart/Overnight use Anytime rates in winter.

Smart Saver on-peak is summer 15:00–19:00 and winter 06:00–08:00 plus 18:00–20:00,
Monday–Friday excluding nine named actual holidays. Intermediate is 06:00–22:00
outside peaks, off-peak 22:00–06:00. The nine dates are New Year's Day, Good Friday,
Memorial Day, Independence Day, Labor Day, Thanksgiving, Thanksgiving Friday,
Christmas Eve and Christmas. There is no filed Friday/Monday substitute rule;
July 3, 2026 remains an ordinary weekday. The calendar is shared by diagnostic
interval rates and the authoritative bill/optimizer expression.

## Commercial winter history

Sheet 55.1 defines seasonal energy as kWh exceeding both 1,000 and the lesser of:
the preceding May kWh, the preceding October kWh, and the maximum monthly kWh
in any preceding summer month. The model requires those dated, documented
billed-import determinants explicitly. It does not infer them from native load,
weather or the current cycle. The account opening summer maximum must encompass
all preceding summer months, not just a silently truncated year.

Numeric bills use `max(1000,min(May,October,summer maximum))` as the Base-use
threshold; the remaining energy gets the Seasonal-use price. The exact same
filled-block expression enters optimization. Each scenario carries its own
history, updating May/October imports after those cycles and the summer maximum
after each summer cycle. All scenarios start with the same inherited account
history; a no-PV reference removes DER assertions without erasing that history.
State must continue into the next cycle, with no future or skipped determinants.
This literal preceding-month model is not a claim about undocumented company
rebilling procedures. Missing-history/electric-heating half-use and later-refund
rules on sheet 55.2 remain unsupported rather than estimated.

## Unsupported features

Other local tax jurisdictions, exemptions and special charges; Ultimate Saver
one-hour demand billing; grandfathered residential TOD; commercial optional
Overnight/TOD; non-AMI meter fees; NEM/netting/export/annual settlement; third-party
supply; community solar, rebates/EE opt-outs, standby/primary service; and cycle
proration. Unsupported dates and eligibility raise errors, with no fallback.

## Validation

Independent filed-arithmetic benchmarks cover base revisions and every rider,
seasonal blocks, tax bases, Smart holidays and boundaries, EMS/Overnight every-day
pricing, Central-time DST, commercial history/state continuity, symbolic/numeric
parity, and dispatch/bill reconciliation. Browser serialization-to-worker tests
cover all three equipment scenarios, electrical results, save/reopen and CSV/ZIP.
Final regression and historical-study results are recorded in the
[integration handoff](Ameren_Missouri_Integration_Handoff_20261021.md) on the frozen
candidate. The release run passed 3,421 tests with one opt-in hosting skip;
GUI tests were excluded. The final browser pass also verified submission,
rendered bills, save/reopen and restoration/rerun. Simulated loads remain synthetic, not
customer-calibrated; ERA5 is historical reanalysis, not measured subhourly weather.

## Completed historical comparisons

### Full-year 2025

| Plan | Grid only | PV only | PV + battery |
|---|---:|---:|---:|
| 1M | $1,757.86 | $1,277.63 | $1,080.12 |
| 1M-EMS | $1,756.60 | $1,270.67 | $1,070.62 |
| 1M-SMART-A | $1,785.68 | $1,223.95 | $756.66 |
| 1M-SMART-B | $1,757.51 | $1,221.48 | $933.38 |
| 1M-OVERNIGHT-A | $1,758.31 | $1,150.69 | $842.19 |
| 1M-OVERNIGHT-B | $1,761.57 | $1,234.12 | $970.30 |
| 2M | $11,900.45 | $10,340.21 | $10,338.85 |

### January–September 2026

| Plan | Grid only | PV only | PV + battery |
|---|---:|---:|---:|
| 1M | $1,469.95 | $1,029.81 | $847.29 |
| 1M-EMS | $1,468.43 | $1,023.49 | $838.83 |
| 1M-SMART-A | $1,493.30 | $977.05 | $586.99 |
| 1M-SMART-B | $1,474.77 | $977.74 | $698.73 |
| 1M-OVERNIGHT-A | $1,470.56 | $924.46 | $652.11 |
| 1M-OVERNIGHT-B | $1,473.88 | $986.77 | $737.54 |
| 2M | $9,729.17 | $8,411.68 | $8,411.14 |

These are synthetic facility comparisons under the confirmed hypothetical account
facts, not calibrated customer bills. All use actual site/year-matched ERA5,
south-facing PV at 30° tilt, 14% system losses and 96% inverter efficiency.
Residential: 3 kW generic peak, 5 kW DC / 4 kW AC PV, 10 kWh / 3 kW storage.
Commercial: 25 kW generic peak, 10 kW DC / 8 kW AC PV, 30 kWh / 8 kW storage.
Battery charge/discharge efficiency is 95% each, with 20–80% SOC and initial/final
50%; SOC continues across cycles. Wear is excluded from the default bill
objective and reported separately.

All 14 studies / 42 scenarios passed independent audits: 441 cycle bills and
1,286,124 electrical intervals, zero electrical failures; maximum unrounded
objective/bill difference $0.00000100. Every primary cycle cost optimum was
proven or a direct bill. Minimum cycling was proven for 142/147 battery cycles;
five retained the verified primary cost-optimal schedule with an explicit
warning (2025 EMS April, Overnight A February, Overnight B January; 2026 EMS
March, Smart B April). This secondary refinement limitation does not invalidate
the primary cost proof.

Representative electrical circuits: 25 kVA / 100 A 120/240 V split-phase
residential and balanced 480 V / 750 kVA commercial, 0.95 lagging physical load
PF. These are not surveyed networks or Ameren service standards. No protection,
transient or network-constrained optimization claim.

Evidence: `.cache/ameren_mo_validation_2025_final/validation-summary.json` and `.cache/ameren_mo_validation_2026_final/validation-summary.json`, engine `d3e9c7bb032eb6721fd027d52e72e1104669e7e313be76f24344b5ef613a0d2f`. Original failed-candidate artifacts retain their own pin.
