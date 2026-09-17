"""Billing calculation.

Pure functions over an interval table plus a tariff and a meter topology.

**Demand charges are not summed across intervals.** Each demand-charge
component bills a single peak import per billing period, once -- summing
per-interval demand would overstate cost by roughly the number of intervals,
which is the most common way this calculation goes wrong. A tariff can still
have *several* demand components on the same bill (e.g. B-19's maximum-demand
charge plus a peak-period one): those are legitimately summed together, each
against its own peak over its own scope (the whole period for `MAXIMUM`;
just the tariff's on-peak/part-peak hours for `PEAK_PERIOD`/
`PART_PEAK_PERIOD`) -- it's summing across intervals, within one component,
that's wrong.

Billing periods are calendar months. A horizon spanning several months gets a
separate peak, and a separate customer charge, for each.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping
from datetime import date
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from .meter_topology import MeterTopology, MeterTopologyMode
from .tariffs import DemandChargeBasis, TariffDefinition, TariffError

if TYPE_CHECKING:
    from .baseline import BaselineAllowance
    from .plans import RatePlan


class BillingError(ValueError):
    pass


@dataclass
class BillingPeriodResult:
    """Charges for one meter over one billing period.

    ``demand_charge_by_component`` gives each demand-charge component's own
    dollar contribution, by name; ``demand_charge`` is their sum. Exposed
    separately so a tariff with several components (e.g. a maximum-demand
    charge plus a peak-period one) can be inspected/tested component by
    component, not just as one total.
    """

    meter_id: str
    tariff_id: str
    period_label: str
    billing_days: float
    customer_charge: float
    import_energy_kWh: float
    import_energy_charge: float
    billed_peak_kw: float
    simulated_peak_kw: float
    demand_charge: float
    export_energy_kWh: float
    export_credit: float
    is_partial_period: bool = False
    previous_peak_was_known: bool = True
    warnings: tuple[str, ...] = field(default_factory=tuple)
    import_energy_charge_by_component: dict[str, float] = field(default_factory=dict)
    demand_charge_by_component: dict[str, float] = field(default_factory=dict)
    import_energy_kWh_by_period: dict[str, float] = field(
        default_factory=dict
    )
    import_energy_charge_by_period: dict[str, float] = field(
        default_factory=dict
    )

    @property
    def total_utility_charge(self) -> float:
        return (
            self.customer_charge
            + self.import_energy_charge
            + self.demand_charge
            - self.export_credit
        )


@dataclass
class BillingResult:
    """All billing periods and meters for one scenario."""

    periods: tuple[BillingPeriodResult, ...]
    battery_degradation_cost: float = 0.0
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def customer_charge(self) -> float:
        return sum(period.customer_charge for period in self.periods)

    @property
    def import_energy_charge(self) -> float:
        return sum(period.import_energy_charge for period in self.periods)

    @property
    def demand_charge(self) -> float:
        return sum(period.demand_charge for period in self.periods)

    @property
    def export_credit(self) -> float:
        return sum(period.export_credit for period in self.periods)

    @property
    def import_energy_kWh(self) -> float:
        return sum(period.import_energy_kWh for period in self.periods)

    @property
    def export_energy_kWh(self) -> float:
        return sum(period.export_energy_kWh for period in self.periods)

    @property
    def import_energy_kWh_by_period(self) -> dict[str, float]:
        return _sum_period_breakdowns(
            self.periods,
            "import_energy_kWh_by_period",
        )

    @property
    def import_energy_charge_by_period(self) -> dict[str, float]:
        return _sum_period_breakdowns(
            self.periods,
            "import_energy_charge_by_period",
        )

    @property
    def total_utility_charge(self) -> float:
        return sum(period.total_utility_charge for period in self.periods)

    @property
    def total_explicit_operating_cost(self) -> float:
        """Utility charges plus battery degradation.

        Degradation is a real operating cost but is not a utility charge, so
        it is reported separately and only combined here.
        """

        return self.total_utility_charge + self.battery_degradation_cost

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "meter_id": period.meter_id,
                    "tariff_id": period.tariff_id,
                    "period": period.period_label,
                    "billing_days": period.billing_days,
                    "customer_charge": period.customer_charge,
                    "import_energy_kWh": period.import_energy_kWh,
                    "import_energy_charge": period.import_energy_charge,
                    **{f"{name}_charge": value for name, value in period.import_energy_charge_by_component.items()},
                    "billed_peak_kw": period.billed_peak_kw,
                    "demand_charge": period.demand_charge,
                    "export_energy_kWh": period.export_energy_kWh,
                    "export_credit": period.export_credit,
                    "total_utility_charge": period.total_utility_charge,
                    "is_partial_period": period.is_partial_period,
                }
                for period in self.periods
            ]
        )


def assign_billing_periods(timestamps: pd.DatetimeIndex) -> pd.Series:
    """Label each interval with its calendar-month billing period."""

    return pd.Series(
        [f"{ts.year:04d}-{ts.month:02d}" for ts in timestamps],
        index=range(len(timestamps)),
    )


def calculate_demand_peak(
    import_kw: np.ndarray,
    *,
    previous_peak_kw: float | Mapping[str, float] | None = None,
) -> tuple[float, float, bool]:
    """Return (billed_peak, simulated_peak, previous_peak_was_known).

    For a partial billing cycle the utility bills against the peak already
    established earlier in the period, so:

        billed_peak = max(previous_peak, simulated_peak)

    When the previous peak is unknown, the simulated peak is used and the
    result is flagged, because the real bill can only be higher.
    """

    simulated_peak = float(np.max(import_kw)) if len(import_kw) else 0.0

    if previous_peak_kw is None:
        return simulated_peak, simulated_peak, False

    if previous_peak_kw < 0:
        raise BillingError("previous_peak_kw must not be negative.")

    return (
        max(float(previous_peak_kw), simulated_peak),
        simulated_peak,
        True,
    )


def calculate_flat_demand_charge(
    dispatch: pd.DataFrame,
    demand_charge_rate_per_kw: float,
    *,
    previous_peak_kw: float | None = None,
    import_column: str = "grid_import_kw",
) -> float:
    """Bill a single flat per-kW demand charge across every calendar month.

    This is the lightweight counterpart to `calculate_meter_billing`: it
    reuses the same `assign_billing_periods` / `calculate_demand_peak`
    primitives, but doesn't require a `TariffDefinition` or meter topology.
    It's for callers that track cost against a simple external price series
    rather than a full tariff — e.g. the multi-day experiment pipeline in
    `signal_pipeline.market_data_integration`, which has no tariff at all.

    `previous_peak_kw` is honoured only for the first represented month, same
    as `calculate_meter_billing` — later months start from zero.
    """

    if demand_charge_rate_per_kw < 0:
        raise BillingError(
            "demand_charge_rate_per_kw must not be negative."
        )

    if demand_charge_rate_per_kw == 0:
        return 0.0

    if "timestamp" not in dispatch.columns:
        raise BillingError("Dispatch data is missing a timestamp column.")

    timestamps = pd.DatetimeIndex(dispatch["timestamp"])
    period_labels = assign_billing_periods(timestamps)

    total_cost = 0.0
    for period_index, period in enumerate(period_labels.unique()):
        mask = (period_labels == period).to_numpy()
        import_kw = dispatch.loc[mask, import_column].to_numpy()
        prior_peak = previous_peak_kw if period_index == 0 else None
        billed_peak, _, _ = calculate_demand_peak(
            import_kw,
            previous_peak_kw=prior_peak,
        )
        total_cost += demand_charge_rate_per_kw * billed_peak

    return float(total_cost)


def calculate_meter_billing(
    dispatch: pd.DataFrame,
    tariff: TariffDefinition,
    *,
    meter_id: str,
    timestep_hours: float,
    import_column: str = "grid_import_kw",
    export_column: str = "grid_export_kw",
    export_price_per_kWh: np.ndarray | float | None = None,
    previous_peak_kw: float | None = None,
    utility_account_count: int = 1,
    expect_full_periods: bool = True,
    baseline: "BaselineAllowance | None" = None,
) -> tuple[BillingPeriodResult, ...]:
    """Bill one meter across every calendar-month period in the horizon.

    ``baseline`` overrides the tariff's default allowance for a tiered
    schedule. Baseline territory belongs to the premises rather than to the
    rate, so a caller that knows the site's territory should say so; without
    one the tariff's own default is used.
    """

    if "timestamp" not in dispatch.columns:
        raise BillingError("Dispatch data is missing a timestamp column.")

    timestamps = pd.DatetimeIndex(dispatch["timestamp"])

    if timestamps.tz is None:
        raise BillingError(
            "Billing requires timezone-aware timestamps: TOU periods and "
            "billing months are defined in local time."
        )

    rates = tariff.energy_rates(timestamps).to_numpy(dtype=float)
    energy_categories = tariff.billing_categories(timestamps).to_numpy()
    seasons = tariff.season_for(timestamps).to_numpy()
    demand_basis_per_interval = tariff.demand_basis_for(timestamps).to_numpy()
    import_kw = dispatch[import_column].to_numpy(dtype=float)

    export_kw = (
        dispatch[export_column].to_numpy(dtype=float)
        if export_column in dispatch.columns
        else np.zeros(len(dispatch))
    )

    export_rates = _export_rate_array(export_price_per_kWh, len(dispatch))

    periods = assign_billing_periods(timestamps)

    invalid_dates = sorted(
        {
            timestamp.date()
            for timestamp in timestamps
            if not tariff.is_effective_on(timestamp.date())
        }
    )

    if invalid_dates:
        raise TariffError(
            f"Tariff {tariff.tariff_id!r} version {tariff.version} is not "
            f"effective on {invalid_dates[0]}. Its effective window begins "
            f"{tariff.effective_start}"
            + (
                f" and ends {tariff.effective_end}"
                if tariff.effective_end is not None
                else ""
            )
            + ". Select the tariff version covering the analysis date."
        )

    results = []

    for period_index, label in enumerate(periods.unique()):
        mask = (periods == label).to_numpy()

        period_import_kw = import_kw[mask]
        period_export_kw = export_kw[mask]
        period_rates = rates[mask]
        period_energy_categories = energy_categories[mask]
        period_export_rates = export_rates[mask]

        import_kWh = period_import_kw * timestep_hours
        export_kWh = period_export_kw * timestep_hours

        if isinstance(previous_peak_kw, Mapping):
            prior_peak_for_period = previous_peak_kw.get(label)
        elif period_index == 0:
            prior_peak_for_period = previous_peak_kw
        else:
            prior_peak_for_period = None

        billed_peak, simulated_peak, previous_known = calculate_demand_peak(
            period_import_kw,
            previous_peak_kw=prior_peak_for_period,
        )

        period_demand_basis = demand_basis_per_interval[mask]
        period_seasons = seasons[mask]

        demand_charge = 0.0
        demand_charge_by_component: dict[str, float] = {}

        for component in tariff.demand_charges:
            if component.basis == DemandChargeBasis.MAXIMUM:
                # The period's overall peak, already resolved above
                # (previous_peak_kw applies here, same as always).
                component_peak = billed_peak
            else:
                # PEAK_PERIOD / PART_PEAK_PERIOD: only the intervals whose
                # active TOU block is tagged with this basis count -- e.g.
                # a peak-period demand charge is measured only over the
                # hours the tariff calls "peak", not the whole month.
                # `previous_peak_kw` is not carried into these narrower
                # peaks: the tariff only documents a single "previous
                # billing peak" concept (used for MAXIMUM), so a brand-new
                # customer's first partial period may understate a
                # period-scoped charge the same way `is_partial` already
                # warns about for the overall one.
                component_scope = period_demand_basis == component.basis
                if component.season is not None:
                    component_scope = component_scope & (
                        period_seasons == component.season.value
                    )
                component_peak, _, _ = calculate_demand_peak(
                    period_import_kw[component_scope]
                )

            component_cost = component.rate_per_kW * component_peak
            demand_charge += component_cost
            demand_charge_by_component[component.name] = component_cost

        period_timestamps = timestamps[mask]
        billing_days = float(
            len(period_timestamps.normalize().unique())
        )

        is_partial = expect_full_periods and not _is_full_month(
            label,
            period_timestamps,
            timestep_hours,
        )

        warnings = []
        if tariff.calendar_month_customer_charge and billing_days < pd.Period(label, freq="M").days_in_month:
            warnings.append("APPROXIMATION: monthly customer charge allocated by service days in the calendar month; not an actual meter-cycle bill.")

        if is_partial and tariff.demand_charges and not previous_known:
            warnings.append(
                f"PARTIAL BILLING PERIOD: {label} is only "
                f"{billing_days:.2f} days and no previously established "
                f"billing peak was supplied. The demand charge reflects only "
                f"the simulated window; an actual bill can only be higher."
            )

        # A tiered schedule prices the period's *total*, not each interval:
        # the rate of a kWh depends on how much came before it. Tier sizes
        # come from the baseline allowance the period earned, so the whole
        # calculation replaces the per-interval product rather than adjusting
        # it. The per-period breakdown then reports tiers instead of TOU
        # blocks, which is what such a bill actually itemises.
        period_total_kWh = float(import_kWh.sum())
        tier_split: dict[str, float] = {}

        if tariff.energy_tiers:
            allowance = (baseline or tariff.baseline).allowance_kWh(
                period_timestamps, tariff.season_definition
            )
            tier_split = tariff.split_tier_kWh(period_total_kWh, allowance)
            rate_by_tier = {
                tier.name: tier.rate_per_kWh for tier in tariff.energy_tiers
            }
            energy_kWh_by_period = dict(tier_split)
            energy_charge_by_period = {
                name: kWh * rate_by_tier[name]
                for name, kWh in tier_split.items()
            }
            total_energy_charge = float(
                sum(energy_charge_by_period.values())
            )
        else:
            total_energy_charge = float((import_kWh * period_rates).sum())
            energy_kWh_by_period = {}
            energy_charge_by_period = {}

        for category in (
            () if tariff.energy_tiers else dict.fromkeys(period_energy_categories)
        ):
            category_mask = period_energy_categories == category
            energy_kWh_by_period[str(category)] = float(
                import_kWh[category_mask].sum()
            )
            energy_charge_by_period[str(category)] = float(
                (import_kWh[category_mask] * period_rates[category_mask]).sum()
            )

        component_charges = {}
        if tariff.energy_components:
            period_names = tariff.period_names(period_timestamps)
            for name, component_rates in tariff.energy_components:
                by_name = dict(zip((p.name for p in tariff.tou_periods), component_rates))
                component_charges[name] = float((import_kWh * period_names.map(by_name).to_numpy()).sum())

        results.append(
            BillingPeriodResult(
                meter_id=meter_id,
                tariff_id=tariff.tariff_id,
                period_label=label,
                billing_days=billing_days,
                customer_charge=(
                    tariff.customer_charge_for(billing_days, days_in_month=pd.Period(label, freq="M").days_in_month)
                    * utility_account_count
                ),
                import_energy_kWh=float(import_kWh.sum()),
                import_energy_charge=total_energy_charge,
                billed_peak_kw=billed_peak,
                simulated_peak_kw=simulated_peak,
                demand_charge=float(demand_charge),
                export_energy_kWh=float(export_kWh.sum()),
                export_credit=float(
                    (export_kWh * period_export_rates).sum()
                ),
                is_partial_period=is_partial,
                previous_peak_was_known=previous_known,
                warnings=tuple(warnings),
                import_energy_charge_by_component=component_charges,
                demand_charge_by_component=demand_charge_by_component,
                import_energy_kWh_by_period=energy_kWh_by_period,
                import_energy_charge_by_period=energy_charge_by_period,
            )
        )

    return tuple(results)


def _sum_period_breakdowns(
    periods: tuple[BillingPeriodResult, ...],
    attribute: str,
) -> dict[str, float]:
    """Sum a named energy-breakdown mapping across billing periods."""

    total: dict[str, float] = {}
    for period in periods:
        for category, value in getattr(period, attribute).items():
            total[category] = total.get(category, 0.0) + float(value)
    return total


def calculate_billing(
    dispatch: pd.DataFrame,
    topology: MeterTopology,
    tariffs: dict[str, TariffDefinition],
    *,
    timestep_hours: float,
    export_price_per_kWh: np.ndarray | float | None = None,
    previous_peak_kw: float | None = None,
    battery_degradation_cost: float = 0.0,
    meter_dispatches: Mapping[str, pd.DataFrame] | None = None,
) -> BillingResult:
    """Bill a dispatch schedule under a meter topology.

    Single-PCC and master-meter topologies bill one aggregate account, with
    demand measured on the combined flow. Individually metered topologies bill
    each account separately, so each has its own peak and its own customer
    charge.
    """

    warnings = list(topology.approximation_warnings)

    if topology.demand_is_aggregate:
        account = topology.utility_accounts[0]
        tariff = _lookup(tariffs, topology.tariff_for(account))

        periods = calculate_meter_billing(
            dispatch,
            tariff,
            meter_id=account.meter_id,
            timestep_hours=timestep_hours,
            export_price_per_kWh=export_price_per_kWh,
            previous_peak_kw=previous_peak_kw,
            utility_account_count=1,
        )

        if topology.mode == MeterTopologyMode.MASTER_WITH_SUBMETERS:
            warnings.append(
                f"Submeters ({len(topology.submeters)}) allocate the master "
                f"bill internally and incur no separate utility customer or "
                f"demand charges."
            )

        return BillingResult(
            periods=periods,
            battery_degradation_cost=battery_degradation_cost,
            warnings=tuple(warnings),
        )

    if topology.mode == MeterTopologyMode.INDIVIDUAL_WITH_SHARED_GENERATION:
        raise BillingError(
            "Shared-generation billing is not implemented yet. Allocation "
            "percentages describe how credits are assigned, but the applicable "
            "NEM/NBT credit rules are not configured. Refusing to split the "
            "aggregate PCC flow equally because that would fabricate per-meter "
            "bills."
        )

    accounts = topology.utility_accounts

    if meter_dispatches is None and not (
        topology.uses_equal_allocation_approximation
    ):
        raise BillingError(
            "Individually metered billing requires meter_dispatches with one "
            "dispatch table per utility account. To use an equal split of the "
            "aggregate site flow instead, explicitly set "
            "uses_equal_allocation_approximation=True on the topology."
        )

    if meter_dispatches is not None:
        required_meter_ids = {account.meter_id for account in accounts}
        missing_meter_ids = required_meter_ids - set(meter_dispatches)

        if missing_meter_ids:
            raise BillingError(
                "Per-meter dispatch data is missing utility accounts: "
                f"{sorted(missing_meter_ids)}."
            )

    share = 1.0 / len(accounts)

    all_periods: list[BillingPeriodResult] = []

    for account in accounts:
        tariff = _lookup(tariffs, topology.tariff_for(account))

        if meter_dispatches is not None:
            meter_dispatch = meter_dispatches[account.meter_id]
            meter_previous_peak = previous_peak_kw
        else:
            # This approximation is used only after explicit opt-in above.
            meter_dispatch = dispatch.copy()
            meter_dispatch["grid_import_kw"] = (
                dispatch["grid_import_kw"] * share
            )

            if "grid_export_kw" in dispatch.columns:
                meter_dispatch["grid_export_kw"] = (
                    dispatch["grid_export_kw"] * share
                )

            meter_previous_peak = (
                previous_peak_kw * share
                if previous_peak_kw is not None
                else None
            )

        all_periods.extend(
            calculate_meter_billing(
                meter_dispatch,
                tariff,
                meter_id=account.meter_id,
                timestep_hours=timestep_hours,
                export_price_per_kWh=export_price_per_kWh,
                previous_peak_kw=meter_previous_peak,
                utility_account_count=1,
            )
        )

    warnings.append(
        f"Each of the {len(accounts)} utility accounts is billed "
        f"independently: separate customer charges and separate demand peaks."
    )

    return BillingResult(
        periods=tuple(all_periods),
        battery_degradation_cost=battery_degradation_cost,
        warnings=tuple(warnings),
    )


def allocate_shared_generation(
    generation_kWh: float,
    topology: MeterTopology,
) -> dict[str, float]:
    """Split shared generation across meters by allocation percentage.

    This is a billing credit. It does not claim particular electrons reached a
    particular unit.
    """

    allocations = {
        meter.meter_id: meter.allocation_percent
        for meter in topology.meters
        if meter.allocation_percent is not None
    }

    if not allocations:
        raise BillingError(
            "Topology defines no allocation percentages."
        )

    total = sum(allocations.values())

    if abs(total - 100.0) > 1e-6:
        raise BillingError(
            f"Allocation percentages sum to {total}, not 100."
        )

    return {
        meter_id: generation_kWh * percent / 100.0
        for meter_id, percent in allocations.items()
    }


def _lookup(
    tariffs: dict[str, TariffDefinition],
    tariff_id: str,
) -> TariffDefinition:
    if tariff_id not in tariffs:
        raise BillingError(
            f"Tariff {tariff_id!r} was not supplied. Available: "
            f"{sorted(tariffs)}."
        )

    return tariffs[tariff_id]


def _export_rate_array(
    export_price_per_kWh,
    interval_count: int,
) -> np.ndarray:
    if export_price_per_kWh is None:
        return np.zeros(interval_count)

    if isinstance(export_price_per_kWh, (int, float)):
        return np.full(interval_count, float(export_price_per_kWh))

    rates = np.asarray(export_price_per_kWh, dtype=float)

    if len(rates) != interval_count:
        raise BillingError(
            f"Export price series has {len(rates)} values but the horizon has "
            f"{interval_count} intervals."
        )

    return rates


def _is_full_month(
    label: str,
    timestamps: pd.DatetimeIndex,
    timestep_hours: float,
) -> bool:
    year, month = (int(part) for part in label.split("-"))
    timezone = timestamps.tz
    month_start = pd.Timestamp(year=year, month=month, day=1, tz=timezone)
    next_month_start = month_start + pd.offsets.MonthBegin(1)
    expected = pd.date_range(
        start=month_start,
        end=next_month_start,
        freq=pd.Timedelta(hours=timestep_hours),
        inclusive="left",
    )

    return timestamps.equals(expected)


@dataclass(frozen=True)
class VersionSegmentResult:
    """What one tariff version billed inside one billing period.

    A segment is the intersection of a billing period and a version's
    effective window: the run of local service dates in that month priced by
    that filed document. Its ``service_days`` never overlap another segment's,
    which is what keeps a fixed charge from being collected twice for one day.
    """

    tariff_id: str
    version: str
    effective_start: date
    effective_end: date | None
    source_url: str
    service_days: int
    first_service_date: date
    last_service_date: date
    import_energy_kWh: float
    import_energy_charge: float
    customer_charge: float
    minimum_bill_floor: float
    import_energy_kWh_by_category: dict[str, float] = field(
        default_factory=dict
    )
    import_energy_charge_by_category: dict[str, float] = field(
        default_factory=dict
    )
    baseline_allowance_kWh: float | None = None


@dataclass(frozen=True)
class TimelineBillingPeriodResult:
    """One meter's bill for one billing period, itemised by tariff version."""

    meter_id: str
    plan_id: str
    plan_description: str
    period_label: str
    billing_days: int
    segments: tuple[VersionSegmentResult, ...]
    export_energy_kWh: float
    export_credit: float
    export_pricing_note: str
    warnings: tuple[str, ...] = ()

    @property
    def import_energy_kWh(self) -> float:
        return sum(s.import_energy_kWh for s in self.segments)

    @property
    def import_energy_charge(self) -> float:
        return sum(s.import_energy_charge for s in self.segments)

    @property
    def customer_charge(self) -> float:
        return sum(s.customer_charge for s in self.segments)

    @property
    def minimum_bill_floor(self) -> float:
        """The floor the period's charges must clear, summed over versions."""

        return sum(s.minimum_bill_floor for s in self.segments)

    @property
    def charges_before_minimum(self) -> float:
        return self.customer_charge + self.import_energy_charge

    @property
    def minimum_bill_adjustment(self) -> float:
        """What the floor added, if the period's own charges fell short."""

        return max(0.0, self.minimum_bill_floor - self.charges_before_minimum)

    @property
    def total_utility_charge(self) -> float:
        return (
            self.charges_before_minimum
            + self.minimum_bill_adjustment
            - self.export_credit
        )

    @property
    def versions_used(self) -> tuple[str, ...]:
        return tuple(s.tariff_id for s in self.segments)


def calculate_timeline_billing(
    dispatch: pd.DataFrame,
    plan: "RatePlan",
    *,
    meter_id: str,
    timestep_hours: float,
    import_column: str = "grid_import_kw",
    export_column: str = "grid_export_kw",
    baseline: "BaselineAllowance | None" = None,
    export_price_per_kWh: np.ndarray | float | None = None,
) -> tuple[TimelineBillingPeriodResult, ...]:
    """Bill one meter across a horizon that may span several rate versions.

    Unlike :func:`calculate_meter_billing`, which takes one version and
    refuses any date outside it, this walks the plan's timeline: every
    interval's energy is priced by the version effective on **its own local
    service date**, and each service date's fixed charge is collected once,
    under whichever version covered that date.

    ``baseline`` overrides the account's baseline allowance for tiered plans.
    Territory and Basic/All-Electric code are properties of the premises, so a
    caller that knows them should pass them; otherwise each version's own
    default is used.

    ``export_price_per_kWh`` is an explicit scenario price. It is **not** a
    filed NEM or Net Billing credit -- those rules are not implemented -- and
    every result carrying a nonzero export credit says so.
    """

    if "timestamp" not in dispatch.columns:
        raise BillingError("Dispatch data is missing a timestamp column.")

    timestamps = pd.DatetimeIndex(dispatch["timestamp"])

    if timestamps.tz is None:
        raise BillingError(
            "Billing requires timezone-aware timestamps: TOU periods and "
            "billing months are defined in local time."
        )

    import_kw = dispatch[import_column].to_numpy(dtype=float)
    export_kw = (
        dispatch[export_column].to_numpy(dtype=float)
        if export_column in dispatch.columns
        else np.zeros(len(dispatch), dtype=float)
    )
    export_rates = _export_rate_array(export_price_per_kWh, len(dispatch))

    # Raises on a gap before any money is computed.
    segments_by_version = plan.segments_for(timestamps)
    version_for_date = {
        service_date: version
        for version, dates in segments_by_version
        for service_date in dates
    }

    service_dates = np.array([stamp.date() for stamp in timestamps])
    period_labels = assign_billing_periods(timestamps)

    results: list[TimelineBillingPeriodResult] = []

    for label in period_labels.unique():
        period_mask = (period_labels == label).to_numpy()
        period_stamps = timestamps[period_mask]
        period_dates = service_dates[period_mask]

        ordered_versions: list[str] = []
        seen: set[str] = set()
        for service_date in period_dates:
            tariff_id = version_for_date[service_date].tariff_id
            if tariff_id not in seen:
                seen.add(tariff_id)
                ordered_versions.append(tariff_id)

        warnings: list[str] = []
        segments: list[VersionSegmentResult] = []

        for tariff_id in ordered_versions:
            version = next(
                v for v, _ in segments_by_version if v.tariff_id == tariff_id
            )
            segment_mask = period_mask & np.array(
                [
                    version_for_date[service_date].tariff_id == tariff_id
                    for service_date in service_dates
                ]
            )
            segment_stamps = timestamps[segment_mask]
            segment_dates = sorted({s.date() for s in segment_stamps})
            segment_import_kWh = import_kw[segment_mask] * timestep_hours
            allowance = None

            if version.energy_tiers:
                allowance = (
                    baseline or version.baseline
                ).allowance_kWh(segment_stamps, version.season_definition)
                split = version.split_tier_kWh(
                    float(segment_import_kWh.sum()), allowance
                )
                rate_by_tier = {
                    tier.name: tier.rate_per_kWh
                    for tier in version.energy_tiers
                }
                kWh_by_category = dict(split)
                charge_by_category = {
                    name: kWh * rate_by_tier[name]
                    for name, kWh in split.items()
                }
            else:
                rates = version.energy_rates(segment_stamps).to_numpy(
                    dtype=float
                )
                categories = version.billing_categories(
                    segment_stamps
                ).to_numpy()
                kWh_by_category = {}
                charge_by_category = {}
                for category in dict.fromkeys(categories):
                    category_mask = categories == category
                    kWh_by_category[str(category)] = float(
                        segment_import_kWh[category_mask].sum()
                    )
                    charge_by_category[str(category)] = float(
                        (
                            segment_import_kWh[category_mask]
                            * rates[category_mask]
                        ).sum()
                    )

            segment_days = len(segment_dates)
            segments.append(
                VersionSegmentResult(
                    tariff_id=version.tariff_id,
                    version=version.version,
                    effective_start=version.effective_start,
                    effective_end=version.effective_end,
                    source_url=version.source_url,
                    service_days=segment_days,
                    first_service_date=segment_dates[0],
                    last_service_date=segment_dates[-1],
                    import_energy_kWh=float(segment_import_kWh.sum()),
                    import_energy_charge=float(
                        sum(charge_by_category.values())
                    ),
                    customer_charge=version.customer_charge_for(segment_days, days_in_month=pd.Timestamp(segment_dates[0]).days_in_month),
                    minimum_bill_floor=version.minimum_bill_for(segment_days),
                    import_energy_kWh_by_category=kWh_by_category,
                    import_energy_charge_by_category=charge_by_category,
                    baseline_allowance_kWh=allowance,
                )
            )

        tiered_segments = [
            segment
            for segment in segments
            if segment.baseline_allowance_kWh is not None
        ]

        if len(tiered_segments) > 1:
            warnings.append(
                f"PARTIAL-CYCLE TIER ACCOUNTING: billing period {label} spans "
                f"{len(tiered_segments)} tariff versions "
                f"({', '.join(s.tariff_id for s in tiered_segments)}). The "
                f"filed schedule documents baseline proration across a "
                f"seasonal changeover (E-1 Special Condition 6) but does not "
                f"state how tier accumulation is treated when rates change "
                f"mid-cycle. Each version's days are billed as their own "
                f"sub-period, with their own prorated baseline and their own "
                f"tier ladder. This is a documented approximation, not a "
                f"filed rule."
            )

        export_kWh = float((export_kw[period_mask] * timestep_hours).sum())
        export_credit = float(
            (export_kw[period_mask] * timestep_hours * export_rates[period_mask]).sum()
        )
        export_note = (
            "No export compensation applied."
            if export_credit == 0.0
            else (
                "SCENARIO EXPORT PRICE, NOT A FILED CREDIT: this credit comes "
                "from an explicit scenario price. PG&E's NEM and Net Billing "
                "Tariff rules are not implemented, so this is not a filed "
                "solar credit and must not be presented as one."
            )
        )

        if export_credit != 0.0:
            warnings.append(export_note)

        results.append(
            TimelineBillingPeriodResult(
                meter_id=meter_id,
                plan_id=plan.identity.plan_id,
                plan_description=plan.identity.describe(),
                period_label=str(label),
                billing_days=len({d for d in period_dates}),
                segments=tuple(segments),
                export_energy_kWh=export_kWh,
                export_credit=export_credit,
                export_pricing_note=export_note,
                warnings=tuple(warnings),
            )
        )

    return tuple(results)
