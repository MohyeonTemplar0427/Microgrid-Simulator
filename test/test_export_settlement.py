import numpy as np
import pandas as pd
import pytest
from src.billing.export_settlement import CreditBalance, monthly_credit_ledger, compare_one_kwh
from src.billing import pge_export
from src.dispatch.solar_export import compare, benefit_breakdown


def account():
 return dict(utility='pge',generation_provider='pge',customer_class='residential',billing_plan='E-ELEC',program='NBT',income_tier=3,
    enrollment_confirmed=True,ordinary_account_confirmed=True,cycle_confirmed=True,no_local_tax_confirmed=True,
    no_other_adjustments_confirmed=True,reference='Hypothetical test',application_year=2026,pto_date='2026-04-01',
    bonus_eligible_confirmed=True,cycle_start='2026-07-01',cycle_end='2026-07-31',next_true_up_date='2027-04-01',storage='renewable_only')


def frame():
 i=pd.date_range('2026-07-01','2026-08-01',inclusive='left',freq='15min',tz='America/Los_Angeles')
 return pd.DataFrame(dict(timestamp=i,native_load_kw=np.ones(len(i)),pv_available_kw=np.where((i.hour>=10)&(i.hour<15),3.,0.)))


def test_restricted_credits_do_not_pay_fixed_or_other_component():
 r=monthly_credit_ledger(dict(generation=10,delivery=30,protected=20),dict(generation=100,delivery=5,bonus=3))
 assert r['amount_due']==42
 assert r['closing_balance']==dict(generation=90,delivery=0,bonus=0)
 assert r['credits_used']==dict(generation=10,delivery=5,bonus=3)


def test_carryover_bonus_and_no_cash_payout():
 r=monthly_credit_ledger(dict(generation=2,delivery=3,protected=4),dict(generation=0,delivery=0,bonus=10),CreditBalance(2,3,1))
 assert r['amount_due']==0
 assert r['closing_balance']['bonus']==7
 with pytest.raises(ValueError):CreditBalance(generation=-1)


def test_official_hourly_rates_dst_and_holiday():
 # CSV instants encode utility day classification. Official July2026 weekday
 # midnight price-sheet values: generation .07278, delivery .00072.
 i=pd.DatetimeIndex(['2026-07-01 00:00'],tz='America/Los_Angeles')
 g,d=pge_export.export_rates(i,2026)
 assert g[0]==pytest.approx(.07278);assert d[0]==pytest.approx(.00072)
 fall=pd.date_range('2026-11-01','2026-11-02',freq='15min',inclusive='left',tz='America/Los_Angeles')
 assert len(pge_export.export_rates(fall,2026)[0])==100
 with pytest.raises(ValueError):pge_export.export_rates(pd.DatetimeIndex(['2025-12-31'],tz='America/Los_Angeles'),2026)


def test_grid_only_bill_matches_existing_total_rate():
 f=frame().assign(grid_import_kw=1.,grid_export_kw=0.)
 r=pge_export.bill(f,account())
 # July every day: 155 peak,124 shoulder,465 off. No automatic climate credit.
 assert r['amount_due']==pytest.approx(155*.55214+124*.39026+465*.33358+31*.79343+744*.0003)
 assert sum(r['credits_earned'].values())==0


@pytest.mark.parametrize('updates',[{'generation_provider':'ava'},{'application_year':2022},{'enrollment_confirmed':False},
 {'program':'NEM2'},{'billing_plan':'E-1'},{'storage':'grid_charged'},{'next_true_up_date':'2026-07-31'}])
def test_unverified_programs_or_trueup_rejected(updates):
 a=account();a.update(updates)
 with pytest.raises(ValueError):pge_export.prices(a,pd.DatetimeIndex(frame().timestamp))


def test_comparison_explains_storage_tradeoff():
 r=compare_one_kwh(.35,.05,.50,round_trip_efficiency=.9,degradation_per_delivered_kwh=.03)
 assert r['value_per_available_kwh']['store_for_load']==pytest.approx(.423)
 assert r['highest_value_action']=='store_for_load'
 assert compare_one_kwh(.35,.60,.50,round_trip_efficiency=.9)['highest_value_action']=='export_now'


def test_optimized_export_physics_and_ledger():
 b=dict(capacity_kWh=4,energy_kWh=.8,SOC_min=.2,SOC_max=.8,max_charge_kw=2,max_discharge_kw=2,charge_efficiency=.95,discharge_efficiency=.95)
 results=compare(frame(),account(),export_limit_kw=3,battery=b,wear_per_kwh=.01)
 assert results['storage_with_export']['operating_cost']<=results['pv_with_export']['operating_cost']+.02
 for key in ('storage_with_export','storage_self_consumption'):
  r=results[key];d=r['dispatch']
  assert r['objective_gap']<.02
  assert np.minimum(d.grid_import_kw,d.grid_export_kw).max()<1e-6
  assert np.minimum(d.battery_charge_kw,d.battery_discharge_kw).max()<1e-6
  assert d.battery_charge_kw.max()<=2+1e-6
  assert (d.battery_charge_kw-d.pv_output_kw).max()<1e-6
  assert abs(.25*(d.battery_charge_kw.sum()*.95-d.battery_discharge_kw.sum()/.95))<1e-5
 assert results['storage_self_consumption']['dispatch'].grid_export_kw.max()<1e-6


def test_solar_benefits_separate_behind_meter_savings_and_unspent_export_credits():
 opening=CreditBalance(generation=10000,delivery=10000)
 results=compare(frame(),account(),export_limit_kw=3,opening=opening)
 flows,bridges,components=benefit_breakdown(results)
 assert [row['scenario'] for row in flows]==['grid_only','pv_self_consumption','pv_with_export']
 assert flows[0]['solar_ac_available_kwh']==0
 assert flows[0]['solar_ac_curtailed_kwh']==0
 assert flows[1]['grid_export_kwh']==0
 assert flows[1]['solar_ac_generated_kwh']>0
 on_site,export=bridges
 assert on_site['comparison']=='Solar panel + inverter, on-site use only'
 assert 'surplus export' in export['comparison']
 assert flows[2]['grid_export_kwh']<flows[2]['solar_ac_generated_kwh']
 assert on_site['current_bill_savings']==pytest.approx(results['grid_only']['bill']['amount_due']-results['pv_self_consumption']['bill']['amount_due'])
 assert export['avoided_import_charges']==pytest.approx(0)
 assert export['current_bill_savings']==pytest.approx(export['change_in_credits_used'])
 assert export['current_bill_savings']>0  # ACC Plus can pay protected charges.
 assert results['pv_with_export']['bill']['credits_used']['generation']==results['pv_self_consumption']['bill']['credits_used']['generation']
 assert results['pv_with_export']['bill']['credits_used']['delivery']==results['pv_self_consumption']['bill']['credits_used']['delivery']
 assert export['change_in_export_credits_earned']>0
 assert export['unspent_credit_change']>0
 assert sum(row['dollars'] for row in components if row['comparison']==on_site['comparison'] and row['category'] in ('avoided_import_charge','change_in_credit_used'))==pytest.approx(on_site['current_bill_savings'])


def test_web_contract_rejects_wrong_service_and_preserves_export_settings():
 from copy import deepcopy
 from src.local_web.contract import DEFAULT_SITE_REQUEST,validate_request
 r=deepcopy(DEFAULT_SITE_REQUEST)
 r.update(start_date='2026-07-01',end_date='2026-07-31',tariff_id='pge_e_elec_residential_tier3_bundled_2026_06_01',carbon_weight=0)
 r['site']['utility']='pge';r['site_profile']=dict(site_type='residential',subtype='house')
 r['battery']['energy_kWh']=r['battery']['capacity_kWh']*r['battery']['SOC_min']
 r['solar_export']=dict(account=account(),opening_balance=dict(generation=0,delivery=0,bonus=0),export_limit_kw=3)
 assert validate_request(r)['solar_export']==r['solar_export']
 r['solar_export']['account']['generation_provider']='ava'
 with pytest.raises(ValueError):validate_request(r)


def test_leap_day_pto_and_invalid_true_up_horizon():
 a=account();a.update(application_year=2024,pto_date='2024-02-29')
 pge_export.prices(a,pd.DatetimeIndex(frame().timestamp))
 a['next_true_up_date']='2028-01-01'
 with pytest.raises(ValueError,match='more than one year'):
  pge_export.prices(a,pd.DatetimeIndex(frame().timestamp))


def test_worker_export_tables_reconcile_with_saved_bills(tmp_path):
 from copy import deepcopy
 import json
 from src.local_web.contract import DEFAULT_SITE_REQUEST
 from src.local_web.export_study import execute
 r=deepcopy(DEFAULT_SITE_REQUEST)
 r.update(start_date='2026-07-01',end_date='2026-07-31',tariff_id='pge_e_elec_residential_tier3_bundled_2026_06_01',carbon_weight=0)
 r['site']['utility']='pge';r['site_profile']=dict(site_type='residential',subtype='house')
 r['battery']=dict(capacity_kWh=4,energy_kWh=.8,SOC_min=.2,SOC_max=.8,max_charge_kw=2,max_discharge_kw=2,charge_efficiency=.95,discharge_efficiency=.95)
 r['solar_export']=dict(account=account(),opening_balance=dict(generation=0,delivery=0,bonus=0),export_limit_kw=3)
 (tmp_path/'engine.json').write_text(json.dumps({'id':'test-fixture'}))
 execute(tmp_path,r,frame(),{'warnings':[]})
 summary=pd.read_csv(tmp_path/'comparison.csv')
 bills=json.loads((tmp_path/'solar_bills.json').read_text())
 assert len(summary)==5
 for row in summary.itertuples():
  assert row.amount_due==pytest.approx(bills[row.scenario]['bill']['amount_due'])
  assert row.operating_cost==pytest.approx(row.amount_due+row.degradation_cost)
 manifest=json.loads((tmp_path/'result.json').read_text())
 assert manifest['tables'][0]['id']=='comparison'
 assert {'solar-benefits','solar-benefit-components','solar-energy-flows'} <= {table['id'] for table in manifest['tables']}
 benefits=pd.read_csv(tmp_path/'solar-benefits.csv')
 assert benefits.iloc[0].comparison=='Solar panel + inverter, on-site use only'
 assert np.allclose(benefits.current_bill_savings,benefits.avoided_import_charges+benefits.change_in_credits_used)
 assert np.allclose(benefits.operating_savings,benefits.current_bill_savings-benefits.battery_wear_change)
 assert any('annual true-up' in warning for warning in manifest['warnings'])
 assert any('Exporting all solar output' in warning for warning in manifest['warnings'])
