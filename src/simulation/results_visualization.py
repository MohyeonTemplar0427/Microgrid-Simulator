"""Render scenario comparisons without depending on Tk or a plotting backend."""

import numpy as np
import pandas as pd
from matplotlib.figure import Figure


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
