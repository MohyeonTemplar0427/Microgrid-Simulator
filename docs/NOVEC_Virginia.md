# Northern Virginia Electric Cooperative R-1 and SC-1

The regional adapter implements ordinary NOVEC residential R-1 and single-phase
Small Commercial Service SC-1 with NOVEC electricity supply. Distribution utility,
supplier, Virginia jurisdiction, Prince William County taxes and PJM Dominion
(`DOM`) metadata remain separate. Wholesale price inputs add no retail charge.

## Verified dates and sources

Complete matching calendar service and bill cycles are supported for
**January–December 2025**. The current R-1 sheet is effective January 1, 2024;
SC-1 is effective April 1, 2023. The 2025 January/February and July official
customer notices establish PCA credits/charges for both residential and
commercial accounts. July's notice explicitly states that its factor applies
for the remainder of 2025. No rate is inferred from a neighboring utility.

| Component | R-1 | Single-phase SC-1 |
| --- | ---: | ---: |
| Monthly distribution service charge | $21.30 | $26.78 |
| Distribution energy | $0.01348/kWh | $0.02064/kWh |
| Electricity supply | $0.09731/kWh | $0.09242/kWh |
| PCA, January–June 2025 | −$0.008/kWh | −$0.008/kWh |
| PCA, July–December 2025 | $0.002/kWh | $0.002/kWh |

These are ordinary full monthly charges and service-charge minimums. R-1's
first-300-kWh and above-300-kWh distribution blocks have equal rates. The
initial model uses one 120/240 V secondary meter and complete consecutive
Eastern-time 15-minute records. Its final-day bill date must match the service
month. Partial, shifted, noncalendar or differently allocated cycles reject.

**All 2026 cycles remain blocked.** A secondary calculator quotes a 2026 PCA
of $0.01320/kWh, but the original dated primary notice has not been recovered.
The current official PCA page was replaced by a November 1, 2026 notice.
That notice gives $0.02482/kWh and a 5% distribution increase, but not the
exact revised R-1/SC-1 fixed and volumetric vectors. The linked rate sheets
still show the older values. Neither the older PCA, a percentage-based
reconstruction, nor a 1,000-kWh illustration is substituted for a complete
filed component stack. Official bill examples currently retrieved are dated
2022, so a secondary claim of a June 2026 example is not adopted.

The [source ledger](utility_sources/novec_va/sources.json) distinguishes filed
informational tariffs, official notices, state/county sources, visual SC-1
transcription and blocked retrievals. Downloaded originals, rendered SC-1 pages,
text and hashes are retained privately under `.cache/novec_va/sources/`.

## Eligibility and tax scope

R-1 covers ordinary residential uses. Residential-farm/church provisions are
in the tariff but outside this initial residential study scope. Single-phase
individual motors must not exceed 10 horsepower. Optional EV/TOU, lighting,
special facilities, supplier choice, budget billing and assistance/other
adjustments are outside the declared account scope.

SC-1 applies to ordinary commercial and small-power consumers unless another
schedule specifically applies. Two months exceeding 30 kW in the preceding
twelve months trigger LP-1 for the succeeding twelve months, with the filed
advance notice rule. Monitoring of energy and demand may be installed at
NOVEC's discretion above 6,000 kWh in a billing month.

The initial SC-1 scope is deliberately narrower: retain independent NOVEC
assignment/no transfer obligation and twelve actual prior monthly demands
**each below 30 kW**, ending the month before the cycle. Native load and
imports are separately capped at 29.9 kW and 5,999 kWh per month. R-1 has a
25 kW native/import study cap. Simulated low demand or PV-reduced imports
cannot establish eligibility. The review evidence must remain applicable to
each cycle, with cycle-specific overrides for a longer study.

Initial tax coverage is ordinary private taxable member service in
**unincorporated Prince William County**. State consumption, actual SCC special
regulatory levy, local consumption and county consumer utility tax are itemized
separately. Governmental and special exemptions, cooperative federal-power
reductions and data-center treatment are excluded by explicit account facts.

State consumption marginal rates are $0.00102, $0.00065 and $0.00050/kWh
at the 2,500 and 50,000 kWh thresholds. Local consumption rates are $0.00038,
$0.00024 and $0.00018/kWh. The actual SCC regulatory levy is $0.000165,
$0.000110 and $0.000077/kWh through July 2025, then $0.000165/kWh in all
three tiers from **August 1, 2025**, according to the SCC. Dominion's distinct
August 16 meter-read applicability is not imported into NOVEC. The higher
statutory maximum is not used as the actual levy.

Prince William County's ordinary electric consumer tax is the lesser of
`$1.40 + $0.01509 × imported kWh` and `$3.00` for residential, or the lesser
of `$2.29 + $0.013487 × imported kWh` and `$100.00` for commercial. FY2025
and FY2026 county publications corroborate the same rates. These active-service
minimums also apply at zero imports. Other municipalities, county tax relief
and special status are not silently assigned zero tax.

## Non-export PV and storage

NOVEC's current Terms and Conditions require approval of the generating
equipment and expressly prohibit parallel operation unless specifically
approved. Initial PV studies therefore require final interconnection approval
effective before the cycle plus written NOVEC confirmation that the exact
non-export configuration retains ordinary import billing without other charges
or minimums. Paired storage charges only from onsite PV. Standalone batteries,
grid charging, export settlement, NEM credit banks and generation-market sales
are unsupported. Hypothetical accounts explicitly label their approval and
eligibility assumptions; defaults leave confirmations unchecked.

## Development checks and evidence limits

The utility-specific [focused receipt](../.cache/novec_va/development/report.json)
records **114 passing tests**, with no skips or failures. Independent literal
Decimal benchmarks cover all three 2025 component regimes, the county tax cap,
the state-tax boundary and zero-import minimums. Numeric/symbolic parity,
complete-year monthly coverage, DST, missing/duplicate intervals, native and
import bounds, independent demand history, taxes, DER approval and unsupported
dates/settlement are exercised. No customer invoice was supplied.

The separate saved-artifact Decimal auditor is retained at
`.cache/novec_va/independent_rebill.py`. Root batch acceptance owns the final
frozen-engine, full-year billing/dispatch, all-interval electrical, worker,
artifact and browser evidence. Development tests alone do not establish those
later acceptance assertions or extend 2026 coverage.
