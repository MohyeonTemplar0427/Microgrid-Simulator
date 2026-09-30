"""Read an explicitly attached meter interval CSV from a bill PDF.

This is a bounded format for measured records, not a reconstruction of load
from a monthly bill. Timestamps carry UTC offsets so DST repetitions remain
distinct. A returned summary retains the attachment hash as provenance.
"""
from __future__ import annotations

import csv
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
from io import BytesIO, StringIO
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pypdf import PdfReader

from .pdf import MAX_PDF_BYTES, PDFExtractionError


ATTACHMENT_NAME = "meter_intervals.csv"
HEADERS = ("timestamp_start", "import_kwh", "export_kwh", "interval_demand_kw",
           "tou_period", "export_credit_usd")
MAX_ATTACHMENT_BYTES = 2 * 1024 * 1024
MAX_INTERVAL_ROWS = 20_000


def read_interval_records(content: bytes, *, minutes: int, required: bool = True) -> tuple[dict, ...]:
    """Return every validated record from the PDF's named CSV attachment.

    The complete series must have one timestamp per `minutes` in UTC order.
    `interval_demand_kw` is the average import kW for that interval, checked
    against import kWh / interval hours; it is not an instantaneous peak.
    """
    if not isinstance(content, bytes) or not content.startswith(b"%PDF-") or len(content) > MAX_PDF_BYTES:
        raise PDFExtractionError("Supply a PDF within the analysis size limit.")
    try:
        attachments = PdfReader(BytesIO(content), strict=False).attachments
    except Exception as exc:
        raise PDFExtractionError("Could not inspect PDF meter attachments.") from exc
    if ATTACHMENT_NAME not in attachments:
        if required:
            raise PDFExtractionError("The PDF has no meter_intervals.csv attachment.")
        return ()
    if isinstance(minutes, bool) or not isinstance(minutes, int) or not 1 <= minutes <= 1440:
        raise PDFExtractionError("A positive whole-number interval resolution is required.")
    payload = attachments[ATTACHMENT_NAME]
    if isinstance(payload, list):
        if len(payload) != 1:
            raise PDFExtractionError("The PDF contains multiple meter interval attachments.")
        payload = payload[0]
    if not isinstance(payload, bytes) or len(payload) > MAX_ATTACHMENT_BYTES:
        raise PDFExtractionError("The meter interval attachment is invalid or exceeds 2 MiB.")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise PDFExtractionError("The meter interval attachment must be UTF-8 CSV.") from exc
    reader = csv.DictReader(StringIO(text, newline=""))
    if tuple(reader.fieldnames or ()) != HEADERS:
        raise PDFExtractionError("The meter interval CSV headers do not match the supported schema.")
    records = []
    previous_utc = None
    step = timedelta(minutes=minutes)
    for row in reader:
        if len(records) >= MAX_INTERVAL_ROWS or None in row or any(value is None for value in row.values()):
            raise PDFExtractionError("The meter interval CSV has too many or malformed rows.")
        try:
            stamp = datetime.fromisoformat(row["timestamp_start"])
            if stamp.tzinfo is None or stamp.utcoffset() is None:
                raise ValueError("missing offset")
            values = {name: Decimal(row[name]) for name in (
                "import_kwh", "export_kwh", "interval_demand_kw", "export_credit_usd")}
        except (ValueError, TypeError, InvalidOperation) as exc:
            raise PDFExtractionError("The meter interval CSV has an invalid timestamp or number.") from exc
        if (any(not value.is_finite() for value in values.values())
                or any(values[name] < 0 for name in ("import_kwh", "export_kwh", "interval_demand_kw"))
                or not 1 <= len(row["tou_period"]) <= 64):
            raise PDFExtractionError("The meter interval CSV has invalid quantities or TOU labels.")
        expected_kw = values["import_kwh"] * Decimal(60) / Decimal(minutes)
        if abs(expected_kw - values["interval_demand_kw"]) > Decimal("0.00001"):
            raise PDFExtractionError("An interval's kWh and average demand kW disagree.")
        stamp_utc = stamp.astimezone(timezone.utc)
        if previous_utc is not None and stamp_utc - previous_utc != step:
            raise PDFExtractionError("Meter interval timestamps have a gap, duplicate, or inconsistent resolution.")
        records.append({"timestamp_start": stamp, **values, "tou_period": row["tou_period"]})
        previous_utc = stamp_utc
    if not records:
        raise PDFExtractionError("The meter interval CSV contains no records.")
    return tuple(records)


def summarize_interval_records(records: tuple[dict, ...], *, minutes: int, period_start: str,
                               period_end: str, time_zone: str, attachment_sha256: str) -> dict:
    """Validate complete local-month coverage and aggregate retrieved records."""
    if not records:
        raise PDFExtractionError("No meter interval records were supplied.")
    try:
        zone = ZoneInfo(time_zone)
        first_day = date.fromisoformat(period_start)
        last_day = date.fromisoformat(period_end)
    except (TypeError, ValueError, ZoneInfoNotFoundError) as exc:
        raise PDFExtractionError("The bill needs valid service dates and an IANA time zone for interval review.") from exc
    expected_first = datetime.combine(first_day, time.min, tzinfo=zone).astimezone(timezone.utc)
    expected_stop = datetime.combine(last_day + timedelta(days=1), time.min, tzinfo=zone).astimezone(timezone.utc)
    step = timedelta(minutes=minutes)
    if (records[0]["timestamp_start"].astimezone(timezone.utc) != expected_first
            or records[-1]["timestamp_start"].astimezone(timezone.utc) + step != expected_stop):
        raise PDFExtractionError("Attached meter intervals do not cover the complete printed billing period.")
    for record in records:
        stamp = record["timestamp_start"]
        if stamp.astimezone(zone).utcoffset() != stamp.utcoffset():
            raise PDFExtractionError("A meter timestamp has an offset inconsistent with the printed time zone.")
    buckets = {}
    for record in records:
        key = record["tou_period"]
        buckets[key] = buckets.get(key, Decimal("0")) + record["import_kwh"]
    return {
        "source_attachment_sha256": attachment_sha256,
        "record_count": len(records), "interval_minutes": minutes,
        "first_timestamp": records[0]["timestamp_start"].isoformat(),
        "last_timestamp": records[-1]["timestamp_start"].isoformat(),
        "meter_import_kwh": float(sum((r["import_kwh"] for r in records), Decimal("0"))),
        "export_kwh": float(sum((r["export_kwh"] for r in records), Decimal("0"))),
        "maximum_demand_kw": float(max(r["interval_demand_kw"] for r in records)),
        "export_credit_usd": float(sum((r["export_credit_usd"] for r in records), Decimal("0"))),
        "tou_kwh": {key: float(value) for key, value in buckets.items()},
    }


def read_interval_summary(content: bytes, *, minutes: int, period_start: str,
                          period_end: str, time_zone: str, required: bool = True) -> dict | None:
    records = read_interval_records(content, minutes=minutes, required=required)
    if not records:
        return None
    attachment = PdfReader(BytesIO(content), strict=False).attachments[ATTACHMENT_NAME]
    if isinstance(attachment, list):
        attachment = attachment[0]
    return summarize_interval_records(records, minutes=minutes, period_start=period_start,
                                      period_end=period_end, time_zone=time_zone,
                                      attachment_sha256=hashlib.sha256(attachment).hexdigest())
