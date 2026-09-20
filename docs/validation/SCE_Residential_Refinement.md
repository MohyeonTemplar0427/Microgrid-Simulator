# SCE residential refinement validation — September 19, 2026

Implemented calendar-year 2025 D, TOU-D-4-9, TOU-D-5-8 and PRIME as five dated versions each. Current coverage remains June 25–September 17, 2026; the intervening gap rejects explicitly.

## Checks

- Full repository suite: **1,106 passed**, using `/usr/local/bin/python3 -m pytest -q`, with desktop/loopback access.
- 24 new historical tests independently check dated D bills, minimum charges including the WFC exclusion, apartment basic charges, November 15 and DST, holiday TOU, HPWH eligibility, credit ordering and balances, timeline gaps/overlaps, and eight battery reconciliation cases.
- Final focused rerun: 49 passed in the sandbox; the one loopback HTTP test required network permission and then passed separately.
- Live API/queue/independent-worker replay: **18 completed residential cases**, D/4–9/5–8 in Santa Monica, Irvine and Palm Desert, July and November 2025. See `sce_2025_residential_replay.csv`. PLUS one November battery case. All objective reconciliation errors were below $0.005 (reported zero).
- Inputs use EIA utility-average monthly residential consumption shaped by SCE hourly class data, resampled to 15 minutes. These are hypothetical loads, not measured households. Baseline regions 6/8/15 and basic allocation are explicit assumptions, with zero local tax. Input generation and source files remain in `.cache/socal_2025_validation/` and `.cache/sce_history_replay/`.
- Actual browser settings restoration and submission completed: candidate study `f93a66ea493546e0a1ff46866c3a06d1`. Historical windows, climate-credit input and applied-version result table were inspected.

November Santa Monica TOU-D-4–9: grid bill $184.633165; battery bill $167.6668 plus $2.5313 degradation = $170.198093 total operating cost, saving $14.435073. No capital/incentive/payback claim.

## Material limits

Across rate/season boundaries, day-prorated baseline/minimum subperiod allocation remains a study approximation, explicitly warned in results. Exact utility meter-read reconciliation is unfinished. Climate credits are bill-confirmed manual inputs applied once after tax; no automatic entitlement or multi-cycle ledger. CARE/FERA/medical/deed-restricted/CPP cases, unsupported generation providers and exports remain excluded. Export-vs-storage optimization requires complete settlement rules before activation.

CCA and further municipal expansion remain deferred while the current structure is refined.

## Subsequent early-2026 extension

The earlier gap described above is now filled for residential plans using verified January 1 and June 1 price sheets, with explicit cancellation chains. See `../utility_sources/socal/history_2026/README.md`. The original 2025 replay and its recorded engine identity remain unchanged.
