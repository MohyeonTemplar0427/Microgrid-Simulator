"""I&M Michigan ordinary RS and non-demand-metered secondary GS."""
import numpy as np
import pandas as pd

from .im_mi_rates import BASE, CODES, COVERAGE, GAPS, SOURCES, rates_for_month

UTILITY = "indiana_michigan_power_michigan"
TIMEZONE = "America/New_York"
PLANS = {"RS": "Residential Standard Service", "GS": "Non-demand-metered Secondary General Service"}
MAX_KW = {"RS": 25., "GS": 9.49}
GS_MAX_KWH = 4500.
CONFIRMATIONS = {
    "eligibility_confirmed": "I&M confirmed Michigan ordinary Standard Service and the exact selected tariff code",
    "ordinary_service_confirmed": "One ordinary 120/240 V single-phase secondary meter, with no optional rates, heating provision, discounts or special charges",
    "full_monthly_charges_confirmed": "Complete calendar meter cycle, matching bill month and full monthly charges",
    "taxable_service_confirmed": "Ordinary taxable Michigan residential or commercial service, with no exemption or additional local charge",
}


def account_fields(plan="RS"):
    fields = [dict(name=name, type="boolean", required=True, label=label)
              for name, label in CONFIRMATIONS.items()]
    fields += [
        dict(name="confirmed_tariff_code", type="text", required=True,
             label="Exact I&M Michigan tariff code on the account"),
        dict(name="account_source", type="text", required=True,
             label="Utility assignment, ordinary-use and tax evidence or explicit hypothetical reference"),
        dict(name="der_ordinary_service_confirmed", type="boolean",
             label="Written I&M special agreement preserves ordinary non-export import billing for this equipment"),
        dict(name="der_activation_date", type="date", label="Final interconnection approval active by"),
        dict(name="der_eligibility_source", type="text",
             label="Approval reference covering the exact PV or PV-plus-storage configuration and all billing terms"),
    ]
    if plan == "GS":
        fields += [
            dict(name="gs_no_demand_meter_confirmed", type="boolean", required=True,
                 label="I&M confirms no demand meter, billed demand, pending reclassification or metering-voltage adjustment"),
            dict(name="gs_ewr_under_10kw_confirmed", type="boolean", required=True,
                 label="I&M assigns the GS secondary under-10-kW EWR class for this cycle"),
            dict(name="gs_average_monthly_kwh", type="number", required=True,
                 label="Independent average monthly kWh used in I&M's demand-meter review, below 4,500"),
            dict(name="gs_review_peak_kw", type="number", required=True,
                 label="Independent actual maximum demand supporting I&M's under-10-kW review"),
            dict(name="gs_meter_review_source", type="text", required=True,
                 label="I&M metering, average usage and EWR classification evidence for this cycle"),
        ]
    return fields


def defaults(plan="RS"):
    if plan not in PLANS:
        raise ValueError("Select I&M Michigan RS or non-demand-metered secondary GS.")
    account = dict(tariff=plan, supply="bundled", export_mode="none", voltage="secondary", phase="single",
                   voltage_v=240., meter_count=1, opening_credit_usd=0., rate_evidence_mode="verified",
                   billing_month="2026-09-01", bill_date="2026-09-30", cycle_kind="regular", cycle_source="",
                   confirmed_tariff_code="", account_source="", der_ordinary_service_confirmed=False,
                   der_activation_date="", der_eligibility_source="")
    account.update(dict.fromkeys(CONFIRMATIONS, False))
    if plan == "GS":
        account.update(gs_no_demand_meter_confirmed=False, gs_ewr_under_10kw_confirmed=False,
                       gs_average_monthly_kwh=None, gs_review_peak_kw=None, gs_meter_review_source="")
    return account


def hypothetical_defaults(plan="RS", *, day=None):
    account = defaults(plan)
    month = pd.Timestamp(day or account["billing_month"]).replace(day=1)
    account.update(dict.fromkeys(CONFIRMATIONS, True))
    account.update(
        hypothetical_account=True, confirmed_tariff_code=CODES[plan][0],
        billing_month=str(month.date()), bill_date=str((month+pd.offsets.MonthEnd()).date()),
        cycle_source="Hypothetical complete calendar meter cycle and matching I&M billing month",
        account_source="Hypothetical ordinary I&M Michigan taxable Standard Service single-phase secondary account",
        der_ordinary_service_confirmed=True, der_activation_date="2024-12-31",
        der_eligibility_source="Hypothetical written I&M special agreement for this exact non-export PV "
                               "and paired storage, retaining ordinary import charges without other fees",
    )
    if plan == "GS":
        account.update(gs_no_demand_meter_confirmed=True, gs_ewr_under_10kw_confirmed=True,
                       gs_average_monthly_kwh=1500., gs_review_peak_kw=8.,
                       gs_meter_review_source="Hypothetical utility confirmation of non-demand metering, "
                                              "1,500 kWh average usage and under-10-kW EWR classification")
    return account


def catalog():
    return [
        dict(id=plan, label=f"I&M Michigan {label}", status="supported",
             customer_class="residential" if plan == "RS" else "commercial",
             coverage=[dict(start=start, end=end) for start, end in COVERAGE],
             coverage_gaps=[dict(start=start, end=end, reason=reason) for start, end, reason in GAPS],
             voltage="secondary", interval_minutes=[15], supply_arrangements=["bundled"],
             equipment_modes=["grid_only", "pv_only", "pv_battery"], solar_modes=["non_export"],
             representative_peak_kw=3. if plan == "RS" else 5.,
             account_fields=account_fields(plan), sources=SOURCES, base_effective_start="2024-07-15",
             eligibility="Confirmed ordinary Michigan Standard Service on one single-phase secondary meter. "
                         "GS requires independent I&M non-demand-meter and under-10-kW EWR assignment.",
             limitations=[
                 "Complete calendar service and billing cycles only. May 2025 tax-rider allocation is blocked.",
                 "RS excludes primary electric space heating, low-income, water-heating, EV and optional provisions.",
                 "GS native and import study caps are 9.49 kW and 4,500 kWh per cycle, separate from utility eligibility.",
                 "Non-export PV and PV-charged paired storage require a written I&M agreement preserving ordinary billing.",
             ])
        for plan, label in PLANS.items()
    ]


def _reference(account, name):
    value = account.get(name)
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 500:
        raise ValueError(f"Document I&M Michigan {name} without personal identifiers.")


def cycle_review(account, index):
    index = pd.DatetimeIndex(index)
    step = pd.Timedelta(minutes=15)
    if (len(index) < 2 or str(index.tz) != TIMEZONE or index.hasnans
            or not np.all(index[1:]-index[:-1] == step)):
        raise ValueError("I&M Michigan requires complete consecutive 15-minute Eastern-time intervals.")
    start, stop = index[0], index[-1]+step
    if (start != start.normalize() or start.day != 1 or stop != start+pd.offsets.MonthBegin()
            or account.get("cycle_kind") != "regular" or account.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("I&M Michigan requires a complete calendar cycle and full monthly charges.")
    month, bill_date = str(start.date()), str(index[-1].date())
    if account.get("billing_month") != month or account.get("bill_date") != bill_date:
        raise ValueError("I&M Michigan requires matching service and billing months with a final-day bill date.")
    rates = rates_for_month(month[:7])
    return dict(service_start=month, service_end=bill_date, billing_month=month, bill_date=bill_date,
                elapsed_hours=float((stop-start)/pd.Timedelta(hours=1)), source_version=rates["source_version"],
                source_grade=rates["source_grade"]), rates


def validate_account(account, index, equipment=None):
    if (not isinstance(account, dict) or account.get("tariff") not in PLANS
            or account.get("confirmed_tariff_code") not in CODES[account["tariff"]]
            or account.get("supply") != "bundled" or account.get("export_mode") != "none"):
        raise ValueError("Confirm the exact I&M Michigan tariff code, Standard Service and zero export.")
    if any(account.get(key) is not True for key in CONFIRMATIONS):
        raise ValueError("Confirm I&M Michigan assignment, ordinary use, complete cycle and taxable status.")
    for name in ("account_source", "cycle_source"):
        _reference(account, name)
    expected = dict(voltage="secondary", phase="single", voltage_v=240., meter_count=1,
                    opening_credit_usd=0., rate_evidence_mode="verified")
    if (any(account.get(key) != value or isinstance(account.get(key), bool) for key, value in expected.items())
            or account.get("provisional_assumptions_accepted", False) is not False):
        raise ValueError("I&M Michigan scope is one ordinary 120/240 V secondary meter and verified rates.")
    cycle, _ = cycle_review(account, index)
    if account["tariff"] == "GS":
        average, peak = account.get("gs_average_monthly_kwh"), account.get("gs_review_peak_kw")
        if (account.get("gs_no_demand_meter_confirmed") is not True
                or account.get("gs_ewr_under_10kw_confirmed") is not True
                or type(average) not in (int, float) or not 0 <= average < GS_MAX_KWH
                or type(peak) not in (int, float) or not 0 <= peak < 10.):
            raise ValueError("I&M Michigan GS requires independent non-demand metering, average usage below "
                             "4,500 kWh and utility-confirmed under-10-kW EWR classification.")
        _reference(account, "gs_meter_review_source")
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or account.get("der_ordinary_service_confirmed") is not True:
            raise ValueError("Confirm written I&M approval preserving ordinary billing for this exact non-export installation.")
        _reference(account, "der_eligibility_source")
        activation = account.get("der_activation_date")
        try:
            active = str(pd.Timestamp(activation).date()) == activation and activation <= cycle["service_start"]
        except (TypeError, ValueError):
            active = False
        if not active:
            raise ValueError("I&M final interconnection approval must be active before the service cycle.")
        if equipment.get("battery") and (equipment.get("renewable_only_charging") is not True
                                        or equipment.get("no_battery_export") is not True):
            raise ValueError("I&M Michigan paired storage requires PV-only charging and zero export.")


def validate_native_load(account, load):
    limit = MAX_KW[account["tariff"]]
    if (np.max(load) > limit+1e-7
            or account["tariff"] == "GS" and .25*np.sum(load) > GS_MAX_KWH+1e-7):
        raise ValueError("I&M Michigan native load exceeds the study envelope. Import reduction cannot establish eligibility.")


def validate_state(account, index, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("I&M Michigan non-export service has no credit bank or demand state.")


def charge_lines(index, imports, exports, account, *, math, state=None):
    validate_state(account, index, state)
    cycle, rates = cycle_review(account, index)
    plan = account["tariff"]
    energy = math.hours*math.sum(imports)
    if math.convex:
        math.constraints.extend([exports == 0, imports <= MAX_KW[plan]])
        if plan == "GS":
            math.constraints.append(energy <= GS_MAX_KWH)
    elif (np.max(exports) > 1e-5 or np.max(imports) > MAX_KW[plan]+1e-7
          or plan == "GS" and energy > GS_MAX_KWH+1e-7):
        raise ValueError("I&M Michigan requires zero export and imports within the declared study envelope.")
    base, column = BASE[plan], 0 if plan == "RS" else 1
    lines = {"delivery_customer": base["customer"]}
    lines.update({name: energy*base[name] for name in ("supply_capacity", "supply_non_capacity", "delivery_energy")})
    lines.update(
        pscr=energy*rates["pscr"], rate_realignment=energy*rates["rate_realignment"][column],
        ewr=energy*rates["ewr"][0] if plan == "RS" else rates["ewr"][1],
        nuclear_decommissioning=0., renewable_energy=0., net_lost_revenue_supply=0., net_lost_revenue_delivery=0.,
        tax_rider_supply=energy*rates["supply_tax_credit"][column],
        tax_rider_delivery=energy*rates["delivery_tax_credit"][column],
    )
    # Treasury Letter Ruling 2013-5 exempts separately itemized LIEAF from sales tax.
    lines["michigan_sales_tax"] = sum(lines.values())*(.04 if plan == "RS" else .06)
    lines["lieaf"] = rates["lieaf"]
    return dict(
        lines=lines, next_state={}, is_complete_bill=True, excluded_components=[],
        rate_sources=rates["sources"], rate_evidence_status="verified", assumption_model=None, rate_assumptions=[],
        metrics={**cycle, "raw_import_kwh": energy, "billing_demand_applied": False,
                 "confirmed_tariff_code": account["confirmed_tariff_code"],
                 "sales_tax_fraction": .04 if plan == "RS" else .06,
                 "lieaf_excluded_from_sales_tax": True, "rounded_cash_optimum_claimed": False},
        warnings=["Ordinary Standard Service with separately itemized power supply, delivery and filed riders.",
                  "The GS EWR class uses independent utility assignment. Simulated demand does not reclassify it.",
                  "Study component rounding can differ from utility invoice rounding."],
    )
