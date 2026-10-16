"""Offline filed-arithmetic, calendar, history and optimizer parity checks."""
from copy import deepcopy
from datetime import date

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import dominion_nc as nc
from src.billing.regional_math import BillingMath


def grid(start="2026-08-01", end="2026-09-01", minutes=15):
    return pd.date_range(start, end, freq=f"{minutes}min", inclusive="left", tz="America/New_York")


def bill(plan="1T", power=1., *, index=None, account=None, exports=None, state=None):
    index = grid() if index is None else index
    a = nc.defaults(plan) if account is None else deepcopy(account)
    a["billing_month"] = index[0].month
    if plan == "6L" and state is None:
        a["history_billing_months"] = [((a["billing_month"]-12+i) % 12)+1 for i in range(11)]
    imports = np.broadcast_to(power, len(index)).copy()
    return nc.charge_lines(index, imports, np.zeros(len(index)) if exports is None else exports,
                           a, math=BillingMath(index), state=state)


@pytest.mark.parametrize("plan", list(nc.BASE))
def test_catalog_every_ordinary_plan_has_an_executable_bill(plan):
    r = bill(plan, 4000 if plan == "6L" else 750 if plan == "6P" else 1)
    assert np.isfinite(sum(r["lines"].values()))
    assert r["is_complete_bill"] is True
    assert r["lines"]["nc_sales_tax"] == pytest.approx(sum(v for k, v in r["lines"].items() if k != "nc_sales_tax")*.07)


def test_schedule1_independent_utility_worksheet_benchmark():
    # Utility workbook, Rate Update Sheet, revision July 29, 2026. Billing
    # month August, 31 days, 744 kWh. No calculator/model helper is reused.
    expected_energy = 744*.121533
    expected_riders = 744*(.005198+.001023+.005602+.001394+.001027+.000133)
    expected_pretax = 14.4+expected_energy+expected_riders+.84-.26
    r = bill("1")
    assert sum(r["lines"].values()) == pytest.approx(expected_pretax*1.07, abs=1e-9)
    assert sum(r["lines"].values()) == pytest.approx(124.2238328)


def test_schedule5p_independent_benchmark():
    # August 2026 has 21 non-holiday weekdays. Constant30 kW: 252 on-peak
    # hours,492 off-peak; an unchanged100 kW distribution contract.
    r = bill("5P", 30)
    base = 96.93+30*11.761+100*2.260+30*252*.064306+30*492*.046025
    riders = 22320*(.003+.000481+.005593+.000618+.001026+.000142)+4.70-1.49
    assert sum(r["lines"].values()) == pytest.approx((base+riders)*1.07, abs=1e-8)


@pytest.mark.parametrize("plan", ["1P", "1T", "5P", "6P"])
@pytest.mark.parametrize("day", ["2026-01-01", "2026-04-03", "2026-05-25", "2026-07-04", "2026-09-07", "2026-11-26", "2026-11-27", "2026-12-24", "2026-12-25"])
def test_filed_nc_holiday_list(plan, day):
    index = pd.date_range(day, periods=96, freq="15min", tz="America/New_York")
    assert not nc.on_peak(index, plan).any()
    assert not nc.on_peak(index, plan, demand=True).any()


def test_no_unfiled_friday_substitution_and_6l_has_no_weekend_override():
    # Independence Day2026 is Saturday. July3 remains an ordinary weekday.
    index = pd.DatetimeIndex([pd.Timestamp("2026-07-03 14:00", tz="America/New_York")])
    assert nc.on_peak(index, "1T").item()
    holiday = pd.DatetimeIndex([pd.Timestamp("2026-12-25 10:00", tz="America/New_York")])
    assert nc.on_peak(holiday, "6L").item()


def test_nc_residential_half_hour_boundary_and_commercial_distinct_demand_hours():
    index = pd.DatetimeIndex([pd.Timestamp("2026-01-06 "+t, tz="America/New_York") for t in ("06:15", "06:30", "11:45", "12:00", "13:00", "17:00", "21:00", "22:00")])
    assert nc.on_peak(index, "1T").tolist() == [False, True, True, False, False, True, False, False]
    assert nc.on_peak(index, "5P").tolist() == [True, True, True, True, True, True, True, False]
    assert nc.on_peak(index, "5P", demand=True).tolist() == [True, True, True, False, False, True, True, False]


@pytest.mark.parametrize("start,end,count", [("2025-03-08", "2025-03-11", 284), ("2025-11-01", "2025-11-04", 292)])
def test_dst_preserves_physical_intervals_and_calendar_days(start, end, count):
    index = grid(start, end)
    r = bill("1", index=index)
    assert len(index) == count
    assert r["metrics"]["billing_days"] == 3
    assert r["metrics"]["import_kwh"] == pytest.approx(count*.25)
    assert r["lines"]["customer"] == pytest.approx(1.44)


def test_half_hour_demand_averages_aligned_quarters():
    index = grid("2026-08-03", "2026-08-04")
    p = np.zeros(len(index))
    p[40], p[41] = 20., 0.
    r = bill("5P", p, index=index)
    assert r["metrics"]["measured_peak_kw"] == 10
    assert r["metrics"]["on_peak_demand_kw"] == 10
    assert r["lines"]["on_peak_supply_demand"] == pytest.approx(10*11.761/30)


@pytest.mark.parametrize("days,factor", [(1, 1/30), (25, 25/30), (26, 1), (31, 1), (40, 1)])
def test_monthly_customer_proration_thresholds(days, factor):
    start = pd.Timestamp("2026-08-01")
    index = grid(start, start+pd.DateOffset(days=days))
    r = bill("1", index=index)
    assert r["lines"]["customer"] == pytest.approx(14.4*factor)


def test_30day_large_general_charge_does_not_borrow_monthly_proration():
    r = bill("6P", 750)
    assert r["lines"]["customer"] == pytest.approx(106.01*31/30)
    assert r["lines"]["distribution_demand"] == pytest.approx(750*1.723*31/30)


def test_billing_month_not_service_date_sets_schedule1_season():
    index = grid("2026-09-15", "2026-10-15")
    a = nc.defaults("1");a["billing_month"] = 10
    r = nc.charge_lines(index, np.ones(len(index)), np.zeros(len(index)), a, math=BillingMath(index))
    assert r["lines"]["energy"] == pytest.approx(720*.105123)


@pytest.mark.parametrize("day", ["2024-12-31", "2026-10-16"])
def test_unverified_composite_dates_reject_instead_of_current_substitution(day):
    index = grid(day, pd.Timestamp(day)+pd.DateOffset(days=1))
    with pytest.raises(ValueError, match="not verified"):
        bill("1", index=index)


def test_historical_rate_components_include_negative_fuel_credit():
    r = bill("1", index=grid("2025-07-01", "2025-08-01"))
    assert r["lines"]["rider_B"] == pytest.approx(-744*.007362)
    assert r["lines"]["rider_C"] == pytest.approx(744*.001520)
    assert r["lines"]["rider_CCR"] == pytest.approx(744*.001690)
    assert r["lines"]["rider_RP"] == pytest.approx(.87)
    assert r["lines"]["rider_RPE"] == pytest.approx(.70)


def test_january_2025_uses_temporary_base_old_riders_and_explicit_a1_decrement():
    r = bill("1", index=grid("2025-01-01", "2025-02-01"))
    expected = 14.4+744*(.105123-.007298+.001854+.006297+.001029+.000288)+.55+.02
    assert sum(r["lines"].values()) == pytest.approx(expected*1.07)
    assert r["lines"]["rider_A1"] == pytest.approx(-744*.007298)
    assert r["lines"]["rider_B1"] == pytest.approx(744*.006297)
    assert r["lines"]["rider_CCR"] == 0


def test_coal_ash_rider_first_applies_march_2025_and_crossing_cycle_is_dated():
    feb = bill("1", index=grid("2025-02-01", "2025-03-01"))
    assert feb["lines"]["rider_CCR"] == 0
    crossing = bill("1", index=grid("2025-02-15", "2025-03-15"))
    assert crossing["metrics"]["import_kwh"] == 671  # Spring DST removes one physical hour.
    assert crossing["lines"]["rider_CCR"] == pytest.approx(671*.001690*14/28)
    assert crossing["is_complete_bill"] is True


def test_first_quarterly_b1_begins_august_2026_and_crossover_is_prorated():
    july = bill("1", index=grid("2026-07-01", "2026-08-01"))
    assert july["lines"]["rider_B1"] == 0
    august = bill("1", index=grid("2026-08-01", "2026-09-01"))
    assert august["lines"]["rider_B1"] == pytest.approx(744*.005602)
    crossing = bill("1", index=grid("2026-07-16", "2026-08-16"))
    assert crossing["lines"]["rider_B1"] == pytest.approx(744*.005602*15/31)
    assert crossing["is_complete_bill"] is True


def test_fixed_rider_change_is_incomplete_until_allocation_is_confirmed():
    index = grid("2025-01-16", "2025-02-16")
    a = nc.defaults("1")
    r = bill("1", index=index, account=a)
    assert r["is_complete_bill"] is False
    assert any("fixed RP/RPE" in x for x in r["warnings"])
    assert r["lines"]["rider_B"] == pytest.approx(744*(16*.001854-15*.007362)/31)
    a.update(fixed_rider_allocation_confirmed=True,
             fixed_rider_allocation_reference="Hypothetical test evidence: utility confirms calendar-day allocation")
    confirmed = bill("1", index=index, account=a)
    assert confirmed["is_complete_bill"] is True
    assert confirmed["lines"] == r["lines"]


@pytest.mark.parametrize("plan", list(nc.BASE))
def test_full_2025_calendar_billing_has_no_rate_gap(plan):
    a = nc.defaults(plan)
    state = None
    power = 4000. if plan == "6L" else 750. if plan == "6P" else 1.
    totals = []
    for first in pd.date_range("2025-01-01", "2025-12-01", freq="MS"):
        r = bill(plan, power, index=grid(first, first+pd.offsets.MonthBegin()), account=a, state=state)
        assert r["is_complete_bill"]
        state = r["next_state"]
        totals.append(sum(r["lines"].values()))
    assert len(totals) == 12 and all(np.isfinite(totals))


def test_schedule5_dynamic_energy_block_width_and_minimum():
    index = grid("2026-08-01", "2026-09-01")
    p = np.full(len(index), 20.)
    r = bill("5", p, index=index)
    expected_energy = 800*.110172+4200*.109334+(14880-5000)*.084338
    assert r["lines"]["energy"] == pytest.approx(expected_energy)
    assert r["lines"]["all_hours_demand"] == 0
    p = np.zeros(96);p[0:2] = 300
    r = bill("5", p, index=grid("2026-08-01", "2026-08-02"))
    pre_riders = sum(v for k, v in r["lines"].items() if not k.startswith("rider_") and k != "nc_sales_tax")
    assert pre_riders == pytest.approx(300*6.782/30)


def test_evolving_usage_history_activates_schedule5_demand():
    index = grid("2026-08-01", "2026-08-02")
    a = nc.defaults("5");a["history_kwh"] = [0.]*11
    p = np.zeros(96);p[:2] = 200
    r = bill("5", p, index=index, account=a, state={"history_kwh": [4000.]+[0.]*10})
    assert r["lines"]["all_hours_demand"] == pytest.approx(100*4.110/30)


def test_large_schedule_separates_on_peak_ratchet_from_all_hours_history():
    a = nc.defaults("6L")
    a["history_peaks_kw"] = [6000.]*11
    a["history_on_peak_kw"] = [3000.]*11
    a["contract_demand_kw"] = 6000.
    r = bill("6L", 1500, account=a)
    assert r["metrics"]["supply_billing_kw"] == 2250
    assert r["metrics"]["distribution_billing_kw"] == 6000
    assert r["next_state"]["history_on_peak_kw"][-1] == 1500


def test_6l_transmission_voltage_has_no_distribution_charge():
    a = nc.defaults("6L");a["voltage_v"] = 69000
    r = bill("6L", 4000, account=a)
    assert r["lines"]["distribution_demand"] == 0


def test_contract_demand_increase_carries_into_following_cycle():
    a = nc.defaults("5P")
    first = bill("5P", 120, account=a)
    second = bill("5P", 40, account=a, state=first["next_state"])
    assert second["metrics"]["distribution_billing_kw"] == 120
    assert a["contract_demand_kw"] == 100


def test_nem_credit_banks_and_one_way_on_to_off_transfer():
    index = grid("2026-08-03", "2026-08-04")
    mask = nc.on_peak(index, "1T")
    imports = np.where(mask, 0., 1.)
    exports = np.where(mask, 3., 0.)
    a = nc.defaults("1T");a.update(solar_program="net_metering", net_metering_confirmed=True, recs_assignment_confirmed=True)
    r = bill("1T", imports, index=index, account=a, exports=exports)
    assert r["metrics"]["on_peak_billed_kwh"] == 0
    assert r["metrics"]["off_peak_billed_kwh"] == 0
    assert r["next_state"]["credit_kwh"] == {"on_peak": 8., "off_peak": 0.}
    # Off-peak surplus cannot erase on-peak imports.
    imports = np.where(mask, 1., 0.)
    exports = np.where(mask, 0., 3.)
    r = bill("1T", imports, index=index, account=a, exports=exports)
    assert r["metrics"]["on_peak_billed_kwh"] == 8
    assert r["next_state"]["credit_kwh"]["off_peak"] == 48


def test_inherited_credits_change_bill_but_default_objective_zeros_only_banks():
    a = nc.defaults("1P");a.update(solar_program="net_metering", net_metering_confirmed=True)
    a["opening_credit_kwh"] = {"on_peak": 100., "off_peak": 100.}
    state = {"credit_kwh": {"on_peak": 10., "off_peak": 20.}, "contract_demand_kw": 100., "history_peaks_kw": [77.]*11}
    copied, objective_state = nc.objective_inputs(a, state, "exclude_opening_credits")
    assert copied["opening_credit_kwh"] == {"on_peak": 0., "off_peak": 0.}
    assert objective_state["credit_kwh"] == {"on_peak": 0., "off_peak": 0.}
    assert objective_state["history_peaks_kw"] == state["history_peaks_kw"]
    assert objective_state["contract_demand_kw"] == 100
    assert a["opening_credit_kwh"]["on_peak"] == 100


def test_summer_credit_reset_is_not_a_cash_trueup():
    a = nc.defaults("1P");a.update(solar_program="net_metering", net_metering_confirmed=True)
    r = bill("1P", index=grid("2025-06-01", "2025-07-01"), account=a,
             state={"credit_kwh": {"on_peak": 1000., "off_peak": 1000.}, "last_billing_month": 5})
    assert r["metrics"]["credit_reset"] is True
    assert r["metrics"]["opening_credit_kwh"] == {"on_peak": 0., "off_peak": 0.}
    assert r["metrics"]["billed_energy_kwh"] == 720


@pytest.mark.parametrize("plan", ["1P", "1T", "5P", "6P", "6L"])
def test_numeric_and_optimizer_share_the_same_filed_charge_expression(plan):
    index = grid("2026-08-03", "2026-08-04")
    power = 4000. if plan == "6L" else 750. if plan == "6P" else 20.
    a = nc.defaults(plan)
    x = cp.Variable(len(index), nonneg=True)
    m = BillingMath(index, convex=True, power_bound=max(5000, power))
    m.register(x, 0, max(5000, power))
    model = nc.charge_lines(index, x, cp.Constant(np.zeros(len(index))), a, math=m)
    problem = cp.Problem(cp.Minimize(sum(model["lines"].values())), m.constraints+[x == power])
    assert problem.is_dcp()
    problem.solve(solver="CLARABEL")
    numeric = nc.charge_lines(index, np.repeat(power, len(index)), np.zeros(len(index)), a, math=BillingMath(index))
    assert problem.value == pytest.approx(sum(numeric["lines"].values()), abs=.001)


def test_declining_tier_schedule5_exact_mip_agrees_with_numeric_bill():
    index = grid("2026-08-03", "2026-08-04", 30)
    a = nc.defaults("5")
    x = cp.Variable(len(index), nonneg=True)
    m = BillingMath(index, convex=True, power_bound=250)
    m.register(x, 0, 250)
    model = nc.charge_lines(index, x, cp.Constant(np.zeros(len(index))), a, math=m)
    problem = cp.Problem(cp.Minimize(sum(model["lines"].values())), m.constraints+[x == 20])
    assert problem.is_dcp() and problem.is_mixed_integer()
    problem.solve(solver="HIGHS")
    numeric = bill("5", 20., index=index)
    assert problem.value == pytest.approx(sum(numeric["lines"].values()), abs=.001)


def test_nonexport_exports_bad_reactive_and_pv_schedule5_are_rejected():
    index = grid("2026-08-03", "2026-08-04")
    with pytest.raises(ValueError, match="curtail"):
        bill("1T", 0, index=index, exports=np.ones(len(index)))
    a = nc.defaults("6P");a["reactive_demand_kvar"] = 10
    with pytest.raises(ValueError, match="reactive"):
        nc.validate_account(a, index)
    with pytest.raises(ValueError, match="Schedule 5"):
        nc.validate_account(nc.defaults("5"), index, equipment={"pv": True, "pv_ac_kw": 10})


def test_evolving_eligibility_is_not_replaced_by_frozen_account_history():
    with pytest.raises(ValueError, match="Evolved demand|5P"):
        bill("5P", 40, state={"history_peaks_kw": [600.]+[40.]*10,
                              "history_on_peak_kw": [600.]+[40.]*10})
    with pytest.raises(ValueError, match="Evolved eleven-cycle|6P"):
        bill("6P", 300, state={"history_peaks_kw": [300.]*11,
                               "history_on_peak_kw": [300.]*11})


def test_missing_and_hourly_intervals_rejected():
    index = grid("2026-08-03", "2026-08-04")
    for broken in (index.delete(4), index[::4], index.tz_localize(None)):
        with pytest.raises(ValueError):
            bill("1T", index=broken)
