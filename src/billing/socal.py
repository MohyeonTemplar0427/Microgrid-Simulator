"""Bounded Southern California account billing; shared numerical/convex costs.

Sources, exclusions and allocation conventions: docs/Southern_California.md.
Amounts are unrounded study estimates. Never infer enrollment from geography.
"""
from datetime import date, timedelta
import numpy as np
import pandas as pd

VERSION = 'socal-2026-09-20.1'
SCE_SOURCE = 'https://www.sce.com/regulatory/regulatory-information/tariff-books/rates-pricing-choices'
LADWP_SOURCE = 'https://www.ladwp.com/account/customer-service/electric-rates/residential-rates'
# Separate quarterly adjustment versions; base rates effective 2019-07-01.
# residential IRCA, commercial IRCA/kW, commercial IRCA/kWh, VEA, CRPSEA, VRPSEA
ADJUSTMENTS = {
 (2025,1):(.04208,2.84,.03100,.00439,.01279,.03091),
 (2025,2):(.04208,2.84,.03100,.00612,.01372,.03294),
 (2025,3):(.05505,2.97,.04652,.00704,.01704,.03114),
 (2025,4):(.05505,2.97,.04652,.00744,.01868,.03208),
 (2026,1):(.05505,2.97,.04652,.00781,.01889,.03317),
 (2026,2):(.05505,2.97,.04652,.00503,.01779,.03296),
 (2026,3):(.06934,3.08,.06302,.01071,.01817,.03307),
}
from .sce_residential import BASELINES, build_plans, charges as residential_charges, version_details
PLANS = {}
for utility,names in [('ladwp',['R-1A','R-1B','A-1A','A-1B','A-2B','A-3A']),
                       ('sce',['D','TOU-D-4-9','TOU-D-5-8','TOU-D-PRIME','TOU-GS-1-E','TOU-GS-1-D','TOU-GS-2-D','TOU-GS-3-D','TOU-8-D'])]:
 for name in names:
  residential=name.startswith('R-') if utility=='ladwp' else name=='D' or name.startswith('TOU-D-')
  key=utility+'_'+name.lower()
  PLANS[key]={'id':key,'utility':utility,'schedule':name,'label':utility.upper()+' '+name,
   'customer_class':'residential' if residential else 'commercial',
   'effective_start':'2025-01-01' if utility=='ladwp' else '2026-06-25',
   'effective_end':'2026-09-17','tariff_data_version':VERSION,
   'source':LADWP_SOURCE if utility=='ladwp' else SCE_SOURCE,
   'demand':not residential and name!='TOU-GS-1-E'}

# Presentation metadata travels with the pinned engine. Qualification remains
# enforced by eligibility(), never by duplicated frontend price rules.
for p in PLANS.values():
 s=p['schedule'];res=p['customer_class']=='residential'
 p['input_groups']=[g for g,show in [('ladwp-region',s=='R-1A'),
  ('sce-region',s in ('D','TOU-D-4-9','TOU-D-5-8')),('prime',s=='TOU-D-PRIME'),
  ('commercial',not res)] if show]
 p['qualification_note']=('Bill-confirmed temperature zone, annual PAC tier and prior-year average below 3000 kWh/month.' if s=='R-1A' else
  'Utility-approved TOU enrollment; rate-switch waiting periods remain account qualifications.' if s=='R-1B' else
  'Bill-confirmed baseline region and basic/all-electric allocation.' if s in ('D','TOU-D-4-9','TOU-D-5-8') else
  'Requires qualifying EV, battery storage or heat-pump technology.' if s=='TOU-D-PRIME' else
  'Assigned schedule, service voltage and 11 prior monthly peaks required; reactive/standby charges excluded.' if p['utility']=='ladwp' else
  'Assigned demand class and non-CPP enrollment required; secondary service only, no optional metering or reactive charges.')


def number(value,name,low=0,high=1e9):
 if isinstance(value,bool) or not isinstance(value,(int,float)) or not np.isfinite(value) or not low<=value<=high:
  raise ValueError(f'{name} must be a finite number between {low} and {high}.')
 return float(value)


def holidays(year):
 days={date(year,1,1),date(year,7,4),date(year,11,11),date(year,12,25)}
 for month,n,weekday in [(2,3,0),(5,-1,0),(9,1,0),(11,4,3)]:
  matches=[d.date() for d in pd.date_range(f'{year}-{month:02}-01',periods=31) if d.month==month and d.weekday()==weekday]
  days.add(matches[n-1] if n>0 else matches[-1])
 return days|{d+timedelta(days=1) for d in days if d.weekday()==6}


def periods(index,utility,schedule):
 hour=index.hour+index.minute/60; summer=np.isin(index.month,[6,7,8,9]); weekday=index.dayofweek<5
 if utility=='ladwp':
  return np.where(weekday&(hour>=13)&(hour<17),'high',np.where(weekday&(hour>=10)&(hour<20),'low','base'))
 special=set().union(*(holidays(y) for y in set(index.year)))
 weekday=weekday & ~np.isin(index.date,list(special))
 begin,finish=(17,20) if schedule=='TOU-D-5-8' else (16,21)
 peak=(hour>=begin)&(hour<finish)
 return np.where(summer&peak&weekday,'on',np.where(peak,'mid',np.where(~summer&(hour>=8)&(hour<begin),'super','off')))


def eligibility(key,account,start,end):
 if key in industry.PLANS:return industry.eligibility(key,account,start,end)
 if key in burbank.PLANS:return burbank.eligibility(key,account,start,end)
 if key in azusa.PLANS:return azusa.eligibility(key,account,start,end)
 if key in pasadena.PLANS:return pasadena.eligibility(key,account,start,end)
 if key in glendale.PLANS:return glendale.eligibility(key,account,start,end)
 if key not in PLANS: raise ValueError('Unsupported Southern California Billing Plan.')
 p=PLANS[key];s=p['schedule'];u=p['utility'];a=account
 begin=date.fromisoformat(start);finish=date.fromisoformat(end)
 if key in RESIDENTIAL_PLANS and begin<=finish:
  try:RESIDENTIAL_PLANS[key].require_coverage(begin,finish)
  except ValueError as exc:raise ValueError('Verified coverage unavailable: '+str(exc)) from exc
 if begin>finish or begin<date.fromisoformat(p['effective_start']) or finish>date.fromisoformat(p['effective_end']):
  raise ValueError(f"Verified coverage: {p['effective_start']} through {p['effective_end']}; current rates are never extended backward.")
 if not isinstance(a,dict):raise ValueError('Supply an account object.')
 if a.get('accommodation','single_family') not in ('single_family','multifamily'):raise ValueError('Select single-family or multifamily accommodation.')
 credit=number(a.get('climate_credit_amount',0.),'Bill-confirmed climate credit',0,1000)
 if credit and (u!='sce' or p['customer_class']!='residential' or a.get('climate_credit_confirmed') is not True):raise ValueError('A climate credit requires SCE residential billing and explicit bill confirmation.')
 if u=='sce' and s=='D' and a.get('heat_pump_water'):raise ValueError('The heat-pump water-heater baseline allowance applies only to TOU-D-4-9/5-8, not D.')
 if u=='sce' and (finish-begin).days+1>40:raise ValueError('SCE studies cover one monthly billing cycle (at most 40 days); split longer periods into cycles.')
 if not isinstance(a,dict) or a.get('customer_class')!=p['customer_class']: raise ValueError('Customer type does not match the plan.')
 for field in ['eligibility_confirmed','cycle_confirmed','ordinary_account_confirmed']:
  if a.get(field) is not True: raise ValueError(f'Confirm {field.replace("_"," ")}; special riders are unsupported.')
 if not isinstance(a.get('reference'),str) or not a['reference'].strip(): raise ValueError('Supply the bill/utility eligibility reference or explicit hypothetical assumption.')
 if a.get('generation_provider')!=u: raise ValueError('CCA generation billing is unsupported. Select an explicitly hypothetical bundled comparison, never substitute SCE automatically.')
 if a.get('solar_program') not in ('none','approved_non_export'): raise ValueError('NEM/NBT export settlement is not yet supported; do not substitute PG&E export rules.')
 if a['solar_program']=='approved_non_export' and a.get('interconnection_confirmed') is not True: raise ValueError('Confirm approved non-export interconnection and applicable standby exemption.')
 if a.get('voltage') not in ('secondary','ladwp_4.8kv','ladwp_34.5kv'): raise ValueError('Select the verified service voltage.')
 if u=='sce' and a['voltage']!='secondary': raise ValueError('Only SCE below-2-kV rates have been loaded.')
 if a.get('phase') not in ('single','three'): raise ValueError('Select service phase.')
 # Tax jurisdiction is separately confirmed, never inferred from utility territory.
 number(a.get('local_tax_percent'),'Confirmed local utility tax percent',0,20)
 if a.get('tax_confirmed') is not True: raise ValueError('Confirm local tax from the account; utility territory is not a tax jurisdiction.')
 if u=='ladwp':
  if s=='R-1A':
   if a.get('temperature_zone') not in ('1','2') or a.get('region_confirmed') is not True: raise ValueError('Confirm LADWP temperature zone from bill or utility; city/county is insufficient.')
   if a.get('pac_tier') not in (1,2,3): raise ValueError('Confirm the annual Power Access Charge tier (October determination); do not infer it from the study month.')
   if number(a.get('annual_average_kwh'),'Prior 12-month average kWh')>=3000: raise ValueError('R-1B is mandatory at annual monthly average >=3000 kWh.')
  if s.startswith('R-') and a['voltage']!='secondary': raise ValueError('Dedicated-transformer residential service is outside R-1 scope.')
  if s.startswith('A-'):
   history=a.get('previous_11_month_peaks_kw')
   if not isinstance(history,list) or len(history)!=11: raise ValueError('Supply 11 preceding monthly peaks for the annual facilities ratchet.')
   for v in history:number(v,'Historical demand')
   if s.startswith('A-1') and max(history)>=30: raise ValueError('This A-1 implementation requires all preceding peaks below 30 kW; transition qualification needs utility review.')
   if a['voltage']!={'A-1A':'secondary','A-1B':'secondary','A-2B':'ladwp_4.8kv','A-3A':'ladwp_34.5kv'}[s]:raise ValueError('LADWP schedule and voltage do not match.')
   if s in ('A-2B','A-3A') and a.get('reactive_charge_exempt_confirmed') is not True:raise ValueError('Reactive-meter/PF billing is unsupported; confirm no reactive charge applies.')
 else:
  if s in ('D','TOU-D-4-9','TOU-D-5-8'):
   if a.get('baseline_region') not in BASELINES or a.get('region_confirmed') is not True:raise ValueError('Confirm the SCE baseline region from the account; delivery territory alone does not determine it.')
   if a.get('baseline_type') not in ('basic','all_electric'):raise ValueError('Confirm basic or utility-approved all-electric baseline.')
  if s=='TOU-D-PRIME' and a.get('prime_qualification') not in ('ev','battery','heat_pump_water','heat_pump_space'):raise ValueError('PRIME requires an eligible EV, storage or heat-pump technology.')
  if p['customer_class']=='commercial':
   if a.get('non_cpp_confirmed') is not True:raise ValueError('Confirm non-CPP option enrollment; CPP event billing is not implemented.')
   if s in ('TOU-GS-3-D','TOU-8-D') and a.get('reactive_charge_exempt_confirmed') is not True:raise ValueError('Confirm zero chargeable reactive demand; PF billing is not implemented.')
 return p


def interval_index(frame,start,end):
 if any(pd.Timestamp(v).tzinfo is None for v in frame['timestamp']):raise ValueError('15-minute timestamps must include an explicit UTC offset.')
 idx=pd.DatetimeIndex(pd.to_datetime(frame['timestamp'],utc=True)).tz_convert('America/Los_Angeles')
 expected=pd.date_range(pd.Timestamp(start,tz='America/Los_Angeles'),pd.Timestamp(end,tz='America/Los_Angeles')+pd.DateOffset(days=1),freq='15min',inclusive='left')
 if not idx.equals(expected):raise ValueError('Supply every actual 15-minute interval for the full cycle, with UTC offsets; hourly demand cannot be upsampled.')
 if len(idx)>10000:raise ValueError('At most 10000 intervals per billing-cycle study.')
 return idx


# Filed delivery and generation rates: summer on/mid/off, winter mid/off/super.
SCE_ENERGY={
 'TOU-D-4-9':((.33156,.33156,.27270,.33156,.27270,.25153),(.25321,.13326,.07396,.17956,.10245,.08452)),
 'TOU-D-5-8':((.33224,.33224,.28231,.33224,.28231,.25527),(.41155,.21138,.06298,.27579,.09965,.07016)),
 'TOU-D-PRIME':((.29624,.29624,.19649,.30157,.18675,.18675),(.29667,.10558,.07049,.26489,.05958,.05958)),
 'TOU-GS-1-E':((.21937,.21937,.16523,.21937,.16523,.13989),(.42432,.11297,.08076,.17145,.09524,.04999)),
 'TOU-GS-1-D':((.08070,.08070,.05402,.08070,.05402,.04199),(.11375,.10273,.06733,.10709,.07561,.05658)),
 'TOU-GS-2-D':((.05674,.05491,.05449,.05674,.05491,.05384),(.10955,.09989,.06409,.07395,.07440,.03907)),
 'TOU-GS-3-D':((.05374,.05200,.05166,.05374,.05200,.05103),(.10160,.09264,.06256,.07221,.07264,.03814)),
 'TOU-8-D':((.04817,.04653,.04617,.04817,.04653,.04557),(.10128,.09236,.06256,.07221,.07266,.03813))}
SCE_FIXED={'TOU-GS-2-D':268.43,'TOU-GS-3-D':780.37,'TOU-8-D':525.16}
SCE_DEMAND={'TOU-GS-1-D':(22.61,21.38,4.92),'TOU-GS-2-D':(28.18,39.60,8.46),'TOU-GS-3-D':(26.75,38.60,10.07),'TOU-8-D':(30.29,42.23,9.73)}


RESIDENTIAL_PLANS = build_plans()
from . import glendale, pasadena, azusa, burbank, industry
PLANS.update(glendale.PLANS)
PLANS.update(pasadena.PLANS)
PLANS.update(azusa.PLANS)
PLANS.update(burbank.PLANS)
PLANS.update(industry.PLANS)
for key,plan in RESIDENTIAL_PLANS.items():
 PLANS[key]['effective_start']=plan.versions[0].effective_start.isoformat()
 PLANS[key]['coverage_windows']=[{'start':v.effective_start.isoformat(),'end':v.effective_end.isoformat(),'version_id':v.tariff_id} for v in plan.versions]


def charge_lines(key,index,imports,account,*,convex=False,constraints=None):
 """One confirmed billing cycle. Identical expressions for billing and dispatch.

 LADWP monthly quantities/prices prorated by service days/30 (explicit study
 approximation until the account's meter-read factor is supplied).
 SCE rounded demand uses integer epigraphs in the optimizer.
 """
 if key in glendale.PLANS:return glendale.charge_lines(key,index,imports,account,convex=convex,constraints=constraints)
 if key in pasadena.PLANS:return pasadena.charge_lines(key,index,imports,account,convex=convex,constraints=constraints)
 if key in burbank.PLANS:return burbank.charge_lines(key,index,imports,account,convex=convex,constraints=constraints)
 if key in industry.PLANS:return industry.charge_lines(key,index,imports,account,convex=convex,constraints=constraints)
 if key in azusa.PLANS:return azusa.charge_lines(key,index,imports,account,convex=convex,constraints=constraints)
 import cvxpy as cp
 p=PLANS[key];s=p['schedule'];u=p['utility'];a=account
 total=cp.sum(imports)*.25 if convex else float(np.sum(imports)*.25)
 maximum=cp.maximum if convex else np.maximum
 sum_=cp.sum if convex else np.sum
 def peak(mask,rounded=False):
  if not np.any(mask):return 0.
  value=cp.max(imports[mask]) if convex else float(np.max(imports[mask]))
  if not rounded:return value
  if not convex:return np.floor(value+.5)
  # Keep a numerical margin below the half-kW rounding boundary; a solver
  # tolerance of a few micro-kW must not turn an optimized 10 kW bill into 11.
  d=cp.Variable(integer=True);constraints.extend([d>=0,value<=d+.4999]);return d
 days=len(index.normalize().unique());factor=a.get('billing_month_factor',days/30)
 number(factor,'Billing month factor',.01,3)
 lines={name:0. for name in ['energy_charge','generation_charge','baseline_credit','fixed_charge','facilities_demand','tou_demand','minimum_adjustment','export_credit']}
 summer=np.isin(index.month,[6,7,8,9]);per=periods(index,u,s)
 if u=='ladwp':
  # Non-TOU meter usage is allocated by days across season/rate changes,
  # as LADWP's residential page explicitly specifies, rather than load shape.
  if s=='R-1A':
   cap=(350 if a['temperature_zone']=='1' else 500)*factor
   lines['fixed_charge']=(2.30,7.90,22.70)[a['pac_tier']-1]*factor
   high_days=len(index[summer].normalize().unique());share=high_days/days
   lines['energy_charge']=.07142*total+(.13001-.07142)*maximum(total-cap,0)+share*(.21702-.13001)*maximum(total-3*cap,0)
   capped=.0702*total+share*(.015*maximum(total-cap,0)+.0348*maximum(total-3*cap,0))
   # Express max(capped,minimum)+incremental directly for convexity.
   minimum=10*factor
   if convex:
    cap_floor=maximum(maximum(.0702*total, (.0702+share*.015)*total-share*.015*cap),(.0702+share*.0498)*total-share*(.015*cap+.0348*3*cap))
    incremental=.00122*total+(.05859-share*.015)*maximum(total-cap,0)+share*.05221*maximum(total-3*cap,0)
    lines['energy_charge']=maximum(cap_floor,minimum)+incremental
   else:lines['minimum_adjustment']=max(0,minimum-capped)
  else:
   base={'R-1B':((.15858,.10018,.07274),(.10018,.10018,.07664)),
    'A-1A':((.08188,)*3,(.05484,)*3),'A-1B':((.14990,.10000,.07082),(.10000,.10000,.07082)),
    'A-2B':((.06322,.05595,.03522),(.05688,.05688,.03895)),
    'A-3A':((.05991,.05365,.03356),(.05464,.05464,.03798))}[s]
   pos=np.select([per=='high',per=='low'],[0,1],default=2)
   prices=np.array([base[0 if hot else 1][j] for hot,j in zip(summer,pos)])
   lines['energy_charge']=sum_(cp.multiply(imports,prices) if convex else imports*prices)*.25
   lines['fixed_charge']={'R-1B':12,'A-1A':7,'A-1B':20,'A-2B':28,'A-3A':75}[s]*factor
  for year,quarter in dict.fromkeys(zip(index.year,(index.month-1)//3+1)):
   mask=(index.year==year)&((index.month-1)//3+1==quarter);v=ADJUSTMENTS[(year,quarter)]
   weight=len(index[mask].normalize().unique())/days
   kwh=total*weight if s=='R-1A' else sum_(imports[mask])*.25
   adjustments={'ECA':.05690,'VEA':v[3],'CRPSEA':v[4],'VRPSEA':v[5]}
   if p['customer_class']=='residential':adjustments.update(ESA=.00147,RCA=.003,IRCA=v[0])
   else:adjustments['IRCA_energy']=v[2]
   for name,rate in adjustments.items():lines[name]=lines.get(name,0)+kwh*rate
   if p['customer_class']=='commercial':
    history=max(a['previous_11_month_peaks_kw']);floor=4 if s.startswith('A-1') else 30
    ratchet=maximum(peak(np.ones(len(index),dtype=bool)),max(history,floor))
    lines['facilities_demand']+=ratchet*(4.56 if s=='A-3A' else 5.36)*factor*weight
    for name,rate in [('ESA_demand',.46),('RCA_demand',.96),('IRCA_demand',v[1])]:lines[name]=lines.get(name,0)+ratchet*rate*factor*weight
  if s in ('A-2B','A-3A'):
   # Seasonal demand charges allocated by service days; maximum per TOU window.
   for hot in (True,False):
    fraction=len(index[summer==hot].normalize().unique())/days
    high=(10 if hot else 4.75) if s=='A-2B' else (9.70 if hot else 4.30)
    low=(3.75 if s=='A-2B' else 3.30) if hot else 0
    lines['tou_demand']+=factor*fraction*(high*peak(per=='high')+low*peak(per=='low'))
 elif key in RESIDENTIAL_PLANS:
  lines.update(residential_charges(RESIDENTIAL_PLANS[key],key,index,imports,a,per,convex))
 else:
  pos=np.where(summer,np.select([per=='on',per=='mid'],[0,1],default=2),np.select([per=='mid',per=='off'],[3,4],default=5))
  for name,rates in zip(['energy_charge','generation_charge'],SCE_ENERGY[s]):
   prices=np.array(rates)[pos];lines[name]=sum_(cp.multiply(imports,prices) if convex else imports*prices)*.25
  lines['fixed_charge']=(days*(.468+(.046 if a['phase']=='three' else 0)) if s.startswith('TOU-GS-1') else (SCE_FIXED[s]-(9.30 if s=='TOU-GS-2-D' and a['phase']=='single' else 0))*factor)
  frc={'TOU-GS-1-E':.00457,'TOU-GS-1-D':.00457,'TOU-GS-2-D':.00483,'TOU-GS-3-D':.00400,'TOU-8-D':.00365}[s]
  if s in SCE_DEMAND:
   fr,on,mid=SCE_DEMAND[s];lines['facilities_demand']=fr*peak(np.ones(len(index),dtype=bool),True)
   weekday=(index.dayofweek<5)&~np.isin(index.date,list(set().union(*(holidays(y) for y in set(index.year)))))
   lines['tou_demand']=on*peak(summer&(per=='on'),True)+mid*peak(~summer&(per=='mid')&weekday,True)
  lines['fixed_recovery_charge']=frc*total
 # Utility user tax is an explicit account input. Recurring estimate excludes
 # climate credits and other account adjustments; no guessed credit month.
 subtotal=sum(lines.values());lines['local_utility_tax']=subtotal*a['local_tax_percent']/100
 lines['state_energy_surcharge']=total*.0003
 lines['climate_credit']=-a.get('climate_credit_amount',0.)
 return lines


def bill(key,frame,account,start,end):
 p=eligibility(key,account,start,end);idx=interval_index(frame,start,end)
 imports=np.asarray(frame['grid_import_kw'],dtype=float)
 if not np.isfinite(imports).all() or (imports<0).any():raise ValueError('Imports must be nonnegative finite kW.')
 if 'grid_export_kw' in frame and (not np.isfinite(frame.grid_export_kw).all() or (np.abs(frame.grid_export_kw)>1e-7).any()):raise ValueError('Export settlement is unsupported; exported energy cannot be silently ignored.')
 s=p['schedule'];maximum=float(imports.max())
 if s.startswith('A-1') and maximum>=30:raise ValueError('A-1 study scope requires demand below 30 kW.')
 if s.startswith('TOU-GS-1') and maximum>20:raise ValueError('GS-1 study exceeds 20 kW; utility must confirm transition eligibility.')
 if s=='TOU-GS-2-D' and maximum>=200:raise ValueError('GS-2 requires confirmed 20–200 kW classification.')
 if s=='TOU-GS-3-D' and maximum>500:raise ValueError('GS-3 requires confirmed 200–500 kW classification.')
 lines={k:float(v) for k,v in charge_lines(key,idx,imports,account).items()}
 if key in pasadena.PLANS:return pasadena.bill_details(key,idx,imports,account,lines)
 if key in burbank.PLANS:return burbank.bill_details(key,idx,imports,account,lines)
 if key in industry.PLANS:return industry.bill_details(key,idx,imports,account,lines)
 if key in azusa.PLANS:return azusa.bill_details(key,idx,imports,account,lines)
 if key in glendale.PLANS:
  if s.startswith('L-2') and (maximum>=20 or imports.sum()*.25>=5000*len(idx.normalize().unique())/30):
   raise ValueError('GWP small-business scope requires <20 kW and <5000 kWh per study month; transition accounts need utility review.')
  return {'total':sum(lines.values()),'line_items':lines,'usage_kWh':float(imports.sum()*.25),'peak_kw':maximum,
   'amount_due':sum(lines.values()),'credit_balance':0.,'tariff':p,'rate_versions':glendale.version_details(idx),
   'adjustment_versions':[v[2] for v in glendale.ADJUSTMENT_VERSIONS],
   'warnings':['GWP daily tier allocation across rate/season boundaries is an explicitly acknowledged study approximation.',
    'No export, customer-generation/standby settlement, assistance discounts, master meters, special holidays or AC network feasibility.']
    + (['Demand floor is account-confirmed historical state; this single-cycle study does not optimize future ratchet costs.'] if p['demand'] else [])
    + (['L-2 limits are conservative study bounds (<20 kW, <5000 kWh per 30 days), not the historical utility classification algorithm.'] if s.startswith('L-2') else [])}
 details=version_details(RESIDENTIAL_PLANS[key],key,idx,account) if key in RESIDENTIAL_PLANS else []
 return {'total':sum(lines.values()),'line_items':lines,'usage_kWh':float(imports.sum()*.25),'peak_kw':maximum,
  'amount_due':max(0.,sum(lines.values())),'credit_balance':max(0.,-sum(lines.values())),
  'rate_versions':details,'tariff':p,'adjustment_versions':sorted({f'{d.year}-Q{(d.month-1)//3+1}' for d in idx}) if p['utility']=='ladwp' else sorted({d['version_id'] for d in details}) if details else ['SCE-5829-E/5837-E'],
  'warnings':(['Rate/season change: baseline and minimum charges are calculated in day-prorated subperiods. This is a study allocation approximation, not verified account meter-read reconciliation.'] if len(details)>1 else []) + ['Climate credit is included only when explicitly confirmed from this bill; other account adjustments and special riders are excluded.',
   'Monthly quantities use the explicitly supplied billing-month factor; default days/30 is a study approximation.',
   'Import-only/non-export study. NEM/NBT settlement and AC network feasibility are not modeled.']}
