# Offline simulation parameter sweep

The repeatable command is:

```bash
env MPLCONFIGDIR=/tmp /usr/local/bin/python3 tools/run_simulation_sweep.py \
  --output docs/validation/Simulation_Parameter_Sweep_2026-09-24.json
```

It uses deterministic hypothetical inputs and no live APIs, customer records,
downloaded weather, or inferred utility rates. An optional `--groups` argument
selects one or more of `commercial`, `pge_residential`, `residential_nbt`,
`socal`, `municipal`, and `boundaries`. Every case records its input parameters, metrics and pass or
failure in the [machine-readable baseline](Simulation_Parameter_Sweep_2026-09-24.json).
The command exits nonzero if any case fails.

The September 24, 2026 run passed **97 of 97** cases:

| Group | Cases | Variation and checks |
| --- | ---: | --- |
| PG&E commercial | 36 | B-10, B-19 Option S and B-20; summer/winter; flat, evening and midday load; PV on/off; idle versus bill-only storage. Checks PCC power balance, battery energy/SOC, and bill non-increase within two cents. |
| PG&E residential bundled | 12 | E-1, E-TOU-D, E-ELEC and EV2; flat, midday and evening consumption; two load levels in a complete July 2026 cycle. Checks billed energy, line-item reconciliation and increasing bills with higher consumption. Assumes income tier 3 and baseline territory T. |
| PG&E residential NBT | 13 | Six load/PV combinations, four storage/wear choices, two small/oversized battery cases with high PV, and one high-export credit-bank case. Checks bill ordering, savings-component reconciliation, dispatch objective and non-cash credit carryover. |
| LADWP/SCE | 24 | LADWP R-1A/R-1B and SCE D, TOU-D-4-9, TOU-D-5-8 and TOU-D-PRIME; two load levels and PV on/off with storage. Checks power balance, bill/objective reconciliation and bill non-increase within two cents. |
| AMP/SVP | 6 | Residential and commercial full-cycle bills, plus two demand-plan storage optimizations. Checks line-item sums, power balance and certified objective gap. |
| Date boundaries | 6 | PG&E Option S spring/fall DST days; SCE's November 2025 basic-to-BSC transition and version switch; explicit rejection before verified PG&E/SCE rate coverage. |

One useful stress result: at an assumed battery wear rate of $0.25 per kWh of
throughput, the bill-only PG&E NBT optimizer reduced the current bill to
$133.61 but produced $37.25 of modeled wear, for $170.86 combined operating
cost. Enabling the wear option left the battery idle and produced a $168.32
bill. This is a hypothetical operating comparison, not a payback result. The
high-PV case had a $19.28 amount due and $40.15 of unused closing credit; the
credit was not treated as a cash payout. The DST cases contained 92 and 100
15-minute intervals respectively.

Passing the sweep establishes **internal consistency under these scenarios**.
It does not establish agreement with an actual utility statement, actual meter
cycle, installation cost, grid reliability, or emissions avoided. The PG&E
commercial comparisons cover short *partial* billing periods; their dollar
savings must not be interpreted as actual two-day bills. LADWP/SCE test inputs
use an explicit two-day fixed-charge allocation. Only documented tariff dates
and supported account arrangements are exercised. The SCE transition uses a
full November 2025 cycle, including the fall DST day.

To expand coverage, add a deterministic case to the relevant group in
`tools/run_simulation_sweep.py`, state its account and tariff assumptions,
verify a meaningful invariant or independent reconciliation, then regenerate
the JSON baseline. Preserve the explicit rejection cases for unsupported
coverage; a successful run must never depend on substituting an adjacent rate.
