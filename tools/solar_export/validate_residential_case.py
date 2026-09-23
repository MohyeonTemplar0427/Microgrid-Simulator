"""Deterministic residential case with source-CSV, independent bill checks.

Run: /usr/local/bin/python3 -m tools.solar_export.validate_residential_case
Requires the official downloaded CSV in .cache/solar_export; no live API calls.
This validates billing/dispatch, not the accuracy of the synthetic load/PV.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from src.billing import pge_export
from src.billing.export_settlement import CreditBalance
from src.billing.pge_true_up import TrueUpRates, reconcile_nbt
from src.dispatch.solar_export import compare


def main():
    out = Path('.cache/pge_residential_validation_2026_07')
    out.mkdir(parents=True, exist_ok=True)
    source = Path('.cache/solar_export/PG&E NBT EEC Values 2026 Vintage.csv')
    raw = pd.read_csv(source, encoding='utf-8-sig')
    raw['instant'] = pd.to_datetime(raw.DateStart+' '+raw.TimeStart, utc=True)
    index = pd.date_range('2026-07-01', '2026-08-01', inclusive='left', freq='15min', tz='America/Los_Angeles')
    hours = index.hour.to_numpy()+index.minute.to_numpy()/60
    load = .3 + .65*np.exp(-((hours-7)/1.4)**2) + 1.1*np.exp(-((hours-19)/2.2)**2)
    load *= 450/(load.sum()*.25)
    pv = 3*np.maximum(0, np.sin(np.pi*(hours-6)/12))
    frame = pd.DataFrame(dict(timestamp=index, native_load_kw=load, pv_available_kw=pv))
    frame.to_csv(out/'inputs.csv', index=False)
    account = dict(utility='pge', generation_provider='pge', customer_class='residential', billing_plan='E-ELEC', program='NBT', income_tier=3,
        enrollment_confirmed=True, ordinary_account_confirmed=True, cycle_confirmed=True, no_local_tax_confirmed=True,
        no_other_adjustments_confirmed=True, reference='Hypothetical validation case; not a customer account', application_year=2026,
        pto_date='2026-04-01', bonus_eligible_confirmed=True, cycle_start='2026-07-01', cycle_end='2026-07-31',
        next_true_up_date='2027-04-01', storage='renewable_only')
    battery = dict(capacity_kWh=10, energy_kWh=2, SOC_min=.2, SOC_max=.9, max_charge_kw=3, max_discharge_kw=3,
                   charge_efficiency=.95, discharge_efficiency=.95)
    results = compare(frame, account, export_limit_kw=3, battery=battery, wear_per_kwh=.01)
    # Independent lookup from source CSV, not the generated runtime table.
    hourly = index.tz_convert('UTC').floor('h')
    export_prices = {}
    for key, prefix in [('generation','USCA-XXPG'),('delivery','USCA-PGXX')]:
        rows = raw.loc[raw.RIN.str.startswith(prefix)].set_index('instant')
        assert rows.index.is_unique
        export_prices[key] = rows.Value.reindex(hourly).to_numpy()
        assert np.isfinite(export_prices[key]).all()
    # Filed E-ELEC summer components; no production rate/bill helper in oracle.
    peak = (hours>=16)&(hours<21)
    shoulder = ((hours>=15)&(hours<16))|(hours>=21)
    total_price = np.where(peak,.55214,np.where(shoulder,.39026,.33358))
    gen_price = np.where(peak,.26299,np.where(shoulder,.16388,.11878))
    nbc = .01230
    def oracle(d):
        imports=d.grid_import_kw.to_numpy()*.25; exports=d.grid_export_kw.to_numpy()*.25
        charges={'generation':float(imports@gen_price),'delivery':float(imports@(total_price-gen_price-nbc)),
                 'protected':float(imports.sum()*(nbc+.0003)+31*.79343)}
        earned={k:float(exports@v) for k,v in export_prices.items()};earned['bonus']=float(exports.sum()*.0088)
        used={k:min(charges[k],earned[k]) for k in ('generation','delivery')}
        rest=sum(charges.values())-sum(used.values());used['bonus']=min(rest,earned['bonus'])
        return charges,earned,used,{k:earned[k]-used[k] for k in earned},rest-used['bonus']
    rows=[];checks=[]
    for name,r in results.items():
        d=r['dispatch'];d.to_csv(out/(name+'.csv'),index=False)
        charges,earned,used,closing,due=oracle(d)
        comparisons=[abs(due-r['bill']['amount_due'])]
        for group,expected in [('import_charges',charges),('credits_earned',earned),('credits_used',used),('closing_balance',closing)]:
            comparisons.extend(abs(value-r['bill'][group][key]) for key,value in expected.items())
        gap=max(comparisons);assert gap<1e-7,(name,gap)
        balance=d.grid_import_kw+d.pv_output_kw+d.battery_discharge_kw-d.native_load_kw-d.battery_charge_kw-d.grid_export_kw
        assert abs(balance).max()<1e-5
        assert np.minimum(d.grid_import_kw,d.grid_export_kw).max()<1e-6
        assert d.grid_export_kw.max()<=3+1e-6
        assert np.minimum(d.battery_charge_kw,d.battery_discharge_kw).max()<1e-6
        if name.startswith('storage'):
            ending=d.energy_kWh.iloc[-1]+.25*(d.battery_charge_kw.iloc[-1]*.95-d.battery_discharge_kw.iloc[-1]/.95)
            assert abs(ending-2)<1e-5
            assert d.energy_kWh.min()>=2-1e-5 and d.energy_kWh.max()<=9+1e-5
            assert (d.battery_charge_kw-d.pv_output_kw).max()<1e-6
        rows.append(dict(scenario=name,imports_kwh=r['bill']['import_kwh'],exports_kwh=r['bill']['export_kwh'],
            bill_due=due,credits_earned=sum(earned.values()),credits_used=sum(used.values()),closing_credit=sum(closing.values()),
            battery_wear=r['degradation_cost'],operating_cost=r['operating_cost'],independent_bill_error=gap))
        checks.append({'scenario':name,'independent_bill_error':gap,'power_balance_error_kw':float(abs(balance).max()),'objective_gap':r['objective_gap']})
    assert results['storage_with_export']['operating_cost']<=results['storage_self_consumption']['operating_cost']+.02
    assert results['storage_with_export']['operating_cost']<=results['pv_with_export']['operating_cost']+.02
    # A large restricted opening bank cannot offset fixed/NBC/state charges.
    grid=results['grid_only']['dispatch']
    stress=pge_export.bill(grid,account,CreditBalance(10000,10000,0))
    protected=450*.0126+31*.79343
    assert abs(stress['amount_due']-protected)<1e-7
    # Published annual statement example; separate from this monthly case.
    annual=json.loads(Path('docs/utility_sources/solar_export/pge_nbt_true_up_example.json').read_text())
    annual['bank']=CreditBalance(**annual['bank']);annual['rates']=TrueUpRates(**annual['rates'])
    trueup=reconcile_nbt(**annual)
    assert abs(trueup['adjustment_if_all_bonus_applied']+66.35)<1e-8
    summary=pd.DataFrame(rows);summary.to_csv(out/'comparison.csv',index=False)
    (out/'validation.json').write_text(json.dumps(dict(checks=checks,restricted_credit_stress_bill=stress['amount_due'],
        true_up=trueup,account=account,battery=battery,load_kwh=float(load.sum()*.25),pv_available_kwh=float(pv.sum()*.25),
        csv_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        source_code_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path('src/billing/pge_export.py'),Path('src/billing/export_settlement.py'),Path('src/dispatch/solar_export.py'),Path('src/billing/pge_true_up.py')]}),indent=2))
    table='| Configuration | Import kWh | Export kWh | Bill due | Wear | Operating cost |\n|---|---:|---:|---:|---:|---:|\n'
    for r in rows:table+=f"| {r['scenario'].replace('_',' ')} | {r['imports_kwh']:.2f} | {r['exports_kwh']:.2f} | ${r['bill_due']:.2f} | ${r['battery_wear']:.2f} | ${r['operating_cost']:.2f} |\n"
    (out/'report.md').write_text('# PG&E residential solar billing validation\n\nPASS: all five cases reconcile independently to within $0.0000001.\n\n'
        'July 1–31, 2026, Pacific time, 15-minute intervals. Hypothetical bundled PG&E E-ELEC/NBT household, ordinary income tier, 2026 application vintage and no local taxes/other adjustments. Zero opening credit balances.\n\n'
        f'Load: 450 kWh, synthetic morning/evening peaks. PV: 3 kW peak AC sine profile from 06:00–18:00, {pv.sum()*.25:.2f} kWh available. This is a controlled billing fixture, not measured usage or weather-derived solar.\n\n'
        'Battery: 10 kWh nominal, 20–90% SOC (7 kWh usable), 3 kW power, 95% each-way efficiency, cyclic 2 kWh initial/final energy. Solar-only charging; $0.01/kWh throughput wear on both charge and discharge. Export limit 3 kW.\n\n'+table+
        f'\nAdditional credit-restriction check: $10,000 generation plus $10,000 delivery opening credits leave ${protected:.5f} due for protected charges with no bonus credit.\n\n'
        'Independent checks read the official hourly export CSV directly and use filed import components, rather than calling the production billing function. Checks include each credit bucket, power balance, export limits, charge/discharge exclusivity, SOC and optimizer/bill reconciliation.\n\n'
        'Separate annual check: PG&E published hypothetical statement reproduces -$66.35. This is not the annual result for the simulated house.\n\n'
        'Scope: monthly cash-cost optimization, unused credits have no assumed terminal value; excludes capital costs, annual dispatch, NEM/NEM2, tax adjustments and electrical-network validation. No actual customer invoice reconciliation is claimed.\n')
    print(summary.to_string(index=False));print('PASS; report:',out/'report.md')


if __name__=='__main__':main()
