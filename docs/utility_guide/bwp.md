# Burbank Water and Power

[Back to the utility guide](../Utility_User_Guide.md)

**Region:** City of Burbank, California  
**Role:** City-owned water and electric utility  
**Simulator status:** Selected plans implemented  
**Reviewed:** October 15, 2026

## Introduction and service area

Burbank Water and Power (BWP) is the community-owned water and electric utility for Burbank residents and businesses. Its rates and solar arrangements are separate from LADWP and SCE.

## What makes this service distinctive

This is a useful city-utility case for examining EV charging and the difference between simple energy billing and larger commercial demand billing. Customer service size, phase, enrollment, and dated energy-cost adjustments can affect the modeled bill.

Official background: [About BWP](https://www.burbankwaterandpower.com/ca/about-bwp-home). [Utility programs and priorities](https://www.burbankwaterandpower.com/about-bwp).

## Using this provider in the simulator

Residential Basic and EV TOU and non-demand commercial C are implemented through the shared browser and dispatch workflow. A bounded EV TOU residential net-billing cycle is also implemented.

Large commercial schedules using kVA demand are not modeled as simple kW demand. Other solar plans, legacy NEM, annual cash-out, and dates outside verified adjustment coverage remain unsupported.

The linked implementation notes define the verified plans and date windows. Availability in a running browser also depends on its active engine version.

- [Burbank import coverage](../LA_County_Utilities.md)
- [Updated Burbank solar scope](../Southern_California.md)

[Terms used in this profile](glossary.md)
