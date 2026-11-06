"""Appalachian Power Virginia filed charge and account boundaries."""
import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import appalachian_va as apco
from src.billing.regional import calculate_cycle
from src.billing.regional_math import BillingMath

JAN25 = "2025-01-01"
NOV25 = "2025-11-01"
JAN26 = "2026-01-01"
OCT26 = "2026-10-01"
NOV26 = "2026-11-01"


def cycle(month):
    start = pd.Timestamp(month, tz=apco.TIMEZONE)
    return pd.date_range(start, start+pd.offsets.MonthBegin(), freq="15min", inclusive="left")


def meter_bill(plan, month, kwh, **changes):
    index = cycle(month)
    account = {**apco.hypothetical_defaults(plan, day=month), **changes}
    imports = np.full(len(index), 4*kwh/len(index))
    return calculate_cycle(apco.UTILITY, index, imports, np.zeros(len(index)), account)


@pytest.mark.parametrize("month,rs,sgs", [
    (JAN25, 173.95, 154.86), (NOV25, 163.88, 144.61), (JAN26, 163.70, 144.43),
    (OCT26, 169.85, 148.41), (NOV26, 169.35, 147.91),
])
def test_1000_kwh_matches_official_rate_summary_or_dated_october_reconstruction(month, rs, sgs):
    for plan, pre_tax, city_tax in (("015", rs, 7.80), ("231", sgs, 8.00)):
        bill = meter_bill(plan, month, 1000)
        lines = bill["unrounded_lines"]
        assert bill["is_complete_bill"] and bill["rate_evidence_status"] == "verified"
        assert lines["triennial_review_refund"] == 0
        assert lines["state_consumption_tax"] == pytest.approx(1.02)
        assert lines["special_regulatory_tax"] == pytest.approx(.165)
        assert lines["local_consumption_tax"] == pytest.approx(.38)
        assert lines["roanoke_consumer_utility_tax"] == pytest.approx(city_tax)
        assert round(bill["unrounded_total_usd"]-1.565-city_tax, 2) == pre_tax
        assert bill["next_state"] == {} and not bill["metrics"]["billing_demand_applied"]


def test_city_tax_minimum_and_state_regulatory_history():
    for plan, fixed in (("015", 7.96), ("231", 9.88)):
        empty = meter_bill(plan, JAN26, 0)
        assert empty["unrounded_total_usd"] == pytest.approx(fixed*1.12)
        small = meter_bill(plan, JAN26, 10)
        assert small["unrounded_lines"]["roanoke_consumer_utility_tax"] == pytest.approx(fixed*.12)
    earlier = meter_bill("231", JAN25, 3000)["unrounded_lines"]
    later = meter_bill("231", NOV25, 3000)["unrounded_lines"]
    assert earlier["roanoke_consumer_utility_tax"] == pytest.approx(8+2000*.0054)
    assert earlier["state_consumption_tax"] == pytest.approx(2500*.00102+500*.00065)
    assert earlier["local_consumption_tax"] == pytest.approx(2500*.00038+500*.00024)
    assert earlier["special_regulatory_tax"] == pytest.approx(2500*.000165+500*.000110)
    assert later["special_regulatory_tax"] == pytest.approx(3000*.000165)
    assert earlier["energy_efficiency_rac"] == pytest.approx(3000*.00237)


@pytest.mark.parametrize("plan,generation,sac", [("015", .03794, .01259), ("231", .03420, .01006)])
def test_securitization_applies_exactly_to_base_generation_and_november_pipp_changes(plan, generation, sac):
    oct_bill = meter_bill(plan, OCT26, 2000)
    nov_bill = meter_bill(plan, NOV26, 2000)
    assert oct_bill["unrounded_lines"]["securitization_base_generation_credit"] == pytest.approx(-.3924*generation*2000)
    assert nov_bill["unrounded_lines"]["securitized_asset_cost"] == pytest.approx(sac*2000)
    assert oct_bill["unrounded_total_usd"]-nov_bill["unrounded_total_usd"] == pytest.approx(1.)
    assert oct_bill["metrics"]["source_grade"] == "dated_filed_sheet_reconstruction"


@pytest.mark.parametrize("month,plan,kwh", [(JAN25,"015",10), (NOV25,"231",2800), (OCT26,"015",1100), (NOV26,"231",5000)])
def test_symbolic_rebill_parity(month, plan, kwh):
    index = cycle(month)
    account = apco.hypothetical_defaults(plan, day=month)
    power = cp.Variable(nonneg=True)
    imports = cp.promote(power, (len(index),))
    ops = BillingMath(index, convex=True, power_bound=25.)
    ops.register(imports, 0., 25.)
    ops.constraints.append(power == 4*kwh/len(index))
    result = apco.charge_lines(index, imports, cp.Constant(np.zeros(len(index))), account, math=ops)
    problem = cp.Problem(cp.Minimize(sum(result["lines"].values())), ops.constraints)
    problem.solve(solver="HIGHS")
    assert problem.status == cp.OPTIMAL
    actual = meter_bill(plan, month, kwh)["unrounded_lines"]
    for key, line in result["lines"].items():
        assert (line.value if hasattr(line, "value") else line) == pytest.approx(actual[key], abs=1e-8)


@pytest.mark.parametrize("changes", [
    {"sgs_review_confirmed": False}, {"sgs_monthly_demands_kw": [15.]*11},
    {"sgs_monthly_demands_kw": [True]+[15.]*11}, {"sgs_monthly_demands_kw": [float("nan")]+[15.]*11},
    {"sgs_monthly_demands_kw": [25.001]*12}, {"sgs_history_through_month": "2025-09-01"},
    {"sgs_history_through_month": "2025-11-01"}, {"sgs_review_source": ""},
    {"locality": "roanoke_county"}, {"locality_confirmed": False},
    {"local_tax_relief_inactive_confirmed": False}, {"bill_date": "2025-12-01"},
    {"export_mode": "net_metering"}, {"phase": "three"}, {"supply": "other"},
    {"provisional_assumptions_accepted": True}, {"cycle_kind": "partial"},
])
def test_unsupported_account_facts_fail_closed(changes):
    with pytest.raises(ValueError):
        meter_bill("231", NOV25, 10, **changes)


def test_sgs_average_boundary_uses_documented_history():
    bill = meter_bill("231", NOV25, 0, sgs_monthly_demands_kw=[30., 20.]+[25.]*10)
    assert bill["metrics"]["sgs_average_metered_demand_kw"] == 25.
    assert bill["import_kwh"] == 0.


@pytest.mark.parametrize("month", ["2025-02-01", "2025-03-01", "2025-10-01", "2025-12-01",
                                  "2026-02-01", "2026-03-01", "2026-09-01", "2026-12-01"])
def test_tariff_gaps_reject(month):
    with pytest.raises(ValueError, match="unverified"):
        meter_bill("015", month, 10)


def test_dst_and_bad_meter_data():
    index = cycle(NOV25)
    assert len(index) == 2884 and meter_bill("015", NOV25, 0)["metrics"]["elapsed_hours"] == 721
    account = apco.hypothetical_defaults(day=NOV25)
    for malformed in (index.delete(10), index.insert(10, index[10]), index[1:], index[::2], index.tz_convert("UTC")):
        with pytest.raises(ValueError):
            apco.validate_account(account, malformed)
    with pytest.raises(ValueError, match="zero export"):
        calculate_cycle(apco.UTILITY, index, np.zeros(len(index)), np.ones(len(index)), account)
    with pytest.raises(ValueError, match="finite"):
        calculate_cycle(apco.UTILITY, index, np.full(len(index), np.nan), np.zeros(len(index)), account)
