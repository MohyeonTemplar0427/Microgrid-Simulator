"""Independent AES Ohio literal Decimal benchmarks; no production rate imports.

Filed distribution facts: docs/utility_sources/aes_ohio/delivery/rates.json.
Supply facts: docs/utility_sources/aes_ohio/supply/rates.json. June2025 G10
has dated official calculators and cached adopted text, with original-PDF gap;
this test does not upgrade that source grade. D33: rules/rules.json and ORC
5727.81(A), no CAT gross-up. Official cached calculator examples below are
exercised on complete30-calendar-day fixtures and ordinary demand, away
from LLF selector ambiguity; published workbook date conventions stay distinct. All expected values are literals or Decimal arithmetic;
production imports only exercise public APIs and symbolic billing expressions.
"""
from decimal import Decimal as D, ROUND_HALF_UP

import numpy as np
import pandas as pd
import pytest


MONTHS = [
    ("2025-01", 744), ("2025-02", 672), ("2025-03", 743),
    ("2025-04", 720), ("2025-05", 744), ("2025-06", 720),
    ("2026-06", 720), ("2026-07", 744), ("2026-09", 720),
    ("2026-10", 744), ("2026-11", 721),
]

# Original percentage units remain percent; divide by100 only in arithmetic.
# Zero ordinary D19 energy means no energy charge in its RATE PER MONTH.
R2025_Q1 = dict(rs_customer="9.75", rs_energy="0.0286082", gs_customer="16.68",
    gs_demand="4.7725904", gs_llf="0.0521380", combined_llf="0.0878585",
    transmission_rs="0.0101098", transmission_kw="2.8762278",
    transmission_energy="0.0005432", transmission_llf="0.0357205",
    supply="0.0857985", iir="10.1090", dir="14.8385", storm=["0.21", "0.80"],
    pro=["0.32", "1.10"], pipp="0.0020072", tax_savings="-0.4889",
    solar_fixed="0.10", solar_energy="0.000290516", legacy_fixed="1.50",
    legacy_energy="0.0017124", economic=["0.0000000", "0.0000000"], programs="0.0000000")
R2025_Q2 = {**R2025_Q1, "iir":"9.2080", "dir":"17.0211", "pro":["2.07", "6.97"]}
R2025_JUNE = {**R2025_Q2, "combined_llf":"0.0980791", "transmission_rs":"0.0150056",
    "transmission_kw":"3.9517849", "transmission_energy":"0.0008294",
    "transmission_llf":"0.0459411", "supply":"0.0945004", "storm":["2.27", "8.38"]}
R2026_JUNE = dict(rs_customer="9.75", rs_energy="0.0493180", gs_customer="19.00",
    gs_demand="7.8040932", gs_llf="0.2138108", combined_llf="0.3339010",
    transmission_rs="0.0179223", transmission_kw="4.3554372",
    transmission_energy="0.0007632", transmission_llf="0.1200902",
    supply="0.1085598", iir="9.0190", dir="2.9731", storm=["0.80", "3.21"],
    pro=["0.65", "2.84"], pipp="0.0032369", tax_savings="2.5675",
    solar_fixed="0.00", solar_energy="0.000000000", legacy_fixed="0.00",
    legacy_energy="0.0000000", economic=["0.0000000", "0.0000000"], programs="0.0022468")
R2026_Q3 = {**R2026_JUNE, "iir":"6.7650", "dir":"5.3313"}
R2026_OCTOBER = {**R2026_Q3, "iir":"6.8880", "dir":"7.4660", "pipp":"0.0042663"}
R2026_NOVEMBER = {**R2026_OCTOBER, "tax_savings":"-0.2577", "economic":["0.0000725", "0.0000358"]}
VECTORS = {
    "2025-01":R2025_Q1, "2025-02":R2025_Q1, "2025-03":R2025_Q1,
    "2025-04":R2025_Q2, "2025-05":R2025_Q2, "2025-06":R2025_JUNE,
    "2026-06":R2026_JUNE, "2026-07":R2026_Q3, "2026-09":R2026_Q3,
    "2026-10":R2026_OCTOBER, "2026-11":R2026_NOVEMBER,
}


class UnresolvedLowLoadEquality(ValueError):
    """Unrounded comparator cannot resolve official interim-cent allocation."""


def literal_tax(energy, calendar_days):
    e = D(str(energy))
    first, second = ((D(2000), D(15000)) if calendar_days == 30 else
                     (D(67)*calendar_days, D(500)*calendar_days))
    return (min(e, first)*D("0.00465") +
            min(max(e-first, D(0)), second-first)*D("0.00419") +
            max(e-second, D(0))*D("0.00363"))


def literal_bill(plan, month, power, history=(), *, calendar_days=None):
    """Independent aligned15min inputs -> actual30min/history -> complete bill."""
    r = VECTORS[month]
    values = [D(str(x)) for x in power]
    assert values and len(values) % 2 == 0
    assert min(values) >= 0
    e = sum(values, D(0))/D(4)
    peak = max((values[i]+values[i+1])/D(2) for i in range(0, len(values), 2))
    rs = plan == "D17"
    prior = [D(str(row["maximum_kw"])) for row in history
             if pd.Timestamp(row["month"]).month in (1, 2, 6, 7, 8, 12)]
    ratchet = D(0) if rs else D("0.75")*max(prior, default=D(0))
    demand = D(0) if rs else max(peak, ratchet)
    price = lambda key: D(r[key])
    customer = price("rs_customer" if rs else "gs_customer")
    distribution_energy = e*price("rs_energy") if rs else D(0)
    distribution_demand = D(0) if rs else demand*price("gs_demand")
    transmission_energy = e*price("transmission_rs" if rs else "transmission_energy")
    transmission_demand = D(0) if rs else demand*price("transmission_kw")
    low_load = False
    comparator = None
    if not rs:
        ordinary = distribution_demand+transmission_energy+transmission_demand
        capped = e*price("combined_llf")
        comparator = ordinary-capped
        if abs(comparator) <= D("0.02") and abs(distribution_demand-e*price("gs_llf")) > D("0.0000001"):
            raise UnresolvedLowLoadEquality("Differing D19 allocations inside$0.02 comparator band")
        low_load = capped < ordinary  # Ordinary at equality; zero branches allowed.
        if low_load:
            distribution_energy, distribution_demand = e*price("gs_llf"), D(0)
            transmission_energy, transmission_demand = e*price("transmission_llf"), D(0)
    base = customer+distribution_energy+distribution_demand
    cls = 0 if rs else 1
    days = calendar_days or pd.Timestamp(month+"-01").days_in_month
    lines = dict(
        distribution_customer=customer, distribution_energy=distribution_energy,
        distribution_demand=distribution_demand, transmission_energy=transmission_energy,
        transmission_demand=transmission_demand, supply_energy=e*price("supply"),
        infrastructure_investment=base*price("iir")/100,
        distribution_investment=base*price("dir")/100,
        storm_recovery=D(r["storm"][cls]),
        regulatory_compliance=base*D("2.82")/100 if rs else D("3.66"),
        proactive_reliability=D(r["pro"][cls]),
        pipp=min(e, D(833000))*price("pipp")+max(e-D(833000), D(0))*D("0.0005700"),
        solar_generation=price("solar_fixed") if rs else min(e, D(833000))*price("solar_energy"),
        legacy_generation=price("legacy_fixed") if rs else min(e, D(833000))*price("legacy_energy"),
        economic_development=e*D(r["economic"][cls]),
        customer_programs=e*price("programs") if rs else D(0),
        energy_efficiency=D(0), customer_refund=D(0), tax_savings=base*price("tax_savings")/100,
        excise_tax=literal_tax(e, days), sales_tax=D(0), minimum_adjustment=max(customer-base, D(0)))
    return lines, dict(energy_kwh=e, actual_peak_kw=peak, billing_demand_kw=demand,
        ratchet_floor_kw=ratchet, low_load=low_load, comparator_usd=comparator,
        base_distribution_usd=base)


def fixture(plan, month, *, historical_kw=40):
    from src.billing import aes_ohio as aes
    first = pd.Timestamp(month+"-01", tz="America/New_York")
    stop = first+pd.offsets.MonthBegin()
    index = pd.date_range(first, stop, freq="15min", inclusive="left")
    account = aes.hypothetical_defaults(plan, day=month+"-01")
    if plan == "D19":
        account["history"] = [dict(month=str(x.date()), maximum_kw=float(historical_kw))
            for x in pd.date_range(end=first.tz_localize(None)-pd.offsets.MonthBegin(), periods=11, freq="MS")]
    return account, index


def assert_literal_bill(account, index, imports, *, state=None):
    from src.billing.regional import calculate_cycle
    month = account["billing_month"][:7]
    history = account["history"] if state is None else state["history"]
    expected, determinants = literal_bill(account["tariff"], month, imports, history)
    actual = calculate_cycle("aes_ohio", index, imports, np.zeros(len(index)), account, state=state)
    assert set(actual["unrounded_lines"]) == set(expected)
    for key, value in expected.items():
        assert actual["unrounded_lines"][key] == pytest.approx(float(value), abs=2e-7), key
    cents = {k: float(v.quantize(D(".01"), rounding=ROUND_HALF_UP)) for k, v in expected.items()}
    assert actual["lines"] == pytest.approx(cents, abs=1e-8)
    assert actual["total_usd"] == pytest.approx(float(sum(D(str(v)) for v in cents.values())), abs=1e-8)
    m = actual["metrics"]
    assert m["actual_30_minute_peak_kw"] == pytest.approx(float(determinants["actual_peak_kw"]), abs=1e-8)
    assert m["billing_demand_kw"] == pytest.approx(float(determinants["billing_demand_kw"]), abs=1e-8)
    assert m["ratchet_floor_kw"] == pytest.approx(float(determinants["ratchet_floor_kw"]), abs=1e-8)
    assert bool(m["low_load_factor_applied"]) is determinants["low_load"]
    assert m["base_distribution_usd"] == pytest.approx(float(determinants["base_distribution_usd"]), abs=1e-8)
    assert m["state_tax_cat_gross_up_applied"] is False
    assert actual["is_complete_bill"] is True
    assert actual["export_kwh"] == 0
    return actual, determinants


@pytest.mark.parametrize("plan", ["D17", "D19"])
@pytest.mark.parametrize("month,hours", MONTHS)
@pytest.mark.parametrize("energy", [1000.137, 2077.137, 16000.137])
def test_literal_all_source_regimes_itemized_tax_and_llf(plan, month, hours, energy):
    account, index = fixture(plan, month)
    assert len(index) == hours*4
    imports = np.full(len(index), energy/hours)
    assert_literal_bill(account, index, imports)


@pytest.mark.parametrize("plan", ["D17", "D19"])
@pytest.mark.parametrize("month,days", [("2025-02", 28), ("2025-06", 30), ("2026-10", 31)])
@pytest.mark.parametrize("band,delta", [(1, -1), (1, 0), (1, 1), (2, -1), (2, 0), (2, 1)])
def test_statutory_daily_tax_breaks_without_affiliate_cat(plan, month, days, band, delta):
    from src.billing.regional import calculate_cycle
    account, index = fixture(plan, month)
    first, second = (2000, 15000) if days == 30 else (67*days, 500*days)
    energy = (first if band == 1 else second)+delta
    imports = np.full(len(index), energy/(len(index)/4))
    actual_energy = sum((D(str(v)) for v in imports), D(0))/4
    bill = calculate_cycle("aes_ohio", index, imports, np.zeros(len(index)), account)
    assert bill["unrounded_lines"]["excise_tax"] == pytest.approx(float(literal_tax(actual_energy, days)), abs=1e-8)
    assert bill["metrics"]["excise_tax_thresholds_kwh"] == [first, second]
    assert bill["unrounded_lines"]["sales_tax"] == 0


@pytest.mark.parametrize("plan,historical_kw", [("D17", 0), ("D19", 0), ("D19", 40)])
@pytest.mark.parametrize("month", ["2025-06", "2026-11"])
def test_zero_usage_retains_customer_and_riders_without_invented_kw_floor(plan, historical_kw, month):
    account, index = fixture(plan, month, historical_kw=historical_kw)
    bill, determinant = assert_literal_bill(account, index, np.zeros(len(index)))
    assert bill["unrounded_lines"]["distribution_energy"] == 0
    assert bill["unrounded_lines"]["distribution_demand"] == 0
    assert bill["unrounded_lines"]["transmission_demand"] == 0
    assert bill["unrounded_lines"]["minimum_adjustment"] == 0
    if plan == "D19":
        assert determinant["billing_demand_kw"] == D(str(historical_kw))*D(".75")
        assert bill["next_state"]["history"][-1]["maximum_kw"] == 0


def test_actual_aligned_30minute_average_not_15minute_spike():
    account, index = fixture("D19", "2025-06", historical_kw=0)
    power = np.tile([0., 20.], len(index)//2)
    bill, determinant = assert_literal_bill(account, index, power)
    assert determinant["actual_peak_kw"] == 10
    assert determinant["billing_demand_kw"] == 10
    assert bill["next_state"]["history"][-1]["maximum_kw"] == 10
    assert bill["next_state"]["next_billing_month"] == "2025-07-01"


def test_seasonal_prior_actual_peak_ignores_larger_nonseasonal_maximum():
    account, index = fixture("D19", "2025-06", historical_kw=10)
    for row in account["history"]:
        if row["month"] == "2025-02-01": row["maximum_kw"] = 80.
        if row["month"] == "2025-05-01": row["maximum_kw"] = 100.
    bill, determinant = assert_literal_bill(account, index, np.full(len(index), 12.))
    assert determinant["ratchet_floor_kw"] == 60
    assert determinant["billing_demand_kw"] == 60
    assert bill["next_state"]["history"][-1] == dict(month="2025-06-01", maximum_kw=12.)
    assert len(bill["next_state"]["history"]) == 11


def test_carried_actual_peak_does_not_recur_as_ratchet_inflated_history():
    account, june_index = fixture("D19", "2025-06", historical_kw=80)
    june, _ = assert_literal_bill(account, june_index, np.full(len(june_index), 2.))
    assert june["metrics"]["billing_demand_kw"] == 60
    assert june["next_state"]["history"][-1]["maximum_kw"] == 2
    july_account, july_index = fixture("D19", "2026-07", historical_kw=0)
    # Use adjacent June->July2025 calendar, but July2025 rates are unsupported.
    # State arithmetic can be asserted directly without executing that gap.
    assert june["next_state"]["next_billing_month"] == "2025-07-01"
    assert june["next_state"]["history"] == account["history"][1:]+[dict(month="2025-06-01", maximum_kw=2.)]
    # Execute adjacent June->July2026 with supported rates and independent state.
    account, june_index = fixture("D19", "2026-06", historical_kw=80)
    june, _ = assert_literal_bill(account, june_index, np.full(len(june_index), 2.))
    july, _ = assert_literal_bill(july_account, july_index, np.full(len(july_index), 2.), state=june["next_state"])
    assert july["metrics"]["demand_history_used"][-1]["maximum_kw"] == 2
    assert july["next_state"]["history"][-1]["maximum_kw"] == 2


@pytest.mark.parametrize("month", ["2025-01", "2025-06", "2026-10"])
def test_clear_lowload_boundary_rejection_preserves_material_allocation_limit(month):
    from src.billing.regional import calculate_cycle
    account, index = fixture("D19", month)
    r = VECTORS[month]
    # At ratchet30kW solve the raw equality independently. Constant current
    # load is below that ratchet; differing distribution branches are material.
    energy = D(30)*(D(r["gs_demand"])+D(r["transmission_kw"]))/(D(r["combined_llf"])-D(r["transmission_energy"]))
    power = np.full(len(index), float(energy/D(len(index)/4)))
    with pytest.raises(UnresolvedLowLoadEquality):
        literal_bill("D19", month, power, account["history"])
    with pytest.raises(ValueError, match=r"0\.02|boundary|comparator"):
        calculate_cycle("aes_ohio", index, power, np.zeros(len(index)), account)


@pytest.mark.parametrize("gap_usd", ["-0.025", "0.025"])
def test_both_sides_outside_boundary_band_choose_matching_d19_and_t08(gap_usd):
    month = "2025-06"
    account, index = fixture("D19", month)
    r = VECTORS[month]
    energy = (D(30)*(D(r["gs_demand"])+D(r["transmission_kw"]))-D(gap_usd))/(D(r["combined_llf"])-D(r["transmission_energy"]))
    bill, determinant = assert_literal_bill(account, index, np.full(len(index), float(energy/D(len(index)/4))))
    assert determinant["low_load"] is (D(gap_usd) > 0)
    assert bool(bill["metrics"]["low_load_factor_applied"]) is (D(gap_usd) > 0)


# Literal cached facts from dated official workbook examples, not recomputed
# from production tables. All fixtures have30 local calendar measurement days.
# The published June/November visible From/To dates are29 elapsed days, and
# calculator normalizer treats25-35days as one full bill. At1000kWh the excise
# amount is below the first threshold under both conventions, so these monetary
# examples reconcile without relabeling workbook boundaries or recalculating it.
OFFICIAL_EXAMPLES = [
    ("D17", "2025-06", "171.42", {"distribution_customer":"9.75", "distribution_energy":"28.61",
        "supply_energy":"94.50", "infrastructure_investment":"3.53", "distribution_investment":"6.53",
        "storm_recovery":"2.27", "regulatory_compliance":"1.08", "proactive_reliability":"2.07",
        "pipp":"2.01", "solar_generation":"0.10", "legacy_generation":"1.50", "tax_savings":"-0.19", "excise_tax":"4.65"}),
    ("D19", "2025-06", "193.73", {"distribution_customer":"16.68", "distribution_demand":"23.86",
        "supply_energy":"94.50", "infrastructure_investment":"3.73", "distribution_investment":"6.90",
        "storm_recovery":"8.38", "regulatory_compliance":"3.66", "proactive_reliability":"6.97",
        "pipp":"2.01", "solar_generation":"0.29", "legacy_generation":"1.71", "tax_savings":"-0.20", "excise_tax":"4.65"}),
    ("D17", "2026-11", "208.24", {"distribution_customer":"9.75", "distribution_energy":"49.32",
        "supply_energy":"108.56", "infrastructure_investment":"4.07", "distribution_investment":"4.41",
        "storm_recovery":"0.80", "regulatory_compliance":"1.67", "proactive_reliability":"0.65",
        "pipp":"4.27", "solar_generation":"0.00", "legacy_generation":"0.00", "economic_development":"0.07",
        "customer_programs":"2.25", "tax_savings":"-0.15", "excise_tax":"4.65"}),
]


@pytest.mark.parametrize("plan,month,total,components", OFFICIAL_EXAMPLES)
def test_official_cached_30day_examples_reconcile_literal_components(plan, month, total, components):
    account, index = fixture(plan, month, historical_kw=0)
    # Exactly1000kWh and actual5kW, without a fractional constant-load sum.
    power = np.zeros(len(index)); power[:800] = 5.
    actual, _ = assert_literal_bill(account, index, power)
    assert actual["metrics"]["cycle_days"] == 30
    assert actual["total_usd"] == float(D(total))
    for component, expected in components.items():
        assert actual["lines"][component] == float(D(expected))
    if plan == "D19":
        assert actual["lines"]["transmission_energy"]+actual["lines"]["transmission_demand"] == pytest.approx(20.59)


@pytest.mark.parametrize("plan", ["D17", "D19"])
@pytest.mark.parametrize("month", ["2026-09", "2026-10", "2026-11"])
def test_post_august_benchmark_requires_prior_one_time_refund_resolution(plan, month):
    from src.billing.regional import calculate_cycle
    account, index = fixture(plan, month)
    # September onward is conditional on independently documented prior receipt,
    # not an assumption that the open-ended one-time credit has disappeared.
    account.update(d43_refund_resolved_confirmed=False, d43_refund_received_date="",
                   d43_refund_received_usd=0., d43_refund_source="")
    with pytest.raises(ValueError, match=r"refund|D43|one.time"):
        calculate_cycle("aes_ohio", index, np.full(len(index), 2.), np.zeros(len(index)), account)


@pytest.mark.parametrize("month,plan,energy", [
    ("2025-06", "D19", 1000.137), ("2025-06", "D19", 16000.137),
    ("2026-10", "D19", 1000.137), ("2026-10", "D19", 16000.137),
    ("2026-10", "D17", 1000.137), ("2026-11", "D17", 1000.137),
])
def test_fixed_flow_symbolic_expressions_match_independent_decimal(month, plan, energy):
    import cvxpy as cp
    from src.billing import aes_ohio as aes
    from src.billing.regional_math import BillingMath
    account, index = fixture(plan, month)
    power = np.full(len(index), energy/(len(index)/4))
    expected, _ = literal_bill(plan, month, power, account["history"])
    x, y = cp.Variable(len(index)), cp.Variable(len(index))
    math = BillingMath(index, convex=True, power_bound=25.)
    math.register_power(x, np.zeros(len(index)), np.full(len(index), 25.))
    result = aes.charge_lines(index, x, y, account, math=math)
    problem = cp.Problem(cp.Minimize(sum(result["lines"].values())), [x == power, y == 0, *math.constraints])
    problem.solve(solver="SCIPY")
    assert problem.status in ("optimal", "optimal_inaccurate")
    for key, value in expected.items():
        actual = result["lines"][key]
        assert float(actual.value if hasattr(actual, "value") else actual) == pytest.approx(float(value), abs=2e-7), key
