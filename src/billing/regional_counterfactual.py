"""Explicit account transformation for an absent-PV grid-only reference.

This is a study counterfactual, not a utility enrollment change. The reference
keeps the chosen ordinary tariff, supplier, demand history, ratchets and existing
contract obligations. It cannot inherit a PV account's NEM eligibility or credits.
Electrical replay remains free to represent genuinely absent PV and storage.
"""
from copy import deepcopy


MODES = {
    "ameren_missouri": ("export_mode", "none"),
    "dominion_energy_virginia": ("solar_mode", "non_export"),
    "dominion_energy_north_carolina": ("solar_program", "non_export"),
    "pseg": ("export_mode", "none"),
    "firstenergy_pa_west_penn": ("export_mode", "none"),
    "firstenergy_ohio_edison": ("export_mode", "none"),
    "peco": ("export_mode", "none"),
    "dte_electric": ("export_mode", "none"),
    "consumers_energy": ("export_mode", "none"),
    "ameren_illinois": ("export_mode", "none"),
}


def grid_only_counterfactual(utility, account, state=None):
    """Return copied reference account/state and an auditable explanation.

    Call only for an absent-PV, absent-storage reference. Scenario orchestration
    must still validate the resulting account against its actual service dates;
    this helper does not waive tariff, contract or reclassification restrictions.
    Already non-export accounts are copied without changing their account facts.
    """
    if utility not in MODES or not isinstance(account, dict) or state is not None and not isinstance(state, dict):
        raise ValueError("Grid-only reference requires a supported utility and structured account/state.")
    result, inherited = deepcopy(account), deepcopy(state)
    field, ordinary_mode = MODES[utility]
    mode = account.get(field)
    if mode not in (ordinary_mode, "net_metering"):
        raise ValueError("Validate the explicit solar enrollment before creating its grid-only reference.")
    changed_account, changed_state = [], []

    def set_account(key, value):
        if key not in result or result[key] != value:
            changed_account.append(key)
        result[key] = value

    def set_state(key, value):
        if inherited is not None and key in inherited:
            if inherited[key] != value:
                changed_state.append(key)
            inherited[key] = value

    applied = mode == "net_metering"
    if utility in ("dte_electric", "consumers_energy", "ameren_illinois", "ameren_missouri"):
        applied = bool(result.get("dg_enrollment_confirmed"))
        set_account("dg_enrollment_confirmed", False)
        set_account("dg_source", "")
        return {"account":result,"state":inherited,"applied":applied,
                "label":"Absent-DER grid-only counterfactual; ordinary full-service tariff retained without DG enrollment",
                "changed_account_fields":changed_account,"changed_state_fields":[],
                "warnings":["Hypothetical ordinary grid-only reference removes PV/storage and DG assertions; no actual account transition or export credits assumed."]}
    if utility.startswith("firstenergy_") or utility == "peco":
        applied = bool(result.get("der_ordinary_service_confirmed"))
        set_account("der_ordinary_service_confirmed", False)
        set_account("der_eligibility_source", "")
        return {"account":result,"state":inherited,"applied":applied,
                "label":"Ordinary absent-DER grid-only counterfactual; selected default tariff and demand history retained",
                "changed_account_fields":changed_account,"changed_state_fields":[],
                "warnings":["Grid-only removes the hypothetical renewable installation; no export credits, standby service or actual account transition is assumed."]}
    if applied:
        set_account(field, ordinary_mode)
        if utility == "dominion_energy_virginia":
            set_account("nem", None)
            if inherited is not None and "nem" in inherited:
                del inherited["nem"]
                changed_state.append("nem")
        elif utility == "dominion_energy_north_carolina":
            empty = {"on_peak": 0., "off_peak": 0.}
            set_account("opening_credit_kwh", empty)
            set_account("net_metering_confirmed", False)
            set_state("credit_kwh", deepcopy(empty))
        else:
            set_account("opening_credit_kwh", {})
            set_account("net_metering_confirmed", False)
            set_account("net_metering_size_confirmed", False)
            set_account("anniversary_true_up", False)
            set_state("credit_kwh", {})
    return {"account": result, "state": inherited, "applied": applied,
            "label": "Ordinary grid-only counterfactual without PV or NEM credits" if applied else "Grid-only reference with unchanged non-export account",
            "changed_account_fields": changed_account, "changed_state_fields": changed_state,
            "warnings": ["Grid-only is a counterfactual ordinary/non-export account without installed PV or storage. Solar NEM enrollment, opening credits and true-up settlement are excluded; the selected tariff, supplier, existing contract obligations and demand history are retained. This is not an actual utility enrollment change."] if applied else []}
