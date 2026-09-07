"""Inspect native FLASH fields/precision and sizes; no data changes."""
import json
from pathlib import Path
import h5py
root=Path('/home/kaan/ic_audit_20260907/grid_tests/flash_chi100')
for p in sorted(root.glob('*hdf5*')):
    with h5py.File(p) as h:
        fields={k:dict(shape=list(v.shape),dtype=str(v.dtype)) for k,v in h.items() if isinstance(v,h5py.Dataset) and v.ndim==4}
        print(json.dumps(dict(path=str(p),bytes=p.stat().st_size,fields=fields,
            node_types=h['node type'][:].tolist(),bbox_shape=list(h['bounding box'].shape),
            real_scalars=str(h['real scalars'][:]))))
