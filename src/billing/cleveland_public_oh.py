"""Cleveland Public Power municipal schedules. Monthly complete bills await dated riders."""

UTILITY = "cleveland_public_power_ohio"
TIMEZONE = "America/New_York"
PLANS = {"523.02": ("Residential", "residential"), "523.03": ("Small Commercial", "commercial")}
CODE = "https://codelibrary.amlegal.com/codes/cleveland/latest/cleveland_oh/"
SOURCES = [CODE+"0-0-0-27146", CODE+"0-0-0-27163", CODE+"0-0-0-27435",
           "https://www.cpp.org/Billing/Rate-Schedule",
           "https://www.cpp.org/sites/default/files/2024-12/CPP_UnderstandingYourBillBrochure_2024_R5_Interior_BillImage.pdf",
           "https://codes.ohio.gov/ohio-revised-code/section-5727.81"]
REASON = ("Cleveland Public Power lacks verified class-specific monthly power supply recovery and environmental "
          "adjustments for complete 2025–2026 cycles. The utility's undated web factors and illustrative residential bill "
          "cannot establish a dated final bill.")
# Dollars/kWh, first and subsequent blocks. Energy follows the period END (June–October summer).
BASE = {
    "523.02": {"first_kwh": 1000, 2025: {"summer": (.0888, .0863), "winter": (.0752, .0405)},
               2026: {"summer": (.0970, .0943), "winter": (.0821, .0443)}},
    "523.03": {"first_kwh": 7500, 2025: {"summer": (.0779, .0457), "winter": (.0675, .0355)},
               2026: {"summer": (.0851, .0499), "winter": (.0737, .0387)}},
}


def defaults(plan_id="523.02"):
    if plan_id not in PLANS:
        raise ValueError("Select Cleveland Public Power 523.02 or 523.03.")
    return dict(tariff=plan_id, supply="bundled", export_mode="none", rate_evidence_mode="verified")


def catalog():
    return [dict(id=p, label=f"Cleveland Public Power §{p} {name}", customer_class=kind, status="unsupported",
                 reason=REASON, billing_supported=False, dispatch_supported=False, coverage=[],
                 coverage_gaps=[dict(start="2025-01-01", end="2026-12-31", reason=REASON)],
                 base_effective_start="2025-01-01", voltage="secondary", interval_minutes=[15],
                 supply_arrangements=["bundled"], equipment_modes=[], solar_modes=[], account_fields=[], sources=list(SOURCES),
                 eligibility=("Individually metered primarily domestic service." if kind == "residential" else
                              "Ordinary metered commercial installation below 30 kW monthly demand. At 30 kW or more the large-commercial schedules apply."),
                 limitations=[REASON, "Meter combinations, special service, homestead adjustments, and export settlement require separate evidence."])
            for p, (name, kind) in PLANS.items()]


def validate_account(account, index, equipment=None):
    raise ValueError(REASON)


def charge_lines(index, imports, exports, account, *, math, state=None):
    raise ValueError(REASON)
