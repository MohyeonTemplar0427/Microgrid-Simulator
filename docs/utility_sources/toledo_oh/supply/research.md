# Toledo Edison ordinary SSO supply and tax review

Reviewed November 1, 2026. This ledger covers Toledo Edison RS and measured GS
secondary **ordinary Standard Service Offer (SSO)**. It is independent of CEI
and Ohio Edison pricing. [Sources](sources.json) retain original public PDF
URLs, binary hashes, page selections and excerpt hashes; full binaries remain
in ignored `.cache/toledo_oh/sources/shared/`.

## Exact supply components

Amounts are **USD per kWh**, converted exactly from filed cents. GEN capacity
is already converted to retail energy units. NMB/transmission belongs to the
separate delivery ledger. No additional LMP, PLC/NSPL, loss, wholesale capacity
or generic whole-bill CAT charge is added to the filed prices.

| Supply dates | GEN energy | RS / GS capacity | GCR | AER | NDU |
| --- | ---: | ---: | ---: | ---: | ---: |
| January 2025 | .073408 | .003647 / .003038 | .003073 | -.000023 | .000317 |
| June 2025 | .073661 | .024846 / .021990 | -.002909 | .000172 | -.000546 |
| July–August 2025 | .073661 | .024846 / .021990 | -.001206 | .000244 | .000159 |
| September 2025 | .066966 | .024846 / .021990 | -.001206 | .000244 | .000159 |
| October–December 2025 | .066966 | .024846 / .021990 | .000841 | .000295 | .001307 |
| October 2026 | .072774 | .029096 / .021536 | .009846 | .000135 | .000784 |

GEN17's winter energy and class capacities establish January; GEN18 and its
ESP-IV chronology are not available for February–May. The complete June 12,
2025 archive contains GEN19 effective June 1 and April quarterlies. The complete
August 25 archive contains July quarterlies; winter GEN19 energy starts with
September. The late-2025 book contains October quarterlies, but its capture
or filename does not establish a later delivery revision. GEN20 effective
June 1, 2026 has one ordinary energy/capacity column and the current book has
October 2026 quarterlies.

**These are supply-only intersections.** The complete-bill adapter must intersect
all independently dated delivery and tax evidence. In particular, July's
missing LGR delivery page and August's fixed-charge allocation prevent full
calendar billing; December 2025 DCR remains unverified despite available supply
components. Final complete-bill dates are controlled by the aggregate utility
ledger, not this wider supply table.

SSO is distinct from competitive supply, PIPP, optional time-of-day, critical
peak and real-time programs. Ordinary GEN rates are selected; no shopping
or optional-pricing substitution is made. GCR1 contains the nonzero ordinary
SSO charge; GCR2 is explicitly zero in retained selections. Its formula already
includes applicable CAT and the filed loss treatment. AER/NDU are avoidable
for certified-supplier customers, which are outside this implementation.

## State taxes

Toledo's Original Sheet 92, effective January 23, 2009, is retained in the
January 2025 and October 2026 originals (PDF pages 100 and 108 respectively).
It applies ordinary state-kWh tax consistent with **ORC5727.81** and explicitly
specifies the CAT formula `1 / (1 − CAT)` for those tax charges.

ORC5727.81(A), current effective October 3, 2023, specifies $.00465, $.00419 and
$.00363/kWh. Exactly thirty measurement days use cumulative 2,000/15,000-kWh
bands. Other measurement periods use daily averages: cumulative thresholds
are **67 × local calendar days** and **500 × local calendar days**, rather
than silently reusing 2,000/15,000 or multiplying elapsed hours by 1/24. Thus
November 2025's thirty days use 2,000/15,000 despite its 721 elapsed hours;
a thirty-one-day month uses 2,077/15,500.

ORC5751.03 defines CAT as .0026; the state-kWh charge therefore divides by
`.9974`. Other filed rate amounts are not grossed up again. ORC5739.02(B)(7)
exempts electricity delivered through wires from generic retail sales tax.
Current official versions of all three sections were rechecked November 1;
the original pre-September2025 sales-tax excerpt is also retained. Statewide
statutory extracts from the earlier source review are reused unchanged with
attribution in [tax_sources.json](tax_sources.json), while Toledo applicability
was established from its own Sheet92. Exact conclusions are in
[tax_rules.json](tax_rules.json).

The supported account must independently confirm no municipal/franchise adder,
self-assessment, special tax contract or exemption. No locality rate is inferred
from a coordinate, postal code, supplier or another affiliate.

## Source limits and verification

Both May 2025 and May 2026 archive captures contain exactly 5,242,880 bytes and
lack a PDF EOF. PyPDF reported an unexpectedly ended stream; one bounded pass
with the existing private PyMuPDF1.26.7 reader found zero recoverable pages.
Neither source supplies a rate. The February 2026 capture is byte-identical to
the late-2025 composite and does not establish 2026 rates. Blocked-source hashes
and outcomes are in [blocked_sources.json](blocked_sources.json). No unchanged
failed route was retried and no rate was reconstructed from a PTC total.

The January2025, June2025 and current GEN tables were rendered and visually
reviewed; numerical capacity, season, cent units and effective headers match
the retained text. [Visual receipts](visual_review.json) pin the three images.
Independent benchmark fixtures and the standalone artifact auditor use literal
reviewed facts, Decimal arithmetic, actual **15-minute** Toledo peaks, and the
statutory calendar-day tax rule. They import no production rate/math code for
expected arithmetic. Study rounding remains half-up of saved raw float
components, with explicit half-cent boundary cases; no exact customer-invoice
or rounded-cash optimum is claimed.
