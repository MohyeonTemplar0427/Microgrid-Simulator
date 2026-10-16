# Signal pipeline

Retrieves electricity-market prices and grid carbon intensity, normalizes
both onto a common 15-minute schema, and hands them to the dispatch layer.

Provider-specific quirks live in `providers/`. Everything downstream of an
adapter sees one schema and never branches on which ISO served the request.

## The provider interface

Every market adapter subclasses `providers.base.MarketProvider` and implements
one method:

```python
fetch_energy_prices(
    start_time: pd.Timestamp,
    end_time: pd.Timestamp,
    location: str,
) -> pd.DataFrame
```

The window is half-open, `[start_time, end_time)`. Naive timestamps are
localized to the provider's own timezone.

The returned frame always has exactly two columns:

| Column | Type | Units |
|---|---|---|
| `timestamp` | tz-aware datetime, in the region's named timezone, sorted ascending, no duplicates | — |
| `price_per_kWh` | float | **$/kWh** |

Both ISOs publish LMPs in **$/MWh**. The division by 1000 happens once, in
`normalize_price_frame`, never in adapter code.

Carbon retrieval stays separate, in `electricity_maps_data.py`, and normalizes
to **gCO2/kWh**.

Call an adapter through the registry rather than constructing it directly:

```python
from src.signal_pipeline.gridstatus_data import fetch_energy_prices

prices = fetch_energy_prices(
    start_time, end_time, "51288", provider="pjm",
)
```

## Supported providers and regions

A region maps one user-facing name to five things that are **not**
interchangeable across ISOs — a CAISO node name means nothing to PJM, and
neither ISO's identifier is an Electricity Maps zone.

| Region | Market provider | Market location | Carbon zone | Timezone |
|---|---|---|---|---|
| `caiso_np15` | `caiso` | `TH_NP15_GEN-APND` (LMP node *name*) | `US-CAL-CISO` | `America/Los_Angeles` |
| `ercot_houston_hub` | `ercot` | `HB_HOUSTON` (*settlement point* name) | `US-TEX-ERCO` | `America/Chicago` |
| `pjm_western_hub` | `pjm` | `51288` (numeric *pnode id*) | `US-MIDA-PJM` | `America/New_York` |
| `pjm_western_hub_gridstatus` | `gridstatus_io` | `WESTERN HUB` (hosted location name) | `US-MIDA-PJM` | `America/New_York` |

Select one on the experiment config:

```python
config = ExperimentConfig(
    start_date="2026-08-25",
    number_of_days=2,
    region="pjm_western_hub",
)
```

Individual fields (`market_location`, `electricity_maps_zone`, `timezone`) can
be overridden and take precedence over the region's defaults.

### Shared configuration resolution

`source_config.resolve_region_config` resolves and validates the preset and
overrides for both `ExperimentConfig` and the guided `resolve_live_api_config`
path. `fetch_region_prices` uses the same resolver for explicit `RegionConfig`
objects. Each result owns a copy of its provider options; changing it cannot
change the registry or another study.

The hosted PJM preset explicitly selects `pjm_lmp_real_time_5_min`, its source
timezone, and a five-minute native interval. Those options now survive the
guided workflow into adapter construction and the price-cache identity, along
with any explicit dataset/column overrides. Previously that workflow dropped
the options and could retrieve the raw adapter's default dataset instead.
Old optionless hosted cache entries are not reused for the corrected preset.

`provider_options` contains non-secret adapter settings. Unknown fields,
credentials in configuration, empty datasets and invalid native intervals are
rejected before retrieval. Switching `market_provider` requires a location
explicitly expressed in that provider's format and discards the old provider's
options. Switching to a hosted provider also requires its dataset, source
timezone and native interval, or selection of its complete region preset.
Changing only the study timezone does not reinterpret the source timezone.

Direct PJM and hosted GridStatus remain separate choices. Missing credentials,
archive limits, missing intervals and retrieval errors propagate from the
selected adapter; they never trigger a switch of provider, dataset or node.
The low-level `get_provider` compatibility API still filters irrelevant
constructor options, such as a CAISO throttle passed while iterating providers.
Region-based configuration is stricter and rejects unknown options.

CSV, retail tariff and fixed-retail price sources retain their own paths.
This refactor does not change weather/carbon source selection, retrieval
limits, units, or utility coverage; wholesale LMP remains separate from retail
billing. Configuration resolution performs no I/O and never loads credentials.

### Provider differences that matter

|  | CAISO | ERCOT | PJM |
|---|---|---|---|
| Credentials | none | none | **`PJM_API_KEY` required** |
| gridstatus call | `get_lmp` | **`get_spp`** | `get_lmp` |
| Price concept | LMP | **Settlement Point Price** | LMP |
| Source column | `LMP` | **`SPP`** | `LMP` |
| Native market | `REAL_TIME_15_MIN` | `REAL_TIME_15_MIN` | `REAL_TIME_5_MIN` — **no 15-minute market exists** |
| Interval handling | used as-is | used as-is | 5-minute prices averaged into 15-minute buckets |
| Location form | node name | settlement point name | numeric pnode id |
| History available | gridstatus-dependent | gridstatus-dependent | **186 days** for 5-minute real-time data |
| Chunking | one request; gridstatus splits internally | one request | 30-day chunks, de-duplicated at the boundaries |

PJM's 5-minute averaging is a plain mean, which is the correct time-weighted
average only because the source intervals are equal-duration.

ERCOT settlement points come in three flavours — trading hubs (`HB_*`), load
zones (`LZ_*`) and resource nodes. All three are passed the same way. The
adapter queries every location type by default; narrow it by constructing
`ERCOTProvider(location_type="Trading Hub")` if a name is ambiguous.

## Environment variables

Use private process environment variables or this checkout's ignored `src/.env`:

| Variable | Required for |
|---|---|
| `ELECTRICITY_MAPS_API_KEY` | all carbon retrieval |
| `PJM_API_KEY` | the `pjm` market provider only |
| `GRIDSTATUS_API_KEY` | the explicitly selected `gridstatus_io` provider only |

The `caiso` and `ercot` providers need no credentials.

Signal CLI entry points and the legacy guided analysis use the shared
`src/credentials.py` loader at execution time, restricted to these three names.
Existing process values win over file values, including during dotenv variable
interpolation. Provider imports do not read dotenv files or snapshot keys into
module globals. Direct provider callers supply credentials explicitly or through
their environment. Keys are never logged, printed, or committed; `.env` is ignored.

Weather retrieval and the browser/desktop launchers use their own narrower
allowlists. Authentication and database settings are never loaded by this helper.

## Integrated schema

`merge_real_market_data` produces the columns the dispatch layer consumes:

`timestamp`, `load_kw`, `pv_kw`, `net_load_kw`, `price_per_kWh`, `gCO2/kWh`

`load_kw` and `pv_kw` remain **site profile inputs**. A regional ISO API
reports prices for a pricing node, not the load or PV production of any
particular site, and is never used as a source for them.

## Price sources

A wholesale market node is not a customer retail tariff, so they are separate
source types in `price_sources.py`. All four produce `timestamp` /
`price_per_kWh` in $/kWh over an `AnalysisHorizon`.

| Mode | Configured with | Notes |
|---|---|---|
| `wholesale_market` | provider + node | Delegates to the provider registry; $/MWh → $/kWh |
| `fixed_retail` | one nonnegative $/kWh | Repeated for every interval |
| `time_of_use` | `TimeOfUseSchedule` of periods | Priced on **local wall-clock** hour and weekday |
| `csv` | frame, column name, `source_unit` | `$/kWh` or `$/MWh`; units declared, never guessed |

### Time-of-use schedules

A `TimeOfUsePeriod` carries a name, a price, `start_hour` (inclusive),
`end_hour` (exclusive) and a set of weekdays (Monday 0 … Sunday 6). A period
may wrap past midnight. A schedule must cover every interval, or set
`default_price_per_kWh`.

- **Weekends** — expressed through each period's `days` set.
- **Daylight saving** — periods are matched against the *local* hour of each
  tz-aware timestamp, so a 4pm peak stays at 4pm local on both sides of a
  transition. A spring-forward day simply has fewer intervals in the skipped
  hour, a fall-back day more in the repeated one.
- **Holidays are not implemented.** A public holiday is priced at its normal
  weekday rate. Real tariffs usually bill holidays off-peak, so a horizon
  containing one will overstate cost. Implementing this needs a holiday
  calendar per utility, not per ISO.

## Daylight saving

Do not assume 96 intervals per day. A spring-forward local day has 92 and a
fall-back day has 100. Interval coverage is checked by walking the observed
timestamps (`check_intervals`) rather than comparing against a fixed count.
`validate_price_data`'s `expected_rows` argument is retained for existing
callers but should be left unset.

## Adding another provider

1. Create `providers/<name>.py` with a `MarketProvider` subclass. Set
   `default_timezone`, `native_interval_minutes`, and — where the API imposes
   them — `max_chunk_days` and `archive_limit_days`. Anything the adapter
   needs at construction (a key, a throttle, a location type) goes in its
   `__init__`; `get_provider` passes through only the options that adapter
   declares, so callers never branch on which provider they are using.
2. In `fetch_energy_prices`, call the vendor client, then reuse the shared
   helpers: `require_aware_timestamps`, `normalize_price_frame`,
   `iterate_chunks` / `combine_chunks`, `trim_to_window`,
   `resample_to_target_interval`, `check_intervals`. Raise the typed errors in
   `providers.base` rather than bare `ValueError`.
3. Register the class in `PROVIDER_REGISTRY` in `providers/__init__.py`.
4. Add a `RegionConfig` entry in `region_config.py`.
5. Add tests with a fabricated response frame. Tests must not hit a live API.

Put nothing provider-specific outside step 1 and step 2's adapter body.
