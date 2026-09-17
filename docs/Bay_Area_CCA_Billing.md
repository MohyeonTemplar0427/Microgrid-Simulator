# Peninsula and South Bay commercial billing

This extension adds ordinary B-1 secondary-voltage import billing for three
providers. Single-phase and polyphase customer charges are selectable; phase
is not the same as primary/secondary voltage. Confirm provider enrollment,
product, phase, PCIA vintage, and schedule eligibility on the actual account.
CEC territory matching suggests providers and never proves enrollment.

| Provider | Products | Supported service dates (2026) | PCIA vintages |
|---|---|---|---|
| WestLight Energy / Peninsula Clean Energy | ECOplus, ECO100 | July 1–September 16 | 2009–2026 |
| Silicon Valley Clean Energy | GreenStart, GreenPrime | April 6–September 16 | 2009–2026 |
| San José Clean Energy | GreenSource, TotalGreen | March 1–September 16 | 2018–2020 |

Dates are deliberately bounded snapshots, not assertions that the tariffs
expire September 16. Older generation versions are not substituted. The
CleanPowerSF cutoff and existing Hetch Hetchy coverage remain unchanged.

## Sources and verification

Reviewed September 17, 2026:

- [WestLight commercial schedule, July 1, 2026](https://www.westlightenergy.org/wp-content/uploads/2026/07/Commercial-WestLight-Energy-Rates-Effective-July-1-2026.pdf):
  page 1 B-1 generation; page 15 ECO100 ($0.01/kWh) and comparison-vintage note.
  The provider's former Peninsula website redirects to WestLight. Both names
  remain visible; its CEC record still says Peninsula Clean Energy.
- [SVCE commercial schedule, January 1, 2026](https://www.svcleanenergy.org/wp-content/uploads/SVCE-Commercial-Rate-Sheet-January-1-2026.pdf):
  page 2 B-1 generation; page 31 GreenPrime ($0.00740/kWh) and timing notes.
  Its spring daylight-saving adjustment is not implemented. Coverage begins
  April 6, after the first Sunday in April, to exclude that window explicitly.
- [SJCE commercial schedule, March 1, 2026](https://sanjosecleanenergy.org/wp-content/uploads/2026/06/SJCE-Commercial-Rates-March-1-2026-1.pdf):
  page 1 B-1; page 5 vintage parity; page 11 TotalGreen ($0.01/kWh).
  The B-series uses its stated daily periods. Legacy A-series timing rules
  and other schedules are excluded.
- [PG&E B-1](https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_B-1.pdf):
  sheets 3–4 (March 1, 2026) and 6 (January 1, 2026).
- [PG&E E-FFS](https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_SCHEDS_E-FFS.pdf):
  Small L&P, sheets 2–4 (January 1, 2026). These still match the existing
  verified snapshot; this extension retains its September 16 cutoff.
- [CEC provider layer](https://services3.arcgis.com/bWPjFyq029ChCGur/arcgis/rest/services/ElectricLoadServingEntities_Other/FeatureServer/0):
  OBJECTIDs 19 (Peninsula), 29 (SVCE), 27 (SJCE), checked September 17.

## Accounting and implementation

The shared `pge_cca.py` helper removes PG&E generation and bundled PCIA from
the bundled energy price, then adds the explicitly selected vintage PCIA and
franchise fee. `bay_area_cca.py` adds the published provider generation and
product premium. It never derives generation rates from advertised discounts
or uses a comparison column that already includes PG&E fees.

SJCE vintage 2019 adds a separate -$0.00046/kWh adjustment; vintage 2020 adds
+$0.00046/kWh. Together with the original PG&E PCIA, these reconcile to the
published 2018 parity rule. Other SJCE vintages are not inferred. Franchise
fees for these three B-1 vintages are identical.

Bill energy is the sum of the additive components. Daily customer charges
are added once, by local service date, including partial months and DST.
Standard B-1 has no demand charge; peak demand is retained for account review.
Location-study dispatch uses the same total import rate as billing. Legacy
CSV studies retain their explicit CSV dispatch prices and existing warnings.
Product selection does not replace the study's carbon-intensity signal.

`services.py` supplies provider IDs and territory aliases to validation and
web capabilities. The web form filters the tariff catalog by the confirmed
service and displays its actual scope notes. The desktop catalog uses the
same tariffs. Cost tables and CSVs include base generation, product premium,
PG&E delivery, PCIA, franchise fee and applicable provider adjustment.
Saved engine snapshots retain the source definitions used for each study.

## Exclusions and next coverage

No primary-voltage B-1, B1-ST, CARE/SJ Cares, special exemption, standby,
residential, municipal, tax, or NEM/NBT/export settlement is modeled by these
options. Carbon-free/renewable marketing claims are not emissions factors.

East Bay and North Bay providers remain subsequent work, following the user's
Peninsula/South Bay priority. Additional commercial schedules need their own
verified generation, delivery and demand components. SVCE spring timing and
historical Peninsula versions need explicit implementation before extending
coverage into those periods.
