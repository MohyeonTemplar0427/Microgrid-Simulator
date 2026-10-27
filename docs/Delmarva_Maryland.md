# Delmarva Maryland R and estimated-demand SGS-S SOS

Reviewed October 26, 2026. Shared backend/local-browser implementation on `main`;
no stable-engine promotion or public deployment. Desktop GUI development is paused.

## Executable dates and bill scope

R residential SOS and SGS-S Type I SOS support complete, matching calendar
service/billing months in **January–June 2025, September 2025 and May–October
2026**. Both report `is_complete_bill=false`, explicit `excluded_components`
and the `verified_charges_subtotal` objective. R excludes unrecovered residential
RGGI/RRC and legislative relief/refunds. SGS-S excludes unresolved Maryland state
sales-tax base/bracket calculation. These amounts are not zero or exemptions;
no complete amount due, complete-bill savings or complete-bill optimum is claimed.

Full-year 2025 is unsupported. July 2025 crosses the July 2 filed MES change;
August 2025 crosses the August 27 transmission change. Allocation of those
crossing cycles has not been independently verified, so they reject. October
2025–April 2026 monthly BSA/PCA/administrative-credit history is incomplete.
November–December 2026 is outside verified coverage. Known base/generation rates
alone do not authorize a bill; no neighboring or current rates fill gaps.

## Independent account facts

The initial jurisdiction is explicitly confirmed **unincorporated Wicomico
County, Maryland**, with ordinary residential/business status and no additional
local energy levy. The county code and DLS county tax inventory support that
absence as a documented code-based inference, not an express zero-tax certificate.
Actual locality and tax status still require separate confirmation. The
hypothetical weather point 38.40 N, 75.65 W assigns neither utility service nor
county boundaries. Municipalities, special exemptions/charges and other localities
are outside this scope.

Delivery utility, SOS supplier, tariff eligibility, tax locality, interconnection
and PJM metadata remain separate. The [PJM region index](https://emergencyprocedures.pjm.com/ep/pages/regions.jsf)
lists **DPL** as a transmission zone covering DE, MD and VA. It selects neither
Delaware/Virginia retail tariffs nor a wholesale node. No wholesale LMP/PLC/NSPL
charge is added to retail SOS.

One ordinary secondary 120/240-V single-phase meter/service at unity billing
power factor is selected. Competitive supply, Type II/hourly SOS, off-peak
contracts, opt-out, assistance, special facilities, standby and assessed/tested
or metered SGS-S demand are unsupported.

## SGS-S estimated-demand boundary

SGS-S is a demand-priced delivery plan. Its ordinary distribution charge is
$26/month plus $0.041549/kWh and **$4.303679 per billed kW** in the selected
versions. It is not Pepco's non-demand GS plan.

Schedule SGS-S E.3 permits the utility to estimate demand for accounts below
20 kW as monthly kWh divided by 175 hours, capped at 20 kW. E.1's nearest-whole-kW
measurement explicitly excepts E.3; no invented rounding rule is applied to the
estimate. The utility must already have assigned this method and approved its
retention across grid-only, PV and PV/storage scenarios. Simulation results do
not choose the method or establish account eligibility.

This first implementation limits **each scenario's monthly imports to 3,500 kWh
and actual 15-minute import peak below 20 kW**. Thus estimated billed demand is
exactly kWh/175, never above 20 kW. Distribution demand is charged; transmission's
first 20 kW demand block is free, while its first 3,500 kWh energy block is
charged. Metered/assessed demand, half-kW rounding ties, imports above 3,500 kWh,
off-peak contracts and other options reject. The minimum monthly customer charge
is inactive beyond the already included customer line because the selected net
variable composites and demand rate are nonnegative.

Independent existing Type I assignment includes historical demand/usage and
annual utility reassignment; modeled usage does not prove it. The filed
classification thresholds include 25 kW, two consecutive winter months above
6,000 kWh (October–May), or one summer month above 7,500 kWh. The stricter study
bounds avoid a modeled transition but do not reconstruct prior history.

USC is $0.32/month residential. SGS-S selects only the independently assigned
$175–$1,299 annual utility-delivery band, $1.85/month. Separate 2025/2026 evidence
must confirm the band throughout each year, before/after its first-quarter update.
The optimizer retains the band across scenarios instead of recomputing it.

## Components, dates and taxes

The frozen Python rate table preserves generation energy, supply administration,
PCA, retail transmission energy, distribution energy, BSA, MES, EmPOWER,
administrative delivery credit, franchise tax and MYP separately. Fixed customer
and USC charges and SGS-S distribution demand are additional. CSEG publications
supply component/arithmetic evidence only; no community-solar or export
settlement is enabled. All retail signs reverse the credit-sheet signs.

Gross receipts tax is **embedded in applicable Delmarva rates** according to
the filed/CSEG footnotes. No additional 2.0408% Pepco-style multiplier is applied.
The franchise line is $0.000620/kWh. R is residential sales-tax exempt under the
filed schedule; SGS-S state sales tax remains visibly excluded because the exact
compound base/statutory bracket calculation lacks an independent benchmark.

The actual filed retail MES is $0.000150/kWh before July 2, 2025, $0.000151 after
that date, and $0.000150 from July 1, 2026. The July 2025 and July 2026 original
filings pin those dates. No inferred gross-up decomposition or substitution of
the statutory assessment cap for the filed retail factor is claimed. R monthly
imports are limited to 7,500 kWh so the MES $1,000 cap is inactive; this is a
study-domain restriction, not residential tariff eligibility.

Transmission changed August 27, 2025 and September 1, 2026; the latter aligns
with a calendar boundary. The February 3, 2025 delivery filing changes the printed
rate-year endpoint but retains identical R/SGS-S prices, so no numerical delivery
split is needed. The February 1 supply-administration change is distinct.
Published July–October 2026 CSEG rows independently state MYP credits; their use
does not extend the standalone leaf's earlier printed end date by inference.
MCAM-S concerns one-time interconnection fees, not an invented recurring rider.

Ordinary meter cycles are 25–35 days; the selected 28–31-day calendar cycles use
one monthly fixed charge. Other periods, shifted bills and unverified component
crossings reject rather than applying generic daily proration.

## PV, storage and evidence

PV/storage requires separately approved ordinary parallel service with no standby
or special recurring charges. Schedule S's small-self-generation exclusion does
not alone establish interconnection approval. This implementation additionally
limits combined PV/storage nameplate to 25 kW. Standalone storage, export/NEM
credit banks, cash settlement and community solar are unsupported. The grid-only
counterfactual removes DER assertions while retaining tariff, supplier, estimated
billing method and USC assignment; it is not an actual enrollment transition.

Shared regional billing/dispatch, immutable workers, PV/weather, saved CSV/ZIP and
representative OpenDSS replay are reused. Numeric and symbolic bills use the
same charge expressions. The strategy rolls across cycles with continuous SOC
and restores initial energy at the final boundary; it is not a joint annual
optimum. Battery wear is separately reported and excluded from the objective by
default. Synthetic loads/weather reanalysis and representative circuits do not
prove actual-account savings or surveyed-site feasibility.

Sources, original hashes, physical pages, rejected/proposed documents and scoped
excerpts are in [the source ledger](utility_sources/delmarva_md/README.md).
Validation and immutable candidate identity are recorded in
[the implementation report](Delmarva_Maryland_Implementation_Validation.md).
