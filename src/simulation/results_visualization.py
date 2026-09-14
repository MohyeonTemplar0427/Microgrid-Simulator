"""Render scenario comparisons without depending on Tk or a plotting backend."""

import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from ..profiles import EQUIPMENT_POWER_STAGE_COLUMNS, POWER_STAGE_COLUMNS


COMPARISON_METRICS = {
    "Total operating cost ($)": "total_explicit_cost",
    "Emissions (kgCO2)": "emissions_kgCO2",
    "Peak grid import (kW)": "peak_grid_import_kw",
    "Carbon-adjusted operating cost ($)": "carbon_adjusted_operating_cost",
    "Grid import energy (kWh)": "pcc_grid_import_energy_kWh",
    "Average daily equivalent full cycles": "average_daily_efc",
}


def available_comparison_metrics(comparison):
    """Offer only metrics containing at least one finite observation."""
    return tuple(
        label for label, column in COMPARISON_METRICS.items()
        if column in comparison
        and np.isfinite(pd.to_numeric(comparison[column], errors="coerce")).any()
    )


def draw_comparison(figure: Figure, comparison, metric: str) -> None:
    """Replace a figure with a horizontal comparison, preserving row order."""
    figure.clear()
    axis = figure.add_subplot(111)
    column = COMPARISON_METRICS[metric]
    values = pd.to_numeric(comparison[column], errors="coerce").to_numpy(dtype=float)
    labels = comparison["scenario"].astype(str).tolist()
    positions = np.arange(len(labels))
    finite = np.isfinite(values)
    colors = ["#64748b" if label == "no_battery" else "#167d9a" for label in labels]
    bars = axis.barh(positions[finite], values[finite], color=np.array(colors)[finite])
    axis.bar_label(bars, labels=[f"{value:,.2f}" for value in values[finite]], padding=5)
    for position in positions[~finite]:
        axis.text(0, position, "Unavailable", va="center", color="#64748b")
    axis.set_yticks(positions, labels=labels)
    axis.invert_yaxis()
    axis.set_xlabel(metric)
    axis.set_title("Scenario comparison")
    axis.axvline(0, color="#64748b", linewidth=0.8)
    axis.set_axisbelow(True)
    axis.grid(axis="x", alpha=0.2)
    axis.margins(x=0.22)
    axis.spines[["top", "right"]].set_visible(False)


def available_pv_power_stages(diagnostics: pd.DataFrame | None) -> tuple[str, ...]:
    """Return model-defined PV power stages present in a diagnostic frame."""

    if diagnostics is None or diagnostics.empty:
        return ()
    model_columns = (
        EQUIPMENT_POWER_STAGE_COLUMNS
        if "pv_dc_at_inverter_input_kw" in diagnostics
        else POWER_STAGE_COLUMNS
    )
    return tuple(
        column for column in model_columns
        if column != "timestamp" and column in diagnostics
    )


def draw_pv_power_stages(figure: Figure, diagnostics: pd.DataFrame) -> None:
    """Plot the Phase 1 or Phase 2 power chain over the analysis horizon."""

    columns = available_pv_power_stages(diagnostics)
    if not columns:
        raise ValueError("No PV power-stage diagnostics are available.")

    figure.clear()
    axis = figure.add_subplot(111)
    timestamps = pd.to_datetime(diagnostics["timestamp"])
    for column in columns:
        axis.plot(
            timestamps,
            pd.to_numeric(diagnostics[column], errors="coerce"),
            label=column.removeprefix("pv_").replace("_kw", "").replace("_", " "),
            linewidth=1.4,
        )
    axis.set_ylabel("Power (kW)")
    axis.set_title("PV model power stages")
    axis.grid(alpha=0.2)
    axis.legend(loc="best", fontsize=8)
    axis.spines[["top", "right"]].set_visible(False)
