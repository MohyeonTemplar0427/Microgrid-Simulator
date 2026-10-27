# Atlantic City Electric New Jersey supply evidence

Reviewed October27,2026. Scope: **Atlantic City Electric Company (ACE), New
Jersey BPU No.11, RS residential and MGS-Secondary on BGS-RSCP**. Delivery
schedule, BGS assignment, annual generation-capacity peak load share (PLS),
retail jurisdiction and PJM/wholesale metadata are separate facts. CIEP,
third-party supplier, RS-TOU, EV-ERR, MGS-SEVC and export settlement are excluded.

## Source packet and initial cycle boundary

Delivery research owns the original full SectionIV books. Supply reuses them,
without duplicate downloads. Exact URLs, original/fulltext SHA256s, selected
physical pages, scoped excerpts and three visually inspected BGS-page renders
are pinned in `.cache/atlantic_city_electric/sources/supply/shared_tariff_receipts.json`.
`supply_snapshots.json` in the same directory contains five fixture-ready
literal component/date/page/eligibility objects: February2025, June2025,
October2025, September2026 and October2026. Dates below describe each adopted
leaf; a snapshot is not automatic authority for every intervening month.

Initial implementation accepts **exactly30 consecutive complete local days
wholly within one adopted component regime and season**. Non30-day, partial,
season-crossing and mid-regime cycles reject while SectionII6.5 allocation is
unverified. The September15,2025 transmission/TEC and July15,2026 TEC changes
must not be silently assigned across a calendar month. Whole-year2025/2026
billing coverage is not established by this packet.

## Literal supply components

All energy/reconciliation/TEC values are **dollars/kWh**. Summer is June through
September; winter October through May. RS summer energy is marginal first750kWh
and excess750kWh blocks. RS winter and MGS-Secondary are flat energy within
season. Source physical71/72/74 in the2025 books and52/53/55 in2026 books.

| Adopted generation leaf | RS summer first750 | RS summer excess750 | RS winter | MGS-S summer | MGS-S winter |
|---|---:|---:|---:|---:|---:|
| June1,2024, Feb2025 book |.089677|.099264|.094339|.092976|.091262|
| June1,2025, Jun/Oct2025 books |.130407|.140360|.139134|.121496|.114061|
| September1,2026, Sep/Oct2026 books |.130325|.140300|.140672|.119776|.113017|

| Adopted reconciliation leaf | RS and MGS-S |
|---|---:|
| October1,2024, Feb2025 book |-.005854|
| June1,2025, Jun2025 book |.004652|
| October1,2025, Oct2025 book |.009954|
| September1,2026, Sep/Oct2026 books |.000000|

2025 RiderBGS sheet60a changes normally June1/October1. The adopted2026 sheet43a
states quarterly June1/September1/December1/March1. Do not borrow PSE&G's
quarterly history or conflate ACE's adjacent **CIEP** sheet60b/43b with RSCP.
For example, October2025 RSCP reconciliation is .009954, while the excluded
CIEP secondary reconciliation is .003950.

| Adopted TEC leaf | RS total | MGS-S total |
|---|---:|---:|
| September1,2024, Feb2025 book |.002709|.002031|
| May1,2025, Jun2025 book |.002997|.002144|
| September15,2025, Oct2025 book |.002979|.002027|
| July15,2026, Sep2026 book |.003144|.001862|
| October1,2026, Oct2026 book |.003174|.001905|

TEC is the **published total**, added once. Its individual transmission-owner
rows must not be added again to that total. Federal transmission projects and
PJM allocation metadata do not change the tariff's separate retail role.

| Adopted transmission leaf | RS all kWh $/kWh | MGS-S summer $/kW above3kW | MGS-S winter $/kW above3kW |
|---|---:|---:|---:|
| September1,2024, Feb/Jun2025 books |.041092|8.24|7.86|
| September15,2025, Oct2025 book |.035260|5.92|5.53|
| December1,2025, Sep2026 book |.035260|5.92|5.53|
| October1,2026, Oct2026 book |.037688|6.88|6.49|

Transmission is on RS physical7; MGS-S physical16 in2025 and12 in2026. All
snapshots explicitly show reliability-must-run surcharge .000000/kWh. MGS
transmission demand is not PLS and not a flat per-kWh comparison-table rate.
Delivery research owns rounded billing-demand calculation and its exclusions.

Generation energy includes energy, generation capacity, ancillary services,
administrative charges under N.J.S.A.48:2-60 and NJ Sales and Use Tax (SUT).
Reconciliation explicitly includes SUT. TEC explicitly includes statutory
administrative charges and SUT. Schedule RS/MGS also states its rates contain
tax components. No second SUT/admin multiplier is added to these published
figures; no missing administrative rate is fabricated.

## PLS and enrollment rules

The adopted BGS leaf offers RS ordinary BGS-RSCP. For MGS-S, **utility-assigned
annual PLS for generation capacity strictlybelow500kW as of November1** permits
RSCP; PLS>=500kW mandates CIEP. Below500 customers may elect CIEP. Election must
reach ACE by the **second working day of January**, takes effect June1, and
remains the default supply for12months. A prior CIEP customer eligible to return
to RSCP must give the same January notice for a June1 return. Require actual
retained RSCP assignment and relevant annual PLS evidence; a study's monthly
15-minute demand cannot prove PLS or annual enrollment status. Later snapshots
repeat the same rule. No auction tranche closing price is used as a retail
energy charge.

## Independent checks, scope and gaps

Official NJBPU [September24,2026 transmission order](https://www.nj.gov/bpu/pdf/boardorders/2026/20260923/2P%20ORDER%20July%2026%20NITS%20TEC.pdf),
DocketER26070406, physical2, approves October1 changes and gives ACE650kWh
monthly impact **+$1.60 including SUT**. Saved `order_2026_tec.pdf/.txt`:
`650*((.037688+.003174)-(.035260+.003144))=$1.59770`, cent-rounded $1.60.
This independently checks the transmission change, not the whole bill.

Official ACE [residential](https://www.atlanticcityelectric.com/my-account/my-service/customer-choice/price-to-compare-residential)
and [business](https://www.atlanticcityelectric.com/my-account/my-service/customer-choice/price-to-compare-business)
PTC content and linked September29,2026 image originals are preserved in
`supply_records.json`. The residential image shows winter energy14.07c,
transmission including TEC4.09c, reconciliation0 and total18.16c/kWh. Raw
October tariff sum is .140672+.037688+.003174=.181534 dollars/kWh; the displayed
sum differs0.0066cent/kWh because published components have been rounded.
Use tolerance0.01cent for this comparison, not an exact rounded-invoice claim.
The business PTC uses class-average transmission in cents/kWh, which must not
replace MGS's account-specific $/kW demand charge. Both page headings retain
stale “Effective7/15/26” text while linked image names are09-29-26; preserve this
source inconsistency and use actual adopted tariff clocks. Do not backdate the
images. Official BPU February12,2026 auction-release650kWh whole-bill estimates
and tranche prices are context, not adopted monthly retail components.

Missing adopted31st/32nd BGS generation leaves and intervening2026
reconciliation/TEC updates prevent June–August2026 extension. Retain each
component's separate clock; no current-rate backdating, neighboring-utility
substitution, inferred zero or projected auction conversion fills a gap.
2025 January–May supply is grounded in older adopted leaves preserved in the
February book; tax/delivery/account adjustments still determine executable
intersection. Legislativecredits/deferral and final quantity-rounding rules
belong to tax/delivery research. Source literal/rounded final invoice checks do
not prove the raw-quantity objective is an exact cash-bill optimum.
