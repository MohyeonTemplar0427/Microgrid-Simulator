"""Ordinary DTE Michigan full-service D1.11/D3/D3.11 monthly bills.

Retail charges alone enter dispatch. MISO prices and resource-adequacy zones
are separate metadata. No demand, export credit, standby or choice billing is
invented. See docs/DTE.md for the account and cycle support boundary.
"""
from copy import deepcopy
from datetime import date

import numpy as np
import pandas as pd

from .dte_rates import SOURCES, THROUGH, service_rates, rendered_rates

UTILITY = "dte_electric"
TIMEZONE = "America/New_York"
PLANS = ("D1.11", "D3", "D3.11")


def periods(index, plan):
    idx = pd.DatetimeIndex(index)
    start, stop = (15, 19) if plan == "D1.11" else (13, 17)
    # C11 holiday exclusions expressly name D4/D11/D8/R3. They do not amend
    # these schedules' Monday–Friday definition, including weekday holidays.
    peak = (idx.dayofweek < 5) & (idx.hour >= start) & (idx.hour < stop) if plan != "D3" else np.zeros(len(idx), bool)
    summer = (idx.month >= 6) & (idx.month <= 9)
    return np.asarray(peak), np.asarray(summer)


def interval_rates(index, plan):
    idx = pd.DatetimeIndex(index)
    peak, summer = periods(idx, plan)
    slot = np.where(summer, 0, 2)+np.where(peak, 0, 1)
    # Cache by local service date, preserving DST and actual interval energy.
    versions = {d: service_rates(d, plan) for d in set(idx.date)}
    rates = {key: np.array([versions[d][key][i] for d, i in zip(idx.date, slot)]) for key in ("capacity", "energy")}
    rates.update({key: np.array([versions[d][key] for d in idx.date]) for key in ("distribution", "nuclear", "irm")})
    return rates


def account_fields(plan="D1.11"):
    fields = [
        dict(name="eligibility_confirmed", type="boolean", default=False, required=True, label="DTE Electric Michigan territory and tariff eligibility confirmed independently of the map"),
        dict(name="ordinary_service_confirmed", type="boolean", default=False, required=True, label="Ordinary full service; no discounts, special riders, self-directed EWR or retail choice"),
        dict(name="local_charges_confirmed", type="boolean", default=False, required=True, label="No additional locality/franchise charges or tax exemptions apply"),
        dict(name="full_monthly_charges_confirmed", type="boolean", default=False, required=True, label="Complete regular monthly meter cycle; full monthly fixed charges apply"),
        dict(name="bill_date", type="date", required=True, label="Bill rendered date · determines PSCR, EWR and securitization riders"),
        dict(name="cycle_source", type="text", required=True, label="Meter-cycle evidence or explicit hypothetical calendar-cycle assumption"),
        dict(name="dg_enrollment_confirmed", type="boolean", default=False, label="PV/storage: utility-approved Category 1 Rider 18 DG, including sizing and storage arrangement"),
        dict(name="dg_source", type="text", label="DG eligibility/interconnection evidence or explicit hypothetical assumption; no personal identifiers"),
    ]
    if plan == "D3.11":
        fields.append(dict(name="tou_enrollment_confirmed", type="boolean", default=False, required=True,
                           label="D3.11 interval-meter enrollment and 12-month commitment confirmed"))
    return fields


def defaults(plan="D1.11"):
    if plan not in PLANS:
        raise ValueError("Choose DTE D1.11, D3 or D3.11.")
    res = plan == "D1.11"
    return dict(tariff=plan, supply="full_service", export_mode="none", eligibility_confirmed=False,
                ordinary_service_confirmed=False, local_charges_confirmed=False, full_monthly_charges_confirmed=False,
                tou_enrollment_confirmed=False, dg_enrollment_confirmed=False, dg_source="", opening_credit_usd=0.,
                billing_month="2026-09-01", bill_date="2026-09-30", cycle_kind="regular", cycle_source="",
                voltage="secondary", phase="single" if res else "three", voltage_v=240. if res else 480., power_factor=1.)


def hypothetical_defaults(plan="D1.11"):
    a = defaults(plan)
    a.update(eligibility_confirmed=True, ordinary_service_confirmed=True, local_charges_confirmed=True,
             full_monthly_charges_confirmed=True, tou_enrollment_confirmed=True, hypothetical_account=True,
             cycle_source="Hypothetical complete calendar meter cycle; full monthly charges; no actual customer statement",
             dg_enrollment_confirmed=True, dg_source="Hypothetical approved Category 1 Rider 18 account; aggregate DER ≤20 kW, utility-approved annual sizing and storage; zero exports and no opening credits")
    return a


def catalog():
    return [dict(id=p, label={"D1.11": "DTE Residential Standard TOU D1.11", "D3": "DTE Commercial General Service D3",
                              "D3.11": "DTE Commercial TOU General Service D3.11"}[p], status="supported",
                 customer_class="residential" if p == "D1.11" else "commercial",
                 coverage=[dict(start="2025-06-01" if p == "D3.11" else "2025-01-01", end=THROUGH)],
                 voltage="secondary", solar_modes=["non_export"], supply_arrangements=["full_service"],
                 equipment_modes=["grid_only", "pv_only", "pv_battery"], account_fields=account_fields(p), sources=SOURCES,
                 representative_peak_kw=2. if p == "D1.11" else 20.,
                 eligibility="Confirmed DTE Michigan full-service monthly account. D1.11 single/double occupancy; D3/D3.11 ordinary commercial ≤1000 kW. DER requires approved Category 1 Rider 18 with no export/credit bank.",
                 limitations=["26–35-day complete regular monthly cycles only; full monthly fixed charges must be confirmed. Partial, initial and final cycle proration is unsupported.",
                              "Service-date base/NS/IRM; bills-rendered PSCR/EWR/securitization/LIEAF. Actual billed PSCR verified through September 2026 only.",
                              "No measured demand charge on these plans. Capacity and transmission are bundled; no additional MISO LMP/PLC/network-tag charge.",
                              "No export credit, legacy NEM, standby, self-directed EWR, RIA/low-income discount, EV-specific service or retail-choice model.",
                              "MISO LRZ7 is a resource-adequacy zone, not a retail territory, PJM transmission zone or wholesale price node."])
            for p in PLANS]


def cycle_review(a, index):
    idx = pd.DatetimeIndex(index)
    if len(idx) < 2 or str(idx.tz) != TIMEZONE:
        raise ValueError("DTE requires at least two Eastern-time intervals.")
    step = idx[1]-idx[0]
    if step not in (pd.Timedelta(minutes=15), pd.Timedelta(minutes=30)) or not np.all(idx[1:]-idx[:-1] == step):
        raise ValueError("DTE meter intervals must be consecutive 15/30-minute averages in elapsed time; no missing data.")
    stop = idx[-1]+step
    days = (stop.date()-idx[0].date()).days
    if (idx[0] != idx[0].normalize() or stop != stop.normalize() or not 26 <= days <= 35
            or a.get("cycle_kind") != "regular" or a.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("DTE first scope requires a complete regular 26–35-day cycle with confirmed full monthly charges; partial/initial/final proration is unsupported.")
    try:
        bill = date.fromisoformat(a["bill_date"])
        month = date.fromisoformat(a["billing_month"])
        if (bill.isoformat() != a["bill_date"] or month.isoformat() != a["billing_month"] or month.day != 1
                or (bill.year, bill.month) != (month.year, month.month) or bill < idx[-1].date()):
            raise ValueError("Inconsistent bill dates")
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("DTE requires an ISO bill date on/after service, and its matching first-of-month billing designation.") from exc
    service_rates(idx[0].date(), a["tariff"])
    service_rates(idx[-1].date(), a["tariff"])
    rendered_rates(bill, a["tariff"] == "D1.11")
    return dict(cycle_days=days, elapsed_hours=float((stop-idx[0])/pd.Timedelta(hours=1)),
                bill_date=str(bill), service_start=str(idx[0].date()), service_end=str(idx[-1].date()),
                base_versions=sorted({service_rates(d, a["tariff"])["version"] for d in set(idx.date)}),
                monthly_charge_factor=1., partial_period_proration_applied=False)


def validate_account(a, index, equipment=None):
    if not isinstance(a, dict) or a.get("tariff") not in PLANS or a.get("supply") != "full_service" or a.get("export_mode") != "none":
        raise ValueError("DTE supports ordinary full-service D1.11/D3/D3.11 with zero exports; no retail choice or export settlement.")
    if any(a.get(k) is not True for k in ("eligibility_confirmed", "ordinary_service_confirmed", "local_charges_confirmed")):
        raise ValueError("Confirm DTE territory, ordinary service and absence of additional locality charges/exemptions.")
    if not isinstance(a.get("cycle_source"), str) or not a["cycle_source"].strip():
        raise ValueError("Document the complete monthly meter cycle; omit personal identifiers.")
    if a.get("opening_credit_usd") != 0.:
        raise ValueError("DTE opening export-credit banks are unsupported; use a confirmed zero bank.")
    res = a["tariff"] == "D1.11"
    allowed = (("single", 240.),) if res else (("single", 240.), ("three", 480.))
    if a.get("voltage") != "secondary" or a.get("power_factor") != 1. or (a.get("phase"), a.get("voltage_v")) not in allowed:
        raise ValueError("DTE first replay supports secondary unity-PF 240-V single-phase residential/commercial or 480-V three-phase commercial service.")
    if a["tariff"] == "D3.11" and a.get("tou_enrollment_confirmed") is not True:
        raise ValueError("Confirm D3.11 enrollment, interval meter and 12-month commitment.")
    cycle_review(a, index)
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or a.get("dg_enrollment_confirmed") is not True or not isinstance(a.get("dg_source"), str) or not a["dg_source"].strip():
            raise ValueError("DTE DER needs confirmed Category 1 Rider 18 renewable-PV enrollment, utility-approved sizing and storage arrangement; ordinary non-export operation alone does not waive standby rules.")
        aggregate = max(equipment.get("pv_dc_kw", 0.), equipment.get("pv_ac_kw", 0.))+equipment.get("battery_kw", 0.)
        if aggregate > 20.+1e-8:
            raise ValueError("DTE first DG scope conservatively limits PV nameplate plus battery discharge rating to 20 kW aggregate.")


def commercial_ewr(energy, fees, math):
    # Continuous imported energy is compared to the printed upper thresholds.
    # Only floating-point ties (one milliwatt-hour) are snapped to a printed
    # boundary; other bill lines retain the actual integrated energy. The
    # strictly increasing fees select the lower band at an exact MILP tie.
    # Apply the identical cutoff to numeric bills, bounded shortcuts and MILP
    # graphs. A numeric-only snap would misprice a constant bound just above
    # 850/1650 kWh by an entire fee band despite microscopic energy noise.
    first, second = 850.+1e-6, 1650.+1e-6
    if not math.convex:
        return fees[0] if energy <= first else fees[1] if energy <= second else fees[2]
    import cvxpy as cp
    lo, hi = math.bounds(energy)
    if hi <= first or lo > second or lo > first and hi <= second:
        return fees[0] if hi <= first else fees[2] if lo > second else fees[1]
    selectors = cp.Variable(3, boolean=True)
    math.constraints.append(cp.sum(selectors) == 1)
    for i, (lower, upper) in enumerate(((lo, first), (first, second), (second, hi))):
        math.constraints.extend([energy >= lower*selectors[i]+lo*(1-selectors[i]),
                                 energy <= upper*selectors[i]+hi*(1-selectors[i])])
    return math.register(fees @ selectors, min(fees), max(fees))


def charge_lines(index, imports, exports, a, *, math, state=None):
    idx = pd.DatetimeIndex(index)
    if math.convex:
        math.constraints.append(exports == 0)
        if a["tariff"] != "D1.11":
            math.constraints.append(imports <= 1000.)
    elif np.max(exports) > 1e-5 or a["tariff"] != "D1.11" and np.max(imports) > 1000.+1e-5:
        raise ValueError("DTE requires zero exports and ordinary commercial imports ≤1000 kW.")
    if state not in (None, {}):
        raise ValueError("DTE export credits and carried settlement state are unsupported.")
    res = a["tariff"] == "D1.11"
    r = interval_rates(idx, a["tariff"])
    rendered = rendered_rates(a["bill_date"], res)
    volume = math.hours*math.sum(imports)
    lines = {key: math.hours*math.dot(imports, r[key]) for key in r}
    lines["service"] = 8.50 if res else 11.25
    for key in ("pscr", "river_rouge", "tcsc", "delivery_securitization"):
        lines[key] = volume*rendered[key]
    lines["energy_waste_reduction"] = volume*rendered["residential_ewr"] if res else commercial_ewr(volume, np.array(rendered["commercial_ewr"]), math)
    # Treasury ruling 2013-5 and DTE Explanation of Charges exempt LIEAF.
    lines["sales_tax"] = sum(lines.values())*(.04 if res else .06)
    lines["lieaf"] = rendered["lieaf"]
    peak, _ = periods(idx, a["tariff"])
    return dict(lines=lines, metrics={**cycle_review(a, idx), "peak_kwh": math.hours*math.dot(imports, peak.astype(float)),
                "off_peak_kwh": math.hours*math.dot(imports, (~peak).astype(float)), "measured_demand_charge": False,
                "pscr_usd_per_kwh": rendered["pscr"], "sales_tax_fraction": .04 if res else .06,
                "rate_effective_basis": "Base/NS/IRM: interval local service date; PSCR/EWR/securitization/LIEAF: bill rendered month/date",
                "capacity_transmission_treatment": "Bundled full-service tariff; no additional wholesale/PLC/transmission-tag charges"},
                next_state=deepcopy(state or {}), is_complete_bill=True, rate_evidence_status="verified",
                assumption_model=None, rate_assumptions=[], rate_sources=SOURCES,
                warnings=["DTE bounded ordinary full-service monthly bill. Zero exports and zero opening credit bank; DER eligibility is independently confirmed, never inferred from location.",
                          "26–35-day normal-cycle limit is this implementation's guard, not a universal DTE proration rule. Full monthly charges must be confirmed.",
                          "Historical perfect foresight within each cycle. MISO configuration is separate from retail billing; no live MISO prices, marginal emissions or site-specific circuit validation."])
