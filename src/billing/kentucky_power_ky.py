"""Kentucky Power RS and bounded non-demand secondary GS, without exports."""
import numpy as np
import pandas as pd

from .kentucky_power_ky_rates import CODES, COVERAGE, GAPS, SOURCES, rates_for_cycle

UTILITY = "kentucky_power_kentucky"
TIMEZONE = "America/New_York"
DEFAULT_SERVICE_MONTH = "2026-08-01"
PLANS = {"RS": "Ordinary residential", "GS": "Small non-demand secondary general service"}
MAX_KW = {"RS": 25., "GS": 9.49}
MAX_KWH = {"RS": 2000., "GS": 4449.}
CONFIRMATIONS = {
    "eligibility_confirmed": "Kentucky Power confirms the exact ordinary RS or secondary GS tariff code",
    "ordinary_service_confirmed": "One ordinary single-phase 120/240 V secondary meter, without optional rates, programs, standby or special charges",
    "full_monthly_charges_confirmed": "Complete calendar service cycle and full ordinary monthly charges, not bimonthly billing",
    "billing_assignment_confirmed": "The Company independently assigned the entered billing month to this cycle; it is not inferred from the service dates",
    "pike_tax_scope_confirmed": "Unincorporated Pike County: 3% school tax, no city franchise fee or other local charge",
}


def account_fields(plan="RS"):
    fields = [dict(name=k, type="boolean", required=True, label=v) for k, v in CONFIRMATIONS.items()]
    fields += [
        dict(name="confirmed_tariff_code", type="text", required=True, label="Exact Kentucky Power tariff code"),
        dict(name="account_source", type="text", required=True, label="Company tariff assignment and ordinary-service evidence"),
        dict(name="billing_assignment_source", type="text", required=True, label="Independent utility billing-month assignment and full-cycle evidence"),
        dict(name="tax_source", type="text", required=True, label="Location, county school tax and applicable sales-tax evidence"),
        dict(name="der_ordinary_service_confirmed", type="boolean", label="Written special agreement retains all ordinary import terms for this exact non-export equipment"),
        dict(name="der_activation_date", type="date", label="Final interconnection approval active by"),
        dict(name="der_eligibility_source", type="text", label="Written approval and ordinary-billing agreement reference"),
    ]
    if plan == "RS":
        fields += [dict(name="domicile_exemption_confirmed", type="boolean", required=True,
                        label="The Company accepted this primary domicile's residential sales-tax exemption")]
    elif plan == "GS":
        fields += [
            dict(name="gs_no_demand_meter_confirmed", type="boolean", required=True,
                 label="Company confirms retained non-demand metering, no voltage correction and no pending reclassification"),
            dict(name="gs_maximum_billing_demand_kw", type="number", required=True,
                 label="Independent actual billing-demand review, including contract and prior history, no more than 10 kW"),
            dict(name="gs_contract_capacity_kw", type="number", required=True,
                 label="Independent ordinary contract capacity, no more than 10 kW"),
            dict(name="gs_meter_review_source", type="text", required=True,
                 label="Company metering, actual-demand, contract and past-eleven-month billing-demand evidence"),
        ]
    return fields


def defaults(plan="RS"):
    if plan not in PLANS:
        raise ValueError("Select Kentucky Power ordinary RS or small non-demand secondary GS.")
    account = dict(tariff=plan, supply="bundled", export_mode="none", voltage="secondary", phase="single",
                   voltage_v=240., meter_count=1, opening_credit_usd=0., rate_evidence_mode="verified",
                   tax_jurisdiction="ky_pike_unincorporated", billing_month="2026-09-01", bill_date="2026-09-01",
                   cycle_kind="regular", cycle_source="", confirmed_tariff_code="", account_source="",
                   billing_assignment_source="", tax_source="", der_ordinary_service_confirmed=False,
                   der_activation_date="", der_eligibility_source="")
    account.update(dict.fromkeys(CONFIRMATIONS, False))
    if plan == "RS":
        account["domicile_exemption_confirmed"] = False
    else:
        account.update(gs_no_demand_meter_confirmed=False, gs_maximum_billing_demand_kw=None,
                       gs_contract_capacity_kw=None, gs_meter_review_source="")
    return account


def hypothetical_cycle_fields(day):
    """Explicit hypothetical cycle facts; never infer these for an actual bill."""
    month = pd.Timestamp(day).replace(day=1)
    billed = str((month+pd.offsets.MonthBegin()).date())
    return dict(billing_month=billed, bill_date=billed, kind="regular",
                source="Hypothetical complete calendar service cycle and full monthly charges, with a bill issued the following day",
                account_overrides=dict(billing_assignment_source="Hypothetical Company assignment to the following named utility billing month with next-day bill issuance; not an actual meter-read calendar"))


def hypothetical_defaults(plan="RS", *, day=None):
    account = defaults(plan)
    month = pd.Timestamp(day or DEFAULT_SERVICE_MONTH).replace(day=1)
    account.update(dict.fromkeys(CONFIRMATIONS, True))
    fields = hypothetical_cycle_fields(month)
    account.update(billing_month=fields["billing_month"], bill_date=fields["bill_date"],
                   cycle_kind=fields["kind"], cycle_source=fields["source"], **fields["account_overrides"])
    account.update(hypothetical_account=True, confirmed_tariff_code=CODES[plan][0],
                   account_source="Hypothetical ordinary Kentucky Power single-phase secondary account",
                   tax_source="Hypothetical confirmed unincorporated Pike County 3% school tax, no city franchise, primary-domicile exemption for RS or ordinary taxable commercial use for GS",
                   der_ordinary_service_confirmed=True, der_activation_date="2024-12-31",
                   der_eligibility_source="Hypothetical final approval and written Kentucky Power special agreement for the exact non-export PV and paired PV-only-charged storage, preserving ordinary rates and waiving standby or additional charges")
    if plan == "RS":
        account["domicile_exemption_confirmed"] = True
    else:
        account.update(gs_no_demand_meter_confirmed=True, gs_maximum_billing_demand_kw=8.,
                       gs_contract_capacity_kw=8.,
                       gs_meter_review_source="Hypothetical Company actual demand and contract review, with all eleven prior billing demands below 10 kW and retained non-demand metering")
    return account


def catalog():
    return [dict(id=plan, label=f"Kentucky Power {label}", status="supported",
                 customer_class="residential" if plan == "RS" else "commercial",
                 coverage=[dict(start=a, end=b) for a, b in COVERAGE],
                 coverage_gaps=[dict(start=a, end=b, reason=r) for a, b, r in GAPS],
                 voltage="secondary", interval_minutes=[15], supply_arrangements=["bundled"],
                 equipment_modes=["grid_only", "pv_only", "pv_battery"], solar_modes=["non_export"],
                 representative_peak_kw=3. if plan == "RS" else 5., account_fields=account_fields(plan),
                 sources=SOURCES, base_effective_start="2024-12-31",
                 eligibility="Confirmed Kentucky Power ordinary RS or secondary non-demand GS, independently assigned utility billing month and unincorporated Pike County taxes.",
                 limitations=["Complete calendar service cycles, full charges, a separately confirmed following utility billing month and a next-day bill date.",
                              "Initial RS native/import study cap 2,000 kWh; higher service-charge tier is outside scope.",
                              "GS study caps 9.49 kW and 4,449 kWh; actual billing demand and contract must independently remain at or below 10 kW.",
                              "Final approval and written special agreement preserving ordinary non-export import terms; paired storage charges only from PV.",
                              "Source conflicts and unsupported periods reject; no uniform two-year or annual-2025 coverage claim."])
            for plan, label in PLANS.items()]


def _reference(account, name):
    value = account.get(name)
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 500:
        raise ValueError(f"Document Kentucky Power {name} without personal identifiers.")


def cycle_review(account, index):
    index = pd.DatetimeIndex(index)
    step = pd.Timedelta(minutes=15)
    if (len(index) < 2 or str(index.tz) != TIMEZONE or index.hasnans
            or not np.all(index[1:]-index[:-1] == step)):
        raise ValueError("Kentucky Power requires complete consecutive 15-minute Eastern-time intervals.")
    start, stop = index[0], index[-1]+step
    if (start != start.normalize() or start.day != 1 or stop != start+pd.offsets.MonthBegin()
            or account.get("cycle_kind") != "regular" or account.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("Kentucky Power requires a complete calendar service cycle and full monthly charges.")
    billing_month = account.get("billing_month")
    bill_date = account.get("bill_date")
    try:
        assigned = pd.Timestamp(billing_month)
        bill = pd.Timestamp(bill_date)
        valid = (str(assigned.date()) == billing_month and assigned.day == 1 and assigned.tz is None
                 and str(bill.date()) == bill_date and bill.tz is None and bill.strftime("%Y-%m") == assigned.strftime("%Y-%m")
                 and assigned == stop.tz_localize(None) and bill == assigned)
    except (TypeError, ValueError):
        valid = False
    if not valid or account.get("billing_assignment_confirmed") is not True:
        raise ValueError("Kentucky Power calendar studies require a confirmed following billing month and next-day bill date.")
    _reference(account, "billing_assignment_source")
    rates = rates_for_cycle(start.strftime("%Y-%m"), assigned.strftime("%Y-%m"))
    return dict(service_start=str(start.date()), service_end=str(index[-1].date()),
                billing_month=billing_month, bill_date=bill_date,
                elapsed_hours=float((stop-start)/pd.Timedelta(hours=1)), source_version=rates["source_version"],
                source_grade=rates["source_grade"]), rates


def validate_account(account, index, equipment=None):
    if (not isinstance(account, dict) or account.get("tariff") not in PLANS
            or account.get("confirmed_tariff_code") not in CODES[account["tariff"]]
            or account.get("supply") != "bundled" or account.get("export_mode") != "none"):
        raise ValueError("Confirm the Kentucky Power tariff code, bundled service and zero export.")
    if any(account.get(k) is not True for k in CONFIRMATIONS):
        raise ValueError("Confirm Kentucky Power assignment, ordinary use, full cycle, billing month and tax scope.")
    for name in ("account_source", "cycle_source", "tax_source", "billing_assignment_source"):
        _reference(account, name)
    expected = dict(voltage="secondary", phase="single", voltage_v=240., meter_count=1,
                    opening_credit_usd=0., rate_evidence_mode="verified", tax_jurisdiction="ky_pike_unincorporated")
    if (any(account.get(k) != v or isinstance(account.get(k), bool) for k, v in expected.items())
            or account.get("provisional_assumptions_accepted", False) is not False):
        raise ValueError("Kentucky Power scope is one ordinary 120/240 V secondary meter with verified unincorporated Pike County taxes.")
    cycle, _ = cycle_review(account, index)
    if account["tariff"] == "RS":
        if account.get("domicile_exemption_confirmed") is not True:
            raise ValueError("Kentucky Power RS requires the Company's accepted primary-domicile sales-tax exemption.")
    else:
        values = [account.get(k) for k in ("gs_maximum_billing_demand_kw", "gs_contract_capacity_kw")]
        if (account.get("gs_no_demand_meter_confirmed") is not True
                or any(type(v) not in (int, float) or not 0 <= v <= 10. for v in values)):
            raise ValueError("Kentucky Power GS requires independent retained non-demand metering, actual billing demand and contract capacity no more than 10 kW.")
        _reference(account, "gs_meter_review_source")
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or account.get("der_ordinary_service_confirmed") is not True:
            raise ValueError("Confirm a written Kentucky Power special agreement preserving ordinary billing for this exact non-export installation.")
        _reference(account, "der_eligibility_source")
        activation = account.get("der_activation_date")
        try:
            active = str(pd.Timestamp(activation).date()) == activation and activation <= cycle["service_start"]
        except (TypeError, ValueError):
            active = False
        if not active:
            raise ValueError("Kentucky Power final approval must be active before the service cycle.")
        if equipment.get("battery") and (equipment.get("renewable_only_charging") is not True or equipment.get("no_battery_export") is not True):
            raise ValueError("Kentucky Power paired storage requires PV-only charging and zero export.")


def validate_native_load(account, load):
    plan = account["tariff"]
    if np.max(load) > MAX_KW[plan]+1e-7 or .25*np.sum(load) > MAX_KWH[plan]+1e-7:
        raise ValueError("Kentucky Power native load exceeds the study envelope. Reduced imports cannot establish eligibility.")


def validate_state(account, index, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("Kentucky Power initial non-export service has no credit bank or demand state.")


def charge_lines(index, imports, exports, account, *, math, state=None):
    validate_state(account, index, state)
    cycle, rates = cycle_review(account, index)
    plan, col = account["tariff"], 0 if account["tariff"] == "RS" else 1
    energy = math.hours*math.sum(imports)
    if math.convex:
        math.constraints.extend([exports == 0, imports <= MAX_KW[plan], energy <= MAX_KWH[plan]])
    elif np.max(exports) > 1e-5 or np.max(imports) > MAX_KW[plan]+1e-7 or energy > MAX_KWH[plan]+1e-7:
        raise ValueError("Kentucky Power requires zero export and imports within the declared study envelope.")
    lines = dict(bundled_customer=rates["customer"][col],
                 bundled_energy=math.tiered(energy, [600.], rates["energy_rs"]) if plan == "RS" else energy*rates["energy_gs"],
                 temporary_residential_charge=energy*rates["temporary_rs"] if plan == "RS" else 0.,
                 residential_energy_assistance=rates["assistance_rs"] if plan == "RS" else 0.,
                 economic_development=rates["development_gs"] if plan == "GS" else 0.)
    for name in ("system_sales", "dsm", "federal_tax_credit", "purchase_power", "generation"):
        factor = rates[name][col] if isinstance(rates[name], tuple) else rates[name]
        lines[name] = energy*factor
    lines["deferred_tax_liability"] = energy*rates["deferred_tax"][col]
    nonfuel_base = sum(lines.values())-energy*rates["embedded_fuel"]
    lines["fuel_adjustment"] = energy*rates["fac"]
    lines["fuel_transition_credit"] = energy*rates["fuel_credit"][col]
    basis = sum(lines.values()) if plan == "RS" else nonfuel_base
    lines["decommissioning"] = basis*rates["decommissioning"][col]
    # PSC2025-00307: SSR applies to DR; DR does not apply to SSR.
    # The utility XLS continues to omit DR from SSR and is not authoritative here.
    lines["securitized"] = (basis+lines["decommissioning"])*rates["securitized"][col]
    lines["environmental"] = basis*rates["environmental"][col]
    lines["school_tax"] = sum(lines.values())*rates["school_tax"]
    lines["city_franchise"] = 0.
    lines["sales_tax"] = sum(lines.values())*rates["commercial_sales_tax"] if plan == "GS" else 0.
    return dict(lines=lines, next_state={}, is_complete_bill=True, excluded_components=[],
                rate_sources=rates["sources"], rate_evidence_status="verified", assumption_model=None, rate_assumptions=[],
                metrics={**cycle, "raw_import_kwh": energy, "billing_demand_applied": False,
                         "confirmed_tariff_code": account["confirmed_tariff_code"],
                         "school_tax_fraction": .03, "sales_tax_fraction": 0. if plan == "RS" else .06,
                         "ssr_includes_decommissioning": True, "rounded_cash_optimum_claimed": False},
                warnings=["The billing month is an independent Company assignment, not inferred from service dates or calculator file names.",
                          "Filed sheets and PSC orders govern corrected environmental factors, tiered base rates and SSR application to DR.",
                          "Initial study bounds exclude higher RS service-charge tiers and measured-demand GS. Component rounding can differ from a utility invoice."])
