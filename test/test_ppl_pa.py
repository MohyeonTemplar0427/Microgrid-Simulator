"""Independent filed PPL arithmetic, account facts, dates and demand objective."""
from decimal import Decimal as D
import json
from pathlib import Path
import hashlib

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import ppl_pa as ppl
from src.billing.ppl_pa_rates import rates_on
from src.billing.regional_math import BillingMath
from src.timeseries import build_interval_index


def fixture(plan="RS", month="2025-07", step=15):
    start=month+"-01";end=str((pd.Timestamp(start)+pd.offsets.MonthEnd()).date())
    a=ppl.hypothetical_defaults(plan);a.update(billing_month=start,bill_date=end)
    return a,build_interval_index(start,end,ppl.TIMEZONE,step).index


def raw_bill(plan="RS", month="2025-07", power=1., **changes):
    a,idx=fixture(plan,month);a.update(changes);ppl.validate_account(a,idx)
    return ppl.charge_lines(idx,np.full(len(idx),power),np.zeros(len(idx)),a,math=BillingMath(idx))


@pytest.mark.parametrize("plan",ppl.PLANS)
@pytest.mark.parametrize("month,hours,res_customer,res_energy,smr,gsc_res,tsc_res,gsc_gs,tsc_gs,ee,storm,dsic,tcja,stas",[
    ("2025-01",744,"15.62",".04990","3.10",".07225",".03546",".07458",".02988",".00243",".00092",".05","-.08","-.00280"),
    ("2025-02",672,"15.62",".04990","3.10",".07225",".03546",".07458",".02988",".00243",".00092",".05","-.08","-.00280"),
    ("2025-03",743,"15.62",".04990","3.10",".07225",".03546",".07458",".02988",".00243",".00092",".0743","-.08","-.00280"),
    ("2025-04",720,"15.70",".04990","3.26",".07225",".03546",".07458",".02988",".00243",".00092",".075","-.08","-.00280"),
    ("2025-05",744,"15.70",".04990","3.26",".07225",".03546",".07458",".02988",".00243",".00092",".075","-.08","-.00280"),
    ("2025-06",720,"15.70",".05049","3.26",".09166",".03324",".08956",".03158",".00166",".00092",".075","-.08","-.00280"),
    ("2025-07",744,"15.58",".05049","3.03",".09166",".03324",".08956",".03158",".00166",".00092",".075","-.08","-.00280"),
    ("2025-08",744,"15.58",".05049","3.03",".09166",".03324",".08956",".03158",".00166",".00092",".075","-.08","-.00280"),
    ("2025-09",720,"15.58",".05049","3.03",".09166",".03324",".08956",".03158",".00166",".00092",".075","-.08","-.00280"),
    ("2025-10",744,"15.52",".05049","2.91",".09166",".03324",".08956",".03158",".00166",".00092",".075","-.08","-.00280"),
    ("2025-11",721,"15.52",".05049","2.91",".09166",".03324",".08956",".03158",".00166",".00092",".075","-.08","-.00280"),
    ("2025-12",744,"15.52",".05049","2.91",".09610",".03343",".09379",".03302",".00166",".00092",".075","-.08","-.00280"),
    ("2026-01",744,"15.48",".04968","2.84",".09610",".03343",".09379",".03302",".00166",".00094",".075","-.0375","-.00311"),
    ("2026-03",743,"15.48",".04968","2.84",".09610",".03343",".09379",".03302",".00166",".00094",".075","-.0375","-.00311"),
    ("2026-04",720,"15.50",".04968","2.86",".09610",".03343",".09379",".03302",".00166",".00094",".075","0","-.00311"),
    ("2026-06",720,"15.50",".04927","2.86",".09804",".03343",".09443",".03302",".00071",".00094",".075","0","-.00311"),
    ("2026-07",744,"15.00",".06157","0",".09753",".03326",".09445",".03303",".00071",".00080","0","0",".00008"),
    ("2026-10",744,"15.00",".06175","0",".09753",".03326",".09445",".03303",".00071",".00094","0","0",".00008"),
])
def test_literal_one_kw_complete_cycle(plan,month,hours,res_customer,res_energy,smr,gsc_res,tsc_res,gsc_gs,tsc_gs,ee,storm,dsic,tcja,stas):
    """Literal filed components and elapsed-hour benchmarks, no rate helper."""
    res=plan=="RS";e=D(hours);post=month>="2026-07"
    expected=dict(distribution_customer=D(res_customer if res else "27.22" if post else "22"),
                  distribution_energy=e*D(res_energy) if res else D(0))
    base=D("14.09")+e*D(".03534") if res else D("27.22" if post else "22")+D("5.923" if post else "4.361")
    if not res:
        expected.update(distribution_demand=D("5.923" if post else "4.361"),
            smart_meter=D(smr),competitive_enhancement=D("0" if post else "-.01"),
            energy_efficiency=e*D(ee),storm_damage=e*D(storm))
    expected["tcja_credit"]=base*D(tcja)
    distribution=sum(expected.values())
    expected["distribution_dsic"]=distribution*D(dsic)
    expected["distribution_state_tax_adjustment"]=(distribution+expected["distribution_dsic"])*D(stas)
    expected["generation_supply"]=e*D(gsc_res if res else gsc_gs)
    expected["transmission_service"]=e*D(tsc_res if res else tsc_gs)
    expected["supply_state_tax_adjustment"]=(expected["generation_supply"]+expected["transmission_service"])*D(".00001")
    expected["sales_tax"]=D(0) if res else sum(expected.values())*D(".06")
    got=raw_bill(plan,month)
    assert got["metrics"]["elapsed_hours"]==hours
    assert set(got["lines"])==set(expected)
    for k,v in expected.items():assert got["lines"][k]==pytest.approx(float(v),abs=1e-9)
    assert got["is_complete_bill"] and got["rate_assumptions"]==[]
    assert not {"merchant_function","gross_receipts_tax","pjm_capacity","pjm_transmission"}&set(got["lines"])
    if res:assert not {"smart_meter","competitive_enhancement","energy_efficiency","storm_damage"}&set(got["lines"])


@pytest.mark.parametrize("plan",ppl.PLANS)
@pytest.mark.parametrize("month",["2025-03","2025-07","2026-04","2026-07","2026-10"])
def test_numerical_symbolic_itemized_bill_parity(plan,month):
    a,idx=fixture(plan,month);imports=.4+2.2*(np.arange(len(idx))%17)/16
    raw=ppl.charge_lines(idx,imports,np.zeros(len(idx)),a,math=BillingMath(idx))
    x=cp.Variable(len(idx));y=cp.Variable(len(idx));m=BillingMath(idx,convex=True,power_bound=4.)
    m.register_power(x,np.zeros(len(idx)),np.full(len(idx),4.))
    expression=ppl.charge_lines(idx,x,y,a,math=m)
    problem=cp.Problem(cp.Minimize(sum(expression["lines"].values())),[x==imports,y==0,*m.constraints])
    problem.solve(solver="SCIPY")
    assert problem.status==cp.OPTIMAL
    for k,v in expression["lines"].items():
        actual=v.value if hasattr(v,"value") else v
        assert float(actual)==pytest.approx(raw["lines"][k],abs=1e-8)


@pytest.mark.parametrize("peak,expected",[(0.,0.),(.49,0.),(.50,1.),(3.49,3.),(3.50,4.),(3.51,4.)])
def test_gs1_whole_kw_half_up_peak_once(peak,expected):
    a,idx=fixture("GS-1");loads=np.zeros(len(idx));loads[50]=peak
    b=ppl.charge_lines(idx,loads,np.zeros(len(idx)),a,math=BillingMath(idx))
    assert b["metrics"]["measured_demand_kw"]==peak
    assert b["metrics"]["billing_demand_kw"]==expected
    assert b["lines"]["distribution_demand"]==pytest.approx(expected*4.361)


@pytest.mark.parametrize("peak", [100., 100.000001])
def test_gs1_study_peak_cap_rejects_exact_boundary_and_above(peak):
    with pytest.raises(ValueError, match="below100kW"):
        raw_bill("GS-1", power=peak)


def test_gs1_study_peak_cap_preserves_supported_lower_edge():
    result = raw_bill("GS-1", power=99.99999)
    assert result["metrics"]["measured_demand_kw"] == pytest.approx(99.99999)
    assert result["metrics"]["billing_demand_kw"] == 100.


def test_half_up_numerical_guard_is_explicit_and_does_not_claim_global_equivalence():
    a,idx=fixture("GS-1");loads=np.zeros(len(idx));loads[50]=3.499995
    with pytest.raises(ValueError,match="guard band"):
        ppl.charge_lines(idx,loads,np.zeros(len(idx)),a,math=BillingMath(idx))
    # The allowed lower edge agrees with the conservative dispatch constraint;
    # an exact half-unit tie always rounds upward in the authoritative bill.
    for p,b in [(3.49999,3.),(3.5,4.)]:
        loads[50]=p
        got=ppl.charge_lines(idx,loads,np.zeros(len(idx)),a,math=BillingMath(idx))
        assert got["metrics"]["billing_demand_kw"]==b
    # Fixed-point convex inputs within the rejected band conservatively select
    # the next kW. They must not be silently labeled exact numerical rebills.
    for p,b in [(3.49999,3.),(3.499995,4.),(3.5,4.)]:
        loads[50]=p
        m=BillingMath(idx,convex=True,power_bound=5.)
        _,d=ppl._billing_demand(m,loads,idx)
        problem=cp.Problem(cp.Minimize(d),m.constraints)
        problem.solve(solver="SCIPY")
        assert problem.status==cp.OPTIMAL and d.value==pytest.approx(b)


def test_bill_rendered_dsic_does_not_split_march_service_energy():
    early=raw_bill("RS","2025-02",bill_date="2025-03-12")
    late=raw_bill("RS","2025-02",bill_date="2025-03-13")
    assert early["metrics"]["rates"]["dsic"]==.05
    assert late["metrics"]["rates"]["dsic"]==.0743
    assert early["lines"]["generation_supply"]==late["lines"]["generation_supply"]
    assert late["lines"]["distribution_dsic"]==pytest.approx(late["metrics"]["dsic_base_distribution_usd"]*.0743)


def test_bill_rendered_tcja_reset_and_base_only_credit():
    early=raw_bill("RS","2026-03",bill_date="2026-04-09")
    late=raw_bill("RS","2026-03",bill_date="2026-04-10")
    assert early["lines"]["tcja_credit"]==pytest.approx(-.0375*(14.09+743*.03534))
    assert late["lines"]["tcja_credit"]==0.
    assert early["lines"]["distribution_energy"]==late["lines"]["distribution_energy"]


@pytest.mark.parametrize("month,transition,count",[("2025-03","2025-03-09",92),("2025-11","2025-11-02",100)])
def test_local_dst_counts_preserve_actual_elapsed_energy(month,transition,count):
    _,idx=fixture(month=month)
    assert sum(idx.date==pd.Timestamp(transition).date())==count
    assert len(idx)==(743 if count==92 else 721)*4


@pytest.mark.parametrize("day",["2024-12-31","2026-11-01","2027-01-01","2025-6-1",None,20250601])
def test_coverage_and_exact_dates_reject(day):
    with pytest.raises(ValueError):rates_on(day)


@pytest.mark.parametrize("change",[
    dict(eligibility_confirmed=False),dict(ordinary_service_confirmed=False),
    dict(local_charges_confirmed=False),dict(full_monthly_charges_confirmed=False),
    dict(supply="retail_supplier"),dict(supply="pjm_lmp"),dict(export_mode="nem"),
    dict(phase="three"),dict(voltage_v=208.),dict(tax_exempt=True),
    dict(tax_jurisdiction="philadelphia"),dict(meter_count=2),dict(opening_credit_usd=1.),
    dict(cycle_source=""),dict(tax_source=""),dict(rate_evidence_mode="provisional"),
    dict(provisional_assumptions_accepted=True),dict(demand_interval_minutes=60),
])
def test_explicit_account_and_unsupported_scope_rejection(change):
    a,idx=fixture();a.update(change)
    with pytest.raises(ValueError):ppl.validate_account(a,idx)


def test_partial_shifted_missing_duplicate_and_wrong_zone_reject():
    a,idx=fixture()
    for invalid in (idx[1:],idx[:-1],idx.delete(30),idx.insert(30,idx[30]),idx.tz_convert("America/Chicago")):
        with pytest.raises(ValueError):ppl.validate_account(a,invalid)
    _,hourly=fixture(step=60)
    with pytest.raises(ValueError,match="15-minute"):ppl.validate_account(a,hourly)


def test_der_confirmation_export_and_state_rejection():
    a,idx=fixture();equipment=dict(pv=True,battery=True,pv_dc_kw=5.,pv_ac_kw=4.,battery_kw=3.)
    ppl.validate_account(a,idx,equipment)
    for changes in [dict(der_ordinary_service_confirmed=False),dict(der_eligibility_source="")]:
        with pytest.raises(ValueError):ppl.validate_account({**a,**changes},idx,equipment)
    with pytest.raises(ValueError,match="50kW"):ppl.validate_account(a,idx,{**equipment,"battery_kw":50.})
    with pytest.raises(ValueError):ppl.validate_state(a,idx,state={"credit":1})
    with pytest.raises(ValueError,match="exports"):
        ppl.charge_lines(idx,np.ones(len(idx)),np.ones(len(idx)),a,math=BillingMath(idx))


def test_catalog_and_safe_defaults_do_not_imply_account_eligibility():
    assert {p["id"] for p in ppl.catalog()}=={"RS","GS-1"}
    for p in ppl.catalog():
        assert p["coverage"]==[dict(start="2025-01-01",end="2026-10-31")]
        assert p["interval_minutes"]==[15] and p["solar_modes"]==["non_export"]
        assert not ppl.defaults(p["id"])["eligibility_confirmed"]


@pytest.mark.parametrize("key",["RS-2025-07","GS-1-2025-07","RS-2026-06","GS-1-2026-06"])
def test_independently_calculated_1000_kwh_benchmark_and_component_rounding(key):
    path=Path(__file__).resolve().parents[1]/"docs/utility_sources/ppl_pa/independent_benchmarks.json"
    expected=json.loads(path.read_text())["cases"][key]
    plan="GS-1" if key.startswith("GS") else "RS"
    a,idx=fixture(plan,expected["billing_month"])
    imports=np.full(len(idx),(1000.-.75)/(len(idx)-1)/.25);imports[40]=3.
    got=ppl.charge_lines(idx,imports,np.zeros(len(idx)),a,math=BillingMath(idx))
    assert sum(imports)*.25==pytest.approx(1000.,abs=1e-8)
    for k,v in expected["unrounded_lines"].items():assert got["lines"][k]==pytest.approx(float(v),abs=1e-8)
    assert sum(got["lines"].values())==pytest.approx(float(expected["unrounded_total"]),abs=1e-8)
    # Study output rounds every item before summing, rather than rounding only
    # the final total; the July2025 commercial example differs by one cent.
    from decimal import ROUND_HALF_UP
    rounded={k:D(str(v)).quantize(D(".01"),rounding=ROUND_HALF_UP) for k,v in got["lines"].items()}
    assert sum(rounded.values())==D(expected["sum_of_rounded_lines_total"])


def test_checked_in_source_extracts_match_provenance_hashes():
    root=Path(__file__).resolve().parents[1]
    ledger=json.loads((root/"docs/utility_sources/ppl_pa/sources.json").read_text())
    assert len(ledger["sources"])>=30
    assert len({r["id"] for r in ledger["sources"]})==len(ledger["sources"])
    for record in ledger["sources"]:
        path=root/record["extracted_text"]
        assert hashlib.sha256(path.read_bytes()).hexdigest()==record["extracted_text_sha256"]
