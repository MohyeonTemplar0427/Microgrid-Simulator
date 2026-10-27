"""Targeted ACE form/worker/proof-scope and saved-artifact acceptance."""
from copy import deepcopy
from io import BytesIO
import json
from zipfile import ZipFile

import numpy as np
import pytest

from src.billing.atlantic_city_electric import RAW_OBJECTIVE, objective_inputs, pls_as_of
from src.billing.regional import account_region, calculate_cycle, cycle_account
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.local_web.regional_study import calendar_cycles, capabilities, defaults, prepare
from tools.run_regional_validation import case_request, checked_bill_scope, selected_cases
from test_regional_study import browser_request
from test_local_web import service, wait_for_study

UTILITY = "atlantic_city_electric_new_jersey"
CASES = (("residential", "RS"), ("commercial", "MGS-SECONDARY"))


def request_for(kind, plan, start="2026-09-01", end="2026-09-30", *, grid_only=False):
    r = defaults(UTILITY, kind, plan)
    r.update(start_date=start, end_date=end, billing_cycles=calendar_cycles(start, end))
    if plan != "RS":
        r["account"]["peak_load_share_as_of"] = pls_as_of(start)
    r["operating_contract"].update(interconnection_confirmed=True, grid_charging_confirmed=True,
        reference="Explicit hypothetical written ordinary non-export PV/storage approval")
    if grid_only:
        r["solar"]["dc_capacity_kw"] = 0.; r["pv_capacity_kw"] = 0.; r["battery"] = None
        r["operating_contract"]["grid_charging_confirmed"] = False
    return r


@pytest.mark.parametrize("kind,plan", CASES)
def test_form_roundtrip_independent_utility_supplier_zone_and_counterfactual(kind, plan):
    entry = capabilities()["utilities"][UTILITY]
    assert (entry["state"], entry["grid_operator"], entry["transmission_zone"]) == ("NJ", "PJM", "AECO")
    assert (UTILITY, kind, plan) in selected_cases([UTILITY])
    r = case_request(UTILITY, kind, "monthly", plan=plan)
    restored = browser_request(r)
    assert restored["account"] == r["account"]
    assert restored["billing_cycles"] == r["billing_cycles"]
    account_region(restored["regional_account"], UTILITY)
    grid, load, cycles, _ = prepare(restored)
    assert len(grid.index) == len(load) == 2880 and len(cycles) == 1
    reference = grid_only_counterfactual(UTILITY, r["account"])
    assert reference["account"]["der_ordinary_service_confirmed"] is False
    for key in ("supply", "peak_load_share_kw", "peak_load_share_as_of", "quantity_objective_confirmed", "demand_method"):
        assert reference["account"][key] == r["account"][key]
    for key, value in (("state_jurisdiction", "MD"), ("retail_supplier", "competitive_supplier"), ("transmission_zone", "PSEG")):
        bad = deepcopy(restored); bad["regional_account"][key] = value
        with pytest.raises(ValueError):
            prepare(bad)


@pytest.mark.parametrize("kind,plan,start,end", [
    ("residential", "RS", "2026-09-01", "2026-09-30"),
    ("commercial", "MGS-SECONDARY", "2026-09-01", "2026-09-30"),
    ("commercial", "MGS-SECONDARY", "2025-11-01", "2025-11-30"),
])
def test_queued_worker_real_bills_proxy_proofs_saved_settings_and_csv_zip(service, kind, plan, start, end):
    app, call, headers = service
    historical_grid = plan != "RS" and start.startswith("2025")
    r = browser_request(request_for(kind, plan, start, end, grid_only=historical_grid)); prepare(r)
    queued = call("/api/v1/regional/studies", r, headers)
    study = wait_for_study(call, queued["id"])
    assert study["status"] == "completed", study.get("error")
    result = study["result"]
    assert result["engine_id"] == app.engine["id"] and result["is_complete_bill"] is True
    expected = {"grid_only"} if historical_grid else {"grid_only", "pv_only", "pv_battery"}
    assert set(result["billing"]) == expected
    for scenario, bills in result["billing"].items():
        assert len(bills) == 1
        b = bills[0]
        assert b["is_complete_bill"] and b["excluded_components"] == [] and b["export_kwh"] < 1e-5
        assert b["rate_evidence_status"] == "verified"
        assert b["total_usd"] == pytest.approx(sum(b["lines"].values()))
        assert b["metrics"]["rounded_cash_optimum_claimed"] is False
        if plan != "RS":
            assert b["metrics"]["quantity_basis"] == "filed_nearest_quantities_no_half_ties"
            assert b["metrics"]["optimization_objective_scope"] == RAW_OBJECTIVE
        assert result["optimization"][scenario]["annual_optimum_proven"] is None
    expected_intervals = 2884 if historical_grid else 2880
    assert result["ac_validation"]["all_intervals_feasible"]
    assert all(x["checked_intervals"] == expected_intervals and x["failed_intervals"] == 0
               for x in result["ac_validation"]["scenarios"])
    base = "/api/studies/"+queued["id"]
    with ZipFile(BytesIO(call(base+"/tables.zip"))) as archive:
        assert archive.testzip() is None and json.loads(archive.read("result-manifest.json")) == result
        assert all("ac-"+s+".csv" in archive.namelist() for s in expected)
    call(base+"/save", {"name": "ACE "+plan+" targeted acceptance"}, headers)
    saved = call(base+"/request.json")
    assert saved["account"] == r["account"] and saved["regional_account"] == r["regional_account"]
    assert browser_request(saved)["account"] == r["account"]


@pytest.mark.parametrize("kind,plan", CASES)
def test_matrix_scope_rejects_hidden_rounding_or_complete_cash_optimum_claims(kind, plan):
    r = request_for(kind, plan)
    grid, load, cycles, equipment = prepare(r)
    _, block, cycle = cycles[0]; a = cycle_account(r["account"], cycle)
    bill = calculate_cycle(UTILITY, grid.index[block], load[block], np.zeros(len(load[block])), a, equipment=equipment)
    assert checked_bill_scope(bill, UTILITY, a, grid.index[block]) == ("complete_utility_bill", [])
    for key, value in (("is_complete_bill", False), ("rate_evidence_status", "provisional"), ("excluded_components", ["missing"])):
        bad = deepcopy(bill); bad[key] = value
        with pytest.raises(AssertionError):
            checked_bill_scope(bad, UTILITY, a, grid.index[block])
    for key, value in (("rounded_cash_optimum_claimed", True), ("quantity_basis", "raw_objective_proxy"),
                       ("optimization_objective_scope", "rounded_invoice_minimum"), ("additional_tax_percentage_applied", True)):
        bad = deepcopy(bill); bad["metrics"][key] = value
        with pytest.raises(AssertionError):
            checked_bill_scope(bad, UTILITY, a, grid.index[block])


def test_mgs_final_bill_and_raw_objective_are_separately_reconciled():
    r = request_for("commercial", "MGS-SECONDARY"); grid, _, cycles, equipment = prepare(r)
    a = cycle_account(r["account"], cycles[0][2])
    imports = np.full(len(grid.index), 1.00123); imports[0] = 8.1234
    final = calculate_cycle(UTILITY, grid.index, imports, np.zeros(len(imports)), a, equipment=equipment)
    proxy_account, state = objective_inputs(a)
    proxy = calculate_cycle(UTILITY, grid.index, imports, np.zeros(len(imports)), proxy_account, state=state, equipment=equipment)
    assert final["metrics"]["billed_peak_kw"] == 8.1
    assert proxy["metrics"]["billed_peak_kw"] == pytest.approx(8.1234)
    assert final["unrounded_total_usd"] != pytest.approx(proxy["unrounded_total_usd"])
    assert abs(final["unrounded_total_usd"]-proxy["unrounded_total_usd"]) <= final["metrics"]["quantity_rounding_charge_error_bound_usd"]
    bad = deepcopy(a); bad["raw_objective_proxy"] = True
    with pytest.raises(ValueError, match="rounding cannot be disabled"):
        calculate_cycle(UTILITY, grid.index, imports, np.zeros(len(imports)), bad, equipment=equipment)


@pytest.mark.parametrize("kind,plan", CASES)
def test_unverified_years_proration_and_historical_commercial_der_reject(kind, plan):
    with pytest.raises(ValueError, match="full-year2025"):
        case_request(UTILITY, kind, "annual", plan=plan)
    for start, end in (("2025-01-01", "2025-01-30"), ("2025-09-01", "2025-09-30"),
                       ("2026-06-01", "2026-06-30"), ("2026-09-01", "2026-09-29"),
                       ("2026-10-01", "2026-10-31"), ("2026-11-01", "2026-11-30")):
        with pytest.raises(ValueError):
            prepare(request_for(kind, plan, start, end))
    if plan != "RS":
        with pytest.raises(ValueError, match="MGS2025"):
            prepare(request_for(kind, plan, "2025-06-01", "2025-06-30"))
