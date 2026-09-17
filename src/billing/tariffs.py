"""Versioned tariff definitions.

Rates are **data with effective dates**, not constants. A tariff that was
correct in 2026 is wrong in 2027, so every definition carries an effective
window, a source-document URL and version metadata, and lookups are made for
a specific date.

Nothing here reads a GUI widget or performs a billing calculation; this module
only describes what a tariff *is*. Charges are computed in
:mod:`src.billing.charges`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:  # avoids a cycle: baseline imports this module
    from .baseline import BaselineAllowance


class ServiceVoltageClass(StrEnum):
    """Service voltage determines which rate schedule applies."""

    SECONDARY = "secondary"      # below 2,400 V
    PRIMARY = "primary"          # 2,400 V to 50 kV
    TRANSMISSION = "transmission"


class CustomerClass(StrEnum):
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    AGRICULTURAL = "agricultural"


class ServiceType(StrEnum):
    """Who supplies the generation component."""

    BUNDLED = "bundled"
    CCA = "cca"
    DIRECT_ACCESS = "direct_access"


class Season(StrEnum):
    SUMMER = "summer"
    WINTER = "winter"


class DemandChargeBasis(StrEnum):
    MAXIMUM = "maximum"              # highest interval demand in the period
    PEAK_PERIOD = "peak_period"      # highest demand within TOU peak hours
    PART_PEAK_PERIOD = "part_peak_period"


#: Pandas weekday numbers, Monday 0 through Sunday 6. Same convention as
#: :data:`src.signal_pipeline.price_sources.ALL_DAYS`, deliberately, so the
#: two places that describe a time-of-use window agree.
ALL_DAYS = frozenset(range(7))

#: Monday through Friday, for schedules whose peak excludes the weekend.
WEEKDAYS = frozenset(range(5))


class TariffError(ValueError):
    pass


@dataclass(frozen=True)
class TOUPeriod:
    """One time-of-use energy rate block.

    ``start_hour`` is inclusive and ``end_hour`` exclusive, in local
    wall-clock hours. A block may wrap past midnight. ``months`` restricts the
    block to specific calendar months (1-12); empty means all months.

    ``days`` restricts the block to weekdays (Monday 0 through Sunday 6);
    it defaults to all seven. The PG&E B-series never needed it -- every one
    of its periods applies "every day, including weekends and holidays" --
    but residential time-of-use peaks are Monday-to-Friday, and charging a
    weekend evening at the peak rate would overstate the bill.

    ``demand_basis`` marks which demand-charge basis this block's *hours*
    also define, if any -- e.g. the same 4-9pm window priced for energy is
    usually the window a peak-period demand charge is measured over. Leave it
    ``None`` on off-peak/super-off-peak blocks, which only ever count toward
    a ``MAXIMUM``-basis charge (already computed over the whole period, with
    no hour filtering needed).
    """

    name: str
    rate_per_kWh: float
    start_hour: int
    end_hour: int
    season: Season | None = None
    months: frozenset[int] = frozenset()
    days: frozenset[int] = ALL_DAYS
    priority: int = 0
    demand_basis: DemandChargeBasis | None = None
    billing_category: str | None = None

    def __post_init__(self) -> None:
        if self.rate_per_kWh < 0:
            raise TariffError(
                f"TOU rate for {self.name!r} must be nonnegative."
            )

        for label, hour in (
            ("start_hour", self.start_hour),
            ("end_hour", self.end_hour),
        ):
            if not 0 <= hour <= 24:
                raise TariffError(
                    f"{self.name!r} {label} must be within 0..24; received "
                    f"{hour}."
                )

        invalid_months = set(self.months) - set(range(1, 13))

        if invalid_months:
            raise TariffError(
                f"{self.name!r} has invalid months {sorted(invalid_months)}."
            )

        if not self.days:
            raise TariffError(
                f"Period {self.name!r} applies to no days of the week."
            )

        invalid_days = set(self.days) - ALL_DAYS

        if invalid_days:
            raise TariffError(
                f"Period {self.name!r} has invalid days "
                f"{sorted(invalid_days)}. Monday is 0, Sunday is 6."
            )

    @property
    def wraps_midnight(self) -> bool:
        return self.end_hour < self.start_hour

    def matches(
        self,
        hours,
        months,
        seasons,
        weekdays=None,
    ):
        """Boolean mask of intervals this block covers.

        ``weekdays`` is optional so a caller that predates day-of-week
        support keeps working; when it is omitted the block is treated as
        applying every day, which is what every all-week period means.
        """

        if self.start_hour == self.end_hour:
            in_hours = hours == hours  # full day
        elif self.wraps_midnight:
            in_hours = (hours >= self.start_hour) | (hours < self.end_hour)
        else:
            in_hours = (hours >= self.start_hour) & (hours < self.end_hour)

        mask = in_hours

        if self.months:
            mask = mask & months.isin(list(self.months))

        if self.season is not None:
            mask = mask & (seasons == self.season.value)

        if weekdays is not None and self.days != ALL_DAYS:
            mask = mask & weekdays.isin(list(self.days))

        return mask


@dataclass(frozen=True)
class DemandChargeComponent:
    """One demand-charge line item, billed per kW of billing-period peak."""

    name: str
    rate_per_kW: float
    basis: DemandChargeBasis = DemandChargeBasis.MAXIMUM
    season: Season | None = None

    def __post_init__(self) -> None:
        if self.rate_per_kW < 0:
            raise TariffError(
                f"Demand rate for {self.name!r} must be nonnegative."
            )


@dataclass(frozen=True)
class ExportCompensationRule:
    """How exported energy is credited under this tariff."""

    name: str = "none"
    rate_per_kWh: float | None = None
    implemented: bool = False
    note: str = ""


@dataclass(frozen=True)
class EnergyTier:
    """One usage tier, bounded as a multiple of the baseline allowance.

    ``upper_bound_fraction`` is the top of the tier expressed against the
    period's baseline: 1.0 is "up to 100% of baseline", 4.0 is "up to 400%",
    and ``None`` is the unbounded top tier. Tiers are stated this way, rather
    than in kWh, because the allowance itself depends on the territory,
    season and number of days in the period.
    """

    name: str
    rate_per_kWh: float
    upper_bound_fraction: float | None = None

    def __post_init__(self) -> None:
        if self.rate_per_kWh < 0:
            raise TariffError(
                f"Tier rate for {self.name!r} must be nonnegative."
            )

        if (
            self.upper_bound_fraction is not None
            and self.upper_bound_fraction <= 0
        ):
            raise TariffError(
                f"Tier {self.name!r} must end above 0% of baseline; received "
                f"{self.upper_bound_fraction}."
            )


@dataclass(frozen=True)
class SeasonDefinition:
    """Which calendar months fall in which season."""

    summer_months: frozenset[int]

    def season_for_months(self, months):
        return pd.Series(
            [
                Season.SUMMER.value
                if month in self.summer_months
                else Season.WINTER.value
                for month in months
            ],
            index=getattr(months, "index", None),
        )


@dataclass(frozen=True)
class TariffDefinition:
    """A complete, versioned tariff."""

    tariff_id: str
    name: str
    utility: str
    effective_start: date
    service_voltage_class: ServiceVoltageClass
    customer_class: CustomerClass
    service_type: ServiceType
    season_definition: SeasonDefinition
    tou_periods: tuple[TOUPeriod, ...]
    source_url: str
    version: str
    effective_end: date | None = None
    daily_customer_charge: float | None = None
    monthly_customer_charge: float | None = None
    #: A **floor** on the period's bill, in $ per meter per day, not a charge
    #: added to it. PG&E residential service carried a "Delivery Minimum Bill
    #: Amount" of this shape before the income-graduated Base Services Charge
    #: replaced it; a household above the floor pays nothing for it, which is
    #: why it must never be modelled as a customer charge.
    daily_minimum_bill: float | None = None
    demand_charges: tuple[DemandChargeComponent, ...] = ()
    #: Usage tiers, lowest first, with exactly one unbounded tier last. Empty
    #: means the schedule prices every kWh at its TOU rate, which is what
    #: every commercial schedule here does.
    energy_tiers: tuple[EnergyTier, ...] = ()
    #: Default baseline allowance for a customer on this schedule. Territory
    #: is really a property of the *premises*, not the tariff, so billing may
    #: override it; this is the starting point when nobody says otherwise.
    baseline: "BaselineAllowance | None" = None
    export_rule: ExportCompensationRule = field(
        default_factory=ExportCompensationRule
    )
    notes: str = ""
    # Additive $/kWh components aligned with tou_periods. Credits may be negative.
    energy_components: tuple[tuple[str, tuple[float, ...]], ...] = ()
    calendar_month_customer_charge: bool = False

    def __post_init__(self) -> None:
        if self.energy_components:
            import math
            names = [name for name, _ in self.energy_components]
            if len(names) != len(set(names)) or self.energy_tiers:
                raise TariffError("Energy components need unique names and an untiered tariff.")
            for _, rates in self.energy_components:
                if len(rates) != len(self.tou_periods) or not all(math.isfinite(r) for r in rates):
                    raise TariffError("Energy components must cover every TOU block with finite rates.")
            for i, period in enumerate(self.tou_periods):
                if not math.isclose(sum(r[i] for _, r in self.energy_components), period.rate_per_kWh, abs_tol=1e-9):
                    raise TariffError("Energy components must sum to each combined TOU rate.")
        if not self.tou_periods:
            raise TariffError(
                f"Tariff {self.tariff_id!r} defines no TOU periods."
            )

        if (
            self.daily_customer_charge is None
            and self.monthly_customer_charge is None
            and self.daily_minimum_bill is None
        ):
            raise TariffError(
                f"Tariff {self.tariff_id!r} defines neither a customer charge "
                f"nor a minimum bill."
            )

        if (
            self.daily_minimum_bill is not None
            and self.daily_minimum_bill < 0
        ):
            raise TariffError(
                f"Tariff {self.tariff_id!r} has a negative minimum bill."
            )

        if self.energy_tiers:
            bounded = [
                tier.upper_bound_fraction
                for tier in self.energy_tiers
                if tier.upper_bound_fraction is not None
            ]

            if len(bounded) != len(self.energy_tiers) - 1:
                raise TariffError(
                    f"Tariff {self.tariff_id!r} must end with exactly one "
                    f"unbounded tier; the rest need an upper bound."
                )

            if self.energy_tiers[-1].upper_bound_fraction is not None:
                raise TariffError(
                    f"Tariff {self.tariff_id!r} puts a bounded tier last; "
                    f"the top tier must be unbounded."
                )

            if bounded != sorted(bounded) or len(set(bounded)) != len(bounded):
                raise TariffError(
                    f"Tariff {self.tariff_id!r} tier bounds must increase; "
                    f"received {bounded}."
                )

            if self.baseline is None:
                raise TariffError(
                    f"Tariff {self.tariff_id!r} defines tiers but no default "
                    f"baseline allowance, so a tier boundary has no size."
                )

        if (
            self.effective_end is not None
            and self.effective_end < self.effective_start
        ):
            raise TariffError(
                f"Tariff {self.tariff_id!r} ends before it begins."
            )

    def is_effective_on(self, on_date: date) -> bool:
        if on_date < self.effective_start:
            return False

        return self.effective_end is None or on_date <= self.effective_end

    def season_for(self, timestamps: pd.DatetimeIndex) -> pd.Series:
        months = pd.Series(timestamps.month)
        return self.season_definition.season_for_months(months)

    def energy_rates(self, timestamps: pd.DatetimeIndex) -> pd.Series:
        """Return the $/kWh energy rate for each interval.

        Rates are matched on **local wall-clock** hour, so a 4 p.m. peak stays
        at 4 p.m. local across a daylight-saving transition.
        """

        hours = pd.Series(timestamps.hour)
        months = pd.Series(timestamps.month)
        weekdays = pd.Series(timestamps.weekday)
        seasons = self.season_for(timestamps)

        rates = pd.Series(float("nan"), index=range(len(timestamps)))

        # Higher priority wins where blocks overlap; a super-off-peak window
        # carved out of a broader off-peak block is expressed that way.
        for period in sorted(
            self.tou_periods,
            key=lambda p: p.priority,
            reverse=True,
        ):
            covered = period.matches(hours, months, seasons, weekdays)
            rates = rates.mask(covered & rates.isna(), period.rate_per_kWh)

        if rates.isna().any():
            position = int(rates.isna().idxmax())
            raise TariffError(
                f"Tariff {self.tariff_id!r} has no rate covering "
                f"{timestamps[position]}. TOU periods must cover every hour "
                f"of every season."
            )

        return rates

    def period_names(self, timestamps: pd.DatetimeIndex) -> pd.Series:
        hours = pd.Series(timestamps.hour)
        months = pd.Series(timestamps.month)
        weekdays = pd.Series(timestamps.weekday)
        seasons = self.season_for(timestamps)

        names = pd.Series(None, index=range(len(timestamps)), dtype=object)

        for period in sorted(
            self.tou_periods,
            key=lambda p: p.priority,
            reverse=True,
        ):
            covered = period.matches(hours, months, seasons, weekdays)
            names = names.mask(covered & names.isna(), period.name)

        return names

    def demand_basis_for(self, timestamps: pd.DatetimeIndex) -> pd.Series:
        """Which demand-charge basis applies to each interval, if any.

        Derived from whichever TOU period is active there (same priority
        resolution as :meth:`energy_rates`), via that period's own
        ``demand_basis``. Intervals covered by a period with no
        ``demand_basis`` (typically off-peak/super-off-peak) come back
        ``None`` -- they still count toward a ``MAXIMUM``-basis charge, just
        not toward a period-scoped one.
        """

        names = self.period_names(timestamps)
        basis_by_name = {
            period.name: period.demand_basis for period in self.tou_periods
        }
        return names.map(basis_by_name)

    def billing_categories(self, timestamps: pd.DatetimeIndex) -> pd.Series:
        """Return stable categories used to group bill-detail energy rows."""

        names = self.period_names(timestamps)
        category_by_name = {
            period.name: period.billing_category or period.name
            for period in self.tou_periods
        }
        return names.map(category_by_name)

    def split_tier_kWh(
        self,
        total_kWh: float,
        allowance_kWh: float,
    ) -> dict[str, float]:
        """Split one period's usage across the tiers, lowest tier first.

        Tier boundaries are multiples of ``allowance_kWh``, so this is where
        "101% - 400% of Baseline" becomes a number of kWh. An untiered tariff
        returns an empty mapping; its energy is priced per interval instead.
        """

        if not self.energy_tiers:
            return {}

        if total_kWh < 0:
            raise TariffError("Tiered usage must not be negative.")

        if allowance_kWh <= 0:
            raise TariffError(
                f"Tariff {self.tariff_id!r} needs a positive baseline "
                f"allowance to place tier boundaries."
            )

        split: dict[str, float] = {}
        consumed = 0.0

        for tier in self.energy_tiers:
            if tier.upper_bound_fraction is None:
                ceiling = total_kWh
            else:
                ceiling = min(
                    total_kWh, tier.upper_bound_fraction * allowance_kWh
                )

            split[tier.name] = max(0.0, ceiling - consumed)
            consumed = max(consumed, ceiling)

        return split

    def customer_charge_for(self, billing_days: float, *, days_in_month: int | None = None) -> float:
        """Customer charge for one meter over ``billing_days`` days."""

        if billing_days < 0:
            raise TariffError("billing_days must not be negative.")

        if self.daily_customer_charge is not None:
            return self.daily_customer_charge * billing_days

        if self.monthly_customer_charge is not None:
            if self.calendar_month_customer_charge:
                if days_in_month not in (28, 29, 30, 31):
                    raise TariffError("Calendar-month charges require the billing month's length.")
                return self.monthly_customer_charge * billing_days / days_in_month
            # Legacy monthly charges retain their existing 30-day convention.
            return self.monthly_customer_charge * (billing_days / 30.0)

        # A schedule whose only fixed provision is a minimum bill adds
        # nothing per day; the floor is applied to the finished bill instead.
        return 0.0

    def minimum_bill_for(self, billing_days: float) -> float:
        """The floor this schedule puts under one meter's period bill."""

        if billing_days < 0:
            raise TariffError("billing_days must not be negative.")

        if self.daily_minimum_bill is None:
            return 0.0

        return self.daily_minimum_bill * billing_days


TARIFF_REGISTRY: dict[str, TariffDefinition] = {}


def register_tariff(tariff: TariffDefinition) -> TariffDefinition:
    TARIFF_REGISTRY[tariff.tariff_id] = tariff
    return tariff


def get_tariff(
    tariff_id: str,
    on_date: date | None = None,
) -> TariffDefinition:
    """Look up a tariff, optionally checking it is effective on a date."""

    if tariff_id not in TARIFF_REGISTRY:
        raise TariffError(
            f"Unknown tariff {tariff_id!r}. Known tariffs: "
            f"{sorted(TARIFF_REGISTRY)}."
        )

    tariff = TARIFF_REGISTRY[tariff_id]

    if on_date is not None and not tariff.is_effective_on(on_date):
        raise TariffError(
            f"Tariff {tariff_id!r} version {tariff.version} is effective from "
            f"{tariff.effective_start}"
            + (
                f" to {tariff.effective_end}"
                if tariff.effective_end
                else ""
            )
            + f", which does not cover {on_date}. Rates change over time; "
            f"add the applicable version rather than reusing this one."
        )

    return tariff


def supported_tariffs() -> list[str]:
    return sorted(TARIFF_REGISTRY)
