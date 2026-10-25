"""Shared regional form, worker, evidence and separate utility/grid identities."""
from copy import deepcopy

import pytest

from src.billing.regional import account_region, adapter
from src.local_web.regional_study import capabilities, calendar_cycles, defaults, prepare
from tools.run_regional_validation import case_request, selected_cases
from test_local_web import service, wait_for_study
from test_regional_study import browser_request


WE = "we_energies_wisconsin"
DUKE = "duke_energy_indiana"


def test_regional_catalog_keeps_clocks_service_and_grid_identity_separate():
    catalog = capabilities()["utilities"]
    for utility, clock, state, zone, lrz in (
        (WE, "America/Chicago", "WI", None, "LRZ2"),
        (DUKE, "America/Indiana/Indianapolis", "IN", "DEI", "LRZ6"),
    ):
        entry = catalog[utility]
        assert entry["timezone"] == clock and entry["state"] == state
        assert entry["grid_operator"] == "MISO"
        assert entry["transmission_zone"] == zone
        assert entry["resource_adequacy_zone"] == lrz
        supported = [p for p in entry["plans"] if p["status"] == "supported"]
        assert set(entry["accounts"]) == {p["id"] for p in supported}
        assert set(entry["defaults"]) == {p["customer_class"] for p in supported}
        for p in supported:
            r = defaults(utility, p["customer_class"], p["id"])
            region = r["regional_account"]
            account_region(region, utility)
            assert region["distribution_utility"] == region["retail_supplier"] == utility
            assert region["wholesale_pricing_location"] is None
            assert r["timezone"] == clock
            bad = deepcopy(region)
            bad["state_jurisdiction"] = "OH"
            with pytest.raises(ValueError):
                account_region(bad, utility)
    # The joint DEI transmission zone does not determine a site's owner.
    assert catalog[DUKE]["transmission_owner"] is None
    assert "Wabash" in catalog[DUKE]["transmission_ownership_context"]


@pytest.mark.parametrize("plan", ("Rg1", "Rg2", "Cg1", "Cg6"))
def test_we_prepared_matrix_requests_use_verified_windows_and_native_load(plan):
    kind = "residential" if plan.startswith("Rg") else "commercial"
    assert (WE, kind, plan) in selected_cases([WE])
    monthly = case_request(WE, kind, "monthly", plan=plan)
    prepare(monthly)
    assert monthly["start_date"] == "2025-04-01"
    assert monthly["timezone"] == "America/Chicago"
    assert monthly["load"]["native_basis_confirmed"]
    for first, last, cycles in (("2025-01-01", "2025-06-30", 6),
                                 ("2026-01-01", "2026-09-30", 9)):
        r = case_request(WE, kind, "custom", plan=plan, start_date=first, end_date=last)
        prepare(r)
        assert len(r["billing_cycles"]) == cycles
    with pytest.raises(ValueError, match="coverage|verified|ECC|environmental"):
        case_request(WE, kind, "annual", plan=plan)


@pytest.mark.parametrize("plan", ("RS", "RS-TOU", "CS", "CS-TOU"))
def test_duke_prepared_case_rejects_unverified_year_and_uses_actual_service(plan):
    kind = "residential" if plan.startswith("RS") else "commercial"
    r = case_request(DUKE, kind, "monthly", plan=plan)
    prepare(r)
    assert r["start_date"] == "2025-03-01" and r["end_date"] == "2025-03-31"
    assert r["timezone"] == "America/Indiana/Indianapolis"
    assert r["electrical_service"]["phase"] == "single"
    assert r["electrical_service"]["nominal_voltage_v"] == 240
    assert r["load"]["native_basis_confirmed"]
    with pytest.raises(ValueError, match="coverage|verified|March|window"):
        prepare(case_request(DUKE, kind, "annual", plan=plan))


@pytest.mark.parametrize("utility,plan,kind,start,end", [
    (WE, plan, "residential" if plan.startswith("Rg") else "commercial", "2026-07-01", "2026-07-31")
    for plan in ("Rg1", "Rg2", "Cg1", "Cg6")
] + [
    (DUKE, plan, "residential" if plan.startswith("RS") else "commercial", "2025-03-01", "2025-03-31")
    for plan in ("RS", "RS-TOU", "CS", "CS-TOU")
])
def test_form_api_worker_save_and_electrical_scenarios(service, utility, plan, kind, start, end):
    app, call, headers = service
    r = defaults(utility, kind, plan)
    r.update(start_date=start, end_date=end, billing_cycles=calendar_cycles(start, end))
    r["operating_contract"].update(interconnection_confirmed=True,
        grid_charging_confirmed=True, reference="Explicit hypothetical utility-approved non-export account")
    r = browser_request(r)
    prepare(r)
    saved = call("/api/v1/regional/studies", r, headers)
    study = wait_for_study(call, saved["id"])
    assert study["status"] == "completed", study.get("error")
    result = study["result"]
    assert result["engine_id"] == app.engine["id"]
    assert result["rate_evidence"]["selected_mode"] == "verified"
    assert result["rate_evidence"]["provisional_assumptions_accepted"] is False
    assert result["rate_evidence"]["status"] == "verified"
    assert result["rate_evidence"]["assumption_models"] == result["rate_evidence"]["assumption_ids"] == []
    assert "billing-assumptions" not in {t["id"] for t in result["tables"]}
    assert set(result["billing"]) == {"grid_only", "pv_only", "pv_battery"}
    assert result["ac_validation"]["status"] == "completed"
    for scenario, bills in result["billing"].items():
        assert len(bills) == 1
        assert bills[0]["is_complete_bill"] and bills[0]["rate_evidence_status"] == "verified"
        assert bills[0]["export_kwh"] < 1e-5
        assert bills[0]["total_usd"] == pytest.approx(sum(bills[0]["lines"].values()))
        assert result["optimization"][scenario]["annual_optimum_proven"] is None
    base = "/api/studies/" + saved["id"]
    components = call(base + "/tables/billing-components.csv")
    assert (b"environmental" if utility == WE else b"indiana_sales_tax") in components
    for scenario in ("grid_only", "pv_only", "pv_battery"):
        assert b"scheduled_grid" in call(base + "/tables/ac-" + scenario + ".csv")
    assert call(base + "/tables.zip")[:2] == b"PK"
    call(base + "/save", {"name": utility + " " + plan + " acceptance"}, headers)
    restored = call(base + "/request.json")
    assert restored["account"] == r["account"]
    assert browser_request(restored)["account"] == r["account"]
