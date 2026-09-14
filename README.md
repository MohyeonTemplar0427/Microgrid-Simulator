# Microgrid Simulator

A single, coherent microgrid engineering workflow — real market and carbon
signals in, validated battery dispatch and utility bills out, checked against
a distribution power flow.

The project is the working vehicle for the **[Accelerated 3-Month Energy
Engineer Learning Plan](Energy_Engineering_3_Month_Learning_Plan_Revised_Aug_2026.pdf)**:
a 12-week roadmap in which Python, pandas, optimization, real grid data,
OpenDSS, SQL, Git, SPICE, C++, and Arduino each *extend the same microgrid
model* rather than becoming disconnected tutorials. Every week ends with an
evidence-based completion gate, and nothing advances until the gate passes.

**Status:** Weeks 1–5 complete (Gates A, B, and C passed). The model has since
grown well beyond the original Week-5 scope — a full PG&E commercial tariff
and billing layer, a Tkinter GUI, multi-ISO price adapters, and a pvlib-based
PV and inverter model. **650 tests pass.**

---

## What the model does 

```text
  INPUTS                DATA SYSTEM            DECISION              VALIDATION
  ----------------      -----------------      ----------------      ------------------
  Load profile          Normalized             Rule-based or         OpenDSS 15-min QSTS
  PV / weather     -->  interval table    -->  CVXPY dispatch   -->  voltage, loading,
  Wholesale price       validation, cache,     cost / carbon /       losses, reverse flow,
  Grid carbon           provenance, MySQL      combined objectives   violations
  Utility tariff                               demand-charge aware        |
                                                     |                    v
                                                     +------------> Utility bill
                                                                    energy, demand,
                                                                    customer charges
```

Concretely, the simulator can:

- Ingest **real wholesale prices** (CAISO NP15, ERCOT Houston Hub, PJM Western
  Hub directly or via GridStatus.io) and **real grid carbon intensity**
  (Electricity Maps), with strict time-series validation, provenance capture,
  and offline cache/replay.
- Build **load and PV profiles** — synthetic building archetypes, CSV imports,
  or a physical PV chain (solar position → Hay-Davies plane-of-array
  transposition → SAPM cell temperature → PVWatts or CEC single-diode module →
  inverter conversion and clipping), with named CEC module and inverter part
  numbers when they are known.
- **Optimize battery dispatch** with CVXPY over cost, carbon, and weighted
  combined objectives, including degradation cost, SOC continuity across
  multi-day horizons, and **monthly demand charges in the objective**
  (`cp.max(grid_import_kw[month])` — peak reduced from 228 kW to 113.5 kW
  under PG&E B-10).
- **Bill the result** against 12 registered PG&E commercial tariffs (B-1, B-6,
  B-10, B-19 mandatory/voluntary/Option R/Option S, B-20 and its options) with
  seasonal TOU periods, demand-charge bases, per-TOU-period breakdowns,
  effective dating, and configurable meter topology.
- **Replay the schedule through OpenDSS** at 15-minute resolution and report
  per-interval voltage, line and transformer loading, losses, reverse flow,
  violations, and feasibility.
- **Persist everything to MySQL** — site, run configuration, signal
  provenance, dispatch decisions, and power-flow results — so a study can be
  reconstructed and queried after the fact.

---

## Quick start

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Run the test suite:

```bash
python3 -m pytest -q
```

Launch the guided GUI:

```bash
python3 -m src.simulation.graphical_interface
```

Run the OpenDSS validation workflow:

```bash
python3 -m src.opendss.validation
```

Run the real-signal market experiment:

```bash
python3 -m src.signal_pipeline.market_data_integration
```

> **Interpreter note.** Use a Python that has `opendssdirect` and
> `mysql-connector` installed. Without them nine test modules fail to
> *collect*, and the suite looks broken when it is not — check the interpreter
> before debugging a low collected count.

API keys (`ELECTRICITY_MAPS_API_KEY`, `GRIDSTATUS_API_KEY`, `PJM_API_KEY`,
`NSRDB_API_KEY`) live in a gitignored `.env`. **No test ever calls a live
API** — every provider is mocked, and the weather and price paths run entirely
from committed fixtures and the on-disk cache.

---

## Repository layout

| Path | Contents |
|---|---|
| `src/timeseries/` | Normalized interval table, schema, and validation |
| `src/profiles/` | Load and PV sources, solar geometry, PV/inverter models, NSRDB weather |
| `src/surplus/` | PV-first surplus allocation, power balance, carbon metrics |
| `src/billing/` | Tariff registry, PG&E schedules, charges, meter topology |
| `src/signal_pipeline/` | Market and carbon providers, validation, caching, provenance |
| `src/dispatch/` | Battery model, CVXPY single-day and multi-day optimization |
| `src/opendss/` | Feeder model, QSTS replay, electrical validation |
| `src/database/` | MySQL connector and loading |
| `src/simulation/` | Tkinter GUI, console interface, analysis orchestration |
| `sql/` | Schema, seed data, engineering queries |
| `spice/` | KiCad project for the Weeks 6–7 circuit work |
| `docs/` | Architecture, tariff reference, weekly completion recaps |
| `test/` | 29 test modules, 650 tests |

**Read [`docs/Microgrid_Backend_Architecture.md`](docs/Microgrid_Backend_Architecture.md)
before changing the backend.** It documents the decisions that cannot be
inferred from the code: PV-first allocation, the inclusive→exclusive date
conversion, demand-charge rules, and tariff versioning.

Tariff rates and structures are documented in
[`docs/PGE_Tariff_Reference.md`](docs/PGE_Tariff_Reference.md), generated from
the registry by `tools/generate_tariff_reference.py` — regenerate it rather
than editing it by hand.

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

---

## Curriculum progress

The 12-week plan, with the current state of each week.

| Week | Focus | Status |
|---|---|---|
| 1 | Dispatch and optimization foundation | ✅ Complete |
| 2 | Real-data consolidation and software gate | ✅ Complete — [recap](docs/Week_2_Completion_Recap.md) |
| 3 | OpenDSS fundamentals | ✅ Complete — [recap](docs/Week_3_Completion_Recap.md) |
| 4 | OpenDSS with DER dispatch | ✅ Complete — [recap](docs/Week_4_Completion_Recap.md) |
| 5 | SQL, provenance, reproducibility | ✅ Complete — [recap](docs/Week_5_Completion_Recap.md) |
| 6 | SPICE fundamentals | ⏳ [Curriculum revised](docs/Weeks_6_7_SPICE_Curriculum_Revision.md); KiCad project scaffolded, no circuits yet |
| 7 | SPICE for power electronics | ⏳ Planned |
| 8 | Rolling control and operational robustness | ⬜ Not started |
| 9 | Network-aware dispatch | ⬜ Not started |
| 10 | C++ fundamentals through model translation | ⬜ Not started |
| 11 | Arduino and embedded monitoring | ⬜ Not started |
| 12 | Integrated capstone | ⬜ Not started |

### Completion gates

| Gate | Condition | Status |
|---|---|---|
| A — Start Week 2 | Sessions 1–6 done; real-carbon workflow demonstrated | ✅ Passed |
| B — Start OpenDSS | Real price and carbon merged; baselines and data checks pass; handoff documented | ✅ Passed |
| C — Finish Month 1 | Base feeder validated; all scenarios replayed; electrical results reported | ✅ Passed |
| D — Start network-aware control | Rolling controller has fallbacks; feeder constraints sourced and reproducible | ⬜ Open |
| E — Capstone complete | Full package reproducible by another reader | ⬜ Open |

### Work beyond the original plan

Several capabilities were added because the modelling demanded them, and are
not attributable to a numbered week:

- **A utility billing layer.** Twelve PG&E commercial tariffs with TOU
  seasons, demand-charge bases, effective dating, per-period bill breakdowns,
  and carbon monetization. This is what turns "kWh shifted" into "dollars
  saved," and it is what made demand-charge-aware optimization worth building.
- **Demand-charge-aware optimization**, which changed the character of the
  dispatch problem — the binding economics of a commercial site are the
  monthly peak, not the energy arbitrage spread.
- **A guided Tkinter GUI** covering region, price mode, tariff, load and PV
  source, meter topology, carbon weighting, and CSV export, with saved
  preferences between runs.
- **Multi-ISO price adapters** (CAISO, ERCOT, PJM direct, PJM via
  GridStatus.io) behind one provider interface.
- **A physical PV and inverter model** in two phases — a PVWatts-style generic
  array, and an equipment-specific CEC single-diode model with real module and
  inverter part numbers, string arrangement, and MPPT distribution.

---

## Known gaps and limitations

Stated plainly, because a simulator that hides its boundaries is worse than
one that does not.

- **`src/surplus/` has no production consumer.** The allocation logic, both
  power-balance validators, and the carbon monetization are imported only by
  their tests, and are unreachable from the GUI. This is the largest open
  item.
- **The optimizer targets only `MAXIMUM`-basis demand.** It sums
  maximum-basis demand components and ignores peak-period ones, so on B-20 it
  chases $39.08/kW of an $80.43/kW summer peak-hour cost. The mechanism works;
  the coverage is incomplete.
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
