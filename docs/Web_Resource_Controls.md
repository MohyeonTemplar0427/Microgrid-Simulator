# Web resource controls: workstream 3

This checkpoint limits study submissions and simultaneous interactive site
calculations for the prepared single-host API and one independent worker.
Cancellation is supported for queued and running studies. Daily signed-in
user limits now bound accepted simulation submissions per UTC day.

## Study queue

The API counts **queued, running, and cancelling** studies. The defaults are 20 studies
across the server and 3 per signed-in user. The local trusted mode has the
server-wide limit but no user ownership. Both values can be set in the API
process environment:

| Variable | Default | Allowed range |
|---|---:|---:|
| `MICROGRID_MAX_PENDING_STUDIES` | 20 | 1–1000 |
| `MICROGRID_MAX_PENDING_PER_USER` | 3 | 1–1000 and no more than the server limit |

Invalid settings fail startup. Reducing a limit does not cancel already accepted
studies; it stops new submissions until the pending count falls below the new
limit. Cancelled, failed and completed studies do not occupy queue slots.

The API checks capacity in a SQLite write transaction and saves the immutable
inputs before the queued row becomes visible to the worker. Concurrent requests
cannot both claim the last slot. This applies to the standard, municipal, and
Southern California submission routes because they all use `Store.submit`.
When full, the API returns HTTP 429 with a short retry message and
`Retry-After: 30`; it does not accept and later discard the study.

## Interactive work and execution

The worker already has an exclusive directory lease and runs one simulation at
a time. The API now allows one concurrent utility lookup, location/weather
retrieval, ESS resolution, or candidate/orientation calculation per API process.
A second interactive request receives HTTP 429. This protects Waitress's four
threads and limits API-side subprocess/provider overlap. A simulation and one
interactive operation may still run together on the host.

These controls assume the documented **single API process** and **single worker**
using one local data directory. The API semaphore is process-local; it does not
coordinate multiple API instances. Do not add another API replica without
replacing it with shared coordination.

## Cancel a study

The owner can use **Cancel study** in the browser or send an authenticated,
CSRF-protected `POST /api/studies/{id}/cancel` with an empty JSON object.
Queued studies become `cancelled` immediately and are never claimed. Running
studies become `cancelling` until the worker terminates the simulation process
group, then become `cancelled`. While a study is cancelling, it still occupies
a queue slot. Another user's study ID returns HTTP 404; unauthenticated callers
cannot reach the action. Completed, failed and already cancelled studies return
HTTP 409. Calling cancel again while stopping is safe.

A cancelled study keeps its saved settings so its owner can load them into a
new study. Partial output files may still exist privately in its run directory;
the API never serves them as completed results. Worker restart converts a
previously cancelling study to cancelled after the exclusive worker lease is
available. A plain interrupted running study is still marked failed for
explicit resubmission.

## Measured simulation runtime

The worker saves `started_at` when it claims a study and measures elapsed
wall time with a monotonic clock until it finishes. It stores that duration as
`runtime_seconds` for completed, failed, or running-then-cancelled studies.
The elapsed time includes worker validation, engine startup, and termination;
it excludes waiting in the queue. It is wall time, not CPU time or cloud cost.

The owner sees **Run time** in the study result and recent-study history. The
same fields are available from the owner-filtered study API. A queued or
queued-then-cancelled study has no runtime. Legacy and interrupted studies whose
run duration was never captured also remain null; the migration adds columns
without inventing historical measurements.

## Daily simulation limit

The initial limit for each signed-in user is **200 accepted simulations per UTC
day**. This is a provisional submission count, not a measured cloud capacity.
Set `MICROGRID_DAILY_STUDY_LIMIT` (1–1000) in the API process environment to
adjust it. Trusted local mode has no per-user daily limit because it has no
user identity.

Every accepted study submission counts, including one cancelled while queued,
to prevent repeated submit/cancel cycles. Solar-orientation calculations do not
count as simulations. Measured simulation and orientation wall time remains in
the private `GET /api/usage` response for observation, but it does not restrict
new work. No daily time-budget setting is used.

The API checks the count inside a SQLite write transaction for all study
submission routes. At the limit, new submissions receive HTTP 429;
`Retry-After` points to the next UTC midnight. Previously accepted queued or
running studies may finish. Existing 30-minute per-run deadlines, the queue
limit, and the single interactive-calculation slot still apply.

`GET /api/usage` returns only the signed-in user's count, measured seconds,
remaining simulations, UTC day and reset time. The browser displays the
submission count near the simulation-service status. An incomplete orientation
event after an API crash is conservatively measured for up to its 30-minute
deadline for that UTC day; this is telemetry only. No email address or
identity-provider token is stored in usage records.

## CSV upload storage

The first storage guard applies to datasets uploaded through the API. Defaults
are **16 MiB per CSV file**, **100 MiB of distinct saved CSV files per signed-in
user**, and **1 GiB of CSV files across the server**. Set the byte limits in
the API process environment:

| Variable | Default (bytes) | Scope |
|---|---:|---|
| `MICROGRID_MAX_UPLOAD_BYTES` | 16,777,216 | One CSV file |
| `MICROGRID_MAX_OWNER_DATASET_BYTES` | 104,857,600 | Files granted to one signed-in user |
| `MICROGRID_MAX_DATASET_STORE_BYTES` | 1,073,741,824 | Distinct CSV files stored on the server |

These are provisional values; the HTTP request body is separately capped at
20 MiB. A user uploading the same CSV again does not consume another allowance,
and identical content shared between users has one physical file. Built-in
samples count toward each user's allowance, so the configured owner and server
limits must fit both samples. Existing CSVs and older grants without recorded
sizes count by their actual file sizes. Trusted local mode has no per-user
quota but still has the per-file and server limits.

The API validates CSV content, then checks ownership and physical storage in a
SQLite write transaction before storing a new file. Concurrent uploads cannot
both take the last quota space. A rejected upload returns HTTP 429 with a clear
error and does not create a dataset grant. The owner limit for uploads currently
requires an administrator to change the limit or remove old data; self-service
dataset deletion is still pending.

## Annual result and weather storage

An offline San Francisco 2025 benchmark used **synthetic clear-sky weather** in
the same annual CSV shape as a cached weather source. It did not call NSRDB or
measure real historical values. With five strategies, removing the saved
interval-by-interval OpenDSS tables changed the run-directory sizes as follows:

| Interval | Rows | Cached weather | Original run | Without AC tables | CSV-only run |
|---|---:|---:|---:|---:|---:|
| 15 minutes | 35,040 | 2,401,262 bytes | 357,746,076 bytes | 76,611,494 bytes | 28,725,748 bytes |
| 5 minutes | 105,120 | 7,204,464 bytes | 1,071,813,796 bytes | 229,792,318 bytes | 86,136,739 bytes |

The new result manifest retains compact AC feasibility counts and up to five
failure timestamps/reasons per scenario. New runs save CSV result tables with
small type/label metadata, and serve browser JSON pages on demand. Previously
completed studies retain their existing JSON and AC files. Run sizes still
include a copy of the weather CSV, input tables, and dispatch tables. Together,
these changes saved about 92% of the measured run-directory space. Reading a
100-row page near the end of the 15-minute CSV took 0.023 seconds on this Mac;
the 5-minute case took 0.068 seconds. Reproduce the current local
measurements without provider credentials using
`/usr/local/bin/python3 tools/benchmark_web_storage.py --interval-minutes 15`
or `--interval-minutes 5`. These are storage measurements on a Mac, not a cloud
capacity or annual historical-weather accuracy benchmark.

Based on those sizes, the provisional limits are:

| Variable | Default | Scope |
|---|---:|---|
| `MICROGRID_MAX_RUN_BYTES` | 2 GiB | One study directory, including copied inputs |
| `MICROGRID_MAX_OWNER_RUN_BYTES` | 8 GiB | One user's stored studies and queued reservations |
| `MICROGRID_MAX_RUN_STORE_BYTES` | 32 GiB | All stored studies and queued reservations |
| `MICROGRID_MAX_WEATHER_BYTES` | 64 MiB | One cached weather resource |
| `MICROGRID_MAX_OWNER_WEATHER_BYTES` | 256 MiB | One user's cached weather |
| `MICROGRID_MAX_WEATHER_STORE_BYTES` | 2 GiB | All cached weather, including ownerless data |
| `MICROGRID_MIN_FREE_BYTES` | 2 GiB | Free-disk reserve after new work is reserved |

Set these in both API and independent-worker environments; values must be
positive integers in bytes, with per-owner and server caps no smaller than the
per-resource cap. The API reserves a whole 2 GiB study allowance when accepting
each job, including queued jobs, inside the same SQLite transaction as queue
admission. Finished studies count their actual directory sizes. Ownerless and
orphaned run directories count against the server cap. It also checks available
disk space after outstanding job reservations.

The worker checks its study directory every 0.2 seconds and stops a study that
exceeds its 2 GiB allowance or reaches the free-space reserve. It discards
partial generated outputs and preserves immutable inputs and the failed study
record. Because monitoring is periodic, a fast write can briefly exceed the
limit; a production host still needs adequate filesystem capacity and
monitoring. Cached weather is checked before retrieval and after saving; an
oversize or failed retrieval is removed without granting access. A provider can
briefly write more than the weather limit before the post-retrieval check. The
one-API-process interactive slot serializes weather retrievals.

The 200-per-day study count is an upper bound on submissions, not a promise of
200 full-year studies being stored. At the 8 GiB owner cap, repeated annual
5-minute saved studies can reach the storage limit first. A user can delete a
finished study and its result files to reclaim run storage; an active study
must first be cancelled and stopped.
In optional guest mode, guest sessions have a two-study daily limit and the
server has a 20-study global guest daily limit. New studies by signed-in users
are also temporary in that mode until explicitly saved. Unsaved results expire
24 hours after completion by default, so they do not consume retained storage
indefinitely; all temporary files still count against storage quotas until then.
Queued temporary jobs are also removed after 24 hours if they never run.
These limits are provisional and must be reviewed against the selected host and
actual workload. Candidate data, utility caches, engine snapshots, the SQLite
database, and backups are not covered by these category caps; backups,
dataset/weather deletion, and host-level disk controls remain deployment blockers.

## Deleting a finished study

The selected study's **Delete study and results** button sends an owner-checked,
CSRF-protected request to `POST /api/studies/<id>/delete` with `{}`. It removes
the study from history and blocks further downloads through all study routes.
Queued, running, and cancelling studies must finish or be cancelled first.
The server then removes the run directory, including copied inputs and result
CSVs. If the filesystem is temporarily busy, the API reports cleanup pending
and the janitor retries. Separate uploaded datasets and cached weather remain
available to their owners; this action does not delete those resources.

For two days the database retains only a minimal quota record: opaque owner ID,
timestamps, duration and a scrubbed study name. This prevents deleting a study
from resetting the daily simulation limit. The janitor then removes that record.
Deletion does not reach any independently retained administrator backup;
backup retention and restore policy still need to be defined before hosting.

## Verification

Run:

```sh
/usr/local/bin/python3 -m pytest -q test/test_local_web_storage.py test/test_local_web_usage.py test/test_local_web_cancellation.py test/test_local_web_limits.py test/test_local_web_auth.py test/test_local_web_pipeline.py
```

The tests exercise concurrent SQLite reservations, per-user and global limits,
HTTP 429 responses, interactive overlap, cancellation ownership and real
subprocess termination, an independent worker, daily UTC reset, concurrent
submissions, and simulation/orientation runtime reporting. No provider
account or live network data is needed.

## Current verification checkpoint

- After queue limits: focused resource, authentication and independent-worker
  tests **31 passed**; full non-GUI suite **1,234 passed, 1 skipped**; real
  Caddy suite **17 passed**.
- After cancellation and final queue accounting: full non-GUI suite
  **1,239 passed, 1 skipped**; real local HTTPS/Caddy suite **17 passed**.
  The skipped test requires an explicit Caddy binary and passed in the
  separate run. Two NumPy runtime warnings occurred in municipal dispatch
  tests; those tests passed.
- With persisted runtime reporting: full non-GUI suite **1,239 passed,
  1 skipped** (two NumPy warnings in passing municipal dispatch tests);
  real local HTTPS/Caddy suite **17 passed**. A temporary one-day, 15-minute
  sample with five strategies completed and stored **2.082 seconds** of worker
  wall time on this computer.
- With daily usage budgets: full non-GUI suite **1,250 passed, 1 skipped**;
  local HTTPS/Caddy suite **17 passed**. The optional Caddy test skipped in the
  broad run passed when run with the verified binary. The final added tests
  for local mode, cancelled runtime, and failed orientation usage passed
  separately: **12 passed**.
- With the 200-submission daily limit and no daily time cutoff: resource and
  authentication checks **48 passed**; full non-GUI suite **1,323 passed,
  1 skipped**. The skipped optional Caddy check was previously run separately.
- With CSV upload quotas: full non-GUI suite **1,334 passed, 1 skipped**.
  After the final built-in-sample startup checks, focused storage,
  authentication, usage, and queue checks **56 passed**.
- With annual result/weather limits: offline annual benchmark measured
  **357,746,076 bytes** for five strategies at 15-minute intervals and
  **1,071,813,796 bytes** at 5-minute intervals. Full non-GUI suite
  **1,347 passed, 1 skipped** after the initial quota implementation; after
  the final CSV free-space reservation check, focused storage/authentication
  checks **53 passed**.
- After removing full OpenDSS result tables: the same offline annual benchmark
  saved **76,611,494 bytes** at 15-minute intervals and **229,792,318 bytes**
  at 5-minute intervals. Browser integration tests **39 passed**; full non-GUI
  regression suite **1,349 passed, 1 skipped**.
- With CSV-only result tables: the same offline benchmark saved **28,725,748
  bytes** at 15-minute intervals and **86,136,739 bytes** at 5-minute
  intervals. A late 100-row dispatch page took **0.023 s** and **0.068 s**
  respectively on this Mac. With guest/session limits, temporary expiry,
  on-demand ZIP downloads, and explicit profile saves, the final non-GUI suite
  **1,351 passed, 1 skipped**. Two NumPy warnings came from passing municipal
  dispatch tests. Authentication tests use fake OIDC identities.
- `git diff --check`, Python and JavaScript syntax checks passed.

No public server or provider account was used. This checkpoint does not validate
an Oracle ARM host or establish safe capacity for a particular number of users.
