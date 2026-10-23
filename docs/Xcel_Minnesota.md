# Xcel Energy Minnesota residential and small-commercial billing

Local candidate, reviewed October 23, 2026. This is Northern States Power
Company's Minnesota retail service, not another Xcel state. The existing shared
browser, isolated worker, PV/storage models, bill/dispatch algebra, CSV/ZIP
exports and representative OpenDSS replay are reused. Stable-engine promotion,
public deployment and desktop GUI development are outside this change.

## Supported account scope

| Plan | Ordinary metered service | Base customer charge | Energy USD/kWh, June–September / other months |
| --- | --- | --- | --- |
| A01 | Residential standard, overhead, non-space-heating | $6/month | .13069 / .11364 |
| A02 | Residential ordinary Time of Day, overhead, non-space-heating | $6/month | On .25879 / .21408; off .05171 all year |
| A10 | Small General, alternating current | $6/month | .11799 / .10094 |
| A12 | Small General ordinary Time of Day, TOD metered | $6/month | On .19782 / .16020; off .05182 all year |

These are base prices, not all-in prices. Required riders and the bounded tax
jurisdiction are separately itemized. These four plans have no measured demand
charge. Larger General A14/A15 demand schedules, ratchets, demand power-factor
adjustments and off-peak excess demand are not enabled by this implementation.

All accounts require independently confirmed utility territory, Minnesota
jurisdiction, ordinary bundled supply, tariff/meter eligibility and tax status.
The representative site at 45.42, -93.83 is explicitly hypothetical. It does not
establish utility territory, an actual interconnection agreement or local taxes.
Small General eligibility includes utility-confirmed classification/history and
required demand metering. Filed rules transfer an account reaching 25 kW to
General service in its next billing month. This model conservatively rejects
any scenario reaching 25 kW instead of attempting that tariff transition.

The first tax-inclusive scope is ordinary taxable service in **unincorporated
Sherburne County**: state 6.875% plus county transit 0.5%, no city/franchise or
special charges. DOR's utility guidance includes fixed, fuel and surcharge
amounts in the taxable sales price. Electric primary-space-heating accounts,
LIHEAP/affordability discounts, exemption certificates, special facilities,
underground service and other jurisdictions are excluded rather than inferred.

## Verified dates and evidence

Executable complete-rate coverage is **January1,2025–September30,2026**, using
complete calendar meter cycles with a bill date on the final service day. These
calendars are hypothetical study assumptions unless the customer independently
confirms the same actual meter cycle. Full-year2025 studies are now enabled.
October2026 is incomplete on the review date; later fuel forecasts do not
establish a completed historical cycle. Earlier/later dates and partial or
shifted cycles remain unsupported.

The former June2025–May2026 gap is resolved by docket **E002/M-25-56**. Xcel's
final filed customer notice (20256-219812-01, clean AttachmentL pp1–2) states
**.00570USD/kWh residential** and **.00518USD/kWh commercial non-demand**, effective
June1,2025 through May31,2026. The July1,2025 PUC order (20257-220520-01, p1)
accepts the sales adjustment and the MISO2024 Planning Resource Auction true-up.
That capacity-related amount is already included in these factors; no separate
MISO capacity charge is added. Published examples reconcile:600kWh residential
adds$3.42 and800kWh Small General adds$4.14 before other charges/tax.

| Component | Verified dated factors used in this extension |
| --- | --- |
| Sales True-Up | Through May2025: residential−.00015, non-demand.00170USD/kWh; June2025–May2026:.00570/.00518; June2026 onward:.00041/.00034 |
| CIP | −.000389USD/kWh through November30,2025; .001397 from December1,2025 |
| RDF | .001385USD/kWh January2025; .001097 February2025–March2026; .001371 from April2026 |
| TCR | Residential/non-demand.004442/.003009USD/kWh in2025; .004436/.003006 January–March2026; .006415/.004445 from April2026 |
| Renewable Energy Standard | 2.41% of base charges through April2026; 2.463% from May2026 |

The source manifest retains official URLs, downloaded-byte SHA256 values,
selected page text and text hashes. Where direct PDF retrieval was blocked,
retained browser screenshots and visual transcriptions are explicitly identified;
the manifest does not claim a hash of undownloaded PDF bytes:
[source manifest](utility_sources/xcel_mn/manifest.json). Full PDFs remain in the
ignored research cache. The ordinary base sheets have January 2025 effective
dates. A June 2025 residential revision changes space-heating prices; ordinary
standard prices do not change. The July 2026 rate-case order requires final
tariff implementation; it is not itself an effective date for replacing the
still-filed interim rates. No proposed rates or 2026 rider proposals are used
as implemented prices.

The utility's generic static ratebook URL is stale and its rider webpage lags
the filed April/May 2026 changes. The current Minnesota-specific public file
viewer supplies the filed sheets; source selection must retain that state.
The retrospective2024 ECO report identifies−.000389/kWh as the existing CIP
factor. The corrected November26,2025 compliance filing (202511-225342-01,
PDFp6, final26th revised sheet5-92) expressly gives **December1,2025** as the
effective date of.001397/kWh, with order dateNovember20,2025. Its bill notice
also saysDecember1. This resolves the rider webpage's conflictingDecember31
entry. The retrospective2025 ECO report corroborates implementationDecember1;
its statedNovember12 approval date is not used instead of the filed order date.

## Charge calculation and TOU rules

- Ordinary TOD on-peak is **09:00–21:00 Monday–Friday**, except New Year's Day,
  Good Friday, Memorial Day, Independence Day, Labor Day, Thanksgiving and
  Christmas. Saturday holidays observe Friday, Sunday holidays observe Monday,
  including New Year's observance across years. This is not the Flex Pricing,
  three-period TOU or EV pilot calendar.
- January 2025 interim surcharge is **7.14% of base customer/energy charges**.
  It is not 5.2% of the entire bill. Fuel and the listed riders are excluded.
- Renewable Energy Standard is 2.41% of base charges through April2026
  and 2.463% from May2026. It does not
  compound the interim surcharge or other riders.
- Fuel is the actual billed FCC for the corresponding calendar month, including
  the dated true-ups, Sherco refund and nuclear production-tax-credit refunds.
  The 2025 utility true-up report, Part A Attachment 7, supplies historical
  actuals. A12 uses **C&I non-demand** fuel, not demand-TOD fuel prices.
- Conservation Improvement, Renewable Development Fund, Transmission Cost
  Recovery, Sales True-Up and affordability charges are itemized. Filed
  mercury, environmental and state-energy-policy zero factors remain explicit.
- Fuel sheet 5-91 weights calendar-month fuel factors by billing days for
  crossing cycles; TCR uses bills rendered. General rule 3.4 has specific
  proration triggers. The first adapter accepts only complete calendar cycles,
  avoiding invented denominators or inconsistent service/bill-date allocation.
- Shared component rounding is half-up cents, with unrounded arithmetic and a
  reconciliation bound retained. Billing and dispatch use the same expression.

Generation/capacity/transmission costs are bundled in retail rates and the
applicable riders. Distribution utility, retail supplier, Minnesota, MISO LRZ1,
NSP transmission owner and any independently verified wholesale cpnode are
separate facts. No wholesale LMP, extra capacity/PLC charge, guessed node or
CAISO carbon signal enters this bundled bill.

## PV/storage, electrical validation and study assumptions

The first DER scope is utility-approved **non-export** operation with ordinary
retail service retained, no NEM/standby/supplemental agreement. Aggregate PV
nameplate plus battery discharge is conservatively bounded to 40 kW as a model
scope limit, not an interconnection entitlement. Grid charging requires its
separate approval. Exports and export credits are disabled.

Every request returns grid-only, PV-only and PV-plus-battery results using the
same native load and weather. Grid-only removes DER eligibility assertions
without pretending a real customer changed enrollment. The generic household
and office loads are synthetic and are not Minnesota-calibrated measured
consumption. Historical ERA5 weather is explicitly selected and retains raw
hashes, grid/request coordinates, UTC timestamps, previous-hour radiation
convention and Open-Meteo/Copernicus attribution. Weather years are never
shifted to make a tariff fit. Clear-sky weather remains an explicit alternative.

Optimization is historical perfect foresight within each billing cycle, not a
forecast controller or proven full-year optimum. Battery wear is optional and
kept separate from utility charges. Existing minimum-cycling proof reporting is
unchanged.

Shared OpenDSS replays every 15-minute scenario interval. Residential uses the
existing representative 120/240-V split-phase service; commercial uses the
configured single/three-phase representative circuit. Scheduled curtailed PV
and battery signs/SOC are preserved. Power-flow losses/PCC measurements do not
change retail meter quantities or bills. This checks quasi-static feasibility,
not surveyed-site, transient or network-constrained dispatch performance.

## Validation

Use `/usr/local/bin/python3 tools/validate.py --tier focused --test
test/test_xcel_mn.py` for independent component benchmarks, observed holidays,
TOU boundaries, dated gaps, Central-time DST, eligibility, absent-equipment
counterfactuals, numeric/symbolic parity and browser-form-to-worker saved-result
checks. Tests are offline. GUI tests remain excluded by project policy.

`tools/run_regional_validation.py --utility xcel_energy_minnesota` supports all
four plans. Its default monthly case is April2025; annual validation runs all
twelve2025 cycles. Explicit custom complete-calendar ranges can select the
verified dates. Prepare actual weather separately with `--prepare-inputs
--env-file /dev/null --inputs .cache/xcel_mn_weather`, then execute using the
matching cached inputs. Private artifacts retain exact candidate attribution;
no candidate or stable engine is promoted by these commands.

### Earlier candidate verification, before the historical-rider extension

Engine `c9abd07f498283ed9e7290b4dd6443fee1650c607a2917bf06087ee3ac50e4dd`; frontend fingerprints are unchanged and retained in the launcher reports. No stable engine was promoted.

- Release tier: **3,528 passed, 1 skipped**, all seven JavaScript checks passed. Three GUI modules excluded; the Caddy integration skip requires its optional test configuration. Twelve SciPy/HiGHS option warnings originate in the unchanged DTE tests.
- Eight independently audited historical studies, four plans in April2025 and July2026: **24 scenario results, 70,272 representative OpenDSS intervals**, all feasible. All primary optima were proven or directly billed; component sums and dispatch bills reconciled. This does not verify a full year or a customer statement.
- Browser acceptance: selected account/region/verified dates, exact input restoration, UI submission, rendered three-scenario comparison/feasibility, name-on-save and reopened saved result verified. The electrical-detail dropdown action immediately after reload timed out and was not retried; its UI selection remains unverified. The 14-file ZIP and saved bytes were checked through API endpoints.

| Period | Plan | Grid only | PV only | PV + battery |
| --- | --- | ---: | ---: | ---: |
| April2025 | A01 | $179.72 | $120.32 | $100.08 |
| April2025 | A02 | $183.08 | $106.58 | $73.23 |
| April2025 | A10 | $458.48 | $299.20 | $284.50 |
| April2025 | A12 | $516.53 | $314.34 | $262.57 |
| July2026 | A01 | $239.47 | $149.26 | $118.06 |
| July2026 | A02 | $245.55 | $130.32 | $82.87 |
| July2026 | A10 | $626.59 | $390.60 | $366.80 |
| July2026 | A12 | $710.54 | $411.16 | $336.46 |

Amounts are tax-inclusive utility charges within the stated scope. Battery wear is excluded from the objective and separately reported. For July2026 A02, estimated wear is $11.37 in addition to the $82.87 utility bill; installation and maintenance costs are not modeled.

Residential: generic synthetic household peak3kW, PV5kWDC/4kWAC, battery10kWh/3kW. Commercial: generic synthetic office peak10kW, PV10kWDC/8kWAC, battery30kWh/8kW. April native consumption is1139.81/3327.82kWh and July1177.01/3460.72kWh respectively. Actual site/year ERA5 weather is used; these are not average-use or measured-load claims.

Private evidence: `.cache/xcel_mn_release/report.json`, `.cache/xcel_mn_matrix_2025/` and `.cache/xcel_mn_matrix_2026/` (each includes `regional/validation-summary.json` and itemized CSVs). The saved local preview and browser receipt are under `.cache/xcel_mn_preview/`; preview port19035. The browser-submitted study reported4.74seconds runtime. Release pytest took652.72seconds; the historical matrix phases took24.85 and25.12seconds. These phase measurements are not total development time or browser automation time.


### Historical-rider extension and full-year2025 validation

Candidate engine `a707bcdbdecb683a7376bead980151884f1202a31b2a2fffa28c83b3a8a2035d` closes June2025–May2026 rate coverage;
it does not promote the stable engine. The earlier c9abd07f4982 evidence above
remains attributed to that earlier pin.

Focused Xcel checks: **169passed**, including independent component bills for
all21 covered calendar months and the filed STUR examples. Shared billing,
dispatch, physical-bound, counterfactual, form/worker, electrical and validation
checks: **224passed**. Seven unchanged JavaScript files pass syntax checks.
GUI tests excluded. The broad release suite was not rerun for this bounded
extension; the earlier release result is not relabeled as current evidence.

The full2025 matrix covers A01/A02/A10/A12, each with grid-only, PV-only and
PV-plus-battery: **12scenarios,144monthly bills,420,480representative15-minute
OpenDSS checks**, all feasible. Every storage cycle has a proven primary cost
optimum and minimum-cycling refinement. The same native/PV input series is
used for both tariffs within each customer class. Monthly bills, component
sums, objective reconciliation, curtailment, no export, rating limits, continuous
SOC and terminal SOC are independently audited by the regional driver.
A separate saved-interval audit checks288monthly STUR/CIP values directly from
meter imports and the documented factors, without calling the bill calculator;
maximum unrounded difference is below1e-8USD.

| 2025 utility charges | Grid only | PV only | PV + battery |
| --- | ---: | ---: | ---: |
| A01 | $2,538.23 | $1,775.55 | $1,498.86 |
| A02 | $2,574.74 | $1,611.92 | $1,154.43 |
| A10 | $6,448.52 | $4,441.55 | $4,246.96 |
| A12 | $7,252.91 | $4,746.73 | $4,050.37 |

Residential native load13,887.5364kWh, generic household peak3kW, PV5kWDC/4kWAC,
battery10kWh/3kW. Commercial native load39,939.108kWh, generic office peak10kW,
PV10kWDC/8kWAC, battery30kWh/8kW. Both use20–80%SOC,95%charge/discharge
efficiency, initial/final50%SOC and explicitly approved grid charging. These
synthetic loads are not measured data or a claim of average Minnesota usage.
Actual2025 site/year ERA5 weather supplies available AC PV7,119.03kWh residential
and14,238.07kWh commercial before scheduled curtailment. Complete hypothetical
calendar cycles, ordinary taxable Sherburne service and non-export assumptions
remain required. Utility bills exclude separately reported battery wear and
installation/maintenance costs; dispatch excludes wear from its objective and
uses rolling-cycle perfect foresight rather than a joint annual optimum.

Evidence: `.cache/xcel_mn_stur_focused_2/report.json` (pytest26.67seconds),
`.cache/xcel_mn_stur_annual_2025/report.json` (shared tests76.64seconds;
annual matrix151.27seconds), nested `regional/validation-summary.json`,
per-study itemized/interval CSVs, and
`.cache/xcel_mn_stur_preview/annual-audit.json`. These are phase wall times,
not total development time. Public source research included one333.87-second
browser file-download stall despite a15-second request, plus one10.09-second
PDF-navigation timeout; neither operation was retried. Browser-viewed official
approval/CIP pages are retained as explicitly labeled screenshot evidence.


The single final browser pass on this candidate opened the saved2025 A02 result,
rendered its three amounts and electrical feasibility banner, showed continuous
2025-01-01→2026-09-30 eligibility coverage, and restored full2025 dates plus all
12explicitly hypothetical meter cycles. API readback matched the original
request exactly; the14-member ZIP passed CRC and saved-byte checks. The electrical
detail dropdown's Playwright label selector returned no_matches in3.31seconds
and was not retried. That specific UI selection, and browser submission/save/rerun
in this pass, are not claimed. Offline form-to-worker/save/restore tests cover
the corresponding contracts. Receipt and screenshot:
`.cache/xcel_mn_stur_preview/browser-acceptance.json` and
`browser-annual-acceptance.png`. Local preview uses the annual matrix store on
port19036; it retains the candidate pin and does not promote any engine.
