# Southern California implementation handoff — 2026-09-17

Main development folder: `~/Desktop/EnergyEngineerSession/Microgrid_Simulator`; main branch. No files copied from the browser clone. No commit, staging, push or public deployment.

## Delivered and remaining scope

The existing browser/queue/worker supports LADWP R-1A/R-1B/A-1A/A-1B/A-2B/A-3A and SCE D/TOU-D-4-9/TOU-D-5-8/PRIME/TOU-GS-1-E/D/TOU-GS-2-D/TOU-GS-3-D/TOU-8-D within the explicit account restrictions in [Southern_California.md](Southern_California.md). CEC location resolution, generation selection, billing, battery optimization, itemized tables, PV diagnostics, configuration reuse and CSV exports are connected.

This is **not the complete requested solar settlement extension**. NEM/NBT, credit-bank/true-up accounting and automatic climate-region geography remain unfinished. Solar is confirmed non-export only; climate region is bill-confirmed. Unsupported CCA, voltage, special riders and historical dates are blocked. Historical weather and equipment catalog controls are not wired into schema 6; its clear-sky PV calculation does reuse the existing physical model. No GUI application change was made (this request targeted the existing browser).

Do not infer completion of those remaining items from a green test suite or the engine pin upgrade.

## Engine upgrade

The existing preview is `http://127.0.0.1:8876/?review=socal`, using `/tmp/microgrid-municipal-browser-review`. It was idle before restart; all eight prior saved studies remain.

- Previous pin: `75d3c93b3c597f4a9f7844b8ed3e45c16eb503d0a409011eb2ecc793e889faac`.
- New pin: `00a262a1b8c2cc6151ba0e0b7d5b9506e8cdae6d1412ff0a141834ed48f0a2f6`.
- Tariff-data version: `socal-2026-09-17.1`.
- Upgrade used the existing `--refresh-engine` mechanism. Prior pointer backed up as `engine-before-socal.json` in the same preview data directory; old immutable engines and saved results were retained.
- Candidate: port 8877, `.cache/socal_candidate`, same final pin. Other local servers, the separate browser clone, and `.cache/local_web_pipeline` were not upgraded.

The preview's data directory is temporary; this preserves the pre-existing launch arrangement, not a production deployment decision. Python engine snapshots include source and dependency/Python fingerprints. Frontend assets follow the existing server's static asset mechanism.

## Actual browser verification

All examples are explicitly hypothetical, use public coordinates and assumed account qualifications, and do not claim verification of an actual customer bill. July 1–31, 2026; zero local-tax assumption.

| Case | Browser result | Candidate saved study |
|---|---|---|
| LADWP residential R-1B, 5 kW DC clear-sky PV, storage | Grid $167.827808; PV $95.803871; PV + storage $50.145426 including degradation | `3091201e9c5b42988b14df9c66651866`; repeated on later candidate as `53a12165b7f34968adc6fe662a649397` |
| SCE residential PRIME, same daily load assumption and PV/storage | Grid $259.570332; PV $157.981666; PV + storage $64.688856 including degradation | `5a2261542ca4420f892e9b64c09cd442` |
| SCE TOU-GS-1-E, constant 10 kW, no equipment | $2,372.801400; independently calculated in test | `6022ac4cb53640c996ceafbe5dfb1ce1` |
| LADWP A-1A, constant 10 kW, prior 11 peaks 20 kW | $2,168.732000; independently calculated in test | `1ba0f87cd3b442c9acb3c3a109f62f52` |
| Downtown LA / Santa Monica | Ambiguous overlaps preserved; LADWP/SCE respectively offered for explicit confirmation or hypothetical comparison | Saved CEC evidence in candidate store |
| Pasadena, 34.1478/-118.1445 | Pasadena Water & Power and MWD unsupported; no LADWP/SCE fallback | Browser inspected |
| SCE + CCA + actual service | Explicit unsupported-CCA message before advancing/submitting; no false bill attestation | Browser inspected; API rejection also tested |

Initial browser verification exposed hidden cost columns, stale alerts, an account-mode restoration collision with load mode, and municipal form visibility interfering with SoCal controls. These were corrected and configuration reuse rerun. The final presentation metadata comes from the backend. Grid-only runs now emit only the grid-only scenario; earlier candidate saved results retain their original repeated comparison rows.

After upgrade, the existing SF historical B-6 result `95c1f1eb32ce415e9dd20c432c8c2b7c` remained readable with its original engine identity and tables.

## Validation

Use `/usr/local/bin/python3`.

- Independent R-1A tiers/adjustments/minimum, R-1B DST, SCE D tiers/baselines, SCE GS-1 energy and demand, and LADWP facilities-ratchet bill calculations.
- Shared bill/optimizer objective reconciliation and power/SOC constraints.
- TOU boundaries, official holidays, independent quarterly versions, unsupported dates, complete 15-minute coverage, explicit UTC offsets, missing qualification history, climate-region confirmation, export rejection.
- CEC agency identity/boundaries/unsupported providers and retained manual-override evidence.
- Actual CCA cannot be relabelled bundled through the API; mismatched location/site class rejected.
- Real local HTTP submission, durable queue, immutable-engine worker, saved request, result metadata, itemized CSV.
- Full regression and focused compatibility results recorded below after final completion.

## Research retained for further solar work

SCE's public EEC Pacific-time workbook was located and downloaded for review, with SHA-256 recorded in the source manifest. It includes 2023/2024/2025/2026 vintages and non-locked-in prices. It is **research only**, not yet part of the pinned bill model. NBT monthly energy-only EEC offsets, separate ACC Plus offsets, current amended carry-forward/true-up and net-surplus adjustments must be implemented together before enabling the option. Do not treat a raw hourly export price as complete settlement.

Final checks: **1,082 passed** in the full suite; **26 passed** in the SoCal-specific suite; **112 passed** in the focused browser/API/municipal compatibility suite before the last additional rejection test. `git diff --check` passed. macOS Tkinter tests require normal desktop access; the initial sandboxed run aborted in Tk initialization, then the complete suite passed with desktop access.

Post-upgrade live browser run: SCE D, hypothetical region 6/basic, constant 1 kW for July 2026, no PV/storage or local tax. Study `ff7e79ec87af473fad9e49ec1e95a7cc` on port 8876 completed on engine `00a262a1b8c2`; bill **$293.681414**, matching the independently calculated test; objective reconciliation error **0**. Grid-only display correctly contains one scenario row.

## Residential refinement upgrade — September 19, 2026

Supersedes the SCE residential coverage and engine pin above. See `Southern_California.md` and `validation/SCE_Residential_Refinement.md`.

- Runtime tariff version: `socal-2026-09-19.1`; 20 verified historical residential versions cover 2025. January 1–June 24, 2026 remains a gap.
- Final engine: `4c5b37576b5b8a86e1197db7ce4a6f8550374aed0bbe555482f5db0e9a8e8c19` on ports 8876 and 8878.
- Port 8876 still uses `/tmp/microgrid-municipal-browser-review`; port 8878 uses `.cache/sce_history_candidate`. Both were idle before refresh. Prior pointers backed up as `engine-before-residential-refinement.json`; all prior immutable engines and results retained.
- Live final study: `6f75d90188994dd1974f72f62a571014`, November 2025 Santa Monica TOU-D-4–9 with storage. Completed; grid bill $184.633165; objective reconciliation error 0. Prior SF study `95c1f1eb32ce415e9dd20c432c8c2b7c` remains readable.
- Full tests: 1,106 passed. Additional final focused checks: 49 passed plus the local HTTP test passed with loopback permission.
- Browser restoration/run tested. Corrected outdated SCE date help and restored battery-only choice enablement. New optional climate-credit field requires bill confirmation; apartment profile selects multifamily basic charge.
- Cross-rate/season allowance and minimum allocation remains an explicit approximation. No export settlement, automatic climate-credit eligibility, or multi-cycle credit ledger. CCA and new municipalities deferred.
- Main branch, no commit or push; existing work preserved.

## Early-2026 residential gap filled — September 19, 2026

The preceding gap notes are superseded: D, TOU-D-4–9, 5–8 and PRIME now cover January 1, 2025–September 17, 2026 continuously. Commercial coverage is unchanged. See `utility_sources/socal/history_2026/README.md` for explicit cancellation chains and the March 20 / June 25 rule review.

- Tariff data `socal-2026-09-19.2`; engine `dc35d428ca013098e67f93a04875fa656babd7aa9eb0d49feeb5c6c487eb1b44`.
- Full regression: **1,128 passed** in 61 seconds, `/usr/local/bin/python3 -m pytest -q`.
- 16 API/queue/worker simulations completed: four plans × January, March DST, June 1–24 and May/June battery boundary cases. Reconciliation errors below $0.005; see `validation/sce_2026_gap_fill.csv`. These are constant-1-kW synthetic validation loads, not average household forecasts.
- Ports 8878 and 8876 refreshed only after idle checks, with prior pointers backed up as `engine-before-2026-gap-fill.json`. Existing saved results and old engines preserved. Other servers and independent browser clone untouched.
- Main preview study `498b3b48ea26446890aa40ccb92d2466`: January 2026 SCE D, synthetic 1 kW / region 6 basic / no local tax. Completed bill $295.18572, matching independent test. Original SF historical result still readable.
- Main branch; no commit or push. Existing allocation and credit-ledger limitations remain.
