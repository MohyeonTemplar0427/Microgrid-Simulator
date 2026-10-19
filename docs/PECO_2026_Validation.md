# PECO 2026 validation

Coverage is January1,2025–October19,2026; see [dated tariff sources and supported account scope](PECO.md). This report adds actual-year2026 weather validation; the [previous2025 evidence](PECO_2025_Validation.md) retains its original candidate and was not relabeled.

Frozen candidate: `13d38dc7d5d1299d5cc5dd16bf49f76f0ee7f0adeb51d723f85709ecf3868a28`. Stable engine was not promoted; nothing was staged, committed, pushed or deployed.

## January–September2026 bills

| Billing option | Grid only | PV only | PV + battery |
|---|---:|---:|---:|
| R | $1,599.17 | $1,051.77 | $767.20 |
| R-TOU | $1,604.66 | $965.30 | $656.10 |
| GS | $9,695.48 | $8,386.47 | $7,957.64 |
| GS-TOU | $10,673.52 | $9,127.78 | $8,066.57 |

These are nine-month totals, not full-year2026 estimates or measured customer bills. Native load, weather and equipment are byte-identical between standard/TOU options within each customer class. Wear is reported separately and excluded from utility-bill optimization.

## Inputs and checks

- Service dates January1–September30,2026; nine hypothetical complete calendar meter cycles, America/New_York,15-minute interval averages. Native demand is the existing synthetic household/office profile (2/20kW peak), not measured or regionally calibrated.
- Hypothetical Chester County site39.96,−75.60, independently confirmed PECO territory/default supply. Residential sales-tax exemption and ordinary commercial6% PA tax; tests independently also check Philadelphia8%. No personal customer data.
- Exact2026 ERA5 hourly reanalysis through Open-Meteo; hourly radiation means shifted to interval starts and held on the15-minute grid. Not on-site measurements or measured15-minute irradiance. Original request, raw response, retrieval time, units and hashes stay in the private cache.
- Residential PV5kW DC/4kW AC and storage10kWh/3kW (initial/final5kWh); commercial PV10kW DC/8kW AC and storage30kWh/8kW (initial/final15kWh). Shared tilt30°, azimuth180°,14% losses,96% inverter efficiency. Approved non-export/grid charging are explicit hypothetical assumptions.
- Rolling-cycle historical perfect foresight with continuous SOC; no joint annual optimality or operational-forecast claim. No capital costs, export compensation, wholesale LMP or extra capacity/transmission tag charges.
- Representative OpenDSS replay:25kVA120/240V split-phase residential;750kVA480V balanced three-phase commercial, lightly loaded by the20kW office. Replay load PF .95lagging, separate from unity billing PF; circuit losses/PCC measurements do not change billing flows. Not site-specific or transient validation.
- All 108 scenario-cycle bills reconcile; 72 dispatch cost proofs and 36 minimum-cycling proofs passed. All 314,448 interval electrical checks converged and passed. Maximum objective/rebilling difference: 0.0000010000USD.
- Independent decimal benchmarks cover January, April, May, June, July and September for all four plans; old2025 bills remain regression-tested. Exact effective-date checks cover January/April/June/July/October; DST and PJM holidays include ordinary Friday July3 versus Saturday July4.
- Separate September20–October19 cycles verify1.05% DSIC applied to the whole distribution subtotal plus STAS by bill date, without splitting the GS demand peak. Both residential and commercial TOU cross-cycle requests also pass production form serialization → API → pinned worker → electrical replay → save/restore/CSV/ZIP checks. These deterministic clear-sky fixtures are separate from the actual-weather nine-month matrix.
- Cycles crossing non-DSIC component changes, partial/extended cycles, RS-2 exports, competitive supply and special eligibility remain explicitly unsupported; no invented allocation or future-rate extrapolation.

## Evidence and timing

Regional and validation-tooling regressions: 943 passed, seven JavaScript syntax checks passed. GUI tests deliberately excluded. Launcher `.cache/peco_2026_final/report.json` retains exact commands, environment/dependency fingerprints and phase timing; matrix `.cache/peco_2026_final/regional/validation.json` retains request/source/result hashes and independent artifact audits.

| Plan | Study ID | Worker seconds | Result SHA256 |
|---|---|---:|---|
| R | `bad8dcc34bb249d5b3b721e8c78d3d75` | 24.42 | `714f13021bf872becded5bea90b10912bcbb271a2dabde85e7628495b12fe7df` |
| R-TOU | `acc6fd50e6484cdaab7c336f86d01d56` | 27.09 | `a44b2fbf744f6d37fafadf02506d56176907443a102757e5b009f0cf39dad03e` |
| GS | `c33d9133157b4b7d95b99d4c162f3ff8` | 31.58 | `984af948feb2d4147623bef6a46ef346a69b9f98173cb048644e37a30559e81a` |
| GS-TOU | `51bbaa900a2943699cca32faad7a4502` | 25.45 | `be3b1322bbce5021f43225646d31cc5beda8599e05c1bafb5601c0ce793b9293` |

Matrix wall time: 116.02s. Worker times include solver and OpenDSS replay and may overlap other checks. They are not active-development measurements.

Weather payload SHA256: `67a64b695b76d0b3d0316513cfef4be8faabb09e630462708cfb9e20a85fff13`.

Use the explicit preparation/execution commands in [PECO.md](PECO.md) with fresh ignored output folders. No cache/year substitution or public downloads of private inputs. The CSV is an aggregate; interval data and saved JSON remain in the local study store.

## Local-browser acceptance

The same frozen candidate ran at `http://127.0.0.1:19043/` in a separate preview
store. The acceptance pass verified PECO coverage/source information,
September2026 dates, deferred naming on Save result, saved-result reopen,
restored configuration and browser submission. The rerun
`953a0f47e5c640dbba6beffa62cb0f18` completed with byte-identical comparison CSV
results; only the unsaved study name differed. All three scenarios passed
representative OpenDSS checks. The separate residential/commercial preview API
cases also verified four saved CSVs and the 14-entry ZIP contents without browser
download-event automation. No browser operation stalled.

Private evidence: `.cache/peco_2026_development/browser_acceptance.json`,
`preview_api.json` and `browser-results.png`. The save operation changed only the
preview store; immutable matrix requests and artifacts were preserved.
