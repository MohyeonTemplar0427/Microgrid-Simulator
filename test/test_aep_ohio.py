"""Independent filed-price arithmetic and explicit ordinary-account boundaries."""
from copy import deepcopy
from decimal import Decimal as D, ROUND_HALF_UP

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import aep_ohio as aep
from src.billing.aep_ohio_rates import rates_on
from src.billing.regional_math import BillingMath
from src.timeseries import build_interval_index


def fixture(plan="RS", month="2026-09", zone="ohio_power", step=15):
    start = month+"-01"
    end = str((pd.Timestamp(start)+pd.offsets.MonthEnd()).date())
    account = aep.hypothetical_defaults(plan)
    account.update(billing_month=start, bill_date=end, legacy_rate_zone=zone)
    return account, build_interval_index(start, end, aep.TIMEZONE, step).index


def calculate(plan="RS", month="2026-09", zone="ohio_power", kwh=None):
    account, index = fixture(plan, month, zone)
    aep.validate_account(account, index)
    imports = np.full(len(index), 1. if kwh is None else kwh/(len(index)*.25))
    return aep.charge_lines(index, imports, np.zeros(len(index)), account, math=BillingMath(index))


# Literal source transcription in dollars; independent of production lookups.
# Rows: month,hours,ESRR,DIR,EDCR,gridRS,gridGS,transRS,transGS,GER,GCRRS,
# GCRGS,ACRR,EE,PIPP,LGRRS,LGRGS,stormRS,stormGS.
ROWS = [
    ("2025-01",744,".0669857",".2363101",".0494232","2.08","17.53",".0438371",".0234674",".07021",".00320",".00273",".0004501",".0008624",".0046279","1.17",".0018007",".97","4.84"),
    ("2025-02",672,".0669857",".2363101",".0494232","2.08","17.53",".0438371",".0234674",".07021",".00320",".00273",".0004501",".0008624",".0046279","1.17",".0018007",".97","4.84"),
    ("2025-03",743,".0669857",".2414004",".0494232","2.08","17.53",".0438371",".0234674",".07021",".00320",".00273",".0004501",".0008624",".0046279","1.17",".0018007",".97","4.84"),
    ("2025-04",720,".0669857",".2414004",".0195121","2.22","18.72",".0353171",".0197070",".07021",".00320",".00273","-.0041073",".0007387",".0046279","1.17",".0018007",".97","4.84"),
    ("2025-05",744,".0669857",".2414004",".0195121","2.22","18.72",".0353171",".0197070",".07021",".00320",".00273","-.0041073",".0007387",".0046279","1.17",".0018007",".97","4.84"),
    ("2025-06",720,".0669857",".2414004",".0195121","2.22","18.72",".0353171",".0197070",".07688",".02298",".01885","-.0041073",".0007387",".0046279","1.17",".0018007",".97","4.84"),
    ("2025-07",744,".0669857",".2337423",".0195121","2.35","19.89",".0353171",".0197070",".07688",".02298",".01885",".0014672",".0007387",".0046279",".88",".0016400",".97","4.84"),
    ("2025-08",744,".0669857",".2337423",".0195121","2.35","19.89",".0353171",".0197070",".07688",".02298",".01885",".0014672",".0007387",".0046279","0","0",".97","4.84"),
    ("2025-09",720,".0669857",".2451638",".0195121","2.35","19.89",".0353171",".0197070",".07688",".02298",".01885",".0014672",".0007387",".0046279","0","0",".97","4.84"),
    ("2025-10",744,".0669857",".2451638",".0353443","2.45","20.75",".0355042",".0215614",".07688",".02298",".01885","-.0057597",".0007387",".0046279","0","0",".97","4.84"),
    ("2025-11",721,".0669857",".2451638",".0353443","2.45","20.75",".0355042",".0215614",".07688",".02298",".01885","-.0057597",".0007387",".0046279","0","0",".20",".99"),
    ("2025-12",744,".0788222",".2407925",".0353443","2.45","20.75",".0355042",".0215614",".07688",".02298",".01885","-.0057597",".0007387",".0046279","0","0",".20",".99"),
    ("2026-01",744,".0788222",".2407925",".0353443","2.62","21.84",".0355042",".0215614",".07688",".02298",".01885",".0027589",".0007387",".0055215","0","0",".20",".99"),
    ("2026-02",672,".0788222",".2407925",".0353443","2.62","21.84",".0355042",".0215614",".07688",".02298",".01885",".0027589",".0007387",".0055215","0","0",".20",".99"),
    ("2026-03",743,".0788222",".2360370",".0353443","2.62","21.84",".0355042",".0215614",".07688",".02298",".01885",".0027589",".0007387",".0055215","0","0",".20",".99"),
    ("2026-05",744,".0580236",".0295915",".0180190","2.80","23.69",".0434364",".0316869",".07688",".02298",".01885","-.0043956",".0004541",".0055215","0","0",".19","1.02"),
    ("2026-06",720,".0580236",".0295915",".0180190","2.80","23.69",".0434364",".0316869",".07508",".02659",".02298","-.0043956",".0004541",".0055215","0","0",".19","1.02"),
    ("2026-07",744,".0580236",".0408549",".0180190","2.65","22.68",".0434364",".0316869",".07508",".02659",".02298",".0041210",".0004541",".0055215","0","0",".19","1.02"),
    ("2026-08",744,".0580236",".0408549",".0180190","2.65","22.68",".0434364",".0316869",".07508",".02659",".02298",".0041210",".0004541",".0055215","0","0",".19","1.02"),
    ("2026-09",720,".0580236",".0538996",".0180190","2.65","22.68",".0434364",".0316869",".07508",".02659",".02298",".0041210",".0004541",".0055215","0","0",".19","1.02"),
    ("2026-10",744,".0580236",".0538996",".0180190","1.26","10.76",".0441180",".0320019",".07508",".02659",".02298","-.0037229",".0004541",".0063634","0","0",".19","1.02"),
]


@pytest.mark.parametrize("plan", aep.PLANS)
@pytest.mark.parametrize("zone", ("ohio_power", "columbus_southern"))
@pytest.mark.parametrize("row", ROWS, ids=[r[0] for r in ROWS])
def test_literal_independent_one_kw_complete_cycle(plan, zone, row):
    month, hours, *values = row
    (esrr,dir_,edcr,grid_res,grid_gs,trans_res,trans_gs,ger,gcr_res,gcr_gs,acrr,
     ee,pipp,lgr_res,lgr_gs,storm_res,storm_gs) = map(D, values)
    res = plan == "RS"
    current = month >= "2026-05"
    kwh = D(hours)
    base_customer = D("13.50" if current and res else "21.00" if current else "10.00" if res else "9.40")
    base_energy = kwh*D(".0347738" if current and res else ".0271520" if current else ".0263125" if res else ".0205802")
    base = base_customer+base_energy
    expected = dict(distribution_customer=base_customer, distribution_energy=base_energy,
        enhanced_service_reliability=base*esrr, distribution_investment=base*dir_,economic_development=base*edcr,
        grid_smart=grid_res if res else grid_gs, storm_damage=storm_res if res else storm_gs,
        transmission=kwh*(trans_res if res else trans_gs), generation_energy=kwh*ger,
        generation_capacity=kwh*(gcr_res if res else gcr_gs), auction_reconciliation=kwh*acrr,
        energy_efficiency=kwh*ee if res else D(0), percentage_income_payment=kwh*pipp,
        legacy_generation_resource=lgr_res if res else kwh*lgr_gs,
        solar_generation_fund=(D(".10") if res else kwh*D(".0002905")) if month < "2025-08" else D(0),
        alternative_energy=kwh*D(".0038973"), ohio_kwh_tax=kwh*D(".00465"),
        throughput_balancing=kwh*D("-.000182") if month == "2025-02" and zone == "columbus_southern" and res else D(0),
        tax_savings_credit=kwh*D("-.001906" if res else "-.001060") if current else D(0))
    expected.update({k:D(0) for k in ("bad_debt","power_forward","ohio_first","retail_reconciliation","sso_credit","energy_efficiency_peak_demand")})
    bill = calculate(plan,month,zone)
    assert bill["metrics"]["elapsed_hours"] == hours
    assert set(bill["lines"]) == set(expected)
    for name, value in expected.items():
        assert bill["lines"][name] == pytest.approx(float(value), abs=1e-9), name
    assert bill["rate_evidence_status"] == "verified" and bill["rate_assumptions"] == []
    assert bill["metrics"]["measured_demand_charge"] is False


@pytest.mark.parametrize("plan,month,expected",[("RS","2026-09","219.22"),("RS","2026-10","211.51"),("GS-1","2026-10","206.38")])
def test_official_example_and_utility_workbook_benchmarks(plan, month, expected):
    bill = calculate(plan,month,kwh=1000.)
    statement = sum(D(str(v)).quantize(D(".01"), rounding=ROUND_HALF_UP) for v in bill["lines"].values())
    assert statement == D(expected)


@pytest.mark.parametrize("plan",aep.PLANS)
@pytest.mark.parametrize("month",["2025-02","2025-07","2025-08","2026-09","2026-10"])
def test_numeric_symbolic_bill_parity(plan,month):
    a,idx = fixture(plan,month,"columbus_southern")
    loads=.6+.3*(np.arange(len(idx))%29)/28
    numeric=aep.charge_lines(idx,loads,np.zeros(len(idx)),a,math=BillingMath(idx))
    x=cp.Variable(len(idx));y=cp.Variable(len(idx));m=BillingMath(idx,convex=True,power_bound=2.)
    m.register_power(x,np.zeros(len(idx)),np.full(len(idx),2.))
    expression=aep.charge_lines(idx,x,y,a,math=m)
    problem=cp.Problem(cp.Minimize(sum(expression["lines"].values())),[x==loads,y==0,*m.constraints])
    problem.solve(solver="SCIPY")
    assert problem.status==cp.OPTIMAL
    for key,value in expression["lines"].items():
        actual=value.value if hasattr(value,"value") else value
        assert float(actual)==pytest.approx(numeric["lines"][key],abs=1e-8)


def test_distinct_generation_transmission_and_no_duplicate_ptc_or_wholesale_charge():
    b=calculate()
    assert set(b["lines"]) >= {"generation_energy","generation_capacity","auction_reconciliation","alternative_energy","transmission"}
    assert not {"price_to_compare","pjm_lmp","plc","nspl","sales_tax","cat_gross_up"}&set(b["lines"])


def test_lgr_and_sgf_cancellation_applies_to_bill_date_not_prorated_service():
    early=rates_on("2025-08-01","RS",bill_date="2025-08-13")
    late=rates_on("2025-08-01","RS",bill_date="2025-08-14")
    assert (early["legacy_generation"],early["solar_generation"])==(.88,.10)
    assert (late["legacy_generation"],late["solar_generation"])==(0.,0.)
    b=calculate("RS","2025-08")
    assert b["lines"]["legacy_generation_resource"]==b["lines"]["solar_generation_fund"]==0.


def test_columbus_southern_february_credit_is_not_applied_to_ohio_power_or_commercial():
    op=calculate("RS","2025-02");csp=calculate("RS","2025-02","columbus_southern")
    assert sum(op["lines"].values())-sum(csp["lines"].values())==pytest.approx(672*.000182)
    assert calculate("GS-1","2025-02","columbus_southern")["lines"]["throughput_balancing"]==0.


@pytest.mark.parametrize("day",["2024-12-31","2026-04-01","2026-04-30","2026-11-01","2026-12-31"])
def test_unverified_dates_and_crossing_base_transition_reject(day):
    with pytest.raises(ValueError,match="coverage|intersections|extrapolation"):
        rates_on(day,"RS")


@pytest.mark.parametrize("value",[None,20250101,"2025-1-1","2025-02-30"])
def test_strict_dates(value):
    with pytest.raises(ValueError,match="ISO"):
        rates_on(value,"RS")


@pytest.mark.parametrize("key,value",[("legacy_rate_zone","nearest_pjm_node"),("eligibility_confirmed",False),
    ("ordinary_service_confirmed",False),("no_local_tax_confirmed",False),("supply","wholesale_lmp"),
    ("tax_self_assessed",True),("meter_count",2),("phase","three"),("power_factor",.9),
    ("cycle_source",""),("rate_evidence_mode","provisional_2025"),("provisional_assumptions_accepted",True)])
def test_account_facts_require_confirmation(key,value):
    a,i=fixture();a[key]=value
    with pytest.raises(ValueError):aep.validate_account(a,i)


def test_no_partial_shifted_missing_duplicate_or_wrong_timezone_intervals():
    a,i=fixture()
    for j in [i[1:],i[:-1],i.delete(50),i.insert(50,i[50]),i.tz_convert("UTC")]:
        with pytest.raises(ValueError):aep.validate_account(a,j)
    a,i=fixture(step=30)
    with pytest.raises(ValueError,match="15-minute|15minute"):aep.validate_account(a,i)


def test_dst_counts_follow_elapsed_index_not_days_times_96():
    for month,hours in [("2025-03",743),("2025-11",721)]:
        a,i=fixture(month=month)
        cycle,_=aep.cycle_review(a,i)
        assert len(i)==hours*4 and cycle["elapsed_hours"]==hours


def test_gs1_eligibility_threshold_is_not_a_demand_charge():
    a,i=fixture("GS-1")
    with pytest.raises(ValueError,match="below10kW"):
        aep.charge_lines(i,np.full(len(i),10.),np.zeros(len(i)),a,math=BillingMath(i))
    a["non_demand_class_confirmed"]=False
    with pytest.raises(ValueError,match="non-demand"):
        aep.validate_account(a,i)


@pytest.mark.parametrize("kwh,expected",[(2000,9.3),(2500,11.395),(15000,63.77),(16000,67.4)])
def test_kwh_tax_tiers_are_monthly_and_not_resummed_per_interval(kwh,expected):
    assert calculate("RS","2026-09",kwh=kwh)["lines"]["ohio_kwh_tax"]==pytest.approx(expected)


def test_der_and_credit_state_are_separate_from_absent_equipment():
    a,i=fixture();equipment=dict(pv=True,battery=True,pv_dc_kw=5.,pv_ac_kw=4.,battery_kw=3.)
    aep.validate_account(a,i,equipment)
    a["der_ordinary_service_confirmed"]=False
    aep.validate_account(a,i,dict(pv=False,battery=False))
    with pytest.raises(ValueError,match="non-export"):
        aep.validate_account(a,i,equipment)
    with pytest.raises(ValueError,match="standalone"):
        aep.validate_account(aep.hypothetical_defaults(),i,dict(pv=False,battery=True))
    with pytest.raises(ValueError,match="opening"):
        aep.validate_state(a,i,state={"credit":1.})


def test_explicit_verified_scope_and_dated_schedule_name():
    assert rates_on("2025-12-31","GS-1")["filed_schedule"]=="GS-1"
    assert rates_on("2026-09-01","GS-1")["filed_schedule"]=="GS-NDM"
    for p in aep.catalog():
        assert p["supply_arrangements"]==["sso"] and p["solar_modes"]==["non_export"]
        assert p["interval_minutes"]==[15]
        assert next(x for x in p["account_fields"] if x["name"]=="rate_evidence_mode")["choices"]==["verified"]
