"""Separate filed-rate transcription, clocks and bounded ordinary KY accounts."""
from decimal import Decimal as D

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import kentucky_power_ky as kp
from src.billing.regional_math import BillingMath


def cycle(month):
    start = pd.Timestamp(month, tz=kp.TIMEZONE)
    return pd.date_range(start, start+pd.offsets.MonthBegin(), freq="15min", inclusive="left")


def bill(plan, month, kwh, **changes):
    index = cycle(month)
    account = {**kp.hypothetical_defaults(plan, day=month), **changes}
    kp.validate_account(account, index)
    imports = np.full(len(index), 4*kwh/len(index))
    return kp.charge_lines(index, imports, np.zeros(len(index)), account, math=BillingMath(index))


# Literal independent transcription: FAC, residential ES, all-other ES. The
# January ES source is PSC2026-00071 Form1.00, not the stale January workbook.
FACTORS = {
    "2025-12-01": (".00586", ".050112", ".086949"),
    "2026-01-01": (".00346", ".048531", ".087593"),
    "2026-02-01": (".00763", ".041856", ".075494"),
    "2026-03-01": (".02200", ".022183", ".036226"),
    "2026-04-01": (".01414", ".035022", ".058077"),
    "2026-05-01": (".01774", ".026526", ".044367"),
    "2026-06-01": (".01377", ".033689", ".057904"),
    "2026-07-01": ("-.00017", ".026963", ".045285"),
    "2026-08-01": (".00496", ".038856", ".067248"),
    "2026-09-01": (".00746", ".033181", ".056682"),
}
SERVICE_MONTHS = [m for m in FACTORS if m <= "2026-08-01"]


def decimal_bill(plan, service_month, kwh, *, billing_month=None):
    """No implementation rate tables or charge functions used here."""
    quantity, new = D(str(kwh)), service_month >= "2026-03-01"
    bm = billing_month or str((pd.Timestamp(service_month)+pd.offsets.MonthBegin()).date())
    fac, res_es, other_es = map(D, FACTORS[bm])
    rs = plan == "RS"
    if rs:
        customer = D("24" if new else "20")
        energy = min(quantity, D("600"))*D(".15385" if new else ".12785")
        energy += max(quantity-D("600"), D(0))*D(".11534" if new else ".12785")
        temporary, assistance, development = quantity*D(".00494"), D(".40"), D(0)
        dsm, tax_credit, ppa = map(D, (".000587", "-.00083", ".00022"))
        gr, dtl = (D(".00476"), D("-.00080")) if new else (D(0), D(0))
        dr, ssr = D(".000082"), D(".057929" if new else ".070704")
        transitional = D("-.00487") if "2026-01-01" <= bm <= "2026-04-01" else D(0)
    else:
        customer = D("31" if new else "28")
        energy = quantity*D(".13725" if new else ".13060")
        temporary, assistance, development = D(0), D(0), D("1")
        dsm, tax_credit, ppa = map(D, (".000573", "-.00058", ".00019"))
        gr, dtl = (D(".00373"), D("-.00057")) if new else (D(0), D(0))
        dr, ssr = D(".000135"), D(".128595" if new else ".109636")
        transitional = D("-.00432") if "2026-01-01" <= bm <= "2026-04-01" else D(0)
    lines = dict(bundled_customer=customer, bundled_energy=energy,
                 temporary_residential_charge=temporary, residential_energy_assistance=assistance,
                 economic_development=development, system_sales=quantity*D("-.00029"),
                 dsm=quantity*dsm, federal_tax_credit=quantity*tax_credit, purchase_power=quantity*ppa,
                 generation=quantity*gr, deferred_tax_liability=quantity*dtl)
    nonfuel = sum(lines.values())-quantity*D(".03380")
    lines.update(fuel_adjustment=quantity*fac, fuel_transition_credit=quantity*transitional)
    basis = sum(lines.values()) if rs else nonfuel
    lines["decommissioning"] = basis*dr
    lines["securitized"] = (basis+lines["decommissioning"])*ssr
    lines["environmental"] = basis*(res_es if rs else other_es)
    lines["school_tax"] = sum(lines.values())*D(".03")
    lines["city_franchise"] = D(0)
    lines["sales_tax"] = D(0) if rs else sum(lines.values())*D(".06")
    return lines


@pytest.mark.parametrize("month", SERVICE_MONTHS)
@pytest.mark.parametrize("plan", ["RS", "GS"])
@pytest.mark.parametrize("kwh", [0, 600, 1000, 2000])
def test_independent_decimal_components(month, plan, kwh):
    actual = bill(plan, month, kwh)
    expected = decimal_bill(plan, month, kwh)
    assert actual["is_complete_bill"] is True
    assert actual["lines"].keys() == expected.keys()
    for name, value in expected.items():
        assert actual["lines"][name] == pytest.approx(float(value), abs=2e-9)


@pytest.mark.parametrize("month", ["2025-12-01", "2026-01-01", "2026-03-01", "2026-08-01"])
@pytest.mark.parametrize("plan,kwh", [("RS", 599.5), ("RS", 600.5), ("GS", 4449)])
def test_exact_numeric_symbolic_parity(month, plan, kwh):
    index, account = cycle(month), kp.hypothetical_defaults(plan, day=month)
    power = cp.Variable(nonneg=True)
    imports = cp.multiply(np.ones(len(index)), power)
    math = BillingMath(index, convex=True, power_bound=25.)
    math.register_power(imports, np.zeros(len(index)), np.full(len(index), 25.), energy_upper=kp.MAX_KWH[plan])
    math.constraints.append(power == 4*kwh/len(index))
    actual = kp.charge_lines(index, imports, cp.Constant(np.zeros(len(index))), account, math=math)
    problem = cp.Problem(cp.Minimize(sum(actual["lines"].values())), math.constraints)
    problem.solve(solver="SCIPY")
    assert problem.status == cp.OPTIMAL
    for name, value in decimal_bill(plan, month, kwh).items():
        amount = actual["lines"][name]
        assert float(amount.value if hasattr(amount, "value") else amount) == pytest.approx(float(value), abs=2e-7)


def test_filed_surcharge_bases_and_january_calculator_correction():
    rs = bill("RS", "2025-12-01", 1000)["lines"]
    ordinary = sum(v for k, v in rs.items() if k not in ("decommissioning", "securitized", "environmental", "school_tax", "city_franchise", "sales_tax"))
    assert rs["environmental"] == pytest.approx(ordinary*.048531)
    assert rs["environmental"] != pytest.approx(ordinary*.050112)
    assert rs["securitized"] == pytest.approx((ordinary+rs["decommissioning"])*.070704)
    gs = bill("GS", "2026-03-01", 1000)["lines"]
    nonfuel = sum(v for k, v in gs.items() if k not in ("fuel_adjustment", "fuel_transition_credit", "decommissioning", "securitized", "environmental", "school_tax", "city_franchise", "sales_tax"))-33.8
    assert gs["decommissioning"] == pytest.approx(nonfuel*.000135)
    assert gs["securitized"] == pytest.approx((nonfuel+gs["decommissioning"])*.128595)
    assert gs["environmental"] == pytest.approx(nonfuel*.058077)
    assert gs["sales_tax"] == pytest.approx((sum(gs.values())-gs["sales_tax"])*.06)


def test_independent_billing_month_and_service_clock():
    # A separate documented utility billing month changes monthly factors, not
    # the service-date base/customer/GR/DTL amounts.
    shifted = bill("RS", "2026-02-01", 1000, billing_month="2026-03-01", bill_date="2026-03-01")
    expected = decimal_bill("RS", "2026-02-01", 1000, billing_month="2026-03-01")
    assert shifted["lines"]["bundled_customer"] == 20
    assert shifted["lines"]["generation"] == 0
    for name, amount in expected.items():
        assert shifted["lines"][name] == pytest.approx(float(amount), abs=2e-9)
    for changes in ({"billing_assignment_confirmed": False}, {"billing_assignment_source": ""},
                    {"billing_month": "2026-05-01", "bill_date": "2026-05-01"},
                    {"bill_date": "2026-01-31"}, {"billing_month": "2026-02-02"},
                    {"billing_month": "2026-02-01", "bill_date": "2026-02-28"}):
        with pytest.raises(ValueError):
            bill("RS", "2026-02-01", 1000, **changes)


@pytest.mark.parametrize("month", ["2024-12-01", "2025-01-01", "2025-11-01", "2026-09-01", "2026-10-01", "2027-01-01"])
def test_unsupported_service_periods_reject(month):
    with pytest.raises(ValueError, match="unverified"):
        bill("RS", month, 1000)


@pytest.mark.parametrize("changes", [
    {"confirmed_tariff_code": "217"}, {"supply": "competitive"}, {"export_mode": "nem"},
    {"tax_jurisdiction": "ky_pikeville"}, {"pike_tax_scope_confirmed": False},
    {"ordinary_service_confirmed": False}, {"tax_source": ""}, {"opening_credit_usd": 1},
    {"gs_no_demand_meter_confirmed": False}, {"gs_maximum_billing_demand_kw": 10.01},
    {"gs_contract_capacity_kw": 10.01}, {"gs_contract_capacity_kw": True},
    {"gs_meter_review_source": ""}, {"provisional_assumptions_accepted": True},
])
def test_account_scope_rejection(changes):
    with pytest.raises(ValueError):
        bill("GS", "2026-08-01", 1000, **changes)


def test_domestic_exemption_native_import_limits_and_dst():
    assert bill("RS", "2026-03-01", 0)["metrics"]["elapsed_hours"] == 743
    with pytest.raises(ValueError, match="domicile"):
        bill("RS", "2026-08-01", 1000, domicile_exemption_confirmed=False)
    for plan, kwh in (("RS", 2000.001), ("GS", 4450)):
        with pytest.raises(ValueError, match="envelope"):
            bill(plan, "2026-08-01", kwh)
    for plan, power in (("RS", 25.01), ("GS", 9.5)):
        with pytest.raises(ValueError, match="native load"):
            kp.validate_native_load(kp.hypothetical_defaults(plan), np.array([power]))
    for plan, energy in (("RS", 2000.001), ("GS", 4449.001)):
        with pytest.raises(ValueError, match="native load"):
            kp.validate_native_load(kp.hypothetical_defaults(plan), np.full(3000, energy/750))


def test_missing_duplicate_intervals_exports_and_state():
    index, account = cycle("2026-03-01"), kp.hypothetical_defaults("RS", day="2026-03-01")
    for malformed in (index.delete(100), index.insert(100, index[100]), index[1:], index[::2], index.tz_convert("UTC")):
        with pytest.raises(ValueError):
            kp.validate_account(account, malformed)
    with pytest.raises(ValueError, match="zero export"):
        kp.charge_lines(index, np.zeros(len(index)), np.ones(len(index)), account, math=BillingMath(index))
    with pytest.raises(ValueError, match="state"):
        kp.validate_state(account, index, {"credit": 1})
    # Fall DST exists even though the unreconciled November stack is blocked.
    fall = cycle("2026-11-01")
    assert len(fall) == 2884
    with pytest.raises(ValueError, match="unverified"):
        kp.validate_account(kp.hypothetical_defaults("RS", day="2026-11-01"), fall)


def test_der_written_agreement_final_date_and_pv_only_storage():
    account, index = kp.hypothetical_defaults("RS", day="2026-08-01"), cycle("2026-08-01")
    equipment = dict(pv=True, battery=True, renewable_only_charging=True, no_battery_export=True)
    kp.validate_account(account, index, equipment)
    for changes in ({"der_ordinary_service_confirmed": False}, {"der_eligibility_source": ""}, {"der_activation_date": "2026-08-02"}):
        with pytest.raises(ValueError):
            kp.validate_account({**account, **changes}, index, equipment)
    for changes in ({"pv": False}, {"renewable_only_charging": False}, {"no_battery_export": False}):
        with pytest.raises(ValueError):
            kp.validate_account(account, index, {**equipment, **changes})
