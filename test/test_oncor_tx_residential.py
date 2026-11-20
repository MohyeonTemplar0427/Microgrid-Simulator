"""Reconcile supplier-side Oncor residential records against printed EFL examples."""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import pytest

from src.billing.oncor_tx_residential import (
    NEC_RESIDENTIAL_LABELS,
    NEC_RESIDENTIAL_RATES,
    RESIDENTIAL_OFFERS,
)


def _average_cents(dollars, usage):
    return (dollars * 100 / usage).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


@pytest.mark.parametrize("label_date, label", NEC_RESIDENTIAL_LABELS.items())
def test_nec_disclosed_energy_and_delivery_reconcile(label_date, label):
    monthly = Decimal(label["monthly"]) + Decimal(label["delivery_monthly"])
    per_kwh = Decimal(label["per_kwh"]) + Decimal(label["delivery_per_kwh"])
    calculated = tuple(_average_cents(monthly + usage * per_kwh, usage) for usage in (500, 1000, 2000))
    reconciled = calculated == tuple(map(Decimal, label["average_cents"]))
    assert label["benchmark_matches"] == reconciled
    assert (label_date in NEC_RESIDENTIAL_RATES) == reconciled


def test_nec_conflicts_missing_documents_and_bill_date_bounds():
    assert set(NEC_RESIDENTIAL_LABELS) - set(NEC_RESIDENTIAL_RATES) == {
        "2025-02-01", "2026-01-01", "2026-09-01", "2026-10-01",
    }
    assert "2025-01-01" not in NEC_RESIDENTIAL_LABELS
    assert NEC_RESIDENTIAL_RATES["2025-10-01"]["bill_end"] == "2025-10-02"
    assert NEC_RESIDENTIAL_RATES["2025-10-03"]["per_kwh"] == "0.0781"
    assert NEC_RESIDENTIAL_RATES["2026-11-01"]["bill_end"] == "2026-11-19"
    previous_end = date.min
    for start, label in sorted(NEC_RESIDENTIAL_LABELS.items()):
        assert previous_end < date.fromisoformat(start) <= date.fromisoformat(label["bill_end"])
        previous_end = date.fromisoformat(label["bill_end"])


@pytest.mark.parametrize("version, delivery_kwh, expected", [
    ("constellation_310745", "0.052974", ("16.6", "16.1", "15.9")),
    ("constellation_381771", "0.050029", ("17.2", "16.8", "16.5")),
    ("constellation_4930520", "0.056183", ("15.3", "14.9", "14.7")),
])
def test_constellation_oncor_fixed_offer_disclosure(version, delivery_kwh, expected):
    label = RESIDENTIAL_OFFERS[version]
    assert label["term_months"] == 12
    assert Decimal(label["monthly"]) == 0
    assert label["average_cents"] == expected
    for kwh, printed in zip((500, 1000, 2000), expected):
        supply = kwh * Decimal(label["per_kwh"])
        delivery = Decimal("4.23") + kwh * Decimal(delivery_kwh)
        # Published comparison, for a bill with assessment reimbursement and
        # no basis exclusions. Other local taxes are outside these examples.
        assessment = ((supply + delivery) * Decimal("0.001667")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        assert _average_cents(supply + delivery + assessment, kwh) == Decimal(printed)


@pytest.mark.parametrize("plan, issue, delivery_kwh, printed", [
    ("fourchange_onerta24lah_o", "2024-09-01", "0.052000", ("16.9", "15.9", "15.5")),
    ("fourchange_onerta24mac_o", "2025-09-02", "0.056032", ("18.2", "17.2", "16.8")),
])
def test_fourchange_24_month_contract_against_issuer_examples(plan, issue, delivery_kwh, printed):
    offer = RESIDENTIAL_OFFERS[plan]
    assert (offer["label_date"], offer["term_months"]) == (issue, 24)
    assert offer["monthly"] == "4.95"
    assert offer["average_cents"] == printed
    for kwh, expected in zip((500, 1000, 2000), printed):
        supply = Decimal(offer["monthly"]) + kwh * Decimal(offer["per_kwh"])
        # Oncor's independently published residential delivery summary at EFL issue.
        delivery = Decimal("4.23") + kwh * Decimal(delivery_kwh)
        assert _average_cents(supply + delivery, kwh) == Decimal(expected)
