# Repository agent instructions

These rules apply throughout this repository in both the main development
checkout and the independent web-browser clone. Keep this file in Git so the
validation policy follows normal commits and merges between branches.

## Primary interface and development scope

- The local browser is the primary interface for development and local use.
  Focus new work on the shared backend and browser workflows.
- Desktop GUI development and design updates are paused unless explicitly
  requested. Preserve existing GUI code and shared contracts; do not remove it.
- Do not launch or leave a native desktop GUI open for routine development or
  validation. GUI-specific tests are opt-in; report their exclusion clearly.
- Public website deployment remains a separate workstream. Do not promote a
  candidate, deploy, commit or push without the user's authorization.

## Validation launcher

Use `/usr/local/bin/python3 tools/validate.py` with explicit `focused`,
`workflow` or `release` tiers; see `docs/Development_Validation.md`. GUI tests
are excluded by default and require `--include-gui`. Historical matrices are
opt-in with prepared inputs; use `--resume` only for matching frozen evidence.

## Validation workflow and browser limits

- **Use local API, queued-worker tests and saved artifacts first.** Validate
  inputs/provenance, itemized bills, dispatch/credit state, electrical results
  and CSV/ZIP contents there. Run bulk scenarios and parameter sweeps through
  scripts, not browser automation. Verify download endpoints and saved bytes
  without waiting for browser download events or file choosers.
- **Freeze the candidate before browser acceptance.** Record its immutable
  engine ID and frontend fingerprints; finish the required regression and
  simulation checks on that candidate first. Keep earlier results attributed
  to their original pin, rather than relabeling them as new-candidate evidence.
- **Run one concise browser acceptance pass on the frozen candidate.** Cover
  representative changed workflows: configuration, submission, rendered
  results, save/reopen and restore/rerun. Do not repeat the full simulation
  matrix in the browser or rerun acceptance after every intermediate edit.
  If acceptance finds a defect, fix it, record the updated candidate and rerun
  the affected checks plus any required regression checks.
- **Stop at the first stalled browser operation.** Use short calls with an
  explicit timeout, normally 30 seconds or less. An unexpected timeout,
  unresolved upload/download wait or stale session is a reason to stop using
  that failing operation, not retry it. Do not increase timeouts, add sleep
  loops or repeat the same route. Requested timeouts have previously failed
  to bound actual elapsed time. Cancel the call if cancellation is available,
  then continue independent work through APIs and artifacts. Avoid the
  upload/download-event automation that has already stalled in this project.
- **Report evidence and time honestly.** If a required browser assertion
  remains blocked, identify it as unverified; API checks do not prove that UI
  action succeeded. Separate wall-clock elapsed time, test/simulation runtime
  and browser-tool waits. Background jobs can overlap those waits, so do not
  describe total elapsed time as active development time.

