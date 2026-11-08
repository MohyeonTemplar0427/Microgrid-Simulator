"""DEC ordinary Residential R / General Service GS, initially non-export only."""
import numpy as np
import pandas as pd

from .delaware_coop_de_rates import COVERAGE, GAPS, SOURCES, NONEXPORT, BATTERY, rates_for_month

UTILITY = "delaware_electric_cooperative"
TIMEZONE = "America/New_York"
PLANS = {"R": "Residential Service", "GS": "General Service below 50 kW"}
MAX_KW = {"R": 25., "GS": 49.9}
CONFIRMATIONS = {
    "eligibility_confirmed": "DEC confirms membership, the selected ordinary R/GS classification and combined DEC supply/delivery",
    "ordinary_service_confirmed": "One ordinary metered 120/240 V single-phase secondary service; no special facilities/minimum, optional riders, lighting, programs, assistance, budget billing or other recurring adjustments",
    "full_monthly_charges_confirmed": "Complete calendar service cycle with full monthly charges, final service-day meter reading and matching final-day bill; no transition allocation or proration",
    "local_charges_confirmed": "Ordinary unincorporated Sussex County location with no additional local charge or special tax treatment",
    "tax_status_confirmed": "Ordinary residential PUT exemption for R, or private taxable GS at 4.25%, without reduced manufacturing/processing rate or other exemption",
    "motor_power_factor_confirmed": "No motor of 10 hp or greater, unusual-load facility charge, or power-factor adjustment; utility confirms ordinary classification",
}


def account_fields(plan_id="R"):
    fields = [dict(name=key, type="boolean", label=value, required=True)
              for key, value in CONFIRMATIONS.items()]
    fields += [
        dict(name="account_source", type="text", required=True, label="DEC classification, locality and tax evidence or explicit hypothetical reference"),
        dict(name="der_ordinary_service_confirmed", type="boolean", label="Final DEC Option B No Sale/non-export approval covers exact PV equipment and retains ordinary import terms without another recurring charge"),
        dict(name="der_activation_date", type="date", label="Final DEC permission to operate active by"),
        dict(name="der_eligibility_source", type="text", label="Exact approved non-export design, sizing/history review, no special monthly charges and, if present, approved battery supplement"),
        dict(name="battery_interconnection_confirmed", type="boolean", label="Final DEC battery supplement approves the exact PV-paired, PV-only-charging, non-export storage installation without an optional battery rider"),
    ]
    if plan_id == "R":
        fields += [dict(name="residential_use_confirmed", type="boolean", required=True,
                        label="One single residential housekeeping unit used for ordinary domestic purposes; farm and separate commercial operations excluded")]
    else:
        fields += [
            dict(name="gs_retained_assignment_confirmed", type="boolean", required=True, label="DEC retains ordinary metered GS with no pending or required transfer to another classification"),
            dict(name="gs_history_through_month", type="date", required=True, label="First day of final month in DEC's immediately preceding twelve-month demand review"),
            dict(name="gs_monthly_demands_kw", type="number_array", required=True, label="Twelve independently reviewed actual monthly demands, oldest first, each below 50 kW"),
            dict(name="gs_review_source", type="text", required=True, label="Independent actual demand history and retained DEC classification evidence"),
            dict(name="gs_contract_confirmed", type="boolean", required=True, label="DEC confirms active GS contract and applicable term, with no facilities or transformation charge above the ordinary $30 monthly minimum"),
        ]
    return fields


def defaults(plan_id="R"):
    if plan_id not in PLANS:
        raise ValueError("Select Delaware Electric Cooperative R or GS.")
    account = dict(tariff=plan_id, supply="bundled", export_mode="none", voltage="secondary", phase="single",
                   voltage_v=240., meter_count=1, opening_credit_usd=0., rate_evidence_mode="verified",
                   locality="sussex_unincorporated", billing_month="2026-07-01", bill_date="2026-07-31",
                   cycle_kind="regular", cycle_source="", account_source="", der_ordinary_service_confirmed=False,
                   der_activation_date="", der_eligibility_source="", battery_interconnection_confirmed=False)
    account.update(dict.fromkeys(CONFIRMATIONS, False))
    if plan_id == "R":
        account["residential_use_confirmed"] = False
    else:
        account.update(gs_retained_assignment_confirmed=False, gs_history_through_month="",
                       gs_monthly_demands_kw=[], gs_review_source="", gs_contract_confirmed=False)
    return account


def hypothetical_defaults(plan_id="R", *, day=None):
    account = defaults(plan_id)
    month = pd.Timestamp(day or account["billing_month"]).replace(day=1)
    account.update(dict.fromkeys(CONFIRMATIONS, True))
    account.update(hypothetical_account=True, billing_month=str(month.date()),
                   bill_date=str((month+pd.offsets.MonthEnd()).date()),
                   cycle_source="Explicit hypothetical complete calendar service cycle, final-day meter read and matching bill with full monthly charges",
                   account_source="Hypothetical ordinary DEC member in unincorporated Sussex County with plan-appropriate tax status",
                   der_ordinary_service_confirmed=True, der_activation_date="2024-12-31",
                   der_eligibility_source="Hypothetical final DEC Option B No Sale/non-export permission for this exact sub-100 kW DC PV design, accepted sizing/history, approved PV-only-charged battery supplement when present, and unchanged ordinary import terms without other recurring charges",
                   battery_interconnection_confirmed=True)
    if plan_id == "R":
        account["residential_use_confirmed"] = True
    else:
        account.update(gs_retained_assignment_confirmed=True, gs_history_through_month=str((month-pd.offsets.MonthBegin()).date()),
                       gs_monthly_demands_kw=[8.]*12, gs_contract_confirmed=True,
                       gs_review_source="Hypothetical DEC retained metered GS assignment, active contract and twelve independently reviewed monthly demands of 8 kW")
    return account


def catalog():
    return [dict(id=plan, label=f"Delaware Electric Cooperative {label}", status="supported",
                 customer_class="residential" if plan == "R" else "commercial",
                 coverage=[dict(start=start, end=end) for start, end in COVERAGE],
                 coverage_gaps=[dict(start=start, end=end, reason=reason) for start, end, reason in GAPS],
                 voltage="secondary", interval_minutes=[15], supply_arrangements=["bundled"],
                 equipment_modes=["grid_only", "pv_only", "pv_battery"], solar_modes=["non_export"],
                 representative_peak_kw=3. if plan == "R" else 5., account_fields=account_fields(plan),
                 sources=SOURCES, base_effective_start="2024-07-01",
                 eligibility="One ordinary 120/240 V single-phase secondary meter in unincorporated Sussex County with DEC supply and separately documented R or retained metered GS assignment.",
                 limitations=[
                     "Complete matching calendar service, final-day meter-reading and bill cycles January 2025 through October 2026 only; PCA changes May 1, 2026.",
                     "GS requires independently reviewed twelve-month demand history below 50 kW, retained classification and an active utility-confirmed contract. Current native/import study caps are R 25 kW and GS 49.9 kW.",
                     "Ordinary R domestic use is PUT exempt; private GS has 4.25% PUT. Other localities, tax reductions/exemptions, special minimums and optional programs are excluded.",
                     "Exact non-export PV below 100 kW DC requires final DEC approval; paired PV-only-charging storage additionally requires the approved battery supplement. No NEM, sale, standby or optional battery-rider rights are inferred.",
                 ]) for plan, label in PLANS.items()]


def _reference(account, key):
    value = account.get(key)
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 500:
        raise ValueError(f"Document Delaware Electric Cooperative {key} without personal identifiers.")


def _history(account, month):
    values = account.get("gs_monthly_demands_kw")
    if (account.get("gs_retained_assignment_confirmed") is not True
            or account.get("gs_contract_confirmed") is not True
            or not isinstance(values, list) or len(values) != 12
            or any(type(v) not in (int, float) or not np.isfinite(v) or not 0 <= v < 50. for v in values)
            or account.get("gs_history_through_month") != str((month-pd.offsets.MonthBegin()).date())):
        raise ValueError("DEC GS requires retained assignment, an active contract and twelve independently reviewed actual monthly demands below 50 kW.")
    _reference(account, "gs_review_source")


def cycle_review(account, index):
    index = pd.DatetimeIndex(index)
    step = pd.Timedelta(minutes=15)
    if (len(index) < 2 or str(index.tz) != TIMEZONE or index.hasnans
            or not np.all(index[1:]-index[:-1] == step)):
        raise ValueError("DEC requires complete consecutive Eastern-time 15-minute intervals.")
    start, stop = index[0], index[-1]+step
    if (start != start.normalize() or start.day != 1 or stop != start+pd.offsets.MonthBegin()
            or account.get("cycle_kind") != "regular" or account.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("DEC requires a complete calendar cycle with full monthly charges and a confirmed final-day meter reading.")
    month, end = str(start.date()), str(index[-1].date())
    if account.get("billing_month") != month or account.get("bill_date") != end:
        raise ValueError("DEC service, meter-reading and billing months must match with a final-day bill date.")
    rates = rates_for_month(month, account["tariff"])
    return dict(service_start=month, service_end=end, billing_month=month, bill_date=end,
                elapsed_hours=float((stop-start)/pd.Timedelta(hours=1)),
                source_version=rates["source_version"], source_grade=rates["source_grade"]), rates


def validate_account(account, index, equipment=None):
    if (not isinstance(account, dict) or account.get("tariff") not in PLANS
            or account.get("supply") != "bundled" or account.get("export_mode") != "none"):
        raise ValueError("Select DEC ordinary R/GS combined supply/delivery and zero export.")
    if any(account.get(key) is not True for key in CONFIRMATIONS):
        raise ValueError("Confirm DEC ordinary classification, complete cycle, locality, tax status and motor/power-factor scope.")
    for key in ("account_source", "cycle_source"):
        _reference(account, key)
    expected = dict(voltage="secondary", phase="single", voltage_v=240., meter_count=1,
                    opening_credit_usd=0., rate_evidence_mode="verified", locality="sussex_unincorporated")
    if (any(account.get(k) != v or isinstance(account.get(k), bool) for k, v in expected.items())
            or account.get("provisional_assumptions_accepted", False) is not False):
        raise ValueError("DEC scope requires one ordinary single-phase Sussex secondary meter and verified rates.")
    cycle, _ = cycle_review(account, index)
    if account["tariff"] == "GS":
        _history(account, pd.Timestamp(cycle["billing_month"]))
    elif account.get("residential_use_confirmed") is not True:
        raise ValueError("Confirm DEC R ordinary single-household domestic use.")
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        pv_dc = equipment.get("pv_dc_kw")
        if (not equipment.get("pv") or account.get("der_ordinary_service_confirmed") is not True
                or type(pv_dc) not in (int, float) or not np.isfinite(pv_dc) or not 0 < pv_dc < 100.):
            raise ValueError("DEC requires final exact-design approval preserving ordinary non-export terms for PV below 100 kW DC.")
        _reference(account, "der_eligibility_source")
        value = account.get("der_activation_date")
        try:
            active = str(pd.Timestamp(value).date()) == value and value <= cycle["service_start"]
        except (TypeError, ValueError):
            active = False
        if not active:
            raise ValueError("DEC final permission to operate must be active before the service cycle.")
        if equipment.get("battery") and (account.get("battery_interconnection_confirmed") is not True
                or equipment.get("renewable_only_charging") is not True or equipment.get("no_battery_export") is not True):
            raise ValueError("DEC paired storage requires an approved battery supplement, PV-only charging and zero export.")


def validate_native_load(account, load):
    values = np.asarray(load, dtype=float)
    if (not values.size or not np.isfinite(values).all() or np.min(values) < 0
            or np.max(values) > MAX_KW[account["tariff"]]+1e-7):
        raise ValueError("DEC native load exceeds the declared study envelope. PV-reduced imports cannot establish GS eligibility.")


def validate_state(account, index, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("DEC non-export service has no credit bank or billed-demand state.")


def charge_lines(index, imports, exports, account, *, math, state=None):
    validate_state(account, index, state)
    cycle, rates = cycle_review(account, index)
    plan = account["tariff"]
    if math.convex:
        math.constraints.extend([exports == 0, imports <= MAX_KW[plan]])
    elif (any(np.asarray(v).shape != (len(index),) or not np.isfinite(v).all()
              or np.min(v) < -1e-5 for v in (imports, exports))
          or np.max(exports) > 1e-5 or np.max(imports) > MAX_KW[plan]+1e-7):
        raise ValueError("DEC requires finite nonnegative imports within the study envelope and zero export.")
    energy = math.hours*math.sum(imports)
    first = math.minimum(energy, 700.)
    lines = dict(distribution_customer=rates["customer"], distribution_energy=energy*rates["distribution"],
                 renewable_resource_fund=energy*rates["renewable_resource_fund"],
                 supply_energy=first*rates["supply_first"]+(energy-first)*rates["supply_over"],
                 power_cost_adjustment=energy*rates["pca"])
    lines["delaware_public_utility_tax"] = sum(lines.values())*rates["public_utility_tax"]
    return dict(lines=lines, next_state={}, is_complete_bill=True, excluded_components=[],
                rate_sources=[*rates["sources"], NONEXPORT, BATTERY], rate_evidence_status="verified",
                assumption_model=None, rate_assumptions=[],
                metrics={**cycle, "raw_import_kwh": energy, "locality": account["locality"],
                         "billing_demand_applied": False, "monthly_minimum_usd": rates["customer"],
                         "gs_actual_review_max_kw": max(account["gs_monthly_demands_kw"]) if plan == "GS" else None,
                         "rounded_cash_optimum_claimed": False},
                warnings=["DEC supply, delivery, renewable fund and PCA are separately itemized. PJM wholesale inputs add no retail charge.",
                          "Ordinary residential R is PUT exempt; private taxable GS pays 4.25% on all otherwise charged components.",
                          "Final-day calendar cycles and study component rounding can differ from actual invoices. Special facilities, optional riders and capital-credit retirements are outside this account scope."])
