# Pepco Maryland source ledger

Reviewed October 26, 2026. This ledger supports ordinary Schedule R residential
and low-voltage Schedule GS Type I Standard Offer Service for an explicitly
confirmed unincorporated Montgomery County account. Utility, supplier,
jurisdiction, schedule assignment and weather/PJM metadata remain separate facts.

The initial complete-component intersection is **January-February 2025 and
July-October 2026**, for complete calendar billing/service cycles. This is a
source scope, not a claim that engine, solver, OpenDSS or browser acceptance
has passed. Export settlement is unsupported.

[`sources.json`](sources.json) records 37 preserved originals, exact primary
URLs, byte counts, SHA-256s, full-text hashes, physical PDF page selections,
checked-in excerpt hashes and selected rendered receipts. The 28 scoped text
excerpts in [`excerpts/`](excerpts/) retain the relevant rates and rules with
whitespace normalized. Original PDF/HTML bytes and full extractions remain in
ignored `.cache/pepco_md/sources/`; excerpts are derivatives, not originals.
PDF page numbers are physical and one-based, which can differ from printed
tariff numbering. Sixteen Maryland supply originals are distinguished from the
inspected DC and Type II-only files that were excluded as R/GS authority.

The principal component benchmarks are the February 2025 CSEG original,
physical R page 1 and GS page 5, and the October 2026 CSEG original, physical
R page 1 and GS page 4. CSEG tables express credits: their component signs
must be reversed for retail bill charges. Their pre-county/pre-GRT composites
provide independently published arithmetic checks, not authority to enable
community-solar or export settlement. Fixed charges and excluded components
must be reconciled separately.

The current filed tariff's physical R pages 8-9, GS pages 12-13 and RDM page
155 preserve the **raw August 11-27, 2026 temporary base charges and separately
offsetting RDM credits**, as well as the August 28 transition. Both raw
components and the CSEG net are retained. Source preservation does not turn
the net cancellation into an independently calibrated transition-allocation
benchmark. The general terms, physical pages 22 and 24, separately document
ordinary monthly charges and the specified-date change rule.

The recurring-cost results have explicit limitations:

- R is a verified recurring-charges subtotal before the unrecovered fixed
  RRC/RGGI credit and account-specific legislative refunds. RRC is a recurring
  tariff credit; excluding it does not mean zero credit or equate it with
  account-specific assistance.
- GS is a verified-charges subtotal excluding unresolved state sales tax.
  The exclusion means unmodeled tax, not an exemption or zero tax. Compound
  tax-base detail and statutory six-percent bracket rounding need further
  evidence before a complete ordinary GS invoice can be claimed.
- May-June 2026 are rejected: the original CSEG prints MES $0.000151/kWh,
  while the simple statutory cap is $0.000150/kWh. The unresolved recovery,
  gross-up or source-error question is retained verbatim; no replacement
  value was invented. July-October is independently supported by the July
  2026 other-surcharge sheet.
- March 2025-April 2026 PCA and counterpart delivery/tax histories remain
  incomplete. No full-year 2025 or 2026 bill coverage is established. Future
  November 2026 revisions, RDM `TBD` columns and unknown PCA values remain
  outside scope. Proposed tariffs were not used as rate authority.

Read [`supply_research.md`](supply_research.md),
[`delivery_research.md`](delivery_research.md) and
[`tax_research.md`](tax_research.md) for dated component interpretation,
eligibility, tax bases, clocks and unresolved evidence. The manifest records
known blocked/exhausted routes and the bounded history-search receipt. Failure
to recover a historical document is not a claim that no such document exists.

To re-audit saved bytes locally without network access, run from the repository
root:

```python
import hashlib, json
from pathlib import Path

root = Path.cwd()
ledger = json.loads((root / "docs/utility_sources/pepco_md/sources.json").read_text())
for source in ledger["records"]:
    for path_key, hash_key in (
        ("original_path", "original_sha256"),
        ("full_text_path", "full_text_sha256"),
        ("checked_in_excerpt_path", "checked_in_excerpt_sha256"),
        ("cache_selected_excerpt_path", "cache_selected_excerpt_sha256"),
        ("visual_transcription_path", "visual_transcription_sha256"),
        ("render_path", "render_sha256"),
    ):
        if source.get(path_key):
            assert hashlib.sha256((root / source[path_key]).read_bytes()).hexdigest() == source[hash_key]
    for render in source.get("rendered_receipts", []):
        assert hashlib.sha256((root / render["path"]).read_bytes()).hexdigest() == render["sha256"]
```

Candidate identity and completed validation belong in the implementation report
and launcher receipts; this source ledger does not relabel older evidence.
