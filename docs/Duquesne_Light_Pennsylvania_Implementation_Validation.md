# Duquesne Light Pennsylvania implementation validation

Development started October 29, 2026 on clean `main`, HEAD
`ff951e2b01412dcd2be1df2d22282ef5674cd725`. No stage, commit, push, deployment or
stable-engine promotion is authorized. Existing code and evidence are preserved.

Scope: [RS residential and GS non-demand fixed default supply](Duquesne_Light_Pennsylvania.md),
complete January 2025–October 2026 calendar cycles, ordinary state-only taxes,
Company-confirmed history/classification and approved non-export renewable
operation. Low-import GS minimum treatment remains unverified and rejects
outside the documented inactive domain; no missing price or minimum is invented.

Implementation uses a new utility-specific adapter/rate module and existing
regional billing/dispatch, worker, main form, PV/storage and electrical components.
Registry/site/coverage/driver entries are additive. No shared billing math,
solver, time-grid, state engine or replay algorithm is changed.

Targeted acceptance selects Duquesne unit/literal benchmark/integration tests,
affected regional counterfactual/coverage/driver/weather-timezone checks and
changed-JavaScript syntax. One selected new-utility historical matrix covers
full 2025 and June 2026 for both plans. Every selected scenario interval is
checked using existing audits. GUI, unrelated utility matrices, full workflow
and release are excluded by the impact policy: shared engine algorithms and
schema/worker contracts are unchanged. This is targeted acceptance, not a
full-release pass or stable-engine promotion.

Source ledgers, hashes and limitations are under
[utility_sources/duquesne_pa](utility_sources/duquesne_pa/sources.json). Private
development receipts are under `.cache/duquesne_pa/`. Earlier evidence keeps its
original pins and is not relabeled as belonging to this implementation.

## Sources and remaining billing boundaries

All ordinary delivery and fixed-supply components for the declared 22 calendar
months were verified against official tariff/PUC records. Base prices, dated
USC/EEC, explicitly zero SMC/RMES, signed DSIC and STAS, DSS and retail TSC remain
separate. April–December 2025 DSIC continuity is established by the filed revision
chain. The GS June 2025–May 2026 EEC credit is negative, not clamped. TSC is
outside STAS and minimums; GRT/capacity/administration are not duplicated.

Early-2025 supply rates were corroborated by original PUC Supplement83 filing
and acceptance; AppendixA prices by the original Supplement85 table. Original
PUC Supplement86 and its acceptance establish January 1, 2025 STAS, resolving
the utility history's 2024 typo. Original filed tables were rendered and checked.
Some later supply pages were retained through readable primary cached PDFs;
direct utility binary requests returned Incapsula HTML. Their ledgers explicitly
distinguish cached text, actual downloaded binaries and inspected images. No
bot response was accepted as a tariff or hashed as if it were PDF evidence.

GS minimum language remains ambiguous for low-import accounts. The initial
domain requires continuous non-demand GS with no historical GM/priced-demand or
contract-minimum obligation, and current delivery amounts safely above either
possible customer-floor reading. The guard checks base distribution, distribution
including signed riders **before DSIC**, and distribution after DSIC/STAS, with
cent checks. A boundary test prevents positive DSIC from masking a negative EEC
minimum-domain failure. No double-customer charge or demand price is billed;
unsupported cases reject after rebilling without forced purchases. This is a
scope restriction, not a universal GS minimum implementation or a provisional rate.

## Frozen candidate and targeted checks

Engine: `bb18528a7a2b9e0ae8e62d3d267b55297738bda76c988edaef5efb30e1d1f9fe`.
`candidate_frozen_1.json` pins its frontend and source-ledger identity;
`frozen_candidate_1/` retains the immutable development snapshot. The launcher,
matrix, preview and browser result used this same pin. All final source,
frontend and retained excerpt hashes were rechecked.

Final selection passed **306 tests**, no skips/failures: Duquesne unit,
independent literal benchmark and main-form/worker tests, regional counterfactual,
coverage, validation-driver and weather-timezone tests. Pytest phase 20.67 s.
The changed `regional.js` passed `node --check`; Python syntax, diff and local
documentation links also passed. Runtime, tests and frontend bytes remained
unchanged after the freeze; only documentation/evidence was completed afterward.

Checks cover all dated windows, exact units, numeric/symbolic parity, taxes and
percentage bases, source/date bounds, DST, missing/duplicate data, account/native
and carried-history restrictions, missing/unsupported settlement, DER approval,
form serialization, queue/worker and saved settings/CSV/ZIP contracts. An earlier
development run found two assertions caused by a missing explicit empty exclusion
list in the new adapter's result; that contract was corrected and the affected
checks plus final selection passed. Earlier receipts remain separate.

Evidence: `acceptance_1/report.json`, its JUnit/logs and fingerprints; separate
development receipts `unit_rules_1/`, `benchmark_focused_1/`,
`integration_focused_1/` and `annual_scope_fix_1/` are not extra final test counts.

## Historical and electrical acceptance

One matrix passed **4 studies, 12 scenarios, 78 cycle bills and 227,520 OpenDSS
interval checks**, zero electrical failures. Every interval was checked; no
sampling, audit bypass, unaffected utility matrix or old-engine reuse occurred.

| Plan | Period | Grid / PV / PV-plus-battery bills | Electrical intervals | Study ID |
| --- | --- | ---: | ---: | --- |
| RS | Full 2025 | $3,192.96 / $2,278.78 / $1,959.60 | 105,120 | `a46728bb1382445dacc878dafd5a903f` |
| RS | June 2026 | $290.01 / $185.43 / $151.70 | 8,640 | `eca7658d7cae47b28771dbcb942b4ec1` |
| GS | Full 2025 | $2,183.26 / $1,807.20 / $1,798.20 | 105,120 | `75ad52f4102942c8b30e87ff39eb558d` |
| GS | June 2026 | $191.62 / $151.28 / $150.60 | 8,640 | `6d20fda8306947f281fbab6277c1c932` |

Exact-site/year ERA5 inputs were prepared at the hypothetical Beaver County
coordinates, with hourly means held over 15-minute intervals and provider
attribution retained. Generic deterministic native profiles are serialized CSV
inputs, synthetic rather than measured or locally calibrated. GS native months
were 765.50–865.18 kWh, with a 2.5 kW peak, independently below the conservative
class guard. RS uses 5 kW DC/4 kW AC PV and 10 kWh/3 kW storage; GS uses
1.5 kW DC/1.2 kW AC and 2 kWh/0.6 kW. Both retain approved ordinary renewable,
PV-only charging, zero-export and equal final/initial battery energy assumptions.
Representative single-phase electrical service is not a surveyed-site finding.

All **52 optimized cycle primary proofs** and **26 battery-cycle minimum-cycling
proofs** passed, with no strict fallbacks; 26 direct grid-only bills make no
optimizer claim. Maximum objective/rebill reconciliation was about $1.000001e-6
within saved proof tolerances. Annual flags remain false: rolling-cycle perfect
foresight with carried SOC/history is not a jointly optimized annual optimum or
prospective customer savings. Other 2026 boundaries have unit/source checks,
not an all-month electrical replay or a complete actual-weather 2026 claim.

The standalone literal Decimal auditor imports no production rate/billing/math
code and makes no API or simulation calls. It reconciled all 78 cycle bills and
saved itemized/comparison tables, native/dispatch/SOC and every electrical row.
Maximum raw component discrepancy was **$2.842170943040401e-14**. Its 50 file
read/checksum identities are retained in `independent_audit.json`.

The launcher matrix phase took 82.69 s; its matrix session 78.86 s and worker
runtimes 31.30 / 4.78 / 32.38 / 4.59 s are overlapping scopes, not additive CPU
or active-development times. Receipts: `acceptance_1/regional/validation.json`,
`validation-summary.json`, pinned validator copies and study artifacts.

## API and browser acceptance

The preview is separate from the matrix store, retaining copied seed bytes and
the same engine/frontend. Local API audit passed all four studies, **52 CSV
endpoints**, paged table metadata, exact saved bytes and ZIP content/manifests.
Receipt: `api_audit_1.json`. No browser download-event or filechooser route used.

One concise browser pass inspected RS results and restored residential class,
supplier and tax controls. It then inspected GS, restored all settings including
Company/history/minimum assertions, reviewed all eight steps, submitted, viewed
results, saved by name, returned home and reopened. **No operation stalled**.
All **25** request fields other than display name exactly matched the GS seed.
RS was not submitted again in the browser; its queue/matrix evidence is separate.
The optional carbon setting stayed off, and the visible not-calculated status
was checked rather than presented as zero emissions.

Saved result: `b6b9058a714b4cb889bf6a03faff979c`, **Duquesne GS browser acceptance**,
at `http://127.0.0.1:59169/`. Its $191.62 / $151.28 / $150.60 results passed
independent rebilling and **8,640 additional** electrical interval checks,
separate from the matrix count; worker runtime 4.57 s. Receipts:
`browser_acceptance_1.json`, `browser_restoration_1.json`,
`browser_independent_audit_1.json`, `browser_api_audit_1.json`, `browser_GS_1.png`.
The combined HTTP audit of seeds plus browser result covers **65 CSV endpoints**
and matching ZIP bytes. Actual browser download handling remains unasserted.
Browser waits and active-development time were not separately instrumented.

No unverified export/NEM settlement, low-import GS minimum, partial-cycle
allocation, special/local tax, exact printed-invoice/rounded-cash optimization,
site-specific network validation or standalone battery support is claimed.
Existing unrelated utility evidence and stable-engine pins remain unchanged.
All changes remain unstaged/uncommitted; no push, deployment or promotion.
