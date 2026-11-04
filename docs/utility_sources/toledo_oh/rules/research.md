# Toledo Edison rules review

Reviewed November 1, 2026. This review owns eligibility, billing rules and DER
scope; separate delivery and supply ledgers establish complete component date
coverage. The [source manifest](sources.json) records original tariff URLs,
PDF hashes/pages, selected text and two visual reviews. [Structured rules](rules.json)
retain the implementation scope and source distinctions.

## Ordinary plans and service

The Toledo Edison Company, Ohio, P.U.C.O. No. 8, names the ordinary schedules
RS Residential Service (Sheet 10) and GS General Service–Secondary (Sheet 20).
The original schedules are effective January 23, 2009 and remain in the 2025
book; first revised schedules apply March 1, 2026. These rule dates alone do
not establish complete billing coverage for every intervening rider window.

RS serves one meter per family unit in a residence/apartment. Mixed commercial
use on the same meter, institutional/commercial premises and apartment common
facilities use an appropriate general service schedule. GS covers general
installations requiring secondary service, one meter per installation. Its
sheet does not impose a universal small-load ceiling; any <=100 kW initial
study envelope is a conservative model choice.

Secondary service is at or below 600 V, assigned by the Company. The current
regulations explicitly list 120/240 V single phase alongside three-phase
options. An initial one-meter 120/240 V single-phase, unity billing-PF scope
avoids three-phase reactive charges and primary-metering adjustments. It does
not establish real account eligibility from coordinates or a reference circuit.

## Measured GS demand and contract

**Toledo GS uses the highest FIFTEEN-minute integrated import kW in both the
2025 original and March 2026 revised schedule.** It must not inherit CEI or
Ohio Edison's thirty-minute demand definition. Billing demand is the maximum
of that measured peak, 5 kW and the actual Company-assigned contract demand.
The price for the first 5 billing kW is a flat monthly amount, followed by a
per-kW excess price. There is no trailing historical demand ratchet or separate
ordinary GS minimum-bill clause in the reviewed sheet.

The 2025 GS base is $7/month, $10.9800 for the first 5 kW and $8.0390/kW above
5. From March 1, 2026 it is $10/month, $17.5166 for the first 5 kW and
$8.2769/kW above 5. Reactive charges apply only to three-phase customers:
$.360/rkVA before March and $.60 thereafter. Primary-meter adjustments change
from 2% to 1.5%; primary-side metering is excluded from the first scope.

For service established after January 22, 2009 or a significant service change,
contract demand is 60% of expected typical monthly peak. Existing contracts
are retained, Company-directed revision may be required for increased service,
and customer-requested reevaluation is no more frequent than once per twelve
months. Supply the documented obligation; do not infer zero or recalculate it
from current PV/battery-reduced imports.

Without a demand meter and above 1,000 kWh/month, estimated measured demand is
kWh/200. Exclude that alternative, unmetered service, optional GSU service,
special meter fees, premium/duplicate circuits and three-phase billing unless
separately implemented and verified. The selected 2025/2026 GS pages were both
rendered and visually reviewed; the fifteen-minute wording and flat capacity
units are unambiguous.

## Cycles, dates and supplier

Bills are monthly and typically cover approximately thirty days. Ordinary
summer service is June–August; winter is September–May unless an individual
component specifies otherwise. Nonseasonal changes begin with service rendered
on their effective date. No general fixed-charge allocation rule for irregular,
partial or split cycles was established. Complete calendar cycles are a narrower
model scope; a midmonth rider transition still needs sourced allocation before
including its entire calendar month.

Only ordinary GEN Standard Service Offer is in scope. Shopping/CRES, aggregation,
TOU/CPP/PTR/RTP, assistance and special arrangements are separate. Supplier changes
normally occur at the regular meter read; one certified supplier serves an
account per billing month, and SSO and certified supply cannot be split within
that month. Wholesale PJM prices never supply missing retail rates.

## PV and paired storage

Toledo's Sheet 93 applies the underlying ordinary tariff and Company-supplied
import peak to a qualifying customer-generator. Sheet 52's Partial Service
applicability expressly excludes generation qualifying for the Net Metering
Rider. Ohio Administrative Code 4901:1-10-28, effective April 8, 2024, requires
standard net-metering retail components/monthly charges to match the underlying
non-generator tariff. It applies to Toledo as an Ohio electric utility; the
unchanged shared state-rule source was retained with its original October 31
retrieval identity and a November 1 applicability review.

Qualification remains independent: onsite eligible renewable generation,
primarily offsetting customer requirements, with Company-approved sizing up to
120% of requirements based on the prior three-year average or a reasonable
Company estimate. The common FirstEnergy Ohio interconnection instructions
explicitly require generation/inverter/storage equipment in the site plan and
one-line drawing, a signed agreement and final permission to operate. This is
not automatic qualification of an arbitrary battery configuration. Confirm the
exact PV and paired-storage approval, metering and absence of Partial Service
or recurring special charges before study service begins.

The conservative implementation subset is zero export/credit bank, PV-only
battery charging and already-active approval. Standalone storage, standby,
Partial Service and export/NEM settlement remain outside scope. A combined
25 kW study-output cap is a model bound, not interconnection approval. Old Sheet
93 requested annual cash-refund wording differs from the current state's
continuous monetary-credit rule; rejecting exports avoids enabling either
unverified settlement interpretation.

## PJM identities and hypothetical site

The common FirstEnergy supplier source explicitly identifies Toledo Edison
(TE), CEI and Ohio Edison in the FE Ohio energy zone, while requiring separate
company transmission/NSPL accounts. PJM's FE-ATSI entry is a control-area
identity. Keep the utility, Ohio jurisdiction, SSO supply arrangement, ATSI/PJM
metadata, any chosen wholesale LMP node and US-MIDA-PJM regional-average carbon
separate. The shared metadata sources retain their original retrieval hashes;
they are reused after confirming explicit Toledo applicability.

Wood County is named in Toledo's current territory sheet. An explicitly
hypothetical unincorporated Wood County site at 41.50, -83.65 is a suitable
reference only with independent utility, local-charge, contract and renewable
approval assertions. County membership and coordinates do not prove them.
