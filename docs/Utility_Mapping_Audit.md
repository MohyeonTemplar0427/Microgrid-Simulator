# Electricity territory mapping audit — 2026-09-17

Revalidated 14 public reference coordinates against the live CEC distribution layer (point intersection and 100 m boundary screen) and CCA layer. These are representative location checks, not exhaustive address-level certification. All tariff coverage limits remain unchanged. No new regional billing schedules were added.

| Reference location | Latitude, longitude | Mapped delivery candidates | Mapped CCA | Result |
|---|---|---|---|---|
| San Francisco | 37.7793, -122.4193 | Pacific Gas & Electric Company; Hetch Hetchy Power | CleanPowerSF (CPSF) | ambiguous |
| San Mateo | 37.563, -122.3255 | Pacific Gas & Electric Company | Peninsula Clean Energy | approximate |
| Redwood City | 37.4852, -122.2364 | Pacific Gas & Electric Company | Peninsula Clean Energy | approximate |
| Sunnyvale | 37.3688, -122.0363 | Pacific Gas & Electric Company; Power and Water Resource Pooling Authority | Silicon Valley Clean Energy (SVCE) | ambiguous |
| Milpitas | 37.4323, -121.8996 | Pacific Gas & Electric Company; Power and Water Resource Pooling Authority | Silicon Valley Clean Energy (SVCE) | ambiguous |
| San José | 37.3382, -121.8863 | Pacific Gas & Electric Company; Power and Water Resource Pooling Authority | San Jose Clean Energy (SJCE) | ambiguous |
| Santa Clara | 37.3541, -121.9552 | Power and Water Resource Pooling Authority; Silicon Valley Power | None | ambiguous |
| Alameda | 37.7652, -122.2416 | Alameda Municipal Power | None | approximate |
| Oakland | 37.8044, -122.2712 | Pacific Gas & Electric Company | Ava Community Energy (Ava) | approximate |
| Palo Alto | 37.4419, -122.143 | Power and Water Resource Pooling Authority; City of Palo Alto | None | ambiguous |
| Los Banos | 37.0583, -120.8499 | Pacific Gas & Electric Company | Peninsula Clean Energy | approximate |
| Sacramento | 38.5816, -121.4944 | Sacramento Municipal Utility District | None | unsupported |
| Los Angeles | 34.0522, -118.2437 | Los Angeles Department of Water & Power; Metropolitan Water District of So. Cal | None | ambiguous |
| San Diego | 32.7157, -117.1611 | San Diego Gas & Electric; Metropolitan Water District of So. Cal | San Diego Community Power (SDCP) | ambiguous |

## Findings and fixes

- AMP applies to the City of Alameda sample, not Alameda County generally. Oakland maps to PG&E delivery and Ava generation; Ava remains visible but billing-disabled.
- Santa Clara maps to SVP; Sunnyvale/Milpitas map to PG&E plus SVCE; San José maps to PG&E plus SJCE. No county-wide SVP or SVCE assignment is made.
- San Mateo, Redwood City and Los Banos map to PG&E plus Peninsula Clean Energy, now WestLight Energy. The older CEC display name is retained as source evidence.
- San Francisco includes PG&E, Hetch Hetchy and CleanPowerSF candidates. Hetch Hetchy eligibility remains account-specific; a polygon intersection is not permission to choose its tariff.
- Palo Alto is not assigned PG&E. Sacramento, Los Angeles and San Diego retain their mapped providers without substituting supported Bay Area tariffs. Billing for those providers is not yet implemented.
- Unsupported CCA candidates are now displayed rather than silently omitted. PG&E delivery does not imply bundled PG&E generation.
- Hetch Hetchy now uses AgencyNum 80522 instead of a browser OBJECTID alias. Implemented CCA identities require both the expected CEC record ID and official name, with Type=CCA. Unknown/renumbered identities remain billing-disabled.
- Administrative overlays such as WAPA are no longer labeled as CCA generation suggestions. PWRPA remains an unresolved delivery overlap; it is not silently discarded.
- Exact point matches and nearby boundary candidates are distinguished. Implemented CCA billing is enabled only with a PG&E point match, not a PG&E polygon merely within the screening buffer.

## Sources and evidence

- [CEC distribution layer](https://services3.arcgis.com/bWPjFyq029ChCGur/arcgis/rest/services/ElectricLoadServingEntities_IOU_POU/FeatureServer/0)
- [CEC Other layer](https://services3.arcgis.com/bWPjFyq029ChCGur/arcgis/rest/services/ElectricLoadServingEntities_Other/FeatureServer/0)
- [SVCE communities](https://www.svcleanenergy.org/about-2/communities/)
- [WestLight service area](https://www.westlightenergy.org/)
- [SVP facts](https://www.siliconvalleypower.com/svp-and-community/about-svp/utility-fact-sheet?navid=1)
- [AMP utility FAQ](https://www.alamedamp.com/faq)
- [Hetch Hetchy Power](https://www.sfpuc.gov/programs/clean-energy/hetch-hetchy-power)
- [Palo Alto Utilities](https://www.paloalto.gov/Departments/Utilities)

Saved evidence: `utility_sources/cec-region-mapping-audit-2026-09-17.json` contains coordinates, timestamps, source versions and response fingerprints; `utility_sources/cec-layer-identities-2026-09-17.json` contains the queried public layer attributes.

## Limits before statewide expansion

CEC layers are approximate screening data and may lag provider membership changes. Generation-layer coverage is a suggestion, not confirmation of CCA enrollment. Geographic data can show institutional or special-service overlaps. Actual service and tariff eligibility still require account confirmation. Cooperative/tribal service classification outside the current supported footprint needs separate review before billing expansion. City-center tests cannot establish correct mapping at every address.

## Validation

- `/usr/local/bin/python3 -m pytest -q`: **1001 passed in 58.08s**.
- The production browser choice builder was exercised against all 14 saved live responses, plus a nearby-only PG&E/CCA boundary case: **15 checks passed**.
- New offline tests cover Hetch Hetchy agency identity, recycled OBJECTIDs, exact versus nearby matches, verified CCA identities, unsupported Ava retention, and administrative-overlay filtering.
- Local preview refreshed with the corrected pinned backend; source changes remain uncommitted on main.
