"""NOVEC ordinary R-1/SC-1 retail service in unincorporated Prince William."""
import numpy as np
import pandas as pd

from .novec_va_rates import BASE, COVERAGE, GAPS, SOURCES, TERMS, rates_for_month

UTILITY = "northern_virginia_electric_cooperative"
TIMEZONE = "America/New_York"
PLANS = {"R-1": "Residential Service", "SC-1": "Single-phase Small Commercial Service"}
MAX_KW = {"R-1": 25., "SC-1": 29.9}
SC_MAX_KWH = 5999.
CONFIRMATIONS = {
    "eligibility_confirmed": "NOVEC confirmed ordinary R-1 or SC-1 service and membership",
    "ordinary_service_confirmed": "One ordinary single-phase 120/240 V secondary meter, no special facilities, optional programs, lighting, discounts or other charges",
    "full_monthly_charges_confirmed": "Complete matching calendar service and bill cycle with full monthly charges",
    "locality_confirmed": "Service is in unincorporated Prince William County and subject to its ordinary electric consumer utility tax",
    "taxable_service_confirmed": "Ordinary private taxable service without relief, governmental exemption, or cooperative federal-power tax reduction",
    "motor_limit_confirmed": "No individual motor exceeds the filed single-phase limit of 10 horsepower",
}


def account_fields(plan_id="R-1"):
    fields = [dict(name=key, type="boolean", label=label, required=True) for key, label in CONFIRMATIONS.items()]
    fields += [
        dict(name="account_source", type="text", required=True, label="NOVEC plan assignment, locality and tax evidence or explicit hypothetical reference"),
        dict(name="der_ordinary_service_confirmed", type="boolean", label="Written NOVEC approval preserves ordinary import billing for this exact non-export installation"),
        dict(name="der_activation_date", type="date", label="Final interconnection approval active by"),
        dict(name="der_eligibility_source", type="text", label="Written approval covering exact PV or paired PV-charged storage and unchanged ordinary billing"),
    ]
    if plan_id == "SC-1":
        fields += [
            dict(name="sc_retained_assignment_confirmed", type="boolean", required=True, label="NOVEC confirms retained SC-1, with no LP-1 transfer obligation or pending change"),
            dict(name="sc_history_through_month", type="date", required=True, label="First day of the final month in NOVEC's preceding-twelve-month demand review"),
            dict(name="sc_monthly_demands_kw", type="number_array", required=True, label="Twelve consecutive actual monthly demands, oldest first, each below 30 kW in this initial scope"),
            dict(name="sc_review_source", type="text", required=True, label="Independent actual demand history and NOVEC classification review evidence"),
        ]
    return fields


def defaults(plan_id="R-1"):
    if plan_id not in PLANS:
        raise ValueError("Select NOVEC R-1 residential or SC-1 single-phase small commercial service.")
    account = dict(tariff=plan_id, supply="bundled", export_mode="none", voltage="secondary", phase="single",
                   voltage_v=240., meter_count=1, opening_credit_usd=0., rate_evidence_mode="verified",
                   locality="prince_william_unincorporated", billing_month="2025-11-01", bill_date="2025-11-30",
                   cycle_kind="regular", cycle_source="", account_source="", der_ordinary_service_confirmed=False,
                   der_activation_date="", der_eligibility_source="")
    account.update(dict.fromkeys(CONFIRMATIONS, False))
    if plan_id == "SC-1":
        account.update(sc_retained_assignment_confirmed=False, sc_history_through_month="",
                       sc_monthly_demands_kw=[], sc_review_source="")
    return account


def hypothetical_defaults(plan_id="R-1", *, day=None):
    account = defaults(plan_id)
    month = pd.Timestamp(day or account["billing_month"]).replace(day=1)
    account.update(dict.fromkeys(CONFIRMATIONS, True))
    account.update(hypothetical_account=True, billing_month=str(month.date()),
                   bill_date=str((month+pd.offsets.MonthEnd()).date()),
                   cycle_source="Hypothetical complete calendar service and matching final-day bill cycle",
                   account_source="Hypothetical ordinary NOVEC taxable member in unincorporated Prince William County",
                   der_ordinary_service_confirmed=True, der_activation_date="2024-12-31",
                   der_eligibility_source="Hypothetical final NOVEC written approval for this exact non-export PV and PV-charged paired storage, retaining all ordinary import terms without other charges")
    if plan_id == "SC-1":
        account.update(sc_retained_assignment_confirmed=True, sc_monthly_demands_kw=[8.]*12,
                       sc_history_through_month=str((month-pd.offsets.MonthBegin()).date()),
                       sc_review_source="Hypothetical utility-retained SC-1 based on twelve actual monthly demands of 8 kW, without LP-1 transfer obligation")
    return account


def catalog():
    return [dict(id=plan, label=f"NOVEC {label}", status="supported",
                 customer_class="residential" if plan == "R-1" else "commercial",
                 coverage=[dict(start=start, end=end) for start, end in COVERAGE],
                 coverage_gaps=[dict(start=start, end=end, reason=reason) for start, end, reason in GAPS],
                 voltage="secondary", interval_minutes=[15], supply_arrangements=["bundled"],
                 equipment_modes=["grid_only", "pv_only", "pv_battery"], solar_modes=["non_export"],
                 representative_peak_kw=3. if plan == "R-1" else 5., account_fields=account_fields(plan),
                 sources=SOURCES, base_effective_start="2024-01-01" if plan == "R-1" else "2023-04-01",
                 eligibility="Ordinary NOVEC member on one single-phase secondary meter in unincorporated Prince William County. SC-1 requires retained assignment and independent preceding-twelve-month demand review.",
                 limitations=["Complete matching calendar cycles in 2025 only; original 2026 PCA/base intersections remain unverified.",
                              "The SC-1 study is restricted to twelve prior demands below 30 kW, current native/import power at most 29.9 kW and energy at most 5,999 kWh.",
                              "Other localities, optional programs, large motors, special facilities and tax exemptions are outside scope.",
                              "Non-export PV and PV-charged paired storage require final written approval preserving ordinary import terms."])
            for plan, label in PLANS.items()]


def _reference(account, key):
    value = account.get(key)
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 500:
        raise ValueError(f"Document NOVEC {key} without personal identifiers.")


def _history(account, month):
    values = account.get("sc_monthly_demands_kw")
    if (account.get("sc_retained_assignment_confirmed") is not True or not isinstance(values, list)
            or len(values) != 12 or any(type(v) not in (int, float) or not np.isfinite(v) or not 0 <= v < 30 for v in values)
            or account.get("sc_history_through_month") != str((month-pd.offsets.MonthBegin()).date())):
        raise ValueError("NOVEC SC-1 requires retained assignment and twelve independently reviewed prior monthly demands below 30 kW.")
    _reference(account, "sc_review_source")


def cycle_review(account, index):
    index = pd.DatetimeIndex(index)
    step = pd.Timedelta(minutes=15)
    if (len(index) < 2 or str(index.tz) != TIMEZONE or index.hasnans or not np.all(index[1:]-index[:-1] == step)):
        raise ValueError("NOVEC requires complete consecutive 15-minute Eastern-time intervals.")
    start, stop = index[0], index[-1]+step
    if (start != start.normalize() or start.day != 1 or stop != start+pd.offsets.MonthBegin()
            or account.get("cycle_kind") != "regular" or account.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("NOVEC requires a complete calendar cycle and full monthly charges.")
    month, bill_date = str(start.date()), str(index[-1].date())
    if account.get("billing_month") != month or account.get("bill_date") != bill_date:
        raise ValueError("NOVEC requires matching service and billing months with a final-day bill date.")
    rates = rates_for_month(month)
    return dict(service_start=month, service_end=bill_date, billing_month=month, bill_date=bill_date,
                elapsed_hours=float((stop-start)/pd.Timedelta(hours=1)),
                source_version=rates["source_version"], source_grade=rates["source_grade"]), rates


def validate_account(account, index, equipment=None):
    if (not isinstance(account, dict) or account.get("tariff") not in PLANS
            or account.get("supply") != "bundled" or account.get("export_mode") != "none"):
        raise ValueError("Confirm NOVEC ordinary R-1/SC-1 supply and zero export.")
    if any(account.get(key) is not True for key in CONFIRMATIONS):
        raise ValueError("Confirm NOVEC ordinary assignment, locality, taxes, motor limit and complete monthly charges.")
    for key in ("account_source", "cycle_source"):
        _reference(account, key)
    expected = dict(voltage="secondary", phase="single", voltage_v=240., meter_count=1,
                    opening_credit_usd=0., rate_evidence_mode="verified", locality="prince_william_unincorporated")
    if (any(account.get(k) != v or isinstance(account.get(k), bool) for k, v in expected.items())
            or account.get("provisional_assumptions_accepted", False) is not False):
        raise ValueError("NOVEC scope is one ordinary single-phase secondary meter in unincorporated Prince William and verified rates.")
    cycle, _ = cycle_review(account, index)
    if account["tariff"] == "SC-1":
        _history(account, pd.Timestamp(cycle["billing_month"]))
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or account.get("der_ordinary_service_confirmed") is not True:
            raise ValueError("Confirm written NOVEC approval preserving ordinary billing for this exact non-export installation.")
        _reference(account, "der_eligibility_source")
        value = account.get("der_activation_date")
        try:
            active = str(pd.Timestamp(value).date()) == value and value <= cycle["service_start"]
        except (TypeError, ValueError):
            active = False
        if not active:
            raise ValueError("NOVEC final interconnection approval must be active before the service cycle.")
        if equipment.get("battery") and (equipment.get("renewable_only_charging") is not True or equipment.get("no_battery_export") is not True):
            raise ValueError("NOVEC paired storage requires PV-only charging and zero export.")


def validate_native_load(account, load):
    if (np.max(load) > MAX_KW[account["tariff"]]+1e-7
            or account["tariff"] == "SC-1" and .25*np.sum(load) > SC_MAX_KWH+1e-7):
        raise ValueError("NOVEC native load exceeds the study envelope. Reduced imports cannot establish eligibility.")


def validate_state(account, index, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("NOVEC non-export service has no credit bank or demand state.")


def charge_lines(index, imports, exports, account, *, math, state=None):
    validate_state(account, index, state)
    cycle, rates = cycle_review(account, index)
    plan = account["tariff"]
    energy = math.hours*math.sum(imports)
    if math.convex:
        math.constraints.extend([exports == 0, imports <= MAX_KW[plan]])
        if plan == "SC-1":
            math.constraints.append(energy <= SC_MAX_KWH)
    elif (np.max(exports) > 1e-5 or np.max(imports) > MAX_KW[plan]+1e-7
          or plan == "SC-1" and energy > SC_MAX_KWH+1e-7):
        raise ValueError("NOVEC requires zero export and imports within the declared study envelope.")
    base = BASE[plan]
    lines = dict(delivery_customer=base["customer"], delivery_energy=energy*base["delivery_energy"],
                 supply_energy=energy*base["supply_energy"], power_cost_adjustment=energy*rates["pca"])
    first, lower_two = math.minimum(energy, 2500.), math.minimum(energy, 50000.)
    volumes = (first, lower_two-first, energy-lower_two)
    for name, factors in (("state_consumption_tax", (.00102, .00065, .00050)),
                          ("special_regulatory_tax", rates["regulatory_tax"]),
                          ("local_consumption_tax", (.00038, .00024, .00018))):
        lines[name] = sum(volume*factor for volume, factor in zip(volumes, factors))
    fixed, marginal, cap = (1.40, .01509, 3.) if plan == "R-1" else (2.29, .013487, 100.)
    lines["prince_william_consumer_utility_tax"] = math.minimum(fixed+energy*marginal, cap)
    return dict(lines=lines, next_state={}, is_complete_bill=True, excluded_components=[],
                rate_sources=[*rates["sources"], TERMS], rate_evidence_status="verified",
                assumption_model=None, rate_assumptions=[],
                metrics={**cycle, "raw_import_kwh": energy, "locality": account["locality"],
                         "billing_demand_applied": False, "distribution_minimum_usd": base["customer"],
                         "sc_actual_review_max_kw": max(account["sc_monthly_demands_kw"]) if plan == "SC-1" else None,
                         "rounded_cash_optimum_claimed": False},
                warnings=["NOVEC supply and distribution charges are separately itemized; PJM wholesale inputs add no retail charge.",
                          "The actual SCC regulatory levy is separate from statutory maximum rates and the county consumer tax.",
                          "Calendar study cycles and component rounding may differ from actual utility invoices."])
