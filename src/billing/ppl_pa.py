"""PPL Pennsylvania RS / ordinary single-phase GS-1 default-supply bills.

Complete hypothetical calendar cycles only. Export compensation, alternate
suppliers, TOU enrollment, standby service and partial-cycle proration are not
inferred. The same charge expressions drive dispatch and numerical rebilling.
"""
import numpy as np
import pandas as pd

from .ppl_pa_rates import COVERAGE, PLANS, SOURCES, iso_day, rates_on

UTILITY = "ppl_electric_pennsylvania"
TIMEZONE = "America/New_York"


def account_fields(plan="RS"):
    return [dict(name=k, type="boolean", default=False, required=True, label=v)
        for k, v in (
            ("eligibility_confirmed", "PPL Pennsylvania delivery territory, selected schedule and fixed GSC-1 default supply independently confirmed"),
            ("ordinary_service_confirmed", "Ordinary one-meter single-phase account; no nonprofit, discontinued FC, assistance, special facilities, standby or discretionary adjustments"),
            ("full_monthly_charges_confirmed", "Complete hypothetical calendar meter cycle and explicit bill-rendered date; no partial/shifted-cycle approximation"),
            ("local_charges_confirmed", "Pennsylvania state-only tax jurisdiction and ordinary residential/business tax status independently confirmed"))] + [
        dict(name="cycle_source", type="text", required=True, label="Meter-cycle evidence or explicit hypothetical calendar-cycle assumption; omit personal information"),
        dict(name="tax_source", type="text", required=True, label="State-only tax status/jurisdiction evidence or explicit hypothetical assumption"),
        dict(name="bill_date", type="date", required=True, label="Bill-rendered date: selects DSIC and TCJA for the whole bill"),
        dict(name="der_ordinary_service_confirmed", type="boolean", default=False,
             label="PV/storage: utility-approved ordinary renewable customer-generator service; no standby/special charges; non-export study"),
        dict(name="der_eligibility_source", type="text", label="Approved ordinary-service/interconnection evidence or explicit hypothetical agreement"),
        dict(name="rate_evidence_mode", type="choice", choices=["verified"], default="verified", label="Verified PPL components only; no provisional fallback"),
    ]


def defaults(plan="RS"):
    if plan not in PLANS:
        raise ValueError("Select PPL RS or ordinary GS-1.")
    return dict(tariff=plan, supply="default_ptc", export_mode="none",
        eligibility_confirmed=False, ordinary_service_confirmed=False,
        full_monthly_charges_confirmed=False, local_charges_confirmed=False,
        tax_jurisdiction="pa_state_only", tax_exempt=False, tax_source="",
        cycle_source="", cycle_kind="regular", billing_month="2026-09-01", bill_date="2026-09-30",
        rate_evidence_mode="verified", provisional_assumptions_accepted=False,
        der_ordinary_service_confirmed=False, der_eligibility_source="",
        voltage="secondary", phase="single", voltage_v=240., power_factor=1.,
        meter_count=1, service_line_count=1, opening_credit_usd=0., demand_interval_minutes=15)


def hypothetical_defaults(plan="RS", year=2025):
    a = defaults(plan)
    a.update(eligibility_confirmed=True, ordinary_service_confirmed=True,
        full_monthly_charges_confirmed=True, local_charges_confirmed=True,
        tax_source="Explicit hypothetical ordinary Pennsylvania state-only account outside Philadelphia/Allegheny; residential exemption or ordinary commercial6%sales tax, no special exemption",
        cycle_source="Explicit hypothetical complete calendar meter cycle and bill issued on final service date; not an actual customer statement",
        der_ordinary_service_confirmed=True,
        der_eligibility_source="Explicit hypothetical utility-approved ordinary renewable PV/storage customer-generator; no standby/additional charges; zero-export dispatch",
        hypothetical_account=True)
    return a


def catalog():
    return [dict(id=p, label="PPL "+("Residential RS fixed default supply" if p == "RS" else "Single-phase General Service GS-1 fixed default supply"),
        status="supported", customer_class="residential" if p == "RS" else "commercial",
        coverage=[dict(start=s, end=e) for s, e in COVERAGE], voltage="secondary",
        interval_minutes=[15], solar_modes=["non_export"], supply_arrangements=["default_ptc"],
        equipment_modes=["grid_only", "pv_only", "pv_battery"],
        representative_peak_kw=3. if p == "RS" else 20.,
        account_fields=account_fields(p), sources=SOURCES,
        eligibility="Confirmed ordinary single-phase secondary PPL Pennsylvania RS or GS-1, one meter, fixed GSC-1 default supply, full calendar cycles and state-only taxes. Location/zone does not establish retail eligibility.",
        limitations=[
            "Verified January2025–October2026; complete consecutive15-minute calendar cycles only. Partial/shifted bills, TOU, other suppliers and larger/three-phase plans remain unsupported.",
            "GS-1 bills one whole-cycle15-minute maximum, rounded to the nearest whole kW with half-up ties; no demand ratchet or invented coincident-peak tag. Bounded study peak stays below100kW.",
            "RS distribution composites include smart-meter/CER and efficiency/USR/storm riders. GS-1 ordinary riders are separate. GSC-1/TSC already include MFC and GRT; no extra wholesale LMP, capacity or transmission-tag charge.",
            "DSIC and TCJA are selected by the explicit bill-rendered date, not service-day allocation. TCJA excludes automatic rider revenue and STAS. July2026 base-rate reset and October2026 storm change are separate versions.",
            "PV/storage requires utility-confirmed ordinary renewable service; all exports are curtailed. No NEM bank, annual true-up, export credit, standalone-storage or standby agreement estimate.",
            "Ordinary state-only jurisdiction: residential electricity exempt from sales tax; ordinary business6%. Other localities, exemptions, budget plans, arrears, late charges and special adjustments are not modeled."])
        for p in PLANS]


def cycle_review(a, index):
    if a.get("rate_evidence_mode", "verified") != "verified" or a.get("provisional_assumptions_accepted", False) is not False:
        raise ValueError("PPL has no provisional-rate mode or price fallback.")
    idx = pd.DatetimeIndex(index)
    if len(idx) < 2 or str(idx.tz) != TIMEZONE:
        raise ValueError("PPL requires America/New_York timestamps with at least two intervals.")
    step = idx[1]-idx[0]
    if step != pd.Timedelta(minutes=15) or not np.all(idx[1:]-idx[:-1] == step):
        raise ValueError("PPL requires consecutive15-minute intervals; gaps, duplicates or hourly substitutes cannot establish a15-minute maximum.")
    stop = idx[-1]+step
    if (idx[0] != idx[0].normalize() or idx[0].day != 1 or stop != idx[0]+pd.offsets.MonthBegin()
            or a.get("cycle_kind") != "regular" or a.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("PPL first scope requires a complete calendar meter cycle; partial/shifted allocation is unverified.")
    if a.get("billing_month") != str(idx[0].date()):
        raise ValueError("PPL billing month must identify the complete calendar service cycle.")
    rendered = iso_day(a.get("bill_date"))
    if rendered < str(idx[-1].date()):
        raise ValueError("PPL bill-rendered date cannot precede service end.")
    first = rates_on(idx[0].date(), a["tariff"], bill_date=rendered)
    last = rates_on(idx[-1].date(), a["tariff"], bill_date=rendered)
    if first != last:
        raise ValueError("PPL service prices cross inside this cycle; no unverified allocation is applied.")
    return dict(service_start=str(idx[0].date()), service_end=str(idx[-1].date()),
        cycle_days=(stop.date()-idx[0].date()).days,
        elapsed_hours=float((stop-idx[0])/pd.Timedelta(hours=1)),
        billing_month=a["billing_month"], bill_date=rendered,
        monthly_charge_factor=1., partial_period_proration_applied=False)


def evidence(index, account):
    cycle_review(account, index)
    return dict(rate_evidence_status="verified", assumption_model=None,
        rate_assumptions=[], objective_scope="complete_utility_bill")


def validate_account(a, index, equipment=None):
    if (not isinstance(a, dict) or a.get("tariff") not in PLANS or a.get("supply") != "default_ptc"
            or a.get("export_mode") != "none"):
        raise ValueError("Select ordinary PPL RS/GS-1 fixed default supply and zero export.")
    if a.get("rate_evidence_mode", "verified") != "verified" or a.get("provisional_assumptions_accepted", False) is not False:
        raise ValueError("PPL has no provisional-rate mode or price fallback.")
    if any(a.get(k) is not True for k in ("eligibility_confirmed", "ordinary_service_confirmed", "local_charges_confirmed")):
        raise ValueError("Confirm PPL delivery/schedule eligibility, ordinary service and tax jurisdiction independently of location.")
    for key in ("cycle_source", "tax_source"):
        if not isinstance(a.get(key), str) or not 1 <= len(a[key].strip()) <= 500:
            raise ValueError("Document PPL complete-cycle and tax assumptions without personal identifiers.")
    if (a.get("tax_jurisdiction") != "pa_state_only" or a.get("tax_exempt") is not False
            or (a.get("voltage"), a.get("phase"), a.get("voltage_v"), a.get("power_factor")) != ("secondary", "single", 240., 1.)
            or a.get("meter_count") != 1 or a.get("service_line_count") != 1
            or a.get("opening_credit_usd") != 0. or a.get("demand_interval_minutes") != 15):
        raise ValueError("PPL first scope requires ordinary state-only taxes, one120/240V single-phase meter/service, unity PF,15-minute demand and no opening credits.")
    cycle_review(a, index)
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if (not equipment.get("pv") or a.get("der_ordinary_service_confirmed") is not True
                or not isinstance(a.get("der_eligibility_source"), str)
                or not 1 <= len(a["der_eligibility_source"].strip()) <= 500):
            raise ValueError("PPL PV/storage requires approved ordinary renewable service without standby or additional charges; standalone storage is outside this scope.")
        if max(equipment.get("pv_dc_kw", 0.), equipment.get("pv_ac_kw", 0.))+equipment.get("battery_kw", 0.) > 50.+1e-8:
            raise ValueError("PPL bounded renewable study limits combined PV/battery nameplate to50kW; this does not prove interconnection eligibility.")


def validate_state(a, index, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("PPL ordinary non-export billing has no modeled opening credit or demand-history state.")


def _billing_demand(math, imports, index):
    peak = math.demand(imports, index, minutes=15)
    if not math.convex:
        if peak >= 100.:
            raise ValueError("PPL bounded GS-1 study requires a measured peak below100kW; account classification remains separately confirmed.")
        below_tie = .5-(float(peak) % 1.)
        if 0. < below_tie < 1e-5-1e-9:
            raise ValueError("PPL demand is inside the0.00001-kW half-up solver guard band; provide billing-quality demand precision rather than claim exact parity at this numerical boundary.")
        return peak, float(np.floor(peak+.5))
    import cvxpy as cp
    whole_kw = cp.Variable(integer=True)
    # One integer; positive net demand cost selects the least filed billing
    # unit. 0.01-W headroom keeps solver feasibility tolerance off half-up ties.
    math.constraints.extend([whole_kw >= 0, whole_kw <= 100,
        peak <= 99.99999, peak <= whole_kw+.5-1e-5])
    return peak, math.register(whole_kw, 0., 100.)


def charge_lines(index, imports, exports, a, *, math, state=None):
    validate_state(a, index, state=state)
    idx = pd.DatetimeIndex(index)
    cycle = cycle_review(a, idx)
    if math.convex:
        math.constraints.append(exports == 0)
    elif np.max(exports) > 1e-5:
        raise ValueError("PPL export settlement is not implemented; exports must be zero.")
    r = rates_on(idx[0].date(), a["tariff"], bill_date=a["bill_date"])
    energy = math.hours*math.sum(imports)
    res = a["tariff"] == "RS"
    lines = dict(distribution_customer=r["customer"], distribution_energy=energy*r["distribution_energy"])
    metrics = {**cycle, "measured_demand_charge":not res, "intraday_time_of_use_pricing":False,
        "base_version":r["base_version"], "distribution_version":r["distribution_version"],
        "supply_version":r["supply_version"]}
    billed = 0.
    if not res:
        peak, billed = _billing_demand(math, imports, idx)
        lines["distribution_demand"] = billed*r["distribution_demand"]
        lines.update(smart_meter=r["smart_meter"], competitive_enhancement=r["competitive_enhancement"],
            energy_efficiency=energy*r["energy_efficiency"], storm_damage=energy*r["storm"])
        metrics.update(measured_demand_kw=peak, billing_demand_kw=billed,
            demand_basis="One full-cycle15-minute average maximum rounded to wholekW, half-up; no ratchet")
    base = r["tcja_base_customer"]+energy*r["tcja_base_energy"]+billed*r["tcja_base_demand"]
    lines["tcja_credit"] = base*r["tcja"]
    distribution = sum(lines.values())
    lines["distribution_dsic"] = distribution*r["dsic"]
    lines["distribution_state_tax_adjustment"] = (distribution+lines["distribution_dsic"])*r["stas_distribution"]
    lines["generation_supply"] = energy*r["generation"]
    lines["transmission_service"] = energy*r["transmission"]
    lines["supply_state_tax_adjustment"] = (lines["generation_supply"]+lines["transmission_service"])*r["stas_supply"]
    lines["sales_tax"] = 0. if res else sum(lines.values())*.06
    metrics.update(rates=r, tcja_base_distribution_usd=base,
        dsic_base_distribution_usd=distribution,
        rs_embedded_riders="RS customer includes SMR2/CER beforeJuly2026; energy includes ACR/USR/SDER; never charged twice" if res else None,
        capacity_transmission_treatment="Filed fixed GSC-1 includes capacity and MFC/GRT; TSC included once as retailper-kWh component. No additional PJM LMP/PLC/NSPL charge.",
        component_application_clocks={"service_prices":"One complete calendar-cycle service version",
            "dsic":"Explicit bill-rendered date selects entire bill factor",
            "tcja":"Explicit bill-rendered date; base distribution only, excluding STAS and automatic riders"},
        sales_tax_rate=0. if res else .06, tax_jurisdiction=a["tax_jurisdiction"],
        rate_effective_basis="Filed service-date component versions; bill-rendered DSIC/TCJA; complete calendar cycle only")
    return dict(lines=lines, metrics=metrics, next_state={}, is_complete_bill=True,
        rate_evidence_status="verified", assumption_model=None, rate_assumptions=[], rate_sources=SOURCES,
        warnings=["PPL ordinary hypothetical non-export account; tariff, supplier, tax and interconnection eligibility must be independently confirmed.",
            "Complete calendar-cycle study only; no unverified partial/shifted-cycle proration, TOU, alternative supplier, export credits or special standby settlement.",
            "Historical perfect foresight within each cycle; representative OpenDSS replay does not validate a surveyed customer installation."])
