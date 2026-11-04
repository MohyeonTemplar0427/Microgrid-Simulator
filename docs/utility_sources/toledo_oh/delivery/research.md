# Toledo Edison delivery review

Reviewed November 1, 2026 for ordinary RS residential and measured secondary GS
SSO. This review owns delivery components; independent supply and tax evidence
must intersect these dates before a complete bill executes. Source references,
original PDF hashes, selected excerpts and visual checks are in
[sources.json](sources.json); exact USD vectors and unit definitions are in
[rates_by_window.json](rates_by_window.json).

## Verified intersections and source identity

The source-reviewed delivery intersections are **January 2025, June 2025,
September–November 2025, and October 2026**. This is neither continuous coverage
between the endpoints nor full-year 2025 coverage.

The old live `TE-2024-Electric-Service.pdf` supplies January 2025 components.
Its August 2024 VMC first revision supersedes the June 2024 original still
retained in the PUCO January composite. The full June 12 and August 25, 2025
Wayback snapshots of the official tariff supply intermediate component pages.
The 2025 archive, old live 2025 URL, and February 2026 capture are **identical
October 2025 composite bytes**, retaining September DCR revision 54. Their
filename or capture date does not establish December 2025 or 2026 rates.
The current 2026 original supplies the complete October 2026 intersection.

The March 2026 base distribution reset is independently filed, but it does not
establish complete March–September 2026 composite bills. No intermediate rider
or refund is carried backward from the current book.

## Base schedules and demand units

| Filed base effective period | RS customer / energy | GS customer / first 5 kW / each excess kW |
| --- | --- | --- |
| Before March 1, 2026 | $4/month + $.035595/kWh | $7/month + $10.9800 total for first 5 kW + $8.0390/kW above 5 |
| From March 1, 2026 | $6.50/month + $.036046/kWh | $10/month + $17.5166 total for first 5 kW + $8.2769/kW above 5 |

Toledo GS measures the highest **fifteen-minute integrated kW**, in both the
old and March 2026 schedules. It is not CEI's thirty-minute measurement.
Billing demand is the maximum of that measured peak, 5 kW and the documented
Company contract. The first-five-kW amount is a single monthly amount, not a
price multiplied by five. There is no ordinary historical demand ratchet in
Sheet 20. Contract demand remains an independent account obligation.

Three-phase reactive demand is priced separately ($.360/rkVA before March,
$.60 thereafter); the initial single-phase scope excludes it. Primary-metering
adjustments, estimated/unmetered demand, special facilities and additional
meter fees require separate treatment and are outside ordinary scope.

## Dated delivery components

All amounts below are USD after exact conversion from filed cents/percent.
The JSON retains all other individual amounts and source selections.

| Window | NMB RS $/kWh / GS $/kW | DCR RS / GS | AMI RS / GS $/month |
| --- | --- | --- | --- |
| January 2025 | .024644 / 5.9053 | .199630 / .171107 of base distribution only | 1.904 / 10.173 |
| June 2025 | .025900 / 5.9776 | .007343/kWh / 2.8210/kW | 1.710 / 9.328 |
| September 2025 | .025900 / 5.9776 | .006914/kWh / 2.6511/kW | 1.216 / 6.687 |
| October–November 2025 | .025298 / 5.9680 | .006914/kWh / 2.6511/kW | 2.226 / 11.769 |
| October 2026 | .025117 / 4.8415 | .000820/kWh / .2575/kW | 1.764 / 7.926 |

January DCR is 19.9630% RS and 17.1107% GS of the underlying distribution
service charge plus base energy/capacity, excluding all riders. Later DCR is
energy-based for RS and billing-demand-based for GS, selected by bill-rendered
date. NMB is service-rendered, includes its specified CAT treatment and recovers
transmission/non-market costs; no extra wholesale transmission/PLC/NSPL adder
is justified. AMI is a fixed monthly amount.

Other independently dated ordinary components include DRR, DUN, PUR, DSE,
EDR's standard charge plus separate automaker charge, TSA, PIR, RER/CCR, VMC,
LGR, SGF, CRC and USF/PIPP. Important details:

- January VMC is positive **$.001331/kWh RS and $.2806/billing-kW GS** from
  the August 1, 2024 first revision. It is absent from the restored ESP-IV
  February rider summary, so the verified June/later windows do not bill it.
- January PIR is **$.000318/kWh**, already the correct January revision in
  the old live Toledo book. CEI's separate PIR correction is not transplanted.
  July 2025 PIR is $.000267/kWh; July 2026 PIR is $.000256/kWh.
- Ordinary positive RS RER applies without legacy heating-credit eligibility:
  $.001393/kWh in January/June and $.001731/kWh in the later 2025 windows.
  October 2026 uses CCR instead: $.002838/kWh RS and $.000201/kWh GS, with
  RER zero. The two must not be added together.
- Mandatory 2025 CRC is −$.51/month RS or −$.000298/kWh GS. Rate 1 is
  bill-rendered and zero; Rate 2 is service-rendered. Both are zero in the
  January 2026 revision retained in the current book.
- TSA is −$.001792/kWh RS / −$.001090/kWh GS for the verified 2025 windows,
  and −$.000831 / −$.000509 from the March 2026 reset.
- October 2026 DUN and PUR are **credits**, −$.000107 and −$.000060/kWh.
  Negative signs from parentheses are preserved.
- USF 2025 is $.0028394/kWh for the first 833,000 kWh; current October 2026
  PIPP is $.0044700/kWh for that first block. The second block is $.0005610.
  A bounded first-block model must reject unsupported high use.
- January/June LGR is $1.50/month RS or $.0018007/kWh GS; SGF is $.10/month
  RS or $.00029051/kWh GS. LGR follows service dates; SGF follows bill dates.
  Both become zero August 14, 2025. That does not establish a fixed-charge
  allocation for a whole August cycle.
- DCR's extra February–April 2026 credits are not reconstructed. Its current
  second page expressly sets them to zero from May 1; that verifies zero for
  October, not their earlier amounts. The RS credit unit is $/kWh.

TAS1 is explicitly zero. The printed historical negative TAS2 ceased September
10, 2010 and is not a current credit. Toledo's retained Fuel rate ceased
December 14, 2009 and is not a current charge. DSM, LEX, DSI, DGC, DFC, RDD,
NDD, GDR, ORR and CSR have explicit zero ordinary rates in their retained
revisions; EEC and SCR are zero for January ESP V and removed from the
February ESP-IV summary. DGC's zero original is effective June 1, 2009; it
must not inherit CEI's different source date. Eligibility-dependent RDC, BDC,
SDC, 4a incentives, RAR, ELR, optional supply, opt-out and other special
programs are excluded by independent ordinary-account confirmation, not
silently priced at a guessed amount.

## Remaining gaps and bounded research

February–May 2025 lacks the complete intermediate ESP-IV component chronology.
July lacks LGR revision 12. August includes the midmonth fixed LGR transition,
whose allocation remains unverified. The December 1, 2025 DCR revision is not
in any retained readable full book. A targeted primary-domain search exposed
a cached lead for revision 55, but opening it returned the old September sheet;
the lead is recorded in [unverified_december_lead.json](unverified_december_lead.json)
and **is not executable rate evidence**. No repeated unchanged route was used.

Earlier 2026 quarterly components, TSA/CRC intersections and February–April
refunds remain incomplete. The February capture is the old October 2025 book.
May 2025/2026 archive captures were intrinsically truncated and are excluded;
root retains the blocker receipt. These gaps prevent an annual billing claim.

The March 2026 GS page and January 2025 DCR page were rendered with Poppler
and visually reviewed. All six original PDF hashes and selected-excerpt hashes
were verified. Original PDFs were preserved and no production code was edited
by this review.
