"""Test lossless HDF5 archive compression on one actual late L4 output.

Creates a separate compressed copy and verifies every dataset and attribute.
Does not replace/delete the original or infer whole-campaign compression ratios.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import h5py
import numpy as np

ROOT=Path('/home/kaan/performance_20260907c')
RUN=Path('/home/kaan/codes/athenapp/runs/RESTART_sharp13_20260907_L4_chi100')


def exact_value(a,b):
    x,y=np.asarray(a),np.asarray(b)
    if x.dtype!=y.dtype or x.shape!=y.shape:return False
    if x.dtype.kind=='O':return np.array_equal(x,y)
    return x.tobytes()==y.tobytes()


def verify(source,destination):
    checked=[]
    with h5py.File(source) as a,h5py.File(destination) as b:
        an,bn=[],[]
        a.visit(an.append);b.visit(bn.append)
        if an!=bn:raise ValueError('HDF5 object tree differs')
        for name in ['']+an:
            x,y=a[name or '/'],b[name or '/']
            if type(x)!=type(y) or set(x.attrs)!=set(y.attrs):raise ValueError('Metadata differs')
            for key in x.attrs:
                if not exact_value(x.attrs[key],y.attrs[key]):raise ValueError('Attribute differs: '+name+'/'+key)
            if isinstance(x,h5py.Dataset):
                if x.shape!=y.shape or x.dtype!=y.dtype:raise ValueError('Shape/dtype differs')
                chunks=[()] if x.ndim==0 else [slice(i,i+1) for i in range(x.shape[0])]
                for region in chunks:
                    if not exact_value(x[region],y[region]):raise ValueError('Raw decoded bytes differ: '+name)
                checked.append(name)
    return checked


def main():
    record=json.loads((RUN/'provenance.json').read_text())
    source=RUN/record['native_time_rows'][-1][1]
    dest=ROOT/'late_l4_lossless.athdf'
    if dest.exists():raise RuntimeError('Pilot already exists')
    started=time.perf_counter()
    subprocess.run(['h5repack','-f','SHUF','-f','GZIP=1',str(source),str(dest)],check=True)
    encoding_seconds=time.perf_counter()-started
    checked=verify(source,dest)
    result=dict(source=str(source),destination=str(dest),source_bytes=source.stat().st_size,
        compressed_bytes=dest.stat().st_size,encoding_seconds=encoding_seconds,
        size_reduction_percent=100*(1-dest.stat().st_size/source.stat().st_size),
        time_tcc=record['native_time_rows'][-1][0],checked_datasets=checked,
        all_attributes_identical=True,decoded_bytes_identical=True,original_retained=True,
        scope='One late L4 Athena++ file only. Not a promised L5/L6 or cross-code ratio.')
    (ROOT/'lossless_probe.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
