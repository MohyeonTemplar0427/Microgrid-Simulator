"""Potomac Edison dated rates and the active history-based capacity minimum."""
from copy import deepcopy
from decimal import Decimal as D
import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import potomac_edison_wv as m
from src.billing.regional import calculate_cycle
from src.billing.regional_math import BillingMath


def index(month):
    start=pd.Timestamp(month,tz=m.TIMEZONE)
    return pd.date_range(start,start+pd.offsets.MonthBegin(),freq="15min",inclusive="left")


def bill(plan,month,kwh,state=None,**changes):
    idx=index(month);a={**m.hypothetical_defaults(plan,day=month),**changes}
    return calculate_cycle(m.UTILITY,idx,np.full(len(idx),4*kwh/len(idx)),np.zeros(len(idx)),a,state=state)


@pytest.mark.parametrize("month,plan,total",[
    ("2025-11-01","R","137.43"),("2025-11-01","G","144.80"),
    ("2026-09-01","R","141.51"),("2026-09-01","G","145.492"),
])
def test_official_notice_independent_1000kwh_benchmark(month,plan,total):
    b=bill(plan,month,1000)
    assert b["unrounded_total_usd"]==pytest.approx(float(D(total)))
    assert b["is_complete_bill"] and b["rate_evidence_status"]=="verified"
    assert b["unrounded_lines"]["local_tax"]==b["unrounded_lines"]["state_sales_tax"]==0


def test_minimum_uses_actual_previous_twelve_and_rolls_without_reset():
    month="2026-09-01"
    a=m.hypothetical_defaults("G",day=month)
    a["history"][0]["import_kwh"]=6000.
    first=bill("G",month,0,history=a["history"])
    assert first["unrounded_lines"]["capacity_minimum_adjustment"]==110.5
    assert first["unrounded_total_usd"]==120.5
    assert first["metrics"]["capacity_for_minimum_kw"]==50.
    assert first["next_state"]["history"]==a["history"][1:]+[dict(month="2026-09",import_kwh=0.)]
    second=bill("G","2026-10-01",0,state=first["next_state"])
    assert second["metrics"]["prior_maximum_import_kwh"]==1000.
    assert second["unrounded_total_usd"]==pytest.approx(1000/120*2.41)


@pytest.mark.parametrize("kwh,historymax",[(0,6000),(399.9,6000),(400.1,1000),(3000,1000)])
def test_exact_symbolic_minimum_parity(kwh,historymax):
    month="2026-09-01";idx=index(month);a=m.hypothetical_defaults("G",day=month)
    a["history"][0]["import_kwh"]=historymax
    power=cp.Variable(nonneg=True);imports=cp.promote(power,(len(idx),))
    math=BillingMath(idx,convex=True,power_bound=10.)
    math.register(imports,0,10.)
    math.constraints.append(power==4*kwh/len(idx))
    out=m.charge_lines(idx,imports,cp.Constant(np.zeros(len(idx))),a,math=math)
    problem=cp.Problem(cp.Minimize(sum(out["lines"].values())),math.constraints)
    problem.solve(solver="HIGHS")
    assert problem.status==cp.OPTIMAL
    numeric=bill("G",month,kwh,history=a["history"])
    for key,val in out["lines"].items():
        assert (val.value if hasattr(val,"value") else val)==pytest.approx(numeric["unrounded_lines"][key],abs=1e-7)


@pytest.mark.parametrize("field,value",[
    ("g_no_demand_meter_confirmed",False),("g_capacity_requirements_kw",10.),
    ("g_capacity_requirements_kw",True),("g_capacity_requirements_kw",float("nan")),
    ("history_source",""),("no_local_tax_confirmed",False),("export_mode","net_metering"),
    ("phase","three"),("supply","other"),("bill_date","2026-10-01"),
])
def test_account_boundary(field,value):
    with pytest.raises(ValueError):bill("G","2026-09-01",0,**{field:value})


def test_history_rejects_gaps_stale_values_and_demand_state():
    a=m.hypothetical_defaults("G",day="2026-09-01")
    for changes in ({"month":"2025-07"},{"import_kwh":6000.001},{"import_kwh":True},{"import_kwh":float("nan")}):
        bad=deepcopy(a["history"]);bad[-1].update(changes)
        with pytest.raises(ValueError):bill("G","2026-09-01",0,history=bad)
    with pytest.raises(ValueError):bill("G","2026-09-01",0,state={"credit":2})
    with pytest.raises(ValueError):bill("G","2026-09-01",0,history=a["history"][:-1])


@pytest.mark.parametrize("month",["2025-01-01","2025-07-01","2026-01-01","2026-04-01","2026-07-01","2026-12-01"])
def test_missing_tariff_windows(month):
    with pytest.raises(ValueError,match="unverified"):bill("R",month,1)


def test_dst_missing_meter_and_native_scope():
    b=bill("R","2025-11-01",0)
    assert b["metrics"]["elapsed_hours"]==721
    idx=index("2025-11-01");a=m.hypothetical_defaults("R",day="2025-11-01")
    for bad in (idx.delete(9),idx.insert(9,idx[9]),idx[::2],idx.tz_convert("UTC")):
        with pytest.raises(ValueError):m.validate_account(a,bad)
    with pytest.raises(ValueError,match="zero export"):
        calculate_cycle(m.UTILITY,idx,np.zeros(len(idx)),np.ones(len(idx)),a)
    with pytest.raises(ValueError,match="native load"):
        m.validate_native_load(m.hypothetical_defaults("G"),np.full(2976,9.))


@pytest.mark.parametrize("month,plan,normalization,ecc,ecc2",[
    ("2025-11-01","R","-0.00066","0.00364","0"),
    ("2025-11-01","G","0.00029","0.00278","0"),
    ("2026-09-01","R","0.00028","0.00280","0.00031"),
    ("2026-09-01","G","-0.00006","0.00229","0.00025"),
])
def test_independent_potomac_riders_not_neighboring_mon_power(month,plan,normalization,ecc,ecc2):
    # Separate notice/Sheets7C/7D/7E transcription. The aggregate notices
    # happen to match Mon Power bills, so a total-only check is insufficient.
    lines=bill(plan,month,1000)["unrounded_lines"]
    for name,rate in (("normalization",normalization),("ecc",ecc),("ecc2",ecc2)):
        assert lines[name]==pytest.approx(float(D(rate)*D(1000)),abs=1e-10)


@pytest.mark.parametrize("field,value",[
    ("der_ordinary_service_confirmed",False),("der_activation_date","2026-10-02"),
    ("der_activation_date",""),("der_eligibility_source",""),
])
def test_exact_installation_agreement_and_activation_required(field,value):
    a=m.hypothetical_defaults("R",day="2026-10-01");a[field]=value
    equipment=dict(pv=True,battery=True,renewable_only_charging=True,no_battery_export=True)
    with pytest.raises(ValueError):m.validate_account(a,index("2026-10-01"),equipment)


@pytest.mark.parametrize("equipment",[
    dict(pv=False,battery=True,renewable_only_charging=True,no_battery_export=True),
    dict(pv=True,battery=True,renewable_only_charging=False,no_battery_export=True),
    dict(pv=True,battery=True,renewable_only_charging=True,no_battery_export=False),
])
def test_unsupported_storage_modes_reject(equipment):
    with pytest.raises(ValueError):m.validate_account(m.hypothetical_defaults("R"),index("2026-11-01"),equipment)
