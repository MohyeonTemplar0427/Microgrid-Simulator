"""Definitions shared by every PG&E schedule, commercial and residential.

Kept separate so the two rate families can live in their own modules without
either importing the other.
"""

from calendar import monthrange
from datetime import date, timedelta
from functools import lru_cache

from src.tou_calendar import HolidayCalendar
from .tariffs import SeasonDefinition

# Summer is June 1 through September 30; winter is October 1 through May 31.
# The same seasons apply to the B-series and to the residential schedules.
PGE_SEASONS = SeasonDefinition(summer_months=frozenset({6, 7, 8, 9}))


@lru_cache(maxsize=128)
def pge_tou_holidays(year: int) -> frozenset[date]:
    """PG&E's eight TOU holidays, on their tariff-observed dates.

    Sunday fixed-date holidays move to Monday; Saturday stays Saturday.
    This is not the federal employee calendar (no Friday substitution, MLK
    Day, Juneteenth or Columbus Day). Do not attach it to every-day tariffs.
    """
    fixed = (date(year, 1, 1), date(year, 7, 4), date(year, 11, 11), date(year, 12, 25))
    days = {d + timedelta(days=1) if d.weekday() == 6 else d for d in fixed}
    for month, weekday, occurrence in ((2, 0, 3), (5, 0, -1), (9, 0, 1), (11, 3, 4)):
        matches = [day for day in range(1, monthrange(year, month)[1] + 1)
                   if date(year, month, day).weekday() == weekday]
        days.add(date(year, month, matches[occurrence - 1] if occurrence > 0 else matches[-1]))
    return frozenset(days)


# E-TOU-D's original time-period conditions (5655-E, effective May 2020)
# retain this list in Sheet 4 (7846-E, effective March 2026). The TOU calendar
# specifies observance; its general residential exclusion is superseded by
# the explicit E-TOU-D tariff. See docs/TOU_Holiday_Rules.md.
PGE_TOU_HOLIDAYS = HolidayCalendar(
    name="pge_e_tou_d_eight_holidays_sunday_observed",
    dates_for_year=pge_tou_holidays,
    source_urls=(
        "https://www.pge.com/tariffs/assets/pdf/adviceletter/ELEC_5655-E.pdf",
        "https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_E-TOU-D.pdf",
        "https://www.pge.com/tariffs/en/rate-information/tou-holidays.html",
    ),
)
