# Microgrid Simulator

**How can a microgrid optimize its operation for a specific goal set by the
consumer?**

That goal might be minimizing life-cycle carbon emissions over a given
operating range, minimizing explicit cost — the bill you actually pay the
utility — or the more ambitious case: minimizing your bill while accounting
for the social cost of the carbon you cause. This repository is a working
answer to that question, from real market and carbon signals through battery
dispatch and a utility bill, validated against a distribution power flow.

---

<<<<<<< HEAD
## About this project

Hi, I am [MohyeonTemplar0427](https://github.com/MohyeonTemplar0427), a UC
Berkeley Energy Engineering 2026 grad. This repo is a personal project marking
a milestone in my undergraduate journey, combining what I learned as an energy
engineer at Cal.

Being an energy engineer still feels vague to me. My interests during my
undergraduate were power electronics, circuit design, signal processing,
control, and programming — so I defined myself as something closer to an
electrical engineer. But I still feel I lack fundamental capabilities I
assumed most electrical engineers would have, which makes my own abilities
seem even more vague to me.

This project is my first effort to take those separate pieces of knowledge and
build the seemingly vague concept of a *microgrid* into a structured, specific
program that helps users understand the system easily. The process of
combining the very things that made my profession feel vague turned out to be
fruitful: I revisited every concept I had learned but nearly lost from memory,
consolidated my understanding of each one, and ultimately of the system
itself.

The project is an extension of a class team project and my undergraduate
capstone research. Although it has "microgrid" in the name, it can be used for
residential cases as well — a feature I will be updating soon.

---

## What's in the repo

Ten major components, each one a package under `src/`.

### 1. Application and simulation workflow — [`src/simulation/`](src/simulation)
Provides desktop and console interfaces, collects simulation settings,
coordinates analyses, and displays results. Use the local GUI for the current
version; later updates will move these functions to the web.

### 2. Load and solar profiles — [`src/profiles/`](src/profiles)
Creates building demand and PV generation profiles from synthetic inputs,
weather data, and PV equipment models. The PV chain runs solar position →
Hay-Davies plane-of-array transposition → SAPM cell temperature → PVWatts or a
CEC single-diode module → inverter conversion and clipping. Named CEC module
and inverter part numbers are supported when they are known.

### 3. Market and carbon data — [`src/signal_pipeline/`](src/signal_pipeline)
Loads electricity prices and grid carbon intensity from external providers or
files and aligns them to the study period. I used **Electricity Maps** and
**[GridStatus.io](https://gridstatus.io)**. The current version requires you
to set up your own API keys in `src/.env` (see [Quick start](#quick-start)).
Regions available: CAISO NP15, ERCOT Houston Hub, and PJM Western Hub, the
last reachable either through PJM directly or through GridStatus.io.

### 4. Time-series framework — [`src/timeseries/`](src/timeseries)
Defines a common interval-table format and validates timestamps, units, and
missing data. Every other layer speaks this format.

### 5. Battery dispatch — [`src/dispatch/`](src/dispatch)
Models battery operation and compares five strategies: no-battery,
rule-based, cost-optimal, carbon-optimal, and combined. Optimization uses
CVXPY and includes degradation cost, SOC continuity across multi-day horizons,
and monthly demand charges in the objective.

### 6. PV surplus allocation — [`src/surplus/`](src/surplus)
Accounts for excess solar energy sent to battery charging, flexible loads,
export, or curtailment. *(Implemented and tested, but not yet reachable from
the GUI — see [Known gaps](#known-gaps-and-limitations).)*

### 7. Metering and billing — [`src/billing/`](src/billing)
Represents meter arrangements and tariffs, then calculates electricity
charges. Twelve PG&E commercial tariffs are registered — B-1, B-6, B-10, B-19
(mandatory, voluntary, Option R, Option S), and B-20 (standard, Option R,
Option S) — with seasonal time-of-use periods, demand-charge bases, effective
dating, and per-period bill breakdowns.

### 8. Baseline analysis — [`src/analysis/`](src/analysis)
Supports no-battery analysis and configuration of carbon weights for comparing
cost against emissions.

### 9. Electrical network validation — [`src/opendss/`](src/opendss)
Replays dispatch schedules through OpenDSS to assess voltage, equipment
loading, losses, and operating violations, at 15-minute resolution across the
full schedule.

### 10. Database storage — [`src/database/`](src/database)
Stores study inputs, provenance, dispatch decisions, and power-flow results in
MySQL and supports engineering queries. Schema and queries live in
[`sql/`](sql).

### How the pieces connect
=======
## What the model does 
>>>>>>> a4710a73f6c7b7168635eb41ce515a6ec8841684

```text
  INPUTS                DATA SYSTEM            DECISION              VALIDATION
  ----------------      -----------------      ----------------      ------------------
  Load profile     (2)  Interval table    (4)  Rule-based or    (5)  OpenDSS QSTS    (9)
  PV / weather     (2)  validation,            CVXPY dispatch        voltage, loading,
  Wholesale price  (3)  provenance,            cost / carbon /       losses, reverse
  Grid carbon      (3)  MySQL           (10)   combined              flow, violations
  Utility tariff   (7)  surplus alloc.   (6)   demand-aware               |
                                                     |                    v
                                                     +------------> Utility bill  (7)
                                                                    vs. baseline   (8)
```

---

## Quick start

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Create `src/.env` with your own API keys. The file is gitignored and is never
committed:

```bash
ELECTRICITY_MAPS_API_KEY=your_key_here
GRIDSTATUS_API_KEY=your_key_here
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=your_database
MYSQL_USER=your_user
MYSQL_PASSWORD=your_password
```

Optional keys: `PJM_API_KEY` for reaching PJM directly rather than through
GridStatus.io, and `NSRDB_API_KEY` plus `NSRDB_API_EMAIL` for fetching
satellite irradiance. Neither is needed to run the simulator — CAISO and ERCOT
prices require no credentials, and the weather path works fully offline from a
CSV.

Launch the guided GUI:

```bash
python3 -m src.simulation.graphical_interface
```

Run the test suite — **650 tests**:

```bash
python3 -m pytest -q
```

> **Interpreter note.** Use a Python that has `opendssdirect` and
> `mysql-connector` installed. Without them nine test modules fail to
> *collect*, and the suite looks broken when it is not — check the interpreter
> before debugging a low collected count.

Other entry points:

```bash
python3 -m src.opendss.validation
```

```bash
python3 -m src.signal_pipeline.market_data_integration
```

**No test ever calls a live API.** Every provider is mocked, and the weather
and price paths run from committed fixtures and an on-disk cache, so the suite
costs no API quota and needs no secret.

---

## Engineering conventions

Three conventions are repeated here because violating them is silent and
costly:

- **Never compute intervals as `days * 96`.** DST days have 92 or 100
  intervals. Counts come from the generated index.
- **Use `pd.DateOffset(days=n)`, never `pd.Timedelta(days=n)`** for calendar
  days. `Timedelta` adds exactly 24 h and drifts an hour across DST.
- **Never sum demand charges across intervals.** One peak per billing month.

A fourth is a performance cliff rather than a correctness one: the CVXPY
constraints in `single_day_analysis.py` are **vectorized** — the SOC recursion
and the interval power balance are two array constraints, not two per
interval. The loop form produces an identical feasible set and fails no test,
but at 2,880 intervals it builds 5,766 constraint objects instead of 8 and
runs roughly 40× slower (16.2 s → 1.15 s for a 30-day, 5-scenario run).

**Read [`docs/Microgrid_Backend_Architecture.md`](docs/Microgrid_Backend_Architecture.md)
before changing the backend.** It documents the decisions that cannot be
inferred from the code: PV-first allocation, the inclusive→exclusive date
conversion, demand-charge rules, and tariff versioning.

Tariff rates and structures are documented in
[`docs/PGE_Tariff_Reference.md`](docs/PGE_Tariff_Reference.md), generated from
the registry by `tools/generate_tariff_reference.py` — regenerate it rather
than editing it by hand.

---

## Learning roadmap

The project doubles as the vehicle for a
[12-week energy-engineering learning plan](Energy_Engineering_3_Month_Learning_Plan_Revised_Aug_2026.pdf),
in which Python, pandas, optimization, real grid data, OpenDSS, SQL, Git,
SPICE, C++, and Arduino each extend this same model rather than becoming
disconnected tutorials. Each week ends with an evidence-based completion gate.

| Week | Focus | Status |
|---|---|---|
| 1 | Dispatch and optimization foundation | ✅ Complete |
| 2 | Real-data consolidation and software gate | ✅ [Recap](docs/Week_2_Completion_Recap.md) |
| 3 | OpenDSS fundamentals | ✅ [Recap](docs/Week_3_Completion_Recap.md) |
| 4 | OpenDSS with DER dispatch | ✅ [Recap](docs/Week_4_Completion_Recap.md) |
| 5 | SQL, provenance, reproducibility | ✅ [Recap](docs/Week_5_Completion_Recap.md) |
| 6 | SPICE fundamentals | ⏳ [Curriculum revised](docs/Weeks_6_7_SPICE_Curriculum_Revision.md); KiCad project scaffolded |
| 7 | SPICE for power electronics | ⏳ Planned |
| 8 | Rolling control and operational robustness | ⬜ Not started |
| 9 | Network-aware dispatch | ⬜ Not started |
| 10 | C++ fundamentals through model translation | ⬜ Not started |
| 11 | Arduino and embedded monitoring | ⬜ Not started |
| 12 | Integrated capstone | ⬜ Not started |

Gates **A**, **B**, and **C** have passed. Gate D (network-aware control) and
Gate E (capstone) remain open.

### Beyond the original plan

Several capabilities were added because the modelling demanded them, and
belong to no numbered week:

- **A utility billing layer** — twelve PG&E commercial tariffs with TOU
  seasons, demand-charge bases, effective dating, and carbon monetization.
  This is what turns "kWh shifted" into "dollars saved."
- **Demand-charge-aware optimization**, which changed the character of the
  problem: the binding economics of a commercial site are the monthly peak,
  not the energy arbitrage spread. Putting `cp.max(grid_import_kw[month])` in
  the objective cut the peak from 228 kW to 113.5 kW under PG&E B-10.
- **A guided Tkinter GUI** covering region, price mode, tariff, load and PV
  source, meter topology, carbon weighting, and CSV export, with preferences
  saved between runs.
- **Multi-ISO price adapters** behind one provider interface.
- **A physical PV and inverter model** in two phases — a PVWatts-style generic
  array, and an equipment-specific CEC single-diode model with real part
  numbers, string arrangement, and MPPT distribution.

### Planned next

- **Move the application to the web**, so the workflow is not limited to a
  local desktop GUI.
- **Residential support.** Residential and multifamily load archetypes already
  exist, but every registered tariff is a PG&E *commercial* schedule; the
  residential case needs residential rate schedules before the bills mean
  anything.
- **Finer and more realistic daily load and PV trends.**

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
