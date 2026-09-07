"""Bounded within-code sensitivity pilot, chi=100, Mach=2, levels 3 and 4.

Eight fresh small controls use a single executable per code and retain all raw
outputs. This is not a replacement campaign. Only velocity_ic differs within a
pair. No deletion, hidden daemon, automatic L5/L6 launch or publication.
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
import h5py
import numpy as np
import psutil

sys.path.insert(0,'/mnt/c/Users/kaanb/CloudCrushing/restart_20260907')
import run_l4 as base
from build import ROOT, sha
r=base.r
CHI=100
LEVELS=(3,4)
OLD={'athpp':'historical_tanh13','apk':'historical_momentum13'}


def save(path, data):
    base.save(Path(path),data)


def case_input(code,level,mode):
    if mode not in ('sharp13',OLD[code]):
        raise ValueError('Unknown velocity law for this code')
    text=r.input_for(code,level,CHI,2**(level+1))
    section='problem' if code=='athpp' else 'problem/cloud'
    text=r.set_sections(text,{section:{'velocity_ic':mode}})
    if code=='athpp':
        text=r.set_sections(text,{'job':{'problem_id':f'sensitivity_L{level}_chi100'}})
    return '# Isolated sensitivity control: see velocity_ic; not a replacement run.\n'+text


def without_mode(text):
    return re.sub(r'(?m)^velocity_ic\s*=.*$', '', text)


def native(path,code):
    with h5py.File(path) as f:
        if code=='athpp':
            a=f['prim'][...]
            names=[x.decode() if isinstance(x,bytes) else str(x) for x in f.attrs['VariableNames']]
            at=lambda k:a[names.index(k)]
            out=dict(rho=at('rho'),p=at('press'),v=[at('vel1'),at('vel2'),at('vel3')],c=at('r0'))
            faces=[f[f'x{i}f'][...] for i in (1,2,3)]
            centers=[f[f'x{i}v'][...] for i in (1,2,3)]
            t=float(f.attrs['Time']);dims=list(map(int,f.attrs['RootGridSize']))
        else:
            a=f['prim'][...]
            info=f['Info'].attrs
            if int(info['IncludesGhost']) or int(info['Multilevel']):
                raise ValueError('Only uniform interior fields are supported')
            expected=['prim_density','prim_velocity_1','prim_velocity_2','prim_velocity_3','prim_pressure','prim_scalar_0']
            if list(info['ComponentNames'])!=expected:raise ValueError('Unexpected primitive ordering')
            out=dict(rho=a[:,0],p=a[:,4],v=[a[:,1],a[:,2],a[:,3]],c=a[:,5])
            faces=[f['Locations/'+ax][...] for ax in 'xyz']
            centers=[f['VolumeLocations/'+ax][...] for ax in 'xyz']
            t=float(info['Time']);dims=list(map(int,info['RootGridSize']))
        if np.any(f['Levels'][...]!=0):raise ValueError('Unexpected refinement')
    out.update(time=t,dims=dims,faces=faces,centers=centers)
    out['coord']=[centers[0][:,None,None,:],centers[1][:,None,:,None],centers[2][:,:,None,None]]
    dx=[np.diff(q,axis=1) for q in faces]
    out['dv']=dx[0][:,None,None,:]*dx[1][:,None,:,None]*dx[2][:,:,None,None]
    for k in ('rho','p','c'):
        if not np.all(np.isfinite(out[k])):raise ValueError('Nonfinite '+k)
    if not all(np.all(np.isfinite(x)) for x in out['v']):raise ValueError('Nonfinite velocity')
    if np.any(out['rho']<=0) or np.any(out['p']<=0) or np.any(out['dv']<=0):raise ValueError('Nonpositive native field')
    return out


def initial_check(data,params,code,level,mode):
    if abs(data['time'])>1e-12:raise ValueError('Not an initial output')
    rad=np.sqrt(sum(x*x for x in data['coord']))
    R=params['r_cloud'];chi=params['chi'];rw=params['rho_wind'];vw=params['v_wind']
    f=.5*(1-np.tanh((rad/R-1)/.1))
    rho=rw*(1+(chi-1)*f)
    if mode=='historical_tanh13':
        vx=vw*(1-.5*(1-np.tanh((rad-1.3*R)/(.1*R))))
    elif mode=='historical_momentum13':
        vx=np.where(rad>1.3*R,rw*vw/rho,0)
    elif mode=='sharp13':
        vx=np.where(rad>1.3*R,vw,0)
    else:raise ValueError('Unknown IC')
    axis=0 if code=='athpp' else 1
    expected_c=f if code=='athpp' else (rad<=R).astype(float)
    errors=dict(density_relative=float(np.max(np.abs(data['rho']-rho)/rho)),
        pressure_relative=float(np.max(np.abs(data['p']-params['p_wind']))/params['p_wind']),
        velocity_over_wind=float(max(np.max(np.abs(data['v'][i]-(vx if i==axis else 0))) for i in range(3))/vw),
        tracer_absolute=float(np.max(np.abs(data['c']-expected_c))))
    dims=[8*2**level,4*2**level,4*2**level]
    if code=='apk':dims=[dims[1],dims[0],dims[2]]
    edges=[[-3,17],[-5,5],[-5,5]] if code=='athpp' else [[-5,5],[-3,17],[-5,5]]
    actual_edges=[[float(a.min()),float(a.max())] for a in data['faces']]
    good=data['dims']==dims and data['rho'].size==int(np.prod(dims)) and np.allclose(actual_edges,edges)
    if not good or max(errors.values())>1e-10:raise ValueError('Native initial condition check failed: '+str(errors))
    return dict(passed=True,errors=errors,dimensions=dims,edges=actual_edges,velocity_ic=mode)


def outputs(folder,code):
    rows=[]
    for p in folder.glob('*.athdf' if code=='athpp' else '*.phdf'):
        with h5py.File(p) as f:
            t=float(f.attrs['Time'] if code=='athpp' else f['Info'].attrs['Time'])
        rows.append((t,p))
    return sorted(rows)


def run_case(code,level,mode,build):
    folder=ROOT/'runs'/f'{code}_L{level}_chi100_{mode}'
    text=case_input(code,level,mode)
    binary=build['codes'][code]['binary'];binary_hash=build['codes'][code]['binary_sha256']
    if sha(binary)!=binary_hash:raise ValueError('Binary changed')
    if folder.exists():
        record=json.loads((folder/'result.json').read_text()) if (folder/'result.json').exists() else {}
        if record.get('status')!='complete_native_checks' or record.get('binary_sha256')!=binary_hash or (folder/'athinput').read_text()!=text:
            raise RuntimeError('Existing incomplete/different run requires review: '+str(folder))
        return record
    profile=base.profile_for(code,level)
    disk,ram=r.budgets(profile)
    storage=r.storage_snapshot(ROOT);r.require_storage(storage,disk)
    if psutil.virtual_memory().available<ram:raise RuntimeError('RAM guard')
    if code=='apk':
        gpu=subprocess.check_output(['/usr/lib/wsl/lib/nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True)
        if int(gpu.strip())<2600:raise RuntimeError('VRAM guard')
    folder.mkdir(parents=True)
    (folder/'athinput').write_text(text)
    params=r.parse_file(folder/'athinput')
    if not (math.isclose(params['chi'],100) and math.isclose(params['mach'],2) and math.isclose(params['tmax']/params['t_cc'],5)):
        raise ValueError('Native parameter mismatch')
    command=r.mpi_command(dict(ranks=16 if code=='athpp' else 1,binary=binary))
    record=dict(status='running',code=code,level=level,chi=CHI,mach=2,velocity_ic=mode,
        directory=str(folder),binary_sha256=binary_hash,parameter_sha256=sha(folder/'athinput'),
        command=command,parameters=params,storage_preflight=storage,started_unix=time.time())
    save(folder/'result.json',record)
    print('START '+folder.name,flush=True)
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    peak=0;timed_out=False
    with (folder/'run.log').open('x') as log, (folder/'resources.jsonl').open('x') as samples:
        proc=subprocess.Popen(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        handle=psutil.Process(proc.pid)
        while proc.poll() is None:
            try:peak=max(peak,sum(p.memory_info().rss for p in handle.children(recursive=True)))
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
            samples.write(json.dumps(dict(unix=time.time(),available_ram_bytes=psutil.virtual_memory().available,
                                           peak_child_rss_bytes=peak,loadavg=os.getloadavg()))+'\n');samples.flush()
            if time.time()-record['started_unix']>1200:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=10)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=10)
                timed_out=True;break
            try:proc.wait(timeout=2)
            except subprocess.TimeoutExpired:pass
    record.update(status='needs_review',returncode=proc.returncode,timed_out=timed_out,
                  wall_seconds=time.time()-record['started_unix'],peak_child_rss_gib=peak/r.GIB)
    save(folder/'result.json',record)
    if proc.returncode:raise RuntimeError('Solver failure; files retained: '+str(folder))
    cadence=base.validate_fields(folder,code,params['t_cc'])
    ic=initial_check(native(outputs(folder,code)[0][1],code),params,code,level,mode)
    if not cadence['complete_outputs']:raise ValueError('Incomplete cadence')
    record.update(status='complete_native_checks',cadence=cadence,initial_check=ic)
    save(folder/'result.json',record)
    print(f"FINISH {folder.name}: {cadence['unique_snapshots']} native times, {record['wall_seconds']:.1f} s",flush=True)
    return record


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run',action='store_true');args=ap.parse_args()
    plan=[(code,level,mode) for code in OLD for level in LEVELS for mode in ('sharp13',OLD[code])]
    if not args.run:print(json.dumps(plan));return
    build=json.loads((ROOT/'build.json').read_text())
    if build['status']!='built':raise RuntimeError('No completed build')
    for code in OLD:
        for level in LEVELS:
            if without_mode(case_input(code,level,'sharp13'))!=without_mode(case_input(code,level,OLD[code])):
                raise RuntimeError('Confounded parameter pair')
    locks=[]
    for name in ('benchmark.lock','production.lock'):
        f=Path('/home/kaan/performance_20260907',name).open('a')
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    batch=dict(status='running',plan=plan,finished=[])
    try:
        for code,level,mode in plan:
            batch['finished'].append(run_case(code,level,mode,build));save(ROOT/'batch.json',batch)
        batch['status']='complete_native_checks'
    except Exception as error:
        batch.update(status='stopped_needs_review',error=str(error));raise
    finally:save(ROOT/'batch.json',batch)


if __name__=='__main__':main()
