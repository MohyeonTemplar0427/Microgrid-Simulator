"""Schema 9: local ComEd bill replay through the shared pinned-engine queue."""
from datetime import date
from io import StringIO
import hashlib
import json
from pathlib import Path

import pandas as pd

from ..billing.comed_residential import ComEdResidentialAccount, ComEdHourlyPrices, calculate_comed_residential_bill
from ..billing.comed_commercial import ComEdCommercialAccount, calculate_comed_commercial_bill
from ..billing import comed_rates
from ..billing.comed_commercial import DELIVERY as COMMERCIAL_CLASSES


def defaults(customer_type="residential"):
    if customer_type not in ("residential", "commercial"):
        raise ValueError("Choose residential or commercial.")
    common = dict(supply="BES", billing_month="2026-09-01", ordinary_import_only_confirmed=False,
                  capacity_obligation_kw=None, capacity_source=None)
    if customer_type == "residential":
        account = dict(common, delivery_class="single_family_non_electric_heat")
    else:
        account = dict(common, delivery_class="small", service_voltage="secondary", utility_transformer=True,
                       previous_12_month_mkd_kw=None, previous_12_month_peak_kw=40., previous_calendar_year_peak_kw=40.,
                       competitively_declared=False, previous_year_months_ge_100kw=0,
                       electric_space_heat=False, watt_hour_eligibility="not_applicable",
                       eligibility_source="Synthetic account assumptions; not a verified customer account")
    return {"schema_version": 9, "name": "Untitled ComEd bill", "customer_type": customer_type,
            "account": account, "utility_reference": "Synthetic ComEd case; location coverage not inferred",
            "load": {"mode": "constant_example", "kw": 1. if customer_type == "residential" else 20.,
                     "csv": None, "source": "Synthetic constant meter imports, not measured consumption"},
            "prices": None}


def capabilities():
    return {"schema_version": 9, "defaults": {c: defaults(c) for c in ("residential", "commercial")},
            "residential_classes": list(comed_rates.DELIVERY), "commercial_classes": list(COMMERCIAL_CLASSES),
            "billing_months": ["2026-09-01", "2026-10-01"], "supplies": ["BES", "BESH"],
            "source_url": comed_rates.RATEBOOK_URL,
            "scope": "One complete calendar month, ordinary import-only accounts. Subtotals exclude state excise tax, municipal taxes and franchise fees. No storage optimization or export settlement."}


def _csv_series(text, value_column):
    if not isinstance(text, str) or not text.strip() or len(text.encode()) > 2*1024*1024:
        raise ValueError("Provide a nonempty CSV of at most 2 MiB.")
    try:
        frame = pd.read_csv(StringIO(text))
        if list(frame.columns) != ["timestamp", value_column] or len(frame) > 4000:
            raise ValueError("CSV requires timestamp," + value_column + " in that order, at most 4000 rows.")
        # utc=True alone would silently interpret naive inputs as UTC.
        if not frame.timestamp.astype(str).str.match(r"^\d{4}-\d{2}-\d{2}[T ].*(?:Z|[+-]\d{2}:\d{2})$").all():
            raise ValueError("Every timestamp must be an ISO interval start with Z or an explicit UTC offset.")
        index = pd.DatetimeIndex(pd.to_datetime(frame.timestamp, utc=True, errors="raise"))
        return pd.Series(frame[value_column].to_numpy(), index=index)
    except (TypeError, pd.errors.ParserError) as exc:
        raise ValueError("Invalid meter/price CSV.") from exc


def prepare(request):
    from .contract import number
    if not isinstance(request, dict) or set(request) != set(defaults()) or type(request.get("schema_version")) is not int or request["schema_version"] != 9:
        raise ValueError("Supply exactly the ComEd schema 9 fields.")
    if not isinstance(request["name"], str) or not 1 <= len(request["name"].strip()) <= 120:
        raise ValueError("Provide a study name of 1–120 characters.")
    kind = request["customer_type"]
    template = defaults(kind)
    account = request["account"]
    if not isinstance(account, dict) or set(account) != set(template["account"]):
        raise ValueError("Supply the exact account fields for this customer type.")
    if not isinstance(request["utility_reference"], str) or not 1 <= len(request["utility_reference"].strip()) <= 500:
        raise ValueError("Document ComEd service confirmation or explicitly label a hypothetical account.")
    if not isinstance(account["billing_month"], str) or account["billing_month"] not in capabilities()["billing_months"]:
        raise ValueError("Verified ComEd coverage is September and October 2026 billing months only.")
    month = date.fromisoformat(account["billing_month"])
    cls = ComEdResidentialAccount if kind == "residential" else ComEdCommercialAccount
    parsed_account = cls(**{**account, "billing_month": month})
    start = pd.Timestamp(month, tz="America/Chicago")
    grid = pd.date_range(start, start+pd.DateOffset(months=1), freq="30min", inclusive="left")
    load = request["load"]
    if not isinstance(load, dict) or set(load) != {"mode", "kw", "csv", "source"} or not isinstance(load["source"], str) or not 1 <= len(load["source"].strip()) <= 500:
        raise ValueError("Supply load mode, kw, csv and a source reference.")
    if load["mode"] == "constant_example":
        number(load["kw"], "Example import kW", 0, 1000000)
        if load["csv"] is not None:
            raise ValueError("Example mode cannot silently ignore a CSV.")
        imports = pd.Series(float(load["kw"]), index=grid)
    elif load["mode"] == "csv":
        if load["kw"] is not None:
            raise ValueError("CSV imports must not carry a scaling assumption.")
        imports = _csv_series(load["csv"], "grid_import_kw")
    else:
        raise ValueError("Choose a labeled constant example or measured interval CSV.")
    parsed_prices = parse_prices(request["prices"], grid)
    calculate = calculate_comed_residential_bill if kind == "residential" else calculate_comed_commercial_bill
    result = calculate(imports, parsed_account, hourly_prices=parsed_prices)
    return imports, result


def parse_prices(prices, grid):
    """Shared source/coverage contract for billing replay and dispatch studies."""
    from .contract import number
    parsed_prices = None
    if prices is not None:
        if not isinstance(prices, dict) or set(prices) != {"mode", "usd_per_mwh", "csv", "source", "basis_confirmed"}:
            raise ValueError("Supply the exact ComEd hourly price fields.")
        if not isinstance(prices["source"], str) or not 1 <= len(prices["source"].strip()) <= 500 or prices["basis_confirmed"] is not True:
            raise ValueError("Confirm real-time residual ComEd-zone LMP in USD/MWh and document the source or synthetic assumption.")
        if prices["mode"] == "constant_example":
            number(prices["usd_per_mwh"], "Example hourly LMP", -1000000, 1000000)
            if prices["csv"] is not None:
                raise ValueError("Example prices cannot silently ignore a CSV.")
            series = pd.Series(float(prices["usd_per_mwh"]), index=grid.tz_convert("UTC").floor("h").unique())
        elif prices["mode"] == "csv":
            if prices["usd_per_mwh"] is not None:
                raise ValueError("CSV prices must not carry a constant-price assumption.")
            series = _csv_series(prices["csv"], "residual_lmp_usd_per_mwh")
        else:
            raise ValueError("Choose synthetic hourly prices or a verified CSV.")
        parsed_prices = ComEdHourlyPrices(series, prices["source"], "COMED", "pjm_real_time_residual_lmp", "USD/MWh", "interval_start")
    return parsed_prices


def validate(request):
    prepare(request)
    return request


def execute(directory, request):
    from .worker import write_json
    from .table_store import save_table
    directory = Path(directory)
    imports, bill = prepare(request)
    tables = []
    def save(key, label, frame):
        save_table(directory, key, [c.replace("_", " ") for c in frame.columns], frame)
        tables.append({"id": key, "label": label, "row_count": len(frame)})
    save("comparison", "ComEd billing subtotal", pd.DataFrame([{
        "customer_type": request["customer_type"], "supply": request["account"]["supply"],
        "delivery_class": request["account"]["delivery_class"], "billing_month": bill["billing_month"],
        "import_kwh": bill["import_kwh"], "subtotal_usd": bill["subtotal_usd"],
        "billed_mkd_kw": bill.get("billed_mkd_kw"), "overall_30min_peak_kw": bill.get("overall_30min_peak_kw"),
        "complete_bill": False}]))
    frame = pd.DataFrame(bill["lines"])
    frame["source_pdf_pages"] = frame.source_pdf_pages.map(lambda x: ", ".join(map(str, x)))
    save("billing-components", "Itemized charges and credits", frame)
    save("meter-imports", "Meter imports · UTC interval starts", pd.DataFrame({"timestamp": imports.index.tz_convert("UTC"), "grid_import_kw": imports.values}))
    # Raw/derived hourly market values remain in the private request, not table
    # downloads. The bill itself carries only the required aggregate charges.
    warnings = [capabilities()["scope"], "No location-to-utility lookup was performed. Account eligibility is explicitly supplied."]
    if request["load"]["mode"] == "constant_example":
        warnings.append("Load is a synthetic constant example, not measured or calibrated consumption.")
    if request["prices"] and request["prices"]["mode"] == "constant_example":
        warnings.append("Hourly energy prices are synthetic assumptions, not observed PJM prices.")
    write_json(directory/"result.json", {"schema_version": 9, "tables": tables, "warnings": warnings,
               "engine": json.loads((directory/"engine.json").read_text()), "request": request, "bill": bill,
               "input_provenance": {"utility_reference": request["utility_reference"], "load_source": request["load"]["source"],
                                    "request_sha256": hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()}})
    write_json(directory/"progress.json", {"message": "ComEd subtotal and itemized charges saved"})
