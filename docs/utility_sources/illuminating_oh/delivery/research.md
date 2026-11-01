# The Illuminating Company: delivery source review

Reviewed October 31, 2026. This is delivery evidence, not a complete-bill or
simulation acceptance report. Supply and Ohio tax evidence are maintained
separately. Root source downloads succeeded with certificate verification;
original PDF bytes and receipts remain in `.cache/illuminating_oh/sources/`.

## Bounded verified intersections

The retained delivery sheets establish complete calendar January 2025,
June 2025, September–December 2025, and October 2026, subject to the separately
verified supply/tax intersection and ordinary-account eligibility. They do not
establish continuous coverage between the first and last supported dates.
Full-year 2025 coverage is unavailable. Rates are in
[`rates_by_window.json`](rates_by_window.json); retained pages and original
PDF identities are in [`sources.json`](sources.json).

Important source corrections:

- The older live `CEI-2024-Electric-Service.pdf` contains January 2025 riders
  but retains stale PIR Sheet 125, 22nd revision, July 1, 2024, 0.0449 cents.
  The PUCO copy and full June 12, 2025 archived official copy contain the
  superseding **23rd revision effective January 1, 2025, 0.0427 cents**.
  January 2025 therefore uses $0.000427/kWh. The original January composite
  is not accepted wholesale as an internally current complete tariff.
- The PUCO source whose search result showed June 2025 DCR contains July
  quarterly riders and August 14 LGR/SGF removals. It is not a clean June
  snapshot. The complete 172-page June 12 archived official book independently
  provides April quarterlies, February DSE/RER, June DCR, January LGR/SGF,
  and the corrected January PIR needed for June 2025.
- The older live `CEI-2025-Electric-Service.pdf` contains October quarterly
  riders and September DCR. The separately archived year-end 2025 book adds
  the December 1 DCR revision. Effective dates on individual sheets govern.
- The current 2026 book contains October 1 quarterlies, September DCR,
  July DSE/CCR/PIR, April NMB and March base/TSA. These establish October
  2026 only; those October quarterly values are not extended backward.

## Billing components and arithmetic

All published cents were divided by 100 exactly in the JSON. Pairs are ordered
RS, GS. GS's first-five-kW capacity charge is a **monthly lump sum**, followed
by a price per kW above five, not a charge multiplied by all five kW.

- Through 2025 the ordinary RS base is $4 plus $0.029510/kWh. Ordinary GS is
  $7 plus $13.6800 for the first five billing kW and $7.4790 per excess kW.
- From March 1, 2026 the RS base is $6.50 plus $0.048397/kWh. GS is $10 plus
  $26.6451 for the first five billing kW and $12.5319 per excess kW.
- GS billing demand is the greatest of the highest thirty-minute integrated
  measured demand, 5.0 kW and actual Company contract demand. The tariff also
  describes non-demand-meter estimates, primary-meter adjustments, three-phase
  reactive billing, and special facilities; the proposed ordinary measured
  secondary single-phase scope excludes those alternatives.
- January 2025 DCR is 47.8156% RS / 44.2175% GS of **base distribution
  charges, excluding all riders**. June/September/December 2025 and September
  2026 DCR instead use RS energy / GS billing-demand rates. DCR is selected
  by bills rendered. This is distinct from service-rendered riders.
- The mandatory CRC is negative $0.51/month for RS and negative
  $0.000298/kWh for GS throughout verified 2025 windows. It is explicitly zero
  effective January 1, 2026. Do not omit this credit or apply it to 2026.
- Mandatory TSA is negative $0.001865 RS / $0.001416 GS per kWh in 2025;
  current March 2026 TSA is negative $0.001054 / $0.000779 per kWh.
- USF is $0.0021322/kWh for the first 833,000 kWh and $0.0005680 for excess
  usage in verified 2025 windows. Current PIPP Sheet 90, effective October 1,
  2026, uses $0.0032567 / $0.0005680. These are ordinary-account funding
  charges, even though PIPP/assistance enrollment itself is outside scope.
- Include signed DRR, DUN, PUR, the fixed AMI, DSE, standard EDR and the
  separate EDR automaker charge. Ordinary EDR cost recovery applies even
  when the account receives no legacy or automaker benefit.
- Include RS energy / GS demand NMB. The filed retail NMB tariff rate already
  contains its CAT factor; no wholesale price or extra transmission adder is
  substituted. Other tariff rates with CAT built into their formulas are not
  grossed up a second time. State kWh tax treatment is separately documented.
- RER applies to every ordinary RS account in the verified 2025 windows;
  do not exclude it merely because the account lacks a legacy heating credit.
  The current 2026 Sheet 122 is CCR and applies to RS and GS at the listed
  July 2026 rates. Do not bill both old RER and new CCR in October 2026.
- January 2025 VMC is positive RS $0.000223/kWh / GS $0.0566 per billing kW.
  VMC/EEC/SCR are removed from the February 2025 summary. EEC and SCR were
  explicitly zero in the January ESP V scope; no later charge is inferred.
- LGR is RS $1.50/month / GS $0.0018007/kWh in January–June 2025, first
  833,000 GS kWh only. SGF is RS $0.10/month / GS $0.00029051/kWh within
  that cap. LGR becomes zero on service rendered August 14, 2025; SGF
  becomes zero for bills rendered August 14, 2025. Their July/August
  transition is outside the supported complete-calendar scope.
- Current DCR Sheet 124 page 2 explicitly sets February–April 2026 special
  credits to zero from May 1. The earlier credit amounts remain unverified;
  zero is not applied retroactively to those months.

## Explicit zero / inapplicable ordinary riders

The retained current sheets, corroborated by historical books where needed,
establish zero TAS1 (TAS2 ceased September 22, 2010), RS DSM, Fuel, LEX,
DSI, DGC, DFC, RS RDD, GS NDD, GDR, ORR, and CSR rates 1/2. GDR and ORR
begin February 1, 2025 and are not applicable in January. The CDR printed
historical credit is **not applied**, as its sheet expressly ended application
August 6, 2011. RGC is zero and its special legacy eligibility is excluded.

RDC/legacy-heating, BDC, SDC, grandfathered contracts/RAR, ELR, PTR, CPP,
RCP, RTP, HLF, AMO, CFA, EV optional service, NMB opt-out, special facilities,
and export/NEM settlement require separate qualification and are outside
ordinary-account scope; their absence is not an invented zero tariff.

## Unresolved source windows

- February–May 2025: February ESP-IV complete component intersection is
  missing. A truncated May 13 archived PDF cannot establish missing rates.
- July–August 2025: LGR 12th revision effective July 1 is missing. August
  additionally crosses the August 14 LGR/SGF transition and needs verified
  fixed-charge allocation. Do not reuse January LGR or assume zero early.
- January–September 2026: earlier quarterly components, January TSA and
  special DCR refund amounts are not fully established. The May 2026 archive
  response is truncated; it is not a complete source or a coverage grant.

No interpolation, adjacent-period carryover, neighboring-utility rates or
provisional assumptions are authorized. The source gaps should remain visible
and unsupported complete cycles should reject.

## Visual review

Rendered and inspected current GS Sheet 20 first page, the January 2025 DCR
52nd-revision percentage table, superseding January 2025 PIR 23rd-revision
table, and October 2026 PIPP 26th-revision energy blocks. Source and rendered
images are retained privately. This selected visual review does not claim
every page of every tariff was visually reviewed.
