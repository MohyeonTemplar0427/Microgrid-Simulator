"""Annual NBT statement replay through the shared desktop/browser study path."""

from calendar import monthrange
from http.client import HTTPConnection
import json
import math
import secrets
import socket
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from src.local_web.pge_annual_study import validate_request
from src.local_web.auth import OIDCConfig, Sessions, digest
from src.local_web.runtime import Application
from src.local_web.server import make_server


def annual_request():
    months = [(2024, month) for month in range(2, 13)] + [(2025, 1)]
    records = []
    for number, (year, month) in enumerate(months):
        records.append({
            "period_start": f"{year}-{month:02d}-01",
            "period_end": f"{year}-{month:02d}-{monthrange(year, month)[1]:02d}",
            "import_kwh": 3000 if number == 0 else 0,
            "export_kwh": 5000 if number == 11 else 0,
            "charges": {"generation": 4 if number == 0 else 0,
                        "delivery": 500 if number == 0 else 0,
                        "protected": 20 if number == 0 else 0},
            "credits_earned": {"generation": 136.94 if number == 11 else 0,
                               "delivery": 22 if number == 11 else 0,
                               "bonus": 1.05 if number == 11 else 0},
            "offsettable_paid": {"generation": 4 if number == 0 else 0,
                                 "delivery": 500 if number == 0 else 0},
            "source_reference": f"Hypothetical cycle {number + 1}",
            "evidence_kind": "hypothetical",
        })
    return {
        "schema_version": 7,
        "name": "Hypothetical PG&E NBT year",
        "account_confirmed": True,
        "records": records,
        "rates": {
            "month": "2025-01",
            "generation_recoupment_per_kwh": .04,
            "delivery_recoupment_per_kwh": .01,
            "nsc_per_kwh": .02965,
            "source_reference": "PG&E guide illustrative factors, not filed rates",
            "evidence_kind": "hypothetical",
        },
    }


def test_annual_request_uses_verified_replay_and_rejects_incomplete_inputs():
    request = annual_request()
    result = validate_request(request)
    assert result["true_up"]["adjustment_if_all_bonus_applied"] == pytest.approx(-66.35)
    request["records"][0]["charges"]["protected"] = math.nan
    with pytest.raises(ValueError, match="finite"):
        validate_request(request)
    request = annual_request()
    request["records"][0]["unexpected"] = 1
    with pytest.raises(ValueError, match="unknown fields"):
        validate_request(request)
    request = annual_request()
    request["account_confirmed"] = False
    with pytest.raises(ValueError, match="Confirm"):
        validate_request(request)


def test_annual_replay_is_saved_and_exports_tables_via_local_http(tmp_path):
    application = Application(tmp_path)
    server = make_server(application, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"

    def get(path):
        with urlopen(base + path, timeout=10) as response:
            return response.read(), response.headers

    try:
        capabilities = json.loads(get("/api/capabilities")[0])
        assert capabilities["pge_annual_replay"]["program"] == "pge_nbt_statement_replay"
        body = json.dumps(annual_request()).encode()
        headers = {"Content-Type": "application/json", "X-Study-Token": capabilities["token"], "Origin": base}
        with pytest.raises(HTTPError) as wrong_route:
            urlopen(Request(base + "/api/studies", body, headers), timeout=10)
        assert wrong_route.value.code == 400
        with urlopen(Request(base + "/api/v1/pge/annual-studies", body, headers), timeout=10) as response:
            study = json.load(response)
            assert response.status == 202
        for _ in range(100):
            study = json.loads(get("/api/studies/" + study["id"])[0])
            if study["status"] in ("completed", "failed"):
                break
            time.sleep(.1)
        assert study["status"] == "completed", study.get("error")
        assert [table["id"] for table in study["result"]["tables"]] == [
            "annual-summary", "monthly-ledger", "true-up-components"]
        assert "not simulated" in " ".join(study["result"]["warnings"])
        summary = json.loads(get(f"/api/studies/{study['id']}/tables/annual-summary")[0])
        column = summary["columns"].index("adjustment_if_all_bonus_applied")
        assert summary["data"][0][column] == pytest.approx(-66.35)
        monthly_csv, csv_headers = get(f"/api/studies/{study['id']}/tables/monthly-ledger.csv")
        assert csv_headers["Content-Type"].startswith("text/csv")
        assert len(monthly_csv.decode().splitlines()) == 13
        assert (application.store.directory / "runs" / study["id"] / "monthly-ledger.meta.json").is_file()
        assert not (application.store.directory / "runs" / study["id"] / "monthly-ledger.json").exists()
        assert json.loads(get(f"/api/studies/{study['id']}/request.json")[0]) == annual_request()
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
        application.close()


def test_annual_route_keeps_member_ownership_and_temporary_policy(tmp_path):
    application = Application(tmp_path, embedded_worker=False)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    auth = Sessions(application.store, OIDCConfig(
        "https://identity.example", "client", "test-secret",
        f"http://127.0.0.1:{port}/auth/callback"), provider=object())
    server = make_server(application, port, auth=auth, allow_guests=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def member(name):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        with application.store.connect() as db:
            db.execute("INSERT INTO auth_sessions VALUES (?, ?, ?, ?, ?)",
                       (digest(token), digest(name), csrf, time.time(), time.time()))
        return {"Cookie": f"{auth.COOKIE}={token}", "X-Study-Token": csrf}

    def call(path, headers, body=None):
        connection = HTTPConnection("127.0.0.1", port, timeout=10)
        connection.request("POST" if body is not None else "GET", path,
                           json.dumps(body) if body is not None else None,
                           {"Content-Type": "application/json", **headers})
        response = connection.getresponse()
        status, payload = response.status, json.loads(response.read())
        connection.close()
        return status, payload

    try:
        alice, bob = member("alice"), member("bob")
        status, study = call("/api/v1/pge/annual-studies", alice, annual_request())
        assert status == 202 and study["owner_id"] == digest("alice") and study["saved"] == 0
        assert call(f"/api/studies/{study['id']}", bob)[0] == 404
        assert call(f"/api/studies/{study['id']}", alice)[0] == 200
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
        application.close()
