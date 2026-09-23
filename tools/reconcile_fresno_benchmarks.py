"""Offline comparison of Fresno model stock and local electricity accounting.

Does not apply a calibration. Run the expanded study first. Public inputs and
explicitly transcribed ACS counts retain source provenance below.
"""
from pathlib import Path
import argparse
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.run_fresno_residential_study import CACHE, ROOT, TOTAL, NET, sha, pd, np

CEC_DOC = 'https://www.energy.ca.gov/data-reports/energy-almanac/california-electricity-data/california-energy-consumption-dashboards-0'
ACS_URL = 'https://labormarketinfo.edd.ca.gov/file/Census2018/fresndp2018.pdf'


def compare_annual(county, cec_gwh, housing_units):
    """Keep source accounting separate; diagnostic ratios are not calibrations."""
    if housing_units <= 0 or cec_gwh <= 0:
        raise ValueError('Positive population and consumption required')
    weight = county.weight
    return [dict(basis=label, mean_kwh_per_model_dwelling=float(np.average(county[col], weights=weight)),
                 model_gwh=float((county[col]*weight).sum()/1e6),
                 model_gwh_at_external_housing_count=float(np.average(county[col], weights=weight)*housing_units/1e6),
                 cec_to_model_ratio=float(cec_gwh/((county[col]*weight).sum()/1e6)))
            for label, col in [('gross_before_pv', TOTAL), ('signed_net_after_modeled_pv', NET)]]


def run(output):
    expanded = json.loads((output/'study_summary.json').read_text())
    if expanded.get('population_basis', 'all_housing_units') != 'all_housing_units':
        raise ValueError('County-total reconciliation requires all housing units; occupied-only calibration needs an occupied-home benchmark.')
    pilot = json.loads((ROOT/'results/residential_fresno_pilot/study_summary.json').read_text())
    metadata = pd.read_parquet(CACHE/'metadata.parquet')
    county = metadata[(metadata['in.county']=='G0600190') & (metadata.completed_status=='Success')]
    cec = pd.read_csv(output/'cec_county_residential_context.csv')
    annual = cec.groupby('YEAR').GWH.sum()
    if len(cec[cec.YEAR==2018]) != 12 or cec[cec.YEAR==2018].MONTH.nunique() != 12:
        raise ValueError('Expected exactly twelve CEC months')
    # Source DP04, page 6. Five-year estimates are a cross-check, not an exact
    # single-year customer/dwelling denominator or calibration target.
    acs = dict(total_housing_units=328577, occupied_housing_units=304624, vacant_housing_units=23953,
               period='2014–2018 ACS five-year estimates', source=ACS_URL, page=6,
               source_sha256=sha(CACHE/'fresno_acs_2018.pdf'))
    comparison = compare_annual(county, float(annual.loc[2018]), acs['total_housing_units'])
    pd.DataFrame(comparison).to_csv(output/'annual_benchmark_comparison.csv',index=False)
    sampling = [{k:s[k] for k in ['sample_models','sample_mean_kwh','full_county_mean_kwh','sample_discrepancy_pct','sampling_standard_error_kwh']} for s in [pilot,expanded]]
    pd.DataFrame(sampling).to_csv(output/'sample_expansion_comparison.csv',index=False)
    occupancy = county.groupby('in.vacancy_status').weight.sum().to_dict()
    result = dict(cec_2018_residential_gwh=float(annual.loc[2018]), cec_2024_residential_gwh=float(annual.loc[2024]),
        cec_documentation=CEC_DOC, acs_cross_check=acs, model_represented_units_by_occupancy=occupancy,
        annual_comparison=comparison, sampling_comparison=sampling, calibration_applied=False,
        calibration_status='Not eligible: county-export self-generation coverage and matched-year housing denominator require confirmation',
        signed_net_is_grid_import=False,
        reason='Signed net subtracts all modeled PV, including possible exports; it is not the sum of positive grid imports.')
    (output/'benchmark_reconciliation.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    gross, net = comparison
    report = f'''# Fresno benchmark reconciliation and expanded sample

## Sample expansion

The design was fixed at 256 models before examining their annual energy.
It uses the same seed, dwelling-type/cooling strata and expansion-weight rule
as the 64-model pilot. It is a new stratified draw, not a nested extension.

| Models | Annual kWh per represented housing unit | Difference from all 1,328 models | Estimated sampling SE, kWh |
|---|---:|---:|---:|
'''+ '\n'.join(f"| {s['sample_models']} | {s['sample_mean_kwh']:.1f} | {s['sample_discrepancy_pct']:+.2f}% | {s['sampling_standard_error_kwh']:.1f} |" for s in sampling)+f'''

The SE describes annual-energy sampling uncertainty, not weather-response,
peak-load or building-model uncertainty. These profiles represent all housing
units, including vacant units; “per home” does not mean per occupied household.

## Local benchmark accounting

CEC reports **{annual.loc[2018]:,.1f} GWh** for Fresno residential consumption in
2018 and **{annual.loc[2024]:,.1f} GWh** in 2024. Compare the 2018 stock/weather
model with 2018; the 2024 county total is context, not a target for fixed-2018
stock scenarios. Customer growth, electrification and equipment changes are
not weather effects.

| Full county model basis | Modeled 2018 GWh | CEC / model ratio (diagnostic only) |
|---|---:|---:|
| Gross demand before PV | {gross['model_gwh']:,.1f} | {gross['cec_to_model_ratio']:.4f} |
| Signed net after modeled PV | {net['model_gwh']:,.1f} | {net['cec_to_model_ratio']:.4f} |

[CEC documentation]({CEC_DOC}) defines total consumption as retail sales,
non-retail consumption and self-generation, while its QFER sales component is
net of PV. The downloaded county workbook has only sector/month/GWh fields;
it does not separately identify residential self-generation or PV exports.
**Do not automatically add rooftop PV to this consumption total.** Equally,
the label alone does not establish which distributed-generation components
are included in each county/sector row. The two model bases above expose the
sensitivity; they are not asserted to bracket a known ground truth.

Signed net demand is not purchased electricity: annual PV subtraction includes
exports, while positive grid imports require interval-level accounting.
No CEC-to-model ratio above has been applied to the hourly profiles.

## Housing denominator

[California EDD's Census DP04 reproduction]({ACS_URL}), page 6, reports
**328,577 total housing units**, **304,624 occupied** and **23,953 vacant** for
2014–2018. ResStock weights represent **{county.weight.sum():,.0f} total units**,
including **{occupancy.get('Vacant',0):,.0f} vacant**. The total-count difference
is **{100*(county.weight.sum()/acs['total_housing_units']-1):+.2f}%**. This is a
five-year estimate, not a single-year account count. It cannot be substituted
silently for 2018 utility customers.

As a denominator sensitivity only, gross model energy at the ACS total housing
count would be **{gross['model_gwh_at_external_housing_count']:,.1f} GWh**.
Changing housing count alone does not remove the consumption discrepancy.
Dividing the whole county energy total by occupied households would also
attribute vacant-unit consumption to occupied households.

## Calibration decision

**Retain uncalibrated profiles.** The larger sample addresses sampling error;
it does not resolve the remaining difference from local consumption statistics.
Before setting absolute regional demand, confirm the county residential export's
self-generation/PV accounting and obtain a matched-year housing stock or a
meter-to-dwelling mapping. Then align the model's gross or grid-import boundary
with that benchmark. A county total cannot uniquely identify end-use scaling
factors; EIA state shares are context, not Fresno-specific targets.

The Census API returned a key-required HTML response, so no API counts were
used. The independently retrieved EDD PDF is hashed in benchmark_reconciliation.json.

## Reproduce

```bash
python3 tools/run_fresno_residential_study.py --sample-size 256 --download --output results/residential_fresno_expanded
python3 tools/reconcile_fresno_benchmarks.py
```

The reconciliation also requires the EDD PDF cached as
.cache/residential_fresno/fresno_acs_2018.pdf (source linked above).
'''
    (output/'benchmark_reconciliation.md').write_text(report)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'results/residential_fresno_expanded')
    run(parser.parse_args().output)
