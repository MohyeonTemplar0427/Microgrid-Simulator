"""Independent Decimal rebills from Oncor tariff sheets, supplier EFLs and Texas 96-1309."""
from decimal import Decimal, ROUND_HALF_UP

import numpy as np
import pandas as pd
import pytest

from src.billing.oncor_tx import hypothetical_defaults
from src.billing.regional import calculate_cycle


# The source tuples are in printed tariff order: customer, meter, distribution,
# NDC, TCRF, EECRF, DCRF and RCE. The first two values are per month.
# Prior base and NDC: PUCT 54817, item 28, part 1, PDF pp. 69, 71, 96.
# September TCRF, March 2025 EECRF and May 2025 DCRF: Oncor tariff sheets
# 6.1, 6.3 and 6.4. June 2026 base and RCE: current book PDF pp. 67, 69, 106.
DELIVERY = {
    ("2025", "res"): ("1.43", "2.80", ".025344", ".000199", ".023580", ".001137", ".005772", "0"),
    ("2025", "small"): ("2.26", "4.61", ".021251", ".000130", ".018157", "-.000196", ".006411", "0"),
    ("2026", "res"): ("1.48", "2.58", ".036043", "0", ".023580", ".001487", "0", ".000086"),
    ("2026", "small"): ("2.34", "4.36", ".031236", "0", ".018157", ".000055", "0", ".000084"),
}
VOLUME_NAMES = (
    "distribution_system_charge", "nuclear_decommissioning", "transmission_cost_recovery",
    "energy_efficiency_cost_recovery", "distribution_cost_recovery", "rate_case_expense",
)


# Supply rates transcribed from the issue-date-matched NEC EFLs and from
# Constellation versions 381771 (May 2025) and 4930520 (April 2026).
@pytest.mark.parametrize(("month", "issued", "plan", "supplier_rate"), [
    ("2025-09-01", "2025-09-30", "NEC-RES", ".0983"),
    ("2025-09-01", "2025-09-30", "NEC-SMALL", ".0983"),
    ("2025-09-01", "2025-10-02", "NEC-SMALL", ".0841"),
    ("2025-09-01", "2025-10-03", "NEC-SMALL", ".0781"),
    ("2025-10-01", "2025-10-31", "NEC-RES", ".0781"),
    ("2025-10-01", "2025-10-31", "constellation_381771", ".1130"),
    ("2026-06-01", "2026-06-30", "NEC-RES", ".0974"),
    ("2026-06-01", "2026-06-30", "NEC-SMALL", ".0974"),
    ("2026-06-01", "2026-06-30", "constellation_4930520", ".0885"),
])
@pytest.mark.parametrize("scope", ["pretax_subtotal", "unincorporated_state_only"])
def test_source_rebill(month, issued, plan, supplier_rate, scope):
    start = pd.Timestamp(month, tz="America/Chicago")
    index = pd.date_range(start, start + pd.offsets.MonthBegin(), freq="15min", inclusive="left")
    commercial = plan == "NEC-SMALL"
    fixed = plan.startswith("constellation")
    usage = 1500 if commercial else 1000
    imports = np.zeros(len(index))
    imports[:usage] = 4.0  # one exact kWh per occupied interval
    account = hypothetical_defaults(plan, day=month)
    account.update(bill_date=issued, tax_treatment=scope)
    result = calculate_cycle("oncor_texas", index, imports, np.zeros(len(index)), account)

    customer, meter, *volumetric = map(Decimal, DELIVERY[(month[:4], "small" if commercial else "res")])
    expected = {
        "rep_base_charge": Decimal(0) if fixed else Decimal("7.50"),
        "rep_energy": usage * Decimal(supplier_rate),
        "oncor_customer_charge": customer,
        "oncor_metering_charge": meter,
        "oncor_interim_surcharge": Decimal(0),
        "oncor_mobile_generation": Decimal(0),
    }
    expected.update({"oncor_" + name: usage * rate for name, rate in zip(VOLUME_NAMES, volumetric)})
    complete = scope == "unincorporated_state_only"
    if complete:
        # Comptroller 96-1309 pp. 6–7 excludes separately disclosed nuclear
        # charges and includes billed reimbursements in taxable sales.
        assessable = sum(expected.values()) - expected["oncor_nuclear_decommissioning"]
        if fixed:
            expected["puc_assessment_reimbursement"] = assessable * Decimal(".001667")
        sales_base = assessable + expected.get("puc_assessment_reimbursement", Decimal(0))
        expected["texas_state_sales_tax"] = sales_base * (Decimal(".0625") if commercial else 0)

    assert result["is_complete_bill"] is complete
    assert result["import_kwh"] == usage
    assert result["unrounded_lines"] == pytest.approx({k: float(v) for k, v in expected.items()}, abs=1e-9)
    assert result["unrounded_total_usd"] == pytest.approx(float(sum(expected.values())), abs=1e-9)
    rounded = {k: v.quantize(Decimal(".01"), rounding=ROUND_HALF_UP) for k, v in expected.items()}
    assert result["lines"] == {k: float(v) for k, v in rounded.items()}
    assert result["total_usd"] == float(sum(rounded.values()))
