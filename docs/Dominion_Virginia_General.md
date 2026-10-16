# Dominion Energy Virginia general billing

Research date: October 15, 2026. Implementation: `src/billing/dominion_va_general.py`.
This extends the existing Dominion work; both general and legacy GS-2T use
`src/billing/dominion.py::gs2t_base_lines` for the same base-rate arithmetic.
The schema-8 historical candidate and its immutable saved results are separate.

## Verified executable coverage

All fifteen ordinary structures have dated executable coverage from
**January 1–October 15, 2026**, including actual predecessor components.
This is the verified research window, not a plan's inception or expiration.
Base rates, recurring riders, deferred fuel and taxes retain their independently
filed effective dates; a September composite is not extended backward.
Schedule 1 and GS-1 also have a separate **January–December 2025 verified-charge
subtotal** path. Historical taxes without a retained dated original are named
exclusions, so these are explicitly incomplete bills. The 2025 path does not
extend 2026 solar rules backward. The separate 2026 reconstruction described
below closes the former January–August gap.

| Plan | Account class and principal requirements | Implemented charge structure |
|---|---|---|
|1|Ordinary individually metered residential use|800-kWh distribution/generation blocks; utility-designated billing month selects generation season|
|1G|Residential AMI; no PJM/company demand-response enrollment; TOU reenrollment restriction|Three TOU buckets; May–September and October–April service-date seasons|
|1S|Residential demand TOU; TOU reenrollment restriction|30-minute on-peak distribution/generation demand; two TOU energy buckets|
|1T|Residential energy TOU; TOU reenrollment restriction|Two TOU energy buckets; ordinary import/non-export service only|
|GS-1|No more than two >=30-kW qualifying peaks in current/prior eleven billing cycles|1400-kWh blocks; phase-specific customer charge; contractual and measured-demand minimums; parallel-service shortfall charge|
|GS-2|At least three >=30-kW and at most two >=500-kW qualifying peaks|200-kWh/kW non-demand/demand branch; declining hours-use generation blocks; contractual minimums and parallel distribution demand|
|GS-2T|Voluntary bundled intermediate service with GS-2 demand eligibility|On-peak supply demand; 12-cycle distribution ratchet; approved parallel-service contract; weekday TOU energy|
|GS-3|Secondary large service; at least three >=500-kW qualifying peaks|12-cycle distribution ratchet; 75% prior-summer on-peak ratchet; off-peak demand above 90% of billed on-peak; reactive demand|
|GS-4 primary|Utility-confirmed primary classification; large-service demand eligibility|Primary-service tiered distribution demand; on/off-peak supply and reactive demand; ratchets|
|GS-4 transmission|Normal delivery>=69kV; large-service demand eligibility|Transmission-service rates; no distribution demand charge; supply/reactive demand and ratchets|
|10 secondary / primary / transmission|Existing qualified large-service account; no demand-response enrollment; sourced daily classifications; explicit unity-meter-PF model|A/B/C variable daily energy; all-hours supply peak; distribution ratchet; voltage-specific riders|
|5C|Sanctuary meter of a qualifying church or synagogue; no parallel operation|3000-kWh distribution/generation blocks|
|5P|Qualifying worship or charitable institution; no parallel operation|On-peak demand and TOU energy with its own holiday exclusion|

The plan catalog records executable billing/dispatch capability separately from
unsupported schedules. A browser entry alone is not validation evidence.
Secondary circuit replay applicability is independent of retail eligibility;
primary/transmission bills must never be forced onto a secondary reference
circuit. The main workflow owns execution, scenario equipment and saved results.

### Account facts

Utility, Virginia jurisdiction, retail supplier, actual tariff and PJM zone/node
remain separate configuration facts. No ZIP/state/PJM node infers the utility.
Bundled capacity recovery is in generation charges/riders. Base transmission and
Rider T1 recover transmission. No LMP, capacity PLC, NSPL or auction charge is added.

The implementation requires an explicit utility-designated billing month,
phase/voltage/metering classification, confirmed ordinary eligibility, approved
parallel-service status where equipment is installed, contract minimums and
minimum-demand floor. Existing commercial service requires eleven ordered prior
billing-cycle all-hours/on-peak demand records and their billing-month numbers.
GS-3/4 require an explicit current reactive-demand input; scalar power factor does
not establish a real customer's reactive peak. A reference case may declare a
synthetic constant-power-factor reactive profile, clearly labeled as an assumption.

Historical measured peaks and an existing parallel contract remain the same for
all initial counterfactuals. `next_state` returns actual current peaks and the
updated contractual demand for the next billing cycle. Summer ratchets store
**measured on-peak demand**, not an already-ratcheted billable demand. The current
orchestrator must propagate this state; monthly resets are not an annual optimum.
The adapter validates propagated history and rejects unsupported tariff
reclassification rather than continuing from frozen original eligibility.
Initial qualification and continued existing service are distinct: GS-2/2T
retain a confirmed enrolled account while any qualifying 30-kW historical peak
remains, and GS-3/4 retain an enrolled account while any qualifying 500-kW peak
remains. Losing the third qualifying peak therefore does not automatically
reclassify an existing account. The explicit existing-enrollment confirmation
must remain the same in every counterfactual. All-low history or upward
reclassification requires utility-confirmed transfer/grace-period treatment;
the adapter does not invent the transfer date or extend a grace period.

Minimum-demand floors must include the utility-established transformer/contract
provisions. Low-power-factor minimums, supplier contracts, voluntary rider
exemptions, facilities charges and 25 MW large-load arrangements are not silently
omitted: those combinations require their own verified inputs/adapter.

### Billing cycles, intervals and calendars

Demand uses aligned 30-minute average imports. Complete 15-minute data can be
averaged in adjacent pairs; 30-minute data are native. Hourly demand reconstruction,
naive timestamps, duplicates, gaps and incomplete averaging blocks reject.
Eastern timestamps retain physical UTC order across DST.

These are confirmed meter cycles, not fragments of a larger unknown bill.
GS-2/2T/3/4 and Schedule 10 use the filed 30-day proration of fixed/demand/appropriate
demand-relative blocks. Monthly Rate plans use full charges and block sizes for
normal 26–40-day cycles. Under T&C X.B, outside that range fixed charges, demand
charges and finite kWh blocks use days/30; this includes GS-1 parallel/minimum
charges and 1S/5P demand charges. Short cycles require an explicit complete
initial/final cycle and source; an arbitrary study fragment is not a utility bill.
Extended 41–45-day cycles require their documented cycle/source. Bimonthly
metering is unavailable without its own explicit treatment.

The official bill worksheet supplies the 30-day denominator and separately keeps
actual consumption-tax thresholds at 2,500/50,000 kWh. Unused worksheet helper
formulas are not treated as operative tax rules. Local tax follows its filed
monthly formula; it is not blindly multiplied by the energy-proration factor.

Residential 1G/1S/1T and 5P exclude New Year's Day, Memorial Day, Independence Day,
Labor Day, Thanksgiving and Christmas. The filed VA schedules do not specify
Friday/Monday substitutions for weekend fixed-date holidays; no such extra
weekday is invented. GS-2T/GS-3/GS-4 specify weekdays with **no holiday exclusion**.
NC and PG&E calendars must not be reused indiscriminately.

### Recurring charges and taxes

Individual lines retain riders A, C1A, C4A, CCR, CE, CERC, DIST, RBB, E, GEN, OSW, PIPP, RGGI, RPS,
SMR, SNA and T1, including explicit zero rates. Conditional GS-2/2T riders use actual
meter load factor at the filed 50% boundary. They must not use native building
energy or available PV. Fuel cost and deferred fuel cost are distinct.

**Deferred Fuel Cost Charge** is 0.2901 cents/kWh from August 1, 2026 and applies to
ordinary nonexempt retail accounts in addition to Rider A. It was omitted in the
older bounded GS-2T candidate; new general bills include it. An HB 1770-exempt
customer instead needs its specific pro-rata fuel-deferral treatment.

The statewide consumption-tax tiers effective for meter readings on/after
August 16, 2025 are 0.001565/0.001055/0.000845 USD/kWh, split at 2,500 and 50,000 kWh.
The state/regulatory/local consumption-tax components are counted once. A separate
effective-dated sales/use-tax surcharge is included: residential $0.000921/kWh,
GS-1 $0.000847, GS-2/2T $0.000712, GS-3 $0.000541, GS-4 $0.000440 and
5C/5P $0.000917. It also remains outside base-tariff minimum offsets.
Henrico's additional utility-consumer tax is residential 0.70 + 0.007537 USD/kWh,
maximum 1.00 USD/month, and commercial 1.15 + 0.00713 USD/kWh, maximum 10.00 USD/month.
A different/unverified locality produces an explicitly **incomplete** bill with
the unknown local utility-consumer tax excluded. It does not assume zero tax or
mislabel the site Henrico. Non-bypassable deferred fuel and taxes remain outside
base-tariff minimum-charge offsets.

## Solar and unsupported arrangements

Approved **non-export** PV and storage remain available where the tariff allows
parallel operation. Surplus is explicitly curtailed. The parallel-service
contract is not inferred from inverter power, and it is not removed from the
grid-only counterfactual. 5C/5P expressly exclude parallel operation.

The official current net-metering rules have been retained as research evidence:

- Ordinary compatible plans are 1, 1G, 1S, GS-1, GS-2, GS-2T, GS-3 and GS-4;
 1T is not a net-metering-compatible energy-only TOU plan.
- Residential generation limit 25 kW, nonresidential 3 MW; installation sizing is
 subject to the utility-approved 150% annual-consumption rule and interconnection.
- Residential standby provisions apply above 20 kW AC in the July 1, 2026
  1/1G/1S sheets; January–June 2026 and older 2025 sheets use 15 kW.
  The vintage must not be silently changed.
- Monthly credits are kWh, carried by the same TOU tier. At the annual boundary,
 carried credits are limited to the current year's billed consumption, excluding
 previous-year credits applied. The net-metering year follows the account's
 first post-interconnection meter reading, not necessarily January–December.
- Without a prearranged PPA there is no annual cash payment. The optional PPA
 uses the published prior-calendar-year DOMZONE day-ahead simple-average LMP,
 not Western Hub, realtime LMP or a current hourly export price. RECs and
 production incentives are separate from bill savings.

**Executable NEM scope:** residential 1, 1G and 1S, under the current February 5,
2026 terms, with service beginning on/after that date and approved aggregate
renewable capacity at or below 15 kW AC before July 1, or 20 kW thereafter, no PPA,
and confirmed utility-approved sizing/PTO. Meter imports and exports net by the
same TOU tier. Credits are kWh, not dollar payments; unused credits have no
assumed terminal cash value. A dated, sourced opening bank or explicitly
hypothetical zero ledger is mandatory. The next-cycle ledger preserves its exact
service-date boundary. Prior credits reduce the reported bill; default dispatch
excludes inherited banks while still valuing current-cycle export offsets.

State consumption tax and local utility tax use **current net delivered kWh**,
not gross purchases and not the reduced amount after inherited bank use. This
comes from Virginia Code §§58.1-2900 C and 58.1-3814 F2. Other billed energy
components use the properly netted/credited kWh. Demand charges continue to use
actual meter demand. The independent tests distinguish these volumes.

The February 16, 2026 DER manual §2.5 and Blue Book §770.5 require approved
storage restrictions. The implemented conservative operating branch uses only
renewable charging and prohibits battery backfeed. The shared dispatcher owns
those physical-origin constraints; a favorable retail price does not authorize
grid-charged NEM exports.

Explicit unavailable NEM branches are annual boundaries (bank origins/carry cap
and PPA settlement), capacity above the dated 15/20-kW threshold (standby
rounding/riders), a NEM cycle crossing changed component prices or a 1G cycle
crossing its seasonal-price boundary (credit allocation between versions),
and commercial load-factor/minimum/reactive-demand interactions. Their known
rules are not presented as executable annual settlement. 1T and 5C/5P are not
made NEM-eligible by this residential adapter.

### Schedule 10 daily classifications and power-factor scope

The official public calendar at `dominionenergy.com/schedule10` exposes its
historical `api/sched10` data. The retained evidence covers every day from
January 1, 2017 through October 15, 2026: 3,575 classifications from 118 monthly
responses, each with its source URL/hash. Unix milliseconds represent local
Eastern midnight and are converted before selecting the date. Some API responses
have `Year=0`; it is not used as the requested calendar year.

Current runtime classifications live in `src/billing/dominion_va_calendar_data.py`.
A/B/C categories apply to actual dates, including weekends and holidays. A missing
retrieval never defaults to C; the filed C default requires evidence that the
utility failed to announce the day by its deadline. Calendar availability does
not establish historical tariff coverage.

Schedule 10 bills max(measured kW, 85% of maximum kVA) supply demand. Its current
executable optimization scope requires an explicit unity-meter-power-factor
model, so that this equals measured kW. Nonunity-PF cases require interval
reactive/apparent-power optimization and reject; a frozen kVA value is not allowed
to underprice battery counterfactuals. Primary/transmission economic results do
not acquire a secondary-circuit validation claim.

Other explicitly unavailable structures include closed 1P/5/6/7/1EV/EV, experimental
DP-R/DP-1/DP-2 critical-period tariffs, GS-3EV enrollment, separately metered 1W
water heating (utility control in fixed EST), approved thermal-storage program
6TS, special 8/MBR/SCR contracts, and future GS-5/high-load rules. The catalog also
identifies utility-owned charging/fleet/session services, qualifying-facility
purchases, experimental renewable/REC arrangements, outdoor lighting, and
shared/multifamily solar subscription accounting separately. Their precise blockers are in the catalog. Retail-choice
law is date-sensitive; no third-party supply is priced without a complete valid
contract and verified eligibility.

## Historical research and evidence

The rolling research target is 2017–2026, bounded by actual plan inception.
This is a research target, not implemented ten-year coverage.

| Period | Evidence retained | Remaining composite gap |
|---|---|---|
|2017–2024|Complete official Schedule 10 daily calendars; actual 2024 SCC base/rider/deferral filings retained|Complete dated composite chains before 2025 are not reconstructed; no executable claim|
|2025|Schedule 1/GS-1 base, supply, delivery, every applicable ordinary recurring rider and deferred fuel normalized from actual filings; complete daily calendar retained|Executable verified-charge subtotals for 1/GS-1, with missing dated sales/use/local tax and pre-August16 consumption-tax originals named explicitly; other schedules lack executable historical adapters|
|Jan–Aug2026|Actual predecessor components normalized for all fifteen structures, including corrected January base filing and clean archived July T1 revision|Executable ordinary bundled coverage; no missing base/rider original remains in this window. Cross-rate demand cycles require confirmed allocation; NEM has separate dated restrictions|
|Sep1–Oct15,2026|All current base/rider/fuel-deferral components verified and archived|None for declared ordinary Henrico bundled non-export account scope|
|Future dates|Some actual filings have later limits/large-load rules|Research date is a verification bound; future rules unavailable before their filed effective date|

Official PDF originals are kept in ignored research cache, while complete selected
page text and hash manifests are retained in
`docs/utility_sources/dominion/va_general_2026` and `va_history_research`.
The current source downloaded October 15 matches the previously archived
October 11 PDF byte-for-byte (TOC revised October 1). Sitecore `?rev=` parameters
can return current content even when an old revision identifier is requested;
such a URL alone is not historical verification. An archival availability lookup returned a nominal September 2025 worksheet
capture, but its actual contents were updated May 29, 2026. It was rejected as
2025 evidence; an archive timestamp does not establish the dates of its bytes. Search-index snippets can also retain
2025 rates while the live official PDF has been replaced by a 2026 filing; snippets
alone are not enabled as historical evidence.

The official SCC public case and document indexes exposed the actual filings:
`DocketSearchAPI/breeze/CASES_ESTABDATE/GetCasesEstDateByParticipant` and
`CaseDetails/GetDocuments`. The retained `approved_2024_2025/manifest.json`
records the document identifiers, filing descriptions, source URLs, PDF hashes
and complete extracted text for 64 retrieved packages. The separate indexed
April 2026 CE document returning 404 is not required by the enabled 2025 chain.
These packages are source evidence, not an executable rate
table; a filing must still be checked against its approval, clean tariff pages,
withdrawals and effective dates. Proposed exhibits and redlines are not treated
as approved prices. The historical Schedule 1T source is present in the public
compliance packages even though its separate utility mirror returned 404.
The separate 2017–2025 case inventory identifies 156 relevant historical dockets;
docket creation dates are not tariff effective dates or proof of rate coverage.

### Executable 2025 Schedule 1 and GS-1

`dominion_va_historical_data.py` preserves independent component versions and SCC
document identifiers, pages, source URLs and original PDF hashes.
`dominion_va_historical.py` supplies the same numerical/optimization expressions.
The original base sheets retain their January 1, 2025 effective dates; 2026 base
prices and parallel-service coefficients are not borrowed.
The normalized source table contains 26 components and 67 dated rows. It separates
coverage segments from filed action dates, so a component not yet introduced is
identified as such rather than presented as a January 1 zero-rate filing.

| Effective date | Verified ordinary-account transition |
|---|---|
|February 1|Deferred fuel changes from 0.3371 to 0.3449 cents/kWh|
|April 1|B/BW/GV/US2/US3/US4 withdraw; GEN begins. The GS-3EV compliance filing reissues other ordinary rider rows without changing their existing-account prices|
|May 1|CE and RBB rates change|
|June 1|GT and U withdraw; DIST begins; RBB remains separate during 2025|
|July 1|Fuel Rider A changes from 2.0735 to 2.9680 cents/kWh|
|August 1|Deferred fuel changes to 0.2906 cents/kWh|
|September 1|C1A/C4A, OSW, RPS, SNA and T1 change; C2A withdraws; SMR begins|
|November 1|Environmental Rider E changes|

The missing April reissues were found in SCC document **378662**, case
PUR-2024-00157, filed March 4, 2025. Its 71 pages include the actual clean/redline
ordinary riders and corresponding prior-version dates. This is independent of
the GEN consolidation filing, document 378661. Both are retained completely.
The rendered GEN clean-sheet footer on page 4 reads April 1, 2025; its embedded
OCR misreads the first `04` as `01`. The normalized effective date follows the
actual printed page, corroborated by the April withdrawal sheets, without
editing the retained original text extraction.

Component changes apply to their actual local service intervals, including a
meter cycle crossing the effective date. Fixed fees, finite energy blocks,
utility-designated generation season, confirmed initial/final proration and
GS-1 minimum/parallel terms apply at the whole meter-cycle level. GS-1's 2025
minimum supplement, demand minimum and parallel shortfall use respectively
1.866, 3.88 and 5.875 USD/kW, versus their different 2026 values. Demand history
and existing parallel-contract demand propagate between cycles.

The historical subtotal always excludes the unverified 2025 sales/use surcharge
and locality utility-consumer tax. Consumption tax is included when the final
service day is on/after August 16, 2025, because the retained filed sheet explicitly
establishes its applicable meter-reading version from that date; earlier cycles
exclude the missing old tax version. These missing components are not zero rates.
Both billing and dispatch return the exclusions and `is_complete_bill=False`.
Dispatch minimizes the **verified charges subtotal**; the result is not a proof
of the complete utility-bill optimum while decision-dependent taxes are missing.
Historical NEM/standby settlement remains unavailable without its applicable
vintage, rather than using the current February 2026 terms.

Important identified transitions include GEN replacing multiple generation
riders in April 2025, DIST replacing GT/U in June 2025, July fuel changes,
February/August deferred-fuel trueups, September DSM/transmission/OSW/RPS/SNA
changes and November environmental adjustments. A constant 2025 rider sum would
therefore be incorrect. An unverified local-tax component can be reported as
excluded, but the model must not label an unverified supply or delivery sum a
complete historical bill.

### Executable January–October 2026 component chain

`dominion_va_2026_data.py` contains predecessor rates with their actual source
identifiers and hashes. `dominion_va_2026.py` selects the effective versions;
the authoritative general calculator and optimizer share these selectors.
The normalized source CSV records 19 components with 35 dated rows, expanding
energy/demand coefficients into separate unit-labeled records.

| Effective date | Verified ordinary-account change |
|---|---|
|January 1|2026 base schedules, CCR and sales/use surcharge apply. Existing 2025 rider versions and August 2025 deferred fuel continue until their actual successors|
|February 1|Deferred fuel changes from 0.2906 to 0.2900 cents/kWh|
|March 1|CERC begins. Its originally filed January 1 rate was suspended December 16, 2025 and **never implemented**|
|April 1|GEN changes|
|May 1|CE changes|
|June 1|DIST changes and RBB withdraws; the separate January–May RBB charge is not omitted or double counted|
|July 1|Fuel Rider A changes. Residential standby thresholds and the T1 footnote change from above 15 kW to above 20 kW; ordinary base and T1 monetary coefficients are verified unchanged|
|August 1|Deferred fuel changes to 0.2901 cents/kWh|
|September 1|C1A, C4A, OSW, RPS, SMR, SNA and T1 change|

January base sheets are in SCC document 385680, filed December 9, 2025.
Schedule 10 uses the **replacement** filed December 18, document 385824, rather
than the superseded version inside the earlier package. CERC's actual March
sheet, document 386988 page 5, explicitly records the suspended January filing;
page 2 gives the suspension/reinstatement narrative. Its page 4 is only a divider.
The February/August deferred-fuel originals are pages 30/40 of documents
385769/389882, accompanied by the filed updated tables of contents.

The exact July T1 sheet was recovered from the official utility CDN's
[July 19 archive](https://web.archive.org/web/20260719064330id_/https://cdn-dominionenergy-prd-001.azureedge.net/-/media/content/rates-and-tariffs/pdfs/virginia/shared/rider-t1.pdf).
It is filed June 18, effective July 1, superseding September 1, 2025; its complete
page and provenance are retained as `t1_2026_07_01.txt` and
`t1_2026_07_01_source.json`. PDF SHA-256 is
`d95972e31c015c58983634cbad1cfbf41298dccfbf7bca64f0a6e7bdd2f76651`;
the retrieved bytes also match the archive's CDX SHA-1. This is an actual original,
not a cached search excerpt or an assumed continuation.

Energy riders use each interval's actual service-date price and meter purchases.
The utility's worksheet explicitly documents energy-rate proration, but does not
establish a universal demand allocation when a meter cycle crosses rates. Such a
cycle therefore requires `demand_rate_change_allocation` set explicitly to
`calendar_day_prorated_cycle_peak` and a nonempty `demand_rate_change_source`
confirming this account's allocation. It applies calendar-day weighted rates to
the measured whole-cycle demand; it does not substitute separate segment peaks
or use 23-hour DST days as fractional billing days. Without that evidence the
cycle rejects. Whole-calendar-month fixtures do not need this extra confirmation.
Monthly NEM cycles crossing changed prices reject because allocating netted kWh
and inherited credits between versions has not been verified.

All 2026 ordinary statewide taxes have actual applicable sheets; the missing
2025 tax originals do not block 2026. Henrico remains the supported complete
local-tax scope; other localities still carry their explicit exclusion.
The indexed April 2026 CE PDF returning 404 does not block this chain: the
current complete filed tariff retains the actual May 1 CE clean sheet.

## Verification

`test/test_dominion_va_general.py` contains independent filed arithmetic for each
implemented structure, energy/tax thresholds, ordinary/holiday/TOU boundaries,
30-minute averaging from 15-minute data, actual noncalendar cycles, documented short/extended proration and fragment rejections, historical gaps,
ratchet-state propagation, missing eligibility,
unknown-locality completeness and evidence hashes. It also solves each supported
structure as a fixed-schedule exact MILP and reconciles its objective to the
numeric calculator. Independent NEM tests cover netting, tier separation,
current-net taxes versus opening credits, monthly ledger continuation, and
objective policy. Schedule 10 tests verify the official daily calendar and its
complete voltage-specific bill arithmetic. This proves tariff-expression agreement; it is not a battery
savings validation or a site electrical check.

`test/test_dominion_va_historical.py` independently reconciles twelve 2025 monthly
benchmarks for each of Schedule 1 and GS-1, their applicable energy blocks,
every dated rider transition, noncalendar periods spanning rate changes,
initial-period proration, DST and the 2025 parallel-service coefficients. It also
checks exact-MILP/numeric agreement, propagated annual history, provenance hashes,
strict missing-version rejection and the explicit incomplete-tax flags.
The retained `historical_2025_independent_benchmarks.json` records the calculation:
constant 1 kW residential imports total 8,760 kWh and $1,338.809717 in verified
annual charges; constant 10 kW GS-1 imports total 87,600 kWh and $10,255.789940.
These are flat-load arithmetic benchmarks, not weather-driven facility studies,
observed bills or complete historical utility bills.

`test/test_dominion_va_2026.py` independently calculates every structure's
January whole bill, reconciles their exact-MILP expressions, exercises every
structure in January–September and a confirmed final October cycle, and tests
all component transitions, actual noncalendar energy allocation, confirmed
demand-rate allocation through DST, July T1 provenance, the suspended CERC
filing, missing-version rejection and dated NEM limits. Earlier saved studies
remain attached to their original immutable engine and coverage.
The retained `historical_2026_independent_benchmarks.json` records all fifteen
January whole-bill fixtures; examples are Schedule 1 at 744 kWh / $132.785592,
GS-1 at 7,440 kWh / $970.853120, and GS-2T at 66,960 kWh / $6,034.206640.
They have different hypothetical account sizes and are not a tariff-ranking
study. `source_normalization_audit_20261016.json` records the final source/code
hashes, source checks and the 431-passing-test focused verification.

The equivalent cumulative-block expressions share the first energy block and
prune selector branches ruled out by proven physical energy bounds. Repeated
numeric history peaks collapse before demand selection, and the already-billed
distribution maximum supplies the next parallel-contract state. These reductions
preserve tariff economics; an offline regression verifies that unreachable tax
tiers do not introduce binary variables.

```sh
/usr/local/bin/python3 -m pytest -q test/test_dominion.py test/test_dominion_va_general.py test/test_dominion_va_historical.py test/test_dominion_va_2026.py
```

The conditional 50% load-factor and 200-kWh/kW regimes are discontinuous at some
filed boundaries. Numeric billing has the specified inclusive/exclusive rule;
optimization must verify selected branches against the numeric bill, handle its
comparison tolerance explicitly, and never claim a globally proven minimum from
an ambiguous cheaper branch.

Official sources:
[Residential catalog](https://www.dominionenergy.com/virginia/rates-and-tariffs/residential-rates),
[Business catalog](https://www.dominionenergy.com/virginia/rates-and-tariffs/business-rates),
[Entire filed tariff](https://www.dominionenergy.com/-/media/content/rates-and-tariffs/pdfs/virginia/shared/entire-filed-tariff.pdf),
[Net-metering terms](https://www.dominionenergy.com/-/media/content/rates-and-tariffs/pdfs/virginia/terms-conditions/vatc25ra.pdf),
[20VAC5-315-50](https://law.lis.virginia.gov/admincode/title20/agency5/chapter315/section50/),
[Henrico tax schedule](https://henrico.gov/finance/approved-tax-rates-and-schedule/).
