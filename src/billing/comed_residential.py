"""ComEd residential BES/BESH subtotal for one complete calendar billing month.

Standard delivery, one meter, no special rider/discount or generation/export
settlement. Taxes and franchise fees are explicitly excluded; this is NOT a
complete invoice or an optimizer. Hourly energy requires validated external
PJM ComEd-zone real-time residual LMP observations, never a generic PJM hub.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from numbers import Real

import numpy as np
import pandas as pd

from . import comed_rates as rates

D = Decimal
TIMEZONE = "America/Chicago"


@dataclass(frozen=True)
class ComEdResidentialAccount:
    supply: str
    delivery_class: str
    billing_month: date
    ordinary_import_only_confirmed: bool
    capacity_obligation_kw: float | None = None
    capacity_source: str | None = None


@dataclass(frozen=True)
class ComEdHourlyPrices:
    """An explicit price contract; constructor does not fetch or infer prices."""
    values: pd.Series
    source: str
    zone: str
    price_basis: str
    unit: str
    timestamp_convention: str


def _round(value: D, quantum: str = ".01") -> D:
    return value.quantize(D(quantum), rounding=ROUND_HALF_UP)


def _validate_account(account):
    if not isinstance(account, ComEdResidentialAccount):
        raise ValueError("Supply a ComEdResidentialAccount.")
    if account.supply not in ("BES", "BESH") or account.delivery_class not in rates.DELIVERY:
        raise ValueError("Select residential BES/BESH and one of the four supported delivery classes.")
    if account.ordinary_import_only_confirmed is not True:
        raise ValueError("Confirm one ordinary residential meter, standard delivery, no discounts, special riders or generation/export settlement.")
    if type(account.billing_month) is not date or account.billing_month.day != 1:
        raise ValueError("billing_month must be a date at the first of the utility billing month.")
    if account.supply == "BESH":
        capacity = account.capacity_obligation_kw
        if isinstance(capacity, bool) or not isinstance(capacity, Real) or not np.isfinite(capacity) or capacity < 0:
            raise ValueError("BESH requires a finite nonnegative capacity_obligation_kw; never inferred from this month's peak.")
        if not isinstance(account.capacity_source, str) or not account.capacity_source.strip():
            raise ValueError("BESH requires capacity_source documenting the account's billed obligation or labeled study assumption.")
    elif account.capacity_obligation_kw is not None or account.capacity_source is not None:
        raise ValueError("BES already includes capacity: do not supply a separate capacity obligation.")
    plan = next(p for p in rates.build_comed_residential_plans()
                if p.identity.schedule == account.supply and p.identity.variant == account.delivery_class)
    return plan, plan.version_on(account.billing_month)


def _month_grid(index, month):
    """Validate physical intervals in UTC against local calendar boundaries."""
    if not isinstance(index, pd.DatetimeIndex) or index.tz is None or len(index) < 2:
        raise ValueError("Supply timezone-aware interval-start timestamps.")
    utc = index.tz_convert("UTC")
    if not utc.is_unique or not utc.is_monotonic_increasing or utc.hasnans:
        raise ValueError("Timestamps must be ordered, unique and nonmissing.")
    step = utc[1] - utc[0]
    if step not in tuple(pd.Timedelta(minutes=m) for m in (15, 30, 60)):
        raise ValueError("Supported meter intervals are 15, 30 or 60 minutes.")
    start = pd.Timestamp(month, tz=TIMEZONE)
    end = start + pd.DateOffset(months=1)
    expected = pd.date_range(start, end, freq=step, inclusive="left").tz_convert("UTC")
    if not utc.equals(expected):
        raise ValueError("Supply one complete calendar month matching billing_month, without gaps; partial or cross-month meter cycles are not supported yet.")
    return utc, D(str(step.total_seconds())) / D(3600)


def _numeric_series(values, index, name, *, nonnegative):
    if not isinstance(values, pd.Series) or not isinstance(values.index, pd.DatetimeIndex) or values.index.tz is None:
        raise ValueError(name + " must be a timestamped pandas Series.")
    if not values.index.tz_convert("UTC").equals(index):
        raise ValueError(name + " timestamps must exactly match the requested grid.")
    if not pd.api.types.is_numeric_dtype(values.dtype) or pd.api.types.is_bool_dtype(values.dtype) or pd.api.types.is_complex_dtype(values.dtype):
        raise ValueError(name + " must contain real numeric values, not booleans or strings.")
    if values.isna().any():
        raise ValueError(name + " has missing values.")
    array = values.to_numpy(dtype=float)
    if not np.isfinite(array).all() or (nonnegative and (array < 0).any()):
        raise ValueError(name + " must be finite" + (" and nonnegative (exports are unsupported)." if nonnegative else "."))
    return array


def _hourly_energy_cost(prices, utc, energy):
    if not isinstance(prices, ComEdHourlyPrices):
        raise ValueError("BESH requires ComEdHourlyPrices.")
    if (prices.zone, prices.price_basis, prices.unit, prices.timestamp_convention) != (
        "COMED", "pjm_real_time_residual_lmp", "USD/MWh", "interval_start"
    ):
        raise ValueError("Require COMED real-time residual LMP in USD/MWh at interval starts; no day-ahead, hub or already-adjusted retail prices.")
    if not isinstance(prices.source, str) or not prices.source.strip():
        raise ValueError("Hourly prices require a source reference.")
    hours = utc.floor("h").unique()
    raw = _numeric_series(prices.values, hours, "hourly prices", nonnegative=False)
    # Index-based mapping, including distinct UTC hours across a DST fold.
    positions = hours.get_indexer(utc.floor("h"))
    return sum((kwh * D(str(raw[pos])) / D(1000) * rates.HEC_MULTIPLIER
                for kwh, pos in zip(energy, positions)), D(0))


def _delivery_rates(delivery):
    """Round each adjustment before adding, as the official billing guide does."""
    def adjusted(base, quantum, factors):
        return base + sum((_round(base * factor, quantum) for factor in factors), D(0))
    factors = (rates.IDUF - 1, rates.DRAF, rates.EDAF, rates.TPAF, delivery.revenue_balancing_factor)
    return {
        "customer": adjusted(delivery.customer, ".01", factors) + rates.RCA,
        "standard_metering": adjusted(delivery.meter, ".01", factors),
        "distribution_facilities": adjusted(delivery.distribution, ".00001", factors) + rates.DGRA,
        "illinois_distribution_tax": adjusted(delivery.iedt, ".00001", (rates.IDUF - 1, delivery.revenue_balancing_factor)),
    }


def calculate_comed_residential_bill(
    grid_import_kw: pd.Series,
    account: ComEdResidentialAccount,
    *,
    hourly_prices: ComEdHourlyPrices | None = None,
) -> dict:
    """Return itemized USD subtotal, provenance and explicit completeness limits.

    Values are average meter-import kW over intervals beginning at their index.
    Zero usage still incurs monthly fixed charges. Negative energy prices and
    filed rider credits retain their signs. No missing data are filled.
    """
    plan, version = _validate_account(account)
    if not isinstance(grid_import_kw, pd.Series):
        raise ValueError("grid_import_kw must be a timestamped pandas Series.")
    utc, hours = _month_grid(grid_import_kw.index, account.billing_month)
    power = _numeric_series(grid_import_kw, utc, "grid_import_kw", nonnegative=True)
    energy = tuple(D(str(kw)) * hours for kw in power)
    kwh = sum(energy, D(0))
    lines = []

    def add(name, quantity, rate, pages, category):
        lines.append({"name": name, "category": category, "quantity": float(quantity),
                      "rate_usd": float(rate), "amount_usd": float(_round(quantity * rate)),
                      "source_pdf_pages": list(pages)})

    for name, rate in _delivery_rates(rates.DELIVERY[account.delivery_class]).items():
        fixed = name in ("customer", "standard_metering")
        pages = [848, 864, 865, 801, 799]
        if name != "illinois_distribution_tax":
            pages += [790, 845, 866]
        if name == "distribution_facilities":
            pages += [839]
        if name == "customer":
            pages += [394, 396, 803, 824]
        add(name, D(1) if fixed else kwh, rate, pages, "delivery")

    if account.supply == "BES":
        if hourly_prices is not None:
            raise ValueError("BES uses filed supply rates; hourly prices must not alter this bill.")
        add("electricity_supply", kwh, version.bes_energy, [782], "supply")
        add("transmission_services", kwh, version.bes_transmission, [783], "supply")
        add("purchased_electricity_adjustment", kwh, version.bes_adjustment, [784], "supply")
    else:
        hourly_cost = _hourly_energy_cost(hourly_prices, utc, energy)
        lines.append({"name": "hourly_electricity_supply", "category": "supply",
                      "quantity": float(kwh), "rate_usd": None,
                      "amount_usd": float(_round(hourly_cost)),
                      "source_pdf_pages": [60, 801, 802, 814]})
        add("capacity", D(str(account.capacity_obligation_kw)), rates.CAPACITY, [785], "supply")
        add("transmission_services", kwh, version.besh_transmission, [786], "supply")
        add("miscellaneous_procurement", kwh, version.besh_procurement, [787], "supply")
        add("purchased_electricity_adjustment", kwh, version.besh_adjustment, [788], "supply")

    for name, (rate, page) in rates.COMMON_ENERGY.items():
        add(name, kwh, rate, [page], "riders")
    add("carbon_free_resource_adjustment", kwh, version.carbon_free_adjustment, [818], "riders")
    add("coal_to_solar", kwh, version.coal_to_solar, [846], "riders")
    add("low_income_discount_recovery", D(1), rates.LID_RECOVERY, [876], "riders")
    subtotal = sum((D(str(line["amount_usd"])) for line in lines), D(0))
    return {
        "plan_id": plan.identity.plan_id, "version_id": version.tariff_id,
        "billing_month": account.billing_month.isoformat(), "timezone": TIMEZONE,
        "import_kwh": float(kwh), "lines": lines, "subtotal_usd": float(subtotal),
        "total_usd": None, "is_complete_bill": False,
        "excluded_components": ["state_electricity_excise_tax", "municipal_utility_taxes", "franchise_costs"],
        "source": {"ratebook_url": rates.RATEBOOK_URL, "ratebook_sha256": rates.RATEBOOK_SHA256,
                   "verified_on": "2026-10-12", "applicability_basis": "utility_billing_month",
                   "capacity_obligation_kw": account.capacity_obligation_kw,
                   "capacity_source": account.capacity_source,
                   "hourly_price_source": hourly_prices.source if hourly_prices else None,
                   "hourly_energy_multiplier": float(rates.HEC_MULTIPLIER) if hourly_prices else None},
    }
