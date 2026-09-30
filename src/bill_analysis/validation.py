"""Review, correction audit, and arithmetic checks for observed bill data."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import math
import re


REQUIRED = ("period_start", "period_end", "billing_days", "meter_import_kwh")
NUMERIC_FIELDS = {"billing_days", "meter_import_kwh", "current_electric_charges", "statement_amount_due",
                  "maximum_demand_kw", "export_kwh", "export_credit", "total_charges",
                  "interval_minutes", "reported_interval_count"}
DATE_FIELDS = {"period_start", "period_end"}
NONNEGATIVE = {"billing_days", "meter_import_kwh", "current_electric_charges", "maximum_demand_kw", "export_kwh"}
EXPECTED_UNITS = {"billing_days": "days", "meter_import_kwh": "kWh",
                  "current_electric_charges": "USD", "statement_amount_due": "USD",
                  "maximum_demand_kw": "kW", "export_kwh": "kWh", "export_credit": "USD",
                  "total_charges": "USD", "interval_minutes": "minutes",
                  "reported_interval_count": "intervals"}


def issue(code: str, severity: str, message: str, path: str = "") -> dict:
    return {"code": code, "severity": severity, "message": message, "path": path}


def _value(fields: dict, name: str):
    record = fields.get(name) if isinstance(fields, dict) else None
    return record.get("value") if isinstance(record, dict) else None


def _check_field(fields: dict, name: str, path: str, problems: list) -> None:
    record = fields.get(name)
    if not isinstance(record, dict):
        problems.append(issue("missing_field", "error" if name in REQUIRED else "warning",
                              f"{name} is missing.", path))
        return
    status = record.get("status")
    value = record.get("value")
    if name in EXPECTED_UNITS and record.get("unit") != EXPECTED_UNITS[name]:
        problems.append(issue("invalid_unit", "error", f"{name} must use {EXPECTED_UNITS[name]}.", path))
    if not isinstance(status, str):
        problems.append(issue("invalid_status", "error", f"{name} review status is invalid.", path))
        return
    if status in {"missing", "ambiguous"} or value is None:
        problems.append(issue(status if status in {"missing", "ambiguous"} else "missing_field",
                              "error" if name in REQUIRED else "warning", f"Review {name}.", path))
        return
    if name in NUMERIC_FIELDS:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            problems.append(issue("invalid_number", "error", f"{name} must be a finite number.", path))
        elif name in NONNEGATIVE and value < 0:
            problems.append(issue("invalid_number", "error", f"{name} cannot be negative.", path))
        elif name == "billing_days" and (int(value) != value or value < 1):
            problems.append(issue("invalid_days", "error", "Billing days must be a positive whole number.", path))
        elif name in {"interval_minutes", "reported_interval_count"} and (int(value) != value or value < 1 or
                (name == "interval_minutes" and value > 1440)):
            problems.append(issue("invalid_interval_metadata", "error",
                                  f"{name} must be a positive whole number in range.", path))
    elif name in DATE_FIELDS:
        try:
            date.fromisoformat(value)
        except (TypeError, ValueError):
            problems.append(issue("invalid_date", "error", f"{name} must be an ISO calendar date.", path))
    elif not isinstance(value, str) or not value.strip() or len(value) > 160:
        problems.append(issue("invalid_text", "error", f"{name} must be short nonempty text.", path))


def validate_draft(draft: dict) -> list[dict]:
    if not isinstance(draft, dict) or draft.get("schema_version") != 1:
        raise ValueError("Unsupported bill-draft schema.")
    fields = draft.get("fields")
    services = draft.get("services")
    if not isinstance(fields, dict) or not isinstance(services, list):
        raise ValueError("Bill draft must contain fields and services.")
    if any(not isinstance(record, dict) for record in fields.values()):
        raise ValueError("Bill fields must be reviewable objects.")
    if not isinstance(draft.get("source_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", draft["source_sha256"]):
        raise ValueError("Bill draft needs a PDF source hash.")
    if len(services) > 8 or not isinstance(draft.get("pages"), list) or len(draft["pages"]) > 12:
        raise ValueError("Bill draft exceeds its page or service-section limit.")
    problems = []
    for page in draft["pages"]:
        if not isinstance(page, dict) or not isinstance(page.get("page"), int) or page.get("method") not in {
                "embedded_text", "local_ocr", "unreadable_scan"}:
            raise ValueError("Bill page metadata is invalid.")
        if page["method"] == "unreadable_scan":
            problems.append(issue("unreadable_scan_page", "warning",
                                  f"Page {page['page']} yielded no OCR text; inspect the original PDF for missing charges.",
                                  f"pages.{page['page']}"))
    for name in REQUIRED + ("current_electric_charges", "delivery_utility", "billing_plan"):
        _check_field(fields, name, f"fields.{name}", problems)
    # Statement amount due may include gas and prior balances. Demand, solar
    # exports and export credits are optional observations, never inferred.
    for name in ("statement_amount_due", "maximum_demand_kw", "export_kwh", "export_credit",
                 "interval_minutes", "reported_interval_count", "time_zone"):
        if _value(fields, name) is not None:
            _check_field(fields, name, f"fields.{name}", problems)
    start, end, days = (_value(fields, name) for name in ("period_start", "period_end", "billing_days"))
    try:
        actual = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
        if actual < 1:
            problems.append(issue("reversed_period", "error", "Billing end date precedes start date.", "fields.period_end"))
        elif isinstance(days, (int, float)) and actual != days:
            problems.append(issue("billing_days_mismatch", "error",
                                  "Printed billing days differ from inclusive service dates.", "fields.billing_days"))
    except (TypeError, ValueError):
        pass
    roles = [(service.get("provider"), service.get("role")) for service in services
             if isinstance(service, dict) and isinstance(service.get("provider"), str)
             and isinstance(service.get("role"), str)]
    if len(roles) != len(set(roles)):
        problems.append(issue("duplicate_service_section", "error",
                              "Repeated provider sections need meter/account review before totals are combined.", "services"))
    for index, service in enumerate(services):
        prefix = f"services.{index}"
        if (not isinstance(service, dict) or not isinstance(service.get("role"), str)
                or service["role"] not in {"delivery", "generation"}):
            problems.append(issue("invalid_service", "error", "Service role must be delivery or generation.", prefix))
            continue
        if not isinstance(service.get("fields"), dict):
            problems.append(issue("invalid_service_fields", "error", "Service fields must be an object.", prefix))
            continue
        if (not isinstance(service.get("provider"), str) or not 1 <= len(service["provider"]) <= 160
                or any(not isinstance(record, dict) for record in service["fields"].values())):
            problems.append(issue("invalid_service_fields", "error", "Service provider or fields are invalid.", prefix))
            continue
        for name in ("period_start", "period_end", "billing_days", "meter_import_kwh", "total_charges", "tariff"):
            _check_field(service.get("fields", {}), name, f"{prefix}.fields.{name}", problems)
        subfields = service.get("fields", {})
        if (_value(subfields, "period_start") is not None and start is not None
                and _value(subfields, "period_start") != start) or (
                _value(subfields, "period_end") is not None and end is not None
                and _value(subfields, "period_end") != end):
            problems.append(issue("service_period_mismatch", "error",
                                  "Electric service sections show different billing periods.", prefix))
        usage = _value(subfields, "meter_import_kwh")
        meter_usage = _value(fields, "meter_import_kwh")
        if isinstance(usage, (int, float)) and isinstance(meter_usage, (int, float)) and abs(usage-meter_usage) > .005:
            problems.append(issue("service_usage_mismatch", "error",
                                  "Delivery and generation sections report different meter purchases.", prefix))
        rows = service.get("line_items", [])
        if not isinstance(rows, list) or len(rows) > 100:
            problems.append(issue("invalid_line_items", "error", "Line items must be a list of at most 100 entries.", prefix))
            continue
        amounts = []
        for item_index, row in enumerate(rows):
            amount = row.get("amount") if isinstance(row, dict) else None
            if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount):
                problems.append(issue("invalid_line_item", "error", "Line-item amount must be finite.",
                                      f"{prefix}.line_items.{item_index}.amount"))
            else:
                amounts.append(amount)
            if isinstance(row, dict) and (not isinstance(row.get("description"), str)
                    or not 1 <= len(row["description"]) <= 160
                    or not isinstance(row.get("kind"), str)
                    or row["kind"] not in {"energy", "demand", "fixed", "tax", "credit", "adjustment"}
                    or row.get("currency") != "USD"):
                problems.append(issue("invalid_line_item", "error", "Line-item description or kind is invalid.",
                                      f"{prefix}.line_items.{item_index}"))
            if isinstance(row, dict) and "quantity_kwh" in row:
                quantity = row["quantity_kwh"]
                if (isinstance(quantity, bool) or not isinstance(quantity, (int, float))
                        or not math.isfinite(quantity) or quantity < 0):
                    problems.append(issue("invalid_quantity", "error", "Line-item kWh must be finite and nonnegative.",
                                          f"{prefix}.line_items.{item_index}.quantity_kwh"))
        total = _value(subfields, "total_charges")
        if isinstance(total, (int, float)) and amounts and len(amounts) == len(rows):
            tolerance = .005 * (len(amounts) + 1) + .001
            if abs(sum(amounts) - total) > tolerance:
                problems.append(issue("charge_reconciliation", "warning",
                                      f"Listed charges differ from the section total by ${abs(sum(amounts)-total):.2f}; review omitted or duplicated items.", prefix))
    totals = [_value(service.get("fields", {}), "total_charges") for service in services if isinstance(service, dict)]
    electric_total = _value(fields, "current_electric_charges")
    if totals and all(isinstance(value, (int, float)) for value in totals) and isinstance(electric_total, (int, float)):
        if abs(sum(totals) - electric_total) > .011:
            problems.append(issue("electric_total_mismatch", "warning",
                                  "Electric service totals do not add to current electric charges.", "fields.current_electric_charges"))
    interval_summary = draft.get("interval_summary")
    if interval_summary is not None:
        if not isinstance(interval_summary, dict) or not isinstance(interval_summary.get("tou_kwh"), dict):
            raise ValueError("Attached meter interval summary is invalid.")
        checks = (("reported_interval_count", "record_count", 0),
                  ("interval_minutes", "interval_minutes", 0),
                  ("meter_import_kwh", "meter_import_kwh", .002),
                  ("maximum_demand_kw", "maximum_demand_kw", .001),
                  ("export_kwh", "export_kwh", .002),
                  ("export_credit", "export_credit_usd", .011))
        for field_name, summary_name, tolerance in checks:
            printed = _value(fields, field_name)
            measured = interval_summary.get(summary_name)
            if (isinstance(printed, (int, float)) and not isinstance(printed, bool)
                    and isinstance(measured, (int, float)) and math.isfinite(measured)
                    and abs(printed - measured) > tolerance):
                problems.append(issue("interval_reconciliation", "error",
                                      f"Printed {field_name} disagrees with the attached meter records.",
                                      f"fields.{field_name}"))
        delivery_rows = [row for service in services if isinstance(service, dict) and service.get("role") == "delivery"
                         and isinstance(service.get("line_items"), list)
                         for row in service["line_items"] if isinstance(row, dict)]
        for period, measured in interval_summary["tou_kwh"].items():
            printed = sum(row["quantity_kwh"] for row in delivery_rows
                          if row.get("description") == period and isinstance(row.get("quantity_kwh"), (int, float)))
            if isinstance(measured, (int, float)) and math.isfinite(measured) and abs(printed - measured) > .002:
                problems.append(issue("interval_reconciliation", "error",
                                      f"Printed {period} kWh disagrees with the attached meter records.",
                                      "services"))
    # Statement amount due can include gas, prior balance and payments. It is
    # deliberately not reconciled against current electricity charges.
    return problems


def apply_corrections(draft: dict, corrections: dict, *, approve: bool = False) -> dict:
    validate_draft(draft)
    if not isinstance(corrections, dict):
        raise ValueError("Corrections must map field paths to reviewed values.")
    if len(corrections) > 200:
        raise ValueError("Supply at most 200 corrections at a time.")
    revised = deepcopy(draft)
    revised.pop("approved", None)
    revised.pop("issues", None)
    if not isinstance(revised.setdefault("corrections", []), list):
        raise ValueError("Correction history must be a list.")
    for path, submitted in corrections.items():
        if not isinstance(path, str):
            raise ValueError("Correction paths must be strings.")
        if isinstance(submitted, dict):
            if set(submitted) - {"value", "reason"} or "value" not in submitted:
                raise ValueError("A correction may contain only value and reason.")
            value, reason = submitted["value"], submitted.get("reason", "")
        else:
            value, reason = submitted, ""
        if not isinstance(reason, str) or len(reason) > 200:
            raise ValueError("Correction reason must be short text.")
        parts = path.split(".")
        if len(parts) == 2 and parts[0] == "fields" and parts[1] in revised["fields"]:
            target = revised["fields"][parts[1]]
            previous = target["value"]
            target["value"], target["status"] = value, "corrected"
        elif (len(parts) == 4 and parts[0] == "services" and parts[1].isdigit()
              and parts[2] == "fields"):
            try:
                target = revised["services"][int(parts[1])]["fields"][parts[3]]
            except (IndexError, KeyError, TypeError) as exc:
                raise ValueError(f"Unknown correction path: {path}.") from exc
            previous = target["value"]
            target["value"], target["status"] = value, "corrected"
        elif (len(parts) == 5 and parts[0] == "services" and parts[1].isdigit()
              and parts[2] == "line_items" and parts[3].isdigit() and parts[4] in {"amount", "description", "kind", "quantity_kwh"}):
            try:
                target = revised["services"][int(parts[1])]["line_items"][int(parts[3])]
            except (IndexError, KeyError, TypeError) as exc:
                raise ValueError(f"Unknown correction path: {path}.") from exc
            previous = target.get(parts[4])
            target[parts[4]] = value
        elif len(parts) == 3 and parts[0] == "services" and parts[1].isdigit() and parts[2] in {"provider", "line_items"}:
            try:
                target = revised["services"][int(parts[1])]
            except (IndexError, TypeError) as exc:
                raise ValueError(f"Unknown correction path: {path}.") from exc
            previous = deepcopy(target[parts[2]])
            target[parts[2]] = value
        else:
            raise ValueError(f"Unknown correction path: {path}.")
        revised["corrections"].append({"path": path, "previous": previous, "value": value,
                                        "reason": reason, "source": "user"})
    revised["issues"] = validate_draft(revised)
    if approve:
        blockers = [item for item in revised["issues"] if item["severity"] == "error"]
        if blockers:
            raise ValueError("Resolve required bill fields and validation errors before approval: "
                             + ", ".join(sorted({item["code"] for item in blockers})))
        revised["approved"] = True
    return revised
