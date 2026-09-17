from copy import deepcopy
import pandas as pd
import pytest
from src.billing import calculate_meter_billing, TariffError
from src.billing.hetch_hetchy import build_c1, HETCH_HETCHY_TARIFFS
from src.local_web.contract import DEFAULT_SITE_REQUEST, validate_request


def bill(start, end, premium=False, kw=1):
    stamps=pd.date_range(start,end,inclusive="left",freq="15min",tz="America/Los_Angeles")
    return calculate_meter_billing(pd.DataFrame({"timestamp":stamps,"grid_import_kw":kw}),
        build_c1(premium=premium),meter_id="pcc",timestep_hours=.25)


def test_full_month_charge_is_not_scaled_to_thirty_days():
    summer, = bill("2026-08-01","2026-09-01")
    winter, = bill("2027-02-01","2027-03-01")
    assert summer.customer_charge == pytest.approx(19.63)
    assert winter.customer_charge == pytest.approx(19.63)
    assert summer.import_energy_charge == pytest.approx(31*24*.39660)
    assert winter.import_energy_charge == pytest.approx(28*24*.31872)
    assert summer.demand_charge == 0
    assert set(summer.import_energy_charge_by_component) == {"hetch_hetchy_energy","hetch_hetchy_premium"}


def test_premium_is_added_once_and_months_are_separate():
    months=bill("2026-10-01","2026-12-01",premium=True)
    assert len(months)==2
    for b in months:
        assert b.customer_charge == pytest.approx(19.63)
        assert b.import_energy_charge_by_component["hetch_hetchy_premium"] == pytest.approx(b.import_energy_kWh*.00950)
        assert sum(b.import_energy_charge_by_component.values()) == pytest.approx(b.import_energy_charge)
    # Hetch Hetchy October is summer, unlike PG&E; November is winter.
    assert months[0].import_energy_charge == pytest.approx(31*24*(.39660+.00950))
    assert months[1].import_energy_charge == pytest.approx((30*24+1)*(.31872+.00950))


def test_partial_month_dst_has_one_day_customer_allocation():
    b, = bill("2027-03-14","2027-03-15")
    assert b.import_energy_kWh == 23
    assert b.customer_charge == pytest.approx(19.63/31)
    assert any("APPROXIMATION" in w for w in b.warnings)


@pytest.mark.parametrize("start,end",[("2026-06-30","2026-07-01"),("2027-06-30","2027-07-02")])
def test_outside_fiscal_year_rejected(start,end):
    with pytest.raises(TariffError): bill(start,end)


def test_web_service_pairing():
    req=deepcopy(DEFAULT_SITE_REQUEST);req["tariff_id"]=build_c1().tariff_id
    for service in ("hetch_hetchy","cec:distribution:52"):
        req["site"]["utility"]=service;validate_request(req)
    for service in ("pge","cleanpowersf","unconfirmed"):
        req["site"]["utility"]=service
        with pytest.raises(ValueError,match="Hetch Hetchy"):validate_request(req)


def test_shared_gui_web_catalog():
    from src.local_web.worker import capabilities
    from src.simulation.application_interface import TARIFF_LABELS
    caps={t["id"]:t for t in capabilities()["tariffs"]}
    for t in HETCH_HETCHY_TARIFFS:
        assert TARIFF_LABELS[t.tariff_id]==t.name
        assert caps[t.tariff_id]["service"]=="hetch_hetchy"
        assert caps[t.tariff_id]["effective_end"]=="2027-06-30"
