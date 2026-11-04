"""AES dated-source, calendar, eligibility and actual-demand-state safeguards."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.billing import aes_ohio as aes
from src.billing.aes_ohio_rates import rates_on, generation_on, transmission_on
from src.billing.regional import calculate_cycle
from src.timeseries import build_interval_index

ROOT = Path(__file__).resolve().parents[1]
MONTHS = ("2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06",
          "2026-06", "2026-07", "2026-09", "2026-10", "2026-11")


def fixture(plan="D17", month="2025-06"):
    day=month+"-01"
    end=str((pd.Timestamp(day)+pd.offsets.MonthEnd()).date())
    return aes.hypothetical_defaults(plan,day=day), build_interval_index(day,end,aes.TIMEZONE,15).index


def bill(a,index,power=2.,state=None,equipment=None):
    x=np.full(len(index),power) if np.isscalar(power) else np.asarray(power)
    return calculate_cycle(aes.UTILITY,index,x,np.zeros(len(index)),a,state=state,equipment=equipment)


def test_retained_source_files_and_originals_have_exact_evidence_identity():
    folder=ROOT/"docs/utility_sources/aes_ohio"
    manifest=json.loads((folder/"sources.json").read_text())
    assert manifest["no_rate_substitution"] and manifest["no_export_settlement"]
    for name,digest in manifest["files"].items():
        assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==digest,name
    for path in (folder/"delivery/source_ledger.json",folder/"supply/sources.json",folder/"rules/sources.json"):
        data=json.loads(path.read_text());rows=data["sources"]
        rows=rows.values() if isinstance(rows,dict) else rows
        for row in rows:
            original=row.get("original_path",row.get("path"))
            if original and row.get("sha256"):
                assert hashlib.sha256((ROOT/original).read_bytes()).hexdigest()==row["sha256"],original


@pytest.mark.parametrize("plan",aes.PLANS)
@pytest.mark.parametrize("month",MONTHS)
def test_every_declared_complete_month_has_dated_itemized_scope(plan,month):
    a,index=fixture(plan,month)
    out=bill(a,index)
    assert out["is_complete_bill"] and out["excluded_components"]==[]
    assert out["rate_evidence_status"]=="verified" and out["rate_assumptions"]==[]
    assert out["metrics"]["source_versions"]==rates_on(index[0].date(),plan,bill_date=a["bill_date"])["source_versions"]
    assert out["metrics"]["partial_period_proration_applied"] is False
    assert out["metrics"]["state_tax_cat_gross_up_applied"] is False
    assert out["lines"]["customer_refund"]==out["lines"]["sales_tax"]==0.


@pytest.mark.parametrize("month",["2024-12","2025-07","2025-08","2025-09","2025-10","2025-11","2025-12",
                                  "2026-01","2026-02","2026-03","2026-04","2026-05","2026-08","2026-12","2027-01"])
def test_missing_intersections_and_one_time_refund_month_reject(month):
    a,index=fixture("D17",month)
    with pytest.raises(ValueError,match="complete verified component coverage"):
        aes.validate_account(a,index)


def test_generation_service_clock_and_transmission_bill_clock_are_separate():
    assert generation_on("2025-05-31")["id"]=="g10_25th_2024_06_01"
    assert generation_on("2025-06-01")["id"]=="g10_26th_2025_06_01"
    assert transmission_on("2025-05-31")["id"]=="t08_24th_2024_09_01"
    assert transmission_on("2025-06-01")["id"]=="t08_25th_2025_06_01"
    assert transmission_on("2025-09-01")["d19_low_load_substitute_usd_per_kwh"]=="0.0549634"
    assert generation_on("2026-06-01")["id"]=="g10_27th_2026_06_01"
    assert generation_on("2025-06-01")["original_pdf_recovered"] is False
    assert generation_on("2025-06-01")["source_status"]=="official_calculator_and_cached_official_adopted_tariff_text"


@pytest.mark.parametrize("month,hours,days",[("2025-02",672,28),("2025-03",743,31),("2026-11",721,30)])
def test_dst_days_and_statutory_measurement_days_are_distinct(month,hours,days):
    a,index=fixture("D17",month)
    cycle=aes.cycle_review(a,index)
    assert len(index)==4*hours
    assert cycle["elapsed_hours"]==hours and cycle["cycle_days"]==days
    assert cycle["excise_tax_thresholds_kwh"]==([2000.,15000.] if days==30 else [67.*days,500.*days])


@pytest.mark.parametrize("damage",["missing","duplicate","unordered","hourly","utc","partial","billing_month","bill_date","provisional"])
def test_time_grid_and_cycle_alignment_reject_without_repair(damage):
    a,index=fixture()
    if damage=="missing":index=index.delete(9)
    elif damage=="duplicate":index=index.insert(9,index[8])
    elif damage=="unordered":index=index.take([1,0,*range(2,len(index))])
    elif damage=="hourly":index=index[::4]
    elif damage=="utc":index=index.tz_convert("UTC")
    elif damage=="partial":index=index[:-96]
    elif damage=="billing_month":a["billing_month"]="2025-05-01"
    elif damage=="bill_date":a["bill_date"]="2025-07-01"
    else:a["rate_evidence_mode"]="provisional"
    with pytest.raises(ValueError):aes.validate_account(a,index)


@pytest.mark.parametrize("key,value",[("eligibility_confirmed",False),("ordinary_service_confirmed",False),
    ("sso_enrollment_confirmed",False),("no_local_tax_confirmed",False),("full_monthly_charges_confirmed",False),
    ("supply","competitive"),("export_mode","net_metering"),("meter_count",2),("phase","three"),
    ("voltage","primary"),("voltage_v",480.),("self_assessor",True),("opening_credit_usd",5.),
    ("demand_interval_minutes",15),("offpeak_election",True),("nspl_opt_in",True),("tcrr_opt_out",True),
    ("connected_load_alternative",True),("agreement_minimum_kw",1.),("tax_source",""),
    ("no_demand_elections_confirmed",False),("history_confirmed",False),("history_source","")])
def test_unsupported_account_options_cannot_be_hidden(key,value):
    a,index=fixture("D19");a[key]=value
    with pytest.raises(ValueError):aes.validate_account(a,index)


@pytest.mark.parametrize("damage",["short","order","gap","future","inflated","nan","boolean","stale","state_reset","state_extra"])
def test_actual_history_is_complete_adjacent_bounded_and_nonresettable(damage):
    a,index=fixture("D19")
    state=None
    if damage=="short":a["history"].pop()
    elif damage=="order":a["history"].reverse()
    elif damage=="gap":a["history"][0]["month"]="2024-06-01"
    elif damage=="future":
        for h in a["history"]:h["month"]=str((pd.Timestamp(h["month"])+pd.DateOffset(years=1)).date())
    elif damage=="inflated":a["history"][0]["maximum_kw"]=101.
    elif damage=="nan":a["history"][0]["maximum_kw"]=float("nan")
    elif damage=="boolean":a["history"][0]["maximum_kw"]=True
    elif damage=="stale":
        for h in a["history"]:h["month"]=str((pd.Timestamp(h["month"])-pd.offsets.MonthBegin()).date())
    elif damage=="state_reset":state={"history":a["history"],"next_billing_month":"2025-05-01"}
    else:state={"history":a["history"],"next_billing_month":a["billing_month"],"bank":1.}
    with pytest.raises(ValueError):bill(a,index,state=state)


def test_only_seasonal_prior_actual_peaks_set_the_ratchet():
    a,index=fixture("D19")
    for h in a["history"]:h["maximum_kw"]=20. if h["month"]=="2025-02-01" else 100. if h["month"]=="2025-05-01" else 0.
    out=bill(a,index,8.)
    assert out["metrics"]["actual_30_minute_peak_kw"]==8.
    assert out["metrics"]["ratchet_floor_kw"]==out["metrics"]["billing_demand_kw"]==15.
    assert out["next_state"]["history"][-1]=={"month":"2025-06-01","maximum_kw":8.}
    assert a["history"][-1]["maximum_kw"]==100. # Caller account remains untouched.


def test_current_demand_uses_integrated30_minutes_and_all_kw_are_priced():
    a,index=fixture("D19")
    for h in a["history"]:h["maximum_kw"]=0.
    out=bill(a,index,np.tile([0.,20.],len(index)//2))
    assert out["metrics"]["actual_30_minute_peak_kw"]==out["metrics"]["billing_demand_kw"]==10.
    out=bill(a,index,1.)
    assert out["metrics"]["billing_demand_kw"]==1.
    assert out["unrounded_lines"]["distribution_demand"]==pytest.approx(4.7725904)
    assert out["unrounded_lines"]["transmission_demand"]==pytest.approx(3.9517849)


@pytest.mark.parametrize("damage",["unconfirmed","amount","future_date","pre_effective","missing_source","different_class"])
def test_later_d43_receipt_must_be_exact_independently_resolved_and_prior(damage):
    a,index=fixture("D17","2026-11")
    if damage=="unconfirmed":a["d43_refund_resolved_confirmed"]=False
    elif damage=="amount":a["d43_refund_received_usd"]=14.38
    elif damage=="future_date":a["d43_refund_received_date"]="2026-11-01"
    elif damage=="pre_effective":a["d43_refund_received_date"]="2026-07-31"
    elif damage=="missing_source":a["d43_refund_source"]=""
    else:a["d43_refund_received_usd"]=49.27
    with pytest.raises(ValueError):aes.validate_account(a,index)


@pytest.mark.parametrize("damage",["no_pv","no_approval","no_source","future_pto","missing_pto","grid_charge","export","oversized"])
def test_exact_approved_der_subset_is_separate_from_rate_eligibility(damage):
    a,index=fixture()
    equipment=dict(pv=True,battery=True,pv_dc_kw=5.,pv_ac_kw=4.,battery_kw=3.,renewable_only_charging=True,no_battery_export=True)
    if damage=="no_pv":equipment["pv"]=False
    elif damage=="no_approval":a["der_ordinary_service_confirmed"]=False
    elif damage=="no_source":a["der_eligibility_source"]=""
    elif damage=="future_pto":a["der_activation_date"]="2025-06-02"
    elif damage=="missing_pto":a["der_activation_date"]=""
    elif damage=="grid_charge":equipment["renewable_only_charging"]=False
    elif damage=="export":equipment["no_battery_export"]=False
    else:equipment["pv_dc_kw"]=26.
    with pytest.raises(ValueError):aes.validate_account(a,index,equipment=equipment)
