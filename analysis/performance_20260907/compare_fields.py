"""Full-field regression across optimization variants, at identical native times."""
import json
from pathlib import Path
import sys
import numpy as np
import h5py
sys.path.insert(0,'/home/kaan/codes/athenapp/vis/python')
import athena_read
ROOT=Path('/home/kaan/performance_20260907/benchmarks_v3')


def uniform_apk(path,field):
    import yt
    yt.set_log_level(40)
    ds=yt.load(str(path))
    cg=ds.covering_grid(0,ds.domain_left_edge,ds.domain_dimensions)
    # Unit-native array; no smoothing, interpolation or downsampling.
    a=cg[field].to_value()
    return float(ds.current_time.to_value('code_time')),np.array(a)


def compare(base_name,candidate_name):
    b=json.loads((ROOT/base_name/'result.json').read_text())
    c=json.loads((ROOT/candidate_name/'result.json').read_text())
    assert b['returncode']==c['returncode']==0
    assert b['dimensions_streamwise']==c['dimensions_streamwise']
    first,last=b['native_outputs'][-1],c['native_outputs'][-1]
    errors={}
    if b['kind']=='athpp':
        with h5py.File(first) as f:
            names=[v.decode() for v in f.attrs['VariableNames']]
            bt=float(f.attrs['Time'])
        with h5py.File(last) as f:ct=float(f.attrs['Time'])
        assert abs(bt-ct)<1e-12
        for field in names:
            x=athena_read.athdf(first,quantities=[field],dtype=np.float64)[field]
            y=athena_read.athdf(last,quantities=[field],dtype=np.float64)[field]
            assert np.all(np.isfinite(x)) and np.all(np.isfinite(y))
            errors[field]=float(np.max(abs(x-y))/max(1,float(np.max(abs(x)))))
    else:
        for field in ('density','velocity_x','velocity_y','velocity_z','pressure','prim_scalar_0'):
            native=('parthenon',field) if field=='prim_scalar_0' else ('gas',field)
            bt,x=uniform_apk(first,native);ct,y=uniform_apk(last,native)
            assert abs(bt-ct)<1e-12
            assert np.all(np.isfinite(x)) and np.all(np.isfinite(y))
            errors[field]=float(np.max(abs(x-y))/max(1,float(np.max(abs(x)))))
    result={'baseline':base_name,'candidate':candidate_name,'time_code':bt,
            'dimensions':b['dimensions_streamwise'],'all_native_cells_compared':int(np.prod(b['dimensions_streamwise'])),
            'max_field_difference_scaled':errors,'tolerance':1e-10,
            'passed':max(errors.values())<=1e-10,
            'scope':'short-run field agreement; not a guarantee of bitwise identity over a full turbulent evolution'}
    print(json.dumps(result),flush=True)
    if not result['passed']:raise AssertionError(result)
    return result


if __name__=='__main__':
    results=[]
    for a,b in [('base32_r8','native32_r8'),('base32_r8','native64_r8_retry'),
                ('base32_r8','native32_r16'),('base32_r8','native64_r16'),
                ('base32_r8','native32_r4'),('apk_block32','apk_block64'),
                ('L6_cpu_base','L6_cpu_native'),('apk_block64','apk_block128_clean'),
                ('L6_apk_block64_retry','L6_apk_block128_clean')]:
        if (ROOT/a/'result.json').exists() and (ROOT/b/'result.json').exists():
            if any(json.loads((ROOT/n/'result.json').read_text())['returncode'] for n in (a,b)):
                continue
            results.append(compare(a,b))
    Path(__file__).with_name('field_regression.json').write_text(json.dumps(results,indent=2))
