# San Diego Gas and Electric

[Back to the utility guide](../Utility_User_Guide.md)

**Region:** San Diego County and southern Orange County, California  
**Role:** Investor-owned delivery utility and bundled supplier  
**Simulator status:** Selected plans implemented  
**Reviewed:** October 15, 2026

## Introduction and service area

San Diego Gas and Electric (SDG&E) supplies electric and gas services in the San Diego region and southern Orange County. Some electric customers receive generation through a community-choice provider while retaining SDG&E delivery.

## What makes this service distinctive

Use site-specific weather and account-confirmed baseline information across coastal and inland locations. A separate generation provider changes supply charges but does not remove the delivery portion of the bill. The same city name does not establish the customer’s generation enrollment.

Official background: [About SDG&E](https://www.sdge.com/more-information/our-company/about-us).

## Using this provider in the simulator

Selected residential TOU-DR1, TOU-DR2, and EV-TOU-5 imports are implemented with bundled, San Diego Community Power, or Clean Energy Alliance generation, subject to account restrictions. The shared browser and battery optimizer use these components.

Commercial plans and solar export are not supported by this extension. CCA accounts inside City of San Diego limits are blocked pending fee-ordering reconciliation, and zero local utility-user tax is required by the bounded path.

The linked implementation notes define the verified plans and date windows. Availability in a running browser also depends on its active engine version.

- [San Diego scope and dates](../San_Diego.md)

[Terms used in this profile](glossary.md)
