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

## Efficient development with billing safeguards

- **Scope and orient once.** Establish the requested outcome, affected paths,
  supported account/date scope and acceptance checks. Inspect Git status,
  relevant instructions, current source and the latest applicable handoff.
  Reuse that orientation; re-read targeted files when they change or concurrent
  work makes an earlier read stale. Keep routine edits and commit-message tasks
  brief; reserve extended investigation for substantive uncertainty.
- **Keep context and handoffs compact.** Put durable decisions in the relevant
  project documentation. For a handoff or requested fresh implementation chat,
  include the goal, constraints, affected paths, candidate identity, evidence
  locations, completed checks, exclusions, unresolved gaps and next steps.
  Reference documents and receipts instead of copying the conversation history.
- **Research specific gaps.** Reuse existing clients, source ledgers and verified
  components after checking their applicability. Target missing components and
  date windows in official utility/regulator sources; preserve references and
  provenance. Record blocked sources and remaining gaps instead of repeatedly
  trying an unchanged route. Never infer missing rates or eligibility, extend
  coverage without evidence or silently substitute data. Provisional assumptions
  require explicit user authorization and separate, visible scope and evidence labels.
- **Delegate bounded, independent work.** Give each agent a distinct question or
  owned edit scope, shared verified context, required checks and a concise output
  contract. Avoid overlapping edits and repeated repository-wide orientation or
  identical research. Retain independent source/benchmark review when it helps
  establish billing correctness; parallel work saves elapsed time, not necessarily
  model usage.
- **Keep tool output focused.** Search relevant paths and read needed sections.
  Save full logs, source material and large artifacts in the appropriate private
  or ignored evidence location; return summaries, failures and receipt paths.
  Inspect detailed output when a failure or unresolved concern warrants it.
  Batch independent reads and avoid frequent unchanged progress polls.
- **Validate in stages and by impact.** Use the targeted validation policy below.
  Routine utility additions require utility-specific acceptance, not the entire
  release suite. Freeze the candidate before final acceptance and the selected
  historical matrix. Avoid repeating passing checks or matrices without a new
  change, failure or unresolved concern. Subsequent edits require affected checks
  and any necessary broader regression; documentation-only edits normally need
  textual/link/diff checks, not simulation reruns. Explicit user-required tiers
  and acceptance checks still apply.
- **Preserve proof and accuracy.** Keep effective dates, eligibility, units,
  timezone/DST, missing-data rejection, independent bill benchmarks, itemized
  bill/dispatch/credit reconciliation and required OpenDSS scenario/interval
  coverage. Resume only under the launcher's matching-fingerprint and artifact
  re-audit rules in `docs/Development_Validation.md`; an old passing report is
  not proof for a changed candidate. Retain original evidence pins and report
  unverified assertions, unsupported scope and solver-proof limitations clearly.

## Validation launcher

Use `/usr/local/bin/python3 tools/validate.py` with explicit `focused`,
`workflow` or `release` tiers; see `docs/Development_Validation.md`. GUI tests
are excluded by default and require `--include-gui`. Historical matrices are
opt-in with prepared inputs; use `--resume` only for matching frozen evidence.

## Targeted validation policy

- **Routine utility additions and tariff updates:** select the utility's tests
  with focused `--test` paths plus directly affected integration/contract tests.
  The broad `--area regional` grouping includes other utilities; it is not the
  default for a single-utility change. Registry entries, default sites and new
  browser account fields do not alone require the full release suite when shared
  behavior is unchanged. Record the affected paths, selected checks and exclusions.
- **Billing acceptance remains strong:** verify dated sources, eligibility,
  delivery/supply/rider/tax arithmetic, independent benchmarks, numeric/symbolic
  parity, dispatch and credit/SOC reconciliation, rate boundaries, DST, missing
  data and rejection of unsupported settlement. For browser wiring, include the
  affected form, queued-worker, saved-settings and CSV/ZIP checks, and syntax
  checks for changed JavaScript. Use the full workflow tier when shared API/worker
  contracts change or targeted checks do not bound their impact.
- **Historical/electrical acceptance:** normally run one explicitly selected
  new-utility matrix on the finished frozen candidate, covering grid-only,
  PV-only and PV-plus-battery cases across supported rate regimes. Include a
  full-year billing/dispatch study where coverage permits and the acceptance
  scope calls for it. Do not rerun unaffected utilities' historical matrices.
  A smaller electrical sample requires a recorded reason and explicit dates,
  scenarios and interval counts; report it as sampled coverage. The current
  driver checks every interval in each selected case: do not bypass its audits
  or present sampled evidence as an all-interval annual electrical pass.
- **Full regression checkpoints:** run the release tier for shared-engine
  behavior changes affecting multiple utilities, including billing math,
  dispatch/solver logic, time grids, credit/state handling, PV/storage physics
  or electrical replay; also run it at release milestones, before stable-engine
  promotion, when explicitly requested, or when failures/uncertain impact require
  broader regression. Touching a shared registry file alone is not this trigger.
  Promotion and deployment still require separate user authorization.
- **Evidence labels:** targeted acceptance is a policy selection using existing
  launcher tiers, not a new tier or a full-release pass. Preserve matching-pin
  resume rules, solver proofs, source gaps and original evidence identities.

## Validation workflow and browser limits

- **Use local API, queued-worker tests and saved artifacts first.** Validate
  inputs/provenance, itemized bills, dispatch/credit state, electrical results
  and CSV/ZIP contents there. Run bulk scenarios and parameter sweeps through
  scripts, not browser automation. Verify download endpoints and saved bytes
  without waiting for browser download events or file choosers.
- **Freeze the candidate before browser acceptance.** Record its immutable
  engine ID and frontend fingerprints; finish the checks and selected matrix
  required by the targeted validation policy on that candidate first. Keep
  earlier results attributed to their original pin, rather than relabeling them
  as new-candidate evidence.
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

