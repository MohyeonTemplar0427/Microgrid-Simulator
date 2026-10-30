# Duquesne Light Pennsylvania RS and GS default service

Local schema 11 candidate for ordinary **RS residential** and Company-retained,
non-demand-metered **GS small commercial** service. Verified dated components
cover complete calendar cycles January 2025–October 2026. The delivery utility,
retail supply, Pennsylvania tax jurisdiction, PJM grid operator, transmission
zone and wholesale prices are separate identities. Coordinates never establish
service or eligibility. The hypothetical default is Center Township, Beaver
County, at 40.65, -80.31; the tariff lists that township among communities served,
but actual service and tax treatment require separate confirmation.

## Rates and evidence

Source ledger: [sources.json](utility_sources/duquesne_pa/sources.json),
[delivery](utility_sources/duquesne_pa/delivery/rates_by_window.json),
[supply](utility_sources/duquesne_pa/supply/rates_by_window.json),
[eligibility/tax/minimum rules](utility_sources/duquesne_pa/rules/research.md).
Original PUC filings are retained privately under `.cache/duquesne_pa/sources/`.
Direct utility binary downloads returned bot-protection HTML, never accepted as
tariff PDFs. Primary readable tariff text, original PUC filings, extracted
pages/hashes and inspected table images are separately identified in the ledger.

RS distribution is $13/month plus $0.082479/kWh. GS is $18/month plus
$0.084601/kWh. Residential USC, dated positive/negative EEC, zero SMC/RMES,
DSIC and STAS remain separate, applied once. Fixed Rider8 DSS and AppendixA
transmission are separately billed using exact filed precision; website rounded
class-average PTC is not substituted. Supply/capacity/loss/admin/PJM/GRT already
embedded in these filed prices are not charged again. TSC is excluded from STAS
and rate-schedule minimums. GS has no modeled demand charge or wholesale adder.

DSIC and STAS follow bills-rendered dates. This initial scope requires a full
calendar service month, explicit matching billing month and bill date on its
last service day. It rejects partial, shifted, crossed-version or unsupported
cycles instead of inventing allocation. UTC instants preserve DST; billing and
qualification use complete 15-minute averages. Billing optimizes unrounded
component arithmetic and separately reports currency-rounded results; this is
not proof of an exact printed/customer-invoice cash minimum.

## Independent eligibility and GS minimum limits

RS is restricted to solely residential ordinary use. Same-meter business, CAP,
heating/special schedules, three-phase/primary service, additional facilities,
optional pilots and special contracts are excluded. Ordinary residential
electricity is sales-tax exempt. GS is ordinary taxable business at the state
6% rate, outside Allegheny/Philadelphia and without a special exemption or local
surcharge. No Allegheny rate is silently assigned to the Beaver County example.

GS requires Company-confirmed established non-demand assignment and default
supply, including applicable annual/October-January reviews. Its distribution
assignment uses preceding usage/demand history; reduced imports after PV cannot
establish eligibility. A conservative initial domain separately bounds every
preceding/current native and imported month at 1,000 kWh and every known/current
15-minute peak at 5 kW. These restrictions keep the class thresholds inactive;
they are narrower than annual average qualification and do not replace Company
review. The first history boundary must precede the study; subsequent cycles
carry adjacent-month bounds independently for each scenario.

The GS/GM minimum-charge paragraph is not explicit enough to claim a universal
low-usage GS minimum. The model requires continuous non-demand GS and separately
confirmed absence of prior GM, priced demand, carried eleven-month demand
minimum or contract obligations. Accepted cases must also have base distribution,
distribution with riders before DSIC, and distribution after DSIC/STAS at least
twice the customer charge, including cent-level checks. Positive DSIC cannot
mask a negative EEC rider reducing the pre-DSIC amount. This is an
**inactive-domain guard for the paragraph's two possible scopes**, not a filed
double-customer minimum or new bill charge.
Cases outside it reject on numeric rebilling; the optimizer never forces
purchases to enter the domain. Low-import minimums remain unverified. No
unsourced demand price, zero assumption or universal floor is enabled.

## PV/storage, browser and electrical scope

PV and PV-plus-battery studies require already-active qualifying ordinary
Rider21 renewable approval and required metering. Storage charges only from PV;
exports, credit banks, standalone storage and unverified settlement reject.
The absent-DER grid reference removes enrollment assertions while retaining the
same class/supply/history facts. All scheduled exports are curtailed.

The existing main form, immutable queued worker, PV/weather/ESS, saved settings,
CSV/ZIP results and representative OpenDSS replay are reused. RS defaults use
5 kW DC/4 kW AC PV and 10 kWh/3 kW storage. GS uses a deliberately smaller
1.5 kW DC/1.2 kW AC array and 2 kWh/0.6 kW storage; arbitrary larger arrays can
leave the supported GS minimum domain and reject. These are explicit study
assumptions, not equipment or interconnection recommendations.

PJM's map labels the transmission zone **DLCO**; emergency-procedure control-area
metadata uses **DUQ**. Neither is an automatically selected wholesale price.
Optional [PJM carbon accounting](PJM_Regional_Carbon.md) uses the independent
regional consumption zone US-MIDA-PJM, with its own coverage and provenance.

The circuit is an assumed 120/240V split-phase secondary reference; billing uses
scheduled ideal meter flows, while measured PCC flows and losses remain separate
diagnostics. Historical annual studies roll complete cycles with carried SOC
and history, not a jointly optimized annual minimum or actual customer savings.
See [implementation validation](Duquesne_Light_Pennsylvania_Implementation_Validation.md)
for frozen identities, selected checks and remaining limitations. No GUI work,
stable-engine promotion or public deployment is implied.
