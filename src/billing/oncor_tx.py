"""Ordinary Oncor delivery paired with an explicitly enrolled Texas retail contract."""
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from functools import lru_cache

import numpy as np
import pandas as pd

from .oncor_tx_commercial import COMMERCIAL_OFFERS, NEC_COMMERCIAL_RATES
from .oncor_tx_delivery import delivery_rates
from .oncor_tx_residential import NEC_RESIDENTIAL_RATES, RESIDENTIAL_OFFERS
from .oncor_tx_secondary import secondary_rates

UTILITY = "oncor_texas"
TIMEZONE = "America/Chicago"
NEC = "NEC Co-op Energy"
VARIABLE = {"NEC-RES": NEC_RESIDENTIAL_RATES, "NEC-SMALL": NEC_COMMERCIAL_RATES}
FIXED = {**RESIDENTIAL_OFFERS, **COMMERCIAL_OFFERS}
DEMAND = "secondary_gt_10_kw"
TARIFF = "https://www.oncor.com/us/en/home/about-us/regulatory/tariffs-rate-schedules.html"
TAX = "https://comptroller.texas.gov/taxes/publications/96-1309.pdf"
PTO = "https://www.oncor.com/content/oncorwww/us/en/home/faqs/faqs-details.html"
NEC_DG = "https://neccoopenergy.com/for-members/buyback/"
NEC_TERMS = {
    "NEC-RES": "https://neccoopenergy.com/wp-content/uploads/2024/08/NEC-Co-op-Energy-Residential-IOU-Variable-Product-TOS-ENG-rev-4-18-24-added-Lubbock74.pdf",
    "NEC-SMALL": "https://neccoopenergy.com/wp-content/uploads/2024/08/NEC-Co-op-Energy-COM-IOU-Variable-Product-TOS-ENG-SPN-rev-4-18-24-added-Lubbock.pdf",
}
EXCLUSIONS = ("State and local sales taxes, municipal gross-receipts reimbursement and separately billed Texas PUC assessment",)
FIRST, LAST = date(2025, 1, 1), date(2026, 10, 31)
FLAGS = {
    "eligibility_confirmed": "Confirmed REP product/version and Oncor assigned delivery class on a standard single-phase meter",
    "ordinary_service_confirmed": "Established single point of delivery, standard Oncor meter, ordinary charges. No special addendum, contract rate amendment, opt-out, underground, resale, special facilities, industrial exemption, member credits, discount or one-time fees",
    "full_monthly_charges_confirmed": "Full calendar read with one monthly charge. The Oncor delivery invoice was rendered on the last service day. Supply uses the separately entered REP bill date",
}


def _plan(plan):
    if not isinstance(plan, str):
        raise ValueError("Choose a named Oncor retail contract.")
    if plan in VARIABLE:
        return NEC, NEC_TERMS[plan]
    if plan in FIXED:
        offer = FIXED[plan]
        return offer["supplier"], offer["terms"]
    raise ValueError("Choose a verified Oncor residential or small-commercial REP contract.")


def _date(value, label):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Supply a documented ISO date for {label}.") from exc


def _schedule(plan):
    if plan in COMMERCIAL_OFFERS:
        return COMMERCIAL_OFFERS[plan]["schedule"]
    return "secondary_le_10_kw" if plan == "NEC-SMALL" else "residential"


def _terms_end(start, offer):
    return (pd.Timestamp(start) + pd.DateOffset(months=offer["term_months"])).date() - timedelta(days=1)


def _assessment(plan):
    if plan in FIXED:
        return FIXED[plan]["puca_treatment"]
    return "included_in_price"


def _rates(plan, first, last, bill):
    if not FIRST <= first <= last <= LAST or not last <= bill <= min(date(2026, 11, 19), last + timedelta(days=31)):
        raise ValueError("Oncor requires completed 2025–October 2026 cycles and a documented REP bill date within 31 days of the read.")
    schedule = _schedule(plan)
    delivery = (secondary_rates(first, last, bill_date=last) if schedule == DEMAND
                else delivery_rates(schedule, first, last, bill_date=last))
    if plan in VARIABLE:
        for key, row in VARIABLE[plan].items():
            if key <= bill.isoformat() <= row["bill_end"]:
                return row, delivery
        raise ValueError("No reconciled NEC Electricity Facts Label for this plan and REP bill date.")
    offer = FIXED[plan]
    issued = _date(offer["label_date"], "offer")
    if first < issued:
        raise ValueError("Service predates the selected fixed-price EFL.")
    return offer, delivery


@lru_cache(maxsize=None)
def _months(plan):
    _plan(plan)
    months = []
    month = FIRST
    while month <= LAST:
        end = month.replace(day=monthrange(month.year, month.month)[1])
        if plan in FIXED and end > _terms_end(_date(FIXED[plan]["label_date"], "offer"), FIXED[plan]):
            break  # Catalog example assumes service starts on issue. Actual service uses signed term dates.
        try:
            _rates(plan, month, end, end)
        except ValueError:
            pass
        else:
            months.append((month, end))
        month = end + timedelta(days=1)
    return tuple(months)


def _coverage(months):
    windows = []
    for start, end in months:
        if windows and date.fromisoformat(windows[-1]["end"]) + timedelta(days=1) == start:
            windows[-1]["end"] = end.isoformat()
        else:
            windows.append(dict(start=start.isoformat(), end=end.isoformat()))
    return windows


def account_fields(plan):
    fields = [dict(name=k, label=v, type="boolean") for k, v in FLAGS.items()]
    fields.extend([
        dict(name="account_source", label="Oncor class and enrolled REP contract, label, bill timing and ordinary-charge evidence"),
        dict(name="tax_treatment", choices=(["pretax_subtotal"] if _assessment(plan) == "unverified" else
                                           ["pretax_subtotal", "unincorporated_state_only"]),
             label="Billing scope: recurring subtotal or confirmed unincorporated meter outside all local taxing districts"),
        dict(name="tax_source", label="For a complete bill, document meter tax boundaries, use, itemized nuclear fee and REP reimbursement treatment"),
        dict(name="tax_status_confirmed", label="Tax scope documented: no local sales tax or municipal gross-receipts charge, ordinary fully taxable business or solely domestic residential use, separately disclosed nuclear fee"),
        dict(name="puca_treatment", choices=["unverified", "included_in_price", "separately_reimbursed"],
             label="REP treatment of the Texas PUC assessment shown on the bill"),
    ])
    if plan == "NEC-RES":
        fields.append(dict(name="non_demand_meter_confirmed", label="REP confirms residential non-demand metering under this NEC EFL"))
    if _schedule(plan) == "secondary_le_10_kw":
        fields.append(dict(name="prior_max_kw", label="Highest documented demand in the preceding 12 months in kW (independent of study imports)"))
    if plan in COMMERCIAL_OFFERS:
        fields.append(dict(name="small_business_contract_confirmed",
                           label="Signed Ambit small-commercial contract for one non-aggregated premises with prior 12-month demand below 50 kW, ordinary unaveraged billing and the selected Oncor meter class"))
    if _schedule(plan) == DEMAND:
        fields.extend([
            dict(name="prior_ncp_kw", type="number_array", label="Previous 11 monthly 15-minute peak demands in kW, oldest first"),
            dict(name="history_through_month", label="First day of the last documented month before the study (YYYY-MM-01)"),
            dict(name="demand_scope_confirmed", label="Oncor-assigned standard 15-minute NCP billing. No 4CP billing or past peak of 700 kW or more, power-factor adjustment, seasonal agriculture, or special demand treatment"),
        ])
    if plan in FIXED:
        fields.extend([dict(name="contract_start", label="Documented effective service start for this signed fixed-price contract"),
                       dict(name="contract_end", label="Last service day under this signed fixed-price contract")])
        if confirmation := FIXED[plan].get("enrollment_confirmation"):
            fields.append(dict(name="retail_enrollment_confirmed", label=confirmation))
    else:
        fields.extend([dict(name="der_ordinary_service_confirmed", label="Oncor permission to operate and NEC confirmation of ordinary imports for this exact non-export installation"),
                       dict(name="der_eligibility_source", label="TDU and supplier references covering selected equipment and zero-export operation"),
                       dict(name="der_activation_date", label="Effective permission-to-operate date")])
    return fields


def catalog():
    result = []
    for plan in (*VARIABLE, *FIXED):
        supplier, terms = _plan(plan)
        schedule = _schedule(plan)
        commercial = schedule != "residential"
        fixed = plan in FIXED
        if fixed:
            offer = FIXED[plan]
            label = f"{offer['product']} · {offer['label_date']}"
            if commercial:
                label += " · secondary >10 kW (through 20 kW)" if schedule == DEMAND else " · secondary ≤10 kW"
        else:
            label = f"NEC Co-op Energy · {'small commercial' if commercial else 'residential'} variable"
        months = _months(plan)
        sources = [TARIFF, terms, TAX]
        if fixed:
            sources.append(offer["source"])
        else:
            sources.extend(row["source"] for row in VARIABLE[plan].values())
        result.append(dict(id=plan, label=label, retail_supplier=supplier,
            customer_class="commercial" if commercial else "residential",
            status="supported" if months else "unsupported", billing_supported=bool(months),
            dispatch_supported=bool(months), coverage=_coverage(months), account_fields=account_fields(plan),
            interval_minutes=[15], voltage="secondary", representative_peak_kw=15 if schedule == DEMAND else 5 if commercial else 3,
            equipment_modes=(["grid_only"] if fixed else ["grid_only", "pv_only", "pv_battery"]) if months else [],
            solar_modes=["non_export"] if not fixed else [], supply_arrangements=[supplier], sources=sources,
            eligibility=("Established single-phase Oncor demand meter, documented 11-month NCP history with maximum above 10 and at most 20 kW, and current peak at most 20 kW."
                         if schedule == DEMAND else "Established single-phase small secondary Oncor assignment and documented non-demand retail enrollment."
                         if commercial else "Individually metered permanent dwelling on ordinary Oncor residential service."),
            limitations=["Coverage shown uses a final-day REP bill. NEC prices follow the actual bill date. Fixed ranges illustrate activation on the EFL issue date. Actual eligibility follows the signed contract and first TDU meter read.",
                         ("This contract supports the recurring subtotal only. Retail assessment treatment is unverified."
                          if _assessment(plan) == "unverified" else "Complete bills require documented unincorporated tax treatment. Other locations can calculate a verified recurring subtotal."),
                         "Export settlement is unavailable. Fixed offers are grid-only."]))
    return result


def defaults(plan_id="NEC-RES"):
    supplier, _ = _plan(plan_id)
    months = _months(plan_id)
    if not months:
        raise ValueError("No verified complete calendar cycles for this Oncor plan.")
    first, last = next((p for p in months if p[0] == date(2025, 9, 1)), months[0])
    a = dict(tariff=plan_id, supply=supplier, export_mode="none", rate_evidence_mode="verified",
             voltage="secondary", phase="single", voltage_v=240, meter_count=1,
             opening_credit_usd=0, opening_credit_kwh=0, cycle_kind="regular", account_source="", cycle_source="",
             billing_month=first.isoformat(), bill_date=last.isoformat(), tax_treatment="pretax_subtotal",
             tax_status_confirmed=False, tax_source="", puca_treatment="unverified", **dict.fromkeys(FLAGS, False))
    if plan_id in FIXED:
        a.update(contract_start="", contract_end="")
        if FIXED[plan_id].get("enrollment_confirmation"):
            a["retail_enrollment_confirmed"] = False
    else:
        a.update(der_ordinary_service_confirmed=False, der_activation_date="", der_eligibility_source="")
    if plan_id == "NEC-RES":
        a["non_demand_meter_confirmed"] = False
    if _schedule(plan_id) == "secondary_le_10_kw":
        a["prior_max_kw"] = None
    if _schedule(plan_id) == DEMAND:
        a.update(prior_ncp_kw=[], history_through_month="", demand_scope_confirmed=False)
    if plan_id in COMMERCIAL_OFFERS:
        a["small_business_contract_confirmed"] = False
    return a


def hypothetical_defaults(plan_id="NEC-RES", *, day=None):
    a = defaults(plan_id)
    first = _date(day or a["billing_month"], "service month")
    last = first.replace(day=monthrange(first.year, first.month)[1])
    a.update(dict.fromkeys(FLAGS, True))
    a.update(hypothetical_account=True, billing_month=first.isoformat(), bill_date=last.isoformat(),
             account_source="Illustrative established single-meter Oncor account enrolled in exactly the selected REP label, no special charges or credits.",
             cycle_source="Hypothetical calendar meter cycle and final-day Oncor and retail bills.",
             tax_treatment="unincorporated_state_only", tax_status_confirmed=True,
             tax_source="Hypothetical separately evidenced unincorporated meter outside every taxing district, ordinary use and separately disclosed nuclear fee.",
             puca_treatment=_assessment(plan_id))
    if _assessment(plan_id) == "unverified":
        a.update(tax_treatment="pretax_subtotal", tax_status_confirmed=False, tax_source="")
    if plan_id in FIXED:
        offer = FIXED[plan_id]
        issued = _date(offer["label_date"], "offer")
        a.update(contract_start=issued.isoformat(), contract_end=_terms_end(issued, offer).isoformat())
        if offer.get("enrollment_confirmation"):
            a["retail_enrollment_confirmed"] = True
    else:
        a.update(der_ordinary_service_confirmed=True, der_activation_date=first.isoformat(),
                 der_eligibility_source="Hypothetical signed Oncor and NEC approval for ordinary import service with the exact zero-export PV and PV-charged storage equipment.")
    if plan_id == "NEC-RES":
        a["non_demand_meter_confirmed"] = True
    if _schedule(plan_id) == "secondary_le_10_kw":
        a["prior_max_kw"] = 7.0
    if _schedule(plan_id) == DEMAND:
        a.update(prior_ncp_kw=[18.] * 11, history_through_month=_previous_month(first), demand_scope_confirmed=True)
    if plan_id in COMMERCIAL_OFFERS:
        a["small_business_contract_confirmed"] = True
    return a


def _previous_month(first):
    return (first - timedelta(days=1)).replace(day=1).isoformat()


def _reference(a, field):
    v = a.get(field)
    return isinstance(v, str) and 0 < len(v.strip()) <= 500


def _cycle(a, index):
    idx = pd.DatetimeIndex(index)
    step = pd.Timedelta(minutes=15)
    if (len(idx) < 2 or str(idx.tz) != TIMEZONE or idx.hasnans
            or not np.all(idx[1:] - idx[:-1] == step) or idx[0] != idx[0].normalize()
            or idx[0].day != 1 or idx[-1] + step != idx[0] + pd.offsets.MonthBegin()):
        raise ValueError("Oncor requires one complete calendar month of consecutive America/Chicago 15-minute intervals.")
    first, last = idx[0].date(), idx[-1].date()
    if a.get("billing_month") != first.isoformat() or a.get("cycle_kind") != "regular":
        raise ValueError("Oncor requires an ordinary full monthly meter cycle.")
    bill = _date(a.get("bill_date"), "REP bill")
    offer, delivery = _rates(a["tariff"], first, last, bill)
    return first, last, offer, delivery


def validate_account(a, index, equipment=None):
    if not isinstance(a, dict):
        raise ValueError("Supply the Oncor account and signed retail plan.")
    plan = a.get("tariff")
    supplier, _ = _plan(plan)
    scope = dict(supply=supplier, export_mode="none", rate_evidence_mode="verified", meter_count=1,
                 voltage="secondary", phase="single", voltage_v=240, opening_credit_usd=0, opening_credit_kwh=0)
    if (any(a.get(k) != v or isinstance(a.get(k), bool) for k, v in scope.items())
            or any(a.get(k) is not True for k in FLAGS) or not _reference(a, "account_source")
            or not _reference(a, "cycle_source") or a.get("provisional_assumptions_accepted", False) is not False):
        raise ValueError("Confirm Oncor classification, metering, full monthly delivery charges, ordinary retail enrollment and zero export.")
    first, last, offer, _ = _cycle(a, index)
    if plan == "NEC-RES" and a.get("non_demand_meter_confirmed") is not True:
        raise ValueError("Confirm that NEC residential service uses a non-demand meter.")
    if plan in COMMERCIAL_OFFERS and a.get("small_business_contract_confirmed") is not True:
        raise ValueError("Document the small-commercial signed contract, demand qualification, meter class and ordinary unaggregated enrollment.")
    if _schedule(plan) == "secondary_le_10_kw":
        peak = a.get("prior_max_kw")
        if type(peak) not in (int, float) or not 0 <= peak <= 10 or (plan == "NEC-SMALL" and peak == 10):
            raise ValueError("Document prior maximum demand within this small-secondary contract's verified range.")
    if _schedule(plan) == DEMAND and a.get("demand_scope_confirmed") is not True:
        raise ValueError("Confirm ordinary Oncor NCP demand billing and the absence of special demand adjustments.")
    if plan in FIXED:
        if offer.get("enrollment_confirmation") and a.get("retail_enrollment_confirmed") is not True:
            raise ValueError("Document the enrollment conditions for this specific retail offer.")
        start, end = _date(a.get("contract_start"), "first meter read"), _date(a.get("contract_end"), "term end")
        if not _date(offer["label_date"], "label") <= start <= first <= last <= end <= _terms_end(start, offer):
            raise ValueError("The whole cycle must fall within the documented, unexpired fixed-price contract.")
    profile = a.get("tax_treatment")
    if profile == "unincorporated_state_only":
        treatment = _assessment(plan)
        if treatment == "unverified" or a.get("tax_status_confirmed") is not True or not _reference(a, "tax_source") or a.get("puca_treatment") != treatment:
            raise ValueError("Document meter jurisdiction, tax base and the matching REP assessment treatment for a complete bill.")
    elif profile != "pretax_subtotal":
        raise ValueError("Choose the verified recurring subtotal or documented unincorporated tax treatment.")
    eq = equipment or {}
    if eq.get("pv") or eq.get("battery"):
        if (plan in FIXED or not eq.get("pv") or a.get("der_ordinary_service_confirmed") is not True
                or not _reference(a, "der_eligibility_source") or _date(a.get("der_activation_date"), "PTO") > first
                or (eq.get("battery") and (eq.get("renewable_only_charging") is not True or eq.get("no_battery_export") is not True))):
            raise ValueError("DER requires NEC ordinary import billing, active Oncor approval and non-export PV with optional PV-only battery charging.")


def validate_native_load(a, load):
    v = np.asarray(load, dtype=float)
    if not v.size or not np.isfinite(v).all() or v.min() < 0:
        raise ValueError("Oncor requires complete and finite nonnegative meter intervals.")
    if FIXED.get(a["tariff"], {}).get("positive_usage_required") and not v.any():
        raise ValueError("This retail subtotal requires positive monthly imports. Inactivity fees are outside the supported scope.")
    if a["tariff"] == "NEC-SMALL" and v.max() >= 10:
        raise ValueError("The native small-commercial study peak must stay below 10 kW.")
    if _schedule(a["tariff"]) == "secondary_le_10_kw" and v.max() > 10:
        raise ValueError("The small-secondary study peak must stay at or below 10 kW.")
    if _schedule(a["tariff"]) == DEMAND and v.max() > 20:
        raise ValueError("This secondary demand study supports peaks through 20 kW.")


def _demand_history(account, index, state):
    evidence = account if state is None else state
    if state is not None and (not isinstance(state, dict) or
                              set(state) != {"prior_ncp_kw", "history_through_month", "tariff"} or
                              state["tariff"] != account["tariff"]):
        raise ValueError("Oncor continuation requires the same contract and its rolled demand history.")
    if evidence.get("history_through_month") != _previous_month(index[0].date()):
        raise ValueError("Oncor demand history must end in the month immediately before this cycle.")
    values = evidence.get("prior_ncp_kw")
    if (not isinstance(values, list) or len(values) != 11 or
            any(type(x) not in (int, float) or not 0 <= x <= 20 for x in values) or max(values) <= 10):
        raise ValueError("Enter 11 monthly NCPs in order with a maximum greater than 10 kW and at most 20 kW.")
    return values


def validate_state(account, index, state=None, equipment=None):
    if _schedule(account["tariff"]) == DEMAND:
        _demand_history(account, index, state)
        return
    if state not in (None, {}):
        raise ValueError("Oncor non-export contracts cannot carry credits or other billing state.")


def charge_lines(index, imports, exports, account, *, math, state=None):
    validate_state(account, index, state)
    first, last, offer, delivery = _cycle(account, index)
    schedule = _schedule(account["tariff"])
    if math.convex:
        math.constraints.extend([imports >= 0, exports == 0])
        if schedule != "residential":
            math.constraints.append(imports <= (20 if schedule == DEMAND else 10))
    elif np.max(np.abs(exports)) > 1e-5:
        raise ValueError("Oncor retail plans require zero export.")
    if not math.convex:
        validate_native_load(account, imports)
    kwh = math.sum(imports) * math.hours
    # Preserve exact tariff half-cents for the numerical bill. CVXPY needs real coefficients.
    coefficient = float if math.convex else Decimal
    if not math.convex:
        kwh = Decimal(str(kwh))
    lines = {"rep_base_charge": coefficient(offer["monthly"]), "rep_energy": kwh * coefficient(offer["per_kwh"])}
    if "usage_fee_below_kwh" in offer:
        # These fixed contracts support grid-only service, so usage is known.
        if math.convex and not imports.is_constant():
            raise ValueError("This fixed contract requires known grid-only imports for its usage fee.")
        readings = imports.value if math.convex else imports
        volume = sum(Decimal(str(v)) for v in readings) * Decimal(".25")
        lines["rep_low_usage_fee"] = coefficient(offer["usage_fee_usd"]) if volume < offer["usage_fee_below_kwh"] else coefficient("0")
    lines.update({"oncor_" + k: coefficient(v) for k, v in delivery.monthly.items()})
    lines.update({"oncor_" + k: kwh * coefficient(v) for k, v in delivery.per_kwh.items()})
    next_state, demand_metrics = {}, {}
    if schedule == DEMAND:
        history = _demand_history(account, index, state)
        peak = math.maximum(imports)
        ratchet = math.maximum(peak, 0.8 * max(history))
        if not math.convex:
            peak = Decimal(str(peak))
            ratchet = max(peak, Decimal(".8") * Decimal(str(max(history))))
            next_state = dict(prior_ncp_kw=history[1:] + [float(peak)], history_through_month=first.isoformat(), tariff=account["tariff"])
            demand_metrics = dict(prior_11_month_ncp_max_kw=max(history), measured_ncp_kw=float(peak), rider_billing_kw=float(ratchet),
                                  oncor_usd_per_ncp_kw=float(sum(delivery.per_ncp_kw.values())),
                                  oncor_usd_per_ratchet_kw=float(sum(delivery.per_ratchet_kw.values())))
        for quantity, factors in ((peak, delivery.per_ncp_kw), (ratchet, delivery.per_ratchet_kw)):
            lines.update({"oncor_" + k: quantity * coefficient(v) for k, v in factors.items()})
    complete = account["tax_treatment"] == "unincorporated_state_only"
    if complete:
        # Comptroller 96-1309 excludes separately listed NDC. TC and SBF do not apply.
        taxable = sum(lines.values()) - lines["oncor_nuclear_decommissioning"]
        if account["puca_treatment"] == "separately_reimbursed":
            lines["puc_assessment_reimbursement"] = taxable * coefficient(".001667")
            taxable += lines["puc_assessment_reimbursement"]
        lines["texas_state_sales_tax"] = taxable * (coefficient(".0625") if schedule != "residential" else 0)
    return dict(lines=lines, next_state=next_state, is_complete_bill=complete,
                excluded_components=[] if complete else list(EXCLUSIONS), rate_evidence_status="verified",
                assumption_model=None, rate_assumptions=[],
                rate_sources=[offer["source"], _plan(account["tariff"])[1], *delivery.sources, TAX]
                             + ([PTO, NEC_DG] if account.get("der_ordinary_service_confirmed") else []),
                metrics=dict(service_start=first.isoformat(), service_end=last.isoformat(), oncor_bill_date=last.isoformat(),
                             bill_date=account["bill_date"], retail_supplier=offer["supplier"], efl_date=offer["label_date"],
                             efl_sha256=offer.get("sha256"),
                             rep_monthly_usd=float(offer["monthly"]), rep_usd_per_kwh=float(offer["per_kwh"]),
                             oncor_monthly_usd=float(sum(delivery.monthly.values())),
                             oncor_usd_per_kwh=float(sum(delivery.per_kwh.values())),
                             tax_treatment=account["tax_treatment"], oncor_schedule=schedule, **demand_metrics),
                warnings=["Supply follows the selected retailer's contract. Oncor delivery is charged once at filed rates. "
                          "The published EFL average includes delivery and is a comparison at a specified usage level."])
