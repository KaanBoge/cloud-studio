"""Read-only diagnosis of native initial recovery differences."""
import json
import numpy as np
from pathlib import Path
from smoke_gizmo import ROOT,read,save
from verify_gizmo import snapshots
records=[]
for case in json.loads((ROOT/'smoke_batch.json').read_text())['finished']:
    folder=Path(case['directory']);ic,t0=read(folder/'ics.hdf5');a,t=read(snapshots(folder/'output')[0]);errors={}
    for key in ic:
        x,y=ic[key].astype(float),a[key].astype(float)
        errors[key]=dict(exact=bool(np.array_equal(x,y)),max_absolute=float(np.max(abs(x-y))),max_scaled=float(np.max(abs(x-y)/np.maximum(abs(x),1))))
    records.append(dict(variant=case['variant'],mode=case['mode'],time=t,errors=errors))
save(ROOT/'initial_recovery_diagnosis.json',dict(records=records));print(json.dumps(records,indent=2))
