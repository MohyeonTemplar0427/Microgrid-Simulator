"""Dated Pepco District of Columbia SOS calendar-cycle intersections."""
ROOT = "https://www.pepco.com/cdn/assets/v3/assets/bltbb7c204688a1a6a8/"
BOOK_2025 = ROOT+"blt1592c0ff5185f738/6838a59f7476148e7ae7d25a/DC_PCA_SOS_Current_Tariff_Eff_6.1.2025.pdf?branch=prod_alias"
BOOK_2026 = ROOT+"blt1592c0ff5185f738/6a31746c61cd281dcff19c9e/DC_FC1017_SOS_Compliant_Eff_06.01.26_WEBPAGE_1.pdf"
AC_2025 = ROOT+"blt66500373b1c2c438/6838ad23e2a01b03084d9c61/Pepco_DC_Admin_Credit_-_062025.pdf?branch=prod_alias"
AC_2026 = ROOT+"blt66500373b1c2c438/6abd76429c1713cfb5c66be2/Pepco_DC_Admin_Credit_-_102026_.pdf"
SURCHARGES_2024 = ROOT+"bltc885fc58885f93bd/6724ed9eac5a5837cf871fed/DC_Applicable_Surcharges_for_Web_10.31.24.pdf?branch=prod_alias"
SURCHARGES_2026 = ROOT+"bltc885fc58885f93bd/69cec85dff660f73157dc8a7/DC_Applicable_Surcharges_for_Web_04.01.2026.pdf"
BSA_2025 = ROOT+"blt55bfb2d4df34768a/67c5e63d86c64e250e36d89b/Pepco_DC_BSA_-_032025.pdf?branch=prod_alias"
BSA_2026 = "https://azure-na-assets.contentstack.com/v3/assets/bltbb7c204688a1a6a8/blt5b5379651528b194/69a0b911cb09cdedba32880d/Pepco_DC_BSA_-_032026_.pdf"
BSA_REPORT = "https://edocket.dcpsc.org/apis/api/filing/download?attachId=250861&guidFileName=29035541-df98-40f9-aa06-d7e9c60907f0.pdf"
SETF_OCT26 = "https://edocket.dcpsc.org/apis/api/filing/download?attachId=250708&guidFileName=1e9c4277-e002-4b2d-bf02-9298c0c7a95f.pdf"
MESF_OCT26 = "https://edocket.dcpsc.org/apis/api/filing/download?attachId=250709&guidFileName=0dd360f4-c89f-4273-bc32-73b80094baef.pdf"
DER_SOURCE = "https://www.pepco.com/my-account/my-service/green-power-connection"
SOURCES = [BOOK_2025, BOOK_2026, AC_2025, AC_2026, SURCHARGES_2024, SURCHARGES_2026,
           BSA_2025, BSA_2026, BSA_REPORT, SETF_OCT26, MESF_OCT26, DER_SOURCE]
PLANS = ("R", "GS-ND")
COVERAGE = (("2025-06-01", "2025-06-30"), ("2026-06-01", "2026-10-31"))
GAPS = (
    ("2025-01-01", "2025-05-31", "Matching administrative-credit and BSA intersections remain unverified."),
    ("2025-07-01", "2026-05-31", "Administrative-credit chart has blank later-month cells; no extension of June 2025 values."),
    ("2026-11-01", "2026-12-31", "Administrative credits and later rider intersection remain unverified."),
)


def rates_for_month(month, plan):
    if plan not in PLANS:
        raise ValueError("Select Pepco DC R or GS-ND SOS.")
    if not (month == "2025-06" or "2026-06" <= month <= "2026-10"):
        raise ValueError(f"Pepco DC component intersection is unverified for {month}.")
    residential = plan == "R"
    newer = month.startswith("2026")
    july = month >= "2026-07"
    october = month == "2026-10"
    sources = ([BOOK_2025, AC_2025, SURCHARGES_2024, BSA_2025] if not newer else
               [BOOK_2026, AC_2026, SURCHARGES_2026, BSA_2026, BSA_REPORT])
    if october:
        sources += [SETF_OCT26, MESF_OCT26]
    return dict(
        customer=(18.09 if newer else 17.09) if residential else (38.30 if newer else 35.59),
        distribution=(.01982, .05659) if newer and residential else (.01715, .04895) if residential else
                     (.07778 if newer else .07813,),
        # The generation minimum includes the first 30 kWh and their admin charge.
        generation_minimum=(4.40 if july else 3.94) if residential else 0.,
        generation=(.14238 if july else .12800) if residential else (.13874 if july else .12602),
        administration=(.00440 if july else .00320) if residential else (.00420 if july else .00450),
        transmission_minimum=.12 if residential else 0.,
        transmission=(.01924 if newer else .01751) if residential else .01415,
        per_kwh=dict(
            procurement_cost_adjustment=.00316 if residential else -.00427,
            administrative_credit=0. if newer else (-.0005703 if residential else -.0011827),
            bsa_adjustment_ii=.000134 if residential else -.000791,
            delivery_tax=.0070 if residential else .0077,
            public_space_occupancy=.002350 if newer else .002280,
            sustainable_energy_trust=(.001666 if october else .002056) if newer else .006510,
            mayors_energy_surcharge=(.005544 if october else .004854) if newer else 0.,
            energy_assistance_trust=.0002322,
            residential_aid_surcharge=.001155 if newer else .000860,
            underground_project=(.00055 if residential else .00067) if newer else (.00027 if residential else .00034),
            underground_rider=0. if newer else (.00001 if residential else -.00026),
            mrp_adjustment=0.,
        ),
        edit=(-.00047, -.00133) if residential else (-.00342,),
        sources=sources,
        source_version="pepco-dc-"+month,
        source_grade="dated_filed_sheets_and_official_bsa_continuation" if newer else "dated_filed_sheets_and_official_monthly_tables",
    )
