# Site type and location in the browser

Step 2 combines geographic location with Commercial or Residential site type.
The same nine-step wizard is retained. Geography still supplies candidate
providers from the CEC map; account eligibility must be confirmed separately.
Site type filters supported model scope and does not establish utility service.

| Site selection | Account class | Connected billing |
| --- | --- | --- |
| Commercial | Commercial | Existing mapped PG&E, CCA, Hetch Hetchy, AMP and SVP schedules |
| Residential: house | Residential | AMP D-1 and SVP D-1, import-only storage |
| Residential: apartment / individual unit | Residential | AMP D-1 and SVP D-1 for an eligible individual account |
| Residential: multifamily common areas | Nonresidential | Existing commercial schedules, only if assigned to the separate common-area account |

Unsupported provider/class combinations remain visible but disabled. Residential
PG&E/CCA/Hetch Hetchy billing and dispatch are not connected to the browser yet;
selecting a house or unit cannot silently use a commercial tariff or flat price.
Existing tariff coverage, phase, voltage, account-history and cycle validation
remain authoritative. This change adds no rates and extends no coverage dates.

Common-area studies exclude dwelling loads and shared-generation settlements.
They use explicit constant loads, or municipal daily-peak/CSV inputs. Whole-building
multifamily synthetic load is not offered as a common-area approximation.
Commercial synthetic profiles remain office, retail, school and industrial load
shapes; a shape does not determine tariff eligibility or create an industrial
customer-class option.

Changing site type/subtype clears provider selection, tariff selection, municipal
account confirmations and load inputs. Location changes clear service and account
confirmation. Battery settings remain editable. Explicit default buttons use
illustrative residential storage (10 kWh, 5 kW, 50% initial SOC) and residential
municipal load (1 kW base, 3 kW evening peak). These are study assumptions, not
sizing recommendations or inferred household consumption. Existing values are
never overwritten by default buttons.

New browser submissions save `site_profile: {site_type, subtype}` with the
request. The shared backend rejects mismatched account classes and unsupported
provider/class combinations before queueing and in the pinned worker. The field
is an additive optional extension of schemas 2–4 so existing saved requests
remain executable under their original contracts. Reopening an older request
requires reviewing its classification; no residential subtype is inferred.

The desktop GUI retains its existing controls and backend billing support;
this change concerns the browser setup and its persisted request validation.

## PV availability after the simulation dates

The section after Step 4 asks whether the simulated microgrid has PV. This
choice is explicit; the default-values buttons do not select it.

- Yes retains Solar weather, PV, Inverter and Battery / ESS configuration.
- No (grid-only) skips all four and goes directly to Economics and Review.
  The calculation bills native load as grid imports. It does not retrieve
  weather, model equipment, optimize storage or perform AC validation.
- AMP/SVP also retain their existing no-PV, battery-only option, which skips
  solar configuration but keeps battery power and energy controls. PV remains
  unavailable for their current supported billing path.

Schema 5 persists generic grid-only studies without solar, weather, battery,
ESS or strategy fields. Existing billing functions calculate all supported
monthly demand, fixed and energy charges. Schema 4 municipal requests use
`grid_only: true`, `battery: null` and zero degradation cost; their authoritative
municipal bill is calculated without invoking the storage optimizer. Existing
saved studies retain their original behavior and reopen with the matching choice.

## Regional historical carbon

New browser studies require Electricity Maps historical carbon, automatically
mapped from the Step 2 coordinates. The currently supported Bay Area study
rectangle (36.8–38.9° N, 123.6–121.0° W) maps to the existing `caiso_np15`
configuration: `US-CAL-CISO`. This rectangle defines application study coverage,
not an exact balancing-authority or utility-service boundary. Locations outside
this coverage fail explicitly until another regional mapping is implemented. The study dates determine
retrieval. This is a CAISO-wide proxy for the supported California sites,
including municipal studies; a municipal or CCA product's own supply mix is
not inferred from it. Regional observations and provider estimates are not
site-level measurements, and average intensity is not marginal avoided carbon.

The worker uses the existing Electricity Maps 15-minute past-range adapter.
Complete native coverage is required; 30/60-minute studies average complete
native intervals. Five-minute historical studies are rejected rather than
interpolated. Local calendar boundaries preserve DST days. API credentials
are loaded from the configured local environment file and never saved with
study inputs. Authentication, entitlement and coverage failures remain errors.

The browser has no carbon source selector or constant-value field. New requests
use `region: from_location`; the backend resolves and validates the coordinates.
Explicit constant sources are rejected. Older requests without `carbon` retain
their original behavior for compatibility; reopening them in the browser uses
location-mapped historical data for a new run. Retrieved
`carbon.csv` and checksum/provenance `carbon.json` are saved in each study;
reusing those files validates both the horizon and checksum. Simulation inputs
and result metadata expose the applied values and regional limitation.
PV studies use the signal in existing carbon-aware optimization; grid-only
and municipal studies report interval-weighted emissions. Municipal dispatch
remains cost-optimal, not carbon-optimal.

## Setup presentation and dates

Economics labels the tariff selector “Billing Plan”; Step 3 uses “Electricity
Service Provider”. Carbon retrieval remains automatic but has no setup section.
Timezone is a hidden derived value from the configured location mapping
(America/Los_Angeles for the current supported area); it remains in saved
requests/results. The OpenStreetMap search notice is at the page bottom.

The explicit default-values button fills empty study dates using today's date
in the site's timezone: start one calendar year earlier, end one calendar month
after start. Leap days and month ends clamp to the last valid date. Existing
entries are preserved. If only one boundary is missing, it is derived one month
from the entered boundary. These date defaults do not extend tariff coverage
or override municipal complete-billing-cycle requirements.
