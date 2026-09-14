# Codex handoff — end of 2026-09-13

Supersedes the morning version of this file. `main` is at `01fdcb6`, working
tree clean, **469 tests passing**.

Read [CLAUDE.md](../CLAUDE.md) first, then
[Microgrid_Backend_Architecture.md](Microgrid_Backend_Architecture.md) before
touching the backend. This file covers what changed today and how the two
agents should divide tomorrow's work.

---

## 1. What landed today

Five commits. Two agents worked in parallel and their changes were merged
into `76e172f`.

**Optimizer made ~40x faster.** The constraint loops in
`run_cost_optimization`, `run_carbon_optimization` and
`run_combined_optimization` built two scalar cvxpy constraints per interval
(5,766 objects at 2880 intervals). They are now two array constraints each.
A 30-day, 5-scenario run went **16.2s -> 1.15s**; 90 days now solves in
~0.5s. Verified bit-identical: 18 runs across four horizons plus
demand-charge and zero-PV cases, worst difference across every numeric
column `0.000e+00`.

**All PG&E business plans implemented** — twelve tariffs, up from two:

| | schedules |
|---|---|
| B-1 | single-phase, polyphase (Codex) |
| B-6 | single-phase, polyphase |
| B-10 | secondary |
| B-19 | mandatory, voluntary, Option R, Option S |
| B-20 | secondary, Option R, Option S |

All secondary voltage, bundled, effective 2026-03-01 (Advice 7846-E).

**Every rate re-validated against the source PDFs** by scraping the sheets
programmatically and diffing against the registry — 34 energy/customer
values and 9 demand values. No discrepancies. Structural decisions confirmed
against source too: seasonal maximum demand collapsed to one component
(B-10/B-19/B-20 all print summer and winter at identical rates), B-1
correctly excludes the B1-ST column, B-6 genuinely has no part-peak block.

**Tariffs reachable from the GUI.** `run_integrated_csv_analysis` now
accepts `tariff_id`, so the offline CSV path bills; previously the tariff
dropdown was disabled in that mode and the tariff was ignored entirely.

**Two eligibility guards.** A ceiling (B-6/B-1 under 75 kW, B-10 under
499 kW) and a floor (B-20 at 1,000 kW) warn when a simulated peak means the
modelled bill is for a plan the account could not be on. Plus a warning that
on the CSV path the optimizer prices against the CSV column while the bill
uses tariff rates — they agree only if the CSV carries the tariff's rates.

**Generated tariff documentation.**
[PGE_Tariff_Reference.md](PGE_Tariff_Reference.md) — every period rate,
demand component, eligibility band and source URL for all twelve schedules,
produced by `tools/generate_tariff_reference.py` from the registry. It
refuses to run if a registered tariff is missing from its display order.
**Regenerate it rather than editing it.**

**Default GUI parameters.** `gui_preferences.json` (gitignored, machine
local) plus two datasets under `data/` — a 254 kW site for B-10 and a 54 kW
site for B-6. Offline, no API keys, runs in 0.33s.

### Corrections to beliefs that were previously recorded

- **Demand-charge-aware optimization is implemented**, contrary to the old
  CLAUDE.md entry. `_build_monthly_demand_charge_cost` puts
  `cp.max(grid_import_kw[month])` in the objective and it works — peak
  228 -> 113.5 kW under B-10.
- **`_maximum_demand_rate` understating the rate costs almost nothing.**
  It passes only `MAXIMUM`-basis components ($39.08 on B-20 rather than the
  $80.43 a summer peak-hour kW really costs), but peak shaving *saturates*:
  once the rate justifies shaving at all, the battery shaves to its physical
  limit and the exact rate stops mattering. It changes the answer only for
  batteries oversized relative to load (10,000 kWh+ on a 1,320 kW peak),
  worth ~19 kW there. Lower priority than it first appeared. The real
  limitation is that one blended rate is applied to the *monthly* maximum,
  so the optimizer cannot tell "shave the 4pm peak" from "shave the 3am
  peak".

---

## 2. State

- `main` @ `01fdcb6`, clean, **469 tests**, suite runs in ~2.7s
- The stale Codex worktree at `~/.codex/worktrees/7d67/` was **deleted**. It
  had a corrupted `core.worktree` pointing at `.git/modules`, which made
  `git status` there report every tracked file as deleted. If a worktree's
  status looks impossible, check
  `git -C <path> rev-parse --show-toplevel` before believing it.
- `gui_preferences.json` is now gitignored and untracked; the local copy
  still drives the GUI.

---

## 3. Tomorrow — two lanes, split by file ownership

Today both agents edited the same six files and the merge had to be done by
hand with `git merge-file --diff3`. The split below is by **file
ownership**, not by feature, so that cannot recur.

### Lane A — backend depth
**Owns:** `src/surplus/`, `src/billing/`, `src/dispatch/`,
`src/profiles/`, `src/signal_pipeline/`, and their tests
(`test_surplus_allocation.py`, `test_billing.py`, `test_dispatch_*.py`,
`test_signal_*.py`, `test_timeseries_framework.py`).
**Never edits `src/simulation/`.**

1. **Wire `surplus` into the dispatch path** — the largest open item. It is
   imported only by its own test today, so `allocate_surplus`, both
   power-balance validators and the carbon monetization in
   `surplus/metrics.py` are unreachable. Expose a function the GUI lane can
   call; agree its signature with Lane B before starting.
2. **Peak-scoped demand variables** in `single_day_analysis.py` — separate
   peak variables for the peak-hour window rather than one blended rate on
   the monthly maximum. Keep the constraints vectorized (see CLAUDE.md).
3. **Shared-generation billing** in `charges.py` — currently raises, because
   the NEM/NBT credit rules are not configured. Needs a modelling decision
   before code.
4. **Holidays** in `price_sources.py` — needs a holiday calendar per
   utility. Note this does *not* affect the PG&E B-series, whose periods all
   apply every day.

### Lane B — GUI and integration
**Owns:** `src/simulation/` (all of it), plus
`test_application_interface.py`, `test_interface_analysis.py`,
`test_graphical_interface.py`, `test_console_interface.py`.
**Never edits `src/billing/` or `src/dispatch/`.**

1. **Results visualisation** — `application_interface.py` still carries the
   placeholder "The completed workflow will provide visual comparisons and
   downloadable CSV outputs here." CSV export works; the charts do not exist.
2. **Meter-topology dropdown** — `billing` has four topology builders,
   `METER_TOPOLOGY_LABELS` exposes two. `individual_meters` is implemented
   and merely unwired.
3. **Tariff comparison run** — one dispatch, billed under several tariffs,
   so the GUI can answer "which plan should this site be on?". All twelve
   are registered; this is presentation only.
4. Wire whatever Lane A exposes, once its signature is agreed.

### Rules for both

- **`src/billing/__init__.py` is Lane A's.** Its import and `__all__` lists
  were the worst conflict today. Lane B must not touch it.
- **`CLAUDE.md` and `docs/`**: either lane, but announce it.
- **Commit before switching lanes.** Today's merge was only recoverable
  because uncommitted work was backed up first.
- **Re-read a file before editing it.** Both agents are live.

---

## 4. Still not implemented, with the blocker

| Item | Blocker |
|---|---|
| B1-ST | $7.86/kW demand assessed 2-11 p.m. only — the union of B-1's peak and part-peak blocks. `DemandChargeComponent` has no windowed basis; two components would take each maximum separately and overcharge. |
| Primary / Transmission voltage classes | Rates are published and parsed, but the modelled 480 V service is secondary, so they would be billing-only. |
| Agricultural schedules | Keyed to annual operating hours with flex-day options on specific weekdays. `TOUPeriod` has no day-of-week field. |
| Other utilities | `REGION_RETAIL_TARIFF_IDS` covers `caiso_np15` only; ERCOT and PJM return an empty tuple. |
| Measured load / weather PV / measured inverter PV | Deliberate. See CLAUDE.md — they raise on purpose. |
| Export compensation (NEM/NBT) | Not part of any of these schedules. |
