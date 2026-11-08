# Rappahannock Electric Cooperative A-1/B-1: researched, billing blocked

REC's ordinary residential A-1 and single-phase small-general-service B-1 are
identified in the regional catalog. **No complete 2025–2026 bill or dispatch is
enabled.** Filed energy components do not establish a complete tax intersection.
The [source ledger](utility_sources/rappahannock_va/sources.json) retains the
dated sources, access failures, independent tax review and requirements to enable.

## Verified component structure

The accepted A-1 and B-1 sheets apply to bills issued on/after October 1, 2024.
A-1 has a $16.50 single-phase access charge, delivery $0.06450/kWh for the first
300 kWh and $0.04472 thereafter. Supply is $0.06777/kWh; June–September usage
above 800 kWh costs $0.09780/kWh. The ordinary delivery minimum is the access
charge unless a special contract applies.

B-1 is single-phase, with maximum demand to be provided of 25 kW, measured in
15-minute intervals. Its access charge is $45/month, delivery $0.02599/kWh,
and supply $0.08217/kWh in June–September or $0.05643 in October–May. Required
transformer capacity above 15 kVA adds $1 per additional kVA or fraction to the
delivery minimum. That required capacity is an independent utility assignment;
PV-reduced imports cannot establish it. Special facilities and contract minima
need separate treatment. Motors above 10 hp require utility approval.

The official exhibit makes both PCA and DR mandatory for these plans. The
retained PCA sheets state $0.02509/kWh for bills from June 1, 2025, and
$0.03426/kWh from May 1, 2026. DR is $0.000032/kWh from January 1, 2025 and
$0.000031/kWh from January 1, 2026. Optional demand-response participation
credits are distinct from that mandatory cost-recovery rider. The preceding
2025 and January–April 2026 PCA factors were not recovered; no rounded reduction
notice is used to manufacture them.

## Tax gap that blocks complete bills

[Virginia §58.1-2900(A)(6)](https://law.lis.virginia.gov/vacode/title58.1/chapter29/section58.1-2900/)
requires an adjustment where qualifying federal electricity purchases apply.
Each state, special-regulatory and local-consumption tax amount is reduced
using the qualifying federal-power cost, including facilities rental, divided
by the cooperative's Virginia operating revenue for the taxable period.
Neither the statutory formula, REC's energy mix nor an account checkbox
establishes that ratio as zero. The independent review found no dated REC/SCC
factor or documented nonapplicability. Unknown tax is not omitted or set to zero.

The actual SCC levy is separate from the statutory ceiling: the retained SCC
source gives $0.000165/kWh in all tiers from August 1, 2025; an older official
statewide table records the preceding tiered rates. Those sources do not solve
REC's cooperative-specific adjustment.

Unincorporated Rockingham County was investigated as a shared locality.
The indexed county codification's §7-10 prints residential $0.1500/kWh with
$1.40 minimum/$3 cap and commercial $0.014674 with $2.29 minimum/$40 cap.
A minimum is not a fixed amount added to usage. The residential decimal and
original ordinance still require reconciliation. No silent correction to
$0.01500 or substitution of another county's tax is made.

## Eligibility and acceptance boundary

REC, its bundled supply, Virginia jurisdiction and PJM metadata remain separate.
PJM documents establish some REC load within Dominion projects; they do not
establish a uniform zone or wholesale pricing location for every REC meter.
No wholesale price is selected by default.

Terms require specific approval for parallel generation. A future non-export
implementation must verify the exact PV/storage agreement, ordinary import
billing and any recurring interconnection/excess-facilities charges. It cannot
infer eligibility from equipment size or absence of exports.

All 24 requested months for both classes reject, including fully confirmed or
hypothetical accounts and supplied provisional factors. Source observations
are not priced subtotals. No complete bill benchmark, dispatch proof, matrix
or electrical/browser execution is claimed for REC. Source originals and the
component review are private under `.cache/rappahannock_va/`. The batch report
owns the final candidate identity and targeted acceptance receipt.
