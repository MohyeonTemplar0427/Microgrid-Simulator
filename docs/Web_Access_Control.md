# Web privacy and sign-in: workstream 1

**Optional guest-flow update:** With the explicit `--allow-guests` API switch,
new visitors receive a private, cookie-bound temporary owner and can run studies
before signing in. New signed-in studies are also temporary in this mode. Unsaved
completed results expire after the configured retention window. Saving a guest
study to a profile requires OIDC sign-in plus the original
guest cookie; knowing a study ID does not transfer ownership. The signed-in-only
mode described below remains the default. No provider is configured or deployed.

**Transport update:** workstream 2 replaces the development HTTP server with
Waitress and adds explicit HTTPS-proxy configuration. See
[Web hosting preparation](Web_Hosting.md). The workstream 1 checkpoint below
records the earlier loopback-only setup; hosted mode now permits exact HTTPS
callbacks and uses Secure cookies with `__Host-` names. Privacy and legacy-data
quarantine remain in effect. No live deployment or provider is configured.

This checkpoint implements application authentication and per-user authorization.
It does **not** make the server suitable for public exposure. The standard-library
HTTP server still accepts only localhost Host/Origin and binds to 127.0.0.1.
No production hosting provider, reverse proxy, container, or deployment configuration
existed in this clone at this checkpoint. Production transport is workstream 2.

## How it works

Choose an OpenID Connect (OIDC) identity provider later. Users click **Sign in**,
authenticate with that provider, and return to their private study workspace.
The application does not handle passwords. **Sign out** invalidates the server
session and clears the page. A different browser account cannot retrieve someone
else's study by copying its URL or changing an ID in an API request.

The implementation uses Authlib's authorization-code client with PKCE S256 and
OIDC claims validation; joserfc checks ID-token signatures. Only RS256/ES256 signed
tokens from the configured issuer, for this client, with a matching nonce and
valid lifetime are accepted. Discovery/key/token requests use verified HTTPS,
15-second timeouts, and no redirects. Provider error details are never returned.
The provider must support discovery, PKCE S256, and client_secret_basic client
authentication. This intentionally bounded integration needs verification with
the eventual provider; it does not claim compatibility with every OIDC service.

A random, HttpOnly, SameSite=Lax cookie identifies a server-side SQLite session.
Only its SHA-256 hash is stored. Sessions have a 30-minute idle limit and an
8-hour absolute limit, survive server restarts, rotate on sign-in, and are revoked
on logout. Authorization flows have a 10-minute lifetime, browser-bound state,
once, and a PKCE verifier; callbacks are single-use. ID/access tokens are discarded
after validation, and never stored in browser storage or returned to the frontend.
An independent per-session CSRF token protects every write, including logout.
It is not authentication. Forwarded identity headers are not trusted.

The cookie intentionally lacks Secure **only in this loopback HTTP development
configuration**. Public callback URLs are rejected. Workstream 2 must configure
HTTPS, Secure/__Host- cookies, canonical public origins, and proxy trust together;
merely changing the bind address or Host allowlist is not a deployment solution.

## Configure a local sign-in rehearsal

Install requirements using the project's verified interpreter:

```sh
/usr/local/bin/python3 -m pip install -r requirements.txt
```

Register a confidential web OIDC client with the chosen provider and allow exactly
`http://127.0.0.1:8765/auth/callback` as its development redirect URI. Provider
policy must permit loopback callbacks; otherwise live rehearsal waits for HTTPS.
Use the exact hostname printed at startup; OIDC mode accepts only the configured
callback hostname/port so its browser-bound cookie cannot be lost between localhost
and 127.0.0.1.
Supply these **server process environment** variables using private configuration:

| Variable | Value |
|---|---|
| `MICROGRID_AUTH_MODE` | `oidc` |
| `MICROGRID_OIDC_ISSUER` | Exact HTTPS issuer from the provider |
| `MICROGRID_OIDC_CLIENT_ID` | Registered client ID |
| `MICROGRID_OIDC_CLIENT_SECRET` | Private client secret |
| `MICROGRID_OIDC_REDIRECT_URI` | `http://127.0.0.1:8765/auth/callback` |

Do not put secrets into frontend JavaScript, source control, URLs, screenshots, or
shell commands saved in history. The existing `--env-file` intentionally reads
only weather/carbon credentials, **not** OIDC settings. Configure OIDC in the
server process environment. Never supply the client secret to the browser.

Launch from the browser clone, after installing dependencies:

```sh
/usr/local/bin/python3 -m src.local_web.server --port 8765 --data-dir .cache/private_web --refresh-engine
```

Use `--refresh-engine` once to adopt the reviewed code in a new/existing rehearsal
store; do not automatically refresh on every deployment. Each queued job retains
its recorded engine. An independent runner uses the same directory and does not
need OIDC client credentials. Only the API server performs user authentication.
Provider and live credentials are intentionally not configured by this change.
By default any account the configured provider allows to sign in can create a
workspace; configure invitation/domain/MFA policy at that provider if needed.
Application account disabling and provider-initiated/back-channel logout are not
implemented. Existing sessions last until logout or expiry.

## Ownership and migration

`studies.owner_id` is added non-destructively on Store initialization; existing
rows receive NULL. The owner is a hash of the validated `(issuer, subject)` pair,
not an email or any user-submitted field. SQL queries check the owner **before**
reading request, progress, manifest, or table files. Cross-user and missing IDs
both return 404; unauthenticated private requests return 401.

Coverage includes history, health queue counts, uploaded CSV metadata, study
submission, saved settings, result JSON, paginated tables, CSV downloads, and the
municipal and Southern California submission routes. Saved utility-resolution and
weather references require ownership before use, including annual orientation and
municipal eligibility/bill routes. Location, weather, and utility lookup caches
are partitioned by user. Identical CSV bytes may share content-addressed storage,
but each user has a separate grant and filename; knowing a hash grants no access.
Only the two built-in sample datasets are explicitly provisioned for each user.

Owners stay on durable queued/running/completed/failed database rows. Workers are
trusted internal consumers, not anonymous HTTP users; they claim jobs across
owners without changing ownership, and write results to the job's existing
random-ID directory. A client cannot submit its own owner field. Internal Python
Store methods retain an ownerless mode for local execution/worker compatibility;
HTTP in OIDC mode always supplies the authenticated owner.

**Old ownerless studies and uploads are quarantined from all signed-in users.**
They are not automatically claimed by the first login or by matching an email.
The new guest-save endpoint does not claim old ownerless records: it requires a
current guest cookie and a completed temporary study owned by that guest.
There is no claim/import endpoint for legacy ownerless data. Back up the entire old store while its
processes are stopped, keep an offline copy for local access, and use a new data
directory for OIDC. Any future migration to an account requires an explicit,
operator-reviewed ownership transfer procedure, not a browser-supplied ID.
Turning on OIDC records `auth_required`; that directory subsequently refuses
unauthenticated local HTTP mode even if the operator removes OIDC configuration.
The default `local` mode remains available for a separate trusted local directory.
Partially supplied OIDC settings fail closed instead of falling back to local.
Protect the data directory with filesystem permissions; operators and the worker
are trusted and can read all data. This is application isolation, not OS isolation.

## Credentials and outputs

Known configured credential values (including encoded forms) are redacted from
JSON persistence and HTTP responses/downloads. Worker processes do not receive
OIDC or MySQL credentials. Raw subprocess stdout/stderr are no longer persisted;
worker.log contains only a sanitized outcome. Provider requests still receive the
credentials they need, solely from the server. Source snapshots include Python
files, not `.env` files. Older exported files/logs outside this flow are not
retroactively audited or erased; do not publish the storage directory as static
content. Credential redaction is defense in depth, not a substitute for keeping
provider response bodies and tokens out of application data.

## Verification and remaining deployment work

Run the browser clone tests, not just the main development tests:

```sh
/usr/local/bin/python3 -m pytest -q test/test_local_web_auth.py
/usr/local/bin/python3 -m pytest -q --ignore=test/test_application_interface.py
```

Security tests use mocked provider HTTP responses and locally signed RSA tokens;
no live sign-in provider or API quota is used. Tests exercise signature/claim
rejection, PKCE, callback binding/replay, cookie rotation, restart/expiry/logout,
CSRF/origin checks, ownerless migration, cross-user routes/IDs/downloads,
credential redaction, and authorized real worker completion.

Next checkpoints remain: production server/HTTPS; queue/concurrency/cancellation
and usage controls; backups/retention/deletion; reproducible deployment and server
validation. There is no rate limiting or provider-based account administration in
this checkpoint. Do not expose this server publicly yet.

Billing/modeling scope is unchanged: PG&E solar billing is a bounded monthly
bundled residential NBT comparison. Annual statement reconciliation is distinct
from annual interval simulation. Annual solar dispatch, legacy NEM/NEM2, and
other utilities' export settlement remain incomplete. No rates, verified coverage,
or simulation assumptions were extended by access-control work.

Protocol reference: [Authlib HTTP/OIDC clients](https://docs.authlib.org/en/stable/oauth2/client/http/index.html).

### Checkpoint verification (2026-09-22)

Verified in the Desktop browser clone on `web-browser`, based on `3c66470`:

- Final non-GUI suite: **1,211 passed**, including 22 access-control tests.
  Two NumPy reduction warnings arose in existing municipal dispatch cases.
- Desktop-interface logic: **73 passed**, **4 native-window tests deselected**
  because the prior native initialization had aborted. Actual windows remain
  unverified in this checkpoint.
- Python compilation, JavaScript syntax, and whitespace/diff checks passed.
- In-app browser check confirmed the signed-out prompt and hidden private
  workspace. The isolated temporary test server was stopped afterward.
- Live provider sign-in is not verified: no provider/client has been selected.
  No commit, push, deployment, or production exposure was performed.
