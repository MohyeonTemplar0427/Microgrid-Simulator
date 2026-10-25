"""Independent Wisconsin Electric bills, tax/fee branches and tariff calendars."""
from decimal import Decimal as D

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import we_energies_wi as wi
from src.billing.regional import calculate_cycle
from src.billing.regional_math import BillingMath
from src.billing.we_energies_wi_rates import service_rates
from src.timeseries import build_interval_index


def fixture(plan="Rg1", month="2026-07", step=15):
    start=month+"-01"; end=str((pd.Timestamp(start)+pd.offsets.MonthEnd()).date())
    a=wi.hypothetical_defaults(plan); a.update(billing_month=start,bill_date=end)
    return a,build_interval_index(start,end,wi.TIMEZONE,step).index


@pytest.mark.parametrize("plan",wi.PLANS)
@pytest.mark.parametrize("month,ecc_res,ecc_ci",[
    ("2025-01",".00056",".00052"),("2025-02",".00056",".00052"),
    ("2025-03",".00056",".00052"),("2025-04",".00056",".00052"),
    ("2025-05",".00056",".00052"),("2025-06",".00055",".00050"),
    ("2025-07",".00055",".00050"),("2025-08",".00055",".00050"),
    ("2025-09",".00055",".00050"),("2025-10",".00055",".00050"),
    ("2025-11",".00055",".00050"),("2025-12",".00055",".00050"),
    ("2026-01",".00052",".00047"),("2026-02",".00052",".00047"),
    ("2026-03",".00052",".00047"),("2026-04",".00052",".00047"),
    ("2026-05",".00052",".00047"),("2026-06",".00054",".00048"),
    ("2026-07",".00054",".00048"),("2026-08",".00054",".00048"),
    ("2026-09",".00054",".00048")])
def test_independent_monthly_component_benchmark(plan,month,ecc_res,ecc_ci):
    a,idx=fixture(plan,month); res=plan in ("Rg1","Rg2"); tou=plan in ("Rg2","Cg6")
    assumed="2025-07"<=month<="2025-12"
    if assumed:
        a.update(rate_evidence_mode="provisional_2025",provisional_assumptions_accepted=True)
    # Explicit fixture dates independently count billed energy. July3,2026 and
    # Good Friday stay ordinary weekdays; no neighboring utility calendar reuse.
    holiday={"2025-01-01","2025-05-26","2025-07-04","2025-09-01","2025-11-27","2025-12-25",
             "2026-01-01","2026-05-25","2026-07-04","2026-09-07"}
    peak=D(sum(t.weekday()<5 and str(t.date()) not in holiday and 9<=t.hour<21 for t in idx))/4
    hours=D(len(idx))/4; days=D(idx[-1].day)
    values={2025:{"Rg1":(".18325",".18325"),"Rg2":(".27006",".10387"),
                  "Cg1":(".16659",".16659"),"Cg6":(".25388",".09765")},
            2026:{"Rg1":(".19342",".19342"),"Rg2":(".30084",".10028"),
                  "Cg1":(".17621",".17621"),"Cg6":(".29475",".09825")}}
    pk,off=map(D,values[int(month[:4])][plan])
    energy=peak*pk+(hours-peak)*off if tou else hours*pk
    refund=D("-.04054" if res else "-.03620") if month=="2025-09" else D(0)
    expected=dict(customer=days*D(".49315"),energy=energy,
        fuel=hours*(D(0) if month.startswith("2025") else D(".00199")),
        fuel_reconciliation=hours*refund,environmental_control=hours*D(ecc_res if res else ecc_ci))
    subtotal=sum(expected.values())
    expected["state_low_income_assistance"]=min(subtotal*D(".03"),D("3.15" if res else "10.66"))
    expected["wisconsin_sales_tax"]=subtotal*(D(0) if res and idx[-1].month in (11,12,1,2,3,4) else D(".05"))
    bill=calculate_cycle(wi.UTILITY,idx,np.ones(len(idx)),np.zeros(len(idx)),a)
    assert bill["unrounded_lines"]==pytest.approx({k:float(v) for k,v in expected.items()},abs=1e-8)
    assert bill["unrounded_total_usd"]==pytest.approx(float(sum(expected.values())),abs=1e-8)
    assert bill["is_complete_bill"] and bill["rate_evidence_status"]==("provisional" if assumed else "verified")
    assert bill["metrics"]["provisional_ecc_applied"]==assumed
    assert bill["metrics"]["billing_rule_evidence_status"]=="verified"
    assert bill["metrics"]["verified_base_energy_and_fuel"] is True
    assert bill["total_usd"]==pytest.approx(sum(bill["lines"].values()))
    assert not bill["metrics"]["measured_demand_charge"]


@pytest.mark.parametrize("plan",["Rg2","Cg6"])
@pytest.mark.parametrize("day,peak",[
    ("2025-01-01 12:00",False),("2025-05-26 12:00",False),
    ("2025-07-04 12:00",False),("2025-09-01 12:00",False),
    ("2025-11-27 12:00",False),("2025-12-25 12:00",False),
    ("2026-07-03 12:00",True),("2027-07-05 12:00",False),
    ("2025-04-18 12:00",True),("2025-06-19 12:00",True),
    ("2025-12-24 12:00",True),("2025-11-28 12:00",True),
    ("2026-07-06 08:45",False),("2026-07-06 09:00",True),
    ("2026-07-06 20:45",True),("2026-07-06 21:00",False)])
def test_six_holidays_and_observed_days(day,peak,plan):
    idx=pd.DatetimeIndex([pd.Timestamp(day,tz=wi.TIMEZONE)])
    assert bool(wi.periods(idx,plan)["peak"][0])==peak


@pytest.mark.parametrize("start",[7,8,9,10])
def test_rg2_customer_selected_windows_and_bill(start):
    a,idx=fixture("Rg2"); a["on_peak_start_hour"]=start
    imp=np.zeros(len(idx)); imp[(idx.day==6)&(idx.hour==start-1)&(idx.minute==45)]=1.
    imp[(idx.day==6)&(idx.hour==start)&(idx.minute==0)]=1.
    imp[(idx.day==6)&(idx.hour==start+12)&(idx.minute==0)]=1.
    bill=calculate_cycle(wi.UTILITY,idx,imp,np.zeros(len(idx)),a)
    assert bill["unrounded_lines"]["energy"]==pytest.approx(.25*(.30084+2*.10028))
    assert wi.periods(idx,"Rg2",start)["peak"].sum()==23*48 # SaturdayJuly4 causes no Friday substitution.


@pytest.mark.parametrize("key,value",[("eligibility_confirmed",False),("ordinary_service_confirmed",False),
    ("full_monthly_charges_confirmed",False),("local_charges_confirmed",False),
    ("tax_jurisdiction","milwaukee"),("tax_source",""),("cycle_source",""),
    ("meter_count",2),("service_line_count",2),("supply","miso_lmp"),
    ("export_mode","net_metering"),("opening_credit_usd",1.),("phase","three"),
    ("principal_residence_confirmed",False),
    ("on_peak_start_hour",6)])
def test_explicit_account_facts_and_bounded_scope(key,value):
    a,idx=fixture(); a[key]=value
    with pytest.raises(ValueError):wi.validate_account(a,idx)


def test_tou_enrollment_commercial_classification_and_der_approval():
    a,idx=fixture("Cg6"); a["tou_enrollment_confirmed"]=False
    with pytest.raises(ValueError,match="TOU"):wi.validate_account(a,idx)
    a["tou_enrollment_confirmed"]=True; a["small_general_confirmed"]=False
    with pytest.raises(ValueError,match="classification"):wi.validate_account(a,idx)
    a["small_general_confirmed"]=True
    a["on_peak_start_hour"]=7
    with pytest.raises(ValueError,match="fixed"):wi.validate_account(a,idx)
    a["on_peak_start_hour"]=9
    with pytest.raises(ValueError,match="329kWh"):calculate_cycle(wi.UTILITY,idx,np.full(len(idx),14.),np.zeros(len(idx)),a)
    equipment=dict(pv=True,battery=True,pv_dc_kw=10.,pv_ac_kw=8.,battery_kw=8.)
    wi.validate_account(a,idx,equipment)
    a["dg_enrollment_confirmed"]=False
    with pytest.raises(ValueError,match="CGS-NP"):wi.validate_account(a,idx,equipment)
    a["dg_enrollment_confirmed"]=True
    with pytest.raises(ValueError,match="40kW"):wi.validate_account(a,idx,{**equipment,"pv_dc_kw":40.})
    with pytest.raises(ValueError,match="standalone"):wi.validate_account(a,idx,{**equipment,"pv":False})
    with pytest.raises(ValueError,match="non-export"):calculate_cycle(wi.UTILITY,idx,np.ones(len(idx)),np.ones(len(idx)),a)


@pytest.mark.parametrize("month,hours,days",[("2025-03",743,31),("2026-03",743,31)])
def test_dst_daily_customer_fee_and_missing_records(month,hours,days):
    a,idx=fixture(month=month)
    bill=calculate_cycle(wi.UTILITY,idx,np.ones(len(idx)),np.zeros(len(idx)),a)
    assert bill["import_kwh"]==hours
    assert bill["unrounded_lines"]["customer"]==pytest.approx(days*.49315)
    for bad in (idx.delete(20),idx.insert(20,idx[20]),idx[1:],idx[:-1],idx.tz_convert("UTC")):
        with pytest.raises(ValueError):wi.validate_account(a,bad)
    with pytest.raises(ValueError,match="complete calendar"):
        wi.validate_account(a,build_interval_index("2025-03-15","2025-04-14",wi.TIMEZONE,15).index)


@pytest.mark.parametrize("day",["2024-12-31","2025-07-01","2025-08-01","2025-09-01","2025-10-01","2025-11-01","2025-12-01","2026-10-01","2026-12-01","2027-01-01"])
def test_coverage_rejects_future_current_book_components(day):
    with pytest.raises(ValueError,match="coverage"):service_rates(day,"Rg1")


@pytest.mark.parametrize("plan",wi.PLANS)
@pytest.mark.parametrize("power",[0.,.25,2.])
@pytest.mark.parametrize("month",["2025-06","2025-09"])
def test_exact_capped_fee_numeric_symbolic_parity(plan,power,month):
    a,idx=fixture(plan,month,30); n=len(idx); g=cp.Variable(n,nonneg=True)
    if month=="2025-09":
        a.update(rate_evidence_mode="provisional_2025",provisional_assumptions_accepted=True)
    math=BillingMath(idx,convex=True,power_bound=3.)
    math.register_power(g,np.zeros(n),np.full(n,3.))
    result=wi.charge_lines(idx,g,cp.Constant(np.zeros(n)),a,math=math)
    problem=cp.Problem(cp.Minimize(sum(result["lines"].values())),[g==power,*math.constraints])
    problem.solve(solver="SCIPY",scipy_options={"time_limit":20.})
    bill=calculate_cycle(wi.UTILITY,idx,np.full(n,power),np.zeros(n),a)
    assert problem.status=="optimal" and problem.value==pytest.approx(bill["unrounded_total_usd"],abs=1e-6)
    fee=bill["unrounded_lines"]["state_low_income_assistance"]
    assert fee==pytest.approx(min(.03*bill["metrics"]["sales_tax_base_usd"],3.15 if plan.startswith("Rg") else 10.66))
    if month=="2025-09":
        assert bill["unrounded_lines"]["fuel_reconciliation"]==pytest.approx(-720*power*(.04054 if plan.startswith("Rg") else .03620))
        assert result["rate_assumptions"]==bill["rate_assumptions"]==wi.evidence(idx,a)["rate_assumptions"]


def test_annual_version_boundaries_and_credits_do_not_appear():
    assert service_rates("2025-06-01","Rg1")["environmental_control"]==.00055
    assert service_rates("2026-01-01","Rg1")["environmental_control"]==.00052
    assert service_rates("2026-01-01","Rg1")["energy"]==(.19342,.19342)
    assert service_rates("2026-06-01","Cg6")["environmental_control"]==.00048
    a,idx=fixture()
    with pytest.raises(ValueError,match="carried"):wi.validate_state(a,idx,state={"credit":5.})


def test_full_2025_study_rejects_unverified_ecc_instead_of_extrapolating():
    from src.local_web.regional_study import calendar_cycles, defaults, prepare
    q=defaults(wi.UTILITY,"residential","Rg1")
    q.update(start_date="2025-01-01",end_date="2025-12-31")
    q["account"]=wi.hypothetical_defaults("Rg1")
    q["billing_cycles"]=calendar_cycles(q["start_date"],q["end_date"])
    q["load"]["native_basis_confirmed"]=True
    q["solar"]["dc_capacity_kw"]=0.; q["pv_capacity_kw"]=0.; q["battery"]=None
    with pytest.raises(ValueError,match="coverage|ECC|environmental"):
        prepare(q)


@pytest.mark.parametrize("mode,accepted",[("verified",False),("verified",True),
    ("provisional_2025",False),("provisional_2025",1),("provisional_2025","true"),
    ("provisional_2025",None),("approximate",True)])
def test_gap_needs_selected_mode_and_strict_boolean_consent(mode,accepted):
    a,idx=fixture(month="2025-07")
    a.update(rate_evidence_mode=mode,provisional_assumptions_accepted=accepted)
    with pytest.raises(ValueError):
        calculate_cycle(wi.UTILITY,idx,np.ones(len(idx)),np.zeros(len(idx)),a)
    with pytest.raises(ValueError):wi.evidence(idx,a)


@pytest.mark.parametrize("plan",wi.PLANS)
@pytest.mark.parametrize("month",["2025-01","2025-06","2026-01","2026-06","2026-09"])
def test_provisional_selection_preserves_every_verified_bill(plan,month):
    a,idx=fixture(plan,month)
    # Irregular deterministic power checks the same TOU dot products rather
    # than only a total kWh identity at a constant load.
    power=.5+np.arange(len(idx))%11/10
    expected=calculate_cycle(wi.UTILITY,idx,power,np.zeros(len(idx)),a)
    a.update(rate_evidence_mode="provisional_2025",provisional_assumptions_accepted=True)
    bill=calculate_cycle(wi.UTILITY,idx,power,np.zeros(len(idx)),a)
    assert bill["unrounded_lines"]==expected["unrounded_lines"]
    assert bill["rate_evidence_status"]=="verified"
    assert bill["rate_assumptions"]==[] and bill["assumption_model"] is None
    assert bill["objective_scope"]=="complete_utility_bill"
    assert bill["metrics"]["provisional_ecc_applied"] is False
    assert not any("Provisional historical estimate" in text for text in bill["warnings"])


@pytest.mark.parametrize("plan",wi.PLANS)
def test_annual_preparation_is_explicitly_provisional_in_six_cycles_only(plan):
    from src.billing.regional import cycle_account,cycle_partitions
    from src.local_web.regional_study import calendar_cycles,defaults,prepare
    kind="residential" if plan.startswith("Rg") else "commercial"
    q=defaults(wi.UTILITY,kind,plan)
    q.update(start_date="2025-01-01",end_date="2025-12-31")
    q["account"].update(rate_evidence_mode="provisional_2025",provisional_assumptions_accepted=True)
    q["billing_cycles"]=calendar_cycles(q["start_date"],q["end_date"])
    q["load"]["native_basis_confirmed"]=True
    q["solar"]["dc_capacity_kw"]=0.;q["pv_capacity_kw"]=0.;q["battery"]=None
    prepare(q)
    idx=build_interval_index("2025-01-01","2025-12-31",wi.TIMEZONE,15).index
    assert len(idx)==35040
    metadata=[wi.evidence(idx[block],cycle_account(q["account"],cycle))
              for _,block,cycle in cycle_partitions(idx,q["billing_cycles"])]
    assert [m["rate_evidence_status"] for m in metadata]==["verified"]*6+["provisional"]*6
    assert all(m["assumption_model"]=="we_energies_wi_2025_provisional_v1" for m in metadata[6:])
    assert wi.evidence(idx,q["account"])["rate_assumptions"]==metadata[6]["rate_assumptions"]


@pytest.mark.parametrize("day",["2024-12-31","2026-10-01","2026-12-01","2027-01-01"])
def test_provisional_opt_in_never_extrapolates_outside_declared_gap(day):
    with pytest.raises(ValueError,match="coverage"):
        service_rates(day,"Rg1",mode="provisional_2025")


@pytest.mark.parametrize("plan,expected",[("Rg1",.00055),("Rg2",.00055),("Cg1",.00050),("Cg6",.00050)])
def test_proxy_dates_assumption_provenance_and_dependent_components(plan,expected):
    from src.billing.regional import bill_scope
    a,idx=fixture(plan,"2025-12")
    a.update(rate_evidence_mode="provisional_2025",provisional_assumptions_accepted=True)
    bill=calculate_cycle(wi.UTILITY,idx,np.ones(len(idx)),np.zeros(len(idx)),a)
    assert bill_scope(bill)=="provisional_modeled_bill"
    assert bill["is_complete_bill"] and bill["objective_scope"]=="provisional_modeled_bill"
    assert bill["metrics"]["environmental_control_usd_per_kwh"]==expected
    assert expected!=service_rates("2026-01-01",plan)["environmental_control"]
    assert bill["unrounded_lines"]["environmental_control"]==pytest.approx(744*expected)
    assumption=bill["rate_assumptions"][0]
    assert assumption["id"]=="WE25-ECC-JUNE-CARRY-FORWARD"
    assert (assumption["start"],assumption["end"])==("2025-07-01","2025-12-31")
    assert set(assumption["components"])=={"environmental_control","state_low_income_assistance","wisconsin_sales_tax"}
    assert assumption["sources"]==["https://s22.q4cdn.com/994559668/files/doc_downloads/2025/June-2025-Monthly-Servicers-Certificate.pdf"]
    assert assumption["assumed_values"]["reference_service_month"]=="2025-06"
    assert any("Provisional historical estimate" in text for text in bill["warnings"])
    assert "not verified" in bill["metrics"]["rider_versions"]["environmental_control"]["reference"]
    # A caller may edit its returned record, but never mutate later evidence.
    assumption["sources"].clear()
    assert wi.evidence(idx,a)["rate_assumptions"][0]["sources"]


def test_gap_fall_dst_retains_local_day_fee_and_holiday_hour_allocation():
    a,idx=fixture("Rg2","2025-11")
    a.update(rate_evidence_mode="provisional_2025",provisional_assumptions_accepted=True)
    bill=calculate_cycle(wi.UTILITY,idx,np.ones(len(idx)),np.zeros(len(idx)),a)
    assert bill["import_kwh"]==721
    assert bill["metrics"]["elapsed_hours"]==721 and bill["metrics"]["cycle_days"]==30
    assert bill["unrounded_lines"]["customer"]==pytest.approx(30*.49315)
    # November has twenty weekdays, with Thanksgiving removed; Friday28 is
    # ordinary peak. The repeated Sunday01:00 interval is entirely off peak.
    assert bill["unrounded_lines"]["energy"]==pytest.approx(19*12*.27006+(721-19*12)*.10387)
    assert bill["unrounded_lines"]["wisconsin_sales_tax"]==0.


def test_catalog_gap_scope_and_all_default_accounts_require_opt_in():
    for plan in wi.catalog():
        assert plan["provisional_coverage"]==[{"start":"2025-07-01","end":"2025-12-31"}]
        for account in (wi.defaults(plan["id"]),wi.hypothetical_defaults(plan["id"])):
            assert account["rate_evidence_mode"]=="verified"
            assert account["provisional_assumptions_accepted"] is False
        assert plan["provisional_assumptions"][0]["id"]=="WE25-ECC-JUNE-CARRY-FORWARD"
    catalog=wi.catalog();catalog[0]["provisional_assumptions"][0]["sources"].clear()
    assert wi.catalog()[0]["provisional_assumptions"][0]["sources"]


def test_utility_sample_bill_independent_components_without_enabling_shifted_cycles():
    # Official example: Feb3,2026 bill; Jan5–Feb2;29days;669kWh;148.53USD.
    # A shifted billing cycle remains unsupported. Compare flat-rate energy,
    # fuel, ECC and the29-day customer arithmetic separately; this is not an
    # assertion that the complete published cycle was executed by this model.
    a,idx=fixture("Rg1","2026-02")
    bill=calculate_cycle(wi.UTILITY,idx,np.full(len(idx),669/672),np.zeros(len(idx)),a)
    assert bill["lines"]["energy"]==129.40
    assert bill["lines"]["fuel"]==1.33
    assert bill["lines"]["environmental_control"]==.35
    assert bill["lines"]["state_low_income_assistance"]==3.15
    assert bill["lines"]["wisconsin_sales_tax"]==0.
    assert round(29*.49315,2)==14.30
    assert round(bill["unrounded_total_usd"]+.49315,2)==148.53
    shifted=build_interval_index("2026-01-05","2026-02-02",wi.TIMEZONE,15).index
    a.update(billing_month="2026-01-05",bill_date="2026-02-03")
    with pytest.raises(ValueError,match="complete calendar"):
        wi.validate_account(a,shifted)


def test_fall_dst_calendar_is_25_hours_even_when_rate_cycle_is_unsupported():
    idx=build_interval_index("2025-11-02","2025-11-02",wi.TIMEZONE,15).index
    assert len(idx)==100 and not wi.periods(idx,"Rg2")["peak"].any()


@pytest.mark.parametrize("start",[7,8,10])
def test_rg2_nondefault_window_survives_flat_plan_comparison_without_repricing_it(start):
    from src.local_web.regional_study import defaults, prepare
    q=defaults(wi.UTILITY,"residential","Rg2")
    q["account"]["on_peak_start_hour"]=start
    q["tariff_comparisons"]=["Rg1"]
    q["load"]["native_basis_confirmed"]=True
    q["solar"]["dc_capacity_kw"]=0.;q["pv_capacity_kw"]=0.;q["battery"]=None
    prepare(q)
    a,idx=fixture("Rg1");a["on_peak_start_hour"]=start
    bill=calculate_cycle(wi.UTILITY,idx,np.ones(len(idx)),np.zeros(len(idx)),a)
    assert bill["unrounded_lines"]["energy"]==pytest.approx(744*.19342)
    assert bill["metrics"]["on_peak_start_hour"] is None
