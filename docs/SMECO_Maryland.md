# SMECO Maryland R and GSS SOS: researched scope, billing blocked

The catalog identifies Southern Maryland Electric Cooperative (SMECO)
Schedule R ordinary residential and Schedule GSS General Service Small
Standard Offer Service. **No complete 2025–2026 billing cycle is enabled.**
Both plans are explicitly unavailable for billing and dispatch until the
required approved monthly components are reconciled. This is a source-led
boundary, not an implemented price estimate or recurring-charge subtotal.

The [source ledger](utility_sources/smeco_md/sources.json) records reviewed
official documents, downloaded hashes, pending rates and blocked retrievals.
The current 193-page utility tariff book and public rates page are retained
under `.cache/smeco_md/sources/`.

## Verified structure and unresolved chronology

Current filed sheets identify R residential and GSS small commercial SOS.
R applies to ordinary residences and eligible combined farm/residential use.
GSS requires an independently established peak below 25 kW and retained utility
classification. Both have separate supply, distribution and facilities charges;
summer is the May–September **billing months**, winter October–April.

The approved August 1, 2026 base sheets show R supply at $0.1248/$0.1319 per
kWh summer/winter, distribution at $0.05404/kWh and facilities at $9.75/month.
GSS supply is $0.1150/$0.1218, distribution $0.04488/kWh and single-phase
secondary facilities $18.28/month. These are component observations; they do
not establish any complete executable bill. GSS also defines 15-minute demand,
prior-eleven-month and contract floors, and power-factor adjustment. Its current
base sheet has no standalone demand-price row, which does not justify assuming
zero for every historical monthly rider or classification.

Mandatory monthly PCA and BSA factors remain unresolved. The public residential
price-to-compare history is **base SOS plus PCA only**; it excludes delivery,
BSA, facilities and other riders/taxes. An official September 2026 newsletter
corroborates August residential supply of $0.132409/kWh and approval of the
base change. It supplies no complete BSA/delivery/tax intersection.

The rates page explicitly labels its November 2026 monthly factors pending.
The separate customer-choice page also labels its retained October figures
pending. Neither elapsed time nor the availability of a later page turns a
pending filing into approved-rate evidence. No such value enters billing.

The current book supplies the BSA formula, January 2026 EMC, June 2025 USP,
the $0.000620/kWh franchise-tax factor, and the obligation to collect the
Maryland environmental surcharge. The separately linked USP PDF is effective
December 1, 2024; the combined book's sheets 177–178 (PDF pages 190–191) are
effective June 1, 2025. Both show residential $0.32/month and the same commercial
revenue tiers. These two source versions are retained separately. Commercial
USP depends on independent prior-year distribution revenue and first-quarter
reassignment. Superseded component intersections and account-specific refunds
still require reconciliation before acceptance. Their amounts are not assumed
zero.

### November 6, 2026 component follow-up

The official [summer refund notice](https://www.smeco.coop/news-releases/smeco-to-distribute-legislative-energy-relief-refund/)
identifies August 2025 credits of $40, $55 or $67.89, requiring an active
account as of August 1 and electricity use during the year ending March 31,
2025. Amounts depend on that year's average usage. Its published ranges overlap
at 400 and 1,200 kWh; no boundary rule is invented. The official
[winter refund page](https://www.smeco.coop/relief/) identifies January 2026
credits of $40–$85.90 across seven tiers, an active account as of December 1,
2025, and positive historical use in the year ending September 30, 2025.
These historical account facts cannot be inferred from a modeled load or
PV-reduced imports. Fractional-average tier assignment, exact eligibility and
credit-balance settlement still require verification before implementation.

[COMAR 03.06.01.10](https://regs.maryland.gov/us/md/exec/comar/03.06.01.10)
confirms residential-schedule sales are exempt and excludes county tax,
environmental surcharge and late-payment penalties from the sales-tax base.
[Public Utilities §7-203](https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=gpu&section=7-203)
sets the customer environmental cap at the lesser of $0.000150/kWh and
$1,000/month;
[COMAR 20.50.01.04](https://regs.maryland.gov/us/md/exec/comar/20.50.01.04)
requires half-up cent rounding. The statutory cap is not an approved historical
SMECO factor. Actual dated environmental rates, locality and the remaining
taxable-charge reconciliation are still needed.

## Source access and identity

The PSC case 9456 index identifies monthly BSA filings, but direct public
retrieval returned 403; the old official host timed out. A distinct official
WordPress media-archive query found the static BSA formula and PCA chart
images rather than approved monthly full stacks. A bounded newsletter search
corroborated supply only. Those gaps are recorded instead of retrying the same
blocked route or reconstructing unknown rates from a formula.

A November 6 follow-up reached distinct public PSC filing-report and MailLog
search routes. Case 9456's August 2026 BSA is **ML332289**, filed July 20,
2026. The October 22 filing report identifies November 2026 **BSA ML335643**
and monthly **PCA ML335644** (Case 9504); the PCA entry does not state its billing
month. Filing entries prove neither their numeric contents nor approval. The
documented filing-view endpoint returned 403, and the alternate search form
linked the same endpoint; that download route was stopped.

A Calvert County public meeting packet was also checked as a possible bill
benchmark. PDF page 26 is an accounting ledger, without tariff class, billed
kWh/kW, meter dates or unit factors. It establishes no R/GSS rate or independent
bill benchmark. The new retrievals, hashes, visual review and filing metadata
are retained in `.cache/smeco_md/gap_20261106/`, alongside the non-monthly source
review. No additional billing period was enabled.

To enable a proposed cycle, obtain the actual approved R/GSS monthly PCA
(including any GSS demand factor) and BSA sheets and their approval/applicability
records; the dated base/EMC/USP/environmental stack; confirmed locality,
taxability and historical USP assignment; and applicable residential credit
eligibility/settlement. For August 2026, ML332289 is a specific starting point,
but its filing metadata alone is insufficient. Then reconcile independent
bills and the ordinary non-export interconnection terms before acceptance.

SMECO is the distribution utility and proposed SOS supplier; jurisdiction is
Maryland. PJM's emergency-region table separately identifies **SMECO** as a
transmission zone inside MIDATL. PJM market/forecast tables group the SMECO
area under **PEPCO**; that distinct aggregation does not select a wholesale
pricing node, replace SMECO's utility identity or add a retail charge.

## Non-export and validation boundary

Non-export operation does not bypass the tariff gap. The utility's Part VIII
requires prior written approval for parallel generation. Exact import-billing
and PV/storage terms must be verified before enabling those configurations;
no generic approval, export settlement, credit bank or storage treatment is
assumed. Hypothetical account defaults also remain blocked.

Focused tests confirm both catalog plans are disabled, every requested monthly
cycle rejects, pending factors or account confirmations cannot enable billing,
and DST/malformed intervals cannot bypass missing source evidence. No complete
SMECO bill benchmark, simulation, solver proof, annual electrical acceptance
or browser execution is claimed. The parent batch report owns the final
candidate identity and targeted-check receipt.
