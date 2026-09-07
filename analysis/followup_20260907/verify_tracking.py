"""Small native 3D regression/restart tests of the separate tracking prototype.

All files are retained. This does not certify a material-preserving box, the full
Farber/Gronke algorithm, other solvers, or a replacement production comparison.
"""
import hashlib
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import h5py
import numpy as np
sys.path.insert(0,'/home/kaan/verified_20260907')
sys.path.insert(0,'/home/kaan/performance_20260907')
sys.path.insert(0,'/home/kaan/codes/athenapp/vis/python')
import athena_read
from run_corrected_athpp import make_input
from run_optimized import set_sections
from check_snapshot import check
from storage_guard import require_storage,storage_snapshot,GIB

WORK=Path('/home/kaan/followup_20260907')
BINARY=WORK/'bin/athpp_tracking'
BASE=Path('/home/kaan/ic_audit_20260907/bin/athpp')
ENV=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')


def run(name,chi=10,shift=False,binary=BINARY,restart=None,end=.4):
    root=WORK/'tracking_tests_v2'/name
    require_storage(storage_snapshot(WORK),2*GIB)
    root.mkdir(parents=True,exist_ok=False)
    tcc=math.sqrt(chi)/(2*math.sqrt(5/3))
    text=set_sections(make_input(3,chi),{'problem':{'galilean_shift':str(shift).lower()},
          'meshblock':{'nx1':16,'nx2':16,'nx3':16},'time':{'tlim':repr(end),'ncycle_out':10},
          'output1':{'dt':repr(end/100)},'output2':{'dt':repr(end/100)},
          'output3':{'dt':repr(end/4)}})
    (root/'athinput').write_text(text)
    cmd=['timeout','--signal=TERM','--kill-after=5s','240','mpirun','--bind-to','core','-np','2',str(binary),'-i','athinput']
    if restart:cmd+=['-r',str(restart)]
    record={'command':cmd,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
            'parameter_sha256':hashlib.sha256(text.encode()).hexdigest(),'restart':str(restart) if restart else None,
            'scope':'native experimental validation, not production','expected_t_end':end}
    (root/'provenance.json').write_text(json.dumps(record,indent=2))
    started=time.time()
    with (root/'run.log').open('x') as f:
        rc=subprocess.run(cmd,cwd=root,env=ENV,stdout=f,stderr=subprocess.STDOUT,timeout=260).returncode
    record.update(returncode=rc,wall_seconds=time.time()-started)
    (root/'provenance.json').write_text(json.dumps(record,indent=2))
    if rc:raise RuntimeError((root/'run.log').read_text()[-2500:])
    fs=sorted(root.glob('*.athdf'),key=lambda f:native_time(f))
    if not fs or not math.isclose(native_time(fs[-1]),end,abs_tol=1e-12):raise ValueError('Native final time missing')
    record['native_outputs']=len(fs)
    if not restart:
        ic=check(str(fs[0]),str(root/'athinput'),'athpp',[0,0,0],[64,32,32])
        record['initial_fields']=ic
        if not ic['passed']:raise ValueError(ic)
    summary=[]
    for f in fs:
        x=athena_read.athdf(str(f),dtype=np.float64)
        with h5py.File(f) as h:names=[n.decode() for n in h.attrs['VariableNames']]
        if any(not np.all(np.isfinite(x[n])) for n in names):raise ValueError('Nonfinite native fields')
        if x['rho'].min()<=0 or x['press'].min()<=0:raise ValueError('Nonpositive native fields')
        sel=x['rho']>chi/3;mass=x['rho'][sel].sum()
        velocity=float((x['rho'][sel]*x['vel1'][sel]).sum()/mass) if mass else None
        summary.append({'file':f.name,'t_code':native_time(f),'t_over_tcc':native_time(f)/tcc,
                        'dense_velocity_in_frame':velocity,'min_pressure':float(x['press'].min()),
                        'tracer_mass_in_box':float(np.sum(x['rho']*x['r0'])*(20/64)**3),
                        'dense_mass_in_box':float(mass*(20/64)**3),
                        'dense_centroid_x':float(np.sum(x['rho']*sel*x['x1v'][None,None,:])/mass) if mass else None})
    record['snapshots']=summary
    if shift and not restart:
        maximum=max(abs(r['dense_velocity_in_frame']) for r in summary if r['dense_velocity_in_frame'] is not None)
        record['maximum_dense_velocity_after_boost']=maximum
        if maximum>1e-10:raise ValueError('Saved primitives did not receive the frame boost')
    (root/'verification.json').write_text(json.dumps(record,indent=2))
    print(name, 'PASS',record['native_outputs'],'snapshots',round(record['wall_seconds'],2),'seconds',flush=True)
    return root,fs,record


def native_time(f):
    with h5py.File(f) as h:return float(h.attrs['Time'])


def compare(a,b):
    x=athena_read.athdf(str(a),dtype=np.float64);y=athena_read.athdf(str(b),dtype=np.float64)
    with h5py.File(a) as h:names=[n.decode() for n in h.attrs['VariableNames']]
    if not math.isclose(native_time(a),native_time(b),abs_tol=1e-12):raise ValueError('Different comparison times')
    errors={n:float(np.max(np.abs(x[n]-y[n]))/max(1,float(np.max(np.abs(x[n]))))) for n in names}
    if max(errors.values())>1e-10:raise ValueError(errors)
    return errors


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--full-time',action='store_true',help='L3 integration tests through 5 t_cc; still not production certification')
    a=p.parse_args()
    if a.full_time:
        result={'scope':'L3 3D integration tests through 5 t_cc; not a matched-code production comparison', 'runs':[]}
        for chi in (10,100,1000):
            end=5*math.sqrt(chi)/(2*math.sqrt(5/3))
            for shift in (False,True):
                _,_,r=run(f'fulltime_chi{chi}_shift{int(shift)}',chi=chi,shift=shift,end=end)
                ratio=r['snapshots'][-1]['tracer_mass_in_box']/r['snapshots'][0]['tracer_mass_in_box']
                r['final_tracer_mass_fraction_in_box']=ratio
                print('Retained tracer mass fraction',ratio,flush=True)
                result['runs'].append(r)
                (WORK/'evidence/tracking_fulltime.json').write_text(json.dumps(result,indent=2))
        result['completed']=True
        (WORK/'evidence/tracking_fulltime.json').write_text(json.dumps(result,indent=2))
        return
    result={'scope':'Short 3D tests at L3, not production or full FG22 tracking','runs':[]}
    _,base,record=run('baseline_no_shift',binary=BASE);result['runs'].append(record)
    _,off,record=run('tracking_disabled');result['runs'].append(record)
    result['disabled_matches_baseline']=compare(base[-1],off[-1])
    on_root,on,record=run('tracking_enabled',shift=True);result['runs'].append(record)
    checkpoints=sorted(on_root.glob('*.rst'))
    # Use a mid-run checkpoint from the uninterrupted trajectory so timestep
    # history before interruption is identical, not two different tlim runs.
    checkpoints=[p for p in checkpoints if '.final.' not in p.name]
    if len(checkpoints)<3:raise ValueError('No intermediate restart checkpoints')
    _,resumed,record=run('tracking_resumed',shift=True,restart=checkpoints[1]);result['runs'].append(record)
    result['restart_matches_uninterrupted']=compare(on[-1],resumed[-1])
    for chi in (100,1000):
        _,_,record=run(f'tracking_chi{chi}',chi=chi,shift=True);result['runs'].append(record)
    result['passed']=True
    (WORK/'evidence/tracking_tests.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='runs'},indent=2),flush=True)


if __name__=='__main__':main()
