"""Shared provider identities and verified CEC territory aliases.

CEC Other layer OBJECTIDs checked 2026-09-17; they suggest service only.
"""
SERVICES = (
    {"id": "pge", "label": "PG&E bundled service", "aliases": ()},
    {"id": "cleanpowersf", "label": "CleanPowerSF + PG&E delivery", "aliases": ("cec:other:12",)},
    {"id": "hetch_hetchy", "label": "Hetch Hetchy Power", "aliases": ("cec:distribution:52",)},
    {"id": "peninsula", "label": "WestLight Energy / Peninsula Clean Energy + PG&E delivery", "aliases": ("cec:other:19",)},
    {"id": "svce", "label": "Silicon Valley Clean Energy + PG&E delivery", "aliases": ("cec:other:29",)},
    {"id": "sjce", "label": "San José Clean Energy + PG&E delivery", "aliases": ("cec:other:27",)},
)


def canonical_service(selection):
    return next((s["id"] for s in SERVICES if selection in (s["id"], *s["aliases"])), selection)


def tariff_service(tariff_id):
    return next((s["id"] for s in SERVICES if tariff_id.startswith(s["id"] + "_")), None)


def validate_service_pairing(tariff_id, selection):
    service = tariff_service(tariff_id)
    if service is None or canonical_service(selection) != service:
        label = next((s["label"] for s in SERVICES if s["id"] == service), "a supported electricity service")
        raise ValueError(f"Confirm {label} for this tariff; actual account eligibility is required.")
