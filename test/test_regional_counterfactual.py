"""Absent-PV reference semantics preserve unrelated account obligations."""
from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from src.billing import dominion_nc as nc, dominion_va_general as va, pseg
from src.billing.regional import calculate_cycle
from src.billing.regional_counterfactual import grid_only_counterfactual


def fixture(utility, commercial=False):
    if utility == "dominion_energy_virginia":
        account = va.defaults("VA-1G")
        account.update(solar_mode="net_metering", parallel_service=True,
            parallel_operation_approved=True, nem=va.nem_defaults())
        account["nem"]["bank_kwh"] = {"on_peak": 10., "off_peak": 20., "super_off_peak": 30.}
        state = {"nem": deepcopy(account["nem"]), "history": deepcopy(account["history"]),
                 "contract_demand_kw": account["contract_demand_kw"]}
        start, end = "2026-09-01", "2026-10-01"
    elif utility == "dominion_energy_north_carolina":
        account = nc.defaults("5P" if commercial else "1T")
        account.update(solar_program="net_metering", net_metering_confirmed=True,
            recs_assignment_confirmed=True, opening_credit_kwh={"on_peak": 10., "off_peak": 20.})
        state = {"credit_kwh": {"on_peak": 40., "off_peak": 50.},
                 "history_peaks_kw": account["history_peaks_kw"].copy(),
                 "history_on_peak_kw": account["history_on_peak_kw"].copy(),
                 "history_kwh": account["history_kwh"].copy(),
                 "history_billing_months": account["history_billing_months"].copy(),
                 "contract_demand_kw": account["contract_demand_kw"]}
        start, end = "2026-08-01", "2026-09-01"
    else:
        account = pseg.hypothetical_defaults("GLP" if commercial else "RS")
        account.update(export_mode="net_metering", net_metering_confirmed=True,
            net_metering_size_confirmed=True, opening_credit_kwh={"all": 10.},
            anniversary_true_up=True,
            true_up_rate={"usd_per_kwh": .05, "source": "Hypothetical verified rate; unused in reference"})
        state = {"credit_kwh": {"all": 20.}, "history_peaks_kw": account["history_peaks_kw"].copy()}
        start, end = "2025-07-01", "2025-08-01"
    index = pd.date_range(start, end, freq="15min", inclusive="left", tz="America/New_York")
    return account, state, index


@pytest.mark.parametrize("utility,commercial", [
    ("dominion_energy_virginia", False),
    ("dominion_energy_north_carolina", False),
    ("dominion_energy_north_carolina", True), ("pseg", False), ("pseg", True),
])
def test_absent_pv_reference_has_no_nem_eligibility_or_bank_and_retains_obligations(utility, commercial):
    account, state, index = fixture(utility, commercial)
    before_account, before_state = deepcopy(account), deepcopy(state)
    ref = grid_only_counterfactual(utility, account, state)
    assert account == before_account and state == before_state
    assert ref["applied"] and ref["warnings"]
    assert "counterfactual" in ref["label"] and "NEM credits" in ref["label"]
    for key, value in account.items():
        if key not in ref["changed_account_fields"]:
            assert ref["account"][key] == value
    for key, value in state.items():
        if key not in ref["changed_state_fields"]:
            assert ref["state"][key] == value
    equipment = {"pv": False, "battery": False, "pv_ac_kw": 0., "battery_kw": 0.}
    bill = calculate_cycle(utility, index, np.ones(len(index)), np.zeros(len(index)),
                           ref["account"], state=ref["state"], equipment=equipment)
    assert np.isfinite(bill["unrounded_total_usd"])
    if utility == "dominion_energy_virginia":
        assert ref["account"]["nem"] is None and "nem" not in ref["state"]
        assert ref["account"]["parallel_service"] is True
    else:
        assert not ref["account"]["net_metering_confirmed"]
        assert not any(ref["account"]["opening_credit_kwh"].values())
        assert not any(ref["state"]["credit_kwh"].values())
    if utility == "pseg":
        assert not ref["account"]["anniversary_true_up"]
        # Pricing evidence is preserved even though its settlement is disabled.
        assert ref["account"]["true_up_rate"] == account["true_up_rate"]
        if commercial:
            assert ref["account"]["generation_obligation_kw"] == 15.
            assert ref["account"]["transmission_obligation_kw"] == 16.


@pytest.mark.parametrize("utility", ["dominion_energy_virginia", "dominion_energy_north_carolina", "pseg"])
def test_without_opening_state_helper_does_not_invent_history(utility):
    account, _, _ = fixture(utility)
    result = grid_only_counterfactual(utility, account)
    assert result["state"] is None
    # Deep copies protect stored user configuration from later scenario mutation.
    result["account"]["tariff"] = "changed"
    assert account["tariff"] != "changed"


@pytest.mark.parametrize("utility", ["dominion_energy_virginia", "dominion_energy_north_carolina", "pseg"])
def test_already_nonexport_accounts_are_idempotent(utility):
    account, state, _ = fixture(utility)
    first = grid_only_counterfactual(utility, account, state)
    second = grid_only_counterfactual(utility, first["account"], first["state"])
    assert second["account"] == first["account"]
    assert second["state"] == first["state"]
    assert second["applied"] is False and second["warnings"] == []
    assert second["changed_account_fields"] == [] and second["changed_state_fields"] == []


def test_unknown_utility_or_ambiguous_export_mode_rejects():
    with pytest.raises(ValueError, match="supported utility"):
        grid_only_counterfactual("unverified", {})
    with pytest.raises(ValueError, match="explicit solar enrollment"):
        grid_only_counterfactual("pseg", {"tariff": "RS"})
