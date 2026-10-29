# PJM regional-average carbon accounting

Schema 11 regional studies can explicitly enable **Include PJM regional-average
emissions** in the local browser's **Simulation time range** step. The default is off. Existing
saved requests without `carbon`, and requests with `carbon: null`, keep their
behavior and report that emissions were not calculated. A missing value is not
zero. The enabled request is:

```json
{"carbon": {"source": "electricity_maps", "region": "US-MIDA-PJM"}}
```

The selected utility's independent grid-operator metadata and confirmed regional
account must both identify PJM. State, tariff, retail supplier, transmission zone
and wholesale pricing location do not assign this carbon signal. MISO utilities
reject this option; no California or PJM factor is substituted for another grid.
This addition is bounded to schema 11, not the separate ComEd/schema 10 or older
PJM/schema 8 study contracts.

## Data and accounting boundary

`local_web/regional_carbon.py` uses the existing Electricity Maps HTTP client,
explicitly requesting `flowTraced=true`, `emissionFactorType=lifecycle`, and
`temporalGranularity=15_minutes` for `US-MIDA-PJM`. Consumption accounting includes
interregional electricity flows. This is a **PJM regional average**, not a
utility/supplier product mix, state-specific intensity or site measurement.
Provider-returned 15-minute resolution does not prove independently measured
15-minute emissions. Source flags and estimation methods remain visible.

See [verified coverage and source ledger](PJM_Carbon_Data_Coverage.md). Only
completed local days in 2025–2026 can be requested. An actual study must obtain
complete matching data; research coverage does not waive per-study validation.
Later 2026 dates cannot be claimed from an earlier receipt.

For each scenario and interval:

```text
grid_import_emissions_kg_co2e =
    scheduled_grid_import_kw * interval_hours * intensity_g_co2e_per_kwh / 1000
```

Comparison and cycle totals sum those interval contributions. The comparison's
`emissions_difference_vs_grid_kg_co2e` is grid-reference emissions minus scenario
emissions under the same signal. It is an attributional accounting difference,
not proven causal avoided emissions or a marginal signal. Exports receive no
emissions credit. There is no carbon price, carbon-optimized dispatch or change
to the retail optimizer. OpenDSS PCC losses remain separate diagnostics. The
lifecycle factor describes imported grid electricity; embodied emissions of
the site's PV, inverter and battery equipment are not assessed.

## Coverage, provenance and saved artifacts

Each source chunk must exactly cover its requested interval grid. Every row
must identify PJM, lifecycle factors, consumption basis, estimation status and
timezone-aware source/revision timestamps. Missing, duplicated, unordered,
negative or nonfinite data rejects the study. No interpolation, gap filling,
constant fallback, future data or substitute grid is used. UTC instants preserve
both autumn repeated hours; local calendar boundaries use `DateOffset`.
Thirty-minute studies average complete pairs of provider 15-minute values.

The study retains full raw responses in `carbon-source/`, a canonical
`carbon-source.csv`, and a `carbon-source.json` manifest with request identity,
retrieval timestamps and SHA-256 hashes. Reuse verifies hashes, source identity,
the exact grid and raw-to-CSV reconciliation. Alternative tariffs reuse the same
source bytes. The result manifest records the zone, provider, factor basis,
units, coverage bounds/counts, estimated counts/methods and source URLs.

The normal browser comparison shows kg CO₂e and the grid-reference accounting
difference. Results disclose coverage and estimated intervals. Input/dispatch
CSV files carry intensity and interval emissions; `carbon-provenance.csv`
preserves provider interval flags/revisions. CSV endpoints and the ordinary ZIP
include these tables and the result manifest. Raw provider responses stay in
the private local study directory. Save/reopen and restore/rerun preserve the
explicit carbon choice; a new run retrieves and validates its own source.

Credentials come from the existing local credential loader. They are never
stored in requests, source receipts or results. Failed access rejects an enabled
study, rather than silently omitting carbon. Existing local-only schema 11
restrictions remain; this work makes no hosted redistribution-rights claim.

## Validation scope

This change adds an optional input and post-dispatch results, without changing
billing math, solver logic, time grids or network physics. Targeted acceptance
uses new carbon/serialization tests, existing Electricity Maps/California-carbon
checks, and the workflow tier for the shared worker/artifact contract. A selected
2025 annual residential and 2026 commercial study exercise all three scenarios
with independent carbon arithmetic and the existing billing/SOC/electrical
audits. It does not rerun unrelated utility matrices or claim a full-release
pass. See [implementation evidence](PJM_Regional_Carbon_Implementation_Validation.md).
