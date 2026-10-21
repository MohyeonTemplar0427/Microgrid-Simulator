# Visually reviewed PBR-R appendix

Source: aiel8rtpbrr08282025.ashx, PDF page 1, filed August 21, 2025,
effective August 28, 2025, Sheet 8.011. Original PDF SHA-256 is recorded
in manifest.json. Numeric tables are image-only in this PDF. Values below
were read from the rendered table; units are USD unless stated otherwise.

| Component | DS-1 2025 | DS-1 2026 | DS-2 standard secondary 2025 | DS-2 standard secondary 2026 |
|---|---:|---:|---:|---:|
| Customer/month | 6.77 | 7.42 | 18.15 | 22.74 |
| Meter/month | 5.32 | 5.96 | 8.02 | 8.94 |
| Summer delivery/kWh | .07477 | .07811 | .06286 | .06660 |
| Winter initial delivery/kWh | .04376 | .04572 | .03352 | .03551 |
| Winter tail delivery/kWh | .02324 | .02427 | .01717 | .01819 |
| Initial winter block kWh | 800 | 800 | 2000 | 2000 |
| Base uncollectible/month, already included | .48 | .52 | .04 | .05 |
| EDT recovery/kWh | .0012550 | .0012567 | .0012550 | .0012567 |

The 2025 DS-1/standard DS-2 columns were also reviewed in the December 26,
2024 and March 21, 2025 appendices and are identical. Those documents contain
different prospective 2026 columns, superseded by the August 2025 revision.
The optional-demand DS-2 table on page 2 is outside this implementation.

Other visually reviewed historical summaries:

- MAP-R: January–April 2025 12.77%; May–December 2025 12.86%;
  January–March 2026 zero; April–December 2026 .01%.
- EDITA: 2025 -2.19%; 2026 zero.
- CGC/month: DS-1 .16 in 2025, .31 in 2026; DS-2 2.48 in 2025,
  6.30 in 2026. Applies to all customers, not only DER accounts.
- CEAC/kWh: January–May 2025 .00189; June–August 2025 .00177;
  September 2025–May 2026 .00183; June–August 2026 .00175;
  September–October 2026 .00071.
- CSESC/kWh: January–September 2025 .00008; October–December 2025
  .00007; January–March 2026 .00008; April–September 2026 .00009;
  October 2026 .00008. Later overlapping rows supersede earlier ranges.

Monthly BGS tables retain their original cents/kWh in selected text. Runtime
values divide those numbers by 100 exactly once. PEA parentheses mean credit.
The monthly supply EUA column is included separately from non-EUA SCA.
