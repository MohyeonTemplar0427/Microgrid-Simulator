"""Independent DEC tariff arithmetic, boundaries, and non-export dispatch."""
from copy import deepcopy
from decimal import Decimal as D, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import delaware_coop_de as dec
from src.billing import regional
from src.billing.delaware_coop_de_rates import rates_for_month
from src.billing.regional_math import BillingMath
from src.dispatch.regional import optimize_cycle


def cycle(month):
    start = pd.Timestamp(month, tz=dec.TIMEZONE)
    return pd.date_range(start, start+pd.offsets.MonthBegin(), freq="15min", inclusive="left")


def independent(plan, month, kwh):
    """Literal source transcription; does not import production tariff data."""
    e = D(str(kwh))
    commercial = plan == "GS"
    result = dict(distribution_customer=D("30" if commercial else "28"),
                  distribution_energy=e*D(".022498" if commercial else ".021400"),
                  renewable_resource_fund=e*D(".000178"),
                  supply_energy=min(e,D("700"))*D(".111090" if commercial else ".101600")
                                +max(e-D("700"),D(0))*D(".101090" if commercial else ".081600"),
                  power_cost_adjustment=e*D(".012161" if month >= "2026-05-01" else "-.001500"))
    result["delaware_public_utility_tax"] = sum(result.values())*D(".0425" if commercial else "0")
    return result


def bill(plan, month, kwh, **changes):
    index = cycle(month)
    account = {**dec.hypothetical_defaults(plan, day=month), **changes}
    dec.validate_account(account, index)
    return dec.charge_lines(index, np.full(len(index),4*kwh/len(index)), np.zeros(len(index)),
                            account, math=BillingMath(index))


@pytest.fixture
def register(monkeypatch):
    # Keep this focused adapter test independent of shared registry edit timing.
    monkeypatch.setitem(regional.UTILITIES, dec.UTILITY,
                        dict(module="delaware_coop_de", state="DE", zone="DPL", timezone=dec.TIMEZONE))


@pytest.mark.parametrize("plan", ("R","GS"))
@pytest.mark.parametrize("month", ("2025-01-01","2026-04-01","2026-05-01","2026-10-01"))
@pytest.mark.parametrize("kwh", (0.,100.,699.99,700.,700.01,1000.,1837.21))
def test_independent_decimal_component_bill(plan, month, kwh):
    result = bill(plan, month, kwh)
    expected = {key:float(value) for key,value in independent(plan,month,kwh).items()}
    assert result["lines"] == pytest.approx(expected, abs=1e-9)
    assert result["is_complete_bill"] and result["excluded_components"] == []
    assert result["next_state"] == {} and result["rate_evidence_status"] == "verified"
    assert result["metrics"]["billing_demand_applied"] is False


@pytest.mark.parametrize("plan", ("R","GS"))
@pytest.mark.parametrize("month", [f"2025-{m:02}-01" for m in range(1,13)]+[f"2026-{m:02}-01" for m in range(1,11)])
def test_every_supported_month_and_source_stack(plan, month):
    result = bill(plan,month,1517.41)
    assert result["lines"] == pytest.approx({k:float(v) for k,v in independent(plan,month,1517.41).items()}, abs=1e-9)
    assert result["metrics"]["billing_month"] == month
    assert len(result["rate_sources"]) == 5


@pytest.mark.parametrize("plan,month,kwh", [
    ("R","2025-03-01",0.), ("GS","2025-03-01",0.),
    ("R","2026-04-01",699.99), ("GS","2026-04-01",699.99),
    ("R","2026-05-01",700.), ("GS","2026-05-01",700.),
    ("R","2026-10-01",700.01), ("GS","2026-10-01",700.01),
    ("R","2025-11-01",1837.21), ("GS","2025-11-01",1837.21),
])
def test_exact_symbolic_numeric_parity_through_decreasing_tier(plan, month, kwh):
    index, account = cycle(month), dec.hypothetical_defaults(plan,day=month)
    power = cp.Variable(nonneg=True)
    imports = cp.promote(power,(len(index),))
    ops = BillingMath(index,convex=True,power_bound=50.)
    ops.register(imports,0.,50.)
    ops.constraints.append(power == 4*kwh/len(index))
    result = dec.charge_lines(index,imports,cp.Constant(np.zeros(len(index))),account,math=ops)
    problem = cp.Problem(cp.Minimize(sum(result["lines"].values())),ops.constraints)
    problem.solve(solver="HIGHS")
    assert problem.status == cp.OPTIMAL
    for name,value in result["lines"].items():
        numeric = value.value if hasattr(value,"value") else value
        assert numeric == pytest.approx(float(independent(plan,month,kwh)[name]),abs=1e-8)
    if kwh == 0:
        assert problem.value == pytest.approx(31.275 if plan == "GS" else 28.)


def test_pca_change_units_and_tax_base():
    old, new = (bill("R",month,1000)["lines"] for month in ("2026-04-01","2026-05-01"))
    assert old["power_cost_adjustment"] == pytest.approx(-1.5)
    assert new["power_cost_adjustment"] == pytest.approx(12.161)
    # The official notice's prose calls these decimals cents. The tariff has
    # dollar signs and the notice's ~$13 illustration confirms dollars/kWh.
    assert sum(new.values())-sum(old.values()) == pytest.approx(13.661)
    gs = bill("GS","2026-05-01",1000)["lines"]
    assert gs["delaware_public_utility_tax"] == pytest.approx(7.3493975)
    assert sum(gs.values()) == pytest.approx(180.2763975)
    assert bill("R","2026-05-01",0)["lines"]["distribution_customer"] == 28.


@pytest.mark.parametrize("month", ("2024-12-01","2026-11-01","2026-12-01","2027-01-01","2025-07-02"))
def test_unknown_periods_fail_closed(month):
    with pytest.raises(ValueError,match="unverified"):
        rates_for_month(month,"R")


@pytest.mark.parametrize("month", ("2025-13-01","20250701","2025-07",None,True))
def test_malformed_rate_date_rejects(month):
    with pytest.raises(ValueError):
        rates_for_month(month,"R")


@pytest.mark.parametrize("changes", [
    {"gs_retained_assignment_confirmed":False}, {"gs_contract_confirmed":False},
    {"gs_monthly_demands_kw":[8.]*11}, {"gs_monthly_demands_kw":[8.]*11+[50.]},
    {"gs_monthly_demands_kw":[8.]*11+[float("nan")]}, {"gs_monthly_demands_kw":[8.]*11+[True]},
    {"gs_monthly_demands_kw":[8.]*11+[-1.]}, {"gs_history_through_month":"2026-05-01"},
    {"gs_review_source":""}, {"account_source":""}, {"cycle_source":""},
    {"eligibility_confirmed":False}, {"ordinary_service_confirmed":False},
    {"full_monthly_charges_confirmed":False}, {"local_charges_confirmed":False},
    {"tax_status_confirmed":False}, {"motor_power_factor_confirmed":False},
    {"locality":"kent_unincorporated"}, {"phase":"three"}, {"voltage":"primary"},
    {"voltage_v":208.}, {"meter_count":True}, {"supply":"third_party"},
    {"export_mode":"net_metering"}, {"opening_credit_usd":1.},
    {"rate_evidence_mode":"provisional"}, {"provisional_assumptions_accepted":True},
    {"cycle_kind":"initial"}, {"bill_date":"2026-08-01"}, {"billing_month":"2026-08-01"},
])
def test_independent_account_and_classification_rejections(changes):
    with pytest.raises(ValueError):
        bill("GS","2026-07-01",0,**changes)


def test_domestic_use_contract_and_native_envelope():
    with pytest.raises(ValueError,match="domestic"):
        bill("R","2026-07-01",1000,residential_use_confirmed=False)
    account = dec.hypothetical_defaults("GS")
    dec.validate_native_load(account,np.array([49.9]))
    for load in (np.array([50.]),np.array([np.nan]),np.array([-1.]),np.array([])):
        with pytest.raises(ValueError,match="native load"):
            dec.validate_native_load(account,load)
    # Lower imports do not cure an independent bad assignment/history.
    with pytest.raises(ValueError):
        bill("GS","2026-07-01",0,gs_monthly_demands_kw=[50.]*12)


def test_defaults_require_facts_and_hypothetical_accounts_are_explicit():
    for plan in ("R","GS"):
        defaults = dec.defaults(plan)
        assert all(defaults[key] is False for key in dec.CONFIRMATIONS)
        assert defaults["der_ordinary_service_confirmed"] is False
        assert defaults["battery_interconnection_confirmed"] is False
        assert dec.hypothetical_defaults(plan)["hypothetical_account"] is True
    assert {plan["id"] for plan in dec.catalog()} == {"R","GS"}
    assert dec.catalog()[0]["coverage"] == [dict(start="2025-01-01",end="2026-10-31")]


@pytest.mark.parametrize("month,hours", (("2025-03-01",743.),("2025-11-01",721.),("2026-03-01",743.)))
def test_dst_complete_calendar_hours(month,hours):
    assert bill("R",month,0)["metrics"]["elapsed_hours"] == hours


def test_missing_duplicate_partial_naive_and_other_timezone_reject():
    index, account = cycle("2025-11-01"), dec.hypothetical_defaults("R",day="2025-11-01")
    bad = (index.delete(100), index.insert(100,index[100]), index[1:],index[::2],
           index.tz_convert("UTC"), index.tz_localize(None), index.insert(1,pd.NaT))
    for malformed in bad:
        with pytest.raises(ValueError):
            dec.validate_account(account,malformed)


@pytest.mark.parametrize("change", [
    {"der_ordinary_service_confirmed":False}, {"der_eligibility_source":""},
    {"der_activation_date":"2026-07-02"}, {"der_activation_date":"2026-7-1"},
    {"battery_interconnection_confirmed":False},
])
def test_final_exact_non_export_and_battery_approvals_required(change):
    index, account = cycle("2026-07-01"), dec.hypothetical_defaults("R")
    equipment = dict(pv=True,pv_dc_kw=6.,battery=True,renewable_only_charging=True,no_battery_export=True)
    dec.validate_account(account,index,equipment)
    with pytest.raises(ValueError):
        dec.validate_account({**account,**change},index,equipment)


@pytest.mark.parametrize("change", [
    {"pv":False}, {"pv_dc_kw":100.}, {"pv_dc_kw":float("nan")},
    {"pv_dc_kw":True}, {"pv_dc_kw":None}, {"pv_dc_kw":0.},
    {"renewable_only_charging":False}, {"no_battery_export":False},
])
def test_der_size_storage_only_and_unsupported_operating_modes_reject(change):
    equipment = dict(pv=True,pv_dc_kw=6.,battery=True,renewable_only_charging=True,no_battery_export=True)
    with pytest.raises(ValueError):
        dec.validate_account(dec.hypothetical_defaults("R"),cycle("2026-07-01"),{**equipment,**change})


def test_flow_export_state_and_rounding_rejections(register):
    index, account = cycle("2026-07-01"), dec.hypothetical_defaults("R")
    zero = np.zeros(len(index))
    for imp,exp in ((zero,np.ones(len(index))), (np.full(len(index),25.01),zero),
                    (np.full(len(index),np.nan),zero),(zero[:-1],zero), (np.full(len(index),-1.),zero)):
        with pytest.raises(ValueError):
            regional.calculate_cycle(dec.UTILITY,index,imp,exp,account)
    with pytest.raises(ValueError,match="state"):
        dec.validate_state(account,index,{"credit":1.})
    result = regional.calculate_cycle(dec.UTILITY,index,np.ones(len(index)),zero,account)
    expected = independent("R","2026-07-01",744.)
    assert result["unrounded_lines"] == pytest.approx({k:float(v) for k,v in expected.items()})
    rounded = {key:float(value.quantize(D(".01"),rounding=ROUND_HALF_UP)) for key,value in expected.items()}
    assert result["lines"] == rounded
    assert result["total_usd"] == pytest.approx(sum(rounded.values()))


@pytest.mark.parametrize("month", ("2025-11-01","2026-07-01"))
def test_frozen_independent_literal_benchmark_receipt(month):
    root = Path(__file__).resolve().parents[1]
    fixture = json.loads((root/"docs/utility_sources/delaware_coop_de/independent_benchmarks.json").read_text())
    for row in fixture["cases"]:
        if row["month"] == month:
            result = bill(row["plan"],month,float(row["kwh"]))
            assert result["lines"] == pytest.approx({k:float(v) for k,v in row["unrounded_lines_usd"].items()},abs=1e-9)
            assert sum(result["lines"].values()) == pytest.approx(float(row["unrounded_total_usd"]),abs=1e-9)


def test_tracked_source_ledger_and_visual_transcription_hashes():
    root = Path(__file__).resolve().parents[1]
    folder = root/"docs/utility_sources/delaware_coop_de"
    ledger = json.loads((folder/"sources.json").read_text())
    assert ledger["utility_id"] == dec.UTILITY
    assert ledger["monthly_intersections"][0]["month"] == "2025-01-01"
    assert ledger["monthly_intersections"][-1]["month"] == "2026-10-01"
    assert len(ledger["monthly_intersections"]) == 22
    for source in ledger["tracked_snapshots"]:
        assert hashlib.sha256((folder/source["file"]).read_bytes()).hexdigest() == source["sha256"]
    for row in ledger["monthly_intersections"]:
        assert rates_for_month(row["month"],"R")["pca"] == float(row["pca_dollars_per_kwh"])


@pytest.mark.parametrize("plan,month", (("R","2025-11-01"),("GS","2026-07-01")))
def test_non_export_pv_battery_dispatch_itemized_rebill_and_soc(register,plan,month):
    index = cycle(month)
    hour = index.hour.to_numpy()+index.minute.to_numpy()/60
    load = np.where((hour>=17)&(hour<22),3.,.9)
    pv = np.maximum(0.,np.sin((hour-6)*np.pi/12))*4.
    data = pd.DataFrame(dict(timestamp=index,native_load_kw=load,pv_available_kw=pv))
    account = dec.hypothetical_defaults(plan,day=month)
    battery = dict(capacity_kWh=6.,energy_kWh=3.,SOC_min=.1,SOC_max=.9,
                   max_charge_kw=2.,max_discharge_kw=2.,charge_efficiency=.95,discharge_efficiency=.95)
    equipment = dict(pv=True,pv_dc_kw=5.,pv_ac_kw=4.,battery=True,battery_kw=2.,
                     renewable_only_charging=True,no_battery_export=True)
    before = deepcopy(account)
    result = optimize_cycle(data,dec.UTILITY,account,battery,equipment=equipment,
                            terminal_energy=3.,time_limit=25.)
    d = result["dispatch"]
    np.testing.assert_allclose(d.grid_import_kw+d.pv_output_kw+d.battery_discharge_kw,
                               d.native_load_kw+d.battery_charge_kw+d.grid_export_kw,atol=1e-5)
    np.testing.assert_allclose(d.pv_output_kw+d.pv_curtailed_kw,d.pv_available_kw,atol=1e-5)
    assert d.grid_export_kw.abs().max() <= 1e-5
    assert np.minimum(d.battery_charge_kw,d.battery_discharge_kw).max() <= 1e-5
    assert (d.battery_charge_kw-d.pv_output_kw).max() <= 1e-5
    energy = d.energy_kWh.to_numpy()
    end = energy+.25*(d.battery_charge_kw.to_numpy()*.95-d.battery_discharge_kw.to_numpy()/.95)
    np.testing.assert_allclose(energy[1:],end[:-1],atol=1e-5)
    assert energy[0] == pytest.approx(3.) and end[-1] == pytest.approx(3.,abs=1e-5)
    assert min(energy.min(),end.min()) >= .6-1e-5
    assert max(energy.max(),end.max()) <= 5.4+1e-5
    kwh = d.grid_import_kw.sum()*.25
    assert result["bill"]["unrounded_lines"] == pytest.approx({k:float(v) for k,v in independent(plan,month,kwh).items()},abs=1e-8)
    assert result["next_state"] == {}
    assert result["reconciliation_difference_usd"] <= 1e-4
    assert result["cost_optimum_proven"] is True
    assert result["bill"]["metrics"]["rounded_cash_optimum_claimed"] is False
    assert account == before
