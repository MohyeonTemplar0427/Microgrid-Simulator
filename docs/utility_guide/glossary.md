# Electricity service and simulation terms

[Back to the utility guide](../Utility_User_Guide.md)

These definitions explain the terms used in the profiles. Exact billing treatment comes from the selected account’s tariff.

| Term | Plain-language explanation |
| --- | --- |
| kW | Power: the rate at which electricity is consumed or produced. |
| kWh | Energy used or produced over time. A constant 2 kW load for 3 hours uses 6 kWh. |
| kVA and power factor | kVA measures apparent power. Power factor relates real kW to apparent kVA; a tariff charging for kVA cannot automatically be modeled as a kW charge. |
| Bundled service | The utility provides the account’s electricity supply and delivery arrangement. |
| CCA | Community Choice Aggregation: a public agency purchases electricity for enrolled customers while the existing utility generally retains delivery. |
| PCIA vintage | An account classification used to select applicable California supply-transition adjustments. It is not automatically the simulation year. |
| TOU | Time-of-use pricing: the energy price depends on when consumption occurs. |
| Energy tier | A price block based on consumption quantity, sometimes with a customer-specific allowance. |
| Baseline allowance | A tariff-defined quantity affecting eligible residential energy charges or credits. It is not the building’s measured baseline load. |
| Demand charge | A charge based on a defined power measurement, usually a maximum averaged over a specified interval and billing window. |
| Demand ratchet | A rule under which earlier demand can set a floor for later billed demand. |
| Contract demand | A utility/account agreement that may establish a billing or operating obligation independently of the current measured peak. |
| Billing cycle | The meter-reading or service period used for a bill; it need not be a calendar month. |
| Rider or adjustment | A separately specified charge or credit added under the tariff. It may change on different dates from base rates. |
| Native load | Building electricity demand before onsite PV and storage alter grid purchases. |
| Non-export PV/storage | An operating arrangement that prevents electricity export. Excess PV may need to be curtailed. |
| Curtailment | Available generation deliberately left unused because of operating or network limits. |
| NEM and net billing | Different solar billing arrangements. Eligible export credits, netting periods, and settlement rules depend on the actual program. |
| SOC | Battery state of charge: stored energy expressed as a fraction or percentage of usable/model capacity. |
| Historical perfect foresight | A simulation that knows the selected historical inputs in advance; it is not a forecast or proof of achievable real-time operation. |
| QSTS replay | Quasi-static time-series power flow: checking a sequence of operating points on a specified circuit. It does not by itself validate protection, transients, or islanding. |
| Pinned engine | A saved engine snapshot used to reproduce a study even when developers change the working source. |
| Supported date window | Dates for which the model has the required verified rates and rules. A software cutoff does not mean the utility stopped offering the plan. |

Examples of the supply/delivery distinction are explained by [CleanPowerSF](https://cleanpowersf.org/faq) and [Clean Energy Alliance](https://thecleanenergyalliance.org/faqs/). Model-specific conventions are documented in the [backend architecture](../Microgrid_Backend_Architecture.md).
