"""PECO ordinary R and measured GS, standard/TOU default supply, 2025–2026.

Embedded distribution riders are decomposed before applying dated changes;
they are never added a second time to the printed all-in distribution price.
See docs/PECO.md and its source manifest for the deliberately bounded account.
"""
from copy import deepcopy
from datetime import date

import numpy as np
import pandas as pd

from .pjm_calendar import holiday_mask

UTILITY = "peco"
TIMEZONE = "America/New_York"
PLANS = ("R", "R-TOU", "GS", "GS-TOU")
VERIFIED_THROUGH = "2026-10-19"
ALLOCATION_MODEL = "peco_cycle_allocation_v1"
# URLs are part of the immutable Python engine, independent of editable docs.
SOURCES = ['https://www.peco.com/cdn/assets/v3/assets/blt1b5616c79bacadb4/blt9448ea371fcf175a/67784c8b1931fe6ea36c46e3/Current_Electric_Tariff_Eff_Jan_1_2025.pdf', 'https://www.peco.com/cdn/assets/v3/assets/blt1b5616c79bacadb4/blt9448ea371fcf175a/67e3ef1cac554b677e7fb714/Current_Electric_Tariff_Eff_April_1_2025.pdf?branch=prod_alias', 'https://www.peco.com/cdn/assets/v3/assets/blt1b5616c79bacadb4/blt9448ea371fcf175a/68b0cc75b3827834f7c7c272/Current_Electric_tariff_eff_Sept_1_2025.pdf', 'https://www.peco.com/cdn/assets/v3/assets/blt1b5616c79bacadb4/blt9448ea371fcf175a/695440103369913565ea1e0f/Current_Electric_Tariff_effective_January_1_2026.pdf?branch=prod_alias', 'https://www.pjm.com/-/media/DotCom/markets-ops/settlements/2025-business-calendar.pdf', 'https://www.pa.gov/agencies/revenue/resources/tax-types-and-information/sales-use-and-hotel-occupancy-tax']
SOURCES += [
    "https://www.peco.com/cdn/assets/v3/assets/blt1b5616c79bacadb4/blt9448ea371fcf175a/69cbdc20a21ea55b33ba7d35/Current_Electric_tariff_effective_April_1_2026.pdf",
    "https://www.peco.com/cdn/assets/v3/assets/blt1b5616c79bacadb4/bltf507baf8e5597bc1/6a8df16382f57bbb562dd5b2/Current_Electric_Tariff_Sept_1_2026_(003).pdf?branch=prod_alias",
    "https://www.peco.com/cdn/assets/v3/assets/blt1b5616c79bacadb4/bltc70b88d49d2a1491/6abbe397d463362a37c0f102/Current_Electric_tariff_eff_Oct_1_2026_(003).pdf?branch=prod_alias",
    "https://www.puc.pa.gov/pcdocs/1937866.pdf",
    "https://azure-na-assets.contentstack.com/v3/assets/blt1b5616c79bacadb4/bltf7c1eb06cdfe6ab9/6a0e7050df378b4731251e82/2026_RESIDENTIAL_Final_Electric_PTC_Effective_06-01-2026.pdf",
    "https://www.pjm.com/-/media/DotCom/markets-ops/settlements/2026-business-calendar.pdf",
]


def _dated(day, versions):
    return next(value for start, value in reversed(versions) if day >= start)


def rates_on(day):
    day = str(day)[:10]
    if not "2025-01-01" <= day <= VERIFIED_THROUGH:
        raise ValueError(f"PECO verified coverage is 2025-01-01 through {VERIFIED_THROUGH}; no extrapolation.")
    return dict(
        # Tuple order: residential, small commercial. TOU: peak, super-off, off.
        gsa=_dated(day, [("2025-01-01", (.08429, .08336)), ("2025-03-01", (.08381, .07170)),
                        ("2025-06-01", (.09508, .08651)), ("2025-12-01", (.10237, .09325)),
                        ("2026-06-01", (.10785, .10728))]),
        tou=_dated(day, [("2025-01-01", ((.28141, .04336, .06157), (.22515, .04406, .06521))),
                        ("2025-03-01", ((.27978, .04311, .06122), (.19367, .03790, .05609))),
                        ("2025-06-01", ((.29688, .04899, .07055), (.22645, .04669, .06863))),
                        ("2025-12-01", ((.31960, .05274, .07595), (.24405, .05032, .07397))),
                        ("2026-06-01", ((.31430, .05767, .08362), (.26264, .06010, .08835)))]),
        tsc=_dated(day, [("2025-01-01", (.00858, 2.13)), ("2025-06-01", (.00892, 2.05)), ("2025-12-01", (.00787, 1.57)), ("2026-06-01", (.00974, 2.20))]),
        nbt=_dated(day, [("2025-01-01", (.00364, .98)), ("2025-06-01", (.00414, .97)), ("2025-12-01", (.00408, .87)), ("2026-06-01", (.00322, .85))]),
        eepc=_dated(day, [("2025-01-01", (.00226, .00899)), ("2025-06-01", (.00176, .00392)), ("2026-06-01", (.00232, .00121))]),
        consumer_education=_dated(day, [("2025-01-01", .04), ("2025-04-01", .05), ("2026-04-01", .04)]),
        ndca=-.0006, usfc=.00045 if day < "2026-01-01" else .00287,
        icus=_dated(day, [("2025-01-01", (-.00313, -.13)), ("2026-01-01", (0., 0.)), ("2026-07-01", (-.00009, 0.))]),
        fars=_dated(day, [("2025-01-01", (-.00072, -.13)), ("2026-01-01", (0., 0.)), ("2026-07-01", (-.00001, 0.))]),
        stas=0. if day < "2026-01-01" else -.0004,
        dsic=_dated(day, [("2025-01-01", 0.), ("2026-04-01", .0011), ("2026-07-01", .0042), ("2026-10-01", .0105)]))


def periods(index):
    idx = pd.DatetimeIndex(index)
    holiday = holiday_mask(idx)
    peak = (idx.dayofweek < 5) & ~holiday & (idx.hour >= 14) & (idx.hour < 18)
    super_off = idx.hour < 6
    return {"peak": np.asarray(peak), "super_off_peak": np.asarray(super_off), "off_peak": np.asarray(~peak & ~super_off)}


def _applicable_rates(r, plan):
    """Ignore changes to a different class/option when bounding a meter cycle."""
    res = plan.startswith("R")
    cls = 0 if res else 1
    values = {"tou_generation" if plan.endswith("TOU") else "generation":
              r["tou"][cls] if plan.endswith("TOU") else r["gsa"][cls]}
    values.update({k: r[k][cls] for k in ("tsc", "nbt", "eepc", "icus", "fars")})
    values.update(ndca=r["ndca"], stas=r["stas"])
    if res:
        values.update(usfc=r["usfc"], consumer_education=r["consumer_education"])
    # DSIC explicitly uses bills rendered (sheet50), unlike the unresolved
    # allocation of the other components. It may change within this cycle.
    return values


def cycle_review(a, index):
    """Explain verified support or explicitly accepted provisional allocation.

    This is also used by billing and dispatch preflight. A missing allocation
    is rejected by default. Provisional policy is separate and opt-in only.
    Scan every local date through bill issuance: endpoint equality alone must
    not hide an intervening change followed by a return to the original rate.
    """
    idx = pd.DatetimeIndex(index)
    if len(idx) < 2 or str(idx.tz) != TIMEZONE or a.get("tariff") not in PLANS:
        raise ValueError("Supply a PECO tariff and at least two Eastern-time meter intervals.")
    step = idx[1]-idx[0]
    if step <= pd.Timedelta(0) or not np.all(idx[1:]-idx[:-1] == step):
        raise ValueError("PECO meter intervals must be consecutive and uniformly spaced in elapsed time.")
    stop = idx[-1]+step
    days = (stop.date()-idx[0].date()).days
    mode = a.get("rate_evidence_mode", "verified")
    if (mode not in ("verified", "provisional_cycles_v1")
            or type(a.get("provisional_assumptions_accepted", False)) is not bool
            or mode == "provisional_cycles_v1" and a.get("provisional_assumptions_accepted") is not True):
        raise ValueError("Provisional PECO allocation requires explicit mode selection and boolean acceptance of the documented assumptions.")
    if (idx[0] != idx[0].normalize() or stop != stop.normalize() or not 1 <= days <= 45
            or a.get("cycle_kind") not in ("regular", "initial", "final")):
        raise ValueError("PECO requires 1–45 whole local service days and a regular, initial or final cycle; partial clock days are unsupported.")
    try:
        bill_date = date.fromisoformat(a["bill_date"])
        if bill_date.isoformat() != a["bill_date"]:
            raise ValueError("Noncanonical bill date")
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Supply a PECO bill date as an ISO local date.") from exc
    if bill_date < idx[-1].date():
        raise ValueError("Bill date cannot precede service end.")
    first = rates_on(idx[0].date())
    rendered = rates_on(bill_date)
    issues = []
    if not 26 <= days <= 35:
        issues.append(dict(code="unverified_partial_allocation", message=(
            f"PECO requires a complete 26–35-day cycle; received {days} local days "
            f"({a.get('cycle_kind', 'unspecified')}). Rules 14.7/17.1 require adjustments for "
            "short/extended periods, but the fixed-charge factor and GS demand/minimum/1100-kWh "
            "threshold allocation are unverified. No 30-day denominator is assumed.")))
    previous = _applicable_rates(first, a["tariff"])
    changes = []
    for day in pd.date_range(idx[0].date(), bill_date, freq="D")[1:]:
        current = _applicable_rates(rates_on(day.date()), a["tariff"])
        changed = {k: dict(before=previous[k], after=current[k])
                   for k in previous if previous[k] != current[k]}
        if changed:
            changes.append(dict(date=str(day.date()),
                                phase="service" if day.date() <= idx[-1].date() else "bill_issuance_gap",
                                components=changed))
        previous = current
    if changes:
        detail = "; ".join(c["date"]+" "+", ".join(c["components"]) for c in changes)
        issues.append(dict(code="unverified_rate_change_allocation", message=(
            "PECO rate-change-crossing service/bill dates require verified allocation: "+detail+
            ". GSA says rates are not prorated but does not resolve the whole-cycle rate date here. "
            "Do not blend supply prices, split GS peaks or truncate an actual meter cycle.")))
    provisional = mode == "provisional_cycles_v1" and bool(issues)
    return dict(cycle_supported=not issues or provisional, cycle_days=days, cycle_kind=a.get("cycle_kind"),
                elapsed_hours=float((stop-idx[0])/pd.Timedelta(hours=1)),
                service_start=str(idx[0].date()), service_end=str(idx[-1].date()),
                bill_date=str(bill_date), rate_changes=changes, issues=[] if provisional else issues,
                allocation_requirements=issues, provisional_allocation_applied=provisional,
                monthly_charge_factor=days/30 if not 26 <= days <= 35 else 1.,
                dsic_fraction=rendered["dsic"], dsic_basis="bills_rendered",
                rules=dict(regular_cycle_days=[26, 35], gsa_prorated=False,
                           partial_period_formula_verified=False,
                           non_dsic_rate_change_allocation_verified=False))


def allocation_evidence(a, index):
    """Versioned study assumptions, separate from the verified price evidence.

    Sources explain the remaining policy uncertainty; they do not verify the
    assumed arithmetic. Include downstream adjustments in component labels.
    """
    review = cycle_review(a, index)
    used = []
    if review["provisional_allocation_applied"]:
        res = a["tariff"].startswith("R")
        downstream = ["state_tax_adjustment", "distribution_dsic"] + ([] if res else ["sales_tax"])
        delivery = (["distribution_customer", "distribution_energy"] if res else
                    ["distribution_customer", "distribution_demand", "distribution_ndca", "energy_efficiency"])
        common = dict(kind="billing_rule", start=review["service_start"], end=review["service_end"],
                      sources=SOURCES[:1], basis="provisional_cycle_allocation")
        if not 26 <= review["cycle_days"] <= 35:
            used.append(dict(**common, id="PECO-CYCLE-30", components=delivery[:1]+([] if res else ["distribution_demand", "transmission"])+downstream,
                assumed_values=dict(reference_days=30, local_service_days=review["cycle_days"], monthly_charge_factor=review["monthly_charge_factor"],
                    gs_low_usage_threshold_kwh=1100*review["monthly_charge_factor"],
                    gs_low_usage_denominator_hours=175*review["monthly_charge_factor"], minimum_demand_kw=1.2),
                explanation="Study assumption: outside 26–35 days use local days/30 for monthly fixed and demand prices. For GS scale the 1100-kWh threshold and 175-hour denominator by the same factor; retain the 1.2-kW floor and one rounded full-cycle demand. Do not scale measured energy or kW a second time. This is not a verified PECO partial-bill formula."))
        if review["rate_changes"]:
            used.append(dict(**common, id="PECO-SUPPLY-END", components=["generation", "transmission"]+([] if res else ["sales_tax"]),
                assumed_values=dict(rate_date=review["service_end"], date_proxy="final_inclusive_service_date", gsa_prorated=False, tsc_prorated=False),
                explanation="Study assumption: final inclusive service date proxies the scheduled-cycle date for whole-cycle GSA/TOU and TSC prices. Do not blend supply prices or use the issue date. Rule1.3's exact operational anchor is unverified; this proxy is not an interpretation confirmed by PECO."))
            used.append(dict(**common, id="PECO-DELIVERY-SEGMENTS", components=delivery+downstream,
                assumed_values=dict(energy_allocation="actual_interval_kwh_by_service_date", monthly_prices="local_calendar_day_weighted", demand="one_full_cycle_peak", stas="per_delivery_segment", dsic="bill_date_on_distribution_plus_stas"),
                explanation="Study assumption: delivery energy uses actual interval usage and dated components; monthly delivery fixed/demand prices use local-day shares and the cycle factor. Apply segment STAS before bill-date DSIC, then commercial sales tax. No separate segment demand peaks. Only DSIC's bills-rendered basis is verified."))
    return dict(rate_evidence_status="provisional" if used else "verified",
                price_evidence_status="verified", billing_allocation_status="provisional" if used else "verified",
                assumption_model=ALLOCATION_MODEL if used else None, rate_assumptions=used)


def _delivery_segments(a, index, review):
    """Few contiguous rate blocks, never one CVXPY expression per interval."""
    idx = pd.DatetimeIndex(index)
    if not review["provisional_allocation_applied"]:
        return [dict(start=0, stop=len(idx), rate_date=str(idx[0].date()), days=review["cycle_days"], monthly_share=1.)]
    days = pd.date_range(idx[0].date(), idx[-1].date(), freq="D")
    segments = []
    previous = None
    for day in days:
        current = _applicable_rates(rates_on(day.date()), a["tariff"])
        if current != previous:
            segments.append(dict(rate_date=str(day.date()), days=0))
        segments[-1]["days"] += 1
        previous = current
    for segment in segments:
        start = pd.Timestamp(segment["rate_date"]).tz_localize(TIMEZONE)
        stop = start + pd.DateOffset(days=segment["days"])
        segment.update(start=int(idx.searchsorted(start)), stop=int(idx.searchsorted(stop)),
                       monthly_share=segment["days"]/review["cycle_days"]*review["monthly_charge_factor"])
    return segments


def account_fields(plan_id="R"):
    fields = [
        dict(name="eligibility_confirmed", type="boolean", label="Confirmed PECO distribution territory and rate eligibility", default=False, required=True),
        dict(name="ordinary_service_confirmed", type="boolean", label="Ordinary single-meter default supply; no CAP, special riders or capacity reservation", default=False, required=True),
        dict(name="cycle_source", type="text", label="Complete meter-cycle evidence or explicit hypothetical assumption", required=True),
        dict(name="bill_date", type="date", label="Bill date", required=True),
        dict(name="cycle_kind", type="choice", choices=["regular", "initial", "final"], default="regular", label="Meter-cycle type", required=True),
        dict(name="rate_evidence_mode", type="choice", choices=["verified", "provisional_cycles_v1"], default="verified", label="Billing allocation: verified only or provisional cycle assumptions", required=True),
        dict(name="provisional_assumptions_accepted", type="boolean", default=False,
             label="I accept PECO provisional allocation: days/30 outside 26–35 days, dated delivery, end-of-service supply prices and one cycle demand; bills/savings are estimates"),
        dict(name="tax_jurisdiction", type="choice", choices=["pa_state_only", "philadelphia"], default="pa_state_only", label="Verified sales-tax jurisdiction", required=True),
        dict(name="der_ordinary_service_confirmed", type="boolean", label="Approved non-export interconnection, ordinary service and no capacity-reservation rider", default=False),
        dict(name="der_eligibility_source", type="text", label="Interconnection/ordinary-service evidence or explicit hypothetical assumption"),
    ]
    if plan_id.startswith("GS"):
        fields += [dict(name="procurement_class_confirmed", type="boolean", default=False, required=True,
                        label="Utility-confirmed procurement class 2 (prior June–May peak ≤100 kW, effective following June)")]
    if plan_id.endswith("TOU"):
        fields += [dict(name="tou_eligibility_confirmed", type="boolean", default=False, required=True,
                        label="Smart interval meter; valid email; no CAP/virtual net metering or 12-cycle re-enrollment lockout")]
    return fields


def defaults(plan_id="R"):
    if plan_id not in PLANS:
        raise ValueError("Select PECO R, R-TOU, measured GS or GS-TOU.")
    res = plan_id.startswith("R")
    return dict(tariff=plan_id, supply="default_service", export_mode="none", eligibility_confirmed=False,
                ordinary_service_confirmed=False, procurement_class_confirmed=False, tou_eligibility_confirmed=False,
                cycle_source="", cycle_kind="regular", bill_date="2026-09-30", billing_month="2026-09-01",
                rate_evidence_mode="verified", provisional_assumptions_accepted=False,
                voltage="secondary", phase="single" if res else "three", voltage_v=240. if res else 480., power_factor=1.,
                tax_jurisdiction="pa_state_only", tax_exempt=False,
                der_ordinary_service_confirmed=False, der_eligibility_source="")


def hypothetical_defaults(plan_id="R"):
    a = defaults(plan_id)
    a.update(eligibility_confirmed=True, ordinary_service_confirmed=True, procurement_class_confirmed=True,
             tou_eligibility_confirmed=True, hypothetical_account=True,
             cycle_source="Explicit hypothetical complete calendar meter cycle; not an actual statement",
             der_ordinary_service_confirmed=True,
             der_eligibility_source="Hypothetical approved <100-kW non-export renewable interconnection; no capacity reservation")
    return a


def catalog():
    return [dict(id=p, label="PECO " + ("Residential R" if p.startswith("R") else "Measured General Service GS ≤100 kW") +
                 (" · TOU generation" if p.endswith("TOU") else " · standard generation"), status="supported",
                 customer_class="residential" if p.startswith("R") else "commercial",
                 coverage=[dict(start="2025-01-01", end=VERIFIED_THROUGH)], voltage="secondary",
                 solar_modes=["non_export"], supply_arrangements=["default_service"],
                 equipment_modes=["grid_only", "pv_only", "pv_battery"], account_fields=account_fields(p), sources=SOURCES,
                 representative_peak_kw=2. if p.startswith("R") else 20.,
                 eligibility="Confirmed ordinary PECO R or measured GS, default supply; verified 26–35-day cycle or explicitly accepted provisional allocation for 1–45 whole local days/crossings. GS confirmed procurement class 2 ≤100 kW, unity billing PF. TOU requires eligible smart-meter enrollment.",
                 limitations=["Prices verified through October 19, 2026. DSIC uses bill date. Partial/extended and non-DSIC crossing calculations require provisional_cycles_v1 plus acceptance; these allocation assumptions are not verified PECO rules.",
                              "Non-export PV below 100 kW only; RS-2 net metering, CAP, RH heating, standby/capacity reservation, competitive supply and large procurement classes are unsupported.",
                              "Nonresidential low-usage and demand rounding follow the filed GS rule; a numerical tolerance band at 1100 kWh is rejected.",
                              "Ordinary PA/Philadelphia sales tax only; exemptions and mixed-use billing are unsupported."])
            for p in PLANS]


def validate_account(a, index, equipment=None):
    idx = pd.DatetimeIndex(index)
    if not isinstance(a, dict) or a.get("tariff") not in PLANS or a.get("supply") != "default_service" or a.get("export_mode") != "none":
        raise ValueError("Select PECO ordinary default supply and non-export operation; competitive/export plans are unsupported.")
    if a.get("eligibility_confirmed") is not True or a.get("ordinary_service_confirmed") is not True:
        raise ValueError("Confirm PECO territory, ordinary service and eligibility independently of location.")
    if not isinstance(a.get("cycle_source"), str) or not a["cycle_source"].strip():
        raise ValueError("Supply documented meter-cycle evidence; omit personal identifiers.")
    review = cycle_review(a, idx)
    if review["issues"]:
        raise ValueError(" ".join(issue["message"] for issue in review["issues"]))
    res = a["tariff"].startswith("R")
    if res and (a.get("voltage") != "secondary" or a.get("power_factor") != 1. or
                (a.get("phase"), a.get("voltage_v")) != ("single", 240.)):
        raise ValueError("Residential PECO scope requires 240-V single-phase secondary service and unity billing power factor.")
    if not res:
        if a.get("procurement_class_confirmed") is not True:
            raise ValueError("Confirm PECO procurement class 2 independently of this study's peak.")
        if a.get("voltage") != "secondary" or a.get("power_factor") != 1. or (a.get("phase"), a.get("voltage_v")) not in (("single", 240.), ("three", 480.)):
            raise ValueError("First measured GS case supports 240-V single or 480-V three-phase secondary unity-PF service.")
    if a["tariff"].endswith("TOU") and a.get("tou_eligibility_confirmed") is not True:
        raise ValueError("Confirm TOU smart-meter/email eligibility, CAP exclusion and re-enrollment rules.")
    if a.get("tax_jurisdiction") not in ("pa_state_only", "philadelphia") or a.get("tax_exempt"):
        raise ValueError("Select verified PA state-only/Philadelphia ordinary tax jurisdiction; exemptions need a separate model.")
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if a.get("der_ordinary_service_confirmed") is not True or not a.get("der_eligibility_source"):
            raise ValueError("Confirm approved non-export interconnection and ordinary service without a capacity-reservation rider.")
        if max(equipment.get("pv_ac_kw", 0), equipment.get("pv_dc_kw", 0)) >= 100:
            raise ValueError("PECO PV ≥100 kW requires separate capacity-reservation eligibility/rules.")


def _billing_demand(math, imports, idx, energy, monthly_factor=1.):
    threshold = 1100*monthly_factor
    hours_use = 175*monthly_factor
    peak = math.demand(imports, idx, minutes=30)
    if not math.convex:
        if peak > 100. + 1e-5:
            raise ValueError("PECO first GS scope requires measured peak ≤100 kW and confirmed procurement class 2.")
        if threshold-1e-5 < energy < threshold:
            raise ValueError("GS 1100-kWh discontinuity tolerance band; provide billing-quality energy precision.")
        measured = np.floor(peak*10+.5)/10
        demand = max(1.2, min(measured, energy/hours_use) if energy < threshold else measured)
        return peak, demand
    import cvxpy as cp
    # A single integer represents the filed nearest-0.1-kW measurement. The
    # strictly positive total demand price selects its smallest feasible value.
    # Conservative 0.00001-kW (0.01-W) headroom keeps feasibility noise off ties.
    tenth = cp.Variable(integer=True)
    math.constraints.extend([peak <= 100., tenth >= 0, tenth <= 1000,
                             peak <= tenth*.1+.05-1e-5])
    measured = math.register(tenth*.1, 0., 100.)
    normal = math.maximum(measured, 1.2, exact=True)
    lo, hi = math.bounds(energy)
    if lo >= threshold:
        return peak, normal
    low = math.maximum(math.minimum(measured, energy/hours_use), 1.2, exact=True)
    if hi < threshold-1e-5:
        return peak, low
    flag = cp.Variable(boolean=True)
    math.constraints.extend([energy <= (threshold-1e-5)*flag + hi*(1-flag),
                             energy >= lo*flag + threshold*(1-flag)])
    demand = cp.Variable()
    math.constraints.extend([demand >= 1.2, demand <= 100., demand >= low-100*(1-flag),
                             demand <= low+100*(1-flag), demand >= normal-100*flag, demand <= normal+100*flag])
    return peak, math.register(demand, 1.2, 100.)


def charge_lines(index, imports, exports, a, *, math, state=None):
    idx = pd.DatetimeIndex(index)
    if math.convex:
        math.constraints.append(exports == 0)
    elif np.max(exports) > 1e-5:
        raise ValueError("PECO solar export/RS-2 settlement is unsupported; require zero export.")
    review = cycle_review(a, idx)
    evidence = allocation_evidence(a, idx)
    provisional = review["provisional_allocation_applied"]
    factor = review["monthly_charge_factor"] if provisional else 1.
    supply_date = idx[-1].date() if provisional else idx[0].date()
    r = rates_on(supply_date)
    res = a["tariff"].startswith("R")
    cls = 0 if res else 1
    energy = math.hours * math.sum(imports)
    rendered = rates_on(a["bill_date"])
    metrics = {"rate_effective_basis": "Provisional cycle allocation; inspect assumption ledger" if provisional else "One applicable service/supply version; DSIC on bills-rendered date",
               "service_rate_date": str(idx[0].date()), "dsic_bill_date": a["bill_date"],
               "supply_rate_date": str(supply_date), "dsic_fraction": rendered["dsic"],
               "cycle_days": ((idx[-1]+(idx[1]-idx[0])).date()-idx[0].date()).days,
               "cycle_kind": a["cycle_kind"],
               "monthly_charge_factor": factor, "partial_period_proration_applied": factor != 1.,
               "provisional_allocation_applied": provisional}
    if a["tariff"].endswith("TOU"):
        masks = periods(idx)
        values = r["tou"][cls]
        supply = sum(math.hours*math.dot(imports, masks[p].astype(float))*v for p, v in zip(masks, values))
        for p, mask in masks.items():
            metrics[p+"_kwh"] = math.hours*math.dot(imports, mask.astype(float))
    else:
        supply = energy*r["gsa"][cls]
    lines = dict(generation=supply, transmission=energy*r["tsc"][0] if res else 0.)
    if not res:
        peak, demand = _billing_demand(math, imports, idx, energy, factor)
        lines["transmission"] = demand*r["tsc"][1]*factor
        metrics.update(measured_demand_kw=peak, billing_demand_kw=demand,
                       demand_interval_minutes=30, gs_low_usage_threshold_kwh=1100*factor,
                       gs_low_usage_denominator_hours=175*factor)
    segments = _delivery_segments(a, idx, review)
    stas = 0.
    dist_rates = []
    for segment in segments:
        d = rates_on(segment["rate_date"])
        share = segment["monthly_share"]
        # Masked dot retains the optimizer's bounded energy operations. Calendar
        # days weight monthly prices; physical interval hours integrate energy.
        mask = np.zeros(len(idx)); mask[segment["start"]:segment["stop"]] = 1.
        volume = energy if len(segments) == 1 else math.hours*math.dot(imports, mask)
        if res:
            dist_rate = .09465+d["ndca"]+d["usfc"]+d["icus"][0]+d["fars"][0]+d["nbt"][0]+d["eepc"][0]
            part = dict(distribution_customer=(11.25+d["consumer_education"])*share,
                        distribution_energy=volume*dist_rate)
        else:
            dist_rate = 10.63+d["nbt"][1]+d["icus"][1]+d["fars"][1]
            part = dict(distribution_customer=(31.20 if a["phase"] == "single" else 74.66)*share,
                        distribution_demand=demand*dist_rate*share, distribution_ndca=volume*d["ndca"],
                        energy_efficiency=volume*d["eepc"][1])
        dist_rates.append(dist_rate)
        segment.update(all_in_distribution_rate=dist_rate, stas_fraction=d["stas"])
        stas += sum(part.values())*d["stas"]
        for key, value in part.items():
            lines[key] = lines.get(key, 0.)+value
    metrics["all_in_distribution_usd_per_kwh" if res else "all_in_distribution_usd_per_kw"] = dist_rates[0] if len(set(dist_rates)) == 1 else None
    metrics["stas_fraction"] = segments[0]["stas_fraction"] if len({s["stas_fraction"] for s in segments}) == 1 else None
    metrics["delivery_rate_segments"] = segments
    distribution = sum(v for k,v in lines.items() if k not in ("generation", "transmission"))
    # STAS is a distribution-only credit; exclude default supply GSA/TSC.
    # DSIC sheet50 then applies to distribution AND STAS, by bill date.
    lines["state_tax_adjustment"] = stas
    lines["distribution_dsic"] = (distribution+lines["state_tax_adjustment"])*rendered["dsic"]
    lines["sales_tax"] = 0. if res else sum(lines.values())*(.08 if a["tax_jurisdiction"] == "philadelphia" else .06)
    return dict(lines=lines, metrics=metrics, next_state=deepcopy(state or {}), is_complete_bill=True,
                **evidence,
                warnings=[f"PECO price coverage through {VERIFIED_THROUGH}; ordinary non-export scope, embedded riders included once. Capacity is in GSA; transmission in TSC/NBT. No extra LMP, capacity PLC or network tag charge.",
                          "Historical perfect foresight within each cycle; no net-metering credits, CAP, competitive supplier or capacity-reservation settlement."] +
                         (["Provisional PECO billing estimate: verified prices with unverified allocation rules. Optimization and savings are conditional on "+ALLOCATION_MODEL+"; solver reconciliation does not validate PECO's billing policy."] +
                          [v["explanation"] for v in evidence["rate_assumptions"]] if provisional else []),
                rate_sources=SOURCES)
