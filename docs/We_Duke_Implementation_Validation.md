# We Energies Wisconsin and Duke Indiana candidate validation

This records the initial bounded candidate below. The subsequent
[2025 history review](We_Duke_2025_History.md) retains its results under their
original pin and documents the remaining source gaps and later cycle changes.

Candidate reviewed October 24, 2026. No stable-engine promotion, deployment,
staging, commit or push is part of this work. The native desktop GUI remains
paused and its opt-in test modules are excluded.

Frozen engine:
`25aa80f26e58e4ba0fe623a2ad3ac5a0ae9ca99db434947377fd8cfa65228545`.
Source, frontend, tests, tools and configuration fingerprints are retained in
`.cache/we_duke_candidate_frozen.json` and each validation launcher report.
An earlier focused run had four test-expectation failures: the validation
request builder rejects an unsupported annual period immediately, rather than
returning a request for a later rejection. The test boundary was corrected;
billing or dispatch code was not changed by that correction. Its superseded
report remains attributed to its original test fingerprint.

## Executable scope

| Utility | Residential | Commercial | Verified complete calendar cycles |
| --- | --- | --- | --- |
| Wisconsin Electric / We Energies, Wisconsin | Rg1, Rg2 TOU | Cg1, Cg6 TOU | Jan–Jun 2025; Jan–Sep 2026 |
| Duke Energy Indiana | RS, RS-TOU | CS, CS-TOU | March 2025 |

All eight selected plans are non-demand tariffs. Larger commercial demand
tariffs are separate future implementations. The two utilities have different
TOU holiday calendars and clock rules: We uses prevailing Central time; Duke's
filed TOU windows use Eastern standard time and shift on daylight clocks.

The Wisconsin July–December 2025 ECC gap and Duke's remaining historical
base/rider versions prevent full-year 2025 claims. Rates outside the declared
intersection reject. Partial and shifted cycles also reject. Neither utility
has export compensation enabled in these cases. See the dated official sources
and account limits in [Wisconsin](We_Energies_Wisconsin.md) and
[Indiana](Duke_Indiana.md).

## Reproducible historical inputs and method

The prepared source files under `.cache/we_duke_weather` contain actual-year
Open-Meteo ERA5 reanalysis for the explicitly hypothetical sites:

- Wisconsin: 43.05 N, 88.25 W; unincorporated Waukesha County, Central time.
- Indiana: 39.70 N, 86.40 W; Plainfield/Hendricks County, Indiana Eastern time.

The raw source bytes, UTC timestamps, retrieval metadata and hashes are retained.
Hourly previous-hour radiation means are aligned to their service intervals
and held over four 15-minute intervals; this does not create measured
15-minute weather. There is no weather-year substitution or silent provider
fallback. No wholesale LMP is added to bundled retail charges and no CAISO
carbon signal is substituted for MISO locations.

Native demand is a deterministic generic household or office archetype,
serialized and imported through the existing CSV contract. It is synthetic,
not measured, weather-calibrated, a regional average, or a next-day forecast.
Every plan and equipment comparison for a given class uses the same native
load and available PV inputs.

| Parameter | Residential | Small commercial |
| --- | ---: | ---: |
| Synthetic native peak | 3 kW | 10 kW |
| PV DC / inverter AC | 5 / 4 kW | 10 / 8 kW |
| PV tilt / azimuth | 30 / 180 degrees | 30 / 180 degrees |
| PV system loss / inverter efficiency | 14% / 96% | 14% / 96% |
| Battery capacity / power | 10 kWh / 3 kW | 30 kWh / 8 kW |
| Initial SOC / operating bounds | 50% / 20–80% | 50% / 20–80% |
| Charge / discharge efficiency | 95% / 95% | 95% / 95% |

Grid-only, PV-only and PV-plus-battery are independently calculated. Dispatch
uses historical perfect foresight within each billing cycle and continuously
propagates SOC across cycles, with the final energy target equal to initial
energy. This is rolling optimization, not a jointly optimized annual minimum
or an implementable forecast strategy. Battery wear is reported at
$0.03/kWh throughput but excluded from the selected utility-bill objective.
Capital costs, production incentives and export credits are excluded.

## Historical matrices and independent checks

The three launcher outputs are:

| Run | Four-plan study period | Scenario results | Itemized monthly bills |
| --- | --- | ---: | ---: |
| `.cache/we_2025_matrix` | We Jan–Jun 2025 | 12 | 72 |
| `.cache/we_2026_matrix` | We Jan–Sep 2026 | 12 | 108 |
| `.cache/duke_march2025_matrix` | Duke March 2025 | 12 | 12 |

All twelve studies and their independent artifact audits passed: 36 scenario
results, 192 monthly bills and 558,576 converged, feasible OpenDSS interval
checks. All twelve storage scenario runs proved their per-cycle cost optima
and minimum-cycling refinements; this does not establish an annual optimum.
Illustrative utility bills below cover the stated periods, not a full
year, and do not establish average customer costs:

| Period | Plan | Grid only | PV only | PV + battery |
| --- | --- | ---: | ---: | ---: |
| We Jan–Jun 2025 | Rg1 | $1,396.85 | $977.00 | $821.95 |
| We Jan–Jun 2025 | Rg2 | $1,303.10 | $846.71 | $634.34 |
| We Jan–Jun 2025 | Cg1 | $3,626.34 | $2,452.17 | $2,334.77 |
| We Jan–Jun 2025 | Cg6 | $4,143.24 | $2,660.92 | $2,253.30 |
| We Jan–Sep 2026 | Rg1 | $2,258.91 | $1,561.39 | $1,310.64 |
| We Jan–Sep 2026 | Rg2 | $2,116.95 | $1,329.08 | $966.74 |
| We Jan–Sep 2026 | Cg1 | $5,837.97 | $3,923.16 | $3,753.97 |
| We Jan–Sep 2026 | Cg6 | $7,098.24 | $4,483.08 | $3,740.31 |
| Duke March 2025 | RS | $191.05 | $142.25 | $125.83 |
| Duke March 2025 | RS-TOU | $204.17 | $147.96 | $106.25 |
| Duke March 2025 | CS | $517.10 | $370.88 | $358.28 |
| Duke March 2025 | CS-TOU | $511.03 | $342.07 | $301.94 |

Each uses `/usr/local/bin/python3 tools/validate.py --tier focused` with the
utility's tests, `--regional`, explicit utility/period bounds and the prepared
input directory. The exact command and immutable candidate fingerprints are
retained in each `report.json`; requests, input/source hashes, bills, dispatch,
electrical interval tables, CSV/ZIP checks and the independent audit are in its
`regional/` directory. No live retrieval occurs during matrix execution.

The Wisconsin published 29-day sample-bill components reconcile to $148.53.
The sample's shifted meter cycle is a component benchmark, not an enabled
shifted-cycle simulation. Independent Duke flat-1-kW March benchmarks are
$133.18 RS, $125.58 RS-TOU, $145.09 CS and $123.66 CS-TOU. Their 743 elapsed
hours include the DST transition. Actual synthetic study loads differ from
that flat benchmark. Independent literal-rate audits of the saved dispatch
verify the itemized bills, including each rider exactly once and the proper
tax/fee base.

## Electrical interpretation

Every returned scenario is replayed at each 15-minute interval. Curtailment,
actual PV output, absent equipment and interval-start/end SOC are preserved.
Scheduled flows determine the bill; PCC measurements and network losses
remain separate diagnostics.

The residential reference uses a 25 kVA, 100 A, 240 V split-phase service. Duke's
single-phase commercial reference uses 75 kVA and 400 A. The default Wisconsin
three-phase commercial matrix retains the existing balanced 750 kVA, 480 V
reference; a 10 kW office lightly loads that network, so these results do not
establish feasibility for a smaller actual service. A separately audited July
2026 Cg6 API study explicitly selects the supported 75 kVA, 400 A, 240 V
single-phase alternative; its three scenarios are also feasible.

Voltage, ratings, impedances and constant 0.95 lagging replay load power factor
are representative assumptions. The billing account's fixed PF placeholder
does not supply a measured electrical power factor or impose a PF charge on
these selected tariffs. No site wiring, protection, dynamic or transient
validation is claimed; these checks do not constrain dispatch.

## Regression and browser acceptance

Full regression passed **3,880 tests, with 1 skip and 16 warnings**, plus all
seven JavaScript syntax checks. The paused GUI modules were excluded. Evidence
is retained in `.cache/we_duke_release/report.json`. Source, frontend, test,
tool and configuration fingerprints still match the frozen candidate.

One concise Chrome acceptance pass followed the completed regression and
historical matrices. It verified:

- Both providers' account controls, supported dates, sources and separate
  retail/MISO identities.
- Rendered bills and OpenDSS summaries for all three scenarios in the We Rg2
  residential and Duke CS-TOU commercial examples.
- Naming a completed result only on Save, saved-history reopening and settings
  restoration through every setup step.
- Browser submission of the restored We study. Every parameter except its
  temporary name matched the original, and the resulting itemized bills were
  identical. Its saved artifacts passed the same independent audit.
- Switching from PSE&G RS to Duke RS updates both plan labels, despite the
  shared plan identifier.

The acceptance tool calls totaled **10.998 seconds**, with no stalls and no
blocked assertions. This is measured browser-tool elapsed time, not the whole
development session. The full pytest phase took 663.64 seconds; historical
matrix phases took 90.35 seconds (We2025), 122.73 seconds (We2026) and 36.18
seconds (Duke March). These jobs overlapped; their durations must not be summed
as active development time.

Browser studies use a separate store under `.cache/we_duke_browser`, with
API-seeded prepared weather and independently audited artifacts. The served
bytes of all eleven frontend files matched the freeze; all three prepared
ZIPs passed CRC and membership checks. Download endpoints and saved bytes were
checked through the API; browser download events and file choosers were not used.
Evidence is in `.cache/we_duke_browser_preflight.json`,
`.cache/we_duke_browser_rerun_check.json` and
`.cache/we_duke_browser_acceptance.json`. The local preview is
<http://127.0.0.1:19037/#53efe7dbd41d4316b5d67a2d36116e46>.
