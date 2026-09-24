"""Saved, statement-level PG&E NBT annual replay for the shared local UI.

This path consumes documented monthly bill components. It deliberately does
not synthesize missing historical interval prices or claim annual dispatch.
"""

from dataclasses import fields
import json
from pathlib import Path

import pandas as pd

from ..billing.export_settlement import CreditBalance
from ..billing.pge_annual_replay import MonthlyNBTRecord, replay_nbt_year
from ..billing.pge_true_up import TrueUpRates


SCHEMA_VERSION = 7
REQUIRED_REQUEST_KEYS = {"schema_version", "name", "account_confirmed", "records", "rates"}
REQUIRED_RECORD_KEYS = {
    "period_start", "period_end", "import_kwh", "export_kwh", "charges",
    "credits_earned", "offsettable_paid", "source_reference", "evidence_kind",
}
OPTIONAL_RECORD_KEYS = {"stated_amount_due", "stated_closing_balance"}
RATE_KEYS = {field.name for field in fields(TrueUpRates)}


def validate_request(request):
    """Parse and reconcile before queueing so invalid years fail immediately."""

    if not isinstance(request, dict) or set(request) != REQUIRED_REQUEST_KEYS:
        raise ValueError("Supply name, account confirmation, twelve records and rates (null for a net consumer).")
    if request["schema_version"] != SCHEMA_VERSION:
        raise ValueError("PG&E annual statement replay requires schema version 7.")
    name = request["name"]
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
        raise ValueError("Give the annual replay a name of 1–120 characters.")
    raw_records = request["records"]
    if not isinstance(raw_records, list) or len(raw_records) != 12:
        raise ValueError("Supply exactly twelve monthly NBT records.")
    records = []
    for number, raw in enumerate(raw_records, 1):
        if not isinstance(raw, dict) or not REQUIRED_RECORD_KEYS <= set(raw) or set(raw) - REQUIRED_RECORD_KEYS - OPTIONAL_RECORD_KEYS:
            raise ValueError(f"Cycle {number} has missing or unknown fields.")
        record = dict(raw)
        balance = record.get("stated_closing_balance")
        if balance is not None:
            if not isinstance(balance, dict) or set(balance) != {"generation", "delivery", "bonus"}:
                raise ValueError(f"Cycle {number} stated closing balance must separate all three credit buckets.")
            record["stated_closing_balance"] = CreditBalance(**balance)
        records.append(MonthlyNBTRecord(**record))
    raw_rates = request["rates"]
    if raw_rates is not None and (not isinstance(raw_rates, dict) or set(raw_rates) != RATE_KEYS):
        raise ValueError("Supply all documented true-up factors for the exact month, or null for a net consumer.")
    rates = None if raw_rates is None else TrueUpRates(**raw_rates)
    result = replay_nbt_year(records, account_confirmed=request["account_confirmed"], rates=rates)
    return result


def _save_table(directory, tables, key, label, rows):
    from .worker import write_json

    frame = pd.DataFrame(rows)
    payload = json.loads(frame.to_json(orient="split", index=False, double_precision=15))
    payload["labels"] = [column.replace("_", " ") for column in payload["columns"]]
    write_json(directory / f"{key}.json", payload)
    frame.to_csv(directory / f"{key}.csv", index=False)
    tables.append({"id": key, "label": label, "row_count": len(frame)})


def execute(directory, request):
    """Write the replay to the ordinary saved-study table and CSV routes."""

    from .worker import write_json

    directory = Path(directory)
    result = validate_request(request)
    true_up = result["true_up"]
    balance = result["pre_true_up_balance"]
    tables = []
    _save_table(directory, tables, "annual-summary", "Annual PG&E NBT statement summary", [{
        "period_start": request["records"][0]["period_start"],
        "period_end": request["records"][-1]["period_end"],
        "annual_import_kwh": result["annual_import_kwh"],
        "annual_export_kwh": result["annual_export_kwh"],
        "monthly_amount_due_sum": result["monthly_amount_due_sum"],
        "net_surplus_kwh": true_up["net_surplus_kwh"],
        "true_up_adjustment_before_bonus": true_up["adjustment_before_bonus"],
        "bonus_credit_available": true_up["bonus_credit_available"],
        "adjustment_if_all_bonus_applied": true_up["adjustment_if_all_bonus_applied"],
        "pre_true_up_generation_credit": balance["generation"],
        "pre_true_up_delivery_credit": balance["delivery"],
        "pre_true_up_bonus_credit": balance["bonus"],
    }])
    monthly = []
    for row in result["monthly"]:
        flat = {key: row[key] for key in (
            "cycle", "period_start", "period_end", "import_kwh", "export_kwh",
            "amount_due", "source_reference",
        )}
        for group in ("import_charges", "credits_earned", "credits_used", "opening_balance", "closing_balance"):
            flat.update({f"{group}_{key}": value for key, value in row[group].items()})
        flat.update({f"offsettable_paid_{key}": value for key, value in row["offsettable_paid"].items()})
        monthly.append(flat)
    _save_table(directory, tables, "monthly-ledger", "Twelve monthly bills and credit balances", monthly)
    _save_table(directory, tables, "true-up-components", "Annual true-up by restricted credit", [
        {"component": key, **component} for key, component in true_up["components"].items()
    ])
    write_json(directory / "result.json", {
        "schema_version": SCHEMA_VERSION,
        "tables": tables,
        "request": request,
        "engine": json.loads((directory / "engine.json").read_text()),
        "program": result["program"],
        "evidence_kind": result["evidence_kind"],
        "sources": true_up["sources"],
        "warnings": [*result["warnings"], *true_up["warnings"],
                     "This is a statement replay, not simulated solar production or annual optimal battery dispatch. No missing utility rates were estimated."],
    })
    write_json(directory / "progress.json", {"message": "Annual statement replay complete"})
