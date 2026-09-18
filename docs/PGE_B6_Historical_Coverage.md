# Historical PG&E B-6 coverage

The September 1–December 31, 2025 bundled secondary B-6 versions cover
single-phase and polyphase accounts. Source: [PG&E historical commercial B
workbook](https://www.pge.com/assets/rates/tariffs/Commercial_B_Sch_250901-251231.xlsx),
listed under that date range on [PG&E's rate archive](https://www.pge.com/tariffs/en/rate-information/electric-rates.html).

The first worksheet's C16:C17 gives daily customer charges of $0.32854 and
$0.82136, respectively. J15:J19 gives summer peak/off-peak energy rates
$0.67220/$0.41458 and winter peak/off-peak/super-off-peak rates
$0.42551/$0.38192/$0.34584 per kWh. There is no demand charge.
The workbook's final worksheet verifies 4–9 pm peak every day, summer
June–September, winter October–May, and 9 am–2 pm super-off-peak only in
March–May (outside this version's coverage).

These are base bundled rates: PDP events/credits, CCA, direct access,
standby, and export compensation remain excluded. Account eligibility must
be confirmed; this addition does not broaden eligibility.

Web Billing Plan choices disable versions outside the selected dates, and
API validation rejects unsupported horizons before queueing. One selected
version must cover the entire inclusive study horizon. This is not automatic
multi-version billing. Earlier periods, January–February 2026, and historical
versions of other plans still require separate verification and implementation.
Both desktop and web use the same registered rates; site-generated dispatch
prices and bill reconciliation use the selected version.
