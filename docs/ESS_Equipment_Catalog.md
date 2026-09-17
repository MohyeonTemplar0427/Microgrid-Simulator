# ESS equipment catalog and candidate integration

## Scope and sources

The offline catalog is `src/equipment/ess_catalog.py`, revision `2026-09-16.2`.
The resolver in `src/equipment/ess.py` has no GUI or network dependency.
`search`, `detail` and `resolve` expose copied records, resolved battery
parameters, assumptions, missing requirements and per-parameter provenance.
Initial charge and backup reserve are user choices, not manufacturer facts.

## Retrieved simulation data

`data/equipment/ess_catalog.json` is a portable export of the three currently
cataloged choices. It contains published facts, source URLs/revisions, review
dates, missing requirements and resolution status. It is generated from the
Python catalog, which remains the source used by the engine. This is not a
claim to cover all CEC equipment. Regenerate it after reviewed catalog changes:

```sh
/usr/local/bin/python3 tools/export_ess_catalog.py data/equipment/ess_catalog.json
```

The default export does not accept modeling assumptions on the user's behalf,
so its `battery` values remain null. To explicitly accept the constant-efficiency
approximation and an AC-deliverable energy assumption for Powerwall 2:

```sh
/usr/local/bin/python3 tools/export_ess_catalog.py /tmp/ess_simulation_inputs.json \
  --accept-efficiency-approximation --powerwall2-capacity-basis ac_deliverable
```

Only `ready=true` resolutions contain engine inputs. Their `battery` mapping
can construct `Battery(**mapping)`; browser studies additionally retain the
whole resolution for validation and reproducibility. Powerwall 3 remains
blocked even with both flags. Its nominal AC energy, system output settings,
charging limits, separate efficiency paths and PV input limits are recorded;
they are not silently converted into an independent AC battery model.
Environmental ranges/derating notes are metadata, not thermal simulation.
Existing server snapshots are not refreshed by exporting or updating these files.

Sources were inspected on 2026-09-16:

- [CEC program](https://www.energy.ca.gov/programs-and-topics/programs/solar-equipment-lists),
  [ESS discovery list](https://solarequipment.energy.ca.gov/Home/EnergyStorage),
  and [battery discovery list](https://solarequipment.energy.ca.gov/Home/BatteryList).
  The latter lists electrochemical batteries, not necessarily complete AC systems.
  Neither listing establishes an interchangeable inverter pairing or an AC energy boundary.
- [Powerwall 2 North American datasheet](https://energylibrary.tesla.com/docs/Public/EnergyStorage/Powerwall/2/Datasheet/en-us/Powerwall-2-Datasheet.pdf),
  footer `NA - BACKUP - 2024-07-02`, p.1: the selected family is 1092170-xx-y;
  13.5 kWh usable, 5 kW continuous charge/discharge, 5.8 kVA, 90% AC–battery–AC
  efficiency, 120/240 V split phase. Conditions: 25 °C and 3.3 kW; efficiency
  is beginning-of-life. The separate 14 kWh total energy is retained but not
  used as the usable window. Surge ratings remain metadata.
- [Powerwall 2 multi-unit manual](https://energylibrary.tesla.com/docs/Public/EnergyStorage/Powerwall/2/InstallManual/BackupGateway/2/en-us/GUID-64A56007-BAD1-4482-90DE-C957756553CA.html),
  undated live page, sections “Service Type and Capacity Requirements” and
  “Pre-Requisites for Design”: up to 10 complete units per Gateway, subject
  to installation, impedance and service limitations. Multiple gateways are deferred.
- [aPower 2 datasheet](https://www.franklinwh.com/document/apower-2-datasheet),
  revision 2025-12-16, pp.1–2: SKU APR-10K15V2-US, nameplate aPower X-20,
  certification family aPower Xyyy. This preset selects 120/240 V, 11.5 kVA,
  8 kW continuous charge and 10 kW discharge. Usable energy is explicitly
  15 kWh AC. Grid–battery–load round-trip efficiency is 90%; energy/efficiency
  conditions are beginning-of-life, 25 °C, 3 kW. Up to 15 complete units per
  aGate is documented. Lower PCS settings, 208 V and mixed aPower arrangements
  are not silently substituted.
- [Powerwall 3 datasheet](https://energylibrary.tesla.com/docs/Public/EnergyStorage/Powerwall/3/Datasheet/en-us/Powerwall-3-Datasheet.pdf),
  2025 edition, pp.1–3: informational only. Its shared PV/storage inverter
  requires joint constraints; the solar-shifting efficiency path cannot be
  substituted for AC round-trip efficiency. Expansion batteries do not add
  a complete inverter's rating.

**Powerwall 2 capacity-boundary gap:** its datasheet labels energy “usable”
without explicitly naming the AC/internal measurement boundary. The
[USA warranty](https://energylibrary.tesla.com/docs/Public/EnergyStorage/Powerwall/General/Warranty/en-us/Powerwall-Warranty-EN.pdf),
Rev.2.6, effective May 6, 2026, p.1 footnote 5, says AC output for *throughput*;
that does not settle the usable-capacity boundary. The resolver therefore
requires the user to choose an explicit AC-deliverable or usable-internal
assumption. This is a conditional model, not a second fully verified energy
mapping. aPower 2 has the documented AC boundary. Both require acceptance of
the approximate one-way efficiency split. Warranty claims do not generate
any degradation curve.

## Equations and engine mapping

The existing optimizer and Battery use terminal charge/discharge power:

`E_next = E + eta_charge * P_charge * dt - P_discharge * dt / eta_discharge`.

Given compatible AC round-trip efficiency `r`, the offered approximation is
`eta_charge = eta_discharge = sqrt(r)`. It is recorded as assumed, not measured.

For AC-deliverable usable energy `U`, the equivalent usable internal capacity
is `C = U / eta_discharge`. With user reserve `b` and initial charge `s`, use
`SOC_min=b`, `SOC_max=1`, `E_initial=s*C`. Thus a full usable discharge delivers
`eta_discharge*C = U` at AC, and replenishing it consumes `U/r` AC. Deliverable
energy above reserve is `U*(1-b)`; available initial energy above reserve is
`U*(s-b)`. The equivalent state need not equal physical nominal cell capacity.
Manufacturer reserves are already excluded from usable energy and are not
subtracted again. For an explicitly chosen usable-internal basis, `C=U`.

Example: 15 kWh AC and 90% round-trip yield approximately 15.8114 kWh of
engine capacity. A 3 kW, five-hour discharge delivers 15 kWh; refilling takes
16.6667 kWh AC. A 20% reserve leaves 12 kWh AC dispatchable from full.

Identical **complete-system** quantities multiply energy and continuous
charge/discharge power separately. Efficiency does not change. No battery-only
expansion is supported. Aggregate power derates can be overridden explicitly;
they retain `user_overridden` provenance. Other changes require manual mode.
Published kVA is retained; no Q capability or actual residential wiring is
inferred from it. Unknown fields remain null, never zero.

Battery validation now allows a zero lower usable-energy bound, while rejecting
nonfinite values, invalid SOC ordering, out-of-window initial energy and invalid
power/efficiency values. Existing defaults and manual studies are preserved.
OpenDSS replay permits at most 1e-6 kWh of solver roundoff at the zero/full
energy boundary and clamps only its replay state; larger violations and
nonfinite values still fail, and the original dispatch table is retained.

## Replay limitations

The optimizer's kW is terminal power. OpenDSS receives that terminal setpoint;
its Storage energy accounting uses the same efficiency parameters. There is
no additional inverter conversion applied to the requested terminal power.
The representative balanced 480 V / 750 kVA circuit remains. Selection of
120/240 V equipment does not validate a split-phase installation. Replay
reports terminal tracking error; equipment kVA, reactive capability,
islanding behaviour and site/gateway service limits are not validated.

Constant efficiency and usable energy are model approximations outside the
source test conditions. Standby draw, thermal derates, installation-specific
limits, aging and mixed/expansion-only configurations remain unresolved or
deferred. This catalog is extensible by market and architecture, but currently
contains residential products only.

## CEC refresh review

The public Excel endpoint is repeatable and requires no credentials:
`https://solarequipment.energy.ca.gov/Home/DownloadtoExcel?filename=EnergyStorage`.
The inspected export contained 6,670 rows, with notice “Data has not changed
since September 11, 2026”. SHA-256:
`77d0c970b5e47c36a3a2fdba2f4cf920aa8c8d0770168ed87db10af729a9e526`.
The exact discovery names are saved on the catalog records. Other CEC variants
may have different powers under similar family names; manufacturer SKU and
operating-configuration review is still required.

Download explicitly, then run:

```sh
/usr/local/bin/python3 tools/review_cec_ess.py downloaded.xlsx review.json
/usr/local/bin/python3 tools/review_cec_ess.py downloaded.xlsx next-review.json --previous review.json
```

This offline tool checks the workbook header, records its hash/source notice,
and reports added/removed identities. It never edits or promotes catalog
records. Detailed changed specifications require source review and a new
catalog revision. It uses pandas/openpyxl in the verified interpreter.
Simulation, catalog resolution and tests never download catalog data.

## Browser contract and reproducibility

Schema 3 extends the location request with `ess` and `solar_optimization`, each
nullable. Manual mode keeps the existing battery fields. Equipment mode saves
the entire reviewed record, catalog revision, selection, user overrides,
resolved battery fields, source provenance, assumptions, resolver version and
checksum. Submission rejects battery fields that differ from the reviewed
resolution. Workers validate against the saved record, not a subsequently
updated catalog. Engine snapshots also retain the catalog's Python source.

Pinned-engine capabilities expose `candidate_defaults` and `ess_catalog`.
`POST /api/ess/resolve` uses the pinned worker, not a live catalog. Source
search/detail can also be consumed by a future desktop GUI. Existing schema
1 and 2 studies remain supported. Older engines hide the candidate controls
and reject unsupported requests; they are never automatically upgraded.

Flow: Manual / Select equipment → manufacturer/model → complete-system count →
initial charge/reserve → explicit required assumptions → Review & apply → run.
Published specifications have source links; unresolved requirements block
application. Only supported power derates are editable in equipment mode.

A separate candidate preview can be started without altering the established
study directory or its pin:

```sh
/usr/local/bin/python3 -m src.local_web.server --port 8766 --data-dir .cache/local_web_candidate_ess_v2 --env-file /absolute/path/to/src/.env
```

The current browser at port 8765 is not upgraded by this work. Promote a
candidate only as a separate explicit user action.

## Full-year historical orientation optimization

The PV button requests a chosen historical year (latest available year by
default) at native hourly resolution, independent of the simulation horizon.
It uses the existing NSRDB cache; credentials stay local. Complete Jan 1–Dec 31
coverage for the site/timezone is required. No clear-sky fallback, year shift
or filling is used. `POST /api/solar/optimize` evaluates all 32,760 integer
orientations with batched pvlib calculations and the same model constants as
`profiles.pv_model`. The objective is available AC kWh after conversion and
clipping, without battery dispatch. Exact ties choose lower tilt then azimuth.

The result records year, weather checksum/provenance, model version, inputs,
energy and selected angles in the saved study. Editing PV/location settings
clears the optimization attribution. Highest output for one historical year
is not a multi-year optimum or a guarantee of installation feasibility.

## Validation

Offline tests cover full AC energy delivery and refill, reserve/initial charge,
asymmetric power, scaling errors, missing fields, incompatible efficiency
paths, source retention, catalog changes, manual compatibility, and a real
catalog-backed dispatch/OpenDSS run. Solar tests compare batched calculations
to the existing model, enforce complete annual coverage, and verify integer
search/tie selection. No live provider calls occur in tests.

```sh
/usr/local/bin/python3 -m pytest -q
```
