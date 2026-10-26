"""BGE main form, ordinary queued worker, saved artifacts and scope audit."""
from copy import deepcopy
from datetime import date
from io import BytesIO
import json
from zipfile import ZipFile

import numpy as np
import pytest

from src.billing.regional import account_region, calculate_cycle, cycle_account
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.billing.bge_md import RELIEF_EXCLUSION
from src.local_web.regional_study import calendar_cycles, capabilities, defaults, prepare
from tools.run_regional_validation import case_request, checked_bill_scope, selected_cases
from test_local_web import service, wait_for_study
from test_regional_study import browser_request

CASES = (("residential", "R"), ("commercial", "G"))


def request_for(kind, plan, start="2026-09-01", end="2026-09-30"):
    r = defaults("bge_maryland", kind, plan)
    r.update(start_date=start, end_date=end, billing_cycles=calendar_cycles(start, end))
    r["operating_contract"].update(interconnection_confirmed=True, grid_charging_confirmed=True,
        reference="Explicit hypothetical approved ordinary non-export PV/storage agreement")
    return r


@pytest.mark.parametrize("kind,plan", CASES)
def test_bge_account_form_and_annual_dst_keep_independent_account_facts(kind, plan):
    entry = capabilities()["utilities"]["bge_maryland"]
    assert (entry["state"], entry["grid_operator"], entry["transmission_zone"]) == ("MD", "PJM", "BGE")
    assert ("bge_maryland", kind, plan) in selected_cases(["bge_maryland"])
    r = case_request("bge_maryland", kind, "annual", plan=plan)
    restored = browser_request(r)
    assert restored["account"] == r["account"]
    assert restored["billing_cycles"] == r["billing_cycles"]
    account_region(restored["regional_account"], "bge_maryland")
    assert restored["regional_account"]["retail_supplier"] == "bge_maryland"
    assert restored["regional_account"]["wholesale_pricing_location"] is None
    grid, native, cycles, _ = prepare(restored)
    assert len(grid.index) == len(native) == 35040 and len(cycles) == 12
    counts = grid.index.to_series().groupby(grid.index.date).size()
    assert counts.loc[date(2025, 3, 9)] == 92 and counts.loc[date(2025, 11, 2)] == 100
    reference = grid_only_counterfactual("bge_maryland", r["account"])
    assert reference["account"]["der_ordinary_service_confirmed"] is False
    assert reference["account"]["usc_band"] == r["account"]["usc_band"]
    assert r["account"]["der_ordinary_service_confirmed"] is True
    for key, value in (("state_jurisdiction", "VA"), ("retail_supplier", "competitive_supplier")):
        broken = deepcopy(restored)
        broken["regional_account"][key] = value
        with pytest.raises(ValueError):
            prepare(broken)


@pytest.mark.parametrize("kind,plan", CASES)
def test_bge_main_form_worker_saved_bills_csv_zip_and_electrical(service, kind, plan):
    app, call, headers = service
    r = browser_request(request_for(kind, plan))
    prepare(r)
    queued = call("/api/v1/regional/studies", r, headers)
    study = wait_for_study(call, queued["id"])
    assert study["status"] == "completed", study.get("error")
    result = study["result"]
    assert result["engine_id"] == app.engine["id"]
    assert result["rate_evidence_status"] == "verified" and result["rate_evidence"]["assumption_ids"] == []
    assert result["is_complete_bill"] is (plan == "G")
    for scenario, bills in result["billing"].items():
        assert len(bills) == 1
        bill = bills[0]
        assert bill["is_complete_bill"] is (plan == "G")
        assert bill["excluded_components"] == ([] if plan == "G" else [RELIEF_EXCLUSION])
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
    call(base+"/save", {"name":"BGE "+plan+" reviewed comparison"}, headers)
    saved = call(base+"/request.json")
    assert saved["account"] == r["account"] and saved["regional_account"] == r["regional_account"]
    restored = browser_request(saved)
    prepare(restored)
    assert restored["account"] == r["account"]


def test_bge_residential_matrix_audit_rejects_hidden_or_changed_refund_exclusion():
    r = case_request("bge_maryland", "residential", "monthly", plan="R")
    grid, native, cycles, equipment = prepare(r)
    _, block, cycle = cycles[0]
    a = cycle_account(r["account"], cycle)
    bill = calculate_cycle("bge_maryland", grid.index[block], native[block], np.zeros(len(native[block])), a, equipment=equipment)
    assert checked_bill_scope(bill, "bge_maryland", a, grid.index[block]) == ("verified_charges_subtotal", [RELIEF_EXCLUSION])
    for key, replacement in (("excluded_components", []), ("rate_evidence_status", "provisional"), ("warnings", [])):
        broken = deepcopy(bill)
        broken[key] = replacement
        with pytest.raises(AssertionError):
            checked_bill_scope(broken, "bge_maryland", a, grid.index[block])


@pytest.mark.parametrize("kind,plan", CASES)
def test_bge_unverified_dates_and_partial_cycles_have_no_fallback(kind, plan):
    for start, end in (("2024-01-01", "2024-01-31"), ("2026-11-01", "2026-11-30"),
                       ("2025-03-02", "2025-03-31")):
        with pytest.raises(ValueError):
            prepare(request_for(kind, plan, start, end))
