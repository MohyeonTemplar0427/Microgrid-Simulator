# PECO 2025 validation

This is a reproducible synthetic account study, not reconciliation to a measured customer bill. See [implemented scope and official sources](PECO.md).

Accepted candidate: `9fa0274eb6c74f7fa1e600653b3e509ebbc9c80b2c28ecb90693bf31df6d8831`. No stable engine promotion, commit, push or deployment.

## Annual utility bills

| Billing option | Grid only | PV only | PV + battery |
|---|---:|---:|---:|
| R | $1,953.45 | $1,325.60 | $991.39 |
| R-TOU | $1,963.98 | $1,237.59 | $852.14 |
| GS | $11,828.82 | $10,424.15 | $9,887.88 |
| GS-TOU | $12,965.52 | $11,349.84 | $10,082.29 |

Standard and TOU use byte-identical physical inputs within each customer class. TOU is not automatically cheaper: the modeled office pays less on standard GS even with storage. Bills exclude installation costs and separately reported battery wear.

## Inputs and limits

- Inclusive local service dates: January1–December31,2025; twelve explicit hypothetical complete calendar meter cycles, America/New_York,35040 fifteen-minute interval averages per scenario. Native load is before PV/storage.
- Site: hypothetical PECO ordinary account at39.96,-75.60, Chester County; state-only6% commercial sales tax, residential exemption. Territory and enrollment are explicit assumptions, not coordinate-derived findings.
- Native loads: existing deterministic synthetic household/office shapes,2/20kW peaks. Annual native consumption is9258.3576/79878.216kWh. No customer, appliance, hourly-from-monthly or regional calibration claim.
- PV: residential5kW DC/4kW AC; commercial10kW DC/8kW AC; tilt30°, azimuth180°,14% system losses,96% inverter efficiency. Available annual AC solar6928.276809/13856.553617kWh. Actual output preserves optimized curtailment.
- Weather: actual-year ERA5 hourly reanalysis via Open-Meteo; requested39.96,-75.60, native grid40.0,-75.5. Existing adapter holds hourly means on the15-minute grid with documented meteorological timing approximations. This is not an on-site observation or measured15-minute solar series.
- Storage: residential10kWh/3kW, initial/final5kWh; commercial30kWh/8kW, initial/final15kWh; shared SOC/efficiency settings retained in the private requests. Grid charging is explicitly assumed approved; no export or export credit. Wear estimate0.03USD/kWh of charge-plus-discharge throughput is excluded from the primary objective.
- Monthly perfect foresight with linked SOC; every PV and storage primary optimum is proven for its modeled cycle. All48 storage minimum-cycling refinements are proven. These are not joint annual optimum proofs or operating forecasts.
- Representative electrical replay: residential25kVA120/240V split phase; commercial shared750kVA480V balanced three phase. The commercial reference is lightly loaded by this20kW office; it is not a surveyed or sized service design. Replay assumes0.95 lagging load PF separately from unity billing PF (no billed PF penalty). Losses and replay PCC measurements do not change scheduled retail bills.
- All144 scenario-month bills reconcile; all420480 interval power-flow checks converge and pass. No voltage, line/transformer, setpoint or inverter capability violations. Maximum optimizer/numeric bill difference is 0.0000010000USD. CSV contains component-independent aggregate diagnostics.

## Candidate-specific evidence

| Source pin | Checks | Result |
|---|---|---|
| `62c8724c3743` | Broad non-GUI regression, before final date guard and evidence metadata | 2896 passed, 1 skipped |
| `56f60e6fcf44` | All regional regression after date guard | 890 passed, 0 skipped |
| `9fa0274eb6c7` | Final PECO/evidence/form-worker/coverage checks | 120 passed, 0 skipped |

Earlier runs remain attributed to their original source pins; they are not relabeled as accepted-candidate evidence. Seven JavaScript syntax checks also passed on unchanged frontend bytes. GUI tests were deliberately excluded. Final annual matrix ran on the accepted pin; private manifest `.cache/peco_2025_accepted/validation.json` retains request/result/validator hashes and independent audits.

| Plan | Study ID | Worker seconds | Result SHA256 |
|---|---|---:|---|
| R | `e5574f1626de4b50936efc068f404b4c` | 33.76 | `6ef46e816d384f11351c9ffe7217708f8ce63a6bffc7e17a8f6a99369f61817c` |
| R-TOU | `13557b06090b420cbf104507206d845c` | 37.13 | `220c89c9fb3824bb2aaf5935e3ee2438814e765d998bd57a058d20b2ed941fd0` |
| GS | `64892d9b692a4838bfd1820a84dda6b2` | 39.32 | `428e2aad2d207321993b38f485129cf76fafc62bd2dbbbb3c31265f655c2ae3a` |
| GS-TOU | `2dc249c341ad4c7c8f5b85a53118445f` | 33.79 | `d756af4bd17d54dead591fba62de3c5956c927cec9f1beddb414f43d5da68db6` |

Final annual matrix elapsed 152.79s; worker times include solver and electrical replay. Timings can overlap other tests and are not active development time. Browser acceptance and its timing are recorded separately.

## Reproduce

Use the commands in [PECO.md](PECO.md), selecting a fresh ignored output folder. Current accepted evidence uses `.cache/peco_2025_accepted`. Source archives and inputs are never silently replaced. CSV reports are aggregates; interval weather/dispatch/electrical files remain private in the ignored study store.

## Browser acceptance

Accepted pin `9fa0274eb6c7`, local preview `http://127.0.0.1:19042/`. Residential and commercial standard/TOU choices, source links, eligibility and 2025 coverage were inspected. Residential save/name/reopen and full settings restoration passed. Browser submission `9c4c300bec294712a3a06ec67298c2f2` completed; API readback confirmed every restored input was unchanged except the draft name. Verified-rate labels and all three commercial electrical summaries rendered correctly. Comparison/component/electrical CSV and ZIP bytes were checked through API endpoints (14 ZIP entries); no browser download-event or file-chooser waits were used. No browser operation stalled. Screenshot and API acceptance hashes remain under `.cache/peco_development/`.
