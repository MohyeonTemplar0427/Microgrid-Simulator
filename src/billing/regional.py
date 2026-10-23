"""Jurisdiction-specific retail adapters behind one cycle/reconciliation contract.

Regional market data and electrical circuits are deliberately absent here.
Existing schema-8 Dominion and other utilities keep their original interfaces.
"""
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
from importlib import import_module

import numpy as np
import pandas as pd

from .regional_math import BillingMath


UTILITIES = {
    "xcel_energy_minnesota": {"label":"Xcel Energy · Minnesota (NSP)", "state":"MN", "zone":None, "module":"xcel_mn", "timezone":"America/Chicago",
                            "grid_operator":"MISO", "resource_adequacy_zone":"LRZ1", "transmission_owner":"Northern States Power Company",
                            "grid_sources":["https://cdn.misoenergy.org/2023%20Regional%20Resource%20Assessment%20Report630736.pdf",
                                            "https://transmissionprod2.xcelenergy.com/Planning/Planning-for-the-Northern-States-Power-Company",
                                            "https://docs.misoenergy.org/miso12-legalcontent/Schedule_09_-_Network_Integration_Transmission_Service.pdf"]},
    "ameren_missouri": {"label":"Ameren Missouri", "state":"MO", "zone":None, "module":"ameren_mo", "timezone":"America/Chicago",
                       "grid_operator":"MISO", "resource_adequacy_zone":"LRZ5", "transmission_owner":"Ameren Missouri",
                       "grid_sources":["https://www.ameren.com/-/media/files/our-company/reliability/capacity-rfp/amo-bid-input-form-py2028-2029.ashx",
                                       "https://docs.misoenergy.org/miso12-legalcontent/Schedule_09_-_Network_Integration_Transmission_Service.pdf"]},
    "dominion_energy_virginia": {"label":"Dominion Energy Virginia", "state":"VA", "zone":"DOM", "module":"dominion_va_general"},
    "dominion_energy_north_carolina": {"label":"Dominion Energy North Carolina", "state":"NC", "zone":"DOM", "module":"dominion_nc"},
    "pseg": {"label":"PSE&G", "state":"NJ", "zone":"PSEG", "module":"pseg"},
    "firstenergy_pa_west_penn": {"label":"FirstEnergy Pennsylvania · West Penn district", "state":"PA", "zone":"APS", "module":"firstenergy_pa"},
    "firstenergy_ohio_edison": {"label":"FirstEnergy Ohio · Ohio Edison", "state":"OH", "zone":"ATSI", "module":"firstenergy_oh"},
    "peco": {"label":"PECO · southeastern Pennsylvania", "state":"PA", "zone":"PECO", "module":"peco"},
    "dte_electric": {"label":"DTE Electric · Michigan", "state":"MI", "zone":None, "module":"dte",
                     "grid_operator":"MISO", "resource_adequacy_zone":"LRZ7", "transmission_owner":"ITC Transmission",
                     "grid_sources":["https://cdn.misoenergy.org/2023%20Regional%20Resource%20Assessment%20Report630736.pdf",
                                     "https://www.michigan.gov/mpsc/consumer/electricity/electric-utility-service-area-map"]},
    "consumers_energy": {"label":"Consumers Energy · Michigan", "state":"MI", "zone":None, "module":"consumers",
                         "grid_operator":"MISO", "resource_adequacy_zone":"LRZ7", "transmission_owner":"Michigan Electric Transmission Company (METC)",
                         "grid_sources":["https://www.consumersenergy.com/about-us/electric-generation",
                                         "https://www.sec.gov/Archives/edgar/data/1317630/000131763026000006/itc-20251231.htm",
                                         "https://cdn.misoenergy.org/2023%20Regional%20Resource%20Assessment%20Report630736.pdf",
                                         "https://www.michigan.gov/mpsc/consumer/electricity/electric-utility-service-area-map"]},
    "ameren_illinois": {"label":"Ameren Illinois", "state":"IL", "zone":None, "module":"ameren_il", "timezone":"America/Chicago",
                        "grid_operator":"MISO", "resource_adequacy_zone":"LRZ4", "transmission_owner":"Ameren Illinois",
                        "grid_sources":["https://www.icc.illinois.gov/docket/P2024-0088/documents/361990/files/633929.pdf",
                                        "https://www.ilga.gov/reports/ReportsSubmitted/159RSGAEmail340RSGAAttachICC%20MISO%20Zone%204%20Report%2012-17-2018.pdf"]},
}


def adapter(utility):
    if utility not in UTILITIES:
        raise ValueError("Choose a supported distribution utility and its separate state jurisdiction.")
    return import_module("src.billing."+UTILITIES[utility]["module"])


def catalog():
    return {key: {"id":key, **{k:v for k,v in data.items() if k!="module"},
                  "plans":adapter(key).catalog()} for key,data in UTILITIES.items()}


def account_region(region, utility):
    """No coordinate, state or node can establish retail service eligibility."""
    data=UTILITIES.get(utility)
    if not data or not isinstance(region,dict):
        raise ValueError("Supply explicit distribution utility, jurisdiction and retail supply facts.")
    expected={"distribution_utility":utility,"state_jurisdiction":data["state"],
              "grid_operator":data.get("grid_operator","PJM"),"transmission_zone":data["zone"]}
    if data.get("grid_operator")=="MISO":
        expected.update(resource_adequacy_zone=data["resource_adequacy_zone"],transmission_owner=data["transmission_owner"])
    fields=set(expected)|{"retail_supplier","verification_kind","reference","wholesale_pricing_location"}
    if set(region)!=fields or any(region[k]!=v for k,v in expected.items()):
        raise ValueError("Distribution utility, state jurisdiction and regional grid configuration must be independently consistent; no node-based territory assignment.")
    if (region["verification_kind"] not in ("electricity_bill","utility_confirmation","hypothetical_case")
            or not isinstance(region["reference"],str) or not 1<=len(region["reference"].strip())<=500):
        raise ValueError("Document utility confirmation or explicitly identify a hypothetical account; omit personal identifiers.")
    if not isinstance(region["retail_supplier"],str) or not region["retail_supplier"].strip():
        raise ValueError("Identify the retail supplier separately from distribution utility.")
    location=region["wholesale_pricing_location"]
    if location is not None:
        if data.get("grid_operator")=="MISO":
            if (not isinstance(location,dict) or set(location)!={"cpnode","node_type","source"}
                    or any(not isinstance(v,str) or not 1<=len(v.strip())<=500 for v in location.values())
                    or location["cpnode"].strip().upper()==data["resource_adequacy_zone"]):
                raise ValueError("MISO pricing identity needs an explicitly verified cpnode, node_type and source; a resource-adequacy zone is not a price node and no hub is substituted.")
            return region
        if (not isinstance(location,dict) or set(location)!={"pnode_id","pnode_name","zone","source"}
                or not str(location["pnode_id"]).isdigit()
                or not isinstance(location["zone"],str)
                or any(not isinstance(location[k],str) or not location[k].strip() for k in ("pnode_name","source"))):
            raise ValueError("A wholesale location requires its verified ID, name, native zone and source; no default hub.")
    return region


def cycle_partitions(index, cycles):
    """Complete consecutive actual or explicitly hypothetical utility cycles."""
    index=pd.DatetimeIndex(index)
    if index.tz is None or not isinstance(cycles,list) or not 1<=len(cycles)<=13:
        raise ValueError("Supply one to thirteen complete, consecutive, documented billing cycles.")
    cursor=0
    for i,cycle in enumerate(cycles):
        if (not isinstance(cycle,dict) or set(cycle)!={"start_date","end_date","billing_month","bill_date","kind","source","account_overrides"}
                or cycle["kind"] not in ("regular","initial","final","hypothetical_calendar")
                or not isinstance(cycle["source"],str) or not 1<=len(cycle["source"].strip())<=500
                or not isinstance(cycle["account_overrides"],dict)):
            raise ValueError("Every billing cycle needs service dates, designated billing month, bill date, kind, source and explicit account overrides.")
        try:
            start=pd.Timestamp(cycle["start_date"]).tz_localize(index.tz)
            stop=pd.Timestamp(cycle["end_date"]).tz_localize(index.tz)+pd.DateOffset(days=1)
            month=pd.Timestamp(cycle["billing_month"])
            bill_date=pd.Timestamp(cycle["bill_date"])
        except (TypeError,ValueError) as exc:
            raise ValueError("Billing cycle dates must be ISO local dates; billing month is its first day.") from exc
        if (any(len(cycle[k])!=10 for k in ("start_date","end_date","billing_month","bill_date"))
                or month.day!=1 or not 0<(stop.date()-start.date()).days<=45
                or bill_date.date()< (stop-pd.DateOffset(days=1)).date()):
            raise ValueError("Supply whole service dates, a first-of-month designation and a bill date on/after the final service day.")
        selected=np.flatnonzero((index>=start)&(index<stop))
        if (not len(selected) or selected[0]!=cursor or index[selected[0]]!=start
                or index[selected[-1]]+pd.Timedelta(index[1]-index[0])!=stop):
            raise ValueError("Billing cycles must cover every study interval exactly, without gaps, overlaps or truncated meter cycles.")
        if {"tariff","supply","rate_evidence_mode","provisional_assumptions_accepted"}&set(cycle["account_overrides"]):
            raise ValueError("Tariff/supplier changes require independently configured studies; cycle overrides cannot change enrollment.")
        cursor=int(selected[-1])+1
        yield i,slice(int(selected[0]),cursor),cycle
    if cursor!=len(index):
        raise ValueError("Billing cycles leave uncovered study intervals.")


def cycle_account(account, cycle):
    return {**deepcopy(account),**deepcopy(cycle["account_overrides"]),
            "billing_month":int(cycle["billing_month"][5:7]) if type(account.get("billing_month")) is int else cycle["billing_month"],"bill_date":cycle["bill_date"],
            "cycle_source":cycle["source"],
            "cycle_kind":"regular" if cycle["kind"]=="hypothetical_calendar" else cycle["kind"]}


def calculate_cycle(utility,index,imports,exports,account,*,state=None,equipment=None):
    module=adapter(utility)
    module.validate_account(account,index,equipment=equipment)
    if hasattr(module,"validate_state"):
        module.validate_state(account,index,state=state,equipment=equipment)
    imports,exports=(np.asarray(v,dtype=float) for v in (imports,exports))
    if any(v.shape!=(len(index),) or not np.isfinite(v).all() or (v < -1e-5).any() for v in (imports,exports)):
        raise ValueError("Retail meter flows must be finite nonnegative kW matching every cycle interval.")
    result=module.charge_lines(index,np.maximum(imports,0),np.maximum(exports,0),account,
                               math=BillingMath(index),state=deepcopy(state))
    lines={key:float(value) for key,value in result["lines"].items()}
    if not all(np.isfinite(value) for value in lines.values()):
        raise ValueError("A tariff returned a nonfinite charge; refusing an incomplete arithmetic result.")
    rounded={key:float(Decimal(str(value)).quantize(Decimal(".01"),rounding=ROUND_HALF_UP)) for key,value in lines.items()}
    result={**result,"lines":rounded,"unrounded_lines":lines,
            "total_usd":float(sum(Decimal(str(v)) for v in rounded.values())),
            "unrounded_total_usd":sum(lines.values()),"import_kwh":float(imports.sum()*BillingMath(index).hours),
            "export_kwh":float(exports.sum()*BillingMath(index).hours),"rounding_bound_usd":len(lines)*.005+1e-7,
            "rounding_policy":"Study component half-up cents; unrounded filed arithmetic also retained"}
    return result


def bill_scope(bill):
    """Component completeness and historical evidence are separate claims."""
    if bill.get("rate_evidence_status")=="provisional":
        return "provisional_modeled_bill"
    return "complete_utility_bill" if bill["is_complete_bill"] else "verified_charges_subtotal"
