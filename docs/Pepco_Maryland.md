# Pepco Maryland R and GS Standard Offer Service

Reviewed October 26, 2026. This is a bounded local development implementation,
with no stable-engine promotion, public deployment or actual-account certification.
The shared backend and local browser are active; desktop GUI work remains paused.

## Supported dates and amount scope

| Plan | Supply | Executable complete calendar cycles | Amount reported |
| --- | --- | --- | --- |
| R residential | Pepco residential SOS | January–February 2025; July–October 2026 | Verified recurring-charge subtotal, excluding residential RGGI and legislative credits |
| GS small general service | Pepco Type I SOS | Same windows | Verified recurring-charge subtotal, excluding unresolved Maryland state sales-tax calculation |

Both plans return `is_complete_bill=false`, explicit `excluded_components` and
the `verified_charges_subtotal` objective label. Omitted charges/credits are
**not zero**. Neither complete amounts due nor complete-bill optima are claimed.
The source gap prevents full-year 2025 Pepco billing; an annual request rejects.

Required monthly PCA/BSA/local-tax history is incomplete for March 2025–April
2026. May–June 2026 also rejects: the published MES factor $0.000151/kWh has
not been reconciled to the statutory $0.000150/kWh cap or a documented embedded
assessment. The implementation neither substitutes another utility's factor nor
silently truncates the published value. November–December 2026 and proposed
future changes are outside coverage. Known generation/base prices alone do not
establish an executable complete component stack.

## Account facts and eligibility

The initial locality is explicitly confirmed **unincorporated Montgomery County,
Maryland**, with no separate municipal assignment or special exemption. The
hypothetical weather point 39.05 N, 77.18 W does not establish county boundaries,
utility service, tariff eligibility or tax status. Pepco distribution, Maryland
jurisdiction, Pepco SOS supplier, local tax facts, and ordinary approved parallel
service remain separate confirmations. The [PJM region index](https://emergencyprocedures.pjm.com/ep/pages/regions.jsf)
lists PEPCO as a transmission zone spanning DC and Maryland; that metadata does
not select DC retail tariffs or a wholesale price node. No node is inferred.

Only one ordinary secondary single-phase 120/240-V meter/service at unity billing
power factor is selected here. Temporary, auxiliary/emergency, special facilities,
standby, assistance, opt-out, consolidated competitive-supplier billing credits,
other voltage/phase classes and special exemptions are excluded.

GS has no base demand charge or energy tiers. Existing utility-confirmed GS and
Type I assignment is required independently of study usage. The filed class
trigger uses maximum **30-minute** demand of at least 25 kW in any of twelve
billing months, more than 6,000 kWh in two consecutive winter months, or more
than 7,500 kWh in one summer month; annual transfers occur with June billing.
The conservative study additionally limits every November–May month to 6,000
kWh, every June–October month to 7,500 kWh and 30-minute imports below 25 kW.
It does not infer twelve-month history or automatically reassign a schedule.

GS Universal Service Charge (USC) is restricted to an independently assigned
previous-annual-distribution-revenue band $175–$1,299, producing $1.85/month.
Separate 2025 and 2026 source fields confirm that assignment throughout each
modeled year, before and after the utility's first-quarter update. A calendar
year alone is not the effective date of reclassification. The model never
recomputes a band from an optimized bill. R USC is $0.32/month.

R's first study domain limits monthly imports to 7,500 kWh. This is a disclosed
model restriction, not a tariff-classification rule. At the verified MES factor,
the $1,000 monthly cap is inactive throughout this domain; no large-account cap
or gross-up interpretation is silently inferred.

## Filed components, clocks and August netting

`src/billing/pepco_md_rates.py` contains snapshot-safe Python literals for each
executable month. Generation energy, supply administration, monthly PCA and
transmission remain separate. Capacity, losses and ancillary costs are already
inside SOS; no wholesale LMP, inferred PLC/NSPL obligation or duplicate retail
transmission price is added. Pepco's transmission rates exclude its separately
calculated 2.0408% GRT, unlike BGE's inclusive presentation.

Distribution seasons are **billing months June–October** for summer and
November–May for winter. Generation's filed June–September and October–May
strips and September transmission resets use their own clocks. BSA is a monthly
billing factor. EmPOWER, MYP, administrative delivery credit, DT, MES and MCS
retain their own dated evidence. No missing month is carried forward.

GTC section 7(b) bills non-demand 16–45-day cycles at monthly rates, supporting
one fixed monthly customer charge for complete calendar cycles. Section 7(e)
distinguishes specified-date changes (assumed 30-day proration), bills-rendered
changes (the designated nominal billing month's consumption) and meter-read
changes (all consumption on the applicable reading). This initial interface
requires matching complete calendar service and billing months and a bill date
on the final service day; arbitrary shifted/partial cycles remain unsupported.

During August 11–27, 2026, filed base prices increase and RDM offsets cancel
exactly on the same usage clock:

| Plan | Customer/month | Summer $/kWh | Winter $/kWh |
| --- | ---: | ---: | ---: |
| R temporary base + RDM | 8.67 − 0.23 = 8.44 | .09713 − .00953 = .08760 | .05469 − .01141 = .04328 |
| GS temporary base + RDM | 13.02 − 0.36 = 12.66 | .09220 − .01090 = .08130 | .05447 − .01175 = .04272 |

The implementation bills explicitly named **net-of-RDM** customer and energy
components. Identical clock/GRT treatment makes the unrounded cancellation
independent of any common allocation weights. The utility's published August
variable composite independently confirms the resulting rates. Raw dates and
base/RDM values remain in bill metrics and the source ledger. No 17/30 or
interval allocation is guessed, and separately rounded original base/RDM invoice
lines are not claimed to have been validated. Consolidated component rounding
can differ by cents from separate utility lines; the shared rounding bound and
unrounded reconciliation remain visible.

## Taxes, fixed credits and incomplete-bill status

The published DT, MES and provider-specific Montgomery County Surcharge (MCS)
are distinct. MCS is not the county's underlying tax rate or BGE's surcharge.
The recovered Pepco CSEG footnote marks transmission, distribution, BSA, DT,
MES, EmPOWER, RDM and MYP for GRT. Distribution GRT also includes the ordinary
fixed customer charge and USC, supported by the official handbook. Administrative
delivery credit is unmarked, and MCS is outside the GRT base. No second PSC
assessment is added to the filed prices.

R is exempt from ordinary state sales tax under its residential filed schedule.
Its RGGI/RRC fixed monthly credit, updated quarterly, and individual legislative
refunds remain unverified and explicitly excluded. Their values are not taken
from a variable CSEG table, another utility, synthetic usage or a generic $80
headline. GS is outside residential RRC scope.

For ordinary GS, state sales-tax liability exists, but the precise compound base
(including the recovery portion of MCS) and application of Maryland's statutory
tax brackets to utility billing remain unresolved. `maryland_state_sales_tax` is
therefore an excluded component; the code does not manufacture a zero rate or
use half-up rounding of 6% as a complete tax implementation. This research also
identifies a separate rounding concern to review in the earlier BGE G work;
existing BGE code/evidence is preserved and is not represented as corrected here.

## Dispatch, PV/storage and validation

Numeric bills and the regional optimizer use the same Pepco charge expressions.
Approved ordinary renewable PV/storage service is required, combined PV/storage
nameplate is bounded to 25 kW, exports remain zero and excess PV is curtailed.
No NEM/export settlement, energy bank, community-solar credit, standalone storage
or standby estimate is enabled. An absent-DER grid reference removes renewable
installation assertions while retaining tariff, supplier, tax and USC facts.

The existing weather/PV, AC-coupled storage, rolling-cycle SOC, queued isolated
workers, saved settings, CSV/ZIP and representative OpenDSS paths are reused.
Per-cycle perfect-foresight subtotal optimization is distinct from a joint annual
or complete-bill optimum. Electrical replay uses actual scheduled flows and is
post-dispatch representative steady state, not surveyed network/protection or
transient validation. Its losses never replace scheduled billing flows.

[Source records](utility_sources/pepco_md/sources.json) preserve originals,
hashes, selected physical pages, interpretations and blocked/unrecovered routes.
The scoped [supply](utility_sources/pepco_md/supply_research.md),
[delivery](utility_sources/pepco_md/delivery_research.md) and
[tax](utility_sources/pepco_md/tax_research.md) notes explain each gap.
The CSEG tables are tariff-component and independent arithmetic evidence; they
do not enable export/community-solar settlement. Tests cover all twelve published
plan/month variable composites, independent GRT/itemized fixtures, numerical/
convex parity, August netting, account/date restrictions, DST and missing data,
and main-form/worker/artifact contracts. Frozen checks and browser evidence are
recorded in [implementation validation](Pepco_Maryland_Implementation_Validation.md).
