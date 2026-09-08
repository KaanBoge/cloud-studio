"""Read-only native Enzo field inventory for the existing audit smoke."""
from pathlib import Path
import yt
import h5py
yt.set_log_level(40)
p=Path('/home/kaan/ic_audit_20260907/grid_tests/enzo_chi100/DD0000/CW_0000')
ds=yt.load(str(p));ad=ds.all_data();print(ds.field_list,ds.gamma)
for f in ds.field_list:
    a=ad[f];print(f,str(a.units),a.shape,float(a.min()),float(a.max()))
for file in p.parent.glob('*.cpu*'):
    with h5py.File(file) as h:
        def visit(name,obj):
            if isinstance(obj,h5py.Dataset):print(name,str(obj.dtype),obj.shape)
        h.visititems(visit)
    break
