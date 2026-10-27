# Delmarva Maryland source ledger

Reviewed October 26, 2026. This ledger supports ordinary Maryland Schedule R
residential and secondary Schedule SGS-S Type I Standard Offer Service. The
hypothetical locality is explicitly confirmed unincorporated Wicomico County;
the absence of an additional ordinary county energy levy is a documented
code-based inference plus account confirmation. Weather coordinates, utility
territory, supplier, jurisdiction, eligibility and PJM metadata remain separate.

The initial source intersection is **January-June and September 2025, plus
May-October 2026**: thirteen complete calendar billing/service cycles. No full
2025 or 2026 billing year is established. This is source coverage, not proof
that a particular engine, solver, OpenDSS scenario or browser assertion passed.
Export and community-solar settlement remain unsupported.

[`sources.json`](sources.json) pins 29 original PDF/HTML files, exact primary
URLs, byte counts, SHA-256s, complete text hashes, physical PDF selections,
26 checked-in [scoped excerpts](excerpts/) and thirteen rendered receipts.
The official PJM regions HTML is metadata only: DPL spans Delaware, Maryland
and Virginia; it does not establish a Maryland retail tariff, account territory
or wholesale pricing node. Its original bytes and retrieval receipt are pinned.
Originals and complete extractions remain in ignored
`.cache/delmarva_md/sources/`. An excerpt or transcription is a derivative,
not an original utility file. PDF page numbers are physical and one-based.
The archive's `supply_book_2025_jun` contains proposed R/SGS leaves and is
explicitly excluded; the actual approved May 22 clean filing supplies those
final rates. No proposed rate, Delaware tariff or neighboring utility was used
to fill a Maryland rate gap.

The independent utility component benchmarks are the May 2025 and September
2025 CSEG originals, physical R page 1 and SGS-S page 2, and the October 2026
original, physical R page 1 and SGS-S page 4. Text extraction reorders some
first-two-month cells. The excerpts therefore label the per-month retail-sign
transcription and preserve rendered source receipts. CSEG credit signs are
reversed for retail charges; the originals explicitly identify embedded GRT.
Pepco's separate percentage GRT adder must not be copied into these rates.

Published variable composites exclude fixed customer/USP and **all demand
charges**. SGS-S is a demand-charged schedule. Its initial scope requires
independent utility assignment to the tariff's **E3 estimated-demand method**,
physical 15-minute peak below 20 kW and monthly imports no more than 3,500 kWh.
E3 billing demand is imported monthly kWh divided by 175 hours; E3 is a rule
identifier, not a fixed 3-kW assignment. Transmission demand is zero within
this domain, while delivery demand remains payable. The independently assigned
USP band must remain applicable throughout each modeled year and technology
scenario. R monthly import is bounded to 7,500 kWh. These restrictions keep
unsupported demand rounding, threshold crossings and large-account cap
allocation outside scope.

The dated source boundaries remain explicit:

- July 2025 is rejected because the filed MES change takes effect July 2;
  August 2025 is rejected because transmission changes August 27. A monthly
  CSEG label cannot establish allocation across either intramonth boundary.
- The actual filed billed MES is $0.000151/kWh from July 2, 2025. Later
  complete cycles retain that tariff value, including May-June 2026. Its
  unexplained distinction from the simple statutory environmental-assessment
  cap is recorded; no PSC/GRT decomposition or replacement rate was invented.
- The recovered July 6, 2026 book explicitly makes $0.000150/kWh effective
  usage July 1, confirming July 2026's boundary. Original tariff leaves and
  their rendered footers are preserved alongside the CSEG monthly history.
- Monthly PCA/BSA/admin-credit evidence for October 2025-April 2026 remains
  incomplete. Blank future cells never mean zero or authority to carry a
  neighboring rate forward.

Results remain **verified-charge subtotals**. R excludes the unrecovered
recurring RRC/RGGI credit and account-specific legislative refunds; these are
different exclusions, and neither means zero credit. SGS-S excludes unresolved
state sales-tax computation, including taxable-base/credit treatment and
statutory bracket rounding. Unmodeled tax is not an exemption or zero tax.
PV/storage requires separately confirmed ordinary interconnection, non-export
operation and retained SGS-S E3 treatment. Project fees, standby assignments,
special agreements and discretionary programs are not inferred from a profile.

Read [supply research](supply_research.md), [delivery research](delivery_research.md)
and [tax research](tax_research.md) for component rates, physical pages, rules
and limitations. The source manifest preserves blocked routes and the bounded
history-search receipt. Failure to recover a source is not a claim that no
historical document exists. The Wicomico code web read is labeled separately:
direct retrieval returned 403, so no preserved original HTML is claimed.

Re-audit saved source bytes from the repository root without network access:

```python
import hashlib, json
from pathlib import Path

root = Path.cwd()
ledger = json.loads((root / "docs/utility_sources/delmarva_md/sources.json").read_text())
for source in ledger["records"]:
    for path_key, hash_key in (
        ("original_path", "original_sha256"),
        ("full_text_path", "full_text_sha256"),
        ("cache_excerpt_path", "cache_excerpt_sha256"),
        ("checked_in_excerpt_path", "checked_in_excerpt_sha256"),
        ("render_path", "render_sha256"),
    ):
        if source.get(path_key):
            assert hashlib.sha256((root / source[path_key]).read_bytes()).hexdigest() == source[hash_key]
    for render in source.get("rendered_receipts", []):
        assert hashlib.sha256((root / render["path"]).read_bytes()).hexdigest() == render["sha256"]
```

Candidate fingerprints and completed validation belong in the implementation
report and launcher receipts; this ledger does not relabel older evidence.
