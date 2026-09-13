"""Generate docs/PGE_Tariff_Reference.md from the registered tariffs.

The reference is generated rather than written by hand so it cannot drift
from the rates the billing code actually applies. Re-run after adding or
re-versioning a tariff:

    /usr/local/bin/python3 tools/generate_tariff_reference.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from src.billing import get_tariff, supported_tariffs  # noqa: E402
from src.billing.tariffs import DemandChargeBasis  # noqa: E402

OUTPUT_PATH = REPOSITORY_ROOT / "docs" / "PGE_Tariff_Reference.md"

# Display order: smallest schedule first, each family's options after its base.
TARIFF_ORDER = (
    "pge_b1_secondary_single_phase_bundled_2026_03_01",
    "pge_b1_secondary_polyphase_bundled_2026_03_01",
    "pge_b6_secondary_single_phase_bundled_2026_03_01",
    "pge_b6_secondary_polyphase_bundled_2026_03_01",
    "pge_b10_secondary_bundled_2026_03_01",
    "pge_b19_secondary_mandatory_bundled_2026_03_01",
    "pge_b19_secondary_voluntary_bundled_2026_03_01",
    "pge_b19_secondary_option_r_bundled_2026_03_01",
    "pge_b19_secondary_option_s_bundled_2026_03_01",
    "pge_b20_secondary_bundled_2026_03_01",
    "pge_b20_secondary_option_r_bundled_2026_03_01",
    "pge_b20_secondary_option_s_bundled_2026_03_01",
)

ELIGIBILITY = {
    "pge_b1_secondary_single_phase_bundled_2026_03_01": "Under 75 kW",
    "pge_b1_secondary_polyphase_bundled_2026_03_01": "Under 75 kW",
    "pge_b6_secondary_single_phase_bundled_2026_03_01": "Under 75 kW",
    "pge_b6_secondary_polyphase_bundled_2026_03_01": "Under 75 kW",
    "pge_b10_secondary_bundled_2026_03_01": "75-499 kW (voluntary below 75 kW)",
    "pge_b19_secondary_mandatory_bundled_2026_03_01": "500-999 kW",
    "pge_b19_secondary_voluntary_bundled_2026_03_01": "Opt-in below 500 kW",
    "pge_b19_secondary_option_r_bundled_2026_03_01": "B-19 accounts with renewables",
    "pge_b19_secondary_option_s_bundled_2026_03_01": "B-19 accounts with storage",
    "pge_b20_secondary_bundled_2026_03_01": "1,000 kW or more",
    "pge_b20_secondary_option_r_bundled_2026_03_01": "B-20 accounts with renewables",
    "pge_b20_secondary_option_s_bundled_2026_03_01": "B-20 accounts with storage",
}

HOUR_LABELS = {
    (16, 21): "16:00-21:00",
    (14, 16): "14:00-16:00",
    (21, 23): "21:00-23:00",
    (9, 14): "09:00-14:00",
    (0, 0): "all remaining hours",
}

BASIS_LABELS = {
    DemandChargeBasis.MAXIMUM: "highest interval demand in the billing month",
    DemandChargeBasis.PEAK_PERIOD: "highest demand inside peak hours",
    DemandChargeBasis.PART_PEAK_PERIOD: "highest demand inside part-peak hours",
}


def hours_of(period) -> str:
    label = HOUR_LABELS.get((period.start_hour, period.end_hour))
    if label is None:
        label = f"{period.start_hour:02d}:00-{period.end_hour:02d}:00"
    if period.months:
        months = ", ".join(
            ("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())[m - 1]
            for m in sorted(period.months)
        )
        label += f" ({months} only)"
    return label


def season_of(period) -> str:
    return period.season.value.capitalize() if period.season else "All year"



ENERGY_COLUMNS = (
    ("summer_peak", "Summer peak", "16-21"),
    ("summer_part_peak", "Summer part-peak", "14-16, 21-23"),
    ("summer_off_peak", "Summer off-peak", "rest"),
    ("winter_peak", "Winter peak", "16-21"),
    ("winter_super_off_peak", "Winter super-off-peak", "9-14, Mar-May"),
    ("winter_off_peak", "Winter off-peak", "rest"),
)

DEMAND_COLUMNS = (
    ("maximum_demand", "Maximum"),
    ("peak_period_demand_summer", "Summer peak-period"),
    ("part_peak_period_demand_summer", "Summer part-peak-period"),
    ("peak_period_demand_winter", "Winter peak-period"),
)


def energy_rate_columns(tariff) -> dict[str, float | None]:
    """Collapse the two part-peak blocks, which always share one rate."""

    rates = {period.name: period.rate_per_kWh for period in tariff.tou_periods}

    afternoon = rates.get("summer_part_peak_afternoon")
    evening = rates.get("summer_part_peak_evening")
    if afternoon is not None and evening is not None:
        if abs(afternoon - evening) > 1e-12:
            raise SystemExit(
                f"{tariff.tariff_id}: the afternoon and evening part-peak "
                "blocks no longer share a rate, so they cannot share one "
                "column. Split them in ENERGY_COLUMNS."
            )
        rates["summer_part_peak"] = afternoon

    return {key: rates.get(key) for key, _, _ in ENERGY_COLUMNS}


def cell(value: float | None, places: int) -> str:
    return "—" if value is None else f"{value:.{places}f}"


def comparison_tables() -> list[str]:
    lines = [
        "### Energy rates side by side ($/kWh)",
        "",
        "The two summer part-peak blocks (afternoon and evening) always carry "
        "the same rate, so they share one column. A dash means the schedule "
        "has no such period — B-1 and B-6 are energy-only schedules, and B-6 "
        "has no part-peak block at all.",
        "",
    ]

    header = "| Schedule | " + " | ".join(
        f"{label}<br><sub>{hours}</sub>" for _, label, hours in ENERGY_COLUMNS
    ) + " |"
    lines += [header, "| --- | " + " | ".join("---:" for _ in ENERGY_COLUMNS) + " |"]

    for tariff_id in TARIFF_ORDER:
        tariff = get_tariff(tariff_id)
        values = energy_rate_columns(tariff)
        lines.append(
            f"| {short_name(tariff_id)} | "
            + " | ".join(cell(values[key], 5) for key, _, _ in ENERGY_COLUMNS)
            + " |"
        )

    lines += [
        "",
        "### Demand charges side by side ($/kW)",
        "",
        "Components apply together, so a summer peak-hour kilowatt on B-19 or "
        "B-20 can attract three of them at once. A dash means the schedule "
        "does not bill that component; both Option R schedules price winter "
        "peak-period demand at zero.",
        "",
        "| Schedule | "
        + " | ".join(label for _, label in DEMAND_COLUMNS)
        + " | Total |",
        "| --- | " + " | ".join("---:" for _ in DEMAND_COLUMNS) + " | ---: |",
    ]

    for tariff_id in TARIFF_ORDER:
        tariff = get_tariff(tariff_id)
        rates = {c.name: c.rate_per_kW for c in tariff.demand_charges}
        total = sum(rates.values())
        lines.append(
            f"| {short_name(tariff_id)} | "
            + " | ".join(cell(rates.get(key), 2) for key, _ in DEMAND_COLUMNS)
            + f" | **{total:.2f}** |"
        )

    lines.append("")
    return lines


SHORT_NAMES = {
    "pge_b1_secondary_single_phase_bundled_2026_03_01": "B-1 single-phase",
    "pge_b1_secondary_polyphase_bundled_2026_03_01": "B-1 polyphase",
    "pge_b6_secondary_single_phase_bundled_2026_03_01": "B-6 single-phase",
    "pge_b6_secondary_polyphase_bundled_2026_03_01": "B-6 polyphase",
    "pge_b10_secondary_bundled_2026_03_01": "B-10",
    "pge_b19_secondary_mandatory_bundled_2026_03_01": "B-19 mandatory",
    "pge_b19_secondary_voluntary_bundled_2026_03_01": "B-19 voluntary",
    "pge_b19_secondary_option_r_bundled_2026_03_01": "B-19 Option R",
    "pge_b19_secondary_option_s_bundled_2026_03_01": "B-19 Option S",
    "pge_b20_secondary_bundled_2026_03_01": "B-20",
    "pge_b20_secondary_option_r_bundled_2026_03_01": "B-20 Option R",
    "pge_b20_secondary_option_s_bundled_2026_03_01": "B-20 Option S",
}


def short_name(tariff_id: str) -> str:
    return SHORT_NAMES.get(tariff_id, tariff_id)


def render_tariff(tariff_id: str) -> list[str]:
    tariff = get_tariff(tariff_id)
    lines: list[str] = [f"## {tariff.name}", ""]

    charge = (
        f"${tariff.daily_customer_charge:,.5f} per meter per day"
        if tariff.daily_customer_charge is not None
        else f"${tariff.monthly_customer_charge:,.5f} per meter per month"
    )
    monthly = (
        f" (about ${tariff.daily_customer_charge * 30:,.2f} over 30 days)"
        if tariff.daily_customer_charge is not None
        else ""
    )

    lines += [
        f"- **Tariff id**: `{tariff.tariff_id}`",
        f"- **Eligibility**: {ELIGIBILITY.get(tariff_id, 'see the schedule')}",
        f"- **Service**: {tariff.service_voltage_class.value} voltage, "
        f"{tariff.service_type.value}, {tariff.customer_class.value}",
        f"- **Customer charge**: {charge}{monthly}",
        f"- **Effective**: {tariff.effective_start.isoformat()} "
        f"(version `{tariff.version}`)",
        f"- **Source**: <{tariff.source_url}>",
        "",
        "### Energy rates",
        "",
        "| Period | Season | Hours | $/kWh |",
        "| --- | --- | --- | ---: |",
    ]

    for period in sorted(
        tariff.tou_periods,
        key=lambda p: (season_of(p), -p.priority, p.start_hour),
    ):
        lines.append(
            f"| {period.name} | {season_of(period)} | {hours_of(period)} "
            f"| {period.rate_per_kWh:.5f} |"
        )

    lines += ["", "### Demand charges", ""]
    if not tariff.demand_charges:
        lines += [
            "None. This schedule bills energy and the customer charge only, "
            "so the bill never depends on the monthly peak.",
            "",
        ]
    else:
        lines += [
            "| Component | Season | Measured over | $/kW |",
            "| --- | --- | --- | ---: |",
        ]
        total = 0.0
        for component in tariff.demand_charges:
            season = (
                component.season.value.capitalize()
                if component.season
                else "All year"
            )
            total += component.rate_per_kW
            lines.append(
                f"| {component.name} | {season} | "
                f"{BASIS_LABELS[component.basis]} | "
                f"{component.rate_per_kW:.2f} |"
            )
        lines += [
            f"| **Total if every component peaks together** | | | "
            f"**{total:.2f}** |",
            "",
            "Components apply together on the same bill. A summer peak-hour "
            "kilowatt can attract the maximum-demand, peak-period and "
            "part-peak-period charges at once.",
            "",
        ]

    lines += [
        "### Export compensation",
        "",
        f"{tariff.export_rule.note}",
        "",
        "### Notes",
        "",
        f"{tariff.notes}",
        "",
    ]
    return lines


def build_document() -> str:
    registered = set(supported_tariffs())
    missing = registered - set(TARIFF_ORDER)
    if missing:
        raise SystemExit(
            "TARIFF_ORDER is missing registered tariffs: "
            f"{sorted(missing)}. Add them and re-run."
        )

    lines = [
        "# PG&E tariff reference",
        "",
        "**Generated file — do not edit by hand.** Regenerate with:",
        "",
        "```bash",
        "/usr/local/bin/python3 tools/generate_tariff_reference.py",
        "```",
        "",
        "Every rate below is read from the tariff registry in "
        "`src/billing/pge_tariffs.py`, so this document and the numbers the "
        "billing code applies cannot disagree. Rates are transcribed from "
        "PG&E's published tariff sheets and are valid for the stated "
        "effective date only; see "
        "[Microgrid_Backend_Architecture.md](Microgrid_Backend_Architecture.md) "
        "for why tariffs are versioned data rather than editable constants.",
        "",
        "All schedules below are **secondary voltage, bundled service**. "
        "Primary and Transmission voltage classes, Peak Day Pricing, "
        "power-factor adjustments and standby charges are not modelled.",
        "",
        "## How the plans compare",
        "",
        "The families form a progression: as an account grows, the fixed and "
        "demand charges rise while the energy spread narrows. A battery "
        "earns its value from the energy spread on the small schedules and "
        "from peak reduction on the large ones.",
        "",
        "Spread is summer peak minus summer off-peak — the per-kWh margin "
        "a battery captures by shifting one kilowatt-hour out of the peak "
        "window. It is the only derived figure in these tables; every "
        "other number is read straight from the registry. Winter rates and "
        "the part-peak blocks are in the next table.",
        "",
        "### Charges at a glance",
        "",
        "| Schedule | Eligibility | Customer $/day | Demand $/kW | Summer peak $/kWh | Summer off-peak $/kWh | Summer spread $/kWh |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    for tariff_id in TARIFF_ORDER:
        tariff = get_tariff(tariff_id)
        rates = {p.name: p.rate_per_kWh for p in tariff.tou_periods}
        spread = rates["summer_peak"] - rates["summer_off_peak"]
        demand_total = sum(c.rate_per_kW for c in tariff.demand_charges)
        lines.append(
            f"| {tariff.name} | {ELIGIBILITY.get(tariff_id, '')} "
            f"| {tariff.daily_customer_charge:,.5f} "
            f"| {demand_total:,.2f} "
            f"| {rates['summer_peak']:.5f} "
            f"| {rates['summer_off_peak']:.5f} "
            f"| {spread:.5f} |"
        )

    lines += [""]
    lines += comparison_tables()

    lines += [
        "Seasons are the same on every schedule: **summer is June 1 through "
        "September 30**, winter is October 1 through May 31. Every period "
        "applies *every day, including weekends and holidays* — none of "
        "these schedules distinguishes weekdays.",
        "",
        "---",
        "",
    ]

    for tariff_id in TARIFF_ORDER:
        lines += render_tariff(tariff_id)
        lines.append("---")
        lines.append("")

    lines += [
        "## Not modelled",
        "",
        "| Schedule | Why |",
        "| --- | --- |",
        "| B1-ST (B-1 storage option) | Its $7.86/kW demand charge is "
        "assessed 2:00 p.m.-11:00 p.m. only — the union of B-1's peak and "
        "part-peak blocks. `DemandChargeComponent` has no windowed basis, and "
        "modelling it as two components would take each maximum separately "
        "and sum them, overcharging. |",
        "| Primary and Transmission voltage classes | Rates are published for "
        "all three classes, but the modelled 480 V service is secondary. |",
        "| Agricultural schedules (AG-A1, AG-A2, AG-B, AG-C) | Keyed to "
        "annual operating hours, with flex-day options tied to specific "
        "weekdays. `TOUPeriod` has no day-of-week field. |",
        "| Peak Day Pricing | Event-driven, priced at $0.60-$0.90/kWh during "
        "events against a summer peak credit. Needs PG&E's event calendar. |",
        "| Export compensation (NEM, NBT) | Not part of any of these rate "
        "schedules. Configure a fixed or CSV export price in the surplus "
        "configuration instead. |",
        "",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(build_document())
    print(f"wrote {OUTPUT_PATH.relative_to(REPOSITORY_ROOT)}")
