# Pacific Gas and Electric Company

[Back to the utility guide](../Utility_User_Guide.md)

**Region:** Northern and Central California  
**Role:** Investor-owned delivery utility and bundled supplier  
**Simulator status:** Selected plans implemented  
**Reviewed:** October 15, 2026

## Introduction and service area

Pacific Gas and Electric Company, usually called PG&E, supplies electricity and natural gas across much of Northern and Central California. Its electric territory contains separate municipal-service areas; a PG&E gas connection does not establish that PG&E delivers electricity to the same address.

## What makes this service distinctive

This is a broad territory rather than one uniform load or weather region. For a study, use the actual site weather, building use, heating equipment, and rate-plan baseline information. Customers may buy bundled electricity from PG&E or receive generation from a community-choice provider while retaining PG&E delivery. Those arrangements require different bill components.

Official background: [PG&E company profile](https://www.pge.com/en/about/company-information/company-profile.html). [Confirm electric service separately from gas](https://help.pge.com/s/article/How-can-I-tell-if-PGE-serves-my-address?language=en_US).

## Using this provider in the simulator

Residential families include E-1, E-TOU-C, E-TOU-D, EV2-A, and E-ELEC; commercial families include B-1, B-6, B-10, B-19, and B-20 with supported variants. Shared billing, dispatch, and browser workflows are present, together with bounded solar settlement and annual replay paths.

Coverage is plan-, date-, account-, and solar-program-specific. A supported import plan does not automatically support every export arrangement. Check the active engine catalog and the applicable solar notes before comparing savings.

The linked implementation notes define the verified plans and date windows. Availability in a running browser also depends on its active engine version.

- [Generated PG&E tariff reference](../PGE_Tariff_Reference.md)
- [Billing and solar architecture](../Microgrid_Backend_Architecture.md)

[Terms used in this profile](glossary.md)
