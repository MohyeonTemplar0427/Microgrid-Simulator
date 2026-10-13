"""Filed residential ComEd composite rates; all money is USD, not cents.

Coverage is by utility BILLING MONTH, not the filing date on each sheet.
See docs/ComEd_Residential_Billing.md and the retained source manifest.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal as D
from types import MappingProxyType

from .plans import RatePlan, RatePlanIdentity

RATEBOOK_URL = (
    "https://www.comed.com/cdn/assets/v3/assets/blt3ebb3fed6084be2a/"
    "blt86ebee5fe6ed02f8/6ab16afb15d5b73190b00e59/2026_Ratebook.pdf?branch=prod_alias"
)
RATEBOOK_SHA256 = "0e3f2ee2fcd2658e41312bc50afbda08a5830f8efaf761430c83e09abff65de1"


@dataclass(frozen=True)
class DeliveryRates:
    customer: D
    meter: D
    distribution: D
    iedt: D
    revenue_balancing_factor: D


# Informational sheets 64.1 (PDF p848) and 18 (p799).
DELIVERY = MappingProxyType({
    "single_family_non_electric_heat": DeliveryRates(D("13.26"), D("3.52"), D(".05698"), D(".00124"), D(".007668")),
    "multi_family_non_electric_heat": DeliveryRates(D("9.76"), D("3.52"), D(".04354"), D(".00124"), D(".011682")),
    "single_family_electric_heat": DeliveryRates(D("15.09"), D("3.52"), D(".02712"), D(".00124"), D(".069810")),
    "multi_family_electric_heat": DeliveryRates(D("10.57"), D("3.52"), D(".02576"), D(".00124"), D(".064486")),
})

# Valid throughout the composite Sep/Oct 2026 window. Explicitly re-verify
# these factors before adding a version outside that window.
IDUF = D("1.0217")       # sheet 20, p801
DRAF = D(".006785")      # sheet 9, p790: 0.6785%, not 0.6785
EDAF = D("0")            # sheet 62, p845
TPAF = D(".06551")       # sheet 65, p866: 6.551%
DGRA = D(".00062")       # sheet 56, p839
RCA = D(".91")           # .05 + .80 + .06: pp394, 396, 824; CB/POR zero p803
LID_RECOVERY = D("1.35")  # sheet 74, p876 (not the means-tested discount)
CAPACITY = D("10.10121") # sheet 4, p785; already includes uncollectible factors
# BESH uses SYSTEM AVERAGE factors, including system-average distribution loss.
HEC_MULTIPLIER = D("1.0124") * D(".9968") * D("1.0406")  # pp60, 801, 802, 814
COMMON_ENERGY = MappingProxyType({
    "environmental_cost_recovery": (D(".00007"), 789),
    "renewable_portfolio_standard": (D(".00516"), 817),
    "zero_emission_standard": (D(".00069"), 820),
    "energy_efficiency_programs": (D(".00369"), 821),
    "energy_transition_assistance": (D(".00084"), 822),
})


@dataclass(frozen=True)
class ComEdVersion:
    tariff_id: str
    effective_start: date
    effective_end: date
    bes_energy: D
    bes_transmission: D
    bes_adjustment: D
    besh_transmission: D
    besh_procurement: D
    besh_adjustment: D
    carbon_free_adjustment: D
    coal_to_solar: D

    def is_effective_on(self, day: date) -> bool:
        return self.effective_start <= day <= self.effective_end


# Supply: sheets 1..7 (pp782..788); CFRA sheet36.1 (p818); CTS sheet63 (p846).
VERSIONS = (
    ComEdVersion("comed_residential_2026_09", date(2026, 9, 1), date(2026, 9, 30),
                 D(".08678"), D(".01723"), D("-.00087"), D(".01073"),
                 D(".00134"), D(".00385"), D("-.01628"), D(".00009")),
    ComEdVersion("comed_residential_2026_10", date(2026, 10, 1), date(2026, 10, 31),
                 D(".08413"), D(".01690"), D("-.01551"), D(".01075"),
                 D(".00226"), D("-.02296"), D("-.00115"), D(".00008")),
)


def build_comed_residential_plans() -> tuple[RatePlan[ComEdVersion], ...]:
    """Eight account choices; use version_on with the confirmed billing month.

    Kept separate from the generic service-date tariff registry: neither raw
    LMP nor monthly ComEd adjustments fit a generic flat energy tariff.
    """
    return tuple(
        RatePlan(RatePlanIdentity("ComEd", supply, "bundled", "residential", delivery), VERSIONS)
        for supply in ("BES", "BESH") for delivery in DELIVERY
    )
