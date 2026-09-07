import json
import numpy as np
from run_flash import ROOT,raw,parameters

data=[]
for name in ('sharp13','tanh13'):
    folder=ROOT/f'smokes/L3_chi100_{name}';p=parameters(folder/'flash.par')
    data.append(raw(folder/'cloudcrush_hdf5_chk_0000',p,True))
for key in sorted(data[0]['fields']):
    a,b=[d['fields'][key] for d in data]
    print(json.dumps(dict(field=key,exact=bool(np.array_equal(a,b)),max_absolute=float(np.max(abs(a-b))),
        max_relative=float(np.max(abs(a-b)/np.maximum(np.maximum(abs(a),abs(b)),1e-300))),
        min_sharp=float(a.min()),max_sharp=float(a.max()))))
