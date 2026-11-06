"""Reviewed complete calendar bill intersections of Virginia Tariff 28.

The source ledger distinguishes accepted sheets, the official illustrative
checks, and the dated reconstructions from surviving superseded sheets.
"""
from calendar import monthrange
from datetime import date

ROOT = "https://www.appalachianpower.com/lib/docs/"
VA = ROOT + "ratesandtariffs/Virginia/"
BOOK_JAN_2025 = ROOT + "cleanenergy/electric-cars/APCoStandardTariff28-January12025SUTUpdate.pdf"
BOOK_NOV_2025 = VA + "Tariff28Nov1-2025-G-RACFuelWWSUpdate.pdf"
BOOK_MAR_2026 = VA + "Tariff_28_March_15-2026-TRACUpdate.pdf"
BOOK_OLD_PIPP = VA + "Tariff28March-1-2026-DR-RAC-E-RAC-VCEA-Update.pdf"
BOOK_NOV_2026 = VA + "Tariff_28_November_1_2026_Update-PIPP.pdf"
SBRR_FILED = VA + "Tariff_28_May-27-2026_Update-Securitization.pdf"
JAN_2025_CHECK = VA + "SelectResidentialandNon-ResidentialCharges-January_1_2025.pdf"
NOV_2025_CHECK = VA + "SelectResidentialandNon-ResidentialCharges-Nov1-2025.pdf"
JAN_2026_CHECK = VA + "SelectResidentialandNon-ResidentialCharges-January-1-2026.pdf"
NOV_2026_CHECK = VA + "Select_Residential_and_Non-Residential_Charges-Nov_1_2026.pdf"
HISTORIC_CONSUMPTION_TAX = (
    "https://www.dominionenergy.com/-/media/content/rates-and-tariffs/pdfs/virginia/shared/consumption-tax.pdf",
    "https://salemva.gov/DocumentCenter/View/2607/Special-Regulatory-Tax-State-PDF",
)
RATE_SOURCES = [BOOK_JAN_2025, BOOK_NOV_2025, BOOK_NOV_2026, SBRR_FILED, JAN_2025_CHECK, NOV_2025_CHECK,
                JAN_2026_CHECK, NOV_2026_CHECK]

CURRENT_REGULATORY_TAX = (.000165, .000165, .000165)


def _schedule(customer, *, generation, delivery, transmission, environmental, generation_rac,
              broadband, pcap, renewables, fuel, sales_use_tax, renewable_compliance,
              demand_response, pipp, securitized_cost, generation_credit_factor=0.):
    return dict(customer=customer, trr_credit=0., per_kwh=dict(
        supply_generation=generation, distribution_energy=delivery, transmission_rac=transmission,
        environmental_rac=environmental, generation_rac=generation_rac, broadband_rac=broadband,
        renewable_capacity_pcap=pcap, renewable_capacity_energy=renewables, fuel_factor=fuel,
        sales_use_tax_rider=sales_use_tax, renewable_compliance=renewable_compliance,
        energy_efficiency_rac=.00237, demand_response_rac=demand_response, pipp_recovery=pipp,
        securitized_asset_cost=securitized_cost,
        securitization_base_generation_credit=generation_credit_factor*generation,
    ))


def _earlier(*, fuel, sales_use_tax, rs_grac, sgs_grac):
    common = dict(fuel=fuel, sales_use_tax=sales_use_tax, renewable_compliance=.00103,
                  demand_response=0., pipp=.00132, securitized_cost=0.)
    return {
        "015": _schedule(7.96, generation=.03794, delivery=.03828, transmission=.03646,
                         environmental=.00284, generation_rac=rs_grac, broadband=.00059,
                         pcap=.00013, renewables=.00011, **common),
        "231": _schedule(9.88, generation=.03420, delivery=.03026, transmission=.02819,
                         environmental=.00248, generation_rac=sgs_grac, broadband=.00054,
                         pcap=.00012, renewables=.00010, **common),
    }


def _securitized(pipp):
    common = dict(fuel=.03133, sales_use_tax=.00014, renewable_compliance=.00324,
                  pipp=pipp, generation_credit_factor=-.3924)
    return {
        "015": _schedule(7.96, generation=.03794, delivery=.03828, transmission=.03804,
                         environmental=.00370, generation_rac=.00320, broadband=.00211,
                         pcap=.00047, renewables=.00192, demand_response=.00013,
                         securitized_cost=.01259, **common),
        "231": _schedule(9.88, generation=.03420, delivery=.03026, transmission=.02942,
                         environmental=.00354, generation_rac=.00247, broadband=.00164,
                         pcap=.00037, renewables=.00148, demand_response=.00011,
                         securitized_cost=.01006, **common),
    }


RATES = {
    "2025-01-01": dict(
        source_version="tariff28-2025-01", source_grade="filed_book_and_corrected_official_summary",
        sources=(BOOK_JAN_2025, JAN_2025_CHECK, *HISTORIC_CONSUMPTION_TAX),
        regulatory_tax=(.000165, .000110, .000077),
        plans=_earlier(fuel=.04139, sales_use_tax=.00032, rs_grac=.00321, sgs_grac=.00266),
    ),
    "2025-11-01": dict(
        source_version="tariff28-2025-11", source_grade="filed_sheets_and_cached_official_summary",
        sources=(BOOK_JAN_2025, BOOK_NOV_2025, BOOK_MAR_2026, NOV_2025_CHECK),
        regulatory_tax=CURRENT_REGULATORY_TAX,
        plans=_earlier(fuel=.03133, sales_use_tax=.00032, rs_grac=.00320, sgs_grac=.00247),
    ),
    "2026-01-01": dict(
        source_version="tariff28-2026-01", source_grade="filed_sheets_and_cached_official_summary",
        sources=(BOOK_JAN_2025, BOOK_NOV_2025, BOOK_NOV_2026, JAN_2026_CHECK),
        regulatory_tax=CURRENT_REGULATORY_TAX,
        plans=_earlier(fuel=.03133, sales_use_tax=.00014, rs_grac=.00320, sgs_grac=.00247),
    ),
    "2026-10-01": dict(
        source_version="tariff28-2026-10", source_grade="dated_filed_sheet_reconstruction",
        sources=(BOOK_NOV_2026, BOOK_OLD_PIPP, SBRR_FILED),
        regulatory_tax=CURRENT_REGULATORY_TAX,
        plans=_securitized(.00132),
    ),
    "2026-11-01": dict(
        source_version="tariff28-2026-11", source_grade="filed_book_and_official_summary",
        sources=(BOOK_NOV_2026, SBRR_FILED, NOV_2026_CHECK),
        regulatory_tax=CURRENT_REGULATORY_TAX,
        plans=_securitized(.00082),
    ),
}
COVERAGE = tuple((month, date.fromisoformat(month).replace(
    day=monthrange(int(month[:4]), int(month[5:7]))[1]).isoformat()) for month in RATES)


def rates_for_month(month):
    try:
        return RATES[month]
    except KeyError:
        raise ValueError(f"Appalachian Power tariff components are unverified for {month[:7]}. "
                         "Select a supported complete calendar cycle.") from None
