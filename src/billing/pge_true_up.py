"""PG&E bundled NBT statement-level annual reconciliation.

Replays confirmed annual statement aggregates, not an annual interval simulation.
Sources: NBT SC2(d–h), SC5(d); PG&E Solar Billing Plan Guide's true-up example.
Rates are explicit dated evidence inputs; no average of the site's exports is
substituted for PG&E's territory-wide recoupment factors.
"""
from dataclasses import dataclass
from datetime import date
from .export_settlement import CreditBalance, nonnegative

TARIFF_SOURCE = 'https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_NBT.pdf'
GUIDE_SOURCE = 'https://www.pge.com/assets/pge/localized/en/docs/clean-energy/solar/pge-solar-billing-plan-guide.pdf'


@dataclass(frozen=True)
class TrueUpRates:
    """Account's true-up-month factors, transcribed from verified evidence.

    ``hypothetical`` is available for transparent validation fixtures. A source
    reference records provenance; this class does not authenticate a document.
    Renewable attribute adders and NSC opt-out are outside this adapter.
    """
    month: str
    generation_recoupment_per_kwh: float
    delivery_recoupment_per_kwh: float
    nsc_per_kwh: float
    source_reference: str
    evidence_kind: str

    def __post_init__(self):
        try:
            parsed = date.fromisoformat(self.month + '-01')
        except (TypeError, ValueError) as exc:
            raise ValueError('Rate month must be YYYY-MM.') from exc
        if parsed.strftime('%Y-%m') != self.month:
            raise ValueError('Rate month must be YYYY-MM.')
        for field in ('generation_recoupment_per_kwh', 'delivery_recoupment_per_kwh', 'nsc_per_kwh'):
            nonnegative(getattr(self, field), field)
        if not isinstance(self.source_reference, str) or not self.source_reference.strip():
            raise ValueError('A non-sensitive rate evidence reference is required.')
        if self.evidence_kind not in ('statement_transcription', 'hypothetical'):
            raise ValueError('Identify statement_transcription or hypothetical rate evidence.')


def reconcile_nbt(*, period_start, period_end, annual_import_kwh,
                  annual_export_kwh, bank, offsettable_paid, account_confirmed,
                  history_reference, rates=None):
    """Return true-up adjustments before application to the current bill.

    Dates are inclusive service dates from the confirmed annual statement.
    ``offsettable_paid`` contains generation/delivery amounts still eligible for
    retrospective offset, AFTER credits previously used (including bonus).
    Do not pass gross prior bills: doing so can refund already credited charges.
    ``bank`` is the unused bank immediately before annual recoupment.
    Bonus remains separately available; this function does not turn it into cash.
    """
    start, end = date.fromisoformat(period_start), date.fromisoformat(period_end)
    if not date(2024, 2, 15) <= end <= date(2026, 9, 21):
        raise ValueError('Verified true-up rule coverage ends September 21, 2026 and begins February 15, 2024.')
    if not 330 <= (end-start).days+1 <= 400:
        raise ValueError('Supply a confirmed full annual relevant period, not a partial study.')
    if account_confirmed is not True:
        raise ValueError('Confirm ordinary bundled PG&E NBT, continued service, NSC participation and no RAA/special adjustments.')
    if not isinstance(history_reference, str) or not history_reference.strip():
        raise ValueError('Supply the source of the complete annual statement aggregates.')
    if not isinstance(bank, CreditBalance):
        raise ValueError('Supply separate generation, delivery and bonus credit balances.')
    if set(offsettable_paid) != {'generation', 'delivery'}:
        raise ValueError('Supply remaining offsettable paid charges separately by component.')
    paid = {k: nonnegative(v, k+' offsettable paid charges') for k,v in offsettable_paid.items()}
    imports = nonnegative(annual_import_kwh, 'Annual imports')
    exports = nonnegative(annual_export_kwh, 'Annual exports')
    surplus = max(exports-imports, 0.)
    if rates is not None and (not isinstance(rates, TrueUpRates) or rates.month != end.strftime('%Y-%m')):
        raise ValueError('Factors must cover the true-up month; no nearest-month substitution.')
    if surplus and rates is None:
        raise ValueError('Net surplus requires verified generation/delivery recoupment and NSC factors for the true-up month.')
    components = {}
    for key in ('generation', 'delivery'):
        debit = surplus * getattr(rates, key+'_recoupment_per_kwh') if surplus else 0.
        available = getattr(bank, key)
        applied = min(available, debit+paid[key])
        components[key] = dict(recoupment_debit=debit, banked_credit_applied=applied,
                               true_up_adjustment=debit-applied,
                               closing_restricted_credit=available-applied)
    nsc = surplus*rates.nsc_per_kwh if surplus else 0.
    adjustment = sum(c['true_up_adjustment'] for c in components.values())-nsc
    return dict(program='PG&E bundled NBT', period_start=period_start, period_end=period_end,
                net_surplus_kwh=surplus, components=components, nsc_credit=nsc,
                adjustment_before_bonus=adjustment,
                bonus_credit_available=bank.bonus,
                adjustment_if_all_bonus_applied=adjustment-bank.bonus,
                closing_restricted_credit={k:v['closing_restricted_credit'] for k,v in components.items()},
                history_reference=history_reference,
                rate_evidence=None if rates is None else dict(rates.__dict__),
                sources=[TARIFF_SOURCE, GUIDE_SOURCE],
                warnings=['Statement-level reconciliation only; annual import/export rates and dispatch are not reconstructed.',
                          'Negative adjustment is a bill credit, not automatic cash payout. Bonus is separately available and must not be subtracted twice.',
                          'Excludes taxes, RAA, NSC opt-out, termination, CCA, aggregation and special accounts.'])
