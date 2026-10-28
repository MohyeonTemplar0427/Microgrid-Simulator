# Penelec Pennsylvania implementation and targeted validation

Recorded 2026-10-28T19:11:47.229956+00:00. Implemented **FirstEnergy
Pennsylvania Penelec district RS residential and Company-retained GS-Small
(GS-S) default Price-to-Compare supply** in the shared backend/local browser.
See [account/billing scope](Penelec_Pennsylvania.md),
[source guide](utility_sources/penelec_pa/README.md),
[source pins](utility_sources/penelec_pa/sources.json) and independent
[delivery](utility_sources/penelec_pa/delivery_research.md),
[supply](utility_sources/penelec_pa/supply_research.md) and
[rules](utility_sources/penelec_pa/tax_rules_research.md) reviews.

## Supported scope and source limits

Executable complete-calendar component intersections are **January 2025–June
2026 and October 2026**. **July–September 2026 DSIC is unverified and rejects**;
no neighboring-district, prior-quarter or current-price substitution is used.
Partial/shifted cycles, unverified proration, special contracts, HP/TOU/hourly or
alternative supply and export/bank/cashout settlement remain unsupported.

**Mandatory LEDC is included**, independent of whether this customer converted
lighting. Its first positive adopted window is April 2025–March 2026:
RS $0.00022 / GS-S $0.00016 per kWh; April 2026 onward uses $0.00007 / $0.00006.
**January–March 2025 has a disclosed source-based start-window interpretation**:
Original245 identifies only a first April 1, 2025 rate window; Original247
specifies the April computational clock; adopted First Revised245 starts April 1.
No explicit January–March zero-priced row was recovered. Zero charge means no
applicable pre-April window under this interpretation, not a filed zero rate,
backdated April charge or silent missing-rate fallback. Both source reviewers
agreed on this reading; full-year modeled scope retains this qualification.

**January 2025 GS-S is a verified-charge subtotal**, with 6% tax on known current
charges and the known $3.42 GRT-inclusive prior-cost refund applied once afterward.
The unresolved prior-refund sales-tax adjustment is explicitly excluded as
`january_2025_refund_prior_sales_tax_adjustment`, never assigned zero. Full-year
GS-S totals below are mixed complete/subtotal component sums, **not complete annual
commercial amounts due**. Solely-residential RS uses its known $6.15 refund once.
January entitlement and its evidence are separate from the imported-model-state
refund flag. The ordinary positive-bill domain avoids inventing negative-balance
or credit-carry settlement for a prior refund.

RS is one solely residential dwelling, ordinary secondary single-phase service,
with Company-confirmed inactive special demand/ratchet and sourced prior-eleven
actual 15-minute peak bound≤25 kW. Native and actual imported peaks also stay≤25.
Penelec's $3.26/excess-kW branch and 75% prior-eleven excess ratchet are not
implemented generally; these are explicit inactive-charge restrictions. Legacy
multiunit provision A(2), farms and mixed residential/business tax are excluded.

GS-S requires Company-retained existing class **without a demand meter**, actual
metered consumption, no fixed/imputed-usage provision C and no early termination.
Its general-provision matrix is A+C, not Penn Power's B500-kW GSDS branch. The
Company's two-consecutive-month reassignment condition remains independent of the
study. The exact gross/native/net qualification predicate is unresolved. Sourced
prior-twelve qualification bounds≤1,500 kWh and separate native/import cycle
energy≤1,500 form a conservative implementation domain, not an invented monthly
tariff eligibility limit. Adjacent state carries conservative 25-kW/1,500-kWh
bounds without reducing history from PV-adjusted purchases.

One ordinary 120/240V secondary meter/service, unity billing PF, matching metering,
state-only PA tax locality and absence of special fees/exemptions are separately
confirmed. Solely residential electricity is exempt; ordinary fully taxable GS-S
uses 6%. Neither weather coordinates nor utility assignment proves tax locality.

PV/storage needs already-active qualifying ordinary approved renewable NEM/
customer-generator service, required metering and no Partial Services Rider.
Penelec standby/admin/legacy facility charges are not automatically waived by
small size or non-export operation. Storage is PV-only charging, no battery export,
zero exports/banks and no standalone storage. Grid-only removes DER assertions
while preserving independently assigned class, history and refund state.

## Candidate, implementation and preservation

Checkout `/Users/junhayang/Desktop/EnergyEngineerSession/Microgrid_Simulator`,
branch `main`, HEAD `5665eec083d7af90d6f18b29dd3746efc0c93294`.
Frozen engine: `1fe3b4035a49380e8d36b39fb61f772775f505acbb2ddf3348880e7eba31cc6b`.
`regional.js` SHA256: `52e4a50a6de9abc3951df059ab0f00ceed4985caa73d90a7dabe3cb3eeaa9936`.
Full source/dependency/frontend/test/tool/configuration identity is retained at
`.cache/penelec_pa/candidate_frozen_1.json`; no production/test/tool/frontend
edit followed the freeze. Documentation and private audit receipts were completed
afterward without relabeling earlier candidates.

New runtime files are `src/billing/penelec_pa.py` and `penelec_pa_rates.py`;
new tests are `test/test_penelec_pa.py` and `test/test_penelec_integration.py`.
Registry/default site/equipment, native eligibility, absent-DER counterfactual,
browser fields/labels, coverage and targeted driver selection reuse existing
components. The shared audit independently reconstructs Penelec DSIC/STAS bases,
rather than accepting reported basis metrics. Billing math, solver/dispatch,
time-grid, credit/SOC algorithms, PV/storage physics, API/worker schema and
OpenDSS replay behavior remain unchanged. Runtime rates/provenance are literal,
with no cache/network dependency. PENELEC wholesale/load-zone and FE-PN emergency
metadata remain separate from utility district, supplier, account facts and tax.
No wholesale price node, PLC/NSPL/LMP or extra GRT charge is inferred.

The baseline covers **2,017 files**. Eight intended shared wiring/architecture
paths change; the other **2,009 remain byte-identical**, including old utility
modules/source ledgers/reports and ignored CLAUDE.md. Architecture additions
preserve the original document as an exact prefix. AGENTS.md and
Development_Validation.md also remain byte-identical. HEAD/index, all original
hashes, final candidate, source pins, local links and diff checks are recorded in
`.cache/penelec_pa/final_preservation.json`. No staging, commit, push, deployment
or stable-engine promotion was performed. No native GUI was opened; prior local
preview stores were preserved, and the new preview is private port59166.

## Sources, arithmetic and independent review

Official utility/regulator sources were verified before implementation. The
ledger pins **35 originals, 81 checked-in excerpts, two private metadata excerpts,
61 source-linked renders and 25 derivatives**. Of the source-linked renders,
59 are marked visually reviewed and two are retained without that assertion;
contact-sheet/composite review aids are separately identified. All **241 reference
hashes** pass. All 1,265 prior tracked source files also matched the orientation
baseline. Ledger SHA256: `4a43ab81afb62bdc084e034db03fd7b7c6eac81d109ed1eb308bd7a0f783c0e5`.
Receipt: `.cache/penelec_pa/source_preservation_audit_1.json`.

Penelec base, DSS/EEC/USC/SMT, signed DSIC/STAS, SPV, LEDC, TCJA and refunds use
Penelec's own columns. **TCJA is positive 3.04% July–December 2025**, restricted to
base distribution/customer charges; 2025 STAS is +0.01%, 2026 STAS −0.02%.
April–June 2025 DSIC is negative −0.01%; April–June 2026 is +0.39%, October +2.70%.
LEDC and all applicable delivery riders enter DSIC; PTC and DSIC then enter STAS;
ordinary current sales tax follows. Source-replacement June 2025 DSS prices are
$0.00798/$0.00362, not the superseded high-precision initial submission.

Published PTC already embeds GRT/admin/loss/capacity/AEPS/supply transmission and
reconciliation. Separate nonbypassable DSS applies once. January–May SPV credit
−$0.00001/kWh applies to ordinary RS/GS-S including DER; the larger-class waiver
is not imported. Later specified SPV recovery stays inside DSS without duplication.

Supply benchmarks cover all four filed PTC windows. Supplement28's literal May30
endpoint is retained; actual official Penelec December2025/April2026 inserts
independently corroborate the same prices through May31,2026. The retained
June2025 insert has correct June prices but an erroneous May2026 endpoint;
filed November30,2025 controls. A stale indexed December filename was unavailable;
the actual current December PDF is correct. Workbook June-year header errors
are not effective dates. Blocked/stale routes and source identity are preserved.

Independent tests cover 38 literal plan/month bill benchmarks, individual charge
stages, six fixed-flow numeric/symbolic CVXPY/SCIPY cases, source hashes and boundary
rules. The private independent saved-study calculator imports no production/test/
rate/math helper and recomputes **78 bills** from literal verified components and
saved purchases. Maximum component difference is $2.84e-14;
maximum bill difference is **$5.68e-14**, with no cent ties
or cent discrepancies. LEDC/DSIC/STAS/current-tax bases, explicit Jan–Mar LEDC
interpretation, refunds once, all three January GS exclusions, native/import/
history bounds, manifest pins and physical state reconcile. Maximum SOC recursion
error is 1.31e-15kWh; power-balance error is
7.2e-16kW. Receipt `independent_audit.json` retains
146 source/artifact file reads and hashes. It ran once without repairs.

No actual complete customer invoice or exact provider quantity/cash-rounding
rule was recovered. Component half-up cents and unrounded operating proofs do
not establish minimum rounded-cash invoices. Raw and component-cent current
pre-refund/pre-sales-tax charges must meet the customer amount as a narrower
inactive-minimum guard, not the full tariff minimum formula. Unknown floor cases
reject without forced imports or clipped refunds.

## Targeted acceptance

**300 tests passed in33.54s**, no skips/failures (launcher phase33.89s). Selection:
Penelec unit/integration tests, directly affected Met-Ed integration tests, and
`test_regional_coverage.py`, `test_regional_validation_driver.py`,
`test_regional_counterfactual.py`. Checks include rate boundaries including
October, DST, missing/duplicate/naive/hourly/nonfinite data, account/state/refund
rejection, unsupported export, provenance/completeness, worker/save/CSV/ZIP and
counterfactual behavior. A corrupted but internally consistent DSIC/STAS basis
omitting LEDC is explicitly rejected. Python AST, changed-JavaScript syntax and
diff checks pass. Syntax receipt: `.cache/penelec_pa/syntax_receipt.json`.

One new-utility historical matrix passed **4 studies, 12 scenarios, 78 monthly
scenario bills and 227,520 OpenDSS interval checks**, zero failed intervals.
Every selected interval was checked; no driver audits were bypassed or intervals
subsampled. Full2025 and June2026 use exact-site ERA5 at hypothetical
Altoona/Blair coordinates40.52,−78.40, with hourly means held over15-minute
intervals and Open-Meteo/Copernicus attribution. The native household/office shapes
are deterministic synthetic loads, not measured or regionally calibrated.

| Plan | Period | Grid / PV / PV+battery utility charges | Interval checks | Study ID |
| --- | --- | ---: | ---: | --- |
| RS | 2025-01-01–2025-12-31 | $2,933.78 / $2,090.68 / $1,792.49 | 105,120 | `167a2a05a72944319afbe09c98089eda` |
| RS | 2026-06-01–2026-06-30 | $267.08 / $170.85 / $139.80 | 8,640 | `096370ae53584a3e85c79795e306d8f2` |
| GS-S | 2025-01-01–2025-12-31 | $2,326.95 / $1,414.85 / $1,300.92 | 105,120 | `133a520828594f36b1e2ffc39cf27197` |
| GS-S | 2026-06-01–2026-06-30 | $209.49 / $104.66 / $93.94 | 8,640 | `eaad64862d744420b9c06e007058adc3` |

2025 RS includes12 complete modeled cycles under the disclosed LEDC start-window
interpretation. 2025 GS-S includes one January subtotal and11 complete ordinary
cycles. June2026 both plans are complete within scope. June is the explicitly
selected2026 representative month; unit source/arithmetic tests cover other
supported boundaries. This is not an all-month2026 electrical pass. Full October
actual weather is unavailable on the research date; no October historical
OpenDSS pass or future-weather substitution is claimed. July–September rejects.

Both plans use5kW DC/4kW AC PV,10kWh/3kW storage,initial5kWh,20–80%SOC and95%
charge/discharge efficiency. Representative replay uses120/240V split phase,
25kVA transformer,100A service and0.95 lagging load PF, separate from unity billing
PF. Scheduled ideal meter flows determine bills; losses/PCC measurements remain
diagnostics, not site-specific wiring/protection/interconnection approval.

All52 optimized PV/PV-battery cycle primary proofs and26 battery-cycle secondary
minimum-cycling proofs pass;26 direct grid bills make no optimizer claim.
Maximum objective/physical-dispatch reconciliation is $1.000002×10⁻⁶ within the
recorded per-cycle tolerances; zero strict fallbacks. Annual secondary objective
sums differ by about $1.2×10⁻⁵ within propagated monthly tolerance budgets.
Six annual scenario proof flags areFalse and six single-month flagsNone:
rolling per-cycle perfect foresight with carried SOC/history is **not a jointly
optimized annual minimum**, and no actual-customer savings are claimed.

Receipts are `.cache/penelec_pa/acceptance_1/report.json`, JUnit/logs and
`regional/validation.json`, `validation-summary.json`, requests/results, CSV
manifests and pinned driver copies. Launcher monotonic elapsed111.89s;
regional phase77.79s, matrix session74.08s and worker-reported total68.70s are
overlapping scopes and must not be added as active-development time. Browser-tool
waits and active development were not separately instrumented. Timestamp records
are retained; no wall-clock subtraction is substituted for these elapsed metrics.

No full workflow/release, broad regional grouping, GUI or unaffected historical
matrix was selected: shared behavior/contracts are unchanged and targeted checks
bound the edits. This is targeted acceptance, **not a full-release or stable-engine
promotion pass**. Met-Ed integration checks establish regression behavior only;
they do not resolve the prior omitted-rider issue described below.

## API, browser and preservation receipts

All four frozen matrix studies passed HTTP/manifest and full artifact audits,
52 exact CSV table endpoints, ZIP integrity and matching result manifests.
Receipt: `.cache/penelec_pa/api_artifact_audit_1.json`.

One concise background browser pass on the same frozen engine/frontend passed
both classes: restore seed, inspect supply/account/history/cycle/PV/weather/
battery settings, review, submit, render results, save with name, return home and
reopen. Residential dwelling text is RS-only; GS-S visibly retains actual metering,
no-demand-meter and no-fixed/imputed-C assertions. History25kW/1500kWh and May2026
prior-month dates, PV-only charging and actual ERA5 selection were retained.
No browser operation timed out/stalled, and no upload/download-event/filechooser
route was used. Browser download handling itself is unasserted; endpoint bytes
and saved artifacts were verified separately.

Browser-created studies: RS `add2c81fa6614fa1a38ab7aacc20f81b` ($267.08/$170.85/$139.80)
and GS-S `bf39fe5ddb1a466f89eb690bd6344de6` ($209.49/$104.66/$93.94).
All24 actual request fields other than display name exactly match their seed.
Both new runs pass all artifact audits,26 CSV endpoints and ZIP bytes, with17,280
additional OpenDSS interval checks and zero failures. These are separate from
the227,520 matrix count. Receipts: `browser_acceptance.json`,
`browser_observations.json`, `browser_restoration_audit.json`,
`browser_api_artifact_audit_1.json`; screenshots `browser_RS.png`/`browser_GS.png`.
Preview: `http://127.0.0.1:59166/`, development snapshot only.

## Related prior Met-Ed LEDC omission

This research found that the earlier Met-Ed adapter omits mandatory LEDC from
April2025 onward. Its prior complete-bill claims need separate correction and
revalidation; its original numerical, optimizer, electrical and browser receipts
remain evidence for the candidate they actually checked, without proving an
omitted tariff component. Do not describe their old pass as a new full-tariff
Met-Ed pass. The original files/evidence pins were preserved unchanged, and this
task does not silently repair/relabel them. Source-backed issue notice:
`.cache/penelec_pa/prior_met_ed_ledc_issue.json` and the Penelec source reviews.
