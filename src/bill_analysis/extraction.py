"""Conservative, evidence-linked extraction of observed electricity bills.

The parser recognizes explicit labels, not tariff rules. Unknown layouts yield
missing/ambiguous fields for review instead of plausible invented values.
"""
from __future__ import annotations

from datetime import date
import re

from .pdf import ExtractedDocument, PageText, extract_pages


DATE = r"\d{1,2}/\d{1,2}/\d{4}"
PERIOD = re.compile(rf"(?P<start>{DATE})\s+to\s+(?P<end>{DATE})\s*\((?P<days>\d+)\s+billing days?\)", re.I)
NUMBER = r"-?\$?\d[\d,]*\.\d{2}"
MONEY = re.compile(rf"(?<![\d.])({NUMBER})(?![\d.])(?=\s|$)")
ENERGY_ROW = re.compile(rf"^(?P<label>.+?)\s+(?P<kwh>\d[\d,]*\.\d+)\s*kWh\s*@\s*-?\$?\d[\d,]*\.\d+\s+(?P<amount>{NUMBER})(?=\s|$)", re.I)
USAGE = re.compile(r"\bTotal Usage\s+([\d,]+(?:\.\d+)?)\s*kWh\b", re.I)
SERVICE = re.compile(r"Details of\s+(.+?)\s+Electric\s+(Delivery|Generation)(?:\s+Charges)?", re.I)
TOTAL = re.compile(rf"^Total\s+(.+?)\s+Electric\s+(Delivery|Generation)\s+Charges\s+({NUMBER})\b", re.I)
DEMAND = re.compile(r"\b(?:Maximum|Billing|Billed) Demand\s*:?\s*([\d,]+(?:\.\d+)?)\s*kW\b", re.I)
EXPORT = re.compile(r"\b(?:Total\s+)?(?:Exported|Export) (?:Energy|Usage)?\s*:?\s*([\d,]+(?:\.\d+)?)\s*kWh\b", re.I)
EXPORT_CREDIT = re.compile(rf"\b(?:Export|Solar) Credits?\s+({NUMBER})\b", re.I)
INTERVAL_RESOLUTION = re.compile(r"\bInterval Resolution:\s*(\d+)\s*(minutes?|mins?|hours?|hrs?)\b", re.I)
INTERVAL_COUNT = re.compile(r"\bReported Intervals:\s*([\d,]+)\b", re.I)
TIME_ZONE = re.compile(r"\bTime Zone:\s*([A-Za-z0-9_+/.-]+)\b", re.I)
AMOUNT_DUE = re.compile(rf"\bTotal Amount Due(?:\s+by\s+{DATE})?\s+({NUMBER})\b", re.I)
RATE = re.compile(r"Rate Schedule:\s*(.+?)(?:\s{2,}|$)", re.I)
UTILITY_LABEL = re.compile(r"^(?:Electric Utility|Utility|Electric Service Provider):\s*(.+)$", re.I)
PRIVATE = re.compile(r"account|service for|service agreement|customer number|meter\s*#|address|phone|e-?mail", re.I)
EMAIL = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
PHONE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b")


def safe_text(value: str) -> str:
    value = " ".join(value.split())[:200]
    if PRIVATE.search(value):
        return "[private source line omitted]"
    return PHONE.sub("[phone removed]", EMAIL.sub("[email removed]", value))


def evidence(page: PageText, line: str) -> dict:
    return {"page": page.page, "method": page.method, "text": safe_text(line)}


def field(candidates: list[tuple[object, dict]], *, unit: str | None = None) -> dict:
    unique = []
    for value, source in candidates:
        if not any(value == prior for prior, _ in unique):
            unique.append((value, source))
    return {
        "value": unique[0][0] if len(unique) == 1 else None,
        "unit": unit,
        "status": "missing" if not unique else "extracted" if len(unique) == 1 else "ambiguous",
        "evidence": [source for _, source in candidates][:12],
        "alternatives": [value for value, _ in unique] if len(unique) > 1 else [],
    }


def _date(value: str) -> str:
    month, day, year = map(int, value.split("/"))
    return date(year, month, day).isoformat()


def _money(value: str) -> float:
    return float(value.replace("$", "").replace(",", ""))


def _lines(page: PageText) -> list[str]:
    # For the PG&E/Ava two-column layout, left_text keeps unrelated right-hand
    # explanatory text out of charge rows. OCR has no column coordinates.
    text = page.left_text if "Details of " in page.text and page.left_text else page.text
    lines = text.splitlines()
    combined = []
    for line in lines:
        if combined and combined[-1].strip().startswith("Total ") and " Electric" in combined[-1] and "Charges" not in combined[-1]:
            # A clipped glyph from the adjacent column may sit between the
            # wrapped provider name and its "Generation Charges" continuation.
            if re.fullmatch(r"[A-Z]", line.strip()):
                continue
            combined[-1] += " " + line.strip()
        else:
            combined.append(line)
    return combined


def _kind(label: str) -> str:
    lower = label.lower()
    if "credit" in lower or "discount" in lower:
        return "credit"
    if "tax" in lower:
        return "tax"
    if "demand" in lower:
        return "demand"
    if "kwh" in lower or "energy" in lower or lower.startswith(("peak", "off peak", "off-peak")):
        return "energy"
    if "customer" in lower or "base" in lower or "minimum" in lower:
        return "fixed"
    return "adjustment"


def _charge_row(page: PageText, line: str) -> dict | None:
    stripped = line.strip()
    if not stripped or stripped.startswith(("Total ", "Net Charges", "Rate Schedule:", "Energy Charges", "Details of ")):
        return None
    energy = ENERGY_ROW.match(stripped)
    match = None if energy else next(iter(MONEY.finditer(stripped)), None)
    if not energy and match is None:
        return None
    # A kWh row may show a unit price before the final charge; its price has
    # five decimals in known layouts and is excluded by MONEY's two decimals.
    label = (energy["label"] if energy else stripped[:match.start()]).strip()
    if len(label) < 3 or PRIVATE.search(label) or not re.search(r"[A-Za-z]", label):
        return None
    if not (energy or re.search(r"credit|charge|tax|surcharge|adjustment|choice|discount|fee|demand", label, re.I)):
        return None
    row = {"description": safe_text(label), "amount": _money(energy["amount"] if energy else match.group(1)),
           "currency": "USD", "kind": "energy" if energy else _kind(label), "evidence": [evidence(page, line)]}
    if energy:
        row["quantity_kwh"] = float(energy["kwh"].replace(",", ""))
    return row


def extract_bill(content: bytes, *, ocr=None) -> dict:
    draft = parse_document(extract_pages(content, ocr=ocr))
    from .interval_attachment import read_interval_summary
    from .validation import validate_draft
    values = {name: draft["fields"][name]["value"] for name in (
        "interval_minutes", "period_start", "period_end", "time_zone")}
    summary = read_interval_summary(content, minutes=values["interval_minutes"],
                                    period_start=values["period_start"], period_end=values["period_end"],
                                    time_zone=values["time_zone"], required=False)
    if summary is not None:
        draft["interval_summary"] = summary
        draft["issues"] = validate_draft(draft)
    return draft


def parse_document(document: ExtractedDocument) -> dict:
    if not isinstance(document, ExtractedDocument) or not document.pages:
        raise ValueError("Supply extracted PDF pages.")
    candidates: dict[str, list] = {name: [] for name in (
        "delivery_utility", "generation_provider", "billing_plan", "period_start", "period_end",
        "billing_days", "meter_import_kwh", "current_electric_charges", "statement_amount_due",
        "maximum_demand_kw", "export_kwh", "export_credit", "interval_minutes", "reported_interval_count",
        "time_zone")}
    services = []
    for page in document.pages:
        full_lines = page.text.splitlines()
        service_match = SERVICE.search(page.text)
        if service_match:
            provider = " ".join(service_match.group(1).split())
            role = service_match.group(2).lower()
            service = {"provider": provider, "role": role, "page": page.page,
                       "fields": {}, "line_items": []}
            services.append(service)
            candidates["delivery_utility" if role == "delivery" else "generation_provider"].append(
                (provider, evidence(page, service_match.group(0))))
        else:
            service = None
        lines = _lines(page)
        page_dates = []
        page_usage = []
        for line in full_lines:
            period = PERIOD.search(line)
            if period:
                try:
                    start, end = _date(period["start"]), _date(period["end"])
                except ValueError:
                    continue
                page_dates.append((start, end, int(period["days"]), evidence(page, line)))
            due = AMOUNT_DUE.search(line)
            if due:
                candidates["statement_amount_due"].append((_money(due[1]), evidence(page, line)))
            usage = USAGE.search(line)
            if usage:
                page_usage.append((float(usage[1].replace(",", "")), evidence(page, line)))
            demand = DEMAND.search(line)
            if demand:
                candidates["maximum_demand_kw"].append((float(demand[1].replace(",", "")), evidence(page, line)))
            exported = EXPORT.search(line)
            if exported:
                candidates["export_kwh"].append((float(exported[1].replace(",", "")), evidence(page, line)))
            credit = EXPORT_CREDIT.search(line)
            if credit:
                candidates["export_credit"].append((_money(credit[1]), evidence(page, line)))
            resolution = INTERVAL_RESOLUTION.search(line)
            if resolution:
                multiplier = 60 if resolution[2].lower().startswith(("hour", "hr")) else 1
                candidates["interval_minutes"].append((int(resolution[1]) * multiplier, evidence(page, line)))
            interval_count = INTERVAL_COUNT.search(line)
            if interval_count:
                candidates["reported_interval_count"].append((int(interval_count[1].replace(",", "")), evidence(page, line)))
            zone = TIME_ZONE.search(line)
            if zone:
                candidates["time_zone"].append((zone[1], evidence(page, line)))
        if service:
            for start, end, days, source in page_dates:
                for name, value in (("period_start", start), ("period_end", end), ("billing_days", days)):
                    service["fields"].setdefault(name, []).append((value, source))
                    candidates[name].append((value, source))
            totals = []
            usages = page_usage
            tariffs = []
            for line in lines:
                total = TOTAL.search(line.strip())
                if total and total.group(2).lower() == service["role"]:
                    totals.append((_money(total[3]), evidence(page, line)))
                    continue
                tariff = RATE.search(line)
                if tariff:
                    tariffs.append((tariff[1].strip(), evidence(page, line)))
                row = _charge_row(page, line)
                if row:
                    service["line_items"].append(row)
            service["fields"].update(
                total_charges=field(totals, unit="USD"),
                meter_import_kwh=field(usages, unit="kWh"),
                tariff=field(tariffs),
            )
            for name in ("period_start", "period_end", "billing_days"):
                service["fields"][name] = field(service["fields"].get(name, []), unit="days" if name == "billing_days" else None)
            if role == "delivery":
                candidates["billing_plan"].extend(tariffs)
                candidates["meter_import_kwh"].extend(usages)
            # Generation and delivery quote the same physical meter purchases;
            # use a generation quote only when no delivery section exists.
            if role == "generation" and not candidates["meter_import_kwh"]:
                candidates["meter_import_kwh"].extend(usages)
            candidates["current_electric_charges"].extend(totals)
        else:
            # Generic single-service bills can still expose an explicit
            # "Total Electric Charges" and "Total Usage" without a known layout.
            electric_page = bool(re.search(r"(?:Total|Current) Electric(?:ity)? Charges|Electric(?:ity)? Usage", page.text, re.I))
            if electric_page:
                for start, end, days, source in page_dates:
                    for name, value in (("period_start", start), ("period_end", end), ("billing_days", days)):
                        candidates[name].append((value, source))
            for line in (lines if electric_page else ()):
                utility = UTILITY_LABEL.search(line.strip())
                if utility and not PRIVATE.search(utility[1]):
                    candidates["delivery_utility"].append((utility[1].strip()[:160], evidence(page, line)))
                tariff = RATE.search(line)
                if tariff and not PRIVATE.search(tariff[1]):
                    candidates["billing_plan"].append((tariff[1].strip()[:160], evidence(page, line)))
                usage = USAGE.search(line)
                if usage:
                    candidates["meter_import_kwh"].append((float(usage[1].replace(",", "")), evidence(page, line)))
                generic_total = re.search(rf"\b(?:Total|Current) Electric(?:ity)? Charges\s+({NUMBER})\b", line, re.I)
                if generic_total:
                    candidates["current_electric_charges"].append((_money(generic_total[1]), evidence(page, line)))
    # Sum separate delivery/generation charge sections exactly once. Do not
    # mistake a whole-statement amount due (possibly including gas) for this.
    service_totals = [s["fields"]["total_charges"] for s in services]
    roles = [(s["provider"], s["role"]) for s in services]
    if (service_totals and len(set(roles)) == len(roles)
            and all(item["status"] == "extracted" for item in service_totals)):
        candidates["current_electric_charges"] = [(round(sum(item["value"] for item in service_totals), 2),
            source) for item in service_totals for source in item["evidence"]]
    units = {"billing_days": "days", "meter_import_kwh": "kWh", "current_electric_charges": "USD",
             "statement_amount_due": "USD", "maximum_demand_kw": "kW", "export_kwh": "kWh", "export_credit": "USD",
             "interval_minutes": "minutes", "reported_interval_count": "intervals"}
    fields = {name: field(values, unit=units.get(name)) for name, values in candidates.items()}
    draft = {"schema_version": 1, "source_sha256": document.sha256,
             "pages": [{"page": page.page, "method": page.method} for page in document.pages],
             "fields": fields, "services": services, "issues": [], "corrections": []}
    from .validation import validate_draft
    draft["issues"] = validate_draft(draft)
    return draft
