"""Independent historical residential bill and dispatch regression cases."""
from datetime import date
import numpy as np
import pytest
from test_socal import account, frame, study_request
from src.billing.socal import bill, eligibility, RESIDENTIAL_PLANS
from src.billing.plans import RatePlan, PlanError
from src.dispatch.socal import optimize


@pytest.mark.parametrize('start,end,lower,upper,gen,basic,bsc',[
 ('2025-01-01','2025-01-31',.21974,.31487,.11136,.031,0),
 ('2025-03-01','2025-03-31',.21733,.31179,.11136,.031,0),
 ('2025-07-01','2025-07-31',.21047,.30297,.11136,.031,0),
 ('2025-10-01','2025-10-31',.23208,.33657,.13170,.031,0),
 ('2025-12-01','2025-12-31',.18534,.28983,.13170,0,.794)])
def test_domestic_filed_versions(start,end,lower,upper,gen,basic,bsc):
 f=frame(start,end);kwh=len(f)*.25;allocation=31*(11.4 if start[5:7]=='07' else 11.)
 result=bill('sce_d',f,account('sce'),start,end)
 expected=allocation*lower+(kwh-allocation)*upper+kwh*(gen+.00198+.0003)+31*(basic+bsc)
 assert result['total']==pytest.approx(expected)
 assert len(result['rate_versions'])==1


def test_november_bsc_transition_not_double_charged():
 r=bill('sce_d',frame('2025-11-01','2025-11-30'),account('sce'),'2025-11-01','2025-11-30')
 # 14 local days before change include 25-hour DST day; 16 days afterward.
 pre=337.;post=384.;a=14*11.;b=16*11.
 expected=a*.23208+(pre-a)*.33657+b*.18534+(post-b)*.28983+721*(.13170+.00198+.0003)+14*.031+16*.794
 assert r['total']==pytest.approx(expected)
 assert r['line_items']['fixed_charge']==pytest.approx(14*.031+16*.794)
 assert [v['service_days'] for v in r['rate_versions']]==[14,16]
 assert any('approximation' in w for w in r['warnings'])


@pytest.mark.parametrize('plan',['sce_d','sce_tou-d-4-9','sce_tou-d-5-8'])
def test_zero_use_delivery_minimum_and_bsc_transition(plan):
 r=bill(plan,frame('2025-11-01','2025-11-30',0),account('sce'),'2025-11-01','2025-11-30')
 assert r['total']==pytest.approx(14*.346+16*.794)
 assert r['line_items']['minimum_adjustment']==pytest.approx(14*(.346-.031))


def test_domestic_minimum_excludes_wildfire_and_generation():
 r=bill('sce_d',frame('2025-07-01','2025-07-31',.01),account('sce'),'2025-07-01','2025-07-31')
 assert r['total']==pytest.approx(31*.346+7.44*(.00595+.11136+.00198+.0003))


def test_multifamily_basic_charge_and_credit_after_tax():
 a=account('sce');a.update(accommodation='multifamily',local_tax_percent=5,climate_credit_amount=56,climate_credit_confirmed=True)
 r=bill('sce_d',frame('2025-07-01','2025-07-31'),a,'2025-07-01','2025-07-31')
 kwh=744;allocation=31*11.4
 pre_tax=allocation*.21047+(kwh-allocation)*.30297+kwh*(.11136+.00198)+31*.024
 assert r['total']==pytest.approx(pre_tax*1.05+kwh*.0003-56)
 assert r['line_items']['climate_credit']==-56
 a['climate_credit_confirmed']=False
 with pytest.raises(ValueError,match='confirmation'):eligibility('sce_d',a,'2025-07-01','2025-07-31')


def test_credit_balance_preserved_not_cash_export_revenue():
 a=account('sce');a.update(climate_credit_amount=56,climate_credit_confirmed=True)
 r=bill('sce_d',frame('2025-12-01','2025-12-31',0),a,'2025-12-01','2025-12-31')
 assert r['amount_due']==0
 assert r['credit_balance']==pytest.approx(56-31*.794)


def test_july_tou_4_9_independent_holiday_and_baseline():
 f=frame('2025-07-01','2025-07-31');i=f.timestamp
 peak=(i.dt.hour>=16)&(i.dt.hour<21);weekday=(i.dt.dayofweek<5)&(i.dt.day!=4)
 on=float((peak&weekday).sum())*.25;mid=float((peak&~weekday).sum())*.25;off=744-on-mid
 expected=on*(.34197+.23967)+mid*(.34197+.12962)+off*(.29227+.07093)-31*11.4*.09250+31*.031+744*(.00198+.0003)
 r=bill('sce_tou-d-4-9',f,account('sce'),'2025-07-01','2025-07-31')
 assert r['total']==pytest.approx(expected)


def test_hpwh_only_eligible_tou_plans():
 a=account('sce');a['heat_pump_water']=True
 with pytest.raises(ValueError,match='water-heater'):eligibility('sce_d',a,'2025-07-01','2025-07-31')
 r=bill('sce_tou-d-4-9',frame('2025-07-01','2025-07-31'),a,'2025-07-01','2025-07-31')
 assert r['rate_versions'][0]['baseline_kwh']==pytest.approx(31*(11.4+1.9))


def test_shared_plan_gap_overlap_and_effective_dates():
 p=RESIDENTIAL_PLANS['sce_d'];assert isinstance(p,RatePlan)
 assert p.version_on(date(2025,11,14)).data['sheet']=='90340-E'
 assert p.version_on(date(2025,11,15)).data['sheet']=='90634-E'
 with pytest.raises(PlanError):p.require_coverage(date(2025,12,31),date(2026,6,25))
 with pytest.raises(PlanError,match='overlap'):RatePlan(p.identity,(p.versions[0],p.versions[0]))


@pytest.mark.parametrize('plan',['sce_d','sce_tou-d-4-9','sce_tou-d-5-8','sce_tou-d-prime'])
@pytest.mark.parametrize('kw',[.01,1.])
def test_transition_dispatch_uses_same_historical_bill(plan,kw):
 f=frame('2025-11-13','2025-11-16',kw)
 r=optimize(plan,f,account('sce'),'2025-11-13','2025-11-16',dict(capacity_kWh=10,energy_kWh=5,SOC_min=.2,SOC_max=.8,max_charge_kw=3,max_discharge_kw=3,charge_efficiency=.95,discharge_efficiency=.95),.01)
 assert r['objective_gap']<.005
 assert r['bill']['total']+r['degradation_cost']<=r['baseline_bill']['total']+.005
 d=r['dispatch'];assert np.allclose(d.grid_import_kw+d.battery_discharge_kw,d.native_load_kw+d.battery_charge_kw,atol=1e-6)
 assert d.energy_kWh.between(2-1e-6,8+1e-6).all()


def test_site_subtype_controls_accommodation_without_mutating_request():
 from src.local_web.socal_study import billing_account,validate
 r=study_request('sce');r['site_profile']['subtype']='apartment_unit'
 assert billing_account(r)['accommodation']=='multifamily'
 assert 'accommodation' not in r['account']
 r['account']['accommodation']='single_family'
 with pytest.raises(ValueError,match='subtype'):validate(r)
