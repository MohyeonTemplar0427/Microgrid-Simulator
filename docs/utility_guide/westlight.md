# WestLight Energy formerly Peninsula Clean Energy

[Back to the utility guide](../Utility_User_Guide.md)

**Region:** San Mateo County and Los Banos, California  
**Role:** Community-choice generation provider with PG&E delivery  
**Simulator status:** Selected plans implemented  
**Reviewed:** October 15, 2026

## Introduction and service area

WestLight Energy is the public community-choice provider formerly named Peninsula Clean Energy. Its service communities include San Mateo County and Los Banos. Older maps, bills, and simulator identifiers may retain the Peninsula name.

## What makes this service distinctive

The provider spans geographically separated communities, so a single weather file is not a good default for every account. Choose site-specific weather and confirm generation enrollment independently of PG&E delivery. Product premiums and applicable delivery adjustments belong in the combined bill.

Official background: [Service communities](https://www.westlightenergy.org/). [Official name change](https://www.westlightenergy.org/news-releases/peninsula-clean-energy-rebrands-as-westlight-energy-name-change-will-appear-on-utility-bills-starting-july-17/).

## Using this provider in the simulator

Commercial secondary B-1 options for ECOplus and ECO100 are modeled with explicit phase and PCIA vintage. Billing and the location-based optimizer use the combined supported import price.

Residential plans, other commercial classes, and solar settlement are not enabled through this provider adapter. Its verified date window is narrower than the company’s operating history.

The linked implementation notes define the verified plans and date windows. Availability in a running browser also depends on its active engine version.

- [Peninsula and South Bay billing](../Bay_Area_CCA_Billing.md)

[Terms used in this profile](glossary.md)
