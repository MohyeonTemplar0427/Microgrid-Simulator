# Fresno benchmark reconciliation and expanded sample

## Sample expansion

The design was fixed at 256 models before examining their annual energy.
It uses the same seed, dwelling-type/cooling strata and expansion-weight rule
as the 64-model pilot. It is a new stratified draw, not a nested extension.

| Models | Annual kWh per represented housing unit | Difference from all 1,328 models | Estimated sampling SE, kWh |
|---|---:|---:|---:|
| 64 | 9099.4 | -10.07% | 532.4 |
| 256 | 9749.1 | -3.65% | 263.6 |

The SE describes annual-energy sampling uncertainty, not weather-response,
peak-load or building-model uncertainty. These profiles represent all housing
units, including vacant units; “per home” does not mean per occupied household.

## Local benchmark accounting

CEC reports **2,655.4 GWh** for Fresno residential consumption in
2018 and **3,133.4 GWh** in 2024. Compare the 2018 stock/weather
model with 2018; the 2024 county total is context, not a target for fixed-2018
stock scenarios. Customer growth, electrification and equipment changes are
not weather effects.

| Full county model basis | Modeled 2018 GWh | CEC / model ratio (diagnostic only) |
|---|---:|---:|
| Gross demand before PV | 3,411.6 | 0.7783 |
| Signed net after modeled PV | 3,142.9 | 0.8449 |

[CEC documentation](https://www.energy.ca.gov/data-reports/energy-almanac/california-electricity-data/california-energy-consumption-dashboards-0) defines total consumption as retail sales,
non-retail consumption and self-generation, while its QFER sales component is
net of PV. The downloaded county workbook has only sector/month/GWh fields;
it does not separately identify residential self-generation or PV exports.
**Do not automatically add rooftop PV to this consumption total.** Equally,
the label alone does not establish which distributed-generation components
are included in each county/sector row. The two model bases above expose the
sensitivity; they are not asserted to bracket a known ground truth.

Signed net demand is not purchased electricity: annual PV subtraction includes
exports, while positive grid imports require interval-level accounting.
No CEC-to-model ratio above has been applied to the hourly profiles.

## Housing denominator

[California EDD's Census DP04 reproduction](https://labormarketinfo.edd.ca.gov/file/Census2018/fresndp2018.pdf), page 6, reports
**328,577 total housing units**, **304,624 occupied** and **23,953 vacant** for
2014–2018. ResStock weights represent **337,184 total units**,
including **23,359 vacant**. The total-count difference
is **+2.62%**. This is a
five-year estimate, not a single-year account count. It cannot be substituted
silently for 2018 utility customers.

As a denominator sensitivity only, gross model energy at the ACS total housing
count would be **3,324.6 GWh**.
Changing housing count alone does not remove the consumption discrepancy.
Dividing the whole county energy total by occupied households would also
attribute vacant-unit consumption to occupied households.

## Calibration decision

**Retain uncalibrated profiles.** The larger sample addresses sampling error;
it does not resolve the remaining difference from local consumption statistics.
Before setting absolute regional demand, confirm the county residential export's
self-generation/PV accounting and obtain a matched-year housing stock or a
meter-to-dwelling mapping. Then align the model's gross or grid-import boundary
with that benchmark. A county total cannot uniquely identify end-use scaling
factors; EIA state shares are context, not Fresno-specific targets.

The Census API returned a key-required HTML response, so no API counts were
used. The independently retrieved EDD PDF is hashed in benchmark_reconciliation.json.

## Reproduce

```bash
python3 tools/run_fresno_residential_study.py --sample-size 256 --download --output results/residential_fresno_expanded
python3 tools/reconcile_fresno_benchmarks.py
```

The reconciliation also requires the EDD PDF cached as
.cache/residential_fresno/fresno_acs_2018.pdf (source linked above).
