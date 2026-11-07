# Potomac Edison West Virginia R and G

The adapter implements ordinary Tariff No. 3 R residential and G small general
service. Potomac Edison is the utility and bundled supplier; West Virginia is
the jurisdiction and APS is PJM transmission-zone metadata. Maryland tariffs
and Mon Power's component rates are separate.

Verified complete calendar cycles cover August–December 2025 and
August–November 2026. Earlier 2025 cycles, July transitions, intermediate
2026 component intersections and December 2026 remain blocked. Use a matching
service/bill month, final-day bill date, full monthly charges and consecutive
Eastern-time 15-minute data. These are explicit study restrictions, not a
claim about every actual meter-reading schedule.

R is ordinary individually metered residential service. G requires independent
Company confirmation of retained non-demand-metered service, no pending
reclassification, and normal maximum electrical requirements below 10 kW.
The study separately caps G native load/imports at 9.9 kW and 6,000 kWh per
month; those bounds do not establish eligibility. R's study peak is 25 kW.

G's active monthly minimum is the greater of customer-plus-energy charges and
$2.41 times capacity necessary to serve. In this non-demand-metered scope,
capacity is the maximum actual kWh in the current or twelve prior months
divided by 120. Exactly twelve consecutive actual prior bills are required.
Each scenario carries forward its actual imports, including zero-import months.
Riders apply in addition to the minimum. PV does not erase inherited history.

The 2025 official notices combine ECC and ECC-2. The 2026 tariff itemizes the
two factors separately. Normalization, vegetation, and the historical effluent
and renewable components remain separate. Potomac's ECC/normalization factors
differ from Mon Power's even though the supported aggregate example bills
coincide; they were transcribed independently from Potomac's sources.

Initial tax scope requires an independently confirmed location outside all
municipalities and local electric-tax districts. Regulated electricity has the
West Virginia sales-tax exclusion. Local tax, assistance, special facilities,
optional programs and other account-specific adjustments are outside scope.

PV and paired storage require final interconnection approval active before the
cycle and a written agreement preserving ordinary import rates for the exact
installation without AGS/standby charges. Storage charges only from onsite PV.
Export settlement, net-metering banks and standalone storage are unsupported.
Hypothetical approvals are labeled as assumptions; actual accounts need evidence.

The [source ledger](utility_sources/potomac_edison_wv/sources.json) records
downloaded tariff/notice hashes, component evidence and gaps. Candidate-specific
acceptance is recorded in the [second batch report](PJM_Second_Five_Utility_Batch_Validation.md).
