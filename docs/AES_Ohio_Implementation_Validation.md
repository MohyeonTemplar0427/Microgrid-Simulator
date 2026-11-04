# AES Ohio implementation and validation

Recorded November 2, 2026. This is targeted local-development acceptance for
ordinary single-phase **D17 Residential** and **D19 Secondary**, **G10 SSO** and
**T08 transmission**. Complete matching calendar service/bill cycles execute
in **January–June 2025, June–July 2026, and September–November 2026**. Later
2026 months require prior one-time D43 receipt evidence. Other dates and
unresolved account/low-load states reject; no full-year 2025 claim is made.

The [utility guide](AES_Ohio.md) contains account, date, demand, minimum,
low-load, tax, refund and DER rules. The
[source manifest](utility_sources/aes_ohio/sources.json) pins 41 retained
evidence files. Delivery/supply/rules reviews recomputed 44/21/28 source-record
hashes respectively; some records reuse the same original. Original PDFs,
macro-free utility calculators, page images and retrieval/blocker receipts
remain private in `../.cache/aes_ohio/sources/`.

## Candidate, preserved work and impact

Work began on `main` at `62d3ed9037bd43e128ed536ab645409b312fd209`, with the
uncommitted Toledo Edison implementation present. Its 62 modified/untracked
files were copied with hashes to private `initial_changes/` evidence before
edits. Fifty-one remain byte-for-byte identical; eleven shared files received
the explicitly scoped AES extension. Earlier utility source ledgers and
validation reports retain their original identity.

Successful acceptance uses engine
`85b64d196abddadd471e628bcaa84b04acddc7e4c86d20e22c6bbf5b591a865f`.
The [frozen-candidate receipt](../.cache/aes_ohio/candidate_frozen_2.json)
records 248 runtime Python files, 11 unchanged frontend files, tests, tools,
configuration and source-manifest identity. The
[preservation receipt](../.cache/aes_ohio/preservation_2.json) identifies the
shared edits; the [final integrity receipt](../.cache/aes_ohio/final_integrity_2.json)
records final hashes and Git state.

New `src/billing/aes_ohio.py` and `aes_ohio_rates.py` contain the AES-specific
contract and static reviewed rates. Additive registry, counterfactual, default
site, validator selection/scope and coverage entries connect existing browser,
worker and artifact components. Shared API schema, worker contract, billing
math, solver, time grid, PV/storage physics and electrical replay are unchanged.
Desktop GUI compatibility is excluded; no GUI was launched.

## Source and account limits

G10 service-rendered pricing is distinct from T08/rider bills-rendered pricing.
The original **G10 revision 26 PDF remains missing**. Executable June 2025
pricing is independently corroborated by preserved dated official calculators
and reproduced cached adopted tariff text. Results retain the exact source
grade `official_calculator_and_cached_official_adopted_tariff_text`, separate
from original-PDF evidence. No missing rate or eligibility is inferred.

D19 uses the actual 30-minute integrated maximum and a 75% seasonal ratchet
over eleven prior actual monthly maxima. No off-peak election, NSPL opt-in,
legacy TCRR opt-out, 85%-connected-load determination or agreement minimum is
modeled. All billing kW are priced, without an invented first-five exemption
or demand floor. The base minimum is the customer charge. The sample account
has eleven explicit hypothetical 40 kW actual peaks; each scenario then carries
its own actual peaks, not ratchet-inflated billing demand.

Coupled D19/T08 low-load selection uses filed unrounded amounts; percentage
riders use customer plus selected D19 variable charges. A $0.02 comparator
band with differing distribution allocations is explicitly unsupported. The
symbolic selector is an outer model there; an independently physical,
numerically replayed candidate must attain its proven lower bound for a cost
proof. A solution trapped inside the excluded band fails acceptance.

D33 uses statutory local measurement-day import-kWh bands and no CAT
gross-up. The official calculator's fixed tax bands for 25–35-day cycles,
intermediate-cent low-load selection and unsupported September 2025 precision
differ from filed/statutory arithmetic and remain documented. Exact printed
invoice rounding and rounded-cash optimality are not claimed.

August 2026 is blocked. September onward requires confirmed exact prior D43
receipt ($14.39 D17 / $49.27 D19), date and source before service. The model
does not infer an ending date or repeat the one-time refund. The example's
August 31 receipt is hypothetical. Approved exact PV/paired storage, active
PTO/metering and ordinary-service continuation without D10 auxiliary capacity
charges are independent account facts. PV-only charging and non-export are
conservative study restrictions, not universal AES approval requirements.

## Focused checks and recorded development failure

The [successful launcher report](../.cache/aes_ohio/acceptance_2/report.json)
records **399 passed, zero failed, zero errors, zero skipped**. This is
focused-tier targeted acceptance, not workflow/release acceptance.

```text
/usr/local/bin/python3 tools/validate.py --tier focused
  --test test/test_aes_ohio.py --test test/test_aes_benchmarks.py
  --test test/test_aes_integration.py --test test/test_pjm_population_coverage.py
  --test test/test_regional_counterfactual.py --test test/test_regional_coverage.py
  --test test/test_regional_validation_driver.py
  --test test/test_regional_weather_timezones.py
  --test test/test_validation_launcher.py
  --regional --utility aes_ohio --period custom
  --start-date 2025-03-01 --end-date 2025-06-30
  --inputs .cache/aes_ohio/weather --output .cache/aes_ohio/acceptance_2
```

The wrapped command is descriptive; the report preserves exact argv.
The 131 independent literal benchmarks cover all eleven source months,
numeric and symbolic itemization, tax thresholds, zero/minimum bills, demand,
history, both low-load branches, boundary rejection, calculator examples and
D43 receipt. Expected rates do not import production tables/math. Other
checks cover source hashes/grades, adjacent rate gaps, DST, missing/duplicate/
unordered inputs, eligibility, unsupported options and export/standalone
storage rejection. Four queued-worker cases cover both plans in June 2025
and November 2026, form serialization, restored settings and CSV/ZIP artifacts.

An earlier 231-check unit/benchmark run passed. The first integration selection
then failed twelve AES tests because the validation request builder overwrote
PV-only charging with grid charging; the adapter correctly rejected those
requests. No historical matrix ran on that attempt. The builder's AES entry
was corrected, a fresh tool fingerprint/candidate receipt and output directory
were created, and the entire selected 399-check suite passed. Runtime source
and engine ID were unchanged by that tooling correction. Original reports are
retained, not relabeled or overwritten.

Unchanged regional JavaScript syntax and final whitespace checks passed. GUI,
full workflow/release and unaffected historical matrices are excluded under
the additive-utility impact policy; no shared behavior/contract changed.

## Historical matrix and independent re-audit

One selected matrix on the finished candidate covers **March 1–June 30, 2025**:
**two fresh studies, six scenarios, 24 cycle bills and 70,248 OpenDSS interval
checks**, with zero electrical failures. Every interval in each selected case
was checked. March includes spring DST; April changes quarterly riders; June
changes generation, transmission and storm charges. Unit/benchmark checks cover
other supported rate regimes. There is no full-year or every-supported-month
weather/electrical acceptance claim.

| Plan | Study ID | Grid-only | PV-only | PV + battery | Electrical intervals across three scenarios |
| --- | --- | ---: | ---: | ---: | ---: |
| D17 | `7e3e31156ad948e588f7276874524ffe` | $728.08 | $500.13 | $421.63 | 35,124 |
| D19 | `6708b421d4a94e4cb8f90472a7a2c9e1` | $3,793.54 | $3,302.26 | $3,294.27 | 35,124 |

All sixteen optimized primary cycle proofs and eight battery secondary
minimum-cycling proofs passed, with zero strict fallbacks. Eight grid-only
cycle bills are direct calculations, without optimizer claims. Maximum primary
gap and reconciliation difference are approximately `1.00000148e-6 USD`.
Rolling-cycle perfect foresight preserves SOC/history but does not establish
a jointly optimized annual bill.

Actual 2025 ERA5 hourly reanalysis for the exact hypothetical coordinates came
through Open-Meteo, with grid coordinates, raw hashes, sampling, timestamps and
attribution retained. Prepared-input SHA-256 is
`efbc2f4fd59db0cc24eec7fe3c7f874922f7a230ea31b5d03eb4e649449d16cf`.
Hourly radiation means are held over four intervals. Native loads are generic
deterministic synthetic archetypes, serialized as imported intervals, not
measured or regionally calibrated customer loads. Account/site facts are
hypothetical; representative electrical feasibility is not surveyed-site,
protection, transient or dynamic validation.

The [matrix summary](../.cache/aes_ohio/acceptance_2/regional/validation-summary.json)
retains original artifacts/proof labels. A separate
[literal Decimal auditor](../.cache/aes_ohio/independent_audit.py), without
production billing imports, reconciled all 24 bills, actual-demand history,
SOC/flows and saved electrical completeness/flags. Its
[receipt](../.cache/aes_ohio/independent_audit_2.json) records maximum raw
component error `1.1368683772161603e-13 USD` and zero half-cent exceptions.
This is an artifact re-audit, not another optimizer/OpenDSS execution or an
independent electrical simulation.

## Browser and API acceptance

One concise pass used [the private preview](http://127.0.0.1:59172/) after
backend acceptance. Both saved November 2026 seed results rendered: D17 bills
$236.40 / $170.99 / $137.56 and D19 $1,195.15 / $1,055.38 / $1,054.45 for
grid / PV / PV-plus-battery. D19 settings restored through step eight,
including the actual-peak history, 30-minute demand, prior D43 receipt,
hypothetical cycle list, provider/supplier/jurisdiction/DAY separation,
non-export PV-only charging, storage and bill-only objective.

**Browser acceptance remains partial.** The final wizard transition attempted
an exact `Next` button selector that had no match, and the operation timed out.
The failing route stopped immediately under AGENTS.md: no selector retry,
alternate submission, longer timeout or sleep loop. Final review, visual
native-CSV review, browser submission/new results, UI save/reopen and complete
restore/rerun remain unverified. The
[browser receipt](../.cache/aes_ohio/browser_acceptance_2.json) and
[configuration screenshot](../.cache/aes_ohio/browser_acceptance_2.png) retain
the observed assertions and exact limitation. No new browser study was submitted.
The restored cycle dropdown labels an explicit list as documented; its JSON
kind/source remain explicitly hypothetical and are not actual meter evidence.

The [API audit](../.cache/aes_ohio/api_audit_1.json) passed for four studies
and **52 CSV endpoints**, including metadata, exact saved bytes, ZIP members
and result manifests. Queued-worker save/settings restoration passed in the
integration tests. Neither proves the missing browser actions. Browser upload,
file-chooser and download events were not exercised. Earlier utility browser
evidence retains its own scope and pin.

The two November 2026 seeds add six bills and **17,304** electrical intervals,
separate from the historical matrix. Their
[independent audit](../.cache/aes_ohio/preview_independent_audit_2.json) passed
with zero half-cent exceptions. Weather is modeled clear-sky, not observed
historical 2026 weather or a forecast. Seed worker runtimes were 14.58/14.59 s.

## Timing and cumulative PJM scope

Final pytest phase was 34.79 s and regional phase 36.62 s; the regional driver
session was 32.63 s. D17/D19 workers were 11.90/18.06 s. Those times are nested,
not additive CPU or active development time. The earlier unit run was 2.71 s
and failed integration phase 12.29 s. Browser-tool waits and full-task active
development time are not separately instrumented.

[PJM progress](PJM_Population_Coverage.md) is now **23 utility/state-district
workflows**: Illinois 1, Virginia 1, North Carolina 1, Pennsylvania 7,
New Jersey 4, Maryland 4 and Ohio 5. AES adds 478,741 residential distribution
accounts and about 1.13 million household-proxy people. The cumulative proxy
is **51.96 million / 67 million = 77.56%, about 78%**, versus Toledo's 22
workflows / about 76%. This is territory footprint, not tariff/date/customer,
annual electrical or carbon-data coverage. Source vintage remains EIA 2024
and the existing Census factors; original historical snapshots are retained.

The next recommended addition is **Duke Energy Ohio electric RS residential
and company-qualified DM small secondary SSO**. Official PUCO No. 19 Sheet 43
uses average monthly demand at most 15 kW with history/reclassification rules;
DS is a separate larger-demand extension. Keep Ohio separate from Kentucky
within PJM DEOK and verify dated 2025–2026 components before implementation.
The [private recommendation receipt](../.cache/aes_ohio/next_utility_recommendation.json)
retains primary source hashes and exact schedule/eligibility references.

No staging, commit, push, deployment or stable-engine promotion was performed.
