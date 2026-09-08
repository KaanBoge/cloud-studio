"""New, frozen short MFV reference/repair diagnostics. No full run or auto-resume."""
import argparse
import fcntl
import gc
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import shutil
import signal
import struct
import subprocess
import time

import h5py
import numpy as np
import psutil
import diagnose_mfv_restart as decoder
from storage_guard import storage_snapshot, require_storage, GIB

ROOT=Path('/home/kaan/sensitivity_20260907/gizmo/mfv_timestep_repair_v1')
OLD=ROOT.parent/'smokes/L3_mfv_tanh13'
RUNROOT=ROOT/'short_native_v1'
SOURCE=Path(__file__).resolve().parent
EXPECTED={
 'reference':'2619110ff4e5391d30d8ff08f822e8d98511410aee89089e0bb248a393bc6928',
 'repaired':'4784336422c25db4714c6f56ef95337347f4be18dfd622e2b7e9acf7e1fe3d3c'}
EVIDENCE={'build_report.json':'01457ba7a87dfc4054366d240b66f0ba8caca310af74f945eeafb6ebd928e509',
 'flux_test_report.json':'ffa2d510b2e2737b66bed38ffd03b445694d1f04c3526dd98e0b1f4bd826d340',
 'build_review.json':'7ac8f279308221ad7a012d33f0e229417d10c38b8aaea42426c3a6eb5950e571'}
FIELDS={'Coordinates':'float64','Density':'float32','InternalEnergy':'float32','Masses':'float32',
 'ParticleChildIDsNumber':'uint32','ParticleIDGenerationNumber':'uint32','ParticleIDs':'uint32',
 'ParticleVelocities':'float32','SmoothingLength':'float32','Velocities':'float32'}
ABI={'global_data_all_processes':['Time','TimeMax','TotNumPart','TotN_gas','MinEgySpec','NumCurrentTiStep','cf_hubble_a','BoxSize'],
 'particle_data':['Type','ID','Mass','Pos','Vel'],
 'gas_cell_data':['MassTrue','dMass','DtMass','Density','Pressure','InternalEnergy','InternalEnergyPred']}


def check(ok,message):
    if not ok:raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def save_new(path,data):
    with Path(path).open('x') as stream:json.dump(data,stream,indent=2,allow_nan=False)


def parameters(text):
    result={}
    for line in text.splitlines():
        words=line.split('%')[0].split('#')[0].split()
        if not words:continue
        check(len(words)==2 and words[0] not in result,'Duplicate/malformed parameter')
        result[words[0]]=words[1]
    return result


def mass_account(initial,true,pending,steps):
    initial,true,pending=[np.asarray(x,dtype=np.float64) for x in (initial,true,pending)]
    check(initial.shape==true.shape==pending.shape and initial.ndim==1 and len(initial)>0,'Invalid mass arrays')
    check(all(np.all(np.isfinite(x)) for x in (initial,true,pending)) and np.all(initial>0) and np.all(true>0),'Invalid mass values')
    check(isinstance(steps,int) and 0<=steps<=256,'Native step count outside prospective gate')
    u=2.0**-53;n=32*len(initial)*(steps+1);check(n*u<.01,'Unbounded accumulation model')
    scale=math.fsum(itertools.chain(abs(initial),abs(true),abs(pending)))
    allowance=(n*u/(1-n*u))*scale
    residual=math.fsum(itertools.chain(true,pending,-initial))
    threshold=32*np.finfo(np.float64).eps*float(np.max(initial))
    return dict(initial=math.fsum(initial),conserved=math.fsum(true),pending=math.fsum(pending),
      combined=math.fsum(itertools.chain(true,pending)),residual=residual,allowance=allowance,
      passes=abs(residual)<=allowance,changed_particles=int(np.count_nonzero(true!=initial)),
      max_absolute_change=float(np.max(abs(true-initial))),response_threshold=threshold,
      response_detected=bool(np.max(abs(true-initial))>threshold),steps=steps,
      criterion='Prospective roundoff-scaled smoke gate; not an arbitrary-flux error theorem.')


def read_arrays(path,native=True):
    with h5py.File(path,'r') as h:
        time_value=float(h['Header'].attrs['Time']);a={k:v[:] for k,v in h['PartType0'].items()}
        check(int(h['Header'].attrs['NumPart_Total'][0])==65536,'Unexpected particle count')
    check(all(np.all(np.isfinite(x)) for x in a.values()),'Nonfinite native field')
    order=np.argsort(a['ParticleIDs']);a={k:v[order] for k,v in a.items()}
    check(np.array_equal(a['ParticleIDs'],np.arange(1,65537)),'IDs missing/duplicated')
    if native:
        check({k:str(v.dtype) for k,v in a.items()}==FIELDS,'Native field schema/precision changed')
        for k in ['Masses','Density','InternalEnergy','SmoothingLength']:check(np.all(a[k]>0),'Nonpositive '+k)
        check(np.all(a['Coordinates']>=0) and np.all(a['Coordinates']<=[20,10,10]),'Out-of-domain snapshot')
    return a,time_value


def validate_inputs(text):
    p=parameters(text)
    check(p==parameters((OLD/'params.txt').read_text()),'Inputs not identical to retained short diagnostic')
    fixed={'TimeMax':.1,'TimeBetSnapshot':.1,'MaxSizeTimestep':.05,'MinSizeTimestep':1e-12,
           'CpuTimeBetRestartFile':3600,'MaxMemSize':1000,'PartAllocFactor':2.5,'MinGasTemp':0,
           'TimeBegin':0,'TimeOfFirstSnapshot':0,'OutputListOn':0,'NumFilesPerSnapshot':1}
    check(all(float(p[k])==v for k,v in fixed.items()),'Native short settings changed')
    check(p['InitCondFile']=='ics' and p['OutputDir']=='output','Unexpected native output path')
    return p


def freeze():
    check(not (ROOT/'short_runner_v1').exists() and not RUNROOT.exists(),'Existing native short preparation')
    for name,digest in EVIDENCE.items():check(sha(ROOT/name)==digest,'Build evidence changed')
    old=json.loads((OLD/'result.json').read_text())
    check(sha(OLD/'params.txt')==old['input_sha256'] and sha(OLD/'ics.hdf5')==old['ic_sha256'],'Retained short IC/parameters changed')
    check(old['variant']=='mfv' and old['mode']==1 and old['level']==3,'Wrong retained control')
    validate_inputs((OLD/'params.txt').read_text())
    restart=sum((OLD/'output/restartfiles'/f'restart.{rank}').stat().st_size for rank in range(8))
    snap=max(Path(r['snapshot']).stat().st_size for r in old['outputs'])
    budget=math.ceil(1.25*(4*snap+3*restart+(OLD/'ics.hdf5').stat().st_size+64*1024**2))
    storage=storage_snapshot(ROOT);require_storage(storage,2*budget)
    check(psutil.virtual_memory().available>12*GIB,'Native RAM preflight')
    dest=ROOT/'short_runner_v1';dest.mkdir()
    scripts=['mfv_short_controls.py','test_mfv_short.py','diagnose_mfv_restart.py','storage_guard.py','MFV_SHORT_VALIDATION_PLAN.md']
    for name in scripts:shutil.copy2(SOURCE/name,dest/name)
    plan=dict(status='frozen_not_launched',files={n:sha(dest/n) for n in scripts},evidence=EVIDENCE,
       old_result_sha256=sha(OLD/'result.json'),ic_sha256=old['ic_sha256'],input_sha256=old['input_sha256'],
       physics=old['physics'],case_bytes=budget,pair_bytes=2*budget,measured_snapshot_bytes=snap,
       measured_restart_bytes=restart,storage=storage,wall_limit=180,stop_grace=15,ranks=8,binaries={})
    for variant,digest in EXPECTED.items():
        binary=ROOT/variant/('GIZMO_'+variant);check(sha(binary)==digest,'Binary changed')
        plan['binaries'][variant]=dict(path=str(binary),sha256=digest)
    with (dest/'tests.log').open('x') as stream:
        subprocess.run(['/home/kaan/venv/bin/python','-m','unittest','-v','test_mfv_short'],cwd=dest,
                       stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=60)
    plan['tests_log_sha256']=sha(dest/'tests.log')
    save_new(dest/'plan.json',plan)
    print(json.dumps(dict(status=plan['status'],plan_sha256=sha(dest/'plan.json'),pair_bytes=2*budget)))


def check_frozen(plan):
    check(SOURCE==ROOT/'short_runner_v1','Only frozen runner can launch or analyze')
    check(all(sha(SOURCE/n)==v for n,v in plan['files'].items()),'Frozen file changed')
    check(sha(SOURCE/'tests.log')==plan['tests_log_sha256'],'Frozen tests changed')
    check(all(sha(ROOT/n)==v for n,v in plan['evidence'].items()),'Evidence changed')
    check(sha(OLD/'ics.hdf5')==plan['ic_sha256'] and sha(OLD/'params.txt')==plan['input_sha256'],'Old inputs changed')
    for b in plan['binaries'].values():check(sha(b['path'])==b['sha256'],'Binary changed')


def stop_owned(proc,folder,grace):
    out=folder/'output'
    if out.is_dir():
        try:(out/'stop').touch(exist_ok=False)
        except FileExistsError:pass
    try:proc.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid,signal.SIGTERM)
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()


def run(plan):
    check_frozen(plan);check(not RUNROOT.exists(),'Native case already attempted')
    require_storage(storage_snapshot(ROOT),plan['pair_bytes'])
    check(psutil.virtual_memory().available>12*GIB,'Native RAM preflight')
    locks=[];records=[]
    try:
        for name in ['benchmark.lock','production.lock']:
            lock=open('/home/kaan/performance_20260907/'+name,'a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(lock)
        RUNROOT.mkdir()
        for variant in ['reference','repaired']:
            check_frozen(plan);require_storage(storage_snapshot(ROOT),plan['case_bytes'])
            folder=RUNROOT/variant;folder.mkdir();(folder/'output').mkdir()
            for name in ['ics.hdf5','params.txt']:shutil.copy2(OLD/name,folder/name)
            check(sha(folder/'ics.hdf5')==plan['ic_sha256'] and sha(folder/'params.txt')==plan['input_sha256'],'Copy differs')
            argv=['mpirun','--bind-to','core','-np','8',plan['binaries'][variant]['path'],'params.txt']
            row=dict(variant=variant,directory=str(folder),command=argv,binary_sha256=plan['binaries'][variant]['sha256'],
                     ic_sha256=plan['ic_sha256'],input_sha256=plan['input_sha256'])
            save_new(folder/'launch.json',row)
            start=time.monotonic();peak=0;last_disk=0;failure=None
            with (folder/'run.log').open('x') as stream:
                proc=subprocess.Popen(argv,cwd=folder,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,
                    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1'))
                handle=psutil.Process(proc.pid)
                try:
                    while proc.poll() is None:
                        try:peak=max(peak,sum(c.memory_info().rss for c in handle.children(recursive=True)))
                        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
                        check(time.monotonic()-start<plan['wall_limit'],'Native wall limit')
                        check(psutil.virtual_memory().available>2*GIB,'Runtime RAM reserve')
                        if time.monotonic()-last_disk>2:
                            require_storage(storage_snapshot(ROOT),0);last_disk=time.monotonic()
                        time.sleep(.1)
                except BaseException as error:
                    failure=str(error);stop_owned(proc,folder,plan['stop_grace'])
            row.update(returncode=proc.returncode,observed_process_wall_seconds=time.monotonic()-start,
                       peak_sampled_child_rss_bytes=peak,guard_failure=failure,
                       status='native_finished_pending_checks' if proc.returncode==0 and failure is None else 'native_failed')
            save_new(folder/'result.json',row);records.append(row)
            check(row['status']=='native_finished_pending_checks','Native failure retained')
        save_new(RUNROOT/'batch.json',dict(status='native_finished_pending_checks',cases=records,plan_sha256=sha(SOURCE/'plan.json')))
        print(json.dumps(dict(status='native_finished_pending_checks',cases=len(records))))
    except BaseException as error:
        if RUNROOT.exists() and not (RUNROOT/'failure.json').exists():save_new(RUNROOT/'failure.json',dict(error=str(error),cases=records))
        raise
    finally:
        for lock in reversed(locks):lock.close()


def restart_check(folder,binary,initial):
    types,abi=decoder.layouts(decoder.parse_dwarf(subprocess.check_output(['readelf','--debug-dump=info',str(binary)],text=True)),ABI)
    parts=[];cells=[];headers=[];files=[];explicit=[]
    for rank in range(8):
        path=folder/'output/restartfiles'/f'restart.{rank}';before=sha(path);blob=path.read_bytes()
        a,p,s,used=decoder.read_prefix(blob,types)
        parts.append(p);cells.append(s);headers.append(a)
        start=types['global_data_all_processes'].itemsize+4+len(p)*types['particle_data'].itemsize+4
        offset=types['gas_cell_data'].fields['MassTrue'][1];size=types['gas_cell_data'].itemsize
        explicit.extend(struct.unpack_from('<d',blob,start+i*size+offset)[0] for i in range(len(s)))
        files.append(dict(path=str(path),bytes=len(blob),sha256=before,parsed_prefix_bytes=used))
        check(sha(path)==before,'Restart changed during read')
    h=headers[0];check(all(all(x[n]==h[n] for n in h.dtype.names) for x in headers),'Restart headers disagree')
    p=np.concatenate(parts);s=np.concatenate(cells);order=np.argsort(p['ID']);p,s=p[order],s[order]
    check(np.array_equal(p['ID'],initial['ParticleIDs']) and len(p)==65536,'Restart ID coverage')
    check(float(h['Time'])==float(h['TimeMax'])==.1 and int(h['TotNumPart'])==65536,'Restart endpoint/count')
    check(float(h['MinEgySpec'])==0 and float(h['BoxSize'])==10 and np.all(p['Type']==0),'Restart physical recipe')
    for key in s.dtype.names:check(np.all(np.isfinite(s[key])),'Nonfinite restart '+key)
    for key in ['MassTrue','Density','Pressure','InternalEnergy','InternalEnergyPred']:check(np.all(s[key]>0),'Nonpositive restart '+key)
    account=mass_account(initial['Masses'],s['MassTrue'],s['dMass'],int(h['NumCurrentTiStep']))
    check(math.fsum(explicit)==account['conserved'],'Independent struct mass decoding differs')
    return dict(time_code=float(h['Time']),mass_account=account,files=files,abi=abi,
        nonzero_DtMass=int(np.count_nonzero(s['DtMass'])),nonzero_dMass=int(np.count_nonzero(s['dMass'])),
        min_energy=float(np.min(s['InternalEnergy'])),min_pressure=float(np.min(s['Pressure'])))


def analyze(plan):
    check_frozen(plan);target=RUNROOT/'validation.json';check(not target.exists(),'Completed native validation exists')
    import yt.frontends.gadget.io
    from yt.frontends.gizmo.api import GizmoDataset
    old_initial,_=read_arrays(OLD/'ics.hdf5',False);cases=[];failures=[];initial_arrays={}
    for variant in ['reference','repaired']:
        folder=RUNROOT/variant;result=json.loads((folder/'result.json').read_text())
        check(result['status']=='native_finished_pending_checks','Unfinished native case')
        paths=sorted((folder/'output').glob('snapshot_*.hdf5'));rows=[]
        for path in paths:
            before=sha(path);a,t=read_arrays(path);mass=a['Masses'].astype(float);rho=a['Density'].astype(float)
            direct=[float(mass.sum()),float(mass[rho>100/3].sum())]
            ds=GizmoDataset(str(path),bounding_box=np.array([[0,20],[0,10],[0,10]]));ad=ds.all_data()
            ym=ad['PartType0','Masses'].to_value('code_mass').astype(float);yr=ad['PartType0','Density'].to_value('code_density').astype(float)
            independent=[float(ym.sum()),float(ym[yr>100/3].sum())]
            check(len(ym)==65536 and abs(float(ds.current_time.to_value('code_time'))-t)<1e-12,'Independent time/coverage')
            errors=[abs(x-y)/max(abs(x),1e-12) for x,y in zip(direct,independent)]
            check(max(errors)<1e-11 and sha(path)==before,'Independent snapshot sum or hash changed')
            if not rows:initial_arrays[variant]=a
            row=dict(path=str(path),sha256=before,time_code=t,total_mass=direct[0],dense_mass=direct[1],independent_relative_errors=errors)
            if variant=='reference':
                oldpath=OLD/'output'/path.name;oa,ot=read_arrays(oldpath)
                exact=t==ot and set(a)==set(oa) and all(np.array_equal(a[k],oa[k]) for k in a)
                row['retained_original_exact']=bool(exact)
                if not exact:failures.append('Reference rebuild differs from old native '+path.name)
            rows.append(row);del ad,ds;gc.collect()
        times=[r['time_code'] for r in rows]
        check(2<=len(times)<=4 and times[0]==0 and times[-1]==.1 and all(y>=x for x,y in zip(times,times[1:])),'Short native cadence')
        restart=restart_check(folder,plan['binaries'][variant]['path'],old_initial)
        if not restart['mass_account']['passes']:failures.append(variant+' conserved ledger fails prospective gate')
        if variant=='repaired' and not restart['mass_account']['response_detected']:failures.append('Repaired conserved mass does not respond')
        cases.append(dict(variant=variant,outputs=rows,restart=restart,resources=result))
    base=initial_arrays['reference'];candidate=initial_arrays['repaired']
    initial_matches={k:bool(np.array_equal(base[k],candidate[k])) for k in base if k not in ['Velocities','ParticleVelocities']}
    if not all(initial_matches.values()):failures.append('Repaired native initial nonvelocity fields differ')
    report=dict(status='passed_short_native_gates_not_full_science' if not failures else 'needs_review',failures=failures,
        cases=cases,initial_nonvelocity_exact=initial_matches,script_sha256=sha(__file__),plan_sha256=sha(SOURCE/'plan.json'),
        completed_full_controls_added=0,accepted_full_controls=44,
        limitations=['Only historical L3 through code time0.1, not the late thermal failure.',
                    'Snapshots and final restart can have different native integration stages.',
                    'Mass allowance is the predeclared roundoff-scaled engineering gate, not a universal error theorem.',
                    'No source, raw, timestep, floor or timestamp was changed after the candidate build.'])
    save_new(target,report)
    print(json.dumps(dict(status=report['status'],native_frames=sum(len(c['outputs']) for c in cases),failures=failures,sha256=sha(target))))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['freeze','run','analyze']);args=parser.parse_args()
    if args.mode=='freeze':freeze()
    else:
        plan=json.loads((SOURCE/'plan.json').read_text())
        try:(run if args.mode=='run' else analyze)(plan)
        except BaseException as error:
            if args.mode=='analyze' and not (RUNROOT/'analysis_error.json').exists():
                save_new(RUNROOT/'analysis_error.json',dict(status='analysis_failed_partial_checks',error=str(error),script_sha256=sha(__file__)))
            raise
