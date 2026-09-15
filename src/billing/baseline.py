"""Baseline allowances for PG&E residential schedules.

A residential bill under a tiered schedule is not priced per interval. The
price of a kWh depends on how much has already been used in the billing
period, measured against a **baseline allowance** -- a daily quantity that
varies by baseline territory, season, and whether the home heats with
electricity.

Quantities are Special Condition 2 of Schedule E-1 (Sheet 4), and the
territory definitions are Part A of the Electric Preliminary Statement, which
assigns a territory by county and elevation band rather than by city.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import pandas as pd

from .tariffs import Season, SeasonDefinition, TariffError


class BaselineTerritory(StrEnum):
    """PG&E baseline territory, assigned by county and elevation."""

    P = "P"
    Q = "Q"
    R = "R"
    S = "S"
    T = "T"
    V = "V"
    W = "W"
    X = "X"
    Y = "Y"
    Z = "Z"


class BaselineCode(StrEnum):
    """Which allowance table applies to the dwelling.

    ``ALL_ELECTRIC`` (PG&E's Code H) is for homes whose primary heat source is
    permanently installed electric heating. Everything else takes ``BASIC``
    (Code B). Where a dwelling has several meters, only the primary meter can
    take the all-electric quantities.
    """

    BASIC = "basic"
    ALL_ELECTRIC = "all_electric"


#: kWh per day, as ``{territory: {code: {season: quantity}}}``.
#:
#: **Effective 1 June 2022** (Advice Letter 6603-E) and unchanged since:
#: the quantities printed on Schedule E-1 Sheet 4 in 2026 are identical to
#: those in PG&E's baseline sheet filed for 2024, checked territory by
#: territory for both Basic and All-Electric. One table therefore covers
#: every rate version this package carries. These are versioned data like
#: every rate here: when PG&E refiles them, add a new table rather than
#: editing these numbers, so past analyses stay reproducible.
BASELINE_QUANTITIES_2022_06_01: dict[
    BaselineTerritory, dict[BaselineCode, dict[Season, float]]
] = {
    BaselineTerritory.P: {
        BaselineCode.BASIC: {Season.SUMMER: 13.5, Season.WINTER: 11.0},
        BaselineCode.ALL_ELECTRIC: {Season.SUMMER: 15.2, Season.WINTER: 26.0},
    },
    BaselineTerritory.Q: {
        BaselineCode.BASIC: {Season.SUMMER: 9.8, Season.WINTER: 11.0},
        BaselineCode.ALL_ELECTRIC: {Season.SUMMER: 8.5, Season.WINTER: 26.0},
    },
    BaselineTerritory.R: {
        BaselineCode.BASIC: {Season.SUMMER: 17.7, Season.WINTER: 10.4},
        BaselineCode.ALL_ELECTRIC: {Season.SUMMER: 19.9, Season.WINTER: 26.7},
    },
    BaselineTerritory.S: {
        BaselineCode.BASIC: {Season.SUMMER: 15.0, Season.WINTER: 10.2},
        BaselineCode.ALL_ELECTRIC: {Season.SUMMER: 17.8, Season.WINTER: 23.7},
    },
    BaselineTerritory.T: {
        BaselineCode.BASIC: {Season.SUMMER: 6.5, Season.WINTER: 7.5},
        BaselineCode.ALL_ELECTRIC: {Season.SUMMER: 7.1, Season.WINTER: 12.9},
    },
    BaselineTerritory.V: {
        BaselineCode.BASIC: {Season.SUMMER: 7.1, Season.WINTER: 8.1},
        BaselineCode.ALL_ELECTRIC: {Season.SUMMER: 10.4, Season.WINTER: 19.1},
    },
    BaselineTerritory.W: {
        BaselineCode.BASIC: {Season.SUMMER: 19.2, Season.WINTER: 9.8},
        BaselineCode.ALL_ELECTRIC: {Season.SUMMER: 22.4, Season.WINTER: 19.0},
    },
    BaselineTerritory.X: {
        BaselineCode.BASIC: {Season.SUMMER: 9.8, Season.WINTER: 9.7},
        BaselineCode.ALL_ELECTRIC: {Season.SUMMER: 8.5, Season.WINTER: 14.6},
    },
    BaselineTerritory.Y: {
        BaselineCode.BASIC: {Season.SUMMER: 10.5, Season.WINTER: 11.1},
        BaselineCode.ALL_ELECTRIC: {Season.SUMMER: 12.0, Season.WINTER: 24.0},
    },
    BaselineTerritory.Z: {
        BaselineCode.BASIC: {Season.SUMMER: 5.9, Season.WINTER: 7.8},
        BaselineCode.ALL_ELECTRIC: {Season.SUMMER: 6.7, Season.WINTER: 15.7},
    },
}


@dataclass(frozen=True)
class BaselineAllowance:
    """How much of a period's usage is priced at the baseline tier."""

    territory: BaselineTerritory = BaselineTerritory.T
    code: BaselineCode = BaselineCode.BASIC

    def quantity_per_day(self, season: Season) -> float:
        return BASELINE_QUANTITIES_2022_06_01[self.territory][self.code][
            season
        ]

    def allowance_kWh(
        self,
        timestamps: pd.DatetimeIndex,
        season_definition: SeasonDefinition,
    ) -> float:
        """Allowance earned over the period the timestamps span.

        Each **local calendar day** earns its own season's quantity, so a
        billing month containing the 1 June or 1 October changeover is
        prorated exactly rather than taking one season for the whole month.
        Days come from the timestamps themselves, never from a month length,
        which keeps a daylight-saving day counted once.
        """

        if len(timestamps) == 0:
            raise TariffError(
                "A baseline allowance needs at least one interval."
            )

        days = pd.DatetimeIndex(timestamps).normalize().unique()
        seasons = season_definition.season_for_months(days.month)

        return float(
            sum(self.quantity_per_day(Season(season)) for season in seasons)
        )
