"""Verified complete Duke Energy Ohio electric rate intersections.

Rate rows are keyed by the designated revenue month for the supported
calendar cycle. Sheet 25.8 generally keys revisions to the final meter read.
The source ledger records each sheet's own applicability and effective date.
"""
from calendar import monthrange
from datetime import date

PUCO_TARIFF_ROOT = (
    "https://dam.assets.ohio.gov/image/upload/puco.ohio.gov/empliibrary/files/"
    "docketing/tariffs/Electric/Duke%20Energy%20Ohio%20-%20Electric/"
)
BOOK_2025 = PUCO_TARIFF_ROOT + "PUCO19%20Schedules%20of%20Rates,%20Classifications,%20Rules%20andRegulations.pdf"
BOOK_2026 = PUCO_TARIFF_ROOT + "PUCO%2019%20Schedules%20of%20Rates,%20Classifications,%20Rules%20and%20Regulations%20(1).pdf"
DCI_2026 = "https://www.duke-energy.com/-/media/pdfs/for-your-home/rates/electric-oh/sheet-no-103-oh-e-rider-dci.pdf"
PLANS = ("RS", "DM")
EXCISE_RATES = (.00465, .00419, .00363)
EXCISE_BREAKS = (2000., 15000.)
DISTRIBUTION = {
    "RS": (8., (.039693,)),
    "DM": (12., (.048863, .004339)),
}
DISTRIBUTION_BREAK = 2800.
CAPACITY_BREAK = 6000.
RS_WINTER_SUPPLY_BREAK = 1000.

JUNE_2025 = {
    "sources": (BOOK_2025,),
    "source_version": "PUCO19-2025-06-10",
    "distribution_fractions": {
        "distribution_tax_cut_credit": -.0327, "service_reliability": .0169,
        "distribution_capital": .17712, "economic_competitiveness": .0012,
    },
    "per_kwh": {"alternative_energy": .000573, "supplier_reconciliation": -.004506,
                "energy_efficiency_recovery": 0.},
    "universal_service_line": "universal_service",
    "universal_service": .0011015,
    "plans": {
        "RS": {
            "per_bill": {"power_future": 1.40, "solar_generation_fund": .10,
                         "distribution_storm": -.08, "legacy_generation_a": 1.18,
                         "legacy_generation_b": -.01},
            "per_kwh": {"base_transmission": .015510, "transmission_rtep_credit": -.000649,
                        "distribution_uncollectible": .001869, "distribution_decoupling": .002453,
                        "demand_side_management": 0.},
            "generation_uncollectible": .002146,
            "capacity": (.028584,),
            "energy": (.079799,),
        },
        "DM": {
            "per_bill": {"power_future": 8.24, "distribution_storm": -.09,
                         "distribution_uncollectible": 1.46},
            "per_kwh": {"base_transmission": .011780, "transmission_rtep_credit": -.000470,
                        "solar_generation_fund": .00029051, "distribution_decoupling": .003162,
                        "legacy_generation_a": .0018637, "legacy_generation_b": -.0000706},
            "generation_uncollectible": 1.66,
            "capacity": (.023240, .003542),
            "energy": (.090242, .031574, .008740),
        },
    },
}

OCTOBER_2026 = {
    "sources": (BOOK_2026, DCI_2026, BOOK_2025),
    "source_version": "PUCO19-2026-10-01+103.46",
    "distribution_fractions": {
        "distribution_tax_cut_credit": -.0275, "service_reliability": .0244,
        "distribution_capital": .18624, "economic_competitiveness": .0096,
    },
    "per_kwh": {"alternative_energy": .000177, "supplier_reconciliation": -.009808,
                "energy_efficiency_recovery": 0.},
    "universal_service_line": "pipp_recovery",
    "universal_service": .0024282,
    "plans": {
        "RS": {
            "per_bill": {"power_future": .87, "solar_generation_fund": 0.,
                         "distribution_storm": .03, "legacy_generation_a": 0.,
                         "legacy_generation_b": 0.},
            "per_kwh": {"base_transmission": .013150, "transmission_rtep_credit": -.000406,
                        "distribution_uncollectible": .002205, "distribution_decoupling": .002229,
                        "demand_side_management": .000317},
            "generation_uncollectible": .000897,
            "capacity": (.033362, .018339),
            "energy": (.081218, .047724),
        },
        "DM": {
            "per_bill": {"power_future": 4.30, "distribution_storm": .04,
                         "distribution_uncollectible": 1.32},
            "per_kwh": {"base_transmission": .011623, "transmission_rtep_credit": -.000293,
                        "solar_generation_fund": 0., "distribution_decoupling": .003078,
                        "legacy_generation_a": 0., "legacy_generation_b": 0.},
            "generation_uncollectible": .24,
            "capacity": (.029300, .003618),
            "energy": (.091847, .032136, .008896),
        },
    },
}

RATES = {
    "2025-06-01": JUNE_2025,
    "2026-10-01": OCTOBER_2026,
}
COVERAGE = tuple((month, date.fromisoformat(month).replace(
    day=monthrange(int(month[:4]), int(month[5:7]))[1]).isoformat()) for month in RATES)


def rates_for_month(month):
    try:
        return RATES[month]
    except KeyError:
        raise ValueError(f"Duke Energy Ohio tariff components are unverified for {month[:7]}. "
                         "Select a supported complete calendar cycle.") from None
