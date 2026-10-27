# JCP&L New Jersey source ledger

Reviewed October27,2026. Scope: **Jersey Central Power & Light Company, New
Jersey BPU No.14, ordinary RS residential and secondary GS, BGS-RSCP**.

[`sources.json`](sources.json) pins **25 unique original tariff, regulator and
provider PDF/HTML files**, exact URLs, SHA256s, byte counts, full extracted text,
physical pages and **283 excerpt-reference pins across152 distinct checked-in
excerpt files**. Five tariff/PTC render receipts were visually checked.
Original bytes and full extractions remain in ignored
`.cache/jcpl_new_jersey/sources/`. Shared original downloads are deduplicated by
hash; source owners' receipts remain recorded. A transcription, normalized
snapshot or rendered image is a derivative, not an original tariff PDF.
Physical PDF pages are one-based;73/81-page book layouts have different offsets
for the same printed sheet. The source packets retain actual page numbers.

The official archive provides15 adopted PartIII snapshots covering2025 and
selected2026 updates. Supply includes three explicit June–May annual energy
windows, quarterly reconciliation, dated base transmission, RMR and every
retained named TEC surcharge. **All retained TEC blocks add once**: the newest
block does not replace older blocks for different transmission owners. Rider
SBC/RRC published totals also add once; their explanatory components are not
additional charges. Auction tranche prices, proposed conversions, CIEP/LMP
charges and neighboring utilities are excluded. Published SUT and applicable
customer/distribution CBT are already included, without a second tax multiplier.

Billing terms are independently preserved in historical July2024 and current
June2026 PartsI/II, with the relevant original leaves effectiveJune1,2024.
Ordinary monthly billing periods **26–35days inclusive** retain full monthly
charges; outside periods have days/30 proration, but initial complete-calendar
scope need not implement irregular periods. No ACE exact30day restriction is
imported. Billing periods and meter facts must still be confirmed and numeric
calendar/DST/missing-data checks must pass.

PartII§3.07 applies charges to service rendered on/after their effective date,
unless a component specifies otherwise. Source comparison confirms that
September15,2025 changes only linear per-kWh TEC, and July15,2026 changes only
linear base transmission/TEC among supply components; delivery customer,
distribution and monthly blocks stay unchanged at those crossings. Actual
interval importedkWh can therefore use the dated linear prices. Whole-cycle
600kWh RS and1000kWh GS blocks remain intact. No uniform daily consumption,
days-averaged price or general nonlinear/fixed/season-crossing allocation is
invented. An override clock or changed fixed/demand/tier branch must be handled
by separate evidence or rejected.

The verified source-rate coverage is **January1,2025 throughOctober31,2026**,
conditional on ordinary account facts and complete calendar cycles. This
establishes full-year2025 source feasibility, not a source-ledger claim that
a complete engine, study or invoice passed. No actual customer eligibility is
asserted by hypothetical study assumptions.
Engine rate coverage, exact selected cycles and validation evidence belong to
the implementation report and registry. Source completeness is conditional on
all account/rider eligibility and component intersections; a tariff book's
existence is not automatic permission to extend its prices backward or forward.

GS has a supported **utility-assigned no-demand-meter branch**: when the
Company determines demand will not exceed10kW and elects not to install the
meter, demand is considered below10kW for billing. The initial study also
requires actual imported15-minute peak no greater than10kW and independently
confirmed current/prior11-month and contract demand no greater than10kW. This
keeps both ordinary excess10kW demand and historical minimum-demand terms zero.
Low modeled demand alone does not establish that account assignment or erase
contract/history. The1000kWh GS energy tiers remain payable.

BGS-RSCP eligibility is separate: GS annual generation-capacity **PLS below500kW
at the exact November1 year printed on its annual supply leaf**, retained RSCP
assignment and no CIEP election. The tariff gives November1,2023 for the
June2024 year, November1,2024 forJune2025 and November1,2025 forJune2026. CIEP
opt-in or return notices are due the second business day ofJanuary, effective
June1 for12months. Monthly demand, assigned PLS and PJM wholesale metadata
must not be conflated.

RawkWh is retained because no JCP&L ordinary RS/GS quantity-rounding rule was
established. No ACE nearest.01kWh rule is borrowed. General line-versus-total
cash-cent rounding remains unverified. Future metered-GS support would need
its nearest.1kW demand rule and unresolved half-tie treatment; the narrow
assigned nondemand branch avoids claiming that feature is implemented.

Mandatory residential EGCC is **−$30 July/August2025 and +$10 September2025–
February2026**, SUT-inclusive. Its regulatory balance rolls into published NGC,
not an invented customer bank. Negative postcredit settlement is unsupported;
check raw and any separately rounded totals and reject an unsupported result
without forcing imports. After February2026 the fixed rider does not continue
merely because its historical leaf remains in a later book.

PV/storage requires already-active approved ordinary NEM service, configuration
permission including any grid charging, non-export operation and no opening
credit balance. **JCP&L has no sourced100kW standby exemption**. GS DER needs
affirmative utility approval of ordinary NEM/noSTB treatment and retained
nondemand billing; study size or a synthetic solar capacity factor does not
prove it. Standby generation-availability history, special water heating,
computed loads, private contract/facility minima, TOU, export banking/cashout,
community solar and standalone storage are excluded unless separately verified.

Independent primary checks have precise limits:

- The saved official September1,2026 PTC includes reconciliation and TEC.
  Every RS summer block, RS winter and GS seasonal supply total matches the
  adopted September components exactly. October TEC decreases.000006/kWh,
  so that mutable September PTC is not an exact October-rate benchmark.
- Official BPU650kWh transmission impacts independently reconcile: May2025
  +$1.58080 rounds+$1.58; July2026 +$1.36045 rounds+$1.36; October2026
  −$.00390 rounds$0.00, matching published nochange. These verify transmission
  changes, not complete customer invoices.
- No independent complete-invoice primary fixture was recovered. A targeted
  August2026 testimony lead remains unverified; third-party totals were not
  substituted. A failed retrieval is not proof no original exists.

Root metadata preserves **FE-JC emergency-region** evidence and a distinct
**JCPL PJM market label** web-verification receipt. The latter does not claim a
preserved original markets HTML file. Neither label selects a wholesale pricing
node or proves retail territory, supplier, tariff or tax eligibility. The blocked
PJM eTariff route was recorded and not retried. No wholesale price series is
used to reconstruct default retail rates.

Read [supply](supply_research.md), [delivery](delivery_research.md) and
[tax/billing rules](tax_rules_research.md) with their excerpt folders. This
ledger proves source preservation only. Engine/frontend pins, focused tests,
itemized bills, dispatch, solver proofs, OpenDSS coverage and browser assertions
require separately pinned validation receipts.

Re-audit saved source bytes from the repository root without network access:

```python
from pathlib import Path
import hashlib, json
ledger = json.loads(Path('docs/utility_sources/jcpl_nj/sources.json').read_text())
for source in ledger['records']:
    for path_key, hash_key in (
        ('original_path', 'original_sha256'),
        ('full_text_path', 'full_text_sha256'),
    ):
        if source.get(path_key):
            assert hashlib.sha256(Path(source[path_key]).read_bytes()).hexdigest() == source[hash_key]
    for excerpt in source['checked_in_excerpts']:
        assert hashlib.sha256(Path(excerpt['path']).read_bytes()).hexdigest() == excerpt['sha256']
    for render in source['rendered_receipts']:
        assert hashlib.sha256(Path(render['path']).read_bytes()).hexdigest() == render['sha256']
for receipt in ledger['derived_receipts']:
    assert hashlib.sha256(Path(receipt['path']).read_bytes()).hexdigest() == receipt['sha256']
```
