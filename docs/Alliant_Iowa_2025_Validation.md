# Alliant Iowa 2025 history and validation

This extends the Iowa Interstate Power & Light candidate using verified
historical component evidence. It preserves the earlier
[2026 candidate receipt](Alliant_Iowa_Implementation_Validation.md) under its
original engine pin. The [current billing scope](Alliant_Iowa.md) and
[source ledger](utility_sources/alliant_ia/sources.json) describe eligibility
and the two separate supported date windows.

## Historical reconstruction

The five schedules are residential 400, 407 and 427, and ordinary small
commercial 600 and 607. The October 2024 base schedules continue through 2025.
The earlier year is reconstructed from actual component histories, rather
than applying a 2026 composite backward:

| Component | Verified 2025 treatment |
| --- | --- |
| EAC | Twelve published designated-billing-month composites; identical for the selected residential and GS classes |
| RCE | $0.00006/kWh included inside the published EAC from September; no additional RCE charge |
| TBR | Separate credit through September: residential -$0.00789/kWh, GS -$0.00592/kWh; zero in complete October–December cycles |
| EECR | Before June 17: residential $0.0009/kWh, GS $0.0014/kWh; from June 17: $0.0006/$0.0032 |
| DRCR | Before June 17: residential $0.0031/kWh, GS $0.0023/kWh; from June 17: $0.0048/$0.0028 |
| RTS | January–August: residential $0.04077/kWh, GS $0.03217/kWh; from September 1: $0.04055/$0.03196; the refund is already included |

The June 12 filing footer and June 17 factor-application date are distinct.
The implementation follows the application date. Actual utility bills in
Boone's public meeting packets corroborate the transition and preceding GS
factors, continuously spanning December 2024 through June 2025. An archived
official Alliant RTS webpage supplies its exact 2025 factors and September 1
application date.

Alliant's own early-2025 standard, Summer Saver and Night Owl bill guides
explicitly show the preceding residential factors, including plan 427. This
resolves the older EECR sheet's omission of 427 from its price-code list.
Together with the successor DRCR sheet's explicit cancellation of substitute
sixth revision, these sources support a reconstruction bounded to 2025. The
exact older sixth-revision DRCR PDF was not recovered; its original 2024
application date is not asserted. Uncorroborated private bill templates on
third-party sites are not implementation evidence.

The source ledger preserves original and extracted-text hashes, retrieval
methods, pages and limitations. Earlier indexed-source records remain intact;
newly retrieved binaries do not retroactively change their provenance.
Original PDFs and public-record packets stay in ignored `.cache` storage.
Checked-in extracts omit account numbers and unrelated personal information.

## Allocation and optimization

An actual May 20–June 19 GS bill splits the EECR and DRCR quantities into
27/30 old-factor and 3/30 new-factor shares of **the entire cycle's kWh**.
This is distinct from summing the actual interval kWh consumed on either side
of the effective date. For the supported June 1–30 hypothetical calendar
cycle, both billing and dispatch use:

```text
June rider coefficient = (16 × old factor + 14 × new factor) / 30
Rider charge = total cycle import kWh × June rider coefficient
```

Both numerical bills and the convex optimization expressions use that same
coefficient. Metadata retains each factor's reference, date segment and day
count. Customer charges use calendar days; TOU energy uses actual interval
consumption. EAC remains selected by the explicitly designated billing month.
TBR is not embedded in EAC; a separately recovered September–October bill
also confirms its day-prorated cutoff. Arbitrary shifted or partial cycles
remain outside this addition, so that evidence is not a claim that all such
cycles are now implemented.

Calendar/DST behavior, filed fixed-CST TOD interpretation, actual Independence
Day exclusion and account confirmation are retained. The utility bill is the
dispatch objective; battery wear is reported separately. Exports and export
compensation remain disabled. None of these five schedules has a customer
maximum-demand charge.

## Reproducible study inputs

The requested comparison uses January 1–December 31, 2025 in
`America/Chicago`, at 15-minute resolution, with twelve explicitly hypothetical
calendar meter cycles. Every schedule compares grid only, PV only and PV plus
battery using identical native-load and available-PV inputs within its case.

- Weather: cached historical ERA5 at 42.10 N, 91.46 W, via Open-Meteo.
  Retrieval uses UTC and includes the next day's padding needed to cover the
  final local service intervals. Hourly radiation means are held over the
  quarter-hour grid; these are not measured 15-minute weather observations.
- Load: deterministic synthetic household or small-office native consumption,
  with a 3 kW reference peak, serialized and re-imported through the native
  CSV contract. It is neither measured nor calibrated to average Iowa use.
- PV: 5 kW DC, 4 kW AC inverter, south-facing at 30 degrees, 14% system losses
  and 96% inverter efficiency.
- Battery: 10 kWh, 3 kW charge/discharge limits, 95% charge and discharge
  efficiencies, 20–80% SOC bounds and 50% initial SOC. SOC continues between
  cycles and is restored at the study end.
- Account: confirmed hypothetical ordinary bundled service in unincorporated
  Linn County, one 120/240 V single-phase meter/service, approved IO-eligible
  non-export PV/storage and grid charging. Weather coordinates establish none
  of these eligibility or tax facts.
- Taxes: residential state energy exemption and 1% local tax; ordinary
  commercial 6% state plus 1% local on the declared common taxable base,
  without a municipal franchise fee.

Dispatch has perfect foresight within each cycle and carries SOC forward; it
does not prove a jointly optimized annual minimum or a forecast-based control
strategy. The comparison excludes installation costs and incentives. Each
scenario receives shared OpenDSS quasi-static replay, using the representative
25 kVA/100 A residential split-phase or 75 kVA/400 A small-commercial
single-phase service. This is not a surveyed circuit or transient validation.

Prepared weather is under `.cache/alliant_weather_rural`; its manifest
preserves the retrieval and input hashes. Tests make no live API calls.

```sh
/usr/local/bin/python3 tools/validate.py --tier focused \
  --test test/test_alliant_ia.py \
  --test test/test_alliant_integration.py \
  --test test/test_alliant_2025_history.py

/usr/local/bin/python3 tools/validate.py --tier focused \
  --test test/test_alliant_2025_history.py \
  --regional --utility alliant_energy_iowa --period annual \
  --inputs .cache/alliant_weather_rural \
  --output .cache/alliant_2025_final --timeout 180 --matrix-timeout 1200
```

Use a fresh output directory for a new candidate. Resume is permitted only for
matching frozen source, validation code and prepared inputs. Earlier results
retain their original pins. January–May 2026 is not implicitly filled by this
2025 reconstruction; dates outside verified coverage continue to reject.

## Frozen candidate and results

Validated October 25, 2026 on candidate engine
`22b4523bcf59a5e8769b527fc0f24f1d952d4c75360f56a44d7df50fe2dd2402`.
The source/frontend/test/tool fingerprints are recorded in
`.cache/alliant_2025_candidate_frozen.json`. The stable engine was not promoted.

The following are annual utility bills, summed from twelve itemized cycle
bills. They exclude separately reported battery wear and capital costs.

| Customer class / plan | Grid only | PV only | PV plus battery |
| --- | ---: | ---: | ---: |
| Residential 400 | $2,350.87 | $1,654.53 | $1,395.00 |
| Residential 407 | $2,354.14 | $1,652.42 | $1,363.02 |
| Residential 427 | $2,360.21 | $1,609.19 | $1,264.55 |
| Commercial 600 | $2,479.77 | $1,398.63 | $1,254.64 |
| Commercial 607 | $2,496.49 | $1,400.58 | $1,229.86 |

Annual native use is 13,887.5364 kWh for each residential case and
11,981.7324 kWh for each small-office case. These are the synthetic test
profiles described above, not average customer consumption. Plans within
each class share the same load and available PV. The study is not a tariff
recommendation or an estimate of a particular customer's savings.

All five studies passed the independent saved-artifact audit:

- 15 scenarios, 180 cycle bills and 35,040 consecutive intervals per scenario.
- All 60 storage-cycle primary-cost and minimum-cycling checks proved within
  their saved solver tolerances; no jointly optimized annual minimum claimed.
- Maximum objective-versus-recomputed unrounded bill difference below
  $0.0000011. Itemized statement rounding is kept separate from solver proof.
- 525,600 OpenDSS interval checks, all converged and feasible on the declared
  representative networks. Zero voltage, line or transformer violations,
  setpoint mismatches or inverter capability violations. Across the cases,
  voltage ranged from approximately 0.99510 to 0.99995 pu. Losses and replay
  PCC measurements remain separate from the scheduled flows used for bills.
- Local HTTP retrieval of all five requests and result manifests, 65 CSV
  tables and five ZIP bundles matched the saved bytes; each ZIP manifest
  matched its result. Source and frontend fingerprints remained frozen.

Evidence paths, relative to the development checkout:

| Check | Receipt | Result / phase wall time |
| --- | --- | --- |
| Alliant and shared regional focused suite | `.cache/alliant_2025_focused_final/report.json` | 303 passed; 35.31 s |
| Shared browser/API/worker/electrical workflow suite | `.cache/alliant_2025_workflow_final/report.json` | 112 passed; 141.01 s pytest, plus seven JavaScript syntax checks |
| Prepared historical matrix | `.cache/alliant_2025_final/report.json` | Five cases passed; 189.59 s matrix phase |
| Annual/monthly/component comparisons and physical audit | `.cache/alliant_2025_final/regional/` | `study-comparison.csv`, `monthly-comparison.csv`, `period-components.csv`, `validation.json` |
| API and downloadable-byte audit | `.cache/alliant_2025_api_artifacts_final.json` | Passed; 6.01 s |
| Source hash audit | `.cache/alliant_2025_provenance_audit.json` | 58 extracts and 29 cached originals matched |

The matrix launcher also repeats the ten historical integration tests before
running the matrix; these are included in the 303 focused tests and must not
be counted twice. Test and matrix jobs ran concurrently, so their elapsed
times are not additive development time. No browser automation waits or
live-provider requests occurred during these final checks. GUI tests were
excluded. No new visual browser acceptance was performed for this backend
coverage extension; Node form serialization, HTTP/queued-worker execution,
save/reopen, CSV and ZIP contracts were validated instead.

## Remaining limits

January–May 2026, arbitrary partial/shifted meter cycles, IO export credits,
standalone storage, larger commercial schedules, other tax jurisdictions and
unconfirmed TOD clock or account eligibility remain unsupported. The older
sixth DRCR PDF limitation above remains visible despite the corroborated
2025 factors. These simulations do not substitute for real-bill calibration,
a site survey, a forecast-based controller or annual joint optimization.
