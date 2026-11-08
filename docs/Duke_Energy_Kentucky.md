# Duke Energy Kentucky: ordinary RS and bounded DS

The backend adapter supports Duke Energy Kentucky ordinary residential **RS**
and a conservative small-commercial subset of **DS**, with bundled Duke supply
and **zero export**. Executable service coverage is **April 1–June 30, 2025**
and **April 1–June 30, 2026**, using complete calendar service cycles and the
separately confirmed following utility billing month. This is targeted utility
coverage, not uniform 2025–2026 or annual acceptance.

The implementation is in [duke_ky.py](../src/billing/duke_ky.py) and
[duke_ky_rates.py](../src/billing/duke_ky_rates.py). The existing shared
`regional.calculate_cycle` constructs rounded bills from the adapter's
`charge_lines`; there is no new shared hook or billing API.

## Source receipts and separate clocks

[sources.json](utility_sources/duke_ky/sources.json) records exact official
URLs, original SHA-256 hashes, byte counts, retrieval timestamps, relevant PDF
pages and workbook cells. The portable
[filed evidence](utility_sources/duke_ky/filed_evidence.txt) and
[workbook readbacks](utility_sources/duke_ky/monthly_workbook_evidence.json)
have their own hashes. Original PDFs, spreadsheets, extraction scripts and
rendered source pages are retained privately under `.cache/duke_ky/`.

The principal sources are the Kentucky PSC electric tariff book, its cancelled
tariff sheets, the official 2025/2026 FAC filings, and the original monthly ESM
workbooks filed in case **2026-00234**. The ESM review includes two post-review
expense months; their original workbooks establish June/July 2026 billing
factors. Published file years and cancellation filenames do not determine
effective dates.

- **Base and DSMR:** retain service applicability separately from bill issuance.
  Sheet 25 applies schedule revisions according to the initial meter reading
  unless a Commission order provides otherwise. Only stable complete service
  cycles are enabled; no unresolved transition allocation is performed.
- **FAC and ESM:** the expense month is two months before the named utility
  billing month. The initial scope requires the exact verified bill date.
- **PSM:** use the named billing quarter and filed effective date. Positive
  numbers in the PSM tariff are **credits**; parenthesized numbers are charges.
  FAC and ESM use the usual signed-factor convention.
- **DS demand:** fifteen-minute maximum, power-factor adjustment where required,
  an 85% summer-peak ratchet effective for the next eleven months, and a 1 kW
  single-phase minimum exist in the tariff. Independent account review keeps
  every applicable billing demand within the first free 15 kW in this subset.

| Service cycle | Named billing month | Required bill date | FAC $/kWh | RS ESM | DS ESM | Signed PSM $/kWh |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| April 2025 | May 2025 | 2025-05-01 | 0.004559 | 3.51% | 5.48% | 0.001508 |
| May 2025 | June 2025 | 2025-06-02 | -0.006385 | 1.49% | 2.34% | 0.000806 |
| June 2025 | July 2025 | 2025-07-01 | 0.000627 | 5.43% | 8.55% | 0.000806 |
| April 2026 | May 2026 | 2026-05-01 | 0.006094 | -0.39% | -0.60% | -0.005893 |
| May 2026 | June 2026 | 2026-06-01 | -0.009567 | -1.91% | -2.88% | -0.003992 |
| June 2026 | July 2026 | 2026-07-01 | -0.001945 | -0.97% | -1.46% | -0.003992 |

The first-business-day bill date is a deliberately narrow study convention.
Real accounts require an independently documented utility assignment; the
service dates alone cannot establish that assignment. `hypothetical_defaults`
and `hypothetical_cycle_fields` label invented study facts explicitly and
refresh the independently labeled DS history cutoff for each study cycle.

## Base charges, riders and taxes

| Component | April–June 2025 service | April–June 2026 service |
| --- | ---: | ---: |
| RS customer/base minimum | $13.00/month | $14.75/month |
| RS base energy | $0.111639/kWh | $0.126104/kWh |
| RS DSMR | $0.002418/kWh | $0.005514/kWh |
| RS Home Energy Assistance | $0.30/month | $0.30/month |
| DS single-phase customer/base minimum | $15.00/month | $15.00/month |
| DS first 6,000 kWh base energy | $0.114788/kWh | $0.126995/kWh |
| DS DSMR | $0.003409/kWh | $0.001154/kWh |

The customer charge supplies the ordinary base minimum. Mandatory riders then
increase or decrease the base bill; a negative rider is preserved at zero
imports. DS demand above 15 kW, later energy blocks, primary metering, power
factor surcharges, former Rate C and special facilities are outside this
implementation. Within the bounded subset, the tariff's maximum base rate is
inactive. Bundled Duke rates are retained as bundled components; no unsupported
delivery/supply split or additional PJM wholesale charge is invented.

RS ESM applies to the ordinary subtotal including customer, energy, DSMR, HEA,
FAC and signed PSM. DS ESM excludes embedded base fuel **$0.033780/kWh** and
FAC, while retaining customer, nonfuel base energy, DSMR and signed PSM. This
class distinction is material; applying RS arithmetic to DS is incorrect.

The tax scope is one independently confirmed account in **unincorporated Boone
County within Boone County school district**, with **3% school tax** and no
local-government fee. The Kentucky Department of Education's approved
FY2025/FY2026 levy tables identify district `035 Boone County` at
`rptTaxRateLevied!A19` and utility tax **3** percent at `P19`; the FY2027 table
confirms the same rate at `A8`/`P8`, covering July 2026 bill issuance. The tables
and exact readbacks are retained in the ledger. A county name or a nearby city does
not establish the district or franchise-fee status. Tariff sheet 95 requires
any applicable local-government fee, so accounts with such a fee reject this
zero-fee scope. RS requires Duke's accepted primary-domicile sales-tax
exemption for the full cycle. Ordinary taxable DS pays **6% sales tax** on the
subtotal including the school levy; exemptions and direct-pay arrangements are
outside scope.

Independent literal Decimal examples at 1,000 imported kWh, with study component
half-up cents, are RS/DS **$142.25/$158.09** for April 2025 service and
**$150.68/$155.83** for April 2026 service. These are computed tariff benchmarks,
not actual customer invoices. Unrounded arithmetic and component rounding are
separate claims.

## Account and equipment limits

`defaults()` is unconfirmed and cannot execute. Required evidence confirms Duke
Kentucky tariff assignment, one ordinary 120/240 V single-phase secondary meter,
complete monthly charges, billing month/date, school district, tax treatment
and absence of other charges. RS is ordinary domestic use; mixed commercial use
and three-phase service do not qualify for this RS implementation.

DS requires retained ordinary assignment, a separately reviewed current billing
demand ceiling between 1 and 15 kW, and twelve preceding actual monthly demands
no greater than 15 kW. The review includes the summer ratchet, any restored
demand history, power factor, metering and classification. The final history
month is the month before the named billing month. The study checks native load
as well as imports; solar reductions cannot establish eligibility. Current
DS native/import limits are **14.99 kW and 5,999 kWh per cycle**, with the
independently reviewed current demand ceiling providing a tighter power limit
when it is below 14.99 kW. RS study bounds
are **25 kW and 10,000 kWh**; these are modeling limits, not RS tariff thresholds.

PV requires final interconnection approval active before the cycle **and** a
written agreement expressly preserving ordinary import billing for the exact
non-export equipment. Sheet 21's auxiliary/supplementary-service restriction,
sheet 83 approval process and GSS applicability must be resolved by that
agreement. Generic permission to interconnect and a zero-export optimizer do
not establish ordinary RS/DS billing. Paired storage requires the same explicit
equipment approval, PV-only charging and no battery export. Standalone storage,
export credits, net-metering enrollment and credit banks are excluded.

## Validation and remaining gaps

The utility-focused suite covers all six monthly intersections, independent
Decimal component bills, numeric/symbolic parity including negative riders and
zero imports, meter/native bounds, billing dates, account/history/tax/DER
rejection, missing/duplicate/partial/wrong-zone intervals and source receipts.
DST month grids reach the source gate correctly but reject missing tariff
coverage; no executable DST billing month is claimed.

Final utility-focused development acceptance passed **177 tests** in **1.49
seconds** of pytest runtime (**1.78 seconds** for the launcher pytest phase),
with the report at `.cache/duke_ky/development/attempt3/report.json`. Earlier
failed and passing reports remain attributed to their original fingerprints.
The final run includes the approved FY2025/FY2026/FY2027 tax receipts and the
independently reviewed current-demand ceiling checks.

Unresolved periods remain fail-closed: January–March 2025; July–October 2025
interim-rate/refund and base transitions; November 2025–March 2026 intermediate
base/DSMR transitions; and July–December 2026 later ESM/base-fuel intersections.
The current tariff book's stale base pages do not authorize September 2026
pricing. Broader account classes, other tax jurisdictions, actual invoice
replication and export settlement are unimplemented.

Shared registry/browser/worker/artifact integration and the frozen historical
OpenDSS matrix are a separate batch responsibility. GUI tests, native GUI,
release-tier regression, annual electrical coverage, promotion, deployment,
staging, commit and push are excluded from this utility subtask.
