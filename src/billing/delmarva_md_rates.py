"""Snapshot-safe Delmarva Maryland verified retail component intersections.

See docs/utility_sources/delmarva_md for originals, dates and exclusions.
CSEG signs are converted to retail charges/credits. Its variable composites do
not include fixed USC/customer or SGS-S demand charges. No runtime API/cache.
"""
from datetime import date

PLANS = ("R", "SGS-S")
COVERAGE = (("2025-01-01", "2025-06-30"), ("2025-09-01", "2025-09-30"), ("2026-05-01", "2026-10-31"))
SOURCES = [
 'https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/bltefc1a0bec7ba2be7/6866ba338877742a736471bb/DPL_MD_Environmental_Surcharge_Update_Filing_.pdf?branch=prod_alias',
 'https://azure-na-assets.contentstack.com/v3/assets/blt47b6e332b18fb457/blt51d66aaf3a9d1f68/6a6d0cba9307daf5efc549e4/2026-07-06_MASTER_MD_DPL_Tariff_Book_1.pdf','https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/bltefc1a0bec7ba2be7/6abbd8bb794a17e7adb9629e/9226_9056_9064_DPL_MD_CURRENT_CLEAN_Admin_Charge_RTOUND_eff_100126.pdf?branch=prod_alias',
 'https://azure-na-assets.contentstack.com/v3/assets/blt47b6e332b18fb457/blt9a557615138ff16d/677315212fdcc317970bef4b/2024-12-11_MASTER_MD_DPL_Tariff_Book.pdf',
 'https://azure-na-assets.contentstack.com/v3/assets/blt47b6e332b18fb457/blt5cef29ea6692979d/68cc2f0c2755d52c3548c849/2025-09-04_MASTER_MD_DPL_Tariff_Book.pdf',
 'https://azure-na-assets.contentstack.com/v3/assets/blt47b6e332b18fb457/blt59b335dd053a56cf/6984dd40a88c121e90f51aa1/2025-12-31_MASTER_MD_DPL_Tariff_Book_.pdf',
 'https://azure-na-assets.contentstack.com/v3/assets/blt47b6e332b18fb457/blt3f938d0d9a94244e/6a8ddbe4c8beba22bf6a393f/2026-08-20_MASTER_DPL_MD_Tariff_Book.pdf',
 'https://azure-na-assets.contentstack.com/v3/assets/blt47b6e332b18fb457/blt710b9f1dbdaa74b9/67a4f005d7d66ba3bfc3bdc0/DPL_CURRENT_CLEAN_GREEN_RIDER_eff_020125.pdf',
 'https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/bltefc1a0bec7ba2be7/6836366f66e14842151acf57/MD_SOS_Type_II_generation_rates_and_Admin_Cha_.pdf?branch=prod_alias',
 'https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6813cee9952c500a8dd0aae0/DPL_MD_CSEG_-_05012025.pdf?branch=prod_alias',
 'https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/68b731f3c1561b3668f1c405/DPL_MD_CSEG_-_09012025.pdf?branch=prod_alias',
 'https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6abea98a15d5b70211b13d6c/CSEG_MD_DPL_-_10_2026_.pdf?branch=prod_alias']

# Generation, supply admin, PCA, transmission energy, distribution energy,
# BSA, MES, EmPOWER, administrative credit, franchise tax, MYP.
MONTHLY = {('2025-01', 'R'): (0.095756, 0.003852, 0.0054462, 0.019456, 0.071482, 0.00784, 0.00015, 0.012649, -0.001201, 0.00062, -0.002647),
 ('2025-01', 'SGS-S'): (0.095756, 0.004067, 0.0018674, 0.019838, 0.041549, 0.005563, 0.00015, 0.011191, -0.000506, 0.00062, -0.001756),
 ('2025-02', 'R'): (0.095756, 0.004813, 0.0050416, 0.019456, 0.071482, 0.000879, 0.00015, 0.012649, -0.001198, 0.00062, -0.002647),
 ('2025-02', 'SGS-S'): (0.095756, 0.005267, 0.0006043, 0.019838, 0.041549, -0.001825, 0.00015, 0.011191, -0.000461, 0.00062, -0.001756),
 ('2025-03', 'R'): (0.095756, 0.004813, 0.0046636, 0.019456, 0.071482, -0.004432, 0.00015, 0.012649, -0.001198, 0.00062, -0.002647),
 ('2025-03', 'SGS-S'): (0.095756, 0.005267, 0.001389, 0.019838, 0.041549, -0.0009, 0.00015, 0.011191, -0.000461, 0.00062, -0.001756),
 ('2025-04', 'R'): (0.095756, 0.004813, 0.0045395, 0.019456, 0.071482, -0.008236, 0.00015, 0.012649, -0.001198, 0.00062, -0.002647),
 ('2025-04', 'SGS-S'): (0.095756, 0.005267, 0.0018005, 0.019838, 0.041549, -0.007077, 0.00015, 0.011191, -0.000461, 0.00062, -0.001756),
 ('2025-05', 'R'): (0.095756, 0.004813, 0.0035164, 0.019456, 0.071482, -0.000542, 0.00015, 0.012649, -0.001198, 0.00062, -0.002647),
 ('2025-05', 'SGS-S'): (0.095756, 0.005267, 0.0010042, 0.019838, 0.041549, 0.000888, 0.00015, 0.011191, -0.000461, 0.00062, -0.001756),
 ('2025-06', 'R'): (0.09449, 0.004834, 0.004527, 0.019456, 0.071482, 0.008328, 0.00015, 0.012649, -0.001282, 0.00062, -0.002647),
 ('2025-06', 'SGS-S'): (0.094633, 0.003878, 0.0008805, 0.019838, 0.041549, -0.002572, 0.00015, 0.011191, -0.000816, 0.00062, -0.001756),
 ('2025-09', 'R'): (0.09449, 0.004834, 0.0084515, 0.020699, 0.071482, -0.008102, 0.000151, 0.012649, -0.001282, 0.00062, -0.000256),
 ('2025-09', 'SGS-S'): (0.094633, 0.003878, 0.0037256, 0.018466, 0.041549, -0.00595, 0.000151, 0.011191, -0.000816, 0.00062, -0.000171),
 ('2026-05', 'R'): (0.095462, 0.004429, 0.0066884, 0.020699, 0.071482, -0.008628, 0.000151, 0.020055, -0.001393, 0.00062, -0.000256),
 ('2026-05', 'SGS-S'): (0.093642, 0.004719, 0.0025753, 0.018466, 0.041549, -0.006056, 0.000151, 0.014937, -0.000802, 0.00062, -0.000171),
 ('2026-06', 'R'): (0.098203, 0.004617, 0.0070129, 0.020699, 0.071482, -0.001603, 0.000151, 0.020055, -0.00138, 0.00062, -0.000256),
 ('2026-06', 'SGS-S'): (0.09863, 0.003944, 0.0025516, 0.018466, 0.041549, -0.000579, 0.000151, 0.014937, -0.000843, 0.00062, -0.000171),
 ('2026-07', 'R'): (0.098203, 0.004617, 0.0075479, 0.020699, 0.071482, 0.002644, 0.00015, 0.020055, -0.00138, 0.00062, -0.000256),
 ('2026-07', 'SGS-S'): (0.09863, 0.003944, 0.0028041, 0.018466, 0.041549, 0.00323, 0.00015, 0.014937, -0.000843, 0.00062, -0.000171),
 ('2026-08', 'R'): (0.098203, 0.004617, 0.0094853, 0.020699, 0.071482, 0.002305, 0.00015, 0.020055, -0.00138, 0.00062, -0.000256),
 ('2026-08', 'SGS-S'): (0.09863, 0.003944, 0.0037427, 0.018466, 0.041549, 0.000547, 0.00015, 0.014937, -0.000843, 0.00062, -0.000171),
 ('2026-09', 'R'): (0.098203, 0.004617, 0.0102448, 0.021361, 0.071482, -0.002557, 0.00015, 0.020055, -0.00138, 0.00062, -0.000256),
 ('2026-09', 'SGS-S'): (0.09863, 0.003944, 0.0043628, 0.018205, 0.041549, -0.000852, 0.00015, 0.014937, -0.000843, 0.00062, -0.000171),
 ('2026-10', 'R'): (0.106302, 0.004267, 0.0101653, 0.021361, 0.071482, 0.008578, 0.00015, 0.020055, -0.00142, 0.00062, -0.000256),
 ('2026-10', 'SGS-S'): (0.103693, 0.003784, 0.0043337, 0.018205, 0.041549, 0.001865, 0.00015, 0.014937, -0.000901, 0.00062, -0.000171)}


SOURCE_REFERENCES = {('2025-01', 'R'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6813cee9952c500a8dd0aae0/DPL_MD_CSEG_-_05012025.pdf?branch=prod_alias',
                    1),
 ('2025-01', 'SGS-S'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6813cee9952c500a8dd0aae0/DPL_MD_CSEG_-_05012025.pdf?branch=prod_alias',
                        2),
 ('2025-02', 'R'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6813cee9952c500a8dd0aae0/DPL_MD_CSEG_-_05012025.pdf?branch=prod_alias',
                    1),
 ('2025-02', 'SGS-S'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6813cee9952c500a8dd0aae0/DPL_MD_CSEG_-_05012025.pdf?branch=prod_alias',
                        2),
 ('2025-03', 'R'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6813cee9952c500a8dd0aae0/DPL_MD_CSEG_-_05012025.pdf?branch=prod_alias',
                    1),
 ('2025-03', 'SGS-S'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6813cee9952c500a8dd0aae0/DPL_MD_CSEG_-_05012025.pdf?branch=prod_alias',
                        2),
 ('2025-04', 'R'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/68b731f3c1561b3668f1c405/DPL_MD_CSEG_-_09012025.pdf?branch=prod_alias',
                    1),
 ('2025-04', 'SGS-S'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/68b731f3c1561b3668f1c405/DPL_MD_CSEG_-_09012025.pdf?branch=prod_alias',
                        2),
 ('2025-05', 'R'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/68b731f3c1561b3668f1c405/DPL_MD_CSEG_-_09012025.pdf?branch=prod_alias',
                    1),
 ('2025-05', 'SGS-S'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/68b731f3c1561b3668f1c405/DPL_MD_CSEG_-_09012025.pdf?branch=prod_alias',
                        2),
 ('2025-06', 'R'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/68b731f3c1561b3668f1c405/DPL_MD_CSEG_-_09012025.pdf?branch=prod_alias',
                    1),
 ('2025-06', 'SGS-S'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/68b731f3c1561b3668f1c405/DPL_MD_CSEG_-_09012025.pdf?branch=prod_alias',
                        2),
 ('2025-09', 'R'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/68b731f3c1561b3668f1c405/DPL_MD_CSEG_-_09012025.pdf?branch=prod_alias',
                    1),
 ('2025-09', 'SGS-S'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/68b731f3c1561b3668f1c405/DPL_MD_CSEG_-_09012025.pdf?branch=prod_alias',
                        2),
 ('2026-05', 'R'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6abea98a15d5b70211b13d6c/CSEG_MD_DPL_-_10_2026_.pdf?branch=prod_alias',
                    1),
 ('2026-05', 'SGS-S'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6abea98a15d5b70211b13d6c/CSEG_MD_DPL_-_10_2026_.pdf?branch=prod_alias',
                        4),
 ('2026-06', 'R'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6abea98a15d5b70211b13d6c/CSEG_MD_DPL_-_10_2026_.pdf?branch=prod_alias',
                    1),
 ('2026-06', 'SGS-S'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6abea98a15d5b70211b13d6c/CSEG_MD_DPL_-_10_2026_.pdf?branch=prod_alias',
                        4),
 ('2026-07', 'R'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6abea98a15d5b70211b13d6c/CSEG_MD_DPL_-_10_2026_.pdf?branch=prod_alias',
                    1),
 ('2026-07', 'SGS-S'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6abea98a15d5b70211b13d6c/CSEG_MD_DPL_-_10_2026_.pdf?branch=prod_alias',
                        4),
 ('2026-08', 'R'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6abea98a15d5b70211b13d6c/CSEG_MD_DPL_-_10_2026_.pdf?branch=prod_alias',
                    1),
 ('2026-08', 'SGS-S'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6abea98a15d5b70211b13d6c/CSEG_MD_DPL_-_10_2026_.pdf?branch=prod_alias',
                        4),
 ('2026-09', 'R'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6abea98a15d5b70211b13d6c/CSEG_MD_DPL_-_10_2026_.pdf?branch=prod_alias',
                    1),
 ('2026-09', 'SGS-S'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6abea98a15d5b70211b13d6c/CSEG_MD_DPL_-_10_2026_.pdf?branch=prod_alias',
                        4),
 ('2026-10', 'R'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6abea98a15d5b70211b13d6c/CSEG_MD_DPL_-_10_2026_.pdf?branch=prod_alias',
                    1),
 ('2026-10', 'SGS-S'): ('https://www.delmarva.com/cdn/assets/v3/assets/blt47b6e332b18fb457/blt37f69113f2ff3899/6abea98a15d5b70211b13d6c/CSEG_MD_DPL_-_10_2026_.pdf?branch=prod_alias',
                        4)}

def rates_on(day, plan="R"):
    key = day.isoformat() if type(day) is date else day
    try:
        if not isinstance(key, str) or date.fromisoformat(key).isoformat() != key:
            raise ValueError
    except ValueError as exc:
        raise ValueError("Use exact ISO Delmarva Maryland local dates.") from exc
    if plan not in PLANS:
        raise ValueError("Select Delmarva Maryland R or SGS-S Type I SOS.")
    if not any(start <= key <= end for start, end in COVERAGE):
        raise ValueError("Delmarva verified intersections cover January–June2025, September2025 and May–October2026 only. July/August2025 allocation and October2025–April2026 monthly history are unverified; no fallback.")
    values = MONTHLY[(key[:7], plan)]
    names = ("generation_energy", "supply_administration", "procurement_cost_adjustment", "transmission_energy",
        "distribution_energy", "bill_stabilization_adjustment", "environmental_surcharge", "empower_maryland",
        "administrative_delivery_credit", "franchise_tax", "multi_year_plan_adjustment")
    energy = dict(zip(names, values))
    return dict(customer=9.43 if plan == "R" else 26., energy=energy,
        monthly=dict(universal_service=.32 if plan == "R" else 1.85),
        distribution_demand_rate=0. if plan == "R" else 4.303679,
        transmission_energy_scope="All R imports; SGS-S first3500kWh only, study imports bounded to3500kWh",
        transmission_demand_scope="SGS-S first20kW free; utility-estimated study demand bounded to20kW",
        gross_receipts_treatment="Embedded in applicable filed rates; no additional GRT multiplier",
        component_month=key[:7],
        source=SOURCE_REFERENCES[(key[:7], plan)][0],
        source_pdf_page=SOURCE_REFERENCES[(key[:7], plan)][1],
        minimum_charge_basis="Customer-charge minimum inactive: selected net variable composites and estimated-demand rate are nonnegative",
        environmental_surcharge_basis="Actual filed retail MES factor; statutory assessment cap is not substituted for the filed customer rate",
        coverage_basis="Recovered matching complete calendar service/billing months; separate incomplete total-bill disclosure")
