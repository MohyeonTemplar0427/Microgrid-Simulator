# Dominion Energy North Carolina retail billing

This is the **North Carolina jurisdiction** of Virginia Electric and Power
Company, trading as Dominion Energy North Carolina. Virginia's schedules,
retail-choice rules, taxes and riders do not apply here. The billing adapter is
[`dominion_nc.py`](../src/billing/dominion_nc.py); its dated source evidence is
in [`utility_sources/dominion_nc/manifest.json`](utility_sources/dominion_nc/manifest.json).
Research cutoff: **October 15, 2026**. This cutoff is not a claimed expiration
of the utility's rates.

## Implemented ordinary schedules

All seven structures below use the same numerical and optimization charge
expressions. They include the ordinary taxable-account energy, demand,
customer, minimum/contract charges and applicable riders. Dollar values in
the result are utility charges; optional battery wear remains separate.

| Schedule | Customer and eligibility | Rate structure | DER and replay scope |
|---|---|---|---|
| 1 | Ordinary separately metered home, flat, apartment or qualifying family-care home; no motor over 15 HP or hotel/commercial use | $14.40 customer; seasonal flat energy | Approved non-export or enrolled renewable NEM; representative 120/240 V single-phase replay |
| 1P | Single-family/family-care home or eligible accessory meter; confirmed TOU enrollment and re-enrollment restrictions | Customer, seasonal on-peak 30-minute demand and on/off energy | Approved non-export or enrolled NEM; RECs retained |
| 1T | Same ordinary residential TOU eligibility | Customer and seasonal on/off energy; no demand charge | Approved non-export or enrolled NEM; NEM RECs assigned to utility |
| 5 | General nonresidential service; the sheet does **not** impose 5P's 500 kW ceiling | Demand-dependent energy-block widths, demand above 100 kW and seasonal demand-based minimum | Ordinary parallel generation is prohibited. Generic PV/storage unavailable; the <=20 kW NC GreenPower Solar+Schools exception requires a separate arrangement |
| 5P | Permanent nonresidential service below 500 kW; a >=500 kW measured cycle blocks this schedule for the following 12 cycles | Customer depends on phase/service amperes, on-peak supply demand, all-hours/contract distribution demand, TOU energy | Approved parallel contract or eligible NEM; <=100 kW NEM has the filed parallel-contract exception |
| 6P | Existing nonresidential customer not eligible for 5P; qualifying demand history required | On-peak/average supply-demand floor, >=500 kW distribution floor, primary/secondary prices, reactive-demand provision and TOU energy | Approved parallel contract or eligible NEM. Implemented dispatch requires explicit unity-PF/zero-kvar load; nonzero reactive demand is unavailable rather than omitted |
| 6L | Prior 6C/6P/10/6VP customer with >=3,000 kW in at least 3 of the 12 cycles immediately before enrollment; >=3 MW contract | All-days TOU, 75% prior-summer **on-peak** ratchet, 1 MW supply floor, evolving distribution contract; no distribution demand at >=69 kV | Billing/dispatch at the declared voltage; representative electrical replay is unavailable for primary/high-voltage service |

The shared browser reports electrical applicability separately from economic
validity. A supported primary-service bill does not imply a supported primary
OpenDSS circuit. See [representative electrical validation](Utility_Electrical_Validation.md).

The current account mode assumes unity power factor and zero reactive demand.
That is a declared modeling condition, not an inferred customer measurement.
An ordinary account with material reactive load requires interval kVA/kvar
measurements and a matching inverter-Q/control model before its costs can be
optimized accurately. It is rejected in this candidate. Transformer-side
metering, which has a filed 2% energy-charge discount, is also rejected pending
its complete charge-component treatment.

## Verified service dates and component changes

Complete composite coverage is **January 1, 2025–October 15, 2026**, bounded to
ordinary accounts and the declared operating conditions. Data are split into
source regimes; a current tariff is never substituted into a historical year.

| Date | Filed change and evidence |
|---|---|
| November 1, 2024 | Temporary base schedules, subject to refund, E-22 Sub 694; same numerical base prices as the final 2025 sheets, verified from the actual temporary filing |
| January 2025 | Temporary base plus the still-applicable 2024 riders, including the separate three-month negative A1 adjustment. These are not February 2025 prices |
| February 1, 2025 | Final base/applicability sheets, Sub 694; A/B/B1 fuel order Sub 712; C/CE order Sub 711; RP/RPE order Sub 710 |
| March 1, 2025 | Newly effective CCR rider, Sub 694. The January/February 2025 rider lists contain no CCR charge |
| February 1, 2026 | Updated A/B,C/CE,CCR,RP/RPE. The January 13, 2026 fuel order explicitly sets separate B1 to zero, recovering its balance through B |
| August 1, 2026 | First quarterly fuel adjustment introduces a **new** positive B1. June 26, 2026 filing Sub 753B uses the regulatory fee effective July 1, 2026 |

The fuel/base-fuel component already included in the base energy price is not
added again. Riders are additional charges or credits. The regulatory fee is
already reflected in the filed rider factors and is not a separate fabricated
customer charge. PJM LMP, capacity PLC and transmission NSPL are not added to
these bundled retail rates.

Per-kWh riders, in **cents/kWh**:

| Period/class | A | A1 | B | B1 | C | CE | CCR |
|---|---:|---:|---:|---:|---:|---:|
| January 2025 residential |0|−0.7298|0.1854|0.6297|0.1029|0.0288|0|
| January 2025 small general |0|−0.7291|0.1853|0.6108|0.1536|0.0251|0|
| January 2025 large general |0|−0.7258|0.1839|0.6295|0.1389|0.0227|0|
| February 2025–January 2026 residential |0|0|−0.7362|0|0.1520|0.0063|0 before March 1;0.1690 thereafter|
| February 2025–January 2026 small general |0|0|−0.7355|0|0.1559|0.0096|0 before March 1;0.1689 thereafter|
| February 2025–January 2026 large general |0|0|−0.7322|0|0.1217|0.0075|0 before March 1;0.1681 thereafter|
| February–July 2026 residential |0.5198|0|0.1023|0|0.1394|0.0133|0.1027|
| February–July 2026 small general |0.3000|0|0.0481|0|0.0618|0.0142|0.1026|
| February–July 2026 large general |0.1750|0|0.1432|0|0.0648|0.0149|0.1023|
| August–October 15, 2026 residential |0.5198|0|0.1023|0.5602|0.1394|0.0133|0.1027|
| August–October 15, 2026 small general |0.3000|0|0.0481|0.5593|0.0618|0.0142|0.1026|
| August–October 15, 2026 large general |0.1750|0|0.1432|0.5578|0.0648|0.0149|0.1023|

RP/RPE are **monthly dollars**, not cents/kWh. Ordinary residential/commercial
amounts are $0.55/$0.02 and $3.07/$0.11 in January 2025; $0.87/$0.70 and $4.82/$3.90
from February 2025 through January 2026; $0.84/−$0.26 and $4.70/−$1.49 from February 2026.
An explicitly confirmed auxiliary/CEPS-exempt account does not receive these
charges. No industrial exemption is automatically granted to a commercial site.

Ordinary North Carolina electric receipts are subject to **7% sales tax**.
Customer, energy, demand and rider charges enter that taxable subtotal once.
The [NCDOR electricity guidance](https://www.ncdor.gov/taxes-forms/sales-and-use-tax/taxable-items/electricity)
confirms this combined rate; the utility's dated bill-calculator worksheet also
records the 7% tax for the historical study period. Account-specific statutory
exemptions, construction/interconnection invoices, deposits, late fees and
voluntary purchases are separate account arrangements.

## Calendars, demand and actual meter cycles

Inputs are timezone-aware America/New_York interval-start averages at 15 or 30
minutes. Demand is an aligned 30-minute average, never the maximum 15-minute
reading or an estimate made from hourly values. Spring/fall DST retain their
actual physical intervals. Daily-rate factors count service dates; they do not
divide by an assumed 96 intervals per day.

For 1P/1T, summer TOU is 13:00–21:00 weekdays; winter is 06:30–12:00 and 17:00–21:00.
For 5P/6P, summer energy/demand is 10:00–22:00 weekdays. Winter **demand** is
06:00–12:00 and 17:00–22:00, while winter **energy** is 06:00–22:00.
Their holiday list is New Year's Day, Good Friday, observed Memorial Day,
July 4, Labor Day, Thanksgiving Thursday/Friday, Christmas Eve and Christmas Day.
No Friday/Monday substitution is invented for a fixed holiday on a weekend.
6L instead applies its on-peak hours **every day**, including weekends and
holidays: 10:00–22:00 summer, 07:00–22:00 winter.

Seasonal charge levels use the explicitly designated utility billing month;
clock masks use each service date. A meter-read date is not automatically the
billing month. This matters around May/June and September/October boundaries.

Monthly schedules 1/1P/1T/5/5P use a full monthly customer/demand charge for 26–40
service days and a days/30 allocation below 26 days, consistent with T&C X and
the utility worksheet. Schedules 6P/6L are explicit **30-day** rates and always
scale the specified customer/demand/minimum charges by days/30. The candidate
accepts confirmed monthly cycles of 1–40 service dates. Bimonthly cycles are
not silently divided into artificial months.

The official residential worksheet explicitly states that per-kWh rates are
prorated when a usage period crosses filing dates. The adapter uses a stated
calendar-day weighting of those per-kWh factors. A fixed RP/RPE change inside
a meter cycle is more limited: absent a bill/utility confirmation of the
allocation, a day-weighted study estimate is returned with
`is_complete_bill=False` and a warning. The account can supply
`fixed_rider_allocation_confirmed` and its evidence reference. This affects
calendar January/February 2025 and 2026 transitions, not ordinary calendar-month
benchmarks. The numerical estimate must not be described as a fully reconciled
actual invoice without that evidence.

## Solar, storage and annual state

T&C XXV provides renewable net metering for eligible customer-owned facilities
up to 1 MW AC, designed for the customer's use and approved for parallel
interconnection. The minimum agreement is one year. Non-TOU excess energy
carries as kWh. TOU energy has separate on/off-peak kWh banks: on-peak surplus
may cover off-peak purchases; off-peak surplus cannot cover on-peak purchases.
Customer, demand and other non-energy charges remain payable. Remaining kWh
credits are forfeited at the beginning of the summer billing season; this is
**not** a cash purchase or avoided-cost payout. No cash value is invented.

Schedules 1P/5P/6P retain RECs. Other schedules require assignment of RECs to
Dominion under XXV.E; that confirmation is explicit. Production incentives and
REC sales are excluded from bill savings.

For solar plus storage, the bounded NEM path permits PV-origin charging only
and prohibits battery export. Approval of a generic renewable generator does
not establish eligibility for grid-charged battery exports. Non-export storage
can grid-charge only under an explicitly confirmed operating contract. Excess
PV is visibly curtailed. Schedule 5's ordinary parallel-operation prohibition
is enforced for both PV and storage.

Initial enrollment/contract facts are fixed across scenario comparisons.
Actual simulated monthly demand peaks, kWh histories, on-peak peaks, contract
increases and credit balances propagate through the shared annual workflow.
6L's enrollment-qualifying twelve-cycle history is distinct from its rolling
eleven-cycle summer ratchet. An old all-hours peak is not a summer on-peak peak.
5P/6P eligibility checks use the evolving history and reject a required
reclassification rather than maintaining frozen eligibility after the evidence
ceases to qualify.

The default objective excludes inherited credits, retaining the user's chosen
accounting policy. Actual carried credits still reduce the cash bill and
produce the next actual ledger. Newly generated exports use the applicable
netting rules. An advanced explicit-cash-bill objective is separately named.
Rolling-cycle perfect foresight is not a jointly optimized annual optimum.

## Validation and remaining historical research

Offline validation:

```sh
/usr/local/bin/python3 -m pytest -q test/test_dominion_nc.py
```

Independent August 2026 arithmetic benchmarks:

| Case | Before tax | With 7% tax |
|---|---:|---:|
| Schedule 1,744 kWh,31 days, ordinary residential |$116.09704|$124.2238328|
| Schedule 5P,30 kW constant,22,320 kWh,100 kW existing distribution contract, three-phase service |$2,086.84756|$2,232.9268892|

The tests independently calculate these amounts from filed literals, check all
seven structures numerically over the complete 2025 calendar, and compare
numeric charges with the shared convex/MILP expressions. Other tests cover
dynamic Schedule 5 blocks/minimum, actual 30-minute peaks, historical versions,
holiday boundaries, DST, proration, summer credit reset, one-way TOU-bank
transfer, contract/history continuity, eligibility failures, and unsupported
reactive/parallel cases. These are synthetic deterministic meter fixtures,
not measured customer bills or historical-weather acceptance evidence.

The research target is ten historical calendar years 2016–2025, plus current 2026
coverage, bounded by plan inception. **Complete executable composite coverage
before 2025 remains unavailable.** The official docket inventory records
identified annual fuel/DSM/REPS proceedings from 2018 onward, the 2019 general
rate case Sub 562, and 2024–2026 source filings. The old tariff comparison sheets
and identified orders are evidence for further research, not permission to
extrapolate all required 2016–2024 component versions. Specifically:

| Historical range | Remaining requirement |
|---|---|
|2016–2018|Complete base, fuel, DSM, REPS, tax/rule versions and account eligibility; the public summary archive does not provide a complete filed-sheet set|
|2019–2023|Reconstruct Sub 562 base-rate transitions and each year's independent fuel/DSM/REPS dates, grandfathering and proration|
|2024|Pre-November base components and all in-year rider/rule changes; November/December temporary base evidence is retained but the executable coverage has not been broadened beyond the validated 2025 start|
|2025|All ordinary calendar-month composites verified; fixed-rider allocations for a real cycle straddling February 1 need invoice/utility confirmation|
|2026 through October 15|All ordinary dated components verified, including new August B1; future-effective/pending changes are unavailable|

Special schedules remain identified but disabled: 1DF,1E,1W,SGS-EV,5C,6C,6VP,
7,10,LGS-RTP,NS,SG,19-FP,19-LMP,26,30,30T and 42. Their catalog entries state
the required contract, meter topology, utility event/classification history,
or qualifying-customer information. A listed disabled schedule is not a claim
of billing or optimization coverage. Third-party retail supply and separate
PJM wholesale settlement are not supported by this bundled adapter.
