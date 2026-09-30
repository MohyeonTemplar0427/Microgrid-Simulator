# Provider-neutral website deployment package

Status: prepared locally, **not publicly deployed**. This package targets one
Linux host with Caddy, the loopback-only Waitress API, a separate simulation
worker, private SQLite/files, and an OpenID Connect (OIDC) provider. It does not
choose a cloud vendor, domain, or sign-in provider. See [hosting security](Web_Hosting.md)
and [privacy](Web_Access_Control.md) before any public launch.

The initial free-tier pilot candidate and owner-controlled domain instructions
are in [Oracle_Free_Pilot.md](Oracle_Free_Pilot.md). They do not change this
provider-neutral package or authorize a public deployment.

## What must be supplied

- A Linux host with persistent storage, enough RAM/CPU for the measured workload,
  Python 3.13 and the repository's native numerical/OpenDSS dependencies.
- A domain name pointing to that host. Only Caddy's ports 80/443 are public;
  Waitress stays on `127.0.0.1:8765`.
- A confidential OIDC web client supporting discovery, PKCE S256 and
  `client_secret_basic`. Register exactly `https://YOUR_DOMAIN/auth/callback`.
- Private `/etc/microgrid/api.env` and `/etc/microgrid/worker.env` files. The
  worker file must not contain OIDC secrets. Caddy uses a separate
  `/etc/microgrid/caddy.env` with the site address only.
- A reviewed, committed source revision and a dependency environment built and
  tested on the selected host architecture. Do not deploy an uncommitted working
  directory or silently adopt later engine source on restart.

The templates are in `deploy/systemd/`; the existing `deploy/Caddyfile` remains
the HTTPS reverse-proxy template. Replace every example hostname and credential
placeholder before starting a service. The tracked examples are never credential
stores. Keep the code and virtual environment under `/opt/microgrid`, the study
store under `/var/lib/microgrid/studies`, and backups under a separate private
`/var/backups/microgrid` directory. The service account needs write access only
to `/var/lib/microgrid`.

## Initial host preparation

These commands are a deployment checklist for a chosen Linux host, **not commands
run by this repository change**. Adjust package installation for that host.

1. Create a dedicated `microgrid` system account, `/var/lib/microgrid` owned by
   it with mode `0700`, and `/var/backups/microgrid` owned by root with mode
   `0700`. The backup directory must not be inside the study directory.
2. Install the reviewed source into `/opt/microgrid/current` and a dedicated
   Python environment at `/opt/microgrid/venv`. Install `requirements.txt` with
   the environment's Python. Validate native OpenDSS and optimizer imports on
   the actual host; a Mac test does not establish Linux/Arm compatibility.
3. Create `/etc/microgrid/api.env`, `worker.env`, and `caddy.env` from their
   respective examples. Keep API/worker files readable only by root and the
   `microgrid` group (for example, mode `0640`). Keep values out of Git and
   shell history. `MICROGRID_PUBLIC_ORIGIN`, `MICROGRID_SITE_ADDRESS`, and the
   OIDC callback must agree exactly. Do not use the repository's development
   `src/.env` on the host.
4. Before a first start, run the following from `/opt/microgrid/current` with
   the API environment loaded privately, and only while the API and worker are
   stopped:

   ```sh
   /opt/microgrid/venv/bin/python -m tools.prepare_web_release --hosted \
     --env-file /etc/microgrid/api.env --data-dir /var/lib/microgrid/studies
   ```

   This checks hosted configuration, the single-worker lease, and the pinned
   engine's capabilities. On later reviewed releases, back up the store and
   drain queued/running studies before using `--refresh-engine`. Do not refresh
   automatically in the service unit: saved jobs carry an engine snapshot and
   must not silently change implementation.
5. Install `deploy/systemd/microgrid-api.service` and
   `microgrid-worker.service` in `/etc/systemd/system/`. Install the Caddyfile
   at `/etc/caddy/Caddyfile` and the Caddy environment drop-in at
   `/etc/systemd/system/caddy.service.d/microgrid.conf`. Check that the packaged
   Caddy service actually reads `/etc/caddy/Caddyfile`; validate its syntax.
6. After DNS, certificates, OIDC callback, firewall rules, and the host checks
   below are ready, start the independent worker, API, and Caddy services.
   Verify sign-in, a private study, result download, logout, and cross-user
   rejection over real HTTPS before allowing other users. Start without
   `--allow-guests`; enabling guest studies is a separate capacity decision.

The existing systemd examples intentionally do not start or alter the system.
They use a fixed single-host layout; review paths and service hardening against
the selected distribution and native solver libraries before installation.

## Offline backups and seven-day retention

The study store contains private requests, uploads, weather, results, sessions,
and engine snapshots. `tools.web_storage` copies the whole store, uses SQLite's
backup API, verifies SHA-256 checksums and database integrity, and restores only
into a **new, absent directory**. Backup creation acquires the API and worker
advisory locks. It fails if either service is running, so files and SQLite are
captured from the same quiet state. A separate backup directory is private by
default. Checksums detect accidental corruption, not malicious replacement of a
backup and its manifest; protect backup access separately.

For a planned maintenance window, first prevent new submissions and let active
runs finish. Stopping the worker during a run interrupts it and marks that study
failed. Then stop the API and worker, create and verify a dated backup, and
restart the services. Example commands from `/opt/microgrid/current`:

```sh
sudo systemctl stop microgrid-api microgrid-worker
sudo /opt/microgrid/venv/bin/python -m tools.web_storage backup \
  --data-dir /var/lib/microgrid/studies \
  --output /var/backups/microgrid/microgrid-$(date -u +%Y%m%dT%H%M%SZ)
sudo systemctl start microgrid-worker microgrid-api
sudo /opt/microgrid/venv/bin/python -m tools.web_storage prune \
  --backup-root /var/backups/microgrid --keep-days 7
```

The `prune` command deletes only managed `microgrid-*` backup directories whose
manifest says they are at least seven days old. Run it daily, including when a
backup attempt fails; otherwise deleted study data could remain in old backups
longer than the selected seven-day window. No timer is installed yet because
stopping an active worker needs an operator-approved maintenance window. A
future scheduler must preserve this behavior and report backup failures.

Before depending on a backup, test recovery into a separate absent directory:

```sh
sudo /opt/microgrid/venv/bin/python -m tools.web_storage verify \
  --backup /var/backups/microgrid/MANAGED_BACKUP_NAME
sudo /opt/microgrid/venv/bin/python -m tools.web_storage restore \
  --backup /var/backups/microgrid/MANAGED_BACKUP_NAME \
  --data-dir /var/lib/microgrid/restore-check
```

Do not point a running API/worker at `restore-check`. Do not overwrite a live
store. A real recovery requires stopping services, preserving the damaged store
for inspection, choosing a restored path, and updating both service units to
use that same path before restart. If root performs the restore, change the
restored directory's ownership to `microgrid:microgrid` before either service
uses it. A restored backup can reintroduce a study
that was deleted after the snapshot; the seven-day retention limits that window
but does not erase independent copies before expiry. Uploaded datasets and
cached weather still lack self-service deletion. Decide their retention policy
before public launch.

Seven full backups may require many times the live study storage. The example
quota ceiling of 32 GiB for run files alone could exceed a small host's disk
once daily backups and the 2 GiB free-space reserve are included. Set quotas
only after measuring the selected host's capacity and real full-year results.
Backups must also be copied to a separately protected location if host loss is
within the required disaster-recovery scope; that location must enforce the
same seven-day deletion policy.

## Host acceptance checks before launch

- Confirm the Linux architecture can install all pinned direct dependencies and
  run an OpenDSS and optimizer study. Transitive packages are not yet locked by
  hash; capture a host-specific lock/manifest before claiming reproducibility.
- Confirm API and worker use the same data directory and compatible Python,
  dependencies and engine snapshot. Check service restart after a host reboot.
- Validate Caddy's actual TLS certificate and OIDC sign-in/callback with the
  chosen provider; test two accounts for study isolation and downloads.
- Measure a representative full-year study against CPU, memory, disk, time and
  concurrency limits. Review the 200-per-day count against available capacity.
- Perform a backup and separate restore check, then verify the seven-day pruning
  procedure and private file permissions.
- Verify only ports 80/443 are externally reachable, API port 8765 is loopback,
  and no credentials appear in responses, exports, access logs or service logs.

The Oracle pilot now has a VM, domain, DNS record, and Auth0 account. Application
source deployment, backup scheduling, host acceptance, and public launch remain
pending. The API, worker, and Caddy services are stopped.
