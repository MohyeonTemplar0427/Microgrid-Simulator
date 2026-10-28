# FirstEnergy Pennsylvania — Penelec RS and GS-Small

Reviewed October 28, 2026. The shared backend/local browser support ordinary
Penelec **RS residential** and **GS-Small (GS-S) non-demand default PTC**.
Verified component intersections cover **January 2025–June 2026 and October
2026**, for matching complete calendar service/bill months. July–September 2026
DSIC is missing and rejects. Other FirstEnergy districts' rates are not used.

See the [source ledger](utility_sources/penelec_pa/README.md),
[source pins](utility_sources/penelec_pa/sources.json),
[delivery research](utility_sources/penelec_pa/delivery_research.md),
[supply research](utility_sources/penelec_pa/supply_research.md),
[tax/rules research](utility_sources/penelec_pa/tax_rules_research.md) and
[implementation acceptance](Penelec_Pennsylvania_Implementation_Validation.md).
Original PDF/HTML/workbook files and larger receipts remain in ignored storage;
the engine uses self-contained literal prices and provenance.

## Account and eligibility boundaries

Ordinary continuous service uses one 120/240 V single-phase secondary meter,
unity billing PF, state-only PA jurisdiction and no special contract/rate,
assistance program or certificate exemption. RS is solely residential; the
tariff's mixed business allowance does not automatically establish sales-tax
exemption. GS-S uses 6% on known current charges. No Philadelphia/Allegheny or
mixed/exempt business tax calculation is enabled. Utility district, supplier,
tax status, active DER and PJM PENELEC market-zone/FE-PN emergency-region labels
are independent facts. No wholesale price node, PLC/NSPL or LMP is inferred.

Penelec RS ordinary scope is one dwelling unit; its marked legacy multiunit provision A(2) is excluded. No neighboring district farm or multiunit allowance is imported.

RS requires independent Company confirmation that special demand and the
prior-eleven-month excess-demand ratchet are inactive, with historical peak
bounds at most 25 kW. Model native and imported 15-minute peaks are also bounded
at 25 kW. History is not erased by PV or inferred from a low current import peak.

GS-S requires Company-confirmed absence of a demand meter and actual metered usage. Its A+C general-provision matrix excludes fixed/imputed-usage provision C and early termination in this scope. Penn Power's B500-kW GSDS cutoff is not a Penelec rule. Default PTC enrollment remains independently confirmed.

For existing Penelec GS-S customers, consumption above 1,500 kWh in two
consecutive months within the latest twelve may lead to Company reassignment.
The exact qualification predicate is not explicitly resolved as gross native
versus NEM net energy. The implementation requires independently retained
Company assignment, documented prior-twelve qualification bounds at most
1,500 kWh, separate modeled native-cycle energy at most 1,500 kWh and imports
at most 1,500 kWh. These are a **conservative inactive-reclassification domain**,
not an invented automatic monthly tariff limit. The conservative 1,500-kWh
envelope carries without being lowered by PV. Transitions/general demand
service and qualification inferred from optimization are not implemented.

Only complete matching calendar cycles are accepted. Monthly fixed charges
remain whole; partial/shifted proration is unsupported. No West Penn 25–35-day
rule is imported into GS-S. Local DST elapsed intervals remain distinct and
missing, duplicate, naive, nonfinite and non-15-minute data reject.

## Components and arithmetic

| Component | Penelec ordinary rule |
| --- | --- |
| Distribution | RS $11.25 + $0.06815/kWh; GS-S $20.87 + $0.04262/kWh |
| PTC Jan–May 2025 | RS $0.10474 / GS-S $0.10382 per kWh |
| PTC Jun–Nov 2025 | RS $0.11003 / GS-S $0.11405 per kWh |
| PTC Dec 2025–May 2026 | RS $0.11747 / GS-S $0.12155 per kWh |
| PTC Jun–Oct 2026, subject to other-rider coverage | RS $0.13142 / GS-S $0.12920 per kWh |
| TCJA | Zero Jan–Jun 2025; **positive 3.04%** Jul–Dec 2025; zero 2026; base distribution/customer basis only |
| STAS | +0.01% in 2025; −0.02% in 2026; applied after other tariff riders/DSIC/PTC, before refund/sales tax |
| DSIC | Zero Jan–Mar 2025, −0.01% Apr–Jun 2025, zero Jul–Dec 2025/Jan–Mar 2026; 0.39% Apr–Jun 2026; 2.70% Oct 2026; Jul–Sep gap rejects |
| Smart meter | Fixed RS $0.01 / GS-S $1.44 in 2025; RS $0.05 / GS-S $0.09 in 2026 |
| LEDC | Mandatory class allocation: RS $0.00022 / GS-S $0.00016 per kWh Apr 2025–Mar 2026; RS $0.00007 / GS-S $0.00006 from Apr 2026; Jan–Mar 2025 treatment explained below |
| January 2025 refund | Mandatory once, RS −$6.15 / GS-S −$3.42, GRT-inclusive; outside current STAS basis |

DSS is RS $0.00854 / GS-S $0.00445 per kWh Jan–May 2025, $0.00798 / $0.00362 Jun 2025–May 2026, and $0.00375 / $0.00056 from Jun 2026. EEC follows $0.00209 / $0.00362, $0.00286 / $0.00253 and $0.00222 / $0.00429 over those windows. Residential USC is $0.01049 Jan–Jul 2025, $0.01699 Aug–Dec 2025 and $0.01844 in 2026; it does not apply to GS-S.

LEDC is nonbypassable on class billing units even when this customer has not converted lighting. **January–March 2025 LEDC non-applicability is a disclosed start-date inference**: Original245 identifies its first rate window as April 1, 2025; Original247 defines the annual April computational clock; the adopted First Revised245 starts positive charges April 1. No explicit January–March zero-priced row was found. The zero charge represents absence of an applicable pre-April period, not backdating an April price or carrying an original provisional zero. Full source text and the independent review are retained.

The dated source packets pin these components and SPVRC. The original June 2025 DSS submission was replaced by the Fourth
Revised page effective the same June 1 date: use RS $0.00798/GS-S $0.00362,
not the earlier high-precision submission. RS and GS-S retain the January–May
2025 SPVRC credit of −$0.00001/kWh, including DER. Its self-generation waiver
names larger classes. Later recovery is incorporated in DSS and not added twice.

DSIC applies to distribution including applicable riders/DSS/**LEDC**, excluding PTC
and STAS. TCJA has its own base-only definition. PTC includes filed GRT,
administration, loss, capacity/AEPS and supply transmission costs; no second
GRT/admin/wholesale adder is used. A conflicting May 30, 2026 PTC footer is
retained as evidence, with May 31 independently corroborated by the original
official Penelec December 2025/April 2026 price inserts and the six-month PTC rule. The retained June 2025 insert has correct June prices but an erroneous May 2026 endpoint; filed November 30, 2025 controls. A stale indexed December filename was unavailable; the actual current December file is correct. These source identities are distinguished in the supply note. Workbook June24 labels are
not used as effective dates in place of adopted June 1 leaves.

**January 2025 GS-S is a verified-charge subtotal.** It computes 6% sales tax
on known current tariff charges and subtracts the known $3.42 refund once,
while explicitly excluding the unresolved prior-refund sales-tax adjustment.
That adjustment is not assigned zero. RS January and other supported ordinary
months can report complete modeled components. Full-year GS comparisons must
retain January's subtotal qualification and cannot claim a complete annual
amount due. January additionally requires independent established-account refund entitlement and a source, including when an imported state already represents it. All refund state is carried once with adjacent billing months.

Raw kWh and existing component half-up cents are retained without an exact
printed-invoice rounding claim. A narrower inactive-minimum domain requires
current tariff raw/component-cent totals before refund/sales tax to meet the
customer amount. Unknown floor cases reject without forced purchases; this is
not a claimed replacement for the tariff's minimum formula. January refunds
are never clipped. Penelec SMT is positive in both covered years; no neighboring district negative-SMT price is imported.

## PV/storage and validation scope

PV-only and PV-plus-battery require already-active qualifying ordinary
customer-generator/NEM approval, required metering and no Partial Services
Rider. Storage is PV-only charging with no battery export; no opening bank,
standalone battery or export credit/banking/cashout is modeled. The combined
25-kW study-output bound does not establish utility eligibility or exemption.
Grid-only removes DER assertions while preserving refund and qualification
history. Native electrical replay PF/transformer/service assumptions remain
separate from billing eligibility.

Validation uses the targeted utility policy: source arithmetic, independent
benchmarks, numeric/symbolic parity, date boundaries/DST/missing data, eligibility,
tax/state/bill/dispatch/SOC reconciliation, worker/form/save/CSV-ZIP and a frozen
candidate matrix followed by one concise browser pass. Historical perfect
foresight is per cycle. No joint annual/rounded-cash optimum, actual customer
savings, complete January GS invoice or surveyed-site/interconnection approval
is claimed. Earlier utility evidence retains its original engine/frontend pin.


## Related earlier-utility finding

Penelec research identified mandatory LEDC in the same source book that the earlier Met-Ed adapter omitted. Prior Met-Ed complete-bill claims need separate correction/revalidation; its recorded numerical/solver/electrical/browser evidence remains attached to its original candidate and does not prove inclusion of this omitted component. This task preserves all prior Met-Ed source, code and report files. The issue receipt is `.cache/penelec_pa/prior_met_ed_ledc_issue.json`; this notice does not relabel or rerun old evidence.
