# South Central Power Company — Ohio

R residential and SGS small general service are researched, visibly unavailable
plans. No complete executable 2025–2026 monthly component intersection was
established. Their base charges and one dated example invoice are preserved as
source observations; neither is presented as an executable bill or dispatch
tariff. Confirmed and hypothetical accounts both reject pricing.

## Primary evidence and verified base observations

The [official member rates page](https://www.southcentralpower.com/your-account/member-rates/)
and [company documents](https://www.southcentralpower.com/about-us/company-documents/)
identify R, SGS, other general-service classes, and Riders A/B. The public
official document catalog recovered the superseded 2024 and 2025 sheets.

| Effective date | Board approval | R consumer charge/month | SGS consumer charge/month | Distribution/kWh |
| --- | --- | --- | --- | --- |
| April 1, 2024 | December 19, 2023 | $27 | $38 | $0.0260 |
| April 1, 2025 | December 17, 2024 | $29 | $41 | $0.0260 |
| April 1, 2026 | March 17, 2026 | $34 | $48 | $0.0260 |

These are partial bill components. Source URLs, original byte hashes, applicable
pages, discovery routes, and observations are in
[the source ledger](utility_sources/south_central_oh/sources.json). Original
downloads remain under `.cache/south_central_oh/sources`.

R covers individual single-family, home or farm single-phase service. SGS covers
non-residential uses and may be limited to billing capacity below 50 kW. The
cooperative retains reclassification authority based on historical use. The
recovered SGS schedules contain no separately priced demand charge. That does
not establish classification from modeled or PV-reduced imports.

Both classes have a transformer-based minimum: the consumer charge covers the
first 5 kVA, with $1.50 per kVA above 5. R uses installed or allocated capacity;
SGS uses allocated capacity and the highest applicable minimum. Unusual SGS
installations can have separate contract minimums; extensions can add facility
or minimum charges. The sheets permit estimated or bimonthly billing and full
charges for a month or part thereof. A transformer allocation, contract, actual
meter cycle and classification must be independently established before any
future account is priced. Single-phase motor limits and starting-control
requirements also apply.

## Missing whole-bill intersections

[Rider A](https://www.southcentralpower.com/wp-content/uploads/Rider-A-1.pdf),
effective June 1, 2009, passes direct or allocable governmental impositions
through to bills. No complete numeric locality/account vector was established.
The [Ohio kWh-tax statute](https://codes.ohio.gov/ohio-revised-code/section-5727.81)
specifies $0.00465/$0.00419/$0.00363 per kWh for 30-day blocks through
2,000/15,000 kWh. Other measurement lengths use daily-average thresholds of
67/500 kWh and the actual days, with separate exemptions and self-assessment
rules. Current [general sales-tax law](https://codes.ohio.gov/ohio-revised-code/section-5739.02)
exempts electricity delivered through wires; it does not resolve every Rider A
imposition or historical account fact.

[Rider B effective October 1, 2025](https://www.southcentralpower.com/wp-content/uploads/Rider-B-effective-2025.pdf)
computes separate monthly generation and transmission factors from supplier
invoices, each rounded to six decimal places with its stated loss multiplier.
It supplies a calculation method, without the actual monthly historical
factors. The previous Rider B original was not recovered. The utility's
[bill explanation](https://www.southcentralpower.com/your-account/payment-billing/understanding-your-bill/)
confirms monthly variation. No monthly factor table was present in the recovered
rate page, bill page or public document catalogs. A formula, upload date or
neighboring month's price cannot fill that gap.

South Central Power's bundled cooperative retail supply and its Buckeye Power
generation/transmission partner are separate facts from PJM regional metadata.
No IOU SSO price, wholesale price or transmission-zone identity substitutes for
this cooperative's retail factor evidence.

## Independent official sample reconciliation

The [official residential example](https://www.southcentralpower.com/wp-content/uploads/Residential-Bill-Example-2026.pdf)
shows April 30–May 29, 2026 service, a June 2 bill date, and 1,201 kWh. Literal
Decimal arithmetic reproduces each printed component:

| Component | Example amount |
| --- | --- |
| Consumer | $34.00 |
| Distribution: 1,201 × $0.026 | $31.23 |
| Generation: 1,201 × $0.078845 | $94.69 |
| Transmission: 1,201 × $0.030777 | $36.96 |
| Ohio kWh tax | $5.58 |
| Total | $202.46 |

[The sample receipt](utility_sources/south_central_oh/sample_bill_benchmark.json)
retains unrounded arithmetic, printed cents and its original source hash.
Its service period spans calendar months and is billed in June. This is an
example-invoice arithmetic check, without established applicability to other
cycles, SGS, or optimized imports. An undated split-bill illustration using a
$27 consumer charge and a separate security-monitoring example are explicitly
excluded as historical electric rate evidence.

## DER and acceptance boundaries

No PV/storage equipment mode is enabled while complete rate coverage remains
unavailable. Future non-export support requires written final South Central
Power approval preserving ordinary import billing for the exact installation,
with active interconnection/metering before the cycle and all extra charges
documented. The [official interconnection process](https://www.southcentralpower.com/faqs/what-is-south-central-power-companys-interconnection-process/)
does not itself establish that account-specific approval. Paired storage would
require PV-only charging and zero export. Standalone/grid-charged storage,
avoided-cost export settlement, net metering and credit banks are unverified.

The targeted focused check is:

```sh
/usr/local/bin/python3 tools/validate.py --tier focused --test test/test_south_central_oh.py --output .cache/south_central_oh/development
```

It verifies source-boundary rejection across both classes and all requested
months, calendar/DST/missing-data rejection, numeric/symbolic entry-point
blocking, conservative defaults, ledger scope and the independent sample
arithmetic. No executable whole-bill, dispatch/SOC proof, annual study,
OpenDSS matrix, browser acceptance or desktop GUI compatibility pass is claimed.
Monthly factor originals and applicability, Rider A/locality/account facts,
transformer/contract minima and exact-installation DER terms are the next
evidence needed before implementation can be enabled.
