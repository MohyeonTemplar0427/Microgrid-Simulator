from copy import deepcopy
import pandas as pd
import pytest
from src.billing import calculate_meter_billing, TariffError
from src.billing.hetch_hetchy import build_c1, build_c2, HETCH_HETCHY_TARIFFS
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


@pytest.mark.parametrize("tariff", HETCH_HETCHY_TARIFFS)
def test_web_service_pairing(tariff):
    req=deepcopy(DEFAULT_SITE_REQUEST);req["tariff_id"]=tariff.tariff_id
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


@pytest.mark.parametrize("voltage,summer,winter,demand", [
    ("secondary", .24654, .19723, 28.50),
    ("primary", .22247, .17798, 23.94),
])
@pytest.mark.parametrize("premium", [False, True])
def test_c2_monthly_peaks_seasons_and_reconciliation(voltage, summer, winter, demand, premium):
    tariff = build_c2(voltage=voltage, premium=premium)
    timestamps = pd.date_range("2026-10-01", "2026-12-01", inclusive="left",
                               freq="15min", tz="America/Los_Angeles")
    frame = pd.DataFrame({"timestamp": timestamps, "grid_import_kw": 100.0})
    frame.loc[0, "grid_import_kw"] = 200.0
    frame.loc[len(frame)-1, "grid_import_kw"] = 150.0
    bills = calculate_meter_billing(frame, tariff, meter_id="pcc", timestep_hours=.25)
    for b, rate, peak, hours in zip(bills, (summer, winter), (200, 150), (744, 721)):
        energy = 100 * hours + (peak - 100) * .25
        assert b.import_energy_charge == pytest.approx(energy * (rate + (.0095 if premium else 0)))
        assert b.customer_charge == 350
        assert b.demand_charge == pytest.approx(peak * demand)
        assert b.total_utility_charge == pytest.approx(b.import_energy_charge + 350 + peak * demand)
        assert sum(b.import_energy_charge_by_component.values()) == pytest.approx(b.import_energy_charge)
        assert not b.is_partial_period


@pytest.mark.parametrize("prior,peak", [(None, 100), (80, 100), (160, 160)])
def test_c2_partial_dst_month_does_not_prorate_demand(prior, peak):
    stamps = pd.date_range("2027-03-14", "2027-03-15", inclusive="left",
                           freq="15min", tz="America/Los_Angeles")
    b, = calculate_meter_billing(pd.DataFrame({"timestamp": stamps, "grid_import_kw": 100}),
        build_c2(), meter_id="pcc", timestep_hours=.25, previous_peak_kw=prior)
    assert b.import_energy_kWh == 2300
    assert b.customer_charge == pytest.approx(350/31)
    assert b.demand_charge == pytest.approx(peak*28.50)
    assert b.is_partial_period
    assert any("APPROXIMATION" in w for w in b.warnings)


@pytest.mark.parametrize("day,valid", [("2026-06-30", False), ("2026-07-01", True),
    ("2027-06-30", True), ("2027-07-01", False)])
def test_c2_fiscal_coverage(day, valid):
    frame = pd.DataFrame({"timestamp": pd.date_range(day, periods=1, tz="America/Los_Angeles"),
                          "grid_import_kw": [100]})
    def calculate():
        return calculate_meter_billing(frame, build_c2(), meter_id="pcc", timestep_hours=.25)
    if valid:
        assert calculate()[0].demand_charge == 2850
    else:
        with pytest.raises(TariffError):
            calculate()


@pytest.mark.parametrize("minutes", [5, 30, 60])
def test_c2_rejects_unsupported_demand_resolution(minutes):
    tariff = build_c2()
    request = deepcopy(DEFAULT_SITE_REQUEST)
    request.update(tariff_id=tariff.tariff_id, timestep_minutes=minutes)
    request["site"]["utility"] = "hetch_hetchy"
    with pytest.raises(TariffError, match="15-minute"):
        validate_request(request)
    frame = pd.DataFrame({"timestamp": pd.date_range("2026-08-01", periods=2,
        freq=f"{minutes}min", tz="America/Los_Angeles"), "grid_import_kw": 100})
    with pytest.raises(TariffError, match="15-minute"):
        calculate_meter_billing(frame, tariff, meter_id="pcc", timestep_hours=minutes/60)


@pytest.mark.parametrize("voltage", ["secondary", "primary"])
def test_c2_optimizer_cost_reconciles_with_billing(voltage):
    from src.dispatch.single_day_analysis import run_cost_optimization
    from src.simulation.interface_analysis import _maximum_demand_rate
    tariff = build_c2(voltage=voltage, premium=True)
    stamps = pd.date_range("2026-10-31 23:30", periods=4, freq="15min", tz="America/Los_Angeles")
    data = pd.DataFrame({"timestamp": stamps, "load_kw": [100, 120, 100, 130], "pv_kw": 0,
                        "price_per_kWh": tariff.energy_rates(stamps).to_numpy()})
    battery = dict(capacity_kWh=20, initial_soc_kWh=10, min_soc_kWh=2, max_soc_kWh=18,
                   max_charge_kw=20, max_discharge_kw=20, charge_efficiency=.95, discharge_efficiency=.95)
    dispatch = run_cost_optimization(data, battery, demand_charge_rate_per_kw=_maximum_demand_rate(tariff.tariff_id))
    bills = calculate_meter_billing(dispatch, tariff, meter_id="pcc", timestep_hours=.25)
    demand = _maximum_demand_rate(tariff.tariff_id)
    assert demand == (28.50 if voltage == "secondary" else 23.94)
    assert sum(b.demand_charge for b in bills) == pytest.approx(
        demand * (dispatch.grid_import_kw.iloc[:2].max() + dispatch.grid_import_kw.iloc[2:].max()))
    assert sum(b.import_energy_charge for b in bills) == pytest.approx(
        (dispatch.grid_import_kw.to_numpy() * data.price_per_kWh.to_numpy()).sum() * .25)
    assert dispatch.grid_import_kw.max() < 130


@pytest.mark.parametrize("peak,check", [(50, True), (100, False), (500, True), (550, True)])
def test_c2_result_eligibility_and_no_c1_warning(peak, check):
    from types import SimpleNamespace
    from src.simulation.interface_analysis import _apply_tariff_billing
    frame = pd.DataFrame({"timestamp": pd.date_range("2026-08-01", periods=4,
        freq="15min", tz="America/Los_Angeles"), "grid_import_kw": peak})
    comparison = pd.DataFrame({"scenario": ["no_battery"], "carbon_weight": [0.0],
                              "degradation_cost": [0.0], "total_explicit_cost": [0.0]})
    billed, warnings = _apply_tariff_billing(comparison,
        {0.0: SimpleNamespace(dispatch_scenarios={"no_battery": frame})}, first_weight=0.0,
        tariff_id=build_c2().tariff_id, meter_topology_mode="single_pcc", submeter_count=1,
        previous_peak_kw=None, timestep_hours=.25)
    assert any("C-2 ELIGIBILITY CHECK" in w for w in warnings) == check
    assert not any("C-1 ELIGIBILITY" in w for w in warnings)
    assert billed.loc[0, "demand_charge"] == pytest.approx(peak * 28.50)
    assert billed.loc[0, "total_utility_charge"] == pytest.approx(
        billed.loc[0, "energy_cost"] + billed.loc[0, "customer_charge"] + billed.loc[0, "demand_charge"])


@pytest.mark.parametrize("voltage,summer,winter", [
    ("secondary", .24654, .19723), ("primary", .22247, .17798)])
def test_c2_may_boundary_and_previous_peak_only_first_month(voltage, summer, winter):
    stamps = pd.date_range("2027-04-30 23:45", periods=2, freq="15min", tz="America/Los_Angeles")
    bills = calculate_meter_billing(pd.DataFrame({"timestamp": stamps, "grid_import_kw": 100}),
        build_c2(voltage=voltage), meter_id="pcc", timestep_hours=.25, previous_peak_kw=200)
    assert [b.billed_peak_kw for b in bills] == [200, 100]
    assert [b.import_energy_charge for b in bills] == pytest.approx([25*winter, 25*summer])
    assert [b.customer_charge for b in bills] == pytest.approx([350/30, 350/31])


def test_c2_rejects_unverified_voltage_and_implicit_premium():
    with pytest.raises(ValueError, match="voltage"):
        build_c2(voltage="transmission")
    with pytest.raises(ValueError, match="explicit boolean"):
        build_c2(premium="yes")
