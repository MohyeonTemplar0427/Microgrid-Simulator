"""Integer fixed-orientation search over one complete historical weather year."""
import hashlib
import json
from pathlib import Path


def energies(weather, grid, config, angles):
    """Batch the same pvlib chain as profiles.pv_model; no battery/AC solves."""
    import numpy as np
    from pvlib import irradiance, temperature, pvsystem, inverter
    from ..profiles.pv_model import solar_position_at, interval_midpoints, CELL_TEMPERATURE_PARAMETERS, TRANSPOSITION_MODEL
    position=solar_position_at(grid,latitude=config.latitude,longitude=config.longitude)
    extra=irradiance.get_extra_radiation(interval_midpoints(grid)).to_numpy()
    def evaluate(batch):
        tilt=np.array([a[0] for a in batch])[:,None]
        azimuth=np.array([a[1] for a in batch])[:,None]
        poa=irradiance.get_total_irradiance(tilt,azimuth,position.apparent_zenith.to_numpy(),position.azimuth.to_numpy(),
            weather.dni_w_per_m2.to_numpy(),weather.ghi_w_per_m2.to_numpy(),weather.dhi_w_per_m2.to_numpy(),
            dni_extra=extra,albedo=config.ground_albedo,model=TRANSPOSITION_MODEL)["poa_global"]
        poa=np.maximum(np.nan_to_num(poa,nan=0),0)
        cell=temperature.sapm_cell(poa,weather.temperature_c.to_numpy(),weather.wind_speed_m_per_s.to_numpy(),**CELL_TEMPERATURE_PARAMETERS)
        dc=pvsystem.pvwatts_dc(poa,cell,config.rated_pv_capacity_kw,config.power_temperature_coefficient_per_c)
        dc=np.maximum(np.nan_to_num(dc,nan=0),0)*(1-config.system_losses_fraction)
        ac=inverter.pvwatts(dc,config.resolved_inverter_ac_capacity_kw/config.nominal_inverter_efficiency,
                           eta_inv_nom=config.nominal_inverter_efficiency)
        return np.maximum(np.nan_to_num(ac,nan=0),0).sum(axis=1)*grid.timestep_minutes/60
    output=[]
    for first in range(0,len(angles),16):
        output.extend(evaluate(angles[first:first+16]).tolist())
    return output


def optimize(directory, study):
    from .contract import validate_request
    from ..profiles import WeatherDerivedPVConfiguration
    from ..profiles.weather import load_weather_csv, align_weather
    from ..timeseries import build_interval_index
    from ..profiles.pv_model import PV_MODEL_VERSION
    validate_request(study)
    directory=Path(directory)
    metadata=json.loads((directory/"weather.json").read_text())
    request=metadata["request"]
    for key in ("latitude","longitude"):
        if request[key]!=study["site"][key]: raise ValueError("Annual weather location differs from the study.")
    if request["timezone"]!=study["timezone"]: raise ValueError("Annual weather timezone differs from the study.")
    checksum=hashlib.sha256((directory/"weather.csv").read_bytes()).hexdigest()
    if checksum!=metadata["sha256"]: raise ValueError("Annual weather checksum changed.")
    if metadata["provenance"].get("source")!="nsrdb_psm4": raise ValueError("Optimization requires historical NSRDB weather, not clear-sky or proxy inputs.")
    year=request["year"]
    grid=build_interval_index(f"{year}-01-01",f"{year}-12-31",study["timezone"],request["timestep_minutes"])
    aligned=align_weather(load_weather_csv(directory/"weather.csv"),grid).frame
    solar=study["solar"]
    config=WeatherDerivedPVConfiguration(latitude=study["site"]["latitude"],longitude=study["site"]["longitude"],
        rated_pv_capacity_kw=solar["dc_capacity_kw"],inverter_ac_capacity_kw=study["pv_capacity_kw"],
        system_losses_fraction=solar["system_losses_fraction"],nominal_inverter_efficiency=solar["inverter_efficiency"])
    angles=[(tilt,azimuth) for tilt in range(91) for azimuth in range(360)]
    original=(solar["tilt_degrees"],solar["azimuth_degrees"])
    scores=energies(aligned,grid,config,angles+[original])
    best=max(range(len(angles)),key=lambda i:scores[i])
    return dict(tilt_degrees=angles[best][0],azimuth_degrees=angles[best][1],energy_kwh=scores[best],
        original_energy_kwh=scores[-1],year=year,interval_count=len(grid.index),weather_sha256=checksum,
        weather_provenance=metadata["provenance"],model_version=PV_MODEL_VERSION,
        evaluated_orientations=len(angles),scope="full_historical_calendar_year",
        inputs=dict(site=study["site"],timezone=study["timezone"],solar=solar,pv_capacity_kw=study["pv_capacity_kw"]),
        assumptions=["Highest modelled available AC energy for this historical year; not a multi-year yield guarantee.",
                     "All integer tilt 0–90 and azimuth 0–359 combinations evaluated. Exact ties choose lowest tilt then azimuth.",
                     "Generic fixed array; no roof feasibility, directional shading or battery/utility optimization."])
