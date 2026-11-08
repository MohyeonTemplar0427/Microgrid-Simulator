"""Duke Energy Kentucky ordinary RS and bounded small single-phase DS.

Initial settlement is strictly non-export. Assignment, tax location, demand
history and permission to retain ordinary import terms are independent facts.
"""
import numpy as np
import pandas as pd

from .duke_ky_rates import COVERAGE, GAPS, SOURCES, rates_for_cycle

UTILITY = "duke_energy_kentucky"
TIMEZONE = "America/New_York"
DEFAULT_SERVICE_MONTH = "2026-04-01"
PLANS = {"RS": "Residential Service", "DS": "Small single-phase secondary distribution service"}
MAX_KW = {"RS": 25., "DS": 14.99}
MAX_KWH = {"RS": 10000., "DS": 5999.}
CONFIRMATIONS = {
    "eligibility_confirmed": "Duke Kentucky independently assigned this ordinary RS or DS tariff",
    "ordinary_service_confirmed": "One ordinary single-phase 120/240 V secondary meter, without optional programs, standby, special facilities, lighting or other charges",
    "full_monthly_charges_confirmed": "Complete regular calendar service cycle with full ordinary monthly charges",
    "billing_assignment_confirmed": "Duke independently confirmed the named utility billing month, bill date and applicable monthly factors",
    "boone_tax_scope_confirmed": "Unincorporated Boone County, Boone County school district: 3% school levy and no city franchise fee or other local charge",
}


def account_fields(plan="RS"):
    fields = [dict(name=k, type="boolean", required=True, label=v) for k, v in CONFIRMATIONS.items()]
    fields += [
        dict(name="account_source", type="text", required=True, label="Duke Kentucky tariff assignment and ordinary-meter evidence"),
        dict(name="billing_assignment_source", type="text", required=True, label="Independent utility billing-month, bill-date and full-cycle evidence"),
        dict(name="tax_source", type="text", required=True, label="School district, unincorporated location and tax-status evidence"),
        dict(name="der_ordinary_service_confirmed", type="boolean", label="Written Duke approval and agreement preserves all ordinary import terms for this exact non-export installation"),
        dict(name="der_activation_date", type="date", label="Final interconnection approval active by"),
        dict(name="der_eligibility_source", type="text", label="Written final approval and ordinary-billing agreement reference, including paired storage if applicable"),
    ]
    if plan == "RS":
        fields.append(dict(name="domicile_exemption_confirmed", type="boolean", required=True,
                           label="Duke accepted this primary domicile's residential sales-tax exemption for the complete cycle"))
    elif plan == "DS":
        fields += [
            dict(name="ds_retained_assignment_confirmed", type="boolean", required=True,
                 label="Duke confirms ordinary DS, no former Rate C, primary-meter adjustment, PF surcharge, special facilities or pending reclassification"),
            dict(name="ds_billing_demand_ceiling_kw", type="number", required=True,
                 label="Independent current billing-demand ceiling, including summer ratchet and all demand adjustments, from 1 to 15 kW"),
            dict(name="ds_history_through_month", type="date", required=True,
                 label="First day of the final billing month in the preceding twelve-month demand review"),
            dict(name="ds_monthly_demands_kw", type="number_array", required=True,
                 label="Twelve independently reviewed actual monthly demands, oldest first, each no more than 15 kW"),
            dict(name="ds_review_source", type="text", required=True,
                 label="Duke retained assignment, power factor, summer ratchet and prior twelve-month demand evidence"),
        ]
    return fields


def defaults(plan="RS"):
    if plan not in PLANS:
        raise ValueError("Select Duke Kentucky ordinary RS or bounded single-phase secondary DS.")
    account = dict(tariff=plan, supply="bundled", export_mode="none", voltage="secondary", phase="single",
                   voltage_v=240., meter_count=1, opening_credit_usd=0., rate_evidence_mode="verified",
                   tax_jurisdiction="ky_boone_unincorporated", billing_month="2026-05-01", bill_date="2026-05-01",
                   cycle_kind="regular", cycle_source="", account_source="", billing_assignment_source="",
                   tax_source="", der_ordinary_service_confirmed=False, der_activation_date="", der_eligibility_source="")
    account.update(dict.fromkeys(CONFIRMATIONS, False))
    if plan == "RS":
        account["domicile_exemption_confirmed"] = False
    else:
        account.update(ds_retained_assignment_confirmed=False, ds_billing_demand_ceiling_kw=None,
                       ds_history_through_month="", ds_monthly_demands_kw=[], ds_review_source="")
    return account


def hypothetical_cycle_fields(day):
    """Explicit hypothetical clock/history facts, never facts about a real bill."""
    month = pd.Timestamp(day).replace(day=1)
    next_month = month+pd.offsets.MonthBegin()
    bill_day = pd.offsets.BDay().rollforward(next_month)
    return dict(billing_month=str(next_month.date()), bill_date=str(bill_day.date()), kind="regular",
                source="Hypothetical complete calendar service cycle with full charges and a following first-business-day bill",
                account_overrides=dict(
                    billing_assignment_source="Hypothetical independent Duke assignment to the following named billing month and first-business-day bill date; not an actual read calendar",
                    ds_history_through_month=str(month.date()), ds_monthly_demands_kw=[8.]*12,
                    ds_review_source="Hypothetical Duke demand review: twelve prior actual billing-month demands of 8 kW, PF at least 90%, no primary adjustment, summer ratchet at most 6.8 kW, ordinary retained DS"))


def hypothetical_defaults(plan="RS", *, day=None):
    account = defaults(plan)
    fields = hypothetical_cycle_fields(day or DEFAULT_SERVICE_MONTH)
    account.update(dict.fromkeys(CONFIRMATIONS, True))
    account.update(billing_month=fields["billing_month"], bill_date=fields["bill_date"],
                   cycle_kind=fields["kind"], cycle_source=fields["source"], **fields["account_overrides"])
    account.update(hypothetical_account=True,
                   account_source="Hypothetical ordinary Duke Energy Kentucky single-phase secondary account with no additional charges",
                   tax_source="Hypothetical confirmed unincorporated Boone County and Boone County school district, 3% school levy, no city franchise; RS accepted primary-domicile exemption or DS ordinary taxable commercial use",
                   der_ordinary_service_confirmed=True, der_activation_date="2025-01-01",
                   der_eligibility_source="Hypothetical final Duke interconnection approval and written auxiliary/supplementary agreement covering the exact non-export PV and paired PV-only-charged storage, retaining ordinary RS/DS rates with no GSS, standby or additional charges")
    if plan == "RS":
        account["domicile_exemption_confirmed"] = True
    else:
        account.update(ds_retained_assignment_confirmed=True, ds_billing_demand_ceiling_kw=15.)
    return account


def catalog():
    return [dict(id=plan, label=f"Duke Kentucky {label}", status="supported",
                 customer_class="residential" if plan == "RS" else "commercial",
                 coverage=[dict(start=a, end=b) for a, b in COVERAGE],
                 coverage_gaps=[dict(start=a, end=b, reason=r) for a, b, r in GAPS],
                 voltage="secondary", interval_minutes=[15], supply_arrangements=["bundled"],
                 equipment_modes=["grid_only", "pv_only", "pv_battery"], solar_modes=["non_export"],
                 representative_peak_kw=3. if plan == "RS" else 5., account_fields=account_fields(plan),
                 sources=SOURCES, base_effective_start="2024-10-01",
                 eligibility="Confirmed ordinary Duke Kentucky RS or bounded single-phase secondary DS in unincorporated Boone County/Boone school district, independently documented billing month and tax status.",
                 limitations=["Complete April–June service cycles in 2025 and 2026 only, with verified following-month factors and first-business-day bill dates.",
                              "DS independently reviewed billing demand and all twelve prior monthly demands must be no more than 15 kW; current native/import study envelope is 14.99 kW and 5,999 kWh.",
                              "RS native/import study envelope is 25 kW and 10,000 kWh; this is a study bound, not a tariff eligibility threshold.",
                              "Non-export PV and paired PV-only-charged storage need final approval and a written agreement retaining all ordinary import terms, with no GSS/standby or additional charge.",
                              "No interim-rate refunds, transition allocation, export settlement or uniform annual/two-year coverage is claimed."])
            for plan, label in PLANS.items()]


def _reference(account, key):
    value = account.get(key)
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 500:
        raise ValueError(f"Document Duke Kentucky {key} without personal identifiers.")


def cycle_review(account, index):
    index = pd.DatetimeIndex(index)
    step = pd.Timedelta(minutes=15)
    if (len(index) < 2 or str(index.tz) != TIMEZONE or index.hasnans
            or not np.all(index[1:]-index[:-1] == step)):
        raise ValueError("Duke Kentucky requires complete consecutive 15-minute Eastern-time intervals.")
    start, stop = index[0], index[-1]+step
    if (start != start.normalize() or start.day != 1 or stop != start+pd.offsets.MonthBegin()
            or account.get("cycle_kind") != "regular" or account.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("Duke Kentucky requires a complete regular calendar service cycle and full monthly charges.")
    billing_month, bill_date = account.get("billing_month"), account.get("bill_date")
    try:
        assigned, bill = pd.Timestamp(billing_month), pd.Timestamp(bill_date)
        valid = (str(assigned.date()) == billing_month and assigned.tz is None and assigned.day == 1
                 and assigned == stop.tz_localize(None) and str(bill.date()) == bill_date
                 and bill.tz is None and bill == pd.offsets.BDay().rollforward(assigned))
    except (TypeError, ValueError):
        valid = False
    if not valid or account.get("billing_assignment_confirmed") is not True:
        raise ValueError("Duke Kentucky requires an independently confirmed following billing month and first-business-day bill date.")
    _reference(account, "billing_assignment_source")
    rates = rates_for_cycle(start.strftime("%Y-%m"), assigned.strftime("%Y-%m"))
    if bill_date != rates["bill_date"]:
        raise ValueError("Duke Kentucky billing factors are not verified for this bill date.")
    return dict(service_start=str(start.date()), service_end=str(index[-1].date()),
                billing_month=billing_month, bill_date=bill_date,
                elapsed_hours=float((stop-start)/pd.Timedelta(hours=1)),
                source_version=rates["source_version"], source_grade=rates["source_grade"]), rates


def validate_account(account, index, equipment=None):
    if (not isinstance(account, dict) or account.get("tariff") not in PLANS
            or account.get("supply") != "bundled" or account.get("export_mode") != "none"):
        raise ValueError("Confirm Duke Kentucky ordinary RS/DS bundled service and zero export.")
    if any(account.get(k) is not True for k in CONFIRMATIONS):
        raise ValueError("Confirm Duke Kentucky ordinary assignment, complete cycle, billing month and Boone tax scope.")
    for name in ("account_source", "cycle_source", "billing_assignment_source", "tax_source"):
        _reference(account, name)
    expected = dict(voltage="secondary", phase="single", voltage_v=240., meter_count=1,
                    opening_credit_usd=0., rate_evidence_mode="verified", tax_jurisdiction="ky_boone_unincorporated")
    if (any(account.get(k) != v or isinstance(account.get(k), bool) for k, v in expected.items())
            or account.get("provisional_assumptions_accepted", False) is not False
            or account.get("opening_credit_kwh", 0.) != 0.):
        raise ValueError("Duke Kentucky scope is one ordinary 120/240 V meter with verified Boone taxes and no opening credit.")
    cycle, _ = cycle_review(account, index)
    if account["tariff"] == "RS":
        if account.get("domicile_exemption_confirmed") is not True:
            raise ValueError("Duke Kentucky RS requires an accepted primary-domicile sales-tax exemption for this complete cycle.")
    else:
        ceiling, demands = account.get("ds_billing_demand_ceiling_kw"), account.get("ds_monthly_demands_kw")
        if (account.get("ds_retained_assignment_confirmed") is not True
                or type(ceiling) not in (int, float) or not np.isfinite(ceiling) or not 1 <= ceiling <= 15.
                or not isinstance(demands, list) or len(demands) != 12
                or any(type(v) not in (int, float) or not np.isfinite(v) or not 0 <= v <= 15. for v in demands)
                or account.get("ds_history_through_month") != cycle["service_start"]):
            raise ValueError("Duke Kentucky DS needs independently retained assignment, current billing-demand ceiling 1–15 kW and twelve prior actual monthly demands no more than 15 kW.")
        _reference(account, "ds_review_source")
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or account.get("der_ordinary_service_confirmed") is not True:
            raise ValueError("Confirm Duke final approval and a written agreement retaining ordinary import terms for this exact non-export equipment.")
        _reference(account, "der_eligibility_source")
        activation = account.get("der_activation_date")
        try:
            active = str(pd.Timestamp(activation).date()) == activation and activation <= cycle["service_start"]
        except (TypeError, ValueError):
            active = False
        if not active:
            raise ValueError("Duke Kentucky final interconnection approval must be active before the service cycle.")
        if equipment.get("battery") and (equipment.get("renewable_only_charging") is not True or equipment.get("no_battery_export") is not True):
            raise ValueError("Duke Kentucky paired storage requires PV-only charging and zero export.")


def validate_native_load(account, load):
    values = np.asarray(load, dtype=float)
    plan = account["tariff"]
    power_limit = min(MAX_KW[plan], account["ds_billing_demand_ceiling_kw"]) if plan == "DS" else MAX_KW[plan]
    if (values.ndim != 1 or not len(values) or not np.isfinite(values).all() or np.min(values) < 0.
            or np.max(values) > power_limit+1e-7 or .25*np.sum(values) > MAX_KWH[plan]+1e-7):
        raise ValueError("Duke Kentucky native load exceeds the study envelope. Reduced imports cannot establish DS eligibility.")


def validate_state(account, index, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("Duke Kentucky initial non-export service has no credit bank or demand state.")


def charge_lines(index, imports, exports, account, *, math, state=None):
    validate_state(account, index, state)
    cycle, rates = cycle_review(account, index)
    plan, col = account["tariff"], 0 if account["tariff"] == "RS" else 1
    power_limit = min(MAX_KW[plan], account["ds_billing_demand_ceiling_kw"]) if plan == "DS" else MAX_KW[plan]
    energy = math.hours*math.sum(imports)
    if math.convex:
        math.constraints.extend([exports == 0, imports >= 0, imports <= power_limit, energy <= MAX_KWH[plan]])
    else:
        imported, exported = np.asarray(imports), np.asarray(exports)
        if (imported.shape != (len(index),) or exported.shape != (len(index),)
                or not np.isfinite(imported).all() or not np.isfinite(exported).all()
                or np.min(imported) < 0. or np.min(exported) < 0.
                or np.max(exported) > 1e-5 or np.max(imported) > power_limit+1e-7
                or energy > MAX_KWH[plan]+1e-7):
            raise ValueError("Duke Kentucky requires complete finite nonnegative meter flows, zero export and the declared study envelope.")
    # Within this envelope DS demand is in its first free 15 kW and all energy
    # is within its first 6,000 kWh. The base-rate maximum is never binding.
    lines = dict(bundled_customer=rates["customer"][col], bundled_energy=energy*rates["energy"][col],
                 bundled_demand=0., demand_side_management=energy*rates["dsm"][col],
                 home_energy_assistance=rates["assistance_rs"] if plan == "RS" else 0.,
                 fuel_adjustment=energy*rates["fac"], profit_sharing=energy*rates["profit_sharing"])
    basis = sum(lines.values())
    if plan == "DS":
        basis -= energy*(rates["embedded_fuel"]+rates["fac"])
    lines["environmental"] = basis*rates["environmental"][col]
    lines["school_tax"] = sum(lines.values())*rates["school_tax"]
    lines["city_franchise"] = 0.
    lines["sales_tax"] = sum(lines.values())*rates["sales_tax"] if plan == "DS" else 0.
    return dict(lines=lines, next_state={}, is_complete_bill=True, excluded_components=[],
                rate_sources=rates["sources"], rate_evidence_status="verified", assumption_model=None, rate_assumptions=[],
                metrics={**cycle, "raw_import_kwh": energy, "billing_demand_applied": False,
                         "base_minimum_usd": rates["customer"][col],
                         "ds_reviewed_billing_demand_ceiling_kw": account.get("ds_billing_demand_ceiling_kw") if plan == "DS" else None,
                         "school_tax_fraction": .03, "sales_tax_fraction": .06 if plan == "DS" else 0.,
                         "rounded_cash_optimum_claimed": False},
                warnings=["The utility billing month, bill date, tariff assignment and tax district are independently confirmed account facts.",
                          "Duke's PSM positive printed factors are credits; parenthesized factors are charges. No separate PJM wholesale retail charge is added.",
                          "DS is restricted to the first energy block and free demand block, including independent history/ratchet review; base and mandatory rider adjustments remain itemized.",
                          "These complete component intersections are study bills, not actual invoices. Component rounding can differ from utility invoices."])
