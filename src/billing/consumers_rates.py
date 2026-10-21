"""Consumers Energy MPSC14 filed USD rates, not rounded marketing examples.

Base/DR/IRM/FCM/deferral use service dates. PSCR/EE/securitization use the
utility billing month. Actual PSCR (not maximum allowed) limits coverage.
See docs/utility_sources/consumers/manifest.json for immutable source evidence.
"""
THROUGH = "2026-06-30"
SOURCES = [
    "https://www.michigan.gov/mpsc/consumer/electricity/data-price/electric-rate-books/mpsc-approved-consumers-energy-electric-rate-books-and-cancelled-sheets",
    "https://www.michigan.gov/-/media/Project/Websites/mpsc/consumer/rate-books/electric/consumers/Consumers_14_current.pdf",
    "https://www.michigan.gov/mpsc/-/media/Project/Websites/mpsc/consumer/rate-books/electric/consumers/Consumers_14_canceled_D.pdf?rev=374cf8b11bc848f995aa558e72be1308&hash=33C19B1A701473025B0C71BDB1705AB5",
    "https://www.michigan.gov/mpsc/-/media/Project/Websites/mpsc/consumer/rate-books/electric/consumers/Consumers_14_canceled_A_B_C.pdf?rev=42d0436d41e14fa4a811a4a14fdae581&hash=AABB9439F27CB95BD60633F56296B6C9",
    "https://www.michigan.gov/treasury/reference/letter/2013-letter-rulings/letter-ruling-2013-5",
    "https://www.michigan.gov/taxes/business-taxes/sales-use-tax",
]
PLANS = ("RSP", "RSH", "GS", "GSTU")
# Slots: summer off/mid/on, winter off/on. RSP winter is flat; GS seasonal.
BASE = {
 "RSP": [
  ((.086217,.086217,.132272,.082887,.082887),(.005990,.005990,.008912,.004667,.004667)),
  ((.091516,.091516,.139098,.079248,.079248),(.007706,.007706,.011465,.006004,.006004)),
  ((.067348,.067348,.098398,.053762,.053762),(.036622,.036622,.053506,.029234,.029234))],
 "RSH": [
  ((.086217,.086217,.132272,.080987,.091448),(.005990,.005990,.008912,.004518,.005139)),
  ((.091516,.091516,.139098,.077159,.088715),(.007706,.007706,.011465,.005812,.006611)),
  ((.067348,.067348,.098398,.052104,.062442),(.036622,.036622,.053506,.028333,.033954))],
 "GS": [
  ((.094566,)*3+(.082686,)*2,(.006246,)*3+(.004372,)*2),
  ((.097639,)*3+(.076879,)*2,(.007743,)*3+(.005420,)*2),
  ((.073051,)*3+(.053797,)*2,(.035056,)*3+(.025987,)*2)],
 "GSTU": [
  ((.073219,.098057,.132113,.071813,.091062),(.004064,.006297,.007579,.003541,.004740)),
  ((.075218,.102027,.134569,.066563,.084687),(.005037,.007806,.009395,.004390,.005876)),
  ((.058059,.077384,.099359,.047509,.058750),(.028063,.037369,.047982,.022961,.028428))],
}
PSCR = {f"2025-{i+1:02d}": v for i,v in enumerate((.00794,.00758,.00909,.00909,.01344,.01084,.01127,.01127,.01023,.00909,.00909,.00909))}
PSCR.update({f"2026-{i+1:02d}":v for i,v in enumerate((.01456,.01456,.01597,.01456,.01456,.01337))})
EE = [
 ("2025-01", .004529, (7.82,57.72,125.14,299.95,772.22,1240.82,1794.32,2145.02,2487.66,2736.73)),
 ("2026-01", .003777, (6.49,48.30,104.61,250.95,648.69,1046.93,1518.26,1822.28,2112.80,2325.29)),
 ("2026-02", .004861, (8.11,59.77,129.62,310.64,799.18,1283.12,1854.55,2215.21,2569.00,2825.27)),
 ("2026-03", .004617, (8.25,59.64,128.73,326.17,747.53,1117.28,1406.91,1771.89,2062.13,2350.47)),
]


def dated(day, versions):
    return next(value for start,value in reversed(versions) if day >= start)


def service_rates(day, plan):
    day = str(day)[:10]
    if plan not in PLANS or not "2025-01-01" <= day <= THROUGH:
        raise ValueError(f"Consumers verified service coverage is 2025-01-01 through {THROUGH}; no extrapolation.")
    res = plan in ("RSP", "RSH")
    v = dated(day, [("2025-01-01",0),("2025-04-04",1),("2026-05-01",2)])
    return dict(version=("2024-03-15","2025-04-04","2026-05-01")[v],
        energy=BASE[plan][v][0],capacity=BASE[plan][v][1],
        distribution=((.074267,.078955,.093333) if res else (.057594,.063166,.069433))[v],
        demand_response=dated(day,[("2025-01-01",0.),("2025-04-04",.002250 if res else .002106),
                                  ("2026-05-01",.002224 if res else .002000)]),
        irm=dated(day,[("2025-01-01",.000150 if res else .000119),
                       ("2025-03-01",.000424 if res else .000337),
                       ("2025-04-04",.000259 if res else .000211),
                       ("2026-03-01",0.),("2026-05-01",.000699 if res else .000534)]),
        fcm=dated(day,[("2025-01-01",0.),("2025-04-25",.000293 if res else .000274),
                       ("2026-01-01",.000243 if res else .000235)]),
        deferral=dated(day,[("2025-01-01",.000430 if res else .000342),
                            ("2025-03-15",0.),("2025-04-04",.001090 if res else .000889),
                            ("2026-04-04",0.),("2026-05-01",.001221 if res else .000933)]))


def rendered_rates(month, residential):
    month = str(month)[:7]
    if month not in PSCR:
        raise ValueError("Consumers actual billed PSCR verified January 2025–June 2026 only; no maximum-factor substitution.")
    c=0 if residential else 1
    ee = dated(month, [(d,(r,fees)) for d,r,fees in EE])
    return dict(pscr=PSCR[month], residential_ee=ee[0],commercial_ee=ee[1],
        power_plant_securitization=dated(month,[("2025-01",(.001187,.001263)),("2025-08",(.001131,.001222))])[c],
        karn_securitization=dated(month,[("2025-01",(.004556,.004103)),("2025-10",(.004049,.003662))])[c],
        lieaf=.87 if month < "2025-09" else 1.25,
        refund_reconciliation=(-.14 if residential else -.41) if month=="2025-02" else 0.,
        irm_reconciliation=(-.02 if residential else -.05) if month=="2026-05" else 0.)
