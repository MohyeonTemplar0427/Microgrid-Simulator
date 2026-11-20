"""Oncor service and invoice clocks, enrollment, data completeness and settlement."""
from copy import deepcopy
from io import BytesIO
import json
from zipfile import ZipFile

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import oncor_tx as model
from src.billing.regional import calculate_cycle
from src.billing.regional_math import BillingMath
from src.local_web.regional_study import defaults, prepare
from test_local_web import service, wait_for_study
from test_regional_study import browser_request
from tools.run_regional_validation import case_request

UTILITY = model.UTILITY

def month(start):
    t = pd.Timestamp(start, tz=model.TIMEZONE)
    return pd.date_range(t, t + pd.offsets.MonthBegin(), freq="15min", inclusive="left")

@pytest.mark.parametrize("day,intervals", [("2025-03-01", 2972), ("2025-11-01", 2884)])
def test_dst_missing_and_duplicate_intervals(day, intervals):
    idx = month(day)
    assert len(idx) == intervals
    a = model.hypothetical_defaults("NEC-RES", day=day)
    model.validate_account(a, idx)
    for bad in [idx.delete(45), idx.insert(45, idx[45]), idx.tz_convert("UTC"), idx[::2]]:
        with pytest.raises(ValueError, match="consecutive"):
            model.validate_account(a, bad)

def test_variable_plan_uses_issue_date_for_supply_and_service_invoice_for_delivery():
    idx = month("2025-09-01")
    a = model.hypothetical_defaults("NEC-SMALL", day="2025-09-01")
    results = []
    for day in ["2025-10-02", "2025-10-03"]:
        a["bill_date"] = day
        results.append(calculate_cycle(UTILITY, idx, np.ones(len(idx)), np.zeros(len(idx)), a))
    left, right = results
    assert [r["metrics"]["rep_usd_per_kwh"] for r in results] == [.0841, .0781]
    assert left["metrics"]["oncor_bill_date"] == right["metrics"]["oncor_bill_date"] == "2025-09-30"
    assert all(right["lines"][k] == v for k, v in left["lines"].items() if k.startswith("oncor_"))
    assert (left["unrounded_lines"]["rep_energy"] - right["unrounded_lines"]["rep_energy"]) == pytest.approx(720*.006)

@pytest.mark.parametrize("plan,day", [("NEC-RES","2025-01-01"), ("NEC-RES","2026-10-01"),
    ("NEC-SMALL","2025-04-01"), ("constellation_381771","2025-12-01"),
    ("constellation_381771","2026-05-01"), ("constellation_4930520","2026-03-01")])
def test_unavailable_months_cannot_produce_bills(plan, day):
    with pytest.raises(ValueError):
        model.validate_account(model.hypothetical_defaults(plan, day=day), month(day))

@pytest.mark.parametrize("field,value", [
    ("supply","oncor_texas"), ("export_mode","net_metering"), ("opening_credit_kwh",3),
    ("phase","three"), ("eligibility_confirmed",1), ("prior_max_kw",10.), ("prior_max_kw",None),
    ("tax_source",""), ("tax_status_confirmed",False), ("puca_treatment","separately_reimbursed"),
    ("full_monthly_charges_confirmed",False), ("tax_treatment","dallas")])
def test_documented_class_supplier_and_tax_boundaries(field, value):
    a = model.hypothetical_defaults("NEC-SMALL", day="2025-09-01")
    a[field] = value
    with pytest.raises(ValueError):
        model.validate_account(a, month("2025-09-01"))

def test_free_of_export_credit_and_retail_contract_substitution():
    idx = month("2025-09-01")
    n = len(idx)
    a = model.hypothetical_defaults("constellation_381771", day="2025-09-01")
    for kw in [np.nan, np.inf, -1.]:
        with pytest.raises(ValueError):
            calculate_cycle(UTILITY, idx, np.full(n, kw), np.zeros(n), a)
    for extra in [dict(state={"credit": 0}), dict(equipment={"pv": True, "pv_ac_kw": 1})]:
        with pytest.raises(ValueError):
            calculate_cycle(UTILITY, idx, np.ones(n), np.zeros(n), a, **extra)
    with pytest.raises(ValueError, match="zero export"):
        calculate_cycle(UTILITY, idx, np.ones(n), np.ones(n), a)
    with pytest.raises(ValueError, match="unexpired"):
        model.validate_account({**a, "contract_start": "2025-09-02"}, idx)
    for peak in [10., np.nan, -1.]:
        with pytest.raises(ValueError):
            model.validate_native_load({"tariff": "NEC-SMALL"}, [peak])

def test_numeric_symbolic_parity_for_separate_assessment_and_taxable_business():
    idx = month("2025-09-01")
    for plan in ("NEC-SMALL", "constellation_381771"):
        a = model.hypothetical_defaults(plan, day="2025-09-01")
        actual = calculate_cycle(UTILITY, idx, np.ones(len(idx)), np.zeros(len(idx)), a)
        symbolic = model.charge_lines(idx, cp.Constant(np.ones(len(idx))), cp.Constant(np.zeros(len(idx))), a,
                                      math=BillingMath(idx, convex=True, power_bound=5.))
        amounts = {k: float(getattr(v, "value", v)) for k,v in symbolic["lines"].items()}
        assert amounts == pytest.approx(actual["unrounded_lines"])
        assert actual["is_complete_bill"]
        partial = calculate_cycle(UTILITY, idx, np.ones(len(idx)), np.zeros(len(idx)), {**a, "tax_treatment": "pretax_subtotal"})
        assert not partial["is_complete_bill"] and partial["excluded_components"] == list(model.EXCLUSIONS)
        assert "puc_assessment_reimbursement" not in partial["lines"] and "texas_state_sales_tax" not in partial["lines"]

def test_browser_contract_rejects_wrong_supplier_wholesale_carbon_and_cycle_overrides():
    r = case_request(UTILITY, "commercial", "monthly", plan="NEC-SMALL")
    rebuilt = browser_request(r)
    assert rebuilt == {**r, "name": "Untitled study"}
    assert rebuilt["regional_account"]["retail_supplier"] == model.NEC
    assert rebuilt["regional_account"]["grid_operator"] == "ERCOT" and rebuilt["timezone"] == model.TIMEZONE
    for field, bad in [("retail_supplier", UTILITY), ("grid_operator","PJM"),
                       ("wholesale_pricing_location",{"pnode_id":123, "pnode_name":"Fake", "zone":"", "source":"Test"})]:
        altered = deepcopy(rebuilt)
        altered["regional_account"][field] = bad
        with pytest.raises(ValueError):
            prepare(altered)
    for k,v in [("carbon",{"source":"electricity_maps","region":"US-MIDA-PJM"}),
                ("tariff_comparisons",["NEC-RES"])]:
        with pytest.raises(ValueError):
            prepare({**rebuilt, k:v})
    altered = deepcopy(rebuilt)
    altered["billing_cycles"][0]["account_overrides"] = {"puca_treatment":"unverified"}
    with pytest.raises(ValueError, match="overrides"):
        prepare(altered)
    real = defaults(UTILITY, "commercial", "NEC-SMALL")
    real["account"] = model.defaults("NEC-SMALL")
    with pytest.raises(ValueError):
        prepare(real)

def test_queued_oncor_saved_request_and_exports(service):
    _, call, headers = service
    req = browser_request(case_request(UTILITY, "commercial", "monthly", plan="NEC-SMALL"))
    base = "/api/studies/" + call("/api/v1/regional/studies", req, headers)["id"]
    completed = wait_for_study(call, base.split("/")[-1])
    assert completed["status"] == "completed", completed.get("error")
    result = completed["result"]
    criteria = result["billing"]["pv_battery"][0]
    assert criteria["metrics"]["retail_supplier"] == model.NEC
    assert criteria["is_complete_bill"] and result["ac_validation"]["all_intervals_feasible"]
    with ZipFile(BytesIO(call(base+"/tables.zip"))) as z:
        assert json.loads(z.read("result-manifest.json")) == result
        for table in result["tables"]:
            filename = table["id"] + ".csv"
            assert z.read(filename) == call(base+"/tables/"+filename)
    call(base+"/save", {"name":"Oncor small-commercial acceptance"}, headers)
    assert call(base)["saved"] and browser_request(call(base+"/request.json")) == req


def test_later_documented_fixed_activation_and_residential_meter_assignment():
    a = model.hypothetical_defaults("constellation_381771", day="2026-05-01")
    a.update(contract_start="2025-06-01", contract_end="2026-05-31")
    model.validate_account(a, month("2026-05-01"))
    a = model.hypothetical_defaults("NEC-RES", day="2025-05-01")
    with pytest.raises(ValueError, match="non-demand"):
        model.validate_account({**a, "non_demand_meter_confirmed": False}, month("2025-05-01"))


DEMAND_PLAN = "ambit_tsc24_20250510_gt10"


@pytest.mark.parametrize("usage,fee", [(1249.99, 9.99), (1250., 0.), (1250.01, 0.)])
def test_ambit_usage_fee_and_distinct_demand_determinants(usage, fee):
    idx = month("2025-09-01")
    a = model.hypothetical_defaults(DEMAND_PLAN, day="2025-09-01")
    a["prior_ncp_kw"] = [20.] + [14.] * 10
    imports = np.zeros(len(idx))
    imports[:415] = 12.0  # 1,245 kWh, with an actual peak of 12 kW
    imports[415:417] = np.round((usage - 1245.) * 2, 2)
    bill = calculate_cycle(UTILITY, idx, imports, np.zeros(len(idx)), a)
    assert bill["unrounded_lines"]["rep_low_usage_fee"] == fee
    assert bill["unrounded_lines"]["rep_energy"] == pytest.approx(usage * .115)
    assert bill["unrounded_lines"]["oncor_distribution_system_charge"] == pytest.approx(12 * 5.121040)
    assert bill["unrounded_lines"]["oncor_nuclear_decommissioning"] == pytest.approx(16 * .045)
    assert bill["next_state"]["prior_ncp_kw"] == [14.] * 10 + [12.]
    assert bill["metrics"]["rider_billing_kw"] == 16
    assert not bill["is_complete_bill"]
    symbolic = model.charge_lines(idx, cp.Constant(imports), cp.Constant(np.zeros(len(idx))), a,
                                  math=BillingMath(idx, convex=True, power_bound=20.))
    assert {k: float(getattr(v, "value", v)) for k, v in symbolic["lines"].items()} == pytest.approx(bill["unrounded_lines"])

    following = month("2025-10-01")
    b = dict(a, billing_month="2025-10-01", bill_date="2025-10-31")
    second = calculate_cycle(UTILITY, following, np.full(len(following), 8.), np.zeros(len(following)), b, state=bill["next_state"])
    assert second["metrics"]["rider_billing_kw"] == pytest.approx(11.2)
    with pytest.raises(ValueError, match="immediately before"):
        calculate_cycle(UTILITY, following, np.zeros(len(following)), np.zeros(len(following)), b)


@pytest.mark.parametrize("field,value", [
    ("prior_ncp_kw", [10.] * 11), ("prior_ncp_kw", [20.001] * 11), ("prior_ncp_kw", [12.] * 10),
    ("prior_ncp_kw", [True] + [18.] * 10), ("prior_ncp_kw", [float("nan")] * 11),
    ("history_through_month", "2025-07-01"), ("demand_scope_confirmed", False),
    ("small_business_contract_confirmed", False), ("tax_treatment", "unincorporated_state_only")])
def test_ambit_demand_requires_supported_documented_account(field, value):
    idx = month("2025-09-01")
    a = model.hypothetical_defaults(DEMAND_PLAN, day="2025-09-01")
    with pytest.raises(ValueError):
        calculate_cycle(UTILITY, idx, np.ones(len(idx)), np.zeros(len(idx)), {**a, field: value})


def test_secondary_class_boundaries_and_residential_enrollment():
    idx = month("2025-10-01")
    for plan, ceiling in [(DEMAND_PLAN, 20.), ("ambit_tsc12_20250510_le10", 10.)]:
        a = model.hypothetical_defaults(plan, day="2025-10-01")
        model.validate_native_load(a, [ceiling])
        with pytest.raises(ValueError):
            model.validate_native_load(a, [ceiling + .001])
        with pytest.raises(ValueError):
            model.validate_account(a, idx, {"pv": True})
    a = model.hypothetical_defaults("fourchange_onerta24mac_o", day="2025-10-01")
    with pytest.raises(ValueError, match="enrollment"):
        model.validate_account({**a, "retail_enrollment_confirmed": False}, idx)
    with pytest.raises(ValueError, match="positive"):
        calculate_cycle(UTILITY, idx, np.zeros(len(idx)), np.zeros(len(idx)), a)


def test_queued_fixed_demand_history_and_subtotal_exports(service):
    _, call, headers = service
    req = browser_request(case_request(UTILITY, "commercial", "custom", plan=DEMAND_PLAN,
                                       start_date="2026-05-01", end_date="2026-06-30"))
    base = "/api/studies/" + call("/api/v1/regional/studies", req, headers)["id"]
    study = wait_for_study(call, base.split("/")[-1])
    assert study["status"] == "completed", study.get("error")
    result = study["result"]
    first, second = result["billing"]["grid_only"]
    assert first["next_state"]["prior_ncp_kw"][1:] == second["next_state"]["prior_ncp_kw"][:-1]
    assert [row["metrics"]["oncor_monthly_usd"] for row in (first, second)] == [32.43, 44.99]
    assert not second["is_complete_bill"] and result["ac_validation"]["all_intervals_feasible"]
    with ZipFile(BytesIO(call(base + "/tables.zip"))) as archive:
        assert json.loads(archive.read("result-manifest.json")) == result
        for table in result["tables"]:
            filename = table["id"] + ".csv"
            assert archive.read(filename) == call(base + "/tables/" + filename)
    call(base + "/save", {"name": "Ambit demand rollover"}, headers)
    assert call(base)["saved"] and browser_request(call(base + "/request.json")) == req
