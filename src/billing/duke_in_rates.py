"""Duke Indiana filed prices and separately identified 2025 study proxies.

Filed dollars, not wholesale market signals. Only the intersection of verified
component windows is verified. Explicit provisional mode never extends that
evidence label. See the source manifest and assumptions for page/hash evidence.
"""
from copy import deepcopy
from datetime import date

PLANS = ("RS", "RS-TOU", "CS", "CS-TOU")
THROUGH = "2026-10-24"
COVERAGE = (("2025-03-01", "2025-03-31"),)
PROVISIONAL_MODEL = "duke_indiana_2025_provisional_v1"
SOURCES = [
    "https://iurc.portal.in.gov/_entity/sharepointdocumentlocation/9b61cc1c-c6e7-ef11-be20-001dd80b8c52/bb9c6bba-fd52-45ad-8e64-a444aef13c39?file=46038_DEI_Step%201%20Compliance%20Filing_Attachment%20C_Redline%20and%20Clean%20Tariff_020725.pdf",
    "https://iurc.portal.in.gov/_entity/sharepointdocumentlocation/245d050d-5bde-ef11-8eea-001dd808c9d7/bb9c6bba-fd52-45ad-8e64-a444aef13c39?file=ord_46038_012925.pdf",
    "https://www.duke-energy.com/home/billing/rates/electric-tariff",
    "https://www.in.gov/oucc/electric/key-cases-by-utility/duke-energy-rates/duke-energy-rate-case",
    "https://www.in.gov/oucc/electric/tips-and-publications/understanding-electric-rates/",
    "https://www.in.gov/dor/resources/tax-rates-and-reports/rates-fees-and-penalties/corporate-sales-tax-history/",
    "https://www.in.gov/dor/about/news-publications/our-team/tax-types/",
    "https://www.duke-energy.com/business/billing/rates/new-2025-tou-rates-dei",
    "https://iurc.portal.in.gov/_entity/sharepointdocumentlocation/a20b062d-56f3-ee11-904c-001dd80b3def/bb9c6bba-fd52-45ad-8e64-a444aef13c39?file=46038_DEI_Petitioner%27s+Ex.+7+-+Flick+Direct_040424.pdf",
    "https://www.in.gov/iurc/files/ord_38707FAC142_123024.pdf",
    "https://www.in.gov/iurc/files/ord_38707FAC143_032625.pdf",
    "https://www.in.gov/iurc/files/ord_38707FAC144_062625.pdf",
    "https://secure.in.gov/iurc/files/ord_38707FAC145_093025.pdf",
    "https://www.in.gov/iurc/files/ord_UA_082025.pdf",
    "https://www.in.gov/iurc/files/ord_UA_121824.pdf",
    "https://iurc.portal.in.gov/_entity/sharepointdocumentlocation/9cc5b793-3bb3-ef11-b8e9-001dd808c9d7/bb9c6bba-fd52-45ad-8e64-a444aef13c39?file=45803+DSM-1_DEI_Submission+of+Final+Tariffs_120524.pdf",
    "https://www.in.gov/iurc/files/ord_45803DSM2_100825.pdf",
    "https://www.in.gov/iurc/files/ord_45647TDSIC5_040826.pdf",
    "https://www.in.gov/iurc/files/ord_42061ECR43_062625.pdf",
    "https://www.in.gov/iurc/files/ord_44932REP7_060425.pdf",
    "https://secure.in.gov/iurc/files/2025-Electric-Residential-Bill-Survey-UPDATED.pdf",
    "https://iurc.portal.in.gov/_entity/sharepointdocumentlocation/cf96af5e-6324-f011-998a-001dd80846ac/bb9c6bba-fd52-45ad-8e64-a444aef13c39?file=46038%20_DEI_Duke%20Response%20to%20OUCC%20and%20Industrial%20Group%27s%20Request%20for%20Ruling_04282025.pdf",
]

BASE = {
    "RS": dict(customer=13.70, bounds=(300., 1000.), energy=(.186556, .135777, .123051)),
    "RS-TOU": dict(customer=13.70, bounds=(), energy=(.214198, .142799, .085679)),
    "CS": dict(customer=13.91, bounds=(300., 1000., 2500.), energy=(.178612, .165677, .150517, .122691)),
    "CS-TOU": dict(customer=13.91, bounds=(), energy=(.169081, .148754, .097014)),
}
# February27 compliance reset values, pages236–303. Do not add the earlier
# January DSM/LC values: those costs were partly moved into the new base rates.
RIDERS = {
    "fuel": (-.001521, -.001521),
    "environmental": (.003339, .003699),
    "tdsic": (.002259, .001874),
    "energy_efficiency": (.002137, .001669),
    "credits_adjustment": (-.014131, -.013589),
    "rto_non_fuel": (-.000105, -.000073),
    "reliability": (.000984, .001010),
    "federal_mandate": (0., 0.),
    "renewable_projects": (.000038, .000028),
    "load_control": (-.000206, -.000215),
}

# Prior ordinary base observations in the compliance redlines, independently
# corroborated by the current-price columns of Flick's 2024 direct exhibit.
# They do not establish the missing pre-reset rider composite.
PRE_BASE = {
    "RS": dict(customer=10.54, bounds=(300., 1000.), energy=(.148799, .108297, .098147)),
    "CS": dict(customer=10.70, bounds=(300., 1000., 2500.), energy=(.140571, .130391, .118460, .096560)),
}
PRE_VERIFIED_RIDERS = {
    "fuel": (.005902, .005902),
    "energy_efficiency": (.003851, .003882),
    "credits_adjustment": (-.007166, -.006399),
    "load_control": (.001406, .001446),
    "federal_mandate": (0., 0.),
}

# Every amount below is an identified proxy, not a newly verified tariff.
# Actual approved later fuel/September credit values are selected separately.
ASSUMPTIONS = [
    dict(id="DEI25-PRE-RESET-RIDERS", kind="rate", start="2025-01-01", end="2025-02-26", basis="service_date",
         components=["environmental", "tdsic", "rto_non_fuel", "reliability", "renewable_projects", "indiana_sales_tax"],
         assumed_values={k: dict(RS=RIDERS[k][0], CS=RIDERS[k][1]) for k in
                         ("environmental", "tdsic", "rto_non_fuel", "reliability", "renewable_projects")},
         explanation="Backcast the same customer class's February27 reset factors for missing pre-reset riders62/65/68/70/73. These are scenario proxies: the reset reallocated costs between base rates and riders, so this backcast may misstate recovery even with the correct old base and verified old60/66/67/74. It is not an official January/February composite.",
         sources=[SOURCES[0], SOURCES[1]]),
    dict(id="DEI25-FAC143-SIGN", kind="rate", start="2025-04-01", end="2025-06-01", basis="billing_month",
         components=["fuel", "indiana_sales_tax"], assumed_values=dict(usd_per_kwh=-.004801),
         explanation="Use negative0.004801 from the order's adjusted fuel0.029577 minus base fuel0.034378, corroborated by its stated decrease and the next order's increase. The printed FAC143 result omits the minus sign; no signed corrected final tariff has been recovered. This sign choice remains provisional.",
         sources=[SOURCES[10], SOURCES[11]]),
    dict(id="DEI25-JULY-RIDER-CONTINUITY", kind="rate", start="2025-07-01", end="2025-12-01", basis="billing_month",
         components=["environmental", "renewable_projects", "indiana_sales_tax"],
         assumed_values={k: dict(RS=RIDERS[k][0], CS=RIDERS[k][1]) for k in ("environmental", "renewable_projects")},
         explanation="Hold March's same-class62/73 factors for July–December. Superseding ECR43 and REP7 approvals are known, but their exact class sheets are missing. The held factors are sensitivity assumptions, not a claim that approved prices were unchanged; later published residential examples show differences.",
         sources=[SOURCES[0], SOURCES[18], SOURCES[19], SOURCES[20]]),
    dict(id="DEI25-DECEMBER-CREDIT67", kind="rate", start="2025-12-01", end="2025-12-01", basis="billing_month",
         components=["credits_adjustment", "indiana_sales_tax"], assumed_values=dict(RS=-.013516, CS=-.013232),
         explanation="Hold the approved September credit67 factors through December despite unresolved temporary wholesale-credit expiration and the missing dated December sheet. This may overstate the credit; no expiration factor is invented.",
         sources=[SOURCES[13]]),
    dict(id="DEI25-ORDINARY-BASE-CONTINUITY", kind="billing_rule", start="2025-05-19", end="2025-12-31", basis="service_date",
         components=["customer", "energy", "indiana_sales_tax"],
         assumed_values=dict(rule="Retain the filed February27 ordinary RS/CS base schedules through2025"),
         explanation="Assume later2025 ordinary RS/CS base prices remain the February27 schedules. The rehearing response describes LLF/HLF amendments, but the final May compliance package has not been recovered; no change to an ordinary account is invented.",
         sources=[SOURCES[0], SOURCES[21]]),
    dict(id="DEI25-BILL-MONTH-ALLOCATION", kind="billing_rule", start="2025-01-01", end="2025-12-31", basis="crossing_calendar_month",
         components=list(RIDERS)+["indiana_sales_tax"],
         assumed_values=dict(rule="Use designated final-service-day billing month for all volumetric rider factors over one complete regular cycle; no day-share blending"),
         explanation="For a complete regular26–34day cycle spanning civil months, use its explicit designated billing month for the whole-cycle riders. Individual billed-month clocks are documented, but their joint historical-cycle allocation is not fully verified. Base prices follow service dates; a February27 base-crossing cycle still rejects.",
         sources=[SOURCES[0], SOURCES[9], SOURCES[11], SOURCES[12], SOURCES[13]]),
]


def provisional_coverage(plan):
    return [dict(start="2025-02-27" if plan.endswith("-TOU") else "2025-01-01", end="2025-12-31")]


def service_rates(day, plan, *, billing_month=None, mode="verified"):
    key = day.isoformat() if type(day) is date else day
    try:
        if not isinstance(key, str) or date.fromisoformat(key).isoformat() != key:
            raise ValueError
    except ValueError as exc:
        raise ValueError("Use an exact ISO Duke Indiana service date.") from exc
    if plan not in PLANS:
        raise ValueError("Choose Duke Indiana RS, RS-TOU, CS or CS-TOU.")
    if mode not in ("verified", "provisional_2025"):
        raise ValueError("Choose verified or explicitly accepted provisional_2025 Duke Indiana rates.")
    month = key[:7]+"-01" if billing_month is None else billing_month
    try:
        if (not isinstance(month, str) or date.fromisoformat(month).isoformat() != month
                or date.fromisoformat(month).day != 1):
            raise ValueError
    except ValueError as exc:
        raise ValueError("Use a separate exact first-of-month Duke Indiana billing designation.") from exc
    verified = any(start <= key <= end for start, end in COVERAGE) and month == "2025-03-01"
    if not verified and mode == "provisional_2025":
        if not "2025-01-01" <= key <= "2025-12-31" or not "2025-01-01" <= month <= "2025-12-01":
            raise ValueError("Duke Indiana provisional coverage is calendar2025 only; no2026 extrapolation.")
        if plan.endswith("-TOU") and key < "2025-02-27":
            raise ValueError("Duke Indiana RS/CS TOU has no pre-February27 coverage; do not backcast a new option.")
        return _provisional_rates(key, plan, month)
    if not any(start <= key <= end for start, end in COVERAGE):
        raise ValueError("Duke Indiana complete-rate coverage is March2025 only; other2025/2026 dates need their verified base and rider histories.")
    if month != "2025-03-01":
        raise ValueError("Duke Indiana complete-rate coverage requires a verified March2025 billing designation; service dates alone do not select billed rider factors.")
    residential = plan.startswith("RS")
    return {**BASE[plan], **{name: value[not residential] for name, value in RIDERS.items()},
            "base_version": "IURC16 original, February27,2025",
            "rider_version": "February27,2025 base-case reset; verified March2025 service and billing designation",
            "designated_billing_month": month}


def _provisional_rates(day, plan, month):
    cls = int(not plan.startswith("RS"))
    before = day < "2025-02-27"
    base = PRE_BASE[plan] if before else BASE[plan]
    riders = {k: v[cls] for k, v in RIDERS.items()}
    if before:
        riders.update({k: v[cls] for k, v in PRE_VERIFIED_RIDERS.items()})
    else:
        if month >= "2025-10-01":
            riders["fuel"] = .000372
        elif month >= "2025-07-01":
            riders["fuel"] = .004042
        elif month >= "2025-04-01":
            riders["fuel"] = -.004801
        if month >= "2025-09-01":
            riders["credits_adjustment"] = (-.013516, -.013232)[cls]
    return {**base, **riders,
            "base_version": "Prior ordinary IURC15 base observations" if before else "IURC16 original, February27,2025",
            "rider_version": "Explicit provisional2025 composite; inspect component assumptions and dated verified observations",
            "designated_billing_month": month}


def evidence(index, account):
    """Only assumptions actually used; selection/acceptance is checked upstream."""
    dates = sorted(set(d.isoformat() for d in index.date))
    month = account["billing_month"]
    used = []
    if account.get("rate_evidence_mode", "verified") == "provisional_2025":
        for item in ASSUMPTIONS:
            basis = item["basis"]
            applies = (item["start"] <= month <= item["end"] if basis == "billing_month" else
                       dates[0][:7] != dates[-1][:7] if basis == "crossing_calendar_month" else
                       any(item["start"] <= d <= item["end"] for d in dates))
            if applies:
                used.append({**deepcopy(item), "applied_service_start": dates[0],
                             "applied_service_end": dates[-1], "designated_billing_month": month})
    return dict(rate_evidence_status="provisional" if used else "verified",
                assumption_model=PROVISIONAL_MODEL if used else None,
                rate_assumptions=used,
                objective_scope="provisional_modeled_bill" if used else "complete_utility_bill")
