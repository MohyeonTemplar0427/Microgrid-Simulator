"""Review a manually downloaded CEC ESS workbook; never publish catalog edits.

Usage: python tools/review_cec_ess.py downloaded.xlsx review.json
Optional --previous review.json reports discovery additions/removals.
"""
import argparse
import hashlib
import json
from pathlib import Path


def review(path):
    import pandas as pd
    content=Path(path).read_bytes()
    raw=pd.read_excel(path,header=None)
    headers=[i for i,row in raw.iterrows() if 'Manufacturer Name' in row.tolist() and 'Model Number' in row.tolist()]
    if len(headers)!=1: raise ValueError('CEC workbook header changed; manual review required.')
    index=headers[0]
    columns=raw.iloc[index].tolist()
    required=('Manufacturer Name','Model Number','Nameplate Energy Capacity','Nameplate Power')
    # Do not infer alternative column meanings on a changed workbook.
    missing=[name for name in required if name not in columns]
    if missing: raise ValueError('CEC workbook columns changed: '+str(missing))
    frame=raw.iloc[index+1:].copy();frame.columns=columns
    items=[]
    for _,row in frame.iterrows():
        if pd.isna(row['Manufacturer Name']) or pd.isna(row['Model Number']):continue
        items.append({key:None if pd.isna(row[key]) else row[key] for key in required})
    return dict(source_url='https://solarequipment.energy.ca.gov/Home/DownloadtoExcel?filename=EnergyStorage',
                file_sha256=hashlib.sha256(content).hexdigest(),source_notice=str(raw.iloc[1,0]),
                records=items,note='Discovery only. Nameplate energy and power are not automatically usable AC energy or separate charge/discharge limits.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbook',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--previous',type=Path)
    args=parser.parse_args();result=review(args.workbook)
    if args.previous:
        old=json.loads(args.previous.read_text())
        key=lambda r:r['Manufacturer Name']+' / '+r['Model Number']
        before={key(r) for r in old['records']};after={key(r) for r in result['records']}
        result['added']=sorted(after-before);result['removed']=sorted(before-after)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__':main()
