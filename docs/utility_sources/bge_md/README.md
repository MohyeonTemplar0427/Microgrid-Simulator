# BGE Maryland source evidence

Reviewed October 25, 2026 against main HEAD `21541dc` before the BGE candidate
was frozen. This folder records the primary sources for residential R and
secondary general-service G with BGE Type I Standard Offer Service. Account
assignment, locality and tax status require independent confirmation.

[`sources.json`](sources.json) pins each retrieved original URL, SHA-256, local
cache path, physical PDF page selections and checked-in excerpt hash. Original
PDFs, complete extractions, public index responses and visual receipts are
preserved under `.cache/bge_md/sources/`; that folder is ignored. An extracted
text file is not an original PDF. A failed source is listed as blocked and is
never represented as a retrieved rate notice.

The checked-in `*-selected.txt` excerpts preserve the selected source pages or
R/G rows with whitespace normalized. Physical PDF page numbers are one-based.
Supplement 751 uses outlined table text: its extraction is incomplete, so the
receipt records visual readback and uses the separately published dated
component ledger for machine-readable corroboration. Some older rotated pages
of the full ledger also extract incompletely; they are outside the selected
2025-2026 R/G pages.

The principal dated source is the utility's original 59-page Community Solar
component ledger: physical pages 12/16 give 2025 R/G and pages 2/6 give January
through October 2026. Its generation, transmission, supply adjustment,
distribution and rider columns are useful tariff evidence. Its independently
published composite arithmetic is a benchmark before fixed charges and selected
local taxes; it does not establish export or community-solar settlement support.
November and December 2026 rate columns are blank and remain outside coverage.

The other originals corroborate schedule eligibility, fixed charges, supply
components, Rider 8/10/25 history, EmPOWER components, dated MYP adjustments,
and the end of the 2024 distribution offset. Use final dated columns; earlier
SOS comparison projections and Supplement 751's pending annual transmission
update must not replace final component history.

Read [`supply_research.md`](supply_research.md),
[`delivery_research.md`](delivery_research.md) and
[`tax_research.md`](tax_research.md) for interpretation and remaining limits.
Those notes distinguish recurring tariff costs from account-specific
legislative refunds, assistance, optional programs, arrears and prior balances.
They also distinguish the statutory commercial tax-base interpretation from
actual customer-bill calibration.

Original source and excerpt integrity can be rechecked locally without live
network requests:

```python
import hashlib, json
from pathlib import Path

root = Path.cwd()
manifest = json.loads((root / "docs/utility_sources/bge_md/sources.json").read_text())
for record in manifest["records"]:
    for path_key, hash_key in (
        ("original_path", "original_sha256"),
        ("extracted_text_path", "extracted_text_sha256"),
        ("checked_in_excerpt_path", "checked_in_excerpt_sha256"),
    ):
        if path_key in record:
            assert hashlib.sha256((root / record[path_key]).read_bytes()).hexdigest() == record[hash_key]
```

This ledger records source identity and interpretation. Validation receipts
must separately pin the engine/frontend candidate and the checks actually run.
