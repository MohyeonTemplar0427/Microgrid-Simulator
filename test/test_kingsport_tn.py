from decimal import Decimal as D

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import kingsport_tn as tn, regional
from src.billing.kingsport_tn_rates import rates_for_month
from src.billing.regional_math import BillingMath


def cycle(month):
    start = pd.Timestamp(month, tz="America/New_York")
    return pd.date_range(start, start + pd.offsets.MonthBegin(), freq="15min", inclusive="left")


def bill(plan, month, kwh, *, equipment=None, **updates):
    account = {**tn.hypothetical_defaults(plan, day=month), **updates}
    index = cycle(month)
    tn.validate_account(account, index, equipment)
    return tn.charge_lines(index, np.full(len(index), 4*kwh/len(index)), np.zeros(len(index)),
                           account, math=BillingMath(index))


def independent(plan, month, day, quantity, *, prompt=True):
    """Literal source transcription, separate from the production rate loader and charge expression."""
    kwh = D(str(quantity))
    commercial = plan == "SGS"
    base = (min(kwh, D(600))*D(".03225") + max(kwh-D(600), D(0))*D(".02076")
            if commercial else kwh*D(".00325"))
    fppar = ((".08279", ".10219") if day < "2025-11-01" else
             (".07699", ".09504") if day < "2026-11-01" else (".08601", ".10617"))
    trp = (("6.87", "3.85") if month < "2025-09-01" else
           ("12.20", "6.84") if month < "2026-07-01" else ("13.94", "7.81"))
    index = 0 if commercial else 1
    result = dict(distribution_customer=D("22.03" if commercial else "16.43"), distribution_energy=base,
                  federal_tax_rate_adjustment=D(0), fuel_purchased_power=kwh*D(fppar[index]),
                  targeted_reliability_major_storm=D(trp[index]), administrative_cost=kwh*D(".00011"))
    result["prompt_payment_discount"] = -sum(result.values())*D(".015") if prompt else D(0)
    result["kingsport_franchise_fee"] = sum(result.values())*D(".05")
    result["tennessee_sales_tax"] = sum(result.values())*(D(".07") if commercial else D(0))
    return result


@pytest.mark.parametrize("plan", ["RS", "SGS"])
@pytest.mark.parametrize("month", [f"2025-{m:02}-01" for m in range(1,13)] +
                                  [f"2026-{m:02}-01" for m in range(1,11)])
def test_every_verified_calendar_month_matches_independent_bill(plan, month):
    r = bill(plan, month, 937.25)
    assert r["lines"] == pytest.approx({k: float(v) for k,v in independent(plan, month, r["metrics"]["bill_date"], 937.25).items()})
    assert r["is_complete_bill"] and r["rate_evidence_status"] == "verified" and not r["excluded_components"]
    assert not r["next_state"] and r["rate_sources"] and r["metrics"]["billing_demand_applied"] is False


@pytest.mark.parametrize("plan,month,kwh,published,city_total", [
    ("RS","2025-03-01",1000,125.72,130.1396775), ("RS","2025-09-01",1000,128.71,133.232085),
    ("RS","2025-11-01",1000,121.56,125.8371975), ("RS","2026-07-01",1000,122.53,126.84042),
    ("SGS","2025-03-01",750,113.45,125.6476505025), ("SGS","2025-09-01",750,118.78,131.5460816775),
    ("SGS","2025-11-01",750,114.43,126.7321650525), ("SGS","2026-07-01",750,116.17,128.6577317025),
])
def test_commission_exhibit_and_complete_city_invoice(plan, month, kwh, published, city_total):
    # TPUC 25-00022/26-00015 exhibit 3 is base + FPPAR + TRP&MS. Its SGS
    # example rounds the 600-kWh blocks separately. City bills also include
    # ACR, payment treatment, the city franchise fee and applicable state tax.
    result = bill(plan, month, kwh)["lines"]
    assert sum(result[k] for k in ("distribution_customer", "distribution_energy", "fuel_purchased_power",
                                   "targeted_reliability_major_storm")) == pytest.approx(published, abs=.01)
    assert sum(result.values()) == pytest.approx(city_total, abs=1e-8)


@pytest.mark.parametrize("kwh,example", [(1000, 131.76), (2000, 239.65)])
def test_utility_november_2026_web_example_before_city_franchise(kwh, example):
    result = bill("RS", "2026-10-01", kwh, bill_date="2026-11-01", billing_month="2026-11-01")["lines"]
    assert round(sum(result.values()) - result["kingsport_franchise_fee"], 2) == example
    assert result["kingsport_franchise_fee"] > 0


@pytest.mark.parametrize("month,bill_date,rs_fuel,rs_storm", [
    ("2025-08-01","2025-09-03",.10219,3.85), ("2025-10-01","2025-10-31",.10219,6.84),
    ("2025-10-01","2025-11-01",.09504,6.84), ("2026-06-01","2026-07-01",.09504,6.84),
    ("2026-07-01","2026-08-04",.09504,7.81), ("2026-10-01","2026-11-19",.10617,7.81),
])
def test_independent_service_and_rendered_bill_clocks(month, bill_date, rs_fuel, rs_storm):
    r = bill("RS", month, 1., bill_date=bill_date, billing_month=bill_date[:7]+"-01")
    assert r["lines"]["fuel_purchased_power"] == pytest.approx(rs_fuel)
    assert r["lines"]["targeted_reliability_major_storm"] == rs_storm


@pytest.mark.parametrize("plan,quantity,prompt", [
    ("RS",0,False), ("RS",1000,True), ("SGS",0,True), ("SGS",599.99,True),
    ("SGS",600,False), ("SGS",600.01,False), ("SGS",1877.25,True),
])
def test_symbolic_and_numeric_expression_parity(plan, quantity, prompt):
    month = "2025-11-01"
    index = cycle(month)
    account = tn.hypothetical_defaults(plan, day=month)
    account["payment_basis"] = "prompt_15_days" if prompt else "gross_bill"
    v = cp.Variable(nonneg=True)
    inputs = cp.promote(v, (len(index),))
    ops = BillingMath(index, convex=True, power_bound=25.)
    ops.register(inputs, 0., 25.)
    ops.constraints.append(v == 4.*quantity/len(index))
    result = tn.charge_lines(index, inputs, cp.Constant(np.zeros(len(index))), account, math=ops)
    problem = cp.Problem(cp.Minimize(sum(result["lines"].values())), ops.constraints)
    problem.solve(solver="HIGHS")
    assert problem.status == cp.OPTIMAL
    values = {k: (v.value if hasattr(v, "value") else v) for k,v in result["lines"].items()}
    assert values == pytest.approx({k: float(v) for k,v in independent(plan, month, account["bill_date"], quantity, prompt=prompt).items()}, abs=1e-8)
    assert values == pytest.approx(bill(plan, month, quantity, payment_basis=account["payment_basis"])["lines"], abs=1e-8)


@pytest.mark.parametrize("changes", [
    {"confirmed_tariff_code":"233"}, {"normal_max_demand_kw":10.}, {"normal_max_demand_kw":float("nan")},
    {"normal_max_demand_kw":True}, {"normal_max_demand_kw":-1.}, {"normal_demand_source":""}, {"account_source":""},
    {"supply":"third_party"}, {"voltage":"primary"}, {"meter_count":True}, {"locality":"outside_city"},
    {"payment_basis":"late_fee"}, {"opening_credit_usd":1.}, {"opening_credit_kwh":12.},
    {"export_mode":"net_metering"}, {"rate_evidence_mode":"provisional"}, {"cycle_kind":"initial"},
    {"provisional_assumptions_accepted":True}, {"bill_date":"2026-06-30"}, {"bill_date":"2026-07-30"},
    {"bill_date":"2026-09-04","billing_month":"2026-09-01"}, {"billing_month":"2026-08-01"},
    *[{key:False} for key in tn.CONFIRMATIONS],
])
def test_unsupported_accounts_rejected(changes):
    with pytest.raises(ValueError):
        bill("SGS", "2026-07-01", 0., **changes)


@pytest.mark.parametrize("month", ["2024-12-01","2026-11-01","2026-12-01","2026-07-02","2026-07",None])
def test_unsupported_or_malformed_date(month):
    with pytest.raises(ValueError):
        rates_for_month(month, "RS")


def test_defaults_native_load_plan_assignment_and_zero_bank():
    for plan in ("RS","SGS"):
        assert not any(tn.defaults(plan)[k] for k in tn.CONFIRMATIONS)
        assert tn.hypothetical_defaults(plan)["hypothetical_account"]
    assert bill("SGS", "2026-07-01", 0., confirmed_tariff_code="232")["metrics"]["tariff_code"] == "232"
    with pytest.raises(ValueError, match="domestic"):
        bill("RS","2026-07-01", 0., residential_use_confirmed=False)
    a = tn.hypothetical_defaults("SGS")
    for invalid in ([10.], [-.1], [np.nan], []):
        with pytest.raises(ValueError):
            tn.validate_native_load(a, invalid)
    tn.validate_native_load(a, [0., 9.999])
    with pytest.raises(ValueError, match="empty"):
        tn.validate_state(a, cycle("2026-07-01"), {"credit_kwh":1})


@pytest.mark.parametrize("equipment,changes", [
    ({"pv":True,"pv_ac_kw":0}, {}), ({"pv":True,"pv_ac_kw":10.01}, {}),
    ({"pv":True,"pv_ac_kw":3}, {"nms_approved":False}), ({"pv":True,"pv_ac_kw":3}, {"der_eligibility_source":""}),
    ({"pv":True,"pv_ac_kw":3}, {"der_activation_date":"2026-07-02"}), ({"pv":True}, {}),
    ({"pv":True,"pv_ac_kw":3}, {"nms_historical_annual_kwh":5000}),
    ({"pv":True,"pv_ac_kw":3}, {"nms_projected_annual_kwh":float("nan")}),
    ({"pv":True,"pv_ac_kw":3,"battery":True}, {}), ({"battery":True}, {}),
])
def test_approved_nonexport_solar_limits_and_storage(equipment, changes):
    with pytest.raises(ValueError):
        bill("RS","2026-07-01", 0., equipment=equipment, **changes)
    assert bill("SGS","2026-07-01", 0., equipment={"pv":True, "pv_ac_kw":10.})["is_complete_bill"]


@pytest.mark.parametrize("month,hours", [("2025-03-01",743.),("2025-11-01",721.),("2026-03-01",743.)])
def test_dst_and_missing_dates(month, hours):
    a = tn.hypothetical_defaults("RS", day=month)
    index = cycle(month)
    assert tn.cycle_review(a, index)[0]["elapsed_hours"] == hours
    for invalid in (index.delete(20), index[1:], index.insert(50, index[50]), index[::2],
                    index.tz_convert("UTC"), index.tz_localize(None), index.insert(1, pd.NaT)):
        with pytest.raises(ValueError):
            tn.validate_account(a, invalid)


def test_numeric_meter_flows_and_line_rounding(monkeypatch):
    monkeypatch.setitem(regional.UTILITIES, tn.UTILITY, dict(module="kingsport_tn", state="TN", zone="AEP"))
    a = tn.hypothetical_defaults("SGS")
    idx = cycle("2026-07-01")
    inputs = np.full(len(idx), 4*750/len(idx))
    zero = np.zeros(len(idx))
    result = regional.calculate_cycle(tn.UTILITY, idx, inputs, zero, a)
    assert result["total_usd"] == pytest.approx(sum(result["lines"].values()))
    assert abs(result["total_usd"]-128.6577317025) <= result["rounding_bound_usd"]
    for bad_import, bad_export in ((inputs, np.ones(len(idx))), (inputs[:-1], zero), (inputs,np.full(len(idx),np.nan)),
                                  (np.full(len(idx),10.),zero), (-inputs,zero)):
        with pytest.raises(ValueError):
            regional.calculate_cycle(tn.UTILITY, idx, bad_import, bad_export, a)
