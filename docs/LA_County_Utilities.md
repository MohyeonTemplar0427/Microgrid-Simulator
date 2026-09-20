# LA County expansion — implementation and research coverage

Reviewed 2026-09-19. This is an **incomplete expansion**, not a declaration that all LA utilities are supported. The executable registry and API coverage metadata distinguish working plans from research records. Existing SCE/LADWP support remains separate.

## Coverage matrix

| Provider | Executable schedules | Verified implemented dates | Solar | Remaining work |
|---|---|---|---|---|
| Glendale GWP | L-1-A, L-1-B, L-2-A, L-2-B, LD-2-A | 2025-01-01–2026-09-19 | Rejected | Other L-1 options, master meters, special riders/assistance, standby/export; see bounded scope below |
| Pasadena PWP | None | None | Rejected | June 2026 restructuring, meter-dependent TOU, street-light tax exemption allocation, demand rounding/PF |
| Burbank BWP | None | None | Rejected | Adopted full schedules/riders, kVA demand, ECAC history, taxes/transfer treatment |
| Azusa ALW | None | None | Rejected | D/G/GL/TOU, independently dated PCA/PBC, minimum bills, declining tiers, rounded demand/ratchets and reactive charges |
| Vernon VPU | None | None | Rejected | Official directory includes residential D/TOU-D; exact filed schedules/riders not retrieved |
| Industry IPU | None | None | Rejected | Partial-city territory, full tariff book and account-specific requirements |
| Cerritos CEU | None | None | Rejected | Generation agreement + separate SCE delivery bill; enrollment acceptance required |
| CPA | None | None | Rejected | Generation products/vintages plus complete unbundled SCE delivery/CCA-CRS/GMS |
| Lancaster Energy | None | None | Rejected | Same independent generation/delivery/rider reconciliation |
| Pico Rivera PRIME | None | None | Rejected | Exact schedules rather than joint-rate-comparison averages |
| Pomona Choice | None | None | Rejected | Exact schedules rather than joint-rate-comparison averages |
| Palmdale EPIC | None | None | Rejected | Included following official SCE directory review; tariff implementation pending |

“None” means no executable billing plan, even when official rates have been located. Incomplete providers remain visible as location suggestions with exclusion reasons. A disabled option is not a working integration.

## Location and enrollment

The existing CEC **electric** distribution layer supplies stable agency IDs: GWP 37452, PWP 71750, BWP 19201, ALW 11991, VPU 93642, IPU 32555. Results retain layer item ID, edit timestamp, response hash and retrieval timestamp. CCA suggestions now also retain layer edit metadata. Point matches remain approximate; overlapping or nearby boundaries remain ambiguous. A user bill/utility attestation is recorded separately and preserves the original map evidence.

IPU is not assigned from city names or ZIPs, and SCE is not inferred by exclusion. CEC distribution object 34 (City of Cerritos, null agency number) is explicitly reclassified as generation evidence using the [CEU service application](https://www.cerritos.gov/media/ugmlrene/cerritos-electric-service-application.pdf). That application includes residential participation, requires utility acceptance, excludes residential onsite generation/storage, and describes separate CEU/SCE bills. Marketing discounts are not tariff coefficients.

The [SCE CCA directory](https://www.sce.com/customer-service-center/community-choice-aggregation) confirms CPA, Lancaster, PRIME, Pomona and Palmdale EPIC. Object IDs are checked against official CEC provider names before assigning an internal generation identifier. Availability never establishes enrollment. No new CCA billing is enabled. CPA territory extends outside LA County; adding billing must include the requested county scope without treating county boundaries as electric-service proof.

## Glendale implementation

Source artifacts and SHA-256 hashes are in `utility_sources/la_county/manifest.json`.

- [Ordinance 6042 and October 7, 2025 meeting](https://glendaleca.primegov.com/Portal/Meeting?meetingTemplateId=39969): adopted minutes confirm passage; scanned Exhibit A is the coefficient source. Phase 2 continues through October 31, 2025; phase 3 begins November 1. Future adopted base rates are not sufficient to extend independently dated rider coverage.
- [Electric code, chapter 13.44](https://ecode360.com/43350677): eligibility, seasons, TOU, demand, billing and public-benefit rules.
- Signed October 1, 2024 Resolution 24-163 establishes the 2.85% public-benefit rate. The current official rate pages report zero ECAC/RAC/RDC. Base and rider records are separate; missing coverage is rejected. A future percentage-rider transition is explicitly rejected until its allocation rule is implemented.
- [Holiday definitions, 3.08.010(A)](https://ecode360.com/43340925): electric code references subsection A. Includes Friday after Thanksgiving. The implementation does not import the employee observance rule from subsection C. Special declared holidays are outside scope.
- [Glendale utility user tax](https://ecode360.com/43341925): 7% with account-confirmed jurisdiction, or explicitly confirmed zero for exemption/outside-city. Tax is not inferred from the CEC polygon.

Bounded scope: ordinary secondary service, individually metered residences, complete or explicitly hypothetical cycles up to 70 days (40 days for demand studies). L-2 comparisons impose <20 kW and <5,000 kWh per 30 study days; this is a conservative study restriction, **not** the utility’s historical classification algorithm. The account must separately confirm eligibility. The billed demand floor is an explicit utility/account-confirmed trailing-history input. Current demand and that floor are compared once per cycle, not summed across intervals. The study does not optimize future ratchet liabilities.

Tier allowances accrue 10 kWh per local service day for each of the first two tiers, split across season/rate changes; the allocation convention is explicitly acknowledged as a study approximation. Local calendar days and actual 15-minute intervals preserve DST. GWP TOU high season is July–October (14:00–20:00); low season November–June (12:00–21:00), applicable weekdays excluding the specified holidays.

The same charge expressions price final bills and dispatch. All five implemented plans have bill/objective reconciliation tests. Storage requires confirmation that the ordinary import schedule applies without a standby rider. PV/export/customer-generation schedules, assistance, reactive charges, master meters and special account adjustments are rejected/excluded, not replaced with other utilities’ rules. Operating costs exclude equipment capital costs. Electrical network feasibility is not evaluated by this study path.

## Remaining source and modeling work

### Pasadena

[June 2026 electric rate card](https://pwp.cityofpasadena.net/wp-content/uploads/2026/07/Summary-Rates-2026_07_updated.pdf), [rate archive](https://pwp.cityofpasadena.net/rate-card-archive/), and March 23, 2026 agenda attachments [resolution](https://ww2.cityofpasadena.net/2026%20Agendas/Mar_23_26/AR%2016%20RESOLUTON.pdf) / [ordinance](https://ww2.cityofpasadena.net/2026%20Agendas/Mar_23_26/AR%2017%20ORDINANCE.pdf) were inspected. Agenda drafts alone are not adoption proof. Current code identifies Ordinance 7466 adopted March 30; exact final provisions still need reconciliation.

The rate card includes a per-kWh PBC, UUT, SLATS with the first 1,000 kWh exempt, and declining-block underground surcharge. Public-benefit charges are excluded from local taxes. The street-light exemption’s allocation across energy/fixed/demand charges remains unresolved. Four-month demand history (including the current month), rounding, power-factor discounts/penalties, and meter-dependent TOU transition require new objective/state treatment. Do not simply add the printed tax percentages to all charges. The website and PDF flat-energy decimal differ; the PDF/base-plus-PCA arithmetic must be reconciled against adopted records before use.

### Burbank

The [official 2026/2027 summary](https://www.burbankwaterandpower.com/documents/d/guest/Summary-of-Electric-Rates-by-Customer-Type_Commercial_all) lists residential and C/D/L/XL schedules. It separates ECAC from base energy. Its commercial “composite” rows mix demand and energy units and must not become kWh prices. Commercial demand is kVA, requiring apparent/reactive-power inputs and physical constraints, not a relabeled kW peak. The [bill explanation](https://www.burbankwaterandpower.com/residential-tou-bill) says ECAC may change monthly and identifies the in-lieu transfer; do not assume a year header proves an unchanged adjustment all year or add an embedded transfer again. Full adopted rules, tax bases, service-size classification, holidays and demand minimums remain to verify.

### Azusa

The [January 2025 rule book](https://azusaca.gov/DocumentCenter/View/48871/Rules-and-Regulations-01-1-2025) provides D/G/GL/TOU and rider schedules. Web text is readable, but direct archival download returned HTTP 404; no fabricated local PDF is recorded. [PCA](https://azusaca.gov/1254/Schedule-PCA) and [PBC](https://www.azusaca.gov/1252/Schedule-PBC) change independently. The current PCA page explicitly covers July–December 2026; PBC covers July 2026–June 2027. Historical rider coverage must be sourced separately. Rule 8 uses monthly billing with specific proration exceptions. G has declining energy blocks; G-2 uses 15-minute demand with an 11-month ratchet and 0.1-kW rounding; GL includes interval transitions and reactive charges. These require explicit implementation, not approximating with Glendale’s cost function. The [tax page](https://www.azusaca.gov/696/Electric-and-Water-Users-Tax) distinguishes residential/commercial rates. Its water-service jurisdictions cannot establish electric service.

### Vernon and Industry

[Vernon’s official schedule directory](https://www.cityofvernonca.gov/government/public-utilities/electric-rate-schedule) lists July 1, 2026 residential and commercial schedules. The live page returned HTTP 403; cached directory names do not provide filed coefficients. A public hearing notice is not an adopted tariff.

[Industry’s electric page](https://www.cityofindustry.org/191/Electric) links a territory map and large tariff/rule PDFs. Direct downloads returned HTTP 404 and the web reader could not retrieve the large rate book. Current displayed solar factors have explicit expiry dates and were not extended. Both utilities remain source-incomplete, distinct from PWP/BWP/ALW modeling work.

### SCE generation providers

[CPA residential](https://cleanpoweralliance.org/residential-rate/) and [commercial](https://cleanpoweralliance.org/commercial-rate/) schedules distinguish products and enrollment vintages. Generation rates exclude SCE delivery, GMS and CCA-CRS. CPA source pages also advertise a newer TOU-SMART pilot, so one generic “CCA rate” is insufficient. PRIME and Pomona joint-rate comparisons encountered during research are averages, not billing coefficients. CEU needs the accepted agreement’s actual generation tariff. Full SCE unbundled delivery and applicable vintage-specific riders must reconcile before any actual CCA/CEU bill is enabled. Existing hypothetical bundled comparisons remain explicitly labeled.

## Validation and promotion

See `LA_County_Handoff.md` for test outcomes, browser study IDs and engine pins. Territorial unit fixtures exercise resolver behavior, not address-level proof of service. No anonymized GWP customer bill was supplied; numerical fixtures are independent hand calculations against the official schedule.
