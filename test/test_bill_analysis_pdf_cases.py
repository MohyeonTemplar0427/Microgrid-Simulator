"""End-to-end extraction from five fictional, one-month PDF statements."""
from __future__ import annotations

import json
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from io import BytesIO

import pytest
from pypdf import PdfWriter

from src.bill_analysis import analyze_bills, apply_corrections, extract_bill, read_interval_records
from src.bill_analysis.pdf import PDFExtractionError
from tools.generate_synthetic_bill_pdfs import RATES, build_case, interval_csv


CASES = Path(__file__).parent / "fixtures" / "synthetic_bills"
EXPECTED = json.loads((CASES / "expected.json").read_text())


def _text_pdf(lines: list[str]) -> bytes:
    """Build a one-page text PDF without a test-time authoring dependency."""
    commands = ["BT /F1 11 Tf 40 740 Td"]
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


@lru_cache(maxsize=5)
def _case_pdf(filename: str) -> bytes:
    case = build_case(EXPECTED[filename]["minutes"])
    lines = [
        "Details of Sample Grid Electric Delivery Charges",
        "03/01/2026 to 03/31/2026 (31 billing days)",
        f"Rate Schedule: {case['tariff']}",
        f"Interval Resolution: {'1 hour' if case['minutes'] == 60 else str(case['minutes']) + ' minutes'}",
        f"Reported Intervals: {case['interval_count']:,}",
        "Time Zone: America/Los_Angeles",
        f"Maximum Demand: {case['maximum_demand_kw']:.3f} kW",
        f"Total Exported Energy {case['export_kwh']:.3f} kWh",
    ]
    for period, rate in RATES.items():
        lines.append(f"{period} {case['tou_kwh'][period]:.3f} kWh @ ${rate:.5f} ${case['energy_charges'][period]:.2f}")
    lines.extend((f"Demand Charge ${case['demand_charge']:.2f}",
                  f"Customer Charge ${case['customer_charge']:.2f}",
                  f"Export Credits -${case['export_credit']:.2f}",
                  f"Total Usage {case['meter_import_kwh']:.3f} kWh",
                  f"Total Sample Grid Electric Delivery Charges ${case['electric_charges_usd']:.2f}",
                  f"Total Amount Due ${case['electric_charges_usd']:.2f}"))
    writer = PdfWriter()
    writer.append(BytesIO(_text_pdf(lines)))
    writer.add_attachment("meter_intervals.csv", interval_csv(case))
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.mark.parametrize("filename", sorted(EXPECTED))
def test_monthly_pdf_extracts_tou_demand_exports_credit_and_interval_metadata(filename):
    expected = EXPECTED[filename]
    draft = extract_bill(_case_pdf(filename))
    fields = draft["fields"]
    assert len(draft["pages"]) == 1
    assert {page["method"] for page in draft["pages"]} == {"embedded_text"}
    assert not draft["issues"]
    for name, value in {
        "delivery_utility": expected["utility"], "billing_plan": expected["tariff"],
        "period_start": expected["period_start"], "period_end": expected["period_end"],
        "billing_days": expected["billing_days"],
        "meter_import_kwh": expected["meter_import_kwh"],
        "maximum_demand_kw": expected["maximum_demand_kw"],
        "export_kwh": expected["export_kwh"],
        "export_credit": expected["export_credit_usd"],
        "current_electric_charges": expected["electric_charges_usd"],
        "interval_minutes": expected["minutes"],
        "reported_interval_count": expected["interval_count"],
    }.items():
        assert fields[name]["value"] == value, name
        assert fields[name]["evidence"]
        assert fields[name]["status"] == "extracted"
    rows = draft["services"][0]["line_items"]
    for period, kwh in expected["tou_kwh"].items():
        row = next(row for row in rows if row["description"] == period)
        assert row["kind"] == "energy"
        assert row["quantity_kwh"] == kwh
        assert row["evidence"][0]["page"] == 1
    assert sum(row["amount"] for row in rows) == pytest.approx(expected["electric_charges_usd"])
    assert sum(expected["tou_kwh"].values()) == pytest.approx(expected["meter_import_kwh"])
    summary = draft["interval_summary"]
    assert summary["source_attachment_sha256"] == expected["interval_attachment_sha256"]
    assert summary["record_count"] == expected["interval_count"]
    assert summary["tou_kwh"] == pytest.approx(expected["tou_kwh"], abs=.001)
    assert summary["meter_import_kwh"] == pytest.approx(expected["meter_import_kwh"], abs=.001)
    assert summary["export_kwh"] == pytest.approx(expected["export_kwh"], abs=.001)
    assert summary["maximum_demand_kw"] == pytest.approx(expected["maximum_demand_kw"], abs=.001)
    assert summary["export_credit_usd"] == pytest.approx(expected["export_credit_usd"], abs=.01)
    reviewed = apply_corrections(draft, {}, approve=True)
    report = analyze_bills([reviewed])
    assert report["cycles"][0]["reported_interval_minutes"] == expected["minutes"]
    assert report["cycles"][0]["reported_interval_count"] == expected["interval_count"]
    assert report["cycles"][0]["interval_summary"]["record_count"] == expected["interval_count"]
    assert all(item["estimated_savings_usd"] is None for item in report["recommendations"])


@pytest.mark.parametrize("filename", sorted(EXPECTED))
def test_full_timestamped_records_independently_reproduce_fictional_bill(filename):
    expected = EXPECTED[filename]
    records = read_interval_records(_case_pdf(filename), minutes=expected["minutes"])
    assert len(records) == expected["interval_count"]
    assert records[0]["timestamp_start"].isoformat() == "2026-03-01T00:00:00-08:00"
    assert records[-1]["timestamp_start"].date().isoformat() == "2026-03-31"
    spring_forward = [record for record in records if record["timestamp_start"].date().isoformat() == "2026-03-08"]
    assert len(spring_forward) == 23 * 60 // expected["minutes"]
    tou = {name: sum((record["import_kwh"] for record in records if record["tou_period"] == name),
                     Decimal("0")) for name in ("Peak", "Part Peak", "Off Peak")}
    imported = sum((record["import_kwh"] for record in records), Decimal("0"))
    exported = sum((record["export_kwh"] for record in records), Decimal("0"))
    maximum = max(record["interval_demand_kw"] for record in records)
    credit = sum((record["export_credit_usd"] for record in records), Decimal("0"))
    milli, cent = Decimal("0.001"), Decimal("0.01")
    rounded = lambda value, unit: value.quantize(unit, rounding=ROUND_HALF_UP)
    assert float(rounded(imported, milli)) == expected["meter_import_kwh"]
    assert float(rounded(exported, milli)) == expected["export_kwh"]
    assert float(rounded(maximum, milli)) == expected["maximum_demand_kw"]
    assert float(rounded(credit, cent)) == expected["export_credit_usd"]
    rates = {"Peak": Decimal("0.31000"), "Part Peak": Decimal("0.22000"),
             "Off Peak": Decimal("0.15000")}
    energy_charges = sum((rounded(rounded(tou[name], milli) * rate, cent)
                          for name, rate in rates.items()), Decimal("0"))
    synthetic_demand_charge = rounded(rounded(maximum, milli) * Decimal("8.00"), cent)
    reproduced_bill = energy_charges + synthetic_demand_charge + Decimal("18.50") + rounded(credit, cent)
    assert float(reproduced_bill) == expected["electric_charges_usd"]


def test_interval_resolution_and_printed_bill_mismatches_are_rejected():
    source = _case_pdf("synthetic_bill_march_2026_5min.pdf")
    with pytest.raises(PDFExtractionError, match="timestamps have a gap|average demand kW disagree"):
        read_interval_records(source, minutes=10)
    draft = extract_bill(source)
    with pytest.raises(ValueError, match="interval_reconciliation"):
        apply_corrections(draft, {"fields.meter_import_kwh": 810.0}, approve=True)


def test_march_dst_interval_counts_and_distinct_demand_measurements():
    for minutes in (5, 10, 15, 30, 60):
        case = EXPECTED[f"synthetic_bill_march_2026_{minutes}min.pdf"]
        assert case["interval_count"] == (31 * 24 - 1) * 60 // minutes
    five = EXPECTED["synthetic_bill_march_2026_5min.pdf"]
    hourly = EXPECTED["synthetic_bill_march_2026_60min.pdf"]
    assert five["meter_import_kwh"] == hourly["meter_import_kwh"]
    assert five["maximum_demand_kw"] > hourly["maximum_demand_kw"]
    assert five["electric_charges_usd"] > hourly["electric_charges_usd"]


def test_same_month_scenarios_are_not_treated_as_sequential_customer_bills():
    five = apply_corrections(extract_bill(_case_pdf("synthetic_bill_march_2026_5min.pdf")),
                             {}, approve=True)
    hourly = apply_corrections(extract_bill(_case_pdf("synthetic_bill_march_2026_60min.pdf")),
                               {}, approve=True)
    with pytest.raises(ValueError, match="overlap"):
        analyze_bills([five, hourly])
