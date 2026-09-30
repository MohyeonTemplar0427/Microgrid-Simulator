# Measured electricity-bill analysis

This workflow reads customer-supplied PDF statements and produces **observed
bill records**, separate from synthetic load profiles and simulated tariff
bills. It does not infer 15-minute demand, native building consumption,
appliance use, or savings from monthly totals. The simulation engine and its
CSV load controls are unchanged.

## Browser workflow

Signed-in users can open **Analyze my bills** directly, without creating a
simulation, or use the optional **Bills & usage data** step after Electricity
Service. Both entry points open the same private review workspace. Choose one
PDF, inspect extracted fields with their page numbers and supporting text,
correct missing or ambiguous values, validate, and explicitly approve the
bill. More approved bills can then be added for a multi-cycle analysis.
The printed billing plan is displayed as unverified text; it never selects a
simulation tariff. Bill totals are never copied into interval load inputs.

The browser keeps the draft, corrections, approved bills, and analysis in
memory in that tab. **Clear bills and analysis from this tab** discards them;
closing the tab also discards them. The server does not retain PDFs in studies,
accounts, or the database. Local OCR may create private temporary files that
are removed after processing. There is no saved
bill history or recovery after closing the tab. Hosted guests must sign in
before using these endpoints. As with any browser upload, the PDF passes
through the HTTP request; the response uses `Cache-Control: no-store`.

## Local workflow

Use `/usr/local/bin/python3` from the project root. Place outputs in a private,
ignored directory such as `.cache/private_bills/`; the CLI creates JSON files
with mode `0600` and refuses to overwrite an existing review record.

```sh
/usr/local/bin/python3 -m src.bill_analysis extract /path/to/statement.pdf --output .cache/private_bills/statement-draft.json
/usr/local/bin/python3 -m src.bill_analysis review .cache/private_bills/statement-draft.json --corrections .cache/private_bills/corrections.json --output .cache/private_bills/statement-reviewed.json
/usr/local/bin/python3 -m src.bill_analysis analyze .cache/private_bills/*-reviewed.json --output .cache/private_bills/analysis.json
```

The draft lists `fields`, separate delivery/generation `services`, source
`pages`, and validation `issues`. Each extracted value carries one-based page
references, supporting text, and `embedded_text` or `local_ocr` method.
`extracted` means machine-read **not confirmed**; `missing` and `ambiguous`
remain explicit. A correction file maps field paths to values, optionally
with a reason:

```json
{
  "fields.billing_plan": {"value": "Confirmed plan on the statement", "reason": "Checked page 3"},
  "services.0.line_items.2.amount": -12.34
}
```

`review` retains each prior value and its extraction evidence in a correction
audit. It refuses approval if billing dates, billing days, or meter-purchase
kWh are unresolved or invalid. Use `--keep-draft` to apply corrections without
approval. Individual service fields, service provider names, and the full
line-item list can also be corrected by path. Review warnings before relying
on cost composition: a charge mismatch suppresses that breakdown.

## Backend API

The private API used by the browser accepts:

- `POST /api/v1/bills/extract` with `{ "pdf_base64": "..." }`.
- `POST /api/v1/bills/review` with `{ "draft": {...}, "corrections": {...}, "approve": true }`.
- `POST /api/v1/bills/analyze` with `{ "bills": [reviewed_bill, ...] }`.

The endpoints require the normal session CSRF token. Hosted guests cannot use
them; a signed-in account or the trusted local API can. All three are
**stateless**: the caller retains the returned JSON. Raw PDFs and OCR text are
not placed in the dataset store, job store, database, or logs. The API uses
`Cache-Control: no-store`, serializes extraction with the existing interactive
calculation slot, caps uploads at 12 MiB and 12 pages, and accepts at most 60
reviewed cycles per analysis. The PDF has a SHA-256 source fingerprint in the
draft; no account number or address is intentionally extracted. Source snippets
containing obvious account/address labels are replaced with a private-line
marker. This is a conservative first privacy layer, not a guarantee that an
arbitrary OCR line cannot contain personally identifying text; inspect drafts
before sharing them.

On macOS, scanned pages use local Apple Vision OCR through the bundled Swift
source. On other systems, Tesseract plus Poppler can be used if installed.
No cloud OCR request is made. A page with no recognized text is flagged;
missing fields are never filled from a neighboring month. OCR output needs
human review. Currently recognized PG&E/Ava two-column statements have
separate delivery and generation totals and duplicate meter kWh; the parser
counts that meter usage once. Unknown layouts yield incomplete drafts for
correction instead of being assigned a generic tariff.

## Validation and interpretation

- Printed inclusive service dates are checked against printed billing days.
  Reviewed cycles cannot overlap in a multi-bill analysis.
- Each service's itemized charges are compared with its total, allowing only
  ordinary cent rounding. Delivery/generation totals are compared with current
  electric charges. Statement amount due is a separate field: it may include
  gas, prior balance, payments, or non-electric charges.
- TOU kWh, maximum demand, exports, and credits stay missing unless explicitly
  found or corrected. Explicit TOU kWh is retained on its charge line with
  source evidence; it is not expanded into an interval load. A tariff name is
  an observation, not eligibility proof. Field units and line-item currency
  are checked before approval.
- An explicitly printed interval resolution and reported interval count are
  retained as metadata. They are not proof that the PDF contains the interval
  records, and no hourly or sub-hourly load shape is reconstructed from them.
  When a PDF explicitly embeds `meter_intervals.csv`, the backend reads the
  timestamped records, validates their kWh/average-kW relationship, sequence,
  time-zone offsets, and full billing-period coverage, then reconciles the
  retrieved totals with printed usage, TOU kWh, demand, exports, and credit.
  A mismatch blocks approval. Only an aggregate and attachment hash are
  included in the review draft; `read_interval_records` can retrieve the
  complete records locally without placing them in the bill-analysis API JSON.
- The report normalizes meter purchases and current electric charges by the
  actual billing days. Calendar-season groups include only cycles wholly
  within one season; they describe timing but do not establish a weather or
  equipment cause. Unreconciled bills do not contribute cost composition.
- Recommendations distinguish observed facts, hypotheses to investigate, and
  data still needed. No tariff-switch, load-shifting, or dollar-savings claim
  is computed from monthly PDF totals. With PV/battery, grid imports are not
  the building's native load; exported energy is not treated as negative load.

Future work includes saved, user-controlled bill records, more provider-specific
statement templates, and optional interval-data linkage for calibration. The
browser currently edits extracted scalar fields and existing itemized rows;
complex line-item or service-section reconstruction can still be performed
through the CLI/API correction contract. Do not pass
monthly bill kWh to `native_load_kw` or dispatch as if it were a measured
interval profile.

## Synthetic PDF regression cases

Five fictional bill cases cover the
same March 1-31, 2026 billing month at 5-, 10-, 15-, 30-, and 60-minute
reported resolutions. The date range crosses the California spring DST change;
their interval counts are 8,916, 4,458, 2,972, 1,486, and 743, respectively.
Each case prints TOU import kWh, maximum demand, exported kWh, an export credit,
itemized charges, and daily aggregates. It also embeds the **full timestamped
month** as `meter_intervals.csv`, with import/export kWh, average interval
demand kW, TOU label, and synthetic export credit per record. The extractor
reads that attachment and blocks approval if its aggregates disagree with the
visible bill; separate tests independently rebuild every fictional bill from
the complete records. This CSV attachment is an explicit test format, not a
claim that utility PDFs generally contain interval data. All rates and the
utility name are invented and must not be used for a real bill estimate.
`tools/generate_synthetic_bill_pdfs.py` builds optional, readable two-page PDFs
in `output/pdf/` using ReportLab and pypdf. The test suite builds equivalent
PDFs in memory and compares them against the checked-in `expected.json` data;
it needs no ReportLab or committed PDF binaries. `--manifest-only` updates that
JSON without creating PDFs. Generated PDFs are ignored by Git.
