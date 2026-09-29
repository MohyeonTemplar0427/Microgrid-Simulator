"""CPA NBT generation bank cannot leak into SCE delivery or protected costs."""
import pytest

from src.billing.cpa_solar_settlement import monthly_generation_ledger
from src.billing.solar_programs import programs_for


def test_cpa_monthly_generation_credit_is_restricted_and_carries():
    result = monthly_generation_ledger(generation_energy_charge=20.,
                                       earned_generation_eec=40.,
                                       opening_generation_eec=5.)
    assert result['applied_generation_eec'] == 20.
    assert result['remaining_generation_energy_charge'] == 0.
    assert result['closing_generation_eec'] == 25.
    # SCE delivery and taxes are not inputs, so CPA credits cannot subtract
    # from them in this ledger.
    assert next(p for p in programs_for('sce', 'cpa')
                if p.id == 'cpa_nbt').simulation_status == 'research_only'


def test_cpa_inherited_credit_is_used_only_up_to_energy_charge():
    result = monthly_generation_ledger(generation_energy_charge=12.,
                                       earned_generation_eec=1.,
                                       opening_generation_eec=4.)
    assert result['applied_generation_eec'] == 5.
    assert result['remaining_generation_energy_charge'] == 7.
    assert result['closing_generation_eec'] == 0.
    with pytest.raises(ValueError, match='nonnegative'):
        monthly_generation_ledger(generation_energy_charge=1.,
                                  earned_generation_eec=-.01)
