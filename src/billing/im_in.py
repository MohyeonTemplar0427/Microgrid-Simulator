"""Ordinary Indiana Michigan Power IURC No. 20 non-export service."""
import numpy as np
import pandas as pd

from .im_in_rates import BASE, COVERAGE, DER, GAPS, SALES_TAX, SALES_TAX_RATE, SOURCES, rates_for_month

UTILITY = "indiana_michigan_power_indiana"
TIMEZONE = "America/Indiana/Indianapolis"
PLANS = {"015": "RS", "016": "RS", "215": "GS", "218": "GS"}
MAX_KW = {"RS": 25., "GS": 10.}
GS_MAX_KWH = 4500.
CONFIRMATIONS = {
    "eligibility_confirmed": "I&M confirmed Indiana bundled service and the exact selected tariff code",
    "ordinary_service_confirmed": "One ordinary 120/240 V single-phase secondary meter, no voltage adjustment, optional program or special charges",
    "full_monthly_charges_confirmed": "Complete calendar meter cycle, matching bill month and full monthly charges",
    "taxable_service_confirmed": "Ordinary Indiana 7% taxable electricity service with no other account taxes or exemptions",
}


def account_fields(plan_id="015"):
    fields = [dict(name=key, type="boolean", label=label, required=True)
              for key, label in CONFIRMATIONS.items()]
    fields += [
        dict(name="confirmed_tariff_code", type="text", required=True,
             label="Exact I&M tariff code shown by the account or written utility confirmation"),
        dict(name="account_source", type="text", required=True,
             label="I&M assignment and tax evidence or explicit hypothetical account reference"),
        dict(name="der_ordinary_service_confirmed", type="boolean",
             label="Written I&M non-export agreement preserves ordinary import billing and excludes standby fees"),
        dict(name="der_activation_date", type="date", label="Final interconnection approval active by"),
        dict(name="der_eligibility_source", type="text", label="Reference for the exact approved PV or PV-plus-storage configuration"),
    ]
    if PLANS[plan_id] == "GS":
        fields += [
            dict(name="gs_no_demand_meter_confirmed", type="boolean", required=True,
                 label="I&M confirms no demand meter, no billed demand and no pending reclassification for this cycle"),
            dict(name="gs_dsm_non_opt_out_confirmed", type="boolean", required=True,
                 label="Ordinary non-opt-out DSM/EE treatment"),
            dict(name="gs_average_monthly_kwh", type="number", required=True,
                 label="Independent average monthly kWh used by I&M for its demand-meter review (below 4,500)"),
            dict(name="gs_meter_review_source", type="text", required=True,
                 label="I&M metering and average usage evidence for this cycle"),
        ]
    return fields


def defaults(plan_id="015"):
    family = PLANS[plan_id]
    start, end = COVERAGE[-1]
    account = dict(
        tariff=plan_id, supply="bundled", export_mode="none", voltage="secondary", phase="single",
        voltage_v=240., meter_count=1, opening_credit_usd=0., rate_evidence_mode="verified",
        billing_month=start, bill_date=end, cycle_kind="regular", cycle_source="", account_source="",
        confirmed_tariff_code="", der_ordinary_service_confirmed=False, der_activation_date="",
        der_eligibility_source="",
    )
    account.update(dict.fromkeys(CONFIRMATIONS, False))
    if family == "GS":
        account.update(gs_no_demand_meter_confirmed=False, gs_dsm_non_opt_out_confirmed=False,
                       gs_average_monthly_kwh=None, gs_meter_review_source="")
    return account


def hypothetical_defaults(plan_id="015", *, day=None):
    account = defaults(plan_id)
    month = pd.Timestamp(day or account["billing_month"]).replace(day=1)
    account.update(dict.fromkeys(CONFIRMATIONS, True))
    account.update(
        hypothetical_account=True, confirmed_tariff_code=plan_id,
        billing_month=str(month.date()), bill_date=str((month+pd.offsets.MonthEnd()).date()),
        cycle_source="Hypothetical complete calendar reading cycle and matching I&M bill month",
        account_source="Hypothetical ordinary single-meter I&M Indiana taxable account",
        der_ordinary_service_confirmed=True, der_activation_date="2024-12-31",
        der_eligibility_source="Hypothetical I&M special agreement for exact non-export equipment, "
                               "with ordinary billing and no standby or other charge",
    )
    if PLANS[plan_id] == "GS":
        account.update(gs_no_demand_meter_confirmed=True, gs_dsm_non_opt_out_confirmed=True,
                       gs_average_monthly_kwh=1500.,
                       gs_meter_review_source="Hypothetical I&M review of independent 1,500 kWh average "
                                              "and retained non-demand-metered secondary GS")
    return account


def catalog():
    return [
        dict(id=plan, label=f"I&M Indiana {family} ({plan})", status="supported",
             customer_class="residential" if family == "RS" else "commercial",
             coverage=[dict(start=start, end=end) for start, end in COVERAGE],
             coverage_gaps=[dict(start=start, end=end, reason=reason) for start, end, reason in GAPS],
             voltage="secondary", interval_minutes=[15], supply_arrangements=["bundled"],
             base_effective_start="2024-05-28", equipment_modes=["grid_only", "pv_only", "pv_battery"],
             solar_modes=["non_export"], representative_peak_kw=3. if family == "RS" else 5.,
             account_fields=account_fields(plan), sources=SOURCES,
             eligibility="I&M-confirmed Indiana ordinary bundled single-phase service. Secondary GS requires "
                         "independent confirmation of non-demand metering, usage review and non-opt-out DSM/EE.",
             limitations=[
                 "Verified complete matching calendar cycles only. 7% ordinary Indiana taxable service.",
                 "GS study cap of 10 kW and 4,500 kWh per cycle applies separately from utility meter eligibility.",
                 "PV and PV-charged paired storage require I&M approval preserving ordinary import billing.",
             ])
        for plan, family in PLANS.items()
    ]


def _reference(account, key):
    value = account.get(key)
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 500:
        raise ValueError(f"Document I&M Indiana {key} without personal identifiers.")


def cycle_review(account, index):
    index = pd.DatetimeIndex(index)
    step = pd.Timedelta(minutes=15)
    if (len(index) < 2 or str(index.tz) != TIMEZONE or index.hasnans
            or not np.all(index[1:]-index[:-1] == step)):
        raise ValueError("I&M Indiana requires complete consecutive 15-minute Indianapolis-time intervals.")
    start, stop = index[0], index[-1]+step
    if (start != start.normalize() or start.day != 1 or stop != start+pd.offsets.MonthBegin()
            or account.get("cycle_kind") != "regular" or account.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("I&M Indiana requires a complete calendar cycle and full monthly charges.")
    month, bill_date = str(start.date()), str(index[-1].date())
    if account.get("billing_month") != month or account.get("bill_date") != bill_date:
        raise ValueError("I&M Indiana requires matching service and billing months with a final-day bill date.")
    version, rates, sources = rates_for_month(month[:7])
    return dict(service_start=month, service_end=bill_date, billing_month=month, bill_date=bill_date,
                elapsed_hours=float((stop-start)/pd.Timedelta(hours=1)),
                source_version=f"iurc20-{version}"), rates, sources


def validate_account(account, index, equipment=None):
    if (not isinstance(account, dict) or account.get("tariff") not in PLANS
            or account.get("confirmed_tariff_code") != account["tariff"]
            or account.get("supply") != "bundled" or account.get("export_mode") != "none"):
        raise ValueError("Confirm the exact I&M Indiana tariff code, bundled service and zero export.")
    if any(account.get(key) is not True for key in CONFIRMATIONS):
        raise ValueError("Confirm I&M Indiana assignment, ordinary service, monthly charges and taxable status.")
    for key in ("account_source", "cycle_source"):
        _reference(account, key)
    expected = dict(voltage="secondary", phase="single", voltage_v=240., meter_count=1,
                    opening_credit_usd=0., rate_evidence_mode="verified")
    if (any(account.get(key) != value or isinstance(account.get(key), bool) for key, value in expected.items())
            or account.get("provisional_assumptions_accepted", False) is not False):
        raise ValueError("I&M Indiana scope is one ordinary 120/240 V secondary meter and verified rates.")
    cycle, _, _ = cycle_review(account, index)
    family = PLANS[account["tariff"]]
    if family == "GS":
        average = account.get("gs_average_monthly_kwh")
        if (account.get("gs_no_demand_meter_confirmed") is not True
                or account.get("gs_dsm_non_opt_out_confirmed") is not True
                or type(average) not in (int, float) or not 0 <= average < GS_MAX_KWH):
            raise ValueError("I&M GS requires confirmed non-demand metering, non-opt-out DSM/EE and an "
                             "independent utility-reviewed monthly average below 4,500 kWh.")
        _reference(account, "gs_meter_review_source")
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or account.get("der_ordinary_service_confirmed") is not True:
            raise ValueError("Confirm written I&M approval preserving ordinary import billing for this non-export installation.")
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
            raise ValueError("I&M paired storage requires PV-only charging and zero export.")


def validate_native_load(account, load):
    family = PLANS[account["tariff"]]
    if np.max(load) > MAX_KW[family]+1e-7 or family == "GS" and .25*np.sum(load) > GS_MAX_KWH+1e-7:
        raise ValueError("I&M native load exceeds the study envelope. Simulated import reductions cannot establish eligibility.")


def validate_state(account, index, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("I&M non-export service has no credit balance or billing-demand state.")


def charge_lines(index, imports, exports, account, *, math, state=None):
    validate_state(account, index, state)
    cycle, rates, sources = cycle_review(account, index)
    family = PLANS[account["tariff"]]
    energy = math.hours*math.sum(imports)
    limit = MAX_KW[family]
    if math.convex:
        math.constraints.extend([exports == 0, imports <= limit])
        if family == "GS":
            math.constraints.append(energy <= GS_MAX_KWH)
    elif (np.max(exports) > 1e-5 or np.max(imports) > limit+1e-7
          or family == "GS" and energy > GS_MAX_KWH+1e-7):
        raise ValueError("I&M requires zero export and imports within the plan's study envelope.")
    customer, first, over = BASE[family]
    base_energy = math.tiered(energy, (900.,), (first, over)) if family == "RS" else first*energy
    lines = {"bundled_customer": customer, "bundled_base_energy": base_energy}
    column = 0 if family == "RS" else 1
    lines.update({name: energy*(factors[column]/100.) for name, factors in rates.items()})
    lines["indiana_sales_tax"] = SALES_TAX_RATE*sum(lines.values())
    metrics = dict(**cycle, raw_import_kwh=energy, billing_demand_applied=False,
                   base_minimum_usd=customer if family == "RS" else None,
                   rounded_cash_optimum_claimed=False)
    if family == "GS":
        metrics.update(gs_average_monthly_kwh=account["gs_average_monthly_kwh"],
                       gs_no_demand_meter_confirmed=True)
    return dict(
        lines=lines, next_state={}, is_complete_bill=True, excluded_components=[],
        rate_sources=[*sources, SALES_TAX, DER], rate_evidence_status="verified",
        assumption_model=None, rate_assumptions=[], metrics=metrics,
        warnings=["I&M bundled base rates do not separately price retail supply and delivery. OSS/PJM is a retail rider.",
                  "Sales tax uses the ordinary taxable subtotal. Exact invoice rounding is outside scope."],
    )
