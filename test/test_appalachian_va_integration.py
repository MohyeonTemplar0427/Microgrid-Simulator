"""APCo Virginia form, worker, saved request and tariff constraints."""
from copy import deepcopy
from io import BytesIO
import json
from zipfile import ZipFile

import pandas as pd
import pytest

from src.billing.appalachian_va import UTILITY
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.local_web.regional_study import capabilities, prepare
from test_local_web import service, wait_for_study
from test_regional_study import browser_request
from tools.run_regional_validation import case_request, selected_cases

PLANS = [("residential", "015"), ("commercial", "231")]


def request(kind, plan, day="2026-11-01"):
    return case_request(UTILITY, kind, "custom", plan=plan, start_date=day,
                        end_date=str((pd.Timestamp(day)+pd.offsets.MonthEnd()).date()))


@pytest.mark.parametrize("kind,plan", PLANS)
def test_browser_keeps_retail_identity_and_history_independent(kind, plan):
    cap = capabilities()["utilities"][UTILITY]
    assert (cap["state"], cap["grid_operator"], cap["transmission_zone"]) == ("VA", "PJM", "AEP")
    assert (UTILITY, kind, plan) in selected_cases([UTILITY])
    raw = request(kind, plan)
    r = browser_request(raw)
    assert r == {**raw, "name": "Untitled study"}
    assert r["regional_account"]["wholesale_pricing_location"] is None
    assert r["regional_account"]["retail_supplier"] == UTILITY and r["account"]["supply"] == "bundled"
    assert len(prepare(r)[0].index) == 2884
    for key, bad in (("state_jurisdiction", "WV"), ("distribution_utility", "aep_ohio"),
                     ("retail_supplier", "other"), ("transmission_zone", "DOM")):
        altered = deepcopy(r)
        altered["regional_account"][key] = bad
        with pytest.raises(ValueError):
            prepare(altered)
    historical = request(kind, plan, "2025-11-01")
    historical["carbon"] = {"source": "electricity_maps", "region": "US-MIDA-PJM"}
    prepare(historical)  # Contract compatibility, without any provider request.


def test_non_export_der_requires_specific_approval_and_history_is_not_reclassified():
    r = request("commercial", "231")
    changed = deepcopy(r)
    changed["load"].update(mode="constant", csv=None, power_kw=25.001, archetype="office")
    with pytest.raises(ValueError, match="native load"):
        prepare(changed)
    for bad in ({"der_ordinary_service_confirmed": False}, {"der_eligibility_source": ""},
                {"der_activation_date": "2026-11-02"}):
        changed = deepcopy(r)
        changed["account"].update(bad)
        with pytest.raises(ValueError):
            prepare(changed)
    changed = deepcopy(r)
    changed["operating_contract"]["grid_charging_confirmed"] = True
    with pytest.raises(ValueError, match="PV-only"):
        prepare(changed)
    a = r["account"]
    reference = grid_only_counterfactual(UTILITY, a)
    assert set(reference["changed_account_fields"]) == {
        "der_ordinary_service_confirmed", "der_activation_date", "der_eligibility_source"
    }
    assert all(reference["account"][key] == value for key, value in a.items()
               if key not in reference["changed_account_fields"])


@pytest.mark.parametrize("kind,plan", PLANS)
def test_queued_worker_bills_saved_settings_csv_and_zip(service, kind, plan):
    app, call, headers = service
    r = browser_request(request(kind, plan))
    study = call("/api/v1/regional/studies", r, headers)
    out = wait_for_study(call, study["id"])
    assert out["status"] == "completed", out.get("error")
    result = out["result"]
    assert result["engine_id"] == app.engine["id"]
    assert result["is_complete_bill"] and result["ac_validation"]["all_intervals_feasible"]
    base = "/api/studies/"+study["id"]
    table = call(base+"/tables/comparison")
    rows = [dict(zip(table["columns"], row)) for row in table["data"]]
    assert {row["scenario"] for row in rows} == {"grid_only", "pv_only", "pv_battery"}
    assert max(row["maximum_reconciliation_difference_usd"] for row in rows) < .0001
    run_dir = app.store.directory/"runs"/study["id"]
    with ZipFile(BytesIO(call(base+"/tables.zip"))) as archive:
        assert archive.testzip() is None
        assert json.loads(archive.read("result-manifest.json")) == result
        for item in result["tables"]:
            filename = item["id"]+".csv"
            assert archive.read(filename) == call(base+"/tables/"+filename) == (run_dir/filename).read_bytes()
    call(base+"/save", {"name": "APCo "+plan+" acceptance"}, headers)
    assert call(base)["saved"]
    assert browser_request(call(base+"/request.json"))["account"] == r["account"]
