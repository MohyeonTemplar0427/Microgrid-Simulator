# Consumers Energy integration handoff · October 20, 2026

Main started clean at `142e14c`. Changes remain unstaged and uncommitted. No
commit, push, deploy, stable-engine promotion, origin change, browser-clone
copy or desktop-GUI launch/development. README remains untouched.

## Frozen candidate and verification

Engine: `f48b88383403a93b1a7e6ae2d65dcf96146055e9dcb3222df56047632f7df64e`.
`regional.js` SHA-256: `a709f06cb92e32bb33e150ac688f9ec3c5a33cf55c655f306ec160954e9c4e17`.
Web UI v1.0.1 is unchanged. Preview:
[Consumers GSTU · June 2026](http://127.0.0.1:19048/#8447c550112a4d58887f2c617ce77601).
It uses its own `.cache/consumers_browser` data store and an empty credential
file; it does not replace an existing preview or stable pin.

- Existing baseline: current pre-edit fingerprints matched the prior DTE report
  with 1,139 passing regional/validation tests. This was a verified reuse of
  matching baseline evidence, not a newly rerun baseline claim.
- Initial Consumers focused suite: 45 passed, pytest 27.54 s / launcher phase
  29.16 s. That initial candidate preceded removal of irrelevant commercial EE
  fields from residential defaults; it is not relabeled as final evidence.
- Final release: **3,195 passed, 1 skipped**, all seven JS syntax checks passed.
  Pytest output 558.79 s; launcher phase 559.33 s. GUI modules excluded. The
  skip is opt-in Caddy HTTPS; twelve SciPy warnings forward a native HiGHS
  feasibility setting in existing DTE geometry fixtures. No Consumers failure.
  Full fingerprints/log/XML: `.cache/consumers_release_final/`.
- Final matrix: **8 studies, 24 scenarios, 628,944 electrical intervals**; zero
  failed/unevaluated intervals. All 216 cycle outcomes were direct bills or
  proven cost optima; minimum cycling proven for **72/72 battery cycles**.
  Maximum bill/objective difference approximately $0.000001.
- One browser pass: Consumers/MISO/LRZ7/METC identity, GSTU/GS choices, actual
  coverage and sources, assigned EE tier and its provenance, restored exact
  dates/PV/inverter/ERA5/storage settings, submission, three rendered results,
  three electrical summary rows, name-on-save and saved-history reopen. API
  verified the browser request exactly matched the seed before naming and
  reproduced identical bills. Both seed and final ZIPs had 14 entries; endpoint
  bytes were checked outside the browser. **Browser stalls: 0**. Screenshot and
  receipt: `.cache/consumers-browser-results.png`,
  `.cache/consumers_browser_acceptance.json`.
- Final source/frontend/tests/tool fingerprints matched the release report.
  `git diff --check` passed. Documentation-only edits followed source freeze.

A preliminary full regression/matrix were deliberately interrupted after about
one minute to remove commercial-only EE inputs from residential setup. Their
old-pin artifacts remain separate in `.cache/consumers_release` and
`.cache/consumers_validation`; they are not final acceptance evidence. The final
source stayed frozen throughout the complete validation and browser pass.

## Historical outcomes and assumptions

| Plan | Period | Grid only | PV only | PV + battery |
|---|---|---:|---:|---:|
| RSP | 2025 | $1,984.22 | $1,294.22 | $945.08 |
| RSH | 2025 | $1,984.44 | $1,291.36 | $939.36 |
| GS | 2025 | $16,314.53 | $13,776.47 | $13,735.88 |
| GSTU | 2025 | $16,589.30 | $13,996.48 | $13,873.72 |
| RSP | Jan–Jun 2026 | $1,018.82 | $658.89 | $484.42 |
| RSH | Jan–Jun 2026 | $1,019.15 | $656.41 | $480.50 |
| GS | Jan–Jun 2026 | $8,233.61 | $6,928.90 | $6,902.81 |
| GSTU | Jan–Jun 2026 | $8,383.23 | $7,050.66 | $7,003.32 |

These are recurring utility bills under explicit hypothetical accounts,
**synthetic native loads** and exact-year **historical ERA5 reanalysis** near
Grand Rapids (42.96, -85.67). No actual customer statement calibration is
claimed. Residential: 2-kW peak household shape, 9,258.36 kWh in 2025; 5-kW DC /
4-kW AC PV, 10-kWh battery, 3-kW charge/discharge, initial/final 5 kWh.
Commercial: 20-kW peak office shape, 79,878.22 kWh in 2025; 10-kW DC / 8-kW AC PV,
30-kWh battery, 8-kW power, initial/final 15 kWh. January–June 2026 native totals
are 4,591.10 residential and 39,537.54 commercial kWh. Commercial EE tier 3 is an
explicitly assigned hypothetical account fact, held across scenarios/years;
the optimizer does not reclassify it from current consumption.

Both have south-facing 30-degree PV, 14% system loss and 96% PV inverter
conversion. Full ESS efficiencies/SOC bounds and all assumptions are retained
in each saved request. Wear is excluded from the objective by default and
reported separately. No exports, installation costs, MISO carbon or wholesale
price signal. Historical perfect foresight is per cycle with continuous SOC,
not a proven annual joint optimum or an online controller.

OpenDSS uses the shared representative 25-kVA/100-A split-phase residential and
480-V/750-kVA balanced commercial circuits. They are not Consumers service
standards or surveyed site models. Actual curtailed PV/storage are replayed at
every 15-minute step. PCC measurements/losses stay separate from billing;
there are no network constraints in optimization or transient validation.

## Source and reproduction evidence

See [Consumers supported scope](Consumers_Energy.md) and
[source manifest](utility_sources/consumers/manifest.json) for dated MPSC current
and canceled sheets, hashes, PDF-page references and explicit calendar/rider
clocks. Full source PDFs and prepared inputs remain in ignored cache.

- 2025 weather: `.cache/consumers_historical_inputs/consumers_energy/era5.json`,
  SHA-256 `18df5a7358a1705b786e581da9b168c56a25d708a92121f1728e2861dd4d5a9f`.
- 2026 weather: `.cache/consumers_historical_inputs_2026/consumers_energy/era5.json`,
  SHA-256 `36ed76c36ad2d70641d2e5b1ffb0dd958de34e4a3d9974c9d88386fcc007d506`.
- Matrix receipts: `.cache/consumers_validation_final/annual_2025/` and
  `first_half_2026/`, with requests/results, bills, component savings, dispatch,
  weather, PV and electrical CSVs. Aggregate: `acceptance.json`.
- Matrix wall times: 159.96 s (four full-year studies), 83.15 s (four half-year
  studies). Matrix and release overlapped; these are not additive active-work
  or CPU times. Browser seed/rerun worker times were 4.95/4.97 s. No time was
  lost to stalled browser operations.

Reproduction commands are in Consumers_Energy.md. Use a new output folder;
resume only matching immutable engine/input/validator evidence. Do not shift
weather years, replace actual PSCR with ceilings, or copy files into the browser
clone. Coordinate any later sync through Git when authorized.

## Deliberate remaining boundaries

- Actual PSCR coverage ends June 2026 in the downloaded regulator snapshot.
  July onward needs additional dated actual factors and matching updated riders;
  current or maximum rates are not borrowed. This is not full-year 2026 support.
- Complete 26–35-day regular cycles with confirmed full monthly charges only;
  partial/initial/final proration is unsupported. Real normal cycles spanning
  calendar/rate boundaries are tested, including distinct bill-month commercial
  seasons versus residential calendar seasons.
- RSP/RSH include weekday holidays; GSTU uses six actual holidays, no Friday or
  Monday substitutes. Never share a calendar merely because both utilities are
  in Michigan or MISO.
- Selected GS/GSTU plans are energy-only, with no measured demand fee. Larger
  GSD demand plans, primary service, SG/standby, optional DR, discounts, retail
  choice, export credits/legacy NEM and standalone storage are unsupported.
- DER requires approved C11.3 DG, historical annual sizing/storage and a
  conservative aggregate nameplate-plus-storage cap of20 kW in this scope.
  Territory, tariff and account eligibility must be confirmed independently of
  map coordinates. No public market-data redistribution or hosting is enabled.
