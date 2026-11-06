"""I&M Michigan independent filed-factor arithmetic and account boundaries."""
from decimal import Decimal as D

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import im_mi
from src.billing.regional_math import BillingMath


def cycle(month):
    start = pd.Timestamp(month, tz=im_mi.TIMEZONE)
    return pd.date_range(start, start+pd.offsets.MonthBegin(), freq="15min", inclusive="left")


def bill(plan, month, kwh, **changes):
    index = cycle(month)
    account = {**im_mi.hypothetical_defaults(plan, day=month), **changes}
    im_mi.validate_account(account, index)
    imports = np.full(len(index), 4*kwh/len(index))
    return im_mi.charge_lines(index, imports, np.zeros(len(index)), account, math=BillingMath(index))


# Separate transcription from D-116,117,118,122,123. Values are dollars/kWh
# except the two per-account charges. Tax-Rider supply and delivery stay separate.
FIXTURES = [
    ("2025-01-01", ".00374", ".000615", ".000567", ".00387", "13.42", ".87", "-.002392", "-.000570", "-.002421", "-.000474"),
    ("2025-02-01", ".00374", ".000615", ".000567", ".00628", "20.05", ".87", "-.002392", "-.000570", "-.002421", "-.000474"),
    ("2025-03-01", ".00358", ".000615", ".000567", ".00628", "20.05", ".87", "-.002392", "-.000570", "-.002421", "-.000474"),
    ("2025-06-01", ".00358", ".000615", ".000567", ".00628", "20.05", ".87", "0", "0", "0", "0"),
    ("2025-08-01", ".00358", ".000507", ".000467", ".00628", "20.05", ".87", "0", "0", "0", "0"),
    ("2025-09-01", ".00358", ".000507", ".000467", ".00628", "20.05", "1.25", "0", "0", "0", "0"),
    ("2026-01-01", ".00193", ".000507", ".000467", ".00529", "16.96", "1.25", "0", "0", "0", "0"),
    ("2026-03-01", ".00193", ".000507", ".000467", ".00836", "8.09", "1.25", "0", "0", "0", "0"),
    ("2026-07-01", "-.01258", ".000507", ".000467", ".00836", "8.09", "1.25", "0", "0", "0", "0"),
    ("2026-08-01", "-.01258", ".000388", ".000358", ".00836", "8.09", "1.25", "0", "0", "0", "0"),
    ("2026-09-01", "-.01258", ".000388", ".000358", ".00836", "8.09", "1.50", "0", "0", "0", "0"),
]


@pytest.mark.parametrize("fixture", FIXTURES)
@pytest.mark.parametrize("plan", ("RS", "GS"))
def test_independent_decimal_component_benchmark(plan, fixture):
    month, pscr, rs_rra, gs_rra, rs_ewr, gs_ewr, lieaf, rs_tax_supply, rs_tax_delivery, gs_tax_supply, gs_tax_delivery = fixture
    kwh = D("1243.21")
    gs = plan == "GS"
    expected = {
        "delivery_customer": D("8.36" if gs else "7.58"),
        "supply_capacity": kwh*D(".03047" if gs else ".03156"),
        "supply_non_capacity": kwh*D(".07486" if gs else ".08675"),
        "delivery_energy": kwh*D(".03262" if gs else ".04593"),
        "pscr": kwh*D(pscr),
        "rate_realignment": kwh*D(gs_rra if gs else rs_rra),
        "ewr": D(gs_ewr) if gs else kwh*D(rs_ewr),
        "tax_rider_supply": kwh*D(gs_tax_supply if gs else rs_tax_supply),
        "tax_rider_delivery": kwh*D(gs_tax_delivery if gs else rs_tax_delivery),
        "nuclear_decommissioning": D(0), "renewable_energy": D(0),
        "net_lost_revenue_supply": D(0), "net_lost_revenue_delivery": D(0),
    }
    expected["michigan_sales_tax"] = sum(expected.values())*D(".06" if gs else ".04")
    expected["lieaf"] = D(lieaf)
    result = bill(plan, month, float(kwh))
    assert result["lines"] == pytest.approx({k: float(v) for k, v in expected.items()}, abs=1e-9)
    assert result["next_state"] == {} and result["is_complete_bill"]
    assert not result["metrics"]["billing_demand_applied"]
    assert result["metrics"]["lieaf_excluded_from_sales_tax"]


@pytest.mark.parametrize("plan,month,usage", [
    ("RS", "2025-01-01", 0), ("GS", "2025-01-01", 0),
    ("RS", "2025-03-01", 1200), ("GS", "2025-06-01", 4500),
    ("RS", "2026-03-01", 1200), ("GS", "2026-07-01", 1837.21),
    ("RS", "2026-11-01", 1000), ("GS", "2026-11-01", 4500),
])
def test_symbolic_numeric_parity_and_fixed_minimum(plan, month, usage):
    index = cycle(month)
    account = im_mi.hypothetical_defaults(plan, day=month)
    power = cp.Variable(nonneg=True)
    imports = cp.promote(power, (len(index),))
    ops = BillingMath(index, convex=True, power_bound=25.)
    ops.register(imports, 0., 25.)
    ops.constraints.append(power == 4*usage/len(index))
    result = im_mi.charge_lines(index, imports, cp.Constant(np.zeros(len(index))), account, math=ops)
    problem = cp.Problem(cp.Minimize(sum(result["lines"].values())), ops.constraints)
    problem.solve(solver="HIGHS")
    assert problem.status == cp.OPTIMAL
    expected = bill(plan, month, usage)["lines"]
    for name, value in result["lines"].items():
        assert (value.value if hasattr(value, "value") else value) == pytest.approx(expected[name], abs=1e-8)
    if usage == 0:
        assert expected["tax_rider_supply"] == expected["tax_rider_delivery"] == 0
        subtotal = 8.36+13.42 if plan == "GS" else 7.58
        assert sum(expected.values()) == pytest.approx(subtotal*(1.06 if plan == "GS" else 1.04)+.87)


def test_verified_july_pscr_reduction_and_separate_fixed_ewr():
    # Filed actual PSCR changes by 14.51 mills/kWh. The utility's May 26,
    # 2026 announcement independently describes roughly $14.50/1000 kWh.
    june = bill("RS", "2026-06-01", 1000)["lines"]
    july = bill("RS", "2026-07-01", 1000)["lines"]
    assert june["pscr"]-july["pscr"] == pytest.approx(14.51)
    assert sum(june.values())-sum(july.values()) == pytest.approx(14.51*1.04)
    january = bill("GS", "2026-01-01", 0)["lines"]
    march = bill("GS", "2026-03-01", 0)["lines"]
    assert january["ewr"] == 16.96 and march["ewr"] == 8.09


@pytest.mark.parametrize("bad", [
    {"confirmed_tariff_code": "015"}, {"gs_no_demand_meter_confirmed": False},
    {"gs_ewr_under_10kw_confirmed": False}, {"gs_average_monthly_kwh": 4500},
    {"gs_average_monthly_kwh": True}, {"gs_average_monthly_kwh": float("nan")},
    {"gs_review_peak_kw": 10}, {"gs_review_peak_kw": True}, {"gs_review_peak_kw": float("inf")},
    {"gs_meter_review_source": ""}, {"taxable_service_confirmed": False},
    {"ordinary_service_confirmed": False}, {"voltage": "primary"}, {"phase": "three"},
    {"supply": "open_access"}, {"export_mode": "net_metering"}, {"opening_credit_usd": 5.},
    {"provisional_assumptions_accepted": True}, {"cycle_kind": "partial"}, {"bill_date": "2026-12-01"},
])
def test_eligibility_is_independent_of_imports(bad):
    with pytest.raises(ValueError):
        bill("GS", "2026-11-01", 0, **bad)


def test_der_agreement_activation_and_storage_facts():
    account = im_mi.hypothetical_defaults("RS", day="2025-06-01")
    index = cycle("2025-06-01")
    equipment = dict(pv=True, battery=True, renewable_only_charging=True, no_battery_export=True)
    im_mi.validate_account(account, index, equipment)
    for changes in ({"der_ordinary_service_confirmed": False}, {"der_eligibility_source": ""},
                    {"der_activation_date": "2025-06-02"}):
        with pytest.raises(ValueError):
            im_mi.validate_account({**account, **changes}, index, equipment)
    for changes in ({"renewable_only_charging": False}, {"no_battery_export": False}, {"pv": False}):
        with pytest.raises(ValueError):
            im_mi.validate_account(account, index, {**equipment, **changes})


@pytest.mark.parametrize("month", ("2024-12-01", "2025-05-01", "2027-01-01"))
def test_unsupported_dates_fail_closed(month):
    with pytest.raises(ValueError, match="unverified"):
        bill("RS", month, 1000)


def test_dst_missing_duplicate_data_and_non_export():
    for month, expected in (("2025-03-01", 743), ("2025-11-01", 721)):
        assert bill("RS", month, 0)["metrics"]["elapsed_hours"] == expected
    index = cycle("2026-11-01")
    account = im_mi.hypothetical_defaults("GS", day="2026-11-01")
    for malformed in (index.delete(100), index.insert(100, index[100]), index[1:], index[::2], index.tz_convert("UTC")):
        with pytest.raises(ValueError):
            im_mi.validate_account(account, malformed)
    with pytest.raises(ValueError, match="zero export"):
        im_mi.charge_lines(index, np.zeros(len(index)), np.ones(len(index)), account, math=BillingMath(index))
    with pytest.raises(ValueError, match="envelope"):
        bill("GS", "2026-11-01", 4500.001)
    with pytest.raises(ValueError, match="native load"):
        im_mi.validate_native_load(account, np.full(len(index), 9.5))
    with pytest.raises(ValueError, match="native load"):
        im_mi.validate_native_load(account, np.full(len(index), 6.25))
    with pytest.raises(ValueError, match="state"):
        im_mi.validate_state(account, index, {"credit": 1})
