"""Provide the guided desktop workflow for a complete microgrid study."""

from datetime import date
from decimal import Decimal, InvalidOperation
import json
import multiprocessing
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..billing import (
    PGE_B1_SECONDARY_POLYPHASE_BUNDLED,
    PGE_B1_SECONDARY_SINGLE_PHASE_BUNDLED,
    PGE_B6_SECONDARY_POLYPHASE_BUNDLED,
    PGE_B6_SECONDARY_SINGLE_PHASE_BUNDLED,
    PGE_B10_SECONDARY_BUNDLED,
    PGE_B19_SECONDARY_MANDATORY_BUNDLED,
    PGE_B20_SECONDARY_BUNDLED,
    PGE_B19_SECONDARY_VOLUNTARY_BUNDLED,
    PGE_B19_SECONDARY_OPTION_R_BUNDLED,
    PGE_B19_SECONDARY_OPTION_S_BUNDLED,
    PGE_B20_SECONDARY_OPTION_R_BUNDLED,
    PGE_B20_SECONDARY_OPTION_S_BUNDLED,
    get_tariff,
    supported_tariffs,
)
from ..signal_pipeline.price_sources import PRICE_MODES
from ..signal_pipeline.region_config import (
    get_region_config,
    supported_regions,
)
from ..dispatch.battery import Battery
from ..profiles import (
    NSRDB_API_KEY_ENV_VAR,
    NSRDB_EMAIL_ENV_VAR,
    NSRDBError,
    NSRDBRequest,
    cec_inverter_names,
    cec_module_names,
    fetch_nsrdb_weather,
    save_weather_csv,
    year_coverage_problem,
)
from ..timeseries.interval_table import build_interval_index
from .geocoding import GeocodingError, LocationSearch
from .interface_analysis import (
    build_analysis_details,
    build_equipment_pv_configuration,
    build_results_table,
    InterfaceAnalysisResult,
    RESULT_TABLE_COLUMNS,
    retail_tariff_ids_for_region,
    run_integrated_csv_analysis,
    run_live_api_analysis,
)
from .model_specifications import MicrogridSpecification
from .results_visualization import (
    available_comparison_metrics,
    draw_comparison,
    draw_pv_power_stages,
)


STRATEGY_LABELS = {
    "no_battery": "No-battery baseline",
    "rule_based": "Rule-based dispatch",
    "cost_optimal": "Cost optimization",
    "carbon_optimal": "Carbon optimization",
    "combined_optimal": "Combined optimization",
}

SOURCE_MODE_LABELS = {
    "live_api": "Live API data",
    "integrated_csv": "Import integrated CSV",
}

REGION_LABELS = {
    "caiso_np15": "Northern California — CAISO NP15",
    "ercot_houston_hub": "Texas — ERCOT Houston Hub",
    "pjm_western_hub": "PJM Western Hub — Direct API",
    "pjm_western_hub_gridstatus": (
        "PJM Western Hub — GridStatus.io"
    ),
}

PRICE_MODE_LABELS = {
    "wholesale_market": "Wholesale market price",
    "fixed_retail": "Fixed retail electricity price",
    "time_of_use": "Time-of-Use(TOU) tariff",
    "csv": "Import price profile from CSV",
}

TARIFF_LABELS = {
    "pge_b6_secondary_single_phase_bundled_2025_09_01": "PG&E B-6 — Single-Phase (Sep–Dec 2025)",
    "pge_b6_secondary_polyphase_bundled_2025_09_01": "PG&E B-6 — Polyphase (Sep–Dec 2025)",
    PGE_B1_SECONDARY_SINGLE_PHASE_BUNDLED.tariff_id: (
        "PG&E B-1 — Secondary Single-Phase Bundled"
    ),
    PGE_B1_SECONDARY_POLYPHASE_BUNDLED.tariff_id: (
        "PG&E B-1 — Secondary Polyphase Bundled"
    ),
    PGE_B6_SECONDARY_SINGLE_PHASE_BUNDLED.tariff_id: (
        "PG&E B-6 — Small General TOU (Single-Phase)"
    ),
    PGE_B6_SECONDARY_POLYPHASE_BUNDLED.tariff_id: (
        "PG&E B-6 — Small General TOU (Polyphase)"
    ),
    PGE_B10_SECONDARY_BUNDLED.tariff_id: (
        "PG&E B-10 — Secondary Bundled"
    ),
    PGE_B19_SECONDARY_MANDATORY_BUNDLED.tariff_id: (
        "PG&E B-19 — Secondary Mandatory Bundled"
    ),
    PGE_B20_SECONDARY_BUNDLED.tariff_id: (
        "PG&E B-20 — Large General TOU (Secondary)"
    ),
    PGE_B19_SECONDARY_VOLUNTARY_BUNDLED.tariff_id: (
        "PG&E B-19 — Voluntary (Secondary)"
    ),
    PGE_B19_SECONDARY_OPTION_R_BUNDLED.tariff_id: (
        "PG&E B-19 Option R — Renewables"
    ),
    PGE_B19_SECONDARY_OPTION_S_BUNDLED.tariff_id: (
        "PG&E B-19 Option S — Storage"
    ),
    PGE_B20_SECONDARY_OPTION_R_BUNDLED.tariff_id: (
        "PG&E B-20 Option R — Renewables"
    ),
    PGE_B20_SECONDARY_OPTION_S_BUNDLED.tariff_id: (
        "PG&E B-20 Option S — Storage"
    ),
}

from ..billing.cleanpowersf import CLEANPOWERSF_TARIFFS
from ..billing.hetch_hetchy import HETCH_HETCHY_TARIFFS
from ..billing.bay_area_cca import BAY_AREA_CCA_TARIFFS
TARIFF_LABELS.update({t.tariff_id: t.name for t in (*CLEANPOWERSF_TARIFFS, *HETCH_HETCHY_TARIFFS, *BAY_AREA_CCA_TARIFFS)})

LOAD_PROFILE_LABELS = {
    "constant": "Constant load",
    "synthetic": "Synthetic building profile",
}

# Step 2 separates three questions that an earlier single "PV profile source"
# selector ran together: how the available-PV profile is obtained, where the
# weather behind it comes from, and how the physical system is modelled. They
# are independent -- a named-equipment plant can be driven by an uploaded CSV
# or by a satellite retrieval -- so combining them produced a list that grew
# multiplicatively and hid the fact that only one axis was changing.

PV_PROFILE_METHOD_LABELS = {
    "capacity_factor_csv": "Capacity-factor CSV",
    "weather": "Calculate from weather",
}

WEATHER_SOURCE_LABELS = {
    "csv": "Upload weather CSV",
    "nsrdb": "Retrieve weather from API (NSRDB)",
}

PV_SYSTEM_MODEL_LABELS = {
    "generic": "Generic array",
    "cec_equipment": "Named CEC equipment",
}

CEC_SEARCH_RESULT_LIMIT = 300

#: Backend profile modes, which :mod:`src.simulation.interface_analysis` still
#: keys on. The GUI derives one from the independent selections rather than
#: asking the user for it, so the analysis contract is unchanged.
PV_PROFILE_LABELS = {
    "capacity_factor_csv": "PV profile CSV — capacity factor",
    "weather_generic": "Weather — generic array",
    "weather_equipment": "Weather — named CEC equipment",
}

#: Saved preferences from before the split. Each legacy value maps onto one
#: combination of the three independent selections.
#:
#: ``synthetic`` has no successor: the redesigned Step 2 offers no synthetic
#: clear-sky option, so a preference file naming it falls back to the
#: capacity-factor CSV method. The backend still implements ``SyntheticPV``;
#: only the control is gone.
LEGACY_PV_PROFILE_MODES = {
    "synthetic": ("capacity_factor_csv", "csv", "generic"),
    "capacity_factor_csv": ("capacity_factor_csv", "csv", "generic"),
    "weather_generic": ("weather", "csv", "generic"),
    "weather_equipment": ("weather", "csv", "cec_equipment"),
}

#: NSRDB retrieval options offered in the interface. The adapter supports
#: more; these are the combinations the product actually publishes for the
#: continental United States.
NSRDB_TIME_STEP_LABELS = {
    "60": "60 minutes (hourly)",
    "30": "30 minutes",
    "15": "15 minutes",
    "5": "5 minutes",
}

LOAD_ARCHETYPE_LABELS = {
    "residential": "Residential",
    "multifamily": "Multifamily",
    "office": "Office",
    "retail": "Retail",
    "school": "School",
    "industrial": "Industrial",
}

METER_TOPOLOGY_LABELS = {
    "single_pcc": "Single utility meter at PCC",
    "master_with_submeters": "Master utility meter with internal submeters",
}

CARBON_WEIGHT_MODE_LABELS = {
    "single": "Single carbon weight",
    "list": "List of carbon weights",
    "range": "Carbon-weight range",
}

GUI_PREFERENCES_PATH = (
    Path(__file__).resolve().parents[2]
    / ".cache"
    / "gui_preferences.json"
)
GUI_PREFERENCES_VERSION = 3


def describe_pv_explanation(
    *,
    pv_profile_method: str,
    weather_source: str,
    pv_system_model: str,
) -> str:
    """Plain-language sentence saying where available PV power will come from."""

    if pv_profile_method == "capacity_factor_csv":
        return (
            "PV available power comes from the selected capacity-factor CSV "
            "multiplied by the rated PV capacity."
        )

    if pv_profile_method != "weather":
        return "Select a supported PV profile method."

    origin = (
        "an uploaded weather CSV"
        if weather_source == "csv"
        else "weather retrieved from the NSRDB API"
    )
    model = (
        "a generic array described by capacity, tilt, azimuth and DC/AC ratio"
        if pv_system_model == "generic"
        else "the named CEC module and inverter wired as configured"
    )

    return (
        f"PV available power is calculated from {origin} using {model}. "
        f"Inverter clipping is applied; operational curtailment is not."
    )


def describe_equipment_ratings(configuration) -> str:
    """Summarise what the selected modules and inverters actually add up to."""

    module_count = sum(
        subarray.module_count * unit.count
        for unit in configuration.inverter_units
        for subarray in unit.subarrays
    )

    return (
        f"Derived plant: {module_count} modules, "
        f"{configuration.rated_dc_capacity_kw:.2f} kW DC, "
        f"{configuration.inverter_ac_capacity_kw:.2f} kW AC "
        f"(DC/AC {configuration.dc_ac_ratio:.2f}); grid-following control."
    )


def resolve_pv_profile_mode(
    pv_profile_method: str,
    pv_system_model: str,
) -> str:
    """Map the independent Step 2 selections onto one backend profile mode.

    The interface asks three separate questions; the analysis layer still
    takes a single ``pv_profile_mode``. Deriving it here keeps the backend
    contract and its tests untouched while the interface stops pretending the
    three questions are one.
    """

    if pv_profile_method == "capacity_factor_csv":
        return "capacity_factor_csv"

    if pv_profile_method != "weather":
        raise ValueError(
            f"Unsupported PV profile method: {pv_profile_method!r}. "
            f"Supported: {list(PV_PROFILE_METHOD_LABELS)}."
        )

    if pv_system_model == "generic":
        return "weather_generic"

    if pv_system_model == "cec_equipment":
        return "weather_equipment"

    raise ValueError(
        f"Unsupported PV system model: {pv_system_model!r}. "
        f"Supported: {list(PV_SYSTEM_MODEL_LABELS)}."
    )


def migrate_legacy_pv_profile_mode(
    legacy_mode: str,
) -> tuple[str, str, str] | None:
    """Split a pre-redesign ``pv_profile_mode`` into the three selections.

    Returns ``(pv_profile_method, weather_source, pv_system_model)``, or
    ``None`` when the saved value is not one this interface ever wrote --
    in which case the defaults stand rather than a guess being restored.
    """

    return LEGACY_PV_PROFILE_MODES.get(str(legacy_mode))


def describe_pv_selection(
    *,
    pv_profile_method: str,
    weather_source: str,
    pv_system_model: str,
) -> str:
    """One readable line naming all three selections, for review and export."""

    method = PV_PROFILE_METHOD_LABELS.get(
        pv_profile_method, pv_profile_method
    )

    if pv_profile_method != "weather":
        return method

    return (
        f"{method} — "
        f"{WEATHER_SOURCE_LABELS.get(weather_source, weather_source)} — "
        f"{PV_SYSTEM_MODEL_LABELS.get(pv_system_model, pv_system_model)}"
    )


def format_cec_equipment_name(name: str) -> str:
    """Turn a database key into a readable manufacturer and model label."""

    return str(name).replace("__", " — ").replace("_", " ")


def filter_cec_equipment_names(
    names: tuple[str, ...],
    query: str,
    *,
    limit: int = CEC_SEARCH_RESULT_LIMIT,
) -> tuple[tuple[str, ...], int]:
    """Return bounded CEC matches while reporting the complete match count."""

    if limit < 1:
        raise ValueError("CEC search result limit must be at least 1.")
    terms = tuple(
        term.casefold()
        for term in query.replace("_", " ").split()
        if term.strip()
    )
    matches = tuple(
        name
        for name in names
        if all(
            term in format_cec_equipment_name(name).casefold()
            for term in terms
        )
    )
    return matches[:limit], len(matches)


class MicrogridApplication:
    """Own one root window and switch between the study workflow pages."""

    def __init__(self, window: tk.Tk) -> None:
        self.window = window
        self.window.title("Microgrid Analysis")
        self.window.geometry("900x850")
        self.window.minsize(780, 700)

        self.values = self._create_variables()
        # Coordinates are correct but rarely interesting, so they start folded
        # away behind the location search that fills them in.
        self.show_coordinates = tk.BooleanVar(value=False)
        self.location_search = LocationSearch()
        self.nsrdb_fetch_thread: threading.Thread | None = None
        # The CEC databases are ~25,000 entries and cost about a second to
        # parse, so they are loaded the first time equipment is selected
        # rather than at startup. Initialised here, not in the page builder,
        # so a layout change cannot drop it and crash on first selection.
        self._cec_options_loaded = False
        self._cec_module_options: tuple[str, ...] = ()
        self._cec_inverter_options: tuple[str, ...] = ()
        self.strategy_values = {
            name: tk.BooleanVar(
                value=name in {"no_battery", "cost_optimal"}
            )
            for name in STRATEGY_LABELS
        }
        self._constrained_price_mode: str | None = None
        self._constrained_tariff_id: str | None = None
        self.preferences_path = GUI_PREFERENCES_PATH
        self._load_preferences()
        self.pages: dict[str, ttk.Frame] = {}
        self.page_canvases: dict[str, tk.Canvas] = {}
        self.current_page_name: str | None = None
        self.battery_entries: list[ttk.Entry] = []
        self.analysis_result: InterfaceAnalysisResult | None = None
        self.analysis_export_parameters: dict[str, object] | None = None
        self.process_context = multiprocessing.get_context("spawn")
        self.analysis_messages = None
        self.analysis_process: multiprocessing.Process | None = None
        self.worker_exit_empty_polls = 0
        self.analysis_started_at: float | None = None
        self.is_closing = False
        self.window.protocol(
            "WM_DELETE_WINDOW",
            self._close_application,
        )

        self._build_header()

        self.page_container = ttk.Frame(window, padding=(30, 10, 30, 20))
        self.page_container.pack(fill="both", expand=True)
        self.page_container.rowconfigure(0, weight=1)
        self.page_container.columnconfigure(0, weight=1)

        self._build_analysis_page()
        self._build_microgrid_page()
        self._build_review_page()
        self._build_results_page()
        self.window.bind(
            "<MouseWheel>",
            self._scroll_current_page,
            add="+",
        )

        # The NSRDB year is a second statement of the study period, so it
        # follows the start date until a person overrides it, and any
        # remaining disagreement is shown before a metered fetch is spent.
        self._nsrdb_year_auto_value = str(self.values["nsrdb_year"].get())
        for field in ("start_date", "end_date_inclusive", "timezone"):
            self.values[field].trace_add(
                "write", self._on_horizon_changed
            )
        self.values["nsrdb_year"].trace_add(
            "write", self._on_nsrdb_year_changed
        )
        self._refresh_nsrdb_year_notice()

        self.show_page("analysis")

    def _on_horizon_changed(self, *_: object) -> None:
        """Track the start date with the NSRDB year, unless it was edited."""

        current = str(self.values["nsrdb_year"].get()).strip()

        if current == self._nsrdb_year_auto_value:
            start = str(self.values["start_date"].get()).strip()
            derived = start[:4]

            if len(derived) == 4 and derived.isdigit():
                self._nsrdb_year_auto_value = derived
                # Assigning re-enters through the year trace, which refreshes
                # the notice; setting it only when it differs keeps that to
                # one pass.
                if current != derived:
                    self.values["nsrdb_year"].set(derived)
                    return

        self._refresh_nsrdb_year_notice()

    def _on_nsrdb_year_changed(self, *_: object) -> None:
        self._refresh_nsrdb_year_notice()

    def _horizon_for_notice(self):
        """Build the interval grid the form describes, or ``None``.

        A half-typed date is the normal state of a text field, so an invalid
        horizon is not an error here -- it simply means there is nothing to
        compare the year against yet.
        """

        try:
            return build_interval_index(
                start_date=str(self.values["start_date"].get()).strip(),
                end_date=str(self.values["end_date_inclusive"].get()).strip(),
                timezone=str(self.values["timezone"].get()).strip(),
                timestep_minutes=int(
                    str(self.values["timestep_minutes"].get()).strip()
                ),
            )
        except Exception:
            return None

    def _nsrdb_year_mismatch(self) -> str | None:
        """Describe a year that will not cover the horizon, if any."""

        horizon = self._horizon_for_notice()

        if horizon is None:
            return None

        try:
            year = int(str(self.values["nsrdb_year"].get()).strip())
        except (TypeError, ValueError):
            return None

        return year_coverage_problem(year, horizon)

    def _refresh_nsrdb_year_notice(self) -> None:
        """Show the coverage advisory beside the year field."""

        notice = getattr(self, "nsrdb_year_notice", None)

        if notice is None:
            return

        notice.configure(text=self._nsrdb_year_mismatch() or "")

    def _create_variables(self) -> dict[str, tk.Variable]:
        """Create shared variables so page values survive navigation."""

        first_region = supported_regions()[0]
        region = get_region_config(first_region)

        return {
            "source_mode": tk.StringVar(value="live_api"),
            "region_id": tk.StringVar(value=first_region),
            "signal_csv_path": tk.StringVar(),
            "start_date": tk.StringVar(value="2026-05-31"),
            "end_date_inclusive": tk.StringVar(value="2026-06-01"),
            "timestep_minutes": tk.StringVar(value="15"),
            "price_mode": tk.StringVar(value="time_of_use"),
            "fixed_retail_price": tk.StringVar(value="0.20"),
            "price_csv_path": tk.StringVar(),
            "market_provider": tk.StringVar(value=region.market_provider),
            "market_location": tk.StringVar(value=region.market_location),
            "carbon_provider": tk.StringVar(value=region.carbon_provider),
            "carbon_zone": tk.StringVar(value=region.carbon_zone),
            "timezone": tk.StringVar(value=region.timezone),
            "carbon_weight_mode": tk.StringVar(value="single"),
            "carbon_weight_single": tk.StringVar(value="0.20"),
            "carbon_weight_list": tk.StringVar(value="0.00, 0.10, 0.20"),
            "carbon_weight_start": tk.StringVar(value="0.00"),
            "carbon_weight_end": tk.StringVar(value="0.50"),
            "carbon_weight_interval": tk.StringVar(value="0.10"),
            "degradation_cost": tk.StringVar(value="0.03"),
            "include_degradation_in_optimization": tk.StringVar(value="false"),
            "battery_capacity": tk.StringVar(value="100"),
            "battery_initial_energy": tk.StringVar(value="50"),
            "battery_max_charge": tk.StringVar(value="10"),
            "battery_max_discharge": tk.StringVar(value="10"),
            "pv_capacity": tk.StringVar(value="20"),
            # Three independent Step 2 selections. The backend's single
            # pv_profile_mode is derived from them by
            # resolve_pv_profile_mode() rather than stored.
            "pv_profile_method": tk.StringVar(value="weather"),
            "weather_source": tk.StringVar(value="csv"),
            "pv_system_model": tk.StringVar(value="generic"),
            "pv_capacity_factor_csv_path": tk.StringVar(),
            "weather_csv_path": tk.StringVar(),
            "nsrdb_year": tk.StringVar(value="2023"),
            "nsrdb_time_step_minutes": tk.StringVar(value="60"),
            # Typed text is a convenience for finding coordinates. The
            # coordinates themselves stay the stored truth, and a failed
            # search must never overwrite them.
            "location_query": tk.StringVar(value="San Francisco, CA"),
            "pv_latitude": tk.StringVar(value="37.77"),
            "pv_longitude": tk.StringVar(value="-122.42"),
            "pv_tilt_degrees": tk.StringVar(value="20"),
            "pv_azimuth_degrees": tk.StringVar(value="180"),
            "pv_dc_ac_ratio": tk.StringVar(value="1.2"),
            "pv_module_name": tk.StringVar(value="Canadian_Solar_Inc__CS6X_300M"),
            "pv_inverter_name": tk.StringVar(value="SMA_America__STP_50_US_41__480V_"),
            "pv_modules_per_string": tk.StringVar(value="15"),
            "pv_strings": tk.StringVar(value="13"),
            "pv_inverter_count": tk.StringVar(value="1"),
            "pv_mppt_input_count": tk.StringVar(value="2"),
            "load_power": tk.StringVar(value="60"),
            "load_profile_mode": tk.StringVar(value="constant"),
            "load_archetype": tk.StringVar(value="multifamily"),
            "load_variability": tk.StringVar(value="0.00"),
            "tariff_id": tk.StringVar(
                value=PGE_B1_SECONDARY_POLYPHASE_BUNDLED.tariff_id
            ),
            "meter_topology_mode": tk.StringVar(value="single_pcc"),
            "submeter_count": tk.StringVar(value="30"),
            "previous_peak_kw": tk.StringVar(),
        }

    def _build_header(self) -> None:
        header = ttk.Frame(self.window, padding=(30, 22, 30, 8))
        header.pack(fill="x")

        ttk.Label(
            header,
            text="Microgrid Analysis",
            font=("Arial", 22, "bold"),
        ).pack(side="left")

    def _load_preferences(self) -> None:
        """Restore the most recently launched valid GUI configuration."""

        try:
            saved = json.loads(self.preferences_path.read_text())
        except (OSError, ValueError, TypeError):
            return

        # Version 2 predates the Step 2 split. Its values are still readable,
        # and its combined pv_profile_mode is migrated below, so it is
        # accepted rather than discarded.
        if saved.get("version") not in {2, GUI_PREFERENCES_VERSION}:
            return

        saved_values = saved.get("values", {})
        if not isinstance(saved_values, dict):
            return

        choice_options = {
            "source_mode": set(SOURCE_MODE_LABELS),
            "region_id": set(supported_regions()),
            "price_mode": set(PRICE_MODE_LABELS),
            "carbon_weight_mode": set(CARBON_WEIGHT_MODE_LABELS),
            "load_profile_mode": set(LOAD_PROFILE_LABELS),
            "load_archetype": set(LOAD_ARCHETYPE_LABELS),
            "pv_profile_method": set(PV_PROFILE_METHOD_LABELS),
            "weather_source": set(WEATHER_SOURCE_LABELS),
            "pv_system_model": set(PV_SYSTEM_MODEL_LABELS),
            "nsrdb_time_step_minutes": set(NSRDB_TIME_STEP_LABELS),
            "tariff_id": set(TARIFF_LABELS) | {""},
            "meter_topology_mode": set(METER_TOPOLOGY_LABELS),
        }

        # A file written before Step 2 was split carries one combined
        # pv_profile_mode. Restoring the three selections it stood for is what
        # keeps an existing setup from silently reverting to the defaults.
        legacy_mode = saved_values.get("pv_profile_mode")
        if isinstance(legacy_mode, str) and "pv_profile_method" not in saved_values:
            migrated = migrate_legacy_pv_profile_mode(legacy_mode)
            if migrated is not None:
                method, weather_source, system_model = migrated
                self.values["pv_profile_method"].set(method)
                self.values["weather_source"].set(weather_source)
                self.values["pv_system_model"].set(system_model)

        for name, value in saved_values.items():
            if name not in self.values or not isinstance(value, str):
                continue
            if name in choice_options and value not in choice_options[name]:
                continue
            self.values[name].set(value)

        saved_strategies = saved.get("strategies", {})
        if isinstance(saved_strategies, dict):
            for name, variable in self.strategy_values.items():
                value = saved_strategies.get(name)
                if isinstance(value, bool):
                    variable.set(value)

        self.strategy_values["no_battery"].set(True)

    def _save_preferences(self) -> bool:
        """Persist the current valid selections outside version control."""

        saved = {
            "version": GUI_PREFERENCES_VERSION,
            "values": {
                name: str(variable.get())
                for name, variable in self.values.items()
            },
            "strategies": {
                name: bool(variable.get())
                for name, variable in self.strategy_values.items()
            },
        }
        temporary_path = self.preferences_path.with_suffix(".tmp")

        try:
            self.preferences_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path.write_text(
                json.dumps(saved, indent=2, sort_keys=True) + "\n"
            )
            temporary_path.replace(self.preferences_path)
        except OSError:
            return False

        return True

    def _new_page(self, name: str) -> ttk.Frame:
        """Create one vertically scrollable wizard page."""

        page_container = ttk.Frame(self.page_container)
        page_container.grid(row=0, column=0, sticky="nsew")
        page_container.rowconfigure(0, weight=1)
        page_container.columnconfigure(0, weight=1)

        canvas = tk.Canvas(page_container, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            page_container,
            orient="vertical",
            command=canvas.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=scrollbar.set)

        page = ttk.Frame(canvas)
        page_window = canvas.create_window((0, 0), window=page, anchor="nw")
        page.bind(
            "<Configure>",
            lambda _event, page_canvas=canvas: page_canvas.configure(
                scrollregion=page_canvas.bbox("all")
            ),
        )
        canvas.bind(
            "<Configure>",
            lambda event, page_canvas=canvas, item=page_window: (
                page_canvas.itemconfigure(item, width=event.width)
            ),
        )

        self.pages[name] = page_container
        self.page_canvases[name] = canvas
        return page

    def _scroll_current_page(self, event):
        """Scroll the visible wizard page with a mouse wheel or trackpad."""

        canvas = self.page_canvases.get(self.current_page_name or "")
        if canvas is None or not event.delta:
            return None
        direction = -1 if event.delta > 0 else 1
        canvas.yview_scroll(direction, "units")
        return "break"

    @staticmethod
    def _page_title(
        page: ttk.Frame,
        step: str,
        title: str,
        description: str,
    ) -> None:
        ttk.Label(
            page,
            text=f"{step}  {title}",
            font=("Arial", 19, "bold"),
        ).pack(anchor="w", pady=(5, 6))
        ttk.Label(page, text=description, wraplength=800).pack(
            anchor="w",
            pady=(0, 18),
        )

    def _build_analysis_page(self) -> None:
        page = self._new_page("analysis")
        self._page_title(
            page,
            "1 of 4",
            "Analysis Setup",
            "Choose the study horizon, data sources, pricing model, and optimization strategies.",
        )

        notebook = ttk.Notebook(page)
        notebook.pack(fill="both", expand=True)

        source_tab = ttk.Frame(notebook, padding=18)
        strategy_tab = ttk.Frame(notebook, padding=18)
        notebook.add(source_tab, text="Data and time range")
        notebook.add(strategy_tab, text="Strategies and costs")

        source_tab.columnconfigure(1, weight=1)
        self._add_combobox(
            source_tab,
            "Data source",
            self.values["source_mode"],
            ("live_api", "integrated_csv"),
            0,
            option_labels=SOURCE_MODE_LABELS,
        ).bind("<<ComboboxSelected>>", self._update_source_controls)

        self.region_combobox = self._add_combobox(
            source_tab,
            "Live API region",
            self.values["region_id"],
            tuple(supported_regions()),
            1,
            option_labels=REGION_LABELS,
        )
        self.region_combobox.bind("<<ComboboxSelected>>", self._apply_region_defaults)

        self.signal_csv_entry, self.signal_csv_button = self._add_file_row(
            source_tab,
            "Integrated signal CSV",
            self.values["signal_csv_path"],
            2,
        )

        self._add_entry(source_tab, "Start date (YYYY-MM-DD)", "start_date", 3)
        self._add_entry(
            source_tab,
            "End date, inclusive (YYYY-MM-DD)",
            "end_date_inclusive",
            4,
        )
        self._add_entry(source_tab, "Timestep (minutes)", "timestep_minutes", 5)

        self.price_mode_combobox = self._add_combobox(
            source_tab,
            "Electricity price model",
            self.values["price_mode"],
            tuple(PRICE_MODES),
            6,
            option_labels=PRICE_MODE_LABELS,
        )
        self.price_mode_combobox.bind(
            "<<ComboboxSelected>>",
            self._on_price_mode_selected,
        )

        self.fixed_price_entry = self._add_entry(
            source_tab,
            "Fixed retail price ($/kWh)",
            "fixed_retail_price",
            7,
        )
        self.price_csv_entry, self.price_csv_button = self._add_file_row(
            source_tab,
            "Price CSV",
            self.values["price_csv_path"],
            8,
        )

        self.tariff_combobox = self._add_combobox(
            source_tab,
            "Retail tariff",
            self.values["tariff_id"],
            tuple(supported_tariffs()),
            9,
            option_labels=TARIFF_LABELS,
        )
        self.tariff_combobox.bind(
            "<<ComboboxSelected>>",
            self._update_price_controls,
        )
        self.meter_topology_combobox = self._add_combobox(
            source_tab,
            "Billing meter arrangement",
            self.values["meter_topology_mode"],
            tuple(METER_TOPOLOGY_LABELS),
            10,
            option_labels=METER_TOPOLOGY_LABELS,
        )
        self.meter_topology_combobox.bind(
            "<<ComboboxSelected>>",
            self._update_price_controls,
        )
        self.submeter_count_entry = self._add_entry(
            source_tab,
            "Internal submeter count",
            "submeter_count",
            11,
        )
        self.previous_peak_entry = self._add_entry(
            source_tab,
            "Earlier billing-month peak (kW, optional)",
            "previous_peak_kw",
            12,
        )
        self.tariff_explanation = ttk.Label(
            source_tab,
            text=(
                "Tariff pricing adds TOU energy, customer, and demand charges. "
                "A blank earlier peak uses only the simulated partial-month peak."
            ),
            wraplength=760,
        )
        self.tariff_explanation.grid(
            row=13,
            column=0,
            columnspan=3,
            sticky="w",
            padx=6,
            pady=(4, 8),
        )

        self.show_overrides = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            source_tab,
            text="Show advanced provider overrides",
            variable=self.show_overrides,
            command=self._toggle_overrides,
        ).grid(row=14, column=0, columnspan=3, sticky="w", pady=(14, 5))

        self.override_frame = ttk.LabelFrame(
            source_tab,
            text="Advanced provider overrides",
            padding=12,
        )
        self.override_frame.columnconfigure(1, weight=1)
        self._add_entry(self.override_frame, "Market provider", "market_provider", 0)
        self._add_entry(self.override_frame, "Price node or hub", "market_location", 1)
        self._add_entry(self.override_frame, "Carbon provider", "carbon_provider", 2)
        self._add_entry(self.override_frame, "Carbon zone", "carbon_zone", 3)
        self._add_entry(self.override_frame, "Timezone", "timezone", 4)

        strategy_tab.columnconfigure(1, weight=1)
        ttk.Label(
            strategy_tab,
            text="Selected dispatch scenarios",
            font=("Arial", 14, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        for row, (name, label) in enumerate(STRATEGY_LABELS.items(), start=1):
            checkbox = ttk.Checkbutton(
                strategy_tab,
                text=label,
                variable=self.strategy_values[name],
                command=self._update_battery_controls,
            )
            checkbox.grid(row=row, column=0, columnspan=2, sticky="w", pady=3)
            if name == "no_battery":
                checkbox.configure(state="disabled")

        self._add_entry(
            strategy_tab,
            "Estimated battery wear ($/kWh throughput)",
            "degradation_cost",
            7,
        )

        ttk.Checkbutton(
            strategy_tab,
            text="Include battery wear in cost optimization (otherwise minimize utility bill)",
            variable=self.values["include_degradation_in_optimization"],
            onvalue="true",
            offvalue="false",
        ).grid(row=8, column=0, columnspan=2, sticky="w", pady=3)

        self.weight_mode_combobox = self._add_combobox(
            strategy_tab,
            "Combined carbon-weight input",
            self.values["carbon_weight_mode"],
            ("single", "list", "range"),
            9,
            option_labels=CARBON_WEIGHT_MODE_LABELS,
        )
        self.weight_mode_combobox.bind("<<ComboboxSelected>>", self._update_weight_controls)

        self.weight_entries = {
            "single": self._add_entry(
                strategy_tab,
                "Single weight ($/kgCO2)",
                "carbon_weight_single",
                10,
            ),
            "list": self._add_entry(
                strategy_tab,
                "Weight list (comma-separated)",
                "carbon_weight_list",
                11,
            ),
            "range_start": self._add_entry(
                strategy_tab,
                "Range start",
                "carbon_weight_start",
                12,
            ),
            "range_end": self._add_entry(
                strategy_tab,
                "Range end (inclusive)",
                "carbon_weight_end",
                13,
            ),
            "range_interval": self._add_entry(
                strategy_tab,
                "Range interval",
                "carbon_weight_interval",
                14,
            ),
        }

        self._navigation(page, next_page="microgrid")
        self._update_region_pricing_options()
        self._update_source_controls()
        self._update_price_controls()
        self._update_weight_controls()

    def _build_microgrid_page(self) -> None:
        page = self._new_page("microgrid")
        self._page_title(
            page,
            "2 of 4",
            "Microgrid Configuration",
            "Define the installed battery, PV capacity, and load assumptions used by the study.",
        )

        battery_frame = ttk.LabelFrame(page, text="Battery", padding=18)
        battery_frame.pack(fill="x", pady=8)
        battery_frame.columnconfigure(1, weight=1)

        self.battery_status = ttk.Label(battery_frame, text="")
        self.battery_status.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        for row, (label, name) in enumerate(
            (
                ("Usable capacity (kWh)", "battery_capacity"),
                ("Initial stored energy (kWh)", "battery_initial_energy"),
                ("Maximum charging power (kW)", "battery_max_charge"),
                ("Maximum discharging power (kW)", "battery_max_discharge"),
            ),
            start=1,
        ):
            self.battery_entries.append(self._add_entry(battery_frame, label, name, row))

        # --- Step 2 PV sections --------------------------------------
        #
        # The four sections answer four separate questions and are shown or
        # hidden as a unit. They live in their own container so a section can
        # be re-packed without landing after the Load frame: pack() appends,
        # so hiding and restoring a sibling of Load would reorder the page.
        pv_container = ttk.Frame(page)
        pv_container.pack(fill="x")
        self.pv_container = pv_container

        profile_frame = ttk.LabelFrame(
            pv_container, text="PV profile method", padding=18
        )
        profile_frame.columnconfigure(1, weight=1)
        self.pv_profile_frame = profile_frame
        self.pv_profile_method_combobox = self._add_combobox(
            profile_frame,
            "PV profile method",
            self.values["pv_profile_method"],
            tuple(PV_PROFILE_METHOD_LABELS),
            0,
            option_labels=PV_PROFILE_METHOD_LABELS,
        )
        self.pv_profile_method_combobox.bind(
            "<<ComboboxSelected>>", self._update_pv_controls
        )
        self.pv_capacity_entry = self._add_entry(
            profile_frame, "Rated PV capacity (kW)", "pv_capacity", 1
        )
        self.pv_capacity_factor_csv_widgets = self._add_file_row(
            profile_frame,
            "PV profile CSV",
            self.values["pv_capacity_factor_csv_path"],
            2,
        )
        self.pv_capacity_factor_csv_hint = ttk.Label(
            profile_frame,
            text=(
                "Required columns: timestamp, capacity_factor. Timestamps "
                "must include a timezone and match the selected analysis "
                "interval. Available PV power is capacity_factor multiplied "
                "by the rated PV capacity above."
            ),
            wraplength=740,
        )
        self.pv_capacity_factor_csv_hint.grid(
            row=3, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 4)
        )

        weather_frame = ttk.LabelFrame(
            pv_container, text="Weather source", padding=18
        )
        weather_frame.columnconfigure(1, weight=1)
        self.pv_weather_frame = weather_frame
        self.weather_source_combobox = self._add_combobox(
            weather_frame,
            "Weather source",
            self.values["weather_source"],
            tuple(WEATHER_SOURCE_LABELS),
            0,
            option_labels=WEATHER_SOURCE_LABELS,
        )
        self.weather_source_combobox.bind(
            "<<ComboboxSelected>>", self._update_pv_controls
        )
        self.weather_csv_widgets = self._add_file_row(
            weather_frame, "Weather CSV", self.values["weather_csv_path"], 1
        )
        self.weather_csv_hint = ttk.Label(
            weather_frame,
            text=(
                "Required columns: timestamp, ghi_w_per_m2, dni_w_per_m2, "
                "dhi_w_per_m2, temperature_c, wind_speed_m_per_s. Timestamps "
                "must include a timezone and be interval starts."
            ),
            wraplength=740,
        )
        self.weather_csv_hint.grid(
            row=2, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 4)
        )
        self.nsrdb_year_entry = self._add_entry(
            weather_frame, "NSRDB year", "nsrdb_year", 3
        )
        self.nsrdb_year_notice = ttk.Label(
            weather_frame,
            text="",
            wraplength=740,
        )
        self.nsrdb_year_notice.grid(
            row=8, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 4)
        )
        self.nsrdb_time_step_combobox = self._add_combobox(
            weather_frame,
            "NSRDB time step",
            self.values["nsrdb_time_step_minutes"],
            tuple(NSRDB_TIME_STEP_LABELS),
            4,
            option_labels=NSRDB_TIME_STEP_LABELS,
        )
        self.fetch_weather_button = ttk.Button(
            weather_frame,
            text="Fetch Weather",
            command=self._fetch_nsrdb_weather,
        )
        self.fetch_weather_button.grid(
            row=5, column=1, sticky="w", padx=6, pady=(8, 4)
        )
        self.nsrdb_status_label = ttk.Label(
            weather_frame,
            text="",
            wraplength=740,
        )
        self.nsrdb_status_label.grid(
            row=6, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 4)
        )
        self.nsrdb_hint = ttk.Label(
            weather_frame,
            text=(
                "Retrieval runs only when Fetch Weather is pressed, because "
                "it makes a network request against a metered account. It "
                "uses the coordinates from Site Location above, needs "
                f"{NSRDB_API_KEY_ENV_VAR} and {NSRDB_EMAIL_ENV_VAR} in the "
                "environment or .env, and saves a weather CSV that later runs "
                "read offline."
            ),
            wraplength=740,
        )
        self.nsrdb_hint.grid(
            row=7, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 4)
        )

        model_frame = ttk.LabelFrame(
            pv_container, text="PV system model", padding=18
        )
        model_frame.columnconfigure(1, weight=1)
        self.pv_model_frame = model_frame
        self.pv_system_model_combobox = self._add_combobox(
            model_frame,
            "PV system model",
            self.values["pv_system_model"],
            tuple(PV_SYSTEM_MODEL_LABELS),
            0,
            option_labels=PV_SYSTEM_MODEL_LABELS,
        )
        self.pv_system_model_combobox.bind(
            "<<ComboboxSelected>>", self._update_pv_controls
        )
        # A second entry bound to the same variable as the one in the profile
        # section. Only ever one of them is visible, and sharing the variable
        # means there is still exactly one rated capacity.
        self.pv_generic_capacity_entry = self._add_entry(
            model_frame, "Rated PV capacity (kW)", "pv_capacity", 1
        )
        # Tilt and azimuth describe how the array is mounted, which is true of
        # a named-equipment plant exactly as much as a generic one -- both
        # models transpose irradiance onto that plane. They are kept separate
        # from the genuinely generic-only fields so both selections can show
        # them.
        self.pv_orientation_entries = [
            self._add_entry(model_frame, "Array tilt (degrees)", "pv_tilt_degrees", 2),
            self._add_entry(
                model_frame, "Array azimuth (degrees)", "pv_azimuth_degrees", 3
            ),
        ]
        self.pv_generic_only_entries = [
            self.pv_generic_capacity_entry,
            self._add_entry(model_frame, "DC/AC ratio", "pv_dc_ac_ratio", 4),
        ]
        #: Every field the generic model owns, orientation included.
        self.pv_generic_entries = [
            *self.pv_generic_only_entries,
            *self.pv_orientation_entries,
        ]
        (
            self.pv_module_combobox,
            self.pv_module_search_button,
        ) = self._add_cec_search_row(
            model_frame,
            "CEC module",
            self.values["pv_module_name"],
            5,
            equipment_kind="module",
        )
        (
            self.pv_inverter_combobox,
            self.pv_inverter_search_button,
        ) = self._add_cec_search_row(
            model_frame,
            "CEC inverter",
            self.values["pv_inverter_name"],
            6,
            equipment_kind="inverter",
        )
        self.pv_equipment_entries = [
            self._add_entry(model_frame, "Modules per string", "pv_modules_per_string", 7),
            self._add_entry(model_frame, "Parallel strings", "pv_strings", 8),
            self._add_entry(model_frame, "Inverter count", "pv_inverter_count", 9),
            self._add_entry(
                model_frame, "MPPT inputs per inverter", "pv_mppt_input_count", 10
            ),
        ]
        self.pv_equipment_summary = ttk.Label(
            model_frame,
            text="",
            wraplength=740,
        )
        self.pv_equipment_summary.grid(
            row=11, column=0, columnspan=3, sticky="w", padx=6, pady=(8, 0)
        )

        location_frame = ttk.LabelFrame(
            pv_container, text="Site location", padding=18
        )
        location_frame.columnconfigure(1, weight=1)
        self.pv_location_frame = location_frame
        ttk.Label(location_frame, text="Search for a place").grid(
            row=0, column=0, sticky="w", padx=6, pady=5
        )
        self.location_query_entry = ttk.Entry(
            location_frame, textvariable=self.values["location_query"]
        )
        self.location_query_entry.grid(row=0, column=1, sticky="ew", padx=6, pady=5)
        self.location_search_button = ttk.Button(
            location_frame,
            text="Search Location",
            command=self._search_site_location,
        )
        self.location_search_button.grid(row=0, column=2, padx=6, pady=5)
        self.location_result_label = ttk.Label(
            location_frame,
            text="",
            wraplength=740,
        )
        self.location_result_label.grid(
            row=1, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 4)
        )
        self.show_coordinates_checkbutton = ttk.Checkbutton(
            location_frame,
            text="Advanced: edit latitude and longitude directly",
            variable=self.show_coordinates,
            command=self._update_pv_controls,
        )
        self.show_coordinates_checkbutton.grid(
            row=2, column=0, columnspan=3, sticky="w", padx=6, pady=(4, 4)
        )
        self.pv_coordinate_entries = [
            self._add_entry(location_frame, "Latitude", "pv_latitude", 3),
            self._add_entry(location_frame, "Longitude", "pv_longitude", 4),
        ]
        self.location_hint = ttk.Label(
            location_frame,
            text=(
                "Searching fills in the latitude and longitude. The analysis "
                "uses those numbers and not the text, so they can always be "
                "typed directly instead."
            ),
            wraplength=740,
        )
        self.location_hint.grid(
            row=5, column=0, columnspan=3, sticky="w", padx=6, pady=(0, 4)
        )

        for entry in self.pv_equipment_entries:
            entry.bind("<FocusOut>", self._update_equipment_summary)

        system_frame = ttk.LabelFrame(page, text="Load", padding=18)
        system_frame.pack(fill="x", pady=12)
        system_frame.columnconfigure(1, weight=1)
        self.load_profile_combobox = self._add_combobox(
            system_frame,
            "Load profile source",
            self.values["load_profile_mode"],
            tuple(LOAD_PROFILE_LABELS),
            0,
        )
        self.load_profile_combobox.bind(
            "<<ComboboxSelected>>",
            self._update_profile_controls,
        )
        self.load_power_label = ttk.Label(
            system_frame,
            text="Load power (kW)",
        )
        self.load_power_label.grid(
            row=1,
            column=0,
            sticky="w",
            padx=6,
            pady=5,
        )
        self.load_power_entry = ttk.Entry(
            system_frame,
            textvariable=self.values["load_power"],
        )
        self.load_power_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=6,
            pady=5,
        )
        self.load_archetype_combobox = self._add_combobox(
            system_frame,
            "Synthetic building type",
            self.values["load_archetype"],
            tuple(LOAD_ARCHETYPE_LABELS),
            2,
        )
        self.load_variability_entry = self._add_entry(
            system_frame,
            "Synthetic variability (fraction, 0 to 1)",
            "load_variability",
            3,
        )

        self.profile_explanation = ttk.Label(
            system_frame,
            wraplength=760,
        )
        self.profile_explanation.grid(
            row=4,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(12, 0),
        )

        self._navigation(page, previous_page="analysis", next_page="review")
        # grid_slaves() stops returning a widget once it has been
        # grid_remove()d, so a section could be hidden but never restored.
        # Snapshotting row membership once, while everything is still
        # gridded, is what makes every selection reversible.
        # Ordered: the four questions in the order the interface asks them.
        # Site location comes before Weather source: the NSRDB fetch reads
        # the coordinates set there, so asking for them first is the order a
        # person actually fills the form in.
        self.pv_section_frames = {
            "profile": self.pv_profile_frame,
            "location": self.pv_location_frame,
            "weather": self.pv_weather_frame,
            "model": self.pv_model_frame,
        }
        self.pv_section_rows = {
            "profile": self._snapshot_rows(self.pv_profile_frame, 4),
            "location": self._snapshot_rows(self.pv_location_frame, 6),
            "weather": self._snapshot_rows(self.pv_weather_frame, 8),
            "model": self._snapshot_rows(self.pv_model_frame, 12),
        }
        self._update_battery_controls()
        self._update_pv_controls()
        self._update_profile_controls()

    def _build_review_page(self) -> None:
        page = self._new_page("review")
        self._page_title(
            page,
            "3 of 4",
            "Review and Run",
            "Confirm the complete study request before data retrieval and simulation begin.",
        )

        review_container = ttk.Frame(page)
        review_container.pack(fill="both", expand=True, pady=8)

        self.review_canvas = tk.Canvas(
            review_container,
            highlightthickness=0,
        )
        self.review_canvas.grid(row=0, column=0, sticky="nsew")

        review_vertical_scrollbar = ttk.Scrollbar(
            review_container,
            orient="vertical",
            command=self.review_canvas.yview,
        )
        review_vertical_scrollbar.grid(row=0, column=1, sticky="ns")

        review_horizontal_scrollbar = ttk.Scrollbar(
            review_container,
            orient="horizontal",
            command=self.review_canvas.xview,
        )
        review_horizontal_scrollbar.grid(row=1, column=0, sticky="ew")

        review_container.rowconfigure(0, weight=1)
        review_container.columnconfigure(0, weight=1)
        self.review_canvas.configure(
            yscrollcommand=review_vertical_scrollbar.set,
            xscrollcommand=review_horizontal_scrollbar.set,
        )

        self.review_table_frame = tk.Frame(self.review_canvas)
        self.review_canvas.create_window(
            (0, 0),
            window=self.review_table_frame,
            anchor="nw",
        )
        self.review_table_frame.bind(
            "<Configure>",
            lambda _event: self.review_canvas.configure(
                scrollregion=self.review_canvas.bbox("all")
            ),
        )

        controls = ttk.Frame(page)
        controls.pack(fill="x", pady=(12, 0))
        ttk.Button(controls, text="Back", command=lambda: self.show_page("microgrid")).pack(side="left")
        self.run_analysis_button = ttk.Button(
            controls,
            text="Run Analysis",
            command=self._validate_and_run_analysis,
        )
        self.run_analysis_button.pack(side="right")

    def _build_results_page(self) -> None:
        page = self._new_page("results")
        self._page_title(
            page,
            "4 of 4",
            "Results",
            "Compare scenario metrics visually, inspect the results table, or export CSV outputs.",
        )

        details_frame = ttk.LabelFrame(
            page,
            text="Analysis details",
            padding=14,
        )
        details_frame.pack(fill="x", pady=(4, 8))
        details_frame.columnconfigure(1, weight=1)

        self.analysis_detail_values: dict[str, tk.StringVar] = {}

        for row, label in enumerate(
            ("Data source", "Location", "Time range", "Time interval")
        ):
            ttk.Label(
                details_frame,
                text=f"{label}:",
                font=("Arial", 11, "bold"),
            ).grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=3)

            value = tk.StringVar(value="—")
            self.analysis_detail_values[label] = value
            ttk.Label(
                details_frame,
                textvariable=value,
                wraplength=680,
            ).grid(row=row, column=1, sticky="w", pady=3)

        output_frame = ttk.LabelFrame(page, text="Analysis output", padding=18)
        output_frame.pack(fill="both", expand=True, pady=10)

        self.progress_message = tk.StringVar(
            value="Run the analysis from the Review and Run page."
        )
        ttk.Label(
            output_frame,
            textvariable=self.progress_message,
            font=("Arial", 13, "bold"),
            wraplength=760,
        ).pack(anchor="w", pady=(0, 10))

        self.analysis_progress = ttk.Progressbar(
            output_frame,
            mode="determinate",
            maximum=100,
        )
        self.analysis_progress.pack(fill="x", pady=(0, 8))

        self.elapsed_message = tk.StringVar(value="Elapsed time: —")
        ttk.Label(
            output_frame,
            textvariable=self.elapsed_message,
        ).pack(anchor="w", pady=(0, 8))

        self.result_message = ttk.Label(
            output_frame,
            text="No results to display yet.",
            wraplength=760,
        )
        self.result_message.pack(anchor="w", pady=(5, 10))

        self.results_notebook = ttk.Notebook(output_frame)
        self.results_notebook.pack(fill="both", expand=True)
        chart_tab = ttk.Frame(self.results_notebook)
        self.results_notebook.add(chart_tab, text="Visual comparison")
        chart_controls = ttk.Frame(chart_tab)
        chart_controls.pack(fill="x", pady=6)
        ttk.Label(chart_controls, text="Compare:").pack(side="left", padx=(0, 8))
        self.comparison_metric = tk.StringVar()
        self.comparison_metric_selector = ttk.Combobox(
            chart_controls, textvariable=self.comparison_metric,
            state="disabled", width=44,
        )
        self.comparison_metric_selector.pack(side="left")
        self.comparison_metric_selector.bind(
            "<<ComboboxSelected>>", lambda _event: self._render_results_chart()
        )
        self.chart_placeholder = ttk.Label(chart_tab, text="Run an analysis to compare scenarios.")
        self.chart_placeholder.pack(anchor="w", pady=12)
        self.chart_host = ttk.Frame(chart_tab)
        self.chart_host.pack(fill="both", expand=True)
        self.chart_canvas = None

        table_container = ttk.Frame(self.results_notebook)
        self.results_notebook.add(table_container, text="Results table")
        table_container.rowconfigure(0, weight=1)
        table_container.columnconfigure(0, weight=1)

        self.table_canvas = tk.Canvas(
            table_container,
            height=100,
            highlightthickness=0,
        )
        self.table_canvas.grid(row=0, column=0, sticky="nsew")

        self.table_scrollbar = ttk.Scrollbar(
            table_container,
            orient="horizontal",
            command=self.table_canvas.xview,
        )
        self.table_scrollbar.grid(row=1, column=0, sticky="ew")

        self.table_vertical_scrollbar = ttk.Scrollbar(
            table_container,
            orient="vertical",
            command=self.table_canvas.yview,
        )
        self.table_vertical_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )
        self.table_canvas.configure(
            xscrollcommand=self.table_scrollbar.set,
            yscrollcommand=self.table_vertical_scrollbar.set,
        )

        self.table_frame = tk.Frame(self.table_canvas)
        self.table_window = self.table_canvas.create_window(
            (0, 0),
            window=self.table_frame,
            anchor="nw",
        )
        self.table_frame.bind(
            "<Configure>",
            self._update_table_scroll_region,
        )
        self._bind_result_table_scrolling(self.table_canvas)
        self._bind_result_table_scrolling(self.table_frame)

        pv_tab = ttk.Frame(self.results_notebook)
        self.results_notebook.add(pv_tab, text="PV model details")
        self.pv_detail_message = tk.StringVar(
            value="Run a Phase 1 or Phase 2 weather-derived PV analysis."
        )
        ttk.Label(
            pv_tab,
            textvariable=self.pv_detail_message,
            wraplength=760,
        ).pack(anchor="w", pady=(8, 4))
        self.pv_chart_placeholder = ttk.Label(
            pv_tab,
            text="PV diagnostics are unavailable for synthetic and imported profiles.",
        )
        self.pv_chart_placeholder.pack(anchor="w", pady=12)
        self.pv_chart_host = ttk.Frame(pv_tab)
        self.pv_chart_host.pack(fill="both", expand=True)
        self.pv_chart_canvas = None

        controls = self._navigation(page, previous_page="review")
        self.export_results_button = ttk.Button(
            controls,
            text="Export Results CSV",
            command=self._export_results_csv,
            state="disabled",
        )
        self.export_results_button.pack(side="right")
        self.export_pv_diagnostics_button = ttk.Button(
            controls,
            text="Export PV Diagnostics CSV",
            command=self._export_pv_diagnostics_csv,
            state="disabled",
        )
        self.export_pv_diagnostics_button.pack(side="right", padx=(0, 8))

    def _navigation(
        self,
        page: ttk.Frame,
        *,
        previous_page: str | None = None,
        next_page: str | None = None,
    ) -> ttk.Frame:
        controls = ttk.Frame(page)
        controls.pack(fill="x", pady=(16, 0))
        if previous_page:
            ttk.Button(
                controls,
                text="Back",
                command=lambda: self.show_page(previous_page),
            ).pack(side="left")
        if next_page:
            ttk.Button(
                controls,
                text="Next",
                command=lambda: self.show_page(next_page),
            ).pack(side="right")
        return controls

    def show_page(self, name: str) -> None:
        """Raise one workflow page while retaining all shared values."""

        if name == "review":
            self._refresh_review()
        self.current_page_name = name
        self.pages[name].tkraise()
        self.page_canvases[name].yview_moveto(0)

    def _add_entry(
        self,
        parent: ttk.Frame,
        label: str,
        variable_name: str,
        row: int,
    ) -> ttk.Entry:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=5)
        entry = ttk.Entry(parent, textvariable=self.values[variable_name])
        entry.grid(row=row, column=1, sticky="ew", padx=6, pady=5)
        return entry

    def _add_combobox(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.Variable,
        options: tuple[str, ...],
        row: int,
        *,
        option_labels: dict[str, str] | None = None,
    ) -> ttk.Combobox:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=5)

        if option_labels is None:
            combobox = ttk.Combobox(
                parent,
                textvariable=variable,
                values=options,
                state="readonly",
            )
        else:
            internal_to_display = {
                option: option_labels.get(option, option)
                for option in options
            }
            display_to_internal = {
                display: internal
                for internal, display in internal_to_display.items()
            }
            display_variable = tk.StringVar(
                value=internal_to_display.get(
                    str(variable.get()),
                    str(variable.get()),
                )
            )
            synchronizing = {"active": False}

            def update_internal_value(*_args) -> None:
                if synchronizing["active"]:
                    return
                display_value = display_variable.get()
                if display_value in display_to_internal:
                    synchronizing["active"] = True
                    variable.set(display_to_internal[display_value])
                    synchronizing["active"] = False

            def update_display_value(*_args) -> None:
                if synchronizing["active"]:
                    return
                internal_value = str(variable.get())
                synchronizing["active"] = True
                display_variable.set(
                    internal_to_display.get(internal_value, internal_value)
                )
                synchronizing["active"] = False

            display_variable.trace_add("write", update_internal_value)
            variable.trace_add("write", update_display_value)

            combobox = ttk.Combobox(
                parent,
                textvariable=display_variable,
                values=tuple(
                    internal_to_display[option]
                    for option in options
                ),
                state="readonly",
            )
            combobox.display_variable = display_variable
            combobox.internal_variable = variable

        combobox.grid(row=row, column=1, columnspan=2, sticky="ew", padx=6, pady=5)
        return combobox

    def _add_cec_search_row(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.Variable,
        row: int,
        *,
        equipment_kind: str,
    ) -> tuple[ttk.Entry, ttk.Button]:
        """Add a selected CEC value and a button opening the search dialog."""

        ttk.Label(parent, text=label).grid(
            row=row, column=0, sticky="w", padx=6, pady=5
        )
        selected_entry = ttk.Entry(
            parent,
            textvariable=variable,
            state="readonly",
        )
        selected_entry.grid(row=row, column=1, sticky="ew", padx=6, pady=5)
        search_button = ttk.Button(
            parent,
            text="Search…",
            command=lambda: self._open_cec_search(equipment_kind),
        )
        search_button.grid(row=row, column=2, padx=6, pady=5)
        return selected_entry, search_button

    def _add_file_row(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.Variable,
        row: int,
    ) -> tuple[ttk.Entry, ttk.Button]:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=5)
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", padx=6, pady=5)
        button = ttk.Button(
            parent,
            text="Browse",
            command=lambda: self._browse_csv(variable),
        )
        button.grid(row=row, column=2, padx=6, pady=5)
        return entry, button

    def _browse_csv(self, variable: tk.Variable) -> None:
        path = filedialog.askopenfilename(
            parent=self.window,
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv")],
        )
        if path:
            variable.set(path)

    def _apply_region_defaults(self, _event=None) -> None:
        region = get_region_config(str(self.values["region_id"].get()))
        self.values["market_provider"].set(region.market_provider)
        self.values["market_location"].set(region.market_location)
        self.values["carbon_provider"].set(region.carbon_provider)
        self.values["carbon_zone"].set(region.carbon_zone)
        self.values["timezone"].set(region.timezone)
        self._update_region_pricing_options()

    def _update_region_pricing_options(self) -> None:
        """Limit retail-price choices to tariffs valid for the region."""

        region_id = str(self.values["region_id"].get())
        tariff_ids = retail_tariff_ids_for_region(region_id)
        price_modes = tuple(
            mode
            for mode in PRICE_MODES
            if mode != "time_of_use" or tariff_ids
        )

        self.price_mode_combobox.configure(
            values=tuple(PRICE_MODE_LABELS[mode] for mode in price_modes)
        )
        self.tariff_combobox.configure(
            values=tuple(TARIFF_LABELS[tariff_id] for tariff_id in tariff_ids)
        )

        selected_price_mode = str(self.values["price_mode"].get())
        if selected_price_mode not in price_modes:
            if selected_price_mode == "time_of_use":
                self._constrained_price_mode = selected_price_mode
            self.values["price_mode"].set("wholesale_market")
        elif tariff_ids:
            constrained_price_mode = getattr(
                self, "_constrained_price_mode", None
            )
            if constrained_price_mode in price_modes:
                self.values["price_mode"].set(constrained_price_mode)
            self._constrained_price_mode = None

        selected_tariff = str(self.values["tariff_id"].get())
        if not tariff_ids:
            if selected_tariff:
                self._constrained_tariff_id = selected_tariff
            self.values["tariff_id"].set("")
        else:
            constrained_tariff = getattr(
                self, "_constrained_tariff_id", None
            )
            if constrained_tariff in tariff_ids:
                selected_tariff = constrained_tariff
            if selected_tariff not in tariff_ids:
                selected_tariff = tariff_ids[0]
            self.values["tariff_id"].set(selected_tariff)
            self._constrained_tariff_id = None

        self._update_price_controls()

    def _on_price_mode_selected(self, _event=None) -> None:
        """Honor an explicit choice over a remembered regional fallback."""

        self._constrained_price_mode = None
        self._update_price_controls()


    def _update_source_controls(self, _event=None) -> None:
        live = self.values["source_mode"].get() == "live_api"
        self.region_combobox.configure(state="readonly" if live else "disabled")
        self.price_mode_combobox.configure(state="readonly" if live else "disabled")
        csv_state = "disabled" if live else "normal"
        self.signal_csv_entry.configure(state=csv_state)
        self.signal_csv_button.configure(state=csv_state)
        self._update_price_controls()
        if hasattr(self, "load_profile_combobox"):
            self._update_profile_controls()
        if hasattr(self, "pv_profile_combobox"):
            self._update_pv_controls()

    def _update_price_controls(self, _event=None) -> None:
        live = self.values["source_mode"].get() == "live_api"
        mode = self.values["price_mode"].get()
        tariff_ids = retail_tariff_ids_for_region(
            str(self.values["region_id"].get())
        )
        self.fixed_price_entry.configure(
            state="normal" if live and mode == "fixed_retail" else "disabled"
        )
        csv_state = "normal" if live and mode == "csv" else "disabled"
        self.price_csv_entry.configure(state=csv_state)
        self.price_csv_button.configure(state=csv_state)
        # The tariff bills the run, so it applies whenever a schedule is
        # available: on the live path only when prices come from the
        # tariff itself, and on the integrated-CSV path always (the CSV
        # supplies dispatch prices, the tariff supplies the bill).
        tariff_active = bool(tariff_ids) and (
            not live or mode == "time_of_use"
        )
        tariff_state = "readonly" if tariff_active else "disabled"
        self.tariff_combobox.configure(state=tariff_state)
        self.meter_topology_combobox.configure(state=tariff_state)
        master_meter = (
            tariff_active
            and self.values["meter_topology_mode"].get()
            == "master_with_submeters"
        )
        self.submeter_count_entry.configure(
            state="normal" if master_meter else "disabled"
        )
        selected_tariff_id = str(self.values["tariff_id"].get())
        tariff_has_demand_charge = (
            tariff_active
            and bool(get_tariff(selected_tariff_id).demand_charges)
        )
        self.previous_peak_entry.configure(
            state="normal" if tariff_has_demand_charge else "disabled"
        )
        if live and not tariff_ids:
            explanation = (
                "No retail tariff is implemented for this region. Select "
                "wholesale market, fixed retail, or CSV pricing."
            )
        elif tariff_active and not tariff_has_demand_charge:
            explanation = (
                "Standard B-1 has TOU energy and customer charges but no "
                "demand charge. Peak import is still shown for operating "
                "analysis and the 75 kW eligibility review. B1-ST is a "
                "separate storage tariff and is not modelled here."
            )
        else:
            explanation = (
                "Tariff pricing adds TOU energy, customer, and demand charges. "
                "A blank earlier peak uses only the simulated partial-month peak."
            )
        if tariff_active and get_tariff(selected_tariff_id).energy_components:
            explanation = get_tariff(selected_tariff_id).notes
        self.tariff_explanation.configure(
            text=explanation,
            foreground="" if tariff_active else "#777777",
        )

    def _toggle_overrides(self) -> None:
        if self.show_overrides.get():
            self.override_frame.grid(row=15, column=0, columnspan=3, sticky="ew", pady=8)
        else:
            self.override_frame.grid_forget()

    def _update_weight_controls(self, _event=None) -> None:
        mode = self.values["carbon_weight_mode"].get()
        for key, entry in self.weight_entries.items():
            active = key == mode or (mode == "range" and key.startswith("range_"))
            entry.configure(state="normal" if active else "disabled")

    def _update_battery_controls(self) -> None:
        enabled = any(
            variable.get()
            for name, variable in self.strategy_values.items()
            if name != "no_battery"
        )
        state = "normal" if enabled else "disabled"
        for entry in self.battery_entries:
            entry.configure(state=state)
        self.battery_status.configure(
            text=(
                "Battery parameters are active."
                if enabled
                else "Only the no-battery baseline is selected; battery inputs will be ignored."
            )
        )

    def _update_profile_controls(self, _event=None) -> None:
        """Enable synthetic-profile details only when live data uses them."""

        live = self.values["source_mode"].get() == "live_api"
        synthetic = self.values["load_profile_mode"].get() == "synthetic"
        self.load_profile_combobox.configure(
            state="readonly" if live else "disabled"
        )
        detail_state = "readonly" if live and synthetic else "disabled"
        self.load_archetype_combobox.configure(state=detail_state)
        self.load_variability_entry.configure(
            state="normal" if live and synthetic else "disabled"
        )
        self.load_power_label.configure(
            text=(
                "Synthetic profile peak load (kW)"
                if live and synthetic
                else "Constant load power (kW)"
            )
        )
        self.load_power_entry.configure(
            state="normal" if live else "disabled"
        )
        if not live:
            explanation = (
                "Load and PV interval values come from the selected integrated CSV "
                "columns load_kw and pv_kw; the profile controls above are ignored."
            )
        else:
            load_explanation = (
                "The program generates one load value per interval from the building "
                "type, peak load, and variability entered above."
                if synthetic
                else "The entered load power is repeated at every interval."
            )
            pv_explanation = describe_pv_explanation(
                pv_profile_method=str(self.values["pv_profile_method"].get()),
                weather_source=str(self.values["weather_source"].get()),
                pv_system_model=str(self.values["pv_system_model"].get()),
            )
            explanation = f"{load_explanation} {pv_explanation}"
        self.profile_explanation.configure(text=explanation)

    @staticmethod
    def _snapshot_rows(frame, row_count: int) -> dict[int, tuple]:
        """Record which widgets sit on each grid row, while all are visible.

        ``grid_slaves()`` stops returning a widget once it has been
        ``grid_remove()``d, so a section read back later would look empty and
        could never be restored. Taking the snapshot once at build time is
        what makes hiding reversible.
        """

        return {row: tuple(frame.grid_slaves(row=row)) for row in range(row_count)}

    def _apply_row_visibility(
        self,
        section: str,
        visible_rows: set[int],
    ) -> None:
        """Show exactly ``visible_rows`` of one PV section."""

        rows = getattr(self, "pv_section_rows", {}).get(section, {})

        for row, widgets in rows.items():
            for widget in widgets:
                if row in visible_rows:
                    widget.grid()
                else:
                    widget.grid_remove()

    def _show_pv_sections(self, visible: tuple[str, ...]) -> None:
        """Pack the named sections, in order, and hide the rest.

        Every section is unpacked first and the visible ones re-packed in a
        fixed order, because ``pack`` appends: restoring one section without
        re-packing the others would move it below its siblings.
        """

        frames = getattr(self, "pv_section_frames", None)

        if frames is None:
            return

        for frame in frames.values():
            frame.pack_forget()

        for name, frame in frames.items():
            if name in visible:
                frame.pack(fill="x", pady=8)

    def _update_pv_controls(self, _event=None) -> None:
        """Reveal only the fields the current three selections actually use."""

        live = self.values["source_mode"].get() == "live_api"
        method = str(self.values["pv_profile_method"].get())
        weather_source = str(self.values["weather_source"].get())
        system_model = str(self.values["pv_system_model"].get())

        weather_method = live and method == "weather"
        capacity_factor = live and method == "capacity_factor_csv"
        generic = weather_method and system_model == "generic"
        equipment = weather_method and system_model == "cec_equipment"
        weather_csv = weather_method and weather_source == "csv"
        weather_api = weather_method and weather_source == "nsrdb"

        # Integrated CSV supplies load_kw and pv_kw directly, so Step 2's
        # profile controls describe nothing and stay collapsed.
        sections = ("profile",)
        if weather_method:
            sections = ("profile", "weather", "model", "location")
        self._show_pv_sections(sections)

        profile_rows = {0}
        if capacity_factor:
            profile_rows.update({1, 2, 3})
        self._apply_row_visibility("profile", profile_rows)

        weather_rows = {0}
        if weather_csv:
            weather_rows.update({1, 2})
        elif weather_api:
            weather_rows.update({3, 4, 5, 6, 7})
        self._apply_row_visibility("weather", weather_rows)

        model_rows = {0}
        if generic:
            model_rows.update({1, 2, 3, 4})
        elif equipment:
            # Rows 2 and 3 are tilt and azimuth. The equipment model reads
            # them too, so hiding them would let a stored orientation change
            # the answer with nothing on screen to explain it.
            model_rows.update({2, 3, 5, 6, 7, 8, 9, 10, 11})
            self._ensure_cec_options_loaded()
        self._apply_row_visibility("model", model_rows)

        location_rows = {0, 1, 2, 5}
        if bool(self.show_coordinates.get()):
            location_rows.update({3, 4})
        self._apply_row_visibility("location", location_rows)

        self.pv_profile_method_combobox.configure(
            state="readonly" if live else "disabled"
        )
        self.weather_source_combobox.configure(
            state="readonly" if weather_method else "disabled"
        )
        self.pv_system_model_combobox.configure(
            state="readonly" if weather_method else "disabled"
        )

        for widget in self.pv_capacity_factor_csv_widgets:
            widget.configure(state="normal" if capacity_factor else "disabled")
        self.pv_capacity_entry.configure(
            state="normal" if capacity_factor else "disabled"
        )

        for widget in self.weather_csv_widgets:
            widget.configure(state="normal" if weather_csv else "disabled")
        self.nsrdb_year_entry.configure(
            state="normal" if weather_api else "disabled"
        )
        self.nsrdb_time_step_combobox.configure(
            state="readonly" if weather_api else "disabled"
        )
        self.fetch_weather_button.configure(
            state="normal" if weather_api else "disabled"
        )

        for entry in self.pv_generic_only_entries:
            entry.configure(state="normal" if generic else "disabled")
        for entry in self.pv_orientation_entries:
            entry.configure(
                state="normal" if generic or equipment else "disabled"
            )

        equipment_state = "readonly" if equipment else "disabled"
        self.pv_module_combobox.configure(state=equipment_state)
        self.pv_inverter_combobox.configure(state=equipment_state)
        search_state = "normal" if equipment else "disabled"
        self.pv_module_search_button.configure(state=search_state)
        self.pv_inverter_search_button.configure(state=search_state)
        for entry in self.pv_equipment_entries:
            entry.configure(state="normal" if equipment else "disabled")

        for widget in (
            self.location_query_entry,
            self.location_search_button,
            self.show_coordinates_checkbutton,
        ):
            widget.configure(state="normal" if weather_method else "disabled")
        for entry in self.pv_coordinate_entries:
            entry.configure(state="normal" if weather_method else "disabled")

        self._update_equipment_summary()
        if hasattr(self, "profile_explanation"):
            self._update_profile_controls()

    def _ensure_cec_options_loaded(self) -> None:
        """Load CEC names once without placing thousands in a combobox."""

        if self._cec_options_loaded:
            return
        self._cec_module_options = tuple(cec_module_names())
        self._cec_inverter_options = tuple(cec_inverter_names())
        self._cec_options_loaded = True

    def _open_cec_search(self, equipment_kind: str) -> None:
        """Open a searchable picker for a CEC module or inverter."""

        self._ensure_cec_options_loaded()
        if equipment_kind == "module":
            title = "Find CEC Module"
            noun = "modules"
            names = self._cec_module_options
            variable = self.values["pv_module_name"]
        elif equipment_kind == "inverter":
            title = "Find CEC Inverter"
            noun = "inverters"
            names = self._cec_inverter_options
            variable = self.values["pv_inverter_name"]
        else:
            raise ValueError(f"Unsupported CEC equipment kind: {equipment_kind!r}.")

        dialog = tk.Toplevel(self.window)
        dialog.title(title)
        dialog.geometry("780x560")
        dialog.minsize(620, 420)
        dialog.transient(self.window)
        dialog.grab_set()

        body = ttk.Frame(dialog, padding=18)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(3, weight=1)

        ttk.Label(
            body,
            text=(
                "Search by manufacturer, model, or several terms. "
                "All terms must match."
            ),
            wraplength=720,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        query = tk.StringVar()
        query_entry = ttk.Entry(body, textvariable=query)
        query_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        clear_button = ttk.Button(body, text="Clear", command=lambda: query.set(""))
        clear_button.grid(row=1, column=1)

        status = tk.StringVar()
        ttk.Label(body, textvariable=status).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(8, 5)
        )

        results_frame = ttk.Frame(body)
        results_frame.grid(row=3, column=0, columnspan=2, sticky="nsew")
        results_frame.rowconfigure(0, weight=1)
        results_frame.columnconfigure(0, weight=1)
        results = tk.Listbox(results_frame, exportselection=False)
        results.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            results_frame, orient="vertical", command=results.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        results.configure(yscrollcommand=scrollbar.set)

        controls = ttk.Frame(body)
        controls.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        select_button = ttk.Button(controls, text="Use Selected", state="disabled")
        select_button.pack(side="right")
        ttk.Button(controls, text="Cancel", command=dialog.destroy).pack(
            side="right", padx=(0, 8)
        )

        visible_names: list[str] = []
        scheduled_refresh = {"id": None}

        def refresh_results() -> None:
            scheduled_refresh["id"] = None
            matches, total = filter_cec_equipment_names(names, query.get())
            visible_names[:] = matches
            results.delete(0, tk.END)
            for name in matches:
                results.insert(tk.END, format_cec_equipment_name(name))
            select_button.configure(state="disabled")
            if total > len(matches):
                status.set(
                    f"Showing {len(matches):,} of {total:,} matching {noun}. "
                    "Add another search term to narrow the results."
                )
            else:
                status.set(f"{total:,} matching {noun}.")

        def schedule_refresh(*_args) -> None:
            pending = scheduled_refresh["id"]
            if pending is not None:
                dialog.after_cancel(pending)
            scheduled_refresh["id"] = dialog.after(120, refresh_results)

        def update_selection_state(_event=None) -> None:
            select_button.configure(
                state="normal" if results.curselection() else "disabled"
            )

        def use_selected(_event=None) -> None:
            selection = results.curselection()
            if not selection:
                return
            variable.set(visible_names[int(selection[0])])
            self._update_equipment_summary()
            dialog.destroy()

        query.trace_add("write", schedule_refresh)
        results.bind("<<ListboxSelect>>", update_selection_state)
        results.bind("<Double-Button-1>", use_selected)
        select_button.configure(command=use_selected)
        query_entry.bind("<Return>", lambda _event: refresh_results())
        refresh_results()
        query_entry.focus_set()

    def _search_site_location(self) -> None:
        """Geocode the typed place and fill in the coordinates.

        A failure leaves the existing latitude and longitude exactly as they
        were: the search is a convenience for finding coordinates, and a
        provider being unreachable is no reason to lose ones that were already
        correct.
        """

        query = str(self.values["location_query"].get())

        try:
            location = self.location_search.search(query)
        except GeocodingError as error:
            self.location_result_label.configure(
                text=f"Location search failed: {error}"
            )
            return

        # Fixed decimals, not significant figures: %g would render a
        # longitude near -122 with three decimal places and quietly throw away
        # about a hundred metres of the provider's answer.
        self.values["pv_latitude"].set(f"{location.latitude:.6f}")
        self.values["pv_longitude"].set(f"{location.longitude:.6f}")
        self.location_result_label.configure(
            text=f"Selected: {location.summary()}"
        )

    def _nsrdb_request(self) -> NSRDBRequest:
        """Build the retrieval described by the form, or raise ValueError."""

        try:
            year = int(str(self.values["nsrdb_year"].get()).strip())
        except (TypeError, ValueError) as error:
            raise ValueError(
                "NSRDB year must be a whole calendar year, for example 2023."
            ) from error

        try:
            latitude = float(self.values["pv_latitude"].get())
            longitude = float(self.values["pv_longitude"].get())
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Latitude and longitude must be numbers. Search for the site "
                "in Site Location, or open Advanced and type them in."
            ) from error

        return NSRDBRequest(
            latitude=latitude,
            longitude=longitude,
            year=year,
            timezone=str(self.values["timezone"].get()),
            time_step_minutes=int(
                str(self.values["nsrdb_time_step_minutes"].get())
            ),
        )

    def _fetch_nsrdb_weather(self) -> None:
        """Retrieve NSRDB weather, on an explicit press, off the GUI thread.

        Retrieval is never triggered by a field changing. It reaches a metered
        external service, so it happens when a person asks for it and at no
        other time.
        """

        if self.nsrdb_fetch_thread is not None and self.nsrdb_fetch_thread.is_alive():
            return

        try:
            request = self._nsrdb_request()
        except (ValueError, NSRDBError) as error:
            self.nsrdb_status_label.configure(text=f"Cannot fetch: {error}")
            return

        destination = (
            GUI_PREFERENCES_PATH.parent
            / "weather"
            / f"nsrdb_{request.latitude:.4f}_{request.longitude:.4f}"
            f"_{request.year}_{request.time_step_minutes}min.csv"
        )

        self.fetch_weather_button.configure(state="disabled")
        self.nsrdb_status_label.configure(
            text=(
                f"Requesting {request.year} NSRDB weather for "
                f"{request.latitude:.4f}, {request.longitude:.4f}…"
            )
        )

        results: queue.Queue = queue.Queue()

        def retrieve() -> None:
            try:
                weather = fetch_nsrdb_weather(request)
                saved = save_weather_csv(weather.frame, destination)
                results.put(("ok", weather, saved))
            except Exception as error:  # surfaced verbatim below
                results.put(("error", error, None))

        self.nsrdb_fetch_thread = threading.Thread(target=retrieve, daemon=True)
        self.nsrdb_fetch_thread.start()
        self.window.after(200, lambda: self._poll_nsrdb_fetch(results))

    def _poll_nsrdb_fetch(self, results: "queue.Queue") -> None:
        """Report a finished retrieval without blocking the interface."""

        try:
            outcome, payload, saved_path = results.get_nowait()
        except queue.Empty:
            self.window.after(200, lambda: self._poll_nsrdb_fetch(results))
            return

        self._update_pv_controls()

        if outcome == "error":
            self.nsrdb_status_label.configure(
                text=f"Weather retrieval failed: {payload}"
            )
            return

        # The retrieval is saved as a weather CSV and the CSV path is what the
        # analysis reads, so a fetched year costs one request and every later
        # run is offline.
        self.values["weather_csv_path"].set(str(saved_path))

        message = (
            f"Retrieved {len(payload.frame)} intervals and saved "
            f"{Path(saved_path).name}."
        )
        if payload.warnings:
            message += " " + " ".join(payload.warnings)
        self.nsrdb_status_label.configure(text=message)

    def _selected_pv_profile_mode(self) -> str:
        """The backend profile mode the current three selections describe."""

        return resolve_pv_profile_mode(
            str(self.values["pv_profile_method"].get()),
            str(self.values["pv_system_model"].get()),
        )

    def _equipment_configuration(self):
        """Build and validate the Phase 2 plant currently shown in the form."""

        return build_equipment_pv_configuration(
            latitude=float(self.values["pv_latitude"].get()),
            longitude=float(self.values["pv_longitude"].get()),
            tilt_degrees=float(self.values["pv_tilt_degrees"].get()),
            azimuth_degrees=float(self.values["pv_azimuth_degrees"].get()),
            module_name=str(self.values["pv_module_name"].get()),
            inverter_name=str(self.values["pv_inverter_name"].get()),
            modules_per_string=int(
                self.values["pv_modules_per_string"].get()
            ),
            strings=int(self.values["pv_strings"].get()),
            inverter_count=int(self.values["pv_inverter_count"].get()),
            mppt_input_count=int(
                self.values["pv_mppt_input_count"].get()
            ),
        )

    def _update_equipment_summary(self, _event=None) -> None:
        """Show the ratings derived from the selected modules and inverters."""

        active = (
            self.values["source_mode"].get() == "live_api"
            and self.values["pv_profile_method"].get() == "weather"
            and self.values["pv_system_model"].get() == "cec_equipment"
        )
        if not active:
            self.pv_equipment_summary.configure(text="")
            return
        try:
            configuration = self._equipment_configuration()
            text = describe_equipment_ratings(configuration)
        except (TypeError, ValueError) as error:
            text = f"Equipment design needs attention: {error}"
        self.pv_equipment_summary.configure(text=text)

    def _refresh_review(self) -> None:
        try:
            weights = parse_carbon_weights(
                str(self.values["carbon_weight_mode"].get()),
                single=str(self.values["carbon_weight_single"].get()),
                explicit_list=str(self.values["carbon_weight_list"].get()),
                range_start=str(self.values["carbon_weight_start"].get()),
                range_end=str(self.values["carbon_weight_end"].get()),
                range_interval=str(self.values["carbon_weight_interval"].get()),
            )
        except ValueError as error:
            weights = [f"Invalid: {error}"]

        strategies = selected_strategies(self.strategy_values)
        source_mode = str(self.values["source_mode"].get())
        battery_active = any(name != "no_battery" for name in strategies)
        pv_equipment_rating = ""
        if (
            source_mode == "live_api"
            and self.values["pv_profile_method"].get() == "weather"
            and self.values["pv_system_model"].get() == "cec_equipment"
        ):
            try:
                configuration = self._equipment_configuration()
                pv_equipment_rating = (
                    f"{configuration.rated_dc_capacity_kw:.2f} kW DC, "
                    f"{configuration.inverter_ac_capacity_kw:.2f} kW AC "
                    f"(DC/AC {configuration.dc_ac_ratio:.2f})"
                )
            except (TypeError, ValueError) as error:
                pv_equipment_rating = f"Invalid equipment design: {error}"


        rows = build_review_rows(
            source_mode=source_mode,
            region_id=str(self.values["region_id"].get()),
            start_date=str(self.values["start_date"].get()),
            end_date_inclusive=str(self.values["end_date_inclusive"].get()),
            timestep_minutes=str(self.values["timestep_minutes"].get()),
            price_mode=str(self.values["price_mode"].get()),
            strategies=strategies,
            carbon_weights=tuple(map(str, weights)),
            degradation_cost=str(self.values["degradation_cost"].get()),
            battery_active=battery_active,
            battery_capacity=str(self.values["battery_capacity"].get()),
            battery_initial_energy=str(self.values["battery_initial_energy"].get()),
            battery_max_charge=str(self.values["battery_max_charge"].get()),
            battery_max_discharge=str(self.values["battery_max_discharge"].get()),
            pv_capacity=str(self.values["pv_capacity"].get()),
            pv_equipment_rating=pv_equipment_rating,
            pv_profile_method=str(self.values["pv_profile_method"].get()),
            weather_source=str(self.values["weather_source"].get()),
            pv_system_model=str(self.values["pv_system_model"].get()),
            pv_capacity_factor_csv_path=str(
                self.values["pv_capacity_factor_csv_path"].get()
            ),
            weather_csv_path=str(self.values["weather_csv_path"].get()),
            location_query=str(self.values["location_query"].get()),
            pv_tilt_degrees=str(self.values["pv_tilt_degrees"].get()),
            pv_azimuth_degrees=str(self.values["pv_azimuth_degrees"].get()),
            pv_latitude=str(self.values["pv_latitude"].get()),
            pv_longitude=str(self.values["pv_longitude"].get()),
            pv_module_name=str(self.values["pv_module_name"].get()),
            pv_inverter_name=str(self.values["pv_inverter_name"].get()),
            load_power=str(self.values["load_power"].get()),
            load_profile_mode=str(self.values["load_profile_mode"].get()),
            load_archetype=str(self.values["load_archetype"].get()),
            load_variability=str(self.values["load_variability"].get()),
            tariff_id=str(self.values["tariff_id"].get()),
            meter_topology_mode=str(
                self.values["meter_topology_mode"].get()
            ),
            submeter_count=str(self.values["submeter_count"].get()),
            previous_peak_kw=str(self.values["previous_peak_kw"].get()),
        )
        self._render_review_table(rows)

    def _render_review_table(
        self,
        rows: tuple[tuple[str, str, str], ...],
    ) -> None:
        """Render the review settings as explicitly bordered cells."""

        for child in self.review_table_frame.winfo_children():
            child.destroy()

        headings = ("Section", "Setting", "Selected value")

        for column_index, heading in enumerate(headings):
            tk.Label(
                self.review_table_frame,
                text=heading,
                font=("Arial", 12, "bold"),
                background="#d9e3f0",
                relief="solid",
                borderwidth=1,
                padx=12,
                pady=8,
            ).grid(row=0, column=column_index, sticky="nsew")

        for row_index, row_values in enumerate(rows, start=1):
            background = "#ffffff" if row_index % 2 else "#f3f6f9"

            for column_index, value in enumerate(row_values):
                font = (
                    ("Arial", 11, "bold")
                    if column_index == 0
                    else ("Arial", 11)
                )
                tk.Label(
                    self.review_table_frame,
                    text=value,
                    font=font,
                    background=background,
                    relief="solid",
                    borderwidth=1,
                    padx=12,
                    pady=7,
                    anchor="w",
                    justify="left",
                ).grid(row=row_index, column=column_index, sticky="nsew")

        self.review_table_frame.update_idletasks()
        self.review_canvas.configure(
            scrollregion=self.review_canvas.bbox("all")
        )

    def _validate_and_run_analysis(self) -> None:
        """Validate the form and start CSV analysis outside the GUI thread."""

        try:
            days = calculate_inclusive_day_count(
                str(self.values["start_date"].get()),
                str(self.values["end_date_inclusive"].get()),
            )
            timestep = int(str(self.values["timestep_minutes"].get()))
            if timestep <= 0:
                raise ValueError("Timestep must be positive.")
            weights = parse_carbon_weights(
                str(self.values["carbon_weight_mode"].get()),
                single=str(self.values["carbon_weight_single"].get()),
                explicit_list=str(self.values["carbon_weight_list"].get()),
                range_start=str(self.values["carbon_weight_start"].get()),
                range_end=str(self.values["carbon_weight_end"].get()),
                range_interval=str(self.values["carbon_weight_interval"].get()),
            )
            if self.values["source_mode"].get() == "integrated_csv" and not self.values["signal_csv_path"].get():
                raise ValueError("Select an integrated signal CSV file.")

            strategies = selected_strategies(self.strategy_values)

            if not any(name != "no_battery" for name in strategies):
                raise ValueError(
                    "The GUI-only no-battery execution path is not connected yet. "
                    "Select at least one battery strategy for this first CSV test."
                )

            battery = Battery(
                capacity_kWh=float(self.values["battery_capacity"].get()),
                energy_kWh=float(self.values["battery_initial_energy"].get()),
                max_charge_kw=float(self.values["battery_max_charge"].get()),
                max_discharge_kw=float(self.values["battery_max_discharge"].get()),
            )
            pv_profile_mode = self._selected_pv_profile_mode()
            pv_capacity_kw = (
                0.0
                if pv_profile_mode == "weather_equipment"
                else float(self.values["pv_capacity"].get())
            )
            degradation_cost = float(self.values["degradation_cost"].get())
            load_variability = float(self.values["load_variability"].get())
            if not 0 <= load_variability <= 1:
                raise ValueError(
                    "Synthetic load variability must be between 0 and 1."
                )
            pv_model_arguments = {}
            if str(self.values["source_mode"].get()) == "live_api":
                if pv_profile_mode not in PV_PROFILE_LABELS:
                    raise ValueError("Select a supported PV profile method.")
                if pv_profile_mode == "capacity_factor_csv":
                    pv_profile_path = str(
                        self.values["pv_capacity_factor_csv_path"].get()
                    ).strip()
                    if not pv_profile_path:
                        raise ValueError(
                            "Select a PV capacity-factor CSV file."
                        )
                    pv_model_arguments = {
                        "pv_capacity_factor_csv_path": pv_profile_path,
                    }
                else:
                    weather_path = str(self.values["weather_csv_path"].get()).strip()
                    if not weather_path:
                        # Both weather sources end at a CSV on disk: an
                        # upload names one directly, and a retrieval saves
                        # one. Saying which is missing depends on which
                        # source the user picked.
                        raise ValueError(
                            "Select a weather CSV for the PV model."
                            if str(self.values["weather_source"].get()) == "csv"
                            else "Press Fetch Weather to retrieve NSRDB data "
                            "before running the analysis."
                        )
                    pv_model_arguments = {
                        "weather_csv_path": weather_path,
                        "pv_latitude": float(self.values["pv_latitude"].get()),
                        "pv_longitude": float(self.values["pv_longitude"].get()),
                        "pv_tilt_degrees": float(self.values["pv_tilt_degrees"].get()),
                        "pv_azimuth_degrees": float(self.values["pv_azimuth_degrees"].get()),
                    }
                    if pv_profile_mode == "weather_generic":
                        pv_model_arguments["pv_dc_ac_ratio"] = float(
                            self.values["pv_dc_ac_ratio"].get()
                        )
                    else:
                        pv_model_arguments.update({
                            "pv_module_name": str(self.values["pv_module_name"].get()),
                            "pv_inverter_name": str(self.values["pv_inverter_name"].get()),
                            "pv_modules_per_string": int(self.values["pv_modules_per_string"].get()),
                            "pv_strings": int(self.values["pv_strings"].get()),
                            "pv_inverter_count": int(self.values["pv_inverter_count"].get()),
                            "pv_mppt_input_count": int(self.values["pv_mppt_input_count"].get()),
                        })
                        equipment = self._equipment_configuration()
                        pv_capacity_kw = equipment.rated_dc_capacity_kw
            specification = MicrogridSpecification(
                battery=battery,
                pv_capacity_kw=pv_capacity_kw,
                load_kw=float(self.values["load_power"].get()),
            )
            if pv_profile_mode == "weather_equipment":
                self.values["pv_capacity"].set(f"{pv_capacity_kw:.6g}")

            price_mode = str(self.values["price_mode"].get())
            previous_peak_text = str(
                self.values["previous_peak_kw"].get()
            ).strip()
            previous_peak_kw = (
                float(previous_peak_text)
                if previous_peak_text
                else None
            )
            selected_tariff_id = str(self.values["tariff_id"].get())
            if (
                price_mode == "time_of_use"
                and selected_tariff_id
                and not get_tariff(selected_tariff_id).demand_charges
            ):
                previous_peak_kw = None
            if previous_peak_kw is not None and previous_peak_kw < 0:
                raise ValueError(
                    "Earlier billing-month peak must not be negative."
                )
            submeter_count = int(
                str(self.values["submeter_count"].get())
            )
            if (
                price_mode == "time_of_use"
                and self.values["meter_topology_mode"].get()
                == "master_with_submeters"
                and submeter_count < 1
            ):
                raise ValueError("Submeter count must be at least 1.")
        except ValueError as error:
            messagebox.showerror("Invalid analysis setup", str(error), parent=self.window)
            return

        source_mode = str(self.values["source_mode"].get())
        self._save_preferences()
        self._update_analysis_details(
            source_mode=source_mode,
            timestep_minutes=timestep,
        )
        self.show_page("results")
        self.progress_message.set(
            "Loading CSV and running dispatch optimization..."
            if source_mode == "integrated_csv"
            else "Retrieving live price and carbon signals..."
        )
        self._set_analysis_message(
            "Analysis is running. The window will remain responsive."
        )
        self._clear_results_table()
        self._clear_results_chart()
        self.export_results_button.configure(state="disabled")
        self.analysis_result = None
        self.run_analysis_button.configure(state="disabled")
        self.analysis_started_at = time.perf_counter()
        self.elapsed_message.set("Elapsed time: 0.0 seconds")
        self.analysis_progress.configure(
            mode="determinate",
            maximum=100,
            value=2,
        )

        common_arguments = {
            "specification": specification,
            "start_date": str(self.values["start_date"].get()),
            "number_of_days": days,
            "timestep_minutes": timestep,
            "selected_scenarios": strategies,
            "carbon_weights": tuple(float(weight) for weight in weights),
            "degradation_cost_per_kWh": degradation_cost,
            "include_degradation_in_optimization": (
                str(self.values["include_degradation_in_optimization"].get()) == "true"
            ),
        }

        if source_mode == "integrated_csv":
            worker_kind = "integrated_csv"
            worker_arguments = {
                **common_arguments,
                "csv_path": str(self.values["signal_csv_path"].get()),
                "expected_timezone": str(self.values["timezone"].get()),
                "tariff_id": str(self.values["tariff_id"].get()) or None,
                "meter_topology_mode": str(
                    self.values["meter_topology_mode"].get()
                ),
                "submeter_count": submeter_count,
                "previous_peak_kw": previous_peak_kw,
            }
        else:
            worker_kind = "live_api"
            worker_arguments = {
                **common_arguments,
                "region_id": str(self.values["region_id"].get()),
                "market_provider": str(self.values["market_provider"].get()),
                "market_location": str(self.values["market_location"].get()),
                "carbon_provider": str(self.values["carbon_provider"].get()),
                "carbon_zone": str(self.values["carbon_zone"].get()),
                "timezone": str(self.values["timezone"].get()),
                "price_mode": price_mode,
                "fixed_retail_price": (
                    float(self.values["fixed_retail_price"].get())
                    if price_mode == "fixed_retail"
                    else None
                ),
                "price_csv_path": str(self.values["price_csv_path"].get()) or None,
                "load_profile_mode": str(
                    self.values["load_profile_mode"].get()
                ),
                "load_archetype": str(
                    self.values["load_archetype"].get()
                ),
                "load_variability_fraction": load_variability,
                "pv_profile_mode": pv_profile_mode,
                **pv_model_arguments,
                "tariff_id": str(self.values["tariff_id"].get()),
                "meter_topology_mode": str(
                    self.values["meter_topology_mode"].get()
                ),
                "submeter_count": submeter_count,
                "previous_peak_kw": previous_peak_kw,
            }

        self.analysis_export_parameters = self._current_export_parameters()

        if self.analysis_messages is None:
            self.analysis_messages = self.process_context.Queue()
        self.analysis_process = self.process_context.Process(
            target=_run_csv_worker_process,
            args=(self.analysis_messages, worker_kind, worker_arguments),
            daemon=True,
        )
        self.analysis_process.start()
        self.worker_exit_empty_polls = 0
        self.window.after(100, self._poll_analysis_messages)

    def _update_analysis_details(
        self,
        *,
        source_mode: str,
        timestep_minutes: int,
    ) -> None:
        """Show the identifying settings for the current analysis run."""

        details = build_analysis_details(
            source_mode=source_mode,
            region_id=str(self.values["region_id"].get()),
            market_location=str(self.values["market_location"].get()),
            csv_path=str(self.values["signal_csv_path"].get()),
            start_date=str(self.values["start_date"].get()),
            end_date_inclusive=str(self.values["end_date_inclusive"].get()),
            timestep_minutes=timestep_minutes,
        )

        for label, value in details:
            self.analysis_detail_values[label].set(value)

    def _poll_analysis_messages(self) -> None:
        """Process a completed worker message without blocking Tkinter."""

        if self.is_closing or self.analysis_messages is None:
            return

        if self.analysis_started_at is not None:
            elapsed = time.perf_counter() - self.analysis_started_at
            self.elapsed_message.set(
                f"Elapsed time: {format_runtime(elapsed)}"
            )

        try:
            status, payload = self.analysis_messages.get_nowait()
        except queue.Empty:
            if (
                self.analysis_process is not None
                and not self.analysis_process.is_alive()
            ):
                self.worker_exit_empty_polls += 1

                if self.worker_exit_empty_polls >= 10:
                    exit_code = self.analysis_process.exitcode
                    self.run_analysis_button.configure(state="normal")
                    elapsed = (
                        time.perf_counter() - self.analysis_started_at
                        if self.analysis_started_at is not None
                        else 0.0
                    )
                    self.analysis_started_at = None
                    self.elapsed_message.set(
                        f"Stopped after: {format_runtime(elapsed)}"
                    )
                    self.progress_message.set("Analysis worker stopped unexpectedly.")
                    self._set_analysis_message(
                        "The simulation worker exited without returning a result. "
                        f"Exit code: {exit_code}."
                    )
                    self._release_finished_analysis_process()
                    return

            self.window.after(100, self._poll_analysis_messages)
            return

        if status == "progress":
            progress_percent, progress_text = payload
            self.analysis_progress.configure(value=progress_percent)
            self.progress_message.set(
                f"{progress_text} ({progress_percent:.0f}%)"
            )
            self.window.after(100, self._poll_analysis_messages)
            return

        self.run_analysis_button.configure(state="normal")
        self._release_finished_analysis_process()

        elapsed = (
            time.perf_counter() - self.analysis_started_at
            if self.analysis_started_at is not None
            else 0.0
        )
        self.analysis_started_at = None

        if status == "error":
            self.elapsed_message.set(
                f"Stopped after: {format_runtime(elapsed)}"
            )
            self.progress_message.set("Analysis failed.")
            error_name, error_message = payload
            display_message = f"{error_name}: {error_message}"
            self._set_analysis_message(display_message)
            messagebox.showerror("Analysis failed", display_message, parent=self.window)
            return

        self.analysis_result = payload
        self.analysis_progress.configure(
            mode="determinate",
            maximum=100,
            value=100,
        )
        self.elapsed_message.set(
            f"Total runtime: {format_runtime(elapsed)}"
        )
        self.progress_message.set(
            f"Analysis complete: {len(payload.comparison)} scenario result(s)."
        )
        self._set_analysis_message(
            (
                " ".join(payload.warnings)
                if payload.warnings
                else "Scroll horizontally to inspect every reported metric."
            )
        )
        self._render_results_table(payload.comparison)
        metrics = available_comparison_metrics(payload.comparison)
        self.comparison_metric_selector.configure(
            values=metrics, state="readonly" if metrics else "disabled"
        )
        self.comparison_metric.set(metrics[0] if metrics else "")
        self._render_results_chart()
        self._render_pv_diagnostics()
        self.export_pv_diagnostics_button.configure(
            state="normal" if payload.pv_diagnostics is not None else "disabled"
        )
        self.export_results_button.configure(state="normal")

    def _export_results_csv(self) -> None:
        """Save displayed scenario results with their input configuration."""

        if (
            self.analysis_result is None
            or self.analysis_export_parameters is None
        ):
            messagebox.showerror(
                "No analysis results",
                "Run an analysis before exporting results.",
                parent=self.window,
            )
            return

        default_name = (
            "microgrid_analysis_"
            f"{self.values['start_date'].get()}_to_"
            f"{self.values['end_date_inclusive'].get()}.csv"
        )
        selected_path = filedialog.asksaveasfilename(
            parent=self.window,
            title="Export microgrid analysis results",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV files", "*.csv")],
        )

        if not selected_path:
            return

        try:
            export_table = build_results_export_table(
                self.analysis_result.comparison,
                self.analysis_export_parameters,
                warnings=self.analysis_result.warnings,
            )
            output_path = Path(selected_path)
            export_table.to_csv(output_path, index=False)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Export failed",
                str(error),
                parent=self.window,
            )
            return

        messagebox.showinfo(
            "Export complete",
            f"Results saved to:\n{output_path}",
            parent=self.window,
        )

    def _current_export_parameters(self) -> dict[str, object]:
        """Collect the GUI inputs that produced the current result table."""

        source_mode = str(self.values["source_mode"].get())
        price_mode = str(self.values["price_mode"].get())
        topology_mode = str(self.values["meter_topology_mode"].get())
        live = source_mode == "live_api"
        tariff_active = live and price_mode == "time_of_use"
        synthetic_load = (
            live
            and self.values["load_profile_mode"].get() == "synthetic"
        )
        pv_profile_method = str(self.values["pv_profile_method"].get())
        weather_source = str(self.values["weather_source"].get())
        pv_system_model = str(self.values["pv_system_model"].get())
        pv_profile_mode = self._selected_pv_profile_mode()
        weather_pv = live and pv_profile_method == "weather"
        capacity_factor_pv = live and pv_profile_method == "capacity_factor_csv"
        equipment_pv = weather_pv and pv_system_model == "cec_equipment"
        equipment = self._equipment_configuration() if equipment_pv else None

        return {
            "input_data_source": source_mode,
            "input_signal_csv_path": (
                "" if live else str(self.values["signal_csv_path"].get())
            ),
            "input_region_id": (
                str(self.values["region_id"].get()) if live else ""
            ),
            "input_market_provider": (
                str(self.values["market_provider"].get()) if live else ""
            ),
            "input_market_location": (
                str(self.values["market_location"].get()) if live else ""
            ),
            "input_carbon_provider": (
                str(self.values["carbon_provider"].get()) if live else ""
            ),
            "input_carbon_zone": (
                str(self.values["carbon_zone"].get()) if live else ""
            ),
            "input_timezone": str(self.values["timezone"].get()),
            "input_start_date": str(self.values["start_date"].get()),
            "input_end_date_inclusive": str(
                self.values["end_date_inclusive"].get()
            ),
            "input_timestep_minutes": int(
                str(self.values["timestep_minutes"].get())
            ),
            "input_price_mode": price_mode if live else "integrated_csv",
            "input_tariff_id": (
                str(self.values["tariff_id"].get())
                if tariff_active
                else ""
            ),
            "input_meter_topology": (
                topology_mode if tariff_active else ""
            ),
            "input_submeter_count": (
                int(str(self.values["submeter_count"].get()))
                if tariff_active
                and topology_mode == "master_with_submeters"
                else ""
            ),
            "input_previous_peak_kw": (
                str(self.values["previous_peak_kw"].get()).strip()
                if tariff_active
                else ""
            ),
            "input_selected_strategies": ",".join(
                selected_strategies(self.strategy_values)
            ),
            "input_carbon_weight_mode": str(
                self.values["carbon_weight_mode"].get()
            ),
            "input_carbon_weights": _format_current_carbon_weights(
                self.values
            ),
            "input_degradation_cost_per_kwh": float(
                self.values["degradation_cost"].get()
            ),
            "input_include_degradation_in_optimization": (
                "include_degradation_in_optimization" in self.values
                and str(self.values["include_degradation_in_optimization"].get()) == "true"
            ),
            "input_battery_capacity_kwh": float(
                self.values["battery_capacity"].get()
            ),
            "input_battery_initial_energy_kwh": float(
                self.values["battery_initial_energy"].get()
            ),
            "input_battery_max_charge_kw": float(
                self.values["battery_max_charge"].get()
            ),
            "input_battery_max_discharge_kw": float(
                self.values["battery_max_discharge"].get()
            ),
            "input_pv_capacity_kw": (
                equipment.rated_dc_capacity_kw
                if equipment is not None
                else float(self.values["pv_capacity"].get())
            ),
            # The derived backend mode is kept for continuity with earlier
            # exports; the three selections beside it are what the interface
            # actually asked, and are what a later reader needs to reproduce
            # the run.
            "input_pv_profile_mode": (
                pv_profile_mode if live else "integrated_csv"
            ),
            "input_pv_profile_method": (
                pv_profile_method if live else "integrated_csv"
            ),
            "input_weather_source": (
                weather_source if weather_pv else ""
            ),
            "input_pv_system_model": (
                pv_system_model if weather_pv else ""
            ),
            "input_pv_location_query": (
                str(self.values["location_query"].get()) if weather_pv else ""
            ),
            "input_nsrdb_year": (
                str(self.values["nsrdb_year"].get())
                if weather_pv and weather_source == "nsrdb"
                else ""
            ),
            "input_nsrdb_time_step_minutes": (
                str(self.values["nsrdb_time_step_minutes"].get())
                if weather_pv and weather_source == "nsrdb"
                else ""
            ),
            "input_weather_csv_path": (
                str(self.values["weather_csv_path"].get())
                if weather_pv
                else ""
            ),
            "input_pv_capacity_factor_csv_path": (
                str(self.values["pv_capacity_factor_csv_path"].get())
                if capacity_factor_pv
                else ""
            ),
            "input_pv_latitude": (
                str(self.values["pv_latitude"].get()) if weather_pv else ""
            ),
            "input_pv_longitude": (
                str(self.values["pv_longitude"].get()) if weather_pv else ""
            ),
            "input_pv_module_name": (
                str(self.values["pv_module_name"].get())
                if equipment_pv
                else ""
            ),
            "input_pv_inverter_name": (
                str(self.values["pv_inverter_name"].get())
                if equipment_pv
                else ""
            ),
            "input_pv_tilt_degrees": (
                float(self.values["pv_tilt_degrees"].get()) if weather_pv else ""
            ),
            "input_pv_azimuth_degrees": (
                float(self.values["pv_azimuth_degrees"].get()) if weather_pv else ""
            ),
            "input_pv_dc_ac_ratio": (
                float(self.values["pv_dc_ac_ratio"].get())
                if weather_pv and pv_system_model == "generic"
                else (equipment.dc_ac_ratio if equipment is not None else "")
            ),
            "input_pv_inverter_ac_capacity_kw": (
                equipment.inverter_ac_capacity_kw
                if equipment is not None
                else ""
            ),
            "input_pv_modules_per_string": (
                int(self.values["pv_modules_per_string"].get())
                if equipment_pv else ""
            ),
            "input_pv_parallel_strings": (
                int(self.values["pv_strings"].get()) if equipment_pv else ""
            ),
            "input_pv_inverter_count": (
                int(self.values["pv_inverter_count"].get())
                if equipment_pv else ""
            ),
            "input_pv_mppt_inputs_per_inverter": (
                int(self.values["pv_mppt_input_count"].get())
                if equipment_pv else ""
            ),
            "input_pv_control_mode": (
                "grid_following" if equipment_pv else ""
            ),
            "input_load_profile_mode": (
                str(self.values["load_profile_mode"].get())
                if live
                else "integrated_csv"
            ),
            "input_load_power_or_peak_kw": (
                float(self.values["load_power"].get()) if live else ""
            ),
            "input_load_archetype": (
                str(self.values["load_archetype"].get())
                if synthetic_load
                else ""
            ),
            "input_load_variability_fraction": (
                float(self.values["load_variability"].get())
                if synthetic_load
                else ""
            ),
        }

    def _release_finished_analysis_process(self) -> None:
        """Join and close a worker after it has returned its final message."""

        process = self.analysis_process

        if process is None:
            return

        process.join(timeout=1.0)

        if process.is_alive():
            return

        process.close()
        self.analysis_process = None

    def _close_application(self) -> None:
        """Release multiprocessing resources before destroying the window."""

        if self.is_closing:
            return

        self.is_closing = True
        process = self.analysis_process

        if process is not None:
            if process.is_alive():
                process.terminate()
            process.join(timeout=2.0)
            if not process.is_alive():
                process.close()
            self.analysis_process = None

        messages = self.analysis_messages
        if messages is not None:
            messages.close()
            messages.join_thread()
            self.analysis_messages = None
        self.window.destroy()

    def _set_analysis_message(self, message: str) -> None:
        """Update the short message shown above the result table."""

        self.result_message.configure(text=message)

    def _clear_results_chart(self) -> None:
        """Discard the previous run's chart before starting another analysis."""
        if self.chart_canvas is not None:
            self.chart_canvas.get_tk_widget().destroy()
            self.chart_canvas.figure.clear()
            self.chart_canvas = None
        self.comparison_metric_selector.configure(values=(), state="disabled")
        self.comparison_metric.set("")
        self.chart_placeholder.configure(text="Run an analysis to compare scenarios.")
        self.chart_placeholder.pack(anchor="w", pady=12)
        if self.pv_chart_canvas is not None:
            self.pv_chart_canvas.get_tk_widget().destroy()
            self.pv_chart_canvas.figure.clear()
            self.pv_chart_canvas = None
        self.pv_detail_message.set(
            "Run a Phase 1 or Phase 2 weather-derived PV analysis."
        )
        self.pv_chart_placeholder.pack(anchor="w", pady=12)
        self.export_pv_diagnostics_button.configure(state="disabled")

    def _render_results_chart(self) -> None:
        """Draw on the Tk thread, reusing the canvas when the metric changes."""
        if self.analysis_result is None or not self.comparison_metric.get():
            self.chart_placeholder.configure(text="No numeric comparison metrics available.")
            return
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure

        self.chart_placeholder.pack_forget()
        if self.chart_canvas is None:
            figure = Figure(figsize=(9, 4), dpi=100, layout="constrained")
            self.chart_canvas = FigureCanvasTkAgg(figure, master=self.chart_host)
            self.chart_canvas.get_tk_widget().pack(fill="both", expand=True)
        draw_comparison(
            self.chart_canvas.figure, self.analysis_result.comparison,
            self.comparison_metric.get(),
        )
        self.chart_canvas.draw_idle()

    def _render_pv_diagnostics(self) -> None:
        """Draw the detailed power stages returned by either weather PV model."""

        if self.analysis_result is None or self.analysis_result.pv_diagnostics is None:
            self.pv_detail_message.set(
                "PV diagnostics are unavailable for synthetic and imported profiles."
            )
            self.pv_chart_placeholder.pack(anchor="w", pady=12)
            return

        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure

        provenance = self.analysis_result.pv_provenance or {}
        description = provenance.get("description")
        model_version = provenance.get("model_version", "weather-derived PV")
        self.pv_detail_message.set(str(description or model_version))
        self.pv_chart_placeholder.pack_forget()
        if self.pv_chart_canvas is None:
            figure = Figure(figsize=(9, 4), dpi=100, layout="constrained")
            self.pv_chart_canvas = FigureCanvasTkAgg(
                figure, master=self.pv_chart_host
            )
            self.pv_chart_canvas.get_tk_widget().pack(fill="both", expand=True)
        draw_pv_power_stages(
            self.pv_chart_canvas.figure,
            self.analysis_result.pv_diagnostics,
        )
        self.pv_chart_canvas.draw_idle()

    def _export_pv_diagnostics_csv(self) -> None:
        """Export the timestamp-aligned Phase 1 or Phase 2 diagnostic frame."""

        diagnostics = (
            self.analysis_result.pv_diagnostics
            if self.analysis_result is not None
            else None
        )
        if diagnostics is None:
            messagebox.showerror(
                "No PV diagnostics",
                "Run a weather-derived PV analysis before exporting diagnostics.",
                parent=self.window,
            )
            return
        selected_path = filedialog.asksaveasfilename(
            parent=self.window,
            title="Export PV diagnostics",
            defaultextension=".csv",
            initialfile="pv_model_diagnostics.csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not selected_path:
            return
        try:
            diagnostics.to_csv(Path(selected_path), index=False)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "PV diagnostic export failed",
                str(error),
                parent=self.window,
            )


    def _clear_results_table(self) -> None:
        """Remove previously displayed table cells."""

        for child in self.table_frame.winfo_children():
            child.destroy()

        self.table_canvas.configure(height=100)

    def _render_results_table(self, comparison) -> None:
        """Display scenario metrics using bordered rows and columns."""

        self._clear_results_table()
        headings, rows = build_results_table(comparison)

        for column_index, heading in enumerate(headings):
            header = tk.Label(
                self.table_frame,
                text=heading,
                font=("Arial", 11, "bold"),
                background="#d9e3f0",
                relief="solid",
                borderwidth=1,
                padx=10,
                pady=8,
            )
            header.grid(
                row=0,
                column=column_index,
                sticky="nsew",
            )
            self._bind_result_table_scrolling(header)

        for row_index, row_values in enumerate(rows, start=1):
            background = "#ffffff" if row_index % 2 else "#f3f6f9"

            for column_index, value in enumerate(row_values):
                cell = tk.Label(
                    self.table_frame,
                    text=value,
                    font=("Arial", 11),
                    background=background,
                    relief="solid",
                    borderwidth=1,
                    padx=10,
                    pady=8,
                )
                cell.grid(
                    row=row_index,
                    column=column_index,
                    sticky="nsew",
                )
                self._bind_result_table_scrolling(cell)

        visible_height = min(48 + len(rows) * 38, 360)
        self.table_canvas.configure(height=visible_height)
        self.table_frame.update_idletasks()
        self._update_table_scroll_region()

    def _update_table_scroll_region(self, _event=None) -> None:
        """Keep both scroll directions aligned with the rendered table."""

        self.table_canvas.configure(
            scrollregion=self.table_canvas.bbox("all")
        )

    def _bind_result_table_scrolling(self, widget) -> None:
        """Enable mouse and trackpad scrolling over table content."""

        widget.bind(
            "<MouseWheel>",
            self._scroll_result_table_vertical,
        )
        widget.bind(
            "<Shift-MouseWheel>",
            self._scroll_result_table_horizontal,
        )

    def _scroll_result_table_vertical(self, event):
        """Move through scenario rows with a wheel or vertical swipe."""

        if event.delta:
            direction = -1 if event.delta > 0 else 1
            self.table_canvas.yview_scroll(direction, "units")
        return "break"

    def _scroll_result_table_horizontal(self, event):
        """Move through metric columns with Shift-wheel or horizontal swipe."""

        if event.delta:
            direction = -1 if event.delta > 0 else 1
            self.table_canvas.xview_scroll(direction, "units")
        return "break"

def _run_csv_worker_process(
    message_queue,
    worker_kind: str,
    arguments: dict,
) -> None:
    """Run data retrieval and OpenDSS in an isolated worker process."""

    try:
        requested_weights = arguments.get("carbon_weights", ())
        selected_scenarios = arguments.get("selected_scenarios", ())
        analysis_set_count = (
            len(requested_weights)
            if "combined_optimal" in selected_scenarios
            else 1
        )
        setup_step_count = 1 if worker_kind == "integrated_csv" else 2
        total_progress_steps = setup_step_count + 4 * analysis_set_count
        completed_progress_steps = 0

        def report_progress(message: str) -> None:
            nonlocal completed_progress_steps
            completed_progress_steps += 1
            progress_percent = calculate_progress_percentage(
                completed_progress_steps,
                total_progress_steps,
            )
            message_queue.put(
                (
                    "progress",
                    (progress_percent, message),
                )
            )

        arguments = {
            **arguments,
            "progress_callback": report_progress,
        }
        if worker_kind == "integrated_csv":
            result = run_integrated_csv_analysis(**arguments)
        elif worker_kind == "live_api":
            result = run_live_api_analysis(**arguments)
        else:
            raise ValueError(f"Unknown analysis worker kind: {worker_kind}.")
    except Exception as error:
        message_queue.put(
            (
                "error",
                (type(error).__name__, str(error)),
            )
        )
    else:
        message_queue.put(("success", result))


def format_runtime(elapsed_seconds: float) -> str:
    """Format an elapsed duration for the results screen."""

    elapsed_seconds = max(float(elapsed_seconds), 0.0)

    if elapsed_seconds < 60:
        return f"{elapsed_seconds:.1f} seconds"

    minutes, seconds = divmod(elapsed_seconds, 60)

    if minutes < 60:
        return f"{int(minutes)} min {seconds:.1f} sec"

    hours, minutes = divmod(int(minutes), 60)
    return f"{hours} hr {minutes} min {seconds:.1f} sec"


def calculate_progress_percentage(
    completed_steps: int,
    total_steps: int,
) -> float:
    """Map completed backend milestones onto a 5–95% progress range."""

    if total_steps <= 0:
        return 5.0

    bounded_steps = min(max(completed_steps, 0), total_steps)
    return 5.0 + 90.0 * bounded_steps / total_steps


def selected_strategies(strategy_values: dict[str, object]) -> tuple[str, ...]:
    """Return selected strategies in stable display order."""

    return tuple(
        name
        for name in STRATEGY_LABELS
        if bool(strategy_values[name].get())
    )


def build_review_rows(
    *,
    source_mode: str,
    region_id: str,
    start_date: str,
    end_date_inclusive: str,
    timestep_minutes: str,
    price_mode: str,
    strategies: tuple[str, ...],
    carbon_weights: tuple[str, ...],
    degradation_cost: str,
    battery_active: bool,
    battery_capacity: str,
    battery_initial_energy: str,
    battery_max_charge: str,
    battery_max_discharge: str,
    pv_capacity: str,
    load_power: str,
    load_profile_mode: str,
    load_archetype: str,
    load_variability: str,
    tariff_id: str,
    meter_topology_mode: str,
    submeter_count: str,
    previous_peak_kw: str,
    pv_profile_method: str = "capacity_factor_csv",
    weather_source: str = "csv",
    pv_system_model: str = "generic",
    pv_capacity_factor_csv_path: str = "",
    weather_csv_path: str = "",
    location_query: str = "",
    pv_tilt_degrees: str = "",
    pv_azimuth_degrees: str = "",
    pv_latitude: str = "",
    pv_longitude: str = "",
    pv_module_name: str = "",
    pv_inverter_name: str = "",
    pv_equipment_rating: str = "",
) -> tuple[tuple[str, str, str], ...]:
    """Build the rows shown in the Step 3 review table."""

    source_label = SOURCE_MODE_LABELS[source_mode]
    region_label = (
        REGION_LABELS.get(region_id, region_id)
        if source_mode == "live_api"
        else "Not applicable"
    )
    price_label = (
        PRICE_MODE_LABELS[price_mode]
        if source_mode == "live_api"
        else "Included in integrated CSV"
    )
    battery_value = "Active" if battery_active else "Ignored"
    tariff_active = source_mode == "live_api" and price_mode == "time_of_use"
    if tariff_active:
        topology_label = METER_TOPOLOGY_LABELS[meter_topology_mode]
        if meter_topology_mode == "master_with_submeters":
            topology_label += f" ({submeter_count} submeters)"
        if get_tariff(tariff_id).demand_charges:
            prior_peak_label = (
                f"{previous_peak_kw.strip() or 'Unknown'} kW"
            )
        else:
            prior_peak_label = "Not applicable — no demand charge"
    else:
        topology_label = "Not used"
        prior_peak_label = "Not used"
    if source_mode == "live_api":
        load_profile_label = LOAD_PROFILE_LABELS[load_profile_mode]
        load_detail = (
            f"{LOAD_ARCHETYPE_LABELS[load_archetype]}, peak {load_power} kW, "
            f"variability {load_variability}"
            if load_profile_mode == "synthetic"
            else f"{load_power} kW at every interval"
        )
        weather_derived = pv_profile_method == "weather"
        equipment_model = weather_derived and pv_system_model == "cec_equipment"

        pv_profile_label = PV_PROFILE_METHOD_LABELS.get(
            pv_profile_method, pv_profile_method
        )
        if pv_profile_method == "capacity_factor_csv":
            pv_profile_label += (
                f"; {Path(pv_capacity_factor_csv_path).name}; "
                f"rated {pv_capacity} kW"
            )

        if weather_derived:
            pv_weather_label = WEATHER_SOURCE_LABELS.get(
                weather_source, weather_source
            )
            if weather_csv_path:
                pv_weather_label += f"; {Path(weather_csv_path).name}"
            pv_system_label = PV_SYSTEM_MODEL_LABELS.get(
                pv_system_model, pv_system_model
            )
            if equipment_model:
                pv_system_label += (
                    f"; module {pv_module_name}; inverter {pv_inverter_name}"
                )
            else:
                pv_system_label += f"; rated {pv_capacity} kW"
            # Orientation feeds both models and moves the answer by a large
            # fraction, so it belongs in the review whichever one is selected.
            pv_system_label += (
                f"; tilt {pv_tilt_degrees} deg, azimuth "
                f"{pv_azimuth_degrees} deg"
            )
            # The coordinates are what the model actually uses, so they are
            # shown even when a place name found them.
            pv_location_label = f"{pv_latitude}, {pv_longitude}"
            if location_query.strip():
                pv_location_label += f" (searched: {location_query.strip()})"
        else:
            pv_weather_label = "Not used"
            pv_system_label = "Not used"
            pv_location_label = "Not used"
    else:
        load_profile_label = "Integrated CSV load_kw"
        load_detail = "Read from the selected integrated signal file"
        pv_profile_label = "Integrated CSV pv_kw"
        pv_weather_label = "Included in integrated CSV"
        pv_system_label = "Included in integrated CSV"
        pv_location_label = "Not used"
        equipment_model = False

    return (
        ("Analysis", "Data source", source_label),
        ("Analysis", "Region", region_label),
        ("Analysis", "Start date", start_date),
        ("Analysis", "End date (inclusive)", end_date_inclusive),
        ("Analysis", "Time interval", f"{timestep_minutes} minutes"),
        ("Analysis", "Electricity price", price_label),
        (
            "Billing",
            "Retail tariff",
            TARIFF_LABELS.get(tariff_id, tariff_id)
            if tariff_active
            else "Not used",
        ),
        ("Billing", "Meter arrangement", topology_label),
        (
            "Billing",
            "Earlier monthly peak",
            prior_peak_label,
        ),
        (
            "Strategies",
            "Selected scenarios",
            ", ".join(
                STRATEGY_LABELS.get(strategy, strategy)
                for strategy in strategies
            ),
        ),
        ("Strategies", "Combined carbon weights", ", ".join(carbon_weights)),
        (
            "Strategies",
            "Battery degradation cost",
            f"{degradation_cost} $/kWh throughput",
        ),
        ("Microgrid", "Battery", battery_value),
        (
            "Microgrid",
            "Battery capacity",
            f"{battery_capacity} kWh" if battery_active else "Ignored",
        ),
        (
            "Microgrid",
            "Initial battery energy",
            f"{battery_initial_energy} kWh" if battery_active else "Ignored",
        ),
        (
            "Microgrid",
            "Maximum charging power",
            f"{battery_max_charge} kW" if battery_active else "Ignored",
        ),
        (
            "Microgrid",
            "Maximum discharging power",
            f"{battery_max_discharge} kW" if battery_active else "Ignored",
        ),
        (
            "Microgrid",
            "PV capacity",
            pv_equipment_rating or "Invalid equipment design"
            if equipment_model
            else f"{pv_capacity} kW",
        ),
        ("Profiles", "PV profile method", pv_profile_label),
        ("Profiles", "PV weather source", pv_weather_label),
        ("Profiles", "PV system model", pv_system_label),
        ("Profiles", "PV site location", pv_location_label),
        ("Profiles", "Load source", load_profile_label),
        ("Profiles", "Load details", load_detail),
    )


def calculate_inclusive_day_count(
    start_date: str,
    end_date_inclusive: str,
) -> int:
    """Return the number of calendar days when both boundaries are included."""

    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date_inclusive)
    except (TypeError, ValueError) as error:
        raise ValueError("Start and end dates must use YYYY-MM-DD format.") from error

    if end < start:
        raise ValueError("Inclusive end date must not precede the start date.")

    return (end - start).days + 1


def parse_carbon_weights(
    mode: str,
    *,
    single: str,
    explicit_list: str,
    range_start: str,
    range_end: str,
    range_interval: str,
) -> list[Decimal]:
    """Parse one, several, or an inclusive range of carbon weights."""

    try:
        if mode == "single":
            values = [Decimal(single)]
        elif mode == "list":
            values = [Decimal(value.strip()) for value in explicit_list.split(",") if value.strip()]
        elif mode == "range":
            start = Decimal(range_start)
            end = Decimal(range_end)
            interval = Decimal(range_interval)
            if interval <= 0:
                raise ValueError("Carbon-weight range interval must be positive.")
            if end < start:
                raise ValueError("Carbon-weight range end must not precede its start.")
            span = end - start
            if span % interval != 0:
                raise ValueError("Carbon-weight interval must land exactly on the inclusive end value.")
            count = int(span / interval)
            values = [start + interval * index for index in range(count + 1)]
        else:
            raise ValueError(f"Unknown carbon-weight mode: {mode}.")
    except InvalidOperation as error:
        raise ValueError("Carbon weights must be valid numbers.") from error

    if not values:
        raise ValueError("Provide at least one carbon weight.")
    if any(value < 0 for value in values):
        raise ValueError("Carbon weights must not be negative.")
    if len(set(values)) != len(values):
        raise ValueError("Carbon weights must not contain duplicates.")
    return values


def _format_current_carbon_weights(values: dict[str, tk.Variable]) -> str:
    """Return the currently configured carbon weights as CSV-safe text."""

    parsed = parse_carbon_weights(
        str(values["carbon_weight_mode"].get()),
        single=str(values["carbon_weight_single"].get()),
        explicit_list=str(values["carbon_weight_list"].get()),
        range_start=str(values["carbon_weight_start"].get()),
        range_end=str(values["carbon_weight_end"].get()),
        range_interval=str(values["carbon_weight_interval"].get()),
    )
    return ",".join(str(weight) for weight in parsed)


def build_results_export_table(
    comparison,
    parameters: dict[str, object],
    *,
    warnings: tuple[str, ...] = (),
):
    """Build a self-describing scenario table for CSV export."""

    hide_demand_columns = (
        "tariff_has_demand_charge" in comparison.columns
        and not comparison["tariff_has_demand_charge"].astype(bool).any()
    )
    hidden_columns = (
        {"demand_charge", "billed_peak_kw"}
        if hide_demand_columns
        else set()
    )
    result_columns = [
        column
        for column, _label in RESULT_TABLE_COLUMNS
        if column in comparison.columns and column not in hidden_columns
    ]
    export_table = comparison[result_columns].copy()

    for column, value in parameters.items():
        export_table[column] = value

    export_table["analysis_warnings"] = " | ".join(warnings)
    return export_table


def create_guided_application_window() -> tk.Tk:
    """Create the main guided microgrid-analysis window."""

    window = tk.Tk()
    application = MicrogridApplication(window)
    window.microgrid_application = application
    return window
