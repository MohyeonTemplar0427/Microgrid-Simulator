# Non-PG&E solar export program consolidation

Reviewed 2026-09-29. The program inventory is in
`src/billing/solar_programs.py` and appears in `/api/capabilities` as
`solar_export_programs`. It identifies account-specific programs; it does **not**
make them billable. All non-PG&E entries except bounded SCE NBT, SCE legacy NEM,
LADWP R-1A NEM and BWP EV TOU net billing remain `research_only`. Import billing,
territory matching, and program identification alone must never turn on export
credits. PG&E bundled residential NBT and those four bounded paths are executable.
Several existing import adapters have verified coverage ending September 16 or
17, 2026; a current-date export study also needs newer import versions, even if
an export rider has been found.

Burbank's EV TOU adapter now combines the July 1–September 20, 2026 avoided-cost
export prices, confirmed post-January-2026 account trigger, imported energy and
ECAC, carried solar dollars, fixed charges, taxes and export-aware dispatch.
It is **one confirmed cycle only**. The published [sample solar bill](https://www.burbankwaterandpower.com/solar-net-bill-breakdown)
confirms that export credits reduce usage plus ECAC before the two 7% charges,
while the customer and service-size charges remain payable. The annual optional
cash-out, legacy NEM, BWP Basic/C solar settlement, special riders and historical
rates outside this window remain unsupported. The Clean Power Alliance monthly
generation-credit restriction remains a component only; CPA still needs dated
generation import/export prices, SCE delivery settlement and its annual adjustment.

## Account model

An export study needs a confirmed **delivery utility**, **generation provider**,
**import schedule**, **solar program**, interconnection/PTO facts, billing-cycle
dates and opening credit balances. Location can suggest delivery territory but
cannot establish CCA enrollment or NEM grandfathering. For a CCA customer,
delivery and generation have separate rates, eligible charges and settlement
rules. The generic `monthly_credit_ledger` is a calculation component, not a
provider tariff. NEM retail netting cannot be substituted with NBT hourly
export pricing, and a dollar credit cannot be assumed to be immediate cash.

| Provider group | Identified program | Rule that changes the model | Still required for executable support |
|---|---|---|---|
| SCE bundled | [NBT export pricing](https://www.sce.com/customer-service-center/help-center/solar/solar-billing-plan/understanding-export-pricing), [NEM 1.0](https://www.sce.com/sites/default/files/custom-files/PDF_Files/ELECTRIC_SCHEDULES_NEM.pdf), [NEM-ST 2.0](https://www.sce.com/sites/default/files/custom-files/PDF_Files/ELECTRIC_SCHEDULES_NEM-ST.pdf) | NBT23–NBT26 use vintage-specific hourly generation/delivery EEC and separate credit banks. Legacy NEM uses retail TOU netting; NEM-ST protects interval import NBCs. Bundled residential TOU-D-PRIME supports bounded 2025–September 17, 2026 cycles with confirmed account status. | Pre-2025 service rates, other import schedules, equity NBT, paired storage on legacy NEM, annual true-up, NSC and jurisdiction-specific taxes remain unsupported. |
| SCE + Clean Power Alliance | [CPA NBT](https://files.cleanpoweralliance.org/uploads/2026/03/CPA-Net-Billing-Tariff-2026-02-05.pdf), [CPA NEM](https://cleanpoweralliance.org/residential-rate/) | CPA's generation export credit applies only to CPA energy charges, not SCE delivery, demand, taxes or fees. The monthly generation-credit restriction is implemented as a component; CPA has its own annual adjustment, refund and cash-out rules. | CPA generation import versions, posted generation EEC factors, SCE delivery settlement and dated account eligibility. |
| SCE + Orange County Power Authority | [OCPA solar NEM](https://www.ocpower.org/energy-programs/solar-net-energy-metering/) | OCPA states it currently treats even NBT generation as NEM 2.0, with monthly generation reconciliation and an April annual true-up. | OCPA dated generation rates and policy, SCE delivery treatment, transition/account checks, credit banks and annual settlement. |
| PG&E + Bay Area CCAs | [CleanPowerSF](https://cleanpowersf.org/residential-rooftop-solar), [WestLight / Peninsula](https://www.peninsulacleanenergy.com/wp-content/uploads/2023/01/10-26-2023-BOD-Agenda-Packet.pdf), [SVCE](https://www.svcleanenergy.org/solar-billing-plan/), [SJCE](https://sanjosecleanenergy.org/solar-billing-nem/), [Ava](https://avaenergy.org/your-energy-options/plans-and-rates/rates/solar-billing-plan/), [MCE](https://mcecleanenergy.org/solar-billing-plan/), [Sonoma](https://sonomacleanpower.org/solar-billing-plan) | Each CCA's generation settlement is distinct from PG&E delivery. Legacy NEM and successor solar billing may differ; CleanPowerSF's public page discusses proposed SBP changes, so adoption must be checked before any SBP claim. | Current adopted CCA riders and generation rates, historical versions, PG&E delivery components, credit eligibility and annual true-up. |
| LADWP | [NEM rider](https://www.ladwp.com/account/customer-service/electric-rates/residential-rates) | Residential R-1A net-import cycles now net billing-period import/export kWh, apply a confirmed opening credit above the protected minimum, and export a credit ledger. | Net-export credit-tier pricing, R-1B TOU allocation, account termination and multi-meter cases remain unsupported. |
| Alameda Municipal Power | [ERG and legacy NEM](https://www.alamedamp.com/195/Solar-Compensation-Billing) | ERG exports earn avoided-cost bill credits; legacy NEM closed to new entrants in August 2017 and retains a 20-year period. | Retrieve adopted dated ERG/NEM riders, export price, tax order, carryover/payout and account interconnection. The official current-rates page links the 2026 riders, but its PDF redirect loop prevented validation of their full text in this review. |
| Silicon Valley Power | [NM](https://www.siliconvalleypower.com/sustainability/solar/understanding-your-bill) | Monthly statements and annual billing/settlement differ from AMP's monthly avoided-cost export. | Dated NM tariff and buyback rate, TOU tiers, annual net-surplus and REC rules. |
| Burbank Water and Power | [New net billing and grandfathered NEM](https://www.burbankwaterandpower.com/solar-net-billing) | A confirmed residential EV TOU net-billing account can now estimate one complete cycle in July 1–September 20, 2026. It uses 15-minute [adopted ACOE export rates](https://www.burbankwaterandpower.com/documents/d/guest/burbank_adopted_fee_schedule), carries unused solar dollars, and prices storage dispatch before inherited credits. | Other schedules, grandfathered NEM, annual cash-out, special riders and earlier/later rates need separate verification. |
| Pasadena, Glendale, Azusa, Industry | [PWP net surplus](https://pwp.cityofpasadena.net/netsurpluscompensation/), [GWP NEM](https://www.glendaleca.gov/government/departments/glendale-water-and-power/solar-education/guide-for-applying-for-interconnection), [ALW NGP](https://www.azusaca.gov/1061/Schedule-NGP), [IPU NEM/ERG](https://cityofindustry.org/191/Electric) | PWP allows different annual versus monthly/bimonthly compensation elections and ties REC value to ownership. ALW pays annual net generator surplus. IPU's NEM and ERG use different energy measures and its published rate expired August 31, 2026. GWP solar service uses separate NEM rate schedules. | Verify adopted solar import schedules, dated export compensation, election/REC facts, tax and true-up rules before reuse of ordinary import billing. |
| Other Bay municipal | [Hetch Hetchy](https://www.sfpuc.gov/interconnection-and-net-energy-metering-requests), [Palo Alto](https://www.paloalto.gov/Departments/Utilities/Electrification/Electrify-My-Home/Consider-Solar/Net-Energy-Metering), [Healdsburg](https://www.ci.healdsburg.ca.us/235/Solar-Energy-Storage) | Eligibility depends on the actual connection and enrollment; no PG&E or SVP billing substitution. | Adopted rider, solar import rate, historical account window and annual settlement. |

## Implementation sequence

1. For each program, record dated official import and export versions, source
   URL/hash, eligible accounts, and account-transition dates. Seek ten years of
   history where available; reject any date gap rather than copying a nearby
   rate. Start with SCE bundled NBT and its linked CPA/OCPA CCA treatment, then
   Bay CCAs and municipal programs.
2. Add provider adapters around the shared interval meter flows and credit
   ledger. The adapter must return a reconciled bill, opening/earned/used/closing
   balances, protected charges, and any annual adjustment. Preserve separate
   generation and delivery accounts where the provider requires them.
3. Make dispatch optimize the applicable cycle charges and newly earned,
   usable export credits, including limits on storage export. Apply inherited
   credits only when reporting the authoritative bill; an opening balance
   must not change the battery schedule. Unused new credits have no assumed
   future value, so this is not a full-year optimum.
4. Enable only validated account combinations in the local browser and desktop
   GUI. Test net consumers/producers, credit saturation, transition dates,
   time-zone/DST boundaries, partial cycles, true-up and final bill reconciliation.

The program catalog deliberately contains no estimated export rates and does
not modify the current fail-closed behavior for other utilities.
