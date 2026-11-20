"""Bundled Kingsport Power RS and metered SGS in the City of Kingsport, Tennessee."""
import numpy as np
import pandas as pd

from .kingsport_tn_rates import (
    CLASSIFICATION, CODES, COVERAGE, DEFAULT_SERVICE_MONTH, GAPS, NMS, SOURCES, iso_date, rates_for_month,
)

UTILITY = "kingsport_power_tennessee"
TIMEZONE = "America/New_York"
PLANS = {"RS": "Residential Service", "SGS": "Small General Service"}
MAX_KW = {"RS": 25., "SGS": 9.999}
CONFIRMATIONS = {
    "eligibility_confirmed": "Kingsport Power confirms the selected bundled Tennessee tariff and exact account code for the study period",
    "ordinary_service_confirmed": "One ordinary secondary 120/240 V single-phase meter, full monthly charges and no optional pricing, special facilities, adjustments or estimated usage",
    "local_charges_confirmed": "Service is inside Kingsport city limits and subject to the ordinary 5% franchise fee",
    "tax_status_confirmed": "Ordinary domestic residential exemption or ordinary private taxable commercial use at 7%, with no reduced industrial rate or other tax exception",
    "billing_assignment_confirmed": "The documented billing month and actual bill issue date apply to the complete calendar service period",
    "payment_basis_confirmed": "The selected prompt-payment treatment applies; no arrears, returned payments or exceptional charges",
}


def account_fields(plan="RS"):
    fields = [dict(name=name, type="boolean", label=label, required=True) for name, label in CONFIRMATIONS.items()]
    fields.extend([
        dict(name="confirmed_tariff_code", type="choice", choices=list(CODES[plan]), required=True, label="Utility-assigned metered tariff code"),
        dict(name="payment_basis", type="choice", choices=["prompt_15_days", "gross_bill"], required=True,
             label="Paid in full within 15 days, or full undiscounted tariff bill"),
        dict(name="account_source", type="text", required=True, label="Classification, municipal, tax and payment evidence or explicit hypothetical reference"),
        dict(name="nms_approved", type="boolean", label="PV only: Kingsport approved the exact PV design, annual sizing and NMS enrollment before this cycle"),
        dict(name="nms_historical_annual_kwh", type="number", label="Historical annual site consumption reviewed by Kingsport (kWh)"),
        dict(name="nms_projected_annual_kwh", type="number", label="Kingsport-reviewed annual output for the approved PV design (kWh)"),
        dict(name="der_activation_date", type="date", label="Final Kingsport PV permission to operate active by"),
        dict(name="der_eligibility_source", type="text", label="Final PV permission, approved historical-consumption sizing, prepaid inspection, zero opening kWh bank and non-export configuration"),
        dict(name="opening_credit_kwh", type="number", label="Opening NMS bank (kWh); zero required"),
    ])
    if plan == "RS":
        fields.append(dict(name="residential_use_confirmed", type="boolean", required=True,
                           label="Ordinary individual domestic service under 015 without controlled water heating, employee or time-of-use service"))
    else:
        fields.extend([
            dict(name="normal_max_demand_kw", type="number", required=True, label="Independent utility-confirmed SGS normal maximum demand (kW, below 10)"),
            dict(name="normal_demand_source", type="text", required=True, label="Source for utility normal maximum demand and retained metered classification"),
        ])
    return fields


def defaults(plan="RS"):
    if plan not in PLANS:
        raise ValueError("Select Kingsport Power Tennessee RS or metered SGS.")
    account = dict(tariff=plan, supply="bundled", export_mode="none", phase="single", voltage="secondary",
                   voltage_v=240., meter_count=1, locality="kingsport_city", rate_evidence_mode="verified",
                   opening_credit_usd=0., opening_credit_kwh=0., confirmed_tariff_code=CODES[plan][0],
                   billing_month=DEFAULT_SERVICE_MONTH, bill_date="2026-07-31", cycle_kind="regular",
                   cycle_source="", account_source="", payment_basis="prompt_15_days",
                   nms_approved=False, nms_historical_annual_kwh=None, nms_projected_annual_kwh=None,
                   der_activation_date="", der_eligibility_source="")
    account.update(dict.fromkeys(CONFIRMATIONS, False))
    if plan == "RS":
        account["residential_use_confirmed"] = False
    else:
        account.update(normal_max_demand_kw=None, normal_demand_source="")
    return account


def hypothetical_defaults(plan="RS", *, day=None):
    account = defaults(plan)
    month = pd.Timestamp(day or DEFAULT_SERVICE_MONTH).replace(day=1)
    account.update(dict.fromkeys(CONFIRMATIONS, True))
    account.update(hypothetical_account=True, billing_month=str(month.date()),
                   bill_date=str((month + pd.offsets.MonthEnd()).date()),
                   cycle_source="Explicit hypothetical complete calendar meter cycle with a final-service-day bill",
                   account_source="Hypothetical Kingsport Power city account with ordinary municipal and Tennessee taxes and full payment within 15 days",
                   nms_approved=True, der_activation_date="2024-12-31",
                   nms_historical_annual_kwh=12000., nms_projected_annual_kwh=6000.,
                   der_eligibility_source="Hypothetical final Kingsport approval for this exact non-export solar-only system under NMS, approved annual output within verified historical consumption, all one-time charges already paid and zero opening kWh credits")
    if plan == "RS":
        account["residential_use_confirmed"] = True
    else:
        account.update(normal_max_demand_kw=6., normal_demand_source="Hypothetical utility classification and independent 6 kW SGS normal maximum demand review for all selected cycles")
    return account


def catalog():
    return [dict(id=plan, label=f"Kingsport Power {label}", status="supported",
                 customer_class="residential" if plan == "RS" else "commercial",
                 coverage=[dict(start=start, end=end) for start, end in COVERAGE],
                 coverage_gaps=[dict(start=start, end=end, reason=reason) for start, end, reason in GAPS],
                 voltage="secondary", interval_minutes=[15], supply_arrangements=["bundled"],
                 equipment_modes=["grid_only", "pv_only"], solar_modes=["non_export"],
                 representative_peak_kw=3. if plan == "RS" else 5., account_fields=account_fields(plan),
                 sources=SOURCES, base_effective_start="2022-08-08",
                 eligibility="Ordinary single-meter Kingsport city domestic RS 015 or utility-assigned metered SGS 231/232 with normal maximum demand below 10 kW.",
                 limitations=["Full calendar service cycles January 2025 through October 2026. The purchased-power rate follows the documented bill date; the storm/reliability rate follows service.",
                              "The City of Kingsport charges a 5% franchise fee. Ordinary commercial service also incurs 7% Tennessee sales tax. Prompt payment in full within 15 days earns the separate 1.5% discount.",
                              "Solar requires prior approval under NMS, solar-only operation, zero opening kWh bank and zero exports. This study covers solar up to 10 kW AC. Storage and credit settlement are unverified."])
            for plan, label in PLANS.items()]


def _reference(account, name):
    value = account.get(name)
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 500:
        raise ValueError(f"Supply documented Kingsport {name} without personal identifiers.")


def cycle_review(account, index):
    index = pd.DatetimeIndex(index)
    step = pd.Timedelta(minutes=15)
    if (len(index) < 2 or str(index.tz) != TIMEZONE or index.hasnans
            or not np.all(index[1:] - index[:-1] == step)):
        raise ValueError("Kingsport requires consecutive Eastern-time 15-minute intervals.")
    start, stop = index[0], index[-1] + step
    if (start != start.normalize() or start.day != 1 or stop != start + pd.offsets.MonthBegin()
            or account.get("cycle_kind") != "regular"):
        raise ValueError("Kingsport requires a complete ordinary calendar service cycle.")
    service = start.date().isoformat()
    bill = account.get("bill_date")
    issued = iso_date(bill)
    if account.get("billing_month") != issued.replace(day=1).isoformat():
        raise ValueError("Kingsport requires the documented month in which the bill was issued.")
    rates = rates_for_month(service, account["tariff"], bill_date=bill)
    return dict(service_start=service, service_end=str(index[-1].date()), bill_date=bill,
                billing_month=account["billing_month"], elapsed_hours=float((stop-start)/pd.Timedelta(hours=1)),
                source_version=rates["source_version"], source_grade=rates["source_grade"]), rates


def validate_account(account, index, equipment=None):
    if not isinstance(account, dict) or account.get("tariff") not in PLANS:
        raise ValueError("Select Kingsport Power RS or metered SGS.")
    plan = account["tariff"]
    expected = dict(supply="bundled", export_mode="none", voltage="secondary", phase="single", voltage_v=240.,
                    meter_count=1, locality="kingsport_city", opening_credit_usd=0., opening_credit_kwh=0.,
                    rate_evidence_mode="verified")
    if (any(account.get(key) != value or isinstance(account.get(key), bool) for key, value in expected.items())
            or account.get("provisional_assumptions_accepted", False) is not False):
        raise ValueError("Kingsport requires verified ordinary bundled city service, one secondary meter, no exports and zero opening credits.")
    if (any(account.get(key) is not True for key in CONFIRMATIONS)
            or account.get("confirmed_tariff_code") not in CODES[plan]
            or account.get("payment_basis") not in ("prompt_15_days", "gross_bill")):
        raise ValueError("Confirm Kingsport tariff assignment, account facts, billing dates, tax and payment basis.")
    for name in ("account_source", "cycle_source"):
        _reference(account, name)
    cycle, _ = cycle_review(account, index)
    if plan == "RS":
        if account.get("residential_use_confirmed") is not True:
            raise ValueError("RS 015 requires ordinary domestic residential use.")
    else:
        demand = account.get("normal_max_demand_kw")
        if type(demand) not in (int, float) or not np.isfinite(demand) or not 0 <= demand < 10.:
            raise ValueError("SGS requires independent utility-confirmed normal maximum demand below 10 kW.")
        _reference(account, "normal_demand_source")
    if equipment and equipment.get("battery"):
        raise ValueError("Kingsport battery billing and storage eligibility under Tennessee NMS are unverified.")
    if equipment and equipment.get("pv"):
        capacity = equipment.get("pv_ac_kw")
        if (account.get("nms_approved") is not True or type(capacity) not in (int, float)
                or not np.isfinite(capacity) or not 0 < capacity <= 10.):
            raise ValueError("Kingsport requires final approved solar-only NMS service at up to 10 kW AC with zero exports.")
        sizing = [account.get(name) for name in ("nms_projected_annual_kwh", "nms_historical_annual_kwh")]
        if (any(type(value) not in (int, float) or not np.isfinite(value) for value in sizing)
                or not 0 < sizing[0] <= sizing[1]):
            raise ValueError("Kingsport-approved annual solar output must be positive and within reviewed historical annual consumption.")
        if iso_date(account.get("der_activation_date")) > iso_date(cycle["service_start"]):
            raise ValueError("Kingsport solar operation must be approved by the start of service.")
        _reference(account, "der_eligibility_source")


def validate_native_load(account, load):
    values = np.asarray(load, dtype=float)
    if (not values.size or not np.isfinite(values).all() or np.min(values) < 0.
            or np.max(values) > MAX_KW[account["tariff"]] + 1e-7):
        raise ValueError("Kingsport native load exceeds the study envelope; net imports cannot establish SGS eligibility.")


def validate_state(account, index, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("Kingsport non-export service requires an empty opening credit and billing state.")


def charge_lines(index, imports, exports, account, *, math, state=None):
    validate_state(account, index, state)
    cycle, rates = cycle_review(account, index)
    plan = account["tariff"]
    if math.convex:
        math.constraints.extend([imports >= 0., exports == 0., imports <= MAX_KW[plan]])
    elif (any(np.asarray(v).shape != (len(index),) or not np.isfinite(v).all() or np.min(v) < -1e-5
              for v in (imports, exports)) or np.max(exports) > 1e-5 or np.max(imports) > MAX_KW[plan]+1e-7):
        raise ValueError("Kingsport requires finite interval imports within the study envelope and zero exports.")
    energy = math.hours * math.sum(imports)
    first = math.minimum(energy, 600.) if plan == "SGS" else energy
    lines = dict(distribution_customer=rates["customer"], distribution_energy=first*rates["first_kwh"]
                 + (energy-first)*rates["additional_kwh"])
    lines["federal_tax_rate_adjustment"] = sum(lines.values())*rates["federal_tax_adjustment"]
    lines.update(fuel_purchased_power=energy*rates["fuel"], targeted_reliability_major_storm=rates["reliability"],
                 administrative_cost=energy*rates["administrative"])
    lines["prompt_payment_discount"] = sum(lines.values())*(rates["prompt_discount"] if account["payment_basis"] == "prompt_15_days" else 0.)
    lines["kingsport_franchise_fee"] = sum(lines.values())*rates["franchise"]
    lines["tennessee_sales_tax"] = sum(lines.values())*rates["sales_tax"]
    return dict(lines=lines, next_state={}, is_complete_bill=True, excluded_components=[],
                rate_evidence_status="verified", rate_sources=[*rates["sources"], CLASSIFICATION, NMS],
                assumption_model=None, rate_assumptions=[],
                metrics={**cycle, "raw_import_kwh": energy, "locality": account["locality"],
                         "tariff_code": account["confirmed_tariff_code"], "payment_basis": account["payment_basis"],
                         "normal_max_demand_kw": account.get("normal_max_demand_kw"),
                         "billing_demand_applied": False, "monthly_minimum_usd": rates["customer"],
                         "fppar_per_kwh": rates["fuel"], "rounded_cash_optimum_claimed": False},
                warnings=["The utility's FPPAR purchases are billed at the filed retail rider. PJM wholesale prices add no separate charge.",
                          "The tariff minimum equals the service charge before applicable riders. Ordinary city tax and franchise charges follow the documented payment basis.",
                          "Study component rounding can differ by cents from invoice rounding at each intermediate step."])
