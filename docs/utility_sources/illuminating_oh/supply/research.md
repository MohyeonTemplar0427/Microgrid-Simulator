# Illuminating Company supply and tax review

Reviewed October 31, 2026. The retained literal table uses USD/kWh, converted
from each filed cents/kWh table, with RS/GS capacity kept separate. It is a
supply-component intersection, not a claim that delivery or every calendar
cycle is verified. Root's final adapter narrows the accepted dates further.

GEN Sheet 114 is retail SSO generation: the capacity cost has already been
converted to a per-kWh amount. Its wholesale derivation does not authorize a
second PJM LMP, PLC, NSPL, capacity, transmission, losses or CAT charge. NMB is a
separate delivery component. GCR1, AER and NDU are separately itemized; they are
not another rounded PTC total. GEN19 distinguishes summer and winter energy;
GEN20 has one energy and one capacity table for all seasons. PIPP, competitive
supplier, TOD/critical-peak/real-time and special-contract service are excluded.

## Source selections

`sources.json` records original or archived official utility URLs, complete PDF
hashes, page counts, selected one-based PDF pages and excerpt hashes. January's
current old-file name contains a January 2025 composite; archived 2024 annual
tariff is a different snapshot and cannot replace it. The June 12 and August 25,
2025 captures are complete PDFs; the later official annual books establish the
October quarter supply tables and GEN19/20.

Representative June 2025 GEN19, July-quarter negative NDU67, June 2026 GEN20
and SKT92 tables were rendered and visually checked. The negative NDU sign and
the change from seasonal to flat GEN energy were confirmed.

## Gaps and blocked routes

CDX on the 2025 URL found May 13, June 12 and August 25 snapshots. The May 13
snapshot is inherently truncated at 5 MiB. The 2026 URL has May 10 and October
8 captures; May 10 is likewise inherently truncated at 5 MiB of an indicated
6,264,014 bytes, with archive Warning 299. Neither has an EOF. A bounded pypdf
then isolated PyMuPDF recovery produced no pages. No recovered rates were used
and the same failed route was not repeatedly requested. Receipts, original
partial bytes and recovery logs are retained in the private supply cache.

The May 2025 GEN18 and earlier ESP-IV component chronology therefore remain
unverified. Earlier 2026 quarter supply chronology is also unverified. A primary
search cache exposes a January 2026 NDU value, but that isolated result cannot
establish a complete billing window. Missing components are not reconstructed
from PTC totals or carried forward. July/August 2025 supply components are
known, but missing delivery LGR12 and crossing allocation prevent a complete
calendar-bill claim. A complete actual 2025 annual bill is unavailable.

## Ohio tax rule

Tariff Sheet92 expressly requires SKT consistency with ORC5727.81. Its
subsection A gives a 30-day measurement table (2,000 and 15,000 kWh thresholds)
and a distinct non-30-day calculation based on daily average usage: first 67,
then through 500 kWh/day. Thus non-30-day energy thresholds are 67 times local
calendar days and 500 times local calendar days, at .00465/.00419/.00363 USD
per kWh; the 30-day case retains 2,000/15,000 rather than 2,010/15,000. DST
elapsed hours do not redefine calendar measurement days. This is explicit
statutory incorporation, not a guessed daily fixed-fee allocation.

Sheet92 separately grosses SKT up by 1/(1-CAT); ORC5751.03 supplies .0026.
That does not add CAT again to every filed rate. ORC5739.02(B)(7) exempts wired
electricity from sales tax; the authenticated 2023 and current 2025 versions
retain that exemption. `tax_sources.json` and selected statutory excerpts pin
these primary records. No local municipal/franchise-specific rate was verified;
the account scope requires separate confirmation of no additional local charge,
ordinary non-self-assessing taxation and no special exemptions.
