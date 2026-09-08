"""New sharp-only repaired MFV preparation; full launch is deliberately separate."""
import argparse
import fcntl
import gc
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import struct
import subprocess
import time

import h5py
import numpy as np
import psutil
import mfv_short_controls as short
import mfv_onset as onset  # only state(), mass_account(), constants; NOT old clock/runner
import diagnose_mfv_restart as decoder
from storage_guard import GIB, storage_snapshot, require_storage

ROOT=short.ROOT
HERE=Path(__file__).resolve().parent
PACKAGE=ROOT/'sharp_prepare_runner_v1'
DEST=ROOT/'sharp_prepare_native_v1'
OLD=ROOT.parent/'runs/L3_mfv_sharp13'
OLDSHORT=ROOT.parent/'smokes/L3_mfv_sharp13'
HIST=ROOT/'onset_native_v1'
BINARY=onset.BINARY
SHARP_IC='ae510c5a853ace97e3c55c6b234efb3e5cf6f64a1dbd512e5ee7be8d0e1b52e5'
SHORT_INPUT='7f693c0d465973b39537bc470082ccd5dbb2f910877f67a1e4c2b486f49d24de'
HIST_REVIEW='53d8f951fabe54ec48795a626be1a55d27a48e25192d5021dd705f7ce95cfb5f'
HIST_PLAN='52c8ecbea186266d336652bcd0ad4d465de3b2a0a8a19b13880f126e027998ce'
sha,check=short.sha,short.check


def safe(value):
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,dict):return {k:safe(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [safe(v) for v in value]
    return value


def save(path,value):short.save_new(path,safe(value))


def clock(p):
    begin,end,dt,first=[float(p[k]) for k in ('TimeBegin','TimeMax','TimeBetSnapshot','TimeOfFirstSnapshot')]
    check(begin==first==0 and end>0 and dt>0 and float(p['ComovingIntegrationOn'])==0,'Unsupported clock')
    tick=end/(1<<60);expected=[];t=first
    while t<=end:
        check(len(expected)<104,'Too many scheduled times')
        expected.append(int(t/tick)*tick);t+=dt
    if expected[-1]!=end:expected.append(end)
    return expected,tick


def cadence(times,p):
    expected,tick=clock(p);tol=2*tick+8*np.finfo(float).eps*float(p['TimeMax'])
    check(len(expected)<=len(times)<=104 and all(math.isfinite(t) for t in times),'Invalid time coverage')
    check(times[0]==0 and abs(times[-1]-float(p['TimeMax']))<=tol and all(b>=a for a,b in zip(times,times[1:])),'Invalid time order/end')
    cursor=0;offsets=[]
    for target in expected:
        while cursor<len(times) and times[cursor]<target-tol:cursor+=1
        check(cursor<len(times) and abs(times[cursor]-target)<=tol,'Missing scheduled state')
        offsets.append(abs(times[cursor]-target));cursor+=1
    return dict(bits=60,actual_count=len(times),expected_count=len(expected),tick_code=tick,
                tolerance_code=float(tol),maximum_offset=max(offsets))


def same_fields(a,b,exclude=()):
    check(set(a)==set(b),'Fields differ')
    matches={k:bool(a[k].dtype==b[k].dtype and np.array_equal(a[k],b[k])) for k in a if k not in exclude}
    check(all(matches.values()),'Nonvelocity fields differ')
    return matches


def ic_law(a,p,sharp_law):
    pos=a['Coordinates'].astype(float);r=np.linalg.norm(pos-p['center'],axis=1)
    vw=p['v_wind'];rv=p['rv_scale'];rho=1+(p['chi']-1)*.5*(1-np.tanh((r-1)/.1))
    expected=np.where(r>rv,vw,0) if sharp_law else vw*(1-.5*(1-np.tanh((r-rv)/.1)))
    check(np.max(abs(a['Velocities'][:,0]-expected))/vw<=2e-7 and (a['Velocities'][:,1:]==0).all(),'Wrong IC velocity law')
    dx=20/64;indices=np.floor(pos/dx).astype(int)
    check(np.max(abs(pos-(indices+.5)*dx))<=1e-6 and len(np.unique(np.ravel_multi_index(indices.T,(64,32,32))))==65536,'Wrong lattice')
    check(np.max(abs(a['Masses'].astype(float)/dx**3-rho)/rho)<=2e-7,'IC density mismatch')
    check(np.max(abs(a['InternalEnergy'].astype(float)*(p['gamma']-1)*rho-1))<=2e-7,'IC pressure construction mismatch')
    return dict(lattice=[64,32,32],max_velocity_error=float(np.max(abs(a['Velocities'][:,0]-expected))))


def scaling(ic,full,half):
    ic,full,half=[np.asarray(v,dtype=float) for v in (ic,full,half)]
    check(ic.shape==full.shape==half.shape and all(np.isfinite(a).all() for a in (ic,full,half)),'Bad timing arrays')
    d1=full-ic;d2=half-ic;norm=np.linalg.norm(d1)
    check(np.max(abs(d1))>=1e-6 and norm>0,'Nondiscriminating timing test')
    ratio=float(np.linalg.norm(d2)/norm);bound=float(4*np.finfo(np.float32).eps*max(1.,float(np.max(abs(ic)))))
    residual=float(np.max(abs(2*half-full-ic)))
    check(abs(ratio-.5)<=.002 and residual<=bound,'Not validated half-kick scaling')
    return dict(norm_ratio=ratio,zero_step_max_error=residual,float32_bound=bound)


def input_text(kind):
    text=(OLDSHORT/'params.txt').read_text()
    if kind=='short':return text
    check(kind in ('timing_full','timing_half'),'Unknown diagnostic')
    p=short.parameters(text);p.update(TimeMax='.00004',TimeBetSnapshot='.00004',MaxSizeTimestep='1e-5' if kind=='timing_full' else '5e-6')
    return ''.join(f'{k:32s} {v}\n' for k,v in p.items())


def recipe():
    p,physics,tcc=onset.inputs()
    check(sha(BINARY)==onset.EXPECTED_BINARY,'Repaired binary changed')
    check(sha(OLD/'ics.hdf5')==sha(OLDSHORT/'ics.hdf5')==SHARP_IC,'Sharp IC changed')
    check(sha(OLD/'params.txt')==onset.EXPECTED_INPUT and sha(OLDSHORT/'params.txt')==SHORT_INPUT,'Sharp params changed')
    original=json.loads((OLD/'result.json').read_text())
    check(original['physics']==physics and (original['variant'],original['mode'],original['level'])==('mfv',0,3),'Sharp recipe differs')
    a,_=short.read_arrays(OLD/'ics.hdf5',False);b,_=short.read_arrays(onset.OLD/'ics.hdf5',False)
    same_fields(a,b,('Velocities',));laws=[ic_law(a,physics,True),ic_law(b,physics,False)]
    with h5py.File(OLD/'ics.hdf5') as x,h5py.File(onset.OLD/'ics.hdf5') as y:
        check(set(x['Header'].attrs)==set(y['Header'].attrs) and all(np.array_equal(x['Header'].attrs[k],y['Header'].attrs[k]) for k in x['Header'].attrs),'IC header difference')
    check(sha(ROOT/'onset_runner_v1/plan.json')==HIST_PLAN and sha(ROOT/'onset_review_v2/report.json')==HIST_REVIEW,'Historical full evidence changed')
    hplan=json.loads((ROOT/'onset_runner_v1/plan.json').read_text());review=json.loads((ROOT/'onset_review_v2/report.json').read_text())
    for name,digest in hplan['files'].items():check(sha(ROOT/'onset_runner_v1'/name)==digest,'Historical frozen helper changed')
    for name,digest in onset.PINNED_SOURCE.items():check(sha(ROOT/'repaired'/name)==digest,'Native source changed')
    check(review['status']=='passed_onset_diagnostic_not_full_pair' and review['native_frames']==101,'Historical diagnostic incomplete')
    check(sha(HIST/'ics.hdf5')==onset.EXPECTED_IC and sha(HIST/'params.txt')==onset.EXPECTED_INPUT,'Historical copied inputs changed')
    launch=json.loads((HIST/'launch.json').read_text())
    check(launch['binary_sha256']==onset.EXPECTED_BINARY and launch['physics']==physics and launch['command']==['mpirun','--bind-to','core','-np','8',str(BINARY),'params.txt'],'Historical launch differs')
    check(sha(ROOT/'short_native_v1/validation.json')==onset.SHORT_VALIDATION,'Repaired historical short evidence changed')
    check(sha(ROOT/'short_native_v1/repaired/params.txt')==SHORT_INPUT,'Historical short input differs')
    return dict(physics=physics,tcc=tcc,laws=laws,historical_review=review,historical_plan=hplan)


def historical_hashes(r):
    rows=r['historical_review']['all_raw_hashes']+r['historical_review']['terminal_restarts']
    for row in rows:check(sha(row['path'])==row['sha256'],'Historical raw changed')
    return len(rows)


def no_competing():
    for p in psutil.process_iter(['name','status']):
        name=p.info['name'] or ''
        check(not (p.info['status']!=psutil.STATUS_ZOMBIE and (name.lower().startswith(('gizmo','athena','flash','gadget','enzo','ramses','gasoline','arepo')) or name in ('cc1','cc1plus','f951','make'))),'Competing native solver/build '+name)


def budget(snapshot,restarts,ic,full=False):
    return math.ceil(1.25*((104 if full else 4)*snapshot+3*restarts+ic+(256 if full else 64)*1024**2))


def freeze():
    check(not PACKAGE.exists() and not DEST.exists(),'Existing sharp preparation; no repeat')
    r=recipe();historical_hashes(r);no_competing()
    snap=max(f.stat().st_size for f in (HIST/'output').glob('snapshot_*.hdf5'))
    restarts=sum((HIST/'output/restartfiles'/f'restart.{i}').stat().st_size for i in range(8));ic=(OLD/'ics.hdf5').stat().st_size
    small=budget(snap,restarts,ic);full=budget(snap,restarts,ic,True);disk=storage_snapshot(ROOT)
    require_storage(disk,3*small+full);check(psutil.virtual_memory().available>12*GIB,'RAM preflight')
    PACKAGE.mkdir()
    names=['mfv_sharp_prepare.py','test_mfv_sharp_prepare.py','MFV_SHARP_PREPARATION_PLAN.md','mfv_short_controls.py','mfv_onset.py','diagnose_mfv_restart.py','storage_guard.py']
    for n in names:shutil.copy2(HERE/n,PACKAGE/n)
    plan=dict(status='frozen_short_only',files={n:sha(PACKAGE/n) for n in names},physics=r['physics'],
        binary_sha256=onset.EXPECTED_BINARY,sharp_ic_sha256=SHARP_IC,short_input_sha256=SHORT_INPUT,
        historical_review_sha256=HIST_REVIEW,historical_plan_sha256=HIST_PLAN,short_case_bytes=small,
        potential_full_bytes=full,all_new_bytes=3*small+full,storage=disk,ic_checks=r['laws'],
        case_names=['short','timing_full','timing_half'],wall_limit=180,stop_grace=15,ranks=8)
    with (PACKAGE/'tests.log').open('x') as log:
        subprocess.run(['/home/kaan/venv/bin/python','-m','unittest','-v','test_mfv_sharp_prepare'],cwd=PACKAGE,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
    plan['tests_sha256']=sha(PACKAGE/'tests.log');save(PACKAGE/'plan.json',plan)
    print(json.dumps(dict(status=plan['status'],new_budget_gib=plan['all_new_bytes']/GIB,sha256=sha(PACKAGE/'plan.json'))))


def frozen(plan):
    check(HERE==PACKAGE,'Only frozen preparation may execute')
    for n,digest in plan['files'].items():check(sha(PACKAGE/n)==digest,'Frozen helper changed')
    check(sha(PACKAGE/'tests.log')==plan['tests_sha256'],'Frozen tests changed')
    recipe()


def run_native(folder,text,ic_source,case_bytes,wall_limit,grace,provenance):
    check(not folder.exists(),'Native target already exists')
    require_storage(storage_snapshot(ROOT),case_bytes);check(psutil.virtual_memory().available>12*GIB,'RAM preflight');no_competing()
    folder.mkdir();(folder/'output').mkdir();shutil.copy2(ic_source,folder/'ics.hdf5')
    with (folder/'params.txt').open('x') as stream:stream.write(text)
    command=['mpirun','--bind-to','core','-np','8',str(BINARY),'params.txt']
    save(folder/'launch.json',dict(command=command,binary_sha256=sha(BINARY),ic_sha256=sha(folder/'ics.hdf5'),
        input_sha256=sha(folder/'params.txt'),started_unix=time.time(),provenance=provenance))
    proc=None;peak=0;cpu=[];prev={};prevtime=None;lastdisk=0;failure=None;start=time.monotonic()
    try:
        with (folder/'run.log').open('x') as log,(folder/'resources.jsonl').open('x') as resources:
            proc=subprocess.Popen(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
                env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1'))
            handle=psutil.Process(proc.pid)
            while proc.poll() is None:
                now=time.monotonic();rss=0;current={}
                try:children=handle.children(recursive=True)
                except psutil.NoSuchProcess:proc.wait(timeout=5);break
                for child in children:
                    try:
                        key=(child.pid,child.create_time());c=child.cpu_times();current[key]=c.user+c.system;rss+=child.memory_info().rss
                    except (psutil.NoSuchProcess,psutil.AccessDenied):pass
                busy=None if prevtime is None else sum(max(0,v-prev[k]) for k,v in current.items() if k in prev)/(now-prevtime)
                if busy is not None:cpu.append(busy)
                prev,prevtime=current,now;peak=max(peak,rss)
                resources.write(json.dumps(dict(elapsed=now-start,rss_bytes=rss,busy_cpu_workers=busy))+'\n');resources.flush()
                check(now-start<wall_limit,'Native wall limit');check(psutil.virtual_memory().available>2*GIB,'Live RAM reserve')
                if now-lastdisk>5:require_storage(storage_snapshot(ROOT),0);lastdisk=time.monotonic()
                time.sleep(.1)
    except BaseException as error:
        failure=str(error)
        if proc is not None and proc.poll() is None:short.stop_owned(proc,folder,grace)
    result=dict(status='native_finished_pending_checks' if proc is not None and proc.returncode==0 and failure is None else 'native_failed',
        returncode=None if proc is None else proc.returncode,failure=failure,wall_seconds=time.monotonic()-start,
        peak_child_rss_bytes=peak,median_busy_cpu_workers=statistics.median(cpu) if cpu else None,resource_samples=len(cpu))
    save(folder/'result.json',result);check(result['status']=='native_finished_pending_checks','Native failure retained: '+str(failure))
    return result


def run(plan):
    frozen(plan);check(not DEST.exists(),'Preparation already attempted');require_storage(storage_snapshot(ROOT),plan['all_new_bytes'])
    locks=[]
    try:
        for n in ('benchmark.lock','production.lock'):
            f=open('/home/kaan/performance_20260907/'+n,'a');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
        DEST.mkdir()
        for kind in plan['case_names']:
            frozen(plan)
            result=run_native(DEST/kind,input_text(kind),OLD/'ics.hdf5',plan['short_case_bytes'],180,15,dict(plan_sha256=sha(PACKAGE/'plan.json'),kind=kind))
            print(json.dumps(dict(case=kind,**result)),flush=True)
    finally:
        for f in reversed(locks):f.close()


def terminal(folder,p,initial,full=False):
    request={**onset.ABI,'global_data_all_processes':onset.ABI['global_data_all_processes']+['Ti_Current']}
    types,abi=decoder.layouts(decoder.parse_dwarf(subprocess.check_output(['readelf','--debug-dump=info',str(BINARY)],text=True)),request)
    check(types['global_data_all_processes'].fields['Ti_Current'][0].itemsize==8,'Wrong clock ABI')
    parts=[];cells=[];headers=[];files=[];explicit=[]
    for rank in range(8):
        path=folder/'output/restartfiles'/f'restart.{rank}';digest=sha(path);blob=path.read_bytes();h,a,b,used=decoder.read_prefix(blob,types)
        parts.append(a);cells.append(b);headers.append(h)
        start=types['global_data_all_processes'].itemsize+4+len(a)*types['particle_data'].itemsize+4
        offset=types['gas_cell_data'].fields['MassTrue'][1];size=types['gas_cell_data'].itemsize
        explicit.extend(struct.unpack_from('<d',blob,start+i*size+offset)[0] for i in range(len(b)))
        check(sha(path)==digest,'Restart changed during read');files.append(dict(path=str(path),sha256=digest,bytes=len(blob),prefix_bytes=used))
    h=headers[0];check(all(all(x[k]==h[k] for k in h.dtype.names) for x in headers),'Rank headers differ')
    a=np.concatenate(parts);b=np.concatenate(cells);order=np.argsort(a['ID']);a,b=a[order],b[order]
    check(np.array_equal(a['ID'],initial['ParticleIDs']) and (a['Type']==0).all(),'Terminal IDs/types')
    check(float(h['Time'])==float(h['TimeMax'])==float(p['TimeMax']) and float(h['TimeBegin'])==0,'Terminal endpoint')
    check(float(h['Timebase_interval'])==clock(p)[1] and int(h['Ti_Current'])==1<<60,'Terminal60-bit clock')
    check(int(h['TotNumPart'])==int(h['TotN_gas'])==65536 and float(h['MinEgySpec'])==0 and float(h['BoxSize'])==10 and int(h['ComovingIntegrationOn'])==0,'Terminal recipe')
    check(all(np.isfinite(v[k]).all() for v in (a,b) for k in v.dtype.names),'Terminal nonfinite field')
    check(all((b[k]>0).all() for k in ('MassTrue','Density','Pressure','InternalEnergy','InternalEnergyPred')),'Terminal nonpositive field')
    account=(onset.mass_account if full else short.mass_account)(initial['Masses'],b['MassTrue'],b['dMass'],int(h['NumCurrentTiStep']))
    check(math.fsum(explicit)==account['conserved'] and account['passes'] and account['response_detected'],'Terminal mass gate')
    return safe(dict(clock=int(h['Ti_Current']),mass_account=account,files=files,abi=abi,
        minima={k:float(min(b[k])) for k in ('Pressure','InternalEnergy','InternalEnergyPred')}))


def audit_outputs(folder,physics):
    import yt
    import yt.frontends.gadget.io
    from yt.frontends.gizmo.api import GizmoDataset
    yt.set_log_level(40);rows=[];initial=None
    check(json.loads((folder/'result.json').read_text())['status']=='native_finished_pending_checks','Native did not finish')
    for path in sorted((folder/'output').glob('snapshot_*.hdf5')):
        a,row=onset.state(path,physics);check(not row['errors'],'Invalid native output: '+str(row['errors']))
        if initial is None:initial=a
        ds=GizmoDataset(str(path),bounding_box=np.array([physics['domain_left'],physics['domain_right']]).T);ad=ds.all_data()
        m=ad['PartType0','Masses'].to_value('code_mass').astype(float);rho=ad['PartType0','Density'].to_value('code_density').astype(float)
        sums=[float(m.sum()),float(m[rho>physics['chi']*physics['rho_wind']/3].sum())]
        rel=[abs(x-y)/max(abs(x),1e-12) for x,y in zip((row['total_mass'],row['dense_mass']),sums)]
        check(len(m)==65536 and abs(float(ds.current_time.to_value('code_time'))-row['time_code'])<=1e-12 and max(rel)<1e-11,'Independent reader mismatch')
        check(sha(path)==row['sha256'],'Raw changed during reader check');row['independent_relative_errors']=rel;rows.append(row)
        del ds,ad,a;gc.collect()
    check(initial is not None,'No native outputs');return initial,rows


def analyze(plan):
    frozen(plan);target=DEST/'validation.json';check(not target.exists(),'Report exists; do not repeat')
    r=recipe();ic,_=short.read_arrays(OLD/'ics.hdf5',False)
    hist,_=short.read_arrays(ROOT/'short_native_v1/repaired/output/snapshot_000.hdf5')
    histfull,_=short.read_arrays(HIST/'output/snapshot_000.hdf5');oldsharp,_=short.read_arrays(OLDSHORT/'output/snapshot_000.hdf5')
    cases=[];vel={}
    for kind in plan['case_names']:
        folder=DEST/kind;check((folder/'params.txt').read_text()==input_text(kind) and sha(folder/'ics.hdf5')==SHARP_IC,'Diagnostic inputs differ')
        initial,rows=audit_outputs(folder,plan['physics']);p=short.parameters((folder/'params.txt').read_text())
        match={label:same_fields(initial,other,('Velocities','ParticleVelocities')) for label,other in (('historical_short',hist),('historical_full',histfull),('original_sharp',oldsharp))}
        for k in ('Coordinates','Masses','ParticleIDs','InternalEnergy'):check(np.array_equal(initial[k],ic[k]),'Initial IC recovery failed')
        vel[kind]=initial['Velocities']
        cases.append(dict(kind=kind,outputs=rows,cadence=cadence([x['time_code'] for x in rows],p),initial_exact=match,
            terminal=terminal(folder,p,ic),resources=json.loads((folder/'result.json').read_text())))
    timing=scaling(ic['Velocities'],vel['timing_full'],vel['timing_half']);n=historical_hashes(r)
    report=dict(status='passed_sharp_preparation_not_full_pair',cases=cases,timing=timing,historical_raw_hashes_rechecked=n,
        historical_recipe_reusable=True,plan_sha256=sha(PACKAGE/'plan.json'),script_sha256=sha(__file__),
        accepted_full_controls=44,completed_full_controls_added=0,
        limitations=['Three sharp diagnostics only, not a completed full pair.','Native velocities remain half-kick staggered.',
            'Original periodic boundaries and nonuniform native pressure retained; no cross-code certification.',
            'Engineering mass gate does not establish physical accuracy.'])
    save(target,report);print(json.dumps(dict(status=report['status'],frames=sum(len(c['outputs']) for c in cases),timing=timing,sha256=sha(target))))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['freeze','run','analyze']);mode=parser.parse_args().mode
    if mode=='freeze':freeze()
    else:
        plan=json.loads((PACKAGE/'plan.json').read_text())
        try:(run if mode=='run' else analyze)(plan)
        except BaseException as error:
            target=DEST/(mode+'_error.json')
            if DEST.exists() and not target.exists():save(target,dict(error=str(error),script_sha256=sha(__file__)))
            raise
