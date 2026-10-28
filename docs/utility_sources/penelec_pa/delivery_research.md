# Penelec Pennsylvania delivery evidence, reviewed 2026-10-28

Penelec RS residential and GS-Small secondary non-demand default-supply delivery components were read from the **Penelec** columns of adopted FEPA tariff originals. The current checkout was `main`, clean at orientation; no Git or previous-utility evidence was modified. The [official tariff index](https://www.firstenergycorp.com/customer_choice/pennsylvania/pennsylvania_tariffs.html) was checked today. Twenty-three retained original hashes were checked before reuse; the final delivery packet retains 18 applicable originals/index/workbook references and 44 page excerpts. Every excerpt page was rendered and visually reviewed, including the class matrix and mandatory LEDC chain.

Private machine packet: `.cache/penelec_pa/sources/delivery/delivery_snapshots.json`; receipt list: `delivery_records.json`; full extracted texts, PNG originals and eleven contact sheets remain in that directory. Checked-in page text is under [delivery/](delivery/). Each component has URL, original SHA256, physical and printed page, revision and excerpt SHA256. Existing originals remain in `.cache/firstenergy_research/` or `.cache/met_ed_pa/sources/delivery/`; they were reused without changes or duplicate downloads.

## Verified component values

All variable amounts below are **USD/kWh**, fixed amounts USD/month, and percentages retain their filed signs. The packet has exact per-component date/source pins.

| Component | Period | RS | GS-S |
|---|---|---:|---:|
| Customer | Jan2025–Oct2026 | 11.25 | 20.87 |
| Distribution energy | Jan2025–Oct2026 | .06815 | .04262 |
| DSS | Jan–May2025 | .00854 | .00445 |
| DSS | Jun2025–May2026 | .00798 | .00362 |
| DSS | Jun–Oct2026 | .00375 | .00056 |
| EEC | Jan–May2025 | .00209 | .00362 |
| EEC | Jun2025–May2026 | .00286 | .00253 |
| EEC | Jun–Oct2026 | .00222 | .00429 |
| USC | Jan–Jul2025 | .01049 | residential only |
| USC | Aug–Dec2025 | .01699 | residential only |
| USC | Jan–Oct2026 | .01844 | residential only |
| Smart meter fixed | 2025 | .01 | 1.44 |
| Smart meter fixed | 2026 | .05 | .09 |
| SPVRC | Jan–May2025 | −.00001 | −.00001 |
| SPVRC | Jun2025 onward | 0 | 0 |
| LEDC | Apr2025–Mar2026 | .00022 | .00016 |
| LEDC | Apr–Oct2026 | .00007 | .00006 |
| January2025 refund, once | bills rendered Jan2025 | −6.15 | −3.42 |

STAS is **+.01%** for 2025, **−.02%** for 2026. TCJA is zero Jan–Jun2025, **+3.04%** Jul–Dec2025, zero in2026. The positive table value and `(I)` indicator control despite generic prose calling this a negative surcharge.

DSIC: Jan–Mar2025 0%; **Apr–Jun2025 −.01%**; Jul–Dec2025 0%; Jan–Mar2026 0%; **Apr–Jun2026 .39%**; **Oct2026 2.70%**. July–September2026 has no recovered adopted tenth-revision leaf and remains unsupported. Ninth/eleventh revisions must not be extended across that gap.

## Mandatory LEDC and replacement traps

LEDC is nonbypassable for all listed residential/commercial billing units, including ordinary RS and GS-S; it is not limited to a customer's own streetlight conversion. [First revised245](delivery/pa-20250515174716_p246.txt), Supplement17, effective April1,2025, establishes .022/.016 cents per kWh; [second revised245](delivery/tariff_current_p246.txt), Supplement34, effective April1,2026, establishes .007/.006 cents per kWh. Units above are divided by100 to USD/kWh. Include LEDC in DSIC/STAS/current commercial sales-tax bases under the separately reviewed ordering rules.

**January–March2025 LEDC:** the numeric zero is labeled `NOT_APPLICABLE_BEFORE_FIRST_APRIL_COMPUTATIONAL_PERIOD`. This is an explicit start-date/absence interpretation, not an explicit zero-priced January row. Newly introduced [Original245](delivery/papuc-1858451_p91.txt) has a January1 footer but restricts the first billed rate window to April1,2025; [Original247](delivery/papuc-1858451_p93.txt) defines the April-to-March computational period and April1 annual changes. The first positive revision begins April1. Independent rules review confirms no pre-April billed period. Do not carry Original245's April provisional zero into April2025, or backfill April's positive rates into January.

DSS [fourth revised213](delivery/pa-20250612040318_p213.txt) supersedes the initial third-revision June2025 table: use .00798/.00362, not .00800/.00365. The same fourth revision is retained in the dated January2026 official book. Its annual computational rule is June1–May31. PTC supply is separate and owned by the supply research stream; no extra wholesale, PLC or transmission amount should be inferred from DSS's industrial columns.

The [refund calculation](delivery/papuc-1858401_p4.txt) and [PUC acceptance](delivery/papuc-1860899_p1.txt) establish Penelec's −6.15/−3.42 once in January2025 on a bills-rendered basis, already GRT-inclusive. January commercial tax adjustment attributable to the earlier refunded charges is unverified: retain that exclusion explicitly and label January/annual GS totals as verified subtotals. Do not call that unknown adjustment zero.

SPVRC's Jan–May credit remains for RS/GS-S with approved renewable equipment: [self-generation exclusion234](delivery/pa-june2024_p234.txt) applies only to GS-Large, GP and TP. The later zero SPV balance is already within DSS, not an additional positive charge.

## Account, billing and coverage boundaries

[RS61](delivery/papuc-1858451_p15.txt) and [GS-S65](delivery/papuc-1858451_p17.txt) establish the base prices. GS-S is Company-assigned non-demand-metered service; the two-consecutive-months-above1500 rule uses recent twelve-month history. Penelec's GS-S general-provision matrix selects **A and C**, including discretionary fixed/imputed usage C; initial executable scope must expressly exclude C and independently confirm metered quantities. Do not import PennPower's GSDS/500kW provision. RS general provisions select A(2), without the adjacent districts' farm branches.

[RS62](delivery/tariff_current_p62.txt) has special demand **3.26USD/kW above25kW**, a15-minute determination and75% preceding-eleven-month excess-demand ratchet. Any narrow inactive envelope needs separate utility/history facts, current/native peak bounds and retained state; PV-reduced purchases do not reset qualification or history. [GS-S66](delivery/tariff_current_p66.txt) and RS62 state customer/energy/applicable-rider minimum wording; the rules stream owns ordering and any restricted inactive minimum domain. No fabricated general tariff floor or forced-import rule follows from this note.

Delivery intersection: complete matched calendar service/billing months **Jan2025–Jun2026 and Oct2026**, subject to account/rules/supply/tax confirmation. All2025 variable delivery components are sourced, including LEDC. A full-year GS result still has the January prior-refund-tax exclusion. July–September2026 DSIC, irregular proration, special/fixed-imputed classes, export banking and unverified DER approvals remain outside scope. Current dated leaf evidence is not by itself historical validation or proof of actual customer eligibility.

One targeted official July2026 DSIC search found current/legacy material but no adopted quarter leaf; the unchanged route was stopped. The historical-rate workbook contains PTC/HP/scaling sheets, not a replacement for the missing DSIC leaf. No official whole-invoice benchmark was recovered in this bounded delivery pass; source-valued arithmetic fixtures may be built from these literals, while supply owns its independent published PTC benchmark. Existing Met-Ed evidence omitted LEDC and was reported to the parent as a separate discovered limitation; none of those frozen receipts was altered.
