from copy import deepcopy
from datetime import date
import pandas as pd
import pytest
from src.billing import get_tariff, calculate_meter_billing, TariffError
from src.billing.cleanpowersf import build_b1, CLEANPOWERSF_TARIFFS
from src.local_web.contract import DEFAULT_SITE_REQUEST, validate_request


def tariff(product="green", vintage=2015, phase="single_phase"):
    return build_b1(phase=phase, product=product, vintage=vintage)


def bill(t, start="2026-06-01", periods=24):
    stamps = pd.date_range(start, periods=periods, freq="h", tz="America/Los_Angeles")
    data = pd.DataFrame({"timestamp": stamps, "grid_import_kw": 1., "grid_export_kw": 0.})
    return calculate_meter_billing(data, t, meter_id="pcc", timestep_hours=1)


def test_combined_bill_replaces_bundled_generation_and_pcia_once():
    t = tariff()
    b, = bill(t)
    # 5 peak, 4 part peak, 15 off peak kWh on a summer day.
    generation = 5 * .16197 + 4 * .11958 + 15 * .10166
    delivery = 24 * .29449
    assert b.import_energy_charge_by_component == pytest.approx({
        "cleanpowersf_generation": generation, "pge_delivery": delivery,
        "pcia": 24 * .03602, "franchise_fee": 24 * .00057})
    assert b.total_utility_charge == pytest.approx(generation + delivery + 24 * (.03602 + .00057) + .32854)
    assert b.import_energy_charge == pytest.approx(sum(b.import_energy_charge_by_component.values()))
    assert b.demand_charge == 0


def test_supergreen_phase_and_negative_pcia():
    green, = bill(tariff())
    supergreen, = bill(tariff(product="supergreen", phase="polyphase"))
    assert supergreen.total_utility_charge - green.total_utility_charge == pytest.approx(24*.005 + .82136-.32854)
    credit, = bill(tariff(vintage=2026))
    assert credit.import_energy_charge_by_component["pcia"] == pytest.approx(-24*.00990)
    assert credit.import_energy_charge_by_component["franchise_fee"] == pytest.approx(24*.00090)


def test_winter_super_off_peak_and_dst():
    t=tariff()
    times=pd.DatetimeIndex(["2026-03-01 10:00", "2026-03-01 17:00", "2026-03-01 23:00"],tz="America/Los_Angeles")
    assert t.energy_rates(times).tolist() == pytest.approx([.08638+.27432+.03602+.00057, .11440+.27432+.03602+.00057, .10052+.27432+.03602+.00057])
    day, = bill(t, "2026-03-08",23)
    assert day.billing_days == 1
    assert day.customer_charge == pytest.approx(.32854)
    assert day.import_energy_kWh == 23


@pytest.mark.parametrize("start", ["2026-02-28", "2026-09-17"])
def test_unverified_dates_are_rejected(start):
    with pytest.raises(TariffError): bill(tariff(), start)


def test_service_validation_and_saved_tariff_identity():
    req=deepcopy(DEFAULT_SITE_REQUEST)
    req["tariff_id"]=tariff().tariff_id
    for utility in ("cleanpowersf", "cec:other:12"):
        req["site"]["utility"]=utility
        validate_request(req)
    req["site"]["utility"]="pge"
    with pytest.raises(ValueError, match="CleanPowerSF"): validate_request(req)
    assert get_tariff(tariff().tariff_id) == tariff()


def test_capabilities_and_gui_share_all_choices():
    from src.local_web.worker import capabilities
    from src.simulation.application_interface import TARIFF_LABELS
    choices={t["id"]:t for t in capabilities()["tariffs"]}
    for t in CLEANPOWERSF_TARIFFS:
        assert t.tariff_id in TARIFF_LABELS
        assert choices[t.tariff_id]["service"] == "cleanpowersf"
        assert choices[t.tariff_id]["effective_end"] == "2026-09-16"
