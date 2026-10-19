# PECO billing-cycle evidence review

Reviewed October 19, 2026. **Exact non-DSIC rate-change allocation and
partial-period rules remain unverified.** Verified-only mode still rejects
them. Following separate user authorization, an opt-in
[provisional allocation model](PECO_Provisional_Allocation.md) now estimates
1–45-day cycles and applicable rate crossings with explicit assumption ledgers.
It does not extend the verified price window. Earlier validation reports remain
evidence for their original engine, not this candidate.

## Findings

The [October 2026 electric tariff](https://www.peco.com/cdn/assets/v3/assets/blt1b5616c79bacadb4/bltc70b88d49d2a1491/6abbe397d463362a37c0f102/Current_Electric_tariff_eff_Oct_1_2026_(003).pdf?branch=prod_alias)
and earlier2025/2026 books are retained in the existing
[source manifest](utility_sources/peco/manifest.json), with selected text,
source/PDF hashes and page numbers. The relevant clauses are:

| Rule | Verified statement | Supported application / remaining question |
|---|---|---|
|1.3, sheet10 | Rates and riders apply with the first scheduled billing cycle after the effective date unless otherwise specified. | This clause was missing from the earlier review. The exact scheduled-cycle anchor and component exceptions still need to be established; a delayed issue date cannot simply be substituted. |
| Definition of month, printed sheet7 | A month can mean one-twelfth of a year or the approximately monthly meter-reading period. | Does not specify an exact short-period denominator. |
|14.7, sheet25 | Monthly metering follows the designated reading schedule; only periods under 26 or over 35 days require proration. Monthly usage is not adjusted for seasonality. | Complete26–35-day regular, initial and final cycles receive one monthly charge. Do not normalize measured kWh to 30 days. |
|17.1, sheet27 | Monthly rate values are adjusted for substantially shorter/longer reading periods. | The clause does not state which exact denominator/factor to apply to fixed charges, demand charges, minimum demand or the GS 1100-kWh rule. |
|GSA, sheets37–39 | Class1/2 standard and TOU prices update on the specified dates and are described as not prorated. TOU charges use interval-metered usage. | Neither phrase alone establishes which price applies to an entire crossing cycle. Do not infer day weighting or a bill/read/start-date selection. |
|DSIC, sheet50 | DSIC is billed on a bills-rendered basis and applies to distribution plus STAS. | Use the bill-date percentage on the whole distribution subtotal, preserving one GS cycle demand. This already supports DSIC-only crossings. |

The corresponding clauses were checked in the January 2025 and2026 books;
compilation dates are not substituted for individual sheet effective dates.
Gas tariffs, other utilities' proration rules, PJM wholesale settlement rules
and online customer comments are not evidence for PECO electric allocation.

The original [December 18, 2024 compliance filing](https://www.puc.pa.gov/pcdocs/1859907.pdf)
states that the new tariff applies to service on/after January 1, 2025. It
includes the same general billing clauses, but does not supply a complete
component-level allocation calculation. The [June 2025 GSA filing](https://www.puc.pa.gov/pcdocs/1892976.pdf)
retains the non-proration language. The [December 12, 2024 order](https://www.puc.pa.gov/pcdocs/1859385.pdf)
does not resolve the missing formulas. These filings were inspected through
the official [base-rate docket](https://www.puc.pa.gov/docket/R-2024-3046931)
and [default-service docket](https://www.puc.pa.gov/docket/P-2024-3046008).
Finding no formula in these documents is a research limitation, not a claim
that PECO has no operational billing rule.

[52 Pa. Code 56.2](https://www.pacodeandbulletin.gov/secure/pacode/data/052/chapter56/s56.2.html)
distinguishes regular residential billing from initial/final bills and permits
certain irregular periods. It does not establish the missing charge arithmetic.
Its residential limits must not be silently applied to commercial customers.

## Implemented safeguards

`src/billing/peco.py::cycle_review` returns a structured, deterministic account
review used by the existing billing/dispatch preflight. It reports:

- Local service dates, number of calendar days and actual elapsed hours; DST
  changes energy integration without changing the calendar-day cycle test.
- Every applicable component change between service start and bill issuance,
  including a change followed by a reversal. Changes affecting another class
  or the unused standard/TOU option do not block an otherwise supported cycle.
- Separate service changes and changes during the bill-issuance gap.
- Missing allocation requirements instead of a guessed 30-day factor,
  blended GSA price or separate segment demand peaks.

In verified-only mode, unsupported inputs fail during browser preparation before a study is queued.
Supported bills retain cycle days, monthly-charge factor 1 and an explicit
`partial_period_proration_applied=false`, plus the actual regular/initial/final
cycle type. A formerly unsupported initial/final label is accepted only within
the same26–35-day window. Verified-only bills retain their earlier arithmetic. The provisional mode adds
separately labeled allocation expressions shared by billing and dispatch. Old
saved results are not relabeled or recomputed.
Do not split a real meter cycle into artificial calendar bills to bypass a
rejection; that can duplicate fixed charges and change GS demand charges.

## Evidence needed to replace provisional estimates with verified rules

Obtain PECO's official billing calculation specification or a written utility
clarification covering:

1. The GSA standard/TOU rate selection for a meter cycle crossing an effective
   date, including an issuance date after a rate change.
2. Delivery energy allocation, fixed-charge allocation, demand measurement
   and demand-rate allocation when their effective dates change within a cycle.
3. Short/extended-period denominator and which quantities it scales: fixed
   charge, GS billed demand/minimum, 1100-kWh threshold and 175-hour rule.
4. STAS/tax ordering when the distribution components have different dates.

An itemized crossing or initial/final bill can provide an independent benchmark
for that account, but does not by itself prove a general rule for every class.
The tariff's monthly definitions do not justify choosing 30, 30.4, 365/12 or the
number of days in the calendar month without that evidence.

## Verification

`test/test_peco_cycles.py` covers all four plans across March/June/December 2025,
January/June 2026, short/extended-period rejection,26/35-day DST cycles of all
three kinds, and
commercial DSIC-only April/July/October 2026 crossings with unequal demand peaks
on opposite sides. It also checks intermediate/reversed changes, issuance gaps
and browser preparation errors. Two complete 30-day initial/final form-to-worker
cases run grid-only/PV-only/PV-plus-battery with 15-minute representative
OpenDSS replay and bill/dispatch reconciliation. Existing PECO tests exercise dispatch rebilling,
API/worker execution, saved artifacts and representative OpenDSS replay.

Run the current checks with the validation launcher; the final run report is
kept in the ignored `.cache/peco_cycles_verified/` directory. This documentation
does not claim that the requested automatic proration feature is complete.

### Recorded candidate results

Engine `ec8345bac5524003ce5379cc2caf28ce1e4c231498ca58e334ee2d51483ee681`:

- The regional plus validation-tooling focused tier passed **1,014 tests**, with
  no failures or skips. Pytest reported 165.64 seconds; launcher phase 166.05 seconds.
  The 71 new cycle tests also passed in a separate focused run. GUI modules were
  excluded. All seven browser JavaScript files passed syntax checks.
- Two additional API/worker studies used July 14–August 12, 2025 service, an
  August 14 bill date and one complete 30-day cycle. Both used explicitly
  synthetic loads and clear-sky PV (assumed 20 °C and 1 m/s), not measured accounts
  or actual weather. No export or battery wear cost entered the bill objective.

| Case | Load peak | PV DC / AC | Battery energy / power | Grid only | PV only | PV + battery |
|---|---:|---:|---:|---:|---:|---:|
|R-TOU residential, initial cycle|2 kW|5 / 4 kW|10 kWh / 3 kW|$165.47|$81.12|$50.33|
|GS-TOU commercial, final cycle|20 kW|10 / 8 kW|30 kWh / 8 kW|$1,105.16|$828.73|$731.04|

The six scenario bills reconciled to their dispatch objectives within $0.00001.
All four optimized costs and both storage minimum-cycling refinements were
proven. Each scenario passed 2,880 representative electrical checks at 15-minute intervals:
**17,280 checks total**, with no convergence, voltage or loading failures.
CSV endpoints and ZIP contents were verified through API bytes. Source, load,
equipment and circuit assumptions remain attached to each result.

The single browser acceptance pass rendered residential/commercial comparisons,
saved and reopened the residential result, restored its initial-cycle JSON,
reviewed the setup and submitted a rerun. The rerun differed only in study name;
its comparison CSV was byte-identical. Evidence is in
`.cache/peco_cycles_development/preview_api.json`, `browser_rerun.json`,
`browser_acceptance.json` and `browser-results.png`. This acceptance does not
claim a browser download event; downloads were checked through the API.
The isolated preview uses its own development snapshot; no stable engine was
promoted. No source changes were made after the passing candidate was frozen.

## Follow-up research: scheduled-cycle rule and operational specification

The follow-up found **Rule 1.3 on printed sheet 10**, which the earlier
review had omitted. It expressly ties application to the first scheduled
billing cycle unless another tariff provision overrides it. That page is now
included in the January 2025, January 2026 and October 2026 source excerpts,
with updated excerpt hashes in the existing manifest. The rule is also present
in the December 2024 tariff; it is not a new 2026 provision.

This narrows the rate-change question, but does not independently identify
whether the operative cycle date is its starting read, closing scheduled read
or scheduled billing-calendar date. It does not provide a numerical partial-
period factor. Verified-only mode still rejects an unsupported allocation rather than
treating this ambiguity as verified arithmetic.

Additional sources inspected:

- PECO's public [supplier support site](https://www.peco.com/doing-business-with-us/energy-suppliers)
  links to its public knowledge/file library. Searches for proration did not
  locate an ordinary R/GS calculation policy. This is not a claim about private
  supplier files or every document PECO may hold.
- The official [bill-sample article](https://peco.my.site.com/s/article/PECO-Bill-Samples)
  links to a public sample package. Its commercial electric/gas example,
  page 2, gives March 14–April 15, 2024 service as 32 days; page 1 gives an
  April 22 issue date. This confirms that a reading date and issue date can
  differ. It is a normal cycle with competitive supply, and does **not**
  establish partial-period or PECO default-supply rate-change arithmetic.
- The official [2024 rate-design volume](https://www.puc.pa.gov/pcdocs/1822419.pdf)
  contains 815 pages. Retail-rates testimony and tariff provisions were
  inspected; they do not supply the missing ordinary R/GS calculation formula.
  [Research notes and provenance](utility_sources/peco/billing-cycle-research-manifest.json)
  are separate from the engine's adopted-rate evidence. Proposed prices and
  unrelated riders were not used as a substitute.

No billing, optimization or browser implementation was changed during that
research-only follow-up. Its engine was the previously tested `ec8345bac552` candidate.
The prior 1,014-test result remains prior evidence, not a new full regression
run. The source-excerpt integrity check was rerun after adding Rule 1.3.

### Questions requiring an authoritative PECO calculation or clarification

These are precise research questions, not sent correspondence or implemented
assumptions:

1. **Cycle anchor:** For a cycle with May 20–June 18 inclusive service, a
   June 19 closing meter read and June 23 issue date, which GSA/TOU, delivery
   and rider versions apply to a June 1 change? Which exact date implements
   Rule 1.3? How does an unscheduled initial/final read differ?
2. **Short-period factor:** For a 12-day initial or final R bill, give the
   fixed-charge factor and its reference period. Is it based on a scheduled
   full cycle, a calendar month, a fixed number of days or another definition?
   Does the answer change in February, a leap year, or a DST month?
3. **GS quantities:** For a 12-day GS period with 900 kWh and 12.36 kW maximum
   30-minute demand, specify the rounding, minimum demand, 1100-kWh condition,
   175-hour rule, demand-price factor and fixed-charge factor, in order.
4. **Crossing delivery prices:** Is energy allocated by measured intervals,
   daily-average kWh or another method? Is one cycle demand used with allocated
   prices, or are separate segment demands measured? Which monthly fixed-charge
   allocation applies?
5. **Extended and special cycles:** Specify the same treatment for a 36-day
   bill and initial/final bills outside the normal window. Identify any different
   residential/commercial limits or exceptions.
6. **Adjustments:** When STAS or a distribution component changes within a
   cycle, identify its date basis and ordering before bill-date DSIC and sales
   tax. DSIC's bills-rendered rule is already verified and remains separate.

The missing evidence for **verified** allocation is the calculation policy,
not another set of rate prices. Provisional estimates are separately labeled. An authoritative response or worked PECO calculation must be retained
with source/date/class applicability, followed by independent bill benchmarks,
shared numeric/dispatch implementation and cycle-specific worker validation.
