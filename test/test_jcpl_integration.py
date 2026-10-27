"""JCP&L form/worker, annual account assignments and saved-artifact contracts."""
from copy import deepcopy
from io import BytesIO
import json
from zipfile import ZipFile

import numpy as np
import pytest

from src.billing.jcpl_nj import history_through, pls_as_of
from src.billing.regional import UTILITIES, account_region, calculate_cycle, cycle_account
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.local_web.regional_study import capabilities, prepare
from tools.run_regional_validation import case_request, checked_bill_scope, selected_cases
from test_local_web import service, wait_for_study
from test_regional_study import browser_request

UTILITY = "jcpl_new_jersey"
CASES = (("residential", "RS"), ("commercial", "GS"))


@pytest.mark.parametrize("kind,plan", CASES)
def test_form_roundtrip_keeps_utility_supplier_jurisdiction_and_pjm_separate(kind, plan):
    entry = capabilities()["utilities"][UTILITY]
    assert (entry["state"], entry["grid_operator"], entry["transmission_zone"]) == ("NJ", "PJM", "JCPL")
    assert UTILITIES[UTILITY]["emergency_region"] == "FE-JC"
    assert (UTILITY, kind, plan) in selected_cases([UTILITY])
    r = case_request(UTILITY, kind, "monthly", plan=plan)
    restored = browser_request(r)
    assert restored["account"] == r["account"]
    assert restored["billing_cycles"] == r["billing_cycles"]
    account_region(restored["regional_account"], UTILITY)
    grid, load, cycles, equipment = prepare(restored)
    assert len(grid.index) == len(load) == 2880 and len(cycles) == 1
    assert equipment["pv_dc_kw"] == r["solar"]["dc_capacity_kw"]
    for key, value in (("state_jurisdiction", "MD"), ("retail_supplier", "competitive_supplier"),
                       ("transmission_zone", "AECO")):
        bad = deepcopy(restored); bad["regional_account"][key] = value
        with pytest.raises(ValueError):
            prepare(bad)


@pytest.mark.parametrize("kind,plan", CASES)
def test_annual_driver_preserves_full_2025_dates_and_explicit_november_pls(kind, plan):
    r = browser_request(case_request(UTILITY, kind, "annual", plan=plan))
    grid, load, cycles, equipment = prepare(r)
    assert len(grid.index) == len(load) == 35040 and len(cycles) == 12
    assert grid.index[0].isoformat() == "2025-01-01T00:00:00-05:00"
    assert grid.index[-1].isoformat() == "2025-12-31T23:45:00-05:00"
    assert len(grid.index[cycles[2][1]]) == 2972  # spring DST retains every elapsed interval
    assert len(grid.index[cycles[10][1]]) == 2884  # autumn repeated hour remains distinct
    state = None
    for _, block, cycle in cycles:
        a = cycle_account(r["account"], cycle)
        if plan == "GS":
            expected = "2023-11-01" if int(cycle["start_date"][5:7]) < 6 else "2024-11-01"
            assert a["peak_load_share_as_of"] == expected == pls_as_of(cycle["start_date"])
            assert expected in a["pls_source"]
        b = calculate_cycle(UTILITY, grid.index[block], load[block], np.zeros(len(load[block])),
                            a, state=state, equipment=equipment)
        assert checked_bill_scope(b, UTILITY, a, grid.index[block]) == ("complete_utility_bill", [])
        state = b["next_state"]
    if plan == "GS":
        assert state == {"gs_history_peak_upper_bound_kw": 10., "through_month": "2025-12-01"}
        bad = deepcopy(r)
        bad["billing_cycles"][5]["account_overrides"]["peak_load_share_as_of"] = "2023-11-01"
        with pytest.raises(ValueError, match="November PLS"):
            prepare(bad)


@pytest.mark.parametrize("kind,plan", CASES)
def test_grid_counterfactual_removes_only_der_assertions_and_retains_history(kind, plan):
    a = case_request(UTILITY, kind, "monthly", plan=plan)["account"]
    state = {"gs_history_peak_upper_bound_kw": 9., "through_month": "2026-08-01"} if plan == "GS" else {}
    counter = grid_only_counterfactual(UTILITY, a, state=state)
    assert counter["state"] == state
    for key in ("der_ordinary_service_confirmed", "gs_standby_not_applicable_confirmed"):
        assert counter["account"][key] is False
    for key in ("der_activation_date", "der_eligibility_source", "gs_standby_source"):
        assert counter["account"][key] == ""
    for key in ("supply", "contract_demand_kw", "gs_no_demand_meter_confirmed", "gs_minimum_domain_confirmed",
                "prior_11_actual_peak_upper_bound_kw", "prior_history_through_month", "peak_load_share_kw",
                "peak_load_share_as_of", "pls_source", "gs_classification_source", "demand_method"):
        assert counter["account"][key] == a[key]
    assert a["der_ordinary_service_confirmed"] is True  # caller not mutated


@pytest.mark.parametrize("kind,plan", CASES)
def test_queued_worker_bills_proofs_saved_settings_and_csv_zip(service, kind, plan):
    app, call, headers = service
    r = browser_request(case_request(UTILITY, kind, "monthly", plan=plan))
    queued = call("/api/v1/regional/studies", r, headers)
    study = wait_for_study(call, queued["id"])
    assert study["status"] == "completed", study.get("error")
    result = study["result"]
    assert result["engine_id"] == app.engine["id"] and result["is_complete_bill"] is True
    assert set(result["billing"]) == {"grid_only", "pv_only", "pv_battery"}
    for scenario, bills in result["billing"].items():
        assert len(bills) == 1
        b = bills[0]
        assert b["is_complete_bill"] and b["excluded_components"] == [] and b["export_kwh"] < 1e-5
        assert b["rate_evidence_status"] == "verified"
        assert b["total_usd"] == pytest.approx(sum(b["lines"].values()))
        assert b["metrics"]["rounded_cash_optimum_claimed"] is False
        assert b["metrics"]["objective_scope"] == "unrounded_ordinary_component_charges"
        assert result["optimization"][scenario]["annual_optimum_proven"] is None
    assert result["ac_validation"]["all_intervals_feasible"]
    assert all(x["checked_intervals"] == 2880 and x["failed_intervals"] == 0
               for x in result["ac_validation"]["scenarios"])
    base = "/api/studies/"+queued["id"]
    comparison = call(base+"/tables/comparison")
    records = [dict(zip(comparison["columns"], row)) for row in comparison["data"]]
    assert all(row["maximum_reconciliation_difference_usd"] < .0001 for row in records)
    assert b"pv_curtailed_kw" in call(base+"/tables/dispatch-pv_battery.csv")
    with ZipFile(BytesIO(call(base+"/tables.zip"))) as archive:
        assert archive.testzip() is None and json.loads(archive.read("result-manifest.json")) == result
        assert all("ac-"+s+".csv" in archive.namelist() for s in result["billing"])
    call(base+"/save", {"name": "JCP&L "+plan+" targeted acceptance"}, headers)
    saved = call(base+"/request.json")
    assert saved["account"] == r["account"] and saved["regional_account"] == r["regional_account"]
    assert browser_request(saved)["account"] == r["account"]


@pytest.mark.parametrize("kind,plan", CASES)
def test_matrix_audit_rejects_hidden_allocation_rounding_and_scope_changes(kind, plan):
    r = case_request(UTILITY, kind, "monthly", plan=plan)
    grid, load, cycles, equipment = prepare(r)
    _, block, cycle = cycles[0]; a = cycle_account(r["account"], cycle)
    b = calculate_cycle(UTILITY, grid.index[block], load[block], np.zeros(len(load[block])), a, equipment=equipment)
    assert checked_bill_scope(b, UTILITY, a, grid.index[block]) == ("complete_utility_bill", [])
    for key, value in (("is_complete_bill", False), ("rate_evidence_status", "provisional"), ("excluded_components", ["missing"])):
        bad = deepcopy(b); bad[key] = value
        with pytest.raises(AssertionError):
            checked_bill_scope(bad, UTILITY, a, grid.index[block])
    for key, value in (("rounded_cash_optimum_claimed", True), ("quantity_basis", "rounded_quantity_proxy"),
                       ("linear_allocation_basis", "uniform days"), ("additional_tax_percentage_applied", True),
                       ("whole_cycle_block_kwh", 999.), ("monthly_charge_factor", .9)):
        bad = deepcopy(b); bad["metrics"][key] = value
        with pytest.raises(AssertionError):
            checked_bill_scope(bad, UTILITY, a, grid.index[block])
    if plan == "GS":
        bad = deepcopy(b); bad["next_state"]["through_month"] = "2026-07-01"
        with pytest.raises(AssertionError):
            checked_bill_scope(bad, UTILITY, a, grid.index[block])


def test_der_facts_and_initial_history_are_required_through_real_prepare():
    base = case_request(UTILITY, "commercial", "monthly", plan="GS")
    assert base["account"]["prior_history_through_month"] == history_through(base["start_date"])
    for key, value in (("gs_no_demand_meter_confirmed", False), ("gs_minimum_domain_confirmed", False),
                       ("gs_standby_not_applicable_confirmed", False), ("gs_standby_source", ""),
                       ("der_activation_date", "2026-09-02"), ("der_eligibility_source", ""),
                       ("prior_history_through_month", "2026-07-01"), ("peak_load_share_kw", 500.)):
        bad = deepcopy(base); bad["account"][key] = value
        with pytest.raises(ValueError):
            prepare(bad)
