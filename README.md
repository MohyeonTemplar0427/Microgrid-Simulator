# Microgrid Simulator

## About this project

Hi, my name is Junha Yang, a 2026 UC Berkeley graduate with a B.S. in
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

The simulator provides framework to analyze how solar and battery operating
strategies affect electricity bills, grid-import emissions, and electrical
performance. It combines load and PV profiles with electricity prices, grid
carbon intensity, and utility tariffs, using CVXPY to optimize battery schedules
for cost, emissions, or a weighted combination of both. OpenDSS checks voltage,
equipment loading, and losses at each simulation interval through quasi-static
power flow. Dynamic and transient analysis remain future development.

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

- **Interface coverage:** The standalone `src/surplus/` module and multi-account
  billing are not exposed in the GUI.
- **Measured inputs:** Direct meter/device integrations and measured inverter
  PV modeling remain unimplemented.
- **Billing scope:** Tariff and export-credit support is limited to documented
  utilities, account types, and dates. Shared solar billing across separate
  utility accounts remains unsupported.
- **Network assumptions:** Electrical validation uses representative three-phase
  and residential network models with assumed equipment parameters.
- **Analysis scope:** Electrical checks run after optimization.
  Network-constrained dispatch and transient analysis remain future development.

---

## Future Development Plan

### Location-specific load forecasting

Location-specific load forecasting is not yet complete. Current studies use
modeled or imported demand profiles. Future work includes developing and
validating forecasts for a selected location using historical electricity
consumption, weather, and calendar data.

### Dynamic and transient analysis

Current electrical checks use quasi-static time-series (QSTS) power flow to
evaluate steady-state voltage, equipment loading, and losses at each simulation
interval. Dynamic and transient analysis remain future work.

Proposed development:

1. **Select critical operating points** from QSTS results, such as maximum
   battery discharge, low voltage, or heavy equipment loading.
2. **Study disturbances** such as faults, inverter trips, sudden load changes,
   and grid disconnection to assess voltage recovery, protection operation,
   and stability.
3. **Refine operating limits** and dispatch constraints using the findings.
