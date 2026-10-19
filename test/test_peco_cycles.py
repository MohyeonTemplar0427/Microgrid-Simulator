"""Cycle-rule evidence boundaries; no invented PECO proration formula."""
import numpy as np
import pandas as pd
import pytest

from src.billing import peco
from src.billing.regional import calculate_cycle
from src.local_web.regional_study import prepare
from src.timeseries import build_interval_index
from test_peco import account
from test_regional_study import browser_request
from src.local_web.regional_study import defaults
from test_local_web import service, wait_for_study


def cycle(plan, start, end, kind="regular", bill_date=None):
    a = peco.hypothetical_defaults(plan)
    a.update(cycle_kind=kind, bill_date=bill_date or end)
    return a, build_interval_index(start, end, peco.TIMEZONE, 15).index


@pytest.mark.parametrize("plan", peco.PLANS)
@pytest.mark.parametrize("start,end,components", [
    ("2025-02-15", "2025-03-16", {"generation"}),
    ("2025-05-15", "2025-06-14", {"generation", "tsc", "nbt", "eepc"}),
    ("2025-11-15", "2025-12-14", {"generation", "tsc", "nbt"}),
    ("2025-12-20", "2026-01-18", {"stas", "icus", "fars"}),
    ("2026-05-15", "2026-06-14", {"generation", "tsc", "nbt", "eepc"}),
])
def test_component_specific_crossing_diagnostics(plan, start, end, components):
    a, idx = cycle(plan, start, end)
    r = peco.cycle_review(a, idx)
    assert not r["cycle_supported"]
    expected = components-{"generation"} | ({"tou_generation" if plan.endswith("TOU") else "generation"}
                                         if "generation" in components else set())
    assert expected <= set(r["rate_changes"][0]["components"])
    assert r["rate_changes"][0]["phase"] == "service"
    with pytest.raises(ValueError, match="verified allocation"):
        calculate_cycle("peco", idx, np.ones(len(idx)), np.zeros(len(idx)), a)


@pytest.mark.parametrize("plan", ["R", "GS"])
@pytest.mark.parametrize("days,kind", [(1,"initial"), (25,"regular"), (25,"final"),
                                      (25,"initial"), (36,"final"), (36,"regular")])
def test_partial_and_nonregular_cycles_need_unverified_determinants(plan, days, kind):
    end = str((pd.Timestamp("2025-07-01")+pd.Timedelta(days=days-1)).date())
    a, idx = cycle(plan, "2025-07-01", end, kind)
    r = peco.cycle_review(a, idx)
    assert r["cycle_days"] == days
    assert r["issues"][0]["code"] == "unverified_partial_allocation"
    assert not r["rules"]["partial_period_formula_verified"]
    with pytest.raises(ValueError, match="No 30-day denominator"):
        peco.validate_account(a, idx)


@pytest.mark.parametrize("plan", peco.PLANS)
@pytest.mark.parametrize("days", [26, 35])
@pytest.mark.parametrize("kind", ["regular", "initial", "final"])
def test_cycle_boundaries_use_one_monthly_charge_despite_fall_dst(plan, days, kind):
    end = str((pd.Timestamp("2025-10-20")+pd.Timedelta(days=days-1)).date())
    a, idx = cycle(plan, "2025-10-20", end, kind)
    r = peco.cycle_review(a, idx)
    assert r["cycle_supported"] and r["cycle_days"] == days
    assert r["elapsed_hours"] == 24*days+1
    power = np.full(len(idx), 1. if plan.startswith("R") else 10.)
    b = calculate_cycle("peco", idx, power, power*0, a)
    assert b["import_kwh"] == pytest.approx(power[0]*(24*days+1))
    assert b["unrounded_lines"]["distribution_customer"] == (11.30 if plan.startswith("R") else 74.66)
    assert b["metrics"]["monthly_charge_factor"] == 1
    assert b["metrics"]["cycle_days"] == days
    assert b["metrics"]["partial_period_proration_applied"] is False


@pytest.mark.parametrize("plan", ["GS", "GS-TOU"])
@pytest.mark.parametrize("start,end,dsic", [("2026-03-20","2026-04-18",.0011),
                                         ("2026-06-20","2026-07-19",.0042),
                                         ("2026-09-20","2026-10-19",.0105)])
def test_gs_dsic_crossings_preserve_single_nonflat_cycle_peak(plan, start, end, dsic):
    a, idx = cycle(plan, start, end)
    power = np.full(len(idx), 10.)
    power[:2] = 20.24  # old-rate portion's 30-minute peak, rounds to 20.2
    power[-2:] = 15.0
    assert peco.cycle_review(a, idx)["cycle_supported"]
    b = calculate_cycle("peco", idx, power, power*0, a)
    m = b["metrics"]
    assert m["billing_demand_kw"] == 20.2
    assert m["dsic_fraction"] == dsic
    assert b["unrounded_lines"]["distribution_demand"] == pytest.approx(20.2*m["all_in_distribution_usd_per_kw"])
    d = sum(v for k,v in b["unrounded_lines"].items()
            if k.startswith("distribution_") and k!="distribution_dsic")+b["unrounded_lines"]["energy_efficiency"]
    assert b["unrounded_lines"]["distribution_dsic"] == pytest.approx(d*.9996*dsic)


def test_transient_rate_change_cannot_hide_behind_equal_endpoints(monkeypatch):
    original = peco.rates_on
    def transient(day):
        r = original(day)
        if str(day)[:10] == "2025-07-15":
            r["usfc"] += .001
        return r
    monkeypatch.setattr(peco, "rates_on", transient)
    a, idx = account()
    assert peco._applicable_rates(transient(idx[0].date()),"R") == peco._applicable_rates(transient(idx[-1].date()),"R")
    r = peco.cycle_review(a, idx)
    assert [v["date"] for v in r["rate_changes"]] == ["2025-07-15", "2025-07-16"]
    with pytest.raises(ValueError, match="usfc"):
        peco.validate_account(a, idx)


def test_service_change_and_issuance_gap_are_separate():
    a, idx = account("R", 5)
    a["bill_date"] = "2025-06-02"
    r = peco.cycle_review(a, idx)
    assert r["rate_changes"][0]["phase"] == "bill_issuance_gap"
    assert r["rate_changes"][0]["date"] == "2025-06-01"
    a["bill_date"] = "2025-05-30"
    with pytest.raises(ValueError, match="precede service end"):
        peco.cycle_review(a, idx)


@pytest.mark.parametrize("plan", ["R-TOU", "GS-TOU"])
@pytest.mark.parametrize("start,end,kind,detail", [
    ("2026-05-20","2026-06-18","regular","tou_generation"),
    ("2026-07-01","2026-07-10","initial","fixed-charge factor"),
])
def test_browser_preparation_reports_missing_allocation_before_queue(plan, start, end, kind, detail):
    request = defaults("peco", "residential" if plan.startswith("R") else "commercial", plan)
    request.update(start_date=start, end_date=end)
    request["operating_contract"].update(interconnection_confirmed=True,
        reference="Explicit hypothetical approved non-export account")
    request["billing_cycles"] = [dict(start_date=start, end_date=end, billing_month=start[:7]+"-01",
        bill_date=end, kind=kind, source="Explicit hypothetical unsupported cycle test", account_overrides={})]
    with pytest.raises(ValueError, match=detail):
        prepare(browser_request(request))


def test_time_unit_does_not_change_cycle_support_and_missing_interval_rejects():
    a, idx = account()
    assert peco.cycle_review(a, idx.as_unit("us")) == peco.cycle_review(a, idx)
    with pytest.raises(ValueError, match="consecutive"):
        peco.cycle_review(a, idx.delete(10))


@pytest.mark.parametrize("plan,kind,cycle_kind", [("R-TOU","residential","initial"),
                                                ("GS-TOU","commercial","final")])
def test_initial_final_form_to_worker_all_scenarios(service, plan, kind, cycle_kind):
    app, call, headers = service
    request = defaults("peco", kind, plan)
    request.update(start_date="2025-07-14",end_date="2025-08-12")
    request["operating_contract"].update(interconnection_confirmed=True,grid_charging_confirmed=True,
        reference="Explicit hypothetical approved non-export account")
    request["billing_cycles"] = [dict(start_date=request["start_date"],end_date=request["end_date"],
        billing_month="2025-08-01",bill_date="2025-08-14",kind=cycle_kind,
        source="Explicit hypothetical complete30-day "+cycle_kind+" meter cycle",account_overrides={})]
    serialized = browser_request(request)
    assert serialized["billing_cycles"][0]["kind"] == cycle_kind
    study = call("/api/v1/regional/studies", serialized, headers)
    out = wait_for_study(call, study["id"])
    assert out["status"] == "completed", out.get("error")
    assert out["result"]["engine_id"] == app.engine["id"]
    assert out["result"]["ac_validation"]["all_intervals_feasible"]
    table = call("/api/studies/"+study["id"]+"/tables/comparison")
    records = [dict(zip(table["columns"],row)) for row in table["data"]]
    assert {r["scenario"] for r in records} == {"grid_only","pv_only","pv_battery"}
    assert all(r["maximum_reconciliation_difference_usd"] < 1e-4 for r in records)
    assert all(r["is_complete_bill"] for r in records)
    csv = call("/api/studies/"+study["id"]+"/tables/billing-cycles.csv")
    assert cycle_kind.encode() in csv and b"monthly_charge_factor" in csv
