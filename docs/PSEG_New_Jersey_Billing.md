# PSE&G New Jersey billing candidate

Verified October 15, 2026. PSE&G in **New Jersey** is distinct from PSEG Long
Island. Retail delivery, default supply, PJM market identity and representative
electrical validation remain separate inputs. A state, ZIP or pricing node does
not establish that an address receives PSE&G service.

## Executable schedules and eligibility

| Plan ID | Filed service | Supply | Eligibility and measurements |
|---|---|---|---|
| RS | Ordinary residential | BGS-RSCP | Summer first 600/excess kWh blocks; no demand charge |
| RS_TOU_3P | Optional residential three-period TOU | BGS-RSCP | Introduced December 8, 2025; on-peak weekdays 16:00–21:00 except PJM holidays; off-peak 00:00–06:00; mid-peak otherwise |
| GLP | General lighting and power, secondary | BGS-RSCP or elected BGS-CIEP | Measured 30-minute maximum; at most 150 kW; utility-installed capacity at most 400 kW; additional prior-LPL transfer restrictions |
| GLP_NIGHT | GLP Night Use | BGS-RSCP or elected BGS-CIEP | Confirmed two-year enrollment and time-of-day meter; weekday 08:00–20:00 day period; summer demand measured during day period |
| LPL_S | Large power and lighting, secondary | BGS-RSCP if eligible PLS<500kW; otherwise BGS-CIEP | 30-minute all-hours maximum plus summer weekday 08:00–22:00 maximum; existing tariff eligibility held across counterfactuals |
| LPL_P | Large power and lighting, primary | BGS-CIEP | 15-minute all-hours maximum and summer weekday 08:00–22:00 maximum |
| HTS_SUB | High tension, subtransmission | BGS-CIEP | 15-minute monthly demand; annual-demand ratchet includes current and preceding 11 months; summer on-peak demand |
| HTS_HV | High tension, high voltage | BGS-CIEP | 15-minute demand and annual-demand ratchet; no invented summer charge |
| RHS | Residential Heating, closed | BGS-RSCP | Existing eligible all-electric heating premise only; winter delivery blocks decline after 600 kWh |
| RLM | Residential Load Management, closed | BGS-RSCP | Existing enrolled premise only; filed weekday 07:00–21:00 **EST**, including summer; no invented holiday exclusion |
| HS | Building Heating, closed | BGS-RSCP | Existing comfort-heating account only; separately elected hourly HS not enabled without its account-obligation treatment |

All executable versions cover billing dates January 1, 2025–October 15, 2026,
except RS_TOU_3P, which begins at its actual inception. Current rows in the
runtime catalog distinguish supported and unavailable arrangements and carry
coverage, source, eligibility and required-account fields. Availability in that
catalog alone does not establish that a browser submission or full-year study
has been tested; see the combined regional acceptance report for those results.

Separate appliance meters WH/WHS, historical HTS transmission conversions,
traction service, DC-fast-charging special provisions, negotiated facilities,
area-development discounts, religious/veterans discounts, curtailable service,
duplicate facilities, tax exemptions and seldom-use annual-minimum accounts
remain separately identified and unavailable in this ordinary-account path.
An incomplete third-party supply contract is rejected instead of substituting
PSE&G default supply or a convenient wholesale price.

## Official evidence and independently dated components

The [official tariff index](https://nj.pseg.com/aboutpseg/regulatorypage/electrictariffs)
links the current B.P.U.N.J.No. 17 book, its
[prior full revisions](https://nj.pseg.com/aboutpseg/regulatorypage/electrictariffs/bpunjno17),
and separate
[2025](https://nj.pseg.com/aboutpseg/regulatorypage/electrictariffs/2025monthlyelectricreconciliationcharges)
and [2026](https://nj.pseg.com/aboutpseg/regulatorypage/electrictariffs/2026monthlyelectricreconciliationcharges)
quarterly BGS reconciliation sheets. The reconciliation sheets are deliberately
absent from full ratebooks; omitting them would understate or overstate supply.

`src/billing/pseg_rates.py` freezes 16 complete dated 2025–2026 ratebook
revisions and 8 quarterly reconciliation revisions into the immutable Python
engine snapshot. Source URLs, original-document SHA256 hashes, retrieval date,
filed sheet effective dates and actual PDF-page references accompany the rates.
`docs/utility_sources/pseg/manifest.json` retains document identities;
`sheets.json` retains 292 deduplicated relevant official sheet texts and maps
them to their original ratebooks/pages. `quarterly_sources.json` retains the
separate quarterly sheet text. The original source PDFs are not added to Git.
`tools/compile_pseg_rates.py` verifies all 16 frozen ratebooks against the retained
official text without network access. It checks sheet hashes and preserves
thousands separators, including the HTS subtransmission $2,038.02 and
high-voltage $1,834.22 monthly customer charges. Default operation only checks;
rewriting the reviewed ratebooks requires its explicit `--write` option.

The 2025 books document changes effective January 1, February 15, March 1,
May 1, June 1, July 1, September 15, October 1, December 1 and December 8.
Quarterly reconciliation also changes September 1 and December 1. Each source
component remains associated with its own effective date; a new supply filing
does not retroactively replace delivery, tax or rider histories.

Included bill lines are customer/distribution charges, applicable demand,
Societal Benefits, Non-utility Generation, Zero Emission, Solar Pilot, Green
Programs, Conservation Incentive, COVID recovery, Tax Adjustment Credit,
supply energy/capacity/transmission and quarterly supply reconciliation.
Infrastructure Improvement Program charges are **already included** in filed
distribution rates and are not added a second time. Published SUT-inclusive
rates are used directly; multiplying the bill by 1.06625 again would double tax.

Residential sheet68 grants a $30 monthly credit in July–August 2025 and
collects $10 monthly in September 2025–February 2026. This separately
identified temporary credit/recovery follows the residential service-charge
minimum. Thus a zero-import July 2025 bill can carry a $24 net credit; the
model does not erase the filed credit by imposing a second minimum afterward.
Commercial schedules instead describe a specially applicable seldom-use
**annual** minimum; they do not establish the residential monthly cash floor.

## Actual meter cycles and seasonal/rate selection

Standard Terms 9.6 defines a month by successive scheduled meter readings.
Rule 9.10 ordinarily applies amended charges to the first regular bill on/after
the filed effective date, including service after the preceding scheduled read.
Therefore the account supplies both its **utility-designated billing month**
and **bill date**; the model does not split a complete bill into calendar-month
sub-bills or blindly blend changes by service day.

Rule 9.7 leaves normal 25–36 day bills unprorated. Initial/final or outside-range
cycles require the documented billing-month day denominator for fixed/demand
charges. RS/RHS partial-cycle 600 kWh block allocation is not separately
specified in the verified filing. Without a utility-confirmed
`residential_tier_block_factor`, confirmation and source, the model provisionally
scales that block by the same day factor, flags the interpretation and returns
`is_complete_bill=False`. Confirmed block allocation is independent of the
fixed-charge factor. Full calendar bills are unchanged. The model does not
invent a universal 30-day denominator. Temporary service and a
BPU order overriding normal applicability need a separate verified model.
Complete local service days are required; UTC spacing preserves 92/100-interval
DST days. A shorter incomplete data file is never treated as a smaller bill.

GLP/LPL secondary demands average aligned 30-minute blocks. Primary/HTS
requires actual 15-minute observations; hourly data cannot establish them.
The tariff's special 5-minute violent-fluctuation and traction-hour provisions
are not approximated from coarser data. GLP estimated demand=kWh/100 is
available only for an explicitly enrolled low-use account with the required
history; it is not a replacement for a missing measured peak.

## Supply obligations and CIEP prices

Residential BGS-RSCP energy rates already include generation capacity, and
separate filed per-kWh transmission charges recover that component. No PJM
capacity auction charge, monthly meter maximum or wholesale LMP is added.

GLP and LPL secondary RSCP instead have a filed per-kWh energy charge and
two **different utility-assigned kW obligations**: generation and transmission.
The account provides both values, their source and their applicable period.
They are not estimated from this month's peak, and storage cannot change an
already assigned obligation retroactively. LPL default-supply eligibility uses
the customer's November 1 Peak Load Share for the following June 1 supply
year; optional CIEP enrollment follows the filed January election deadline.
The account's existing confirmed enrollment is held across scenarios.

PSE&G's
[official CIEP methodology slideshow](https://nj.pseg.com/-/media/pseg/public-site/documents/ciep/webciep-slides-for-website-for-06-01-2023.ashx)
shows PJM pricing node **116472957 / PSEG_RESID_AGG**, native type
**RESIDUAL_METERED_EDC**, and a **blank native zone field**. The separate
retail-account transmission zone is PSEG. This is real-time load-weighted
residual-metered-load aggregate LMP, not Western Hub, generic PSEG zonal LMP,
day-ahead energy, or a three-year auction result.

`pseg.import_ciep_prices` calls the existing
`PJMProvider.import_historical_file`. The same strict importer validates UTC,
current revisions, node/name/native zone, gaps, units and internal-use
permission. CIEP additionally requires the residual EDC type. Private
`account.market_data={csv_text,metadata}` uses the existing PJM metadata keys:
`market=REAL_TIME_HOURLY`, official`source_url`, offset-aware`retrieved_at`,
`unit=$/MWh`, and`usage_permission=internal_use_only`. Missing data reject
CIEP and do not block independent RSCP studies. Raw licensed price rows remain
private, and provenance explicitly disables public download redistribution.

The [official worked Excel example](https://nj.pseg.com/-/media/pseg/public-site/documents/ciep/bgs-ciep_calculations_worksheet-june-2023.ashx)
defines loss expansion as `(1-mean_PJM_marginal_loss)/(1-tariff_loss)`.
Filed mean marginal losses are 0.79690% before June 2025,0.91210% from
June 2025 and 0.92504% from June 2026. Tariff losses are 5.8327% secondary,
3.3153% primary,2.0472% subtransmission and0.8605% high voltage.
The worked methodology rounds the loss expansion and successive unit-charge
stages to six decimals using Excel `ROUND`, with midpoint ties away from zero
for positive and negative prices. The implementation uses decimal
`ROUND_HALF_UP`, rather than binary ties-to-even. Energy and the $0.006/kWh ancillary charge are adjusted
for those losses and SUT; filed generation/transmission obligations, CIEP
standby and quarterly reconciliation are added separately. This does not add
the same capacity or transmission charge twice.

## PV, storage and net metering

Utility-approved parallel operation is required even for no-export studies.
No-export schedules curtail surplus; exports are not treated as free disposal.
Commercial self-generation reaching 50% of annual peak can trigger standby
demand rules. The implementation conservatively requires appropriate
classification when configured PV plus storage output cannot be proven below
that threshold using supplied history. This is a study eligibility check, not
a utility interconnection approval or an assertion that every battery has the
same enrollment treatment. In standby treatment the annual charge uses the
current/prior 11-month ratchet, and the summer peak uses the customer's demand
within the **actual PSE&G distribution-system monthly peak hour**. That hour
needs explicit utility evidence and covered meter data; a PJM zone peak or
the customer's own maximum is not substituted. Histories evolve through
`next_state`, rather than resetting monthly.

Standard Terms 15 and the
[official net-metering explanation](https://nj.pseg.com/saveenergyandmoney/solarandrenewableenergy/netmetering)
support approved Class I renewable systems sized within annual electricity
needs. Community-solar enrollment is incompatible. Net kWh credits carry
forward; every TOU period has its own bank and cannot offset another period.
The account's anniversary closes its annualized period. Demand measurement and
fixed capacity/transmission obligations remain based on their original rules,
even when energy credits reduce billed kWh to zero.

An anniversary surplus is purchased at verified avoided wholesale power cost,
not retail rates. The exact class/voltage/date-specific avoided-cost rate is a
required sourced account input when a surplus remains. The separately listed
PEP qualifying-facility rates are not assumed to be this NEM rate. Without
verified payout evidence, numeric positive-bank true-up rejects and optimization
explicitly constrains its ending bank to zero. This permits supported
net-import cases without inventing a payout. CIEP hourly NEM settlement is not
enabled; its account-specific credit allocation still needs verification.
New Jersey SREC/SuSI incentives are not automatically added to utility savings.

The operating objective defaults to excluding inherited credits, following the
project's existing policy. `objective_inputs` copies and zeros only opening
credit banks; demand history and fixed obligations remain intact. The cash bill
then uses actual inherited balances. An advanced explicit-cash-bill policy is
separate. Annual orchestration must identify whether it is rolling horizon and
must propagate SOC and closing ledger state; monthly resets are not an annual
optimum.
An inherited positive NEM bank cannot silently enter non-export mode. Both
account and carried-state inputs reject that unsupported program transition;
its settlement requires explicit treatment rather than dropping the balance.

## Validation and historical research limits

Offline tests are in `test/test_pseg_billing.py`. Independent source arithmetic:

| Case | Inputs | Unrounded result |
|---|---|---:|
| January 2025 RS | 744 kWh; filed January components and December2024 reconciliation | $163.341120 |
| July 2025 RS | 744 kWh;600/excess blocks; temporary $30 credit | $198.240240 |
| July 2025 GLP | 14,880 kWh, 20 kW measured peak,15/16 kW generation/transmission obligations | $2,683.132340 |
| Official CIEP worksheet | 33.278903 $/MWh; 30 kWh; secondary losses; 0.79690% marginal losses | $1.323660 energy plus ancillary |

Tests also cover current and historical structures, effective dates, closed
enrollment, independent quarterly changes, bill-date applicability, proration,
DST, EST/EPT, PJM holiday exclusions versus unaffected weekday tariffs,
averaged demand, ratchets and coincident-hour requirements, obligations,
negative/absent/incorrect price data, credit banks and expiry, object immutability
and authoritative numeric/MILP reconciliation. Run:

```sh
/usr/local/bin/python3 -m pytest -q test/test_pseg_billing.py
```

The rolling ten-calendar-year research target here is 2017–2026, bounded by
actual plan inception. Official prior booksNo. 15 andNo. 16 and quarterly
reconciliation indexes were located for 2017–2024 and recorded in
`docs/utility_sources/pseg/history_inventory_2017_2024.json`. Their complete
composite rates have **not been compiled or validated**; those dates reject.
This is outstanding implementation/research, not a claim that the filings are
unavailable. RS_TOU_3P begins December 8, 2025; predecessors are not silently
merged into it. A permitted official node 116472957 Data Miner export was
retrieved privately for 2025 and validated as 8,760 consecutive UTC hours,
including 23/25-hour spring/fall days and current revision 1. The unmodified
download includes the additional January 1, 2026 boundary hour; the importer
explicitly excludes it from the 2025 study. Raw rows, retrieval metadata and
file hashes remain under ignored `.cache/regional_historical_inputs/pseg`.
Input coverage and completed studies are recorded separately. The reproducible
regional driver subsequently completed monthly and full-year 2025 RS, GLP and
GLP CIEP studies, each comparing grid-only, PV-only and PV-plus-battery operation
with actual NSRDB weather and imported, explicitly synthetic native demand.
The final source-pinned evidence and private report locations are documented in
`docs/Regional_Validation.md`. Independent audits rebilled every cycle, checked
continuous SOC and actual history propagation, and replayed every scheduled
interval through the representative OpenDSS network. These non-export studies
do not validate an actual customer's bill or an annual solar payout. An annual
net-export payout
requires the missing verified account/class/voltage payout evidence described
above. Representative electrical replay cannot validate a real feeder,
protection system, transient response or hosting capacity.
