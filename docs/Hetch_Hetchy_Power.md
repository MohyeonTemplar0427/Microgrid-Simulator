# Hetch Hetchy Power retail C-1

The initial implementation covers retail small-commercial C-1, standard and
confirmed Premium enrollment. It does not represent residential, municipal
CG-1, Enterprise A-1U, medium/large commercial, industrial or special accounts.
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

Next extensions need their own published rates and eligibility mapping:
C-2S/C-2P monthly maximum demand, then larger TOU schedules (including Hetch
Hetchy's half-hour boundaries and holiday rules), residential tiers, and the
separate municipal/Enterprise families. No such tariff is approximated by C-1.
