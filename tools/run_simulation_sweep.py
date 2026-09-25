"""Deterministic, offline simulation stress sweep across supported study paths.

Run from the repository root with ``/usr/local/bin/python3
tools/run_simulation_sweep.py --output /tmp/microgrid-sweep.json``. All inputs
are hypothetical. A passing case checks internal physics, billing, or a
documented rejection; it does not validate an estimate against a real bill.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.billing import (  # noqa: E402
    PGE_B10_SECONDARY_BUNDLED,
    PGE_B19_SECONDARY_OPTION_S_BUNDLED,
    PGE_B20_SECONDARY_BUNDLED,
    PGE_E1_RESIDENTIAL_TIER3_BUNDLED,
    PGE_E_TOU_D_RESIDENTIAL_TIER3_BUNDLED,
    PGE_E_ELEC_RESIDENTIAL_TIER3_BUNDLED,
    PGE_EV2_RESIDENTIAL_TIER3_BUNDLED,
    calculate_meter_billing,
)
from src.billing.municipal import bill_cycle  # noqa: E402
from src.billing.socal import bill as socal_bill  # noqa: E402
from src.billing.socal import RESIDENTIAL_PLANS  # noqa: E402
from src.dispatch.municipal import optimize_storage  # noqa: E402
from src.dispatch.single_day_analysis import run_cost_optimization  # noqa: E402
from src.dispatch.socal import optimize as socal_optimize  # noqa: E402
from src.dispatch.solar_export import benefit_breakdown, compare  # noqa: E402

PACIFIC = "America/Los_Angeles"
TOLERANCE_DOLLARS = 0.02


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def close(actual: float, expected: float, *, atol: float = 1e-5) -> bool:
    return math.isclose(float(actual), float(expected), abs_tol=atol, rel_tol=0)


def record(cases: list[dict], group: str, case_id: str, inputs: dict, run) -> None:
    try:
        metrics = run()
        require(all(np.isfinite(value) for value in metrics.values()), "nonfinite result")
        cases.append({"id": case_id, "group": group, "inputs": inputs,
                      "status": "passed", "metrics": metrics})
    except Exception as exc:
        cases.append({"id": case_id, "group": group, "inputs": inputs,
                      "status": "failed", "error": f"{type(exc).__name__}: {exc}"})


def commercial_cases(cases: list[dict]) -> None:
    plans = (
        ("pge_b10", PGE_B10_SECONDARY_BUNDLED, 120., 20., 10.),
        ("pge_b19_option_s", PGE_B19_SECONDARY_OPTION_S_BUNDLED, 600., 50., 25.),
        ("pge_b20", PGE_B20_SECONDARY_BUNDLED, 1200., 100., 50.),
    )
    for name, tariff, base_kw, capacity_kwh, power_kw in plans:
        for season, start in (("summer", "2026-07-15"), ("winter", "2026-11-15")):
            timestamps = pd.date_range(start, periods=192, freq="15min", tz=PACIFIC)
            hour = np.asarray(timestamps.hour) + np.asarray(timestamps.minute) / 60
            for shape in ("flat", "evening", "midday"):
                bump = {
                    "flat": np.zeros(len(hour)),
                    "evening": np.where((hour >= 16) & (hour < 21), .30, 0.),
                    "midday": np.where((hour >= 9) & (hour < 14), .30, 0.),
                }[shape]
                load = base_kw * (1 + bump)
                for pv_on in (False, True):
                    pv = (base_kw * .2 * np.maximum(
                        0., np.sin(np.pi * (hour - 6) / 12)
                    ) if pv_on else np.zeros(len(hour)))
                    inputs = {"plan": name, "season": season, "load_shape": shape,
                              "pv": pv_on, "battery_kwh": capacity_kwh,
                              "battery_kw": power_kw, "intervals": len(timestamps)}

                    def run(tariff=tariff, load=load, pv=pv, timestamps=timestamps,
                            capacity_kwh=capacity_kwh, power_kw=power_kw):
                        data = pd.DataFrame({
                            "timestamp": timestamps, "load_kw": load, "pv_kw": pv,
                            "price_per_kWh": tariff.energy_rates(timestamps).to_numpy(),
                        })
                        battery = dict(
                            initial_soc_kWh=capacity_kwh * .5,
                            min_soc_kWh=capacity_kwh * .1,
                            max_soc_kWh=capacity_kwh * .9,
                            max_charge_kw=power_kw, max_discharge_kw=power_kw,
                            charge_efficiency=.95, discharge_efficiency=.95,
                        )
                        optimized = run_cost_optimization(
                            data.copy(), battery, demand_tariff=tariff
                        )
                        baseline = pd.DataFrame({
                            "timestamp": timestamps, "grid_import_kw": load - pv,
                        })
                        before = sum(period.total_utility_charge for period in
                                     calculate_meter_billing(
                                         baseline, tariff, meter_id="pcc",
                                         timestep_hours=.25, expect_full_periods=False,
                                     ))
                        after = sum(period.total_utility_charge for period in
                                    calculate_meter_billing(
                                        optimized, tariff, meter_id="pcc",
                                        timestep_hours=.25, expect_full_periods=False,
                                    ))
                        balance = float(np.max(np.abs(
                            optimized.pv_kw + optimized.battery_discharge_kw
                            + optimized.grid_import_kw - optimized.load_kw
                            - optimized.battery_charge_kw - optimized.grid_export_kw
                        )))
                        require(balance < 1e-4, "PCC power balance failed")
                        require(after <= before + TOLERANCE_DOLLARS,
                                "bill-only dispatch increased the modeled bill")
                        require(close(optimized.battery_soc_kWh.iloc[-1],
                                      battery["initial_soc_kWh"], atol=1e-4),
                                "terminal SOC differs from initial SOC")
                        soc_end = optimized.battery_soc_kWh.to_numpy()
                        soc_start = np.r_[battery["initial_soc_kWh"], soc_end[:-1]]
                        soc_residual = float(np.max(np.abs(
                            soc_end - soc_start - .25 * (
                                .95 * optimized.battery_charge_kw.to_numpy()
                                - optimized.battery_discharge_kw.to_numpy() / .95
                            )
                        )))
                        require(soc_residual < 1e-4,
                                "battery energy transition failed")
                        require(soc_end.min() >= battery["min_soc_kWh"] - 1e-4
                                and soc_end.max() <= battery["max_soc_kWh"] + 1e-4,
                                "battery SOC exceeded its bounds")
                        return {"idle_bill": round(before, 4),
                                "optimized_bill": round(after, 4),
                                "balance_error_kw": round(balance, 8),
                                "soc_error_kwh": round(soc_residual, 8)}

                    record(cases, "commercial", f"{name}-{season}-{shape}-pv{int(pv_on)}",
                           inputs, run)


def nbt_account() -> dict:
    return dict(
        utility="pge", generation_provider="pge", customer_class="residential",
        billing_plan="E-ELEC", program="NBT", income_tier=3,
        enrollment_confirmed=True, ordinary_account_confirmed=True,
        cycle_confirmed=True, no_local_tax_confirmed=True,
        no_other_adjustments_confirmed=True,
        reference="Hypothetical offline sweep", application_year=2026,
        pto_date="2026-04-01", bonus_eligible_confirmed=True,
        cycle_start="2026-07-01", cycle_end="2026-07-31",
        next_true_up_date="2027-04-01", storage="renewable_only",
    )


def nbt_frame(load_kw: float, pv_peak_kw: float) -> pd.DataFrame:
    timestamps = pd.date_range(
        "2026-07-01", "2026-08-01", freq="15min", inclusive="left", tz=PACIFIC
    )
    hour = np.asarray(timestamps.hour) + np.asarray(timestamps.minute) / 60
    return pd.DataFrame({
        "timestamp": timestamps,
        "native_load_kw": np.full(len(timestamps), load_kw),
        "pv_available_kw": pv_peak_kw * np.maximum(
            0., np.sin(np.pi * (hour - 6) / 12)
        ),
    })


def pge_residential_cases(cases: list[dict]) -> None:
    """Exercise ordinary bundled import bills independently of NBT settlement."""
    timestamps = pd.date_range(
        "2026-07-01", "2026-08-01", freq="15min", inclusive="left", tz=PACIFIC
    )
    hour = np.asarray(timestamps.hour) + np.asarray(timestamps.minute) / 60
    plans = (
        ("e1", PGE_E1_RESIDENTIAL_TIER3_BUNDLED),
        ("e_tou_d", PGE_E_TOU_D_RESIDENTIAL_TIER3_BUNDLED),
        ("e_elec", PGE_E_ELEC_RESIDENTIAL_TIER3_BUNDLED),
        ("ev2", PGE_EV2_RESIDENTIAL_TIER3_BUNDLED),
    )
    for name, tariff in plans:
        for shape in ("flat", "midday", "evening"):
            bump = {
                "flat": np.zeros(len(hour)),
                "midday": np.where((hour >= 10) & (hour < 15), .5, 0.),
                "evening": np.where((hour >= 17) & (hour < 22), .5, 0.),
            }[shape]
            inputs = {"plan": name, "income_tier": 3, "baseline_territory": "T",
                      "cycle": "2026-07", "shape": shape,
                      "load_levels_kw": [.5, 1.5], "pv": False}

            def run(tariff=tariff, bump=bump):
                bills = []
                for base_kw in (.5, 1.5):
                    frame = pd.DataFrame({
                        "timestamp": timestamps,
                        "grid_import_kw": base_kw * (1 + bump),
                    })
                    periods = calculate_meter_billing(
                        frame, tariff, meter_id="pcc", timestep_hours=.25
                    )
                    require(len(periods) == 1 and not periods[0].is_partial_period,
                            "expected one complete July billing period")
                    bill = periods[0]
                    require(bill.export_credit == 0 and bill.demand_charge == 0,
                            "import-only residential bill has export or demand charge")
                    require(close(bill.import_energy_kWh,
                                  float(frame.grid_import_kw.sum()) * .25),
                            "billed import energy differs from interval energy")
                    require(close(bill.total_utility_charge,
                                  bill.customer_charge + bill.import_energy_charge),
                            "residential bill components do not reconcile")
                    bills.append(bill.total_utility_charge)
                require(bills[1] > bills[0],
                        "higher residential load did not increase the bill")
                return {"low_load_bill": round(bills[0], 4),
                        "high_load_bill": round(bills[1], 4)}

            record(cases, "pge_residential", f"pge-{name}-{shape}", inputs, run)


def residential_nbt_cases(cases: list[dict]) -> None:
    account = nbt_account()
    for load_kw in (.5, 1., 2.):
        for pv_peak_kw in (1., 3.):
            inputs = {"load_kw": load_kw, "pv_peak_kw": pv_peak_kw,
                      "cycle": "2026-07", "battery": False}

            def run(load_kw=load_kw, pv_peak_kw=pv_peak_kw):
                results = compare(nbt_frame(load_kw, pv_peak_kw), account,
                                  export_limit_kw=3.)
                amounts = [results[key]["bill"]["amount_due"] for key in
                           ("grid_only", "pv_self_consumption", "pv_with_export")]
                require(amounts[1] <= amounts[0] + TOLERANCE_DOLLARS,
                        "on-site PV increased the bill")
                require(amounts[2] <= amounts[1] + TOLERANCE_DOLLARS,
                        "surplus export increased the bill")
                _, bridges, _ = benefit_breakdown(results)
                for bridge in bridges:
                    require(close(bridge["current_bill_savings"],
                                  bridge["avoided_import_charges"]
                                  + bridge["change_in_credits_used"]),
                            "solar savings bridge failed")
                return {"grid_bill": round(amounts[0], 4),
                        "on_site_bill": round(amounts[1], 4),
                        "export_bill": round(amounts[2], 4)}

            record(cases, "residential_nbt",
                   f"nbt-load{load_kw:g}-pv{pv_peak_kw:g}", inputs, run)

    battery = dict(capacity_kWh=4., energy_kWh=.8, SOC_min=.2, SOC_max=.8,
                   max_charge_kw=2., max_discharge_kw=2.,
                   charge_efficiency=.95, discharge_efficiency=.95)
    for wear in (.01, .25):
        for aware in (False, True):
            inputs = {"load_kw": 1., "pv_peak_kw": 3.,
                      "battery_kwh": 4., "wear_per_kwh": wear,
                      "optimize_wear": aware, "cycle": "2026-07"}

            def run(wear=wear, aware=aware):
                results = compare(nbt_frame(1., 3.), account,
                                  export_limit_kw=3., battery=battery,
                                  wear_per_kwh=wear,
                                  include_degradation_in_optimization=aware)
                storage = results["storage_with_export"]
                require(storage["objective_gap"] < TOLERANCE_DOLLARS,
                        "storage bill and objective disagree")
                require(close(storage["operating_cost"],
                              storage["bill"]["amount_due"]
                              + storage["degradation_cost"]),
                        "storage operating-cost bridge failed")
                return {"bill": round(storage["bill"]["amount_due"], 4),
                        "wear": round(storage["degradation_cost"], 4),
                        "operating_cost": round(storage["operating_cost"], 4),
                        "objective_gap": round(storage["objective_gap"], 8)}

            record(cases, "residential_nbt", f"nbt-storage-wear{wear:g}-{aware}",
                   inputs, run)

    for capacity_kwh, power_kw in ((.5, .25), (40., 10.)):
        inputs = {"load_kw": .2, "pv_peak_kw": 10.,
                  "battery_kwh": capacity_kwh, "battery_kw": power_kw,
                  "export_limit_kw": 3., "cycle": "2026-07"}

        def storage_extreme(capacity_kwh=capacity_kwh, power_kw=power_kw):
            battery = dict(capacity_kWh=capacity_kwh,
                           energy_kWh=capacity_kwh * .1,
                           SOC_min=.1, SOC_max=.9,
                           max_charge_kw=power_kw,
                           max_discharge_kw=power_kw,
                           charge_efficiency=.95, discharge_efficiency=.95)
            results = compare(nbt_frame(.2, 10.), account,
                              export_limit_kw=3., battery=battery,
                              wear_per_kwh=0.,
                              include_degradation_in_optimization=False)
            storage = results["storage_with_export"]
            require(storage["objective_gap"] < TOLERANCE_DOLLARS,
                    "extreme storage bill and objective disagree")
            require(storage["bill"]["amount_due"] >= 0,
                    "extreme storage produced a negative amount due")
            require(storage["bill"]["amount_due"] <=
                    results["pv_with_export"]["bill"]["amount_due"]
                    + TOLERANCE_DOLLARS,
                    "bill-only storage increased the current bill")
            return {"bill": round(storage["bill"]["amount_due"], 4),
                    "objective_gap": round(storage["objective_gap"], 8)}

        record(cases, "residential_nbt", f"nbt-storage-{capacity_kwh:g}kwh-high-pv",
               inputs, storage_extreme)

    def high_pv():
        results = compare(nbt_frame(.2, 10.), account, export_limit_kw=3.)
        bill = results["pv_with_export"]["bill"]
        closing = sum(bill["closing_balance"].values())
        require(bill["amount_due"] >= 0, "credit bank treated as cash payout")
        require(closing > 0, "high-export case did not carry a credit bank")
        return {"amount_due": round(bill["amount_due"], 4),
                "closing_credit": round(closing, 4)}

    record(cases, "residential_nbt", "nbt-high-pv-credit-bank",
           {"load_kw": .2, "pv_peak_kw": 10., "export_limit_kw": 3.}, high_pv)


def socal_account(utility: str) -> dict:
    return dict(
        customer_class="residential", eligibility_confirmed=True,
        cycle_confirmed=True, ordinary_account_confirmed=True,
        reference="Hypothetical offline sweep", generation_provider=utility,
        solar_program="approved_non_export", interconnection_confirmed=True,
        voltage="secondary", phase="single", local_tax_percent=0.,
        tax_confirmed=True, temperature_zone="1", region_confirmed=True,
        pac_tier=1, annual_average_kwh=500, baseline_region="6",
        baseline_type="basic", prime_qualification="battery",
        billing_month_factor=2/30,
    )


def socal_cases(cases: list[dict]) -> None:
    timestamps = pd.date_range(
        "2026-07-06", "2026-07-08", freq="15min", inclusive="left", tz=PACIFIC
    )
    hour = np.asarray(timestamps.hour) + np.asarray(timestamps.minute) / 60
    battery = dict(capacity_kWh=10., energy_kWh=5., SOC_min=.2, SOC_max=.8,
                   max_charge_kw=3., max_discharge_kw=3.,
                   charge_efficiency=.95, discharge_efficiency=.95)
    for utility, plan in (
        ("ladwp", "ladwp_r-1a"), ("ladwp", "ladwp_r-1b"),
        ("sce", "sce_d"), ("sce", "sce_tou-d-4-9"),
        ("sce", "sce_tou-d-5-8"), ("sce", "sce_tou-d-prime"),
    ):
        for load_kw in (1., 2.):
            for pv_peak_kw in (0., 3.):
                inputs = {"plan": plan, "load_kw": load_kw,
                          "pv_peak_kw": pv_peak_kw, "service_days": 2}

                def run(utility=utility, plan=plan, load_kw=load_kw,
                        pv_peak_kw=pv_peak_kw):
                    pv = pv_peak_kw * np.maximum(
                        0., np.sin(np.pi * (hour - 6) / 12)
                    )
                    frame = pd.DataFrame({
                        "timestamp": timestamps,
                        "native_load_kw": np.full(len(timestamps), load_kw),
                        "grid_import_kw": np.full(len(timestamps), load_kw),
                        "pv_available_kw": pv,
                    })
                    result = socal_optimize(
                        plan, frame, socal_account(utility), "2026-07-06",
                        "2026-07-07", battery, .01,
                    )
                    dispatch = result["dispatch"]
                    balance = float(np.max(np.abs(
                        dispatch.grid_import_kw + dispatch.pv_output_kw
                        + dispatch.battery_discharge_kw - dispatch.native_load_kw
                        - dispatch.battery_charge_kw
                    )))
                    require(balance < 1e-4, "SoCal power balance failed")
                    require(result["objective_gap"] < TOLERANCE_DOLLARS,
                            "SoCal bill and objective disagree")
                    require(result["bill"]["total"] <=
                            result["solar_bill"]["total"] + TOLERANCE_DOLLARS,
                            "bill-only storage increased the SoCal bill")
                    return {"solar_bill": round(result["solar_bill"]["total"], 4),
                            "optimized_bill": round(result["bill"]["total"], 4),
                            "balance_error_kw": round(balance, 8),
                            "objective_gap": round(result["objective_gap"], 8)}

                record(cases, "socal", f"{plan}-load{load_kw:g}-pv{pv_peak_kw:g}",
                       inputs, run)


def municipal_account(schedule: str) -> dict:
    account = dict(
        customer_class="residential" if schedule == "D-1" else "commercial",
        phase="single", voltage="secondary", metered=True,
        onsite_generation=False, special_riders=[], billing_cycle_confirmed=True,
        state_surcharge_exempt=False, confirmed_schedule=schedule,
        schedule_confirmation_reference="Hypothetical offline sweep",
        uut_status="standard", heating_source="gas_or_other",
        demand_interval_minutes=15, minimum_charge_load_units=0,
        power_factor_adjustment_active=False,
        power_factor_state_reference="Hypothetical inactive adjustment",
    )
    if schedule == "CB-1":
        start = pd.Timestamp("2026-08-01")
        account["previous_11_month_peaks_kw"] = {
            (start - pd.DateOffset(months=month)).strftime("%Y-%m"): 100.
            for month in range(1, 12)
        }
    return account


def municipal_cases(cases: list[dict]) -> None:
    timestamps = pd.date_range(
        "2026-08-01", "2026-09-01", freq="15min", inclusive="left", tz=PACIFIC
    )
    hour = np.asarray(timestamps.hour) + np.asarray(timestamps.minute) / 60
    cycle_start, cycle_end = timestamps[0], pd.Timestamp("2026-09-01", tz=PACIFIC)
    for tariff, schedule, base_kw in (
        ("amp_d1_2026_07_01", "D-1", .5),
        ("amp_a2_2026_07_01", "A-2", 20.),
        ("svp_d1_2026_01_01", "D-1", 2.),
        ("svp_cb1_2026_01_01", "CB-1", 20.),
    ):
        load = base_kw * (1 + .5 * ((hour >= 17) & (hour < 19)))
        data = pd.DataFrame({"timestamp": timestamps, "grid_import_kw": load})
        account = municipal_account(schedule)

        def bill_run(tariff=tariff, data=data, account=account):
            result = bill_cycle(tariff, data, cycle_start=cycle_start,
                                cycle_end=cycle_end, account=account)
            require(close(result["total"], sum(result["line_items"].values())),
                    "municipal bill line items do not reconcile")
            return {"bill": round(result["total"], 4),
                    "import_kwh": round(result["import_kwh"], 4)}

        record(cases, "municipal", f"{tariff}-bill",
               {"tariff": tariff, "base_kw": base_kw, "cycle": "2026-08"}, bill_run)
        if schedule not in ("A-2", "CB-1"):
            continue

        def storage_run(tariff=tariff, data=data, account=account):
            battery = dict(capacity_kWh=200., energy_kWh=100.,
                           max_charge_kw=40., max_discharge_kw=40.,
                           SOC_min=.1, SOC_max=.9,
                           charge_efficiency=.95, discharge_efficiency=.95)
            result = optimize_storage(
                tariff, data, cycle_start=cycle_start, cycle_end=cycle_end,
                account=account, battery=battery,
            )
            dispatch = result["dispatch"]
            balance = float(np.max(np.abs(
                dispatch.grid_import_kw - data.grid_import_kw
                - dispatch.charge_kw + dispatch.discharge_kw
            )))
            require(balance < 1e-4, "municipal power balance failed")
            require(result["optimality_gap_bound_dollars"] < TOLERANCE_DOLLARS,
                    "municipal optimality gap exceeds tolerance")
            require(close(result["bill"]["total"],
                          sum(result["bill"]["line_items"].values())),
                    "optimized municipal bill does not reconcile")
            require(result["bill"]["total"] <=
                    result["baseline_bill"]["total"] + TOLERANCE_DOLLARS,
                    "bill-only storage increased the municipal bill")
            return {"baseline_bill": round(result["baseline_bill"]["total"], 4),
                    "optimized_bill": round(result["bill"]["total"], 4),
                    "balance_error_kw": round(balance, 8)}

        record(cases, "municipal", f"{tariff}-storage",
               {"tariff": tariff, "base_kw": base_kw,
                "battery_kwh": 200., "cycle": "2026-08"}, storage_run)


def boundary_cases(cases: list[dict]) -> None:
    tariff = PGE_B19_SECONDARY_OPTION_S_BUNDLED
    for start, end, expected_intervals in (
        ("2026-03-08", "2026-03-09", 92),
        ("2026-11-01", "2026-11-02", 100),
    ):
        timestamps = pd.date_range(start, end, freq="15min",
                                    inclusive="left", tz=PACIFIC)

        def run(timestamps=timestamps, expected_intervals=expected_intervals):
            require(len(timestamps) == expected_intervals,
                    "DST interval count is incorrect")
            data = pd.DataFrame({"timestamp": timestamps,
                                 "grid_import_kw": np.full(len(timestamps), 600.)})
            (bill,) = calculate_meter_billing(
                data, tariff, meter_id="pcc", timestep_hours=.25,
                expect_full_periods=False,
            )
            require(bill.demand_charge > 0, "DST demand bill missing")
            return {"intervals": len(timestamps),
                    "demand_charge": round(bill.demand_charge, 4)}

        record(cases, "boundaries", f"pge-option-s-dst-{start}",
               {"start": start, "expected_intervals": expected_intervals}, run)

    def sce_transition():
        timestamps = pd.date_range(
            "2025-11-01", "2025-12-01", freq="15min",
            inclusive="left", tz=PACIFIC,
        )
        data = pd.DataFrame({"timestamp": timestamps,
                             "grid_import_kw": np.ones(len(timestamps)),
                             "native_load_kw": np.ones(len(timestamps)),
                             "pv_available_kw": np.zeros(len(timestamps))})
        account = socal_account("sce")
        account.update(solar_program="none", billing_month_factor=1.)
        result = socal_bill("sce_d", data, account,
                            "2025-11-01", "2025-11-30")
        days = [version["service_days"] for version in result["rate_versions"]]
        require(days == [14, 16], "SCE November BSC transition misallocated")
        return {"intervals": len(timestamps), "bill": round(result["total"], 4),
                "pre_bsc_days": days[0], "bsc_days": days[1]}

    record(cases, "boundaries", "sce-2025-november-bsc",
           {"plan": "sce_d", "cycle": "2025-11"}, sce_transition)

    def rejected(run, expected_message: str):
        try:
            run()
        except ValueError as exc:
            require(expected_message.lower() in str(exc).lower(),
                    f"wrong rejection reason: {exc}")
            return {"rejected": 1}
        raise AssertionError("unsupported tariff date was accepted")

    def old_pge():
        timestamp = pd.Timestamp("2026-02-28 17:00", tz=PACIFIC)
        data = pd.DataFrame({"timestamp": [timestamp], "grid_import_kw": [600.]})
        return rejected(lambda: calculate_meter_billing(
            data, tariff, meter_id="pcc", timestep_hours=.25,
            expect_full_periods=False,
        ), "not effective")

    record(cases, "boundaries", "pge-option-s-before-effective",
           {"date": "2026-02-28", "expected": "rejection"}, old_pge)

    def old_sce():
        timestamps = pd.date_range("2024-05-01", "2024-06-01",
                                    freq="15min", inclusive="left", tz=PACIFIC)
        data = pd.DataFrame({"timestamp": timestamps,
                             "grid_import_kw": np.ones(len(timestamps)),
                             "native_load_kw": np.ones(len(timestamps)),
                             "pv_available_kw": np.zeros(len(timestamps))})
        account = socal_account("sce")
        account.update(solar_program="none", billing_month_factor=1.)
        return rejected(lambda: socal_bill(
            "sce_d", data, account, "2024-05-01", "2024-05-31"
        ), "coverage")

    record(cases, "boundaries", "sce-before-verified-coverage",
           {"date": "2024-05", "expected": "rejection"}, old_sce)

    def sce_version_boundary():
        before = RESIDENTIAL_PLANS["sce_d"].version_on(
            pd.Timestamp("2025-11-14").date()
        )
        after = RESIDENTIAL_PLANS["sce_d"].version_on(
            pd.Timestamp("2025-11-15").date()
        )
        require(before.tariff_id != after.tariff_id,
                "SCE boundary failed to switch versions")
        return {"switched_versions": 1}

    record(cases, "boundaries", "sce-2025-bsc-version-switch",
           {"before": "2025-11-14", "after": "2025-11-15"},
           sce_version_boundary)


GROUPS = {
    "commercial": commercial_cases,
    "pge_residential": pge_residential_cases,
    "residential_nbt": residential_nbt_cases,
    "socal": socal_cases,
    "municipal": municipal_cases,
    "boundaries": boundary_cases,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groups", nargs="+", choices=tuple(GROUPS),
                        default=tuple(GROUPS), help="Sweep groups to run")
    parser.add_argument("--output", type=Path,
                        help="Optional JSON report path; stdout always shows a summary")
    args = parser.parse_args(argv)
    cases: list[dict] = []
    for name in dict.fromkeys(args.groups):
        GROUPS[name](cases)
    counts = Counter(case["group"] for case in cases)
    failures = [case for case in cases if case["status"] == "failed"]
    report = {
        "schema_version": 1,
        "scope": "Hypothetical offline consistency checks; not bill calibration or field validation",
        "groups": dict(counts),
        "cases": len(cases),
        "passed": len(cases) - len(failures),
        "failed": len(failures),
        "results": cases,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{report['passed']}/{report['cases']} passed; {report['failed']} failed")
    print("groups:", ", ".join(f"{key}={value}" for key, value in counts.items()))
    for case in failures:
        print(f"FAIL {case['id']}: {case['error']}", file=sys.stderr)
    if args.output:
        print(f"report: {args.output}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
