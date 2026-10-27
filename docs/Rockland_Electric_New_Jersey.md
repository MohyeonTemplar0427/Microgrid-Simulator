# Rockland Electric New Jersey SC1/SC2 BGS-RSCP

Reviewed October 27, 2026. The shared backend/local browser support ordinary
**SC1 non-TOD residential** and **SC2 secondary metered non-demand-billed**
BGS-RSCP accounts in **Bergen County/Eastern Division/PJM**, for complete
calendar cycles in **October 2026 only**. Earlier 2025–2026 component fragments
remain research evidence; no missing transmission or other prices are backfilled.
Central/Western divisions and other control areas are not enabled.

Read the [official-source ledger](utility_sources/rockland_nj/README.md),
[source pins](utility_sources/rockland_nj/sources.json) and
[implementation validation](Rockland_Electric_Implementation_Validation.md).
Original PDF/HTML bytes and larger receipts remain under ignored
`.cache/rockland_electric_nj/`; runtime prices are snapshot-safe Python literals.

## Verified ordinary account scope

One established, continuously served, ordinary taxable 120/240 V single-phase
secondary meter/service is modeled with unity billing power factor. Billing
eligibility and representative OpenDSS power factor are separate facts.
Utility, supplier, county/division, tax jurisdiction and PJM RECO metadata do
not establish each other. No wholesale pricing node, LMP or extra PLC/NSPL charge
is inferred from coordinates or the transmission-zone label.

SC2 requires independent utility assignment to **non-demand billing**, retained
through all proposed operation. An AMI meter may record interval power without
making the account demand billed. No numeric classification threshold, prior
eleven-month ceiling or November PLS rule was verified or borrowed from JCP&L.
The official PTC independently distinguishes the non-demand all-kWh row from
the adjacent demand-billed kW row; the $2.79/kW transmission term is inactive
for the independently assigned non-demand branch. General metered demand,
connected-load, kVA/ratchet, CIEP and standby calculations are not implemented.
No CIEP eligibility/assignment/election is permitted in the initial account scope.

Ordinary monthly billing periods are **26–34 days inclusive** under General
Information 7. Complete matching calendar cycles retain whole monthly charges
and the SC1 600-kWh block. Partial, shifted, initial/final or mixed billing-month
cycles reject; days/30 proration is not implemented. BGS reconciliation applies
to **all usage billed in the indicated month**, not a generic service-time split.
Calendar service/bill months must match. The July 16, 2026 nonlinear distribution
credit crossing is outside enabled coverage, with no invented allocation.

## October 2026 components

All values below retain applicable filed CBT/SUT. Generation already includes
capacity, ancillary services and administration. No extra tax/admin multiplier
is added. The transmission surcharge bundles RMR, EL05-121 and TEC once.

| Component | SC1 non-TOD | SC2 metered non-demand |
| --- | ---: | ---: |
| Customer/monthly minimum | $6.00 | $16.00 |
| Winter distribution, $/kWh | 0.06886 | 0.03601 |
| Distribution adjustment, $/kWh | −0.01416 | Not applicable |
| BGS generation, $/kWh | 0.14435 | 0.11305 |
| Base transmission, $/kWh | 0.01809 | 0.00579 |
| Bundled transmission surcharge, $/kWh | 0.02187 | 0.01247 |
| BGS reconciliation, $/kWh | −0.02000 | −0.02000 |
| SBC, $/kWh | 0.007696 | 0.007696 |
| RGGI, $/kWh | 0.006867 | 0.006867 |
| CIP, $/kWh | 0.006170 | −0.001480 |
| ZEC, $/kWh | −0.004265 | −0.004265 |

SBC and RGGI constituent lines sum once to their published totals. IIP is
combined in base prices, TTAC ended June 2021 and residential EGCC ended
February 2026. Historical credits are not extended into October. No individual
regulatory credit bank is invented.

At 1,000 raw imported kWh, independent source arithmetic gives unrounded
ordinary charges of $241.478 for SC1 and $172.138 for SC2. The official annual
PTC is an older transmission vintage: its winter supply excluding reconciliation
is $0.18425/$0.13129 per kWh, while adopted October components sum to
$0.18431/$0.13131. This dated difference is retained; the PTC is not relabeled
as an October invoice. No independent actual customer whole-invoice fixture
was recovered. Raw kWh and existing component half-up monetary cents are study
conventions, without an exact printed-invoice or minimum rounded-cash claim.

Post-adjustment raw and component-cent totals must meet the ordinary monthly
minimum. Cases where floor ordering could affect the result reject without
forcing purchases or inventing a minimum formula. Initial/termination, contract
settlement, special facilities, manual-reading/AMI opt-out and changeout fees
are excluded by explicit ordinary account facts. No fictitious zero fee is used
for an opt-out customer.

## PV/storage and acceptance limits

PV-only and PV-plus-battery studies require an already-active executed ordinary
Class I NEM/parallel agreement, required installed metering, approved sizing and
permitted storage/grid charging. The effective active date must precede the
cycle; an application is insufficient. Rockland's source does not establish
JCP&L's 20-day initiation rule. SC2 must retain non-demand billing for the
proposed operation; the tariff's standby rider names demand-billed SC2/SC7.
No generic size exemption is inferred. The 25-kW combined study-output bound
is an implementation bound, not utility approval. Exports and opening banks
are zero; standalone storage, export credits/banking/cashout and special service
reject. Grid-only removes DER assertions while preserving account classification.

October 2026 is not complete at the review date. Acceptance therefore uses
**explicit modeled clear-sky inputs**, native synthetic load and all-interval
representative replay. It is not a historical-weather or annual acceptance pass.
Missing historical prices and unavailable future weather are never filled with
substitutes. Full-year 2025, August/September transmission and full-year 2026
remain unverified. Existing shared billing, PV/storage, worker, browser and
OpenDSS components are reused. Targeted validation excludes GUI/full release
unless a shared behavioral change or unresolved regression requires them.
