"""Wheeling Power WV authoritative charges and independently confirmed account limits."""
from decimal import Decimal as D
import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import wheeling_wv as m
from src.billing.regional import calculate_cycle
from src.billing.regional_math import BillingMath


def index(month):
    first=pd.Timestamp(month,tz=m.TIMEZONE)
    return pd.date_range(first,first+pd.offsets.MonthBegin(),inclusive="left",freq="15min")


def bill(plan,month,kwh,**changes):
    idx=index(month)
    a={**m.hypothetical_defaults(plan,day=month),**changes}
    return calculate_cycle(m.UTILITY,idx,np.full(len(idx),kwh*4/len(idx)),np.zeros(len(idx)),a)


@pytest.mark.parametrize("month,plan,kwh,expected",[
    ("2025-10-01","RS",1000,"175.3373"),
    ("2025-10-01","SGS",1000,"131.6645"),
    ("2026-09-01","RS",1000,"183.0646"),
    ("2026-10-01","RS",2000,"344.5292"),
    ("2026-09-01","SGS",1000,"136.133"),
])
def test_independent_filed_bill_and_published_current_residential_examples(month,plan,kwh,expected):
    result=bill(plan,month,kwh)
    assert result["unrounded_total_usd"]==pytest.approx(float(D(expected)))
    assert result["unrounded_lines"]["state_sales_tax"]==result["unrounded_lines"]["local_tax"]==0
    assert result["metrics"]["crrc_applicable"] is False
    assert result["is_complete_bill"] and result["rate_evidence_status"]=="verified"


@pytest.mark.parametrize("plan,kwh",[("RS",0),("RS",499.9),("RS",500),("RS",1500),("SGS",0),("SGS",1834.5)])
@pytest.mark.parametrize("month",["2025-10-01","2026-09-01"])
def test_exact_symbolic_parity(plan,kwh,month):
    idx=index(month);a=m.hypothetical_defaults(plan,day=month)
    power=cp.Variable(nonneg=True);imports=cp.promote(power,(len(idx),))
    math=BillingMath(idx,convex=True,power_bound=25.)
    math.register(imports,0,25.)
    math.constraints.append(power==kwh*4/len(idx))
    out=m.charge_lines(idx,imports,cp.Constant(np.zeros(len(idx))),a,math=math)
    problem=cp.Problem(cp.Minimize(sum(out["lines"].values())),math.constraints)
    problem.solve(solver="HIGHS")
    assert problem.status==cp.OPTIMAL
    numeric=bill(plan,month,kwh)["unrounded_lines"]
    for name,value in out["lines"].items():
        assert (value.value if hasattr(value,"value") else value)==pytest.approx(numeric[name],abs=1e-8)


@pytest.mark.parametrize("changes",[
    {"sgs_capacity_requirements_kw":10.},{"sgs_capacity_requirements_kw":True},
    {"sgs_capacity_requirements_kw":float("nan")},{"sgs_assignment_confirmed":False},
    {"sgs_capacity_source":""},{"supply":"third_party"},{"tax_jurisdiction":"charleston"},
    {"no_local_tax_confirmed":False},{"export_mode":"net_metering"},{"phase":"three"},
    {"cycle_kind":"partial"},{"bill_date":"2026-11-01"},
])
def test_eligibility_and_tax_facts_reject(changes):
    with pytest.raises(ValueError):bill("SGS","2026-10-01",100,**changes)


@pytest.mark.parametrize("month",["2025-01-01","2025-09-01","2025-12-01",
                                  "2026-01-01","2026-03-01","2026-07-01","2026-11-01","2026-12-01"])
def test_source_gaps_reject(month):
    with pytest.raises(ValueError,match="unverified"):bill("RS",month,1)


def test_missing_meter_data_export_and_state():
    idx=index("2026-10-01");a=m.hypothetical_defaults("RS",day="2026-10-01")
    for bad in (idx.delete(5),idx.insert(5,idx[5]),idx[1:],idx.tz_convert("UTC"),idx[::2]):
        with pytest.raises(ValueError):m.validate_account(a,bad)
    zero=np.zeros(len(idx))
    with pytest.raises(ValueError,match="zero export"):
        calculate_cycle(m.UTILITY,idx,zero,np.ones(len(idx)),a)
    with pytest.raises(ValueError,match="state"):
        calculate_cycle(m.UTILITY,idx,zero,zero,a,state={"credit":1})
    assert bill("RS","2026-09-01",0)["total_usd"]==14.02


def test_wheeling_identity_and_joint_tariff_source_do_not_select_apco():
    from src.billing.regional import UTILITIES
    from src.billing.wheeling_wv_rates import ORIGINAL_ENG
    assert m.UTILITY=="wheeling_power_west_virginia"
    assert UTILITIES[m.UTILITY]["module"]=="wheeling_wv"
    out=bill("RS","2025-10-01",1000)
    assert out["metrics"]["source_version"].startswith("tariff21-")
    assert ORIGINAL_ENG in out["rate_sources"]
    assert out["unrounded_lines"]["renewable_generation"]==pytest.approx(.0313)


def test_dst_and_company_specific_crrc_applicability():
    assert len(index("2026-03-01"))/4==743
    with pytest.raises(ValueError,match="unverified"):
        m.validate_account(m.hypothetical_defaults("RS",day="2026-03-01"),index("2026-03-01"))
    result=bill("RS","2025-11-01",1000)
    assert result["metrics"]["elapsed_hours"]==721
    assert result["metrics"]["crrc_applicable"] is False
    assert result["unrounded_lines"]["enec"]==pytest.approx(57.79)
    assert not any("crrc" in k for k in result["unrounded_lines"])


@pytest.mark.parametrize("field,value",[
    ("der_ordinary_service_confirmed",False),("der_activation_date","2026-10-02"),
    ("der_activation_date",""),("der_eligibility_source",""),
])
def test_exact_non_export_der_agreement_required(field,value):
    a=m.hypothetical_defaults("RS",day="2026-10-01");a[field]=value
    equipment=dict(pv=True,battery=True,renewable_only_charging=True,no_battery_export=True)
    with pytest.raises(ValueError):m.validate_account(a,index("2026-10-01"),equipment)
