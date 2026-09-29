"""Exercise the production SoCal form request builder through HTTP and the worker."""
import json
import subprocess
from pathlib import Path

import pytest

from src.local_web.runtime import JobRunner
from test_local_web_pipeline import api_service, until
from test_socal import study_request


FORM_SCRIPT = Path(__file__).resolve().parents[1] / 'src/local_web/static/socal.js'
NODE_DRIVER = """
const fs = require('node:fs');
const {buildSocalRequest} = require(process.argv[1]);
const data = JSON.parse(fs.readFileSync(0, 'utf8'));
const field = name => ({value: data.values[name] ?? '', checked: !!data.checks[name]});
const request = buildSocalRequest({
  field, siteCustomerClass: () => 'residential',
  siteProfile: () => ({site_type: 'residential', subtype: 'house'}),
  gridOnly: () => false, capabilities: data.capabilities,
  savedResolution: {resolution_id: data.resolution_id},
  loadCsv: null, climateCreditVisible: true,
});
process.stdout.write(JSON.stringify(request));
"""


def browser_payload(capabilities, resolution_id, program, start_date, *,
                    end_date=None, value_overrides=None, check_overrides=None):
    values = {
        'name': f'Synthetic {program} browser submission',
        'utility': 'sce', 'pv_choice': 'yes',
        'start_date': start_date, 'end_date': end_date or start_date,
        'degradation_cost_per_kWh': '0',
        'sc_generation': 'bundled', 'sc_tariff_id': 'sce_tou-d-prime',
        'sc_solar_program': program, 'sc_reference': 'Synthetic SCE account',
        'sc_mode': 'hypothetical_bundled', 'sc_voltage': 'secondary',
        'sc_phase': 'single', 'sc_local_tax_percent': '0',
        'sc_month_factor': str(1 / 30),
        'sc_pv_kw': '5', 'sc_tilt': '20', 'sc_azimuth': '180',
        'sc_nbt_vintage': '2023',
        'sc_nbt_interconnection_request_date': '2023-05-01',
        'sc_nbt_pto_date': '2023-06-01',
        'sc_nbt_bonus_status': 'eligible_non_equity',
        'sc_nbt_opening_delivery_eec': '1',
        'sc_nbt_opening_generation_eec': '2',
        'sc_nbt_opening_acc_plus': '3',
        'sc_nbt_relevant_period_end': '2025-08-01',
        'sc_sce_nem_version': 'nem2',
        'sc_sce_nem_request_date': '2022-05-01',
        'sc_sce_nem_pto_date': '2022-06-01',
        'sc_sce_nem_relevant_period_end': '2026-08-01',
        'sc_sce_nem_opening_energy_credit': '2.50',
        'sc_temperature_zone': '1', 'sc_baseline_region': '6',
        'sc_baseline_type': 'basic', 'sc_prime_qualification': 'battery',
        'sc_pac_tier': '1', 'sc_annual_average_kwh': '500',
        'sc_load_mode': 'daily_peak', 'sc_base_kw': '1', 'sc_peak_kw': '2',
        'sc_peak_start_hour': '16', 'sc_peak_end_hour': '21',
    }
    checks = {f'sc_{name}': True for name in (
        'eligibility_confirmed', 'ordinary_account_confirmed',
        'cycle_confirmed', 'tax_confirmed', 'region_confirmed',
        'interconnection_confirmed', 'nbt_opening_balances_confirmed',
        'nbt_bonus_confirmed', 'sce_nem_legacy_confirmed',
        'sce_nem_credit_confirmed',
    )}
    values.update(value_overrides or {})
    checks.update(check_overrides or {})
    fixture = dict(values=values, checks=checks, capabilities=capabilities,
                   resolution_id=resolution_id)
    result = subprocess.run(['node', '-e', NODE_DRIVER, str(FORM_SCRIPT)],
                            input=json.dumps(fixture), text=True,
                            capture_output=True, check=True)
    return json.loads(result.stdout)


@pytest.mark.parametrize('program,start_date', [
    ('sce_nbt', '2025-07-07'),
    ('sce_nem', '2026-07-06'),
])
def test_sce_solar_form_submission_reaches_saved_worker_result(
        tmp_path, program, start_date):
    resolution = study_request('sce')['resolution']
    resolution_id = 'a' * 32
    source = tmp_path / 'candidate' / resolution_id
    source.mkdir(parents=True)
    (source / 'resource-request.json').write_text(
        json.dumps({'kind': 'utility-resolution'}))
    (source / 'resource.json').write_text(json.dumps(resolution))

    with api_service(tmp_path) as (app, call):
        caps = call('/api/capabilities')[1]
        payload = browser_payload(caps, resolution_id, program, start_date)
        assert payload['solar']['capacity_kw'] == 5
        assert payload['battery'] is None
        assert payload['account']['solar_program'] == program
        if program == 'sce_nbt':
            assert payload['account']['nbt_vintage'] == '2023'
            assert payload['account']['nbt_opening_delivery_eec'] == 1
            assert payload['account']['nbt_opening_generation_eec'] == 2
            assert payload['account']['nbt_opening_acc_plus'] == 3
            assert payload['account']['nbt_relevant_period_end'] == '2025-08-01'
        else:
            assert payload['account']['sce_nem_version'] == 'nem2'
            assert payload['account']['sce_nem_opening_energy_credit'] == 2.5
            assert payload['account']['sce_nem_billing_option'] == 'monthly'

        code, job = call('/api/v1/socal/studies', payload, caps['token'])
        assert code == 202
        runner = JobRunner(app.store)
        try:
            saved = until(lambda: call('/api/studies/' + job['id'])[1],
                          lambda value: value['status'] in ('completed', 'failed'))
            assert saved['status'] == 'completed', saved.get('error')
            assert saved['request']['account'] == payload['account']
            assert saved['request']['battery'] is None
            assert any(t['id'] == 'solar_credit_ledger'
                       for t in saved['result']['tables'])
            ledger = call('/api/studies/' + job['id']
                          + '/tables/solar_credit_ledger')[1]
            rows = [dict(zip(ledger['columns'], row))
                    for row in ledger['data']]
            pv_ledger = {row['component']: row['amount'] for row in rows
                         if row['scenario'] == 'pv_only'}
            opening = ('opening_delivery_eec' if program == 'sce_nbt'
                       else 'opening_energy_credit')
            assert pv_ledger[opening] == (1 if program == 'sce_nbt' else 2.5)
            comparison = call('/api/studies/' + job['id']
                              + '/tables/comparison')[1]
            scenarios = {row['scenario']: row for row in
                         (dict(zip(comparison['columns'], values))
                          for values in comparison['data'])}
            assert set(scenarios) == {'grid_only', 'pv_only'}
            assert scenarios['pv_only']['utility_bill'] < scenarios['grid_only']['utility_bill']
        finally:
            runner.close()


def test_bwp_solar_form_submission_reaches_saved_worker_result(tmp_path):
    from test_socal import study_request
    resolution = study_request('sce')['resolution']
    resolution['delivery_utility'] = 'bwp'
    resolution['delivery_candidates'] = [{'utility_id': 'bwp'}]
    resolution_id = 'b' * 32
    source = tmp_path / 'candidate' / resolution_id
    source.mkdir(parents=True)
    (source / 'resource-request.json').write_text(
        json.dumps({'kind': 'utility-resolution'}))
    (source / 'resource.json').write_text(json.dumps(resolution))
    overrides = dict(utility='bwp', sc_tariff_id='bwp_ev',
                     sc_reference='Synthetic BWP EV solar account',
                     sc_local_tax_percent='7', sc_month_factor='1',
                     sc_bwp_service_size='medium',
                     sc_bwp_solar_capacity_kw='4',
                     sc_bwp_permit_issue_date='2026-02-01',
                     sc_bwp_upgrade_date='', sc_bwp_account_transfer_date='',
                     sc_bwp_opening_credit='10')
    checks = {f'sc_{name}': True for name in (
        'bwp_ecac_confirmed', 'bwp_ev_confirmed',
        'bwp_opening_balance_confirmed')}
    with api_service(tmp_path) as (app, call):
        caps = call('/api/capabilities')[1]
        payload = browser_payload(caps, resolution_id, 'bwp_net_billing',
                                  '2026-07-01', end_date='2026-07-25',
                                  value_overrides=overrides,
                                  check_overrides=checks)
        assert payload['account']['solar_capacity_kw'] == 4
        assert payload['account']['permit_issue_date'] == '2026-02-01'
        assert payload['account']['bwp_opening_credit'] == 10
        assert payload['account']['bwp_opening_balance_confirmed']
        code, job = call('/api/v1/socal/studies', payload, caps['token'])
        assert code == 202
        runner = JobRunner(app.store)
        try:
            saved = until(lambda: call('/api/studies/' + job['id'])[1],
                          lambda value: value['status'] in ('completed', 'failed'))
            assert saved['status'] == 'completed', saved.get('error')
            ledger = call('/api/studies/' + job['id']
                          + '/tables/solar_credit_ledger')[1]
            rows = [dict(zip(ledger['columns'], row)) for row in ledger['data']]
            pv_ledger = {row['component']: row['amount'] for row in rows
                         if row['scenario'] == 'pv_only'}
            assert pv_ledger['opening_credit'] == 10
            assert pv_ledger['earned_export_credit'] > 0
            assert pv_ledger['closing_credit'] >= 0
            comparison = call('/api/studies/' + job['id']
                              + '/tables/comparison')[1]
            scenarios = {row['scenario']: row for row in
                         (dict(zip(comparison['columns'], values))
                          for values in comparison['data'])}
            assert set(scenarios) == {'grid_only', 'pv_only'}
            assert scenarios['pv_only']['utility_bill'] < scenarios['grid_only']['utility_bill']
        finally:
            runner.close()
