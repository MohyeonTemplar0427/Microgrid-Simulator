"""Pepco Maryland local form/worker/artifact contracts and explicit scope gaps."""
from copy import deepcopy
from io import BytesIO
import json
from zipfile import ZipFile

import numpy as np
import pytest

from src.billing.regional import account_region, calculate_cycle, cycle_account
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.billing.pepco_md import excluded_components
from src.local_web.regional_study import calendar_cycles, capabilities, defaults, prepare
from tools.run_regional_validation import case_request, checked_bill_scope, selected_cases
from test_local_web import service, wait_for_study
from test_regional_study import browser_request

CASES = (("residential", "R"), ("commercial", "GS"))


def request_for(kind, plan, start="2026-09-01", end="2026-09-30"):
    r = defaults("pepco_maryland", kind, plan)
    r.update(start_date=start, end_date=end, billing_cycles=calendar_cycles(start, end))
    r["operating_contract"].update(interconnection_confirmed=True, grid_charging_confirmed=True,
        reference="Explicit hypothetical approved ordinary non-export PV/storage installation")
    return r


@pytest.mark.parametrize("kind,plan", CASES)
@pytest.mark.parametrize("start,end,intervals,cycle_count", [
    ("2025-01-01", "2025-02-28", 5664, 2),
    ("2026-07-01", "2026-09-30", 8832, 3),
])
def test_form_roundtrip_preserves_supported_windows_and_independent_account_facts(kind, plan, start, end, intervals, cycle_count):
    entry = capabilities()["utilities"]["pepco_maryland"]
    assert (entry["state"], entry["grid_operator"], entry["transmission_zone"]) == ("MD", "PJM", "PEPCO")
    assert ("pepco_maryland", kind, plan) in selected_cases(["pepco_maryland"])
    r = case_request("pepco_maryland", kind, "custom", plan=plan, start_date=start, end_date=end)
    restored = browser_request(r)
    assert restored["account"] == r["account"]
    assert restored["billing_cycles"] == r["billing_cycles"]
    account_region(restored["regional_account"], "pepco_maryland")
    assert restored["regional_account"]["retail_supplier"] == "pepco_maryland"
    assert restored["regional_account"]["wholesale_pricing_location"] is None
    grid, native, cycles, _ = prepare(restored)
    assert len(grid.index) == len(native) == intervals and len(cycles) == cycle_count
    reference = grid_only_counterfactual("pepco_maryland", r["account"])
    assert reference["account"]["der_ordinary_service_confirmed"] is False
    assert reference["account"]["usc_band"] == r["account"]["usc_band"]
    for year in (2025, 2026):
        key = f"usc_assignment_{year}_source"
        assert reference["account"][key] == r["account"][key]
    for key, value in (("state_jurisdiction", "DC"), ("retail_supplier", "competitive_supplier")):
        broken = deepcopy(restored)
        broken["regional_account"][key] = value
        with pytest.raises(ValueError):
            prepare(broken)


@pytest.mark.parametrize("kind,plan", CASES)
def test_main_browser_request_worker_subtotal_bills_saved_csv_zip_and_electrical(service, kind, plan):
    app, call, headers = service
    r = browser_request(request_for(kind, plan))
    prepare(r)
    queued = call("/api/v1/regional/studies", r, headers)
    study = wait_for_study(call, queued["id"])
    assert study["status"] == "completed", study.get("error")
    result = study["result"]
    assert result["engine_id"] == app.engine["id"]
    assert result["rate_evidence_status"] == "verified" and result["rate_evidence"]["assumption_ids"] == []
    assert result["is_complete_bill"] is False
    for scenario, bills in result["billing"].items():
        assert len(bills) == 1
        bill = bills[0]
        assert bill["is_complete_bill"] is False
        assert bill["excluded_components"] == excluded_components(plan)
        assert bill["rate_assumptions"] == [] and bill["export_kwh"] < 1e-5
        assert bill["total_usd"] == pytest.approx(sum(bill["lines"].values()))
        assert result["optimization"][scenario]["annual_optimum_proven"] is None
    ac = result["ac_validation"]
    assert ac["status"] == "completed" and ac["all_intervals_feasible"]
    assert all(x["checked_intervals"] == 2880 and x["failed_intervals"] == 0 for x in ac["scenarios"])
    base = "/api/studies/"+queued["id"]
    with ZipFile(BytesIO(call(base+"/tables.zip"))) as archive:
        assert archive.testzip() is None
        assert json.loads(archive.read("result-manifest.json")) == result
        for scenario in result["billing"]:
            assert "ac-"+scenario+".csv" in archive.namelist()
    call(base+"/save", {"name":"Pepco Maryland "+plan+" reviewed subtotal"}, headers)
    saved = call(base+"/request.json")
    assert saved["account"] == r["account"] and saved["regional_account"] == r["regional_account"]
    restored = browser_request(saved)
    prepare(restored)
    assert restored["account"] == r["account"]


@pytest.mark.parametrize("kind,plan", CASES)
def test_audit_rejects_hidden_exclusions_or_false_complete_bill_promotion(kind, plan):
    r = case_request("pepco_maryland", kind, "monthly", plan=plan)
    grid, native, cycles, equipment = prepare(r)
    _, block, cycle = cycles[0]
    a = cycle_account(r["account"], cycle)
    bill = calculate_cycle("pepco_maryland", grid.index[block], native[block], np.zeros(len(native[block])), a, equipment=equipment)
    assert checked_bill_scope(bill, "pepco_maryland", a, grid.index[block]) == ("verified_charges_subtotal", sorted(excluded_components(plan)))
    for key, replacement in (("excluded_components", []), ("rate_evidence_status", "provisional"),
                              ("warnings", []), ("is_complete_bill", True)):
        broken = deepcopy(bill)
        broken[key] = replacement
        with pytest.raises(AssertionError):
            checked_bill_scope(broken, "pepco_maryland", a, grid.index[block])


@pytest.mark.parametrize("kind,plan", CASES)
def test_full_year_and_missing_rate_windows_never_fall_back_to_known_base_rates(kind, plan):
    with pytest.raises(ValueError, match="full-year2025"):
        case_request("pepco_maryland", kind, "annual", plan=plan)
    for start, end in (("2025-01-01", "2025-12-31"), ("2025-03-01", "2025-03-31"),
                       ("2026-05-01", "2026-05-31"), ("2026-06-01", "2026-06-30"),
                       ("2026-11-01", "2026-11-30"), ("2026-08-02", "2026-08-31")):
        with pytest.raises(ValueError):
            prepare(request_for(kind, plan, start, end))
