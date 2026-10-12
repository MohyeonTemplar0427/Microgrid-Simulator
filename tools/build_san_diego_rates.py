"""Rebuild bounded San Diego literals from checked-in official PDF extractions.

Offline only. This does not enable the unverified historical research archive.
Run with /usr/local/bin/python3 tools/build_san_diego_rates.py.
"""
from pathlib import Path
import json
import re
from pprint import pformat

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / 'docs/utility_sources/san_diego'


def build():
    manifest = {x['id']: x for x in json.loads((SOURCES / 'source_manifest.json').read_text())}
    def source(name):
        x = manifest[name]
        return {k: x[k] for k in ('url', 'sha256', 'retrieved_on', 'text_file')}

    sdge = {}
    for schedule in ('TOU-DR1', 'TOU-DR2', 'EV-TOU-5'):
        sdge[schedule] = []
        for start, end in [('2026-06-01', '2026-07-31'), ('2026-08-01', '2026-10-11')]:
            name = f'sdge-{schedule}-{start}'
            text = (SOURCES / (name + '.txt')).read_text()
            season = None
            rates = {}
            for line in text.splitlines():
                if line.strip() in ('Summer', 'Winter'):
                    season = line.strip().lower()
                m = re.match(r'^\s*(On-Peak|Off-Peak|Super Off-Peak)\s+', line)
                if m and season:
                    # Last four columns: UDC, WF/DWR, EECC, total.
                    numbers = re.findall(r'\(?-?\d+\.\d+\)?', line[m.end():])
                    values = [(-float(x[1:-1]) if x.startswith('(') else float(x)) for x in numbers]
                    assert len(values) == 12, (name, line)
                    udc, wf, gen, total = values[-4:]
                    assert abs(udc + wf + gen - total) < .000011
                    rates[season + '_' + {'On-Peak':'on', 'Off-Peak':'off', 'Super Off-Peak':'super'}[m[1]]] = (udc, wf, gen)
            expected = 4 if schedule == 'TOU-DR2' else 6
            assert len(rates) == expected, (name, rates)
            fixed = next(x for x in text.splitlines() if 'Base Services Charge ($/Day)' in x)
            bsc = float(re.findall(r'\d+\.\d+', fixed)[-1])
            credit = 0.
            if schedule != 'EV-TOU-5':
                row = next(x for x in text.splitlines() if '130% of Baseline' in x)
                credit = float(re.findall(r'\((\d+\.\d+)\)', row)[-1])
            pcia = {int(y): float(v) for y, v in re.findall(r'^(20\d\d) Vintage\s+\$([\d.]+)\s*$', text, re.M)}
            assert len(pcia) == 18 and bsc == .79343
            sdge[schedule].append(dict(start=start, end=end, rates=rates, daily_fixed=bsc,
                                      baseline_credit=credit, pcia=pcia, source=source(name)))
    sdcp = {}
    for cohort in (2021, 2022):
        name = f'sdcp-current-{cohort}'
        text = (SOURCES / (name + '.txt')).read_text()
        schedules = {}
        for schedule, printed in [('TOU-DR1','TOU-DR-1'), ('TOU-DR2','TOU-DR-2'), ('EV-TOU-5','EV-TOU-5')]:
            pos = text.index(printed + ' ' , text.index('Community Power Rates Effective'))
            rows = []
            for line in text[pos:].splitlines():
                m = re.search(r'(Summer|Winter)\s+Generation\s+(On-Peak|Off-Peak|Super Off-Peak)\s+\$([\d.]+)\s+\$([\d.]+)', line)
                if m:
                    rows.append((m[1].lower() + '_' + {'On-Peak':'on','Off-Peak':'off','Super Off-Peak':'super'}[m[2]], (float(m[3]),float(m[4]))))
                if len(rows) == (4 if schedule == 'TOU-DR2' else 6):
                    break
            assert len(dict(rows)) == len(rows) == (4 if schedule == 'TOU-DR2' else 6), (name, schedule)
            schedules[schedule] = dict(rows)
        sdcp[cohort] = dict(rates=schedules, source=source(name))
    cea = {'TOU-DR1': {'summer_on':.55397,'summer_off':.22298,'summer_super':.04914,
                        'winter_on':.19791,'winter_off':.08433,'winter_super':.05138},
           'TOU-DR2': {'summer_on':.53685,'summer_off':.14663,'winter_on':.19180,'winter_off':.06703},
           'EV-TOU-5': {'summer_on':.51684,'summer_off':.15975,'summer_super':.04961,
                       'winter_on':.24430,'winter_off':.15782,'winter_super':.05187}}
    # Verify the transcribed two season columns against the printed CEA rows.
    text = (SOURCES / 'cea-2026-06-01.txt').read_text()
    compact = re.sub(r'(?<=\d)\s+(?=\d)|(?<=\$)\s+|(?<=\d)\s+(?=\.)|(?<=\.)\s+', '', text)
    for schedule, rates in cea.items():
        printed = schedule.replace('DR1', 'DR-1').replace('DR2', 'DR-2')
        for period in ('on', 'off', 'super'):
            if 'summer_' + period not in rates:
                continue
            label = {'on':r'On-P\s*e\s*ak', 'off':r'Off-P\s*e\s*ak', 'super':r'Super Off-Peak'}[period]
            m = re.search(re.escape(printed) + r'\s+' + label + r'\s+\$([\d.]+)\s+\$([\d.]+)', compact)
            assert m and tuple(map(float, m.groups())) == (rates['summer_' + period], rates['winter_' + period]), (schedule, period)
    return dict(SDGE=sdge, SDCP=sdcp, CEA=dict(rates=cea, source=source('cea-2026-06-01')))


if __name__ == '__main__':
    data = build()
    output = '"""Official bounded rate literals; generated by tools/build_san_diego_rates.py."""\n'
    output += '\n'.join(k + ' = ' + pformat(v, sort_dicts=False, width=105) + '\n' for k, v in data.items())
    (ROOT / 'src/billing/san_diego_data.py').write_text(output)
