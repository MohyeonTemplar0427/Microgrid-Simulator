"""Physical terminal checks for timestamped AC inverter replay."""
import numpy as np
import pandas as pd
import pytest
import opendssdirect as dss

from src.dispatch.battery import Battery
from src.opendss.ac_replay import PVInverterReplay, PVReplayConfiguration
from src.opendss.opendss_analysis import replay_dispatch_timeseries


def battery():
    return Battery(capacity_kWh=20, SOC_min=0.1, SOC_max=0.9,
                   energy_kWh=10, max_charge_kw=5, max_discharge_kw=5)


def schedule():
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-06-01 12:00", periods=4, freq="15min", tz="America/Los_Angeles"),
        "load_kw": [8., 3., 12., 4.], "pv_kw": [0., 8., 5., 0.],
        "battery_net_injection_kw": [0., -2., 2., 0.],
        "battery_soc_kWh": [10., 10., 10., 10.],
        "grid_net_import_kw": [8., -3., 5., 4.],
        "load_kvar": [2., 0., 3., -1.],
    })


def configuration(frame):
    return PVReplayConfiguration(
        (PVInverterReplay("East", 6., 7.), PVInverterReplay("West", 4., 5.)),
        pd.DataFrame({"East": [0., 6., 3., 0.], "West": [0., 4., 2., 0.]},
                     index=pd.DatetimeIndex(frame.timestamp)),
    )


def test_individual_ac_outputs_follow_availability_and_curtailment():
    frame = schedule()
    frame["pv_East_requested_kvar"] = [0., 1., -1., 0.]
    replay = replay_dispatch_timeseries(frame, battery=battery(), pv_capacity_kw=15.,
                                        pv_replay=configuration(frame))
    assert set(dss.Generators.AllNames()) == {"east", "west"}
    assert replay.pv_East_requested_kw.tolist() == pytest.approx([0., 4.8, 3., 0.])
    assert replay.pv_West_requested_kw.tolist() == pytest.approx([0., 3.2, 2., 0.])
    assert replay.pv_actual_kw.tolist() == pytest.approx(frame.pv_kw, abs=0.01)
    assert replay.load_actual_kw.tolist() == pytest.approx(frame.load_kw, abs=0.01)
    assert replay.load_actual_kvar.tolist() == pytest.approx(frame.load_kvar, abs=0.01)
    assert replay.pv_East_actual_kvar.tolist() == pytest.approx([0., 1., -1., 0.], abs=0.01)
    assert replay.pcc_balance_error_kw.abs().max() < 0.01
    assert replay.feasible.all()
    assert replay.network_real_loss_kw.gt(0).all()


def test_night_generation_is_rejected_by_weather_availability():
    frame = schedule()
    frame.loc[0, "pv_kw"] = 1.
    with pytest.raises(ValueError, match="available power"):
        replay_dispatch_timeseries(frame, battery=battery(), pv_capacity_kw=15.,
                                   pv_replay=configuration(frame))


def test_inverter_kva_limit_is_checked_before_solving():
    frame = schedule()
    frame["pv_East_requested_kvar"] = 8.
    with pytest.raises(ValueError, match="kVA capability"):
        replay_dispatch_timeseries(frame, battery=battery(), pv_capacity_kw=15.,
                                   pv_replay=configuration(frame))


def test_missing_timestamp_cannot_be_filled_by_position():
    frame = schedule()
    config = configuration(frame)
    config.available_power_kw.index += pd.Timedelta(minutes=15)
    with pytest.raises(ValueError, match="Missing inverter availability"):
        replay_dispatch_timeseries(frame, battery=battery(), pv_capacity_kw=15., pv_replay=config)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.])
def test_invalid_inverter_availability_is_rejected(bad):
    frame = schedule()
    values = configuration(frame).available_power_kw
    values.iloc[0, 0] = bad
    with pytest.raises(ValueError, match="Invalid AC availability"):
        PVReplayConfiguration(configuration(frame).inverters, values)


def test_dst_repeated_hour_keeps_distinct_inverter_values():
    # 2 a.m. PDT falls back to 1 a.m. PST, so 01:15 and 01:30 each occur twice
    # on this date at two different instants. A lookup matching on wall-clock
    # time instead of the instant would read the first fold's row for both.
    #
    # The aggregate alone cannot detect that: setpoints are scaled to the
    # requested total, so pv_actual_kw equals pv_kw whichever row is read.
    # What does detect it is the split between inverters, so the two folds
    # put their generation on *different* inverters.
    timestamps = pd.date_range(
        "2024-11-03 01:15-07:00", periods=6, freq="15min"
    ).tz_convert("America/Los_Angeles")

    wall_clock = [stamp.strftime("%H:%M") for stamp in timestamps]
    assert wall_clock.count("01:15") == 2 and wall_clock.count("01:30") == 2

    frame = pd.DataFrame({
        "timestamp": timestamps,
        "load_kw": [4.] * 6,
        "pv_kw": [3., 3., 0., 0., 2., 2.],
        "battery_net_injection_kw": [0.] * 6,
        "battery_soc_kWh": [10.] * 6,
        "grid_net_import_kw": [1., 1., 4., 4., 2., 2.],
        "load_kvar": [1.] * 6,
    })
    replay_configuration = PVReplayConfiguration(
        (PVInverterReplay("East", 6., 7.), PVInverterReplay("West", 4., 5.)),
        pd.DataFrame(
            # First fold generates on East only, second on West only.
            {"East": [6., 6., 0., 0., 0., 0.],
             "West": [0., 0., 0., 0., 4., 4.]},
            index=pd.DatetimeIndex(timestamps),
        ),
    )

    replay = replay_dispatch_timeseries(
        frame, battery=battery(), pv_capacity_kw=10.,
        pv_replay=replay_configuration,
    )

    assert replay.pv_actual_kw.tolist() == pytest.approx(frame.pv_kw, abs=0.01)

    # 01:15 in the first fold: all on East.
    assert replay.loc[0, "pv_East_actual_kw"] == pytest.approx(3., abs=0.01)
    assert replay.loc[0, "pv_West_actual_kw"] == pytest.approx(0., abs=0.01)
    # 01:15 again, after the clocks went back: all on West. Reading the first
    # fold's availability here would put the power on East instead.
    assert replay.loc[4, "pv_East_actual_kw"] == pytest.approx(0., abs=0.01)
    assert replay.loc[4, "pv_West_actual_kw"] == pytest.approx(2., abs=0.01)
    assert replay.feasible.all()


def test_converged_powerflow_with_wrong_pv_output_is_not_feasible(monkeypatch):
    from src.opendss import opendss_analysis
    original = opendss_analysis.apply_dispatch_operating_point
    def altered_output(row, **kwargs):
        original(row, **kwargs)
        dss.Text.Command("Edit Generator.East kW=0 kvar=0")
        dss.Solution.Solve()
    monkeypatch.setattr(opendss_analysis, "apply_dispatch_operating_point", altered_output)
    frame = schedule()
    replay = replay_dispatch_timeseries(frame, battery=battery(), pv_capacity_kw=15.,
                                        pv_replay=configuration(frame))
    assert replay.converged.all()
    assert bool(replay.loc[1, "setpoint_mismatch"])
    assert not bool(replay.loc[1, "feasible"])


def test_zero_pv_site_replays_without_a_generator():
    frame = schedule()
    frame["pv_kw"] = 0.
    frame["grid_net_import_kw"] = frame.load_kw - frame.battery_net_injection_kw
    replay = replay_dispatch_timeseries(frame, battery=battery(), pv_capacity_kw=0.)
    assert not dss.Generators.AllNames()
    assert replay.pv_actual_kw.eq(0).all()
    assert replay.feasible.all()
