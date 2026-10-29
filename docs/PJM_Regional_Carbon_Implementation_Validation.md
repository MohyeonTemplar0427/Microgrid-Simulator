# PJM regional carbon implementation and validation

October 29, 2026. Development on `main`, base HEAD
`e67597c00e1f8d2a504b117c729df59ea6208de5`. Pre-existing Penn Power changes are
preserved. No staging, commit, push, deployment or stable-engine promotion.

## Implemented scope

Optional Electricity Maps `US-MIDA-PJM` lifecycle consumption accounting for
schema 11 regional studies. The browser preserves the choice and shows
grid-import emissions and the accounting difference against the grid reference,
in kg CO2e, with provider/source/coverage/estimation provenance. It does not
change billing, optimization, export settlement or representative network physics.

See [implementation and browser use](PJM_Regional_Carbon.md) and
[verified data coverage](PJM_Carbon_Data_Coverage.md). Coverage is complete for
2025 and January 1–October 28, 2026, with 44 and 1,620 provider-estimated
intervals respectively. Full-year 2026 is unverified.

Affected implementation paths are `local_web/regional_carbon.py`,
`local_web/regional_study.py`, `local_web/static/regional.js`,
`local_web/static/app.js`, and the optional explicit accounting-basis arguments
in `signal_pipeline/electricity_maps_data.py`. Existing client callers retain
their parameter contract. New tests are `test_regional_carbon.py` and
`test_regional_carbon_browser.py`; the architecture documentation links this scope.

## Acceptance selection

Focused checks cover provenance/basis enforcement, DST, missing/duplicate/
invalid data, exact alignment and aggregation, source-cache integrity,
independent emissions arithmetic, unchanged dispatch/bills, no export carbon
credit, and shared-source tariff comparisons. Browser contract checks cover
serialization, restore settings, non-PJM exclusion, visible units/provenance
and missing values. Existing California-carbon and Electricity Maps tests
bound the shared client's existing behavior.

The workflow tier is required for the optional worker/artifact input and result
contract. Full release is not selected: no billing math, solver algorithm,
time-grid behavior, credit/state handling, PV/storage physics or electrical
replay changes. GUI tests and unrelated historical matrices remain excluded.
This is targeted acceptance, not a full-release or promotion pass.

## Frozen candidate and checks

The frozen development engine is
`8a3d6991efe8bc903535c407869fea98cce4b77c1d5ff17c6d86a62015db6388`.
`candidate_preacceptance_fingerprints_1.json` and `candidate_frozen_1.json` under
`.cache/pjm_carbon/` retain source/dependency/test/tool and frontend identities.
Workflow, historical studies and browser used this same engine; final source
and frontend bytes were rechecked. Earlier development receipts retain their
original frontend fingerprints rather than being relabeled.

- `focused_parent_1/report.json`: **51 passed**, new backend carbon and existing
  Electricity Maps/California carbon tests; pytest phase 14.19 seconds.
- `frontend-focused/report.json`: **5 browser contract tests passed**. The later
  estimated-count/resolution display edit reran its affected test successfully
  in `frontend-estimation/report.json`; this is one rerun, not a sixth unique test.
- `workflow_1/report.json`: **112 passed**, plus all **7 JavaScript syntax
  checks**. The first attempt could not bind localhost inside the filesystem/
  network sandbox (6 failures, 23 setup errors). Resuming the identical frozen
  selection with loopback access passed; both attempts remain recorded. The
  passing pytest phase took 141.12 seconds. No skipped tests in these selections.
- Python syntax, final diff and local documentation links passed. Tests use
  mocked providers and never fetch live historical carbon. Separate source
  verification and selected acceptance use the preserved real data.

## Selected historical acceptance

`historical_acceptance_1.json` records two freshly executed worker studies:

| Study | Scenarios | Cycle bills checked | OpenDSS intervals |
| --- | ---: | ---: | ---: |
| Penn Power RS, full 2025 | 3 | 36 | 105,120 |
| Penn Power GS-S, June 2026 | 3 | 3 | 8,640 |

Grid-only, PV-only and PV-plus-battery all passed exact input grids, independent
carbon dot products, interval/cycle/comparison reconciliation, the existing
bill/component/SOC/state audit and **all 113,760 selected OpenDSS intervals**.
No electrical sampling or audit bypass was used. These are cumulative scenario
timesteps, not independent test cases. The annual result remains rolling
cycle-by-cycle perfect foresight, not a jointly optimized annual optimum.

2025 RS emissions were 5,715.4098114 / 4,066.74489081647 /
3,465.80442308326 kg CO2e for grid / PV / PV-plus-battery respectively.
June GS-S emissions were 394.3352854125 / 180.573569881632 /
155.004985904819 kg CO2e. Each comparison uses the same signal across scenarios.
The annual source included 44 provider-estimated intervals; June included 84.

Prepared, exact-site/year ERA5 inputs and independently verified carbon archives
were reused. Annual source reuse needed no new HTTP requests; June needed two
exact boundary-day requests, with their original payloads retained. The two
new studies' bills and physical dispatch were also compared with preserved
Penn Power baseline artifacts: zero differences in charges and grid/battery
flows. This is an explicit invariance comparison; old evidence remains owned
by its original engine, not transferred to the new pin.

Historical acceptance elapsed 38.74 seconds, including preparation, queue,
worker and independent audit. Worker-reported runtimes were 30.94 and 4.32
seconds. These overlap the aggregate duration and are not additive CPU or active
development time. Full source-retrieval history has its separate receipt.

## API and browser acceptance

`api_audit_1.json` passed both historical studies, all **28 CSV endpoints**,
paged table metadata, exact saved bytes and ZIP manifests/content integrity.
The API inspection did not invoke browser download events.

One concise browser pass used `http://127.0.0.1:59168/` and the frozen frontend:
open the commercial seed, restore, inspect utility/account/dates and checked
carbon option, review all eight configuration steps, submit, inspect rendered
kg CO2e columns/source disclosure, save by name, return home and reopen.
The ordinary summary displayed emissions without enabling Show all columns.
Source zone, UTC coverage, 84/2,880 estimated intervals and provider/study
resolution were visible. There were **no stalled browser operations**.

Saved browser study: `6321c2adf8f645a9bc07c94944382299`, named
**PJM carbon browser acceptance**. All **25** request fields other than display
name exactly matched the seed, including carbon, account, weather, electrical
service and operating facts. Fresh retrieval and execution took 21.18
worker-reported seconds. It passed an additional 3 cycle bills, independent
carbon arithmetic and **8,640** OpenDSS intervals with zero electrical failures.
These are separate from the historical matrix's 113,760 count.

Receipts: `browser_acceptance_1.json`, `browser_restoration_1.json`,
`browser_api_audit_1.json` and `browser_results_1.png`, all under
`.cache/pjm_carbon/`. The combined API audit of the two seeds and browser result
passed **42 CSV endpoints**, their table metadata and matching ZIP bytes.
Actual browser download handling/file choosers were not exercised; endpoint
and saved-byte checks are separate evidence. Browser tool waits and active
development time were not separately instrumented.

## Retained limits

This is optional attributional PJM consumption accounting. It does not establish
state/utility/site-specific emissions, marginal or causal avoided emissions,
export emissions credits, carbon-optimized dispatch, onsite equipment embodied
emissions or hosted data redistribution rights. Full 2026 is unverified; the
verified archive ends October 28. Per-study completeness still rejects missing
or unavailable data, even inside a previously researched date range. Provider
estimates remain estimates and later source revisions require their own pin.

All existing tariff/eligibility/solver limitations remain in their utility
documents. Separate ComEd/schema 10 and older PJM/schema 8 contracts were not
expanded, MISO carbon is unsupported, native GUI tests were excluded, and no
full-release or stable-engine promotion pass is claimed. All changes remain
unstaged and uncommitted; no push, deployment or promotion was performed.
