"""The municipal bill example verifies arithmetic, with no dated rider coverage."""
import json
from decimal import Decimal as D, ROUND_HALF_UP
from pathlib import Path

import pytest

from src.billing import cleveland_public_oh as utility


def test_city_winter_brochure_and_dated_energy_blocks():
    path = Path(__file__).resolve().parents[1]/"docs/utility_sources/cleveland_public_oh/sources.json"
    sample = json.loads(path.read_text())["illustrative_bill"]
    kwh = D(str(sample["kwh"]))
    base = kwh*D(str(utility.BASE["523.02"][2025]["winter"][0]))
    tax = (kwh*D(".00465")).quantize(D(".01"), ROUND_HALF_UP)
    recovery = kwh*D(str(sample["recovery_usd_per_kwh"]))
    assert [base, tax, recovery, base+tax+recovery] == [D("37.60"), D("2.33"), D("39.69"), D("79.62")]
    assert utility.BASE["523.03"]["first_kwh"] == 7500
    assert utility.BASE["523.03"][2026]["summer"] == (.0851, .0499)


@pytest.mark.parametrize("plan", ("523.02", "523.03"))
@pytest.mark.parametrize("month", ["2025-01", "2025-11", "2026-01", "2026-10", "2026-12"])
def test_complete_bills_blocked_even_for_brochure_month(plan, month):
    row = next(p for p in utility.catalog() if p["id"] == plan)
    assert row["status"] == "unsupported" and row["coverage"] == row["equipment_modes"] == []
    account = {**utility.defaults(plan), "billing_month": month+"-01", "eligibility_confirmed": True}
    with pytest.raises(ValueError, match="monthly power supply recovery"):
        utility.validate_account(account, None)
