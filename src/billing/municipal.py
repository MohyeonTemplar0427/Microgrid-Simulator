"""Verified municipal rate versions and complete-cycle bill replay.

Separate from TariffDefinition: that interface cannot express SVP's annual
ratchet or proportional TOU tiers. Never register these as flat-price tariffs.
See docs/Municipal_Utilities.md for the supported account envelope.
"""
from dataclasses import asdict, dataclass
from datetime import date, timedelta
import math

import numpy as np
import pandas as pd
from .municipal_sources import SOURCE_HASHES

VERIFIED_THROUGH = date(2026, 9, 17)
SVP_SOURCE = 'https://santaclara.legistar.com/View.ashx?GUID=B4AEAF03-4B68-4F86-92D3-5C3BF99F2CC5&ID=15038898&M=F'
AMP_BASE = 'https://www.alamedamp.com/DocumentCenter/View/'
STATE_SOURCE = 'https://cdtfa.ca.gov/taxes-and-fees/special-taxes-and-fees-tax-rates/'
NERC_SOURCE = 'https://www.nerc.com/comm/OC/RS%20Agendas%20Highlights%20and%20Minutes%20DL/Additional_Off-peak_Days.pdf'


@dataclass(frozen=True)
class MunicipalRate:
    id: str
    utility: str
    schedule: str
    effective_start: date
    fixed: float
    energy: tuple[float, ...]
    demand: float = 0
    tier_kwh: float | None = None
    tou_peak: tuple[float, ...] = ()
    tou_offpeak: tuple[float, ...] = ()
    source: str = ''
    version: str = ''
    verified_through: date = VERIFIED_THROUGH

    def metadata(self):
        result = asdict(self)
        result.update(effective_start=self.effective_start.isoformat(),
                      verified_through=self.verified_through.isoformat(), effective_end=None,
                      delivery_utility=self.utility, generation_provider=self.utility,
                      export_program='none', dispatch_optimization_supported=True,
                      source_sha256=SOURCE_HASHES.get(self.source))
        return result


RATES = {}
for schedule, doc, fixed, energy, demand in (
    ('D-1',1563,24.27,(.13934,.26723),0),
    ('A-1',1559,41.99,(.20946,),0),
    ('A-2',1560,212.62,(.15316,),14.62),
    ('A-3',1561,573.60,(.14952,),18.50),
):
    rid = 'amp_' + schedule.lower().replace('-', '') + '_2026_07_01'
    RATES[rid] = MunicipalRate(rid,'amp',schedule,date(2026,7,1),fixed,energy,demand,
                               source=AMP_BASE+str(doc)+'?bidId=',version='AMP Resolution 5249')
for schedule, fixed, energy, demand, tier, peak, off in (
    ('D-1',5.11,(.15612,.17946),0,300,(.17960,.20295),(.13690,.16023)),
    ('C-1',5.52,(.26620,.24166),0,800,(.28968,.26514),(.24697,.22242)),
    ('CB-1',100.45,(.16139,),12.14,None,(.18490,),(.14217,)),
    ('CB-3',100.45,(.14864,),16.19,None,(.17210,),(.12938,)),
):
    rid = 'svp_' + schedule.lower().replace('-', '') + '_2026_01_01'
    RATES[rid] = MunicipalRate(rid,'svp',schedule,date(2026,1,1),fixed,energy,demand,tier,
                               peak,off,SVP_SOURCE,'SVP Resolution 25-9516')

UNSUPPORTED = {
    'amp_A-4': 'Published A-4 is suspended; its price table is blank pending a cost-of-service study.',
    'amp_EV-TOU': 'Optional EV schedule and enrollment not implemented.',
    'svp_CB-6': 'Large-load tier/voltage and minimum-demand rules are not implemented.',
    'svp_CB-7': 'Market-based option needs CAISO DLAP, TAC, losses, RECs, GMC and contract allocation inputs; no fixed-rate substitute.',
    'svp_CB-8': 'Negotiated customer-load-retention discount and marginal-cost floor require utility agreement inputs.',
    'standby': 'AMP SS and SVP SB-1 contract capacity/reactive/backup rules are not implemented.',
    'export': 'NEM/ERG/NM settlement and eligibility are not implemented; no export credit.',
    'partial_cycle': 'Partial cycles and within-cycle version changes require verified utility proration rules.',
    'discount_programs': 'Medical, income assistance and meter opt-out riders are not implemented.',
}


def finite(value, name, low=0, high=float('inf')):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{name} must be a finite number from {low} to {high}.')
    return float(value)


def nerc_holidays(year):
    """Six off-peak holidays; Sunday observed Monday, Saturday stays Saturday."""
    fixed = [date(year,1,1),date(year,7,4),date(year,12,25)]
    may = date(year,5,31)
    september = date(year,9,1)
    november = date(year,11,1)
    return {d + timedelta(days=1) if d.weekday()==6 else d for d in fixed} | {
        may-timedelta(days=may.weekday()),
        september+timedelta(days=(-september.weekday())%7),
        november+timedelta(days=(3-november.weekday())%7+21),
    }


def svp_peak_mask(stamps):
    holidays = set().union(*(nerc_holidays(y) for y in set(stamps.year)))
    return np.array([s.weekday()!=6 and s.date() not in holidays and 6<=s.hour<22 for s in stamps])


def eligibility(utility, account, start, end):
    """Return eligible/excluded/missing-input cases; history never comes from a short replay.

    Confirmed current assignment is authoritative for retention/discretionary
    transfer rules. Raw history is disclosed but cannot authorize a transfer.
    """
    start, end = date.fromisoformat(start), date.fromisoformat(end)
    if end <= start:
        raise ValueError('End must follow start (exclusive end).')
    if not isinstance(account, dict):
        raise ValueError('Supply an account object.')
    allowed = {'customer_class','phase','voltage','metered','onsite_generation','special_riders',
               'billing_cycle_confirmed','state_surcharge_exempt','demand_interval_minutes','uut_status',
               'heating_source','monthly_power_factor_percent','previous_11_month_peaks_kw',
               'power_factor_adjustment_active','power_factor_state_reference','secondary_service_approved',
               'minimum_charge_load_units','primary_discount_qualified','time_of_use','tou_enrollment_confirmed',
               'tax_confirmation_reference','confirmed_schedule','schedule_confirmation_reference','history_12_months'}
    if set(account)-allowed:
        raise ValueError('Unknown account fields: '+', '.join(sorted(set(account)-allowed)))
    output = []
    for rate in RATES.values():
        if rate.utility != utility:
            continue
        missing, reasons = [], []
        for key in ('customer_class','phase','voltage','metered','onsite_generation','special_riders'):
            if key not in account:
                missing.append(key)
        required = ['billing_cycle_confirmed','state_surcharge_exempt']
        if rate.demand:
            required.append('demand_interval_minutes')
            if account.get('demand_interval_minutes') not in (None,15):
                reasons.append('Utility-assigned 1/5-minute demand measurement is unsupported; use the actual account interval.')
        if rate.utility == 'amp':
            required.append('uut_status')
            if rate.schedule == 'D-1':
                required.append('heating_source')
            if rate.schedule == 'A-3':
                required.append('monthly_power_factor_percent')
                if account.get('voltage') == 'primary_12kv':
                    reasons.append('Combined AMP primary discount and PF adjustment ordering requires confirmation; secondary A-3 is supported.')
        if rate.utility == 'svp':
            if rate.demand:
                required.append('previous_11_month_peaks_kw')
            if rate.schedule == 'CB-1':
                required.extend(['power_factor_adjustment_active','power_factor_state_reference'])
                if account.get('power_factor_adjustment_active') is True:
                    required.append('monthly_power_factor_percent')
            if rate.schedule == 'CB-3':
                required.append('monthly_power_factor_percent')
                if account.get('voltage') == 'secondary' and account.get('secondary_service_approved') is not True:
                    required.append('secondary_service_approved')
            if rate.schedule == 'C-1':
                required.append('minimum_charge_load_units')
        if account.get('voltage') == 'primary_12kv':
            required.append('primary_discount_qualified')
        if account.get('time_of_use') is True:
            required.append('tou_enrollment_confirmed')
        if account.get('state_surcharge_exempt') is True or account.get('uut_status') in ('reduced_confirmed','exempt_confirmed'):
            required.append('tax_confirmation_reference')
        missing.extend(k for k in required if k not in account)
        for key in ('billing_cycle_confirmed','primary_discount_qualified','tou_enrollment_confirmed','secondary_service_approved'):
            if key in required and key in account and account[key] is not True:
                reasons.append(key+' must be explicitly confirmed.')
        if account.get('state_surcharge_exempt') is not None and type(account['state_surcharge_exempt']) is not bool:
            reasons.append('state_surcharge_exempt must be boolean.')
        if rate.utility=='svp' and rate.schedule in ('D-1','C-1') and account.get('voltage')=='primary_12kv':
            reasons.append('Primary D-1/C-1 service is unsupported.')
        residential = rate.schedule == 'D-1'
        if account.get('customer_class') is not None and ((account['customer_class']=='residential') != residential):
            reasons.append('Customer class does not match schedule; apartment common areas are nonresidential.')
        if account.get('customer_class') not in (None,'residential','commercial','industrial'):
            reasons.append('Unsupported customer class.')
        if account.get('phase') not in (None,'single','three'):
            reasons.append('Unsupported phase.')
        if residential and account.get('phase') not in (None,'single'):
            reasons.append('D-1 requires single-phase service.')
        if rate.schedule in ('A-3','CB-3') and account.get('phase') not in (None,'three'):
            reasons.append('Large commercial service requires three-phase supply in this implementation.')
        if account.get('voltage') not in (None,'secondary','primary_12kv'):
            reasons.append('Only secondary or confirmed 12 kV primary service is implemented.')
        if residential and account.get('voltage') not in (None,'secondary'):
            reasons.append('Primary residential service is unsupported.')
        if account.get('metered') is not None and account['metered'] is not True:
            reasons.append('Unmetered service is unsupported.')
        if account.get('onsite_generation') is not None and account['onsite_generation'] is not False:
            reasons.append('Onsite generation requires unimplemented export/standby eligibility review.')
        if account.get('special_riders') is not None and account['special_riders'] != []:
            reasons.append('Special riders/discount programs are unsupported.')
        if start < rate.effective_start or end-timedelta(days=1)>rate.verified_through:
            reasons.append('Requested period extends outside verified rate coverage.')
        if account.get('confirmed_schedule') != rate.schedule or not account.get('schedule_confirmation_reference'):
            missing.extend(['confirmed_schedule','schedule_confirmation_reference'])
        if not residential and not account.get('history_12_months'):
            # Confirmation supports continued existing service; no automatic transfers.
            history_note = 'Usage/demand history unavailable; only confirmed existing assignment can be billed. No transfer eligibility inferred.'
        else:
            history_note = 'Existing assignment must be confirmed; qualification and retention rules require utility review for transfers.'
        output.append({'tariff':rate.metadata(),'status':'excluded' if reasons else 'missing_inputs' if missing else 'eligible',
                       'reasons':reasons,'missing_inputs':sorted(set(missing)),'history_note':history_note,
                       'qualification': qualification(rate, account)})
    return output


def qualification(rate, account):
    rules = {
        'amp_A-1':'Any one of the last 12 months below 8000 kWh; demand below 500 kW. AMP reviews twice yearly, transfers to A-2 after 12 consecutive months above 8000 kWh; normally only one change per year.',
        'amp_A-2':'At least six of the last 12 months at or above 8000 kWh and demand below 500 kW. Retention and transfers depend on AMP review, PF and the one-change-per-year rule.',
        'amp_A-3':'At least six of the last 12 months with demand at least 500 and below 4000 kW. Downward transfer is subject to PF and AMP review.',
        'svp_C-1':'Does not qualify for D-1 or CB demand schedules. CB-1 retention persists until 12 consecutive months below 6000 kWh and SVP elects a transfer.',
        'svp_CB-1':'Above 8000 kWh for three consecutive months, or utility-assessed initial connected load. Retained until 12 months below 6000 kWh and SVP elects C-1.',
        'svp_CB-3':'Billing demand above 4000 kW for three consecutive months or utility-assessed initial connected load. Retained until 12 consecutive billing periods below 4000 kW.',
    }
    return {'rule':rules.get(rate.utility+'_'+rate.schedule,'Single-phase residential dwelling service; excludes apartment common areas.'),
            'basis':'confirmed existing schedule' if account.get('confirmed_schedule')==rate.schedule and account.get('schedule_confirmation_reference') else 'not established',
            'missing_for_transfer':['dated usage/demand history','current enrollment and utility transfer approval'] if rate.schedule!='D-1' else [],
            'automatic_transfer_supported':False}


def _required(account, key):
    if key not in account:
        raise ValueError(f'Missing account input: {key}.')
    return account[key]


def bill_cycle(tariff_id, dispatch, *, cycle_start, cycle_end, account):
    """Bill a complete, confirmed regular cycle of 15-minute imports.

    AMP supports its filed 27–33 day regular cycles; SVP calendar months only.
    Dated historical peaks are mandatory for SVP ratchets. Account state
    (PF activation, exemptions, enrollment) must come from the bill/utility.
    """
    if tariff_id not in RATES:
        raise ValueError('Unsupported municipal tariff version.')
    rate = RATES[tariff_id]
    start, end = pd.Timestamp(cycle_start), pd.Timestamp(cycle_end)
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError('Cycle boundaries need timezone offsets.')
    start, end = start.tz_convert('America/Los_Angeles'), end.tz_convert('America/Los_Angeles')
    days = (end.date()-start.date()).days
    if start != start.normalize() or end != end.normalize() or (rate.utility=='amp' and not 27<=days<=33) or (rate.utility=='svp' and (start.day != 1 or end != start+pd.DateOffset(months=1))):
        raise ValueError('Use an AMP regular 27–33 day cycle or an SVP complete calendar month; partial-cycle proration is unsupported.')
    if _required(account,'billing_cycle_confirmed') is not True:
        raise ValueError('Confirm actual billing-cycle boundaries; hypothetical cases must label their assumed cycle.')
    entry = next(x for x in eligibility(rate.utility,account,str(start.date()),str(end.date())) if x['tariff']['id']==tariff_id)
    if entry['status']!='eligible':
        raise ValueError('Tariff eligibility: '+str(entry['reasons']+entry['missing_inputs']))
    if not isinstance(dispatch,pd.DataFrame) or not {'timestamp','grid_import_kw'} <= set(dispatch.columns):
        raise ValueError('Dispatch requires timestamp and grid_import_kw.')
    raw_stamps = list(dispatch.timestamp)
    if any(pd.Timestamp(s).tzinfo is None for s in raw_stamps):
        raise ValueError('Interval timestamps require explicit timezone offsets.')
    stamps = pd.DatetimeIndex(pd.to_datetime(raw_stamps,utc=True)).tz_convert('America/Los_Angeles')
    expected = pd.date_range(start,end,freq='15min',inclusive='left')
    if not stamps.equals(expected):
        raise ValueError('Complete, ordered, gap-free 15-minute interval data is required; hourly peaks are unsupported.')
    imports = np.array([finite(v,'grid_import_kw') for v in dispatch.grid_import_kw])
    if 'grid_export_kw' in dispatch:
        exports = np.array([finite(v,'grid_export_kw') for v in dispatch.grid_export_kw])
        if np.any(exports):
            raise ValueError('Export settlement is unsupported; refusing an actual bill for an exporting account.')
    for col in ('pv_kw','pv_available_kw','generation_kw'):
        if col in dispatch and any(finite(v,col)>0 for v in dispatch[col]):
            raise ValueError('Onsite generation requires unimplemented standby/export review.')
    total_kwh = float(imports.sum()*.25)
    peak_mask = svp_peak_mask(stamps)
    peak_kw = float(imports[peak_mask].max(initial=0)) if rate.utility=='svp' else float(imports.max(initial=0))
    billing_kw = peak_kw
    history = {}
    if rate.utility=='svp' and rate.demand:
        history = _required(account,'previous_11_month_peaks_kw')
        months = [(start-pd.DateOffset(months=i)).strftime('%Y-%m') for i in range(1,12)]
        if not isinstance(history,dict) or set(history)!=set(months):
            raise ValueError('SVP ratchet requires exactly the preceding 11 dated monthly eligible-window peaks; missing history cannot be zero-filled.')
        history = {m:finite(v,'previous peak') for m,v in history.items()}
        billing_kw = (peak_kw+max(peak_kw,*history.values()))/2
    fixed = rate.fixed
    if rate.schedule=='C-1' and account['phase']=='three':
        fixed += 4.33
    tou = account.get('time_of_use',False)
    if type(tou) is not bool:
        raise ValueError('time_of_use must be boolean.')
    if tou and not rate.tou_peak:
        raise ValueError('This AMP schedule has no TOU option.')
    if tou and _required(account,'tou_enrollment_confirmed') is not True:
        raise ValueError('Confirm TOU enrollment and metering; one-time installation fees are outside recurring bills.')
    tier = rate.tier_kwh
    if rate.utility=='amp' and rate.schedule=='D-1':
        heat = _required(account,'heating_source')
        if heat not in ('gas_or_other','permanent_electric'):
            raise ValueError('Use gas_or_other or permanent_electric heating_source.')
        summer = 5<=start.month<=10
        tier = (211 if summer else 253) if heat=='gas_or_other' else (258 if summer else 473)
    quantities = [total_kwh] if tier is None else [min(total_kwh,tier),max(0,total_kwh-tier)]
    fraction_peak = float(imports[peak_mask].sum()*.25/total_kwh) if total_kwh else 0
    lines = {'customer_charge':fixed}
    energy_detail = []
    for i,kwh in enumerate(quantities):
        if tou:
            for name,fraction,prices in [('peak',fraction_peak,rate.tou_peak),('off_peak',1-fraction_peak,rate.tou_offpeak)]:
                energy_detail.append(dict(tier=i+1,period=name,kwh=kwh*fraction,rate=prices[i],amount=kwh*fraction*prices[i]))
        else:
            energy_detail.append(dict(tier=i+1,period='all',kwh=kwh,rate=rate.energy[i],amount=kwh*rate.energy[i]))
    lines['energy_charge'] = sum(x['amount'] for x in energy_detail)
    lines = charge_lines(rate, lines['energy_charge'], billing_kw, total_kwh, account,
                         cb3_pf_active=rate.schedule=='CB-3' and peak_kw >= .1*max(history.values()))
    component_detail = {}
    if rate.utility == 'amp':
        components = {
            'D-1': ((.04612,.11051),(.00652,.00652),(.08670,.15020)),
            'A-1': ((.10031,),(.00652,),(.10263,)),
            'A-2': ((.04439,),(.00652,),(.10225,)),
            'A-3': ((.04693,),(.00652,),(.09607,)),
        }[rate.schedule]
        component_detail = {name:sum(kwh*price for kwh,price in zip(quantities,prices))
                            for name,prices in zip(('distribution','public_purpose','generation'),components)}
    return {'tariff':rate.metadata(),'cycle_start':start.isoformat(),'cycle_end':end.isoformat(),
            'import_kwh':total_kwh,'metered_demand_kw':peak_kw,'billing_demand_kw':billing_kw,
            'energy_detail':energy_detail,'energy_component_detail':component_detail,
            'line_items':lines,'total':sum(lines.values()),
            'account_provenance':dict(account),'source_urls':[rate.source,STATE_SOURCE]+([AMP_BASE+str(i)+'?bidId=' for i in (186,730,184,733)] if rate.utility=='amp' else [NERC_SOURCE]),
            'limitations':['Recurring regular-cycle import bill only. No one-time fees, special programs, standby or export settlement.',
                           'Storage optimization uses the dedicated municipal study path; legacy flat-price studies are separate.']}


def charge_lines(rate, energy_charge, billing_kw, total_kwh, account, *, cb3_pf_active=False, maximum=max):
    """Common bill algebra for numeric billing and dispatch objectives."""
    fixed = rate.fixed + (4.33 if rate.schedule=='C-1' and account['phase']=='three' else 0)
    lines = {'customer_charge':fixed,'energy_charge':energy_charge}
    lines['demand_charge'] = rate.demand*billing_kw
    primary = account['voltage']=='primary_12kv'
    if primary and _required(account,'primary_discount_qualified') is not True:
        raise ValueError('Primary discounts require confirmed tariff-specific delivery/transformer qualification.')
    if rate.utility=='amp':
        lines['energy_adjustment_charge'] = 0.0 # current Rider EAC explicitly states no charge
        lines['primary_voltage_adjustment'] = -.03*sum(lines.values()) if primary else 0.0
        if rate.schedule=='A-3':
            pf = finite(_required(account,'monthly_power_factor_percent'),'monthly power factor',0,100)
            lines['power_factor_adjustment'] = (lines['energy_charge']+lines['demand_charge'])*(1-.03*primary)*(.001*(95-pf))
        else:
            lines['power_factor_adjustment'] = 0.0 # Rider PF is currently A-3 only
        tax = _required(account,'uut_status')
        if tax not in ('standard','reduced_confirmed','exempt_confirmed'):
            raise ValueError('Specify standard/reduced_confirmed/exempt_confirmed uut_status.')
        if tax!='standard' and not account.get('tax_confirmation_reference'):
            raise ValueError('Tax reduction/exemption requires confirmation provenance.')
        lines['utility_users_tax'] = sum(lines.values())*{'standard':.075,'reduced_confirmed':.055,'exempt_confirmed':0}[tax]
    else:
        lines['primary_voltage_adjustment'] = -1.52*billing_kw if primary and rate.demand else 0.0
        if primary and not rate.demand:
            raise ValueError('Primary service under D-1/C-1 is outside supported scope.')
        apply_pf = False
        if rate.schedule=='CB-1':
            apply_pf = _required(account,'power_factor_adjustment_active')
            if type(apply_pf) is not bool or not account.get('power_factor_state_reference'):
                raise ValueError('Confirm the historical CB-1 power-factor activation state and its provenance.')
        if rate.schedule=='CB-3':
            apply_pf = cb3_pf_active
        lines['power_factor_adjustment'] = 0.0
        if apply_pf:
            pf = finite(_required(account,'monthly_power_factor_percent'),'monthly power factor',0,100)
            pf = math.floor(pf+.5)
            lines['power_factor_adjustment'] = sum(lines.values())*.001*(85-pf)
        if rate.schedule=='C-1':
            load = finite(_required(account,'minimum_charge_load_units'),'minimum-charge connected kVA/HP units')
            lines['minimum_charge_adjustment'] = maximum(0,3.43*load-sum(lines.values()))
        lines['public_benefits_charge'] = (fixed+lines['energy_charge']+lines['demand_charge']+lines['primary_voltage_adjustment']+lines['power_factor_adjustment'])*.0285
    exempt = _required(account,'state_surcharge_exempt')
    if type(exempt) is not bool:
        raise ValueError('state_surcharge_exempt must be boolean.')
    if exempt and not account.get('tax_confirmation_reference'):
        raise ValueError('State surcharge exemption requires confirmation provenance.')
    lines['state_energy_surcharge'] = 0.0 if exempt else total_kwh*.00030
    lines['export_credit'] = 0.0
    return lines
