"""Pepco DC independent filed-rate benchmarks and bounded account contracts."""
from copy import deepcopy
from decimal import Decimal as D

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import pepco_dc as dc
from src.billing.regional_math import BillingMath


def index(month):
    start=pd.Timestamp(month,tz=dc.TIMEZONE)
    return pd.date_range(start,start+pd.offsets.MonthBegin(),freq="15min",inclusive="left")


def bill(plan,month,kwh,**changes):
    idx=index(month)
    account={**dc.hypothetical_defaults(plan,day=month),**changes}
    dc.validate_account(account,idx)
    flow=np.full(len(idx),4*kwh/len(idx))
    return dc.charge_lines(idx,flow,np.zeros(len(idx)),account,math=BillingMath(idx))


# Independent USD/kWh vectors from filed component sheets and monthly charts.
NAMES = """procurement_cost_adjustment administrative_credit bsa_adjustment_ii
delivery_tax public_space_occupancy sustainable_energy_trust mayors_energy_surcharge
energy_assistance_trust residential_aid_surcharge underground_project underground_rider mrp_adjustment""".split()
RATES = {
 ("2025-06-01","R"): ".00316 -.0005703 .000134 .007 .00228 .00651 0 .0002322 .00086 .00027 .00001 0",
 ("2025-06-01","GS-ND"): "-.00427 -.0011827 -.000791 .0077 .00228 .00651 0 .0002322 .00086 .00034 -.00026 0",
 ("2026-06-01","R"): ".00316 0 .000134 .007 .00235 .002056 .004854 .0002322 .001155 .00055 0 0",
 ("2026-06-01","GS-ND"): "-.00427 0 -.000791 .0077 .00235 .002056 .004854 .0002322 .001155 .00067 0 0",
 ("2026-07-01","R"): ".00316 0 .000134 .007 .00235 .002056 .004854 .0002322 .001155 .00055 0 0",
 ("2026-07-01","GS-ND"): "-.00427 0 -.000791 .0077 .00235 .002056 .004854 .0002322 .001155 .00067 0 0",
 ("2026-10-01","R"): ".00316 0 .000134 .007 .00235 .001666 .005544 .0002322 .001155 .00055 0 0",
 ("2026-10-01","GS-ND"): "-.00427 0 -.000791 .0077 .00235 .001666 .005544 .0002322 .001155 .00067 0 0",
}


def independent_lines(plan,month,usage):
    residential=plan=="R"
    newer=month[:4]=="2026"
    july=month>="2026-07-01"
    k=D(str(usage)); first=min(k,D(400)); extra=max(k-D(30),D(0)) if residential else k
    expected=dict(
        distribution_customer=D("18.09" if newer else "17.09") if residential else D("38.30" if newer else "35.59"),
        distribution_energy=(first*D(".01982")+(k-first)*D(".05659") if newer else
                             first*D(".01715")+(k-first)*D(".04895")) if residential else k*D(".07778" if newer else ".07813"),
        generation_minimum_including_admin=D("4.40" if july else "3.94") if residential else D(0),
        generation_energy=extra*D((".14238" if july else ".12800") if residential else (".13874" if july else ".12602")),
        supply_administration=extra*D((".00440" if july else ".00320") if residential else (".00420" if july else ".00450")),
        transmission_minimum=D(".12") if residential else D(0),
        transmission_energy=extra*D((".01924" if newer else ".01751") if residential else ".01415"),
        excess_deferred_income_tax_credit=first*D("-.00047")+(k-first)*D("-.00133") if residential else k*D("-.00342"),
    )
    expected.update({name:k*D(v) for name,v in zip(NAMES,RATES[month,plan].split(),strict=True)})
    return {key:float(value) for key,value in expected.items()}


@pytest.mark.parametrize("month,plan", RATES)
@pytest.mark.parametrize("kwh",[0,15,30,30.5,399.5,400,400.5,1000])
def test_independent_full_component_benchmarks(month,plan,kwh):
    actual=bill(plan,month,kwh)
    assert actual["lines"]==pytest.approx(independent_lines(plan,month,kwh),abs=1e-9)
    assert actual["is_complete_bill"] and not actual["excluded_components"]
    assert actual["next_state"]=={} and not actual["metrics"]["billed_demand"]


@pytest.mark.parametrize("month,plan,kwh",[
 ("2025-06-01","R",15),("2025-06-01","R",30.5),("2026-06-01","R",400.5),
 ("2026-07-01","R",1000),("2026-10-01","R",1000),("2026-10-01","GS-ND",1837.21),
])
def test_numeric_symbolic_parity(month,plan,kwh):
    idx=index(month)
    account=dc.hypothetical_defaults(plan,day=month)
    power=cp.Variable(nonneg=True)
    imports=cp.promote(power,(len(idx),))
    ops=BillingMath(idx,convex=True,power_bound=25.)
    ops.register(imports,0.,25.)
    ops.constraints.append(power==4*kwh/len(idx))
    result=dc.charge_lines(idx,imports,cp.Constant(np.zeros(len(idx))),account,math=ops)
    problem=cp.Problem(cp.Minimize(sum(result["lines"].values())),ops.constraints)
    problem.solve(solver="HIGHS")
    assert problem.status==cp.OPTIMAL
    expected=independent_lines(plan,month,kwh)
    for name,line in result["lines"].items():
        assert (line.value if hasattr(line,"value") else line)==pytest.approx(expected[name],abs=1e-8)


@pytest.mark.parametrize("month",["2025-01-01","2025-03-01","2025-05-01","2025-07-01",
                                  "2025-11-01","2026-02-01","2026-03-01","2026-05-01",
                                  "2026-11-01","2026-12-01","2027-01-01"])
def test_missing_component_periods_reject(month):
    with pytest.raises(ValueError,match="unverified"):
        bill("R",month,1000)


@pytest.mark.parametrize("changes",[
 {"gs_retained_classification_confirmed":False},{"gs_no_demand_meter_confirmed":False},
 {"gs_prior_monthly_usage_kwh":[6000.]*12},{"gs_prior_monthly_usage_kwh":[1500.]*11},
 {"gs_prior_monthly_usage_kwh":[True]*12},{"gs_prior_monthly_usage_kwh":[float("nan")]*12},
 {"gs_usage_review_source":""},{"gs_prior_monthly_demands_kw":[25.]*12},
 {"gs_prior_monthly_demands_kw":[1.]*11},{"gs_prior_monthly_demands_kw":[True]*12},
 {"gs_prior_monthly_demands_kw":[float("nan")]*12},{"gs_history_source":""},
 {"ordinary_service_confirmed":False},{"tax_status_confirmed":False},
 {"supply":"competitive"},{"phase":"three"},{"voltage_v":208.},
 {"export_mode":"net_metering"},{"billing_month":"2026-09-01"},{"bill_date":"2026-11-01"},
 {"rate_evidence_mode":"provisional"},{"opening_credit_usd":1},
])
def test_unsupported_account_facts(changes):
    with pytest.raises(ValueError):
        bill("GS-ND","2026-10-01",10,**changes)


def test_cycle_dst_and_missing_data_fail_closed():
    assert len(index("2025-11-01"))==2884
    assert len(index("2026-03-01"))==2972
    # Both DST months are source gaps, even though their time grids are valid.
    a=dc.hypothetical_defaults("R",day="2026-06-01");idx=index("2026-06-01")
    for malformed in (idx.delete(5),idx.insert(5,idx[5]),idx[1:],idx[::2],idx.tz_convert("UTC")):
        with pytest.raises(ValueError):
            dc.validate_account(a,malformed)
    with pytest.raises(ValueError,match="unverified"):
        dc.validate_account(dc.hypothetical_defaults("R",day="2026-03-01"),index("2026-03-01"))


def test_der_approval_native_scope_and_state():
    idx=index("2026-06-01")
    account=dc.hypothetical_defaults("GS-ND",day="2026-06-01")
    equipment=dict(pv=True,battery=True,renewable_only_charging=True,no_battery_export=True)
    dc.validate_account(account,idx,equipment)
    for changes in ({"der_ordinary_service_confirmed":False},{"der_activation_date":"2026-06-02"},{"der_eligibility_source":""}):
        with pytest.raises(ValueError):
            dc.validate_account({**account,**changes},idx,equipment)
    with pytest.raises(ValueError):
        dc.validate_account(account,idx,{**equipment,"renewable_only_charging":False})
    with pytest.raises(ValueError,match="native load"):
        dc.validate_native_load(account,np.full(len(idx),25.))
    with pytest.raises(ValueError,match="state"):
        dc.validate_state(account,idx,{"credit":1})
    zero=np.zeros(len(idx))
    with pytest.raises(ValueError,match="zero export"):
        dc.charge_lines(idx,zero,np.ones(len(idx)),account,math=BillingMath(idx))


def test_gs_non_demand_energy_limit_is_separate_from_demand_and_reduced_imports():
    month="2026-07-01";idx=index(month)
    account=dc.hypothetical_defaults("GS-ND",day=month)
    # A sub-25kW native profile still breaches this conservative energy domain.
    with pytest.raises(ValueError,match="native load"):
        dc.validate_native_load(account,np.full(len(idx),24000/len(idx)))
    with pytest.raises(ValueError,match="6,000"):
        bill("GS-ND",month,6000)
    assert bill("GS-ND",month,5999.5)["is_complete_bill"]
    power=cp.Variable(nonneg=True);imports=cp.promote(power,(len(idx),))
    ops=BillingMath(idx,convex=True,power_bound=25.)
    ops.register(imports,0.,25.);ops.constraints.append(power==24000/len(idx))
    result=dc.charge_lines(idx,imports,cp.Constant(np.zeros(len(idx))),account,math=ops)
    problem=cp.Problem(cp.Minimize(sum(result["lines"].values())),ops.constraints)
    problem.solve(solver="HIGHS")
    assert problem.status==cp.INFEASIBLE
