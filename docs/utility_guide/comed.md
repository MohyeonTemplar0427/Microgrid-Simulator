# Commonwealth Edison

[Back to the utility guide](../Utility_User_Guide.md)

**Region:** Northern Illinois, including the Chicago region  
**Role:** Regulated electric delivery utility with separate supply arrangements  
**Simulator status:** Selected plans implemented  
**Reviewed:** October 15, 2026

## Introduction and service area

Commonwealth Edison, known as ComEd, delivers electricity in northern Illinois. The delivery utility and the chosen electricity supply arrangement are separate parts of an account; ComEd should not be treated as the name of a wholesale electricity market.

## What makes this service distinctive

The regional wholesale system is PJM. A customer’s tariff determines whether hourly market prices affect the retail bill directly. For seasonal studies, specify the building’s actual heating fuel and cooling/occupancy schedule rather than assuming all winter heating is electric.

Official background: [ComEd service introduction — historical fact sheet, used only for identity and geography](https://www.exeloncorp.com/company/Documents/ComEd_overview_fact_sheet.pdf).

## Using this provider in the simulator

Residential and commercial BES/BESH arrangements are connected to the main load, PV, ESS, billing, and comparison workflow. Verified 2025 annual studies, historical weather inputs, saved results, and applicable representative electrical replay are documented.

Bills remain explicitly incomplete where state/local taxes and franchise charges are excluded. The integrated PV/storage case is non-export. Hourly supply requires the correct identified price series and account obligations; wholesale values must not be added again to bundled charges.

The linked implementation notes define the verified plans and date windows. Availability in a running browser also depends on its active engine version.

- [ComEd main workflow](../ComEd_Simulation_Integration.md)
- [Historical cycles](../ComEd_Historical_Rates_and_Billing_Cycles.md)
- [Annual input validation](../ComEd_Historical_Annual_Inputs.md)

[Terms used in this profile](glossary.md)
