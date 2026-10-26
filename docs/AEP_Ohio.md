# AEP Ohio / Ohio Power Company billing

Reviewed October 25, 2026. This adapter models ordinary secondary **RS**
residential service and **GS-1** non-demand general service on the utility's
Standard Service Offer (SSO). The latter's filed name becomes **GS-NDM** under
P.U.C.O. No. 22 on April 10, 2026. The stable model ID is `GS-1`; every bill
retains its actual dated filed schedule name and base version.

Ohio Power Company is distinct from Ohio Edison. The legacy Ohio Power and
Columbus Southern Power rate zones remain explicit account facts; coordinates
or a PJM pricing node do not determine either territory or zone. AEP Ohio's
current [rates page](https://www.aepohio.com/company/about/rates/) describes
both zones. Ordinary class membership and the applicable billing cycle must
be independently confirmed, including for hypothetical studies.

## Supported dates and account

The complete component intersections support January 1, 2025–March 31, 2026
and May 1–October 31, 2026. Only complete calendar meter cycles are accepted,
with consecutive 15-minute `America/New_York` timestamps and an explicitly
aligned utility-designated billing month. The bill date is the final service
day in this bounded workflow. This is an explicitly hypothetical calendar
cycle, not an assertion that a customer's actual meter cycle uses those dates.
Partial/shifted cycles remain rejected.

**April 2026 is unsupported.** Filed No. 22 base rates and several rider
rebases take effect April 10. The verified prices do not establish a complete
allocation rule for an April 1–30 cycle. No service-day blend, end-of-cycle
base rate, or fixed-charge proration is silently assumed. Annual 2025
simulation is fully supported; this is not full-year 2026 coverage or a
promise about unpublished November–December 2026 prices.

RS is ordinary single-meter residential secondary service. Common areas,
separate commercial uses, primary service and special/legacy electric-heat
options are excluded. The non-demand commercial schedule requires maximum
demand **less than 10 kW**, plus utility-confirmed classification/history.
For the 2026 successor, the tariff additionally describes the prior 12-month
classification conditions. A simulated small peak alone does not establish
enrollment. Billing and dispatch enforce imports below 10 kW, including
battery charging. These selected plans have no measured customer-demand
charge and no TOU energy periods; holidays do not alter their all-hours prices.

The initial physical/account scope is one secondary 120/240 V single-phase
meter, ordinary SSO, unity billing power factor, standard kWh tax, no PIPP
assistance or tax self-assessment, special agreements/credits, extra
facilities or AMI opt-out. An explicit locality confirmation establishes that
there are no additional municipal/franchise charges. This is separate from
the weather coordinate and from actual account eligibility.

## Itemized charges and optimization

All prices are stored in dollars, with cents/kWh converted explicitly.
Numerical billing and CVXPY dispatch call the same `charge_lines` expressions:

- Base customer and distribution energy charges.
- Enhanced Service Reliability, Distribution Investment, Economic
  Development and zero Bad Debt percentage riders, applied independently to
  **base customer plus distribution energy**, excluding all other riders.
- Fixed gridSMART, storm-damage and applicable legacy/solar-fund charges.
- Separate retail Basic Transmission, PIPP/USF, throughput balancing,
  efficiency, tax savings and other filed riders, including documented zero
  placeholders.
- SSO Generation Energy, Generation Capacity, Auction Cost Reconciliation
  and Alternative Energy components. The published residential Price to
  Compare is a rounded cross-check, not an additional charge.
- Monthly Ohio kWh tax tiers: $0.00465/kWh for the first 2,000 kWh,
  $0.00419 for the next 13,000 and $0.00363 thereafter. PIPP has its own
  833,000-kWh boundary; the filed commercial SGF cap/volume boundaries are
  preserved even though they cannot bind an ordinary sub-10-kW test case.

Capacity is already in the retail Generation Capacity rider, and transmission
in Basic Transmission. No extra PJM LMP, PLC or transmission-tag payment is
added. The 1CP/6CP transmission pilot, demand-metered GS, wholesale pass-through,
competitive supplier contracts, TOU/EV pilots and large-load/data-center
schedules have different eligibility and rules and are not offered here.

Battery wear is separately reported and is excluded from bill-only dispatch
unless the shared explicit wear option is selected. Perfect-foresight rolling
cycle studies do not prove annual joint optimality or forecast-based control.
OpenDSS measurements/losses remain separate from the scheduled meter flows
used in the bill; replay is representative electrical validation after dispatch.

## Historical boundaries and source conflicts

The [source ledger](utility_sources/aep_ohio/sources.json) preserves original
PDF hashes, selected pages, extracted-text hashes, official URLs and separate
indexed historical evidence where a superseded original now returns 404.
Original PDFs and workbooks remain in ignored `.cache` storage. No utility
rates or policies are inferred from neighboring periods.

Key distinctions include:

1. The February 2025 throughput rider credits **Columbus Southern Power RS**
   at $0.000182/kWh. Ohio Power RS and both GS non-demand classes are zero;
   March restores zero for both zones. Omitting the legacy zone would miss
   this real class-specific difference.
2. July 2025 LGR revision 8 sets residential $0.88/month and commercial
   $0.0016400/kWh up to 833,000 kWh. The archived July book retains older
   revision 7; the later official indexed August sheet explicitly supplies
   revision 8 and its July 1 application date. The model follows the dated
   sheet rather than the misleading book title.
3. The filed zero LGR/SGF sheets apply to all customer bills effective August
   14, 2025. The [Ohio Legislative Service Commission's final HB 15 analysis](https://www.legislature.ohio.gov/download?key=25768)
   also confirms that an EDU may not collect LGR from any customer beginning
   that date. An aligned August 31 bill therefore uses zero on the entire
   bill, not an invented 13/31 residential fixed-charge allocation. General
   shifted-cycle service-date allocation is not thereby implemented.
4. The utility's October 2026 book erroneously retains obsolete **No. 21**
   EDCR sheet 420-1 at 2.39150%. The regulator's **No. 22 original** sheet,
   effective April 10, establishes **1.80190%**. The June/July 2026 originals,
   September utility bill example and October utility workbook independently
   corroborate the latter. The model uses the applicable No. 22 sheet and
   retains the conflicting source as evidence.
5. The December 2025 ESRR sheet's embedded font cannot be reliably extracted.
   Its **7.88222%** factor and effective date were visually checked against
   the original regulator PDF page 164; a separate visual-source record
   prevents corrupted extraction text from becoming rate data.

The ten-year research target is separate from executable history: PUCO's
public residential PTC index supplies older annual tables, but does not
establish all older distribution, fixed, rider and account rules. Complete
2016–2024 billing coverage is not claimed.

## PV and storage

The filed RS and general-service special terms allow ordinary service for
some customer-side sources, or an explicit utility agreement. PURPA qualifying
facilities may require COGEN/SPP, NEMS or an agreement. Consequently PV/storage
requires `der_ordinary_service_confirmed` plus a source/explicit hypothetical
ordinary non-export agreement. Zero exports are enforced. Eligibility is not
inferred from export prevention alone. Standalone storage, standby charges,
NEM credits and export settlement remain unsupported.

## Verification

The focused tests independently calculate each supported plan-month bill from
literal source prices, rather than reusing the production lookup. They cover
both legacy zones, DST, mandatory rider changes, credit ordering, monthly tax
tiers, class limits, missing/duplicate intervals, rejected partial periods,
unknown dates and numerical/CVXPY parity.

The official September 2026 residential 1,000-kWh example reconciles exactly
to **$219.22**. The utility's October 2026 bill-calculation workbook independently
reconciles to **$211.51 RS** and **$206.38 GS-NDM** at 1,000 kWh. These examples
sum individually cent-rounded lines, while dispatch uses the unrounded
underlying expressions; statement rounding is not represented as a false
solver-proof failure. Historical source validity is separate from solver
optimality and electrical replay success.

Run with `/usr/local/bin/python3 tools/validate.py --tier focused --test
test/test_aep_ohio.py`. Shared annual and browser validation receipts are
recorded by the integration workflow under their own frozen engine IDs.
