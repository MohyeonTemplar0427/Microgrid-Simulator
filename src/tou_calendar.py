"""Explicit utility calendars shared by retail signals and billing periods.

There is no default national/ISO calendar. A tariff opts into a documented
calendar and specifies how each period treats its holidays. Calendar functions
return local dates for holidays originating in a year, including their own
observance rules; timestamps are never converted to UTC for day matching.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import AbstractSet, Callable

import pandas as pd


class HolidayTreatment(StrEnum):
    REGULAR = "regular"  # Apply the ordinary weekday restriction.
    EXCLUDE = "exclude"  # Ordinary days, excluding calendar holidays.
    INCLUDE = "include"  # Ordinary days OR calendar holidays.
    ONLY = "only"        # Calendar holidays, irrespective of weekday.


@dataclass(frozen=True)
class HolidayCalendar:
    name: str
    dates_for_year: Callable[[int], AbstractSet[date]]
    source_urls: tuple[str, ...] = ()

    def mask(self, timestamps: pd.DatetimeIndex) -> pd.Series:
        """Match local dates without discarding repeated DST intervals."""
        # Adjacent years include observed New Year's dates shifted across the
        # year boundary by calendars that use that convention.
        years = {int(year) + offset for year in timestamps.year.unique()
                 for offset in (-1, 0, 1) if 1 <= int(year) + offset <= 9999}
        dates = set().union(*(self.dates_for_year(year) for year in years))
        return pd.Series(timestamps.date).isin(dates)


def match_days(
    weekdays: pd.Series,
    days: frozenset[int],
    treatment: HolidayTreatment,
    holidays: pd.Series | None = None,
) -> pd.Series:
    """Shared day predicate; missing holiday context must never be ignored."""
    ordinary = weekdays.isin(days)
    if treatment == HolidayTreatment.REGULAR:
        return ordinary
    if holidays is None:
        raise ValueError("Holiday-aware TOU matching requires a holiday calendar mask.")
    if treatment == HolidayTreatment.EXCLUDE:
        return ordinary & ~holidays
    if treatment == HolidayTreatment.INCLUDE:
        return ordinary | holidays
    if treatment == HolidayTreatment.ONLY:
        return holidays
    raise ValueError(f"Unknown holiday treatment: {treatment!r}.")


def validate_holiday_calendar(calendar, treatments) -> None:
    if calendar is not None and not isinstance(calendar, HolidayCalendar):
        raise ValueError("holiday_calendar must be an explicit HolidayCalendar.")
    if calendar is None and any(t != HolidayTreatment.REGULAR for t in treatments):
        raise ValueError("Holiday-aware TOU periods require an explicit holiday_calendar.")
