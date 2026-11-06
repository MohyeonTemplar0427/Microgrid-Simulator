"""I&M Indiana catalog, browser request, queued worker and saved artifacts."""
from copy import deepcopy
from io import BytesIO
import json
from zipfile import ZipFile

import pytest

from src.billing.im_in import UTILITY
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.local_web.regional_study import capabilities, prepare
from test_local_web import service, wait_for_study
from test_regional_study import browser_request
from tools.run_regional_validation import case_request, selected_cases


@pytest.mark.parametrize("kind,code", [("residential", "015"), ("residential", "016"),
                                       ("commercial", "215"), ("commercial", "218")])
def test_catalog_form_identity_and_calendars(kind, code):
    caps = capabilities()["utilities"][UTILITY]
    assert (caps["state"], caps["grid_operator"], caps["transmission_zone"]) == ("IN", "PJM", "AEP")
    assert (UTILITY, kind, code) in selected_cases([UTILITY])
    raw = case_request(UTILITY, kind, "monthly", plan=code)
    r = browser_request(raw)
    assert r == {**raw, "name": "Untitled study"}
    assert r["account"]["confirmed_tariff_code"] == code
    assert r["regional_account"]["wholesale_pricing_location"] is None
    assert r["regional_account"]["retail_supplier"] == UTILITY
    for key, wrong in (("state_jurisdiction", "MI"), ("distribution_utility", "duke_energy_indiana"),
                       ("retail_supplier", "other"), ("transmission_zone", "DEI")):
        altered = deepcopy(r)
        altered["regional_account"][key] = wrong
        with pytest.raises(ValueError):
            prepare(altered)
    r["carbon"] = {"source": "electricity_maps", "region": "US-MIDA-PJM"}
    assert len(prepare(r)[0].index) == 2976


def test_native_domain_and_der_approval():
    r = case_request(UTILITY, "commercial", "monthly", plan="218")
    for kw in (6.1, 10.001):
        changed = deepcopy(r)
        changed["load"].update(mode="constant", csv=None, power_kw=kw, archetype="office")
        with pytest.raises(ValueError, match="native load"):
            prepare(changed)
    for bad in ({"der_ordinary_service_confirmed": False}, {"der_eligibility_source": ""},
                {"der_activation_date": "2025-07-02"}):
        changed = deepcopy(r)
        changed["account"].update(bad)
        with pytest.raises(ValueError):
            prepare(changed)
    changed = deepcopy(r)
    changed["operating_contract"]["grid_charging_confirmed"] = True
    with pytest.raises(ValueError, match="PV-only"):
        prepare(changed)
    r["tariff_comparisons"] = ["215"]
    with pytest.raises(ValueError, match="exact I&M Indiana tariff code"):
        prepare(r)
    reference = grid_only_counterfactual(UTILITY, r["account"])
    assert set(reference["changed_account_fields"]) == {
        "der_ordinary_service_confirmed", "der_activation_date", "der_eligibility_source"
    }
    assert reference["account"]["gs_average_monthly_kwh"] == r["account"]["gs_average_monthly_kwh"]


@pytest.mark.parametrize("kind,code", [("residential", "015"), ("commercial", "218")])
def test_queued_worker_bill_save_and_exports(service, kind, code):
    app, call, headers = service
    r = browser_request(case_request(UTILITY, kind, "custom", plan=code,
                                     start_date="2026-11-01", end_date="2026-11-30"))
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
    call(base+"/save", {"name": "I&M "+code+" acceptance"}, headers)
    assert call(base)["saved"]
    assert browser_request(call(base+"/request.json"))["account"] == r["account"]
