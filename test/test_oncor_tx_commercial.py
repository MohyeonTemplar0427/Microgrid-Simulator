"""Independent rebilling against Oncor small-commercial EFL examples."""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import pytest

from src.billing.oncor_tx_commercial import COMMERCIAL_OFFERS, NEC_COMMERCIAL_RATES


def _subtotal(row, kwh):
    fixed = Decimal(row["monthly"]) + Decimal(row["delivery_monthly"])
    unit_rate = Decimal(row["per_kwh"]) + Decimal(row["delivery_per_kwh"])
    return fixed + kwh * unit_rate


@pytest.mark.parametrize("start", NEC_COMMERCIAL_RATES)
def test_commercial_label_examples(start):
    row = NEC_COMMERCIAL_RATES[start]
    assert row["label_date"] == start
    assert row["term_months"] == 0
    assert len(row["average_cents"]) == 3
    for kwh, published in zip((1500, 2500, 3500), row["average_cents"]):
        cents_per_kwh = _subtotal(row, kwh) * 100 / kwh
        assert cents_per_kwh.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP) == Decimal(published)


def test_october_2025_change_is_by_bill_issue_date():
    first = NEC_COMMERCIAL_RATES["2025-10-01"]
    revised = NEC_COMMERCIAL_RATES["2025-10-03"]
    assert first["bill_end"] == "2025-10-02"
    assert revised["bill_end"] == "2025-10-31"
    assert _subtotal(first, 2500) == Decimal("339.0025")
    assert _subtotal(revised, 2500) == Decimal("324.0025")


@pytest.mark.parametrize("blocked", [
    "2025-01-31", "2025-03-31", "2025-04-30", "2025-06-30", "2025-07-31",
    "2025-08-31", "2026-08-31", "2026-11-20", "2026-12-01",
])
def test_missing_and_conflicting_commercial_efls_have_no_enabled_row(blocked):
    issue_date = date.fromisoformat(blocked)
    assert not any(
        date.fromisoformat(start) <= issue_date <= date.fromisoformat(row["bill_end"])
        for start, row in NEC_COMMERCIAL_RATES.items()
    )


@pytest.mark.parametrize("term,expected", [
    (12, ("18.0", "19.0", "18.8")),
    (24, ("16.6", "17.6", "17.4")),
])
def test_ambit_fixed_labels_against_three_published_examples(term, expected):
    # EFL tables print the illustrative TDU components and demand explicitly.
    # Actual bills use the tariff in force at service, independent of these figures.
    examples = [
        ("le10", "secondary_le_10_kw", 1500, 7, "6.87", "0.046202", "0"),
        ("gt10", "secondary_gt_10_kw", 2500, 11, "32.43", "0.000223", "10.878180"),
        ("gt10", "secondary_gt_10_kw", 3500, 16, "32.43", "0.000223", "10.878180"),
    ]
    for (tier, schedule, kwh, kw, fixed, delivery_energy, demand), cents in zip(examples, expected):
        row = COMMERCIAL_OFFERS[f"ambit_tsc{term}_20250510_{tier}"]
        assert row["term_months"] == term
        assert row["schedule"] == schedule
        assert row["label_date"] == "2025-05-10"
        assert row["usage_fee_below_kwh"] == 1250
        assert row["usage_fee_usd"] == "9.99"
        tdu = Decimal(fixed) + Decimal(delivery_energy) * kwh + Decimal(demand) * kw
        supply = Decimal(row["monthly"]) + Decimal(row["per_kwh"]) * kwh
        average = (tdu + supply) * 100 / kwh
        assert average.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP) == Decimal(cents)
