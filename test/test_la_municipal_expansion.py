import numpy as np
import pandas as pd
import pytest
from src.billing.socal import bill, eligibility
from src.billing.burbank import periods, holidays
from src.dispatch.socal import optimize
from test_socal import account, frame


def municipal_account(u,**kw):
    a=account(u)
    a.update(accommodation='single_family',local_tax_percent={'bwp':7,'ipu':0,'alw':4}[u],
             bwp_service_size='medium',bwp_ecac_confirmed=True,bwp_ev_confirmed=True,bwp_c_confirmed=True,
             ipu_domestic_confirmed=True,alw_ordinary_meter_confirmed=True,municipal_storage_confirmed=True)
    a.update(kw);return a


def test_azusa_domestic_and_minimum_independent():
    a=municipal_account('alw')
    b=bill('alw_d',frame('2025-01-01','2025-01-31'),a,'2025-01-01','2025-01-31')
    assert b['total']==pytest.approx((250*.1091+494*.1487+744*(.06137+.00591))*1.04+744*.0003)
    b=bill('alw_d',frame('2025-01-01','2025-01-31',kw=.01),a,'2025-01-01','2025-01-31')
    assert b['total']==pytest.approx((5.8+7.44*(.06137+.00591))*1.04+7.44*.0003)


def test_azusa_declining_commercial_tiers_and_rider_version():
    a=municipal_account('alw',customer_class='commercial',local_tax_percent=8)
    b=bill('alw_g-1',frame('2026-07-01','2026-07-31'),a,'2026-07-01','2026-07-31')
    assert b['total']==pytest.approx((10+500*.165+244*.143+744*(.05+.00536))*1.08+744*.0003)
    assert b['adjustment_versions']==['ALW-PCA-2026H2','ALW-PBC-FY2027']
    before=bill('alw_d',frame('2026-06-01','2026-06-30'),municipal_account('alw'),'2026-06-01','2026-06-30')
    assert before['line_items']['public_benefits_charge']==pytest.approx(720*.00528)
    with pytest.raises(ValueError,match='rider'):eligibility('alw_d',municipal_account('alw'),'2026-06-15','2026-07-14')
    with pytest.raises(ValueError,match='rider'):eligibility('alw_d',municipal_account('alw'),'2025-08-01','2025-08-31')


def test_burbank_basic_independent_and_no_tax_on_tax():
    b=bill('bwp_basic',frame('2026-07-01','2026-07-31'),municipal_account('bwp'),'2026-07-01','2026-07-31')
    base=19.5+4.45+300*.146+444*.2442+744*.034
    assert b['total']==pytest.approx(base*1.14+744*.0003)
    assert b['line_items']['in_lieu_transfer']==pytest.approx(base*.07)
    assert b['line_items']['local_utility_tax']==pytest.approx(base*.07)


def test_burbank_official_sample_tax_fixture():
    # Official 2023 bill example: energy 28.24+44.09+34.13, ECAC157.32,
    # service16.22; independent evidence for the tax base, not 2026 prices.
    base=28.24+44.09+34.13+157.32+16.22
    assert round(base*.07,2)==19.60
    assert round(base*1.14+.43,2)==319.63


def test_burbank_calendar_boundaries():
    i=pd.DatetimeIndex(['2026-07-03 16:00','2026-07-04 16:00','2026-07-06 15:45',
                        '2026-07-06 16:00','2026-07-06 19:00','2026-07-06 23:00',
                        '2026-06-19 16:00','2026-03-31 10:00'],tz='America/Los_Angeles')
    assert list(periods(i))==['on','off','mid','on','mid','off','off','off']
    assert pd.Timestamp('2026-11-27').date() in holidays(2026)


def test_burbank_commercial_independent_energy():
    # July2026: 23 weekdays; July4 is Saturday, no Friday substitution.
    b=bill('bwp_c',frame('2026-07-01','2026-07-31'),municipal_account('bwp',customer_class='commercial'),'2026-07-01','2026-07-31')
    base=28+69*.4018+276*.2623+399*.1403+744*.034
    assert b['total']==pytest.approx(base*1.14+744*.0003)


def test_industry_domestic_daily_charge_and_dst():
    for accommodation,daily in [('single_family',.033),('multifamily',.025)]:
        b=bill('ipu_d',frame('2025-03-01','2025-03-31'),municipal_account('ipu',accommodation=accommodation),'2025-03-01','2025-03-31')
        assert b['total']==pytest.approx(31*daily+743*(.10882+.00328+.0003))


@pytest.mark.parametrize('plan,u,updates',[('bwp_basic','bwp',{'bwp_service_size':''}),('bwp_ev','bwp',{'bwp_ev_confirmed':False}),
 ('bwp_c','bwp',{'customer_class':'commercial','bwp_c_confirmed':False}),('ipu_d','ipu',{'ipu_domestic_confirmed':False}),
 ('alw_d','alw',{'alw_ordinary_meter_confirmed':False})])
def test_missing_qualification_rejected(plan,u,updates):
    with pytest.raises(ValueError):eligibility(plan,municipal_account(u,**updates),'2026-07-01','2026-07-31')


@pytest.mark.parametrize('plan,u',[('alw_d','alw'),('alw_g-1','alw'),('bwp_basic','bwp'),('bwp_ev','bwp'),('bwp_c','bwp'),('ipu_d','ipu')])
def test_battery_bill_reconciliation_and_physics(plan,u):
    a=municipal_account(u)
    if plan in ('alw_g-1','bwp_c'):a.update(customer_class='commercial',local_tax_percent=8 if u=='alw' else 7)
    b=dict(capacity_kWh=10,energy_kWh=5,SOC_min=.2,SOC_max=.8,max_charge_kw=3,max_discharge_kw=3,charge_efficiency=.95,discharge_efficiency=.95)
    r=optimize(plan,frame('2026-07-01','2026-07-31'),a,'2026-07-01','2026-07-31',b,.01)
    d=r['dispatch'];assert r['objective_gap']<.02
    assert np.max(np.abs(d.grid_import_kw+d.battery_discharge_kw-1-d.battery_charge_kw))<1e-6
    assert abs(.25*(d.battery_charge_kw.sum()*.95-d.battery_discharge_kw.sum()/.95))<1e-5
    assert r['bill']['total']+r['degradation_cost']<=r['baseline_bill']['total']+.01
