# Bay Area solar billing coverage audit

Reviewed 2026-09-21 against the main working tree (uncommitted changes retained).
**Result: FAIL — the Bay Area is not fully covered. LA expansion must not be
presented as the next completed regional milestone.**

A provider appearing in location matching, or having import rates, does not mean
its solar program is implemented. A downloaded export price is also not a
complete settlement model. The audit distinguishes executable support from
programs identified in official sources.

## Existing executable scope

Subsequent PG&E work added [NBT annual statement reconciliation](PGE_Solar_True_Up.md).
It is separate from interval simulation; the annual simulation/dispatch and
legacy NEM/NEM2 gaps below remain open.

`src/billing/pge_export.py` accepts only bundled PG&E, residential E-ELEC, ordinary
income tier 3, NBT, confirmed ACC Plus eligibility and renewable-only storage.
It covers one complete confirmed 25–35-day cycle between June 1 and September
21, 2026, before annual true-up. It rejects other providers, legacy NEM, annual
true-up and grid-charged export. `src/dispatch/solar_export.py` calls that exact
adapter; there is no other utility adapter behind this comparison.

`src/local_web/export_study.py` additionally restricts the web path to individual
houses/apartments, 15-minute data and the current E-ELEC tariff ID. Web controls
are PG&E-residential only. The desktop GUI does not expose this new adapter.

`src/billing/municipal.py` explicitly rejects exporting AMP/SVP accounts;
`src/local_web/municipal_service.py` only accepts export_program=none.
`src/billing/bay_area_cca.py` excludes NEM/NBT/export settlement. Import-plan
coverage and the earlier successful Ava bill reconciliation do not establish
Ava solar settlement support.

## Provider and program inventory

This inventory covers ordinary behind-the-meter retail solar across the nine
Bay Area counties, including providers outside the current application menu.
Special contracts, wholesale sales, feed-in tariffs, virtual/aggregate metering,
master meters and municipal/Enterprise accounts require additional inventory and
validation; this document does not assert that every such arrangement is listed.

| Provider | Official program evidence / families | Executable solar support |
|---|---|---|
| PG&E bundled | [NBT tariff](https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_NBT.pdf); [NEM2](https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_NEM2.pdf); legacy NEM | Partial monthly residential NBT only; annual and legacy programs missing |
| CleanPowerSF + PG&E | [Residential rooftop solar](https://cleanpowersf.org/residential-rooftop-solar): NEM; page describes SBP changes as proposed | None; do not treat proposal as adopted |
| Peninsula Clean Energy / WestLight + PG&E | [Official board tariff material](https://www.peninsulacleanenergy.com/wp-content/uploads/2023/01/10-26-2023-BOD-Agenda-Packet.pdf): SBP; legacy NEM requires separate verification | None; retrieve current adopted tariff before coding |
| Silicon Valley Clean Energy + PG&E | [Solar program](https://www.svcleanenergy.org/solar/), [SBP](https://www.svcleanenergy.org/solar-billing-plan/): NEM and SBP | None |
| San José Clean Energy + PG&E | [Solar billing](https://sanjosecleanenergy.org/solar-billing-nem/): NEM and SBP | None |
| Ava Community Energy + PG&E | [NEM](https://avaenergy.org/your-energy-options/plans-and-rates/rates/net-energy-metering/), [SBP](https://avaenergy.org/your-energy-options/plans-and-rates/rates/solar-billing-plan/) | None |
| MCE + PG&E | [SBP](https://mcecleanenergy.org/solar-billing-plan/) and [solar information](https://mcecleanenergy.org/solar-and-storage-basics/): legacy NEM and SBP | None; broader provider integration also required |
| Sonoma Clean Power + PG&E | [SBP](https://sonomacleanpower.org/solar-billing-plan), [NEM tariff](https://sonomacleanpower.org/uploads/documents/Net_Energy_Metering_Tariff.pdf) | None; broader provider integration also required |
| Hetch Hetchy Power | [SFPUC interconnection/NEM](https://www.sfpuc.gov/interconnection-and-net-energy-metering-requests): connection-dependent eligibility | None; no universal NEM assumption for PG&E WDT-connected accounts |
| Alameda Municipal Power | [Solar compensation](https://www.alamedamp.com/195/Solar-Compensation-Billing): ERG and legacy NEM | None |
| Silicon Valley Power | [NM billing](https://www.siliconvalleypower.com/sustainability/solar/understanding-your-bill), [filed 2026 NM schedule](https://www.siliconvalleypower.com/home/showpublisheddocument/58854/638399684553970000) | None |
| Palo Alto Utilities | [Net energy metering](https://www.paloalto.gov/Departments/Utilities/Electrification/Electrify-My-Home/Consider-Solar/Net-Energy-Metering): legacy and successor treatment | None; broader provider integration also required |
| Healdsburg Electric | [Solar and storage](https://www.ci.healdsburg.ca.us/235/Solar-Energy-Storage): solar interconnection and NEMA information | None; retrieve adopted settlement tariffs and add provider integration |

Official public overview pages identify programs; they do not by themselves
verify every rate, tax, historical version, or billing-order rule. No new rates
were inferred or enabled during this audit.

## Completion criteria before calling a provider covered

1. Separate delivery provider, generation provider, import plan and solar
   program, with confirmed enrollment, application/PTO dates and meter topology.
2. Dated import and export versions with sources, strict coverage and vintage /
   grandfathering / transition rules.
3. Monthly and annual settlement: eligible credit buckets, NBCs, fixed/minimum
   charges, taxes, balances, retrospective credit application, net-surplus
   compensation, payout/reset/rollover and termination where applicable.
4. Dispatch uses the same bill algebra, respects storage export eligibility,
   and reconciles interval energy, monthly peaks and final bills.
5. Web and desktop expose only supported account combinations and preserve
   settings; required account facts cannot be inferred from geographic location.
6. Independent fixtures cover net consumers/producers, credit saturation,
   true-up, plan changes, date/rate boundaries, DST, and applicable demand charges.

## Work order

First finish PG&E settlement and extend the reusable credit/account framework.
Then implement Peninsula/SVCE/SJCE, CleanPowerSF/Ava and AMP/SVP/Hetch Hetchy with
provider-specific rules. Add MCE/Sonoma/Palo Alto/Healdsburg to satisfy the broader
regional scope. Validate each supported account envelope before marking it done.

LA follows the Bay Area milestone: SCE NBT/NEM-ST/NEM; LADWP NEM; Burbank new net
billing and grandfathered NEM; Pasadena, Glendale, Azusa and Industry export
riders. Include separate CCA generation (for example Clean Power Alliance) when
claiming geographic LA coverage. Existing LA import billing is not solar support.
