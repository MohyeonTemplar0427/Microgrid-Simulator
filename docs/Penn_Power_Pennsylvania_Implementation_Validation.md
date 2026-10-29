# Penn Power Pennsylvania implementation and targeted validation

Recorded 2026-10-29T20:19:06.062845+00:00. Implements ordinary
**FirstEnergy Pennsylvania Penn Power district RS residential and GS-Small
(GS-S) default Price-to-Compare supply** in the shared backend/local browser.
Read [account and billing scope](Penn_Power_Pennsylvania.md), the
[source guide](utility_sources/penn_power_pa/README.md),
[source pins](utility_sources/penn_power_pa/sources.json) and independent
[delivery](utility_sources/penn_power_pa/delivery_research.md),
[supply](utility_sources/penn_power_pa/supply_research.md) and
[rules](utility_sources/penn_power_pa/tax_rules_research.md) reviews.

## Candidate and preservation

Checkout `/Users/junhayang/Desktop/EnergyEngineerSession/Microgrid_Simulator`,
branch `main`, HEAD `e67597c00e1f8d2a504b117c729df59ea6208de5`.
Frozen engine: `e1072cef6954d8304d6c3cc44b48eda0160555bf0455f5536181ad0e7c57d423`.
`regional.js` SHA256: `717ff3bb1a0f637901a05c5336e3a53ec313e413860379c5823169f8265223da`.
Full source/dependency/frontend/test/tool/configuration fingerprints remain at
`.cache/penn_power_pa/candidate_frozen_1.json`. No source/test/tool/frontend edit
followed that freeze; subsequent documentation/private receipts need no simulation
rerun. Earlier utilities' results retain their original pins.

New runtime modules: `src/billing/penn_power_pa.py`, `penn_power_pa_rates.py`;
new tests: `test/test_penn_power_pa.py`, `test/test_penn_power_integration.py`.
Registry, site/equipment defaults, native eligibility, counterfactual, browser
fields/labels, coverage and validation-driver hooks reuse existing components.
Shared billing math, dispatch/solver logic, time-grid/credit/SOC algorithms,
PV/storage physics, API/worker schema and OpenDSS replay behavior are unchanged.
Runtime prices/provenance are literal; no ignored cache or network dependency.

The baseline covers **2,109 files**. Only eight intended shared wiring/architecture
paths changed; the other **2,101 are byte-identical**. AGENTS.md, ignored CLAUDE.md
and Development_Validation.md are unchanged. Architecture preserves its old
contents as an exact prefix; all previous utility source/code/report files remain
preserved, including the separately recorded Met-Ed LEDC issue. Final HEAD/index,
file hashes, candidate, source pins, links and diff checks are recorded in
`.cache/penn_power_pa/final_preservation.json`. No staging, commit, push, deployment
or stable-engine promotion occurred. No GUI was opened. Prior preview stores were
preserved; Penn Power uses a separate development store on local port59167.

## Verified scope and limits

Executable intersections are **January2025–June2026 and October2026 complete
calendar service/bill cycles**. **July–September2026 DSIC is unverified and rejects**;
no prior/current/neighboring price substitution or unverified proration occurs.
Monthly charges stay whole; local fifteen-minute DST grids and all source clocks
remain explicit. Partial/shifted cycles and missing/duplicate/naive/hourly/
nonfinite data reject.

RS is one family unit per meter, solely residential, ordinary120/240V secondary
single-phase service with no same-meter business, farm or multiple-meter special
case. Mixed business does not inherit the neighboring districts'2000W allowance.
Independent inactive special-demand/ratchet confirmation and prior-eleven actual
15-minute peak bounds≤25kW accompany native/current import peaks≤25kW. The general
$2.25/excess-kW branch and75% prior-eleven excess ratchet remain outside this
inactive-charge domain. These restrictions do not establish eligibility from PV.

GS-S requires independently retained existing class without a demand meter,
actual usage, no fixed/imputed usage and native/import cycle energy≤1500kWh, plus
prior-twelve qualification bounds≤1500. Penn Power explicitly has the initial
1500kWh availability wording; existing two-consecutive-month reassignment is a
separate Company decision. Exact native/gross/NEM-net classification semantics
are not inferred. Conservative history envelopes carry between adjacent cycles.

**GSDS/hourly eligibility is separately sourced over all applicable qualifying
history.** Penn Power's provisionB includes its stated historical500kW,
otherwise-GP/TP and without-contract conditions. No twelve-month GSDS cutoff is
invented. Current small load or PV does not establish absence of mandatory HP.
Initial default PTC rejects without independent full-history confirmation/source;
HP/hourly, TOU, alternative suppliers and general demand transitions are unsupported.

A bounded two-route primary-source review resolved the apparent missing F clause:
retained official June2024 Original67 literally says **F. THREE-PHASE**; current
Original67 labels the same text **C. THREE-PHASE**, both January1,2024. Independent
normalized-body SHA256 matches
`b69c335423e63168301ed8b855e819d65ea988e9c2d7134de743fe8bd2480de2`.
The actual clause permits ordinary single phase and addresses phase/metering/
lighting-gear arrangements; no standalone F price is present. Ordinary one-meter
single-phase, no combined/three-phase gear, added transformer/capacity/fluctuating-
load fee, mixed-service separation or termination cases are accepted. Label-version
inconsistency stays recorded; no F meaning/zero was inferred from paragraph order.

**January2025 GS-S is a verified-charge subtotal.** Historical Penn Power rowGS
has a known GRT-inclusive$4.84 refund; currentGS-S alone does not prove that legacy
mapping. January requires independent evidence tying this established account to
the exact legacyGS-row entitlement, including explicitly labeled hypothetical
legacy-eligible accounts. Without it, JanuaryGS rejects rather than assuming a
refund/zero/mapping. Known current charges carry6% sales tax; the confirmed4.84
refund applies once afterward. Its unknown prior-refund sales-tax adjustment is
explicitly excluded, not assigned zero. AnnualGS totals retain that qualification.
RS uses its known6.19 refund once with independent entitlement/source. Refund
state remains separate and adjacent; no negative-refund bank settlement is invented.

State-only tax locality is independently outside Philadelphia/Allegheny, with
solely residential exemption forRS and ordinary fully taxable6% GS current tax.
No special exemptions/assistance/private contracts are enabled. ATSI market-zone
and FE-ATSI emergency control-area labels remain distinct from tariff district,
supplier, tax, utility territory and wholesale prices. The official emergency
row's OH state cell is preserved despite describing Penn Power; Pennsylvania
jurisdiction comes independently from the tariff. No node/ownership/LMP/PLC fee
is inferred from metadata or coordinates.

PV/storage needs already-active qualifying ordinary approved renewable NEM/
interconnection, metering, retained class/default supply and no Partial Services
Rider/special fees. Size/non-export does not prove approval or standby exemption.
Storage charges from PV only; no battery export, export credits/bank/cashout,
aggregation, standalone battery or Penelec-specific legacy facility clause is
implemented. Grid-only removes DER assertions while preserving qualification,
GSDS, refund and inherited state.

## Source arithmetic and independent proof

The source ledger retains **34 originals,93 checked-in excerpts,72 source-linked
renders and30 derivatives**. Sixty-nine renders are marked visually reviewed;
three are retained without that assertion, with review aids separately labeled.
All **279 reference hash checks/277 unique paths pass**. All1351 prior tracked
source files match the baseline. Ledger SHA256:
`c01c4dcd483c807425c64d05966444208a886d021edb44db28dca86eece1c534`.
Source receipt: `.cache/penn_power_pa/source_preservation_audit_1.json`.

All32 dated components use Penn Power's own columns. Positive1.59%TCJA July–
December2025 has a base-only basis. STAS is+.01% in2025/−.01% in2026; DSIC iszero
in2025 and January–March2026, +.16% April–June2026 and+2.40% October. Mandatory
LEDC applies to ordinary class billing units, not only individual conversions,
and enters DSIC/STAS/current-tax bases once. January–March2025 LEDC non-applicability
is a disclosed first-April-rate-window interpretation: no explicit Jan–Mar
zero-priced row was recovered and no April price/provisional zero is backdated.

Penn Power SPV is explicitly zero in January–May2025; no neighboring credit is
copied. Negative2025 RS monthly SMT−.01 and June2026 GS DSS−.00080/kWh remain
signed. Known current raw/component-cent charges below the customer amount reject
under a conservative inactive-minimum guard. Some zero-import2025 RS cases reject;
imports are not forced and refunds are not clipped. This guard does not replace
the full tariff minimum or prove exact printed monetary rounding.

Published PTC already includes GRT/admin/loss/capacity/AEPS/supply transmission/
reconciliation; nonbypassable DSS is separate once. Penn Power PTC1.0661 is not
HP GS-S1.0515, and neither loss factor is applied again to final PTC. The adopted
June2025 DSS replacement supersedes the initial high-precision submission.
Supplement28's literal May30 endpoint is retained; actual Penn Power December/
April inserts corroborate identical PTC throughMay31,2026. June2025's insert has
correct June prices but a wrong May2026 endpoint; filedNovember30 controls.
Workbook June-year header discrepancies are retained rather than used as dates.

Independent tests include38 literal monthly plan benchmarks, individual charge
bases, six fixed-flow numeric/symbolic CVXPY/SCIPY cases, source pins and negative-
SMT zero-import rejection without forced symbolic imports. The independent saved-
study calculator imports no production/test/rate/math helpers. It recomputes all
**78 bills**, source/rider/tax/refund stages, cents, full-history/legacy facts,
state/native/import bounds, manifest hashes and physical flows from saved data.
Maximum component difference is $2.84e-14; maximum
bill difference **$5.68e-14**, with no cent discrepancies
or cent ties. SOC recursion error≤1.31e-15kWh and
power-balance error≤6e-16kW. It ran once without
repairs;157 source/artifact file reads and hashes are retained in
`.cache/penn_power_pa/independent_audit.json`. No actual whole-customer-invoice
calibration or minimum rounded-cash invoice proof is claimed.

## Targeted tests and historical/electrical acceptance

**331 tests passed in47.46s**, no skips/failures (launcher phase47.83s), selecting
Penn Power unit/integration tests, directly affected Penelec and Met-Ed integration
tests, regional coverage, validation-driver and counterfactual tests. Boundary/DST/
missing data, eligibility/state/refunds, unsupported settlement/provisional input,
source/cent arithmetic, percentage-base corruption, form serialization, queued
worker, save/restore and CSV/ZIP checks pass. PythonAST, changed-JavaScript syntax
and diff checks pass; see `syntax_receipt.json` and `acceptance_1/` JUnit/logs.

One explicitly selected new-utility historical matrix passed **4 studies,12
scenarios,78 monthly scenario bills and227,520 OpenDSS interval checks**, zero failed
intervals. Every interval in every selected case is checked; no sampling or audit
bypass. Full2025 and June2026 use exact-site ERA5 at hypothetical New Castle/
Lawrence coordinates41.00,−80.35, with hourly means held over15-minute intervals
and Open-Meteo/Copernicus attribution. Native profiles are deterministic generic
synthetic household/office shapes, not measured or regionally calibrated.

| Plan | Period | Grid / PV / PV+battery utility charges | Interval checks | Study ID |
| --- | --- | ---: | ---: | --- |
| RS | 2025-01-01–2025-12-31 | $2,686.05 / $1,918.66 / $1,652.70 | 105,120 | `1a45d0fb1f0449e6b9f24fd1d18f54c2` |
| RS | 2026-06-01–2026-06-30 | $244.89 / $155.74 / $127.04 | 8,640 | `0f76ed3884dc4848a63defa5c378e8ea` |
| GS-S | 2025-01-01–2025-12-31 | $2,654.30 / $1,650.48 / $1,529.99 | 105,120 | `90435ae7349244d7a098201a709518b9` |
| GS-S | 2026-06-01–2026-06-30 | $230.80 / $120.39 / $107.96 | 8,640 | `152f638b207e4163b2b95295c6f7581d` |

RS2025 includes12 complete modeled cycles under the disclosed LEDC start-window
interpretation. GS2025 includes one January subtotal and11 complete ordinary
cycles for an explicitly legacy-refund-qualified hypothetical account. June2026
both plans are complete in scope. June is the selected2026 representative month;
other supported boundaries have unit arithmetic/source coverage, not an all-month
2026 electrical pass. October actual full-period weather is unavailable on the
research date; no October historical replay/future-weather substitution is claimed.
July–September DSIC gaps remain rejected.

Both plans use5kW DC/4kW AC PV,10kWh/3kW storage,initial5kWh,20–80%SOC and95%
charge/discharge efficiency. Representative replay uses120/240V split phase,
25kVA transformer,100A service and0.95 lagging load PF, separate from unity billing
PF. Scheduled ideal meter flows determine bills; losses/PCC measurements are
separate diagnostics, not surveyed-site/protection/interconnection validation.

All52 optimized PV/PV-battery cycle primary proofs and26 battery-cycle secondary
minimum-cycling proofs pass;26 direct grid bills make no optimizer claim. Maximum
objective/dispatch reconciliation is $1.000003e-06, within
recorded per-cycle tolerances; no strict fallbacks. Annual secondary sums differ
by about1.2e-5USD within propagated monthly tolerances. Six annual proof flags
areFalse; six single-month flagsNone: rolling per-cycle perfect foresight with
carried SOC/history is not a jointly optimized annual minimum or actual savings.

Launcher monotonic elapsed128.05s;
regional phase80.05s, matrix session75.95s,
worker total70.36s
are overlapping scopes, not additive active-development time. Browser waits and
active development were not separately instrumented. Receipts: `acceptance_1/`
`report.json`, JUnit/logs, `regional/validation.json`, `validation-summary.json`,
pinned driver copies and per-study request/result/CSV manifests.

No broad regional grouping, full workflow/release, GUI or unaffected historical
matrix was selected: this utility-specific addition leaves shared behavior/
contracts unchanged. This is **targeted acceptance**, not a full-release or
stable-engine promotion pass. Coupled old-utility checks establish regression
behavior only and do not resolve the separately recorded Met-Ed LEDC issue.

## API, browser and final receipts

Read-only local API audit passed all four matrix studies,52 exact CSV endpoints,
ZIP integrity/matching manifests and complete bill/dispatch/state/electrical
audit on the frozen pin: `.cache/penn_power_pa/api_artifact_audit_1.json`.
A separate preview preserves seed request/result bytes and uses the same engine.

One concise background browser pass passed both plans: restore seed, inspect
account/history/supply/calendar/PV/weather/battery, review, submit, view results,
save with name, return home and reopen. RS family-per-meter facts and25kW history,
GS1500kWh qualification and independent full GSDS-history source/confirmation,
May2026 prior-history dates, PV-only charging and historical ERA5 were retained.
June's separate January legacy-refund assertion is visibly false; annual true
legacy facts are covered by form serialization/worker/matrix checks, not an
extra annual browser run. No browser operation timed out or stalled. No upload,
filechooser or download-event route was used; actual browser download handling
is unasserted, with endpoint/saved-byte checks providing separate evidence.

Browser saved studies: RS `a293e09963354dbc8210175b89cdf0b6`
($244.89/$155.74/$127.04), GS-S `3fd01edd3cd94a1e89db505904410768`
($230.80/$120.39/$107.96). All24 actual request fields other than display name
exactly match seed settings, including every account and electrical-service field.
Both new runs pass all artifact audits,26 CSV endpoints/ZIP bytes and17,280
additional OpenDSS checks with zero failures, separate from the227,520 matrix
count. Receipts: `browser_acceptance.json`, `browser_observations.json`,
`browser_restoration_audit.json`, `browser_api_artifact_audit_1.json`,
`browser_RS.png`/`browser_GS.png`, all under `.cache/penn_power_pa/`.
The private development preview remains at `http://127.0.0.1:59167/`.
