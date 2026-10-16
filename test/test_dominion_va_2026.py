"""Independent 2026 filed-date and billing/optimization reconciliation fixtures."""
from copy import deepcopy
from datetime import date
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
import pytest
from src.billing import dominion_va_general as va
from src.billing.dominion_va_2026 import Components,versions,base_metadata
from src.billing.regional_math import BillingMath


def index(start,end):
    return pd.date_range(start,end,tz=va.TIMEZONE,freq='30min',inclusive='left')


def bill(plan='VA-1',start='2026-01-01',end='2026-02-01',power=None,patch=None):
    a=va.defaults(plan);a.update(billing_month=pd.Timestamp(start).month)
    a.update(patch or {});idx=index(start,end)
    if power is None:power=1. if a['customer_class']=='residential' else 10. if plan in ('VA-GS1','VA-5C','VA-5P') else 90. if plan in ('VA-GS2','VA-GS2T') else 600.
    load=np.broadcast_to(power,len(idx)).copy()
    return va.charge_lines(idx,load,np.zeros(len(idx)),a,math=BillingMath(idx))


# Dated sums independently transcribed from the actual residential source rows.
# These expectations do not import runtime rate tables.
JAN_RES=(.029680,.000231,.001336,.001765,.003668,0.,.006241,.000625,
         .007564,.011229,0.,0.,.007676,.000287,.003475,.011789,.002906,.000531)
JAN_GS1=(.029680,.000171,.000988,.001765,.002567,0.,.004002,.000456,
         .005989,.007957,0.,0.,.007676,.000212,.002561,.010069,.002906,.000348)


def monthly_sum(month,group):
    rates=list(JAN_RES if group=='res' else JAN_GS1)
    if month>=2:rates[16]=.002900
    if month>=3:rates[5]=.000754 if group=='res' else .000541
    if month>=4:rates[8]=.005729 if group=='res' else .004100
    if month>=5:rates[4]=.006054 if group=='res' else .004673
    if month>=6:rates[6]=.007685 if group=='res' else .005780;rates[17]=0.
    if month>=7:rates[0]=.037648
    if month>=8:rates[16]=.002901
    if month>=9:
        rates[1]=.000454 if group=='res' else .000384
        rates[2]=.001322 if group=='res' else .001116
        rates[9]=.011362 if group=='res' else .009229
        rates[12]=.005520;rates[13]=.000147 if group=='res' else .000124
        rates[14]=.004027 if group=='res' else .003429
        rates[15]=.012730 if group=='res' else .011929
    return sum(rates)


@pytest.mark.parametrize('plan',['VA-1','VA-GS1'])
@pytest.mark.parametrize('month',range(1,10))
def test_each_month_independent_complete_flat_load_bill(plan,month):
    start=pd.Timestamp(2026,month,1);end=start+pd.DateOffset(months=1)
    r=bill(plan,start.isoformat(),end.isoformat());kwh=r['metrics']['import_kWh']
    residential=plan=='VA-1';summer=6<=month<=9
    first=min(kwh,800. if residential else 1400.)
    d=(.035690,.023596) if residential else (.025525,.018928)
    g=((.031212,.046243) if summer else (.030064,.026965)) if residential else ((.030788,.041350) if summer else (.030788,.019886))
    expected=(7.58 if residential else 13.39)+first*(d[0]+g[0])+(kwh-first)*(d[1]+g[1])
    expected+=kwh*((.00970 if residential else .00582)+monthly_sum(month,'res' if residential else 'gs1')+(.000921 if residential else .000847))
    expected+=min(kwh,2500)*.001565+max(kwh-2500,0)*.001055+(1. if residential else 10.)
    assert sum(r['lines'].values())==pytest.approx(expected,abs=1e-7)
    assert r['is_complete_bill'] is True
    assert r['excluded_components']==[]


@pytest.mark.parametrize('plan',list(va.PLAN_INFO))
@pytest.mark.parametrize('month',range(1,10))
def test_every_structure_full_january_through_september(plan,month):
    start=pd.Timestamp(2026,month,1);end=start+pd.DateOffset(months=1)
    r=bill(plan,start.isoformat(),end.isoformat())
    assert r['is_complete_bill']
    assert all(np.isfinite(float(v)) for v in r['lines'].values())
    assert 'deferred_fuel' in r['lines'] and 'rider_RBB' in r['lines']
    assert r['lines']['rider_RBB']>=0
    assert r['rate_components']['base']['effective_start']=='2026-01-01'
    for name,records in r['rate_components'].items():
        if name=='base':continue
        assert all(record['effective_start']<=end.date().isoformat() or record.get('status')=='not_yet_effective' for record in records)
        assert all(len(record['pdf_sha256'])==64 for record in records)


@pytest.mark.parametrize('plan',list(va.PLAN_INFO))
def test_final_partial_october_all_structures(plan):
    r=bill(plan,'2026-10-01','2026-10-16',patch={'cycle_kind':'final','cycle_source':'Explicit hypothetical final meter cycle'})
    assert r['is_complete_bill']
    assert r['metrics']['proration_factor']==.5


def test_cerc_suspended_january_filing_never_charged_and_march_begins():
    for month in (1,2):
        r=bill('VA-1',f'2026-{month:02}-01',f'2026-{month+1:02}-01')
        assert r['lines']['rider_CERC']==0.
        assert r['rate_components']['CERC'][0]['status']=='not_yet_effective'
        assert r['rate_components']['CERC'][0]['document_id']==386988
        assert r['rate_components']['CERC'][0]['page']==5
        assert r['rate_components']['CERC'][0]['supporting_pages']==[2,5]
    assert bill('VA-1','2026-03-01','2026-04-01')['lines']['rider_CERC']==pytest.approx(743*.000754)


@pytest.mark.parametrize('start,end', [('2026-01-16','2026-02-16'),('2026-02-16','2026-03-16'),('2026-03-16','2026-04-16'),('2026-04-16','2026-05-16'),('2026-05-16','2026-06-16'),('2026-06-16','2026-07-16'),('2026-07-16','2026-08-16'),('2026-08-16','2026-09-16')])
def test_actual_energy_intervals_cross_each_rate_boundary(start,end):
    idx=index(start,end);load=np.where(idx.day<=15,3.,1.)
    r=bill('VA-1',start,end,load)
    expected=sum(float(p)*.5*monthly_sum(stamp.month,'res') for stamp,p in zip(idx,load))
    actual=sum(value for name,value in r['lines'].items() if name.startswith('rider_') or name=='deferred_fuel')
    assert actual==pytest.approx(expected,abs=1e-8)
    assert r['lines']['customer']==7.58


def test_demand_rate_change_requires_explicit_confirmed_allocation():
    with pytest.raises(ValueError,match='demand-rider rate changes'):
        bill('VA-GS2T','2026-02-16','2026-03-16')
    patch={'demand_rate_change_allocation':'calendar_day_prorated_cycle_peak','demand_rate_change_source':'Explicit hypothetical utility-confirmed days applied to whole-cycle peak'}
    r=bill('VA-GS2T','2026-02-16','2026-03-16',power=90.,patch=patch)
    assert r['metrics']['peak_kw']==90.
    #13 February days +15 March days. DST does not turn a local day into23/24.
    assert r['lines']['rider_CERC']==pytest.approx(90.*.208*15/30)
    assert r['metrics']['proration_factor']==28/30


@pytest.mark.parametrize('plan',list(va.PLAN_INFO))
def test_every_january_expression_fixed_schedule_exact_milp(plan):
    import cvxpy as cp
    idx=index('2026-01-01','2026-02-01');a=va.defaults(plan);a['billing_month']=1
    load=1. if a['customer_class']=='residential' else 10. if plan in ('VA-GS1','VA-5C','VA-5P') else 90. if plan in ('VA-GS2','VA-GS2T') else 600.
    power=cp.Variable(len(idx));m=BillingMath(idx,convex=True,power_bound=1000.)
    m.register(power,0.,1000.);m.constraints.append(power==load)
    r=va.charge_lines(idx,power,cp.Constant(np.zeros(len(idx))),a,math=m)
    problem=cp.Problem(cp.Minimize(sum(r['lines'].values())),m.constraints)
    assert problem.is_dcp()
    problem.solve(solver='HIGHS',highs_options={'time_limit':20.})
    assert problem.status=='optimal'
    assert problem.value==pytest.approx(sum(bill(plan,power=load)['lines'].values()),abs=1e-6)


def test_nem_dated_terms_and_standby_threshold_are_not_backdated():
    def account(start,capacity):
        a=va.defaults('VA-1');a.update(solar_mode='net_metering',parallel_service=True,parallel_operation_approved=True,nem=va.nem_defaults('VA-1',start));a['nem']['approved_capacity_ac_kw']=capacity
        return a
    with pytest.raises(ValueError,match='terms begin 2026-02-05'):
        va.validate_account(account('2026-01-01',8.),index('2026-01-01','2026-02-01'))
    with pytest.raises(ValueError,match='above 15 kW'):
        va.validate_account(account('2026-06-01',18.),index('2026-06-01','2026-07-01'))
    assert va.validate_account(account('2026-07-01',18.),index('2026-07-01','2026-08-01'))
    with pytest.raises(ValueError,match='NEM meter cycle crosses dated rates'):
        va.validate_account(account('2026-03-16',8.),index('2026-03-16','2026-04-16'))


def test_2026_actual_sources_and_base_correction_hashes():
    from src.billing.dominion_va_2026_data import SOURCE_DOCUMENTS
    root=Path(__file__).parents[1]/'docs/utility_sources/dominion/va_history_research/approved_2024_2025'
    manifest=json.loads((root/'manifest.json').read_text());rows={item['document']['DocID']:item for item in manifest['filings']}
    for doc,source in SOURCE_DOCUMENTS.items():
        assert rows[doc]['pdf_sha256']==source['pdf_sha256']
        text=root/rows[doc]['text_file'];assert hashlib.sha256(text.read_bytes()).hexdigest()==rows[doc]['text_sha256']
    source=base_metadata('VA-10-secondary',index('2026-01-01','2026-02-01'))
    assert source['document_id']==385824 #Dec18 correction replacesDec9Schedule10.
    assert source['pages']==list(range(4,12))


@pytest.mark.parametrize('plan',list(va.PLAN_INFO))
def test_independent_january_whole_bill_for_every_structure(plan):
    #January2026 has744hours,22weekdays; NewYear's exclusion leaves21
    #holiday-excluding weekdays. GS2T/3/4 include January1 in weekday pricing.
    from collections import Counter
    r=bill(plan);kwh=float(r['metrics']['import_kWh']);f=31/30
    p=1. if plan in ('VA-1','VA-1G','VA-1S','VA-1T') else 10. if plan in ('VA-GS1','VA-5C','VA-5P') else 90. if plan in ('VA-GS2','VA-GS2T') else 600.
    reactive=600*np.tan(np.arccos(.95))
    if plan=='VA-1':
        first=min(kwh,800);base=7.58+first*(.035690+.030064)+(kwh-first)*(.023596+.026965)+kwh*.00970
    elif plan=='VA-1G':
        base=7.58+126*(.041294+.119944)+155*(.024315+.015514)+463*(.028185+.017867)+kwh*.00970
    elif plan=='VA-1S':
        base=12.99+2.478+2.407+168*.031424+576*.002911+kwh*(.015465+.00970)
    elif plan=='VA-1T':
        base=12.99+168*(.080512+.056744)+576*(.008440+.014167)+kwh*.00970
    elif plan=='VA-GS1':
        base=13.39+1400*(.025525+.030788)+(kwh-1400)*(.018928+.019886)+kwh*.00582
    elif plan=='VA-5C':
        base=13.88+3000*(.029255+.039064)+(kwh-3000)*(.024674+.036161)+kwh*.00887
    elif plan=='VA-5P':
        base=23.01+10*(4.055+3.834)+10*(315*.014615+429*.006928)+kwh*(.010088+.00887)
    elif plan=='VA-GS2':
        block=150*90*f
        base=(31.90+90*(4.963+.588+1.971))*f+kwh*.000079
        base+=block*(.039031+.021879+.009461)+(kwh-3*block)*.002301
    elif plan=='VA-GS2T':
        base=(37.08+90*(4.963+2.215+2.313))*f+kwh*.000079+90*(330*.020278+414*.009928)
    elif plan in ('VA-GS3','VA-GS4-primary','VA-GS4-transmission'):
        if plan=='VA-GS3':base=(185.34+600*(3.316+8.976+2.277)+60*.320+reactive*.235)*f+kwh*.000111
        elif plan=='VA-GS4-primary':base=(343.54+600*(2.717+9.436+2.371)+60*.558+reactive*.393)*f+kwh*.000157
        else:base=(343.54+600*(9.280+2.310)+60*.558+reactive*.393)*f+kwh*.000157
        base+=600*(330*.004648+414*.003299)
    else:
        source=Path(__file__).parents[1]/'docs/utility_sources/dominion/va_history_research/schedule10_calendar_2017_2026.json'
        records=json.loads(source.read_text())['records'];count=Counter(value for day,value in records.items() if day.startswith('2026-01-'))
        secondary=plan=='VA-10-secondary';primary=plan=='VA-10-primary'
        base=(201.65+600*((3.316 if secondary else 2.717 if primary else 0.)+(1.094 if secondary else .646)))*f+kwh*(.001682 if secondary else .001771)
        base+=600*sum(count[label]*(10*on+14*off) for label,on,off in [('A',.278424,.074905),('B',.022304,.010106),('C',.017001,.009477)])
    if plan in ('VA-1','VA-1G','VA-1S','VA-1T'):
        riders=kwh*sum(JAN_RES);sales=.000921;local=1.
    elif plan=='VA-GS1':riders=kwh*sum(JAN_GS1);sales=.000847;local=10.
    elif plan in ('VA-5C','VA-5P'):
        riders=kwh*sum((.029680,.000237,.001371,.001765,.003996,0.,.004295,.000636,.008697,.011736,.007676,.000291,.003560,.009874,.002906,.000368));sales=.000917;local=10.
    elif plan in ('VA-GS2','VA-GS2T'):
        dist,bb,trans=(1.044,.075,2.929) if plan=='VA-GS2' else (.806,.058,3.526)
        riders=kwh*sum((.029680,.000157,.000911,.001765,.007676,.002906))
        riders+=90*f*sum((dist,bb,trans,.955,0.,.182,2.354,3.100,.084,1.022));sales=.000712;local=10.
    elif plan=='VA-GS3':
        riders=kwh*sum((.029680,.000121,.000702,.001765,.007676,.002906))+600*f*sum((.259,.050,3.774,.730,0.,.167,1.831,2.565,.077,.937));sales=.000541;local=10.
    elif plan.startswith('VA-GS4'):
        primary=plan=='VA-GS4-primary'
        demand=(.229,.039,4.175,.425,0.,.147,1.909,1.994,.069,.836) if primary else (0.,0.,4.129,.418,0.,.145,1.860,1.961,.068,.822)
        riders=kwh*sum((.029680,.000095,.000543,.001765,.007676,.002906))+600*f*sum(demand);sales=.000440;local=10.
    elif plan=='VA-10-secondary':
        riders=kwh*sum((.029680,.000121,.000702,.001765,.001414,0.,.000322,.003542,.004971,.007676,.000150,.001812,.002906))+600*f*(.259+.050+2.880);sales=.000541;local=10.
    else:
        primary=plan=='VA-10-primary'
        riders=kwh*sum((.029680,.000095,.000543,.001765,.000731,0.,.000252,.003267,.003431,.007676,.000118,.001432,.002906))+600*f*(3.201+(.229+.039 if primary else 0.));sales=.000440;local=10.
    tax=min(kwh,2500)*.001565+min(max(kwh-2500,0),47500)*.001055+max(kwh-50000,0)*.000845
    assert sum(r['lines'].values())==pytest.approx(base+riders+kwh*sales+tax+local,abs=1e-7)


def test_july_t1_actual_original_closes_intermediate_version():
    from src.billing.dominion_va_2026_data import T1_JULY_REVISION
    root=Path(__file__).parents[1]/'docs/utility_sources/dominion/va_history_research'
    source=json.loads((root/'t1_2026_07_01_source.json').read_text())
    assert source['pdf_sha256']==T1_JULY_REVISION['pdf_sha256']=='d95972e31c015c58983634cbad1cfbf41298dccfbf7bca64f0a6e7bdd2f76651'
    text=(root/source['text_file']).read_bytes()
    assert hashlib.sha256(text).hexdigest()==source['text_sha256']
    assert source['filed_on']=='2026-06-18'
    assert source['archive_timestamp']=='20260719064330'
    c=Components(index('2026-06-16','2026-07-16'),va.RATE_COMPONENTS)
    assert [row['effective_start'] for row in c.metadata['T1']]==['2025-09-01','2026-07-01']
    assert c.rate('T1','gs2t')==pytest.approx(np.full(len(c.index),3.526))
    assert c.metadata['T1'][1]['pdf_sha256']==source['pdf_sha256']


@pytest.mark.parametrize('plan',['VA-1','VA-GS1','VA-GS2T','VA-GS3','VA-10-primary'])
def test_cross_rate_cycle_numeric_and_exact_optimization_share_all_lines(plan):
    import cvxpy as cp
    start,end='2026-05-16','2026-06-16';idx=index(start,end)
    a=va.defaults(plan);a.update(billing_month=6,demand_rate_change_allocation='calendar_day_prorated_cycle_peak',demand_rate_change_source='Explicit hypothetical utility-confirmed allocation')
    load=1. if plan=='VA-1' else 10. if plan=='VA-GS1' else 90. if plan=='VA-GS2T' else 600.
    m=BillingMath(idx,convex=True,power_bound=1000.);power=cp.Variable(len(idx));m.register(power,0.,1000.);m.constraints.append(power==load)
    r=va.charge_lines(idx,power,cp.Constant(np.zeros(len(idx))),a,math=m)
    problem=cp.Problem(cp.Minimize(sum(r['lines'].values())),m.constraints);assert problem.is_dcp()
    problem.solve(solver='HIGHS',highs_options={'time_limit':20.});assert problem.status=='optimal'
    q=bill(plan,start,end,power=load,patch=a)
    for name,expression in r['lines'].items():
        assert float(expression.value if hasattr(expression,'value') else expression)==pytest.approx(q['lines'][name],abs=1e-6)


def test_2026_missing_component_is_not_silently_extended(monkeypatch):
    from src.billing import dominion_va_2026 as dated
    before=deepcopy(dated.PREDECESSORS)
    monkeypatch.delitem(dated.PREDECESSORS,'CE')
    with pytest.raises(ValueError,match='Missing verified 2026 Dominion component CE'):
        Components(index('2026-01-01','2026-02-01'),va.RATE_COMPONENTS)
    assert before['CE'][0]=='2025-05-01'
