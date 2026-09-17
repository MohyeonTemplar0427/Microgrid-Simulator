# CleanPowerSF commercial billing

Implemented first schedule: standard B-1, secondary voltage, single-phase or
polyphase, Green or SuperGreen, with an explicitly selected PCIA vintage
(2009–2026). The tariff label includes all three account choices; no vintage
is inferred from location, enrollment date, or simulation year. Confirm it on
the actual bill. This is for ordinary non-exempt commercial accounts, not
CARE, exempt government accounts, B1-ST, or special standby service.

## Sources and supported dates

Reviewed September 16, 2026:

- [CleanPowerSF commercial rate tables](https://cleanpowersf.org/commercial-rate-tables),
  effective March 1, 2026: Green B-1 TOU energy and $0.005/kWh SuperGreen premium.
- [PG&E B-1](https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-1.pdf),
  sheets 3–4, advice 7846-E, March 1, 2026: customer charge, total energy,
  generation, bundled PCIA. Sheet 6, advice 7797-E, January 1, 2026:
  CCA billing rule and vintage PCIA.
- [PG&E E-FFS](https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_E-FFS.pdf),
  sheets 2–4, advice 7797-E, January 1, 2026: Small L&P vintage franchise fees.

The combined snapshot accepts March 1 through September 16, 2026 inclusive.
The ending date is the verification cutoff, NOT a published expiration date.
CleanPowerSF's longer published generation window does not prove future PG&E
component rates. Add another verified version to extend coverage; do not
silently extrapolate. Source-derived values are stored in cleanpowersf.py and
pge_commercial.py, pinned with each web study's engine snapshot.

## Accounting

Per interval, delivery energy = PG&E bundled energy - PG&E generation -
bundled PCIA. The bundled PCIA here is NEGATIVE (-0.00990), so removing it
increases the delivery subtotal. Combined import price = delivery +
CleanPowerSF generation + vintage PCIA + vintage franchise fee. The optimizer
uses this combined price, and billing uses exactly the same tariff. Customer
charges are added once, separately. Standard B-1 has no demand charge.

Results expose four additive energy components and the separate customer
charge in both interfaces. PCIA credits remain signed. These components sum
to energy cost; they must not be added again to that subtotal.

Taxes, special discounts/exemptions, standby reservation charges, and NEM/NBT
export settlements are excluded. Carbon emissions continue to use the study's
carbon signal, not the marketed renewable fraction of Green/SuperGreen.
B-1 account eligibility still requires historical demand review.

## Interfaces

Web: select CleanPowerSF + PG&E delivery in Electricity Service (including the
mapped CEC CleanPowerSF choice), then a B-1 phase/product/vintage in Economics.
Incompatible PG&E bundled tariffs are hidden and rejected by the backend.
GUI: select CAISO region, TOU pricing, then the CleanPowerSF B-1 tariff with
matching phase/product/vintage. The tariff explanation displays scope and
coverage. CSV workflows keep their explicit input dispatch prices as before.

## Next: Hetch Hetchy Power

Confirm the site's actual Hetch Hetchy account eligibility, customer class,
voltage and applicable SFPUC schedule. Retrieve the official schedule and
historical effective versions; identify any generation, delivery, demand,
fixed charges, minimum bills, and applicable adjustments. Do not reuse the
CleanPowerSF-plus-PG&E formula unless the Hetch Hetchy schedule explicitly
requires those components. Register validated tariffs in the same backend,
expose them in both interfaces, and test source worked examples, monthly
peaks, date boundaries and result reconciliation. Add export compensation
only after the applicable interconnection/export rules are implemented.
