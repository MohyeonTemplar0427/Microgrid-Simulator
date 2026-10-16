"""Independent PSE&G acceptance of the shared regional optimizer (offline)."""
from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from src.billing import pseg
from src.dispatch.regional import optimize_cycle
from test_pseg_billing import prices


def sample(plan="RS",*,solar=True,year=2025,month=7,net_metering=False):
    first=pd.Timestamp(year=year,month=month,day=1,tz=pseg.TIMEZONE)
    idx=pd.date_range(first,first+pd.DateOffset(days=2),freq="15min",inclusive="left")
    commercial=plan in pseg.COMMERCIAL
    load=np.where((idx.hour>=16)&(idx.hour<21),25. if commercial else 4.,12. if commercial else 1.)
    pv=np.maximum(0,np.sin((idx.hour.to_numpy()+idx.minute.to_numpy()/60-6)*np.pi/12))*(8. if commercial else 6.) if solar else np.zeros(len(idx))
    data=pd.DataFrame({"timestamp":idx,"native_load_kw":load,"pv_available_kw":pv})
    account=pseg.hypothetical_defaults(plan,year)
    account.update(billing_month=f"{year}-{month:02}-01",bill_date=f"{year}-{month:02}-02",
        cycle_kind="initial",proration_denominator_days=31,
        **pseg.hypothetical_obligation_overrides(plan,f"{year}-{month:02}-01"))
    if net_metering:
        account.update(export_mode="net_metering",net_metering_confirmed=True,net_metering_size_confirmed=True)
    battery={"capacity_kWh":12. if commercial else 8.,"energy_kWh":6. if commercial else 4.,
        "SOC_min":.1,"SOC_max":.9,"max_charge_kw":5. if commercial else 2.,
        "max_discharge_kw":5. if commercial else 2.,"charge_efficiency":.95,"discharge_efficiency":.95}
    equipment={"pv":solar,"battery":True,"pv_ac_kw":8. if commercial and solar else 6. if solar else 0.,"battery_kw":battery["max_discharge_kw"]}
    return data,account,battery,equipment


def verify_physics(result,inputs,battery):
    d=result["dispatch"];dt=.25
    np.testing.assert_allclose(d.grid_import_kw+d.pv_output_kw+d.battery_discharge_kw,
        d.native_load_kw+d.battery_charge_kw+d.grid_export_kw,atol=1e-5)
    np.testing.assert_allclose(d.pv_output_kw+d.pv_curtailed_kw,d.pv_available_kw,atol=1e-5)
    assert np.max(np.minimum(d.grid_import_kw,d.grid_export_kw))<=1e-5
    assert np.max(np.minimum(d.battery_charge_kw,d.battery_discharge_kw))<=1e-5
    if battery:
        start=d.energy_kWh.to_numpy();end=start+dt*(d.battery_charge_kw.to_numpy()*.95-d.battery_discharge_kw.to_numpy()/.95)
        assert start[0]==pytest.approx(battery["energy_kWh"],abs=1e-5)
        np.testing.assert_allclose(start[1:],end[:-1],atol=1e-5)
        assert end[-1]==pytest.approx(battery["energy_kWh"],abs=1e-5)
        assert min(start.min(),end.min())>=battery["capacity_kWh"]*.1-1e-5
        assert max(start.max(),end.max())<=battery["capacity_kWh"]*.9+1e-5
        assert d.battery_charge_kw.max()<=battery["max_charge_kw"]+1e-5
        assert d.battery_discharge_kw.max()<=battery["max_discharge_kw"]+1e-5
    assert result["cost_optimum_proven"] is True
    assert result["reconciliation_difference_usd"]<1e-4
    assert result["recalculated_objective_usd"]==pytest.approx(result["objective_usd"],abs=1e-4)


@pytest.mark.parametrize("plan,year,month",[("RS",2025,7),("RHS",2025,1),("RS_TOU_3P",2026,7),("GLP",2025,7),("GLP_NIGHT",2025,7),("LPL_S",2025,7)])
def test_variable_power_cost_optimum_physics_and_authoritative_bill(plan,year,month):
    data,a,b,equipment=sample(plan,year=year,month=month)
    before=(data.copy(deep=True),deepcopy(a),deepcopy(b))
    result=optimize_cycle(data,"pseg",a,b,equipment=equipment,terminal_energy=b["energy_kWh"],time_limit=20)
    verify_physics(result,data,b)
    replay=pseg.bill(pd.DatetimeIndex(data.timestamp),result["dispatch"].grid_import_kw,result["dispatch"].grid_export_kw,a)
    assert replay["total_usd"]==pytest.approx(result["recalculated_objective_usd"],abs=1e-5)
    pd.testing.assert_frame_equal(data,before[0]);assert a==before[1];assert b==before[2]
    if plan in pseg.COMMERCIAL:
        assert result["bill"]["unrounded_lines"]["supply_capacity"]==pytest.approx(a["generation_obligation_kw"]*pseg.version_on(a["bill_date"])[0]["rates"]["rscp"]["GLP" if plan=="GLP_NIGHT" else plan]["capacity"]*2/31)


def test_new_export_credits_change_cash_billing_and_are_optimized():
    data,a,b,equipment=sample("RS_TOU_3P",year=2026,net_metering=True)
    result=optimize_cycle(data,"pseg",a,b,export_enabled=True,equipment=equipment,
        terminal_energy=b["energy_kWh"],time_limit=20)
    verify_physics(result,data,b)
    assert result["dispatch"].grid_export_kw.sum()>0
    assert result["bill"]["metrics"]["export_kwh"]>0
    assert result["credit_objective_policy"]=="exclude_opening_credits"


def test_opening_credit_policy_preserves_operating_schedule_and_history():
    data,a,b,equipment=sample("RS_TOU_3P",year=2026,net_metering=True)
    aa=deepcopy(a);aa["opening_credit_kwh"]={"on_peak":50.,"mid_peak":50.,"off_peak":50.}
    kwargs=dict(export_enabled=True,equipment=equipment,terminal_energy=b["energy_kWh"],time_limit=20)
    no_bank=optimize_cycle(data,"pseg",a,b,**kwargs)
    with_bank=optimize_cycle(data,"pseg",aa,b,**kwargs)
    for key in ("grid_import_kw","grid_export_kw","battery_charge_kw","battery_discharge_kw","energy_kWh"):
        np.testing.assert_allclose(no_bank["dispatch"][key],with_bank["dispatch"][key],atol=1e-5)
    assert no_bank["objective_usd"]==pytest.approx(with_bank["objective_usd"],abs=1e-5)
    assert with_bank["bill"]["total_usd"]<=no_bank["bill"]["total_usd"]
    assert with_bank["optimization_bill"]["unrounded_total_usd"]==pytest.approx(no_bank["optimization_bill"]["unrounded_total_usd"])


def test_explicit_cash_bill_policy_is_separate_and_can_change_cycling():
    data,a,b,equipment=sample("RS_TOU_3P",year=2026,net_metering=True)
    a["opening_credit_kwh"]={"on_peak":100.,"mid_peak":100.,"off_peak":100.}
    kwargs=dict(export_enabled=True,equipment=equipment,terminal_energy=b["energy_kWh"],time_limit=20)
    ordinary=optimize_cycle(data,"pseg",a,b,**kwargs)
    cash=optimize_cycle(data,"pseg",a,b,credit_objective_policy="explicit_cash_bill",**kwargs)
    assert cash["recalculated_objective_usd"]==pytest.approx(cash["bill"]["unrounded_total_usd"],abs=1e-5)
    assert cash["credit_objective_policy"]=="explicit_cash_bill"
    assert cash["dispatch"].battery_charge_kw.sum()<1e-4
    assert ordinary["dispatch"].battery_charge_kw.sum()>1


def test_grid_only_retains_same_opening_credit_objective_basis():
    data,a,_,equipment=sample("RS",solar=False,net_metering=True)
    a["opening_credit_kwh"]={"all":200.};equipment.update(battery=False,battery_kw=0.)
    result=optimize_cycle(data,"pseg",a,None,equipment=equipment)
    assert result["credit_objective_policy"]=="exclude_opening_credits"
    assert result["optimization_bill"]["unrounded_total_usd"]>result["bill"]["unrounded_total_usd"]
    assert result["objective_usd"]==result["optimization_bill"]["unrounded_total_usd"]
    assert np.max(result["dispatch"].battery_charge_kw)==0


def test_pv_only_preserves_curtailment_and_absent_battery_fields():
    data,a,_,equipment=sample("RS")
    equipment.update(battery=False,battery_kw=0.)
    result=optimize_cycle(data,"pseg",a,None,equipment=equipment,time_limit=20)
    verify_physics(result,data,None)
    assert result["dispatch"].pv_curtailed_kw.sum()>1
    assert result["dispatch"].grid_export_kw.sum()==pytest.approx(0,abs=1e-5)
    assert result["dispatch"].energy_kWh.sum()==0


def test_true_up_without_payout_requires_zero_bank_instead_of_guessing():
    data,a,b,equipment=sample("RS",net_metering=True)
    data["pv_available_kw"]*=.1  # net-import cycle can clear its energy bank.
    a["anniversary_true_up"]=True
    result=optimize_cycle(data,"pseg",a,b,export_enabled=True,equipment=equipment,
        terminal_energy=b["energy_kWh"],time_limit=20)
    verify_physics(result,data,b)
    assert result["bill"]["next_state"]["credit_kwh"]=={"all":0.}
    assert result["bill"]["unrounded_lines"]["net_metering_annual_payout"]==0


def test_hourly_ciep_negative_prices_keep_exclusivity_and_reconcile():
    data,a,b,equipment=sample("GLP",solar=False)
    a.update(supply="bgs_ciep",obligation_enrollment_confirmed=True)
    with pytest.raises(ValueError,match="market_data"):
        optimize_cycle(data,"pseg",a,b,equipment=equipment,terminal_energy=b["energy_kWh"])
    hours=pd.DatetimeIndex(data.timestamp).tz_convert("UTC").floor("h").unique()
    # A bounded stress event avoids the all-negative-flat-price symmetries of
    # an unrestricted full-cycle loss-cycling stress problem.
    a["market_data"]=prices(pd.DatetimeIndex(data.timestamp),value=np.where(hours.hour<6,-1000.,50.))
    result=optimize_cycle(data,"pseg",a,b,grid_charging=True,equipment=equipment,
        terminal_energy=b["energy_kWh"],time_limit=20)
    verify_physics(result,data,b)
    assert result["bill"]["unrounded_lines"]["supply_hourly_energy"]<0
    assert result["bill"]["unrounded_lines"]["supply_capacity"]>0
    assert result["bill"]["unrounded_lines"]["supply_transmission"]>0
    assert result["dispatch"].battery_charge_kw.sum()>0
    # Any rewarded losses must come from actual exclusive, SOC-consistent
    # time-separated cycling, never simultaneous charging and discharging.
    assert np.max(np.minimum(result["dispatch"].battery_charge_kw,result["dispatch"].battery_discharge_kw))<1e-5


def test_rolling_history_der_classification_is_validated_before_solve():
    data,a,b,equipment=sample("GLP")
    state={"history_peaks_kw":[20.]*11,"credit_kwh":{}}
    with pytest.raises(ValueError,match="cannot be frozen"):
        optimize_cycle(data,"pseg",a,b,state=state,equipment=equipment,
            terminal_energy=b["energy_kWh"],time_limit=20)


def test_stored_energy_wear_is_distinct_from_utility_bill():
    data,a,b,equipment=sample("GLP")
    result=optimize_cycle(data,"pseg",a,b,wear=.03,include_wear=True,
        equipment=equipment,terminal_energy=b["energy_kWh"],time_limit=20)
    verify_physics(result,data,b)
    assert result["recalculated_objective_usd"]==pytest.approx(result["optimization_bill"]["unrounded_total_usd"]+result["wear_usd"],abs=1e-5)
