# Alliant Iowa implementation and validation

This document preserves the **initial 2026 candidate's** scope and evidence.
The later [2025 history and validation](Alliant_Iowa_2025_Validation.md)
extends coverage; the limitations below describe the original engine pin,
not the newer candidate. Earlier results keep their original fingerprints.

Reviewed October 25, 2026. This is a local-browser candidate for Interstate
Power & Light in Iowa, not Wisconsin Power & Light. See
[billing scope and official sources](Alliant_Iowa.md) and the
[source ledger](utility_sources/alliant_ia/sources.json).

## Implemented scope

The shared retail registry, bill calculation, dispatch objective, browser
configuration, queued worker, saved results and electrical replay support:

| Class | Schedules |
| --- | --- |
| Residential | 400 seasonal, 407 two-part TOD, 427 three-part TOD |
| Small commercial | 600 seasonal, 607 two-part TOD |

Complete verified component coverage is **June 1–October 31, 2026**, for
complete calendar billing cycles at consecutive **15-minute** intervals.
Coarser averages reject because they can conceal the quarter-hour net inflows
and outflows used by the filed IO metering rules. The bill includes daily customer charges,
seasonal/TOD energy, the dated EAC, EECR, DRCR and RTS factors, and the explicitly
confirmed unincorporated Linn County tax case. Numeric bills and CVXPY
optimization use the same expressions. These five schedules do not levy
customer maximum-demand charges; DRCR is an energy rider.

The filed-CST TOD interpretation is disclosed and requires account
confirmation. The actual July 4 holiday is excluded from summer peak pricing;
another utility's observed-holiday calendar is not imported. Location,
distribution utility, supplier, rate eligibility, tax jurisdiction and
interconnection remain separate facts. The browser uses its existing dynamic
regional controls and shows the dated scope and source links.

The grid-only counterfactual clears DG-enrollment metadata. PV cases require
explicit ordinary Inflow–Outflow eligibility and interconnection/sizing
assertions and constrain exports to zero. The hypothetical account does not
prove an actual site's eligibility. No export compensation or credit ledger
is implemented by this addition.

## Historical-weather comparison inputs

The reproducible comparison covers **June 1–September 30, 2026**, four complete
calendar cycles, for every schedule and the same three scenarios: grid only,
PV only, and PV plus battery. It is not a full-year study.

| Input | Residential / commercial assumptions |
| --- | --- |
| Weather point | 42.10 N, 91.46 W, representative rural Linn County |
| Weather | Historical Open-Meteo ERA5 hourly reanalysis, prepared separately from tests |
| Interval grid | 15 minutes, `America/Chicago`, offset-aware timestamps |
| Native load | Imported synthetic household / small-office shape, 3 kW reference rating |
| PV | 5 kW DC, 4 kW AC inverter, south-facing, 30-degree tilt |
| Conversion assumptions | 14% system losses, 96% inverter efficiency |
| Battery | 10 kWh, 3 kW charge/discharge, 95% charge and discharge efficiencies |
| SOC | 50% initial, 20–80% bounds, continuous across cycles, final restoration |
| Operation | Approved hypothetical non-export connection and grid charging |
| Objective | Utility bill; degradation excluded from dispatch, reported separately at $0.03/kWh throughput |

ERA5 is reanalysis, not a station measurement. Its preceding-hour means are
held across four quarter-hour steps; these are not measured 15-minute weather
observations. Native load is synthetic, not customer data or a calibrated
regional reference model. Each schedule's scenarios share the same native
load and available PV inputs.

Dispatch has perfect foresight within each billing cycle. Rolling-cycle
optimization and its secondary minimum-throughput refinement do not establish
an annual optimum or an implementable forecast-based control policy. Both
the itemized utility bill and the separately reported wear cost are retained.

## Electrical assumptions

Every scenario is replayed at every 15-minute interval through the shared
OpenDSS quasi-static workflow. Residential service uses the representative
25 kVA, 120/240 V split-phase transformer and 100 A service. The commercial
case uses a representative 75 kVA, 240 V single-phase service with a 400 A
service limit. These small examples remain inside the adapter's declared
single-phase scope; no three-phase facility is implied.

Replay checks convergence, voltage, line and transformer loading, inverter
capability and scheduled-setpoint consistency. Losses and replay PCC flows
remain separate from the scheduled flows used for billing. The circuits do
not represent a surveyed site and provide neither dynamic validation nor
network constraints inside optimization.

## Reproduction

Prepared weather and simulation stores are ignored private artifacts. The
weather manifest records the retrieval, coordinates, source and content hashes
under `.cache/alliant_weather_rural/weather-input-manifest.json`. Tests do not
make live provider requests or load credentials.

```sh
/usr/local/bin/python3 tools/validate.py --tier focused \
  --test test/test_alliant_ia.py \
  --test test/test_alliant_integration.py

/usr/local/bin/python3 tools/validate.py --tier focused \
  --test test/test_alliant_integration.py \
  --test test/test_regional_coverage.py \
  --test test/test_ameren_il.py::test_account_region_central_clock_and_existing_clocks \
  --regional --utility alliant_energy_iowa --period custom \
  --start-date 2026-06-01 --end-date 2026-09-30 \
  --inputs .cache/alliant_weather_rural \
  --output .cache/alliant_2026_matrix_15min --timeout 180 --matrix-timeout 1200

/usr/local/bin/python3 tools/validate.py --tier release \
  --output .cache/alliant_release_15min --timeout 1200
```

Use a fresh output directory for a new candidate. Resume is valid only when
the recorded fingerprints and prepared inputs match. The final engine pin is
`0d77f10e36016eca9bab0fa4382bbc9d5f5ecbfe37882c6b42e70fc0d8e6388d`;
`.cache/alliant_candidate_frozen_final.json` also records source, frontend,
test, tool and configuration hashes. GUI tests are excluded by policy.

## Verified historical-weather results

The final matrix passed all five studies on the frozen engine above. These
are **four-month hypothetical operating bills**, including the declared
taxes; they are not actual customer bills or installed-system payback results.
Residential native consumption was 4,639.58 kWh and small-office native
consumption was 4,023.68 kWh. The synthetic examples are not claims about
average Iowa households or businesses.

| Schedule | Grid only | PV only | PV plus battery |
| --- | ---: | ---: | ---: |
| 400 residential seasonal | $922.30 | $621.36 | $520.89 |
| 407 residential two-part TOD | $928.23 | $619.53 | $487.53 |
| 427 residential three-part TOD | $920.95 | $598.45 | $445.56 |
| 600 general service seasonal | $973.51 | $517.26 | $467.55 |
| 607 general service TOD | $992.50 | $518.12 | $441.27 |

The 15 scenario results contain 60 complete cycle bills and **175,680
OpenDSS interval checks**. Every interval converged and passed the declared
electrical limits. All 20 battery-cycle cost optima and minimum-throughput
refinements were proven within recorded solver tolerances. Maximum
bill/objective reconciliation difference was less than $0.0000011; power
balance and SOC-recursion errors were below 2e-15 in their respective units.
Exports remained zero. These are bill and schedule consistency checks,
not validation against actual customer statements.

The final launcher receipt is
`.cache/alliant_2026_matrix_15min/report.json`: 31 focused integration/coverage
tests passed, followed by the five-case matrix. The regional phase took
77.42 seconds wall time; its driver recorded 73.47 seconds. These timings
cover overlapping queue/worker execution and artifact audits, not development
time. Earlier receipts retain their original engine pins and are not
relabeled as final-candidate evidence.

The backend release suite passed **4,152 tests, with one skip**, plus all seven
JavaScript syntax checks. Pytest reported 735.65 seconds; the launcher recorded
737.43 seconds for the complete release run. The skipped real-HTTPS hosting
test requires an explicitly configured, verified Caddy binary. The three GUI
test modules were excluded by policy rather than counted as that skip.
Evidence: `.cache/alliant_release_15min/report.json`.

Browser acceptance then found that the shared interval selector still offered
30 minutes for Alliant. The frontend now reads each plan's `interval_minutes`,
disables unsupported options, validates that selection before advancing, and
restores the other workflows' options when leaving. It preserves the selected
value rather than silently resampling inputs. The changed frontend and its
additional regression test passed **186 focused tests** in 69.72 seconds
(70.07 seconds for the phase), plus `node --check` and `git diff --check`.
Evidence: `.cache/alliant_frontend_interval_final/report.json`.

That correction changed only frontend/test files. The release and historical
matrix retain their original full fingerprints in their reports and in
`.cache/alliant_candidate_frozen_backend_release.json`; their backend engine
and simulation evidence remain unchanged. The final frontend/test fingerprint
is `.cache/alliant_candidate_frozen_final.json`, including `regional.js` SHA-256
`622d8a7384d2427e35742cf42266e2b0b951fa77c1811a8d9ffa84b89e342cdc`.

Saved-result HTTP checks independently reopened all five completed studies,
verified their candidate IDs and Alliant catalog, compared every one of the
65 CSV downloads byte-for-byte with disk, and checked all five ZIP bundles
for CRC integrity, matching result manifests and matching CSV hashes. The
served index, JavaScript and stylesheet also matched the frozen files. The
receipt is `.cache/alliant_api_artifacts_final.json`.
The earlier check took 3.35 seconds; repeating it through the running preview
after the frontend correction took 1.55 seconds. The earlier receipt is kept
as `.cache/alliant_api_artifacts_backend_release.json`.

Final browser acceptance verified the 427 account identity, supported dates,
15-minute-only choices, restored native CSV and historical ERA5, submission,
rendered bills/electrical results, naming only when saving, and reopening from
Recent studies. The new request matched the original exactly except its saved
name, and all itemized bills matched. The worker took 12.34 seconds. The saved
result is `8a1beed6ec0444d7984755341ad6253c`; the receipt and screenshot are
`.cache/alliant_browser_acceptance.json` and
`.cache/alliant-browser-acceptance.jpg`. The visible version remains
**Web UI v1.0.1**.

The acceptance window was 255.29 seconds, including the frontend correction,
its focused tests, API/worker execution and work between calls. The reported
browser-call wall times summed to 9.96 seconds, excluding the initial browser
inventory/documentation calls. No browser timeout, stalled operation or
upload/download event wait occurred. These are elapsed-time measures, not
active development time, and overlapping runtimes must not be added as if
they were sequential work.

## Remaining limits

Full-year 2025 lacks complete verified historical rider intersections and
application dates. Earlier isolated EAC or base prices do not fill those gaps.
There is no Alliant provisional-rate mode. Shifted, partial and crossing
cycles reject pending the applicable allocation rules. October 2026 is
covered by numeric billing benchmarks, not by this June–September
historical-weather matrix.

Other tax jurisdictions, larger/demand tariffs, Wisconsin service, export
settlement and standalone storage require separate implementation. The stable
engine and the independent web-browser clone have not been promoted or
changed. Nothing is staged, committed, pushed or deployed by this work.

For the separate population question, see the
[PJM population estimate](PJM_Population_Coverage.md). Alliant Iowa is in MISO
and contributes zero additional PJM population coverage.
