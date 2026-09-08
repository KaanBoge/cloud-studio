"""Read-only completed-run and native field inventory."""
import json
from pathlib import Path
import yt
yt.set_log_level(40)
root=Path('/home/kaan/sensitivity_20260907/athw')
b=json.loads((root/'batch.json').read_text())
print('BATCH',b['status'])
for r in b['finished']:
    print(json.dumps({k:r[k] for k in ('level','mode','status','unique_snapshots','wall_seconds','peak_child_rss_gib')}))
p=next((root/'runs/L3_chi100_sharp13/id0').glob('*.0000.vtk'))
ds=yt.load(str(p));print('FIELDS',ds.field_list)
ad=ds.all_data()
for field in ds.field_list:
    a=ad[field]
    print(field,str(a.units),a.shape,float(a.min()),float(a.max()))
