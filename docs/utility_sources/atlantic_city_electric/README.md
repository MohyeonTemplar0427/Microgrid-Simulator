# Atlantic City Electric New Jersey source ledger

Reviewed October27,2026. This ledger covers source research for ordinary
**RS residential and single-phase MGS-Secondary, BGS-RSCP**, New Jersey BPU
No.11. It does not claim that all2025–2026 dates, accounts or bills are supported.

[`sources.json`](sources.json) pins **20 unique original PDF/HTML/JSON/image
files**, their exact URLs, SHA256s, byte counts, full extracted text where
applicable, physical page selections and **38 checked-in excerpt receipts**.
Three BGS-leaf renders and two historical-terms redline renders have visual
verification receipts (five renders total). Original bytes and full
extractions are in ignored `.cache/atlantic_city_electric/sources/`. Shared
originals are deduplicated by hash; owner receipts remain recorded. Text
extraction, visual transcription, snapshot JSON and public-content JSON are
identified separately from original tariff PDFs. PDF numbers are physical,
one-based; printed sheets were renumbered in December2025.

The supply/delivery packets preserve adopted February/June/July/October2025
and September/October2026 snapshots. Every component keeps its own effective
date. The current generation table does not establish earlier transmission or
reconciliation rates. Missing intervening2026 supply leaves and rider updates
remain gaps; no auction tranche price, proposal, adjoining-state rate or blank
cell substitutes for a missing retail charge. BGS-RSCP reconciliation is
separate from adjacent CIEP reconciliation, capacity and standby tables.

Initial cycle scope is **exactly30 consecutive complete local civil days,
wholly in one adopted component regime and season**. Non30-day, partial,
season-crossing and component-change cycles reject because SectionII6.5 does
not establish the needed component allocation formulas. September15,2025 and
July15,2026 changes cannot be assigned across an entire calendar month.
Historical SectionII continuity is now verified: the adopted November2025
order preserves unchanged §4.7 text on physical244 (old leaf effective
July5,2024) and §6.5 on physical249 (old leaf effectiveDecember1,2023),
with clean counterparts92/96 and visual redline receipts. The exact30day
restriction remains because precise proration/allocation is still unverified.
No full-year2025/2026 acceptance is established here. Source-backed production windows are **February–May2025, June2025,
July–August2025, October–November2025, and September–October2026**. Every
cycle must still contain exactly30 complete local days within a single
component regime/season; a named calendar month does not waive that rule.
Actual implementation date support belongs to its rate registry and
validation receipts, not the existence of a snapshot alone.

MGS eligibility requires utility-assigned annual generation-capacity **PLS
below500kW**, the applicable November1 assessment and retained BGS-RSCP
selection. Monthly meter demand and a study peak are different quantities.
CIEP election/return requires notice by the second working day of January,
effective June1 for12months. Territory, supplier, rate schedule, tax status,
interconnection permission, weather and PJM metadata are separate facts.

Ordinary published rates include specified CBT/SUT and statutory administrative
components; there is no extra SUT/admin multiplier. RS is not given Maryland's
residential sales-tax exemption. The adopted mandatory residential rider is
**−$30 in July/August2025 and +$10 September2025–February2026**, SUT-inclusive.
It is not optional low-income assistance. Negative-balance carry/refund and
irregular-cycle posting are unverified, so no cash-refund settlement is invented.

RS uses raw energy because no sourced RS nearest.01kWh rule was found. MGS
final energy rounds to nearest.01kWh and demand to nearest.1kW; exact half ties
reject while the convention is unknown. Demand charges apply to all MGS billed
kW for distribution, and separately above3kW for transmission. A raw-quantity
optimization objective is an explicitly disclosed proxy. Its objective bound
or optimality proof does not establish an optimum for the rounded final cash
bill. Numeric/raw-objective reconstruction and final-quantity billing remain
separate checks.

Historical standby rules matter. The2025 MGS standby rider uses generation
availability over sixmonths and a50% threshold; initial MGS2025 DER is excluded.
The adopted December1,2025 change sets the new non-intermittent outage-available
generation threshold above100kW, preserved in September2026 physical43 and the
November2025 BPU order physical4/8/166. Initial2026 MGS DER still requires
explicit ordinary-tariff/noSTB approval and the conservative configured size
limit. RS/MGS PV-plus-storage requires written utility approval for the combined
configuration, permitted grid charging, non-export operation and no opening
NEM bank. NEM export/cashout/community-solar and standalone storage are unverified.

Independent evidence has limited claims:

- BPU October2026 transmission order physical2 gives ACE650kWh change+$1.60.
  Tariff arithmetic gives650×[(.037688+.003174)−(.035260+.003144)]=$1.59770,
  which rounds to$1.60. This verifies that change, not a complete bill.
- Official PTC images give rounded class comparison prices. The residential
  October winter18.16cents/kWh differs0.0066cent from raw tariff18.1534cents;
  compare with.01cent tolerance. MGS average transmission cents must not replace
  account-specific $/kW billing. Content headings remain stale7/15/26 while
  images are dated09-29-26; adopted tariff clocks control.
- The November2025 BPU order's649kWh190.61→197.38 estimate excludes temporary
  credits/recovery and lacks a standalone seasonal30day specification. The
  February2026 auction release likewise estimates whole-bill impacts. Neither
  is a reconciled independent whole-cycle invoice for this candidate.

AECO transmission-zone and AECO_ENGLAND demand-response-subzone records are
**metadata only**, not a wholesale pricing-node selection or retail account
eligibility proof. Current SectionI/III context is preserved separately. A
retrieved old file namedI_III contains SectionsI andIII, not SectionII; it is
explicitly unused as billing/proration authority. Research routes and missing
windows remain honest gaps; failed retrieval does not prove no source exists.

Read [supply research](supply_research.md), [delivery research](delivery_research.md)
and [tax/billing rules](tax_rules_research.md) with their owned excerpt folders.
This ledger is source preservation only. Engine/frontend identities, focused
checks, independent fixtures, dispatch/OpenDSS coverage, solver limitations and
browser assertions require separately pinned validation evidence.

Re-audit source bytes from the repository root, without network:

```python
from pathlib import Path
import hashlib, json
ledger = json.loads(Path('docs/utility_sources/atlantic_city_electric/sources.json').read_text())
for source in ledger['records']:
    for path_key, hash_key in (
        ('original_path', 'original_sha256'),
        ('full_text_path', 'full_text_sha256'),
    ):
        if source.get(path_key):
            assert hashlib.sha256(Path(source[path_key]).read_bytes()).hexdigest() == source[hash_key]
    for excerpt in source.get('checked_in_excerpts', []):
        assert hashlib.sha256(Path(excerpt['path']).read_bytes()).hexdigest() == excerpt['sha256']
    for render in source.get('rendered_receipts', []):
        assert hashlib.sha256(Path(render['path']).read_bytes()).hexdigest() == render['sha256']
for receipt in ledger['derived_receipts']:
    assert hashlib.sha256(Path(receipt['path']).read_bytes()).hexdigest() == receipt['sha256']
```
