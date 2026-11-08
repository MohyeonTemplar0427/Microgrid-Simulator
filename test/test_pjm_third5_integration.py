"""Targeted form, worker and saved-artifact contracts for the third PJM batch."""
from copy import deepcopy
from io import BytesIO
import json
import os
from pathlib import Path
import shutil
import subprocess
from urllib.error import HTTPError
from zipfile import ZipFile

import pytest

from src.billing.regional import adapter
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.local_web.regional_study import capabilities, defaults, prepare
from test_local_web import service, wait_for_study
from test_regional_study import browser_request
from tools.run_regional_validation import PJM_THIRD5_CASES, case_request, selected_cases

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = {"duke_energy_kentucky": ("KY", "DEOK"), "delaware_electric_cooperative": ("DE", "DPL")}
BLOCKED = {
    "rappahannock_electric_cooperative": ("VA", ("A-1", "B-1")),
    "south_central_power_ohio": ("OH", ("R", "SGS")),
    "shenandoah_valley_electric_cooperative": ("VA", ("A-15", "B-16")),
}


@pytest.mark.parametrize("utility,kind,plan", PJM_THIRD5_CASES)
def test_forms_preserve_identity_account_obligations_and_non_export(utility, kind, plan):
    raw = case_request(utility, kind, "monthly", plan=plan)
    request = browser_request(raw)
    assert request == {**raw, "name": "Untitled study"}
    cap = capabilities()["utilities"][utility]
    assert (cap["state"], cap["transmission_zone"]) == IDENTITY[utility]
    assert cap["grid_operator"] == "PJM"
    assert (utility, kind, plan) in selected_cases([utility])
    assert request["regional_account"]["retail_supplier"] == utility
    assert request["regional_account"]["wholesale_pricing_location"] is None
    assert request["operating_contract"]["renewable_only_charging"]
    prepare(request)
    initial = defaults(utility, kind, plan)
    assert initial["operating_contract"]["interconnection_confirmed"] is False
    initial["operating_contract"].update(interconnection_confirmed=True,
        reference="Explicit hypothetical final approval for the exact PV and paired-storage design")
    prepare(initial)
    for key, value in (("distribution_utility", "kentucky_power_kentucky"),
                       ("state_jurisdiction", "XX"), ("transmission_zone", "OTHER"),
                       ("retail_supplier", "third_party")):
        altered = deepcopy(request)
        altered["regional_account"][key] = value
        with pytest.raises(ValueError):
            prepare(altered)
    for target, key, value in (("operating_contract", "grid_charging_confirmed", True),
                               ("operating_contract", "mode", "net_metering"),
                               ("account", "der_ordinary_service_confirmed", False)):
        altered = deepcopy(request)
        altered[target][key] = value
        with pytest.raises(ValueError):
            prepare(altered)
    reference = grid_only_counterfactual(utility, request["account"])
    assert reference["account"]["der_ordinary_service_confirmed"] is False
    assert reference["account"]["der_activation_date"] == reference["account"]["der_eligibility_source"] == ""
    assert all(reference["account"][key] == value for key, value in request["account"].items()
               if key not in reference["changed_account_fields"])


def test_duke_clock_uses_following_month_and_first_business_day():
    for year, expected in ((2025, [("2025-05-01", "2025-05-01"), ("2025-06-01", "2025-06-02"), ("2025-07-01", "2025-07-01")]),
                           (2026, [("2026-05-01", "2026-05-01"), ("2026-06-01", "2026-06-01"), ("2026-07-01", "2026-07-01")])):
        request = case_request("duke_energy_kentucky", "commercial", "custom", plan="DS",
                               start_date=f"{year}-04-01", end_date=f"{year}-06-30")
        assert [(c["billing_month"], c["bill_date"]) for c in request["billing_cycles"]] == expected
        assert browser_request(request)["billing_cycles"] == request["billing_cycles"]
        altered = deepcopy(request)
        altered["billing_cycles"][0].update(billing_month=f"{year}-04-01", bill_date=f"{year}-04-30")
        with pytest.raises(ValueError):
            prepare(altered)
    with pytest.raises(ValueError, match="full-year"):
        case_request("duke_energy_kentucky", "residential", "annual", plan="RS")


def test_dec_annual_history_and_dst_are_explicit_without_using_reduced_imports():
    request = case_request("delaware_electric_cooperative", "commercial", "annual", plan="GS")
    grid, _, cycles, _ = prepare(browser_request(request))
    assert len(grid.index) == 35040 and len(cycles) == 12
    assert len(grid.index[grid.index.month == 3]) == 743*4
    assert len(grid.index[grid.index.month == 11]) == 721*4
    for cycle in request["billing_cycles"]:
        facts = adapter("delaware_electric_cooperative").hypothetical_defaults("GS", day=cycle["start_date"])
        assert cycle["account_overrides"]["gs_history_through_month"] == facts["gs_history_through_month"]
        assert cycle["account_overrides"]["gs_monthly_demands_kw"] == [8.]*12
    altered = deepcopy(request)
    altered["billing_cycles"][4]["account_overrides"]["gs_monthly_demands_kw"][-1] = 50.
    with pytest.raises(ValueError):
        prepare(altered)


def test_dec_exact_installation_dc_and_battery_supplement_survive_form():
    request = browser_request(case_request("delaware_electric_cooperative", "residential", "monthly", plan="R"))
    assert request["account"]["battery_interconnection_confirmed"] is True
    for value in (100., 101.):
        altered = deepcopy(request)
        altered["solar"]["dc_capacity_kw"] = value
        with pytest.raises(ValueError):
            prepare(altered)
    altered = deepcopy(request)
    altered["account"]["battery_interconnection_confirmed"] = False
    with pytest.raises(ValueError):
        prepare(altered)


@pytest.mark.parametrize("utility", BLOCKED)
def test_source_gaps_remain_visible_and_cannot_create_api_studies(service, utility):
    state, plans = BLOCKED[utility]
    cap = capabilities()["utilities"][utility]
    assert cap["state"] == state and cap["grid_operator"] == "PJM"
    assert cap["transmission_zone"] is None
    assert not cap["defaults"] and not cap["accounts"]
    assert {p["id"] for p in cap["plans"]} == set(plans)
    assert all(p["status"] == "unsupported" and not p["coverage"] for p in cap["plans"])
    with pytest.raises(ValueError):
        defaults(utility)
    with pytest.raises(ValueError):
        selected_cases([utility])
    script = "const fs=require('node:fs');const {regionalUnavailableReason}=require('./src/local_web/static/regional.js');const c=JSON.parse(fs.readFileSync(0,'utf8'));process.stdout.write(JSON.stringify(['residential','commercial'].map(k=>regionalUnavailableReason(c,k))));"
    reasons = json.loads(subprocess.run(["node", "-e", script], input=json.dumps(cap), text=True,
                                       capture_output=True, check=True, cwd=ROOT).stdout)
    assert all("unavailable" in r.lower() for r in reasons)
    app, call, headers = service
    request = case_request("delaware_electric_cooperative", "residential", "monthly", plan="R")
    request["site"]["utility"] = utility
    request["regional_account"].update(distribution_utility=utility, retail_supplier=utility,
                                       state_jurisdiction=state, transmission_zone=None)
    request["account"] = adapter(utility).hypothetical_defaults(plans[0], day=request["start_date"])
    with pytest.raises(HTTPError) as error:
        call("/api/v1/regional/studies", request, headers)
    assert error.value.code == 400
    response = json.loads(error.value.read())
    assert "error" in response and "id" not in response


@pytest.mark.parametrize("utility,kind,plan", PJM_THIRD5_CASES)
def test_queued_worker_save_reopen_and_csv_zip_bytes(service, utility, kind, plan):
    app, call, headers = service
    request = browser_request(case_request(utility, kind, "monthly", plan=plan))
    run = call("/api/v1/regional/studies", request, headers)
    finished = wait_for_study(call, run["id"])
    assert finished["status"] == "completed", finished.get("error")
    result = finished["result"]
    assert result["engine_id"] == app.engine["id"] and result["is_complete_bill"]
    assert result["ac_validation"]["all_intervals_feasible"]
    assert all(c["cost_optimum_proven"] is True for scenario in ("pv_only", "pv_battery")
               for c in result["optimization"][scenario]["cycles"])
    base = "/api/studies/"+run["id"]
    directory = app.store.directory/"runs"/run["id"]
    with ZipFile(BytesIO(call(base+"/tables.zip"))) as archive:
        assert archive.testzip() is None
        assert json.loads(archive.read("result-manifest.json")) == result
        for table in result["tables"]:
            filename = table["id"]+".csv"
            assert archive.read(filename) == call(base+"/tables/"+filename) == (directory/filename).read_bytes()
    call(base+"/save", {"name": utility+" "+plan+" targeted acceptance"}, headers)
    assert call(base)["saved"]
    reopened = call(base+"/request.json")
    rebuilt = browser_request(reopened)
    assert rebuilt["account"] == request["account"] and rebuilt["billing_cycles"] == request["billing_cycles"]
    retained = os.environ.get("PJM_THIRD5_WORKER_EVIDENCE")
    if retained:
        target = (ROOT/retained).resolve()
        assert target.is_relative_to(ROOT/".cache")
        target = target/"runs"/run["id"]
        target.parent.mkdir(exist_ok=True, parents=True)
        shutil.copytree(directory, target)
