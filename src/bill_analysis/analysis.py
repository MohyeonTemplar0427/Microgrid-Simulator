"""Observed billing-cycle trends; no reconstruction of interval/native load."""
from __future__ import annotations

from datetime import date

from .validation import validate_draft


def _get(bill: dict, name: str):
    return bill.get("fields", {}).get(name, {}).get("value")


def _season(day: date) -> str:
    return ("winter" if day.month in {12, 1, 2} else
            "spring" if day.month in {3, 4, 5} else
            "summer" if day.month in {6, 7, 8} else "fall")


def analyze_bills(bills: list[dict]) -> dict:
    if not isinstance(bills, list) or not bills:
        raise ValueError("Supply at least one reviewed bill.")
    if len(bills) > 60:
        raise ValueError("Analyze at most 60 billing cycles together.")
    entries = []
    for bill in bills:
        if not isinstance(bill, dict) or bill.get("approved") is not True:
            raise ValueError("Every bill must be reviewed and approved before analysis.")
        problems = validate_draft(bill)
        if any(problem["severity"] == "error" for problem in problems):
            raise ValueError("An approved bill has unresolved validation errors.")
        start, end = date.fromisoformat(_get(bill, "period_start")), date.fromisoformat(_get(bill, "period_end"))
        days = (end - start).days + 1
        usage = float(_get(bill, "meter_import_kwh"))
        charges = _get(bill, "current_electric_charges")
        composition = None
        if (bill.get("services") and all(service.get("line_items") for service in bill["services"])
                and not any(item["code"] in {"charge_reconciliation", "electric_total_mismatch"}
                            for item in problems)):
            composition = {}
            for service in bill["services"]:
                for row in service["line_items"]:
                    composition[row["kind"]] = round(composition.get(row["kind"], 0.0) + row["amount"], 2)
        start_season, end_season = _season(start), _season(end)
        entry = {
            "source_sha256": bill.get("source_sha256"), "period_start": start.isoformat(),
            "period_end": end.isoformat(), "billing_days": days,
            "delivery_utility": _get(bill, "delivery_utility"),
            "generation_provider": _get(bill, "generation_provider"),
            "billing_plan": _get(bill, "billing_plan"),
            "meter_import_kwh": usage, "meter_import_kwh_per_day": round(usage / days, 4),
            "current_electric_charges_usd": charges,
            "electric_charges_usd_per_day": round(charges / days, 4) if charges is not None else None,
            "itemized_cost_usd_by_kind": composition,
            "maximum_demand_kw": _get(bill, "maximum_demand_kw"),
            "export_kwh": _get(bill, "export_kwh"),
            "export_credit_usd": _get(bill, "export_credit"),
            "reported_interval_minutes": _get(bill, "interval_minutes"),
            "reported_interval_count": _get(bill, "reported_interval_count"),
            "interval_summary": bill.get("interval_summary"),
            "calendar_season": start_season if start_season == end_season else None,
            "unresolved_warnings": [item for item in problems if item["severity"] == "warning"],
        }
        entries.append(entry)
    entries.sort(key=lambda item: (item["period_start"], item["period_end"]))
    previous = None
    for entry in entries:
        if previous and entry["period_start"] <= previous["period_end"]:
            raise ValueError("Billing periods overlap; resolve duplicate or revised statements before analysis.")
        if previous:
            base = previous["meter_import_kwh_per_day"]
            entry["change_from_previous_daily_import_percent"] = (
                round(100 * (entry["meter_import_kwh_per_day"] / base - 1), 2) if base > 0 else None)
            entry["gap_days_from_previous"] = (date.fromisoformat(entry["period_start"])
                                               - date.fromisoformat(previous["period_end"])).days - 1
        else:
            entry["change_from_previous_daily_import_percent"] = None
            entry["gap_days_from_previous"] = None
        previous = entry
    season_groups = {}
    for season in ("winter", "spring", "summer", "fall"):
        selected = [item for item in entries if item["calendar_season"] == season]
        if selected:
            season_groups[season] = {
                "cycles": len(selected), "meter_import_kwh_per_day": round(
                    sum(item["meter_import_kwh"] for item in selected)
                    / sum(item["billing_days"] for item in selected), 4),
            }
    facts = []
    if len(entries) >= 2:
        high, low = max(entries, key=lambda item: item["meter_import_kwh_per_day"]), min(
            entries, key=lambda item: item["meter_import_kwh_per_day"])
        facts.append({"type": "observed_range", "basis": "meter purchases normalized by billing days",
                      "highest_period_start": high["period_start"], "lowest_period_start": low["period_start"],
                      "highest_kwh_per_day": high["meter_import_kwh_per_day"],
                      "lowest_kwh_per_day": low["meter_import_kwh_per_day"]})
    recommendations = []
    large_changes = [entry for entry in entries[1:]
                     if entry["change_from_previous_daily_import_percent"] is not None
                     and abs(entry["change_from_previous_daily_import_percent"]) >= 20]
    if large_changes:
        recommendations.append({
            "claim_level": "hypothesis_to_investigate", "kind": "review_usage_change",
            "message": "Daily-average grid purchases changed substantially between billing cycles. Check occupancy, equipment, weather and any PV/battery changes before attributing a cause.",
            "evidence_periods": [item["period_start"] for item in large_changes],
            "estimated_savings_usd": None, "additional_data": ["interval meter data", "site operating history"],
        })
    demand_heavy = [entry for entry in entries if entry["itemized_cost_usd_by_kind"] and
                    entry["current_electric_charges_usd"] and
                    entry["itemized_cost_usd_by_kind"].get("demand", 0) / entry["current_electric_charges_usd"] >= .2]
    if demand_heavy:
        recommendations.append({
            "claim_level": "hypothesis_to_investigate", "kind": "review_demand_peak",
            "message": "Demand charges are a substantial share of these observed bills. Examine interval peaks and the applicable demand windows before considering peak reduction.",
            "evidence_periods": [item["period_start"] for item in demand_heavy],
            "estimated_savings_usd": None, "additional_data": ["interval meter data", "verified tariff demand rules"],
        })
    if len(season_groups) >= 2 and all(group["cycles"] >= 2 for group in season_groups.values()):
        highs = sorted(season_groups.items(), key=lambda pair: pair[1]["meter_import_kwh_per_day"])
        if highs[-1][1]["meter_import_kwh_per_day"] > 1.2 * highs[0][1]["meter_import_kwh_per_day"]:
            recommendations.append({
                "claim_level": "hypothesis_to_investigate", "kind": "review_calendar_pattern",
                "message": "Observed grid purchases differ across calendar seasons. Review weather, occupancy and on-site generation before assigning a cause.",
                "evidence_periods": [item["period_start"] for item in entries if item["calendar_season"] in {highs[0][0], highs[-1][0]}],
                "estimated_savings_usd": None, "additional_data": ["site context", "interval data or equipment records"],
            })
    # Even a complete stack of monthly bills supplies no within-day timing.
    recommendations.append({
        "claim_level": "data_needed", "kind": "interval_data_for_tariff_savings",
        "message": "A tariff-switch or load-shifting saving cannot be quantified from monthly totals alone.",
        "evidence_periods": [], "estimated_savings_usd": None,
        "additional_data": ["time-stamped meter imports/exports", "account eligibility", "dated tariff rules"],
    })
    return {
        "schema_version": 1, "basis": "observed_utility_meter_purchases_not_native_building_load",
        "cycles": entries, "season_groups": season_groups, "observed_facts": facts,
        "recommendations": recommendations,
        "limitations": [
            "Monthly bills do not reveal hourly or 15-minute loads, appliance consumption or peak timing.",
            "With PV or batteries, grid purchases are not native building consumption.",
            "Statement amount due may include gas, previous balances or payments; this analysis uses current electric charges only.",
        ],
    }
