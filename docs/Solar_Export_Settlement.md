# Solar export settlement implementation

Status reviewed 2026-09-21. **The request to cover every utility is not complete.**
The current executable adapter is a bounded monthly PG&E bundled residential
Solar Billing Plan (NBT) comparison. It is not a complete annual bill or legacy
NEM implementation. Existing import-only utilities remain import-only.
See [the Bay Area coverage audit](Bay_Area_Solar_Coverage_Audit.md) for the
provider inventory, code evidence and completion criteria.

## Implemented and verified

- Exact official 2026 hourly generation/delivery export factors for application
  vintages 2023–2026, indexed by UTC instant, including DST and utility holidays.
- PG&E E-ELEC June 2026 import components, ordinary residential ACC Plus,
  separate eligible generation/delivery credits, protected charges and opening/
  closing balances. Credits earned are not automatically cash savings.
- One confirmed complete 25–35-day cycle, June 1–September 21, 2026, ending
  before the account's next annual true-up. This cutoff is verified coverage,
  not a tariff expiration date. Full calendar-year export data does not extend
  the import-rate coverage.
- Five cases: grid only; PV self-consumption; PV with export; PV and battery
  without export; PV and battery with export. The no-PV case uses the same
  E-ELEC schedule as a counterfactual, not an asserted no-PV account assignment.
- Renewable-only charging, charge/discharge and import/export exclusivity,
  export-power limit, efficiency losses, throughput wear, cyclic minimum SOC.
  Dispatch minimizes cash due plus wear for this cycle. Unused closing credits
  have no assumed terminal cash value, so this is not annual optimal dispatch.
- Shared credit restrictions in billing and optimization, with final numerical
  bill reconciliation. Web form, durable worker, result tables and CSV exports.

Excluded: CCA generation, CARE/FERA/medical accounts, unconfirmed bonus
eligibility, local taxes/other adjustments, grid-charged storage exports,
annual retrospective credit application, NSC, termination, virtual/aggregate
accounts, equipment capital cost and electrical-network feasibility. The desktop
GUI has not yet been connected to this new export comparison.

## Sources and reproducibility

`utility_sources/solar_export/manifest.json` records URLs and SHA-256 hashes.
PG&E NBT special condition 2 provides credit restrictions and carryover;
condition 8 governs renewable-only paired storage. E-ELEC provides import rates.
`tools/solar_export/build_pge_export_data.py` extracts only 2026 from the official
CSV archive into `src/billing/pge_export_data.py`; later illustrative forecasts
are not used. Original large downloads stay in ignored cache.

## Browser validation example

Hypothetical San Francisco house, July 1–31, 2026, 15-minute intervals,
constant 1 kW native demand, 3 kW DC/AC PV, clear-sky weather, tilt 20 degrees,
azimuth 180 degrees, PV loss 14%, inverter efficiency 96%. Battery: 4 kWh,
2 kW charge/discharge, 20–80% SOC, starting/ending 0.8 kWh, 95% efficiency each
way, $0.01/kWh charging-plus-discharging throughput wear. Export limit 3 kW.
NBT application 2026, PTO 2026-04-01, next true-up 2027-04-01, opening credits
zero. Explicit hypothetical ordinary-account and bonus-eligibility assumptions.
Carbon objective weight zero; CAISO historical carbon remains retrieved with
its regional-proxy warning. This is not a real customer's bill or measured PV.

| Case | Bill due | Battery wear | Operating cost |
|---|---:|---:|---:|
| Grid only | $313.91 | $0.00 | $313.91 |
| PV self-consumption | $181.93 | $0.00 | $181.93 |
| PV with export | $167.61 | $0.00 | $167.61 |
| Battery, no export | $142.88 | $1.49 | $144.37 |
| Battery and export | $132.92 | $1.49 | $134.41 |

All credits earned were usable in this example. Storage reduced export credit
from $14.32 to $9.96, while reducing imported energy costs sufficiently to save
another $33.20 relative to PV/export without storage, after wear. Exporting the
remaining surplus saved $9.96 relative to the optimized no-export battery case.
Saved candidate study: `18ac90d61e0e4f309c2d23a145bbe772`, engine `19d5a2797366`.
Results reside in ignored `.cache/solar_export_candidate/runs/`.

## Which action is worth more?

For one available AC kWh, compare marginal usable values:

- Use now: the avoided marginal import charge, considering tiers and credits.
- Export now: the usable export credit, not necessarily a cash payment.
- Store for load: round-trip efficiency × later avoided import value, minus
  wear and the export credit forgone now.
- Store for export: round-trip efficiency × later usable export credit, minus
  wear and the export credit forgone now, only if the program permits it.

Storage capacity competes across times. Demand-charge savings arise only when
reducing the billed peak or applicable ratchet, not on every shifted kWh. Modern
low midday export prices can favor self-consumption or evening storage. Retail
netting can favor export over lossy storage, and high export-price hours can
reverse the usual ordering. Equipment payback requires a separate lifecycle
calculation; this monthly operating comparison does not establish it.

## Remaining utility work (do not substitute PG&E rules)

PG&E now has a separate [annual statement reconciliation component](PGE_Solar_True_Up.md).
It reproduces the published guide example but does not yet provide annual
interval billing, annual dispatch or annual browser/GUI controls.

| Utility/provider | Required work before enabling full settlement |
|---|---|
| PG&E | Annual true-up/NSC and verified historical average-export debit; NEM/NEM2; commercial and special accounts; GUI |
| SCE | Import component and EEC vintage mapping, monthly/annual NBT, NEM/NEM-ST, taxes and GUI/web integration |
| LADWP | OAS-specific NEM netting, credit restrictions, minimum bills and termination |
| CleanPowerSF, Peninsula, SVCE, SJCE, Ava | Provider-specific generation program plus separate PG&E delivery settlement; do not use PG&E generation credits |
| Hetch Hetchy | Confirm actual connection/eligibility; PG&E WDT-connected nonmunicipal accounts are not automatically eligible for SFPUC NEM |
| AMP | Adopted current ERG rider, tax ordering, carryover/payout and legacy NEM |
| SVP | NM/NEM program eligibility, retail netting, annual NSC/REC and aggregation exclusions |
| BWP | New 2026 net billing versus grandfathered NEM, ACOE, tax ordering and annual payout |
| PWP/GWP/ALW/IPU | Individual adopted export riders, enrollment, credit restrictions, taxes and annual settlement |

Research links: [SCE export pricing](https://www.sce.com/customer-service-center/help-center/solar/solar-billing-plan/understanding-export-pricing),
[BWP net billing](https://www.burbankwaterandpower.com/solar-net-billing),
[AMP current rates](https://www.alamedamp.com/157/Alameda-Municipal-Power-Rates),
[Hetch Hetchy interconnection](https://www.sfpuc.gov/interconnection-and-net-energy-metering-requests).
AMP's listed 2026 ERG PDF returned 404 during retrieval; a 2025 rider and proposed
2026 meeting material are not substitutes for verified adopted current rules.
SCE's official public folder is visible in the browser, but direct archive
retrieval returned 403 and browser download did not deliver a file in this run.
These are retrieval issues, not evidence that the utilities lack export programs.
