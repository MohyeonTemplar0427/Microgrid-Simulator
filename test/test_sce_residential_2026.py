"""Independent filed-price checks for the formerly unsupported 2026 dates."""
from datetime import date
import numpy as np
import pandas as pd
import pytest
from test_socal import account, frame
from src.billing.socal import bill, RESIDENTIAL_PLANS, PLANS
from src.billing.plans import PlanError
from src.dispatch.socal import optimize


@pytest.mark.parametrize('start,end', [('2026-01-01','2026-01-31'),('2026-03-01','2026-03-31'),('2026-05-01','2026-05-31')])
def test_domestic_january_prices_until_june(start,end):
 f=frame(start,end);energy=len(f)*.25;days=len(pd.DatetimeIndex(f.timestamp).normalize().unique());baseline=days*11
 r=bill('sce_d',f,account('sce'),start,end)
 expected=baseline*.18482+(energy-baseline)*.28590+energy*(.11761+.00619+.0003)+days*.794
 assert r['total']==pytest.approx(expected)
 assert r['rate_versions'][0]['sheet']=='90841-E'
 assert r['line_items']['minimum_adjustment']==0


@pytest.mark.parametrize('plan,peak,endhour,delivery,generation,credit',[
 ('sce_tou-d-4-9',16,21,(.33082,.27338,.25272),(.18077,.10212,.08364),.10108),
 ('sce_tou-d-5-8',17,20,(.33150,.28277,.25638),(.27710,.09955,.06937),.10108),
 ('sce_tou-d-prime',16,21,(.30091,.18785,.18785),(.26489,.05958,.05958),0)])
@pytest.mark.parametrize('month',[1,3,5])
def test_winter_tou_independent_bill(plan,peak,endhour,delivery,generation,credit,month):
 start=f'2026-{month:02}-01';end=f'2026-{month:02}-31';f=frame(start,end);hour=f.timestamp.dt.hour
 mid=(hour>=peak)&(hour<endhour);superoff=(hour>=8)&(hour<peak);off=~(mid|superoff)
 volumes=[float(x.sum())*.25 for x in (mid,off,superoff)]
 expected=sum(k*(d+g) for k,d,g in zip(volumes,delivery,generation))-31*11*credit+31*.794+sum(volumes)*(.00619+.0003)
 r=bill(plan,f,account('sce'),start,end)
 assert r['total']==pytest.approx(expected)
 assert len(r['rate_versions'])==1


def test_june_first_rates_and_season_apply_before_june_25():
 f=frame('2026-05-31','2026-06-01');r=bill('sce_d',f,account('sce'),'2026-05-31','2026-06-01')
 expected=11*.18482+13*.28590+11.4*.18453+12.6*.28552+48*(.11761+.00619+.0003)+2*.794
 assert r['total']==pytest.approx(expected)
 assert [x['sheet'] for x in r['rate_versions']]==['90841-E','91130-E']
 assert [x['service_days'] for x in r['rate_versions']]==[1,1]


def test_january_first_replaces_december_without_retroactive_prices():
 f=frame('2025-12-31','2026-01-01');r=bill('sce_d',f,account('sce'),'2025-12-31','2026-01-01')
 expected=11*.18534+13*.28983+24*(.13170+.00198)+11*.18482+13*.28590+24*(.11761+.00619)+48*.0003+2*.794
 assert r['total']==pytest.approx(expected)


@pytest.mark.parametrize('plan',list(RESIDENTIAL_PLANS))
def test_complete_coverage_and_no_false_june_25_price_boundary(plan):
 p=RESIDENTIAL_PLANS[plan];p.require_coverage(date(2025,1,1),date(2026,9,17))
 assert p.version_on(date(2026,5,31)).data['advice_letter']=='5725-E'
 assert p.version_on(date(2026,6,1)).data['advice_letter']=='5829-E'
 assert p.version_on(date(2026,6,24)) is p.version_on(date(2026,6,25))
 assert len(PLANS[plan]['coverage_windows'])==7
 with pytest.raises(PlanError):p.require_coverage(date(2026,9,17),date(2026,9,18))
 # The terms-only June change must not split allowance accumulation.
 r=bill(plan,frame('2026-06-01','2026-06-30'),account('sce'),'2026-06-01','2026-06-30')
 assert len(r['rate_versions'])==1
 assert r['line_items']['fixed_charge']==pytest.approx(30*.794)


@pytest.mark.parametrize('plan',list(RESIDENTIAL_PLANS))
def test_new_dates_dispatch_and_bill_reconcile(plan):
 f=frame('2026-05-30','2026-06-02')
 r=optimize(plan,f,account('sce'),'2026-05-30','2026-06-02',dict(capacity_kWh=10,energy_kWh=5,SOC_min=.2,SOC_max=.8,max_charge_kw=3,max_discharge_kw=3,charge_efficiency=.95,discharge_efficiency=.95),.01)
 assert r['objective_gap']<.005
 assert r['bill']['total']+r['degradation_cost']<=r['baseline_bill']['total']+.005
 d=r['dispatch'];assert np.allclose(d.grid_import_kw+d.battery_discharge_kw,d.native_load_kw+d.battery_charge_kw,atol=1e-6)
