# Repository agent instructions

These rules apply throughout this repository in both the main development
checkout and the independent web-browser clone. Keep this file in Git so the
validation policy follows normal commits and merges between branches.

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

