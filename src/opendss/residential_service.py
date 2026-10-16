"""Representative 120/240 V service, not a surveyed PG&E installation.

Transformer topology/impedances follow EPRI's center-tapped example. Service
impedance, ampacity and household leg allocation are explicit study assumptions.
"""
from dataclasses import asdict, dataclass, replace
import math

import opendssdirect as dss

from .ac_replay import PVReplayConfiguration, replay_inverters


SOURCE = "https://opendss.epri.com/ModelingSingle-PhaseTransformers.html"


@dataclass(frozen=True)
class ResidentialService:
    transformer_kva: float = 25.
    service_amps: float = 100.
    service_length_km: float = .03
    conductor_r_ohm_per_km: float = .4
    conductor_x_ohm_per_km: float = .1
    # Remaining fraction is a 240 V load. No appliance/leg information is
    # inferred from the aggregate load series.
    l1_load_fraction: float = .4
    l2_load_fraction: float = .4

    def __post_init__(self):
        for name in ("transformer_kva", "service_amps", "service_length_km", "conductor_r_ohm_per_km"):
            if not math.isfinite(getattr(self, name)) or getattr(self, name) <= 0:
                raise ValueError(f"Residential {name} must be finite and positive.")
        if not math.isfinite(self.conductor_x_ohm_per_km) or self.conductor_x_ohm_per_km < 0:
            raise ValueError("Residential conductor reactance must be finite and nonnegative.")
        fractions = (self.l1_load_fraction, self.l2_load_fraction)
        if any(not math.isfinite(f) or f < 0 for f in fractions) or sum(fractions) > 1:
            raise ValueError("Residential 120 V load fractions must be nonnegative and sum to at most one.")

    @property
    def load_elements(self):
        return ("BuildingL1", "BuildingL2", "Building240")

    @property
    def storage_connection(self):
        return "bus1=load_bus.1.2 phases=1 conn=wye kv=0.24"

    @property
    def description(self):
        return (f"Representative 120/240 V split-phase service; {self.transformer_kva:g} kVA "
                f"center-tapped transformer; {self.service_amps:g} A three-wire service")

    def metadata(self):
        return dict(id="residential_split_phase_v1", **asdict(self),
                    primary_voltage_kv=12.47, secondary_voltage_v=[120, 240],
                    transformer_xhl_percent=2.04, transformer_xht_percent=2.04,
                    transformer_xlt_percent=1.36, transformer_winding_r_percent=[.6, 1.2, 1.2],
                    transformer_no_load_loss_percent=.2,
                    secondary_half_winding_limit_kva=self.transformer_kva / 2,
                    voltage_limits_pu=[.95, 1.05],
                    grounding="Center tap grounded at transformer; explicit service neutral; no earth-return path",
                    source=SOURCE, scope="Representative assumptions; no customer wiring, protection or thermal study")

    def pv_configuration(self, capacity, configuration, frame):
        """Keep production and equipment ratings; explicitly rewire at 240 V.

        Profile builders currently supply generic 480 V replay connections.
        This selected service model owns wiring, not the weather/PV model.
        Reject other/custom wiring instead of silently relocating it.
        """
        inverters = replay_inverters(capacity, configuration)
        if not inverters:
            return None
        rewired = []
        for item in inverters:
            wiring = (item.bus, item.phases, item.voltage_kv, item.connection)
            if wiring not in (("load_bus.1.2.3", 3, .48, "wye"),
                              ("load_bus.1.2", 1, .24, "wye")):
                raise ValueError("Residential replay requires generic site or explicit 240 V line-to-line inverter wiring.")
            rewired.append(replace(item, bus="load_bus.1.2", phases=1, voltage_kv=.24, connection="wye"))
        if configuration is None:
            import pandas as pd
            values = frame.get("pv_available_kw", frame.pv_kw).to_numpy()
            availability = pd.DataFrame({inverters[0].name: values}, index=pd.DatetimeIndex(frame.timestamp))
        else:
            availability = configuration.available_power_kw
        return PVReplayConfiguration(tuple(rewired), availability)

    def create_circuit(self):
        dss.Text.Command("Clear")
        dss.Text.Command("New Circuit.ResidentialService phases=3 bus1=pcc_bus basekv=12.47 pu=1")
        # EPRI line-to-line primary example. Reverse the second half-secondary
        # terminals to obtain opposite 120 V polarities, not a 120-degree wye.
        dss.Text.Command(
            "New Transformer.ServiceTransformer phases=1 windings=3 "
            "buses=[pcc_bus.1.2 service_bus.1.0 service_bus.0.2] "
            "conns=[delta wye wye] kVs=[12.47 .12 .12] "
            f"kVAs=[{self.transformer_kva} {self.transformer_kva} {self.transformer_kva}] "
            "%Rs=[.6 1.2 1.2] Xhl=2.04 Xht=2.04 Xlt=1.36 %noloadloss=.2 %imag=0"
        )
        r, x = self.conductor_r_ohm_per_km, self.conductor_x_ohm_per_km
        # Three explicit conductors: L1, L2, neutral. Here phases=3 sets the
        # matrix order; their actual voltage angles come from the transformer.
        # No Kron reduction, mutual coupling or capacitive shunt is assumed.
        dss.Text.Command(
            "New Line.Feeder phases=3 bus1=service_bus.1.2.0 bus2=load_bus.1.2.3 "
            f"length={self.service_length_km} units=km "
            f"rmatrix=[{r} | 0 {r} | 0 0 {r}] xmatrix=[{x} | 0 {x} | 0 0 {x}] "
            f"cmatrix=[0 | 0 0 | 0 0 0] normamps={self.service_amps} emergamps={self.service_amps}"
        )
        for name, bus, kv in (("BuildingL1", "1.3", .12), ("BuildingL2", "2.3", .12),
                              ("Building240", "1.2", .24)):
            dss.Text.Command(f"New Load.{name} phases=1 bus1=load_bus.{bus} conn=wye "
                             f"kv={kv} kw=0 kvar=0 model=1 vminpu=.9 vmaxpu=1.1")
        dss.Text.Command("Set VoltageBases=[12.47 .208]")
        dss.Text.Command("CalcVoltageBases")
        # DSS's LN kVBase is explicit; never treat neutral voltage as a phase.
        dss.Text.Command("SetkVBase bus=service_bus kVln=.12")
        dss.Text.Command("SetkVBase bus=load_bus kVln=.12")
        dss.Text.Command("Set Mode=Snapshot")
        dss.Solution.Solve()
        if not dss.Solution.Converged():
            raise RuntimeError("Residential no-load circuit did not converge.")

    def set_load(self, kw, kvar):
        fractions = (self.l1_load_fraction, self.l2_load_fraction,
                     1 - self.l1_load_fraction - self.l2_load_fraction)
        for name, fraction in zip(self.load_elements, fractions):
            dss.Text.Command(f"Edit Load.{name} kW={kw * fraction} kvar={kvar * fraction}")

    def measurements(self):
        dss.Circuit.SetActiveBus("load_bus")
        values = dss.Bus.Voltages()
        nodes = dict(zip(dss.Bus.Nodes(), [complex(*values[i:i+2]) for i in range(0, len(values), 2)]))
        l1, l2, neutral = (nodes[i] for i in (1, 2, 3))
        dss.Circuit.SetActiveElement("Line.Feeder")
        currents = dss.CktElement.CurrentsMagAng()[0:6:2]
        dss.Circuit.SetActiveElement("Transformer.ServiceTransformer")
        powers = dss.CktElement.Powers()
        n = 2 * dss.CktElement.NumConductors()
        winding_kva = [abs(complex(sum(powers[i:i+n:2]), sum(powers[i+1:i+n:2])))
                       for i in range(0, 3*n, n)]
        return dict(voltage_l1_neutral_v=abs(l1-neutral), voltage_l2_neutral_v=abs(l2-neutral),
                    voltage_l1_l2_v=abs(l1-l2), neutral_voltage_v=abs(neutral),
                    service_l1_current_a=currents[0], service_l2_current_a=currents[1],
                    service_neutral_current_a=currents[2],
                    transformer_primary_loading_percent=winding_kva[0]/self.transformer_kva*100,
                    transformer_l1_loading_percent=winding_kva[1]/(self.transformer_kva/2)*100,
                    transformer_l2_loading_percent=winding_kva[2]/(self.transformer_kva/2)*100)
