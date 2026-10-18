"""Explicit Ohio Edison2025 research assumptions, never verified tariff coverage.

Amounts are dollars/kWh unless a unit is stated. These source-pinned values
are replaceable assumptions; solver/replay checks cannot verify their history.
"""
from copy import deepcopy

MODEL = "ohio_edison_2025_provisional_v1"
TESTIMONY = "https://www.firstenergycorp.com/content/dam/customer/OpCoHome/files/ohio-esp-vi/"
BOOK = "https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/Ohio/tariffs/"

FEBRUARY = dict(esp="ESP IV", ami=(2.185, 9.346), dcr=(.009711, 3.2608),
                dcr_basis="energy_or_demand", dse=.001151,
                edr=(.000252, .002662), automaker=.000022, vmc=(0., 0.))

ASSUMPTIONS = [
    dict(id="OE25-GEN18", kind="rate", start="2025-02-01", end="2025-05-31", basis="service_date",
         components=["supply_energy", "supply_capacity"],
         assumed_values=dict(energy_usd_per_kwh=.073408, capacity_rs_usd_per_kwh=.003080, capacity_gs_usd_per_kwh=.002908),
         explanation="Assume January GEN17 winter energy/capacity rates continue through May31. Approved February GEN18 has not been recovered; June GEN19 is not carried backward.",
         sources=[BOOK+"OE-2024-Electric-Service.pdf"]),
    dict(id="OE25-FEB-RECONSTRUCTION", kind="rate", start="2025-02-01", end="2025-03-31", basis="service_date",
         components=["advanced_meter", "demand_side_efficiency", "economic_development", "automaker_recovery"],
         assumed_values=dict(ami_rs_usd_per_month=2.185, ami_gs_usd_per_month=9.346,
             dse_usd_per_kwh=.001151, edr_rs_usd_per_kwh=.000252, edr_gs_usd_per_kwh=.002662, automaker_usd_per_kwh=.000022),
         explanation="Reconstruct February ESP-IV AMI/DSE/EDR from current-rate columns in January31 testimony and hold through March31. Proposed ESP-VI columns are excluded; approved compliance-sheet continuity is unverified.",
         sources=[TESTIMONY+"Testimony-Brandon-McMillen.pdf", TESTIMONY+"Testimony-Dhara-Patel.pdf"]),
    dict(id="OE25-FEB-RIDER-CONTINUITY", kind="rate", start="2025-02-01", end="2025-03-31", basis="service_date",
         components=["alternative_energy", "delta_revenue", "distribution_uncollectible", "generation_reconciliation",
                     "pipp_uncollectible", "nondistribution_uncollectible", "non_market_transmission",
                     "phase_in_recovery", "residential_heating_recovery", "legacy_generation", "vegetation_management"],
         assumed_values=dict(aer=-.000167, drr_rs=.000006, drr_gs=.000005, dun=.000409, gcr=.003073,
             pur=.000030, ndu=.000483, nmb_rs_usd_per_kwh=.021982, nmb_gs_usd_per_kw=6.2252,
             pir=.000436, rer_rs=.003541, vmc_rs_usd_per_kwh=0., vmc_gs_usd_per_kw=0., lgr_rs_usd_per_month=1.50, lgr_gs_usd_per_kwh=.0018007),
         explanation="Assume remaining January quarterly riders continue through March31 after the ESP-IV return. Do not retain ESP-V vegetation/storm charges; base/tax/CRC/USF terms use the retained filed rules.",
         sources=[BOOK+"OE-2024-Electric-Service.pdf", TESTIMONY+"Testimony-Dhara-Patel.pdf"]),
    dict(id="OE25-FEB-DCR", kind="rate", start="2025-02-01", end="2025-05-31", basis="bill_date",
         components=["delivery_capital"], assumed_values=dict(rs_usd_per_kwh=.009711, gs_usd_per_kw=3.2608),
         explanation="Use February current-rate DCR from testimony for bills dated February–May, assuming no intervening change. Apply ESP-IV kWh/kW charges, not January ESP-V distribution percentages.",
         sources=[TESTIMONY+"Testimony-Brandon-McMillen.pdf", TESTIMONY+"Testimony-Dhara-Patel.pdf"]),
    dict(id="OE25-LGR12", kind="rate", start="2025-07-01", end="2025-08-13", basis="service_date",
         components=["legacy_generation"], assumed_values=dict(rs_usd_per_month=1.50, gs_usd_per_kwh=.0018007),
         explanation="Assume January LGR11 rates continue for July1–August13 because LGR12 is missing. Apply the filed zero LGR rate from August14.",
         sources=[BOOK+"OE-2024-Electric-Service.pdf", BOOK+"OE-2025-Electric-Service.pdf"]),
    dict(id="OE25-AUGUST-LGR-ALLOCATION", kind="billing_rule", start="2025-08-14", end="2025-08-14", basis="crossing_service_date",
         customer_class="RS", components=["legacy_generation"],
         assumed_values=dict(rule="monthly LGR multiplied by local service-day share before August14; no physical-hour weighting"),
         explanation="For an RS cycle crossing August14, allocate the fixed monthly LGR by local service days at each rate. This is an explicit study approximation, not a verified utility allocation rule. GS LGR remains volumetric; SGF uses bill date.",
         sources=[BOOK+"OE-2025-Electric-Service.pdf"]),
]


def rates_on(day, verified):
    """Only missing2025 intersections; caller keeps all verified dates intact."""
    if "2025-02-01" <= day <= "2025-03-31":
        return {**verified("2025-01-01"), **deepcopy(FEBRUARY)}
    if "2025-04-01" <= day <= "2025-05-31":
        rates = verified("2025-06-01")
        january = verified("2025-01-01")
        rates.update(supply_energy=january["supply_energy"], supply_capacity=january["supply_capacity"],
                     dcr=FEBRUARY["dcr"])
        return rates
    if "2025-07-01" <= day <= "2025-08-13":
        rates = verified("2025-08-14")
        january = verified("2025-01-01")
        rates.update(lgr=january["lgr"], sgf=january["sgf"])
        return rates
    raise ValueError("Provisional assumptions cover only the declared missing2025 Ohio Edison windows.")


def evidence(index, account):
    """Return only assumptions actually used, with their dates and values."""
    dates = sorted(set(d.isoformat() for d in index.date))
    used = []
    if account.get("rate_evidence_mode", "verified") == "provisional_2025":
        for item in ASSUMPTIONS:
            if item.get("customer_class") not in (None, account["tariff"]):
                continue
            basis = item["basis"]
            applies = (item["start"] <= account["bill_date"] <= item["end"] if basis == "bill_date" else
                       dates[0] < item["start"] <= dates[-1] if basis == "crossing_service_date" else
                       any(item["start"] <= d <= item["end"] for d in dates))
            if applies:
                used.append(deepcopy(item))
    return dict(rate_evidence_status="provisional" if used else "verified",
                assumption_model=MODEL if used else None, rate_assumptions=used,
                objective_scope="provisional_modeled_bill" if used else "complete_utility_bill")
