# PECO residential and small-commercial billing

Candidate backend and local-browser scope: **January 1, 2025–October 19, 2026**, ordinary PECO
default-supply **R, R-TOU, measured GS and GS-TOU**. These are four study options
on two filed base schedules; TOU changes generation pricing, not delivery service.
See the [source manifest](utility_sources/peco/manifest.json) and normalized
selected tariff pages beside it. Original PDFs remain in the ignored research
cache; document URLs, PDF hashes, page numbers and excerpt hashes are retained.

Distribution utility, Pennsylvania jurisdiction, PECO retail supplier, PJM,
PECO transmission zone and optional wholesale node remain separate fields.
Selecting PECO requires independent service/eligibility confirmation; a state,
coordinate or nearby PJM node does not establish service territory. The default
site is an explicitly hypothetical Chester County account outside Philadelphia.

## Verified rates and arithmetic

All rates below are dollars. Generation columns are standard / TOU peak /
TOU super-off-peak / TOU off-peak, per kWh. Effective-date boundaries are local
Eastern dates. January prices are filed in the January2025 book; March prices
in the April book; June prices in the September book; December2025 prices in
the January2026 compilation on sheets **effective December1,2025**. January2026
delivery prices are never used for2025.

| Effective | R generation | GS generation | R TSC/kWh | GS TSC/billed kW |
|---|---|---|---:|---:|
| Jan1 | .08429 / .28141 / .04336 / .06157 | .08336 / .22515 / .04406 / .06521 | .00858 | 2.13 |
| Mar1 | .08381 / .27978 / .04311 / .06122 | .07170 / .19367 / .03790 / .05609 | .00858 | 2.13 |
| Jun1 | .09508 / .29688 / .04899 / .07055 | .08651 / .22645 / .04669 / .06863 | .00892 | 2.05 |
| Dec1 | .10237 / .31960 / .05274 / .07595 | .09325 / .24405 / .05032 / .07397 | .00787 | 1.57 |

TOU peak is **14:00–18:00 Monday–Friday except PJM holidays**; super-off-peak
is midnight–06:00 every day; other intervals are off-peak. The published
[2025 PJM calendar](https://www.pjm.com/-/media/DotCom/markets-ops/settlements/2025-business-calendar.pdf)
includes MLK Day, Presidents' Day and the Friday after Thanksgiving, unlike
the shorter NERC off-peak list. PECO's broader general holiday definition is
also not substituted for the TOU-specific PJM rule. Local DST is preserved.
TOU enrollment requires the eligible smart meter/email and no CAP, virtual net
metering or active twelve-billing-month re-enrollment exclusion; confirm these
facts without collecting an email address or account identifier.

Printed distribution prices already include riders. The adapter strips those
components from the original January schedule and recomposes the dated riders
once. R's underlying variable base is .09465/kWh; GS's underlying demand base
is10.63/kW. This yields R distribution .09655/kWh January–November and
.09649/kWh December; GS demand11.35 January–May,11.34 June–November and11.24
December. R customer charge is11.29 January–March and11.30 April–December,
including consumer education. GS fixed charge is31.20 single-phase measured
or74.66 polyphase. GS also has NDCA−.0006/kWh and separate EEPC .00899/kWh
January–May, .00392 June–December. Residential EEPC, USFC, NDCA, ICUS/FARS and
NBT are embedded, not additional bill lines. DSIC and STAS are filed0% in2025.
The year-long ICUS and FARS credits are included; their2026 expiry is not
backdated. The unrounded components and study half-up-cent lines are retained.

### 2026 extension (reviewed October 19, 2026)

The January, April, September and October2026 compilations retain the dated
component sheets needed to reconstruct the year. The July1 cleanup also has
an independent [PUC effectiveness letter](https://www.puc.pa.gov/pcdocs/1937866.pdf).
Compilation dates do not replace individual sheet effective dates. The October
filings change some other classes but leave R/GS ICUS/FARS at their July values.
December2026 supply and January2027 USFC are still listed as **proposed** on
PECO's revision page; they are not enabled. Coverage is bounded to the review
date rather than extrapolating the current book through the rest of2026.

| Effective | R generation standard / peak / super-off / off ($/kWh) | GS generation standard / peak / super-off / off ($/kWh) | R TSC/kWh | GS TSC/billed kW |
|---|---|---|---:|---:|
| Jan1 (Dec2025 supply retained) | .10237 / .31960 / .05274 / .07595 | .09325 / .24405 / .05032 / .07397 | .00787 | 1.57 |
| Jun1 | .10785 / .31430 / .05767 / .08362 | .10728 / .26264 / .06010 / .08835 | .00974 | 2.20 |

The official residential PTC corroborates the supply sum:11.024¢/kWh before
June1 and11.759¢/kWh afterward. TOU multipliers change in June; the filed final
prices above are used directly, rather than recalculated from rounded multipliers.

| Effective | R fixed | R embedded distribution/kWh | GS distribution/billed kW | GS separate EEPC/kWh | DSIC |
|---|---:|---:|---:|---:|---:|
| Jan1 | 11.30 | .10276 | 11.50 | .00392 | 0% |
| Apr1 | 11.29 | .10276 | 11.50 | .00392 | .11% |
| Jun1 | 11.29 | .10246 | 11.48 | .00121 | .11% |
| Jul1 | 11.29 | .10236 | 11.48 | .00121 | .42% |
| Oct1 | 11.29 | .10236 | 11.48 | .00121 | 1.05% |

January USFC becomes .00287/kWh; the2025 ICUS/FARS credits end. April consumer
education becomes .04/month, included once in the printed11.29 fixed charge.
June NBT becomes .00322/kWh R and .85/billed kW GS; EEPC becomes .00232/kWh R
(embedded) and .00121/kWh GS (separate). July introduces small R reconciliation
credits: ICUS−.00009/kWh and FARS−.00001/kWh. GS remains zero for both credits.
NDCA remains−.0006/kWh. The underlying distribution bases remain unchanged.

STAS is a **0.04% credit from January1** on distribution base and rider charges,
excluding GSA generation and default-supply TSC. DSIC applies to **distribution
plus STAS**, using the **bill date** (printed sheet50, bills-rendered basis).
Ordinary commercial sales tax follows those adjustments; residential remains
exempt. Both numeric bills and symbolic dispatch use these same expressions.
Bill metrics retain the service rate date, bill date and percentage rates.

The [PJM2026 calendar](https://www.pjm.com/-/media/DotCom/markets-ops/settlements/2026-business-calendar.pdf)
lists July4 on Saturday; **July3 remains an ordinary weekday**. The code does
not invent a Friday observed holiday or apply PECO's broader general calendar.

GS uses maximum **30-minute** average import, with filed nearest0.1-kW demand
measurement, minimum1.2kW and the below1100-kWh rule (lesser measured demand
or monthly kWh/175, still at least1.2kW). Dispatch uses the same expressions.
Integer demand rounding uses conservative0.00001-kW (0.01-W) headroom at a rounding
tie. A0.00001-kWh band immediately below the discontinuous1100-kWh boundary
is explicitly rejected; numeric and optimized bills must reconcile. This first
GS scope requires utility-confirmed procurement class2 and measured peak≤100kW;
the class is determined from the **prior June–May** period for the following
June, never inferred from a newly optimized peak. Unity billing PF is explicit;
reactive adjustments, unmeasured GS and larger contract-demand rules are excluded.

Capacity, ancillary services, losses and AEPS are included in GSA. Network
transmission is charged through TSC; nonbypassable transmission is embedded in
distribution. There is no extra PJM LMP, capacity PLC or transmission tag charge.
[PA tax rules](https://www.pa.gov/agencies/revenue/resources/tax-types-and-information/sales-use-and-hotel-occupancy-tax)
exempt residential electricity; ordinary commercial purchases use6% state tax,
or8% in Philadelphia when explicitly selected. Exempt and mixed-use business
accounts require their own rules.

## Supported cycles and equipment

Supply complete26–35-day regular, initial or final meter cycles, including
explicitly hypothetical calendar months. Rule14.7 bases proration on period
length; an initial/final label alone does not prorate a26–35-day bill.
A cycle may cross a **DSIC-only** change: its single measured
GS demand and full distribution subtotal receive the rate on its bill date.
For example, September20–October19,2026 uses1.05% DSIC, not a blended .42/1.05%
rate or two separately measured monthly peaks. The browser's documented-cycle
JSON supports this cycle, and the resulting bills expose their rate basis.

The default **verified-only** mode still rejects service/bill dates crossing
other applicable component changes and short/extended cycles. The GSA's
non-proration clause and Rule 1.3 do not establish the missing operational
allocation policy. See the [evidence review](PECO_Billing_Cycle_Review.md).

An explicitly accepted **provisional cycle mode** now supports 1–45 complete
local days and applicable crossings, within the same price coverage. It assumes
local days/30 outside 26–35 days; actual-interval delivery energy; local-day
weighted monthly delivery prices; one full-cycle GS demand; normalized low-usage
threshold/hours; and whole-cycle GSA/TSC selected by the final inclusive service
date. DSIC retains bill-date treatment. These are study assumptions, not verified
PECO allocation rules. Bills, dispatch objectives, savings, warnings and downloads
retain the versioned assumption ledger. Details and reproduction:
[PECO provisional allocation](PECO_Provisional_Allocation.md).

`peco.cycle_review(account, index)` retains local days separately from elapsed
hours, all intervening component changes and issuance-gap diagnostics. In
provisional mode it reports the unresolved allocation requirements separately
from blocking errors. Old saved requests default to verified-only behavior;
old results are not relabeled. Both service and bill dates remain within the
verified price window. Do not artificially split a real meter cycle to bypass
these checks or exploit the declared proration boundaries.

PV and storage reuse the shared equipment/dispatch models and require approved
non-export ordinary service. PV DC and inverter AC ratings must each be<100kW;
the capacity-reservation rider applies to qualifying generation≥100kW and is
not modeled. Storage is not itself a generator under that rider. Grid charging
requires explicit operating permission; no battery or solar exports are credited.
RS-2 net metering, heating RH, CAP, competitive suppliers, night service, special
riders and larger procurement classes are not part of this implementation.

All three scenarios use identical native load/weather, with the same initial
and final battery energy. Annual execution is linked monthly perfect foresight,
not a jointly optimized year or an operational forecast. Shared OpenDSS replay
checks every15-minute interval with representative residential split-phase or
commercial three-phase circuits. It does not establish surveyed-site feasibility
or impose network constraints on dispatch. Scheduled billing flows are kept
separate from replay PCC measurements and circuit losses.

## Reproduce validation

```sh
/usr/local/bin/python3 tools/validate.py --tier focused --test test/test_peco.py
/usr/local/bin/python3 tools/run_regional_validation.py --prepare-inputs --utility peco --inputs .cache/peco_inputs_2025
/usr/local/bin/python3 tools/run_regional_validation.py --execute --utility peco --period annual --inputs .cache/peco_inputs_2025 --output .cache/peco_2025_validation
```

Preparation explicitly retrieves2025 Open-Meteo ERA5 reanalysis at the declared
site, retains original JSON/request/provenance/hash and never substitutes
NSRDB or a different year. ERA5 hourly reanalysis is converted by the existing
adapter to the15-minute study grid; it is not a15-minute station measurement.
Native demand is the existing deterministic synthetic household/office shape,
scaled to2/20-kW peaks, imported back as timestamped CSV. It is not a PECO
measured or calibrated customer profile. Residential PV is5kW DC/4kW AC,
battery10kWh/3kW; commercial PV10kW DC/8kW AC, battery30kWh/8kW. Wear is
reported separately and excluded from the bill-minimizing objective by default.
The driver selects both standard and TOU plans for both classes and audits
bills, physical balances, SOC, proof status, saved tables and electrical replay.
Validation results and candidate identity are recorded separately after execution.

Validated results, parameters, source pins and limitations: [PECO 2025 validation](PECO_2025_Validation.md); [aggregate CSV](PECO_2025_Validation.csv).

The local browser now starts hypothetical PECO studies in **September2026**,
the latest complete calendar month. Previously saved2025 requests keep their
explicit dates and tariffs. The historical driver still selects2025 unless
custom dates are supplied. To execute January–September2026, prepare an
independent exact-date ERA5 cache and use `--period custom --start-date
2026-01-01 --end-date 2026-09-30`; never reuse or shift the2025 weather cache.


The2026 prepared cache can be reproduced with the existing ERA5 adapter (live
retrieval is a separate, explicit step; the validation launcher remains offline):

```sh
/usr/local/bin/python3 - <<'PYCODE'
import json
from pathlib import Path
from src.profiles.era5 import fetch_era5
folder = Path(".cache/peco_inputs_2026/peco")
folder.mkdir(parents=True, exist_ok=True)
target = folder / "era5.json"
if target.exists():
    raise FileExistsError("Preserve cached evidence; select a new input folder")
payload = fetch_era5("2026-01-01", "2026-09-30", 39.96, -75.60)
target.write_text(json.dumps(payload, indent=2) + "\n")
PYCODE
/usr/local/bin/python3 tools/validate.py --tier focused --area regional --area validation --timeout 360 --regional --utility peco --period custom --start-date 2026-01-01 --end-date 2026-09-30 --inputs .cache/peco_inputs_2026 --output .cache/peco_2026_validation
```

Validated2026 evidence: [January–September simulations and boundary tests](PECO_2026_Validation.md); [aggregate CSV](PECO_2026_Validation.csv).
