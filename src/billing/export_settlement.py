"""Restricted credit accounts shared by billing and dispatch.

A credit earned is not cash revenue. This monthly ledger explicitly distinguishes
usable generation/delivery credits, unrestricted bonus credits, and carryover.
It does not implement annual true-up, NSC, retail netting or account termination.
Those must be supplied by a provider adapter before offering a complete program.
"""
from dataclasses import dataclass, asdict
import math


def nonnegative(value, name):
    if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value) or value<0:
        raise ValueError(f'{name} must be finite and nonnegative.')
    return float(value)


@dataclass(frozen=True)
class CreditBalance:
    generation: float=0.
    delivery: float=0.
    bonus: float=0.

    def __post_init__(self):
        for name,value in asdict(self).items(): nonnegative(value,name+' credit balance')


def monthly_credit_ledger(charges, earned, opening=CreditBalance()):
    """Pay eligible components first; unused credits persist by component.

    Charges: generation, delivery, protected (NBC/fixed/demand/etc).
    Earned: generation, delivery, bonus. All nonnegative dollars.
    Bonus is used only after restricted credits to avoid wasting flexibility.
    """
    if set(charges)!={'generation','delivery','protected'} or set(earned)!={'generation','delivery','bonus'}:
        raise ValueError('Supply all generation/delivery/protected charges and generation/delivery/bonus credits.')
    charges={k:nonnegative(v,k+' charge') for k,v in charges.items()}
    earned={k:nonnegative(v,k+' earned credit') for k,v in earned.items()}
    used={};closing={}
    for k in ('generation','delivery'):
        available=getattr(opening,k)+earned[k]
        used[k]=min(charges[k],available);closing[k]=available-used[k]
    remaining=sum(charges.values())-sum(used.values())
    used['bonus']=min(remaining,opening.bonus+earned['bonus'])
    closing['bonus']=opening.bonus+earned['bonus']-used['bonus']
    return dict(import_charges=charges,credits_earned=earned,credits_used=used,
                amount_due=max(0.,remaining-used['bonus']),opening_balance=asdict(opening),
                closing_balance=closing)


def monthly_credit_objective(charges, earned, opening, constraints):
    """Exact minimized cash due for the same monthly credit restrictions.

    No terminal cash value is assigned to unused credit. Callers must disclose
    this finite-horizon objective. Not a substitute for annual true-up.
    """
    import cvxpy as cp
    used={key:cp.Variable(nonneg=True) for key in ('generation','delivery','bonus')}
    for key in ('generation','delivery'):
        constraints.extend([used[key]<=charges[key],used[key]<=getattr(opening,key)+earned[key]])
    rest=sum(charges.values())-used['generation']-used['delivery']
    constraints.extend([used['bonus']<=rest,used['bonus']<=opening.bonus+earned['bonus']])
    return rest-used['bonus']


def compare_one_kwh(import_now, export_now, import_later, *, round_trip_efficiency,
                    degradation_per_delivered_kwh=0., avoided_demand_value=0., export_later=None):
    """Marginal values for one AC kWh; export inputs must be usable-credit values.

    Diagnostic only: does not schedule a battery or claim annual profitability.
    Demand value must reflect reduction of a billed peak, not every interval.
    """
    for name,value in locals().copy().items():
        if value is not None:nonnegative(value,name)
    if not 0<round_trip_efficiency<=1:raise ValueError('Efficiency must be in (0, 1].')
    eta=round_trip_efficiency
    values={'use_now':import_now,'export_now':export_now,
            'store_for_load':eta*(import_later-degradation_per_delivered_kwh)+avoided_demand_value}
    if export_later is not None:values['store_for_export']=eta*(export_later-degradation_per_delivered_kwh)
    return {'value_per_available_kwh':values,'highest_value_action':max(values,key=values.get),
            'assumption':'Marginal usable credits; excludes equipment capital cost and competing capacity/SOC constraints.'}
