# Alliant Energy Iowa / Interstate Power & Light

The shared local-browser candidate supports ordinary bundled Iowa service
under the five residential and small-commercial tariffs below. **Complete
verified component coverage is January 1–December 31, 2025 and June 1–October
31, 2026**, on complete calendar
billing cycles with consecutive **15-minute meter intervals**. Thirty-minute
averages cannot establish the IO tariff's quarter-hour net inflows and are
rejected for this entire initial scope, including grid-only comparisons.
Other isolated prices are retained as research evidence,
not silently assembled into complete bills. No Alliant provisional-rate mode
is available. The prior We Energies/Duke acceptance does not authorize
unverified Alliant prices.

Alliant Iowa is Interstate Power & Light (IPL), in MISO. Wisconsin Power &
Light is a separate Alliant utility and is not covered by this adapter.
Distribution utility, Iowa jurisdiction, supplier, resource-adequacy zone,
transmission ownership, tax jurisdiction and wholesale price identity remain
separate account facts. Adding Iowa does not expand PJM population coverage.

## Selected retail plans

| Code | Customer class and ordinary energy structure |
| --- | --- |
| 400 | Residential seasonal energy |
| 407 | Residential two-part Time of Day |
| 427 | Residential three-part Time of Day, including daily super-off-peak |
| 600 | Non-residential General Service seasonal energy |
| 607 | Non-residential General Service two-part Time of Day |

The [posted residential](https://www.alliantenergy.com/-/media/alliant/documents/accountandbilling/ratesandtariffs/iowaelectricrates/electricresidentialserviceusage.pdf)
and [general-service sheets](https://www.alliantenergy.com/-/media/alliant/documents/accountandbilling/ratesandtariffs/iowaelectricrates/electricgeneralserviceusage.pdf)
are effective October 1, 2024. The customer charge is a **daily** price:
$0.5096 residential and $0.7562 general service per meter. The monthly amounts
printed for comparison are not charged in addition. The summer season is
June–August; September returns to winter energy prices.

All five selected plans are non-demand tariffs. The Demand Response Cost
Recovery rider is a per-kWh recovery factor, not a charge on the customer's
monthly maximum kW. Optional demand 507/707, larger commercial tariffs,
three-phase supplements, special facilities, assistance/exemption cases,
Second Nature subscriptions and discretionary Energy Efficiency Bill Credit
payments are outside the ordinary-account scope.

Residential enrollment is for domestic single-family or individually metered
apartment use. General-service classification is separately confirmed with
the utility and its monthly usage history. Section 2.03 says classification
generally relates to monthly energy; this model does not interpret the
tariff's 20,000-kWh wording as a total annual cutoff. For its deliberately
bounded 600/607 case, every scenario stays below 20,000 kWh of cycle purchases.
That bound does not establish eligibility, remove continuation rights of
existing accounts or automatically transfer an account between schedules.

## Dated charges and double-count prevention

Billing and optimization call the same charge expressions. Each numerical
bill exposes both rounded line items and unrounded reconciliation arithmetic.

| Component | Supported treatment |
| --- | --- |
| Customer and base energy | Daily customer charge and October 2024 base schedule, with the applicable seasonal/TOD period |
| Energy adjustment | Published designated-billing-month EAC composite, applied once |
| EECR | January 1–June 16, 2025: $0.0009/$0.0014 per kWh residential/general service; June 17–December 31: $0.0006/$0.0032; June–October 2026: $0.0013/$0.0038 |
| DRCR | Bounded January 1–June 16, 2025 reconstruction: $0.0031/$0.0023 per kWh; June 17–December 31: $0.0048/$0.0028; June–October 2026: $0.0042/$0.0023 |
| RTS | January–August 2025: $0.04077/$0.03217 per kWh; September–December: $0.04055/$0.03196, refund included; February 6–July 31, 2026 filed factors $0.04494/$0.03568; August 1 factors $0.04456/$0.03539 (complete bills remain June–October 2026) |
| TBR | Separate credit $0.00789/kWh residential or $0.00592/kWh general service for January–September 2025; expires October 1, 2025 |
| State sales tax | Residential energy exemption; ordinary commercial 6% |
| Local-option tax | Confirmed unincorporated Linn County 1%, using the same electric-service base; no franchise supplement |

The official EAC summary includes Rate Case Expense of $0.00006/kWh from
September 2025 onward. The adapter does not add RCE a second time. The EAC
totals also retain their included AEP/fuel portions. Historical EAC's TBR
column is dashed, and official utility statements separately bill the Tax
Benefit Rider. It is therefore an additional negative charge before tax for
January–September 2025, rather than a second copy of a composite component.
The TBR cutoff is a **service-date rule on October 1, 2025**, independent of
EAC's designated billing month. A government-published September–October bill
shows the credit prorated for its September days even while the entire cycle
uses October EAC. This model still rejects such shifted cycles; complete
October calendar cycles receive no TBR. The expired credit adds no zero-value
line to existing 2026 bills.

EECR, DRCR and RTS changes use **whole-cycle imported kWh multiplied by
calendar-day fractions**. They do not multiply the actual interval purchases
on each side of the change. The June 17, 2025 change therefore gives a complete
June cycle 16/30 of the old factor and 14/30 of the new factor, applied to all
of that cycle's imports. Original utility bills in public municipal packets
demonstrate this allocation for both EECR and DRCR, including a May 20–June 19
cycle with 27 old-factor days and three new-factor days. The optimizer uses
the same constant weighted coefficients, so concentrating purchases after
June 17 cannot incorrectly avoid the old portion of a rider.

Results retain each rider segment's start/end dates, calendar-day count,
factor and source reference, plus the billed weighted factor. Existing
`rider_versions` are first-service-date source snapshots; the complete
`rider_allocation_segments` field is authoritative for a crossing month.

Some filing headers and factor-application dates differ. The implementation
uses the explicitly stated factor date, including June 17, 2025 and June 1,
2026 for EECR/DRCR and
February 6/August 1 for RTS. The generic public RTS explanation's earlier
2026 date label does not replace the dated filed factor clock. The original
sixth DRCR sheet was not recovered: early-2025 class factors are reconstructed
from official utility bill guides for 400/407/427 and general service,
continuous original general-service bills in public municipal records, and
the filed seventh revision expressly replacing the substitute sixth revision
on June 17. This evidence does not assert an unrecovered 2024 start date.
The older EECR sheet's price-code list omits 427; the utility's official
Night Owl 427 guide directly confirms its early-2025 EECR/DRCR factors, so no
other plan's eligibility or price was silently substituted. EAC's blank
November/December 2026 entries are missing data, not zero prices.

RTS is a retail per-kWh charge on these plans. No wholesale LMP, customer
capacity/PLC obligation or extra transmission-tag price is added to the
ordinary bill. Supply and regional wholesale market signals remain separate.

## TOD clock and holiday boundary

The filed sheets specify **CST** for the summer weekday 2–7 p.m. peak. Code
uses fixed UTC−06:00, so those peak hours appear at 3–8 p.m. on daylight local
clocks. Rate 427's midnight–8 a.m. CST super-off-peak applies daily throughout
the year. The summer season itself uses local service dates.

The [public program guide](https://www.alliantenergy.com/ways-to-save/time-of-day-iowa)
uses the broader term CT. This source wording difference is disclosed, and
TOD accounts must explicitly confirm that the actual billing meter follows
the filed-CST interpretation. Arithmetic and solver agreement cannot resolve
the utility's operational meter configuration. No alternative floating-CT
interpretation is silently selected.

Independence Day is the only stated summer peak exclusion. The actual July 4
date is excluded; no Friday/Monday observed-day substitution, Juneteenth or
another utility's holiday list is imported. Rate 427 retains its daily
super-off-peak window on July 4. DST interval grids preserve the spring gap
and both timestamps in the fall fold; a day is never assumed to be 96 records.

## Account, tax and solar scope

The representative weather point is near rural Linn County at 42.10 N,
91.46 W. Neither it nor a postal code proves IPL service or an unincorporated
tax address. The account separately confirms unincorporated Linn County,
ordinary taxable status and no franchise, government-relocation or other
supplemental charges. The [county](https://www.linncountyiowa.gov/1593/Local-Option-Sales-Tax-Referendum)
documents the 1% local-option continuation through 2034; Iowa DOR documents
the residential state-energy exemption and local-option treatment. Cedar
Rapids city has different franchise charges and is not substituted for this
unincorporated account.

The first electrical account is one meter/service line, ordinary secondary
120/240 V single phase, without excess-facility charges or a billing PF
adjustment. Shared OpenDSS checks use declared representative service circuits;
they do not verify the actual site, supply tariff or tax jurisdiction.

The filed [Inflow–Outflow DG tariff](https://www.alliantenergy.com/-/media/alliant/documents/accountandbilling/ratesandtariffs/iowaelectricrates/inflowoutflowtariff.pdf)
retains the eligible ordinary schedule's charges and riders for each 15-minute
net inflow. It provides standard bidirectional metering without an additional
meter charge beyond the applicable ordinary schedule. These comparisons use
that ordinary inflow treatment with outflow constrained to zero.

The user must confirm IO eligibility, applicable 110%-of-annual-use sizing,
approved interconnection and ordinary import billing, or state an explicit
hypothetical approved agreement. The study does not infer the utility's
three-year usage/sizing determination from a short synthetic profile. Its
aggregate PV-nameplate-plus-battery-discharge bound of 20 kW is a conservative
study limit, not proof of a legal interconnection category. Standalone storage,
legacy net-metering enrollment, exports, credit banks, annual forfeiture and
IO export settlement remain unsupported. One-time installation/interconnection
capital costs are not part of the operating-bill comparison.

## Evidence, gaps and verification

[The source pack](utility_sources/alliant_ia/README.md) records every component,
source revision, retrieved date, method and extract hash. Newly recovered
original PDFs and archived official utility pages retain their binary hashes;
older indexed-only evidence remains marked as such. A historical Sitecore
hash parameter is not an immutable version: several old URLs now return the
current 2026 PDF. Attached utility sheets in a public housing-authority report
provide additional dated historical observations; the consultant's compiled
estimates are not treated as complete utility bill benchmarks.

All twelve 2025 calendar months are executable for all five plans. The
[archived official RTS history](https://web.archive.org/web/20250907174848id_/https://www.alliantenergy.com/account-and-billing/understanding-bill-rates/iowa/electric/rts)
explicitly identifies January–August and September-onward factors and the
September 1 application date. The refund is already included. This does not
extend coverage to January–May 2026, whose remaining rate intersections are
still rejected. Initial/final, shifted and partial cycles remain unsupported,
even where a recovered statement demonstrates a particular allocation.
Complete hypothetical calendar cycles keep designated billing months and
service-date clocks explicit. The ten-year research target is not a ten-year
coverage claim.

Focused billing validation for the 2025 extension passed **203 tests** using
`/usr/local/bin/python3 tools/validate.py --tier focused --test test/test_alliant_ia.py`.
Evidence is `.cache/validation_alliant_2025_billing_final/report.json`. The tests
include **60 independent 2025 monthly bills** and 25 preserved 2026 monthly
bills, all five plans' numerical/CVXPY agreement, uneven June imports on either
side of June 17, itemized TBR expiry, RCE double-count prevention, RTS refund
boundaries, CST/TOD/holiday/DST handling, missing data, eligibility and
non-export limits. Literal March/November benchmarks use 743/721 elapsed hours
and independently counted fixed-CST super-off hours. The ordinary grid-only
reference clears IO enrollment reporting while retaining the same ordinary
charge expressions. All five plans reject 30-minute cycles so no IO
quarter-hour netting is inferred. No live data request is made by these tests.
The parent candidate validation separately records browser/API,
historical-weather studies and OpenDSS results; this focused count is not a
claim of those workflows.
GUI development/tests remain paused. Nothing was staged, committed or pushed.
