"""Snapshot-safe Pepco Maryland R/GS component intersections in dollar units.

No current-rate, DC or neighboring-utility substitution. Source documents also
contain uncovered months, which are not executable merely because a base or
generation price is known. See docs/utility_sources/pepco_md.
"""
from datetime import date

PLANS = ("R", "GS")
COVERAGE = (("2025-01-01", "2025-02-28"), ("2026-07-01", "2026-10-31"))
ROOT = "https://www.pepco.com/cdn/assets/v3/assets/bltbb7c204688a1a6a8/"
CURRENT = ROOT+"blte8a580e4cc79e2c4/6abad89015d5b7d18eb100f3/9232_AND_9761_Pepco_MD_CURRENT_CLEAN_Admin_Ch_.pdf?branch=prod_alias"
CSEG_2025 = ROOT+"blt184aa0644dce17a4/67a0f1215b6934124e523dd3/Pepco_MD_CSEG_-_02012025.pdf?branch=prod_alias"
CSEG_2026 = ROOT+"blt184aa0644dce17a4/6abebe49c7c45d25867c0a5a/CSEG_MD_Pepco_-_10_2026_.pdf?branch=prod_alias"
SOURCES = [CURRENT, CSEG_2025, CSEG_2026,
    ROOT+"blt9e3743d1d4f743f9/679d1303c9ecbb3763c0d104/Pepco_MD_SOS_-_PCA_022025.pdf?branch=prod_alias",
    ROOT+"blt9e3743d1d4f743f9/6abd8ce1d4633692b4c108e9/Pepco_MD_PCA_-_102026_.pdf?branch=prod_alias",
    ROOT+"blt048e03b25e5de0cf/6abfc95f15d5b747d1b1848e/Pepco_MD_BSA_-_102026.pdf?branch=prod_alias",
    ROOT+"bltb770f5b6804c804c/6939d02c4b4e4a1bd61743cd/MD_Terms_and_Conditions_-_master_file.pdf?branch=prod_alias",
    ROOT+"blteda6ce8aea39a7c0/67c5e1da64440c13171e98ff/Pepco_MD_Admin_Credit_-_032025.pdf?branch=prod_alias",
    ROOT+"blteda6ce8aea39a7c0/6abd91df9c17130cafc66f32/Pepco_MD_Admin_Credit_-_102026_.pdf?branch=prod_alias",
    "https://regs.maryland.gov/us/md/exec/comar/03.06.01.10",
    "https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=gtg&section=11-104",
    "https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=gpu&section=7-203",
    "https://www.pepco.com/my-account/my-dashboard/rates-tariffs/maryland/current-tariffs",
]

# Each row: generation energy, supply administration, PCA, transmission,
# BSA, administrative delivery credit. Only independently recovered rows.
MONTHLY = {
    ("2025-01", "R"):(.10115,.00391,-.0017815,.01951,.003928,-.001630),
    ("2025-02", "R"):(.10115,.00589,-.0030934,.01951,-.001328,-.001090),
    ("2025-01", "GS"):(.10050,.00326,-.0154652,.01302,.005600,0.),
    ("2025-02", "GS"):(.10050,.00530,-.0162402,.01302,.005659,0.),
    ("2026-07", "R"):(.10764,.00404,.0045355,.02101,-.000852,-.001180),
    ("2026-08", "R"):(.10764,.00404,.0053515,.02101,.002386,-.001180),
    ("2026-09", "R"):(.10764,.00404,.0055633,.02007,-.007579,-.001180),
    ("2026-10", "R"):(.12266,.00415,.0054696,.02007,.004347,-.001250),
    ("2026-07", "GS"):(.10675,.00362,-.0164524,.01423,.009858,-.000690),
    ("2026-08", "GS"):(.10675,.00362,-.0176268,.01423,.009855,-.000690),
    ("2026-09", "GS"):(.10675,.00362,-.0180350,.01421,.009906,-.000690),
    ("2026-10", "GS"):(.11923,.00367,-.0179397,.01421,.009998,-.000710),
}


def distribution_versions(plan):
    """Raw filed values retained independently of consolidated net billing."""
    if plan not in PLANS:
        raise ValueError("Select Pepco Maryland R or GS Type I SOS.")
    res = plan == "R"
    ordinary = dict(customer=8.44 if res else 12.66,
        summer=.08760 if res else .08130, winter=.04328 if res else .04272)
    increased = dict(customer=8.67 if res else 13.02,
        summer=.09713 if res else .09220, winter=.05469 if res else .05447)
    offset = dict(customer=-.23 if res else -.36,
        summer=-.00953 if res else -.01090, winter=-.01141 if res else -.01175)
    return dict(ordinary=ordinary, temporary=increased, temporary_rdm=offset,
        temporary_start="2026-08-11", temporary_end="2026-08-27",
        restored_start="2026-08-28", verified_end="2026-10-31",
        clock="Identical usage-date applicability for base and RDM")


def rates_on(day, plan="R"):
    key = day.isoformat() if type(day) is date else day
    try:
        if not isinstance(key, str) or date.fromisoformat(key).isoformat() != key:
            raise ValueError
    except ValueError as exc:
        raise ValueError("Use exact ISO Pepco Maryland local dates.") from exc
    if plan not in PLANS:
        raise ValueError("Select Pepco Maryland R or GS Type I SOS.")
    if not any(start <= key <= end for start, end in COVERAGE):
        raise ValueError("Pepco verified component intersections cover January–February2025 and July–October2026 only. Missing PCA/BSA/tax evidence and the May–June2026 MES discrepancy are not replaced by current rates.")
    energy, admin, pca, transmission, bsa, credit = MONTHLY[(key[:7], plan)]
    res = plan == "R"
    current = key.startswith("2026")
    summer = 6 <= int(key[5:7]) <= 10  # Distribution's BILLING month.
    raw = distribution_versions(plan)
    rdm_customer = 0. if current else .05 if res else .03
    rdm_energy = 0. if current else (.00400 if res else .00235) if summer else (.00238 if res else .00113)
    ordinary = raw["ordinary"]
    components = dict(
        distribution_energy_net_rdm=ordinary["summer" if summer else "winter"]+rdm_energy,
        generation_energy=energy, supply_administration=admin,
        procurement_cost_adjustment=pca, transmission_service=transmission,
        bill_stabilization_adjustment=bsa, administrative_delivery_credit=credit,
        empower_maryland=(.020618 if res else .011986) if current else (.013790 if res else .008044),
        multi_year_plan_adjustment=(.00168 if res else .00123) if current else (.00020 if res else .00015),
        delivery_tax=.000620, environmental_surcharge=.000150,
        montgomery_county_surcharge=(.0113242 if res else .0202525) if current else (.0113205 if res else .0202459))
    grt_components = ["distribution_energy_net_rdm", "bill_stabilization_adjustment",
        "empower_maryland", "multi_year_plan_adjustment", "delivery_tax", "environmental_surcharge"]
    return dict(customer_net_rdm=ordinary["customer"]+rdm_customer,
        energy=components, monthly=dict(universal_service=.32 if res else 1.85),
        gross_receipts_rate=.020408, grt_delivery_components=grt_components,
        distribution_season="summer" if summer else "winter",
        distribution_netting=dict(raw_versions=raw,
            initial_2025_rdm_customer=rdm_customer, initial_2025_rdm_energy=rdm_energy,
            basis="Base and RDM share usage clocks and GRT inclusion. August2026 temporary changes cancel exactly; no individual transition allocation inferred.",
            separate_base_rdm_invoice_rounding_verified=False),
        component_month=key[:7], source=CSEG_2026 if current else CSEG_2025,
        source_pdf_page=(1 if res else 4) if current else (1 if res else 5),
        gross_receipts_source="CSEG footnote(1); separately calculated transmission and distribution GRT, AC/MCS excluded",
        coverage_basis="Recovered complete matching calendar billing/service months; incomplete total-bill scope separately disclosed")
