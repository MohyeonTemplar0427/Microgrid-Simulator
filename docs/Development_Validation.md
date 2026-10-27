# Development validation

The local browser and shared backend are the active development targets.
Desktop GUI development is paused. Default runs do not open a native GUI;
the launcher never opens a browser, file chooser or download-event listener.
It does not retrieve external weather/prices or promote an engine.

Run from the repository using `/usr/local/bin/python3`:

```sh
# Inspect a utility-specific selection without starting checks or writing reports.
/usr/local/bin/python3 tools/validate.py --tier focused --test test/test_delmarva_md.py --test test/test_delmarva_integration.py --dry-run

# Routine utility work: select the affected utility and integration tests.
/usr/local/bin/python3 tools/validate.py --tier focused --test test/test_delmarva_md.py --test test/test_delmarva_integration.py

# Tooling/shared changes: explicitly select the affected area(s) or test nodes.
/usr/local/bin/python3 tools/validate.py --tier focused --area validation
/usr/local/bin/python3 tools/validate.py --tier focused --area billing --area dispatch
/usr/local/bin/python3 tools/validate.py --tier focused --test test/test_regional_dispatch.py

# Shared API/worker contract changes: offline HTTP/form/worker/electrical workflows.
/usr/local/bin/python3 tools/validate.py --tier workflow

# Shared-engine changes or release milestones: full regression and JS syntax.
/usr/local/bin/python3 tools/validate.py --tier release
```

Focused areas are `validation` (the default tooling checks), `regional`,
`billing`, `dispatch`, `electrical`, `profiles` and `web`. Area selection is an
explicit test-file grouping, not automatic proof that all dependants were
covered. Shared changes can require several groups or the release tier.
`--test` accepts repeatable repository test paths/nodes. For routine utility
work, prefer these explicit paths over `--area regional`, which includes the
other utilities. Workflow/release tiers cannot be narrowed with `--area` or
`--test`. Focused runs do not automatically add JavaScript syntax phases;
check changed JavaScript with the existing Node toolchain (for example,
`node --check src/local_web/static/regional.js`). Workflow/release tiers run
the configured JavaScript syntax checks automatically.

## Select validation by change impact

Routine utility additions and tariff updates default to **targeted utility
acceptance**, not the full release suite. This is a policy selection made with
the existing `focused`, `workflow` and `release` tiers; no new launcher tier or
sampling flag is introduced. Record affected paths, selected tests/scenarios,
coverage, exclusions and the reason for any broader run in the implementation
report. A focused acceptance pass must not be labeled a full-release pass.

| Change | Default checks |
| --- | --- |
| Utility-specific rates, eligibility or billing adapter | Utility-specific source/arithmetic/boundary tests, numeric/symbolic parity, dispatch/state reconciliation and directly affected integration tests |
| Utility registration, default site, catalog or browser account fields with unchanged shared behavior | Above, plus affected form serialization, queued-worker, saved-settings/CSV/ZIP checks and changed-JavaScript syntax checks |
| Shared API/worker contracts or workflow impact not bounded by targeted tests | Workflow tier plus affected utility tests; add full release when shared-engine behavior or cross-utility impact requires it |
| Shared billing math, dispatch/solver algorithms, time grids, credit/state handling, PV/storage physics or electrical replay affecting multiple utilities | Full release plus relevant cross-utility historical matrices |
| Release milestone, before stable-engine promotion, explicit user requirement, or failures/uncertain impact requiring broader regression | Full release and explicitly selected historical acceptance matrices |
| Documentation or commit message | Text, local-link and diff checks; no simulation reruns |

Touching a shared registry file does not alone require full regression. Determine
whether the edit changes shared behavior or only adds a bounded utility entry.
Tests must still cover direct consumers and any changed contract; a file-count
heuristic is not an impact assessment. This policy never waives an explicit
user-required tier or acceptance check, and validation does not authorize
staging, committing, pushing, deployment or stable-engine promotion.

### Utility acceptance safeguards

Preserve verified effective dates, units, eligibility, supply/delivery/rider/tax
separation, independent bill benchmarks and itemized reconciliation. Exercise
rate boundaries, timezone/DST, missing/duplicate data, unsupported settlement and
account/state rejection. Check numeric/symbolic billing parity, optimized
dispatch, SOC/credit continuity, reported proof limits and saved artifacts.
New billing expressions can alter dispatch even when the shared architecture is
unchanged; targeted validation must cover those effects.

Use affected checks while editing. On the finished frozen candidate, normally
run **one explicitly selected new-utility historical matrix**, covering grid-only,
PV-only and PV-plus-battery across the supported rate regimes. Include full-year
billing/dispatch validation where verified coverage permits and the acceptance
scope calls for it. Reject coverage gaps rather than manufacturing an annual
case. Do not rerun unaffected utilities' historical matrices, or repeat passing
suites/matrices without a change, failure or unresolved concern.

Interval checks are cumulative scenario timesteps, not independent test cases.
The current regional driver and worker check every OpenDSS interval in each
selected case. Keep that normal final-matrix coverage when it is inexpensive.
A smaller electrical sample requires a recorded reason, selected dates/scenarios
and interval counts, and explicit **sampled electrical coverage** labels. Use
supported case selection, not an audit bypass or an invented sampling option.
Shorter studies do not establish full-year billing/dispatch or an all-interval
annual electrical pass. Never silently subsample an annual case or relabel old
electrical evidence as belonging to a changed candidate.

Default runs exclude `test_application_interface.py`,
`test_desktop_application.py` and `test_graphical_interface.py`. This is a
reported scope exclusion, not a GUI compatibility pass. Shared backend and
browser tests remain included. `--include-gui` explicitly opts into desktop
compatibility testing when it is requested. Raw `python -m pytest` still has
its original all-tests behavior; the launcher does not change global pytest
collection. Local API tests need permission to bind loopback sockets.

## Reports, deadlines and phase resume

Without `--output`, each invocation gets a fresh ignored
`.cache/validation_runs/<timestamp>-<id>` directory. It prints that path.
Reports must stay inside this checkout's `.cache`; no secrets/environment
values are copied into them. A directory cannot have two launcher writers.

`report.json` records the tier, exact commands, excluded GUI modules, Python
and dependency versions, source-derived engine ID, frontend/test/tool hashes,
phase status and elapsed time. Logs and JUnit XML have unique attempt names;
earlier attempts are retained. Pytest records its twenty slowest tests. A
zero-test result, failure, deadline, interrupted process or mid-run source
change cannot become a passing report. No browser acceptance is claimed.

```sh
/usr/local/bin/python3 tools/validate.py --tier focused --area regional --output .cache/validation/my-change
/usr/local/bin/python3 tools/validate.py --tier focused --area regional --output .cache/validation/my-change --resume
```

Resume requires identical source, tests, tools, frontend, dependencies and
selection. Passed test/syntax phases are reused only if their saved log/XML
fingerprints still match. Failed or damaged phases rerun with new attempt
files. Changed source or selection requires a fresh output directory; do not
relabel earlier evidence as belonging to a later candidate.

Default pytest deadlines are 180 seconds for focused, 600 for workflow and
1,200 for release; `--timeout` explicitly overrides this per-phase budget.
JavaScript checks have a 30-second budget. Heavy phases run sequentially.
On expiry the launcher first sends SIGINT so fixtures/queue owners can clean
up, then escalates termination after a bounded grace period. Logs remain
available. These POSIX process/lock controls target local macOS and Linux.

## Historical matrices and case resume

Long historical studies are opt-in. Existing cached, year/location-matched
inputs are required; the launcher has no input-download flag. All utility
eligibility, coverage and authoritative bill/physical audits remain in the
existing regional driver. No solver proof or OpenDSS check is relaxed.

Historical matrices are selected according to the impact policy above. They do
not require the full release tier for every utility addition: a focused utility
selection can include `--regional` with prepared inputs, for example:

```sh
/usr/local/bin/python3 tools/validate.py --tier focused --test test/test_delmarva_md.py --test test/test_delmarva_integration.py --regional --utility delmarva_maryland --period custom --start-date 2026-05-01 --end-date 2026-09-30 --inputs .cache/delmarva_md/weather --output .cache/validation/delmarva-targeted
```

This example is targeted partial-year acceptance, not a full-release or annual
claim. Choose dates, plans and prepared inputs appropriate to the task. Checks
inside every selected case and the resume contract below remain unchanged.

```sh
/usr/local/bin/python3 tools/validate.py --tier release --regional --utility dominion_energy_north_carolina --plan 1T --period monthly --inputs .cache/regional_historical_inputs/weather_20261015_final --output .cache/validation/release-candidate
# Same selection and output; resume does not resolve already verified cases.
/usr/local/bin/python3 tools/validate.py --tier release --regional --utility dominion_energy_north_carolina --plan 1T --period monthly --inputs .cache/regional_historical_inputs/weather_20261015_final --output .cache/validation/release-candidate --resume
```

The launcher forwards the driver's repeatable `--utility`, `--plan`, `--period`,
custom date bounds, `--include-va-history`, `--include-ciep` and `--ciep-inputs`.
For AEP Ohio, `--aep-rate-zone ohio_power` or
`--aep-rate-zone columbus_southern` selects the explicit legacy retail district
for its historical matrix. The option requires AEP Ohio in a `--regional`
selection and enters the immutable execution and request identity. It does
not infer a district from the site or pricing node; other utilities' requests
remain unchanged. Use a separate output directory for a different district.
`--allow-we-duke-provisional` explicitly selects and accepts the documented
We Energies/Duke Indiana 2025 rate assumptions. It is off by default, enters
the immutable execution/resume selection, and does not enable other utilities
or extend verified coverage. Use We Rg1/Rg2/Cg1/Cg6 or Duke RS/CS for annual
2025 validation; Duke TOU was not available in January. The artifact audit
requires the exact assumption model, affected components, values and warning.
For custom dates, use `--period custom` alone. CIEP requires its verified
private price file, not a substitute hub. See
[regional validation](Regional_Validation.md) for exact prepared input paths
and historical coverage restrictions.

The matrix phase always re-enters the driver on resume, even if the launcher
previously recorded success. Each case must match its engine, validator,
prepared request and saved artifact hashes, then pass an independent bill,
SOC/flow/state and electrical-results re-audit before it is reused. Reuse
does not run the optimizer/OpenDSS again. Failed, interrupted, missing or
modified cases receive new study IDs; original attempts remain recorded.
Changed inputs/selection/validator require a fresh output folder. Older
manifests without this resume contract remain readable evidence but cannot
be silently upgraded to resumable acceptance.

Case timing records input preparation, queue/worker wait, the worker-reported
runtime when available, and artifact audit time. Matrix sessions separately
count executed/reused cases and their elapsed time. Solver and OpenDSS timing
are not separately inferred from these aggregate measurements. Queue wait
can overlap worker runtime; do not add them as independent CPU measurements.

`--case-timeout` defaults to 2,100 seconds and requests cancellation on expiry;
the ordinary worker's existing 30-minute run limit is unchanged.
`--matrix-timeout` defaults to 3,600 seconds for the entire matrix phase. The
direct driver also supports `--execute --resume --case-timeout ...`.

## Candidate acceptance

Select checks using the change-impact policy above. Use focused checks while
editing and workflow checks for shared API/worker contract changes. Freeze the
candidate before final targeted acceptance and its selected historical matrix;
run the full release tier when a full-regression trigger applies, not automatically
for every utility addition. Finish those checks before browser acceptance. Perform
one concise manual browser acceptance pass only when UI behavior changed,
including new provider/plan/account-field wiring.
Record its actual engine/frontend identity separately. A CLI-only tooling
change does not require launching the browser. Report any blocked UI action
as unverified; API/ZIP checks cannot establish that a browser click succeeded.


## Verification recorded October 17, 2026

The unchanged engine was
`9e84bc5be182dabec955247f35e7b80bc5b609fb13348d2b2b089e8c8df73ae7`.
The release tier passed 2,779 tests with one skip, excluding the three GUI
modules above, and all seven JavaScript syntax checks. The real Caddy HTTPS
test was skipped because `MICROGRID_TEST_CADDY` was not configured. Total launcher wall
time was 343.36 seconds; its pytest phase was 342.30 seconds. Evidence is in
`.cache/validation_launcher_release_20261017/report.json` and the adjacent
attempt logs/JUnit XML. No GUI or browser acceptance was run for this CLI-only
change, and no engine was promoted.

A cached July 2025 Dominion North Carolina residential 1T study passed the
ordinary isolated worker and independent artifact audit. Its grid-only,
PV-only and PV-plus-battery scenarios each passed all 2,976 representative
OpenDSS intervals. The first launcher session took 42.26 seconds, including
15.01 worker-reported seconds. Resume took 25.16 seconds including startup
and summary work; its case re-audit took 0.11 seconds. Resume kept the same
study ID, submitted zero new simulations, and reused the passed test phase.
The report and case receipts are under
`.cache/validation_launcher_smoke_20261017/`. These times are overlapping wall
measurements, not additive CPU or active-development measurements.
