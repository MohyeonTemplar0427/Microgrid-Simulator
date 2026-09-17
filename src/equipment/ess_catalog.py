"""Reviewed offline facts. Values are not fetched or refreshed during a study."""
REVISION = "2026-09-16.2"
RETRIEVED = "2026-09-16"
PW2 = "https://energylibrary.tesla.com/docs/Public/EnergyStorage/Powerwall/2/Datasheet/en-us/Powerwall-2-Datasheet.pdf"
AP2 = "https://www.franklinwh.com/document/apower-2-datasheet"
PW3 = "https://energylibrary.tesla.com/docs/Public/EnergyStorage/Powerwall/3/Datasheet/en-us/Powerwall-3-Datasheet.pdf"
MULTI = "https://energylibrary.tesla.com/docs/Public/EnergyStorage/Powerwall/2/InstallManual/BackupGateway/2/en-us/GUID-64A56007-BAD1-4482-90DE-C957756553CA.html"
CEC = "https://solarequipment.energy.ca.gov/Home/DownloadtoExcel?filename=EnergyStorage"


def fact(value, url, revision, section, status="published", note=""):
    return dict(value=value, status=status, source_url=url, document_revision=revision,
                section=section, retrieved_on=RETRIEVED, note=note)


def pw(value, section="p.1 performance; footnotes 1,3"):
    return fact(value, PW2, "NA-BACKUP-2024-07-02", section)


def ap(value, section="p.1 performance; footnotes 1,2"):
    return fact(value, AP2, "2025-12-16", section)


def pw3(value, section="p.2 system specifications; footnote 1"):
    return fact(value, PW3, "2025 edition", section)


CATALOG = [
    dict(id="tesla.powerwall2.1092170.na", catalog_revision=REVISION,
         manufacturer="Tesla", model="Powerwall 2 AC — 1092170-xx-y", region="North America, 120/240 V",
         market="residential", architecture=pw("ac_connected"),
         fields=dict(usable_energy_kwh=pw(13.5), total_energy_kwh=pw(14),
                     energy_basis=pw(None, "p.1: usable energy, measurement boundary not explicitly stated"),
                     charge_kw=pw(5), discharge_kw=pw(5), inverter_kva=pw(5.8),
                     round_trip_efficiency=pw(.90), efficiency_path=pw("ac_battery_ac"),
                     voltage_v=pw([120,240]), phase=pw("split_phase"), frequency_hz=pw(60),
                     max_units=fact(10,MULTI,"undated live manual; retrieved 2026-09-16","Service Type and Capacity Requirements"),
                     surge_kw=pw(7,"p.1: 10 seconds off-grid/backup"),
                     test_conditions=pw("25 C, 3.3 kW charge/discharge; efficiency at beginning of life"),
                     operating_temperature_c=pw([-20,50], "p.1 environmental specifications"),
                     thermal_derating_note=pw("Derating possible below 10 C or above 43 C; no numerical curve provided", "p.1 footnote 5")),
         discovery=fact("AC Powerwall 1092170-XX-Y",CEC,"2026-09-11","Model Number"),
         unresolved=["Usable-energy AC versus internal measurement boundary requires an explicit user assumption. Warranty footnote 'AC output' describes throughput, not capacity."],
         configuration_note="Identical complete AC units with one Backup Gateway, maximum 10. Site impedance, panel/gateway limits and installation approval are not simulated."),
    dict(id="franklinwh.apower2.apr10k15v2us.240", catalog_revision=REVISION,
         manufacturer="FranklinWH", model="aPower 2 — APR-10K15V2-US / aPower X-20", region="US/Canada, selected 120/240 V variant",
         market="residential", architecture=ap("ac_connected"),
         fields=dict(usable_energy_kwh=ap(15), total_energy_kwh=ap(None,"not stated"),
                     energy_basis=ap("ac_deliverable"), charge_kw=ap(8), discharge_kw=ap(10),
                     inverter_kva=ap(11.5), round_trip_efficiency=ap(.90),
                     efficiency_path=ap("ac_battery_ac"), voltage_v=ap([120,240]),
                     phase=ap("2 W+N+PE"), frequency_hz=ap(60), max_units=ap(15),
                     surge_kw=ap(15,"p.1: 10 seconds off-grid; 11.5 kVA configuration"),
                     test_conditions=ap("25 C, 3 kW charge/discharge, beginning of life; 8/10 kW ratings require 11.5 kVA setting"),
                     chemistry=ap("LFP", "p.1 battery chemistry"),
                     operating_temperature_c=ap([-20,50], "p.2 environmental specifications"),
                     thermal_derating_note=ap("Operation up to 55 C at 5 kW derated output; no full numerical curve provided", "p.2 environmental specifications")),
         discovery=fact("aPower Xyyy {240V, 10kW}",CEC,"2026-09-11","Model Number"),
         unresolved=["CEC also lists other Xyyy powers/voltages. They are not interchangeable with this SKU/configuration.","Site-specific aGate/service throughput limits remain installation inputs."],
         configuration_note="Identical complete AC units, up to 15 per aGate. Battery-only, mixed-product and 208 V arrangements are deferred."),
    dict(id="tesla.powerwall3.1707000.na", catalog_revision=REVISION,
         manufacturer="Tesla", model="Powerwall 3 — 1707000-xx-y (informational)", region="US/Canada",
         market="residential", architecture=pw3("hybrid_shared_inverter", "p.1 integrated solar and battery system"),
         fields=dict(nominal_ac_energy_kwh=pw3(13.5),
                     usable_energy_kwh=pw3(None, "p.2 calls energy nominal AC; usable-window mapping requires review"),
                     total_energy_kwh=pw3(None, "not stated"),
                     energy_basis=pw3(None, "usable-window mapping unresolved"),
                     charge_kw=pw3(5, "p.2 continuous AC charging, no Expansion"),
                     discharge_kw=pw3(None, "p.2 lists system AC output settings; separate battery-only mapping not established"),
                     inverter_kva=pw3(11.5, "p.2 selected maximum on-grid inverter setting"),
                     shared_ac_output_kw=pw3(11.5, "p.2 selected maximum on-grid system output"),
                     ac_output_settings_kw=pw3([5.8,7.6,10,11.5]),
                     round_trip_efficiency=pw3(None, "AC-to-battery-to-AC efficiency not stated"),
                     efficiency_path=pw3(None, "AC-to-battery-to-AC efficiency not stated"),
                     solar_battery_home_efficiency=pw3(.89, "p.2 footnotes 1,4; solar shifting path only"),
                     solar_home_efficiency=pw3(.975, "p.2 footnote 5; CEC-weighted PV conversion"),
                     voltage_v=pw3([120,240]), phase=pw3("split_phase"), frequency_hz=pw3(60),
                     max_units=pw3(4, "p.2 complete Powerwall 3 units"),
                     max_expansion_units=pw3(3, "p.2 maximum 3 Expansions, 7 total units"),
                     charge_with_expansion_kw=pw3(8, "p.2 with up to 3 Expansion units"),
                     pv_stc_input_kw=pw3(20, "p.3 solar specifications"),
                     pv_mppt_voltage_range_v=pw3([60,480], "p.3 solar specifications"),
                     mppt_count=pw3(6, "p.3 solar specifications"),
                     operating_temperature_c=pw3([-20,50], "p.3 environmental specifications"),
                     thermal_derating_note=pw3("Derating possible above 40 C; no numerical curve provided", "p.3 footnote 9"),
                     test_conditions=pw3("25 C, 3.3 kW charge/discharge, beginning of life; efficiency paths must remain separate")),
         discovery=None,
         unresolved=["Shared PV/storage inverter constraints are not implemented.",
                     "Published solar-to-battery-to-home efficiency is not AC-to-AC battery efficiency.",
                     "Nominal AC energy and system AC output are retained separately from unresolved usable-window and battery-only discharge mappings."],
         configuration_note="Data-only record for 11.5 kW on-grid setting, no Expansion. Unsupported by current resolver; Expansions do not add inverter power."),
]
