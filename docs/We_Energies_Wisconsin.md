# We Energies: Wisconsin Electric Power Company

This adapter models ordinary bundled Wisconsin Electric service in Wisconsin,
under Rg1 residential, Rg2 residential Time of Use, Cg1 small commercial General
Secondary, and Cg6 small commercial General Secondary Time of Use. It does not
model We Energies natural gas, Michigan service, Wisconsin Public Service,
Alliant, or municipal utilities.

## Supported dates and account facts

Verified complete calendar billing cycles cover **January–June 2025 and
January–September 2026**. July–December 2025 still lacks verified dated
environmental control charge (ECC) evidence. The default verified mode rejects
that gap before dispatching a study to the worker.

An explicitly selected **`provisional_2025`** mode, together with boolean
`provisional_assumptions_accepted: true`, permits full-year 2025 studies by
carrying June's ECC through July–December. This is a user-authorized study
assumption, not evidence that those filed factors remained effective. Neither
mode selection alone nor acceptance alone enables the gap. Account defaults,
including hypothetical accounts, remain verified-only and unaccepted. Verified
months remain verified even when provisional mode is selected. October 2026
and later dates remain unsupported; provisional mode never expands them. The
latest downloaded book contains future December 2026 ECC prices, which do not
apply to earlier service.

The initial tax scope is explicitly assumed **unincorporated Waukesha County**,
one ordinary meter and one service line. Coordinates suggest a study location;
they do not establish service territory, tariff enrollment, a tax jurisdiction,
or interconnection approval. Other tax localities, exempt commercial accounts,
assistance discounts, special facilities and contracts remain unsupported.
Residential accounts must separately confirm permanent principal residence,
because the winter sales-tax exemption does not cover second homes or transient
accommodations. The catalog starts confirmations unchecked; hypothetical study
builders mark their assumptions explicitly.

Only secondary 240 V split-phase residential service and 240 V single-phase or
480 V three-phase commercial service are in this model scope. Other service
voltages may be tariff eligible but need their own explicit physical/account
configuration. Circuit replay is representative quasi-static analysis, not a
utility approval or site engineering study.

## Prices and bill composition

All four plans charge **$0.49315 per local calendar day**, including one meter.
The energy rates in dollars per kWh are:

| Plan | 2025 flat/on-peak | 2025 off-peak | 2026 flat/on-peak | 2026 off-peak |
| --- | ---: | ---: | ---: | ---: |
| Rg1 | .18325 | .18325 | .19342 | .19342 |
| Rg2 | .27006 | .10387 | .30084 | .10028 |
| Cg1 | .16659 | .16659 | .17621 | .17621 |
| Cg6 | .25388 | .09765 | .29475 | .09825 |

These are non-demand plans. Cg2 becomes mandatory at 329 kWh/day for three
billing months within twelve months, subject to the filed classification and
waiver rules. The first implementation requires current Cg1/Cg6 classification
and prior-history confirmation, and conservatively keeps **every simulated
cycle below 329 kWh/day**. It does not infer tariff enrollment from one low-use
month or model the special 80% off-peak large-customer exception.

Each bill itemizes customer charge, energy, fuel adjustment, dated fuel
reconciliation, ECC, state low-income assistance, and sales tax. Ordinary fuel
adjustment is zero in 2025 and $0.00199/kWh in 2026. ECC factors differ between
residential and small commercial non-demand accounts:

| Verified period | Residential ECC $/kWh | Small commercial ECC $/kWh |
| --- | ---: | ---: |
| Jan–May 2025 | .00056 | .00052 |
| Jun 2025 | .00055 | .00050 |
| Jan–May 2026 | .00052 | .00047 |
| Jun–Sep 2026 | .00054 | .00048 |

For **July–December 2025 only**, assumption
`WE25-ECC-JUNE-CARRY-FORWARD` uses **$0.00055 residential / $0.00050 small
commercial per kWh**, referenced to June's official issuer certificate. No
filing has verified those six months' factors or their effective dates. In
particular, January 2026's lower factors are not applied backward to December.
The assumption ledger records model `we_energies_wi_2025_provisional_v1`, dates,
units, proxy values, reference source and replacement evidence still needed.

The verified September 2025 fuel reconciliation remains a separate credit:
**−$0.04054/kWh residential / −$0.03620/kWh small commercial**, applied to
September use. The provisional model preserves that credit, verified base
energy and TOU prices, the zero 2025 ordinary fuel adjustment, and existing
calendar rules. It does not substitute a single combined guessed rate.

The state low-income assistance charge is the lower of 3% of the electric
subtotal or **$3.15 residential / $10.66 small commercial per service line per
month**. It is not taxable. Ordinary unincorporated Waukesha service has 5% state
sales tax; qualifying residential bills dated November–April are exempt. The
implementation uses service dates for rate components and bill date for that
tax exemption. It supports full calendar cycles whose bill date is the final
service day; shifted, partial and crossing cycles are rejected rather than
assigning an unverified charge allocation.

Wisconsin Act 141 energy-efficiency amounts are already included in base prices.
The informational sheet 20.1 is not a second rider. Ordinary bundled supply also
includes capacity and transmission costs: MISO LMP, a capacity PLC, a transmission
PLC, and ATC network charges are not added to this retail bill. The MISO LRZ2 / ATC
metadata are separate from tariff enrollment and any wholesale pricing location.

## TOU calendar

Rg2 has a customer-selected twelve-hour on-peak window starting at **7, 8, 9 or
10 a.m.**, retained for twelve months. Cg6 uses **9 a.m.–9 p.m.**. On-peak applies
Monday–Friday in prevailing America/Chicago time, excluding New Year's,
Memorial, Independence, Labor, Thanksgiving and Christmas days. Wisconsin
Statute 995.20 moves a Sunday legal holiday to Monday; Saturday stays Saturday.
Consequently **Friday July 3, 2026 is an ordinary peak weekday**. Good Friday,
Juneteenth and the day after Thanksgiving are also ordinary weekdays under
these particular tariffs. Other utilities' calendars are not reused.

Tariff periods are half-open at their boundaries. Energy uses actual interval
duration in UTC, while the daily customer fee counts local calendar days; the
spring DST month has 743 hours and still 31 daily charges. TOU billing and the
dispatch objective use the same mask and rates.

## PV, storage and optimization

CGS-NP sheets 201.4–201.5, effective April 1, 2023, require the non-purchase
generation enrollment for on-site customers who do not sell to the utility.
Imports retain the ordinary applicable retail rate. Inadvertent exports receive
no payment. This implementation instead enforces zero scheduled export and
preserves PV curtailment. It requires explicit approved CGS-NP/interconnection
assumptions, PV with or without AC-coupled storage, and no extra project-specific
fees. Standalone storage, NEM/net billing and export settlement are excluded.
The first study scope conservatively bounds PV nameplate plus battery discharge
at 40 kW; that is a simulator boundary, not the tariff's 15 MW ceiling.

The shared charge expression produces both numerical bills and the dispatch
objective. The capped state fee uses an exact bounded minimum graph; the
optimizer cannot avoid the fee by substituting an unbounded or loose epigraph.
Battery wear is optional under the existing shared policy. Historical
perfect-foresight optimization, billed scheduled meter flows and representative
OpenDSS losses/PCC measurements remain separate quantities.

Bills in the gap report `rate_evidence_status: provisional`,
`objective_scope: provisional_modeled_bill`, the assumption model and the
actual assumptions used. ECC and the dependent state-assistance fee/sales-tax
amounts carry the assumption ID; the fee and tax **rules** remain verified.
An exempt tax or capped fee may numerically remain unchanged, but its dependent
component is still identified. Other components retain verified evidence.
Itemization completeness does not make a provisional bill historically verified.
Annual comparisons containing any gap month are provisional estimates, including
the dispatch objective and savings. Solver reconciliation, optimization and
representative electrical checks cannot validate historical tariff assumptions.
Saved results preserve the evidence metadata, warnings and assumption records.

## Evidence and verification

Official sources and byte hashes for downloaded files are in
[the source manifest](utility_sources/we_energies_wi/manifest.json), with selected
text extracts. Original PDFs and research caches remain ignored. The June 2025
monthly certificate proves that month's actual ECC; it does not prove July–
December. The June 2026 revision 22 sheet is available through the official
document's search-indexed historical text; no original-byte hash is claimed
for that extract. The original current book now contains future revision 23.

The utility's illustrative February 3, 2026 Rg1 bill has 669 kWh over 29 days:
customer $14.30, energy $129.40, fuel $1.33, ECC $0.35 and state fee $3.15, total
**$148.53**. Tests independently reconcile these components and the extra daily
charge against a supported February calendar calculation. The published shifted
cycle itself remains rejected; this benchmark does not claim cycle support.

Focused offline tests cover all executable plan/month combinations, explicit
account facts, tariff boundaries, all Rg2 windows, legal/observed holidays,
ordinary weekdays, DST, missing/duplicate intervals, the fee cap's branches,
numeric/symbolic objective parity, strict provisional consent, default rejection
of unverified dates, all six provisional monthly benchmarks, fall DST, preserved
September refund, annual cycle preparation and the published sample components.
Historical scenarios use the existing prepared ERA5
weather and explicitly synthetic household/office load; weather observations do
not make that load measured or regionally calibrated. A full-year 2025 numerical
validation is a **provisional model check**; it is not a verified reconstruction
of actual utility bills. Actual tariff-history gaps remain open until primary
evidence replaces the declared assumptions.
