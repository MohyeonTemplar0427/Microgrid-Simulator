"""UGI Electric Pennsylvania R and GS-1 ordinary GSR-1 full-calendar bills."""
from datetime import date

import numpy as np
import pandas as pd

from .ugi_pa_rates import COVERAGE, PLANS, SOURCES, TRANSITIONS, rates_for_month

UTILITY = "ugi_electric_pennsylvania"
TIMEZONE = "America/New_York"
CONFIRMATIONS = {
    "eligibility_confirmed": "UGI confirms electric service territory and the selected ordinary R or GS-1 assignment",
    "ordinary_service_confirmed": "One established 120/240 V secondary single-phase meter with standard facilities, no special contracts, assistance, outdoor lighting, optional charges or past due balances",
    "full_monthly_charges_confirmed": "Full calendar meter cycle with one full monthly charge, read and billed on the last service date",
    "fixed_default_supply_confirmed": "UGI GSR-1 default generation for this service period without an EGS, hourly pricing or migration reconciliation",
    "local_charges_confirmed": "Ordinary state-only Pennsylvania tax treatment in UGI electric territory in Luzerne or Wyoming County",
}
GS_FACTS = {
    "gs_retained_assignment_confirmed": "UGI confirms established ordinary GS-1 service for the full study under an active standard yearly contract",
    "gs_non_demand_confirmed": "Ordinary non-worship account with utility-confirmed demands at or below 5 kW throughout the year, no recurring usage above 2,000 kWh and no metered-demand service",
}


def account_fields(plan="R"):
    confirmations = {**CONFIRMATIONS}
    if plan == "R":
        confirmations["residential_use_confirmed"] = "One dwelling used solely for ordinary household purposes with residential sales-tax exemption"
    else:
        confirmations.update(GS_FACTS)
    fields = [dict(name=k, type="boolean", required=True, label=v) for k, v in confirmations.items()]
    fields.extend([
        dict(name="account_source", type="text", required=True, label="Utility class, GSR-1 assignment, jurisdiction and tax evidence"),
        dict(name="der_ordinary_service_confirmed", type="boolean", label="Final UGI Rule 17 interconnection, single bidirectional meter and ordinary import billing approved for the exact installed non-export design"),
        dict(name="der_activation_date", type="date", label="Effective date of final UGI interconnection and required metering"),
        dict(name="der_eligibility_source", type="text", label="Utility approval covering this PV installation, ordinary import tariff, no aggregation, no credit balance and no special recurring charge"),
        dict(name="battery_interconnection_confirmed", type="boolean", label="UGI approval explicitly includes this paired PV-only-charging battery with no export or additional recurring charge"),
    ])
    if plan == "GS-1":
        fields.extend([
            dict(name="gs_prior_peak_upper_bound_kw", type="number", required=True, label="UGI-confirmed highest service demand bound in kW across the relevant year (at most 5)"),
            dict(name="gs_supply_peak_impact_kw", type="number", label="UGI GSR-1 supply peak load impact in kW for applicable September 30 reviews from June 2025 (below 100)"),
            dict(name="gs_review_source", type="text", required=True, label="Independent class, prior usage/demand, yearly assignment and GSR-1 review covering the study dates"),
        ])
    return fields


def defaults(plan="R"):
    if plan not in PLANS:
        raise ValueError("Select UGI Pennsylvania R or GS-1.")
    account = dict(tariff=plan, supply="default_ptc", export_mode="none", voltage="secondary",
                   phase="single", voltage_v=240., meter_count=1, opening_credit_usd=0.,
                   tax_jurisdiction="pa_state_only", tax_exempt=False, rate_evidence_mode="verified",
                   billing_month="2025-03-01", bill_date="2025-03-31", cycle_kind="regular",
                   cycle_source="", account_source="", der_ordinary_service_confirmed=False,
                   der_activation_date="", der_eligibility_source="", battery_interconnection_confirmed=False)
    account.update(dict.fromkeys(CONFIRMATIONS, False))
    if plan == "R":
        account["residential_use_confirmed"] = False
    else:
        account.update(dict.fromkeys(GS_FACTS, False), gs_prior_peak_upper_bound_kw=None,
                       gs_supply_peak_impact_kw=None, gs_review_source="")
    return account


def hypothetical_defaults(plan="R", *, day=None):
    account = defaults(plan)
    start = pd.Timestamp(day or account["billing_month"]).replace(day=1)
    account.update(
        dict.fromkeys(CONFIRMATIONS, True), hypothetical_account=True, billing_month=str(start.date()),
        bill_date=str((start + pd.offsets.MonthEnd()).date()),
        cycle_source="Explicit hypothetical calendar cycle with an ordinary final-day meter read and bill",
        account_source="Explicit hypothetical UGI Electric GSR-1 service in Dallas Borough, Luzerne County with ordinary plan-specific state tax treatment",
        der_ordinary_service_confirmed=True, der_activation_date="2024-12-01",
        der_eligibility_source="Explicit hypothetical final UGI Rule 17 approval covering the exact PV and any paired battery, single bidirectional meter, ordinary import billing, no other charge, aggregation or bank",
        battery_interconnection_confirmed=True,
    )
    if plan == "R":
        account["residential_use_confirmed"] = True
    else:
        account.update(dict.fromkeys(GS_FACTS, True), gs_prior_peak_upper_bound_kw=3.,
                       gs_supply_peak_impact_kw=3.,
                       gs_review_source="Explicit hypothetical utility-retained GS-1 business with documented annual demand up to 3 kW, ordinary annual contract, no recurring months over 2,000 kWh and separately confirmed GSR-1 determinations")
    return account


def catalog():
    rows = []
    for plan, label in PLANS.items():
        gaps = [dict(start=month+"-01", end=str((pd.Timestamp(month+"-01")+pd.offsets.MonthEnd()).date()),
                     reason="Midmonth service-rendered STAS change; allocation of the fixed monthly charge is unverified")
                for month in TRANSITIONS]
        if plan == "R":
            gaps.append(dict(start="2026-12-01", end="2026-12-31", reason="Residential USP reconciliation for the December GSR change is unverified"))
        rows.append(dict(
            id=plan, label=f"UGI Electric PA {plan} {label}, GSR-1", status="supported",
            customer_class="residential" if plan == "R" else "commercial", voltage="secondary",
            coverage=[dict(start=s, end=e) for s, e in COVERAGE[plan]], coverage_gaps=gaps,
            interval_minutes=[15], solar_modes=["non_export"], supply_arrangements=["default_ptc"],
            equipment_modes=["grid_only", "pv_only", "pv_battery"], representative_peak_kw=2.5,
            account_fields=account_fields(plan), sources=SOURCES,
            eligibility="Utility-confirmed ordinary single-phase residential R or non-demand GS-1 with GSR-1 default supply and documented state-only tax treatment.",
            limitations=["Calendar cycles with the final-day bill only. The five midmonth STAS changes lack verified allocation.",
                         "November 2026 is in progress as of November 19. December GS-1 uses Supplement 101 as published; the residential USP rate remains open.",
                         "PV and paired storage require final approval for the exact design, ordinary import rates, zero exports and zero opening credits. Standalone storage and export settlements are outside coverage."],
        ))
    return rows


def _reference(account, key):
    value = account.get(key)
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 500:
        raise ValueError(f"Document UGI {key} without personal identifiers.")


def _number(value):
    return type(value) in (int, float) and np.isfinite(value)


def cycle_review(account, index):
    index = pd.DatetimeIndex(index)
    step = pd.Timedelta(minutes=15)
    if (len(index) < 2 or str(index.tz) != TIMEZONE or index.hasnans
            or not np.all(index[1:] - index[:-1] == step)):
        raise ValueError("UGI requires complete consecutive America/New_York 15-minute intervals.")
    start, stop = index[0], index[-1] + step
    if (start != start.normalize() or start.day != 1 or stop != start + pd.offsets.MonthBegin()
            or account.get("cycle_kind") != "regular" or account.get("full_monthly_charges_confirmed") is not True):
        raise ValueError("UGI requires a complete calendar meter cycle and one full monthly charge.")
    month, end = str(start.date()), str(index[-1].date())
    if account.get("billing_month") != month or account.get("bill_date") != end:
        raise ValueError("UGI requires matching service dates and a bill rendered on the final service date.")
    rates = rates_for_month(month, account["tariff"])
    return dict(service_start=month, service_end=end, billing_month=month, bill_date=end,
                elapsed_hours=float((stop-start)/pd.Timedelta(hours=1)),
                source_versions=rates["source_versions"], coverage_timing=rates["coverage_timing"]), rates


def validate_account(account, index, equipment=None):
    if (not isinstance(account, dict) or account.get("tariff") not in PLANS
            or account.get("supply") != "default_ptc" or account.get("export_mode") != "none"):
        raise ValueError("Select UGI Electric R or GS-1, ordinary GSR-1 default service and no export.")
    if any(account.get(key) is not True for key in CONFIRMATIONS):
        raise ValueError("Confirm UGI territory, plan, supply, state-only taxes, ordinary service and full cycles.")
    for key in ("account_source", "cycle_source"):
        _reference(account, key)
    expected = dict(voltage="secondary", phase="single", voltage_v=240., meter_count=1,
                    opening_credit_usd=0., tax_jurisdiction="pa_state_only", rate_evidence_mode="verified")
    if (any(account.get(k) != v or isinstance(account.get(k), bool) for k, v in expected.items())
            or account.get("provisional_assumptions_accepted", False) is not False
            or account.get("tax_exempt") is not False):
        raise ValueError("UGI requires one ordinary 120/240 V single-phase meter, no special tax exemption, provisional rates or opening bank.")
    cycle, _ = cycle_review(account, index)
    if account["tariff"] == "R":
        if account.get("residential_use_confirmed") is not True:
            raise ValueError("UGI R requires a solely residential metered dwelling for the Pennsylvania exemption.")
    else:
        peak = account.get("gs_prior_peak_upper_bound_kw")
        impact = account.get("gs_supply_peak_impact_kw")
        if (any(account.get(key) is not True for key in GS_FACTS) or not _number(peak) or not 0 <= peak <= 5.):
            raise ValueError("UGI GS-1 needs independent retained assignment, annual demand at most 5 kW and documented historical usage.")
        if cycle["billing_month"] >= "2025-06-01" and (not _number(impact) or not 0 <= impact < 100.):
            raise ValueError("UGI GSR-1 needs a separate utility-determined supply peak load impact below 100 kW.")
        _reference(account, "gs_review_source")
    if not equipment or not (equipment.get("pv") or equipment.get("battery")):
        return
    if equipment.get("pv") is not True or account.get("der_ordinary_service_confirmed") is not True:
        raise ValueError("UGI renewable service requires final approval of this PV installation; standalone storage is unsupported.")
    _reference(account, "der_eligibility_source")
    try:
        active = date.fromisoformat(account.get("der_activation_date"))
    except (TypeError, ValueError):
        raise ValueError("Provide the active UGI interconnection and metering date.") from None
    if active.isoformat() != account["der_activation_date"] or active.isoformat() > cycle["service_start"]:
        raise ValueError("UGI renewable service and metering must be active before the cycle.")
    # Both classes stay in the small approved inverter-based subset in this adapter.
    pv_dc, pv_ac = equipment.get("pv_dc_kw"), equipment.get("pv_ac_kw")
    battery_kw = equipment.get("battery_kw") if equipment.get("battery") else 0.
    if (any(not _number(v) or v < 0 for v in (pv_dc, pv_ac, battery_kw))
            or min(pv_dc, pv_ac) <= 0 or max(pv_dc, pv_ac) + battery_kw > 10. + 1e-7):
        raise ValueError("UGI initial scope requires a positive small PV system and combined nameplate at most 10 kW.")
    if equipment.get("battery") and (battery_kw <= 0 or account.get("battery_interconnection_confirmed") is not True
            or equipment.get("renewable_only_charging") is not True or equipment.get("no_battery_export") is not True):
        raise ValueError("UGI paired storage needs exact utility approval, PV-only charging and zero export.")


def validate_native_load(account, load):
    values = np.asarray(load, dtype=float)
    if values.ndim != 1 or not values.size or not np.isfinite(values).all() or np.min(values) < 0:
        raise ValueError("UGI needs a finite, nonnegative native-load series for each service cycle.")
    if account["tariff"] == "GS-1" and (np.max(values) > 5.+1e-7 or .25*values.sum() > 2000.+1e-7):
        raise ValueError("UGI GS-1 native load must stay within 5 kW and 2,000 kWh per cycle in this ordinary non-demand subset.")


def validate_state(account, index, state=None, equipment=None):
    if state not in (None, {}):
        raise ValueError("UGI ordinary non-export service supports no opening credits, demand state or other balances.")


def charge_lines(index, imports, exports, account, *, math, state=None):
    validate_state(account, index, state)
    cycle, rates = cycle_review(account, index)
    if math.convex:
        math.constraints.append(exports == 0)
    elif np.max(np.abs(exports)) > 1e-5:
        raise ValueError("UGI export settlement is unsupported; exports must be zero.")
    kwh = math.hours * math.sum(imports)
    if account["tariff"] == "GS-1":
        if math.convex:
            math.constraints.extend([imports <= 5., kwh <= 2000.])
        else:
            validate_native_load(account, imports)
    lines = dict(distribution_customer=rates["customer"], distribution_energy=kwh*rates["distribution"],
                 energy_efficiency=kwh*rates["efficiency"])
    if account["tariff"] == "R":
        lines["universal_service"] = kwh*rates["universal_service"]
    dsic_basis = sum(lines.values())
    lines["distribution_dsic"] = dsic_basis*rates["dsic"]
    lines["default_service_supply"] = kwh*rates["supply"]
    stas_basis = sum(lines.values())
    lines["state_tax_adjustment"] = stas_basis*rates["stas"]
    taxable = sum(lines.values())
    lines["sales_tax"] = taxable*rates["sales_tax"]
    return dict(
        lines=lines, next_state={}, is_complete_bill=True, excluded_components=[], rate_sources=SOURCES,
        rate_evidence_status="verified", assumption_model=None, rate_assumptions=[],
        metrics={**cycle, "rates": rates, "raw_import_kwh": kwh, "dsic_basis_usd": dsic_basis,
                 "stas_basis_usd": stas_basis, "sales_tax_basis_usd": taxable if account["tariff"] == "GS-1" else 0.,
                 "monthly_minimum_usd": rates["customer"], "rounded_cash_optimum_claimed": False},
        warnings=["GSR-1 already includes generation, transmission, PJM costs and Pennsylvania gross receipts tax. "
                  "The separate state sales tax applies only to the ordinary commercial account in this scope.",
                  "Only verified complete calendar cycles with a final-day bill are supported. "
                  "Published forward rates and completed service are distinguished in coverage_timing."],
    )
