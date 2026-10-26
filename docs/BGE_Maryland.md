# BGE Maryland residential and small commercial

Reviewed October 25, 2026. Local development on `main`; no stable-engine
promotion, public deployment or actual-account certification. Shared backend and
local browser only; desktop GUI development and GUI checks remain paused.

## Executable account and date scope

| Plan | Supply | Verified complete calendar cycles | Amount reported |
| --- | --- | --- | --- |
| R residential | BGE residential Standard Offer Service | January 2025–October 2026 | Recurring tariff subtotal; historical-account legislative relief refunds excluded |
| G ordinary secondary General Service | BGE Type I Standard Offer Service | January 2025–October 2026 | Ordinary utility bill within the selected account and tax restrictions |

Schedule G has flat delivery and flat SOS energy prices. Elective GS has
time-of-use SOS and is outside this implementation. Neither plan here has a
customer demand charge. G Type I eligibility uses 30-minute demand and prior
billing-month consumption; a low simulated peak does not establish membership.
Existing utility-assigned Type I membership must be explicitly confirmed. The
bounded study additionally keeps 30-minute imports below 25 kW and imported
energy at most 6,000 kWh each October–May month or 7,500 kWh each June–September
month. The winter restriction is deliberately stricter than the tariff's
two-consecutive-month trigger. No automatic service-type reassignment occurs.

The selected locality is explicitly confirmed **unincorporated Anne Arundel
County, outside Annapolis and Highland Beach**. Utility service, Maryland
jurisdiction, BGE SOS supplier, tax locality, and approved ordinary interconnection
are separate account facts. The hypothetical weather coordinates do not prove
any of them. [PJM's region index](https://emergencyprocedures.pjm.com/ep/pages/regions.jsf)
identifies BGE as a Maryland transmission zone. That is metadata; a pricing node is optional
and independently sourced. No wholesale price, inferred capacity tag or extra
transmission obligation enters an ordinary SOS bill.

Only one secondary single-phase 120/240-V meter/service at unity power factor
is supported by this initial billing/electrical study. G retains an explicitly
confirmed utility-assigned annual delivery-charge band of $175–$1,299, producing
a $1.85 monthly Universal Service Charge (USC). R USC is $0.32. That inherited
G assignment stays fixed across scenarios and independently documented billing
years; no tier is recomputed from optimized usage. The tariff's reclassification
timing was not recovered, so the simulator does not predict future USC bands.

## Components and billing clocks

Snapshot-safe Python literals in `src/billing/bge_md_rates.py` preserve each
monthly generation, transmission, Rider 8 energy-cost adjustment, Rider 25
monthly adjustment, Rider 10 administrative credit, and Rider 16 MYP factor.
The base customer/energy and EmPOWER Riders 2/15/26 use the appropriate 2025
or 2026 version. R16 applies January–February 2025, is zero March 2025–January
2026, and resumes February 2026. R34's offset expired December 2024; ERI is zero
through the verified ledger. Neither is silently carried forward as a charge.

The official 2026 G component ledger groups DR into its row labeled Rider 2.
The separate filed riders establish $0.03526/kWh EE, $0.00027 DR and $0.00013
PTR; their $0.03566 total is charged once. Residential 2026 EmPOWER totals
$0.01310/kWh. Generation includes its published administration/tax components;
transmission includes applicable GRT/PSC assessment. No second percentage PSC
assessment or wholesale/capacity charge is added to those published prices.

Only complete consecutive 15-minute calendar service cycles whose designated
billing month matches the service month and whose hypothetical bill date is
the final service day are accepted. This avoids inventing the allocation of
monthly billing factors across shifted service dates. Partial/extended cycles,
cross-month rate allocation, future months and missing intervals reject. Local
calendar dates and actual timestamp counts preserve 92/100-interval DST days.

`src/billing/bge_md.py` shares the identical charge expressions between numerical
bills and the regional dispatch objective. Original component arithmetic is
retained; the shared regional statement view rounds each named modeled component
half-up to cents. The utility may group components differently, so itemized
rounding is reconciled explicitly rather than advertised as an exact printed
statement match. EES is separately rounded half-up as specified by COMAR.

## Taxes and residential refund boundary

Both plans include franchise $0.000620/kWh and EES $0.000150/kWh, with EES capped
at $1,000 per account/month. Anne Arundel residential electricity is exempt from
county and ordinary state sales tax. Ordinary G adds county tax $0.0025/kWh
and state sales tax 6%. Maryland's taxable-price rules exclude the separately
stated county tax and EES. The modeled state base includes ordinary supply,
delivery, riders, USC and passed-through franchise consideration. This follows
the cited statutory/COMAR rules; no actual G statement was recovered to
independently calibrate that tax-base interpretation.

Residential legislative relief is an account-history-dependent refund, separate
from recurring rates. The 2025 summer phase and 2026 winter phase use eligibility
and historical usage, and their exact account posting cycles are unverified.
The current winter tiers are not reused for summer. No blanket $80 credit is
invented. R always returns `is_complete_bill=false`, with exactly
`account_specific_legislative_relief_refund` in `excluded_components`, explicit
warnings and a verified-subtotal objective label. The same account facts are
retained across grid-only/PV/storage; study usage never manufactures refund
eligibility or an amount. Annual R totals therefore do not claim a complete
customer amount due. G is not assigned a residential relief credit.

## PV/storage and unsupported accounts

The existing regional PV, AC-coupled battery, isolated worker, saved-study and
representative OpenDSS paths are reused. Approved ordinary renewable service
without standby/special charges must be confirmed; combined PV/battery nameplate
is bounded to 25 kW. Exports are zero and surplus PV is curtailed. An absent-DER
grid reference removes the renewable installation assertions while preserving
ordinary tariff, tax and USC facts. No NEM/export credits, energy bank, annual
settlement, standalone storage, GS TOU, Type II/hourly SOS, third-party supplier,
primary/three-phase metering, assistance/opt-out, special exemption or another
local jurisdiction is inferred.

Historical dispatch has perfect foresight within each meter cycle, with SOC
carried between cycles and equal initial/final energy at the annual boundary.
It does not prove a jointly optimized annual minimum or a practical day-ahead
strategy. Representative steady-state network replay is separate from billing
and does not certify a surveyed site, inverter dynamics or protection.

## Sources and validation

[The source ledger](utility_sources/bge_md/sources.json) pins original PDFs,
physical pages, extracted records and hashes. The three focused research notes
retain [supply](utility_sources/bge_md/supply_research.md),
[delivery/riders](utility_sources/bge_md/delivery_research.md) and
[taxes](utility_sources/bge_md/tax_research.md), including blocked/superseded
routes. The official historical CSEG ledger is used as a published component
and independent arithmetic source; it does not enable community-solar credit
or export settlement. Original PDFs remain in ignored `.cache/bge_md/sources/`.

All 44 published R/G monthly variable composites are independent benchmarks.
Literal component and tax-base fixtures, numerical/symbolic parity, Type I
boundaries, source/date/account rejection, DST, missing data, main form/worker
and saved-artifact checks are in `test/test_bge_md.py` and
`test/test_bge_integration.py`. The legislative 901-kWh example verifies delivery
and tax components only; its blended service-cycle supply is not forced into
a complete-calendar September benchmark. Frozen release, historical scenarios,
source identities, browser evidence and limitations are recorded in
[implementation validation](BGE_Maryland_Implementation_Validation.md).
