# PPL Electric Utilities, Pennsylvania

Reviewed October 25, 2026. The shared regional backend supports ordinary
single-phase residential **RS** and single-phase secondary commercial
**GS-1**, with PPL fixed-price **GSC-1 default supply**, for complete calendar
meter cycles from **January 2025 through October 2026**. These are bounded
account arrangements, not the complete PPL tariff book. The
[source ledger](utility_sources/ppl_pa/sources.json) records original document
hashes and selected pages; original PDFs remain in ignored research storage.

PPL's distribution territory, Pennsylvania jurisdiction, retail supplier,
PJM transmission zone and wholesale pricing location remain separate facts.
The first hypothetical site is outside Philadelphia/Allegheny in Lehigh
County. Coordinates establish weather inputs, not utility eligibility or tax
status. No PJM LMP is substituted for the retail GSC-1 price.

## Supported account and study scope

- One ordinary single-phase 120/240 V meter and service, unity billing power
  factor, no special facilities, assistance discounts, alternate supplier,
  nonprofit option, discontinued FC demand cap or standby agreement.
- Residential eligibility is a single dwelling or individually metered unit.
  Master-metered multiple dwellings, mixed commercial uses and other special
  RS applications are outside this first scope.
- GS-1 has one 15-minute monthly maximum, rounded to the nearest whole kW
  with half-up ties. It has no modeled prior-month ratchet. The representative
  small-office profile has a 20 kW reference peak; the bounded study requires
  imports below 100 kW, independently of utility-confirmed classification.
- Consecutive 15-minute data and complete calendar cycles are required.
  Spring/fall DST changes alter elapsed hours and interval counts. There is
  no weekday/holiday TOU override for the selected fixed-price options.
- PV-only and PV-plus-battery cases require explicit utility-approved ordinary
  renewable service and interconnection evidence or an explicitly hypothetical
  agreement. Combined PV/battery nameplate is conservatively bounded to
  50 kW in this study; it is not automatic interconnection approval.
- Export is constrained to zero. Curtailment is preserved. This does not
  implement net-metering credits, credit banks, annual payout, special
  standby contracts or standalone storage.

Rule 9 describes ordinary 26–35-day billing and proration for short or long
initial/final periods, but a general per-charge allocation method has not been
implemented here. Shifted and partial cycles reject. Each full-year run
explicitly treats its twelve calendar cycles as hypothetical meter readings;
it must not be presented as an exact reconstruction of actual meter cycles.

## Dated charges and double-counting controls

Residential RS published distribution prices already include the active
smart-meter/competitive-enhancement customer adjustments and the efficiency,
universal-service and storm components. Those are not added again. Ordinary
GS-1 uses its filed base customer/demand charges and separately applies its
commercial riders.

| Period beginning | RS customer / month | RS composite distribution / kWh |
| --- | ---: | ---: |
| January 1, 2025 | $15.62 | $0.04990 |
| April 1, 2025 | $15.70 | $0.04990 |
| June 1, 2025 | $15.70 | $0.05049 |
| July 1, 2025 | $15.58 | $0.05049 |
| October 1, 2025 | $15.52 | $0.05049 |
| January 1, 2026 | $15.48 | $0.04968 |
| April 1, 2026 | $15.50 | $0.04968 |
| June 1, 2026 | $15.50 | $0.04927 |
| July 1, 2026 | $15.00 | $0.06157 |
| October 1, 2026 | $15.00 | $0.06175 |

Ordinary GS-1 base charges are $22/month plus $4.361 per billing kW through
June 2026, then $27.22/month plus $5.923/kW from July 1, 2026. Pre-July
smart-meter charges change quarterly; the January 2026 official business
history records each 2025 factor. The competitive-enhancement adjustment is
-$0.01/month before July 2026. The July 2026 tariff removes the separate
SMR/CER riders as part of the new base-rate structure.

Commercial Act 129 recovery is $0.00243/kWh through May 2025,
$0.00166 from June 2025 through May 2026, then $0.00071 from June 2026.
The expired ACR4 factor retained in a later tariff book is not added to its
successor ACR5. Storm recovery is separately dated; the July 2026 reset and
October 2026 reinstatement are distinct versions.

GSC-1 and TSC are shown separately in results but their sum is the published
Price to Compare, before its very small Part 2 state-tax adjustment. Their
filed factors already include the merchant-function charge and statutory
gross-receipts tax. Default supply procurement includes capacity costs and
the TSC recovers retail transmission costs; adding wholesale LMP, a capacity
PLC amount, or a transmission peak tag would double count this arrangement.
Large-account GSC-2/MRPL rules are not implemented as a substitute.

| Service period beginning | RS GSC-1 / TSC, $/kWh | GS-1 GSC-1 / TSC, $/kWh |
| --- | --- | --- |
| January 1, 2025 | 0.07225 / 0.03546 | 0.07458 / 0.02988 |
| June 1, 2025 | 0.09166 / 0.03324 | 0.08956 / 0.03158 |
| December 1, 2025 | 0.09610 / 0.03343 | 0.09379 / 0.03302 |
| June 1, 2026 | 0.09804 / 0.03343 | 0.09443 / 0.03302 |
| July 1, 2026 | 0.09753 / 0.03326 | 0.09445 / 0.03303 |

The off-cycle July 2026 supply update must not be hidden behind a generic
June/December price-change assumption. Prices published beyond October are
retained as research evidence, not permission to extend the executable window.

## Bill-date riders, tax and reconciliation

The explicit **bill-rendered date** selects the whole-bill DSIC and TCJA
factors. DSIC is 5% before March 13, 2025, 7.43% from March 13, 7.50% from
April 1, and zero from July 1, 2026. The TCJA base-distribution credit is
8% in 2025, 3.75% from January 1, 2026, then zero on bills rendered from
April 10, 2026. Neither mid-month change is allocated to actual consumption
on either side of its bill-date boundary.

TCJA excludes STAS and automatic-adjustment rider revenue. For RS, its
pre-July base is $14.09 plus $0.03534/kWh, rather than the larger published
composite. For GS-1 it is the base customer plus rounded demand charge.
The calculation order is:

1. Calculate base distribution and applicable distribution riders, with the
   separate TCJA credit applied only to base distribution.
2. Apply DSIC to the resulting distribution amount, excluding STAS.
3. Apply distribution STAS to distribution including DSIC. TCJA does not
   directly credit DSIC; the DSIC rule's prohibition on credits/discounts is
   preserved.
4. Calculate GSC-1 and TSC once; apply Part 2 STAS of 0.001% to their sum.
5. Apply ordinary commercial Pennsylvania sales tax of 6% last. Residential
   electricity is exempt; other localities or exemptions are rejected.

Distribution STAS is -0.280% in 2025, -0.311% from January 2026, and
+0.008% from July 2026. The modeled state-only account facts are explicit;
the calculator does not derive exemption or local taxes from the tariff name.

Independent Decimal calculations for 1,000 kWh give these component-rounded
study totals:

| Complete cycle | Residential RS | GS-1, 3 kW measured/billed peak |
| --- | ---: | ---: |
| July 2025 | $191.49 | $171.44 |
| June 2026 | $200.88 | $180.06 |

The [benchmark records](utility_sources/ppl_pa/independent_benchmarks.json)
are independent tariff calculations, not measured customer statements.
The shared result contract retains unrounded arithmetic and rounds individual
lines half-up to cents before summing. Rounding only the final commercial
July total would instead give $171.45; that is a rounding-policy difference,
not a change in the underlying charge formula.

## Dispatch and numerical demand boundary

The optimizer and bill share the same charge expressions and minimize the
complete modeled utility bill by default. Battery wear remains separately
reported and is included only when requested. A full-year study uses rolling
monthly perfect foresight with linked SOC; it does not prove a joint annual
optimum or implement a forecast-based controller.

GS-1's half-up discontinuity uses one integer billing-kW variable, rather
than thousands of per-interval integer selectors. The dispatch constraint
retains **0.00001 kW (0.01 W) of conservative headroom** below a half-kW tie
to prevent solver feasibility noise from pricing an exact tie downward.
The numerical bill explicitly rejects peaks inside that open guard band
(allowing 0.000000001 kW at its lower edge for floating-point representation).
For example, 3.499995 kW is rejected for exact numerical reconciliation;
3.49999 kW bills 3 kW and an exact 3.5 kW bills 4 kW. Convex fixed inputs
inside the rejected band conservatively select the upper unit. This is a
documented numerical limitation, not global mathematical equivalence at every
real-valued demand boundary.

Shared OpenDSS replay remains independent of the tariff. Its representative
network, losses and PCC measurements do not alter scheduled flows used for
retail bills. It adds quasi-static validation after optimization, without
transient analysis or network constraints in dispatch.

## Verification and unsupported scope

`test/test_ppl_pa.py` checks independent 2025/2026 component arithmetic,
bill-rendered DSIC/TCJA dates, July supply/base transitions, October storm
changes, source-priced demand rounding, numerical/CVXPY reconciliation away
from the explicit guard band, DST, missing/duplicate intervals, eligibility,
zero-export safeguards and independent benchmark totals. Root workflow and
annual matrix receipts are recorded separately under the frozen candidate.

TOU, competitive supplier contracts, GSC-2 large-account capacity/MRPL and
transmission obligations, export credits/true-up, other tax jurisdictions,
standby, partial or shifted meter cycles and unverified dates remain
unsupported. PPL publishes Price-to-Compare history back to 2012; the
ten-year research target does not make older delivery/rider combinations
executable without their own verified component histories.
