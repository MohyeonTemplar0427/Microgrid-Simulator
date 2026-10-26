"""PPL/AEP account controls, native inputs, queued billing and electrical replay."""
from copy import deepcopy
from datetime import date
from io import BytesIO
import json
from zipfile import ZipFile

import pytest

from src.billing.regional import account_region, adapter
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.local_web.regional_study import calendar_cycles, capabilities, defaults, prepare
from tools.run_regional_validation import case_request, selected_cases
from test_local_web import service, wait_for_study
from test_regional_study import browser_request


CASES = (("ppl_electric_pennsylvania", "residential", "RS", "PA", "PPL"),
         ("ppl_electric_pennsylvania", "commercial", "GS-1", "PA", "PPL"),
         ("aep_ohio", "residential", "RS", "OH", "AEP"),
         ("aep_ohio", "commercial", "GS-1", "OH", "AEP"))
WORKER_CASES = tuple(row + (None,) for row in CASES) + tuple(
    row + ("columbus_southern",) for row in CASES if row[0] == "aep_ohio")


def request_for(utility, kind, plan, start="2026-09-01", end="2026-09-30"):
    r = defaults(utility, kind, plan)
    r.update(start_date=start, end_date=end, billing_cycles=calendar_cycles(start, end))
    r["operating_contract"].update(interconnection_confirmed=True, grid_charging_confirmed=True,
        reference="Explicit hypothetical approved ordinary non-export PV/storage agreement; no export compensation")
    return r


@pytest.mark.parametrize("utility,kind,plan,state,zone", CASES)
def test_accounts_and_main_form_keep_retail_service_separate_from_pjm(utility, kind, plan, state, zone):
    entry = capabilities()["utilities"][utility]
    assert entry["state"] == state and entry["grid_operator"] == "PJM"
    assert entry["transmission_zone"] == zone and entry["timezone"] == "America/New_York"
    assert (utility, kind, plan) in selected_cases([utility])
    r = request_for(utility, kind, plan)
    account_region(r["regional_account"], utility)
    assert r["regional_account"]["retail_supplier"] == utility
    assert r["regional_account"]["wholesale_pricing_location"] is None
    restored = browser_request(r)
    assert restored["account"] == r["account"]
    assert restored["regional_account"] == r["regional_account"]
    grid, native, cycles, equipment = prepare(restored)
    assert len(grid.index) == len(native) == 2880 and len(cycles) == 1
    assert equipment["pv_dc_kw"] == r["solar"]["dc_capacity_kw"]
    changed = deepcopy(r)
    changed["regional_account"]["state_jurisdiction"] = "IL"
    with pytest.raises(ValueError, match="independently consistent"):
        prepare(changed)
    changed = deepcopy(r)
    changed["regional_account"]["retail_supplier"] = "competitive_supplier"
    with pytest.raises(ValueError, match="contract"):
        prepare(changed)


@pytest.mark.parametrize("utility,kind,plan,state,zone", CASES)
def test_full_year_native_form_roundtrip_preserves_dst_and_cycles(utility, kind, plan, state, zone):
    r = case_request(utility, kind, "annual", plan=plan)
    restored = browser_request(r)
    assert restored["account"] == r["account"] and restored["load"] == r["load"]
    assert restored["billing_cycles"] == r["billing_cycles"]
    grid, native, cycles, equipment = prepare(restored)
    assert len(grid.index) == len(native) == 35040 and len(cycles) == 12
    counts = grid.index.to_series().groupby(grid.index.date).size()
    assert counts.loc[date(2025, 3, 9)] == 92
    assert counts.loc[date(2025, 11, 2)] == 100
    assert r["load"]["mode"] == "csv" and "synthetic" in r["load"]["source"].lower()
    reference = grid_only_counterfactual(utility, restored["account"])
    assert reference["account"]["tariff"] == plan
    assert reference["account"]["der_ordinary_service_confirmed"] is False
    assert restored["account"]["der_ordinary_service_confirmed"] is True


@pytest.mark.parametrize("utility,kind,plan,state,zone,legacy_zone", WORKER_CASES)
def test_main_form_worker_bills_electrical_tables_and_saved_account(service, utility, kind, plan, state, zone, legacy_zone):
    app, call, headers = service
    r = request_for(utility, kind, plan)
    if legacy_zone is not None:
        r["account"]["legacy_rate_zone"] = legacy_zone
    r = browser_request(r)
    prepare(r)
    before = deepcopy(r)
    queued = call("/api/v1/regional/studies", r, headers)
    study = wait_for_study(call, queued["id"])
    assert study["status"] == "completed", study.get("error")
    result = study["result"]
    assert result["engine_id"] == app.engine["id"]
    assert result["rate_evidence_status"] == "verified"
    assert result["rate_evidence"]["assumption_ids"] == []
    assert set(result["billing"]) == {"grid_only", "pv_only", "pv_battery"}
    for scenario, bills in result["billing"].items():
        assert len(bills) == 1
        bill = bills[0]
        assert bill["is_complete_bill"] and bill["rate_assumptions"] == []
        assert bill["export_kwh"] < 1e-5
        assert bill["total_usd"] == pytest.approx(sum(bill["lines"].values()))
        assert not any("export_credit" in key for key in bill["lines"])
        assert result["optimization"][scenario]["annual_optimum_proven"] is None
    ac = result["ac_validation"]
    assert ac["status"] == "completed" and ac["all_intervals_feasible"]
    assert all(x["checked_intervals"] == 2880 and x["failed_intervals"] == 0 for x in ac["scenarios"])
    base = "/api/studies/" + queued["id"]
    with ZipFile(BytesIO(call(base + "/tables.zip"))) as archive:
        assert archive.testzip() is None
        assert json.loads(archive.read("result-manifest.json")) == result
        for scenario in result["billing"]:
            assert "ac-" + scenario + ".csv" in archive.namelist()
    call(base + "/save", {"name": utility + " " + plan + " reviewed comparison"}, headers)
    saved = call(base + "/request.json")
    assert saved["account"] == before["account"]
    assert saved["regional_account"] == before["regional_account"]
    rebuilt = browser_request(saved)
    prepare(rebuilt)
    assert rebuilt["account"] == saved["account"]


def test_aep_legacy_zone_is_an_explicit_saved_fact():
    r = request_for("aep_ohio", "commercial", "GS-1")
    r["account"]["legacy_rate_zone"] = "columbus_southern"
    restored = browser_request(r)
    assert restored["account"]["legacy_rate_zone"] == "columbus_southern"
    prepare(restored)
    restored["account"]["legacy_rate_zone"] = "nearest_pjm_node"
    with pytest.raises(ValueError):
        prepare(restored)


def test_aep_historical_matrix_selects_zone_without_changing_other_utilities():
    ordinary = case_request("aep_ohio", "residential", "annual", plan="RS")
    csp = case_request("aep_ohio", "residential", "annual", plan="RS",
                       aep_rate_zone="columbus_southern")
    assert ordinary["account"]["legacy_rate_zone"] == "ohio_power"
    assert csp["account"]["legacy_rate_zone"] == "columbus_southern"
    assert ordinary["load"] == csp["load"] and ordinary["billing_cycles"] == csp["billing_cycles"]
    assert ordinary["regional_account"] == csp["regional_account"]
    with pytest.raises(ValueError, match="legacy rate zone"):
        case_request("aep_ohio", "residential", "annual", plan="RS", aep_rate_zone="nearest_node")


@pytest.mark.parametrize("utility,kind,plan,state,zone", CASES)
def test_unverified_dates_and_provisional_modes_never_substitute_current_prices(utility, kind, plan, state, zone):
    r = request_for(utility, kind, plan, "2024-01-01", "2024-01-31")
    with pytest.raises(ValueError):
        prepare(r)
    r = request_for(utility, kind, plan)
    r["account"].update(rate_evidence_mode="provisional_2025", provisional_assumptions_accepted=True)
    with pytest.raises(ValueError):
        prepare(r)
