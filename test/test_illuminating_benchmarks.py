"""Independent literal filed CEI components and Decimal arithmetic.

Expected rates are frozen facts from the preserved delivery/supply selections,
not imported from production tables. Tests import production only to exercise
its public billing and symbolic expressions. No live requests.
"""
from decimal import Decimal as D, ROUND_HALF_UP

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest


MONTHS = [
    ("2025-01", 744), ("2025-06", 720), ("2025-09", 720),
    ("2025-10", 744), ("2025-11", 721), ("2025-12", 744),
    ("2026-10", 744),
]


def literal_tax(energy, calendar_days):
    """ORC5727.81(A): a separate daily rule for non30-day measurements."""
    e = D(str(energy))
    first, second = ((D(2000), D(15000)) if calendar_days == 30 else
                     (D(67) * calendar_days, D(500) * calendar_days))
    base = (min(e, first) * D(".00465") +
            min(max(e-first, D(0)), second-first) * D(".00419") +
            max(e-second, D(0)) * D(".00363"))
    return base / D(".9974")


def literal_lines(plan, month, energy, measured_peak=0, contract_kw=0, calendar_days=None):
    """Literal arithmetic; no production rate/math imports or lookups."""
    r = VECTORS[month]
    e = D(str(energy))
    cls = 0 if plan == "RS" else 1
    residential = cls == 0
    days = calendar_days or pd.Timestamp(month+"-01").days_in_month
    price = lambda key: D(r[key][cls] if isinstance(r[key], list) else r[key])
    demand = max(D(str(measured_peak)), D(5), D(str(contract_kw))) if not residential else D(0)
    base_customer = D(r["rs_customer"] if residential else r["gs_customer"])
    base_energy = e * D(r["rs_energy"]) if residential else D(0)
    base_demand = D(0) if residential else D(r["gs_first_5_kw"]) + (demand-D(5))*D(r["gs_excess_kw"])
    dcr = (base_customer+base_energy+base_demand)*price("dcr") if r["dcr_basis"] == "base_distribution" else (e if residential else demand)*price("dcr")
    return {
        "distribution_customer": base_customer,
        "distribution_energy": base_energy,
        "distribution_demand": base_demand,
        "supply_energy": e*D(r["energy"]),
        "supply_capacity": e*D(r["capacity"][plan]),
        "non_market_transmission": (e if residential else demand)*price("nmb"),
        "delivery_capital": dcr,
        "delivery_capital_credit": (e*D(r["dcr_credit_rs"]) if residential else
            demand*D(r["dcr_credit_gs_kw"])+e*D(r["dcr_credit_gs_kwh"])),
        "alternative_energy": e*D(r["aer"]),
        "delta_revenue": e*price("drr"),
        "distribution_uncollectible": e*D(r["dun"]),
        "generation_reconciliation": e*D(r["gcr"]),
        "pipp_uncollectible": e*D(r["pur"]),
        "nondistribution_uncollectible": e*D(r["ndu"]),
        "economic_development": e*price("edr"),
        "automaker_recovery": e*D(r["automaker"]),
        "tax_savings": e*price("tsa"),
        "demand_side_efficiency": e*D(r["dse"]),
        "phase_in_recovery": e*D(r["pir"]),
        "residential_heating_recovery": e*D(r["rer"]) if residential else D(0),
        "customer_credit_recovery": e*price("ccr"),
        "consumer_rate_credit": D(r["crc_fixed_rs"]) if residential else e*D(r["crc_energy_gs"]),
        "legacy_generation": D(r["lgr_rs"]) if residential else e*D(r["lgr_gs"]),
        "solar_generation_fund": D(r["sgf_rs"]) if residential else e*D(r["sgf_gs"]),
        "vegetation_management": (e if residential else demand)*price("vmc"),
        "advanced_meter": price("ami"),
        "universal_service": e*D(r["usf_first_833000_kwh"]),
        "state_kwh_tax": literal_tax(e, days),
        "sales_tax": D(0),
    }


def fixture(plan, month, contract_kw=12):
    from src.billing import illuminating_oh as cei
    from src.timeseries import build_interval_index
    first = month+"-01"
    end = str((pd.Timestamp(first)+pd.offsets.MonthEnd()).date())
    account = cei.hypothetical_defaults(plan, day=first)
    account.update(billing_month=first, bill_date=end)
    if plan == "GS":
        account["contract_demand_kw"] = contract_kw
    index = build_interval_index(first, end, "America/New_York", 15).index
    return account, index


@pytest.mark.parametrize("plan", ["RS", "GS"])
@pytest.mark.parametrize("month,hours", MONTHS)
@pytest.mark.parametrize("energy", [1000.137, 2077.137, 16000.137])
def test_literal_itemized_months_and_tax_blocks(plan, month, hours, energy):
    from src.billing import illuminating_oh as cei
    from src.billing.regional import calculate_cycle
    from src.billing.regional_math import BillingMath
    account, index = fixture(plan, month)
    imports = np.full(len(index), energy/hours)
    # Generic study bills round their raw floating-point components. Non-tie
    # usage keeps cent reconciliation distinct from exact-decimal invoice
    # rounding; the dedicated tie tests below expose that contract explicitly.
    supplied_energy = sum((D(str(v)) for v in imports), D(0))*D(".25")
    supplied_peak = float(imports.reshape(-1, 2).mean(axis=1).max())
    expected = literal_lines(plan, month, supplied_energy, supplied_peak, 12 if plan == "GS" else 0)
    assert len(index) == hours*4
    cei.validate_account(account, index)
    raw = cei.charge_lines(index, imports, np.zeros(len(index)), account, math=BillingMath(index))
    assert set(raw["lines"]) == set(expected)
    for key, amount in expected.items():
        assert raw["lines"][key] == pytest.approx(float(amount), abs=1e-8), key
    bill = calculate_cycle(cei.UTILITY, index, imports, np.zeros(len(index)), account)
    cents = {k: v.quantize(D(".01"), rounding=ROUND_HALF_UP) for k, v in expected.items()}
    assert bill["lines"] == pytest.approx({k: float(v) for k, v in cents.items()}, abs=1e-8)
    assert bill["total_usd"] == pytest.approx(float(sum(cents.values())), abs=1e-8)
    assert not {"wholesale_lmp", "pjm_capacity", "cat_whole_bill"} & set(raw["lines"])


@pytest.mark.parametrize("month,component,literal_amount", [
    ("2025-11", "economic_development", "2.435"),
    ("2026-10", "phase_in_recovery", ".445"),
])
def test_known_decimal_half_ties_retain_the_generic_study_rounding_contract(month, component, literal_amount):
    from src.billing import illuminating_oh as cei
    from src.billing.regional import calculate_cycle
    account, index = fixture("GS", month)
    imports = np.full(len(index), 1000/(len(index)*.25))
    bill = calculate_cycle(cei.UTILITY, index, imports, np.zeros(len(index)), account)
    literal = D(literal_amount)
    actual_raw = bill["unrounded_lines"][component]
    assert actual_raw == pytest.approx(float(literal), abs=1e-10)
    study_cents = D(str(actual_raw)).quantize(D(".01"), rounding=ROUND_HALF_UP)
    decimal_cents = literal.quantize(D(".01"), rounding=ROUND_HALF_UP)
    assert bill["lines"][component] == float(study_cents)
    # A component exactly at half a cent can land on either adjacent cent
    # after floating-point arithmetic. This is not an exact-invoice claim.
    assert abs(study_cents-decimal_cents) in (D(0), D(".01"))


@pytest.mark.parametrize("plan", ["RS", "GS"])
@pytest.mark.parametrize("month", ["2025-01", "2025-06", "2025-09", "2025-12", "2026-10"])
def test_fixed_flow_symbolic_itemization_agrees_with_literal_arithmetic(plan, month):
    from src.billing import illuminating_oh as cei
    from src.billing.regional_math import BillingMath
    account, index = fixture(plan, month, contract_kw=5)
    # Individual15min spikes do not become30min billing demand unchanged.
    power = np.where(np.arange(len(index)) % 2, 5., 19.)
    if plan == "RS":
        power = power/6
    energy = D(str(float(power.sum()*.25)))
    peak = float(power.reshape(-1, 2).mean(axis=1).max())
    expected = literal_lines(plan, month, energy, peak, 5)
    x = cp.Variable(len(index)); y = cp.Variable(len(index))
    math = BillingMath(index, convex=True, power_bound=25.)
    math.register_power(x, np.zeros(len(index)), np.full(len(index), 25.))
    actual = cei.charge_lines(index, x, y, account, math=math)
    problem = cp.Problem(cp.Minimize(sum(actual["lines"].values())),
                         [x == power, y == 0, *math.constraints])
    problem.solve(solver="SCIPY")
    assert problem.status in ("optimal", "optimal_inaccurate")
    for key, amount in expected.items():
        v = actual["lines"][key]
        assert float(v.value if hasattr(v, "value") else v) == pytest.approx(float(amount), abs=1e-7), key


@pytest.mark.parametrize("month,days", [("2025-06", 30), ("2025-10", 31)])
@pytest.mark.parametrize("band,delta", [(1, -1), (1, 0), (1, 1), (2, -1), (2, 0), (2, 1)])
def test_real_month_bills_straddle_both_statutory_tax_thresholds(month, days, band, delta):
    from src.billing import illuminating_oh as cei
    from src.billing.regional import calculate_cycle
    first, second = (2000, 15000) if days == 30 else (67*days, 500*days)
    energy = (first if band == 1 else second)+delta
    account, index = fixture("GS", month)
    imports = np.full(len(index), energy/(len(index)*.25))
    bill = calculate_cycle(cei.UTILITY, index, imports, np.zeros(len(index)), account)
    assert bill["unrounded_lines"]["state_kwh_tax"] == pytest.approx(float(literal_tax(energy, days)), abs=1e-9)


VECTORS = {'2025-01': {'rs_customer': '4.00',
             'rs_energy': '0.029510',
             'gs_customer': '7.00',
             'gs_first_5_kw': '13.6800',
             'gs_excess_kw': '7.4790',
             'gs_reactive_rkva': '0.36',
             'usf_first_833000_kwh': '0.0021322',
             'usf_excess_kwh': '0.0005680',
             'tsa': ['-0.001865', '-0.001416'],
             'crc_fixed_rs': '-0.51',
             'crc_energy_gs': '-0.000298',
             'ccr': ['0', '0'],
             'dcr_credit_rs': '0',
             'dcr_credit_gs_kw': '0',
             'dcr_credit_gs_kwh': '0',
             'drr': ['0.000006', '0.000005'],
             'dun': '0.000233',
             'ami': ['1.750', '16.215'],
             'pur': '-0.000029',
             'dse': '0',
             'edr': ['0.001044', '0.003842'],
             'automaker': '0.000027',
             'nmb': ['0.025913', '7.6850'],
             'rer': '0.001172',
             'dcr': ['0.478156', '0.442175'],
             'dcr_basis': 'base_distribution',
             'pir': '0.000427',
             'lgr_rs': '1.50',
             'lgr_gs': '0.0018007',
             'sgf_rs': '0.10',
             'sgf_gs': '0.00029051',
             'vmc': ['0.000223', '0.0566'],
             'energy': '.073408',
             'capacity': {'RS': '.003130', 'GS': '.002846'},
             'gcr': '.003073',
             'aer': '-.000213',
             'ndu': '.000524'},
 '2025-06': {'rs_customer': '4.00',
             'rs_energy': '0.029510',
             'gs_customer': '7.00',
             'gs_first_5_kw': '13.6800',
             'gs_excess_kw': '7.4790',
             'gs_reactive_rkva': '0.36',
             'usf_first_833000_kwh': '0.0021322',
             'usf_excess_kwh': '0.0005680',
             'tsa': ['-0.001865', '-0.001416'],
             'crc_fixed_rs': '-0.51',
             'crc_energy_gs': '-0.000298',
             'ccr': ['0', '0'],
             'dcr_credit_rs': '0',
             'dcr_credit_gs_kw': '0',
             'dcr_credit_gs_kwh': '0',
             'drr': ['0.000006', '0.000004'],
             'dun': '0.001024',
             'ami': ['1.882', '16.303'],
             'pur': '-0.000034',
             'dse': '0.001151',
             'edr': ['0.000262', '0.002953'],
             'automaker': '0.000024',
             'nmb': ['0.023233', '6.7456'],
             'rer': '0.001172',
             'dcr': ['0.010944', '4.7478'],
             'dcr_basis': 'energy_or_demand',
             'pir': '0.000427',
             'lgr_rs': '1.50',
             'lgr_gs': '0.0018007',
             'sgf_rs': '0.10',
             'sgf_gs': '0.00029051',
             'vmc': ['0', '0'],
             'energy': '.073661',
             'capacity': {'RS': '.022112', 'GS': '.021864'},
             'gcr': '-.002909',
             'aer': '.000219',
             'ndu': '-.001976'},
 '2025-09': {'rs_customer': '4.00',
             'rs_energy': '0.029510',
             'gs_customer': '7.00',
             'gs_first_5_kw': '13.6800',
             'gs_excess_kw': '7.4790',
             'gs_reactive_rkva': '0.36',
             'usf_first_833000_kwh': '0.0021322',
             'usf_excess_kwh': '0.0005680',
             'tsa': ['-0.001865', '-0.001416'],
             'crc_fixed_rs': '-0.51',
             'crc_energy_gs': '-0.000298',
             'ccr': ['0', '0'],
             'dcr_credit_rs': '0',
             'dcr_credit_gs_kw': '0',
             'dcr_credit_gs_kwh': '0',
             'drr': ['0.000002', '0.000001'],
             'dun': '0.000738',
             'ami': ['1.019', '13.291'],
             'pur': '0.000009',
             'dse': '0.000462',
             'edr': ['0.000190', '0.001163'],
             'automaker': '0.000026',
             'nmb': ['0.023233', '6.7456'],
             'rer': '0.001360',
             'dcr': ['0.010814', '4.6748'],
             'dcr_basis': 'energy_or_demand',
             'pir': '0.000459',
             'lgr_rs': '0',
             'lgr_gs': '0',
             'sgf_rs': '0',
             'sgf_gs': '0',
             'vmc': ['0', '0'],
             'energy': '.066966',
             'capacity': {'RS': '.022112', 'GS': '.021864'},
             'gcr': '-.001206',
             'aer': '.000257',
             'ndu': '-.000926'},
 '2025-10': {'rs_customer': '4.00',
             'rs_energy': '0.029510',
             'gs_customer': '7.00',
             'gs_first_5_kw': '13.6800',
             'gs_excess_kw': '7.4790',
             'gs_reactive_rkva': '0.36',
             'usf_first_833000_kwh': '0.0021322',
             'usf_excess_kwh': '0.0005680',
             'tsa': ['-0.001865', '-0.001416'],
             'crc_fixed_rs': '-0.51',
             'crc_energy_gs': '-0.000298',
             'ccr': ['0', '0'],
             'dcr_credit_rs': '0',
             'dcr_credit_gs_kw': '0',
             'dcr_credit_gs_kwh': '0',
             'drr': ['-0.000001', '-0.000001'],
             'dun': '0.000161',
             'ami': ['1.939', '17.917'],
             'pur': '0.000036',
             'dse': '0.000462',
             'edr': ['0.000267', '0.002435'],
             'automaker': '0.000029',
             'nmb': ['0.025030', '7.1987'],
             'rer': '0.001360',
             'dcr': ['0.010814', '4.6748'],
             'dcr_basis': 'energy_or_demand',
             'pir': '0.000459',
             'lgr_rs': '0',
             'lgr_gs': '0',
             'sgf_rs': '0',
             'sgf_gs': '0',
             'vmc': ['0', '0'],
             'energy': '.066966',
             'capacity': {'RS': '.022112', 'GS': '.021864'},
             'gcr': '.000841',
             'aer': '.000342',
             'ndu': '.001303'},
 '2025-11': {'rs_customer': '4.00',
             'rs_energy': '0.029510',
             'gs_customer': '7.00',
             'gs_first_5_kw': '13.6800',
             'gs_excess_kw': '7.4790',
             'gs_reactive_rkva': '0.36',
             'usf_first_833000_kwh': '0.0021322',
             'usf_excess_kwh': '0.0005680',
             'tsa': ['-0.001865', '-0.001416'],
             'crc_fixed_rs': '-0.51',
             'crc_energy_gs': '-0.000298',
             'ccr': ['0', '0'],
             'dcr_credit_rs': '0',
             'dcr_credit_gs_kw': '0',
             'dcr_credit_gs_kwh': '0',
             'drr': ['-0.000001', '-0.000001'],
             'dun': '0.000161',
             'ami': ['1.939', '17.917'],
             'pur': '0.000036',
             'dse': '0.000462',
             'edr': ['0.000267', '0.002435'],
             'automaker': '0.000029',
             'nmb': ['0.025030', '7.1987'],
             'rer': '0.001360',
             'dcr': ['0.010814', '4.6748'],
             'dcr_basis': 'energy_or_demand',
             'pir': '0.000459',
             'lgr_rs': '0',
             'lgr_gs': '0',
             'sgf_rs': '0',
             'sgf_gs': '0',
             'vmc': ['0', '0'],
             'energy': '.066966',
             'capacity': {'RS': '.022112', 'GS': '.021864'},
             'gcr': '.000841',
             'aer': '.000342',
             'ndu': '.001303'},
 '2025-12': {'rs_customer': '4.00',
             'rs_energy': '0.029510',
             'gs_customer': '7.00',
             'gs_first_5_kw': '13.6800',
             'gs_excess_kw': '7.4790',
             'gs_reactive_rkva': '0.36',
             'usf_first_833000_kwh': '0.0021322',
             'usf_excess_kwh': '0.0005680',
             'tsa': ['-0.001865', '-0.001416'],
             'crc_fixed_rs': '-0.51',
             'crc_energy_gs': '-0.000298',
             'ccr': ['0', '0'],
             'dcr_credit_rs': '0',
             'dcr_credit_gs_kw': '0',
             'dcr_credit_gs_kwh': '0',
             'drr': ['-0.000001', '-0.000001'],
             'dun': '0.000161',
             'ami': ['1.939', '17.917'],
             'pur': '0.000036',
             'dse': '0.000462',
             'edr': ['0.000267', '0.002435'],
             'automaker': '0.000029',
             'nmb': ['0.025030', '7.1987'],
             'rer': '0.001360',
             'dcr': ['0.010831', '4.7142'],
             'dcr_basis': 'energy_or_demand',
             'pir': '0.000459',
             'lgr_rs': '0',
             'lgr_gs': '0',
             'sgf_rs': '0',
             'sgf_gs': '0',
             'vmc': ['0', '0'],
             'energy': '.066966',
             'capacity': {'RS': '.022112', 'GS': '.021864'},
             'gcr': '.000841',
             'aer': '.000342',
             'ndu': '.001303'},
 '2026-10': {'rs_customer': '6.50',
             'rs_energy': '0.048397',
             'gs_customer': '10.00',
             'gs_first_5_kw': '26.6451',
             'gs_excess_kw': '12.5319',
             'gs_reactive_rkva': '0.60',
             'usf_first_833000_kwh': '0.0032567',
             'usf_excess_kwh': '0.0005680',
             'tsa': ['-0.001054', '-0.000779'],
             'crc_fixed_rs': '0',
             'crc_energy_gs': '0',
             'ccr': ['0.002491', '0.000597'],
             'drr': ['0.000006', '0.000004'],
             'dun': '0.000283',
             'ami': ['0.882', '6.483'],
             'pur': '-0.000134',
             'dse': '0.000874',
             'edr': ['0.000291', '0.002192'],
             'automaker': '0.000029',
             'nmb': ['0.029134', '6.6568'],
             'rer': '0',
             'dcr': ['0.001216', '0.4665'],
             'dcr_basis': 'energy_or_demand',
             'dcr_credit_rs': '0',
             'dcr_credit_gs_kw': '0',
             'dcr_credit_gs_kwh': '0',
             'pir': '0.000445',
             'lgr_rs': '0',
             'lgr_gs': '0',
             'sgf_rs': '0',
             'sgf_gs': '0',
             'vmc': ['0', '0'],
             'energy': '.072774',
             'capacity': {'RS': '.028612', 'GS': '.021729'},
             'gcr': '.009846',
             'aer': '.000169',
             'ndu': '.000975'}}

