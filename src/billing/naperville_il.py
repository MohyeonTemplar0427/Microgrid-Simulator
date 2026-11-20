"""City of Naperville flat residential and small general service, inside city limits."""
from datetime import date

import numpy as np
import pandas as pd

UTILITY = "naperville_illinois"
TIMEZONE = "America/Chicago"
ORDINANCE = "https://library.municode.com/il/naperville/ordinances/code_of_ordinances?nodeId=1330189"
SCHEDULE = "https://naperville.legistar.com/View.ashx?GUID=DB34630C-7A31-4303-9B1F-2CADADC170B3&ID=13544827&M=F"
TAX_CODE = "https://library.municode.com/il/naperville/codes/code_of_ordinances?nodeId=TIT8PUUT_CH1EL"
SURVEY = "https://www.nimpaonline.org/wp-content/uploads/2025/10/NIMPA-Comparative-Monthly-Electric-Bills-Final-Report-2025.pdf"
SOLAR_BILL = "https://www.naperville.il.us/globalassets/media/projects/electric/sustainability-grant-forms/net-metering-utility-ebill-explained---june-2025.pdf"
SOLAR = "https://www.naperville.il.us/357/Solar-Panels"
SOURCES = [ORDINANCE, SCHEDULE, TAX_CODE, SURVEY, SOLAR_BILL, SOLAR]
PLANS = {"FRS": "Flat Residential", "FGS": "Flat General Service 1"}
# Ordinance 24-123. Dollars/customer/month and dollars/kWh. Base terms alone never enable a bill.
BASE = {2025: {"FRS": (19.26, .11433), "FGS": (37.71, .11475)},
        2026: {"FRS": (21.52, .11968), "FGS": (41.77, .11933)}}
PPA = {"2025-08-01": .00535}  # Exact bill-month factor. Exhibit 21 and page 26 of the NIMPA survey.
GAP = "The monthly Naperville purchased power adjustment billed in this period has not been verified."
FLAGS = {
    "eligibility_confirmed": "City confirms FRS ordinary one-household use or FGS ordinary private GS1 service at one meter",
    "ordinary_service_confirmed": "Inside Naperville city limits, ordinary taxable flat service, full customer charge, no special facilities, power-quality fee, optional program or adjustments",
    "full_monthly_charges_confirmed": "Full calendar meter cycle with a final-day bill in the same month, applying that billing month's published PPA",
    "tax_status_confirmed": "City confirms standard 5% city use tax and ordinary state tax on this account, including correct historical tax treatment",
}


def account_fields(plan_id):
    fields = [dict(name=k, type="boolean", required=True, label=v) for k, v in FLAGS.items()]
    fields.extend([
        dict(name="account_source", type="text", required=True, label="Utility classification, bill month, tax and ordinary account evidence"),
        dict(name="der_ordinary_service_confirmed", type="boolean", label="Signed city approval and permission to operate retain ordinary import billing for this exact curtailed solar installation"),
        dict(name="der_activation_date", type="date", label="Date city permission to operate became effective"),
        dict(name="der_eligibility_source", type="text", label="Interconnection, metering and zero opening solar credit evidence"),
    ])
    if plan_id == "FGS":
        fields.extend([
            dict(name="gs_review_year", type="number", required=True, label="Year of January city GS1 assignment"),
            dict(name="gs_prior_peak_kw", type="number", required=True, label="Greatest actual monthly demand at any site meter in the previous calendar year (kW)"),
            dict(name="gs_assignment_source", type="text", required=True, label="January GS1 city review and separately documented prior-year demand"),
        ])
    return fields


def defaults(plan_id="FRS"):
    if plan_id not in PLANS:
        raise ValueError("Select Naperville FRS or FGS (GS1).")
    account = dict(tariff=plan_id, supply="bundled", export_mode="none", rate_evidence_mode="verified",
                   locality="naperville_city", voltage="secondary", voltage_v=240., phase="single", meter_count=1,
                   opening_credit_usd=0., opening_credit_kwh=0., billing_month="2025-08-01",
                   bill_date="2025-08-31", cycle_kind="regular", account_source="", cycle_source="",
                   der_ordinary_service_confirmed=False, der_eligibility_source="", der_activation_date="")
    account.update(dict.fromkeys(FLAGS, False))
    if plan_id == "FGS":
        account.update(gs_review_year=None, gs_prior_peak_kw=None, gs_assignment_source="")
    return account


def hypothetical_defaults(plan_id="FRS", *, day=None):
    a = defaults(plan_id)
    m = pd.Timestamp(day or a["billing_month"]).replace(day=1)
    a.update(dict.fromkeys(FLAGS, True))
    a.update(hypothetical_account=True, billing_month=str(m.date()), bill_date=str((m+pd.offsets.MonthEnd()).date()),
             account_source="Hypothetical one-meter city account, independently assigned flat plan and statutory taxes.",
             cycle_source="Hypothetical full calendar read and final-day city bill in the published PPA billing month.",
             der_ordinary_service_confirmed=True, der_activation_date=str(m.date()),
             der_eligibility_source="Hypothetical signed permission for this small self-owned PV, ordinary flat imports, no other charge, zero bank and verified zero export.")
    if plan_id == "FGS":
        a.update(gs_review_year=m.year, gs_prior_peak_kw=8.,
                 gs_assignment_source="Hypothetical January GS1 assignment and maximum of all prior-year site meter demands.")
    return a


def catalog():
    return [dict(id=p, label=f"Naperville {p} · {label}", customer_class="residential" if p == "FRS" else "commercial",
                 status="supported", billing_supported=True, dispatch_supported=True,
                 coverage=[dict(start="2025-08-01", end="2025-08-31")],
                 coverage_gaps=[dict(start="2025-01-01", end="2025-07-31", reason=GAP),
                                dict(start="2025-09-01", end="2026-12-31", reason=GAP)],
                 base_effective_start="2025-01-01", voltage="secondary", interval_minutes=[15],
                 supply_arrangements=["bundled"], equipment_modes=["grid_only", "pv_only"], solar_modes=["non_export"],
                 representative_peak_kw=3. if p == "FRS" else 5., account_fields=account_fields(p), sources=list(SOURCES),
                 eligibility="Inside-city ordinary FRS domestic service or an established private GS1 site assigned in the January review with all prior-year peaks below 50 kW.",
                 limitations=[GAP, "Solar requires signed active city approval, zero opening bank and zero export. Historical paired-storage import terms are unverified.",
                              "Only the statutory inside-city tax treatment is included. Accounts billed another tax basis, including historical billing errors, require separate review."])
            for p, label in PLANS.items()]


def rates_for_month(month, plan="FRS"):
    if plan not in PLANS or month not in PPA:
        raise ValueError(f"Naperville {plan} {month}: {GAP}")
    customer, energy = BASE[int(month[:4])][plan]
    return dict(customer=customer, energy=energy, ppa=PPA[month], state_per_kwh=.0032, city_tax=.05)


def cycle_review(account, index):
    index = pd.DatetimeIndex(index)
    step = pd.Timedelta(minutes=15)
    if (len(index) < 2 or str(index.tz) != TIMEZONE or index.hasnans
            or not np.all(index[1:] - index[:-1] == step)):
        raise ValueError("Naperville requires consecutive 15-minute America/Chicago intervals.")
    first, stop = index[0], index[-1]+step
    month, end = str(first.date()), str(index[-1].date())
    if (first.day != 1 or first != first.normalize() or stop != first+pd.offsets.MonthBegin()
            or account.get("cycle_kind") != "regular" or account.get("billing_month") != month
            or account.get("bill_date") != end or account.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("Naperville requires a complete calendar cycle and matching final-day bill.")
    return dict(service_start=month, service_end=end, billing_month=month, bill_date=end,
                source_version="Naperville Ord. 24-123 / NIMPA August 2025", source_grade="ordinance_and_dated_municipal_survey",
                elapsed_hours=float((stop-first)/pd.Timedelta(hours=1))), rates_for_month(month, account["tariff"])


def _reference(a, key):
    value = a.get(key)
    return isinstance(value, str) and 0 < len(value.strip()) <= 500


def validate_account(a, index, equipment=None):
    if not isinstance(a, dict) or a.get("tariff") not in PLANS:
        raise ValueError("Select Naperville FRS or FGS.")
    scope = dict(supply="bundled", export_mode="none", rate_evidence_mode="verified", locality="naperville_city",
                 voltage="secondary", voltage_v=240., phase="single", meter_count=1, opening_credit_usd=0., opening_credit_kwh=0.)
    if (any(a.get(k) != v or isinstance(a.get(k), bool) for k, v in scope.items())
            or any(a.get(k) is not True for k in FLAGS) or a.get("provisional_assumptions_accepted", False) is not False
            or not all(_reference(a, key) for key in ("account_source", "cycle_source"))):
        raise ValueError("Confirm the one-meter ordinary taxable city flat account, cycle, zero credits and zero export.")
    cycle, _ = cycle_review(a, index)
    if a["tariff"] == "FGS":
        peak = a.get("gs_prior_peak_kw")
        if (a.get("gs_review_year") != int(cycle["service_start"][:4]) or not _reference(a, "gs_assignment_source")
                or type(peak) not in (int, float) or not 0 <= peak < 50.):
            raise ValueError("FGS requires independent January GS1 assignment and every prior-year meter peak below 50 kW.")
    eq = equipment or {}
    if eq.get("battery"):
        raise ValueError("Naperville August 2025 paired-storage and storage-only import terms are unverified.")
    if eq.get("pv"):
        capacity = eq.get("pv_ac_kw")
        try:
            active = date.fromisoformat(a.get("der_activation_date", "")) <= date.fromisoformat(cycle["service_start"])
        except (ValueError, TypeError):
            active = False
        if (a.get("der_ordinary_service_confirmed") is not True or not _reference(a, "der_eligibility_source")
                or not active or type(capacity) not in (int, float) or not 0 < capacity <= 10.):
            raise ValueError("Naperville requires active city approval for the exact curtailed PV installation up to 10 kW AC within this study scope.")


def validate_native_load(a, load):
    values = np.asarray(load, dtype=float)
    if not values.size or not np.isfinite(values).all() or values.min() < 0:
        raise ValueError("Naperville requires finite, complete, nonnegative native load.")


def validate_state(account, index, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("Naperville non-export scope cannot import solar credit balances or other billing state.")


def charge_lines(index, imports, exports, account, *, math, state=None):
    validate_state(account, index, state)
    cycle, r = cycle_review(account, index)
    if math.convex:
        math.constraints.extend([imports >= 0, exports == 0])
    elif (any(np.asarray(v).shape != (len(index),) or not np.isfinite(v).all() or np.min(v) < -1e-5 for v in (imports, exports))
          or np.max(exports) > 1e-5):
        raise ValueError("Naperville requires complete nonnegative meter flows and zero export.")
    kwh = math.sum(imports)*math.hours
    lines = dict(customer=r["customer"], bundled_energy=kwh*r["energy"], purchased_power_adjustment=kwh*r["ppa"])
    lines["municipal_use_tax"] = sum(lines.values())*r["city_tax"]
    # In the verified month even the volumetric subtotal alone exceeds $0.064/kWh.
    # Therefore $0.0032/kWh is always the lesser of the two state-tax alternatives.
    lines["illinois_utility_tax"] = kwh*r["state_per_kwh"]
    return dict(lines=lines, next_state={}, is_complete_bill=True, excluded_components=[], rate_sources=list(SOURCES),
                rate_evidence_status="verified", assumption_model=None, rate_assumptions=[],
                metrics={**cycle, "raw_import_kwh": kwh, "monthly_minimum_usd": r["customer"],
                         "billed_ppa_usd_per_kwh": r["ppa"], "billing_demand_applied": False},
                warnings=["Bundled city electric charges and the billed PPA are separate from PJM prices. The study rounds each bill component to cents."])
