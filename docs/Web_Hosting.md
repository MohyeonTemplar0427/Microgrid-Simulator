# Production transport preparation: workstream 2

This change replaces the standard-library development HTTP server with
**Waitress 3.0.2**, while retaining the existing API routes, frontend, ownership
checks, SQLite store, and process-isolated simulation engine. It prepares a
**single-host Caddy → Waitress → independent worker** arrangement. It neither
creates cloud resources nor publishes this application.

```
Browser ── HTTPS ── Caddy ── localhost HTTP ── Waitress / API
                                               │
                                     private SQLite + files
                                               │
                                     independent job runner
                                               │
                                      simulation subprocess
```

Caddy terminates TLS: it receives encrypted browser traffic and forwards requests
to the private Python server on the same computer. Waitress serves the browser
assets and API. The worker reads the durable queue and writes result tables, so
an API restart need not interrupt a simulation. Both processes require the same
local data directory. This is not a multi-host or multiple-API-instance design.

No hosting provider is required to prepare this arrangement locally. Oracle Free
Tier remains a candidate, not a selected or verified environment. Its capacity,
processor compatibility, memory needs, and operational policies still need review.
No commercial service, domain, or identity-provider account was created.

## Local development still works

From `~/Desktop/EnergyEngineerSession/Microgrid_Web_Browser`:

```sh
/usr/local/bin/python3 -m pip install -r requirements.txt
/usr/local/bin/python3 -m src.local_web.server --port 8765
```

This now uses Waitress, on 127.0.0.1 only. Its default embedded worker and local
mode remain convenient for a trusted local directory. OIDC rehearsal with a
loopback callback still works as described in [Web access control](Web_Access_Control.md).
Do not silently switch an OIDC data directory back to local mode: that fails.

## Hosted settings (prepare now; enable only in a reviewed environment)

`deploy/hosting.env.example` lists the variable names, without real credentials.
It is a reference, not a working credential file. Supply actual values through
private process configuration. The CLI's `--env-file` continues to read only
weather/carbon credentials, not hosting/OIDC configuration.

| Setting | Requirement |
|---|---|
| `MICROGRID_PUBLIC_ORIGIN` | Exact `https://YOUR_DOMAIN`, optional explicit port; no trailing slash or path |
| `MICROGRID_AUTH_MODE` | `oidc`; optional guest sessions still require configured OIDC for profile saving |
| `MICROGRID_OIDC_ISSUER` | Exact HTTPS issuer provided by the identity service |
| `MICROGRID_OIDC_CLIENT_ID` | Registered confidential web client |
| `MICROGRID_OIDC_CLIENT_SECRET` | Server-only secret |
| `MICROGRID_OIDC_REDIRECT_URI` | Exactly `MICROGRID_PUBLIC_ORIGIN` plus `/auth/callback` |
| `MICROGRID_SITE_ADDRESS` | Same HTTPS address, supplied to Caddy |

Startup refuses incomplete configuration, non-HTTPS public origins, callback
mismatches, or hosted settings without the explicit `--hosted` switch. This switch
**does not** bind the API to a public interface. It forces a separate worker and
requires requests to arrive with the exact configured Host and HTTPS scheme.

Once private configuration and a suitable data directory have been prepared, the
process commands are:

```sh
# API process; backend remains 127.0.0.1:8765
/usr/local/bin/python3 -m src.local_web.server --hosted --port 8765 --data-dir /ABSOLUTE/PRIVATE/STUDY_DIRECTORY

# Independent worker process on the same host
/usr/local/bin/python3 -m src.local_web.runner --data-dir /ABSOLUTE/PRIVATE/STUDY_DIRECTORY
```

Set weather/carbon keys in the processes that use them: weather retrieval occurs
through the API, and historical carbon may be fetched by the simulation worker.
Do not give the independent worker OIDC secrets. Engine subprocesses also remove
OIDC and MySQL credentials from their inherited environment.

A new data directory pins current source automatically. For an existing directory,
use `--refresh-engine` explicitly only after validation to adopt new engine code;
previous queued jobs keep their saved snapshots. Do not automatically refresh
on every restart. Preserve the ownerless-data quarantine from workstream 1.

To allow temporary guest studies, add `--allow-guests` to the API command. This
is an explicit opt-in; without it, the existing sign-in-before-use policy stays
in force. Guest access uses a private, HttpOnly cookie and a separate temporary
owner. In this mode, **both guest and signed-in new studies are temporary**.
A completed unsaved result expires 24 hours after completion by default;
queued temporary studies also expire after 24 hours if no worker starts them.
The API removes expired run directories in the background and on startup. Guests
may submit two studies per UTC day, and the server accepts at most 20 guest
submissions total per UTC day by default. At most 100 new guest sessions are
created globally per UTC day. Guest setup lookups have separate
limits of 20 per guest and 100 globally per UTC day. These are configurable through the
`MICROGRID_GUEST_*` and `MICROGRID_TEMP_RESULT_HOURS` settings in the example
environment file. Sign-in through the configured OIDC provider is required to
save a guest result to a profile; signed-in users can save their own temporary
results directly.
The browser keeps the pending study ID through that redirect, and the server
requires both the signed-in session and original guest cookie to transfer it.
Downloads create a ZIP from the saved CSV tables only on request; the temporary
ZIP is removed after transfer. The API permits one ZIP transfer at a time and
returns a retry message to concurrent requests. Downloading does not extend the
result's expiry.
The guest cookie itself lasts 48 hours; guest-only uploads and caches are removed
after that session expires and no studies remain for it. Existing saved studies
remain saved. No live provider or public guest capacity has been validated yet.

## HTTPS proxy boundary

`deploy/Caddyfile` is a validated **template**, not an installed service. It
proxies to 127.0.0.1:8765. For a chosen domain, Caddy can provision/renew certificates
and redirect HTTP to HTTPS. Real issuance requires working DNS, network access,
and an eligible domain. Those have not been configured or tested here.

Waitress trusts **only `X-Forwarded-Proto` from 127.0.0.1**, with one proxy hop.
Caddy explicitly sets that value from the actual incoming connection. Other
forwarding headers cannot supply Host or user identity. The API checks the real
Host against its configured origin and checks Origin on browser writes. Forwarded
identity headers remain unused; OIDC sessions are still required for private APIs.
Local mode does not trust forwarded scheme headers.

This topology trusts processes on the server itself. Keep port 8765 private;
only Caddy should accept external traffic. It intentionally does not support
remote proxies, containers on different networks, or a second forwarding hop.
Do not add wildcard proxy trust or change the bind address to make another
topology work without revisiting the boundary and its tests.

HTTPS sessions and login-state cookies use `__Host-` names, `Secure`, `HttpOnly`,
`SameSite=Lax`, `Path=/`, and no Domain attribute. Local HTTP cookies have separate
names. A move from local HTTP to HTTPS requires a fresh sign-in. HSTS is emitted
for hosted responses, without enabling preload or applying it to all subdomains.

Caddy access logging is disabled. Its operational-log filter removes the request
object and response headers, including callback query codes and cookies. Waitress
is configured not to expose tracebacks; unexpected application exceptions produce
a generic JSON error instead of logging provider details. Richer operational
logging must preserve these privacy rules.

## Local verification

Ordinary tests require localhost socket permission, not cloud accounts:

```sh
/usr/local/bin/python3 -m pytest -q test/test_local_web_hosting.py test/test_local_web_auth.py test/test_local_web_pipeline.py test/test_local_web.py
```

The real Caddy integration test is optional when its binary is unavailable. To
include it, set `MICROGRID_TEST_CADDY` to a verified official executable and run:

```sh
MICROGRID_TEST_CADDY=/ABSOLUTE/PATH/TO/caddy /usr/local/bin/python3 -m pytest -q test/test_local_web_hosting.py
```

The test generates a short-lived localhost certificate, verifies that certificate
with the HTTP client, and runs Caddy and Waitress on loopback. It does not disable
TLS verification, install a trusted CA, register accounts, contact the identity
provider, or request public certificates. A fake provider supplies test identities;
sign-in, real independent-worker execution, downloads and logout use actual HTTPS.
It also checks malicious forwarding headers and callback secrecy in proxy errors.

## Remaining checkpoints

This is **production-server preparation, not a production-readiness claim**.
Live identity-provider interoperability, a real domain/certificate, and the chosen
Linux host still require verification. The existing synchronous provider and
orientation endpoints can occupy Waitress threads. The first resource-control
checkpoint now bounds queued/running studies and concurrent interactive lookups
and supports cancellation; see [Web resource controls](Web_Resource_Controls.md).
Daily study counts, CSV upload quotas, and provisional result/weather storage
limits are now prepared. Controls for long interactive requests remain pending
in workstream 3.
Waitress's parser limits and fixed thread count do not replace those controls.

Backups, restore testing, retention/deletion and storage deployment policy remain
workstream 4; reproducible packaging, service supervision and full server-environment
validation remain workstream 5. No automatic deployment, container infrastructure,
or public firewall changes are included here. Billing rates, date coverage, and
solar-model limitations remain unchanged.

Sources: [Waitress proxy settings](https://docs.pylonsproject.org/projects/waitress/en/latest/reverse-proxy.html),
[Caddy reverse proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy),
[Caddy HTTPS](https://caddyserver.com/docs/automatic-https),
[Caddy log filtering](https://caddyserver.com/docs/caddyfile/directives/log).

## Workstream 2 verification checkpoint

Verified in the Desktop browser clone on `web-browser`:

- Full non-GUI regression suite: **1,228 passed** with the real Caddy test enabled.
- Final focused hosting suite: **17 passed**, including the actual HTTPS
  sign-in → queued study → independent worker → CSV download → logout flow.
- Desktop-interface logic: **73 passed; 4 native-window checks deselected**.
  Those previously aborting native-window checks remain unverified.
- Browser smoke test: form initialization and navigation under Waitress passed,
  with no browser console errors or warnings.
- Python/JavaScript syntax and diff checks passed.
- Official Caddy **2.11.4**, verified against the release's SHA-512 checksum, was
  used from a temporary directory. The template was parsed and exercised locally;
  no system service or certificate trust was installed. Test servers were stopped.

Live identity-provider sign-in, public certificate issuance, Linux-host execution,
and public deployment remain unverified. No commit, push, or deployment occurred.
