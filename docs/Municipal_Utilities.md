# Municipal electricity service and bill replay — 2026-09-17

## Delivered scope

New backend and local HTTP interfaces resolve electricity **delivery**, retain account confirmation provenance, and replay recurring import bills for these published versions:

| Utility | Schedules | Effective start | Verified through | Billing envelope |
|---|---|---|---|---|
| Alameda Municipal Power (AMP) | D-1, A-1, A-2, A-3 | 2026-07-01 | 2026-09-17 | Complete, confirmed regular 27–33 day cycles; A-3 secondary only |
| Silicon Valley Power (SVP) | D-1, C-1, CB-1, CB-3 | 2026-01-01 | 2026-09-17 | Complete, confirmed calendar months |

The verification cutoff is a software coverage limit, **not a claimed tariff expiration**. No earlier municipal rate version has been loaded. Missing historical periods, future periods beyond verification, partial cycles, or a cycle crossing the coverage boundary fail explicitly. In particular a complete September 2026 bill is not yet covered. Existing PG&E, CleanPowerSF, Hetch Hetchy and Bay Area CCA registries retain their prior coverage; CleanPowerSF/CCA PG&E component coverage still stops September 16.

The browser uses one shared nine-step setup for all supported providers. AMP/SVP service choices are determined by Step 2 coordinates and selected in Step 3; municipal requests use schema 4 and a dedicated account-aware storage optimizer. It compares no battery with cost-optimal, grid-charged storage and exports itemized bills, energy-tier details, native loads and interval dispatch. Actual accounts require saved delivery confirmation; hypothetical alternative locations are explicitly labeled. SF/CCA solar studies use the same setup structure. Municipal onsite generation, export and standby service are not implemented.

The objective includes the same customer charges, energy tiers, eligible-window demand, historical demand ratchet, voltage/PF adjustments, minimum bill and taxes as the bill replay. It enforces battery power/energy limits and equal starting/final energy. Monthly tier regimes are solved separately, including decreasing C-1 prices. Constraints are vectorized; a binary charging-mode fallback prevents simultaneous charge/discharge if the continuous relaxation produces it. Every accepted dispatch is rebilled with the authoritative calculator and compared against the objective.

SVP proportional TOU tier allocation contains a small nonlinear term from the published rate rounding. Optimization uses a rigorous lower bound and reports the resulting dollar optimality-gap bound; final bills always use exact filed prices. The energy-term bound is $0.006 for D-1 and $0.008 for C-1, before the 2.85% public benefits charge. The optimizer rejects CB-3 cases where storage could cross the historical low-load PF exemption threshold. These cases remain available for bill replay. Monthly PF values and account activation states are held fixed.

This is an import-only billing/storage study, with no AC power-flow validation or claim of network feasibility. It does not determine whether a different schedule should be assigned by the utility.

## Geographic resolution

`src/local_web/utility_resolution.py` uses the CEC ArcGIS electric load-serving-entity distribution layer:

- [CEC distribution service](https://services3.arcgis.com/bWPjFyq029ChCGur/arcgis/rest/services/ElectricLoadServingEntities_IOU_POU/FeatureServer/0)
- CEC item `30410214d637434ba1003cbdcc32cf55`; observed data edit epoch milliseconds `1788541732680` (read afresh for every resolution).
- Stable `AgencyNum` values: PG&E `71021`, AMP `10500`, SVP `80560`, Hetch Hetchy `80522`. AMP appears under the historical map name “Alameda Power & Telecom”; canonical display uses its current utility name. OBJECTIDs are preserved as evidence, not used as geographic rules.
- Point intersection plus a **100 metre screening buffer**, in the server's geospatial engine. This buffer is a conservative application rule, not a claim about dataset accuracy.
- The CEC Other layer supplies separate generation **suggestions**, never account enrollment.

An interior single-provider match is `approximate`; overlap or a competing boundary within the buffer is `ambiguous`; missing/unrecognized service or failed boundary metadata is `unsupported`. There is no ZIP/county assignment and no outside-municipal→PG&E fallback. `verified` means **user attestation** from an electricity bill or utility confirmation, not independent account authentication. It retains the original map result, coordinates, confirmation date/reference, CEC source/version, retrieval time and response fingerprints. Do not collect full account numbers in references.

Live public-coordinate checks are archived in `utility_sources/cec-*-validation.json`. Alameda city resolved to AMP and Oakland to PG&E. Santa Clara city returned SVP plus an overlapping Power and Water Resource Pooling Authority polygon; San José returned PG&E plus that overlap. Both remain ambiguous. Palo Alto returned its own municipal utility plus the overlap; it was **not** assigned PG&E. These records corroborate city/county distinctions but are not address-level evidence. Utility context was checked against the [City of Alameda](https://www.alamedaca.gov/Departments/Alameda-Municipal-Power) and [City of Santa Clara](https://www.santaclaraca.gov/services/utilities) official pages.

Geocoding remains the existing `/api/location` operation. Send its selected coordinates to utility resolution separately. A map result does not establish generation enrollment, a rate schedule, or export eligibility.

## Filed rates and billing rules

All energy prices below are dollars/kWh; demand prices dollars/kW per billing month. Values were checked against text and rendered tables in the official PDFs archived under `utility_sources/`. `manifest.json` records URL, retrieval date and SHA-256. `municipal_sources.py` includes the same fingerprints in pinned-engine rate metadata.

### AMP

[Official rates index](https://www.alamedamp.com/157/Alameda-Municipal-Power-Rates), Resolution 5249, adopted April 20, 2026, effective July 1, 2026:

| Schedule | Monthly customer | Energy | Demand |
|---|---:|---|---:|
| D-1 | 24.27 | Baseline .13934; excess .26723 | None |
| A-1 metered | 41.99 | .20946 | None |
| A-2 | 212.62 | .15316 | 14.62 |
| A-3 | 573.60 | .14952 | 18.50 |

D-1 single-phase separately metered dwellings excludes apartment common areas. Gas/other baseline: summer 211 kWh, winter 253. Permanently installed electric heat: summer 258, winter 473. Seasons start with May and November billing cycles; the filed schedule normally does **not** split baseline seasonally inside a cycle. Heating source must be supplied.

The filed A-1 schedule says any one of the preceding 12 months below 8,000 kWh and demand below 500 kW; transfer to A-2 after 12 consecutive months above 8,000 kWh, subject to utility review. This supersedes the contradictory website summary. A-2 uses at least six of 12 months at/above 8,000 kWh and demand below 500 kW. A-3 uses at least six of 12 months at/above 500 and below 4,000 kW. Transfers/retention also involve PF, twice-yearly review and normally one schedule change per year. The API requires a confirmed existing assignment, reports these rules and missing transfer history, and does not infer eligibility for a transfer from simulated peaks.

A-2/A-3 demand is the maximum 15-minute interval. Utility-assigned 1/5-minute measurement for fluctuating loads is explicitly unsupported. Primary A-1/A-2 receives 3% off charges before taxes only when 12 kV delivery, transformer ownership and discount qualification are confirmed. Primary A-3 is withheld pending verification of discount/PF ordering. Rider PF currently applies **only A-3**, despite cross-references in A-1/A-2: .1% per percentage point below/above 95% on energy+demand, excluding customer charges.

Mandatory riders: EAC explicitly states no current charge; ERS .00030/kWh (confirmed against current CDTFA); UUT 7.5% of charges except ERS, with confirmed 5.5% reduced or exempt status and reference supported. AMP energy component detail reconciles distribution + public purpose + generation to energy charges without double-adding it to the total. Actual tax exemptions require customer evidence.

[AMP Rules and Regulations](https://www.alamedamp.com/DocumentCenter/View/448/Alameda-Municipal-Power-Rules-and-Regulations-PDF?bidId=), Article V, defines a regular monthly interval as 27–33 days. Irregular/partial and initial/closing bills require separate proration rules; initial service of 15 days or less carries into the next bill. Those cases are rejected instead of using Hetch Hetchy's study approximation.

### SVP

[Adopted Resolution 25-9516 and rate schedules](https://santaclara.legistar.com/View.ashx?GUID=B4AEAF03-4B68-4F86-92D3-5C3BF99F2CC5&ID=15038898&M=F), effective January 1, 2026:

| Schedule | Monthly fixed | Non-TOU energy | TOU peak / off-peak | Demand |
|---|---:|---|---|---:|
| D-1 | 5.11 | First 300: .15612; excess .17946 | First 300: .17960 / .13690; excess .20295 / .16023 | None |
| C-1 single-phase | 5.52 | First 800: .26620; excess .24166 | First 800: .28968 / .24697; excess .26514 / .22242 | None |
| CB-1 | 100.45 | .16139 | .18490 / .14217 | 12.14 |
| CB-3 | 100.45 | .14864 | .17210 / .12938 | 16.19 |

C-1 three-phase adds 4.33/month. Its connected-equipment minimum is 3.43 per applicable kVA/HP unit; `minimum_charge_load_units` is the account's applicable connected-load sum from the schedule (not the observed grid peak). The minimum is a floor, not an extra customer charge. D-1 excludes apartment common-area service. C-1 is for accounts not qualifying for D-1/CB schedules.

CB-1 entry: above 8,000 kWh for three consecutive months or utility-assessed initial connected load. Retention continues until 12 consecutive months below 6,000 kWh and SVP elects transfer. CB-3 entry: billing demand above 4,000 kW for three consecutive months or assessed initial load; retained until 12 periods below 4,000. New enrollment/transfer approval is not inferred. Confirm existing assignment on the account.

TOU peak is 06:00 inclusive–22:00 exclusive Monday–Saturday, excluding the six specified holidays; all other time is off-peak. D-1/C-1 allocate **each tier proportionally** using the cycle's peak-kWh share, not chronological consumption order. TOU enrollment/metering must be confirmed; installation fees are outside recurring bills.

CB-1/CB-3 demand ignores off-peak hours **even in non-TOU service**, per Note H. Billing demand is the mean of the current eligible-window maximum and the largest such maximum in the year ending with the current month. Exactly 11 preceding dated monthly eligible-window maxima are required; no zero-filled history. 15-minute complete interval data is mandatory. NERC holiday handling follows the [official off-peak convention](https://www.nerc.com/comm/OC/RS%20Agendas%20Highlights%20and%20Minutes%20DL/Additional_Off-peak_Days.pdf): Saturday stays Saturday, Sunday observes Monday. Current 2026 holidays do not require a Sunday substitution.

At qualified 12 kV primary service CB-1/CB-3 discount is 1.52 per billing kW. CB-3 secondary service needs SVP approval. PF adjustment is .1% per percentage point from 85%, applied to customer+energy+demand+voltage adjustment, monthly PF rounded to nearest integer. CB-1 activation after three months above 300 kW, retained until 12 below 200 kW, requires explicit current utility-confirmed PF state. CB-3 skips PF correction when the current maximum is below 10% of the preceding 11-month maximum. Public benefits charge is 2.85% of the filed charge base; state surcharge .00030/kWh per [CDTFA](https://cdtfa.ca.gov/taxes-and-fees/special-taxes-and-fees-tax-rates/). No Santa Clara UUT is added.

## Interfaces and persistence

The browser task was consulted before changes. Legacy request schemas **1/2/3 are unchanged**. New operations are additive, local-only, token-protected and run in the pinned engine subprocess. Their requests/results live in the existing `candidate/<resource_id>/` cache, including selected account facts and geography provenance. The three v1 resolution/eligibility/bill operations are synchronous. Schema 4 storage studies use the independent worker and durable simulation queue.

- `GET /api/capabilities`: new `municipal` field with eight versioned tariffs, coverage, sources/hashes, limitations and supported operations. Separate from legacy `tariffs`.
- `POST /api/v1/utility-resolution`: `{latitude, longitude, manual_confirmation?}`; returns `resolution_id`, canonical delivery candidates, separate generation suggestions, status and evidence. Manual confirmation fields: `{delivery_utility, evidence_type: "electricity_bill" | "utility_confirmation", reference, confirmed_on: "YYYY-MM-DD"}`.
- `POST /api/v1/municipal/eligibility`: request below without `dispatch`; returns each schedule's eligibility/exclusions/missing account fields and qualification rules.
- `POST /api/v1/municipal/bill`: request below; returns itemized bill, energy tier/TOU details, demand determinants, source coverage, account evidence, limitations, `resource_id` and `engine_id`.

Example bill request (abbreviated interval list; actual request must cover the whole cycle):

```json
{
  "interface_version": 1,
  "mode": "actual_service",
  "resolution_id": "<saved 32-character resolution ID>",
  "arrangement": {
    "delivery_utility": "amp",
    "generation_provider": "amp",
    "tariff_id": "amp_a1_2026_07_01",
    "export_program": "none"
  },
  "start": "2026-08-01",
  "end": "2026-09-01",
  "account": {
    "customer_class": "commercial",
    "phase": "single",
    "voltage": "secondary",
    "metered": true,
    "onsite_generation": false,
    "special_riders": [],
    "billing_cycle_confirmed": true,
    "state_surcharge_exempt": false,
    "uut_status": "standard",
    "confirmed_schedule": "A-1",
    "schedule_confirmation_reference": "August electricity bill reviewed"
  },
  "dispatch": [
    {"timestamp": "2026-08-01T00:00:00-07:00", "grid_import_kw": 1.0}
  ]
}
```

`end` is **exclusive** in this dedicated interface (unlike the inclusive day selection in legacy simulation forms). All timestamps need offsets and are converted to America/Los_Angeles. Exactly matching 15-minute indexes reject duplicates, gaps, reordered samples and hourly peak approximations. DST energy uses actual intervals.

For hypothetical comparisons use `mode: "alternative_location"`. It preserves original location evidence and labels results as alternative-location scenarios; it does not claim the alternative utility is available at the original site. Supply the assumed account facts explicitly. Actual mode requires matching saved, user-confirmed delivery. The server rejects injected `resolution` payloads; it loads evidence by `resolution_id`. PG&E/CCA arrangements are checked by the existing provider pairing guard but continue billing through their established study API; unsupported CCA service never becomes a bundled PG&E bill. Municipal arrangements reject external CCA generation or PG&E delivery additions.

Desktop callers may use `src.billing.municipal.eligibility`, `bill_cycle`, and `src.local_web.utility_resolution.resolve_service`. Browser integration must preserve the returned resolution ID and every account input through edit/resubmit, and should render missing/excluded reasons before enabling billing. Do **not** copy these tariffs into the legacy flat-price dropdown. Restart the local server with `--refresh-engine` to expose the new capability in a newly pinned engine.


## Browser and queued storage studies

Set the site in Step 2, then choose a mapped electricity provider in Step 3. The workflow selector and separate municipal form have been removed. The same nine steps, navigation, review page and Run simulation button serve all providers. AMP/SVP account confirmation appears in Step 3, complete-cycle confirmation in Step 4, and tariff/history/PF/tax fields in Step 9. Steps 5 and 6 explain why municipal solar is unavailable; shared inverter and battery parameters remain in Steps 7 and 8. Municipal native load is entered on Review & run. Reuse restores the saved location evidence and municipal account/load/battery inputs into this shared structure.

Location changes immediately clear the prior service, tariff and municipal account confirmations/history. Stale asynchronous lookup results cannot overwrite a newer location. Provider options come from the versioned CEC resolver; CCA suggestions require a mapped PG&E delivery candidate. Unsupported providers are displayed as unavailable, with no outside-municipal-to-PG&E fallback or global list of unrelated regions. Actual account eligibility must still be confirmed. A failed lookup can be retried using Refresh service matches. Defaults fill simulation assumptions only, never demand history or account confirmations.

`POST /api/v1/municipal/studies` returns HTTP 202 with a study ID. Required fields are `schema_version: 4`, `name`, saved `resolution_id`, `mode`, `arrangement`, `account`, `start_date`, inclusive `end_date`, `timezone: America/Los_Angeles`, `timestep_minutes: 15`, all eight `battery` settings and `degradation_cost_per_kWh`. The server attaches saved resolution evidence; client-supplied `resolution` is rejected.

Load choices:
- `{mode: "constant", base_kw: 20}`.
- `{mode: "daily_peak", base_kw: 20, peak_kw: 90, peak_start_hour: 17, peak_end_hour: 19}`, applied every day in local time.
- `{mode: "csv", csv: "..."}` or `{mode: "intervals", intervals: [...]}`, with exactly `timestamp,grid_import_kw` and a complete timezone-aware 15-minute cycle.

Saved studies use the existing status, result manifest, table and CSV routes. Unsupported dates, partial cycles, missing history and invalid service pairings fail before queue insertion. Optimizer-specific unsupported PF-threshold cases fail explicitly in the worker. Restart with `--refresh-engine` after changing the implementation so the server advertises a matching pinned engine.

## Explicitly deferred

- AMP A-4: current linked 2020 document explicitly suspends the schedule; rate table is blank pending a cost-of-service study. No numeric tariff created.
- AMP EV-TOU, unmetered A-1, medical/income assistance/meter opt-out riders: not implemented.
- SVP CB-6: multiple-service aggregation, 13:00–22:00 demand window, 5,000 kW minimum, large energy tiers and voltage adjustments need a distinct model.
- SVP CB-7: market-based option needs contract allocation and CAISO DLAP/TAC/losses/REC/GMC inputs, not a fixed blended rate.
- SVP CB-8: utility-approved retention discount up to 12%, limited term and marginal-cost floor require agreement-specific inputs.
- AMP SS and SVP SB-1: standby/contract capacity/reactive charges not implemented. Accounts with onsite generation are rejected; zero export alone does not establish a standby exemption.
- AMP ERG/NEM and SVP NM: no settlement/export credits; nonzero exports fail rather than appearing as a complete actual bill.
- Partial/irregular cycles, within-cycle rate transitions and unverified historical versions; SVP non-calendar meter-read cycles; AMP primary A-3 discount/PF combination.
- Municipal desktop GUI controls. Existing legacy studies have not been retroactively converted to this richer account contract.

## Validation

Municipal unit tests cover independent hand bills, taxes, tier allocation, voltage/PF, demand ratchet and exclusions, TOU boundaries, holidays, DST, missing history, effective-date gaps, malformed intervals, actual-versus-comparison modes, geographic ambiguity and manual evidence. The real HTTP test runs a saved resolution and full bill through the pinned subprocess, checks persistence and rejects client-injected evidence. Tests mock geography; live city-center checks were separate manual research, not test dependencies.

Validation on 2026-09-17: `/usr/local/bin/python3 -m pytest -q` — **991 passed in 57.16s**. Added dispatch physics, tier/TOU bound, ratchet, off-peak demand, unsupported-period and queued CSV-study tests. `git diff --check` passed. No files have been staged, committed, pushed or promoted to the independent browser clone.

Browser validation: the hypothetical Santa Clara August 2026 CB-1 example completed through the page, after live CEC resolution returned an ambiguous overlap. Study `0a1d9695068e4d04aeca417edf720ffb`: baseline bill $4,423.1383253; optimized utility bill $3,961.065521889474; degradation $131.541274238227; total optimized cost $4,092.606796127701. Billed demand fell from 90 to 50 kW, while the all-hours maximum remained 90 kW because Sunday peaks are excluded from this schedule's demand window. Saved-settings reuse, line-item sums and all five result CSVs were checked. These are scenario results, not an actual customer account or savings guarantee.

Unified setup validation: 77 focused local-web, municipal billing and dispatch tests passed. Browser verification restored and ran saved SVP study through all nine shared steps (study `17bd84d2e71847fa822fef285b7373bb`), then changed Step 2 coordinates to verify immediate removal of the prior service selection. Live Alameda lookup offered AMP; live San José lookup offered PG&E and San José Clean Energy, without unrelated municipal/CCA options.

See [Utility Mapping Audit](Utility_Mapping_Audit.md) for the subsequent 14-location revalidation, guarded CCA identities, visible unsupported providers and point-versus-boundary distinction.
