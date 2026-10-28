# Met-Ed Pennsylvania implementation and targeted validation

Recorded 2026-10-28T03:03:26.386724+00:00. Implements **FirstEnergy
Pennsylvania Met-Ed district RS residential and Company-retained GS-Small
(GS-S) default Price-to-Compare supply** in the shared backend/local browser.
Read [billing/account scope](Met_Ed_Pennsylvania.md), the
[source guide](utility_sources/met_ed_pa/README.md) and
[dated source ledger](utility_sources/met_ed_pa/sources.json).

## Coverage and unresolved scope

Verified executable component intersections are **January2025–June2026 and
October2026**, complete ordinary matching calendar cycles only. **July–September2026
DSIC remains unverified and rejects**; April's value is not carried forward and
October's value is not backfilled. No alternative-supplier, TOU/HP/GSDS, export,
bank, cashout, partial/shifted-cycle or unverified proration settlement is enabled.

**January2025 GS-S is a verified-charge subtotal.** Current tariff charges carry
6% current sales tax; the known $4.18 GRT-inclusive prior-cost refund applies once
afterward. Its unknown prior-period sales-tax adjustment is explicitly excluded
as `january_2025_refund_prior_sales_tax_adjustment`, never assumed zero. Therefore
2025 GS-S annual totals below are mixed complete/subtotal component sums, **not
complete annual commercial amounts due**. The solely-residential RS exemption
allows its January bill to remain complete with the known $6.53 refund once.
Account entitlement/posting facts remain independent of the study's refund state.

Initial eligibility is deliberately narrow: one ordinary continuous secondary
120/240V single-phase meter/service; no special rates, CAP/PCAP or other fees;
state-only tax facts separately confirmed. RS requires solely residential use,
Company-confirmed inactive special-demand/ratchet treatment, independent prior11
actual15-minute peak upper bound≤25kW and both native/current-import peak≤25kW.
GS-S requires Company-retained non-demand class and independent prior12
qualification upper bound≤1500kWh plus native/current-import cycle energy≤1500kWh.
The conservative envelopes carry between adjacent cycles and are never reduced
from PV-adjusted purchases. These are **implementation domains**, not general
tariff eligibility tests or an interpretation of the unresolved GS gross/net
classification quantity. The tariff's two-consecutive-month reassignment condition
and RS demand-metering triggers remain documented in the source notes.

Current raw and component-cent pre-refund/pre-sales-tax charges must meet the
customer amount to stay inside a conservative inactive-minimum domain. Unknown
floor/negative-credit ordering cases reject without forced purchases; this guard
does not claim to implement the tariff's full minimum formula. In particular,
GS-S zero-import2026 can reject with its negative smart-meter rider. January's
refund is never clipped or counted in STAS/current-tax bases.

PV/storage requires already-active qualifying ordinary approved renewable
NEM/customer-generator service, required metering, no Partial Services Rider,
PV-only charging, no battery export and zero exports/opening bank. Grid-only
removes DER assertions while preserving independent classification/refund/history.
Equipment bounds and coordinates do not establish eligibility or approval.

## Candidate, changes and preservation

Checkout `/Users/junhayang/Desktop/EnergyEngineerSession/Microgrid_Simulator`,
branch `main`, HEAD `5b32d89eb2672f4e29becd1e6f74b651c3d64ccf`.
Frozen engine: `3f5cf2e651f0216eb3030636173008ad6dd2c8e66fdfd9c1f39e79b33f0befa9`.
Final `regional.js` SHA256:
`3f0f29df423e497a17996ca63cd9cd1799549e8bf807bf2b9a6d14d6a55043ff`.
Original complete matrix fingerprints are `candidate_frozen_1.json`; final
browser/form fingerprints are `candidate_frozen_2.json`, both under
`.cache/met_ed_pa/`. A browser-discovered PTC choice inherited an inapplicable
GSC-1 label. The sole post-matrix change corrects that display label **only for
Met-Ed**. Source/tests/tools/configuration/dependencies and engine ID remain
identical; original matrix evidence retains its original frontend pin. Final
form tests and browser/API checks use pin2. See `frontend_label_correction.json`.

New modules `src/billing/met_ed_pa.py` and `met_ed_pa_rates.py` contain the adapter
and snapshot-safe dated literals. Tests are `test/test_met_ed_pa.py` and
`test/test_met_ed_integration.py`. Existing registry/counterfactual, explicit study
site/defaults, native eligibility guards, browser account fields, coverage and
validation-driver hooks were extended. Shared billing math, solver/dispatch
algorithms, PV/storage physics, worker/API schema and OpenDSS replay are unchanged.
No runtime network or ignored source-cache dependency is introduced.

The baseline covers1,927 files. Only eight intended shared wiring/architecture
paths change; the other1,919 remain byte-identical. The architecture document
preserves its old contents as an exact prefix. AGENTS.md, ignored CLAUDE.md and
Development_Validation.md remain byte-identical. Final instructions, original-file,
HEAD/index, candidate, source-hash, local-link and diff checks are recorded in
`.cache/met_ed_pa/final_preservation.json`. No staging, commit, push, deployment
or stable-engine promotion was performed. Existing preview stores and earlier
utilities' source/report/evidence pins remain preserved.

## Dated sources and independent billing benchmarks

Official utility/regulator sources were researched before implementation.
The ledger contains **34 unique originals,79 checked-in excerpts,2 private
metadata excerpts,20 source-linked renders and14 hashed derivatives**. Nineteen
renders are marked visually reviewed; one is retained without that assertion.
All186 hash checks/185 unique pinned paths pass. Source ledger SHA256:
`d9d6018a104109642c56bf3b6aa07fd2ffd8f494915808ad80e92d9f5ef4ebe0`.
Source receipt: `.cache/met_ed_pa/source_preservation_audit_1.json`.
Original bytes, versions/physical pages, printed leaves, effective dates,
service/bills-rendered clocks, original/excerpt hashes and blocked routes remain
in the ledger and owner research notes.

Met-Ed's own district columns control: base RS11.25+.05138/kWh,
GS-S23.78+.05092/kWh, dated PTC, DSS, EEC, USC, SMT, DSIC, SPVRC, STAS, TCJA
and January refunds. PTC already includes its GRT/admin/loss/capacity/AEPS/supply
transmission components; separate non-bypassable DSS applies once. No wholesale
LMP, PLC, extra GRT or borrowed neighboring-district rate is added.

The retained official June12,2025 book's replacement Fourth Revised p213
supersedes the initial June1 DSS submission with the same effective date.
Met-Ed TCJA is **positive1.12% July–December2025**, restricted to base delivery;
2025 STAS is **+.02%**, including superseding January revision, versus2026
**−.02%**. DSIC excludes PTC/STAS, current sales tax follows STAS, and refunds
follow current tax. The January–May SPV credit applies to RS/GS-S DER; the
large-class self-generation waiver is not imported. Later DSS includes its
specified SPV recovery without a second standalone amount.

Supplement28 prints May30,2026; the retained official customer insert independently
extends the identical PTC through **May31** with the six-month rider clock.
Historical workbook June year-label errors are retained and reconciled against
adopted filings. No source discrepancy is silently corrected or treated as a new
rate. FE-ME emergency metadata and METED wholesale/load-zone labels remain
separate from utility district, retail supplier, tax jurisdiction and account
eligibility. The PJM proposal map proves only its METED label, not adoption of
proposed geography or a wholesale pricing node.

Independent literal source arithmetic in utility tests covers38 plan/month
benchmarks and individual tax/rider/refund stages; six fixed-flow CVXPY/SCIPY
cases verify numeric/symbolic parity. The private independent saved-study auditor
imports no production/test/rate/math helpers and re-computes all78 bills from
literal verified components and saved raw interval purchases. Maximum raw
component/bill difference is **$5.68e-14**; rounded
component cents reconcile, with no decimal cent ties. Refunds occur once per2025
scenario; all three January GS bills retain the exact exclusion. It also checks
native/import/history envelopes, state, CSV manifest pins and dispatch/SOC/power
balance. Maximum SOC recursion error is 1.26e-15kWh;
maximum power-balance error is 7.1e-16kW.
Receipt: `.cache/met_ed_pa/independent_audit.json`.

No actual customer whole-invoice calibration or exact provider quantity/cash
rounding rule was recovered. Official PTC comparisons validate a component,
not a whole invoice. Existing half-up component cents/unrounded primary proofs
are not a minimum rounded-cash invoice claim. The private audit initially used
an overly narrow aggregate annual objective tolerance; it now sums recorded
per-cycle tolerances and independently verifies the exact saved objective sum.
The matrix and frozen production artifacts were not changed to pass that audit.

## Targeted tests and historical/electrical acceptance

`tools/validate.py --tier focused` passed **262 tests in20.77s** (launcher21.08s),
no skips/failures, selecting the two Met-Ed test files plus
`test_regional_coverage.py`, `test_regional_validation_driver.py` and
`test_regional_counterfactual.py`. Coverage includes dated component arithmetic,
source integrity, native/history constraints, inactive minima, tax/completeness
and state, refund once, supported boundaries including October, DST, missing/
duplicate/naive/hourly data, provisional/unsupported-export rejection, form
serialization, queued worker, save and CSV/ZIP contents. Python AST, changed
JavaScript syntax and diff checks pass. After the display-only correction,
**14 directly affected integration tests passed in13.51s** (launcher13.78s).

One selected historical matrix ran on the frozen engine: **4 studies,12 scenarios,
78 monthly scenario bills and227,520 OpenDSS interval checks**, zero failed
intervals. This checks every interval in each selected case, not a sample within
a scenario. Full2025 and June2026 use explicitly retrieved ERA5 at hypothetical
Reading coordinates40.34,−75.93. Exact year/site responses and attribution are in
`.cache/met_ed_pa/weather/weather-input-manifest.json`; hourly reanalysis means
are held over fifteen-minute intervals, not measured subhourly weather. Native
loads are deterministic synthetic generic household/office shapes, not measured
or regionally calibrated. No silent fallback or missing-data backfill is used.

| Plan | Period | Grid / PV / PV+battery utility charges | Interval checks | Study ID |
| --- | --- | ---: | ---: | --- |
| RS | 2025-01-01–2025-12-31 | $2,620.71 / $1,861.56 / $1,585.10 | 105,120 | `0d6dbea9e9ce4694a3304d2151b356be` |
| RS | 2026-06-01–2026-06-30 | $252.23 / $159.78 / $129.33 | 8,640 | `07e34a967088468a88f1bad45f831ec9` |
| GS-S | 2025-01-01–2025-12-31 | $2,461.90 / $1,467.58 / $1,339.94 | 105,120 | `2bab656343a543efa1e54d2a6a462107` |
| GS-S | 2026-06-01–2026-06-30 | $219.33 / $109.28 / $97.33 | 8,640 | `cbfdd6fef522494fa591ac4b5a6c038b` |

GS-S2025 amounts are verified-component sums with the January exclusion above.
RS2025 has12 complete modeled cycles. June2026 both plans are complete within
scope. There is no all-month2026 electrical claim: June is the explicitly
selected2026 representative month; January–May/October component boundaries
are checked in unit arithmetic, and July–September rejects. Complete October
actual weather is unavailable on the research date; no October historical
OpenDSS pass or fabricated future weather is claimed.

Both plans use5kW DC/4kW AC PV,10kWh/3kW storage,initial5kWh,20–80%SOC,
95%charge/discharge efficiency and PV-only charging. Representative replay uses
120/240V split phase,25kVA transformer,100A service and0.95 lagging load PF;
these engineering assumptions do not alter billing PF or prove surveyed-site
adequacy/protection/interconnection. Scheduled ideal meter flows determine bills;
PCC losses/measurements remain separate diagnostics.

All52 selected optimized PV/PV-battery cycle primary proofs and26 battery-cycle
secondary minimum-cycling proofs pass;26 direct grid bills carry no optimizer
claim. Maximum objective/physical-dispatch reconciliation difference is
$1.000002×10⁻⁶, within recorded per-cycle proof tolerances; zero strict fallbacks.
Annual results use rolling per-cycle perfect foresight, carried SOC/refund/history,
and **no jointly optimized annual minimum**. Six annual scenario flags areFalse;
six single-month flags areNone. No actual-customer savings claim follows.

Launcher receipts: `.cache/met_ed_pa/acceptance_1/report.json`, JUnit/logs and
`regional/validation.json`, `validation-summary.json`, per-study requests/results,
CSV manifests and pinned driver copies. Tests+matrix launcher elapsed99.77s;
regional phase78.54s, matrix session74.82s, total worker-reported69.27s. These
are overlapping scopes, not additive active-development time.

No broad regional grouping, full workflow/release, GUI or unaffected historical
matrix rerun was selected: this is an isolated utility adapter/default/registry/
frontend addition with unchanged shared behavior/contracts. The small label fix
required affected form checks, not a second unchanged-engine annual matrix.
This is **targeted acceptance**, not a full-release pass or stable-promotion proof.

## API/artifacts and concise browser acceptance

Read-only loopback auditing passed all four matrix studies,52 table endpoints,
ZIP integrity/exact manifest and CSV bytes, complete bill/dispatch/credit/SOC/
electrical audit, and frontend pin1. Receipt `api_artifact_audit_1.json` retains
those original identities. A separately copied private preview store preserves
seed request/result bytes and uses the same immutable engine.

Browser acceptance on corrected frontend pin2 passed RS and GS-S: restore seed,
inspect account/history/supply/tax/calendar/PV/weather/battery settings, review,
submit, view comparison results, save a named result, return home and reopen.
RS special-demand/history25kW and GS qualification/history1500kWh were visibly
retained, with May2026 prior-history dates. The PTC label no longer displays
GSC-1 for Met-Ed. No browser operation timed out or stalled. No filechooser,
upload or download-event route was used; actual browser-download handling was
not asserted. CSV/ZIP download endpoints and saved bytes are proven separately.

| Plan | Browser-created/saved study | Grid / PV / PV+battery charges |
| --- | --- | ---: |
| RS | `645789beaaf54eb3983aac5d07fd30f2` | $252.23 / $159.78 / $129.33 |
| GS-S | `20993f98f8de4d7eb694f3e07843510a` | $219.33 / $109.28 / $97.33 |

All17 selected configuration groups, including every account field and electrical
service, exactly match their original seed request. All24 actual request fields
other than the display name also match exactly. Both new results pass artifact/manifest audit,
26 CSV endpoints and ZIP bytes, with17,280 additional all-interval checks and
zero failures. These browser reruns are separate from the227,520 matrix count.
Receipts are `.cache/met_ed_pa/browser_acceptance.json`,
`browser_observations.json`, `browser_restoration_audit.json`,
`browser_api_artifact_audit_1.json` and screenshots `browser_RS.png`/`browser_GS.png`.
The preview remains at `http://127.0.0.1:59165/`; no stable-store refresh occurs.

Browser-tool wait time was not separately instrumented, so no precise browser
wait/active-development-time claim is made. Overall wall time from orientation
to final preservation includes source research, implementation, tool waits and
checks; only the recorded launcher/worker durations above are test/simulation
runtime. Earlier utilities' reports, unresolved gaps and engine/frontend evidence
remain attributed to their original candidates.
