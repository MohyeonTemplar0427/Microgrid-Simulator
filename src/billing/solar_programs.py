"""Source-backed solar-program inventory, separate from executable billing.

Identification is not eligibility.  A provider's import tariff, export rate,
credit restrictions, and true-up must all be verified before a program can be
offered as a simulation.  In particular, CCA generation is never PG&E or SCE
bundled generation merely because the same utility delivers the electricity.
"""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SolarProgram:
    id: str
    delivery_utility: str
    generation_provider: str
    label: str
    family: str
    source: str
    simulation_status: str = "research_only"
    scope: str = "Provider rules and dated rates must be implemented before billing or dispatch."

    def public(self):
        return asdict(self)


PROGRAMS = (
    SolarProgram("pge_nbt_monthly", "pge", "pge", "Solar Billing Plan (NBT)", "net_billing",
                 "https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_NBT.pdf",
                 "bounded_monthly", "Bundled residential E-ELEC, one confirmed cycle June 1–September 21, 2026; no annual interval settlement."),
    SolarProgram("cleanpowersf_nem", "pge", "cleanpowersf", "CleanPowerSF NEM", "cca_net_metering",
                 "https://cleanpowersf.org/residential-rooftop-solar"),
    SolarProgram("peninsula_sbp", "pge", "peninsula", "WestLight / Peninsula solar billing", "cca_net_billing",
                 "https://www.peninsulacleanenergy.com/wp-content/uploads/2023/01/10-26-2023-BOD-Agenda-Packet.pdf"),
    SolarProgram("svce_sbp", "pge", "svce", "SVCE Solar Billing Plan", "cca_net_billing",
                 "https://www.svcleanenergy.org/solar-billing-plan/"),
    SolarProgram("sjce_sbp", "pge", "sjce", "SJCE Solar Billing Plan", "cca_net_billing",
                 "https://sanjosecleanenergy.org/solar-billing-nem/"),
    SolarProgram("ava_sbp", "pge", "ava", "Ava Solar Billing Plan", "cca_net_billing",
                 "https://avaenergy.org/your-energy-options/plans-and-rates/rates/solar-billing-plan/"),
    SolarProgram("mce_sbp", "pge", "mce", "MCE Solar Billing Plan", "cca_net_billing",
                 "https://mcecleanenergy.org/solar-billing-plan/"),
    SolarProgram("sonoma_sbp", "pge", "sonoma", "Sonoma Clean Power Solar Billing Plan", "cca_net_billing",
                 "https://sonomacleanpower.org/solar-billing-plan"),
    SolarProgram("hetch_hetchy_nem", "hetch_hetchy", "hetch_hetchy", "Hetch Hetchy NEM", "municipal_net_metering",
                 "https://www.sfpuc.gov/interconnection-and-net-energy-metering-requests"),
    SolarProgram("amp_erg", "amp", "amp", "AMP Eligible Renewable Generation", "municipal_avoided_cost",
                 "https://www.alamedamp.com/195/Solar-Compensation-Billing"),
    SolarProgram("amp_legacy_nem", "amp", "amp", "AMP grandfathered NEM", "municipal_net_metering",
                 "https://www.alamedamp.com/195/Solar-Compensation-Billing"),
    SolarProgram("svp_nm", "svp", "svp", "SVP net metering", "municipal_net_metering",
                 "https://www.siliconvalleypower.com/sustainability/solar/understanding-your-bill"),
    SolarProgram("palo_alto_nem", "palo_alto", "palo_alto", "Palo Alto NEM", "municipal_net_metering",
                 "https://www.paloalto.gov/Departments/Utilities/Electrification/Electrify-My-Home/Consider-Solar/Net-Energy-Metering"),
    SolarProgram("healdsburg_nem", "healdsburg", "healdsburg", "Healdsburg solar metering", "municipal_net_metering",
                 "https://www.ci.healdsburg.ca.us/235/Solar-Energy-Storage"),
    SolarProgram("sce_nbt", "sce", "sce", "SCE Solar Billing Plan (NBT)", "net_billing",
                 "https://www.sce.com/customer-service-center/help-center/solar/solar-billing-plan/understanding-export-pricing"),
    SolarProgram("sce_legacy_nem", "sce", "sce", "SCE legacy NEM", "net_metering",
                 "https://www.sce.com/save-money/rates-financing/solar-billing-plan"),
    SolarProgram("cpa_nbt", "sce", "cpa", "Clean Power Alliance Solar Billing Plan", "cca_net_billing",
                 "https://files.cleanpoweralliance.org/uploads/2026/03/CPA-Net-Billing-Tariff-2026-02-05.pdf"),
    SolarProgram("cpa_nem", "sce", "cpa", "Clean Power Alliance NEM", "cca_net_metering",
                 "https://cleanpoweralliance.org/residential-rate/"),
    SolarProgram("ocpa_solar", "sce", "ocpa", "Orange County Power Authority solar NEM", "cca_net_metering",
                 "https://www.ocpower.org/energy-programs/solar-net-energy-metering/"),
    SolarProgram("ladwp_nem", "ladwp", "ladwp", "LADWP NEM", "municipal_net_metering",
                 "https://www.ladwp.com/account/customer-service/electric-rates/residential-rates"),
    SolarProgram("bwp_net_billing", "bwp", "bwp", "BWP solar net billing", "municipal_net_billing",
                 "https://www.burbankwaterandpower.com/solar-net-billing"),
    SolarProgram("bwp_legacy_nem", "bwp", "bwp", "BWP grandfathered NEM", "municipal_net_metering",
                 "https://www.burbankwaterandpower.com/solar-net-billing"),
    SolarProgram("gwp_nem", "gwp", "gwp", "Glendale NEM", "municipal_net_metering",
                 "https://www.glendaleca.gov/government/departments/glendale-water-and-power/solar-education/guide-for-applying-for-interconnection"),
    SolarProgram("pwp_nem", "pwp", "pwp", "Pasadena NEM", "municipal_net_metering",
                 "https://pwp.cityofpasadena.net/netsurpluscompensation/"),
    SolarProgram("alw_ngp", "alw", "alw", "Azusa net generator payment", "municipal_net_metering",
                 "https://www.azusaca.gov/1061/Schedule-NGP"),
    SolarProgram("ipu_nem", "ipu", "ipu", "Industry NEM 1.0", "municipal_net_metering",
                 "https://cityofindustry.org/191/Electric"),
    SolarProgram("ipu_erg", "ipu", "ipu", "Industry eligible renewable generation", "municipal_avoided_cost",
                 "https://cityofindustry.org/191/Electric"),
)


def programs_for(delivery_utility, generation_provider):
    """Return program candidates for a *confirmed* account pairing only."""
    return tuple(program for program in PROGRAMS
                 if program.delivery_utility == delivery_utility
                 and program.generation_provider == generation_provider)
