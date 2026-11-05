"""Duke Ohio filed rates, independent benchmarks, and strict account scope."""
import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import duke_oh
from src.billing.regional import calculate_cycle
from src.billing.regional_math import BillingMath

JUNE = "2025-06-01"
OCTOBER = "2026-10-01"


def month_index(month):
    start = pd.Timestamp(month, tz=duke_oh.TIMEZONE)
    return pd.date_range(start, start+pd.offsets.MonthBegin(), freq="15min", inclusive="left")


def meter_bill(plan, month, kwh, **changes):
    index = month_index(month)
    account = {**duke_oh.hypothetical_defaults(plan, day=month), **changes}
    return calculate_cycle(duke_oh.UTILITY, index, np.full(len(index), kwh*4/len(index)),
                           np.zeros(len(index)), account)


# Independent Decimal readings of the filed sheets, retained with provenance.
# Compare raw arithmetic rather than assuming Duke's invoice rounding.
@pytest.mark.parametrize("month,plan,kwh,expected", [
    (JUNE, "RS", 0, 11.89016),
    (JUNE, "RS", 750, 145.14596477),
    (JUNE, "DM", 0, 25.22024),
    (JUNE, "DM", 1000, 213.88056476),
    (JUNE, "DM", 2000, 402.54088952),
    (JUNE, "DM", 2800, 553.101149328),
    (JUNE, "DM", 4000, 646.427890464),
    (JUNE, "DM", 6000, 801.972459024),
    (JUNE, "DM", 6500, 819.592601164),
    (OCTOBER, "RS", 0, 10.44192),
    (OCTOBER, "RS", 750, 143.763891615),
    (OCTOBER, "RS", 1500, 252.82736323),
    (OCTOBER, "DM", 0, 20.21288),
    (OCTOBER, "DM", 1000, 211.49593462),
    (OCTOBER, "DM", 2000, 402.77898924),
    (OCTOBER, "DM", 2800, 555.437432936),
    (OCTOBER, "DM", 4000, 649.045231568),
    (OCTOBER, "DM", 6000, 805.058229288),
    (OCTOBER, "DM", 6500, 819.600478718),
])
def test_independent_filed_bill(month, plan, kwh, expected):
    result = meter_bill(plan, month, kwh)
    assert result["unrounded_total_usd"] == pytest.approx(expected, abs=1e-8)
    assert result["is_complete_bill"] and result["rate_evidence_status"] == "verified"
    assert result["next_state"] == {} and not result["metrics"]["billing_demand_applied"]


@pytest.mark.parametrize("month,expected", [(JUNE, 145.15), (OCTOBER, 143.76)])
def test_puco_cincinnati_rs_survey(month, expected):
    result = meter_bill("RS", month, 750)
    assert round(result["unrounded_total_usd"], 2) == expected


@pytest.mark.parametrize("month,plan,kwh,calculator,rounding_delta", [
    (JUNE, "RS", 750, 145.14871477, .00275),
    (JUNE, "DM", 1000, 213.87556476, -.005),
    (JUNE, "DM", 2000, 402.54088952, 0),
    (JUNE, "DM", 2800, 553.105149328, .004),
    (JUNE, "DM", 4000, 646.438290464, .0104),
    (JUNE, "DM", 6000, 801.976859024, .0044),
    (JUNE, "DM", 6500, 819.596501164, .0039),
    (OCTOBER, "RS", 750, 143.758891615, -.005),
    (OCTOBER, "RS", 1500, 252.82586323, -.0015),
    (OCTOBER, "DM", 1000, 211.49593462, 0),
    (OCTOBER, "DM", 2000, 402.77898924, 0),
    (OCTOBER, "DM", 2800, 555.439432936, .002),
    (OCTOBER, "DM", 4000, 649.047231568, .002),
    (OCTOBER, "DM", 6000, 805.060229288, .002),
    (OCTOBER, "DM", 6500, 819.605978718, .0055),
])
def test_duke_workbook_reconciliation(month, plan, kwh, calculator, rounding_delta):
    # Duke rounds selected distribution/RC/RE blocks inside the workbook.
    # The engine retains unrounded arithmetic for those blocks.
    result = meter_bill(plan, month, kwh)
    assert result["unrounded_total_usd"] + rounding_delta == pytest.approx(calculator, abs=1e-8)


@pytest.mark.parametrize("plan,month,kwh", [
    ("RS", JUNE, 15500), ("RS", OCTOBER, 1500),
    ("DM", JUNE, 2700), ("DM", JUNE, 6100), ("DM", OCTOBER, 4200),
])
def test_exact_symbolic_components_agree_with_rebill(plan, month, kwh):
    index = month_index(month)
    account = duke_oh.hypothetical_defaults(plan, day=month)
    consumption = cp.Variable(nonneg=True)
    imports = cp.promote(consumption, (len(index),))
    bill_math = BillingMath(index, convex=True, power_bound=duke_oh.IMPORT_LIMIT_KW[plan])
    bill_math.register(imports, 0., duke_oh.IMPORT_LIMIT_KW[plan])
    bill_math.constraints.append(consumption == 4*kwh/len(index))
    result = duke_oh.charge_lines(index, imports, cp.Constant(np.zeros(len(index))),
                                  account, math=bill_math)
    problem = cp.Problem(cp.Minimize(sum(result["lines"].values())), bill_math.constraints)
    problem.solve(solver="HIGHS")
    assert problem.status == cp.OPTIMAL
    numeric = meter_bill(plan, month, kwh)["unrounded_lines"]
    for key, expression in result["lines"].items():
        assert (expression.value if hasattr(expression, "value") else expression) == pytest.approx(numeric[key], abs=1e-7)


@pytest.mark.parametrize("month", [JUNE, OCTOBER])
def test_filed_oet_is_separate_from_supply_and_tax_cut_credit(month):
    lines = meter_bill("RS", month, 15500)["unrounded_lines"]
    assert lines["state_kwh_tax"] == pytest.approx(2000*.00465+13000*.00419+500*.00363)
    assert lines["distribution_tax_cut_credit"] < 0 and lines["sales_tax"] == 0
    assert ("pipp_recovery" in lines) == (month == OCTOBER)
    assert ("universal_service" in lines) == (month == JUNE)


@pytest.mark.parametrize("change", [
    {"dm_review_confirmed": False}, {"dm_monthly_demands_kw": [10.]*11},
    {"dm_monthly_demands_kw": [True]+[10.]*11}, {"dm_monthly_demands_kw": [float("nan")]+[10.]*11},
    {"dm_monthly_demands_kw": [15.001]*12}, {"dm_monthly_demands_kw": [31., 31.]+[1.]*10},
    {"dm_history_through_month": "2025-06-01"}, {"dm_history_through_month": "2024-05-01"},
    {"dm_review_source": ""}, {"ue_gen_status": "unconfirmed"}, {"export_mode": "net_metering"},
    {"supply": "third_party"}, {"phase": "three"}, {"no_local_tax_confirmed": False},
    {"self_assessor": True}, {"bill_date": "2025-06-29"},
    {"provisional_assumptions_accepted": True}, {"cycle_kind": "partial"},
])
def test_missing_or_unsupported_account_facts_reject(change):
    with pytest.raises(ValueError):
        meter_bill("DM", JUNE, 0, **change)


def test_dm_exact_threshold_and_optional_por_treatment():
    allowed = dict(dm_monthly_demands_kw=[30., 30.]+[12.]*10)
    standard = meter_bill("DM", JUNE, 4000, **allowed)
    exempt = meter_bill("DM", JUNE, 4000, **allowed, ue_gen_status="exempt")
    assert standard["metrics"]["dm_review_average_kw"] == 15
    assert standard["metrics"]["dm_review_months_over_30_kw"] == 0
    assert standard["unrounded_lines"]["generation_uncollectible"] == 1.66
    assert exempt["unrounded_lines"]["generation_uncollectible"] == 0.
    assert standard["unrounded_total_usd"]-exempt["unrounded_total_usd"] == pytest.approx(1.66)


@pytest.mark.parametrize("month,count", [("2025-03-01", 2972), ("2025-11-01", 2884),
    ("2025-05-01", 2976), ("2025-07-01", 2976), ("2026-09-01", 2880), ("2026-11-01", 2884)])
def test_unverified_boundaries_and_dst_reject_without_rate_substitution(month, count):
    assert len(month_index(month)) == count
    with pytest.raises(ValueError, match="unverified"):
        meter_bill("RS", month, 0)


def test_missing_duplicate_and_export_intervals_reject():
    index = month_index(JUNE)
    account = duke_oh.hypothetical_defaults(day=JUNE)
    for malformed in (index.delete(11), index.insert(11, index[11]), index[1:], index[::2], index.tz_convert("UTC")):
        with pytest.raises(ValueError):
            duke_oh.validate_account(account, malformed)
    purchases = np.zeros(len(index))
    with pytest.raises(ValueError, match="zero export"):
        calculate_cycle(duke_oh.UTILITY, index, purchases, np.ones(len(index)), account)
    purchases[11] = np.nan
    with pytest.raises(ValueError, match="finite"):
        calculate_cycle(duke_oh.UTILITY, index, purchases, np.zeros(len(index)), account)
