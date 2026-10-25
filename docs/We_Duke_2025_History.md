# We Energies and Duke Indiana: remaining 2025 rate evidence

Research date: October 24, 2026. **Verified full-year 2025 pricing remains
incomplete.** The user subsequently authorized explicit provisional assumptions
for the remaining gaps. Verified-only remains the default; opting in does not
turn those assumptions into filed rates. See the separate
[provisional implementation and validation](We_Duke_2025_Provisional_Validation.md)
for the new scope, assumptions and results. The source gaps below remain open.

The preceding candidate's 3,880-pass / one-skip regression report remains
attributed to engine
`25aa80f26e58e4ba0fe623a2ad3ac5a0ae9ca99db434947377fd8cfa65228545`.
That report and the earlier partial-period matrices are not evidence of
new full-year support. See [the earlier candidate validation](We_Duke_Implementation_Validation.md).

## Exact remaining evidence

| Utility / period | Required source content |
| --- | --- |
| We July–November 2025 | Applicable Wisconsin Electric sheet 20.2 with actual effective dates and residential/small-C&I ECC factors, or the actual monthly certificates establishing those factors |
| We December 2025 | Applicable superseding dated sheet 20.2; January 2026 brochure prices alone do not establish December applicability |
| Duke January–February 26 | Prior class tables for ECR42/62, TDSIC3/65, RTO60/68, SRA9/70 and REP6/73; isolated known base/other rider prices do not constitute a complete bill |
| Duke April–June | Reconcile FAC143's printed positive sign against three official calculations yielding negative $0.004801/kWh; final tariff transcription remains unavailable |
| Duke July–December | Actual ECR43 and REP7 class factors and the dated December credit67 treatment |

The exact official We issuer URLs, archived original ratebook links, capture
digests, exclusions and failed access routes are retained in
[the Wisconsin retrieval record](utility_sources/we_energies_wi/2025-gap-retrieval-status.md).
The dated Duke observations and missing components are in
[the Indiana evidence ledger](utility_sources/duke_in/history2025-evidence-status.json).
These research records are not executable dispatch price sets.

The Duke website identifies a
[2025 quarterly adjustment tracker](https://www.duke-energy.com/-/media/pdfs/for-your-home/rates/electric-in/iurc-16/2025-quarterly-rate-adjustment-trackers.pdf?rev=d18c3bd38ba347929b6c0fc1c59a6247).
Its actual PDF content, together with the applicable pre-reset sheets, would
provide a direct route to resolving the missing class factors. The public
IURC search required a CAPTCHA that the user could not pass; known direct
46038 docket links remained readable. A normal browser request to the Duke
tracker returned 403 in the preceding attempt. No CAPTCHA bypass was used.

We's PSC entry points returned 403; issuer certificate delivery returned 451;
the two original 2025 ratebook archive captures were indexed but PDF replay
returned 429 without a Retry-After header. Distinct public Common Crawl
indexes failed upstream, and the independent Arquivo.pt exact-URL history had
no captures. An overwritten government URDB record displaying 2026 prices
under a 2025 effective date was excluded.

## Source-backed billing-cycle work

Duke's filed general term 12.4 supplies the ordinary full schedule for complete
regular 26–34-day cycles. The implementation now validates that bounded cycle
length and keeps designated billing month separate from interval service
dates. Unsupported base-version crossings still reject; this is not a new
partial-period or rate-change proration approximation. Supported March prices
and earlier March bill benchmarks are retained.

The reproducible driver now has an explicit **hypothetical** 12-cycle 2025
reading schedule: January 1–26; January 27–February 26; February 27–March 31;
then April–December calendar cycles. It covers every interval exactly once,
uses twelve monthly charge/block sets, retains DST and avoids the February 27
service-rendered base-rate boundary inside a bill. These are study inputs,
not actual customer readings. The prepared schedule does not authorize
missing January or later prices: in verified-only mode the tariff coverage
gate still rejects the annual request before queueing it. The new provisional
mode requires its separate component assumptions and explicit acceptance.

The January 29 order introduces the optional RS/CS TOU plans; they cannot be
applied retroactively to January. There is also a source discrepancy between
the filed 6.5/7.5 calendar and broader proposal/business guidance. The current
filed-sheet interpretation is preserved, with an explicit TOU-only warning and
calendar-evidence metadata requiring utility confirmation. Standard RS/CS
calculations are unaffected. See [Duke scope](Duke_Indiana.md).

## Validation boundary

The shared validation launcher is used with the system interpreter and GUI
tests excluded. Focused tests cover the unchanged price-gaps, the exact
12-cycle scaffold, DST, full charge/block treatment for confirmed 26-day
March cycles, form-to-worker submission, bill reconciliation and representative
OpenDSS results. Existing prepared actual-year ERA5 inputs are retained under
`.cache/we_duke_weather`; no live API is called by the tests.

The final focused run passed **374 tests in 82.43 seconds** (82.79 seconds
for its pytest phase) on engine
`eb631672f21486f5cfc05c55b3df05d9182f2583e7c7c265564b0f53acfc9325`.
The exact source/test/tool fingerprints and output are retained in
`.cache/we_duke_2025_history_focused/report.json`; the freeze is
`.cache/we_duke_2025_history_candidate.json`. Both new 26-day residential and
commercial API/worker cases returned grid-only, PV-only and PV-plus-battery
bills at the full monthly charge, with 2,492 converged/feasible intervals in
each scenario. Those integration cases use deterministic clear-sky solar and
synthetic native loads; they are not full-year actual-weather validation.
No new browser acceptance was run because frontend code was unchanged. The
earlier browser acceptance remains evidence for its original candidate only.

These earlier results remain partial-period evidence under their original pin.
New full-year residential and commercial matrices are permitted only as
explicitly accepted provisional estimates while the missing histories remain
unverified. Existing partial-period totals must not be relabeled annual, and a
successful solver cannot validate assumed tariff inputs.
