"""Extended native tracking tests; retain all raw outputs and report failed physics gates.

No cooling or full production runs. Existing IC, domain, Mach, solver and binary
are unchanged. New directories only. Frame history is recorded every step at
double-precision text accuracy so displacement can be checked independently.
"""
import fcntl
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import h5py
import numpy as np

sys.path[:0]=['/home/kaan/verified_20260907','/home/kaan/performance_20260907',
               '/mnt/c/Users/kaanb/CloudCrushing/followup_20260907']
from run_corrected_athpp import make_input
from run_optimized import set_sections
from run_params import parse_file
from storage_guard import storage_snapshot,require_storage,GIB
from verify_tracking import native_time,compare
from check_snapshot import check

WORK=Path('/home/kaan/followup_20260907')
ROOT=WORK/'tracking_validation_v1'
BIN=WORK/'bin/athpp_tracking'
EXPECTED='3885d83e2238eae01382b88add7a168f713ef72f46420c44219ad23bc7bd7655'
ENV=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def native_fields(path):
    with h5py.File(path) as h:
        if len(h['prim'].shape)!=5 or np.any(h['Levels'][:]):
            raise ValueError('Only audited uniform, native, 3D primitive layouts supported')
        names=[s.decode() if isinstance(s,bytes) else str(s) for s in h.attrs['VariableNames']]
        if names!=['rho','press','vel1','vel2','vel3','r0']:
            raise ValueError('Unexpected native variable layout')
        a=h['prim'][:]
        if not np.all(np.isfinite(a)):raise ValueError('Nonfinite native fields')
        f={n:a[i] for i,n in enumerate(names)}
        dx=np.diff(h['x1f'][:],axis=1);dy=np.diff(h['x2f'][:],axis=1);dz=np.diff(h['x3f'][:],axis=1)
        volume=dx[:,None,None,:]*dy[:,None,:,None]*dz[:,:,None,None]
        x=h['x1v'][:][:,None,None,:]
        return f,volume,x,float(h.attrs['Time'])


def read_history(path,source_input=None):
    text=path.read_text();header=next((line for line in text.splitlines() if '[1]=time' in line),None)
    if header is None and source_input:
        # A new restart directory can contain headerless history: the native
        # output counter was restored. Read names from its pinned parent run.
        source_history=next(Path(source_input).parent.glob('*.hst'))
        header=next((line for line in source_history.read_text().splitlines() if '[1]=time' in line),None)
    if header is None:raise ValueError('Native history column header is unavailable')
    names=re.findall(r'\[\d+\]=([^\s]+)',header)
    a=np.loadtxt(path,comments='#',ndmin=2)
    if a.shape[1]!=len(names) or not np.all(np.isfinite(a)):raise ValueError('Invalid native history')
    # A restart appends a new initial record only in its new directory; exact
    # duplicate timestamps may occur there. Retain the last identical-time row.
    _,rev=np.unique(a[::-1,0],return_index=True);a=a[::-1][np.sort(rev)][::-1]
    if np.any(np.diff(a[:,0])<=0):raise ValueError('Nonmonotonic history')
    return {n:a[:,i] for i,n in enumerate(names)}


def assess(root,chi,level,restart=False):
    params=parse_file(root/'athinput');tcc=params['t_cc']
    files=sorted(root.glob('*.athdf'),key=native_time)
    if not files:raise ValueError('Missing native snapshots')
    provenance=json.loads((root/'provenance.json').read_text())
    history=read_history(next(root.glob('*.hst')),provenance.get('source_input'))
    if history['time'].size<2:raise ValueError('Insufficient history')
    # Independent discrete integral: each completed step used the PREVIOUS
    # frame speed. Do not compare displacement to velocity times final time.
    delta=history['frame_x'][1:]-history['frame_x'][:-1]
    expected=history['frame_v'][:-1]*np.diff(history['time'])
    offset_error=float(np.max(np.abs(delta-expected)))
    if offset_error>1e-10:raise ValueError(f'Frame displacement integration mismatch {offset_error}')
    rows=[]
    for p in files:
        f,v,x,t=native_fields(p)
        if f['rho'].min()<=0 or f['press'].min()<=0:raise ValueError('Nonpositive native state')
        k=int(np.argmin(np.abs(history['time']-t)))
        if abs(history['time'][k]-t)>1e-11*max(1,tcc):raise ValueError('No contemporaneous frame history')
        tracer=f['rho']*f['r0'];mass=float(np.sum(tracer*v))
        if mass<=0:raise ValueError('No tracer mass to diagnose')
        centroid=float(np.sum(tracer*v*x)/mass)
        dense=f['rho']>chi/3;dense_mass=float(np.sum(f['rho']*dense*v))
        vel=float(np.sum(f['rho']*dense*f['vel1']*v)/dense_mass) if dense_mass else None
        sums_error=abs(mass-history['0-scalar'][k])/max(1,mass)
        if sums_error>1e-10:raise ValueError('Native snapshot/history tracer integrals disagree')
        rows.append({'file':p.name,'time_code':t,'t_over_tcc':t/tcc,'tracer_mass_in_box':mass,
                     'dense_mass_in_box':dense_mass,'dense_mean_v_in_frame':vel,
                     'tracer_centroid_x_in_frame':centroid,'frame_v':float(history['frame_v'][k]),
                     'frame_x':float(history['frame_x'][k]),'tracer_centroid_x_lab':centroid+float(history['frame_x'][k]),
                     'min_pressure':float(f['press'].min()),'tracer_min':float(f['r0'].min()),
                     'tracer_max':float(f['r0'].max()),'snapshot_history_tracer_relative_error':sums_error})
    times=np.array([r['t_over_tcc'] for r in rows])
    if np.any(np.diff(times)<=0):raise ValueError('Repeated or nonmonotonic snapshot times')
    if abs(rows[-1]['time_code']-params['tmax'])>1e-10:raise ValueError('Incomplete native final time')
    result={'scope':'native frame/restart validation, not proof of all-material retention',
            'parameters':params,'level':level,'dimensions':[8*2**level,4*2**level,4*2**level],
            'native_snapshots':len(rows),'step_history_rows':len(history['time']),
            'history_displacement_max_absolute_error':offset_error,
            'native_numerical_checks_passed':True,'series':rows}
    if not restart:
        ic=check(str(files[0]),str(root/'athinput'),'athpp',[0,0,0],result['dimensions'])
        if not ic['passed']:raise ValueError(ic)
        result['initial_condition_check']=ic
        for r in rows:r['tracer_mass_over_initial']=r['tracer_mass_in_box']/rows[0]['tracer_mass_in_box']
        result['final_tracer_mass_fraction']=rows[-1]['tracer_mass_over_initial']
        if abs(times[-1]-5)<1e-10:
            result['target_snapshots']=101
            result['measured_cadence_max_offset_tcc']=float(np.max(np.abs(times-np.linspace(0,5,101)))) if len(rows)==101 else None
            result['cadence_count_passed']=len(rows)==101
            result['net_retention_within_one_percent_at_5tcc']=abs(result['final_tracer_mass_fraction']-1)<=.01
            result['one_percent_gate_note']='A diagnostic net-mass tolerance, not proof of zero boundary loss or publication approval.'
    (root/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    return files,result


def run(name,level,chi,ranks=8,restart=None,source_input=None,end=None):
    if digest(BIN)!=EXPECTED:raise ValueError('Native tracking binary changed')
    budget=8*GIB if level==4 else 2*GIB
    storage=storage_snapshot(WORK);require_storage(storage,budget)
    folder=ROOT/name
    text=source_input.read_text() if source_input else make_input(level,chi)
    updates={'problem':{'galilean_shift':'true'},'output1':{'dt':'1e-30','data_format':'%24.16e'}}
    if not source_input:
        updates['meshblock']={'nx1':16,'nx2':16,'nx3':16}
    if end is not None:updates.update(time={'tlim':repr(end)},output2={'dt':repr(end/10)})
    text=set_sections(text,updates)
    if folder.exists():
        previous=json.loads((folder/'provenance.json').read_text())
        wanted=hashlib.sha256(text.encode()).hexdigest()
        if previous.get('returncode')!=0 or previous['binary_sha256']!=EXPECTED or previous['input_sha256']!=wanted or digest(folder/'athinput')!=wanted:
            raise ValueError('Existing case is not an identical completed run; nothing overwritten')
        files,result=assess(folder,chi,level,restart=bool(restart));result['provenance']=previous
        print('REUSED',name,flush=True);return files,result
    folder.mkdir(parents=True,exist_ok=False)
    (folder/'athinput').write_text(text)
    cmd=['timeout','--signal=TERM','--kill-after=10s','900','mpirun','--bind-to','core','-np',str(ranks),str(BIN),'-i','athinput']
    if restart:cmd+=['-r',str(restart)]
    provenance={'command':cmd,'binary_sha256':EXPECTED,'input_sha256':digest(folder/'athinput'),
                'restart_file':str(restart) if restart else None,'restart_sha256':digest(restart) if restart else None,
                'source_input':str(source_input) if source_input else None,'storage_preflight':storage,
                'scope':'validation only; same existing IC and box; raw output retained'}
    (folder/'provenance.json').write_text(json.dumps(provenance,indent=2))
    start=time.monotonic()
    print('RUNNING',name,flush=True)
    with (folder/'run.log').open('x') as out:
        p=subprocess.Popen(cmd,cwd=folder,env=ENV,stdout=out,stderr=subprocess.STDOUT)
        last=start
        while p.poll() is None:
            time.sleep(1)
            if time.monotonic()-last>30:
                print('PROGRESS',name,'elapsed',round(time.monotonic()-start),'s snapshots',len(list(folder.glob('*.athdf'))),flush=True)
                last=time.monotonic()
    provenance.update(returncode=p.returncode,solver_wall_seconds=time.monotonic()-start)
    (folder/'provenance.json').write_text(json.dumps(provenance,indent=2))
    if p.returncode:raise ValueError((folder/'run.log').read_text()[-3000:])
    files,result=assess(folder,chi,level,restart=bool(restart))
    result['provenance']=provenance
    print('CHECKED',name,len(files),'snapshots; retention',result.get('final_tracer_mass_fraction'),'solver s',round(provenance['solver_wall_seconds'],1),flush=True)
    return files,result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--resume-validation',action='store_true');args=parser.parse_args()
    ROOT.mkdir(exist_ok=args.resume_validation)
    # Share the optimized launcher's lock as well as our own per-run-directory guard.
    with (Path('/home/kaan/performance_20260907')/'production.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        results={'scope':'existing-condition Athena++ native tracking validation; no cooling reruns','tests':{}}
        output=WORK/'evidence/tracking_extended.json'
        def save():output.write_text(json.dumps(results,indent=2)+'\n')
        for chi in (10,100,1000):
            old=WORK/'tracking_tests_v2'/f'fulltime_chi{chi}_shift1'
            checkpoint=next(old.glob('*.00002.rst'))
            files,report=run(f'L3_chi{chi}_late_restart',3,chi,ranks=2,restart=checkpoint,source_input=old/'athinput')
            target=max(old.glob('*.athdf'),key=native_time)
            report['restart_final_field_errors']=compare(target,files[-1])
            results['tests'][f'L3_chi{chi}_late_restart']=report;save()
        mpi=[]
        for ranks in (1,4):
            files,report=run(f'L3_chi100_mpi{ranks}',3,100,ranks=ranks,end=.4)
            results['tests'][f'L3_chi100_mpi{ranks}']=report;mpi.append(files[-1]);save()
        results['mpi_decomposition_final_field_errors']=compare(*mpi);save()
        for chi in (10,100,1000):
            _,report=run(f'L4_chi{chi}_full',4,chi)
            results['tests'][f'L4_chi{chi}_full']=report;save()
        results['execution_completed']=True
        results['all_material_retention_certified']=False
        save();print('EXTENDED TESTS COMPLETE; inspect individual physics gates',flush=True)

if __name__=='__main__':main()
