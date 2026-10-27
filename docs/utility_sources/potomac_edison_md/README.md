# Potomac Edison Maryland source ledger

Reviewed October26,2026. Initial shared scope is **Schedule R Residential SOS
and Schedule G Type I SOS, September–October2026**, complete matching calendar
service/billing cycles, in explicitly confirmed unincorporated Washington
County, Maryland. Utility territory, supplier, tariff assignment, jurisdiction,
weather and PJM metadata are separate account/study facts.

[`sources.json`](sources.json) preserves **23 unique original PDF/HTML files**,
exact URLs, byte counts and SHA256s, complete text hashes, physical page
selections, **23 checked-in scoped excerpts** and **eight rendered receipts**.
Identical shared downloads are deduplicated by original hash; their owner/path
receipts remain listed. Originals and full extractions live in ignored
`.cache/potomac_edison_md/sources/`; an extraction or transcription is a
labeled derivative, not an original utility document. Physical PDF pages are
one-based. The utility notes that electronic tariffs are not the official
filed documents; its published approved tariff leaves retain approval/effective
footers. Pending documents never supersede those leaves.

R has ordinary recurring tariff-component coverage within this initial window,
conditional on confirmed account eligibility and no opening bank, special
charges or adjustments. Its 2026 published RGGI customer-credit cells literally
read accounting `$ -`, normalized to $0 with that notation preserved. Legislative
refund posting is September2025 and February2026, outside this scope; no
historical account award is invented. Residential sales-tax exemption is
independently sourced. MES is the actual filed **$.000149/kWh**, effective
bills rendered July1,2026, with cent rounding half upward; it is not replaced
by another provider's factor or the statutory maximum.

G is a **verified-charge subtotal**. It explicitly excludes **state sales tax
and the unverified transmission minimum/capacity component**. The verified
transmission energy blocks remain included. Neither omission means an
exemption or a zero charge; subtotal savings/optimization must not be described
as complete-bill savings. Its demand/minimum/history requirements remain
material even for a utility-confirmed account without a demand meter.

The initial G domain requires an independently assigned Type I classification,
confirmed no-demand-meter method, retained twelve-month energy history,
actual thirty-minute import peak below7.5kW, ordinary established service,
no special monthly-service/connection charges, and utility-assigned USP band.
The selected $175–$1,299 prior-year distribution-bill USP band is **$1.84/month**.
The account must pass the independently documented distribution-minimum guard
in each grid/PV/battery result; unsupported floor-active results reject after
solving rather than forcing imports to satisfy an optimizer constraint. The
transmission $.34/$.19 minimum nesting remains excluded and unproven.

Current R physical62 is effective June1,2026; its source window is wider than
the initial common executable scope. Current G physical70 takes effect
September1,2026. The June–September generation table on that G leaf does not
prove a June–August transmission rate. No adopted earlier transmission leaf
was recovered, so the September clock is retained. All2026 ECA and
administrative-credit monthly values are explicit, but missing2025 originals,
January–May2026 base evidence and other historical tax/rider gaps prevent
full-year2025 or2026 coverage. No neighboring rate or blank-as-zero substitute
is permitted.

The official customer-choice page independently gives current R price to
compare12.433cents/kWh: October supply.10209 + transmission.00396 + ECA.01828
=.12433 dollars/kWh. That benchmark excludes delivery, taxes and administrative
credit. The September4,2026 base-rate filing's ExhibitRV-13 **CURRENT** columns,
physical172–173, independently corroborate R/G ordinary distribution arithmetic.
Its proposed columns are excluded. Floor-active distribution and transmission
minimum invoice behavior remain outside those benchmarks.

The2026 PURPA filing contains a proposed alternative allocation; only amounts
corroborated by current adopted book physical52 are used for2026. The2025
EmPOWER filing contains competing proposals and is not adoption proof. Current
adopted2026 EmPOWER is physical56. Old SOS-directory tariffs retain historical
terms but their old prices do not establish2025 rates. Pending base/grid/large
load proposals, TypeII rates, other states and unverified export/community-solar
settlement are excluded. Preserve ordinary approved parallel PV-plus-storage,
zero-export and no-opening-bank requirements, including unchanged G billing
method/history and no AGS/special charges.

Supplier-tariff and PJM-region originals provide **APS/FE-AP metadata only**.
They do not establish Maryland retail account eligibility or select a wholesale
pricing node. The blocked indexed zone-PDF route and historical DMS403 are
recorded; unchanged routes were stopped. Missing retrieval does not prove a
historical source does not exist.

Read [supply](supply_research.md), [delivery](delivery_research.md) and
[tax/account rules](tax_research.md) for exact rates, source pages and limits.
Washington County's no-extra-energy-levy conclusion is an inventory-based
inference requiring explicit account confirmation, not a zero-tax certificate.
This ledger is source evidence only. Engine/frontend identity, targeted
acceptance, independent bill fixtures, dispatch/OpenDSS and browser assertions
belong in separately pinned implementation/validation receipts.

Re-audit saved bytes from the repository root without network access:

```python
from pathlib import Path
import hashlib, json
ledger = json.loads(Path('docs/utility_sources/potomac_edison_md/sources.json').read_text())
for source in ledger['records']:
    for path_key, hash_key in (
        ('original_path', 'original_sha256'),
        ('full_text_path', 'full_text_sha256'),
        ('checked_in_excerpt_path', 'checked_in_excerpt_sha256'),
    ):
        assert hashlib.sha256(Path(source[path_key]).read_bytes()).hexdigest() == source[hash_key]
    for receipt in source.get('rendered_receipts', []):
        assert hashlib.sha256(Path(receipt['path']).read_bytes()).hexdigest() == receipt['sha256']
for receipt in ledger['derived_receipts']:
    assert hashlib.sha256(Path(receipt['path']).read_bytes()).hexdigest() == receipt['sha256']
```
