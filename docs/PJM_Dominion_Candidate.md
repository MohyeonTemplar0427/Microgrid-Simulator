# PJM / Dominion Virginia candidate — October 11, 2026

## Status and acceptance

The first executable case is **Henrico County, Dominion Energy Virginia bundled
GS-2T, commercial, approved non-export parallel operation**, September 1–30,
2026. Composite verified tariff coverage is September 1–October 11, 2026.
This is a local development candidate, not a promoted engine or a complete
historical-year release. The existing Web UI v1.0.1 designation is unchanged.

| Acceptance item | Evidence / current limit |
|---|---|
| Independent tariff benchmark | Constant 20 kW, September 2026: $1,874.5798, reconciled against independently coded filed-rate arithmetic |
| End-to-end case | 1,440 half-hour intervals; grid, PV and PV + storage; component savings and representative OpenDSS replay |
| Historical weather | ERA5 September 2026 through Open-Meteo, raw response hash, retrieval time, request and grid coordinates retained |
| Historical PJM data | Strict official-file import bypasses the live 186-day archive guard, preserving native observations and revisions; full 2025 DST coverage tested with **synthetic fixtures** |
| Actual PJM retrieval | No PJM key configured; unauthenticated API returned 401. A genuine customer-selected DOM file has not been supplied. The case explicitly reports the absent wholesale signal |
| Full historical-year bills | **Not complete.** All 2025 base/rider versions and linked billing-cycle orchestration still need verification. A preflight rejects the year instead of extrapolating current rates |
| Public release | **Not promoted.** Candidate API and saved-study retrieval are local-only; market data excluded from table and ZIP downloads |

## Three independent layers

`src/regional/account.py` records distribution utility, state jurisdiction,
retail supplier, customer class, tariff, grid operator, transmission zone,
separate wholesale pricing location and utility-verification evidence. No
state-to-utility assignment, nearest-node lookup or Western Hub default is used.
The current case is a labeled hypothetical account; real selections require
bill or utility confirmation. The **Henrico locality is an explicit account
fact**, not a polygon lookup. Other local tax jurisdictions are unsupported.

`src/signal_pipeline/providers/pjm.py` remains the live market adapter. Its
existing guarded five-minute retrieval is retained to avoid an unbounded
all-node archive download. `import_historical_file` adds a validated local-file
path using `pjm_file.py`; archive age does not reject it. PJM's official archive
guide and installed gridstatus 0.36.0 confirm historical LMP retrieval exists;
the old wording that those data were deleted was incorrect.

`src/billing/dominion.py` calculates retail charges independently of wholesale
prices. `src/dispatch/dominion.py` uses the same charge expressions, then
reconciles against the authoritative numeric bill. `opendss` separately replays
the resulting power schedule. Wholesale signals cannot alter this bundled
bill or its storage objective.

The interfaces support later region-specific adapters without embedding CAISO
timezones in the account contract. ComEd, ERCOT and MISO are not implemented.

## Filed GS-2T rules and selected scope

Official [business-rate catalog](https://www.dominionenergy.com/virginia/rates-and-tariffs/business-rates)
and [GS-2T](https://www.dominionenergy.com/-/media/content/rates-and-tariffs/pdfs/virginia/large-business/schedule-gs2t.pdf).
Base rates effective January 1, 2026; the composite window starts when all
included current riders are verified, September 1, 2026. Coverage ends on the
research date, not an inferred future expiration of the utility plan.

- Voluntary nonresidential bundled service: at least three >=30 kW measured
  demands and no more than two >=500 kW demands in the current/prior eleven
  billing months. This first existing-account path conservatively requires
  eleven supplied prior peaks below 500 kW, three qualifying peaks, PF >=85%,
  secondary metering, no special contracts or rider exemptions. It does not
  automatically apply this tariff to a hyperscale data center.
- Demand is the highest **30-minute average**. Summer on-peak is weekdays
  10:00–22:00, June–September; winter is weekdays 07:00–22:00. The filed
  schedule does not exclude holidays. All other hours are off-peak.
- Ordinary distribution demand uses the current/prior eleven-month maximum,
  at least 30 kW. For the selected approved parallel-service case, the
  distribution charge instead uses the utility contract demand; that contract
  must cover the ratchet and cannot be exceeded by optimized imports.
- Contract distribution demand is held constant across all three
  counterfactuals, including grid-only. These are comparisons under the **same
  existing parallel-service contract**, not predictions of a new installation's
  contract negotiation. Distribution-demand savings are zero in this case.
- Generation and transmission demand use the current cycle's on-peak maximum.
  Supply demand season is determined by the **explicit utility billing month**;
  TOU energy hours use each service date. Billing month is not inferred from
  the last interval or meter-read date.
- Base fixed/demand and associated demand rider charges use the documented
  30-day proration convention; energy charges use actual kWh. One confirmed
  cycle of 1–40 complete local service dates is required. This is not a
  simulated fragment of a larger unknown cycle.

Implemented base rates, in dollars:

| Component | Rate |
|---|---:|
| Basic customer, 30 days | 37.08 |
| Distribution demand, kW | 4.963 |
| Distribution energy, kWh | 0.000079 |
| Summer / winter generation on-peak demand, kW | 4.526 / 2.215 |
| Generation adjustment demand | 0.000 |
| Transmission on-peak demand, kW | 2.313 |
| On/off-peak generation energy, kWh | 0.020278 / 0.009928 |

Riders A, C1A, C4A, CCR, RPS, RGGI, PIPP, DIST and T1 are separate lines.
CE, CERC, E, GEN, OSW, SMR and SNA use their filed energy charge when meter
load factor is <=50%, and their on-peak demand charge otherwise. Load factor
uses meter purchases / calendar billing days / 24 / measured maximum; it does
not use native building demand or generated PV. Zero RGGI/PIPP rates remain
explicit. Rider D concerns construction contributions and is not a recurring
bill charge; voluntary CRC is for separately qualifying large-service accounts.
Their eligibility documents are retained, not silently added.

Capacity recovery is bundled in the generation tariff/riders; base transmission
and Rider T1 recover transmission. **No PJM auction capacity price, capacity
PLC or transmission NSPL charge is added.** These retail peaks are not a PJM
coincident-peak obligation. A future retail-access adapter must separately
record capacity and transmission measurement windows, later delivery/billing
periods and contractual rates; it cannot reuse this bundled charge treatment.

Consumption tax uses the filed August 16, 2025 tiers: $0.001565/kWh through
2,500; $0.001055 on the next 47,500; $0.000845 thereafter. The total includes
state, regulatory and local consumption tax components, once.
[Henrico's separate commercial utility-consumer tax](https://henrico.gov/finance/approved-tax-rates-and-schedule/)
is $1.15 + $0.00713/kWh, capped at $10/month. Both are itemized. Data-center,
construction, contracted minimum/facilities, low-PF and voluntary rider cases
are rejected rather than omitted from a purported full bill.

## Optimization scope

The numeric bill implements both load-factor rider branches and all tax tiers.
The first optimizer only accepts configurations **provably below 50% load
factor for every feasible terminal-neutral schedule** and above the Henrico tax
cap. It bounds minimum imports using native load minus available PV minus
maximum discharge. It bounds maximum imported energy using native energy plus
maximum possible cycling losses. Failure to prove this scope causes rejection;
there is no guessed regime or manipulable artificial maximum-demand variable.

Declining consumption-tax tiers are enumerated as affine regimes, constrained
to their correct energy volumes. Import/export balance and SOC recursion are
vectorized; equal initial/final energy, charging power, discharge power,
efficiencies and SOC limits reuse the existing `Battery` model. Simultaneous
charge/discharge is rejected. Bill-only optimization is default; optional wear
uses charge + discharge throughput and remains separately reported.

Storage has historical perfect foresight. PV-only follows instantaneous
self-consumption and curtails surplus. A forecast-driven/rolling controller,
inter-cycle ratchet optimization and export settlement are not implemented.
No expected operational savings or avoided emissions claim is made.

## Inputs and reproducibility

Reference site: 37.6, -77.5, Henrico County; not a customer address. The load
model is an explicit **synthetic** late-operating commercial profile: weekday
8 kW closed, 30 kW 07:00–19:00, 50 kW 19:00–22:00 with a 90 kW
20:00–21:00 demand; weekend 16 kW 09:00–20:00 and 8 kW otherwise.
This is a stress/illustrative operating case, not a measured grocery/office
dataset or a regional average. No weather-driven HVAC calibration is claimed.
Eleven prior 90 kW peaks and the 90 kW parallel contract are assumptions.

PV uses the existing `WeatherDerivedPV` model: 40 kW DC, 35 kW AC inverter,
25° tilt, 180° azimuth, existing 14% system loss and 96% nominal efficiency.
Battery: 80 kWh, 40 kWh initial/final, SOC 0.2–0.8, 20 kW charge/discharge,
0.95/0.95 efficiencies. Estimated wear $0.03/kWh charge+discharge throughput.
No inverter night tare is assumed for this generic model.

[ERA5 through Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api)
provides hourly reanalysis, **not on-site measured weather**. Radiation means
for the previous hour are shifted to interval starts; hourly means are held
over two 30-minute intervals, with endpoint meteorology approximating that
hour. Native and requested resolution, request/grid coordinates, raw hash,
request parameters and retrieval timestamp are retained. Nulls, gaps, incorrect
units/time standard and mismatched sites reject. NASA POWER returned valid
meteorology but all missing September 2026 irradiance; that attempted source
was rejected and is not used in the delivered case.

```sh
/usr/local/bin/python3 tools/run_pjm_case.py --fetch-weather --data-dir .cache/pjm_candidate
# Reuse the exact saved request and weather bytes (no network):
/usr/local/bin/python3 tools/run_pjm_case.py --request .cache/pjm_candidate/runs/STUDY_ID/request.json --data-dir .cache/pjm_replay
# Explicitly returns unsupported, without neighboring-rate substitution:
/usr/local/bin/python3 tools/run_pjm_case.py --year 2025
```

The saved request contains raw weather bytes; JSON-decoded bytes match their
recorded hash. Source snapshots include Python rate literals. The CLI and
browser use the same queue/worker, save/provenance contract and result routes.
The API saves an unnamed draft, and asks for a name only when results are saved.

## PJM file and permissions contract

[PJM Data Miner](https://www.pjm.com/markets-and-operations/etools/data-miner-2.aspx)
and [historical guide](https://www.pjm.com/-/media/DotCom/etools/data-miner-2/data-miner-2-historic-data-guide.pdf):
five-minute prices archive after 186 days, hourly after roughly two years.
Archived data have restricted filters; downloading all nodes can be very large.
The installed gridstatus adapter handles that with in-memory filtering. This
candidate uses explicit historical imports instead of that unbounded download.
Nonmember API limits are six connections/minute, member limits 600; the current
live adapter has no verified pagination-wide throttler, so annual live API
retrieval is not enabled.

Required CSV fields: `datetime_beginning_utc`, `pnode_id`, `pnode_name`, `zone`,
`total_lmp_rt` or `total_lmp_da`, `version_nbr`, `row_is_current`. Exact official
display aliases such as “Pricing Node ID” and “Latest Version” are supported.
The explicit UTC source column may contain naive UTC values; local-only EPT
timestamps are rejected. Accepts hourly DA/RT or five-minute RT, $/MWh only;
preserves the source grid and converts prices separately to $/kWh. It does not
fabricate half-hour market observations. Requested half-open coverage must
match exactly; revision conflicts and missing latest observations reject.
Metadata includes official source URL, timezone-aware retrieval time, feed,
units, private-use designation, hash and selected revision numbers. The node
ID/name/zone must all match the separate verified pricing-location configuration.

PJM restricts redistribution of Data Miner information and derived data absent
appropriate membership/license. The import accepts **internal use only**.
Raw PJM CSV appears only in private saved inputs and `private-pjm-market.csv`,
never in downloadable result tables or ZIP manifests. No LMP-derived financial
outputs are generated. All schema-8 API submission and saved-study retrieval
are blocked in hosted mode, including request downloads. Public access requires
separate permission review and release validation; current user confirmation is
not represented as a PJM-issued redistribution license.

Open-Meteo data require CC BY 4.0 attribution; the hosted free API is for
noncommercial use. Local research only is enabled. Commercial hosting requires
a suitable service arrangement or a different permitted provider.

## Candidate release and remaining work

Start a **separate** preview, preserving the existing data directory/pointer:

```sh
/usr/local/bin/python3 -m src.local_web.server --port 19012 --data-dir .cache/pjm_candidate_review
```

Open `/pjm.html` or the capability-gated PJM link on the existing homepage.
Old pinned engines do not advertise the candidate; no automatic upgrade occurs.
Both browser and modern desktop wrapper use the shared local service; a desktop
process pinned to an older engine remains unchanged. Adoption must follow
`Local_Web_Application.md`: validate the exact candidate, stop the target,
explicitly adopt the tested immutable pin, preserve prior results/snapshots and
rerun saved-study acceptance. No promotion, commit, push or deployment occurred.

Outstanding before the requested full historical-year case: verify all 2025
base/rider transitions and bill-proration rules across those transitions;
obtain actual explicitly selected DOM LMP observations; add linked billing
cycles/contract-ratchet updates; validate any new nonconvex load-factor regimes.
Historical import fixtures prove parsing and coverage, not availability or
authenticity of a year of real market prices. Export/NEM, retail access,
capacity/transmission PLC accounting, data-center tariffs, broader local taxes,
actual facility calibration and operational forecasting remain unsupported.

## Validation and review handoff

Reviewed on `main`, HEAD `db1914383fe607f484d69e053a9b8db2ab42ba75`.
The pre-existing San Diego working changes were preserved. Nothing was staged,
committed, pushed or deployed; the independent browser clone was not modified.

- Baseline before PJM changes: `/usr/local/bin/python3 -m pytest -q`,
  **1,534 passed, 1 skipped**. Final full regression: **1,581 passed, 1 skipped**.
- After the final UTC table correction, the 47 Dominion/PJM-specific tests
  passed again. They cover independent tariff arithmetic, rider load-factor
  branches, partial confirmed cycles, effective-date rejection, demand windows,
  contract/eligibility checks, full-year synthetic UTC/DST market fixtures,
  missing/revised observations, weather coverage/units, form-to-worker flow
  and hosted submission/private-input download rejection.
- `node --check` passed for both `app.js` and `pjm.js`; `git diff --check`
  passed. Actual browser form submission, historical-weather retrieval and
  queued worker completion were verified. The final result tables were viewed
  in the browser, including their default scenario comparison.
- Candidate pin:
  `c0ae24eb12adf60be1313ab8dbdaeee3570fdb0aac534fe40f7e4b2c946cdfe7`.
  Final saved study: `7a29d2dde39a40a0afafdaa4585084c3`, named
  “Dominion GS-2T · September 2026 reference”, in
  `.cache/pjm_candidate_review/runs/`. Source timestamps in downloaded tables
  are UTC; retail billing and solar geometry use Eastern time.
  It was named through the existing save-after-results dialog and has no
  temporary-result expiration. Its original request bytes are preserved.
- Stable preview at port 19011 retained pin
  `fcb9727e72b019722897c24e0f40164c75087bdb51ec6400ea33e6112b053eae`.
  The candidate remains separate at port 19012, with Web UI v1.0.1 retained.

The exact saved request includes the historical weather response, so replay
does not require another weather download. Final CLI offline replay in
`.cache/pjm_offline_final/`, study `a3c78adfefe448d5a3686125987e4f85`, used the
same candidate pin and produced identical comparison, itemized bill, input and
weather tables. The documented reference case has
15,924 kWh of synthetic native demand. Its bills are:

| Scenario | Utility bill | Savings vs. grid | Estimated battery wear, separate |
|---|---:|---:|---:|
| Grid only | $3,008.46 | $0.00 | $0.00 |
| PV only | $2,635.84 | $372.62 | $0.00 |
| PV plus battery | $2,393.26 | $615.20 | $63.44 |

PV alone does not reduce the 90 kW evening on-peak maximum. Storage reduces it
to 70 kW; the 90 kW distribution contract remains unchanged. The tariff bill
and storage objective differ by less than $0.00003. All 1,440 intervals in
each of the three scenarios pass the representative OpenDSS checks. This is
steady-state replay of an assumed circuit, not a verified customer feeder.
The final request contains no PJM file; no wholesale signal is invented.

Generated weather, request/result files, snapshots, logs and browser screenshot
remain under ignored `.cache/` directories. Filed source text, URL/effective-date
metadata and original PDF hashes are retained under
`docs/utility_sources/dominion/`. The PDF binaries are not added to Git.
