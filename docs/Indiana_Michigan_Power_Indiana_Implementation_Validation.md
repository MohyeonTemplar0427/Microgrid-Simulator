# I&M Indiana implementation and validation

Recorded November 4, 2026 on `main` at base `6d51e06`, with the
existing Appalachian Power Virginia working-tree changes preserved. The
[utility guide](Indiana_Michigan_Power_Indiana.md) defines the account,
date, tax and non-export scope. The
[source ledger](utility_sources/im_in/sources.json) records filed sheets,
superseded rates, official orders, document hashes and coverage gaps.

## Bill benchmarks

The IURC's July 1 residential surveys publish these pre-sales-tax
amounts. The implementation reproduces them from the filed base rates and
eight tracker factors for both RS codes.

| Survey | 500 kWh | 1,000 kWh | 1,500 kWh | 2,000 kWh |
| --- | ---: | ---: | ---: | ---: |
| July 2025 | $91.11 | $166.56 | $239.36 | $312.16 |
| July 2026 | $89.02 | $162.37 | $233.09 | $303.80 |

The comparison also matches the surveyed trackers to the nearest cent
at 1,000 kWh. The actual ordinary taxable study adds Indiana's 7% sales
tax on the fixed and net variable charges. The IURC survey aggregates
unrounded charges before rounding the bill to cents. The engine rounds
each component for display and also stores the underlying unrounded
amounts. This can cause small differences from the survey display.

The secondary GS benchmark independently transcribes the filed
non-opt-out, low-energy rates, charge bases and tax for all eight
supported rate stacks. No customer GS invoice was supplied. The fixed
charge at zero use, the RS 900 kWh breakpoint, and the separate GS
4,500 kWh study and metering boundaries have dedicated checks. The
utility's written approval preserving ordinary non-export service is
an account input. Validation uses explicit hypothetical approvals.

## Targeted acceptance

Engine `7c3a1d369cd1eed2549f71ea5e952af3d42e899b18b66a933de05e97c85d3778`
with the system interpreter is pinned in the
[candidate receipt](../.cache/im_in/candidate_frozen.json). The initial
virtual environment preflight used the same source bytes with a different
SCS dependency. Its separate receipt records that identity. The final
launcher, matrix, queued-worker artifacts and browser preview used the
system interpreter and share the engine ID above.

The [launcher receipt](../.cache/im_in/acceptance/report.json) records
**200 passed** with zero failures or skips. It covers the I&M billing and
integration tests, counterfactual behavior, coverage reporting, matrix
driver, weather clock and launcher contract. The I&M checks include
independent Decimal rates, numeric/symbolic parity, unsupported dates and
accounts, non-export approval, DST, missing/duplicate intervals,
browser-form serialization, queued-worker bills, saved settings and
CSV/ZIP byte reconciliation. No shared solver, physics, worker API or
frontend code changed. The full release tier and desktop GUI tests
were outside the selected scope.

One utility matrix used representative RS 015 and GS 218, with all
four individual codes also checked by the billing and form tests.
The matrix uses grid-only, PV-only and PV-plus-battery cases. Each
row below checks every OpenDSS interval in the selected scenarios.

| Cycles | Weather | Scenario bills | OpenDSS intervals |
| --- | --- | ---: | ---: |
| June–August 2025 | Fort Wayne ERA5 | 18 | 52,992 |
| November 2025 | Fort Wayne ERA5 | 6 | 17,304 |
| March–April 2026 | Fort Wayne ERA5 | 12 | 35,112 |
| July 2026 | Fort Wayne ERA5 | 6 | 17,856 |
| November 2026 queued-worker cases | Modeled clear sky | 6 | 17,304 |
| Total | | 48 | 140,568 |

The exact-site, exact-year ERA5 inputs and their hashes are in the
candidate receipt. The selected periods exercise all eight rate
stacks and both DST transitions. Separate driver runs handle the
disjoint historical windows. There is no complete verified 2025 or
2026 annual window. Native load is synthetic and the circuits are
representative. November 2026 is modeled clear-sky evidence.
The historical receipts record [June–August 2025](../.cache/im_in/acceptance/regional/validation-summary.json),
[November 2025](../.cache/im_in/nov25/validation-summary.json),
[March–April 2026](../.cache/im_in/spring26/validation-summary.json)
and [July 2026](../.cache/im_in/jul26/validation-summary.json).

The [independent saved-artifact rebill](../.cache/im_in/independent_rebill.json)
reconstructed all 48 itemized bills from dispatched meter imports,
converted from UTC to Indianapolis time before grouping. The largest
raw component difference was $0.00000000000005 and the largest
optimization-to-rebill difference was about $0.000001. Primary
bill-cost and secondary battery-cycling proofs passed throughout the
selected studies. The driver also audited SOC, state and physical
replay. The [coverage report](../.cache/im_in/coverage.md) preserves
evidence separately from tariff availability.

The launcher reported 20.75 s for its focused tests and 26.60 s for
its historical phase. The three separate matrix sessions took 10.78,
17.05 and 11.88 s. Some runs overlapped.

## Browser acceptance

The local preview connected and displayed the pinned engine ID.
The first form selector for site type timed out after approximately
2.6 seconds. The browser route stopped at that operation. Utility
selection, configuration, submission, result rendering, save/reopen
and restore/rerun remain unverified in the UI. The queued-worker
and saved-artifact checks above provide separate evidence for their
respective contracts. No upload or download-event automation was used.
