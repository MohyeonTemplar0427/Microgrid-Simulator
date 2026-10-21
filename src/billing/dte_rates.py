"""DTE Electric filed prices; cents/kWh in source tables, USD here.

Service-effective base/NS/IRM and bills-rendered riders have separate clocks.
PSCR is the actual billed factor, never the authorized maximum. Source page
numbers and immutable download hashes are in docs/utility_sources/dte/.
"""
THROUGH = "2026-09-30"
SOURCES = [
    "https://www.dteenergy.com/content/dam/dteenergy/deg/website/common/service-and-price/rate-cards/DTEElectricRateBook.pdf",
    "https://www.michigan.gov/-/media/Project/Websites/mpsc/consumer/rate-books/electric/dte/dtee1cand1throughend.pdf",
    "https://www.michigan.gov/documents/mpsc/dtee1cana1throughc_579208_7.pdf",
    "https://www.michigan.gov/-/media/Project/Websites/mpsc/consumer/rate-books/electric/dte/dtee1cur.pdf?rev=a501ba54eeda4cb185ac62862e291337",
    "https://s24.q4cdn.com/970999156/files/doc_downloads/2025/12/U-21338_12-05-25-Finalized.pdf",
    "https://www.dteenergy.com/content/dam/dteenergy/deg/website/common/billing-and-payment/billing/understanding-your-bill/ExplanationCharges.pdf",
    "https://www.michigan.gov/treasury/reference/letter/2013-letter-rulings/letter-ruling-2013-5",
    "https://www.michigan.gov/taxes/business-taxes/sales-use-tax",
]


def dated(day, versions):
    return next(value for start, value in reversed(versions) if day >= start)


def service_rates(day, plan):
    day = str(day)[:10]
    start = "2025-06-01" if plan == "D3.11" else "2025-01-01"
    if plan not in ("D1.11", "D3", "D3.11") or not start <= day <= THROUGH:
        raise ValueError(f"DTE {plan} verified service coverage is {start} through {THROUGH}; no extrapolation.")
    version = dated(day, [("2025-01-01", 0), ("2025-02-06", 1), ("2026-03-05", 2)])
    # TOU tuple order: summer on, summer off, winter on, winter off.
    capacity = {"D1.11": [(2.060, 1.241, 1.438, 1.241), (5.649, 3.403, 3.984, 3.403), (5.360, 3.240, 3.839, 3.240)],
                "D3": [(1.010,)*4, (2.763,)*4, (2.603,)*4],
                "D3.11": [None, (4.347, 2.593, 2.774, 2.593), (4.086, 2.496, 2.667, 2.496)]}
    energy = {"D1.11": [(12.201, 7.354, 8.518, 7.354), (8.838, 5.325, 6.233, 5.325), (9.047, 5.469, 6.480, 5.469)],
              "D3": [(7.096,)*4, (5.413,)*4, (5.562,)*4],
              "D3.11": [None, (8.516, 5.079, 5.435, 5.079), (8.730, 5.332, 5.699, 5.332)]}
    res = plan == "D1.11"
    return dict(version=("2023-12-15", "2025-02-06", "2026-03-05")[version],
                capacity=tuple(v/100 for v in capacity[plan][version]),
                energy=tuple(v/100 for v in energy[plan][version]),
                distribution=([8.137, 8.907, 9.726] if res else [5.288, 5.858, 6.670])[version]/100,
                service=8.50 if res else 11.25,
                nuclear=([.0882, .0911, .0890][version])/100,
                irm=dated(day, [("2025-01-01", (.0941, .0595)), ("2026-01-01", (.2183, .1391)),
                                ("2026-03-05", (.2762, .1796))])[0 if res else 1]/100)


def rendered_rates(day, residential):
    day = str(day)[:10]
    if not "2025-01-01" <= day <= THROUGH:
        raise ValueError("DTE actual billed PSCR verified only January 2025–September 2026; a maximum factor is not an actual billed factor.")
    c = 0 if residential else 1
    return dict(pscr=(.250 if day < "2026-03-01" else 1.877)/100,
                river_rouge=dated(day, [("2025-01-01", (.0255, .0209)), ("2025-04-01", (.0242, .0197)),
                                       ("2026-04-01", (.0221, .0180))])[c]/100,
                tcsc=dated(day, [("2025-01-01", (.1862, .1521)), ("2025-12-01", (.2292, .1867))])[c]/100,
                delivery_securitization=dated(day, [("2025-01-01", (.1575, .0996)), ("2025-04-01", (.1749, .1145)),
                                                  ("2026-04-01", (.1617, .1058))])[c]/100,
                residential_ewr=dated(day, [("2025-01-01", .2699), ("2026-01-01", .2481), ("2026-02-01", .4488)])/100,
                commercial_ewr=dated(day, [("2025-01-01", (5.53, 33.51, 140.98)),
                                           ("2026-01-01", (5.75, 34.85, 146.61)),
                                           ("2026-02-01", (4.91, 29.81, 125.39))]),
                lieaf=dated(day, [("2025-01-01", .87), ("2025-09-01", 1.25), ("2026-09-01", 1.50)]))
