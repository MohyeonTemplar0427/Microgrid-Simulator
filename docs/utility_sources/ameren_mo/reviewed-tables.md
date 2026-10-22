# Ameren Missouri rate extraction review · October21,2026

The manifest records downloaded PDF hashes, retrieval timestamps and selected
page numbers with text hashes. Runtime values are Python literals included in
the engine, not reads from these documentation files or the research cache.
The PDFs are text-based. Rotated regulator filing/cancellation stamps remain
in the retained text; their date strings must not replace each sheet's printed
issue/effective date or explicit service window.

Visually inspected rendered sources include:

- Cancelled sheets1–58, PDFpage23: 7th revised54, effectiveDecember3,2023,
  cancelledJune1,2025: residential9.00customer/.14pilot, summer.1372/kWh,
  winterfirst750 .0934/tail.0627.
- Same bookpage81: 6th revised55, regulator-corrected effectiveJuly9,2023,
  cancelledJune1,2025: standardcommercial11.96single/22.87three/.20pilot,
  summer.1197, winterbase.0894/seasonal.0516. The printed July19 date is
  corrected in the filing stamp; no2025price difference depends on that correction.
- Residential PDFpage9, sheet54.8: Smart Saver local periods and nine named
  holidays, without substitute-day language. July3,2026 is not removed from peaks.
- Cancelled sheets90.5–123,page62, 6th revised91.23: totalEEIR .002171 for1(M)
  and .002819 for2(M), February1,2025–January31,2026. Component negatives in
  parentheses must be subtracted; use the total once, not add it to its components.
- Current sheets1–92.3,page293, 8th revised90.4: secondarySUR .00157/kWh,
  October1,2026–March31,2027; it already includes the voltage adjustment.
- DOR January2025 tablepage2: ColeCounty00000-051-000 sales5.6000%, domestic
  utility0%. All nine linked2025/2026period tables have the same specific row.

Important cross-checks from the operative filed documents:

- June2025 actualFAC is **6th revised71.32**, Document825521, secondary.00360/kWh
  forJune–September2025. The new original72.14 zero-filled form saysXXXXXX for
  applicability and must not be treated as a filed zero-price service period.
- RESRAM10th revised93.4, effectiveJune1,2025, supersedes the9th revision's
  Februaryannual factor: .00133 replaces.00313 as costs move into base rates.
- Ordinary commercial5.6% tax and domestic0% come from independent DOR
  jurisdiction records, not an assumption that all Missouri locations share them.
- Standard2(M) seasonal-use threshold is max(1000,min(documentedMay,
  documentedOctober,maximumanyprecedingsummermonth)). The company history/source
  is required; missing-history and later-refund procedures are outside this scope.
