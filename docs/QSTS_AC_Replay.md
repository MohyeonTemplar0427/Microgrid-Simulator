# QSTS AC replay integration

Implemented 2026-09-15. pvlib computes available AC generation from weather,
module/string/MPPT configuration, inverter efficiency and clipping. OpenDSS
receives that AC schedule as constant-P/Q Generator elements (model 1), one
per physical inverter. It does not repeat the solar conversion calculation.
These are steady-state grid-following equivalents, not inverter dynamics.

## GUI path

`create_site_profile` attaches a `PVReplayConfiguration` containing electrical
inverter ratings and timestamp-indexed availability. Equipment configurations
expand each unit's `count`; the backend's unit diagnostic is already summed
across count, so each identical physical inverter gets that series / count.
Phase 1 uses its derived AC inverter rating. DC nameplate remains distinct.
The live analysis adapter carries this configuration through the simulation
specification into every scenario, including carbon-weight sweeps.

Inverter night tare is added once to the site load before dispatch and billing.
The original PV diagnostics preserve that contribution separately.
Synthetic/CSV inputs retain their existing single aggregate AC rating; they
contain no equipment-specific wiring information.

## Electrical contract

- `PVInverterReplay`: unique safe identifier, AC kW, kVA, bus with nodes,
  phases, connection, nominal kV. kVA must be at least rated AC kW.
- `PVReplayConfiguration.available_power_kw`: timezone-aware timestamp index;
  columns match physical inverter IDs; finite nonnegative values within ratings.
  Missing timestamps raise. Matching uses instants, preserving DST repeated hours.
- Dispatch `pv_kw`: requested aggregate AC output. It cannot exceed the sum of
  availability at the selected timestamp. Reduction is allocated in proportion
  to each inverter's available power. The optimizer still supplies fixed PV;
  this interface can replay curtailment but does not add an optimizer variable.
- Optional `pv_<ID>_requested_kvar`: reactive injection, positive supplying vars.
  Default zero. P/Q must satisfy the specified kVA circle before solving.
- Optional `load_kvar`: reactive consumption, positive inductive. Alternatively
  `load_power_factor` in (0, 1] derives lagging kvar. Default PF is 0.95.
  Explicit kvar takes precedence. Electrical columns are timestamp-aligned and
  carried through dispatch without changing its optimization objective.

## Measurements and feasibility

Each interval records actual load P/Q, battery terminal real power, per-inverter
available/requested/actual P/Q, inverter ratings, loading, and tracking errors.
Any P or Q mismatch above 0.01 kW/kvar, or actual kVA excess beyond a 0.01 kVA
numerical allowance, makes that interval infeasible alongside existing network
checks. The GUI comparison and CSV summary include power tracking failure and
inverter limit violation counts. Detailed CSV exports retain each inverter.

`network_real_loss_kw` is OpenDSS circuit real loss. `pcc_balance_error_kw` is
PCC import minus scheduled net import minus network loss. The existing
`grid_import_error_kw` remains the feeder receiving-end comparison.

## Explicit assumptions and next work

The GUI still uses the representative 12.47 kV / 480 V balanced three-phase
network, 750 kVA transformer and common load bus. Selected CEC equipment does
not specify installation topology. CEC Paco is an AC **kW** rating; GUI replay
assumes kVA = kW and Q = 0 and reports that assumption. Programmatic callers
can supply actual kVA and an existing bus/connection through the replay types.

Future work: residential split-phase service and site wiring configuration,
verified inverter reactive capability curves, Volt-Var/Volt-Watt controls,
and dispatch feedback when network constraints alter delivered power.
The present Generator elements do not run OpenDSS PVSystem InvControl models.
QSTS remains a one-way validation of a dispatch schedule.

Hourly historical loads remain hourly information even when repeated at finer
simulation intervals. This change does not implement a residential load adapter
or infer household sub-hour peaks.
