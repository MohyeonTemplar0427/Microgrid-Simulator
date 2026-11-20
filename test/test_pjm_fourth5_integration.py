"""Fourth PJM utility batch through the native form, queue, result files and saved settings."""
from copy import deepcopy
from io import BytesIO
import json
import subprocess
from urllib.error import HTTPError
from zipfile import ZipFile

import pytest

from src.billing.regional import UTILITIES, adapter
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.local_web.regional_study import capabilities, defaults, prepare
from test_local_web import service, wait_for_study
from test_regional_study import browser_request
from tools.run_regional_validation import PJM_FOURTH5_CASES, case_request, expected_scenarios, selected_cases


@pytest.mark.parametrize("utility,kind,plan", PJM_FOURTH5_CASES)
def test_plan_forms_and_account_boundaries(utility, kind, plan):
    raw = case_request(utility, kind, "monthly", plan=plan)
    req = browser_request(raw)
    assert req == {**raw, "name": "Untitled study"}
    assert (utility, kind, plan) in selected_cases([utility])
    assert req["regional_account"]["retail_supplier"] == utility
    assert req["regional_account"]["wholesale_pricing_location"] is None
    assert req["regional_account"]["transmission_zone"] == {
        "ugi_electric_pennsylvania": "UGI", "kingsport_power_tennessee": "AEP", "naperville_illinois": "COMED"
    }[utility]
    assert req["timezone"] == ("America/Chicago" if utility == "naperville_illinois" else "America/New_York")
    _, _, _, equipment = prepare(req)
    assert ("pv_battery" in expected_scenarios(utility, plan)) == equipment["battery"]
    reference = grid_only_counterfactual(utility, req["account"])
    assert reference["applied"] and reference["account"]["der_activation_date"] == ""
    approval = "nms_approved" if utility == "kingsport_power_tennessee" else "der_ordinary_service_confirmed"
    assert reference["account"][approval] is False
    for target, field, value in [
        ("regional_account", "retail_supplier", "third_party"), ("regional_account", "state_jurisdiction", "XX"),
        ("regional_account", "transmission_zone", "UNKNOWN"), ("operating_contract", "mode", "net_metering"),
        ("operating_contract", "grid_charging_confirmed", True), ("account", approval, False),
    ]:
        altered = deepcopy(req)
        altered[target][field] = value
        with pytest.raises(ValueError):
            prepare(altered)
    if req["battery"] is None:
        altered = deepcopy(req)
        altered["battery"] = defaults("ugi_electric_pennsylvania")["battery"]
        with pytest.raises(ValueError, match="(?i)storage|battery"):
            prepare(altered)


@pytest.mark.parametrize("utility", ["cleveland_public_power_ohio", "choptank_electric_cooperative"])
def test_blocked_utility_rejects_each_plan_at_api(service, utility):
    _, call, headers = service
    cap = capabilities()["utilities"][utility]
    assert not cap["defaults"] and not cap["accounts"]
    assert {row["customer_class"] for row in cap["plans"]} == {"residential", "commercial"}
    assert all(not row["coverage"] and not row["equipment_modes"] and row["reason"] for row in cap["plans"])
    unavailable = "const {regionalUnavailableReason}=require('./src/local_web/static/regional.js');const c=JSON.parse(require('node:fs').readFileSync(0,'utf8'));console.log(['commercial','residential'].every(k=>regionalUnavailableReason(c,k).includes('unavailable')));"
    assert subprocess.run(["node", "-e", unavailable], input=json.dumps(cap), text=True,
                          check=True, capture_output=True).stdout.strip() == "true"
    with pytest.raises(ValueError):
        selected_cases([utility])
    for row in cap["plans"]:
        with pytest.raises(ValueError):
            defaults(utility, row["customer_class"], row["id"])
        req = defaults("kingsport_power_tennessee", row["customer_class"])
        req["site"]["utility"] = utility
        req["regional_account"].update(distribution_utility=utility, retail_supplier=utility,
                                      state_jurisdiction=cap["state"], transmission_zone=UTILITIES[utility]["zone"])
        req["account"] = adapter(utility).defaults(row["id"])
        with pytest.raises(HTTPError) as exc:
            call("/api/v1/regional/studies", req, headers)
        assert exc.value.code == 400
        assert json.loads(exc.value.read())["error"]


@pytest.mark.parametrize("utility,kind,plan", PJM_FOURTH5_CASES[1::2])
def test_queue_saved_results_and_downloads(service, utility, kind, plan):
    app, call, headers = service
    req = browser_request(case_request(utility, kind, "monthly", plan=plan))
    created = call("/api/v1/regional/studies", req, headers)
    finished = wait_for_study(call, created["id"])
    assert finished["status"] == "completed", finished.get("error")
    result = finished["result"]
    assert result["engine_id"] == app.engine["id"] and result["is_complete_bill"]
    assert {row["scenario"] for row in result["ac_validation"]["scenarios"]} == set(expected_scenarios(utility, plan))
    assert result["ac_validation"]["all_intervals_feasible"]
    base = "/api/studies/"+created["id"]
    with ZipFile(BytesIO(call(base+"/tables.zip"))) as archive:
        assert archive.testzip() is None and json.loads(archive.read("result-manifest.json")) == result
        for table in result["tables"]:
            name = table["id"]+".csv"
            assert archive.read(name) == call(base+"/tables/"+name)
    call(base+"/save", {"name": f"{utility} {plan} targeted validation"}, headers)
    assert call(base)["saved"]
    assert browser_request(call(base+"/request.json")) == req
