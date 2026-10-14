# ComEd historical rates and documented meter cycles

Development candidate, October 13, 2026. Existing schema-9 calendar bill studies
and schema-10 calendar simulation requests remain valid. An optional
`billing_cycles` contract extends schema 10 and the shared ComEd billing/dispatch
API. No stable engine is promoted automatically.

## Verified historical evidence and coverage

Coverage applies to the supported residential/commercial account classes and
depends on the supply plan. Only complete composites are enabled for that plan:

| Supply | Verified 2025 utility billing months | Verified 2026 utility billing months |
|---|---|---|
| BES | January–December | January–October |
| BESH | January–December | January–October |

Both supplies now have complete 2025 and January–October 2026 monthly composites.
November onward in 2026 still rejects. A known supply price or base CFR
adjustment alone cannot fill a missing composite. A twelve-cycle 2025 billing
replay is supported with explicit utility billing-month designations and full
interval coverage. This establishes rate coverage, not measured load/weather
coverage, an annual solar settlement, or guaranteed full-year MILP convergence.
The research target remains 2017–2026; no ten-year coverage is claimed.

June was added from ICC filings [ERM26-082](https://www.icc.illinois.gov/downloads/public/filing/4/399143.pdf),
[ERM26-087](https://www.icc.illinois.gov/downloads/public/filing/4/399174.pdf),
and [ERM26-086](https://www.icc.illinois.gov/downloads/public/filing/4/399171.pdf),
with applicable delivery and rider tables from the filed 2026 ratebook.
Retained evidence and document hashes are in
[`utility_sources/comed/history/manifest.json`](utility_sources/comed/history/manifest.json).
Each new bill line identifies its source document, hash and one-based pages;
the legacy `source_pdf_pages` field remains for compatibility and must be read
with the named source document.

| June component | Verified value | Source |
|---|---:|---|
| Residential BES purchased electricity | $0.08677/kWh | ERM26-082 p4 |
| Demand non-heating BES purchased electricity | $0.08810/kWh | ERM26-082 p4 |
| BES PEA | $0.00230/kWh | ERM26-087 p3 |
| BESH HPEA | -$0.00191/kWh | ERM26-087 p4 |
| BESH capacity | $10.11236/kW-month | ERM26-082 p6 |
| BESH transmission | $0.01074/kWh | ERM26-082 p7 |
| BESH miscellaneous procurement | $0.00134/kWh | ERM26-082 p8 |
| Residential IDUF | 1.0206 | ERM26-082 p9 / ratebook p801 |
| Other nonresidential / large IDUF | 1.0054 / 1.0015 | Same |
| BESH incremental supply factor | 0.9979 | Same |
| Environmental recovery | $0.00009/kWh | Ratebook p789 |
| Zero-emission adjustment | $0.00087/kWh | Ratebook p820 |
| CFRA including reconciliation | -$0.01344/kWh | ERM26-086 p3 / ratebook p818 |

The June BESH multiplier is `1.0124 × 0.9979 × 1.0406`. Its factors and
capacity are stored on the dated composite, not borrowed from September.
Independent constant-import benchmarks are $141.82 for a residential
single-family non-heating account at 1 kW, and $1,900.31 for the documented
small-secondary commercial fixture at 20 kW. Both are modeled subtotals.

### July and August 2026

The official [October 2026 monthly adjustment record](https://www.comed.com/cdn/assets/v3/assets/blt3ebb3fed6084be2a/bltd0031ae7271bf238/6ac685e1ff666ce7a12a40f7/2026_PEA_record_for_rate_book.pdf?branch=prod_alias)
establishes BES PEA and BESH HPEA, including their credit signs. ERM26-082 and
the later ratebook corroborate June–August supply prices/factors; the ratebook
also records the August ECR change and both CFRA reconciliation totals.

| Component, USD/kWh | July 2026 | August 2026 |
|---|---:|---:|
| BES PEA | 0.00247 | -0.00142 |
| BESH HPEA | 0.00690 | -0.00376 |
| ECR | 0.00009 | 0.00007 |
| CFRA total | -0.01228 | -0.00690 |

The 744-kWh single-family non-heating BES benchmark is $146.86 for July and
$147.95 for August, before excluded taxes and fees. BESH still requires dated
COMED-zone residual LMP data and a separately documented capacity obligation.

### January–May 2026

The ICC filing index was inspected in the user-unlocked browser session. The
stamped filings are retained as PDFs and extracted text with URLs, SHA256 hashes,
index filing/effective dates, and original page numbers in the evidence manifest.
Applicability comes from each table's **utility billing month**, which can differ
from the stamped effective date. No CAPTCHA bypass or neighboring-rate fallback
is used.

[ERM26-068 pp4–8](https://icc.illinois.gov/downloads/public/filing/4/398491.pdf)
explicitly corroborates January–May supply components: residential BES energy
$0.07841/kWh and transmission $0.01819/kWh; commercial Watt-Hour/demand/space-heat
energy $0.07870/$0.07899/$0.07565 per kWh and transmission $0.01805/kWh; BESH
capacity $8.32925/kW-month, transmission $0.01083/kWh and procurement
$0.00062/kWh. Its forecast June figures were superseded and are not used.
The December 2025 filed ratebook p785 states the January–May IDUF values
1.0090 residential, 1.0065 other nonresidential and 1.0014 large-load, with
ISUF 1.0002. The BESH hourly-energy multiplier is
`1.0124 × 1.0002 × 1.0406` throughout these five billing months.

The filed annual 2026 delivery, RBAF, TPAF, DGRA, EE, ETAC and RCA tables
explicitly cover this period. Annual applicability is verified rather than
inferred from their publication dates. REA is $0.00502/kWh and ZEA is
$0.00189/kWh through May. ECR is $0.00010/kWh in January–March and
$0.00009/kWh in April–May. DRAF changes from zero to 0.6785% in April,
as [ERM26-031 p3](https://icc.illinois.gov/downloads/public/filing/4/396435.pdf)
specifies. EDAF remains zero. The retained annual/rider text excerpt identifies
the original ratebook pages for each component.

| Billing month, 2026 | BES PEA, $/kWh | BESH HPEA, $/kWh | CFRA total, $/kWh | CTS, $/kWh | LID residential / small / large, $/month |
|---|---:|---:|---:|---:|---|
| January | 0.00357 | 0.00743 | -0.02381 | 0.00007 | 1.17 / 11.70 / 438.75 |
| February | 0.00889 | -0.00189 | -0.02182 | 0.00007 | 1.22 / 12.20 / 457.50 |
| March | -0.00151 | -0.01528 | -0.04110 | 0.00007 | 1.22 / 12.20 / 457.50 |
| April | 0.01159 | 0.01773 | -0.03186 | 0.00006 | 1.35 / 13.50 / 506.25 |
| May | 0.08166 | 0.08032 | -0.06414 | 0.00009 | 1.35 / 13.50 / 506.25 |

PEA/HPEA come from [ERM26-005 pp3–4](https://icc.illinois.gov/downloads/public/filing/4/395199.pdf),
[ERM26-019 pp3–4](https://icc.illinois.gov/downloads/public/filing/4/395844.pdf),
[ERM26-037 pp3–4](https://icc.illinois.gov/downloads/public/filing/4/396728.pdf),
and [ERM26-058 pp3–4](https://icc.illinois.gov/downloads/public/filing/4/398254.pdf).
CFRA uses the complete CFR+CFRMR **total**, retaining its credit sign, from
[ERM26-008 p3](https://icc.illinois.gov/downloads/public/filing/4/395230.pdf),
[ERM26-020 p3](https://icc.illinois.gov/downloads/public/filing/4/395863.pdf),
[ERM26-039 p3](https://icc.illinois.gov/downloads/public/filing/4/396796.pdf),
and [ERM26-059 p3](https://icc.illinois.gov/downloads/public/filing/4/398271.pdf).
LID changes are in [ERM26-007 p4](https://icc.illinois.gov/downloads/public/filing/4/395227.pdf)
and [ERM26-033 p4](https://icc.illinois.gov/downloads/public/filing/4/396597.pdf).
CTS uses [ERM26-034 p3](https://icc.illinois.gov/downloads/public/filing/4/396598.pdf)
and [ERM26-063 p3](https://icc.illinois.gov/downloads/public/filing/4/398278.pdf).
Published cents are converted to dollars; no base-only CFR or month-to-month
interpolation is used.

The annual DGRA table also exposed a transcription error in the prior 2026
Extra Large commercial adapter: the filed adjustment is **$0.13/kW**, whereas
$0.14/kW belongs to High Voltage. Extra Large is corrected for all verified
2026 billing months and independently tested. The High Voltage DFC formula
continues to exclude DGRA as filed.

Independent Decimal benchmarks use a constant 1-kW import for a single-family
non-heating residential account. BESH uses explicitly synthetic $50/MWh
COMED-zone residual prices and a fixed 2-kW capacity obligation. Reference
arithmetic is separate from the production billing code; these are modeled
subtotals before excluded taxes and franchise costs, not observed bills.

| Billing month, 2026 | Physical hours / kWh | BES subtotal, $ | BESH subtotal, $ |
|---|---:|---:|---:|
| January | 744 | 132.97 | 128.35 |
| February | 672 | 127.01 | 114.62 |
| March | 743 | 116.23 | 98.54 |
| April | 720 | 129.85 | 127.56 |
| May | 744 | 161.66 | 153.17 |

The documented-cycle contract is unchanged: an explicitly **April-designated**
March 15–April 14 cycle uses the April composite throughout, with one set of
monthly charges and its own measured demand. No service-calendar splitting
or automatic short-service proration is introduced.

### Dated 2025 delivery and riders

The January, July and December 2025 utility archive revisions were downloaded
and hashed. Selected component pages are retained, rather than copying large
ratebooks into the repository. The [2025 PEA/HPEA record through June](https://www.comed.com/cdn/assets/v3/assets/blt3ebb3fed6084be2a/bltd0031ae7271bf238/682c9fe866e148d5541a49fe/2025_PEA_record_for_rate_book.pdf?branch=prod_alias)
and the [ICC historical BES price table](https://icc.illinois.gov/downloads/public/pluginillinois/HistoricalPriceToCompare.pdf)
provide additional monthly adjustment evidence. The latter is a residential
price-to-compare table, not a source of commercial PEC subgroup prices or HPEA.
Commercial subgroups come from filed sheet1, including
[ERM25-131](https://www.icc.illinois.gov/downloads/public/filing/4/393526.pdf).

The adapter now dates residential/commercial delivery bases, IDUF, DRAF, EDAF,
RBAF, TPAF, DGRA, RCA, LID recovery, REA, EE, ETAC, ECR, ZEA, CFRA and CTS.
Commercial supply is owned by the year/month composite, eliminating the former
month-number-only lookup. BESH capacity and system-average SBUF/ISUF/DLF are
also dated. Filed supply and capacity charges are already uplifted and receive
no second uncollectible adjustment.

| 2025 billing month | DRAF | EDAF |
|---|---:|---:|
| January–March | 17.2495% | -0.0359 |
| April–October | 17.0696% | -0.0380 |
| November | 10.8072% | -0.0291 |
| December | 14.0883% | -0.0327 |

EDAF is a decimal factor, not a percent printed without conversion. The
November revisions are independently filed in [DRAF](https://www.icc.illinois.gov/downloads/public/filing/4/394253.pdf)
and [EDAF](https://www.icc.illinois.gov/downloads/public/filing/4/394254.pdf).
RBAF is explicitly not applicable before January 2026. The first MRPP annual
reconciliation proceeding begins in May 2025; its first TPAF is filed in
December 2025 for January 2026. Initial LID tables likewise begin January 2026.
Neither adjustment nor the LID recovery charge is backfilled into 2025.
The October archive's 2025 columns corroborate annual EE, ETAC and RCA values.

The retained source has two footer inconsistencies: July 2025 sheet9 says
March 2024 while the table describes 2025, and December 2025 sheet63 says
November 2026 while its table describes October–December 2025. Their filing
index/applicability tables and the later stamped DRAF revision are preserved
and documented in the manifest; the original text is not silently corrected.

The user completed the ICC CAPTCHA, allowing the 2025 filing index to be
inspected. Exact public PDF links were downloaded, hashed, text-extracted and
rendered; the CAPTCHA was not bypassed. The web reader still returned 502 for
some PDFs, while ordinary direct HTTPS retrieval succeeded. Two mutable URLs
returned 2026 documents despite cached 2025 search excerpts: the bare
Contentstack `Ratebook.pdf` and ICC `currentbooks` informational sheets. Those
excerpts were not used to enable historical rates.

### Closing the 2025 gaps

CFRA informational sheet36.1 revisions29–31 explicitly establish the **total**
CFR adjustment plus monthly reconciliation, rather than just the CFR base:

| Utility billing month | CFRA total, USD/kWh | Filed evidence |
|---|---:|---|
| March 2025 | 0.00803 | [ERM25-015 p3](https://icc.illinois.gov/downloads/public/filing/4/388714.pdf) |
| April 2025 | 0.00810 | [ERM25-033 p3](https://icc.illinois.gov/downloads/public/filing/4/389486.pdf) |
| May 2025 | -0.00522 | [ERM25-056 p3](https://icc.illinois.gov/downloads/public/filing/4/390849.pdf) |

[ERM25-047 pp4–8](https://icc.illinois.gov/downloads/public/filing/4/390605.pdf)
corroborates January–May PECs, PJM service charges, capacity and procurement.
Its forecast June figures were superseded and are not used. Spring PEA/HPEA
come from the retained 2025 utility adjustment record. ECR changes from
$0.00002 to $0.00007/kWh in the **April billing month**, as filed in
[ERM25-026 p2](https://icc.illinois.gov/downloads/public/filing/4/389292.pdf).
April also changes DRAF/EDAF; January–May IDUF/ISUF remain their separately
filed values. [ERM25-031 p3](https://icc.illinois.gov/downloads/public/filing/4/389345.pdf)
confirms zero CTS through May. The ordinary 2025 delivery and other rider
sources continue to apply; no 2026 factor is backfilled.

| Utility billing month | HPEA, USD/kWh | Filed evidence |
|---|---:|---|
| August 2025 | 0.00628 | [ERM25-121 p4](https://icc.illinois.gov/downloads/public/filing/4/393256.pdf) |
| September 2025 | -0.00538 | [ERM25-132 p4](https://icc.illinois.gov/downloads/public/filing/4/393564.pdf) |
| October 2025 | 0.02498 | [ERM25-154 p4](https://icc.illinois.gov/downloads/public/filing/4/393873.pdf) |
| November 2025 | -0.04214 | [ERM25-166 p4](https://icc.illinois.gov/downloads/public/filing/4/394224.pdf) |

These filings also corroborate BES PEA on p3. Filing dates are not the
applicable billing-month dates: a July filing can establish the August rate.
Credits keep their parentheses-derived negative signs after cents-to-dollars
conversion. The catalog remains supply-specific and still excludes a version
from BESH if its HPEA is unverified.

The stamped sources preserve two additional date inconsistencies. ERM25-033
has a March19 receipt/index date and March20 footer; its explicit April2025
table and March21 effective date determine scope. ERM25-027 has a March2025
ICC receipt but a March2024 footer; its explicit 2025 DRAF table is corroborated
by the later stamped October revision. Both original records and differences
are retained in the manifest.

Independent constant-1-kW single-family non-heating benchmarks, excluding
state excise, municipal and franchise charges:

| 2025 month | Physical hours/kWh | BES subtotal | BESH subtotal |
|---|---:|---:|---:|
| March | 743 | $128.94 | $130.95 |
| April | 720 | $122.81 | $126.60 |
| May | 744 | $133.46 | $138.99 |

BESH uses explicitly synthetic $50/MWh residual hourly prices and a fixed
2-kW account capacity obligation in these benchmarks. The full-year BES
benchmark consumes 8,760 kWh and totals $1,569.53, the sum of twelve independently
calculated monthly subtotals. It is not a complete customer invoice or a
weather-derived solar performance study.

Reproduce downloads with:

```sh
/usr/local/bin/python3 tools/retrieve_comed_history.py --source-id ERM26-082
```

The command accepts identified official documents only, checks their pinned
SHA256 before writing, and never registers rates. A different revision requires
review. Production billing/tests do not download data.

### October 13 validation and candidate

Baseline: `/usr/local/bin/python3 -m pytest -q` gave **1,744 passed, 1 skipped**.
The expanded full suite gave **1,780 passed, 1 skipped** (226.39 seconds).
Checks include independent 2025/2026 Decimal bill benchmarks, all dated rider
inputs, BES/BESH availability differences, unknown-rate rejection, historical
commercial demand and November factor changes, real-cycle DST coverage,
bill/dispatch reconciliation, physical battery operation and form-to-worker
cases for August 2026 BESH and November 2025 commercial BES. Both replayed
through the representative OpenDSS circuit. Source URLs/hashes match the retained
manifest. JavaScript syntax and `git diff --check` passed.

Separate candidate: `http://127.0.0.1:19015/`, store
`.cache/comed_history_preview`, immutable engine
`12019ed3e32259f1f315e0c9cf86fdf572f4a1fc1d17a1b362020d7441e3764f`.
The standalone browser also completed November 2025 residential BES (constant
1 kW, 721 kWh, $120.89 subtotal) and August 2026 residential BESH (constant
1 kW, synthetic $50/MWh residual LMP and 2 kW capacity obligation, 744 kWh,
$137.16 subtotal). Switching to BESH removed the unverified November 2025
choice and required a new selection. These are hypothetical validation cases,
not measured customer bills or observed market-price studies.

The modern desktop window serves the same form, queue and backend; there is no
second rate implementation to update. Its native window was not separately
opened during this check. Existing San Diego, ComEd integration and ComEd cycle
pins were preserved. Web UI v1.0.1 remains unchanged. No staging, commit, push,
deployment or release promotion was performed. Restart this candidate with
`--data-dir .cache/comed_history_preview --port 19015`, omitting
`--refresh-engine` to retain its reviewed pin.

### Validation of completed 2025 history

After the human CAPTCHA handoff, the unchanged focused baseline was **165
passed**. The expanded focused run passed 217 tests and exposed one obsolete
September2025 rejection expectation; the rejection test now uses unsupported
September2024 and passes. The final complete regression run gave **1,812
passed, 1 skipped** in 239.65 seconds with `/usr/local/bin/python3 -m pytest -q`.
JavaScript syntax and `git diff --check` also passed.

Tests exercise all twelve 2025 composites for residential/commercial BES/BESH,
independent March–May subtotals, signed August–November hourly adjustments and
exact source pages/hashes, twelve consecutive cycle bills and cost expressions,
8,760 annual physical hours with 743 in March/721 in November, missing intervals,
unverified HPEA rejection and early2026 gaps. New production-form-to-worker
cases cover March2025 residential BES, May2025 commercial BESH and November2025
residential BESH; all replayed through the representative OpenDSS model.
This is representative-circuit validation, not a site-specific feasibility claim.

The separate candidate is `http://127.0.0.1:19016/`, store
`.cache/comed_2025_preview`, immutable engine
`9dc4a0e08282cf59d6a4817167b1c42b1972d29ad4f214efcd591ecd4c544ce0`.
Actual standalone browser submissions completed March2025 BES at $128.94
(743 kWh) and November2025 BESH at $96.17 (721 kWh, synthetic $50/MWh prices,
fixed 2-kW obligation). All input and tariff assumptions remain explicit.
The main simulation form and modern desktop service reuse the same catalog;
no second set of rates is introduced. The native desktop window was not
separately opened in this check. Restart this candidate with
`--data-dir .cache/comed_2025_preview --port 19016`, without `--refresh-engine`
to retain this pin. Existing engine pins and Web UI v1.0.1 remain unchanged.
No staging, commit, push, deployment or stable release promotion was performed.

### Validation of January–May 2026 history

The focused pre-change baseline was **156 passed**. The expanded billing,
cycle, dispatch and shared API/worker run passed **246 tests** with
`/usr/local/bin/python3`. One obsolete March2026 rejection expectation was
updated to verify its now-supported DST month; November2026 still rejects.
The full regression suite passed **1,840 tests, with 1 skipped**, in 247.41
seconds using `/usr/local/bin/python3 -m pytest -q`. Two NumPy reduction
warnings came from the unchanged municipal-dispatch tests, which passed.
JavaScript syntax and `git diff --check` passed.

Checks include independent five-month BES/BESH subtotals, dated commercial
delivery and LID charges, Extra Large DGRA, May short-service factors, credit
signs, terminal battery energy, missing-interval rejection, catalog boundaries
and strict per-component provenance. Production-form-to-worker cases cover
March2026 residential BES, May2026 commercial BESH, and an April-designated
March15–April14 commercial BES cycle. All three replayed through the
representative OpenDSS circuit; this is not site-specific validation.

Separate candidate: `http://127.0.0.1:19017/`, store
`.cache/comed_early_2026_preview`, immutable engine
`5393b1adc258dcb088ff2a96490b739ef2610ecb9ce48b7b9e18e9933b0b77a0`.
Actual standalone browser submissions matched January2026 BES at **$132.97**
and May2026 BESH at **$153.17**, both 744-kWh single-family non-heating
synthetic examples. The hourly case uses $50/MWh synthetic residual prices
and a fixed 2-kW capacity obligation. These are subtotal benchmarks, not
measured customer bills. The browser lists all January–May2026 choices for
both supplies.

The main browser and modern desktop service share the catalog and worker;
there is no duplicated rate implementation. The native desktop window was not
separately opened. All five prior engine pins and Web UI v1.0.1 are unchanged.
Restart with `--data-dir .cache/comed_early_2026_preview --port 19017`, without
`--refresh-engine` to retain this candidate. No staging, commit, push,
deployment or stable-release promotion was performed.

## What a billing month means

GTC sheet197, original PDF p257, defines the billing month by the utility's
meter-reading/data-acquisition schedule. The service days start the day after
the previous read and include the current read day. Holidays/weekends can move
a scheduled billing-month read outside the corresponding calendar month.
GTC sheet133 (p178) and BES sheet22 (p27) apply the summer/nonsummer supply
choice to the named billing month. Filing dates printed at the bottom of an
informational sheet are not a substitute for its explicit applicability table.

For example, **September 15–October 14**, explicitly designated as the
**October billing month**, uses the October monthly composite over the entire
cycle. It does not split the supply price or PEA on October 1. It receives one
customer charge, one metering charge and one commercial MKD measurement over
all eligible half-hours in that cycle. Two consecutive documented cycles have
separate monthly rates, fixed charges and demand peaks, even when their service
dates cross a rate-change boundary.

There is currently no verified service-date-only mid-cycle change in the
enabled composites. Such a change must get its own component applicability and
allocation rules before being enabled; the model does not apply generic
calendar splitting or split a demand peak merely because rates changed.

## Cycle contract and partial periods

`ComEdBillingCycle` stores first/last inclusive service dates, designated
billing month, `kind`, source reference and optional per-charge allocation
factors. Intervals remain half-open internally. UTC physical interval checking
preserves Central-time DST folds/gaps. Commercial 15-minute inputs must cover
both records in each aligned XX:00/XX:30 demand block. No missing interval is
filled, resampled or reinterpreted as a shorter bill.

The bounded regular-study contract accepts 20–45 whole service days, charges
monthly amounts once, and requires a documented or explicitly hypothetical
cycle source. Those duration bounds are simulator limits, not filed utility
eligibility thresholds. A non-calendar regular cycle uses normal monthly
charges once; it is not charged twice or automatically prorated because it
contains only part of two calendar months.

For a **shortened first/final service bill**, select `short_service` and supply
explicit allocation factors for every applicable fixed/capacity/demand line.
The source must document the charge allocations from a bill or applicable
rule; factors apply to the adjusted charge before final half-up cent rounding.
No universal first/final-bill proration rule has been verified in this work.
The model neither assumes `days/30` nor prorates a commercial peak or a capacity
obligation automatically. It validates the input structure, not the authenticity
of the source. Hypothetical allocations must be labeled as such.

**An incomplete excerpt of a longer ongoing cycle is unsupported.** Supply all
intervals for the actual regular or shortened bill; an unknown earlier/later
peak cannot be reconstructed from a subset. Account tariff/supplier/class
switching within a cycle and multiple short-service bills assigned to one
utility billing month also remain unsupported.

```python
from datetime import date
from src.billing.comed_cycles import ComEdBillingCycle
from src.billing.comed_costs import calculate, compile_costs

cycle = ComEdBillingCycle(date(2026, 9, 15), date(2026, 10, 14),
    date(2026, 10, 1), source="Confirmed October cycle from bill; no identifiers")
bill = calculate(imports, account, hourly_prices, billing_cycles=[cycle])
costs = compile_costs(imports.index, account, hourly_prices, billing_cycles=[cycle])
```

`calculate` retains every cycle's authoritative bill and dated line items.
`compile_costs` builds matching cycle-local demand expressions. Battery SOC is
continuous across consecutive cycles; terminal SOC equals initial SOC for the
whole study. Fixed historical eligibility and BESH obligations are preserved.
The optimizer still handles negative prices with exclusive storage modes,
enforces non-export balance and reports variable-line cent-rounding bounds.

## Browser and reproducibility

The main wizard has **ComEd billing cycle** controls beside study dates. Choose
a calendar study or a documented cycle, explicitly select the utility billing
month, and provide source evidence. Short-service factors are advanced JSON;
an advanced list supports consecutive cycles. Backend validation requires exact
ordered coverage and rejects overlaps/gaps/unsupported billing months.
Saved settings retain the whole contract; the worker uses its immutable engine
snapshot. Old pinned engines do not expose the new cycle choice. Schema 9
remains a calendar-month bill-checking tool listing all verified billing months.

Results include a **Subtotals and demand by documented meter cycle** table and
cycle-indexed itemized charges. The comparison's peak summary is the maximum
over cycles, not the sum of charged peaks. Inspect cycle rows for the charged
MKD and individual subtotals. `total_usd=None`, `is_complete_bill=False` and
tax/franchise exclusions remain unchanged. Non-export/clear-sky/representative
OpenDSS scope and solver limits remain as described in
[ComEd simulation integration](ComEd_Simulation_Integration.md).

Tests cover independently calculated June components, both customer classes and
BES/BESH, cycle designation across October 1, separate peaks/charges for linked
cycles, explicit short-service allocations, weekend-only zero MKD, DST grid
counts, missing data, overlaps, unsupported history, cost/bill reconciliation,
terminal energy and production form-to-worker saved-result propagation.

Earlier cycle-extension validation: **1,744 passed, 1 skipped** using `/usr/local/bin/python3 -m
pytest -q`. The first full candidate run encountered one SciPy error in the
unchanged municipal optimizer; that file passed independently (10 tests), and
the full rerun passed. JavaScript syntax and Git whitespace checks passed.
The real browser restored and submitted the October-designated September
15–October 14 commercial BES study, then saved the named result. Its candidate
engine is `6c00c587a8daaf5af9d5824fee8d227d140585f1560c5abca9718bc93442a708`;
the grid/PV/PV+battery subtotals are $1,763.95/$1,260.83/$1,204.76. The study
is hypothetical, clear-sky and non-export, not measured bill reconciliation.
Existing staged work and stable engine pointers were preserved; the extension
was not staged, committed, pushed or deployed.

Remaining historical work: retrieve and reconcile complete monthly composites
for 2017–2024 and November 2026 onward; verify universal shortened
service proration and any actual service-date transitions; reconcile measured
ComEd bills; then extend taxes, other supplier/TOU contracts and export rules.
