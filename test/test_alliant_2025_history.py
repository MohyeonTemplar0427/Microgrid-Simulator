"""Historical account/form contracts; full-year weather runs are opt-in artifacts."""
from copy import deepcopy
from datetime import date
from io import BytesIO
import json
from zipfile import ZipFile

import pytest

from src.local_web.regional_study import capabilities, prepare
from tools.run_regional_validation import case_request
from test_alliant_integration import PLANS, UTILITY, request_for
from test_local_web import service, wait_for_study
from test_regional_study import browser_request


@pytest.mark.parametrize("plan", PLANS)
def test_full_year_2025_main_form_preserves_native_inputs_and_dst(plan):
    kind = "commercial" if plan in ("600", "607") else "residential"
    request = case_request(UTILITY, kind, "annual", plan=plan)
    restored = browser_request(request)
    assert restored["account"] == request["account"]
    assert restored["load"] == request["load"]
    assert restored["billing_cycles"] == request["billing_cycles"]
    grid, native, cycles, equipment = prepare(restored)
    assert len(grid.index) == len(native) == 35040
    assert len(cycles) == 12 and equipment["pv_dc_kw"] == 5.
    counts = grid.index.to_series().groupby(grid.index.date).size()
    assert counts.loc[date(2025, 3, 9)] == 92
    assert counts.loc[date(2025, 11, 2)] == 100
    assert all(c["billing_month"].startswith("2025-") for c in restored["billing_cycles"])
    entry = capabilities()["utilities"][UTILITY]
    selected = next(p for p in entry["plans"] if p["id"] == plan)
    assert any(w["start"] <= "2025-01-01" and w["end"] >= "2025-12-31"
               for w in selected["coverage"])
    assert entry["defaults"][kind]["start_date"].startswith("2026-")


@pytest.mark.parametrize("plan,start,end,credit", [
    ("427", "2025-09-01", "2025-09-30", True),
    ("607", "2025-10-01", "2025-10-31", False),
])
def test_historical_form_worker_credit_boundary_and_reopen(service, plan, start, end, credit):
    app, call, headers = service
    request = browser_request(request_for(plan, start, end))
    original = deepcopy(request)
    queued = call("/api/v1/regional/studies", request, headers)
    study = wait_for_study(call, queued["id"])
    assert study["status"] == "completed", study.get("error")
    result = study["result"]
    assert result["engine_id"] == app.engine["id"]
    assert result["rate_evidence_status"] == "verified"
    assert result["ac_validation"]["all_intervals_feasible"]
    for scenario, bills in result["billing"].items():
        assert len(bills) == 1
        bill = bills[0]
        assert bill["is_complete_bill"] and bill["rate_assumptions"] == []
        tbr = bill["lines"].get("tax_benefit", 0.)
        assert tbr < 0 if credit else tbr == 0
        assert bill["total_usd"] == pytest.approx(sum(bill["lines"].values()))
        assert bill["export_kwh"] < 1e-5
        assert bill["metrics"]["eac_includes_rce"] is True
        assert result["optimization"][scenario]["annual_optimum_proven"] is None
    base = "/api/studies/" + queued["id"]
    with ZipFile(BytesIO(call(base + "/tables.zip"))) as archive:
        assert archive.testzip() is None
        saved_manifest = json.loads(archive.read("result-manifest.json"))
        assert saved_manifest["rate_evidence_status"] == "verified"
        for scenario in result["billing"]:
            assert "ac-" + scenario + ".csv" in archive.namelist()
    call(base + "/save", {"name": "Alliant 2025 " + plan + " historical boundary"}, headers)
    saved = call(base + "/request.json")
    assert saved["account"] == original["account"]
    rebuilt = browser_request(saved)
    prepare(rebuilt)
    assert rebuilt["billing_cycles"] == original["billing_cycles"]
    assert rebuilt["load"] == original["load"]


@pytest.mark.parametrize("start,end", [
    ("2024-01-01", "2024-01-31"),
    ("2026-01-01", "2026-01-31"),
    ("2026-11-01", "2026-11-30"),
])
def test_2025_extension_does_not_extrapolate_other_gaps(start, end):
    request = request_for("400", start, end)
    with pytest.raises(ValueError):
        prepare(request)
