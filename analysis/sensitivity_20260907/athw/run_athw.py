"""Persistent bounded Athena 4.2 sensitivity queue, L3/L4/L5 at chi=100/Mach=2.

Preserves every native VTK field and all restart files. Native VTK is float32;
the solver and restarts remain at the existing precision. No cleanup or restart
from unvalidated checkpoints. Only a velocity-mode parameter changes per pair.
"""
import argparse
import fcntl
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import numpy as np
import psutil
import yt

sys.path.insert(0,'/mnt/c/Users/kaanb/CloudCrushing/sensitivity_20260907')
from build import sha
sys.path.insert(0,'/home/kaan/verified_20260907')
from run_params import parse_file
from storage_guard import storage_snapshot,require_storage,GIB
sys.path.insert(0,'/mnt/c/Users/kaanb/CloudCrushing/audit_20260907')
from grid_smokes import set_sections

ROOT=Path('/home/kaan/sensitivity_20260907/athw')
LEVELS=(3,4,5)
yt.set_log_level(40)

def save(path,record):
    p=Path(path);tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(record,indent=2,allow_nan=False));tmp.replace(p)

def input_for(level,mode,end=None):
    if level not in LEVELS or mode not in (0,1):raise ValueError('Unvalidated case')
    nx=8*2**level;tcc=math.sqrt(100)/(2*math.sqrt(5/3));end=5*tcc if end is None else end
    text=Path('/home/kaan/ic_audit_20260907/grid_tests/athw_chi100/athinput').read_text()
    text=text[text.index('<job>'):]
    text='\n'.join(line.split('#',1)[0].rstrip() for line in text.splitlines())
    return '# Isolated 3D sensitivity control; chi=100, Mach=2.\n'+set_sections(text,{
        'job':{'problem_id':f'SensitivityL{level}','maxout':3},
        'time':{'nlim':-1,'tlim':repr(end),'cour_no':.4},
        'domain1':{'Nx1':nx,'Nx2':nx//2,'Nx3':nx//2,'NGrid_x1':2,'NGrid_x2':2,'NGrid_x3':2},
        'problem':{'velocity_ic_tanh':mode,'Mach':2,'drat':100,'rv_scale':1.3,'gamma':repr(5/3)},
        'output1':{'dt':repr(tcc/20)},'output2':{'dt':repr(tcc/20)},
        'output3':{'out_fmt':'rst','out':'cons','dt':repr(tcc)}})

def snapshot(path,params,initial=False,level=3,mode=0):
    ds=yt.load(str(path));ad=ds.all_data()
    rho=ad['gas','density'].to_value('code_density')
    vol=ad['index','cell_volume'].to_value('code_length**3')
    pressure=ad['gas','pressure'].to_value('code_pressure')
    xyz=np.stack([ad['index',a].to_value('code_length') for a in 'xyz'],axis=1)
    velocity=np.stack([ad['gas','velocity_'+a].to_value('code_velocity') for a in 'xyz'],axis=1)
    if not all(np.all(np.isfinite(a)) for a in (rho,vol,pressure,velocity)) or np.min(rho)<=0 or np.min(pressure)<=0:
        raise ValueError('Nonfinite or nonpositive native field')
    dims=[8*2**level,4*2**level,4*2**level]
    if len(rho)!=np.prod(dims):raise ValueError('Incomplete MPI output: unexpected total cells')
    if not np.allclose(ds.domain_width.to_value('code_length'),[20,10,10]):raise ValueError('Wrong domain')
    if not np.allclose(vol,2000/np.prod(dims),rtol=1e-5):raise ValueError('Unexpected cell volume')
    t=float(ds.current_time.to_value('code_time'))
    mass=rho*vol;dense=rho>params['chi']*params['rho_wind']/3;dm=float(mass[dense].sum())
    out=dict(snapshot=str(path),time_code=t,t_over_tcc=t/params['t_cc'],
        dense_mass=dm,total_mass=float(mass.sum()),cells=len(rho),
        dense_centroid_R=float(np.dot(mass[dense],xyz[dense,0])/dm) if dm>0 else None)
    if initial:
        if abs(t)>1e-10:raise ValueError('Expected t=0')
        rad=np.linalg.norm(xyz,axis=1);f=.5*(1-np.tanh((rad-1)/.1))
        expected_rho=1+99*f;vw=params['v_wind']
        vx=vw*(1-.5*(1-np.tanh((rad-1.3)/.1))) if mode else np.where(rad>1.3,vw,0)
        errors=dict(rho_relative=float(np.max(np.abs(rho-expected_rho)/expected_rho)),
          velocity_over_wind=float(max(np.max(np.abs(velocity[:,0]-vx)),np.max(np.abs(velocity[:,1:])))/vw),
          pressure_absolute=float(np.max(np.abs(pressure-1))))
        if max(errors.values())>3e-6:raise ValueError('IC check failed: '+str(errors))
        out['initial_checks']=errors
    return out

def validate(folder,params,level,mode,smoke=False):
    paths=sorted((folder/'id0').glob('*.vtk'))
    if not paths:raise ValueError('Missing native rank-0 files')
    rows=[snapshot(p,params,i==0,level,mode) for i,p in enumerate(paths)]
    rows.sort(key=lambda x:x['time_code'])
    unique=[];duplicates=[]
    for row in rows:
        if unique and abs(row['time_code']-unique[-1]['time_code'])<1e-8:
            duplicates.append(row)
        else:unique.append(row)
    if not smoke:
        if len(unique)!=101 or abs(unique[-1]['t_over_tcc']-5)>1e-4:raise ValueError('Incomplete native cadence')
        offsets=np.array([x['t_over_tcc'] for x in unique])-np.linspace(0,5,101)
        if offsets.min() < -1e-4 or offsets.max()>=.05:raise ValueError('Bad output cadence')
    if unique[0]['dense_mass']<=0:raise ValueError('No initial dense mass')
    for row in unique:row['dense_mass_over_initial']=row['dense_mass']/unique[0]['dense_mass']
    # VTK is full primitive native output, not an archive of double precision.
    return dict(unique_snapshots=len(unique),series=unique,duplicate_time_outputs_retained=duplicates,
                native_output_precision='VTK float32; native solver/restart precision unchanged')

def run_case(level,mode,smoke=False):
    build=json.loads((ROOT/'build.json').read_text());binary=build['binary']
    if sha(binary)!=build['binary_sha256']:raise ValueError('Binary changed')
    folder=ROOT/('smokes' if smoke else 'runs')/f"L{level}_chi100_{'tanh13' if mode else 'sharp13'}"
    text=input_for(level,mode,.01 if smoke else None)
    if folder.exists():
        prior=json.loads((folder/'result.json').read_text())
        if prior.get('status')!='complete_native_checks' or (folder/'athinput').read_text()!=text or prior['binary_sha256']!=build['binary_sha256']:
            raise RuntimeError('Existing partial/different case requires review: '+str(folder))
        return prior
    n=(8*2**level)*(4*2**level)**2
    # Measured native VTK is 24 B/cell (see audit L3); reserve 32 B/cell,
    # 20 percent plot margin, eight full 64 B/cell restarts plus MPI metadata.
    disk=int(n*(32*103*1.2+8*64)+GIB) if not smoke else GIB
    storage=storage_snapshot(ROOT);require_storage(storage,disk)
    if psutil.virtual_memory().available<n*768+2*GIB:raise RuntimeError('RAM guard')
    folder.mkdir(parents=True);(folder/'athinput').write_text(text);params=parse_file(folder/'athinput')
    if not (math.isclose(params['chi'],100) and math.isclose(params['mach'],2)):raise ValueError('Parameter mismatch')
    command=['mpirun','--bind-to','core','-np','8',binary,'-i','athinput']
    record=dict(status='running',level=level,mode=mode,directory=str(folder),parameters=params,
       command=command,binary_sha256=build['binary_sha256'],parameter_sha256=sha(folder/'athinput'),
       storage_preflight=storage,reserved_output_gib=disk/GIB,started_unix=time.time())
    save(folder/'result.json',record);save(ROOT/'current.json',record)
    print('START '+str(folder),flush=True)
    peak=0;env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    with (folder/'run.log').open('x') as log, (folder/'resources.jsonl').open('x') as resources:
        proc=subprocess.Popen(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        handle=psutil.Process(proc.pid)
        while proc.poll() is None:
            try:peak=max(peak,sum(p.memory_info().rss for p in handle.children(recursive=True)))
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
            resources.write(json.dumps(dict(unix=time.time(),peak_child_rss_bytes=peak,
                              ram_available_bytes=psutil.virtual_memory().available,loadavg=os.getloadavg()))+'\n');resources.flush()
            if time.time()-record['started_unix']>(300 if smoke else 21600):
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=15)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=15)
                break
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:pass
    record.update(status='needs_review',returncode=proc.returncode,wall_seconds=time.time()-record['started_unix'],peak_child_rss_gib=peak/GIB)
    save(folder/'result.json',record)
    if proc.returncode:raise RuntimeError('Solver failure; retained outputs')
    record.update(validate(folder,params,level,mode,smoke))
    record['status']='complete_native_checks';save(folder/'result.json',record);save(ROOT/'current.json',record)
    print(f"FINISH L{level} mode={mode}: {record['unique_snapshots']} times, {record['wall_seconds']:.1f}s",flush=True)
    return record

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--smoke',action='store_true');args=ap.parse_args()
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        f=Path('/home/kaan/performance_20260907',name).open('a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    levels=(3,) if args.smoke else LEVELS
    batch=dict(status='running',pid=os.getpid(),finished=[])
    output=ROOT/('smoke_batch.json' if args.smoke else 'batch.json')
    try:
        if not args.smoke:
            proof=json.loads((ROOT/'smoke_batch.json').read_text())
            if proof['status']!='complete_native_checks':raise ValueError('Smoke validation required')
        for level in levels:
            a=input_for(level,0);b=input_for(level,1)
            if re.sub(r'velocity_ic_tanh = [01]','',a)!=re.sub(r'velocity_ic_tanh = [01]','',b):raise ValueError('Confounded pair')
            for mode in (0,1):
                batch['finished'].append(run_case(level,mode,args.smoke));save(output,batch)
        batch['status']='complete_native_checks'
    except Exception as error:
        batch.update(status='stopped_needs_review',error=str(error));raise
    finally:save(output,batch)

if __name__=='__main__':main()
