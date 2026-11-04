# Toledo Edison, Ohio

This local-development adapter covers The Toledo Edison Company, Ohio,
P.U.C.O. No. 8, ordinary **RS Residential Service** and measured **GS General
Service–Secondary**, with **Standard Service Offer (SSO)** default supply.
Complete matching calendar service/bill cycles execute in **January and June
2025, September–November 2025, and October 2026**. The shared regional browser,
queued worker, PV/storage, billing/dispatch and OpenDSS components are reused.
Native desktop GUI work remains paused; no stable engine is promoted.

Sources and exact component vectors are retained in the [aggregate ledger](utility_sources/toledo_oh/sources.json),
[delivery review](utility_sources/toledo_oh/delivery/research.md),
[supply/tax review](utility_sources/toledo_oh/supply/research.md) and
[eligibility review](utility_sources/toledo_oh/rules/research.md).
Candidate-specific acceptance is in the
[implementation report](Toledo_Edison_Ohio_Implementation_Validation.md).

## Account scope

The account independently confirms Toledo Edison service, Ohio jurisdiction,
ordinary SSO throughout the cycle, one 120/240 V single-phase secondary meter,
unity billing PF and no municipal/franchise charge, self-assessment, special
tax arrangement, extra facilities or recurring optional meter charge. The
default unincorporated Wood County coordinates are explicitly hypothetical;
neither coordinates nor a PJM node establishes territory, supplier, tax status
or approval.

RS serves exclusively residential use, one family unit per meter. Mixed
business use, shared apartment facilities, legacy heating/distribution credits,
assistance, shopping/aggregation, optional TOU/CPP/PTR/RTP, AMI opt-out,
primary-side metering, three-phase/reactive service and special contracts are
outside this scope. Mandatory ordinary riders and credits still apply.

GS demand is the highest **15-minute integrated import kW**, verified in both
the 2025 and March 2026 schedule versions. Billing demand is the maximum of
that peak, **5 kW**, and the actual documented Company contract demand. The
first-five-kW capacity amount is a **flat monthly charge**, then a per-kW price
applies above 5 kW. There is no trailing eleven-month ratchet. Contract demand
is an independent obligation, never inferred from DER-reduced imports. The
sample retains an explicit hypothetical 12 kW contract across scenarios.
Estimated/unmetered demand, special meters and optional GSU service are excluded.

The model bounds native and imported interval peaks at 25 kW for RS and 100 kW
for GS, and usage at 833,000 kWh/cycle to keep high-use USF blocks inactive.
These conservative study bounds do not restate the whole tariff's eligibility.

## Verified dated rates

Amounts below are USD. Before March 1, 2026, RS base delivery is $4/month plus
$.035595/kWh; GS is $7/month plus $10.9800 for the first 5 billing kW, then
$8.0390/kW above 5. The revised filed bases are RS $6.50 plus $.036046/kWh and
GS $10 plus $17.5166 for the first 5 kW and $8.2769/kW above 5. The March base
change alone does not establish complete March–September 2026 billing coverage.
GS reactive charges apply only to excluded three-phase service; primary-side
loss reductions change from 2% to 1.5% and are excluded with primary metering.

| Supported service/bill months | GEN energy, $/kWh | RS / GS capacity, $/kWh | Component regime |
| --- | ---: | ---: | --- |
| January 2025 | .073408 | .003647 / .003038 | ESP V; base-only DCR percentage and positive VMC |
| June 2025 | .073661 | .024846 / .021990 | ESP IV summer GEN19, April quarterlies and DCR53 |
| September 2025 | .066966 | .024846 / .021990 | Winter GEN19, July quarterlies and DCR54 |
| October–November 2025 | .066966 | .024846 / .021990 | October quarterlies; September DCR54 |
| October 2026 | .072774 | .029096 / .021536 | GEN20, October quarterlies, September DCR58, revised distribution |

All ordinary nonzero GEN, AER, DRR, DUN, GCR, AMI, PUR, NDU, EDR plus separate
automaker recovery, NMB, DCR, TSA, DSE, PIR, RER/CCR, CRC, LGR, SGF, VMC and USF
components have independent dated evidence. January DCR is a percentage of
base customer plus base energy/capacity only; later RS DCR is per kWh and GS
DCR per billing kW. Sources preserve amounts, units, revisions and applicability.

Toledo-specific safeguards include January VMC from the August 2024 first
revision ($.001331/kWh RS and $.2806/billing-kW GS), rather than a stale original
page retained in another composite; January PIR $.000318/kWh; mandatory 2025
CRC of −$0.51/month RS or −$.000298/kWh GS; and negative October 2026 DUN/PUR.
Ordinary positive 2025 RS RER applies even without legacy heating-credit
eligibility. October 2026 uses CCR with RER zero. Explicitly ceased Fuel/TAS2
and other zero/inapplicable ordinary riders remain documented; historical
printed charges are not automatically current charges.

GEN already expresses energy/capacity in retail $/kWh, and NMB separately
recovers non-market/transmission costs. No duplicate LMP, PLC/NSPL, losses,
capacity/transmission or whole-bill CAT adder is applied. Ohio Edison and CEI
share neither Toledo's rate values nor its demand averaging rule by inference.

## Taxes, calendars and quantities

Toledo Sheet 92 incorporates ORC5727.81. State-kWh tax marginal rates are
$.00465, $.00419 and $.00363/kWh, with the specified CAT gross-up `1 / .9974`.
Exactly 30 measurement days use cumulative thresholds 2,000 and 15,000 kWh.
Other periods use statutory daily-average bands: **67 × local calendar days**
and **500 × local calendar days**. A 31-day cycle therefore uses 2,077/15,500;
November 2025 has 30 days and 721 elapsed hours but keeps 2,000/15,000.
Wired electricity is sales-tax exempt under ORC5739.02(B)(7). Local charges,
self-assessor exemptions and special arrangements require a different scope.

Complete consecutive 15-minute Eastern-time data reject missing, duplicate,
unordered, UTC-substituted or hourly inputs. Full calendar measurement month,
designated billing month and final-day bill date must agree. Monthly charges
are whole. Partial/shifted cycles and midmonth fixed-charge allocation reject
without sourced rules. Raw interval energy and measured demand feed the same
symbolic and numerical charge expressions, followed by the shared study's
component half-up cent rounding. Exact printed-invoice rounding and rounded-cash
optimality are not claimed; known floating-point half-cent boundaries are
explicitly checked in the independent benchmarks.

## Approved renewable service and separate grid metadata

The exact PV and paired-storage system must already have Company approval,
required metering and final permission to operate before service. Ohio's
current net-metering rule requires ordinary underlying retail charges, while
qualifying onsite use, approved sizing up to 120% of requirements and the exact
storage configuration remain independent eligibility facts. Toledo's Partial
Service sheet excludes net-metering-qualifying facilities; this is not automatic
approval of arbitrary PV or storage.

The implemented subset requires PV-only battery charging, zero exports and no
credit bank, with combined study output bounded at 25 kW. Standalone storage,
Partial Service/standby and export/NEM settlement are unavailable. The old
tariff's requested cash refund language differs from the current state's
continuous-credit rule; that unresolved settlement is not enabled. Grid-only
removes DER assertions/activation while retaining the actual contract, tariff,
SSO and other account obligations.

PJM, ATSI transmission context and **FE-ATSI control area** are metadata.
Utility, Ohio jurisdiction, SSO arrangement, selected wholesale pricing location
and optional **US-MIDA-PJM regional-average carbon** remain separate. Existing
carbon accounting can consume matching verified inputs independently; it is
not Toledo-specific intensity and does not set retail charges or dispatch.

## Unsupported periods

February–May 2025 lacks complete ESP-IV/intermediate component chronology.
July's LGR revision and August 14 fixed-charge allocation remain unverified.
December 2025 lacks a reproducible DCR55 primary sheet: the retained archived,
old-live and February 2026 books all retain September DCR54. A cached-search
lead is recorded as unverified and is not an executable rate. January–September
2026 lacks complete earlier rider/credit intersections. Two May archive
captures were truncated and yielded zero recoverable pages. There is no
provisional mode, missing-rate substitution or full-year 2025 coverage claim.
