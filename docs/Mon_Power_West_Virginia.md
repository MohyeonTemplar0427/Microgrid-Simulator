# Mon Power West Virginia A and B

The regional adapter supports Monongahela Power Tariff 22 ordinary
residential A and non-demand-metered small general service B.
The utility and supplier are Mon Power, the jurisdiction is West Virginia
and PJM zone metadata is APS. Base prices bundle supply and delivery.
Potomac Edison West Virginia has a separate tariff and is outside this adapter.

Verified complete calendar cycles cover August–December 2025 and
August–November 2026. January–July 2025 and January–July 2026 lack
reconciled component intersections. July's service-date changes and
later December 2026 rates are blocked. Ordinary full monthly charges,
matching service/bill months and complete Eastern 15-minute data
are required.

Schedule B needs independent Company confirmation of non-demand
metering, retained classification and normal maximum electrical
requirements below 10 kW. It is available through one meter point.
The study separately caps B native load/imports at 9.9 kW and 6,000 kWh
per month. A has a 25 kW study cap.

The B minimum equals the greater of the normal customer-plus-energy
bill and $2.41 times capacity necessary to serve. For this non-demand
metered scope, capacity is the maximum of current or the twelve prior
months' actual meter kWh divided by 120. Exactly twelve consecutive
prior bills are required. Each scenario carries its actual billed
imports forward, including a zero-import month. PV cannot erase the
inherited minimum. Changing service within a year retains prior
history under the filed rule. The implementation prices this active
minimum exactly in numeric and symbolic billing. Riders apply in
addition to the minimum.

Environmental control, normalization, vegetation, and the dated effluent
and renewable components remain separate. The 2025 official notice
combines the environmental control amounts. Current 2026 sheets split
ECC and ECC-2. The 2026 notice confirms vegetation still applies despite
the omission marker beside the schedule's rider list.

Tax scope requires independently confirmed location outside every
municipality and local electric-tax district. Regulated electricity
qualifies for West Virginia's sales-tax exclusion. Local B&O/excise
tax bases differ by component and are outside this initial scope.

Final approval and an explicit written special agreement preserving
ordinary rates for the exact non-export PV/storage installation are
required. Paired storage charges only from onsite PV. Net metering,
Alternative Generation Service, standby treatment, export settlement,
demand-metered B and special rates remain outside scope.

The [ledger](utility_sources/mon_power_wv/sources.json) preserves rate
notices, current sheets, dates, benchmark evidence and explicit gaps.
The [batch validation report](PJM_Five_Utility_Batch_Validation.md)
records candidate-specific acceptance.
