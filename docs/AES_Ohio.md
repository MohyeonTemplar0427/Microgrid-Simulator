# AES Ohio

This local-development adapter models The Dayton Power and Light Company dba
AES Ohio, P.U.C.O. No. 17: ordinary **D17 Residential** and metered,
single-phase **D19 Secondary**, with **G10 Standard Offer (SSO)** and mandatory
**T08 non-bypassable transmission**. It reuses the shared regional browser,
queued worker, PV/storage, numeric/symbolic billing, rolling dispatch and
OpenDSS replay. Desktop GUI work remains paused; no stable engine is promoted.

Complete matching calendar service/bill cycles execute in **January–June
2025, June–July 2026, and September–November 2026**. September 2026 onward
requires a documented prior receipt of the one-time D43 credit. Other dates,
partial/shifted cycles and unresolved receipt/selector states reject.

The [aggregate source ledger](utility_sources/aes_ohio/sources.json) pins
retained evidence. Exact vectors and review are in
[delivery](utility_sources/aes_ohio/delivery/README.md),
[supply and calculator evidence](utility_sources/aes_ohio/supply/README.md) and
[account/tax rules](utility_sources/aes_ohio/rules/research.md). Candidate
acceptance is recorded in the
[implementation report](AES_Ohio_Implementation_Validation.md).

## Dated components and source grades

G10 applies to **service rendered**; T08 and the dated riders apply to
**bills rendered**. These clocks are stored separately. Calendar cycles use
their matching final-day bill date and full monthly charges; a generic
day/30 fixed-charge or mixed-rate demand allocation is not inferred.

| Service/bill months | D17 delivery, customer + energy | D19 delivery, customer + all billing kW | G10, $/kWh | T08 D17, $/kWh | T08 D19, $/kW + $/kWh |
| --- | --- | --- | ---: | ---: | --- |
| January–May 2025 | $9.75 + $.0286082/kWh | $16.68 + $4.7725904/kW | .0857985 | .0101098 | 2.8762278 + .0005432 |
| June 2025 | $9.75 + $.0286082/kWh | $16.68 + $4.7725904/kW | .0945004 | .0150056 | 3.9517849 + .0008294 |
| Supported 2026 months | $9.75 + $.0493180/kWh | $19.00 + $7.8040932/kW | .1085598 | .0179223 | 4.3554372 + .0007632 |

The supply ledger distinguishes adopted-original PDFs from **G10 revision 26
(June 2025–May 2026)**: its exact rate/date/applicability are corroborated by
preserved dated official calculators and reproduced cached adopted tariff
text, while the original PDF remains unavailable. Executable June 2025 keeps
that source grade in result metrics and warnings; it is not relabeled as an
adopted-original PDF. No missing rate is inferred. Other supported generation
and transmission revisions retain their originals.

D29 infrastructure investment, D36 distribution investment and signed D41 tax
savings percentages apply to customer plus the **selected distribution
variable charges**, excluding T08. D31 is 2.82% of that base for D17, but a
$3.66 monthly charge for single-phase D19. D30 storm and D32 reliability are
fixed by class; D28 PIPP, D27 solar generation, D40 legacy generation, D39
economic development, D37 customer programs and D38 efficiency keep their
dated class-specific amounts and explicit zero/inapplicable treatment.

D41 is a **positive 2.5675%** in supported June–October 2026 months despite
its credit-related name; November 2026 changes it to **negative .2577%** and
introduces positive D39 energy amounts. G10 already includes alternative-energy
costs. T08 is charged once, with no additional wholesale LMP, PLC, NSPL,
capacity, transmission or whole-bill CAT adder.

## Demand, low load and minimum bill

D19 uses the greatest **30-minute integrated import kW**. Initial scope is
below 100 kW and explicitly excludes an off-peak election now or throughout
the prior eleven months; every current interval has full weight. Billing
demand is the maximum of the current actual peak and **75% of the greatest
actual peak in June, July, August, December, January or February within the
preceding eleven months**. The supplied history must contain eleven exact,
consecutive monthly records, oldest first. Missing records are never zeroed.
Each scenario carries its own subsequent actual peaks; ratchet-inflated
billing kW do not become new actual-history peaks.

Both D19 and T08 price all billing kW: there is **no first-five-kW exemption,
five-kW floor or ordinary contract-demand floor**. The base monthly minimum is
the customer charge. Zero import may still incur that customer charge and
applicable fixed/percentage riders. Contractual minimum load, NSPL opt-in,
legacy TCRR opt-out, off-peak metering election, special 85%-connected-load
determination, unmetered service and special facilities are excluded.

The ordinary D19/T08 variable-charge total is compared with the combined
low-load-factor energy cap. If the cap is lower, D19 and T08 each use their
own filed per-kWh substitute; the customer charge remains separate and
percentage riders then use the selected D19 base. A separate minimum on each
component would fabricate a bill. The original tariffs do not prescribe the
calculator's interim-cent comparison, and the two branches can assign
different distribution amounts even at equal combined totals.

The shared bounded selector models filed **unrounded** arithmetic. Numeric
rebilling rejects a **$0.02 comparison band when the distribution allocations
differ**. This is an explicit study exclusion, not an AES eligibility rule.
At zero/identical allocations the ambiguity is absent. The symbolic graph is
an outer model at the excluded boundary; authoritative replay must accept a
physical candidate attaining the proven lower bound before a cost proof is
reported. A solution trapped in the excluded band fails acceptance. Exact
printed-invoice or rounded-cash optimization is not claimed.

## Taxes and one-time refund

D33 incorporates ORC 5727.81(A): utility-import kWh, marginal rates
$.00465/$.00419/$.00363, and cumulative thresholds 2,000/15,000 kWh for
**exactly 30 measurement days**. Other periods use **67 × local calendar days**
and **500 × local calendar days**. DST changes elapsed hours, not calendar
measurement days. AES D33 provides no affiliate-style CAT gross-up.
Wired-electricity sales tax is exempt. Self-assessment, special exemptions and
additional local/franchise charges are excluded and require independent
account confirmation.

The official calculator normalizes 25–35-day cycles to fixed 2,000/15,000 tax
bands, which differs from the incorporated statute for non-30-day cycles.
Calculator benchmarks use matching 30-day tax treatment; non-30-day model
results follow the detailed statutory rule and retain this discrepancy.
September 2025 spreadsheet precision also differs from the filed cap, outside
this adapter's executable months.

D43 states a one-time credit beginning August 1, 2026: **$14.39 D17** or
**$49.27 D19**, without an explicit ending date or first-receipt allocation.
August is blocked. For September onward, the account must document the exact
credit amount, a receipt date on/after August 1 and before service, its source
and confirmation of prior receipt. The current bill has a zero refund line;
the credit is never repeated or silently presumed absent. Defaults identify
an August 31 receipt as an explicit hypothetical account fact, not customer
evidence.

## Account, DER and grid identities

Initial D17 scope is ordinary residential single-phase secondary service, one
meter, within the tariff's residential classification. D19 is ordinary
single-phase secondary nonresidential service at one premises location.
The model bounds native and imported peaks at 25/100 kW respectively and
usage at 833,000 kWh/cycle. These are study restrictions, not complete tariff
eligibility definitions. Shopping/aggregation, PIPP/assistance, optional
pricing, adjustments, multi-meter, primary/three-phase and emergency/auxiliary
agreements are excluded.

The exact PV and paired-storage configuration must already have Company
approval, final permission to operate and required metering, with ordinary
D17/D19 continuation and no D10 auxiliary/standby capacity charges confirmed.
The 2023 D35 text already contemplates inverter/battery interconnections;
later technical guidance is not backdated to establish historical approval.
PV-only charging, zero exports/credit bank and combined study output at most
25 kW are conservative model restrictions. They do not establish universal
AES approval or charging requirements. Standalone storage and export/NEM
settlement are unsupported. Grid-only removes DER assertions but preserves
actual history, tax, SSO and prior-refund facts.

The Montgomery County coordinates and account are explicitly hypothetical.
Coordinates do not identify service territory, supplier, tax status or PTO.
**PJM / DAY** transmission and control-area metadata are independent from AES
retail service, Ohio jurisdiction, G10 supply, any chosen wholesale price node
and optional **US-MIDA-PJM regional-average carbon**. Existing carbon accounting
requires matching inputs and does not alter this retail bill or dispatch.

## Unsupported periods

July–December 2025 lacks required intermediate distribution rider/base
originals; November also lacks a verified November 6 mixed-cycle allocation.
January–May 2026 lacks complete earlier distribution intersections. August
2026 first-refund treatment and December 2026 later components are unverified.
No provisional mode, rate interpolation, current-rate backfill or full-year
2025 coverage is enabled. Source failures and grades remain in the ledgers.
