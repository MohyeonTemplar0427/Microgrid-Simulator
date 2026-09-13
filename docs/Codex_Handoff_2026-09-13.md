# Codex handoff — microgrid backend

Written 2026-09-13. Last code change was 2026-09-11 22:31 (`0bc5048`).
Working tree clean, `main`, **423 tests passing**.

Read this first, then
[docs/Microgrid_Backend_Architecture.md](Microgrid_Backend_Architecture.md)
before touching anything under `src/`. The architecture doc records decisions
you cannot infer from the code; this file records current state and open work.

---

## 1. Environment

```bash
/usr/local/bin/python3 -m pytest -q
```

**Use `/usr/local/bin/python3`, not `.venv/bin/python`.** The venv lacks
`opendssdirect` and `mysql-connector`, so 9 test files fail to *collect* there
and the suite looks broken when it isn't. The venv has `gridstatusio`, which
the system Python lacks — that only matters for the GridStatus.io adapter,
which imports it lazily.

Baseline is **423 passing** in ~6s. Fewer collected means wrong interpreter,
not a real failure. Check that before debugging anything.

Secrets live in `src/.env` (gitignored): `ELECTRICITY_MAPS_API_KEY`,
`GRIDSTATUS_API_KEY`, `PJM_API_KEY`. Never print, echo, or commit them.
**Tests must never call live APIs — mock the client.**

---

## 2. Layer map

Data flows strictly downward. No layer imports from one below it.

```
timeseries  →  profiles  →  surplus  →  billing
     (normalized interval table, then load/PV sources,
      then allocation + power balance, then tariffs/charges)

signal_pipeline (market + carbon providers)  ┐
dispatch (optimizer, scenarios)              ├→ simulation (Tkinter GUI)
opendss (QSTS replay, validation)            ┘
```

Public surface of the four backend layers, as exported today:

| Layer | Key exports |
|---|---|
| `src/timeseries` | `NormalizedIntervalTable`, `IntervalIndex`, `build_interval_index`, `build_interval_index_from_days`, `normalize_any_frame`, `to_legacy_columns`, `from_legacy_columns`, `align_to_index`, `convert_to_kw`, `validate_interval_table`, `MissingDataPolicy`, `PowerUnit` |
| `src/profiles` | `LoadProfileSource` / `PVProfileSource` base types; `CSVLoad`, `ConstantLoad`, `SyntheticLoad`, `BuildingArchetype`, `LoadScaling`; `CSVPowerPV`, `CSVCapacityFactorPV`, `SyntheticPV`; plus three *deliberately unimplemented* adapters (§6) |
| `src/surplus` | `allocate_surplus`, `SurplusConfiguration`, `default_surplus_configuration`, `GridExportCapability`, `FlexibleLoadCapability`, `ExportCompensationMode`, `validate_power_balance`, `validate_no_simultaneity` |
| `src/billing` | `calculate_billing`, `calculate_meter_billing`, `calculate_demand_peak`, `calculate_flat_demand_charge`, `assign_billing_periods`, `allocate_shared_generation`; `TariffDefinition`, `get_tariff`, `register_tariff`, `supported_tariffs`, `PGE_B10_SECONDARY_BUNDLED`, `PGE_B19_SECONDARY_MANDATORY_BUNDLED`; four topology builders (`single_pcc_topology`, `master_with_submeters_topology`, `individual_meters_topology`, `shared_generation_topology`) |

---

## 3. Conventions that are silent and costly to violate

These three cause wrong numbers with no error. They are the most common way
to break this codebase.

1. **Never compute intervals as `days * 96`.** DST days have 92 or 100
   intervals. Interval counts always come from the generated index
   (`build_interval_index` / `build_interval_index_from_days`).

2. **Use `pd.DateOffset(days=n)`, never `pd.Timedelta(days=n)`** for calendar
   arithmetic. `Timedelta` adds exactly 24h and drifts an hour across a DST
   boundary.

3. **Never sum demand charges across intervals.** Demand is one peak per
   billing month. Summing per-interval demand charges inflates the bill by
   roughly the interval count.

Two more from the architecture doc:

4. **PV-first allocation.** PV serves load before anything else; battery and
   export see only the residual. Don't reorder this.
5. **Tariffs are versioned data, not code.** Rates carry effective dates and a
   `source_url`. Add a new dated version; do not edit an existing one in place.

Date ranges from the GUI are **inclusive**; the interval index is
**exclusive** at the end. The conversion happens once, at the boundary —
don't apply it twice.

---

## 4. What landed on 2026-09-11

Five commits, ~8,000 lines, 45 files. Summary so you don't have to read the
whole diff:

- `d30274c` — `GridStatusIOProvider` (`src/signal_pipeline/providers/gridstatus_io.py`),
  registered in `region_config.py` and the providers registry. This is the
  workaround for the blocked PJM key (§7).
- `f0d9e27` — the four backend layers above, all created at once, each with
  tests; plus the 276-line architecture doc.
- `98c0849` — `.gitignore` only.
- `1fb3e80` — GUI CSV export: "Export Results CSV" button, integrated-CSV vs
  live-API mode switching, `run_integrated_csv_analysis`; matching plumbing in
  `interface_analysis.py`, `single_day_analysis.py`, `dispatch/config.py`,
  `market_data_integration.py`.
- `0bc5048` — PG&E B-19 (`PGE_B19_SECONDARY_MANDATORY_BUNDLED`) with source
  URL and 105 lines of new billing tests.

---

## 5. Integration status — read this before picking work

The four backend layers are **not** equally wired in. Verified by import
graph, not by assumption:

| Layer | Reached from production code? |
|---|---|
| `timeseries` | **Yes** — `interface_analysis.py` (`build_interval_index_from_days`), `time_series_analysis.py` (`normalize_any_frame`, `to_legacy_columns`) |
| `profiles` | **Yes** — `interface_analysis.py` (`BuildingArchetype`, `ConstantLoad`, `LoadScaling`, `SyntheticLoad`, `SyntheticPV`) |
| `billing` | **Yes** — `interface_analysis.py` (`calculate_billing`, `get_tariff`, both topology builders), `application_interface.py` (`PGE_B10_SECONDARY_BUNDLED`, `supported_tariffs`), `market_data_integration.py` (`calculate_flat_demand_charge`) |
| `surplus` | **No — imported only by `test/test_surplus_allocation.py`** |

So `src/surplus/` is fully built and tested (17 tests) but has **zero
production consumers**. `allocate_surplus`, the power-balance validators, and
the carbon monetization in `surplus/metrics.py` are unreachable from the GUI.
`src/dispatch/dispatch_scenarios.py` imports none of the four layers.

---

## 6. Open work, roughly in priority order

1. **Wire `surplus` into the analysis path.** The largest real gap. Decide
   where `allocate_surplus` belongs relative to the existing dispatch
   scenarios in `interface_analysis.py`, and route `validate_power_balance` /
   `validate_no_simultaneity` so violations surface instead of passing
   silently. This is the one item that unlocks the carbon monetization work
   already written in `surplus/metrics.py`.

2. **Demand-charge-aware optimization.** Billing computes demand correctly,
   but the optimizer does not *target* it. This needs a peak variable in the
   objective — a post-hoc addition of the demand charge after optimizing for
   energy will not produce the right dispatch. Non-trivial; treat as its own
   piece of work.

3. **`dispatch_scenarios.py` integration.** It still runs on the legacy path
   and imports none of `timeseries`/`profiles`/`surplus`/`billing`.

4. **GUI results surface.** `application_interface.py:563` still carries the
   placeholder "The completed workflow will provide visual comparisons and
   downloadable CSV outputs here." The CSV export is live as of `1fb3e80`;
   the visual comparison half is not.

---

## 7. Deliberately not implemented — do not "fix" these

Each raises a clear error on purpose, so no GUI control can silently produce
invented numbers. If you think one should be implemented, raise it with the
user first; the reasons are modelling decisions, not oversights.

| Thing | Where | Why |
|---|---|---|
| Measured load adapters (Green Button, Modbus, SunSpec, MQTT) | `profiles/load_sources.py:314` | Planned extension point; no hardware or utility-download connection exists. Use `CSVLoad` for exported data. |
| Weather-derived PV | `profiles/pv_sources.py:321` | Config validated, but no irradiance provider (PVGIS/NSRDB/PVWatts) connected. |
| Measured inverter PV | `profiles/pv_sources.py:357` | Inverter telemetry reports *delivered* power; recovering *available* power needs a curtailment signal. Unresolved modelling. |
| `ExportCompensationMode.TARIFF` | `surplus/configuration.py:79` | NEM / NBT not modelled. Use `fixed`, `csv`, or `none`. |

Note the B-10 and B-19 tariffs both raise on **export compensation**
specifically (`pge_tariffs.py:118` and `:252`) while supporting import
billing fully. That is intentional and follows from the row above.

**PG&E B-19 is now implemented** (as of `0bc5048`). Older notes listing it as
unimplemented are stale.

---

## 8. Ground rules

- **Re-read files before editing.** Claude works this repo in parallel; a
  file you wrote earlier is often stale by the time you return to it.
- **Never `git checkout` / `reset` / `restore` to resolve a conflict** with
  parallel work. Merge by hand or ask.
- **Don't stage, commit, or push unless explicitly asked.**
- New docs go in `docs/`.
- Don't rename `results/` files to strip historical `week*` names.
- Don't restore the Manual Operating-Point Tool button.

## 9. PJM API — known blocked, don't re-litigate

The user's PJM account is non-member (`Other [Other]`). Non-members must email
PJM's account manager confirming internal-use-only before the portal issues a
key; granting "PJM Public" in Account Manager is necessary but not sufficient.
Symptom: `apiportal.pjm.com` redirects to `tools.pjm.com` with no key anywhere.

Rate limits: **non-members 6 connections/minute**, members 600/minute. The PJM
adapter chunks at 30 days, so a multi-month request fires several calls in
quick succession and will need throttling between chunks if the key ever
arrives.

Working alternatives that exercise the same adapter path with no credentials:
`ercot_houston_hub`, CAISO. Or `pjm_western_hub_gridstatus`, which reaches PJM
through GridStatus.io with a self-serve key (free tier: 500k rows/month).
