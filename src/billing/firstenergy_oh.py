"""Ohio Edison ordinary RS / measured GS SSO, bounded verified 2025 scope.

Complete component intersections: January, June and August14–December31 2025.
The default rejects source gaps. Explicitly accepted provisional2025 studies
record assumptions separately. PJM wholesale prices never replace retail rates.
"""
from copy import deepcopy
from datetime import date

import numpy as np
import pandas as pd

from .firstenergy_pa import _number
from . import firstenergy_oh_provisional as provisional

UTILITY = "firstenergy_ohio_edison"
TIMEZONE = "America/New_York"
ROOT = "https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/Ohio/tariffs/"
SOURCES = [ROOT + "2025-OE-Electric-Service-Tariff.pdf",
           ROOT + "OE-2024-Electric-Service.pdf",
           "https://web.archive.org/web/20250612032328id_/" + ROOT + "OE-2025-Electric-Service.pdf",
           "https://web.archive.org/web/20250825000744id_/" + ROOT + "OE-2025-Electric-Service.pdf",
           "https://web.archive.org/web/20251104135547id_/" + ROOT + "OE-2025-Electric-Service.pdf",
           "https://codes.ohio.gov/ohio-revised-code/section-5751.03"]
COMPLETE_COVERAGE = [("2025-01-01", "2025-01-31"),
                     ("2025-06-01", "2025-06-30"),
                     ("2025-08-14", "2025-12-31")]
# This is the approved operating-plan transition, not approval of proposed
# ESP VI rates. It does not establish missing component sheets by itself.
ESP_TRANSITION = dict(effective_date="2025-02-01", previous="ESP V", current="ESP IV",
    source="https://www.sec.gov/Archives/edgar/data/1031296/000103129625000006/fe-20241231.htm")
GAPS = [dict(start="2025-02-01", end="2025-05-31",
             reason="Complete February ESP-IV compliance composite, including GEN Sheet114 revision18 and intermediate rider continuity, remains unverified."),
        dict(start="2025-07-01", end="2025-08-13",
             reason="LGR Sheet135 revision12 is missing; cycles crossing its August14 removal also require a verified fixed-charge allocation rule.")]


def rates_on(day, *, mode="verified"):
    day = str(day)[:10]
    if mode not in ("verified", "provisional_2025"):
        raise ValueError("Choose verified or explicitly accepted provisional_2025 Ohio Edison rates.")
    if not any(start <= day <= end for start, end in COMPLETE_COVERAGE):
        if mode == "provisional_2025" and "2025-01-01" <= day <= "2025-12-31":
            return provisional.rates_on(day, _verified_rates)
        reason = next((g["reason"] for g in GAPS if g["start"] <= day <= g["end"]), "Outside verified calendar2025 sources.")
        raise ValueError("Ohio Edison complete verified coverage is January, June and August14–December31 2025. " + reason + " No rate extrapolation.")
    return _verified_rates(day)


def _verified_rates(day):
    """Known component intersections; public access must pass rates_on's guard."""
    if day < "2025-02-01":
        return dict(esp="ESP V", aer=-.000167, drr=(.000006, .000005),
                    dun=.000409, gcr=.003073, ami=(2.141, 9.118), pur=.000030,
                    ndu=.000483, edr=(.001044, .003982), automaker=.000027,
                    nmb=(.021982, 6.2252), dcr=(.351979, .285339), dcr_basis="base_distribution",
                    supply_energy=.073408, supply_capacity=(.003080, .002908),
                    dse=0., pir=.000436, rer=.003541, vmc=(.000047, .0087),
                    lgr=(1.50, .0018007), sgf=(.10, .00029051))
    if day < "2025-07-01":
        return dict(esp="ESP IV", aer=.000207, drr=(.000006, .000004),
                    dun=.000920, gcr=-.002909, ami=(2.332, 9.081), pur=.000009,
                    ndu=.000549, edr=(.000262, .003090), automaker=.000024,
                    nmb=(.023602, 6.3482), dcr=(.009032, 3.3606), dcr_basis="energy_or_demand",
                    supply_energy=.073661, supply_capacity=(.021953, .021732),
                    dse=.001151, pir=.000436, rer=.003541, vmc=(0., 0.),
                    lgr=(1.50, .0018007), sgf=(.10, .00029051))
    october = day >= "2025-10-01"
    # Dollar/kWh, except AMI ($/month), NMB/DCR GS ($/billing kW).
    return dict(esp="ESP IV", aer=.000296 if october else .000175,
                drr=(-.000001, -.000001) if october else (.000002, .000001),
                dun=.000247 if october else .000888,
                gcr=.000841 if october else -.001206,
                ami=(2.378, 9.565) if october else (1.514, 5.450),
                pur=.000048 if october else .000015,
                ndu=.001000 if october else .000709,
                edr=(.000267, .002546) if october else (.000190, .001213),
                automaker=.000029 if october else .000026,
                nmb=(.024468, 7.1203) if october else (.023602, 6.3482),
                dcr=(.009048, 3.1087) if day >= "2025-12-01" else
                    (.008770, 3.2527) if day >= "2025-09-01" else (.009032, 3.3606),
                dcr_basis="energy_or_demand", supply_energy=.073661 if day < "2025-09-01" else .066966,
                supply_capacity=(.021953, .021732), dse=.000462, pir=.000476,
                rer=.003545, vmc=(0., 0.), lgr=(0., 0.), sgf=(0., 0.))


def account_fields(plan_id="RS"):
    fields = [
        {"name":"rate_evidence_mode", "type":"text", "label":"Tariff evidence mode", "choices":["verified","provisional_2025"]},
        {"name":"provisional_assumptions_accepted", "type":"boolean", "label":"I accept the documented provisional rates and billing rules; bills and savings are historical estimates", "default":False},
        {"name":"eligibility_confirmed", "type":"boolean", "label":"Confirmed Ohio Edison ordinary RS/GS SSO enrollment", "default":False, "required":True},
        {"name":"ordinary_service_confirmed", "type":"boolean", "label":"No legacy heating credits, special contracts, assistance, standby, primary metering or AMI opt-out", "default":False, "required":True},
        {"name":"no_local_tax_confirmed", "type":"boolean", "label":"Verified locality has no additional municipal utility/franchise charge", "default":False, "required":True},
        {"name":"cycle_source", "type":"text", "label":"Complete meter-cycle evidence or hypothetical assumption", "required":True},
        {"name":"bill_date", "type":"date", "label":"Bill date selecting DCR and SGF", "required":True},
        {"name":"der_ordinary_service_confirmed", "type":"boolean", "label":"Utility-approved renewable PV/storage account not subject to Partial Service rider", "default":False, "required":False},
        {"name":"der_eligibility_source", "type":"text", "label":"Approved ordinary renewable service evidence or hypothetical assumption", "required":False},
    ]
    if plan_id == "GS":
        fields.append({"name":"contract_demand_kw", "type":"number", "label":"Actual utility contract demand (kW), not inferred from monthly peak", "required":True})
    return fields


def defaults(plan_id="RS"):
    if plan_id not in ("RS", "GS"):
        raise ValueError("Select Ohio Edison RS or measured General Service Secondary GS.")
    return dict(tariff=plan_id, supply="sso", export_mode="none", eligibility_confirmed=False,
                rate_evidence_mode="verified", provisional_assumptions_accepted=False,
                ordinary_service_confirmed=False, no_local_tax_confirmed=False,
                cycle_source="", cycle_kind="regular", billing_month="2025-10-01", bill_date="2025-10-31",
                voltage="secondary", phase="single", voltage_v=240., power_factor=1.,
                contract_demand_kw=0., der_ordinary_service_confirmed=False, der_eligibility_source="")


def hypothetical_defaults(plan_id="RS", year=2025):
    a = defaults(plan_id)
    a.update(eligibility_confirmed=True, ordinary_service_confirmed=True, no_local_tax_confirmed=True,
             cycle_source="Hypothetical complete calendar cycle; no actual customer bill",
             der_ordinary_service_confirmed=True,
             der_eligibility_source="Hypothetical approved qualifying renewable account exempt from Partial Service; zero export and PV-only charging",
             hypothetical_account=True)
    return a


def catalog():
    return [dict(id=p, label=label, status="supported", customer_class=kind,
                 coverage=[dict(start=start, end=end) for start, end in COMPLETE_COVERAGE],
                 coverage_gaps=deepcopy(GAPS), esp_transition=deepcopy(ESP_TRANSITION), voltage="secondary",
                 provisional_coverage=[dict(start="2025-01-01",end="2025-12-31")],
                 provisional_assumptions=deepcopy(provisional.ASSUMPTIONS),
                 supply_arrangements=["sso"],
                 solar_modes=["non_export"], equipment_modes=["grid_only", "pv_only", "pv_battery"],
                 representative_peak_kw=3. if p == "RS" else 20.,
                 account_fields=account_fields(p), sources=SOURCES+[provisional.TESTIMONY+"Testimony-Brandon-McMillen.pdf",provisional.TESTIMONY+"Testimony-Dhara-Patel.pdf"],
                 eligibility="Ohio Edison district only, ordinary SSO, single-meter 240 V single phase; measured 30-minute GS demand, no special/legacy credits, municipal charges or standby rider.",
                 limitations=["Verified service dates: January, June and August14–December31 2025; complete regular 25–35-day cycles only. Full-year 2025 requires explicit provisional mode and acceptance.",
                              "February–May ESP-transition composite and July1–August13 LGR rates remain unverified. Verified mode rejects these dates; provisional mode records reconstruction, carry-forward and August RS allocation assumptions.",
                              "Zero export, utility-confirmed ordinary renewable service, PV-only battery charging. No export credits or Partial Service estimate."])
            for p, label, kind in [("RS", "Ohio Edison Residential RS (SSO)", "residential"),
                                   ("GS", "Ohio Edison General Service Secondary GS (SSO)", "commercial")]]


def validate_account(a, index, equipment=None):
    idx = pd.DatetimeIndex(index)
    if not isinstance(a, dict) or a.get("tariff") not in ("RS", "GS") or a.get("supply") != "sso" or a.get("export_mode") != "none":
        raise ValueError("Select Ohio Edison ordinary SSO; competitive supply and export settlement are unsupported.")
    if any(a.get(k) is not True for k in ("eligibility_confirmed", "ordinary_service_confirmed", "no_local_tax_confirmed")):
        raise ValueError("Confirm Ohio Edison eligibility, ordinary service, absent legacy/special provisions and locality charges.")
    mode=a.get("rate_evidence_mode","verified")
    if (mode not in ("verified","provisional_2025") or type(a.get("provisional_assumptions_accepted",False)) is not bool
            or mode=="provisional_2025" and a.get("provisional_assumptions_accepted") is not True):
        raise ValueError("Provisional Ohio Edison2025 rates require explicit mode selection and acceptance of the documented assumptions.")
    stop = idx[-1] + (idx[1] - idx[0])
    if (str(idx.tz) != TIMEZONE or a.get("cycle_kind") != "regular" or not a.get("cycle_source")
            or idx[0] != idx[0].normalize() or stop != stop.normalize()
            or not 25 <= (stop.date() - idx[0].date()).days <= 35):
        raise ValueError("First Ohio Edison scope requires a complete regular 25–35-day Eastern-time cycle; partial charges are unverified.")
    for d in (idx[0].date(), idx[-1].date(), date.fromisoformat(a["bill_date"])):
        rates_on(d,mode=mode)
    if date.fromisoformat(a["bill_date"]) < idx[-1].date():
        raise ValueError("Bill date cannot precede service end.")
    if a.get("voltage") != "secondary" or a.get("phase") != "single" or a.get("voltage_v") != 240. or a.get("power_factor") != 1.:
        raise ValueError("First Ohio Edison case uses confirmed 240 V single-phase unity-PF service, without primary-metering corrections.")
    _number(a.get("contract_demand_kw"), "contract demand")
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or a.get("der_ordinary_service_confirmed") is not True or not a.get("der_eligibility_source"):
            raise ValueError("Utility must confirm renewable ordinary-service treatment without Partial Service; storage-only is unsupported.")
        if equipment.get("battery") and (not equipment.get("renewable_only_charging") or not equipment.get("no_battery_export")):
            raise ValueError("First renewable scope requires PV-only charging and zero battery export.")


def charge_lines(index, imports, exports, a, *, math, state=None):
    idx = pd.DatetimeIndex(index)
    if math.convex:
        math.constraints.append(exports == 0)
    elif np.max(exports) > 1e-5:
        raise ValueError("Ohio Edison export settlement is unsupported; zero export is required.")
    residential = a["tariff"] == "RS"
    cls = 0 if residential else 1
    mode=a.get("rate_evidence_mode","verified")
    versions = [rates_on(d,mode=mode) for d in idx.date]
    billed = rates_on(a["bill_date"],mode=mode)
    evidence=provisional.evidence(idx,a)
    energy = math.hours * math.sum(imports)
    def volume(key):
        return math.hours * math.dot(imports, [v[key][cls] if isinstance(v[key], tuple) else v[key] for v in versions])
    lines = dict(distribution_customer=4. if residential else 7.)
    metrics = {}
    if residential:
        lines["distribution_energy"] = .031898 * energy
    else:
        peak = math.demand(imports, idx, minutes=30)
        demand = math.maximum([peak, 5., a["contract_demand_kw"]])
        lines["distribution_demand"] = 12.8 + 5.4635 * (demand - 5.)
        metrics.update(measured_demand_kw=peak, billing_demand_kw=demand)
    # GEN energy/capacity and rider dates are independent. June and August are
    # summer; January and September–December are winter. No automatic RDC/BDC credit.
    base_distribution = sum(lines.values())
    dcr = (billed["dcr"][cls] * base_distribution if billed["dcr_basis"] == "base_distribution"
           else billed["dcr"][cls] * (energy if residential else demand))
    lgr=versions[0]["lgr"][cls] if residential else volume("lgr")
    if residential and len({v["lgr"][cls] for v in versions})>1:
        if mode!="provisional_2025":
            raise ValueError("A fixed LGR change inside a cycle requires verified allocation or explicit provisional mode.")
        # Explicit research rule: equal weight per LOCAL service day, including
        # a23/25-hour DST day, never physical-interval daily proration.
        by_day={d:v["lgr"][cls] for d,v in zip(idx.date,versions)}
        lgr=sum(by_day.values())/len(by_day)
    lines.update(supply_energy=volume("supply_energy"),
                 supply_capacity=volume("supply_capacity"),
                 non_market_transmission=volume("nmb") if residential else demand * versions[0]["nmb"][cls],
                 delivery_capital=dcr,
                 alternative_energy=volume("aer"), delta_revenue=volume("drr"),
                 distribution_uncollectible=volume("dun"), generation_reconciliation=volume("gcr"),
                 pipp_uncollectible=volume("pur"), nondistribution_uncollectible=volume("ndu"),
                 economic_development=volume("edr"), automaker_recovery=volume("automaker"),
                 tax_savings=energy * (-.001725 if residential else -.001028),
                 demand_side_efficiency=volume("dse"), phase_in_recovery=volume("pir"),
                 residential_heating_recovery=volume("rer") if residential else 0.,
                 consumer_rate_credit=-.51 if residential else -.000298 * energy,
                 legacy_generation=lgr,
                 solar_generation_fund=billed["sgf"][cls] * (1. if residential else energy))
    vmc = volume("vmc") if residential else demand * versions[0]["vmc"][cls]
    if versions[0]["vmc"][cls]:
        lines["vegetation_management"] = vmc
    # Service-rendered fixed AMI changes require a documented allocation, not
    # an invented daily fixed-fee proration in a spanning meter cycle.
    if len({v["ami"] for v in versions}) != 1 or not residential and len({v["nmb"] for v in versions}) != 1:
        raise ValueError("A fixed AMI or demand NMB rate change inside a cycle requires sourced allocation; use verified complete cycles.")
    lines["advanced_meter"] = versions[0]["ami"][cls]
    # Representative RS/GS cases stay below the documented833000-kWh block.
    if math.convex:
        math.constraints.append(energy <= 833000.)
    elif energy > 833000. + 1e-5:
        raise ValueError("First ordinary RS/GS case is bounded below the USF833000-kWh threshold.")
    lines["universal_service"] = .0028408 * energy
    # Sheet92 tax grossed up for the Ohio Commercial Activity Tax, not sales tax.
    lines["state_kwh_tax"] = math.tiered(energy, [2000., 15000.], [.00465, .00419, .00363]) / (1. - .0026)
    warnings=["Ordinary SSO: capacity is in GEN and transmission in NMB; no additional wholesale LMP/PLC charge. Legacy heating credits, standby, municipal charges and export settlement are excluded by account eligibility."]
    if evidence["rate_evidence_status"]=="provisional":
        warnings.append("Provisional historical estimate: rates/rules use "+", ".join(x["id"] for x in evidence["rate_assumptions"])+". Reconciliation, solver optimality and OpenDSS do not verify historical tariff accuracy; inspect the assumptions table.")
    return dict(lines=lines, metrics=metrics, next_state=deepcopy(state or {}), is_complete_bill=True, **evidence,
                warnings=warnings,
                rate_sources=sorted(set(SOURCES+[source for item in evidence["rate_assumptions"] for source in item["sources"]])))
