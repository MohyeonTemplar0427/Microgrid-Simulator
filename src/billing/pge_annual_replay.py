"""Replay a confirmed year of bundled PG&E NBT monthly statement components.

This composes the restricted monthly credit ledger with statement-level true-up.
Monthly charges and earned credits must come from documented statements or a
clearly marked hypothetical fixture; this module does not supply historical rates.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from .export_settlement import CreditBalance, monthly_credit_ledger, nonnegative
from .pge_true_up import TrueUpRates, reconcile_nbt


@dataclass(frozen=True)
class MonthlyNBTRecord:
    period_start: str
    period_end: str
    import_kwh: float
    export_kwh: float
    charges: dict[str, float]
    credits_earned: dict[str, float]
    offsettable_paid: dict[str, float]
    source_reference: str
    evidence_kind: str
    stated_amount_due: float | None = None
    stated_closing_balance: CreditBalance | None = None


def _dates(record):
    try:
        start = date.fromisoformat(record.period_start)
        end = date.fromisoformat(record.period_end)
    except (TypeError, ValueError) as exc:
        raise ValueError('Monthly service dates must be YYYY-MM-DD.') from exc
    if not 20 <= (end - start).days + 1 <= 40:
        raise ValueError('Each confirmed monthly cycle must contain 20–40 service dates.')
    return start, end


def replay_nbt_year(records, *, account_confirmed, rates=None):
    """Reconcile twelve contiguous confirmed monthly cycles and annual true-up.

    ``offsettable_paid`` is transcribed *remaining* eligible paid generation and
    delivery charges after all monthly credits, including ACC Plus. Its split
    cannot safely be inferred from a single undifferentiated monthly amount due.
    The first cycle starts with zero bank; prior-period carryover is outside this
    first replay contract. Monetary checks allow a two-cent statement rounding
    difference but do not invent or adjust missing charges.
    """
    if not isinstance(records, (list, tuple)) or len(records) != 12:
        raise ValueError('Supply twelve documented monthly NBT cycles.')
    if account_confirmed is not True:
        raise ValueError('Confirm ordinary bundled PG&E NBT and continued service.')
    if rates is not None and not isinstance(rates, TrueUpRates):
        raise ValueError('Supply verified true-up factors or none for a net consumer.')
    balance = CreditBalance()
    monthly = []
    eligible_paid = {'generation': 0., 'delivery': 0.}
    imports = exports = cash_due = 0.
    previous_end = None
    evidence_kind = None
    for number, record in enumerate(records, 1):
        if not isinstance(record, MonthlyNBTRecord):
            raise ValueError('Each cycle must be a MonthlyNBTRecord.')
        start, end = _dates(record)
        if previous_end is not None and start != previous_end + timedelta(days=1):
            raise ValueError('Monthly service dates must be ordered and contiguous.')
        previous_end = end
        if record.evidence_kind not in ('statement_transcription', 'hypothetical'):
            raise ValueError('Identify statement_transcription or hypothetical evidence.')
        if evidence_kind is None:
            evidence_kind = record.evidence_kind
        elif record.evidence_kind != evidence_kind:
            raise ValueError('Do not mix actual statement and hypothetical monthly evidence.')
        if not isinstance(record.source_reference, str) or not record.source_reference.strip():
            raise ValueError('Each monthly record needs a non-sensitive source reference.')
        imported = nonnegative(record.import_kwh, 'Monthly imports')
        exported = nonnegative(record.export_kwh, 'Monthly exports')
        ledger = monthly_credit_ledger(record.charges, record.credits_earned, balance)
        if record.stated_amount_due is not None:
            stated = nonnegative(record.stated_amount_due, 'Stated monthly amount due')
            if abs(stated - ledger['amount_due']) > .02:
                raise ValueError('Stated monthly electricity amount due does not reconcile with the credit ledger.')
        if record.stated_closing_balance is not None:
            if not isinstance(record.stated_closing_balance, CreditBalance):
                raise ValueError('Stated closing balance must separate generation, delivery and bonus.')
            for key, computed in ledger['closing_balance'].items():
                if abs(getattr(record.stated_closing_balance, key) - computed) > .02:
                    raise ValueError('Stated monthly closing credit balance does not reconcile.')
        if not isinstance(record.offsettable_paid, dict) or set(record.offsettable_paid) != {'generation', 'delivery'}:
            raise ValueError('Supply remaining offsettable paid generation and delivery charges.')
        paid = {key: nonnegative(record.offsettable_paid[key], key + ' paid') for key in eligible_paid}
        for key in eligible_paid:
            uncredited = ledger['import_charges'][key] - ledger['credits_used'][key]
            if paid[key] > uncredited + .02:
                raise ValueError('Offsettable paid charges exceed eligible charges after restricted credits.')
            eligible_paid[key] += paid[key]
        if sum(paid.values()) > ledger['amount_due'] + .02:
            raise ValueError('Offsettable paid charges exceed the monthly amount due after ACC Plus.')
        imports += imported
        exports += exported
        cash_due += ledger['amount_due']
        monthly.append(dict(cycle=number, period_start=record.period_start, period_end=record.period_end,
                            import_kwh=imported, export_kwh=exported, source_reference=record.source_reference,
                            offsettable_paid=paid, **ledger))
        balance = CreditBalance(**ledger['closing_balance'])
    if rates is not None and rates.evidence_kind != evidence_kind:
        raise ValueError('True-up factors and monthly records must use the same evidence kind.')
    true_up = reconcile_nbt(period_start=records[0].period_start,
                            period_end=records[-1].period_end,
                            annual_import_kwh=imports, annual_export_kwh=exports,
                            bank=balance, offsettable_paid=eligible_paid,
                            account_confirmed=account_confirmed,
                            history_reference='; '.join(record.source_reference for record in records),
                            rates=rates)
    return dict(program='PG&E bundled NBT annual statement replay', evidence_kind=evidence_kind,
                monthly=monthly, annual_import_kwh=imports, annual_export_kwh=exports,
                monthly_amount_due_sum=cash_due, pre_true_up_balance=dict(balance.__dict__),
                remaining_offsettable_paid=eligible_paid, true_up=true_up,
                next_period_balance_before_bonus_application=dict(**true_up['closing_restricted_credit'], bonus=balance.bonus),
                warnings=['Monthly charges and export credits are supplied from documented statements or hypothetical fixtures; historical interval rates are not inferred.',
                          'The true-up adjustment is a separate bill credit or charge, not necessarily an immediate cash payment.',
                          'Annual dispatch, taxes, prior-period opening credits and special accounts are outside this replay.'])
