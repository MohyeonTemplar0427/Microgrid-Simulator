# DTE integration handoff · October 19, 2026

Main began clean at `de0aabf`. All work remains unstaged and uncommitted. No push, deployment, engine promotion, origin change or desktop-GUI work was performed. README was not edited.

## Final candidate and evidence

Engine: `6b40dd83bf178c808b3bb5cf20c9fb6d0b60d2c10a98afd17c335e9c6f24448a`.
Browser: [http://127.0.0.1:19047/#32ec677455424d268f2cc9f02a1960af](http://127.0.0.1:19047/#32ec677455424d268f2cc9f02a1960af). Web UI v1.0.1 is unchanged.

Frontend `regional.js` SHA-256: `a0a2b0eb2b562cab6b96a0347a9dd8d033e5d64ef01d3dc803f7046f86662b38`. Other frontend fingerprints, source/tests/tool hashes and dependency versions are retained in `.cache/dte_final_regional_2/report.json`.

- Final focused regional + validation-tool regression: **1,139 passed**; pytest 226.78 s, launcher pytest phase 227.22 s. GUI modules excluded. Twelve SciPy notices concern forwarding the native HiGHS MIP feasibility option in sub-mWh geometry fixtures, not inaccurate accepted bills.
- Final source-manifest verification: **1 passed**, 2.19 s, `.cache/dte_source_manifest_check/`.
- Unchanged frontend: seven syntax checks passed in the earlier full release; final `node --check src/local_web/static/regional.js` and `git diff --check` passed.
- Final historical matrix: **9 studies, 27 scenarios, 324,552 checked electrical intervals**, no failed/unevaluated intervals. All 111 cycle outcomes were direct bills or proven primary optima; minimum cycling was proven for all 37 battery cycles. Largest objective/bill reconciliation difference was approximately $0.000001.
- One concise browser pass verified DTE/MISO identity, plan selection, dated coverage and sources, configuration restore, submission/rerun, three rendered scenarios, save/name and reopen. Restored request matched the API seed exactly before naming; all rerun bills matched. Browser operation stalls: **0**. API-verified ZIP: 14 entries; screenshot and receipt are `.cache/dte-browser-results.png` and `.cache/dte_browser_acceptance.json`.

The earlier full release at engine `d22f47475d9d0e6e9dc1ab68e3303f05a2456260a424e8a34b4b7f908c6f439c` passed **3,140 tests, 1 skip**, plus seven JavaScript syntax checks (pytest 531.56 s). The skip was the opt-in Caddy HTTPS integration; one PECO solver warning occurred on a bounded attempt before its acceptance checks passed. That release preceded the DTE floating-point EWR cutoff fix and is **not** relabeled as final-candidate evidence. Its report remains `.cache/dte_release/report.json`. The final candidate reran all affected regional checks and the entire DTE historical matrix.

## Historical results

All amounts below are recurring utility bills. Weather is exact-year archived ERA5; native loads and accounts are explicit synthetic/hypothetical studies, not measured customer evidence. No exports, installation costs or carbon signal. Billing components and savings are retained in each folder’s `period-components.csv`.

| Plan | Period | Grid only | PV only | PV + battery |
|---|---|---:|---:|---:|
| D1.11 | 2025-01-01–2025-12-31 | $1,958.22 | $1,294.90 | $949.38 |
| D3 | 2025-01-01–2025-12-31 | $14,358.40 | $12,251.83 | $12,222.71 |
| D3.11 | 2025-06-01–2025-12-31 | $8,581.32 | $7,267.74 | $7,194.52 |
| D1.11 | 2026-03-01–2026-03-31 | $187.46 | $125.74 | $94.30 |
| D3 | 2026-03-01–2026-03-31 | $1,376.72 | $1,174.08 | $1,167.94 |
| D3.11 | 2026-03-01–2026-03-31 | $1,360.33 | $1,159.88 | $1,153.66 |
| D1.11 | 2026-09-01–2026-09-30 | $188.15 | $125.83 | $92.40 |
| D3 | 2026-09-01–2026-09-30 | $1,366.23 | $1,169.66 | $1,166.93 |
| D3.11 | 2026-09-01–2026-09-30 | $1,428.99 | $1,216.63 | $1,201.07 |

Residential inputs: 2-kW peak reference household shape (9,258.36 native kWh in 2025), 5-kW DC PV/4-kW AC inverter, 10-kWh battery with 3-kW charge/discharge limits, initial/final 5 kWh. Commercial: 20-kW peak office shape (79,878.22 native kWh in 2025), 10-kW DC/8-kW AC PV, 30-kWh battery/8-kW power, initial/final 15 kWh. Both use south-facing 30° tilt, 14% system loss, 96% PV inverter efficiency and the shared effective ESS efficiencies/SOC bounds in the saved request. Wear is reported but excluded from dispatch by default. Calendar cycles are hypothetical; fixed charges apply once per confirmed full monthly cycle.

Residential replay is a representative 25-kVA/100-A 120/240-V split-phase circuit; commercial replay is the existing balanced 480-V/750-kVA reference. These are not DTE service specifications or surveyed wiring. There are no network constraints in dispatch and no transient validation. Historical perfect foresight is per billing cycle with continuous SOC, not a proven annual joint optimum.

Browser acceptance used a separate September 2026 commercial D3.11 **clear-sky** case, explicitly disclosed in its warnings, rather than claiming to repeat the historical weather matrix in the UI. Browser bills were $1,428.99 / $1,141.34 / $1,124.99; those are not the archived-weather September row above.

## Reproduction and retained provenance

See [DTE scope](DTE.md), [source manifest](utility_sources/dte/manifest.json) and [validation policy](Development_Validation.md). Prepared weather is private local cache, not a Git fixture:

- 2025: `.cache/dte_historical_inputs/`; weather SHA-256 `c42c308237cb2f5b8be2df531456b342cd1d0fa88ae83640a13a41d83aeaa84f`.
- 2026: `.cache/dte_historical_inputs_2026/`; weather SHA-256 `82058bf16047c244cf1eb53a1d0862b4dd967a0230a3a0ba887b9014ac93687c`. Retrieved with existing `fetch_era5("2026-01-01", "2026-09-30", 42.28, -83.73)` and verified by `parse_era5` on the exact local 15-minute study grid. Do not shift years or overwrite revised data under an existing checksum.

```sh
/usr/local/bin/python3 tools/validate.py --tier focused --area regional --area validation --timeout 600
/usr/local/bin/python3 tools/run_regional_validation.py --execute --utility dte_electric --plan D1.11 --plan D3 --period annual --inputs .cache/dte_historical_inputs --output .cache/dte_repeat_annual
/usr/local/bin/python3 tools/run_regional_validation.py --execute --utility dte_electric --plan D3.11 --period custom --start-date 2025-06-01 --end-date 2025-12-31 --inputs .cache/dte_historical_inputs --output .cache/dte_repeat_tou
/usr/local/bin/python3 tools/run_regional_validation.py --execute --utility dte_electric --period custom --start-date 2026-03-01 --end-date 2026-03-31 --inputs .cache/dte_historical_inputs_2026 --output .cache/dte_repeat_march
/usr/local/bin/python3 tools/run_regional_validation.py --execute --utility dte_electric --period custom --start-date 2026-09-01 --end-date 2026-09-30 --inputs .cache/dte_historical_inputs_2026 --output .cache/dte_repeat_september
```

Final historical evidence is in `.cache/dte_validation_final/{annual_2025,tou_2025,march_2026,september_2026}/validation.json`, with saved requests/results, dispatch, itemized bills and AC CSVs. `.cache/dte_validation_final/acceptance.json` aggregates checks. Timings in `batch.json` are wall-clock measurements per run, not CPU or active development time; do not add worker wait to worker runtime.

## Scope and remaining work

- D1.11/D3: January 2025–September 2026; D3.11: June 2025 onward. Actual billed PSCR after September 2026 is absent from the retrieved table; authorized maxima are not substituted.
- Complete 26–35-day regular cycles and confirmed full monthly fixed charges only. One complete meter cycle crossing months/rate changes is tested numerically; the generic validation driver’s custom mode splits dates into calendar cycles. A February 15–March 17 driver attempt was therefore correctly rejected as two unsupported partial cycles, before simulation. Rejected receipts remain in `.cache/dte_validation/crossing_2026/`; they are not counted as completed studies.
- DER requires independently confirmed Category 1 Rider 18, approved sizing/storage and conservative aggregate ≤20 kW. Zero exports and zero opening credits only. Standalone storage, larger DG, standby, legacy NEM and export-credit settlement remain unsupported.
- Commercial D3/D3.11 have energy charges and EWR consumption-band fees, not measured demand charges. Capacity is bundled, so no extra MISO capacity/transmission/PLC charge is added.
- MISO configuration separates LRZ7 resource adequacy, ITC Transmission and an optional explicitly sourced cpnode. No live MISO market feed, wholesale optimization signal or MISO carbon model is implemented. No default hub or California carbon is substituted.
- Account eligibility, ordinary tax/locality facts and full monthly charge applicability are user assertions. Independent filed-arithmetic benchmarks passed; no actual DTE customer statement calibration is claimed.
- Review and merge through Git when requested. Do not copy changes into the browser clone or promote/deploy this candidate automatically.
