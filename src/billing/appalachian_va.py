"""Appalachian Power Virginia Tariff 28 Standard Service (015 and 231)."""
import numpy as np
import pandas as pd

from .appalachian_va_rates import COVERAGE, RATE_SOURCES, rates_for_month

UTILITY = "appalachian_power_virginia"
TIMEZONE = "America/New_York"
PLANS = {"015": "Traditional Residential RS", "231": "Small General Service SGS"}
STUDY_LIMIT_KW = 25.
TAX_SOURCES = [
    "https://law.lis.virginia.gov/vacode/title58.1/chapter29/section58.1-2900/",
    "https://law.lis.virginia.gov/vacode/title58.1/chapter29/section58.1-2902/",
    "https://www.scc.virginia.gov/regulated-industries/public-taxation/taxes-and-fees/",
    "https://www.roanokeva.gov/3259/Consumer-Utility-Tax",
    "https://www.roanokeva.gov/DocumentCenter/View/8874/guidelines-Consumer-Utility-Tax?bidId=",
]
DER_SOURCE = "https://www.appalachianpower.com/business/builders/generating-equipment"
SOURCES = [*RATE_SOURCES, *TAX_SOURCES, DER_SOURCE]
GAPS = (
    ("2025-02-01", "2025-10-31", "Intermediate filed rider intersections are unverified."),
    ("2025-12-01", "2025-12-31", "December rider intersection is unverified."),
    ("2026-02-01", "2026-09-30", "Intermediate rider intersections and within-cycle allocations are unverified."),
    ("2026-12-01", "2026-12-31", "Later filed rider intersection is unverified."),
)
CONFIRMATIONS = {
    "eligibility_confirmed": "Appalachian Power confirmed the Virginia RS 015 or SGS 231 assignment",
    "ordinary_service_confirmed": "Ordinary bundled Standard Service, one single-phase secondary meter, no special charges or credits",
    "full_monthly_charges_confirmed": "Complete calendar measurement cycle with matching bill date and full monthly charges",
    "locality_confirmed": "City of Roanoke utility tax applies, with ordinary private residential or commercial status",
    "local_tax_relief_inactive_confirmed": "No special local utility tax exemption or residential heating relief applies",
}


def account_fields(plan_id="015"):
    fields = [dict(name=key, type="boolean", label=label, required=True)
              for key, label in CONFIRMATIONS.items()]
    fields += [
        dict(name="account_source", type="text", required=True,
             label="Company assignment and City of Roanoke tax evidence or explicit hypothetical assumption"),
        dict(name="der_ordinary_service_confirmed", type="boolean",
             label="Written Appalachian Power agreement permits this exact non-export installation on unchanged Standard Service terms"),
        dict(name="der_activation_date", type="date", label="Final interconnection and metering approval active by"),
        dict(name="der_eligibility_source", type="text",
             label="Approval and special-agreement reference confirming no other billing charges, minimums or credits"),
    ]
    if plan_id == "231":
        fields += [
            dict(name="sgs_review_confirmed", type="boolean", required=True,
                 label="Company confirmed SGS 231 throughout the cycle using independent actual demand history"),
            dict(name="sgs_history_through_month", type="date", required=True,
                 label="First day of the last month in the Company's 12-month SGS review"),
            dict(name="sgs_monthly_demands_kw", type="number_array", required=True,
                 label="12 consecutive actual monthly metered demands, oldest first (kW)"),
            dict(name="sgs_review_source", type="text", required=True,
                 label="Utility classification, 12-month review and no pending reclassification evidence"),
        ]
    return fields


def defaults(plan_id="015"):
    if plan_id not in PLANS:
        raise ValueError("Select Appalachian Power Virginia Standard Service 015 or 231.")
    month = pd.Timestamp(COVERAGE[-1][0])
    account = dict(
        tariff=plan_id, supply="bundled", export_mode="none", voltage="secondary", phase="single",
        voltage_v=240., meter_count=1, locality="roanoke_city", opening_credit_usd=0.,
        billing_month=str(month.date()), bill_date=str((month+pd.offsets.MonthEnd()).date()),
        cycle_kind="regular", cycle_source="", account_source="", rate_evidence_mode="verified",
        der_ordinary_service_confirmed=False, der_activation_date="", der_eligibility_source="",
    )
    account.update(dict.fromkeys(CONFIRMATIONS, False))
    if plan_id == "231":
        account.update(sgs_review_confirmed=False, sgs_history_through_month="",
                       sgs_monthly_demands_kw=[], sgs_review_source="")
    return account


def hypothetical_defaults(plan_id="015", *, day=None):
    account = defaults(plan_id)
    month = pd.Timestamp(day or account["billing_month"]).replace(day=1)
    account.update(dict.fromkeys(CONFIRMATIONS, True))
    account.update(
        hypothetical_account=True, billing_month=str(month.date()),
        bill_date=str((month+pd.offsets.MonthEnd()).date()),
        cycle_source="Hypothetical complete calendar reading cycle with a matching bill date",
        account_source="Hypothetical eligible single-meter Virginia Standard Service in the City of Roanoke",
        der_ordinary_service_confirmed=True, der_activation_date="2024-12-31",
        der_eligibility_source="Hypothetical written utility special agreement and permission to operate. "
                               "Exact non-export PV and paired storage retain ordinary import billing without other terms.",
    )
    if plan_id == "231":
        account.update(sgs_review_confirmed=True, sgs_monthly_demands_kw=[15.]*12,
                       sgs_history_through_month=str((month-pd.offsets.MonthBegin()).date()),
                       sgs_review_source="Hypothetical retained SGS 231 based on 12 actual 15 kW monthly demands")
    return account


def catalog():
    return [
        dict(
            id=plan, label=f"Appalachian Power {label} ({plan})", status="supported",
            customer_class="residential" if plan == "015" else "commercial",
            coverage=[dict(start=start, end=end) for start, end in COVERAGE],
            coverage_gaps=[dict(start=start, end=end, reason=reason) for start, end, reason in GAPS],
            voltage="secondary", interval_minutes=[15], supply_arrangements=["bundled"],
            equipment_modes=["grid_only", "pv_only", "pv_battery"], solar_modes=["non_export"],
            representative_peak_kw=3. if plan == "015" else 15.,
            account_fields=account_fields(plan), sources=SOURCES,
            eligibility="Ordinary Virginia Standard Service in the City of Roanoke, single meter. "
                        "SGS 231 requires documented average metered demand at most 25 kW and retained assignment.",
            limitations=[
                "Only listed matching complete calendar cycles. Missing filed rates, other localities and special tax relief reject.",
                "Study envelope of 25 kW for native load and imports. No billed demand for SGS 231.",
                "PV and PV-charged paired storage require an account-specific written non-export special agreement and approval "
                "retaining all ordinary import billing terms.",
            ],
        )
        for plan, label in PLANS.items()
    ]


def _reference(account, key):
    value = account.get(key)
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 500:
        raise ValueError(f"Document Appalachian Power {key} without personal identifiers.")


def _sgs_history(account, month):
    demands = account.get("sgs_monthly_demands_kw")
    if (account.get("sgs_review_confirmed") is not True or not isinstance(demands, list)
            or len(demands) != 12 or any(type(kw) not in (int, float) or not 0 <= kw <= 1e6 for kw in demands)):
        raise ValueError("SGS 231 requires retained utility assignment and 12 actual monthly metered demands.")
    _reference(account, "sgs_review_source")
    date = account.get("sgs_history_through_month")
    try:
        end = pd.Timestamp(date)
        valid = end.day == 1 and str(end.date()) == date
    except (TypeError, ValueError):
        valid = False
    if not valid or end != month-pd.offsets.MonthBegin():
        raise ValueError("SGS review history must cover the 12 months immediately preceding the billed month.")
    average = sum(demands)/12
    if average > 25.:
        raise ValueError("SGS 231 excludes demand histories with an average above 25 kW.")
    return dict(sgs_average_metered_demand_kw=average, sgs_history_through_month=date,
                sgs_monthly_demands_kw=list(demands))


def cycle_review(account, index):
    index = pd.DatetimeIndex(index)
    step = pd.Timedelta(minutes=15)
    if (len(index) < 2 or str(index.tz) != TIMEZONE or index.hasnans
            or not np.all(index[1:]-index[:-1] == step)):
        raise ValueError("Appalachian Power requires complete consecutive Eastern-time 15-minute intervals.")
    start, stop = index[0], index[-1]+step
    if (start != start.normalize() or start.day != 1 or stop != start+pd.offsets.MonthBegin()
            or account.get("cycle_kind") != "regular" or account.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("Appalachian Power initial scope requires a complete calendar cycle and full monthly charges.")
    month, bill_date = str(start.date()), str(index[-1].date())
    if account.get("billing_month") != month or account.get("bill_date") != bill_date:
        raise ValueError("Appalachian Power requires matching calendar service month and final-day bill date.")
    rates = rates_for_month(month)
    return dict(service_start=month, service_end=bill_date, billing_month=month, bill_date=bill_date,
                cycle_days=(stop.date()-start.date()).days,
                elapsed_hours=float((stop-start)/pd.Timedelta(hours=1)), source_version=rates["source_version"],
                source_grade=rates["source_grade"])


def validate_account(account, index, equipment=None):
    if (not isinstance(account, dict) or account.get("tariff") not in tuple(PLANS)
            or account.get("supply") != "bundled" or account.get("export_mode") != "none"):
        raise ValueError("Select Appalachian Power Virginia 015 or 231 bundled Standard Service and zero export.")
    if any(account.get(key) is not True for key in CONFIRMATIONS):
        raise ValueError("Confirm Appalachian Power assignment, ordinary service, cycle and City of Roanoke tax facts.")
    for key in ("account_source", "cycle_source"):
        _reference(account, key)
    expected = dict(voltage="secondary", phase="single", voltage_v=240., meter_count=1,
                    locality="roanoke_city", opening_credit_usd=0., rate_evidence_mode="verified")
    if (any(account.get(key) != value or isinstance(account.get(key), bool) for key, value in expected.items())
            or account.get("provisional_assumptions_accepted", False) is not False):
        raise ValueError("Appalachian Power scope is one ordinary 120/240 V secondary meter, Roanoke City and verified rates.")
    cycle = cycle_review(account, index)
    if account["tariff"] == "231":
        _sgs_history(account, pd.Timestamp(cycle["billing_month"]))
    if equipment and (equipment.get("pv") or equipment.get("battery")):
        if not equipment.get("pv") or account.get("der_ordinary_service_confirmed") is not True:
            raise ValueError("Confirm the exact non-export PV installation and unchanged tariff in a written utility special agreement.")
        _reference(account, "der_eligibility_source")
        date = account.get("der_activation_date")
        try:
            active = str(pd.Timestamp(date).date()) == date and date <= cycle["service_start"]
        except (TypeError, ValueError):
            active = False
        if not active:
            raise ValueError("Appalachian Power final interconnection approval and metering must be active before service.")
        if equipment.get("battery") and (equipment.get("renewable_only_charging") is not True
                                        or equipment.get("no_battery_export") is not True):
            raise ValueError("Appalachian Power paired storage requires PV-only charging and zero export.")
        if max(equipment.get("pv_dc_kw", 0.), equipment.get("pv_ac_kw", 0.))+equipment.get("battery_kw", 0.) > STUDY_LIMIT_KW+1e-8:
            raise ValueError("Appalachian Power combined DER exceeds the 25 kW study limit.")


def validate_state(account, index, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("Appalachian Power non-export Standard Service has no credit bank or billing-demand state.")


def charge_lines(index, imports, exports, account, *, math, state=None):
    validate_state(account, index, state)
    cycle = cycle_review(account, index)
    month = cycle["billing_month"]
    rates = rates_for_month(month)
    plan = account["tariff"]
    if math.convex:
        math.constraints.extend([exports == 0, imports <= STUDY_LIMIT_KW])
    elif np.max(exports) > 1e-5 or np.max(imports) > STUDY_LIMIT_KW+1e-7:
        raise ValueError("Appalachian Power requires zero export and imports within the study power limit.")
    energy = math.hours*math.sum(imports)
    schedule = rates["plans"][plan]
    customer = schedule["customer"]
    lines = {"distribution_customer": customer}
    lines.update({name: energy*price for name, price in schedule["per_kwh"].items()})
    lines["triennial_review_refund"] = schedule["trr_credit"]

    # State statutory tiers, the SCC's actual special regulatory levy and the
    # statutory local portion are distinct from Roanoke's city consumer tax.
    first = math.minimum(energy, 2500.)
    lower_two = math.minimum(energy, 50000.)
    volumes = (first, lower_two-first, energy-lower_two)
    for name, prices in (
        ("state_consumption_tax", (.00102, .00065, .00050)),
        ("special_regulatory_tax", rates["regulatory_tax"]),
        ("local_consumption_tax", (.00038, .00024, .00018)),
    ):
        lines[name] = sum(volume*price for volume, price in zip(volumes, prices))
    city_rates = (.00780, .00450) if plan == "015" else (.00800, .00540)
    city_variable = math.tiered(energy, (1000.,), city_rates)
    city_minimum = customer*.12
    lines["roanoke_consumer_utility_tax"] = math.maximum([city_variable, city_minimum], exact=True)

    history = _sgs_history(account, pd.Timestamp(month)) if plan == "231" else {}
    return dict(
        lines=lines, next_state={}, is_complete_bill=True, excluded_components=[],
        rate_sources=[*rates["sources"], *TAX_SOURCES, DER_SOURCE],
        rate_evidence_status="verified", assumption_model=None, rate_assumptions=[],
        metrics={**cycle, **history, "raw_import_kwh": energy, "locality": account["locality"],
                 "distribution_minimum_usd": customer, "roanoke_tax_minimum_usd": city_minimum,
                 "billing_demand_applied": False, "rounded_cash_optimum_claimed": False},
        warnings=[
            "Company-confirmed ordinary Standard Service in the City of Roanoke. SGS demand history determines eligibility.",
            "Electricity charges and statutory/local taxes use unrounded study quantities. Exact invoice rounding and special tax relief are outside scope.",
            "Non-export PV and paired storage require written APCo approval retaining ordinary billing, including all applicable fees and minimums.",
        ],
    )
