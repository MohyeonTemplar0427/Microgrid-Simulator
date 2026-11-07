"""Kentucky Power ordinary RS/secondary GS: verified component intersections.

Dollar/kWh and decimal revenue factors. Service clocks and the independently
assigned utility billing month are distinct. Published calculators contain
known stale fields; the filed sheets and Commission orders govern.
"""
BOOK = "https://psc.ky.gov/tariffs/electric/Kentucky%20Power%20Company/Tariff.pdf"
CANCELLED = "https://psc.ky.gov/tariffs/Electric/Kentucky%20Power%20Company/Cancelled%20Tariff%20Pages/2026/"
FAC_2025 = "https://psc.ky.gov/PSCFAC/aep-kentucky%20power%20company/2025_KP.pdf"
ES_REVIEW = "https://psc.ky.gov/pscecf/2026-00071/mmcaldwell%40aep.com/05152026024532/04_KPCO_R_KPSC_1_1_Attachment1.xlsx"
SSR_ORDER = "https://psc.ky.gov/pscscf/2025%20Cases/2025-00307//20261008_PSC_ORDER.pdf"
FUEL_CREDIT_ORDER = "https://psc.ky.gov/order_vault/Orders_2025/202300008_12222025.pdf"
MARCH_FAC = "https://psc.ky.gov/trf4/uploadedFiles/300_Kentucky_Power_Company/02122026024156/KPCO_Tariff_1st_Revised_Tariff_Sheet_30-3_Annotated.pdf"
DSM_CASE = "https://psc.ky.gov/Case/ViewCaseFilings/2025-00365"
CALCULATOR_ROOT = "https://www.kentuckypower.com/lib/docs/ratesandtariffs/Kentucky/"
CALCULATORS = [CALCULATOR_ROOT+f"2026-{m:02}_KP_Rate.xls" for m in range(1, 12)]
SOURCES = [BOOK, CANCELLED, FAC_2025, ES_REVIEW, SSR_ORDER, FUEL_CREDIT_ORDER, MARCH_FAC, DSM_CASE, *CALCULATORS]
COVERAGE = (("2025-12-01", "2026-08-31"),)
GAPS = (
    ("2025-01-01", "2025-11-30", "Earlier complete component intersections and transition allocations are unverified."),
    ("2026-09-01", "2026-09-30", "The service-date Decommissioning Rider step on September 29 requires unverified allocation."),
    ("2026-10-01", "2026-12-31", "Later annual rider sheets and the complete December monthly factor stack are not reconciled."),
)
CODES = {"RS": ("015", "017", "022"), "GS": ("211", "212", "215", "216", "218")}

# Named utility billing month, FAC, residential ES, non-residential ES.
# December FAC is the filed December billing factor, not its October expense
# label. January ES uses the regulator review's November expense factor;
# the January calculator erroneously repeats October's environmental factor.
MONTHLY = {
    "2025-12": (.00586, .050112, .086949),
    "2026-01": (.00346, .048531, .087593),
    "2026-02": (.00763, .041856, .075494),
    "2026-03": (.02200, .022183, .036226),
    "2026-04": (.01414, .035022, .058077),
    "2026-05": (.01774, .026526, .044367),
    "2026-06": (.01377, .033689, .057904),
    "2026-07": (-.00017, .026963, .045285),
    "2026-08": (.00496, .038856, .067248),
    "2026-09": (.00746, .033181, .056682),
}


def rates_for_cycle(service_month, billing_month=None):
    year, month = map(int, service_month.split("-"))
    following = f"{year+(month == 12):04}-{month%12+1:02}"
    billing_month = billing_month or following
    if not any(a[:7] <= service_month <= b[:7] for a, b in COVERAGE):
        raise ValueError(f"Kentucky Power service components or transition allocation are unverified for {service_month}.")
    if billing_month not in MONTHLY:
        raise ValueError(f"Kentucky Power monthly billing factors are unverified for {billing_month}.")
    if billing_month != following:
        raise ValueError("Kentucky Power initial calendar studies require independently confirmed next-month billing.")
    new = service_month >= "2026-03"
    fac, es_rs, es_gs = MONTHLY[billing_month]
    return dict(
        customer=(24., 31.) if new else (20., 28.),
        energy_rs=(.15385, .11534) if new else (.12785, .12785),
        energy_gs=.13725 if new else .13060,
        temporary_rs=.00494, assistance_rs=.40, development_gs=1.,
        system_sales=-.00029, dsm=(.000587, .000573),
        federal_tax_credit=(-.00083, -.00058), purchase_power=(.00022, .00019),
        generation=(.00476, .00373) if new else (0., 0.),
        deferred_tax=(-.00080, -.00057) if new else (0., 0.),
        fac=fac,
        fuel_credit=(-.00487, -.00432) if "2026-01" <= billing_month <= "2026-04" else (0., 0.),
        environmental=(es_rs, es_gs), decommissioning=(.000082, .000135),
        securitized=(.057929, .128595) if new else (.070704, .109636),
        embedded_fuel=.03380, school_tax=.03, commercial_sales_tax=.06,
        source_version=f"kp-ky-service-{service_month}-billing-{billing_month}",
        source_grade="filed_sheets_orders_and_official_monthly_factors",
        sources=SOURCES,
    )


def rates_for_month(month):
    return rates_for_cycle(month)
