# PJM regional-average carbon data coverage

Verified October 29, 2026 using the configured Electricity Maps account. This
document records source availability and independent carbon accounting checks;
it is not a billing, dispatch, electrical, browser or release acceptance report.
No account credential or provider data is included in this tracked document.

## Source and accounting boundary

The source is Electricity Maps v4 `carbon-intensity/past-range`, with explicit
zone `US-MIDA-PJM`, `flowTraced=true`, `emissionFactorType=lifecycle`,
`temporalGranularity=15_minutes` and `disableCallerLookup=true`.
The [carbon definition](https://app.electricitymaps.com/docs/reference/carbon-intensity)
specifies **gCO2eq/kWh**. Display derived totals as **kgCO2e**, including when a
legacy internal column retains the name `gCO2/kWh`.

This is a consumption-based PJM regional average, including interregional
electricity flows. It is a location-based accounting proxy, not a utility's
supplier product, an individual site's measured emissions, or marginal emissions
avoided by dispatch. Lifecycle factors include upstream and infrastructure
emissions associated with generation. The [methodology](https://www.electricitymaps.com/data/methodology)
describes mixed upstream reporting frequencies and estimated gap handling;
15-minute API delivery does not establish independently measured 15-minute data.

The [public zone catalogue](https://api.electricitymaps.com/v3/zones) identified
PJM as `TIER_A` with no listed child zones. Utility, supplier, state, transmission
zone and wholesale prices remain separate from this carbon zone.

## Verified historical coverage

Dates below are inclusive **America/New_York** calendar dates. Requests use
half-open UTC bounds derived from those dates. Every returned timestamp was
compared with the complete 15-minute grid: no missing, duplicate, extra or
out-of-order intervals; all intensities were finite and nonnegative. Zone,
factor basis and flow tracing were verified on every row. No application-side
gap filling, interpolation or assumed value was used.

| Period | Exact intervals | Provider-estimated intervals | Provider method for estimated rows | Range (gCO2eq/kWh) |
| --- | ---: | ---: | --- | ---: |
| 2025-01-01–2025-12-31 | 35,040 | 44 | `TIME_SLICER_AVERAGE` | 276–535 |
| 2026-01-01–2026-10-28 | 28,892 | 1,620 | `TIME_SLICER_AVERAGE` | 265–529 |

The combined audit covers **63,932 intervals** across 334 two-calendar-day
or shorter chunks. Estimated rows remain provider estimates even though the
returned series is complete. All estimated rows supplied an estimation method;
the remaining 62,268 rows had `isEstimated=false` and a null method.
The provider flags are not proof of site measurement. Historical values may
later be revised, so this evidence belongs to the preserved response bytes.

Full calendar 2026 coverage is **not verified**. October 29–December 31 is outside
this archive. This does not authorize extrapolation, a constant fallback, or
claims that an unsupported study horizon has complete carbon coverage.

## Private evidence and provenance

All provider responses remain in Git-ignored `.cache/pjm_carbon/coverage/`:

- `coverage-receipt.json`: request parameters, row counts, per-chunk hashes,
  source update bounds and annual coverage summaries.
- `raw/<start>_<end-exclusive>.json`: complete original response payloads.
- `pjm_carbon_2025.csv` and `pjm_carbon_2026.csv`: chronological UTC data retaining
  `zone`, `carbonIntensity`, `datetime`, `createdAt`, `updatedAt`,
  `emissionFactorType`, `flowTraced`, `isEstimated` and `estimationMethod`.
  Additional `timestamp` and `gCO2/kWh` columns provide legacy compatibility.
- `zone-catalogue.json`, `source-ledger.json`, `probe-receipt.json` and
  `independent_2025_audit.json` / `independent_2026_audit.json`.

CSV SHA-256 identities:

```text
2025: 5c0e543457baa5f10648c0653dcfb5cb97675c9390501b65cec91b5f0d6e06aa
2026: c726e7eb07f88e417bb62656ea973bb8c5e715901daf1bd76b9ee87d70dd60a6
```

Independent constant-1-kW import checks use
`sum(import_kW * interval_hours * intensity_gCO2e_per_kWh) / 1000`:

| Period | Import energy (kWh) | Emissions (kgCO2e) | Time-weighted intensity (gCO2e/kWh) |
| --- | ---: | ---: | ---: |
| Full 2025 | 8,760 | 3,589.3095 | 409.73852739726027 |
| Verified 2026 period | 7,223 | 2,966.03625 | 410.63771978402326 |

DST audit counts are 92 intervals on March 9, 2025, 100 on November 2, 2025,
and 92 on March 8, 2026. The November 2026 transition is outside this archive.
These are carbon accounting checks, not additional OpenDSS interval checks.

## Retrieval and use limits

The [historical API reference](https://app.electricitymaps.com/docs/reference/carbon-intensity/past-range)
currently permits up to four days per 15-minute request; this audit retained the
existing client's two-day chunk policy. Retrieval was paced conservatively
after checking the provider's documented default request limit. Saved chunks
were reused instead of downloading them again.

The [March 24, 2026 terms](https://help.electricitymaps.com/en/articles/11750446-terms-of-service)
make external data availability dependent on the subscription and require
attribution when permitted. Account-specific redistribution rights were not
verified. Keep this archive and its derived study artifacts local; this source
check does not authorize hosted publication or redistribution.
