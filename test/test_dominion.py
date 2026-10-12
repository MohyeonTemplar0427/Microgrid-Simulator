"""Independent filed-rate arithmetic and bounded dispatch scope."""
from copy import deepcopy
import numpy as np
import pandas as pd
import pytest
from src.billing.dominion import bill, on_peak, validate_account, validate_index, PLAN
from src.local_web.pjm_study import defaults
from src.dispatch.dominion import optimize
from src.timeseries.interval_table import build_interval_index


def grid():
    return build_interval_index("2026-09-01", "2026-09-30", "America/New_York", 30).index


def test_independent_high_load_factor_benchmark():
    index=grid(); account=defaults()["account"]
    result=bill(index,np.full(len(index),20.),account)
    # September 2026 has 22 weekdays: 264 on-peak and 456 off-peak hours.
    expected=37.08+90*(4.963+1.169)+14400*.000079
    expected+=20*(264*.020278+456*.009928)
    expected+=20*(4.526+2.313+4.554+1.633+.208+.182+1.581+3.366+.046+1.322)
    expected+=14400*(.037648+.000335+.000967+.001765+.005520)
    expected+=2500*.001565+11900*.001055+10
    assert result["total"]==pytest.approx(expected,abs=1e-8)
    assert sum(result["lines"].values())==result["total"]
    assert result["load_factor"]==1
    assert result["lines"]["rider_CE"]==20*1.633
    assert result["distribution_demand_kw"]==90


def test_low_factor_energy_riders_and_30_minute_peak():
    index=grid();g=np.full(len(index),8.);g[40]=90
    r=bill(index,g,defaults()["account"])
    assert r["peak_kw"]==90
    assert r["lines"]["rider_CE"]==pytest.approx(r["import_kWh"]*.004480)
    assert r["lines"]["rider_T1"]==pytest.approx(90*4.554)


def test_exact_50_percent_boundary_uses_energy():
    index=grid();g=np.full(len(index),45.);g[0]=90;g[1]=0
    r=bill(index,g,defaults()["account"])
    assert r["load_factor"]==.5
    assert r["lines"]["rider_CE"]==pytest.approx(g.sum()*.5*.004480)


def test_partial_cycle_uses_calendar_days_and_prorates_demand():
    index=build_interval_index("2026-09-01","2026-09-15","America/New_York",30).index
    r=bill(index,np.full(len(index),20.),defaults()["account"])
    assert r["lines"]["customer"]==37.08*.5
    assert r["lines"]["distribution_demand"]==90*4.963*.5
    assert r["lines"]["rider_T1"]==20*4.554*.5
    assert r["lines"]["rider_A"]==pytest.approx(7200*.037648)


@pytest.mark.parametrize("day",["2026-08-31","2026-10-12","2025-09-01"])
def test_unverified_effective_dates_reject(day):
    with pytest.raises(ValueError):
        PLAN.version_on(pd.Timestamp(day).date())


def test_peak_and_offpeak_boundaries_do_not_invent_holidays():
    idx=pd.date_range("2026-09-07 09:30",periods=26,freq="30min",tz="America/New_York")
    # Filed GS-2T specifies weekdays without a holiday exclusion.
    mask=on_peak(idx);assert not mask[0] and mask[1] and mask[-2] and not mask[-1]
    assert not on_peak(pd.date_range("2026-09-05 12:00",periods=2,freq="30min",tz="America/New_York")).any()
    assert on_peak(pd.date_range("2026-10-01 07:00",periods=1,freq="30min",tz="America/New_York"))[0]


@pytest.mark.parametrize("patch",[{"history_peaks_kw":[]},{"history_peaks_kw":[500.]*11},{"power_factor":.8},{"facility":"data_center"},{"special_riders":True},{"eligibility_confirmed":False},{"contract_demand_kw":80},{"locality":"richmond"}])
def test_unsupported_accounts_reject(patch):
    with pytest.raises(ValueError):validate_account({**defaults()["account"],**patch})


@pytest.mark.parametrize("change",["missing","duplicate","hourly","naive"])
def test_meter_grid_is_strict(change):
    idx=grid()
    idx={"missing":idx.delete(5),"duplicate":idx.insert(5,idx[5]),"hourly":idx[::2],"naive":idx.tz_localize(None)}[change]
    with pytest.raises(ValueError):validate_index(idx)


def test_optimizer_reconciles_and_wholesale_prices_do_not_change_bill():
    idx=grid();h=idx.hour;weekday=idx.dayofweek<5
    load=np.where(weekday,np.where(h==20,90,np.where((h>=7)&(h<22),30,8)),8)
    pv=np.where((h>=10)&(h<16),20.,0.)
    frame=pd.DataFrame({"timestamp":idx,"native_load_kw":load,"pv_available_kw":pv})
    r=defaults();a=optimize(frame,r["account"],r["battery"])
    altered=frame.copy();altered["wholesale_lmp_per_MWh"]=np.arange(len(frame))*100
    b=optimize(altered,r["account"],r["battery"])
    assert a["bill"]["total"]==pytest.approx(b["bill"]["total"],abs=.001)
    assert a["objective_gap"]<.01
    d=a["dispatch"]
    assert np.max(np.minimum(d.battery_charge_kw,d.battery_discharge_kw))<1e-5
    assert np.max(abs(d.grid_import_kw+d.pv_output_kw+d.battery_discharge_kw-load-d.battery_charge_kw))<1e-5
    assert a["terminal_energy_kWh"]==r["battery"]["energy_kWh"]
    assert a["bill"]["lines"]["distribution_demand"]==90*4.963
    assert a["bill"]["total"]<=bill(idx,np.maximum(load-pv,0),r["account"])["total"]+.01


def test_optimizer_refuses_unproved_load_factor_regime():
    frame=pd.DataFrame({"timestamp":grid(),"native_load_kw":40.,"pv_available_kw":0.})
    with pytest.raises(ValueError,match="50%"):
        optimize(frame,defaults()["account"],defaults()["battery"])
