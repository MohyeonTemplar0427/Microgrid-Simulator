"""Duke Energy Ohio Electric No. 19, ordinary RS and DM SSO."""
from copy import deepcopy

import numpy as np
import pandas as pd

from .duke_oh_rates import (
    BOOK_2025, BOOK_2026, CAPACITY_BREAK, COVERAGE, DCI_2026, DISTRIBUTION,
    DISTRIBUTION_BREAK, EXCISE_BREAKS, EXCISE_RATES, PLANS, RS_WINTER_SUPPLY_BREAK, rates_for_month,
)

UTILITY = "duke_energy_ohio"
TIMEZONE = "America/New_York"
IMPORT_LIMIT_KW = {"RS": 25., "DM": 15.}
RULE_SOURCES = [
    "https://codes.ohio.gov/ohio-revised-code/section-5727.81",
    "https://codes.ohio.gov/ohio-revised-code/section-5739.02",
    "https://codes.ohio.gov/ohio-administrative-code/chapter-4901:1-22",
]
SOURCES = [BOOK_2025, BOOK_2026, DCI_2026, *RULE_SOURCES]
GAPS = [
    {"start": "2025-01-01", "end": "2025-05-31", "reason": "Pre-June rider intersections remain unverified."},
    {"start": "2025-07-01", "end": "2026-09-30", "reason": "Intermediate filed rider revisions and cycle intersections remain unverified."},
    {"start": "2026-11-01", "end": "2026-12-31", "reason": "Later filed rider changes and cycle intersections remain unverified."},
]
CONFIRMATIONS = {
    "eligibility_confirmed": "Duke confirmed ordinary Ohio RS domestic or retained DM secondary classification",
    "ordinary_service_confirmed": "One ordinary 120/240 V single-phase meter with no special facilities, credits or programs",
    "sso_enrollment_confirmed": "Ordinary non-PIPP SSO throughout the cycle without supplier changes",
    "no_local_tax_confirmed": "No additional local charges, special tax treatment or self-assessment",
    "full_monthly_charges_confirmed": "Complete calendar cycle with a matching final monthly read and revenue month",
}
REFERENCES = {
    "supply_source": "Duke assignment and SSO evidence or explicit hypothetical assumption",
    "tax_source": "Ordinary state excise and absent local-charge evidence or explicit hypothetical assumption",
    "por_source": "UE-GEN rider applicability evidence or explicit hypothetical assumption",
}


def account_fields(plan_id="RS"):
    fields = [
        {"name": key, "type": "boolean", "label": label, "required": True}
        for key, label in CONFIRMATIONS.items()
    ] + [
        {"name": key, "type": "text", "label": label, "required": True}
        for key, label in REFERENCES.items()
    ]
    fields += [
        {"name": "ue_gen_status", "type": "select", "choices": ["unconfirmed", "applies", "exempt"],
         "label": "Confirmed Duke UE-GEN applicability (Sheet 88)", "required": True},
        {"name": "der_ordinary_service_confirmed", "type": "boolean",
         "label": "Duke approved the exact non-export renewable PV/storage and ordinary tariff continuation"},
        {"name": "der_activation_date", "type": "date", "label": "Final interconnection and metering active by"},
        {"name": "der_eligibility_source", "type": "text", "label": "Exact installation approval or hypothetical reference"},
    ]
    if plan_id == "DM":
        fields += [
            {"name": "dm_review_confirmed", "type": "boolean",
             "label": "Duke retained ordinary DM after its initial term and through this cycle; no pending DS reassignment",
             "required": True},
            {"name": "dm_history_through_month", "type": "date",
             "label": "First day of the last month in Duke's most recent annual demand review", "required": True},
            {"name": "dm_monthly_demands_kw", "type": "number_array",
             "label": "Duke's 12 consecutive actual monthly demands, oldest first (kW)", "required": True},
            {"name": "dm_review_source", "type": "text",
             "label": "Duke demand history and retained classification evidence or hypothetical assumption", "required": True},
        ]
    return fields


def defaults(plan_id="RS"):
    if plan_id not in PLANS:
        raise ValueError("Select Duke Energy Ohio RS or DM SSO.")
    month, last_day = COVERAGE[-1]
    account = dict(
        tariff=plan_id, supply="sso", export_mode="none", voltage="secondary", phase="single",
        voltage_v=240., meter_count=1, opening_credit_usd=0., self_assessor=False,
        tax_jurisdiction="oh_state_only", rate_evidence_mode="verified",
        cycle_kind="regular", billing_month=month, bill_date=last_day, cycle_source="",
        ue_gen_status="unconfirmed", der_ordinary_service_confirmed=False,
        der_activation_date="", der_eligibility_source="",
    )
    account.update(dict.fromkeys(CONFIRMATIONS, False))
    account.update(dict.fromkeys(REFERENCES, ""))
    if plan_id == "DM":
        account.update(dm_review_confirmed=False, dm_history_through_month="",
                       dm_monthly_demands_kw=[], dm_review_source="")
    return account


def hypothetical_defaults(plan_id="RS", *, day=None):
    account = defaults(plan_id)
    month = pd.Timestamp(day or account["billing_month"]).replace(day=1)
    account.update(dict.fromkeys(CONFIRMATIONS, True))
    account.update(
        hypothetical_account=True, billing_month=str(month.date()),
        bill_date=str((month+pd.offsets.MonthEnd()).date()),
        cycle_source="Explicit hypothetical complete calendar meter cycle and matching final read",
        supply_source="Hypothetical Company-confirmed ordinary Ohio SSO classification",
        tax_source="Hypothetical state excise without local charges or self-assessment",
        ue_gen_status="applies", por_source="Hypothetical account subject to Duke Rider UE-GEN",
        der_ordinary_service_confirmed=True, der_activation_date="2024-12-31",
        der_eligibility_source="Hypothetical approved exact renewable PV/paired storage, active meter and ordinary service continuation",
    )
    if plan_id == "DM":
        account.update(
            dm_review_confirmed=True, dm_monthly_demands_kw=[10.]*12,
            dm_history_through_month=str((month-pd.offsets.MonthBegin()).date()),
            dm_review_source="Hypothetical Duke retained DM based on 12 actual monthly 10 kW demands; no DS reassignment",
        )
    return account


def catalog():
    return [
        dict(
            id=plan, label=f"Duke Energy Ohio {'Residential RS' if plan == 'RS' else 'Small Secondary DM'} (SSO)",
            status="supported", customer_class="residential" if plan == "RS" else "commercial",
            coverage=[dict(start=start, end=end) for start, end in COVERAGE], coverage_gaps=deepcopy(GAPS),
            voltage="secondary", supply_arrangements=["sso"], solar_modes=["non_export"],
            equipment_modes=["grid_only", "pv_only", "pv_battery"], interval_minutes=[15],
            representative_peak_kw=3. if plan == "RS" else 10.,
            account_fields=account_fields(plan), sources=SOURCES,
            eligibility="Company-confirmed ordinary Ohio SSO on one 120/240 V single-phase meter. "
                        "DM requires retained classification and independent Company demand history.",
            limitations=[
                "Only the listed complete matching calendar cycles are priced. Other dates and shifted reads reject.",
                "DM requires a post-initial-term annual review with 12 actual monthly demands and no pending DS reclassification.",
                "Native and import study limits are 25 kW for RS and 15 kW for DM. These are study limits.",
                "Approved non-export PV and paired PV-charged storage only. Special accounts and unverified export settlement reject.",
            ],
        )
        for plan in PLANS
    ]


def _reference(account, key):
    value = account.get(key)
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 500:
        raise ValueError(f"Document Duke Energy Ohio {key} without personal identifiers.")


def _dm_history(account, service_month):
    demands = account.get("dm_monthly_demands_kw")
    if (account.get("dm_review_confirmed") is not True or not isinstance(demands, list)
            or len(demands) != 12 or any(type(kw) not in (int, float) or not 0 <= kw <= 1e6 for kw in demands)):
        raise ValueError("DM requires Duke's retained classification and 12 finite actual monthly demands.")
    _reference(account, "dm_review_source")
    date = account.get("dm_history_through_month")
    try:
        history_through = pd.Timestamp(date)
        valid = history_through.day == 1 and str(history_through.date()) == date
    except (TypeError, ValueError):
        valid = False
    if not valid or not service_month-pd.DateOffset(months=12) <= history_through < service_month:
        raise ValueError("DM demand review history must end in one of the 12 months before the billed month.")
    average = sum(demands)/12
    over_30 = sum(kw > 30. for kw in demands)
    if average > 15. or over_30 >= 2:
        raise ValueError("DM demand history reaches the tariff's DS reclassification criteria.")
    return dict(dm_review_average_kw=average, dm_review_months_over_30_kw=over_30,
                dm_history_through_month=date, dm_monthly_demands_kw=list(demands))


def cycle_review(account, index):
    idx = pd.DatetimeIndex(index)
    step = pd.Timedelta(minutes=15)
    if (len(idx) < 2 or str(idx.tz) != TIMEZONE or idx.hasnans
            or not np.all(idx[1:]-idx[:-1] == step)):
        raise ValueError("Duke Energy Ohio requires complete consecutive Eastern-time 15-minute intervals.")
    start = idx[0]
    stop = idx[-1]+step
    if (start != start.normalize() or start.day != 1 or stop != start+pd.offsets.MonthBegin()
            or account.get("cycle_kind") != "regular" or account.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("Duke Energy Ohio requires a complete calendar cycle with full monthly charges.")
    month, last_day = str(start.date()), str(idx[-1].date())
    if account.get("billing_month") != month or account.get("bill_date") != last_day:
        raise ValueError("Duke Energy Ohio requires matching calendar service, revenue month and final-read dates.")
    rates = rates_for_month(month)
    days = (stop.date()-start.date()).days
    return dict(
        service_start=month, service_end=last_day, billing_month=month, bill_date=last_day,
        final_meter_read_date=last_day, revenue_season="summer" if 6 <= start.month <= 9 else "winter",
        cycle_days=days, elapsed_hours=float((stop-start)/pd.Timedelta(hours=1)),
        excise_tax_thresholds_kwh=list(EXCISE_BREAKS),
        source_version=rates["source_version"],
    )


def validate_account(account, index, equipment=None):
    if (not isinstance(account, dict) or account.get("tariff") not in PLANS
            or account.get("supply") != "sso" or account.get("export_mode") != "none"):
        raise ValueError("Select ordinary Duke Energy Ohio RS or DM SSO with zero export.")
    if any(account.get(key) is not True for key in CONFIRMATIONS):
        raise ValueError("Confirm Duke account classification, ordinary SSO, taxes and final-read cycle separately.")
    for key in (*REFERENCES, "cycle_source"):
        _reference(account, key)
    if account.get("ue_gen_status") not in ("applies", "exempt"):
        raise ValueError("Confirm Duke UE-GEN rider applicability from the account.")
    expected = dict(voltage="secondary", phase="single", voltage_v=240., meter_count=1,
                    opening_credit_usd=0., self_assessor=False, tax_jurisdiction="oh_state_only",
                    rate_evidence_mode="verified")
    if (any(account.get(key) != value or isinstance(account.get(key), bool) != isinstance(value, bool)
            for key, value in expected.items()) or account.get("provisional_assumptions_accepted", False) is not False):
        raise ValueError("Duke scope requires ordinary single-phase secondary service, state excise and verified rates.")
    cycle = cycle_review(account, index)
    if account["tariff"] == "DM":
        _dm_history(account, pd.Timestamp(cycle["billing_month"]))
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or account.get("der_ordinary_service_confirmed") is not True:
            raise ValueError("Duke requires approved non-export PV with ordinary tariff continuation.")
        _reference(account, "der_eligibility_source")
        date = account.get("der_activation_date")
        try:
            active = str(pd.Timestamp(date).date()) == date and date <= cycle["service_start"]
        except (TypeError, ValueError):
            active = False
        if not active:
            raise ValueError("Duke interconnection and metering must be active before service.")
        if equipment.get("battery") and (equipment.get("renewable_only_charging") is not True
                                        or equipment.get("no_battery_export") is not True):
            raise ValueError("Duke initial paired-storage studies require PV-only charging and zero export.")
        if max(equipment.get("pv_dc_kw", 0.), equipment.get("pv_ac_kw", 0.))+equipment.get("battery_kw", 0.) > 25.+1e-8:
            raise ValueError("Duke combined PV and storage output exceeds the 25 kW study limit.")


def validate_state(account, index, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("Duke RS/DM study has no export credit bank or billing demand state.")


def charge_lines(index, imports, exports, account, *, math, state=None):
    validate_state(account, index, state)
    cycle = cycle_review(account, index)
    rate = rates_for_month(cycle["billing_month"])
    plan = account["tariff"]
    is_residential = plan == "RS"
    class_rate = rate["plans"][plan]
    limit = IMPORT_LIMIT_KW[plan]
    if math.convex:
        math.constraints.extend([exports == 0, imports <= limit])
    elif np.max(exports) > 1e-5 or np.max(imports) > limit+1e-7:
        raise ValueError("Duke RS/DM requires zero export and imports within the declared study limit.")
    usage = math.hours*math.sum(imports)
    customer, distribution_rates = DISTRIBUTION[plan]
    if is_residential:
        distribution = distribution_rates[0]*usage
        if len(class_rate["capacity"]) == 1:
            supply_capacity = class_rate["capacity"][0]*usage
            supply_energy = class_rate["energy"][0]*usage
        else:
            first = math.minimum(usage, RS_WINTER_SUPPLY_BREAK)
            supply_capacity = class_rate["capacity"][0]*first + class_rate["capacity"][1]*(usage-first)
            supply_energy = class_rate["energy"][0]*first + class_rate["energy"][1]*(usage-first)
    else:
        first = math.minimum(usage, DISTRIBUTION_BREAK)
        first_two = math.minimum(usage, CAPACITY_BREAK)
        distribution = distribution_rates[0]*first + distribution_rates[1]*(usage-first)
        capacity_first, capacity_later = class_rate["capacity"]
        supply_capacity = capacity_first*first_two + capacity_later*(usage-first_two)
        energy_first, energy_middle, energy_later = class_rate["energy"]
        supply_energy = energy_first*first + energy_middle*(first_two-first) + energy_later*(usage-first_two)
    base = customer+distribution
    generation_uncollectible = class_rate["generation_uncollectible"]*(usage if is_residential else 1.)
    lines = dict(distribution_customer=customer, distribution_energy=distribution,
                 supply_capacity=supply_capacity, supply_energy=supply_energy)
    lines.update({key: base*factor for key, factor in rate["distribution_fractions"].items()})
    lines.update(class_rate["per_bill"])
    lines.update({key: usage*price for key, price in {**rate["per_kwh"], **class_rate["per_kwh"]}.items()})
    # Supported 15-minute power envelopes keep the bill below 833,000 kWh.
    lines[rate["universal_service_line"]] = usage*rate["universal_service"]
    lines.update(
        generation_uncollectible=generation_uncollectible if account["ue_gen_status"] == "applies" else 0.,
        state_kwh_tax=math.tiered(usage, EXCISE_BREAKS, EXCISE_RATES), sales_tax=0.,
    )
    history = {} if is_residential else _dm_history(account, pd.Timestamp(cycle["billing_month"]))
    return dict(
        lines=lines, next_state={}, is_complete_bill=True, excluded_components=[],
        rate_sources=[*rate["sources"], *RULE_SOURCES], rate_evidence_status="verified",
        assumption_model=None, rate_assumptions=[],
        metrics={**cycle, **history, "base_distribution_usd": base, "raw_import_kwh": usage,
                 "distribution_minimum_usd": customer, "ue_gen_status": account["ue_gen_status"],
                 "excise_tax_basis": "filed_OET_billed_kwh_blocks",
                 "state_tax_cat_gross_up_applied": False, "billing_demand_applied": False,
                 "rounded_cash_optimum_claimed": False},
        warnings=[
            "The filed customer charge is the distribution minimum. DM demand history establishes classification, without a demand price.",
            "Only ordinary state excise is modeled. Separate printed-bill rounding and other account adjustments require independent evidence.",
            "The study models zero export and approved PV/paired storage under the ordinary tariff.",
        ],
    )
