"""Actual utility optimizers/bills followed by independent electrical replay."""
from copy import deepcopy
import json

import numpy as np
import pandas as pd
import pytest

from src.local_web import socal_study, municipal_study
from test_utility_electrical_replay import BATTERY


def socal_request(utility,provider="bundled"):
    from test_socal import study_request,account
    from test_la_county import gwp_account
    from test_pasadena import pwp_account
    from test_la_municipal_expansion import municipal_account
    from test_san_diego import account as sdge_account
    plans={"sce":"sce_tou-d-4-9","ladwp":"ladwp_r-1b","sdge":"sdge_tou-dr1",
           "gwp":"gwp_l-1-b","pwp":"pwp_r-1_flat","bwp":"bwp_ev","alw":"alw_d","ipu":"ipu_d"}
    r=study_request("sce")
    r["tariff_id"]=plans[utility]
    r["resolution"].update(delivery_utility=utility,delivery_candidates=[{"utility_id":utility}])
    a=(gwp_account() if utility=="gwp" else pwp_account() if utility=="pwp" else
       municipal_account(utility) if utility in ("bwp","alw","ipu") else
       sdge_account(provider) if utility=="sdge" else account(utility))
    a.setdefault("actual_generation_provider","bundled")
    if utility=="alw":a["alw_storage_confirmed"]=True
    r.update(account=a,battery=deepcopy(BATTERY),degradation_cost_per_kWh=.01)
    if utility in ("sce","ladwp","sdge"):
        r["solar"]["capacity_kw"]=3.
        a.update(solar_program="approved_non_export",interconnection_confirmed=True)
    return r


@pytest.mark.parametrize("utility,provider",[(u,"bundled") for u in (
    "sce","ladwp","sdge","gwp","pwp","bwp","alw","ipu")]+[("sdge","sdcp"),("sdge","cea")])
def test_socal_actual_bills_and_dispatch_are_unchanged_by_replay(tmp_path,monkeypatch,utility,provider):
    from src.dispatch import socal
    original=socal.optimize;captured={}
    def optimize(*args,**kwargs):
        result=original(*args,**kwargs)
        captured.update(result=result,before=deepcopy(result))
        return result
    monkeypatch.setattr(socal,"optimize",optimize)
    r=socal_request(utility,provider)
    before=deepcopy(r)
    (tmp_path/"engine.json").write_text("{}")
    socal_study.execute(tmp_path,r)
    assert r==before
    raw,prior=captured["result"],captured["before"]
    pd.testing.assert_frame_equal(raw["dispatch"],prior["dispatch"])
    result=json.loads((tmp_path/"result.json").read_text())
    for label,key in (("grid_only","baseline_bill"),("pv_only","solar_bill"),
                      ("pv_storage" if r["solar"]["capacity_kw"] else "battery_storage","bill")):
        if label in result["bills"]:assert result["bills"][label]==prior[key]
    assert result["objective_reconciliation_error"]==prior["objective_gap"]
    assert not any('AC network feasibility are not modeled' in w or 'or AC network feasibility.' in w
                   for w in result['warnings'])
    validation=result["ac_validation"]
    assert validation["status"]=="completed"
    assert {x["scenario"] for x in validation["scenarios"]}==set(result["bills"])
    assert all(s["checked_intervals"]==2976 for s in validation["scenarios"])
    assert validation["network_configuration"]["id"]=="residential_split_phase_v1"
    for s in validation["scenarios"]:
        ac=pd.read_csv(tmp_path/(s["interval_table"]+".csv"))
        assert len(ac)==2976
        assert np.max(abs(ac.scheduled_grid_net_import_kw-(ac.scheduled_grid_import_kw-ac.scheduled_grid_export_kw)))<1e-9
    if r["solar"]["capacity_kw"]:
        pv=pd.read_csv(tmp_path/"ac-pv_only.csv")
        assert pv.scheduled_pv_curtailed_kw.max()>0
        assert pv.scheduled_grid_export_kw.eq(0).all()
        assert pv.pv_actual_kw.max()<=r["solar"]["capacity_kw"]/1.2+1e-6


def municipal_request(utility="amp",commercial=False,primary=False):
    from test_site_profile import municipal_request as initial
    from test_municipal import account,history
    r=initial()
    schedule=("CB-1" if utility=="svp" else "A-2") if commercial else "D-1"
    r["arrangement"].update(delivery_utility=utility,generation_provider=utility,
        tariff_id=f"{utility}_{schedule.lower().replace('-','')}_2026_"+("07_01" if utility=="amp" else "01_01"))
    r["resolution"]["delivery_utility"]=utility
    r["site_profile"]={"site_type":"commercial" if commercial else "residential","subtype":None if commercial else "house"}
    r["account"]=account(schedule)
    r["battery"]=deepcopy(BATTERY)
    r["load"]={"mode":"daily_peak","base_kw":1.,"peak_kw":3.,"peak_start_hour":16,"peak_end_hour":21}
    if utility=="svp":
        if commercial:
            r["account"].update(phase="three",previous_11_month_peaks_kw=history(kw=20))
        else:r["account"].update(time_of_use=True,tou_enrollment_confirmed=True)
    if primary:r["account"].update(voltage="primary_12kv",primary_discount_qualified=True)
    return r


@pytest.mark.parametrize("utility,commercial,large",[(u,c,False) for u in ("amp","svp") for c in (False,True)]+[("svp",True,True)])
def test_amp_svp_preserve_exact_bills_and_start_soc_dispatch(tmp_path,monkeypatch,utility,commercial,large):
    original=municipal_study.optimize_storage;captured={}
    def optimize(*args,**kwargs):
        result=original(*args,**kwargs)
        captured.update(result=result,before=deepcopy(result))
        return result
    monkeypatch.setattr(municipal_study,"optimize_storage",optimize)
    r=municipal_request(utility,commercial)
    if large:
        r['battery'].update(capacity_kWh=100,energy_kWh=50,max_charge_kw=20,max_discharge_kw=20)
        r['load'].update(base_kw=30,peak_kw=60)
        r['account']['previous_11_month_peaks_kw']={k:60. for k in r['account']['previous_11_month_peaks_kw']}
    before=deepcopy(r)
    (tmp_path/"engine.json").write_text("{}")
    municipal_study.execute_study(tmp_path,r)
    assert r==before
    raw,prior=captured["result"],captured["before"]
    pd.testing.assert_frame_equal(raw["dispatch"],prior["dispatch"])
    result=json.loads((tmp_path/"result.json").read_text())
    assert result["bills"]==json.loads(json.dumps({"no_battery":prior["baseline_bill"],"cost_optimal":prior["bill"]}))
    assert result["ac_validation"]["status"]=="completed"
    ac=pd.read_csv(tmp_path/"ac-cost_optimal.csv")
    assert ac.battery_soc_start_kWh.tolist()==pytest.approx(prior["dispatch"].energy_start_kwh.tolist())
    assert ac.battery_soc_end_kWh.tolist()==pytest.approx(prior["dispatch"].energy_end_kwh.tolist())
    assert ac.scheduled_grid_import_kw.tolist()==pytest.approx(prior["dispatch"].grid_import_kw.tolist(),abs=1e-6)
    assert ac.scheduled_pv_available_kw.eq(0).all()
    assert ac.pv_kw.eq(0).all()
    assert len(ac)==2976 and (tmp_path/"ac-no_battery.csv").is_file()


@pytest.mark.parametrize("grid_only",[False,True])
def test_amp_primary_keeps_bill_and_reports_unsupported_network(tmp_path,grid_only):
    r=municipal_request("amp",True,True)
    if grid_only:r.update(grid_only=True,battery=None,degradation_cost_per_kWh=0)
    (tmp_path/"engine.json").write_text("{}")
    municipal_study.execute_study(tmp_path,r)
    result=json.loads((tmp_path/"result.json").read_text())
    assert result["bills"]["no_battery"]["total"]>0
    assert result["ac_validation"]["status"]=="unsupported"
    assert result["ac_validation"]["all_intervals_feasible"] is None
    assert not (tmp_path/"ac-no_battery.csv").exists()
    rows=pd.read_csv(tmp_path/"comparison.csv")
    assert rows.all_intervals_feasible.isna().all()


def test_socal_completed_calculation_can_be_electrically_infeasible(tmp_path,monkeypatch):
    from src.dispatch import socal
    captured={};original=socal.optimize
    def optimize(*args,**kwargs):
        result=original(*args,**kwargs);captured.update(before=deepcopy(result));return result
    monkeypatch.setattr(socal,"optimize",optimize)
    r=socal_request("ladwp")
    r.update(battery=None,solar={"capacity_kw":0.,"tilt":20.,"azimuth":180.})
    r["account"]["solar_program"]="none"
    r.update(start_date="2026-07-06",end_date="2026-07-06")
    r["account"]["billing_month_factor"]=1/30
    r["load"].update(base_kw=60.,peak_kw=60.)
    (tmp_path/"engine.json").write_text("{}")
    socal_study.execute(tmp_path,r)
    result=json.loads((tmp_path/"result.json").read_text())
    assert result["bills"]["grid_only"]==captured["before"]["baseline_bill"]
    assert result["ac_validation"]["status"]=="completed"
    assert not result["ac_validation"]["all_intervals_feasible"]
    assert result["ac_validation"]["scenarios"][0]["failed_intervals"]==96
    assert any("failed representative" in w for w in result["warnings"])


@pytest.mark.parametrize("primary",[False,True])
def test_socal_commercial_voltage_selects_reference_or_explicit_unsupported(tmp_path,primary):
    r=socal_request("sce" if not primary else "ladwp")
    r.update(battery=None,site_profile={"site_type":"commercial","subtype":None},
             solar={"capacity_kw":0.,"tilt":20.,"azimuth":180.},
             tariff_id="ladwp_a-2b" if primary else "sce_tou-gs-1-e")
    r["account"].update(customer_class="commercial",phase="three",solar_program="none",
        voltage="ladwp_4.8kv" if primary else "secondary",non_cpp_confirmed=True,
        previous_11_month_peaks_kw=[40.]*11,reactive_charge_exempt_confirmed=True)
    if primary:r["load"].update(base_kw=40.,peak_kw=50.)
    (tmp_path/"engine.json").write_text("{}")
    socal_study.execute(tmp_path,r)
    result=json.loads((tmp_path/"result.json").read_text())
    validation=result["ac_validation"]
    assert result["bills"]["grid_only"]["total"]>0
    if primary:
        assert validation["status"]=="unsupported" and validation["all_intervals_feasible"] is None
    else:
        assert validation["status"]=="completed" and validation["all_intervals_feasible"]
        assert validation["network_configuration"]["id"]=="balanced_three_phase_480v_v1"


@pytest.mark.parametrize("program",["sce_nbt","sce_nem1","sce_nem2","ladwp_nem","bwp_net_billing"])
def test_solar_credit_ledgers_and_optimized_flows_are_not_changed(tmp_path,monkeypatch,program):
    from src.dispatch import socal
    from test_sce_nbt import nbt_account
    from test_sce_nem import nem_account as sce_nem
    from test_ladwp_nem import nem_account as ladwp_nem
    from test_bwp_net_billing import account as bwp_account
    u="sce" if program.startswith("sce_") else "ladwp" if program=="ladwp_nem" else "bwp"
    r=socal_request(u)
    r["solar"]["capacity_kw"]=3.
    if program=="sce_nbt":r.update(tariff_id="sce_tou-d-prime",account=nbt_account())
    elif program.startswith("sce_nem"):
        r.update(tariff_id="sce_tou-d-prime",battery=None,
            account=sce_nem(program[-4:],sce_nem_opening_energy_credit=2.5,billing_month_factor=1.))
    elif program=="ladwp_nem":r.update(tariff_id="ladwp_r-1a",account=ladwp_nem(nem_opening_credit=10.))
    else:r.update(tariff_id="bwp_ev",account=bwp_account(solar_capacity_kw=3.,actual_generation_provider="bundled",
        bwp_first_cycle_confirmed=False,bwp_opening_balance_confirmed=True,bwp_opening_credit=10.,municipal_storage_confirmed=True))
    r["account"].setdefault("actual_generation_provider","bundled")
    original=socal.optimize;captured={}
    def optimize(*args,**kwargs):
        out=original(*args,**kwargs);captured.update(before=deepcopy(out),after=out);return out
    monkeypatch.setattr(socal,"optimize",optimize)
    (tmp_path/"engine.json").write_text("{}")
    socal_study.execute(tmp_path,r)
    result=json.loads((tmp_path/"result.json").read_text())
    prior=captured["before"]
    pd.testing.assert_frame_equal(prior["dispatch"],captured["after"]["dispatch"])
    assert result["bills"]["pv_only"]==prior["solar_bill"]
    assert result["bills"].get("pv_storage",result["bills"]["pv_only"])==prior["bill"]
    assert all(s["checked_intervals"]==2976 for s in result["ac_validation"]["scenarios"])
    assert (tmp_path/"solar_credit_ledger.csv").is_file()
    ac=pd.read_csv(tmp_path/"ac-pv_only.csv")
    assert ac.scheduled_grid_export_kw.max()>0
    assert ac.pv_actual_kw.tolist()==pytest.approx(ac.pv_kw.tolist(),abs=.01)


@pytest.mark.parametrize("start,end,count",[("2025-03-08","2025-03-10",284),("2025-11-01","2025-11-03",292)])
def test_socal_replays_every_dst_interval_without_resampling(tmp_path,start,end,count):
    r=socal_request("ladwp")
    r.update(start_date=start,end_date=end)
    r["account"]["billing_month_factor"]=3/30
    (tmp_path/"engine.json").write_text("{}")
    socal_study.execute(tmp_path,r)
    result=json.loads((tmp_path/"result.json").read_text())
    assert all(s["checked_intervals"]==count for s in result["ac_validation"]["scenarios"])
    a=pd.read_csv(tmp_path/"ac-pv_storage.csv")
    b=pd.read_csv(tmp_path/"dispatch.csv")
    assert pd.to_datetime(a.timestamp,utc=True).equals(pd.to_datetime(b.timestamp,utc=True))
