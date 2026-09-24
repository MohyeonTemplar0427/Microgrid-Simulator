# PG&E tariff reference

**Generated file — do not edit by hand.** Regenerate with:

```bash
/usr/local/bin/python3 tools/generate_tariff_reference.py
```

Every rate below is read from the tariff registry built by `src/billing/pge_commercial.py` and `src/billing/pge_residential.py`, so this document and the numbers the billing code applies cannot disagree. Rates are transcribed from PG&E's published tariff sheets and historical rate workbooks, and are valid for the stated effective date only; a simulation picks the version effective on each local service date via `src/billing/plans.py`. See [Microgrid_Backend_Architecture.md](Microgrid_Backend_Architecture.md) for why tariffs are versioned data rather than editable constants.

All schedules below are **secondary voltage, bundled service**. Primary and Transmission voltage classes, Peak Day Pricing, power-factor adjustments and standby charges are not modelled.

## How the plans compare

The families form a progression: as an account grows, the fixed and demand charges rise while the energy spread narrows. A battery earns its value from the energy spread on the small schedules and from peak reduction on the large ones.

Spread is summer peak minus summer off-peak — the per-kWh margin a battery captures by shifting one kilowatt-hour out of the peak window. It is the only derived figure in these tables; every other number is read straight from the registry. Winter rates and the part-peak blocks are in the next table.

### Charges at a glance

| Schedule | Eligibility | Customer $/day | Summer peak $/kWh | Summer off-peak $/kWh | Summer spread $/kWh |
| --- | --- | ---: | ---: | ---: | ---: |
| PG&E B-1 Small General Service (Single-Phase) | Under 75 kW | 0.32854 | 0.47087 | 0.40083 | 0.07004 |
| PG&E B-1 Small General Service (Polyphase) | Under 75 kW | 0.82136 | 0.47087 | 0.40083 | 0.07004 |
| PG&E B-6 Small General Time-of-Use Service (Single-Phase) | Under 75 kW | 0.32854 | 0.64253 | 0.38491 | 0.25762 |
| PG&E B-6 Small General Time-of-Use Service (Polyphase) | Under 75 kW | 0.82136 | 0.64253 | 0.38491 | 0.25762 |
| PG&E B-10 Medium General Demand-Metered Service | 75-499 kW (voluntary below 75 kW) | 11.36882 | 0.33947 | 0.24522 | 0.09425 |
| PG&E B-19 Medium General Demand-Metered TOU Service (Mandatory) | 500-999 kW | 58.62824 | 0.18648 | 0.12037 | 0.06611 |
| PG&E B-19 Medium General Demand-Metered TOU Service (Voluntary) | Opt-in below 500 kW | 11.36882 | 0.18648 | 0.12037 | 0.06611 |
| PG&E B-19 Option R (Renewables), Mandatory Tier | B-19 accounts with renewables | 58.62824 | 0.43568 | 0.19137 | 0.24431 |
| PG&E B-19 Option S (Storage), Mandatory Tier | B-19 accounts with storage | 58.62824 | 0.43568 | 0.19137 | 0.24431 |
| PG&E B-20 Large General Demand-Metered TOU Service | 1,000 kW or more | 107.36636 | 0.17702 | 0.11482 | 0.06220 |
| PG&E B-20 Option R (Renewables) | B-20 accounts with renewables | 107.36636 | 0.40620 | 0.16434 | 0.24186 |
| PG&E B-20 Option S (Storage) | B-20 accounts with storage | 107.36636 | 0.40620 | 0.16434 | 0.24186 |
| PG&E E-TOU-D Residential TOU 5-8 p.m. (Income Tier 1) | Residential, opt-in; income tier 1 (CARE-level) | 0.19713 | 0.47708 | 0.34212 | 0.13496 |
| PG&E E-TOU-D Residential TOU 5-8 p.m. (Income Tier 2) | Residential, opt-in; income tier 2 (FERA-level) | 0.39688 | 0.47708 | 0.34212 | 0.13496 |
| PG&E E-TOU-D Residential TOU 5-8 p.m. (Income Tier 3) | Residential, opt-in; income tier 3 (all others) | 0.79343 | 0.47708 | 0.34212 | 0.13496 |
| PG&E E-ELEC Residential Electric Home (Income Tier 1) | Electrified home, opt-in; income tier 1 (CARE-level) | 0.19713 | 0.55214 | 0.33358 | 0.21856 |
| PG&E E-ELEC Residential Electric Home (Income Tier 2) | Electrified home, opt-in; income tier 2 (FERA-level) | 0.39688 | 0.55214 | 0.33358 | 0.21856 |
| PG&E E-ELEC Residential Electric Home (Income Tier 3) | Electrified home, opt-in; income tier 3 (all others) | 0.79343 | 0.55214 | 0.33358 | 0.21856 |
| PG&E EV2-A Residential Electric Vehicle (Income Tier 1) | Household with an EV; income tier 1 (CARE-level) | 0.19713 | 0.53809 | 0.22558 | 0.31251 |
| PG&E EV2-A Residential Electric Vehicle (Income Tier 2) | Household with an EV; income tier 2 (FERA-level) | 0.39688 | 0.53809 | 0.22558 | 0.31251 |
| PG&E EV2-A Residential Electric Vehicle (Income Tier 3) | Household with an EV; income tier 3 (all others) | 0.79343 | 0.53809 | 0.22558 | 0.31251 |

### Energy rates side by side ($/kWh)

The two summer part-peak blocks (afternoon and evening) always carry the same rate, so they share one column. A dash means the schedule has no such period — B-1 and B-6 are energy-only schedules, and B-6 has no part-peak block at all.

| Schedule | Summer peak<br><sub>16-21</sub> | Summer part-peak<br><sub>14-16, 21-23</sub> | Summer off-peak<br><sub>rest</sub> | Winter peak<br><sub>16-21</sub> | Winter super-off-peak<br><sub>9-14, Mar-May</sub> | Winter off-peak<br><sub>rest</sub> |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| B-1 single-phase | 0.47087 | 0.42164 | 0.40083 | 0.39545 | 0.36291 | 0.37933 |
| B-1 polyphase | 0.47087 | 0.42164 | 0.40083 | 0.39545 | 0.36291 | 0.37933 |
| B-6 single-phase | 0.64253 | — | 0.38491 | 0.39584 | 0.31617 | 0.35225 |
| B-6 polyphase | 0.64253 | — | 0.38491 | 0.39584 | 0.31617 | 0.35225 |
| B-10 | 0.33947 | 0.27778 | 0.24522 | 0.26321 | 0.19139 | 0.22773 |
| B-19 mandatory | 0.18648 | 0.14775 | 0.12037 | 0.16188 | 0.06442 | 0.12026 |
| B-19 voluntary | 0.18648 | 0.14775 | 0.12037 | 0.16188 | 0.06442 | 0.12026 |
| B-19 Option R | 0.43568 | 0.25184 | 0.19137 | 0.18276 | 0.10462 | 0.14044 |
| B-19 Option S | 0.43568 | 0.25184 | 0.19137 | 0.18276 | 0.10462 | 0.14044 |
| B-20 | 0.17702 | 0.14227 | 0.11482 | 0.15632 | 0.05872 | 0.11460 |
| B-20 Option R | 0.40620 | 0.22337 | 0.16434 | 0.17396 | 0.09448 | 0.13023 |
| B-20 Option S | 0.40620 | 0.22337 | 0.16434 | 0.17396 | 0.09448 | 0.13023 |
| pge_e_tou_d_residential_tier1_bundled_2026_06_01 | 0.47708 | — | 0.34212 | 0.38747 | — | 0.34886 |
| pge_e_tou_d_residential_tier2_bundled_2026_06_01 | 0.47708 | — | 0.34212 | 0.38747 | — | 0.34886 |
| pge_e_tou_d_residential_tier3_bundled_2026_06_01 | 0.47708 | — | 0.34212 | 0.38747 | — | 0.34886 |
| pge_e_elec_residential_tier1_bundled_2026_06_01 | 0.55214 | 0.39026 | 0.33358 | 0.32063 | — | 0.28468 |
| pge_e_elec_residential_tier2_bundled_2026_06_01 | 0.55214 | 0.39026 | 0.33358 | 0.32063 | — | 0.28468 |
| pge_e_elec_residential_tier3_bundled_2026_06_01 | 0.55214 | 0.39026 | 0.33358 | 0.32063 | — | 0.28468 |
| pge_ev2_residential_tier1_bundled_2026_06_01 | 0.53809 | 0.42760 | 0.22558 | 0.41099 | — | 0.22558 |
| pge_ev2_residential_tier2_bundled_2026_06_01 | 0.53809 | 0.42760 | 0.22558 | 0.41099 | — | 0.22558 |
| pge_ev2_residential_tier3_bundled_2026_06_01 | 0.53809 | 0.42760 | 0.22558 | 0.41099 | — | 0.22558 |

### Monthly demand charges side by side ($/kW per billing month)

Components apply together, so a summer peak-hour kilowatt on B-19 or B-20 can attract three of them at once. A dash means the schedule does not bill that component; both Option R schedules price winter peak-period demand at zero. Option S has separate daily and monthly charges and is listed below this table.

| Schedule | Maximum | Summer peak-period | Summer part-peak-period | Winter peak-period | Summer sum | Winter sum |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| B-1 single-phase | — | — | — | — | 0.00 | 0.00 |
| B-1 polyphase | — | — | — | — | 0.00 | 0.00 |
| B-6 single-phase | — | — | — | — | 0.00 | 0.00 |
| B-6 polyphase | — | — | — | — | 0.00 | 0.00 |
| B-10 | 20.50 | — | — | — | 20.50 | 20.50 |
| B-19 mandatory | 37.37 | 46.16 | 10.52 | 2.31 | 94.05 | 39.68 |
| B-19 voluntary | 37.37 | 46.16 | 10.52 | 2.31 | 94.05 | 39.68 |
| B-19 Option R | 36.61 | 6.50 | 1.87 | — | 44.98 | 36.61 |
| B-20 | 39.08 | 41.35 | 9.27 | 2.32 | 89.70 | 41.40 |
| B-20 Option R | 38.23 | 5.62 | 1.61 | — | 45.46 | 38.23 |
| pge_e_tou_d_residential_tier1_bundled_2026_06_01 | — | — | — | — | 0.00 | 0.00 |
| pge_e_tou_d_residential_tier2_bundled_2026_06_01 | — | — | — | — | 0.00 | 0.00 |
| pge_e_tou_d_residential_tier3_bundled_2026_06_01 | — | — | — | — | 0.00 | 0.00 |
| pge_e_elec_residential_tier1_bundled_2026_06_01 | — | — | — | — | 0.00 | 0.00 |
| pge_e_elec_residential_tier2_bundled_2026_06_01 | — | — | — | — | 0.00 | 0.00 |
| pge_e_elec_residential_tier3_bundled_2026_06_01 | — | — | — | — | 0.00 | 0.00 |
| pge_ev2_residential_tier1_bundled_2026_06_01 | — | — | — | — | 0.00 | 0.00 |
| pge_ev2_residential_tier2_bundled_2026_06_01 | — | — | — | — | 0.00 | 0.00 |
| pge_ev2_residential_tier3_bundled_2026_06_01 | — | — | — | — | 0.00 | 0.00 |

Option S: B-19 bills $6.35/kW monthly excluding 09:00–14:00, $9.13/kW monthly across all hours, $1.60/kW **per day** at the summer peak, $0.08/kW per day at summer part-peak, and $1.22/kW per day at the winter peak. B-20 has the same scopes at $5.56, $11.06, $1.30, $0.07, and $1.02 respectively. Summer and winter daily charges do not apply together.

Seasons are the same on every schedule: **summer is June 1 through September 30**, winter is October 1 through May 31. Every *commercial* period applies *every day, including weekends and holidays*. The residential time-of-use schedules do not: their peak is weekday-only, and the Hours column says so. Holidays are not modelled anywhere — a holiday falling on a weekday is priced at the ordinary weekday rate.

Schedules priced by usage tier rather than by hour (E-1) are compared separately below; peak and off-peak have no meaning for them.

### Tiered schedules

| Schedule | Eligibility | Customer $/day | Baseline territory | Tier 1 $/kWh | Tier 2 $/kWh |
| --- | --- | ---: | :---: | ---: | ---: |
| PG&E E-1 Residential Tiered (Income Tier 1) | Residential default schedule; income tier 1 (CARE-level) | 0.19713 | T | 0.32561 | 0.40702 |
| PG&E E-1 Residential Tiered (Income Tier 2) | Residential default schedule; income tier 2 (FERA-level) | 0.39688 | T | 0.32561 | 0.40702 |
| PG&E E-1 Residential Tiered (Income Tier 3) | Residential default schedule; income tier 3 (all others) | 0.79343 | T | 0.32561 | 0.40702 |

---

## PG&E B-1 Small General Service (Single-Phase)

- **Tariff id**: `pge_b1_secondary_single_phase_bundled_2026_03_01`
- **Eligibility**: Under 75 kW
- **Service**: secondary voltage, bundled, commercial
- **Customer charge**: $0.32854 per meter per day (about $9.86 over 30 days)
- **Effective**: 2026-03-01 (version `2026-03-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-1.pdf>

### Energy rates

| Period | Season | Hours | $/kWh |
| --- | --- | --- | ---: |
| summer_peak | Summer | 16:00-21:00 | 0.47087 |
| summer_part_peak_afternoon | Summer | 14:00-16:00 | 0.42164 |
| summer_part_peak_evening | Summer | 21:00-23:00 | 0.42164 |
| summer_off_peak | Summer | all remaining hours | 0.40083 |
| winter_peak | Winter | 16:00-21:00 | 0.39545 |
| winter_super_off_peak | Winter | 09:00-14:00 (Mar, Apr, May only) | 0.36291 |
| winter_off_peak | Winter | all remaining hours | 0.37933 |

### Demand charges

None. This schedule bills energy and the customer charge only, so the bill never depends on the monthly peak.

### Export compensation

B-1 export compensation is not part of the B-1 rate schedule. Configure the account's NEM or Net Billing Tariff export prices separately.

### Notes

Standard B-1, secondary voltage and bundled service. The account must not have reached 75 kW or more for three consecutive months in the latest twelve. B1-ST, PDP, CCA, Direct Access, export compensation, standby charges and power-factor adjustments are not modelled.

---

## PG&E B-1 Small General Service (Polyphase)

- **Tariff id**: `pge_b1_secondary_polyphase_bundled_2026_03_01`
- **Eligibility**: Under 75 kW
- **Service**: secondary voltage, bundled, commercial
- **Customer charge**: $0.82136 per meter per day (about $24.64 over 30 days)
- **Effective**: 2026-03-01 (version `2026-03-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-1.pdf>

### Energy rates

| Period | Season | Hours | $/kWh |
| --- | --- | --- | ---: |
| summer_peak | Summer | 16:00-21:00 | 0.47087 |
| summer_part_peak_afternoon | Summer | 14:00-16:00 | 0.42164 |
| summer_part_peak_evening | Summer | 21:00-23:00 | 0.42164 |
| summer_off_peak | Summer | all remaining hours | 0.40083 |
| winter_peak | Winter | 16:00-21:00 | 0.39545 |
| winter_super_off_peak | Winter | 09:00-14:00 (Mar, Apr, May only) | 0.36291 |
| winter_off_peak | Winter | all remaining hours | 0.37933 |

### Demand charges

None. This schedule bills energy and the customer charge only, so the bill never depends on the monthly peak.

### Export compensation

B-1 export compensation is not part of the B-1 rate schedule. Configure the account's NEM or Net Billing Tariff export prices separately.

### Notes

Standard B-1, secondary voltage and bundled service. The account must not have reached 75 kW or more for three consecutive months in the latest twelve. B1-ST, PDP, CCA, Direct Access, export compensation, standby charges and power-factor adjustments are not modelled.

---

## PG&E B-6 Small General Time-of-Use Service (Single-Phase)

- **Tariff id**: `pge_b6_secondary_single_phase_bundled_2026_03_01`
- **Eligibility**: Under 75 kW
- **Service**: secondary voltage, bundled, commercial
- **Customer charge**: $0.32854 per meter per day (about $9.86 over 30 days)
- **Effective**: 2026-03-01 (version `2026-03-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-6.pdf>

### Energy rates

| Period | Season | Hours | $/kWh |
| --- | --- | --- | ---: |
| summer_peak | Summer | 16:00-21:00 | 0.64253 |
| summer_off_peak | Summer | all remaining hours | 0.38491 |
| winter_peak | Winter | 16:00-21:00 | 0.39584 |
| winter_super_off_peak | Winter | 09:00-14:00 (Mar, Apr, May only) | 0.31617 |
| winter_off_peak | Winter | all remaining hours | 0.35225 |

### Demand charges

None. This schedule bills energy and the customer charge only, so the bill never depends on the monthly peak.

### Export compensation

B-6 export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Small General Time-of-Use Service, secondary voltage, bundled service. The account must not have reached 75 kW or more for three consecutive months in the latest twelve. Not modelled: Peak Day Pricing, which B-6 defaults eligible customers onto and which prices event hours at $0.60/kWh against a summer peak credit -- it needs PG&E's event calendar, which is not available here. CCA, Direct Access, standby charges and power-factor adjustments are also not modelled.

---

## PG&E B-6 Small General Time-of-Use Service (Polyphase)

- **Tariff id**: `pge_b6_secondary_polyphase_bundled_2026_03_01`
- **Eligibility**: Under 75 kW
- **Service**: secondary voltage, bundled, commercial
- **Customer charge**: $0.82136 per meter per day (about $24.64 over 30 days)
- **Effective**: 2026-03-01 (version `2026-03-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-6.pdf>

### Energy rates

| Period | Season | Hours | $/kWh |
| --- | --- | --- | ---: |
| summer_peak | Summer | 16:00-21:00 | 0.64253 |
| summer_off_peak | Summer | all remaining hours | 0.38491 |
| winter_peak | Winter | 16:00-21:00 | 0.39584 |
| winter_super_off_peak | Winter | 09:00-14:00 (Mar, Apr, May only) | 0.31617 |
| winter_off_peak | Winter | all remaining hours | 0.35225 |

### Demand charges

None. This schedule bills energy and the customer charge only, so the bill never depends on the monthly peak.

### Export compensation

B-6 export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Small General Time-of-Use Service, secondary voltage, bundled service. The account must not have reached 75 kW or more for three consecutive months in the latest twelve. Not modelled: Peak Day Pricing, which B-6 defaults eligible customers onto and which prices event hours at $0.60/kWh against a summer peak credit -- it needs PG&E's event calendar, which is not available here. CCA, Direct Access, standby charges and power-factor adjustments are also not modelled.

---

## PG&E B-10 Medium General Demand-Metered Service

- **Tariff id**: `pge_b10_secondary_bundled_2026_03_01`
- **Eligibility**: 75-499 kW (voluntary below 75 kW)
- **Service**: secondary voltage, bundled, commercial
- **Customer charge**: $11.36882 per meter per day (about $341.06 over 30 days)
- **Effective**: 2026-03-01 (version `2026-03-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-10.pdf>

### Energy rates

| Period | Season | Hours | $/kWh |
| --- | --- | --- | ---: |
| summer_peak | Summer | 16:00-21:00 | 0.33947 |
| summer_part_peak_afternoon | Summer | 14:00-16:00 | 0.27778 |
| summer_part_peak_evening | Summer | 21:00-23:00 | 0.27778 |
| summer_off_peak | Summer | all remaining hours | 0.24522 |
| winter_peak | Winter | 16:00-21:00 | 0.26321 |
| winter_super_off_peak | Winter | 09:00-14:00 (Mar, Apr, May only) | 0.19139 |
| winter_off_peak | Winter | all remaining hours | 0.22773 |

### Demand charges

| Component | Season | Measured over | Frequency | Rate ($/kW) |
| --- | --- | --- | --- | ---: |
| maximum_demand | All year | highest interval demand in the billing month | monthly | 20.50 |

Each component is calculated in its own stated time scope; summer and winter components are mutually exclusive. Daily rates apply to each local day's applicable peak, while monthly rates apply once to the billing month's applicable peak.

### Export compensation

B-10 export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Secondary voltage means service below 2,400 V, which includes the modelled 480 V service. Rates are bundled (PG&E supplies generation); CCA and Direct Access customers pay different generation components and are not modelled.

---

## PG&E B-19 Medium General Demand-Metered TOU Service (Mandatory)

- **Tariff id**: `pge_b19_secondary_mandatory_bundled_2026_03_01`
- **Eligibility**: 500-999 kW
- **Service**: secondary voltage, bundled, commercial
- **Customer charge**: $58.62824 per meter per day (about $1,758.85 over 30 days)
- **Effective**: 2026-03-01 (version `2026-03-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-19.pdf>

### Energy rates

| Period | Season | Hours | $/kWh |
| --- | --- | --- | ---: |
| summer_peak | Summer | 16:00-21:00 | 0.18648 |
| summer_part_peak_afternoon | Summer | 14:00-16:00 | 0.14775 |
| summer_part_peak_evening | Summer | 21:00-23:00 | 0.14775 |
| summer_off_peak | Summer | all remaining hours | 0.12037 |
| winter_peak | Winter | 16:00-21:00 | 0.16188 |
| winter_super_off_peak | Winter | 09:00-14:00 (Mar, Apr, May only) | 0.06442 |
| winter_off_peak | Winter | all remaining hours | 0.12026 |

### Demand charges

| Component | Season | Measured over | Frequency | Rate ($/kW) |
| --- | --- | --- | --- | ---: |
| maximum_demand | All year | highest interval demand in the billing month | monthly | 37.37 |
| peak_period_demand_summer | Summer | highest demand inside peak hours | monthly | 46.16 |
| part_peak_period_demand_summer | Summer | highest demand inside part-peak hours | monthly | 10.52 |
| peak_period_demand_winter | Winter | highest demand inside peak hours | monthly | 2.31 |

Each component is calculated in its own stated time scope; summer and winter components are mutually exclusive. Daily rates apply to each local day's applicable peak, while monthly rates apply once to the billing month's applicable peak.

### Export compensation

B-19 export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Mandatory tier, secondary voltage, bundled service only. The Voluntary tier and Options R and S are registered separately as `pge_b19_secondary_voluntary_bundled_2026_03_01`, `..._option_r_...` and `..._option_s_...`. Not modelled: Primary and Transmission voltage classes, and the power-factor adjustment. `previous_peak_kw` carryover applies only to the maximum-demand component -- the peak-period and part-peak-period components always start fresh from the supplied data, same caveat as a MAXIMUM-only tariff's first partial period.

---

## PG&E B-19 Medium General Demand-Metered TOU Service (Voluntary)

- **Tariff id**: `pge_b19_secondary_voluntary_bundled_2026_03_01`
- **Eligibility**: Opt-in below 500 kW
- **Service**: secondary voltage, bundled, commercial
- **Customer charge**: $11.36882 per meter per day (about $341.06 over 30 days)
- **Effective**: 2026-03-01 (version `2026-03-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-19.pdf>

### Energy rates

| Period | Season | Hours | $/kWh |
| --- | --- | --- | ---: |
| summer_peak | Summer | 16:00-21:00 | 0.18648 |
| summer_part_peak_afternoon | Summer | 14:00-16:00 | 0.14775 |
| summer_part_peak_evening | Summer | 21:00-23:00 | 0.14775 |
| summer_off_peak | Summer | all remaining hours | 0.12037 |
| winter_peak | Winter | 16:00-21:00 | 0.16188 |
| winter_super_off_peak | Winter | 09:00-14:00 (Mar, Apr, May only) | 0.06442 |
| winter_off_peak | Winter | all remaining hours | 0.12026 |

### Demand charges

| Component | Season | Measured over | Frequency | Rate ($/kW) |
| --- | --- | --- | --- | ---: |
| maximum_demand | All year | highest interval demand in the billing month | monthly | 37.37 |
| peak_period_demand_summer | Summer | highest demand inside peak hours | monthly | 46.16 |
| part_peak_period_demand_summer | Summer | highest demand inside part-peak hours | monthly | 10.52 |
| peak_period_demand_winter | Winter | highest demand inside peak hours | monthly | 2.31 |

Each component is calculated in its own stated time scope; summer and winter components are mutually exclusive. Daily rates apply to each local day's applicable peak, while monthly rates apply once to the billing month's applicable peak.

### Export compensation

Export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Voluntary tier: identical rates to Mandatory B-19 apart from the customer charge ($11.36882 rather than $58.62824 per day). Secondary voltage, bundled service only. Not modelled: Primary and Transmission voltage classes, the power-factor adjustment, Peak Day Pricing, and Schedule SB standby charges. `previous_peak_kw` carryover applies only to the all-hours monthly maximum-demand component.

---

## PG&E B-19 Option R (Renewables), Mandatory Tier

- **Tariff id**: `pge_b19_secondary_option_r_bundled_2026_03_01`
- **Eligibility**: B-19 accounts with renewables
- **Service**: secondary voltage, bundled, commercial
- **Customer charge**: $58.62824 per meter per day (about $1,758.85 over 30 days)
- **Effective**: 2026-03-01 (version `2026-03-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-19.pdf>

### Energy rates

| Period | Season | Hours | $/kWh |
| --- | --- | --- | ---: |
| summer_peak | Summer | 16:00-21:00 | 0.43568 |
| summer_part_peak_afternoon | Summer | 14:00-16:00 | 0.25184 |
| summer_part_peak_evening | Summer | 21:00-23:00 | 0.25184 |
| summer_off_peak | Summer | all remaining hours | 0.19137 |
| winter_peak | Winter | 16:00-21:00 | 0.18276 |
| winter_super_off_peak | Winter | 09:00-14:00 (Mar, Apr, May only) | 0.10462 |
| winter_off_peak | Winter | all remaining hours | 0.14044 |

### Demand charges

| Component | Season | Measured over | Frequency | Rate ($/kW) |
| --- | --- | --- | --- | ---: |
| maximum_demand | All year | highest interval demand in the billing month | monthly | 36.61 |
| peak_period_demand_summer | Summer | highest demand inside peak hours | monthly | 6.50 |
| part_peak_period_demand_summer | Summer | highest demand inside part-peak hours | monthly | 1.87 |

Each component is calculated in its own stated time scope; summer and winter components are mutually exclusive. Daily rates apply to each local day's applicable peak, while monthly rates apply once to the billing month's applicable peak.

### Export compensation

Export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Option R, mandatory-tier customer charge. Eligibility rules for Option R enrolment are not modelled. Secondary voltage, bundled service only. Not modelled: Primary and Transmission voltage classes, the power-factor adjustment, Peak Day Pricing, and Schedule SB standby charges. `previous_peak_kw` carryover applies only to the all-hours monthly maximum-demand component.

---

## PG&E B-19 Option S (Storage), Mandatory Tier

- **Tariff id**: `pge_b19_secondary_option_s_bundled_2026_03_01`
- **Eligibility**: B-19 accounts with storage
- **Service**: secondary voltage, bundled, commercial
- **Customer charge**: $58.62824 per meter per day (about $1,758.85 over 30 days)
- **Effective**: 2026-03-01 (version `2026-03-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-19.pdf>

### Energy rates

| Period | Season | Hours | $/kWh |
| --- | --- | --- | ---: |
| summer_peak | Summer | 16:00-21:00 | 0.43568 |
| summer_part_peak_afternoon | Summer | 14:00-16:00 | 0.25184 |
| summer_part_peak_evening | Summer | 21:00-23:00 | 0.25184 |
| summer_off_peak | Summer | all remaining hours | 0.19137 |
| winter_peak | Winter | 16:00-21:00 | 0.18276 |
| winter_super_off_peak | Winter | 09:00-14:00 (Mar, Apr, May only) | 0.10462 |
| winter_off_peak | Winter | all remaining hours | 0.14044 |

### Demand charges

| Component | Season | Measured over | Frequency | Rate ($/kW) |
| --- | --- | --- | --- | ---: |
| maximum_demand_excluding_09_to_14 | All year | highest interval demand in the billing month, excluding 09:00–14:00 local time | monthly | 6.35 |
| maximum_demand_all_hours | All year | highest interval demand in the billing month | monthly | 9.13 |
| peak_period_demand_summer_daily | Summer | highest demand inside peak hours | daily | 1.60 |
| part_peak_period_demand_summer_daily | Summer | highest demand inside part-peak hours | daily | 0.08 |
| peak_period_demand_winter_daily | Winter | highest demand inside peak hours | daily | 1.22 |

Each component is calculated in its own stated time scope; summer and winter components are mutually exclusive. Daily rates apply to each local day's applicable peak, while monthly rates apply once to the billing month's applicable peak.

### Export compensation

Export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Option S, mandatory-tier customer charge. Requires a storage system rated at least 10 percent of the account's peak demand over the previous twelve months, and is subject to an enrolment cap; neither condition is modelled. Secondary voltage, bundled service only. Not modelled: Primary and Transmission voltage classes, the power-factor adjustment, Peak Day Pricing, and Schedule SB standby charges. `previous_peak_kw` carryover applies only to the all-hours monthly maximum-demand component.

---

## PG&E B-20 Large General Demand-Metered TOU Service

- **Tariff id**: `pge_b20_secondary_bundled_2026_03_01`
- **Eligibility**: 1,000 kW or more
- **Service**: secondary voltage, bundled, commercial
- **Customer charge**: $107.36636 per meter per day (about $3,220.99 over 30 days)
- **Effective**: 2026-03-01 (version `2026-03-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-20.pdf>

### Energy rates

| Period | Season | Hours | $/kWh |
| --- | --- | --- | ---: |
| summer_peak | Summer | 16:00-21:00 | 0.17702 |
| summer_part_peak_afternoon | Summer | 14:00-16:00 | 0.14227 |
| summer_part_peak_evening | Summer | 21:00-23:00 | 0.14227 |
| summer_off_peak | Summer | all remaining hours | 0.11482 |
| winter_peak | Winter | 16:00-21:00 | 0.15632 |
| winter_super_off_peak | Winter | 09:00-14:00 (Mar, Apr, May only) | 0.05872 |
| winter_off_peak | Winter | all remaining hours | 0.11460 |

### Demand charges

| Component | Season | Measured over | Frequency | Rate ($/kW) |
| --- | --- | --- | --- | ---: |
| maximum_demand | All year | highest interval demand in the billing month | monthly | 39.08 |
| peak_period_demand_summer | Summer | highest demand inside peak hours | monthly | 41.35 |
| part_peak_period_demand_summer | Summer | highest demand inside part-peak hours | monthly | 9.27 |
| peak_period_demand_winter | Winter | highest demand inside peak hours | monthly | 2.32 |

Each component is calculated in its own stated time scope; summer and winter components are mutually exclusive. Daily rates apply to each local day's applicable peak, while monthly rates apply once to the billing month's applicable peak.

### Export compensation

B-20 export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Secondary voltage, bundled service only. Option R and Option S are registered separately as `pge_b20_secondary_option_r_bundled_2026_03_01` and `..._option_s_...`. Not modelled: Primary and Transmission voltage classes, the power-factor adjustment ($0.00005 per kWh per percent), Peak Day Pricing, Schedule SB standby charges, and the fuel-cell Generation Demand Adjustment. `previous_peak_kw` carryover applies only to the maximum-demand component -- the peak-period and part-peak-period components always start fresh from the supplied data.

---

## PG&E B-20 Option R (Renewables)

- **Tariff id**: `pge_b20_secondary_option_r_bundled_2026_03_01`
- **Eligibility**: B-20 accounts with renewables
- **Service**: secondary voltage, bundled, commercial
- **Customer charge**: $107.36636 per meter per day (about $3,220.99 over 30 days)
- **Effective**: 2026-03-01 (version `2026-03-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-20.pdf>

### Energy rates

| Period | Season | Hours | $/kWh |
| --- | --- | --- | ---: |
| summer_peak | Summer | 16:00-21:00 | 0.40620 |
| summer_part_peak_afternoon | Summer | 14:00-16:00 | 0.22337 |
| summer_part_peak_evening | Summer | 21:00-23:00 | 0.22337 |
| summer_off_peak | Summer | all remaining hours | 0.16434 |
| winter_peak | Winter | 16:00-21:00 | 0.17396 |
| winter_super_off_peak | Winter | 09:00-14:00 (Mar, Apr, May only) | 0.09448 |
| winter_off_peak | Winter | all remaining hours | 0.13023 |

### Demand charges

| Component | Season | Measured over | Frequency | Rate ($/kW) |
| --- | --- | --- | --- | ---: |
| maximum_demand | All year | highest interval demand in the billing month | monthly | 38.23 |
| peak_period_demand_summer | Summer | highest demand inside peak hours | monthly | 5.62 |
| part_peak_period_demand_summer | Summer | highest demand inside part-peak hours | monthly | 1.61 |

Each component is calculated in its own stated time scope; summer and winter components are mutually exclusive. Daily rates apply to each local day's applicable peak, while monthly rates apply once to the billing month's applicable peak.

### Export compensation

Export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Option R. Eligibility rules for Option R enrolment are not modelled. Secondary voltage, bundled service only. Not modelled: Primary and Transmission voltage classes, the power-factor adjustment, Peak Day Pricing, and Schedule SB standby charges. `previous_peak_kw` carryover applies only to the all-hours monthly maximum-demand component.

---

## PG&E B-20 Option S (Storage)

- **Tariff id**: `pge_b20_secondary_option_s_bundled_2026_03_01`
- **Eligibility**: B-20 accounts with storage
- **Service**: secondary voltage, bundled, commercial
- **Customer charge**: $107.36636 per meter per day (about $3,220.99 over 30 days)
- **Effective**: 2026-03-01 (version `2026-03-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-20.pdf>

### Energy rates

| Period | Season | Hours | $/kWh |
| --- | --- | --- | ---: |
| summer_peak | Summer | 16:00-21:00 | 0.40620 |
| summer_part_peak_afternoon | Summer | 14:00-16:00 | 0.22337 |
| summer_part_peak_evening | Summer | 21:00-23:00 | 0.22337 |
| summer_off_peak | Summer | all remaining hours | 0.16434 |
| winter_peak | Winter | 16:00-21:00 | 0.17396 |
| winter_super_off_peak | Winter | 09:00-14:00 (Mar, Apr, May only) | 0.09448 |
| winter_off_peak | Winter | all remaining hours | 0.13023 |

### Demand charges

| Component | Season | Measured over | Frequency | Rate ($/kW) |
| --- | --- | --- | --- | ---: |
| maximum_demand_excluding_09_to_14 | All year | highest interval demand in the billing month, excluding 09:00–14:00 local time | monthly | 5.56 |
| maximum_demand_all_hours | All year | highest interval demand in the billing month | monthly | 11.06 |
| peak_period_demand_summer_daily | Summer | highest demand inside peak hours | daily | 1.30 |
| part_peak_period_demand_summer_daily | Summer | highest demand inside part-peak hours | daily | 0.07 |
| peak_period_demand_winter_daily | Winter | highest demand inside peak hours | daily | 1.02 |

Each component is calculated in its own stated time scope; summer and winter components are mutually exclusive. Daily rates apply to each local day's applicable peak, while monthly rates apply once to the billing month's applicable peak.

### Export compensation

Export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Option S. Requires a storage system rated at least 10 percent of the account's peak demand over the previous twelve months, and is subject to an enrolment cap; neither condition is modelled. Secondary voltage, bundled service only. Not modelled: Primary and Transmission voltage classes, the power-factor adjustment, Peak Day Pricing, and Schedule SB standby charges. `previous_peak_kw` carryover applies only to the all-hours monthly maximum-demand component.

---

## PG&E E-TOU-D Residential TOU 5-8 p.m. (Income Tier 1)

- **Tariff id**: `pge_e_tou_d_residential_tier1_bundled_2026_06_01`
- **Eligibility**: Residential, opt-in; income tier 1 (CARE-level)
- **Service**: secondary voltage, bundled, residential
- **Customer charge**: $0.19713 per meter per day (about $5.91 over 30 days)
- **Effective**: 2026-06-01 (version `2026-06-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_E-TOU-D.pdf>

### Energy rates

| Period | Season | Hours | $/kWh |
| --- | --- | --- | ---: |
| summer_peak | Summer | 17:00-20:00, Mon-Fri | 0.47708 |
| summer_off_peak | Summer | all remaining hours | 0.34212 |
| winter_peak | Winter | 17:00-20:00, Mon-Fri | 0.38747 |
| winter_off_peak | Winter | all remaining hours | 0.34886 |

### Demand charges

None. This schedule bills energy and the customer charge only, so the bill never depends on the monthly peak.

### Export compensation

E-TOU-D export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Residential time-of-use, voluntary opt-in. Peak is 5-8 p.m. Monday through Friday; all other hours, weekends and holidays are off-peak. Holidays are NOT modelled -- a public holiday falling on a weekday is priced at the weekday peak rate, which overstates the bill for those few days. Also not modelled: the California Climate Credit ($36.18 per household, paid in the August and September bill cycles), CARE and FERA discounts, Standby Service under Schedule S, CCA and Direct Access.

---

## PG&E E-TOU-D Residential TOU 5-8 p.m. (Income Tier 2)

- **Tariff id**: `pge_e_tou_d_residential_tier2_bundled_2026_06_01`
- **Eligibility**: Residential, opt-in; income tier 2 (FERA-level)
- **Service**: secondary voltage, bundled, residential
- **Customer charge**: $0.39688 per meter per day (about $11.91 over 30 days)
- **Effective**: 2026-06-01 (version `2026-06-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_E-TOU-D.pdf>

### Energy rates

| Period | Season | Hours | $/kWh |
| --- | --- | --- | ---: |
| summer_peak | Summer | 17:00-20:00, Mon-Fri | 0.47708 |
| summer_off_peak | Summer | all remaining hours | 0.34212 |
| winter_peak | Winter | 17:00-20:00, Mon-Fri | 0.38747 |
| winter_off_peak | Winter | all remaining hours | 0.34886 |

### Demand charges

None. This schedule bills energy and the customer charge only, so the bill never depends on the monthly peak.

### Export compensation

E-TOU-D export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Residential time-of-use, voluntary opt-in. Peak is 5-8 p.m. Monday through Friday; all other hours, weekends and holidays are off-peak. Holidays are NOT modelled -- a public holiday falling on a weekday is priced at the weekday peak rate, which overstates the bill for those few days. Also not modelled: the California Climate Credit ($36.18 per household, paid in the August and September bill cycles), CARE and FERA discounts, Standby Service under Schedule S, CCA and Direct Access.

---

## PG&E E-TOU-D Residential TOU 5-8 p.m. (Income Tier 3)

- **Tariff id**: `pge_e_tou_d_residential_tier3_bundled_2026_06_01`
- **Eligibility**: Residential, opt-in; income tier 3 (all others)
- **Service**: secondary voltage, bundled, residential
- **Customer charge**: $0.79343 per meter per day (about $23.80 over 30 days)
- **Effective**: 2026-06-01 (version `2026-06-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_E-TOU-D.pdf>

### Energy rates

| Period | Season | Hours | $/kWh |
| --- | --- | --- | ---: |
| summer_peak | Summer | 17:00-20:00, Mon-Fri | 0.47708 |
| summer_off_peak | Summer | all remaining hours | 0.34212 |
| winter_peak | Winter | 17:00-20:00, Mon-Fri | 0.38747 |
| winter_off_peak | Winter | all remaining hours | 0.34886 |

### Demand charges

None. This schedule bills energy and the customer charge only, so the bill never depends on the monthly peak.

### Export compensation

E-TOU-D export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Residential time-of-use, voluntary opt-in. Peak is 5-8 p.m. Monday through Friday; all other hours, weekends and holidays are off-peak. Holidays are NOT modelled -- a public holiday falling on a weekday is priced at the weekday peak rate, which overstates the bill for those few days. Also not modelled: the California Climate Credit ($36.18 per household, paid in the August and September bill cycles), CARE and FERA discounts, Standby Service under Schedule S, CCA and Direct Access.

---

## PG&E E-1 Residential Tiered (Income Tier 1)

- **Tariff id**: `pge_e1_residential_tier1_bundled_2026_06_01`
- **Eligibility**: Residential default schedule; income tier 1 (CARE-level)
- **Service**: secondary voltage, bundled, residential
- **Customer charge**: $0.19713 per meter per day (about $5.91 over 30 days)
- **Effective**: 2026-06-01 (version `2026-06-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_E-1.pdf>

### Energy rates

Priced by **usage tier**, not by time of day. Tier boundaries are multiples of the baseline allowance, which for the default territory **T** (basic) is 6.5 kWh/day in summer and 7.5 kWh/day in winter. Each day of the billing period earns its own season's quantity.

| Tier | Usage range | $/kWh |
| --- | --- | ---: |
| tier_1_baseline | 0% - 100% of baseline | 0.32561 |
| tier_2_over_baseline | 100% - 400% of baseline | 0.40702 |
| tier_2_over_400_percent | over 400% of baseline | 0.40702 |

### Demand charges

None. This schedule bills energy and the customer charge only, so the bill never depends on the monthly peak.

### Export compensation

E-1 export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Residential service, tiered by usage against a baseline allowance; no time-of-use periods and no demand charge. Defaults to baseline territory T (basic) -- territory is a property of the premises, set by county and elevation, so pass an explicit BaselineAllowance when the site is elsewhere. Not modelled: the California Climate Credit ($36.18 per household, paid in the August and September bill cycles), CARE and FERA discounts, Standby Service under Schedule S, CCA and Direct Access.

---

## PG&E E-1 Residential Tiered (Income Tier 2)

- **Tariff id**: `pge_e1_residential_tier2_bundled_2026_06_01`
- **Eligibility**: Residential default schedule; income tier 2 (FERA-level)
- **Service**: secondary voltage, bundled, residential
- **Customer charge**: $0.39688 per meter per day (about $11.91 over 30 days)
- **Effective**: 2026-06-01 (version `2026-06-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_E-1.pdf>

### Energy rates

Priced by **usage tier**, not by time of day. Tier boundaries are multiples of the baseline allowance, which for the default territory **T** (basic) is 6.5 kWh/day in summer and 7.5 kWh/day in winter. Each day of the billing period earns its own season's quantity.

| Tier | Usage range | $/kWh |
| --- | --- | ---: |
| tier_1_baseline | 0% - 100% of baseline | 0.32561 |
| tier_2_over_baseline | 100% - 400% of baseline | 0.40702 |
| tier_2_over_400_percent | over 400% of baseline | 0.40702 |

### Demand charges

None. This schedule bills energy and the customer charge only, so the bill never depends on the monthly peak.

### Export compensation

E-1 export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Residential service, tiered by usage against a baseline allowance; no time-of-use periods and no demand charge. Defaults to baseline territory T (basic) -- territory is a property of the premises, set by county and elevation, so pass an explicit BaselineAllowance when the site is elsewhere. Not modelled: the California Climate Credit ($36.18 per household, paid in the August and September bill cycles), CARE and FERA discounts, Standby Service under Schedule S, CCA and Direct Access.

---

## PG&E E-1 Residential Tiered (Income Tier 3)

- **Tariff id**: `pge_e1_residential_tier3_bundled_2026_06_01`
- **Eligibility**: Residential default schedule; income tier 3 (all others)
- **Service**: secondary voltage, bundled, residential
- **Customer charge**: $0.79343 per meter per day (about $23.80 over 30 days)
- **Effective**: 2026-06-01 (version `2026-06-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_E-1.pdf>

### Energy rates

Priced by **usage tier**, not by time of day. Tier boundaries are multiples of the baseline allowance, which for the default territory **T** (basic) is 6.5 kWh/day in summer and 7.5 kWh/day in winter. Each day of the billing period earns its own season's quantity.

| Tier | Usage range | $/kWh |
| --- | --- | ---: |
| tier_1_baseline | 0% - 100% of baseline | 0.32561 |
| tier_2_over_baseline | 100% - 400% of baseline | 0.40702 |
| tier_2_over_400_percent | over 400% of baseline | 0.40702 |

### Demand charges

None. This schedule bills energy and the customer charge only, so the bill never depends on the monthly peak.

### Export compensation

E-1 export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Residential service, tiered by usage against a baseline allowance; no time-of-use periods and no demand charge. Defaults to baseline territory T (basic) -- territory is a property of the premises, set by county and elevation, so pass an explicit BaselineAllowance when the site is elsewhere. Not modelled: the California Climate Credit ($36.18 per household, paid in the August and September bill cycles), CARE and FERA discounts, Standby Service under Schedule S, CCA and Direct Access.

---

## PG&E E-ELEC Residential Electric Home (Income Tier 1)

- **Tariff id**: `pge_e_elec_residential_tier1_bundled_2026_06_01`
- **Eligibility**: Electrified home, opt-in; income tier 1 (CARE-level)
- **Service**: secondary voltage, bundled, residential
- **Customer charge**: $0.19713 per meter per day (about $5.91 over 30 days)
- **Effective**: 2026-06-01 (version `2026-06-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_E-ELEC.pdf>

### Energy rates

| Period | Season | Hours | $/kWh |
| --- | --- | --- | ---: |
| summer_peak | Summer | 16:00-21:00 | 0.55214 |
| summer_part_peak_afternoon | Summer | 15:00-16:00 | 0.39026 |
| summer_part_peak_evening | Summer | 21:00-24:00 | 0.39026 |
| summer_off_peak | Summer | all remaining hours | 0.33358 |
| winter_peak | Winter | 16:00-21:00 | 0.32063 |
| winter_part_peak_afternoon | Winter | 15:00-16:00 | 0.29854 |
| winter_part_peak_evening | Winter | 21:00-24:00 | 0.29854 |
| winter_off_peak | Winter | all remaining hours | 0.28468 |

### Demand charges

None. This schedule bills energy and the customer charge only, so the bill never depends on the monthly peak.

### Export compensation

Export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Residential time-of-use for an electrified home; requires a qualifying electric technology (heat pump space or water heating, or an electric vehicle). Peak is 4-9 p.m. every day, including weekends and holidays, so no day-of-week restriction applies. No baseline tiers and no demand charge. Not modelled: the qualifying-technology eligibility test itself, the California Climate Credit ($36.18 per household, paid in the August and September bill cycles), CARE and FERA discounts, Standby Service under Schedule S, CCA and Direct Access.

---

## PG&E E-ELEC Residential Electric Home (Income Tier 2)

- **Tariff id**: `pge_e_elec_residential_tier2_bundled_2026_06_01`
- **Eligibility**: Electrified home, opt-in; income tier 2 (FERA-level)
- **Service**: secondary voltage, bundled, residential
- **Customer charge**: $0.39688 per meter per day (about $11.91 over 30 days)
- **Effective**: 2026-06-01 (version `2026-06-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_E-ELEC.pdf>

### Energy rates

| Period | Season | Hours | $/kWh |
| --- | --- | --- | ---: |
| summer_peak | Summer | 16:00-21:00 | 0.55214 |
| summer_part_peak_afternoon | Summer | 15:00-16:00 | 0.39026 |
| summer_part_peak_evening | Summer | 21:00-24:00 | 0.39026 |
| summer_off_peak | Summer | all remaining hours | 0.33358 |
| winter_peak | Winter | 16:00-21:00 | 0.32063 |
| winter_part_peak_afternoon | Winter | 15:00-16:00 | 0.29854 |
| winter_part_peak_evening | Winter | 21:00-24:00 | 0.29854 |
| winter_off_peak | Winter | all remaining hours | 0.28468 |

### Demand charges

None. This schedule bills energy and the customer charge only, so the bill never depends on the monthly peak.

### Export compensation

Export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Residential time-of-use for an electrified home; requires a qualifying electric technology (heat pump space or water heating, or an electric vehicle). Peak is 4-9 p.m. every day, including weekends and holidays, so no day-of-week restriction applies. No baseline tiers and no demand charge. Not modelled: the qualifying-technology eligibility test itself, the California Climate Credit ($36.18 per household, paid in the August and September bill cycles), CARE and FERA discounts, Standby Service under Schedule S, CCA and Direct Access.

---

## PG&E E-ELEC Residential Electric Home (Income Tier 3)

- **Tariff id**: `pge_e_elec_residential_tier3_bundled_2026_06_01`
- **Eligibility**: Electrified home, opt-in; income tier 3 (all others)
- **Service**: secondary voltage, bundled, residential
- **Customer charge**: $0.79343 per meter per day (about $23.80 over 30 days)
- **Effective**: 2026-06-01 (version `2026-06-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_E-ELEC.pdf>

### Energy rates

| Period | Season | Hours | $/kWh |
| --- | --- | --- | ---: |
| summer_peak | Summer | 16:00-21:00 | 0.55214 |
| summer_part_peak_afternoon | Summer | 15:00-16:00 | 0.39026 |
| summer_part_peak_evening | Summer | 21:00-24:00 | 0.39026 |
| summer_off_peak | Summer | all remaining hours | 0.33358 |
| winter_peak | Winter | 16:00-21:00 | 0.32063 |
| winter_part_peak_afternoon | Winter | 15:00-16:00 | 0.29854 |
| winter_part_peak_evening | Winter | 21:00-24:00 | 0.29854 |
| winter_off_peak | Winter | all remaining hours | 0.28468 |

### Demand charges

None. This schedule bills energy and the customer charge only, so the bill never depends on the monthly peak.

### Export compensation

Export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Residential time-of-use for an electrified home; requires a qualifying electric technology (heat pump space or water heating, or an electric vehicle). Peak is 4-9 p.m. every day, including weekends and holidays, so no day-of-week restriction applies. No baseline tiers and no demand charge. Not modelled: the qualifying-technology eligibility test itself, the California Climate Credit ($36.18 per household, paid in the August and September bill cycles), CARE and FERA discounts, Standby Service under Schedule S, CCA and Direct Access.

---

## PG&E EV2-A Residential Electric Vehicle (Income Tier 1)

- **Tariff id**: `pge_ev2_residential_tier1_bundled_2026_06_01`
- **Eligibility**: Household with an EV; income tier 1 (CARE-level)
- **Service**: secondary voltage, bundled, residential
- **Customer charge**: $0.19713 per meter per day (about $5.91 over 30 days)
- **Effective**: 2026-06-01 (version `2026-06-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_EV2%20(Sch).pdf>

### Energy rates

| Period | Season | Hours | $/kWh |
| --- | --- | --- | ---: |
| summer_peak | Summer | 16:00-21:00 | 0.53809 |
| summer_part_peak_afternoon | Summer | 15:00-16:00 | 0.42760 |
| summer_part_peak_evening | Summer | 21:00-24:00 | 0.42760 |
| summer_off_peak | Summer | all remaining hours | 0.22558 |
| winter_peak | Winter | 16:00-21:00 | 0.41099 |
| winter_part_peak_afternoon | Winter | 15:00-16:00 | 0.39428 |
| winter_part_peak_evening | Winter | 21:00-24:00 | 0.39428 |
| winter_off_peak | Winter | all remaining hours | 0.22558 |

### Demand charges

None. This schedule bills energy and the customer charge only, so the bill never depends on the monthly peak.

### Export compensation

Export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Residential time-of-use for a household with a plug-in electric vehicle (PG&E Schedule EV2, rate option A). Same period structure as E-ELEC -- 4-9 p.m. peak every day including weekends and holidays -- but a far cheaper off-peak, which is the whole point: it prices overnight charging at $0.22558/kWh in both seasons. No baseline tiers and no demand charge. Not modelled: the EV-ownership eligibility test, the California Climate Credit, CARE and FERA discounts, Standby Service under Schedule S, CCA and Direct Access.

---

## PG&E EV2-A Residential Electric Vehicle (Income Tier 2)

- **Tariff id**: `pge_ev2_residential_tier2_bundled_2026_06_01`
- **Eligibility**: Household with an EV; income tier 2 (FERA-level)
- **Service**: secondary voltage, bundled, residential
- **Customer charge**: $0.39688 per meter per day (about $11.91 over 30 days)
- **Effective**: 2026-06-01 (version `2026-06-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_EV2%20(Sch).pdf>

### Energy rates

| Period | Season | Hours | $/kWh |
| --- | --- | --- | ---: |
| summer_peak | Summer | 16:00-21:00 | 0.53809 |
| summer_part_peak_afternoon | Summer | 15:00-16:00 | 0.42760 |
| summer_part_peak_evening | Summer | 21:00-24:00 | 0.42760 |
| summer_off_peak | Summer | all remaining hours | 0.22558 |
| winter_peak | Winter | 16:00-21:00 | 0.41099 |
| winter_part_peak_afternoon | Winter | 15:00-16:00 | 0.39428 |
| winter_part_peak_evening | Winter | 21:00-24:00 | 0.39428 |
| winter_off_peak | Winter | all remaining hours | 0.22558 |

### Demand charges

None. This schedule bills energy and the customer charge only, so the bill never depends on the monthly peak.

### Export compensation

Export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Residential time-of-use for a household with a plug-in electric vehicle (PG&E Schedule EV2, rate option A). Same period structure as E-ELEC -- 4-9 p.m. peak every day including weekends and holidays -- but a far cheaper off-peak, which is the whole point: it prices overnight charging at $0.22558/kWh in both seasons. No baseline tiers and no demand charge. Not modelled: the EV-ownership eligibility test, the California Climate Credit, CARE and FERA discounts, Standby Service under Schedule S, CCA and Direct Access.

---

## PG&E EV2-A Residential Electric Vehicle (Income Tier 3)

- **Tariff id**: `pge_ev2_residential_tier3_bundled_2026_06_01`
- **Eligibility**: Household with an EV; income tier 3 (all others)
- **Service**: secondary voltage, bundled, residential
- **Customer charge**: $0.79343 per meter per day (about $23.80 over 30 days)
- **Effective**: 2026-06-01 (version `2026-06-01`)
- **Source**: <https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_EV2%20(Sch).pdf>

### Energy rates

| Period | Season | Hours | $/kWh |
| --- | --- | --- | ---: |
| summer_peak | Summer | 16:00-21:00 | 0.53809 |
| summer_part_peak_afternoon | Summer | 15:00-16:00 | 0.42760 |
| summer_part_peak_evening | Summer | 21:00-24:00 | 0.42760 |
| summer_off_peak | Summer | all remaining hours | 0.22558 |
| winter_peak | Winter | 16:00-21:00 | 0.41099 |
| winter_part_peak_afternoon | Winter | 15:00-16:00 | 0.39428 |
| winter_part_peak_evening | Winter | 21:00-24:00 | 0.39428 |
| winter_off_peak | Winter | all remaining hours | 0.22558 |

### Demand charges

None. This schedule bills energy and the customer charge only, so the bill never depends on the monthly peak.

### Export compensation

Export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Residential time-of-use for a household with a plug-in electric vehicle (PG&E Schedule EV2, rate option A). Same period structure as E-ELEC -- 4-9 p.m. peak every day including weekends and holidays -- but a far cheaper off-peak, which is the whole point: it prices overnight charging at $0.22558/kWh in both seasons. No baseline tiers and no demand charge. Not modelled: the EV-ownership eligibility test, the California Climate Credit, CARE and FERA discounts, Standby Service under Schedule S, CCA and Direct Access.

---

## Rate history

Superseded versions, kept so a study of a past year stays reproducible. A simulation selects the version effective on each local service date; see `src/billing/plans.py`.

| Version | Schedule | Effective | Tier 1 $/kWh | Tier 2 $/kWh | Fixed provision |
| --- | --- | --- | ---: | ---: | --- |
| `2025-09-01` | PG&E B-6 Small General Time-of-Use Service (Single-Phase) | 2025-09-01 to 2025-12-31 | — | — | customer charge $0.32854/day |
| `2025-09-01` | PG&E B-6 Small General Time-of-Use Service (Polyphase) | 2025-09-01 to 2025-12-31 | — | — | customer charge $0.82136/day |
| `2024-01-01` | E-1 | 2024-01-01 to 2024-02-29 | 0.42009 | 0.52566 | minimum bill $0.37612/day |
| `2024-03-01` | E-1 | 2024-03-01 to 2024-03-31 | 0.42101 | 0.52708 | minimum bill $0.39167/day |
| `2024-04-01` | E-1 | 2024-04-01 to 2024-05-31 | 0.42676 | 0.53406 | minimum bill $0.39167/day |
| `2024-06-01` | E-1 | 2024-06-01 to 2024-06-30 | 0.42676 | 0.53406 | minimum bill $0.39167/day |
| `2024-07-01` | E-1 | 2024-07-01 to 2024-08-31 | 0.38828 | 0.48617 | minimum bill $0.39167/day |
| `2024-09-01` | E-1 | 2024-09-01 to 2024-09-30 | 0.39033 | 0.48870 | minimum bill $0.39167/day |
| `2024-10-01` | E-1 | 2024-10-01 to 2024-12-31 | 0.40206 | 0.50323 | minimum bill $0.39167/day |
| `2025-01-01` | E-1 | 2025-01-01 to 2025-02-28 | 0.40122 | 0.50257 | minimum bill $0.39167/day |
| `2025-03-01` | E-1 | 2025-03-01 to 2025-08-31 | 0.40730 | 0.51031 | minimum bill $0.40317/day |
| `2025-09-01` | E-1 | 2025-09-01 to 2025-12-31 | 0.39834 | 0.49918 | minimum bill $0.40317/day |
| `2026-01-01` | E-1 | 2026-01-01 to 2026-02-28 | 0.37839 | 0.47405 | minimum bill $0.40317/day |
| `2024-01-01` | PG&E E-ELEC Residential Electric Home (2024-01-01 to 2024-02-29) | 2024-01-01 to 2024-02-29 | — | — | customer charge $0.49281/day |
| `2024-03-01` | PG&E E-ELEC Residential Electric Home (2024-03-01 to 2024-03-31) | 2024-03-01 to 2024-03-31 | — | — | customer charge $0.49281/day |
| `2024-04-01` | PG&E E-ELEC Residential Electric Home (2024-04-01 to 2024-05-31) | 2024-04-01 to 2024-05-31 | — | — | customer charge $0.49281/day |
| `2024-06-01` | PG&E E-ELEC Residential Electric Home (2024-06-01 to 2024-06-30) | 2024-06-01 to 2024-06-30 | — | — | customer charge $0.49281/day |
| `2024-07-01` | PG&E E-ELEC Residential Electric Home (2024-07-01 to 2024-08-31) | 2024-07-01 to 2024-08-31 | — | — | customer charge $0.49281/day |
| `2024-09-01` | PG&E E-ELEC Residential Electric Home (2024-09-01 to 2024-09-30) | 2024-09-01 to 2024-09-30 | — | — | customer charge $0.49281/day |
| `2024-10-01` | PG&E E-ELEC Residential Electric Home (2024-10-01 to 2024-12-31) | 2024-10-01 to 2024-12-31 | — | — | customer charge $0.49281/day |
| `2025-01-01` | PG&E E-ELEC Residential Electric Home (2025-01-01 to 2025-02-28) | 2025-01-01 to 2025-02-28 | — | — | customer charge $0.49281/day |
| `2025-03-01` | PG&E E-ELEC Residential Electric Home (2025-03-01 to 2025-08-31) | 2025-03-01 to 2025-08-31 | — | — | customer charge $0.49281/day |
| `2025-09-01` | PG&E E-ELEC Residential Electric Home (2025-09-01 to 2025-12-31) | 2025-09-01 to 2025-12-31 | — | — | customer charge $0.49281/day |
| `2026-01-01` | PG&E E-ELEC Residential Electric Home (2026-01-01 to 2026-02-28) | 2026-01-01 to 2026-02-28 | — | — | customer charge $0.49281/day |
| `2024-01-01` | PG&E E-TOU-D Residential TOU 5-8 p.m. (2024-01-01 to 2024-02-29) | 2024-01-01 to 2024-02-29 | — | — | minimum bill $0.37612/day |
| `2024-03-01` | PG&E E-TOU-D Residential TOU 5-8 p.m. (2024-03-01 to 2024-03-31) | 2024-03-01 to 2024-03-31 | — | — | minimum bill $0.39167/day |
| `2024-04-01` | PG&E E-TOU-D Residential TOU 5-8 p.m. (2024-04-01 to 2024-05-31) | 2024-04-01 to 2024-05-31 | — | — | minimum bill $0.39167/day |
| `2024-06-01` | PG&E E-TOU-D Residential TOU 5-8 p.m. (2024-06-01 to 2024-06-30) | 2024-06-01 to 2024-06-30 | — | — | minimum bill $0.39167/day |
| `2024-07-01` | PG&E E-TOU-D Residential TOU 5-8 p.m. (2024-07-01 to 2024-08-31) | 2024-07-01 to 2024-08-31 | — | — | minimum bill $0.39167/day |
| `2024-09-01` | PG&E E-TOU-D Residential TOU 5-8 p.m. (2024-09-01 to 2024-09-30) | 2024-09-01 to 2024-09-30 | — | — | minimum bill $0.39167/day |
| `2024-10-01` | PG&E E-TOU-D Residential TOU 5-8 p.m. (2024-10-01 to 2024-12-31) | 2024-10-01 to 2024-12-31 | — | — | minimum bill $0.39167/day |
| `2025-01-01` | PG&E E-TOU-D Residential TOU 5-8 p.m. (2025-01-01 to 2025-02-28) | 2025-01-01 to 2025-02-28 | — | — | minimum bill $0.39167/day |
| `2025-03-01` | PG&E E-TOU-D Residential TOU 5-8 p.m. (2025-03-01 to 2025-08-31) | 2025-03-01 to 2025-08-31 | — | — | minimum bill $0.40317/day |
| `2025-09-01` | PG&E E-TOU-D Residential TOU 5-8 p.m. (2025-09-01 to 2025-12-31) | 2025-09-01 to 2025-12-31 | — | — | minimum bill $0.40317/day |
| `2026-01-01` | PG&E E-TOU-D Residential TOU 5-8 p.m. (2026-01-01 to 2026-02-28) | 2026-01-01 to 2026-02-28 | — | — | minimum bill $0.40317/day |
| `2024-01-01` | PG&E EV2-A Residential EV (2024-01-01 to 2024-02-29) | 2024-01-01 to 2024-02-29 | — | — | minimum bill $0.37612/day |
| `2024-03-01` | PG&E EV2-A Residential EV (2024-03-01 to 2024-03-31) | 2024-03-01 to 2024-03-31 | — | — | minimum bill $0.39167/day |
| `2024-04-01` | PG&E EV2-A Residential EV (2024-04-01 to 2024-05-31) | 2024-04-01 to 2024-05-31 | — | — | minimum bill $0.39167/day |
| `2024-06-01` | PG&E EV2-A Residential EV (2024-06-01 to 2024-06-30) | 2024-06-01 to 2024-06-30 | — | — | minimum bill $0.39167/day |
| `2024-07-01` | PG&E EV2-A Residential EV (2024-07-01 to 2024-08-31) | 2024-07-01 to 2024-08-31 | — | — | minimum bill $0.39167/day |
| `2024-09-01` | PG&E EV2-A Residential EV (2024-09-01 to 2024-09-30) | 2024-09-01 to 2024-09-30 | — | — | minimum bill $0.39167/day |
| `2024-10-01` | PG&E EV2-A Residential EV (2024-10-01 to 2024-12-31) | 2024-10-01 to 2024-12-31 | — | — | minimum bill $0.39167/day |
| `2025-01-01` | PG&E EV2-A Residential EV (2025-01-01 to 2025-02-28) | 2025-01-01 to 2025-02-28 | — | — | minimum bill $0.39167/day |
| `2025-03-01` | PG&E EV2-A Residential EV (2025-03-01 to 2025-08-31) | 2025-03-01 to 2025-08-31 | — | — | minimum bill $0.40317/day |
| `2025-09-01` | PG&E EV2-A Residential EV (2025-09-01 to 2025-12-31) | 2025-09-01 to 2025-12-31 | — | — | minimum bill $0.40317/day |
| `2026-01-01` | PG&E EV2-A Residential EV (2026-01-01 to 2026-02-28) | 2026-01-01 to 2026-02-28 | — | — | minimum bill $0.40317/day |

---

## Not modelled

| Schedule | Why |
| --- | --- |
| B1-ST (B-1 storage option) | Its $7.86/kW demand charge is assessed 2:00 p.m.-11:00 p.m. only — the union of B-1's peak and part-peak blocks. `DemandChargeComponent` has no windowed basis, and modelling it as two components would take each maximum separately and sum them, overcharging. |
| Primary and Transmission voltage classes | Rates are published for all three classes, but the modelled 480 V service is secondary. |
| Agricultural schedules (AG-A1, AG-A2, AG-B, AG-C) | Keyed to annual operating hours, with flex-day options tied to specific weekdays. `TOUPeriod` has no day-of-week field. |
| Peak Day Pricing | Event-driven, priced at $0.60-$0.90/kWh during events against a summer peak credit. Needs PG&E's event calendar. |
| Export compensation (NEM, NBT) | Not part of any of these rate schedules. Configure a fixed or CSV export price in the surplus configuration instead. |

