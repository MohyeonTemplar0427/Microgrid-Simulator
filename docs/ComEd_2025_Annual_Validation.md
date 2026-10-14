# ComEd 2025 annual billing and dispatch validation

This records the earlier synthetic-load/clear-sky **BES** benchmark. The subsequent
[historical-weather and actual-price BESH validation](ComEd_Historical_Annual_Inputs.md)
uses different supply inputs; its results should not be treated as a weather-only
comparison with this run.

Development validation, October 13, 2026. Two hypothetical accounts compare
grid-only, PV-only and PV plus battery using the shared schema-10 study worker.
No stable engine pin or Web UI v1.0.1 designation is changed. Account service
and eligibility are assumptions, not inferred from Chicago coordinates.

## Inputs and method

Both cases cover January 1–December 31, 2025 in `America/Chicago`, with
30-minute interval starts: **17,520 intervals / 8,760 physical hours** per
scenario. Twelve explicitly calendar-designated billing cycles are supplied.
March has 743 physical hours and November has 721. These are synthetic cycle
designations, not actual customer meter-reading dates.

| Parameter | Residential | Commercial |
|---|---|---|
| Supplier / plan | ComEd BES | ComEd BES |
| Delivery class | Single family without electric space heat | Small Load, secondary service with utility transformation |
| Native load | Generic residential daily archetype, 3-kW weekday peak | Generic office daily archetype, 60-kW weekday peak |
| Annual native consumption | 13,887.54 kWh | 239,634.65 kWh |
| PV / inverter | 5 kW DC / 4 kW AC | 40 kW DC / 35 kW AC |
| Battery | 13.5 kWh / 5 kW charge and discharge | 100 kWh / 30 kW charge and discharge |
| Battery initial / annual terminal energy | 6.75 kWh | 50 kWh |
| SOC bounds | 10–90% | 10–90% |
| Charge / discharge efficiency | 95% / 95% | 95% / 95% |

Loads reuse `SyntheticLoad`, including its deterministic weekday/weekend
shapes, zero random variability and fixed seed. They are native consumption
before PV/storage, not utility-meter purchases. They are not calibrated Illinois
load models and do not model weather-driven heating/cooling or holiday closures.
The commercial account assumes prior 12-month and previous-calendar-year peaks
of 60 kW, no previous-year months at/above 100 kW and no competitive declaration.
These histories remain fixed across scenarios; current optimized demand does
not reclassify the account or establish future eligibility.

PV reuses the shared weather/PV physics at 41.8781, -87.6298: Chicago clear-sky
Ineichen irradiance sampled at interval midpoints, 30° tilt, 180° azimuth,
14% system losses, 96% nominal inverter efficiency, assumed constant 20°C and
1 m/s wind. **No measured 2025 weather is used.** Clear skies ignore actual
clouds and cannot establish expected real-world annual PV savings.

Both accounts assume an approved non-export operating arrangement retaining
the ordinary import tariff, with grid charging allowed and no special DER,
standby or rebate charges. Exports and export credits are zero. Capital costs,
state electricity excise tax, municipal taxes and franchise fees are excluded;
Illinois distribution tax is included. Results are **subtotals**, not complete
utility bills. BES receives no additional wholesale or capacity charge.

Each scenario uses the same load and dated 2025 supply/delivery/rider
composites. PV-only minimizes its own subtotal. The battery solve is a single
continuous annual historical-perfect-foresight optimization: it does **not**
reset SOC monthly. Initial and December-terminal energy are equal. The objective
excludes degradation by user preference; estimated wear at $0.03/kWh of total
charge-plus-discharge throughput is reported separately. Annual results do not
describe a forecast-driven controller or the exact minimum of a cent-rounded
invoice. Source pages/hashes and historical benchmarks are documented in
[ComEd historical rates](ComEd_Historical_Rates_and_Billing_Cycles.md).

## Solver issue discovered by the annual run

The original candidate completed the residential year. The commercial primary
cost MILP also proved optimal in a diagnostic run (40.19 seconds), but its
secondary minimum-throughput MILP hit the 60-second limit without an incumbent.
CVXPY surfaced a SciPy solver error, causing the otherwise valid study to fail.
Original failed study: `1d519923f2564784937c150732f57ab4`, retained under
`.cache/comed_2025_year_validation/`. Its candidate pin is
`5393b1adc258dcb088ff2a96490b739ef2610ecb9ce48b7b9e18e9933b0b77a0`.

The repair preserves independent copies of the proven primary solution before
starting the secondary solve. If the tie-break errors or is unproven, that
solution is retained and passes the same physical and billing reconciliation.
Unproven **primary** solves still reject. No relaxed solution, shortened study
or monthly optimization substitute is used. Results expose
`cost_optimum_proven`, `throughput_tie_break_status` and a warning that minimum
cycling among equal-cost solutions was not established when applicable.
The browser and modern desktop share this result payload and warning display.

Focused validation: 116 history/cycle/dated-rate tests passed; 42 dispatch and
worker regressions passed; the additional saved-result warning test passed.
Failure-injection tests deliberately overwrite solver variable values and
verify that the independent saved primary schedule survives. A separate test
confirms unproven primary solves still fail.
Final complete regression: **1,844 passed, 1 skipped**, in 261.66 seconds with
`/usr/local/bin/python3 -m pytest -q`. JavaScript syntax and `git diff --check`
also passed. Candidate source hashes match the checkout; earlier engine pins
and the original failed annual run were preserved.

## Validated results

Both repaired-candidate studies completed and passed the saved-output audit.
The tool observed residential completion in 50.27 seconds and commercial
completion in 113.53 seconds. All six primary cost optima were proven. The residential throughput
tie-break completed; commercial retained its primary optimum after the
secondary solver error and displays that limitation in the browser.

| Annual modeled subtotal | Residential BES | Commercial BES |
|---|---:|---:|
| Grid only | $2,351.59 | $34,240.29 |
| PV only | $1,602.43 | $25,032.71 |
| PV plus battery | $1,084.57 | $21,790.86 |
| PV savings versus grid | $749.16 (31.86%) | $9,207.58 (26.89%) |
| PV plus battery savings versus grid | $1,267.02 (53.88%) | $12,449.43 (36.36%) |
| Battery increment versus PV only | $517.86 | $3,241.85 |
| Estimated battery wear, excluded from objective and subtotals | $213.84 | $1,172.34 |

Commercial annual demand charges fall from $10,428.00 grid-only to $7,782.84
PV-only and $4,794.09 with storage. Thus $2,988.75 of storage's additional
$3,241.85 savings comes from demand charges; the remaining $253.10 is net
energy-related savings. Residential has no demand charge in this scope.
Fixed customer/metering charges are unchanged. Reduced imports also reduce
some negative PEA/CFRA credits, offsetting part of the gross energy savings;
signed component comparisons preserve these effects.

The commercial all-hours peak increases from 60 kW to 76.398 kW with storage,
while the maximum **billed MKD across the twelve cycles** falls from 60 kW to
32.558 kW. This is consistent with this plan's weekday 09:00–18:00 demand
measurement; the all-hours peak is not substituted into that billed component.
These summary maxima are not summed monthly demands. The monthly CSV contains
each separate charge and measured peak. Future classification/obligation changes
remain outside the model.

Each scenario passed all 17,520 representative AC intervals: **105,120 checks**
in total, with zero infeasible intervals. Maximum audited interval power-balance
error was below 4e-13 kW and SOC-recursion error below 8e-13 kWh. Battery initial
and terminal energies match. The largest absolute annual bill/objective rounding
difference is $0.04886, within the declared $0.7200012 annual bound. All 72
monthly scenario bills reconcile their itemized lines and import energy. The
audit is internal software validation using independently benchmarked tariff
components, not reconciliation with a real customer invoice.

Reviewed candidate engine:
`04df8054b8533e4c61b100e8b848369e29bb32330d0cad698907808478b1a4ea`.
The original failed candidate and all earlier pins remain unchanged.
Browser readback confirmed the three commercial totals and the tie-break
warning in the existing results interface. View the saved studies at:

- [Residential annual results](http://127.0.0.1:19018/#e6174cd38e124bf1a7b702eb99c97432)
- [Commercial annual results](http://127.0.0.1:19018/#056a46c021f14ebc923d30782465a3c1)
- [Monthly subtotal chart](../.cache/comed_2025_year_validation_repaired/monthly-subtotals.png)
- [Monthly scenario CSV](../.cache/comed_2025_year_validation_repaired/monthly-comparison.csv)

The modern desktop serves this same configuration, backend and warning payload;
its native window was not separately opened. No staging, commit, push, deployment
or stable-release promotion was performed.

## Reproduce and inspect

```sh
/usr/local/bin/python3 tools/run_comed_year_validation.py \
  --output .cache/comed_2025_year_validation_repaired
```

Use a fresh output directory when source changes. The tool never refreshes an
existing engine pin and rejects a store whose pin differs from the checkout.
The isolated worker preserves requests, source/dependency hashes, timestamped
inputs, PV/weather provenance, monthly charges, dispatches and all AC replay
rows. `validation.json` records the driver hash, study IDs, output CSV hashes
and physical/reconciliation checks. The annual and monthly comparison/component
CSVs are generated under the ignored output store, not committed sample data.
The exact executed driver is also retained alongside its hash. A harmless pandas
FutureWarning from concatenating all-missing residential demand fields was
removed in the current driver with explicit nullable numeric typing; the updated
audit reproduces all 72 saved monthly subtotals without that warning.

To reopen the candidate without refreshing its pin:

```sh
/usr/local/bin/python3 -m src.local_web.server --port 19018 \
  --data-dir .cache/comed_2025_year_validation_repaired
```

Checks cover every interval's power balance, PV availability/curtailment,
non-export operation, exclusive battery modes, charge/discharge bounds, SOC
recursion and annual terminal energy. Each month uses its dated version; line
items sum to its Decimal subtotal, kWh match interval imports, and commercial
MKD is remeasured from aligned weekday 09:00–18:00 imports excluding NERC
holidays. Monthly charges reconcile with annual expressions within their
explicit line-rounding bound. All schedules are replayed on the balanced
representative 12.47-kV/480-V circuit with a 750-kVA transformer, load PF 0.95
and Q=0 inverters. This is representative steady-state validation, not a
site-specific, protection, transient or islanding study.
