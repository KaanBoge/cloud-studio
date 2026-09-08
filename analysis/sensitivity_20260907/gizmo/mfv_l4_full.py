"""Fresh repaired MFV L4 pair only after own-level validation passes."""
import argparse
import gc
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import struct
import subprocess
import sys
import time

import numpy as np
import psutil

PREP=Path('/home/kaan/sensitivity_20260907/gizmo/mfv_timestep_repair_v1/l4_prepare_runner_v1')
sys.path.insert(0,str(PREP))
import mfv_l4_prepare as p
import mfv_l4_native_checks as v
from mfv_l4_native_checks import check,sha,save

HERE=Path(__file__).resolve().parent
PACKAGE=p.BASE/'mfv_timestep_repair_v1/l4_full_runner_v1'
RAW=Path('/mnt/c/Users/kaanb/CloudCrushing/native_runs/sensitivity_20260907/mfv_L4_velocity_pair_v1')
PREP_SHA='579f85c2ca74cf7e44a8529b77d3d8f80e45e6760ccc18fa9aad9bae7c15e096'


def admission(report):
    check(report['status']=='passed_L4_short_preparation_not_full_pair' and len(report['cases'])==6
          and report['full_controls_added']==0 and report['plan_sha256']==PREP_SHA,'Incomplete/wrong L4 preparation')
    check(set(report['timing'])=={'sharp13','tanh13'} and report['full_pair_budget']['bytes']>0,'Missing L4 timing/budget')
    for c in report['cases']:
        check(c['status']=='passed_short_native_checks' and all(r['elements']==v.N for r in c['rows']),'Unvalidated L4 case')


def prerequisites():
    check(sha(PREP/'plan.json')==PREP_SHA,'Preparation plan changed')
    plan=json.loads((PREP/'plan.json').read_text());p.frozen(plan)
    report=json.loads((p.RAW/'validation.json').read_text());admission(report)
    for c in report['cases']:
        for row in c['rows']+c['terminal']['files']:check(sha(row['path'])==row['sha256'],'Preparation raw changed')
        f=Path(c['resources']['directory'])
        check(sha(f/'params.txt')==c['input_sha256'] and sha(f/'ics.hdf5')==c['ic_sha256'],'Preparation inputs changed')
    return plan,report


def inputs_equal(a,b):
    check(a==b,'Paired full inputs differ')
    values=v.parameters(a)
    check(float(values['MaxSizeTimestep'])==.05 and float(values['CpuTimeBetRestartFile'])==3600,'Timing cap/restart change in full run')


def freeze():
    p.new_target(PACKAGE);p.new_target(RAW);held=p.locks();p.no_competing();prior,report=prerequisites()
    before=p.storage(report['full_pair_budget']['bytes']);check(psutil.virtual_memory().available>=16*p.GIB,'Full RAM preflight')
    PACKAGE.mkdir();RAW.mkdir();(RAW/'scratch').mkdir();readback={}
    for law in ('sharp13','tanh13'):
        folder=RAW/law;folder.mkdir()
        shutil.copy2(p.RAW/'inputs'/f'{law}.hdf5',folder/'ics.hdf5');shutil.copy2(p.RAW/'inputs/full.txt',folder/'params.txt')
        for n in ('ics.hdf5','params.txt'):readback[f'{law}/{n}']=sha(folder/n)
    inputs_equal((RAW/'sharp13/params.txt').read_text(),(RAW/'tanh13/params.txt').read_text())
    check(v.parameters((RAW/'sharp13/params.txt').read_text())==p.input_values((p.BASE/'params_mfv_L4.txt').read_text(),prior['physics'],'full'),'Full native numerical settings changed')
    v.prior.same_fields(v.read(RAW/'sharp13/ics.hdf5',False)[0],v.read(RAW/'tanh13/ics.hdf5',False)[0],('Velocities',))
    names=['mfv_l4_full.py','test_mfv_l4_full.py','MFV_L4_FULL_PLAN.md']
    for n in names:shutil.copy2(HERE/n,PACKAGE/n)
    pins={str(PACKAGE/n):sha(PACKAGE/n) for n in names}
    pins.update({str(RAW/n):digest for n,digest in readback.items()})
    for f in (PREP/'plan.json',p.RAW/'validation.json',v.BINARY):pins[str(f)]=sha(f)
    tests=subprocess.run(['/home/kaan/venv/bin/python','-m','unittest','-v','test_mfv_l4_full'],cwd=PACKAGE,capture_output=True,text=True,timeout=60)
    save(PACKAGE/'tests.json',dict(returncode=tests.returncode,stdout=tests.stdout,stderr=tests.stderr))
    check(tests.returncode==0 and 'Ran 7 tests' in tests.stderr and '\nOK\n' in tests.stderr,'New full tests failed')
    pins[str(PACKAGE/'tests.json')]=sha(PACKAGE/'tests.json')
    plan=dict(status='frozen_L4_full_pair_needs_windows_readback',pins=pins,physics=prior['physics'],windows_readback_files=readback,
        preparation_sha256=sha(p.RAW/'validation.json'),budget=report['full_pair_budget'],storage_before=before,
        storage_after=p.storage(report['full_pair_budget']['bytes']),tests=7,native_controls_started=0,binary_sha256=v.BINARY_SHA)
    save(PACKAGE/'plan.json',plan)
    print(json.dumps(dict(status=plan['status'],plan_sha256=sha(PACKAGE/'plan.json'),budget_gib=plan['budget']['bytes']/p.GIB)),flush=True)


def frozen(plan):
    check(HERE==PACKAGE and RAW.resolve()==RAW and plan['status']=='frozen_L4_full_pair_needs_windows_readback','Wrong frozen full scope')
    for path,digest in plan['pins'].items():check(sha(path)==digest,'Changed full pin '+path)
    check(sha(PREP/'plan.json')==PREP_SHA,'Preparation changed')
    p.frozen(json.loads((PREP/'plan.json').read_text()))


def progress(batch):
    tmp=RAW/'batch.json.tmp';p.new_target(tmp);save(tmp,batch);tmp.replace(RAW/'batch.json')


def execute(law,plan):
    folder=RAW/law;p.new_target(folder/'output');p.new_target(folder/'result.json');frozen(plan);p.no_competing()
    p.storage(plan['budget']['bytes']//2);check(psutil.virtual_memory().available>=16*p.GIB,'Full RAM gate')
    command=['mpirun','--bind-to','core','-np','8',str(v.BINARY),'params.txt']
    launch=dict(law=law,command=command,binary_sha256=v.BINARY_SHA,ic_sha256=sha(folder/'ics.hdf5'),input_sha256=sha(folder/'params.txt'),
        started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),plan_sha256=sha(PACKAGE/'plan.json'))
    save(folder/'launch.json',launch);start=time.monotonic();proc=None;failure=None;peak=0;prev={};lastsample=None;busy=[];lastdisk=0
    print('START full L4 '+law,flush=True)
    try:
        with (folder/'run.log').open('x') as log,(folder/'resources.jsonl').open('x') as res:
            proc=subprocess.Popen(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
                env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',TMPDIR=str(RAW/'scratch')))
            handle=psutil.Process(proc.pid);created=handle.create_time();save(folder/'process.json',dict(pid=proc.pid,create_time=created))
            while proc.poll() is None:
                now=time.monotonic();current={};rss=0
                try:children=handle.children(recursive=True)
                except psutil.NoSuchProcess:proc.wait(timeout=5);break
                for child in children:
                    try:
                        c=child.cpu_times();current[(child.pid,child.create_time())]=c.user+c.system;rss+=child.memory_info().rss
                    except psutil.NoSuchProcess:pass
                cores=None if not prev else sum(max(0,c-prev[k]) for k,c in current.items() if k in prev)/(now-lastsample)
                if cores is not None:busy.append(cores)
                prev,lastsample=current,now;peak=max(peak,rss)
                res.write(json.dumps(dict(elapsed_seconds=now-start,child_rss_bytes=rss,busy_cpu_workers=cores))+'\n');res.flush()
                check(now-start<6000,'Full runtime cap');check(psutil.virtual_memory().available>=2*p.GIB,'Full live RAM reserve')
                if now-lastdisk>=30:p.storage(0,True);lastdisk=time.monotonic()
                try:proc.wait(timeout=1)
                except subprocess.TimeoutExpired:pass
    except BaseException as exc:
        failure=repr(exc)
        if proc is not None and proc.poll() is None:p.stop_owned(proc,created,folder)
    result=dict(status='native_finished_pending_checks' if proc is not None and proc.returncode==0 and failure is None else 'failed',
        returncode=proc.returncode if proc else None,error=failure,wall_seconds=time.monotonic()-start,
        peak_child_rss_bytes=peak,median_busy_cpu_workers=statistics.median(busy) if busy else None)
    save(folder/'result.json',result);check(result['status']=='native_finished_pending_checks','Full case failed; raw retained')
    log=(folder/'run.log').read_text();flags=json.loads((p.BASE/'build.json').read_text())['expected_config']['mfv']
    check(all(f in log for f in flags) and 'HYDRO_MESHLESS_FINITE_MASS' not in log and 'Simulation ends.' in log and 'Final time=' in log,'Full native provenance/endpoint')
    return result


def terminal_full(folder,values,ic):
    request={**v.prior.onset.ABI,'global_data_all_processes':v.prior.onset.ABI['global_data_all_processes']+['Ti_Current']}
    types,abi=v.layouts(v.parse_dwarf(subprocess.check_output(['readelf','--debug-dump=info',str(v.BINARY)],text=True)),request)
    v.clock_abi(types);parts=[];cells=[];headers=[];files=[];explicit=[]
    for rank in range(8):
        path=folder/'output/restartfiles'/f'restart.{rank}';digest=sha(path);blob=path.read_bytes()
        h,a,b,used=v.prefix(blob,types);headers.append(h);parts.append(a);cells.append(b)
        start=types['global_data_all_processes'].itemsize+4+len(a)*types['particle_data'].itemsize+4
        offset=types['gas_cell_data'].fields['MassTrue'][1];size=types['gas_cell_data'].itemsize
        explicit.extend(struct.unpack_from('<d',blob,start+i*size+offset)[0] for i in range(len(b)))
        check(sha(path)==digest,'Terminal raw changed');files.append(dict(path=str(path),bytes=len(blob),sha256=digest,prefix_bytes=used))
    h=headers[0];check(all(all(x[k]==h[k] for k in h.dtype.names) for x in headers),'Full rank headers differ')
    a,b=np.concatenate(parts),np.concatenate(cells);order=np.argsort(a['ID']);a,b=a[order],b[order]
    check(np.array_equal(a['ID'],ic['ParticleIDs']) and (a['Type']==0).all(),'Full terminal IDs/types')
    check(float(h['Time'])==float(h['TimeMax'])==float(values['TimeMax']) and float(h['TimeBegin'])==0,'Full terminal endpoint')
    check(float(h['Timebase_interval'])==v.prior.clock(values)[1] and int(h['Ti_Current'])==1<<60,'Full60-bit terminal clock')
    check(int(h['TotNumPart'])==int(h['TotN_gas'])==v.N and float(h['MinEgySpec'])==0 and float(h['BoxSize'])==10 and int(h['ComovingIntegrationOn'])==0,'Full terminal recipe')
    check(all(np.isfinite(x[k]).all() for x in (a,b) for k in x.dtype.names),'Full nonfinite restart')
    check(all((b[k]>0).all() for k in ('MassTrue','Density','Pressure','InternalEnergy','InternalEnergyPred')),'Full nonpositive restart')
    account=v.prior.onset.mass_account(ic['Masses'],b['MassTrue'],b['dMass'],int(h['NumCurrentTiStep']))
    check(math.fsum(explicit)==account['conserved'] and account['passes'] and account['response_detected'],'Full conserved mass gate')
    # Retain provenance of any earlier restart generation too, without deleting it.
    retained=[dict(path=str(f),bytes=f.stat().st_size,sha256=sha(f)) for f in sorted((folder/'output/restartfiles').iterdir()) if f.is_file()]
    return dict(files=files,retained_files=retained,abi=abi,mass_account=account,
                minima={k:float(min(b[k])) for k in ('Density','Pressure','InternalEnergy','InternalEnergyPred')})


def audit_full(law,plan,resources):
    import yt
    import yt.frontends.gadget.io
    from yt.frontends.gizmo.api import GizmoDataset
    yt.set_log_level(40);folder=RAW/law;physics=plan['physics'];rows=[];initial=None
    ic,_=v.read(folder/'ics.hdf5',False);short,_=v.read(p.RAW/(law+'_smoke')/'output/snapshot_000.hdf5')
    for path in sorted((folder/'output').glob('snapshot_*.hdf5')):
        digest=sha(path);a,t=v.read(path);m=a['Masses'].astype(float);rho=a['Density'].astype(float)
        direct=[float(m.sum()),float(m[rho>physics['chi']*physics['rho_wind']/3].sum())]
        ds=GizmoDataset(str(path),bounding_box=np.array([physics['domain_left'],physics['domain_right']]).T);ad=ds.all_data()
        ym=ad['PartType0','Masses'].to_value('code_mass').astype(float);yr=ad['PartType0','Density'].to_value('code_density').astype(float)
        errors=[abs(x-y)/max(abs(x),1e-12) for x,y in zip(direct,[float(ym.sum()),float(ym[yr>physics['chi']*physics['rho_wind']/3].sum())])]
        check(len(ym)==v.N and float(ds.current_time.to_value('code_time'))==t and max(errors)<=1e-11 and sha(path)==digest,'Full independent reader differs')
        if initial is None:
            initial=a;v.prior.same_fields(initial,short,('Velocities','ParticleVelocities'))
            for k in ('Coordinates','Masses','InternalEnergy','ParticleIDs'):check(np.array_equal(a[k],ic[k]),'Full initial IC recovery')
        rows.append(dict(path=str(path),sha256=digest,bytes=path.stat().st_size,time_code=t,t_over_tcc=t/physics['t_cc'],elements=v.N,
            total_mass=direct[0],dense_mass=direct[1],independent_relative_errors=errors,min_energy=float(min(a['InternalEnergy']))))
        del ds,ad;gc.collect()
    values=v.parameters((folder/'params.txt').read_text());schedule=v.prior.cadence([r['time_code'] for r in rows],values)
    check(initial is not None and rows[0]['dense_mass']>0,'Missing valid full initial state')
    term=terminal_full(folder,values,ic);frozen(plan)
    report=dict(status='passed_full_native_checks',law=law,physics=physics,binary_sha256=v.BINARY_SHA,rows=rows,cadence=schedule,terminal=term,resources=resources,
        input_sha256=sha(folder/'params.txt'),ic_sha256=sha(folder/'ics.hdf5'),scope='Mass diagnostics; native velocities staggered, periodic box, not a cross-code equivalence or physical-accuracy proof.')
    save(folder/'validation.json',report);return report,initial


def run():
    p.new_target(RAW/'batch.json');held=p.locks();p.no_competing();plan=json.loads((PACKAGE/'plan.json').read_text());frozen(plan)
    win=json.loads((RAW/'windows_readback.json').read_text(encoding='utf-8-sig'))
    check(win['plan_sha256']==sha(PACKAGE/'plan.json') and win['hashes']==plan['windows_readback_files'],'Full Windows readback mismatch')
    p.storage(plan['budget']['bytes']);batch=dict(status='running',finished=[],plan_sha256=sha(PACKAGE/'plan.json'),full_controls_added_to_analysis=0)
    progress(batch);initials=[]
    import tempfile
    tempfile.tempdir=str(RAW/'scratch')
    try:
        for index,law in enumerate(('sharp13','tanh13')):
            p.storage(plan['budget']['bytes']*(2-index)//2);batch['active_law']=law;progress(batch)
            resources=execute(law,plan);result,initial=audit_full(law,plan,resources);initials.append(initial);batch['finished'].append(result)
            print(f"FINISH full L4 {law}: {len(result['rows'])} native states, {resources['wall_seconds']:.2f}s, peak {resources['peak_child_rss_bytes']/p.GIB:.3f}GiB",flush=True)
            batch.pop('active_law',None);progress(batch)
        v.prior.same_fields(*initials,('Velocities','ParticleVelocities'))
        inputs_equal((RAW/'sharp13/params.txt').read_text(),(RAW/'tanh13/params.txt').read_text())
        check(batch['finished'][0]['rows'][0]['dense_mass']==batch['finished'][1]['rows'][0]['dense_mass'],'Paired initial denominator differs')
        batch.update(status='passed_full_pair_pending_analysis',new_full_controls_validated=2);progress(batch)
        print('PAIR COMPLETE; new immutable L3/L4 analysis and publication still required.',flush=True)
    except BaseException as exc:
        batch.update(status='needs_review',error=repr(exc));progress(batch);save(RAW/'failure.json',batch);raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['freeze','run']);args=parser.parse_args();(freeze if args.mode=='freeze' else run)()
