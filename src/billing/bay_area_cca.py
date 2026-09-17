"""Reviewed Peninsula and South Bay B-1 import tariffs; no live rate inference."""
from dataclasses import dataclass, replace
from datetime import date

from .pge_cca import PCIA, FFS, FFS_SOURCE, b1_components
from .pge_commercial import B1_SOURCE_URL
from .tariffs import ServiceType, register_tariff

VERIFIED_THROUGH = date(2026, 9, 16)  # Preserve the shared PG&E snapshot boundary.


@dataclass(frozen=True)
class Provider:
    name: str
    source: str
    generation_effective: date
    supported_start: date
    # Summer peak, part-peak (twice), off-peak; winter peak, super-off, off.
    generation: tuple[float, ...]
    products: tuple[tuple[str, str, float], ...]
    vintages: tuple[int, ...]
    notes: str = ""


PROVIDERS = {
    "peninsula": Provider(
        "WestLight Energy (Peninsula Clean Energy)",
        "https://www.westlightenergy.org/wp-content/uploads/2026/07/Commercial-WestLight-Energy-Rates-Effective-July-1-2026.pdf",
        date(2026, 7, 1), date(2026, 7, 1),
        (.13091, .08414, .08414, .06437, .07842, .04751, .06311),
        (("ecoplus", "ECOplus", 0.0), ("eco100", "ECO100", .01)), tuple(PCIA),
        "The source's comparison column assumes vintage 2016; this study uses your explicit vintage. "),
    "svce": Provider(
        "Silicon Valley Clean Energy",
        "https://www.svcleanenergy.org/wp-content/uploads/SVCE-Commercial-Rate-Sheet-January-1-2026.pdf",
        date(2026, 1, 1), date(2026, 4, 6),
        (.13823, .08949, .08949, .06889, .08353, .05131, .06757),
        (("greenstart", "GreenStart", 0.0), ("greenprime", "GreenPrime", .0074)), tuple(PCIA),
        "Coverage starts April 6 to exclude the source's spring daylight-saving adjustment window; "
        "that generation timing rule is not yet implemented. "),
    "sjce": Provider(
        "San José Clean Energy",
        "https://sanjosecleanenergy.org/wp-content/uploads/2026/06/SJCE-Commercial-Rates-March-1-2026-1.pdf",
        date(2026, 3, 1), date(2026, 3, 1),
        (.13452, .08677, .08677, .06658, .08093, .04936, .06529),
        (("greensource", "GreenSource", 0.0), ("totalgreen", "TotalGreen", .01)), (2018, 2019, 2020),
        "The separate SJCE vintage adjustment puts the documented 2019/2020 vintages at "
        "2018 PCIA/FFS parity. Other vintages and SJ Cares are not modeled. "),
}


def build_b1(*, provider, phase, product, vintage):
    if provider not in PROVIDERS:
        raise ValueError("Choose a supported Peninsula or South Bay provider.")
    spec = PROVIDERS[provider]
    products = {key: (label, premium) for key, label, premium in spec.products}
    if product not in products or type(vintage) is not int or vintage not in spec.vintages:
        raise ValueError("Choose a supported provider product and explicit PCIA vintage.")
    base, delivery = b1_components(phase=phase, vintage=vintage)
    label, premium = products[product]
    components = (("cca_generation", spec.generation),
                  ("cca_product_premium", (premium,) * 7), *delivery)
    if provider == "sjce":
        adjustment = round(PCIA[2018] + FFS[2018] - PCIA[vintage] - FFS[vintage], 8)
        components += (("cca_vintage_adjustment", (adjustment,) * 7),)
    start = spec.supported_start
    return replace(base,
        tariff_id=f"{provider}_b1_{phase}_{product}_v{vintage}_{start:%Y_%m_%d}",
        name=f"{spec.name} {label} + PG&E B-1 ({phase.replace('_', ' ')}, PCIA {vintage})",
        utility=f"{spec.name} / Pacific Gas and Electric", service_type=ServiceType.CCA,
        effective_start=start, effective_end=VERIFIED_THROUGH,
        version=f"generation-{spec.generation_effective}_pge-2026-03-01_verified-2026-09-16",
        source_url=spec.source, energy_components=components,
        tou_periods=tuple(replace(period, rate_per_kWh=round(sum(rates[i] for _, rates in components), 8))
                          for i, period in enumerate(base.tou_periods)),
        notes=(f"{spec.name} {label}: standard B-1 secondary-voltage, {phase.replace('_', ' ')}, "
               f"PCIA vintage {vintage}. Confirm actual provider enrollment, phase, vintage and B-1 "
               "account eligibility from your bill; territory matching does not establish eligibility. "
               "Generation, product premium, PG&E delivery, PCIA and franchise fee are itemized; "
               "the customer charge is added once. Standard B-1 has no demand charge. "
               f"Supported service dates {start} through {VERIFIED_THROUGH}; the end is a verification "
               "cutoff, not a filed expiration. " + spec.notes +
               "Excludes taxes, CARE and other discounts/exemptions, primary-voltage rates, B1-ST, "
               "standby charges and NEM/NBT/export settlements. Product choice does not change "
               "the study's carbon signal. "
               f"Sources: {spec.source}; {B1_SOURCE_URL}; {FFS_SOURCE}"))


BAY_AREA_CCA_TARIFFS = tuple(register_tariff(build_b1(
    provider=provider, phase=phase, product=product, vintage=vintage))
    for provider, spec in PROVIDERS.items()
    for phase in ("single_phase", "polyphase")
    for product, _, _ in spec.products for vintage in spec.vintages)
