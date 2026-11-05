"""Duke Ohio browser request, worker, and saved artifact contract."""
from copy import deepcopy
from io import BytesIO
import json
from zipfile import ZipFile

import pandas as pd
import pytest

from src.billing.duke_oh import UTILITY
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.local_web.regional_study import capabilities, prepare
from test_local_web import service, wait_for_study
from test_regional_study import browser_request
from tools.run_regional_validation import case_request, selected_cases

PLANS = [("residential", "RS"), ("commercial", "DM")]


def request(kind, plan, day="2026-10-01"):
    last_day = str((pd.Timestamp(day)+pd.offsets.MonthEnd()).date())
    return case_request(UTILITY, kind, "custom", plan=plan, start_date=day, end_date=last_day)


@pytest.mark.parametrize("kind,plan", PLANS)
def test_browser_serialization_separates_retail_supply_and_pjm(kind, plan):
    cap = capabilities()["utilities"][UTILITY]
    assert (cap["state"], cap["grid_operator"], cap["transmission_zone"]) == ("OH", "PJM", "DEOK")
    assert (UTILITY, kind, plan) in selected_cases([UTILITY])
    r = request(kind, plan)
    out = browser_request(r)
    assert out == {**r, "name": "Untitled study"}
    assert out["regional_account"]["wholesale_pricing_location"] is None
    assert out["regional_account"]["retail_supplier"] == UTILITY and out["account"]["supply"] == "sso"
    assert len(prepare(out)[0].index) == 2976
    for key, bad in (("state_jurisdiction", "KY"), ("distribution_utility", "duke_energy_indiana"),
                     ("retail_supplier", "other"), ("transmission_zone", "DEI")):
        altered = deepcopy(out)
        altered["regional_account"][key] = bad
        with pytest.raises(ValueError):
            prepare(altered)
    out["carbon"] = {"source": "electricity_maps", "region": "US-MIDA-PJM"}
    prepare(out)  # Optional provenance contract only. No live carbon retrieval.


def test_native_scope_and_storage_approval_reject_bad_requests():
    r = request("commercial", "DM")
    changed = deepcopy(r)
    changed["load"].update(mode="constant", csv=None, power_kw=15.001, archetype="office")
    with pytest.raises(ValueError, match="native load"):
        prepare(changed)
    changed = deepcopy(r)
    changed["operating_contract"]["grid_charging_confirmed"] = True
    with pytest.raises(ValueError, match="PV-only"):
        prepare(changed)
    changed = deepcopy(r)
    changed["account"]["der_activation_date"] = "2026-10-02"
    with pytest.raises(ValueError, match="active"):
        prepare(changed)


def test_grid_only_reference_retains_company_dm_assignment():
    account = request("commercial", "DM")["account"]
    reference = grid_only_counterfactual(UTILITY, account)
    assert set(reference["changed_account_fields"]) == {
        "der_ordinary_service_confirmed", "der_activation_date", "der_eligibility_source"
    }
    assert all(reference["account"][key] == value for key, value in account.items()
               if key not in reference["changed_account_fields"])


@pytest.mark.parametrize("kind,plan", PLANS)
def test_queued_worker_complete_bills_saved_settings_and_downloads(service, kind, plan):
    app, call, headers = service
    r = browser_request(request(kind, plan))
    study = call("/api/v1/regional/studies", r, headers)
    out = wait_for_study(call, study["id"])
    assert out["status"] == "completed", out.get("error")
    result = out["result"]
    assert result["engine_id"] == app.engine["id"]
    assert result["is_complete_bill"] and result["ac_validation"]["all_intervals_feasible"]
    base = "/api/studies/"+study["id"]
    comparison = call(base+"/tables/comparison")
    rows = [dict(zip(comparison["columns"], row)) for row in comparison["data"]]
    assert {row["scenario"] for row in rows} == {"grid_only", "pv_only", "pv_battery"}
    assert max(row["maximum_reconciliation_difference_usd"] for row in rows) < .0001
    run_dir = app.store.directory/"runs"/study["id"]
    for table in result["tables"]:
        filename = table["id"]+".csv"
        assert call(base+"/tables/"+filename) == (run_dir/filename).read_bytes()
    with ZipFile(BytesIO(call(base+"/tables.zip"))) as archive:
        assert archive.testzip() is None
        assert json.loads(archive.read("result-manifest.json")) == result
        for table in result["tables"]:
            filename = table["id"]+".csv"
            assert archive.read(filename) == (run_dir/filename).read_bytes()
    call(base+"/save", {"name": "Duke Ohio "+plan+" acceptance"}, headers)
    assert call(base)["saved"]
    restored = call(base+"/request.json")
    assert browser_request(restored)["account"] == r["account"]
