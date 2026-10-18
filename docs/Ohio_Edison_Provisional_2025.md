# Ohio Edison provisional 2025 studies

This opt-in research mode estimates ordinary residential RS and measured General
Service Secondary GS bills across calendar2025. It is **not verified historical
coverage** or a customer-bill calibration. The default `verified` mode still
rejects missing component versions. An account must explicitly set
`rate_evidence_mode: provisional_2025` and
`provisional_assumptions_accepted: true`; applying hypothetical account defaults
does not accept these assumptions automatically. Older saved requests retain
strict behavior when the new fields are absent.

## Assumed rates and billing rules

Source-pinned definitions, exact values, dates and component keys are in
`src/billing/firstenergy_oh_provisional.py`. They are replaceable, versioned
assumptions (`ohio_edison_2025_provisional_v1`), not confidence percentages.
Retained official excerpts and original document hashes are catalogued in
[the FirstEnergy source manifest](utility_sources/firstenergy/manifest.json).

| ID | Applicable dates / basis | Provisional treatment |
|---|---|---|
| OE25-GEN18 | Service February1–May31 | Carry January GEN17 winter energy $.073408/kWh and capacity $.003080/kWh RS / $.002908/kWh GS forward. Missing approved GEN18 may differ. Do not backfill June GEN19. |
| OE25-FEB-RECONSTRUCTION | Service February1–March31 | Use January31 testimony's **current**, not proposed ESP-VI, AMI $2.185 RS / $9.346 GS per month; DSE $.001151/kWh; EDR $.000252/kWh RS / $.002662/kWh GS; automaker $.000022/kWh. Assume continuity through March31. |
| OE25-FEB-RIDER-CONTINUITY | Service February1–March31 | Carry the documented January AER/DRR/DUN/GCR/PUR/NDU/NMB/PIR/RER/LGR values forward. Remove ESP-V vegetation/storm charges on the confirmed return to ESP IV. Intermediate approved compliance sheets remain unverified. Exact numeric values are retained in every applicable result. |
| OE25-FEB-DCR | **Bills dated** February1–May31 | Use testimony current DCR $.009711/kWh RS / $3.2608/kW GS; assume no intervening revision. This replaces January's percentage of base distribution. |
| OE25-LGR12 | Service July1–August13 | Carry January LGR11 $1.50/month RS / $.0018007/kWh GS forward because LGR12 is missing. Filed zero LGR starts August14. |
| OE25-AUGUST-LGR-ALLOCATION | RS cycles crossing August14 | Weight the monthly LGR by the number of **local service days** before/after removal, not physical hours. A full August RS cycle is $1.50×13/31 before component rounding. This allocation is a study approximation. GS LGR is volumetric; SGF follows the filed bill-date rule. |

The February1,2025 return from ESP V to ESP IV is documented; that transition
does not prove that the reconstructed composite matches every accepted filing.
January, June and August14–December31 verified intersections are unchanged.
April/May use the documented April rider quarter with the explicit GEN/DCR
assumptions above. July/August use the documented July rider quarter with the
explicit LGR assumption. September–December use their dated verified rates.

Official evidence underlying these choices includes the
[January service ratebook](https://www.firstenergycorp.com/content/dam/customer/Customer%20Choice/Files/Ohio/tariffs/OE-2024-Electric-Service.pdf),
[McMillen testimony](https://www.firstenergycorp.com/content/dam/customer/OpCoHome/files/ohio-esp-vi/Testimony-Brandon-McMillen.pdf),
[Patel testimony](https://www.firstenergycorp.com/content/dam/customer/OpCoHome/files/ohio-esp-vi/Testimony-Dhara-Patel.pdf),
and the dated ratebook captures listed in [FirstEnergy.md](FirstEnergy.md).
These documents support retained or reconstructed inputs; they do not convert
missing revisions or allocation assumptions into verified facts.

## Model and output contracts

- Same dated component expressions drive dispatch and independent rebilling.
  Capacity remains in GEN, transmission in NMB; no PJM LMP or separate PLC/TPLC
  charge is added to ordinary SSO bills.
- Modeled charge completeness (`is_complete_bill`) is separate from
  `rate_evidence_status`. Applicable bills/scenario totals use `provisional`
  and `objective_scope: provisional_modeled_bill`. Individual line items
  identify the assumption IDs affecting their rates. Unknown evidence in older
  saved results is not retroactively labeled verified.
- `result.json`, `billing-cycles.csv`, `billing-components.csv` and
  `billing-assumptions.csv` preserve assumption IDs, values, dates, sources and
  model version. The browser displays the evidence mode, acceptance control,
  full assumptions, result warning and comparison evidence column. CSV/ZIP
  downloads contain the same provenance.
- The simulator still requires complete regular25–35-day meter cycles. It
  rejects unsupported partial-service charges, fixed AMI or demand NMB changes
  inside a cycle, unapproved DER, competitive supply and export settlement.
  Provisional mode does not waive these guards or enable dates outside2025.
- Native load is distinct from net meter purchases. The representative annual
  cases use imported synthetic household/office series, actual cached2025 ERA5
  weather, existing PV/ESS models, zero export and PV-only battery charging.
  ERA5 hourly reanalysis is not measured15-minute weather.
- Optimization is historical perfect foresight **within each linked cycle**,
  continuous SOC, and specified initial/final annual SOC. There is no joint
  annual optimality or real-time strategy claim. Wear is reported separately
  and excluded from the default bill-minimization objective.
- OpenDSS QSTS checks the unchanged scheduled flows on representative circuits.
  Feasibility, solver proof and arithmetic reconciliation cannot verify the
  assumed historical rates. Electrical losses remain separate from bills.

## Reproduction

Prepared weather inputs remain in ignored local storage; this execution command
does not request new data or credentials:

```bash
/usr/local/bin/python3 tools/run_regional_validation.py --execute \
  --utility firstenergy_ohio_edison --period annual \
  --allow-ohio-provisional \
  --inputs .cache/firstenergy_weather_2025 \
  --output .cache/ohio_provisional_2025
```

Use a fresh output directory for changed source/inputs. The validation launcher
also forwards `--allow-ohio-provisional` when `--regional` is selected. Without
this flag, full-year Ohio studies reject rather than silently assume rates.

Recover GEN18, LGR12 and the complete approved February/intermediate compliance
sheets next. Compare each with the recorded assumption, update the version and
rerun affected bills, dispatch and reconciliation. Verified coverage should
expand only after that evidence is recovered. Provisional annual results retain
their original engine ID and must not be relabeled verified after later fixes.

## First annual comparison

The first frozen candidate completed both full-year cases. Annual modeled bills
(grid /PV /PV plus battery) are residential $2,335.48 /$1,640.19 /$1,393.90 and
commercial $11,417.32 /$9,927.12 /$9,407.53. Six months use provisional inputs,
so **both annual comparisons are provisional estimates**. The corresponding
engine, inputs, monthly amounts, solver proofs and QSTS evidence are recorded
in [FirstEnergy_Validation.md](FirstEnergy_Validation.md).

Commercial storage's $519.59 incremental savings versus PV alone includes
$219.00 NMB, $184.23 base distribution demand and $105.59 DCR savings. These
components together account for $508.82; the remainder is net energy/tax/rider
changes. This verifies that the modeled demand costs affect dispatch; it does
not establish historical tariff accuracy. Residential storage principally
reduces imports by using otherwise curtailed PV after solar hours. No export
credit is assumed, and battery wear is outside these bill amounts.
