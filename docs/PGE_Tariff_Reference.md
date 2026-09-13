# PG&E tariff reference

**Generated file — do not edit by hand.** Regenerate with:

```bash
/usr/local/bin/python3 tools/generate_tariff_reference.py
```

Every rate below is read from the tariff registry in `src/billing/pge_tariffs.py`, so this document and the numbers the billing code applies cannot disagree. Rates are transcribed from PG&E's published tariff sheets and are valid for the stated effective date only; see [Microgrid_Backend_Architecture.md](Microgrid_Backend_Architecture.md) for why tariffs are versioned data rather than editable constants.

All schedules below are **secondary voltage, bundled service**. Primary and Transmission voltage classes, Peak Day Pricing, power-factor adjustments and standby charges are not modelled.

## How the plans compare

The families form a progression: as an account grows, the fixed and demand charges rise while the energy spread narrows. A battery earns its value from the energy spread on the small schedules and from peak reduction on the large ones.

Spread is summer peak minus summer off-peak — the per-kWh margin a battery captures by shifting one kilowatt-hour out of the peak window. It is the only derived figure in these tables; every other number is read straight from the registry. Winter rates and the part-peak blocks are in the next table.

### Charges at a glance

| Schedule | Eligibility | Customer $/day | Demand $/kW | Summer peak $/kWh | Summer off-peak $/kWh | Summer spread $/kWh |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| PG&E B-1 Small General Service (Single-Phase) | Under 75 kW | 0.32854 | 0.00 | 0.47087 | 0.40083 | 0.07004 |
| PG&E B-1 Small General Service (Polyphase) | Under 75 kW | 0.82136 | 0.00 | 0.47087 | 0.40083 | 0.07004 |
| PG&E B-6 Small General Time-of-Use Service (Single-Phase) | Under 75 kW | 0.32854 | 0.00 | 0.64253 | 0.38491 | 0.25762 |
| PG&E B-6 Small General Time-of-Use Service (Polyphase) | Under 75 kW | 0.82136 | 0.00 | 0.64253 | 0.38491 | 0.25762 |
| PG&E B-10 Medium General Demand-Metered Service | 75-499 kW (voluntary below 75 kW) | 11.36882 | 20.50 | 0.33947 | 0.24522 | 0.09425 |
| PG&E B-19 Medium General Demand-Metered TOU Service (Mandatory) | 500-999 kW | 58.62824 | 96.36 | 0.18648 | 0.12037 | 0.06611 |
| PG&E B-19 Medium General Demand-Metered TOU Service (Voluntary) | Opt-in below 500 kW | 11.36882 | 96.36 | 0.18648 | 0.12037 | 0.06611 |
| PG&E B-19 Option R (Renewables), Mandatory Tier | B-19 accounts with renewables | 58.62824 | 44.98 | 0.43568 | 0.19137 | 0.24431 |
| PG&E B-19 Option S (Storage), Mandatory Tier | B-19 accounts with storage | 58.62824 | 18.38 | 0.43568 | 0.19137 | 0.24431 |
| PG&E B-20 Large General Demand-Metered TOU Service | 1,000 kW or more | 107.36636 | 92.02 | 0.17702 | 0.11482 | 0.06220 |
| PG&E B-20 Option R (Renewables) | B-20 accounts with renewables | 107.36636 | 45.46 | 0.40620 | 0.16434 | 0.24186 |
| PG&E B-20 Option S (Storage) | B-20 accounts with storage | 107.36636 | 19.01 | 0.40620 | 0.16434 | 0.24186 |

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

### Demand charges side by side ($/kW)

Components apply together, so a summer peak-hour kilowatt on B-19 or B-20 can attract three of them at once. A dash means the schedule does not bill that component; both Option R schedules price winter peak-period demand at zero.

| Schedule | Maximum | Summer peak-period | Summer part-peak-period | Winter peak-period | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| B-1 single-phase | — | — | — | — | **0.00** |
| B-1 polyphase | — | — | — | — | **0.00** |
| B-6 single-phase | — | — | — | — | **0.00** |
| B-6 polyphase | — | — | — | — | **0.00** |
| B-10 | 20.50 | — | — | — | **20.50** |
| B-19 mandatory | 37.37 | 46.16 | 10.52 | 2.31 | **96.36** |
| B-19 voluntary | 37.37 | 46.16 | 10.52 | 2.31 | **96.36** |
| B-19 Option R | 36.61 | 6.50 | 1.87 | — | **44.98** |
| B-19 Option S | 15.48 | 1.60 | 0.08 | 1.22 | **18.38** |
| B-20 | 39.08 | 41.35 | 9.27 | 2.32 | **92.02** |
| B-20 Option R | 38.23 | 5.62 | 1.61 | — | **45.46** |
| B-20 Option S | 16.62 | 1.30 | 0.07 | 1.02 | **19.01** |

Seasons are the same on every schedule: **summer is June 1 through September 30**, winter is October 1 through May 31. Every period applies *every day, including weekends and holidays* — none of these schedules distinguishes weekdays.

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

| Component | Season | Measured over | $/kW |
| --- | --- | --- | ---: |
| maximum_demand | All year | highest interval demand in the billing month | 20.50 |
| **Total if every component peaks together** | | | **20.50** |

Components apply together on the same bill. A summer peak-hour kilowatt can attract the maximum-demand, peak-period and part-peak-period charges at once.

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

| Component | Season | Measured over | $/kW |
| --- | --- | --- | ---: |
| maximum_demand | All year | highest interval demand in the billing month | 37.37 |
| peak_period_demand_summer | Summer | highest demand inside peak hours | 46.16 |
| part_peak_period_demand_summer | Summer | highest demand inside part-peak hours | 10.52 |
| peak_period_demand_winter | Winter | highest demand inside peak hours | 2.31 |
| **Total if every component peaks together** | | | **96.36** |

Components apply together on the same bill. A summer peak-hour kilowatt can attract the maximum-demand, peak-period and part-peak-period charges at once.

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

| Component | Season | Measured over | $/kW |
| --- | --- | --- | ---: |
| maximum_demand | All year | highest interval demand in the billing month | 37.37 |
| peak_period_demand_summer | Summer | highest demand inside peak hours | 46.16 |
| part_peak_period_demand_summer | Summer | highest demand inside part-peak hours | 10.52 |
| peak_period_demand_winter | Winter | highest demand inside peak hours | 2.31 |
| **Total if every component peaks together** | | | **96.36** |

Components apply together on the same bill. A summer peak-hour kilowatt can attract the maximum-demand, peak-period and part-peak-period charges at once.

### Export compensation

Export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Voluntary tier: identical rates to Mandatory B-19 apart from the customer charge ($11.36882 rather than $58.62824 per day). Secondary voltage, bundled service only. Not modelled: Primary and Transmission voltage classes, the power-factor adjustment, Peak Day Pricing, and Schedule SB standby charges. `previous_peak_kw` carryover applies only to the maximum-demand component.

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

| Component | Season | Measured over | $/kW |
| --- | --- | --- | ---: |
| maximum_demand | All year | highest interval demand in the billing month | 36.61 |
| peak_period_demand_summer | Summer | highest demand inside peak hours | 6.50 |
| part_peak_period_demand_summer | Summer | highest demand inside part-peak hours | 1.87 |
| **Total if every component peaks together** | | | **44.98** |

Components apply together on the same bill. A summer peak-hour kilowatt can attract the maximum-demand, peak-period and part-peak-period charges at once.

### Export compensation

Export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Option R, mandatory-tier customer charge. Eligibility rules for Option R enrolment are not modelled. Secondary voltage, bundled service only. Not modelled: Primary and Transmission voltage classes, the power-factor adjustment, Peak Day Pricing, and Schedule SB standby charges. `previous_peak_kw` carryover applies only to the maximum-demand component.

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

| Component | Season | Measured over | $/kW |
| --- | --- | --- | ---: |
| maximum_demand | All year | highest interval demand in the billing month | 15.48 |
| peak_period_demand_summer | Summer | highest demand inside peak hours | 1.60 |
| part_peak_period_demand_summer | Summer | highest demand inside part-peak hours | 0.08 |
| peak_period_demand_winter | Winter | highest demand inside peak hours | 1.22 |
| **Total if every component peaks together** | | | **18.38** |

Components apply together on the same bill. A summer peak-hour kilowatt can attract the maximum-demand, peak-period and part-peak-period charges at once.

### Export compensation

Export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Option S, mandatory-tier customer charge. Requires a storage system rated at least 10 percent of the account's peak demand over the previous twelve months, and is subject to an enrolment cap; neither condition is modelled. Secondary voltage, bundled service only. Not modelled: Primary and Transmission voltage classes, the power-factor adjustment, Peak Day Pricing, and Schedule SB standby charges. `previous_peak_kw` carryover applies only to the maximum-demand component.

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

| Component | Season | Measured over | $/kW |
| --- | --- | --- | ---: |
| maximum_demand | All year | highest interval demand in the billing month | 39.08 |
| peak_period_demand_summer | Summer | highest demand inside peak hours | 41.35 |
| part_peak_period_demand_summer | Summer | highest demand inside part-peak hours | 9.27 |
| peak_period_demand_winter | Winter | highest demand inside peak hours | 2.32 |
| **Total if every component peaks together** | | | **92.02** |

Components apply together on the same bill. A summer peak-hour kilowatt can attract the maximum-demand, peak-period and part-peak-period charges at once.

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

| Component | Season | Measured over | $/kW |
| --- | --- | --- | ---: |
| maximum_demand | All year | highest interval demand in the billing month | 38.23 |
| peak_period_demand_summer | Summer | highest demand inside peak hours | 5.62 |
| part_peak_period_demand_summer | Summer | highest demand inside part-peak hours | 1.61 |
| **Total if every component peaks together** | | | **45.46** |

Components apply together on the same bill. A summer peak-hour kilowatt can attract the maximum-demand, peak-period and part-peak-period charges at once.

### Export compensation

Export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Option R. Eligibility rules for Option R enrolment are not modelled. Secondary voltage, bundled service only. Not modelled: Primary and Transmission voltage classes, the power-factor adjustment, Peak Day Pricing, and Schedule SB standby charges. `previous_peak_kw` carryover applies only to the maximum-demand component.

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

| Component | Season | Measured over | $/kW |
| --- | --- | --- | ---: |
| maximum_demand | All year | highest interval demand in the billing month | 16.62 |
| peak_period_demand_summer | Summer | highest demand inside peak hours | 1.30 |
| part_peak_period_demand_summer | Summer | highest demand inside part-peak hours | 0.07 |
| peak_period_demand_winter | Winter | highest demand inside peak hours | 1.02 |
| **Total if every component peaks together** | | | **19.01** |

Components apply together on the same bill. A summer peak-hour kilowatt can attract the maximum-demand, peak-period and part-peak-period charges at once.

### Export compensation

Export compensation (NEM or the Net Billing Tariff) is not modelled. Configure an explicit fixed or CSV export price in the surplus configuration instead.

### Notes

Option S. Requires a storage system rated at least 10 percent of the account's peak demand over the previous twelve months, and is subject to an enrolment cap; neither condition is modelled. Secondary voltage, bundled service only. Not modelled: Primary and Transmission voltage classes, the power-factor adjustment, Peak Day Pricing, and Schedule SB standby charges. `previous_peak_kw` carryover applies only to the maximum-demand component.

---

## Not modelled

| Schedule | Why |
| --- | --- |
| B1-ST (B-1 storage option) | Its $7.86/kW demand charge is assessed 2:00 p.m.-11:00 p.m. only — the union of B-1's peak and part-peak blocks. `DemandChargeComponent` has no windowed basis, and modelling it as two components would take each maximum separately and sum them, overcharging. |
| Primary and Transmission voltage classes | Rates are published for all three classes, but the modelled 480 V service is secondary. |
| Agricultural schedules (AG-A1, AG-A2, AG-B, AG-C) | Keyed to annual operating hours, with flex-day options tied to specific weekdays. `TOUPeriod` has no day-of-week field. |
| Peak Day Pricing | Event-driven, priced at $0.60-$0.90/kWh during events against a summer peak credit. Needs PG&E's event calendar. |
| Export compensation (NEM, NBT) | Not part of any of these rate schedules. Configure a fixed or CSV export price in the surplus configuration instead. |

