"""North Carolina's separate Dominion bundled retail schedules.

Filed rates are dollars/kWh, dollars/kW and dollars/billing month. Virginia
rates, PJM LMP and renewable production incentives never enter this adapter.
The source manifest documents independent component dates and research gaps.
"""
from copy import deepcopy
from datetime import date, timedelta
from functools import lru_cache
import math as _math

import numpy as np
import pandas as pd
from dateutil.easter import easter

BASE_URL = "https://www.dominionenergy.com/-/media/content/rates-and-tariffs/pdfs/north-carolina/"
SOURCES = [BASE_URL + "shared/entire-filing.pdf",
           "https://starw1.ncuc.gov/NCUC/ViewFile.aspx?Id=9e03cc94-bc99-4055-a626-cfb06fe391fb",
           "https://starw1.ncuc.gov/NCUC/ViewFile.aspx?Id=6ba227d9-759c-4661-ae2e-596c61a4d09f",
           "https://starw1.ncuc.gov/NCUC/ViewFile.aspx?Id=844198fa-587a-4065-962d-13c1e11a4619",
           "https://starw1.ncuc.gov/NCUC/ViewFile.aspx?Id=cf8c6ee2-cabb-4c1d-83e6-e452e4097fef",
           "https://starw1.ncuc.gov/NCUC/ViewFile.aspx?Id=35396898-2b4a-4686-8ec3-83fd440c9171",
           "https://starw1.ncuc.gov/NCUC/ViewFile.aspx?Id=cb736c4b-e606-4437-ab43-286cf94e7806",
           "https://starw1.ncuc.gov/NCUC/ViewFile.aspx?Id=735b55ff-a92c-401c-8549-dac6dbcd64a7",
           "https://starw1.ncuc.gov/NCUC/ViewFile.aspx?Id=1ba2b1a0-08cf-458d-9753-1638eeca616f",
           "https://starw1.ncuc.gov/NCUC/ViewFile.aspx?Id=5cc97da4-1391-4c41-a9ea-30f7a3392409",
           "https://starw1.ncuc.gov/NCUC/ViewFile.aspx?Id=135e3bd0-fd48-46f4-af08-9ed398017c8d",
           "https://starw1.ncuc.gov/NCUC/ViewFile.aspx?Id=2e772c3e-09b1-40d3-ad93-4b3b7ef14fbb",
           "https://www.dominionenergy.com/-/media/content/paying-my-bill/understand-my-bill/files/bill-calculator-worksheet-nc.xlsx",
           "https://www.ncdor.gov/taxes-forms/sales-and-use-tax/taxable-items/electricity"]

# Base rate sheets filed January 17, 2025, E-22 Sub 694. The temporary
# November 2024 filing has the same rates, but different applicability text.
BASE = {
    "1": {"customer": 14.40, "summer_energy": .121533, "winter_energy": .105123},
    "1P": {"customer": 14.40, "summer_demand": 11.084, "winter_demand": 6.490,
           "on_energy": .077548, "off_energy": .053685},
    "1T": {"customer": 14.40, "summer_on": .269467, "summer_off": .062731,
           "winter_on": .223556, "winter_off": .057137},
    "5": {"customer": 22.97, "demand": 4.110,
          "summer_energy": (.110172, .109334, .084338),
          "winter_energy": (.101258, .100431, .075615),
          "summer_minimum": 6.782, "winter_minimum": 2.791},
    "5P": {"customer_single_200a": 27.00, "customer_other": 96.93,
           "summer_demand": 11.761, "winter_demand": 8.708, "distribution": 2.260,
           "on_energy": .064306, "off_energy": .046025},
    "6P": {"customer": 106.01, "demand": 15.954, "primary": 1.154,
           "secondary": 1.723, "reactive": .211,
           "on_energy": .045753, "off_energy": .038436},
    "6L": {"customer": 106.01, "demand": 21.708, "primary": 1.124,
           "secondary": 1.686, "on_energy": .028606, "off_energy": .026774},
}

# Independently effective components. January2025 is the filed temporary base
# rate, 2024 riders and three-month A1 decrement, rather than a backfilled
# February2025 composite. The base schedule prices match in these two filings;
# their separate applicability and document identities are retained in evidence.
_COVERAGE = [("2025-01-01", "2026-01-31"), ("2026-02-01", "2026-07-31"),
             ("2026-08-01", "2026-10-15")]
_RIDER_TABLES = {
    "2025-01": {
        "residential": {"A": 0., "A1": -.007298, "B": .001854, "B1": .006297, "C": .001029, "CCR": 0., "CE": .000288, "RP": .55, "RPE": .02},
        "sgs": {"A": 0., "A1": -.007291, "B": .001853, "B1": .006108, "C": .001536, "CCR": 0., "CE": .000251, "RP": 3.07, "RPE": .11},
        "lgs": {"A": 0., "A1": -.007258, "B": .001839, "B1": .006295, "C": .001389, "CCR": 0., "CE": .000227, "RP": 3.07, "RPE": .11},
    },
    "2025": {
        "residential": {"A": 0., "A1": 0., "B": -.007362, "B1": 0., "C": .001520, "CCR": .001690, "CE": .000063, "RP": .87, "RPE": .70},
        "sgs": {"A": 0., "A1": 0., "B": -.007355, "B1": 0., "C": .001559, "CCR": .001689, "CE": .000096, "RP": 4.82, "RPE": 3.90},
        "lgs": {"A": 0., "A1": 0., "B": -.007322, "B1": 0., "C": .001217, "CCR": .001681, "CE": .000075, "RP": 4.82, "RPE": 3.90},
    },
    "2026": {
        "residential": {"A": .005198, "A1": 0., "B": .001023, "B1": .005602, "C": .001394, "CCR": .001027, "CE": .000133, "RP": .84, "RPE": -.26},
        "sgs": {"A": .003000, "A1": 0., "B": .000481, "B1": .005593, "C": .000618, "CCR": .001026, "CE": .000142, "RP": 4.70, "RPE": -1.49},
        "lgs": {"A": .001750, "A1": 0., "B": .001432, "B1": .005578, "C": .000648, "CCR": .001023, "CE": .000149, "RP": 4.70, "RPE": -1.49},
    },
}

_UNSUPPORTED = {
    "1DF": ("residential", "Closed dual-fuel companion meter; grandfathered controlled heat-pump installation and companion-meter usage required."),
    "1E": ("residential", "500-account experimental critical-peak plan; utility event notifications and enrollment evidence are not available."),
    "1W": ("residential", "Separate controlled-storage heating meter; requires companion-meter topology and enforced equipment operating schedule."),
    "SGS-EV": ("commercial", "Experimental third-party EV charging service; enrollment, dedicated charger meter and approved demand-discount history required."),
    "5C": ("commercial", "Seasonal cotton-gin service requires documented agricultural operating season and eligible equipment."),
    "6C": ("commercial", "Curtailable service requires utility curtailment events, notification records, customer baseline and noncompliance settlement."),
    "6VP": ("commercial", "Variable pricing requires utility-issued hourly supply prices, contract and billing history; PJM hub LMP is not that retail price."),
    "10": ("commercial", "Requires actual utility A/B/C day classifications (announced by 18:00 preceding day), contract and demand history; no default classification is invented."),
    "LGS-RTP": ("commercial", "Requires complete utility hourly pricing, contracted customer baseline and capacity obligation; no PJM hub substitution."),
    "7": ("commercial", "Closed electric-heating companion schedule requires grandfathered meter and equipment evidence."),
    "NS": ("commercial", "Negotiated special-rate contract requires complete individual contract terms."),
    "SG": ("commercial", "Closed standby-generator experimental program requires enrollment and utility dispatch-event data."),
    "19-FP": ("commercial", "Qualifying-facility production-purchase agreement is separate from retail net metering and requires its own executed contract."),
    "19-LMP": ("commercial", "Qualifying-facility LMP purchase contract requires identified settlement location, loss/imbalance terms and applicable dated agreement."),
    "26": ("commercial", "Outdoor-lighting equipment schedule; requires fixture inventory and ownership rather than native building demand."),
    "30": ("commercial", "County/municipal/housing-authority special class; ordinary private commercial eligibility does not establish access."),
    "30T": ("commercial", "Separate public traffic-control meter and qualifying public authority required."),
    "42": ("commercial", "Public-authority all-electric building special class requires documented ownership and eligible heating equipment."),
}


def defaults(plan_id=None):
    plan_id = plan_id or "1T"
    if plan_id not in BASE:
        raise ValueError("Select an implemented Dominion North Carolina ordinary schedule.")
    residential = plan_id.startswith("1")
    peak = 4000. if plan_id == "6L" else 750. if plan_id == "6P" else 100.
    return {"tariff": plan_id, "customer_class": "residential" if residential else "commercial",
            "supplier": "bundled", "billing_month": 8, "billing_cycle_confirmed": True,
            "eligibility_confirmed": True, "voltage_v": 240 if residential else 480,
            "phase": "single" if residential else "three", "service_amperes": 200 if residential else 400,
            "contract_demand_kw": 0. if residential or plan_id == "5" else peak,
            "contract_minimum_usd": 0., "power_factor": 1., "reactive_demand_kvar": 0.,
            "conservation_discount": False, "ceps_exempt": False,
            "parallel_operation_approved": True, "solar_program": "non_export",
            "parallel_service_contract": plan_id in ("5P", "6P", "6L"),
            "tou_enrollment_confirmed": True, "prior_large_service_confirmed": plan_id == "6L",
            "entry_qualifying_peaks_kw": [peak]*12 if plan_id == "6L" else [],
            "demand_meter": not residential, "history_peaks_kw": [peak]*11,
            "history_on_peak_kw": [peak]*11,
            "history_kwh": [1000. if residential else peak*200]*11,
            "history_billing_months": [9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7],
            "opening_credit_kwh": {"on_peak": 0., "off_peak": 0.},
            "net_metering_confirmed": False, "recs_assignment_confirmed": False,
            "metering_side": "delivery", "rate_change_method": "calendar_day_weighted",
            "fixed_rider_allocation_confirmed": False, "fixed_rider_allocation_reference": ""}


def catalog():
    names = {"1": "Basic Residential", "1P": "Residential TOU with demand", "1T": "Residential Energy TOU",
             "5": "Small General Service — energy blocks and minimum demand bill",
             "5P": "Small General Service TOU — below 500 kW", "6P": "Large General Service TOU — 500 kW and above",
             "6L": "Large General Service — existing eligible 3 MW service"}
    fields = [{"name": k, "label": k.replace("_", " ").capitalize(), "required": True}
              for k in defaults()]
    rows = [{"id": key, "label": "Schedule " + key + " · " + label,
             "customer_class": "residential" if key.startswith("1") else "commercial",
             "status": "supported", "reason": "Bundled ordinary service only; reactive-demand and special-account restrictions are validated.",
             "coverage": [{"start": a, "end": b} for a, b in _COVERAGE],
             "verified_start": _COVERAGE[0][0], "verified_end": _COVERAGE[-1][1],
             "representative_peak_kw": 4000. if key == "6L" else 750. if key == "6P" else 40. if key in ("5", "5P") else 3.,
             "supply_arrangements": ["bundled"], "sources": SOURCES, "account_fields": fields,
             "billing": True, "dispatch": True, "net_metering": key != "5",
             "solar_modes": ["non_export", "net_metering"] if key != "5" else [],
             "equipment_modes": ["grid_only"] if key == "5" else ["grid_only", "pv_only", "pv_battery", "storage_only"]}
            for key, label in names.items()]
    rows += [{"id": key, "label": "Schedule " + key, "customer_class": kind, "status": "unsupported",
              "reason": reason, "coverage": [], "sources": SOURCES, "billing": False, "dispatch": False}
             for key, (kind, reason) in _UNSUPPORTED.items()]
    return rows


@lru_cache(maxsize=40)
def holidays(year):
    """Filed NC list, with no invented Friday/Monday substitutions.

    Only Memorial Day is explicitly labelled '(observed)' in these sheets.
    Independence Day on a weekend does not create a Friday/Monday holiday.
    """
    last_may = date(year, 5, 31)
    memorial = last_may-timedelta(days=last_may.weekday())
    sept = date(year, 9, 1)
    labor = sept+timedelta(days=(-sept.weekday()) % 7)
    nov = date(year, 11, 1)
    thanksgiving = nov+timedelta(days=(3-nov.weekday()) % 7+21)
    return frozenset((date(year, 1, 1), easter(year)-timedelta(days=2), memorial,
                      date(year, 7, 4), labor, thanksgiving, thanksgiving+timedelta(days=1),
                      date(year, 12, 24), date(year, 12, 25)))


def on_peak(index, plan_id, *, demand=False):
    index = pd.DatetimeIndex(index)
    minute = index.hour*60+index.minute
    summer = (index.month >= 6) & (index.month <= 9)
    if plan_id == "6L":
        return np.where(summer, (minute >= 600) & (minute < 1320), (minute >= 420) & (minute < 1320))
    working = (index.dayofweek < 5) & np.array([x.date() not in holidays(x.year) for x in index])
    if plan_id in ("1P", "1T"):
        clock = np.where(summer, (minute >= 780) & (minute < 1260),
                         ((minute >= 390) & (minute < 720)) | ((minute >= 1020) & (minute < 1260)))
    else:
        winter = (((minute >= 360) & (minute < 720)) | ((minute >= 1020) & (minute < 1320))) if demand else ((minute >= 360) & (minute < 1320))
        clock = np.where(summer, (minute >= 600) & (minute < 1320), winter)
    return np.asarray(working & clock)


def _index(index):
    index = pd.DatetimeIndex(index)
    if index.empty or index.tz is None or str(index.tz) != "America/New_York":
        raise ValueError("North Carolina billing requires America/New_York interval-start timestamps.")
    if len(index) < 2 or not index.is_unique or not index.is_monotonic_increasing:
        raise ValueError("Supply complete ordered 15- or 30-minute interval averages.")
    dt = int(index.asi8[1]-index.asi8[0])
    if dt not in (pd.Timedelta(minutes=15).value, pd.Timedelta(minutes=30).value) or not (np.diff(index.asi8) == dt).all():
        raise ValueError("North Carolina 30-minute demand cannot be inferred from missing or hourly data.")
    if index[0] != index[0].normalize() or index[-1]+pd.Timedelta(dt, unit="ns") != index[-1].normalize()+pd.DateOffset(days=1):
        raise ValueError("Supply complete service dates of a confirmed billing cycle.")
    days = len(index.normalize().unique())
    if not 1 <= days <= 40:
        raise ValueError("Current NC adapter supports one confirmed monthly cycle of 1–40 service days; bimonthly service is separate.")
    for day in index.normalize().unique():
        if not any(date.fromisoformat(a) <= day.date() <= date.fromisoformat(b) for a, b in _COVERAGE):
            raise ValueError(f"Dominion North Carolina composite rates are not verified on {day.date()}; no current-rate substitution.")
    return index, days


def _finite(value, name, minimum=0.):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not _math.isfinite(value) or value < minimum:
        raise ValueError(name + " must be a finite number within the supported range.")


def validate_account(account, index, equipment=None):
    index, _ = _index(index)
    if not isinstance(account, dict) or account.get("tariff") not in BASE:
        raise ValueError("Select an implemented Dominion North Carolina tariff.")
    a = account
    required = set(defaults(a["tariff"]))
    if not required <= set(a):
        raise ValueError("Supply required NC account facts: " + ", ".join(sorted(required-set(a))))
    plan = a["tariff"]
    kind = "residential" if plan.startswith("1") else "commercial"
    if a["customer_class"] != kind or a["supplier"] != "bundled":
        raise ValueError("North Carolina requires the applicable Dominion bundled residential/commercial service; third-party retail supply is unavailable.")
    if a["eligibility_confirmed"] is not True or a["billing_cycle_confirmed"] is not True:
        raise ValueError("Confirm utility/tariff eligibility and the complete meter cycle; a location does not establish eligibility.")
    for flag in ("conservation_discount", "ceps_exempt", "parallel_operation_approved", "parallel_service_contract", "tou_enrollment_confirmed", "prior_large_service_confirmed", "demand_meter", "net_metering_confirmed", "recs_assignment_confirmed", "fixed_rider_allocation_confirmed"):
        if type(a[flag]) is not bool:
            raise ValueError(flag+" must be an explicit account confirmation.")
    if type(a["billing_month"]) is not int or not 1 <= a["billing_month"] <= 12:
        raise ValueError("Supply the utility-designated billing month independently of service dates.")
    if a["phase"] not in ("single", "three") or a["metering_side"] != "delivery":
        raise ValueError("Supply service phase and delivery-side metering. Transformer-side metering needs its documented 2% energy treatment.")
    for key in ("voltage_v", "service_amperes", "contract_demand_kw", "contract_minimum_usd", "reactive_demand_kvar"):
        _finite(a[key], key)
    if a["voltage_v"] < 100 or a["service_amperes"] <= 0:
        raise ValueError("Identify actual/hypothetical service voltage and rating.")
    _finite(a["power_factor"], "power_factor", .85)
    if a["power_factor"] > 1:
        raise ValueError("Power factor cannot exceed one.")
    if a["power_factor"] != 1 or a["reactive_demand_kvar"] != 0:
        raise ValueError("This NC dispatch adapter currently requires explicit unity-PF/zero-reactive-load assumptions; actual nonzero reactive demand needs interval kVA/kvar billing and inverter-Q control.")
    if a["rate_change_method"] != "calendar_day_weighted":
        raise ValueError("Use the documented calendar-day weighted rate-change allocation; no interval-usage allocation is silently substituted.")
    if not isinstance(a["fixed_rider_allocation_reference"], str) or (a["fixed_rider_allocation_confirmed"] and not a["fixed_rider_allocation_reference"].strip()):
        raise ValueError("A confirmed fixed-rider change allocation needs bill/utility evidence.")
    if plan in ("1P", "1T") and a["tou_enrollment_confirmed"] is not True:
        raise ValueError("Confirm residential TOU enrollment and the one-year re-enrollment restriction.")
    if a["conservation_discount"] and kind != "residential":
        raise ValueError("The closed 5% conservation discount is a residential grandfathered account condition.")
    if kind == "residential" and (a["contract_minimum_usd"] != 0 or a["contract_demand_kw"] != 0):
        raise ValueError("The implemented ordinary residential schedules do not include a commercial contract-demand/minimum obligation.")
    for key in ("history_peaks_kw", "history_on_peak_kw", "history_kwh", "history_billing_months"):
        if not isinstance(a[key], list) or len(a[key]) != 11:
            raise ValueError("Supply eleven ordered prior meter-cycle peaks, kWh and billing months; no history is guessed.")
    for value in a["history_peaks_kw"]+a["history_on_peak_kw"]+a["history_kwh"]:
        _finite(value, "history")
    if any(on > overall for on, overall in zip(a["history_on_peak_kw"], a["history_peaks_kw"])):
        raise ValueError("An historical on-peak maximum cannot exceed its same-cycle all-hours maximum.")
    if any(type(m) is not int or not 1 <= m <= 12 for m in a["history_billing_months"]):
        raise ValueError("Historical summer ratchets require utility billing-month labels.")
    if plan == "5P" and max(a["history_peaks_kw"]) >= 500:
        raise ValueError("Schedule 5P is unavailable for twelve succeeding cycles after measured demand reaches 500 kW.")
    if plan == "6P" and max(a["history_peaks_kw"]) < 500:
        raise ValueError("Schedule 6P requires a documented existing account ineligible for 5P; supply the qualifying >=500 kW history or a separately modeled new-service determination.")
    if plan == "6L":
        entry = a["entry_qualifying_peaks_kw"]
        if not isinstance(entry, list) or len(entry) != 12:
            raise ValueError("Schedule 6L needs the twelve measured peaks immediately before enrollment, separate from evolving ratchet history.")
        for value in entry:
            _finite(value, "entry_qualifying_peaks_kw")
        if a["prior_large_service_confirmed"] is not True or a["contract_demand_kw"] < 3000 or sum(x >= 3000 for x in entry) < 3:
            raise ValueError("Schedule 6L requires prior 6C/6P/10/6VP service, three qualifying 3 MW entry cycles and a >=3 MW contract.")
        if a["contract_demand_kw"] < max(a["history_peaks_kw"]):
            raise ValueError("An existing 6L contract must include any previously exceeded distribution-contract peak.")
    if not isinstance(a["opening_credit_kwh"], dict) or set(a["opening_credit_kwh"]) != {"on_peak", "off_peak"}:
        raise ValueError("Keep on/off-peak kWh credits separately; no dollar-bank conversion.")
    for value in a["opening_credit_kwh"].values():
        _finite(value, "opening_credit_kwh")
    if a["solar_program"] not in ("non_export", "net_metering"):
        raise ValueError("Choose verified net metering or approved non-export curtailment.")
    if a["solar_program"] == "net_metering":
        if plan == "5":
            raise ValueError("Schedule 5 generally prohibits parallel generation; its <=20 kW Solar+Schools exception is a separate arrangement. Select applicable 5P.")
        if not a["net_metering_confirmed"] or not a["parallel_operation_approved"]:
            raise ValueError("Confirm renewable net-metering enrollment/interconnection and the one-year agreement.")
        if plan not in ("1P", "5P", "6P") and not a["recs_assignment_confirmed"]:
            raise ValueError("This schedule requires renewable certificates assigned to Dominion under NC T&C XXV.E; production incentives are not bill savings.")
    elif any(a["opening_credit_kwh"].values()):
        raise ValueError("A non-export account cannot carry net-metering credits.")
    if equipment:
        has_der = equipment.get("pv", False) or equipment.get("battery", False)
        if has_der and not a["parallel_operation_approved"]:
            raise ValueError("Parallel operation requires utility approval or a clearly labeled hypothetical approval assumption.")
        if has_der and plan == "5":
            raise ValueError("Ordinary Schedule 5 does not authorize general parallel PV/storage; use eligible 5P or the documented special Solar+Schools arrangement.")
        if a["solar_program"] == "net_metering":
            if not equipment.get("pv") or equipment.get("pv_ac_kw", 0) > 1000:
                raise ValueError("NC net metering requires eligible renewable PV with <=1 MW AC capacity.")
            if equipment.get("battery") and (not equipment.get("renewable_only_charging") or not equipment.get("no_battery_export")):
                raise ValueError("NC solar storage requires PV-only charging and no battery exports in this bounded settlement path.")
        if has_der and kind == "commercial" and not (a["solar_program"] == "net_metering" and equipment.get("pv_ac_kw", 0) <= 100):
            if a["contract_demand_kw"] <= 0 or not a["parallel_service_contract"]:
                raise ValueError("Nonresidential parallel service requires the contracted maximum kW supply; <=100 kW eligible NEM is the filed exception.")
    return deepcopy(a)


def objective_inputs(account, state, policy):
    account, state = deepcopy(account), deepcopy(state or {})
    if policy == "exclude_opening_credits":
        account["opening_credit_kwh"] = {"on_peak": 0., "off_peak": 0.}
        state["credit_kwh"] = {"on_peak": 0., "off_peak": 0.}
    elif policy != "explicit_cash_bill":
        raise ValueError("Unknown carried-credit objective policy.")
    return account, state


def validate_state(account, index, *, state=None, equipment=None):
    """Validate actual inherited history without changing enrollment evidence."""
    inherited = state or {}
    if not isinstance(inherited, dict):
        raise ValueError("Inherited North Carolina billing state must be a structured ledger.")
    revised = deepcopy(account)
    for key in ("history_peaks_kw", "history_on_peak_kw", "history_kwh", "history_billing_months", "contract_demand_kw"):
        if key in inherited:
            revised[key] = deepcopy(inherited[key])
    if "credit_kwh" in inherited:
        revised["opening_credit_kwh"] = deepcopy(inherited["credit_kwh"])
    validate_account(revised, index, equipment=equipment)
    if account["tariff"] == "6L" and "history_billing_months" not in inherited:
        expected = [((account["billing_month"]-12+i) % 12)+1 for i in range(11)]
        if list(account["history_billing_months"]) != expected:
            raise ValueError("6L opening ratchet history must identify the eleven consecutive utility billing months immediately before the first simulated cycle.")


def charge_lines(index, imports_kw, exports_kw, account, *, math, state=None):
    index, days = _index(index)
    validate_account(account, index)
    validate_state(account, index, state=state)
    a = account
    state = deepcopy(state or {})
    plan = a["tariff"]
    base = BASE[plan]
    summer = 6 <= a["billing_month"] <= 9
    factor = days/30 if plan in ("6P", "6L") or days < 26 else 1.
    dt = math.hours
    if not np.isclose(dt*60, (index.asi8[1]-index.asi8[0])/6e10):
        raise ValueError("Tariff math and meter intervals do not match.")
    if not math.convex:
        imports_kw, exports_kw = np.asarray(imports_kw, dtype=float), np.asarray(exports_kw, dtype=float)
        if imports_kw.shape != (len(index),) or exports_kw.shape != imports_kw.shape or not np.isfinite(imports_kw).all() or not np.isfinite(exports_kw).all() or min(imports_kw.min(), exports_kw.min()) < -1e-6:
            raise ValueError("Supply nonnegative finite interval-average imports and exports matching the exact index.")
        if np.any((imports_kw > 1e-5) & (exports_kw > 1e-5)):
            raise ValueError("A single retail meter cannot simultaneously import and export.")
        imports_kw, exports_kw = np.maximum(imports_kw, 0), np.maximum(exports_kw, 0)
        if a["solar_program"] == "non_export" and exports_kw.max() > 1e-6:
            raise ValueError("Non-export operation must curtail excess production, not discard unpriced exports.")
    elif a["solar_program"] == "non_export":
        math.constraints.append(exports_kw == 0)
    total_import, total_export = math.sum(imports_kw)*dt, math.sum(exports_kw)*dt
    energy_mask = on_peak(index, plan)
    demand_mask = on_peak(index, plan, demand=True)
    def masked_sum(values, mask):
        return math.sum(values[mask]) if np.any(mask) else 0.
    exact_peaks = plan == "5" or a["contract_minimum_usd"] > 0
    measured_peak = math.demand(imports_kw, index, 30, exact=exact_peaks)
    on_demand = math.demand(imports_kw, index, 30, demand_mask, exact=exact_peaks)
    if plan == "5P":
        if math.convex:
            math.constraints.append(measured_peak <= 500-1e-5)
        elif measured_peak >= 500-1e-6:
            raise ValueError("Current demand reaches 500 kW; 5P eligibility must be updated for succeeding cycles.")
    opening = deepcopy(state.get("credit_kwh", a["opening_credit_kwh"]))
    reset = a["billing_month"] == 6 and state.get("last_billing_month") != 6
    if reset:
        opening = {"on_peak": 0., "off_peak": 0.}
    credit = {"on_peak": 0., "off_peak": 0.}
    if a["solar_program"] == "net_metering":
        if plan == "1":
            balance = total_import-total_export-opening["on_peak"]-opening["off_peak"]
            billed_total = math.positive(balance, exact=True)
            credit["off_peak"] = math.positive(-balance, exact=True)
            billed_on, billed_off = 0., billed_total
        else:
            balance_on = masked_sum(imports_kw-exports_kw, energy_mask)*dt-opening["on_peak"]
            balance_off = masked_sum(imports_kw-exports_kw, ~energy_mask)*dt-opening["off_peak"]
            billed_on = math.positive(balance_on, exact=True)
            surplus_on = math.positive(-balance_on, exact=True)
            off_debit = math.positive(balance_off, exact=True)
            transfer = math.minimum(surplus_on, off_debit)
            billed_off = off_debit-transfer
            credit = {"on_peak": surplus_on-transfer, "off_peak": math.positive(-balance_off, exact=True)}
            billed_total = billed_on+billed_off
    else:
        billed_on = masked_sum(imports_kw, energy_mask)*dt
        billed_off = masked_sum(imports_kw, ~energy_mask)*dt
        billed_total = total_import
    discount = .95 if a["conservation_discount"] else 1.
    customer = (base["customer_single_200a"] if a["phase"] == "single" and a["service_amperes"] <= 200 else base["customer_other"]) if plan == "5P" else base["customer"]
    lines = {"customer": customer*factor}
    distribution, supply = 0., 0.
    history_peaks = state.get("history_peaks_kw", a["history_peaks_kw"])
    history_months = state.get("history_billing_months", a["history_billing_months"])
    prior_contract = state.get("contract_demand_kw", a["contract_demand_kw"])
    next_contract = prior_contract
    if plan == "5P" and max(history_peaks) >= 500:
        raise ValueError("Evolved demand history makes Schedule 5P unavailable for twelve succeeding cycles; provide a documented eligible schedule change.")
    if plan == "6P" and max(history_peaks) < 500:
        raise ValueError("Evolved eleven-cycle demand history no longer proves ineligibility for 5P; obtain the utility's current 6P eligibility determination instead of retaining frozen history.")
    if plan == "6L" and "history_billing_months" not in state:
        expected_months = [((a["billing_month"]-12+i) % 12)+1 for i in range(11)]
        if list(history_months) != expected_months:
            raise ValueError("6L opening ratchet history must identify the eleven consecutive utility billing months immediately before the first simulated cycle.")
    if plan == "1":
        lines["energy"] = billed_total*base["summer_energy" if summer else "winter_energy"]*discount
    elif plan == "1T":
        season = "summer" if summer else "winter"
        lines["energy_on_peak"] = billed_on*base[season+"_on"]*discount
        lines["energy_off_peak"] = billed_off*base[season+"_off"]*discount
    elif plan == "5":
        demand_applies = a["demand_meter"] and (max(state.get("history_kwh", a["history_kwh"])) > 3000)
        if a["demand_meter"] and not demand_applies:
            # The tariff activates demand when this cycle exceeds 3,000 kWh;
            # an exact regime is required, not a peak inferred from kWh.
            peak = math.choose_leq(total_import, 3000, 0., measured_peak)
        else:
            peak = measured_peak if demand_applies else 0.
        width = (2200+200*math.minimum(math.positive(peak-10, exact=True), 20)+100*math.positive(peak-30, exact=True))*factor
        rates = base["summer_energy" if summer else "winter_energy"]
        lines["energy"] = math.tiered(billed_total, [800*factor, 800*factor+width], rates)
        lines["all_hours_demand"] = math.positive(peak-100, exact=True)*base["demand"]*factor
        minimum = math.maximum([customer*factor, peak*base["summer_minimum" if summer else "winter_minimum"]*factor, a["contract_minimum_usd"]*factor], exact=True)
        lines["minimum_bill_adjustment"] = math.positive(minimum-sum(lines.values()), exact=True)
    else:
        supply = on_demand
        if plan == "1P":
            lines["on_peak_demand"] = supply*base["summer_demand" if summer else "winter_demand"]*factor*discount
        elif plan == "5P":
            distribution = math.maximum(measured_peak, prior_contract, exact=exact_peaks)
            next_contract = distribution if a["parallel_service_contract"] else prior_contract
            lines["on_peak_supply_demand"] = supply*base["summer_demand" if summer else "winter_demand"]*factor
            lines["distribution_demand"] = distribution*base["distribution"]*factor
        elif plan == "6P":
            supply = math.maximum(on_demand, total_import/(days*24), exact=exact_peaks)
            distribution = math.maximum([measured_peak, prior_contract, 500.], exact=exact_peaks)
            next_contract = math.maximum(prior_contract, measured_peak) if a["parallel_service_contract"] else prior_contract
            lines["on_peak_supply_demand"] = supply*base["demand"]*factor
            lines["distribution_demand"] = distribution*base["primary" if a["voltage_v"] >= 2000 else "secondary"]*factor
            lines["reactive_demand"] = 0.  # Validated unity-PF/zero-kvar account.
        elif plan == "6L":
            history_on = state.get("history_on_peak_kw", a["history_on_peak_kw"])
            summer_history = [p*.75 for p, m in zip(history_on, history_months) if 6 <= m <= 9]
            supply = math.maximum([on_demand, 1000.]+summer_history, exact=exact_peaks)
            next_contract = math.maximum(prior_contract, measured_peak, exact=exact_peaks)
            distribution = next_contract
            lines["on_peak_supply_demand"] = supply*base["demand"]*factor
            lines["distribution_demand"] = 0. if a["voltage_v"] >= 69000 else distribution*base["primary" if a["voltage_v"] >= 2000 else "secondary"]*factor
        lines["energy_on_peak"] = billed_on*base["on_energy"]*discount
        lines["energy_off_peak"] = billed_off*base["off_energy"]*discount
        if plan != "1P" and a["contract_minimum_usd"] > 0:
            # Demand/customer floor plus riders is preserved under NEM.
            fixed_demand = sum(v for k, v in lines.items() if not k.startswith("energy_"))
            lines["contract_minimum_adjustment"] = math.positive(a["contract_minimum_usd"]*factor-fixed_demand-lines["energy_on_peak"]-lines["energy_off_peak"], exact=True)
    rider_class = "residential" if plan.startswith("1") else "sgs" if plan in ("5", "5P") else "lgs"
    service_days = index.normalize().unique()
    weighted = {k: 0. for k in _RIDER_TABLES["2026"][rider_class]}
    versions = set()
    for day in service_days:
        version = "2025-01" if day.date() < date(2025, 2, 1) else "2025" if day.date() <= date(2026, 1, 31) else "2026"
        versions.add(version)
        values = {**_RIDER_TABLES[version][rider_class]}
        if day.date() < date(2025, 3, 1):
            values["CCR"] = 0.  # Newly authorized rider, first effective March1.
        if date(2026, 2, 1) <= day.date() < date(2026, 8, 1):
            # January13 fuel order explicitly sets B1=0; June26 first
            # quarterly update introduces the new B1 effective August1.
            values["B1"] = 0.
        for key, value in values.items():
            weighted[key] += value/days
    for key, value in weighted.items():
        if key in ("RP", "RPE"):
            lines["rider_"+key] = 0. if a["ceps_exempt"] else value*(days/30 if days < 26 else 1.)*discount
        else:
            lines["rider_"+key] = billed_total*value*discount
    subtotal = sum(lines.values())
    lines["nc_sales_tax"] = subtotal*.07
    next_state = {"credit_kwh": credit, "contract_demand_kw": next_contract,
                  "last_billing_month": a["billing_month"],
                  "history_peaks_kw": list(history_peaks[1:])+[measured_peak],
                  "history_on_peak_kw": list(state.get("history_on_peak_kw", a["history_on_peak_kw"])[1:])+[on_demand],
                  "history_billing_months": list(history_months[1:])+[a["billing_month"]],
                  "history_kwh": list(state.get("history_kwh", a["history_kwh"])[1:])+[total_import]}
    fixed_change = len({(_RIDER_TABLES[v][rider_class]["RP"], _RIDER_TABLES[v][rider_class]["RPE"]) for v in versions}) > 1 and not a["ceps_exempt"]
    complete = not fixed_change or a["fixed_rider_allocation_confirmed"]
    warnings = ["Retail bill assumes a confirmed ordinary taxable account with unity power factor and no voluntary/special riders; PJM capacity/transmission are bundled and are not added separately."]
    if fixed_change and not complete:
        warnings.append("Incomplete bill: this cycle crosses a fixed RP/RPE rider change. A calendar-day allocation is shown as a study estimate pending bill/utility confirmation; the utility worksheet establishes per-kWh proration but does not resolve this fixed-rider allocation.")
    return {"lines": lines, "metrics": {"import_kwh": total_import, "export_kwh": total_export,
             "billed_energy_kwh": billed_total, "on_peak_billed_kwh": billed_on, "off_peak_billed_kwh": billed_off,
             "measured_peak_kw": measured_peak, "on_peak_demand_kw": on_demand,
             "distribution_billing_kw": distribution, "supply_billing_kw": supply,
             "billing_days": days, "customer_demand_factor": factor,
             "credit_reset": reset, "opening_credit_kwh": opening,
             "closing_credit_kwh": credit, "supply_arrangement": "bundled",
             "rate_versions": sorted(versions)},
            "next_state": next_state,
            "warnings": warnings, "is_complete_bill": complete}
