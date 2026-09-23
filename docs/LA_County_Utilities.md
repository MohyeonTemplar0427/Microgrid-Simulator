# LA County expansion — implementation and research coverage

Reviewed 2026-09-20. This is an **incomplete expansion**, not a declaration that all LA utilities are supported. The executable registry and API coverage metadata distinguish working plans from research records. Existing SCE/LADWP support remains separate.

## Coverage matrix

| Provider | Executable schedules | Verified implemented dates | Solar | Remaining work |
|---|---|---|---|---|
| Glendale GWP | L-1-A, L-1-B, L-2-A, L-2-B, LD-2-A | 2025-01-01–2026-09-19 | Rejected | Other L-1 options, master meters, special riders/assistance, standby/export; see bounded scope below |
| Pasadena PWP | R-1/R-2/S-1 legacy flat | 2026-06-01–2026-07-31 | Deferred | Confirmed flat enrollment; TOU/CPP, demand/PF and partial-service rules not enabled |
| Burbank BWP | Residential Basic/EV TOU; commercial C | 2026-07-01–2026-09-20 | Deferred | Confirmed $0.034 ECAC, ordinary monthly service; kVA demand plans not enabled |
| Azusa ALW | Residential D; non-demand G-1 | 2025-01-01–2025-06-30; 2026-01-01–2026-09-20 | Deferred | Full monthly cycle within one rider window; 2025H2 PCA missing; G-2/GL/TOU not enabled |
| Vernon VPU | None | None | Deferred | Base D and adopted ECA procedure retrieved; actual dated ECA/renewable factors and tax rules remain incomplete |
| Industry IPU | Individual domestic D | 2025-01-01–2026-09-20 | Deferred | Confirmed ordinary contract; commercial seasons/contract rules not verified; general posted rules are draft |
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

## Newly implemented billing scope

All four new providers use the shared SoCal bill/dispatch interface and the existing location-first browser wizard. Account qualification, dates and ordinary service restrictions are validated in the backend. Unsupported dates reject before a job is queued. These are bounded import implementations, not complete tariff books. Solar export settlement is deferred by user instruction until utility-region coverage is finished.

### Pasadena

The [June 2026 electric rate card](https://pwp.cityofpasadena.net/wp-content/uploads/2026/07/Summary-Rates-2026_07_updated.pdf) and [adopted code](https://library.municode.com/ca/pasadena/codes/code_of_ordinances?nodeId=TIT13UTSE_CH13.04PORARE) establish the implemented June–July window. Current code identifies Ordinance 7466 adopted March 30. R-1, R-2 and S-1 require confirmed legacy flat enrollment; a new interval-meter account cannot silently use the flat schedule. R-2 requires the specified multifamily qualification; S-1 is restricted below 30 kW.

Fixed, distribution, energy/PCA, transmission, public-benefit, UUT, SLATS and underground charges are itemized. The printed energy price includes PCA, so it is split rather than added twice. PMC 4.54.020(D) exempts energy and periodic schedule adjustment charges for the first 1,000 kWh from SLATS; it does not exempt the whole first portion of the bill. PBC is excluded from municipal tax bases under 13.04.230(G). Underground charges use declining dollar blocks. Complete monthly/bimonthly cycles use an explicit 1/2-month factor; opening/closing proration is excluded. Only ordinary 7.67% UUT accounts are supported.

**Outstanding modeling:** TOU/CPP meter transition, M-class demand history and rounding, power-factor treatment, special assistance and partial-service proration. These rules require implementation; they are not all missing source data.

### Burbank

The [adopted FY2026–27 fee schedule](https://www.burbankwaterandpower.com/documents/d/guest/burbank_adopted_fee_schedule) supplies Basic, EV TOU and non-demand commercial C. Current support is July 1–September 20, 2026. Published $0.034/kWh ECAC must be confirmed for the account/cycle; it may change monthly and is not extrapolated across earlier history. Residential service-size charges and C phase charges are explicit inputs.

The [official bill example](https://www.burbankwaterandpower.com/residential-tou-bill) independently confirms that 7% in-lieu transfer and 7% UUT both apply to the pre-tax service subtotal, without tax-on-tax. EV/C energy periods and adopted holidays are implemented, including Sunday observance and no Friday substitution for Saturday holidays. Billing and dispatch use identical cost expressions. Public-benefit revenue obligations are not added again as a fabricated separate bill charge.

**Outstanding modeling:** D/L/XL demand is kVA, not kW. These plans need apparent/reactive-power inputs, physical constraints, demand minimums and qualification history. Historical ECAC/rule coverage and special account programs also remain incomplete.

### Azusa

Official [January 2025](https://www.azusaca.gov/DocumentCenter/View/48871/Rules-and-Regulations-01-1-2025), [January 2026](https://www.azusaca.gov/DocumentCenter/View/49491/Rules-and-Regulations-01-1-2026) and [June 2026](https://www.azusaca.gov/DocumentCenter/View/50568/Rules-and-Regulations-6-1-2026) rule books were retrieved successfully. D/G-1 base rates and independently dated PCA/PBC records are implemented. D minimum base energy is applied before riders. G-1 declining energy blocks are preserved. Full 25–35-day monthly cycles must stay within a single verified rider window. 2025H2 PCA remains missing, so those dates reject. July 2026 changes PBC from .00528 to .00536; PCA remains .05000. Residential/commercial tax is separately confirmed at 4%/8%, or documented zero.

**Outstanding modeling:** heating/assistance and meter opt-out, G-2 rounded 15-minute demand with prior 11-month ratchet, GL/TOU/reactive charges and partial-service proration. D/G-1 have flat monotone import costs; with no PV and equal initial/final SOC, idle storage is analytically optimal even with declining tiers.

### Industry

The [signed rate book](https://www.cityofindustry.org/DocumentCenter/View/226/IPU-Rate-Information-PDF), Resolution 2023-01 effective February 1, 2023, verifies domestic D. The supported study window is January 2025–September 20, 2026. Daily customer charges distinguish individual single-family and multifamily meters; energy, public-purpose and state charges are itemized. No local UUT is applied for ordinary Industry service. Eligibility requires a confirmed ordinary domestic contract and complete 27–33-day cycle. Flat positive import prices make idle storage optimal with equal terminal SOC.

The official site’s general rules are marked **Draft March 2002**. They are not treated as adopted authority. Commercial A/B/C tables were retrieved, but season definitions and binding contract/rule terms still need verification. IPU serves only part of Industry; overlapping SCE/IPU map evidence remains ambiguous until account confirmation.

### Vernon — required source inputs still missing

The [July 2026 domestic D sheet](https://www.cityofvernonca.gov/home/showpublisheddocument/5269/639173912746630000) was retrieved through the browser despite direct HTTP errors. It contains base charges and points to separate ECA/renewable adjustments; the 3% in-lieu amount is already embedded in base rates.

The [August 15, 2023 council packet](https://cityofvernon.primegov.com/Public/CompiledDocument/4701) and [adopted minutes](https://cityofvernon.primegov.com/Public/CompiledDocument/5016) establish Resolution 2023-19. It sets prospective ECA factors but expressly permits monthly recalculation and true-up. Those coefficients alone do not prove actual monthly billing factors. The official June 2025 newsletter, archived with the [state water report](https://ear.waterboards.ca.gov/Home/ViewCCR?PwsID=CA1910167&Year=2024&isCert=true), verifies renewable adjustment .0200/kWh for July–December 2025. It does not supply the complete matching ECA history or 2026 renewable values. VPU remains disabled pending matching dated adjustments, application/tax rules and complete schedule reconciliation; missing riders are not assumed zero.

### SCE generation providers

[CPA residential](https://cleanpoweralliance.org/residential-rate/) and [commercial](https://cleanpoweralliance.org/commercial-rate/) schedules distinguish products and enrollment vintages. Generation rates exclude SCE delivery, GMS and CCA-CRS. CPA source pages also advertise a newer TOU-SMART pilot, so one generic “CCA rate” is insufficient. PRIME and Pomona joint-rate comparisons encountered during research are averages, not billing coefficients. CEU needs the accepted agreement’s actual generation tariff. Full SCE unbundled delivery and applicable vintage-specific riders must reconcile before any actual CCA/CEU bill is enabled. Existing hypothetical bundled comparisons remain explicitly labeled.

## Validation and promotion

See `LA_County_Handoff.md` for test outcomes, browser study IDs and engine pins. Territorial unit fixtures exercise resolver behavior, not address-level proof of service. No anonymized GWP customer bill was supplied; numerical fixtures are independent hand calculations against the official schedule.
