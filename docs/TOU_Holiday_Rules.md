# TOU holiday rules

Reviewed October 14, 2026. This correction changes period classification, not
rate amounts, eligibility, rate-version identifiers, or verified date coverage.
It applies to the shared Python backend used by local browser and desktop
studies. Pinned/released engines retain their own code until separately promoted.

## PG&E E-TOU-D

Peak is 17:00 inclusive through 20:00 exclusive on non-holiday weekdays.
All other intervals are off-peak. The holiday list is New Year's Day,
Presidents Day, Memorial Day, Independence Day, Labor Day, Veterans Day,
Thanksgiving and Christmas. Fixed-date Sunday holidays are observed Monday;
Saturday holidays do not create a Friday holiday. MLK Day, Juneteenth,
Columbus Day and the day after Thanksgiving are not added to this list.

Evidence and version applicability:

- [PG&E Advice 5655-E](https://www.pge.com/tariffs/assets/pdf/adviceletter/ELEC_5655-E.pdf),
  approved effective May 1, 2020: attachment 2, E-TOU-D special condition 1,
  establishes the eight holidays and non-holiday weekday peak.
- [PG&E Advice 7846-E](https://www.pge.com/tariffs/assets/pdf/adviceletter/ELEC_7846-E.pdf)
  and the [current E-TOU-D schedule](https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_E-TOU-D.pdf),
  sheet 4: revised sheet 61137-E, effective March 1, 2026, replaces original
  sheet 46544-E and retains those time-period conditions. The 2026 rate change
  does not introduce a new holiday calendar.
- [PG&E TOU holiday calendar](https://www.pge.com/tariffs/en/rate-information/tou-holidays.html)
  supplies the Sunday/Saturday observation convention and dated tables. Its
  introductory text describes non-residential TOU calendars and contains a
  broad statement excluding residential weekday holidays. That statement
  conflicts with E-TOU-D's explicit filed conditions and PG&E's
  [E-TOU-D customer description](https://www.pge.com/en/account/rate-plans/time-of-use-rate-plans.html).
  The filed schedule controls whether this calendar applies; this implementation
  attaches it only to E-TOU-D, not all PG&E schedules.

The same calendar is attached to every implemented E-TOU-D version:
January, March, April, June, July, September and October 2024;
January, March and September 2025; January 2026; and all three June 2026
income-tier variants. Each still selects its own dated rates. The existing
March–May 2026 rate-data gap remains an error, including Memorial Day.
Calendar tests for older observed dates are not evidence of rate coverage
before 2024.

## Schedules that retain every-day periods

The generic model has no implicit federal, ISO, state or utility calendar.
These PG&E schedules remain unchanged:

| Schedule | Official time-period evidence | Behavior |
| --- | --- | --- |
| [E-TOU-C](https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_E-TOU-C.pdf) | Special condition 2, all days | 16:00–21:00 peak even on holidays |
| [EV2](https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_EV2%20%28Sch%29.pdf) | Special condition 1, every day | Peak and shoulders retain holiday pricing |
| [E-ELEC](https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_E-ELEC.pdf) | Special condition 1, every day | Peak and shoulders retain holiday pricing |
| [B-1](https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-1.pdf), [B-6](https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-6.pdf), [B-10](https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-10.pdf), [B-19](https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-19.pdf), [B-20](https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-20.pdf) | Their time-period definitions include weekends and holidays | Energy and applicable demand windows remain active on holidays, including Option R/S |
| E-1 | Tiered energy, no TOU peak | Holiday classification does not change billing |

The existing SCE/SDG&E, municipal/NERC, Burbank and other utility calendars
are not replaced. For example, NERC omits Presidents Day and Veterans Day;
Burbank includes additional holidays. Even the existing SCE helper retains
both the actual Sunday and its observed Monday, whereas the PG&E calendar
returns the published observed date. Sharing a national calendar would lose
these distinctions. This change is not a fresh audit of all other utilities.

## Shared implementation and checks

`HolidayCalendar` carries a name, an annual date function and source URLs.
`holiday_treatment` on both `TimeOfUsePeriod` and `TOUPeriod` supports:

- `regular`: apply the existing weekday restriction.
- `exclude`: exclude holidays from the normal weekday selection.
- `include`: include holidays in addition to the selected weekdays.
- `only`: select holidays independently of weekday.

The latter three require an explicit calendar. `TimeOfUseSchedule` and
`TariffDefinition` compute a local-date mask and use the same day predicate.
Wrapped periods use each interval's local date, not the date of the previous
evening. Adjacent-year holiday dates are consulted for calendars whose
observation crosses New Year. Repeated DST intervals are retained.

Billing's period names, energy component categories and demand bases share
this predicate. The existing demand optimizer consumes `demand_basis_for`;
it therefore sees the same holiday exclusions as the final bill. E-TOU-D has
no demand charges; demand-calendar tests use a clearly synthetic tariff.

`test/test_tou_holidays.py` checks published date tables; Sunday observation;
Saturday non-observation; excluded federal holidays; every implemented
E-TOU-D version's interval rates and bills; a Labor Day rate-change boundary;
season changes; DST days; effective-date rejection; midnight and 17:00/20:00
boundaries; explicit-calendar errors; daily/monthly peak and part-peak demand
objective reconciliation; E-TOU-D dispatch and bill agreement; and unchanged
every-day PG&E tariffs. Generic calendars require explicit configuration;
this work does not automatically assign a calendar to custom user schedules.
