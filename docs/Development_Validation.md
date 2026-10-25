# Development validation

The local browser and shared backend are the active development targets.
Desktop GUI development is paused. Default runs do not open a native GUI;
the launcher never opens a browser, file chooser or download-event listener.
It does not retrieve external weather/prices or promote an engine.

Run from the repository using `/usr/local/bin/python3`:

```sh
# Inspect commands and coverage without starting anything or writing reports.
/usr/local/bin/python3 tools/validate.py --tier focused --area regional --dry-run

# Fast iteration: explicitly select the changed area(s), or an individual test.
/usr/local/bin/python3 tools/validate.py --tier focused --area validation
/usr/local/bin/python3 tools/validate.py --tier focused --area billing --area dispatch
/usr/local/bin/python3 tools/validate.py --tier focused --test test/test_regional_dispatch.py

# Offline HTTP/API, form serialization, queued-worker and electrical workflows.
/usr/local/bin/python3 tools/validate.py --tier workflow

# Broad backend/browser regression plus JavaScript syntax checks.
/usr/local/bin/python3 tools/validate.py --tier release
```

Focused areas are `validation` (the default tooling checks), `regional`,
`billing`, `dispatch`, `electrical`, `profiles` and `web`. Area selection is an
explicit test-file grouping, not automatic proof that all dependants were
covered. Shared changes can require several groups or the release tier.
`--test` accepts repeatable repository test paths/nodes. Workflow/release tiers
cannot be narrowed with `--area` or `--test`.

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

```sh
/usr/local/bin/python3 tools/validate.py --tier release --regional --utility dominion_energy_north_carolina --plan 1T --period monthly --inputs .cache/regional_historical_inputs/weather_20261015_final --output .cache/validation/release-candidate
# Same selection and output; resume does not resolve already verified cases.
/usr/local/bin/python3 tools/validate.py --tier release --regional --utility dominion_energy_north_carolina --plan 1T --period monthly --inputs .cache/regional_historical_inputs/weather_20261015_final --output .cache/validation/release-candidate --resume
```

The launcher forwards the driver's repeatable `--utility`, `--plan`, `--period`,
custom date bounds, `--include-va-history`, `--include-ciep` and `--ciep-inputs`.
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

Use focused checks while editing, workflow checks when wiring APIs/contracts,
then freeze the source and run the required release/matrix checks. Perform
one concise manual browser acceptance pass only when UI behavior changed.
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
