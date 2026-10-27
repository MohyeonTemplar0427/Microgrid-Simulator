# JCP&L New Jersey supply evidence

Reviewed October27,2026. Scope: **Jersey Central Power & Light Company,
BPU No.14 PartIII, ordinary RS and secondary GS full-service BGS-RSCP**.
Alternative suppliers, CIEP, TOU/GST, special water heating, lighting and export
settlement are excluded. PLS assignment, monthly measured demand, utility
territory, retail jurisdiction and PJM market metadata remain separate facts.

## Preserved source packet

Delivery research owns all15 adopted PartIII book originals from the official
[tariff index](https://www.firstenergycorp.com/customer_choice/new_jersey/new_jersey_tariffs.html).
Supply reused them without duplicate downloads. Exact original URL/SHA256,
physical pages and scoped text are in ignored
`.cache/jcpl_new_jersey/sources/supply/shared_tariff_receipts.json`.
`supply_snapshots.json` gives literal energy, reconciliation, per-owner TEC
components and sums, base transmission, effective dates and assigned-PLS year
for every snapshot. Physical pages vary: printed41/42 are physical42/43 in
73-page books and48/49 in81-page books. Four adopted tariff-page renders and
the PTC render were visually checked; PDF originals remain immutable.

These are actual adopted tariff leaves with approval/effective footers, not
auction prices or proposed retail conversions. Missing bill/settlement rules
cannot be supplied by the existence of a rate snapshot.

## Literal component tables

All amounts below are **dollars/kWh**, inclusive of published NJ SUT. Summer
June–September, winter October–May. RS summer is a marginal first600kWh and
excess600kWh block; winter RS and ordinary GS are flat within season.

| Explicit service-rendered energy window | RS summer first600 | RS summer excess600 | RS winter | GS summer | GS winter | PLS reference for GS |
|---|---:|---:|---:|---:|---:|---|
| Jun1,2024–May31,2025 |.092332|.101557|.101010|.095517|.095073|Nov1,2023|
| Jun1,2025–May31,2026 |.125888|.135113|.136817|.124982|.124626|Nov1,2024|
| Jun1,2026–May31,2027 |.128815|.138040|.141185|.124922|.124319|Nov1,2025|

The energy leaf includes energy, generation capacity, ancillary services and
related cost. No separate CIEP $/kW-day capacity or LMP charge belongs in RSCP.
No standalone administrative adder is published for these RSCP rows. Use the
inclusive charges directly rather than inventing an administrative component.

| Reconciliation service period | RS/GS charge, credit negative |
|---|---:|
| Dec2024–Feb2025 |-.004426|
| Mar–May2025 |.001036|
| Jun–Aug2025 |.000039|
| Sep–Nov2025 |.002501|
| Dec2025–Feb2026 |-.009951|
| Mar–May2026 |.000000|
| Jun–Aug2026 |.004441|
| Sep–Oct2026 reviewed scope |.008040|

Quarterly true-ups are explicit. A later sheet date changing TEC does not reset
an unchanged reconciliation rate: the September15,2025 and October1,2026 leaves
retain the preceding September rate. Adjacent CIEP reconciliation is excluded.

| Base transmission window | RS and GS all imported kWh |
|---|---:|
| Jun1,2024–Apr30,2025 |.012709|
| May1,2025–Jul14,2026 |.014877|
| From Jul15,2026, through reviewed Oct2026 |.017244|

This is a per-kWh charge for these secondary schedules, not assigned capacity,
PJM wholesale price or monthly demand. RMR is explicitly .000000/kWh effective
September1,2019. Demand/minimum charges in GS delivery are separate and owned
by delivery research.

| All-active TEC sum window | RS/GS total |
|---|---:|
| Sep1,2024–Apr30,2025 |.004071|
| May1,2025–Sep14,2025 |.004335|
| Sep15,2025–Jul14,2026 |.004339|
| Jul15,2026–Sep30,2026 |.004065|
| From Oct1,2026, reviewed scope |.004059|

**Sum every retained dated TEC block once.** Different effective-date blocks
contain different transmission-owner surcharges; the newest block does not
replace all earlier blocks. The packet preserves each owner/value/date and
uses Decimal sums. Each snapshot's19/20/21 extracted TEC rows was count-checked
against every printed `-TEC surcharge of` occurrence. SUT is explicitly included
in energy, reconciliation, base transmission, RMR and TEC. No extra SUT
multiplier is added. Customer/distribution CBT is a separate published tariff
inclusion and is not reconstructed as a supply adder.

## Enrollment and dated transitions

RS is BGS-RSCP eligible. GS must be utility-assigned secondary service with
annual generation-capacity **PLS strictlybelow500kW at the exact November1 date
shown in the annual energy leaf**, plus actual retained RSCP assignment.
PLS>=500kW mandates CIEP. Eligible GS may elect CIEP by the second business day
of January, effective June1 for the following12months. Returning to RSCP needs
the same January notice for a June1 return. A low study peak or utility ZIP
cannot establish historical PLS, election status or GS nondemand billing.

September15,2025 changes only named TEC rows, total+.000004/kWh. Base
transmission .014877, annual energy and September1 reconciliation .002501 remain
unchanged. July15,2026 changes base transmission and named TEC rows; annual
June1 energy and reconciliation .004441 remain unchanged. Both intramonth
supply transitions are **linear imported-kWh components**. The TEC text says
Effective[date], applicable to allkWh, and no bills-rendered override was found.
The energy leaf expressly uses service-rendered dates. Tax research's sourced
PartII§3.07 service-effective rule can therefore support actual interval import
allocation at these dates; do not substitute a days-weighted monthly average
or prorate whole-cycle600kWh/1000kWh blocks. Billing-period, demand eligibility,
DER and tier/charge rules must independently pass the other source streams.

## Independent primary checks and limits

The official [PTC PDF](https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/New%20Jersey/PriceToCompare.pdf)
was preserved and visually read; it is explicitly **effective September1,2026**.
It independently includes reconciliation and transmission with all TEC:

- Transmission .017244+.004065=.021309.
- RS summer first600 .128815+.021309+.008040=.158164; excess .167389.
- RS winter .141185+.021309+.008040=.170534.
- GS summer .124922+.021309+.008040=.154271; winter .153668.

These match the separate official PTC literals exactly. The PDF is mutable;
its saved September identity is retained. October TEC is lower by.000006/kWh,
so the September PDF is not an exact October-price benchmark. PTC checks supply,
not customer/distribution/riders or a complete invoice.

Three independently published BPU650kWh transmission impacts are preserved:

- [April23,2025 order, effective May1](https://www.nj.gov/bpu/pdf/boardorders/2025/20250423/2O%20ORDER%20%20January%202025%20TEC%20Filing.pdf):650×[(.014877+.004335)−(.012709+.004071)]=$1.58080, matching+$1.58.
- [June30,2026 order, effective July15](https://www.nj.gov/bpu/pdf/boardorders/2026/20260630/2B%20ORDER%20March%202026%20TEC%20Filing.pdf):650×[(.017244+.004065)−(.014877+.004339)]=$1.36045, matching+$1.36.
- [September24,2026 order, effective October1](https://www.nj.gov/bpu/pdf/boardorders/2026/20260923/2P%20ORDER%20July%2026%20NITS%20TEC.pdf):650×(.004059−.004065)=−$.00390, rounded$0.00, consistent with published nochange.

These verify transmission changes only. A third-party lead describes an
August6,2026 testimony MonthlyBillComparison excluding BGS reconciliation;
its actual primary original was not recovered in the bounded targeted pass.
No quoted third-party total is used as a verified whole-bill fixture. The
absence of a recovered benchmark is not proof no original exists. Auction
tranche prices, proposals and LMPs are not retail replacements. Source research
alone proves neither complete bill scope nor engine/solver/OpenDSS/browser
acceptance; those require separately pinned checks.
