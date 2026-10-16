# Southern California, AMP and SVP electrical validation

The shared queued study worker now runs OpenDSS **after** dispatch and billing for:

- Schema 6: SCE, LADWP, SDG&E (including supported SDCP/CEA supply), Glendale,
  Pasadena, Burbank, Azusa and Industry Public Utilities. Every returned
  grid-only, PV-only, battery-only or PV-plus-storage scenario is checked.
- Schema 4: AMP and SVP grid-only and storage studies. Both the no-battery
  baseline and cost-optimal storage schedule are checked when returned.

This does not extend any tariff, solar-program eligibility or export coverage.
AMP/SVP studies remain import-only. Unsupported electrical service does not
invalidate an otherwise supported bill; it produces an explicit unevaluated
electrical result.

## Representative circuits

`src/local_web/electrical_replay.py` selects a circuit using the account's
explicit customer class, voltage class and phase. Tariff names, coordinates and
load magnitude do not determine wiring. All scenarios use the same circuit.

| Confirmed secondary-service account | Study circuit |
| --- | --- |
| Residential, single phase | 12.47 kV / 120–240 V center-tapped transformer, 25 kVA; 100 A, 30 m three-wire service |
| Commercial/industrial, single phase | Same split-phase topology; 75 kVA transformer, 400 A, 30 m service |
| Commercial/industrial, three phase | Existing balanced 12.47 kV / 480 V circuit; 750 kVA transformer, 800 A, 100 m feeder |

These ratings and nominal voltages are representative assumptions, not facts
established by a tariff's “secondary” designation. A feasibility result applies
only to the saved reference circuit; the circuit is not enlarged to make a
schedule pass. Primary/high-voltage service, three-phase individual residential
service and missing service facts are explicitly **unsupported**. No 480 V
circuit is silently substituted for those accounts.

The split-phase topology follows [EPRI's center-tapped transformer example](https://opendss.epri.com/ModelingSingle-PhaseTransformers.html):
three windings with opposite secondary polarity, %R = 0.6/1.2/1.2,
XHL/XHT = 2.04%, XLT = 1.36%, and no-load loss = 0.2%.
The commercial 75 kVA rating reuses these per-unit impedances as a study
assumption; EPRI's 25 kVA example is not a 75 kVA equipment specification.
Each secondary half-winding is checked against half the transformer rating.

Both split-phase models allocate 40% of load to each 120 V leg and 20% to
240 V. Each conductor, including the neutral, has an explicit series impedance
with no mutual coupling or shunt capacitance. Residential R/X is 0.4/0.1 ohm/km;
commercial R/X is 0.1/0.05 ohm/km. Lengths, allocation, impedance and ampacity
are study assumptions, not a surveyed service or a verified conductor design.
The three-phase model uses transformer %R = 0.5/0.5, XHL = 5.75%, and feeder
R1/X1 = 0.02/0.04, R0/X0 = 0.04/0.08 ohm/km. All parameters are recorded in
`ac_validation.network_configuration`.

Load reactive power assumes constant 0.95 lagging PF. A tariff's monthly PF
adjustment is not treated as an interval measurement. PV uses aggregate AC
nameplate from the existing production model (DC nameplate / 1.2 in schema 6),
constant P/Q, Q = 0 and kVA = AC kW. Storage is externally dispatched using
the existing AC-side efficiencies. Absent PV/storage is omitted from the circuit.
The [shared replay contract](QSTS_AC_Replay.md) and
[split-phase model](Residential_Service_Replay.md) describe the physical checks.

## Schedule mapping and accounting

Every timezone-aware 15-minute interval is replayed without resampling. Actual
instants preserve spring/fall DST transitions. SoCal `energy_kWh` and municipal
`energy_start_kwh` both represent **start-of-interval** battery energy. Replay
checks the energy update, next start, configured bounds, initial energy and
cyclic terminal energy; municipal interval-end energy is reconciled explicitly.

PV availability is distinct from actual output. Explicit optimized output and
curtailment are preserved. Where the PV-only bill supplies only meter flows,
actual PV output is reconstructed from native load, imports, exports and battery
flows; remaining availability is curtailed. Available solar is never replayed as
actual production when the schedule curtailed it.

When inferring PV output, cancellation at an equipment boundary can produce a
tiny negative number even with no PV (the browser CB-1 case exposed
-1.78e-15 kW). The adapter projects only values within the shared 1e-5 kW
power-balance tolerance onto zero/available PV boundaries. This changes only
the replay copy; larger inconsistencies are rejected, and original meter and
battery schedules remain untouched.

Original dispatch tables, utility bills, objective reconciliation and solar
credit ledgers remain unchanged. Scheduled directional import/export remains
the billing basis. OpenDSS PCC import/export, feeder/transformer losses and
setpoint tracking are separate diagnostics. This is one-way QSTS validation;
it does not impose network constraints on optimization or perform protection,
dynamic, transient, thermal-aging or site-specific validation.

## Results and compatibility

- Scenario comparison and `ac-summary.csv`: checked/converged/feasible/failed
  counts, voltage extrema, line/transformer loading, tracking violations and
  separate replay PCC/loss energy.
- `ac-<scenario>.csv`: every replay interval, scheduled flows, actual PV and
  battery power, start/end SOC, electrical measurements and failure flags.
- `result.json` → `ac_validation`: circuit/inverter assumptions, each scenario's
  interval-table ID and up to five failure timestamps with reasons. A completed
  calculation may have electrical failures; the browser reports this explicitly.

Nonconverged electrical measurements are missing, not zero. When any solve
fails, electrical energy aggregates are withheld to avoid presenting a partial
sum as full-period energy. Scheduled billing quantities remain available.
Unsupported service has status `unsupported`, null feasibility, a reason and
an `ac-summary` table; it has no fabricated interval measurements. Older saved
studies without validation remain unevaluated and retain their original files.

The existing authenticated table/download routes, retention rules and immutable
worker snapshots are reused. The modern desktop shares that browser/worker
path. Previously pinned engines/results are not rewritten or promoted.

## Deterministic verification

`test/test_utility_electrical_replay.py` checks circuit selection, curtailment,
absent equipment, directional power, SOC, DST, overload, nonconvergence and
unsupported service. `test/test_utility_electrical_workflows.py` runs real
utility optimizers, compares bills and dispatch exactly before/after replay,
checks all Southern California providers plus AMP/SVP residential/commercial
cases, and preserves SCE NBT/NEM, LADWP NEM and BWP net-billing ledgers.
Existing municipal and Southern California form-to-worker tests verify saved
manifests and full downloadable electrical tables. Inputs are deterministic;
no live weather, utility or other provider APIs are required.

Verification on 2026-10-15 with `/usr/local/bin/python3`: 517 focused utility,
OpenDSS, form/worker, saved-result, auth/storage, desktop and ComEd regression
tests passed. Four NumPy reduction warnings arose in municipal optimization
cases, including existing municipal-dispatch tests; no test failed. JavaScript
syntax and Git whitespace checks also passed. The root README and pre-existing
ComEd refinement changes were preserved.

Browser follow-up used a separate local candidate on port 19024 with engine
`77d80be6eb5f`. Six hypothetical July 2026 studies covered residential and
commercial SCE, AMP and SVP accounts: SCE TOU-D-4-9 / TOU-GS-2-D, AMP D-1 /
A-2 and SVP D-1 TOU / CB-1. All 14 returned scenarios passed, with 2,976
intervals each (41,664 checks). Rebilling every scenario from its saved scheduled
meter flows reproduced each total/line item within $0.001. A browser-downloaded
SVP bundle matched the saved CSVs byte for byte. The CB-1 no-PV roundoff case
above now has focused regression coverage; the final focused run passed 49 tests.
Local case parameters, hashes and interval audit results are in the ignored
`.cache/utility_electrical_preview/review/` directory. Earlier failed/intermediate
studies retain their original engine and status. No stable engine was promoted.

## Eastern schema-11 candidate

Dominion Virginia, Dominion North Carolina and PSE&G reuse this electrical
workflow with America/New_York timestamps and the actual configured interval
length. Native-load, delivered PV (after curtailment), battery AC power and
start-of-interval SOC map explicitly to the replay adapter. Grid-only and PV-only
cases have genuinely absent equipment. Residential uses the 25 kVA split-phase
reference; compatible secondary commercial service uses 75 kVA single-phase or
750 kVA three-phase references. Unsupported primary/high-voltage or other nominal
service remains electrically unevaluated even when the retail bill is valid.
Every compatible scenario has downloadable per-interval convergence, voltage,
thermal, losses and setpoint diagnostics. These are quasi-static representative
checks after optimization, not network-constrained dispatch, surveyed feeder,
transient, protection or interconnection studies. See the generated
[coverage matrix](Regional_Utility_Coverage.md) and private-source validation
reproduction in [Regional Validation](Regional_Validation.md).
