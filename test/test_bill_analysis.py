"""Synthetic statements only: never commit customer bills or account details."""
from copy import deepcopy
import base64
import hashlib
from io import BytesIO
import json

import pytest

from src.bill_analysis import analyze_bills, apply_corrections, extract_pages, parse_document
from src.bill_analysis.pdf import PDFExtractionError, ExtractedDocument, PageText


def _pdf(lines=()):
    """Minimal PDF with an optional embedded-text page; no test PDF on disk."""
    commands = ["BT /F1 12 Tf 40 740 Td"]
    for index, line in enumerate(lines):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.append(("" if index == 0 else "0 -18 Td ") + f"({escaped}) Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    result = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, value in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(f"{number} 0 obj\n".encode() + value + b"\nendobj\n")
    xref = len(result)
    result.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        result.extend(f"{offset:010d} 00000 n \n".encode())
    result.extend(f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(result)


def _draft():
    delivery = """Details of PG&E Electric Delivery Charges
01/01/2026 to 01/30/2026 (30 billing days)
Rate Schedule: Time-of-Use
Peak 100.000 kWh @ $0.20000 $20.00
Off Peak 200.000 kWh @ $0.30000 60.00
Customer Charge 20.00
Total Usage 300.000 kWh
Total PG&E Electric Delivery Charges $100.00"""
    generation = """Details of Ava Community Energy Electric Generation
01/01/2026 to 01/30/2026 (30 billing days)
Rate Schedule: Bright Choice
Off Peak 200.000 kWh @ $0.10000 $20.00
Credit -5.00
Total Usage 300.000 kWh
Total Ava Community Energy Electric
Generation Charges $15.00"""
    first = PageText(1, delivery + "\nTotal Amount Due $185.00", "embedded_text", delivery)
    second = PageText(2, generation, "embedded_text", generation)
    return parse_document(ExtractedDocument("a" * 64, (first, second)))


def test_pdf_text_and_scanned_page_dispatch_to_local_ocr():
    content = _pdf(["Utility: Example Electric", "Total Electric Charges $12.00"])
    document = extract_pages(content)
    assert document.sha256 == hashlib.sha256(content).hexdigest()
    assert document.pages[0].method == "embedded_text"
    assert "Example Electric" in document.pages[0].text
    scan = _pdf()
    document = extract_pages(scan, ocr=lambda _, pages: {pages[0]: "Scanned Electric Bill\nTotal Usage 50 kWh"})
    assert document.pages[0].method == "local_ocr"
    with pytest.raises(PDFExtractionError, match="no readable bill text"):
        extract_pages(scan, ocr=lambda *_: {1: ""})
    with pytest.raises(PDFExtractionError, match="PDF document"):
        extract_pages(b"not a pdf")


def test_pdf_size_and_page_limits():
    from pypdf import PdfWriter

    with pytest.raises(PDFExtractionError, match="12 MiB"):
        extract_pages(b"%PDF-" + bytes(12 * 1024 * 1024))
    writer = PdfWriter()
    for _ in range(13):
        writer.add_blank_page(width=612, height=792)
    output = BytesIO()
    writer.write(output)
    with pytest.raises(PDFExtractionError, match="1–12 pages"):
        extract_pages(output.getvalue())


def test_separate_delivery_generation_and_non_electric_statement_amount():
    draft = _draft()
    fields = draft["fields"]
    assert fields["meter_import_kwh"]["value"] == 300  # not 600
    assert fields["current_electric_charges"]["value"] == 115
    assert fields["statement_amount_due"]["value"] == 185
    assert fields["maximum_demand_kw"]["status"] == "missing"
    assert fields["export_kwh"]["status"] == "missing"
    assert not draft["issues"]
    assert {source["page"] for source in fields["billing_days"]["evidence"]} == {1, 2}
    assert draft["services"][0]["line_items"][0]["quantity_kwh"] == 100
    assert draft["services"][0]["line_items"][0]["evidence"][0]["page"] == 1


def test_corrections_are_audited_without_erasing_original_evidence():
    original = _draft()
    revised = apply_corrections(original, {"fields.billing_plan": {
        "value": "Confirmed TOU plan", "reason": "Checked the account page"}}, approve=True)
    assert revised["approved"] is True
    assert revised["fields"]["billing_plan"]["status"] == "corrected"
    assert revised["corrections"][0]["previous"] == "Time-of-Use"
    assert original["fields"]["billing_plan"]["value"] == "Time-of-Use"
    assert revised["fields"]["billing_plan"]["evidence"] == original["fields"]["billing_plan"]["evidence"]
    with pytest.raises(ValueError, match="Unknown correction path"):
        apply_corrections(original, {"fields.account_number": "123"})


def test_reconciliation_and_dates_block_unreviewed_or_inconsistent_bill():
    draft = _draft()
    draft["services"][0]["line_items"].pop()
    assert any(item["code"] == "charge_reconciliation" for item in apply_corrections(draft, {})["issues"])
    changed = apply_corrections(_draft(), {"fields.billing_days": 31})
    assert any(item["code"] == "billing_days_mismatch" for item in changed["issues"])
    with pytest.raises(ValueError, match="billing_days_mismatch"):
        apply_corrections(_draft(), {"fields.billing_days": 31}, approve=True)
    private = PageText(1, "Service For: 10 Main St\nTotal Usage 20 kWh", "embedded_text")
    from src.bill_analysis.extraction import evidence
    assert evidence(private, "Service For: 10 Main St")["text"] == "[private source line omitted]"
    from src.bill_analysis.extraction import _charge_row
    assert _charge_row(private, "Peak 100.00 kWh @ $0.20000 $20.00")["amount"] == 20
    invalid_unit = _draft()
    invalid_unit["fields"]["meter_import_kwh"]["unit"] = "kW"
    with pytest.raises(ValueError, match="invalid_unit"):
        apply_corrections(invalid_unit, {}, approve=True)


def test_day_normalized_analysis_without_fabricated_interval_savings():
    first = apply_corrections(_draft(), {}, approve=True)
    second = deepcopy(first)
    second["source_sha256"] = "b" * 64
    for path, value in {
        "fields.period_start": "2026-02-01", "fields.period_end": "2026-02-20",
        "fields.billing_days": 20, "fields.meter_import_kwh": 300,
        "services.0.fields.period_start": "2026-02-01", "services.0.fields.period_end": "2026-02-20",
        "services.0.fields.billing_days": 20, "services.0.fields.meter_import_kwh": 300,
        "services.1.fields.period_start": "2026-02-01", "services.1.fields.period_end": "2026-02-20",
        "services.1.fields.billing_days": 20, "services.1.fields.meter_import_kwh": 300,
    }.items():
        second = apply_corrections(second, {path: value})
    second = apply_corrections(second, {}, approve=True)
    report = analyze_bills([second, first])
    assert [item["meter_import_kwh_per_day"] for item in report["cycles"]] == [10, 15]
    assert report["cycles"][1]["change_from_previous_daily_import_percent"] == 50
    assert report["cycles"][0]["itemized_cost_usd_by_kind"]["energy"] == 100
    assert report["basis"] == "observed_utility_meter_purchases_not_native_building_load"
    assert all(item["estimated_savings_usd"] is None for item in report["recommendations"])
    assert any(item["kind"] == "review_usage_change" for item in report["recommendations"])
    with pytest.raises(ValueError, match="overlap"):
        analyze_bills([first, first])


def test_backend_api_extract_review_analyze_without_storing_pdf(tmp_path):
    from src.local_web.runtime import Application
    from src.local_web.server import make_wsgi_app

    app = Application(tmp_path, embedded_worker=False)
    wsgi = make_wsgi_app(app, 8765)
    def call(path, body=None, token=""):
        payload = json.dumps(body).encode() if body is not None else b""
        environ = {"REQUEST_METHOD": "POST" if body is not None else "GET", "PATH_INFO": path,
                   "QUERY_STRING": "", "HTTP_HOST": "127.0.0.1:8765", "wsgi.url_scheme": "http",
                   "wsgi.input": BytesIO(payload), "CONTENT_LENGTH": str(len(payload)),
                   "CONTENT_TYPE": "application/json", "HTTP_X_STUDY_TOKEN": token}
        details = {}
        def start(status, headers):
            details["status"] = int(status.split()[0])
            details["headers"] = dict(headers)
        content = b"".join(wsgi(environ, start))
        return details["status"], json.loads(content), details["headers"]
    try:
        _, session, _ = call("/api/session")
        pdf = _pdf(["Electric Usage", "Utility: Example Electric", "Rate Schedule: R-1",
                    "01/01/2026 to 01/30/2026 (30 billing days)",
                    "Total Usage 300 kWh", "Total Electric Charges $100.00"])
        status, draft, headers = call("/api/v1/bills/extract",
                                      {"pdf_base64": base64.b64encode(pdf).decode()}, session["token"])
        assert status == 200 and headers["Cache-Control"] == "no-store"
        assert draft["fields"]["meter_import_kwh"]["value"] == 300
        assert draft["fields"]["current_electric_charges"]["value"] == 100
        assert draft["fields"]["delivery_utility"]["value"] == "Example Electric"
        assert draft["fields"]["billing_plan"]["value"] == "R-1"
        assert not list(tmp_path.rglob("*.pdf"))
        status, reviewed, _ = call("/api/v1/bills/review", {"draft": draft, "corrections": {}, "approve": True}, session["token"])
        assert status == 200 and reviewed["approved"] is True
        status, analysis, _ = call("/api/v1/bills/analyze", {"bills": [reviewed]}, session["token"])
        assert status == 200 and analysis["cycles"][0]["meter_import_kwh_per_day"] == 10
        status, error, _ = call("/api/v1/bills/extract", {"pdf_base64": "not-valid"}, session["token"])
        assert status == 400 and "base64" in error["error"]
        assert call("/api/v1/bills/extract", {"pdf_base64": "not-valid"})[0] == 403
    finally:
        app.close()
