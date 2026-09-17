"""CleanPowerSF standard B-1 combined import tariffs; verified 2026-09-16.

Non-exempt commercial accounts only. Rates are a reviewed snapshot, never
fetched during simulation. The cutoff is a verification bound, not a claim
that any provider's rates expire then. See docs/CleanPowerSF.md.
"""
from dataclasses import replace
from datetime import date
from .pge_commercial import (PGE_B1_SECONDARY_SINGLE_PHASE_BUNDLED,
                             PGE_B1_SECONDARY_POLYPHASE_BUNDLED, B1_SOURCE_URL)
from .tariffs import ServiceType, register_tariff

GENERATION_SOURCE = "https://cleanpowersf.org/commercial-rate-tables"
from .pge_cca import PCIA, FFS, FFS_SOURCE, PGE_GENERATION, BUNDLED_PCIA, b1_components

GREEN = (.16197, .11958, .11958, .10166, .11440, .08638, .10052)
VERIFIED_THROUGH = date(2026, 9, 16)


def build_b1(*, phase, product, vintage):
    """Require explicit account choices; never infer vintage from location."""
    if phase not in ("single_phase", "polyphase") or product not in ("green", "supergreen") or vintage not in PCIA:
        raise ValueError("Choose a supported B-1 phase, CleanPowerSF product and PCIA vintage.")
    base, delivery_components = b1_components(phase=phase, vintage=vintage)
    generation = tuple(r + (.005 if product == "supergreen" else 0) for r in GREEN)
    components = (("cleanpowersf_generation", generation), *delivery_components)
    return replace(base,
        tariff_id=f"cleanpowersf_b1_{phase}_{product}_v{vintage}_2026_03_01",
        name=f"CleanPowerSF {'SuperGreen' if product == 'supergreen' else 'Green'} + PG&E B-1 ({phase.replace('_', ' ')}, PCIA {vintage})",
        utility="CleanPowerSF / Pacific Gas and Electric", service_type=ServiceType.CCA,
        effective_end=VERIFIED_THROUGH,
        tou_periods=tuple(replace(period, rate_per_kWh=round(sum(rates[i] for _, rates in components), 8))
                          for i, period in enumerate(base.tou_periods)),
        energy_components=components,
        source_url=GENERATION_SOURCE,
        version="2026-03-01_verified-2026-09-16",
        notes=(f"Standard B-1, {product}, PCIA vintage {vintage}; non-exempt commercial account. "
               "Confirm phase and the PCIA vintage printed on your bill; vintage is not the study year. "
               "Includes CleanPowerSF generation, PG&E delivery, vintage PCIA and franchise fee; "
               "customer charge is added once. Verified coverage March 1–September 16, 2026. "
               "Excludes taxes, special exemptions/discounts, standby charges and NEM/NBT export settlements. "
               "B1-ST is not included. B-1 eligibility requires account demand history. "
               f"Sources: {GENERATION_SOURCE}; {B1_SOURCE_URL}; {FFS_SOURCE}"))


CLEANPOWERSF_TARIFFS = tuple(register_tariff(build_b1(phase=phase, product=product, vintage=vintage))
    for phase in ("single_phase", "polyphase")
    for product in ("green", "supergreen") for vintage in PCIA)
