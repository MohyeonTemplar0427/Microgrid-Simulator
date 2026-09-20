from copy import deepcopy
from datetime import date

import numpy as np
import pandas as pd
import pytest
import requests

from src.billing.municipal import RATES, bill_cycle, eligibility, nerc_holidays, svp_peak_mask
from src.local_web.utility_resolution import resolve_service
from src.local_web.municipal_service import execute, validate_arrangement


def account(schedule='A-1', **changes):
    return dict(customer_class='residential' if schedule=='D-1' else 'commercial',
        phase='single',voltage='secondary',metered=True,onsite_generation=False,special_riders=[],
        billing_cycle_confirmed=True,state_surcharge_exempt=False,confirmed_schedule=schedule,
        schedule_confirmation_reference='Customer electricity bill, August 2026',
        uut_status='standard',heating_source='gas_or_other',demand_interval_minutes=15,
        minimum_charge_load_units=0,power_factor_adjustment_active=False,
        power_factor_state_reference='Utility confirmed inactive August 2026',**changes)


def frame(start='2026-08-01',end='2026-09-01',kw=1):
    return pd.DataFrame({'timestamp':pd.date_range(start,end,tz='America/Los_Angeles',freq='15min',inclusive='left'),'grid_import_kw':kw})


def run(tariff,df=None,a=None,start='2026-08-01',end='2026-09-01'):
    return bill_cycle(tariff,frame(start,end) if df is None else df,
        cycle_start=pd.Timestamp(start,tz='America/Los_Angeles'),cycle_end=pd.Timestamp(end,tz='America/Los_Angeles'),
        account=a or account(RATES[tariff].schedule))


def history(start='2026-08-01',kw=100):
    return {(pd.Timestamp(start)-pd.DateOffset(months=i)).strftime('%Y-%m'):kw for i in range(1,12)}


def test_amp_d1_independent_hand_bill_and_tier():
    # 744 kWh, summer gas baseline 211; taxes exclude state surcharge.
    b=run('amp_d1_2026_07_01')
    energy=211*.13934+533*.26723
    assert b['line_items']['energy_charge']==pytest.approx(energy)
    assert b['total']==pytest.approx((24.27+energy)*1.075+744*.0003)
    assert b['line_items']['energy_adjustment_charge']==0
    assert sum(b['line_items'].values())==b['total']


def test_amp_a1_and_primary_discount():
    b=run('amp_a1_2026_07_01')
    assert b['total']==pytest.approx((41.99+744*.20946)*1.075+744*.0003)
    a=account(); a.update(voltage='primary_12kv',primary_discount_qualified=True)
    b=run('amp_a1_2026_07_01',a=a)
    assert b['total']==pytest.approx((41.99+744*.20946)*.97*1.075+744*.0003)


def test_amp_a2_monthly_peak_not_interval_sum():
    df=frame(kw=10); df.loc[0,'grid_import_kw']=100
    b=run('amp_a2_2026_07_01',df)
    assert b['billing_demand_kw']==100
    assert b['line_items']['demand_charge']==1462
    assert b['total']==pytest.approx((212.62+(7440+22.5)*.15316+1462)*1.075+(7440+22.5)*.0003)


def test_amp_a3_pf_excludes_customer_charge():
    a=account('A-3'); a.update(phase='three',monthly_power_factor_percent=90)
    b=run('amp_a3_2026_07_01',frame(kw=600),a)
    assert b['line_items']['power_factor_adjustment']==pytest.approx((744*600*.14952+600*18.5)*.005)


def test_svp_d1_and_c1_tiers_and_phase():
    b=run('svp_d1_2026_01_01')
    assert b['total']==pytest.approx((5.11+300*.15612+444*.17946)*1.0285+744*.0003)
    a=account('C-1'); a['phase']='three'
    b=run('svp_c1_2026_01_01',frame(kw=2),a)
    assert b['total']==pytest.approx((9.85+800*.26620+688*.24166)*1.0285+1488*.0003)


def test_svp_c1_minimum_is_floor_not_additional_fee():
    a=account('C-1'); a['minimum_charge_load_units']=10
    b=run('svp_c1_2026_01_01',frame(kw=0),a)
    assert b['line_items']['minimum_charge_adjustment']==pytest.approx(34.3-5.52)
    assert b['line_items']['public_benefits_charge']==pytest.approx(5.52*.0285)


def test_svp_tou_proportionally_allocates_tiers():
    df=frame(kw=0)
    # 600 kWh peak, 400 off; 300 baseline split 180/120, excess 420/280.
    df.loc[df.timestamp==pd.Timestamp('2026-08-03T06:00:00-07:00'),'grid_import_kw']=2400
    df.loc[df.timestamp==pd.Timestamp('2026-08-03T22:00:00-07:00'),'grid_import_kw']=1600
    a=account('D-1'); a.update(time_of_use=True,tou_enrollment_confirmed=True)
    b=run('svp_d1_2026_01_01',df,a)
    assert b['line_items']['energy_charge']==pytest.approx(180*.17960+120*.13690+420*.20295+280*.16023)


def test_svp_cb1_ratchet_and_offpeak_exclusions_non_tou():
    df=frame(kw=10)
    df.loc[df.timestamp==pd.Timestamp('2026-08-03T06:00:00-07:00'),'grid_import_kw']=50
    df.loc[df.timestamp==pd.Timestamp('2026-08-02T14:00:00-07:00'),'grid_import_kw']=1000 # Sunday
    df.loc[df.timestamp==pd.Timestamp('2026-08-03T22:00:00-07:00'),'grid_import_kw']=2000
    a=account('CB-1'); a['previous_11_month_peaks_kw']=history()
    b=run('svp_cb1_2026_01_01',df,a)
    assert b['metered_demand_kw']==50
    assert b['billing_demand_kw']==75
    assert b['line_items']['demand_charge']==pytest.approx(75*12.14)
    assert b['total']==pytest.approx((100.45+b['import_kwh']*.16139+75*12.14)*1.0285+b['import_kwh']*.0003)


def test_svp_cb3_primary_pf_and_low_load_exception():
    a=account('CB-3'); a.update(phase='three',voltage='primary_12kv',primary_discount_qualified=True,
        monthly_power_factor_percent=90,previous_11_month_peaks_kw=history(kw=5000))
    b=run('svp_cb3_2026_01_01',frame(kw=1000),a)
    assert b['billing_demand_kw']==3000
    subtotal=100.45+744000*.14864+3000*(16.19-1.52)
    assert b['total']==pytest.approx(subtotal*.995*1.0285+744000*.0003)
    b=run('svp_cb3_2026_01_01',frame(kw=100),a)
    assert b['line_items']['power_factor_adjustment']==0


def test_holidays_and_exact_tou_boundaries():
    stamps=pd.DatetimeIndex(['2026-07-03T12:00:00-07:00','2026-07-04T12:00:00-07:00','2026-07-05T12:00:00-07:00',
        '2026-07-06T05:45:00-07:00','2026-07-06T06:00:00-07:00','2026-07-06T21:45:00-07:00','2026-07-06T22:00:00-07:00'])
    assert list(svp_peak_mask(stamps))==[True,False,False,False,True,True,False]
    assert date(2027,7,5) in nerc_holidays(2027)
    assert date(2026,7,3) not in nerc_holidays(2026)


def test_dst_calendar_month_energy_counts():
    b=run('svp_d1_2026_01_01',start='2026-03-01',end='2026-04-01')
    assert b['import_kwh']==743


@pytest.mark.parametrize('change',[lambda f:f.iloc[::4],lambda f:f.iloc[:-1],lambda f:f.iloc[::-1],lambda f:pd.concat([f.iloc[:1],f])])
def test_rejects_coarse_missing_unordered_duplicate_intervals(change):
    with pytest.raises(ValueError,match='15-minute'):
        run('amp_a2_2026_07_01',change(frame()))


def test_regular_amp_read_cycle_and_partial_rejection():
    b=run('amp_a1_2026_07_01',start='2026-07-15',end='2026-08-14')
    assert b['line_items']['customer_charge']==41.99
    with pytest.raises(ValueError,match='proration'):
        run('amp_a1_2026_07_01',start='2026-08-01',end='2026-08-10')


@pytest.mark.parametrize('start,end',[('2026-06-01','2026-07-01'),('2026-06-15','2026-07-15'),('2026-09-01','2026-10-01')])
def test_no_backward_or_forward_rate_extrapolation(start,end):
    with pytest.raises(ValueError,match='coverage'):
        run('amp_a1_2026_07_01',start=start,end=end)


def test_historical_peak_inputs_and_interval_assignment_required():
    a=account('CB-1')
    with pytest.raises(ValueError,match='previous_11'):
        run('svp_cb1_2026_01_01',a=a)
    a['previous_11_month_peaks_kw']={'2026-07':0}
    with pytest.raises(ValueError,match='preceding 11'):
        run('svp_cb1_2026_01_01',a=a)
    a['previous_11_month_peaks_kw']=history(); a['demand_interval_minutes']=5
    with pytest.raises(ValueError,match='1/5-minute'):
        run('svp_cb1_2026_01_01',a=a)


def test_eligibility_missing_history_never_inferred_from_replay():
    a=account(); del a['confirmed_schedule']; del a['schedule_confirmation_reference']
    items=eligibility('amp',a,'2026-08-01','2026-09-01')
    a1=next(x for x in items if x['tariff']['schedule']=='A-1')
    assert a1['status']=='missing_inputs'
    assert 'confirmed_schedule' in a1['missing_inputs']
    assert a1['qualification']['missing_for_transfer']
    assert next(x for x in items if x['tariff']['schedule']=='D-1')['status']=='excluded'


def test_unsupported_export_generation_and_unknown_fields():
    df=frame(); df['grid_export_kw']=1
    with pytest.raises(ValueError,match='Export'):
        run('amp_a1_2026_07_01',df)
    a=account(); a['onsite_generation']=True
    with pytest.raises(ValueError,match='Onsite'):
        run('amp_a1_2026_07_01',a=a)
    a=account(); a['pcia_vintage']=2020
    with pytest.raises(ValueError,match='Unknown account'):
        run('amp_a1_2026_07_01',a=a)


def feature(agency,name='Electricity utility',oid=1):
    return {'attributes':{'OBJECTID':oid,'AgencyNum':agency,'Utility':name}}


class Response:
    def __init__(self,data): self.data=data
    def raise_for_status(self): pass
    def json(self): return self.data


def geo_get(exact,near=None):
    def get(url,params,timeout):
        if not url.endswith('/query'):
            return Response({'editingInfo':{'dataLastEditDate':1788541732680},'serviceItemId':'cec-fixture'})
        if 'Other' in url: return Response({'features':[]})
        return Response({'features':exact if 'distance' not in params else exact if near is None else near})
    return get


@pytest.mark.parametrize('agency,expected',[(10500,'amp'),(80560,'svp'),(71021,'pge')])
def test_official_agency_mapping_not_city_county_strings(agency,expected):
    # Deliberately misleading display name cannot turn a PG&E polygon into AMP.
    r=resolve_service({'latitude':37.7,'longitude':-122.2},get=geo_get([feature(agency,'Alameda County / Santa Clara County')]))
    assert r['status']=='approximate' and r['delivery_utility']==expected
    assert r['sources'][0]['data_last_edit_epoch_ms']==1788541732680


def test_boundary_and_overlapping_territories_are_ambiguous():
    r=resolve_service({'latitude':37.7,'longitude':-122.2},get=geo_get([feature(10500)], [feature(10500),feature(71021,oid=2)]))
    assert r['status']=='ambiguous' and r['delivery_utility'] is None
    r=resolve_service({'latitude':37.7,'longitude':-122.2},get=geo_get([feature(80560),feature(999,oid=2)]))
    assert r['status']=='ambiguous'


def test_missing_unknown_geography_has_no_pge_fallback():
    for get in (geo_get([]),geo_get([feature(999)])):
        r=resolve_service({'latitude':37.7,'longitude':-122.2},get=get)
        assert r['status']=='unsupported' and r['delivery_utility'] is None
    def fail(*args,**kwargs): raise requests.ConnectionError('offline')
    assert resolve_service({'latitude':37.7,'longitude':-122.2},get=fail)['status']=='unsupported'
    with pytest.raises(ValueError,match='coordinates'):
        resolve_service({'zip':'95050'})


def test_manual_override_preserves_map_and_reference():
    confirmation=dict(delivery_utility='svp',evidence_type='electricity_bill',reference='August bill reviewed',confirmed_on='2026-09-17')
    r=resolve_service({'latitude':37.7,'longitude':-122.2,'manual_confirmation':confirmation},get=geo_get([feature(71021)]))
    assert r['status']=='verified' and r['delivery_utility']=='svp'
    assert r['mapped_delivery_utility']=='pge'
    assert r['manual_confirmation']==confirmation and len(r['provenance_sha256'])==64


def test_actual_and_comparison_modes_and_generation_separation():
    arr=dict(delivery_utility='amp',generation_provider='amp',tariff_id='amp_a1_2026_07_01',export_program='none')
    with pytest.raises(ValueError,match='confirmed delivery'):
        validate_arrangement(arr,{'status':'approximate','delivery_utility':'amp'})
    validate_arrangement(arr,{},comparison=True)
    arr['generation_provider']='pge'
    with pytest.raises(ValueError,match='Municipal service'):
        validate_arrangement(arr,{},comparison=True)
    arr=dict(delivery_utility='pge',generation_provider='cleanpowersf',tariff_id='pge_b1_single_2026_03_01',export_program='none')
    with pytest.raises(ValueError): validate_arrangement(arr,{},comparison=True)


def test_versioned_service_bill_replay():
    df=frame(); df['timestamp']=df.timestamp.map(lambda t:t.isoformat())
    r=execute('municipal-bill',dict(interface_version=1,mode='alternative_location',resolution={},
        arrangement=dict(delivery_utility='amp',generation_provider='amp',tariff_id='amp_a1_2026_07_01',export_program='none'),
        account=account(),start='2026-08-01',end='2026-09-01',dispatch=df.to_dict('records')))
    assert 'alternative-location' in r['label']
    assert r['bill']['total']==pytest.approx((41.99+744*.20946)*1.075+744*.0003)


def test_hetch_hetchy_uses_agency_identity_not_recycled_object_id():
    r=resolve_service({'latitude':37.7793,'longitude':-122.4193},get=geo_get([feature(80522,oid=999)]))
    assert r['delivery_utility']=='hetch_hetchy'
    r=resolve_service({'latitude':37.7793,'longitude':-122.4193},get=geo_get([feature(999,oid=52)]))
    assert r['delivery_candidates'][0]['utility_id']=='cec:distribution:52'
    assert r['status']=='unsupported'


def test_point_match_is_distinct_from_nearby_pge_boundary():
    r=resolve_service({'latitude':37.7,'longitude':-122.2},get=geo_get([feature(10500)], [feature(10500),feature(71021,oid=2)]))
    assert {x['utility_id']:x['match'] for x in r['delivery_candidates']}=={'amp':'point','pge':'nearby_boundary'}


@pytest.mark.parametrize('oid,name,kind,expected',[
    (12,'CleanPowerSF (CPSF)','CCA','cleanpowersf'),
    (19,'Peninsula Clean Energy','CCA','peninsula'),
    (19,'WestLight Energy','CCA','peninsula'),
    (27,'San Jose Clean Energy (SJCE)','CCA','sjce'),
    (29,'Silicon Valley Clean Energy (SVCE)','CCA','svce'),
    (9,'Ava Community Energy (Ava)','CCA',None),
    (19,'Different provider after record renumbering','CCA',None),
    (1,'Western Area Power Administration','ADMIN',None),
])
def test_cca_identity_and_nonretail_overlay_filter(oid,name,kind,expected):
    base=geo_get([feature(71021)])
    def get(url,params,timeout):
        if 'Other' in url and url.endswith('/query'):return Response({'features':[{'attributes':{'OBJECTID':oid,'Utility':name,'Type':kind}}]})
        return base(url,params,timeout)
    result=resolve_service({'latitude':37.7,'longitude':-122.2},get=get)
    if kind!='CCA':assert result['generation_candidates']==[]
    else:
        assert result['generation_candidates'][0]['service_id']==expected
        assert result['generation_candidates'][0]['name']==name
