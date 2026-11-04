# AES Ohio billing rules and eligibility review

Reviewed November 2, 2026. This review owns eligibility, common billing rules,
D33 excise tax, and DER exclusions. Delivery and supply ledgers own their dated
numeric rates. Original PDFs/HTML and rendering receipts are private under
`.cache/aes_ohio/sources/rules/`; the source ledger records hashes, exact URLs,
selected pages, and reused evidence identities.

## Implementation scope

Use ordinary, single-meter D17 residential or single-phase metered D19 secondary
nonresidential service, G10 Standard Offer generation, and mandatory T8
transmission. D14 defines ordinary residential service as single-phase secondary,
at most 400 amps, primarily residential. D17 also covers churches and certain
noncommercial barns/sheds; those broader uses are outside the initial ordinary
residential study scope.

D19's minimum charge is its monthly customer charge. It has no generic minimum
kW or contract-demand floor. Preserve ordinary low-load-factor customers and model
the applicable D19/T8 cap using the dated delivery/supply values. Exclude
primary-voltage metering, unmetered accounts, county fairs/agricultural societies,
the special 85%-connected-load determination, alternate suppliers, tax-exempt or
self-assessing accounts, and emergency/auxiliary service contracts.

Accept complete calendar billing months only where the delivery/supply source
intersection is complete. The common rules do not establish rate coverage by
themselves. No full-year 2025 or 2026 claim follows from this review.

## Billing calendar and transitions

D05 Eighth Revised, effective September 1, 2023, is in the PUCO book at PDF pages
9-17. Ninth Revised D05 is effective November 6, 2025. B(2) in both versions says
bills normally are monthly, other intervals require customer request and Company
agreement, and bills are computed monthly with adjustments for readings. Neither
version specifies a numeric `days / 30` proration formula for fixed charges,
demand charges, or minimum bills. G05 B(1) and T05 B refer these rules back to D05.

The November 6, 2025 change occurs inside a calendar month. No adopted source was
recovered that determines how to split D19 demand, the low-load-factor cap, T8,
customer/minimum charges, and percentage riders across that transition. November
2025 and other partial or unresolved mixed-rate cycles must be rejected until the
allocation is sourced. A rider's separate bills-rendered wording does not establish
a general mixed-bill allocation rule.

D05 B(9) disallows combining separate delivery/meter readings absent a specific
tariff or agreement. Actual utilities may estimate unread meters; that does not
authorize a simulator to silently fill missing interval data. Reject missing data.

## D19 demand and history

D19 uses the highest **30-minute integrated demand**. The tariff distinguishes
100% on-peak demand, 75% eligible off-peak demand, and a 75% ratchet based on the
greatest applicable off-peak/on-peak demand used for billing in June, July,
August, December, January, or February within the prior eleven months.

For customers below 1,000 kW, no demand is designated off-peak without election
of the $20/month off-peak metering option. That option has a one-year minimum
term, then thirty days' termination notice. Ordinary no-election service must
therefore treat all current intervals at full weight. If the option is modeled
later, its window is 8 p.m.-8 a.m., weekends, and the six listed observed holidays:
New Year's Day, Memorial Day, Independence Day, Labor Day, Thanksgiving, Christmas.

Require authentic prior billing-demand records, or explicit evidence of genuine
new service without prior history. Do not silently convert missing history to
zero. Exact tariff wording is retained in `D19_book_2025-selected.txt` and
`D19_2026-selected.txt` for implementation/benchmark review. The unusual
85%-connected-load service determination has no low-load-factor cap and is
excluded.

## D33 and Ohio excise tax

The current adopted tariff index links Fourth Revised D33, effective October 1,
2018, filed under case 15-1830-EL-AIR. The same sheet is in the assembled June
2025 PUCO distribution book, PDF page 98. It assesses monthly billing kWh of
electricity distributed and expressly incorporates ORC 5727.81(A). Both ordinary
D17 and D19 have these rates, in USD/kWh:

| Tier | Exactly 30 measurement days | Other measurement lengths |
| --- | --- | --- |
| 0.00465 | First 2,000 kWh | First `67 * days` kWh |
| 0.00419 | Next 13,000 kWh, to 15,000 | Next `433 * days`, to `500 * days` |
| 0.00363 | Remaining kWh | Remaining kWh |

For nonnegative utility import `Q`, breakpoints `b1,b2`, and the three rates,
the unrounded component is
`r1*min(Q,b1) + r2*min(max(Q-b1,0),b2-b1) + r3*max(Q-b2,0)`.
Exactly thirty days is intentionally a special case: do not use `67*30` in
place of 2,000. Measurement days are local calendar days; DST's 23/25 elapsed
hours do not change a calendar day's count.

Use electricity distributed through the utility meter, which equals gross
utility-import kWh under the non-export study restriction. Native behind-meter
load and self-consumed PV are not utility-distributed kWh. The entire retained
six-page authenticated ORC 5727.81, effective October 3, 2023, was reviewed. It
contains no ordinary residential/secondary tax maximum. Its special high-use
self-assessor regime and federal, qualified-manufacturing, regeneration, and
other special exemptions are excluded.

**Calculator discrepancy:** the supply review traced the official commercial
calculator's excise normalizer: 25-35 billed days use normalizer 1 and fixed
2,000/15,000 bands. That differs from the statute's daily thresholds for every
non-thirty-day measurement. The calculator is an independent tax arithmetic
benchmark only for exactly thirty-day inputs. Preserve this difference; do not
silently rewrite either source. The simulator's stated formula should follow
the detailed D33/statutory contract. `tax_benchmarks.json` contains independent
Decimal vectors at each breakpoint for 28, 29, 30, and 31 days; these are
formula benchmarks, not measured customer invoices.

No AES D33 CAT gross-up or generic whole-bill CAT adder was found. In particular,
do not inherit Toledo Edison's explicit gross-up. ORC 5751.03's 0.0026 taxpayer
gross-receipts rate does not by itself authorize an AES retail line item.
D05/G05/T05 and D15 do not add one. ORC 5739.02(B)(7) exempts electricity
delivered through wires from sales tax; both the 2023 authenticated and current
September 30, 2025 versions are retained with original provenance. No separate
municipal/franchise percentage was verified. Initial accounts require an
ordinary jurisdiction with no separate local adder; do not guess one.

## PV, paired storage, and excluded contracts

For 2025, use adopted D35 Fourth Revised, effective September 1, 2023, and D05,
rather than backdating the February 2026 technical guide. D35 covers physical
connection and parallel operation. Definition (K) includes static inverters;
PDF page 18's supplemental review explicitly distinguishes PV without battery
storage from other generation. Thus battery configurations were contemplated
by the adopted tariff before 2026, but a tariff review is not a site approval.

Model PV or PV with paired storage only when the Company has approved the exact
equipment and non-export operating configuration, the interconnection agreement
is executed, and permission to operate is in force. The account must continue
under ordinary D17/D19 with no D10 emergency/auxiliary contract-capacity charge.
No individual customer's approvals were obtained in this work. These must be
explicit study eligibility attestations, not an assertion that any proposed
configuration will automatically qualify.

D05 and OAC 4901:1-10-28, effective April 8, 2024, require primarily offsetting
own electricity requirements and sizing within 120% of requirements, based on
the average utility-supplied electricity annually over the preceding three
years. The rule permits a supported consumption estimate for unique cases.
The current public FAQ's previous-year shorthand does not replace that rule.
OAC B(4) gives standard net-metered customers the same rate structure, retail
components, and monthly charges as the otherwise-applicable account. Export
credits and all export/NEM settlement remain unimplemented under the requested
non-export scope, even though the tariff describes them.

No AES renewable-only battery-charging mandate was verified. Charging only from
PV is a conservative simulator restriction, not an asserted tariff requirement.
Standalone storage, sales to third parties, wholesale/PJM settlement, QF/PURPA
cogeneration, and emergency/auxiliary supply contracts remain excluded.

D10(D), PUCO book PDF pages 33-34, makes emergency/auxiliary service subject to a
service agreement and a Contract Capacity Charge using the greater of the prior
twelve-month peak billing kW or agreed capacity, multiplied by the relevant
distribution kW rate less continuous costs. Do not treat those accounts as
ordinary avoided-import billing. G11 is an additional separate QF sales regime,
effective May 1, 2018 despite its filename, with a service agreement, total output
sale requirement, and monthly administrative charge.

The February 11, 2026 technical guide separately defines energy storage and a
behind-the-meter non-exporting class, with anti-islanding protection and PTO
conditions. It is retained as current supplementary guidance only. Its scope
paragraph and non-export section should not be flattened into a universal
historical eligibility assertion. Current OAC Chapter 4901:1-22 includes July
2026 amendments; that current text also was not backdated to 2025.

## Evidence and gaps

- `sources.json`: source URLs, private originals, hashes, selected pages and reuse
  attribution. Original statewide law and NEM evidence remains attributed to its
  Illuminating/Toledo research; only applicability was reviewed here.
- `rules.json`: structured implementation constraints.
- `tax_benchmarks.json`: independent Decimal tax vectors.
- Private `visuals/render_receipts.json`: eight relevant pages rendered and
  visually inspected. Poppler emitted font-cache warnings; the inspected rates,
  units, section labels and effective-date footers rendered readably.
- Local-network DNS was blocked once; a single authorized network-mode fallback
  retained the sources. The current excise-law web reader timed out once; the
  hash-verified prior original and authenticated PDF provided the full text.
  Historical OAC web routes were inaccessible and were not repeatedly retried.
- Unresolved: numeric midcycle proration, November 2025 mixed-rate allocation,
  blanket automatic paired-storage eligibility, individual site PTO/approval,
  and any municipal/franchise adder. Preserve these limitations visibly.

No production code, tests, historical matrix, GUI, Git staging, commit, push,
deployment or stable-engine promotion was performed by this rules workstream.
