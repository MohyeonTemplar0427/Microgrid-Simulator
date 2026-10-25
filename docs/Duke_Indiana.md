# Duke Energy Indiana candidate billing

The shared regional browser workflow supports one deliberately bounded first
case: verified March 2025 service and billing designation on ordinary bundled
residential RS/RS-TOU or commercial CS/CS-TOU. A separately selected,
explicitly accepted `provisional_2025` mode enables standard RS/CS studies
throughout 2025 using the component assumptions below. It does not turn those
assumptions into verified historical rates. TOU has no coverage before
February 27; broader 2025 TOU dates also retain the disclosed calendar
interpretation uncertainty. No 2026 prices or wholesale-as-retail substitutes
are enabled. The default evidence mode remains `verified`.

The representative location is near Plainfield, Hendricks County, Indiana,
39.70 N, 86.40 W, using `America/Indiana/Indianapolis`. Its coordinates do not
establish Duke service, tariff enrollment, tax jurisdiction or interconnection
eligibility. The account must separately confirm those facts or explicitly
describe a hypothetical study.
Complete regular meter cycles of 26–34 whole local days use the full rate
schedule under General Terms12.4, including the full connection charge and
energy-block quantities. The ordinary March calendar cycle remains the default.
The designated billing month is explicit and separately validated; unsupported
service/billing combinations and base-reset crossings reject. Provisional mode
can span civil months under the explicit designated-bill-month assumption;
it does not enable partial, extended or initial/final-service proration.

## Retail plans and electrical scope

The IURC16 original sheets became effective February 27, 2025. Ordinary RS
and CS have decreasing monthly energy blocks and a monthly connection charge;
they do not bill a measured demand charge. The selected first scope uses
single-phase 120/240 V service, maximum load requirements of 75 kW or less.
The filed alternative 120/208 V arrangement is not included in this first
electrical configuration. Three-phase service and larger demand-billed tariffs
are separate future work; ordinary CS is not assigned to a data center.

| Plan | Monthly connection | Base energy, USD/kWh |
| --- | ---: | --- |
| RS | 13.70 | First 300 kWh: .186556; next 700: .135777; over 1,000: .123051 |
| RS-TOU | 13.70 | Peak .214198; off-peak .142799; discount .085679 |
| CS | 13.91 | First 300 kWh: .178612; next 700: .165677; next 1,500: .150517; over 2,500: .122691 |
| CS-TOU | 13.91 | Peak .169081; off-peak .148754; discount .097014 |

These are base prices, not all-in retail rates. Billing includes the ten
applicable reset adjustments: fuel60, environmental62, TDSIC65,
energy-efficiency66, credits67, RTO68, reliability70, federal72,
renewable-project73 and load-control74. The February reset moved costs into
base rates; adding January 2025's earlier EE/load-control factors would double
count some costs. The fuel adjustment is negative .001521 USD/kWh; the base
fuel of .034378 USD/kWh is already included and is not charged again.

Ordinary taxable accounts include Indiana's 7% sales tax on pre-tax retail
charges. The utility receipts tax was repealed July 2022 and is not added.
Manufacturing, nonprofit, agricultural and other exemptions, extra local
charges, assistance programs, EE opt-outs, AMI opt-out fees, excess facilities
and negotiated agreements are outside this adapter's ordinary-account scope.
Users must confirm their actual tax and local-charge treatment.

## Time-of-use calendar

Both TOU plans require voluntary enrollment, smart metering, a prior twelve-month
average Billing Maximum Load of at least 1 kW, and maximum load no greater than
75 kW. These are account facts, not inferred from a synthetic study month.

The filed peak is 5–9 p.m. Eastern standard time every day, plus 6–8 a.m.
during winter. Discount hours are midnight–4 a.m. Eastern standard time.
The tariff shifts those windows one hour later on daylight clocks: the summer
evening peak is 6–10 p.m. EDT. Winter runs from the first Sunday in November
to the second Sunday in March. There is no weekday-only restriction.

New Year's Day, Memorial Day, Independence Day, Labor Day, Thanksgiving and
Christmas are off-peak for their entire local civil day, including discount
hours. Saturday holidays include the observed Friday; Sunday holidays include
the observed Monday. The holiday date is matched before the standard-clock
conversion, preserving the first local hour of a daylight-time holiday.
Juneteenth and Good Friday are not silently imported from other utilities'
calendars. Interval grids preserve both fall-fold timestamps and the spring
gap; March 2025 has 743 elapsed hours.

An additional source review found a calendar discrepancy that remains unresolved.
The filed RS6.5/CS7.5 sheets specify that a holiday's entire 24 hours are
off-peak and do not state a weekday-only peak restriction. The January29 order's
witness summary (pages101–103) and the utility's
[business2025 TOU explanation](https://www.duke-energy.com/business/billing/rates/new-2025-tou-rates-dei)
describe weekday peaks; the business guide additionally includes holidays in
the discount period. The guide does not identify RS/CS and may describe other
commercial TOU schedules; it cannot silently replace their individual sheets.
The current calendar follows the filed individual tariff
sheets. Arithmetic reconciliation and simulation sweeps establish that
implementation's consistency, but do not resolve the conflicting source
descriptions. Actual-account TOU use requires confirming which rules govern
the specific enrollment; no pre-February27 TOU prices are inferred. Broader
2025 provisional TOU studies retain the same filed-sheet interpretation and
source-discrepancy warning.
TOU results carry a warning and
`calendar_evidence_status=filed_sheet_interpretation_utility_confirmation_required`.
Numeric prices remain filed-source verified, while completeness and optimality
are expressly conditional on that calendar interpretation. Standard RS/CS
results are unaffected and do not carry the TOU warning.

## PV, storage and optimization

The first DER path uses Tariff51 Option2, reduction in usage. Its ordinary
retail schedule remains in force for supplemental, backup and maintenance
power, with no credit for generation exceeding load. Tariff80 interconnection
approval is required. The model requires explicit confirmation of this
arrangement, sets export to zero and preserves curtailment. A QF purchase
agreement, excess-distributed-generation enrollment, legacy net metering and
special backup agreement cannot be substituted for Option2.

This first implementation conservatively limits aggregate PV nameplate plus
battery discharge capability to 40 kW. That is a model scope bound, not a new
utility eligibility rule. Standalone storage is not enabled. The default
representative home has a 3 kW synthetic peak, 5 kW DC/4 kW AC PV, and a
10 kWh/3 kW battery; the small office has a 10 kW synthetic peak, 10 kW DC/
8 kW AC PV, and a 30 kWh/8 kW battery. Neither is measured customer data.

One `charge_lines` expression supplies the numerical bill and optimization
objective, including exact filled decreasing blocks. The shared optimizer
retains historical perfect foresight within each cycle, physical battery
limits, terminal SOC, explicit grid-charging authorization and optional wear.
Grid-only, PV-only and PV-plus-battery comparisons use the same native load
and available PV inputs. Their representative OpenDSS replay remains separate
from retail billing and does not establish site-specific feasibility.

## Regional metadata

The account stores distribution utility, Indiana state jurisdiction and bundled
retail supplier separately from MISO metadata. The representative resource
adequacy zone is LRZ6; the transmission zone is DEI. That zone includes
Duke, IMPA and Wabash Valley transmission facilities and does not identify
the transmission owner serving a particular site. No wholesale pricing cpnode
is assumed. Bundled retail supply plus the filed RTO/TDSIC riders is not
augmented by a second MISO LMP, capacity/PLC or transmission-tag charge.
No CAISO carbon intensity is substituted for Indiana.

## Evidence, coverage gaps and verification

[Source manifest](utility_sources/duke_in/manifest.json) preserves original
URLs, PDF hashes, selected PDF pages and text hashes. The clean portion of the
February 7 compliance filing is used for rates; redline overprinting is not
parsed as arithmetic. The February 25 docket entry records Energy Division
review and interim approval, subject to refund. Later compliance filings and
rehearing orders require their own versioned evidence.
The intervening February 11 notice only redesignates confidential special
contracts; February 12 resubmits missing Attachment A revenue requirements.
Neither revises the ordinary public RS/CS base or rider sheets used here.

The verified service/billing-month intersection remains March 1–31, 2025. January–February
need the prior rate book and reset allocation. April onward needs superseding
FAC and other rider filings; July and September adjustments and temporary
credit expirations must not be ignored. The 2026 second-step rates and
generation cost tracker need separate source-backed history. Confirmed complete
regular 26–34-day cycles use the full schedule; partial initial/final service,
cycles outside that length bound, unsupported service/billing months and
rate-change crossings still reject. A partial calendar month can be a complete
confirmed meter cycle; it is not silently assigned daily-prorated charges.
Verified full-year studies remain unsupported. Explicitly accepted provisional
standard RS/CS full-year studies are enabled as described below.

The subsequent2025 source review preserved the prior RS/CS base prices and
verified starting components (FAC142, EE66, credits67 and load-control74),
plus later approved fuel factors and rider-continuity evidence. The exact
[component and gap ledger](utility_sources/duke_in/history2025-evidence-status.json)
keeps these observations separate from executable complete rates. Starting
class tables62/65/68/70/73, the signed FAC143 factor resolving an order sign
discrepancy, later ECR43/REP7 class factors and December67 treatment remain
missing. Individual component evidence does not authorize a full-year bill.

Focused verification covers independent itemized decimal arithmetic, block
boundaries, TOU boundaries, the tariff's holidays and observed dates, DST,
missing intervals, eligibility and export rejection, numerical/symbolic parity,
and dispatch/bill reconciliation. Shared browser/API/worker and historical
matrix evidence is reported separately after validation on a frozen candidate.
The initial focused launcher run passed 102 tests in 3.77 seconds of pytest
runtime (4.06 seconds for the phase), excluding native GUI tests. Its report
is `.cache/validation_duke_in_focused_20261024_a/report.json`; this is focused
development evidence, not a full-year or browser acceptance claim.
The subsequent historical-evidence/cycle-clock pass passed 109 tests in
3.37 seconds of pytest runtime (3.68 seconds for the phase), including complete
26-day cycles at full blocks/connection, bill-month mismatch/reset rejection,
and TOU-only source-conflict disclosure. Evidence is
`.cache/validation_duke_in_history_evidence_20261024/report.json`. No new complete
pricing window or full-year simulation is implied by this passing test run.

## Explicit provisional2025 studies

Select `rate_evidence_mode=provisional_2025` and set
`provisional_assumptions_accepted=true`. A truthy string or numeric value is
not acceptance. Existing saved studies with no evidence fields retain verified
mode and continue to reject the historical gaps. Account, non-export,
interconnection, taxable status, voltage and regular-cycle eligibility checks
are unchanged.

Each result records `rate_evidence_status`, `assumption_model`,
`rate_assumptions` and `objective_scope`. An assumption includes its identity,
dates, affected charges including tax, numerical values, explanation and
source references. Only assumptions used by that cycle appear. Merely
selecting provisional mode for an otherwise verified March cycle leaves its
bill and evidence status unchanged. Billing and dispatch share the same
assumed component expressions; their agreement establishes implementation
consistency rather than historical tariff accuracy.

The study model is `duke_indiana_2025_provisional_v1`:

| Identity and period | Explicit assumption |
| --- | --- |
| `DEI25-PRE-RESET-RIDERS`, Jan1–Feb26 service | Use old RS/CS base observations and recovered old60/66/67/74, with72zero. For missing62/65/68/70/73, backcast same-class March reset factors: RS .003339/.002259/-.000105/.000984/.000038; CS .003699/.001874/-.000073/.001010/.000028 USD/kWh. The reset moved costs between base and riders, so this proxy can misstate recovery; it is not an official pre-reset composite. |
| `DEI25-FAC143-SIGN`, Apr–Jun designated bills | Fuel -.004801 USD/kWh from .029577 minus .034378, consistent with the stated decrease and subsequent increase. The printed order result lacks its negative sign; a signed corrected final tariff is missing. |
| `DEI25-JULY-RIDER-CONTINUITY`, Jul–Dec designated bills | Hold missing62/73 at March same-class factors: RS .003339/.000038; CS .003699/.000028 USD/kWh. ECR43/REP7 approvals are known and later residential examples differ. These are held sensitivity values, not actual approved later factors. |
| `DEI25-DECEMBER-CREDIT67`, Dec designated bills | Hold September67 at RS -.013516/CS -.013232 USD/kWh despite unresolved temporary-credit expiration; the bill may overstate this credit. |
| `DEI25-ORDINARY-BASE-CONTINUITY`, May19–Dec31 service | Retain filed February27 ordinary base prices. The rehearing response discusses LLF/HLF amendments, but the final May package has not been recovered. |
| `DEI25-BILL-MONTH-ALLOCATION`, cycles spanning civil months | Apply the explicit final-service-day designated billing month's riders to the whole regular cycle. Retain one full monthly connection charge and block quantities; do not blend rider factors by day. Base-reset crossings still reject. This historical allocation is a study assumption. |

Known observations are retained instead of replacing them with proxies:

- Before reset, RS connection10.54 and energy .148799/.108297/.098147;
  CS connection10.70 and energy .140571/.130391/.118460/.096560.
  Prior fuel is +.005902 USD/kWh; old EE66 is RS .003851/CS .003882,
  credit67 RS -.007166/CS -.006399, and load-control74 RS .001406/CS .001446.
- Approved fuel is +.004042 for July–September designated bills and
  +.000372 for October–December. Base fuel is already included; it is never
  charged again. September credit67 uses the approved values in the table.
- Reset EE66/load-control74 continue through2025 because their next
  effective adjustment starts2026. The recovered TDSIC history likewise
  identifies the next recovery update in2026.

A reproducible hypothetical twelve-cycle2025 meter schedule can avoid the
unresolved February27 allocation: Jan1–Jan26 (26days), Jan27–Feb26 (31days),
Feb27–Mar31 (33days), then April–December calendar cycles. This covers every
2025 interval once with twelve complete regular cycles and twelve connection
charges. It is not a customer meter-reading schedule. Full-year TOU cannot
use it because no ordinary RS/CS TOU prices are supplied for January or early
February. A calendar-February cycle crossing the reset still rejects even
with provisional acceptance.

The independent [IURC updated2025 residential survey](https://secure.in.gov/iurc/files/2025-Electric-Residential-Bill-Survey-UPDATED.pdf)
reports157.98USD before tax for1000kWh on bills issuedJuly1. Its rounded
tracker table corroborates that later62/73 differ from March. Under our
explicitly held62/73 assumptions, the comparable1000kWh July model is
163.0677USD before tax: **5.0877USD higher**, about3.22%. This discrepancy is
preserved and tested; the model is not calibrated to force agreement. The
snapshot does not provide precise commercial class rates or a full quarterly
history. Provisional results are useful for exercising full-year accounting,
dispatch and electrical workflows and sensitivity analysis; they do not
establish the customer's actual2025 bill or savings.

[Versioned assumption ledger](utility_sources/duke_in/provisional2025-assumptions.json)
and source hashes preserve the distinction. Replacing a proxy with a recovered
filing requires a new evidence version and corresponding regression checks.

The provisional-mode focused run passed133 tests in4.18 seconds of pytest
runtime (4.48 seconds for the phase), with no GUI or live API tests. It covers
strict opt-in, recovered old bases/riders, fuel and credit boundaries,
cross-civil-month billing clocks, full-year twelve-cycle coverage, pre-inception
TOU and2026 rejection, numerical/symbolic agreement, unchanged verified March
bills and the preserved July benchmark discrepancy. Evidence is
`.cache/validation_duke_in_provisional_20261024_a/report.json`, engine
`1a246035b6823b9c85f172df9654a986567d34ddbe98719a6584f0bc3cb4373d`.
Full-year queued-worker/OpenDSS evidence is recorded separately by the shared
regional validation workflow; the focused test count alone does not claim it.
