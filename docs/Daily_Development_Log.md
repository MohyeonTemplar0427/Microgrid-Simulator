# Daily development log

Add one dated entry when a development session ends. Keep the newest entry first. Record what changed, how it was checked, where the code was saved, and what remains. Use the same headings for future entries so this document stays easy to scan.

## 2026-09-23 — Browser hosting and temporary results

**Workspace:** `Microgrid_Web_Browser`

**Branch:** `web-browser`

**GitHub:** [Commit `4d6aa30` — Prepare browser hosting and temporary study results](https://github.com/MohyeonTemplar0427/Microgrid-Simulator/commit/4d6aa306e31fc1a70093d04aa8d167b67693f9f2)

### Work flow

1. Added OpenID Connect sign-in, private sessions, and server-side ownership checks for studies, uploads, saved inputs, results, and downloads. Existing ownerless local studies remain quarantined from hosted users.
2. Prepared a single-host deployment path: Caddy for HTTPS, Waitress for the browser/API, and a separate simulation worker. The API still binds to localhost.
3. Added resource controls: queue and concurrency limits, cancellation of queued or running studies, runtime measurement, a 200-simulation daily limit for signed-in users, and storage limits.
4. Measured full-year study storage. New runs retain compact OpenDSS validation summaries instead of the large interval-by-interval AC tables. New result tables are stored as CSV with small metadata files; browser pages are read from those CSVs on demand.
5. Added optional temporary guest studies. A guest can run, inspect, and download private results. “Save to my profile” starts sign-in and transfers the study only when the signed-in session also has the original guest cookie. Signed-in users can save their own temporary results directly. Unsaved results expire 24 hours after completion; a download does not extend that period.

### Verification and outcome

- The broad non-GUI suite passed: **1,351 passed, 1 skipped**. Final focused privacy, download, and expiry checks passed: **4 passed**. JavaScript syntax and staged diff checks passed.
- In the synthetic full-year, five-strategy storage benchmark, a 15-minute study fell from **357.7 MB originally** to **28.7 MB** after removing saved AC tables and duplicate JSON result tables. These are disk measurements, not RAM or cloud-capacity measurements.
- Pushed `4d6aa30` to GitHub on `web-browser`. The browser clone was clean and synchronized at wrap-up. The clone's `origin` was changed from an outdated SSH address to the repository's working HTTPS address. `main` was not changed.

### Remaining work

- Choose and validate a hosting environment and a live OpenID Connect provider. The site has not been deployed publicly.
- Review resource and storage limits against the selected server, then address persistent-storage operations: backups, retention, and user deletion.
- Validate a reproducible deployment and the full browser → API → worker flow on that server.

Detailed implementation notes: [Web access control](Web_Access_Control.md), [Web hosting](Web_Hosting.md), and [Web resource controls](Web_Resource_Controls.md).
