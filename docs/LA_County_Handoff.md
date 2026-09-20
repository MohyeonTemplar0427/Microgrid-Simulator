# LA County expansion handoff — 2026-09-19

## Status

**Partial implementation. The overall requested expansion is not complete.**
Glendale's five ordinary import plans are implemented in billing, dispatch and the existing browser. All six new distribution utilities and the LA generation providers have mapped identities and explicit coverage records. Mapping/research records are not executable tariffs.

Remaining work has two different causes:
- Source retrieval/verification gaps: Vernon filed schedules, Industry rate/rule books and account terms, CEU generation agreement terms, complete SCE unbundled/CCA rider combinations.
- Unfinished implementation and rule reconciliation: Pasadena, Burbank, Azusa and CCA products. These are not all unavailable data. Several official rate tables were found; work is still required to implement their rules accurately. Continue in the user's priority order; do not treat this checkpoint as scope closure.

See [coverage matrix and source ledger](LA_County_Utilities.md). Unsupported features reject or remain disabled; current rates are not backdated.

## Repository and preview

Work is directly in `/Users/junhayang/Desktop/EnergyEngineerSession/Microgrid_Simulator`, branch `main`. Pre-existing SCE history/refinement changes were preserved. Nothing staged, committed or pushed. The independent `Microgrid_Web_Browser` clone was not changed.

- Tariff registry: `socal-2026-09-19.3`; GWP rates: `gwp-2026-09-19.1`.
- Candidate port 8879, data `.cache/la_county_candidate`.
- Main preview port 8876, data `/tmp/microgrid-municipal-browser-review`.
- Validated/promoted engine: `a85efaef54fb1638d920a3e311c02a0cf193728e82f0ccd9fbbd3306073312ac`.
- Previous main engine: `dc35d428ca013098e67f93a04875fa656babd7aa9eb0d49feeb5c6c487eb1b44`; pointer backup `engine-before-la-county.json` in its data directory.
- Servers were idle before restart; immutable old engines and studies retained. Existing SF study `95c1f1eb32ce415e9dd20c432c8c2b7c` result still returned HTTP 200 after promotion.
- Static assets follow the existing server mechanism; capability-based utility activation keeps new GWP controls disabled against older pins. Research coverage metadata is served by the pinned backend.

## Validation

`/usr/local/bin/python3 -m pytest -q`: **1,157 passed**, two existing NumPy warnings in municipal dispatch tests. Subsequently added a direct-dispatch PV rejection test and refined GWP warning text: affected LA/SoCal suite **56 passed**. JavaScript syntax checks passed. The full-suite result predates that final added test; do not report it as 1,158 full-suite passes.

Tests cover independent GWP energy/tier/tax calculations, November base-rate transition and DST, TOU boundaries/Thanksgiving Friday, demand history and 15-minute requirements, missing/future/rider coverage rejection, all five plans' battery physical balance and objective reconciliation, six municipal identities/boundary ambiguity, CEU/SCE role separation and no SCE-by-exclusion, five LA CCA identities with provenance, and research-versus-executable coverage. Existing CCA mocks were updated to supply the new layer metadata request.

### Actual browser runs

1. `87191e384e39453aad68f90cb380e6bd` on candidate 8879, initial candidate engine `ed1174771ded744b5a92df222f9db9f9490522ec4bf00fdf5aa13997e7f2e720`:
   - Synthetic Glendale residence, coordinates 34.1425, -118.2551, July 1–31, 2026 inclusive, 15 minutes/Pacific.
   - L-1-A, 1 kW constant load = 744 kWh, secondary/single phase, 7% Glendale tax; no PV/battery. Hypothetical account, not a claim of actual customer eligibility.
   - Bill **$322.469925801000** (browser rounds $322.4699; verify full-precision CSV if needed).
   - Independent formula `(31*.75 + 310*.3071 + 310*.3806 + 124*.4547)*1.0285*1.07 + 744*.0003`.
   - Saved settings restored coordinates, tariff, tax and account confirmations; old result remained readable after candidate refresh.

2. `9229c5cb3845401bbe9a5d49d7653ed8` on final candidate engine:
   - Same synthetic residence, dates, 1 kW load, tax and no PV; L-1-B.
   - Battery 10 kWh, initial/final 5 kWh, SOC .2–.8, max charge/discharge 3 kW, each efficiency .95, degradation $.01 per kWh of charge plus discharge throughput.
   - Baseline **$281.725639119**; storage explicit operating cost **$222.272313697** (bill about $219.5087 plus wear $2.7636), savings **$59.453325422**.
   - Independent analytic fixture: 23 peak weekdays, 138 peak hours and 606 base hours. Each daily cycle delivers 5.7 kWh using 6/.95 kWh charging; apply the same public-benefit/tax multipliers, incremental state surcharge and throughput wear. Matches the browser result.

3. Real CEC browser lookup at 33.86, -118.08:
   - Preserved SCE plus Metropolitan Water District ambiguity; CEU displayed as a disabled generation option with participation/storage and missing-billing explanation, not delivery.
   - Selecting SCE + actual CCA generation blocked advancement with an explicit unsupported-billing message. No synthetic CCA bill was produced.

These checks validate GWP and unsupported-pair behavior; they do **not** satisfy the requested successful simulation of a newly implemented CCA/CEU bill. That remains outstanding. No browser simulation is claimed for PWP/BWP/ALW/VPU/IPU because no billing plan was enabled for them.

## Next implementation work

1. Resolve PWP final restructuring/TOU meter-transition text, SLATS exemption allocation and declining underground surcharge. Add exact rounded-demand/PF and history treatment shared by bill and optimizer; independently test monthly/bimonthly cycles.
2. Load BWP adopted full schedules and adjustment history. Extend physical inputs/objective for apparent demand rather than assuming kVA=kW; resolve transfer/tax inclusions before computing totals.
3. Integrate ALW dated base/PCA/PBC records and minimum/proration rules, then declining-block and rounded-demand optimization. Historical books and current rider pages are recorded in the source ledger.
4. Retrieve Vernon and Industry filed schedules through official archive alternatives or utility-supplied documents. Do not use public hearing drafts as adoption proof.
5. Build SCE unbundled delivery and independently versioned CCA-CRS/PCIA/GMS before adding CPA then the remaining providers. CEU requires accepted agreement terms and separate-bill presentation.
6. For each newly enabled provider repeat independent fixtures, actual browser runs, saved-state/unsupported checks, then candidate promotion. Preserve the user's existing dirty changes.
