"""Source-pinned CCA billing, provider boundaries, and shared interface coverage."""
from copy import deepcopy
from datetime import timedelta

import pandas as pd
import pytest

from src.billing import TariffError, calculate_meter_billing, get_tariff
from src.billing.bay_area_cca import BAY_AREA_CCA_TARIFFS, PROVIDERS, build_b1
from src.billing.services import SERVICES, canonical_service, tariff_service
from src.local_web.contract import DEFAULT_SITE_REQUEST, validate_request


def tariff(provider, product=None, phase="single_phase", vintage=2018):
    return build_b1(provider=provider, phase=phase,
                    product=product or PROVIDERS[provider].products[0][0], vintage=vintage)


def bill(t, day="2026-08-01", periods=24):
    stamps = pd.date_range(day, periods=periods, freq="h", tz="America/Los_Angeles")
    return calculate_meter_billing(pd.DataFrame({"timestamp": stamps, "grid_import_kw": 1.0}),
                                   t, meter_id="pcc", timestep_hours=1)


@pytest.mark.parametrize("provider,peak,part,off", [
    ("peninsula", .13091, .08414, .06437),
    ("svce", .13823, .08949, .06889),
    ("sjce", .13452, .08677, .06658),
])
def test_source_rates_and_no_duplicate_generation_or_adjustments(provider, peak, part, off):
    b, = bill(tariff(provider))
    expected_generation = 5*peak + 4*part + 15*off
    assert b.import_energy_charge_by_component["cca_generation"] == pytest.approx(expected_generation)
    assert b.import_energy_charge_by_component["pge_delivery"] == pytest.approx(24*.29449)
    assert b.import_energy_charge_by_component["pcia"] == pytest.approx(24*.03600)
    assert b.import_energy_charge_by_component["franchise_fee"] == pytest.approx(24*.00057)
    assert b.total_utility_charge == pytest.approx(expected_generation + 24*(.29449+.03600+.00057) + .32854)
    assert sum(b.import_energy_charge_by_component.values()) == pytest.approx(b.import_energy_charge)
    assert b.demand_charge == 0


@pytest.mark.parametrize("provider,product,premium", [
    ("peninsula", "eco100", .01), ("svce", "greenprime", .0074), ("sjce", "totalgreen", .01)])
def test_product_and_phase_changes_added_once(provider, product, premium):
    base, = bill(tariff(provider))
    upgraded, = bill(tariff(provider, product, "polyphase"))
    assert upgraded.total_utility_charge-base.total_utility_charge == pytest.approx(24*premium+.82136-.32854)
    assert upgraded.import_energy_charge_by_component["cca_product_premium"] == pytest.approx(24*premium)


@pytest.mark.parametrize("vintage,adjustment", [(2018, 0), (2019, -.00046), (2020, .00046)])
def test_sjce_vintage_parity_is_signed_and_separate(vintage, adjustment):
    b, = bill(tariff("sjce", vintage=vintage))
    base, = bill(tariff("sjce", vintage=2018))
    assert b.import_energy_charge_by_component["cca_vintage_adjustment"] == pytest.approx(24*adjustment)
    assert b.total_utility_charge == pytest.approx(base.total_utility_charge)


@pytest.mark.parametrize("provider", ["peninsula", "svce"])
def test_negative_pcia_stays_a_credit(provider):
    b, = bill(tariff(provider, vintage=2026))
    assert b.import_energy_charge_by_component["pcia"] == pytest.approx(-24*.00990)
    assert b.import_energy_charge_by_component["franchise_fee"] == pytest.approx(24*.00090)


@pytest.mark.parametrize("provider", PROVIDERS)
def test_supported_window_is_enforced(provider):
    t = tariff(provider)
    for day in (t.effective_start, t.effective_end):
        assert bill(t, str(day))
    for day in (t.effective_start-timedelta(days=1), t.effective_end+timedelta(days=1)):
        with pytest.raises(TariffError, match="effective"):
            bill(t, str(day))


@pytest.mark.parametrize("provider,peak,superoff,off", [
    ("svce", .08353, .05131, .06757), ("sjce", .08093, .04936, .06529)])
def test_winter_boundaries_weekends_and_summer_change(provider, peak, superoff, off):
    t = tariff(provider)
    stamps = pd.DatetimeIndex(["2026-05-31 08:45", "2026-05-31 09:00", "2026-05-31 13:45",
        "2026-05-31 14:00", "2026-05-31 16:00", "2026-05-31 21:00", "2026-06-01 16:00"], tz="America/Los_Angeles")
    fees = .03600+.00057
    assert t.energy_rates(stamps).tolist() == pytest.approx([
        r+.27432+fees for r in (off, superoff, superoff, off, peak, off)] +
        [PROVIDERS[provider].generation[0]+.29449+fees])


def test_sjce_dst_day_customer_charge_counts_one_service_date():
    b, = bill(tariff("sjce"), "2026-03-08", 23)
    assert b.import_energy_kWh == 23
    assert b.customer_charge == .32854
    assert b.billing_days == 1


@pytest.mark.parametrize("provider,alias", [("peninsula", "cec:other:19"), ("svce", "cec:other:29"), ("sjce", "cec:other:27")])
def test_provider_pairing_requires_explicit_confirmation(provider, alias):
    req = deepcopy(DEFAULT_SITE_REQUEST)
    req["tariff_id"] = tariff(provider).tariff_id
    for selection in (provider, alias):
        req["site"]["utility"] = selection
        validate_request(req)
    for selection in ("pge", "unconfirmed", "other", "cleanpowersf", "hetch_hetchy",
                      *(p for p in PROVIDERS if p != provider)):
        req["site"]["utility"] = selection
        with pytest.raises(ValueError, match="Confirm"):
            validate_request(req)
    assert canonical_service(alias) == provider


def test_every_registered_choice_reaches_both_interfaces():
    from src.local_web.worker import capabilities
    from src.simulation.application_interface import TARIFF_LABELS
    caps = capabilities()
    choices = {t["id"]: t for t in caps["tariffs"]}
    assert caps["services"] == SERVICES
    assert len(BAY_AREA_CCA_TARIFFS) == 156
    for t in BAY_AREA_CCA_TARIFFS:
        assert get_tariff(t.tariff_id) == t
        assert TARIFF_LABELS[t.tariff_id] == t.name
        assert choices[t.tariff_id]["service"] == tariff_service(t.tariff_id)
        assert choices[t.tariff_id]["notes"] == t.notes
        assert choices[t.tariff_id]["effective_end"] == "2026-09-16"


@pytest.mark.parametrize("kwargs", [dict(provider="unknown"), dict(phase="primary"),
    dict(product="green"), dict(vintage=True), dict(vintage=2027), dict(provider="sjce", vintage=2021)])
def test_unverified_choices_rejected(kwargs):
    options = dict(provider="peninsula", phase="single_phase", product="ecoplus", vintage=2018)
    options.update(kwargs)
    with pytest.raises(ValueError):
        build_b1(**options)
