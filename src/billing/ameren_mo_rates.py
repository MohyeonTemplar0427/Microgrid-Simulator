"""Filed Missouri 1(M)/2(M) prices, in USD, inside immutable engine snapshots.

Service-date factors are not authorized maxima, forecasts or wholesale LMPs.
Source pages, revisions and hashes: docs/utility_sources/ameren_mo/manifest.json.
"""
from datetime import date

THROUGH = "2026-10-21"
PLANS = ("1M", "1M-EMS", "1M-SMART-A", "1M-SMART-B", "1M-OVERNIGHT-A", "1M-OVERNIGHT-B", "2M")
SOURCES = [
    "https://www.ameren.com/-/media/rates/missouri/residential/electric-rates/rates/uecsheet54rate1mres.ashx",
    "https://www.ameren.com/-/media/rates/missouri/non-residential/electric-rates/rates/uecdsheet55rate2msgs.ashx",
    "https://efis.psc.mo.gov/Tariff/Display/21976",
    "https://efis.psc.mo.gov/Document/Display/358720",
    "https://efis.psc.mo.gov/Document/Display/374382",
    "https://efis.psc.mo.gov/Document/Display/364118",
    "https://efis.psc.mo.gov/Document/Display/370166",
    "https://efis.psc.mo.gov/Document/Display/367355",
    "https://efis.psc.mo.gov/Document/Display/825521",
    "https://www.ameren.com/-/media/rates/missouri/residential/electric-rates/general-rules/uecsheet130rrsecvbillingpractices.ashx",
    "https://www.ameren.com/-/media/rates/missouri/uecesheetno92riderssrstandbyservicerider.ashx",
    "https://dor.mo.gov/resources/official-final-rules/documents/12_CSR_10-108_300_Sales_of_Electricity%2C_Water_Gas.pdf",
    "https://dor.mo.gov/taxation/business/tax-types/sales-use/rate-tables/2025/",
    "https://dor.mo.gov/taxation/business/tax-types/sales-use/rate-tables/2026/",
]

# (summer, winter first750, winter tail); TOU arrays are peak/intermediate/off.
BASE = {
    "2023-12-03": dict(anytime=(.1372,.0934,.0627), ems=(.1340,.0919,.0616),
        ems_adder=(.0050,.0025), smart_summer=(.3562,.1069,.0674),
        smart_winter=(.1907,.0684,.0558), overnight=(.1617,.0644,.0910,.0555),
        residential_customer=9., residential_pilot=.14,
        commercial_customer=(11.96,22.87), commercial_pilot=.20, commercial=(.1197,.0894,.0516)),
    "2025-06-01": dict(anytime=(.1560,.1062,.0714), ems=(.1524,.1045,.0701),
        ems_adder=(.0057,.0028), smart_summer=(.4051,.1216,.0767),
        smart_winter=(.2169,.0778,.0635), overnight=(.1839,.0732,.1034,.0631),
        residential_customer=9., residential_pilot=.19,
        commercial_customer=(13.46,25.73), commercial_pilot=.26, commercial=(.1346,.1005,.0581)),
}

# Inclusive filed service windows; already voltage-adjusted secondary factors.
FAC = (("2024-10-01","2025-01-31",.00229),
       ("2025-02-01","2025-05-31",.00114),
       ("2025-06-01","2025-09-30",.00360),
       ("2025-10-01","2026-01-31",.00330),
       ("2026-02-01","2026-05-31",.00540),
       ("2026-06-01","2026-09-30",.00894),
       ("2026-10-01","2027-01-31",.00445))
SUR = (("2024-12-20","2025-09-30",.00200),
       ("2025-10-01","2026-03-31",.00108),
       ("2026-04-01","2026-09-30",.00118),
       ("2026-10-01","2027-03-31",.00157))
EEIC = (("2024-02-01","2025-01-31",(.003572,.003739)),
        ("2025-02-01","2026-01-31",(.002171,.002819)),
        ("2026-02-01","2027-01-31",(.001905,.002272)))
# June2025 supersedes the original Feb2025 factor: rebased costs are in base rates.
RESRAM = (("2024-02-01","2025-01-31",.00204),
          ("2025-02-01","2025-05-31",.00313),
          ("2025-06-01","2026-01-31",.00133),
          ("2026-02-01","2027-01-31",.00207))


def service_rates(day, plan):
    key = day.isoformat() if isinstance(day,date) else str(day)
    try:
        if date.fromisoformat(key).isoformat()!=key:raise ValueError
    except ValueError as exc:
        raise ValueError("Use an exact valid ISO service date for Missouri rates.") from exc
    if plan not in PLANS or not "2025-01-01" <= key <= THROUGH:
        raise ValueError("Ameren Missouri verified service coverage is January 1, 2025–October 21, 2026; no rate extrapolation.")
    version = "2023-12-03" if key < "2025-06-01" else "2025-06-01"
    result = {**BASE[version], "base_version":version}
    for name, rows in (("fuel_adjustment",FAC),("securitization",SUR),("energy_efficiency",EEIC),("renewable_adjustment",RESRAM)):
        match=[(start,value) for start,end,value in rows if start<=key<=end]
        if len(match)!=1:
            raise ValueError("Missing or overlapping verified Missouri rider coverage: "+name)
        start,value=match[0]
        result[name]=value[plan=="2M"] if isinstance(value,tuple) else value
        result[name+"_version"]=start
    return result
