# Delaware Electric Cooperative R and GS

The regional adapter implements Delaware Electric Cooperative (DEC) ordinary
Residential Service **R** and metered General Service **GS** with DEC supply.
DEC is distinct from Delmarva Power and from Delaware County Electric
Cooperative in New York. Utility membership, supplier, tariff assignment,
Delaware tax status and PJM metadata remain separate account facts. Wholesale
prices do not add a retail bill component.

## Accepted component and date scope

Complete calendar service cycles from **January 2025 through October 2026**
have verified component intersections. The supported cycle has a confirmed
final service-day meter reading, full monthly charges and a matching final-day
bill. Partial, shifted, initial/final, transition-allocated and noncalendar
cycles reject. The interval grid is complete consecutive 15-minute records in
`America/New_York`, including both daylight-saving transitions.

| Component | Residential R | General Service GS |
| --- | ---: | ---: |
| Monthly service charge and ordinary minimum | $28.00 | $30.00 |
| Distribution energy | $0.021400/kWh | $0.022498/kWh |
| Supply, first 700 kWh in each cycle | $0.101600/kWh | $0.111090/kWh |
| Supply, remaining kWh | $0.081600/kWh | $0.101090/kWh |
| Renewable Resource Fund | $0.000178/kWh | $0.000178/kWh |
| PCA, January 2025-April 2026 | -$0.001500/kWh | -$0.001500/kWh |
| PCA, May-October 2026 | $0.012161/kWh | $0.012161/kWh |
| Delaware public utility tax | Exempt | 4.25% of all other charges |

The [November 2024 tariff](https://www.delaware.coop/sites/default/files/2024-11/Tariff%20-%20Revised%20November%202024.pdf),
[March 2025 tariff](https://www.delaware.coop/sites/default/files/2025-03/Tariff%20-%20Revised%20March%202025.pdf)
and [August 2025 tariff](https://www.delaware.coop/sites/default/files/2025-08/Tariff%20-%20Revised%20August%202025.pdf)
retain the ordinary R/GS base rates and negative PCA. Their R/GS leaves state
meter-reading applicability from July 1, 2024. The
[June 2026 tariff](https://www.delaware.coop/sites/default/files/2026-06/Tariff%20-%20Revised%20June%202026%20.pdf)
retains those base rates and lists the new PCA. Its ordinary R leaf 47 is an
image and was visually checked; the optional R-BTP distribution price of
$0.021314/kWh is not substituted for R's $0.021400/kWh.

The [April 2 PCA approval notice](https://www.delaware.coop/press-room/board-approves-pca-change)
sets May 1, 2026 as the change date. Its prose incorrectly calls the decimal
factors cents per kWh. The tariff uses dollar signs, and the notice's roughly
$13 increase at 1,000 kWh confirms the intended dollar units: the exact change
is **$13.661** at 1,000 kWh before GS tax. The old factor is not inferred from
an average bill. Standing dated tariffs and the replacement notice establish
the two periodic PCA regimes; no artificial monthly PCA variation is added.

November-December 2026 remain outside accepted coverage because those cycles
were incomplete or future at the November 7 evidence cutoff. Earlier and later
years also reject. This is **full-year 2025 availability and partial-year 2026
availability**, not full-year 2026 acceptance.

## Eligibility and account requirements

Initial service scope is one ordinary single-phase 120/240 V secondary meter
in **unincorporated Sussex County**. Other localities and account-specific
charges require separate evidence before adding coverage. R covers one
domestic residential housekeeping unit. Farm, multifamily, separate commercial
or industrial uses are excluded from this first R implementation. Motors of
10 hp or greater, power-factor adjustments, unusual loads, facilities charges,
optional TOU/program riders, lighting, special minimums, assistance, budget
billing and other recurring adjustments are excluded by account confirmations.

GS requires a utility-confirmed retained assignment and twelve independently
reviewed actual monthly demand values, each below **50 kW**, ending in the
month immediately before the service cycle. The source says maximum average
monthly demand below 50 kW in the preceding twelve months. The adapter uses a
deliberately bounded subset and requires all twelve actual values plus the
utility's classification review. Simulated load, PV-reduced imports and zero
imports cannot establish eligibility. A longer study needs cycle-specific
history review overrides. Current native load and imports are separately
capped at **25 kW for R** and **49.9 kW for GS**; these are study limits.

The GS tariff has a thirty-month contract reference on leaf 51 and an
at-least-one-year contract clause on leaf 52. The adapter does not invent a
resolution of those provisions. It requires DEC to confirm the active
contract, applicable term, retained assignment and ordinary $30 minimum with
no facilities or transformation addition. Unmetered GS service is excluded.

Tariff section 17 and [30 Del. C. chapter 55](https://delcode.delaware.gov/title30/c055/)
establish ordinary 4.25% GS tax and the residential exemption. GS tax includes
the fixed service charge, delivery, supply, renewable fund and the positive or
negative PCA. Manufacturing/food/agribusiness processing reductions, government
and other exemptions are outside scope. Taxable status is confirmed separately
from the tariff and locality.

## Non-export PV and paired storage

Tariff section 18.2 **Option B, No Sale** bills imports under the applicable
standard schedule without an offset for excess generation. This is the
ordinary-import basis for the initial non-export implementation.

The [official non-export application below 100 kW DC](https://www.delaware.coop/sites/default/files/2024-05/DEC%20Interconnection%20Agreement%20%28Under%20100kW%29%20April%202024%20Non-Export_1.pdf)
requires preliminary review, non-export protection and final permission to
operate. It also contains a sizing/history review and directs members adding
storage to submit the separate
[battery application](https://www.delaware.coop/sites/default/files/2023-09/DEC%20Interconnection%20Agreement%20%28Battery%20Storage%29%2C%20Updated.pdf).
The adapter requires written final approval active by the first cycle day for
the exact PV design, accepted sizing/history and ordinary import terms without
another recurring charge. Installed PV DC nameplate must be finite, positive
and below 100 kW. This is the chosen agreement scope, not a general statement
that larger projects cannot interconnect.

Paired storage additionally requires the final battery supplement for the
exact design, **PV-only charging and zero export**, with no optional battery
program rider. PV-only charging is an implementation restriction, not a
universal DEC tariff rule. Standalone storage, grid charging, net metering,
energy sales, credit banks, standby service and optional dispatch credits are
unsupported. A public interconnection form does not establish an individual
member's approval or unchanged recurring charges.

Defaults leave account confirmations false. `hypothetical_defaults()` marks
explicit hypothetical facts and supplies a representative July 2026 cycle;
it is not utility evidence. The catalog proposes R at 3 kW and GS at 5 kW.

## Evidence and validation

The [source ledger](utility_sources/delaware_coop_de/sources.json) records the
22 monthly intersections, original source URLs, original PDF/tax-HTML hashes,
component locators, unit conflict, scope exclusions and retrieval failures.
Originals and the rendered R leaf remain under
`.cache/delaware_coop_de/sources/`. Some public HTML routes returned HTTP 403
to the system network client. The precise 2026 notice was read through the web
tool and its extraction was saved and hashed separately; that hash is not
represented as original HTML. An older February 16 PCA-increase article was
identified as inapplicable and is not used for 2026 rates.

[Independent Decimal benchmarks](utility_sources/delaware_coop_de/independent_benchmarks.json)
use literal source transcriptions without importing executable rate data. At
1,000 kWh, unrounded ordinary R totals are $143.678 before May 2026 and
$157.339 after; ordinary GS totals are $166.034805 and $180.2763975. Exact
component arithmetic is retained alongside the shared study's half-up cent
rounding; it does not claim exact utility invoice rounding or an optimum of
rounded cash payments. Account-specific capital-credit retirements are not
forecast or deducted.

Focused development checks use:

```sh
/usr/local/bin/python3 tools/validate.py --tier focused --test test/test_delaware_coop_de.py --output .cache/delaware_coop_de/development
```

The tests cover literal/Decimal bills, exact symbolic parity across the
decreasing 700-kWh supply tier, PCA and tax boundaries, all supported months,
DST, malformed intervals, independent eligibility, native/import limits,
export/state rejection, exact DER approvals and PV-battery dispatch/SOC/itemized
rebilling. The November 7 development run passed **176 tests** with no failures,
errors or skips; pytest phase wall time was **2.42 seconds**. Its pre-freeze
receipt is `.cache/delaware_coop_de/development/report.json`, engine identity
`b8dfd196b4f3f659b31047d036692506cb1427ab42eef5ea15875c46cfc59fc6`.
The original-byte audit also verified all ten retained PDF/tax-HTML hashes.
The parent batch owns final frozen-candidate integration, selected
historical/electrical matrices and the concise browser pass. Focused adapter
checks do not establish those later acceptance claims. Desktop GUI tests and
native GUI launches are excluded.
