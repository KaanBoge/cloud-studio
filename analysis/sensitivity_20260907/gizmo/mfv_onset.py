"""Guarded new historical MFV repair diagnostic. Existing data is never resumed."""
import argparse
import fcntl
import gc
import itertools
import json
import math
import os
from pathlib import Path
import shutil
import signal
import statistics
import struct
import subprocess
import time

import h5py
import numpy as np
import psutil
import mfv_short_controls as short
import diagnose_mfv_restart as decoder
from storage_guard import GIB, storage_snapshot, require_storage

ROOT=short.ROOT
OLD=ROOT.parent/'runs/L3_mfv_tanh13'
PACKAGE=ROOT/'onset_runner_v1'
DEST=ROOT/'onset_native_v1'
SOURCE=Path(__file__).resolve().parent
BINARY=ROOT/'repaired/GIZMO_repaired'
EXPECTED_BINARY=short.EXPECTED['repaired']
EXPECTED_INPUT='3af6f94f62c2b7b7187e24fb4b4087f6f57a2aec5497a72102bba8c33b49c9b2'
EXPECTED_IC='b85251c1ecae2dab665cec6525f06543104b11dc0a2c2763159ecfa5670bc4f0'
SHORT_VALIDATION='1a454241ada059c40994ecc0cde6e2a774fbd7f0ed6d8a608419739188019cc6'
OLD_RESULT='7c14c7e5a55e99f0cc57607aaaddf1c61c47557c4a3e2ad0f8f0c718a4da766e'
PINNED_SOURCE={'run.c':'ed2fd6c642411bd61db8d763e8a328e134d285e9acdddae110cb87b2b45d25dd',
 'allvars.h':'0514cb0c9ffb94bdae1dcbbc5671b6899d71988cfc78d764d24e20d6062041bf',
 'init.c':'6c1fe5e6bb0aa043cbffa988b677927e45bda09fd457757088ba5c21700bd1ba'}
ABI={**short.ABI,'global_data_all_processes':short.ABI['global_data_all_processes']+
     ['TimeBegin','Timebase_interval','ComovingIntegrationOn'],
     'gas_cell_data':short.ABI['gas_cell_data']+['DtInternalEnergy']}
sha,check,save_new=short.sha,short.check,short.save_new


def schedule(p):
    begin,end,dt,first=[float(p[k]) for k in ['TimeBegin','TimeMax','TimeBetSnapshot','TimeOfFirstSnapshot']]
    check(begin==first==0 and end>0 and dt>0 and float(p['ComovingIntegrationOn'])==0,'Unsupported native clock')
    tick=(end-begin)/(1<<29);targets=[];t=first
    while t<=end:
        check(len(targets)<104,'Too many requested outputs')
        targets.append(begin+int((t-begin)/tick)*tick);t+=dt
    if targets[-1]!=end:targets.append(end)
    return targets,tick


def cadence(times,p):
    expected,tick=schedule(p);tol=2*tick+8*np.finfo(float).eps*float(p['TimeMax'])
    check(len(times)>=len(expected) and len(times)<=104,'Missing/excess native states')
    check(all(math.isfinite(t) for t in times) and all(b>=a for a,b in zip(times,times[1:])),'Nonmonotonic native times')
    check(times[0]==0 and abs(times[-1]-float(p['TimeMax']))<=tol,'Native endpoint mismatch')
    cursor=0
    for target in expected:
        while cursor<len(times) and times[cursor]<target-tol:cursor+=1
        check(cursor<len(times) and abs(times[cursor]-target)<=tol,'Missing scheduled native state')
        cursor+=1
    return dict(expected_count=len(expected),actual_count=len(times),tick_code=tick,tolerance_code=tol)


def mass_account(initial,true,pending,steps):
    initial,true,pending=[np.asarray(a,dtype=float) for a in [initial,true,pending]]
    check(initial.ndim==1 and len(initial)>0 and initial.shape==true.shape==pending.shape,'Mass shape mismatch')
    check(all(np.isfinite(a).all() for a in [initial,true,pending]) and (initial>0).all() and (true>0).all(),'Invalid mass ledger')
    check(isinstance(steps,int) and 0<=steps<=32768,'Prospective synchronization envelope exceeded')
    u=2.**-53;n=32*len(initial)*(steps+1);check(n*u<.01,'Unbounded accumulation model')
    scale=math.fsum(itertools.chain(abs(initial),abs(true),abs(pending)))
    residual=math.fsum(itertools.chain(true,pending,-initial));allowance=n*u/(1-n*u)*scale
    change=float(np.max(abs(true-initial)));threshold=32*np.finfo(float).eps*float(max(initial))
    return dict(initial=math.fsum(initial),conserved=math.fsum(true),pending=math.fsum(pending),
      combined=math.fsum(itertools.chain(true,pending)),residual=residual,allowance=allowance,
      passes=abs(residual)<=allowance,changed_particles=int(np.count_nonzero(true!=initial)),
      max_absolute_change=change,response_threshold=threshold,response_detected=change>threshold,steps=steps,
      criterion='Predeclared engineering accumulation gate, not a physical accuracy theorem.')


def inputs():
    check(sha(OLD/'params.txt')==EXPECTED_INPUT and sha(OLD/'ics.hdf5')==EXPECTED_IC,'Original input changed')
    check(sha(OLD/'result.json')==OLD_RESULT,'Original native result changed')
    p=short.parameters((OLD/'params.txt').read_text());old=json.loads((OLD/'result.json').read_text())
    physics=old['physics'];tcc=math.sqrt(physics['chi'])*physics['r_cloud']/physics['v_wind']
    check(physics['chi']==100 and physics['mach']==2 and old['level']==3 and old['mode']==1,'Wrong original recipe')
    check(float(p['TimeMax'])==5*tcc and float(p['TimeBetSnapshot'])==.05*tcc,'Actual schedule inconsistent with pinned physics')
    check(p['InitCondFile']=='ics' and p['OutputDir']=='output' and float(p['CpuTimeBetRestartFile'])==3600,'Wrong native paths/restart')
    return p,physics,tcc


def freeze():
    check(not PACKAGE.exists() and not DEST.exists(),'Existing diagnostic/package; do not repeat')
    p,physics,tcc=inputs()
    check(sha(ROOT/'short_native_v1/validation.json')==SHORT_VALIDATION,'Short evidence changed')
    check(json.loads((ROOT/'short_native_v1/validation.json').read_text())['status']=='passed_short_native_gates_not_full_science','Short gate incomplete')
    shortplan=json.loads((ROOT/'short_runner_v1/plan.json').read_text())
    for name in ['mfv_short_controls.py','diagnose_mfv_restart.py','storage_guard.py']:
        check(sha(SOURCE/name)==shortplan['files'][name],'Previously validated helper changed')
    check(sha(BINARY)==EXPECTED_BINARY,'Repaired executable changed')
    for name,digest in PINNED_SOURCE.items():check(sha(ROOT/'repaired'/name)==digest,'Native scheduling source changed')
    oldpaths=sorted((OLD/'output').glob('snapshot_*.hdf5'));oldtimes=[]
    for path in oldpaths:
        with h5py.File(path,'r') as h:oldtimes.append(float(h['Header'].attrs['Time']))
    oldcadence=cadence(oldtimes,p)
    snap=max(path.stat().st_size for path in oldpaths)
    restart=sum((OLD/'output/restartfiles'/f'restart.{i}').stat().st_size for i in range(8))
    budget=math.ceil(1.25*(104*snap+3*restart+(OLD/'ics.hdf5').stat().st_size+256*1024**2))
    disk=storage_snapshot(ROOT);require_storage(disk,budget)
    check(psutil.virtual_memory().available>12*GIB,'RAM preflight failed')
    PACKAGE.mkdir()
    names=['mfv_onset.py','test_mfv_onset.py','MFV_ONSET_PLAN.md','mfv_short_controls.py','diagnose_mfv_restart.py','storage_guard.py']
    for name in names:shutil.copy2(SOURCE/name,PACKAGE/name)
    plan=dict(status='frozen_not_launched',files={n:sha(PACKAGE/n) for n in names},binary_sha256=EXPECTED_BINARY,
       ic_sha256=EXPECTED_IC,input_sha256=EXPECTED_INPUT,old_result_sha256=OLD_RESULT,short_validation_sha256=SHORT_VALIDATION,
       native_source=PINNED_SOURCE,physics=physics,actual_schedule=dict(begin_code=0,end_code=float(p['TimeMax']),
       interval_code=float(p['TimeBetSnapshot']),tcc_code=tcc,end_tcc=float(p['TimeMax'])/tcc,interval_tcc=float(p['TimeBetSnapshot'])/tcc),
       original_cadence_check=oldcadence,case_bytes=budget,measured_snapshot_bytes=snap,measured_restart_bytes=restart,
       storage_preflight=disk,ranks=8,wall_limit_seconds=600,stop_grace_seconds=30,step_envelope=32768,
       scope='One historical repaired L3 diagnostic; not a full accepted pair or a higher-level launch.')
    with (PACKAGE/'tests.log').open('x') as stream:
        subprocess.run(['/home/kaan/venv/bin/python','-m','unittest','-v','test_mfv_onset'],cwd=PACKAGE,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=60)
    plan['tests_log_sha256']=sha(PACKAGE/'tests.log');save_new(PACKAGE/'plan.json',plan)
    print(json.dumps(dict(status=plan['status'],budget_gib=budget/GIB,plan_sha256=sha(PACKAGE/'plan.json'),cadence=oldcadence)))


def frozen(plan):
    check(SOURCE==PACKAGE,'Only frozen diagnostic may run/analyze')
    for name,digest in plan['files'].items():check(sha(PACKAGE/name)==digest,'Frozen file changed')
    check(sha(PACKAGE/'tests.log')==plan['tests_log_sha256'],'Frozen tests changed')
    check(sha(BINARY)==EXPECTED_BINARY,'Repaired binary changed')
    check(sha(ROOT/'short_native_v1/validation.json')==SHORT_VALIDATION,'Completed short gate changed')
    inputs()


def run(plan):
    frozen(plan);check(not DEST.exists(),'Native diagnostic already attempted')
    require_storage(storage_snapshot(ROOT),plan['case_bytes']);check(psutil.virtual_memory().available>12*GIB,'RAM preflight failed')
    locks=[];proc=None
    try:
        for name in ['benchmark.lock','production.lock']:
            lock=open('/home/kaan/performance_20260907/'+name,'a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(lock)
        DEST.mkdir();(DEST/'output').mkdir()
        for name in ['ics.hdf5','params.txt']:shutil.copy2(OLD/name,DEST/name)
        check(sha(DEST/'ics.hdf5')==EXPECTED_IC and sha(DEST/'params.txt')==EXPECTED_INPUT,'Input copy mismatch')
        command=['mpirun','--bind-to','core','-np','8',str(BINARY),'params.txt']
        launch=dict(command=command,started_unix=time.time(),plan_sha256=sha(PACKAGE/'plan.json'),binary_sha256=EXPECTED_BINARY,
                    ic_sha256=EXPECTED_IC,input_sha256=EXPECTED_INPUT,physics=plan['physics'],actual_schedule=plan['actual_schedule'])
        save_new(DEST/'launch.json',launch);peak=0;failure=None;last_disk=0;previous={};prevtime=None;cpu=[]
        with (DEST/'run.log').open('x') as log,(DEST/'resources.jsonl').open('x') as resources:
            start=time.monotonic()
            proc=subprocess.Popen(command,cwd=DEST,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
                env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1'))
            handle=psutil.Process(proc.pid)
            try:
                while proc.poll() is None:
                    now=time.monotonic();current={};rss=0
                    try:children=handle.children(recursive=True)
                    except psutil.NoSuchProcess:
                        proc.wait(timeout=5);break
                    for child in children:
                        try:
                            stamp=(child.pid,child.create_time());c=child.cpu_times();current[stamp]=c.user+c.system;rss+=child.memory_info().rss
                        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
                    busy=None if prevtime is None else sum(max(0,v-previous[k]) for k,v in current.items() if k in previous)/(now-prevtime)
                    if busy is not None:cpu.append(busy)
                    previous,prevtime=current,now;peak=max(peak,rss)
                    resources.write(json.dumps(dict(elapsed=now-start,child_rss_bytes=rss,busy_cpu_workers=busy))+'\n');resources.flush()
                    check(now-start<plan['wall_limit_seconds'],'External diagnostic wall cap reached')
                    check(psutil.virtual_memory().available>2*GIB,'Runtime RAM reserve')
                    if now-last_disk>=5:require_storage(storage_snapshot(ROOT),0);last_disk=time.monotonic()
                    time.sleep(.5)
            except BaseException as error:
                failure=str(error);short.stop_owned(proc,DEST,plan['stop_grace_seconds'])
        result=dict(status='native_finished_pending_checks' if proc.returncode==0 and failure is None else 'native_failed',
              returncode=proc.returncode,stop_reason=failure,observed_wall_seconds=time.monotonic()-start,
              peak_child_rss_bytes=peak,median_busy_cpu_workers=statistics.median(cpu) if cpu else None,
              resource_samples=len(cpu),plan_sha256=sha(PACKAGE/'plan.json'))
        save_new(DEST/'result.json',result);print(json.dumps(result))
    except BaseException as error:
        if proc is not None and proc.poll() is None:short.stop_owned(proc,DEST,30)
        if DEST.exists() and not (DEST/'failure.json').exists():save_new(DEST/'failure.json',dict(error=str(error)))
        raise
    finally:
        for lock in reversed(locks):lock.close()


def state(path,physics):
    before=sha(path)
    with h5py.File(path,'r') as h:
        t=float(h['Header'].attrs['Time']);count=int(h['Header'].attrs['NumPart_Total'][0]);a={k:v[:] for k,v in h['PartType0'].items()}
    errors=[]
    if count!=65536 or {k:str(v.dtype) for k,v in a.items()}!=short.FIELDS:errors.append('Native schema/count mismatch')
    check('ParticleIDs' in a,'Missing IDs');order=np.argsort(a['ParticleIDs']);a={k:v[order] for k,v in a.items()}
    if not np.array_equal(a['ParticleIDs'],np.arange(1,65537)):errors.append('Native ID coverage')
    for k,v in a.items():
        if not np.isfinite(v).all():errors.append('Nonfinite '+k)
    for k in ['Density','InternalEnergy','Masses','SmoothingLength']:
        if k not in a or not (a[k]>0).all():errors.append('Nonpositive/missing '+k)
    if not (np.all(a['Coordinates']>=physics['domain_left']) and np.all(a['Coordinates']<=physics['domain_right'])):errors.append('Native domain bounds')
    u=a['InternalEnergy'].astype(float);m=a['Masses'].astype(float);rho=a['Density'].astype(float)
    sums=[float(m.sum()),float(m[rho>physics['chi']*physics['rho_wind']/3].sum())]
    quantile=np.quantile(u,[0,.001,.01,.5]).tolist() if np.isfinite(u).all() else None
    history={str(i):float(u[np.flatnonzero(a['ParticleIDs']==i)[0]]) if np.count_nonzero(a['ParticleIDs']==i)==1 and np.isfinite(u[a['ParticleIDs']==i]).all() else None for i in [96,99,102,109]}
    row=dict(path=str(path),sha256=before,time_code=t,errors=errors,total_mass=sums[0] if math.isfinite(sums[0]) else None,
       dense_mass=sums[1] if math.isfinite(sums[1]) else None,energy_quantiles=quantile,
       nonpositive_energy=int(np.count_nonzero(u<=0)),nonfinite_energy=int(np.count_nonzero(~np.isfinite(u))),tracked_ids_energy=history)
    check(sha(path)==before,'Snapshot changed during read')
    return a,row


def terminal(plan,initial):
    types,abi=decoder.layouts(decoder.parse_dwarf(subprocess.check_output(['readelf','--debug-dump=info',str(BINARY)],text=True)),ABI)
    parts=[];cells=[];headers=[];files=[];explicit=[];errors=[]
    for rank in range(8):
        path=DEST/'output/restartfiles'/f'restart.{rank}';digest=sha(path);blob=path.read_bytes()
        h,p,s,used=decoder.read_prefix(blob,types);parts.append(p);cells.append(s);headers.append(h)
        start=types['global_data_all_processes'].itemsize+4+len(p)*types['particle_data'].itemsize+4
        offset=types['gas_cell_data'].fields['MassTrue'][1];size=types['gas_cell_data'].itemsize
        explicit.extend(struct.unpack_from('<d',blob,start+i*size+offset)[0] for i in range(len(s)))
        check(sha(path)==digest,'Restart changed during read');files.append(dict(path=str(path),sha256=digest,bytes=len(blob),parsed_prefix_bytes=used))
    h=headers[0];check(all(all(x[k]==h[k] for k in h.dtype.names) for x in headers),'Restart header mismatch')
    p=np.concatenate(parts);s=np.concatenate(cells);order=np.argsort(p['ID']);p,s=p[order],s[order]
    check(np.array_equal(p['ID'],initial['ParticleIDs']) and (p['Type']==0).all(),'Restart ID/type coverage')
    end=plan['actual_schedule']['end_code'];tick=end/(1<<29)
    check(float(h['Time'])==float(h['TimeMax'])==end and float(h['Timebase_interval'])==tick,'Restart endpoint/clock mismatch')
    check(int(h['TotNumPart'])==65536 and int(h['TotN_gas'])==65536 and float(h['MinEgySpec'])==0 and float(h['BoxSize'])==10 and int(h['ComovingIntegrationOn'])==0,'Restart recipe mismatch')
    for k in s.dtype.names:
        if not np.isfinite(s[k]).all():errors.append('Nonfinite terminal '+k)
    for k in ['MassTrue','Density','Pressure','InternalEnergy','InternalEnergyPred']:
        if not (s[k]>0).all():errors.append('Nonpositive terminal '+k)
    account=mass_account(initial['Masses'],s['MassTrue'],s['dMass'],int(h['NumCurrentTiStep']))
    check(math.fsum(explicit)==account['conserved'],'Independent struct mass differs')
    if not account['passes']:errors.append('Conserved ledger residual exceeds prospective allowance')
    if not account['response_detected']:errors.append('Conserved masses do not respond')
    energies={k:dict(minimum=float(np.min(s[k])) if np.isfinite(s[k]).all() else None,
       nonpositive=int(np.count_nonzero(s[k]<=0))) for k in ['InternalEnergy','InternalEnergyPred','Pressure']}
    return dict(errors=errors,time_code=float(h['Time']),mass_account=account,fields=energies,files=files,abi=abi)


def analyze(plan):
    frozen(plan);target=DEST/'validation.json';check(not target.exists(),'Completed diagnostic report exists')
    import yt.frontends.gadget.io
    from yt.frontends.gizmo.api import GizmoDataset
    physics=plan['physics'];p,_,tcc=inputs();rows=[];failures=[];initial=None
    result=json.loads((DEST/'result.json').read_text())
    if result['status']!='native_finished_pending_checks':failures.append('Native run did not complete without a guard')
    paths=sorted((DEST/'output').glob('snapshot_*.hdf5'))
    for path in paths:
        try:
            a,row=state(path,physics);row['time_tcc']=row['time_code']/tcc
            if initial is None:initial=a
            ds=GizmoDataset(str(path),bounding_box=np.array(list(zip(physics['domain_left'],physics['domain_right']))));ad=ds.all_data()
            mass=ad['PartType0','Masses'].to_value('code_mass').astype(float);rho=ad['PartType0','Density'].to_value('code_density').astype(float)
            sums=[float(mass.sum()),float(mass[rho>physics['chi']*physics['rho_wind']/3].sum())]
            direct=[row['total_mass'],row['dense_mass']]
            relative=[abs(x-y)/max(abs(x),1e-12) if x is not None and math.isfinite(y) else None for x,y in zip(direct,sums)]
            row['independent_relative_errors']=relative
            if len(mass)!=65536 or abs(float(ds.current_time.to_value('code_time'))-row['time_code'])>1e-12 or any(x is None or x>=1e-11 for x in relative):row['errors'].append('Independent reader mismatch')
            check(sha(path)==row['sha256'],'Raw changed after independent read')
            rows.append(row);del ad,ds,a;gc.collect()
        except Exception as error:
            rows.append(dict(path=str(path),sha256=sha(path),errors=['Audit exception: '+str(error)]))
    for row in rows:failures.extend(pathlib_label(row['path'])+': '+e for e in row['errors'])
    checks={}
    try:checks['cadence']=cadence([r['time_code'] for r in rows],p)
    except Exception as error:failures.append('Cadence: '+str(error))
    try:
        original,_=state(OLD/'output/snapshot_000.hdf5',physics)
        checks['initial_nonvelocity_exact']={k:bool(np.array_equal(initial[k],original[k])) for k in short.FIELDS if k not in ['Velocities','ParticleVelocities']}
        if not all(checks['initial_nonvelocity_exact'].values()):failures.append('Initial nonvelocity fields differ from retained original')
    except Exception as error:failures.append('Initial comparison: '+str(error))
    try:
        ic,_=short.read_arrays(OLD/'ics.hdf5',False);checks['terminal']=terminal(plan,ic);failures.extend(checks['terminal']['errors'])
    except Exception as error:failures.append('Terminal check: '+str(error))
    report=dict(status='passed_onset_diagnostic_not_full_pair' if not failures else 'needs_review',failures=failures,outputs=rows,
       checks=checks,resources=result,plan_sha256=sha(PACKAGE/'plan.json'),script_sha256=sha(__file__),physics=physics,
       actual_schedule=plan['actual_schedule'],accepted_full_controls=44,completed_full_controls_added=0,
       limitations=['One repaired historical L3 diagnostic, not the sharp/historical pair or finer convergence.',
        'Velocity and snapshot/restart fields can be staggered in native integration stage.',
        'Mass allowance is a prospective engineering gate, not a physical accuracy bound.',
        'All actual fields/times retained; no cooling, tracking or cross-code baseline certification.'])
    save_new(target,report);print(json.dumps(dict(status=report['status'],frames=len(rows),failures=failures,sha256=sha(target))))


def pathlib_label(path):return Path(path).name


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['freeze','run','analyze']);mode=parser.parse_args().mode
    if mode=='freeze':freeze()
    else:
        plan=json.loads((PACKAGE/'plan.json').read_text())
        (run if mode=='run' else analyze)(plan)
