# Southern California Edison

[Back to the utility guide](../Utility_User_Guide.md)

**Region:** Parts of Central, coastal, and Southern California  
**Role:** Investor-owned electric delivery utility and bundled supplier  
**Simulator status:** Selected plans implemented  
**Reviewed:** October 15, 2026

## Introduction and service area

Southern California Edison (SCE) serves a large territory across Central, coastal, and Southern California. Municipal utilities occupy separate service areas, including Los Angeles city. An address in Los Angeles County is not enough to select SCE.

## What makes this service distinctive

For studies across this broad territory, check location-specific weather, baseline information, and commercial operating hours. Some customers have separate community-choice generation; selecting an SCE bundled plan for such an account changes the supply assumption.

Official background: [SCE service area](https://www.sce.com/customer-service-center/help-center/stop-start-move-service/faq/how-to-know-if-sce-is-my-electric-utility). [About SCE](https://www.sce.com/about-sce).

## Using this provider in the simulator

Selected residential D and TOU-D options and secondary commercial TOU-GS-1/2/3 and TOU-8 options are connected to billing, battery dispatch, and the shared browser. Bounded TOU-D-PRIME NBT and legacy NEM paths are documented separately.

The main Southern California account path is bounded and does not establish complete SCE CCA billing. Solar support varies by program, vintage, billing cycle, and storage arrangement; it is not a blanket annual true-up implementation.

The linked implementation notes define the verified plans and date windows. Availability in a running browser also depends on its active engine version.

- [Southern California coverage and solar rules](../Southern_California.md)
- [LA provider coverage](../LA_County_Utilities.md)

[Terms used in this profile](glossary.md)
