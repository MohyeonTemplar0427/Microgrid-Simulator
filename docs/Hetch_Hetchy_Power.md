# Hetch Hetchy Power retail C-1 and C-2

Supported retail schedules are small-commercial C-1 and medium-commercial
C-2S/C-2P, Standard or confirmed Premium enrollment. Residential, municipal,
Enterprise, large-commercial, industrial and special accounts are excluded.
Coordinates suggest providers; users must confirm actual account eligibility.

Source: [SFPUC FY2026-27 Rate Schedules and Fees](https://www.sfpuc.gov/sites/default/files/accounts-and-services/Rates_Schedule_HHP_CleanPowerSF_2026-7.pdf),
reviewed September 16, 2026. Printed pages 1–2 describe classification and
seasons; page 12 gives C-1; page 32 gives Premium enrollment and surcharge.

- C-1 customer charge: $19.63/month.
- May–October: $0.39660/kWh, all hours.
- November–April: $0.31872/kWh, all hours.
- Optional Premium: $0.00950/kWh, confirmed enrollment required.
- No demand charge. Small commercial classification is below 75 kW.

Generation and delivery are already included. No PG&E generation replacement,
PCIA or franchise surcharge is added. The model preserves energy and Premium
as separate additive components. The same combined energy rate drives dispatch
and billing. Carbon remains the study's signal; product selection does not
silently change emissions.

## Billing scope

The catalog covers July 1, 2026–June 30, 2027. The source describes meter
readings on/after July 1; this model uses service dates and does not reproduce
actual meter-read transition bills. Monthly charges are exactly one published
charge per full calendar month, including February and 31-day months. Partial
months allocate the charge by covered local calendar dates divided by days in
that month, with an explicit approximation warning. This is a study convention,
not an asserted SFPUC proration rule. DST changes interval energy, not day count.

Taxes, special discounts, special contracts and NEM/export settlements are not
included. A simulation at or above 75 kW warns that C-1 eligibility requires
account review. SFPUC assesses the prior twelve months; it does not use PG&E's
three-consecutive-month rule, and simulated demand does not reassign a tariff.

## Use

Web: Electricity Service → Hetch Hetchy Power; Economics → C-1 Standard or
Premium enrolled. Incompatible providers' tariffs are hidden and rejected.
GUI: CAISO region → tariff pricing → Hetch Hetchy C-1. Although the generic
pricing selector says TOU, C-1 varies by season only. Results include the base
energy, optional Premium and separate customer charge. The representative
OpenDSS network remains a study assumption, not validation of the site's
actual service connection.

## C-2S / C-2P extension

Verified September 17, 2026 against the same official source: printed page 13
(rates), iv–vi (demand/voltage), 1 (classification), and 32 (Premium).

| Component | C-2S secondary | C-2P primary |
|---|---:|---:|
| Monthly customer charge | $350.00 | $350.00 |
| Summer energy, $/kWh | 0.24654 | 0.22247 |
| Winter energy, $/kWh | 0.19723 | 0.17798 |
| Monthly maximum demand, $/kW | 28.50 | 23.94 |

Medium-commercial demand is 75–500 kW. Classification considers the prior
12 months; exceeding the assigned maximum for more than three months triggers
subsequent transfer. The shared 500 kW boundary requires account confirmation.
Primary service is from a single customer substation or untransformed standard
primary voltage. Secondary is below 2,400 V or outside primary/transmission
definitions. The representative network does not establish service class.

The same FY coverage, Premium, exclusions and customer-charge approximation
above apply. Billing and optimization require 15-minute inputs. Each calendar
month incurs its full demand rate on its maximum import; a supplied earlier
peak floors the first month's peak. Unknown outside-study peaks may increase
actual charges. Demand is never prorated for partial studies.

Both interfaces use the shared registry and display schedule-specific notes.
Location studies optimize with tariff energy and demand costs; legacy CSV
studies retain their explicitly supplied energy prices. Fixed customer costs
do not change dispatch. Account eligibility is advisory, never reassigned.

Next: larger TOU schedules (half-hour boundaries and holidays), residential,
and separate municipal/Enterprise families. Export settlement remains excluded.
