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
FFS_SOURCE = "https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_E-FFS.pdf"
# B-1 sheet 6, effective January 1, 2026. A negative PCIA is a credit.
PCIA = dict(zip(range(2009, 2027), (
    .02910, .03294, .03417, .03597, .03628, .03607, .03602,
    .03608, .03582, .03600, .03646, .03554, .05151, .05159,
    .05265, .04957, -.00990, -.00990)))
# E-FFS sheets 2-4, Small L&P, effective January 1, 2026.
FFS = dict(zip(range(2009, 2027), (
    .00062, .00059, .00058, .00057, .00057, .00057, .00057,
    .00057, .00057, .00057, .00057, .00057, .00046, .00046,
    .00045, .00047, .00090, .00090)))
# Ordered to match standard B-1's seven TOU blocks (part-peak occurs twice).
GREEN = (.16197, .11958, .11958, .10166, .11440, .08638, .10052)
PGE_GENERATION = (.18628, .13705, .13705, .11624, .13103, .09849, .11491)
BUNDLED_PCIA = -.00990
VERIFIED_THROUGH = date(2026, 9, 16)


def build_b1(*, phase, product, vintage):
    """Require explicit account choices; never infer vintage from location."""
    if phase not in ("single_phase", "polyphase") or product not in ("green", "supergreen") or vintage not in PCIA:
        raise ValueError("Choose a supported B-1 phase, CleanPowerSF product and PCIA vintage.")
    base = (PGE_B1_SECONDARY_SINGLE_PHASE_BUNDLED if phase == "single_phase"
            else PGE_B1_SECONDARY_POLYPHASE_BUNDLED)
    generation = tuple(r + (.005 if product == "supergreen" else 0) for r in GREEN)
    delivery = tuple(round(period.rate_per_kWh - gen - BUNDLED_PCIA, 8)
                     for period, gen in zip(base.tou_periods, PGE_GENERATION))
    components = (("cleanpowersf_generation", generation),
                  ("pge_delivery", delivery),
                  ("pcia", (PCIA[vintage],) * 7),
                  ("franchise_fee", (FFS[vintage],) * 7))
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
