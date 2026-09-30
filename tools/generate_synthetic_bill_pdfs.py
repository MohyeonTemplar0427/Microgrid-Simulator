"""Build five reproducible, fictional March 2026 bill PDFs for parser checks.

Run with the Codex bundled Python (which includes ReportLab). Tests construct
equivalent PDFs in memory from this deterministic profile, so no generated PDF
must be committed. No utility's filed rates are represented.
"""
from __future__ import annotations

from collections import defaultdict
import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import csv
import hashlib
from io import StringIO
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from pypdf import PdfWriter


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf"
FIXTURES = ROOT / "test" / "fixtures" / "synthetic_bills"
MONTH_START = datetime(2026, 3, 1, tzinfo=ZoneInfo("America/Los_Angeles"))
MONTH_END = datetime(2026, 4, 1, tzinfo=ZoneInfo("America/Los_Angeles"))
CENT = Decimal("0.01")
MILLI = Decimal("0.001")
RATES = {"Peak": Decimal("0.31000"), "Part Peak": Decimal("0.22000"),
         "Off Peak": Decimal("0.15000")}


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def energy(value: Decimal) -> Decimal:
    return value.quantize(MILLI, rounding=ROUND_HALF_UP)


def build_case(minutes: int) -> dict:
    duration = Decimal(minutes) / Decimal(60)
    base_duration = Decimal(5) / Decimal(60)
    instant = MONTH_START.astimezone(timezone.utc)
    stop = MONTH_END.astimezone(timezone.utc)
    usage = defaultdict(lambda: Decimal("0"))
    days = defaultdict(lambda: {"count": 0, "import": Decimal("0"),
                                "export": Decimal("0"), "max_kw": Decimal("0")})
    export = Decimal("0")
    maximum = Decimal("0")
    count = 0
    records = []
    while instant < stop:
        local = instant.astimezone(MONTH_START.tzinfo)
        hour = local.hour
        interval_import = Decimal("0")
        interval_export = Decimal("0")
        # One physical 5-minute reference profile is averaged into each meter
        # resolution. Energy stays comparable; the measured demand peak changes.
        for offset in range(0, minutes, 5):
            sample = (instant + timedelta(minutes=offset)).astimezone(MONTH_START.tzinfo)
            sample_hour = sample.hour
            native = (Decimal("1.15") + Decimal(sample.day % 5) * Decimal("0.05")
                      + (Decimal("0.55") if 16 <= sample_hour < 21 else Decimal("0"))
                      + (Decimal("0.25") if 7 <= sample_hour < 9 else Decimal("0"))
                      + (Decimal("0.80") if 16 <= sample_hour < 21 and sample.minute in {15, 20} else Decimal("0")))
            solar = (Decimal("2.35") if 10 <= sample_hour < 15 else
                     Decimal("0.90") if 9 <= sample_hour < 10 or 15 <= sample_hour < 16 else Decimal("0"))
            if 10 <= sample_hour < 15 and sample.minute in {30, 35}:
                solar += Decimal("0.60")
            interval_import += max(native - solar, Decimal("0")) * base_duration
            interval_export += max(solar - native, Decimal("0")) * base_duration
        import_kw = interval_import / duration
        period = "Peak" if 16 <= hour < 21 else "Part Peak" if 9 <= hour < 16 or 21 <= hour < 22 else "Off Peak"
        usage[period] += interval_import
        export += interval_export
        maximum = max(maximum, import_kw)
        day = days[local.date().isoformat()]
        day["count"] += 1
        day["import"] += interval_import
        day["export"] += interval_export
        day["max_kw"] = max(day["max_kw"], import_kw)
        records.append({
            "timestamp_start": local.isoformat(), "import_kwh": f"{interval_import:.9f}",
            "export_kwh": f"{interval_export:.9f}",
            "interval_demand_kw": f"{import_kw:.6f}", "tou_period": period,
            "export_credit_usd": f"{-interval_export * Decimal('0.06500'):.9f}",
        })
        instant += timedelta(minutes=minutes)
        count += 1
    shown_usage = {period: energy(usage[period]) for period in RATES}
    shown_export = energy(export)
    shown_maximum = energy(maximum)
    energy_charges = {period: money(shown_usage[period] * rate) for period, rate in RATES.items()}
    demand_charge = money(shown_maximum * Decimal("8.00"))
    customer_charge = Decimal("18.50")
    export_credit = money(shown_export * Decimal("0.06500"))
    total = sum(energy_charges.values()) + demand_charge + customer_charge - export_credit
    return {
        "minutes": minutes, "interval_count": count,
        "period_start": "2026-03-01", "period_end": "2026-03-31", "billing_days": 31,
        "timezone": "America/Los_Angeles", "utility": "Sample Grid",
        "tariff": "SYN-COM-TOU-D", "tou_kwh": {key: float(value) for key, value in shown_usage.items()},
        "meter_import_kwh": float(sum(shown_usage.values())),
        "maximum_demand_kw": float(shown_maximum), "export_kwh": float(shown_export),
        "export_credit_usd": float(-export_credit), "electric_charges_usd": float(total),
        "daily": [{"day": name, "intervals": value["count"],
                   "import_kwh": float(energy(value["import"])),
                   "export_kwh": float(energy(value["export"])),
                   "max_kw": float(value["max_kw"])} for name, value in sorted(days.items())],
        "energy_charges": energy_charges, "demand_charge": demand_charge,
        "customer_charge": customer_charge, "export_credit": export_credit,
        "records": records,
    }


def interval_csv(case: dict) -> bytes:
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=("timestamp_start", "import_kwh", "export_kwh",
                                                "interval_demand_kw", "tou_period", "export_credit_usd"),
                            lineterminator="\n")
    writer.writeheader()
    writer.writerows(case["records"])
    return stream.getvalue().encode("utf-8")


def draw_pdf(case: dict, path: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    pdf = canvas.Canvas(str(path), pagesize=letter, pageCompression=1)
    pdf.setTitle(f"Synthetic March 2026 electricity bill - {case['minutes']} minute intervals")
    width, height = letter

    def header(page: int, title: str) -> None:
        pdf.setFillColor(colors.HexColor("#143244"))
        pdf.rect(0, height - 92, width, 92, fill=1, stroke=0)
        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(45, height - 48, title)
        pdf.setFont("Helvetica", 10)
        pdf.drawString(45, height - 70, "FICTIONAL TEST DATA - NOT A UTILITY BILL")
        pdf.setFillColor(colors.HexColor("#526773"))
        pdf.setFont("Helvetica", 9)
        pdf.drawRightString(width - 45, 27, f"Page {page} of 2")

    header(1, "Synthetic electricity statement")
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(45, 675, "One-month billing cycle")
    pdf.setFont("Helvetica", 10)
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
    y = 650
    for line in lines:
        pdf.drawString(45, y, line)
        y -= 21
    pdf.setStrokeColor(colors.HexColor("#a8bac1"))
    pdf.line(45, y + 7, width - 45, y + 7)
    y -= 22
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(45, y, "Itemized electricity charges")
    y -= 25
    pdf.setFont("Helvetica", 10)
    for period, rate in RATES.items():
        pdf.drawString(45, y, f"{period} {case['tou_kwh'][period]:.3f} kWh @ ${rate:.5f} ${case['energy_charges'][period]:.2f}")
        y -= 21
    for line in (f"Demand Charge ${case['demand_charge']:.2f}",
                 f"Customer Charge ${case['customer_charge']:.2f}",
                 f"Export Credits -${case['export_credit']:.2f}"):
        pdf.drawString(45, y, line)
        y -= 21
    pdf.drawString(45, y, f"Total Usage {case['meter_import_kwh']:.3f} kWh")
    y -= 25
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(45, y, f"Total Sample Grid Electric Delivery Charges ${case['electric_charges_usd']:.2f}")
    y -= 25
    pdf.drawString(45, y, f"Total Amount Due ${case['electric_charges_usd']:.2f}")
    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(colors.HexColor("#526773"))
    pdf.drawString(45, 87, "Synthetic rates and profiles are invented for parser validation only.")
    pdf.drawString(45, 72, "All timestamped meter records are embedded as meter_intervals.csv.")
    pdf.drawString(45, 57, "The visible pages summarize the attached full-month interval record.")
    pdf.showPage()

    header(2, "Daily meter summary")
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(45, 679, "Service: March 1-31, 2026 (America/Los_Angeles); interval count reflects the DST change.")
    pdf.setFillColor(colors.HexColor("#eaf0f2"))
    pdf.rect(45, 644, width - 90, 24, fill=1, stroke=0)
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 9)
    positions = (51, 167, 265, 361, 463)
    for x, title in zip(positions, ("Day", "Intervals", "Import kWh", "Export kWh", "Max kW")):
        pdf.drawString(x, 652, title)
    y = 626
    pdf.setFont("Helvetica", 9)
    for index, row in enumerate(case["daily"]):
        if index % 2:
            pdf.setFillColor(colors.HexColor("#f4f7f8"))
            pdf.rect(45, y - 5, width - 90, 17, fill=1, stroke=0)
            pdf.setFillColor(colors.black)
        for x, value in zip(positions, (row["day"], str(row["intervals"]),
                                        f"{row['import_kwh']:.3f}", f"{row['export_kwh']:.3f}",
                                        f"{row['max_kw']:.3f}")):
            pdf.drawString(x, y, value)
        y -= 18
    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(colors.HexColor("#526773"))
    pdf.drawString(45, 52, "Daily figures are rounded for display; bill totals are calculated from the full interval series.")
    pdf.save()
    writer = PdfWriter()
    writer.append(str(path))
    writer.add_attachment("meter_intervals.csv", interval_csv(case))
    temporary = path.with_name(path.stem + ".building.pdf")
    with temporary.open("wb") as target:
        writer.write(target)
    temporary.replace(path)


def main(*, manifest_only: bool = False) -> None:
    if not manifest_only:
        OUTPUT.mkdir(parents=True, exist_ok=True)
    FIXTURES.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for minutes in (5, 10, 15, 30, 60):
        case = build_case(minutes)
        filename = f"synthetic_bill_march_2026_{minutes}min.pdf"
        if not manifest_only:
            draw_pdf(case, OUTPUT / filename)
        manifest[filename] = {key: value for key, value in case.items()
                              if key not in {"energy_charges", "demand_charge", "customer_charge", "export_credit", "records", "daily"}}
        manifest[filename]["interval_attachment_sha256"] = hashlib.sha256(interval_csv(case)).hexdigest()
    (FIXTURES / "expected.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Updated {len(manifest)} synthetic bill cases for {MONTH_START:%Y-%m}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-only", action="store_true", help="Update expected JSON without creating PDFs.")
    main(manifest_only=parser.parse_args().manifest_only)
