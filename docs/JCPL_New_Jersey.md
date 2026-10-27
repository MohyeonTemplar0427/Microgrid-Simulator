# JCP&L New Jersey RS and GS secondary BGS-RSCP

Reviewed October 27, 2026. The shared backend and local browser support ordinary
RS residential and the bounded, utility-assigned **GS secondary no-demand-meter**
branch on default **BGS-RSCP**. Verified component coverage is **January 1, 2025
through October 31, 2026**, for complete calendar cycles at 15-minute resolution
in `America/New_York`. Actual eligibility remains an independently confirmed
account fact; the provided representative accounts are explicitly hypothetical.

See the [source ledger](utility_sources/jcpl_nj/README.md),
[source pins](utility_sources/jcpl_nj/sources.json) and
[implementation acceptance](JCPL_New_Jersey_Implementation_Validation.md).
Original PDF/HTML bytes, full text and larger receipts are retained privately
under `.cache/jcpl_new_jersey/`; checked-in leaf excerpts retain effective dates,
physical PDF pages, printed sheets, URLs and hashes. Runtime rates are literal
snapshot-safe data in `src/billing/jcpl_nj_rates.py`, without cache/network reads.

## Account and cycle boundaries

Both plans require ordinary taxable continuous service on one 120/240 V
single-phase secondary meter/service, unity billing power factor, no opening
credit bank, BGS-RSCP enrollment and no special contract, facilities, heating,
water-heater, computed-load, EV or discounted provision. Three-phase, primary,
CIEP, competitive-supplier, tax-exempt and special-service calculations reject.
The representative electrical replay has its own power-factor inputs; those do
not replace billing eligibility.

GS requires affirmative Company determination that demand will not exceed
10 kW and its election to omit a demand meter. In that branch the tariff
considers billing demand below 10 kW. The implementation additionally requires
independent Contract Demand and an upper bound for the preceding eleven
**actual created peaks** no greater than 10 kW, dated through the immediately
preceding month. Current 15-minute imported power also cannot exceed 10 kW.
This makes every ordinary excess-10-kW demand/minimum term inactive. Optimized
imports cannot establish classification, erase inherited peaks or lower the
contract. A conservative running peak ceiling carries separately per scenario;
this is not a general ratchet implementation and may retain a bound longer
than the utility's rolling window.

GS BGS-RSCP also needs separately assigned generation-capacity **PLS strictly
below 500 kW**, retained RSCP enrollment and no CIEP election. The dated annual
supply leaves name November 1, 2023 for June 2024–May 2025, November 1, 2024 for
June 2025–May 2026, and November 1, 2025 for June 2026–May 2027. A multi-year
study must supply explicit cycle overrides at each procurement-year boundary.
PLS is never derived from native load, monthly billing demand or PJM prices.

Part II §§3.03–3.04 retain full monthly charges for ordinary 26–35-day periods.
The initial implementation accepts only complete matching calendar months,
with final-day bill dates. It rejects partial, shifted, initial/final and
otherwise irregular periods rather than inventing days/30 treatment. Civil
days and elapsed DST hours remain distinct; missing, duplicate, naive and
non-15-minute intervals reject.

Part II §3.07 prices service on/after its effective date. September 15, 2025
TEC and July 15, 2026 transmission/TEC changes affect only linear per-kWh
charges; those use **actual interval imported energy** at the dated rate.
Monthly fixed charges and unchanged 600-kWh RS/1,000-kWh GS blocks stay whole.
There is no days-averaged energy assumption or whole-month end-date price.
Unverified nonlinear, fixed-charge or seasonal crossings reject.

## Dated components and arithmetic

The complete ordinary stack contains distribution customer/energy, BGS energy,
quarterly BGS reconciliation, transmission service, every retained TEC owner
block, RMR, NGC, SBC, RRC, ZEC, RP/ENJ, LRAM, CRC and applicable residential
EGCC. Components retain their own effective dates; the date on a compiled book
does not replace a leaf's service-effective date. SBC/RRC constituent amounts
sum once to the published total. A newer TEC owner's block does not remove
still-active blocks belonging to other owners.

| Component | Verified ordinary rule |
| --- | --- |
| RS distribution | $4.27/month; summer first 600 kWh $0.020182, excess $0.079810; winter $0.033061/kWh |
| GS distribution | $4.65/month single-phase; first 1,000 kWh summer $0.075288, winter $0.069662; excess $0.006021/kWh |
| Summer | June–September; winter October–May |
| Base transmission | $0.012709/kWh through April 2025; $0.014877 May 2025–July 14, 2026; $0.017244 from July 15, 2026 |
| Summed TEC | $0.004071 through April 2025; $0.004335 May–September 14, 2025; $0.004339 September 15, 2025–July 14, 2026; $0.004065 July 15–September 2026; $0.004059 October 2026 |
| Residential EGCC | Mandatory −$30 July/August 2025; +$10 September 2025–February 2026; no continued individual balance afterward |
| ZEC | +$0.004265/kWh through May 2025; explicit zero from June 2025; reserved February 15–May 2026; −$0.004265 June–October 2026 |
| RP/ENJ | RP zero through September 2026; ENJ October 2026 RS $0.000135/GS $0.000148 per kWh |

The [delivery](utility_sources/jcpl_nj/delivery_research.md) and
[supply](utility_sources/jcpl_nj/supply_research.md) packets give the full dated
BGS, reconciliation, SBC, RRC, NGC, LRAM, CRC and TEC constituent tables.
Published ordinary rates already include applicable CBT/SUT and BGS capacity,
ancillary and related costs. The implementation adds no second tax multiplier,
retail administration percentage, PLC/NSPL fee or wholesale LMP charge.

Raw kWh is retained: an ACE-specific quantity-rounding rule is not transferred
to JCP&L. The existing framework uses component half-up monetary cents. No
independent printed-invoice rounding rule was established, so the model does
not claim exact printed-invoice or minimum rounded-cash results. Negative raw
or component-rounded post-EGCC totals reject; the optimizer does not force
additional purchases to consume a credit. The EGCC regulatory balance rolls
into NGC, not an invented customer credit bank.

Independent primary benchmarks reconcile the official September 2026 PTC
and BPU 650-kWh transmission impacts: May 2025 +$1.58080 → $1.58; July 2026
+$1.36045 → $1.36; October 2026 −$0.00390 → $0.00. September PTC is not
relabeled as October after the TEC change. These are component/change
benchmarks; no independent complete customer invoice was recovered. Separate
literal arithmetic checks cover each month/plan and saved study bills.

## PV, storage and settlement

PV-only and PV-plus-battery studies require already-active approved ordinary
Class I NEM/parallel service, required installed metering and completion of
the required initiation period before the cycle. Approval must cover the
proposed equipment, annual-needs sizing and any grid charging. A dated active
service record and evidence reference are required; an application is
insufficient. All modeled exports and opening banks are zero.

GS DER additionally requires **explicit utility confirmation of ordinary
NEM/no-STB treatment and retained no-demand-meter classification throughout
the proposed operation**. No generic size exemption was verified. Standby
availability/history calculations are unimplemented; neither a small inverter
nor a synthetic solar capacity factor proves an exemption. The combined
PV/storage study-output bound of 25 kW is only an implementation bound.
Standalone storage, export credits/banking/cashout, community/remote solar,
QFS and unapproved standby configurations reject.

The grid-only counterfactual removes DER activation/approval/no-STB assertions
while retaining tariff, supplier, PLS, contract and inherited actual-peak
facts. It describes an absent-DER reference, not an approved account transition.

## Reused components and proof limits

Existing regional billing math, PV/storage models, queued worker, persistence,
CSV/ZIP exports, browser forms and representative OpenDSS replay are reused.
No shared solver, worker/API schema, physics or replay behavior is changed.
Utility, supplier, NJ jurisdiction and PJM **JCPL market/transmission label**
remain separate. **FE-JC emergency region** is separately sourced metadata;
neither label selects a wholesale node or proves retail service territory.
The default Monmouth County coordinates are hypothetical and do not establish
customer eligibility.

Validation follows the targeted utility policy. Per-cycle historical perfect
foresight and unrounded operating objectives do not establish a joint annual
optimum, minimum rounded cash invoice, actual customer savings, interconnection
approval or surveyed-site electrical feasibility. Solver cost and secondary
cycling proofs must be read separately in the pinned acceptance receipts.
