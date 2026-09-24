from copy import deepcopy
import numpy as np
import pandas as pd
import pytest
from test_municipal import account, frame, history
from src.dispatch.municipal import optimize_storage
from src.billing.municipal import bill_cycle

BATTERY=dict(capacity_kWh=200,energy_kWh=100,max_charge_kw=40,max_discharge_kw=40,
             SOC_min=.1,SOC_max=.9,charge_efficiency=.95,discharge_efficiency=.95)

def optimize(tariff, data, a, **kwargs):
    return optimize_storage(tariff,data,cycle_start=data.timestamp.iloc[0],
        cycle_end=data.timestamp.iloc[-1]+pd.Timedelta(minutes=15),
        account=a,battery=BATTERY,**kwargs)

@pytest.mark.parametrize('utility,schedule', [('amp','A-2'),('svp','CB-1')])
def test_peak_shaving_reconciles_physics_and_exact_bill(utility,schedule):
    data=frame(kw=20)
    data.loc[(data.timestamp.dt.hour>=17)&(data.timestamp.dt.hour<19),'grid_import_kw']=90
    a=account(schedule)
    if utility=='svp': a['previous_11_month_peaks_kw']=history(kw=100)
    tariff=f"{utility}_{schedule.lower().replace('-','')}_2026_"+('07_01' if utility=='amp' else '01_01')
    result=optimize(tariff,data,a)
    d=result['dispatch']
    assert result['total_explicit_cost']<result['baseline_bill']['total']-50
    assert d.grid_import_kw.to_numpy()==pytest.approx(data.grid_import_kw+d.charge_kw-d.discharge_kw)
    assert d.energy_end_kwh.to_numpy()==pytest.approx(d.energy_start_kwh+.25*(.95*d.charge_kw-d.discharge_kw/.95))
    assert d.energy_end_kwh.iloc[-1]==pytest.approx(100)
    assert (np.minimum(d.charge_kw,d.discharge_kw)<1e-6).all()
    assert d.energy_end_kwh.between(20-1e-6,180+1e-6).all()
    assert result['bill']['total']==pytest.approx(sum(result['bill']['line_items'].values()))
    assert result['optimality_gap_bound_dollars']<1e-4
    if utility=='svp':
        assert result['bill']['billing_demand_kw']==pytest.approx((result['bill']['metered_demand_kw']+100)/2)

@pytest.mark.parametrize('schedule,kw,tou',[('D-1',.2,False),('D-1',2,True),('C-1',.5,False),('C-1',2,True)])
def test_tiers_and_tou_have_exact_bills_and_certified_gap(schedule,kw,tou):
    a=account(schedule)
    a.update(time_of_use=tou,tou_enrollment_confirmed=tou)
    result=optimize('svp_'+schedule.lower().replace('-','')+'_2026_01_01',frame(kw=kw),a,
                    include_degradation_in_optimization=True)
    assert result['total_explicit_cost']<=result['baseline_bill']['total']+1e-6
    assert result['optimality_gap_bound_dollars']<.009
    assert result['bill']['total']==pytest.approx(sum(result['bill']['line_items'].values()))

def test_offpeak_spike_does_not_create_svp_demand_savings():
    data=frame(kw=20)
    data.loc[data.timestamp==pd.Timestamp('2026-08-02T14:00:00-07:00'),'grid_import_kw']=1000
    a=account('CB-1');a['previous_11_month_peaks_kw']=history(kw=100)
    result=optimize('svp_cb1_2026_01_01',data,a)
    assert result['bill']['billing_demand_kw']==pytest.approx(60)
    assert result['degradation_cost']==pytest.approx(0,abs=1e-5)


def test_municipal_bill_only_and_wear_aware_objectives_diverge():
    data=frame(kw=20)
    data.loc[(data.timestamp.dt.hour>=17)&(data.timestamp.dt.hour<19),'grid_import_kw']=90
    a=account('CB-1');a['previous_11_month_peaks_kw']=history(kw=100)
    bill_only=optimize('svp_cb1_2026_01_01',data,a,degradation_cost_per_kWh=100)
    wear_aware=optimize('svp_cb1_2026_01_01',data,a,degradation_cost_per_kWh=100,
                        include_degradation_in_optimization=True)
    assert bill_only['bill']['total'] < wear_aware['bill']['total']-1
    assert bill_only['degradation_cost'] > 0
    assert wear_aware['degradation_cost'] == pytest.approx(0,abs=1e-4)

def test_cb3_discontinuous_pf_boundary_is_rejected():
    a=account('CB-3');a.update(phase='three',secondary_service_approved=True,
        monthly_power_factor_percent=90,previous_11_month_peaks_kw=history(kw=1000))
    with pytest.raises(ValueError,match='exemption boundary'):
        optimize('svp_cb3_2026_01_01',frame(kw=100),a)

def test_incomplete_cycle_and_outside_coverage_rejected():
    with pytest.raises(ValueError):
        optimize('amp_a2_2026_07_01',frame(end='2026-08-15'),account('A-2'))
    with pytest.raises(ValueError):
        optimize('svp_c1_2026_01_01',frame(start='2026-09-01',end='2026-10-01'),account('C-1'))
