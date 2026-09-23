# LA County expansion handoff — 2026-09-20

## Status

**Partial implementation. The overall requested expansion is not complete.**
Glendale's five existing ordinary import plans are joined by nine plans: PWP R-1/R-2/S-1 legacy flat, BWP Basic/EV/C, ALW D/G-1, IPU D. These are connected to billing, dispatch, account eligibility, location/site-type filtering and the existing browser wizard. See [coverage matrix and source ledger](LA_County_Utilities.md) for exact date windows and exclusions.

Remaining source gaps: matching actual Vernon ECA/renewable adjustments and taxes, Industry commercial season/contract rules (posted general rules are draft), Cerritos accepted generation-agreement terms and complete SCE unbundled/CCA rider combinations. Remaining implementation is distinct: PWP TOU/CPP/demand/PF, BWP kVA demand, ALW G-2/GL/TOU/ratchets/reactive charges, partial-service proration and assistance. Official tables exist for several of those; they must not be described as wholly unavailable data. Solar export settlement is explicitly deferred by the user until utility-region coverage is finished.

## Repository and preview

Work is directly in `/Users/junhayang/Desktop/EnergyEngineerSession/Microgrid_Simulator`, branch `main`. Pre-existing SCE history/refinement changes were preserved. Nothing staged, committed or pushed. The independent `Microgrid_Web_Browser` clone was not changed.

- Tariff registry: `socal-2026-09-20.1`; new municipal modules each `2026-09-20.1`.
- Candidate port 8879, data `.cache/la_county_candidate`; four new successful browser studies retained there.
- Main preview port 8876, data `/tmp/microgrid-municipal-browser-review`.
- Validated/promoted engine: `f4a65114b24ed2775ac4e9ca4f62956ecc97893e8eca5e85eb2fd63752349d43`.
- Previous main engine: `a85efaef54fb1638d920a3e311c02a0cf193728e82f0ccd9fbbd3306073312ac`; backup pointer `engine-before-municipal-expansion.json`.
- The exact validated immutable candidate was copied and hash-verified before changing the stopped main server's pointer. A fresh checkout snapshot was deliberately not made because concurrent residential-profile development continued after candidate testing. The normal server startup verified the promoted snapshot and dependencies.
- Main health returned ready/worker connected/zero queued or running. Existing SF study `95c1f1eb32ce415e9dd20c432c8c2b7c` result still returned HTTP 200 after promotion. Old engines and studies were retained.
- Static assets follow the existing server mechanism; capability-based activation disables unsupported controls against older pins. Research coverage metadata comes from the pinned backend.
- Unrelated residential/Fresno/Alameda changes and outputs were preserved. Nothing staged, committed or pushed; the independent browser clone was not changed.

## Validation

`/usr/local/bin/python3 -m pytest -q`: **1,238 passed** in 63.63 seconds. Initial sandbox execution aborted during native Tk initialization; rerunning outside that sandbox passed the full suite. New PWP plus municipal expansion tests: **28 passed**. Combined LA County/PWP/municipal expansion suite: **58 passed**. JavaScript syntax check passed. Later changes were documentation/source artifacts and promotion, not billing code. Concurrent unrelated development means this count describes the tested checkout at that time, not every subsequent profile edit.

New tests cover independent itemized bills, PWP monthly/bimonthly factors and SLATS/underground taxes, ALW minimum/declining tiers and independent rider windows, BWP tax bases/TOU/holiday boundaries, IPU DST daily charges, missing qualification and unsupported dates, physical battery balance and bill/objective reconciliation. Billing and dispatch share cost expressions. Flat no-PV tariffs have an analytic idle-storage optimum; BWP TOU uses the shared solver. No anonymized customer bills were supplied for these new utilities; fixtures are synthetic and explicitly hypothetical.

### September 20 actual browser runs — promoted engine

All runs used 15-minute Pacific timestamps, July 1–31, 2026 inclusive, a constant 1 kW load (744 kWh), residential house, bundled generation and explicitly hypothetical account eligibility. No PV/export. Complete one-month billing cycle. Settings were restored between runs and changed through the existing wizard.

| Utility / study ID | Coordinates | Account inputs | Grid-only bill |
|---|---|---|---:|
| PWP `e4d1e85d7f334098b76598fe2adabb65` | 34.1478, -118.1445 | R-1 legacy flat, secondary single-phase, 7.67% UUT, flat enrollment confirmed | $211.3504 |
| ALW `1e686959a7314426a2d02e811d9e1a5e` | 34.1336, -117.9076 | D ordinary meter, secondary single-phase, 4% UUT | $147.8207 |
| BWP `1533b780a87e4a349bb7b50eaaebdb34` | 34.1808, -118.3090 | EV TOU, medium service size, 7% UUT, .034 ECAC and enrollment confirmed | $211.29135 |
| IPU `76f6b028c0e542378d806ac28a050291` | 34.0197, -117.9728 | Individual single-family D, ordinary contract confirmed, 0% local UUT | $84.6486 |

PWP independent subtotal: `17.5 + 350*.03505 + 394*.14018 + 744*(.10825+.01609)`; total `subtotal*1.1201 + (subtotal-744*.10825)*.0743 + 744*.00715`.
ALW: `(250*.1091+494*.1487+744*(.05+.00536))*1.04+744*.0003`.
IPU: `31*.033+744*(.10882+.00328+.0003)`.

BWP also used a 10 kWh battery, initial/final 5 kWh, SOC .2–.8, charge/discharge limits 3 kW, each efficiency .95, wear .01 per kWh charge+discharge throughput. Optimized bill **187.840995694**, wear **2.760627632**, operating total **190.601623326**, savings **20.689726674**. Independent July counts: 69 on-peak hours, 276 mid, 399 off. Internal cycling is `22*6+5.85=137.85` kWh; the final day's 23:00–24:00 recharge limit restricts its cycle to 5.85. Independently calculated avoided import costs, incremental losses, taxes and wear match the browser result. Capital costs are excluded.

Real CEC lookups preserved PWP/BWP overlaps and SCE/IPU boundary ambiguity. Hypothetical selection did not assert actual enrollment. A browser attempt to run IPU July 2024 returned the explicit coverage error before job submission, retaining the prior completed result. Saved settings restored successfully. Browser console reported no warnings/errors during the successful new runs.

The successful generation-provider combination is still **outstanding**: CCA/CEU remain disabled rather than generating unsupported bills. Previous unsupported SCE/CCA browser checks are recorded below.

### September 19 browser runs — previous engine

1. `87191e384e39453aad68f90cb380e6bd` on candidate 8879, initial candidate engine `ed1174771ded744b5a92df222f9db9f9490522ec4bf00fdf5aa13997e7f2e720`:
   - Synthetic Glendale residence, coordinates 34.1425, -118.2551, July 1–31, 2026 inclusive, 15 minutes/Pacific.
   - L-1-A, 1 kW constant load = 744 kWh, secondary/single phase, 7% Glendale tax; no PV/battery. Hypothetical account, not a claim of actual customer eligibility.
   - Bill **$322.469925801000** (browser rounds $322.4699; verify full-precision CSV if needed).
   - Independent formula `(31*.75 + 310*.3071 + 310*.3806 + 124*.4547)*1.0285*1.07 + 744*.0003`.
   - Saved settings restored coordinates, tariff, tax and account confirmations; old result remained readable after candidate refresh.

2. `9229c5cb3845401bbe9a5d49d7653ed8` on final candidate engine:
   - Same synthetic residence, dates, 1 kW load, tax and no PV; L-1-B.
   - Battery 10 kWh, initial/final 5 kWh, SOC .2–.8, max charge/discharge 3 kW, each efficiency .95, degradation $.01 per kWh of charge plus discharge throughput.
   - Baseline **$281.725639119**; storage explicit operating cost **$222.272313697** (bill about $219.5087 plus wear $2.7636), savings **$59.453325422**.
   - Independent analytic fixture: 23 peak weekdays, 138 peak hours and 606 base hours. Each daily cycle delivers 5.7 kWh using 6/.95 kWh charging; apply the same public-benefit/tax multipliers, incremental state surcharge and throughput wear. Matches the browser result.

3. Real CEC browser lookup at 33.86, -118.08:
   - Preserved SCE plus Metropolitan Water District ambiguity; CEU displayed as a disabled generation option with participation/storage and missing-billing explanation, not delivery.
   - Selecting SCE + actual CCA generation blocked advancement with an explicit unsupported-billing message. No synthetic CCA bill was produced.

These checks validate GWP and unsupported-pair behavior; they do **not** satisfy the requested successful simulation of a newly implemented CCA/CEU bill. That remains outstanding. Those September 19 checks predate the four newly enabled providers verified above; Vernon remains disabled.

## Next implementation work

1. Extend PWP beyond confirmed legacy flat accounts: interval-meter TOU/CPP, exact demand rounding/history and PF treatment shared by bill/optimizer.
2. BWP demand schedules require kVA/apparent-power modeling and history, not relabeling active kW. Retrieve historical ECAC/rule windows separately.
3. ALW G-2/GL/TOU need declining-block, rounded-demand/ratchet and reactive-charge optimization. Retrieve missing 2025H2 PCA. Implement rider-crossing allocation only after its governing rule is verified.
4. Vernon: use the now-working official PrimeGov archive and filed schedule links; missing complete dated ECA/renewable records remain the blocker. Industry: verify binding commercial season/contract rules, not draft general rules.
5. CEU: accepted agreement generation coefficients plus SCE delivery and separate bills. CCAs: complete SCE unbundled delivery and PCIA/GMS/CCA-CRS before enabling CPA and remaining providers.
6. Repeat independent fixtures, actual browser runs and candidate promotion per newly enabled scope. Do not confuse working limited plans with full LA coverage. Keep export settlement deferred.
