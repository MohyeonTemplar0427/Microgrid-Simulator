# Microgrid backend architecture

Reference for the time-series, surplus, metering and tariff layers. Covers the
conventions that are decisions rather than derivations — the things a reader
cannot recover from the code alone.

## Dispatch cost objective

Cost-optimal dispatch minimizes modeled electricity charges by default. The
browser and desktop GUI expose an unchecked **Include battery wear in cost
optimization** choice. When checked, the optimizer adds the specified
throughput-based degradation estimate to its objective. The estimate remains
visible in results in either mode, and `total_explicit_cost` includes it; that
reported total is therefore distinct from the bill-only optimization target.
Combined carbon-and-cost dispatch uses the same wear choice but also includes
the user's carbon weight. A customer charge that is fixed for the selected
plan does not alter dispatch.

PG&E B-19/B-20 Option S uses two separate monthly maximum-demand measurements:
one over all hours and one excluding 09:00–14:00 local time. Its summer peak,
summer part-peak, and winter peak demand rates apply to each local day's
maximum in the respective TOU window. Billing and dispatch both use these
same scopes. The study's calendar-month periods are an approximation of actual
meter-read billing cycles, particularly when a cycle straddles a season or
rate-change boundary. For a partial period, `previous_peak_kw` can carry in
only the all-hours monthly peak; prior daily peaks and the prior excluded-hour
maximum are unknown, so a partial-period Option S bill may understate charges.

## Layer separation

| Layer | Package | Answers |
|---|---|---|
| Time series | `src/timeseries` | What are the inputs, on what grid, in what units? |
| Profiles | `src/profiles` | Where do load and PV come from? |
| Surplus | `src/surplus` | Where does excess PV go, and does it balance? |
| Metering | `src/billing/meter_topology.py` | Which flows are billed together? |
| Tariffs | `src/billing/tariffs.py` | What are the rates, and when were they valid? |
| Rate plans | `src/billing/plans.py` | Which filed version applies on each service date? |
| Baselines | `src/billing/baseline.py` | How much usage is priced at the baseline tier? |
| Billing | `src/billing/charges.py` | What does it cost? |
| AC replay | `src/opendss/ac_replay.py` | What does each inverter actually put on the network? |

Tariff definitions themselves live in `src/billing/pge_commercial.py` and
`src/billing/pge_residential.py`, split because the two families differ
structurally and not merely in price — see *Residential is not commercial*
below.

The physical network (`src/opendss`) and the billing topology are deliberately
distinct. OpenDSS determines voltages, currents, losses and real PCC power.
Meter topology determines what appears on which bill. Two sites with identical
physics can bill very differently, so neither layer can be inferred from the
other.

## The normalized interval table

Required columns:

| Column | Units | Meaning |
|---|---|---|
| `timestamp` | tz-aware | **Start** of the interval |
| `native_load_kw` | kW | Site demand before PV and battery effects |
| `pv_available_kw` | kW | Maximum PV from sunlight, before curtailment |
| `price_per_kWh` | $/kWh | Import energy price |
| `carbon_intensity_g_per_kWh` | gCO₂/kWh | Grid carbon intensity |

Optional: `flexible_load_available_kw`, `export_limit_kw`,
`export_price_per_kWh`. Absent means the capability is *disabled*, which is not
the same as present-and-zero.

### Inclusive end date

The GUI takes an **inclusive** end date. Internally the horizon is half-open:

```
user picks   2026-06-01 .. 2026-06-03   (inclusive)
internal     2026-06-01 00:00 .. 2026-06-04 00:00   (start <= t < end)
```

The conversion advances one calendar day with `pd.DateOffset(days=1)`, **not**
`pd.Timedelta(days=1)`. Timedelta adds exactly 24 hours, which lands at 01:00
local on a daylight-saving day and silently drops or duplicates an hour.

### Interval counts are never assumed

A local day is not always 96 fifteen-minute intervals. Spring-forward days have
92 and fall-back days have 100. Every count comes from the generated index, and
`number_of_days * 96` appears nowhere.

### Missing data

`MissingDataPolicy` defaults to `REJECT`. Filling happens only under an
explicit policy, and the number of distinct timestamps filled in any input
column is recorded on the result so a filled interval is never presented as
measured.

## PV allocation: the PV-first convention

Within each interval, available PV is allocated in fixed priority order:

1. **Native load** — displaces grid import first, the highest-value use under
   any tariff with a positive import price.
2. **Battery charging** — surplus beyond native load, up to scheduled charge.
3. **Flexible load** — if enabled.
4. **Grid export** — if enabled, up to the limit.
5. **Curtailment** — whatever remains.

This is an **accounting** convention, not a claim about electrons. Real power
flow is set by the network; the convention decides how a kWh is *labelled* for
reporting "self-consumed PV" and "battery charging attributed to surplus PV".
It matters because battery charge can come from PV or the grid, and the split
is otherwise ambiguous. Under PV-first, charging is attributed to PV only up to
the PV remaining after native load; anything beyond is grid-charged.

The interval identity that always holds:

```
pv_available = pv_serving_native_load + pv_charging_battery
             + flexible_load_supplied + grid_export
             + pv_curtailed + losses
```

and the bus balance:

```
grid_import + pv_output + battery_discharge
  = native_load + flexible_load + battery_charge + grid_export
```

Both are enforced by `validate_power_balance`.

### Surplus capabilities coexist

Export, flexible load and curtailment are **not** four mutually exclusive
modes. A site can export up to a limit, divert some surplus to flexible load,
and curtail the rest, all in one interval. Curtailment has no enable flag: it
is always available and is the final feasibility mechanism, since not producing
power is always physically achievable.

Defaults are conservative: export **off**, flexible load **off**, remainder
**curtailed**.

### Simultaneity

Materially simultaneous grid import/export and battery charge/discharge are
rejected by `validate_no_simultaneity` within a kW tolerance. No mixed-integer
solver is introduced: with positive import prices and nonnegative export
compensation, simultaneity is economically dominated in a convex formulation,
so the schedule is *validated* rather than constrained with binaries.

## Tariffs are versioned data

A tariff carries an effective window, a source-document URL and a version
string. Lookups may be made for a date, and a lookup outside the effective
window raises rather than silently returning stale rates.

When rates change, **add a new definition** with its own effective window
rather than editing the numbers in place, so historical analyses stay
reproducible.

### Historical coverage target

When adding or retrieving a billing plan, research a **rolling ten calendar
years of history** ending on the latest verified effective date. Store each
actual filed rate or rule change as a dated version with its source, effective
window and account-eligibility conditions. Ten annual averages are not ten
years of billing coverage: fixed charges, energy and demand rates, seasonal and
TOU rules, baselines, riders, generation/delivery splits and solar settlement
rules may change on different dates. A plan introduced less than ten years ago
starts at its documented inception; a retired predecessor is a separate plan
unless a filing establishes continuity.

Publish the verified coverage window and any gaps for each plan. A ten-year
research target does **not** mean the simulator may fill missing periods by
carrying a neighboring version backward or forward. Unsupported dates still
raise. PG&E's [historical electric-rate index](https://www.pge.com/tariffs/en/rate-information/electric-rates.html)
is one source for this work, but every applicable component and rule must be
checked against its dated filing. Current implemented plans have varying,
often much shorter, historical coverage; this target is future research scope,
not a claim that ten years are already supported.

### A plan is not a version

A **plan** is what a customer is on and stays on: "PG&E E-1 bundled, income
tier 3". A **version** is what that plan's rates were between two dates. PG&E
refiled residential rates seven times during 2024 alone, so one year of one
plan touches many versions, and one billing month can touch two.

`RatePlan` in `src/billing/plans.py` holds a plan's versions in effective-date
order and enforces two things at construction:

- **No overlap.** Effective windows are inclusive, so two versions may not
  share a date. Only the newest version may be open-ended.
- **No silent gaps.** `require_coverage` refuses a horizon containing a date
  no version covers, naming the first uncovered date and listing the windows
  that do exist.

A gap is not a bug to paper over. Where PG&E's sources do not state what
applied — currently 2026-03-01 to 2026-05-31, where the rate workbook and the
filed tariff disagree about when the current rates began — billing **raises**.
Substituting a neighbouring version would move a residential bill by roughly
19% while looking entirely normal.

### Two billing entry points

| Function | Takes | Behaviour outside the window |
|---|---|---|
| `calculate_meter_billing` | one `TariffDefinition` | Raises. Strict, unchanged. |
| `calculate_timeline_billing` | a `RatePlan` | Selects the version effective on each local service date. |

The strict path is deliberately preserved: a caller that means "bill this
month at these rates" should still be told when its horizon leaves the window.
The timeline path is for studies that cross a refiling.

Each interval's energy is priced by the version effective on **its own local
service date**, and each service date's fixed charge is collected exactly
once, under whichever version covered that date. Service dates come from the
timestamps, so a daylight-saving day is one service date like any other.
Results are itemised per `VersionSegmentResult` — the intersection of one
billing period and one version — while still totalling to one bill per meter
per period.

### PG&E B-10, effective 2026-03-01

Secondary voltage (below 2,400 V — the modelled 480 V service qualifies),
bundled service.

| Component | Value |
|---|---|
| Customer charge | $11.36882 per meter per day |
| Maximum demand | $20.50 per kW |

Summer (Jun 1 – Sep 30): peak 4–9 p.m. $0.33947; part-peak 2–4 p.m. and
9–11 p.m. $0.27778; off-peak $0.24522.

Winter (Oct 1 – May 31): peak 4–9 p.m. $0.26321; super off-peak 9 a.m.–2 p.m.
**in March, April and May only** $0.19139; other off-peak $0.22773.

Rates match on **local wall-clock hour**, so a 4 p.m. peak stays at 4 p.m.
local on both sides of a DST transition.

B-19 and B-20 now have separate maximum, peak-period and part-peak-period
demand components. Their registered options retain their own rates and
eligibility limits; they must not be approximated by B-10's one component.

## Residential is not commercial

The two families differ in structure, not just in price, which is why they
live in separate modules and why residential needed capabilities the B-series
never exercised.

| | Commercial (B-series) | Residential |
|---|---|---|
| Peak days | Every day, including weekends and holidays | Weekday-only on E-TOU-D |
| Demand charges | Central to the bill | None |
| Energy price | Per-interval TOU rate | Per-interval **or** tiered on period volume |
| Fixed charge | Daily customer charge | Customer charge *or* a minimum bill |

**Day-of-week (`TOUPeriod.days`).** Every B-series period applies every day,
which is why the commercial work never needed this field and why its absence
went unnoticed. E-TOU-D's peak is 5–8 p.m. Monday through Friday; without day
matching, every weekend evening would bill at the peak rate. Holidays are
still **not** modelled — a holiday falling on a weekday is priced at the
ordinary weekday rate, which overstates those few days.

**Tiered energy (`EnergyTier`).** E-1 has no time-of-use periods at all. The
price of a kWh depends on how much came before it in the billing period,
measured against a baseline allowance. Tier bounds are therefore expressed as
multiples of that allowance (100%, 400%), not as kWh, because the allowance
itself depends on territory, season and the number of days in the period.
`charges.py` prices the period total for a tiered schedule and never the
per-interval rate.

**Baseline allowances (`src/billing/baseline.py`).** Quantities vary by
baseline territory (P, Q, R, S, T, V, W, X, Y, Z), season, and whether the
home is all-electric. Territory is a property of the **premises**, set by
county and elevation — never inferred from the tariff name — so billing
accepts an explicit `BaselineAllowance` override. Each local calendar day
earns its own season's quantity, which is E-1 Special Condition 6's documented
rule for a period spanning the June or October changeover.

**Minimum bill is not a customer charge.** A customer charge is *added* to the
bill; a minimum bill is a *floor* under it. PG&E residential service carried a
Delivery Minimum Bill before the income-graduated Base Services Charge
replaced it, and a typical household never reaches the floor. Modelling the
2024 minimum bill as a customer charge would add roughly $11.65 a month PG&E
did not charge — a plausible-looking error of exactly the kind this package
exists to prevent.

**One rule the sources do not state.** The filed schedule documents baseline
proration across a *seasonal* changeover but says nothing about tier
accumulation when *rates* change mid-cycle. Where that happens, each version's
days are billed as their own sub-period with their own prorated baseline, and
the result carries an explicit warning that this is a documented
approximation rather than a filed rule.

## Production and network physics are separate models

### PV–battery connection

The current location-study dispatch is **AC-coupled**: the PV production model
provides available AC power after inverter conversion and clipping, while the
battery's charge/discharge efficiencies are effective AC-side values. The
residential browser form records this under Advanced settings when a PV and
battery comparison is configured. Older saved studies omit the field and retain
the same AC-coupled behavior. A DC-coupled selection is deliberately unavailable.

Future DC-coupled charging must pass PV power **before** inverter conversion and
clipping into dispatch. Each interval must allocate that DC power among the
DC-to-DC battery charger, the shared inverter, and curtailment; model charger
losses and battery state of charge; and constrain the combined PV and battery AC
output by the shared inverter rating. Grid charging, if enabled, needs its own
AC-to-DC path and eligibility rules. Validate interval energy balance, clipping
recovery, meter imports/exports, bill reconciliation, and compatibility with
equipment specifications before enabling the browser choice. Do not reinterpret
AC equipment-catalog efficiencies or ratings as DC-side specifications.

`pvlib` owns production; OpenDSS owns network physics. The PV chain in
`src/profiles/` converts weather, module and inverter configuration into an AC
availability schedule, and `src/opendss/ac_replay.py` hands that schedule to
OpenDSS as constant-P/Q `Generator` elements (model 1), one per **physical**
inverter. OpenDSS does not repeat the solar conversion.

This matters because the alternative — an OpenDSS `PVSystem` with its own
irradiance-to-power model — would compute production twice, from two models
that disagree, and the disagreement would surface as a network result rather
than as a modelling error. One model owns each question.

**These are steady-state grid-following equivalents, not inverter dynamics.**
The Generator elements do not run `InvControl`, Volt-Var or Volt-Watt. QSTS
stays a one-way validation of a dispatch schedule: it answers "is this
schedule electrically acceptable?", never "what would the inverter have done
instead?".

### The replay contract

- **Availability is indexed by instant, not wall clock.** A missing timestamp
  raises rather than being filled by position. On the autumn daylight-saving
  transition a local hour occurs twice, and the two folds are different
  instants carrying different availability — see *Interval counts are never
  assumed* above for the same principle on the input side.
- **Requested PV cannot exceed availability.** Where dispatch asks for less,
  the reduction is allocated in proportion to each inverter's available
  power. The interface can replay curtailment but adds no optimizer variable.
- **P and Q must satisfy each inverter's kVA circle before solving.** A
  setpoint that cannot physically be met is rejected rather than handed to
  the solver, which would otherwise converge on something else and report
  success.
- **Tracking is measured, not assumed.** Every interval compares requested
  against delivered P and Q at each terminal. A mismatch beyond 0.01
  kW/kvar makes the interval infeasible *even when the power flow converged* —
  convergence alone is not evidence the schedule was followed.

### Inverter night tare

A CEC inverter draws a small standby power at night. That draw is added once
to site load before dispatch and billing, because it is a real import the
meter sees. The PV diagnostics keep it as a separate series, so the building
load and the inverter's self-consumption never become indistinguishable.

### Assumptions currently baked in

The GUI path uses the representative balanced 12.47 kV / 480 V network with a
750 kVA transformer and a common load bus. CEC `Paco` is an AC **kW** rating
and says nothing about installation wiring, so GUI replay assumes kVA equals
kW and Q is zero, and reports that assumption in the run's warnings.
Programmatic callers can supply real kVA, bus and connection details instead.

## Demand and customer charges

**Demand charges are never summed across intervals.** Each component bills its
highest eligible 15-minute average import per billing period, once: the
overall maximum uses every interval, while peak and part-peak components use
their tariff-defined hours and season. Multiple components may apply to the
same interval. Summing per-interval demand overstates cost by roughly the
interval count.

Billing periods are calendar months. A multi-month horizon gets a separate peak
*and* a separate customer charge per month.

For a partial billing cycle:

```
billed_peak = max(previous_peak, simulated_peak)
```

When the previous peak is unknown the simulated peak is used and the period is
flagged `is_partial_period` with a warning, because a real bill can only be
higher.

The general cost and combined dispatch objectives now use the selected
tariff's demand components, TOU basis and local seasons, matching those peak
scopes in numeric billing. The supplied `previous_peak_kw` applies only to the
first period's **overall** maximum; prior peak/part-peak history is not inferred.
Callers without a tariff can still provide one flat maximum-demand rate.
Energy-price sources and other tariff provisions remain separate from this
demand-component alignment.

Customer charge:

```
customer_charge = daily_rate * billing_days * utility_account_count
```

`billing_days` counts local calendar service dates. It is not calculated as
elapsed hours divided by 24, because a daylight-saving date with 23 or 25 hours
is still one billing day.

Only **utility accounts** count. Submeters under a master meter allocate an
internal share and incur no separate customer or demand charge. A commercial
demand-metered schedule is never applied by default to residential unit meters:
a meter with no tariff and no explicit default raises rather than inheriting
one.

## Meter topologies

| Mode | Utility accounts | Demand measured at |
|---|---|---|
| `single_pcc` (default) | 1 | Aggregate PCC import |
| `master_with_submeters` | 1 | Master meter |
| `individual_meters` | one per unit | Each meter independently |
| `individual_with_shared_generation` | per unit + generation meter | Each meter independently |

Shared-generation allocation percentages must sum to 100% within tolerance, so
every generated kWh is credited exactly once. The allocation is a **billing
credit** — it does not assert that specific physical electrons reached a
specific unit.

Individually metered billing accepts a `meter_dispatches` table for every
utility account. Where per-unit load profiles are unavailable,
`individual_meters_topology` accepts
`uses_equal_allocation_approximation=True`, which records an explicit
`APPROXIMATION:` warning for display in Review and Run and in results. Without
either actual meter data or that explicit opt-in, billing raises instead of
silently splitting the PCC flow.

Shared-generation allocation percentages can be validated and energy can be
allocated for reporting, but utility billing for that topology deliberately
raises until an applicable NEM/NBT credit rule is configured. Equal division of
the PCC flow would not represent the separately metered accounts.

## Carbon-adjusted operating objective

The scenario comparison distinguishes physical emissions from their optional
monetary valuation:

```
monetized_carbon_cost = carbon_weight_$_per_kgCO2 * emissions_kgCO2
carbon_adjusted_operating_cost =
    total_explicit_operating_cost + monetized_carbon_cost
```

The primary results table shows emissions and the carbon-adjusted operating
cost. The standalone monetized component remains available in detailed data.
Objective values are comparable across strategies evaluated with the same
carbon weight; a carbon-weight sweep changes the scoring rule and should be
interpreted as a cost-versus-emissions tradeoff.

## Extension points (deliberately unimplemented)

These raise `NotImplementedError` with an explanation rather than returning
fabricated data, so no GUI control can silently produce invented numbers:

- `MeasuredLoadAdapter` — Green Button, Modbus, SunSpec, MQTT
- `WeatherDerivedPV` — configuration (location, tilt, azimuth, inverter
  efficiency, system losses) is validated and persistable, but no irradiance
  provider is connected
- `MeasuredInverterPV` — inverter telemetry reports *delivered* power;
  recovering *available* power additionally needs a curtailment signal or a
  clear-sky reference, which is an unresolved modelling decision
- `ExportCompensationMode.TARIFF` — NEM/NBT export rules are not modelled; use
  fixed or CSV export pricing

**Azimuth convention:** 0° north, 90° east, 180° south, 270° west.

## Backward compatibility

Legacy columns remain readable and writable:

| Legacy | Canonical |
|---|---|
| `load_kw` | `native_load_kw` |
| `pv_kw` | `pv_available_kw` |
| `gCO2/kWh` | `carbon_intensity_g_per_kWh` |
| `net_load_kw` | derived: `native_load_kw - pv_available_kw` |

`normalize_any_frame` accepts either schema. `to_legacy_columns` renders back.
Existing result CSVs in `results/` are unchanged, and their historical `week*`
filenames are retained.

The legacy `pv_kw` was ambiguous — available PV in inputs, delivered PV in
dispatch output. The canonical schema splits it into `pv_available_kw` and
`pv_output_kw`, which is what makes curtailment expressible at all.

## Future system-sizing extension

The current scope evaluates operation of an already-built microgrid. A future
system-sizing study may add battery and PV capital cost, installation cost,
inverter replacement, fixed maintenance, project lifetime, discount rate,
incentives, tax credits, and battery replacement schedules. Those lifecycle
cash flows are intentionally excluded from present operating-cost results.


### Municipal import-only storage extension (2026-09-17)

Schema 4 municipal studies enter through `POST /api/v1/municipal/studies`.
The server attaches immutable saved utility-resolution evidence and validates the
complete cycle/account/load before enqueueing in the existing SQLite store.
The pinned worker calls `src/local_web/municipal_study.py`, which invokes
`src/dispatch/municipal.py`. The numerical bill and CVXPY objective share
`src/billing/municipal.py:charge_lines`; an authoritative post-dispatch bill
checks reconciliation. Vectorized tier-regime optimization includes an optional
binary charging-mode fallback when required for physical exclusivity.
Results use existing table/CSV/manifest routes. This path does not run OpenDSS
and rejects PV/export/standby cases. See `Municipal_Utilities.md` for coverage,
TOU optimality bounds, PF-threshold exclusions and browser controls.

### Utility-specific dated residential versions

`RatePlan` accepts versions satisfying `DatedRateVersion`, retaining the shared gap, overlap and coverage checks. SCE's `ResidentialRateVersion` carries structured historical prices and terms; `sce_residential.charges` supplies the same numeric/convex expression to billing and dispatch. Source data are included in Python engine snapshots. Effective dates are bounded by verified filings, and applied versions appear in result tables. The SCE cross-rate/season baseline allocation remains a disclosed study approximation; see `Southern_California.md`.
