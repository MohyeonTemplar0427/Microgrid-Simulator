"""Schema 11 main-wizard retail studies with utility-specific jurisdictions/clocks.

One shared physical input path; separate jurisdiction adapters own every rate.
All execution remains offline in the immutable, process-isolated study worker.
"""
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..billing.regional import UTILITIES,adapter,account_region,cycle_partitions,cycle_account,bill_scope
from ..dispatch.battery import Battery
from ..timeseries import build_interval_index
from .contract import DEFAULT_SITE_REQUEST,number,identifier
from .site_profile import customer_class


SITES={"firstenergy_pa_penn_power":(41.00,-80.35,"Explicit hypothetical New Castle/Lawrence County Pennsylvania site; Penn Power district/default PTC, state-only tax, GS-S/GSDS history and active ordinary renewable approval are independent account facts, not inferred from coordinates"),
       "firstenergy_pa_penelec":(40.52,-78.40,"Explicit hypothetical Altoona/Blair County Pennsylvania site; Penelec district/default PTC, state-only tax, retained GS-S assignment and active ordinary renewable approval are independent facts, not inferred from coordinates"),
       "firstenergy_pa_met_ed":(40.34,-75.93,"Explicit hypothetical Reading/Berks County Pennsylvania site; Met-Ed district, default supply, state-only tax, Company GS-S qualification and active ordinary renewable approval are independent facts, not inferred from coordinates"),
       "rockland_electric_new_jersey":(40.95,-74.02,"Explicit hypothetical Bergen County/Eastern Division site; Rockland BGS-RSCP, non-demand billing, ordinary taxable service and active DER approval are independent account facts, not inferred from coordinates"),
       "jcpl_new_jersey":(40.28,-74.12,"Explicit hypothetical Monmouth County, New Jersey site; JCP&L service, BGS-RSCP, PLS, tax and active ordinary DER/no-STB classification are independently confirmed, not inferred from coordinates"),
       "atlantic_city_electric_new_jersey":(39.45,-74.58,"Explicit hypothetical Atlantic County, New Jersey site; ACE territory, BGS-RSCP, PLS, tax status and written interconnection approval are independent, not inferred from coordinates"),
       "potomac_edison_maryland":(39.60,-77.73,"Hypothetical unincorporated Washington County, Maryland site; Potomac Edison utility/SOS, unmetered history and tax jurisdiction independently confirmed, not inferred from coordinates"),
       "delmarva_maryland":(38.40,-75.65,"Hypothetical unincorporated Wicomico County, Maryland site; Delmarva service, SOS, estimated-demand assignment and tax jurisdiction independently confirmed, not inferred from coordinates"),
       "pepco_maryland":(39.05,-77.18,"Hypothetical unincorporated Montgomery County, Maryland site; Pepco service, SOS and tax jurisdiction independently confirmed, not inferred from coordinates"),
       "bge_maryland":(39.08,-76.57,"Hypothetical unincorporated Anne Arundel County, Maryland site outside Annapolis/Highland Beach; BGE service, SOS and tax jurisdiction require independent confirmation"),
       "ppl_electric_pennsylvania":(40.63,-75.61,"Hypothetical unincorporated Lehigh County, Pennsylvania site; PPL service, ordinary default supply and tax jurisdiction are explicit account assumptions, not a map finding"),
       "aep_ohio":(40.22,-83.03,"Hypothetical unincorporated Delaware County, Ohio site; Ohio Power Company service, legacy rate zone and absence of municipal charges require separate account confirmation"),
       "alliant_energy_iowa":(42.10,-91.46,"Hypothetical rural Linn County, Iowa site; Interstate Power & Light service and unincorporated tax jurisdiction are explicit account assumptions, not a map finding"),
       "we_energies_wisconsin":(43.05,-88.25,"Hypothetical unincorporated Waukesha County, Wisconsin site; Wisconsin Electric service and tax jurisdiction independently confirmed, not a map finding"),
       "duke_energy_indiana":(39.70,-86.40,"Hypothetical Plainfield/Hendricks County, Indiana site; Duke Indiana service, local charges and Eastern-clock account independently confirmed, not a map finding"),
       "xcel_energy_minnesota":(45.42,-93.83,"Hypothetical unincorporated Sherburne County, Minnesota site; NSP service and tax jurisdiction independently confirmed, not a map finding"),
       "ameren_missouri":(38.49,-92.16,"Hypothetical unincorporated Cole County, Missouri site; Ameren service and tax jurisdiction independently confirmed, not a map finding"),
       "ameren_illinois":(39.75,-89.70,"Hypothetical unincorporated Sangamon County, Illinois site; Ameren service, Rate Zone II and no municipal charges independently confirmed"),
       "dominion_energy_virginia":(37.63,-77.52,"Hypothetical Henrico-area Virginia site; locality independently confirmed"),
       "dominion_energy_north_carolina":(36.44,-76.50,"Hypothetical northeastern North Carolina site"),
       "pseg":(40.74,-74.17,"Hypothetical Newark, New Jersey site"),
       "firstenergy_pa_west_penn":(40.30,-79.54,"Hypothetical Westmoreland County, Pennsylvania site; West Penn service independently confirmed"),
       "firstenergy_ohio_edison":(41.16,-81.64,"Hypothetical unincorporated Summit County, Ohio site; Ohio Edison service and absence of municipal charges independently confirmed"),
       "peco":(39.96,-75.60,"Hypothetical Chester County, Pennsylvania site; PECO service independently confirmed; outside Philadelphia"),
       "consumers_energy":(42.96,-85.67,"Hypothetical Grand Rapids-area Michigan site; Consumers service and absence of additional locality charges independently confirmed"),
       "dte_electric":(42.28,-83.73,"Hypothetical Ann Arbor-area Michigan site; DTE service and no additional locality charges independently confirmed")}


def calendar_cycles(start,end):
    """An explicitly hypothetical meter schedule, never an inferred real cycle."""
    first,last=pd.Timestamp(start),pd.Timestamp(end)
    result=[]
    for month in pd.date_range(first.normalize().replace(day=1),last.normalize().replace(day=1),freq="MS"):
        a=max(first,month);b=min(last,month+pd.offsets.MonthEnd())
        result.append({"start_date":a.date().isoformat(),"end_date":b.date().isoformat(),
            "billing_month":month.date().isoformat(),"bill_date":b.date().isoformat(),
            "kind":"hypothetical_calendar","source":"Explicit hypothetical calendar meter cycle, not an actual utility reading schedule",
            "account_overrides":{}})
    return result


def defaults(utility="dominion_energy_virginia",kind="residential",plan_id=None):
    module=adapter(utility)
    plans=[p for p in module.catalog() if p.get("status")=="supported" and p.get("customer_class")==kind]
    if not plans:
        raise ValueError("No supported plan for this utility/customer class.")
    plan_id=plan_id or next((p["id"] for p in plans if p["id"] in ("VA-1G","1T","RS","VA-GS2T","5P","GLP")),plans[0]["id"])
    plan=next(p for p in plans if p["id"]==plan_id)
    account=(module.hypothetical_defaults(plan_id) if hasattr(module,"hypothetical_defaults") else module.defaults(plan_id))
    coverage=plan["coverage"][-1]
    first=pd.Timestamp(coverage["start"])
    preferred=account.get("billing_month")
    candidate=None
    if type(preferred) is int and 1<=preferred<=12:
        candidate=first.replace(month=preferred,day=1)
    elif isinstance(preferred,str) and len(preferred)==10:
        candidate=pd.Timestamp(preferred)
    if candidate is not None and any(pd.Timestamp(w["start"])<=candidate and candidate+pd.offsets.MonthEnd()<=pd.Timestamp(w["end"]) for w in plan["coverage"]):
        # Hypothetical history is anchored to this declared billing month.
        # Broader verified coverage must not silently move that account to a
        # different month (or outside a solar program's separate dated terms).
        first=candidate
    start=(first if first.day==1 else first+pd.offsets.MonthBegin()).date().isoformat()
    end=min(pd.Timestamp(start)+pd.offsets.MonthEnd(),pd.Timestamp(coverage["end"])).date().isoformat()
    lat,lon,label=SITES[utility]
    residential=kind=="residential"
    supplier=account.get("supply",account.get("supplier",account.get("supply_arrangement","bundled")))
    request={"schema_version":11,"name":"Untitled study",
        "site":{"latitude":lat,"longitude":lon,"label":label,"utility":utility},
        "site_profile":{"site_type":kind,"subtype":"house" if residential else None},
        "regional_account":{"distribution_utility":utility,"state_jurisdiction":UTILITIES[utility]["state"],
            "retail_supplier":utility,"grid_operator":UTILITIES[utility].get("grid_operator","PJM"),"transmission_zone":UTILITIES[utility]["zone"],
            "wholesale_pricing_location":None,"verification_kind":"hypothetical_case",
            "reference":"Explicit hypothetical retail account, not a territory or enrollment finding"},
        "account":account,"start_date":start,"end_date":end,"timezone":data_timezone(utility),"timestep_minutes":15,
        "billing_cycles":calendar_cycles(start,end),
        "load":{"mode":"synthetic","power_kw":plan.get("representative_peak_kw",3. if residential else 90. if utility.endswith("virginia") else 40.),
            "archetype":"residential" if residential else "office","csv":None,
            "source":"Generic deterministic household/office reference shape; synthetic, not measured or regionally calibrated",
            "native_basis_confirmed":False},
        "solar":{**deepcopy(DEFAULT_SITE_REQUEST["solar"]),"dc_capacity_kw":5. if residential else 10.},
        "pv_capacity_kw":4. if residential else 8.,"weather_source":"clear_sky","weather_id":None,"weather":None,
        "battery":{**deepcopy(DEFAULT_SITE_REQUEST["battery"]),"capacity_kWh":10. if residential else 30.,
            "energy_kWh":5. if residential else 15.,"max_charge_kw":3. if residential else 8.,"max_discharge_kw":3. if residential else 8.},
        "ess":None,"degradation_cost_per_kWh":.03,"include_degradation_in_optimization":False,
        "credit_objective_policy":"exclude_opening_credits","tariff_comparisons":[],"carbon":None,
        "operating_contract":{"mode":"non_export","interconnection_confirmed":False,"grid_charging_confirmed":False,
            "renewable_only_charging":False,"no_battery_export":True,"reference":""},
        "electrical_service":{"voltage":account.get("voltage",plan.get("voltage","secondary")),"phase":account.get("phase","single" if residential else "three"),
            "nominal_voltage_v":account.get("delivery_voltage_kv",0)*1000 or account.get("voltage_v",240 if residential else 480),
            "reference":"Explicit representative circuit assumption, not surveyed site wiring"}}
    if UTILITIES[utility].get("grid_operator") == "MISO":
        request["regional_account"].update({k:UTILITIES[utility][k] for k in ("resource_adequacy_zone","transmission_owner")})
    if utility=="pseg" and plan_id.startswith("GLP"):
        # Keep combined DER below the ordinary-service threshold even after
        # starting demand history rolls out. These remain explicit assumptions.
        request["load"]["power_kw"]=40.
        request["solar"]["dc_capacity_kw"]=6.25
        request["pv_capacity_kw"]=5.
        request["battery"].update(max_charge_kw=5.,max_discharge_kw=5.)
    if utility.startswith("firstenergy_"):
        request["operating_contract"]["renewable_only_charging"]=True
    if utility in ("alliant_energy_iowa", "aep_ohio", "bge_maryland", "pepco_maryland", "delmarva_maryland", "potomac_edison_maryland", "atlantic_city_electric_new_jersey", "jcpl_new_jersey", "rockland_electric_new_jersey", "firstenergy_pa_met_ed", "firstenergy_pa_penelec", "firstenergy_pa_penn_power") and not residential:
        # An explicitly small-office reference, not automatic classification
        # from a simulated monthly/annual load or the default larger office.
        request["solar"]["dc_capacity_kw"]=5.
        request["pv_capacity_kw"]=4.
        request["battery"].update(capacity_kWh=10.,energy_kWh=5.,max_charge_kw=3.,max_discharge_kw=3.)
    return request


def data_timezone(utility):
    """Utility study clock; adding Central time must not shift existing studies."""
    return UTILITIES[utility].get("timezone","America/New_York")


def capabilities():
    utilities={}
    for utility,data in UTILITIES.items():
        module=adapter(utility)
        plans=module.catalog()
        supported=[p for p in plans if p.get("status")=="supported"]
        utilities[utility]={"id":utility,"label":data["label"],"state":data["state"],"transmission_zone":data["zone"],
            "grid_operator":data.get("grid_operator","PJM"),"resource_adequacy_zone":data.get("resource_adequacy_zone"),
            "transmission_owner":data.get("transmission_owner"),"timezone":data_timezone(utility),
            "transmission_ownership_context":data.get("transmission_ownership_context"),
            "grid_sources":data.get("grid_sources",[]),
            "plans":plans,"accounts":{p["id"]:module.defaults(p["id"]) for p in supported},
            "hypothetical_accounts":{p["id"]:(module.hypothetical_defaults(p["id"]) if hasattr(module,"hypothetical_defaults") else module.defaults(p["id"])) for p in supported},
            "study_defaults_by_plan":{p["id"]:defaults(utility,p["customer_class"],p["id"]) for p in supported},
            "hypothetical_nem":{p["id"]:module.nem_defaults(p["id"]) for p in supported if "net_metering" in p.get("solar_modes",[]) } if hasattr(module,"nem_defaults") else {},
            "defaults":{kind:defaults(utility,kind) for kind in ("residential","commercial")
                if any(p["customer_class"]==kind for p in supported)}}
    return {"schema_version":11,"utilities":utilities,"timezone":"America/New_York",
        "interval_minutes":[15,30],"max_days":366,"csv_max_bytes":2*1024*1024,
        "credit_objective_policies":["exclude_opening_credits","explicit_cash_bill"],
        "scope":"Local candidate. Utility-specific dated retail bills; rolling-cycle historical perfect foresight, actual credit/history/SOC continuity, representative electrical replay."}


def _load(settings,grid,kind):
    from .comed_study import _csv_series
    from ..profiles import ConstantLoad,SyntheticLoad,BuildingArchetype,LoadScaling,CSVLoad
    if (not isinstance(settings,dict) or set(settings)!={"mode","power_kw","archetype","csv","source","native_basis_confirmed"}
            or not isinstance(settings["source"],str) or not 1<=len(settings["source"].strip())<=500
            or type(settings["native_basis_confirmed"]) is not bool):
        raise ValueError("Identify the native-load source and whether it is measured, reference or synthetic.")
    mode=settings["mode"]
    if mode=="csv":
        if settings["native_basis_confirmed"] is not True or settings["power_kw"] is not None or settings["archetype"] is not None:
            raise ValueError("Confirm native consumption before PV/storage; net meter purchases cannot silently become building load.")
        series=_csv_series(settings["csv"],"native_load_kw",max_rows=min(35136,len(grid.index)))
        if not series.index.equals(grid.index.tz_convert("UTC")) or not np.isfinite(series).all() or (series<0).any():
            raise ValueError("Native CSV must match every exact study interval with finite nonnegative kW; no resampling, interpolation or scaling.")
        return CSVLoad(pd.DataFrame({"timestamp":series.index,"native_load_kw":series.values}),load_column="native_load_kw").build_load_kw(grid).to_numpy()
    if mode not in ("constant","synthetic") or settings["csv"] is not None:
        raise ValueError("Choose explicit constant/synthetic native demand or a complete native CSV.")
    number(settings["power_kw"],"Native power",0,100000)
    allowed=("residential","multifamily") if kind=="residential" else ("office","retail","school","industrial")
    if settings["archetype"] not in allowed:
        raise ValueError("Select a generic native-load archetype appropriate to the account; no California model is assigned.")
    model=ConstantLoad(settings["power_kw"]) if mode=="constant" else SyntheticLoad(
        archetype=BuildingArchetype(settings["archetype"]),scaling=LoadScaling.PEAK_KW,peak_kw=settings["power_kw"],
        variability_fraction=0,random_seed=20260101)
    return model.build_load_kw(grid).to_numpy()


def _validate_rate_evidence_selection(account, plan):
    """Require an explicit, typed opt-in before any provisional input is used.

    Legacy saved accounts without these optional fields retain verified-only
    behavior. The utility adapter still decides whether a particular dated
    cycle actually uses assumptions; selecting the mode is not rate evidence.
    """
    fields={item["name"]:item for item in plan.get("account_fields",[]) if isinstance(item,dict)}
    choices=fields.get("rate_evidence_mode",{}).get("choices")
    if not choices:
        return
    mode=account.get("rate_evidence_mode","verified")
    accepted=account.get("provisional_assumptions_accepted",False)
    if (mode not in choices or type(accepted) is not bool
            or mode!="verified" and accepted is not True):
        raise ValueError("Select a supported rate evidence mode and explicitly accept the documented provisional rates and billing assumptions. Verified mode never fills rate gaps.")


def _rate_evidence_manifest(account, bills):
    """Keep selected permissions separate from assumptions actually used."""
    bills=list(bills)
    status=("provisional" if any(b.get("rate_evidence_status")=="provisional" for b in bills)
            else "verified" if bills and all(b.get("rate_evidence_status")=="verified" for b in bills)
            else "not_recorded")
    return {"selected_mode":account.get("rate_evidence_mode","verified"),
            "provisional_assumptions_accepted":account.get("provisional_assumptions_accepted",False),
            "status":status,
            "assumption_models":sorted({b["assumption_model"] for b in bills if b.get("assumption_model")}),
            "assumption_ids":sorted({item["id"] for b in bills for item in b.get("rate_assumptions",[])}),
            "note":"Selection permits only the catalogued assumptions. Each cycle and component records whether they were actually used; component completeness is separate from historical verification."}


def prepare(r):
    utility=r.get("site",{}).get("utility") if isinstance(r,dict) else None
    if utility not in UTILITIES:
        raise ValueError("Choose a supported regional utility with explicit district and jurisdiction confirmation.")
    if set(r)-{"tariff_comparisons","carbon"}!=set(defaults(utility)) - {"tariff_comparisons","carbon"} or type(r.get("schema_version")) is not int or r["schema_version"]!=11:
        raise ValueError("Supply exactly the regional main-study schema 11 fields.")
    if not isinstance(r["name"],str) or not 1<=len(r["name"].strip())<=120:
        raise ValueError("Supply a valid draft/saved title.")
    kind=customer_class(r["site_profile"])
    account_region(r["regional_account"],utility)
    site=r["site"]
    if set(site)!={"latitude","longitude","label","utility"} or not isinstance(site["label"],str) or not site["label"].strip():
        raise ValueError("Supply site coordinates and a label independently of utility service confirmation.")
    number(site["latitude"],"Latitude",-90,90);number(site["longitude"],"Longitude",-180,180)
    if r["timezone"]!=data_timezone(utility) or type(r["timestep_minutes"]) is not int or r["timestep_minutes"] not in (15,30):
        raise ValueError("Use the selected utility's configured timezone and 15/30-minute interval averages, not hourly commercial demand guesses.")
    try:
        if not 0<=(date.fromisoformat(r["end_date"])-date.fromisoformat(r["start_date"])).days<366:
            raise ValueError("Study exceeds one historical year.")
        grid=build_interval_index(r["start_date"],r["end_date"],r["timezone"],r["timestep_minutes"])
    except (TypeError,ValueError) as exc:
        raise ValueError("Use valid inclusive local dates, at most 366 service days.") from exc
    from .regional_carbon import validate as validate_carbon
    validate_carbon(r)
    module=adapter(utility)
    plans={p["id"]:p for p in module.catalog()}
    a=r["account"]
    if not isinstance(a,dict) or a.get("tariff") not in plans:
        raise ValueError("Choose an engine-supported account billing plan.")
    plan=plans[a["tariff"]]
    if plan.get("status")!="supported":
        raise ValueError(plan.get("reason") or "This plan is not implemented.")
    if plan.get("customer_class")!=kind:
        raise ValueError("The selected billing plan does not match the residential/commercial site class.")
    _validate_rate_evidence_selection(a,plan)
    supplier=a.get("supply",a.get("supplier",a.get("supply_arrangement")))
    if r["regional_account"]["retail_supplier"]!=utility:
        raise ValueError("This adapter requires the named utility as default retail supplier; third-party supply needs a complete contract model.")
    if utility=="pseg" and supplier=="bgs_ciep":
        location=r["regional_account"]["wholesale_pricing_location"]
        if not location or str(location["pnode_id"])!="116472957" or location["pnode_name"]!="PSEG_RESID_AGG" or location["zone"]!="":
            raise ValueError("PSE&G CIEP requires the independently verified PSEG_RESID_AGG node116472957 with its native blank zone; no hub substitution.")
    load=_load(r["load"],grid,kind)
    if not isinstance(r["solar"],dict) or set(r["solar"])!=set(DEFAULT_SITE_REQUEST["solar"]):
        raise ValueError("Supply the shared PV/inverter settings.")
    for key,bounds in {"dc_capacity_kw":(0,100000),"tilt_degrees":(0,90),"azimuth_degrees":(0,359.999999),
            "system_losses_fraction":(0,.999999),"inverter_efficiency":(.001,1),"temperature_c":(-95,65),"wind_speed_m_per_s":(0,120)}.items():
        number(r["solar"][key],key,*bounds)
    number(r["pv_capacity_kw"],"AC inverter rating",0,100000)
    pv=r["solar"]["dc_capacity_kw"]>0
    if pv and r["pv_capacity_kw"]<=0 or not pv and r["pv_capacity_kw"]!=0:
        raise ValueError("PV arrays require an AC inverter; absent PV requires zero inverter rating.")
    battery=Battery(**r["battery"]) if r["battery"] is not None else None
    if r["ess"] is not None:
        from ..equipment.ess import validate_resolution
        if validate_resolution(r["ess"])["battery"]!=r["battery"]:
            raise ValueError("Battery settings do not match reviewed ESS equipment.")
    number(r["degradation_cost_per_kWh"],"Estimated wear",0,10)
    if type(r["include_degradation_in_optimization"]) is not bool or r["credit_objective_policy"] not in ("exclude_opening_credits","explicit_cash_bill"):
        raise ValueError("Choose explicit wear and carried-credit objective policies.")
    op=r["operating_contract"]
    if (not isinstance(op,dict) or set(op)!=set(defaults(utility)["operating_contract"])
            or op["mode"] not in ("non_export","net_metering")
            or any(type(op[k]) is not bool for k in ("interconnection_confirmed","grid_charging_confirmed","renewable_only_charging","no_battery_export"))):
        raise ValueError("Supply the explicit approved non-export or net-metering operating contract.")
    if pv or battery:
        if op["interconnection_confirmed"] is not True or not isinstance(op["reference"],str) or not op["reference"].strip():
            raise ValueError("Document parallel-operation approval or clearly label a hypothetical interconnection assumption.")
    if op["mode"]=="net_metering":
        if not pv:
            raise ValueError("Solar net metering requires eligible renewable PV equipment.")
        if battery and (not op["renewable_only_charging"] or not op["no_battery_export"] or op["grid_charging_confirmed"]):
            raise ValueError("This solar-storage path requires PV-only battery charging and no battery exports; grid-charged export is unsupported.")
    elif battery and not op["grid_charging_confirmed"] and not pv:
        raise ValueError("Storage-only studies require explicit grid-charging authorization.")
    account_export=a.get("export_mode",a.get("solar_mode",a.get("solar_program","none")))
    if (account_export in ("net_metering","nem"))!=(op["mode"]=="net_metering"):
        raise ValueError("The account's export enrollment and operating contract must agree.")
    if r["weather_source"] not in ("clear_sky","nsrdb","era5"):
        raise ValueError("Select explicit clear-sky, historical NSRDB or historical ERA5 weather; no source substitution.")
    if r["weather_source"]=="nsrdb" and pv:
        from .site_inputs import validate_weather_request
        if not identifier(r["weather_id"]) or r["weather"] is not None or r["start_date"][:4]!=r["end_date"][:4]:
            raise ValueError("Retrieve matching historical NSRDB weather for the actual study year.")
        validate_weather_request({"latitude":site["latitude"],"longitude":site["longitude"],"year":int(r["start_date"][:4]),
            "timezone":r["timezone"],"timestep_minutes":r["timestep_minutes"]})
    elif r["weather_source"]=="era5" and pv:
        from ..profiles.era5 import parse_era5
        if (r["weather_id"] is not None or not isinstance(r["weather"],dict)
                or set(r["weather"])!={"provider","raw_json","request","retrieved_at"}
                or r["weather"]["provider"]!="open_meteo_era5" or not isinstance(r["weather"]["retrieved_at"],str)):
            raise ValueError("Retrieve explicit site- and period-matched ERA5 weather, including source and retrieval metadata.")
        parse_era5(r["weather"]["raw_json"],grid,site["latitude"],site["longitude"])
    elif r["weather_id"] is not None or r["weather"] is not None:
        raise ValueError("Do not retain unused weather inputs or silently substitute their provider.")
    electrical=r["electrical_service"]
    if (not isinstance(electrical,dict) or set(electrical)!={"voltage","phase","nominal_voltage_v","reference"}
            or electrical["voltage"] not in ("secondary","primary","subtransmission","high_voltage","transmission")
            or electrical["phase"] not in ("single","three") or not isinstance(electrical["reference"],str) or not electrical["reference"].strip()):
        raise ValueError("Supply explicit electrical service facts or a clearly labeled representative circuit assumption.")
    number(electrical["nominal_voltage_v"],"Nominal service voltage",100,500000)
    account_voltage=a.get("voltage",plan.get("voltage"))
    numeric_volts=a.get("voltage_v") or (a.get("delivery_voltage_kv",0)*1000)
    if account_voltage is None and numeric_volts:
        account_voltage="high_voltage" if numeric_volts>=69000 else "primary" if numeric_volts>=2400 else "secondary"
    if account_voltage and electrical["voltage"]!=account_voltage:
        raise ValueError("Electrical replay service classification must match the explicit retail-account voltage; primary/HV cannot use a secondary reference circuit.")
    if numeric_volts and electrical["nominal_voltage_v"]!=numeric_volts:
        raise ValueError("Electrical service nominal volts must match the separately confirmed account service voltage.")
    if a.get("phase") is not None and electrical["phase"]!=a["phase"]:
        raise ValueError("Electrical phase must match the confirmed account phase.")
    equipment={"pv":pv,"battery":battery is not None,"pv_ac_kw":r["pv_capacity_kw"],"battery_kw":battery.max_discharge_kw if battery else 0.,
        "renewable_only_charging":op["renewable_only_charging"],"no_battery_export":op["no_battery_export"]}
    if utility in ("firstenergy_pa_penn_power", "firstenergy_pa_penelec", "firstenergy_pa_met_ed", "rockland_electric_new_jersey", "jcpl_new_jersey", "atlantic_city_electric_new_jersey", "potomac_edison_maryland", "delmarva_maryland", "pepco_maryland", "bge_maryland", "ppl_electric_pennsylvania", "aep_ohio", "peco", "dte_electric", "consumers_energy", "ameren_illinois", "ameren_missouri", "xcel_energy_minnesota", "we_energies_wisconsin", "duke_energy_indiana", "alliant_energy_iowa"):
        equipment["pv_dc_kw"] = r["solar"]["dc_capacity_kw"]
    if utility.startswith("firstenergy_") and (pv or battery) and (op["grid_charging_confirmed"] or op["mode"]!="non_export"):
        raise ValueError("FirstEnergy first renewable scope requires non-export operation and PV-only battery charging.")
    cycles=list(cycle_partitions(grid.index,r["billing_cycles"]))
    for _,block,cycle in cycles:
        module.validate_account(cycle_account(a,cycle),grid.index[block],equipment=equipment)
        if utility in ("firstenergy_pa_met_ed","firstenergy_pa_penelec","firstenergy_pa_penn_power") and a["tariff"]=="GS-S" and float(np.sum(load[block])*.25)>1500.+1e-7:
            raise ValueError(UTILITIES[utility]["label"]+" GS-S initial declared domain separately bounds native cycle energy at1500kWh; PV-reduced imports cannot establish qualification.")
        if utility in ("firstenergy_pa_met_ed","firstenergy_pa_penelec","firstenergy_pa_penn_power") and a["tariff"]=="RS" and float(np.max(load[block]))>25.+1e-7:
            raise ValueError(UTILITIES[utility]["label"]+" RS native15-minute peak exceeds the inactive special-demand envelope; PV-reduced imports cannot erase demand eligibility/history.")
    if utility in ("ameren_missouri", "potomac_edison_maryland", "jcpl_new_jersey", "firstenergy_pa_met_ed", "firstenergy_pa_penelec", "firstenergy_pa_penn_power"):
        _,first_block,first_cycle=cycles[0]
        module.validate_state(cycle_account(a,first_cycle),grid.index[first_block],equipment=equipment)
    alternatives=r.get("tariff_comparisons",[])
    if not isinstance(alternatives,list) or len(alternatives)>1 or any(not isinstance(p,str) for p in alternatives):
        raise ValueError("Choose at most one alternative tariff for an independently optimized comparison.")
    for alternative in alternatives:
        if alternative==a["tariff"] or alternative not in plans or plans[alternative].get("status")!="supported" or plans[alternative].get("customer_class")!=kind:
            raise ValueError("Choose a distinct implemented alternative tariff for the same utility/customer class.")
        if plans[alternative].get("voltage") and plans[alternative]["voltage"]!=electrical["voltage"]:
            raise ValueError("A tariff comparison cannot change the site's confirmed electrical service class.")
        alternative_account={**a,"tariff":alternative}
        _validate_rate_evidence_selection(alternative_account,plans[alternative])
        for _,block,cycle in cycles:
            module.validate_account(cycle_account(alternative_account,cycle),grid.index[block],equipment=equipment)
    return grid,load,cycles,equipment


def validate(r):
    prepare(r)
    return r


def _json_value(value):
    if isinstance(value,dict):return {str(k):_json_value(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [_json_value(v) for v in value]
    if isinstance(value,(date,pd.Timestamp)):return value.isoformat()
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,np.ndarray):return [_json_value(v) for v in value]
    return value


def _execute_single_plan(directory,r):
    from .worker import write_json
    from .table_store import save_table
    from .site_inputs import build_site_generation
    from .electrical_replay import replay_study
    from ..dispatch.regional import optimize_cycle
    from ..billing.regional_counterfactual import grid_only_counterfactual
    directory=Path(directory)
    grid,load,cycles,equipment=prepare(r)
    from .regional_carbon import values as carbon_values
    carbon,carbon_provenance=carbon_values(r,directory,grid.index)
    utility=r["site"]["utility"]
    available=np.zeros(len(grid.index));source_tables={};pv_provenance={"source":"no PV configured"};warnings=[]
    if equipment["pv"]:
        pv,weather,weather_provenance,pv_warnings=build_site_generation(r,directory,grid)
        available=pv.pv_available_kw.to_numpy();source_tables={"weather":weather,"pv-production":pv.diagnostics}
        pv_provenance={"weather":weather_provenance,"pv":pv.provenance};warnings.extend(pv_warnings)
    inputs=pd.DataFrame({"timestamp":grid.index,"native_load_kw":load,"pv_available_kw":available})
    if carbon is not None:
        inputs["carbon_intensity_g_co2e_per_kwh"]=carbon
        warnings.append(carbon_provenance["warning"])
    specs={"grid_only":(False,False)}
    if equipment["pv"]:specs["pv_only"]=(True,False)
    if r["battery"] is not None:specs["pv_battery" if equipment["pv"] else "storage_only"]=(equipment["pv"],True)
    results={};cycle_rows=[];items=[];tables=[];replays={};baseline_semantics=None;assumption_rows=[]
    for name,(has_pv,has_storage) in specs.items():
        state=None;parts=[];bills=[];outcomes=[];current=deepcopy(r["battery"]) if has_storage else None
        for i,block,cycle in cycles:
            write_json(directory/"progress.json",{"message":f"Calculating {name.replace('_',' ')} · billing cycle {i+1}/{len(cycles)}"})
            frame=inputs.iloc[block].copy()
            if not has_pv:frame["pv_available_kw"]=0.
            account=cycle_account(r["account"],cycle)
            if name=="grid_only":
                reference=grid_only_counterfactual(utility,account,state)
                account,state=reference["account"],reference["state"]
                if baseline_semantics is None:
                    baseline_semantics={k:v for k,v in reference.items() if k not in ("account","state","warnings")}
                warnings.extend(reference["warnings"])
            result=optimize_cycle(frame,utility,account,current,state=state,
                wear=r["degradation_cost_per_kWh"],include_wear=r["include_degradation_in_optimization"],
                terminal_energy=r["battery"]["energy_kWh"] if has_storage and i==len(cycles)-1 else None,
                export_enabled=has_pv and r["operating_contract"]["mode"]=="net_metering",
                grid_charging=r["operating_contract"]["grid_charging_confirmed"],
                credit_objective_policy=r["credit_objective_policy"],equipment={**equipment,"pv":has_pv,"battery":has_storage,
                    **({"pv_dc_kw":r["solar"]["dc_capacity_kw"] if has_pv else 0.} if "pv_dc_kw" in equipment else {}),
                    "pv_ac_kw":r["pv_capacity_kw"] if has_pv else 0.,"battery_kw":current["max_discharge_kw"] if current else 0.})
            if carbon is not None:
                result["dispatch"]["carbon_intensity_g_co2e_per_kwh"]=carbon[block]
                result["dispatch"]["grid_import_emissions_kg_co2e"]=(
                    result["dispatch"]["grid_import_kw"].to_numpy()*grid.timestep_hours*carbon[block]/1000)
            state=result["next_state"];parts.append(result["dispatch"]);bills.append(result["bill"]);outcomes.append(result)
            if has_storage:current["energy_kWh"]=result["terminal_energy_kwh"]
            bill=result["bill"]
            warnings.extend(name+": "+text for text in bill.get("warnings",[])+result.get("warnings",[]))
            cycle_rows.append({"scenario":name,"cycle_index":i,**{k:v for k,v in cycle.items() if k!="account_overrides"},
                "total_usd":bill["total_usd"],"unrounded_total_usd":bill["unrounded_total_usd"],
                "is_complete_bill":bill["is_complete_bill"],"objective_scope":bill_scope(bill),
                "rate_evidence_status":bill.get("rate_evidence_status","not_recorded"),
                "assumption_model":bill.get("assumption_model"),
                "rate_assumption_ids":json.dumps([x["id"] for x in bill.get("rate_assumptions",[])]),
                "import_kwh":bill["import_kwh"],"export_kwh":bill["export_kwh"],
                **({"grid_import_emissions_kg_co2e":float(result["dispatch"]["grid_import_emissions_kg_co2e"].sum())} if carbon is not None else {}),
                "optimization_objective_usd":result["objective_usd"],"reconciliation_difference_usd":result["reconciliation_difference_usd"],
                "closing_state":json.dumps(_json_value(state),sort_keys=True),"metrics":json.dumps(_json_value(bill.get("metrics",{})),sort_keys=True)})
            for assumption in bill.get("rate_assumptions",[]):
                assumption_rows.append({"scenario":name,"cycle_index":i,"billing_month":cycle["billing_month"],
                    "assumption_model":bill["assumption_model"],"assumption_id":assumption["id"],
                    **{k:json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in assumption.items() if k!="id"}})
            for key,amount in bill["lines"].items():
                related=[x["id"] for x in bill.get("rate_assumptions",[]) if key in x["components"]]
                items.append({"scenario":name,"cycle_index":i,"billing_month":cycle["billing_month"],"bill_date":cycle["bill_date"],
                    "component":key,"amount_usd":amount,"unrounded_amount_usd":bill["unrounded_lines"][key],
                    "rate_evidence_status":"provisional" if related else "verified" if bill.get("rate_evidence_status") in ("verified","provisional") else "not_recorded",
                    "rate_assumption_ids":json.dumps(related)})
        dispatch=pd.concat(parts,ignore_index=True)
        results[name]={"dispatch":dispatch,"bills":bills,"outcomes":outcomes,"closing_state":state}
        replays[name]=(dispatch,r["battery"] if has_storage else None,r["pv_capacity_kw"] if has_pv else 0.)
    electrical={"customer_class":customer_class(r["site_profile"]),**r["electrical_service"]}
    nominal=electrical["nominal_voltage_v"]
    if electrical["phase"]=="single" and nominal!=240 or electrical["phase"]=="three" and nominal!=480:
        electrical["voltage"]="unsupported_nominal_voltage"
    ac_tables,ac_rows,ac_manifest,ac_warnings=replay_study(replays,electrical,
        timestep_minutes=r["timestep_minutes"],timezone=r["timezone"],
        progress=lambda text:write_json(directory/"progress.json",{"message":text}))
    warnings.extend(ac_warnings)
    ac_by_name={row["scenario"]:row for row in ac_rows}
    base=sum(b["total_usd"] for b in results["grid_only"]["bills"])
    comparisons=[]
    base_emissions=(float(results["grid_only"]["dispatch"]["grid_import_emissions_kg_co2e"].sum()) if carbon is not None else None)
    for name,result in results.items():
        dispatch=result["dispatch"];bills=result["bills"];outcomes=result["outcomes"]
        evidence=_rate_evidence_manifest(r["account"],bills)
        total=sum(b["total_usd"] for b in bills)
        comparisons.append({"scenario":name,"utility_bill_usd":total,"savings_vs_grid_usd":base-total,
            "is_complete_bill":all(b["is_complete_bill"] for b in bills),
            "objective_scope":"provisional_modeled_bill" if any(bill_scope(b)=="provisional_modeled_bill" for b in bills) else "complete_utility_bill" if all(b["is_complete_bill"] for b in bills) else "verified_charges_subtotal",
            "rate_evidence_status":"provisional" if any(b.get("rate_evidence_status")=="provisional" for b in bills) else "verified" if all(b.get("rate_evidence_status")=="verified" for b in bills) else "not_recorded",
            "rate_assumption_ids":json.dumps(evidence["assumption_ids"]),
            "assumption_models":json.dumps(evidence["assumption_models"]),
            "import_kwh":sum(b["import_kwh"] for b in bills),"export_kwh":sum(b["export_kwh"] for b in bills),
            **({"grid_import_emissions_kg_co2e":float(dispatch["grid_import_emissions_kg_co2e"].sum()),
                "emissions_difference_vs_grid_kg_co2e":base_emissions-float(dispatch["grid_import_emissions_kg_co2e"].sum())} if carbon is not None else {}),
            "pv_curtailed_kwh":float(dispatch.pv_curtailed_kw.sum()*grid.timestep_hours),
            "battery_charge_kwh":float(dispatch.battery_charge_kw.sum()*grid.timestep_hours),
            "battery_discharge_kwh":float(dispatch.battery_discharge_kw.sum()*grid.timestep_hours),
            "estimated_battery_wear_usd":sum(o["wear_usd"] for o in outcomes),
            "optimization_objective_usd":sum(o["objective_usd"] for o in outcomes),
            "maximum_reconciliation_difference_usd":max(o["reconciliation_difference_usd"] for o in outcomes),
            "all_cycle_cost_optima_proven":all(o["cost_optimum_proven"] is not False for o in outcomes) if any(o["cost_optimum_proven"] is not None for o in outcomes) else None,
            "all_cycling_refinements_proven":all(o["minimum_cycling_proven"] is not False for o in outcomes) if any(o["minimum_cycling_proven"] is not None for o in outcomes) else None,
            "annual_optimum_proven":False if len(cycles)>1 else None,
            **{k:v for k,v in ac_by_name[name].items() if k!="scenario"}})
    base_lines={(row["cycle_index"],row["component"]):row["amount_usd"] for row in items if row["scenario"]=="grid_only"}
    for row in items:row["savings_vs_grid_usd"]=base_lines.get((row["cycle_index"],row["component"]),0)-row["amount_usd"]
    def save(key,label,frame):
        frame=frame.copy()
        if "timestamp" in frame:frame["timestamp"]=pd.to_datetime(frame["timestamp"],utc=True)
        save_table(directory,key,[c.replace("_"," ") for c in frame],frame)
        tables.append({"id":key,"label":label,"row_count":len(frame)})
    rate_evidence=_rate_evidence_manifest(r["account"],(b for value in results.values() for b in value["bills"]))
    save("comparison",("Provisional historical estimates" if rate_evidence["status"]=="provisional" else "Retail bills")+", operation and electrical comparison",pd.DataFrame(comparisons))
    save("billing-components","Itemized charges and component savings",pd.DataFrame(items))
    save("billing-cycles","Bills and closing state by confirmed cycle",pd.DataFrame(cycle_rows))
    if assumption_rows:save("billing-assumptions","Provisional tariff rates and billing rules",pd.DataFrame(assumption_rows))
    save("inputs","Native demand, available AC PV"+(" and PJM carbon intensity" if carbon is not None else ""),inputs)
    if carbon is not None:
        save("carbon-provenance","PJM carbon source and provider interval provenance",pd.read_csv(directory/"carbon-source.csv"))
    for name,result in results.items():save("dispatch-"+name,"Dispatch · "+name,result["dispatch"])
    for key,label,frame in ac_tables:save(key,label,frame)
    for key,frame in source_tables.items():save(key,key.replace("-"," ").title(),frame)
    warnings.extend(["Historical perfect foresight within each billing cycle. Multiple cycles use rolling optimization, continuous SOC and propagated billing history/credit ledgers; no jointly optimized annual minimum is claimed.",
        "Existing obligations and starting demand history are identical across scenarios; actual endogenous state evolves independently. A net-metered study labels its absent-PV grid-only counterfactual separately and removes NEM enrollment and solar credits from that reference.",
        "Utility charges use scheduled ideal meter flows. OpenDSS PCC measurements and network losses are separate diagnostics and never alter the bill.",
        "Load: "+r["load"]["source"]+". Monthly meter purchases cannot establish native loads or interval behavior.",
        "No capital costs or production incentives are included. Wholesale prices are used only where the retail supply arrangement explicitly requires them.",
        *([] if carbon is not None else [carbon_provenance["warning"]]),
        "Credit objective policy: "+r["credit_objective_policy"]+". Actual carried credits remain in the bill ledger; excluded opening credits do not change dispatch."])
    if r["operating_contract"]["mode"]=="net_metering":
        warnings.append("Closing credits are reported at their filed utility-ledger value. The rolling-cycle optimizer assigns no invented terminal cash value to unused kWh banks; equally priced schedules can curtail different amounts of PV. Minimum cycling does not prove minimum PV curtailment or a jointly optimized annual benefit.")
    write_json(directory/"result.json",_json_value({"schema_version":11,"tables":tables,"warnings":list(dict.fromkeys(warnings)),
        "billing":{k:v["bills"] for k,v in results.items()},"ac_validation":ac_manifest,
        "optimization":{k:{"method":"rolling_cycle_historical_perfect_foresight","annual_optimum_proven":False if len(cycles)>1 else None,
            "cycles":[{field:out[field] for field in ("objective_usd","reconciliation_difference_usd","cost_optimum_proven","refinement_status","minimum_cycling_proven","terminal_energy_kwh","cost_proof_method","primary_lower_bound_usd","primary_optimality_gap_usd","primary_proof_tolerance_usd","cycling_proof_method","cycling_lower_bound_kwh","cycling_optimality_gap_kwh","cycling_proof_tolerance_kwh","relaxation_status","relaxed_lower_bound_usd","strict_fallback_used")} for out in v["outcomes"]]} for k,v in results.items()},
        "grid_only_reference":baseline_semantics,
        "regional_account":r["regional_account"],"account":r["account"],"operating_contract":r["operating_contract"],
        "is_complete_bill":all(row["is_complete_bill"] for row in comparisons),
        "rate_evidence_status":"provisional" if any(row["rate_evidence_status"]=="provisional" for row in comparisons) else comparisons[0]["rate_evidence_status"],
        "rate_evidence":rate_evidence,
        "billing_evidence_note":"Component completeness, historical rate evidence, solver proof and representative electrical feasibility are separate claims. Provisional savings use the recorded assumptions.",
        "input_provenance":{"load":{k:v for k,v in r["load"].items() if k!="csv"},"pv":pv_provenance,"carbon":carbon_provenance,
            "native_csv_sha256":hashlib.sha256(r["load"]["csv"].encode()).hexdigest() if r["load"]["csv"] else None,
            "request_sha256":hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest()},
        "engine_id":json.loads((directory/"engine.json").read_text())["id"]}))
    write_json(directory/"progress.json",{"message":"Retail comparisons, billing ledgers and representative electrical checks saved"})


def execute(directory,r):
    """Compare eligible plans by optimizing each independently, with shared facts."""
    import shutil
    from .worker import write_json
    from .table_store import save_table
    directory=Path(directory)
    prepare(r)
    primary={**r,"tariff_comparisons":[]}
    _execute_single_plan(directory,primary)
    result=json.loads((directory/"result.json").read_text())
    primary_tariff=r["account"]["tariff"]
    for table_id in ("comparison","billing-components","billing-cycles"):
        frame=pd.read_csv(directory/(table_id+".csv"))
        frame.insert(0,"tariff",primary_tariff)
        if table_id=="comparison":frame["tariff_comparison_method"]="independently_optimized_per_tariff"
        save_table(directory,table_id,[c.replace("_"," ") for c in frame],frame)
    for i,tariff in enumerate(r.get("tariff_comparisons",[]),1):
        write_json(directory/"progress.json",{"message":"Independently optimizing alternative tariff "+tariff})
        folder=directory/("alternative-"+str(i));folder.mkdir(exist_ok=True)
        for name in ("engine.json","weather.csv","weather.json"):
            if (directory/name).is_file():shutil.copyfile(directory/name,folder/name)
        if r.get("carbon") is not None:
            for name in ("carbon-source.csv","carbon-source.json"):
                shutil.copyfile(directory/name,folder/name)
            shutil.copytree(directory/"carbon-source",folder/"carbon-source",dirs_exist_ok=True)
        alternative={**primary,"account":{**deepcopy(r["account"]),"tariff":tariff}}
        write_json(folder/"request.json",alternative)
        _execute_single_plan(folder,alternative)
        other=json.loads((folder/"result.json").read_text())
        prefix="alt"+str(i)+"-"
        for table in other["tables"]:
            source_id=table["id"]
            if source_id in ("inputs","weather","pv-production","carbon-provenance"):
                continue  # Shared physical inputs have one authoritative table.
            frame=pd.read_csv(folder/(source_id+".csv"))
            if "scenario" in frame:frame["scenario"]=prefix+frame["scenario"]
            if source_id in ("comparison","billing-components","billing-cycles"):
                frame.insert(0,"tariff",tariff)
                if source_id=="comparison":frame["tariff_comparison_method"]="independently_optimized_per_tariff"
                existing=pd.read_csv(directory/(source_id+".csv"))
                frame=pd.concat([existing,frame],ignore_index=True)
                target_id=source_id
                next(t for t in result["tables"] if t["id"]==source_id)["row_count"]=len(frame)
            else:
                target_id=prefix+source_id
                result["tables"].append({"id":target_id,"label":"Alternative "+tariff+" · "+table["label"],"row_count":len(frame)})
            save_table(directory,target_id,[c.replace("_"," ") for c in frame],frame)
        result["billing"].update({prefix+k:v for k,v in other["billing"].items()})
        result["optimization"].update({prefix+k:{**v,"tariff":tariff} for k,v in other["optimization"].items()})
        for item in other["ac_validation"].get("scenarios",[]):
            item={**item,"scenario":prefix+item["scenario"],**({"interval_table":prefix+item["interval_table"]} if item.get("interval_table") else {})}
            result["ac_validation"]["scenarios"].append(item)
        statuses=[result["ac_validation"].get("all_intervals_feasible"),other["ac_validation"].get("all_intervals_feasible")]
        result["ac_validation"]["all_intervals_feasible"]=False if False in statuses else None if None in statuses else True
        result["is_complete_bill"] &= other["is_complete_bill"]
        if other.get("rate_evidence_status")=="provisional":result["rate_evidence_status"]="provisional"
        result["warnings"].extend("Alternative "+tariff+": "+w for w in other["warnings"])
    result["tariff_comparison"]={"method":"independently_optimized_per_tariff","primary":primary_tariff,
        "alternatives":r.get("tariff_comparisons",[]),"account_history_and_obligations":"same initial facts",
        "same_schedule_repricing":False}
    result["rate_evidence"]=_rate_evidence_manifest(r["account"],(bill for bills in result["billing"].values() for bill in bills))
    result["input_provenance"]["request_sha256"]=hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest()
    write_json(directory/"result.json",result)
    write_json(directory/"progress.json",{"message":"Retail scenario and independently optimized tariff comparisons saved"})
