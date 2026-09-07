"""Compare every saved native field, using identical solver/time/resolution pairs."""
import hashlib
import json
from pathlib import Path
import sys
import h5py
import numpy as np
sys.path.insert(0,'/home/kaan/codes/athenapp/vis/python')
import athena_read
ROOT=Path('/home/kaan/performance_20260907b/runs')
HERE=Path(__file__).resolve().parent

def compare_cpu(base,candidate):
    xfile=base['native_outputs'][-1];yfile=candidate['native_outputs'][-1]
    with h5py.File(xfile) as f:
        names=[s.decode() if isinstance(s,bytes) else str(s) for s in f.attrs['VariableNames']]
        xt=float(f.attrs['Time']);dims=f.attrs['RootGridSize'].tolist()
    with h5py.File(yfile) as f:
        assert dims==f.attrs['RootGridSize'].tolist()
        assert abs(float(f.attrs['Time'])-xt)<1e-12
    errors={}
    for name in names:
        x=athena_read.athdf(xfile,quantities=[name],dtype=np.float64)[name]
        y=athena_read.athdf(yfile,quantities=[name],dtype=np.float64)[name]
        assert np.isfinite(x).all() and np.isfinite(y).all()
        errors[name]=float(np.max(abs(x-y))/max(1,float(np.max(abs(x)))))
    return dict(time_code=xt,dimensions=dims,max_scaled_field_errors=errors,
                passed=max(errors.values())<=1e-10,tolerance=1e-10)

def compare_gpu(base,candidate):
    xfile=base['native_outputs'][-1];yfile=candidate['native_outputs'][-1]
    checked=[]
    with h5py.File(xfile) as x,h5py.File(yfile) as y:
        assert abs(float(x['Info'].attrs['Time'])-float(y['Info'].attrs['Time']))<1e-12
        names=[]
        x.visititems(lambda name,obj:names.append(name) if isinstance(obj,h5py.Dataset) and obj.dtype.kind in 'fiu' else None)
        for name in names:
            a,b=x[name],y[name]
            assert a.dtype==b.dtype and a.shape==b.shape
            if a.ndim==0:
                assert np.array_equal(a[()],b[()]);continue
            for i in range(a.shape[0]):
                aa,bb=a[i],b[i]
                if a.dtype.kind=='f':assert np.isfinite(aa).all() and np.isfinite(bb).all()
                assert np.array_equal(aa,bb),name
            checked.append(name)
        assert 'prim' in checked
        return dict(time_code=float(x['Info'].attrs['Time']),all_numeric_datasets=checked,
                    decoded_fields_exactly_equal=True,passed=True,
                    note='All numeric datasets compared without thinning; compression changes container bytes only.')

if __name__=='__main__':
    rows={p.parent.name:json.loads(p.read_text()) for p in ROOT.glob('*/result.json')}
    results=[]
    pairs=[('current',k) for k in ('wide128','wide256','small128','small64','lto64','lto128','best_repeat2','best_repeat3') if k in rows]
    if 'L6_candidate' in rows:pairs.append(('L6_current','L6_candidate'))
    pairs.extend([('gpu_io_c5','gpu_io_c1'),('gpu_io_c5','gpu_io_c0')])
    for i in (2,3):
        if f'gpu_c1_repeat{i}' in rows:pairs.append((f'gpu_c5_repeat{i}',f'gpu_c1_repeat{i}'))
    for an,bn in pairs:
        a,b=rows[an],rows[bn]
        assert a['rc']==b['rc']==0 and a['code']==b['code'] and a['level']==b['level']
        r=compare_cpu(a,b) if a['code']=='athpp' else compare_gpu(a,b)
        r.update(baseline=an,candidate=bn,baseline_binary_sha256=a['binary_sha256'],
                 candidate_binary_sha256=b['binary_sha256'],scope='short native-field regression, not full-run convergence proof')
        print(json.dumps(r),flush=True);results.append(r)
        if not r['passed']:raise AssertionError(r)
    (HERE/'field_regression.json').write_text(json.dumps(results,indent=2))
