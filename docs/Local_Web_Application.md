# Local browser application

The browser interface is labeled **Web UI v1.0.0**. This identifies the current
website page design; the simulation engine snapshot, request schema, and future
hosted deployment have separate version or configuration lifecycles.

## Current server transport

The launcher now uses Waitress. Explicit hosted mode prepares a same-host HTTPS
proxy and requires OIDC; the backend still binds only to 127.0.0.1. See
[Web hosting preparation](Web_Hosting.md) for configuration and remaining release
requirements. Nothing is publicly deployed by these changes.

## Current access-control checkpoint

Provider-neutral OIDC sign-in and per-user authorization are available for a
loopback rehearsal. See [Web access control](Web_Access_Control.md) for setup,
legacy-data quarantine, session behavior, and migration. Authentication is no
longer wholly deferred, but production hosting and HTTPS remain unimplemented.
The original local-mode instructions below still apply to a separate trusted
local store. Some feature descriptions below are historical; the access-control
document and current route handlers describe the new security boundaries.


This application runs the existing Python simulation engine on the local
computer and displays its result tables in a browser. It uses Waitress and SQLite; no Node build, cloud account, or PostgreSQL
server is required. Install requirements.txt, which now includes Authlib and
joserfc for OIDC sign-in, plus Waitress for HTTP serving. The current launcher
supports macOS and Linux (the single-server lock uses `fcntl`).

## Start

From this project checkout, using the project's verified interpreter:

```sh
/usr/local/bin/python3 -m src.local_web.server
```

Open <http://127.0.0.1:8765>. Keep the process running and the computer awake.
Closing the browser does not cancel a study. Ctrl-C stops the service and
interrupts an active run. Restarting preserves history; interrupted runs are
marked failed, and queued studies continue. Use **Load these settings** and
**Run simulation** to retry a failed study as a new run.

Optional arguments:

```sh
/usr/local/bin/python3 -m src.local_web.server --port 8766
/usr/local/bin/python3 -m src.local_web.server --data-dir /absolute/path/to/studies
```

The service only binds to `127.0.0.1`. It checks Host and Origin and requires
a per-server request token for writes. This is a local development service,
not a publicly hosted or multiuser deployment.

## First study

New studies use a location, an explicit load model, and weather-derived PV.
The default is a San Francisco clear-sky study on August 1, 2026 at 15-minute
resolution. It assumes 20 °C air temperature, 1 m/s wind, 60 kW constant load,
60 kW DC PV / 50 kW AC, $0.25/kWh energy, and 300 gCO₂/kWh grid carbon.
These are editable assumptions, not measured site data.

1. Enter a city/address and click **Find location**, or enter coordinates directly.
   The existing GUI geocoder supplies coordinates. Search contacts OpenStreetMap
   Nominatim only on explicit action; results are cached and requests serialized
   at less than one per second. Confirm the displayed match and timezone.
2. Confirm electricity service. The San Francisco locality hint suggests PG&E
   as a candidate; it is not an authoritative territory or account lookup.
   CleanPowerSF/other CCA and municipal service can differ. Bundled PG&E tariffs
   require explicit account confirmation. Other utilities currently use assumed
   flat energy prices, not an invented utility bill.
3. Choose **Clear-sky estimate** for locally calculated cloud-free irradiance
   and explicit constant temperature/wind assumptions. This is neither observed
   weather nor a forecast.
4. Alternatively choose **Historical weather · NSRDB**, set dates within one
   year (2018–2025, CONUS coverage), then click **Retrieve historical weather**.
   The app uses the existing NSRDB adapter and current provider endpoint,
   retrieves the year at the selected resolution, and caches it locally.
   Matching location/year/timezone/interval and complete interval coverage are
   required. No year shifting, resampling, or silent clear-sky fallback occurs.
5. Set constant or synthetic building load, PV nameplate/orientation/losses,
   battery/inverter settings, prices and strategies; click **Run simulation**.

Historical retrieval uses the existing local NSRDB credentials. They stay on
this computer; only the requested site/weather parameters and credentials go
to NSRDB. The browser, result manifests, snapshots and error logs receive no
credential values. Start with an existing environment file if needed:

```sh
/usr/local/bin/python3 -m src.local_web.server --refresh-engine --env-file /absolute/path/to/src/.env
```

Only `NSRDB_API_KEY` and `NSRDB_API_EMAIL` are read from that file. Existing
process environment values take precedence. The default path is this checkout's
`src/.env`; credential files are not copied into engine snapshots. Retrieving
weather requires internet; clear-sky studies and cached weather run offline.

New results include scenario comparison, cost summary, normalized simulation
inputs, weather (GHI/DNI/DHI, temperature, wind), PV model diagnostics, and
per-scenario dispatch. Each saved table has full CSV export. OpenDSS replay
contributes compact feasibility counts and extrema to scenario comparison;
the result manifest stores up to five failure timestamps and reasons per
scenario, rather than full interval-by-interval AC tables. New tables are stored
once as CSV with small column metadata; the server builds browser pages from
that CSV and offers an on-demand ZIP of all result tables. Previously saved
studies still expose their existing AC/JSON tables. The manifest also records model
assumptions and provenance.
**Completed means the calculation finished, not that every interval is
electrically feasible.** Inspect the comparison's feasibility counts and any
failure warnings.

A selected tariff supplies both dispatch energy prices and billing; its
version must cover the study dates. In particular, a 2026 tariff cannot be
applied to 2025 historical weather. Use an explicit flat price if no historical
tariff version exists. Billing uses one PCC meter and an unknown previous
billing-period peak. Grid carbon remains an explicit constant assumption.
The representative balanced network remains; PV is a generic pvlib model,
with grid-following AC replay at Q=0 and kVA assumed equal to AC kW.

Existing version 1 sample/CSV studies remain readable and reusable with their
original inputs. **New location study** switches back to the new workflow.
No profile-upload section has been reintroduced.

## Input contract

`src/local_web/contract.py` defines version 1 (legacy CSV) and version 2 (location) JSON requests, independent of
HTTP and Tkinter. The legacy version 1 fields are:

| Field | Meaning |
|---|---|
| `schema_version` | Integer 1 for legacy CSV; unknown versions/fields are rejected |
| `name`, `dataset_id` | Study name and SHA-256 of the uploaded CSV bytes |
| `start_date`, `end_date` | Local dates, both inclusive |
| `timezone`, `timestep_minutes` | IANA timezone and 5/15/30/60 minute interval |
| `strategies` | Selected engine strategies, including `no_battery` |
| `carbon_weight` | One carbon weight, dollars per kg CO₂ |
| `degradation_cost_per_kWh` | Battery degradation price |
| `tariff_id` | Supported commercial tariff, or null for CSV prices |
| `pv_capacity_kw` | Aggregate AC rating for this CSV replay |
| `battery` | Capacity, initial energy, charge/discharge power, SOC bounds, efficiencies |

Version 2 replaces `dataset_id` with `site` (label, coordinates, utility account
selection), `weather_source` (`clear_sky` or `nsrdb`), optional `weather_id`,
`solar` (DC capacity, tilt, azimuth, losses, inverter efficiency and clear-sky
temperature/wind assumptions), `load` (mode, power/peak and archetype),
`fixed_price_per_kWh`, and `carbon_intensity_g_per_kWh`. Common horizon,
battery, strategies and AC capacity fields retain their meanings. The full
validated defaults are returned in capabilities as `site_defaults`.

For programmatic dataset uploads through the API, use a UTF-8 CSV with `timestamp`, `load_kw`, `pv_kw`, `price_per_kWh`,
and `gCO2/kWh`. The canonical alternatives `native_load_kw`,
`pv_available_kw`, and `carbon_intensity_g_per_kWh` are accepted. If both
aliases are present they must agree. Timestamps must include UTC offsets.
The service checks finite values, ordered unique instants, and evenly spaced
rows. The worker verifies exact coverage of the requested horizon and
resolution before calling the engine. It does not fill or resample data.

Dates become a half-open horizon by advancing the inclusive end by one
calendar day in the selected timezone. Interval counts come from that grid;
they are never computed as days times 96. Inputs are serialized in UTC before
passing them to the existing CSV adapter, preserving repeated autumn hours.

The request type is available for a future Tkinter adapter, but this change
does not alter the current Tkinter implementation or backend ownership.
The result manifest records the request schema version. Table responses contain
`columns`, `labels`, `data`, `total`, and `offset`; numbers retain precision
and unavailable diagnostics serialize as null. Browser rounding is display-only.

## Execution and persistence

1. The API saves the validated request and a historical weather or CSV copy when applicable, then queues the study.
2. A single dispatcher atomically claims a queued study in SQLite.
3. A fresh Python subprocess runs the saved engine snapshot. OpenDSS state
   is never shared between study processes or request-handling threads.
4. The worker reports progress and writes output files atomically, then the
   dispatcher records completion or failure.
5. The browser polls status and retrieves tables in pages of 100 rows;
   CSV downloads contain the whole table.

The default study directory is `.cache/local_web/`, already covered by the
repository's ignore rules:

```text
studies.sqlite3          study identity, status, engine ID, errors, timestamps
engine.json             current development engine pin
engines/<hash>/          copied Python source and manifest
datasets/<hash>.csv      uploaded or bundled input bytes
datasets/<hash>.json     dataset metadata
weather/<hash>/         cached canonical weather, checksum and provenance
locations/<hash>/       cached location search results
runs/<id>/              request, input copy, progress, logs, engine manifest,
                        normalized CSV, result tables, and result manifest
```

Although this directory is under `.cache`, it holds persistent study history:
do not clear it if you need those studies. Use `--data-dir` for a dedicated
storage location and back up that complete directory while the server is stopped.

Local limits: 20 MB HTTP bodies, 16 MiB per CSV upload by default,
110,000 CSV intervals, 1–366 calendar days per study, one active worker,
and 30 minutes per run. The default CSV store cap is 1 GiB. Saved study results
and retrieved weather have separate provisional storage limits; see
[Web resource controls](Web_Resource_Controls.md) for their values and scope.
There is no automatic data deletion. The database contains job metadata;
large interval tables remain files. New CSV-only results are paged from the
CSV without loading a full JSON copy; legacy JSON pages still read the whole
file before slicing. This is intended for local studies, not large-scale
analytics.

## Engine snapshots and upgrades

The first launch saves a copy of the Python source and records SHA-256 hashes,
Python version, and numerical-engine dependency versions. Subsequent launches
reuse that pin even if the checkout changes. Before each study, the service
checks snapshot hashes and recorded dependency versions. Jobs use their saved
engine ID, including jobs queued before a restart.

This is a **local development snapshot**, not a published release, wheel,
or fully isolated dependency environment. Dependencies still come from the
selected interpreter. Version mismatches cause rejection, but this does not
prove installed package bytes are unchanged. No production release is claimed.

To explicitly adopt the current checkout after testing, stop the server and run:

```sh
/usr/local/bin/python3 -m src.local_web.server --refresh-engine
```

Old source snapshots and results remain saved. Loading an old study's settings
and submitting creates a new study under the current engine pin; it does not
rewrite old results. Schema changes must add an explicit migration or reject
the old request. Future formal engine releases should package code with a
separate locked dependency environment and a broader saved-study acceptance set.

## API

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/capabilities` | Defaults, supported tariffs/strategies, engine ID, write token |
| POST | `/api/location` | Geocode an explicit `{query}` with cached results |
| POST | `/api/weather` | Retrieve/cache `{latitude, longitude, year, timezone, timestep_minutes}` |
| GET / POST | `/api/datasets` | List datasets / upload `{name, csv}` |
| GET / POST | `/api/studies` | List the most recent 100 / submit a version 1 or 2 request |
| GET | `/api/studies/<id>` | Status, request, progress, result manifest when completed |
| GET | `/api/studies/<id>/tables/<table>?offset=0&limit=100` | Page of numeric result data |
| GET | `/api/studies/<id>/tables/<table>.csv` | Full table download |
| GET | `/api/studies/<id>/tables.zip` | On-demand ZIP of CSV result tables and manifest |
| POST | `/api/studies/<id>/save` | In guest-enabled OIDC mode, make a completed temporary study permanent; guest claims require sign-in and its original cookie |
| GET | `/api/studies/<id>/request.json` | Saved request download |
| GET | `/api/studies/<id>/result.json` | Result/provenance manifest download |

POST requests use `Content-Type: application/json` and `X-Study-Token` from
capabilities. POST study returns HTTP 202 and a study ID; simulation errors
appear on the saved job and never masquerade as successful results.

## Verification and remaining scope

```sh
/usr/local/bin/python3 -m pytest -q test/test_local_web.py
/usr/local/bin/python3 -m pytest -q
```

Web integration tests need permission to bind a loopback port. They use local
fixtures only and compare a real subprocess run (dispatch, tariff billing,
and OpenDSS) against the existing engine entry point. They also cover request
compatibility, validation, snapshot pinning/tampering, immutable inputs, atomic
job claiming, failed-job recovery, paging, downloads, same-origin checks, weather
copy integrity, historical date mismatch rejection, clear-sky day/night and DST,
PV capacity/orientation effects, tariff price consistency and credential-safe
provider errors. Provider retrieval tests use fixtures and do not consume API quota.

Next extensions: equipment-catalog forms, authoritative utility territory lookup, full itemized
billing records, additional meter topologies, carbon-weight sweeps, job
cancellation, importable study bundles, and broader upgrade comparison reports.
Hosting, PostgreSQL, authentication, and multiple workers are deferred.

## Candidate equipment and annual orientation features

See [ESS equipment catalog](ESS_Equipment_Catalog.md) for the source-backed
ESS resolver, schema 3, manual/equipment flow, and full-year historical
integer orientation optimization. These features are prepared under a separate
candidate engine. Existing pinned engines are not upgraded automatically.


## Frontend/backend pipeline and independent worker

The browser sends validated study settings to `POST /api/studies`. The API
returns HTTP 202 with the saved study ID. SQLite retains the queued job while
its immutable request, engine manifest and inputs live in the run directory.
The worker records `started_at` on claim and `runtime_seconds` on finish;
the browser shows Run time in completed study details and history. Queue waiting
is excluded from that runtime.
A single worker atomically claims jobs and invokes the pinned simulation engine
in a separate subprocess. The browser polls `GET /api/studies/{id}` and loads
`GET /api/studies/{id}/tables/{table}` or its `.csv` download when complete.
`GET /api/health` exposes worker connectivity and queued/running/cancelling counts; the
browser updates this status every five seconds. Submission while the worker
is offline remains valid until the bounded queue fills; then the API returns
HTTP 429 with a retry message. The owner can cancel a queued or running study
from the result view; a running process stops before the status becomes cancelled.
See [Web resource controls](Web_Resource_Controls.md) for the per-user daily
study and measured simulation/orientation budgets in signed-in mode.

The existing one-command launch still runs an embedded worker. For independent
processes, run these commands from the main project folder in two terminals:

```sh
/usr/local/bin/python3 -m src.local_web.server --port 8767 --data-dir .cache/local_web_pipeline --external-worker
```

```sh
/usr/local/bin/python3 -m src.local_web.runner --data-dir .cache/local_web_pipeline
```

Open <http://127.0.0.1:8767>. Both processes must use the same data directory.
This separate directory creates a new engine snapshot without changing an
existing preview's pin. Subsequent source updates still require the explicit
`--refresh-engine` option; each previously queued study retains its own engine.

In external mode, restarting the web/API server does not stop the worker or
mark its active job failed. Worker startup alone recovers interrupted running
records as failed, with saved inputs available for explicit resubmission.
Stopping the worker interrupts its active job; queued jobs remain queued.
The worker holds an exclusive lock, inherited by the simulation subprocess,
so a replacement cannot recover a job while an orphaned engine is still running.
Once that child exits, restart the worker to recover the interrupted record.
Only one worker per directory is supported. SIGINT/SIGTERM shut down the
standalone worker gracefully. Separate processes do not yet provide multi-host
execution, automatic retries, authentication or production hosting. Location,
weather and annual orientation requests still use their existing synchronous
API paths; study execution is the durable asynchronous pipeline.

Run `python -m pytest -q test/test_local_web_pipeline.py test/test_local_web.py`
to verify independent-worker execution, restart persistence, locking, failure
recovery and actual result-table retrieval without provider network calls.


## Utility territory choices

`POST /api/utilities` accepts latitude/longitude and queries the California
Energy Commission's ArcGIS polygon layers for IOU/POU and other load-serving
entities (including CCAs). The frontend retrieves choices on form initialization,
after location search, and after coordinate edits. It rejects stale lookup
responses and clears the prior account selection when coordinates change.
Successful matches are cached locally for 24 hours, with source URLs and retrieval
time. Partial/provider failures stay explicit and are not cached as complete.
Outside California, manual selection remains available; no bounding-box utility
assignment is used. The coverage bounding box only avoids unnecessary requests.

Sources: https://www.arcgis.com/home/item.html?id=30410214d637434ba1003cbdcc32cf55
and https://www.arcgis.com/home/item.html?id=07224640a2fe42f89399be796e7b8810.
CEC warns boundaries are approximate and not all entities are represented.
Multiple matches remain choices, not automatic enrollment. Selecting PG&E bundled
service still requires the user to identify that account arrangement. CCA/other
provider identifiers are retained in the saved site; their tariffs are not yet
modeled, so they use the explicit flat-price assumption. No CCA rate is inferred.
The reset button is labeled “Reset study inputs”; it does not delete saved runs.

## Multi-step setup

The form shows nine setup screens (study name, location, electricity service,
simulation time range, solar weather, PV, inverter, battery/ESS, economics)
followed by Review & run. Back/Next preserves values in the same form; visited
steps can be revisited from the step navigation. Reset and loading saved settings
start at the first applicable step. Legacy CSV studies skip location-only steps.
Native field constraints and key date/weather/battery checks run before advancing;
submission rechecks all steps and reveals the first invalid one. The review screen
summarizes settings and retains load and strategy controls. Inputs remain in memory
while navigating; they are durably saved only when a study is submitted.


### Explicit defaults

New/reset studies start with blank editable parameters and unselected configuration
choices. Each step offers **Use Default Values**, filling only empty fields on that
step. Existing entries and manually chosen comparison strategies are preserved.
The no-battery reference remains mandatory. Saved studies still restore their
stored inputs. Utility matches and calculated orientation retain their existing
lookup/calculation flows. Annual orientation requires the later PV/inverter fields
to be configured first. Required blank numbers are rejected rather than treated
as zero. Unused fields required by the legacy request schema (for example constant
weather assumptions in historical mode) retain internal placeholders only; they
are not active user assumptions in those modes. Defaults remain the current static
values; context-dependent recommendations are future work.
