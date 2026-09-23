"""Generate pinned 2026 hourly NBT data from PG&E's official UTC CSVs.

Usage: python tools/solar_export/build_pge_export_data.py <download-directory>
The ZIP source is https://www.pge.com/eecvalues. No network in runtime/tests.
"""
from pathlib import Path
import sys, hashlib, pprint
import pandas as pd

root=Path(sys.argv[1]); output=Path('src/billing/pge_export_data.py')
records={};hashes={}
for vintage in (2023,2024,2025,2026):
 p=root/f'PG&E NBT EEC Values {vintage} Vintage.csv'
 frame=pd.read_csv(p,encoding='utf-8-sig')
 start=pd.to_datetime(frame.DateStart+' '+frame.TimeStart,utc=True)
 finish=pd.to_datetime(frame.DateEnd+' '+frame.TimeEnd,utc=True)
 index=pd.date_range('2026-01-01', '2027-01-01',freq='h',inclusive='left',tz='America/Los_Angeles').tz_convert('UTC')
 frame=frame.loc[start.isin(index)].copy();frame['utc']=start.loc[frame.index]
 assert (finish.loc[frame.index]-start.loc[frame.index]).eq(pd.Timedelta(seconds=3599)).all()
 assert frame.Unit.eq('Export $/kWh').all()
 values=[]
 for prefix in ('USCA-XXPG','USCA-PGXX'):
  selected=frame[frame.RIN.str.startswith(prefix)].set_index('utc').sort_index()
  assert selected.index.equals(index),f'Missing/duplicate {vintage} {prefix}'
  rates=selected.Value.to_numpy();ints=(rates*100000).round().astype(int)
  assert abs(rates-ints/100000).max()<1e-10
  values.append(ints.tolist())
 records[vintage]=list(zip(*values));hashes[vintage]=hashlib.sha256(p.read_bytes()).hexdigest()
output.write_text('''"""Generated official PG&E 2026 UTC-hour export factors. Do not hand edit.

Each pair is (generation, delivery), units $0.00001/kWh. Index zero is
2026-01-01 08:00 UTC. Use instants, not hand-built holiday/DST tables.
Source: https://www.pge.com/assets/pge/docs/vanities/PGE-Solar-Billing-Plan-Export-Rates.zip
Retrieved 2026-09-21. Only 2026 retained; future illustrative data excluded.
"""\nSOURCE_SHA256 = '''+repr(hashes)+'\nRATES = '+pprint.pformat(records,width=110,compact=True)+'\n')
print(output,output.stat().st_size)
