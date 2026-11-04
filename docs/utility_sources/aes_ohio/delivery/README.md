# AES Ohio adopted delivery evidence

Verified November 2, 2026. This folder contains numerical facts and attributable
source metadata for adopted P.U.C.O. No. 17 D17 Residential and ordinary
single-phase, secondary-metered D19 Secondary service. It contains no production
implementation or acceptance claim.

- [Exact rate rows and component intersections](rates.json).
- [Original URLs, SHA-256 hashes, private paths and failed routes](source_ledger.json).
- Private originals, extracted text, retrieval receipts and 17 visually reviewed
  PDF-page renders: `.cache/aes_ohio/sources/delivery/`.

## Source selection and date scope

The [official tariff page](https://www.aes-ohio.com/rates-tariffs) starts with a
proposed distribution tariff download. That proposal was excluded. Adopted
customer tariff links lower on the page, dated AES archives, and official PUCO
assembled books supply these facts. The live HTML was preserved because cached
web results still linked older D39/D41 sheets after the November 1, 2026 update.

The official PUCO assembled distribution book at the unnumbered URL is a June 1,
2025 snapshot; the `(1)` URL is a December 1, 2024 snapshot. They establish
historical scope, not current rates. Their original tariff indices and the AES
January/July/October 2025, November 6, 2025, January/April/July/November 2026
indices bound continuity and expose intervening revisions. Source dates and
printed sheet revisions control over filenames and web crawl dates.

The complete **delivery component** source intersections are January-June 2025
and June-November 2026. These are not independently executable whole bills:
dated G10/T08, D33 and eligibility come from the other ledgers; D19 requires
history; D43 requires one-time refund state. No complete-year or December 2026
coverage is established. March-June 2025 is a source-complete delivery window
covering the April rider and June storm/transmission changes.

Most riders expressly use a bills-rendered basis. D28 uses the first billing
cycle unit of its effective month; D27/D40 changed August 14, 2025. The exact
day boundaries remain in the rate rows. They do not authorize service-day
proration. November 2025 is blocked: the adopted November 6 index identifies
the new base sheets, but their numerical originals and an allocation rule for
mixed cycles were not recovered.

## Ordinary D19 determinants

D19 measures greatest 30-minute integrated kW. Its general demand rule selects
current on-peak demand, 75% of current off-peak demand, and 75% of the greatest
qualifying prior demand in the preceding eleven months. The qualifying
calendar months are January, February, June, July, August and December. D19
describes the prior determinant as "such off-peak or on-peak demand as used
for billing".

Below 1,000 kW no demand may be designated off-peak without election of the
$20/month metering option. That option has a one-year minimum and 30 days'
written termination notice. Restricting the initial domain to actual maxima
at or below 100 kW, with no off-peak election in the current or prior eleven
months, removes the off-peak discount ambiguity. Within that restricted
domain, interpreting each prior determinant as that month's actual all-hours
30-minute maximum gives:

`billing_kW = max(current_actual_peak, 0.75 * max(qualifying_prior_actual_peaks))`

That determinant interpretation is explicitly an inference from the tariff's
three demand paragraphs; do not recursively substitute ratchet-inflated
billing demand. Reject missing history rather than assume zero. No D19
excess-five-kW reduction, contract-demand floor or ordinary PF surcharge is
stated. T08 first-five-kW and NSPL terms are separate components.

The minimum base charge is the customer charge. The special 85%-of-connected-
load provision disallows the low-load-factor cap and is excluded. Primary-
voltage metering adjusts billing kW/kWh downward 1% and is excluded. Unmetered
service, county fairs/agricultural societies, off-peak elections and special
service agreements remain outside this ordinary subset.

## Low-load-factor selection and material limits

D19 caps its demand/energy provisions jointly with T08, with a separately
specified D19 component cap. Its monthly customer charge remains separate.
The filed D19 sheets give no interim-cent-rounding instruction and do not
specify an equality tie rule.

The supply agent's official commercial calculator trace is preserved at
`.cache/aes_ohio/sources/supply/formula_review.json`. It establishes:

- The combined comparator excludes customer charges and separately rounds
  its normal variable demand/energy test components. The normal T08 side
  includes its first-five-kW, excess-five-kW and NSPL determinants.
- The low-load branch is selected only when the rounded combined cap is
  strictly below the rounded ordinary test. Equality selects ordinary.
- When selected, D19 and T08 each use their own low-load variable rate.
- D29, D36 and D41 apply to the customer charge plus the **selected D19**
  variable amount, excluding T08.

Combined-charge equality does not establish equality of the D19 component.
Consequently, percentage riders can produce different final bills for the two
branches at a combined equality. A solver selector allowing either branch at
equality needs a proven equivalent result or a rejected unresolved equality
band. An unrounded tariff comparator does not prove parity with the rounded
official calculator or exact rounded-invoice optimization.

The September 2025 D19 sheet prints combined cap `$0.1196054/kWh` and D19 cap
`$0.0646420/kWh`. The calculator retains `$0.11960537` and `$0.06464197`.
Preserve that precision discrepancy; the ledger records the filed sheet's
original numbers without silently replacing them with calculator values.

## Rider distinctions and remaining gaps

D31 is 2.82% of base distribution for D17, but $3.66/bill for single-phase
D19. D37 applies only to D17/D18; its new June 2026 residential energy charge
does not apply to D19. D27 and D40 use the first 833,000 kWh for D19. D28 has a
separate over-833,000-kWh rate. D34 switching fees are transactional and are
not ordinary recurring charges; no switching event is included.

D41's November 6, 2025 original prints **positive 2.5675%**, despite its credit
name; visual review confirms the sign. November 1, 2026 changes it to
**-0.2577%**. D39 changes from zero to class-specific charges November 1, 2026.
D43 supplies a **one-time** credit beginning August 1, 2026: $14.39 for D17 and
$49.27 for D19. Its original does not state a terminal window or prior-receipt
state; it must never become a recurring monthly credit.

The rate ledger lists every unsupported period and missing component. The
bounded archive pass did not recover the July 2025 D40 original, August 2025
D41 original, October 2025 D29/D36 originals, November 6 base/rider originals,
December 2025 D30 original, or January 2026 D19/D29/D36 originals. The official
PUCO case index route returned Request Rejected and was stopped. No missing
rate was inferred, no unchanged failing route was retried, and no passing
simulation or matrix was relabeled as evidence for these research artifacts.
