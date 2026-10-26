"""Ohio Power Company ordinary RS and non-demand general-service SSO bills.

Retail riders are evaluated once here for both numerical bills and dispatch.
Transmission and capacity are filed retail components, not wholesale tags.
"""
from datetime import date

import numpy as np
import pandas as pd

from .aep_ohio_rates import COVERAGE, PLANS, SOURCES, rates_on

UTILITY = "aep_ohio"
TIMEZONE = "America/New_York"


def account_fields(plan="RS"):
    result = [dict(name=k, type="boolean", default=False, required=True, label=label)
        for k, label in (
            ("eligibility_confirmed", "Ohio Power Company distribution territory and selected ordinary rate independently confirmed"),
            ("ordinary_service_confirmed", "Ordinary single-meter SSO account: no PIPP assistance, special contracts, electric-heat legacy rates, special facilities or AMI opt-out"),
            ("full_monthly_charges_confirmed", "Complete calendar billing cycle and utility-designated billing month confirmed"),
            ("no_local_tax_confirmed", "Verified locality has no additional municipal utility/franchise charges"))]
    result += [dict(name="legacy_rate_zone", type="choice", choices=["ohio_power", "columbus_southern"],
                    default="ohio_power", required=True, label="Verified legacy Ohio Power or Columbus Southern Power rate zone"),
        dict(name="cycle_source", type="text", required=True, label="Complete meter-cycle evidence or explicit hypothetical calendar-cycle assumption"),
        dict(name="der_ordinary_service_confirmed", type="boolean", default=False,
             label="PV/storage: approved non-export installation under ordinary service or explicit utility agreement; no additional standby charges"),
        dict(name="der_eligibility_source", type="text", label="Ordinary non-export interconnection/agreement evidence or explicit hypothetical assumption"),
        dict(name="rate_evidence_mode", type="choice", choices=["verified"], default="verified", label="Verified tariff components only")]
    if plan == "GS-1":
        result.append(dict(name="non_demand_class_confirmed", type="boolean", default=False, required=True,
            label="Utility-confirmed non-demand secondary classification and history; modeled import remains below10kW"))
    return result


def defaults(plan="RS"):
    if plan not in PLANS:
        raise ValueError("Select AEP Ohio RS or GS-1/GS-NDM ordinary non-demand service.")
    return dict(tariff=plan, supply="sso", export_mode="none", eligibility_confirmed=False,
        ordinary_service_confirmed=False, full_monthly_charges_confirmed=False, no_local_tax_confirmed=False,
        non_demand_class_confirmed=False, legacy_rate_zone="ohio_power", cycle_source="",
        der_ordinary_service_confirmed=False, der_eligibility_source="", rate_evidence_mode="verified",
        provisional_assumptions_accepted=False, billing_month="2026-09-01", bill_date="2026-09-30", cycle_kind="regular",
        voltage="secondary", phase="single", voltage_v=240., power_factor=1., meter_count=1,
        opening_credit_usd=0., tax_self_assessed=False)


def hypothetical_defaults(plan="RS"):
    a = defaults(plan)
    a.update(eligibility_confirmed=True, ordinary_service_confirmed=True,
        full_monthly_charges_confirmed=True, no_local_tax_confirmed=True, non_demand_class_confirmed=True,
        hypothetical_account=True,
        cycle_source="Explicit hypothetical complete calendar meter cycle and full monthly billing charges; not actual customer billing data",
        der_ordinary_service_confirmed=True,
        der_eligibility_source="Explicit hypothetical utility-approved ordinary non-export PV/storage agreement; no standby, reserve or extra agreement charges")
    return a


def catalog():
    return [dict(id=p, label="AEP Ohio " + ("Residential RS" if p == "RS" else "Small General Service GS-1 / GS-NDM"),
        status="supported", customer_class="residential" if p == "RS" else "commercial",
        coverage=[dict(start=s, end=e) for s, e in COVERAGE], voltage="secondary", interval_minutes=[15],
        solar_modes=["non_export"], supply_arrangements=["sso"],
        equipment_modes=["grid_only", "pv_only", "pv_battery"], representative_peak_kw=3.,
        account_fields=account_fields(p), sources=SOURCES,
        eligibility="Confirmed Ohio Power Company ordinary secondary single-meter SSO account; explicit legacy rate zone, locality and non-export interconnection facts. GS non-demand maximum must remain below10kW.",
        limitations=["Complete calendar billing cycles only; no shifted/partial-period or unverified rate-change allocation. Unsupported component dates reject.",
            "GS-1 is the historical non-demand general-service schedule, renamed GS-NDM in tariff22 effectiveApril10,2026; filed schedule name and source remain dated in each bill.",
            "These selected RS/non-demand plans have no customer measured-demand charge or TOU pricing. Demand-metered GS, electric-heating/EV pilots, PIPP assistance, competitive suppliers and specialized agreements are excluded.",
            "Generation energy, capacity and auction reconciliation are retail SSO components. BasicTransmission is charged separately once; no extra PJM LMP, PLC or NSPL amount is added.",
            "Non-export PV/storage requires independently confirmed ordinary-service/agreement eligibility. No NEM credit, export settlement, standalone-storage or standby estimate."])
        for p in PLANS]


def cycle_review(a, index):
    idx = pd.DatetimeIndex(index)
    if a.get("rate_evidence_mode", "verified") != "verified" or a.get("provisional_assumptions_accepted", False) is not False:
        raise ValueError("AEP Ohio has no provisional-rate model; only verified component coverage is permitted.")
    if len(idx) < 2 or str(idx.tz) != TIMEZONE:
        raise ValueError("AEP Ohio requires America/New_York interval timestamps.")
    step = idx[1] - idx[0]
    if step != pd.Timedelta(minutes=15) or not np.all(idx[1:] - idx[:-1] == step):
        raise ValueError("AEP Ohio requires consecutive15-minute intervals without gaps or duplicate timestamps.")
    stop = idx[-1] + step
    if (idx[0] != idx[0].normalize() or idx[0].day != 1 or stop != idx[0] + pd.offsets.MonthBegin()
            or a.get("cycle_kind") != "regular" or a.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("AEP Ohio first scope requires complete calendar cycles; partial/shifted allocation is unverified.")
    if a.get("billing_month") != str(idx[0].date()) or a.get("bill_date") != str(idx[-1].date()):
        raise ValueError("AEP Ohio designated billing month must align with service and bill date with the final service day.")
    r = rates_on(str(idx[0].date()), a["tariff"], bill_date=a["bill_date"], zone=a.get("legacy_rate_zone"))
    rates_on(str(idx[-1].date()), a["tariff"], bill_date=a["bill_date"], zone=a.get("legacy_rate_zone"))
    return dict(cycle_days=(stop.date() - idx[0].date()).days,
        elapsed_hours=float((stop - idx[0]) / pd.Timedelta(hours=1)), monthly_charge_factor=1.,
        service_start=str(idx[0].date()), service_end=str(idx[-1].date()),
        billing_month=a["billing_month"], bill_date=a["bill_date"], partial_period_proration_applied=False), r


def evidence(index, account):
    cycle_review(account, index)
    return dict(rate_evidence_status="verified", assumption_model=None, rate_assumptions=[],
                objective_scope="complete_utility_bill")


def validate_account(a, index, equipment=None):
    if (not isinstance(a, dict) or a.get("tariff") not in PLANS or a.get("supply") != "sso"
            or a.get("export_mode") != "none"):
        raise ValueError("Select AEP Ohio ordinary RS/GS-1 SSO with zero export; other supply arrangements are unsupported.")
    if any(a.get(k) is not True for k in ("eligibility_confirmed", "ordinary_service_confirmed", "no_local_tax_confirmed")):
        raise ValueError("Confirm Ohio Power territory, ordinary SSO eligibility and absent additional locality charges.")
    if not isinstance(a.get("cycle_source"), str) or not 1 <= len(a["cycle_source"].strip()) <= 500:
        raise ValueError("Document the complete AEP Ohio cycle or explicit hypothetical assumption.")
    if ((a.get("voltage"), a.get("phase"), a.get("voltage_v"), a.get("power_factor")) != ("secondary", "single", 240., 1.)
            or a.get("meter_count") != 1 or a.get("opening_credit_usd") != 0. or a.get("tax_self_assessed") is not False):
        raise ValueError("AEP Ohio first scope is ordinary240V single-phase secondary, one meter, unity PF, standard kWh tax and zero carried credit.")
    if a["tariff"] == "GS-1" and a.get("non_demand_class_confirmed") is not True:
        raise ValueError("Confirm utility-approved non-demand GS class/history independently of synthetic peak demand.")
    cycle_review(a, index)
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if (not equipment.get("pv") or a.get("der_ordinary_service_confirmed") is not True
                or not isinstance(a.get("der_eligibility_source"), str)
                or not 1 <= len(a["der_eligibility_source"].strip()) <= 500):
            raise ValueError("AEP Ohio requires confirmed ordinary non-export PV/storage; standalone storage or assumed standby eligibility is unsupported.")


def validate_state(a, index, *, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("AEP Ohio ordinary non-export non-demand schedules have no modeled opening credit or demand state.")


def charge_lines(index, imports, exports, a, *, math, state=None):
    validate_state(a, index, state=state)
    cycle, r = cycle_review(a, index)
    if math.convex:
        math.constraints.append(exports == 0)
        if a["tariff"] == "GS-1":
            math.constraints.append(imports <= 9.999999)
    elif np.max(exports) > 1e-5 or a["tariff"] == "GS-1" and np.max(imports) >= 10.:
        raise ValueError("AEP Ohio non-export non-demand GS cases must retain maximum imports below10kW.")
    kwh = math.hours * math.sum(imports)
    lines = dict(distribution_customer=r["customer"], distribution_energy=kwh*r["distribution_energy"])
    distribution_base = sum(lines.values())
    for name, factor in r["base_percent"].items():
        lines[name] = distribution_base*factor
    for name, amount in r["monthly"].items():
        lines[name] = amount
    for name, factor in r["energy"].items():
        lines[name] = kwh*factor
    lines["ohio_kwh_tax"] = math.tiered(kwh, [2000., 15000.], [.00465, .00419, .00363])
    lines["percentage_income_payment"] = math.tiered(kwh, [833000.], [r["pipp"], .0001756])
    if a["tariff"] == "GS-1":
        lines["legacy_generation_resource"] = math.tiered(kwh, [833000.], [r["legacy_generation"], 0.])
        lines["solar_generation_fund"] = math.minimum(math.tiered(kwh, [833000.], [r["solar_generation"], 0.]), 242.)
    else:
        lines["legacy_generation_resource"] = r["legacy_generation"]
        lines["solar_generation_fund"] = r["solar_generation"]
    return dict(lines=lines, metrics={**cycle,
        "filed_schedule":r["filed_schedule"], "base_version":r["base_version"],
        "legacy_rate_zone":a["legacy_rate_zone"], "rider_versions":r["versions"],
        "measured_demand_charge":False, "intraday_time_of_use_pricing":False,
        "distribution_percentage_basis":"Base distribution customer plus energy only; riders excluded",
        "capacity_transmission_treatment":"Filed SSO generation energy/capacity/auction and retail BasicTransmission once; no additional wholesale LMP/PLC/NSPL charges",
        "rate_effective_basis":"Complete designated calendar billing month; LGR/SGF cancellation applies to bills effectiveAugust14,2025",
        "generation_program":"Confirmed ordinary non-export PV/storage" if a.get("der_ordinary_service_confirmed") is True else "Ordinary absent-DER service"},
        next_state={}, is_complete_bill=True, rate_evidence_status="verified", assumption_model=None,
        rate_assumptions=[], rate_sources=SOURCES,
        warnings=["Hypothetical ordinary non-export account; service territory, legacy zone, tariff enrollment, locality and interconnection are independent confirmed facts.",
                  "No customer demand charge or TOU incentive exists in these selected schedules. Representative electrical replay does not establish site-specific engineering approval."])
