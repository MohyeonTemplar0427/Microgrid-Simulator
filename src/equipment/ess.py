"""Resolve published AC-system facts into the engine's internal-energy state.

No GUI, network, catalog refresh, or mutations of the published records.
"""
from copy import deepcopy
import hashlib
import json
import math
from .ess_catalog import CATALOG, REVISION
from ..dispatch.battery import Battery

RESOLVER_VERSION = "ac-equivalent-v1"
LIMITATION = "Equipment voltage/phase metadata is retained, but OpenDSS uses the representative balanced 480 V circuit. This is not residential split-phase installation validation. Battery terminal P is replayed at Q=0; physical inverter kVA and site/gateway constraints are not validated."


def search(query="", manufacturer=None):
    return [deepcopy(x) for x in CATALOG if query.casefold() in (x["manufacturer"]+" "+x["model"]).casefold()
            and (manufacturer is None or manufacturer==x["manufacturer"])]


def detail(equipment_id):
    for entry in CATALOG:
        if entry["id"] == equipment_id:
            return deepcopy(entry)
    raise ValueError("Unknown ESS equipment ID.")


def finite(value, name, low=0, high=None):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<low or high is not None and value>high:
        raise ValueError(f"Invalid {name}.")
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()


def resolve(equipment_id, quantity=1, initial_soc=.5, backup_reserve=.2,
            capacity_basis=None, efficiency_approximation=False, overrides=None, *, record=None):
    entry = detail(equipment_id) if record is None else deepcopy(record)
    if entry["id"] != equipment_id:
        raise ValueError("Equipment identity does not match saved record.")
    if type(quantity) is not int or quantity<1:
        raise ValueError("Quantity must be a positive integer of identical complete systems.")
    finite(initial_soc,"initial SOC",0,1); finite(backup_reserve,"backup reserve",0,1)
    if backup_reserve>=1 or initial_soc<backup_reserve:
        raise ValueError("Initial SOC must be at least reserve, and reserve must be below 100%.")
    if type(efficiency_approximation) is not bool:
        raise ValueError("Efficiency approximation must be explicitly accepted.")
    if overrides is not None and not isinstance(overrides, dict):
        raise ValueError("Overrides must be a mapping of power derates.")
    selection=dict(equipment_id=equipment_id,quantity=quantity,initial_soc=initial_soc,
                   backup_reserve=backup_reserve,capacity_basis=capacity_basis,
                   efficiency_approximation=efficiency_approximation,overrides=overrides or {})
    result=dict(resolver_version=RESOLVER_VERSION,catalog_revision=entry["catalog_revision"],
                equipment=entry,selection=selection,ready=False,battery=None,requirements=[],
                assumptions=[LIMITATION,entry["configuration_note"]],provenance={})
    if entry["architecture"]["value"]!="ac_connected":
        result["requirements"]=entry["unresolved"]
        return result
    facts=entry["fields"]
    required=("usable_energy_kwh","charge_kw","discharge_kw","round_trip_efficiency","efficiency_path","max_units")
    missing=[name for name in required if facts.get(name,{}).get("value") is None]
    if missing:
        result["requirements"]=["Unresolved specification: "+name for name in missing]
        return result
    if type(facts["max_units"]["value"]) is not int or facts["max_units"]["value"] < 1:
        raise ValueError("Invalid documented unit limit.")
    if quantity>facts["max_units"]["value"]:
        raise ValueError("Quantity exceeds documented complete-system configuration.")
    if facts["efficiency_path"]["value"]!="ac_battery_ac":
        result["requirements"]=["A compatible AC-to-AC efficiency is required."]
        return result
    basis=facts.get("energy_basis",{}).get("value")
    if basis is None:
        if capacity_basis not in ("ac_deliverable","usable_internal"):
            result["requirements"].append("Choose an explicit usable-energy measurement assumption; the source does not resolve it.")
        else:
            basis=capacity_basis
            result["assumptions"].append("User assumes capacity basis: "+basis+"; not a verified manufacturer measurement boundary.")
    elif capacity_basis is not None and capacity_basis!=basis:
        raise ValueError("A published energy measurement basis cannot be replaced by an incompatible assumption.")
    if not efficiency_approximation:
        result["requirements"].append("Accept equal square-root splitting of AC round-trip efficiency; one-way efficiencies are not published measurements.")
    if result["requirements"]:
        return result
    if basis not in ("ac_deliverable","usable_internal"):
        raise ValueError("Unsupported energy basis.")
    eff=finite(facts["round_trip_efficiency"]["value"],"round-trip efficiency",.000001,1)**.5
    usable=finite(facts["usable_energy_kwh"]["value"],"usable energy",.000001)*quantity
    capacity=usable/eff if basis=="ac_deliverable" else usable
    charge=finite(facts["charge_kw"]["value"],"charge power",.000001)*quantity
    discharge=finite(facts["discharge_kw"]["value"],"discharge power",.000001)*quantity
    battery=dict(capacity_kWh=capacity,energy_kWh=capacity*initial_soc,SOC_min=backup_reserve,SOC_max=1.,
                 max_charge_kw=charge,max_discharge_kw=discharge,charge_efficiency=eff,discharge_efficiency=eff)
    if not isinstance(selection["overrides"],dict) or set(selection["overrides"])-{"max_charge_kw","max_discharge_kw"}:
        raise ValueError("Equipment overrides support only explicit aggregate continuous power derates; use manual mode for other models.")
    for key,value in selection["overrides"].items():
        finite(value,key,.000001,battery[key])
        battery[key]=value
    Battery(**battery)
    result["assumptions"].extend([
        "Equal sqrt(AC round-trip efficiency) split is an approximation, not measured one-way efficiency.",
        "Engine energy is an equivalent internal usable window, not nameplate cell energy. Manufacturer reserves are already excluded; user backup reserve is applied once.",
        "Constant beginning-of-life efficiency/energy are extrapolated from source test conditions; no temperature/power derating, standby consumption or degradation curve is inferred."])
    for key,value in battery.items():
        source_keys={"max_charge_kw":["charge_kw"],"max_discharge_kw":["discharge_kw"]}.get(key,["usable_energy_kwh","energy_basis","round_trip_efficiency"])
        result["provenance"][key]=dict(value=value,status="user_overridden" if key in selection["overrides"] else "assumed" if "efficiency" in key else "derived",
                                      sources=[facts[k] for k in source_keys],resolver_version=RESOLVER_VERSION)
    for key in ("energy_kWh","SOC_min"):
        result["provenance"][key]["user_input"]=initial_soc if key=="energy_kWh" else backup_reserve
    result.update(ready=True,battery=battery,usable_ac_energy_kwh=capacity*eff,
                  dispatchable_ac_energy_kwh=capacity*(1-backup_reserve)*eff)
    result["sha256"]=digest(result)
    return result


def validate_resolution(saved):
    if not isinstance(saved,dict) or saved.get("resolver_version")!=RESOLVER_VERSION or not saved.get("ready"):
        raise ValueError("Review and resolve the ESS selection before submitting.")
    try:
        expected=resolve(**saved["selection"],record=saved["equipment"])
    except (KeyError,TypeError) as exc:
        raise ValueError("Malformed saved equipment resolution.") from exc
    if expected!=saved:
        raise ValueError("Saved ESS parameters/provenance changed. Resolve the selection again.")
    return saved
