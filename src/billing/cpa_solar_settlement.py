"""Clean Power Alliance NBT generation-credit restrictions, monthly only.

CPA's amended February 5, 2026 NBT tariff sections (b) and (c) restrict its
generation EEC to CPA energy charges. This component does not determine
hourly CPA EEC prices, CPA import rates, SCE delivery settlement or annual
adjustments; it must not be exposed as an executable combined bill.
"""
import math


SOURCE = 'https://files.cleanpoweralliance.org/uploads/2026/03/CPA-Net-Billing-Tariff-2026-02-05.pdf'


def _dollars(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f'{label} must be finite nonnegative dollars.')
    return float(value)


def monthly_generation_ledger(*, generation_energy_charge,
                              earned_generation_eec, opening_generation_eec=0.):
    """Apply CPA EEC only to CPA energy; retain the unused dollar balance.

    SCE delivery, CPA demand, taxes, fixed charges and fees are outside this
    ledger and cannot be paid with the credit. Rates must be priced upstream
    from the customer's actual dated CPA schedule and export-price vintage.
    """
    charge = _dollars(generation_energy_charge, 'CPA generation energy charge')
    earned = _dollars(earned_generation_eec, 'CPA earned generation EEC')
    opening = _dollars(opening_generation_eec, 'CPA opening generation EEC')
    applied = min(charge, opening + earned)
    return dict(generation_energy_charge=charge,
                opening_generation_eec=opening,
                earned_generation_eec=earned,
                applied_generation_eec=applied,
                remaining_generation_energy_charge=charge - applied,
                closing_generation_eec=opening + earned - applied,
                source=SOURCE)
