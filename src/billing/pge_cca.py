"""Verified PG&E standard B-1 CCA delivery components (March 2026 snapshot)."""
from .pge_commercial import (PGE_B1_SECONDARY_SINGLE_PHASE_BUNDLED,
                             PGE_B1_SECONDARY_POLYPHASE_BUNDLED)

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
PGE_GENERATION = (.18628, .13705, .13705, .11624, .13103, .09849, .11491)
BUNDLED_PCIA = -.00990


def b1_components(*, phase, vintage):
    """Delivery, PCIA and FFS only; provider generation is added separately."""
    if phase not in ("single_phase", "polyphase") or type(vintage) is not int or vintage not in PCIA:
        raise ValueError("Choose a supported B-1 phase and explicit PCIA vintage.")
    base = (PGE_B1_SECONDARY_SINGLE_PHASE_BUNDLED if phase == "single_phase"
            else PGE_B1_SECONDARY_POLYPHASE_BUNDLED)
    delivery = tuple(round(period.rate_per_kWh - gen - BUNDLED_PCIA, 8)
                     for period, gen in zip(base.tou_periods, PGE_GENERATION))
    return base, (("pge_delivery", delivery),
                  ("pcia", (PCIA[vintage],) * 7),
                  ("franchise_fee", (FFS[vintage],) * 7))
