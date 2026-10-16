"""Rebuild audited PSE&G ratebooks from retained official sheet text, offline.

Default operation verifies the frozen Python data without writing. --write
updates only ratebooks, preserving independently dated reconciliation data.
Every retained sheet checksum is checked before parsing; decimal amounts retain
thousands separators. This is a review tool, never a live tariff fallback.
"""
import argparse
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import pprint
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def values(line):
    out=[]
    for m in re.finditer(r'-?(?:\d{1,3}(?:,\d{3})+|\d+)\.\d+',line):
        p=line[max(0,m.start()-3):m.start()]
        out.append(-abs(float(m[0].replace(',', ''))) if '(' in p else float(m[0].replace(',', '')))
    return out

def sheets(text):
    out={}
    for chunk in text.split('=== PDF PAGE ')[1:]:
        n,s=chunk.split(' ===',1)
        m=re.search(r'No\. 17 ELECTRIC[^\n]*Sheet No\. (\d+[A-Z]?)',s)
        if m: out[m[1]]=(int(n),s)
    return out

def line(s,prefix):
    return next(x for x in s.splitlines() if x.strip().startswith(prefix))

def numbers(s,prefix): return values(line(s,prefix))
def season_pair(v):
    if len(v)==2: return [v[1],v[1]]
    assert len(v)==4,v
    return [v[1],v[3]]

def rates(meta,evidence):
    mapping=evidence['source_mapping'][meta['file']]
    sh={}
    for n,entry in mapping.items():
        text=evidence['texts'][entry['text_sha256']]
        if hashlib.sha256(text.encode()).hexdigest()!=entry['text_sha256']:
            raise ValueError('Retained PSE&G sheet checksum differs: '+meta['file']+' sheet'+n)
        sh[n]=(entry['pdf_page'],text)
    page=lambda n:sh[str(n)][1]
    numeric=lambda n,prefix:numbers(page(n),prefix)
    delivered={}
    for plan,n in [('RS',93),('RHS',99),('RLM',105),('HS',123),('GLP',129),('LPL_S',142),('LPL_P',143),('HTS_SUB',155),('HTS_HV',156)]:
        p=page(n); rows=[x.strip() for x in p.splitlines() if len(values(x))>=2 and (' $' in x or x.strip().startswith('$') or x.strip().startswith('On-Peak') or x.strip().startswith('Off-Peak'))]
        rows=[x for x in rows if not x.startswith('adjustment factor')]
        fixed=values(next(x for x in rows if 'in each month' in x))[1]
        if plan in ['RS','RHS']:
            rr=[values(x) for x in rows if len(values(x))==4]
            delivered[plan]={'customer':fixed,'tier_first':season_pair(rr[0]),'tier_excess':season_pair(rr[1])}
            if plan=='RS' and len(rr)>2:
                delivered['RS_TOU_3P']={'customer':fixed,**{k:season_pair(rr[i+2]) for i,k in enumerate(['on_peak','mid_peak','off_peak'])}}
        elif plan=='RLM':delivered[plan]={'customer':fixed,'on_peak':season_pair(numeric(n,'On-Peak')),'off_peak':season_pair(numeric(n,'Off-Peak'))}
        elif plan=='HS':delivered[plan]={'customer':fixed,'energy':season_pair(next(values(x) for x in rows if len(values(x))==4))}
        elif plan=='GLP':
            v=[values(x) for x in rows if 'per kilowatt of' in x]
            e=next(values(x) for x in rows if 'per kilowatt-hour' in x)
            delivered[plan]={'customer':fixed,'annual_demand':v[0][1],'summer_demand':v[1][1],'energy':season_pair(e)}
        else:
            v=[values(x) for x in rows if 'per kilowatt of' in x]
            delivered[plan]={'customer':fixed,'annual_demand':v[0][1],'summer_demand':v[1][1] if len(v)>1 else 0.,'energy':[0.,0.]}
    supply={}
    p75=page(75);p76=page(76)
    for plan in ['RS','RHS']:
        supply[plan]={'tier_first':season_pair(numbers(p75,plan+' – first')),'tier_excess':season_pair(numbers(p75,plan+' – in excess')),'transmission':season_pair(numbers(p76,plan+' '))}
    for plan in ['RLM','RS_TOU_3P']:
        key='RS-TOU 3P' if plan=='RS_TOU_3P' else plan
        if plan not in delivered:continue
        periods=['On-Peak','Mid-Peak','Off-Peak'] if plan=='RS_TOU_3P' else ['On-Peak','Off-Peak']
        supply[plan]={'energy':{},'transmission':{}}
        for per in periods:
            k=per.lower().replace('-','_')
            supply[plan]['energy'][k]=season_pair(numbers(p75,key+' '+per))
            supply[plan]['transmission'][k]=season_pair(numbers(p76,key+' '+per))
    supply['HS']={'energy':season_pair(numbers(p75,'HS ')),'transmission':season_pair(numbers(p76,'HS '))}
    supply['GLP']={'energy':season_pair(numbers(p76,'GLP ')),'night_energy':season_pair(numbers(p76,'GLP Night Use'))}
    end=p76.split('LPL-Sec. under')[1]
    supply['LPL_S']={'energy':{'on_peak':season_pair(numbers(end,'On-Peak')),'off_peak':season_pair(numbers(end,'Off-Peak'))}}
    cap=lambda n:values(line(page(n),'Charge including New Jersey Sales'))[0]
    tr=lambda n:values(line(page(n),'Charge including New Jersey Sales'))[-1]
    trans=[values(x)[-1] for x in page(79).splitlines() if x.strip().startswith('Charge including New Jersey Sales')][-1]
    for plan in ['GLP','LPL_S']:supply[plan].update(capacity=cap(79),transmission=trans)
    ciepcap=cap(82);cieptr=tr(83)
    marginal=re.search(r'marginal losses of ([0-9.]+)%',page(82))[1]
    after=page(60).split('Charges including New Jersey')[1]
    before=page(57)
    sbc={k:numbers(before,pref)[0] for k,pref in [('secondary','Secondary Service '),('primary','LPL Primary '),('subtransmission','HTS Subtransmission '),('high_voltage','HTS High Voltage & HTS Transmission ')]}
    ngc={k:numbers(after,pref)[-1] for k,pref in [('residential','RS, RHS & RLM '),('secondary','Other Secondary Service '),('primary','LPL Primary '),('subtransmission','HTS Subtransmission '),('high_voltage','HTS High Voltage & HTS Transmission ')]}
    riders={'societal_benefits':sbc,'nonutility_generation':ngc,'zero_emission':cap(61),'solar_pilot':cap(64),'green_programs':cap(65)}
    riders['conservation']={k:numeric(66,p)[1] for k,p in [('RS','RS & RHS'),('RHS','RS & RHS'),('RLM','RLM '),('GLP','GLP '),('LPL_S','LPL-S ')]}
    riders['covid']=cap(67) if 'COVID-19 COST RECOVERY CHARGE' in page(67) else 0.
    riders['tax_adjustment']={k:numeric(69,p)[1] for k,p in [('RS','RS '),('RHS','RHS '),('RLM','RLM '),('HS','HS '),('GLP','GLP '),('LPL_S','LPL – Secondary '),('LPL_P','LPL – Primary '),('HTS_SUB','HTS – Subtransmission '),('HTS_HV','HTS – High Voltage ')]}
    standby=cap(73)
    rr={'delivery':delivered,'rscp':supply,'ciep':{'capacity':ciepcap,'transmission':cieptr,'mean_marginal_loss_pct':float(marginal),'ancillary_per_kwh':.006,'standby':standby},'riders':riders}
    source={'document_id':Path(meta['file']).stem,'url':meta['url'],'sha256':meta['sha256'],'retrieved_date':'2026-10-15','sheets':{n:{'pdf_page':pn,'effective':re.findall(r'Effective:\s*([^\n]+)',s)[-1].strip() if re.findall(r'Effective:\s*([^\n]+)',s) else None} for n,(pn,s) in sh.items() if n in ['19','30','31','38','39','40','57','60','61','64','65','66','67','68','69','73','75','76','79','82','83','93','99','105','123','129','142','143','155','156']}}
    return rr,source

def compile_ratebooks(directory=ROOT/'docs/utility_sources/pseg'):
    directory=Path(directory)
    evidence=json.loads((directory/'sheets.json').read_text())
    manifest=json.loads((directory/'manifest.json').read_text())
    out=[]
    for meta in manifest:
        if meta['file'] not in evidence['source_mapping']:
            continue
        stamp=re.search(r'(\d{8})',meta['file'])[1]
        day=date(int(stamp[:4]),int(stamp[4:6]),int(stamp[6:]))
        if day<date(2025,1,1):
            continue
        compiled,source=rates(meta,evidence)
        out.append({'effective_start':day.isoformat(),'rates':compiled,'source':source})
    return sorted(out,key=lambda row:row['effective_start'])


def main():
    from src.billing.pseg_rates import DATA
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true',help='Rewrite frozen ratebooks after source review; reconciliation is preserved')
    args=parser.parse_args()
    compiled=compile_ratebooks()
    if args.write:
        updated=deepcopy(DATA);updated['ratebooks']=compiled
        path=ROOT/'src/billing/pseg_rates.py'
        header=path.read_text().split('DATA = ',1)[0]
        path.write_text(header+'DATA = '+pprint.pformat(updated,width=120,sort_dicts=False)+'\n')
    elif compiled!=DATA['ratebooks']:
        raise SystemExit('Compiled official sheet rates differ from frozen data; review the difference before --write.')
    print(str(len(compiled))+' official PSE&G ratebooks verified')


if __name__=='__main__':
    main()
