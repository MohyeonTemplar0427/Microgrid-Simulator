"""Availability checks prevent a documented program becoming a simulated rate."""

from src.billing.solar_programs import PROGRAMS, programs_for
from src.local_web.worker import capabilities


def test_catalog_keeps_cca_generation_separate_from_delivery():
    ids = [p.id for p in PROGRAMS]
    assert len(ids) == len(set(ids))
    assert all(p.source.startswith("https://") for p in PROGRAMS)
    assert {p.id for p in programs_for("pge", "ava")} == {"ava_sbp"}
    assert {p.id for p in programs_for("sce", "cpa")} == {"cpa_nbt", "cpa_nem"}
    assert {p.id for p in programs_for("sce", "ocpa")} == {"ocpa_solar"}
    assert not programs_for("pge", "cpa")
    assert not programs_for("sce", "ava")


def test_capabilities_do_not_advertise_unimplemented_export_billing():
    from src.billing.socal import PLANS as SOCAL_PLANS
    from src.billing.municipal import RATES as MUNICIPAL_RATES

    published = capabilities()["solar_export_programs"]
    assert {p["id"] for p in published} == {p.id for p in PROGRAMS}
    enabled = [p for p in published if p["simulation_status"] != "research_only"]
    assert [p["id"] for p in enabled] == ["pge_nbt_monthly"]
    assert {p["generation_provider"] for p in published if p["family"].startswith("cca_")} >= {
        "cleanpowersf", "peninsula", "svce", "sjce", "ava", "mce", "sonoma", "cpa", "ocpa"
    }
    assert {p["utility"] for p in SOCAL_PLANS.values()} | {r.utility for r in MUNICIPAL_RATES.values()} <= {
        p["delivery_utility"] for p in published
    }


def test_catalog_does_not_turn_on_unsupported_export_requests():
    from src.local_web.municipal_service import validate_arrangement
    import pytest

    arrangement = dict(delivery_utility="amp", generation_provider="amp",
                       tariff_id="amp_d1_2026_07_01", export_program="amp_erg")
    with pytest.raises(ValueError, match="not implemented"):
        validate_arrangement(arrangement, {"status": "verified", "delivery_utility": "amp"})
