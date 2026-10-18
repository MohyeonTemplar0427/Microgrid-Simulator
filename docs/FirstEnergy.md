# FirstEnergy Pennsylvania and Ohio retail studies

This is local candidate development, with separate distribution utility,
jurisdiction, retail supplier, PJM zone and optional wholesale pricing identity.
Neither coordinates nor a pricing node establishes service eligibility. Other
FirstEnergy rate districts are not interchangeable with the two selected here.
The local browser uses the existing schema-11 regional workflow. Native desktop
GUI work remains paused. No stable-engine promotion or public deployment occurs.

| Territory | Class and plan | Complete executable coverage |
|---|---|---|
| FirstEnergy Pennsylvania, West Penn district, PA; APS zone | Residential RS; measured GS-Medium, default supply under100kW | January1–December31,2025 |
| Ohio Edison, OH; ATSI zone | Residential RS; measured General Service Secondary GS, SSO | January2025; June2025; August14–December31,2025; complete regular25–35-day cycles only |

**Verified Ohio full-year2025 coverage is not complete.** January ESP-V, June
ESP-IV and August14–December31 component intersections are executable by
default. February–May still lacks the approved compliance composite including
GEN18 and intermediate continuity; July1–August13 lacks LGR12 and verified RS
fixed-charge allocation across its removal. The confirmed return to ESP IV does
not establish those rates by itself. Strict verified mode rejects these gaps.

An explicitly accepted **provisional2025** mode now permits annual research
estimates using documented carry-forward, reconstruction and allocation
assumptions. It preserves known dated rates and does not extend verified
coverage. See [all provisional values, rules and output contracts](Ohio_Edison_Provisional_2025.md).
Other partial-service and fixed AMI/demand NMB allocation guards remain in force.

Research also inspected the public FirstEnergy calculator (explicitly limited
to current bills) and PUCO's itemized-bill Tableau service (visibly unavailable
for maintenance). Neither establishes the missing historical values. The
previous CAPTCHA-protected filing-viewer route was not bypassed. Detailed
source selections and unresolved components are retained in the manifest.

## Verified rates and billing rules

Amounts below are dollars unless stated otherwise. Source documents, downloaded
SHA256s and page selections are in [the manifest](utility_sources/firstenergy/manifest.json).
Research PDFs remain in ignored local storage; no large PDF corpus was added.
Tariff documents control over abbreviated historical spreadsheets. The PA
historical workbook labels a June column June24; Supp19 actually takes effect
June1,2025. The implementation uses the filed date.

West Penn ordinary RS has a $9 monthly customer charge and $.04306/kWh base
distribution energy. Measured GS-M has $23.29/month, $.00531/kWh distribution,
$3.46/kW billing demand and $.22/kVAr reactive billing demand. The initial case
is240V single phase with confirmed unity billing PF and zero reactive billing
demand. It excludes TOU demand meters, unmetered demand, primary service,
special residential demand provisions and larger hourly-priced default service.
RS interval demand is bounded at25kW within the ordinary-account assumption.

GS-M billing demand is the greatest of measured meter demand, contract demand,
and50% of the greatest **billing** demand in the preceding eleven cycles. The
meter's confirmed averaging period is15,30 or60minutes, built only from equally
fine or finer complete aligned intervals. History evolves separately for every
scenario. Utility annual PTC classification is an explicit confirmed account
fact, not an inferred PJM PLC. The bounded case remains under100kW; twelve
consecutive cycles below1500kWh require reclassification rather than silently
retaining GS-M. Contract demand and initial history are held equal across cases.

| West Penn component | Jan–May2025 | Jun–Nov2025 | Dec2025 |
|---|---:|---:|---:|
| RS supply PTC, $/kWh | .09481 | .10317 | .10947 |
| GS-M supply PTC, $/kWh | .10013 | .10536 | .10993 |
| RS DSS, $/kWh | .00539 | .00770 | .00770 |
| GS-M DSS, $/kWh | .00288 | .00407 | .00407 |
| RS EEC, $/kWh | .00161 | .00186 | .00186 |
| Commercial EEC, $/kWh | .00330 | .00200 | .00200 |

Other independently dated components:

- USC residential: $.00589/kWh through July31; $.00920 from August1.
- SMT: residential credit $.00004/kWh; commercial $.85/month.
- TCJA: zero before July1; then-.53% of base distribution, on a bills-rendered
  basis, excluding STAS and automatic-rider revenues.
- DSIC: zero Jan–Mar; .02% Apr–Jun; zero Jul–Dec. Original page241 specifies
  bills-rendered treatment on distribution service including applicable riders,
  excluding STAS. PTC supply is separate; nonbypassable DSS is delivery service.
- STAS: .01% after applicable tariff riders. Filed supply includes GRT; no
  separate5.9% gross-receipts adder is applied.
- January bills-rendered one-time refunds: RS$4.45 and legacy GP30/GS-M$15.48,
  already GRT-inclusive. Recorded once in evolving state, outside STAS basis.
- Ordinary residential use is sales-tax exempt. Commercial first scope requires
  the PA state-only6% jurisdiction and no exemption; Allegheny, Philadelphia,
  manufacturing/agricultural/resale exemptions and mixed use are rejected.

Ohio Edison RS uses $4/month plus $.031898/kWh base distribution. GS uses
$7/month, $12.80 covering the first5kW and $5.4635/kW above5. Billing demand is
the maximum of the actual **30-minute integrated** meter peak,5kW and actual
contract demand. There is no invented monthly history ratchet. The first case
uses240V single phase, secondary metering, no three-phase reactive charge,
no AMI opt-out, no special/legacy heating-credit enrollment and no municipal
utility/franchise charge. RDC and BDC are legacy eligibility provisions; they
are **not automatic winter discounts**.

Sheet4 defines winter as September1–May31. January uses GEN energy
$.073408/kWh and capacity $.003080/kWh RS / $.002908/kWh GS. June uses summer
energy $.073661/kWh and capacity $.021953/kWh RS / $.021732/kWh GS. The same
summer rates apply to the verified August14–31 service dates. The
September–December winter energy rate is $.066966/kWh with the same capacity.
Capacity is already converted to retail energy units. Transmission/non-market
costs are in NMB: January RS $.021982/kWh / GS$6.2252/kW; June and
August14–September30 RS $.023602/kWh / GS$6.3482/kW; October–December RS
$.024468/kWh / GS$7.1203/kW. DCR is bills-rendered:
RS $.008770/kWh / GS$3.2527/kW September–November; RS $.009048/kWh /
GS$3.1087/kW from December1.

All nonzero ordinary AER, DRR, DUN, GCR, AMI, PUR, NDU, EDR including automaker
recovery, TSA, DSE, PIR, RER, CRC and USF components are included with their
filed changes. January includes the ESP-V VMC (RS $.000047/kWh, GS $.0087/kW),
with DSE zero. June has DSE $.001151/kWh and no VMC. January DCR is35.1979%
(RS) /28.5339% (GS) of base distribution, including its customer charge but
excluding riders. June–August bills use DCR $.009032/kWh RS /$3.3606/kW GS
within the verified service-date windows. January and
June LGR is$1.50/month RS / $.0018007/kWh GS; SGF is $.10/month RS /
$.00029051/kWh GS. SGF follows bill date; LGR follows service date. LGR and
SGF are zero from August14. August14–September30 uses AMI $1.514 RS /$5.450 GS,
DSE $.000462/kWh, PIR $.000476/kWh, RER $.003545/kWh RS and the filed July
quarter volumetric riders. A cycle spanning September1 splits GEN energy by
service date and applies the bill-date DCR rate to the entire applicable cycle.
Fuel rider text
explicitly says it no longer applies after December8,2009; its retained old
negative number is not a2025 credit. Zero-rate riders remain documented in the
source selections. State-kWh tax uses $.00465 for the first2000kWh, $.00419
for the next13000 and $.00363 above15000, grossed up by1/(1-.0026) for CAT.
No generic sales-tax percentage is substituted. The bounded RS/GS case remains
below833000kWh/cycle, avoiding unimplemented high-use USF blocks.

Both adapters require complete, documented regular25–35-day cycles. Monthly
fixed charges are not prorated on invented daily factors. West Penn volumetric
rates follow service dates across changes; DSIC and TCJA follow bill date.
Ohio cycles spanning an AMI fixed-charge or NMB demand-rate change reject until
the filed allocation is established. Partial initial/final cycles are unsupported.

## PV, storage and optimization

The first PV cases are **utility-confirmed qualifying renewable accounts with
ordinary-service billing, operated with a zero-export study constraint**. A
checkbox is the user's assertion or a clearly labeled hypothetical assumption;
the simulator does not determine legal eligibility. Both tariffs have Partial
Service/standby provisions; ordinary billing must not be assumed for an
ineligible generator. No standby bill, NEM credit, export compensation, grant,
tax incentive or annual settlement is implemented here. Storage-only is disabled.
PV-plus-battery requires PV-only charging and no battery exports.

Grid-only removes the renewable installation as an explicit counterfactual,
retaining tariff, supplier, initial demand history and contract obligations.
PV-only and PV-plus-battery use identical native loads, weather and PV equipment.
Every charge expression feeds the shared optimizer and is independently rebilled
numerically. Battery wear remains optional and excluded from default utility-bill
minimization. Linked cycles retain SOC and demand/refund state but optimize each
cycle with historical perfect foresight; this is not an annual optimum or a
real-time controller.

All scenarios reuse OpenDSS QSTS at every15-minute interval, preserving actual
PV curtailment, signed meter flow and interval-start SOC. Reference circuits
are25kVA120/240V split phase residential and75kVA240V single phase commercial.
Wiring, service size, impedance and inverter behavior are representative
assumptions. The shared replay uses a.95lagging load PF as electrical stress;
it is not an observation of the account's unity-PF billing assumption. Replay
losses/PCC values do not replace the scheduled meter flows used for billing.
Electrical infeasibility remains visible without changing the tariff bill.

## Reproduction and verification

Use `/usr/local/bin/python3 tools/validate.py --tier focused --area regional
--area validation --output .cache/firstenergy_focused` and the release tier after
focused checks pass. `test/test_firstenergy.py` includes independent Decimal
tariff benchmarks, bill-date/service-date boundaries, the one-time refund,
eleven-cycle ratchet,30-minute integration, DST, tax blocks, rejection of missing
rates/unsupported arrangements, and actual main-form serialization→API→pinned
worker→billing/OpenDSS→save/restore/download tests without live requests.

The historical driver accepts explicit `--utility firstenergy_pa_west_penn`
and `--utility firstenergy_ohio_edison`. `--prepare-inputs` explicitly retrieves
site-matched2025 ERA5, preserving raw JSON, units, coordinates, retrieval time
and hashes; it does not fall back from NSRDB. ERA5 hourly reanalysis is held
across15-minute study intervals; it is not measured subhourly irradiance.
Imported load CSVs are deterministic generic household/office scenarios, not
measured customer loads, regional forecasts or weather-calibrated occupancy.
Open-Meteo/Copernicus attribution and free-API noncommercial-use limits apply.

West Penn `--period annual` validates2025. Ohio `--period monthly` selects
October2025. Custom complete January and June cycles validate the new versions; `--period custom --start-date 2025-09-01 --end-date 2025-12-31`
tests the full enabled four-month window. `--period annual` rejects explicitly.
Use fresh output folders for changed source or validators. Candidate IDs,
per-case runtime, audit results and artifact fingerprints are recorded locally;
older runs must retain their original engine attribution.

Remaining work: recover and reconcile Ohio's February–May and July1–August13 sources,
then run the full Ohio year; verify standby/export programs separately; extend
partial-cycle and fixed/demand-change allocation; other PA districts and Ohio
operating companies; three-phase/reactive/primary service; other tax localities;
longer verified history; measured bill calibration. Wholesale PJM prices and
unassigned capacity/transmission obligations are never added to these defaults.

## Ohio source recovery still required

The first recovery pass enables January and June, not a complete annual bill.
Before enabling February–May, obtain the complete approved February1,2025
compliance tariff (GEN Sheet114 revision18 and all applicable rider sheets) and
verify subsequent revisions through May31. Current-rate columns in the January31
McMillen/Patel testimony confirm February DCR, AMI, DSE and EDR values; their
proposed ESP-VI columns are not adopted tariffs. They do not alone verify every
component's later continuity. A numerical agreement with an annualized typical
bill cannot establish missing individual filed rates.

Before enabling July1–August13, obtain Ohio Edison LGR Sheet135 revision12,
including its effective date and RS/GS rates, and the August6,2025 compliance
order or other filed allocation rule for the August14 residential fixed LGR
change. Sheet135 revision13 sets LGR to zero on a service-rendered basis, while
Sheet136 sets SGF to zero on a bills-rendered basis. Neither the January LGR
value nor another utility's July rate is a substitute for the missing sheet.

A second recovery pass inspected the official Supreme Court docket2025-0490,
the appellants' appendix, FirstEnergy's merit brief and the industry appellees'
volume4. These confirm the litigation/plan context and reproduce earlier orders
and H.B.15, but do not supply the missing GEN18 or LGR12 rates. The official
`OE-2023-Electric-Service.pdf` was also inspected: it contains GEN16 effective
June2023 and LGR8 effective January2024, not the missing2025 revisions. Research
document URLs, hashes and outcomes are retained separately from executable rate
sources in the manifest. The unavailable PUCO viewer was not bypassed.

The source manifest records accessible PDFs, selected text, hashes and research
access failures. No archived PDF or personal bill was added to Git.
