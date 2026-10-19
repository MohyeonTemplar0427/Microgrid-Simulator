"""Independent provisional arithmetic, scope guards and real saved workflows.

Passing tests verify the declared model, not PECO's unknown allocation policy.
"""
from copy import deepcopy
import io
import json
import zipfile

import numpy as np
import pandas as pd
import pytest

from src.billing import peco
from src.billing.regional import calculate_cycle, bill_scope, cycle_partitions
from src.dispatch.regional import optimize_cycle
from src.local_web.regional_study import defaults
from src.timeseries import build_interval_index
from test_local_web import service, wait_for_study
from test_regional_study import browser_request
from tools.run_regional_validation import audit, checked_bill_scope


def case(plan="R", start="2025-07-01", end="2025-07-12", bill_date=None):
    idx = build_interval_index(start, end, peco.TIMEZONE, 15).index
    a = peco.hypothetical_defaults(plan)
    a.update(rate_evidence_mode="provisional_cycles_v1", provisional_assumptions_accepted=True,
             cycle_kind="initial", bill_date=bill_date or end)
    return a, idx


@pytest.mark.parametrize("plan", peco.PLANS)
@pytest.mark.parametrize("start,end,days,hours", [
    ("2025-03-01", "2025-03-12", 12, 287),
    ("2025-10-25", "2025-11-05", 12, 289),
    ("2025-07-01", "2025-08-05", 36, 864),
    ("2025-07-01", "2025-08-14", 45, 1080),
])
def test_partial_cycle_independent_benchmarks_and_dst(plan, start, end, days, hours):
    a, idx = case(plan, start, end)
    res = plan.startswith("R")
    p = np.full(len(idx), 1. if res else 10.)
    b = calculate_cycle("peco", idx, p, p*0, a)
    factor = days/30
    kwh = hours*p[0]
    # March/July/November2025 all retain these delivery prices. March differs
    # from summer only in supply/TSC/EEPC, independently specified here.
    march = start[5:7] == "03"
    distribution = ((11.29 if march else 11.30)*factor+kwh*.09655 if res else
                    74.66*factor+10*(11.35 if march else 11.34)*factor+kwh*(-.0006+(.00899 if march else .00392)))
    if plan.endswith("TOU"):
        holidays = {"2025-11-27", "2025-11-28", "2025-07-04"}
        prices = ((.27978,.04311,.06122) if march else (.29688,.04899,.07055)) if res else (
                 (.19367,.03790,.05609) if march else (.22645,.04669,.06863))
        gsa = sum(p[0]*.25*(prices[1] if t.hour < 6 else prices[0] if t.weekday() < 5 and 14 <= t.hour < 18 and str(t.date()) not in holidays else prices[2]) for t in idx)
    else:
        gsa = kwh*((.08381 if march else .09508) if res else (.07170 if march else .08651))
    tsc = kwh*(.00858 if march else .00892) if res else 10*factor*(2.13 if march else 2.05)
    expected = (distribution+gsa+tsc)*(1 if res else 1.06)
    assert b["unrounded_total_usd"] == pytest.approx(expected, abs=1e-7)
    assert b["import_kwh"] == pytest.approx(kwh)
    assert b["metrics"]["cycle_days"] == days
    assert b["metrics"]["monthly_charge_factor"] == factor
    assert b["metrics"]["partial_period_proration_applied"]
    assert bill_scope(b) == "provisional_modeled_bill"
    assert b["price_evidence_status"] == "verified" and b["billing_allocation_status"] == "provisional"


@pytest.mark.parametrize("energy,expected_demand", [(0,1.2),(100,100/70),(439,439/70),(440,12.4),(900,12.4)])
def test_partial_gs_scaled_low_usage_rule_one_peak_and_rounding(energy, expected_demand):
    a, idx = case("GS")
    p = np.full(len(idx), max(0., (energy-6.18)/((len(idx)-2)*.25)))
    p[:2] = 12.36 if energy else 0
    b = calculate_cycle("peco", idx, p, p*0, a)
    assert b["metrics"]["billing_demand_kw"] == pytest.approx(expected_demand)
    assert b["metrics"]["gs_low_usage_threshold_kwh"] == 440
    assert b["unrounded_lines"]["distribution_demand"] == pytest.approx(expected_demand*11.34*.4)
    assert b["unrounded_lines"]["transmission"] == pytest.approx(expected_demand*2.05*.4)


@pytest.mark.parametrize("days,factor,status", [(1,1/30,"provisional"),(25,25/30,"provisional"),
    (26,1.,"verified"),(35,1.,"verified"),(36,1.2,"provisional"),(45,1.5,"provisional")])
@pytest.mark.parametrize("plan", ["R","GS"])
def test_factor_boundaries_do_not_normalize_meter_energy(days,factor,status,plan):
    end = str((pd.Timestamp("2025-07-01")+pd.DateOffset(days=days-1)).date())
    a, idx = case(plan,end=end)
    p = np.full(len(idx), 1. if plan == "R" else 10.)
    b = calculate_cycle("peco",idx,p,p*0,a)
    assert b["metrics"]["monthly_charge_factor"] == factor
    assert b["rate_evidence_status"] == status
    assert b["import_kwh"] == days*24*p[0]
    assert b["unrounded_lines"]["distribution_customer"] == pytest.approx((11.30 if plan == "R" else 74.66)*factor)


def test_crossing_delivery_energy_uses_actual_usage_not_average_daily_load():
    a, idx = case("R","2026-06-20","2026-07-19")
    p = np.where(idx.month == 6, 1., 3.)
    b = calculate_cycle("peco",idx,p,p*0,a)
    assert b["unrounded_lines"]["distribution_energy"] == pytest.approx(11*24*.10246+19*24*3*.10236)
    assert b["unrounded_lines"]["distribution_customer"] == pytest.approx(11.29)
    assert b["metrics"]["dsic_fraction"] == .0042


@pytest.mark.parametrize("plan", peco.PLANS)
def test_crossing_supply_whole_cycle_delivery_interval_energy_and_one_demand(plan):
    a, idx = case(plan, "2025-05-20", "2025-06-18", "2025-06-23")
    res = plan.startswith("R")
    p = np.where(idx.month == 5, 1. if res else 10., 2. if res else 5.)
    if not res:
        p[:2] = 20.24
        p[-2:] = 15.
    b = calculate_cycle("peco", idx, p, p*0, a)
    m = b["metrics"]; lines = b["unrounded_lines"]
    before = p[idx.month == 5].sum()*.25; after = p[idx.month == 6].sum()*.25
    assert m["monthly_charge_factor"] == 1
    assert m["supply_rate_date"] == "2025-06-18"
    assert [(s["days"], s["monthly_share"]) for s in m["delivery_rate_segments"]] == [(12,.4),(18,.6)]
    if res:
        assert lines["distribution_customer"] == pytest.approx(11.30)
        assert lines["distribution_energy"] == pytest.approx((before+after)*.09655)
        assert lines["transmission"] == pytest.approx((before+after)*.00892)
    else:
        assert m["billing_demand_kw"] == 20.2
        assert lines["distribution_demand"] == pytest.approx(20.2*(11.35*.4+11.34*.6))
        assert lines["energy_efficiency"] == pytest.approx(before*.00899+after*.00392)
        assert lines["transmission"] == pytest.approx(20.2*2.05)
    if not plan.endswith("TOU"):
        assert lines["generation"] == pytest.approx((before+after)*(.09508 if res else .08651))
    else:
        prices = (.29688,.04899,.07055) if res else (.22645,.04669,.06863)
        rates = [prices[1] if t.hour < 6 else prices[0] if t.weekday() < 5 and str(t.date()) != "2025-05-26" and 14 <= t.hour < 18 else prices[2] for t in idx]
        assert lines["generation"] == pytest.approx(np.dot(p,rates)*.25)
    assert {v["id"] for v in b["rate_assumptions"]} == {"PECO-SUPPLY-END","PECO-DELIVERY-SEGMENTS"}


@pytest.mark.parametrize("plan", ["R", "GS"])
def test_january_stas_and_dsic_tax_order_and_issuance_gap(plan):
    a, idx = case(plan, "2025-12-20", "2026-01-18", "2026-01-22")
    p = np.where(idx.year == 2025, 1. if plan == "R" else 10., 2. if plan == "R" else 5.)
    b = calculate_cycle("peco", idx, p, p*0, a)
    # Only January delivery attracts STAS; fixed/demand use18/30 days.
    jan_energy = p[idx.year == 2026].sum()*.25
    january_dist = (11.30*.6+jan_energy*.10276 if plan == "R" else
                    74.66*.6+10*11.50*.6+jan_energy*(.00392-.0006))
    assert b["unrounded_lines"]["state_tax_adjustment"] == pytest.approx(january_dist*-.0004)
    assert b["metrics"]["stas_fraction"] is None
    a, idx = case(plan, "2026-03-20", "2026-04-10", "2026-04-15")
    p = np.full(len(idx), 1 if plan == "R" else 10.)
    b = calculate_cycle("peco", idx, p, p*0, a)
    l = b["unrounded_lines"]
    if plan == "R":
        assert l["distribution_customer"] == pytest.approx(11.30*12/30+11.29*10/30)
    distribution = sum(v for k,v in l.items() if k.startswith("distribution_") and k != "distribution_dsic")+l.get("energy_efficiency",0)
    assert l["state_tax_adjustment"] == pytest.approx(distribution*-.0004)
    assert l["distribution_dsic"] == pytest.approx(distribution*.9996*.0011)
    assert l["sales_tax"] == pytest.approx(0 if plan == "R" else sum(v for k,v in l.items() if k != "sales_tax")*.06)
    # June rate changes after all service: no new supply price is backdated.
    a, idx = case(plan, "2025-05-01", "2025-05-31", "2025-06-03")
    p = np.full(len(idx), 1 if plan == "R" else 10.)
    b = calculate_cycle("peco", idx, p, p*0, a)
    assert b["unrounded_lines"]["generation"] == pytest.approx(p.sum()*.25*(.08381 if plan == "R" else .07170))
    assert b["rate_evidence_status"] == "provisional"


@pytest.mark.parametrize("changes", [{"rate_evidence_mode":"unknown"},{"provisional_assumptions_accepted":False},{"provisional_assumptions_accepted":1}])
def test_explicit_opt_in_and_exact_boolean_required(changes):
    a, idx = case();a.update(changes)
    with pytest.raises(ValueError, match="explicit mode"):
        calculate_cycle("peco", idx, np.ones(len(idx)), np.zeros(len(idx)), a)


def test_provisional_does_not_bypass_dates_equipment_or_whole_day_guards():
    a, idx = case(end="2025-07-31")
    p = np.ones(len(idx))
    normal = calculate_cycle("peco", idx, p, p*0, a)
    assert normal["rate_evidence_status"] == "verified" and normal["rate_assumptions"] == []
    legacy = {k:v for k,v in a.items() if k not in ("rate_evidence_mode","provisional_assumptions_accepted")}
    assert calculate_cycle("peco", idx, p, p*0, legacy)["lines"] == normal["lines"]
    with pytest.raises(ValueError, match="whole local"):
        peco.validate_account(a, idx[1:])
    with pytest.raises(ValueError, match="coverage"):
        a["bill_date"] = "2026-10-20";peco.validate_account(a,idx)
    a, idx = case(start="2025-07-01",end="2025-08-15")
    with pytest.raises(ValueError, match="1–45"):
        peco.validate_account(a,idx)
    assert peco.defaults()["rate_evidence_mode"] == "verified"


@pytest.mark.parametrize("plan,start,end,power", [
    ("R-TOU","2025-03-04","2025-03-15",1.),
    ("GS","2025-07-01","2025-07-12",.8),
    ("GS-TOU","2025-05-20","2025-06-18",4.),
])
def test_provisional_dispatch_rebills_the_same_model(plan,start,end,power):
    a, idx = case(plan,start,end)
    data = pd.DataFrame(dict(timestamp=idx,native_load_kw=power,
        pv_available_kw=np.maximum(0,np.sin((idx.hour.to_numpy()-6)*np.pi/12))*2))
    battery = defaults("peco","residential" if plan.startswith("R") else "commercial",plan)["battery"]
    out = optimize_cycle(data,"peco",a,battery=battery,terminal_energy=battery["energy_kWh"],grid_charging=True,time_limit=30)
    assert out["cost_optimum_proven"] and out["reconciliation_difference_usd"] < 1e-4
    d = out["dispatch"]
    rebill = calculate_cycle("peco",idx,d.grid_import_kw,d.grid_export_kw,a)
    assert rebill["unrounded_total_usd"] == pytest.approx(out["objective_usd"],abs=1e-4)
    assert rebill["assumption_model"] == peco.ALLOCATION_MODEL


def provisional_request(plan,start,end,kind):
    r = defaults("peco","residential" if plan.startswith("R") else "commercial",plan)
    r.update(start_date=start,end_date=end)
    r["account"].update(rate_evidence_mode="provisional_cycles_v1",provisional_assumptions_accepted=True)
    r["operating_contract"].update(interconnection_confirmed=True,grid_charging_confirmed=True,
        reference="Explicit hypothetical approved non-export account")
    r["billing_cycles"] = [dict(start_date=start,end_date=end,billing_month=start[:7]+"-01",bill_date=end,
        kind=kind,source="Explicit hypothetical provisional allocation validation",account_overrides={})]
    return r


@pytest.mark.parametrize("plan,start,end,kind", [
    ("R-TOU","2025-03-04","2025-03-15","initial"),
    ("GS-TOU","2025-07-01","2025-07-12","final"),
    ("R","2026-06-20","2026-07-19","regular"),
    ("GS-TOU","2025-05-20","2025-06-18","regular"),
])
def test_provisional_form_worker_artifacts_and_save_restore(service,plan,start,end,kind):
    app,call,headers = service
    r = browser_request(provisional_request(plan,start,end,kind))
    study = call("/api/v1/regional/studies",r,headers)
    out = wait_for_study(call,study["id"])
    assert out["status"] == "completed",out.get("error")
    result = out["result"]
    assert result["rate_evidence_status"] == "provisional"
    assert result["ac_validation"]["all_intervals_feasible"]
    assert len(result["ac_validation"]["scenarios"]) == 3
    path = app.store.directory/"runs"/study["id"]
    rows,_,_ = audit(path,r,app.engine["id"])
    assert rows.rate_evidence_status.eq("provisional").all()
    base = "/api/studies/"+study["id"]
    csv = call(base+"/tables/billing-assumptions.csv")
    assumptions = pd.read_csv(io.BytesIO(csv))
    assert set(assumptions.scenario) == {"grid_only","pv_only","pv_battery"}
    assert assumptions.assumption_model.eq(peco.ALLOCATION_MODEL).all()
    with zipfile.ZipFile(io.BytesIO(call(base+"/tables.zip"))) as z:
        assert z.read(next(n for n in z.namelist() if n.endswith("billing-assumptions.csv"))) == csv
    call(base+"/save",{"name":"Provisional PECO acceptance"},headers)
    restored = call(base+"/request.json")
    assert call(base)["saved"] and browser_request(restored)["account"] == r["account"]
    tampered = deepcopy(result["billing"]["grid_only"][0])
    tampered["rate_assumptions"][0]["assumed_values"]["tampered"] = True
    with pytest.raises(AssertionError,match="provenance"):
        checked_bill_scope(tampered,"peco",r["account"],build_interval_index(start,end,peco.TIMEZONE,15).index)


def test_cycle_override_cannot_enable_provisional_without_account_opt_in():
    r = provisional_request("R","2025-07-01","2025-07-12","initial")
    r["billing_cycles"][0]["account_overrides"] = {"rate_evidence_mode":"provisional_cycles_v1"}
    idx = build_interval_index(r["start_date"],r["end_date"],peco.TIMEZONE,15).index
    with pytest.raises(ValueError,match="cannot change enrollment"):
        list(cycle_partitions(idx,r["billing_cycles"]))
