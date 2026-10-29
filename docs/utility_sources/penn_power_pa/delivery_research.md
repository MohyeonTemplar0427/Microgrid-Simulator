# Penn Power Pennsylvania delivery evidence — 2026-10-29

Penn Power RS residential and ordinary GS-Small secondary default-supply delivery prices were independently read from the **Penn Power** columns of the adopted FEPA originals. Checkout was `main`, clean at orientation; no Git, runtime, tests or prior utility evidence was modified. The [official tariff index](https://www.firstenergycorp.com/customer_choice/pennsylvania/pennsylvania_tariffs.html) was checked today. Eighteen retained original/index/workbook hashes were verified before reuse; 49 source pages were excerpted, rendered and visually reviewed. The old book's applicability to Penn Power was checked separately from its applicability to other FEPA districts.

The private machine packet is `.cache/penn_power_pa/sources/delivery/delivery_snapshots.json`, with `delivery_records.json`, extracted texts, page PNGs, render inventory and contact sheets in the same folder. Checked-in page text is in [delivery/](delivery/). Every component identifies original URL/SHA256, physical and printed page/revision, and excerpt SHA256. Originals remain at their existing `.cache/firstenergy_research/` or `.cache/met_ed_pa/` paths, read-only. No duplicate tariff downloads were made.

## Filed literal prices

Variable rates below are **USD/kWh**, smart meter/customer rates are USD/month. Supply/PTC is separate and researched by the supply stream.

| Component | Period | RS | GS-S ordinary |
|---|---|---:|---:|
| Customer | Jan2025–Oct2026 | 11.00 | 30.04 |
| Distribution | Jan2025–Oct2026 | .05480 | .04817 |
| DSS | Jan–May2025 | .00221 | .00042 |
| DSS | Jun2025–May2026 | .00264 | .00084 |
| DSS | Jun–Oct2026 | .00116 | **−.00080** |
| EEC | Jan–May2025 | .00215 | .00400 |
| EEC | Jun2025–May2026 | .00228 | .00129 |
| EEC | Jun–Oct2026 | .00189 | .00296 |
| USC | Jan–Jul2025 | .00646 | residential only |
| USC | Aug–Dec2025 | .01003 | residential only |
| USC | Jan–Oct2026 | .01236 | residential only |
| Smart meter fixed | 2025 | **−.01** | 1.83 |
| Smart meter fixed | 2026 | .03 | .20 |
| SPVRC | All sourced periods | **0** | **0** |
| LEDC | Apr2025–Mar2026 | .00004 | .00004 |
| LEDC | Apr–Oct2026 | .00009 | .00008 |
| January2025 refund, once | eligible established account | −6.19 | **−4.84, conditional historical GS row** |

STAS: **+.01%** in2025; **−.01%** in2026. TCJA: zero Jan–Jun2025; **+1.59%** Jul–Dec2025; zero in2026. The positive filed table and `(I)` indicator control despite generic prose describing a negative surcharge.

DSIC: **0% throughout2025**; **0% Jan–Mar2026**; **.16% Apr–Jun2026**; **2.40% Oct2026**. The adopted tenth-revision239 July–September2026 leaf was not recovered. Do not extend April or October rates across that gap. One targeted official utility/PUC search found only current/earlier material; that unchanged route was stopped. The historical-rate workbook contains PTC/HP/scaling sheets, not a DSIC substitute.

[Base61](delivery/papuc-1858451_p15.txt) and [base65](delivery/papuc-1858451_p17.txt) are Supplement14 first-revision leaves, effective January1,2025, retained unchanged in the current book. [STAS182 second revision](delivery/pa-20250515174716_p182.txt), Supplement15, supersedes the same-effective initial Supplement14 zero. Current third-revision182 is the2026 −.01% row.

## Mandatory LEDC and source replacements

LEDC applies nonbypassably to all listed ordinary class billing units, independent of an individual lighting conversion. [First revised245](delivery/pa-20250515174716_p246.txt), Supplement17, effective April1,2025, gives .004/.004 cents per kWh; [second revised245](delivery/tariff_current_p246.txt), Supplement34, effective April1,2026, gives .009/.008 cents per kWh. Divide cents by100 for USD. Include LEDC in the independently reviewed DSIC/STAS/current commercial sales-tax bases.

**January–March2025 LEDC:** packet status `NOT_APPLICABLE_BEFORE_FIRST_APRIL_COMPUTATIONAL_PERIOD` explicitly records a start-date/absence interpretation, not an explicit January zero-priced row. Newly introduced [Original245](delivery/papuc-1858451_p91.txt) has a January1 footer but restricts its first billed rate window to April1,2025; [Original247](delivery/papuc-1858451_p93.txt) defines the April-to-March computational period and April1 annual changes; first positive charges start April1. Do not extend the provisional zero table into April or backdate positive April rates into January.

[DSS fourth revised213](delivery/pa-20250612040318_p213.txt) replaces initial [third revised213](delivery/pa-20250515174716_p213.txt): **.00264/.00084**, rather than .00266/.00085, from June1,2025. The same fourth revision is independently retained in the dated [January2026 book](delivery/pa-2026-01_p213.txt). Annual DSS computational periods run June1–May31. The GS-S(GSDS) industrial/demand column is separate from ordinary GS-S and cannot supply its prices.

Penn Power's [SPVRC Jan–May2025 column](delivery/pa-june2024_p231.txt) is explicitly zero. Later standalone and DSS-contained balance rows remain zero. No neighboring district credit or positive rate is substituted. Self-generation exclusion234 is limited to GS-Large/GP/TP; small-class PV checkboxes do not establish any exemption.

## Clocks, formulas and refund boundary

Service-rendered clocks are retained for base, STAS, USC, EEC, SMT, DSS, SPVRC and LEDC. TCJA and January refund use bills-rendered dates. DSIC's [original241](delivery/pa-20250515174716_p242.txt) and [first revised241](delivery/tariff_current_p242.txt) explicitly say **bills-rendered basis**; every DSIC packet row has the exact clock and a corresponding rules pin. Matched complete calendar service/billing cycles avoid unsupported cross-month proration.

TCJA applies to base distribution charges; DSIC to current distribution service, including applicable non-supply riders, excluding STAS; STAS follows all applicable current riders including DSIC. Filed GRT is embedded once. Ordinary PA commercial6% sales tax is separate; statutory residential exemption and locality require independent account facts. Tax/rules review owns the full formula proof and exclusion boundaries.

[Refund calculation physical5](delivery/papuc-1858401_p5.txt) has RS6.19 and a **historical row labeled GS4.84**, including GRT. [PUC acceptance](delivery/papuc-1860899_p1.txt) establishes January2025 bills-rendered, once-per-account treatment. **Current GS-S does not automatically establish entitlement to that historical GS refund row.** January GS can use the known4.84 only with separate utility/account evidence identifying the historical row, eligibility and exact amount/posting. Otherwise that January branch is unsupported; do not invent another amount. Even when entitlement is confirmed, the tax adjustment attributable to earlier refunded commercial charges remains unknown and explicitly excluded. Thus JanuaryGS and an annualGS total including it remain verified subtotals. Refund follows current rider/tax calculation without a second GRT grossup or clipping.

## Supported account intersection and gaps

Delivery component intersection is **January2025–June2026 and October2026**, with the January commercial condition above and the disclosed January–March LEDC applicability interpretation. Runtime coverage additionally requires independently confirmed supply, tax, billing and equipment facts. This is a source recommendation, not historical/electrical validation or actual customer eligibility.

Ordinary RS scope is solely residential, one family unit, one meter and single phase; exclude farmB(2), multiple-meterC and mixed business. [RS62](delivery/tariff_current_p62.txt) has a **2.25USD/kW excess-demand** charge above25kW, 15-minute measurement and75% preceding-eleven-month excess-demand ratchet. A narrow inactive model needs independent no-ratchet/current-demand facts, prior/native/import peak bounds and preserved history; PV does not reset eligibility.

Ordinary GS-S requires Company assignment, actual single-phase metered quantities, retained eligibility and independent recent-twelve-month qualification facts. The two-consecutive-months-above1500kWh rule is not an automatic general hard cap; a conservative prior/native/import<=1500 study envelope may preserve an inactive reclassification domain. [GS-S66](delivery/tariff_current_p66.txt) marks A+B+C+F: exclude early termination, fixed/imputed provisionC, historic500kW GSDS/HP branch and special service by account evidence. **A retained-version label inconsistency is documented:** [June2024 Original67](delivery/pa-june2024_p67.txt) explicitly labels `F. THREE-PHASE`, while the [current Original67](delivery/tariff_current_p67.txt) labels the identical condition body `C. THREE-PHASE`; the preceding two labels likewise move D/E to A/B. Both originals retain the same printed leaf/footer. Lowercase alphanumeric normalization of the complete three-phase body matches exactly; the packet records that comparison and its hash. This is direct body evidence, not a meaning inferred from clause order. Preserve both labels and require actual ordinary single-phase/no combined-metering equipment facts; do not invent an extra fee, rename the filed clause or assign an unknown F a zero rate. [GS-S67](delivery/tariff_current_p67.txt) also describes fluctuating-load transformer facility charge2.1%, separate residential service and three-phase arrangements; those are outside the initial ordinary single-phase account scope.

The negative2025RS monthly SMT is retained. At very low imports it can leave a runtime's deliberately narrower inactive-minimum domain, particularly before the positive July TCJA begins. This is not proof of a universal tariff customer-charge floor: preserve signed prices, reject any unverified minimum-ordering case and never force extra imports merely to satisfy an implementation guard.

July–September2026 missing DSIC, shifted/irregular cycles, alternative supply, fixed/imputed usage, GSDS/special fees, export banking and unverified DER approvals remain excluded. No official whole-invoice benchmark was recovered in this bounded delivery pass; source-literal bill formulas can support independent arithmetic checks, while supply owns published PTC comparison evidence. Prior utility evidence, including the unresolved Met-Ed LEDC limitation, remains untouched and attributed to its original candidate.
