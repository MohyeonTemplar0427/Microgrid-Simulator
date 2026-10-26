"""Snapshot-safe BGE R/G monthly tariff components, dollars per imported kWh.

Original dated component ledger plus filed schedules/riders; no market-price,
neighboring-month or proposed-rate substitution. See the checked-in source ledger.
"""
from datetime import date

PLANS = ("R", "G")
COVERAGE = (("2025-01-01", "2026-10-31"),)
ASSETS = "https://azure-na-assets.contentstack.com/v3/assets/blt71bfe6e8a1c2d265/"
COMPONENT_LEDGER = "https://www.bge.com/cdn/assets/v3/assets/blt71bfe6e8a1c2d265/blt8ad3da6ba8d050f5/6acfc043f4251ab7b699fb93/Rdr32_CS_Current_Rates_12.pdf?branch=prod_alias"
SOURCES = [COMPONENT_LEDGER,
    ASSETS+"blt10129d1f47260cd7/P3_SCH_R.pdf",
    ASSETS+"bltae5a035d36f7f19e/P3_SCH_G.pdf",
    ASSETS+"blt970ee32f55c20fde/6abe810c794a172f39b99bc0/Rdr_1_9.pdf",
    ASSETS+"blt0b5280aebf1a4a36/Rdr_2.pdf",
    ASSETS+"blt3c6680987cbdeb5f/Rdr_3.pdf",
    ASSETS+"blt95b3f3254f635c76/Rdr_15.pdf",
    ASSETS+"blt722af29653644b4e/Rdr_16_17.pdf",
    ASSETS+"blt8ca2dfc58e27bd9a/Rdr_25.pdf",
    ASSETS+"bltbcb53d4782e3ba22/Rdrs_26_27.pdf",
    ASSETS+"blt0bfdbd25fd81f70c/Rdr_33_34.pdf",
    "https://www.bge.com/cdn/assets/v3/assets/blt71bfe6e8a1c2d265/bltf75afad89af14ef3/6acce6326214c42d62238ff5/POLR_RateAdjustmentChart_1.pdf?branch=prod_alias",
    "https://www.bge.com/cdn/assets/v3/assets/blt71bfe6e8a1c2d265/blt5d58e3f9b4655346/6abe7c86a1315212b30adbc1/Rider_25_Historical_Chart.pdf?branch=prod_alias",
    "https://codelibrary.amlegal.com/codes/annearundel/latest/annearundelco_md/0-0-0-152054",
    "https://regs.maryland.gov/us/md/exec/comar/03.06.01.10",
    "https://regs.maryland.gov/us/md/exec/comar/03.06.01.08",
    "https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=gtg&section=11-101",
    "https://mgaleg.maryland.gov/mgawebsite/laws/StatuteText?article=gpu&section=7-203",
    "https://www.bge.com/my-account/customer-support/assistance-programs/legislative-energy-relief-refund",
]

# Arrays are Jan–Dec2025 or Jan–Oct2026, never open-ended.
# Generation includes its applicable administration/tax components; transmission
# includes its applicable GRT/PSC assessment. Rider8 is separate, once.
GENERATION = {
    (2025,"R"):(.10405,.10397,.10397,.10397,.10397,.10247,.10247,.10247,.13496,.14321,.14321,.11071),
    (2025,"G"):(.10027,.10046,.10046,.10046,.10046,.10123,.10123,.10123,.12320,.12521,.12521,.10324),
    (2026,"R"):(.11071,.11115,.14365,.14365,.14365,.12519,.12519,.12519,.12519,.12962),
    (2026,"G"):(.10324,.10372,.12569,.12569,.12569,.12140,.12140,.12140,.12140,.12076),
}
TRANSMISSION = {
    (2025,"R"):(.01682,)*5+(.02322,)*7,
    (2025,"G"):(.01413,)*5+(.01986,)*7,
    (2026,"R"):(.02322,)*5+(.02228,)*5,
    (2026,"G"):(.01986,)*5+(.01762,)*5,
}
ENERGY_COST_ADJUSTMENT = {
    (2025,"R"):(-.00165,)+(-.00180,)*4+(.00018,)*4+(.00088,)*3,
    (2025,"G"):(.00422,)+(.00510,)*4+(-.00088,)*4+(.00118,)*3,
    (2026,"R"):(.00088,)+(-.00049,)*4+(-.00138,)*4+(-.01050,),
    (2026,"G"):(.00118,)+(.00736,)*4+(-.00285,)*4+(-.00736,),
}
MONTHLY_RATE_ADJUSTMENT = {
    (2025,"R"):(.00330,.00424,-.00019,.00371,.00475,-.00295,.00321,.00118,-.00148,.00475,-.00475,.00200),
    (2025,"G"):(.00419,.00064,-.00475,-.00482,-.00340,-.00411,.00046,.00192,-.00171,.00332,-.00482,-.00387),
    (2026,"R"):(.00367,-.00095,-.00189,-.00333,.00482,.00031,.00210,-.00005,-.00152,-.00173),
    (2026,"G"):(-.00086,-.00243,.00250,-.00497,-.00307,-.00477,-.00084,.00297,.00220,.00066),
}
ADMINISTRATIVE_CREDIT = {
    (2025,"R"):(-.00097,)+(-.00101,)*4+(-.00096,)*7,
    (2025,"G"):(-.00065,)+(-.00061,)*4+(-.00064,)*4+(-.00063,)*3,
    (2026,"R"):(-.00096,)+(-.00111,)*4+(-.00107,)*4+(-.00108,),
    (2026,"G"):(-.00063,)+(-.00062,)*4+(-.00064,)*4+(-.00063,),
}
MYP = {(2025,"R"):(.00254,)*2+(0.,)*10,
       (2025,"G"):(.00241,)*2+(0.,)*10,
       (2026,"R"):(0.,)+(.00086,)*9,
       (2026,"G"):(0.,)+(.00041,)*9}


def rates_on(day, plan="R"):
    key = day.isoformat() if type(day) is date else day
    try:
        if not isinstance(key, str) or date.fromisoformat(key).isoformat() != key:
            raise ValueError
    except ValueError as exc:
        raise ValueError("Use exact ISO BGE local dates.") from exc
    if plan not in PLANS:
        raise ValueError("Select BGE R or G Type I SOS.")
    if not any(start <= key <= end for start, end in COVERAGE):
        raise ValueError("BGE verified monthly coverage is January2025–October2026; no missing/future price substitution.")
    year, month = int(key[:4]), int(key[5:7])
    index = month-1
    pair = (year, plan)
    res = plan == "R"
    current = year == 2026
    return dict(customer=(10. if current else 9.65) if res else (15.6 if current else 15.1),
        energy=dict(distribution_energy=(.04859 if current else .04751) if res else (.04965 if current else .04819),
            generation_supply=GENERATION[pair][index], transmission_service=TRANSMISSION[pair][index],
            energy_cost_adjustment=ENERGY_COST_ADJUSTMENT[pair][index],
            monthly_rate_adjustment=MONTHLY_RATE_ADJUSTMENT[pair][index],
            administrative_cost_credit=ADMINISTRATIVE_CREDIT[pair][index],
            multi_year_plan_adjustment=MYP[pair][index],
            energy_efficiency=(.01097 if current else .00764) if res else (.03526 if current else .02059),
            demand_response=(.00198 if current else .00251) if res else (.00027 if current else 0.),
            peak_time_rebate=(.00015 if current else .00013) if res else (.00013 if current else .00011),
            franchise_tax=.00062),
        monthly=dict(universal_service=.32 if res else 1.85),
        environmental_rate=.00015, environmental_monthly_cap=1000.,
        county_tax_rate=0. if res else .0025, sales_tax_rate=0. if res else .06,
        base_version=f"January1,{year}", rider_version=key[:7],
        supply_includes_administration_and_tax=True,
        source_component_pages={"R":2 if current else 12,"G":6 if current else 16}[plan],
        source=COMPONENT_LEDGER)
