import numpy as np
import pytest
from src.billing.socal import bill, eligibility
from src.dispatch.socal import optimize
from test_socal import account, frame


def pwp_account(**updates):
    a=account('pwp');a.update(local_tax_percent=7.67,pwp_flat_enrollment_confirmed=True,
                            pwp_r2_qualification_confirmed=True,pwp_storage_confirmed=True)
    a.update(updates);return a


def test_residential_independent_bill_and_exemption_base():
    b=bill('pwp_r-1_flat',frame('2026-06-01','2026-06-30'),pwp_account(),'2026-06-01','2026-06-30')
    # 720 kWh: 350 at first distribution tier and 370 at second.
    base=17.5+350*.03505+370*.14018+720*(.10825+.01609)
    assert b['total']==pytest.approx(base*(1+.0767+.0434)+(base-720*.10825)*.0743+720*(.00685+.0003))
    assert b['line_items']['power_cost_adjustment']==pytest.approx(720*.05165)
    assert b['line_items']['street_light_traffic_signal_tax']>0 # fixed/delivery charges are not exempt


def test_small_commercial_declining_underground_surtax():
    b=bill('pwp_s-1_flat',frame('2026-06-01','2026-06-30',kw=8),pwp_account(customer_class='commercial'),'2026-06-01','2026-06-30')
    base=31.7+5760*(.06862+.01609+.14186)
    assert b['line_items']['underground_surtax']==pytest.approx(1000*.0434+(base-1000)*.037)
    assert b['total']==pytest.approx(base*1.0767+(base-1000*.14186)*.0743+43.4+(base-1000)*.037+5760*.00715)


def test_bimonthly_tiers_not_reset_at_calendar_boundary():
    a=pwp_account(billing_month_factor=2)
    b=bill('pwp_r-2_flat',frame('2026-06-01','2026-07-31'),a,'2026-06-01','2026-07-31')
    assert b['line_items']['distribution_charge']==pytest.approx(700*.03505+764*.14018)
    assert b['line_items']['customer_charge']==22


@pytest.mark.parametrize('updates',[{'pwp_flat_enrollment_confirmed':False},{'generation_provider':'cpa'},
                                  {'solar_program':'nem'},{'billing_month_factor':.5},{'local_tax_percent':0}])
def test_unverified_account_rejected(updates):
    with pytest.raises(ValueError):eligibility('pwp_r-1_flat',pwp_account(**updates),'2026-06-01','2026-06-30')


def test_missing_history_partial_period_and_demand_schedule_rejected():
    with pytest.raises(ValueError,match='coverage'):eligibility('pwp_r-1_flat',pwp_account(),'2025-06-01','2025-06-30')
    with pytest.raises(ValueError,match='complete'):eligibility('pwp_r-1_flat',pwp_account(),'2026-06-01','2026-06-10')
    with pytest.raises(ValueError,match='below 30'):bill('pwp_s-1_flat',frame('2026-06-01','2026-06-30',kw=30),pwp_account(customer_class='commercial'),'2026-06-01','2026-06-30')


def test_flat_battery_optimum_idles_and_preserves_energy():
    f=frame('2026-06-01','2026-06-30')
    b=dict(capacity_kWh=10,energy_kWh=5,SOC_min=.2,SOC_max=.8,max_charge_kw=3,max_discharge_kw=3,charge_efficiency=.95,discharge_efficiency=.95)
    r=optimize('pwp_r-1_flat',f,pwp_account(),'2026-06-01','2026-06-30',b,.01)
    assert r['bill']['total']==r['baseline_bill']['total']
    assert r['degradation_cost']==0 and r['objective_gap']==0
    assert np.all(r['dispatch'].energy_kWh==5)
    assert np.all(r['dispatch'].battery_charge_kw==0)
