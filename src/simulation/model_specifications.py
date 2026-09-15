from dataclasses import dataclass
from ..dispatch.battery import Battery
from ..opendss.ac_replay import PVReplayConfiguration

@dataclass
class MicrogridSpecification:
    """Store the physical equipment selected for a simulation."""

    battery: Battery
    pv_capacity_kw: float
    load_kw: float
    pv_replay: PVReplayConfiguration | None = None

    @property
    def pv_ac_capacity_kw(self) -> float:
        """AC terminal limit; legacy profiles use their supplied capacity."""
        return self.pv_replay.rated_ac_kw if self.pv_replay else self.pv_capacity_kw

    def __post_init__(self) -> None:
        """Validate the specification immediately after creation."""

        if not isinstance(self.battery, Battery):
            raise TypeError(
                "battery must be a Battery object"
            )

        if self.pv_capacity_kw < 0:
            raise ValueError(
                "PV capacity must not be negative."
            )

        if self.load_kw < 0:
            raise ValueError(
                "Load power must not be negative."
            )
