"""Potomac Edison Maryland R and bounded unmetered G Type I SOS.

R has complete ordinary component coverage; G is a disclosed subtotal. Unknown
G transmission minimum/capacity and state tax never silently become zero. The
G distribution minimum is accepted only when conservatively proved inactive.
"""
from copy import deepcopy
import numpy as np
import pandas as pd
from .potomac_edison_md_rates import COVERAGE, PLANS, SOURCES, rates_on

UTILITY = "potomac_edison_maryland"
TIMEZONE = "America/New_York"
TRANSMISSION_EXCLUSION = "g_transmission_minimum_capacity_charge"
SALES_TAX_EXCLUSION = "maryland_state_sales_tax"


def excluded_components(plan):
    return [] if plan == "R" else [TRANSMISSION_EXCLUSION, SALES_TAX_EXCLUSION]


def hypothetical_history(billing_month="2026-09-01"):
    end = pd.Timestamp(billing_month)-pd.offsets.MonthBegin()
    return [dict(month=str(x.date())[:7], import_kwh=1000.) for x in pd.date_range(end=end, periods=12, freq="MS")]


def account_fields(plan="R"):
    return [dict(name=k, type="boolean", default=False, required=True, label=v) for k,v in (
        ("eligibility_confirmed", "Potomac Edison Maryland delivery, selected R/G schedule and residential/Type I SOS independently confirmed"),
        ("ordinary_service_confirmed", "Ordinary continuous service for at least12months; no Monthly Service adders, competitive supply, standby/AGS, assistance, special facilities or adjustments"),
        ("full_monthly_charges_confirmed", "Complete calendar meter cycle with matching billing month and final-day bill date; no shifted/partial allocation"),
        ("local_charges_confirmed", "Unincorporated Washington County ordinary tax status and no special local/relocation surcharge independently confirmed"))] + [
        dict(name="tax_source", type="text", required=True, label="Tax locality/status evidence or explicit hypothetical assumption; omit personal identifiers"),
        dict(name="cycle_source", type="text", required=True, label="Meter-cycle evidence or explicit hypothetical calendar-cycle assumption"),
        dict(name="type_i_confirmed", type="boolean", default=False, label="G: existing utility-assigned Type I SOS including prior demand/usage, independently confirmed"),
        dict(name="demand_method", type="choice", choices=["not_applicable", "unmetered"], label="G: utility-confirmed connection without demand meter; no assessed/metered/off-peak option"),
        dict(name="unmetered_source", type="text", label="G: utility-approved unmetered billing retained across grid/PV/storage scenarios, including unchanged minimum/history rules"),
        dict(name="history_confirmed", type="boolean", default=False, label="G: complete prior12calendar-cycle import history confirmed; retained independently across scenarios"),
        dict(name="history", type="json", label="G: prior12calendar months as month YYYY-MM and import_kwh; current cycle not included"),
        dict(name="history_source", type="text", label="G: historical import evidence or explicit hypothetical history; no capacity reset from simulated PV"),
        dict(name="usc_band", type="choice", choices=["residential", "175_to_1299"], label="Utility-assigned USC annual distribution band; not recomputed by optimization"),
        dict(name="usc_assignment_2026_source", type="text", label="G: utility-assigned USC band throughout2026 based on prior-calendar-year distribution bills; no inferred update date"),
        dict(name="subtotal_scope_confirmed", type="boolean", default=False, label="G: verified-charge subtotal excludes unresolved transmission minimum/capacity and Maryland state sales-tax calculation; distribution minimum must be inactive"),
        dict(name="der_ordinary_service_confirmed", type="boolean", default=False, label="PV/storage: approved ordinary NEM-account parallel service with zero exports and no standby/AGS/special charges"),
        dict(name="der_eligibility_source", type="text", label="Approved ordinary PV/storage agreement, retaining ordinary charges/history; no export settlement or standalone storage modeled"),
        dict(name="rate_evidence_mode", type="choice", choices=["verified"], default="verified", label="Verified intersections only; no provisional or current-rate fallback"),
    ]


def defaults(plan="R"):
    if plan not in PLANS: raise ValueError("Select Potomac Edison Maryland R or G Type I SOS.")
    return dict(tariff=plan, supply="sos", export_mode="none", eligibility_confirmed=False,
        ordinary_service_confirmed=False, full_monthly_charges_confirmed=False, local_charges_confirmed=False,
        tax_jurisdiction="washington_unincorporated", tax_exempt=False, tax_source="", cycle_source="",
        cycle_kind="regular", billing_month="2026-09-01", bill_date="2026-09-30",
        type_i_confirmed=False, demand_method="not_applicable" if plan == "R" else "unmetered", unmetered_source="",
        history_confirmed=False, history=[] if plan == "R" else hypothetical_history(), history_source="",
        usc_band="residential" if plan == "R" else "175_to_1299", usc_assignment_2026_source="",
        subtotal_scope_confirmed=False, rate_evidence_mode="verified", provisional_assumptions_accepted=False,
        der_ordinary_service_confirmed=False, der_eligibility_source="", voltage="secondary", phase="single",
        voltage_v=240., power_factor=1., meter_count=1, service_line_count=1, opening_credit_usd=0., demand_interval_minutes=30)


def hypothetical_defaults(plan="R", year=2026):
    a=defaults(plan)
    a.update(eligibility_confirmed=True, ordinary_service_confirmed=True, full_monthly_charges_confirmed=True,
        local_charges_confirmed=True, hypothetical_account=True, type_i_confirmed=plan == "G",
        history_confirmed=plan == "G", subtotal_scope_confirmed=plan == "G",
        tax_source="Explicit hypothetical ordinary unincorporated Washington County account; no special exemption, local energy levy, relocation or historical adjustment",
        cycle_source="Explicit hypothetical complete calendar meter cycle and final-day bill date; not a customer statement",
        unmetered_source="Explicit hypothetical utility approval of unmetered G method retained with PV/storage, ordinary capacity/minimum/history rules unchanged" if plan == "G" else "Not applicable to R",
        history_source="Explicit hypothetical 1000kWh imported in each of the12calendar cycles preceding the study; ordinary continuous account, no historical reset" if plan == "G" else "Not applicable to R",
        usc_assignment_2026_source="Explicit hypothetical utility-assigned $175–$1299 prior-calendar-year distribution bracket retained throughout2026" if plan == "G" else "Residential USC",
        der_ordinary_service_confirmed=True,
        der_eligibility_source="Explicit hypothetical approved Potomac Edison Maryland ordinary NEM-account PV/storage service, zero exports, no standby/AGS/special charges; ordinary billing method and history retained")
    return a


def catalog():
    return [dict(id=p, label="Potomac Edison Maryland " + ("Residential R SOS" if p == "R" else "G Type I SOS · bounded unmetered subtotal"),
        status="supported", customer_class="residential" if p == "R" else "commercial", voltage="secondary",
        coverage=[dict(start=s,end=e,is_complete_bill=p == "R",scope="Complete ordinary component coverage" if p == "R" else "Verified subtotal; transmission minimum/capacity and state sales tax excluded",excluded_components=excluded_components(p)) for s,e in COVERAGE],
        interval_minutes=[15],solar_modes=["non_export"],supply_arrangements=["sos"],equipment_modes=["grid_only","pv_only","pv_battery"],representative_peak_kw=3.,account_fields=account_fields(p),sources=SOURCES,
        eligibility="Explicit ordinary R residential or unmetered G Type I SOS, continuous service, one secondary120/240V meter, Washington County tax scope and matching complete calendar cycles.",
        limitations=[
            "September–October2026 only. Missing2025 adjustments/earlier final supply/transmission evidence, shifted/partial cycles and future dates reject.",
            "G retains prior12calendar-cycle imported-energy history and the utility-approved unmetered method. Actual30-minute imports must stay below7.5kW and the conservative unmetered capacity upper bound at most7.5kW; metered/assessed demand, reactive charges, other voltage, off-peak and Monthly Service adders are unsupported.",
            "G rejects numerically unless ordinary distribution energy charges exceed the conservative minimum-capacity upper bound, including possible half-kW rounding. Optimization does not force extra purchases to enter this domain; active/uncertain minimum cases fail.",
            "G excludes unresolved transmission minimum/capacity charges and state sales tax. Exclusions are not zero; unknown charges can change dispatch ranking. Proofs concern the verified subtotal, never a complete G bill.",
            "R complete ordinary component coverage includes published zero2026RRC; legislative posting months are outside this window. Component half-up cents and an unrounded objective do not prove an exact rounded-invoice optimum.",
            "USC assignment, locality and Type I history are separate account facts, not derived from modeled usage. No extra GRT, supply admin or wholesale LMP/PLC/NSPL is added to inclusive SOS prices.",
            "PV/storage requires approved ordinary NEM-account service, unchanged billing rules/history and zero exports. No credit bank, NEM export settlement, AGS, standby or standalone storage."])
        for p in PLANS]


def cycle_review(a,index):
    idx=pd.DatetimeIndex(index);step=pd.Timedelta(minutes=15)
    if len(idx)<2 or str(idx.tz)!=TIMEZONE or not np.all(idx[1:]-idx[:-1]==step):
        raise ValueError("Potomac Edison Maryland requires consecutive America/New_York15-minute intervals; missing/duplicate/hourly data reject.")
    stop=idx[-1]+step
    if (idx[0]!=idx[0].normalize() or idx[0].day!=1 or stop!=idx[0]+pd.offsets.MonthBegin()
            or a.get("cycle_kind")!="regular" or a.get("full_monthly_charges_confirmed") is not True
            or a.get("billing_month")!=str(idx[0].date()) or a.get("bill_date")!=str(idx[-1].date())):
        raise ValueError("Potomac Edison scope requires a complete matching calendar meter/service/billing month and bill date on its final day; shifted/partial allocation is unverified.")
    rates_on(a["billing_month"],a["tariff"])
    return dict(service_start=str(idx[0].date()),service_end=str(idx[-1].date()),billing_month=a["billing_month"],bill_date=a["bill_date"],cycle_days=(stop.date()-idx[0].date()).days,elapsed_hours=float((stop-idx[0])/pd.Timedelta(hours=1)),monthly_charge_factor=1.,partial_period_proration_applied=False)


def evidence(index,account):
    cycle_review(account,index)
    return dict(rate_evidence_status="verified",assumption_model=None,rate_assumptions=[],objective_scope="complete_utility_bill" if account["tariff"]=="R" else "verified_charges_subtotal")


def _reference(a,key):
    if not isinstance(a.get(key),str) or not 1<=len(a[key].strip())<=500:
        raise ValueError("Document Potomac Edison cycle, locality, history, USC and operating approvals without personal identifiers.")


def _history(value):
    if not isinstance(value,list) or len(value)!=12:
        raise ValueError("G needs exactly12 prior calendar-month import observations; do not infer missing history.")
    result=[]
    for item in value:
        if not isinstance(item,dict) or set(item)!={"month","import_kwh"} or not isinstance(item['month'],str):
            raise ValueError("G history needs month YYYY-MM and import_kwh only.")
        try:month=pd.Timestamp(item['month']+'-01')
        except (ValueError,TypeError) as exc:raise ValueError("Use exact YYYY-MM G history months.") from exc
        kwh=item['import_kwh']
        if str(month.date())[:7]!=item['month'] or type(kwh) not in (int,float) or not np.isfinite(kwh) or not 0<=kwh<=6000.:
            raise ValueError("G history must have exact months and finite nonnegative kWh within this conservative6000kWh history domain.")
        if result and month!=pd.Timestamp(result[-1]['month']+'-01')+pd.offsets.MonthBegin():
            raise ValueError("G prior-month history must be ordered and consecutive, without duplicates/gaps.")
        result.append(dict(month=item['month'],import_kwh=float(kwh)))
    return result


def validate_account(a,index,equipment=None):
    if not isinstance(a,dict) or a.get('tariff') not in PLANS or a.get('supply')!='sos' or a.get('export_mode')!='none':
        raise ValueError("Select Potomac Edison Maryland R/G residential/Type I SOS and zero export.")
    if a.get('rate_evidence_mode','verified')!='verified' or a.get('provisional_assumptions_accepted',False) is not False:
        raise ValueError("Potomac Edison has no provisional or missing-price fallback.")
    if any(a.get(k) is not True for k in ('eligibility_confirmed','ordinary_service_confirmed','local_charges_confirmed')):
        raise ValueError("Confirm utility, tariff, SOS, ordinary continuous account and Washington County locality independently.")
    for key in ('tax_source','cycle_source'):_reference(a,key)
    if (a.get('tax_jurisdiction')!='washington_unincorporated' or a.get('tax_exempt') is not False
            or (a.get('voltage'),a.get('phase'),a.get('voltage_v'),a.get('power_factor'))!=('secondary','single',240.,1.)
            or a.get('meter_count')!=1 or a.get('service_line_count')!=1 or a.get('opening_credit_usd')!=0. or a.get('demand_interval_minutes')!=30):
        raise ValueError("Potomac Edison first scope needs one ordinary120/240V single-phase meter/service, unity billing PF,30-minute demand and no credits/special tax status.")
    if a['tariff']=='G':
        if a.get('type_i_confirmed') is not True or a.get('demand_method')!='unmetered' or a.get('usc_band')!='175_to_1299' or a.get('history_confirmed') is not True or a.get('subtotal_scope_confirmed') is not True:
            raise ValueError("Confirm utility-assigned G Type I unmetered method, USC band, historical imports and incomplete subtotal scope.")
        for key in ('unmetered_source','history_source','usc_assignment_2026_source'):_reference(a,key)
        _history(a.get('history'))
    elif a.get('type_i_confirmed') is not False or a.get('demand_method')!='not_applicable' or a.get('usc_band')!='residential' or a.get('history')!=[]:
        raise ValueError("R needs residential SOS/USC and no G demand/history method.")
    cycle_review(a,index)
    if equipment and (equipment.get('pv') or equipment.get('battery')):
        if not equipment.get('pv') or a.get('der_ordinary_service_confirmed') is not True:
            raise ValueError("PV/storage needs approved ordinary NEM-account service, zero exports and no standalone storage/AGS/standby charges.")
        _reference(a,'der_eligibility_source')
        if max(equipment.get('pv_dc_kw',0.),equipment.get('pv_ac_kw',0.))+equipment.get('battery_kw',0.)>25.+1e-8:
            raise ValueError("Potomac Edison implementation limits combined PV/storage to25kW; this does not prove approved interconnection.")


def validate_state(a,index,state=None,equipment=None):
    if a['tariff']=='R':
        if state not in (None,{}):raise ValueError("R has no modeled opening credit/history state.")
        return
    if state not in (None,{}) and (not isinstance(state,dict) or set(state)!={'history'}):
        raise ValueError("G carried state contains only its evolving12-month import history.")
    history=_history((state or {}).get('history',a['history']))
    previous=pd.DatetimeIndex(index)[0].normalize()-pd.offsets.MonthBegin()
    if history[-1]['month']!=str(previous.date())[:7]:
        raise ValueError("G history must end immediately before the current complete calendar cycle; no skipped months or reset.")


def charge_lines(index,imports,exports,a,*,math,state=None):
    validate_state(a,index,state=state);idx=pd.DatetimeIndex(index);cycle=cycle_review(a,idx)
    if math.convex:math.constraints.append(exports==0)
    elif np.max(exports)>1e-5:raise ValueError("Potomac Edison export/NEM settlement is not implemented; exports must be zero.")
    r=rates_on(a['billing_month'],a['tariff']);energy=math.hours*math.sum(imports);res=a['tariff']=='R'
    metrics={**cycle,'rates':r,'tax_jurisdiction':a['tax_jurisdiction'],'usc_band':a['usc_band'],
        'additional_gross_receipts_tax_applied':False,'state_sales_tax_status':'residential_filed_schedule_exempt' if res else 'excluded_unresolved_compound_base_and_statutory_brackets',
        'capacity_transmission_treatment':'SOS administration included once; no wholesale LMP/PLC/NSPL charge. G includes verified transmission energy only; minimum/capacity charge is excluded.',
        'legislative_refund_status':'published_posting_months_outside_scope_no_other_adjustments',
        'objective_rounding_scope':'Unrounded filed charge expressions; component half-up cents retained with rounding bound, not exact rounded-invoice optimum'}
    lines={'distribution_customer':r['customer'],'distribution_energy':energy*r['distribution_energy'],**r['monthly']}
    lines.update({k:energy*v for k,v in r['energy'].items()})
    if res:
        lines['generation_energy']=energy*(r['generation_including_admin']-r['embedded_supply_administration'])
        lines['transmission_energy']=energy*r['transmission_energy'];next_state={}
        if math.convex:math.constraints.append(energy<=7500.)
        elif energy>7500.+1e-7:raise ValueError("R study imports must be at most7500kWh; larger-account environmental cap allocation is outside scope.")
    else:
        peak=math.demand(imports,idx,minutes=30)
        if math.convex:math.constraints.extend([peak<=7.49999,energy<=6000.])
        elif peak>=7.5 or energy>6000.+1e-7:raise ValueError("Unmetered G study requires actual30-minute import peak below7.5kW and at most6000kWh/month; no metered-demand/Type I reassignment is inferred.")
        history=_history((state or {}).get('history',a['history']));prior_max=max(x['import_kwh'] for x in history)
        capacity=math.maximum(energy,.5*prior_max,exact=True)/250.
        upper=capacity+.25
        # Regular distribution charges are a lower bound with any upward minimum.
        # Do not constrain purchases to make a minimum inactive. Numeric acceptance
        # must attain this relaxation without entering an unverified floor branch.
        if not math.convex and upper>7.5+1e-7:
            raise ValueError("G conservative unmetered minimum-capacity upper bound must be at most7.5kW; larger capacity/excess-charge interpretation is outside scope.")
        if not math.convex and lines['distribution_energy']+1e-7<1.70*upper:
            raise ValueError("G distribution-minimum inactive domain is unproven for this schedule; no artificial extra imports, assumed rounding or floor formula is allowed.")
        lines['generation_energy']=math.tiered(energy,[700.],[x-r['embedded_supply_administration'] for x in r['generation_including_admin']])
        lines['transmission_energy']=math.tiered(energy,[700.],r['transmission_energy'])
        next_state={'history':(deepcopy(history)+[dict(month=str(idx[0].date())[:7],import_kwh=energy if math.convex else float(energy))])[-12:]}
        metrics.update(actual_30_minute_peak_kw=peak,unmetered_minimum_capacity_raw_kw=capacity,
            minimum_capacity_conservative_upper_kw=upper,distribution_minimum_inactive_verified=None if math.convex else True,
            distribution_minimum_guard='Regular distribution energy >=1.70*(max(current_import_kWh,0.5*prior12max_import_kWh)/250+0.25); conservative rounding/placement guard, checked numerically without forcing purchases',
            transmission_minimum_capacity_status='excluded_unverified_combination_and_rounding',
            demand_method=a['demand_method'],opening_import_history=history,usc_source=a['usc_assignment_2026_source'])
    lines['supply_administration']=energy*r['embedded_supply_administration']
    return dict(lines=lines,metrics=metrics,next_state=next_state,is_complete_bill=res,excluded_components=excluded_components(a['tariff']),
        rate_evidence_status='verified',assumption_model=None,rate_assumptions=[],rate_sources=SOURCES,
        warnings=['Potomac Edison Maryland hypothetical ordinary continuous account; utility/SOS, locality, USC, history and interconnection require independent confirmation.',
            'Complete matching calendar September–October2026 cycles only; no missing-rate substitution or export settlement.',
            'G verified-charge subtotal excludes transmission minimum/capacity and state sales tax; omitted amounts are not zero and can alter dispatch rankings. R has complete ordinary component coverage in this window.',
            'Unmetered G distribution minimum must be conservatively inactive; unknown active branches reject instead of forcing extra imports. No precise half-kW minimum rounding is claimed.',
            '2026 RRC accounting dashes normalize to zero; published legislative posting months are outside this scope, not inferred historical credits.',
            'Historical perfect foresight per cycle; proofs concern unrounded modeled charges within the accepted domain. Representative OpenDSS is not surveyed-site validation.'])
