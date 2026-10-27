"""Snapshot-safe Potomac Edison Maryland R/G component intersections.

Only September–October2026 is executable. Earlier known base/generation prices
cannot substitute for missing adjustment or dated transmission evidence.
"""
from datetime import date

PLANS = ("R", "G")
COVERAGE = (("2026-09-01", "2026-10-31"),)
TARIFF = "https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/maryland/tariffs/PotomacEdisonRetailTariff.pdf"
ADJUSTMENTS = "https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/maryland/tariffs/PotomacEdisonaceca.pdf"
SOURCES = [TARIFF, ADJUSTMENTS,
    "https://www.firstenergycorp.com/content/customer/customer_choice/maryland/maryland_tariffs.html",
    "https://regs.maryland.gov/us/md/exec/comar/20.50.01.04",
    "https://regs.maryland.gov/us/md/exec/comar/03.06.01.10"]


def rates_on(day, plan="R"):
    key = day.isoformat() if type(day) is date else day
    try:
        if not isinstance(key, str) or date.fromisoformat(key).isoformat() != key:
            raise ValueError
    except ValueError as exc:
        raise ValueError("Use exact ISO Potomac Edison Maryland local dates.") from exc
    if plan not in PLANS:
        raise ValueError("Select Potomac Edison Maryland R or G Type I SOS.")
    if not any(start <= key <= end for start, end in COVERAGE):
        raise ValueError("Potomac Edison executable intersections cover September–October2026 only; missing2025 adjustments, January–May2026 final supply originals and G June–August transmission are not replaced by current rates.")
    res = plan == "R"; october = key[5:7] == "10"
    return dict(customer=6. if res else 4.85,
        distribution_energy=.02287 if res else .02243,
        generation_including_admin=(.10209 if october else .10824) if res else (.15064, .06977) if october else (.13108, .06067),
        embedded_supply_administration=.004 if res else .00550,
        transmission_energy=.00396 if res else (.00440, .00214),
        energy_block_kwh=None if res else 700.,
        energy=dict(procurement_energy_cost_adjustment=(.01828 if october else .01716) if res else (-.00338 if october else .01841),
            administrative_delivery_credit=(-.00210 if october else -.00234) if res else (-.00224 if october else -.00230),
            purpa_termination_surcharge=.00806 if res else .00953,
            empower_maryland=.01376 if res else .01142,
            franchise_tax=.000620, environmental_surcharge=.000149),
        monthly={"universal_service":.32 if res else 1.84, **({"residential_rggi_credit":0.} if res else {})},
        additional_gross_receipts_tax=False,
        distribution_minimum_capacity_rate=0. if res else 1.70,
        component_month=key[:7], source=TARIFF, source_pdf_page=62 if res else 70,
        adjustment_source=ADJUSTMENTS, adjustment_pdf_page=1,
        supply_effective_basis="R leaf effectiveJune1,2026; G transmission leaf effectiveSeptember1,2026; dated generation tables selected by service month",
        credit_basis="2026 RRC sheet explicitly prints accounting '$ -' in each month, normalized to zero; G is not RRC-eligible",
        environmental_surcharge_basis="Bills rendered fromJuly1,2026; positive half-up cents in authoritative numeric bill",
        legislative_refund_basis="Published September2025/February2026 posting months outside executable September–October2026; ordinary account without other adjustments",
        coverage_basis="Matching complete calendar meter/service/billing months only; known prices outside the intersection are not executable")
