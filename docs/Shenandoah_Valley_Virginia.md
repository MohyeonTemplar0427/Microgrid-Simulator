# Shenandoah Valley Electric Cooperative — Virginia

Current residential A-15 and general-service B-16 are visible, unavailable
plans. No complete 2025–2026 dated whole-bill intersection was established.
Published bases and PCA history remain source observations. Confirmed and
hypothetical accounts both reject billing and dispatch.

## Verified components and chronology

The [official rates page](https://www.svec.coop/your-account/rates/) publishes
current schedules, seasonal billing-month rules and twelve monthly PCA factors.
The SCC's [accepted May 2026 schedules](https://www.scc.virginia.gov/docketsearch/DOCS/8c5q01%21.PDF)
and [approved tariffs/workpapers](https://www.scc.virginia.gov/docketsearch/DOCS/8bzn01%21.PDF)
independently corroborate current A-15/B-16. Both apply to bills rendered on or
after May 1, 2026; the acceptance stamp is May 12.

| Component | A-15 residential | B-16 general service |
| --- | --- | --- |
| Single-phase consumer charge | $30/month | $30/month |
| Distribution energy | $0.03323/kWh | First 500 kWh: $0.02611; next 3,700: $0.00239; above 4,200: $0.00091 |
| Fifteen-minute demand | No demand price line | First 20 kW: $4.79/kW; above 20: $8.89/kW |
| Reactive demand, if measured/billed | No RKVA price line | $0.59/RKVA |
| June–September supply | First 800 kWh: $0.06380; above 800: $0.09024 | $0.06979/kWh |
| October–May supply | $0.06380/kWh | $0.06066/kWh |

A is permanent single-family residential/farm service, excluding construction.
B is secondary general/non-residential service; qualifying dedicated large-load
accounts must use LPD-2 or its successor. B's distribution minimum involves the
basic charge, half the preceding calendar year's highest monthly demand or half
requested capacity, and any contract minimum. Actual demand, RKVA billing,
contract terms and retained classification must be established independently of
modeled or PV-reduced imports. Multi-phase, primary-voltage and special-service
conditions are outside the contemplated ordinary single-phase study scope.

The recovered [B-15 predecessor](https://www.svec.coop/wp-content/uploads/General-Service-Schedule-B-15.pdf)
is effective January 1, 2026, with different distribution rates. It is preserved
as historical evidence without executable coverage. The exact prior A-14 sheet
was not recovered; an approximate increase notice is insufficient to reconstruct
its rates.

| Published PCA billing months | Dollars/kWh |
| --- | --- |
| December 2025 | $0.02818 |
| January–April 2026 | $0.02299 |
| May–November 2026 | $0.03411 |

Earlier 2025 and December 2026 factors remain unverified. These dates are not
extended from adjacent months. SVEC's retail supply and its Old Dominion
Electric Cooperative wholesale partner remain separate from PJM metadata and
wholesale pricing; no IOU supply tariff is substituted.

## Missing surcharge and tax intersections

[STS-12](https://www.svec.coop/wp-content/uploads/VA-Sales-and-Use-Surcharge-2026.pdf)
states a $1.25 debit per account per month effective January 5, 2026, and
expressly names A-14 and B-14 among its schedules. It does not expressly name
A-15, B-15 or B-16 or include a successor clause. The current website still
repeats those older suffixes. The recovered current base filings, generic bill
explanation and A-X/B-X classification terms do not resolve that discrepancy.
The 2025 STS original was also not recovered. Neither zero surcharge nor
automatic successor applicability is assumed.

[Virginia Code 58.1-2900(A)(6)](https://law.lis.virginia.gov/vacode/title58.1/chapter29/section58.1-2900/)
requires a cooperative-specific adjustment to the three consumption-tax amounts
when qualifying federal power is purchased. Its ratio uses total federal power
cost, including facilities rental, divided by the cooperative's Virginia
operating revenue for the taxable period. A dated SVEC numeric factor or
independently established statutory nonapplicability is missing. An account
checkbox cannot establish a zero factor. The actual SCC levy and complete
effective local tax/account intersection also require reconciliation. No generic
ordinary-tax or locality confirmation bypasses these source gaps.

Unincorporated Rockingham County is the contemplated locality, without enabled
tax pricing. Other jurisdictions, governmental exemptions, special accounts and
unverified tax reductions remain outside scope.

## Evidence, DER and validation

[The source ledger](utility_sources/shenandoah_va/sources.json) preserves original
URLs, bytes, hashes, effective dates, source/version conflicts, unavailable
routes and requirements to enable. Raw material is under
`.cache/shenandoah_va/sources`. The SCC public docket client successfully
provided its document index and current accepted schedules. Its original
application and revised-schedule PDF routes returned 404 and were not retried.
Filing metadata is not treated as recovered tariff content.

The [2026 terms](https://www.svec.coop/wp-content/uploads/Terms-and-Conditions-2026.pdf)
require approval for parallel generating equipment and specify monthly billing,
start/end prorating and estimates when valid readings are unavailable. Tariffs
allow readings billed in 10 kWh units. Future acceptance therefore needs actual
meter precision and complete account cycle facts. Exact-installation written
permission must preserve ordinary import billing and document all extra charges
before PV or paired storage can be enabled. Paired storage would require PV-only
charging and zero export. No export credit bank, net metering or standalone/grid
charging is implemented.

The focused check is:

```sh
/usr/local/bin/python3 tools/validate.py --tier focused --test test/test_shenandoah_va.py --output .cache/shenandoah_va/development
```

It checks rejection for both plans and all requested months, unsupported
supplier/settlement/history, calendar/DST/missing data, conservative defaults,
numeric/symbolic entry-point blocking and source-boundary consistency. No
complete-bill benchmark, dispatch/SOC proof, annual study, OpenDSS matrix,
browser acceptance or desktop GUI compatibility pass is claimed.
