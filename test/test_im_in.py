"""I&M Indiana filed schedules, benchmarks and account boundaries."""
from decimal import Decimal, ROUND_HALF_UP

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import im_in
from src.billing.regional import calculate_cycle
from src.billing.regional_math import BillingMath

D = Decimal
JUL25, MAR26, JUL26, NOV26 = "2025-07-01", "2026-03-01", "2026-07-01", "2026-11-01"


def cycle(month):
    start = pd.Timestamp(month, tz=im_in.TIMEZONE)
    return pd.date_range(start, start+pd.offsets.MonthBegin(), freq="15min", inclusive="left")


def bill(plan, month, kwh, **changes):
    index = cycle(month)
    account = {**im_in.hypothetical_defaults(plan, day=month), **changes}
    imports = np.full(len(index), 4*kwh/len(index))
    return calculate_cycle(im_in.UTILITY, index, imports, np.zeros(len(index)), account)


@pytest.mark.parametrize("month,expected", [
    (JUL25, (91.11, 166.56, 239.36, 312.16)),
    (JUL26, (89.02, 162.37, 233.09, 303.80)),
])
@pytest.mark.parametrize("plan", ["015", "016"])
def test_official_iurc_residential_bill_survey(plan, month, expected):
    for kwh, total in zip((500, 1000, 1500, 2000), expected):
        result = bill(plan, month, kwh)
        lines = result["unrounded_lines"]
        subtotal = result["unrounded_total_usd"]-lines["indiana_sales_tax"]
        assert round(subtotal, 2) == total
        assert lines["indiana_sales_tax"] == pytest.approx(subtotal*.07)
        assert result["is_complete_bill"] and result["rate_evidence_status"] == "verified"
        assert not result["metrics"]["billing_demand_applied"]
    lines = bill(plan, month, 1000)["unrounded_lines"]
    surveyed_riders = (.45, 1.94, 1.72, 28.91, .40, .15) if month == JUL25 else (1.93, 1.38, 1.54, 22.75, .73, .15)
    keys = ("fuel", "dsm_ee", "environmental", "oss_pjm", "resource_adequacy", "solar_power")
    assert tuple(round(abs(lines[key]), 2) for key in keys) == surveyed_riders
    assert round(lines["tax_rider"], 2) == 3.28
    assert round(lines["phase_in_credit"], 2) == -2.29


# Independently transcribed USD/kWh from Sheets 44–53 and the
# superseded IURC sheets/orders. Always the low-energy non-opt-out GS row.
GS_RIDERS = {
    "2025-06-01": ("-.000450", ".001576", ".001413", ".023571", ".000325", ".000115"),
    JUL25: ("-.000450", ".001576", ".001413", ".023011", ".000325", ".000115"),
    "2025-08-01": ("-.000450", ".001576", ".001413", ".023011", ".002303", ".000115"),
    "2025-11-01": ("-.000168", ".001576", ".001413", ".023011", ".002303", ".000127"),
    MAR26: ("-.000168", ".003873", ".001321", ".023011", ".002303", ".000127"),
    "2026-04-01": ("-.000168", ".003873", ".001321", ".023011", ".000590", ".000127"),
    JUL26: (".002422", ".003873", ".001321", ".017635", ".000590", ".000127"),
    NOV26: (".000096", ".003873", ".001321", ".017635", ".000590", ".000117"),
}


@pytest.mark.parametrize("month,factors", GS_RIDERS.items())
@pytest.mark.parametrize("plan", ["215", "218"])
def test_independent_secondary_gs_bill(plan, month, factors):
    usage = D("1837.21")
    expected = {"bundled_customer": D("29.00"), "bundled_base_energy": usage*D(".11050")}
    names = ("fuel", "dsm_ee", "environmental", "oss_pjm", "resource_adequacy", "solar_power",
             "phase_in_credit", "tax_rider")
    expected.update({key: usage*D(rate) for key, rate in zip(names, (*factors, "-.001511", ".002648"))})
    expected["indiana_sales_tax"] = sum(expected.values())*D(".07")
    result = bill(plan, month, float(usage))
    assert result["unrounded_lines"] == pytest.approx({k: float(v) for k, v in expected.items()})
    assert result["total_usd"] == float(sum(v.quantize(D(".01"), rounding=ROUND_HALF_UP) for v in expected.values()))
    assert result["next_state"] == {} and not result["metrics"]["billing_demand_applied"]


@pytest.mark.parametrize("plan,usage", [("015", 0), ("015", 899.5), ("016", 900.5), ("218", 4500)])
def test_exact_symbolic_parity(plan, usage):
    index = cycle(NOV26)
    account = im_in.hypothetical_defaults(plan, day=NOV26)
    power = cp.Variable(nonneg=True)
    imports = cp.promote(power, (len(index),))
    ops = BillingMath(index, convex=True, power_bound=25.)
    ops.register(imports, 0., 25.)
    ops.constraints.append(power == 4*usage/len(index))
    result = im_in.charge_lines(index, imports, cp.Constant(np.zeros(len(index))), account, math=ops)
    problem = cp.Problem(cp.Minimize(sum(result["lines"].values())), ops.constraints)
    problem.solve(solver="HIGHS")
    assert problem.status == cp.OPTIMAL
    actual = bill(plan, NOV26, usage)["unrounded_lines"]
    assert actual["bundled_base_energy"] == pytest.approx(
        min(usage, 900)*.11856+max(0, usage-900)*.11195 if plan.startswith("0") else usage*.11050)
    for name, line in result["lines"].items():
        assert (line.value if hasattr(line, "value") else line) == pytest.approx(actual[name], abs=1e-8)


@pytest.mark.parametrize("changes", [
    {"confirmed_tariff_code": "218"}, {"gs_no_demand_meter_confirmed": False},
    {"gs_average_monthly_kwh": 4500}, {"gs_average_monthly_kwh": True},
    {"gs_average_monthly_kwh": float("nan")}, {"gs_average_monthly_kwh": None},
    {"gs_meter_review_source": ""}, {"gs_dsm_non_opt_out_confirmed": False},
    {"phase": "three"}, {"supply": "third_party"}, {"taxable_service_confirmed": False},
    {"export_mode": "net_metering"}, {"cycle_kind": "partial"}, {"bill_date": "2026-12-01"},
])
def test_independent_account_eligibility(changes):
    with pytest.raises(ValueError):
        bill("215", NOV26, 10, **changes)


@pytest.mark.parametrize("month", [
    "2024-12-01", "2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01",
    "2025-05-01", "2025-10-01", "2026-05-01", "2026-06-01", "2026-12-01", "2027-01-01",
])
def test_unsupported_date_windows_fail_closed(month):
    with pytest.raises(ValueError, match="unverified"):
        bill("015", month, 10)


def test_dst_gap_and_non_export():
    assert bill("015", MAR26, 0)["metrics"]["elapsed_hours"] == 743
    assert bill("015", NOV26, 0)["metrics"]["elapsed_hours"] == 721
    assert bill("015", NOV26, 0)["total_usd"] == 16.05
    assert bill("218", NOV26, 0)["total_usd"] == 31.03
    index = cycle(NOV26)
    account = im_in.hypothetical_defaults("215", day=NOV26)
    for malformed in (index.delete(30), index.insert(30, index[30]), index[1:], index[::2], index.tz_convert("UTC")):
        with pytest.raises(ValueError):
            im_in.validate_account(account, malformed)
    empty = np.zeros(len(index))
    with pytest.raises(ValueError, match="zero export"):
        calculate_cycle(im_in.UTILITY, index, empty, np.ones(len(index)), account)
    with pytest.raises(ValueError, match="finite"):
        calculate_cycle(im_in.UTILITY, index, empty, np.full(len(index), np.nan), account)
    with pytest.raises(ValueError, match="envelope"):
        bill("215", NOV26, 4500.001)
    with pytest.raises(ValueError, match="state"):
        calculate_cycle(im_in.UTILITY, index, empty, empty, account, state={"credit": 1})
