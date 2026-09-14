# Codex handoff — PV modelling, 2026-09-14

Supplements [Codex_Handoff_2026-09-13.md](Codex_Handoff_2026-09-13.md). Read
[CLAUDE.md](../CLAUDE.md) first.

**Nothing below is committed.** It sits in the shared working tree alongside
your GUI work. Suite: **644 passing** (was 469 at the last handoff).

Claude owns `src/profiles/`. You own `src/simulation/` and the GUI tests —
untouched here, and no reference to any of this leaked into them. `src/opendss/`
was not touched either; electrical feasibility is later work.

---

## What is new

Four new backend modules, all in `src/profiles/`. Every one is offline unless
you explicitly ask for a network fetch.

| file | what it does | tests |
|---|---|---|
| `weather.py` | canonical weather frame: validation, units, alignment | — |
| `pv_model.py` | **Phase 1** — generic PVWatts-style array | 51 |
| `pv_equipment.py` | **Phase 2** — named CEC module + inverter, real strings | 76 |
| `nsrdb.py` | NSRDB satellite weather adapter | 46 |

`pvlib==0.15.2` is pinned in `requirements.txt`. Its CEC module and inverter
databases ship as CSV inside the package, so equipment lookup needs no network.

---

## The one thing that matters for the GUI

Both PV phases are `PVProfileSource` subclasses and both answer the same
question, so a mode selector can swap them without changing what any
downstream number means:

```python
source.build_pv_available_kw(interval_index) -> pd.Series   # existing contract
```

`pv_available_kw` is the maximum nonnegative AC real power available after
inverter conversion and equipment clipping, **before operational
curtailment**. Dispatch still owns `pv_output_kw = pv_available_kw -
pv_curtailed_kw`.

For a results tab, call `build_detailed()` instead. It returns the same series
plus everything behind it, and the most recent result is also left on
`source.last_result`, so the simple path still gets the detail afterwards:

```python
result = source.build_detailed(interval_index)
result.pv_available_kw       # pd.Series, the optimizer-facing number
result.diagnostics           # per-interval power stages, timestamp aligned
result.warnings              # tuple[str, ...] — surface these verbatim
result.provenance            # dict — how the profile was made
```

Phase 2 adds two more, both keyed by name:

```python
result.subarray_diagnostics  # "<inverter unit>/<subarray>" -> frame
result.inverter_diagnostics  # "<inverter unit>" -> frame
```

`diagnostics` is one row per interval, aligned to `IntervalIndex.index`, safe
to plot or join directly. Phase 2 columns:

```
timestamp, solar_zenith_degrees, solar_azimuth_degrees,
plane_of_array_irradiance_w_per_m2, effective_irradiance_w_per_m2,
estimated_cell_temperature_c, pv_module_dc_power_kw,
pv_dc_after_system_losses_kw, pv_dc_at_inverter_input_kw,
pv_ac_before_clipping_kw, pv_inverter_clipping_kw, pv_available_kw,
pv_inverter_night_tare_kw
```

Phase 1 carries the same set minus `pv_dc_at_inverter_input_kw`,
`effective_irradiance_w_per_m2` and `pv_inverter_night_tare_kw`. The stages
fall monotonically, so they stack into a loss waterfall as they are. Constants
`DIAGNOSTIC_COLUMNS` and `EQUIPMENT_DIAGNOSTIC_COLUMNS` are exported — build
against those rather than hard-coding the names.

---

## Building a Phase 2 plant

Everything is exported from `src.profiles`. Capacities are **derived** from the
equipment, so there is no nameplate field to collect:

```python
module = ModuleSpecification.from_cec_database("Canadian_Solar_Inc__CS6X_300M")
inverter = InverterSpecification.from_cec_database(
    "SMA_America__STP_50_US_41__480V_", mppt_input_count=2)

configuration = EquipmentSpecificPVConfiguration(
    latitude=37.77, longitude=-122.42,
    inverter_units=(
        InverterUnitConfiguration(
            inverter=inverter,
            count=2,                      # identical instances
            subarrays=(                   # one subarray per MPPT input
                SubarrayConfiguration(module=module, modules_per_string=15,
                                      strings=13, tilt_degrees=20.0,
                                      azimuth_degrees=180.0, name="south"),
            ),
        ),
    ),
)

configuration.rated_dc_capacity_kw       # 117.01  — from the modules
configuration.inverter_ac_capacity_kw    # 100.02  — from the inverters
configuration.dc_ac_ratio                #   1.17
configuration.is_homogeneous             #   True
```

For dropdowns: `cec_module_names()` (~21,500) and `cec_inverter_names()`
(~3,300). Both are cached; the first call parses a 5 MB CSV, so call it once at
startup rather than per keystroke.

Configuration errors raise `PVEquipmentError` (a `ValueError`), not
`PVSourceError`. The messages are written to be shown to a user unchanged —
they name the fix, not just the fault. Three are worth surfacing well:

- a string too long for its inverter when cold, naming the largest that fits;
- more subarrays than MPPT inputs;
- any `control_mode` other than `"grid_following"`.

---

## Boundaries to respect in the GUI

**Grid-following only.** `control_mode` accepts `"grid_following"` and nothing
else. Do not offer grid-forming, islanded, droop or black-start options — the
model assumes the grid sets voltage and frequency, and that assumption is what
makes "maximum available AC power" answerable. `SUPPORTED_CONTROL_MODES` is the
list to build a control from; `CONTROL_BEHAVIOUR_NOT_MODELLED` is what to say
if someone asks why.

**Clipping is per inverter, not per plant.** On a mixed plant, do **not**
display `max(pv_ac_before_clipping_kw - plant AC rating, 0)`. It can read zero
while real clipping is large — a 12 kW and a 50 kW inverter on identical arrays
lost 38.1 kWh in a day that the plant-level formula reported as 0.0. Use
`pv_inverter_clipping_kw`, and attribute it from `inverter_diagnostics`.
`configuration.is_homogeneous` is false exactly when this matters.

**`pv_inverter_night_tare_kw` is a load, not generation.** It is inverter
self-consumption overnight, reported positive and never subtracted from
`pv_available_kw`. Do not add it to a PV production chart.

---

## NSRDB weather (optional)

Needs `NSRDB_API_KEY` and `NSRDB_API_EMAIL` in `.env`. Read only when a fetch
happens — importing, configuring and every offline path need no credential.

```python
weather = fetch_nsrdb_weather(NSRDBRequest(
    latitude=37.77, longitude=-122.42, year=2023,
    timezone="America/Los_Angeles", time_step_minutes=60))

save_weather_csv(weather.frame, "data/weather/sf_2023.csv")   # then offline forever
```

`weather.frame` goes straight into either PV source as `weather_data`.
`weather.warnings` and `weather.provenance` are worth surfacing.

If you wire this to a button: it is a **billable network call**, so it belongs
behind an explicit fetch action with a cache path, never on a parameter change.
The supplied-frame and CSV paths are unchanged and stay fully offline; NSRDB is
an additional way to get a frame, not a new dependency.

Two gotchas the adapter already handles, both of which would silently shift a
profile if hand-rolled: NSRDB reports local **standard** time all year at a
fixed offset (converted, never re-localised), and labels hourly records at the
**middle** of the hour (detected and shifted to interval starts). Hourly data
on a 15-minute grid needs an explicit `MissingDataPolicy` and warns that
interpolation smooths away the cloud transients that drive clipping.

---

## One behaviour change outside the new modules

`weather.py` could not read a local-time CSV spanning a daylight-saving
fall-back: the repeated hour carries two UTC offsets, pandas returns object
dtype, and the old code died on `.dt` with an `AttributeError` that said
nothing useful. It now parses those into a single zone. Existing cases are
byte-identical — the fallback only engages when the normal parse comes back
mixed — and `save_weather_csv` writes UTC for the same reason.

---

## Still open

- Nothing is committed. Phase 1, Phase 2, NSRDB and your GUI work are all
  uncommitted together.
- Neither PV phase is wired into the GUI. That is yours; the backend interface
  above is stable and will not change under you.
- `_sandia_eff` is a private pvlib function, used to get AC before clipping.
  Tests pin it bit-exactly against `inverter.sandia` and `sandia_multi`, so a
  pvlib upgrade fails loudly rather than drifting. If those tests break after
  an upgrade, that is the cause.
