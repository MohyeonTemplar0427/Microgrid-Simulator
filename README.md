# Microgrid Simulator

Microgrid Simulator is a Python project for studying how solar generation and
battery storage affect electricity bills, grid-related carbon emissions, and
electrical network operation.

It combines load and solar profiles, electricity prices, grid carbon intensity,
and utility tariffs to compare battery operating strategies. CVXPY optimizes
battery schedules for cost, emissions, or a weighted combination of both.
OpenDSS evaluates those schedules through time-series power-flow simulations
to check voltage, equipment loading, and network losses.

The central question is: **How should a microgrid operate to meet a user's
cost and emissions goals while respecting battery limits, and what electrical
constraints does the resulting schedule reveal?**

---

## About this project

Hi, my name is Junha Yang, and I’m a 2026 UC Berkeley graduate with a B.S. in
Energy Engineering. This repository is a personal extension of a class team
project on microgrids and my undergraduate capstone research.

Due to the broad range of disciplines within the field, being an energy
engineer still feels vague to me, even after graduation. This project is my
first effort to bring separate pieces of knowledge together and translate
abstract concepts within energy engineering into a structured program that
helps me organize and strengthen my foundational knowledge. The process has
been rewarding: revisiting, applying, and connecting concepts from my studies
within this project helped me develop a more concrete understanding of the
system as a whole.

The simulator combines electricity demand, solar generation, electricity
prices, grid carbon intensity, and utility tariffs to optimize battery
schedules for cost, emissions, or both. It compares the resulting electricity
bills and emissions across operating strategies, then uses OpenDSS to evaluate
voltage, equipment loading, and network losses. This allows users to explore
how operating decisions affect both economic outcomes and electrical
performance. The current electrical feasibility check uses quasi-static
power-flow snapshots at individual simulation time steps. The model does not
yet evaluate the system’s transient response; that analysis is left for future
development.

---

## What's in the repo

| Component | Purpose |
|---|---|
| [Application](src/simulation) | Configures studies, runs simulations, and displays results. |
| [Load and solar profiles](src/profiles) | Generates electricity demand and solar production profiles. |
| [Market and carbon data](src/signal_pipeline) | Retrieves and aligns electricity prices and grid carbon intensity. |
| [Metering and billing](src/billing) | Calculates electricity charges using meter arrangements and utility tariffs. |
| [Battery dispatch](src/dispatch) | Compares operating strategies and optimizes battery schedules. |
| [Time-series framework](src/timeseries) | Standardizes data and validates timestamps, units, and missing values. |
| [PV surplus allocation](src/surplus) | Models excess solar allocation; not connected to the GUI. |
| [Baseline analysis](src/analysis) | Provides no-battery baselines and cost–emissions comparisons. |
| [Electrical validation](src/opendss) | Checks voltage, equipment loading, and losses using OpenDSS. |
| [Database storage](src/database) | Stores study inputs, sources, and results in MySQL. |

Documentation: [Local web application](docs/Local_Web_Application.md) · [ESS catalog and annual solar optimization](docs/ESS_Equipment_Catalog.md)

---

## Quick start

Run from the repository root. If Conda’s `(base)` environment is active, run
`conda deactivate` first.

**1. Install dependencies**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**2. Configure API access**

Create `src/.env`, which is excluded from Git:

```dotenv
# Required: historical grid carbon data
ELECTRICITY_MAPS_API_KEY=your_key_here

# Needed only for NSRDB historical weather
NSRDB_API_KEY=your_key_here
NSRDB_API_EMAIL=you@example.com
```

Your Electricity Maps key must provide access to the requested historical
data. Clear-sky solar calculations do not require NSRDB access.

**3. Launch the application**

```bash
python -m src.local_web.server
```

Open <http://127.0.0.1:8765>. Keep the terminal running; press `Ctrl+C` to stop.

**4. Run tests (optional)**

```bash
python -m pytest -q
```

See the [Local web application guide](docs/Local_Web_Application.md) for
configuration and saved studies.

---

## Engineering conventions

- **Time intervals:** Generate timestamps explicitly; do not assume every day
  has 96 fifteen-minute intervals.
- **Calendar days:** Use `pd.DateOffset(days=n)` to preserve local time across
  daylight saving changes.
- **Demand charges:** Calculate each demand component from its applicable
  billing-period peak.
- **Optimization:** Keep CVXPY battery constraints vectorized for efficient
  time-series studies.

Read the [backend architecture](docs/Microgrid_Backend_Architecture.md) before
changing the backend. Regenerate the [PG&E tariff reference](docs/PGE_Tariff_Reference.md)
using [the reference generator](tools/generate_tariff_reference.py) after tariff
changes.

---

## Known gaps and limitations

Stated plainly, because a simulator that hides its boundaries is worse than
one that does not.

- **`src/surplus/` has no production consumer.** The allocation logic, both
  power-balance validators, and the carbon monetization are imported only by
  their tests and are unreachable from the GUI. This is the largest open item.
- **The optimizer targets only `MAXIMUM`-basis demand.** It sums maximum-basis
  demand components and ignores peak-period ones, so on B-20 it chases
  $39.08/kW of an $80.43/kW summer peak-hour cost. The mechanism works; the
  coverage is incomplete.
- **Two meter topologies are built but not offered** in the GUI.
  `individual_meters` is implemented and merely unwired; `shared_generation`
  is blocked on unmodelled NEM/NBT credit rules.
- **Holidays are priced at the ordinary weekday rate.** Harmless for the PG&E
  B-series, whose periods all apply "every day, including weekends and
  holidays"; it matters for ISO price shaping and any future weekday-only
  tariff.
- **`dispatch_scenarios.py` uses none of the four backend layers**, and
  `market_data_integration.py` reaches into billing for a single function.

### Deliberately not implemented

These raise `NotImplementedError` **on purpose**, so that no GUI control can
silently produce an invented number:

- Measured load adapters (Green Button, Modbus, SunSpec, MQTT)
- Measured inverter PV — delivered ≠ available power, and the modelling is
  unresolved
- `ExportCompensationMode.TARIFF` — NEM and NBT are not modelled
- Shared-generation billing — allocation percentages exist, but splitting PCC
  flow without the credit rules would fabricate per-meter bills

Unverified placeholder parameters are not presented as real system data.
Anything used for future work should come from manufacturer documentation,
utility filings, applicable standards, or a clearly identified engineering
assumption.

---

## Future development: dynamic and transient analysis

Dynamic and transient electrical analysis are **not implemented**. The current
OpenDSS workflow uses 15-minute quasi-static time-series (QSTS) simulation:
each interval is solved as a separate steady-state power flow, evaluating
settled voltage, current, equipment loading, and losses once the network has
reached a new operating point.

### Why QSTS is appropriate today

- The dispatch schedule that drives the simulation operates on 15-minute
  intervals, so there is no need to resolve behavior faster than that.
- Most electromagnetic transients — switching surges, fault-current spikes,
  controller response — settle in milliseconds to a few seconds, far shorter
  than one interval.
- The current objective is to characterize sustained operating conditions
  across a full schedule, not sub-second behavior.
- This is a scoping choice, not a claim that transients do not occur. They
  happen between the snapshots QSTS solves; they are simply outside the
  analysis boundary.

### Proposed future workflow

1. Run QSTS across the complete operating schedule, as today.
2. Identify critical intervals — maximum charging, maximum discharging,
   minimum voltage, maximum equipment loading.
3. Use the solved network state from each critical interval as the initial
   condition for a dynamic or transient study.
4. Apply an event of interest: a fault, an inverter trip, a sudden load
   change, a switching event, or a grid disconnection.
5. Evaluate current peaks, voltage recovery, protection timing, stability, and
   inverter ride-through.
6. Feed any operational restriction discovered back into the dispatch
   optimizer, so the schedule respects limits QSTS alone cannot reveal.

### Data that would improve the existing QSTS model

Line resistance, reactance, length, and ampacity; transformer voltage ratio,
impedance, and kVA rating; load real and reactive power and power factor; PV
and battery inverter kVA and reactive capability; bus-voltage limits;
equipment-loading limits; and explicit load, PV, and battery sign conventions.

### Data required for transient studies

Protection curves and clearing times; fault type, location, and impedance;
inverter current limits and controller parameters; PLL and inner-control
behavior; voltage and frequency ride-through settings; trip and reconnection
timing; transformer saturation and inrush data; motor inertia and dynamic-load
models; and subsecond input and measurement profiles.

OpenDSS itself supports fault studies, harmonic analysis, duty-cycle studies,
and basic dynamics. Detailed electromagnetic-transient (EMT) work may require
a dedicated EMT tool.
