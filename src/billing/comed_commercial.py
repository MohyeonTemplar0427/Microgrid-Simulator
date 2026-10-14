"""ComEd ordinary commercial BES/BESH, September/October 2026 billing months.

One service voltage and ordinary non-exempt account; no export/standby,
special contracts, lighting, railroads or alternate supplier settlement.
Returns a subtotal with the same tax/franchise exclusions as residential.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal as D
from numbers import Real
from types import MappingProxyType

import numpy as np
import pandas as pd

from . import comed_rates as rates
from .comed_residential import (
    ComEdHourlyPrices, _month_grid, _numeric_series, _hourly_energy_cost, _round,
)
from .municipal import nerc_holidays
from .plans import RatePlan, RatePlanIdentity


@dataclass(frozen=True)
class CommercialDelivery:
    customer: D
    meter: D
    secondary: D
    primary: D
    transformer: D
    rbaf: D
    dgra: D
    iduf: D
    source_page: int


# 2026 base prices: informational sheets64.3/64.5/64.7 (pp850/852/854).
# RBAF p799; DGRA p839; IDUFN/IDUFA p801. All rates in dollars.
def _delivery(cc, meter, sv, pv, tc, rbaf, dgra, iduf, page):
    return CommercialDelivery(*(D(x) for x in (cc, meter, sv, pv, tc, rbaf, dgra, iduf)), page)


DELIVERY = MappingProxyType({
    "watt_hour": _delivery("15.01", "2.66", ".02854", "0", "0", "-.067279", ".00034", "1.0042", 850),
    "small": _delivery("14.62", "6.71", "12.50", "5.53", ".36", "-.055901", ".15", "1.0042", 850),
    "medium": _delivery("24.78", "11.56", "12.78", "7.18", ".36", "-.070968", ".15", "1.0042", 850),
    "large": _delivery("145.77", "11.88", "12.47", "9.78", ".45", "-.054212", ".15", "1.0042", 852),
    "very_large": _delivery("898.11", "12.33", "11.49", "9.33", ".45", "-.004777", ".13", "1.0005", 852),
    "extra_large": _delivery("2051.45", "35.00", "11.63", "10.83", ".50", "-.139901", ".13", "1.0005", 852),
    "high_voltage": _delivery("710.36", "32.06", "0", "0", "0", "-.036869", "0", "1.0005", 854),
})
DELIVERY_2025 = MappingProxyType({
    "watt_hour": _delivery("14.74", "2.65", ".02883", "0", "0", "0", ".00026", "1.0017", 850),
    "small": _delivery("14.42", "6.74", "12.71", "5.60", ".35", "0", ".11", "1.0017", 850),
    "medium": _delivery("24.32", "11.63", "13.02", "7.36", ".35", "0", ".12", "1.0017", 850),
    "large": _delivery("143.55", "11.94", "12.72", "10.04", ".44", "0", ".11", "1.0017", 852),
    "very_large": _delivery("878.23", "12.39", "11.77", "9.63", ".44", "0", ".10", "1.0005", 852),
    "extra_large": _delivery("2011.40", "35.10", "11.43", "10.71", ".48", "0", ".10", "1.0005", 852),
    "high_voltage": _delivery("701.57", "32.11", "0", "0", "0", "0", "0", "1.0005", 854),
})
DELIVERY_BY_YEAR = MappingProxyType({2025: DELIVERY_2025, 2026: DELIVERY})
HV_BASES = MappingProxyType({2025: ((D(".66"), D("4.76")), (D(".62"), D("2.56"))),
                            2026: ((D(".71"), D("4.61")), (D(".44"), D("2.46")))})


@dataclass(frozen=True)
class ComEdCommercialAccount:
    supply: str
    delivery_class: str
    billing_month: date
    ordinary_import_only_confirmed: bool
    service_voltage: str  # secondary, primary, high_voltage; one voltage only
    utility_transformer: bool
    previous_12_month_peak_kw: float
    previous_calendar_year_peak_kw: float
    competitively_declared: bool
    previous_year_months_ge_100kw: int
    electric_space_heat: bool
    watt_hour_eligibility: str  # not_applicable, legacy_pre_2022, dedicated_ev
    eligibility_source: str
    previous_12_month_mkd_kw: float | None = None
    capacity_obligation_kw: float | None = None
    capacity_source: str | None = None


@dataclass(frozen=True)
class ComEdCommercialVersion:
    tariff_id: str
    effective_start: date
    effective_end: date
    bes_watt_energy: D
    bes_demand_energy: D
    bes_heat_energy: D
    bes_transmission: D
    bes_adjustment: D
    besh_transmission: D
    besh_procurement: D
    besh_adjustment: D
    carbon_free_adjustment: D
    coal_to_solar: D
    common: rates.ComEdVersion

    def is_effective_on(self, day):
        return self.effective_start <= day <= self.effective_end


# Share only the verified common monthly riders with residential; supply
# subgroups and the version identity are explicitly commercial.
VERSIONS = tuple(ComEdCommercialVersion(
    f"comed_commercial_{v.effective_start.year}_{v.effective_start.month:02}", v.effective_start, v.effective_end,
    *v.commercial_supply, v.bes_adjustment, v.besh_transmission,
    v.besh_procurement, v.besh_adjustment, v.carbon_free_adjustment, v.coal_to_solar, v,
) for v in rates.VERSIONS)


def build_comed_commercial_plans():
    return tuple(RatePlan(RatePlanIdentity("ComEd", supply, "bundled", "commercial", delivery),
                          tuple(v for v in VERSIONS if supply == "BES" or v.besh_adjustment is not None))
                 for supply in ("BES", "BESH") for delivery in DELIVERY)


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, Real) or not np.isfinite(value) or value < 0:
        raise ValueError(label + " must be a finite nonnegative number.")


def validate_account(a):
    if not isinstance(a, ComEdCommercialAccount) or a.delivery_class not in DELIVERY or a.supply not in ("BES", "BESH"):
        raise ValueError("Choose a supported ComEd commercial class and BES/BESH supply.")
    if a.ordinary_import_only_confirmed is not True or not isinstance(a.eligibility_source, str) or not a.eligibility_source.strip():
        raise ValueError("Confirm an ordinary non-exempt import-only account and document utility eligibility or a labeled study assumption.")
    if type(a.billing_month) is not date or a.billing_month.day != 1:
        raise ValueError("billing_month must be the first date of the confirmed billing month.")
    for name in ("utility_transformer", "competitively_declared", "electric_space_heat"):
        if type(getattr(a, name)) is not bool:
            raise ValueError(name + " must be a boolean.")
    for name in ("previous_12_month_peak_kw", "previous_calendar_year_peak_kw"):
        _number(getattr(a, name), name)
    if type(a.previous_year_months_ge_100kw) is not int or not 0 <= a.previous_year_months_ge_100kw <= 12:
        raise ValueError("Supply 0–12 previous-calendar-year months with demand >=100 kW.")
    if (a.previous_calendar_year_peak_kw >= 100) != (a.previous_year_months_ge_100kw > 0):
        raise ValueError("Previous-year peak and months >=100 kW contradict each other.")
    # Delivery class uses the highest demand in the PRECEDING twelve cycles;
    # it does not impose a ratchet on this month's billed MKD (pp181–183).
    bands = {"small": (0, 100), "medium": (100, 400), "large": (400, 1000),
             "very_large": (1000, 10000), "extra_large": (10000, float("inf"))}
    if a.delivery_class in bands:
        lo, hi = bands[a.delivery_class]
        if not (lo < a.previous_12_month_peak_kw <= hi or a.delivery_class == "small" and a.previous_12_month_peak_kw == 0):
            raise ValueError("Delivery class does not match the preceding twelve-month maximum (not current-month MKD).")
    if a.delivery_class == "watt_hour":
        if a.watt_hour_eligibility not in ("legacy_pre_2022", "dedicated_ev") or a.service_voltage != "secondary":
            raise ValueError("Watt-Hour requires a confirmed pre-2022 legacy account or dedicated EV service; this adapter supports secondary service only.")
        if a.watt_hour_eligibility == "legacy_pre_2022" and a.supply == "BESH":
            raise ValueError("Legacy watt-hour-only metering cannot be assumed eligible for hourly supply; verify a demand-metered account/class first.")
    elif a.watt_hour_eligibility != "not_applicable":
        raise ValueError("Watt-Hour eligibility is only applicable to Watt-Hour delivery.")
    if a.delivery_class == "high_voltage":
        _number(a.previous_12_month_mkd_kw, "previous_12_month_mkd_kw")
        if a.previous_12_month_mkd_kw > a.previous_12_month_peak_kw:
            raise ValueError("Prior MKD cannot exceed the prior overall peak over the same twelve months.")
        if a.service_voltage != "high_voltage":
            raise ValueError("High Voltage class requires a single service point at >=69 kV.")
    elif a.service_voltage not in ("secondary", "primary"):
        raise ValueError("Choose secondary or primary service for this delivery class.")
    if a.delivery_class != "high_voltage" and a.previous_12_month_mkd_kw is not None:
        raise ValueError("Separate prior MKD applies only to High Voltage delivery in this adapter.")
    if a.service_voltage == "secondary" and not a.utility_transformer:
        raise ValueError("Secondary service here requires utility transformation to below 2.4 kV.")
    if a.supply == "BES":
        if a.competitively_declared or a.previous_year_months_ge_100kw >= 2:
            raise ValueError("BES is unavailable to competitively declared customers; choose BESH or a separately modeled supplier contract.")
        if a.capacity_obligation_kw is not None or a.capacity_source is not None:
            raise ValueError("BES already includes capacity; do not supply a separate obligation.")
    else:
        _number(a.capacity_obligation_kw, "capacity_obligation_kw")
        if not isinstance(a.capacity_source, str) or not a.capacity_source.strip():
            raise ValueError("Document the account capacity obligation or a labeled study assumption.")
    plan = next(p for p in build_comed_commercial_plans()
                if p.identity.schedule == a.supply and p.identity.variant == a.delivery_class)
    return plan, plan.version_on(a.billing_month)


def mkd_mask(index):
    local = index.tz_convert("America/Chicago")
    holidays = set().union(*(nerc_holidays(y) for y in set(local.year)))
    return (local.dayofweek < 5) & (local.hour >= 9) & (local.hour < 18) & ~np.isin(local.date, list(holidays))


def calculate_comed_commercial_bill(grid_import_kw, account, *, hourly_prices: ComEdHourlyPrices | None = None, billing_cycle=None):
    plan, version = validate_account(account)
    if not isinstance(grid_import_kw, pd.Series):
        raise ValueError("Supply a timestamped meter-import Series.")
    if billing_cycle is None:
        utc, duration = _month_grid(grid_import_kw.index, account.billing_month)
    else:
        from .comed_cycles import cycle_grid
        if billing_cycle.billing_month != account.billing_month:
            raise ValueError("Account and cycle billing-month designations differ.")
        utc, duration = cycle_grid(grid_import_kw.index, billing_cycle)
    power = _numeric_series(grid_import_kw, utc, "grid_import_kw", nonnegative=True)
    if duration > D(".5"):
        raise ValueError("Commercial demand requires 15- or 30-minute meter data; hourly peaks cannot establish 30-minute demand.")
    # Align non-overlapping XX:00/XX:30 blocks. Energy is preserved.
    half_hour = pd.Series(power, index=utc).resample("30min").mean()
    eligible = half_hour[mkd_mask(half_hour.index)]
    mkd = D(str(float(eligible.max()))) if len(eligible) else D(0)
    overall_peak = float(half_hour.max())
    energy = tuple(D(str(v)) * duration for v in power)
    kwh = sum(energy, D(0)); a = account; common = version.common
    d = DELIVERY_BY_YEAR[common.delivery_year][a.delivery_class]
    lines = []

    def add(name, quantity, rate, category, pages, unit="kWh"):
        factor = billing_cycle.factor(name) if billing_cycle else D(1)
        documents = rates.line_sources(version.common, name, pages)
        lines.append({"name": name, "category": category, "quantity": float(quantity),
                      "quantity_unit": unit, "rate_usd": float(rate),
                      "amount_usd": float(_round(quantity * rate * factor)),
                      "billing_multiplier": float(factor), "source_pdf_pages": documents[0]["pdf_pages"],
                      "source_documents": documents})

    iduf = version.common.large_iduf if a.delivery_class in ("very_large", "extra_large", "high_voltage") else version.common.nonresidential_iduf
    factors = (iduf - 1, common.delivery_reconciliation, common.excess_deferred_income_tax,
               common.total_plan_adjustment, d.rbaf)
    def adjusted(base, quantum=".01", factors=factors):
        return base + sum((_round(base*f, quantum) for f in factors), D(0))
    # RCA pp394/824 and LID p876 use PREVIOUS CALENDAR YEAR, not rolling year.
    big = a.previous_calendar_year_peak_kw >= 10000
    adjustment_pages = [790, 799, 801, 845, 864, 865, 866]
    add("customer", D(1), adjusted(d.customer) + (common.large_commercial_assessment if big else common.small_commercial_assessment), "delivery", [d.source_page, 394, 803, 824] + adjustment_pages, "month")
    add("standard_metering", D(1), adjusted(d.meter), "delivery", [d.source_page] + adjustment_pages, "month")
    if a.delivery_class == "watt_hour":
        add("distribution_facilities", kwh, adjusted(d.secondary, ".00001") + d.dgra, "delivery", [850, 839] + adjustment_pages)
    else:
        if a.service_voltage == "high_voltage":
            # No DGRA added to HV DFC or HV transformer: sheet64.17 formula.
            base, transformer = HV_BASES[common.delivery_year][int(a.previous_12_month_mkd_kw > 10000)]
        else:
            base = d.secondary if a.service_voltage == "secondary" else d.primary
            transformer = d.transformer if a.service_voltage == "primary" else D(0)
        rate = adjusted(base) + (D(0) if a.service_voltage == "high_voltage" else d.dgra)
        add("distribution_demand", mkd, rate, "delivery", [d.source_page, 174, 839] + adjustment_pages, "kW")
        if a.utility_transformer and transformer:
            add("transformer_demand", mkd, adjusted(transformer), "delivery", [d.source_page, 26, 58] + adjustment_pages, "kW")
    add("illinois_distribution_tax", kwh, adjusted(D(".00124"), ".00001", (iduf-1, d.rbaf)), "delivery", [d.source_page, 864, 799, 801])
    if a.supply == "BES":
        if hourly_prices is not None:
            raise ValueError("BES uses filed supply rates, not hourly prices.")
        # Filed nonresidential supply subgroups, sheet1. Dedicated EV is Demand
        # supply despite Watt-Hour delivery (sheet139), not legacy WH supply.
        legacy = a.delivery_class == "watt_hour" and a.watt_hour_eligibility == "legacy_pre_2022"
        group = "heat" if a.electric_space_heat else "watt" if legacy else "demand"
        pec = getattr(version, "bes_" + group + "_energy")
        add("electricity_supply", kwh, pec, "supply", [782])
        add("transmission_services", kwh, version.bes_transmission, "supply", [783])
        add("purchased_electricity_adjustment", kwh, version.bes_adjustment, "supply", [784])
    else:
        cost = _hourly_energy_cost(hourly_prices, utc, energy, version.common.hec_multiplier)
        lines.append({"name": "hourly_electricity_supply", "category": "supply", "quantity": float(kwh),
                      "quantity_unit": "kWh", "rate_usd": None, "amount_usd": float(_round(cost)),
                      "source_pdf_pages": rates.line_sources(common, "hourly_electricity_supply", [60, 801, 802, 814])[0]["pdf_pages"],
                      "source_documents": rates.line_sources(version.common, "hourly_electricity_supply", [60, 801, 802, 814])})
        add("capacity", D(str(a.capacity_obligation_kw)), version.common.capacity, "supply", [785], "kW")
        add("transmission_services", kwh, version.besh_transmission, "supply", [786])
        add("miscellaneous_procurement", kwh, version.besh_procurement, "supply", [787])
        add("purchased_electricity_adjustment", kwh, version.besh_adjustment, "supply", [788])
    for name, (rate, page) in rates.COMMON_ENERGY.items():
        rate = getattr(common, name)
        if name == "energy_efficiency_programs":
            rate = common.large_commercial_efficiency if a.delivery_class in ("very_large", "extra_large", "high_voltage") else common.small_commercial_efficiency
        add(name, kwh, rate, "riders", [page])
    add("carbon_free_resource_adjustment", kwh, version.carbon_free_adjustment, "riders", [818])
    add("coal_to_solar", kwh, version.coal_to_solar, "riders", [846])
    lid = common.large_commercial_lid_recovery if big else common.small_commercial_lid_recovery
    if lid is not None:
        add("low_income_discount_recovery", D(1), lid, "riders", [876], "month")
    return {"plan_id": plan.identity.plan_id, "version_id": version.tariff_id,
            "billing_month": a.billing_month.isoformat(), "timezone": "America/Chicago",
            "billing_cycle": rates.cycle_source(billing_cycle, common),
            "import_kwh": float(kwh), "overall_30min_peak_kw": overall_peak, "billed_mkd_kw": float(mkd),
            "lines": lines, "subtotal_usd": float(sum((D(str(x["amount_usd"])) for x in lines), D(0))),
            "total_usd": None, "is_complete_bill": False,
            "excluded_components": ["state_electricity_excise_tax", "municipal_utility_taxes", "franchise_costs"],
            "source": {**rates.primary_source(common),
                       "verified_on": "2026-10-13", "eligibility_source": a.eligibility_source,
                       "delivery_adjustment_sources": rates.line_sources(common, "delivery_adjustments", adjustment_pages + [839]),
                       "holiday_source": "ComEd GTC MKD definition; NERC holiday calendar for the service year",
                       "capacity_source": a.capacity_source, "hourly_price_source": hourly_prices.source if hourly_prices else None,
                       "hourly_energy_multiplier": float(version.common.hec_multiplier) if hourly_prices else None,
                       "historical_source_references": list(version.common.source_references)}}
