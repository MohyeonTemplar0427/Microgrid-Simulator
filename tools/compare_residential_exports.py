"""Run a local, identifier-free PG&E residential billing comparison report."""
import argparse
from pathlib import Path
import sys
import html
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.billing.residential_comparison import compare_cycle
from src.billing.baseline import BaselineAllowance,BaselineTerritory,BaselineCode


def read_export(path, expected):
    lines=Path(path).read_text(encoding='utf-8-sig').splitlines()
    start=next((i for i,line in enumerate(lines) if line.startswith(expected)),None)
    if start is None: raise ValueError('Expected PG&E CSV table header not found.')
    return pd.read_csv(path,skiprows=start)


def run(usage_path,bill_path,output,territory):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    u=read_export(usage_path,'TYPE,DATE,START TIME')
    b=read_export(bill_path,'TYPE,START DATE,END DATE')
    rows=[]; excluded=[]
    for _,bill in b.iterrows():
        start,end=bill['START DATE'],bill['END DATE']
        part=u[(u.DATE>=start)&(u.DATE<=end)].copy()
        reason=None
        if start<u.DATE.min() or end>u.DATE.max():reason='Interval file does not cover this billing cycle.'
        if not reason:
            naive=pd.DatetimeIndex(pd.to_datetime(part.DATE+' '+part['START TIME']))
            try:
                idx=naive.tz_localize('America/Los_Angeles',ambiguous='raise',nonexistent='raise')
            except Exception:
                reason='Ambiguous or nonexistent daylight-saving timestamp; source clarification required.'
        observed=float(part['USAGE (kWh)'].sum()); billed=float(bill['USAGE (kWh)'])
        # Half of the reported 0.01 kWh precision per row plus bill rounding.
        if not reason and abs(observed-billed)>len(part)*.005+.005:
            reason='Usage difference exceeds the bound from rounding each exported row to 0.01 kWh.'
        if reason:
            excluded.append(dict(start_date=start,end_date=end,reason=reason,interval_kWh=observed,billed_kWh=billed));continue
        for code in BaselineCode:
            result=compare_cycle(pd.Series(part['USAGE (kWh)'].to_numpy(),index=idx),
                                 BaselineAllowance(BaselineTerritory(territory),code))
            rows.append(dict(start_date=start,end_date=end,baseline=code.value,**result,
                             exported_bill=float(bill.COST.replace('$','')),
                             billed_kWh=billed,usage_difference_kWh=observed-billed,
                             estimated_rows=int(part.NOTES.notna().sum())))
    results=pd.DataFrame(rows);results.to_csv(output/'plan_comparison.csv',index=False)
    pd.DataFrame(excluded).to_csv(output/'excluded_cycles.csv',index=False)
    totals=results.groupby('baseline')[['usage_kWh','e1_subtotal','tou_c_subtotal','tou_c_savings','exported_bill']].sum()
    totals.to_csv(output/'comparison_totals.csv')
    text=f'''# Residential measured-usage comparison

PG&E bundled service; baseline territory {territory} selected for this study (confirm against the account); no CARE, FERA, or Medical Baseline.
Basic and all-electric heating are alternative eligibility scenarios, not an account determination.
No PV, battery, or hypothetical load changes are added; the model replays recorded grid energy.

{totals.round(2).to_string()}

Positive savings means E-TOU-C has lower modeled energy plus base charges.
This covers {len(results)//2} eligible billing cycles, not a complete year.

## Scope

These are energy-plus-base-charge subtotals, not reconstructed final utility bills.
Taxes, climate credits, delivery minimum adjustments, other account adjustments,
and export compensation are excluded. Actual exported bill totals are shown separately
and include unknown components; differences are not model validation errors by themselves.
No hourly export COST is used as a tariff or marginal price.

The study uses actual billing-cycle dates. Baseline allowance accrues by local service day.
When rates change mid-cycle, each rate segment gets its own prorated baseline and usage;
this is a study approximation, not a verified PG&E mid-cycle allocation rule.
The two heating scenarios use the filed quantities for the selected territory.
No eligibility for reduced base services charges based on subsidized housing is assumed.

## Source data exclusions

{pd.DataFrame(excluded).to_string(index=False)}

No missing or ambiguous hourly consumption is invented. Other small usage differences
fall within the arithmetic bound from rounding the exported hourly values to 0.01 kWh;
this does not prove rounding is their cause. Provider-estimated rows remain marked in CSV.

## Rate sources

- https://www.pge.com/tariffs/en/rate-information/electric-rates.html
- https://www.pge.com/tariffs/assets/pdf/adviceletter/ELEC_7846-E.pdf (March 2026 rates)
- https://www.pge.com/tariffs/assets/pdf/adviceletter/ELEC_7921-E.pdf (June climate-credit timing)
- https://www.pge.com/assets/rates/tariffs/res-inclu-tou-current.xlsx (rates cross-check)
- https://www.pge.com/tariffs/assets/pdf/tariffbook/ELEC_PRELIM_A.pdf (territory)

Historical workbook URLs are recorded for each cycle in plan_comparison.csv.
This report does not enable PG&E residential dispatch in the browser.
'''
    (output/'comparison_report.md').write_text(text)
    (output/'comparison_report.html').write_text('<!doctype html><meta charset="utf-8"><title>Residential plan comparison</title><style>body{font:16px system-ui;max-width:1100px;margin:48px auto;color:#173238}table{border-collapse:collapse;width:100%}td,th{padding:10px;border-bottom:1px solid #ccd8d6;text-align:right}pre{white-space:pre-wrap;line-height:1.6}</style><h1>Residential plan comparison</h1>'+totals.round(2).to_html()+ '<h2>Billing cycles</h2>'+results[['start_date','end_date','baseline','e1_subtotal','tou_c_subtotal','tou_c_savings']].round(2).to_html(index=False)+'<h2>Scope and sources</h2><pre>'+html.escape(text)+'</pre>')
    print(totals.round(2).to_string());print('included cycles',len(results)//2,'excluded',len(excluded))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--usage',required=True);p.add_argument('--bills',required=True);p.add_argument('--output',required=True);p.add_argument('--territory',required=True,choices=[x.value for x in BaselineTerritory]);a=p.parse_args()
    run(a.usage,a.bills,a.output,a.territory)
