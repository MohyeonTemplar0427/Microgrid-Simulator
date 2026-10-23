"""NSP Minnesota ordinary non-demand tariffs; filed dollars, not market prices.

Only the intersection of verified component windows is executable. Sources and
page/hash evidence live in docs/utility_sources/xcel_mn/manifest.json.
"""
from datetime import date

PLANS = ("A01", "A02", "A10", "A12")
THROUGH = "2026-10-23"
COVERAGE = (("2025-01-01", "2026-09-30"),)
SOURCES = [
    "https://xcelnew.my.salesforce.com/sfc/p/1U0000011ttV/a/R3000009eD7q/dG8j89hN0JiO6SAKQKFHcNhiXf0Osoz7XMTYXy0qV2o",
    "https://xcelnew.my.salesforce.com/sfc/p/1U0000011ttV/a/R3000009e89p/6CCLEW5S0IzVq.omDH.mYhUSD0E_R2DThBnsFiWShaY",
    "https://xcelnew.my.salesforce.com/sfc/p/1U0000011ttV/a/R3000009e3DN/aTr4AtBhOStSP5symY_0MDt4hVbAzxoN3crNQ3NWMK0",
    "https://legistar.granicus.com/minnesotapuc/attachments/49485675-93e3-4200-acfa-1ea163bbe715.pdf",
    "https://www.xcelenergy.com/staticfiles/xe-responsive/Company/Rates%20&%20Regulations/Me_Section_5.pdf",
    "https://www.xcelenergy.com/company/rates_and_regulations/rates/rate_riders",
    "https://webapi.legistar.com/v1/minnesotapuc/matters/4502/attachments/42010/file",
    "https://webapi.legistar.com/v1/minnesotapuc/matters/4504/attachments/43807/file",
    "https://minnesotapuc.legistar.com/View.ashx?GUID=04ABAF9B-7DAE-4139-B233-3CD71CEF7039&ID=13394953&M=F",
    "https://xcelnew.my.salesforce.com/sfc/p/1U0000011ttV/a/8b000002yLiP/27fcisWyYTkolndzNJOZBmaAcZfAkgpze7HiGxkTwv4",
    "https://www.revenue.state.mn.us/sites/default/files/2023-01/FS157.pdf",
    "https://www.revenue.state.mn.us/sites/default/files/2018-12/General_Notice_Sherburne_Co.pdf",
    "https://www.revenue.state.mn.us/sites/default/files/2025-11/local-sales-and-use-tax-rate-guide-2026-q1.pdf",
    "https://www.revenue.state.mn.us/sites/default/files/2026-02/local-sales-and-use-tax-rate-guide-2026-q2.pdf",
    "https://www.revenue.state.mn.us/sites/default/files/2026-08/local-sales-and-use-tax-rate-guide-2026-q4.pdf",
    "https://xcelnew.my.salesforce.com/sfc/p/1U0000011ttV/a/R3000005SWoa/i3UeIgvecEiRLArSFuoyRf8.Y0PhSYrhgX9vSVIqxHc",
    "https://xcelnew.my.salesforce.com/sfc/p/1U0000011ttV/a/R300000NK9Ba/3vK6hTm0TgsICrTCtYQNLWGqqxtHjUAxfpxGbX.P9ak",
    "https://efiling.web.commerce.state.mn.us/documents/%7B30205F97-0000-C619-8AE9-075F3CEC6B70%7D/download?contentSequence=0&rowIndex=5",
    "https://efiling.web.commerce.state.mn.us/documents/%7B0082C697-0000-C912-BA22-B35FA5868587%7D/download?contentSequence=0&rowIndex=1",
    "https://efiling.web.commerce.state.mn.us/documents/%7B40C1C19A-0000-C91E-AE92-1342137088AF%7D/download?contentSequence=0&rowIndex=2",
]
# Standard/peak summer, standard/peak winter, off-peak (where applicable).
BASE = {"A01": (.13069, .11364, None), "A02": (.25879, .21408, .05171),
        "A10": (.11799, .10094, None), "A12": (.19782, .16020, .05182)}
# Actual billed FCC, including dated refunds/true-ups, not forecast fuel alone.
FUEL = {
    2025: ((.02617,.02819,.02919,.00972,.02618,.02839,.02787,.02617,.02300,.02099,.01839,.01608),
           (.02615,.02817,.02916,.00970,.02616,.02837,.02783,.02615,.02299,.02097,.01837,.01606)),
    2026: ((.01568,.01575,.01681,.02499,.02695,.02973,.02927,.02780,.02448,-.00179,.01926,.02162),
           (.01566,.01574,.01679,.02497,.02693,.02971,.02924,.02778,.02445,-.00179,.01925,.02159)),
}


# Inclusive windows. Tuple prices are (residential, commercial NON-DEMAND),
# including A12. Do not use demand-class fuel or STUR for a TOD non-demand plan.
# The supported complete calendar cycles put service and bill-render clocks
# in the same rate month; shifted/partial cycles remain explicitly rejected.
RIDER_HISTORY = {
    "sales_true_up": (
        ("2025-01-01", "2025-05-31", (-.00015, .00170), "5-118.1 revision1, June2024 term"),
        ("2025-06-01", "2026-05-31", (.00570, .00518), "E002/M-25-56 approved notice, June2025 term"),
        ("2026-06-01", "2026-09-30", (.00041, .00034), "5-118.1 revision3, June2026 term"),
    ),
    "cip": (
        ("2025-01-01", "2025-11-30", -.000389, "5-92 revision25; retrospective2024 ECO report"),
        ("2025-12-01", "2026-09-30", .001397, "5-92 revision26; corrected November26,2025 compliance"),
    ),
    "rdf": (
        ("2025-01-01", "2025-01-31", .001385, "5-143 revision27"),
        ("2025-02-01", "2026-03-31", .001097, "February1,2025 effective rider"),
        ("2026-04-01", "2026-09-30", .001371, "5-143 revision29"),
    ),
    "tcr": (
        ("2025-01-01", "2025-12-31", (.004442, .003009), "E002/M-24-371 December17,2024 order"),
        ("2026-01-01", "2026-03-31", (.004436, .003006), "January1,2026 published implemented rider"),
        ("2026-04-01", "2026-09-30", (.006415, .004445), "5-144 revision21 bills-rendered factor"),
    ),
    "res_factor": (
        ("2025-01-01", "2026-04-30", .0241, "E002/M-24-353 December17,2024 order"),
        ("2026-05-01", "2026-09-30", .02463, "5-147 revision21"),
    ),
}


def _rider(component, key, residential):
    matches = [row for row in RIDER_HISTORY[component] if row[0] <= key <= row[1]]
    if len(matches) != 1:
        raise ValueError(f"Minnesota {component} needs one verified dated factor on {key}.")
    start, end, values, reference = matches[0]
    value = values[0 if residential else 1] if isinstance(values, tuple) else values
    return value, dict(start=start, end=end, reference=reference)


def service_rates(day, plan):
    key = day.isoformat() if isinstance(day, date) else str(day)
    try:
        d = date.fromisoformat(key)
        if d.isoformat() != key:
            raise ValueError
    except ValueError as exc:
        raise ValueError("Use exact ISO Minnesota service dates.") from exc
    if plan not in PLANS:
        raise ValueError("Select supported Minnesota A01/A02/A10/A12 ordinary service.")
    if not any(start <= key <= end for start, end in COVERAGE):
        raise ValueError("Minnesota complete-rate coverage is January2025–September2026 only; no October partial cycle or extrapolation.")
    res = plan in ("A01", "A02")
    dated = {name: _rider(name, key, res) for name in RIDER_HISTORY}
    return dict(customer=6., energy=BASE[plan], fuel=FUEL[d.year][not res][d.month-1],
        **{name: value for name, (value, _) in dated.items()},
        interim=.0714, affordability=2.12,
        mercury=0., environmental=0., state_energy_policy=0.,
        base_version="2025-01-01 (standard non-space-heating prices unchanged June2025)",
        fuel_version=f"{d.year}-{d.month:02d}",
        rider_version="; ".join(f"{name}:{version['start']}" for name, (_, version) in dated.items()),
        rider_versions={name: version for name, (_, version) in dated.items()})
