"""Delmarva Delaware ordinary R and SGS-ND fixed-price SOS, zero export."""
import numpy as np
import pandas as pd

from .delmarva_de_rates import COVERAGE, GAPS, SOURCES, rates_for_month

UTILITY = "delmarva_delaware"
TIMEZONE = "America/New_York"
PLANS = {"R": "Residential", "SGS-ND": "Small General Service non-demand"}
MAX_KW = {"R": 25., "SGS-ND": 10.}
SGS_NATIVE_KWH_LIMIT = 3499.
CONFIRMATIONS = {
    "eligibility_confirmed": "Delmarva confirms Delaware service, the selected classification and fixed-price SOS",
    "ordinary_service_confirmed": "One ordinary single-phase secondary meter, without special rates, assistance, optional programs or separate heating",
    "full_monthly_charges_confirmed": "Complete matching calendar service and bill month with full monthly charges",
    "local_charges_confirmed": "Ordinary unincorporated Sussex County location with no additional local charge or special tax status",
    "transmission_assignment_confirmed": "Separate Delmarva utility-assigned SOS transmission PLC and its validity dates are documented",
}


def account_fields(plan_id="R"):
    fields = [dict(name=key, type="boolean", required=True, label=value)
              for key, value in CONFIRMATIONS.items()]
    fields += [
        dict(name="account_source", type="text", required=True, label="Utility classification and locality evidence or explicit hypothetical assumption"),
        dict(name="transmission_plc_kw", type="number", required=True, label="Utility-assigned SOS transmission PLC billed in kW"),
        dict(name="transmission_valid_from", type="date", required=True, label="Transmission assignment valid from"),
        dict(name="transmission_valid_through", type="date", required=True, label="Transmission assignment valid through"),
        dict(name="transmission_assignment_source", type="text", required=True, label="Utility transmission-billing evidence, independent of simulated load"),
        dict(name="der_ordinary_service_confirmed", type="boolean", label="Written Delmarva approval permits this exact non-export installation on ordinary import billing"),
        dict(name="der_activation_date", type="date", label="Final interconnection approval active by"),
        dict(name="der_eligibility_source", type="text", label="Approved non-export agreement reference, including PV-only charging for paired storage"),
    ]
    if plan_id == "R":
        fields += [dict(name="rs_no_space_heating_confirmed", type="boolean", required=True,
                        label="Household use does not qualify for the distinct electric space-heating rate")]
    else:
        fields += [
            dict(name="sgs_assignment_confirmed", type="boolean", required=True,
                 label="Utility retains SGS-ND, without an outstanding 12-month MGS-S transfer obligation"),
            dict(name="sgs_prior_max_month_kwh", type="number", required=True,
                 label="Independent maximum monthly usage in the utility's prior classification review, below 3,500 kWh"),
            dict(name="sgs_classification_source", type="text", required=True,
                 label="Utility's retained SGS-ND assignment and independent usage/history review"),
        ]
    return fields


def defaults(plan_id="R"):
    if plan_id not in PLANS:
        raise ValueError("Select Delmarva Delaware R or SGS-ND.")
    account = dict(
        tariff=plan_id, supply="sos", export_mode="none", voltage="secondary", phase="single",
        voltage_v=240., meter_count=1, locality="sussex_unincorporated", opening_credit_usd=0.,
        rate_evidence_mode="verified", billing_month="2026-09-01", bill_date="2026-09-30",
        cycle_kind="regular", cycle_source="", account_source="", transmission_plc_kw=None,
        transmission_valid_from="", transmission_valid_through="", transmission_assignment_source="",
        der_ordinary_service_confirmed=False, der_activation_date="", der_eligibility_source="",
    )
    account.update(dict.fromkeys(CONFIRMATIONS, False))
    if plan_id == "R":
        account["rs_no_space_heating_confirmed"] = False
    else:
        account.update(sgs_assignment_confirmed=False, sgs_prior_max_month_kwh=None, sgs_classification_source="")
    return account


def hypothetical_defaults(plan_id="R", *, day=None):
    account = defaults(plan_id)
    month = pd.Timestamp(day or account["billing_month"]).replace(day=1)
    account.update(dict.fromkeys(CONFIRMATIONS, True))
    account.update(
        hypothetical_account=True, billing_month=str(month.date()),
        bill_date=str((month+pd.offsets.MonthEnd()).date()),
        cycle_source="Explicit hypothetical complete calendar meter cycle and matching bill month",
        account_source="Hypothetical ordinary Delmarva Delaware unincorporated Sussex account",
        transmission_plc_kw=2. if plan_id == "R" else 4.,
        transmission_valid_from=f"{month.year}-01-01", transmission_valid_through=f"{month.year}-12-31",
        transmission_assignment_source="Hypothetical company-assigned SOS transmission determinant retained throughout the declared year",
        der_ordinary_service_confirmed=True, der_activation_date="2024-12-31",
        der_eligibility_source="Hypothetical written Delmarva no-sale interconnection approval for exact equipment "
                               "preserving ordinary import billing, PV-only paired storage and zero export",
    )
    if plan_id == "R":
        account["rs_no_space_heating_confirmed"] = True
    else:
        account.update(sgs_assignment_confirmed=True, sgs_prior_max_month_kwh=2000.,
                       sgs_classification_source="Hypothetical utility review retaining SGS-ND with maximum prior usage 2,000 kWh and no MGS-S obligation")
    return account


def catalog():
    return [
        dict(id=plan, label=f"Delmarva Delaware {label} SOS", status="supported",
             customer_class="residential" if plan == "R" else "commercial",
             coverage=[dict(start=start, end=end) for start, end in COVERAGE],
             coverage_gaps=[dict(start=start, end=end, reason=reason) for start, end, reason in GAPS],
             voltage="secondary", interval_minutes=[15], supply_arrangements=["sos"],
             equipment_modes=["grid_only", "pv_only", "pv_battery"], solar_modes=["non_export"],
             representative_peak_kw=3., account_fields=account_fields(plan), sources=SOURCES,
             eligibility="Ordinary single-phase secondary fixed-price SOS in unincorporated Sussex County, "
                         "with independent utility classification and separately documented transmission PLC.",
             limitations=[
                 "Complete December 2025 and September–November 2026 cycles only.",
                 "SGS-ND independent history must remain below 3,500 kWh, and no outstanding MGS-S transfer obligation may apply.",
                 "The SGS-ND study bounds native load and imports to 3,499 kWh and 10 kW. RS study peak is 25 kW.",
                 "Written utility approval must preserve ordinary no-export billing for PV and PV-charged storage.",
             ])
        for plan, label in PLANS.items()
    ]


def _reference(account, key):
    value = account.get(key)
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 500:
        raise ValueError(f"Document Delmarva Delaware {key} without personal identifiers.")


def _iso_date(value):
    try:
        return str(pd.Timestamp(value).date()) == value
    except (ValueError, TypeError):
        return False


def cycle_review(account, index):
    index = pd.DatetimeIndex(index)
    step = pd.Timedelta(minutes=15)
    if (len(index) < 2 or str(index.tz) != TIMEZONE or index.hasnans
            or not np.all(index[1:]-index[:-1] == step)):
        raise ValueError("Delmarva Delaware requires complete consecutive Eastern-time 15-minute intervals.")
    start, stop = index[0], index[-1]+step
    if (start != start.normalize() or start.day != 1 or stop != start+pd.offsets.MonthBegin()
            or account.get("cycle_kind") != "regular" or account.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("Delmarva Delaware requires complete calendar cycles and full monthly charges.")
    month, end = str(start.date()), str(index[-1].date())
    if account.get("billing_month") != month or account.get("bill_date") != end:
        raise ValueError("Delmarva Delaware service and billing months must match with a final-day bill date.")
    rates = rates_for_month(month[:7], account["tariff"])
    return dict(service_start=month, service_end=end, billing_month=month, bill_date=end,
                elapsed_hours=float((stop-start)/pd.Timedelta(hours=1)),
                source_version=rates["source_version"]), rates


def validate_account(account, index, equipment=None):
    if (not isinstance(account, dict) or account.get("tariff") not in PLANS
            or account.get("supply") != "sos" or account.get("export_mode") != "none"):
        raise ValueError("Select Delmarva Delaware R/SGS-ND fixed-price SOS and zero export.")
    if any(account.get(key) is not True for key in CONFIRMATIONS):
        raise ValueError("Confirm Delmarva Delaware ordinary classification, meter cycle, locality and transmission assignment.")
    for key in ("account_source", "cycle_source", "transmission_assignment_source"):
        _reference(account, key)
    expected = dict(voltage="secondary", phase="single", voltage_v=240., meter_count=1,
                    locality="sussex_unincorporated", opening_credit_usd=0., rate_evidence_mode="verified")
    if (any(account.get(key) != value or isinstance(account.get(key), bool) for key, value in expected.items())
            or account.get("provisional_assumptions_accepted", False) is not False):
        raise ValueError("Delmarva Delaware scope requires ordinary 120/240 V secondary Sussex service and verified rates.")
    cycle, _ = cycle_review(account, index)
    plc = account.get("transmission_plc_kw")
    lo, hi = account.get("transmission_valid_from"), account.get("transmission_valid_through")
    if (type(plc) not in (int, float) or not 0 <= plc <= 10000
            or not _iso_date(lo) or not _iso_date(hi)
            or lo > cycle["service_start"] or hi < cycle["service_end"]):
        raise ValueError("Document a finite utility-assigned transmission PLC and validity covering the entire cycle.")
    if account["tariff"] == "R":
        if account.get("rs_no_space_heating_confirmed") is not True:
            raise ValueError("Confirm ordinary residential use without the distinct space-heating classification.")
    else:
        prior = account.get("sgs_prior_max_month_kwh")
        if (account.get("sgs_assignment_confirmed") is not True
                or type(prior) not in (int, float) or not 0 <= prior < 3500.):
            raise ValueError("Delmarva SGS-ND needs independent retained assignment and prior usage below 3,500 kWh.")
        _reference(account, "sgs_classification_source")
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or account.get("der_ordinary_service_confirmed") is not True:
            raise ValueError("Obtain written Delmarva approval preserving ordinary service for this exact non-export installation.")
        _reference(account, "der_eligibility_source")
        activation = account.get("der_activation_date")
        if not _iso_date(activation) or activation > cycle["service_start"]:
            raise ValueError("Delmarva final interconnection approval must predate the service cycle.")
        if equipment.get("battery") and (equipment.get("renewable_only_charging") is not True
                                        or equipment.get("no_battery_export") is not True):
            raise ValueError("Delmarva Delaware storage requires PV-only charging and zero export.")


def validate_native_load(account, load):
    if (np.max(load) > MAX_KW[account["tariff"]]+1e-7
            or account["tariff"] == "SGS-ND" and .25*np.sum(load) > SGS_NATIVE_KWH_LIMIT+1e-7):
        raise ValueError("Delmarva Delaware native load exceeds the declared study envelope. "
                         "PV-reduced imports cannot establish SGS-ND eligibility.")


def validate_state(account, index, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("Delmarva Delaware non-export service has no credit bank or billed-demand state.")


def charge_lines(index, imports, exports, account, *, math, state=None):
    validate_state(account, index, state)
    cycle, rates = cycle_review(account, index)
    plan = account["tariff"]
    energy = math.hours*math.sum(imports)
    if math.convex:
        math.constraints.extend([exports == 0, imports <= MAX_KW[plan]])
        if plan == "SGS-ND":
            math.constraints.append(energy <= SGS_NATIVE_KWH_LIMIT)
    elif (np.max(exports) > 1e-5 or np.max(imports) > MAX_KW[plan]+1e-7
          or plan == "SGS-ND" and energy > SGS_NATIVE_KWH_LIMIT+1e-7):
        raise ValueError("Delmarva Delaware imports exceed the study envelope or exports are nonzero.")
    lines = {"distribution_customer": rates["customer"], "distribution_energy": energy*rates["distribution"]}
    distribution_base = sum(lines.values())
    for name in ("supply", "procurement_cost_adjustment", "green_energy", "low_income",
                 "renewable_portfolio", "qualified_fuel_cell", "energy_efficiency", "edit_credit", "storm_expense"):
        lines[name] = energy*rates[name]
    lines["dsic"] = distribution_base*rates["dsic_fraction"]
    lines["ufrc"] = distribution_base*rates["ufrc_fraction"]
    lines["sos_transmission"] = account["transmission_plc_kw"]*rates["transmission_per_kw"]
    lines["delaware_public_utility_tax"] = sum(lines.values())*rates["public_utility_tax"]
    return dict(
        lines=lines, next_state={}, is_complete_bill=True, excluded_components=[],
        rate_sources=rates["sources"], rate_evidence_status="verified", assumption_model=None, rate_assumptions=[],
        metrics=dict(**cycle, transmission_plc_kw=account["transmission_plc_kw"],
                     transmission_determinant="Independent utility-assigned billed SOS transmission PLC",
                     raw_import_kwh=energy, billing_demand_applied=False, rounded_cash_optimum_claimed=False),
        warnings=["Ordinary unincorporated Sussex account. R has the statutory residential PUT exemption and SGS-ND has ordinary 4.25% PUT.",
                  "Filed transmission, supply and rider rates retain their embedded PSC assessment. No additional wholesale adder.",
                  "Exact utility invoice rounding and special account-specific charges remain outside this study scope."],
    )
