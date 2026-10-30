"""Filed Duquesne RS/GS components; dollars, not rounded website PTC.

Original PUC filings and retained primary tariff excerpts are indexed in
docs/utility_sources/duquesne_pa. No wholesale, capacity or GRT adders apply.
"""
from datetime import date

PLANS=("RS","GS")
COVERAGE=(("2025-01-01","2026-10-31"),)
SOURCES=[
    "https://duquesnelight.com/service-reliability/service-map/rates/tariff-resources",
    "https://www.duquesnelight.com/service-reliability/service-map/rates/tariff-resources/tariff-history",
    "https://www.puc.pa.gov/pcdocs/1859015.pdf",
    "https://www.puc.pa.gov/pcdocs/1851302.pdf",
    "https://www.puc.pa.gov/pcdocs/1855715.pdf",
    "https://www.puc.pa.gov/pcdocs/1826568.pdf",
    "https://www.puc.pa.gov/pcdocs/1877398.pdf",
    "https://www.puc.pa.gov/pcdocs/1927034.pdf",
    "https://www.puc.pa.gov/pcdocs/1860313.pdf",
    "https://www.puc.pa.gov/pcdocs/1861038.pdf",
    "https://www.pa.gov/agencies/revenue/resources/tax-types-and-information/sales-use-and-hotel-occupancy-tax",
]
BASE={"RS":(13.,.082479),"GS":(18.,.084601)}
SUPPLY=(
    ("2025-01-01",(.084472,.024048),(.077009,.015625),"puc1851302/puc1859015"),
    ("2025-06-01",(.097093,.027187),(.084471,.018386),"DLC110 printed98A/98B;DLC99 printed142"),
    ("2025-12-01",(.110275,.027187),(.097016,.018386),"DLC110 printed98A/98B;DLC99 printed142"),
    ("2026-06-01",(.109568,.031841),(.096754,.012015),"DLC110 printed98A/98B/142"),
)
EEC=(("2025-01-01",(.0021,.0020),"PUC1826568/Supp76"),
     ("2025-06-01",(.0019,-.0006),"PUC1877398/Supp93"),
     ("2026-06-01",(.0017,.0009),"PUC1927034/Supp104"))
USC=(("2025-01-01",.01549,"PUC1857627/Supp84"),
     ("2026-01-01",.01599,"PUC1904364/Supp97"))
DSIC=(("2025-01-01",-.0010,"Supp87/25th revised137"),
      ("2025-04-01",.0002,"Supp90/26th revised137;cancelled bySupp99"),
      ("2026-01-01",.0049,"Supp99/27th revised137"),
      ("2026-04-01",.0139,"Supp101/28th revised137"),
      ("2026-07-01",.0217,"Supp107/29th revised137"),
      ("2026-10-01",.0336,"Supp110/30th revised137"))
STAS=(("2025-01-01",-.001278,"Supp86 printed112"),
      ("2026-01-01",-.000964,"Supp98 printed112"))


def iso_day(day):
    key=day.isoformat() if type(day) is date else day
    if not isinstance(key,str):raise ValueError("Use exact ISO Duquesne service/bill dates.")
    try:valid=date.fromisoformat(key).isoformat()==key
    except ValueError:valid=False
    if not valid:raise ValueError("Use exact ISO Duquesne service/bill dates.")
    if not any(s<=key<=e for s,e in COVERAGE):raise ValueError("Duquesne verified dated coverage is January2025–October2026; missing/future prices are not substituted.")
    return key


def _version(day,versions):
    return next(row for row in reversed(versions) if row[0]<=day)


def rates_on(day,plan="RS",*,bill_date=None):
    service=iso_day(day);rendered=iso_day(day if bill_date is None else bill_date)
    if service[:7]!=rendered[:7]:raise ValueError("Duquesne bill-rendered date must stay in the matching calendar service month; shifted allocation is unverified.")
    if plan not in PLANS:raise ValueError("Select Duquesne RS or non-demand GS fixed default service.")
    res=plan=="RS";customer,distribution=BASE[plan]
    supply=_version(service,SUPPLY);dss,tsc=supply[1 if res else 2]
    eec=_version(service,EEC);usc=_version(service,USC);dsic=_version(rendered,DSIC);stas=_version(rendered,STAS)
    return dict(customer=customer,distribution_kwh=distribution,dss_kwh=dss,tsc_kwh=tsc,
        eec_kwh=eec[1][0 if res else 1],usc_kwh=usc[1] if res else 0.,
        smart_meter=0.,rmes=0.,dsic_fraction=dsic[1],stas_distribution_fraction=stas[1],stas_all_fraction=0.,
        source_versions={"base":"Supp85 effective2024-12-20; originalPUC1859015/1859726",
            "supply":{"start":supply[0],"source":supply[3]},"energy_efficiency":{"start":eec[0],"source":eec[2]},
            "universal_service":{"start":usc[0],"source":usc[2]} if res else {"status":"not_applicable_GS_Rider5"},
            "DSIC":{"start":dsic[0],"source":dsic[2],"basis":"bill-rendered date; distribution clauses/riders excluding STAS"},
            "STAS":{"start":stas[0],"source":stas[2],"part2":"explicit_zero"},
            "smart_meter":"Supp55 effective2023-01-01 printed129 explicitzero",
            "retail_market_enhancement":"Supp40 effective2022-02-01 printed88 explicitzero RS/smallCI"})
