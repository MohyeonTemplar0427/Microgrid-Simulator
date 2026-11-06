# Appalachian Power West Virginia RS and SGS

The regional adapter supports ordinary Tariff 16 RS residential (015) and
metered SGS small commercial (231), one 120/240 V single-phase secondary
meter and bundled supply. Utility, supplier, West Virginia jurisdiction
and PJM AEP metadata remain independent. Optional wholesale prices add
no charges to this bundled tariff.

Verified complete matching calendar cycles are October 2025 and
September–October 2026. Earlier periods and intermediate 2026 changes
remain blocked. November 2025–January 2026 also remain blocked because
the surviving combined ENEC sheet and November CRRC true-up have not
been reconciled. Later 2026 true-ups are outside the evidence.

RS uses a monthly customer charge and decreasing 500 kWh energy block,
with a third block above 1,350 kWh in January, February and December.
The supported cycles are outside that winter block. SGS is a flat energy
rate and monthly customer charge. Confirm the Company's SGS assignment
and independent normal maximum electrical capacity requirements below
10 kW. The implementation's native/import caps are 25 kW RS and 9.9 kW
SGS and do not determine tariff eligibility.

Base charges, ENEC including its embedded CRRC, EEDR, environmental
compliance, broadband, Business Ready Sites and ENG/RET stay separately
identified. CRRC is collected once within ENEC. The original ENG precision
is 0.00313 cents/kWh RS and 0.00245 cents/kWh SGS. Rounded charge-table
amounts are unsuitable for reproducing that calculation. Current rates
match the utility's published 1,000 and 2,000 kWh residential examples.

The initial tax scope requires independently confirmed location outside
all municipalities and local electric-tax districts. West Virginia's
regulated-electricity sales-tax exclusion applies. Municipal B&O,
excise surcharges, assistance, optional programs and special charges
are outside this scope.

PV and PV-charged paired storage require final interconnection approval
and a written Company special agreement that preserves these ordinary
import rates for the exact installed equipment. The statutory solar
settlements, optional generation tariffs, export credits, standalone
storage and grid charging remain outside the implemented account scope.

The [source ledger](utility_sources/appalachian_wv/sources.json) distinguishes
downloaded current sheets from cached official historical sheets, whose
direct PDF routes returned 404. See the [batch validation report](PJM_Five_Utility_Batch_Validation.md)
for candidate-specific checks and exclusions.
