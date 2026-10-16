from .battery import Battery
from dataclasses import dataclass
from ..signal_pipeline.source_config import resolve_region_config

battery = Battery(
    capacity_kWh = 20.0,
    energy_kWh = 10.0,
    max_charge_kw=5.0,
    max_discharge_kw=5.0
)

@dataclass
## Configuration for the experiment, attributes are set for simpliciy, but for later use,
## it will inclue more parameters for the experiment.
class ExperimentConfig:
    start_date: str
    number_of_days: int

    carbon_weight: float = 0.20
    degradation_cost_per_kWh: float = 0.03
    timestep_hours: float = 0.25

    demand_charge_rate_per_kw: float = 0.0
    previous_peak_kw: float | None = None

    # The region supplies the market provider, price node, carbon zone and
    # timezone. The fields below stay None unless a caller overrides one.
    region: str = "caiso_np15"

    market_location: str | None = None
    electricity_maps_zone: str | None = None
    timezone: str | None = None

    # Deprecated alias for market_location, kept for existing CAISO callers.
    caiso_node: str | None = None

    sleep_seconds: float = 1.0
    provider_options: dict | None = None

    def __post_init__(self) -> None:

        location = self.market_location if self.market_location is not None else self.caiso_node
        region_config = resolve_region_config(
            self.region, market_location=location,
            carbon_zone=self.electricity_maps_zone, timezone=self.timezone,
            provider_options=self.provider_options,
        )

        self.market_provider = region_config.market_provider
        self.carbon_provider = region_config.carbon_provider

        self.market_location = region_config.market_location
        self.electricity_maps_zone = region_config.carbon_zone
        self.timezone = region_config.timezone
        self.provider_options = region_config.provider_options
        self.caiso_node = self.market_location

        if self.number_of_days <= 0:
            raise ValueError("Number of days must be greater than 0.")

        if self.timestep_hours <= 0:
            raise ValueError("timestep_hours must be greater than 0.")

        if self.carbon_weight < 0:
            raise ValueError("Carbon weight must be greater than 0.")

        if self.degradation_cost_per_kWh < 0:
            raise ValueError("Degradation cost per kWh must be greater than 0.")

        if self.demand_charge_rate_per_kw < 0:
            raise ValueError("Demand charge rate must be greater than 0.")

        if self.previous_peak_kw is not None and self.previous_peak_kw < 0:
            raise ValueError("Previous peak kW must be greater than 0.")

        if self.sleep_seconds < 0:
            raise ValueError("Sleep seconds must be greater than 0.")
            
def to_optimizer_parameters(
        self,
) -> dict[str, float]:

    return {
        "capacity_kWh": self.capacity_kWh,
        "initial_soc_kWh": self.energy_kWh,
        "min_soc_kWh": self.minimum_energy_kWh,
        "max_soc_kWh": self.maximum_energy_kWh,
        "max_charge_kw": self.max_charge_kw,
        "max_discharge_kw": self.max_discharge_kw,
        "charge_efficiency": self.charge_efficiency,
        "discharge_efficiency": self.discharge_efficiency
    }

