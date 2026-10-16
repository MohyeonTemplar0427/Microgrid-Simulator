"""Filed Dominion Virginia retail charges, separate from PJM wholesale prices.

All arithmetic is shared between numeric billing and bounded optimization through
``regional_math``. A source version is never extended into an unverified date.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import date, timedelta
import math as _math
import numpy as np
import pandas as pd

UTILITY = 'dominion_va'
TIMEZONE = 'America/New_York'
VERIFIED_START = date(2026, 1, 1)
VERIFIED_END = date(2026, 10, 15)
SOURCE = 'https://www.dominionenergy.com/-/media/content/rates-and-tariffs/pdfs/virginia/'
FULL_SOURCE = SOURCE + 'shared/entire-filed-tariff.pdf'
SOURCES = [FULL_SOURCE, 'https://www.dominionenergy.com/virginia/rates-and-tariffs/residential-rates',
           'https://www.dominionenergy.com/virginia/rates-and-tariffs/business-rates',
           'https://henrico.gov/finance/approved-tax-rates-and-schedule/']
# Dollars/kWh, except where tuple includes dollars/kW. Independent filed dates
# remain in RATE_COMPONENTS; the executable intersection is not a plan's inception.
RATE_COMPONENTS = {
 'A': {'effective_start':'2026-07-01','page':321,'all':.037648},
 'C1A': {'effective_start':'2026-09-01','page':322,'res':.000454,'gs1':.000384,'gs2':.000335,'gs3':.000271,'gs4':.000212,'church':.000513},
 'C4A': {'effective_start':'2026-09-01','page':323,'res':.001322,'gs1':.001116,'gs2':.000967,'gs3':.000834,'gs4':.000698,'church':.001480},
 'CCR': {'effective_start':'2026-01-01','page':324,'all':.001765},
 'CE': {'effective_start':'2026-05-01','page':325,'res':.006054,'gs1':.004673,'gs2':(.004480,1.633),'gs3':1.090,'gs4p':.507,'gs4t':.499,'church':.007423},
 'CERC': {'effective_start':'2026-03-01','page':326,'res':.000754,'gs1':.000541,'gs2':(.000574,.208),'gs3':.189,'gs4p':.161,'gs4t':.158,'church':.000756},
 'DIST': {'effective_start':'2026-06-01','page':331,'res':.007685,'gs1':.005780,'gs2_non_demand':.004174,'gs2_demand':1.482,'gs2t':1.169,'gs3':.403,'gs4p':.311,'gs4t':0.,'church':.006294},
 'E': {'effective_start':'2025-11-01','page':332,'res':.000625,'gs1':.000456,'gs2':(.000502,.182),'gs3':.167,'gs4p':.147,'gs4t':.145,'church':.000636},
 'GEN': {'effective_start':'2026-04-01','page':344,'res':.005729,'gs1':.004100,'gs2':(.004375,1.581),'gs3':1.118,'gs4p':.993,'gs4t':.967,'church':.006420},
 'OSW': {'effective_start':'2026-09-01','page':345,'res':.011362,'gs1':.009229,'gs2':(.009231,3.366),'gs3':2.911,'gs4p':2.437,'gs4t':2.396,'church':.013210},
 'PIPP': {'effective_start':'2025-04-01','page':346,'all':0.},
 'RGGI': {'effective_start':'2025-04-01','page':349,'all':0.},
 'RPS': {'effective_start':'2026-09-01','page':350,'all':.005520},
 'SMR': {'effective_start':'2026-09-01','effective_end':'2027-08-31','page':351,'res':.000147,'gs1':.000124,'gs2':(.000130,.046),'gs3':.044,'gs4p':.041,'gs4t':.040,'church':.000166},
 'SNA': {'effective_start':'2026-09-01','page':352,'res':.004027,'gs1':.003429,'gs2':(.003674,1.322),'gs3':1.073,'gs4p':.901,'gs4t':.886,'church':.004691},
 'T1': {'effective_start':'2026-09-01','page':353,'res':.012730,'gs1':.011929,'gs2_non_demand':.029476,'gs2_demand':3.798,'gs2t':4.554,'gs3':3.972,'gs4p':4.729,'gs4t':4.673,'church':.012823},
 'deferred_fuel': {'effective_start':'2026-08-01','page':318,'all':.002901},
 'sales_use_tax': {'effective_start':'2026-01-01','page':374,'res':.000921,'gs1':.000847,'gs2':.000712,'gs3':.000541,'gs4p':.000440,'gs4t':.000440,'church':.000917},
}
PLAN_INFO = {
 'VA-1': ('Residential Schedule 1','residential','800-kWh seasonal energy blocks', [105,106,107]),
 'VA-1G': ('Residential Schedule 1G Off-Peak','residential','AMI, no demand-response enrollment; three TOU buckets', [108,109,110,111]),
 'VA-1S': ('Residential Schedule 1S Demand TOU','residential','30-minute on-peak demand and TOU energy', [116,117,118,119]),
 'VA-1T': ('Residential Schedule 1T Energy TOU','residential','two TOU buckets', [120,121,122]),
 'VA-GS1': ('GS-1 Small General Service','commercial','No more than two >=30-kW peaks in current/prior eleven cycles', [160,161,162,163,164]),
 'VA-GS2': ('GS-2 Intermediate General Service','commercial','Initial three >=30-kW peaks; confirmed existing accounts retain service while a qualifying peak remains; no more than two >=500-kW peaks', [170,171,172,173,174,175,176]),
 'VA-GS2T': ('GS-2T Intermediate General Service TOU','commercial','Voluntary bundled service; same GS-2 demand eligibility', [177,178,179,180]),
 'VA-GS3': ('GS-3 Large General Service Secondary','commercial','Initial three >=500-kW qualifying peaks; existing-account retention; secondary service', [186,187,188,189,190,191,192,193,194]),
 'VA-GS4-primary': ('GS-4 Large General Service Primary','commercial','Initial three >=500-kW qualifying peaks; existing-account retention; verified primary service classification', [202,203,204,205,206,207,208,209,210]),
 'VA-GS4-transmission': ('GS-4 Large General Service Transmission','commercial','Initial three >=500-kW qualifying peaks; existing-account retention; >=69-kV normal delivery', [202,203,204,205,206,207,208,209,210]),
 'VA-10-secondary': ('Schedule 10 Variable Rate Secondary','commercial','Existing >=500-kW qualifying account; official daily A/B/C calendar; unity-PF model; no demand-response enrollment',list(range(250,258))),
 'VA-10-primary': ('Schedule 10 Variable Rate Primary','commercial','Existing >=500-kW qualifying account; official daily A/B/C calendar; unity-PF model; no demand-response enrollment',list(range(250,258))),
 'VA-10-transmission': ('Schedule 10 Variable Rate Transmission','commercial','Existing >=500-kW qualifying account; official daily A/B/C calendar; unity-PF model; >=69kV',list(range(250,258))),
 'VA-5C': ('5C Church and Synagogue','commercial','Sanctuary meter only; excludes parallel operation', [150,151]),
 'VA-5P': ('5P Worship and Charitable Institution TOU','commercial','Qualifying worship/charity account; excludes parallel operation', [152,153,154]),
}
NEM_PLANS = ('VA-1','VA-1G','VA-1S')
NEM_SOURCE = SOURCE + 'terms-conditions/vatc25ra.pdf'
BASE_EFFECTIVE_START = {plan:'2026-01-01' for plan in PLAN_INFO}
# Filed Schedule 10 supply riders are volumetric, unlike GS3/4 demand riders.
# The suffix indicates secondary versus primary/transmission delivery.
SCHEDULE10_ENERGY_RIDERS = {
 'C1A':(.000271,.000212),'C4A':(.000834,.000698),'CE':(.002126,.000826),
 'CERC':(.000365,.000275),'E':(.000322,.000252),'GEN':(.002163,.001700),
 'OSW':(.005678,.003972),'SMR':(.000087,.000070),'SNA':(.002101,.001530),
}
for _component,(_secondary,_high_voltage) in SCHEDULE10_ENERGY_RIDERS.items():
    RATE_COMPONENTS[_component].update({'10s':_secondary,'10p':_high_voltage,'10t':_high_voltage})
RATE_COMPONENTS['DIST'].update({'10s':.403,'10p':.311,'10t':0.})
RATE_COMPONENTS['T1'].update({'10s':3.897,'10p':3.988,'10t':3.988})
RATE_COMPONENTS['sales_use_tax'].update({'10s':.000541,'10p':.000440,'10t':.000440})


def catalog():
    entries=[]
    for key,(name,customer,eligibility,pages) in PLAN_INFO.items():
        historical=key in ('VA-1','VA-GS1')
        coverage=([{'start':'2025-01-01','end':'2025-12-31','is_complete_bill':False,
                    'scope':'Verified historical bundled charges; explicitly missing dated taxes'}] if historical else [])
        coverage.append({'start':str(VERIFIED_START),'end':str(VERIFIED_END)})
        entries.append({'id':key,'tariff':key,'name':name,'label':name,'status':'supported','reason':'','utility':UTILITY,'jurisdiction':'VA',
          'customer_class':customer,'supply_arrangements':['bundled'],
          'coverage':coverage,
          'verified_start':coverage[0]['start'],'verified_end':str(VERIFIED_END),
          'base_effective_start':BASE_EFFECTIVE_START[key],
          'billing_supported':True,'dispatch_supported':True,'eligibility':eligibility,
          'representative_peak_kw':3. if customer=='residential' else 20. if key in ('VA-GS1','VA-5C','VA-5P') else 90. if key in ('VA-GS2','VA-GS2T') else 600.,
          'equipment_modes':['grid_only'] if key in ('VA-5C','VA-5P') else ['grid_only','pv_only','pv_battery','storage_only'],
          'electrical_replay':'secondary_service_reference_only',
          'sources':SOURCES+(['https://www.dominionenergy.com/schedule10'] if key.startswith('VA-10-') else []),'source_pages':pages,
          'account_fields':account_fields(),
          'solar_modes':['non_export','net_metering'] if key in NEM_PLANS else ['non_export'],
          'nem_coverage':([{'start':'2026-02-05','end':'2026-06-30','maximum_ac_kw':15.},{'start':'2026-07-01','end':str(VERIFIED_END),'maximum_ac_kw':20.}] if key in NEM_PLANS else []),
          'solar_unsupported_reason':('Residential NEM uses verified terms from February5,2026, with <=15kW AC before July1 and <=20kW thereafter; annual/PPA and multi-rate netting cycles need separate settlement.' if key in NEM_PLANS else '1T and 5C/5P are not eligible NEM plans; commercial NEM load-factor/minimum/reactive-demand interactions require a separately reconciled adapter.'),
          'limitations':[('2025 verified charges exclude missing dated taxes; complete ordinary 2026 components begin January 1.' if historical else '2026 ordinary rates are dated; 2025 and earlier composites for this structure are not executable.'),'NEM begins February 5, 2026, <=15 kW AC before July and <=20 kW thereafter; no annual boundary, multi-rate cycle or PPA.']})
    unavailable={
      'VA-1W':'Separately metered utility-controlled water-heating service requires a second meter and its fixed-EST control schedule.',
      'VA-1P':'Closed residential TOU account needs grandfathered enrollment evidence.',
      'VA-DP-R':'Closed experimental dynamic pricing needs actual day classifications and critical periods.',
      'VA-DP1':'Closed experimental dynamic pricing needs actual day classifications and critical periods.',
      'VA-DP2':'Closed experimental dynamic pricing needs actual day classifications and critical periods.',
      'VA-GS3EV':'Experimental separately metered public EV charging with 250-account participation limit.',
      'VA-5':'Closed small-general-service enrollment and separate rates are not implemented.',
      'VA-6':'Closed large-general-service enrollment and separate rates are not implemented.',
      'VA-7':'Closed electric-heating enrollment and separate rates are not implemented.',
      'VA-8':'Supplementary/maintenance/standby service requires generator-specific contracted demand.',
      'VA-6TS':'Requires utility-approved electric thermal-storage equipment, its operating constraints and separate thermal-energy state; an electrochemical battery is not eligible thermal storage.',
      'VA-1G-rebate':'Closed experimental rebate commitment and thermostat operation need the actual rebate/enrollment contract; ordinary 1G remains available.',
      'VA-1EV':'Closed residential EV pilot requires grandfathered enrollment and its distinct metering/control conditions.',
      'VA-EV':'Closed separately metered EV pilot requires enrollment evidence and its separate meter.',
      'VA-EVCF':'Fleet charging service recovers utility-owned charging facilities; requires the installation/service agreement.',
      'VA-EVCL2':'Level2 charging-facility service requires the actual utility equipment and customer agreement.',
      'VA-EVCR':'Utility-owned residential charging-facility service requires the executed equipment/service agreement.',
      'VA-EVFCP':'Public utility DC fast-charger session price requires session energy/time inputs, not a building meter bill.',
      'VA-EVL2P':'Public utility Level2 charging session price requires charger/session inputs, not a building meter bill.',
      'VA-19':'Qualifying-facility wholesale power purchase requires generator certification, export metering and an executed power-purchase agreement.',
      'VA-CFG':'Experimental carbon-free/renewable generation supply requires an actual eligible supply-resource agreement.',
      'VA-RF':'Environmental-attribute purchase is an incentive/REC transaction, not ordinary electricity service; requires the accepted facility contract.',
      'VA-SP':'Closed experimental solar purchase requires grandfathered enrollment and separate generator-meter accounting.',
      'VA-24-29':'Outdoor-lighting tariffs require fixture wattage/count/ownership/burn-hour contracts and separate lighting bill components.',
      'VA-MSS-SS':'Shared/multifamily solar requires the utility-approved subscription allocation, subscriber minimum bill and bill-date-specific credit ledger.',
      'VA-GS5':'25-MW large-load tariff starts 2027; not ordinary commercial service and unavailable before its effective date.',
      'VA-MBR':'Market-based retail service needs the actual priced supply arrangement and NSPL obligations.',
      'VA-SCR':'Special contract rate requires the executed supplier/account contract.',
    }
    entries.extend({'id':key,'tariff':key,'name':key,'label':key,'utility':UTILITY,'jurisdiction':'VA','billing_supported':False,
                    'dispatch_supported':False,'status':'unsupported','reason':reason,'sources':SOURCES,
                    'coverage':[]} for key,reason in unavailable.items())
    return entries


def account_fields():
    """Describe account facts without inferring them from a facility profile."""
    fields=[
        ('phase','Service phase','choice',['single','three']),
        ('voltage','Utility service classification','choice',['secondary','primary','transmission']),
        ('supply_arrangement','Retail electricity supplier arrangement','choice',['bundled','third_party']),
        ('locality','Actual locality for utility-consumer tax; unverified yields an incomplete bill','text',None),
        ('eligibility_confirmed','Tariff eligibility confirmed or explicitly hypothetical','boolean',None),
        ('existing_tariff_enrollment_confirmed','Existing service under this tariff; required for declining-demand retention','boolean',None),
        ('ordinary_use_confirmed','Ordinary residential/commercial use; no special large-load terms','boolean',None),
        ('parallel_service','Existing parallel-service contract applies in every scenario','boolean',None),
        ('parallel_operation_approved','Utility-approved PV/storage parallel operation','boolean',None),
        ('contract_demand_kw','Utility-assigned existing parallel contract demand (kW)','number',None),
        ('contract_minimum_charge','Existing contractual minimum charge (USD)','number',None),
        ('established_minimum_kw','Utility-established minimum demand including transformer/contract (kW)','number',None),
        ('history','Eleven prior cycles, oldest first: billing month and actual maximum/on-peak kW','object',None),
        ('reactive_peak_kvar','Current cycle measured or explicitly synthetic reactive peak (kvar)','number',None),
        ('solar_mode','Approved solar operating and billing arrangement','choice',['non_export','net_metering']),
        ('nem','NEM current-rule eligibility, capacity, meter-year and dated TOU bank evidence','object',None),
        ('demand_rate_change_allocation','Confirmed allocation for a cycle crossing demand rates','choice',['unconfirmed','calendar_day_prorated_cycle_peak']),
        ('demand_rate_change_source','Utility bill or confirmed allocation evidence for demand-rate transitions','text',None),
        ('ami','AMI meter installed','boolean',None),
        ('demand_response_enrolled','PJM/company demand-response enrollment','boolean',None),
        ('tou_reenrollment_eligible','TOU one-year reenrollment restriction satisfied','boolean',None),
    ]
    return [{'name':name,'label':label,'type':kind,**({'choices':choices} if choices else {})} for name,label,kind,choices in fields]


def defaults(plan_id=None):
    """Explicit hypothetical facts, never inferred from ZIP/state/PJM zone."""
    plan_id=plan_id or 'VA-1G'
    if plan_id not in PLAN_INFO:
        raise ValueError('Choose an executable Dominion Virginia plan.')
    residential=PLAN_INFO[plan_id][1]=='residential'
    large=plan_id in ('VA-GS3','VA-GS4-primary','VA-GS4-transmission') or plan_id.startswith('VA-10-')
    small=plan_id=='VA-GS1'
    peak=12. if residential else 600. if large else 20. if small else 90.
    return {'tariff':plan_id,'customer_class':PLAN_INFO[plan_id][1],
        'supply_arrangement':'bundled','eligibility_confirmed':True,'ordinary_use_confirmed':True,
        'existing_tariff_enrollment_confirmed':True,
        'special_riders':False,'metering_side':'customer','locality':'henrico','billing_month':9,
        'demand_rate_change_allocation':'unconfirmed','demand_rate_change_source':'',
        'phase':'single' if residential or small else 'three',
        'voltage':'primary' if plan_id in ('VA-GS4-primary','VA-10-primary') else 'transmission' if plan_id in ('VA-GS4-transmission','VA-10-transmission') else 'secondary',
        'delivery_voltage_kv':69. if plan_id in ('VA-GS4-transmission','VA-10-transmission') else 12.47 if plan_id in ('VA-GS4-primary','VA-10-primary') else .24 if residential or small else .48,
        'primary_service_confirmed':True,'parallel_service':False,'parallel_operation_approved':False,
        'contract_demand_kw':peak,'contract_minimum_charge':0.,'established_minimum_kw':525. if large else 0.,
        'minimum_demand_basis_confirmed':True,'power_factor':1. if plan_id.startswith('VA-10-') else .95,
        'reactive_peak_kvar':0. if plan_id.startswith('VA-10-') else peak*_math.tan(_math.acos(.95)),
        'history':[{'billing_month':m,'maximum_kw':peak,'on_peak_kw':peak} for m in (10,11,12,1,2,3,4,5,6,7,8)],
        'ami':True,'demand_response_enrolled':False,'tou_reenrollment_eligible':True,
        'worship_charity_eligible':plan_id in ('VA-5C','VA-5P'),'solar_mode':'non_export','nem':None,
        'schedule10_original_enrollment_confirmed':plan_id.startswith('VA-10-'),
        'unity_power_factor_model_confirmed':plan_id.startswith('VA-10-')}


def _number(value,name,minimum=0.):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not _math.isfinite(value) or value<minimum:
        raise ValueError(f'{name} must be finite and at least {minimum}.')
    return float(value)


def nem_defaults(plan_id='VA-1G',period_start='2026-09-01'):
    """Explicit hypothetical first-cycle NEM facts; never account verification."""
    tiers=('all',) if plan_id=='VA-1' else ('on_peak','off_peak','super_off_peak') if plan_id=='VA-1G' else ('on_peak','off_peak')
    return {'terms_version':'2026-02-05','permission_to_operate':True,
        'approved_capacity_ac_kw':8.,'sizing_approved':True,'ppa':False,
        'period_start':period_start,'bank_as_of':period_start,
        'bank_kwh':{tier:0. for tier in tiers},
        'bank_source':'Explicit hypothetical first-cycle zero opening ledger',
        'storage_restrictions_confirmed':True}


def _validate_nem(account,idx,equipment=None,state=None):
    tariff=account['tariff'];nem=account.get('nem')
    if tariff not in NEM_PLANS:
        raise ValueError('Net-metering billing is currently verified only for residential 1/1G/1S; commercial settlement and 1T/5C/5P eligibility are not inferred.')
    if not account['parallel_service'] or account.get('parallel_operation_approved') is not True:
        raise ValueError('Net-metering requires explicitly approved parallel operation.')
    if not isinstance(nem,dict) or nem.get('terms_version')!='2026-02-05' or nem.get('permission_to_operate') is not True or nem.get('sizing_approved') is not True:
        raise ValueError('Net-metering requires current filed terms, permission to operate and utility-approved generation sizing.')
    if idx[0].date()<date(2026,2,5):
        raise ValueError('Verified NEM terms begin 2026-02-05; the prior terms version is not substituted.')
    capacity=_number(nem.get('approved_capacity_ac_kw'),'approved NEM capacity',.000001)
    standby_threshold=15. if idx[0].date()<date(2026,7,1) else 20.
    if capacity>standby_threshold:
        raise ValueError(f'Residential NEM above {standby_threshold:g} kW AC in this dated version needs verified standby-demand rounding and rider treatment; it is not silently billed without standby.')
    if equipment and equipment.get('pv') and equipment.get('pv_ac_kw') is not None:
        if _number(equipment['pv_ac_kw'],'PV AC rating')>capacity+1e-7:
            raise ValueError('Configured PV AC capacity exceeds the explicitly utility-approved NEM capacity.')
    if nem.get('ppa') is not False:
        raise ValueError('NEM PPA annual excess-generation compensation needs the actual contract and applicable DOMZONE annual price; this monthly path does not price it.')
    if equipment and equipment.get('battery') and nem.get('storage_restrictions_confirmed') is not True:
        raise ValueError('Confirm NEM storage uses renewable-only charging and no battery backfeed under the approved operating sequence.')
    try:
        period_start=pd.Timestamp(nem['period_start']).tz_localize(TIMEZONE)
        period_end=period_start+pd.DateOffset(years=1)
    except (KeyError,TypeError,ValueError) as exc:
        raise ValueError('Provide the first meter-reading date of the actual 12-month NEM period.') from exc
    stop=idx[-1]+(idx[1]-idx[0])
    if idx[0]<period_start or stop>=period_end:
        raise ValueError('Annual NEM boundaries require separately verified bank-origin/carry-cap settlement; this adapter supports monthly carryover strictly within the stated NEM year.')
    if tariff=='VA-1G' and len(set((5<=m<=9) for m in idx.month))!=1:
        raise ValueError('A Schedule 1G NEM cycle crossing the seasonal energy-price boundary requires verified credit allocation between seasons; no average price is assumed.')
    ledger=(state or {}).get('nem',nem)
    if not isinstance(ledger,dict) or ledger.get('period_start')!=nem['period_start'] or ledger.get('bank_as_of')!=idx[0].date().isoformat():
        raise ValueError('The NEM opening ledger must identify this period and the exact first service date; gaps or stale banks cannot be silently carried.')
    tiers=('all',) if tariff=='VA-1' else ('on_peak','off_peak','super_off_peak') if tariff=='VA-1G' else ('on_peak','off_peak')
    banks=ledger.get('bank_kwh')
    if not isinstance(banks,dict) or set(banks)!=set(tiers):
        raise ValueError('Supply explicit NEM opening kWh banks for every applicable tariff TOU tier.')
    for tier,value in banks.items(): _number(value,'opening NEM '+tier+' bank')
    if not isinstance(ledger.get('bank_source'),str) or not ledger['bank_source'].strip():
        raise ValueError('Provide the opening NEM bank provenance or explicitly label hypothetical zero banks.')
    return tiers,ledger


def validate_state(account,index,*,state=None,equipment=None):
    if account.get('solar_mode')=='net_metering':
        _validate_nem(account,pd.DatetimeIndex(index),equipment=equipment,state=state)


def objective_inputs(account,state=None,policy='exclude_opening_credits'):
    """Opening credits reduce the reported bill without changing default dispatch."""
    if policy not in ('exclude_opening_credits','explicit_cash_bill'):
        raise ValueError('Select exclude_opening_credits or explicit_cash_bill explicitly.')
    result=deepcopy(account);next_state=deepcopy(state)
    if policy=='exclude_opening_credits' and account.get('solar_mode')=='net_metering':
        for ledger in [result.get('nem'),(next_state or {}).get('nem')]:
            if ledger is not None:
                ledger['bank_kwh']={tier:0. for tier in ledger['bank_kwh']}
    return result,next_state


def validate_account(account,index,equipment=None):
    if not isinstance(account,dict): raise ValueError('Provide the Dominion Virginia account facts.')
    tariff=account.get('tariff')
    if tariff not in PLAN_INFO:
        reason=next((x.get('reason') for x in catalog() if x['id']==tariff),'Unknown Dominion Virginia billing plan.')
        raise ValueError(reason)
    if account.get('supply_arrangement')!='bundled':
        raise ValueError('Third-party supply needs a complete dated contract; bundled retail rates cannot price it.')
    if account.get('eligibility_confirmed') is not True or account.get('ordinary_use_confirmed') is not True:
        raise ValueError('Confirm ordinary residential/commercial schedule eligibility; no data-center or special-service inference.')
    if account.get('special_riders') is not False:
        raise ValueError('Confirm no voluntary rider, low-income exemption, special contract, fuel-deferral exemption or facilities charge.')
    if account.get('metering_side')!='customer':
        raise ValueError('Transformer-side metering discounts require a separately verified account treatment.')
    if not isinstance(account.get('locality'),str) or not account['locality'].strip():
        raise ValueError('Specify the actual locality or mark it unverified; a complete local utility-consumer tax is currently verified for Henrico only.')
    if type(account.get('billing_month')) is not int or not 1<=account['billing_month']<=12:
        raise ValueError('Specify the utility-designated billing month, separately from calendar service dates.')
    if account.get('phase') not in ('single','three'): raise ValueError('Select single- or three-phase service.')
    if account.get('customer_class')!=PLAN_INFO[tariff][1]: raise ValueError('The tariff does not match the account customer class.')
    voltage=account.get('voltage')
    needed='primary' if tariff in ('VA-GS4-primary','VA-10-primary') else 'transmission' if tariff in ('VA-GS4-transmission','VA-10-transmission') else 'secondary'
    allowed=('secondary','primary','transmission') if tariff in ('VA-GS1','VA-GS2','VA-GS2T') else (needed,)
    if voltage not in allowed: raise ValueError(f'{tariff} requires verified service classification in {allowed}.')
    if tariff.startswith(('VA-GS4','VA-10-')):
        v=_number(account.get('delivery_voltage_kv'),'delivery_voltage_kv')
        if needed=='transmission' and v<69: raise ValueError('Transmission service requires at least 69-kV normal delivery.')
        if needed=='primary' and account.get('primary_service_confirmed') is not True:
            raise ValueError('Confirm filed GS-4 primary classification; nominal voltage alone does not determine it.')
    if account.get('parallel_service') not in (True,False): raise ValueError('Confirm whether an existing parallel-service contract applies to all scenarios.')
    if account['parallel_service'] and account.get('parallel_operation_approved') is not True:
        raise ValueError('Confirm approved parallel operation; the simulation is not an interconnection approval.')
    if tariff in ('VA-5C','VA-5P'):
        if account.get('worship_charity_eligible') is not True: raise ValueError('Confirm the sanctuary/charitable meter is eligible for this restricted service.')
        if account['parallel_service']: raise ValueError('5C/5P expressly exclude parallel operation; PV and storage require another eligible plan.')
    if tariff=='VA-1G' and (account.get('ami') is not True or account.get('demand_response_enrolled') is not False):
        raise ValueError('1G requires AMI and no PJM/company demand-response enrollment.')
    if tariff in ('VA-1G','VA-1S','VA-1T') and account.get('tou_reenrollment_eligible') is not True:
        raise ValueError('Confirm the one-year TOU reenrollment restriction does not bar this account.')
    if account.get('solar_mode','non_export') not in ('non_export','net_metering'):
        raise ValueError('Choose explicitly supported non_export or net_metering operation.')
    for k in ('contract_minimum_charge','established_minimum_kw'):
        _number(account.get(k),k)
    if not tariff.startswith('VA-GS') and account['contract_minimum_charge']!=0:
        raise ValueError('A separately contracted minimum is not part of this ordinary monthly-rate schedule; provide its special contract adapter.')
    if tariff.startswith(('VA-GS','VA-10-')):
        if account.get('minimum_demand_basis_confirmed') is not True:
            raise ValueError('Confirm the utility-established minimum-demand floor, including transformer-capacity/contract provisions.')
        hist=account.get('history')
        if not isinstance(hist,list) or len(hist)!=11: raise ValueError('Supply eleven ordered prior billing-cycle demand records; no ratchet history is inferred.')
        for h in hist:
            if not isinstance(h,dict) or type(h.get('billing_month')) is not int or not 1<=h['billing_month']<=12:
                raise ValueError('Each historical cycle needs its actual utility billing month.')
            _number(h.get('maximum_kw'),'historical maximum_kw'); _number(h.get('on_peak_kw'),'historical on_peak_kw')
            if h['on_peak_kw']>h['maximum_kw']+1e-7: raise ValueError('Historical on-peak demand exceeds its all-hours maximum.')
        pf=_number(account.get('power_factor'),'power_factor',.85)
        if pf>1: raise ValueError('Power factor cannot exceed one; lower-PF minimum demand needs explicit kVA measurements.')
        if tariff=='VA-GS1' and sum(h['maximum_kw']>=30 for h in hist)>2:
            raise ValueError('GS-1 history no longer meets its ordinary small-service eligibility.')
        existing=account.get('existing_tariff_enrollment_confirmed') is True
        if tariff in ('VA-GS2','VA-GS2T'):
            qualifying=sum(h['maximum_kw']>=30 for h in hist)
            retained=existing and qualifying>=1
            if (qualifying<3 and not retained) or sum(h['maximum_kw']>=500 for h in hist)>2:
                raise ValueError('GS-2/GS-2T require three qualifying >=30-kW cycles, or confirmed existing service with a retained qualifying peak; at most two >=500-kW cycles are allowed. Reclassification/grace-period treatment needs utility confirmation.')
        if tariff in ('VA-GS3','VA-GS4-primary','VA-GS4-transmission'):
            qualifying=sum(h['maximum_kw']>=500 for h in hist)
            if qualifying<3 and not (existing and qualifying>=1):
                raise ValueError('Large general service requires three qualifying >=500-kW cycles, or confirmed existing service with a retained qualifying peak; no eligibility migration or grace period is inferred.')
            _number(account.get('reactive_peak_kvar'),'reactive_peak_kvar')
            if max(h['maximum_kw'] for h in hist)>=25000:
                raise ValueError('25-MW high-load/future GS-5 rules are a distinct unsupported account class.')
        if tariff.startswith('VA-10-'):
            if account.get('schedule10_original_enrollment_confirmed') is not True or max(h['maximum_kw'] for h in hist)<500:
                raise ValueError('Schedule 10 requires documented original qualifying enrollment and continuing demand eligibility; automatic tariff migration is unsupported.')
            if account.get('demand_response_enrolled') is not False:
                raise ValueError('Schedule 10 excludes PJM/company demand-response enrollment.')
            if pf!=1. or account.get('unity_power_factor_model_confirmed') is not True:
                raise ValueError('Schedule 10 currently requires an explicit unity-meter-power-factor model. Its mandatory 85%-of-maximum-kVA supply demand otherwise requires interval reactive/apparent-power optimization; a frozen kVA input cannot price battery counterfactuals.')
            if max(h['maximum_kw'] for h in hist)>=25000:
                raise ValueError('25-MW Schedule 10 high-load requirements are unavailable in this ordinary account adapter.')
        if account['parallel_service']:
            _number(account.get('contract_demand_kw'),'contract_demand_kw')
    if equipment and (equipment.get('pv') or equipment.get('battery')) and not account['parallel_service']:
        raise ValueError('PV/storage require explicit approved parallel-operation and tariff applicability confirmation.')
    idx=pd.DatetimeIndex(index)
    if idx.empty or idx.tz is None or str(idx.tz)!=TIMEZONE or not idx.is_unique or not idx.is_monotonic_increasing:
        raise ValueError('Use ordered unique America/New_York interval starts.')
    minutes=(idx[1].value-idx[0].value)/6e10 if len(idx)>1 else None
    if minutes not in (15.,30.) or not np.all(np.diff(idx.asi8)==int(minutes*6e10)):
        raise ValueError('Complete aligned 15- or 30-minute intervals are required; hourly data cannot establish a 30-minute demand.')
    if idx[0]!=idx[0].normalize() or idx[-1]+pd.Timedelta(minutes=minutes)!=idx[-1].normalize()+pd.DateOffset(days=1):
        raise ValueError('Provide complete local service dates for one confirmed billing cycle.')
    historical=(tariff in ('VA-1','VA-GS1') and idx[0].date()>=date(2025,1,1) and idx[-1].date()<=date(2025,12,31))
    if not historical and (idx[0].date()<VERIFIED_START or idx[-1].date()>VERIFIED_END):
        extra=(' A separate 2025-01-01 through 2025-12-31 verified subtotal excludes missing historical taxes; complete ordinary 2026 coverage begins January 1.' if tariff in ('VA-1','VA-GS1') else '')
        raise ValueError(f'Verified Dominion VA composite coverage is {VERIFIED_START} through {VERIFIED_END}; no historical rider extrapolation.'+extra)
    if historical and account.get('solar_mode','non_export')!='non_export':
        raise ValueError('2025 solar-export settlement requires its own NEM terms and standby vintage; current 2026 NEM rules are not substituted.')
    days=len(idx.normalize().unique())
    if not 1<=days<=45: raise ValueError('One confirmed cycle may cover1–45 local service days; bimonthly treatment requires its own explicit meter-cycle designation.')
    monthly_rate=not tariff.startswith(('VA-GS','VA-10-')) or tariff=='VA-GS1'
    if monthly_rate and not 26<=days<=40:
        if (account.get('cycle_kind') not in ('initial','final','regular')
                or not isinstance(account.get('cycle_source'),str) or not account['cycle_source'].strip()
                or days<26 and account.get('cycle_kind') not in ('initial','final')):
            raise ValueError('Monthly Rate proration requires a documented complete initial/final short cycle or extended regular cycle; a study fragment is not a meter bill.')
    if not historical:
        from .dominion_va_2026 import Components, validate_allocation
        validate_allocation(account,Components(idx,RATE_COMPONENTS))
    if account.get('solar_mode')=='net_metering':
        # Stateful ledger dates are checked in validate_state/charge_lines.
        _validate_nem(account,idx,equipment=equipment,state={'nem':{**(account.get('nem') or {}),'bank_as_of':idx[0].date().isoformat()}})
    if tariff.startswith('VA-10-'):schedule10_generation_rates(idx)
    return {'tariff':tariff,'index':idx,'days':days,'hours':minutes/60,
        'factor':1. if monthly_rate and 26<=days<=40 else days/30}


def holidays(year):
    # The filed VA schedules name six holidays and do not substitute Friday or
    # Monday when fixed dates fall on a weekend. This calendar is not NC's.
    def nth(month,weekday,n):
        d=date(year,month,1); return d+timedelta(days=(weekday-d.weekday())%7+7*(n-1))
    maylast=date(year,6,1)-timedelta(days=1)
    memorial=maylast-timedelta(days=maylast.weekday())
    return {date(year,1,1),memorial,date(year,7,4),nth(9,0,1),nth(11,3,4),date(year,12,25)}


def periods(index,tariff):
    idx=pd.DatetimeIndex(index);hour=idx.hour+idx.minute/60
    weekdays=np.asarray(idx.dayofweek<5)
    holiday=np.array([d in holidays(d.year) for d in idx.date])
    if tariff=='VA-1G':
        summer=np.asarray((idx.month>=5)&(idx.month<=9))
        peak=weekdays&~holiday&np.where(summer,(hour>=15)&(hour<18),((hour>=6)&(hour<9))|((hour>=17)&(hour<20)))
        return np.where(hour<5,'super_off_peak',np.where(peak,'on_peak','off_peak'))
    summer=np.asarray((idx.month>=6)&(idx.month<=9))
    if tariff in ('VA-1S','VA-1T'):
        peak=weekdays&~holiday&np.where(summer,(hour>=11)&(hour<22),((hour>=7)&(hour<11))|((hour>=17)&(hour<21)))
    else:
        peak=weekdays&np.where(summer,(hour>=10)&(hour<22),(hour>=7)&(hour<22))
        if tariff=='VA-5P': peak &= ~holiday
    return np.where(peak,'on_peak','off_peak')


def schedule10_generation_rates(index):
    """Price official daily classifications; missing data never defaults to C."""
    from .dominion_va_calendar_data import CLASSIFICATIONS
    idx=pd.DatetimeIndex(index);rates=[];classes=[]
    for stamp in idx:
        classification=CLASSIFICATIONS.get(stamp.date().isoformat())
        if classification not in ('A','B','C'):
            raise ValueError('Official Schedule 10 day classification is missing for '+stamp.date().isoformat()+'. Missing retrieval is not evidence that the company failed to announce a classification.')
        hour=stamp.hour+stamp.minute/60;summer=5<=stamp.month<=9
        if summer:
            start,stop,on_rate,off_rate={'A':(14,19,.278424,.061924),'B':(11,21,.022304,.005910),'C':(7,22,.009616,.005546)}[classification]
            peak=start<=hour<stop
        else:
            peak=(6<=hour<12) or (17<=hour<21)
            on_rate,off_rate={'A':(.278424,.074905),'B':(.022304,.010106),'C':(.017001,.009477)}[classification]
        rates.append(on_rate if peak else off_rate);classes.append(classification)
    return np.asarray(rates),np.asarray(classes)


def charge_lines(index,imports_kw,exports_kw,account,*,math,state=None):
    from . import dominion_va_historical
    if dominion_va_historical.supports(account,index):
        return dominion_va_historical.charge_lines(index,imports_kw,exports_kw,account,math=math,state=state)
    effective_account=dict(account)
    if state and 'history' in state:
        effective_account['history']=[dict(record) for record in state['history']]
    try:
        cfg=validate_account(effective_account,index)
    except ValueError as exc:
        if state and 'history' in state and any(word in str(exc) for word in ('eligibility','qualifying','high-load')):
            raise ValueError('Propagated demand history requires utility-confirmed tariff reclassification; automatic migration is unsupported. '+str(exc)) from exc
        raise
    idx=cfg['index'];tariff=cfg['tariff'];dt=cfg['hours'];f=cfg['factor'];days=cfg['days']
    from .dominion_va_2026 import Components, base_metadata
    dated=Components(idx,RATE_COMPONENTS)
    nem_mode=account.get('solar_mode')=='net_metering'
    if not math.convex:
        imports_kw=np.asarray(imports_kw,float);exports_kw=np.asarray(exports_kw,float)
        if imports_kw.shape!=(len(idx),) or exports_kw.shape!=(len(idx),) or not np.isfinite(imports_kw).all() or not np.isfinite(exports_kw).all() or np.min(imports_kw)<-1e-7 or np.min(exports_kw)<-1e-7 or (not nem_mode and np.max(np.abs(exports_kw))>1e-7):
            raise ValueError('Provide finite nonnegative meter imports and zero exports; no-export PV must be curtailed explicitly.')
        imports_kw=np.maximum(imports_kw,0.)
        exports_kw=np.maximum(exports_kw,0.)
        if np.max(np.minimum(imports_kw,exports_kw))>1e-7:
            raise ValueError('Meter import and export cannot occur simultaneously in the same interval.')
    elif not nem_mode:
        math.constraints += [exports_kw==0]
    meter_import=math.sum(imports_kw)*dt;meter_export=math.sum(exports_kw)*dt
    total=meter_import;tax_volume=total;net_billed={};nem_state=None;nem_metrics={}
    labels=periods(idx,tariff);mask=labels=='on_peak'
    if nem_mode:
        tiers,ledger=_validate_nem(account,idx,state=state)
        if math.convex:
            math.constraints.append(exports_kw<=account['nem']['approved_capacity_ac_kw'])
        elif np.max(exports_kw)>account['nem']['approved_capacity_ac_kw']+1e-7:
            raise ValueError('NEM meter exports exceed the approved renewable generation capacity.')
        banks={};earned={};used={};net_by_tier={}
        for tier in tiers:
            selector=np.ones(len(idx),bool) if tier=='all' else labels==tier
            net=math.dot(imports_kw-exports_kw,selector.astype(float))*dt
            net_by_tier[tier]=net
            purchases=math.positive(net,exact=True)
            earned[tier]=math.positive(-net,exact=True)
            used[tier]=_bounded_minimum(math,purchases,ledger['bank_kwh'][tier])
            net_billed[tier]=purchases-used[tier]
            banks[tier]=ledger['bank_kwh'][tier]-used[tier]+earned[tier]
        total=sum(net_billed.values())
        # Tax law defines current energy delivered net of renewable exports;
        # opening credits do not alter current physical net deliveries.
        tax_volume=math.positive(meter_import-meter_export,exact=True)
        nem_state={'period_start':ledger['period_start'],
            'bank_as_of':(idx[-1]+(idx[1]-idx[0])).date().isoformat(),
            'bank_kwh':banks,'bank_source':'Prior validated cycle ledger; filed same-tier kWh carryover'}
        nem_metrics={'net_kwh_by_tier':net_by_tier,'billed_kwh_by_tier':net_billed,
            'credit_earned_kwh_by_tier':earned,'opening_credit_used_kwh_by_tier':used,
            'closing_credit_kwh_by_tier':banks,'tax_net_delivered_kwh':tax_volume}
    peak=math.demand(imports_kw,idx,30,exact=tariff in ('VA-GS1','VA-GS2','VA-GS2T','VA-GS3','VA-GS4-primary','VA-GS4-transmission') or tariff.startswith('VA-10-'))
    on=math.demand(imports_kw,idx,30,mask=mask,exact=tariff in ('VA-GS2T','VA-GS3','VA-GS4-primary','VA-GS4-transmission'))
    off=math.demand(imports_kw,idx,30,mask=~mask,exact=tariff in ('VA-GS3','VA-GS4-primary','VA-GS4-transmission'))
    summer=6<=account['billing_month']<=9
    lines={};metrics={'import_kWh':meter_import,'export_kWh':meter_export,'billed_energy_kwh':total,'peak_kw':peak,'on_peak_kw':on,'billing_days':days,'proration_factor':f,'rate_version':'dominion_va_dated_components_2026',**nem_metrics}
    # Copy the validated prior-cycle records so every counterfactual starts from
    # identical account history and the calculator never mutates caller state.
    prior=[dict(x) for x in (state or {}).get('history',account.get('history',[]))]
    measured_on=on
    supplement=0.
    contract=(state or {}).get('contract_demand_kw',account.get('contract_demand_kw',0.))
    distribution=0.;group='res' if PLAN_INFO[tariff][1]=='residential' else 'gs1' if tariff=='VA-GS1' else 'gs2' if tariff in ('VA-GS2','VA-GS2T') else 'gs3' if tariff=='VA-GS3' else 'gs4p' if tariff=='VA-GS4-primary' else 'gs4t' if tariff=='VA-GS4-transmission' else '10s' if tariff=='VA-10-secondary' else '10p' if tariff=='VA-10-primary' else '10t' if tariff=='VA-10-transmission' else 'church'
    first_blocks={}
    def tier(x,bound,rates):
        # The cumulative first block is shared by distribution and generation.
        # A nonnegative billed volume needs no separate positive-remainder graph.
        key=(id(x),bound)
        if key not in first_blocks:
            first_blocks[key]=_bounded_minimum(math,x,bound)
        used=first_blocks[key]
        return x*rates[1]+used*(rates[0]-rates[1])
    if tariff in ('VA-1','VA-GS1','VA-5C'):
        if tariff=='VA-1': fixed,bound,dist,gen,trans=7.58,800,(.035690,.023596),((.031212,.046243) if summer else (.030064,.026965)),.00970
        elif tariff=='VA-GS1': fixed,bound,dist,gen,trans=(13.39 if account['phase']=='single' else 18.05),1400,(.025525,.018928),((.030788,.041350) if summer else (.030788,.019886)),.00582
        else: fixed,bound,dist,gen,trans=13.88,3000,(.029255,.024674),((.039064,.041197) if summer else (.039064,.036161)),.00887
        lines={'customer':fixed*f,'distribution_energy':tier(total,bound*f,dist),'generation_energy':tier(total,bound*f,gen),'transmission_energy':total*trans}
        if tariff=='VA-GS1':
            established=account['established_minimum_kw']
            floor=max(established,max(x['maximum_kw'] for x in prior)) if any(x['maximum_kw']>=500 for x in prior) else established
            supplement=math.positive(floor-peak,exact=True)*2.092*f
            if account['parallel_service']:
                contract=math.maximum([contract,peak,floor],exact=True)
                lines['parallel_contract_shortfall']=6.588*(contract-peak)*f
    elif tariff in ('VA-1G','VA-1T','VA-1S','VA-5P'):
        fixed={'VA-1G':7.58,'VA-1T':12.99,'VA-1S':12.99,'VA-5P':23.01}[tariff];lines['customer']=fixed*f
        if tariff=='VA-1G':
            ss=np.asarray((idx.month>=5)&(idx.month<=9))
            dist=np.where(labels=='on_peak',np.where(ss,.046743,.041294),np.where(labels=='super_off_peak',np.where(ss,.023674,.024315),np.where(ss,.032360,.028185)))
            gen=np.where(labels=='on_peak',np.where(ss,.153972,.119944),np.where(labels=='super_off_peak',np.where(ss,.000112,.015514),np.where(ss,.009307,.017867)))
            if nem_mode:
                distribution_energy=sum(net_billed[tier]*float(dist[labels==tier][0]) for tier in net_billed if np.any(labels==tier))
                generation_energy=sum(net_billed[tier]*float(gen[labels==tier][0]) for tier in net_billed if np.any(labels==tier))
            else:
                distribution_energy=math.dot(imports_kw,dist)*dt;generation_energy=math.dot(imports_kw,gen)*dt
            lines.update(distribution_energy=distribution_energy,generation_energy=generation_energy,transmission_energy=total*.00970)
        elif tariff=='VA-1T':
            lines.update(distribution_energy=math.dot(imports_kw,np.where(mask,.080512,.008440))*dt,generation_energy=math.dot(imports_kw,np.where(mask,.056744,.014167))*dt,transmission_energy=total*.00970)
        elif tariff=='VA-1S':
            gen=(net_billed['on_peak']*.031424+net_billed['off_peak']*.002911) if nem_mode else math.dot(imports_kw,np.where(mask,.031424,.002911))*dt
            lines.update(distribution_energy=total*.015465,distribution_demand=on*2.478*f,generation_demand=on*2.407*f,generation_energy=gen,transmission_energy=total*.00970)
        else:
            lines.update(distribution_energy=total*.010088,distribution_demand=on*4.055*f,generation_demand=on*(6.332 if summer else 3.834)*f,generation_energy=math.dot(imports_kw,np.where(mask,.014615,.006928))*dt,transmission_energy=total*.00887)
    elif tariff=='VA-GS2':
        # Exact choice of200kWh/kW regime and demand-relative declining blocks.
        nondemand=math.choose_leq(total,200*peak,1.,0.)
        minimum_kw=account['established_minimum_kw']
        if any(x['maximum_kw']>=500 for x in prior):
            minimum_kw=max(minimum_kw,max(x['maximum_kw'] for x in prior))
        distribution=math.maximum(peak,minimum_kw,exact=True)
        supplement=math.positive(minimum_kw-peak,exact=True)*2.113*f
        if account['parallel_service']:distribution=math.maximum(distribution,contract,exact=True)
        lines['customer']=31.90*f
        lines['distribution_demand']=math.choose_leq(total,200*peak,0.,distribution*4.963*f)
        lines['distribution_energy']=math.choose_leq(total,200*peak,total*.035418,total*.000079)
        gen=total*.002301
        rates=(.039031,.021879,.009461,.002301)
        for cut,diff in zip((150,300,450),(rates[0]-rates[1],rates[1]-rates[2],rates[2]-rates[3])):
            gen+=diff*math.minimum(total,cut*peak*f)
        lines['generation_energy']=math.choose_leq(total,200*peak,total*(.030838 if summer else .025627),gen)
        lines['generation_demand']=math.choose_leq(total,200*peak,0.,peak*(1.803 if summer else .588)*f)
        lines['transmission_energy']=math.choose_leq(total,200*peak,total*.01476,0.)
        lines['transmission_demand']=math.choose_leq(total,200*peak,0.,peak*1.971*f)
        metrics['non_demand_billing']=nondemand
    elif tariff.startswith('VA-10-'):
        distribution=math.maximum(max(500.,account['established_minimum_kw'],*[record['maximum_kw'] for record in prior]),peak,exact=True)
        secondary=tariff=='VA-10-secondary';transmission=tariff=='VA-10-transmission'
        generation,classes=schedule10_generation_rates(idx)
        lines={'customer':201.65*f,
            'distribution_demand':distribution*3.316*f if secondary else 0. if transmission else tier(distribution,5000,(2.717,2.076))*f,
            'distribution_energy':total*(.001682 if secondary else .001771),
            'generation_energy':math.dot(imports_kw,generation)*dt,
            'generation_adjustment_demand':peak*0.,
            'transmission_demand':peak*(1.094 if secondary else .646)*f}
        metrics['daily_classification_counts']={key:len(set(idx.date[classes==key])) for key in ('A','B','C')}
        metrics['supply_peak_kw']=peak
    else:
        floor=30. if tariff=='VA-GS2T' else 500.
        distribution=math.maximum(max(floor,account['established_minimum_kw'],*[x['maximum_kw'] for x in prior]),peak,exact=True)
        if account['parallel_service']: distribution=math.maximum(distribution,contract,exact=True)
        if tariff=='VA-GS2T':
            from .dominion import gs2t_base_lines
            lines=gs2t_base_lines(idx,imports_kw,distribution,on,account['billing_month'],f,math=math)
        else:
            on=math.maximum(max([100.,*[.75*x['on_peak_kw'] for x in prior if 6<=x['billing_month']<=9]]),on,exact=True)
            excess=math.positive(off-.9*on,exact=True)
            metrics['billed_on_peak_kw']=on;metrics['billed_off_peak_excess_kw']=excess
            gs3=tariff=='VA-GS3';transmission=tariff=='VA-GS4-transmission'
            lines={'customer':(185.34 if gs3 else 343.54)*f,'distribution_demand':distribution*3.316*f if gs3 else (0. if transmission else tier(distribution,5000,(2.717,2.076))*f),
                   'reactive_demand':account['reactive_peak_kvar']*(.235 if gs3 else .393)*f,'distribution_energy':total*(.000111 if gs3 else .000157),
                   'generation_demand':on*(8.976 if gs3 else 9.280 if transmission else 9.436)*f,'off_peak_generation_demand':excess*(.320 if gs3 else .558)*f,
                   'generation_energy':math.dot(imports_kw,np.where(mask,.004648,.003299))*dt,'transmission_demand':on*(2.277 if gs3 else 2.310 if transmission else 2.371)*f}
    # Effective-dated recurring riders. Interval energy uses actual purchases;
    # a confirmed cross-rate demand cycle retains its whole-cycle measurement.
    def energy(name,key,position=None):
        vector=dated.rate(name,key,position)
        return total*float(vector[0]) if nem_mode else math.dot(imports_kw,vector)*dt
    def demand_rate(name,key,position=None):
        return dated.demand_rate(name,key,position)
    for name in dated.records:
        if name=='sales_use_tax':continue
        key='rider_'+name if name!='deferred_fuel' else name
        if name in ('A','CCR','PIPP','RGGI','RPS','deferred_fuel'):
            lines[key]=energy(name,'all');continue
        if group in ('10s','10p','10t'):
            if name in ('DIST','RBB'):lines[key]=distribution*demand_rate(name,group)*f
            elif name=='T1':lines[key]=peak*demand_rate(name,group)*f
            else:lines[key]=energy(name,group)
        elif name in ('DIST','RBB','T1') and group=='gs2':
            if tariff=='VA-GS2T':lines[key]=(distribution if name in ('DIST','RBB') else on)*demand_rate(name,'gs2t')*f
            else:lines[key]=math.choose_leq(total,200*peak,energy(name,'gs2_non_demand'),(distribution if name in ('DIST','RBB') else peak)*demand_rate(name,'gs2_demand')*f)
        elif name in ('DIST','RBB') and group in ('gs3','gs4p','gs4t'):
            lines[key]=distribution*demand_rate(name,group)*f
        elif name in ('CE','CERC','E','GEN','OSW','SMR','SNA') and group=='gs2':
            lines[key]=math.choose_leq(total,days*12*peak,energy(name,group,0),(on if tariff=='VA-GS2T' else peak)*demand_rate(name,group,1)*f)
        elif name in ('CE','CERC','E','GEN','OSW','SMR','SNA','T1') and group in ('gs3','gs4p','gs4t'):
            lines[key]=on*demand_rate(name,group)*f
        else:lines[key]=energy(name,group)
    if tariff=='VA-GS1':
        pre=sum(v for k,v in lines.items() if k not in ('deferred_fuel','parallel_contract_shortfall'))
        minimum=math.maximum(account['contract_minimum_charge']*f,pre+supplement)
        minimum=math.maximum(minimum,math.choose_leq(peak,50-1e-8,0.,4.35*peak*f))
        lines['minimum_bill_adjustment']=math.positive(minimum-pre)
    elif tariff=='VA-GS2':
        pre=sum(v for k,v in lines.items() if k!='deferred_fuel')
        minimum=math.maximum(account['contract_minimum_charge']*f,pre+supplement)
        demand_minimum=math.choose_leq(peak,50-1e-8,0.,4.39*peak*f)
        minimum=math.maximum(minimum,math.choose_leq(total,200*peak,demand_minimum,0.))
        lines['minimum_bill_adjustment']=math.positive(minimum-pre)
    elif tariff not in ('VA-1','VA-1G','VA-1S','VA-1T','VA-5C','VA-5P'):
        pre=sum(v for k,v in lines.items() if k!='deferred_fuel')
        lines['minimum_bill_adjustment']=math.positive(account['contract_minimum_charge']*f-pre)
    lines['sales_use_tax_surcharge']=energy('sales_use_tax',group)
    # Equivalent filled declining blocks, avoiding unreachable exact selectors
    # when physical energy bounds prove the bill cannot enter a higher block.
    lines['consumption_tax']=tax_volume*.000845+_bounded_minimum(math,tax_volume,2500.)*.000510+_bounded_minimum(math,tax_volume,50000.)*.000210
    warnings=['Retail bundled costs include transmission/capacity; no PJM wholesale adder.',
       'Approved non-export parallel operation when equipment is installed; surplus PV is curtailed, not credited.']
    complete=account['locality']=='henrico'
    if complete:
        if PLAN_INFO[tariff][1]=='residential': lines['henrico_utility_tax']=_bounded_minimum(math,.70+tax_volume*.007537,1.)
        else: lines['henrico_utility_tax']=_bounded_minimum(math,1.15+tax_volume*.00713,10.)
    else:
        warnings.append('INCOMPLETE BILL: the actual locality utility-consumer tax is not verified and is excluded. State consumption tax is included; no zero local tax is assumed.')
    metrics['distribution_demand_kw']=distribution
    next_state={'history':(prior+[{'billing_month':account['billing_month'],'maximum_kw':peak,'on_peak_kw':measured_on}])[-11:]} if prior else {}
    if nem_mode:
        next_state['nem']=nem_state
        warnings[1]='Residential NEM monthly same-tier kWh netting and carryover; no annual boundary, PPA payment, >20-kW standby or terminal bank cash value is modeled.'
        warnings.append('NEM storage must charge only from renewable generation and must not backfeed the utility; dispatch-origin constraints and approved operating sequence remain required.')
    if tariff.startswith('VA-10-'):
        warnings.append('Schedule 10 uses sourced official A/B/C day classifications, including weekends/holidays. The unity-meter-PF assumption makes 85% of maximum kVA no larger than measured kW; nonunity-PF dispatch is unsupported.')
    if account['parallel_service'] and tariff.startswith('VA-GS'):
        # Each demand-plan distribution maximum already includes current peak
        # and the inherited parallel contract; GS1 computes that contract above.
        next_state['contract_demand_kw']=contract if tariff=='VA-GS1' else distribution
    return {'lines':lines,'metrics':metrics,'next_state':next_state,'warnings':warnings, 'is_complete_bill':complete,
       'excluded_components':[] if complete else ['local_utility_consumer_tax'],
       'sources':sorted(set(SOURCES+[entry['source_url'] for entries in dated.metadata.values() for entry in entries]))+([NEM_SOURCE,'https://law.lis.virginia.gov/vacode/title58.1/chapter29/section58.1-2900/','https://law.lis.virginia.gov/vacode/title58.1/chapter38/section58.1-3814/'] if nem_mode else []),
       'rate_components':{'base':base_metadata(tariff,idx),**dated.metadata}}


def _bounded_minimum(math,left,right):
    """Preserve exact minima while pruning branches ruled out by physical bounds."""
    if math.convex:
        a,b=math.bounds(left);c,d=math.bounds(right)
        if b<=c:
            return left
        if d<=a:
            return right
    return math.minimum(left,right)
