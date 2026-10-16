# Representative residential service replay

New PG&E residential export comparisons use `ResidentialService` through the
shared OpenDSS replay. Every scenario uses identical network assumptions.
Dispatch, retail bills and credit ledgers retain their original scheduled
flows. Electrical losses and transformer excitation are diagnostics, not
additional billed consumption. The browser and desktop shared study worker
use the same export adapter; the separate general three-phase workflow is
unchanged. No release promotion or existing-result migration is implied.

## Model and provenance

| Component | Assumption |
|---|---|
| Source | Idealized regulated 12.47 kV three-phase source; transformer primary connected line-to-line |
| Transformer | 25 kVA single-phase, three windings, two series-opposed 120 V secondaries |
| Transformer impedance | XHL/XHT 2.04%, XLT 1.36%; winding resistances 0.6/1.2/1.2%, on EPRI's 25/25/25 kVA winding bases |
| Excitation | 0.2% no-load real loss; zero magnetizing vars; no saturation |
| Service | 30 m; two hot conductors and explicit neutral; each 0.4 ohm/km resistance, 0.1 ohm/km reactance; mutual coupling/shunt capacitance omitted |
| Rating checks | 100 A per hot conductor and neutral; 25 kVA primary and 12.5 kVA per half-secondary |
| Ground reference | Transformer center tap grounded; neutral returned through service wire; earth-return parallel paths omitted |
| Native load | 40% L1–N, 40% L2–N, 20% L1–L2; constant P/Q, default 0.95 lagging PF |
| PV/storage | 240 V L1–L2; same AC production/curtailment, kW/kVA ratings and dispatch as before |
| Voltage check | Both L–N voltages / 120 V and L–L / 240 V against 0.95–1.05 pu; neutral voltage is reported separately |

Transformer construction and impedance values follow
[EPRI's center-tapped transformer modeling example](https://opendss.epri.com/ModelingSingle-PhaseTransformers.html).
The opposing winding terminal order is essential. EPRI's model winding kVA
bases are retained for impedance calculations; independent half-secondary
loading checks enforce the assumed 12.5 kVA physical limit on each leg.
PG&E's [underground transformer application document](https://www.pge.com/content/dam/pge/docs/account/service-requests/062111-r-28-application-of-underground-distribution-transformers.pdf)
also lists 25 kVA 240/120 V equipment. Neither source establishes the wiring,
transformer size, line impedance, service rating or load split of this study's
hypothetical home. The service and load values above are engineering study
assumptions, not a conductor-sizing calculation or customer measurements.

The explicit neutral permits unbalanced load testing. Production defaults are
balanced because no measured leg allocation is available. Programmatic callers
can change the two 120 V load fractions and service parameters; invalid values
fail before solving. Generic 480 V PV profile wiring is explicitly replaced
by 240 V connections while retaining equipment ratings and availability.
Other/custom wiring is rejected, not silently relocated.

## Results and scope

The result manifest records network identifier `residential_split_phase_v1`,
parameter values and source. Validation version 2 identifies the new export
replay; version 1 results retain their old 750 kVA three-phase assumptions.
Interval CSVs expose L1–N, L2–N and L1–L2 volts, neutral displacement/current,
hot-leg currents, and primary/half-secondary loading. `transformer_loading_percent`
is the maximum of primary and the two half-secondary percentages. This avoids
missing an overloaded leg when aggregate kVA is below nameplate.

Replay still respects interval-start SOC and actual curtailed PV. The model
does not constrain optimization, add breaker/protection or panel busbar checks,
simulate inverter dynamics, or model temperature-dependent transformer aging.
It excludes neighboring homes and upstream voltage variations. Household
behavior and sub-interval peaks are not inferred from the circuit or a constant
load input. A passing run is feasibility under these assumptions, not electrical
design approval for a real home.

Offline tests cover polarity, both voltages, a loaded neutral, half-winding and
service overloads, all five scenarios, absent equipment, unchanged input and
billing data, and the existing three-phase workflow. The saved browser study
provides the full-month replay of the original July 2026 example.

## Synthetic household and electrical stress validation

The shared local browser/desktop form now offers **Synthetic daily pattern →
Total study consumption · kWh** for the schema 2/3 location workflow (including
PG&E residential solar export). Enter 744 kWh for July 1–31, 2026 to reproduce
the energy of the previous flat 1 kW example. The old peak-kW and constant-load
settings retain their behavior. Other utility-specific forms retain their own
load contracts; this addition does not silently change their scaling.

`SyntheticLoad` reuses the existing residential morning/evening shape, including
its flatter, slightly higher-energy weekends. It normalizes the integral over
the actual timezone-aware intervals to the requested energy. For this July,
the resulting demand is 0.531–1.896 kW, averaging 24 kWh per calendar day over
the month. Weekday and weekend totals differ; 24 kWh is the monthly average.
Hourly shape blocks repeat at 15-minute resolution. These are hypothetical
native-building loads before PV/storage, not measured meter purchases, appliance
estimates, regional calibration, weather-driven HVAC, or next-day forecasts.
Source metadata records the scaling, integrated kWh, peak kW and synthetic status.
Spring/fall DST horizons retain every actual interval and the specified energy.

Run the deterministic, offline validation from the repository root:

```sh
/usr/local/bin/python3 tools/run_residential_export_validation.py --output .cache/residential_export_validation_july
```

Choose a new empty output directory for a rerun. The tool preserves previous
artifacts. It records a source/dependency snapshot and runner hash, normalized
inputs, weather/PV diagnostics, scenario dispatch, credit ledgers, electrical
interval CSV/JSON tables, and a combined `summary.csv`. The returned manifest
distinguishes successful calculation from failed electrical feasibility.
`validation.json` reports success only when the invariants and expected stress
failures hold; it does **not** mean all circuits are feasible.

All cases use July 2026, 2,976 fifteen-minute intervals, PG&E bundled residential
E-ELEC/NBT tier 3 (hypothetical 2026 enrollment), zero opening credits, bill-only
optimization, and the same 4 kWh battery (20–80% SOC, initially/finally 0.8 kWh,
2 kW charge/discharge, 95% efficiency each way). Wear at $0.01/kWh throughput
is reported separately and excluded from the objective. PV uses local pvlib
clear-sky irradiance at 37.7749, -122.4194, 20° tilt, 180° azimuth, 14% losses,
96% nominal inverter efficiency, assumed 20°C air and 1 m/s wind. No live data
requests occur. Carbon is not assessed in this offline cost/electrical sweep.
The browser rerun can reuse its independently verified cached July carbon data;
carbon has zero objective weight and cannot change these bill results.

| Case | Change from reference | Electrical result (failed / 2,976 intervals per scenario) |
|---|---|---|
| Daily household | 744 kWh; 3 kW DC / 3 kW AC PV; 3 kW export limit; default 25 kVA, 100 A, 30 m service | All five pass |
| Evening peak | Redistribute 80% of each local day's energy into 18:00–19:00; retain daily and monthly kWh; peak 20.317 kW | All five pass, up to 91.31% service loading |
| Large PV | Original daily load; 36 kW DC / 30 kW AC PV and 30 kW export limit | PV/export and storage/export each fail 298 intervals; other three pass |
| Uneven legs | Evening-peak load with 85% L1–N, 5% L2–N, 10% at 240 V | All five fail 124 intervals; service/half-secondary overloads and some undervoltage |
| Long service | Evening-peak load with balanced legs and 150 m service | All five fail 124 intervals due to undervoltage |

These are intentionally severe **hypothetical stress assumptions**, not typical
household configurations, interconnection eligibility claims, or recommended
installations. Large-PV export reaches 104.70% service loading and 101.69%
transformer loading. The uneven-leg case reaches 169.08% service loading and
159.07% half-secondary loading. The long-service case reaches 0.93569 pu.
All 74,400 interval power flows converged; 1,836 intervals were electrically
infeasible. A converged solution alone is not a passing feasibility result.

| Reference daily-profile scenario | July utility bill |
|---|---:|
| Grid only | $332.69 |
| PV, no export | $207.34 |
| PV with export | $192.35 |
| PV + battery, no export | $168.30 |
| PV + battery with export | $157.64 |

All 25 dispatch results integrate to 744 kWh of native demand, preserve power
balance and PV curtailment, and reconcile the existing billing objective and
ledger. Network-only changes preserve every scheduled billing component exactly.
Battery operation assumes full-cycle historical perfect foresight; the electrical
replay remains after optimization and does not repair infeasible schedules.

The stress runner passes explicit `ResidentialService` overrides to the same
export adapter used by the shared worker. These are saved in `ac_validation`
and the validation provenance, with dynamic warnings. The evening redistribution
and service overrides belong to this validation tool, not new browser controls.
Reproduce stress cases with the named runner and saved `normalized.csv`;
`request.json` alone recreates the underlying ordinary study and does not apply
these validation-only overrides. The baseline energy-scaled profile is fully
round-trippable through the browser and shared desktop form.
