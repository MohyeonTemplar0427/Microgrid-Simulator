# Indiana Michigan Power · Michigan ordinary Standard Service

The adapter supports ordinary RS residential and non-demand-metered
secondary GS Standard Service. The selected plan IDs are `RS` and `GS`.
A separate account fact retains the exact utility code, 015/016 for RS
or 215/218 for GS. The rate books also list other codes, which this
initial scope does not enable.

The [source ledger](utility_sources/im_mi/sources.json) pins the reviewed
utility books and the MPSC's surviving superseded sheets. Source material,
including extracted text and cached regulator-table reviews, is retained
under `.cache/im_mi/sources`.

## Dates and billing clocks

Verified complete calendar cycles are January–April and June–December 2025,
and January–December 2026. May 2025 is blocked. The Tax Rider's body states
a bills-rendered basis while its revision footer starts service rendered
May 16, 2025. The initial implementation requires a complete cycle
wholly before or after that transition rather than choosing an allocation
rule. Partial cycles, cross-month readings and other dates reject.

Use complete consecutive 15-minute records in `America/New_York`.
The designated utility bill month and final-day bill date must match the
modeled calendar cycle. I&M's ordinary reading schedule is not necessarily
a calendar month. These are explicitly selected calendar study cycles
with full monthly charges.

| Component | Filed rate and effective boundary |
| --- | --- |
| RS base, D-2 | $7.58 delivery service charge; 3.156¢/kWh supply capacity, 8.675¢ non-capacity and 4.593¢ delivery, effective July 15, 2024 |
| Secondary GS without demand meter, D-19 | $8.36 service charge; first 4,500 kWh at 3.047¢ supply capacity, 7.486¢ non-capacity and 3.262¢ delivery |
| Actual PSCR, D-116 | 3.74 mills/kWh January–February 2025; 3.58 March–December 2025; 1.93 January–June 2026; −12.58 July–December 2026 |
| Rate Realignment, D-117 | RS/GS 0.0615/0.0567¢ through July 2025; 0.0507/0.0467¢ August 2025–July 2026; 0.0388/0.0358¢ from August 2026 |
| EWR, D-118 | RS 0.387¢/kWh and GS $13.42 in January 2025; RS 0.628¢ and GS $20.05 February–December 2025; RS 0.529¢ and GS $16.96 January–February 2026; RS 0.836¢ and under-10-kW secondary GS $8.09 from March 2026 |
| LIEAF, D-122 | $0.87 through August 2025; $1.25 September 2025–August 2026; $1.50 from September 2026 |
| Tax Rider, D-123 | Original RS supply/delivery credits −0.2392/−0.0570¢/kWh, GS −0.2421/−0.0474¢; zero credits after the May 16, 2025 revision |
| Other D-114 riders | Nuclear decommissioning, renewable energy and supply/delivery net lost revenue are separately itemized at filed zero rates |

The PSCR history uses the filed **actual factors billed**, including the
July 2026 reduction, and keeps that history separate from the authorized
maximum table. The 2026 utility book is MPSC No. 19, an accessibility
reissue of the existing rates; the surviving MPSC No. 18 sheets preserve
older factors and dates.

Michigan sales tax is 4% for ordinary residential use and 6% for ordinary
commercial use. The state Treasury's Letter Ruling 2013-5 excludes the
separately itemized LIEAF from the taxable subtotal. The rate-making Tax
Rider remains separate from state sales tax. The account must confirm
no exemption, franchise adjustment, additional local charge, special
facilities, assistance credit, primary-electric-heating provision,
water-heating rider, EV credit or other optional program.

## Eligibility and equipment

The initial replay scope is one 120/240 V single-phase secondary meter.
RS has a declared native/import study limit of 25 kW. GS has separate
native and imported-energy study limits of 9.49 kW and 4,500 kWh per
calendar cycle. These study bounds do not determine utility eligibility.

For GS, independently confirm I&M's retained non-demand-meter assignment,
the reviewed average monthly use below 4,500 kWh, an actual under-10-kW
maximum, and the secondary under-10-kW EWR assignment for each cycle.
D-20 requires demand metering at average usage of 4,500 kWh or greater
and permits metering below that threshold. The full GS tariff's demand
charge, ratchets and higher-energy blocks are outside this declared
scope. The no-demand-meter monthly service charge is $8.36. The
minimum includes that charge and all per-account riders.

PV and PV-plus-battery studies require final I&M interconnection approval
before the first service interval and a written special agreement for
the exact installation preserving all ordinary import billing terms.
RS D-5 and GS D-23 direct generating customers to the applicable NMS,
COGEN/SPP or a special agreement. The initial implementation models
the approved non-export special-agreement path only. Paired batteries
charge from PV and export no energy. Standalone storage and export
settlement reject.

I&M Michigan is both the distribution utility and Standard Service
supplier, with Michigan jurisdiction and PJM AEP metadata. Wholesale
pricing data is independent and adds no charge to these retail rates.

## Validation

The utility-specific development receipt is
[available locally](../.cache/im_mi/development/report.json).
The tests independently transcribe the filed rate vectors using Decimal
arithmetic across eleven dated intersections, verify numeric/symbolic
parity and fixed-charge minimums, exercise DST and missing/duplicate data,
and reject unsupported dates, settlement, eligibility and equipment
facts. The published I&M May 26, 2026 announcement independently
corroborates the approximately $14.50 per 1,000 kWh PSCR reduction.
The exact filed factor difference is $14.51 before sales tax.

No customer invoice was supplied. The independent component benchmarks
are calculations from separately transcribed source sheets. Final
worker, historical, electrical and browser acceptance belongs to the
batch candidate's implementation report.
