import pytest
from src.billing.export_settlement import CreditBalance
from src.billing.pge_true_up import TrueUpRates, reconcile_nbt


def inputs():
    return dict(period_start='2024-01-31', period_end='2025-01-31',
                annual_import_kwh=3000., annual_export_kwh=5000.,
                bank=CreditBalance(136.94,22.,1.05),
                offsettable_paid={'generation':4.,'delivery':500.},
                account_confirmed=True, history_reference='PG&E published hypothetical guide example',
                rates=TrueUpRates('2025-01',.04,.01,.02965,'PG&E guide example; not a production rate table','hypothetical'))


def test_published_guide_true_up_example():
    r=reconcile_nbt(**inputs())
    assert r['components']['generation']['recoupment_debit']==80
    assert r['components']['delivery']['recoupment_debit']==20
    assert r['components']['generation']['true_up_adjustment']==-4
    assert r['components']['delivery']['true_up_adjustment']==-2
    assert r['closing_restricted_credit']==pytest.approx({'generation':52.94,'delivery':0})
    assert r['nsc_credit']==pytest.approx(59.3)
    assert r['adjustment_if_all_bonus_applied']==pytest.approx(-66.35)
    assert r['bonus_credit_available']==1.05


def test_recoupment_can_exceed_bank_and_create_charge():
    a=inputs();a['bank']=CreditBalance(0,0,5)
    r=reconcile_nbt(**a)
    assert r['adjustment_before_bonus']==pytest.approx(40.7)
    assert r['bonus_credit_available']==5  # Never recoup ACC Plus.


def test_net_consumer_retroactive_credit_without_nsc_rates():
    a=inputs();a.update(annual_import_kwh=6000,rates=None)
    r=reconcile_nbt(**a)
    assert r['net_surplus_kwh']==0
    assert r['nsc_credit']==0
    assert r['adjustment_before_bonus']==-26
    assert r['closing_restricted_credit']['generation']==pytest.approx(132.94)


@pytest.mark.parametrize('change',[
    {'period_end':'2027-01-31'}, {'rates':None}, {'account_confirmed':False}, {'history_reference':''},
    {'period_start':'2025-01-01'}, {'annual_import_kwh':float('nan')},
    {'annual_export_kwh':-1}, {'offsettable_paid':{'generation':4}},
    {'rates':TrueUpRates('2025-02',.04,.01,.03,'Wrong month','hypothetical')},
])
def test_missing_or_invalid_evidence_rejected(change):
    a=inputs();a.update(change)
    with pytest.raises(ValueError):reconcile_nbt(**a)
