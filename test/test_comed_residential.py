"""Filed-rate benchmarks and input-contract checks; no live API calls."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
import json

import numpy as np
import pandas as pd
import pytest

from src.billing.comed_rates import build_comed_residential_plans
from src.billing.comed_residential import (
    ComEdHourlyPrices, ComEdResidentialAccount, _month_grid,
    calculate_comed_residential_bill as bill,
)


def account(month=9, supply="BES", **kwargs):
    values = dict(supply=supply, delivery_class="single_family_non_electric_heat",
                  billing_month=date(2026, month, 1), ordinary_import_only_confirmed=True)
    if supply == "BESH":
        values.update(capacity_obligation_kw=2., capacity_source="Synthetic account: 2 kW billed obligation")
    return ComEdResidentialAccount(**(values | kwargs))


def meter(month=9, freq="15min"):
    start = pd.Timestamp(year=2026, month=month, day=1, tz="America/Chicago")
    return pd.Series(1., index=pd.date_range(start, start + pd.DateOffset(months=1),
                                          inclusive="left", freq=freq))


def prices(grid):
    return ComEdHourlyPrices(
        pd.Series(50., index=grid.index.tz_convert("UTC").floor("h").unique()),
        source="Synthetic hourly residual LMP fixture, not observed PJM data",
        zone="COMED", price_basis="pjm_real_time_residual_lmp",
        unit="USD/MWh", timestamp_convention="interval_start")


def lines(result):
    return {line["name"]: line["amount_usd"] for line in result["lines"]}


def test_september_independent_bes_benchmark():
    result = bill(meter(), account())
    # Independently transcribed/hand-calculated, all USD. Delivery adjustments
    # are individually rounded per official guide before forming billed rates.
    expected = {
        "customer": 15.52, "standard_metering": 3.88,
        "distribution_facilities": 45.65, "illinois_distribution_tax": .92,
        "electricity_supply": 62.48, "transmission_services": 12.41,
        "purchased_electricity_adjustment": -.63,
        "environmental_cost_recovery": .05, "renewable_portfolio_standard": 3.72,
        "zero_emission_standard": .50, "energy_efficiency_programs": 2.66,
        "energy_transition_assistance": .60, "carbon_free_resource_adjustment": -11.72,
        "coal_to_solar": .06, "low_income_discount_recovery": 1.35,
    }
    assert lines(result) == expected
    assert result["subtotal_usd"] == float(sum(map(lambda x: Decimal(str(x)), expected.values())))
    assert result["import_kwh"] == 720
    assert result["is_complete_bill"] is False and result["total_usd"] is None
    assert "franchise_costs" in result["excluded_components"]
    assert all(line["source_pdf_pages"] for line in result["lines"])
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("delivery,expected", [
    ("single_family_non_electric_heat", (15.52, 3.88, .06340, .00128)),
    ("multi_family_non_electric_heat", (11.70, 3.89, .04876, .00128)),
    ("single_family_electric_heat", (18.47, 4.10, .03218, .00136)),
    ("multi_family_electric_heat", (13.15, 4.08, .03046, .00135)),
])
def test_delivery_classes_and_component_rounding(delivery, expected):
    result = bill(meter(), account(delivery_class=delivery))
    assert tuple(row["rate_usd"] for row in result["lines"][:4]) == expected


def test_october_has_its_own_rates_and_credit_signs():
    result = bill(meter(10), account(10))
    assert result["import_kwh"] == 744
    actual = lines(result)
    assert actual["electricity_supply"] == 62.59
    assert actual["transmission_services"] == 12.57
    assert actual["purchased_electricity_adjustment"] == -11.54
    assert actual["carbon_free_resource_adjustment"] == -.86
    assert actual["coal_to_solar"] == .06
    assert result["version_id"] == "comed_residential_2026_10"


def test_hourly_weighted_energy_capacity_and_no_double_uplift():
    grid = meter()
    grid.iloc[:] = 0.
    grid.iloc[:4] = 8.  # 8 kWh during first hour, 1 kWh during second
    grid.iloc[4:8] = 1.
    p = prices(grid)
    p.values.iloc[0] = -100.
    p.values.iloc[1] = 200.
    result = bill(grid, account(supply="BESH"), hourly_prices=p)
    actual = lines(result)
    # System loss factor .0406, not class loss .0459. Negative prices survive.
    expected_energy = round((-100 * 8 + 200 * 1) / 1000 * 1.0124 * .9968 * 1.0406, 2)
    assert actual["hourly_electricity_supply"] == expected_energy
    assert actual["capacity"] == 20.20  # 2 * 10.10121, no second uplift
    assert actual["transmission_services"] == .10
    assert actual["miscellaneous_procurement"] == .01
    assert actual["purchased_electricity_adjustment"] == .03


def test_capacity_is_not_this_months_maximum_demand():
    grid = meter()
    p = prices(grid)
    a = account(supply="BESH")
    first = lines(bill(grid, a, hourly_prices=p))["capacity"]
    grid.iloc[100] = 100.
    assert lines(bill(grid, a, hourly_prices=p))["capacity"] == first
    zero = replace(a, capacity_obligation_kw=0.)
    assert lines(bill(grid, zero, hourly_prices=p))["capacity"] == 0


def test_zero_usage_keeps_fixed_charges():
    result = bill(meter() * 0, account())
    assert result["subtotal_usd"] == 20.75


@pytest.mark.parametrize("freq", ["15min", "30min", "60min"])
def test_supported_resolutions_and_utc_input_agree(freq):
    grid = meter(freq=freq)
    assert bill(grid, account())["subtotal_usd"] == bill(meter(), account())["subtotal_usd"]
    a = bill(grid, account(supply="BESH"), hourly_prices=prices(grid))
    grid.index = grid.index.tz_convert("UTC")
    b = bill(grid, account(supply="BESH"), hourly_prices=prices(grid))
    assert a == b


@pytest.mark.parametrize("month,hours", [(3, 743), (11, 721)])
def test_calendar_grid_handles_dst_without_inventing_rate_coverage(month, hours):
    # Timestamp validation is separate from tariff coverage; no fake rates.
    utc, interval_hours = _month_grid(meter(month).index, date(2026, month, 1))
    assert len(utc) * interval_hours == hours
    assert len(utc.floor("h").unique()) == hours
    with pytest.raises(ValueError, match="no filed version"):
        bill(meter(month), account(month))


@pytest.mark.parametrize("month", [1, 8, 11, 12])
def test_unsupported_months_reject(month):
    with pytest.raises(ValueError, match="no filed version"):
        bill(meter(month), account(month))


@pytest.mark.parametrize("change", ["gap", "duplicate", "reverse", "naive", "partial", "5min", "wrong_month"])
def test_invalid_meter_grid_rejects(change):
    grid = meter()
    if change == "gap": grid = grid.drop(grid.index[4])
    if change == "duplicate": grid = pd.concat([grid.iloc[:1], grid])
    if change == "reverse": grid = grid.iloc[::-1]
    if change == "naive": grid.index = grid.index.tz_localize(None)
    if change == "partial": grid = grid.iloc[4:]
    if change == "5min": grid = meter(freq="5min")
    if change == "wrong_month": grid = meter(10)
    with pytest.raises(ValueError): bill(grid, account())


@pytest.mark.parametrize("value", [-1., np.nan, np.inf, True, "1", 1j])
def test_invalid_power_rejects(value):
    grid = meter()
    if isinstance(value, (str, bool, complex)): grid = pd.Series(value, index=grid.index)
    else: grid.iloc[0] = value
    with pytest.raises(ValueError): bill(grid, account())


@pytest.mark.parametrize("change", ["gap", "extra", "reverse", "duplicate", "naive", "shift", "nan", "bool", "15min"])
def test_hourly_price_grid_and_values_are_strict(change):
    grid = meter(); p = prices(grid); v = p.values.copy()
    if change == "gap": v = v.drop(v.index[0])
    if change == "extra": v.loc[v.index[-1] + pd.Timedelta(hours=1)] = 50.
    if change == "reverse": v = v.iloc[::-1]
    if change == "duplicate": v = pd.concat([v.iloc[:1], v])
    if change == "naive": v.index = v.index.tz_localize(None)
    if change == "shift": v.index += pd.Timedelta(hours=1)
    if change == "nan": v.iloc[0] = np.nan
    if change == "bool": v = pd.Series(True, index=v.index)
    if change == "15min": v = grid.copy()
    with pytest.raises(ValueError):
        bill(grid, account(supply="BESH"), hourly_prices=replace(p, values=v))


@pytest.mark.parametrize("patch", [
    {"zone": "WESTERN HUB"}, {"price_basis": "day_ahead_lmp"},
    {"price_basis": "adjusted_comed_retail"}, {"unit": "cents/kWh"},
    {"timestamp_convention": "hour_ending"}, {"source": ""},
])
def test_incompatible_price_basis_rejects(patch):
    grid = meter()
    with pytest.raises(ValueError):
        bill(grid, account(supply="BESH"), hourly_prices=replace(prices(grid), **patch))


@pytest.mark.parametrize("patch", [
    {"supply": "BEST"}, {"delivery_class": "commercial"},
    {"ordinary_import_only_confirmed": False}, {"ordinary_import_only_confirmed": 1},
    {"billing_month": date(2026, 9, 2)}, {"billing_month": "2026-09"},
    {"capacity_obligation_kw": 1.},
])
def test_unsupported_account_rejects(patch):
    with pytest.raises(ValueError): bill(meter(), account(**patch))


@pytest.mark.parametrize("patch", [
    {"capacity_obligation_kw": None}, {"capacity_obligation_kw": -1},
    {"capacity_obligation_kw": True}, {"capacity_obligation_kw": np.inf},
    {"capacity_source": None}, {"capacity_source": ""},
])
def test_hourly_requires_documented_capacity(patch):
    grid = meter()
    with pytest.raises(ValueError):
        bill(grid, account(supply="BESH", **patch), hourly_prices=prices(grid))


def test_supply_inputs_cannot_be_silently_ignored():
    grid = meter()
    with pytest.raises(ValueError): bill(grid, account(), hourly_prices=prices(grid))
    with pytest.raises(ValueError): bill(grid, account(supply="BESH"))


def test_plan_catalog_has_eight_choices_and_bounded_versions():
    plans = build_comed_residential_plans()
    assert len({p.identity.plan_id for p in plans}) == 8
    for plan in plans:
        assert len(plan.versions) == 2
        assert plan.version_on(date(2026, 9, 1)).bes_energy == Decimal(".08678")
        assert plan.version_on(date(2026, 10, 31)).bes_energy == Decimal(".08413")
        with pytest.raises(ValueError): plan.version_on(date(2026, 11, 1))
