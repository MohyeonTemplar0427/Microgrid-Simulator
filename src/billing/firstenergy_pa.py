"""West Penn RS / measured GS-Medium default service, verified calendar 2025.

Retail charges share their arithmetic with dispatch. PJM prices and network
losses never enter these rates. See docs/FirstEnergy.md for source/version scope.
"""
from copy import deepcopy
from datetime import date

import numpy as np
import pandas as pd

UTILITY = "firstenergy_pa_west_penn"
TIMEZONE = "America/New_York"
SOURCE = "https://www.puc.pa.gov/pcdocs/"
SOURCES = [SOURCE + str(n) + ".pdf" for n in (
    1858451, 1860899, 1858401, 1859431, 1860381, 1870842, 1879559,
    1877401, 1879719, 1883054, 1885199, 1895067, 1898804)]
SOURCES += ["https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/PA/tariffs/FE-PA-Supp-No-11-PTC-HPS-Rider-Changes-12-1-2024.pdf",
            "https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/PA/tariffs/FEPA-Supp-No-19-PTC-and-HPS-Rider.pdf"]


def _dated(day, versions):
    return next(value for start, value in reversed(versions) if day >= start)


def rates_on(day):
    day = str(day)[:10]
    if not "2025-01-01" <= day <= "2025-12-31":
        raise ValueError("West Penn verified coverage is calendar 2025; no historical/future extrapolation.")
    return dict(
        supply=_dated(day, [("2025-01-01", (.09481, .10013)),
                           ("2025-06-01", (.10317, .10536)), ("2025-12-01", (.10947, .10993))]),
        dss=_dated(day, [("2025-01-01", (.00539, .00288)), ("2025-06-01", (.00770, .00407))]),
        eec=_dated(day, [("2025-01-01", (.00161, .00330)), ("2025-06-01", (.00186, .00200))]),
        usc=_dated(day, [("2025-01-01", .00589), ("2025-08-01", .00920)]),
        dsic=_dated(day, [("2025-01-01", 0.), ("2025-04-01", .0002), ("2025-07-01", 0.)]))


def account_fields(plan_id="RS"):
    fields = [
        {"name": "eligibility_confirmed", "type": "boolean", "label": "Confirmed West Penn district and rate eligibility", "default": False, "required": True},
        {"name": "ordinary_service_confirmed", "type": "boolean", "label": "Ordinary single-meter account; no special riders, assistance or standby charges", "default": False, "required": True},
        {"name": "cycle_source", "type": "text", "label": "Meter-cycle evidence or explicit hypothetical assumption", "required": True},
        {"name": "bill_date", "type": "date", "label": "Bill date (TCJA and January refund)", "required": True},
        {"name": "cycle_kind", "type": "choice", "choices": ["regular"], "default": "regular", "label": "Complete regular meter cycle", "required": True},
        {"name": "der_ordinary_service_confirmed", "type": "boolean", "label": "Utility confirms renewable PV/storage remains ordinary service, without Partial Services Rider", "default": False, "required": False},
        {"name": "der_eligibility_source", "type": "text", "label": "Approved renewable interconnection / ordinary-service evidence (or hypothetical assumption)", "required": False},
    ]
    if plan_id == "GS-M":
        fields += [
            {"name": "contract_demand_kw", "type": "number", "label": "Filed account contract demand (kW)", "required": True},
            {"name": "history_billing_kw", "type": "number_array", "label": "Eleven preceding BILLING demands, oldest first", "required": True},
            {"name": "history_kwh", "type": "number_array", "label": "Eleven preceding delivered kWh, oldest first", "required": True},
            {"name": "demand_interval_minutes", "type": "number", "default": 15, "label": "Utility-confirmed demand averaging minutes (15/30/60)", "required": True},
            {"name": "ptc_review_confirmed", "type": "boolean", "label": "Utility annual review confirms <100 kW default-service class", "default": False, "required": True},
            {"name": "reactive_billing_kvar", "type": "number", "label": "Utility-assigned coincident reactive billing demand (kVAr)", "required": True},
        ]
    return fields


def defaults(plan_id="RS"):
    if plan_id not in ("RS", "GS-M"):
        raise ValueError("Select West Penn RS or measured GS-Medium default service.")
    return dict(tariff=plan_id, supply="default_ptc", eligibility_confirmed=False,
                ordinary_service_confirmed=False, billing_month="2025-07-01", bill_date="2025-07-31",
                cycle_kind="regular", cycle_source="", export_mode="none", voltage="secondary",
                phase="single", voltage_v=240., power_factor=1.,
                der_ordinary_service_confirmed=False, der_eligibility_source="",
                contract_demand_kw=0., history_billing_kw=[], history_kwh=[],
                demand_interval_minutes=15, ptc_review_confirmed=False, reactive_billing_kvar=0.,
                tax_jurisdiction="pa_state_only", tax_exempt=False)


def hypothetical_defaults(plan_id="RS", year=2025):
    a = defaults(plan_id)
    a.update(eligibility_confirmed=True, ordinary_service_confirmed=True,
             cycle_source="Hypothetical complete calendar cycle; not a measured bill",
             der_ordinary_service_confirmed=True,
             der_eligibility_source="Hypothetical utility-approved qualifying renewable PV/storage account exempt from Partial Services Rider; zero-export study constraint",
             ptc_review_confirmed=True, history_billing_kw=[20.] * 11,
             history_kwh=[6000.] * 11, hypothetical_account=True)
    return a


def catalog():
    return [dict(id=p, label=label, status="supported", customer_class=kind,
                 coverage=[dict(start="2025-01-01", end="2025-12-31")],
                 voltage="secondary", solar_modes=["non_export"],
                 supply_arrangements=["default_ptc"],
                 equipment_modes=["grid_only", "pv_only", "pv_battery"],
                 account_fields=account_fields(p), sources=SOURCES,
                 representative_peak_kw=3. if p == "RS" else 20.,
                 eligibility="Confirmed West Penn district, ordinary default supply, regular cycle. GS-M: measured demand, non-TOU demand meter, <100 kW utility-reviewed PTC class; excludes standby/special service.",
                 limitations=["Calendar 2025 only; other Pennsylvania districts are not covered.",
                              "PV/storage requires utility-confirmed ordinary renewable service and zero export; no export credits or standby estimate.",
                              "State-only sales tax jurisdiction; no Allegheny/Philadelphia or exempt/mixed-use business tax."])
            for p, label, kind in [("RS", "West Penn Residential RS", "residential"),
                                   ("GS-M", "West Penn GS-Medium (<100 kW default supply)", "commercial")]]


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) or value < 0:
        raise ValueError(name + " must be an explicit finite nonnegative number.")
    return float(value)


def validate_account(a, index, equipment=None):
    idx = pd.DatetimeIndex(index)
    if (not isinstance(a, dict) or a.get("tariff") not in ("RS", "GS-M")
            or a.get("supply") != "default_ptc" or a.get("export_mode") != "none"):
        raise ValueError("Select ordinary West Penn default supply; third-party and export settlement are not implemented.")
    if a.get("eligibility_confirmed") is not True or a.get("ordinary_service_confirmed") is not True:
        raise ValueError("Confirm West Penn district, ordinary service and account eligibility independently of location.")
    if str(idx.tz) != TIMEZONE or a.get("cycle_kind") != "regular" or not a.get("cycle_source"):
        raise ValueError("Supply a documented complete regular Eastern-time meter cycle.")
    stop = idx[-1] + (idx[1] - idx[0])
    days = (stop.date() - idx[0].date()).days
    if idx[0] != idx[0].normalize() or stop != stop.normalize() or not 25 <= days <= 35:
        raise ValueError("West Penn first scope requires a complete regular 25–35-day cycle; partial-cycle allocation is unverified.")
    for d in (idx[0].date(), idx[-1].date(), date.fromisoformat(a["bill_date"])):
        rates_on(d)
    if date.fromisoformat(a["bill_date"]) < idx[-1].date():
        raise ValueError("Bill date cannot precede service end.")
    if a.get("voltage") != "secondary" or a.get("phase") != "single" or a.get("voltage_v") != 240. or a.get("power_factor") != 1.:
        raise ValueError("First West Penn case uses confirmed 240 V single-phase unity-PF service; three-phase reactive billing is not inferred.")
    if a.get("tax_jurisdiction") != "pa_state_only" or a.get("tax_exempt"):
        raise ValueError("Only Pennsylvania state-only ordinary tax jurisdiction is implemented; verify locality and exemptions.")
    if a["tariff"] == "GS-M":
        if not a.get("ptc_review_confirmed") or a.get("demand_interval_minutes") not in (15, 30, 60):
            raise ValueError("Confirm annual <100-kW PTC review and the utility demand-meter interval.")
        for k in ("contract_demand_kw", "reactive_billing_kvar"):
            _number(a.get(k), k)
        if a["contract_demand_kw"] >= 100:
            raise ValueError("First GS-M default supply case requires contract demand below100kW.")
        if a["reactive_billing_kvar"] != 0:
            raise ValueError("This unity-power-factor study requires confirmed zero reactive billing demand.")
        validate_state(a, idx)
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or not a.get("der_ordinary_service_confirmed") or not a.get("der_eligibility_source"):
            raise ValueError("PV/storage requires utility-confirmed ordinary renewable service without Partial Services Rider; storage-only/standby is unsupported.")
        if equipment.get("pv_ac_kw", 0) > (50 if a["tariff"] == "RS" else 3000):
            raise ValueError("Renewable account exceeds the filed residential/commercial capacity limit.")
        if equipment.get("battery") and (not equipment.get("renewable_only_charging") or not equipment.get("no_battery_export")):
            raise ValueError("First renewable storage scope requires PV-only charging and no battery export.")


def validate_state(a, index, state=None, equipment=None):
    if state is not None and (not isinstance(state, dict) or type(state.get("january_refund_applied", False)) is not bool):
        raise ValueError("West Penn carried state must retain an explicit boolean January refund flag.")
    if a["tariff"] != "GS-M":
        return
    for k in ("history_billing_kw", "history_kwh"):
        values = (state or {}).get(k, a.get(k))
        if not isinstance(values, list) or len(values) != 11:
            raise ValueError("West Penn requires eleven ordered historical " + k + " values.")
        for v in values:
            _number(v, k)
    if max((state or {}).get("history_billing_kw", a["history_billing_kw"])) >= 100:
        raise ValueError("First GS-M default-supply scope requires <100 kW confirmed eligibility; historical peak does not establish a new PLC.")


def charge_lines(index, imports, exports, a, *, math, state=None):
    idx = pd.DatetimeIndex(index)
    if not math.convex and np.max(exports) > 1e-5:
        raise ValueError("West Penn export settlement is unsupported; all scenarios must be zero export.")
    if math.convex:
        math.constraints.append(exports == 0)
    residential = a["tariff"] == "RS"
    cls = 0 if residential else 1
    versions = [rates_on(d) for d in idx.date]
    energy = math.hours * math.sum(imports)
    def volumetric(key):
        values = [v[key][cls] if isinstance(v[key], tuple) else v[key] for v in versions]
        return math.hours * math.dot(imports, values)
    lines = {"distribution_customer": 9. if residential else 23.29,
             "distribution_energy": energy * (.04306 if residential else .00531)}
    next_state = deepcopy(state or {})
    metrics = {}
    if residential:
        peak = math.demand(imports, idx, minutes=int(math.hours * 60))
        if math.convex:
            math.constraints.append(peak <= 25.)
        elif peak > 25. + 1e-5:
            raise ValueError("Residential >25-kW special demand provisions require a separate account model.")
    else:
        history = (state or {}).get("history_billing_kw", a["history_billing_kw"])
        peak = math.demand(imports, idx, minutes=int(a["demand_interval_minutes"]))
        demand = math.maximum([peak, a["contract_demand_kw"], .5 * max(history)])
        if math.convex:
            # All demand coefficients, including the small tax credit, have
            # positive net marginal cost. One epigraph avoids thousands of
            # binary peak selectors; numeric rebilling proves equality.
            import cvxpy as cp
            epigraph = cp.Variable()
            math.constraints.extend([epigraph >= demand])
            floor = max(a["contract_demand_kw"], .5 * max(history))
            demand = math.register(epigraph, floor, max(floor, math.power_bound))
            math.constraints.append(demand <= 99.99999)
        elif demand >= 100:
            raise ValueError("GS-M default supply case exceeds its verified <100-kW enrollment scope.")
        lines["distribution_demand"] = 3.46 * demand
        lines["distribution_reactive"] = .22 * a["reactive_billing_kvar"]
        previous_kwh = (state or {}).get("history_kwh", a["history_kwh"])
        if all(v < 1500 for v in previous_kwh):
            if math.convex:
                math.constraints.append(energy >= 1500.)
            elif energy < 1500 - 1e-5:
                raise ValueError("Twelve consecutive <1500-kWh cycles require GS-Small reclassification.")
        next_state.update(history_billing_kw=(history + [demand])[-11:],
                          history_kwh=(previous_kwh + [energy])[-11:])
        metrics.update(measured_demand_kw=peak, billing_demand_kw=demand)
    base = sum(lines.values())
    lines.update(supply=volumetric("supply"),
                 default_service_support=volumetric("dss"), energy_efficiency=volumetric("eec"),
                 smart_meter=energy * -.00004 if residential else .85,
                 universal_service=volumetric("usc") if residential else 0.,
                 tcja=base * (-.0053 if a["bill_date"] >= "2025-07-01" else 0.))
    # Original p241: bills-rendered DSIC on distribution INCLUDING applicable
    # riders, excluding STAS. PTC supply is separate; DSS is nonbypassable
    # delivery service. TCJA itself excludes automatic-rider revenues.
    distribution = sum(v for k, v in lines.items() if k != "supply")
    lines["distribution_dsic"] = distribution * rates_on(a["bill_date"])["dsic"]
    lines["state_tax_adjustment"] = sum(lines.values()) * .0001
    # One January refund per account, already inclusive of GRT. It is a
    # separate post-tariff adjustment, not another STAS assessment basis.
    refund = a["bill_date"] < "2025-02-01" and not (state or {}).get("january_refund_applied", False)
    lines["january_refund"] = (-4.45 if residential else -15.48) if refund else 0.
    next_state["january_refund_applied"] = bool(refund or (state or {}).get("january_refund_applied", False))
    lines["sales_tax"] = 0. if residential else sum(lines.values()) * .06
    return dict(lines=lines, metrics=metrics, next_state=next_state, is_complete_bill=True,
                warnings=["Non-export qualifying renewable study; export credits, standby service and other districts are unsupported. Capacity/transmission are included in default supply; no separate PJM LMP/PLC charge."],
                rate_sources=SOURCES)
