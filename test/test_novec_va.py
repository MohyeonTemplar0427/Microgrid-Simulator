"""NOVEC independent tariff/tax arithmetic and declared account boundaries."""
from decimal import Decimal as D
from copy import deepcopy

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import novec_va
from src.billing.regional import calculate_cycle
from src.billing.regional_math import BillingMath


def cycle(month):
    start = pd.Timestamp(month, tz=novec_va.TIMEZONE)
    return pd.date_range(start, start+pd.offsets.MonthBegin(), freq="15min", inclusive="left")


def bill(plan, month, kwh, **changes):
    index = cycle(month)
    account = {**novec_va.hypothetical_defaults(plan, day=month), **changes}
    novec_va.validate_account(account, index)
    return novec_va.charge_lines(index, np.full(len(index), 4*kwh/len(index)),
                                np.zeros(len(index)), account, math=BillingMath(index))


def independent(plan, month, kwh):
    """Literal transcriptions, independently separate from production rate data."""
    energy = D(str(kwh))
    commercial = plan == "SC-1"
    pca = D("-.008" if month < "2025-07-01" else ".002")
    volumes = (min(energy, D(2500)), min(max(energy-D(2500), D(0)), D(47500)), max(energy-D(50000), D(0)))
    result = {
        "delivery_customer": D("26.78" if commercial else "21.30"),
        "delivery_energy": energy*D(".02064" if commercial else ".01348"),
        "supply_energy": energy*D(".09242" if commercial else ".09731"),
        "power_cost_adjustment": energy*pca,
        "state_consumption_tax": sum(v*D(p) for v, p in zip(volumes, (".00102", ".00065", ".00050"))),
        "special_regulatory_tax": sum(v*D(p) for v, p in zip(volumes, (".000165", ".000110", ".000077") if month < "2025-08-01" else (".000165",)*3)),
        "local_consumption_tax": sum(v*D(p) for v, p in zip(volumes, (".00038", ".00024", ".00018"))),
        "prince_william_consumer_utility_tax": min(D("2.29" if commercial else "1.40")+energy*D(".013487" if commercial else ".01509"), D("100" if commercial else "3")),
    }
    return result


@pytest.mark.parametrize("plan", ("R-1", "SC-1"))
@pytest.mark.parametrize("month", ("2025-01-01", "2025-07-01", "2025-08-01"))
@pytest.mark.parametrize("energy", (0., 100., 106.03, 300., 1000., 2500., 2500.01, 5999.))
def test_independent_decimal_components(plan, month, energy):
    result = bill(plan, month, energy)
    expected = independent(plan, month, energy)
    assert result["lines"] == pytest.approx({key: float(value) for key, value in expected.items()}, abs=1e-9)
    assert result["is_complete_bill"] and not result["excluded_components"] and result["next_state"] == {}


@pytest.mark.parametrize("plan", ("R-1", "SC-1"))
@pytest.mark.parametrize("month", [f"2025-{m:02}-01" for m in range(1, 13)])
def test_complete_year_calendar_source_stacks(plan, month):
    result = bill(plan, month, 1837.21)
    assert result["lines"] == pytest.approx({k: float(v) for k, v in independent(plan, month, 1837.21).items()})
    assert result["metrics"]["billing_month"] == month
    assert result["rate_evidence_status"] == "verified"


@pytest.mark.parametrize("plan,month,energy", [
    ("R-1", "2025-03-01", 0.), ("SC-1", "2025-03-01", 0.),
    ("R-1", "2025-07-01", 100.), ("R-1", "2025-07-01", 106.03),
    ("R-1", "2025-08-01", 106.04), ("SC-1", "2025-07-01", 3500.),
    ("SC-1", "2025-08-01", 3500.), ("SC-1", "2025-11-01", 5999.),
])
def test_numeric_symbolic_parity_and_fixed_minimum(plan, month, energy):
    index, account = cycle(month), novec_va.hypothetical_defaults(plan, day=month)
    power = cp.Variable(nonneg=True)
    imports = cp.promote(power, (len(index),))
    ops = BillingMath(index, convex=True, power_bound=30.)
    ops.register(imports, 0., 30.)
    ops.constraints.append(power == 4*energy/len(index))
    result = novec_va.charge_lines(index, imports, cp.Constant(np.zeros(len(index))), account, math=ops)
    problem = cp.Problem(cp.Minimize(sum(result["lines"].values())), ops.constraints)
    problem.solve(solver="HIGHS")
    assert problem.status == cp.OPTIMAL
    for key, expected in independent(plan, month, energy).items():
        value = result["lines"][key]
        assert (value.value if hasattr(value, "value") else value) == pytest.approx(float(expected), abs=1e-8)
    if energy == 0:
        assert problem.value == pytest.approx(29.07 if plan == "SC-1" else 22.70)


def test_pca_and_actual_regulatory_levy_boundaries():
    june, july = [bill("R-1", f"2025-{month:02}-01", 1000)["lines"] for month in (6, 7)]
    assert july["power_cost_adjustment"]-june["power_cost_adjustment"] == pytest.approx(10.)
    july, august = [bill("SC-1", f"2025-{month:02}-01", 3500)["lines"] for month in (7, 8)]
    assert august["special_regulatory_tax"]-july["special_regulatory_tax"] == pytest.approx(.055)
    assert july["state_consumption_tax"] == august["state_consumption_tax"]
    assert july["local_consumption_tax"] == august["local_consumption_tax"]
    # The SCC levy, not the larger statutory ceiling, is collected.
    assert august["special_regulatory_tax"] == pytest.approx(.5775)


@pytest.mark.parametrize("changes", [
    {"sc_retained_assignment_confirmed": False}, {"sc_monthly_demands_kw": [8.]*11},
    {"sc_monthly_demands_kw": [8.]*11+[30.]}, {"sc_monthly_demands_kw": [8.]*11+[float("nan")]},
    {"sc_monthly_demands_kw": [8.]*11+[True]}, {"sc_history_through_month": "2025-10-01"},
    {"sc_review_source": ""}, {"taxable_service_confirmed": False}, {"locality_confirmed": False},
    {"motor_limit_confirmed": False}, {"locality": "manassas_park"}, {"voltage": "primary"},
    {"phase": "three"}, {"supply": "retail_choice"}, {"export_mode": "net_metering"},
    {"opening_credit_usd": 1.}, {"provisional_assumptions_accepted": True},
    {"ordinary_service_confirmed": False}, {"account_source": ""}, {"cycle_source": ""},
    {"cycle_kind": "partial"}, {"bill_date": "2025-12-30"},
])
def test_independent_account_and_locality_rejections(changes):
    with pytest.raises(ValueError):
        bill("SC-1", "2025-12-01", 0, **changes)


def test_initial_sc_scope_is_stricter_than_tariff_reclassification():
    account = novec_va.hypothetical_defaults("SC-1", day="2025-12-01")
    index = cycle("2025-12-01")
    novec_va.validate_account(account, index)
    with pytest.raises(ValueError, match="envelope"):
        novec_va.validate_native_load(account, np.full(len(index), 30.))
    with pytest.raises(ValueError, match="envelope"):
        novec_va.validate_native_load(account, np.full(len(index), 6000/(len(index)*.25)))
    with pytest.raises(ValueError, match="envelope"):
        bill("SC-1", "2025-12-01", 6000.)
    assert bill("SC-1", "2025-12-01", 0)["metrics"]["sc_actual_review_max_kw"] == 8.


@pytest.mark.parametrize("month", ("2024-12-01", "2026-01-01", "2026-06-01", "2026-10-01", "2026-11-01", "2026-12-01", "2027-01-01"))
def test_missing_component_years_fail_closed(month):
    with pytest.raises(ValueError, match="unverified"):
        bill("R-1", month, 1000)


def test_dst_malformed_intervals_state_and_export():
    for month, expected in (("2025-03-01", 743.), ("2025-11-01", 721.)):
        assert bill("R-1", month, 0)["metrics"]["elapsed_hours"] == expected
    index, account = cycle("2025-11-01"), novec_va.hypothetical_defaults("R-1", day="2025-11-01")
    for malformed in (index.delete(100), index.insert(100, index[100]), index[1:], index[::2], index.tz_convert("UTC")):
        with pytest.raises(ValueError):
            novec_va.validate_account(account, malformed)
    with pytest.raises(ValueError, match="zero export"):
        novec_va.charge_lines(index, np.zeros(len(index)), np.ones(len(index)), account, math=BillingMath(index))
    with pytest.raises(ValueError, match="state"):
        novec_va.validate_state(account, index, {"credit": 1.})


def test_final_der_agreement_and_pv_only_storage_required():
    account = novec_va.hypothetical_defaults("R-1", day="2025-11-01")
    index = cycle("2025-11-01")
    equipment = dict(pv=True, battery=True, renewable_only_charging=True, no_battery_export=True)
    novec_va.validate_account(account, index, equipment)
    for change in ({"der_ordinary_service_confirmed": False}, {"der_eligibility_source": ""}, {"der_activation_date": "2025-11-02"}):
        with pytest.raises(ValueError):
            novec_va.validate_account({**account, **change}, index, equipment)
    for change in ({"renewable_only_charging": False}, {"no_battery_export": False}, {"pv": False}):
        with pytest.raises(ValueError):
            novec_va.validate_account(account, index, {**equipment, **change})


def test_shared_numeric_adapter_retains_components_and_default_confirmations():
    index, account = cycle("2025-11-01"), novec_va.hypothetical_defaults("R-1", day="2025-11-01")
    result = calculate_cycle(novec_va.UTILITY, index, np.ones(len(index)), np.zeros(len(index)), account)
    assert result["is_complete_bill"] and result["export_kwh"] == 0
    assert result["unrounded_lines"] == pytest.approx({k: float(v) for k, v in independent("R-1", "2025-11-01", 721.).items()})
    defaults = novec_va.defaults("SC-1")
    assert all(defaults[k] is False for k in novec_va.CONFIRMATIONS)
    assert defaults["sc_retained_assignment_confirmed"] is False
    assert {p["id"] for p in novec_va.catalog()} == {"R-1", "SC-1"}
