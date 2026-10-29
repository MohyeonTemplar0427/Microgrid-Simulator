# FirstEnergy Pennsylvania — Penn Power RS and GS-Small

Reviewed October 29, 2026. The shared backend/local browser implements ordinary
**Penn Power RS residential and GS-Small (GS-S) default Price-to-Compare supply**.
Component intersections cover **January 2025–June 2026 and October 2026**, complete
matching calendar service/bill months only. **July–September 2026 DSIC remains
unverified and rejects**. No neighboring-district or current-price substitution.

Read the [source guide](utility_sources/penn_power_pa/README.md),
[source pins](utility_sources/penn_power_pa/sources.json),
[delivery research](utility_sources/penn_power_pa/delivery_research.md),
[supply research](utility_sources/penn_power_pa/supply_research.md),
[rules review](utility_sources/penn_power_pa/tax_rules_research.md) and
[implementation acceptance](Penn_Power_Pennsylvania_Implementation_Validation.md).
Originals/large receipts stay in ignored evidence storage. Runtime prices and
provenance are self-contained literals; the engine does not read those caches.

## Account and operating scope

RS is standard single-phase service for **one family unit per meter**, solely
residential. Same-meter business use belongs on General Service; Penn Power has
no Met-Ed/Penelec 2,000-W mixed-business allowance. Farms, multiple meters and
special-service provisions are excluded. Solely residential sales-tax exemption
is separately established. One 120/240V secondary service and unity billing PF
are explicit account facts, not inferred from weather coordinates or classification.

The initial RS scope independently confirms inactive special-demand/excess-demand
ratchet treatment, prior-eleven 15-minute peak bounds≤25kW, and native/current
import peaks≤25kW. The general tariff charges $2.25 per excess kW over25, with a
75% preceding-eleven excess ratchet; that active branch is not modeled. Peak
history is not erased by PV. Demand-metering triggers and inactive-charge bounds
are distinct facts; these restrictions do not prove interconnection approval.

Penn Power GS-S availability explicitly mentions single-meter loads≤1,500kWh.
Existing consumption over1,500 in two consecutive months in the latest twelve
may lead to Company reassignment. The simulator additionally requires Company-
retained existing GS-S classification, no demand meter, actual metered usage,
prior-twelve qualification bounds≤1,500 and separate native/import cycle energy
≤1,500. Gross/native/NEM-net qualification interpretation remains unresolved;
these conservative bounds do not assign a class from optimized purchases.
Adjacent state carries the conservative envelope without PV-derived resets.

**Historical GSDS/hourly assignment is a separate review.** Penn Power's marked
General Provision B includes the stated historical500kW, otherwise-GP/TP and
without-contract circumstances that require HP service. No invented twelve-month
GSDS lookback is used. Initial default PTC requires independent review/source for
all applicable qualification history and confirmation that mandatory hourly
assignment does not apply. Current small load or PV does not establish that fact.
HP/TOU/hourly/alternative supply calculations remain unsupported.

GS-S excludes fixed/imputed-usage provision C, early termination, mixed-service
separation, highly fluctuating loads with added transformer/capacity fees and
combined/three-phase arrangements or customer lighting gear. Preserved official
June2024 Original67 literally labels **F. THREE-PHASE**; current Original67 labels
the same body **C. THREE-PHASE**. Independent normalized-body comparison and visual
review confirm identity. This resolves the actual clause from source text, not
paragraph-order inference. Its ordinary single-phase branch has no separate F
price; the additional arrangements are outside this implementation.

Tax locality is independently PA state-only, outside Philadelphia/Allegheny, with
no business exemption/apportionment or special fee/rate/assistance arrangement.
Ordinary GS current charges use6% sales tax; RS solely residential is exempt.
PJM **ATSI** zone and **FE-ATSI** emergency control-area labels remain separate
from Penn Power district, supplier, eligibility, locality and wholesale prices.
The emergency source's state cell says OH despite naming Penn Power; it is
preserved verbatim, while PA jurisdiction comes from the tariff independently.
No pricing node, ownership, PLC/NSPL or wholesale LMP charge is inferred.

## Rates and calculation

| Component | Ordinary Penn Power RS / GS-S rule |
| --- | --- |
| Base delivery | RS $11.00/month +$0.05480/kWh; GS-S $30.04/month +$0.04817/kWh |
| PTC Jan–May2025 | $0.11168 / $0.12098 per kWh |
| PTC Jun–Nov2025 | $0.11857 / $0.12726 per kWh |
| PTC Dec2025–May2026 | $0.12606 / $0.13729 per kWh |
| PTC Jun–Oct2026, subject to rider coverage | $0.13477 / $0.13729 per kWh |
| DSS Jan–May2025; Jun2025–May2026; fromJun2026 | $0.00221/$0.00042; $0.00264/$0.00084; $0.00116/−$0.00080 per kWh |
| EEC over those same windows | $0.00215/$0.00400; $0.00228/$0.00129; $0.00189/$0.00296 per kWh |
| Residential USC only | $0.00646/kWh Jan–Jul2025; $0.01003 Aug–Dec2025; $0.01236 in2026 |
| Monthly smart meter | 2025 RS −$0.01 / GS-S $1.83; 2026 RS $0.03 / GS-S $0.20 |
| TCJA | Positive1.59% Jul–Dec2025 on base customer+distribution energy only; zero Jan–Jun2025 and2026 |
| STAS | +0.01% in2025; −0.01% in2026, after other tariff riders/DSIC/PTC |
| DSIC | Zero in2025 and Jan–Mar2026; +0.16% Apr–Jun2026; +2.40% Oct2026; Jul–Sep gap |
| LEDC | Mandatory all ordinary billing units: $0.00004/kWh both plans Apr2025–Mar2026; $0.00009/$0.00008 fromApr2026 |
| SPVRC | Explicit Penn Power zero Jan–May2025; later published standalone zero/recovery inside DSS, no duplicated charge or copied neighboring credit |
| January2025 prior-cost refund | RS −$6.19 once when entitled; historical GS row −$4.84 only with separately confirmed exact legacy entitlement |

Published PTC includes its GRT, administration, losses, capacity/AEPS and supply
transmission/reconciliation components. Nonbypassable DSS is separate once.
Penn Power PTC loss factor1.0661 is not the HP GS-S1.0515 factor. Neither factor
is multiplied into the already-final PTC price again. The adopted June2025 DSS
replacement controls over the superseded initial high-precision submission.

TCJA has a base-only definition. DSIC applies to applicable delivery including
DSS/LEDC and other riders, excluding PTC/STAS; STAS includes PTC and DSIC; current
GS sales tax follows. Acceptance independently reconstructs the bases rather
than trusting self-reported metrics. Negative SMT/DSS remain signed.

**January–March2025 LEDC non-applicability is a disclosed source-date inference**:
Original245's first rate window is April1,2025, Original247 defines April annual
computational changes and the adopted First Revised245 starts April1. No explicit
Jan–Mar zero-priced row was recovered. Zero charge denotes no applicable pre-April
window under that interpretation, not an April rate backfill or provisional zero.

Supplement28 prints a May30,2026 PTC endpoint; Penn Power-specific actual December
and April shopping inserts corroborate identical prices throughMay31. The June2025
insert has correct June prices but a wrong May2026 endpoint; filed November30
controls. Source discrepancies and workbook June-year header errors are retained.

## January refund, minimum and evidence limits

January2025 refund eligibility/source is independent of a prior-refund-represented
model-state flag. GS-S additionally requires a separate assertion/source tying
this established account to the historical **Penn Power GS row and exact $4.84
entitlement**. Current GS-S membership alone does not prove the old-to-new mapping.
Without that independent fact, January GS rejects rather than assuming a refund,
zero or universal mapping. Explicit hypothetical accounts state that exact legacy
fact. Refunds apply after current tax, once, with adjacent carried model state.

**January GS-S remains a verified-charge subtotal:** current6% tax and the known
confirmed4.84 refund are included; the unresolved prior-refund sales-tax adjustment
is explicitly excluded, never assigned zero. Annual GS totals retain that mixed
complete/subtotal scope and do not claim a complete annual amount due. RS ordinary
January may include its confirmed6.19 refund within complete modeled components.
No negative-refund-balance/bank settlement is invented.

The inactive-minimum guard rejects when raw or component-cent current charges
before tax/refund fall below the customer amount. It is narrower than a complete
tariff minimum formula. The negative2025 RS SMT makes some zero-import cases
unsupported; imports are not forced to manufacture a passing bill and refunds
are not clipped. Exact provider quantity/cash rounding and actual complete
customer-invoice calibration are unverified. Half-up component cents and raw
primary-cost proofs do not prove a minimum rounded-cash invoice.

## PV/storage and validation

PV/storage needs already-active qualified ordinary renewable NEM/interconnection,
proper metering, retained underlying class/default supply and no Partial Services
Rider/special recurring fee treatment. Small size/non-export operation does not
prove approval or an exemption. No Penelec-specific legacy facility clause is
imported. Storage charges from PV only, with no battery export, zero exports and
opening bank, and no standalone-battery/export-credit/cashout/aggregation model.
Grid-only removes DER facts while preserving classification, GSDS and refund history.

Use the targeted policy: independent literal arithmetic, source/date/eligibility,
percentage bases, numeric/symbolic parity, missing data/DST, dispatch/SOC/state,
queued worker, save/restore/CSV/ZIP and one frozen new-utility matrix plus concise
browser pass. Full2025 and selected2026 studies use hypothetical account/load facts
and historical ERA5, with representative OpenDSS replay. They do not establish
actual customer savings, site-specific engineering approval or jointly optimized
annual/rounded-cash optima. Earlier utility evidence keeps its own pins; the
previously recorded Met-Ed LEDC issue remains separate and unmodified.
