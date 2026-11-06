"""Delmarva Delaware source arithmetic and bounded account/date scope."""
from copy import deepcopy
from decimal import Decimal as D, ROUND_HALF_UP

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest

from src.billing import delmarva_de as de
from src.billing.delmarva_de_rates import rates_for_month
from src.billing.regional_math import BillingMath


def cycle(month):
    start = pd.Timestamp(month, tz=de.TIMEZONE)
    return pd.date_range(start, start+pd.offsets.MonthBegin(), freq="15min", inclusive="left")


def calculate(plan, month, kwh, **changes):
    index = cycle(month)
    account = {**de.hypothetical_defaults(plan, day=month), **changes}
    imports = np.full(len(index), 4*kwh/len(index))
    de.validate_account(account, index)
    return de.charge_lines(index, imports, np.zeros(len(index)), account, math=BillingMath(index))


# Independent source transcription, in dollars. Numbers are not loaded from
# the executable rate table. The table's December25 column applies only to
# that recorded bill month, with no backfill of earlier monthly QFCP rates.
DEC25 = dict(customer=("13.50", "18.77"), delivery=(".046594", ".062487"),
             supply=(".094804", ".084689"), rps=".005795", qfcp=".003860", pca=".000957",
             ee=(".000476", "0"), dsic=".0532", transmission="5.782620")
SEP26 = dict(customer=("14.72", "19.79"), delivery=(".050660", ".070076"),
             supply=(".111063", ".103985"), rps=".005172", qfcp=".004042", pca=".004997",
             ee=(".000874", "0"), dsic="0", transmission="5.952635")
OCT26 = {**SEP26, "supply": (".114049", ".099489")}


@pytest.mark.parametrize("month,transcribed", [
    ("2025-12-01", DEC25), ("2026-09-01", SEP26), ("2026-10-01", OCT26), ("2026-11-01", OCT26),
])
@pytest.mark.parametrize("plan", ["R", "SGS-ND"])
@pytest.mark.parametrize("kwh", ["0", "500", "1375.25"])
def test_independent_itemized_decimal_bill(month, transcribed, plan, kwh):
    t = transcribed
    column = int(plan == "SGS-ND")
    usage, plc = D(kwh), D(2 if plan == "R" else 4)
    expected = dict(
        distribution_customer=D(t["customer"][column]), distribution_energy=usage*D(t["delivery"][column]),
        supply=usage*D(t["supply"][column]), procurement_cost_adjustment=usage*D(t["pca"]),
        green_energy=usage*D(".000356"), low_income=usage*D(".000095"),
        renewable_portfolio=usage*D(t["rps"]), qualified_fuel_cell=usage*D(t["qfcp"]),
        energy_efficiency=usage*D(t["ee"][column]), edit_credit=D(0), storm_expense=D(0),
        sos_transmission=plc*D(t["transmission"]), ufrc=D(0),
    )
    expected["dsic"] = (expected["distribution_customer"]+expected["distribution_energy"])*D(t["dsic"])
    expected["delaware_public_utility_tax"] = sum(expected.values())*D(".0425" if column else "0")
    result = calculate(plan, month, float(usage))
    assert result["lines"] == pytest.approx({k:float(v) for k,v in expected.items()}, abs=1e-10)
    assert result["is_complete_bill"] and not result["excluded_components"] and result["next_state"] == {}
    assert not result["metrics"]["billing_demand_applied"]
    assert result["metrics"]["transmission_plc_kw"] == float(plc)


@pytest.mark.parametrize("plan,month", [("R","2025-12-01"), ("SGS-ND","2026-09-01"), ("R","2026-11-01")])
def test_symbolic_numeric_parity_and_fixed_transmission_obligation(plan, month):
    index = cycle(month)
    account = de.hypothetical_defaults(plan, day=month)
    power = cp.Variable(nonneg=True)
    imports = cp.promote(power, (len(index),))
    ops = BillingMath(index, convex=True, power_bound=25.)
    ops.register(imports, 0., 25.)
    ops.constraints.append(power == 4*1250/len(index))
    result = de.charge_lines(index, imports, cp.Constant(np.zeros(len(index))), account, math=ops)
    problem = cp.Problem(cp.Minimize(sum(result["lines"].values())), ops.constraints)
    problem.solve(solver="HIGHS")
    assert problem.status == cp.OPTIMAL
    expected = calculate(plan, month, 1250)["lines"]
    for name,line in result["lines"].items():
        assert (line.value if hasattr(line,"value") else line) == pytest.approx(expected[name], abs=1e-8)
    zero = calculate(plan, month, 0)["lines"]
    assert zero["sos_transmission"] == expected["sos_transmission"]


def test_filed_delivery_component_benchmark_and_season_boundary():
    # July8 compliance filing JLM-S 9+3-1 Interim Tables13–14 independently
    # transcribes these ordinary non-space-heating R and SGS-ND base rates.
    for plan,customer,energy in (("R",14.72,.050660),("SGS-ND",19.79,.070076)):
        lines = calculate(plan,"2026-09-01",1000)["lines"]
        assert lines["distribution_customer"] == customer
        assert lines["distribution_energy"] == pytest.approx(1000*energy)
    assert calculate("R","2026-09-01",1000)["lines"]["supply"] == pytest.approx(111.063)
    assert calculate("R","2026-10-01",1000)["lines"]["supply"] == pytest.approx(114.049)


@pytest.mark.parametrize("month", ["2025-01-01","2025-06-01","2025-11-01","2026-01-01",
                                   "2026-03-01","2026-06-01","2026-07-01","2026-08-01",
                                   "2026-12-01","2027-01-01"])
def test_missing_component_or_transition_windows_reject(month):
    with pytest.raises(ValueError, match="unverified"):
        calculate("R",month,500)


@pytest.mark.parametrize("changes", [
    {"sgs_assignment_confirmed":False}, {"sgs_prior_max_month_kwh":3500.},
    {"sgs_prior_max_month_kwh":True}, {"sgs_prior_max_month_kwh":float("nan")},
    {"sgs_classification_source":""}, {"transmission_assignment_confirmed":False},
    {"transmission_plc_kw":None}, {"transmission_plc_kw":float("nan")},
    {"transmission_plc_kw":True}, {"transmission_plc_kw":-1},
    {"transmission_valid_from":"2026-10-01"}, {"transmission_valid_through":"2026-09-29"},
    {"supply":"third_party"}, {"export_mode":"net_metering"},
    {"locality":"wilmington"}, {"voltage":"primary"}, {"phase":"three"},
    {"cycle_kind":"partial"}, {"bill_date":"2026-10-01"},
])
def test_independent_account_facts_reject(changes):
    with pytest.raises(ValueError):
        calculate("SGS-ND","2026-09-01",500,**changes)


def test_native_load_and_meter_envelopes_do_not_establish_classification():
    account = de.hypothetical_defaults("SGS-ND")
    index = cycle("2026-09-01")
    with pytest.raises(ValueError, match="native load"):
        de.validate_native_load(account, np.full(len(index),3500/(len(index)*.25)))
    with pytest.raises(ValueError, match="native load"):
        de.validate_native_load(account,np.full(len(index),10.001))
    with pytest.raises(ValueError, match="envelope"):
        calculate("SGS-ND","2026-09-01",3500)
    zero = calculate("SGS-ND","2026-09-01",0)
    assert zero["metrics"]["transmission_plc_kw"] == 4
    with pytest.raises(ValueError, match="space-heating"):
        calculate("R","2026-09-01",10,rs_no_space_heating_confirmed=False)


def test_dst_complete_cycle_rejection_and_written_non_export_approval():
    index = cycle("2026-11-01")
    account = de.hypothetical_defaults("R",day="2026-11-01")
    assert len(index) == 2884 and calculate("R","2026-11-01",0)["metrics"]["elapsed_hours"] == 721
    for malformed in (index.delete(10),index.insert(10,index[10]),index[1:],index[::2],index.tz_convert("UTC")):
        with pytest.raises(ValueError):
            de.validate_account(account, malformed)
    equip = dict(pv=True,battery=True,renewable_only_charging=True,no_battery_export=True)
    for bad in ({"der_activation_date":"2026-11-02"},{"der_ordinary_service_confirmed":False},
                {"der_eligibility_source":""}):
        with pytest.raises(ValueError):
            de.validate_account({**account,**bad},index,equipment=equip)
    for bad in (dict(equip,renewable_only_charging=False), dict(equip,no_battery_export=False),dict(equip,pv=False)):
        with pytest.raises(ValueError):
            de.validate_account(account,index,equipment=bad)
    with pytest.raises(ValueError,match="exports"):
        de.charge_lines(index,np.zeros(len(index)),np.ones(len(index)),account,math=BillingMath(index))
    with pytest.raises(ValueError,match="state"):
        de.validate_state(account,index,state={"credit":1})


def test_evidence_rates_never_request_wholesale_prices():
    for plan in de.catalog():
        assert plan["supply_arrangements"] == ["sos"]
        assert plan["solar_modes"] == ["non_export"]
        assert plan["coverage"] == [{"start":x,"end":y} for x,y in de.COVERAGE]
    assert rates_for_month("2025-12","R")["transmission_per_kw"] == 5.782620
    assert rates_for_month("2026-11","R")["transmission_per_kw"] == 5.952635
