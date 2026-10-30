"""Literal filed Duquesne prices, independently composed with Decimal.

The expected arithmetic imports no production rate table or BillingMath. Its
inputs come from the preserved Supplement83/85/93/94/102/105 and rider pages.
"""
from decimal import Decimal as D, ROUND_HALF_UP

import cvxpy as cp
import numpy as np
import pandas as pd
import pytest


MONTHS = [
    ("2025-01",744),("2025-02",672),("2025-03",743),("2025-04",720),
    ("2025-05",744),("2025-06",720),("2025-07",744),("2025-08",744),
    ("2025-09",720),("2025-10",744),("2025-11",721),("2025-12",744),
    ("2026-01",744),("2026-02",672),("2026-03",743),("2026-04",720),
    ("2026-05",744),("2026-06",720),("2026-07",744),("2026-08",744),
    ("2026-09",720),("2026-10",744),
]


def literal_prices(plan, month):
    """Independent factual fixture; never use the implementation's rate helper."""
    res = plan == "RS"
    if month <= "2025-05":
        dss, tsc = ((".084472", ".024048") if res else (".077009", ".015625"))
    elif month <= "2025-11":
        dss, tsc = ((".097093", ".027187") if res else (".084471", ".018386"))
    elif month <= "2026-05":
        dss, tsc = ((".110275", ".027187") if res else (".097016", ".018386"))
    else:
        dss, tsc = ((".109568", ".031841") if res else (".096754", ".012015"))
    eec = ((".0021" if res else ".0020") if month <= "2025-05" else
           (".0019" if res else "-.0006") if month <= "2026-05" else
           (".0017" if res else ".0009"))
    dsic = ("-.001" if month <= "2025-03" else ".0002" if month <= "2025-12" else
            ".0049" if month <= "2026-03" else ".0139" if month <= "2026-06" else
            ".0217" if month <= "2026-09" else ".0336")
    return {"customer": D("13" if res else "18"),
        "distribution": D(".082479" if res else ".084601"),
        "usc": D((".01549" if month <= "2025-12" else ".01599") if res else "0"),
        "eec": D(eec), "smart_meter": D("0"), "rmes": D("0"),
        "dsic": D(dsic), "stas1": D("-.001278" if month <= "2025-12" else "-.000964"),
        "stas2": D("0"), "dss": D(dss), "tsc": D(tsc)}


def literal_lines(plan, month, energy):
    r = literal_prices(plan, month)
    e = D(str(energy))
    lines = {"distribution_customer": r["customer"],
        "distribution_energy": e*r["distribution"],
        "retail_market_enhancement": r["rmes"], "universal_service": e*r["usc"],
        "energy_efficiency": e*r["eec"], "smart_meter": r["smart_meter"]}
    # Filed DSIC excludes STAS and retail supply/transmission; it retains the
    # signed EEC rider. Appendix A excludes transmission from STAS and minimum.
    distribution = sum(lines.values())
    lines["distribution_dsic"] = distribution*r["dsic"]
    lines["distribution_state_tax_adjustment"] = (distribution+lines["distribution_dsic"])*r["stas1"]
    lines["default_service_supply"] = e*r["dss"]
    lines["all_service_state_tax_adjustment"] = sum(lines.values())*r["stas2"]
    lines["retail_transmission"] = e*r["tsc"]
    lines["sales_tax"] = D("0") if plan == "RS" else sum(lines.values())*D(".06")
    return lines


def fixture(plan, month):
    from src.billing import duquesne_pa as dlc
    from src.timeseries import build_interval_index
    first=month+"-01"
    end=str((pd.Timestamp(first)+pd.offsets.MonthEnd()).date())
    return dlc.hypothetical_defaults(plan,day=first),build_interval_index(first,end,"America/New_York",15).index


@pytest.mark.parametrize("plan",["RS","GS"])
@pytest.mark.parametrize("month,hours",MONTHS)
def test_literal_one_kw_complete_month_all_dated_windows(plan,month,hours):
    from src.billing import duquesne_pa as dlc
    from src.billing.regional import calculate_cycle
    from src.billing.regional_math import BillingMath
    account,index=fixture(plan,month)
    expected=literal_lines(plan,month,hours)
    dlc.validate_account(account,index)
    raw=dlc.charge_lines(index,np.ones(len(index)),np.zeros(len(index)),account,math=BillingMath(index))
    assert len(index)==hours*4
    assert raw["metrics"]["elapsed_hours"]==hours
    assert set(raw["lines"])==set(expected)
    for key,amount in expected.items():
        assert raw["lines"][key]==pytest.approx(float(amount),abs=1e-9),key
    assert not {"gross_receipts_tax","merchant_function","wholesale_lmp","pjm_capacity","nspl_demand"}&set(raw["lines"])
    bill=calculate_cycle("duquesne_light_pennsylvania",index,np.ones(len(index)),np.zeros(len(index)),account)
    cents={k:v.quantize(D(".01"),rounding=ROUND_HALF_UP) for k,v in expected.items()}
    assert bill["lines"]==pytest.approx({k:float(v) for k,v in cents.items()},abs=1e-9)
    assert bill["total_usd"]==pytest.approx(float(sum(cents.values())),abs=1e-9)


@pytest.mark.parametrize("plan",["RS","GS"])
@pytest.mark.parametrize("month",["2025-03","2025-06","2025-12","2026-06","2026-10"])
def test_literal_fixed_flow_symbolic_component_parity(plan,month):
    from src.billing import duquesne_pa as dlc
    from src.billing.regional_math import BillingMath
    account,index=fixture(plan,month)
    power=.95+.2*(np.arange(len(index))%19)/18
    energy=D(str(float(power.sum()*.25)))
    expected=literal_lines(plan,month,energy)
    x=cp.Variable(len(index));y=cp.Variable(len(index))
    math=BillingMath(index,convex=True,power_bound=2.)
    math.register_power(x,np.zeros(len(index)),np.full(len(index),2.))
    out=dlc.charge_lines(index,x,y,account,math=math)
    problem=cp.Problem(cp.Minimize(sum(out["lines"].values())),[x==power,y==0,*math.constraints])
    problem.solve(solver="SCIPY")
    assert problem.status in ("optimal","optimal_inaccurate")
    for key,amount in expected.items():
        actual=out["lines"][key]
        assert float(actual.value if hasattr(actual,"value") else actual)==pytest.approx(float(amount),abs=1e-7),key
